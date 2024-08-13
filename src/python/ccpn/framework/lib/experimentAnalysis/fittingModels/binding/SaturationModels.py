"""
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-08-13 16:37:44 +0100 (Tue, August 13, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from ccpn.util.Logging import getLogger
from ccpn.core.DataTable import TableFrame
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC, MinimiserModel, MinimiserResult
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.core.lib.ContextManagers import progressHandler


def oneSiteBinding_func(x, Kd, BMax):
    """
    The one-site Specific Binding equation for a saturation binding experiment.

    Y = Bmax*X/(Kd + X)

    :param x:   1d array. The data to be fitted.
                In the CSM it's the array of deltas (deltas among chemicalShifts, CS, usually in ppm positions)

    :param Kd:  Defines the equilibrium dissociation constant. The value to get a half-maximum binding at equilibrium.
                In the CSM the initial value is calculated from the ligand concentration.
                The ligand concentration is inputted in the SpectrumGroup Series values.

    :param BMax: Defines the max specific binding.
                In the CSM the initial value is calculated from the CS deltas.
                Note, The optimised BMax will be (probably always) larger than the measured CS.

    :return:    Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
                When plotting BMax is the Y axis, Kd the X axis.
    """
    return (BMax * x) / (x + Kd)


def oneSiteNonSpecBinding_func(x, NS, B=1):
    """
    The  one-site non specific Binding equation for a saturation binding experiment.

    Y = NS*X + B

    :param x:  1d array. The data to be fitted.
               In the CSM it's the array of deltas (deltas among chemicalShifts, CS, usually in ppm positions)

    :param NS: the slope of non-specific binding
    :param B:  The non specific binding without ligand.

    :return:   Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
               When plotting BMax is the Y axis, Kd the X axis.
    """

    YnonSpecific = NS * x + B

    return YnonSpecific


def fractionBound_func(x, Kd, BMax):
    """
    The one-site fractionBound equation for a saturation binding experiment.
    V2 equation.
    Y = BMax * (Kd + x - sqrt((Kd + x)^2 - 4x))

    ref: 1) In-house calculations (V2 - wayne - Double check )

    :param x:   1d array. The data to be fitted.
                In the CSM it's the array of deltas (deltas among chemicalShifts, CS, usually in ppm positions)

    :param Kd:  Defines the equilibrium dissociation constant. The value to get a half-maximum binding at equilibrium.
                In the CSM the initial value is calculated from the ligand concentration.
                The ligand concentration is inputted in the SpectrumGroup Series values.

    :param BMax: Defines the max specific binding.
                In the CSM the initial value is calculated from the CS deltas.
                Note, The optimised BMax will be (probably always) larger than the measured CS.

    :return:    Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
                When plotting BMax is the Y axis, Kd the X axis.
    """

    qd = np.sqrt((Kd + x)**2 - 4 * x)
    Y = BMax * (Kd + x - qd)

    return Y


def fractionBoundWithPro_func(x, Kd, BMax, T=1):
    """
    The one-site fractionBound equation for a saturation binding experiment.
    V2 equation.
    Y = BMax * ( (P + x + Kd) - sqrt(P + x + Kd)^2 - 4*P*x)) / 2 * P

    ref: 1) M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).


    :param x:   1d array. The data to be fitted.
                In the CSM it's the array of deltas (deltas among chemicalShifts, CS, usually in ppm positions)

    :param Kd:  Defines the equilibrium dissociation constant. The value to get a half-maximum binding at equilibrium.
                In the CSM the initial value is calculated from the ligand concentration.
                The ligand concentration is inputted in the SpectrumGroup Series values.

    :param BMax: Defines the max specific binding.
                In the CSM the initial value is calculated from the CS deltas.
                Note, The optimised BMax will be (probably always) larger than the measured CS.

    :param T: Target concentration.

    :return:    Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
                When plotting BMax is the Y axis, Kd the X axis.
    """

    Y = BMax * ((T + x + Kd) - np.sqrt((T + x + Kd)**2 - 4 * T * x)) / 2 * T
    return Y


def cooperativity_func(x, Kd, BMax, Hs):
    """
    The cooperativity equation for a saturation binding experiment.

    Y = Bmax*X^Hs/(Kd^Hs + X^Hs)

    :param x:   1d array. The data to be fitted.
                In the CSM it's the array of deltas (deltas among chemicalShifts, CS, usually in ppm positions)

    :param Kd:  Defines the equilibrium dissociation constant. The value to get a half-maximum binding at equilibrium.
                In the CSM the initial value is calculated from the ligand concentration.
                The ligand concentration is inputted in the SpectrumGroup Series values.

    :param BMax: Defines the max specific binding.
                In the CSM the initial value is calculated from the CS deltas.
                Note, The optimised BMax will be (probably always) larger than the measured CS.
    :param Hs: hill slope. Default 1 to assume no cooperativity.
                Hs = 1: ligand/monomer binds to one site with no cooperativity.
                Hs > 1: ligand/monomer binds to multiple sites with positive cooperativity.
                Hs < 0: ligand/monomer binds to multiple sites with variable affinities or negative cooperativity.
    :return:    Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
                When plotting BMax is the Y axis, Kd the X axis.
    """

    Y = (BMax * x**Hs) / (x**Hs + Kd**Hs)
    return Y


## -----------------------     Saturation Minimisers       -----------------------      ##

class _Binding1SiteMinimiser(MinimiserModel):
    """A model based on the oneSiteBindingCurve Fitting equation.
    """
    FITTING_FUNC = oneSiteBinding_func
    MODELNAME = '1_Site_Binding_Model'
    KD = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAX = sv.BMAX
    defaultParams = {KD:1,
                     BMAX:0.5}

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.PROPAGATE_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(_Binding1SiteMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**_Binding1SiteMinimiser.defaultParams)

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

        params.get(self.KD).value = np.mean(x)
        params.get(self.KD).min = minKD
        params.get(self.KD).max = maxKD
        params.get(self.BMAX).value = np.mean(data)
        params.get(self.BMAX).min = 0.001
        params.get(self.BMAX).max = np.max(data)+(np.max(data)*0.5)
        return params

class _Binding2SiteMinimiser(MinimiserModel):
    """A model based on the twoSiteBindingCurve Fitting equations.
    To be implemented
    """
    FITTING_FUNC = None
    MODELNAME = '2_Site_Binding_Model'

class _Binding1SiteAllostericMinimiser(MinimiserModel):
    """A model based on the 1-Site-with-Allosteric Fitting equation.
    To be implemented

    """
    FITTING_FUNC = None
    MODELNAME = '1SiteAllosteric_Model'

class _BindingCooperativityMinimiser(MinimiserModel):
    """A model based on the Binding with Cooperativity  Fitting equation.
    """

    FITTING_FUNC = cooperativity_func
    MODELNAME = 'Cooperativity_binding_Model'

    KD = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAX = sv.BMAX
    HILLSLOPE = sv.HillSlope
    defaultParams = {KD:1,
                     BMAX:0.5,
                     HILLSLOPE:1}

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.PROPAGATE_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(_BindingCooperativityMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**_BindingCooperativityMinimiser.defaultParams)

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

        params.get(self.HILLSLOPE).value = 1
        params.get(self.KD).value = np.mean(x)
        params.get(self.KD).min = minKD
        params.get(self.KD).max = maxKD
        params.get(self.BMAX).value = np.mean(data)
        params.get(self.BMAX).min = 0.001
        params.get(self.BMAX).max = np.max(data)+(np.max(data)*0.5)
        return params

class _FractionBindingMinimiser(MinimiserModel):
    """A model based on the fraction bound Fitting equation.
      Eq. from in house calculation (V2 equation)
    """
    FITTING_FUNC = fractionBound_func
    KD = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAX = sv.BMAX
    defaultParams = {KD:1,
                     BMAX:0.5}

    def __init__(self, **kwargs):
        super().__init__(_FractionBindingMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**_FractionBindingMinimiser.defaultParams)

    def guess(self, data, x, **kws):
        """
        :param data: y values 1D array
        :param x: the x axis values. 1D array
        :param kws:
        :return: dict of params needed for the fitting
        """
        params = self.params
        params.get(self.KD).value = np.median(x)
        params.get(self.BMAX).value = np.max(data)
        return params

class _FractionBindingWitTargetConcentMinimiser(MinimiserModel):
    """A model based on the fraction bound Fitting equation.
      Eq. 6 from  M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).
    """
    FITTING_FUNC = fractionBoundWithPro_func
    KD = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAX = sv.BMAX
    Tstr = sv.T

    defaultParams = {KD:1,
                     BMAX:0.5,
                     Tstr:1}

    def __init__(self, **kwargs):
        super().__init__(_FractionBindingWitTargetConcentMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**_FractionBindingWitTargetConcentMinimiser.defaultParams)

    def guess(self, data, x, **kws):
        """
        :param data: y values 1D array
        :param x: the x axis values. 1D array
        :param kws:
        :return: dict of params needed for the fitting
        """
        params = self.params
        params.get(self.KD).value = np.median(x)
        params.get(self.BMAX).value = np.max(data)
        return params

## -----------------------     End of  Minimisers       -----------------------       ##


## -----------------------      Saturation Models       -----------------------        ##


class BindingModelBC(FittingModelABC):
    """
    Binding Model Base Class
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
        resultData = inputData.copy()
        grouppedByCollectionsId = resultData.groupby([sv.COLLECTIONID])
        with progressHandler(title='Fitting Data', maximum=len(resultData), text='Fitting data....',
                             hideCancelButton=True, ) as progress:
            for jj, (collectionId, groupDf) in enumerate(grouppedByCollectionsId):
                progress.setValue(jj)
                groupDf.sort_values([self.xSeriesStepHeader], inplace=True)
                seriesSteps = groupDf[self.xSeriesStepHeader]
                seriesValues = groupDf[self.ySeriesStepHeader]
                xArray = np.copy(seriesSteps.values)  # e.g. ligand concentration
                yArray = np.copy(seriesValues.values)  # e.g.  DeltaDeltas

                minimiser = self.Minimiser()
                minimiser.setMethod(self._minimiserMethod)
                try:
                    params = minimiser.guess(yArray, xArray)
                    params = self._preFittingAdditionalParamsSettings(groupDf, params)
                    result = minimiser.fit(yArray, params, x=xArray, nan_policy=sv.PROPAGATE_MODE, method=self._minimiserMethod)
                    finalParams = result.calculateStandardErrors(xArray, yArray, self._uncertaintiesMethod, samples=self._uncertaintiesSampleSize)

                except:
                    getLogger().warning(f'Fitting Failed for collectionId: {collectionId} data.')
                    params = minimiser.params
                    result = MinimiserResult(minimiser, params)

                for ix, row in groupDf.iterrows():
                    for resultName, resulValue in result.getAllResultsAsDict(params=finalParams).items():
                        resultData.loc[ix, resultName] = resulValue
                    resultData.loc[ix, sv.MODEL_NAME] = self.modelName
                    resultData.loc[ix, sv.MINIMISER_METHOD] = minimiser.method
                    resultData.loc[ix, sv.UNCERTAINTIESMETHOD] = self._uncertaintiesMethod
        return resultData

    @staticmethod
    def _getAdditionalValueFromArray(arr):
        """Get the first additional value for an array of additional series steps. We take only one because we don't support yet multi values, eg.: multi target concentrations """
        if arr.size == 0:
            return None
        if np.all(arr == arr[0]) and not np.isnan(arr[0]) and arr[0] is not None:
            return arr[0]
        else:
            return None

    def _preFittingAdditionalParamsSettings(self, df, params, **kwargs):
        """called before running the fitting routine to set any additional params options. To be subclasses"""
        return params


