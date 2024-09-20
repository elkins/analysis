"""Module Documentation here

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
__dateModified__ = "$dateModified: 2024-09-09 19:03:26 +0100 (Mon, September 09, 2024) $"
__version__ = "$Revision: 3.2.6 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui
import numpy as np
from itertools import product
from collections import namedtuple
from PyQt5 import QtCore, QtGui
from numba import jit

from ccpn.ui.gui.lib.GuiSpectrumView import GuiSpectrumView, SpectrumCache
from ccpn.util import Colour
from ccpn.util.Logging import getLogger
from ccpn.core.Spectrum import MAXALIASINGRANGE
from ccpn.core.lib.ContextManagers import notificationEchoBlocking
from ccpnc.contour import Contourer2d


AxisPlaneData = namedtuple('AxisPlaneData', 'startPoint endPoint pointCount')


def _getLevels(count: int, base: float, factor: float) -> list:
    """return a list with contour levels"""
    levels = []
    if count > 0:
        levels = [base]
        for n in range(count - 1):
            levels.append(np.float32(factor * levels[-1]))
    return levels


#=========================================================================================
# GuiSpectrumViewNd
#=========================================================================================

class GuiSpectrumViewNd(GuiSpectrumView):

    ###PeakListItemClass = PeakListNdItem

    #def __init__(self, guiSpectrumDisplay, apiSpectrumView, dimMapping=None, region=None, **kwds):
    def __init__(self):
        """ guiSpectrumDisplay is the parent
            apiSpectrumView is the (API) SpectrumView object
        """

        self.setAcceptedMouseButtons = QtCore.Qt.LeftButton
        self.posLevelsPrev = []
        self.negLevelsPrev = []
        self.zRegionPrev = None
        self.posDisplayLists = []
        self.negDisplayLists = []
        self._traceScale = None  # For now: Initialised by CcpOpenGl._getSliceData
        self.okDataFile = True  # used to keep track of warning message that data file does not exist

        dimensionCount = len(self.strip.axisCodes)
        self.previousRegion = dimensionCount * [None]

        # have to have this set before _setupBorderItem called
        self._application = self.strip.spectrumDisplay.mainWindow.application

        GuiSpectrumView.__init__(self)

        self.setZValue(-1)  # this is so that the contours are drawn on the bottom

        self.buildContours = True
        self.buildContoursOnly = False

    def _turnOnPhasing(self):
        """
        # CCPN INTERNAL - called by turnOnPhasing method of GuiStrip.
        """
        phasingFrame = self.strip.spectrumDisplay.phasingFrame
        if phasingFrame.isVisible():
            direction = phasingFrame.getDirection()
            traces = self.hPhaseTraces if direction == 0 else self.vPhaseTraces
            for trace, line in traces:
                trace.setVisible(True)
                line.setVisible(True)

    def _turnOffPhasing(self):
        """
        # CCPN INTERNAL - called by turnOffPhasing method of GuiStrip.
        """
        for traces in self.hPhaseTraces, self.vPhaseTraces:
            for trace, line in traces:
                trace.setVisible(False)
                line.setVisible(False)

    def _changedPhasingDirection(self):

        phasingFrame = self.strip.spectrumDisplay.phasingFrame
        direction = phasingFrame.getDirection()
        if direction == 0:
            for trace, line in self.hPhaseTraces:
                trace.setVisible(True)
                line.setVisible(True)
            for trace, line in self.vPhaseTraces:
                trace.setVisible(False)
                line.setVisible(False)
        else:
            for trace, line in self.hPhaseTraces:
                trace.setVisible(False)
                line.setVisible(False)
            for trace, line in self.vPhaseTraces:
                trace.setVisible(True)
                line.setVisible(True)

        self._updatePhasing()

    def _updatePhasing(self):
        """
        # CCPN INTERNAL - called in _updatePhasing method of GuiStrip
        """
        if not self.isDisplayed:
            return

    @property
    def traceScale(self) -> float:
        """Scale for trace in this spectrumView"""
        return self._traceScale

    @traceScale.setter
    def traceScale(self, value):
        """Setter for scale for trace in this spectrumView"""
        self._traceScale = value
        self.strip._updateTraces()
        self._updatePhasing()

    @staticmethod
    def _printContourData(printer, contourData, colour, xTile0, xTile1, yTile0, yTile1, xTranslate, xScale,
                          xTotalPointCount, yTranslate, yScale,
                          yTotalPointCount):

        for xTile in range(xTile0, xTile1):
            for yTile in range(yTile0, yTile1):
                for contour in contourData:
                    n = len(contour) // 2
                    contour = contour.copy()
                    contour = contour.reshape((n, 2))
                    contour[:, 0] += xTotalPointCount * xTile
                    contour[:, 0] *= xScale
                    contour[:, 0] += xTranslate
                    contour[:, 1] += yTotalPointCount * yTile
                    contour[:, 1] *= yScale
                    contour[:, 1] += yTranslate
                    printer.writePolyline(contour, colour)

    def _buildGLContours(self, glList):
        """Build the contour arrays
        """
        if self.spectrum.positiveContourBase is None or self.spectrum.positiveContourBase == 0.0:
            raise RuntimeError('Positive Contour Base is not defined')

        if self.spectrum.negativeContourBase is None or self.spectrum.negativeContourBase == 0.0:
            raise RuntimeError('Negative Contour Base is not defined')

        if self.spectrum.includePositiveContours:  # .displayPositiveContours:
            self.posLevels = _getLevels(self.positiveContourCount, self.positiveContourBase,
                                        self.positiveContourFactor)
        else:
            self.posLevels = []

        if self.spectrum.includeNegativeContours:  # .displayNegativeContours:
            self.negLevels = _getLevels(self.negativeContourCount, self.negativeContourBase,
                                        self.negativeContourFactor)
        else:
            self.negLevels = []

        colName = self._getColour('positiveContourColour') or '#E00810'
        if not colName.startswith('#'):
            # get the colour from the gradient table or a single red
            colListPos = tuple(Colour.scaledRgba(col) for col in
                               Colour.colorSchemeTable[colName]) if colName in Colour.colorSchemeTable else (
                (1, 0, 0, 1),)
        else:
            colListPos = (Colour.scaledRgba(colName),)

        colName = self._getColour('negativeContourColour') or '#E00810'
        if not colName.startswith('#'):
            # get the colour from the gradient table or a single red
            colListNeg = tuple(Colour.scaledRgba(col) for col in
                               Colour.colorSchemeTable[colName]) if colName in Colour.colorSchemeTable else (
                (1, 0, 0, 1),)
        else:
            colListNeg = (Colour.scaledRgba(colName),)

        glList.posColours = self.posColours = colListPos
        glList.negColours = self.negColours = colListNeg

        try:
            self._constructContours(self.posLevels, self.negLevels, glList=glList)
        except FileNotFoundError:
            self._project._logger.warning("No data file found for %s" % self)
            return

    def _constructContours(self, posLevels, negLevels, glList=None):
        """Construct the contours for this spectrum using an OpenGL display list
        The way this is done here, any change in contour level needs to call this function.
        """

        posLevelsArray = np.array(posLevels, np.float32)
        negLevelsArray = np.array(negLevels, np.float32)

        self.posLevelsPrev = list(posLevels)
        self.negLevelsPrev = list(negLevels)
        self.zRegionPrev = tuple([tuple(axis.region) for axis in self.strip.orderedAxes[2:] if axis is not None])

        # posContoursAll = negContoursAll = None
        # numDims = self.spectrum.dimensionCount

        # get the positive/negative contour colour lists
        _posColours = self._interpolateColours(self.posColours, posLevels)
        _negColours = self._interpolateColours(self.negColours, negLevels)

        contourList = None
        try:
            if True:  # numDims < 3 or self._application.preferences.general.generateSinglePlaneContours:
                dataArrays = tuple()

                for position, dataArray in self._getPlaneData():
                    # overlay all the planes into a single plane
                    dataArrays += (dataArray,)
                    # break

                # moved to C Code
                # if len(dataArrays) > 1 and not self._application.preferences.general.generateSinglePlaneContours:
                #     sum = dataArrays[0]
                #     for ii in range(1, len(dataArrays)):
                #         sum = np.max(sum, dataArrays[ii].clip(0.0, 1e16)) + np.min(sum, dataArrays[ii].clip(-1e16, 0.0))
                #     dataArrays = (sum,)

                # build the contours
                contourList = Contourer2d.contourerGLList(dataArrays,
                                                          posLevelsArray,
                                                          negLevelsArray,
                                                          np.array(_posColours, dtype=np.float32),
                                                          np.array(_negColours, dtype=np.float32),
                                                          not self._application.preferences.general.generateSinglePlaneContours)

        except Exception as es:
            getLogger().warning(f'Contouring error: {es}')

        finally:
            if contourList and contourList[1] > 0:

                # self._expand(contourList[2])  # indices compressed inplace

                # set the contour arrays for the GL object
                glList.numVertices = contourList[1]
                glList.indices = contourList[2]
                glList.vertices = contourList[3]
                glList.colors = contourList[4]

            else:
                # clear the arrays
                glList.numVertices = 0
                glList.indices = np.array((), dtype=np.uint32)
                glList.vertices = np.array((), dtype=np.float32)
                glList.colors = np.array((), dtype=np.float32)

    @staticmethod
    def _interpolateColours(colourList, levels):
        xdim = 256
        colours = []
        stepX = len(levels) - 1
        stepY = len(colourList) - 1
        if stepX > 0 and stepY > 0:
            # fill a pixmap with a linear-gradient defined by the colour-list
            pix = QtGui.QPixmap(QtCore.QSize(xdim, 1))
            painter = QtGui.QPainter(pix)
            grad = QtGui.QLinearGradient(0, 0, xdim, 0)
            for ii, col in enumerate(colourList):
                grad.setColorAt(ii / stepY, QtGui.QColor.fromRgbF(*col))
            painter.fillRect(pix.rect(), grad)
            painter.end()
            img = pix.toImage()
            for ii in range(stepX + 1):
                # grab the colour from the pixmap
                xx = int((xdim - 1) * ii / stepX)
                col = img.pixelColor(xx, 0).getRgbF()
                colours.extend(col)
        else:
            colours = colourList[0] * len(levels)

        return colours

    def _getPlaneData(self):

        spectrum = self.spectrum
        dimensionCount = spectrum.dimensionCount
        dimIndices = self.dimensionIndices
        xDim = dimIndices[0]
        yDim = dimIndices[1]

        orderedAxes = self.strip.axes

        if dimensionCount == 2:
            planeData = spectrum.getPlaneData(xDim=xDim + 1, yDim=yDim + 1)
            position = [1, 1]
            yield position, planeData

        elif dimensionCount == 3:

            # start with the simple case
            axisData = self._getAxisInfo(orderedAxes, 2)
            if not axisData:
                return

            position = dimensionCount * [1]
            # if axisData.startPoint <= axisData.endPoint:  # need to check after other bits working
            #     _loopArgs = range(axisData.startPoint, axisData.endPoint)
            # else:
            #     _loopArgs = range(axisData.startPoint - 1, axisData.endPoint - 1, -1)
            # for z in _loopArgs:
            for z in range(axisData.startPoint, axisData.endPoint,
                           1 if axisData.endPoint > axisData.startPoint else -1):
                position[dimIndices[2]] = (z % axisData.pointCount) + 1
                planeData = spectrum.getPlaneData(position, xDim=xDim + 1, yDim=yDim + 1)
                yield position, planeData

        elif dimensionCount >= 4:

            # get the axis information
            axes = [self._getAxisInfo(orderedAxes, dim) for dim in range(2, dimensionCount)]
            if None in axes:
                return

            # create a tuple of the ranges for the planes
            _loopArgs = tuple(
                    range(axis.startPoint, axis.endPoint, 1 if axis.endPoint > axis.startPoint else -1) for axis in
                    axes)

            position = dimensionCount * [1]
            _offset = dimensionCount - len(_loopArgs)  # should always be 2?

            # iterate over all the axes
            for _plane in product(*_loopArgs):

                # get the axis position and put into the position vector
                for dim, pos in enumerate(_plane):
                    _axis = axes[dim]
                    position[dimIndices[dim + _offset]] = (pos % axes[dim].pointCount) + 1

                # get the plane data
                planeData = spectrum.getPlaneData(position, xDim=xDim + 1, yDim=yDim + 1)
                yield position, planeData

    def _getAxisInfo(self, orderedAxes, axisIndex):
        """Get the information for the required axis
        """
        indx = self.dimensionIndices[axisIndex]
        if indx is None:
            return

        # get the axis region
        zPosition = orderedAxes[axisIndex].position
        width = orderedAxes[axisIndex].width
        axisCode = self.strip.spectrumDisplay.axisCodes[axisIndex]

        # get the ppm range
        zPointCount = (self.spectrum.pointCounts)[indx]
        zRegionValue = (zPosition + 0.5 * width, zPosition - 0.5 * width)  # Note + and - (axis backwards)

        # clip to the aliasingLimits of the spectrum - ignore if both greater/less than limits
        aliasing = (self.spectrum.aliasingLimits)[indx]
        if all(val <= aliasing[0] for val in zRegionValue) or all(val >= aliasing[1] for val in zRegionValue):
            return
        zRegionValue = tuple(float(np.clip(val, *aliasing)) for val in zRegionValue)

        # convert ppm- to point-range
        zPointFloat0 = self.spectrum.ppm2point(zRegionValue[0], axisCode=axisCode) - 1.0
        zPointFloat1 = self.spectrum.ppm2point(zRegionValue[1], axisCode=axisCode) - 1.0

        # convert to integers
        zPointInt0, zPointInt1 = (
            int(zPointFloat0 + (1 if zPointFloat0 >= 0 else 0)),  # this gives first and 1+last integer in range
            int(zPointFloat1 + (1 if zPointFloat1 >= 0 else 0)))  # and takes into account negative ppm2Point

        if zPointInt0 == zPointInt1:
            # only one plane visible, need to 2 points for range()
            if zPointFloat0 - (zPointInt0 - 1) < zPointInt1 - zPointFloat1:  # which is closest to an integer
                zPointInt0 -= 1
            else:
                zPointInt1 += 1
        elif (zPointInt1 - zPointInt0) >= zPointCount:
            # range is more than range of planes, set to maximum
            zPointInt0 = 0
            zPointInt1 = zPointCount

        return AxisPlaneData(zPointInt0, zPointInt1, zPointCount)

    def _getVisiblePlaneList(self, firstVisible=None, minimumValuePerPoint=None):

        spectrum = self.spectrum
        dimensionCount = spectrum.dimensionCount
        dimIndices = self.dimensionIndices
        orderedAxes = self._apiStripSpectrumView.strip.orderedAxes

        if dimensionCount <= 2:
            return None, None, []

        planeList = ()
        planePointValues = ()

        for dim in range(2, dimensionCount):

            indx = self.dimensionIndices[dim]
            if indx is None:
                return

            # make sure there is always a spectrumView to base visibility on
            # useFirstVisible = firstVisible if firstVisible else self
            zPosition = orderedAxes[dim].position
            axisCode = orderedAxes[dim].code

            # get the plane count from the widgets
            planeCount = self.strip.planeAxisBars[dim - 2].planeCount  #   .planeToolbar.planeCounts[dim - 2].value()

            zPointCount = (self.spectrum.pointCounts)[indx]
            zValuePerPoint = (self.spectrum.ppmPerPoints)[indx]
            # minSpectrumFrequency, maxSpectrumFrequency = (self.spectrum.spectrumLimits)[index]

            # pass in a smaller valuePerPoint - if there are differences in the z-resolution, otherwise just use local valuePerPoint
            minZWidth = 3 * zValuePerPoint
            zWidth = (planeCount + 2) * minimumValuePerPoint[dim - 2] \
                     if minimumValuePerPoint else (planeCount + 2) * zValuePerPoint
            zWidth = max(zWidth, minZWidth)

            zRegionValue = (zPosition + 0.5 * zWidth, zPosition - 0.5 * zWidth)  # Note + and - (axis backwards)

            # ppm position to point range
            zPointFloat0 = self.spectrum.ppm2point(zRegionValue[0], axisCode=axisCode) - 1
            zPointFloat1 = self.spectrum.ppm2point(zRegionValue[1], axisCode=axisCode) - 1

            # convert to integers
            zPointInt0, zPointInt1 = (
                int(zPointFloat0 + (1 if zPointFloat0 >= 0 else 0)),  # this gives first and 1+last integer in range
                int(zPointFloat1 + (1 if zPointFloat1 >= 0 else 0)))  # and takes into account negative ppm2Point

            if zPointInt0 == zPointInt1:
                # only one plane visible, need to 2 points for range()
                if zPointFloat0 - (zPointInt0 - 1) < zPointInt1 - zPointFloat1:  # which is closest to an integer
                    zPointInt0 -= 1
                else:
                    zPointInt1 += 1

            # check that the point values are not outside the maximum aliasing limits
            zPointInt0 = max(zPointInt0, -MAXALIASINGRANGE * zPointCount)
            zPointInt1 = min(zPointInt1, (MAXALIASINGRANGE + 1) * zPointCount)
            _temp = (tuple((zz % zPointCount) for zz in range(zPointInt0, zPointInt1)), 0, zPointCount)
            planeList = planeList + (_temp,)

            # need to add 0.5 for the indexing in the api
            planePointValues = ()

            # not sure tha the ppm's are needed here
            # planePointValues = planePointValues + ((tuple(self.spectrum.ppm2point(zz + 0.5, axisCode=axisCode)
            #                                               for zz in range(zPointInt0, zPointInt1 + 1)), zPointOffset, zPointCount),)

        return planeList, planePointValues, dimIndices

    def getVisibleState(self, dimensionCount=None):
        """Get the visible state for the X/Y axes
        """
        if not dimensionCount:
            dimensionCount = self.spectrum.dimensionCount

        return tuple(self._getSpectrumViewParams(vParam) for vParam in range(0, dimensionCount))

    def refreshData(self):
        # spawn a rebuild in the openGL strip
        self.buildContours = True

        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=self)
        GLSignals.emitPaintEvent()

    def _getSliceData(self, points, sliceDim):
        """Get the slice along sliceDim.
        Separate routine to allow for caching,
        uses Spectrum._getSliceDataFromPlane for efficient extraction of slices

        points as integer list, with points[sliceDim-1] set to 1, as this allows
        the cached _getSliceFromPlane to work best

        return sliceData numpy array
        """

        # need to block logging
        with notificationEchoBlocking(self.application):
            axisCodes = [a.code for a in self.strip.axes][0:2]
            # planeDims = spectrumView.spectrum.getByAxisCodes('dimensions', axisCodes)
            pointCounts = self.spectrum.pointCounts
            pointInt = [int(round(pnt) % pointCounts[ii]) + 1 for ii, pnt in enumerate(points)]
            pointInt[sliceDim - 1] = 1  # To improve caching; points, dimensions are 1-based

            # GWV: why copy again into numpy array? the routine already returns this
            # data = np.array(spectrumView.spectrum._getSliceDataFromPlane(position=pointInt,
            #                                                              xDim=planeDims[0], yDim=planeDims[1], sliceDim=sliceDim))
            # GWV reverted to getSliceData
            data = self.spectrum.getSliceData(position=pointInt, sliceDim=sliceDim)
            if self._traceScale is None:
                self._traceScale = 1.0 / max(data) * 0.5
        return data

    def _getVisibleSpectrumViewParams(self, dimRange=None, delta=None, stacking=None) -> SpectrumCache:
        """Get parameters for axisDim'th axis (zero-origin) of spectrum in display-order.

        Returns SpectrumCache object of the form:

            dimensionIndices            visible order of dimensions

            pointCount                  number of points in the dimension
            ppmPerPoint                 ppm width spanning a point value
            ppmToPoint                  method to convert ppm to data-source point value

            minSpectrumFrequency        minimum spectrum frequency
            maxSpectrumFrequency        maximum spectrum frequency
                                        spectrum frequencies defined by the ppm positions of points [1] and [pointCount]
            spectralWidth               maxSpectrumFrequency - minSpectrumFrequency
            spectrometerFrequency       spectrometer frequency to give correct Hz/ppm/point conversion

            minAliasingFrequency        minimum aliasing frequency
            maxAliasingFrequency        maximum aliasing frequency
                                        aliasing frequencies define the span of the spectrum, beyond the range of the defined points
                                        for aliasingIndex (0, 0) this will correspond to points [0.5], [pointCount + 0.5]
            aliasingWidth               maxAliasingFrequency - minAliasingFrequency
            aliasingIndex               a tuple (min, max) defining how many integer multiples the aliasing frequencies span the spectrum
                                        (0, 0) implies the aliasing range matches the spectral range
                                        (s, t) implies:
                                            the minimum limit = minSpectrumFrequency - 's' spectral widths - should always be negative or zero
                                            the maximum limit = maxSpectrumFrequency + 't' spectral widths - should always be positive or zero
            axisDirection               1.0 if the point [pointCount] corresponds to the maximum spectrum-frequency
                                        else -1.0, i.e., ppm increases with point-count

            minFoldingFrequency         minimum folding frequency
            maxFoldingFrequency         maximum folding frequency
                                        folding frequencies define the ppm positions of points [0.5] and [pointCount + 0.5]
                                        currently the exact ppm at which the spectrum is folded
            foldingWidth                maxFoldingFrequency - minFoldingFrequency
            foldingMode                 the type of folding: 'circular', 'mirror' or None

            regionBounds                a tuple of ppm values (min, ..., max) in multiples of the spectral width from the lower aliasingLimit
                                        to the upper aliasingLimit
            isTimeDomain                True if the axis is a time domain, otherwise False

            delta                       multipliers for the axes, either -1.0|1.0
            scale                       scaling for each dimension
        """
        if self.pointCounts[0]:
            minFoldingFrequencies = [min(*val) for val in self.foldingLimits]
            spectralWidths = self.spectralWidths
            aliasingIndexes = self.aliasingIndexes
            regionBounds = [[minFoldingFrequency + ii * spectralWidth
                             for ii in range(aliasingIndex[0], aliasingIndex[1] + 2)]
                            for minFoldingFrequency, spectralWidth, aliasingIndex in
                            zip(minFoldingFrequencies, spectralWidths, aliasingIndexes)]

            minSpec = [min(*val) for val in self.spectrumLimits][:2]
            maxSpec = [max(*val) for val in self.spectrumLimits][:2]
            specWidth = list(self.spectralWidths[:2])
            axesReversed = self.axesReversed[:2]
            for ii in range(2):
                # spectrum frequencies are badly defined
                if abs(maxSpec[ii] - minSpec[ii]) < 1e-8:
                    minSpec[ii] = -1.0
                    maxSpec[ii] = 1.0
                    specWidth[ii] = 2.0

            xScale = (-1.0 if axesReversed[0] else 1.0) * specWidth[0] / self.pointCounts[0]
            yScale = (-1.0 if axesReversed[1] else 1.0) * specWidth[1] / self.pointCounts[1]

            # build the point->ppm matrices here for the display
            foldX = 1.0 if axesReversed[0] else -1.0
            foldY = 1.0 if axesReversed[1] else -1.0
            xOffset = maxSpec[0] if axesReversed[0] else minSpec[0]
            yOffset = maxSpec[1] if axesReversed[1] else minSpec[0]
            centreMatrix = None
            mvMatrices = []
            for ii, jj in product(range(aliasingIndexes[0][0], aliasingIndexes[0][1] + 1),
                                  range(aliasingIndexes[1][0], aliasingIndexes[1][1] + 1)):
                # if folding[0] == 'mirror':
                #     # to be implemented correctly later
                #     foldX = pow(-1, ii)  # WILL CHANGE FOR MIRRORED!
                #     foldXOffset = -dxAF if foldX < 0 else 0
                # if folding[1] == 'mirror':
                #     foldY = pow(-1, jj)
                #     foldYOffset = -dyAF if foldY < 0 else 0
                mm = QtGui.QMatrix4x4()
                mm.translate(xOffset + (ii * specWidth[0]),
                             yOffset + (jj * specWidth[1]))
                mm.scale(xScale * foldX, yScale * foldY, 1.0)
                mvMatrices.append(mm)
                if ii == 0 and jj == 0:
                    # SHOULD always be here
                    centreMatrix = mm
            if not centreMatrix:
                raise RuntimeError(f'{self.__class__.__name__}._getVisibleSpectrumViewParams: '
                                   f'centre matrix not defined')

            return SpectrumCache(dimensionIndices=self.dimensionIndices[:2],
                                 pointCount=self.pointCounts[:2],
                                 ppmPerPoint=self.ppmPerPoints[:2],
                                 ppmToPoint=self.ppmToPoints[:2],

                                 minSpectrumFrequency=minSpec,
                                 maxSpectrumFrequency=maxSpec,
                                 spectralWidth=specWidth,
                                 spectrometerFrequency=self.spectrometerFrequencies[:2],

                                 minAliasedFrequency=[val[0] for val in self.aliasingLimits][:2],
                                 maxAliasedFrequency=[val[1] for val in self.aliasingLimits][:2],
                                 aliasingWidth=self.aliasingWidths[:2],
                                 aliasingIndex=self.aliasingIndexes[:2],
                                 axisDirection=[-1.0 if ar else 1.0 for ar in axesReversed],

                                 minFoldingFrequency=[min(*val) for val in self.foldingLimits][:2],
                                 maxFoldingFrequency=[max(*val) for val in self.foldingLimits][:2],
                                 foldingWidth=self.foldingWidths[:2],
                                 foldingMode=self.foldingModes[:2],

                                 regionBounds=regionBounds[:2],
                                 isTimeDomain=self.isTimeDomains[:2],
                                 axisCode=self.axisCodes[:2],
                                 isotopeCode=self.isotopeCodes[:2],

                                 scale=[xScale, yScale],
                                 delta=delta,

                                 stackedMatrixOffset=[0.0, 0.0],
                                 # matrix=np.array([xScale, 0.0, 0.0, 0.0,
                                 #                  0.0, yScale, 0.0, 0.0,
                                 #                  0.0, 0.0, 1.0, 0.0,
                                 #                  maxSpec[0], maxSpec[1], 0.0, 1.0],
                                 #                 dtype=np.float32),
                                 matrix=centreMatrix,
                                 stackedMatrix=np.array([1.0, 0.0, 0.0, 0.0,
                                                         0.0, 1.0, 0.0, 0.0,
                                                         0.0, 0.0, 1.0, 0.0,
                                                         0.0, 0.0, 0.0, 1.0],
                                                        dtype=np.float32),

                                 spinningRate=self.spectrum.spinningRate,
                                 mvMatrices=mvMatrices,
                                 )

        else:
            # points are not defined for the spectrum
            return SpectrumCache(dimensionIndices=self.dimensionIndices[:2],

                                 pointCount=[1, 1],
                                 ppmPerPoint=[1.0, 1.0],
                                 ppmToPoint=[lambda: 0.0, lambda: 0.0],

                                 minSpectrumFrequency=[-1.0, -1.0],
                                 maxSpectrumFrequency=[1.0, 1.0],
                                 spectralWidth=[2.0, 2.0],
                                 spectrometerFrequency=[0.0, 0.0],

                                 minAliasedFrequency=[-1.0, -1.0],
                                 maxAliasedFrequency=[1.0, 1.0],
                                 aliasingWidth=[2.0, 2.0],
                                 aliasingIndex=[[0, 0], [0, 0]],
                                 axisDirection=[1.0, 1.0],

                                 minFoldingFrequency=[-1.0, -1.0],
                                 maxFoldingFrequency=[1.0, 1.0],
                                 foldingWidth=[2.0, 2.0],
                                 foldingMode=[0, 0],

                                 regionBounds=[[-1.0, 1.0], [-1.0, 1.0]],
                                 isTimeDomain=[False, False],
                                 axisCode=['', ''],
                                 isotopeCode=['', ''],

                                 scale=[1.0, 1.0],
                                 delta=[1.0, 1.0],

                                 stackedMatrixOffset=[0.0, 0.0],
                                 matrix=np.array([1.0, 0.0, 0.0, 0.0,
                                                  0.0, 1.0, 0.0, 0.0,
                                                  0.0, 0.0, 1.0, 0.0,
                                                  0.0, 0.0, 0.0, 1.0],
                                                 dtype=np.float32),
                                 stackedMatrix=np.array([1.0, 0.0, 0.0, 0.0,
                                                         0.0, 1.0, 0.0, 0.0,
                                                         0.0, 0.0, 1.0, 0.0,
                                                         0.0, 0.0, 0.0, 1.0],
                                                        dtype=np.float32),

                                 spinningRate=0.0,
                                 )
