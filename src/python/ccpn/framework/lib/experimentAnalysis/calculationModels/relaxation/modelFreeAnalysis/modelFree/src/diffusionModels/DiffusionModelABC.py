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
__dateModified__ = "$dateModified: 2024-06-20 16:39:47 +0100 (Thu, June 20, 2024) $"
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
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.experimentAnalysis.fittingModels.UncertaintyEstimationABC import MonteCarloSimulation
from ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.spectralDensityLib import estimateOverallCorrelationTimeFromR1R2, estimateAverageS2
from .MinimiserLib import MinimiserSettingsPreset, _DefaultParameters
from ..RateModels import RatesHandler
from ..SpectralDensityFunctions import SDFHandler
from ..modelSelectionLib import _ModelSelection
from ..minimisationScoringFunctions import calculateChiSquared
from ..diffusionTensors.structureLib import _calculateAnisotropicCoeficients
from ..SpectralDensityFunctionsConstants import SDMConstants
from ..io.Logger import getLogger

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

    def __init__(self, parent):
        self.parent = parent
        self.settingsHandler = self.parent.settingsHandler
        self.inputsHandler = self.parent.inputsHandler
        self.outputsHandler = self.parent.outputsHandler
        self.structureHandler = self.parent.structureHandler

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
            getLogger().debug(f'Starting Minimisation {model} -- {modelName}')
            self.activeModel = model(self)
        else:
            getLogger().debug(f'This model is not yet available -- {modelName}')

    def startMinimisation(self):
        if self.activeModel:
            getLogger().info('Minimisation started.')
            self.activeModel.startMinimisation()
            self.activeModel.writeResults()



