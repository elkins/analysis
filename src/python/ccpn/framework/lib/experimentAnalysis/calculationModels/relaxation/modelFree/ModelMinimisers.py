"""
A module containing a Minimiser for each model function.

"""

import numpy as np
from ccpn.util.DataEnum import DataEnum
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import ccpn.framework.lib.experimentAnalysis.ExperimentConstants as constants
from ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.modelFree.modelFuncs import (_calculateJwModel0,
                                                                                                     _calculateJwModel1,
                                                                                                     _calculateJwModel2,
                                                                                                     _calculateJwModel3,
                                                                                                     _calculateJwModel4)
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC, MinimiserModel, MinimiserResult
from lmfit import Parameters



class _JWModelBC(MinimiserModel):
    """ See modelFuncs.py for the full documentation."""
    FITTING_FUNC = None #TODO
    MODEL_FUNC = _calculateJwModel0

    ti = sv.Ti
    ci = sv.Ci
    w = sv.W
    s2 = sv.S2
    te = sv.TE
    rex = sv.REX

    defaultParams = {
                                ti: {'value': 1.0, 'min': 0.0, 'max': 10.0},
                                ci: {'value': 1.0, 'min': 0.0, 'max': 10.0},
                                w: {'value': 1.0, 'min': 1.0, 'max': 10.0},
                                s2: {'value': .7, 'min': 0.0, 'max': 1.0},
                                te: {'value': 1.0, 'min': 1.0, 'max': 10.0},
                                rex: {'value': 1.0, 'min': 1.0, 'max': 10.0},
                                }

    def __init__(self, **kwargs):
        super().__init__(self.FITTING_FUNC, method='differential_evolution', **kwargs)
        self.name = self.MODELNAME
        self.params = self.makeParams(self.defaultParams)
        # self.func = self.FITTING_FUNC

    def makeParams(self, paramDict):
        """Make params from a dict containing for each argument the value, min and max."""
        params = Parameters()
        for name, valueDict in paramDict.items():
            params.add(name, value=valueDict['value'], min=valueDict['min'], max=valueDict['max'])
        return params



class _JWModel1(_JWModelBC):
    MODEL_FUNC = _calculateJwModel1

class _JWModel2(_JWModelBC):
    MODEL_FUNC = _calculateJwModel2

class _JWModel3(_JWModelBC):
    MODEL_FUNC = _calculateJwModel3

class _JWModel4(_JWModelBC):
    MODEL_FUNC = _calculateJwModel4


