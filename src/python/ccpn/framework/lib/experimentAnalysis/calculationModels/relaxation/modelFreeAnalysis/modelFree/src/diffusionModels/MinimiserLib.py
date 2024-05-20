#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-05-20 09:41:34 +0100 (Mon, May 20, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"

#=========================================================================================
# Start of code
#=========================================================================================

from lmfit import Parameters
from ccpn.framework.lib.experimentAnalysis import SeriesAnalysisVariables as sv
from ccpn.util.DataEnum import DataEnum


class MinimiserSettingsPreset(DataEnum):

    """
    A set of options in predefined presets.
    DataEnum described as: name, value, description, dataValue = dict of preset values

    These settings are specific for a Differential Evolution minimisation algorithm.

    'ftol': specifies the tolerance for convergence based on the relative change in the objective function value.  ftol determines how much the objective function value must change
            between iterations before the optimisation process considers the solution to have converged.
            A lower ftol value indicates that a smaller change in the objective function value is required for convergence,
            leading to higher precision but potentially requiring more iterations for convergence.
            Example values:  1e-4 for low accuracy;  use 1e-8 for high accuracy, provides a good balance between precision and computational efficiency.

    'xtol': specifies the tolerance for convergence based on the relative change in the parameter values.  In short, xtol determines how much the parameter
            values must change between iterations before the optimisation process considers the solution to have converged.
            A lower xtol value indicates that a smaller change in the parameter values is required for convergence,
            leading to higher precision but potentially requiring more iterations for convergence.

    'max_nfev':  short for "maximum number of function evaluations," specifies the maximum number of times the objective function
                    is evaluated during the optimisation process.

    'popsize': determines the population size, i.e., the number of candidate solutions (individuals) in each generation of the optimisation process.
                   the algorithm maintains a population of candidate solutions (individuals), where each individual represents a possible solution to the optimisation problem.
                   These individuals are evolved over successive generations through mutation, crossover, and selection operations. A larger population size can sometimes lead to better
                   exploration of the search space and may help to find better solutions, but it also increases the computational cost of each generation.


    """
    LOW_ACCURACY = 0, 'low', {
        'ftol'    : 1e-5,
        'xtol'    : 1e-5,
        'gtol'    : 1e-5,
        'max_nfev': int(1e4), # make it at least 10'000
        'popsize' : 20,
        'workers' : 1
        }

    MEDIUM_ACCURACY = 1, 'medium', {
        'ftol'    : 1e-7,
        'xtol'    : 1e-7,
        'gtol'    : 1e-7,
        'max_nfev': int(1e6),
        'popsize' : 50,
        'workers' : 1
        }

    HIGH_ACCURACY = 2, 'high', {
        'ftol'    : 1e-9,
        'xtol'    : 1e-9,
        'gtol'    : 1e-9,
        'max_nfev': int(1e9),
        'popsize' : 100,
        'workers' : 1
        }

    MULTI_PROCESS = -1, 'multi_process', {
        'ftol'    : 1e-8,
        'xtol'    : 1e-8,
        'gtol'    : 1e-8,
        'max_nfev': 1e9,
        'popsize' : 1e2,
        'workers' : -1 #-1 to set the multiprocess
        }
    @staticmethod
    def getPreset(key):
        """
        :param key: string or int, one of 'low_accuracy', 'medium_accuracy', 'high_accuracy' or 0-2
        :return: dict of preset values
        """
        if isinstance(key, str):
            if key.islower():
                available = MinimiserSettingsPreset.descriptions()
                if key in available:
                    index = available.index(key)
                    return MinimiserSettingsPreset.dataValues()[index]
                else:
                    raise ValueError(f'Invalid key. Use one of {available}.')
        if isinstance(key, int):
            available = MinimiserSettingsPreset.descriptions()
            if key < len(available):
                return MinimiserSettingsPreset.dataValues()[key]
            else:
                raise ValueError(f'Invalid key. Use one of between 0-{len(available)}.')
        else:
            raise ValueError("Invalid key type. Use string or integer.")


class _DefaultParameters(Parameters):
    """
    A class to contain all the default minimisation parameters that are needed during the various models.
    Note, this is a container only, not all parameters are need at each minimisation.
    """

    def __init__(self, TiCount=1, varyCi=False,  *args, **kwargs):
        super().__init__(*args, **kwargs)

        # S2
        self.add(name=sv.S2, value=0.5, min=0.01, max=1, vary=True)
        self.add(name=sv.S2f, value=0.5, min=0.01, max=0.9, vary=True)
        self.add(name=sv.S2s, value=0.5, min=0.01, max=0.9, vary=True)

        # Ti add the Ti based on the diffusion model
        for i in range(1, TiCount+1):
            self.add(name=f'{sv.Ti}_{i}', value=1e-8, min=1e-9, max=1e-8, vary=True)
            # Ci
            self.add(name=f'{sv.Ci}_{i}', value=1, min=.99, max=1.01, vary=varyCi)

        # Te
        self.add(name=sv.TE, value=2e-11, min=1e-14, max=1e-10, vary=True)
        self.add(name=sv.Ts, value=2e-11, min=1e-14, max=1e-10, vary=True)
        self.add(name=sv.Tf, value=2e-11, min=1e-14, max=1e-10, vary=True)

        # Rex
        self.add(name=sv.REX, value=0, min=-1, max=1e3, vary=True)

    @property
    def asDict(self):
        return self.valuesdict()

    @property
    def names(self):
        return list(self.asDict)

    @property
    def asEmptyDict(self):
        """
        Get the
        :return: params as dict with all keys containing None values.
        """
        return {key: None for key in self.asDict}

    def getNewParamsByNames(self, paramsNeeded:list):
        """
        :return: a new Parameters instance with only the needed arguments needed
        """
        params = Parameters()
        for need in paramsNeeded:
            default = self.get(need)
            params.add(default)
        return params

    @staticmethod
    def extractLocalParams(params, residueCode):
        localParams = Parameters()
        for name, param in params.items():
            if f'_{residueCode}' in name:
                _name = name.split(f'_{residueCode}')[0]
                localParams.add(_name, value=param.value, min=param.min, max=param.max, vary=param.vary)
        return localParams

