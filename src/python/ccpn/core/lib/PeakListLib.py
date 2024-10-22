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
__dateModified__ = "$dateModified: 2024-10-10 15:45:26 +0100 (Thu, October 10, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2021-06-01 09:23:39 +0100 (Tue, June 1, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from typing import Sequence
from ccpn.core.PeakList import PARABOLICMETHOD, GAUSSIANMETHOD
from ccpnmodel.ccpncore.lib._ccp.nmr.Nmr.PeakList import pickNewPeaks


def _pickPeaksRegion(peakList, regionToPick: dict = {},
                     doPos: bool = True, doNeg: bool = True,
                     minLinewidth=None, exclusionBuffer=None,
                     minDropFactor: float = 0.1, checkAllAdjacent: bool = True,
                     fitMethod: str = PARABOLICMETHOD, excludedRegions=None,
                     excludedDiagonalDims=None, excludedDiagonalTransform=None,
                     estimateLineWidths=True):
    """
    DEPRECATED - please use spectrum.pickPeaks()
    
    Pick peaks in the region defined by the regionToPick dict.

    Axis limits are passed in as a dict containing the axis codes and the required limits.
    Each limit is defined as a key, value pair: (str, tuple),
    with the tuple supplied as (min,max) axis limits in ppm.

    For axisCodes that are not included, the limits will be taken from the aliasingLimits of the spectrum.

    Illegal axisCodes will raise an error.

    Example dict:

    ::

        {'Hn': (7.0, 9.0),
         'Nh': (110, 130)
         }

    doPos, doNeg - pick positive/negative peaks or both.

    exclusionBuffer defines the size to extend the region by in index units, e.g. [1, 1, 1]
                extends the region by 1 index point in all axes.
                Default is 1 in all axis directions.

    minDropFactor - minimum drop factor, value between 0.0 and 1.0
                Ratio of max value to adjacent values in dataArray. Default is 0.1
                i.e., difference between all adjacent values and local maximum must be greater than 10%
                for maximum to be considered as a peak.

    fitMethod - curve fitting method to find local maximum at peak location in dataArray.
                Current methods are ('gaussian', 'lorentzian').
                Default is gaussian.

    :param regionToPick: dict of axis limits
    :param doPos: pick positive peaks
    :param doNeg: pick negative peaks
    :param minLinewidth:
    :param exclusionBuffer: array of int
    :param minDropFactor: float defined on [0.0, 1.0] default is 0.1
    :param checkAllAdjacent: True/False, default True
    :param fitMethod: str in 'gaussian', 'lorentzian'
    :param excludedRegions:
    :param excludedDiagonalDims:
    :param excludedDiagonalTransform:
    :return: list of peaks.
    """

    from ccpnc.peak import Peak as CPeak

    spectrum = peakList.spectrum
    dataSource = spectrum._apiDataSource
    numDim = dataSource.numDim

    peaks = []

    if not minLinewidth:
        minLinewidth = [0.0] * numDim

    if not exclusionBuffer:
        exclusionBuffer = [1] * numDim
    else:
        if len(exclusionBuffer) != numDim:
            raise ValueError('Error: pickPeaksRegion, exclusion buffer length must match dimension of spectrum')
        for nDim in range(numDim):
            if exclusionBuffer[nDim] < 1:
                raise ValueError('Error: pickPeaksRegion, exclusion buffer must contain values >= 1')

    nonAdj = 1 if checkAllAdjacent else 0

    if not excludedRegions:
        excludedRegions = []

    if not excludedDiagonalDims:
        excludedDiagonalDims = []

    if not excludedDiagonalTransform:
        excludedDiagonalTransform = []

    posLevel = spectrum.positiveContourBase if doPos else None
    negLevel = spectrum.negativeContourBase if doNeg else None
    if posLevel is None and negLevel is None:
        return peaks

    # find the regions from the spectrum - sometimes returning None which gives an error
    foundRegions = peakList.spectrum.getRegion(**regionToPick)

    if not foundRegions:
        return peaks

    for region in foundRegions:
        if not region:
            continue

        dataArray, intRegion, \
            startPoints, endPoints, \
            startPointBufferActual, endPointBufferActual, \
            startPointIntActual, numPointInt, \
            startPointBuffer, endPointBuffer = region

        if dataArray is not None and dataArray.size:
            # find new peaks
            # exclusion code copied from Nmr/PeakList.py
            excludedRegionsList = [np.array(excludedRegion, dtype=np.float32) - startPointBuffer
                                   for excludedRegion in excludedRegions]
            excludedDiagonalDimsList = []
            excludedDiagonalTransformList = []
            for n in range(len(excludedDiagonalDims)):
                dim1, dim2 = excludedDiagonalDims[n]
                a1, a2, b12, d = excludedDiagonalTransform[n]
                b12 += a1 * startPointBuffer[dim1] - a2 * startPointBuffer[dim2]
                excludedDiagonalDimsList.append(np.array((dim1, dim2), dtype=np.int32))
                excludedDiagonalTransformList.append(np.array((a1, a2, b12, d), dtype=np.float32))

            doPos = posLevel is not None
            doNeg = negLevel is not None
            posLevel = posLevel or 0.0
            negLevel = negLevel or 0.0

            # print('>>dataArray', dataArray)
            # NOTE:ED requires an exclusionBuffer of 1 in all axis directions
            peakPoints = CPeak.findPeaks(dataArray, doNeg, doPos,
                                         negLevel, posLevel, exclusionBuffer,
                                         nonAdj, minDropFactor, minLinewidth,
                                         excludedRegionsList, excludedDiagonalDimsList, excludedDiagonalTransformList)

            peakPoints = [(np.array(position), height) for position, height in peakPoints]

            # only keep those points which are inside original region, not extended region
            peakPoints = [(position, height) for position, height in peakPoints if
                          ((startPoints - startPointIntActual) <= position).all() and
                          (position < (endPoints - startPointIntActual)).all()]
            existingPositions = [np.array([int(pp) - 1 for pp in pk.pointPositions]) for pk in peakList.peaks]

            # NB we can not overwrite exclusionBuffer, because it may be used as a parameter in redoing
            # and 'if not exclusionBuffer' does not work on np arrays.
            npExclusionBuffer = np.array(exclusionBuffer)

            validPeakPoints = []
            for thisPeak in peakPoints:

                position, height = thisPeak

                position += startPointBufferActual

                for existingPosition in existingPositions:
                    delta = abs(existingPosition - position)

                    # TODO:ED changed to '<='
                    if (delta <= npExclusionBuffer).all():
                        break
                else:
                    validPeakPoints.append(thisPeak)

            allPeaksArray = None
            allRegionArrays = []
            regionArray = None

            for position, height in validPeakPoints:
                position -= startPointBufferActual
                numDim = len(position)

                # get the region containing this point
                firstArray = np.maximum(position - 2, 0)
                lastArray = np.minimum(position + 3, numPointInt)
                localRegionArray = np.array((firstArray, lastArray))
                localRegionArray = localRegionArray.astype(np.int32)

                # get the larger regionArray size containing all points so far
                firstArray = np.maximum(position - 3, 0)
                lastArray = np.minimum(position + 4, numPointInt)
                if regionArray is not None:
                    firstArray = np.minimum(firstArray, regionArray[0])
                    lastArray = np.maximum(lastArray, regionArray[1])

                peakArray = position.reshape((1, numDim))
                peakArray = peakArray.astype(np.float32)
                firstArray = firstArray.astype(np.int32)
                lastArray = lastArray.astype(np.int32)
                regionArray = np.array((firstArray, lastArray))

                if allPeaksArray is None:
                    allPeaksArray = peakArray
                else:
                    allPeaksArray = np.append(allPeaksArray, peakArray, axis=0)
                allRegionArrays.append(localRegionArray)

            if allPeaksArray is not None:

                # parabolic - generate all peaks in one operation
                result = CPeak.fitParabolicPeaks(dataArray, regionArray, allPeaksArray)

                for height, centerGuess, linewidth in result:
                    center = np.array(centerGuess)

                    position = center + startPointBufferActual
                    peak = peakList.newPickedPeak(pointPositions=position, height=height,
                                                  lineWidths=linewidth if estimateLineWidths else None,
                                                  fitMethod=fitMethod)
                    peaks.append(peak)

                if fitMethod != PARABOLICMETHOD:
                    peakList.fitExistingPeaks(peaks, fitMethod=fitMethod,
                                              singularMode=False)  # group-mode by default

    return peaks


