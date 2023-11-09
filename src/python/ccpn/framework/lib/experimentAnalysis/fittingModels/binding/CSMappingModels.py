"""
This module defines base classes for Series Analysis
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2023"
__credits__ = ("Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2023-11-09 09:49:31 +0000 (Thu, November 09, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
import warnings
from ccpn.util.Logging import getLogger
from ccpn.core.DataTable import TableFrame
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC, MinimiserModel, MinimiserResult, CalculationModel
from ccpn.framework.lib.experimentAnalysis.SeriesTables import CSMOutputFrame
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import ccpn.framework.lib.experimentAnalysis.fittingModels.fitFunctionsLib as lf


########################################################################################################################
####################################    DataSeries Models    ###########################################################
########################################################################################################################

class EuclideanCalculationModel(CalculationModel):
    """
    ChemicalShift Analysis DeltaDeltas shift distance calculation
    """
    ModelName = sv.EUCLIDEAN_DISTANCE
    Info        = 'Calculate The DeltaDelta shifts for a series using the average Euclidean Distance.'
    # MaTex       = r'$\sqrt{\frac{1}{N}\sum_{i=0}^N (\alpha_i*\delta_i)^2}$'
    Description = f'''Model:
                    d = √ 1/N * ∑(𝝰_i * δ_i)^2
                    {sv.uALPHA}: the alpha factor for each atom of interest
                    i: atom type (isotope code per dimension 1H, 15N...)
                    N: atom count
                    {sv.uDelta}: delta shift per atom in the series
                    (with ∑ i=1 to N)
                    Note peak assignments are not mandatory for the calculation.'''
    References  = '''
                    1) Eq. (9) M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).
                    2) Mureddu, L. & Vuister, G. W. Simple high-resolution NMR spectroscopy as a tool in molecular biology.
                       FEBS J. 286, 2035–2042 (2019).
                  '''
    FullDescription = f'{Info} \n {Description}\nReferences: {References}'
    _minimisedProperty = sv.RELDISPLACEMENT

    def __init__(self):
        super().__init__()
        self._alphaFactors = {}
        self._euclideanCalculationMethod = 'mean'

    @property
    def modelArgumentNames(self):
        """ The list of parameters as str used in the calculation model.
          These names will appear as column headers in the output result frames. """
        return [sv.DELTA_DELTA, sv.DELTA_DELTA_ERR]

    def setAlphaFactors(self, values):
        self._alphaFactors = values

    def calculateValues(self, inputDataTables) -> TableFrame:
        """
        Calculate the DeltaDeltas for an input SeriesTable.
        :param inputData: CSMInputFrame
        :return: outputFrame
        """

        outputFrame = CSMOutputFrame()
        outputFrame._buildColumnHeaders()

        inputData = self._getFirstData(inputDataTables)

        grouppedByCollectionsId = inputData.groupby([sv.COLLECTIONID])
        rowIndex = 1
        with warnings.catch_warnings():
            warnings.filterwarnings(action='ignore', category=RuntimeWarning)
            while True:
                for collectionId, groupDf in grouppedByCollectionsId:
                    groupDf.sort_values([self.xSeriesStepHeader], inplace=True)
                    dimensions = groupDf[sv.DIMENSION].unique()
                    dataPerDimensionDict = {}
                    for dim in dimensions:
                        dimRow = groupDf[groupDf[sv.DIMENSION] == dim]
                        dataPerDimensionDict[dim] = dimRow[sv._PPMPOSITION].values
                    alphaFactors = []
                    for i in dataPerDimensionDict:  # get the correct alpha factors per IsotopeCode/dimension and not derive it by atomName.
                        ic = groupDf[groupDf[sv.DIMENSION] == i][sv.ISOTOPECODE].unique()[-1]
                        alphaFactors.append(self._alphaFactors.get(ic, 1))
                    values = np.array(list(dataPerDimensionDict.values()))
                    seriesValues4residue = values.T  ## take the series values in axis 1 and create a 2D array. e.g.:[[8.15 123.49][8.17 123.98]]
                    deltaDeltas = EuclideanCalculationModel._calculateDeltaDeltas(seriesValues4residue, alphaFactors)
                    csmValue = np.mean(deltaDeltas[1:])  ## first item is excluded from as it is always 0 by definition.

                    nmrAtomNames = inputData._getAtomNamesFromGroupedByHeaders(groupDf)

                    # seriesSteps = groupDf[self.xSeriesStepHeader].unique() #cannot use unique! Could be series with same value!!
                    seriesUnits = groupDf[sv.SERIESUNIT].unique()
                    peakPids = groupDf[sv.PEAKPID].unique()
                    snrs = groupDf[sv._SNR].unique()
                    csmValueError = lf.peakErrorBySNRs(snrs, factor=csmValue, power=-2, method='std')
                    for delta, peakPid in zip(deltaDeltas, peakPids):
                        # build the outputFrame
                        peak = self.project.getByPid(peakPid)
                        if not peak:
                            getLogger().warn(f'Cannot find Peak {peakPid}.Skipping...')
                            continue
                        spectrum = peak.spectrum
                        seriesStep = groupDf[groupDf[sv.SPECTRUMPID] == spectrum.pid][sv.SERIES_STEP_X].values[-1]
                        outputFrame.loc[rowIndex, sv.COLLECTIONID] = collectionId
                        outputFrame.loc[rowIndex, sv.PEAKPID] = peakPid
                        outputFrame.loc[rowIndex, sv.COLLECTIONPID] = groupDf[sv.COLLECTIONPID].values[-1]
                        outputFrame.loc[rowIndex, sv.NMRRESIDUEPID] = groupDf[sv.NMRRESIDUEPID].values[-1]
                        outputFrame.loc[rowIndex, sv.SERIES_STEP_Y] = delta
                        outputFrame.loc[rowIndex, self.xSeriesStepHeader] = seriesStep
                        outputFrame.loc[rowIndex, sv.SERIESUNIT] = seriesUnits[-1]
                        outputFrame.loc[rowIndex, sv.CALCULATION_MODEL] = self.ModelName
                        outputFrame.loc[rowIndex, sv.GROUPBYAssignmentHeaders] = \
                        groupDf[sv.GROUPBYAssignmentHeaders].values[0]
                        outputFrame.loc[rowIndex, sv.NMRATOMNAMES] = nmrAtomNames[0] if len(nmrAtomNames) > 0 else ''
                        if len(self.modelArgumentNames) == 2:
                            for header, value in zip(self.modelArgumentNames, [csmValue, csmValueError]):
                                outputFrame.loc[rowIndex, header] = value
                        rowIndex += 1
                break
        return outputFrame

    @staticmethod
    def _calculateDeltaDeltas(data, alphaFactors):
        """
        :param data: 2D array containing A and B coordinates to measure.
        e.g.: for two HN peaks data will be a 2D array, e.g.: [[  8.15842 123.49895][  8.17385 123.98413]]
        :return: float
        """
        deltaDeltas = []
        origin = data[0] # first set of positions (any dimensionality)
        for coord in data:# the other set of positions (same dim as origin)
            dd = lf.euclideanDistance_func(origin, coord, alphaFactors)
            deltaDeltas.append(dd)
        return deltaDeltas


########################################################################################################################
####################################          Saturation Models                      ###################################
########################################################################################################################


class CSMBindingModelBC(FittingModelABC):
    """
    ChemicalShift Analysis: Base calculation model.
    Created as all of the model share the same FitSeries routine
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ySeriesLabel = 'sv.RELDISPLACEMENT'

    def fitSeries(self, inputData:TableFrame, *args, **kwargs) -> TableFrame:
        """
        :param inputData: Datatable derived from a CalculationModel, e.g. the EuclideanCalculationModel.
                    This MUST contain the xColumnHeader ySeriesStepHeader columns.

        :return: output dataTable
        """
        getLogger().warning(sv.UNDER_DEVELOPMENT_WARNING)
        grouppedByCollectionsId = inputData.groupby([sv.COLLECTIONID])
        for collectionId, groupDf in grouppedByCollectionsId:
            groupDf.sort_values([self.xSeriesStepHeader], inplace=True)
            seriesSteps = groupDf[self.xSeriesStepHeader]
            seriesValues = groupDf[self.ySeriesStepHeader]
            xArray = seriesSteps.values # e.g. ligand concentration
            yArray = seriesValues.values # DeltaDeltas
            minimiser = self.Minimiser()
            minimiser.setMethod(self._minimiserMethod)
            try:
                params = minimiser.guess(yArray, xArray)
                result = minimiser.fit(yArray, params, x=xArray)
            except:
                getLogger().warning(f'Fitting Failed for collectionId: {collectionId} data.')
                params = minimiser.params
                result = MinimiserResult(minimiser, params)
            inputData.loc[collectionId, sv.MODEL_NAME] = self.ModelName
            inputData.loc[collectionId, sv.MINIMISER_METHOD] = minimiser.method
            for ix, row in groupDf.iterrows():
                for resultName, resulValue in result.getAllResultsAsDict().items():
                    inputData.loc[ix, resultName] = resulValue
        return inputData

