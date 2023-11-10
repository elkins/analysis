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
__dateModified__ = "$dateModified: 2023-11-10 16:40:19 +0000 (Fri, November 10, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.DataEnum import DataEnum
from lmfit.models import update_param_vals
import numpy as np
import pandas as pd
import ccpn.framework.lib.experimentAnalysis.fittingModels.fitFunctionsLib as lf
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl
from ccpn.framework.lib.experimentAnalysis.ExperimentConstants import N15gyromagneticRatio, HgyromagneticRatio
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.util.Logging import getLogger
from ccpn.core.DataTable import TableFrame
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC, MinimiserModel, MinimiserResult
from ccpn.framework.lib.experimentAnalysis.calculationModels.CalculationModelABC import CalculationModel
from ccpn.framework.lib.experimentAnalysis.SeriesTables import ETAOutputFrame, HetNoeOutputFrame, R2R1OutputFrame, RSDMOutputFrame

#####################################################
###########        Minimisers        ################
#####################################################

class InversionRecoveryMinimiser(MinimiserModel):
    """
    """
    MODELNAME = 'InversionRecoveryMinimiser'
    FITTING_FUNC = lf.inversionRecovery_func
    AMPLITUDEstr = sv.AMPLITUDE
    DECAYstr = sv.DECAY
    # _defaultParams must be set. They are required. Also Strings must be exactly as they are defined in the FITTING_FUNC arguments!
    # There is a clever signature inspection that set the args as class attributes. This was too hard/dangerous to change!
    defaultParams = {
                        AMPLITUDEstr:1,
                        DECAYstr:0.5
                      }

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.OMIT_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(InversionRecoveryMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**self.defaultParams)

    def guess(self, data, x, **kwargs):
        """Estimate initial model parameter values from data."""
        try:
            sval, oval = np.polyfit(x, np.log(abs(data)+1.e-15), 1)
        except TypeError:
            sval, oval = 1., np.log(abs(max(data)+1.e-9))
        params = self.make_params(amplitude=np.exp(oval), decay=-1.0/sval)
        return update_param_vals(params, self.prefix, **kwargs)


###########################################################

class OnePhaseDecayMinimiser(MinimiserModel):
    """
    """
    MODELNAME = 'OnePhaseDecayMinimiser'
    FITTING_FUNC = lf.onePhaseDecay_func
    AMPLITUDEstr = sv.AMPLITUDE
    RATEstr = sv.RATE
    # _defaultParams must be set. They are required. Also Strings must be exactly as they are defined in the FITTING_FUNC arguments!
    # There is a clever signature inspection that set the args as class attributes. This was too hard/dangerous to change!
    defaultParams = {
                        AMPLITUDEstr:1,
                        RATEstr:1.5
                      }

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.OMIT_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(OnePhaseDecayMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**self.defaultParams)

    def guess(self, data, x, **kwargs):
        """Estimate initial model parameter values from data."""
        try:
            sval, oval = np.polyfit(x, np.log(abs(data)+1.e-15), 1)
        except TypeError:
            sval, oval = 1., np.log(abs(max(data)+1.e-9))
        params = self.make_params(amplitude=np.exp(oval), rate=abs(sval))
        return update_param_vals(params, self.prefix, **kwargs)

################

