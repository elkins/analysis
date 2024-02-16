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
__dateModified__ = "$dateModified: 2024-02-16 17:53:11 +0000 (Fri, February 16, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:42 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np

def _ppm2pnt(ppm, npoints, sf, sw, refppm, refpt):
    t = - npoints * sf / float(sw)
    pnt = t*(ppm - refppm) + refpt
    return pnt

def _ppm2hz(ppm, npoints, sf, sw, refppm, refpt):
    pnt = _ppm2pnt(ppm, npoints, sf, sw, refppm, refpt)
    hz = _pnt2hz(pnt, npoints, sf, sw, refppm, refpt)
    return hz

def _pnt2ppm(pnt, npoints, sf, sw, refppm, refpt):
    t = - npoints * sf / float(sw)
    ppm = (pnt - refpt)/t + refppm
    return ppm

def _pnt2hz(pnt, npoints, sf, sw, refppm, refpt):
    t = - npoints / float(sw)
    hz = (pnt - refpt)/t + sf*refppm
    return hz

def _hz2pnt(hz, npoints, sf, sw, refppm, refpt):
    t = - npoints / float(sw)
    pnt = t*(hz - sf*refppm) + refpt
    return pnt

def _hz2ppm(hz, npoints, sf, sw, refppm, refpt):
    pnt = _hz2pnt(hz, npoints, sf, sw, refppm, refpt)
    ppm = _pnt2ppm(pnt, npoints, sf, sw, refppm, refpt)
    return ppm

def _hzXpnt(sw, npoints):
    return sw/npoints

def _hzXppm(sw_ppm, npoints):
    return sw_ppm/npoints

## time conversions

def _sec2pts(sec, sw):
    return sec * sw

def _pts2sec(pts, sw):
    return pts * 1. / sw

def _ms2pts(ms, sw):
    return ms * sw / 1.e3

def _pts2ms(pts, sw):
    return pts * 1.e3 / sw

def _us2pts(us, sw):
    return us * sw / 1.e6

def _pts2us(pts, sw):
    return pts * 1.e6 / sw

## scales

def ppmScale(ppmLimits, npoints):
    """
    :param ppmLimits: spectrum ppm limits
    :param npoints: total number of points
    :return: an array in ppm scale ("backwards")
    """
    x0, x1 = max(ppmLimits), min(ppmLimits)
    return np.linspace(x0, x1, npoints)

def hzScale():
    pass

def secScale():
    pass

def msScale():
    pass

def usScale():
    pass


def _getSpUnitConversionArguments(spectrum):
    """
    :param spectrum:
    :return: tuple of tuples containing the spectrum properties needed for unit conversions
    """
    npoints = spectrum.pointCounts
    sf = spectrum.spectrometerFrequencies
    sw = spectrum.spectralWidthsHz
    refppm = spectrum.referenceValues
    refpt = spectrum.referencePoints
    return npoints, sf, sw, refppm, refpt


class TimeConverter:
    @staticmethod
    def secToNs(seconds):
        return seconds * 1e9

    @staticmethod
    def nsToSec(nanoseconds):
        return nanoseconds / 1e9

    @staticmethod
    def secToPs(seconds):
        return seconds * 1e12

    @staticmethod
    def psToSec(picoseconds):
        return picoseconds / 1e12

    @staticmethod
    def nsToPs(nanoseconds):
        return nanoseconds * 1e3

    @staticmethod
    def psToNs(picoseconds):
        return picoseconds / 1e3