def _pickPeaksNd(peakList, regionToPick: Sequence[float] = None,
                 doPos: bool = True, doNeg: bool = True,
                 fitMethod: str = GAUSSIANMETHOD, excludedRegions=None,
                 excludedDiagonalDims=None, excludedDiagonalTransform=None,
                 minDropFactor: float = 0.1):
    # TODO NBNB Add doc string and put type annotation on all parameters
    # DEPRECATED

    startPoint = []
    endPoint = []
    spectrum = peakList.spectrum
    aliasingLimits = spectrum.aliasingLimits
    apiPeaks = []
    spectrumReferences = spectrum.spectrumReferences
    if None in spectrumReferences:
        # TODO if we want to pick in Sampeld fo FId dimensions, this must be added
        raise ValueError("pickPeaksNd() only works for Frequency dimensions"
                         " with defined primary SpectrumReferences ")
    if regionToPick is None:
        regionToPick = peakList.spectrum.aliasingLimits
    for ii, spectrumReference in enumerate(spectrumReferences):
        aliasingLimit0, aliasingLimit1 = aliasingLimits[ii]
        value0 = regionToPick[ii][0]
        value1 = regionToPick[ii][1]
        value0, value1 = min(value0, value1), max(value0, value1)
        if value1 < aliasingLimit0 or value0 > aliasingLimit1:
            break  # completely outside aliasing region
        value0 = max(value0, aliasingLimit0)
        value1 = min(value1, aliasingLimit1)
        # -1 below because points start at 1 in data model
        position0 = spectrumReference.valueToPoint(value0) - 1
        position1 = spectrumReference.valueToPoint(value1) - 1
        position0, position1 = min(position0, position1), max(position0, position1)
        # want integer grid points above position0 and below position1
        # add 1 to position0 because above
        # add 1 to position1 because doing start <= x < end not <= end
        # yes, this negates -1 above but they are for different reasons
        position0 = int(position0 + 1)
        position1 = int(position1 + 1)
        startPoint.append((spectrumReference.dimension, position0))
        endPoint.append((spectrumReference.dimension, position1))
    else:
        startPoints = [point[1] for point in sorted(startPoint)]
        endPoints = [point[1] for point in sorted(endPoint)]
        # print(isoOrdering, startPoint, startPoints, endPoint, endPoints)

        posLevel = spectrum.positiveContourBase if doPos else None
        negLevel = spectrum.negativeContourBase if doNeg else None

        # with logCommandBlock(get='peakList') as log:
        #     log('pickPeaksNd')
        #     with notificationBlanking():

        apiPeaks = pickNewPeaks(peakList._apiPeakList, startPoint=startPoints, endPoint=endPoints,
                                posLevel=posLevel, negLevel=negLevel, fitMethod=fitMethod,
                                excludedRegions=excludedRegions, excludedDiagonalDims=excludedDiagonalDims,
                                excludedDiagonalTransform=excludedDiagonalTransform, minDropfactor=minDropFactor)

    data2ObjDict = peakList._project._data2Obj
    result = [data2ObjDict[apiPeak] for apiPeak in apiPeaks]
    # for peak in result:
    #     peak._finaliseAction('create')

    return result