#----------------------------------------------------------------------------------------------------------------------#

class Binding1SiteMinimiser(MinimiserModel):
    """A model based on the oneSiteBindingCurve Fitting equation.
    """
    FITTING_FUNC = lf.oneSiteBinding_func
    MODELNAME = '1_Site_Binding_Model'
    KDstr = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAXstr = sv.BMAX
    defaultParams = {KDstr:1,
                     BMAXstr:0.5}

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.OMIT_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(Binding1SiteMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**Binding1SiteMinimiser.defaultParams)

    def guess(self, data, x, **kws):
        """
        :param data: y values 1D array
        :param x: the x axis values. 1D array
        :param kws:
        :return: dict of params needed for the fitting
        """
        params = self.params
        minKD = np.min(x)
        maxKD = np.max(x)+(np.max(x)*0.5)
        if minKD == maxKD == 0:
            getLogger().warning(f'Fitting model min==max {minKD}, {maxKD}')
            minKD = -1

        params.get(self.KDstr).value = np.mean(x)
        params.get(self.KDstr).min = minKD
        params.get(self.KDstr).max = maxKD
        params.get(self.BMAXstr).value = np.mean(data)
        params.get(self.BMAXstr).min = 0.001
        params.get(self.BMAXstr).max = np.max(data)+(np.max(data)*0.5)
        return params

