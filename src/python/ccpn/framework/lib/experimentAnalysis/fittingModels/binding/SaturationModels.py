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
__dateModified__ = "$dateModified: 2024-08-23 16:13:41 +0100 (Fri, August 23, 2024) $"
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


def fractionBound_func(x, Kd, BMax):
    """
    The one-site fractionBound equation for a saturation binding experiment.
    V2 equation.
    Y = BMax * (Kd + x - sqrt((Kd + x)^2 - 4x))


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


def fractionBoundWithFixedTargetConcentration(x, Kd, BMax, T):
    """
    The one-site fractionBound equation for a saturation binding experiment with a Fixed Target Concentration.
     Note, the parameter T doesn't vary during minimisation.
    V2 equation.
    Y = BMax * ((T + x + Kd) - sqrt(T + x + Kd)^2 - 4*T*x) / 2 * T

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


def fractionBoundWithVariableProteinConcentration(x, Xs, Kd, BMax, T):

    """
    The one-site fractionBound equation for a saturation binding experiment with a variable Target Concentration. Note the similarity with the fractionBoundWithFixedTargetConcentration
        totT = T * (1 - (x / Xs))
        Y = BMax*(((totT + x + Kd) - np.sqrt((totT + x + Kd)**2 - (4 * totT * x))) / (2 * totT))

    :param x: The ligand concentration.
    :param Xs: The ligand stock concentration.
    :param Kd: The dissociation constant.
    :param BMax: he maximum observed chemical shift.
    :param P0: The initial protein concentration.
    :return:  Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
                When plotting BMax is the Y axis, Kd the X axis.
    """
    totT = T * (1 - (x / Xs))
    Y = BMax*(((totT + x + Kd) - np.sqrt((totT + x + Kd)**2 - (4 * totT * x))) / (2 * totT))
    
    return Y

def monomerDimerBinding_v2(x, BMax, Kd, C):
    """
    Calculate the observed shift y based on the given parameters using the provided equation.

    Equation:
    y = A * ((B + 4x - sqrt((B + 4x)^2 - 16x^2)) / (4x)) + C


    :param x:  1d array. The data to be fitted, representing the concentration of the ligand.
               For example, x could be an array of total monomer concentrations [A]_T.
    :param BMax:  Scaling factor for the shift.
               It could represent Δδ_max, the maximum chemical shift difference.
    :param Kd:  Parameter related to the dissociation constant (Kd).
               B could represent the dissociation constant itself.
    :param C:  Baseline shift.
               It could represent δ_A, the chemical shift of the monomer.
    :return:   y array of the same shape as x. Represents the points for the fitted curve y to be plotted.
               When plotting, y is the Y axis, and x is the X axis.
    """

    sqrt_term = np.sqrt((Kd + 4 * x)**2 - 16 * x**2)
    y = BMax * ((Kd + 4*x - sqrt_term) / (4 * x)) + C
    return y


def monomerDimerBinding(x, Kd, BMax, dA):
    """
    Calculate the observed chemical shift (δ_obs) for a dimerisation binding model.
    This is yet another way of representing 'monomerDimerBinding_v2'
    or   y = A * ((B + 4x - sqrt((B + 4x)^2 - 16x^2)) / (4x)) + C

    Equation:
    δ_obs = δ_A + (Δδ_max / (2 * x)) * (Kd + 4 * x - sqrt((Kd + 4 * x)^2 - 16 * x^2))

    :param x:  1d array. Total concentration of the monomer [A]_T.
                 In a titration experiment, this is the array of ligand concentrations.
    :param Kd:   Defines the equilibrium dissociation constant. The value at which half of the monomer is dimerized.
                 The initial value might be guessed from the binding affinity.
    :param BMax: Defines the maximum possible chemical shift difference (Δδ_max).
                      Represents the shift difference between the monomer and the dimer.
    :param dA: delta_A, Defines the chemical shift of the monomer (δ_A).
                    The shift when no dimerization occurs.
    :return:    δ_obs array of the same shape as x. Represents the observed chemical shifts for each [A]_T.
                When plotting, δ_obs is the Y axis, [A]_T is the X axis.
    """

    sqrt_term = np.sqrt((Kd + 4 * x)**2 - 16 * x**2)
    delta_obs = dA + (BMax / (4 * x)) * (Kd + 4 * x - sqrt_term)

    return delta_obs

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
    _defaultGlobalParams = [KD]

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
    _defaultGlobalParams = [KD]

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
    _defaultGlobalParams = [KD]

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