class LipariSzaboModel(ABC):
    name = 'generic'
    model_id = -1
    TiCount = 1  # rotational correlation time count
    DiCount = 1 # tensor D param count
    molecularStructureNeeded = False

    def __init__(self, diffusionModelHandler, **kwargs):
        self.params = {}
        self._diffusionModelHandler = diffusionModelHandler
        self._settingsHandler = self._diffusionModelHandler.settingsHandler
        self._outputsHandler = self._diffusionModelHandler.outputsHandler
        self._structureHandler = self._diffusionModelHandler.structureHandler
        self.rateColumns = self._settingsHandler.computingRates
        self.rateErrColumns = self._settingsHandler.computingRateErrors
        self._errIter = self._settingsHandler.errorCalculationIterations
        self._defaultMinimiserParams = _DefaultParameters(self.TiCount , self.DiCount)
        self._storeMinimiserProgress = False # store each evaluation result in a separate file. (use only for testing)
        self._progressData = {} #this will be a dict of dict of DataFrames! {residueCode1: {model_1: data, model_2: data}}
        self._minimiserAccuracyPreset = self._settingsHandler.minimisationAccuracy
        self._modelSelectionMethod = self._settingsHandler.modelSelectionMethod
        self._modelSelectionObj = _ModelSelection(methodName=self._modelSelectionMethod, evaluationDataFrame=None, storeEvaluations=False)
        self.resultDataFrames = {}

        if self._structureHandler.structureObj is None and self.molecularStructureNeeded:
            raise RuntimeError('This model requires a valid molecular structure to compute the Parameters')

    @staticmethod
    def _calculateRatesFromParams(params, sdModel, neededRates, constantsDict):
        """
        The lowest level call from the minimiser.
        Here is where the spectral density functions models are employed to compute the theoretical rates given the minimised params and field-dependent constants.
        ~ Keep abstract and speed-optimised ~
        :param params: obj. Parameters object containing the minimised values e.g.: tm, te, rex etc.
        :param sdModel: class, the spectralDensityFunction model. it contains the function to execute. e.g. Model 1 which optimise for the S2. see class documentation.
        :param neededRates: list. list of names for rate to calculate, e.g.: ['R1', 'R2'...]
        :param constantsDict: a dict of objs. key: spectrometer Frequency , value an obj (dict represented) containing the field dependent constants. e.g.: omegaH
        :return: array of floats, the newly predicted rates per given model, params and constants.
        """
        paramDict = params.valuesdict()  # these are the optimised params from the minimiser: tm, te, rex etc. as a dict
        paramDict[sv.Ci] = np.array([p.value for n, p in params.items() if n.startswith(sv.Ci)])
        paramDict[sv.Ti] = np.array([p.value for n, p in params.items() if n.startswith(sv.Ti)])
        predictedRates = []
        for sf, _ in constantsDict.items():
            omegas = [0.0, _.omegaH, _.omegaH - _.omegaN,  _.omegaH + _.omegaN,  _.omegaN] # Order is important !!! It mirrors the args signature in the RatesHandler methods.
            jws = [sdModel.calculate(**{**paramDict, sv.W: w}) for w in omegas] # update the omega in the ParamDict and calculate the j(w)s:  j0, jH, jHmN, jHpN, jN at field
            for rateDef in neededRates: # loop over the required rate definition, e.g.: R1, R2 etc and compute the predicted rates value given the various j(w)
                if rateDef == sv.R2 and sdModel.plusRex: #update Rex kwarg if R2 calculation.
                    _rateArgs = (rateDef, _.dFactor, _.cFactor, *jws,  params[sv.REX].value)
                else:
                    _rateArgs = (rateDef, _.dFactor, _.cFactor, *jws)
                predictedRates.append(RatesHandler.calculate(*_rateArgs)) #signature: *(rateName, d2, c2, j0, jH, jHmN, jHpN, jN, ^rex^) ^rex->R2-only^
        return np.array(predictedRates)

    @staticmethod
    def _localObjectiveFunction(params, calcRatesFunc, sdModel, neededRates, expRates, expErrors, constantsDict, residueCode):
        """
        The local minimisation function which optimise the densityFunction models parameters per residue.
        Called by the minimiser
        :param params: minimiser Parameter object
        :param calcRatesFunc. the  LipariSzaboModel._calculateRatesFromParams function
        :param expRates: 1d array with the experimental rates by rate type, e.g.: R1 per ascending field strength ,e.g.: r1at600,  r2at600, ... r1at800, r2at800...
        :param expErrors: 1d array, same as expRates
        :param constantsDict: a dict of dict. {field:{constants}} e.g.: {600: {c_factor:float, ...}}. see above
        :param residueCode: int. the source of the optimising parameters
        :return: the chi-squared value obtained between the experimental values and the theoretical values calculated by the selected model.
        """
        predictions = calcRatesFunc(params, sdModel, neededRates, constantsDict)
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
            SDM = SDMConstants(sf)
            SDMdict[sf] = SDM
        return SDMdict

    def _minimiseResidue(self, residueData, TiValues=None, CiValues=None, varyTensorParams=True, iterationCount=1):
        """Minimise the optimisation params based on the setting models for a residue.
         :param: ResidueData: pandas dataFrame for one residue at single/ multiple field rates
         """
        sdfHandler = self._diffusionModelHandler.sdfHandler
        constantsDict = self._getConstantsDict()
        sdfModels = self._diffusionModelHandler._getSDFmodel_ids()
        calcRatesFunc = self._calculateRatesFromParams
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
            neededParams = sdModel.optimisedParams
            params = self._defaultMinimiserParams.getNewParamsByNames(neededParams)
            for i in range(self.TiCount):
                i+=1
                tiParam = self._defaultMinimiserParams.get(f'{sv.Ti}_{i}')
                ciParam = self._defaultMinimiserParams.get(f'{sv.Ci}_{i}')
                params.add(tiParam)
                params.add(ciParam)

            if TiValues is not None and len(TiValues)==self.TiCount:
                for i in range(self.TiCount):
                    i += 1
                    params[f'{sv.Ti}_{i}'].set(value=TiValues[i], vary=varyTensorParams)
                    params[f'{sv.Ci}_{i}'].set(value=CiValues[i], vary=False)

            if self._storeMinimiserProgress:
                progressDict = self._progressData[residueCode]
                progressDict[model_id] = pd.DataFrame(columns=self._defaultMinimiserParams.names)
                minimizer = Minimizer(self._localObjectiveFunction, params, fcn_args=(calcRatesFunc, sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict, residueCode),
                                      method='differential_evolution', iter_cb=self._storeMinimiserIterationProgress)  #this is a callback for each minimisation step sent by the minimiser
            else:
                minimizer = Minimizer(self._localObjectiveFunction, params, fcn_args=(calcRatesFunc, sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict, residueCode), method='differential_evolution', )

            # Perform the optimisation
            minSettings = MinimiserSettingsPreset.getPreset(self._minimiserAccuracyPreset)
            result = minimizer.minimize(method='differential_evolution', **minSettings)
            result.model_id = model_id
            usedModels.append(sdModel)
            hasConverged = result.success
            if hasConverged: #keep the model for the selection only if it has converged
                results.append(result)
        n = len(ratesExp)
        bestMinimiserResult = self._modelSelectionObj._getBestModel(residueCode, usedModels, results, n, iterationCount=iterationCount)
        return bestMinimiserResult
        
    def startMinimisation(self):
        getLogger().info(f'Active model: {self.name}')

        ratesData = self._diffusionModelHandler.getRatesData()
        dataGroupedByResidue = ratesData.groupby(sv.NMRRESIDUECODE)
        calcRatesFunc = self._calculateRatesFromParams

        ## ~~~~~~~ Step 1): Local Minimisation for initial Tc estimation ~~~~~~~~~~~~ #
        ## we loop residue by residue and we do the first optimisation with Tc variable
        n = 1
        getLogger().info('Starting fitting...')
        resultRows = []
        for residueCode, residueData in dataGroupedByResidue:
            minimiserResult = self._minimiseResidue(residueData, iterationCount=1)
            _rowRes = self._defaultMinimiserParams.asEmptyDict
            _rowRes[sv.NMRRESIDUECODE] = residueCode
            _rowRes['model_id'] = minimiserResult.model_id
            _rowRes[sv.MINIMISER_OBJ] = minimiserResult
            for i, (paramName, param) in enumerate(minimiserResult.params.items()):
                _rowRes[paramName] = param.value
                _rowRes[f'{paramName}{sv._ERR}'] = None
            resultRows.append(_rowRes)
        # store data
        _result = pd.DataFrame(resultRows)
        self.resultDataFrames[n] = _result
        n += 1
        ## ~~~~ Step 2): Local Minimisation for final Model selection.  ~~~~ #
        ##  Get the median Tc  as the initial value, keep it fix and do a model selection.
        getLogger().info('Computing step 2....')
        Ti_columns = _result.loc[:, _result.columns.str.startswith(sv.Ti)]
        ti = Ti_columns.median()
        resultRows = []
        getLogger().info(f'Starting model Selection. Estimated initial Tc: {ti} ...')
        for residueCode, residueData in dataGroupedByResidue:
            minimiserResult = self._minimiseResidue(residueData, TiValues=[ti], varyTensorParams=False,  iterationCount=2)
            _rowRes = self._defaultMinimiserParams.asEmptyDict
            _rowRes[sv.NMRRESIDUECODE] = residueCode
            _rowRes['model_id'] = minimiserResult.model_id
            _rowRes[sv.MINIMISER_OBJ] = minimiserResult
            residueData.sort_values(by=sv.SF, inplace=True)
            ratesExp = residueData[self.rateColumns].values.flatten()
            errorsExp = residueData[self.rateErrColumns].values.flatten()
            _rowRes['rates'] = ratesExp
            _rowRes[f'rates{sv._ERR}'] = errorsExp
            for i, (paramName, param) in enumerate(minimiserResult.params.items()):
                _rowRes[paramName] = param.value
                _rowRes[f'{paramName}{sv._ERR}'] = None
            resultRows.append(_rowRes)
        globalDataFrame = pd.DataFrame(resultRows)
        self.resultDataFrames[n] = globalDataFrame

        n += 1
        # ~~~~ Step 3) individual residues with Tc variable, global X2~~~~ #
        ##  Get the median Tc  as the initial value, keep it fix and do a model selection.
        getLogger().info('Computing step 3....')
        finalResultRows = []
        getLogger().info(f'Starting final optimisation. Tc variable: {ti} ...')
        for ix, row in globalDataFrame.iterrows():
            residueCode = row[sv.NMRRESIDUECODE]
            minimiserResult = row[sv.MINIMISER_OBJ]
            # we need to unfix Tc
            params = minimiserResult.params
            params[sv.Ti].set(value=ti, vary=True)
            ratesExp = row['rates']
            errorsExp = row[f'rates{sv._ERR}']
            sdModel = self._diffusionModelHandler.sdfHandler.getById(minimiserResult.model_id)
            minimiserKwargs = {'fcn_args': (calcRatesFunc, sdModel, self.rateColumns, ratesExp, errorsExp, self._getConstantsDict())}
            mc = MonteCarloSimulation(Minimizer, params, self._localObjectiveFunction, minimiserMethod='differential_evolution', nSamples=self._errIter, **minimiserKwargs)
            mcParams = mc.estimateUncertainties(prefixMessage=f'Computing {residueCode}. ')
            _mcRowRes = self._defaultMinimiserParams.asEmptyDict
            _mcRowRes['model_id'] = minimiserResult.model_id
            _mcRowRes[sv.NMRRESIDUECODE] = residueCode
            for i, (paramName, param) in enumerate(mcParams.items()):
                _mcRowRes[paramName] = param.value
                _mcRowRes[f'{paramName}{sv._ERR}'] = param.stderr
            finalResultRows.append(_mcRowRes)
        _mcResult = pd.DataFrame(finalResultRows)
        _mcResult[sv.TC] = _mcResult[sv.Ti].median()
        _mcResult[sv.TC_ERR] = _mcResult[sv.Ti].std()
        self.resultDataFrames[n] = _mcResult

    def _storeMinimiserIterationProgress(self, params, iter, score, calcRateFunc , sdModel, neededRates, expRates, expErrors, constantsDict, residueCode, *args, **kwargs):
        """Internal to the minimiser. This is a special callback function to store the progress in a Pandas DataFrame and is only called from within the minimiser iter_cb argument.
        It has a specific defined signature. """
        try:
            calc = LipariSzaboModel._calculateRatesFromParams
            cosVector = kwargs.get('cosVector')
            Dis = np.array([p.value for n, p in params.items() if n.startswith(sv.Di)])
            tiValues = FullyAnisotropicModel._calculateTiFromDiso(*Dis)
            ciValues = _calculateAnisotropicCoeficients(cosVector, *Dis)
            for i, (ti, ci) in enumerate(zip(tiValues, ciValues)):
                i += 1
                params.add(f'{sv.Ti}_{i}', value=ti)
                params.add(f'{sv.Ci}_{i}', value=ci)
            predictions = calc(params, sdModel, neededRates=neededRates, constantsDict=constantsDict)
            dfDict = self._progressData[residueCode]
            df = dfDict[sdModel.model_id]
            x2 = calculateChiSquared(expRates, predictions, expErrors)
            scoreFunc = self._modelSelectionObj.methodFunc
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
        except Exception as e:
            getLogger().warn(f'Cannot store progress. {e}')

    def writeResults(self):
        """ Save the various frames."""
        outputdir = self._outputsHandler._fetchTablesDirPath(self.name)
        for dataFrameName, dataFrame in self.resultDataFrames.items():
            outputPath = f'{outputdir}/{dataFrameName}.csv'
            dataFrame.to_csv(outputPath)
            getLogger().info(f'Exported result: {dataFrameName} to {outputPath}')

        if self._modelSelectionObj._storeEvaluations:
            outputPath = f'{outputdir}/_modelSelectionEvaluations.csv'
            self._modelSelectionObj._save(outputPath)
            getLogger().info(f'Exported Model Selection Evaluations to {outputPath}')

        if self._storeMinimiserProgress:
            for residueCode, _progressData in self._progressData.items():
                interimDir =  aPath(fetchDir(outputdir, 'minimiserProgress'))
                outputDir = aPath(fetchDir(interimDir, str(residueCode)))
                for modId, df in _progressData.items():
                    outputPath = outputDir / f'{residueCode}_Model_{modId}.csv'
                    df.to_csv(outputPath)
                    getLogger().info(f'Exported Model ID: {modId} minimisation progress to {outputPath}')

