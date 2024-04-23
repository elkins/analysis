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
__dateModified__ = "$dateModified: 2024-04-23 12:58:39 +0100 (Tue, April 23, 2024) $"
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
from collections import OrderedDict
from lmfit import Parameters, minimize, Minimizer, fit_report
from ccpn.core.lib.Cache import cached
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl
import ccpn.framework.lib.experimentAnalysis.ExperimentConstants as constants
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from datetime import datetime

from ..RateModels import RatesHandler
from ..SpectralDensityFunctions import SDFHandler
from ..Scores import calculateChiSquared, calculateAIC
from ..io.Outputs import getOutputDir

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
progress_data = pd.DataFrame(columns=['Iteration', sv.S2, sv.TE, sv.TM,sv.REX])
def store_progress(params, iteration, resid,  neededRates, expRates, expErrors, constantsDict, *args, **kwargs):
    global progress_data
    s2 = params[sv.S2].value
    te = params[sv.TE].value
    tm = params[sv.TM].value
    rex = params[sv.REX].value
    ratesPredicted = defaultdict(list)
    ...
    progress_data = progress_data.append(
                                            {'Iteration': iteration,
                                          sv.S2: s2,
                                          sv.TE: te,
                                          sv.TM: tm,
                                          sv.REX:rex,
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
        self.maxfev =  self._settingsHandler.maxfev
        self._storeMinimiserProgress = False # store each evaluation result in a separate file. (use only for testing)

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
    def _calculateRatesFromParams(params, sdModel, neededRates, constantsDict):
        # calculate the predicted rates from J(omega) at new given values from the Minimiser
        paramDict = params.valuesdict()
        paramDict[sv.Ci] = 1  # for the isotropic => testing
        paramDict[sv.Ti] = paramDict[sv.TM]
        ratesP = []
        for sf, consDict in constantsDict.items():
            jH = sdModel.calculate(**{**paramDict, sv.W: consDict['omegaH']})
            jN = sdModel.calculate(**{**paramDict, sv.W: consDict['omegaN']})
            jHpN = sdModel.calculate(**{**paramDict, sv.W: consDict['omegaH'] + consDict['omegaN']})
            jHmN = sdModel.calculate(**{**paramDict, sv.W: consDict['omegaH'] + consDict['omegaN']})
            j0 = sdModel.calculate(**{**paramDict, sv.W: 0.0})
            for rateDef in neededRates:  #loop over the required rate definition, e.g.: R1, R2 etc
                if rateDef == sv.R2 and sdModel.plusRex:
                    rex = params[sv.REX].value
                    ratep = RatesHandler.calculate(rateDef, consDict['dFactor'], consDict['cFactor'], j0, jH, jHmN, jHpN, jN, rex=rex)
                else:
                    ratep = RatesHandler.calculate(rateDef, consDict['dFactor'], consDict['cFactor'], j0, jH, jHmN, jHpN, jN)
                ratesP.append(ratep)
        # now concatenate the newly predicted values
        return np.array(ratesP)

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
        calc = LipariSzaboModel._calculateRatesFromParams
        predictions = calc(params, sdModel, neededRates, constantsDict)
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

    def _getDefaultParamsDict(self) -> dict:
        """
        TODO get proper estimates from the other lib funcs. Could make as traits class
        :return:  dict with the default params as a dict
        """
        defaults = OrderedDict((
            (sv.S2, {'name': sv.S2, 'value': 0.5, 'min': 0.1, 'max': 1, 'vary': True, 'multiplier':1}),
            ( sv.S2f, {'name': sv.S2f, 'value': 0.5, 'min': 0.1, 'max': 1, 'vary': True, 'multiplier':1}),
            ( sv.S2s, {'name': sv.S2s, 'value': 0.5, 'min': 0.1, 'max': 1, 'vary': True, 'multiplier':1}),

            ( sv.TE , {'name': sv.TE, 'value': 2e-11, 'min': 1e-14, 'max': 1e-10, 'vary': True, 'multiplier':1e12}),
            ( sv.Ts , {'name': sv.Ts, 'value': 2e-11, 'min': 1e-14, 'max': 1e-10, 'vary': True,  'multiplier':1e12}),
            (sv.Tf , {'name': sv.Tf, 'value': 2e-11, 'min': 1e-14, 'max': 1e-10, 'vary': True,  'multiplier':1e12}),

            ( sv.REX, {'name': sv.REX, 'value': 0, 'min': -1, 'max': 1000, 'vary': True,  'multiplier':1}),
            ( sv.TM , {'name': sv.TM, 'value': 1e-8, 'min': 1e-9, 'max': 1e-8, 'vary': True,  'multiplier':1e9}),
            ))
        return defaults

    def _getParamDictMapping(self):
        _dict = self._getDefaultParamsDict()
        return {_dict[i]['name']:i for i in _dict}

    def _getMinimiserInitialParams(self, paramsNeeded):
        """
        :return:
        """
        params = Parameters()
        for need in paramsNeeded:
            default = self._getDefaultParamsDict().get(need)
            default.pop('multiplier', None)
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

        return bestResult

    def _minimiseResidue(self, residueData, tmValue=None, varyTm=True):
        """Minimise the optimisation params based on the setting models for a residue.
         :param: ResidueData: pandas dataFrame for one residue at single/ multiple field rates
         """
        sdfHandler = self._diffusionModelHandler.sdfHandler
        constantsDict = self._getConstantsDict()
        sdfModels = self._diffusionModelHandler._getSDFmodel_ids()
        # we expect rates at multiple fields.  sort by ascending (low->high) the spectrometerFrequency value
        residueData.sort_values(by=sv.SF, inplace=True)
        # create a 1D array of rates at different fields. e.g.: R1s, R2s, NOEs in ascending field strength  (r1_600, r2_600, hetNoe_600,  r1_800, r2_800, hetNoe_800,  etc...)
        ratesExp = residueData[self.rateColumns].values.flatten()
        errorsExp = residueData[self.rateErrColumns].values.flatten()
        # calculate the predicted values at each field and make the same array construct as per the ExpRates.
        results = []
        usedModels = []
        for model_id in sdfModels:
            sdModel = sdfHandler.getById(model_id)
            params = self._getMinimiserInitialParams([sv.TM] + sdModel.optimisedParams)
            if tmValue:
                params[sv.TM].set(value=tmValue, vary=varyTm)
            print('Calculating with Params ===> ',params)
            if self._storeMinimiserProgress:
                minimizer = Minimizer(self.objectiveFunction, params, fcn_args=(sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict),
                                      method='differential_evolution', iter_cb=store_progress)  #this is a callback for each minimisation step sent by the minimiser
            else:
                minimizer = Minimizer(self.objectiveFunction, params, fcn_args=(sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict), method='differential_evolution', )

            # Perform the optimisation
            result = minimizer.minimize(method='differential_evolution', max_nfev=self.maxfev)
            result.model_id = model_id
            usedModels.append(sdModel)
            # Report the optimized parameters and uncertainties
            hasConverged = result.success
            if hasConverged:
                results.append(result)
        n = len(ratesExp)
        bestMinimiserResult = self.getBestModel(usedModels, results, n)
        return bestMinimiserResult
        
    def startMinimisation(self):
        ratesData = self._diffusionModelHandler.getRatesData()
        resultRows = []
        dataGroupedByResidue = ratesData.groupby(sv.NMRRESIDUECODE)
        # we loop residue by residue and we do the first optimisation with Tm variable
        for residueCode, residueData in dataGroupedByResidue:
            minimiserResult = self._minimiseResidue(residueData)
            print(f'RES: {residueCode} --Best Model --------{minimiserResult.model_id}')
            _rowRes =  {key: None for key in self._getDefaultParamsDict()}
            for i, (paramName, param) in enumerate(minimiserResult.params.items()):
                print(f'{paramName}: {param.value} +/- {param.stderr}')
                _rowRes[sv.NMRRESIDUECODE] = residueCode
                _rowRes[paramName] = param.value
                _rowRes['model_id'] = minimiserResult.model_id
                _rowRes[sv.CHISQR] = minimiserResult.chisqr
            resultRows.append(_rowRes)

            # progress_data.to_csv('fitting_progress.csv', index=False)
        _result = pd.DataFrame(resultRows)
        ##  Get the median or mean TM and re optimised tith Tm fixed
        outputdir = getOutputDir()
        now = datetime.now()
        formatted_time = now.strftime("%H-%M_%d-%m-%y")
        _result.to_csv(f'{outputdir}/fitting_result_TM_fixed_{formatted_time}.csv')
        tm = _result[sv.TM].median()

        resultRows = []
        for residueCode, residueData in dataGroupedByResidue:
            minimiserResult = self._minimiseResidue(residueData, tmValue=tm, varyTm=False)
            print(f'RES: {residueCode} --Best Model --------{minimiserResult.model_id}')
            _rowRes = {key: None for key in self._getDefaultParamsDict()}
            for i, (paramName, param) in enumerate(minimiserResult.params.items()):
                print(f'{paramName}: {param.value} +/- {param.stderr}')
                _rowRes[sv.NMRRESIDUECODE] = residueCode
                _rowRes[paramName] = param.value
                _rowRes['model_id'] = minimiserResult.model_id
                _rowRes[sv.CHISQR] = minimiserResult.chisqr
            # show the original rates
            residueData.sort_values(by=sv.SF, inplace=True)
            ratesExp = residueData[self.rateColumns].values.flatten()
            errorsExp = residueData[self.rateErrColumns].values.flatten()
            calc = LipariSzaboModel._calculateRatesFromParams
            sdModel = self._diffusionModelHandler.sdfHandler.getById(minimiserResult.model_id)
            predictions = calc(minimiserResult.params, sdModel, neededRates=self.rateColumns, constantsDict=self._getConstantsDict())
            _rowRes['rates'] = ratesExp
            _rowRes['errorsExp'] = errorsExp
            _rowRes['predictions'] = predictions
            resultRows.append(_rowRes)

        _result = pd.DataFrame(resultRows)
        _result.to_csv(f'{outputdir}/fitting_result_TM_vary_{formatted_time}.csv')

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