class OnePhaseDecayPlateauMinimiser(MinimiserModel):
    """
    """
    MODELNAME = 'OnePhaseDecayPlateauMinimiser'
    FITTING_FUNC = lf.onePhaseDecayPlateau_func
    AMPLITUDEstr = sv.AMPLITUDE
    RATEstr = sv.RATE
    PLATEAUstr = sv.PLATEAU
    # _defaultParams must be set. They are required. Also Strings must be exactly as they are defined in the FITTING_FUNC arguments!
    # There is a clever signature inspection that set the args as class attributes. This was too hard/dangerous to change!
    defaultParams = {
                        AMPLITUDEstr:1,
                        RATEstr:1.5,
                        PLATEAUstr:0
                      }

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.OMIT_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(OnePhaseDecayPlateauMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**self.defaultParams)


    def guess(self, data, x, **kwargs):
        """Estimate initial model parameter values from data."""

        try:
            sval, oval = np.polyfit(x, np.log(abs(data)+1.e-15), 1)
        except TypeError:
            sval, oval = 1., np.log(abs(max(data)+1.e-9))

        params = self.make_params(
                amplitude=dict(value=np.exp(oval), min=max(data) / 2, max=max(data) * 2),
                rate=dict(value=abs(sval)),
                plateau=dict(value=min(data), min=None, max=min(data) * 2)
                )
        return update_param_vals(params, self.prefix, **kwargs)


class ExpDecayMinimiser(MinimiserModel):
    """
    A model to fit the time constant in a exponential decay
    """
    MODELNAME = 'ExponentialDecayMinimiser'
    FITTING_FUNC = lf.exponentialDecay_func
    AMPLITUDEstr = sv.AMPLITUDE
    DECAYstr = sv.DECAY
    # _defaultParams must be set. They are required. Also Strings must be exactly as they are defined in the FITTING_FUNC arguments!
    # There is a clever signature inspection that set the args as class attributes. This was too hard/dangerous to change!
    defaultParams = {
                        AMPLITUDEstr:1,
                        DECAYstr:0.5
                      }

    def __init__(self, independent_vars=['x'], prefix='', nan_policy=sv.OMIT_MODE, **kwargs):
        kwargs.update({'prefix': prefix, 'nan_policy': nan_policy, 'independent_vars': independent_vars})
        super().__init__(ExpDecayMinimiser.FITTING_FUNC, **kwargs)
        self.name = self.MODELNAME
        self.params = self.make_params(**self.defaultParams)

    def guess(self, data, x, **kwargs):
        """Estimate initial model parameter values from data."""
        try:
            sval, oval = np.polyfit(x, np.log(abs(data)+1.e-15), 1)
        except TypeError:
            sval, oval = 1., np.log(abs(max(data)+1.e-9))
        params = self.make_params(amplitude=np.exp(oval), decay=-1.0/sval)
        return update_param_vals(params, self.prefix, **kwargs)


class _ExponentialBaseModel(FittingModelABC):
    """
    A Base model class for multiple Exponential types
    """
    peakProperty =  sv._HEIGHT
    targetSeriesAnalyses = [sv.RelaxationAnalysis]

    def fitSeries(self, inputData:TableFrame, rescale=True, *args, **kwargs) -> TableFrame:
        """
        :param inputData:
        :param rescale:
        :param args:
        :param kwargs:
        :return:
        """
        getLogger().warning(sv.UNDER_DEVELOPMENT_WARNING)
        ## Keep only one IsotopeCode as we are using only Height/Volume
        inputData = inputData[inputData[sv.ISOTOPECODE] == inputData[sv.ISOTOPECODE].iloc[0]]
        minimisedProperty = self.PeakProperty
        if not self.ySeriesStepHeader in inputData.columns:
            inputData[self.ySeriesStepHeader] = inputData[self.PeakProperty]


        grouppedByCollectionsId = inputData.groupby([sv.COLLECTIONID])
        for collectionId, groupDf in grouppedByCollectionsId:
            groupDf.sort_values([self.xSeriesStepHeader], inplace=True)
            seriesSteps = Xs = groupDf[self.xSeriesStepHeader].values
            seriesValues = Ys = groupDf[self.ySeriesStepHeader].values
            minimiser = self.Minimiser()
            try:
                params = minimiser.guess(Ys, Xs)
                minimiser.setMethod(self._minimiserMethod)
                result = minimiser.fit(Ys, params, x=Xs)
            except:
                getLogger().warning(f'Fitting Failed for collectionId: {collectionId} data. Make sure you are using the right model for your data.')
                params = minimiser.params
                result = MinimiserResult(minimiser, params)

            for ix, row in groupDf.iterrows():
                for resultName, resulValue in result.getAllResultsAsDict().items():
                    inputData.loc[ix, resultName] = resulValue
                inputData.loc[ix, sv.MODEL_NAME] = self.modelName
                inputData.loc[ix, sv.MINIMISER_METHOD] = minimiser.method
                try:
                    nmrAtomNames = inputData._getAtomNamesFromGroupedByHeaders(groupDf)
                    inputData.loc[ix, sv.NMRATOMNAMES] = nmrAtomNames[0] if len(nmrAtomNames) > 0 else ''
                except:
                    inputData.loc[ix, sv.NMRATOMNAMES] = ''

        return inputData


