"""
This module defines the various fitting functions for Series Analysis.
Some functions are vectorised and called recursively by the Minimiser (see Minimiser Object)

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2023"
__credits__ = ("Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2023-11-13 10:25:55 +0000 (Mon, November 13, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from ccpn.util.Logging import getLogger


def _checkValidValues(values):
    """
    Check if values contain 0, None or np.nan
    :param values: list
    :return: bool
    """
    notAllowed = [0, None, np.nan]
    for i in values:
        if i in notAllowed:
            return False
    return True

def peakErrorBySNRs(snrs, factor=1, power=-2, method='sum'):
    """
    Calculate error by signal to noise ratio and a scaling factor.
    :param snrs: list of floats, list of signal to noise ratio for Peaks
    :param factor: float, correction factor.
    :param power: float/int, the power value. -2 as default
    :param method: str, the calculation mode for combining observation values. One of mean, sum, std, median
    :return: float or None
    Ref.: 1) derived from eq. 4 from Kharchenko, V., et al. Dynamic 15N{1H} NOE measurements: a tool for studying protein dynamics.
             J Biomol NMR 74, 707–716 (2020). https://doi.org/10.1007/s10858-020-00346-6
    """
    if not _checkValidValues(snrs+[factor]):
        return
    defaultMethod = 'sum'
    allowedMethods = ['mean', 'sum', 'std', 'median']
    if method not in allowedMethods:
        getLogger().warning(f'Method not available. Reverted to default: {defaultMethod}. Use one of {allowedMethods}')
        method = defaultMethod
    func = getattr(np, method, np.sum)
    values = np.array(snrs, dtype=float)
    inner = func(np.power(values, power))
    error = abs(factor) * np.sqrt(inner)
    return error

def calculateUncertaintiesError(v1,v2, ev1, ev2):
    """
    Calculate the Uncertainties errors for a ratio of two values and their original errors
    :return:  float. the ratio error
    """
    try:
        return (ev1 / v1 + ev2 / v2) * v2 / v1
    except Exception:
        return

def calculateUncertaintiesProductError(v1,v2, ev1, ev2):
    """
    Calculate the Uncertainties errors for a product of two values and their original errors
    :return:  float. the ratio error
    """
    try:
        return (ev1 * v1 + ev2* v2) / v2 * v1
    except Exception:
        return

def _scaleMinMaxData(data, minMaxRange=(1.e-5, 1)):
    """
    :param data: 1d Array
    :return 1d Array
    Scale data  to value minMaxRange"""
    from sklearn.preprocessing import MinMaxScaler
    data = data.reshape(-1, 1)
    scaler = MinMaxScaler(feature_range=minMaxRange)
    scaler = scaler.fit(data)
    scaledData = scaler.transform(data)
    scaledData = scaledData.flatten()
    return scaledData

def _scaleStandardData(data, with_mean=True, with_std=True):
    """
    :param data: 1d Array
    :return 1d Array
    Scale data to StandardScale; Standardise features by removing the mean and scaling to unit variance.
    see sklearn StandardScaler for more information"""
    from sklearn.preprocessing import StandardScaler
    data = data.reshape(-1, 1)
    scaler = StandardScaler(with_mean=with_mean, with_std=with_std)
    scaler = scaler.fit(data)
    scaledData = scaler.transform(data)
    return scaledData.flatten()

def aad(data, axis=None):
    """AAD as --average absolute deviation-- also known as the --mean absolute deviation (MAD) --.
     Called AAD to don't be confused with the -- median absolute difference --, also known as MAD!"""
    return np.mean(np.absolute(data - np.mean(data, axis)), axis)

