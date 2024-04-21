"""
This module contains the diffusion models  used in the Lipari-Szabo conventions:

    1) Isotropic Rotational Diffusion (Isotropic Model):
        This model assumes that the probe molecule undergoes isotropic rotational diffusion, meaning that it rotates freely and uniformly in all directions.

    2) Axial Symmetric (Axial Model):
        The probe molecule is assumed to have an axial symmetry, such as when it is aligned with a preferred axis

    3) Fully Anisotropic (Rhombic Model):
        The fully anisotropic or rhombic model is used when the probe molecule has no preferred axis of rotation, and its rotational diffusion is fully anisotropic.
"""
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
__dateModified__ = "$dateModified: 2024-04-21 16:02:31 +0100 (Sun, April 21, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

from abc import ABC
from collections import defaultdict
import numpy as np
import pandas as pd
from lmfit import Parameters, minimize, Minimizer, fit_report
from ccpn.core.lib.Cache import cached
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl
import ccpn.framework.lib.experimentAnalysis.ExperimentConstants as constants
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv

from ..RateModels import RatesHandler
from ..SpectralDensityFunctions import SDFHandler
from ..Scores import calculateChiSquared, calculateAIC

CACHEDATA       = '_cachedData'

class DiffusionModelHandler(object):
    """
    The  top object to handle the various Diffusion Models
    """

    models = {}

    @classmethod
    def register(cls, model):
        """
        Add a model to the registered models
        """
        if model.model_id not in cls.models:
            cls.models[model.model_id] = model
        else:
            raise RuntimeError('Model already registered')

    @classmethod
    def deregister(cls, model):
        """
        add a model to the registered models
        """
        if model.model_id in cls.models:
            cls.models.pop(model.model_id, None)

    def __init__(self, settingsHandler, inputsHandler, outputsHandler):
        self.settingsHandler = settingsHandler
        self.inputsHandler = inputsHandler
        self.outputsHandler = outputsHandler

        self.rateModelsHandler = RatesHandler()
        self.sdfHandler = SDFHandler(self.settingsHandler) # the spectral density functions handler.
        self.errorEstimationHandler = None
        self.activeModel = None
        self._initModelFromSettings()


    def _getSDFmodel_ids(self):
        return self.settingsHandler.spectralDensityFuncModels

    def getRatesData(self):
        return self.inputsHandler.ratesData

    def getRatesDataBySF(self):
        """get grouped by Spectrometer Frequency """
        return self.inputsHandler.getGroupedRatesDataByFrequency()

    @cached(CACHEDATA, maxItems=20000, debug=False)
    def _getSDMdict(self, spectrometerFrequency=600.05):
        """ Get the factors and constants needed during the minimisations """
        omegaH = sdl.calculateOmegaH(spectrometerFrequency, scalingFactor=1e6)
        omegaN = sdl.calculateOmegaN(spectrometerFrequency, scalingFactor=1e6)
        omegaC = sdl.calculateOmegaC(spectrometerFrequency, scalingFactor=1e6)
        gammaHN = constants.GAMMA_H / constants.GAMMA_N
        dFactor = sdl.calculate_d_factor(constants.rNH)
        cFactor = sdl.calculate_c_factor(omegaN, constants.N15_CSA)
        SDMdict = {
                   'dFactor': dFactor,
                   'cFactor': cFactor,
                   'omegaH': omegaH,
                   'omegaN': omegaN,
                    'omegaC': omegaC,
                    'gammaHN': gammaHN
                    }
        return SDMdict

    def getModelByName(self, name):
        for model_id, model in self.models.items():
            if model.name == name:
                return model

    def _initModelFromSettings(self):
        modelName = self.settingsHandler.diffusionModel

        if model := self.getModelByName(modelName):
            print(f'Starting Minimisations {model} -- {modelName}')
            self.activeModel = model(self)
        else:
            print(f'This model is not yet available -- {modelName}')

    def startMinimisation(self):

        if self.activeModel:
            # for i in range(3):
                self.activeModel.startMinimisation()


# Define a callback function to store the progress in a Pandas DataFrame
progress_data = pd.DataFrame(columns=['Iteration', 's2', 'te', 'tm','rex'])
def store_progress(params, iteration, resid,  neededRates, expRates, expErrors, constantsDict, *args, **kwargs):
    global progress_data
    s2 = params['s2'].value
    te = params['te'].value
    tm = params['tm'].value
    rex = params['rex'].value
    ratesPredicted = defaultdict(list)
    ...
    progress_data = progress_data.append(
                                            {'Iteration': iteration,
                                          's2': s2,
                                          'te': te,
                                          'tm': tm,
                                          'rex':rex,
                                            'r1':expRates[0],
                                             'r2':expRates[1],
                                             'noe': expRates[2],
                                              'r1p':ratesPredicted.get(sv.R1)[0],
                                           'r2p': ratesPredicted.get(sv.R2)[0],
                                             'noep': ratesPredicted.get(sv.HETNOE)[0]
                                             },

                                         ignore_index=True)