def _fitExistingPeaks(peakList, peaks: Sequence['Peak'], fitMethod: str = GAUSSIANMETHOD, singularMode: bool = False,
                      halfBoxSearchWidth: int = 4, halfBoxFitWidth: int = 4):
    """Refit the current selected peaks.
    Must be called with peaks that belong to this peakList
    """
    # DEPRECATED

    from ccpn.core.lib.SpectrumLib import fetchPeakPicker
    from ccpn.framework.Application import getApplication

    getApp = getApplication()

    if peaks:
        badPeaks = [peak for peak in peaks if peak.peakList is not peakList]
        if badPeaks:
            raise ValueError('List contains peaks that are not in the same peakList.')

        myPeakPicker = fetchPeakPicker(spectrum=peakList.spectrum)
        myPeakPicker.setParameters(dropFactor=getApp.preferences.general.peakDropFactor,
                                   fitMethod=fitMethod,
                                   searchBoxMode=getApp.preferences.general.searchBoxMode,
                                   searchBoxDoFit=getApp.preferences.general.searchBoxDoFit,
                                   halfBoxSearchWidth=halfBoxSearchWidth,
                                   halfBoxFitWidth=halfBoxFitWidth,
                                   searchBoxWidths=getApp.preferences.general.searchBoxWidthsNd,
                                   singularMode=singularMode
                                   )

        myPeakPicker.fitExistingPeaks(peaks)
