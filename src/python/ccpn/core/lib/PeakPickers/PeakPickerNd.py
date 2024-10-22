"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
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
__dateModified__ = "$dateModified: 2024-10-11 11:32:03 +0100 (Fri, October 11, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2021-02-08 11:42:15 +0000 (Mon, February 08, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

import math
import numpy as np
from typing import Sequence
from collections import Counter
import matplotlib.pyplot as plt

from ccpn.core.lib.PeakPickers.PeakPickerABC import PeakPickerABC, SimplePeak
from ccpn.util.traits.CcpNmrTraits import CFloat, CInt, CBool, CList, Dict
from ccpn.util.Logging import getLogger
from ccpnc.peak import Peak as CPeak


GAUSSIANMETHOD = 'gaussian'
LORENTZIANMETHOD = 'lorentzian'
PARABOLICMETHOD = 'parabolic'
PICKINGMETHODS = (GAUSSIANMETHOD, LORENTZIANMETHOD, PARABOLICMETHOD)

_DEBUG = False
_DEBUGPLOT = False
_MAXGROUPING = 5


# these functions could probably go into a .lib somewhere
def _makeGauss(N, sigma, mu, height):
    """Generate a gaussian distribution from given parameters
    """
    k = height
    s = -1.0 / (2 * sigma * sigma)
    return k * np.exp(s * (N - mu) * (N - mu))


def _makeLorentzian(N, fwhm, mu, height):
    """Generate a lorentzian distribution from given parameters
    """
    k = height
    return k * (0.5 * fwhm)**2 / ((N - mu) * (N - mu) + ((0.5 * fwhm)**2))


def _makeParabola(x, fwhm, mu, height):
    a = -2 * height / fwhm**2
    return a * (x - mu)**2 + height


def _sigma2fwhm(sigma):
    return sigma * np.sqrt(8 * np.log(2))


def _fwhm2sigma(fwhm):
    return fwhm / np.sqrt(8 * np.log(2))


def _logp(z):
    return np.log(z / (1 - z))


def _checkOverlap(arr1, arr2):
    # Check if two arrays overlap
    min_overlap = np.maximum(arr1[0], arr2[0])
    max_overlap = np.minimum(arr1[1], arr2[1])
    return np.all(max_overlap >= min_overlap)


