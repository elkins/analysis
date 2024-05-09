"""
This module contains the equations for calculating the theoretical Rates values.
These functions are the lowest level of computation, they need to be quickly accessed and executed.
ABCs for these are inefficients. Do not beautify in a class per rate!

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

import math
import numpy as np
from numba import jit
from collections import OrderedDict
from ccpn.framework.lib.experimentAnalysis.ExperimentConstants import GAMMA_HN
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv


class RatesHandler:
    """
    - A class to handle the execution of the various theoretical Rate calculations.
    - Functions are registered at the bottom of this module.
    - The class attr "_cached" is  used to store the cached results of function calls to avoid redundant computations. Before calling the rate function,
        it checks if the result for the given inputs (name, args, kwargs) exists in the memoization cache.  If it does, the cached result is returned;
        otherwise, computes the result, cache it, and return it.
    """

    rates = OrderedDict() # store the various theoretical calculation functions
    _cached = {}  # Memoization cache

    @classmethod
    def add(cls, name, rate):
        """
        Add a rate function to the RatesHandler.
        :param name: (str): The name of the rate function.
        :param rate: (callable): The rate function to be added.
        :return:
        """
        if name not in cls.rates:
            cls.rates[name] = rate

    @classmethod
    def get(cls, name):
        """
        Get the rate function
        :param name: (str): The name of the rate function.
        :return rate: (callable): The rate function to be called.
        """
        return cls.rates.get(name)

    @classmethod
    def calculate(cls, name, *args, **kwargs):
        """
        :param name: (str): The name of the rate function to run.
        :param args: Variable length argument list to be passed to the rate function.
        :param kwargs: Arbitrary keyword arguments to be passed to the rate function.
        :return: The result of executing the rate function with the given arguments.
        """

        rateFunc = cls.get(name)
        if rateFunc:
            # Check if the signature has been seen previously
            key = (name, args, tuple(kwargs.items()))
            if key in cls._cached: # check this way because is much faster than dict.get(x) for a large dict
                return cls._cached[key]
            else:
                # calculate the rate and add the signature/result to cache
                result = rateFunc(*args, **kwargs)
                cls._cached[key] = float(result)
                return result
        else:
            #keep the else, maybe add to logger?
            return None

    def _flushCache(self):
        self._cached = {}

# --------- Define the various Equations --------- #

# @jit(nopython=True)
def _calculateR1(d2, c2, j0, jH, jHmN, jHpN, jN):
    """
    Calculate the longitudinal relaxation rate (R1)
    Eq. 1 The role of protein motions in molecular recognition: insights from heteronuclear NMR relaxation measurements. R. Andrew Atkinson, Bruno Kieffer.
    Progress in Nuclear Magnetic Resonance Spectroscopy 44 (2004) 141–187.
    :param d2: float, the d^2 factor
    :param c2: float, the c^2 factor
    :param jN: float, the JWN
    :param jHpN: float, the JWH + JWN
    :param jHmN: float, the JWH - JWN
    :return:  theoretical R1
    """
    r1 = (3*d2*jN) + (d2*jHmN) + (6*d2*jHpN) + (c2*jN)
    return r1

# @jit(nopython=True)
def _calculateR2(d2, c2, j0, jH, jHmN, jHpN, jN, rex=None):
    """
    Eq. 2 The role of protein motions in molecular recognition: insights from heteronuclear NMR relaxation measurements. R. Andrew Atkinson, Bruno Kieffer.
    Progress in Nuclear Magnetic Resonance Spectroscopy 44 (2004) 141–187.
    Calculate the transverse relaxation rate (R2)
     :param d2: float, the d^2 factor
    :param c2: float, the c^2 factor
    :param jN: float, the JWN
    :param jHpN: float, the JWH + JWN
    :param jHmN: float, the JWH - JWN
    :param rex: float the Rex value
    :return:  theoretical R2
    """
    _a = (2 * d2 * j0)
    _b = ((3 * d2) / 2) * jN
    _c = (d2 / 2) * jHmN
    _d = 3 * d2 * jH
    _e = 3 * d2 * jHpN
    _f = ((2 * c2) / 3) * j0
    _g = (c2 / 2) * jN
    r2 = _a + _b + _c + _d + _e + _f + _g
    if rex is not None:
        r2 += rex
    return r2

# @jit(nopython=True)
def _calculateHetNoe(d2, c2, j0, jH, jHmN, jHpN, jN):
    """
    Calculate the steady-state NOE enhancement
    :param d2: float, the d^2 factor
    :param c2: float, the c^2 factor. Not used, only for signature consistency
    :param jN: float, the JWN.  Not used, only for signature consistency
    :param jHpN: float, the JWH + JWN
    :param jHmN: float, the JWH - JWN
    :param gammaHN: float, ratio of gammaH over gammaN. Gammas are fixed defined in the constants
    :param t1: float 1 over R1, experimental R1.
    :return: float theoretical Noe
    """
    r1 = _calculateR1(d2, c2, j0, jH, jHmN, jHpN, jN)
    if r1 == 0:
        return 1
    t1 = 1/r1
    hetNoe = 1.0 + (d2 * GAMMA_HN * t1 * ((6 * jHpN) - jHmN))
    return hetNoe

# @jit(nopython=True)
def _legendreP2(x):
    """
    Calculate the 2nd degree Legendre polynomial of x. Convenient function used in calculateETAxy, calculateETAz
    :param x: (float): The value at which to evaluate the Legendre polynomial. For the Etas is x is the cosBeta
    :return: The value of Legendre polynomial of degree 2 at x.
    """
    return 0.5 * (3 * x**2 - 1)

# @jit(nopython=True)
def calculateETAxy(d2, c2, j0, jH, jHmN, jHpN, jN, beta=20):
    """
    Calculate the transverse relaxation rate etaXy.
    Eq 24 as Tjandra.  The role of protein motions in molecular recognition: insights from heteronuclear NMR relaxation measurements. R. Andrew Atkinson, Bruno Kieffer.
     Progress in Nuclear Magnetic Resonance Spectroscopy 44 (2004) 141–187.

    :param beta: Angle in degree.
     :param d2: float, the d^2 factor
    :param c2: float, the c^2 factor
    :param j0: float
    :param jN: float
    :return: etaXy: Transverse relaxation rate.
    """

    beta = math.radians(beta)
    p2 = _legendreP2(np.cos(beta))
    ETAxy = - (np.sqrt(3)/6) * p2 * np.sqrt(d2) * np.sqrt(c2) * (4*j0 + 3*jN)
    return ETAxy

# @jit(nopython=True)
def calculateETAz(d2, c2, j0, jH, jHmN, jHpN, jN, beta=20):
    """
    Calculate the transverse relaxation rate etaZ.
    Eq 26 as Tjandra.  The role of protein motions in molecular recognition: insights from heteronuclear NMR relaxation measurements. R. Andrew Atkinson, Bruno Kieffer.
     Progress in Nuclear Magnetic Resonance Spectroscopy 44 (2004) 141–187.

    :param beta: Angle in degree.
    :param d2: float, the d^2 factor
    :param c2: float, the c^2 factor
    :param jN: float
    :return: ETAz: Transverse relaxation rate.
    """
    beta = math.radians(beta)
    p2 = _legendreP2(np.cos(beta))
    ETAz = - (np.sqrt(3)) * p2 * np.sqrt(d2) * (np.sqrt(c2)*jN)
    return ETAz

# @jit(nopython=True)
def calculateREX(d2, c2, j0, jH, jHmN, jHpN, jN):
    """
    Calculate the transverse relaxation rate etaZ.
    Eq 27 as Tjandra.  The role of protein motions in molecular recognition: insights from heteronuclear NMR relaxation measurements. R. Andrew Atkinson, Bruno Kieffer.
     Progress in Nuclear Magnetic Resonance Spectroscopy 44 (2004) 141–187.

    :param beta: Angle in radians.
    :param d2: float, the d^2 factor
    :param c2: float, the c^2 factor
    :param jN: float
    :return: ETAz: Transverse relaxation rate.
    """
    ETAxy = calculateETAxy(d2, c2, j0, jH, jHmN, jHpN, jN)
    ETAz = calculateETAz(d2, c2, j0, jH, jHmN, jHpN, jN)
    rex = (3*d2 +c2) * (2/3*j0 - (ETAxy/ETAz - 1/2)*jN)
    return rex

# --------- Ends of Rate Functions --------- #

## Register the rate functions
RatesHandler.add(sv.R1, _calculateR1)
RatesHandler.add(sv.R2, _calculateR2)
RatesHandler.add(sv.HETNOE, _calculateHetNoe)
RatesHandler.add(sv.ETAXY, calculateETAxy)
RatesHandler.add( sv.ETAZ, calculateETAz)
RatesHandler.add(sv.REX, calculateREX)

## Quick testing
if __name__ == "__main__":
    ratesHandler = RatesHandler()
    rates = [sv.R1, sv.R2, sv.HETNOE]
    np.random.seed(42) # just for testing the cache
    for rate in rates:
        value = ratesHandler.calculate(sv.R1, *np.random.rand(7))
        print(f'{rate} = {value}')
