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
__dateModified__ = "$dateModified: 2023-11-10 15:58:41 +0000 (Fri, November 10, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from lmfit import lineshapes as ls
import numpy as np
from ccpn.util.Logging import getLogger
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import ccpn.framework.lib.experimentAnalysis.ExperimentConstants as constants
from math import pi
from random import random, randint
from math import sqrt, exp
import pandas as pd

## Common built-in functions.
gaussian_func    = ls.gaussian
lorentzian_func  = ls.lorentzian
linear_func      = ls.linear
parabolic_func   = ls.parabolic
lognormal_func   = ls.lognormal
pearson7_func    = ls.pearson7
students_t_func  = ls.students_t
powerlaw_func    = ls.powerlaw

CommonStatFuncs = {
                sv.MEAN     : np.mean,
                sv.MEDIAN   : np.median,
                sv.STD      : np.std,
                sv.VARIANCE : np.var,
                }


########################################################################################################################
########################            Ligand - Receptor Binding equations        #########################################
########################################################################################################################

"""
    Below a set of library functions used in the Series Analysis, in particular the ChemicalShiftMapping module (CSM).
    They are called recursively from each specific Fitting Model and its Minimiser object.
    Function Arguments (*args) are used/inspected to set the attr to the Minimiser object and other functionality.
    <-> WARNING <-> : Do not change the function signature without amending the Minimiser default parameters or 
    will result in a broken Model. E.g.: oneSiteBinding_func(x, Kd, BMax) to oneSiteBinding_func(x, kd, bmax) will break
    See MinimiserModel _defaultParams for more info. 

"""

def oneSiteBinding_func(x, Kd, BMax):
    """
    The one-site Specific Binding equation for a saturation binding experiment.

    Y = Bmax*X/(Kd + X)

    :param x:   1d array. The data to be fitted.
                In the CSM it's the array of deltas (deltas among chemicalShifts, CS, usually in ppm positions)

    :param Kd:  Defines the equilibrium dissociation constant. The value to get a half-maximum binding at equilibrium.
                In the CSM the initial value is calculated from the ligand concentration.
                The ligand concentration is inputted in the SpectrumGroup Series values.

    :param BMax: Defines the max specific binding.
                In the CSM the initial value is calculated from the CS deltas.
                Note, The optimised BMax will be (probably always) larger than the measured CS.

    :return:    Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
                When plotting BMax is the Y axis, Kd the X axis.
    """
    return (BMax * x) / (x + Kd)


def oneSiteNonSpecBinding_func(x, NS, B=1):
    """
    The  one-site non specific Binding equation for a saturation binding experiment.

    Y = NS*X + B

    :param x:  1d array. The data to be fitted.
               In the CSM it's the array of deltas (deltas among chemicalShifts, CS, usually in ppm positions)

    :param NS: the slope of non-specific binding
    :param B:  The non specific binding without ligand.

    :return:   Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
               When plotting BMax is the Y axis, Kd the X axis.
    """

    YnonSpecific = NS * x + B

    return YnonSpecific


def fractionBound_func(x, Kd, BMax):
    """
    The one-site fractionBound equation for a saturation binding experiment.
    V2 equation.
    Y = BMax * (Kd + x - sqrt((Kd + x)^2 - 4x))

    ref: 1) In-house calculations (V2 - wayne - Double check )

    :param x:   1d array. The data to be fitted.
                In the CSM it's the array of deltas (deltas among chemicalShifts, CS, usually in ppm positions)

    :param Kd:  Defines the equilibrium dissociation constant. The value to get a half-maximum binding at equilibrium.
                In the CSM the initial value is calculated from the ligand concentration.
                The ligand concentration is inputted in the SpectrumGroup Series values.

    :param BMax: Defines the max specific binding.
                In the CSM the initial value is calculated from the CS deltas.
                Note, The optimised BMax will be (probably always) larger than the measured CS.

    :return:    Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
                When plotting BMax is the Y axis, Kd the X axis.
    """

    qd = np.sqrt((Kd+x)**2 - 4*x)
    Y = BMax * (Kd + x - qd)

    return Y

def fractionBoundWithPro_func(x, Kd, BMax, T=1):
    """
    The one-site fractionBound equation for a saturation binding experiment.
    V2 equation.
    Y = BMax * ( (P + x + Kd) - sqrt(P + x + Kd)^2 - 4*P*x)) / 2 * P

    ref: 1) M.P. Williamson. Progress in Nuclear Magnetic Resonance Spectroscopy 73, 1–16 (2013).


    :param x:   1d array. The data to be fitted.
                In the CSM it's the array of deltas (deltas among chemicalShifts, CS, usually in ppm positions)

    :param Kd:  Defines the equilibrium dissociation constant. The value to get a half-maximum binding at equilibrium.
                In the CSM the initial value is calculated from the ligand concentration.
                The ligand concentration is inputted in the SpectrumGroup Series values.

    :param BMax: Defines the max specific binding.
                In the CSM the initial value is calculated from the CS deltas.
                Note, The optimised BMax will be (probably always) larger than the measured CS.
                
    :param T: Target concentration.

    :return:    Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
                When plotting BMax is the Y axis, Kd the X axis.
    """

    Y = BMax * ((T + x + Kd) - np.sqrt((T + x + Kd)**2 - 4 * T * x)) / 2 * T
    return Y


