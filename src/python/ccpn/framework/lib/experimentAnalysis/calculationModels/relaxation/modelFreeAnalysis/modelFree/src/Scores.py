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
__dateModified__ = "$dateModified: 2024-04-15 15:38:24 +0100 (Mon, April 15, 2024) $"
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

@jit(nopython=True)
def calculateReducedChiSquared(x2, dof):
    """
    The reduced Chi-squared provides a way to compare the goodness of fit of models with different numbers of parameters or to compare different datasets.
    It is particularly useful when comparing models with different complexities, as it accounts for the different degrees of freedom in the models.
    A smaller reduced Chi-squared value indicates a better fit of the model to the data.
    :param x2: float,  Chi-squared  value
    :param dof: int, the degrees of freedom (dof). dof is given by dof=N−k, where N is the number of observations and k is the number of parameters estimated from the data.
    :return: float. Reduced Chi-squared
    """
    return x2 / dof

@jit(nopython=True)
def calculateAIC(observed, predictions, numParams, errors=None):
    """
    Calculate the Akaike Information Criterion (AIC)  from data.
    """
    x2 = calculateChiSquared(observed, predictions, errors)
    return x2 + 2 * numParams

@jit(nopython=True)
def calculateAICcorrected(x2, observationsCount, paramsCount ):
    """
    Calculate the Akaike Information Criterion (AIC) corrected.
    The AICc is used for model selection when dealing with a relatively small sample size.
    It corrects for the bias that can occur in the AIC when the sample size is small relative to the number of parameters being estimated in the model.
    """
    AICc =  x2 + 2 * paramsCount * (paramsCount + 1) / (observationsCount - paramsCount - 1)
    return AICc

@jit(nopython=True)
def sse(observed, predictions):
    residuals = observed - predictions
    return np.sum(residuals**2)

@jit(nopython=True)
def rmse(observed, predictions):
    residuals = observed - predictions
    return np.sqrt(np.mean(residuals**2))



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