class OneSiteBindingModel(CSMBindingModelBC):
    """
    ChemicalShift Analysis: One Site-Binding Curve calculation model
    """
    ModelName = sv.ONE_SITE_BINDING_MODEL
    Info = 'Fit data to using the One-Site Specific Binding model in a saturation binding experiment analysis.'
    Description = '''This simple model can be used when a small fraction of the ligand binds to the target, in this state, the bound concentration is ~ equal to the unbound.
                    \nModel:
                    Y = Bmax*X/(Kd + X)
                    Bmax: is the maximum specific binding and in the CSM is given by the Relative displacement (Deltas among ChemicalShifts).
                    Kd: is the (equilibrium) dissociation constant in the same unit as the Series.
                    The Kd represents the [ligand] required to get a half-maximum binding at equilibrium.
                    X: is the Series steps. 
    '''
    References = '''
                1) Model derived from  E.q. 13. Receptor and Binding Studies. Hein et al. 2005. https://doi.org/10.1007/3-540-26574-0_37
                '''
    # MaTex = r'$\frac{B_{Max} * [L]}{[L] + K_d}$'
    Minimiser = Binding1SiteMinimiser
    FullDescription = f'{Info} \n {Description}\nReferences: {References}'

#----------------------------------------------------------------------------------------------------------------------#

class Binding1SiteAllostericMinimiser(MinimiserModel):
    """A model based on the 1-Site-with-Allosteric Fitting equation.
    To be implemented

    """
    FITTING_FUNC = None
    MODELNAME = '1SiteAllosteric_Model'


class OneSiteWithAllostericBindingModel(CSMBindingModelBC):
    """
    ChemicalShift Analysis: One Site-Binding Curve with allosteric modulator calculation model.
    This is different from a Competitive experiment! This model works when two ligands bind different sites.
    The allosteric binding can decrease-increase the main binding event.
    """
    ModelName = sv.ONE_SITE_BINDING_ALLOSTERIC_MODEL
    Info = 'Fit data to using the One Site with allosteric modulator model.'
    Description = sv.NIY_WARNING
    References  = sv.NIY_WARNING
    # References = '''
    #                 1) A. Christopoulos and T. Kenakin, Pharmacol Rev, 54: 323-374, 2002.
    #               '''
    # MaTex = r''
    Minimiser = Binding1SiteAllostericMinimiser
    FullDescription = f'{Info} \n {Description}\nReferences: {References}'
    isEnabled = False

    def fitSeries(self, inputData:TableFrame, rescale=True, *args, **kwargs) -> TableFrame:
        """
        :param inputData:
        :param rescale:
        :param args:
        :param kwargs:
        :return:
        """
        raise RuntimeError(sv.FMNOYERROR)