class LipariSzaboModel(ABC):
    name = 'generic'
    model_id = 0
    TcCount = 0  # rotational correlation time count

    def __init__(self, diffusionModelHandler, **kwargs):
        self.params = {}
        self._diffusionModelHandler = diffusionModelHandler
        self._settingsHandler = self._diffusionModelHandler.settingsHandler
        self.rateColumns = self._settingsHandler._useRates
        self.rateErrColumns = self._settingsHandler._useRateErrors

    def _validateRateColumns(self):
        """ Ensure that the requested rates from the settings are available in the given dataFrame column."""
        # TODO move this at higher level
        ratesData = self._diffusionModelHandler.getRatesData()
        for r, e in zip(self.rateColumns, self.rateErrColumns):
            if r not in ratesData.columns:
                raise ValueError(f'Cannot proceed with the minimisation. Requested calculation rate: {r} but experimental data is not found.')
            elif e not in ratesData.columns:
                raise ValueError(f'Cannot proceed with the minimisation. Requested calculation rate: {e} but experimental data is not found.')
        return True

    def _getParamValue(self, params, name):
        """
        :param params: the minimiser parameters
        :param name: the required param name
        :return: float
        """
        param = params.get(name)
        if param is None:
            return
        else:
            return param.value

    @staticmethod
    def objectiveFunction(params, sdModel, neededRates, expRates, expErrors, constantsDict):
        """
        Called by the minimiser
        :param params: minimiser Parameter object
        :param expRates: 1d array with the experimental rates by rate type, e.g.: R1 per ascending field strength ,e.g.: r1at600,  r2at600, ... r1at800, r2at800...
        :param expErrors: 1d array, same as expRates
        :param constantsDict: a dict of dict. {field:{constants}} e.g.: {600: {c_factor:float, ...}}. see above
        :return: the Xsquared value obtained between the experimental values and the theoretical values calculated by the selected model.
        """
        # calculate the predicted rates from J(omega) at new given values from the Minimiser

        paramDict = params.valuesdict()
        paramDict['ci'] = 1 # for the isotropic => testing
        paramDict['ti'] = paramDict['tm']

        ratesP = []
        for sf, consDict in constantsDict.items():
            jH = sdModel.calculate(**{**paramDict, 'w': consDict['omegaH']})
            jN =  sdModel.calculate(**{**paramDict, 'w': consDict['omegaN']})
            jHpN = sdModel.calculate(**{**paramDict, 'w': consDict['omegaH']+consDict['omegaN']})
            jHmN = sdModel.calculate(**{**paramDict, 'w': consDict['omegaH']+consDict['omegaN']})
            j0 = sdModel.calculate(**{**paramDict, 'w': 0.0})

            for rateDef in neededRates: #loop over the required rate definition, e.g.: R1, R2 etc
                if rateDef == sv.R2 and sdModel.plusRex:
                    rex = params['rex'].value
                    ratep = RatesHandler.calculate(rateDef, consDict['dFactor'], consDict['cFactor'], j0, jH, jHmN, jHpN, jN, rex=rex)
                else:
                    ratep =  RatesHandler.calculate(rateDef, consDict['dFactor'], consDict['cFactor'], j0, jH, jHmN, jHpN, jN)
                ratesP.append(ratep)
        # now concatenate the newly predicted values
        predictions = np.array(ratesP)
        # calculate score
        score = calculateChiSquared(expRates, predictions, expErrors)
        return score


    def _getConstantsDict(self):
        """
        Get the various constants field dependent based on the Rates dataFrame
        :return: {field:{'dFactor': float,  'cFactor': float,  'omegaH': float, ...  }}
        """
        ratesData = self._diffusionModelHandler.getRatesData()
        frequencies = ratesData[sv.SF].unique()
        SDMdict = {}
        for sf in frequencies:
            SDM = self._diffusionModelHandler._getSDMdict(sf)
            SDMdict[sf] = SDM
        return SDMdict

    def _getMinimiserInitialParams(self, paramsNeeded):
        """
        TODO get proper estimates from the other lib funcs
        :return:
        """
        defaults = {
            sv.S2: {'name':sv.S2.lower(), 'value':0.5, 'min':0.1, 'max':1,  'vary':True},
            sv.S2f: {'name': sv.S2f.lower(), 'value': 0.5, 'min': 0.1, 'max': 1, 'vary':True},
            sv.S2s: {'name': sv.S2s.lower(), 'value': 0.5, 'min': 0.1, 'max': 1, 'vary':True},

            sv.TE: {'name': sv.TE.lower(), 'value': 2e-11, 'min': 1e-14, 'max': 1e-10, 'vary':True},
            sv.Ts: {'name': sv.Ts.lower(), 'value': 2e-11, 'min': 1e-14, 'max': 1e-10, 'vary':True},
            sv.Tf: {'name': sv.Tf.lower(), 'value': 2e-11, 'min': 1e-14, 'max': 1e-10, 'vary':True},

            sv.REX: {'name': sv.REX.lower(), 'value': 0, 'min': -1, 'max': 1000, 'vary':True},
            sv.TM: {'name': sv.TM.lower(), 'value': 1e-8, 'min': 1e-9, 'max': 1e-8, 'vary':True},
            }
        params = Parameters()
        for need in paramsNeeded:
            default = defaults.get(need)
            params.add(**default)
        return params

    def getBestModel(self, models, minimiserResults, n):
        """ Calculate the AIC for each minimiser result and return the lowest AIC minimiserResult and the utilised model"""
        results = np.array(minimiserResults)
        models = np.array(models)
        aics = []
        for result, model in zip(results, models):
            chisqr = result.chisqr
            aic = calculateAIC(chisqr, len(model.optimisedParams), n)
            aics.append(aic)
        aics = np.array(aics)
        bestIX = np.argmin(aics)
        bestResult = results[bestIX]
        bestModel = minimiserResults[bestIX]
        return bestResult, bestModel

    def startMinimisation(self):
        sdfHandler = self._diffusionModelHandler.sdfHandler
        ratesData = self._diffusionModelHandler.getRatesData()
        constantsDict = self._getConstantsDict()
        sdfModels = self._diffusionModelHandler._getSDFmodel_ids()
        # we start by grouping by residue number
        dataGroupedByResidue = ratesData.groupby(sv.NMRRESIDUECODE)
        # we loop residue by residue
        for residueCode, residueData in dataGroupedByResidue:
            # we expect rates at multiple fields.  sort by ascending (low->high) the spectrometerFrequency value
            residueData.sort_values(by=sv.SF, inplace=True)
            # get the rates of interest
            # create a 1D array of rates at different fields. e.g.: R1s, R2s, NOEs in ascending field strength  (r1_600, r2_600, hetNoe_600,  r1_800, r2_800, hetNoe_800,  etc...)
            ratesExp = residueData[self.rateColumns].values.flatten()
            errorsExp = residueData[self.rateErrColumns].values.flatten()
            # calculate the predicted values at each field and make the same array construct as per the ExpRates.
            results = []
            usedModels = []
            for model_id in sdfModels:
                sdModel = sdfHandler.getById(model_id)
                params = self._getMinimiserInitialParams([sv.TM] + sdModel.optimisedParams)

                minimizer = Minimizer(self.objectiveFunction,
                                      params,
                                      fcn_args=(sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict),
                                      method='differential_evolution',
                                      )
                                      # iter_cb=store_progress) #this is a callback for each minimisation step sent by the minimiser

                maxfev = 10000  # Adjust this value as needed nd then get from the settings

                # Perform the optimization
                result = minimizer.minimize(method='differential_evolution', max_nfev=maxfev)
                result.model_id = model_id
                usedModels.append(sdModel)
                # Report the optimized parameters and uncertainties

                hasConverged = result.success
                if hasConverged:
                    results.append(result)

                # print(f'RUNNING {model_id}. Converged: {result.success}, {result.chisqr}')
                # for i, (name, param) in enumerate(result.params.items()):
                #     print(f'{name}: {param.value} +/- {param.stderr}')

            print('----------' * 5)
            n = len(ratesExp)
            result, bestModel = self.getBestModel(usedModels, results, n)
            print(f'RES: {residueCode} --Best Model --------{bestModel.model_id},X2s: ', [result.chisqr for result in results] )
            for i, (name, param) in enumerate(result.params.items()):
                print(f'{name}: {param.value} +/- {param.stderr}')

            print('--' * 20)
            progress_data.to_csv('fitting_progress.csv', index=False)




class IsotropicModel(LipariSzaboModel):
    name = 'Isotropic'
    model_id = 1
    TcCount = 1  # described total rotational correlation time count


class AxialSymmetricModel(LipariSzaboModel):
    name = 'Axially-Symmetric'
    model_id = 2
    TcCount = 2


class FullyAnisotropicModel(LipariSzaboModel):
    name = 'Fully-Anisotropic'
    model_id = 3
    TcCount = 3


class PartiallyAnisotropicModel(LipariSzaboModel):
    name = 'Partially-Anisotropic'
    modelEnum = 4
    TcCount = 2
    #   not sure


# ~~~~~~~~~ Register the Models ~~~~~~~~~~ #

DiffusionModelHandler.register(LipariSzaboModel)
DiffusionModelHandler.register(IsotropicModel)
# DiffusionModelHandler.register(AxialSymmetricModel)
# DiffusionModelHandler.register(FullyAnisotropicModel)
# DiffusionModelHandler.register(PartiallyAnisotropicModel)


