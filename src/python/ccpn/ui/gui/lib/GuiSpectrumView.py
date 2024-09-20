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
__dateModified__ = "$dateModified: 2024-08-07 13:10:49 +0100 (Wed, August 07, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
import numpy as np
import collections
from dataclasses import dataclass, field
from ccpn.util import Colour
from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.util.Logging import getLogger
from ccpn.core.lib.Notifiers import Notifier
from typing import Optional, Tuple


SpectrumViewParams = collections.namedtuple('SpectrumViewParams',
                                            'valuePerPoint pointCount minAliasedFrequency maxAliasedFrequency '
                                            'minSpectrumFrequency maxSpectrumFrequency axisReversed '
                                            'spectralWidth aliasingIndex foldingMode regionBounds '
                                            'minFoldingFrequency maxFoldingFrequency isTimeDomain '
                                            'spectrometerFrequency ppmToPoint')
TraceParameters = collections.namedtuple('TraceParameters', 'inRange pointPositions startPoint endPoint')


@dataclass(slots=True)
class SpectrumCache():
    # matrix: np.array = None
    matrix: QtGui.QMatrix4x4 = None
    stackedMatrix: np.array = None
    spinningRate: float = None

    dimensionIndices: list = field(default_factory=list)

    pointCount: list = field(default_factory=list)
    ppmPerPoint: list = field(default_factory=list)
    ppmToPoint: list = field(default_factory=list)

    minSpectrumFrequency: list = field(default_factory=list)
    maxSpectrumFrequency: list = field(default_factory=list)
    spectralWidth: list = field(default_factory=list)
    spectrometerFrequency: list = field(default_factory=list)

    minAliasedFrequency: list = field(default_factory=list)
    maxAliasedFrequency: list = field(default_factory=list)
    aliasingWidth: list = field(default_factory=list)
    aliasingIndex: list = field(default_factory=list)
    axisDirection: list = field(default_factory=list)

    minFoldingFrequency: list = field(default_factory=list)
    maxFoldingFrequency: list = field(default_factory=list)
    foldingWidth: list = field(default_factory=list)
    foldingMode: list = field(default_factory=list)

    regionBounds: list = field(default_factory=list)
    isTimeDomain: list = field(default_factory=list)
    axisCode: list = field(default_factory=list)
    isotopeCode: list = field(default_factory=list)

    scale: list = field(default_factory=list)
    delta: list = field(default_factory=list)
    stackedMatrixOffset: list = field(default_factory=list)
    mvMatrices: list[QtGui.QMatrix4x4] = field(default_factory=list)


@dataclass
class AxisCache():
    valuePerPoint: tuple = field(default_factory=tuple)
    pointCount: tuple = field(default_factory=tuple)
    minAliasedFrequency: tuple = field(default_factory=tuple)
    maxAliasedFrequency: tuple = field(default_factory=tuple)
    minSpectrumFrequency: tuple = field(default_factory=tuple)
    maxSpectrumFrequency: tuple = field(default_factory=tuple)
    axisDirection: tuple = field(default_factory=tuple)
    spectralWidth: tuple = field(default_factory=tuple)
    aliasingIndex: tuple = field(default_factory=tuple)
    foldingMode: tuple = field(default_factory=tuple)
    regionBounds: tuple = field(default_factory=tuple)
    minFoldingFrequency: tuple = field(default_factory=tuple)
    maxFoldingFrequency: tuple = field(default_factory=tuple)
    foldingWidth: tuple = field(default_factory=tuple)
    isTimeDomain: tuple = field(default_factory=tuple)
    spectrometerFrequency: tuple = field(default_factory=tuple)
    ppmToPoint: tuple = field(default_factory=tuple)
    stackedMatrixOffset: list = field(default_factory=list)
    matrix = None
    stackedMatrix = None


@dataclass
class TraceCache():
    inRange: tuple = field(default_factory=tuple)
    pointPositions: tuple = field(default_factory=tuple)
    startPoint: tuple = field(default_factory=tuple)
    endPoint: tuple = field(default_factory=tuple)


#=========================================================================================
# GuiSpectrumView
#=========================================================================================

