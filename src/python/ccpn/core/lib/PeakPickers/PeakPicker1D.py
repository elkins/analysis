"""
Simple 1D PeakPicker; for testing only
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See http://www.ccpn.ac.uk/v3-software/downloads/license",
               )
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, http://doi.org/10.1007/s10858-016-0060-y"
                )
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2025-03-11 19:28:30 +0000 (Tue, March 11, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.core.lib.PeakPickers.PeakPickerABC import PeakPickerABC, SimplePeak
import numpy as np
from scipy.integrate import trapz
from lmfit.models import LorentzianModel, GaussianModel
from ccpn.util.UnitConverters import  _getSpUnitConversionArguments, _pnt2hz
from scipy.integrate import quad
from ccpn.util.Logging import getLogger

def _find1DMaxima(y, x, positiveThreshold, negativeThreshold=None, findNegative=False):
    """
    from https://gist.github.com/endolith/250860#file-readme-md which was translated from
    http://billauer.co.il/peakdet.html Eli Billauer, 3.4.05.
    Explicitly not copyrighted and any uses allowed.
    """
    maxtab = []
    mintab = []
    mn, mx = np.Inf, -np.Inf
    mnpos, mxpos = np.NaN, np.NaN
    lookformax = True
    if negativeThreshold is None: negativeThreshold = 0

    for i in np.arange(len(y)):
        this = y[i]
        if this > mx:
            mx = this
            mxpos = x[i]
        if this < mn:
            mn = this
            mnpos = x[i]
        if lookformax:
            if not findNegative:  # just positives
                this = abs(this)
            if this < mx - positiveThreshold:
                maxtab.append((float(mxpos), float(mx)))
                mn = this
                mnpos = x[i]
                lookformax = False
        else:
            if this > mn + positiveThreshold:
                mintab.append((float(mnpos), float(mn)))
                mx = this
                mxpos = x[i]
                lookformax = True
    filteredNeg = []
    for p in mintab:
        pos, height = p
        if height <= negativeThreshold:
            filteredNeg.append(p)
    filtered = []
    for p in maxtab:
        pos, height = p
        if height >= positiveThreshold:
            filtered.append(p)
    return filtered, filteredNeg

def _find1DPositiveMaxima(y, x, positiveThreshold=None):
    """
    The same routine as above but 100t times faster by just masking above the positive threshold
    """
    maxtab = []
    mintab = []
    mn, mx = np.Inf, -np.Inf
    mnpos, mxpos = np.NaN, np.NaN
    lookformax = True
    if positiveThreshold is None:
        positiveThreshold = float(np.median(y) + 1 * np.std(y))
    _y = y
    _x = x
    mask = y>=positiveThreshold
    y = y[mask]
    x = x[mask]
    for i in np.arange(len(y)):
        this = y[i]
        if this > mx:
            mx = this
            mxpos = x[i]
        if this < mn:
            mn = this
            mnpos = x[i]
        if lookformax:
            this = abs(this)
            if this < mx - positiveThreshold:
                maxtab.append((float(mxpos), float(mx)))
                mn = this
                mnpos = x[i]
                lookformax = False
        else:
            if this > mn + positiveThreshold:
                mintab.append((float(mnpos), float(mn)))
                mx = this
                mxpos = x[i]
                lookformax = True
    return maxtab, mintab

def _find1DMaximaIndexes(y, positiveThreshold=None):
    """
    The same routine as above but 100t times faster by just masking above the positive threshold
    """
    mn, mx = np.Inf, -np.Inf
    lookformax = True
    if positiveThreshold is None:
        positiveThreshold = float(np.median(y) + 1 * np.std(y))
    mask = y>=positiveThreshold
    y = y[mask]
    indexes = []
    for i in np.arange(len(y)):
        this = y[i]
        if this > mx:
            mx = this
        if this < mn:
            mn = this
        if lookformax:
            this = abs(this)
            if this < mx - positiveThreshold:
                indexes.append(i)
                mn = this
                lookformax = False
        else:
            if this > mn + positiveThreshold:
                indexes.append(i)
                mx = this
                lookformax = True
    return np.array(indexes)

def _getPositionsHeights(x, y, minimalHeightThreshold):
    maxtab, mintab = _find1DPositiveMaxima(y, x, minimalHeightThreshold)
    if len(maxtab) == 0:
        return [], []
    positions = np.array(maxtab).T[0]
    heights = np.array(maxtab).T[1]
    return positions, heights

class PeakPicker1D(PeakPickerABC):
    """A peak picker based on  Eli Billauer, 3.4.05. algorithm (see _findMaxima function).
    """

    peakPickerType = "PeakPicker1D"
    onlyFor1D = True

    def __init__(self, spectrum):
        super().__init__(spectrum=spectrum)
        self.noise = None
        application = spectrum.project.application
        self._doNegativePeaks = application.preferences.general.negativePeakPick1D


    def _setThresholdsFromSpectrum(self):
        """ Get the initial noise thresholds from the spectrum contour base"""
        if not self.positiveThreshold:
            self.positiveThreshold = self.spectrum.positiveContourBase

        if not self.negativeThreshold:
            self.negativeThreshold = self.spectrum.negativeContourBase

    def _isHeightWithinIntesityLimits(self, height):
        """ check if value is within the intensity limits. This is a different check from the noise Thresholds.
        Used when picking in a Gui Spectrum Display to make sure is picking only within the drawn box.
        """
        if self._intensityLimits is None or len(self._intensityLimits)==0:
            self._intensityLimits = (np.inf, -np.inf)
        value = min(self._intensityLimits) < height < max(self._intensityLimits)
        return value

    def _isPositionWithinLimits(self, pointValue):
        withinLimits = []
        ppmValue = self.spectrum.point2ppm(pointValue, axisCode=self.spectrum.axisCodes[0])
        excludePpmRegions = self._excludePpmRegions.get(self.spectrum.axisCodes[0])
        if excludePpmRegions is None:
            excludePpmRegions = [[0, 0], ]
        for limits in excludePpmRegions:
            if len(limits)>0:
                value = min(limits) < ppmValue < max(limits)
                withinLimits.append(not value)
        return all(withinLimits)


    def findPeaks(self, data):
        peaks = []
        start = int(self.spectrum.referencePoints[0])
        x = np.arange(start, start + len(data))
        self._setThresholdsFromSpectrum()
        maxValues, minValues = _find1DMaxima(y=data, x=x,
                                             positiveThreshold=self.positiveThreshold,
                                             negativeThreshold=self.negativeThreshold,
                                             findNegative=self._doNegativePeaks)
        for position, height in maxValues:
            if self._isHeightWithinIntesityLimits(height) and self._isPositionWithinLimits(position):
                points=(float(position - start),)
                pk = SimplePeak(points=points, height=float(height))
                peaks.append(pk)
        if self._doNegativePeaks:
            for position, height in minValues:
                if self._isHeightWithinIntesityLimits(height) and self._isPositionWithinLimits(position):
                    points = (float(position - start),)
                    pk = SimplePeak(points=(float(position),), height=float(height))
                    peaks.append(pk)

        return peaks

    def fitExistingPeaks(self, peaks, calculateVolume=False):
        """Refit the current selected peaks.
        Must be called with peaks that belong to this peakList
        """
        from ccpn.core.PeakList import GAUSSIANMETHOD, LORENTZIANMETHOD, PARABOLICMETHOD # here for bad imports

        self._models = {
                                GAUSSIANMETHOD: GaussianModel,
                                LORENTZIANMETHOD: LorentzianModel
                                }

        spectrum = peaks[0].spectrum
        x = np.arange(1, spectrum.pointCounts[0]+1)
        y = spectrum.intensities
        npoints, sfs, sws, refppms, refpts = _getSpUnitConversionArguments(spectrum)
        npoint, sf, sw, refppm, refpt = npoints[0], sfs[0], sws[0], refppms[0], refpts[0]
        modelCls = self._models.get(self.fitMethod, LorentzianModel)
        if self.fitMethod not in self._models:
            getLogger().info(f'Selected Fitting model {self.fitMethod} is not available for this PeakPicker {self}. Used {modelCls.name} instead')

        for peak in peaks:
            height = peak.height
            position = int(peak.pointPositions[0])
            # Create a  model with fixed height and position
            model = modelCls()
            params = model.make_params(amplitude=height, center=position)
            # Fit the Lorentzian model to the data with fixed parameters
            result = model.fit(y, params, x=x)
            # Extract the param values from the fitted model
            fwhm = result.params['fwhm'].value
            amplitude, center, sigma = result.params['amplitude'].value, result.params['center'].value, result.params['sigma'].value
            fwhmLeft = center - fwhm / 2
            fwhmRight = center + fwhm / 2
            # covert points to Hz
            leftHz = _pnt2hz(fwhmLeft, npoint, sf, sw, refppm, refpt)
            rightHz = _pnt2hz(fwhmRight, npoint, sf, sw, refppm, refpt)
            hwhmHz = abs(rightHz - leftHz)
            peak.lineWidths = [hwhmHz]

            # calculate volume from the traps. Quad method is much slower
            if calculateVolume:
                try:
                    indicesInRange = (x >= fwhmLeft) & (x <= fwhmRight)
                    xRange = x[indicesInRange]
                    yRange = y[indicesInRange]
                    volume = float(trapz(yRange, xRange))
                    peak.volume = abs(volume)
                except Exception as err:
                    peak.volume = None
                    getLogger().warn(f'Cannot calculate volume for peak {peak}. {err}')

PeakPicker1D._registerPeakPicker()