class IsotropicModel(LipariSzaboModel):
    name = 'Isotropic'
    model_id = 1
    TiCount = 1  # described total rotational correlation time count
    DiCount = 1
    molecularStructureNeeded = False


class AxialSymmetricModel(LipariSzaboModel):
    name = 'Axially-Symmetric'
    model_id = 2
    TiCount = 3
    DiCount = 3 # corresponds to  Di_1 -> Dperpendicular; Di_2 -> Dparallel

    molecularStructureNeeded = True

    @staticmethod
    def calculateTensorCoefficients(theta):
        """
        Calculate the coefficients for an Axially Symmetric rotational Diffusion model

        Reference:
        E.q 12 The role of protein motions in molecular recognition: insights from heteronuclear NMR relaxation measurements. R. Andrew Atkinson, Bruno Kieffer.
        Progress in Nuclear Magnetic Resonance Spectroscopy 44 (2004) 141–187.

        Latex
            J(w) eq. 12 of reference
            J(\omega) = \frac{2}{5} \biggl[ A \frac {\tau_A} {1+\omega^2\tau_A^2} + B \frac {\tau_B} {1+\omega^2\tau_B^2} + C \frac {\tau_C} {1+\omega^2\tau_C^2} \biggr]

            Coefficients
            A = \frac{1}{4} \: (3 \cos^2 \theta -1)^2
            B = 3 \sin^2 \theta \cos^2 \theta
            C = \frac{3}{4} \: \sin^4 \theta
            where theta is the angle between the N-H vector and the unique axis of the diffusion tensor
        """
        A = (1 / 4) * (3 * np.cos(theta)**2 - 1)**2
        B = 3 * np.sin(theta)**2 * np.cos(theta)**2
        C = (3 / 4) * np.sin(theta)**4
        return np.array([A, B, C])

    @staticmethod
    def calculateDiffusionCoefficientsProlate(D_iso):
        D_perp = 0.75 * D_iso
        D_parallel = 1.25 * D_iso
        return D_perp, D_perp, D_parallel

    @staticmethod
    def calculateDiffusionCoefficientsOblate(D_iso):
        D_perp = 0.75 * D_iso
        D_parallel = 1.25 * D_iso
        return D_parallel, D_parallel, D_perp

    def _calculateTiFromDiso(self, D_iso):
        """
        :param D_iso: Diffusion Isotropic value. Diso = 1/6TauC
        :return: array of Ta, Tb, Tc
        """
        structureHandler = self._diffusionModelHandler.structureHandler
        shape = structureHandler.getEllipsoidShape()
        if shape == sv.PROLATE:
            D_perp, D_perp, D_parallel = self.calculateDiffusionCoefficientsProlate(D_iso)
        elif shape == sv.OBLATE:
            D_parallel, D_parallel, D_perp = self.calculateDiffusionCoefficientsOblate(D_iso)
        else:
            raise RuntimeError(f'Undefined shape. Cannot Compute Ti for model {self.name}')

        ta = 1/(6*D_parallel)
        tb = 1/(D_perp+5*D_parallel)
        tc = 1/(4*D_perp + 2*D_parallel)
        return np.array([ta, tb, tc])

    def startMinimisation(self):
        getLogger().info(f'Active model: {self.name}')
        structureHandler = self._diffusionModelHandler.structureHandler
        _NH_anglesDict = structureHandler.get_NH_anglesByResidueDict()

        ratesData = self._diffusionModelHandler.getRatesData()
        dataGroupedByResidue = ratesData.groupby(sv.NMRRESIDUECODE)
        calcRatesFunc = self._calculateRatesFromParams

        ## ~~~~~~~ Step 1): Local Minimisation for initial Tc estimation ~~~~~~~~~~~~ #
        ## we loop residue by residue and we do the first optimisation with Tc variable
        n = 1
        getLogger().info('Starting fitting...')
        resultRows = []

        ratesDataBySF = self._diffusionModelHandler.getRatesDataBySF()
        taucFields = []
        for sf, df in ratesDataBySF.items():
            r1 = df['R1'].values
            r2 = df['R2'].values
            noe = df[sv.HETNOE].values
            # Calculate the overall correlation time
            localTcs = estimateOverallCorrelationTimeFromR1R2(r1, r2, spectrometerFrequency=float(sf))
            fieldTc = np.median(localTcs)
            taucFields.append(fieldTc)
            s2 = estimateAverageS2(r1, r2, noe=noe, noeExclusionLimit=0.65, method='median', proportiontocut=.1)
        tc = np.mean(taucFields)

        Diso = (1/(6*tc))*1e-7
        TiValues = self._calculateTiFromDiso(Diso)
        for residueCode, residueData in dataGroupedByResidue:
            getLogger().info(f'Minimising residue {residueCode}')
            theta, thetaStd = _NH_anglesDict.get(residueCode)
            ciValues = self.calculateTensorCoefficients(theta)

            sdfHandler = self._diffusionModelHandler.sdfHandler
            constantsDict = self._getConstantsDict()
            sdfModels = self._diffusionModelHandler._getSDFmodel_ids()
            calcRatesFunc = self._calculateRatesFromParams
            # we expect rates at multiple fields.  sort by ascending (low->high) the spectrometerFrequency value
            residueData.sort_values(by=sv.SF, inplace=True)
            # create a 1D array of rates at different fields. e.g.: R1s, R2s, NOEs in ascending field strength  (r1_600, r2_600, hetNoe_600,  r1_800, r2_800, hetNoe_800,  etc...)
            ratesExp = residueData[self.rateColumns].values.flatten()
            errorsExp = residueData[self.rateErrColumns].values.flatten()
            residueCode = residueData[sv.NMRRESIDUECODE].values[0]
            # calculate the predicted values at each field and make the same array construct as per the ExpRates.
            results = []
            usedModels = []
            if self._storeMinimiserProgress:
                self._progressData[residueCode] = {}
            for model_id in sdfModels:
                sdModel = sdfHandler.getById(model_id)
                neededParams = sdModel.optimisedParams
                params = self._defaultMinimiserParams.getNewParamsByNames(neededParams)
                for i, (ci, ti) in enumerate(zip(ciValues, TiValues)):
                    i += 1
                    tiParam = self._defaultMinimiserParams.get(f'{sv.Ti}_{i}')
                    ciParam = self._defaultMinimiserParams.get(f'{sv.Ci}_{i}')
                    params.add(tiParam)
                    params.add(ciParam)
                    params[f'{sv.Ti}_{i}'].set(value=ti, vary=True)
                    params[f'{sv.Ci}_{i}'].set(value=ci, min=0, max=ci*2, vary=False)
                if self._storeMinimiserProgress:
                    progressDict = self._progressData[residueCode]
                    progressDict[model_id] = pd.DataFrame(columns=self._defaultMinimiserParams.names)
                    minimizer = Minimizer(self._localObjectiveFunction, params, fcn_args=(calcRatesFunc, sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict, residueCode),
                                          method='differential_evolution', iter_cb=self._storeMinimiserIterationProgress)  #this is a callback for each minimisation step sent by the minimiser
                else:
                    minimizer = Minimizer(self._localObjectiveFunction, params, fcn_args=(calcRatesFunc, sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict, residueCode), method='differential_evolution', )

                # Perform the optimisation
                minSettings = MinimiserSettingsPreset.getPreset(self._minimiserAccuracyPreset)
                result = minimizer.minimize(method='differential_evolution', **minSettings)
                result.model_id = model_id
                usedModels.append(sdModel)
                hasConverged = result.success
                if hasConverged:  #keep the model for the selection only if it has converged
                    results.append(result)

            n = len(ratesExp)
            try:
                minimiserResult = self._modelSelectionObj._getBestModel(residueCode, usedModels, results, n, iterationCount=1)
                _rowRes = self._defaultMinimiserParams.asEmptyDict
                _rowRes[sv.NMRRESIDUECODE] = residueCode
                _rowRes['model_id'] = minimiserResult.model_id
                _rowRes[sv.MINIMISER_OBJ] = minimiserResult
                for i, (paramName, param) in enumerate(minimiserResult.params.items()):
                    _rowRes[paramName] = param.value
                    _rowRes[f'{paramName}{sv._ERR}'] = None
                resultRows.append(_rowRes)
            except Exception as err:
                getLogger().warn(f'Could not minimise residue {residueCode}. Exit with error: {err}.')

            if self._storeMinimiserProgress:
                outputdir = self._outputsHandler._fetchTablesDirPath(self.name)
                _progressData = self._progressData[residueCode]
                interimDir = aPath(fetchDir(outputdir, 'minimiserProgress'))
                outputDir = aPath(fetchDir(interimDir, str(residueCode)))
                for modId, df in _progressData.items():
                    outputPath = outputDir / f'{residueCode}_Model_{modId}.csv'
                    df.to_csv(outputPath)
                    getLogger().info(f'Exported Model ID: {modId} minimisation progress to {outputPath}')

        _result = pd.DataFrame(resultRows)
        self.resultDataFrames[n] = _result