class GuiSpectrumView(QtWidgets.QGraphicsObject):

    #def __init__(self, guiSpectrumDisplay, apiSpectrumView, dimMapping=None):
    def __init__(self):
        """ spectrumPane is the parent
            spectrum is the Spectrum object
            dimMapping is from spectrum numerical dimensions to spectrumPane numerical dimensions
            (for example, xDim is what gets mapped to 0 and yDim is what gets mapped to 1)
        """

        QtWidgets.QGraphicsItem.__init__(self)

        self.spectrumGroupsToolBar = None

        action = self.strip.spectrumDisplay.spectrumActionDict.get(self.spectrum)
        if action and not action.isChecked():
            self.setVisible(False)

        self._showContours = True

        self.cache = None

    # To write your own graphics item, you first create a subclass of QGraphicsItem, and
    # then start by implementing its two pure virtual public functions:
    # boundingRect(), which returns an estimate of the area painted by the item,
    # and paint(), which implements the actual painting. For example:

    # mandatory function to override for QGraphicsItem
    # Implemented in GuiSpectrumViewNd or GuiSpectrumView1d
    def paint(self, painter, option, widget=None):
        pass

    # def updateGeometryChange(self):  # ejb - can we call this?
    #     self._currentBoundingRect = self.strip.plotWidget.sceneRect()
    #     self.prepareGeometryChange()
    #     # print ('>>>prepareGeometryChange', self._currentBoundingRect)

    # mandatory function to override for QGraphicsItem
    # def boundingRect(self):  # seems necessary to have
    #     return self._currentBoundingRect

    # Earlier versions too large value (~1400,1000);
    # i.e larger then initial MainWindow size; reduced to (900, 700); but (100, 150) appears
    # to give less flicker in Scrolled Strips.

    # override of Qt setVisible
    def setVisible(self, visible):
        """Change visible state of the spectrumView
        """
        QtWidgets.QGraphicsItem.setVisible(self, visible)
        self.isDisplayed = visible
        try:
            action = self.strip.spectrumDisplay.spectrumActionDict.get(self.spectrum)
            if action:
                action.setChecked(visible)
        except Exception as es:
            getLogger().debug(f'Error in setVisible {es}')  # gwv changed to debug to reduce output

        self._notifyChange()

    def setDisplayed(self, visible):
        """Change visible state of the spectrumView
        """
        QtWidgets.QGraphicsItem.setVisible(self, visible)
        self.isDisplayed = visible
        try:
            action = self.strip.spectrumDisplay.spectrumActionDict.get(self.spectrum)
            if action:
                action.setChecked(visible)
        except Exception as es:
            getLogger().debug(f'Error in setDisplayed {es}')  # gwv changed to debug to reduce output

        self._notifyChange()

    def _notifyChange(self):
        # repaint all displays - this is called for each spectrumView in the spectrumDisplay
        # all are attached to the same click
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=self)
        GLSignals.emitPaintEvent()

        # notify that the spectrumView has changed
        # self._finaliseAction('change')

    def _getSpectrumViewParams(self, axisDim: int) -> Optional[Tuple]:
        """Get parameters for axisDim'th axis (zero-origin) of spectrum.

        Returns None or namedTuple of the form:

            valuePerPoint               ppm width spanning a point value
            pointCount                  number of points in the dimension
            minAliasingFrequency        minimum aliasing frequency
            maxAliasingFrequency        maximum aliasing frequency
                                        aliasing frequencies define the span of the spectrum, beyond the range of the defined points
                                        for aliasingIndex (0, 0) this will correspond to points [0.5], [pointCount + 0.5]
            minSpectrumFrequency        minimum spectrum frequency
            maxSpectrumFrequency        maximum spectrum frequency
                                        spectrum frequencies defined by the ppm positions of points [1] and [pointCount]
            axisReversed                True if the point [pointCount] corresponds to the maximum spectrum frequency
            spectralWidth               maxSpectrumFrequency - minSpectrumFrequency
            aliasingIndex               a tuple (min, max) defining how many integer multiples the aliasing frequencies span the spectrum
                                        (0, 0) implies the aliasing range matches the spectral range
                                        (s, t) implies:
                                            the minimum limit = minSpectrumFrequency - 's' spectral widths - should always be negative or zero
                                            the maximum limit = maxSpectrumFrequency + 't' spectral widths - should always be positive or zero
            foldingMode                 the type of folding: 'circular', 'mirror' or None
            regionBounds                a tuple of ppm values (min, ..., max) in multiples of the spectral width from the lower aliasingLimit
                                        to the upper aliasingLimit
            minFoldingFrequency         minimum folding frequency
            maxFoldingFrequency         maximum folding frequency
                                        folding frequencies define the ppm positions of points [0.5] and [pointCount + 0.5]
                                        currently the exact ppm at which the spectrum is folded
            isTimeDomain                True if the axis is a time domain, otherwise False
            spectrometerFrequency       spectrometer frequency to give correct Hz
            ppmToPoint                  method to convert ppm to data-source point value
        """

        ii = self.dimensionIndices[axisDim]
        if ii is not None:
            _spectrum = self.spectrum
            # extent of the spectrum
            minAliasedFrequency, maxAliasedFrequency = (_spectrum.aliasingLimits)[ii]
            # ppmPositions of the first and last point
            minSpectrumFrequency, maxSpectrumFrequency = sorted(_spectrum.spectrumLimits[ii])
            # spectrumLimits extended by 0.5point on either end
            minFoldingFrequency, maxFoldingFrequency = sorted(_spectrum.foldingLimits[ii])
            pointCount = (_spectrum.pointCounts)[ii]
            valuePerPoint = (_spectrum.ppmPerPoints)[ii]
            axisReversed = (_spectrum.axesReversed)[ii]
            spectralWidth = (_spectrum.spectralWidths)[ii]
            aliasingIndex = (_spectrum.aliasingIndexes)[ii]
            foldingMode = (_spectrum.foldingModes)[ii]
            regionBounds = tuple(minFoldingFrequency + ii * spectralWidth
                                 for ii in range(aliasingIndex[0], aliasingIndex[1] + 2))
            isTimeDomain = (_spectrum.isTimeDomains)[ii]
            spectrometerFrequency = (_spectrum.spectrometerFrequencies)[ii]
            ppmToPoint = (_spectrum.ppmToPoints)[ii]

            return SpectrumViewParams(valuePerPoint, pointCount,
                                      minAliasedFrequency, maxAliasedFrequency,
                                      minSpectrumFrequency, maxSpectrumFrequency,
                                      axisReversed, spectralWidth, aliasingIndex,
                                      foldingMode, regionBounds,
                                      minFoldingFrequency, maxFoldingFrequency,
                                      isTimeDomain, spectrometerFrequency, ppmToPoint)

    def _getVisibleSpectrumViewParams(self, dimRange=None, delta=None, stacking=None) -> SpectrumCache:
        """Get parameters for axisDim'th axis (zero-origin) of spectrum.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: function {repr(sys._getframe().f_code.co_name)} not implemented')

    def _refreshCache(self) -> Optional[Tuple]:
        """Get parameters for axisDim'th axis (zero-origin) of spectrum.

        Returns None or namedTuple of the form:

            valuePerPoint               ppm width spanning a point value
            pointCount                  number of points in the dimension
            minAliasingFrequency        minimum aliasing frequency
            maxAliasingFrequency        maximum aliasing frequency
                                        aliasing frequencies define the span of the spectrum, beyond the range of the defined points
                                        for aliasingIndex (0, 0) this will correspond to points [0.5], [pointCount + 0.5]
            minSpectrumFrequency        minimum spectrum frequency
            maxSpectrumFrequency        maximum spectrum frequency
                                        spectrum frequencies defined by the ppm positions of points [1] and [pointCount]
            axisReversed                True if the point [pointCount] corresponds to the maximum spectrum frequency
            spectralWidth               maxSpectrumFrequency - minSpectrumFrequency
            aliasingIndex               a tuple (min, max) defining how many integer multiples the aliasing frequencies span the spectrum
                                        (0, 0) implies the aliasing range matches the spectral range
                                        (s, t) implies:
                                            the minimum limit = minSpectrumFrequency - 's' spectral widths - should always be negative or zero
                                            the maximum limit = maxSpectrumFrequency + 't' spectral widths - should always be positive or zero
            foldingMode                 the type of folding: 'circular', 'mirror' or None
            regionBounds                a tuple of ppm values (min, ..., max) in multiples of the spectral width from the lower aliasingLimit
                                        to the upper aliasingLimit
            minFoldingFrequency         minimum folding frequency
            maxFoldingFrequency         maximum folding frequency
                                        folding frequencies define the ppm positions of points [0.5] and [pointCount + 0.5]
                                        currently the exact ppm at which the spectrum is folded
            isTimeDomain                True if the axis is a time domain, otherwise False
            spectrometerFrequency       spectrometer frequency to give correct Hz
            ppmToPoint                  method to convert ppm to data-source point value
        """
        minFoldingFrequencies = tuple(min(*val) for val in self.foldingLimits)
        spectralWidths = self.spectralWidths
        aliasingIndexes = self.aliasingIndexes
        regionBounds = tuple(tuple(minFoldingFrequency + ii * spectralWidth
                                   for ii in range(aliasingIndex[0], aliasingIndex[1] + 2))
                             for minFoldingFrequency, spectralWidth, aliasingIndex in
                             zip(minFoldingFrequencies, spectralWidths, aliasingIndexes))

        # NOTE:ED - fill with defaults if the pointCount is not defined
        #       specialise for 1d depending on the view order
        #       i.e., fill one axis with defaults, other with correct values
        #       OR let guiSpectrumView1d sort it?

        return SpectrumViewParams(self.ppmPerPoints, self.pointCounts,
                                  tuple(val[0] for val in self.aliasingLimits),
                                  tuple(val[1] for val in self.aliasingLimits),
                                  tuple(min(*val) for val in self.spectrumLimits),
                                  tuple(max(*val) for val in self.spectrumLimits),
                                  self.axesReversed, self.spectralWidths,
                                  self.aliasingIndexes, self.foldingModes,
                                  regionBounds,
                                  tuple(min(*val) for val in self.foldingLimits),
                                  tuple(max(*val) for val in self.foldingLimits),
                                  self.isTimeDomains, self.spectrometerFrequencies, self.ppmToPoints,
                                  )

    def getTraceParameters(self, position, dim):
        # dim  = spectrumView index, i.e. 0 for X, 1 for Y

        _indices = self.dimensionIndices
        index = _indices[dim]
        if index is None:
            getLogger().warning('getTraceParameters: bad index')
            return

        pointCount = self.spectrum.pointCounts[index]
        minSpectrumFrequency, maxSpectrumFrequency = sorted(self.spectrum.spectrumLimits[index])

        inRange = (minSpectrumFrequency <= position[index] <= maxSpectrumFrequency)
        pointPos = (self.spectrum.ppm2point(position[index], dimension=index + 1) - 1) % pointCount

        return TraceParameters(inRange, pointPos, 0, pointCount - 1)

    def _getColour(self, colourAttr, defaultColour=None):

        colour = getattr(self, colourAttr)
        if not colour:
            colour = defaultColour

        colour = Colour.colourNameToHexDict.get(colour, colour)  # works even if None

        return colour

    def refreshData(self):
        """refresh/rebuild contour data.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")


