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
__dateModified__ = "$dateModified: 2023-11-13 10:25:55 +0000 (Mon, November 13, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from lmfit.models import update_param_vals
import numpy as np
from ccpn.framework.lib.experimentAnalysis.fittingModels.relaxation.ExponentialDecayModels import _ExponentialBaseModel
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import MinimiserModel

## ----------       Lineshape Functions       ---------- ##

def exponentialGrowth_func(x, amplitude, decay):
    return amplitude * np.exp(decay * x)

## ----------       Minimisers       ---------- ##

class _ExponentialGrowthMinimiser(MinimiserModel):
    """
    """
    MODELNAME = 'InversionRecoveryMinimiser'
    FITTING_FUNC = exponentialGrowth_func
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
        super().__init__(_ExponentialGrowthMinimiser.FITTING_FUNC, **kwargs)
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

class _OnePhaseAssociationMinimiser(MinimiserModel):
    """
    """
    MODELNAME = 'OnePhaseAssociation'

class _TwoPhaseAssociationMinimiser(MinimiserModel):
    """
    """
    MODELNAME = 'TwoPhaseAssociation'

class _PlateauOnePhaseAssociationMinimiser(MinimiserModel):
    """
    """
    MODELNAME = 'PlateauOnePhaseAssociation'

## ------------- Exponential Growth Models --------------- ##

class  ExponentialGrowthModel(_ExponentialBaseModel):
    """
    InversionRecovery model class containing fitting equation and fitting information
    """
    modelName = sv.InversionRecovery
    modelInfo = '''Exponential Growth Model fitting model. '''
    description = '''
                  '''
    references = '''
                  '''
    Minimiser = _ExponentialGrowthMinimiser
    # MaTex =  r'$amplitude*(1 - e^{-time/decay})$'
    