class OneSiteBindingModel(BindingModelBC):
    """
    ChemicalShift Analysis: One Site-Binding Curve calculation model
    """
    modelName = sv.ONE_SITE_BINDING_MODEL
    modelInfo = 'Fit data to using the One-Site Specific Binding model in a saturation binding experiment analysis.'
    description = '''This simple model can be used when a small fraction of the ligand binds to the target, in this state, the bound concentration is ~ equal to the unbound.
                    \nModel:
                    Y = Bmax*X/(Kd + X)
                    Bmax: is the maximum specific binding and in the CSM is given by the Relative displacement (Deltas among ChemicalShifts).
                    Kd: is the (equilibrium) dissociation constant in the same unit as the Series.
                    The Kd represents the [ligand] required to get a half-maximum binding at equilibrium.
                    X: is the Series steps. 
    '''
    references = '''
                1) Model derived from  E.q. 13. Receptor and Binding Studies. Hein et al. 2005. https://doi.org/10.1007/3-540-26574-0_37
                '''
    # MaTex = r'$\frac{B_{Max} * [L]}{[L] + K_d}$'
    Minimiser = _Binding1SiteMinimiser
    

class TwoSiteBindingModel(BindingModelBC):
    """
    ChemicalShift Analysis: Two Site-Binding Curve calculation model
    """
    modelName = sv.TWO_BINDING_SITE_MODEL
    modelInfo = 'Fit data to using the Two-Binding-Site model.'
    description = sv.NIY_WARNING
    references  = sv.NIY_WARNING
    # MaTex = r''
    Minimiser = _Binding2SiteMinimiser
    
    isEnabled = False
    targetSeriesAnalyses = [
                                            sv.ChemicalShiftMappingAnalysis
                                            ]

    def fitSeries(self, inputData:TableFrame, rescale=True, *args, **kwargs) -> TableFrame:
        """
        :param inputData:
        :param rescale:
        :param args:
        :param kwargs:
        :return:
        """
        raise RuntimeError(sv.FMNOYERROR)