#----------------------------------------------------------------------------------------------------------------------#

class BindingCooperativityMinimiser(MinimiserModel):
    """A model based on the Binding with Cooperativity  Fitting equation.
    """

    FITTING_FUNC = lf.cooperativity_func
    MODELNAME = 'Cooperativity_binding_Model'

    KDstr = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAXstr = sv.BMAX
    HillSlopestr = sv.HillSlope
    defaultParams = {KDstr:1,
                     BMAXstr:0.5,
                     HillSlopestr:1}

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.OMIT_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(BindingCooperativityMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**BindingCooperativityMinimiser.defaultParams)

    def guess(self, data, x, **kws):
        """
        :param data: y values 1D array
        :param x: the x axis values. 1D array
        :param kws:
        :return: dict of params needed for the fitting
        """
        params = self.params
        minKD = np.min(x)
        maxKD = np.max(x)+(np.max(x)*0.5)
        if minKD == maxKD == 0:
            getLogger().warning(f'Fitting model min==max {minKD}, {maxKD}')
            minKD = -1

        params.get(self.HillSlopestr).value = 1
        params.get(self.KDstr).value = np.mean(x)
        params.get(self.KDstr).min = minKD
        params.get(self.KDstr).max = maxKD
        params.get(self.BMAXstr).value = np.mean(data)
        params.get(self.BMAXstr).min = 0.001
        params.get(self.BMAXstr).max = np.max(data)+(np.max(data)*0.5)
        return params

class CooperativityBindingModel(CSMBindingModelBC):
    """
    ChemicalShift Analysis: Cooperativity-Binding calculation model
    """
    ModelName = sv.COOPERATIVITY_BINDING_MODEL
    Info = 'Fit data to using the  Cooperativity Binding  model in a saturation binding experiment analysis.'
    Description = '''
                    \nModel:
                    Y=Bmax*x^{Hs}/(Kd^{Hs} + x^{Hs}).
                    Bmax: is the maximum specific binding and in the CSM is given by the Relative displacement
                    (Deltas among chemicalShifts).
                    Kd: is the (equilibrium) dissociation constant in the same unit as the Series.
                    The Kd represents the [ligand] required to get a half-maximum binding at equilibrium.
                    
                    Hs: Hill slope coefficient.
                    Hs = 1: ligand/monomer binds to one site with no cooperativity.
                    Hs > 1: ligand/monomer binds to multiple sites with positive cooperativity.
                    Hs < 0: ligand/monomer binds to multiple sites with variable affinities or negative cooperativity.
                    '''
    References = '''
                 1) Model derived from the Hill equation: https://en.wikipedia.org/wiki/Cooperative_binding. 
                 '''
    # MaTex = r'$\frac{B_{Max} * [L]^Hs }{[L]^Hs + K_d^Hs}$'
    Minimiser = BindingCooperativityMinimiser
    FullDescription = f'{Info} \n {Description}\nReferences: {References}'

#----------------------------------------------------------------------------------------------------------------------#

class FractionBindingMinimiser(MinimiserModel):
    """A model based on the fraction bound Fitting equation.
      Eq. from in house calculation (V2 equation)
    """
    FITTING_FUNC = lf.fractionBound_func
    KDstr = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAXstr = sv.BMAX
    defaultParams = {KDstr:1,
                     BMAXstr:0.5}

    def __init__(self, **kwargs):
        super().__init__(FractionBindingMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**FractionBindingMinimiser.defaultParams)

    def guess(self, data, x, **kws):
        """
        :param data: y values 1D array
        :param x: the x axis values. 1D array
        :param kws:
        :return: dict of params needed for the fitting
        """
        params = self.params
        params.get(self.KDstr).value = np.median(x)
        params.get(self.BMAXstr).value = np.max(data)
        return params

