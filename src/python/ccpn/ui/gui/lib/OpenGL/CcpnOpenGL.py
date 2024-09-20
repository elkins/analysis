"""
By Functionality:

Zoom and pan:
    Left-drag:                          pans the spectrum.

    shift-left-drag:                    draws a zooming box and zooms the viewing window.
    shift-middle-drag:                  draws a zooming box and zooms the viewing window.
    shift-right-drag:                   draws a zooming box and zooms the viewing window.
    Two successive shift-right-clicks:  define zoombox
    control-right click:                reset the zoom

Peaks:
    Left-click:                         select peak near cursor in a spectrum display, deselecting others
    Control(Cmd)-left-click:            (de)select peak near cursor in a spectrum display, adding/removing to selection.
    Control(Cmd)-left-drag:             selects peaks in an area specified by the dragged region.
    Middle-drag:                        Moves a selected peak.
    Control(Cmd)-Shift-Left-click:      picks a peak at the cursor position, adding to selection
    Control(Cmd)-shift-left-drag:       picks peaks in an area specified by the dragged region.

Others:
    Right-click:                        raises the context menu.


By Mouse button:

    Left-click:                         select peak near cursor in a spectrum display, deselecting others
    Control(Cmd)-left-click:            (de)select peak near cursor in a spectrum display, adding/removing to selection.
    Control(Cmd)-Shift-Left-click:      picks a peak at the cursor position, adding to selection

    Left-drag:                          pans the spectrum.
    shift-left-drag:                    draws a zooming box and zooms the viewing window.
    Control(Cmd)-left-drag:             selects peaks in an area specified by the dragged region.
    Control(Cmd)-shift-left-drag:       picks peaks in an area specified by the dragged region.


    shift-middle-drag:                  draws a zooming box and zooms the viewing window.

    Right-click:                        raises the context menu.
    control-right click:                reset the zoom
    Two successive shift-right-clicks:  define zoombox

    shift-right-drag:                   draws a zooming box and zooms the viewing window.
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
__dateModified__ = "$dateModified: 2024-09-16 16:56:38 +0100 (Mon, September 16, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2018-12-20 13:28:13 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

import math
import re
import time
import numpy as np
from functools import partial
from typing import Tuple
from pyqtgraph import functions as fn
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPoint, Qt, pyqtSlot
from PyQt5.QtWidgets import QApplication, QOpenGLWidget
from PyQt5.QtGui import QSurfaceFormat
from ccpn.core.PeakList import PeakList
from ccpn.core.Peak import Peak
from ccpn.core.Integral import Integral
from ccpn.core.Multiplet import Multiplet
from ccpn.ui.gui.lib.mouseEvents import getCurrentMouseMode
from ccpn.ui.gui.lib.GuiStrip import (DefaultMenu, PeakMenu, IntegralMenu,
                                      MultipletMenu, PhasingMenu, AxisMenu)
from ccpn.ui.gui.guiSettings import (CCPNGLWIDGET_BACKGROUND, CCPNGLWIDGET_FOREGROUND, CCPNGLWIDGET_PICKCOLOUR,
                                     CCPNGLWIDGET_GRID, CCPNGLWIDGET_HIGHLIGHT, CCPNGLWIDGET_LABELLING,
                                     CCPNGLWIDGET_PHASETRACE, getColours,
                                     CCPNGLWIDGET_HEXBACKGROUND, CCPNGLWIDGET_ZOOMAREA, CCPNGLWIDGET_PICKAREA,
                                     CCPNGLWIDGET_SELECTAREA, CCPNGLWIDGET_ZOOMLINE, CCPNGLWIDGET_MOUSEMOVELINE,
                                     CCPNGLWIDGET_HARDSHADE, CCPNGLWIDGET_BADAREA, CCPNGLWIDGET_BUTTON_FOREGROUND)
from ccpn.ui.gui.lib.mouseEvents import (leftMouse, shiftLeftMouse, controlLeftMouse, controlShiftLeftMouse,
                                         controlShiftRightMouse,
                                         middleMouse, shiftMiddleMouse, rightMouse, shiftRightMouse, controlRightMouse,
                                         PICK,
                                         makeDragEvent)
from ccpn.ui.gui.lib.OpenGL import GL
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLNotifier import GLNotifier
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLGlobal import GLGlobalData
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLFonts import GLString
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLSimpleLabels import GLSimpleStrings
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLArrays import (GLRENDERMODE_DRAW, GLRENDERMODE_RESCALE, GLRENDERMODE_REBUILD,
                                                     GLREFRESHMODE_REBUILD, GLVertexArray)
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLViewports import GLViewports
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLWidgets import (GLExternalRegion, GLRegion, REGION_COLOURS, GLInfiniteLine)
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLMultiplet import GLmultipletNdLabelling, GLmultiplet1dLabelling
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLPeak import GLpeakNdLabelling, GLpeak1dLabelling
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLIntegral import GLintegralNdLabelling, GLintegral1dLabelling
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLExport import GLExporter
import ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs as GLDefs
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import PaintModes
import ccpn.util.Phasing as Phasing
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.lib.mouseEvents import getMouseEventDict
from ccpn.ui.gui.lib.ModuleLib import getBlockingDialogs
from ccpn.ui.gui.lib.GuiStripContextMenus import (_hidePeaksSingleActionItems, _hideMultipletsSingleActionItems,
                                                  _setEnabledAllItems, _ARRANGELABELS,
                                                  _RESETLABELS)
from ccpn.core.lib.AxisCodeLib import getAxisCodeMatchIndices
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking, undoStackBlocking
from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.lib import Pid
from ccpn.util.Constants import AXIS_FULLATOMNAME
from ccpn.util.Logging import getLogger


UNITS_PPM = 'ppm'
UNITS_HZ = 'Hz'
UNITS_POINT = 'point'
UNITS = [UNITS_PPM, UNITS_HZ, UNITS_POINT]

ZOOMTIMERDELAY = 1
ZOOMMAXSTORE = 1
ZOOMHISTORYSTORE = 10

STRINGOFFSET = -2
removeTrailingZero = re.compile(r'^(\d*[\d.]*?)\.?0*$')

PEAKSELECT = Peak._pluralLinkName
INTEGRALSELECT = Integral._pluralLinkName
MULTIPLETSELECT = Multiplet._pluralLinkName
SELECTOBJECTS = [PEAKSELECT, INTEGRALSELECT, MULTIPLETSELECT]

CURSOR_SOURCE_NONE = None
CURSOR_SOURCE_SELF = 'self'
CURSOR_SOURCE_OTHER = 'other'

SCROLL_DELTA_LIMIT = 12.0
SCROLL_DELTA_SCALE = 12.0

AXES_MARKER_MIN_PIXEL = 10


class CcpnGLWidget(QOpenGLWidget):
    """Widget to handle all visible spectra/peaks/integrals/multiplets
    """
    painted = QtCore.pyqtSignal(object)

    AXIS_MARGINRIGHT = 50
    AXIS_MARGINBOTTOM = 25
    AXIS_LINE = 7
    AXIS_OFFSET = 3
    AXIS_INSIDE = False
    YAXISUSEEFORMAT = False
    XDIRECTION = -1.0
    YDIRECTION = -1.0
    AXISLOCKEDBUTTON = True
    AXISLOCKEDBUTTONALLSTRIPS = True
    SPECTRUMXZOOM = 1.0e1
    SPECTRUMYZOOM = 1.0e1
    SHOWSPECTRUMONPHASING = True
    XAXES = GLDefs.XAXISUNITS
    YAXES = GLDefs.YAXISUNITS
    AXIS_MOUSEYOFFSET = AXIS_MARGINBOTTOM + (0 if AXIS_INSIDE else AXIS_LINE)

    def __init__(self, strip=None, mainWindow=None, stripIDLabel=None, antiAlias=4):

        # add a flag so that scaling cannot be done until the gl attributes are initialised
        self.glReady = False

        super().__init__(strip)

        # GST add antiAliasing, no perceptible speed impact on my mac (intel iris graphics!)
        # samples = 4 is good enough but 8 also works well in terms of speed...
        try:
            self.setUpdateBehavior(QtWidgets.QOpenGLWidget.PartialUpdate)
            fmt = QSurfaceFormat()
            fmt.setSamples(antiAlias)
            self.setFormat(fmt)

            samples = self.format().samples()  # GST a use for the walrus
            if samples != antiAlias:
                getLogger().warning('hardware changed antialias level, expected %i got %i...' % (samples, antiAlias))
        except Exception as es:
            getLogger().warning(f'error during anti aliasing setup {str(es)}, anti aliasing disabled...')

        # flag to display paintGL but keep an empty screen
        self._blankDisplay = False
        self.setAutoFillBackground(False)

        if not strip:  # don't initialise if nothing there
            return

        self.strip = strip
        self.spectrumDisplay = strip.spectrumDisplay

        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = None
            self.project = None
            self.current = None

        self._preferences = self.application.preferences.general
        self.globalGL = None
        self.stripIDLabel = stripIDLabel or ''
        self.setMouseTracking(True)  # generate mouse events when button not pressed

        # always respond to mouse events
        self.setFocusPolicy(Qt.StrongFocus)
        # initialise all attributes
        self._initialiseAll()

        # set a minimum size so that the strips resize nicely
        self.setMinimumSize(self.AXIS_MARGINRIGHT + 10, self.AXIS_MARGINBOTTOM + 10)
        # initialise the pyqt-signal notifier
        self.GLSignals = GLNotifier(parent=self, strip=strip)
        self.lastPixelRatio = None
        self._setStyle()

    def _setStyle(self):
        self._checkPalette(self.palette())

    def _checkPalette(self, pal: QtGui.QPalette, *args):
        # this is effectively handled by _preferencesUpdate
        self._setColourScheme(pal)
        # set the flag to update the background in the paint event
        self._updateBackgroundColour = True
        self.update()

    def _initialiseAll(self):
        """Initialise all attributes for the display
        """
        # if self.glReady: return

        self.w = self.width()
        self.h = self.height()

        self._threads = {}
        self._threadUpdate = False

        self.lastPos = QPoint()
        self._mouseX = 0
        self._mouseY = 0
        self._mouseStart = (0.0, 0.0)
        self._mouseEnd = (0.0, 0.0)

        self.pixelX = 1.0
        self.pixelY = 1.0
        self.deltaX = 1.0
        self.deltaY = 1.0
        self.symbolX = 1.0
        self.symbolY = 1.0

        self.peakWidthPixels = 16

        # set initial axis limits - should be changed by strip.display..
        self.axisL = -1.0
        self.axisR = 1.0
        self.axisT = 1.0
        self.axisB = -1.0

        self._zoomHistory = [None] * ZOOMHISTORYSTORE
        self._zoomHistoryCurrent = 0
        self._zoomHistoryHead = 0
        self._zoomHistoryTail = 0
        self._zoomTimerLast = time.time()

        self.base = None
        self.spectrumValues = []

        self.highlighted = False
        self._drawSelectionBox = False
        self._drawMouseMoveLine = False
        self._drawDeltaOffset = False
        self._mouseInLabel = False
        self._selectionMode = 0
        self._startCoordinate = None
        self._endCoordinate = None
        self.cursorSource = CURSOR_SOURCE_NONE  # can be CURSOR_SOURCE_NONE / CURSOR_SOURCE_SELF / CURSOR_SOURCE_OTHER
        self.cursorCoordinate = np.zeros((4,), dtype=np.float32)
        self.doubleCursorCoordinate = np.zeros((4,), dtype=np.float32)

        self._shift = False
        self._command = False

        self._lastClick = None
        self._mousePressed = False
        self._draggingLabel = False
        self._lastTimeClicked = time.time_ns() // 1e6
        self._clickInterval = QtWidgets.QApplication.instance().doubleClickInterval()

        self.buildMarks = True
        self._marksList = None
        self._infiniteLines = []
        self._regionList = None
        self._orderedAxes = None
        self._axisOrder = None
        self._axisCodes = None
        self._refreshMouse = False
        self._successiveClicks = None  # GWV: Store successive click events for zooming; None means first click not set
        self._dottedCursorCoordinate = None
        self._dottedCursorVisible = None
        self._spectrumBordersVisible = True

        self.gridList = []
        self._gridVisible = True  #self._preferences.showGrid
        self._crosshairVisible = True  #self._preferences.showCrosshair
        # self._doubleCrosshairVisible = True  #self._preferences.showDoubleCrosshair
        self._sideBandsVisible = True

        self.diagonalGLList = None
        self.diagonalSideBandsGLList = None
        self.boundingBoxes = None
        self._updateAxes = True
        self.axesChanged = False
        self.axisLabelling = {'0': [], '1': []}

        self._axesVisible = True
        self._aspectRatioMode = 0
        self._aspectRatios = {}
        self._lockedAspectRatios = {}

        self._fixedAspectX = 1.0
        self._fixedAspectY = 1.0

        self._showSpectraOnPhasing = False
        self._xUnits = 0
        self._yUnits = 0

        self.modeDecimal = [False, False]

        # here for completeness, although they should be updated in rescale
        self._currentView = GLDefs.MAINVIEW
        self._currentRightAxisView = GLDefs.RIGHTAXIS
        self._currentRightAxisBarView = GLDefs.RIGHTAXISBAR
        self._currentBottomAxisView = GLDefs.BOTTOMAXIS
        self._currentBottomAxisBarView = GLDefs.BOTTOMAXISBAR

        self._oldStripIDLabel = None
        self.stripIDString = None
        self._spectrumSettings = {}
        self._newStripID = False
        self._lockedStringFalse = None
        self._lockedStringTrue = None
        self._fixedStringFalse = None
        self._fixedStringTrue = None
        self._setColourScheme()

        self._updateHTrace = False
        self._updateVTrace = False
        self._lastTracePoint = {}  # [-1, -1]
        self.showActivePhaseTrace = True

        self._applyXLimit = True  #.zoomXLimitApply
        self._applyYLimit = True  #self._preferences.zoomYLimitApply
        self._intensityLimit = True  #self._preferences.intensityLimit

        self._GLIntegralLists = {}
        self._GLIntegralLabels = {}

        self._marksAxisCodes = []

        self._regions = []
        self._infiniteLines = []
        self._buildTextFlag = True

        # define a new class holding the entire peak-list symbols and labelling
        if self.is1D:
            self._drawRightAxis = True
            self._drawBottomAxis = True
            self._fullHeightRightAxis = True
            self._fullWidthBottomAxis = True

            self._GLPeaks = GLpeak1dLabelling(parent=self, strip=self.strip,
                                              name='peaks', enableResize=True)
            self._GLIntegrals = GLintegral1dLabelling(parent=self, strip=self.strip,
                                                      name='integrals', enableResize=True)
            self._GLMultiplets = GLmultiplet1dLabelling(parent=self, strip=self.strip,
                                                        name='multiplets', enableResize=True)
        else:
            self._drawRightAxis = True
            self._drawBottomAxis = True
            self._fullHeightRightAxis = True
            self._fullWidthBottomAxis = True

            self._GLPeaks = GLpeakNdLabelling(parent=self, strip=self.strip,
                                              name='peaks', enableResize=True)
            self._GLIntegrals = GLintegralNdLabelling(parent=self, strip=self.strip,
                                                      name='integrals', enableResize=True)
            self._GLMultiplets = GLmultipletNdLabelling(parent=self, strip=self.strip,
                                                        name='multiplets', enableResize=True)

        self._buildMouse = True
        self._mouseCoords = [-1.0, -1.0]
        self.mouseString = None
        self.mouseStringDQ = None
        # self.diffMouseString = None
        self._symbolLabelling = 0
        self._symbolType = 0
        self._symbolSize = 12
        self._symbolThickness = 1
        self._multipletLabelling = 0
        self._multipletType = 0
        self._contourThickness = 1
        self._aliasEnabled = True
        self._aliasShade = 0.0
        self._aliasLabelsEnabled = True
        self._peakSymbolsEnabled = True
        self._peakLabelsEnabled = True
        self._peakArrowsEnabled = True
        self._multipletSymbolsEnabled = True
        self._multipletLabelsEnabled = True
        self._multipletArrowsEnabled = True
        self._arrowType = 0
        self._arrowSize = 0
        self._arrowMinimum = 0

        self._contourList = {}

        self._hTraces = {}
        self._vTraces = {}
        self._staticHTraces = []
        self._staticVTraces = []
        self._currentTraces = []
        self._axisXLabelling = []
        self._axisYLabelling = []
        self._axisScaleLabelling = []

        self._stackingValue = (0.0, 0.0)
        self._stackingMode = False
        self._hTraceVisible = False
        self._vTraceVisible = False
        self.w = 0
        self.h = 0

        self._uVMatrix = QtGui.QMatrix4x4()
        self._aMatrix = QtGui.QMatrix4x4()

        self.vInv = None
        self.mouseTransform = None

        self._useTexture = np.zeros((1,), dtype=int)
        self._axisScale = np.zeros((4,), dtype=np.float32)
        self._background = np.zeros((4,), dtype=np.float32)
        self._parameterList = np.zeros((4,), dtype=np.int32)
        self._updateBackgroundColour = True

        # get information from the parent class (strip)
        self.orderedAxes = self.strip.orderedAxes
        self.axisOrder = self.strip.axisOrder
        self.axisCodes = self.strip.axisCodes

        self._dragRegions = set()
        self._dragValues = {}

        self.resetRangeLimits()

        self._ordering = []
        self._visibleOrdering = []
        self._firstVisible = None
        self.visiblePlaneList = {}
        self.visiblePlaneListPointValues = {}
        self.visiblePlaneDimIndices = {}
        self._visibleSpectrumViewsChange = False
        self._matchingIsotopeCodes = False
        self._visibleOrderingDict = {}
        self._visibleOrderingAxisCodes = ()
        self._tilePosition = (0, 0)

        self.viewports = None

        self._cursorFrameCounter = GLDefs.CursorFrameCounterModes.CURSOR_DEFAULT
        self._menuActive = False
        self._disableCursorUpdate = False

    def close(self):
        self.GLSignals.glXAxisChanged.disconnect()
        self.GLSignals.glYAxisChanged.disconnect()
        self.GLSignals.glAllAxesChanged.disconnect()
        self.GLSignals.glMouseMoved.disconnect()
        self.GLSignals.glEvent.disconnect()
        self.GLSignals.glAxisLockChanged.disconnect()
        self.GLSignals.glAxisUnitsChanged.disconnect()
        self.GLSignals.glKeyEvent.disconnect()

    def threadUpdate(self):
        self.update()

    def update(self, mode=PaintModes.PAINT_ALL):
        """Update the glWidget with the correct refresh mode
        """
        self._paintMode = mode
        super().update()

    def rescale(self, rescaleOverlayText=True, rescaleMarksRulers=True,
                rescaleIntegralLists=True, rescaleRegions=True,
                rescaleSpectra=True, rescaleStaticHTraces=True,
                rescaleStaticVTraces=True, rescaleSpectrumLabels=True,
                rescaleLegend=True):
        """Change to axes of the view, axis visibility, scale and rebuild matrices when necessary
        to improve display speed
        """

        if self.strip.isDeleted or not self.globalGL:
            return

        # update the shader settings - assume axis limits have changed
        self._resizeGL()

        # calculate the aspect ratios for the current screen
        self._lockedAspectRatios = self._aspectRatios.copy()
        kx = self._getValidAspectRatioKey(self.axisCodes[0])
        ky = self._getValidAspectRatioKey(self.axisCodes[1])
        base = self._preferences._baseAspectRatioAxisCode
        if kx == base:
            if ky != base:
                self._lockedAspectRatios[ky] = abs(self._lockedAspectRatios[kx] * self.pixelY / self.pixelX)
        elif ky == base:
            if kx != base:
                self._lockedAspectRatios[kx] = abs(self._lockedAspectRatios[ky] * self.pixelX / self.pixelY)

        # rescale all the items in the scene
        if rescaleOverlayText:
            self._rescaleOverlayText()

        if rescaleMarksRulers:
            self.rescaleMarksRulers()

        if rescaleIntegralLists:
            self._GLIntegrals.rescaleIntegralLists()
            self._GLIntegrals.rescale()

        if rescaleRegions:
            self._rescaleRegions()

        if rescaleSpectra:
            self.rescaleSpectra()

        if rescaleSpectrumLabels:
            self._spectrumLabelling.rescale()

        # if rescaleLegend:
        #     self._legend.rescale()

        if rescaleStaticHTraces:
            self.rescaleStaticHTraces()

        if rescaleStaticVTraces:
            self.rescaleStaticVTraces()

    def mainViewHeight(self):
        if self.viewports:
            vp = self.viewports.getViewportFromWH(self._currentView, self.w, self.h)
            return vp.height

    def setStackingValue(self, val):
        self._stackingValue = val

    def setStackingMode(self, value):
        self._stackingMode = value
        self.rescaleSpectra()
        self._spectrumLabelling.rescale()
        self.update()

    # def setLegendMode(self, value):
    #     self._legendMode = value
    #     self._legend.rescale()
    #     self.update()

    def resetRangeLimits(self, allLimits=True):
        # reset zoom limits for the display
        self._minXRange, self._maxXRange = GLDefs.RANGELIMITS
        self._minYRange, self._maxYRange = GLDefs.RANGELIMITS
        self._maxX, self._minX = GLDefs.AXISLIMITS
        self._maxY, self._minY = GLDefs.AXISLIMITS
        if allLimits:
            self._rangeXDefined = False
            self._rangeYDefined = False
            self._minXReached = False
            self._minYReached = False
            self._maxXReached = False
            self._maxYReached = False

            self._minReached = False
            self._maxReached = False

    def rescaleSpectra(self):
        if self.strip.isDeleted:
            return
        self.updateVisibleSpectrumViews()

        self.resetRangeLimits(allLimits=False)

        for stackCount, spectrumView in enumerate(self._ordering):
            if spectrumView.isDeleted:
                self._spectrumSettings[spectrumView] = {}
                continue

            self._buildSpectrumSetting(spectrumView=spectrumView, stackCount=stackCount)

    def setXRegion(self, axisL=None, axisR=None):
        if axisL is not None:
            self.axisL = axisL
        if axisR is not None:
            self.axisR = axisR
        self._setRegion(self._orderedAxes[0], (self.axisL, self.axisR))

    def setYRegion(self, axisT=None, axisB=None):
        if axisT is not None:
            self.axisT = axisT
        if axisB is not None:
            self.axisB = axisB
        self._setRegion(self._orderedAxes[1], (self.axisT, self.axisB))

    def _setRegion(self, axisObject, value):
        """Set the region attribute in the axis object"""
        # self.strip.project._undo.increaseBlocking()
        undo = self.mainWindow.application._getUndo()
        undo.increaseBlocking()
        if axisObject:
            axisObject.region = value
        # self.strip.project._undo.decreaseBlocking()
        undo.decreaseBlocking()

    def autoRange(self):
        self._updateVisibleSpectrumViews()
        for spectrumView in self._ordering:
            if spectrumView.isDeleted:
                self._spectrumSettings[spectrumView] = {}
                continue

            self._buildSpectrumSetting(spectrumView)

            if self.XDIRECTION < 0:
                self.setXRegion(float(self._maxX), float(self._minX))
            else:
                self.setXRegion(float(self._minX), float(self._maxX))

            if self.YDIRECTION < 0:
                self.setYRegion(float(self._minY), float(self._maxY))
            else:
                self.setYRegion(float(self._maxY), float(self._minY))
            self.update()

    def refreshDevicePixelRatio(self):
        """refresh the devicePixelRatio for the viewports
        """
        # control for changing screens has now been moved to mainWindow so only one signal is needed
        # GST this most probably ought to be deferred until the drag completes...
        # possibly via an event...
        newPixelRatio = self.devicePixelRatioF()
        if newPixelRatio != self.lastPixelRatio:
            self.lastPixelRatio = newPixelRatio
            if hasattr(self, GLDefs.VIEWPORTSATTRIB) and self.viewports:
                self.viewports.devicePixelRatio = newPixelRatio

                self.buildOverlayStrings()
                for spectrumView in self._ordering:
                    for listView in spectrumView.peakListViews:
                        listView.buildLabels = True
                    for listView in spectrumView.integralListViews:
                        listView.buildLabels = True
                    for listView in spectrumView.multipletListViews:
                        listView.buildLabels = True
                self.buildMarks = True
                self.update()

    def _getValidAspectRatio(self, axisCode):
        va = [ax for ax in self._aspectRatios.keys() if ax.upper()[0] == axisCode.upper()[0]]
        if va and len(va) > 0:
            return self._aspectRatios[va[0]]
        else:
            return 1.0

    def _getValidAspectRatioKey(self, axisCode):
        """Get the valid key from the axis ratios dict - valid for _aspectRatios and _lockedAspectRatios
        """
        va = [ax for ax in self._aspectRatios.keys() if ax.upper()[0] == axisCode.upper()[0]]
        if va and len(va) > 0:
            return va[0]

    def _getValidLockedAspectRatio(self, axisCode):
        va = [ax for ax in self._lockedAspectRatios.keys() if ax.upper()[0] == axisCode.upper()[0]]
        if va and len(va) > 0:
            return abs(self._lockedAspectRatios[va[0]])
        else:
            return 1.0

    def resizeGL(self, w, h):
        """Resize event from the openGL architecture
        """
        # if self.visibleRegion().isEmpty():
        #     return

        # would need to defer resizing until first visible paint?
        # print(f'--> resizeGL   {id(self)}   {self.strip}   {not self.visibleRegion()}')

        # must be set here to catch the change of screen - possibly when unplugging a monitor
        self.refreshDevicePixelRatio()
        self.w, self.h = w, h

        if not self.glReady:
            return

        self._rescaleAllZoom()

    def _resizeGL(self):
        """Resize - update the GL settings
        update  viewports
                shader settings
                pixel ratios
        """
        if not self.viewports:
            getLogger().debug(f'viewport not defined: {self}')
            return

        shader = self._shaderPixel.bind()

        # set projection to axis coordinates
        shader.setProjection(self.axisL, self.axisR, self.axisB, self.axisT, -1.0, 1.0)
        shader.setMVMatrixToIdentity()

        # needs to be offset from (0, 0) for mouse scaling
        if self._drawRightAxis and self._drawBottomAxis:

            self._currentView = GLDefs.MAINVIEW
            self._currentRightAxisView = GLDefs.RIGHTAXIS
            self._currentRightAxisBarView = GLDefs.RIGHTAXISBAR
            self._currentBottomAxisView = GLDefs.BOTTOMAXIS
            self._currentBottomAxisBarView = GLDefs.BOTTOMAXISBAR

        elif self._drawRightAxis and not self._drawBottomAxis:

            self._currentView = GLDefs.MAINVIEWFULLHEIGHT
            self._currentRightAxisView = GLDefs.FULLRIGHTAXIS
            self._currentRightAxisBarView = GLDefs.FULLRIGHTAXISBAR

        elif not self._drawRightAxis and self._drawBottomAxis:

            self._currentView = GLDefs.MAINVIEWFULLWIDTH
            self._currentBottomAxisView = GLDefs.FULLBOTTOMAXIS
            self._currentBottomAxisBarView = GLDefs.FULLBOTTOMAXISBAR

        else:

            self._currentView = GLDefs.FULLVIEW

        vp = self.viewports.getViewportFromWH(self._currentView, self.w, self.h)
        vpwidth, vpheight = vp.width or 1, vp.height or 1
        self._uVMatrix = shader.getViewportMatrix(0, vpwidth, 0, vpheight, -1.0, 1.0)

        self.pixelX = (self.axisR - self.axisL) / vpwidth
        self.pixelY = (self.axisT - self.axisB) / vpheight
        self.deltaX = 1.0 / vpwidth
        self.deltaY = 1.0 / vpheight
        self.symbolX = abs(self._symbolSize * self.pixelX)
        self.symbolY = abs(self._symbolSize * self.pixelY)
        self.strip.pixelSizeChanged.emit(self.strip, (self.pixelX, self.pixelY))

        shader.setMVMatrixToIdentity()
        # map mouse coordinates to world coordinates - only needs to change on resize, move soon
        self._aMatrix = shader.getViewportMatrix(self.axisL, self.axisR, self.axisB, self.axisT, -1.0, 1.0)

        # calculate the screen to axes transform
        self.vInv = self._uVMatrix.inverted()
        self.mouseTransform = self._aMatrix * self.vInv[0]

        # change to the text shader
        self._axisScale = QtGui.QVector4D(self.pixelX, self.pixelY, 1.0, 1.0)
        shader = self._shaderText.bind()
        shader.setProjection(self.axisL, self.axisR, self.axisB, self.axisT, -1.0, 1.0)
        shader.setAxisScale(self._axisScale)

    def viewRange(self):
        return ((self.axisL, self.axisR),
                (self.axisT, self.axisB))

    def mainViewSize(self):
        """Return the width/height for the mainView of the OpenGL widget
        """
        if self.viewports:
            mw = self.viewports.getViewportFromWH(self._currentView, self.w, self.h)
            return (mw.width, mw.height)
        else:
            return (self.w, self.h)

    def wheelEvent(self, event):

        if self.strip and not self._ordering:  # strip.spectrumViews:
            return

        # check the movement of the wheel first
        zoomCentre = self._preferences.zoomCentreType

        # get the keyboard state
        keyModifiers = QApplication.keyboardModifiers()

        # read the deltas from wheel/touchpad
        pixDelta = event.pixelDelta()
        angDelta = event.angleDelta()

        if not pixDelta.isNull():  # not for Windows?
            x, y = pixDelta.x(), pixDelta.y()
        elif not angDelta.isNull():
            x, y = angDelta.x() / SCROLL_DELTA_SCALE, angDelta.y() / SCROLL_DELTA_SCALE
        else:
            return

        scrollDirection = x if abs(x) > abs(y) else y
        zoomScale = min(abs(scrollDirection), SCROLL_DELTA_LIMIT)

        if (keyModifiers & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier)):

            # process wheel with buttons here
            # transfer event to the correct widget for changing the plane OR raising base contour level...
            if (keyModifiers & Qt.ShiftModifier):
                # raise/lower base contour level - should be strip I think
                if self.strip.spectrumDisplay.is1D:
                    return
                if scrollDirection > 0:
                    self.strip.spectrumDisplay.raiseContourBase()
                else:
                    self.strip.spectrumDisplay.lowerContourBase()

            elif (keyModifiers & Qt.ControlModifier):
                # scroll through planes
                pT = self.strip.planeAxisBars if hasattr(self.strip, 'planeAxisBars') else None
                activePlaneAxis = self.strip.activePlaneAxis
                if pT and activePlaneAxis is not None and (activePlaneAxis - 2) < len(pT):
                    # pass the event to the correct double spinbox
                    pT[activePlaneAxis - 2].scrollPpmPosition(event)

            elif (keyModifiers & Qt.AltModifier):
                if scrollDirection > 0:
                    self.strip.spectrumDisplay.increaseSpectrumScale()
                else:
                    self.strip.spectrumDisplay.decreaseSpectrumScale()

            return

        # test whether the limits have been reached in either axis
        if (scrollDirection > 0 and self._minReached and self._aspectRatioMode) or \
                (scrollDirection < 0 and self._maxReached and self._aspectRatioMode):
            return

        zoomIn = (100.0 + zoomScale) / 100.0
        zoomOut = 100.0 / (100.0 + zoomScale)

        h = self.h
        w = self.w

        # find the correct viewport
        if (self._drawRightAxis and self._drawBottomAxis):
            mw = self.viewports.getViewportFromWH(self._currentView, w, h)
            ba = self.viewports.getViewportFromWH(self._currentBottomAxisBarView, w, h)
            ra = self.viewports.getViewportFromWH(self._currentRightAxisBarView, w, h)

        elif (self._drawBottomAxis):
            mw = self.viewports.getViewportFromWH(self._currentView, w, h)
            ba = self.viewports.getViewportFromWH(self._currentBottomAxisBarView, w, h)
            ra = (0, 0, 0, 0)

        elif (self._drawRightAxis):
            mw = self.viewports.getViewportFromWH(self._currentView, w, h)
            ba = (0, 0, 0, 0)
            ra = self.viewports.getViewportFromWH(self._currentRightAxisBarView, w, h)

        else:  # no axes visible
            mw = self.viewports.getViewportFromWH(self._currentView, w, h)
            ba = (0, 0, 0, 0)
            ra = (0, 0, 0, 0)

        mx = event.pos().x()
        my = self.height() - event.pos().y()

        tilePos = self.strip.tilePosition if self.strip else self.tilePosition
        if self.between(mx, mw[0], mw[0] + mw[2]) and self.between(my, mw[1], mw[1] + mw[3]):

            # if in the mainView

            if (scrollDirection > 0 and self._minReached) or \
                    (scrollDirection < 0 and self._maxReached):
                return

            if zoomCentre == 0:  # centre on mouse
                mb0 = (mx - mw[0]) / (mw[2] - mw[0])
                mb1 = (my - mw[1]) / (mw[3] - mw[1])
            else:  # centre on the screen
                mb0 = 0.5
                mb1 = 0.5

            mbx = self.axisL + mb0 * (self.axisR - self.axisL)
            mby = self.axisB + mb1 * (self.axisT - self.axisB)

            if scrollDirection < 0:
                self.axisL = mbx + zoomIn * (self.axisL - mbx)
                self.axisR = mbx - zoomIn * (mbx - self.axisR)
                self.axisB = mby + zoomIn * (self.axisB - mby)
                self.axisT = mby - zoomIn * (mby - self.axisT)
            else:
                self.axisL = mbx + zoomOut * (self.axisL - mbx)
                self.axisR = mbx - zoomOut * (mbx - self.axisR)
                self.axisB = mby + zoomOut * (self.axisB - mby)
                self.axisT = mby - zoomOut * (mby - self.axisT)

            self.GLSignals._emitAllAxesChanged(source=self, strip=self.strip,
                                               axisB=self.axisB, axisT=self.axisT,
                                               axisL=self.axisL, axisR=self.axisR,
                                               row=tilePos[0], column=tilePos[1],
                                               zoomAll=True)

            self._rescaleAllAxes()
            self._storeZoomHistory()

        elif self.between(mx, ba[0], ba[0] + ba[2]) and self.between(my, ba[1], ba[1] + ba[3]):

            # in the bottomAxisBar, so zoom in the X axis

            # check the X limits
            if (scrollDirection > 0 and self._minXReached) or (scrollDirection < 0 and self._maxXReached):
                return

            if zoomCentre == 0:  # centre on mouse
                mb = (mx - ba[0]) / (ba[2] - ba[0])
            else:  # centre on the screen
                mb = 0.5

            mbx = self.axisL + mb * (self.axisR - self.axisL)

            if scrollDirection < 0:
                self.axisL = mbx + zoomIn * (self.axisL - mbx)
                self.axisR = mbx - zoomIn * (mbx - self.axisR)
            else:
                self.axisL = mbx + zoomOut * (self.axisL - mbx)
                self.axisR = mbx - zoomOut * (mbx - self.axisR)

            if not self._aspectRatioMode:
                self._rescaleXAxis()
                self.GLSignals._emitXAxisChanged(source=self, strip=self.strip,
                                                 axisB=self.axisB, axisT=self.axisT,
                                                 axisL=self.axisL, axisR=self.axisR,
                                                 row=tilePos[0], column=tilePos[1],
                                                 aspectRatios=self._lockedAspectRatios)

                self._storeZoomHistory()

            else:
                self._scaleToXAxis()

                self.GLSignals._emitAllAxesChanged(source=self, strip=self.strip,
                                                   axisB=self.axisB, axisT=self.axisT,
                                                   axisL=self.axisL, axisR=self.axisR,
                                                   row=tilePos[0], column=tilePos[1])

                self._storeZoomHistory()

        elif self.between(mx, ra[0], ra[0] + ra[2]) and self.between(my, ra[1], ra[1] + ra[3]):

            # in the rightAxisBar, so zoom in the Y axis

            # check the Y limits
            if (scrollDirection > 0 and self._minYReached) or (scrollDirection < 0 and self._maxYReached):
                return

            if zoomCentre == 0:  # centre on mouse
                mb = (my - ra[1]) / (ra[3] - ra[1])
            else:  # centre on the screen
                mb = 0.5

            mby = self.axisB + mb * (self.axisT - self.axisB)

            if scrollDirection < 0:
                self.axisB = mby + zoomIn * (self.axisB - mby)
                self.axisT = mby - zoomIn * (mby - self.axisT)
            else:
                self.axisB = mby + zoomOut * (self.axisB - mby)
                self.axisT = mby - zoomOut * (mby - self.axisT)

            if not self._aspectRatioMode:
                self._rescaleYAxis()
                self.GLSignals._emitYAxisChanged(source=self, strip=self.strip,
                                                 axisB=self.axisB, axisT=self.axisT,
                                                 axisL=self.axisL, axisR=self.axisR,
                                                 row=tilePos[0], column=tilePos[1],
                                                 aspectRatios=self._lockedAspectRatios)

                self._storeZoomHistory()

            else:
                self._scaleToYAxis()

                self.GLSignals._emitAllAxesChanged(source=self, strip=self.strip,
                                                   axisB=self.axisB, axisT=self.axisT,
                                                   axisL=self.axisL, axisR=self.axisR,
                                                   row=tilePos[0], column=tilePos[1])

                self._storeZoomHistory()

    def emitAllAxesChanged(self, allStrips=False):
        """Signal all strips in the spectrumDisplay to refresh
        Strips will be scaled to the Y-Axis if aspect ratio is set to Locked/Fixed
        :param allStrips: True/False, if true, apply scaling to all strips; False, ignore the current strip in spectrumDisplay
        """
        tilePos = self.strip.tilePosition if self.strip else self.tilePosition
        self.GLSignals._emitAllAxesChanged(source=None if allStrips else self,
                                           strip=None, spectrumDisplay=self.spectrumDisplay,
                                           axisB=self.axisB, axisT=self.axisT,
                                           axisL=self.axisL, axisR=self.axisR,
                                           row=tilePos[0], column=tilePos[1])

    def emitYAxisChanged(self, allStrips=False, aspectRatios=None):
        """Signal all strips in the spectrumDisplay to refresh
        Strips will be scaled to the Y-Axis if aspect ratio is set to Locked/Fixed
        :param allStrips: True/False, if true, apply scaling to all strips; False, ignore the current strip in spectrumDisplay
        """
        tilePos = self.strip.tilePosition if self.strip else self.tilePosition
        self.GLSignals._emitYAxisChanged(source=None if allStrips else self,
                                         strip=None, spectrumDisplay=self.spectrumDisplay,
                                         axisB=self.axisB, axisT=self.axisT,
                                         axisL=self.axisL, axisR=self.axisR,
                                         row=tilePos[0], column=tilePos[1],
                                         aspectRatios=aspectRatios.copy() if aspectRatios else None)

    def emitXAxisChanged(self, allStrips=False, aspectRatios=None):
        """Signal all strips in the spectrumDisplay to refresh
        Strips will be scaled to the X-Axis if aspect ratio is set to Locked/Fixed
        :param allStrips: True/False, if true, apply scaling to all strips; False, ignore the current strip in spectrumDisplay
        """
        tilePos = self.strip.tilePosition if self.strip else self.tilePosition
        self.GLSignals._emitXAxisChanged(source=None if allStrips else self,
                                         strip=None, spectrumDisplay=self.spectrumDisplay,
                                         axisB=self.axisB, axisT=self.axisT,
                                         axisL=self.axisL, axisR=self.axisR,
                                         row=tilePos[0], column=tilePos[1],
                                         aspectRatios=aspectRatios.copy() if aspectRatios else None)

    def _scaleToXAxis(self, rescale=True, update=False):
        _useFirstDefault = getattr(self.strip.spectrumDisplay, '_useFirstDefault', False)
        if (self._aspectRatioMode or _useFirstDefault):

            if (self._aspectRatioMode == 2) or _useFirstDefault:
                ax0 = self._getValidAspectRatio(self._axisCodes[0])
                ax1 = self._getValidAspectRatio(self._axisCodes[1])
            else:
                try:
                    ax0, ax1 = self.spectrumDisplay._stripAddMode
                except:
                    ax0 = self.pixelX
                    ax1 = self.pixelY

            if self.viewports:
                vp = self.viewports.getViewportFromWH(self._currentView, self.w, self.h)
                width = vp.width
                height = vp.height
            else:
                width = (self.w - self.AXIS_MARGINRIGHT) if self._drawRightAxis else self.w
                height = (self.h - self.AXIS_MOUSEYOFFSET) if self._drawBottomAxis else self.h

            ratio = (height / width) * 0.5 * abs((self.axisL - self.axisR) * ax1 / ax0)
            mby = 0.5 * (self.axisT + self.axisB)
            self.axisB = mby + ratio * self.sign(self.axisB - mby)
            self.axisT = mby - ratio * self.sign(mby - self.axisT)

            if rescale:
                self._rescaleAllAxes(update)
        else:
            if rescale:
                self._rescaleXAxis(update)

    def _scaleToYAxis(self, rescale=True, update=False):
        _useFirstDefault = getattr(self.strip.spectrumDisplay, '_useFirstDefault', False)
        if (self._aspectRatioMode or _useFirstDefault):

            if (self._aspectRatioMode == 2) or _useFirstDefault:
                ax0 = self._getValidAspectRatio(self._axisCodes[0])
                ax1 = self._getValidAspectRatio(self._axisCodes[1])
            else:  # must be 1
                try:
                    ax0, ax1 = self.spectrumDisplay._stripAddMode
                except:
                    ax0 = self.pixelX
                    ax1 = self.pixelY

            if self.viewports:
                vp = self.viewports.getViewportFromWH(self._currentView, self.w, self.h)
                width = vp.width
                height = vp.height
            else:
                width = (self.w - self.AXIS_MARGINRIGHT) if self._drawRightAxis else self.w
                height = (self.h - self.AXIS_MOUSEYOFFSET) if self._drawBottomAxis else self.h

            ratio = (width / height) * 0.5 * abs((self.axisT - self.axisB) * ax0 / ax1)
            mbx = 0.5 * (self.axisR + self.axisL)
            self.axisL = mbx + ratio * self.sign(self.axisL - mbx)
            self.axisR = mbx - ratio * self.sign(mbx - self.axisR)

            if rescale:
                self._rescaleAllAxes()
        else:
            if rescale:
                self._rescaleYAxis(update)

    def _getSelectionBoxRatio(self, delta=(0.0, 0.0)):
        """Get the current deltas for the selection box and restrict to the aspectRatio if locked/fixed
        """
        if (self._aspectRatioMode == 2):
            ax0 = self._getValidAspectRatio(self._axisCodes[0])
            ax1 = self._getValidAspectRatio(self._axisCodes[1])
        else:  # must be 1
            ax0 = self.pixelX
            ax1 = self.pixelY

        if self.viewports:
            vp = self.viewports.getViewportFromWH(self._currentView, self.w, self.h)
            width = vp.width
            height = vp.height
        else:
            width = (self.w - self.AXIS_MARGINRIGHT) if self._drawRightAxis else self.w
            height = (self.h - self.AXIS_MOUSEYOFFSET) if self._drawBottomAxis else self.h

        if width > height:
            dy = abs(height * delta[0] * ax1 / (ax0 * width)) * self.sign(delta[1])
            return (delta[0], dy)
        else:
            dx = abs(width * delta[1] * ax0 / (ax1 * height)) * self.sign(delta[0])
            return (dx, delta[1])

    def _rescaleXAxis(self, rescale=True, update=True):
        if rescale:
            self._testAxisLimits()
            self.rescale(rescaleStaticHTraces=False)

            # spawn rebuild event for the grid
            self._updateAxes = True
            if self.gridList:
                for gr in self.gridList:
                    gr.renderMode = GLRENDERMODE_REBUILD

            # ratios have changed so rescale the peak/multiplet symbols
            self._GLPeaks.rescale()
            self._GLMultiplets.rescale()

            self._rescaleOverlayText()

        self.setXRegion()

        if update:
            self.update()

    def _rescaleYAxis(self, rescale=True, update=True):
        if rescale:
            self._testAxisLimits()
            self.rescale(rescaleStaticVTraces=False)

            # spawn rebuild event for the grid
            self._updateAxes = True
            if self.gridList:
                for gr in self.gridList:
                    gr.renderMode = GLRENDERMODE_REBUILD

            # ratios have changed so rescale the peak/multiplet symbols
            self._GLPeaks.rescale()
            self._GLMultiplets.rescale()

            self._rescaleOverlayText()

        self.setYRegion()

        if update:
            self.update()

    def _testAxisLimits(self, setLimits=False):
        xRange = abs(self.axisL - self.axisR) / 3.0
        yRange = abs(self.axisT - self.axisB) / 3.0
        self._minXReached = False
        self._minYReached = False
        self._maxXReached = False
        self._maxYReached = False

        if xRange < self._minXRange and self._rangeXDefined and self._applyXLimit:
            if setLimits:
                xMid = (self.axisR + self.axisL) / 2.0
                self.axisL = xMid - self._minXRange * self.sign(self.pixelX)
                self.axisR = xMid + self._minXRange * self.sign(self.pixelX)
            self._minXReached = True

        if yRange < self._minYRange and self._rangeYDefined and self._applyYLimit:
            if setLimits:
                yMid = (self.axisT + self.axisB) / 2.0
                self.axisT = yMid + self._minYRange * self.sign(self.pixelY)
                self.axisB = yMid - self._minYRange * self.sign(self.pixelY)
            self._minYReached = True

        if xRange > self._maxXRange and self._rangeXDefined and self._applyXLimit:
            if setLimits:
                xMid = (self.axisR + self.axisL) / 2.0
                self.axisL = xMid - self._maxXRange * self.sign(self.pixelX)
                self.axisR = xMid + self._maxXRange * self.sign(self.pixelX)
            self._maxXReached = True

        if yRange > self._maxYRange and self._rangeYDefined and self._applyYLimit:
            if setLimits:
                yMid = (self.axisT + self.axisB) / 2.0
                self.axisT = yMid + self._maxYRange * self.sign(self.pixelY)
                self.axisB = yMid - self._maxYRange * self.sign(self.pixelY)
            self._maxYReached = True

        self._minReached = self._minXReached or self._minYReached
        self._maxReached = self._maxXReached or self._maxYReached

    def _rescaleAllZoom(self, rescale=True):
        """Reset the zoom to fit the spectra, including aspect checking
        """
        if self.strip.isDeleted:
            return

        _useFirstDefault = getattr(self.strip.spectrumDisplay, '_useFirstDefault', False)
        if (self._aspectRatioMode or _useFirstDefault):

            # check which is the primary axis and update the opposite axis - similar to wheelEvent
            if self.spectrumDisplay.stripArrangement == 'Y':

                # strips are arranged in a row
                self._scaleToYAxis(rescale=rescale)

            elif self.spectrumDisplay.stripArrangement == 'X':

                # strips are arranged in a column
                self._scaleToXAxis(rescale=rescale)

            elif self.spectrumDisplay.stripArrangement == 'T':

                # NOTE:ED - Tiled plots not fully implemented yet
                getLogger().warning(f'Tiled plots not implemented for spectrumDisplay: '
                                    f'{str(self.spectrumDisplay.pid)}')

            else:
                getLogger().warning(f'Strip direction is not defined for spectrumDisplay: '
                                    f'{str(self.spectrumDisplay.pid)}')

        else:
            self.rescale()

            # put stuff in here that will change on a resize
            self._updateAxes = True
            for gr in self.gridList:
                gr.renderMode = GLRENDERMODE_REBUILD
            self._GLPeaks.rescale()
            self._GLMultiplets.rescale()

        self._clearAndUpdate()
        self.update()

        self.emitAllAxesChanged(allStrips=True)

    def _rescaleAllAxes(self, mouseMoveOnly=False, update=True):
        self._testAxisLimits()
        self.rescale(rescaleStaticHTraces=True, rescaleStaticVTraces=True,
                     rescaleSpectra=not mouseMoveOnly)

        # spawn rebuild event for the grid
        self._updateAxes = True
        if self.gridList:
            for gr in self.gridList:
                gr.renderMode = GLRENDERMODE_REBUILD

        if not mouseMoveOnly:
            # if (self._useLockedAspect or self._useDefaultAspect):
            # ratios have changed so rescale the peak/multiplet symbols
            self._GLPeaks.rescale()
            self._GLMultiplets.rescale()

        self._rescaleOverlayText()
        self.setXRegion()
        self.setYRegion()

        if update:
            self.update()

    def _movePeaks(self, direction: str = 'up'):
        """Move the peaks with the cursor keys
        """
        # this is a bit convoluted
        if len(self.current.peaks) < 1:
            return

        moveFactor = 5
        moveDict = {
            'left' : (-self.pixelX * moveFactor, 0),
            'right': (self.pixelX * moveFactor, 0),
            'up'   : (0, self.pixelX * moveFactor),
            'down' : (0, -self.pixelX * moveFactor)
            }

        if direction in moveDict:
            with undoBlockWithoutSideBar():
                for peak in self.current.peaks:
                    self._movePeak(peak, moveDict.get(direction))

    def _panSpectrum(self, direction, movePercent=20):
        """Implements Arrows up,down, left, right to pan the spectrum """
        # percentage of the view to set as single step

        moveFactor = movePercent / 100.0
        dx = (self.axisR - self.axisL) / 2.0
        dy = (self.axisT - self.axisB) / 2.0

        if direction == 'left':
            self.axisL -= moveFactor * dx
            self.axisR -= moveFactor * dx

        elif direction == 'up':
            self.axisT += moveFactor * dy
            self.axisB += moveFactor * dy

        elif direction == 'right':
            self.axisL += moveFactor * dx
            self.axisR += moveFactor * dx

        elif direction == 'down':
            self.axisT -= moveFactor * dy
            self.axisB -= moveFactor * dy

        elif direction == 'plus':
            self._testAxisLimits()
            if self._minReached:
                return

            self.zoomIn()

        elif direction == 'minus':
            self._testAxisLimits()
            if self._maxReached:
                return

            self.zoomOut()

        else:
            # not a movement key
            return

        tilePos = self.strip.tilePosition if self.strip else self.tilePosition
        self.GLSignals._emitAllAxesChanged(source=self, strip=self.strip,
                                           axisB=self.axisB, axisT=self.axisT,
                                           axisL=self.axisL, axisR=self.axisR,
                                           row=tilePos[0], column=tilePos[1])

        self._rescaleAllAxes()
        self._storeZoomHistory()

    def _panGLSpectrum(self, key, movePercent=20):
        """Implements Arrows up,down, left, right to pan the spectrum """
        # percentage of the view to set as single step

        moveFactor = movePercent / 100.0
        dx = (self.axisR - self.axisL) / 2.0
        dy = (self.axisT - self.axisB) / 2.0

        if key == QtCore.Qt.Key_Left:
            self.axisL -= moveFactor * dx
            self.axisR -= moveFactor * dx

        elif key == QtCore.Qt.Key_Up:
            self.axisT += moveFactor * dy
            self.axisB += moveFactor * dy

        elif key == QtCore.Qt.Key_Right:
            self.axisL += moveFactor * dx
            self.axisR += moveFactor * dx

        elif key == QtCore.Qt.Key_Down:
            self.axisT -= moveFactor * dy
            self.axisB -= moveFactor * dy

        elif key == QtCore.Qt.Key_Plus or key == QtCore.Qt.Key_Equal:  # Plus:
            self._testAxisLimits()
            if self._minReached:
                return

            self.zoomIn()

        elif key == QtCore.Qt.Key_Minus:
            self._testAxisLimits()
            if self._maxReached:
                return

            self.zoomOut()

        else:
            # not a movement key
            return

        tilePos = self.strip.tilePosition if self.strip else self.tilePosition
        self.GLSignals._emitAllAxesChanged(source=self, strip=self.strip,
                                           axisB=self.axisB, axisT=self.axisT,
                                           axisL=self.axisL, axisR=self.axisR,
                                           row=tilePos[0], column=tilePos[1])

        self._rescaleAllAxes()
        self._storeZoomHistory()

    def _moveAxes(self, delta=(0.0, 0.0)):
        """Implements Arrows up,down, left, right to pan the spectrum """
        # percentage of the view to set as single step

        self.axisL += delta[0]
        self.axisR += delta[0]
        self.axisT += delta[1]
        self.axisB += delta[1]

        tilePos = self.strip.tilePosition if self.strip else self.tilePosition
        self.GLSignals._emitAllAxesChanged(source=self, strip=self.strip,
                                           axisB=self.axisB, axisT=self.axisT,
                                           axisL=self.axisL, axisR=self.axisR,
                                           row=tilePos[0], column=tilePos[1])
        self._rescaleAllAxes()

    def initialiseAxes(self, strip=None):
        """set up the correct axis range and padding
        """
        self.orderedAxes = strip.orderedAxes
        self._axisCodes = strip.axisCodes
        self._axisOrder = strip.axisOrder

        axis = self.orderedAxes[0]
        if axis:
            # trap missing axis for a bad strip
            region = axis.region
            if self.XDIRECTION < 0:
                self.axisL = max(region[0], region[1])
                self.axisR = min(region[0], region[1])
            else:
                self.axisL = min(region[0], region[1])
                self.axisR = max(region[0], region[1])
            # self._xUnits = axis._unitIndex

        axis = self.orderedAxes[1]
        if axis:
            # trap missing axis for a bad strip
            region = axis.region
            if self.YDIRECTION < 0:
                self.axisB = max(region[0], region[1])
                self.axisT = min(region[0], region[1])
            else:
                self.axisB = min(region[0], region[1])
                self.axisT = max(region[0], region[1])
            # if not self.spectrumDisplay.is1D:
            #     self._yUnits = axis._unitIndex

        self.update()

    def zoom(self, xRegion: Tuple[float, float], yRegion: Tuple[float, float]):
        """Zooms strip to the specified region
        """
        if self.XDIRECTION < 0:
            self.axisL = max(xRegion[0], xRegion[1])
            self.axisR = min(xRegion[0], xRegion[1])
        else:
            self.axisL = min(xRegion[0], xRegion[1])
            self.axisR = max(xRegion[0], xRegion[1])

        if self.YDIRECTION < 0:
            self.axisB = max(yRegion[0], yRegion[1])
            self.axisT = min(yRegion[0], yRegion[1])
        else:
            self.axisB = min(yRegion[0], yRegion[1])
            self.axisT = max(yRegion[0], yRegion[1])
        self._rescaleAllAxes()

    def zoomX(self, x1: float, x2: float):
        """Zooms x-axis of strip to the specified region
        """
        if self.XDIRECTION < 0:
            self.axisL = max(x1, x2)
            self.axisR = min(x1, x2)
        else:
            self.axisL = min(x1, x2)
            self.axisR = max(x1, x2)
        self._rescaleXAxis()

    def zoomY(self, y1: float, y2: float):
        """Zooms y-axis of strip to the specified region
        """
        if self.YDIRECTION < 0:
            self.axisB = max(y1, y2)
            self.axisT = min(y1, y2)
        else:
            self.axisB = min(y1, y2)
            self.axisT = max(y1, y2)
        self._rescaleYAxis()

    def resetXZoom(self):
        self._resetAxisRange(xAxis=True, yAxis=False)

        self._zoomHistoryCurrent = self._zoomHistoryHead
        self._storeZoomHistory()

        self._rescaleXAxis()

    def resetYZoom(self):
        self._resetAxisRange(xAxis=False, yAxis=True)

        self._zoomHistoryCurrent = self._zoomHistoryHead
        self._storeZoomHistory()

        self._rescaleYAxis()

    def resetAllZoom(self):
        self._resetAxisRange(xAxis=True, yAxis=True)

        self._zoomHistoryCurrent = self._zoomHistoryHead
        self._storeZoomHistory()

        self._rescaleAllAxes()

    def _storeZoomHistory(self, force=False):
        """Store the current axis state to the zoom history
        """
        currentAxis = (self.axisL, self.axisR, self.axisB, self.axisT)
        zC = self._zoomHistoryCurrent % len(self._zoomHistory)

        # store the current value if current zoom has not been set
        if self._zoomHistory[zC] is None:
            self._zoomHistory[zC] = currentAxis

        if self._widthsChangedEnough(currentAxis, self._zoomHistory[zC], tol=1e-8) or force:
            currentTime = time.time()
            if currentTime - self._zoomTimerLast < ZOOMTIMERDELAY:

                # still on the current zoom item - write new value
                self._zoomHistory[zC] = currentAxis

            else:
                # increment the head of the zoom history
                self._zoomHistoryCurrent += 1
                zC = self._zoomHistoryCurrent % len(self._zoomHistory)
                self._zoomHistory[zC] = currentAxis
                self._zoomHistoryHead = self._zoomHistoryCurrent
                if (self._zoomHistoryHead - self._zoomHistoryTail) >= len(self._zoomHistory):
                    self._zoomHistoryTail = self._zoomHistoryHead - len(self._zoomHistory) + 1

            # reset the timer, so you have to wait another 5 seconds
            self._zoomTimerLast = currentTime

    def previousZoom(self):
        """Move to the previous stored zoom
        """
        if self._zoomHistoryCurrent > self._zoomHistoryTail:
            self._zoomHistoryCurrent -= 1

            restoredZooms = self._zoomHistory[self._zoomHistoryCurrent % len(self._zoomHistory)]
            if restoredZooms:
                # only update if a zoom as been stored
                self.axisL, self.axisR, self.axisB, self.axisT = restoredZooms[0], restoredZooms[1], restoredZooms[2], \
                    restoredZooms[3]
                # use this because it rescales all the symbols
                self._rescaleXAxis()

    def nextZoom(self):
        """Move to the next stored zoom
        """
        if self._zoomHistoryCurrent < self._zoomHistoryHead:
            self._zoomHistoryCurrent += 1

            restoredZooms = self._zoomHistory[self._zoomHistoryCurrent % len(self._zoomHistory)]
            if restoredZooms:
                # only update if a zoom as been stored
                self.axisL, self.axisR, self.axisB, self.axisT = restoredZooms[0], restoredZooms[1], restoredZooms[2], \
                    restoredZooms[3]
                # use this because it rescales all the symbols
                self._rescaleXAxis()

    def storeZoom(self):
        """Store the current axis values to the zoom stack
        Sets this to the top of the stack, removing everything after
        """
        self._storeZoomHistory(force=True)

    @property
    def zoomState(self):
        return (self.axisL, self.axisR, self.axisB, self.axisT)

    def restoreZoom(self, zoomState=None):
        """Restore zoom to the last stored zoom
        zoomState = (axisL, axisR, axisB, axisT)
        """
        if self._zoomHistoryCurrent < self._zoomHistoryHead:
            self._zoomHistoryCurrent = self._zoomHistoryHead

            restoredZooms = self._zoomHistory[self._zoomHistoryCurrent % len(self._zoomHistory)]
            if restoredZooms:
                # only update if a zoom as been stored
                self.axisL, self.axisR, self.axisB, self.axisT = restoredZooms[0], restoredZooms[1], restoredZooms[2], \
                    restoredZooms[3]
                # use this because it rescales all the symbols
                self._rescaleXAxis()

    def resetZoom(self):
        self._resetAxisRange()
        self._rescaleAllAxes()

    def zoomIn(self):
        zoomPercent = -self._preferences.zoomPercent / 100.0
        dx = (self.axisR - self.axisL) / 2.0
        dy = (self.axisT - self.axisB) / 2.0
        self.axisL -= zoomPercent * dx
        self.axisR += zoomPercent * dx
        self.axisT += zoomPercent * dy
        self.axisB -= zoomPercent * dy

        self._rescaleAllAxes()
        self.emitAllAxesChanged(allStrips=True)

    def zoomOut(self):
        zoomPercent = self._preferences.zoomPercent / 100.0
        dx = (self.axisR - self.axisL) / 2.0
        dy = (self.axisT - self.axisB) / 2.0
        self.axisL -= zoomPercent * dx
        self.axisR += zoomPercent * dx
        self.axisT += zoomPercent * dy
        self.axisB -= zoomPercent * dy

        self._rescaleAllAxes()
        self.emitAllAxesChanged(allStrips=True)

    def _resetAxisRange(self, xAxis=True, yAxis=True):
        """
        reset the axes to the limits of the spectra in this view
        """
        # set a default empty axisRange
        axisLimits = []

        # iterate over spectrumViews
        for spectrumView in self._ordering:  # strip.spectrumViews:
            if spectrumView.isDeleted:
                continue

            fxMin, fyMin = self._spectrumSettings[spectrumView].minSpectrumFrequency
            fxMax, fyMax = self._spectrumSettings[spectrumView].maxSpectrumFrequency

            if not axisLimits:
                axisLimits = [fxMax, fxMin, fyMax, fyMin]
            else:
                axisLimits[0] = max(axisLimits[0], fxMax)
                axisLimits[1] = min(axisLimits[1], fxMin)
                axisLimits[2] = max(axisLimits[2], fyMax)
                axisLimits[3] = min(axisLimits[3], fyMin)

        if axisLimits:
            if xAxis:
                if self.XDIRECTION < 0:
                    self.axisL, self.axisR = axisLimits[0:2]
                else:
                    self.axisR, self.axisL = axisLimits[0:2]

            if yAxis:
                if self.YDIRECTION < 0:
                    self.axisB, self.axisT = axisLimits[2:4]
                else:
                    self.axisT, self.axisB = axisLimits[2:4]

        self._rescaleAllZoom(rescale=False)

    def initializeGL(self):
        # GLversionFunctions = self.context().versionFunctions()
        # GLversionFunctions.initializeOpenGLFunctions()
        # self._GLVersion = GLversionFunctions.glGetString(GL.GL_VERSION)

        # initialise a common to all OpenGL windows
        self.globalGL = GLGlobalData(parent=self, mainWindow=self.mainWindow)
        self.globalGL.initialiseShaders(self)

        # move outside GLGlobalData to check threading on windows
        self.globalGL.bindFonts()

        # initialise the arrays for the grid and axes
        self.gridList = []
        for li in range(3):
            self.gridList.append(GLVertexArray(numLists=1,
                                               renderMode=GLRENDERMODE_REBUILD,
                                               blendMode=False,
                                               drawMode=GL.GL_LINES,
                                               dimension=2,
                                               GLContext=self))

        self.diagonalGLList = GLVertexArray(numLists=1,
                                            renderMode=GLRENDERMODE_REBUILD,
                                            blendMode=False,
                                            drawMode=GL.GL_LINES,
                                            dimension=2,
                                            GLContext=self)

        self.diagonalSideBandsGLList = GLVertexArray(numLists=1,
                                                     renderMode=GLRENDERMODE_REBUILD,
                                                     blendMode=False,
                                                     drawMode=GL.GL_LINES,
                                                     dimension=2,
                                                     GLContext=self)

        self.boundingBoxes = GLVertexArray(numLists=1,
                                           renderMode=GLRENDERMODE_REBUILD,
                                           blendMode=False,
                                           drawMode=GL.GL_LINES,
                                           dimension=2,
                                           GLContext=self)

        # get the current buffering mode and set the required length to the number of buffers
        fmt = self.format()
        self._numBuffers = int(fmt.swapBehavior()) or 2
        self._glCursorQueue = ()
        for buf in range(self._numBuffers):
            self._glCursorQueue += (GLVertexArray(numLists=1,
                                                  renderMode=GLRENDERMODE_REBUILD,
                                                  blendMode=False,
                                                  drawMode=GL.GL_LINES,
                                                  dimension=2,
                                                  GLContext=self),)
        self._clearGLCursorQueue()

        self._glCursor = GLVertexArray(numLists=1,
                                       renderMode=GLRENDERMODE_REBUILD,
                                       blendMode=False,
                                       drawMode=GL.GL_LINES,
                                       dimension=2,
                                       GLContext=self)

        self._externalRegions = GLExternalRegion(project=self.project, GLContext=self, spectrumView=None,
                                                 integralListView=None)

        self._selectionBox = GLVertexArray(numLists=1,
                                           renderMode=GLRENDERMODE_REBUILD,
                                           blendMode=True,
                                           drawMode=GL.GL_QUADS,
                                           dimension=3,
                                           GLContext=self)
        self._selectionOutline = GLVertexArray(numLists=1,
                                               renderMode=GLRENDERMODE_REBUILD,
                                               blendMode=True,
                                               drawMode=GL.GL_LINES,
                                               dimension=3,
                                               GLContext=self)
        self._marksList = GLVertexArray(numLists=1,
                                        renderMode=GLRENDERMODE_REBUILD,
                                        blendMode=False,
                                        drawMode=GL.GL_LINES,
                                        dimension=2,
                                        GLContext=self)
        self._regionList = GLVertexArray(numLists=1,
                                         renderMode=GLRENDERMODE_REBUILD,
                                         blendMode=True,
                                         drawMode=GL.GL_QUADS,
                                         dimension=2,
                                         GLContext=self)

        self._testSpectrum = GLVertexArray(numLists=1,
                                           renderMode=GLRENDERMODE_REBUILD,
                                           blendMode=True,
                                           drawMode=GL.GL_TRIANGLES,
                                           dimension=4,
                                           GLContext=self)

        self._spectrumLabelling = GLSimpleStrings(parent=self, strip=self.strip, name='spectrumLabelling')

        # self._legend = GLSimpleLegend(parent=self, strip=self.strip, name='legend')
        # for ii, spectrum in enumerate(self.project.spectra):
        #     # add some test strings
        #     self._legend.addString(spectrum, (ii*15,ii*15),
        #                                       colour="#FE64C6", alpha=0.75)

        self.viewports = GLViewports()
        self._initialiseViewPorts()

        # set strings for the overlay text
        self.buildOverlayStrings()

        # This is the correct blend function to ignore stray surface blending functions
        #   think this was an old QT bug
        # GL.glBlendFuncSeparate(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA, GL.GL_ONE, GL.GL_ONE)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        self._setColourScheme()
        self.setBackgroundColour(self.background, silent=True)
        shader = self._shaderText
        shader.bind()
        shader.setBlendEnabled(False)
        shader.setAlpha(1.0)
        shader = self._shaderTextAlias
        shader.bind()
        shader.setBlendEnabled(True)
        shader.setAlpha(1.0)

        if self.strip:
            self.updateVisibleSpectrumViews()

            self.initialiseAxes(self.strip)
            # NOTE:ED - why is this called here?
            # self.initialiseTraces()

        # set the painting mode
        self._paintMode = PaintModes.PAINT_ALL
        self._paintLastFrame = True
        self._leavingWidget = False

        # check that the screen device pixel ratio is correct
        self.refreshDevicePixelRatio()

        # set the pyqtsignal responders
        self.GLSignals.glXAxisChanged.connect(self._glXAxisChanged)
        self.GLSignals.glYAxisChanged.connect(self._glYAxisChanged)
        self.GLSignals.glAllAxesChanged.connect(self._glAllAxesChanged)
        self.GLSignals.glMouseMoved.connect(self._glMouseMoved)
        self.GLSignals.glEvent.connect(self._glEvent)
        self.GLSignals.glAxisLockChanged.connect(self._glAxisLockChanged)
        self.GLSignals.glAxisUnitsChanged.connect(self._glAxisUnitsChanged)
        self.GLSignals.glKeyEvent.connect(self._glKeyEvent)

        self.glReady = True

        # make sure that the shaders are initialised
        self._resizeGL()

    def _clearGLCursorQueue(self):
        """Clear the cursor glLists
        """
        if not self._disableCursorUpdate:
            for glBuf in self._glCursorQueue:
                glBuf.clearArrays()
            self._glCursorHead = 0
            self._glCursorTail = (self._glCursorHead - 1) % self._numBuffers

    def _advanceGLCursor(self):
        """Advance the pointers for the cursor glLists
        """
        if not self._disableCursorUpdate:
            self._glCursorHead = (self._glCursorHead + 1) % self._numBuffers
            self._glCursorTail = (self._glCursorHead - 1) % self._numBuffers

    def _initialiseViewPorts(self):
        """Initialise all the viewports for the widget
        """
        self.viewports.clearViewports()

        # define the main viewports
        if self.AXIS_INSIDE:
            self.viewports.addViewport(GLDefs.MAINVIEW, self,
                                       (0, 'a'), (self.AXIS_MARGINBOTTOM, 'a'),
                                       (-self.AXIS_MARGINRIGHT, 'w'), (-self.AXIS_MARGINBOTTOM, 'h'))

            self.viewports.addViewport(GLDefs.MAINVIEWFULLWIDTH, self,
                                       (0, 'a'), (self.AXIS_MARGINBOTTOM, 'a'),
                                       (0, 'w'), (-self.AXIS_MARGINBOTTOM, 'h'))

            self.viewports.addViewport(GLDefs.MAINVIEWFULLHEIGHT, self,
                                       (0, 'a'), (0, 'a'),
                                       (-self.AXIS_MARGINRIGHT, 'w'), (0, 'h'))
        else:
            self.viewports.addViewport(GLDefs.MAINVIEW, self,
                                       (0, 'a'), (self.AXIS_MARGINBOTTOM + self.AXIS_LINE, 'a'),
                                       (-(self.AXIS_MARGINRIGHT + self.AXIS_LINE), 'w'),
                                       (-(self.AXIS_MARGINBOTTOM + self.AXIS_LINE), 'h'))

            self.viewports.addViewport(GLDefs.MAINVIEWFULLWIDTH, self,
                                       (0, 'a'), (self.AXIS_MARGINBOTTOM + self.AXIS_LINE, 'a'),
                                       (0, 'w'), (-(self.AXIS_MARGINBOTTOM + self.AXIS_LINE), 'h'))

            self.viewports.addViewport(GLDefs.MAINVIEWFULLHEIGHT, self,
                                       (0, 'a'), (0, 'a'),
                                       (-(self.AXIS_MARGINRIGHT + self.AXIS_LINE), 'w'), (0, 'h'))

        # define the viewports for the right axis bar
        if self.AXIS_INSIDE:
            self.viewports.addViewport(GLDefs.RIGHTAXIS, self,
                                       (-(self.AXIS_MARGINRIGHT + self.AXIS_LINE), 'w'),
                                       (self.AXIS_MARGINBOTTOM, 'a'),
                                       (self.AXIS_LINE, 'a'), (-self.AXIS_MARGINBOTTOM, 'h'))
            self.viewports.addViewport(GLDefs.RIGHTAXISBAR, self,
                                       (-self.AXIS_MARGINRIGHT, 'w'),
                                       (self.AXIS_MARGINBOTTOM, 'a'),
                                       (self.AXIS_MARGINRIGHT, 'a'), (-self.AXIS_MARGINBOTTOM, 'h'))

        else:
            self.viewports.addViewport(GLDefs.RIGHTAXIS, self,
                                       (-(self.AXIS_MARGINRIGHT + self.AXIS_LINE), 'w'),
                                       (self.AXIS_MARGINBOTTOM + self.AXIS_LINE, 'a'),
                                       (self.AXIS_LINE, 'a'), (-(self.AXIS_MARGINBOTTOM + self.AXIS_LINE), 'h'))

            self.viewports.addViewport(GLDefs.RIGHTAXISBAR, self,
                                       (-self.AXIS_MARGINRIGHT, 'w'),
                                       (self.AXIS_MARGINBOTTOM + self.AXIS_LINE, 'a'),
                                       (self.AXIS_MARGINRIGHT, 'a'), (-(self.AXIS_MARGINBOTTOM + self.AXIS_LINE), 'h'))

        self.viewports.addViewport(GLDefs.FULLRIGHTAXIS, self,
                                   (-(self.AXIS_MARGINRIGHT + self.AXIS_LINE), 'w'), (0, 'a'),
                                   (self.AXIS_LINE, 'a'), (0, 'h'))

        self.viewports.addViewport(GLDefs.FULLRIGHTAXISBAR, self,
                                   (-self.AXIS_MARGINRIGHT, 'w'), (0, 'a'),
                                   (self.AXIS_MARGINRIGHT, 'a'), (0, 'h'))

        # define the viewports for the bottom axis bar
        if self.AXIS_INSIDE:
            self.viewports.addViewport(GLDefs.BOTTOMAXIS, self, (0, 'a'),
                                       (self.AXIS_MARGINBOTTOM, 'a'),
                                       (-self.AXIS_MARGINRIGHT, 'w'), (self.AXIS_LINE, 'a'))

            self.viewports.addViewport(GLDefs.BOTTOMAXISBAR, self,
                                       (0, 'a'), (0, 'a'),
                                       (-self.AXIS_MARGINRIGHT, 'w'), (self.AXIS_MARGINBOTTOM, 'a'))
        else:
            self.viewports.addViewport(GLDefs.BOTTOMAXIS, self,
                                       (0, 'a'), (self.AXIS_MARGINBOTTOM, 'a'),
                                       (-(self.AXIS_MARGINRIGHT + self.AXIS_LINE), 'w'), (self.AXIS_LINE, 'a'))

            self.viewports.addViewport(GLDefs.BOTTOMAXISBAR, self,
                                       (0, 'a'), (0, 'a'),
                                       (-(self.AXIS_MARGINRIGHT + self.AXIS_LINE), 'w'), (self.AXIS_MARGINBOTTOM, 'a'))

        self.viewports.addViewport(GLDefs.FULLBOTTOMAXIS, self,
                                   (0, 'a'), (self.AXIS_MARGINBOTTOM, 'a'),
                                   (0, 'w'), (self.AXIS_LINE, 'a'))

        self.viewports.addViewport(GLDefs.FULLBOTTOMAXISBAR, self,
                                   (0, 'a'), (0, 'a'),
                                   (0, 'w'), (self.AXIS_MARGINBOTTOM, 'a'))

        # define the full viewport
        self.viewports.addViewport(GLDefs.FULLVIEW, self, (0, 'a'), (0, 'a'), (0, 'w'), (0, 'h'))

        # define the remaining corner
        self.viewports.addViewport(GLDefs.AXISCORNER, self,
                                   (-self.AXIS_MARGINRIGHT, 'w'), (0, 'a'),
                                   (self.AXIS_MARGINRIGHT, 'a'),
                                   (self.AXIS_MARGINBOTTOM, 'a'))

        # define an empty view (for printing mainly)
        self.viewports.addViewport(GLDefs.BLANKVIEW, self, (0, 'a'), (0, 'a'), (0, 'a'), (0, 'a'))

    def buildOverlayStrings(self):
        smallFont = self.getSmallFont()

        dy = STRINGOFFSET * self.deltaY
        self._lockedStringFalse = GLString(text=GLDefs.LOCKEDSTRING, font=smallFont, x=0, y=dy,
                                           colour=self.buttonForeground, GLContext=self)
        self._lockedStringTrue = GLString(text=GLDefs.LOCKEDSTRING, font=smallFont, x=0, y=dy,
                                          colour=self.highlightColour, GLContext=self)

        dx = self._lockedStringTrue.width * self.deltaX
        self._fixedStringFalse = GLString(text=GLDefs.FIXEDSTRING, font=smallFont, x=dx, y=dy,
                                          colour=self.buttonForeground, GLContext=self)
        self._fixedStringTrue = GLString(text=GLDefs.FIXEDSTRING, font=smallFont, x=dx, y=dy,
                                         colour=self.highlightColour, GLContext=self)
        cornerButtons = ((self._lockedStringTrue, self._toggleAxisLocked),
                         (self._fixedStringTrue, self._toggleAxisFixed))
        self._buttonCentres = ()
        buttonOffset = 0
        for button, callBack in cornerButtons:
            w = (button.width / 2)
            h = (button.height / 2)
            # define a slightly wider, lower box
            self._buttonCentres += ((w + 2 + buttonOffset, h - 2, w, h - 3, callBack),)
            buttonOffset += button.width
        self.stripIDString = GLString(text='', font=smallFont, x=0, y=0, GLContext=self, obj=None)

    def getSmallFont(self, transparent=False):
        """Get the current active font
        """
        scale = self.viewports.devicePixelRatio
        size = self.globalGL.glSmallFontSize

        # get the correct font depending on the scaling and set the scaled height/width
        _font = list(self.globalGL.fonts.values())[0].closestFont(size * scale)

        if not (0.9999 < scale < 1.0001):
            _font.charHeight = _font.height / scale
            _font.charWidth = _font.width / scale

        return _font

    def getAxisFont(self, transparent=False):
        """Get the font for the axes
        """
        scale = self.viewports.devicePixelRatio
        size = self.globalGL.glAxisFontSize

        # get the correct font depending on the scaling and set the scaled height/width
        _font = list(self.globalGL.fonts.values())[0].closestFont(size * scale)

        if not (0.9999 < scale < 1.0001):
            _font.charHeight = _font.height / scale
            _font.charWidth = _font.width / scale

        return _font

    def _setColourScheme(self, pal: QtGui.QPalette = None):
        """Update colours from colourScheme
        """
        cols = self.colours = getColours()
        self.hexBackground = cols[CCPNGLWIDGET_HEXBACKGROUND]
        self.background = cols[CCPNGLWIDGET_BACKGROUND]
        self.foreground = cols[CCPNGLWIDGET_FOREGROUND]
        self.buttonForeground = cols[CCPNGLWIDGET_BUTTON_FOREGROUND]
        self.mousePickColour = cols[CCPNGLWIDGET_PICKCOLOUR]
        self.gridColour = cols[CCPNGLWIDGET_GRID]
        self.highlightColour = cols[CCPNGLWIDGET_HIGHLIGHT]
        self._labellingColour = cols[CCPNGLWIDGET_LABELLING]
        self._phasingTraceColour = cols[CCPNGLWIDGET_PHASETRACE]

        self.zoomAreaColour = cols[CCPNGLWIDGET_ZOOMAREA]
        self.pickAreaColour = cols[CCPNGLWIDGET_PICKAREA]
        self.selectAreaColour = cols[CCPNGLWIDGET_SELECTAREA]
        self.badAreaColour = cols[CCPNGLWIDGET_BADAREA]

        self.zoomLineColour = cols[CCPNGLWIDGET_ZOOMLINE]
        self.mouseMoveLineColour = cols[CCPNGLWIDGET_MOUSEMOVELINE]

        self.zoomAreaColourHard = (*cols[CCPNGLWIDGET_ZOOMAREA][0:3], CCPNGLWIDGET_HARDSHADE)
        self.pickAreaColourHard = (*cols[CCPNGLWIDGET_PICKAREA][0:3], CCPNGLWIDGET_HARDSHADE)
        self.selectAreaColourHard = (*cols[CCPNGLWIDGET_SELECTAREA][0:3], CCPNGLWIDGET_HARDSHADE)
        self.badAreaColourHard = (*cols[CCPNGLWIDGET_BADAREA][0:3], CCPNGLWIDGET_HARDSHADE)

    def _preferencesUpdate(self):
        """update GL values after the preferences have changed
        """
        self._preferences = self.application.preferences.general

        self._setColourScheme()
        # set the new limits
        self._applyXLimit = self._preferences.zoomXLimitApply
        self._applyYLimit = self._preferences.zoomYLimitApply
        self._intensityLimit = self._preferences.intensityLimit

        # set the flag to update the background in the paint event
        self._updateBackgroundColour = True

        self.stripIDString.renderMode = GLRENDERMODE_REBUILD

        # rebuild all the strings if the fontSize has changed
        _size = self.application.preferences.appearance.spectrumDisplayFontSize
        if _size != self.globalGL.glSmallFontSize:
            self.globalGL.glSmallFontSize = _size

        _size = self.application.preferences.appearance.spectrumDisplayAxisFontSize
        if _size != self.globalGL.glAxisFontSize:
            self.globalGL.glAxisFontSize = _size

        self.refreshDevicePixelRatio()

        self.buildOverlayStrings()

        # # get the updated font
        # smallFont = self.getSmallFont()
        #
        # # change the colour of the selected 'Lock' string
        # self._lockedStringTrue = GLString(text=GLDefs.LOCKEDSTRING, font=smallFont, x=0, y=0,
        #                                   colour=self.highlightColour, GLContext=self)
        #
        # # change the colour of the selected 'Fixed' string
        # self._fixedStringTrue = GLString(text=GLDefs.FIXEDSTRING, font=smallFont, x=0, y=0,
        #                                  colour=self.highlightColour, GLContext=self)

    def setBackgroundColour(self, col, silent=False, makeCurrent=False):
        """
        set all background colours in the shaders
        :param col - vec4, 4 element list e.g.: [0.05, 0.05, 0.05, 1.0], very dark gray
        """
        if makeCurrent:
            self.makeCurrent()

        GL.glClearColor(*col)
        self.background = np.array(col, dtype=np.float32)
        bg = QtGui.QVector4D(*col)
        shader = self._shaderText
        shader.bind()
        shader.setBackground(bg)
        shader = self._shaderPixelAlias
        shader.bind()
        shader.setBackground(bg)
        shader = self._shaderTextAlias
        shader.bind()
        shader.setBackground(bg)

        if not silent:
            self.update()
        if makeCurrent:
            self.doneCurrent()

    def mapMouseToAxis(self, pnt):
        if isinstance(pnt, QPoint):
            mx = pnt.x()
            if self._drawBottomAxis:
                my = self.height() - pnt.y() - self.AXIS_MOUSEYOFFSET
            else:
                my = self.height() - pnt.y()
            result = self.mouseTransform * QtGui.QVector4D(mx, my, 0.0, 1.0)
            return (result.x(), result.y())

        else:
            return None

    def _toggleAxisLocked(self):
        """Toggle the axis locked button
        """
        self._aspectRatioMode = 0 if self._aspectRatioMode == 1 else 1

        # create a dict and event to update this strip first
        aDict = {GLNotifier.GLSOURCE         : None,
                 GLNotifier.GLSPECTRUMDISPLAY: self.spectrumDisplay,
                 GLNotifier.GLVALUES         : (self._aspectRatioMode,)
                 }
        self._glAxisLockChanged(aDict)
        self.GLSignals._emitAxisLockChanged(source=self, strip=self.strip, lockValues=(self._aspectRatioMode,))

    def _toggleAxisFixed(self):
        """Toggle the use fixed aspect button
        """
        self._aspectRatioMode = 0 if self._aspectRatioMode == 2 else 2
        self._emitAxisFixed()

    def _emitAxisFixed(self):
        # create a dict and event to update this strip first
        aDict = {GLNotifier.GLSOURCE         : None,
                 GLNotifier.GLSPECTRUMDISPLAY: self.spectrumDisplay,
                 GLNotifier.GLVALUES         : (self._aspectRatioMode,)
                 }
        self._glAxisLockChanged(aDict)
        self.GLSignals._emitAxisLockChanged(source=self, strip=self.strip, lockValues=(self._aspectRatioMode,))

    def _getAxisDict(self):
        # create a dict and event to update this strip first
        aDict = {GLNotifier.GLSOURCE         : None,
                 GLNotifier.GLSPECTRUMDISPLAY: self.spectrumDisplay,
                 GLNotifier.GLVALUES         : (self._aspectRatioMode,)
                 }
        return aDict

    def mousePressInCornerButtons(self, mx, my):
        """Check if the mouse has been pressed in the lock button
        """
        if self.AXISLOCKEDBUTTON and (
                self.AXISLOCKEDBUTTONALLSTRIPS or self.strip == self.strip.spectrumDisplay.strips[0]):
            for button in self._buttonCentres:
                minDiff = abs(mx - button[0])
                maxDiff = abs(my - button[1])

                if (minDiff < button[2]) and (maxDiff < button[3]):
                    button[4]()
                    return True

    def mousePressInLabel(self, mx, my, ty):
        """Check if the mouse has been pressed in the stripIDlabel
        """
        smallFont = self.getSmallFont()

        buttons = (((GLDefs.TITLEXOFFSET + 0.5 * len(self.stripIDLabel)) * smallFont.charWidth,
                    ty - ((GLDefs.TITLEYOFFSET - 0.5) * smallFont.charHeight),
                    0.5 * len(self.stripIDLabel) * smallFont.charWidth,
                    0.4 * smallFont.charHeight),)

        for button in buttons:
            minDiff = abs(mx - button[0])
            maxDiff = abs(my - button[1])

            if (minDiff < button[2]) and (maxDiff < button[3]):
                return True

    def _dragStrip(self, mouseDict):  #, event: QtGui.QMouseEvent):
        """
        Re-implementation of the mouse press event to enable a NmrResidue label to be dragged as a json object
        containing its id and a modifier key to encode the direction to drop the strip.
        """
        # create the dataDict
        dataDict = {DropBase.PIDS: [self.strip.pid]}

        # update the dataDict with all mouseEvents{"controlRightMouse": false, "text": "NR:@-.@27.", "leftMouse": true, "controlShiftMiddleMouse": false, "middleMouse": false, "controlMiddleMouse": false, "controlShiftLeftMouse": false, "controlShiftRightMouse": false, "shiftMiddleMouse": false, "_connectDir": "isRight", "controlLeftMouse": false, "rightMouse": false, "shiftLeftMouse": false, "shiftRightMouse": false}
        dataDict.update(mouseDict)

        makeDragEvent(self, dataDict, [self.stripIDLabel], self.stripIDLabel)

    def mousePressIn1DArea(self, regions):
        cursorCoordinate = self.getCurrentCursorCoordinate()

        if self.spectrumDisplay.is1D and self.spectrumDisplay._flipped:
            cx, cy, ornt = cursorCoordinate[1], cursorCoordinate[0], 'h'
        else:
            cx, cy, ornt = cursorCoordinate[0], cursorCoordinate[1], 'v'

        for region in regions:
            if region._objectView and not region._objectView.isDisplayed:
                continue

            if isinstance(region._object, Integral):
                thisRegion = region._object._1Dregions
                if thisRegion:
                    mid = np.median(thisRegion[1])
                    delta = (np.max(thisRegion[1]) - np.min(thisRegion[1])) / 2.0
                    inX = self._widthsChangedEnough((mid, 0.0),
                                                    (cx, 0.0),
                                                    tol=delta)

                    mx = np.max([thisRegion[0], np.max(thisRegion[2])])
                    mn = np.min([thisRegion[0], np.min(thisRegion[2])])
                    mid = (mx + mn) / 2.0
                    delta = (mx - mn) / 2.0
                    inY = self._widthsChangedEnough((0.0, mid),
                                                    (0.0, cy),
                                                    tol=delta)
                    if not inX and not inY:
                        # add horizontal/vertical drag area to check-list
                        self._dragRegions.add((region, ornt, 3))

        return self._dragRegions

    def mousePressInRegion(self, regions):
        cursorCoordinate = self.getCurrentCursorCoordinate()
        cx, cy, ornt = cursorCoordinate[0], cursorCoordinate[1], 'v'

        for region in regions:
            if region._objectView and not region._objectView.isDisplayed:
                continue

            if region.visible and region.movable:
                if region.orientation == 'h':
                    if not self._widthsChangedEnough((0.0, region.values[0]),
                                                     (0.0, cy),
                                                     tol=abs(3 * self.pixelY)):
                        self._dragRegions.add((region, 'h', 0))  # line 0 of h-region
                        # break

                    elif not self._widthsChangedEnough((0.0, region.values[1]),
                                                       (0.0, cy),
                                                       tol=abs(3 * self.pixelY)):
                        self._dragRegions.add((region, 'h', 1))  # line 1 of h-region
                        # break
                    else:
                        mid = (region.values[0] + region.values[1]) / 2.0
                        delta = abs(region.values[0] - region.values[1]) / 2.0
                        if not self._widthsChangedEnough((0.0, mid),
                                                         (0.0, cy),
                                                         tol=delta):
                            self._dragRegions.add((region, 'h', 3))  # both lines of h-region
                            # break

                elif region.orientation == 'v':
                    if not self._widthsChangedEnough((region.values[0], 0.0),
                                                     (cx, 0.0),
                                                     tol=abs(3 * self.pixelX)):
                        self._dragRegions.add((region, 'v', 0))  # line 0 of v-region
                        # break

                    elif not self._widthsChangedEnough((region.values[1], 0.0),
                                                       (cx, 0.0),
                                                       tol=abs(3 * self.pixelX)):
                        self._dragRegions.add((region, 'v', 1))  # line 1 of v-region
                        # break
                    else:
                        mid = (region.values[0] + region.values[1]) / 2.0
                        delta = abs(region.values[0] - region.values[1]) / 2.0
                        if not self._widthsChangedEnough((mid, 0.0),
                                                         (cx, 0.0),
                                                         tol=delta):
                            self._dragRegions.add((region, 'v', 3))  # both lines of v-region
                            # break

        return self._dragRegions

    def mousePressInfiniteLine(self, regions):
        cursorCoordinate = self.getCurrentCursorCoordinate()
        for region in regions:
            if region._objectView and not region._objectView.isDisplayed:
                continue

            if region.visible and region.movable and region.values == region.values:  # nan/inf check
                if region.orientation == 'h':
                    if not self._widthsChangedEnough((0.0, region.values),
                                                     (0.0, cursorCoordinate[1]),
                                                     tol=abs(3 * self.pixelY)):
                        self._dragRegions.add((region, 'h', 4))  # line 0 of h-region

                elif region.orientation == 'v':
                    if not self._widthsChangedEnough((region.values, 0.0),
                                                     (cursorCoordinate[0], 0.0),
                                                     tol=abs(3 * self.pixelX)):
                        self._dragRegions.add((region, 'v', 4))  # line 0 of v-region

        return self._dragRegions

    def mousePressInIntegralLists(self):
        """Check whether the mouse has been pressed in an integral
        """

        # check moved to 1D class
        # if not self._stackingMode and not(self.is1D and self.strip._isPhasingOn):

        # for reg in self._GLIntegralLists.values():
        for reg in self._GLIntegrals._GLSymbols.values():
            if not reg.integralListView.isDisplayed or \
                    not reg.spectrumView.isDisplayed:
                continue

            integralPressed = self.mousePressInRegion(reg._regions)
            # if integralPressed:
            #   break

    def _checkMousePressAllowed(self):
        """Check whether a mouse click is allowed
        """
        # get delta between now and last mouse click
        _lastTime = self._lastTimeClicked
        _thisTime = time.time_ns() // 1e6
        delta = _thisTime - _lastTime

        # if interval large enough then reset timer and return True
        if delta > self._clickInterval:
            self._lastTimeClicked = _thisTime
            return True

    def _handleLabelDrag(self, event):
        """handle a mouse drag event of a label
        """
        if self._mouseButton == QtCore.Qt.LeftButton and self._pids:
            if (event.pos() - self._dragStartPosition).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                mouseDict = getMouseEventDict(event)
                self._dragStrip(mouseDict)
                self._draggingLabel = False

    def mousePressEvent(self, ev):

        # disable mouse presses in the double-click interval
        if not self._checkMousePressAllowed():
            return
        # get the keyboard state
        keyModifiers = QApplication.keyboardModifiers()

        cursorCoordinate = self.getCurrentCursorCoordinate()
        self._mousePressed = True
        self.lastPos = ev.pos()

        mx = ev.pos().x()
        if self._drawBottomAxis:
            my = self.height() - ev.pos().y() - self.AXIS_MOUSEYOFFSET
            top = self.height() - self.AXIS_MOUSEYOFFSET
        else:
            my = self.height() - ev.pos().y()
            top = self.height()
        self._mouseStart = (mx, my)
        sc = self.mouseTransform * QtGui.QVector4D(mx, my, 0.0, 1.0)
        self._startCoordinate = [sc.x(), sc.y()]

        self._startMiddleDrag = False
        self._validRegionPick = False
        self._mouseInLabel = False

        self._endCoordinate = self._startCoordinate

        if int(ev.buttons() & (Qt.MiddleButton | Qt.RightButton)):
            # no modifiers pressed
            if not (keyModifiers & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)):
                # drag a peak
                xPosition = cursorCoordinate[0]  # self.mapSceneToView(event.pos()).x()
                yPosition = cursorCoordinate[1]  #
                if self._mouseInPeakLabel(xPosition, yPosition, firstOnly=True) or \
                        self._mouseInMultipletLabel(xPosition, yPosition, firstOnly=True):
                    # move from the mouse position
                    # NOTE:ED - need stacking offset!
                    # try:
                    #     if self.spectrumDisplay.is1D:  # and \
                    #             # (specViews := [spectrumView for spectrumView in self.strip.spectrumViews
                    #             #                for plv in spectrumView.peakListViews if spectrumView.isDisplayed and plv.isDisplayed
                    #             #                for pv in plv.peakViews if pv.peak in objs]) and \
                    #             # (_coord := self._spectrumSettings[specViews[0]].get(GLDefs.SPECTRUM_STACKEDMATRIXOFFSET)) is not None:
                    #
                    #         specViews = [spectrumView for spectrumView in self.strip.spectrumViews
                    #                        for plv in spectrumView.peakListViews if spectrumView.isDisplayed and plv.isDisplayed
                    #                        for pv in plv.peakViews if pv.peak in objs]
                    #         _coord = self._spectrumSettings[specViews[0]].get(GLDefs.SPECTRUM_STACKEDMATRIXOFFSET)
                    #
                    #         xOffset, yOffset = _coord
                    #         # self._startCoordinate = [cursorCoordinate[0] + xOffset, cursorCoordinate[1] + yOffset]
                    #         self._startCoordinate = cursorCoordinate[:2]
                    #
                    #     else:
                    #         self._startCoordinate = cursorCoordinate[:2]
                    #
                    # except Exception as es:
                    # DUH! always the screen co-ordinate
                    self._startCoordinate = cursorCoordinate[:2]

                    # set the flags for middle mouse dragging
                    self._startMiddleDrag = True
                    self._drawMouseMoveLine = True
                    self._drawDeltaOffset = True
                    self._mouseInLabel = True

                elif objs := self._mouseInPeak(xPosition, yPosition, firstOnly=True):
                    # move from the centre of the clicked peak
                    self.getPeakPositionFromMouse(objs[0], self._startCoordinate, cursorCoordinate)

                    # set the flags for middle mouse dragging
                    self._startMiddleDrag = True
                    self._drawMouseMoveLine = True
                    self._drawDeltaOffset = True

        if self.mousePressInLabel(mx, my, top):
            self._draggingLabel = False  # True to enable dragging of label

        else:
            # check if the corner buttons have been pressed
            self.mousePressInCornerButtons(mx, my)

            # check for dragging of infinite lines, region boundaries, integrals
            self.mousePressInfiniteLine(self._infiniteLines)

            while len(self._dragRegions) > 1:  # only keep the first region
                self._dragRegions.pop()
            # self._dragRegions.clear()

            if not self._dragRegions:
                if not self.mousePressInRegion(self._externalRegions._regions):
                    self.mousePressInIntegralLists()

        if int(ev.buttons() & (Qt.LeftButton | Qt.RightButton)):
            # find the bounds for the region that has currently been clicked
            # if (keyModifiers & (Qt.ShiftModifier | Qt.ControlModifier)):

            if self.is1D:
                bounds = ([],)
                self._minBounds = [None, ]
                self._maxBounds = [None, ]
            else:
                bounds = ([], [])
                self._minBounds = [None, None]
                self._maxBounds = [None, None]

            # get the list of visible spectrumViews, or the first in the list
            visibleSpectrumViews = [specView for specView in self._ordering
                                    if not specView.isDeleted and specView.isDisplayed]

            for specView in visibleSpectrumViews:
                specSettings = self._spectrumSettings[specView]

                if not self.is1D:
                    pIndex = specSettings.dimensionIndices
                    if None in pIndex:
                        continue

                for ii in range(len(bounds)):
                    _rb = list(specSettings.regionBounds[ii])
                    bounds[ii].extend(_rb[1:-1])  # skip the outer ppm values

            bounds = [sorted(set([round(b, 12) for b in bnd])) for bnd in bounds]

            mn = min(self.axisL, self.axisR)
            mx = max(self.axisL, self.axisR)
            bounds[0] = [mn] + [bnd for bnd in bounds[0] if mn < bnd < mx] + [mx]
            if len(bounds) > 1:
                mn = min(self.axisB, self.axisT)
                mx = max(self.axisB, self.axisT)
                bounds[1] = [mn] + [bnd for bnd in bounds[1] if mn < bnd < mx] + [mx]

            for jj in range(len(bounds)):
                for minB, maxB in zip(bounds[jj], bounds[jj][1:]):
                    if minB < self._startCoordinate[jj] < maxB:
                        self._minBounds[jj] = minB
                        self._maxBounds[jj] = maxB
                        break

            if None not in self._minBounds and None not in self._maxBounds:
                # not currently used, but available to set the region to red if required
                self._validRegionPick = True

        self.current.strip = self.strip
        self.update()

    def mouseDoubleClickEvent(self, ev):
        self._mouseDoubleClickEvent(ev)

    def mouseReleaseEvent(self, ev):

        # if no self.current then strip is not defined correctly
        if not getattr(self.current, 'mouseMovedDict', None):
            return

        if not self._mousePressed:
            return

        self._mousePressed = False
        self._draggingLabel = False

        # here or at the end of release?
        self._clearAndUpdate()

        mx = ev.pos().x()
        if self._drawBottomAxis:
            my = self.height() - ev.pos().y() - self.AXIS_MOUSEYOFFSET
        else:
            my = self.height() - ev.pos().y()
        self._mouseEnd = (mx, my)

        # add a 2-pixel tolerance to the click event - in case of a small wiggle on coordinates
        if not self._widthsChangedEnough(self._mouseStart, self._mouseEnd, tol=2):
            # perform click action
            self._mouseClickEvent(ev)

        else:
            # end of drag event - perform action
            self._mouseDragEvent(ev)

        self._startMiddleDrag = False

    def _movePeakFromGLKeys(self, key):

        if len(self.current.peaks) < 1:
            return

        # move by 5 pixels
        moveFactor = 5
        moveDict = {
            QtCore.Qt.Key_Left : (-self.pixelX * moveFactor, 0),
            QtCore.Qt.Key_Right: (self.pixelX * moveFactor, 0),
            QtCore.Qt.Key_Up   : (0, self.pixelY * moveFactor),
            QtCore.Qt.Key_Down : (0, -self.pixelY * moveFactor)
            }

        if key in moveDict:

            with undoBlockWithoutSideBar():
                for peak in self.current.peaks:
                    self._movePeak(peak, moveDict.get(key))

    def _referenceSpectrumFromGLKeys(self, key):

        if len(self.current.spectra) < 1:
            return
        # move by 5 pixels
        moveFactor = 5
        moveDict = {
            QtCore.Qt.Key_Left : (-self.pixelX * moveFactor, 0),
            QtCore.Qt.Key_Right: (self.pixelX * moveFactor, 0),
            QtCore.Qt.Key_Up   : (0, self.pixelY * moveFactor),
            QtCore.Qt.Key_Down : (0, -self.pixelY * moveFactor)
            }

        if key in moveDict:
            with undoBlockWithoutSideBar():
                for spectrum in self.current.spectra:
                    if spectrum.dimensionCount == 1:
                        if key in [QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]:
                            shift = moveDict.get(key)[0]
                            spectrum.referenceValues = [spectrum.referenceValues[0] + shift]
                            spectrum.positions = np.array(spectrum.positions) + shift
                        if key in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down]:
                            offset = moveDict.get(key)[1]
                            # need to check the peak position/height
                            spectrum.intensities = spectrum.intensities + offset
                    else:
                        getLogger().warning('This option is not yet available for nD spectra')

    def _singleKeyAction(self, key, isShift, isOption=False):
        """
        :return: Actions for single key press. If current peaks, moves the peaks when using
        directional arrow otherwise pans the spectrum.
        """
        if isOption:
            self._referenceSpectrumFromGLKeys(key)
            return

        if not isShift:
            self._panGLSpectrum(key)

        if isShift:
            self._movePeakFromGLKeys(key)

    def _KeyModifiersAction(self, key):
        keyModifiers = QApplication.keyboardModifiers()
        if keyModifiers & (Qt.MetaModifier | Qt.ControlModifier) and key == Qt.Key_A:
            self.mainWindow.selectAllPeaks(self.strip)
        # elif keyModifiers & (Qt.MetaModifier | Qt.AltModifier) and key == Qt.Key_Left:
        #     print('@@@ Left')

    def glKeyPressEvent(self, aDict):
        """Process the key events from GLsignals
        """
        if (self.strip and not self.strip.isDeleted):

            # this may not be the current strip
            if self.strip == self.current.strip:
                self._singleKeyAction(aDict[GLNotifier.GLKEY], aDict[GLNotifier.GLMODIFIER])
                self.update()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Process key events or pass to current strip of required
        """
        if (self.strip and not self.strip.isDeleted):
            _key = event.key()
            keyModifiers = QApplication.keyboardModifiers()

            isShift = True if (keyModifiers & Qt.ShiftModifier) else False
            isOption = True if (keyModifiers & Qt.AltModifier) else False

            if self.strip == self.current.strip:
                self._singleKeyAction(_key, isShift=isShift, isOption=isOption)
                self._KeyModifiersAction(_key)

            elif not self._preferences.currentStripFollowsMouse:
                self.GLSignals._emitKeyEvent(strip=self.strip, key=event.key(),
                                             modifier=True if (keyModifiers & Qt.ShiftModifier) else False)

    def _clearAndUpdate(self):
        self._drawSelectionBox = False
        self._drawDeltaOffset = False
        self._drawMouseMoveLine = False
        self._dragRegions = set()
        self.update()

    def enterEvent(self, ev: QtCore.QEvent):
        self.GLSignals._mouseInGLWidget = True
        super().enterEvent(ev)
        if not getBlockingDialogs('GL enter-event'):
            if self.strip and not self.strip.isDeleted:
                if self._preferences.currentStripFollowsMouse and self.current.strip != self.strip:
                    self.current.strip = self.strip
                    self.application._focusStrip = self.strip
                    self.setFocus()
                elif self._preferences.focusFollowsMouse and not self.hasFocus():
                    if getattr(self.application, '_focusStrip', None) != self.strip:
                        self.application._focusStrip = self.strip
                        self.setFocus()
        self._clearAndUpdate()

    def focusInEvent(self, ev: QtGui.QFocusEvent):
        super().focusInEvent(ev)
        self._clearAndUpdate()

    def focusOutEvent(self, ev: QtGui.QFocusEvent):
        super().focusOutEvent(ev)
        self._clearAndUpdate()

    def leaveEvent(self, ev: QtCore.QEvent):
        # set a flag for leaving this widget
        self._leavingWidget = True
        self._cursorFrameCounter = GLDefs.CursorFrameCounterModes.CURSOR_DRAWLAST
        self.GLSignals._mouseInGLWidget = False

        super().leaveEvent(ev)
        self._clearAndUpdate()

    def getMousePosition(self):
        """Get the coordinates of the mouse in the window (in ppm) based on the current axes
        """
        point = self.mapFromGlobal(QtGui.QCursor.pos())

        # calculate mouse coordinate within the mainView
        mx = point.x()
        if self._drawBottomAxis:
            my = self.height() - point.y() - self.AXIS_MOUSEYOFFSET
            _top = self.height() - self.AXIS_MOUSEYOFFSET
        else:
            my = self.height() - point.y()
            _top = self.height()

        mt = self.mouseTransform * QtGui.QVector4D(mx, my, 0.0, 1.0)
        return (mt.x(), mt.y(), mt.z(), mt.w())

    def mouseMoveEvent(self, event):

        self.cursorSource = CURSOR_SOURCE_SELF

        if self.strip.isDeleted:
            return
        if not self._ordering:  # strip.spectrumViews:
            return
        if self._draggingLabel:
            self._handleLabelDrag(event)
            return

        if abs(self.axisL - self.axisR) < 1.0e-6 or abs(self.axisT - self.axisB) < 1.0e-6:
            return

        # reset on the first mouseMove - frees the locked/default axis
        setattr(self.strip.spectrumDisplay, '_useFirstDefault', False)

        keyModifiers = QApplication.keyboardModifiers()

        cursorCoordinate, dx, dy, mouseMovedDict = self._updateMouseEvent()

        if int(event.buttons() & (Qt.LeftButton | Qt.RightButton)):
            # do the complicated key-presses first
            # other keys are: Key_Alt, Key_Meta, and _isALT, _isMETA

            # NOTE:ED I think that Linux is doing a strange button switch when you press shift/ctrl

            if (keyModifiers & Qt.ShiftModifier) and (keyModifiers & Qt.ControlModifier):

                if self.is1D:
                    # self._endCoordinate = cursorCoordinate  #[event.pos().x(), self.height() - event.pos().y()]
                    # self._selectionMode = 3
                    # check for a valid region pick
                    if self._validRegionPick:
                        self._endCoordinate = [np.clip(cursorCoordinate[0], self._minBounds[0], self._maxBounds[0]),
                                               cursorCoordinate[1]]
                        self._selectionMode = 3
                    else:
                        # in case bad picking needs to be shown to the user, shows a red box
                        # awkward for overlaid spectra with different aliasing regions specified
                        self._endCoordinate = [np.clip(cursorCoordinate[0], self._minBounds[0], self._maxBounds[0]),
                                               cursorCoordinate[1]]
                        self._selectionMode = 4

                    self._drawSelectionBox = True
                    self._drawDeltaOffset = True
                else:
                    # check for a valid region pick
                    if self._validRegionPick:
                        self._endCoordinate = [np.clip(pos, mn, mx)
                                               for pos, mn, mx in zip(cursorCoordinate,
                                                                      self._minBounds, self._maxBounds)]
                        self._selectionMode = 3
                    else:
                        # in case bad picking needs to be shown to the user, shows a red box
                        # awkward for overlaid spectra with different aliasing regions specified
                        self._endCoordinate = [np.clip(pos, mn, mx)
                                               for pos, mn, mx in zip(cursorCoordinate, self._minBounds,
                                                                      self._maxBounds)]  #cursorCoordinate  #[event.pos().x(), self.height() - event.pos().y()]
                        self._selectionMode = 4

                    self._drawSelectionBox = True
                    self._drawDeltaOffset = True

            elif (keyModifiers & Qt.ShiftModifier) and int(event.buttons() & Qt.LeftButton):

                # fix the box to the screen ratio
                if self.aspectRatioMode:
                    self._endCoordinate = cursorCoordinate
                    dx = self._startCoordinate[0] - self._endCoordinate[0]  # deltaX
                    dy = self._startCoordinate[1] - self._endCoordinate[1]  # deltaY
                    _delta = self._getSelectionBoxRatio((dx, dy))
                    dx = _delta[0]  #* self.sign(dx)
                    dy = _delta[1]  #* self.sign(dy)
                    # dx = abs(dy * self.pixelX / self.pixelY) * self.sign(dx)
                    self._endCoordinate[0] = self._startCoordinate[0] - dx
                    self._endCoordinate[1] = self._startCoordinate[1] - dy
                else:
                    self._endCoordinate = cursorCoordinate  #[event.pos().x(), self.height() - event.pos().y()]
                self._selectionMode = 1
                self._drawSelectionBox = True
                self._drawDeltaOffset = True

            elif (keyModifiers & Qt.ControlModifier) and int(event.buttons() & Qt.LeftButton):

                self._endCoordinate = cursorCoordinate  #[event.pos().x(), self.height() - event.pos().y()]
                self._selectionMode = 2
                self._drawSelectionBox = True
                self._drawDeltaOffset = True

            elif int(event.buttons() & Qt.LeftButton):

                if self._dragRegions:
                    for reg in self._dragRegions:
                        values = reg[0].values
                        if reg[1] == 'v':

                            if reg[2] == 3:

                                # moving the mouse in a region
                                values[0] += dx * self.pixelX
                                values[1] += dx * self.pixelX
                            elif reg[2] == 4:

                                # moving an infinite line
                                values += dx * self.pixelX
                            else:

                                # moving one edge of a region
                                values[reg[2]] += dx * self.pixelX

                        elif reg[1] == 'h':

                            if reg[2] == 3:

                                # moving the mouse in a region
                                values[0] -= dy * self.pixelY
                                values[1] -= dy * self.pixelY
                            elif reg[2] == 4:

                                # moving an infinite line
                                values -= dy * self.pixelY
                            else:

                                # moving one edge of a region
                                values[reg[2]] -= dy * self.pixelY

                        # keep first and last drag values
                        if reg[0] in self._dragValues:
                            firstVal, _newVal = self._dragValues[reg[0]]
                        else:
                            firstVal = reg[0].values

                        reg[0].values = values
                        # write into drag values to update when the mouse is released
                        self._dragValues[reg[0]] = (firstVal, values)

                        # # NOTE:ED check moving of baseline
                        # if hasattr(reg[0], '_integralArea'):
                        #     # reg[0].renderMode = GLRENDERMODE_REBUILD
                        #     reg[0]._rebuildIntegral()
                else:

                    # Main mouse drag event - handle moving the axes with the mouse
                    self.axisL -= dx * self.pixelX
                    self.axisR -= dx * self.pixelX
                    self.axisT += dy * self.pixelY
                    self.axisB += dy * self.pixelY

                    tilePos = self.strip.tilePosition if self.strip else self.tilePosition
                    self.GLSignals._emitAllAxesChanged(source=self, strip=self.strip,
                                                       axisB=self.axisB, axisT=self.axisT,
                                                       axisL=self.axisL, axisR=self.axisR,
                                                       row=tilePos[0], column=tilePos[1])
                    self._selectionMode = 0
                    self._rescaleAllAxes(mouseMoveOnly=True)
                    self._storeZoomHistory()

        elif event.buttons() & Qt.MiddleButton:
            if self._startMiddleDrag and not (
                    keyModifiers & (Qt.ShiftModifier | Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)):
                # drag a peak
                self._endCoordinate = cursorCoordinate
                self._drawMouseMoveLine = True
                self._drawDeltaOffset = True

        if not event.buttons():
            self.GLSignals._emitMouseMoved(source=self, coords=cursorCoordinate, mouseMovedDict=mouseMovedDict,
                                           mainWindow=self.mainWindow)

        # spawn rebuild/paint of traces
        if self._updateHTrace or self._updateVTrace:
            self.updateTraces()

        self.update()

    def _updateMouseEvent(self):
        """Update the current mouse dict
        """
        currentPos = self.mapFromGlobal(QtGui.QCursor.pos())
        dx = currentPos.x() - self.lastPos.x()
        dy = currentPos.y() - self.lastPos.y()
        self.lastPos = currentPos
        cursorCoordinate = self.getCurrentCursorCoordinate()
        mouseMovedDict = self._updateMouseDict(cursorCoordinate)

        return cursorCoordinate, dx, dy, mouseMovedDict

    # def _updateMouseDict(self, cursorCoordinate):
    #     try:
    #         mouseMovedDict = self.current.mouseMovedDict
    #     except:
    #         # initialise a new mouse moved dict
    #         mouseMovedDict = {MOUSEDICTSTRIP          : self.strip,
    #                           AXIS_MATCHATOMTYPE      : {},
    #                           AXIS_FULLATOMNAME       : {},
    #                           }
    #
    #     xPos = yPos = 0
    #     atTypes = mouseMovedDict[AXIS_MATCHATOMTYPE] = {}
    #     atCodes = mouseMovedDict[AXIS_FULLATOMNAME] = {}
    #
    #     # transfer the mouse position from the coords to the mouseMovedDict for the other displays
    #     for n, (atomType, axis) in enumerate(zip(self.spectrumDisplay.isotopeCodes, self._orderedAxes)):
    #         ats = atTypes.setdefault(atomType, [])
    #         atcs = atCodes.setdefault(axis.code, [])
    #         if n == 0:
    #             xPos = pos = cursorCoordinate[0]
    #         elif n == 1:
    #             yPos = pos = cursorCoordinate[1]
    #         else:
    #             # for other Nd dimensions
    #             pos = axis.position
    #
    #         ats.append(pos)
    #         atcs.append(pos)
    #
    #     if self._matchingIsotopeCodes:
    #         # add a copy to show the reflected ppm values
    #         for n, (atomType, axis) in enumerate(zip(self.spectrumDisplay.isotopeCodes, self._orderedAxes)):
    #             ats = atTypes.setdefault(atomType, [])
    #             atcs = atCodes.setdefault(axis.code, [])
    #             if n == 0:
    #                 xPos = pos = cursorCoordinate[1]
    #             elif n == 1:
    #                 yPos = pos = cursorCoordinate[0]
    #             else:
    #                 # can ignore the rest
    #                 break
    #
    #             ats.append(pos)
    #             atcs.append(pos)
    #
    #     self.current.cursorPosition = (xPos, yPos)
    #     self.current.mouseMovedDict = mouseMovedDict
    #
    #     return mouseMovedDict

    @staticmethod
    def sign(x):
        return 1.0 if x >= 0 else -1.0

    def _rescaleOverlayText(self):
        if self.stripIDString:
            smallFont = self.getSmallFont()
            offsets = [GLDefs.TITLEXOFFSET * smallFont.charWidth * self.deltaX,
                       1.0 - (GLDefs.TITLEYOFFSET * smallFont.charHeight * self.deltaY),
                       0.0, 0.0]

            self.stripIDString.attribs[:] = offsets * self.stripIDString.numVertices
            self.stripIDString.pushTextArrayVBOAttribs()

        if self._lockedStringTrue:
            dy = STRINGOFFSET * self.deltaY
            offsets = [0.0, dy, 0.0, 0.0]
            self._lockedStringTrue.attribs[:] = offsets * self._lockedStringTrue.numVertices
            self._lockedStringTrue.pushTextArrayVBOAttribs()

            if self._lockedStringTrue:
                self._lockedStringFalse.attribs[:] = offsets * self._lockedStringFalse.numVertices
                self._lockedStringFalse.pushTextArrayVBOAttribs()
            dx = self._lockedStringTrue.width * self.deltaX

            offsets = [dx, dy, 0.0, 0.0]
            if self._fixedStringFalse:
                self._fixedStringFalse.attribs[:] = offsets * self._fixedStringFalse.numVertices
                self._fixedStringFalse.pushTextArrayVBOAttribs()

            if self._fixedStringTrue:
                self._fixedStringTrue.attribs[:] = offsets * self._fixedStringTrue.numVertices
                self._fixedStringTrue.pushTextArrayVBOAttribs()

    def _updateHighlightedIntegrals(self, spectrumView, integralListView):
        drawList = self._GLIntegralLists[integralListView]
        drawList._rebuild()

    def _processSpectrumNotifier(self, data):
        trigger = data[Notifier.TRIGGER]

        if trigger in [Notifier.RENAME]:
            obj = data[Notifier.OBJECT]
            self._spectrumLabelling.renameString(obj)

        self.update()

    def _processPeakNotifier(self, data):
        self._updateVisibleSpectrumViews()
        self._GLPeaks._processNotifier(data)

        self.update()

    def _processPeakListNotifier(self, data):
        self._updateVisibleSpectrumViews()
        self._GLPeaks._processNotifier(data)

        self.update()

    def _processNmrAtomNotifier(self, data):
        self._updateVisibleSpectrumViews()
        self._GLPeaks._processNotifier(data)
        self._GLMultiplets._processNotifier(data)
        self._nmrAtomsNotifier(data)

        self.update()

    def _processIntegralNotifier(self, data):
        self._updateVisibleSpectrumViews()
        self._GLIntegrals._processNotifier(data)

        self.update()

    def _processMultipletNotifier(self, data):
        self._updateVisibleSpectrumViews()
        self._GLMultiplets._processNotifier(data)

        self.update()

    def _processMultipletListNotifier(self, data):
        self._updateVisibleSpectrumViews()
        self._GLMultiplets._processNotifier(data)

        self.update()

    def _nmrAtomsNotifier(self, data):
        """respond to a rename-notifier on an nmrAtom, and update marks
        """
        trigger = data[Notifier.TRIGGER]

        if trigger in [Notifier.RENAME]:
            nmrAtom = data[Notifier.OBJECT]
            oldPid = Pid.Pid(data[Notifier.OLDPID])
            oldId = oldPid.id

            # search for the old name in the strings and remake
            for mark in self._marksAxisCodes:
                if mark.text == oldId:
                    mark.text = nmrAtom.id

                    # rebuild string
                    mark.buildString()
                    self._rescaleMarksAxisCode(mark)

            self.update()

    @staticmethod
    def _round_sig(x, sig=6, small_value=1.0e-9):
        return 0 if x == 0 else round(x, sig - int(math.floor(math.log10(max(abs(x), abs(small_value))))) - 1)

    @staticmethod
    def between(val, l, r):
        return (l - val) * (r - val) <= 0

    def _setViewPortFontScale(self):
        # set the scale for drawing the overlay text correctly
        self._axisScale = QtGui.QVector4D(self.deltaX, self.deltaY, 1.0, 1.0)
        shader = self._shaderText
        shader.setAxisScale(self._axisScale)
        shader.setProjection(0.0, 1.0, 0, 1.0, -1.0, 1.0)

    def updateVisibleSpectrumViews(self):
        self._visibleSpectrumViewsChange = True
        self.update()

    # @contextmanager
    def glBlocking(self):
        try:
            # stop notifiers and logging interfering with paint event
            self.project.blankNotification()
            self.application._increaseNotificationBlocking()

            yield

        finally:
            # re-enable notifiers
            self.application._decreaseNotificationBlocking()
            self.project.unblankNotification()

    def _buildGL(self):
        """Separate the building of the display from the paint event; not sure that this is required
        """
        # if abs(self.axisL - self.axisR) < 1e-9 or abs(self.axisT - self.axisB) < 1e-9:
        #     return

        self.buildCursors()
        if self.underMouse():
            self.buildMouseCoords()

        # build spectrumSettings, spectrumView visibility
        self.buildSpectra()

        # only call if the axes have changed, and after spectra
        if self._updateAxes:
            self.buildGrid()
            self.buildDiagonals()
            self._updateAxes = False

        # self.buildBoundingBoxes()

        self._GLPeaks._spectrumSettings = self._spectrumSettings
        self._GLMultiplets._spectrumSettings = self._spectrumSettings
        self._GLIntegrals._spectrumSettings = self._spectrumSettings

        self._GLPeaks.buildSymbols()
        self._GLPeaks.buildArrows()
        self._GLMultiplets.buildSymbols()
        self._GLMultiplets.buildArrows()
        if not self._stackingMode:
            self._GLIntegrals.buildSymbols()
            self.buildRegions()

        if self.buildMarks:
            self._marksList.renderMode = GLRENDERMODE_REBUILD
            self.buildMarks = False

        self.buildMarksRulers()

        self._GLPeaks.buildLabels()
        self._GLMultiplets.buildLabels()
        if not self._stackingMode:
            self._GLIntegrals.buildLabels()

        phasingFrame = self.spectrumDisplay.phasingFrame
        if phasingFrame.isVisible():
            self.buildStaticTraces()

    from ccpn.util.decorators import profile

    @profile()
    def _buildGLWithProfile(self):
        """A new test method for profiling the _buildGL
        """
        self._buildGL()

    def paintGL(self):
        """Handle the GL painting
        """
        if self._blankDisplay:
            return

        if self.strip.isDeleted:
            return

        # if self.visibleRegion().isEmpty():
        #     return
        # print(f'--> paintGL   {id(self)}   {self.strip}   {not self.visibleRegion()}')

        # NOTE:ED - testing, remove later
        # self._paintMode = PaintModes.PAINT_ALL

        if self._paintMode == PaintModes.PAINT_NONE:

            # do nothing
            pass

        elif self._paintMode == PaintModes.PAINT_ALL or self._leavingWidget:

            # NOTE:ED - paint all content to the GL widget - need to work on this
            self._clearGLCursorQueue()

            # check whether the visible spectra list needs updating
            if self._visibleSpectrumViewsChange:
                self._visibleSpectrumViewsChange = False
                self._updateVisibleSpectrumViews()

            # if there are no spectra then skip the paintGL event
            if not self._ordering:
                return

            for _ in self.glBlocking():
                # simple profile of building all

                # NOTE:ED - this should be updated to explicit build calls
                #   and the _buildGL only moves it to the graphics card

                if hasattr(self.project, '_buildWithProfile') and self.project._buildWithProfile is True:
                    self.project._buildWithProfile = False

                    # create simple speed-caches for the current peaks/multiplets/integrals
                    for objList in [self._GLPeaks, self._GLMultiplets, self._GLIntegrals]:
                        objList._caching = True
                        objList._objCache = None

                    self._buildGLWithProfile()

                    for objList in [self._GLPeaks, self._GLMultiplets, self._GLIntegrals]:
                        objList._caching = False
                        objList._objCache = None

                else:
                    # create simple speed-caches for the current peaks/multiplets/integrals
                    for objList in [self._GLPeaks, self._GLMultiplets, self._GLIntegrals]:
                        objList._caching = True
                        objList._objCache = None

                    self._buildGL()

                    for objList in [self._GLPeaks, self._GLMultiplets, self._GLIntegrals]:
                        objList._caching = False
                        objList._objCache = None

                self._paintGL()

            # make all following paint events into mouse only
            # so only paints a single frame from an update event
            self._paintMode = PaintModes.PAINT_MOUSEONLY
            self._paintLastFrame = True
            self._leavingWidget = False

        elif self._paintMode == PaintModes.PAINT_MOUSEONLY:
            self._paintLastFrame = False
            self._leavingWidget = False

            # only need to paint the mouse cursor
            self._paintGLMouseOnly()

    # @contextmanager
    @staticmethod
    def _disableGLAliasing():
        """Disable aliasing for the contained routines
        """
        try:
            GL.glDisable(GL.GL_MULTISAMPLE)
            yield
        finally:
            GL.glEnable(GL.GL_MULTISAMPLE)

    # @contextmanager
    @staticmethod
    def _enableGLAliasing():
        """Enable aliasing for the contained routines
        """
        try:
            GL.glEnable(GL.GL_MULTISAMPLE)
            yield
        finally:
            GL.glDisable(GL.GL_MULTISAMPLE)

    # @contextmanager
    @staticmethod
    def _enableLogicOp(logicOp=GL.GL_COPY):
        """Enable logic operation for the contained routines
        """
        # valid values are: GL_CLEAR, GL_SET, GL_COPY, GL_COPY_INVERTED, GL_NOOP,
        #                   GL_INVERT, GL_AND, GL_NAND, GL_OR, GL_NOR,
        #                   GL_XOR, GL_EQUIV, GL_AND_REVERSE, GL_AND_INVERTED,
        #                   GL_OR_REVERSE, and GL_OR_INVERTED.The
        # initial value is GL_COPY

        try:
            GL.glEnable(GL.GL_COLOR_LOGIC_OP)
            GL.glLogicOp(logicOp)

            # NOTE:ED needed to cure that strange pyqt5 window-mask
            GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_FALSE)

            yield  # pass control to the calling function

        finally:
            GL.glColorMask(GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE, GL.GL_TRUE)
            GL.glLogicOp(GL.GL_COPY)
            GL.glDisable(GL.GL_COLOR_LOGIC_OP)

    def _paintGLMouseOnly(self):
        """paintGL event - paint only the mouse in Xor mode

        *** This assumes that the paint-mode is double-buffered and the buffer does not clear between swap-buffers
        """
        # reset the paint mode - need to check the logic here
        # self._paintMode = PaintModes.PAINT_ALL

        shader = self._shaderPixel.bind()
        shader.setMVMatrixToIdentity()

        # draw the spectra, need to reset the viewport
        self.viewports.setViewport(self._currentView)

        for _ in self._disableGLAliasing():
            shader.setProjection(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)
            self.buildCursors()

            for _ in self._enableLogicOp(GL.GL_INVERT):
                # enable invert mode so that only the cursor needs to be refreshed in the other viewports
                self.drawLastCursors()
                self.drawCursors()

    def _paintGL(self):

        if self._updateBackgroundColour:
            self._updateBackgroundColour = False
            self.setBackgroundColour(self.background, silent=True)

        # MUST be done in paint if a painter is used later
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glEnable(GL.GL_MULTISAMPLE)

        shader = self._shaderPixel.bind()

        # start with the grid mapped to (0..1, 0..1) to remove zoom errors here
        shader.setProjection(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)
        shader.setMVMatrixToIdentity()

        for _ in self._disableGLAliasing():
            # draw the grid components
            self.drawGrid()

        # set the scale to the axis limits, needs addressing correctly, possibly same as grid
        shader.setProjection(self.axisL, self.axisR, self.axisB, self.axisT, -1.0, 1.0)

        # draw the spectra, need to reset the viewport
        _w, _h = self.viewports.setViewport(self._currentView)

        self.drawSpectra()
        self.drawBoundingBoxes()

        if self._peakSymbolsEnabled or self._peakArrowsEnabled or self._multipletSymbolsEnabled or self._multipletArrowsEnabled:
            # draw all the aliased symbols
            self.drawAliasedSymbols(self._peakSymbolsEnabled, self._peakArrowsEnabled,
                                    self._multipletSymbolsEnabled, self._multipletArrowsEnabled)

        self._shaderPixel.bind()

        if not self._stackingMode:
            if not (self.is1D and self.strip._isPhasingOn):  # other mouse buttons checks needed here
                self._GLIntegrals.drawSymbols(self._spectrumSettings, shader=self._shaderPixel)
                for _ in self._disableGLAliasing():
                    self._GLIntegrals.drawSymbolRegions(self._spectrumSettings)
                    self.drawRegions()

            for _ in self._disableGLAliasing():
                self.drawMarksRulers()

        # draw the text to the screen
        self.enableTexture()
        self.enableTextClientState()

        if self._peakLabelsEnabled or self._multipletLabelsEnabled:
            self.drawAliasedLabels()

        # change to the text shader
        shader = self._shaderText.bind()

        shader.setProjection(self.axisL, self.axisR, self.axisB, self.axisT, -1.0, 1.0)

        self._axisScale = QtGui.QVector4D(self.pixelX, self.pixelY, 1.0, 1.0)
        shader.setAxisScale(self._axisScale)
        shader.setStackOffset(QtGui.QVector2D(0.0, 0.0))

        if not self._stackingMode:
            if not (self.is1D and self.strip._isPhasingOn):
                self.drawIntegralLabels()

            self.drawMarksAxisCodes()

        else:
            # make the overlay/axis solid
            shader.setBlendEnabled(False)
            self._spectrumLabelling.drawStrings()

            # not fully implemented yet
            # self._legend.drawStrings()

            shader.setBlendEnabled(True)

        self.disableTextClientState()

        shader = self._shaderPixel.bind()

        self.drawTraces(shader)
        shader.setMVMatrixToIdentity()

        for _ in self._disableGLAliasing():
            self.drawInfiniteLines()

            shader.setProjection(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)

            self.drawSelectionBox()
            self.drawMouseMoveLine()

            if self._successiveClicks:
                self.drawDottedCursor()

            for _ in self._enableLogicOp(GL.GL_INVERT):
                # enable invert mode so that only the cursor needs to be refreshed in the other viewports
                self.drawCursors()

        shader = self._shaderText.bind()
        self.enableTextClientState()
        self._setViewPortFontScale()

        self.drawMouseCoords()

        # make the overlay/axis solid
        shader.setBlendEnabled(False)
        self.drawOverlayText()
        self.drawAxisLabels(shader)
        shader.setBlendEnabled(True)

        self.disableTextClientState()
        self.disableTexture()

        # emit signal to allow user-painting to the strip - experimental
        self.painted.emit(self.strip)

    def enableTexture(self):
        GL.glEnable(GL.GL_BLEND)
        # GL.glEnable(GL.GL_TEXTURE_2D)
        # GL.glBindTexture(GL.GL_TEXTURE_2D, self.globalGL.glSmallFont.textureId)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.getSmallFont()._parent.textureId)
        # GL.glActiveTexture(GL.GL_TEXTURE1)
        # GL.glBindTexture(GL.GL_TEXTURE_2D, self.getSmallFont(transparent=True).textureId)

    @staticmethod
    def disableTexture():
        GL.glDisable(GL.GL_BLEND)

    def buildAllContours(self):
        for spectrumView in self._ordering:  # strip.spectrumViews:
            if not spectrumView.isDeleted:
                spectrumView.buildContours = True

    def buildSpectra(self):
        if self.strip.isDeleted:
            return

        # self._spectrumSettings = {}
        rebuildFlag = False
        for spectrumView in self._ordering:  # strip.spectrumViews:
            if spectrumView.isDeleted:
                continue

            if spectrumView.buildContours or spectrumView.buildContoursOnly:

                # flag the peaks for rebuilding
                if not spectrumView.buildContoursOnly:
                    for peakListView in spectrumView.peakListViews:
                        peakListView.buildSymbols = True
                        peakListView.buildLabels = True
                        peakListView.buildArrows = True
                    for integralListView in spectrumView.integralListViews:
                        integralListView.buildSymbols = True
                        integralListView.buildLabels = True
                    for multipletListView in spectrumView.multipletListViews:
                        multipletListView.buildSymbols = True
                        multipletListView.buildLabels = True
                        multipletListView.buildArrows = True

                spectrumView.buildContours = False
                spectrumView.buildContoursOnly = False

                # rebuild the contours
                if spectrumView not in self._contourList.keys():
                    self._contourList[spectrumView] = GLVertexArray(numLists=1,
                                                                    renderMode=GLRENDERMODE_DRAW,
                                                                    blendMode=False,
                                                                    drawMode=GL.GL_LINES,
                                                                    dimension=2,
                                                                    GLContext=self)

                spectrumView._buildGLContours(self._contourList[spectrumView])

                self._buildSpectrumSetting(spectrumView=spectrumView)

                rebuildFlag = True

                # define the VBOs to pass to the graphics card
                self._contourList[spectrumView].defineIndexVBO()

        # rebuild the traces as the spectrum/plane may have changed
        if rebuildFlag:
            self.rebuildTraces()

    @staticmethod
    def enableTextClientState():
        _attribArrayIndex = 1
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glEnableVertexAttribArray(_attribArrayIndex)

    @staticmethod
    def disableTextClientState():
        _attribArrayIndex = 1
        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glDisableVertexAttribArray(_attribArrayIndex)

    def buildGrid(self):
        """Build the grids for the mainGrid and the bottom/right axes
        """

        # build the axes
        self.axisLabelling, self.axesChanged = self._buildAxes(self.gridList[0], axisList=[0, 1],
                                                               scaleGrid=[1, 0],
                                                               r=self.foreground[0],
                                                               g=self.foreground[1],
                                                               b=self.foreground[2],
                                                               transparency=300.0,
                                                               _includeDiagonal=self._matchingIsotopeCodes,
                                                               _diagonalList=None,
                                                               _includeAxis=False)  #self.diagonalGLList)

        if self.axesChanged:
            if self.highlighted:
                self._buildAxes(self.gridList[1], axisList=[1], scaleGrid=[1, 0], r=self.highlightColour[0],
                                g=self.highlightColour[1],
                                b=self.highlightColour[2], transparency=32.0)
                self._buildAxes(self.gridList[2], axisList=[0], scaleGrid=[1, 0], r=self.highlightColour[0],
                                g=self.highlightColour[1],
                                b=self.highlightColour[2], transparency=32.0)
            else:
                self._buildAxes(self.gridList[1], axisList=[1], scaleGrid=[1, 0], r=self.foreground[0],
                                g=self.foreground[1],
                                b=self.foreground[2], transparency=32.0)
                self._buildAxes(self.gridList[2], axisList=[0], scaleGrid=[1, 0], r=self.foreground[0],
                                g=self.foreground[1],
                                b=self.foreground[2], transparency=32.0)

            # buffer the lists to VBOs
            for gr in self.gridList:
                gr.defineIndexVBO()

            # # buffer the diagonal GL line
            # self.diagonalGLList.defineIndexVBO()

    def drawGrid(self):
        # set to the mainView and draw the grid
        # self.buildGrid()

        GL.glEnable(GL.GL_BLEND)
        GL.glLineWidth(GLDefs.GLDEFAULTLINETHICKNESS * self.viewports.devicePixelRatio)

        # draw the main grid
        if self._gridVisible:
            self.viewports.setViewport(self._currentView)
            self.gridList[0].drawIndexVBO()

        # draw the diagonal line - independent of viewing the grid
        if self._matchingIsotopeCodes:  # and self.diagonalGLList:
            # viewport above may not be set
            if not self._gridVisible:
                self.viewports.setViewport(self._currentView)
            if self.diagonalGLList:
                self.diagonalGLList.drawIndexVBO()
            if self.diagonalSideBandsGLList and self._sideBandsVisible:
                self.diagonalSideBandsGLList.drawIndexVBO()

        # draw the axes tick marks (effectively the same grid in smaller viewport)
        if self._axesVisible:
            if self._drawRightAxis:
                # draw the grid marks for the right axis
                self.viewports.setViewport(self._currentRightAxisView)
                self.gridList[1].drawIndexVBO()

            if self._drawBottomAxis:
                # draw the grid marks for the bottom axis
                self.viewports.setViewport(self._currentBottomAxisView)
                self.gridList[2].drawIndexVBO()

    def _floatFormat(self, f=0.0, prec=3):
        """return a float string, remove trailing zeros after decimal
        """
        return (('%.' + str(prec) + 'f') % f).rstrip('0').rstrip('.')

    def _intFormat(self, ii=0, prec=0):
        """return an integer string
        """
        return self._floatFormat(ii, 1)
        # return '%i' % ii

    def _eFormat(self, f=0.0, prec=4):
        """return an exponential with trailing zeroes removed
        """
        s = '%.*e' % (prec, f)
        if 'e' in s:
            mantissa, exp = s.split('e')
            mantissa = mantissa.rstrip('0')
            if mantissa.endswith('.'):
                mantissa += '0'
            exp = exp.lstrip('0+')
            if exp:
                if exp.startswith('-'):
                    return '%se%d' % (mantissa, int(exp))
                else:
                    return '%se+%d' % (mantissa, int(exp))
            else:
                return '%s' % mantissa

        else:
            return ''

    def _buildSingleWildCard(self, _axisCodes):
        """Buld the axisCode appending wildcard as required
        """
        _code = ''
        if _axisCodes:
            _maxLen = max(len(ax) for ax in _axisCodes)
            _chs = [a for a in zip(*_axisCodes)]
            for ch in _chs:
                chSet = set(ch)
                if len(chSet) == 1:
                    _code += ch[0]
                else:
                    _code += '*'
                    break
            else:
                if len(_code) < _maxLen:
                    _code += '*'
        _code = _code or '*'

        return _code

    def _buildAxisCodesWithWildCards(self):
        """Build the visible axis codes from the visible spectra appending wildcard as required
        """
        _visibleSpec = [(specView, self._spectrumSettings[specView])
                        for specView in self._ordering
                        if not specView.isDeleted and specView.isDisplayed and
                        specView in self._spectrumSettings]
        _firstVisible = ((self._ordering[0], self._spectrumSettings[self._ordering[0]]),) \
            if self._ordering and not self._ordering[0].isDeleted and \
               self._ordering[0] in self._spectrumSettings else ()
        self._visibleOrderingDict = _visibleSpec or _firstVisible

        # quick fix to take the set of matching letters from the spectrum axisCodes - append a '*' to denote trailing differences
        if self.spectrumDisplay.is1D:
            # get the x-axis codes for 1d
            dim = self.spectrumDisplay._flipped

            _axisCodes = [spec.spectrum.axisCodes[0] for spec, settings in self._visibleOrderingDict]
            if dim:
                _axisWildCards = (
                    self.axisCodes[1 - dim] or '*',
                    self._buildSingleWildCard(_axisCodes),
                    )
            else:
                _axisWildCards = (
                    self._buildSingleWildCard(_axisCodes),
                    self.axisCodes[1 - dim] or '*',
                    )

        else:
            dim = len(self.spectrumDisplay.axisCodes)
            _axisWildCards = []
            for axis in range(dim):
                # get the correct x-axis mapped axis codes for Nd
                _axisCodes = []
                for spec, settings in self._visibleOrderingDict:
                    try:
                        _axisCodes.append(spec.spectrum.axisCodes[settings.dimensionIndices[axis]])
                    except Exception as es:
                        # can skip for now
                        pass
                _code = self._buildSingleWildCard(_axisCodes)
                _axisWildCards.append(_code)

        self._visibleOrderingAxisCodes = _axisWildCards

    def buildAxisLabels(self, refresh=False):
        # build axes labelling
        if refresh or self.axesChanged:

            self._axisXLabelling = []
            self._axisScaleLabelling = []

            if self.highlighted:
                labelColour = self.highlightColour
            else:
                labelColour = self.foreground

            smallFont = self.getAxisFont()

            if self._drawBottomAxis:
                # create the X axis labelling
                for axLabel in self.axisLabelling['0'].values():
                    axisX = axLabel[2]
                    axisXLabel = axLabel[3]

                    if self.YAXISUSEEFORMAT:
                        axisXText = self.XMode(axisXLabel)
                    else:
                        axisXText = self._intFormat(axisXLabel) if axLabel[4] >= 1 else self.XMode(axisXLabel)

                    self._axisXLabelling.append(GLString(text=axisXText,
                                                         font=smallFont,
                                                         x=axisX - (0.4 * smallFont.charWidth * self.deltaX * len(
                                                                 axisXText)),
                                                         y=self.AXIS_MARGINBOTTOM - GLDefs.TITLEYOFFSET * smallFont.charHeight,

                                                         colour=labelColour, GLContext=self,
                                                         obj=None))

                # append the axisCode
                self._axisXLabelling.append(GLString(
                        text=self._visibleOrderingAxisCodes[0] if self._visibleOrderingAxisCodes else '*',
                        font=smallFont,
                        x=GLDefs.AXISTEXTXOFFSET * self.deltaX,
                        y=self.AXIS_MARGINBOTTOM - GLDefs.TITLEYOFFSET * smallFont.charHeight,
                        colour=labelColour, GLContext=self,
                        obj=None))
                # and the axis dimensions
                xUnitsLabels = self.XAXES[self._xUnits]
                self._axisXLabelling.append(GLString(text=xUnitsLabels,
                                                     font=smallFont,
                                                     x=1.0 - (self.deltaX * len(xUnitsLabels) * smallFont.charWidth),
                                                     y=self.AXIS_MARGINBOTTOM - GLDefs.TITLEYOFFSET * smallFont.charHeight,
                                                     colour=labelColour, GLContext=self,
                                                     obj=None))

            self._axisYLabelling = []

            if self._drawRightAxis:
                # create the Y axis labelling
                for xx, ayLabel in enumerate(self.axisLabelling['1'].values()):
                    axisY = ayLabel[2]
                    axisYLabel = ayLabel[3]

                    if self.YAXISUSEEFORMAT:
                        axisYText = self.YMode(axisYLabel)
                    else:
                        axisYText = self._intFormat(axisYLabel) if ayLabel[4] >= 1 else self.YMode(axisYLabel)

                    self._axisYLabelling.append(GLString(text=axisYText,
                                                         font=smallFont,
                                                         x=self.AXIS_OFFSET,
                                                         y=axisY - (GLDefs.AXISTEXTYOFFSET * self.deltaY),
                                                         colour=labelColour, GLContext=self,
                                                         obj=None))

                # append the axisCode
                self._axisYLabelling.append(GLString(
                        text=self._visibleOrderingAxisCodes[1] if self._visibleOrderingAxisCodes and
                                                                  len(self._visibleOrderingAxisCodes) > 1 else '*',
                        font=smallFont,
                        x=self.AXIS_OFFSET,
                        y=1.0 - (GLDefs.TITLEYOFFSET * smallFont.charHeight * self.deltaY),
                        colour=labelColour, GLContext=self,
                        obj=None))
                # and the axis dimensions
                yUnitsLabels = self.YAXES[self._yUnits]
                self._axisYLabelling.append(GLString(text=yUnitsLabels,
                                                     font=smallFont,
                                                     x=self.AXIS_OFFSET,
                                                     y=1.0 * self.deltaY,
                                                     colour=labelColour, GLContext=self,
                                                     obj=None))

    def drawAxisLabels(self, shader):
        # draw axes labelling

        if self._axesVisible:
            self.buildAxisLabels()

            if self._drawBottomAxis:
                # put the axis labels into the bottom bar
                _w, _h = self.viewports.setViewport(self._currentBottomAxisBarView)

                self._axisScale = QtGui.QVector4D(self.deltaX, 1.0, 1.0, 1.0)
                shader.setAxisScale(self._axisScale)
                shader.setProjection(0.0, 1.0, 0,
                                     self.AXIS_MARGINBOTTOM, -1.0, 1.0)
                # shader.setViewport(QtGui.QVector4D(_w // self.devicePixelRatio(),
                #                                    _h // self.devicePixelRatio(),
                #                                    self.devicePixelRatioF(), 0.0
                #                                    )
                #                    )

                for lb in self._axisXLabelling:
                    lb.drawTextArrayVBO()

            if self._drawRightAxis:
                # put the axis labels into the right bar
                _w, _h = self.viewports.setViewport(self._currentRightAxisBarView)

                self._axisScale = QtGui.QVector4D(1.0, self.deltaY, 1.0, 1.0)
                shader.setAxisScale(self._axisScale)
                shader.setProjection(0, self.AXIS_MARGINRIGHT,
                                     0.0, 1.0, -1.0, 1.0)
                # shader.setViewport(QtGui.QVector4D(_w // self.devicePixelRatio(),
                #                                    _h // self.devicePixelRatio(),
                #                                    self.devicePixelRatioF(), 0.0
                #                                    )
                #                    )

                for lb in self._axisYLabelling:
                    lb.drawTextArrayVBO()

    def removeInfiniteLine(self, line):
        if line in self._infiniteLines:
            self._infiniteLines.remove(line)
        self.update()

    def addInfiniteLine(self, values=None, axisCode=None, orientation=None,
                        brush=None, colour='blue',
                        movable=True, visible=True, bounds=None,
                        obj=None, lineStyle='dashed', lineWidth=1.0):

        if colour in REGION_COLOURS.keys():
            if colour == 'highlight':
                brush = self.highlightColour
            else:
                brush = REGION_COLOURS[colour]
        else:
            brush = colour

        if orientation == 'h':
            axisCode = self._axisCodes[1]
        elif orientation == 'v':
            axisCode = self._axisCodes[0]
        else:
            if axisCode:
                axisIndex = None
                for ps, psCode in enumerate(self._axisCodes[0:2]):
                    if self._preferences.matchAxisCode == 0:  # default - match atom type

                        if axisCode[0] == psCode[0]:
                            axisIndex = ps
                    elif self._preferences.matchAxisCode == 1:  # match full code
                        if axisCode == psCode:
                            axisIndex = ps

                    if axisIndex == 0:
                        orientation = 'v'
                    elif axisIndex == 1:
                        orientation = 'h'

                if not axisIndex:
                    getLogger().warning('Axis code %s not found in current strip' % axisCode)
                    return None
            else:
                axisCode = self._axisCodes[0]
                orientation = 'v'

        newInfiniteLine = GLInfiniteLine(self.strip, self._regionList,
                                         values=values,
                                         axisCode=axisCode,
                                         orientation=orientation,
                                         brush=brush,
                                         colour=colour,
                                         movable=movable,
                                         visible=visible,
                                         bounds=bounds,
                                         obj=obj,
                                         lineStyle=lineStyle,
                                         lineWidth=lineWidth)
        self._infiniteLines.append(newInfiniteLine)

        self.update()
        return newInfiniteLine

    def removeExternalRegion(self, region):
        pass
        self._externalRegions._removeRegion(region)
        self._externalRegions.renderMode = GLRENDERMODE_REBUILD
        # if self._dragRegions[0] == region:
        #   self._dragRegions = set()
        for reg in self._dragRegions:
            if reg[0] == region:
                self._dragRegions.remove(reg)
                break

        self.update()

    def addExternalRegion(self, values=None, axisCode=None, orientation=None,
                          brush=None, colour='blue',
                          movable=True, visible=True, bounds=None,
                          obj=None, **kwds):

        newRegion = self._externalRegions._addRegion(values=values, axisCode=axisCode, orientation=orientation,
                                                     brush=brush, colour=colour,
                                                     movable=movable, visible=visible, bounds=bounds,
                                                     obj=obj, **kwds)

        self._externalRegions.renderMode = GLRENDERMODE_REBUILD
        self.update()

        return newRegion

    def addRegion(self, values=None, axisCode=None, orientation=None,
                  brush=None, colour='blue',
                  movable=True, visible=True, bounds=None,
                  obj=None):

        if colour in REGION_COLOURS.keys():
            brush = REGION_COLOURS[colour]

        if orientation == 'h':
            axisCode = self._axisCodes[1]
        elif orientation == 'v':
            axisCode = self._axisCodes[0]
        else:
            if axisCode:
                axisIndex = None
                for ps, psCode in enumerate(self._axisCodes[0:2]):
                    if self._preferences.matchAxisCode == 0:  # default - match atom type

                        if axisCode[0] == psCode[0]:
                            axisIndex = ps
                    elif self._preferences.matchAxisCode == 1:  # match full code
                        if axisCode == psCode:
                            axisIndex = ps

                    if axisIndex == 0:
                        orientation = 'v'
                    elif axisIndex == 1:
                        orientation = 'h'

                if not axisIndex:
                    getLogger().warning('Axis code %s not found in current strip' % axisCode)
                    return None
            else:
                axisCode = self._axisCodes[0]
                orientation = 'v'

        newRegion = GLRegion(self.strip, self._regionList,
                             values=values,
                             axisCode=axisCode,
                             orientation=orientation,
                             brush=brush,
                             colour=colour,
                             movable=movable,
                             visible=visible,
                             bounds=bounds,
                             obj=obj)
        self._regions.append(newRegion)

        self._regionList.renderMode = GLRENDERMODE_REBUILD
        self.update()
        return newRegion

    def buildRegions(self):

        drawList = self._externalRegions
        if drawList.renderMode == GLRENDERMODE_REBUILD:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode
            drawList._rebuild()

            drawList.defineIndexVBO()

        elif drawList.renderMode == GLRENDERMODE_RESCALE:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode
            drawList._resize()

            drawList.defineIndexVBO()

    def buildMarksRulers(self):
        drawList = self._marksList

        if drawList.renderMode == GLRENDERMODE_REBUILD:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode
            drawList.refreshMode = GLREFRESHMODE_REBUILD
            drawList.clearArrays()

            # clear the attached strings
            self._marksAxisCodes = []

            # build the marks VBO
            index = 0
            # for mark in self.project.marks:
            for mark in self.mainWindow.marks + \
                        self.strip.spectrumDisplay.marks + \
                        self.strip.marks:

                # find the matching axisCodes to the display
                exactMatch = (self._preferences.matchAxisCode == AXIS_FULLATOMNAME)
                indices = getAxisCodeMatchIndices(mark.axisCodes, self._axisCodes[:2], exactMatch=exactMatch,
                                                  allMatches=not exactMatch)

                for axisIndices, rr in zip(indices, mark.rulerData):
                    if not isinstance(axisIndices, tuple):  # may be single axis-code
                        axisIndices = (axisIndices,)

                    for axisIndex in axisIndices:
                        if axisIndex is not None and axisIndex < 2:

                            # NOTE:ED check axis units - assume 'ppm' for the minute
                            if axisIndex == 0:
                                # vertical ruler
                                pos = x0 = x1 = rr.position
                                y0 = self.axisT
                                y1 = self.axisB
                                textX = pos + (3.0 * self.pixelX)
                                textY = self.axisB + (3.0 * self.pixelY)
                            else:
                                # horizontal ruler
                                pos = y0 = y1 = rr.position
                                x0 = self.axisL
                                x1 = self.axisR
                                textX = self.axisL + (3.0 * self.pixelX)
                                textY = pos + (3.0 * self.pixelY)

                            colour = mark.colour
                            colR = int(colour.strip('# ')[0:2], 16) / 255.0
                            colG = int(colour.strip('# ')[2:4], 16) / 255.0
                            colB = int(colour.strip('# ')[4:6], 16) / 255.0

                            drawList.indices = np.append(drawList.indices,
                                                         np.array((index, index + 1), dtype=np.uint32))
                            drawList.vertices = np.append(drawList.vertices,
                                                          np.array((x0, y0, x1, y1), dtype=np.float32))
                            drawList.colors = np.append(drawList.colors,
                                                        np.array((colR, colG, colB, 1.0) * 2, dtype=np.float32))
                            drawList.attribs = np.append(drawList.attribs, (axisIndex, pos, axisIndex, pos))

                            # build the string and add the extra axis code
                            label = rr.label or rr.axisCode

                            newMarkString = GLString(text=label,
                                                     font=self.getSmallFont(),
                                                     x=textX,
                                                     y=textY,
                                                     colour=(colR, colG, colB, 1.0),
                                                     GLContext=self,
                                                     obj=None)
                            # this is in the attribs
                            newMarkString.axisIndex = axisIndex
                            newMarkString.axisPosition = pos
                            self._marksAxisCodes.append(newMarkString)

                            index += 2
                            drawList.numVertices += 2

            drawList.defineIndexVBO()

        elif drawList.renderMode == GLRENDERMODE_RESCALE:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode

            drawList.defineIndexVBO()

    def drawMarksRulers(self):
        if self.strip.isDeleted:
            return

        self._marksList.drawIndexVBO()

    def drawRegions(self):
        if self.strip.isDeleted:
            return

        self._externalRegions.drawIndexVBO()

    def drawMarksAxisCodes(self):
        if self.strip.isDeleted:
            return

        # strings are generated when the marksRulers are modified
        for mark in self._marksAxisCodes:
            mark.drawTextArrayVBO()

    def _scaleAxisToRatio(self, values):
        return [((values[0] - self.axisL) / (self.axisR - self.axisL))
                if values[0] is not None and abs(self.axisR - self.axisL) > 1e-9 else 0.0,
                ((values[1] - self.axisB) / (self.axisT - self.axisB))
                if values[1] is not None and abs(self.axisT - self.axisB) > 1e-9 else 0.0]

    # def buildCursors(self):
    #     """Build and draw the cursors/doubleCursors
    #     """
    #     if not self._disableCursorUpdate and self._crosshairVisible:
    #
    #         # get the next cursor drawList
    #         self._advanceGLCursor()
    #         drawList = self._glCursorQueue[self._glCursorHead]
    #         vertices = []
    #         indices = []
    #         index = 0
    #
    #         # map the cursor to the ratio coordinates - double cursor is flipped about the line x=y
    #
    #         cursorCoordinate = self.getCurrentCursorCoordinate()
    #
    #         newCoords = self._scaleAxisToRatio(cursorCoordinate[0:2])
    #         # doubleCoords = self._scaleAxisToRatio(self.getCurrentDoubleCursorCoordinates()[0:2])
    #
    #         if getCurrentMouseMode() == PICK and self.underMouse():
    #
    #             x = self.deltaX * 8
    #             y = self.deltaY * 8
    #
    #             vertices = [newCoords[0] - x, newCoords[1] - y,
    #                         newCoords[0] + x, newCoords[1] - y,
    #                         newCoords[0] + x, newCoords[1] - y,
    #                         newCoords[0] + x, newCoords[1] + y,
    #                         newCoords[0] + x, newCoords[1] + y,
    #                         newCoords[0] - x, newCoords[1] + y,
    #                         newCoords[0] - x, newCoords[1] + y,
    #                         newCoords[0] - x, newCoords[1] - y
    #                         ]
    #             indices = [0, 1, 2, 3, 4, 5, 6, 7]
    #             col = self.mousePickColour
    #             index = 8
    #
    #         else:
    #             col = self.foreground
    #
    #         phasingFrame = self.spectrumDisplay.phasingFrame
    #         if not phasingFrame.isVisible():
    #             if (coords := self.current.mouseMovedDict):
    #
    #                 # read values from isotopeCode or axisCode
    #                 if self._preferences.matchAxisCode == 0:  # default - match atom type
    #                     atomTypes = self.spectrumDisplay.isotopeCodes
    #                     xPosList = coords[AXIS_MATCHATOMTYPE].get(atomTypes[0], [])
    #                     if not self.spectrumDisplay.is1D:
    #                         yPosList = coords[AXIS_MATCHATOMTYPE].get(atomTypes[1], [])
    #                 else:
    #                     atCodes = self._orderedAxes
    #                     xPosList = coords[AXIS_FULLATOMNAME].get(atCodes[0].code, [])
    #                     if not self.spectrumDisplay.is1D:
    #                         yPosList = coords[AXIS_FULLATOMNAME].get(atCodes[1].code, [])
    #
    #                 foundX = []
    #                 foundY = []
    #                 if not self._updateVTrace and newCoords[0] is not None:
    #                     for pos in xPosList:
    #                         x, _y = self._scaleAxisToRatio([pos, 0])
    #                         if all(abs(x - val) > self.deltaX for val in foundX):
    #
    #                             # store the found value so that overlaying lines are not drawn - OpenGL uses an XOR draw mode
    #                             foundX.append(x)
    #                             vertices.extend([x, 1.0, x, 0.0])
    #                             indices.extend([index, index + 1])
    #                             index += 2
    #
    #                         if self._matchingIsotopeCodes:
    #                             # draw the cursor reflected about the x=y line (need to check gammaRatio)
    #                             _x, y = self._scaleAxisToRatio([0, pos])
    #                             if all(abs(y - val) > self.deltaY for val in foundY):
    #                                 foundY.append(y)
    #                                 vertices.extend([0.0, y, 1.0, y])
    #                                 indices.extend([index, index + 1])
    #                                 index += 2
    #
    #                 if not self._updateHTrace and newCoords[1] is not None and not self.spectrumDisplay.is1D:
    #                     for pos in yPosList:
    #                         _x, y = self._scaleAxisToRatio([0, pos])
    #                         if all(abs(y - val) > self.deltaY for val in foundY):
    #                             foundY.append(y)
    #                             vertices.extend([0.0, y, 1.0, y])
    #                             indices.extend([index, index + 1])
    #                             index += 2
    #
    #                         if self._matchingIsotopeCodes:
    #                             # draw the cursor reflected about the x=y line (need to check gammaRatio)
    #                             x, _y = self._scaleAxisToRatio([pos, 0])
    #                             if all(abs(x - val) > self.deltaX for val in foundX):
    #                                 foundX.append(x)
    #                                 vertices.extend([x, 1.0, x, 0.0])
    #                                 indices.extend([index, index + 1])
    #                                 index += 2
    #
    #             # _drawDouble = True  # self._doubleCrosshairVisible  # any([specView.spectrum.showDoubleCrosshair == True for specView in self._ordering])
    #             #
    #             # if not self._updateVTrace and newCoords[0] is not None:
    #             #     vertices.extend([newCoords[0], 1.0, newCoords[0], 0.0])
    #             #     indices.extend([index, index + 1])
    #             #     index += 2
    #             #
    #             #     # add the double cursor
    #             #     if _drawDouble and self._matchingIsotopeCodes and doubleCoords[0] is not None and abs(doubleCoords[0] - newCoords[0]) > self.deltaX:
    #             #         vertices.extend([doubleCoords[0], 1.0, doubleCoords[0], 0.0])
    #             #         indices.extend([index, index + 1])
    #             #         index += 2
    #             #
    #             # if not self._updateHTrace and newCoords[1] is not None:
    #             #     vertices.extend([0.0, newCoords[1], 1.0, newCoords[1]])
    #             #     indices.extend([index, index + 1])
    #             #     index += 2
    #             #
    #             #     # add the double cursor
    #             #     if _drawDouble and self._matchingIsotopeCodes and doubleCoords[1] is not None and abs(doubleCoords[1] - newCoords[1]) > self.deltaY:
    #             #         vertices.extend([0.0, doubleCoords[1], 1.0, doubleCoords[1]])
    #             #         indices.extend([index, index + 1])
    #             #         index += 2
    #
    #         drawList.vertices = np.array(vertices, dtype=np.float32)
    #         drawList.indices = np.array(indices, dtype=np.int32)
    #         drawList.numVertices = len(vertices) // 2
    #         drawList.colors = np.array(col * drawList.numVertices, dtype=np.float32)
    #
    #         # build and draw the VBO
    #         drawList.defineIndexVBO()

    def drawLastCursors(self):
        """Draw the cursors/doubleCursors
        """
        cursor = self._glCursorQueue[self._glCursorTail]
        if cursor.indices.size:
            cursor.drawIndexVBO()

    def drawCursors(self):
        """Draw the cursors/doubleCursors
        """
        cursor = self._glCursorQueue[self._glCursorHead]
        if cursor.indices.size:
            cursor.drawIndexVBO()

    def getCurrentCursorCoordinate(self):

        if self.cursorSource is None or self.cursorSource == 'self':
            currentPos = self.mapFromGlobal(QtGui.QCursor.pos())

            # calculate mouse coordinate within the mainView
            mx = currentPos.x()
            if self._drawBottomAxis:
                my = self.height() - currentPos.y() - self.AXIS_MOUSEYOFFSET
                _top = self.height() - self.AXIS_MOUSEYOFFSET
            else:
                my = self.height() - currentPos.y()
                _top = self.height()

            mt = self.mouseTransform * QtGui.QVector4D(mx, my, 0.0, 1.0)
            result = [mt.x(), mt.y(), mt.z(), mt.w()]

        else:
            result = self.cursorCoordinate

        return result

    # def getCurrentDoubleCursorCoordinates(self):
    #     if self.cursorSource in (CURSOR_SOURCE_NONE, CURSOR_SOURCE_SELF):
    #         cursorCoordinate = self.getCurrentCursorCoordinate()
    #
    #         # flip cursor about x=y to get double cursor
    #         result = [cursorCoordinate[1],
    #                   cursorCoordinate[0],
    #                   cursorCoordinate[2],
    #                   cursorCoordinate[3]]
    #     else:
    #         result = self.doubleCursorCoordinate
    #
    #     return result

    def drawDottedCursor(self):
        # draw the cursors
        # need to change to VBOs

        GL.glColor4f(*self.zoomLineColour)
        GL.glLineStipple(1, 0xF0F0)
        GL.glEnable(GL.GL_LINE_STIPPLE)

        succClick = self._scaleAxisToRatio(self._successiveClicks[0:2])

        GL.glBegin(GL.GL_LINES)
        GL.glVertex2d(succClick[0], 1.0)
        GL.glVertex2d(succClick[0], 0.0)
        GL.glVertex2d(0.0, succClick[1])
        GL.glVertex2d(1.0, succClick[1])
        GL.glEnd()

        GL.glDisable(GL.GL_LINE_STIPPLE)

    def setInfiniteLineColour(self, infLine, colour):
        for reg in self._infiniteLines:
            if reg == infLine:
                colR = int(colour.strip('# ')[0:2], 16) / 255.0
                colG = int(colour.strip('# ')[2:4], 16) / 255.0
                colB = int(colour.strip('# ')[4:6], 16) / 255.0
                reg.brush = (colR, colG, colB, 1.0)

    def drawInfiniteLines(self):
        # draw the simulated infinite lines - using deprecated GL :)

        GL.glDisable(GL.GL_BLEND)
        GL.glEnable(GL.GL_LINE_STIPPLE)
        for infLine in self._infiniteLines:

            if infLine.visible:
                GL.glColor4f(*infLine.brush)
                GL.glLineStipple(1, GLDefs.GLLINE_STYLES[infLine.lineStyle])

                GL.glLineWidth(infLine.lineWidth * self.viewports.devicePixelRatio)
                GL.glBegin(GL.GL_LINES)
                if infLine.orientation == 'h':
                    GL.glVertex2d(self.axisL, infLine.values)
                    GL.glVertex2d(self.axisR, infLine.values)
                else:
                    GL.glVertex2d(infLine.values, self.axisT)
                    GL.glVertex2d(infLine.values, self.axisB)

                GL.glEnd()

        GL.glDisable(GL.GL_LINE_STIPPLE)
        GL.glLineWidth(GLDefs.GLDEFAULTLINETHICKNESS * self.viewports.devicePixelRatio)

    def setStripID(self, name):
        self.stripIDLabel = name
        self._newStripID = True

    def drawOverlayText(self, refresh=False):
        """Draw extra information to the screen
        """
        # cheat for the moment
        if self._newStripID or self.stripIDString.renderMode == GLRENDERMODE_REBUILD:
            self.stripIDString.renderMode = GLRENDERMODE_DRAW
            self._newStripID = False

            if self.highlighted:
                colour = self.highlightColour
            else:
                colour = self.buttonForeground

            smallFont = self.getSmallFont()
            self.stripIDString = GLString(text=self.stripIDLabel,
                                          font=smallFont,
                                          x=GLDefs.TITLEXOFFSET * smallFont.charWidth * self.deltaX,
                                          y=1.0 - (GLDefs.TITLEYOFFSET * smallFont.charHeight * self.deltaY),
                                          colour=colour, GLContext=self,
                                          obj=None, blendMode=False)

            self._oldStripIDLabel = self.stripIDLabel

        # Don't draw for the minute, but keep for print strip
        # # draw the strip ID to the screen
        # self.stripIDString.drawTextArrayVBO()

        # only display buttons in the first strip (not required in others)
        if self.AXISLOCKEDBUTTON and (
                self.AXISLOCKEDBUTTONALLSTRIPS or self.strip == self.strip.spectrumDisplay.strips[0]):
            if self._aspectRatioMode == 2:
                self._fixedStringTrue.drawTextArrayVBO()
            else:
                self._fixedStringFalse.drawTextArrayVBO()

            if self._aspectRatioMode == 1:
                self._lockedStringTrue.drawTextArrayVBO()
            else:
                self._lockedStringFalse.drawTextArrayVBO()

    def _rescaleRegions(self):
        self._externalRegions._rescale()

    def _rescaleMarksRulers(self):
        vertices = self._marksList.numVertices

        if vertices:
            for pp in range(0, 2 * vertices, 4):
                axisIndex = int(self._marksList.attribs[pp])
                axisPosition = self._marksList.attribs[pp + 1]

                if axisIndex == 0:
                    offsets = [axisPosition, self.axisT,
                               axisPosition, self.axisB]
                else:
                    offsets = [self.axisL, axisPosition,
                               self.axisR, axisPosition]
                self._marksList.vertices[pp:pp + 4] = offsets

            self._marksList.defineIndexVBO()

    def _rescaleMarksAxisCode(self, mark):
        vertices = mark.numVertices

        # mark.attribs[0][0] = axisIndex
        # mark.attribs[0][1] = axisPosition
        if vertices:
            if mark.axisIndex == 0:
                offsets = [mark.axisPosition + (GLDefs.MARKTEXTXOFFSET * self.pixelX),
                           self.axisB + (GLDefs.MARKTEXTYOFFSET * self.pixelY)]
            else:
                offsets = [self.axisL + (GLDefs.MARKTEXTXOFFSET * self.pixelX),
                           mark.axisPosition + (GLDefs.MARKTEXTYOFFSET * self.pixelY)]

            for pp in range(0, 4 * vertices, 4):
                mark.attribs[pp:pp + 2] = offsets

            # redefine the mark's VBOs
            mark.pushTextArrayVBOAttribs()

    def rescaleMarksRulers(self):
        """rescale the marks
        """
        self._rescaleMarksRulers()
        for mark in self._marksAxisCodes:
            self._rescaleMarksAxisCode(mark)

    def setRightAxisVisible(self, axisVisible=True):
        """Set the visibility of the right axis
        """
        self._drawRightAxis = axisVisible
        if self._drawRightAxis and self._drawBottomAxis:
            self._fullHeightRightAxis = self._fullWidthBottomAxis = False
        else:
            self._fullHeightRightAxis = self._fullWidthBottomAxis = True

        self.rescale(rescaleStaticHTraces=False)
        self.update()

    def setBottomAxisVisible(self, axisVisible=True):
        """Set the visibility of the bottom axis
        """
        self._drawBottomAxis = axisVisible
        if self._drawRightAxis and self._drawBottomAxis:
            self._fullHeightRightAxis = self._fullWidthBottomAxis = False
        else:
            self._fullHeightRightAxis = self._fullWidthBottomAxis = True

        self.rescale(rescaleStaticVTraces=False)
        self.update()

    def getAxesVisible(self):
        """Get the visibility of the axes
        """
        return (self._drawRightAxis, self._drawBottomAxis)

    def setAxesVisible(self, rightAxisVisible=True, bottomAxisVisible=False):
        """Set the visibility of the axes
        """
        self._drawRightAxis = rightAxisVisible
        self._drawBottomAxis = bottomAxisVisible

    @property
    def axesVisible(self):
        return self._axesVisible

    @axesVisible.setter
    def axesVisible(self, visible):
        self._axesVisible = visible
        self.update()

    def toggleAxes(self):
        self._axesVisible = not self._axesVisible
        self.update()

    @property
    def showSpectraOnPhasing(self):
        return self._showSpectraOnPhasing

    @showSpectraOnPhasing.setter
    def showSpectraOnPhasing(self, visible):
        self._showSpectraOnPhasing = visible
        self.update()

    def toggleShowSpectraOnPhasing(self):
        self._showSpectraOnPhasing = not self._showSpectraOnPhasing
        self.update()

    @property
    def axisOrder(self):
        return self._axisOrder

    @axisOrder.setter
    def axisOrder(self, axisOrder):
        self._axisOrder = axisOrder

    @property
    def axisCodes(self):
        return self._axisCodes

    @axisCodes.setter
    def axisCodes(self, axisCodes):
        self._axisCodes = axisCodes

    @property
    def xUnits(self):
        return self._xUnits

    @xUnits.setter
    def xUnits(self, xUnits):
        self._xUnits = xUnits
        self._rescaleAllAxes()

    @property
    def yUnits(self):
        return self._yUnits

    @yUnits.setter
    def yUnits(self, yUnits):
        self._yUnits = yUnits
        self._rescaleAllAxes()

    @property
    def aspectRatioMode(self):
        return self._aspectRatioMode

    @aspectRatioMode.setter
    def aspectRatioMode(self, value):
        self._aspectRatioMode = value
        self._rescaleAllAxes()

    @property
    def aspectRatios(self):
        return self._aspectRatios

    @aspectRatios.setter
    def aspectRatios(self, value):
        self._aspectRatios = value
        self._rescaleAllAxes()

    @property
    def orderedAxes(self):
        return self._orderedAxes

    @orderedAxes.setter
    def orderedAxes(self, axes):
        self._orderedAxes = axes

        try:
            if self._orderedAxes[1] and self._orderedAxes[1].code == 'intensity':
                self.mouseFormat = " %s: %.3f\n %s: %.6g"
                self.diffMouseFormat = " d%s: %.3f\n d%s: %.6g"
            else:
                self.mouseFormat = " %s: %.3f\n %s: %.3f"
                self.diffMouseFormat = " d%s: %.3f\n d%s: %.3f"
        except:
            self.mouseFormat = " %s: %.3f  %s: %.4g"
            self.diffMouseFormat = " d%s: %.3f  d%s: %.4g"

    @property
    def updateHTrace(self):
        return self._updateHTrace

    @updateHTrace.setter
    def updateHTrace(self, visible):
        self._updateHTrace = visible

    @property
    def updateVTrace(self):
        return self._updateVTrace

    @updateVTrace.setter
    def updateVTrace(self, visible):
        self._updateVTrace = visible

    @staticmethod
    def _valueToRatio(val, x0, x1):
        if abs(x1 - x0) > 1e-9:
            return (val - x0) / (x1 - x0)
        else:
            return 0.0

    def _ensureOnScreen(self, mx, my, xROff : float = 0, xLOff : float = 0,
                        yTOff : float = 0, yBOff : float = 0) -> tuple[float, float]:
        """Check the string is constraint to the bounds of the strip
        :param mx: Crosshair x coordinate
        :param my: Crosshair y coordinate
        :param xROff: Offset from right of crosshair
        :param xLOff: Offset from left of crosshair
        :param yTOff: Offset from top of crosshair
        :param yBOff: Offset from bottom of crosshair
        :return: Offsets - tuple[ox, oy]
        """
        _mouseOffsetR = self._valueToRatio(mx + xROff, self.axisL, self.axisR)
        _mouseOffsetL = self._valueToRatio(mx + xLOff, self.axisL, self.axisR)
        ox = -min(max(_mouseOffsetR - 1.0, 0.0), _mouseOffsetL)

        _mouseOffsetT = self._valueToRatio(my + yTOff, self.axisB, self.axisT)
        _mouseOffsetB = self._valueToRatio(my + yBOff, self.axisB, self.axisT)
        oy = -min(max(_mouseOffsetT - 1.0, 0.0), _mouseOffsetB)

        return ox, oy

    def buildMouseCoordsDQ(self, refresh=False):
        """Builds Mouse Coord text for DQ crosshair."""
        try:
            cursorCoordinate = self.mouseCoordDQ
            mx, my = cursorCoordinate[0], cursorCoordinate[1]
        except (AttributeError, TypeError):
            return

        smallFont = self.getSmallFont()
        newCoords = (f' {self._visibleOrderingAxisCodes[0]}: {self.XMode(mx)}\n'
                     f' {self._visibleOrderingAxisCodes[1]}: {self.YMode(my)}')

        self.mouseStringDQ = True

        self.mouseStringDQ = GLString(text=newCoords,
                                      font=smallFont,
                                      x=self._valueToRatio(mx - self.pixelX * 85.0, self.axisL, self.axisR),
                                      y=self._valueToRatio(my - self.pixelY * self.mouseString.height, self.axisB,
                                                           self.axisT),
                                      colour=self.foreground, GLContext=self,
                                      obj=None)

        xOff = self.pixelX * 80.0
        yOff = self.pixelY * self.mouseString.height
        ox, oy = self._ensureOnScreen(mx, my, xLOff=-xOff, yBOff=-yOff)
        self.mouseStringDQ.setStringOffset((ox, oy))
        self.mouseStringDQ.pushTextArrayVBOAttribs()

    def buildMouseCoords(self, refresh=False):
        def valueToRatio(val, x0, x1):
            if abs(x1 - x0) > 1e-9:
                return (val - x0) / (x1 - x0)
            else:
                return 0.0

        cursorCoordinate = self.getCurrentCursorCoordinate()
        if refresh or self._widthsChangedEnough(cursorCoordinate[:2], self._mouseCoords[:2], tol=1e-8):

            if not self._drawDeltaOffset:
                self._startCoordinate = cursorCoordinate

            # get the list of visible spectrumViews, or the first in the list
            visibleSpectrumViews = [specView for specView in self._ordering
                                    if not specView.isDeleted and specView.isDisplayed]
            thisSpecView = visibleSpectrumViews[0] if visibleSpectrumViews else \
                self._ordering[0] if self._ordering and not self._ordering[0].isDeleted else None

            if thisSpecView:
                specSet = self._spectrumSettings[thisSpecView]

                # generate different axes depending on units - X Axis
                if self.XAXES[self._xUnits] == GLDefs.AXISUNITSINTENSITY:
                    cursorX = cursorCoordinate[0]
                    startX = self._startCoordinate[0]

                elif self.XAXES[self._xUnits] == GLDefs.AXISUNITSPPM:
                    cursorX = cursorCoordinate[0]
                    startX = self._startCoordinate[0]
                    # XMode = '%.3f'

                elif self.XAXES[self._xUnits] == GLDefs.AXISUNITSHZ:
                    if self._ordering:
                        freq = specSet.spectrometerFrequency[0]
                        cursorX = cursorCoordinate[0] * freq
                        startX = self._startCoordinate[0] * freq

                    else:
                        # error trap all spectra deleted
                        cursorX = cursorCoordinate[0]
                        startX = self._startCoordinate[0]

                else:
                    if self._ordering:
                        ppm2point = specSet.ppmToPoint[0]
                        cursorX = ppm2point(cursorCoordinate[0])
                        startX = ppm2point(self._startCoordinate[0])

                    else:
                        # error trap all spectra deleted
                        cursorX = cursorCoordinate[0]
                        startX = self._startCoordinate[0]

                # generate different axes depending on units - Y Axis, always use first option for 1d
                if self.YAXES[self._yUnits] == GLDefs.AXISUNITSINTENSITY:
                    cursorY = cursorCoordinate[1]
                    startY = self._startCoordinate[1]

                elif self.YAXES[self._yUnits] == GLDefs.AXISUNITSPPM:
                    cursorY = cursorCoordinate[1]
                    startY = self._startCoordinate[1]

                elif self.YAXES[self._yUnits] == GLDefs.AXISUNITSHZ:
                    if self._ordering:
                        freq = specSet.spectrometerFrequency[1]
                        cursorY = cursorCoordinate[1] * freq
                        startY = self._startCoordinate[1] * freq

                    else:
                        # error trap all spectra deleted
                        cursorY = cursorCoordinate[1]
                        startY = self._startCoordinate[1]

                else:
                    if self._ordering:
                        ppm2point = specSet.ppmToPoint[1]
                        # map to a point
                        cursorY = ppm2point(cursorCoordinate[1])
                        startY = ppm2point(self._startCoordinate[1])

                    else:
                        # error trap all spectra deleted
                        cursorY = cursorCoordinate[1]
                        startY = self._startCoordinate[1]

            else:

                # no visible spectra
                return

            deltaOffset = 0
            newCoords = (f' {self._visibleOrderingAxisCodes[0]}: {self.XMode(cursorX)}\n'
                         f' {self._visibleOrderingAxisCodes[1]}: {self.YMode(cursorY)}')

            smallFont = self.getSmallFont()

            if self._drawDeltaOffset:
                newCoords += '\n d%s: %s\n d%s: %s' % (self._visibleOrderingAxisCodes[0], self.XMode(cursorX - startX),
                                                       self._visibleOrderingAxisCodes[1], self.YMode(cursorY - startY))
                deltaOffset = smallFont.charHeight * 2.0 * self.pixelY

            mx, my = cursorCoordinate[0], cursorCoordinate[1] - deltaOffset
            self.mouseString = GLString(text=newCoords,
                                        font=smallFont,
                                        x=valueToRatio(mx, self.axisL, self.axisR),
                                        y=valueToRatio(my, self.axisB, self.axisT),
                                        colour=self.foreground, GLContext=self,
                                        obj=None)
            self._mouseCoords = (cursorCoordinate[0], cursorCoordinate[1])

            # check that the string is actually visible, or constraint to the bounds of the strip
            # _offset = self.pixelX * 80.0
            # _mouseOffsetR = valueToRatio(mx + _offset, self.axisL, self.axisR)
            # _mouseOffsetL = valueToRatio(mx, self.axisL, self.axisR)
            # ox = -min(max(_mouseOffsetR - 1.0, 0.0), _mouseOffsetL)
            #
            # _offset = self.pixelY * self.mouseString.height
            # _mouseOffsetT = valueToRatio(my + _offset, self.axisB, self.axisT)
            # _mouseOffsetB = valueToRatio(my, self.axisB, self.axisT)
            # oy = -min(max(_mouseOffsetT - 1.0, 0.0), _mouseOffsetB)

            xOff = self.pixelX * 80.0
            yOff = self.pixelY * self.mouseString.height
            ox, oy = self._ensureOnScreen(mx, my, xROff=xOff, yTOff=yOff)
            self.mouseString.setStringOffset((ox, oy))
            self.mouseString.pushTextArrayVBOAttribs()

            self.buildMouseCoordsDQ()

    def drawMouseCoords(self):
        # if self.underMouse() or self._disableCursorUpdate:  # and self.mouseString:  # crosshairVisible
        #     self.buildMouseCoords()

        if self.underMouse():
            if self.mouseString is not None:
                # draw the mouse coordinates to the screen
                self.mouseString.drawTextArrayVBO()
            if self.mouseStringDQ is not None:
                self.mouseStringDQ.drawTextArrayVBO()


    def drawSelectionBox(self):
        # should really use the proper VBOs for this
        if self._drawSelectionBox:
            GL.glEnable(GL.GL_BLEND)

            self._dragStart = self._scaleAxisToRatio(self._startCoordinate[0:2])
            self._dragEnd = self._scaleAxisToRatio(self._endCoordinate[0:2])

            if self._selectionMode == 1:  # yellow
                GL.glColor4f(*self.zoomAreaColour)
            elif self._selectionMode == 2:  # purple
                GL.glColor4f(*self.selectAreaColour)
            elif self._selectionMode == 3:  # cyan
                GL.glColor4f(*self.pickAreaColour)
            else:  # red
                GL.glColor4f(*self.badAreaColour)

            GL.glBegin(GL.GL_QUADS)
            GL.glVertex2d(self._dragStart[0], self._dragStart[1])
            GL.glVertex2d(self._dragEnd[0], self._dragStart[1])
            GL.glVertex2d(self._dragEnd[0], self._dragEnd[1])
            GL.glVertex2d(self._dragStart[0], self._dragEnd[1])
            GL.glEnd()

            if self._selectionMode == 1:  # yellow
                GL.glColor4f(*self.zoomAreaColourHard)
            elif self._selectionMode == 2:  # purple
                GL.glColor4f(*self.selectAreaColourHard)
            elif self._selectionMode == 3:  # cyan
                GL.glColor4f(*self.pickAreaColourHard)
            else:  # red
                GL.glColor4f(*self.badAreaColourHard)

            GL.glBegin(GL.GL_LINE_STRIP)
            GL.glVertex2d(self._dragStart[0], self._dragStart[1])
            GL.glVertex2d(self._dragEnd[0], self._dragStart[1])
            GL.glVertex2d(self._dragEnd[0], self._dragEnd[1])
            GL.glVertex2d(self._dragStart[0], self._dragEnd[1])
            GL.glVertex2d(self._dragStart[0], self._dragStart[1])
            GL.glEnd()
            GL.glDisable(GL.GL_BLEND)

    def drawMouseMoveLine(self):
        """Draw the line for the middleMouse dragging of peaks
        """
        if self._drawMouseMoveLine:
            GL.glColor4f(*self.mouseMoveLineColour)
            GL.glBegin(GL.GL_LINES)

            cursorCoordinate = self.getCurrentCursorCoordinate()
            startCoord = self._scaleAxisToRatio(self._startCoordinate[0:2])
            cursCoord = self._scaleAxisToRatio(cursorCoordinate[0:2])

            GL.glVertex2d(startCoord[0], startCoord[1])
            GL.glVertex2d(cursCoord[0], cursCoord[1])
            GL.glEnd()

    def _getSliceDataTest(self, spectrumView, points, sliceDim, ppmPositions, range):
        # quick method for testing
        # need to block logging
        with notificationEchoBlocking(self.application):
            code = spectrumView.spectrum.axisCodes[0]
            vpps = spectrumView.spectrum.ppmPerPoints
            axisCodes = spectrumView.spectrum.axisCodes

            _region = {axis: (ppmPosition + 0.5 * vpp, ppmPosition + 0.5 * vpp)
                       for axis, ppmPosition, vpp, in zip(axisCodes, ppmPositions, vpps)}
            _region[code] = sorted(range)

            data = spectrumView.spectrum.getRegion(**_region)

            if spectrumView._traceScale is None:
                spectrumView._traceScale = 1.0 / max(data) * 0.5
        return data

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Code for traces
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _newStaticHTraceData(self, spectrumView, tracesDict,
                             point, dim, positionPixel):

        try:
            data = spectrumView._getSliceData(points=point, sliceDim=dim)
            x = spectrumView.spectrum.getPpmArray(dimension=dim)
            _posColour = spectrumView.posColours[0]
            colR, colG, colB = _posColour[0:3]

            hSpectrum = GLVertexArray(numLists=1,
                                      renderMode=GLRENDERMODE_RESCALE,
                                      blendMode=False,
                                      drawMode=GL.GL_LINE_STRIP,
                                      dimension=2,
                                      GLContext=self)
            tracesDict.append(hSpectrum)

            # add extra vertices to give a horizontal line across the trace
            xLen = x.size
            x = np.append(x, (x[xLen - 1], x[0]))

            numVertices = len(x)
            hSpectrum.indices = numVertices
            hSpectrum.numVertices = numVertices
            hSpectrum.indices = np.arange(numVertices, dtype=np.uint32)
            hSpectrum.vertices = np.empty(hSpectrum.numVertices * 2, dtype=np.float32)
            hSpectrum.vertices[::2] = x
            hSpectrum.colors = np.array(self._phasingTraceColour * numVertices, dtype=np.float32)

            # change to colour of the last 2 points to the spectrum colour
            colLen = hSpectrum.colors.size
            hSpectrum.colors[colLen - 8:colLen] = (colR, colG, colB, 1.0, colR, colG, colB, 1.0)

            # store the pre-phase data
            hSpectrum.data = data
            hSpectrum.positionPixel = positionPixel
            hSpectrum.spectrumView = spectrumView

        except Exception as es:
            tracesDict = []

    def _newStaticVTraceData(self, spectrumView, tracesDict,
                             point, dim, positionPixel):

        try:
            data = spectrumView._getSliceData(points=point, sliceDim=dim)
            y = spectrumView.spectrum.getPpmArray(dimension=dim)
            _posColour = spectrumView.posColours[0]
            colR, colG, colB = _posColour[0:3]

            vSpectrum = GLVertexArray(numLists=1,
                                      renderMode=GLRENDERMODE_RESCALE,
                                      blendMode=False,
                                      drawMode=GL.GL_LINE_STRIP,
                                      dimension=2,
                                      GLContext=self)
            tracesDict.append(vSpectrum)

            # add extra vertices to give a horizontal line across the trace
            yLen = y.size
            y = np.append(y, (y[yLen - 1], y[0]))

            numVertices = len(y)
            vSpectrum.indices = numVertices
            vSpectrum.numVertices = numVertices
            vSpectrum.indices = np.arange(numVertices, dtype=np.uint32)
            vSpectrum.vertices = np.empty(vSpectrum.numVertices * 2, dtype=np.float32)
            vSpectrum.vertices[1::2] = y
            vSpectrum.colors = np.array(self._phasingTraceColour * numVertices, dtype=np.float32)

            # change to colour of the last 2 points to the spectrum colour
            colLen = vSpectrum.colors.size
            vSpectrum.colors[colLen - 8:colLen] = (colR, colG, colB, 1.0, colR, colG, colB, 1.0)

            # store the pre-phase data
            vSpectrum.data = data
            vSpectrum.positionPixel = positionPixel
            vSpectrum.spectrumView = spectrumView

        except Exception as es:
            tracesDict = []

    def _updateHTraceData(self, spectrumView, tracesDict,
                          point, dim, positionPixel,
                          ph0=None, ph1=None, pivot=None):

        try:
            data = spectrumView._getSliceData(points=point, sliceDim=dim)

            if ph0 is not None and ph1 is not None and pivot is not None:
                data = Phasing.phaseRealData(data, ph0, ph1, pivot)

            x = spectrumView.spectrum.getPpmArray(dimension=dim)

            # x = spectrumView.spectrum.getPpmAliasingLimitsArray(dimension=dim)  # this seems okay - need to check _getSliceData
            # data = self._getSliceDataTest(spectrumView=spectrumView, points=point, sliceDim=dim,
            #                               ppmPositions=positionPixel, range=[x[0], x[-1]])
            # data = data[0]
            # if ph0 is not None and ph1 is not None and pivot is not None:
            #     data = Phasing.phaseRealData(data, ph0, ph1, pivot)

            y = positionPixel[1] + spectrumView._traceScale * (self.axisT - self.axisB) * data
            _posColour = spectrumView.posColours[0]
            colR, colG, colB = _posColour[0:3]

            if spectrumView not in tracesDict.keys():
                tracesDict[spectrumView] = GLVertexArray(numLists=1,
                                                         renderMode=GLRENDERMODE_REBUILD,
                                                         blendMode=False,
                                                         drawMode=GL.GL_LINE_STRIP,
                                                         dimension=2,
                                                         GLContext=self)

            # add extra vertices to give a horizontal line across the trace
            xLen = x.size
            x = np.append(x, (x[xLen - 1], x[0]))
            y = np.append(y, (positionPixel[1], positionPixel[1]))

            numVertices = len(x)
            hSpectrum = tracesDict[spectrumView]
            hSpectrum.indices = numVertices
            hSpectrum.numVertices = numVertices
            hSpectrum.indices = np.arange(numVertices, dtype=np.uint32)
            hSpectrum.vertices = np.empty(numVertices * 2, dtype=np.float32)
            hSpectrum.vertices[::2] = x
            hSpectrum.vertices[1::2] = y
            hSpectrum.colors = np.array([colR, colG, colB, 1.0] * numVertices, dtype=np.float32)

            # colour the negative points - gives a nice fade
            if self._preferences.traceIncludeNegative:
                _negColour = spectrumView.negColours[0]
                _negCol = [*_negColour[0:3], 1.0]
                mask = np.nonzero(data < 0.0)
                for mm in mask[0]:
                    m4 = mm * 4
                    hSpectrum.colors[m4:m4 + 4] = _negCol

        except Exception as es:
            tracesDict[spectrumView].clearArrays()

    def _updateVTraceData(self, spectrumView, tracesDict,
                          point, dim, positionPixel,
                          ph0=None, ph1=None, pivot=None):

        try:
            data = spectrumView._getSliceData(points=point, sliceDim=dim)

            if ph0 is not None and ph1 is not None and pivot is not None:
                data = Phasing.phaseRealData(data, ph0, ph1, pivot)

            y = spectrumView.spectrum.getPpmArray(dimension=dim)
            x = positionPixel[0] + spectrumView._traceScale * (self.axisL - self.axisR) * data
            _posColour = spectrumView.posColours[0]
            colR, colG, colB = _posColour[0:3]

            if spectrumView not in tracesDict.keys():
                tracesDict[spectrumView] = GLVertexArray(numLists=1,
                                                         renderMode=GLRENDERMODE_REBUILD,
                                                         blendMode=False,
                                                         drawMode=GL.GL_LINE_STRIP,
                                                         dimension=2,
                                                         GLContext=self)

            # add extra vertices to give a vertical line across the trace
            yLen = y.size
            y = np.append(y, (y[yLen - 1], y[0]))
            x = np.append(x, (positionPixel[0], positionPixel[0]))

            numVertices = len(x)
            vSpectrum = tracesDict[spectrumView]
            vSpectrum.indices = numVertices
            vSpectrum.numVertices = numVertices
            vSpectrum.indices = np.arange(numVertices, dtype=np.uint32)
            vSpectrum.vertices = np.zeros(numVertices * 2, dtype=np.float32)
            vSpectrum.vertices[::2] = x
            vSpectrum.vertices[1::2] = y
            vSpectrum.colors = np.array([colR, colG, colB, 1.0] * numVertices, dtype=np.float32)

            # colour the negative points - gives a nice fade
            if self._preferences.traceIncludeNegative:
                _negColour = spectrumView.negColours[0]
                _negCol = [*_negColour[0:3], 1.0]
                mask = np.nonzero(data < 0.0)
                for mm in mask[0]:
                    m4 = mm * 4
                    vSpectrum.colors[m4:m4 + 4] = _negCol

        except Exception as es:
            tracesDict[spectrumView].clearArrays()

    # NOTE:ED - remember these for later, may create larger vertex arrays for symbols, but should be quicker
    #       --
    #       x = np.array([1, 2, 3, -1, 5, 0, 3, 4, 4, 7, 3, 5, 9, 0, 5, 4, 3], dtype=np.uint32)
    #       seems to be the fastest way of getting masked values
    #           SKIPINDEX = np.uint32(-1) = 4294967295
    #           i.e. max index number, use as fill
    #           timeit.timeit('import numpy as np; x = np.array([1, 2, 3, -1, 5, 0, 3, 4, 4, 7, 3, 5, 9, 0, 5, 4, 3], dtype=np.uint32); x[np.where(x != 3)]', number=200000)
    #       fastest way to create filled arrays
    #           *** timeit.timeit('import numpy as np; x = np.array([1, 2, 3, -1, 5, 0, 3, 4, 4, 7, 3, 5, 9, 0, 5, 4, 3], dtype=np.uint32); a = x[x != SKIPINDEX]', number=200000)
    #               timeit.timeit('import numpy as np; x = np.array([1, 2, 3, -1, 5, 0, 3, 4, 4, 7, 3, 5, 9, 0, 5, 4, 3], dtype=np.uint32); mx = np.full(200000, SKIPINDEX, dtype=np.uint32)', number=20000)
    #       --
    #       np.take(x, np.where(x != 3))
    #       mx = np.ma.masked_values(x, 3)
    #       a = x[np.where(x != 3)]
    #       *** a = x[x != SKIPINDEX]
    #       np.where(data < 0)[0] * 4

    def updateTraces(self):
        if self.strip.isDeleted:
            return

        cursorCoordinate = self.getCurrentCursorCoordinate()
        position = [cursorCoordinate[0], cursorCoordinate[1]]  #list(cursorPosition)
        for axis in self._orderedAxes[2:]:
            position.append(axis.position)

        for spectrumView in self._ordering:  # strip.spectrumViews:
            if spectrumView.isDeleted:
                continue

            if self.showActivePhaseTrace and self._tracesNeedUpdating(spectrumView):

                phasingFrame = self.spectrumDisplay.phasingFrame
                dimension = spectrumView.dimensionIndices
                ppm2point = spectrumView.spectrum.ppm2point
                point2ppm = spectrumView.spectrum.point2ppm

                if phasingFrame.isVisible():
                    ph0 = phasingFrame.slider0.value()
                    ph1 = phasingFrame.slider1.value()
                    pivotPpm = phasingFrame.pivotEntry.get()
                    direction = phasingFrame.getDirection()

                    axisIndex = dimension[direction]
                    pivot = ppm2point(pivotPpm, dimension=axisIndex + 1) - 1
                else:
                    direction = 0
                    ph0 = ph1 = pivot = None

                # map to the spectrum pointPositions
                point = [ppm2point(position[dimension.index(n)], dimension=n + 1) - 1 for n in range(len(dimension))]
                intPositionPixel = [point2ppm(round(point[n]) + 1, dimension=n + 1) for n in dimension]

                if direction == 0:
                    if self._updateHTrace:
                        self._updateHTraceData(spectrumView, self._hTraces, point, dimension[0] + 1, intPositionPixel,
                                               ph0, ph1, pivot)
                    if self._updateVTrace:
                        self._updateVTraceData(spectrumView, self._vTraces, point, dimension[1] + 1, intPositionPixel)
                else:
                    # pivots are on the opposite axis
                    if self._updateHTrace:
                        self._updateHTraceData(spectrumView, self._hTraces, point, dimension[0] + 1, intPositionPixel)
                    if self._updateVTrace:
                        self._updateVTraceData(spectrumView, self._vTraces, point, dimension[1] + 1, intPositionPixel,
                                               ph0, ph1, pivot)

    def newTrace(self, position=None):
        # cursorCoordinate = self.getCurrentCursorCoordinate(self.cursorCoordinate)
        cursorCoordinate = self.current.cursorPosition
        position = position if position else [cursorCoordinate[0], cursorCoordinate[1]]

        # add to the list of traces
        self._currentTraces.append(position)

        for axis in self._orderedAxes[2:]:
            position.append(axis.position)

        for spectrumView in self._ordering:  # strip.spectrumViews:

            if spectrumView.isDeleted:
                continue

            # only add phasing trace for the visible spectra
            if spectrumView.isDisplayed:

                phasingFrame = self.spectrumDisplay.phasingFrame

                ph0 = phasingFrame.slider0.value()
                ph1 = phasingFrame.slider1.value()
                pivotPpm = phasingFrame.pivotEntry.get()
                direction = phasingFrame.getDirection()
                dimension = spectrumView.dimensionIndices
                ppm2point = spectrumView.spectrum.ppm2point
                point2ppm = spectrumView.spectrum.point2ppm

                if self.is1D:
                    pivot = spectrumView.spectrum.ppm2point(pivotPpm, dimension=1) - 1

                    self._newStatic1DTraceData(spectrumView,
                                               self._staticVTraces if self.spectrumDisplay._flipped else self._staticHTraces,
                                               position, ph0, ph1, pivot)

                else:
                    # map to the spectrum pointPositions
                    point = [ppm2point(position[dimension.index(n)], dimension=n + 1) - 1
                             for n in range(len(dimension))]
                    intPositionPixel = [point2ppm(round(point[n]) + 1, dimension=n + 1) for n in dimension]

                    if direction == 0:
                        self._newStaticHTraceData(spectrumView, self._staticHTraces, point, dimension[0] + 1,
                                                  intPositionPixel)
                    else:
                        self._newStaticVTraceData(spectrumView, self._staticVTraces, point, dimension[1] + 1,
                                                  intPositionPixel)

    def clearStaticTraces(self):
        self._staticVTraces = []
        self._staticHTraces = []
        self._currentTraces = []
        self.update()

    def rescaleStaticTraces(self):
        for hTrace in self._staticHTraces:
            hTrace.renderMode = GLRENDERMODE_RESCALE

        for vTrace in self._staticVTraces:
            vTrace.renderMode = GLRENDERMODE_RESCALE

        # need to update the current active trace - force reset of lastVisible trace
        for spectrumView in self._ordering:
            numDim = len(spectrumView.strip.axes)
            self._lastTracePoint[spectrumView] = [-1] * numDim

        # rebuild traces
        self.updateTraces()
        self.update()

    def rescaleStaticHTraces(self):
        for hTrace in self._staticHTraces:
            hTrace.renderMode = GLRENDERMODE_RESCALE

    def rescaleStaticVTraces(self):
        for vTrace in self._staticVTraces:
            vTrace.renderMode = GLRENDERMODE_RESCALE

    def rebuildTraces(self):
        traces = self._currentTraces
        self.clearStaticTraces()
        for trace in traces:
            self.newTrace(trace[:2])

    def buildStaticTraces(self):

        phasingFrame = self.spectrumDisplay.phasingFrame
        if phasingFrame.isVisible():
            ph0 = phasingFrame.slider0.value()
            ph1 = phasingFrame.slider1.value()
            pivotPpm = phasingFrame.pivotEntry.get()
            direction = phasingFrame.getDirection()

            deleteHList = []
            for trace in self._staticHTraces:

                specView = trace.spectrumView

                if specView and specView.isDeleted:
                    deleteHList.append(trace)
                    continue

                if trace.renderMode == GLRENDERMODE_RESCALE:
                    trace.renderMode = GLRENDERMODE_DRAW

                    axisIndex = specView.dimensionIndices[direction]
                    pivot = specView.spectrum.ppm2point(pivotPpm, dimension=axisIndex + 1)
                    positionPixel = trace.positionPixel
                    preData = Phasing.phaseRealData(trace.data, ph0, ph1, pivot)

                    if self.is1D:
                        trace.vertices[1::2] = preData
                    else:
                        y = positionPixel[1] + specView._traceScale * (self.axisT - self.axisB) * preData
                        y = np.append(y, (positionPixel[1], positionPixel[1]))
                        trace.vertices[1::2] = y

                    # build the VBOs here
                    trace.defineVertexColorVBO()

            for dd in deleteHList:
                self._staticHTraces.remove(dd)

            deleteVList = []
            for trace in self._staticVTraces:

                specView = trace.spectrumView

                if specView and specView.isDeleted:
                    deleteVList.append(trace)
                    continue

                if trace.renderMode == GLRENDERMODE_RESCALE:
                    trace.renderMode = GLRENDERMODE_DRAW

                    axisIndex = specView.dimensionIndices[direction]
                    pivot = specView.spectrum.ppm2point(pivotPpm, dimension=axisIndex + 1)
                    positionPixel = trace.positionPixel
                    preData = Phasing.phaseRealData(trace.data, ph0, ph1, pivot)

                    if self.is1D:
                        trace.vertices[::2] = preData
                    else:
                        x = positionPixel[0] + specView._traceScale * (self.axisL - self.axisR) * preData
                        x = np.append(x, (positionPixel[0], positionPixel[0]))
                        trace.vertices[::2] = x

                    # build the VBOs here
                    trace.defineVertexColorVBO()

            for dd in deleteVList:
                self._staticVTraces.remove(dd)

    def drawTraces(self, shader):
        if self.strip.isDeleted:
            return

        phasingFrame = self.spectrumDisplay.phasingFrame
        if phasingFrame.isVisible():

            for hTrace in self._staticHTraces:
                if hTrace.spectrumView and not hTrace.spectrumView.isDeleted and hTrace.spectrumView.isDisplayed:

                    if self._stackingMode:
                        # use the stacking matrix to offset the 1D spectra
                        shader.setMVMatrix(self._spectrumSettings[hTrace.spectrumView].stackedMatrix)
                    else:
                        shader.setMVMatrixToIdentity()
                    hTrace.drawVertexColorVBO()

            for vTrace in self._staticVTraces:
                if vTrace.spectrumView and not vTrace.spectrumView.isDeleted and vTrace.spectrumView.isDisplayed:

                    if self._stackingMode:
                        # use the stacking matrix to offset the 1D spectra
                        shader.setMVMatrix(self._spectrumSettings[vTrace.spectrumView].stackedMatrix)
                    else:
                        shader.setMVMatrixToIdentity()
                    vTrace.drawVertexColorVBO()

        # only paint if mouse is in the window, or menu has been raised in this strip
        if self.underMouse() or self._menuActive:

            deleteHList = []
            if self._updateHTrace and (self.showActivePhaseTrace or not phasingFrame.isVisible()):
                for hTrace in self._hTraces.keys():
                    trace = self._hTraces[hTrace]
                    if hTrace and hTrace.isDeleted:
                        deleteHList.append(hTrace)
                        continue

                    if hTrace and not hTrace.isDeleted and hTrace.isVisible():
                        trace.defineVertexColorVBO()
                        trace.drawVertexColorVBO()

            for dd in deleteHList:
                del self._hTraces[dd]

            deleteVList = []
            if self._updateVTrace and (self.showActivePhaseTrace or not phasingFrame.isVisible()):
                for vTrace in self._vTraces.keys():
                    trace = self._vTraces[vTrace]
                    if vTrace and vTrace.isDeleted:
                        deleteVList.append(vTrace)
                        continue

                    if vTrace and not vTrace.isDeleted and vTrace.isVisible():
                        trace.defineVertexColorVBO()
                        trace.drawVertexColorVBO()

            for dd in deleteVList:
                del self._vTraces[dd]

    # NOTE:ED - don't delete this yet
    # def _makeSpectrumArray(self, spectrumView, drawList):
    #     drawList.renderMode = GLRENDERMODE_DRAW
    #     drawList.clearArrays()
    #
    #     for position, dataArray in spectrumView._getPlaneData():
    #         ma = np.amax(dataArray)
    #         mi = np.amin(dataArray)
    #         # min(  abs(  fract(P.z * gsize) - 0.5), 0.2);
    #         # newData = np.clip(np.absolute(np.remainder((50.0*dataArray/ma), 1.0)-0.5), 0.2, 50.0)
    #         dataScale = 15.0
    #         newData = dataScale * dataArray / ma
    #         npX = dataArray.shape[0]
    #         npY = dataArray.shape[1]
    #
    #         indexing = (npX - 1) * (npY - 1)
    #         elements = npX * npY
    #         drawList.indices = np.zeros(int(indexing * 6), dtype=np.uint32)
    #         drawList.vertices = np.zeros(int(elements * 4), dtype=np.float32)
    #         drawList.colors = np.zeros(int(elements * 4), dtype=np.float32)
    #
    #         ii = 0
    #         for y0 in range(0, npY):
    #             for x0 in range(0, npX):
    #                 vertex = [y0, x0, newData[x0, y0], 0.5 + newData[x0, y0] / (2.0 * dataScale)]
    #                 color = [0.5, 0.5, 0.5, 1.0]
    #                 drawList.vertices[ii * 4:ii * 4 + 4] = vertex
    #                 drawList.colors[ii * 4:ii * 4 + 4] = color
    #                 ii += 1
    #         drawList.numVertices = elements
    #
    #         ii = 0
    #         for y0 in range(0, npY - 1):
    #             for x0 in range(0, npX - 1):
    #                 corner = x0 + (y0 * npX)
    #                 indices = [corner, corner + 1, corner + npX,
    #                            corner + 1, corner + npX, corner + 1 + npX]
    #                 drawList.indices[ii * 6:ii * 6 + 6] = indices
    #                 ii += 1
    #         break

    @staticmethod
    def set3DProjection():
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(-0.5, +0.5, +0.5, -0.5, 4.0, 15.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

    @staticmethod
    def setClearColor(c):
        GL.glClearColor(c.redF(), c.greenF(), c.blueF(), c.alphaF())

    @staticmethod
    def setColor(c):
        GL.glColor4f(c.redF(), c.greenF(), c.blueF(), c.alphaF())

    def highlightCurrentStrip(self, current):
        if current:
            self.highlighted = True

            self._updateAxes = True
            for gr in self.gridList:
                gr.renderMode = GLRENDERMODE_REBUILD
            if self.stripIDString:
                self.stripIDString.renderMode = GLRENDERMODE_REBUILD

        else:
            self.highlighted = False

            self._updateAxes = True
            for gr in self.gridList:
                gr.renderMode = GLRENDERMODE_REBUILD
            if self.stripIDString:
                self.stripIDString.renderMode = GLRENDERMODE_REBUILD

        self.update()

    def _buildAxes(self, gridGLList, axisList=None, scaleGrid=None, r=0.0, g=0.0, b=0.0, transparency=256.0,
                   _includeDiagonal=False, _diagonalList=None, _includeAxis=True):
        """Build the grid
        """

        def getDigit(ll, order):
            ss = '{0:.1f}'.format(ll[3] / order)
            valLen = len(ss)
            return ss[valLen - 3]

        def getDigitLen(ll, order):
            ss = '{0:.1f}'.format(ll[3] / order)
            return len(ss)

        def check(ll):
            # check if a number ends in an even digit
            val = '%.0f' % (ll[3] / ll[4])
            valLen = len(val)
            if val[valLen - 1] in '02468':
                return True

        def valueToRatio(val, x0, x1):
            return (val - x0) / (x1 - x0)

        labelling = {'0': {}, '1': {}}
        axesChanged = False
        _minPow = None
        _minOrder = None
        _minSet = False
        _labelRestrictList = ('0123456789', '0258', '05', '0')

        # check if the width is too small to draw too many grid levels
        boundX = (self.w - self.AXIS_MARGINRIGHT) if self._drawRightAxis else self.w
        boundY = (self.h - self.AXIS_MOUSEYOFFSET) if self._drawBottomAxis else self.h
        scaleBounds = (boundX, boundY)

        if gridGLList.renderMode == GLRENDERMODE_REBUILD:

            # get the list of visible spectrumViews, or the first in the list
            visibleSpectrumViews = [specView for specView in self._ordering
                                    if not specView.isDeleted and specView.isDisplayed]
            thisSpecView = visibleSpectrumViews[0] if visibleSpectrumViews else \
                self._ordering[0] if self._ordering and not self._ordering[0].isDeleted else None

            if thisSpecView:
                # thisSpec = thisSpecView.spectrum
                specSet = self._spectrumSettings[thisSpecView]

                if self.XAXES[self._xUnits] == GLDefs.AXISUNITSINTENSITY:  # self.is1D:
                    axisLimitL = self.axisL
                    axisLimitR = self.axisR
                    self.XMode = self._eFormat  # '%.6g'

                # generate different axes depending on units - X Axis
                elif self.XAXES[self._xUnits] == GLDefs.AXISUNITSPPM:
                    axisLimitL = self.axisL
                    axisLimitR = self.axisR
                    self.XMode = self._floatFormat

                elif self.XAXES[self._xUnits] == GLDefs.AXISUNITSHZ:
                    if self._ordering:
                        freq = specSet.spectrometerFrequency[0]
                        axisLimitL = self.axisL * freq
                        axisLimitR = self.axisR * freq

                    else:
                        # error trap all spectra deleted
                        axisLimitL = self.axisL
                        axisLimitR = self.axisR
                    self.XMode = self._floatFormat

                else:
                    if self._ordering:
                        ppm2point = specSet.ppmToPoint[0]
                        axisLimitL = ppm2point(self.axisL)
                        axisLimitR = ppm2point(self.axisR)

                    else:
                        # error trap all spectra deleted
                        axisLimitL = self.axisL
                        axisLimitR = self.axisR
                    self.XMode = self._intFormat

                # generate different axes depending on units - Y Axis, always use first option for 1d
                if self.YAXES[self._yUnits] == GLDefs.AXISUNITSINTENSITY:  # self.is1D:
                    axisLimitT = self.axisT
                    axisLimitB = self.axisB
                    self.YMode = self._eFormat  # '%.6g'

                elif self.YAXES[self._yUnits] == GLDefs.AXISUNITSPPM:
                    axisLimitT = self.axisT
                    axisLimitB = self.axisB
                    self.YMode = self._floatFormat  # '%.3f'

                elif self.YAXES[self._yUnits] == GLDefs.AXISUNITSHZ:
                    if self._ordering:
                        freq = specSet.spectrometerFrequency[1]
                        axisLimitT = self.axisT * freq
                        axisLimitB = self.axisB * freq

                    else:
                        axisLimitT = self.axisT
                        axisLimitB = self.axisB
                    self.YMode = self._floatFormat  # '%.3f'

                else:
                    if self._ordering:
                        ppm2point = specSet.ppmToPoint[1]
                        axisLimitT = ppm2point(self.axisT)
                        axisLimitB = ppm2point(self.axisB)

                    else:
                        axisLimitT = self.axisT
                        axisLimitB = self.axisB
                    self.YMode = self._intFormat  # '%i'

                minX = min(axisLimitL, axisLimitR)
                maxX = max(axisLimitL, axisLimitR)
                minY = min(axisLimitT, axisLimitB)
                maxY = max(axisLimitT, axisLimitB)
                ul = np.array([minX, minY])
                br = np.array([maxX, maxY])

                gridGLList.renderMode = GLRENDERMODE_DRAW
                axesChanged = True

                gridGLList.clearArrays()

                vertexList = ()
                indexList = ()
                colorList = ()

                index = 0
                for scaleOrder, i in enumerate(scaleGrid):  #  [2,1,0]:   ## Draw three different scales of grid
                    dist = br - ul

                    if 0 in dist:
                        # skip if one of the axes is zero
                        continue

                    nlTarget = 10.**i  # i: 0 -> major tick-marks, 1 -> minor, (2 -> tiny-minor :) if needed)
                    _pow = np.log10(abs(dist / nlTarget)) + 0.5
                    d = 10.**np.floor(_pow)
                    if 0 in d:
                        continue

                    ul1 = np.ceil(ul / d) * d  # get the first tick-mark inside
                    br1 = np.ceil(br / d) * d  # get the last tick-mark outside
                    dist = br1 - ul1
                    nl = (dist / d) + 0.5  # tick marks to draw - 0.5 fixes rounding errors for small numbers
                    # _kk = 0
                    # print(f'i:{i}  dx:{(br-ul)[_kk]:0.5f}    dist:{dist[_kk]:5}  _pow:{_pow[_kk]:5}'
                    #       f'  d:{d[_kk]:5}  min:{ul1[_kk]:5}  max:{br1[_kk]:5}  nl:{nl[_kk]:5}')

                    # _minPow = np.floor(_pow) if _minPow is None else np.minimum(_minPow, np.floor(_pow))
                    _minOrder = d if _minOrder is None else np.minimum(_minOrder, d)
                    p1 = np.array([0., 0.])
                    p2 = np.array([0., 0.])
                    for ax in axisList:  #   range(0,2):  ## Draw grid for both axes

                        c = 30.0 + (scaleOrder * 20)
                        bx = (ax + 1) % 2  # x-y ordering

                        for x in range(0, int(nl[ax])):
                            p1[ax] = ul1[ax] + x * d[ax]
                            p2[ax] = p1[ax]
                            p1[bx] = ul[bx]
                            p2[bx] = br[bx]
                            if p1[ax] < min(ul[ax], br[ax]) or p1[ax] > max(ul[ax], br[ax]):
                                continue

                            if i == 1:  # should be largest scale grid
                                d[0] = self._round_sig(d[0], sig=4)
                                d[1] = self._round_sig(d[1], sig=4)

                                if ax == 0:
                                    includeGrid = not (self.XMode == self._intFormat and d[0] < 1 and
                                                       abs(p1[0] - int(p1[0])) > d[0] / 2.0)
                                else:
                                    includeGrid = not (self.YMode == self._intFormat and d[1] < 1 and
                                                       abs(p1[1] - int(p1[1])) > d[1] / 2.0)

                                if includeGrid:
                                    if '%.5f' % p1[0] == '%.5f' % p2[0]:  # check whether a vertical line - x axis
                                        pp = self._round_sig(p1[0], sig=10)

                                        # xLabel = str(int(p1[0])) if d[0] >=1 else self.XMode % p1[0]
                                        labelling[str(ax)][pp] = ((i, ax, valueToRatio(p1[0], axisLimitL, axisLimitR),
                                                                   pp, d[0]))
                                    else:
                                        pp = self._round_sig(p1[1], sig=10)

                                        # num = int(p1[1]) if d[1] >=1 else self.XMode % p1[1]
                                        labelling[str(ax)][pp] = ((i, ax, valueToRatio(p1[1], axisLimitB, axisLimitT),
                                                                   pp, d[1]))

                                    # append the new points to the end of nparray, ignoring narrow grids
                                    if scaleBounds[ax] * (scaleOrder + 1) > AXES_MARKER_MIN_PIXEL:
                                        indexList += (index, index + 1)
                                        vertexList += (valueToRatio(p1[0], axisLimitL, axisLimitR),
                                                       valueToRatio(p1[1], axisLimitB, axisLimitT),
                                                       valueToRatio(p2[0], axisLimitL, axisLimitR),
                                                       valueToRatio(p2[1], axisLimitB, axisLimitT))

                                        alpha = min([1.0, c / transparency])
                                        colorList += (r, g, b, alpha, r, g, b, alpha)

                                        gridGLList.numVertices += 2
                                        index += 2

                # add the extra axis lines
                if _includeAxis:
                    for ax in axisList:

                        offset = GLDefs.AXISDRAWOFFSET if self.AXIS_INSIDE else (1 - GLDefs.AXISDRAWOFFSET)
                        if ax == 0:
                            # add the x-axis line
                            indexList += (index, index + 1)
                            vertexList += (0.0, offset, 1.0, offset)
                            colorList += (r, g, b, 1.0, r, g, b, 1.0)
                            gridGLList.numVertices += 2
                            index += 2

                        elif ax == 1:
                            # add the y-axis line
                            indexList += (index, index + 1)
                            vertexList += (1.0 - offset, 0.0, 1.0 - offset, 1.0)
                            colorList += (r, g, b, 1.0, r, g, b, 1.0)
                            gridGLList.numVertices += 2
                            index += 2

                # copy the arrays the GLstore
                gridGLList.vertices = np.array(vertexList, dtype=np.float32)
                gridGLList.indices = np.array(indexList, dtype=np.uint32)
                gridGLList.colors = np.array(colorList, dtype=np.float32)

                # restrict the labelling to the maximum without overlap based on width
                # should be dependent on font size though
                _maxChars = 1
                for k, val in list(labelling['0'].items()):
                    _maxChars = max(_maxChars, getDigitLen(val, _minOrder[0]))
                _width = self.w / (7.0 * _maxChars)  # num of columns
                restrictList = 0
                ll = len(labelling['0'])
                while ll > _width and restrictList < 3:
                    ll /= 2
                    restrictList += 1
                for k, val in list(labelling['0'].items()):
                    if getDigit(val, _minOrder[0]) not in _labelRestrictList[restrictList]:
                        # remove the item
                        del labelling['0'][k]

                _height = self.h / 15.0  # num of rows
                restrictList = 0
                ll = len(labelling['1'])
                while ll > _height and restrictList < 3:
                    ll /= 2
                    restrictList += 1
                for k, val in list(labelling['1'].items()):
                    if getDigit(val, _minOrder[1]) not in _labelRestrictList[restrictList]:
                        # remove the item
                        del labelling['1'][k]

        return labelling, axesChanged

    @staticmethod
    def _widthsChangedEnough(r1, r2, tol=1e-5):
        if len(r1) != len(r2):
            raise ValueError('WidthsChanged must be the same length')

        for ii in zip(r1, r2):
            if abs(ii[0] - ii[1]) > tol:
                return True

    def getAxisPosition(self, axisIndex):
        position = None
        if axisIndex == 0:
            position = (self.axisR + self.axisL) / 2.0

        elif axisIndex == 1:
            position = (self.axisT + self.axisB) / 2.0

        return position

    def setAxisPosition(self, axisIndex, position, rescale=True, update=True):
        if axisIndex == 0:
            diff = (self.axisR - self.axisL) / 2.0
            self.axisL = position - diff
            self.axisR = position + diff

            if rescale:
                self._rescaleXAxis(rescale=rescale, update=update)

        elif axisIndex == 1:
            diff = (self.axisT - self.axisB) / 2.0
            self.axisB = position - diff
            self.axisT = position + diff

            if rescale:
                self._rescaleYAxis(rescale=rescale, update=update)

    def getAxisWidth(self, axisIndex):
        width = None
        if axisIndex == 0:
            width = abs(self.axisR - self.axisL)

        elif axisIndex == 1:
            width = abs(self.axisT - self.axisB)

        return width

    def setAxisWidth(self, axisIndex, width, rescale=True, update=True):
        if axisIndex == 0:
            diff = self.sign(self.axisR - self.axisL) * abs(width) / 2.0
            mid = (self.axisR + self.axisL) / 2.0
            self.axisL = mid - diff
            self.axisR = mid + diff

            self._scaleToXAxis(rescale=rescale, update=update)

        elif axisIndex == 1:
            diff = self.sign(self.axisT - self.axisB) * abs(width) / 2.0
            mid = (self.axisT + self.axisB) / 2.0
            self.axisB = mid - diff
            self.axisT = mid + diff

            self._scaleToYAxis(rescale=rescale, update=update)

    def getAxisRegion(self, axisIndex):
        """Return the region for visible axisIndex 0/1 (for X/Y)
        if axis is reversed, the region will be returned as (max, min)
        """
        if axisIndex == 0:
            return self.axisL, self.axisR

        elif axisIndex == 1:
            return self.axisB, self.axisT

    def setAxisRegion(self, axisIndex, region, rescale=True, update=True):
        if axisIndex == 0:
            if self.XDIRECTION < 0:
                self.axisL = max(region)
                self.axisR = min(region)
            else:
                self.axisL = min(region)
                self.axisR = max(region)

            if rescale:
                self._rescaleXAxis(rescale=rescale, update=update)

        elif axisIndex == 1:
            if self.YDIRECTION < 0:
                self.axisB = max(region)
                self.axisT = min(region)
            else:
                self.axisB = min(region)
                self.axisT = max(region)

            if rescale:
                self._rescaleYAxis(rescale=rescale, update=update)

    @pyqtSlot(dict)
    def _glXAxisChanged(self, aDict):
        if self._aspectRatioMode:
            self._glAllAxesChanged(aDict)
            return

        if self.strip.isDeleted:
            return

        if aDict[GLNotifier.GLSOURCE] != self and aDict[GLNotifier.GLSPECTRUMDISPLAY] == self.spectrumDisplay:

            # match only the scale for the X axis
            _dict = aDict[GLNotifier.GLAXISVALUES]

            axisL = _dict[GLNotifier.GLLEFTAXISVALUE]
            axisR = _dict[GLNotifier.GLRIGHTAXISVALUE]
            row = _dict[GLNotifier.GLSTRIPROW]
            col = _dict[GLNotifier.GLSTRIPCOLUMN]

            if any(val is None for val in (axisL, axisR, row, col)):
                return

            if self._widthsChangedEnough([axisL, self.axisL], [axisR, self.axisR]):

                if self.spectrumDisplay.stripArrangement == 'Y':
                    if self.strip.tilePosition[1] == col:
                        self.axisL = axisL
                        self.axisR = axisR
                    else:
                        diff = (axisR - axisL) / 2.0
                        mid = (self.axisR + self.axisL) / 2.0
                        self.axisL = mid - diff
                        self.axisR = mid + diff

                elif self.spectrumDisplay.stripArrangement == 'X':
                    if self.strip.tilePosition[0] == row:
                        self.axisL = axisL
                        self.axisR = axisR
                    else:
                        diff = (axisR - axisL) / 2.0
                        mid = (self.axisR + self.axisL) / 2.0
                        self.axisL = mid - diff
                        self.axisR = mid + diff
                else:
                    raise
                self._rescaleXAxis()
                self._storeZoomHistory()

    @pyqtSlot(dict)
    def _glAxisLockChanged(self, aDict):
        if self.strip.isDeleted:
            return

        if aDict[GLNotifier.GLSOURCE] != self and aDict[GLNotifier.GLSPECTRUMDISPLAY] == self.spectrumDisplay:
            self._aspectRatioMode = aDict[GLNotifier.GLVALUES][0]

            if self._aspectRatioMode:

                # check which is the primary axis and update the opposite axis - similar to wheelEvent
                if self.spectrumDisplay.stripArrangement == 'Y':

                    # strips are arranged in a row
                    self._scaleToYAxis()

                elif self.spectrumDisplay.stripArrangement == 'X':

                    # strips are arranged in a column
                    self._scaleToXAxis()

                elif self.spectrumDisplay.stripArrangement == 'T':

                    # NOTE:ED - Tiled plots not fully implemented yet
                    getLogger().warning(f'Tiled plots not implemented for spectrumDisplay: '
                                        f'{str(self.spectrumDisplay.pid)}')

                else:
                    getLogger().warning(f'Strip direction is not defined for spectrumDisplay: '
                                        f'{str(self.spectrumDisplay.pid)}')

            else:
                # paint to update lock button colours
                self.update()

    @pyqtSlot(dict)
    def _glAxisUnitsChanged(self, aDict):
        if self.strip.isDeleted:
            return

        # update the list of visible spectra
        self._updateVisibleSpectrumViews()

        if aDict[GLNotifier.GLSOURCE] != self and aDict[GLNotifier.GLSPECTRUMDISPLAY] == self.spectrumDisplay:

            # read values from dataDict and set units
            if aDict[GLNotifier.GLVALUES]:  # and aDict[GLNotifier.GLVALUES][GLDefs.AXISLOCKASPECTRATIO]:

                self._xUnits = aDict[GLNotifier.GLVALUES][GLDefs.AXISXUNITS]
                self._yUnits = aDict[GLNotifier.GLVALUES][GLDefs.AXISYUNITS]
                if GLDefs.AXISASPECTRATIOMODE in aDict[GLNotifier.GLVALUES]:
                    aRM = aDict[GLNotifier.GLVALUES][GLDefs.AXISASPECTRATIOMODE]

                    if self._aspectRatioMode != aRM:
                        self._aspectRatioMode = aRM
                        changeDict = {GLNotifier.GLSOURCE         : None,
                                      GLNotifier.GLSPECTRUMDISPLAY: self.spectrumDisplay,
                                      GLNotifier.GLVALUES         : (aRM,)
                                      }
                        self._glAxisLockChanged(changeDict)

                    if GLDefs.AXISASPECTRATIOS in aDict[GLNotifier.GLVALUES]:
                        self._aspectRatios.update(aDict[GLNotifier.GLVALUES][GLDefs.AXISASPECTRATIOS])
                        if aRM == 2:
                            self._rescaleAllZoom(rescale=True)

            # spawn rebuild event for the grid
            self._updateAxes = True
            if self.gridList:
                for gr in self.gridList:
                    gr.renderMode = GLRENDERMODE_REBUILD
            self.update()

    @pyqtSlot(dict)
    def _glYAxisChanged(self, aDict):
        if self._aspectRatioMode:
            self._glAllAxesChanged(aDict)
            return

        if self.strip.isDeleted:
            return

        if aDict[GLNotifier.GLSOURCE] != self and aDict[GLNotifier.GLSPECTRUMDISPLAY] == self.spectrumDisplay:

            # match the Y axis
            _dict = aDict[GLNotifier.GLAXISVALUES]

            axisB = _dict[GLNotifier.GLBOTTOMAXISVALUE]
            axisT = _dict[GLNotifier.GLTOPAXISVALUE]
            row = _dict[GLNotifier.GLSTRIPROW]
            col = _dict[GLNotifier.GLSTRIPCOLUMN]

            if any(val is None for val in (axisB, axisT, row, col)):
                return

            if self._widthsChangedEnough([axisB, self.axisB], [axisT, self.axisT]):

                if self.spectrumDisplay.stripArrangement == 'Y':
                    if self.strip.tilePosition[0] == row:
                        self.axisB = axisB
                        self.axisT = axisT
                    else:
                        diff = (axisT - axisB) / 2.0
                        mid = (self.axisT + self.axisB) / 2.0
                        self.axisB = mid - diff
                        self.axisT = mid + diff

                elif self.spectrumDisplay.stripArrangement == 'X':
                    if self.strip.tilePosition[1] == col:
                        self.axisB = axisB
                        self.axisT = axisT
                    else:
                        diff = (axisT - axisB) / 2.0
                        mid = (self.axisT + self.axisB) / 2.0
                        self.axisB = mid - diff
                        self.axisT = mid + diff
                else:
                    raise

                self._rescaleYAxis()
                self._storeZoomHistory()

    @pyqtSlot(dict)
    def _glAllAxesChanged(self, aDict):
        if self.strip.isDeleted:
            return

        sDisplay = aDict[GLNotifier.GLSPECTRUMDISPLAY]
        source = aDict[GLNotifier.GLSOURCE]

        if source != self and sDisplay == self.spectrumDisplay:

            # match the values for the Y axis, and scale for the X axis
            _dict = aDict[GLNotifier.GLAXISVALUES]

            axisB = _dict[GLNotifier.GLBOTTOMAXISVALUE]
            axisT = _dict[GLNotifier.GLTOPAXISVALUE]
            axisL = _dict[GLNotifier.GLLEFTAXISVALUE]
            axisR = _dict[GLNotifier.GLRIGHTAXISVALUE]
            row = _dict[GLNotifier.GLSTRIPROW]
            col = _dict[GLNotifier.GLSTRIPCOLUMN]
            # zoomAll = _dict[GLNotifier.GLSTRIPZOOMALL]

            if any(val is None for val in (axisB, axisT, axisL, axisR, row, col)):
                return

            if self._widthsChangedEnough([axisB, self.axisB], [axisT, self.axisT]) and \
                    self._widthsChangedEnough([axisL, self.axisL], [axisR, self.axisR]):

                # # do the matching row and column only unless _useLockedAspect or self._useDefaultAspect are set
                # if not (self.strip.tilePosition[0] == row or self.strip.tilePosition[1] == col) and \
                #         not (self._useLockedAspect or self._useDefaultAspect) and zoomAll:
                #     return

                if self.spectrumDisplay.stripArrangement == 'Y':

                    # strips are arranged in a row
                    if self.strip.tilePosition[1] == col:
                        self.axisL = axisL
                        self.axisR = axisR
                    else:  #if self._useLockedAspect or self._useDefaultAspect:
                        diff = (axisR - axisL) / 2.0
                        mid = (self.axisR + self.axisL) / 2.0
                        self.axisL = mid - diff
                        self.axisR = mid + diff

                    if self.strip.tilePosition[0] == row:
                        self.axisB = axisB
                        self.axisT = axisT
                    else:  #if self._useLockedAspect or self._useDefaultAspect:
                        diff = (axisT - axisB) / 2.0
                        mid = (self.axisT + self.axisB) / 2.0
                        self.axisB = mid - diff
                        self.axisT = mid + diff

                elif self.spectrumDisplay.stripArrangement == 'X':

                    # strips are arranged in a column
                    if self.strip.tilePosition[1] == col:
                        self.axisB = axisB
                        self.axisT = axisT
                    else:  #if self._useLockedAspect or self._useDefaultAspect:
                        diff = (axisT - axisB) / 2.0
                        mid = (self.axisT + self.axisB) / 2.0
                        self.axisB = mid - diff
                        self.axisT = mid + diff

                    if self.strip.tilePosition[0] == row:
                        self.axisL = axisL
                        self.axisR = axisR
                    else:  #if self._useLockedAspect or self._useDefaultAspect:
                        diff = (axisR - axisL) / 2.0
                        mid = (self.axisR + self.axisL) / 2.0
                        self.axisL = mid - diff
                        self.axisR = mid + diff

                elif self.spectrumDisplay.stripArrangement == 'T':

                    # NOTE:ED - Tiled plots not fully implemented yet
                    pass

                else:
                    # currently ignore - warnings will be logged elsewhere
                    pass

                self._rescaleAllAxes()
                self._storeZoomHistory()

    @pyqtSlot(dict)
    def _glMouseMoved(self, aDict):
        if self.strip.isDeleted:
            return

        if aDict[GLNotifier.GLSOURCE] != self:

            mouseMovedDict = aDict[GLNotifier.GLMOUSEMOVEDDICT]

            if self._crosshairVisible:
                exactMatch = (self._preferences.matchAxisCode == AXIS_FULLATOMNAME)
                # indices = getAxisCodeMatchIndices(self._axisCodes[:2], mouseMovedDict[AXIS_ACTIVEAXES], exactMatch=exactMatch)
                #
                # if indices and len(indices) > 1:
                #     for n in range(2):
                #         if indices[n] is not None:
                #
                #             axis = mouseMovedDict[AXIS_ACTIVEAXES][indices[n]]
                #             self.cursorSource = CURSOR_SOURCE_OTHER
                #             self.cursorCoordinate[n] = mouseMovedDict[AXIS_FULLATOMNAME][axis]
                #
                #             # coordinates have already been flipped
                #             self.doubleCursorCoordinate[1 - n] = self.cursorCoordinate[n]
                #
                #         else:
                #             self.cursorSource = CURSOR_SOURCE_OTHER
                #             self.cursorCoordinate[n] = None
                #             self.doubleCursorCoordinate[1 - n] = None

                self.update(mode=PaintModes.PAINT_MOUSEONLY)

    @pyqtSlot(dict)
    def _glKeyEvent(self, aDict):
        """Process Key events from the application/popups and other strips
        :param aDict - dictionary containing event flags:
        """
        if self.strip.isDeleted:
            return

        if not self.globalGL:
            return

        self.glKeyPressEvent(aDict)

    @pyqtSlot(dict)
    def _glEvent(self, aDict):
        """Process events from the application/popups and other strips
        :param aDict - dictionary containing event flags:
        """
        if self.strip.isDeleted:
            return

        if not self.globalGL:
            return

        if aDict:
            if aDict[GLNotifier.GLSOURCE] != self:

                # check the params for actions and update the display
                triggers = aDict[GLNotifier.GLTRIGGERS]
                targets = aDict[GLNotifier.GLTARGETS]

                if triggers or targets:

                    if GLNotifier.GLRESCALE in triggers:
                        self._rescaleXAxis(update=False)

                    if GLNotifier.GLPREFERENCES in triggers:
                        self._preferencesUpdate()
                        self._rescaleXAxis(update=False)

                    if GLNotifier.GLPEAKLISTS in triggers:
                        for spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            for peakListView in spectrumView.peakListViews:
                                for peakList in targets:
                                    if peakList == peakListView.peakList:
                                        peakListView.buildSymbols = True
                                        peakListView.buildArrows = True
                        # self.buildPeakLists()

                    if GLNotifier.GLPEAKLISTLABELS in triggers:
                        for spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            for peakListView in spectrumView.peakListViews:
                                for peakList in targets:
                                    if peakList == peakListView.peakList:
                                        peakListView.buildLabels = True
                                        peakListView.buildArrows = True
                        # self.buildPeakListLabels()

                    if GLNotifier.GLMARKS in triggers:
                        self.buildMarks = True

                    if GLNotifier.GLHIGHLIGHTPEAKS in triggers:
                        self._GLPeaks.updateHighlightSymbols()

                    if GLNotifier.GLHIGHLIGHTMULTIPLETS in triggers:
                        self._GLMultiplets.updateHighlightSymbols()

                    if GLNotifier.GLHIGHLIGHTINTEGRALS in triggers:
                        self._GLIntegrals.updateHighlightSymbols()

                    if GLNotifier.GLALLCONTOURS in triggers:
                        self.buildAllContours()

                    if GLNotifier.GLALLPEAKS in triggers:
                        self._GLPeaks.updateAllSymbols()

                    if GLNotifier.GLALLMULTIPLETS in triggers:
                        self._GLMultiplets.updateAllSymbols()

                    if GLNotifier.GLANY in targets:
                        self._rescaleXAxis(update=False)

                    if GLNotifier.GLPEAKNOTIFY in targets:
                        self._GLPeaks.updateHighlightSymbols()

                    if GLNotifier.GLINTEGRALLISTS in triggers:
                        for spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            for integralListView in spectrumView.integralListViews:
                                for integralList in targets:
                                    if integralList == integralListView.integralList:
                                        integralListView.buildSymbols = True

                    if GLNotifier.GLINTEGRALLISTLABELS in triggers:
                        for spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            for integralListView in spectrumView.integralListViews:
                                for integralList in targets:
                                    if integralList == integralListView.integralList:
                                        integralListView.buildLabels = True

                    if GLNotifier.GLMULTIPLETLISTS in triggers:
                        for spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            for multipletListView in spectrumView.multipletListViews:
                                for multipletList in targets:
                                    if multipletList == multipletListView.multipletList:
                                        multipletListView.buildSymbols = True
                                        multipletListView.buildArrows = True

                    if GLNotifier.GLMULTIPLETLISTLABELS in triggers:
                        for spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            for multipletListView in spectrumView.multipletListViews:
                                for multipletList in targets:
                                    if multipletList == multipletListView.multipletList:
                                        multipletListView.buildLabels = True
                                        multipletListView.buildArrows = True

                    if GLNotifier.GLCLEARPHASING in triggers:
                        if self.spectrumDisplay == aDict[GLNotifier.GLSPECTRUMDISPLAY]:
                            self.clearStaticTraces()

                    if GLNotifier.GLADD1DPHASING in triggers:
                        if self.spectrumDisplay == aDict[GLNotifier.GLSPECTRUMDISPLAY]:
                            self.clearStaticTraces()
                            self.newTrace()

        # repaint
        self.update()

    def _renderCursorOnly(self):

        # NOTE:ED - use partialUpdate
        #           when the mouse is moving somewhere else then only render the mouse using XOR
        #           without clearing the screen
        #           normal paintGL should include GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        #           draw original mouse in Xor - OR replace vertical/horizontal columns as bitmap
        #           update mouse coordinates
        #            OR grab vertical/horizontal columns as bitmap
        #           draw new mouse in Xor

        self.makeCurrent()

        if self._crosshairVisible:

            drawList = self._glCursor

            vertices = []
            indices = []
            index = 0

            # map the cursor to the ratio coordinates - double cursor is flipped about the line x=y
            newCoords = self._scaleAxisToRatio(self.cursorCoordinate[0:2])

            if getCurrentMouseMode() == PICK and self.underMouse():

                x = self.deltaX * 8
                y = self.deltaY * 8

                vertices = [newCoords[0] - x, newCoords[1] - y,
                            newCoords[0] + x, newCoords[1] - y,
                            newCoords[0] + x, newCoords[1] - y,
                            newCoords[0] + x, newCoords[1] + y,
                            newCoords[0] + x, newCoords[1] + y,
                            newCoords[0] - x, newCoords[1] + y,
                            newCoords[0] - x, newCoords[1] + y,
                            newCoords[0] - x, newCoords[1] - y
                            ]
                indices = [0, 1, 2, 3, 4, 5, 6, 7]
                col = self.mousePickColour
                index = 8

            else:
                col = self.foreground

            drawList.vertices = np.array(vertices, dtype=np.float32)
            drawList.indices = np.array(indices, dtype=np.int32)
            drawList.numVertices = len(vertices) // 2
            drawList.colors = np.array(col * drawList.numVertices, dtype=np.float32)

            # build and draw the VBO
            drawList.defineIndexVBO()

            # GL.glDrawBuffer(GL.GL_FRONT)
            drawList.drawIndexVBO()

        self.doneCurrent()

    def _resetBoxes(self):
        """Reset/Hide the boxes
        """
        self._successiveClicks = None

    def _selectPeak(self, xPosition, yPosition, append=False):
        """(de-)Select first peak near cursor xPosition, yPosition
        if peak already was selected, de-select it
        """
        newPeaks = self._mouseInPeak(xPosition, yPosition)
        if append:
            peaks = set(self.current.peaks)
            self.current.peaks = list(peaks ^ set(newPeaks))  # symmetric difference
        else:
            self.current.peaks = newPeaks

    def _selectIntegral(self, xPosition, yPosition, append=False):
        """(de-)Select first integral near cursor xPosition, yPosition
        if integral already was selected, de-select it
        """
        newIntegrals = self._mouseInIntegral(xPosition, yPosition)
        if append:
            integrals = set(self.current.integrals)
            self.current.integrals = list(integrals ^ set(newIntegrals))  # symmetric difference
        else:
            self.current.integrals = newIntegrals

    def _selectMultiplet(self, xPosition, yPosition, append=False):
        """(de-)Select first multiplet near cursor xPosition, yPosition
        if multiplet already was selected, de-select it
        """
        newMultiplets = self._mouseInMultiplet(xPosition, yPosition)
        if append:
            multiplets = set(self.current.multiplets)
            self.current.multiplets = list(multiplets ^ set(newMultiplets))  # symmetric difference
        else:
            self.current.multiplets = newMultiplets

    def _pickAtMousePosition(self, event):
        """pick the peaks at the mouse position
        """
        event.accept()
        self._resetBoxes()

        cursorCoordinate = self.getCurrentCursorCoordinate()
        mousePosition = (cursorCoordinate[0], cursorCoordinate[1])
        ppmPositions = [mousePosition[0], mousePosition[1]]
        for orderedAxis in self._orderedAxes[2:]:
            ppmPositions.append(orderedAxis.position)

        self.strip.createPeak(ppmPositions)

    def _clearIntegralRegions(self):
        """Clear the integral regions
        """
        self._regions = []
        self._regionList.renderMode = GLRENDERMODE_REBUILD
        self._dragRegions = set()
        self.update()

    # @contextmanager
    def _mouseUnderMenu(self):
        """Context manager to set the menu status to active
        so that when the menu appears the live traces stay visible
        """
        self._menuActive = True
        try:
            yield
        finally:
            self._menuActive = False

    # @contextmanager
    def _disableCursorUpdating(self):
        """Context manager to set the menu status to active
        so that when the menu appears the live traces stay visible
        """
        self._disableCursorUpdate = True
        try:
            yield
        finally:
            self._disableCursorUpdate = False

    def getObjectsUnderMouse(self):
        """Return a list of objects under the mouse position as a dict
        dict is of the form: {object plural name: list, ...}
            e.g. {'peaks': []}
        Current objects returned are: peaks, integrals, multiplets
        :return: dict of objects
        """

        def _addObjects(objDict, attrName):
            """Add the selected objects to the dict
            """
            objSelected = (set(objs or []) & set(getattr(self.current, attrName, None) or []))
            if objSelected:
                objDict[attrName] = objs

        if self.strip.isDeleted:
            return {}
        if abs(self.axisL - self.axisR) < 1.0e-6 or abs(self.axisT - self.axisB) < 1.0e-6:
            return {}

        cursorPos = self.getMousePosition()
        xPosition = cursorPos[0]
        yPosition = cursorPos[1]
        objDict = {}

        # add objects to the dict
        objs = self._mouseInPeak(xPosition, yPosition, firstOnly=False)
        _addObjects(objDict, PEAKSELECT)

        objs = self._mouseInIntegral(xPosition, yPosition, firstOnly=False)
        _addObjects(objDict, INTEGRALSELECT)

        objs = self._mouseInMultiplet(xPosition, yPosition, firstOnly=False)
        _addObjects(objDict, MULTIPLETSELECT)

        # return the list of objects
        return objDict

    def _selectPeaksFromMultiplets(self, multiplets):
        peaks = set(self.current.peaks)
        for multiplet in multiplets:
            # add/remove the multiplet peaks
            newPeaks = multiplet.peaks
            self.current.peaks = list(peaks | set(newPeaks))  # symmetric difference

    def _selectMultipletPeaks(self, xPosition, yPosition):
        # get the list of multiplets under the mouse
        multiplets = self._mouseInMultiplet(xPosition, yPosition, firstOnly=True)

        peaks = set(self.current.peaks)
        for multiplet in multiplets:
            # add/remove the multiplet peaks
            newPeaks = multiplet.peaks
            self.current.peaks = list(peaks | set(newPeaks))  # symmetric difference

    def _mouseDoubleClickEvent(self, event: QtGui.QMouseEvent, axis=None):
        """handle the mouse click event
        """
        # get the mouse coordinates
        cursorCoordinate = self.getCurrentCursorCoordinate()
        xPosition = cursorCoordinate[0]  # self.mapSceneToView(event.pos()).x()
        yPosition = cursorCoordinate[1]  # self.mapSceneToView(event.pos()).y()

        if leftMouse(event):
            multiplets = self._mouseInMultiplet(xPosition, yPosition, firstOnly=True)

            if multiplets:
                # Left-doubleClick; select only peaks attached to multiplets
                self._resetBoxes()
                self.current.clearPeaks()
                self._selectPeaksFromMultiplets(multiplets)
                event.accept()

        elif controlLeftMouse(event):
            multiplets = self._mouseInMultiplet(xPosition, yPosition, firstOnly=True)

            if multiplets:
                # Control-left-doubleClick; (de-)select multiplet peaks and add/remove to selection
                self._resetBoxes()
                self._selectMultipletPeaks(xPosition, yPosition)
                event.accept()

    def _mouseClickEvent(self, event: QtGui.QMouseEvent, axis=None):
        """handle the mouse click event
        """
        # self.current.strip = self.strip
        cursorCoordinate = self.getCurrentCursorCoordinate()
        xPosition = cursorCoordinate[0]  # self.mapSceneToView(event.pos()).x()
        yPosition = cursorCoordinate[1]  # self.mapSceneToView(event.pos()).y()
        self.current.positions = [xPosition, yPosition]

        # This is the correct future style for cursorPosition handling
        self.current.cursorPosition = (xPosition, yPosition)

        if getCurrentMouseMode() == PICK and leftMouse(event):
            if self._validRegionPick:
                self._pickAtMousePosition(event)

        if controlShiftLeftMouse(event) or controlShiftRightMouse(event):
            if self._validRegionPick:
                # Control-Shift-left-click: pick peak
                self._pickAtMousePosition(event)

        elif controlLeftMouse(event):
            # Control-left-click; (de-)select peak and add/remove to selection
            event.accept()
            self._resetBoxes()
            self._selectMultiplet(xPosition, yPosition, append=True)
            self._selectPeak(xPosition, yPosition, append=True)
            self._selectIntegral(xPosition, yPosition, append=True)

        elif leftMouse(event):
            # Left-click; select peak/integral/multiplet, deselecting others
            event.accept()
            self._resetBoxes()
            # self.current.clearPeaks()
            # self.current.clearIntegrals()
            # self.current.clearMultiplets()

            self._selectMultiplet(xPosition, yPosition)
            self._selectPeak(xPosition, yPosition)
            self._selectIntegral(xPosition, yPosition)

        elif shiftRightMouse(event):
            # Two successive shift-right-clicks: define zoom-box
            event.accept()
            if self._successiveClicks is None:
                self._resetBoxes()
                self._successiveClicks = (cursorCoordinate[0], cursorCoordinate[1])
            else:

                if self._widthsChangedEnough((cursorCoordinate[0], cursorCoordinate[1]),
                                             (self._successiveClicks[0], self._successiveClicks[1]),
                                             3 * max(abs(self.pixelX),
                                                     abs(self.pixelY))):

                    if self.XDIRECTION < 0:
                        # need to stop float becoming a np.float64
                        self.axisL = float(max(self._startCoordinate[0], self._successiveClicks[0]))
                        self.axisR = float(min(self._startCoordinate[0], self._successiveClicks[0]))
                    else:
                        self.axisL = float(min(self._startCoordinate[0], self._successiveClicks[0]))
                        self.axisR = float(max(self._startCoordinate[0], self._successiveClicks[0]))

                    if self.YDIRECTION < 0:
                        self.axisB = float(max(self._startCoordinate[1], self._successiveClicks[1]))
                        self.axisT = float(min(self._startCoordinate[1], self._successiveClicks[1]))
                    else:
                        self.axisB = float(min(self._startCoordinate[1], self._successiveClicks[1]))
                        self.axisT = float(max(self._startCoordinate[1], self._successiveClicks[1]))

                    self._testAxisLimits(setLimits=True)
                    self._rescaleXAxis()

                self._resetBoxes()
                self._successiveClicks = None

        elif rightMouse(event) and axis is None:
            # right click on canvas, not the axes
            strip = self.strip
            menu = None
            event.accept()
            self._resetBoxes()

            mouseInAxis = self._mouseInAxis(event.pos())

            self._updateMouseEvent()
            self._raiseRightMouseMenu(event.screenPos(), menu, mouseInAxis, strip)

        elif controlRightMouse(event) and axis is None:
            # control-right-mouse click: reset the zoom
            event.accept()
            self._resetBoxes()
            self._resetAxisRange()
            self._rescaleXAxis(update=True)

        else:
            # reset and hide all for all other clicks
            self._resetBoxes()
            event.ignore()

        self.update()

    def _raiseRightMouseMenu(self, position, menu, mouseInAxis, strip):
        if mouseInAxis == GLDefs.MAINVIEW:

            # strip should handle the selection of correct menu
            selectedDict = self.getObjectsUnderMouse()
            if PEAKSELECT in selectedDict:

                # Search if the event is in a range of a selected peak.
                peaks = list(self.current.peaks)

                # SHOULDN'T be the GL's responsibility to handle the menu :|
                if self.is1D:
                    _menu = strip._contextMenus.get(PeakMenu)
                    if len(peaks) > 1:
                        _hidePeaksSingleActionItems(_menu)
                    else:
                        _setEnabledAllItems(_menu, True)

                # will only work for self.current.peak
                strip._addItemsToNavigateToPeakMenu(selectedDict[PEAKSELECT])
                strip._addItemsToMarkInPeakMenu(selectedDict[PEAKSELECT])

                strip.contextMenuMode = PeakMenu
                menu = strip._contextMenus.get(strip.contextMenuMode)
                strip._lastClickedObjects = selectedDict[PEAKSELECT]

            elif INTEGRALSELECT in selectedDict:
                strip.contextMenuMode = IntegralMenu
                menu = strip._contextMenus.get(strip.contextMenuMode)
                strip._lastClickedObjects = selectedDict[INTEGRALSELECT]

            elif MULTIPLETSELECT in selectedDict:
                _menu = strip._contextMenus.get(MultipletMenu)
                multiplets = list(self.current.multiplets)
                if len(multiplets) == 1:
                    peakMults = {mult for pk in list(self.current.peaks) for mult in pk.multiplets} - set(multiplets)
                    if peakMults:
                        _hideMultipletsSingleActionItems(_menu, strip)
                else:
                    _setEnabledAllItems(_menu, True)
                strip.contextMenuMode = MultipletMenu
                menu = strip._contextMenus.get(strip.contextMenuMode)
                strip._lastClickedObjects = selectedDict[MULTIPLETSELECT]

            strip._navigateToPeakMenuMain.menuAction().setVisible(False)  # created from stripMethodName
            strip._makeStripPlotItemMain.setVisible(False)
            strip._estimateVolumesItemMain.setVisible(False)
            strip._estimateVolumesItemSelected.setVisible(False)
            if PEAKSELECT not in selectedDict:
                _setEnabledAllItems(strip._selectedPeaksMenu, True if self.current.peaks else False)

                # keep arrange/reset items enabled
                for name in [_ARRANGELABELS, _RESETLABELS]:
                    if act := strip._selectedPeaksMenu.getActionByName(name):
                        act.setEnabled(True)

            # check other menu items before raising menus
            strip._addItemsToNavigateToCursorPosMenu()
            strip._addItemsToMarkInCursorPosMenu()

            # this isn't as nice as below, could be cleaned up a little
            strip.markAxesMenu.clear()
            strip._addItemsToMarkAxesMenuMainView()

            strip._addItemsToCopyAxisFromMenusMainView()
            if not self.is1D:
                strip._addItemsToMatchAxisCodesFromMenusMainView()
            strip._checkMenuItems()

        elif mouseInAxis in [GLDefs.BOTTOMAXIS, GLDefs.RIGHTAXIS, GLDefs.AXISCORNER]:
            strip.contextMenuMode = AxisMenu
            menu = strip._contextMenus.get(strip.contextMenuMode)

            # create a dynamic menu based on the available axisCodes
            menu.clear()
            strip._addItemsToMarkAxesMenuAxesView(mouseInAxis, menu)
            strip._addItemsToCopyAxisFromMenusAxes(mouseInAxis, menu, self.is1D)
        if menu is not None:
            strip.viewStripMenu = menu
        else:
            strip.viewStripMenu = self._getCanvasContextMenu()
        for _ in self._mouseUnderMenu():
            strip._raiseContextMenu(position=position)

    def _mouseInAxis(self, mousePos):
        h = self.h
        w = self.w

        # find the correct viewport
        if (self._drawRightAxis and self._drawBottomAxis):
            mw = [0, self.AXIS_MARGINBOTTOM, w - self.AXIS_MARGINRIGHT, h - 1]
            ba = [0, 0, w - self.AXIS_MARGINRIGHT, self.AXIS_MARGINBOTTOM - 1]
            ra = [w - self.AXIS_MARGINRIGHT, self.AXIS_MARGINBOTTOM, w, h]

        elif (self._drawBottomAxis):
            mw = [0, self.AXIS_MARGINBOTTOM, w, h - 1]
            ba = [0, 0, w, self.AXIS_MARGINBOTTOM - 1]
            ra = [w, self.AXIS_MARGINBOTTOM, w, h]

        elif (self._drawRightAxis):
            mw = [0, 0, w - self.AXIS_MARGINRIGHT, h - 1]
            ba = [0, 0, w - self.AXIS_MARGINRIGHT, 0]
            ra = [w - self.AXIS_MARGINRIGHT, 0, w, h]

        else:  # no axes visible
            mw = [0, 0, w, h]
            ba = [0, 0, w, 0]
            ra = [w, 0, w, h]

        mx = mousePos.x()
        my = self.height() - mousePos.y()

        if self.between(mx, mw[0], mw[2]) and self.between(my, mw[1], mw[3]):

            # if in the mainView
            return GLDefs.MAINVIEW

        elif self.between(mx, ba[0], ba[2]) and self.between(my, ba[1], ba[3]):

            # in the bottomAxisBar, so zoom in the X axis
            return GLDefs.BOTTOMAXIS

        elif self.between(mx, ra[0], ra[2]) and self.between(my, ra[1], ra[3]):

            # in the rightAxisBar, so zoom in the Y axis
            return GLDefs.RIGHTAXIS

        else:

            # must be in the corner
            return GLDefs.AXISCORNER

    def _getCanvasContextMenu(self):
        """Give a needed menu based on strip mode
        """
        strip = self.strip
        menu = strip._contextMenus.get(DefaultMenu)

        # set the checkboxes to the correct settings
        strip.toolbarAction.setChecked(strip.spectrumDisplay.spectrumUtilToolBar.isVisible())
        if hasattr(strip, 'crosshairAction'):
            strip.crosshairAction.setChecked(self._crosshairVisible)

        strip.gridAction.setChecked(self._gridVisible)
        if hasattr(strip, 'lastAxisOnlyCheckBox'):
            strip.lastAxisOnlyCheckBox.setChecked(strip.spectrumDisplay.lastAxisOnly)

        if not strip.spectrumDisplay.is1D:
            strip.sideBandsAction.setChecked(self._sideBandsVisible)

        if strip._isPhasingOn:
            menu = strip._contextMenus.get(PhasingMenu)

        return menu

    def _setContextMenu(self, menu):
        """Set a needed menu based on strip mode
        """
        self.strip.viewStripMenu = menu

    def _selectPeaksInRegion(self, xPositions, yPositions, zPositions):
        currentPeaks = set(self.current.peaks)

        peaks = set()
        originalxPositions = xPositions
        _data2Obj = self.strip.project._data2Obj
        pixX, pixY = self.strip._CcpnGLWidget.pixelX, self.strip._CcpnGLWidget.pixelY
        sgnX, sgnY = np.sign(pixX), np.sign(pixY)

        for spectrumView in self._ordering:  # strip.spectrumViews:
            if spectrumView.isDeleted:
                continue

            for peakListView in spectrumView.peakListViews:
                if not peakListView.isDisplayed or not spectrumView.isDisplayed:
                    continue

                peakList = peakListView.peakList
                if not isinstance(peakList, PeakList):  # it could be an IntegralList
                    continue

                if len(spectrumView.spectrum.axisCodes) == 1:
                    # should be sub-classed somewhere!
                    xOffset, yOffset = self._spectrumSettings[spectrumView].stackedMatrixOffset
                    xDim, yDim = self._spectrumSettings[spectrumView].dimensionIndices

                    y0 = self._startCoordinate[1]
                    y1 = self._endCoordinate[1]
                    y0, y1 = min(y0, y1), max(y0, y1)
                    # add offsets for when in stack-mode
                    y0, y1 = np.array([y0, y1]) - yOffset
                    xPositions = np.array(originalxPositions) - xOffset
                    # xAxis = 0

                    # for peak in peakList.peaks:
                    if labelling := self._GLPeaks._GLLabels.get(peakListView):
                        for drawList in labelling.stringList:
                            try:
                                peak = drawList.stringObject
                                pView = peak.getPeakView(peakListView)
                                if xDim:  # need to decide on a consistent way of doing this flip :|
                                    px, py = float(peak.height), float(peak.position[0])
                                else:
                                    px, py = float(peak.position[0]), float(peak.height)
                                tx, ty = pView.textOffset
                                if not tx and not ty:
                                    # TODO: ED - nasty :|
                                    # pixels
                                    tx, ty = self._symbolSize, self._symbolSize
                                    # ppm
                                    # tx, ty = self.symbolX, self.symbolY

                                # pixels
                                # mx, my = px + (tx + drawList.width / 2) * pixX, py + (ty + drawList.height / 2) * pixY
                                # ppms
                                mx, my = px + tx * sgnX + drawList.width * pixX / 2, py + ty * sgnY + drawList.height * pixY / 2

                                # height = peak.height  # * scale # TBD: is the scale already taken into account in peak.height???
                                if (xPositions[0] < px < xPositions[1] and y0 < py < y1) or \
                                        (xPositions[0] < mx < xPositions[1] and y0 < my < y1):
                                    peaks.add(peak)

                            except Exception as es:
                                # NOTE:ED - skip for now
                                print(f'mouse in label error {es}')
                                continue

                else:
                    if labelling := self._GLPeaks._GLLabels.get(peakListView):
                        spectrumIndices = spectrumView.dimensionIndices
                        xAxis = spectrumIndices[0]
                        yAxis = spectrumIndices[1]

                        # for peak in peakList.peaks:
                        for drawList in labelling.stringList:

                            try:
                                peak = drawList.stringObject
                                # NOTE:ED - need to speed this up
                                pView = peak.getPeakView(peakListView)
                                _pos = peak.position
                                px, py = float(_pos[xAxis]), float(_pos[yAxis])
                                tx, ty = pView.textOffset
                                if not tx and not ty:
                                    # pixels
                                    tx, ty = self._symbolSize, self._symbolSize
                                    # ppm
                                    # tx, ty = self.symbolX, self.symbolY

                                # pixels
                                # mx, my = px + (tx + drawList.width / 2) * pixX, py + (ty + drawList.height / 2) * pixY
                                # ppms
                                mx, my = px + tx * sgnX + drawList.width * pixX / 2, py + ty * sgnY + drawList.height * pixY / 2

                                if (xPositions[0] < px < xPositions[1] and yPositions[0] < py < yPositions[1]) or \
                                        (xPositions[0] < mx < xPositions[1] and yPositions[0] < my < yPositions[1]):
                                    if len(peak.axisCodes) > 2 and zPositions is not None:
                                        # zAxis = spectrumIndices[2]

                                        # within the XY bounds so check whether inPlane
                                        _isInPlane, _isInFlankingPlane, planeIndex, fade = self._GLPeaks.objIsInVisiblePlanes(
                                                spectrumView, peak)

                                        # if zPositions[0] < float(peak.position[zAxis]) < zPositions[1]:
                                        if _isInPlane or _isInFlankingPlane:
                                            peaks.add(peak)
                                    else:
                                        peaks.add(peak)

                            except Exception:
                                # NOTE:ED - skip for now
                                continue

        self.current.peaks = list(currentPeaks | peaks)

    def _selectMultipletsInRegion(self, xPositions, yPositions, zPositions):
        currentMultiplets = set(self.current.multiplets)

        multiplets = set()
        for spectrumView in self._ordering:  # strip.spectrumViews:

            if spectrumView.isDeleted:
                continue

            for multipletListView in spectrumView.multipletListViews:
                if not multipletListView.isDisplayed or not spectrumView.isDisplayed:
                    continue

                multipletList = multipletListView.multipletList

                if len(spectrumView.spectrum.axisCodes) == 1:

                    y0 = self._startCoordinate[1]
                    y1 = self._endCoordinate[1]
                    y0, y1 = min(y0, y1), max(y0, y1)
                    xAxis = 0

                    for multiplet in multipletList.multiplets:
                        if not multiplet.position:
                            continue

                        height = multiplet.height
                        if xPositions[0] < float(multiplet.position[xAxis]) < xPositions[1] and y0 < height < y1:
                            multiplets.add(multiplet)

                else:
                    spectrumIndices = spectrumView.dimensionIndices
                    xAxis = spectrumIndices[0]
                    yAxis = spectrumIndices[1]

                    for multiplet in multipletList.multiplets:
                        if not multiplet.position:
                            continue

                        if (xPositions[0] < float(multiplet.position[xAxis]) < xPositions[1]
                                and yPositions[0] < float(multiplet.position[yAxis]) < yPositions[1]):
                            if len(multiplet.axisCodes) > 2 and zPositions is not None:
                                zAxis = spectrumIndices[2]

                                # within the XY bounds so check whether inPlane
                                _isInPlane, _isInFlankingPlane, planeIndex, fade = self._GLPeaks.objIsInVisiblePlanes(
                                        spectrumView, multiplet)

                                # if zPositions[0] < float(multiplet.position[zAxis]) < zPositions[1]:
                                if _isInPlane or _isInFlankingPlane:
                                    multiplets.add(multiplet)
                            else:
                                multiplets.add(multiplet)

        self.current.multiplets = list(currentMultiplets | multiplets)

    def _mouseDragEvent(self, event: QtGui.QMouseEvent, axis=None):
        cursorCoordinate = self.getCurrentCursorCoordinate()
        if controlShiftLeftMouse(event) or controlShiftRightMouse(event):
            # Control(Cmd)+shift+left drag: Peak-picking
            event.accept()

            self._resetBoxes()
            selectedRegion = [tuple([round(self._startCoordinate[0], 3), round(self._endCoordinate[0], 3)]),
                              tuple([round(self._startCoordinate[1], 3), round(self._endCoordinate[1], 3)])
                              ]

            if self._validRegionPick:

                # only pick if the region is inside the bounds
                for axis in self._orderedAxes[2:]:
                    if axis.width > 0.05:
                        # round the value for prettier reporting, but only for large enough values
                        # as otherwise it might go wrong with time axes
                        region = tuple([round(val, 3) for val in axis.region])
                    else:
                        region = tuple(axis.region)
                    selectedRegion.append(region)

                # selectedRegion is tuple((xL, xR), (yB, yT), ...) - from display
                # ... is other Nd axes

                self.strip.pickPeaks(selectedRegion)

        elif controlLeftMouse(event):
            # Control(Cmd)+left drag: selects peaks - purple box
            event.accept()

            self._resetBoxes()
            xPositions = sorted([self._startCoordinate[0], self._endCoordinate[0]])
            yPositions = sorted([self._startCoordinate[1], self._endCoordinate[1]])

            if len(self._orderedAxes) > 2:
                zPositions = self._orderedAxes[2].region
            else:
                zPositions = None

            self._selectMultipletsInRegion(xPositions, yPositions, zPositions)
            self._selectPeaksInRegion(xPositions, yPositions, zPositions)

        elif middleMouse(event) or rightMouse(event):
            # middle drag: moves selected peaks
            event.accept()

            if self._startMiddleDrag:
                peaks = list(self.current.peaks)
                multiplets = list(self.current.multiplets)
                if not (peaks or multiplets):
                    return

                deltaPosition = [cursorCoordinate[0] - self._startCoordinate[0],
                                 cursorCoordinate[1] - self._startCoordinate[1]]

                if self._mouseInLabel:
                    # # NOTE:ED - not very nice again, needs cleaning up
                    # plvs = [plv._wrappedData.peakListView for spectrumView in self.strip.spectrumViews
                    #             for plv in spectrumView.peakListViews
                    #                 if spectrumView.isDisplayed and plv.isDisplayed]
                    # pvs = [pv for pk in peaks for pv in pk.peakViews if pv._wrappedData.peakListView in plvs]

                    pvs = {pv for spectrumView in self.strip.spectrumViews
                           for plv in spectrumView.peakListViews if spectrumView.isDisplayed and plv.isDisplayed
                           for pv in plv.peakViews if pv.peak in peaks}
                    mltvs = {mv for spectrumView in self.strip.spectrumViews
                             for mlv in spectrumView.multipletListViews if spectrumView.isDisplayed and mlv.isDisplayed
                             for mv in mlv.multipletViews if mv.multiplet in multiplets}

                    with undoBlockWithoutSideBar():
                        for pv in pvs:
                            pos = list(pv.textOffset)
                            # pixels
                            # pos[0] += (deltaPosition[0] / self.pixelX)
                            # pos[1] += (deltaPosition[1] / self.pixelY)
                            # ppms
                            pos[0] += deltaPosition[0] * np.sign(self.pixelX)
                            pos[1] += deltaPosition[1] * np.sign(self.pixelY)
                            pv.textOffset = pos

                        for mv in mltvs:
                            pos = list(mv.textOffset)
                            # pixels
                            # pos[0] += (deltaPosition[0] / self.pixelX)
                            # pos[1] += (deltaPosition[1] / self.pixelY)
                            # ppms
                            pos[0] += deltaPosition[0] * np.sign(self.pixelX)
                            pos[1] += deltaPosition[1] * np.sign(self.pixelY)
                            mv.textOffset = pos

                else:
                    for peak in peaks:
                        peak.startPosition = peak.position

                    with undoBlockWithoutSideBar():
                        for peak in peaks:
                            self._movePeak(peak, deltaPosition)

                    self.current.peaks = peaks

        elif shiftLeftMouse(event):
            # zoom into the region - yellow box
            if self.XDIRECTION < 0:
                # need to stop float becoming a np.float64
                self.axisL = float(max(self._startCoordinate[0], self._endCoordinate[0]))
                self.axisR = float(min(self._startCoordinate[0], self._endCoordinate[0]))
            else:
                self.axisL = float(min(self._startCoordinate[0], self._endCoordinate[0]))
                self.axisR = float(max(self._startCoordinate[0], self._endCoordinate[0]))

            if self.YDIRECTION < 0:
                self.axisB = float(max(self._startCoordinate[1], self._endCoordinate[1]))
                self.axisT = float(min(self._startCoordinate[1], self._endCoordinate[1]))
            else:
                self.axisB = float(min(self._startCoordinate[1], self._endCoordinate[1]))
                self.axisT = float(max(self._startCoordinate[1], self._endCoordinate[1]))

            self._testAxisLimits(setLimits=True)
            self._resetBoxes()
            self.emitAllAxesChanged(allStrips=True)

            # this also rescales the peaks
            self._rescaleXAxis()

        elif shiftMiddleMouse(event) or shiftRightMouse(event):
            pass

        else:
            VALUES = 'values'

            if self._dragValues:
                with undoStackBlocking() as addUndoItem:
                    for obj, (preValues, postValues) in self._dragValues.items():

                        if obj._object and not obj._object.isDeleted:
                            # set the values and add item to the undo-stack
                            obj.values = postValues

                            addUndoItem(undo=partial(setattr, obj, VALUES, preValues),
                                        redo=partial(setattr, obj, VALUES, postValues), )
                        if hasattr(obj, 'editingFinished'):  #fire callback when drag is finished
                            _d = {VALUES: getattr(obj, VALUES), 'obj': obj}
                            obj.editingFinished.emit(_d)

            self._dragValues = {}

            event.ignore()

        self.update()

    def exportToPDF(self, filename='default.pdf', params=None):
        return GLExporter(self, self.strip, filename, params)

    def exportToSVG(self, filename='default.svg', params=None):
        return GLExporter(self, self.strip, filename, params)

    def exportToPNG(self, filename='default.png', params=None):
        return GLExporter(self, self.strip, filename, params)

    def exportToPS(self, filename='default.ps', params=None):
        return GLExporter(self, self.strip, filename, params)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# need to use the class below to make everything more generic
GLOptions = {
    'opaque'     : {GL.GL_DEPTH_TEST: True,
                    GL.GL_BLEND     : False,
                    GL.GL_ALPHA_TEST: False,
                    GL.GL_CULL_FACE : False,
                    },
    'translucent': {GL.GL_DEPTH_TEST: True,
                    GL.GL_BLEND     : True,
                    GL.GL_ALPHA_TEST: False,
                    GL.GL_CULL_FACE : False,
                    'glBlendFunc'   : (GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA),
                    },
    'additive'   : {GL.GL_DEPTH_TEST: False,
                    GL.GL_BLEND     : True,
                    GL.GL_ALPHA_TEST: False,
                    GL.GL_CULL_FACE : False,
                    'glBlendFunc'   : (GL.GL_SRC_ALPHA, GL.GL_ONE),
                    },
    }


class CcpnTransform3D(QtGui.QMatrix4x4):
    """
    Extension of QMatrix4x4 with some helpful methods added.
    """

    def __init__(self, *args):
        QtGui.QMatrix4x4.__init__(self, *args)

    def matrix(self, nd=3):
        if nd == 3:
            return np.array(self.copyDataTo()).reshape(4, 4)
        elif nd == 2:
            m = np.array(self.copyDataTo()).reshape(4, 4)
            m[2] = m[3]
            m[:, 2] = m[:, 3]
            return m[:3, :3]
        else:
            raise Exception("Argument 'nd' must be 2 or 3")

    def map(self, obj):
        """Extends QMatrix4x4.map() to allow mapping (3, ...) arrays of coordinates
        """
        if isinstance(obj, np.ndarray) and obj.ndim >= 2 and obj.shape[0] in (2, 3):
            return fn.transformCoordinates(self, obj)
        else:
            return QtGui.QMatrix4x4.map(self, obj)

    def inverted(self):
        inv, b = QtGui.QMatrix4x4.inverted(self)
        return CcpnTransform3D(inv), b


class CcpnGLItem():
    _nextId = 0

    def __init__(self, parentItem=None):
        self._id = CcpnGLItem._nextId
        CcpnGLItem._nextId += 1

        self.strip = None
        # self._view = None
        self._children = set()
        self._transform = CcpnTransform3D()
        self._visible = True
        # self.setParentItem(parentItem)
        # self.setDepthValue(0)
        self._glOpts = {}


vertex_data = np.array([0.75, 0.75, 0.0,
                        0.75, -0.75, 0.0,
                        -0.75, -0.75, 0.0], dtype=np.float32)

color_data = np.array([1, 0, 0,
                       0, 1, 0,
                       0, 0, 1], dtype=np.float32)