class OnePhaseDecayModel(_ExponentialBaseModel):
    """
    FittingModel model class containing fitting equation and fitting information
    """
    modelName   = sv.OnePhaseDecay
    modelInfo        = '''A model to describe the rate of a decay.  '''
    description = '''Model:\nY=amplitude*exp(-rate*X)      
                 X:the various times values
                 amplitude: the Y value when X (time) is zero. Same units as Y
                 rate: the rate constant, expressed in reciprocal of the X axis time units,  e.g.: Second-1.
                  '''
    references  = '''
                  '''
    Minimiser = OnePhaseDecayMinimiser
    

    @property
    def _preferredYPlotArgName(self):
        """  Private only used in UI mode."""

        return self.Minimiser.RATEstr

class OnePhaseDecayPlateauModel(_ExponentialBaseModel):
    """
    FittingModel model class containing fitting equation and fitting information
    """
    modelName   = sv.OnePhaseDecayWithPlateau
    modelInfo        = '''A model to describe the rate of a decay.  '''
    description = '''Model:\nY=(amplitude - plateau) *exp(-rate*X) + plateau     
                 X:the various times values
                 amplitude: the Y value when X (time) is zero. Same units as Y
                 rate: the rate constant, expressed in reciprocal of the X axis time units,  e.g.: Second-1
                 plateau: the Y value at infinite times. Same units as Y.
                  '''
    references  = '''
                  '''
    Minimiser = OnePhaseDecayPlateauMinimiser
    

    @property
    def _preferredYPlotArgName(self):
        """  Private only used in UI mode."""

        return self.Minimiser.RATEstr


class ExponentialDecayModel(_ExponentialBaseModel):
    """
    FittingModel model class containing fitting equation and fitting information
    """
    modelName = sv.ExponentialDecay
    modelInfo = '''A model to describe the time constant of a decay (also known as Tau). '''
    description = '''Model:\nY=amplitude*exp(-X / decay)

                 X:the various times values
                 amplitude: the Y value when X (time) is zero. Same units as Y
                 decay: the time constant (Tau), same units as  X axis e.g.: Second.
                  '''
    references = '''
                  '''
    Minimiser = ExpDecayMinimiser
    

    @property
    def _preferredYPlotArgName(self):
        """  Private only used in UI mode."""

        return self.Minimiser.DECAYstr

class InversionRecoveryModel(_ExponentialBaseModel):
    """
    InversionRecovery model class containing fitting equation and fitting information
    """
    modelName = sv.InversionRecovery
    modelInfo = '''Inversion Recovery fitting model. '''
    description = '''Model:\nY = amplitude * (1 - e^{-time/decay})
    
                 X:the various times values
                 amplitude: the Y value when X (time) is zero. Same units as Y
                 decay: the time constant, same units as  X axis.
                  '''
    references = '''
                  '''
    Minimiser = InversionRecoveryMinimiser
    # MaTex =  r'$amplitude*(1 - e^{-time/decay})$'
    

    @property
    def _preferredYPlotArgName(self):
        """  Private only used in UI mode."""
        return self.Minimiser.DECAYstr