class FullyAnisotropicModel(LipariSzaboModel):
    name = 'Fully-Anisotropic'
    model_id = 3
    TiCount = 5
    DiCount = 3 # expressed as Di_1 to Di_3 and correspond to   Dxx; Dyy; Dzz


    molecularStructureNeeded = True

    @staticmethod
    def _localObjectiveFunction(params, calcRatesFunc, sdModel, neededRates, expRates, expErrors, constantsDict, residueCode,  **kwargs):
        """
        The local minimisation function which optimise the densityFunction models parameters per residue.
        Called by the minimiser
        :param params: minimiser Parameter object
        :param calcRatesFunc. the  LipariSzaboModel._calculateRatesFromParams function
        :param expRates: 1d array with the experimental rates by rate type, e.g.: R1 per ascending field strength ,e.g.: r1at600,  r2at600, ... r1at800, r2at800...
        :param expErrors: 1d array, same as expRates
        :param constantsDict: a dict of dict. {field:{constants}} e.g.: {600: {c_factor:float, ...}}. see above
        :param residueCode: int. the source of the optimising parameters
        :return: the chi-squared value obtained between the experimental values and the theoretical values calculated by the selected model.
        """
        # need to build the Ti params from Di
        cosVector = kwargs.get('cosVector')
        Dis = np.array([p.value for n, p in params.items() if n.startswith(sv.Di)])
        tiValues = FullyAnisotropicModel._calculateTiFromDiso(*Dis)
        ciValues = _calculateAnisotropicCoeficients(cosVector, *Dis)
        for i, (ti, ci) in enumerate(zip(tiValues,ciValues)):
            i += 1
            params.add(f'{sv.Ti}_{i}', value=ti)
            params.add(f'{sv.Ci}_{i}', value=ci)
        predictions = calcRatesFunc(params, sdModel, neededRates, constantsDict)
        score = calculateChiSquared(expRates, predictions, expErrors)
        for i, (ti, ci) in enumerate(zip(tiValues,ciValues)):
            i += 1
            params.pop(f'{sv.Ti}_{i}', None)
            params.pop(f'{sv.Ci}_{i}', None)
        return score

    @staticmethod
    def _calculateTiFromDiso(D1, D2, D3):
        """
        :param D_iso: Diffusion Isotropic value. Diso = 1/6TauC
        :return: array of Tau1, tau2, tau3, tauPlus, tauMinus
        """
        R1, R2, R3 = D1, D2, D3
        R = np.mean([R1, R2, R3])
        L2 = np.mean([R1*R2, R1*R3, R2*R3])
        tau1 = 1 / (4*R1 + R2 + R3)
        tau2 = 1 / (R1 + 4*R2 + R3)
        tau3 = 1 / (R1 + R2 + 4*R3)
        tauPlus = 1/ (6 * (R + np.sqrt(R**2 - L2)))
        tauMinus = 1/ (6 * (R - np.sqrt(R**2 - L2)))
        return np.array([tau1, tau2, tau3, tauPlus, tauMinus])

    def startMinimisation(self):
        getLogger().info(f'Active model: {self.name}')
        structureHandler = self._diffusionModelHandler.structureHandler
        _NH_anglesDict = structureHandler.get_NH_cosineAnglesByResidueDict()

        ratesData = self._diffusionModelHandler.getRatesData()
        dataGroupedByResidue = ratesData.groupby(sv.NMRRESIDUECODE)
        calcRatesFunc = self._calculateRatesFromParams

        ## ~~~~~~~ Step 1): Local Minimisation for initial Tc estimation ~~~~~~~~~~~~ #
        ## we loop residue by residue and we do the first optimisation with Tc variable
        n = 1
        getLogger().info('Starting fitting...')
        resultRows = []

        ratesDataBySF = self._diffusionModelHandler.getRatesDataBySF()
        taucFields = []
        for sf, df in ratesDataBySF.items():
            r1 = df['R1'].values
            r2 = df['R2'].values
            noe = df[sv.HETNOE].values
            # Calculate the overall correlation time
            localTcs = estimateOverallCorrelationTimeFromR1R2(r1, r2, spectrometerFrequency=float(sf))
            fieldTc = np.median(localTcs)
            taucFields.append(fieldTc)
            s2 = estimateAverageS2(r1, r2, noe=noe, noeExclusionLimit=0.65, method='median', proportiontocut=.1)
        tc = np.mean(taucFields)

        Diso = 1/(6*tc)

        for residueCode, residueData in dataGroupedByResidue:
            getLogger().info(f'Minimising residue {residueCode}')
            cosVector = _NH_anglesDict.get(residueCode)
            sdfHandler = self._diffusionModelHandler.sdfHandler
            constantsDict = self._getConstantsDict()
            sdfModels = self._diffusionModelHandler._getSDFmodel_ids()
            calcRatesFunc = self._calculateRatesFromParams
            # we expect rates at multiple fields.  sort by ascending (low->high) the spectrometerFrequency value
            residueData.sort_values(by=sv.SF, inplace=True)
            # create a 1D array of rates at different fields. e.g.: R1s, R2s, NOEs in ascending field strength  (r1_600, r2_600, hetNoe_600,  r1_800, r2_800, hetNoe_800,  etc...)
            ratesExp = residueData[self.rateColumns].values.flatten()
            errorsExp = residueData[self.rateErrColumns].values.flatten()
            residueCode = residueData[sv.NMRRESIDUECODE].values[0]
            # calculate the predicted values at each field and make the same array construct as per the ExpRates.
            results = []
            usedModels = []
            if self._storeMinimiserProgress:
                self._progressData[residueCode] = {}
            for model_id in sdfModels:
                sdModel = sdfHandler.getById(model_id)
                neededParams = sdModel.optimisedParams
                params = self._defaultMinimiserParams.getNewParamsByNames(neededParams)
                # add the initial Tensor information to params
                Dxx, Dyy, Dzz = 0.75 * Diso, Diso, 1.25 * Diso
                for i, Di in enumerate([Dxx, Dyy, Dzz]):
                    i += 1
                    diParam = self._defaultMinimiserParams.get(f'{sv.Di}_{i}')
                    params.add(diParam)
                    params[f'{sv.Di}_{i}'].set(value=Di, min=Di/2, max=Di*2, vary=True)

                if self._storeMinimiserProgress:
                    progressDict = self._progressData[residueCode]
                    progressDict[model_id] = pd.DataFrame(columns=self._defaultMinimiserParams.names)
                    minimizer = Minimizer(self._localObjectiveFunction, params, fcn_args=(calcRatesFunc, sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict, residueCode), fcn_kws={'cosVector':cosVector},
                                          method='differential_evolution', iter_cb=self._storeMinimiserIterationProgress)  #this is a callback for each minimisation step sent by the minimiser
                else:
                    minimizer = Minimizer(self._localObjectiveFunction, params, fcn_args=(calcRatesFunc, sdModel, self.rateColumns, ratesExp, errorsExp, constantsDict, residueCode),  fcn_kws={'cosVector':cosVector},
                                          method='differential_evolution', )

                # Perform the optimisation
                minSettings = MinimiserSettingsPreset.getPreset(self._minimiserAccuracyPreset)
                # try:
                result = minimizer.minimize(method='differential_evolution', **minSettings)
                result.model_id = model_id
                usedModels.append(sdModel)
                hasConverged = result.success
                if hasConverged:  #keep the model for the selection only if it has converged
                    results.append(result)
                # except Exception as err:
                #     getLogger().warn(f'Could not minimise residue {residueCode}. Exit with error: {err}.')

            n = len(ratesExp)
            try:
                minimiserResult = self._modelSelectionObj._getBestModel(residueCode, usedModels, results, n, iterationCount=1)
                Dis = np.array([p.value for n, p in minimiserResult.params.items() if n.startswith(sv.Di)])
                tiValues = FullyAnisotropicModel._calculateTiFromDiso(*Dis)
                ciValues = _calculateAnisotropicCoeficients(cosVector, *Dis)
                for i, (ti, ci) in enumerate(zip(tiValues, ciValues)):
                    i += 1
                    minimiserResult.params.add(f'{sv.Ti}_{i}', value=ti)
                    minimiserResult.params.add(f'{sv.Ci}_{i}', value=ci)
                _rowRes = self._defaultMinimiserParams.asEmptyDict
                _rowRes[sv.NMRRESIDUECODE] = residueCode
                _rowRes['model_id'] = minimiserResult.model_id
                _rowRes[sv.MINIMISER_OBJ] = minimiserResult
                for i, (paramName, param) in enumerate(minimiserResult.params.items()):
                    _rowRes[paramName] = param.value
                    _rowRes[f'{paramName}{sv._ERR}'] = None
                resultRows.append(_rowRes)
            except Exception as err:
                getLogger().warn(f'Could not minimise residue {residueCode}. Exit with error: {err}.')

            if self._storeMinimiserProgress:
                outputdir = self._outputsHandler._fetchTablesDirPath(self.name)
                _progressData = self._progressData[residueCode]
                interimDir = aPath(fetchDir(outputdir, 'minimiserProgress'))
                outputDir = aPath(fetchDir(interimDir, str(residueCode)))
                for modId, df in _progressData.items():
                    outputPath = outputDir / f'{residueCode}_Model_{modId}.csv'
                    df.to_csv(outputPath)
                    getLogger().info(f'Exported Model ID: {modId} minimisation progress to {outputPath}')

        _result = pd.DataFrame(resultRows)
        self.resultDataFrames[n] = _result


# ~~~~~~~~~ Register the Models ~~~~~~~~~~ #

DiffusionModelHandler.register(IsotropicModel)
DiffusionModelHandler.register(AxialSymmetricModel)
DiffusionModelHandler.register(FullyAnisotropicModel)


