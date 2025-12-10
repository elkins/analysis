"""Module Documentation here

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2025-03-06 16:18:32 +0000 (Thu, March 06, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from scipy import signal


def phaseRealData(data: np.ndarray, ph0: float = 0.0, ph1: float = 0.0,
                  pivot: float = 1.0) -> np.ndarray:
    # data is the (1D) spectrum data (real)
    # ph0 and ph1 are in degrees

    data = np.array(data)
    data = signal.hilbert(data)  # convert real to complex data in best way possible
    data = phaseComplexData(data, ph0, ph1, pivot)
    data = data.real

    return data


def phaseComplexData(data: np.ndarray, ph0: float = 0.0, ph1: float = 0.0,
                     pivot: float = 1.0) -> np.ndarray:
    # data is the (1D) spectrum data (complex)
    # ph0 and ph1 are in degrees

    data = np.array(data)

    ph0 *= np.pi / 180.0
    ph1 *= np.pi / 180.0
    pivot -= 1  # points start at 1 but code below assumes starts at 0

    npts = len(data)
    angles = ph0 + (np.arange(npts) - pivot) * ph1 / npts
    multipliers = np.exp(-1j * angles)

    data *= multipliers

    return data


def autoPhaseReal(data, fn, p0=0.0, p1=0.0):
    """
    Automatic linear phase correction from NmrGlue
    Parameters
    ----------
    data : ndarray
        Array of NMR intensity data.
    fn : str or function
        Algorithm to use for phase scoring. Built in functions can be
        specified by one of the following strings: "acme", "peak_minima"
    p0 : float
        Initial zero order phase in degrees.
    p1 : float
        Initial first order phase in degrees.

    Returns
    -------
    ndata : ndarray
        Phased NMR data.

    """
    import nmrglue as ng

    data = signal.hilbert(data)  # convert real to complex data in best way possible
    data = ng.proc_autophase.autops(data, fn, p0=p0, p1=p1)
    data = data.real
    return data
