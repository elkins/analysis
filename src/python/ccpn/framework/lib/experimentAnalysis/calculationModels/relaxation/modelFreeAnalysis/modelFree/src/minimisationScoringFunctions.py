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
__dateModified__ = "$dateModified: 2024-05-15 19:54:04 +0100 (Wed, May 15, 2024) $"
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


# ~~~~~~ minimisation scoring functions ~~~~~~~~~ #

def calculateChiSquared(observed, predictions, errors):
    """
    Calculate the Chi-squared (χ²) statistic given observed (aka experimental) and expected values.
    :param observed: 1d array
    :param predictions: 1d array. Same length of observed
    :param errors: 1d array. Observed Errors.  Same length of observed
    :return: float, the SSE
    """
    squaredDifferences = (observed - predictions)**2
    x2 = np.sum(squaredDifferences / errors**2)
    return x2

def calculateSSE(observed, predictions):
    """
    The Sum of Squared Errors (SSE).  Measures the squared differences between the actual values and the predicted values.
    :param observed: 1d array
    :param predictions: 1d array
    :return: float, the SSE
    """
    residuals = observed - predictions
    return np.sum(residuals**2)

def calculateRMSE(observed, predictions):
    """
    The Root Mean Squared Error (RMSE).
    It measures the average squared difference between the actual values and the predicted values produced by the model.
    :param observed: 1d array
    :param predictions: 1d array
    :return:float,  RMSE
    """
    residuals = observed - predictions
    return np.sqrt(np.mean(residuals**2))