def cooperativity_func(x, Kd, BMax, Hs):
    """
    The cooperativity equation for a saturation binding experiment.

    Y = Bmax*X^Hs/(Kd^Hs + X^Hs)

    :param x:   1d array. The data to be fitted.
                In the CSM it's the array of deltas (deltas among chemicalShifts, CS, usually in ppm positions)

    :param Kd:  Defines the equilibrium dissociation constant. The value to get a half-maximum binding at equilibrium.
                In the CSM the initial value is calculated from the ligand concentration.
                The ligand concentration is inputted in the SpectrumGroup Series values.

    :param BMax: Defines the max specific binding.
                In the CSM the initial value is calculated from the CS deltas.
                Note, The optimised BMax will be (probably always) larger than the measured CS.
    :param Hs: hill slope. Default 1 to assume no cooperativity.
                Hs = 1: ligand/monomer binds to one site with no cooperativity.
                Hs > 1: ligand/monomer binds to multiple sites with positive cooperativity.
                Hs < 0: ligand/monomer binds to multiple sites with variable affinities or negative cooperativity.
    :return:    Y array same shape of x. Represents the points for the fitted curve Y to be plotted.
                When plotting BMax is the Y axis, Kd the X axis.
    """

    Y =  (BMax * x **Hs) / (x**Hs + Kd**Hs)
    return Y


########################################################################################################################
########################                     Various Fitting Functions                       ###########################
########################################################################################################################

def inversionRecovery_func(x, decay=1, amplitude=1):
    """ Function used to describe the T1 decay
    """
    decay = ls.not_zero(decay)
    return amplitude * (1 - np.exp(-x / decay))

def exponentialDecay_func(x, decay=1, amplitude=1):
    """ Function used to describe the T2 decay
    """
    decay = ls.not_zero(decay)

    return amplitude * np.exp(-x / decay)

def onePhaseDecay_func(x, rate=1.0, amplitude=1.0):
    """ Function used to describe the  decay rate in an exponential decay model
    rate is the rate constant, expressed in reciprocal of the X axis time units.
     If X is in seconds, then rate is expressed in inverse seconds, (Spower-1)
    """
    rate = ls.not_zero(rate)
    result = amplitude * np.exp(-rate * x)
    return result

def onePhaseDecayPlateau_func(x, rate=1, amplitude=1, plateau=0):
    """ Function used to describe the  decay rate in an exponential decay model with the extra argument plateau.
    rate is the rate constant, expressed in reciprocal of the X axis time units.
     If X is in seconds, then rate is expressed in inverse seconds, (Spower-1)
     Y=(Y0 - Plateau)*exp(-K*X) + Plateau
    """
    rate = ls.not_zero(rate)
    result = (amplitude - plateau) * np.exp(-rate * x) + plateau
    return result

def exponentialGrowth_func(x, amplitude, decay):
    return amplitude * np.exp(decay * x)

def blank_func(x, argA, argB):
    """
    A mock fitting function. Used for a Blank model.
    :param x: example argument. Not in use.
    :param argA: example argument. Not in use.
    :param argB: example argument. Not in use.
    :return: None
    """
    return

########################################################################################################################
########################                     Various Calculation Functions                   ###########################
########################################################################################################################

def r2_func(y, redchi):
    """
    Calculate the R2 (called from the minimiser results).
    :param redchi: Chi-square. From the Minimiser Obj can be retrieved as "result.redchi"
    :return: r2
    """
    var = np.var(y, ddof=2)
    if var != 0:
        r2 = 1 - redchi / var
        return r2


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

def _formatValue(value, maxInt=3, floatPrecision=3, expDigits=1):
    """Convert value to numeric when possible """
    try:
        if isinstance(value, (float, int)):
            if len(str(int(value))) > maxInt:
                value = np.format_float_scientific(value, precision=floatPrecision, exp_digits=expDigits)
            else:
                value = round(value, 4)
    except Exception as ex:
        getLogger().debug2(f'Impossible to format {value}. Error:{ex}')
    return value

def calculateRollingAverage(data, windowSize=10):
    """
    Get the rolling average of an array
    :param data:
    :param windowSize: the number of point to use for calculating the average
    :return: array of same length as the input data
    """
    window = np.ones(int(windowSize))/float(windowSize)
    return np.convolve(data, window,  mode='same')


def aad(data, axis=None):
    """The mean absolute deviation. Do not confuse with the median absolute difference. """
    return np.mean(np.absolute(data - np.mean(data, axis)), axis)