class OneSiteWithAllostericBindingModel(BindingModelBC):
    """
    ChemicalShift Analysis: One Site-Binding Curve with allosteric modulator calculation model.
    This is different from a Competitive experiment! This model works when two ligands bind different sites.
    The allosteric binding can decrease-increase the main binding event.
    """
    modelName = sv.ONE_SITE_BINDING_ALLOSTERIC_MODEL
    modelInfo = 'Fit data to using the One Site with allosteric modulator model.'
    description = sv.NIY_WARNING
    references  = sv.NIY_WARNING
    # References = '''
    #                 1) A. Christopoulos and T. Kenakin, Pharmacol Rev, 54: 323-374, 2002.
    #               '''
    # MaTex = r''
    Minimiser = _Binding1SiteAllostericMinimiser
    
    isEnabled = False
    targetSeriesAnalyses = [
                                            sv.ChemicalShiftMappingAnalysis
                                            ]

    def fitSeries(self, inputData:TableFrame, rescale=True, *args, **kwargs) -> TableFrame:
        """
        :param inputData:
        :param rescale:
        :param args:
        :param kwargs:
        :return:
        """
        raise RuntimeError(sv.FMNOYERROR)

class CooperativityBindingModel(BindingModelBC):
    """
    ChemicalShift Analysis: Cooperativity-Binding calculation model
    """
    modelName = sv.COOPERATIVITY_BINDING_MODEL
    modelInfo = 'Fit data to using the  Cooperativity Binding  model in a saturation binding experiment analysis.'
    description = '''
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
    references = '''
                 1) Model derived from the Hill equation: https://en.wikipedia.org/wiki/Cooperative_binding. 
                 '''
    # MaTex = r'$\frac{B_{Max} * [L]^Hs }{[L]^Hs + K_d^Hs}$'
    Minimiser = _BindingCooperativityMinimiser
    isEnabled = True
    targetSeriesAnalyses = [
                                            sv.ChemicalShiftMappingAnalysis
                                            ]

class FractionBindingModel(BindingModelBC):
    """
    ChemicalShift Analysis: FractionBinding fitting Curve calculation model
    """
    modelName = sv.FRACTION_BINDING_MODEL
    modelInfo = 'Fit data to using the Fraction Binding model.'
    description = '''Fitting model for one-site fraction bound in a saturation binding experiment. This model can be used when a large fraction of the ligand binds to the target.
                    \nModel:
                    Y = BMax * (Kd + x - sqrt((Kd + x)^2 - 4x)) 
                    Bmax: is the maximum specific binding and in the CSM is given by the Relative displacement (Deltas among chemicalShifts).
                    Kd: is the (equilibrium) dissociation constant in the same unit as the Series.
                    The Kd represents the [ligand] required to get a half-maximum binding at equilibrium.
                  '''
    references  = '1) Model derived from Eq. 6  M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).'
    # MaTex = r'$B_{Max}*(K_d+[L]- \sqrt{(K_d+[L]^2)}-4[L]$'
    
    Minimiser = _FractionBindingMinimiser
    isEnabled = True
    targetSeriesAnalyses = [
                                            sv.ChemicalShiftMappingAnalysis
                                            ]

class FractionBindingWithTargetConcentrModel(BindingModelBC):
    """
    ChemicalShift Analysis: FractionBinding with Target Concentration fitting Curve calculation model
    """
    modelName = sv.FRACTION_BINDING_WITHTARGETMODEL
    modelInfo = 'Fit data to using the Fraction Binding model.'
    description = sv.NIY_WARNING
    references  = sv.NIY_WARNING
    # MaTex = ''
    Minimiser = _FractionBindingWitTargetConcentMinimiser
    isEnabled = True
    targetSeriesAnalyses = [
                                            sv.ChemicalShiftMappingAnalysis
                                            ]


    def _setGlobalTargetConcentrationToParams(self, df, params,):
        """
        :param df:
        :param params:
        :return: LMFIT params with added the Global Target Concentration value as fixed argument.
        """
        globalConcentration = 1 # Fallback. default set to 1 #
        if self.xSeriesStepAdditionalHeader in df:
            seriesAdditionalSteps = df[self.xSeriesStepAdditionalHeader]
            tArray = np.copy(seriesAdditionalSteps.values)
            v = self._getAdditionalValueFromArray(tArray)
            if v is not None:
                globalConcentration = v
        params[sv.T].set(value=globalConcentration, vary=False)
        return params

    def _preFittingAdditionalParamsSettings(self, df, params, **kwargs):
        """called before running the fitting routine to set any additional params options. To be subclasses"""
        params = self._setGlobalTargetConcentrationToParams(df, params)
        return params
