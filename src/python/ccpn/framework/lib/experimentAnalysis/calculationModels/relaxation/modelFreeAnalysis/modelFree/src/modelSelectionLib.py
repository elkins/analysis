"""
This module contains the equations for calculating the various scoring functions, E.g.: AIC and chi Squared.

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
__dateModified__ = "$dateModified: 2024-05-24 16:14:11 +0100 (Fri, May 24, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
import pandas as pd
# from numba import jit
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv

def calculateAIC(k, n, x2):
    """
    Calculate the Akaike Information Criterion (AIC).
    :param k: Float, Number of free parameters in the model.
    :param n: Float, Number of data points.
    :param x2:  Float, Chi-squared
    :return: Float, The Akaike Information Criterion value.
    Note. Keep n, for the function signature to be consistent with the rest.
    """
    AIC = 2 * k + 2 * np.log(x2)
    return AIC


def calculateAICc(k, n, x2):
    """
    Calculate the corrected Akaike Information Criterion (AICc).
    :param k: Float, Number of free parameters in the model.
    :param n: Float, Number of data points.
    :param x2:  Float, Chi-squared
    :return: Float, The Corrected Akaike Information Criterion value.
    TODO check for zero-division on the factor
    """
    AIC =  calculateAIC(k, n, x2)
    AICc = AIC + (2 * k * (k + 1)) / (n - k - 1)
    return AICc

def calculateBIC(k, n, x2):
    """
    Calculate the Bayesian Information Criterion (BIC).
    :param k: Number of free parameters in the model.
    :param n:  Number of data points.
    :param x2:  Chi-squared
    :return: Float, Bayesian Information Criterion (BIC)
    """
    BIC = k * np.log(n) + 2 * np.log(x2)
    return BIC

def calculateBICc(k, n, x2):
    """
    Calculate the corrected Bayesian Information Criterion (BIC). Hurvich and Tsai in 1989
    :param k: Number of free parameters in the model.
    :param n:  Number of data points.
    :param x2:  Chi-squared
    :return: Float, Bayesian Information Criterion (BIC)
    TODO check for zero-division on the factor
    """
    BIC =  calculateBIC(k, n, x2)
    factor = (k * (k + 1) / 2) * np.log(n) / (n - k - 1)
    BICc = BIC + factor
    return BICc


# @singleton
class _ModelSelection(object):

    _FUNDICT = {
                           sv.AIC : calculateAIC,
                           sv.AICc: calculateAICc,
                           sv.BIC : calculateBIC,
                           sv.BICc: calculateBICc,
                           }

    def __init__(self, methodName, evaluationDataFrame=None, storeEvaluations=False):

        if methodName not in self._FUNDICT:
            methodName = sv.BICc
        self.methodName = methodName
        self._storeEvaluations = storeEvaluations
        self._evaluationDataFrame = evaluationDataFrame or pd.DataFrame(columns=[])

    @property
    def methodFunc(self):
        return self._FUNDICT.get(self.methodName)


    def _getBestModel(self, residueCode, models, minimiserResults, n, iterationCount=1):
        """ Calculate the AIC for each minimiser result and return the lowest AIC minimiserResult and the utilised model"""
        results = np.array(minimiserResults)
        models = np.array(models)
        scores = []

        for result, model in zip(results, models):
            if self._storeEvaluations:
                self._writeEvaluations(residueCode, model, result, n, iterationCount)
            chisqr = result.chisqr
            score = self.methodFunc(model.model_id, n, chisqr)
            scores.append(score)
        scores = np.array(scores)
        print(scores, 'SCORES')
        bestIX = np.argmin(scores) # self.prioritiseScoreByDeltas(scores)
        bestResult = results[bestIX]
        return bestResult

    def _writeEvaluations(self, residueCode, model, minimiserResult, n, iterationCount=1):
        """Store the calculation result for each method evaluated (calculate all AIC,BIC, AICc, BICc) to the _evaluationDataFrame """
        hasConverged = minimiserResult.success
        chisqr = minimiserResult.chisqr
        _resultParams = {}
        _resultParams[sv.NMRRESIDUECODE] = residueCode
        _resultParams['model_id'] = model.model_id
        _resultParams[sv.CHISQR] = chisqr
        _resultParams[sv.RESIDUAL] = minimiserResult.residual[-1]
        _resultParams['dataSize'] = n
        _resultParams['iterationCount'] = iterationCount
        _resultParams['converged'] = hasConverged
        for funcName, func in self._FUNDICT.items():
            score = func(model.model_id, n, chisqr)
            _resultParams[funcName] = score

        for paramName, param in minimiserResult.params.items():
            _resultParams[paramName] = param.value
            _resultParams[f'{paramName}{sv._ERR}'] = param.stderr

        x = len(self._evaluationDataFrame)
        for k,v in _resultParams.items():
            self._evaluationDataFrame.loc[x, k] = v

        return self._evaluationDataFrame

    def _save(self, path):
        self._evaluationDataFrame.to_csv(path)