def _spectrumViewHasChanged(data):
    """Change action icon colour and other changes when spectrumView changes.

    NB SpectrumView change notifiers are triggered when either DataSource or ApiSpectrumView change.
    """
    self = data[Notifier.OBJECT]

    if self.isDeleted:
        return

    spectrumDisplay = self.strip.spectrumDisplay

    # Update action icon colour
    action = spectrumDisplay.spectrumActionDict.get(self.spectrum)
    if action:
        # add spectrum action for non-grouped action
        _addActionIcon(action, self, spectrumDisplay)

    # if spectrumDisplay.isGrouped and self in spectrumDisplay.spectrumViews:
    #     if hasattr(self, '_guiChanged'):
    if self in spectrumDisplay.spectrumViews and hasattr(self, '_guiChanged'):
        del self._guiChanged

        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=self)

        self.buildContoursOnly = True

        # repaint
        GLSignals.emitPaintEvent()

    # Update strip
    self.strip.update()


def _addActionIcon(action, self, spectrumDisplay):
    _iconX = int(60 / spectrumDisplay.devicePixelRatio())
    _iconY = int(10 / spectrumDisplay.devicePixelRatio())
    pix = QtGui.QPixmap(QtCore.QSize(_iconX, _iconY))

    if getattr(self, '_showContours', True) or spectrumDisplay.isGrouped:
        if spectrumDisplay.is1D:
            _col = self.sliceColour
        else:
            _col = self.positiveContourColour

        if _col and _col.startswith('#'):
            pix.fill(QtGui.QColor(_col))

        elif _col in Colour.colorSchemeTable:
            colourList = Colour.colorSchemeTable[_col]

            step = _iconX
            stepX = _iconX
            stepY = len(colourList) - 1
            jj = 0
            painter = QtGui.QPainter(pix)

            for ii in range(_iconX):
                _interp = (stepX - step) / stepX
                _intCol = Colour.interpolateColourHex(colourList[min(jj, stepY)], colourList[min(jj + 1, stepY)],
                                                      _interp)

                painter.setPen(QtGui.QColor(_intCol))
                painter.drawLine(ii, 0, ii, _iconY)
                step -= stepY
                while step < 0:
                    step += stepX
                    jj += 1

            painter.end()

        else:
            pix.fill(QtGui.QColor('gray'))
    else:
        pix.fill(QtGui.QColor('gray'))

    action.setIcon(QtGui.QIcon(pix))