def _plotGaussLorentzGroup(data, fwhm2sigma, logp, make_gauss, make_lorentzian, method, regionArray, result):
    try:
        fig = plt.figure(figsize=(10, 8), dpi=100)
        axS = fig.gca()
        # plot the centre-line of the pick-region
        axS.plot(data[data.shape[0] // 2,
                 regionArray[0, 1]:regionArray[1, 1],
                 data.shape[2] // 2])
        for _intensity, _centre, _linewidth in result:
            _cc = _centre[1] - regionArray[0, 1]
            axS.scatter(_cc, _intensity, marker='+', s=200,
                        linewidths=2, c='red')
            # make a 2d peak
            lim = 3 * _linewidth[1] / 2.0
            xx = np.linspace(0.05, 0.95, 25)
            # make a scale biased towards the centre
            xxLog = -logp(xx) / logp(xx[0:1])[0]  # [-1, 1]
            xxPpm = lim * xxLog
            if method == 0:
                vals = make_gauss(xxPpm, fwhm2sigma(_linewidth[1]), 0, _intensity)
            else:
                vals = make_lorentzian(-3 * xxLog, 2, 0, _intensity)  # [-3, 3]
            axS.plot(xxPpm + _cc, vals, c='orange', linewidth=2)
        axS.grid()
    except Exception:
        ...


def _plotGaussLorentz(data, fwhm2sigma, localRegionArray, localResult, logp, make_gauss, make_lorentzian,
                      method):
    try:
        _intensity, _centre, _linewidth = localResult[0]
        _cc = _centre[1] - localRegionArray[0, 1]
        fig = plt.figure(figsize=(10, 8), dpi=100)
        axS = fig.gca()
        axS.plot(data[data.shape[0] // 2,
                 localRegionArray[0, 1]:localRegionArray[1, 1],
                 data.shape[2] // 2])
        axS.scatter(_cc, _intensity, marker='+', s=200,
                    linewidths=2, c='red')
        # make a 2d peak
        lim = 3 * _linewidth[1] / 2.0
        xx = np.linspace(0.05, 0.95, 25)
        # make a scale biased towards the centre
        xxLog = -logp(xx) / logp(xx[0:1])[0]  # [-1, 1]
        xxPpm = lim * xxLog
        if method == 0:
            vals = make_gauss(xxPpm, fwhm2sigma(_linewidth[1]), 0, _intensity)
        else:
            vals = make_lorentzian(-3 * xxLog, 2, 0, _intensity)  # [-3, 3]
        axS.plot(xxPpm + _cc, vals, c='orange', linewidth=2)
        axS.grid()
    except Exception:
        ...


def _plotParabolic(data, logp, make_parabola, regionArray, result):
    try:
        fig = plt.figure(figsize=(10, 8), dpi=100)
        axS = fig.gca()
        # plot the centre-line of the pick-region
        axS.plot(data[data.shape[0] // 2,
                 regionArray[0, 1]:regionArray[1, 1],
                 data.shape[2] // 2])
        for _intensity, _centre, _linewidth in result:
            _cc = _centre[1] - regionArray[0, 1]
            axS.scatter(_cc, _intensity, marker='+', s=200,
                        linewidths=2, c='red')
            # make a 2d peak
            lim = 3 * _linewidth[1] / 2.0
            xx = np.linspace(0.05, 0.95, 25)
            # make a scale biased towards the centre
            xxLog = -logp(xx) / logp(xx[0:1])[0]  # [-1, 1]
            xxPpm = lim * xxLog
            vals = make_parabola(xxPpm, _linewidth[1], 0, _intensity)
            dd = np.array([xxPpm + _cc, vals])
            if _intensity >= 0:
                # remove the negative part of the trace
                dd = dd[:, dd[1, :] > 0]
            else:
                dd = dd[:, dd[1, :] < 0]
            # small tweak so the end-points go to zero, not really necessary though
            left, right = np.copy(dd[:, 0]), np.copy(dd[:, -1])
            left[1] = right[1] = 0
            dd = np.concatenate((left.reshape(-1, 1), dd, right.reshape(-1, 1)), axis=1)
            axS.plot(dd[0], dd[1], c='orange', linewidth=2)
        axS.grid()
    except Exception:
        ...


#=========================================================================================
# PeakPickerNd
#=========================================================================================

class PeakPickerNd(PeakPickerABC):
    """A simple Nd peak picker for testing
    """

    peakPickerType = "PeakPickerNd"
    onlyFor1D = False

    # list of peakPicker attributes that need to be stored/restored
    # these pertain to a particular peakPicker subclass
    # this cannot contain items that are not JSON serialisable

    noise = CFloat(allow_none=True, default_value=None)
    minimumLineWidth = CList(allow_none=True, default_value=[])
    checkAllAdjacent = CBool(allow_none=True, default_value=True)
    singularMode = CBool(allow_none=True, default_value=False)
    halfBoxFindPeaksWidth = CInt(allow_none=True, default_value=4)
    halfBoxSearchWidth = CInt(allow_none=True, default_value=4)
    halfBoxFitWidth = CInt(allow_none=True, default_value=4)
    searchBoxDoFit = CBool(allow_none=True, default_value=True)
    setLineWidths = CBool(allow_none=True, default_value=True)
    searchBoxMode = CBool(allow_none=True, default_value=True)
    searchBoxWidths = Dict(allow_none=True, default_value={})

    def __init__(self, spectrum):
        super().__init__(spectrum=spectrum)

        self.positiveThreshold = spectrum.positiveContourBase if spectrum.includePositiveContours else None
        self.negativeThreshold = spectrum.negativeContourBase if spectrum.includeNegativeContours else None
        self.fitMethod = PARABOLICMETHOD
        self._hbsWidth = None
        self._hbfWidth = None
        self.findFunc = None

    def findPeaks(self, data) -> list:
        """find the peaks in data (type numpy-array) and return as a list of SimplePeak instances
        note that SimplePeak.points are ordered z,y,x for nD, in accordance with the numpy nD data array

        called from the pickPeaks() method

        any required parameters that findPeaks method needs should be initialised/set before using the
        setParameters() method; i.e.:
                myPeakPicker = PeakPicker(spectrum=mySpectrum)
                myPeakPicker.setParameters(dropFactor=0.2, positiveThreshold=1e6, negativeThreshold=None)
                corePeaks = myPeakPicker.pickPeaks(axisDict={'H':(6.0,11.5),'N':(102.3,130.0)}, spectrum.peaklists[-1])

        :param data: nD numpy array
        :return list of SimplePeak instances
        """

        # find the list of peaks in the region
        allPeaksArray, allRegionArrays, regionArray, _ = self._findPeaks(data, self.positiveThreshold,
                                                                         self.negativeThreshold)
        if allPeaksArray is None or allPeaksArray.size == 0:
            return []

        result = self._fitPeaks(allPeaksArray, np.array(allRegionArrays), data, regionArray)
        func = self.findFunc
        return func(filter(None, result))

    def _fitPeaks(self, allPeaksArray, allRegionArrays, data, regionArray):
        # if peaks exist then create a list of fitted peaks
        fitMethod = self.fitMethod
        singularMode = self.singularMode
        try:
            if fitMethod == PARABOLICMETHOD:  # and singularMode is True:
                getLogger().debug(f'{self.__class__.__name__}._fitPeaks: parabolic')
                # parabolic - generate all peaks in one operation
                result = CPeak.fitParabolicPeaks(data, regionArray, allPeaksArray)
                if _DEBUGPLOT:
                    # debugging - make plots of the centre-line of the picked-region
                    #             (not actually very good unless in pick-and-assign module)
                    _plotParabolic(data, _logp, _makeParabola, regionArray, result)
            else:
                result = ()
                # currently gaussian or lorentzian
                method = 0 if fitMethod == GAUSSIANMETHOD else 1
                maxGroup = 1 if singularMode else _MAXGROUPING
                getLogger().debug(f'{self.__class__.__name__}._fitPeaks: {method} {maxGroup}')
                _errorMsgs = []

                arrMins = allRegionArrays[:, 0]  # effectively the bottom-left of a peak-regions
                arrMaxs = allRegionArrays[:, 1]  # the top-right, but can be any number of dimensions
                # Create a comparison across all pairs
                # creates a correlation matrix for which peak-regions overlap (their min/max point-positions)
                # True values in the same row correspond to overlapped regions
                # the last 2 lines only keep the first occurrence of a region in each column
                # so that regions are not processed twice
                #   COULD replace these with estimated ppms/linewidths from parabolic fit above
                minmax = arrMins[:, None, :] < arrMaxs[None, :, :]
                maxmin = arrMaxs[:, None, :] > arrMins[None, :, :]
                # find all places where bounds are overlapping
                # change to upper-triangular - probably not needed
                mask = np.triu(np.all(minmax, axis=-1) & np.all(maxmin, axis=-1), k=0)
                # remove all Trues below the first occurrence in each column
                mask = mask > (mask.argmax(axis=0) < np.arange(mask.shape[0]).reshape(-1, 1))
                # remove any rows that are all False - these have been merged into a previous region
                mask = mask[np.isin(mask, True).any(axis=1)]

                arrays = []
                if _DEBUG:
                    getLogger().debug(str(mask))
                    getLogger().debug('==> partitioning for group fitting ~~~~~~~~~~~')
                for row in range(mask.shape[0]):
                    # read the indexes for all the regions in this row
                    rowMask = np.where(mask[row, :] == True)[0]
                    if len(rowMask) == 0:
                        # SHOULD always contain 1 value
                        continue
                    # partition so that number of grouped peaks is not too large
                    partitions = [rowMask[kk:kk + maxGroup] for kk in range(0, len(rowMask), maxGroup)]
                    # merge the bounds of the regions in this partition
                    for blocks in partitions:
                        startArray = allRegionArrays[blocks[0]]
                        for mergeBlock in blocks[1:]:
                            # successively merge the region containing the adjacent peaks
                            endArray = allRegionArrays[mergeBlock]
                            startArray = np.array([np.minimum(startArray[0], endArray[0]),
                                                   np.maximum(startArray[1], endArray[1])])
                        arrays.append((startArray, blocks))
                        if _DEBUG:
                            getLogger().debug(str(arrays[-1]))

                if _DEBUGPLOT:
                    fig = plt.figure(figsize=(10, 8), dpi=100)
                    ax = fig.add_subplot(111, projection='3d')
                    xmS, ymS = np.meshgrid(range(data.shape[1]), range(data.shape[0]))
                    ax.plot_wireframe(xmS, ymS, data)

                # now iterate over all the new merged-regions, as group-peak-fits
                for row, (lRegion, slc) in enumerate(arrays):
                    peakArray = allPeaksArray[slc, :]
                    try:
                        localResult = CPeak.fitPeaks(data, lRegion, peakArray, method)
                        result += tuple(localResult)
                    except Exception as es:
                        # catch all errors as a single report - make sure results stay aligned
                        # by padding with Nones
                        _errorMsgs.append(f'failed to fit peaks: {peakArray}\n{es}')
                        result += tuple([None] * len(slc))
                    else:
                        if _DEBUGPLOT:
                            # debugging - make plots of the centre-line of the picked-region
                            # (not actually very good unless in pick-and-assign module)
                            _plotGaussLorentzGroup(data, _fwhm2sigma, _logp, _makeGauss, _makeLorentzian, method,
                                                   lRegion, localResult)
                if _errorMsgs:
                    getLogger().warning('\n'.join(_errorMsgs))

            if _DEBUGPLOT:
                # quick hack to show plots
                try:
                    plt.show()
                except Exception:
                    ...
            return result

        except CPeak.error as es:
            getLogger().warning(f'Aborting peak fit: {es}')
            return []

    def _findPeaks(self, data, posThreshold, negThreshold):
        """find the peaks in data (type numpy-array) and return as a list of SimplePeak instances
        """
        # NOTE:ED - need to validate the parameters first

        # set threshold values
        doPos = posThreshold is not None
        doNeg = negThreshold is not None
        posLevel = posThreshold or 0.0
        negLevel = negThreshold or 0.0

        # accounted for by pickPeaks in superclass
        exclusionBuffer = [0] * self.dimensionCount
        excludedRegionsList = []
        excludedDiagonalDimsList = []
        excludedDiagonalTransformList = []
        nonAdj = 1 if self.checkAllAdjacent else 0
        minLinewidth = [0.0] * self.dimensionCount if not self.minimumLineWidth else self.minimumLineWidth
        pointPeaks = CPeak.findPeaks(data, doNeg, doPos,
                                     negLevel, posLevel, exclusionBuffer,
                                     nonAdj,
                                     self.dropFactor,
                                     minLinewidth,
                                     excludedRegionsList, excludedDiagonalDimsList, excludedDiagonalTransformList)

        # get the peak maxima from pointPeaks
        pointPeaks = [(np.array(position), height) for position, height in pointPeaks]

        # ignore exclusion buffer for the minute
        validPointPeaks = [pk for pk in pointPeaks]
        allPeaksArray = None
        allRegionArrays = []
        regionArray = None

        # get the offset of the bottom left of the slice region
        startPoint = np.array([pp[0] for pp in self.sliceTuples])
        endPoint = np.array([pp[1] for pp in self.sliceTuples])
        numPointInt = (endPoint - startPoint) + 1

        for position, height in validPointPeaks:

            # get the region containing this point
            bLeft = np.maximum(position - self._hbsWidth, 0)
            tRight = np.minimum(position + self._hbsWidth + 1, numPointInt)
            localRegionArray = np.array((bLeft, tRight), dtype=np.int32)

            # get the larger regionArray size containing all points so far
            # the actual picked region may be huge, only need the bounds containing the maxima
            bLeftAll = np.maximum(position - self._hbsWidth - 1, 0)
            tRightAll = np.minimum(position + self._hbsWidth + 1, numPointInt)
            if regionArray is not None:
                bLeftAll = np.array(np.minimum(bLeftAll, regionArray[0]), dtype=np.int32)
                tRightAll = np.array(np.maximum(tRightAll, regionArray[1]), dtype=np.int32)

            # numpy arrays need tweaking to pass to the c code
            peakArray = position.reshape((1, self.dimensionCount))
            peakArray = peakArray.astype(np.float32)
            regionArray = np.array((bLeftAll, tRightAll), dtype=np.int32)

            if allPeaksArray is None:
                allPeaksArray = peakArray
            else:
                allPeaksArray = np.append(allPeaksArray, peakArray, axis=0)
            allRegionArrays.append(localRegionArray)

        return allPeaksArray, allRegionArrays, regionArray, validPointPeaks

    def pickPeaks(self, sliceTuples, peakList, positiveThreshold=None, negativeThreshold=None) -> list:
        """Set the default functionality for picking simplePeaks from the region defined by axisDict
        """
        # set the correct parameters for the standard findPeaks
        self._hbsWidth = self.halfBoxFindPeaksWidth
        self.findFunc = self._returnSimplePeaks

        return super().pickPeaks(sliceTuples=sliceTuples, peakList=peakList,
                                 positiveThreshold=positiveThreshold, negativeThreshold=negativeThreshold)

    def _returnSimplePeaks(self, foundPeaks):
        """Return a list of SimplePeak objects from the height/point/lineWidth foundPeaks list
        """
        peaks = [SimplePeak(points=point[::-1],
                            height=height,
                            lineWidths=pointLineWidths if self.setLineWidths else None)
                 for height, point, pointLineWidths in foundPeaks]
        return peaks

    def snapToExtremum(self, peak) -> list:
        """
        :param axisDict: Axis limits  are passed in as a dict of (axisCode, tupleLimit) key, value
                         pairs with the tupleLimit supplied as (start,stop) axis limits in ppm
                         (lower ppm value first).
        :param peakList: peakList instance to add newly pickedPeaks
        :return: list of core.Peak instances
        """
        if self.spectrum is None:
            raise RuntimeError('%s.spectrum is None' % self.__class__.__name__)

        if not self.spectrum.hasValidPath():
            raise RuntimeError('%s.pickPeaks: spectrum %s, No valid spectral datasource defined' %
                               (self.__class__.__name__, self.spectrum))

        pointPositions = peak.pointPositions
        if not pointPositions or None in pointPositions:
            raise ValueError(f'Peak.position is invalid for {peak}')

        # set up the search box widths
        self._hbsWidth = self.halfBoxSearchWidth
        self._hbfWidth = self.halfBoxFitWidth

        spectrum = peak.spectrum
        valuesPerPoint = spectrum.ppmPerPoints
        axisCodes = spectrum.axisCodes

        # searchBox for Nd
        if self.searchBoxMode:

            boxWidths = []
            axisCodes = self.spectrum.axisCodes
            valuesPerPoint = self.spectrum.ppmPerPoints
            for axisCode, valuePerPoint in zip(axisCodes, valuesPerPoint):
                letterAxisCode = (axisCode[0] if axisCode != 'intensity' else axisCode) if axisCode else None
                if letterAxisCode in self.searchBoxWidths:
                    newWidth = math.floor(self.searchBoxWidths[letterAxisCode] / (2.0 * valuePerPoint))
                    boxWidths.append(max(1, newWidth))
                else:
                    # default to the given parameter value
                    boxWidths.append(max(1, self._hbsWidth or 1))
        else:
            boxWidths = []
            pointCounts = spectrum.pointCounts
            peakBoxWidths = peak.boxWidths
            for axisCode, pointCount, peakBWidth, valuePPoint in zip(axisCodes, pointCounts, peakBoxWidths,
                                                                     valuesPerPoint):
                _halfBoxWidth = pointCount / 100  # copied from V2
                boxWidths.append(max(_halfBoxWidth, 1, int((peakBWidth or 1) / 2)))

        # add the new boxWidths array as np.int32 type
        boxWidths = np.array(boxWidths, dtype=np.int32)
        pLower = np.floor(pointPositions).astype(np.int32)
        # find the co-ordinates of the lower corner of the data region
        startPoint = np.maximum(pLower - boxWidths, 0)

        self.sliceTuples = [(int(pos - bWidth), int(pos + bWidth + 1))
                            for pos, bWidth in zip(pointPositions, boxWidths)]
        data = self.spectrum.dataSource.getRegionData(self.sliceTuples,
                                                      aliasingFlags=[1] * self.spectrum.dimensionCount)

        # get the height of the current peak (to stop peak flipping)
        height = spectrum.getPointValue(peak.pointPositions)
        scaledHeight = 0.5 * height  # this is so that have sensible pos/negLevel
        if height > 0:
            posLevel = scaledHeight
            negLevel = None
        else:
            posLevel = None
            negLevel = scaledHeight

        # find the list of peaks in the region
        allPeaksArray, allRegionArrays, regionArray, validPoints = self._findPeaks(data, posLevel, negLevel)

        # if peaks exist then create a list of simple peaks
        if allPeaksArray is not None and allPeaksArray.size != 0:

            # find the closest peak in the found list
            bestHeight = peakPoint = None
            bestFit = 0.0
            validPoints = sorted(validPoints, key=lambda val: abs(val[1]))
            for ii, findNextPeak in enumerate(validPoints):

                # find the highest peak to start from
                peakHeight = findNextPeak[1]
                peakDist = np.linalg.norm((np.array(findNextPeak[0]) - boxWidths) / boxWidths)
                peakFit = abs(height) / (1e-6 + peakDist)

                if height is None or peakFit > bestFit:
                    bestFit = peakFit
                    bestHeight = abs(peakHeight)
                    peakPoint = findNextPeak[0]

            # use this as the centre for the peak fitting
            peakPoint = np.array(peakPoint)
            peakArray = peakPoint.reshape((1, spectrum.dimensionCount))
            peakArray = peakArray.astype(np.float32)

            try:
                # NOTE:ED - this still needs duplicate-code check with _fitPeaks
                if self.searchBoxDoFit:
                    if self.fitMethod == PARABOLICMETHOD:
                        # parabolic - generate all peaks in one operation
                        result = CPeak.fitParabolicPeaks(data, regionArray, peakArray)

                    else:
                        method = 0 if self.fitMethod == GAUSSIANMETHOD else 1

                        # use the halfBoxFitWidth to give a close fit
                        firstArray = np.maximum(peakArray[0] - self._hbfWidth, regionArray[0])
                        lastArray = np.minimum(peakArray[0] + self._hbfWidth + 1, regionArray[1])
                        regionArray = np.array((firstArray, lastArray), dtype=np.int32)

                        # fit the single peak
                        result = CPeak.fitPeaks(data, regionArray, peakArray, method)
                else:
                    # take the maxima
                    result = ((bestHeight, peakPoint, None),)

                # if any results are found then set the new peak position/height
                if result:
                    height, center, linewidth = result[0]

                    _shape = data.shape[::-1]
                    newPos = list(peak.pointPositions)
                    for ii in range(len(center)):
                        if 0.5 < center[ii] < (_shape[ii] - 0.5):
                            newPos[ii] = float(center[ii] + startPoint[ii])

                    peak.pointPositions = newPos
                    if linewidth:
                        peak.pointLineWidths = linewidth

                    if self.searchBoxDoFit:
                        peak.height = height
                    else:
                        # get the interpolated height
                        peak.height = spectrum.getPointValue(peak.pointPositions)

            except CPeak.error as es:
                getLogger().warning(f'Aborting peak fit: {es}')
                return []

        return []

    def fitExistingPeaks(self, peaks: Sequence['Peak']):
        """Refit the current selected peaks.
        Must be called with peaks that belong to this peakList
        """

        if not peaks:
            return

        # set the correct parameters for the standard findPeaks
        self._hbsWidth = self.halfBoxFindPeaksWidth
        allPeaksArray = None
        allRegionArrays = []
        regionArray = None

        numLists = Counter([pk.peakList for pk in peaks])
        if len(numLists) > 1:
            raise ValueError('List contains peaks from more than one peakList.')

        # pointPositions = peaks[0].pointPositions
        spectrum = peaks[0].spectrum
        pointCounts = spectrum.pointCounts
        numDim = spectrum.dimensionCount

        # only consider peaks that have a valid pointPosition (does not contain None)
        pointPeaks = [pk for pk in peaks if pk.pointPositions and None not in pk.pointPositions]

        for peak in pointPeaks:
            pointPositions = peak.pointPositions

            # round up/down the position
            pLower = np.floor(pointPositions).astype(np.int32)
            pUpper = np.ceil(pointPositions).astype(np.int32)
            position = np.round(np.array(pointPositions))

            # generate a np array with the number of points per dimension
            numPoints = np.array(pointCounts)

            # consider for each dimension on the interval [point-3,point+4>, account for min and max
            # of each dimension
            if self.fitMethod == PARABOLICMETHOD:  # or self.singularMode is True:
                firstArray = np.maximum(pLower - self._hbsWidth, 0)
                lastArray = np.minimum(pUpper + self._hbsWidth, numPoints)
            else:
                # extra plane in each direction increases accuracy of group fitting
                firstArray = np.maximum(pLower - self._hbsWidth - 1, 0)
                lastArray = np.minimum(pUpper + self._hbsWidth + 1, numPoints)

            # Cast to int for subsequent call
            firstArray = firstArray.astype(np.int32)
            lastArray = lastArray.astype(np.int32)
            localRegionArray = np.array((firstArray, lastArray), dtype=np.int32)

            if regionArray is not None:
                firstArray = np.minimum(firstArray, regionArray[0])
                lastArray = np.maximum(lastArray, regionArray[1])

            # requires reshaping of the array for use with CPeak.fitParabolicPeaks
            peakArray = position.reshape((1, numDim))
            peakArray = peakArray.astype(np.float32)
            regionArray = np.array((firstArray, lastArray), dtype=np.int32)

            if allPeaksArray is None:
                allPeaksArray = peakArray
            else:
                allPeaksArray = np.append(allPeaksArray, peakArray, axis=0)
            allRegionArrays.append(localRegionArray)

        if allPeaksArray is None or allPeaksArray.size == 0:
            return

        self.sliceTuples = [(fst, lst) for fst, lst in zip(firstArray, lastArray)]
        data = self.spectrum.dataSource.getRegionData(self.sliceTuples,
                                                      aliasingFlags=[1] * self.spectrum.dimensionCount)

        # update positions relative to the corner of the data array
        #   - maps all regions to (0, 0)
        regionArray -= firstArray
        allPeaksArray -= firstArray.astype(np.float32)
        allRegionArrays = np.array(allRegionArrays) - firstArray

        result = self._fitPeaks(allPeaksArray, allRegionArrays, data, regionArray)

        for pkNum, peak in enumerate(pointPeaks):
            # result indexing SHOULD correspond to original peaks, with Nones as bad refits
            if not (res := result[pkNum]):
                continue
            height, center, linewidth = res
            # overwrite the peak pointPositions
            _shape = data.shape[::-1]
            newPos = list(peak.pointPositions)
            for ii in range(len(center)):
                if 0.5 < center[ii] < (_shape[ii] - 0.5):
                    newPos[ii] = center[ii] + firstArray[ii]
            peak.pointPositions = newPos
            peak.pointLineWidths = linewidth
            peak.height = height


# register the peakPicker as available
PeakPickerNd._registerPeakPicker()