class _FractionBindingWithFixedTargetConcentMinimiser(MinimiserModel):
    """A model based on the fraction bound Fitting equation.
      Eq. 6 from  M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).
    """
    FITTING_FUNC = fractionBoundWithFixedTargetConcentration
    KD = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAX = sv.BMAX
    Tstr = sv.T

    defaultParams = {KD:1,
                     BMAX:0.5,
                     Tstr:1}
    _defaultGlobalParams = [KD]
    _fixedParams = [Tstr]


    def __init__(self, **kwargs):
        super().__init__(_FractionBindingWithFixedTargetConcentMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**_FractionBindingWithFixedTargetConcentMinimiser.defaultParams)

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

class _FractionBindingWithVariableTargetConcentMinimiser(MinimiserModel):
    """A model based on the fraction bound Fitting equation at variable Target concentration.
    """
    FITTING_FUNC = fractionBoundWithVariableProteinConcentration
    KD = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAX = sv.BMAX
    Xs = 'xs' # ligand stock
    Tstr = sv.T

    defaultParams = {KD:1,
                                 Xs:10,
                                 BMAX:0.5,
                                 Tstr:1}

    _defaultGlobalParams = [KD]
    _fixedParams = [Tstr, Xs]


    def __init__(self, **kwargs):
        super().__init__(_FractionBindingWithVariableTargetConcentMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**_FractionBindingWithVariableTargetConcentMinimiser.defaultParams)

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


class _MonomerDimerMinimiser(MinimiserModel):
    """
    """
    FITTING_FUNC = monomerDimerBinding_v2
    KD = sv.KD # They must be exactly as they are defined in the FITTING_FUNC arguments! This was too hard to change!
    BMAX = sv.BMAX
    C = sv.C

    defaultParams = {KD:1,
                     BMAX:0.5,
                     C:0.1}
    _defaultGlobalParams = [KD]
    _fixedParams = []

    def __init__(self, **kwargs):
        super().__init__(_MonomerDimerMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**_MonomerDimerMinimiser.defaultParams)

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
        params.get(self.C).value = np.min(data)
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

    def _setGlobalTargetConcentrationToParams(self, df, params):
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



class FractionBindingModel(BindingModelBC):
    """
    ChemicalShift Analysis: FractionBinding fitting Curve calculation model
    """
    modelName = sv.FRACTION_BINDING_MODEL
    modelInfo = 'Fit data to using the simple Fraction Binding model.'
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

class FractionBindingWithFixedTargetConcentrModel(BindingModelBC):
    """
    ChemicalShift Analysis: FractionBinding with Target Concentration fitting Curve calculation model
    """
    modelName = sv.FRACTION_BINDING_WITH_FIXED_TARGET_MODEL
    modelInfo = 'Fit data to using the Fraction Binding model.'
    description = '''Fitting model that implements the 'exact binding' model for a one-site saturation binding experiment with a global fixed target concentration. 
                            \nModel:
                            Y = BMax * ((T + x + Kd) - sqrt(T + x + Kd)^2 - 4*T*x) / 2 * T
                            Bmax: is the maximum specific binding and in the CSM is given by the Relative displacement (Deltas among chemicalShifts).
                            Kd: is the (equilibrium) dissociation constant in the same unit as the Series.
                            The Kd represents the [ligand] required to get a half-maximum binding at equilibrium.
                            T: Target concentration. (Value is kept fixed during the minimisation)

    '''
    references  = '1) Eq. 6 from M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).'
    # MaTex = ''
    Minimiser = _FractionBindingWithFixedTargetConcentMinimiser
    isEnabled = True
    targetSeriesAnalyses = [
                                            sv.ChemicalShiftMappingAnalysis
                                            ]


    def _preFittingAdditionalParamsSettings(self, df, params, **kwargs):
        """called before running the fitting routine to set any additional params options. To be subclasses"""
        return self._setGlobalTargetConcentrationToParams(df, params)


