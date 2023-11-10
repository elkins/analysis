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
__dateModified__ = "$dateModified: 2023-11-10 15:58:41 +0000 (Fri, November 10, 2023) $"
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
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC, MinimiserModel, MinimiserResult
from ccpn.framework.lib.experimentAnalysis.calculationModels.CalculationModelABC import CalculationModel
from ccpn.framework.lib.experimentAnalysis.SeriesTables import CSMOutputFrame
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import ccpn.framework.lib.experimentAnalysis.fittingModels.fitFunctionsLib as lf





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

## -----------------------     Saturation Minimisers       -----------------------      ##

class _Binding1SiteMinimiser(MinimiserModel):
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

        params.get(self.KDstr).value = np.mean(x)
        params.get(self.KDstr).min = minKD
        params.get(self.KDstr).max = maxKD
        params.get(self.BMAXstr).value = np.mean(data)
        params.get(self.BMAXstr).min = 0.001
        params.get(self.BMAXstr).max = np.max(data)+(np.max(data)*0.5)
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

        params.get(self.HillSlopestr).value = 1
        params.get(self.KDstr).value = np.mean(x)
        params.get(self.KDstr).min = minKD
        params.get(self.KDstr).max = maxKD
        params.get(self.BMAXstr).value = np.mean(data)
        params.get(self.BMAXstr).min = 0.001
        params.get(self.BMAXstr).max = np.max(data)+(np.max(data)*0.5)
        return params

class _FractionBindingMinimiser(MinimiserModel):
    """A model based on the fraction bound Fitting equation.
      Eq. from in house calculation (V2 equation)
    """
    FITTING_FUNC = lf.fractionBound_func
    KDstr = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAXstr = sv.BMAX
    defaultParams = {KDstr:1,
                     BMAXstr:0.5}

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
        params.get(self.KDstr).value = np.median(x)
        params.get(self.BMAXstr).value = np.max(data)
        return params

class _FractionBindingWitTargetConcentMinimiser(MinimiserModel):
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
        params.get(self.KDstr).value = np.median(x)
        params.get(self.BMAXstr).value = np.max(data)
        return params

## -----------------------     End of  Minimisers       -----------------------       ##


## -----------------------      Saturation Models       -----------------------        ##


class OneSiteBindingModel(BindingModelBC):
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
    Minimiser = _Binding1SiteMinimiser
    FullDescription = f'{Info} \n {Description}\nReferences: {References}'

class TwoSiteBindingModel(BindingModelBC):
    """
    ChemicalShift Analysis: Two Site-Binding Curve calculation model
    """
    ModelName = sv.TWO_BINDING_SITE_MODEL
    Info = 'Fit data to using the Two-Binding-Site model.'
    Description = sv.NIY_WARNING
    References  = sv.NIY_WARNING
    # MaTex = r''
    Minimiser = _Binding2SiteMinimiser
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

class OneSiteWithAllostericBindingModel(BindingModelBC):
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
    Minimiser = _Binding1SiteAllostericMinimiser
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

class CooperativityBindingModel(BindingModelBC):
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
    Minimiser = _BindingCooperativityMinimiser
    FullDescription = f'{Info} \n {Description}\nReferences: {References}'

class FractionBindingModel(BindingModelBC):
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
    Minimiser = _FractionBindingMinimiser
    isEnabled = True

class FractionBindingWithTargetConcentrModel(BindingModelBC):
    """
    ChemicalShift Analysis: FractionBinding with Target Concentration fitting Curve calculation model
    """
    ModelName = sv.FRACTION_BINDING_WITHTARGETMODEL
    Info = 'Fit data to using the Fraction Binding model.'
    Description = sv.NIY_WARNING
    References  = sv.NIY_WARNING
    # MaTex = ''
    Minimiser = _FractionBindingWitTargetConcentMinimiser
    isEnabled = True


## Add a new Model to the list to be available throughout the program


FittingModels = [
        OneSiteBindingModel,
        TwoSiteBindingModel,
        FractionBindingModel,
        CooperativityBindingModel,
        OneSiteWithAllostericBindingModel,
        ]
