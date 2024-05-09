"""
This module contains the equations for calculating the various scoring functions, Eg.: AIC and chi Squared.

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

import numpy as np
from numba import jit


@jit(nopython=True)
def calculateChiSquared(observed, predictions, errors):
    """
    Calculate the Chi-squared (χ²) statistic given observed and expected values.
    The Chi-squared   is a measure of the difference between observed and expected frequencies of a dataset.
     It is commonly used in statistics to assess the goodness of fit of a model to the data.
     Latex:
        \chi^2 = \sum \frac{(observed - predictions)^2}{errors^2}

    """
    squaredDifferences = (observed - predictions)**2
    x2 = np.sum(squaredDifferences / errors**2)
    return x2

def calculateAIC(k, n, max_likelihood):
    """
    Calculate the Akaike Information Criterion (AIC).

    Parameters:
    - k: Number of free parameters in the model.
    - max_likelihood: Maximum value of the likelihood function for the model.

    Returns:
    - AIC: Akaike Information Criterion value.
    """
    AIC = 2 * k + 2 * np.log(max_likelihood)
    return AIC

def calculateAIC_s(k, n, x2):
    """
    Calculate the Akaike Information Criterion (AIC).

    Parameters:
    - k: Number of free parameters in the model.
    - max_likelihood: Maximum value of the likelihood function for the model.

    Returns:
    - AIC: Akaike Information Criterion value.
    """
    AIC = (2*k) + x2
    return AIC

def calculateAICc(k, n, max_likelihood):
    """
    Calculate the corrected Akaike Information Criterion (AICc).
    Parameters:
    - AIC: Akaike Information Criterion.
    - k: Number of free parameters in the model.
    - n: Number of data points.

    Returns:
    - AICc: Corrected Akaike Information Criterion value.
    """
    AIC =  calculateAIC(k, n, max_likelihood)
    AICc = AIC + (2 * k * (k + 1)) / (n - k - 1)
    return AICc

def calculateBIC(k, n, x2):
    """
    Calculate the Bayesian Information Criterion (BIC).

    Parameters:
    - k: Number of free parameters in the model.
    - n: Number of data points.
    - max_likelihood: Maximum value of the likelihood function for the model. e.g. Chi-squared

    Returns:
    - BIC: Bayesian Information Criterion value.
    """
    BIC = k * np.log(n) + 2 * np.log(x2)
    return BIC

def calculateBIC_s(k, n, x2):
    """
    Calculate the Bayesian Information Criterion (BIC).

    Parameters:
    - k: Number of free parameters in the model.
    - n: Number of data points.
    - max_likelihood: Maximum value of the likelihood function for the model. e.g. Chi-squared

    Returns:
    - BIC: Bayesian Information Criterion value.
    """
    BIC = (k*np.log(n)) + x2
    return BIC

def calculateBICc(k, n, max_likelihood):
    """
    The additional term in the corrected Bayesian Information Criterion (BICc) formula,
     is an adjustment for finite sample sizes. It was proposed by Hurvich and Tsai in 1989 to address potential bias in the BIC when applied to small datasets.
    Parameters:
    - k: Number of free parameters in the model.
    - n: Number of data points.
    - max_likelihood: Maximum value of the likelihood function for the model. e.g. Chi-squared
    Returns:
    - BICc: Corrected Bayesian Information Criterion value.
    """
    BIC =  calculateBIC(k, n, max_likelihood)
    factor = (k * (k + 1) / 2) * np.log(n) / (n - k - 1)
    BICc = BIC + factor
    return BICc

@jit(nopython=True)
def sse(observed, predictions):
    residuals = observed - predictions
    return np.sum(residuals**2)

@jit(nopython=True)
def rmse(observed, predictions):
    residuals = observed - predictions
    return np.sqrt(np.mean(residuals**2))

import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv

_modelSelectionScoringFuncs = {sv.AIC: calculateAIC,
                          sv.AICc: calculateAICc,
                          sv.BIC: calculateBIC,
                          sv.BICc: calculateBICc,
                               'AIC_s': calculateAIC_s,
                               'BIC_s' : calculateBIC_s,
                               }

## Quick testing
if __name__ == "__main__":
    # E.g.: R1, R2, HetNoe at 600Mhz
    observed = np.array([1.2, 2.3, 0.8])
    predictions =  np.array([1.201, 2.302, 0.803])
    errors =  np.array([1e-2, 1e-3, 1e-3])
    X2 =  calculateChiSquared(observed, predictions, errors)
    print(f'Single Field X2  = {X2}')
    ## simulate multi field
    # E.g.: R1_600, R1_800,  R2_600, R2_800, HetNoe_600, HetNoe_800
    observed   = np.array([1.200, 1.500,  2.300, 3.101,  0.801, 0.861])
    predictions = np.array([1.201, 1.503,  2.302, 3.105,  0.802, 0.862])
    errors = np.array([1e-2, 1e-2, 1e-3, 1e-3, 1e-3, 1e-3])
    X2 = calculateChiSquared(observed, predictions, errors)
    print(f'Multi field X2 = {X2}')