class FractionBindingModel(CSMBindingModelBC):
    """
    ChemicalShift Analysis: FractionBinding fitting Curve calculation model
    """
    ModelName = sv.FRACTION_BINDING_MODEL
    Info = 'Fit data to using the Fraction Binding model.'
    Description = '''Fitting model for one-site fraction bound in a saturation binding experiment. This model can be used when a large fraction of the ligand binds to the target.
                    \nModel:
                    Y = BMax * (Kd + x - sqrt((Kd + x)^2 - 4x)) 
                    Bmax: is the maximum specific binding and in the CSM is given by the Relative displacement (Deltas among chemicalShifts).
                    Kd: is the (equilibrium) dissociation constant in the same unit as the Series.
                    The Kd represents the [ligand] required to get a half-maximum binding at equilibrium.
                  '''
    References  = '1) Model derived from Eq. 6  M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).'
    # MaTex = r'$B_{Max}*(K_d+[L]- \sqrt{(K_d+[L]^2)}-4[L]$'
    FullDescription = f'{Info} \n {Description}\nReferences: {References}'
    Minimiser = FractionBindingMinimiser
    isEnabled = True

#----------------------------------------------------------------------------------------------------------------------#

class FractionBindingWitTargetConcentMinimiser(MinimiserModel):
    """A model based on the fraction bound Fitting equation.
      Eq. 6 from  M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).
    """
    FITTING_FUNC = lf.fractionBoundWithPro_func
    KDstr = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAXstr = sv.BMAX
    Tstr = sv.T

    defaultParams = {KDstr:1,
                     BMAXstr:0.5,
                     Tstr:1}

    def __init__(self, **kwargs):
        super().__init__(FractionBindingWitTargetConcentMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**FractionBindingWitTargetConcentMinimiser.defaultParams)

    def guess(self, data, x, **kws):
        """
        :param data: y values 1D array
        :param x: the x axis values. 1D array
        :param kws:
        :return: dict of params needed for the fitting
        """
        params = self.params
        params.get(self.KDstr).value = np.median(x)
        params.get(self.BMAXstr).value = np.max(data)
        return params

class FractionBindingWithTargetConcentrModel(CSMBindingModelBC):
    """
    ChemicalShift Analysis: FractionBinding with Target Concentration fitting Curve calculation model
    """
    ModelName = sv.FRACTION_BINDING_WITHTARGETMODEL
    Info = 'Fit data to using the Fraction Binding model.'
    Description = sv.NIY_WARNING
    References  = sv.NIY_WARNING
    # MaTex = ''
    Minimiser = FractionBindingWitTargetConcentMinimiser
    isEnabled = True

#----------------------------------------------------------------------------------------------------------------------#

class Binding2SiteMinimiser(MinimiserModel):
    """A model based on the twoSiteBindingCurve Fitting equations.
    To be implemented
    """
    FITTING_FUNC = None
    MODELNAME = '2_Site_Binding_Model'

class TwoSiteBindingModel(CSMBindingModelBC):
    """
    ChemicalShift Analysis: Two Site-Binding Curve calculation model
    """
    ModelName = sv.TWO_BINDING_SITE_MODEL
    Info = 'Fit data to using the Two-Binding-Site model.'
    Description = sv.NIY_WARNING
    References  = sv.NIY_WARNING
    # MaTex = r''
    Minimiser = Binding2SiteMinimiser
    FullDescription = f'{Info} \n {Description}\nReferences: {References}'
    isEnabled = False

    def fitSeries(self, inputData:TableFrame, rescale=True, *args, **kwargs) -> TableFrame:
        """
        :param inputData:
        :param rescale:
        :param args:
        :param kwargs:
        :return:
        """
        raise RuntimeError(sv.FMNOYERROR)


########################################################################################################################
####################################           Competion Models                      ###################################
########################################################################################################################



########################################################################################################################
########################################################################################################################



## Add a new Model to the list to be available throughout the program

FittingModels = [
        OneSiteBindingModel,
        FractionBindingModel,
        CooperativityBindingModel,
        OneSiteWithAllostericBindingModel,
        TwoSiteBindingModel,
        ]
CalculationModels = [
                    EuclideanCalculationModel,
                    ]