class FractionBindingWithVariableTargetConcentrationModel(BindingModelBC):
    """
    ChemicalShift Analysis: FractionBinding with Target Concentration fitting Curve calculation model
    """
    modelName = sv.FRACTION_BINDING_WITH_VARIABLE_TARGET_MODEL
    modelInfo = 'Fit data to using the Exact Fraction Binding model.'
    description = ''' This model describes a one-site saturation binding experiment where the concentration of the target (protein) varies as the ligand is added. 
                            \nModel:
                                Y = BMax*(((totT + x + Kd) - np.sqrt((totT + x + Kd)**2 - (4 * totT * x))) / (2 * totT))
                            
                            totT = T * (1 - (x / Xs))
                            Bmax: is the maximum specific binding and in the CSM is given by the Relative displacement (Deltas among chemicalShifts).
                            Kd: is the (equilibrium) dissociation constant in the same unit as the Series.
                            The Kd represents the [ligand] required to get a half-maximum binding at equilibrium.
                            T: Target concentration. (Fixed value during the minimisation)
                            Xs: ligand stock solution concentration. 
    '''
    references  = '1) Eq. 6 from M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).'
    # MaTex = ''
    Minimiser = _FractionBindingWithVariableTargetConcentMinimiser
    isEnabled = True
    targetSeriesAnalyses = [
                                            sv.ChemicalShiftMappingAnalysis
                                            ]


    def _preFittingAdditionalParamsSettings(self, df, params, **kwargs):
        """called before running the fitting routine to set any additional params options. To be subclasses"""

        return self._setGlobalTargetConcentrationToParams(df, params)


class MonomerDimerBindingModel(BindingModelBC):
    """
    ChemicalShift Analysis: Monomer-Dimer  fitting Curve calculation model
    """
    modelName = sv.MONOMERDIMER_BINDING_MODEL
    modelInfo = 'Fit data to using the Monomer-Dimer model.'
    description = '''Fitting model for one-site fraction bound in a saturation binding experiment. This model can be used when a large fraction of the ligand binds to the target.
                    \nModel:
                    Y = A * ((B + 4x - sqrt((B + 4x)^2 - 16x^2)) / (4x) ) + C
                    or 
                    Y = BMax * ( (Kd + 4x - sqrt((Kd + 4x)^2 - 16x^2)) / (4x) ) + C

                    Bmax: is the maximum specific binding and in the CSM is given by the Relative displacement (Deltas among chemicalShifts).
                    Kd: is the (equilibrium) dissociation constant in the same unit as the Series.
                    The Kd represents the [ligand] required to get a half-maximum binding at equilibrium.
                    C:  the chemical shift of the monomer (δA)
                  '''
    references = ''

    Minimiser = _MonomerDimerMinimiser
    isEnabled = True
    targetSeriesAnalyses = [
        sv.ChemicalShiftMappingAnalysis
        ]


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

## ~~~~~~~~~~~~~ Disabled models ~~~~~~~~~~~~~ ##


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
    isEnabled = False


class TwoSiteBindingModel(BindingModelBC):
    """
    ChemicalShift Analysis: Two Site-Binding Curve calculation model
    """
    modelName = sv.TWO_BINDING_SITE_MODEL
    modelInfo = 'Fit data to using the Two-Binding-Site model.'
    description = sv.NIY_WARNING
    references = sv.NIY_WARNING
    # MaTex = r''
    Minimiser = _Binding2SiteMinimiser

    isEnabled = False
    targetSeriesAnalyses = [
        sv.ChemicalShiftMappingAnalysis
        ]

    def fitSeries(self, inputData: TableFrame, rescale=True, *args, **kwargs) -> TableFrame:
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
    references = sv.NIY_WARNING
    # References = '''
    #                 1) A. Christopoulos and T. Kenakin, Pharmacol Rev, 54: 323-374, 2002.
    #               '''
    # MaTex = r''
    Minimiser = _Binding1SiteAllostericMinimiser

    isEnabled = False
    targetSeriesAnalyses = [
        sv.ChemicalShiftMappingAnalysis
        ]

    def fitSeries(self, inputData: TableFrame, rescale=True, *args, **kwargs) -> TableFrame:
        """
        :param inputData:
        :param rescale:
        :param args:
        :param kwargs:
        :return:
        """
        raise RuntimeError(sv.FMNOYERROR)
