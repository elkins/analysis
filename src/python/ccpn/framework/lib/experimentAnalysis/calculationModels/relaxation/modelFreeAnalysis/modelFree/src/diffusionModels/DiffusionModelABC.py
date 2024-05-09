"""
This module contains the diffusion models  used in the Lipari-Szabo conventions:

    1) Isotropic Rotational Diffusion (Isotropic Model):
        This model assumes that the probe molecule undergoes isotropic rotational diffusion, meaning that it rotates freely and uniformly in all directions.

    2) Axial Symmetric (Axial Model):
        The probe molecule is assumed to have an axial symmetry, such as when it is aligned with a preferred axis

    3) Fully Anisotropic (Rhombic Model):
        The fully anisotropic or rhombic model is used when the probe molecule has no preferred axis of rotation, and its rotational diffusion is fully anisotropic.


    Minimiser settings:

    Methods: differential evolution (DE). https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html#scipy.optimize.differential_evolution
    Convergence criteria:
        ftol (Function Tolerance): The relative tolerance for convergence of the cost function. The optimisation process stops when the relative reduction in the cost function is less than ftol.
        xtol (Parameter Tolerance): The relative tolerance for convergence of the parameters. The optimisation process stops when the relative change in the parameters is less than xtol.
        maxiter (Maximum Iterations): The maximum number of iterations allowed during optimisation. Increasing maxiter allows the optimisation process to continue for a longer time, potentially improving convergence.
        popsize (Population Size): The number of candidate solutions (individuals) in each generation of the evolutionary algorithm. Increasing popsize can help explore the parameter space more thoroughly but may also increase computation time.
        Note: There is no gradient in the DE  like the Grid-search.  therefore criteria like ftol, xtol, and gtol, are not applicable.

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
__dateModified__ = "$dateModified: 2024-05-09 15:50:51 +0100 (Thu, May 09, 2024) $"
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
from ccpn.util.Path import aPath, fetchDir
import numpy as np
import pandas as pd
from lmfit import Parameters, Minimizer
import ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib as sdl
import ccpn.framework.lib.experimentAnalysis.ExperimentConstants as constants
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.experimentAnalysis.fittingModels.UncertaintyEstimationABC import MonteCarloSimulation
from .MinimiserLib import MinimiserSettingsPreset, _DefaultParameters
from ..RateModels import RatesHandler
from ..SpectralDensityFunctions import SDFHandler
from ..Scores import calculateChiSquared, _modelSelectionScoringFuncs


class SDMConstants:
    """
    Class to hold the factors and constants needed during the minimizations.
    """

    def __init__(self, spectrometerFrequency=600.05):
        self._spectrometerFrequency = spectrometerFrequency
        self._calculate_factors()

    def _calculate_factors(self):
        self.omegaH = sdl.calculateOmegaH(self._spectrometerFrequency, scalingFactor=1e6)
        self.omegaN = sdl.calculateOmegaN(self._spectrometerFrequency, scalingFactor=1e6)
        self.omegaC = sdl.calculateOmegaC(self._spectrometerFrequency, scalingFactor=1e6)
        self.gammaHN = constants.GAMMA_H / constants.GAMMA_N
        self.dFactor = sdl.calculate_d_factor(constants.rNH)
        self.cFactor = sdl.calculate_c_factor(self.omegaN, constants.N15_CSA)

    def __iter__(self):
        for key, value in vars(self).items():
            if not key.startswith('_'):
                yield key, value

    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        return repr(dict(self))

    def __str__(self):
        return str(dict(self))


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

    def getModelByName(self, name):
        for model_id, model in self.models.items():
            if model.name == name:
                return model

    def _initModelFromSettings(self):
        modelName = self.settingsHandler.diffusionModel

        if model := self.getModelByName(modelName):
            print(f'Starting Minimisation {model} -- {modelName}')
            self.activeModel = model(self)
        else:
            print(f'This model is not yet available -- {modelName}')

    def startMinimisation(self):
        if self.activeModel:
            # for i in range(3):
                self.activeModel.startMinimisation()


class LipariSzaboModel(ABC):
    name = 'generic'
    model_id = 0
    TcCount = 0  # rotational correlation time count

    def __init__(self, diffusionModelHandler, **kwargs):
        self.params = {}
        self._diffusionModelHandler = diffusionModelHandler
        self._settingsHandler = self._diffusionModelHandler.settingsHandler
        self._outputsHandler = self._diffusionModelHandler.outputsHandler
        self.rateColumns = self._settingsHandler._useRates
        self.rateErrColumns = self._settingsHandler._useRateErrors
        self._errIter = self._settingsHandler.errorCalculationIterations
        self._defaultMinimiserParams = _DefaultParameters()
        self._storeMinimiserProgress = False # store each evaluation result in a separate file. (use only for testing)
        self._progressData = {} #this will be a dict of dict of DataFrames! {residueCode1: {model_1: data, model_2: data}}
        self._storeInterimModelResults = False # store the statistical result for each model selection
        self._globalParamOptimisations = self._settingsHandler._globalParamOptimisations
        self._interimModelResults = pd.DataFrame(columns=[])  #a large dataframe containing optimised params, score results per residue for each evaluated model
        self._minimiserAccuracyPreset = self._settingsHandler.minimisationAccuracy
        self._modelSelectionMethod = self._settingsHandler._modelSelectionMethod

    @staticmethod
    def _calculateRatesFromParams(params, sdModel, neededRates, constantsDict):
        """
        :param params: obj. Parameters object containing the minimised values e.g.: tm, te, rex etc.
        :param sdModel: class, the spectralDensityFunction model. it contains the function to execute. e.g. Model 1 which optimise for the S2. see class documentation.
        :param neededRates: list. list of names for rate to calculate, e.g.: ['R1', 'R2'...]
        :param constantsDict: a dict of objs. key: spectrometer Frequency , value an obj (dict represented) containing the field dependent constants. e.g.: omegaH
        :return: array of floats, the newly predicted rates per given model, params and constants.
        """

        paramDict = params.valuesdict() # these are the optimised params from the minimiser: tm, te, rex etc. as a dict
        paramDict[sv.Ci] = 1  # for the isotropic => testing
        paramDict[sv.Ti] = paramDict[sv.TM]
        ratesP = []
        for sf, constants in constantsDict.items():
            # calculate the j(w) as required
            jH = sdModel.calculate(**{**paramDict, sv.W: constants.omegaH})
            jN = sdModel.calculate(**{**paramDict, sv.W: constants.omegaN})
            jHpN = sdModel.calculate(**{**paramDict, sv.W: constants.omegaH + constants.omegaN})
            jHmN = sdModel.calculate(**{**paramDict, sv.W: constants.omegaH - constants.omegaN})
            j0 = sdModel.calculate(**{**paramDict, sv.W: 0.0})
            # loop over the required rate definition, e.g.: R1, R2 etc and compute the predicted value given the j(w)
            for rateDef in neededRates:
                if rateDef == sv.R2 and sdModel.plusRex:
                    rex = params[sv.REX].value
                    ratep = RatesHandler.calculate(rateDef, constants.dFactor, constants.cFactor, j0, jH, jHmN, jHpN, jN, rex=rex)
                else:
                    ratep = RatesHandler.calculate(rateDef, constants.dFactor, constants.cFactor, j0, jH, jHmN, jHpN, jN)
                ratesP.append(ratep)
        return np.array(ratesP)

    @staticmethod
    def _localObjectiveFunction(params, sdModel, neededRates, expRates, expErrors, constantsDict, residueCode):
        """
        The local minimisation function which optimise the densityFunction models parameters per residue.
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

    @staticmethod
    def _globalObjectiveFunction(params, globalDataFrame, constantsDict):
        """
        The global minimisation function which optimise the global Tm for all residues.
        :return: the total sum of the individual chi-squared value obtained between the experimental values and the theoretical values calculated by the selected model per residue
        """
        totalScore = 0
        for ix, row in globalDataFrame.iterrows():
            residueCode = row[sv.NMRRESIDUECODE]
            expRates = row['rates']
            expErrors = row[f'rates{sv._ERR}']
            sdModel = row['sdModel']
            neededRates = row['rateColumns']
            _localParams = _DefaultParameters.extractLocalParams(params, residueCode)
            _localParams.add(params[sv.TM])
            score = LipariSzaboModel._localObjectiveFunction(_localParams, sdModel, neededRates, expRates, expErrors, constantsDict, residueCode)
            totalScore += score
        return totalScore

    def _getConstantsDict(self):
        """
        Get the various constants field dependent based on the Rates dataFrame
        :return: {field:{'dFactor': float,  'cFactor': float,  'omegaH': float, ...  }}
        """
        ratesData = self._diffusionModelHandler.getRatesData()
        frequencies = ratesData[sv.SF].unique()
        SDMdict = {}
        for sf in frequencies:
            SDM = SDMConstants(sf)
            SDMdict[sf] = SDM
        return SDMdict

    def _storeInterimModels(self, residueCode, model, result, n, iterationCount=1):
        hasConverged = result.success
        chisqr = result.chisqr
        _resultParams = {}
        _resultParams[sv.NMRRESIDUECODE] = residueCode
        _resultParams['model_id'] = model.model_id
        _resultParams[sv.CHISQR] = chisqr
        _resultParams[sv.RESIDUAL] = result.residual[-1]
        _resultParams['dataSize'] = n
        _resultParams['iterationCount'] = iterationCount
        _resultParams['converged'] = hasConverged
        for funcName, func in _modelSelectionScoringFuncs.items():
            score = func(model.model_id, n, chisqr)
            _resultParams[funcName] = score
        _rowRes = self._defaultMinimiserParams.asEmptyDict
        _resultParams.update(_rowRes)
        for paramName, param in result.params.items():
            _resultParams[paramName] = param.value
            _resultParams[f'{paramName}{sv._ERR}'] = param.stderr

        x = len(self._interimModelResults)
        for k,v in _resultParams.items():
            self._interimModelResults.loc[x, k] = v

        return self._interimModelResults

    def _getModelSelectionFunction(self):
        fun = _modelSelectionScoringFuncs.get(self._modelSelectionMethod, _modelSelectionScoringFuncs.get(sv.BICc))
        return fun

    def _getBestModel(self, residueCode, models, minimiserResults, n, iterationCount=1):
        """ Calculate the AIC for each minimiser result and return the lowest AIC minimiserResult and the utilised model"""
        results = np.array(minimiserResults)
        models = np.array(models)
        scores = []
        modelSelectFunc =  self._getModelSelectionFunction()
        for result, model in zip(results, models):
            if self._storeInterimModelResults:
                self._storeInterimModels(residueCode, model, result, n, iterationCount)
            chisqr = result.chisqr
            score = modelSelectFunc(model.model_id, n, chisqr)
            scores.append(score)
        scores = np.array(scores)
        bestIX = np.argmin(scores)# self.prioritiseScoreByDeltas(scores)# np.argmin(scores)
        bestResult = results[bestIX]
        return bestResult

    def _minimiseResidue(self, residueData, tmValue=None, varyTm=True, iterationCount=1):
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
        residueCode =  residueData[sv.NMRRESIDUECODE].values[0]
        # calculate the predicted values at each field and make the same array construct as per the ExpRates.
        results = []
        usedModels = []

        if self._storeMinimiserProgress:
            self._progressData[residueCode] = {}

        for model_id in sdfModels:
            sdModel = sdfHandler.getById(model_id)
            neededParams = [sv.TM] + sdModel.optimisedParams
            params = self._defaultMinimiserParams.getNewParamsByNames(neededParams)
            if tmValue:
                params[sv.TM].set(value=tmValue, vary=varyTm)
            if self._storeMinimiserProgress:
                progressDict = self._progressData[residueCode]
                progressDict[model_id] = pd.DataFrame(columns=self._defaultMinimiserParams.names)
                minimizer = Minimizer(self._localObjectiveFunction, params, fcn_args=(sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict, residueCode),
                                      method='differential_evolution', iter_cb=self._storeProgress)  #this is a callback for each minimisation step sent by the minimiser
            else:
                minimizer = Minimizer(self._localObjectiveFunction, params, fcn_args=(sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict, residueCode), method='differential_evolution', )

            # Perform the optimisation
            minSettings = MinimiserSettingsPreset.getPreset(self._minimiserAccuracyPreset)
            result = minimizer.minimize(method='differential_evolution', **minSettings)
            result.model_id = model_id
            usedModels.append(sdModel)
            # Report the optimized parameters and uncertainties
            hasConverged = result.success
            if hasConverged:
                results.append(result)
        n = len(ratesExp)
        bestMinimiserResult = self._getBestModel(residueCode, usedModels, results, n, iterationCount=iterationCount)
        return bestMinimiserResult
        
    def startMinimisation(self):
        ratesData = self._diffusionModelHandler.getRatesData()
        resultFrames = []
        dataGroupedByResidue = ratesData.groupby(sv.NMRRESIDUECODE)
        calc = LipariSzaboModel._calculateRatesFromParams

        # ~~~~~~~ Step 1): Local Minimisation for initial TM estimation ~~~~~~~~~~~~ #
        ## we loop residue by residue and we do the first optimisation with Tm variable
        resultRows = []
        for residueCode, residueData in dataGroupedByResidue:
            minimiserResult = self._minimiseResidue(residueData, iterationCount=1)
            _rowRes = self._defaultMinimiserParams.asEmptyDict
            for i, (paramName, param) in enumerate(minimiserResult.params.items()):
                print(f'{paramName}: {param.value} +/- {param.stderr}')
                _rowRes[sv.NMRRESIDUECODE] = residueCode
                _rowRes[paramName] = param.value
                _rowRes[f'{paramName}{sv._ERR}'] = 0
                _rowRes['model_id'] = minimiserResult.model_id
                _rowRes[sv.CHISQR] = minimiserResult.chisqr
                # show the original rates
                residueData.sort_values(by=sv.SF, inplace=True)
                ratesExp = residueData[self.rateColumns].values.flatten()
                errorsExp = residueData[self.rateErrColumns].values.flatten()
                sdModel = self._diffusionModelHandler.sdfHandler.getById(minimiserResult.model_id)
                predictions = calc(minimiserResult.params, sdModel, neededRates=self.rateColumns, constantsDict=self._getConstantsDict())
                _rowRes['rates'] = ratesExp
                _rowRes[f'rates{sv._ERR}'] = errorsExp
                _rowRes['predictions'] = predictions
                _rowRes['_minimiser'] = minimiserResult
                _rowRes['sdModel'] = sdModel
                _rowRes['neededRates'] = self.rateColumns
            resultRows.append(_rowRes)

        # store data
        _result = pd.DataFrame(resultRows)
        resultFrames.append(_result)
        _result.name = 'TM_vary'
        outputdir = self._outputsHandler._fetchTablesDirPath(self.name)
        _result.to_csv(f'{outputdir}/fitting_result_TM_vary.csv')

        # ~~~~ Step 2): Local Minimisation for final Model selection.  ~~~~ #
        ##  Get the median TM  as the initial value, keep it fix and do a model selection.
        print('Computing step 2....')
        tm = _result[sv.TM].median()
        tm_err = _result[sv.TM].std()
        resultRows = []
        globalParams = Parameters() #needed for next step in the protocol
        print(f'Starting model Selection. Estimated initial Tm: {tm} ...')
        for residueCode, residueData in dataGroupedByResidue:
            minimiserResult = self._minimiseResidue(residueData, tmValue=tm, varyTm=False,  iterationCount=2)
            print(f'RES: {residueCode} --Best Model --------{minimiserResult.model_id}')
            _rowRes = self._defaultMinimiserParams.asEmptyDict
            for i, (paramName, param) in enumerate(minimiserResult.params.items()):
                print(f'{paramName}: {param.value} +/- {param.stderr}')
                _rowRes[sv.NMRRESIDUECODE] = residueCode
                _rowRes[paramName] = param.value
                _rowRes[f'{paramName}{sv._ERR}'] = 0
                _rowRes['model_id'] = minimiserResult.model_id
                _rowRes[sv.CHISQR] = minimiserResult.chisqr
                # show the original rates
                residueData.sort_values(by=sv.SF, inplace=True)
                ratesExp = residueData[self.rateColumns].values.flatten()
                errorsExp = residueData[self.rateErrColumns].values.flatten()
                sdModel = self._diffusionModelHandler.sdfHandler.getById(minimiserResult.model_id)
                predictions = calc(minimiserResult.params, sdModel, neededRates=self.rateColumns, constantsDict=self._getConstantsDict())
                _rowRes['rates'] = ratesExp
                _rowRes[f'rates{sv._ERR}'] = errorsExp
                _rowRes['predictions'] = predictions
                _rowRes['_minimiser'] = minimiserResult
                _rowRes['sdModel'] = sdModel
                _rowRes['rateColumns'] = self.rateColumns
                for paramName, param in minimiserResult.params.items():
                    if paramName == sv.TM:
                        globalParams.add(paramName, value=param.value, min=param.min, max=param.max, vary=True)
                    else:
                        newParamName = f'{paramName}_{residueCode}'
                        globalParams.add(newParamName, value=param.value, min=param.min, max=param.max, vary=True)
            resultRows.append(_rowRes)
        globalDataFrame = pd.DataFrame(resultRows)
        globalDataFrame.to_csv(f'{outputdir}/fitting_result_Model_selection.csv')
        if self._storeInterimModelResults:
            outputPath = f'{outputdir}/interim_results.csv'
            self._interimModelResults.to_csv(outputPath)

        # ~~~~ Step 3) individual residues with Tm variable, global X2~~~~ #
        ##  Get the median TM  as the initial value, keep it fix and do a model selection.
        print('Computing step 3....')
        finalResultRows = []
        print(f'Starting final optimisation. Tm variable: {tm} ...')
        for ix, row in globalDataFrame.iterrows():
            residueCode = row[sv.NMRRESIDUECODE]
            minimiserResult = row['_minimiser']
            # we need to unfix Tm
            params = minimiserResult.params
            params[sv.TM].set(value=tm, vary=True)
            print('----> Starting MC Param:',params)
            ratesExp = row['rates']
            errorsExp = row[f'rates{sv._ERR}']
            sdModel = self._diffusionModelHandler.sdfHandler.getById(minimiserResult.model_id)
            minimiserKwargs = {'fcn_args': (sdModel, self.rateColumns, ratesExp, errorsExp, self._getConstantsDict(), residueCode)}
            mc = MonteCarloSimulation(Minimizer, params, self._localObjectiveFunction, minimiserMethod='differential_evolution', nSamples=self._errIter, **minimiserKwargs)
            mcParams = mc.estimateUncertainties(prefixMessage=f'Computing {residueCode}. ')
            _mcRowRes = self._defaultMinimiserParams.asEmptyDict
            for i, (paramName, param) in enumerate(mcParams.items()):
                print('+++> Final MC Param:', paramName, param.value)
                _mcRowRes[sv.NMRRESIDUECODE] = residueCode
                _mcRowRes[paramName] = param.value
                _mcRowRes[f'{paramName}{sv._ERR}'] = param.stderr
                _mcRowRes['model_id'] = minimiserResult.model_id
            predictions = calc(mcParams, sdModel, neededRates=self.rateColumns, constantsDict=self._getConstantsDict())
            _mcRowRes['rates'] = ratesExp
            _mcRowRes[f'rates{sv._ERR}'] = errorsExp
            _mcRowRes['predictions'] = predictions
            finalResultRows.append(_mcRowRes)
        _mcResult = pd.DataFrame(finalResultRows)
        _mcResult[sv.TM] = _mcResult[sv.TM].median()
        _mcResult[sv.TM_ERR] = _mcResult[sv.TM].std()

        _mcResult.name = 'Final'
        resultFrames.append(_mcResult)
        outputPath = f'{outputdir}/fitting_result_final.csv'
        _mcResult.to_csv(outputPath)

        # ~~~~ Step 3b optinal): Global Minimisation. Tm variable, global X2 minimisation for all residues ~~~~ #
        print('Computing step 3...')
        if self._globalParamOptimisations:
            print('paramsList', globalParams)
            minSettings = MinimiserSettingsPreset.getPreset(self._minimiserAccuracyPreset)
            minimizer = Minimizer(self._globalObjectiveFunction, params=globalParams, fcn_args=[globalDataFrame, self._getConstantsDict()])
            result = minimizer.minimize(method='differential_evolution', **minSettings)
            resultDict = defaultdict(dict)
            tmValues = []
            tmErrValues = []
            for i, (paramName, param) in enumerate(result.params.items()):
                print(f'GLOBAL ==> {paramName}: {param.value} +/- {param.stderr}')
                if '_' in paramName:
                    parts = paramName.split('_')
                    resCode = parts[-1]
                    _paramName = ''.join(parts[:-1])
                    resultDict[resCode].update(  {_paramName:param.value, f'{_paramName}{sv._ERR}':param.stderr})
                else:
                    tmValues.append(param.value)
                    tmErrValues.append(param.stderr)
            finalGlobalDf = pd.DataFrame(resultDict)
            finalGlobalDf = finalGlobalDf.transpose()
            finalGlobalDf[sv.TM] = tmValues[0]
            finalGlobalDf[f'{sv.TM}{sv._ERR}'] = tmErrValues[0]
            finalGlobalDf.name = 'TM_global'
            outputdir = self._outputsHandler._fetchTablesDirPath(self.name)
            finalGlobalDf.to_csv(f'{outputdir}/fitting_result_TM_global.csv')


        if self._storeMinimiserProgress:
            for residueCode, _progressData in self._progressData.items():
                outputDir = aPath(fetchDir(outputdir, str(residueCode)))
                for modId, df in _progressData.items():
                    fname = outputDir / f'{residueCode}_Model_{modId}.csv'
                    df.to_csv(fname)
                    print('exported: ', fname)

    # Define a callback function to store the progress in a Pandas DataFrame
    def _storeProgress(self, params, iter, resid, sdModel, neededRates, expRates, expErrors, constantsDict, residueCode, *args, **kwargs):
        """ This is for testing only. Might be fully removed or needs cleanup"""

        calc = LipariSzaboModel._calculateRatesFromParams
        predictions = calc(params, sdModel, neededRates=neededRates, constantsDict=constantsDict)
        dfDict = self._progressData[residueCode]
        df = dfDict[sdModel.model_id]
        x2 = calculateChiSquared(expRates, predictions, expErrors)
        scoreFunc = self._getModelSelectionFunction()
        score = scoreFunc(sdModel.model_id, len(expRates), x2)
        df.loc[iter, sv.CHISQR] = x2
        df.loc[iter, self._modelSelectionMethod] = score
        for paramName, param in params.items():
            df.loc[iter,paramName] = param.value
        for i, field in enumerate(constantsDict):
            for j, rate in enumerate(neededRates):
                ix = i * len(neededRates) + j
                expValue = expRates[ix]
                expError = expErrors[ix]
                pValue = predictions[ix]
                df.loc[iter, f'{rate}_{field}'] = expValue
                df.loc[iter, f'{rate}{sv._ERR}_{field}'] = expError
                df.loc[iter, f'{rate}_{field}_p'] = pValue
                df.loc[iter, f'model_id'] = sdModel.model_id

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


