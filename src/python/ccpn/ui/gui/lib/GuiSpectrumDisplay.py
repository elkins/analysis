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
__dateModified__ = "$dateModified: 2024-08-23 19:25:20 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
from functools import partial
from copy import deepcopy
from contextlib import contextmanager
from typing import Tuple, Sequence

from ccpn.core.Peak import Peak
from ccpn.core.PeakList import PeakList
from ccpn.core.Spectrum import Spectrum
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.core.Sample import Sample
from ccpn.core.Substance import Substance
from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.NmrChain import NmrChain
from ccpn.core.lib.SpectrumLib import DIMENSION_TIME, DIMENSION_SAMPLED
from ccpn.ui._implementation.SpectrumDisplay import SpectrumDisplay

from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.lib.AssignmentLib import _assignNmrAtomsToPeaks, _assignNmrResiduesToPeaks

from ccpn.ui.gui.widgets.ToolBar import ToolBar
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.widgets.PhasingFrame import PhasingFrame
from ccpn.ui.gui.widgets.SpectrumToolBar import SpectrumToolBar
from ccpn.ui.gui.widgets.SpectrumGroupToolBar import SpectrumGroupToolBar
from ccpn.ui.gui.widgets.ScrollArea import ScrollArea, SpectrumDisplayScrollArea
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Font import setWidgetFont, getFontHeight
from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier
from ccpn.ui.gui.lib.GuiStrip import GuiStrip, STRIP_MINIMUMWIDTH, STRIP_MINIMUMHEIGHT

from ccpn.ui.gui.widgets.GLAxis import GuiNdWidgetAxis, Gui1dWidgetAxis
from ccpn.ui.gui.widgets.SpectrumGroupToolBar import _spectrumGroupViewHasChanged
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import PEAKSELECT, MULTIPLETSELECT, CcpnGLWidget, GLNotifier
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import AXISXUNITS, AXISYUNITS, \
    SYMBOLTYPE, ANNOTATIONTYPE, SYMBOLSIZE, SYMBOLTHICKNESS, AXISASPECTRATIOS, AXISASPECTRATIOMODE, \
    ALIASENABLED, ALIASSHADE, ALIASLABELSENABLED, CONTOURTHICKNESS, \
    PEAKLABELSENABLED, MULTIPLETLABELSENABLED, MULTIPLETTYPE, MULTIPLETANNOTATIONTYPE, PEAKSYMBOLSENABLED, PEAKARROWSENABLED, MULTIPLETSYMBOLSENABLED, MULTIPLETARROWSENABLED, ARROWTYPES, ARROWSIZE, ARROWMINIMUM
from ccpn.ui.gui.lib.GuiSpectrumView import _spectrumViewHasChanged
from ccpn.util.Constants import AXISUNITS
from ccpn.util.Logging import getLogger
from ccpn.util import Colour

from ccpn.ui._implementation.PeakListView import PeakListView
from ccpn.ui._implementation.IntegralListView import IntegralListView
from ccpn.ui._implementation.MultipletListView import MultipletListView
from ccpn.ui.gui.widgets.SettingsWidgets import SpectrumDisplaySettings
from ccpn.ui._implementation.SpectrumView import SpectrumView
from ccpn.core.lib.ContextManagers import undoStackBlocking, notificationBlanking, \
    BlankedPartial, ccpNmrV3CoreSetter, notificationEchoBlocking, undoBlockWithoutSideBar, \
    waypointBlocking
from ccpn.util.decorators import logCommand
from ccpn.util.Common import makeIterableList
from ccpn.core.lib import Undo
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.ui.gui.guiSettings import ZPlaneNavigationModes


STRIP_SPACING = 5
AXIS_WIDTH = 30

STRIPDIRECTIONS = ['Y', 'X', 'T']

MAXTILEBOUND = 65536
INCLUDE_AXIS_WIDGET = True


# GST All this complication is added because the scroll frame appears to have a lower margin added by some part of Qt
#     that we can't control in PyQt. Specifically even if you override setContentsMargins on ScrollArea it is never
#     called but at the same time ScrollArea gets a lower contents margin of 1 pixel that we didn't ask for... ;-(
def styleSheetPredicate(target):
    children = [child for child in target.children() if isinstance(child, QtWidgets.QWidget)]

    return len(children) < 2


def styleSheetMutator(styleSheetTemplate, predicate, clazz):
    if predicate:
        styleSheet = styleSheetTemplate % (clazz.__class__.__name__, '')
    else:
        styleSheet = styleSheetTemplate % (clazz.__class__.__name__, 'background-color: #191919;')

    return styleSheet


class ScrollAreaWithPredicateStylesheet(ScrollArea):

    def __init__(self, styleSheetTemplate, predicate, mutator, *args, **kwds):
        self.styleSheetTemplate = styleSheetTemplate
        self.predicate = predicate
        self.mutator = mutator
        super().__init__(*args, **kwds)

    def checkPredicate(self):
        return self.predicate(self)

    def modifyStyleSheet(self, predicate):
        self.setStyleSheet(self.mutator(self.styleSheetTemplate, predicate, self))

    def resizeEvent(self, e):
        self.modifyStyleSheet(self.checkPredicate())
        return super().resizeEvent(e)


#=========================================================================================
# GuiSpectrumDisplay
#=========================================================================================

class GuiSpectrumDisplay(CcpnModule):
    """
    Main spectrum display Module object.

    This module inherits the following attributes from the SpectrumDisplay wrapper class:

    title             Name of spectrumDisplay;
                        :return <str>
    stripDirection    Strip axis direction
                        :return <str>:('X', 'Y', None) - None only for non-strip plots
    stripCount        Number of strips
                        :return <str>.
    comment           Free-form text comment
                        comment = <str>
                        :return <str>
    axisCodes         Fixed string Axis codes in original display order
                        :return <tuple>:(X, Y, Z1, Z2, ...)
    axisOrder         String Axis codes in display order, determine axis display order
                        axisOrder = <sequence>:(X, Y, Z1, Z2, ...)
                        :return <tuple>:(X, Y, Z1, Z2, ...)
    is1D              True if this is a 1D display
                        :return <bool>
    window            Gui window showing SpectrumDisplay
                        window = <Window>
                        :return <Window>
    nmrResidue        NmrResidue attached to SpectrumDisplay
                        nmrResidue = <NmrResidue>
                        :return <NmrResidue>
    positions         Axis centre positions, in display order
                        positions = <Tuple>
                        :return <Tuple>
    widths            Axis display widths, in display order
                        widths = <Tuple>
                        :return <Tuple>
    units             Axis units, in display order
                        :return <Tuple>

    resetAxisOrder    Reset display to original axis order
    findAxis          Find axis
                        findAxis(axisCode)
                          :param axisCode
                          :return axis
    """

    MAXPEAKLABELTYPES = 0
    MAXPEAKSYMBOLTYPES = 0
    MAXMULTIPLETLABELTYPES = 0
    MAXMULTIPLETSYMBOLTYPES = 0
    MAXARROWSYMBOLTYPES = 0

    # Sub-classed in the 1d/nD implementations
    # NB: 'self' is added to the callback in _fillToolbar using partial
    _toolbarItems = []

    # override in specific module implementations
    includeSettingsWidget = True
    maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    settingsPosition = 'left'
    settingsMinimumSizes = (250, 50)
    _allowRename = True

    # internal namespace
    _ISGROUPED = 'isGrouped'
    _SPECTRUMGROUPS = 'groupList'
    _STRIPARRANGEMENT = 'stripArrangement'
    _ZPLANENAVIGATIONMODE = 'zPlaneNavigationMode'
    _RESTORESETTINGS = '_restoreSettings'
    _WIDGETSSTATE = 'widgets'
    _PROPERTIESSTATE = 'properties'
    _GRIDVISIBLE = 'gridVisible'
    _CROSSHAIRVISIBLE = 'crosshairVisible'
    _SIDEBANDSVISIBLE = 'sideBandsVisible'
    _SHOWSPECTRAONPHASING = 'showSpectraOnPhasing'
    _SPECTRUMBORDERSVISIBLE = '_spectrumBordersVisible'

    def __init__(self, mainWindow, useScrollArea=False):
        """
        Initialise the Gui spectrum display object

        :param mainWindow: MainWindow instance
        :param useScrollArea: Having a scrolled widget containing OpenGL and PyQtGraph widgets does not seem to work.
                              The leftmost strip is full of random garbage if it's not completely visible.
                              So for now add option below to have it turned off (False) or on (True).
        """
        if self.MAXPEAKLABELTYPES == 0:
            raise RuntimeError(f'MAXPEAKLABELTYPES == 0: cannot initialise')

        moduleTitle = str(self.id)  # the name that appears on the GUI Module
        getLogger().debug('GuiSpectrumDisplay.__init__>> mainWindow %s; name: %s' % (mainWindow, moduleTitle))
        super(GuiSpectrumDisplay, self).__init__(mainWindow=mainWindow, name=moduleTitle,
                                                 size=(1100, 1300), autoOrientation=False
                                                 )
        self.mainWindow = mainWindow
        self.application = mainWindow.application
        # derive current from application
        self.current = mainWindow.application.current
        # cannot set self.project because self is a wrapper object
        # self.project = mainWindow.application.project

        # self.mainWidget will be the parent of all the subsequent widgets
        self.qtParent = self.mainWidget

        # set up the widgets
        self._setWidgets(mainWindow, useScrollArea)

        # populate the widgets
        self._populateWidgets()

        # self.stripFrame.setAcceptDrops(True)
        self._spectrumDisplaySettings.stripArrangementChanged.connect(self._stripDirectionChangedInSettings)
        self._spectrumDisplaySettings.zPlaneNavigationModeChanged.connect(self._zPlaneNavigationModeChangedInSettings)

        # notifier to respond to items being dropped onto the spectrumDisplay
        self.setAcceptDrops(True)
        self._droppedNotifier = self.setGuiNotifier(self, [GuiNotifier.DROPEVENT], [DropBase.URLS, DropBase.PIDS],
                                                    self._processDroppedItems)

        # GWV: This assures that a 'hoverbar' is visible over the strip when dragging
        # the module to another location
        self.hoverEvent = self._hoverEvent

        self._phasingTraceScale = 1.0e-7
        self.stripScaleFactor = 1.0

        self._registerNotifiers()

        self._fillToolBar()

        #TODO: have SpectrumToolbar own and maintain this
        self.spectrumActionDict = {}  # apiDataSource --> toolbar action (i.e. button); used in SpectrumToolBar

        # self.isGrouped = False
        self.spectrumActionDict = {}
        self.activePeakItemDict = {}  # maps peakListView to apiPeak to peakItem for peaks which are being displayed
        # cannot use (wrapper) peak as key because project._data2Obj dict invalidates mapping before deleted callback is called
        # TBD: this might change so that we can use wrapper peak (GWV:NONO!)  (which would make nicer code in showPeaks and deletedPeak below)
        # self.inactivePeakItems = set() # contains unused peakItems
        self.inactivePeakItemDict = {}  # maps peakListView to apiPeak to set of peaks which are not being displayed

        self._spectrumUtilActions = {}  # Filled by _fillToolBar

    def _fillToolBar(self):
        """
        Adds specific icons for 1d spectra to the spectrum utility toolbar.
        """
        tb = self.spectrumUtilToolBar
        self._spectrumUtilActions = {}

        # create the actions from the lists
        for aName, icon, tooltip, active, callback in self._toolbarItems:
            action = tb.addAction(tooltip, partial(callback, self))
            if icon is not None:
                ic = Icon(icon)
                action.setIcon(ic)
            self._spectrumUtilActions[aName] = action

    def _setWidgets(self, mainWindow, useScrollArea):
        """Set the widgets for the spectrumDisplay
        """
        # get the settings from preferences
        _general = self.application.preferences.general

        xAxisUnits = yAxisUnits = 0
        # create settings widget
        if self.is1D:
            _yTexts = ['']
            _yAx = _general.yAxisUnits
            _showY = False
        else:
            _yTexts = AXISUNITS
            _yAx = yAxisUnits
            _showY = True
        self._setDisplaySettings(_general, _showY, _yAx, _yTexts, xAxisUnits)

        self._spectrumDisplaySettings.settingsChanged.connect(self._settingsChanged)
        self.settingsWidget.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        # respond to values changed in the containing spectrumDisplay settings widget
        self._spectrumDisplaySettings.stripArrangementChanged.connect(self._stripDirectionChangedInSettings)
        self._spectrumDisplaySettings.zPlaneNavigationModeChanged.connect(self._zPlaneNavigationModeChangedInSettings)

        spectrumRow = 1
        toolBarRow = 0
        stripRow = 2
        axisRow = 3
        phasingRow = 4
        _spacing = 4
        _styleSheet = 'QToolBar { spacing: 2px; padding: 0px; }'
        # give some spacing between buttons so that can raise a general context menu for toolbar (not the actions).

        _iconSize = max(getFontHeight(size='VLARGE') or 30, 30)
        # TOOLBAR_HEIGHT = _iconSize + _spacing
        self.toolBarFrame = Frame(parent=self.qtParent, grid=(spectrumRow, 0), gridSpan=(1, 7), setLayout=True,
                                  hPolicy='preferred', hAlign='left', showBorder=False,
                                  spacing=(_spacing, _spacing), margins=(_spacing, _spacing, _spacing, _spacing))
        # Utilities Toolbar; filled in Nd/1d classes
        self.spectrumUtilToolBar = ToolBar(parent=self.toolBarFrame, iconSizes=(_iconSize, _iconSize),
                                           grid=(0, 0), hPolicy='preferred', hAlign='left')
        # spectrum toolbar - holds spectrum icons for spectrumDisplay
        self.spectrumToolBar = SpectrumToolBar(parent=self.toolBarFrame, widget=self,
                                               grid=(1, 0), hPolicy='preferred', hAlign='left')
        # spectrumGroupsToolBar - holds spectrumGroup icons, slightly different behaviour
        self.spectrumGroupToolBar = SpectrumGroupToolBar(parent=self.toolBarFrame, spectrumDisplay=self,
                                                         grid=(2, 0), hPolicy='preferred', hAlign='left')

        self.spectrumGroupToolBar.hide()
        self.spectrumUtilToolBar.setStyleSheet(_styleSheet)
        self.spectrumToolBar.setStyleSheet(_styleSheet)
        self.spectrumGroupToolBar.setStyleSheet(_styleSheet)
        if self.application.preferences.general.showToolbar:
            self.spectrumUtilToolBar.show()
        else:
            self.spectrumUtilToolBar.hide()
        self.stripFrame = Frame(setLayout=True, showBorder=False, spacing=(5, 0), stretch=(1, 1), margins=(0, 0, 0, 0),
                                acceptDrops=True)
        if useScrollArea:
            # scroll area for strips
            # This took a lot of sorting-out; better leave as is or test thoroughly
            # self._stripFrameScrollArea = ScrollAreaWithPredicateStylesheet(parent=self.qtParent,
            self._stripFrameScrollArea = SpectrumDisplayScrollArea(parent=self.qtParent,
                                                                   # styleSheetTemplate = frameStyleSheetTemplate,
                                                                   # predicate=styleSheetPredicate, mutator=styleSheetMutator,
                                                                   setLayout=True, acceptDrops=False,
                                                                   scrollBarPolicies=('asNeeded', 'never'),
                                                                   minimumSizes=(STRIP_MINIMUMWIDTH, STRIP_MINIMUMHEIGHT),
                                                                   spectrumDisplay=self,
                                                                   cornerWidget=True)  # not self.is1D)
            self._stripFrameScrollArea.setWidget(self.stripFrame)
            self._stripFrameScrollArea.setWidgetResizable(True)
            self.qtParent.getLayout().addWidget(self._stripFrameScrollArea, stripRow, 0, 1, 7)
            self._stripFrameScrollArea.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                                     QtWidgets.QSizePolicy.Expanding)
            self.stripFrame.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                                          QtWidgets.QSizePolicy.Expanding)

        else:
            self._stripFrameScrollArea = None
            self.qtParent.getLayout().addWidget(self.stripFrame, stripRow, 0, 1, 7)
            # self.stripFrame.setStyleSheet(frameStyleSheetTemplate % ('Frame', ''))

        if INCLUDE_AXIS_WIDGET:
            # NOTE:ED - testing new axis widget - required actually adding tiling
            if self.is1D:
                self._rightGLAxis = Gui1dWidgetAxis(self._stripFrameScrollArea, spectrumDisplay=self, mainWindow=self.mainWindow,
                                                    drawRightAxis=True, drawBottomAxis=False,
                                                    fullHeightRightAxis=False, fullWidthBottomAxis=False)

            else:
                self._rightGLAxis = GuiNdWidgetAxis(self._stripFrameScrollArea, spectrumDisplay=self, mainWindow=self.mainWindow,
                                                    drawRightAxis=True, drawBottomAxis=False,
                                                    fullHeightRightAxis=False, fullWidthBottomAxis=False)

            self._rightGLAxis.tilePosition = (0, -1)
            self._rightGLAxis.setAxisType(1)
            self._rightGLAxis.show()

            # NOTE:ED - testing new axis widget - required actually adding tiling
            if self.is1D:
                self._bottomGLAxis = Gui1dWidgetAxis(self._stripFrameScrollArea, spectrumDisplay=self, mainWindow=self.mainWindow,
                                                     drawRightAxis=False, drawBottomAxis=True,
                                                     fullHeightRightAxis=False, fullWidthBottomAxis=False
                                                     )

            else:
                self._bottomGLAxis = GuiNdWidgetAxis(self._stripFrameScrollArea, spectrumDisplay=self, mainWindow=self.mainWindow,
                                                     drawRightAxis=False, drawBottomAxis=True,
                                                     fullHeightRightAxis=False, fullWidthBottomAxis=False)

            self._bottomGLAxis.tilePosition = (-1, 0)
            self._bottomGLAxis.setAxisType(0)
            self._bottomGLAxis.hide()

        self.qtParent.getLayout().setContentsMargins(1, 0, 1, 0)
        self.qtParent.getLayout().setSpacing(0)
        self.lastAxisOnly = mainWindow.application.preferences.general.lastAxisOnly

        # GWV moved post init
        # if not self.is1D:
        #     self.setVisibleAxes()

        from ccpn.ui.gui.widgets.PlaneToolbar import ZPlaneToolbar

        self._stripToolBarWidget = Frame(parent=self.qtParent, setLayout=True, grid=(axisRow, 0), gridSpan=(1, 7),
                                         hAlign='c', hPolicy='ignored')
        self.zPlaneFrame = ZPlaneToolbar(self._stripToolBarWidget, mainWindow, self, showHeader=True, showLabels=True,
                                         grid=(0, 0), gridSpan=(1, 1), margins=(2, 2, 2, 2), hPolicy='preferred')
        if len(self.axisCodes) < 3:
            self._stripToolBarWidget.setVisible(False)
        includeDirection = not self.is1D
        self.phasingFrame = PhasingFrame(parent=self.qtParent,
                                         showBorder=False,
                                         includeDirection=includeDirection,
                                         callback=self._updatePhasing,
                                         returnCallback=self._updatePivot,
                                         directionCallback=self._changedPhasingDirection,
                                         applyCallback=self._applyPhasing,
                                         grid=(phasingRow, 0), gridSpan=(1, 7), hAlign='top',
                                         margins=(2, 2, 2, 2), spacing=(0, 0))
        self.phasingFrame.setVisible(False)

    def _setDisplaySettings(self, _general, _showY, _yAx, _yTexts, xAxisUnits):
        """Set the default spectrum display settings.
        """
        self._spectrumDisplaySettings = SpectrumDisplaySettings(parent=self.settingsWidget,
                                                                mainWindow=self.mainWindow, spectrumDisplay=self,
                                                                grid=(0, 0),
                                                                xTexts=AXISUNITS, xAxisUnits=_general.xAxisUnits,
                                                                yTexts=AXISUNITS, yAxisUnits=_general.yAxisUnits,
                                                                showXAxis=True if _showY else not bool(self._flipped),
                                                                showYAxis=True if _showY else bool(self._flipped),
                                                                _baseAspectRatioAxisCode=_general._baseAspectRatioAxisCode,
                                                                _aspectRatios=_general.aspectRatios,
                                                                symbolType=_general.symbolType,
                                                                annotationType=_general.annotationType,
                                                                symbolSize=_general.symbolSizePixel,
                                                                symbolThickness=_general.symbolThickness,
                                                                arrowType=_general.arrowType,
                                                                arrowSize=_general.arrowSize,
                                                                arrowMinimum=_general.arrowMinimum,
                                                                multipletAnnotationType=_general.multipletAnnotationType,
                                                                multipletType=_general.multipletType,
                                                                aliasEnabled=_general.aliasEnabled,
                                                                aliasShade=_general.aliasShade,
                                                                aliasLabelsEnabled=_general.aliasLabelsEnabled,
                                                                peakSymbolsEnabled=_general.peakSymbolsEnabled,
                                                                peakLabelsEnabled=_general.peakLabelsEnabled,
                                                                peakArrowsEnabled=_general.peakArrowsEnabled,
                                                                multipletSymbolsEnabled=_general.multipletSymbolsEnabled,
                                                                multipletLabelsEnabled=_general.multipletLabelsEnabled,
                                                                multipletArrowsEnabled=_general.multipletArrowsEnabled,
                                                                stripArrangement=_general.stripArrangement,
                                                                _aspectRatioMode=_general.aspectRatioMode,
                                                                contourThickness=_general.contourThickness,
                                                                zPlaneNavigationMode=_general.zPlaneNavigationMode,
                                                                )

    def _populateWidgets(self):
        """Update the state of spectrumDisplay from the project layout OR from preferences if not found
        """
        # populate settings widget
        if self.application.preferences.general.restoreLayoutOnOpening and \
                self.mainWindow.moduleLayouts:

            try:
                # not very clean - need to separate into an attribute dict
                with self._spectrumDisplaySettings.blockWidgetSignals(recursive=False):
                    with self.phasingFrame.blockWidgetSignals(recursive=False):
                        # read from the project layout
                        found = self.restoreSpectrumState(discard=True)
            except Exception as es:
                found = False

            if not found:
                # read from the preferences
                self._updateStateFromPreferences()
        else:
            # read from the preferences
            self._updateStateFromPreferences()

    def _addStrip(self, strip, tilePosition):
        """Add a Strip instance using tilePosition
        :param strip: Strip instance
        :param tilePosition: an (x,y) tuple

        CPPNINTERNAL: used in GuiStrip to insert itself at the right spot
        """
        if not isinstance(tilePosition, (tuple, list)) or len(tilePosition) != 2:
            raise ValueError(f'Invalid tilePosition: {tilePosition}')
        self.stripFrame.layout().addWidget(strip, tilePosition[0], tilePosition[1])

    def _updateStateFromPreferences(self):
        """Update the state of spectrumDisplay from the preferences
        """
        prefsGen = self.application.preferences.general
        # initialise to the project defaults
        self._spectrumDisplaySettings._populateWidgets(prefsGen.aspectRatioMode, prefsGen.aspectRatios,
                                                       prefsGen.annotationType, prefsGen.stripArrangement,
                                                       prefsGen.symbolSizePixel, prefsGen.symbolThickness, prefsGen.symbolType,
                                                       prefsGen.arrowType, prefsGen.arrowSize, prefsGen.arrowMinimum,
                                                       prefsGen.multipletAnnotationType, prefsGen.multipletType,
                                                       prefsGen.xAxisUnits, prefsGen.yAxisUnits,
                                                       prefsGen.aliasEnabled, prefsGen.aliasShade, prefsGen.aliasLabelsEnabled,
                                                       prefsGen.peakSymbolsEnabled, prefsGen.peakLabelsEnabled, prefsGen.peakArrowsEnabled,
                                                       prefsGen.multipletSymbolsEnabled, prefsGen.multipletLabelsEnabled, prefsGen.multipletArrowsEnabled,
                                                       prefsGen.contourThickness,
                                                       prefsGen.zPlaneNavigationMode)

    def _updateSettingsAxesUnits(self):
        """Update the settings of x- and y-axis units of the display
        CCPNINTERNAL: used in _newS[ectrumDisplay and when setting Axis.unit attribute
        """
        xUnit = self._unitIndices[0]
        yUnit = self._unitIndices[1] if not self.is1D else None

        self._spectrumDisplaySettings._setAxesUnits(xUnit, yUnit)
        self._spectrumDisplaySettings._settingsChanged()

    def restoreSpectrumState(self, discard=False):
        """Restore the state for this widget
        """
        if self.mainWindow._spectrumModuleLayouts:
            return self.mainWindow.moduleArea.restoreModuleState(self.mainWindow._spectrumModuleLayouts, self, discard=discard)

    def _updateStripsFromSettings(self):

        from copy import deepcopy

        # copy values from preferences
        numStrips = len(self.strips)

        settings = self._getSettingsDict()

        self._setFloatingAxes(xUnits=settings[AXISXUNITS],
                              yUnits=settings[AXISYUNITS],
                              aspectRatioMode=settings[AXISASPECTRATIOMODE],
                              aspectRatios=settings[AXISASPECTRATIOS])

        for strip in self.strips:
            # get the values from the settings (check in case the number of states has changed)
            strip.symbolLabelling = min(settings[ANNOTATIONTYPE], self.MAXPEAKLABELTYPES - 1)
            strip.symbolType = min(settings[SYMBOLTYPE], self.MAXPEAKSYMBOLTYPES - 1)
            strip.symbolSize = settings[SYMBOLSIZE]
            strip.symbolThickness = settings[SYMBOLTHICKNESS]
            strip.multipletLabelling = min(settings[MULTIPLETANNOTATIONTYPE], self.MAXMULTIPLETLABELTYPES - 1)
            strip.multipletType = min(settings[MULTIPLETTYPE], self.MAXMULTIPLETSYMBOLTYPES - 1)

            strip.contourThickness = settings[CONTOURTHICKNESS]
            strip.aliasEnabled = settings[ALIASENABLED]
            strip.aliasShade = settings[ALIASSHADE]
            strip.aliasLabelsEnabled = settings[ALIASLABELSENABLED]

            strip.peakSymbolsEnabled = settings[PEAKSYMBOLSENABLED]
            strip.peakLabelsEnabled = settings[PEAKLABELSENABLED]
            strip.peakArrowsEnabled = settings[PEAKARROWSENABLED]
            strip.multipletSymbolsEnabled = settings[MULTIPLETSYMBOLSENABLED]
            strip.multipletLabelsEnabled = settings[MULTIPLETLABELSENABLED]
            strip.multipletArrowsEnabled = settings[MULTIPLETARROWSENABLED]

            strip.arrowType = min(settings[ARROWTYPES], self.MAXARROWTYPES - 1)
            strip.arrowSize = settings[ARROWSIZE]
            strip.arrowMinimum = settings[ARROWMINIMUM]

            strip._CcpnGLWidget._xUnits = settings[AXISXUNITS]
            strip._CcpnGLWidget._yUnits = settings[AXISYUNITS]
            strip._CcpnGLWidget._aspectRatioMode = settings[AXISASPECTRATIOMODE]
            strip._CcpnGLWidget._aspectRatios = deepcopy(settings[AXISASPECTRATIOS])

            if numStrips < 2:
                strip.setAxesVisible(True, True)

            else:
                if self.stripArrangement == 'Y':
                    if self.lastAxisOnly:
                        strip.setAxesVisible(False, True)
                    else:
                        strip.setAxesVisible(True, True)
                elif self.stripArrangement == 'X':
                    if self.lastAxisOnly:
                        strip.setAxesVisible(True, False)
                    else:
                        strip.setAxesVisible(True, True)
                else:
                    strip.setAxesVisible(True, True)

    def _getPropertiesState(self):
        """Get a dict of the required properties.
        """
        pDict = {}
        if self.strips and (strp := self.strips[0]):
            # NOTE:ED - not the best way, but can improve later
            pDict[self._GRIDVISIBLE] = strp.gridVisible
            pDict[self._CROSSHAIRVISIBLE] = strp.crosshairVisible
            pDict[self._SIDEBANDSVISIBLE] = strp.sideBandsVisible
            pDict[self._SHOWSPECTRAONPHASING] = strp.showSpectraOnPhasing
            pDict[self._SPECTRUMBORDERSVISIBLE] = strp.spectrumBordersVisible

        return pDict

    def _setPropertiesState(self, **widgetsState):
        """Get a dict of the required properties.
        """
        for strp in self.strips:
            if (value := widgetsState.get(self._GRIDVISIBLE)) is not None:
                strp.gridVisible = value
            if (value := widgetsState.get(self._CROSSHAIRVISIBLE)) is not None:
                strp.crosshairVisible = value
            if (value := widgetsState.get(self._SIDEBANDSVISIBLE)) is not None:
                strp.sideBandsVisible = value
            if (value := widgetsState.get(self._SHOWSPECTRAONPHASING)) is not None:
                strp.showSpectraOnPhasing = value
            if (value := widgetsState.get(self._SPECTRUMBORDERSVISIBLE)) is not None:
                strp.spectrumBordersVisible = value

    def restoreWidgetsState(self, **widgetsState):
        """Restore the state of the gui-settings and additional properties accessed through menus.
        """
        # block the GL-signals from updating the display as not required until first paint
        GLSignals = GLNotifier(parent=None)
        with GLSignals.blocking():
            super().restoreWidgetsState(**widgetsState)

            # set the non-widget properties
            self._setPropertiesState(**widgetsState)

            # need to set the values from the restored state
            self._spectrumDisplaySettings._updateLockedSettings(always=True)

            # ensure that the settings-widget and the properties are synced
            self._updateStripsFromSettings()

    @CcpnModule.widgetsState.getter
    def widgetsState(self):
        """Add extra parameters to the state-dict for values handled by the menus.
        """
        state = super().widgetsState

        state |= self._getPropertiesState()
        return state

    def renameModule(self, name):

        if super(GuiSpectrumDisplay, self).renameModule(name):
            self.rename(name)  # rename the core-object, use notifier to update

    def clearSpectra(self):
        """
        :return: remove all displayed spectra
        """
        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                for specView in self.spectrumViews:
                    if specView.spectrum is not None:
                        self.removeSpectrum(specView.spectrum)

    def _registerNotifiers(self):
        self._spectrumChangeNotifier = self.setNotifier(self.project,
                                                        [Notifier.CHANGE, Notifier.RENAME, Notifier.DELETE],
                                                        Spectrum.className,
                                                        self._spectrumChanged)

        self._spectrumViewNotifier = self.setNotifier(self.project,
                                                      [Notifier.CREATE, Notifier.DELETE, Notifier.CHANGE],
                                                      SpectrumView.className,
                                                      self._spectrumViewChanged,
                                                      onceOnly=True)

        self._peakListViewNotifier = self.setNotifier(self.project,
                                                      [Notifier.CREATE, Notifier.DELETE, Notifier.CHANGE],
                                                      PeakListView.className,
                                                      self._listViewChanged,
                                                      onceOnly=True)

        self._integralListViewNotifier = self.setNotifier(self.project,
                                                          [Notifier.CREATE, Notifier.DELETE],
                                                          IntegralListView.className,
                                                          self._listViewChanged,
                                                          onceOnly=True)

        self._multipletListViewNotifier = self.setNotifier(self.project,
                                                           [Notifier.CREATE, Notifier.DELETE],
                                                           MultipletListView.className,
                                                           self._listViewChanged,
                                                           onceOnly=True)

        self._spectrumGroupNotifier = self.setNotifier(self.project,
                                                       [Notifier.CHANGE, Notifier.RENAME, Notifier.DELETE],
                                                       SpectrumGroup.className,
                                                       self._spectrumGroupChanged,
                                                       onceOnly=True)

        self._spectrumDisplayNotifier = self.setNotifier(self.project,
                                                         [Notifier.RENAME],
                                                         SpectrumDisplay.className,
                                                         self._spectrumDisplayChanged,
                                                         onceOnly=True)

    @property
    def _flipped(self):
        """Return 0|1 depending on whether the 1d spectrum-display is flipped with intensity on the x-axis.
        """
        if self.is1D:
            return 1 - self.axisCodes.index('intensity')
        return 0

    def setRightOverlayArea(self, value):
        """Set the overlay state for the right axis.
        """
        self._rightGLAxis.setOverlayArea(value)

    def setBottomOverlayArea(self, value):
        """Set the overlay state for the bottom axis.
        """
        self._bottomGLAxis.setOverlayArea(value)

    def _setFloatingAxes(self, xUnits, yUnits, aspectRatioMode, aspectRatios):
        """Set the aspectRatio and units for the floating axes
        """
        if hasattr(self, '_rightGLAxis'):
            self._rightGLAxis._xUnits = xUnits
            self._rightGLAxis._yUnits = yUnits
            self._rightGLAxis._aspectRatioMode = aspectRatioMode
            self._rightGLAxis._aspectRatios = deepcopy(aspectRatios)
        if hasattr(self, '_bottomGLAxis'):
            self._bottomGLAxis._xUnits = xUnits
            self._bottomGLAxis._yUnits = yUnits
            self._bottomGLAxis._aspectRatioMode = aspectRatioMode
            self._bottomGLAxis._aspectRatios = deepcopy(aspectRatios)

    def showAllStripHeaders(self, handle=None):
        """Convenience to show headers of all strips
        """
        for strip in self.strips:
            strip.header.headerVisible = True
            if handle:
                strip.header.handle = handle

    def hideAllStripHeaders(self, handle=None):
        """Convenience to hide headers of all strips
        """
        for strip in self.strips:
            # only hide the strips that match the handle or hide all if None
            if handle is None:
                strip.header.headerVisible = False
            elif strip.header.handle == handle:
                strip.header.headerVisible = False

    def getSpectrumViewFromSpectrum(self, spectrum):
        """Get the local spectrumView linked to the spectrum
        """
        specViews = [specView for specView in self.spectrumViews if specView.spectrum == spectrum]
        return specViews

    def _refreshSpectrumView(self, spectrum, specViews):
        # specViews = self.getSpectrumViewFromSpectrum(spectrum)
        for specView in specViews:
            specView.buildContours = True

            for strp in self.strips:
                _order = strp._CcpnGLWidget._ordering
                if specView in _order:
                    # force an update of the spectrum-view-settings dict for the GLWidget
                    stackCount = _order.index(specView)
                    strp._CcpnGLWidget._buildSpectrumSetting(spectrumView=specView, stackCount=stackCount)

        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        # fire refresh event to repaint the screen
        GLSignals = GLNotifier(parent=spectrum)
        targets = [objList for objList in spectrum.peakLists] + [objList for objList in spectrum.multipletLists]
        GLSignals.emitEvent(targets=targets, triggers=[GLNotifier.GLPEAKLISTS,
                                                       GLNotifier.GLPEAKLISTLABELS,
                                                       GLNotifier.GLMULTIPLETLISTS,
                                                       GLNotifier.GLMULTIPLETLISTLABELS
                                                       ])

    def _spectrumChanged(self, data):
        """Handle notifier for changes to spectrum
        This can also be used after creation of new spectrumView
        """
        # NOTE:ED - this needs a better system to determine which notifiers affect the screen
        trigger = data[Notifier.TRIGGER]
        spectrum = data[Notifier.OBJECT]

        if trigger == Notifier.CHANGE:
            specViews = self.getSpectrumViewFromSpectrum(spectrum)
            if not specViews:
                return

            action = self.spectrumActionDict.get(spectrum)
            if action:
                # update toolbar button name
                action.setText(spectrum.name)
                setWidgetFont(action, size='SMALL')

            # update's
            for strip in self.strips:
                strip._updatePlaneAxes()
            self._refreshSpectrumView(spectrum, specViews)

            if (specs := data.get(Notifier.SPECIFIERS)) and specs.get('_openFile'):
                # scale the axes to the new file
                for strip in self.strips:
                    # NOTE:ED - need to execute this in the correct place/time
                    strip._queueAppend([strip._resetAllZoom, None])

        elif trigger == Notifier.RENAME:
            self.spectrumToolBar._spectrumRename(data)

        elif trigger == Notifier.DELETE:
            self.removeSpectrum(spectrum)

    def _spectrumViewChanged(self, data):
        """Respond to spectrumViews being created/deleted, update contents of the spectrumWidgets frame
        """
        spectrumView = data[Notifier.OBJECT]
        if self.isDeleted or spectrumView not in self.spectrumViews:
            # can ignore spectrumViews not belonging to this spectrumDisplay
            return

        for strip in self.strips:
            strip._updateVisibility()
        self._updateAxesVisibility()

        trigger = data[Notifier.TRIGGER]

        # respond to the create/delete notifiers
        if trigger == Notifier.CREATE:
            for strip in self.strips:
                strip._updatePlaneAxes()

            if spectrumView in self.spectrumViews:
                self._spectrumChanged({Notifier.TRIGGER: Notifier.CHANGE,
                                       Notifier.OBJECT : spectrumView.spectrum})

        elif trigger == Notifier.DELETE:

            for strip in self.strips:
                strip._updatePlaneAxes()

        elif trigger == Notifier.CHANGE:
            if spectrumView in self.spectrumViews:
                _spectrumViewHasChanged({Notifier.OBJECT: spectrumView})

    def decreaseSpectrumScale(self):
        """
        Decreases Spectrum Scale for current spectra.
        """
        step = self.application.preferences.general.scalingFactorStep
        with undoBlockWithoutSideBar():
            for spectrumView in self.spectrumViews:
                if spectrumView.isDisplayed:
                    spectrum = spectrumView.spectrum
                    if spectrum in self.current.spectra:
                        spectrum.scale -= step

    def increaseSpectrumScale(self):
        """
        Increases  Spectrum Scale for current spectra.
        """
        step = self.application.preferences.general.scalingFactorStep
        with undoBlockWithoutSideBar():
            for spectrumView in self.spectrumViews:
                if spectrumView.isDisplayed:
                    spectrum = spectrumView.spectrum
                    if spectrum in self.current.spectra:
                        spectrum.scale += step

    def _spectrumDisplayChanged(self, data):
        """Respond to spectrumDisplay being renamed, update contents of label.
        """
        if data:
            trigger = data[Notifier.TRIGGER]
            if trigger == Notifier.RENAME and data[Notifier.OBJECT] == self:
                self.label.setText(self._name)
                self.label.updateGeometry()
                self.label.repaint()

    def _spectrumGroupChanged(self, data):
        """Respond to spectrumViews being created/deleted, update contents of the spectrumWidgets frame
        """
        if self.isGrouped and data:
            trigger = data[Notifier.TRIGGER]
            spectrumGroup = data[Notifier.OBJECT]
            if trigger == Notifier.RENAME:
                self.spectrumGroupToolBar._spectrumGroupRename(data)

            elif trigger == Notifier.CHANGE:
                spectrumGroups = [action.text() for action in self.spectrumGroupToolBar.actions()]
                if spectrumGroup.pid not in spectrumGroups:
                    return
                self._colourChanged(spectrumGroup)
                _spectrumGroupViewHasChanged({Notifier.OBJECT: spectrumGroup})

            elif trigger == Notifier.DELETE:
                # remove from the spectrumGroup toolbar
                self.spectrumGroupToolBar._removeSpectrumGroup(None, spectrumGroup)

    def _colourChanged(self, spectrumGroup):
        if self.is1D:
            self._1dColourChanged(spectrumGroup)
        else:
            self._NdColourChanged(spectrumGroup)

    def _NdColourChanged(self, spectrumGroup):
        _posCol = spectrumGroup.positiveContourColour
        _negCol = spectrumGroup.negativeContourColour
        _specViews = [specView for spec in spectrumGroup.spectra for specView in self.spectrumViews if specView.spectrum == spec]

        _posColours = (None,)
        if _posCol and _posCol.startswith('#'):
            _posColours = (_posCol,)
        elif _posCol in Colour.colorSchemeTable:
            _posColours = Colour.colorSchemeTable[_posCol]
        # get the positive contour colour list
        stepX = len(_specViews) - 1
        step = stepX
        stepY = len(_posColours) - 1
        jj = 0
        if stepX > 0:
            for ii in range(stepX + 1):
                _interp = (stepX - step) / stepX
                _intCol = Colour.interpolateColourHex(_posColours[min(jj, stepY)], _posColours[min(jj + 1, stepY)],
                                                      _interp,
                                                      alpha=1.0)
                _specViews[ii].positiveContourColour = _intCol
                step -= stepY
                while step < 0:
                    step += stepX
                    jj += 1
        elif stepX == 0:
            _specViews[0].positiveContourColour = _posColours[0]
        _negColours = (None,)
        if _negCol and _negCol.startswith('#'):
            _negColours = (_negCol,)
        elif _negCol in Colour.colorSchemeTable:
            _negColours = Colour.colorSchemeTable[_negCol]
        # get the negative contour colour list
        stepX = len(_specViews) - 1
        step = stepX
        stepY = len(_negColours) - 1
        jj = 0
        if stepX > 0:
            for ii in range(stepX + 1):
                _interp = (stepX - step) / stepX
                _intCol = Colour.interpolateColourHex(_negColours[min(jj, stepY)], _negColours[min(jj + 1, stepY)],
                                                      _interp,
                                                      alpha=1.0)
                _specViews[ii].negativeContourColour = _intCol
                step -= stepY
                while step < 0:
                    step += stepX
                    jj += 1
        elif stepX == 0:
            _specViews[0].negativeContourColour = _negColours[0]

    def _1dColourChanged(self, spectrumGroup):
        _sliceCol = spectrumGroup.sliceColour
        _specViews = [specView for spec in spectrumGroup.spectra for specView in self.spectrumViews if specView.spectrum == spec]

        _sliceColours = (None,)
        if _sliceCol and _sliceCol.startswith('#'):
            _sliceColours = (_sliceCol,)
        elif _sliceCol in Colour.colorSchemeTable:
            _sliceColours = Colour.colorSchemeTable[_sliceCol]
        # get the slice contour colour list
        stepX = len(_specViews) - 1
        step = stepX
        stepY = len(_sliceColours) - 1
        jj = 0
        if stepX > 0:
            for ii in range(stepX + 1):
                _interp = (stepX - step) / stepX
                _intCol = Colour.interpolateColourHex(_sliceColours[min(jj, stepY)], _sliceColours[min(jj + 1, stepY)],
                                                      _interp,
                                                      alpha=1.0)
                _specViews[ii].sliceColour = _intCol
                step -= stepY
                while step < 0:
                    step += stepX
                    jj += 1
        elif stepX == 0:
            _specViews[0].sliceColour = _sliceColours[0]

    def _spectrumViewVisibleChanged(self):
        """Respond to a visibleChanged in one of the spectrumViews.
        """
        for strip in self.strips:
            strip._updateVisibility()
        self._updateAxesVisibility()

        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=None)
        GLSignals._emitAxisUnitsChanged(source=None, strip=self.strips[0], dataDict={})

    def _settingsChanged(self, dataDict):
        """Handle changes that occur in the settings widget
        dataDict is a dictionary of settingsWidget contents:
            {
            xUnits: range(0-number of options)
            yUnits: range(0-number of options)
            lockAspectRatio: True/False
            }
        """
        # spawn a redraw of the GL windows
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=None)
        GLSignals._emitAxisUnitsChanged(source=None, strip=self.strips[0], dataDict=dataDict)

    def _stripDirectionChangedInSettings(self, value):
        """Handle changing the stripDirection from the settings widget
        """
        if value not in range(len(STRIPDIRECTIONS)):
            raise ValueError('stripDirection not in ', STRIPDIRECTIONS)

        newDirection = STRIPDIRECTIONS[value]

        # if newDirection != self.stripArrangement:
        # set the new stripDirection, and redraw
        self.stripArrangement = newDirection

        # notify settings widget - because cheating
        self._spectrumDisplaySettings.setStripArrangementButtons(value)
        self._redrawLayout()
        self._forceRedrawFloatingAxes()

    def _zPlaneNavigationModeChangedInSettings(self, value):
        """Handle changing the zPlaneNavigation mode from the settings widget
        """
        if value not in ZPlaneNavigationModes.values():
            raise ValueError('zPlaneNavigation not in ', ZPlaneNavigationModes)

        newDirection = ZPlaneNavigationModes(value).dataValue

        if newDirection != self.zPlaneNavigationMode:
            # set the new stripDirection, and redraw
            self.zPlaneNavigationMode = newDirection

            # notify settings widget
            self.attachZPlaneWidgets()
            self._forceRedrawFloatingAxes()

    def _listViewChanged(self, data):
        """Respond to spectrumViews being created/deleted, update contents of the spectrumWidgets frame
        """
        for strip in self.strips:
            strip._updateVisibility()
        self._updateAxesVisibility()

        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=None)
        GLSignals.emitPaintEvent()

    def getVisibleSpectra(self) -> list:
        """Return a list of spectra currently visible in the spectrumDisplay
        """
        spectra = set()
        if self.strips:
            for spectrum in self.strips[0].getSpectra():
                for spectrumView in spectrum.spectrumViews:
                    if spectrumView.isDisplayed:
                        spectra.add(spectrum)
                        break
        return list(spectra)

    # GWV 07/01/2022: replace by getVisibleSpectra() fro naming consistency
    # @property
    # def visibleSpectra(self) -> list:
    #     """List of spectra currently visible in the spectrumDisplay
    #     """
    #     return self.getVisibleSpectra()
    # displayedSpectra = visibleSpectra

    @property
    def isGrouped(self):
        """Return whether the spectrumDisplay contains grouped spectra
        """
        # Using AbstractWrapperObject because there seems to already be a setParameter
        # belonging to spectrumDisplay
        grouped = AbstractWrapperObject._getInternalParameter(self, self._ISGROUPED)
        if grouped is not None:
            return grouped

        return False

    @isGrouped.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def isGrouped(self, grouped):
        """Set whether the spectrumDisplay contains grouped spectra
        """
        AbstractWrapperObject._setInternalParameter(self, self._ISGROUPED, grouped)

    @property
    def stripArrangement(self):
        """Strip axis direction ('X', 'Y', 'T', None) - None only for non-strip plots
        """
        # Using AbstractWrapperObject because there seems to already be a setParameter
        # belonging to spectrumDisplay
        arrangement = AbstractWrapperObject._getInternalParameter(self, self._STRIPARRANGEMENT)
        if arrangement is not None:
            return arrangement

        # get default values in the ccpnInternal store
        arrangement = self._wrappedData.stripDirection  # SHOULD always be 'Y', if it makes a difference
        return arrangement

    @stripArrangement.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def stripArrangement(self, value):
        """Set the new strip direction ('X', 'Y', 'T', None) - None only for non-strip plots
        """
        if not isinstance(value, str):
            raise TypeError('stripArrangement must be a string')
        elif value not in STRIPDIRECTIONS:
            raise ValueError("stripArrangement must be either 'X', 'Y' or 'T'")

        AbstractWrapperObject._setInternalParameter(self, self._STRIPARRANGEMENT, value)

        self.setVisibleAxes()

    @property
    def zPlaneNavigationMode(self):
        """Position of the zPlane navigation buttons
        """
        # Using AbstractWrapperObject because there seems to already be a setParameter
        # belonging to spectrumDisplay
        arrangement = AbstractWrapperObject._getInternalParameter(self, self._ZPLANENAVIGATIONMODE)
        if arrangement is not None:
            return arrangement

        return ZPlaneNavigationModes(0).dataValue

    @zPlaneNavigationMode.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def zPlaneNavigationMode(self, value):
        """Set the new position of zPlane navigation buttons
        """
        labels = [val.dataValue for val in ZPlaneNavigationModes]
        if not isinstance(value, str):
            raise TypeError('zPlaneNavigationMode must be a string')
        elif value not in labels:
            raise ValueError(f"zPlaneNavigationMode must be in {repr(labels)}")

        AbstractWrapperObject._setInternalParameter(self, self._ZPLANENAVIGATIONMODE, value)

    def _updateAxesVisibility(self):
        # if not self.is1D:
        self._rightGLAxis.updateVisibleSpectrumViews()
        self._bottomGLAxis.updateVisibleSpectrumViews()

    def setVisibleAxes(self):
        """Set which of the axis widgets are visible based on the strip tilePositions and stripArrangement
        """
        # NOTE:ED - currently only one row or column
        #           Should no-shared-axis mean don't show either axis?
        #           Need to think about tiles later
        # leave a gap for overlaying the axis widgets

        if not self.lastAxisOnly or len(self.strips) < 2:
            # remove the margins and hide the axes
            self._stripFrameScrollArea.setViewportMargins(0, 0, 0, 0)
            self._rightGLAxis.hide()
            self._bottomGLAxis.hide()
        else:

            # show the required axis
            if self.stripArrangement == 'Y':
                self._stripFrameScrollArea.setViewportMargins(0, 0, self._rightGLAxis.width(), 0)
                # self._stripFrameScrollArea.setViewportMargins(0, 0, self._rightGLAxis.width(), self._bottomGLAxis.height())
                aDict = self.strips[0]._CcpnGLWidget._getAxisDict()
                self._stripAddMode = (self.strips[0]._CcpnGLWidget.pixelX, self.strips[0]._CcpnGLWidget.pixelY)
                self._rightGLAxis.show()
                self._bottomGLAxis.hide()
                # self._rightGLAxis._glAxisLockChanged(aDict)
                self._stripAddMode = None
                self._rightGLAxis._updateAxes = True
            else:
                self._stripFrameScrollArea.setViewportMargins(0, 0, 0, self._bottomGLAxis.height())
                # self._stripFrameScrollArea.setViewportMargins(0, 0, self._rightGLAxis.width(), self._bottomGLAxis.height())
                aDict = self.strips[0]._CcpnGLWidget._getAxisDict()
                self._stripAddMode = (self.strips[0]._CcpnGLWidget.pixelX, self.strips[0]._CcpnGLWidget.pixelY)
                self._rightGLAxis.hide()
                self._bottomGLAxis.show()
                # self._bottomGLAxis._glAxisLockChanged(aDict)
                self._stripAddMode = None
                self._bottomGLAxis._updateAxes = True

        self.stripFrame.update()
        self._stripFrameScrollArea._updateAxisWidgets()
        self._forceRedrawFloatingAxes()

    def _forceRedrawFloatingAxes(self):
        """force a fractional delayed update of the extra axes
        """
        # can't think of a better way yet - will be fixable of single window used for all viewports in fucture
        QtCore.QTimer.singleShot(50, self._stripFrameScrollArea.refreshViewPort)

    # def _setPlaneAxisWidgets(self):
    #     """Update the widgets in the planeToolbar
    #     CCPNINTERNAL: used in a few spots
    #     """
    #     if not self.is1D:
    #         for strip in self.strips:
    #             strip._setPlaneAxisWidgets()

    def _stripRange(self):
        """Return the bounds for the tilePositions of the strips
        as tuple of tuples ((minRow, minColumn), (maxRow, maxColumn))
        """
        maxTilePos = (0, 0)
        minTilePos = (MAXTILEBOUND, MAXTILEBOUND)
        for strip in self.strips:
            tilePos = strip.tilePosition or (0, strip.stripIndex)
            minTilePos = tuple(min(ii, jj) for ii, jj in zip(minTilePos, tilePos))
            maxTilePos = tuple(max(ii, jj) for ii, jj in zip(maxTilePos, tilePos))

        if minTilePos != (0, 0):
            raise ValueError('Illegal tilePosition in strips')

        return (minTilePos, maxTilePos)

    @property
    def rowCount(self):
        """Strip row count.
        This is independent of the stripArrangement and always returns the same value.
        If stripArrangement is 'Y', strips are in a row and 'row' will return the visible row count
        If stripArrangement is 'X', strips are in a column and 'row' will return the visible column count
        """
        _, maxTilePos = self._stripRange()
        return maxTilePos[0] + 1

    @property
    def columnCount(self):
        """Strip column count.
        This is independent of the stripArrangement and always returns the same value.
        If stripArrangement is 'Y', strips are in a row and 'column' will return the visible column count
        If stripArrangement is 'X', strips are in a column and 'column' will return the visible row count
        """
        _, maxTilePos = self._stripRange()
        return maxTilePos[1] + 1

    def stripAtTilePosition(self, tilePosition: Tuple[int, int]) -> 'Strip':
        """Return the strip at a given tilePosition
        """
        if not isinstance(tilePosition, tuple):
            raise ValueError('Expected a tuple for tilePosition')
        if len(tilePosition) != 2:
            raise ValueError('Tuple must be (x, y)')
        if any(type(vv) != int for vv in tilePosition):
            raise ValueError('Tuple must be of type int')

        for strip in self.strips:
            stripTilePos = strip.tilePosition or (0, strip.stripIndex)
            if tilePosition == stripTilePos:
                return strip

    def _stripList(self, dim, value):
        foundStrips = []
        for strip in self.strips:
            stripTilePos = strip.tilePosition or (0, strip.stripIndex)
            if stripTilePos[dim] == value:
                # append the strip with its row
                foundStrips.append((strip, stripTilePos[1 - dim]))

        # sort by required dimension
        sortedStrips = sorted(foundStrips, key=lambda k: k[dim])
        return tuple(strip for strip, dim in sortedStrips)

    def stripRow(self, row: int) -> ['Strip']:
        """Return the ordered stripRow at a given row
        tilePositions are independent of stripArrangement
        """
        if not isinstance(row, int):
            raise ValueError('Expected an int')

        return self._stripList(0, row)

    def stripColumn(self, column: int) -> ['Strip']:
        """Return the ordered stripColumn at a given column
        tilePositions are independent of stripArrangement
        """
        if not isinstance(column, int):
            raise ValueError('Expected an int')

        return self._stripList(1, column)

    def _getSpectrumGroups(self):
        """Return the groups contained in the spectrumDisplay
        """
        # Using AbstractWrapperObject because there seems to already be a setParameter
        # belonging to spectrumDisplay
        _spectrumGroups = AbstractWrapperObject._getInternalParameter(self, self._SPECTRUMGROUPS)
        if _spectrumGroups is not None:
            return _spectrumGroups

        return ()

    def _setSpectrumGroups(self, groups):
        """Set the groups in the spectrumDisplay
        """
        AbstractWrapperObject._setInternalParameter(self, self._SPECTRUMGROUPS, groups)

    def _getSettingsDict(self):
        """get the settings dict from the settingsWidget
        """
        return self._spectrumDisplaySettings.getValues()

    @property
    def pinnedStrips(self):
        """Return the list of pinned strips.
        """
        return list(filter(lambda st: st.pinned, self.strips))

    #=========================================================================================
    # Methods
    #=========================================================================================

    def resizeEvent(self, ev):
        if self.isDeleted:
            return

        # resize the contents of the stripFrame
        # self.setColumnStretches(stretchValue=True, widths=False)
        super().resizeEvent(ev)

    def _hoverEvent(self, event):
        event.accept()

    def _processDroppedItems(self, data):
        """
        CallBack for Drop events
        CCPN INTERNAL: Also called from GuiStrip
        """
        # local import to avoid cycles
        from ccpn.framework.Framework import MAXITEMLOGGING
        from ccpn.core.Project import Project

        theObject = data.get('theObject')
        objs = []

        if DropBase.URLS in data:
            # process dropped items but don't open any spectra
            objs = self.mainWindow._processDroppedItems(data)

            # discard any further loads if project loaded (may be inconsistent)
            if list(filter(lambda obj: isinstance(obj, Project), objs)):
                return

            # filter out internal objs that have already been processed
            objs = list(filter(lambda obj: isinstance(obj, Spectrum), objs))

        elif DropBase.PIDS in data:
            # handle Pids
            pids = data.get(DropBase.PIDS, [])
            objs = self.project.getObjectsByPids(pids)

        if len(objs) > 0:

            if len(objs) > MAXITEMLOGGING:
                with notificationEchoBlocking():
                    self._handleObjs(objs, theObject)
            else:
                self._handleObjs(objs, theObject)

    def _handleObjs(self, objs: (list, tuple), strip=None) -> bool:
        """handle a list of objects;
        :return True in case it is a Spectrum or a SpectrumGroup
        """
        success = False
        nmrChains = []
        nmrResidues = []
        nmrAtoms = []
        substances = []

        getLogger().info('Handling objects...')

        for obj in objs:
            if isinstance(obj, Spectrum):
                if self.isGrouped:
                    showWarning('Forbidden drop', 'A Single spectrum cannot be dropped onto grouped displays.')
                    return success

                with undoBlockWithoutSideBar():
                    try:
                        self.displaySpectrum(obj)
                    except RuntimeError as es:
                        errorTxt = str(es)
                        if self.mainWindow.application._isInDebugMode:
                            showWarning('Incompatible drop', errorTxt)
                        else:
                            getLogger().warning(f'Incompatible drop: {errorTxt}')
                        # raise RuntimeError(errorTxt)
                        return success

                if strip in self.strips:
                    self.current.strip = strip
                elif self.current.strip not in self.strips:
                    self.current.strip = self.strips[0]

                success = True

            elif isinstance(obj, PeakList):
                with undoBlockWithoutSideBar():
                    self._handlePeakList(obj)
                success = True

            elif isinstance(obj, Peak):
                self._handlePeak(obj, strip)

            elif isinstance(obj, SpectrumGroup):
                with undoBlockWithoutSideBar():
                    self._handleSpectrumGroup(obj)
                success = True

            elif isinstance(obj, Sample):
                with undoBlockWithoutSideBar():
                    self._handleSample(obj)
                success = True

            elif isinstance(obj, NmrAtom):
                nmrAtoms.append(obj)

            elif isinstance(obj, Substance):
                substances.append(obj)

            elif isinstance(obj, NmrResidue):
                nmrResidues.append(obj)

            elif obj is not None and isinstance(obj, NmrChain):
                nmrChains.append(obj)

            elif isinstance(obj, GuiStrip):
                self._handleStrip(obj, strip)

            else:
                showWarning(
                        f'Dropped item {obj!r}',
                        'Wrong kind; drop Spectrum, SpectrumGroup, Peak, PeakList,'
                        ' NmrChain, NmrResidue, NmrAtom or Strip',
                        )
        if nmrChains:
            with undoBlockWithoutSideBar():
                self._handleNmrChains(nmrChains)
        if nmrResidues:
            with undoBlockWithoutSideBar():
                self._handleNmrResidues(nmrResidues)
        if nmrAtoms:
            with undoBlockWithoutSideBar():
                self._handleNmrAtoms(nmrAtoms)
        if substances:
            with undoBlockWithoutSideBar():
                self._handleSubstances(substances)

        return success

    def _handlePeak(self, peak, strip, widths=None):
        """Navigate to the peak position in the strip
        """
        from ccpn.ui.gui.lib.SpectrumDisplayLib import navigateToPeakInStrip

        # use the library method
        navigateToPeakInStrip(self, strip, peak, widths=None)

    def _handleStrip(self, moveStrip, dropStrip):
        """Move a strip within a spectrumDisplay by dragging the strip label to another strip
        """
        if moveStrip.spectrumDisplay == self:
            strips = self.orderedStrips
            stripInd = strips.index(dropStrip)

            if stripInd != strips.index(moveStrip):
                moveStrip.moveTo(stripInd)

    def _handlePeakList(self, peakList):
        """See if peaklist can be copied
        """
        spectrum = peakList.spectrum

        if spectrum.dimensionCount < self.dimensionCount:
            showWarning('Dropped PeakList "%s"' % peakList.pid,
                        'Cannot copy: dimensionCount\'s PeakList and SpectrumDisplay do not match')
            return
        else:
            from ccpn.ui.gui.popups.CopyPeakListPopup import CopyPeakListPopup

            popup = CopyPeakListPopup(parent=self.mainWindow, mainWindow=self.mainWindow,
                                      spectrumDisplay=self, selectItem=peakList.pid)
            # popup.sourcePeakListPullDown.select(peakList.pid)
            popup.exec_()
        # showInfo(title='Copy PeakList "%s"' % peakList.pid, message='Copy to selected spectra')

    def _handleSpectrumGroup(self, spectrumGroup):
        """
        Add spectrumGroup on the display and its button on the toolBar
        CCPNINTERNAL: also called from open module-related code OpenItemObjects
        """
        if self.isGrouped:
            self.spectrumGroupToolBar._addAction(spectrumGroup)
            for spectrum in spectrumGroup.spectra:
                self.displaySpectrum(spectrum)
            if self.current.strip not in self.strips:
                self.current.strip = self.strips[0]

    def _handleSample(self, sample):
        """
        Add spectra linked to sample and sampleComponent. Used for screening
        """
        for spectrum in sample.spectra:
            self.displaySpectrum(spectrum)
        for sampleComponent in sample.sampleComponents:
            if sampleComponent.substance is not None:
                for spectrum in sampleComponent.substance.referenceSpectra:
                    self.displaySpectrum(spectrum)
        if self.current.strip not in self.strips:
            self.current.strip = self.strips[0]

    def _handleNmrChains(self, nmrChains):
        nmrResidues = []
        for chain in nmrChains:
            nmrResidues += chain.nmrResidues

        # mark all nmrChains.nmrResidues.nmrAtoms to the window
        self._handleNmrResidues(nmrResidues, showDialog=False)

    def _handleNmrResidues(self, nmrResidues, showDialog=True):

        # get the widget that is under the cursor, SHOULD be guiWidget
        point = QtGui.QCursor.pos()
        destStrip = QtWidgets.QApplication.widgetAt(point)

        if destStrip and isinstance(destStrip, CcpnGLWidget):
            objectsClicked = destStrip.getObjectsUnderMouse()

            if objectsClicked is None:
                return

            if PEAKSELECT in objectsClicked or MULTIPLETSELECT in objectsClicked:
                # dropped onto a peak or multiplet
                # dropping onto a multiplet will apply to all attached peaks

                # dialogResult = showMulti('nmrResidue', 'What do you want to do with the nmrResidues?',
                #                          texts=['Mark and Assign', 'Assign NmrResidues to selected peaks/multiplets'])

                # Assign nmrResidues atoms to peaks
                peaks = set(self.current.peaks)
                for mult in self.current.multiplets:
                    peaks = peaks | set(mult.peaks)
                _assignNmrResiduesToPeaks(peaks=list(peaks), nmrResidues=nmrResidues)

                # # mark all nmrResidues.nmrAtoms to the window
                # if 'Mark' in dialogResult:
                #     for nmrResidue in nmrResidues:
                #         self._createNmrResidueMarks(nmrResidue)

            elif not objectsClicked:
                # mark all nmrResidues.nmrAtoms to the window
                for nmrResidue in nmrResidues:
                    self._createNmrResidueMarks(nmrResidue, destStrip)

    def _handleSubstances(self, substances):
        # get the widget that is under the cursor, SHOULD be guiWidget
        # if selected peaks, will add the substance Name as peak.annotation

        peaks = set(self.current.peaks)
        replaceAnnotation = True
        for mult in self.current.multiplets:
            peaks = peaks | set(mult.peaks)
        if peaks:
            visibleSpectra = self.getVisibleSpectra()
            with undoBlockWithoutSideBar():
                for substance in substances:
                    annotation = substance.name
                    for peak in peaks:
                        if peak.peakList.spectrum in visibleSpectra:
                            if not replaceAnnotation:  # if want appending instead of replacing
                                annotation = ', '.join(filter(None, set([peak.annotation, substance.name])))  # Filter to make sure is not duplicating any existing annotation
                            peak.annotation = annotation

        # # FIXME below still doesn't work if in stack mode
        # point = QtGui.QCursor.pos()
        # destStrip = QtWidgets.QApplication.widgetAt(point)
        #
        # if destStrip and isinstance(destStrip, CcpnGLWidget):
        #     objectsClicked = destStrip.getObjectsUnderMouse()
        #
        #     if objectsClicked is None:
        #         return
        #
        #     if PEAKSELECT in objectsClicked or MULTIPLETSELECT in objectsClicked:
        #         # dropped onto a peak or multiplet
        #         # dropping onto a multiplet will apply to all attached peaks
        #         # Set substance name to peak.annotation
        #         peaks = set(self.current.peaks)
        #         for mult in self.current.multiplets:
        #             peaks = peaks | set(mult.peaks)
        #         for substance in substances:
        #             for peak in peaks:
        #                 # make sure is not duplicating any existing annotation, and is appending not replacing.
        #                 annotation = ', '.join(filter(None, set([peak.annotation, substance.name])))
        #                 peak.annotation = annotation
        #
        #     elif not objectsClicked:
        #         # function not defined yet
        #         showWarning('Dropped Substance(s).','Action not implemented yet' )

    def _handleNmrAtoms(self, nmrAtoms):

        # get the widget that is under the cursor, SHOULD be guiWidget
        point = QtGui.QCursor.pos()
        destStrip = QtWidgets.QApplication.widgetAt(point)

        if destStrip and isinstance(destStrip, CcpnGLWidget):
            objectsClicked = destStrip.getObjectsUnderMouse()

            if objectsClicked is None:
                return

            if PEAKSELECT in objectsClicked or MULTIPLETSELECT in objectsClicked:
                # dropped onto a peak or multiplet
                # dropping onto a multiplet will apply to all attached peaks

                # dialogResult = showMulti('nmrAtoms', 'What do you want to do with the nmrAtoms?',
                #                          texts=['Mark and Assign', 'Assign NmrAtoms to selected peaks/multiplets'])

                # Assign nmrAtoms to peaks
                peaks = set(self.current.peaks)
                for mult in self.current.multiplets:
                    peaks = peaks | set(mult.peaks)
                _assignNmrAtomsToPeaks(nmrAtoms=nmrAtoms, peaks=list(peaks))

                # # mark all nmrAtoms to the window
                # if 'Mark' in dialogResult:
                #     for nmrAtom in nmrAtoms:
                #         self._markNmrAtom(nmrAtom)

            elif not objectsClicked:
                # mark all nmrResidues.nmrAtoms to the window
                for nmrAtom in nmrAtoms:
                    self._markNmrAtom(nmrAtom, destStrip)

    def _createNmrResidueMarks(self, nmrResidue, destStrip):
        """
        Mark a list of nmrAtoms in the spectrum displays
        """
        # showInfo(title='Mark nmrResidue "%s"' % nmrResidue.pid, message='mark nmrResidue in strips')

        from ccpn.AnalysisAssign.modules.BackboneAssignmentModule import nmrAtomsFromOffsets
        from ccpn.ui.gui.lib.StripLib import markNmrAtoms

        guiStrip = destStrip.strip
        nmrAtoms = nmrAtomsFromOffsets(nmrResidue)
        if nmrAtoms:
            markNmrAtoms(self.mainWindow, nmrAtoms, guiStrip)

    def _markNmrAtom(self, nmrAtom, destStrip):
        """
        Mark an nmrAtom in the spectrum displays with horizontal/vertical bars
        """
        # showInfo(title='Mark nmrAtom "%s"' % nmrAtom.pid, message='mark nmrAtom in strips')

        from ccpn.ui.gui.lib.StripLib import markNmrAtoms

        guiStrip = destStrip.strip
        markNmrAtoms(self.mainWindow, [nmrAtom], guiStrip)

    def setScrollbarPolicies(self, horizontal='asNeeded', vertical='asNeeded'):
        """Set the scrollbar policies; convenience to expose to the user
        """
        from ccpn.ui.gui.widgets.ScrollArea import SCROLLBAR_POLICY_DICT

        if horizontal not in SCROLLBAR_POLICY_DICT or \
                vertical not in SCROLLBAR_POLICY_DICT:
            getLogger().warning('Invalid scrollbar policy (%s, %s)' % (horizontal, vertical))
        self.stripFrame.setScrollBarPolicies((horizontal, vertical))

    def _updatePivot(self):
        """Updates pivot in all strips contained in the spectrum display."""
        for strip in self.strips:
            strip._updatePivot()

    def _updatePhasing(self):
        """Updates phasing in all strips contained in the spectrum display."""
        for strip in self.strips:
            strip._updatePhasing()

    def _changedPhasingDirection(self):
        """Changes direction of phasing from horizontal to vertical or vice versa."""
        for strip in self.strips:
            strip._changedPhasingDirection()

    def updateSpectrumTraces(self):
        """Add traces to all strips"""
        for strip in self.strips:
            strip._updateTraces()

    def _applyPhasing(self, phasingValues):
        """apply the phasing values here
        phasingValues is a dict:

        { 'direction': 'horizontal' or 'vertical' - the last direction selected
          'horizontal': {'ph0': float,
                         'ph1': float,
                         'pivot': float},
          'vertical':   {'ph0': float,
                         'ph1': float,
                         'pivot': float}
        }
        """
        pass

    def toggleHTrace(self):
        if not self.is1D and self.current.strip:
            trace = not self.current.strip.hTraceAction.isChecked()
            self.setHorizontalTraces(trace)
        else:
            getLogger().warning('no strip selected')

    def toggleVTrace(self):
        if not self.is1D and self.current.strip:
            trace = not self.current.strip.vTraceAction.isChecked()
            self.setVerticalTraces(trace)
        else:
            getLogger().warning('no strip selected')

    def setHorizontalTraces(self, trace):
        for strip in self.strips:
            strip._setHorizontalTrace(trace)

    def setVerticalTraces(self, trace):
        for strip in self.strips:
            strip._setVerticalTrace(trace)

    def removePhasingTraces(self):
        """
        Removes all phasing traces from all strips.
        """
        for strip in self.strips:
            strip.removePhasingTraces()

    def togglePhaseConsole(self):
        """Toggles whether phasing console is displayed.
        """
        isVisible = not self.phasingFrame.isVisible()
        self.phasingFrame.setVisible(isVisible)

        if self.is1D:
            self.hTraceAction = True
            self.vTraceAction = False

            if not self.phasingFrame.pivotsSet:
                pivot = np.mean(self.spectrumViews[0].spectrum.spectrumLimits[0])
                self.phasingFrame.setInitialPivots((pivot, 0.0))

        else:
            self.hTraceAction = self.current.strip.hTraceAction.isChecked()
            self.vTraceAction = self.current.strip.vTraceAction.isChecked()

            if not self.phasingFrame.pivotsSet:
                specView = self.spectrumViews[0]
                limits = specView.spectrum.getByAxisCodes('spectrumLimits', axisCodes=specView.strip.axisCodes)
                pivot = [np.mean(lim) for lim in limits[:2]]
                self.phasingFrame.setInitialPivots(pivot)

        for strip in self.strips:
            if isVisible:
                strip.turnOnPhasing()
            else:
                strip.turnOffPhasing()
        self._updatePhasing()

    def showToolbar(self):
        """show the toolbar"""
        # showing the toolbar, but we need to update the checkboxes of all strips as well.
        self.spectrumUtilToolBar.show()
        for strip in self.strips:
            strip.toolbarAction.setChecked(True)

    def hideToolbar(self):
        """hide the toolbar"""
        # hiding the toolbar, but we need to update the checkboxes of all strips as well.
        self.spectrumUtilToolBar.hide()
        for strip in self.strips:
            strip.toolbarAction.setChecked(False)

    def toggleToolbar(self):
        """Toggle the toolbar """
        if not self.spectrumUtilToolBar.isVisible():
            self.showToolbar()
        else:
            self.hideToolbar()

    def showSpectrumToolbar(self):
        """show the spectrum toolbar"""
        # showing the spectrum toolbar, but we need to update the checkboxes of all strips as well.
        if self.isGrouped:
            self.spectrumGroupToolBar.show()
        else:
            self.spectrumToolBar.show()

        for strip in self.strips:
            strip.spectrumToolbarAction.setChecked(True)

    def hideSpectrumToolbar(self):
        """hide the spectrum toolbar"""
        # hiding the spectrum toolbar, but we need to update the checkboxes of all strips as well.
        if self.isGrouped:
            self.spectrumGroupToolBar.hide()
        else:
            self.spectrumToolBar.hide()

        for strip in self.strips:
            strip.spectrumToolbarAction.setChecked(False)

    def toggleSpectrumToolbar(self):
        """Toggle the spectrum toolbar """
        if self.isGrouped:
            if not self.spectrumGroupToolBar.isVisible():
                self.showSpectrumToolbar()
            else:
                self.hideSpectrumToolbar()
        else:
            if not self.spectrumToolBar.isVisible():
                self.showSpectrumToolbar()
            else:
                self.hideSpectrumToolbar()

    def arrangeLabels(self, selected: bool = False):
        """Auto-arrange the peak/multiplet labels to minimise any overlaps.
        """
        from ccpn.ui.gui.lib.SpectrumDisplayLib import arrangeLabelPositions

        arrangeLabelPositions(self, selected=selected)

    def resetLabels(self, selected: bool = False):
        """Reset arrangement of peak/multiplet labels.
        """
        from ccpn.ui.gui.lib.SpectrumDisplayLib import resetLabelPositions

        resetLabelPositions(self, selected=selected)

    def _closeModule(self):
        """
        CCPN-INTERNAL: used to close the module
        Closes spectrum display and deletes it from the project.
        """
        self.mainWindow._deleteSpectrumDisplay(self)

    def _removeIndexStrip(self, value):
        self.deleteStrip(self.strips[value])

    def _redrawLayout(self):
        """Redraw the stripFrame with the new stripDirection
        """
        layout = self.stripFrame.getLayout()

        if layout and layout.count() > 0:

            with self.stripFrame.blockWidgetSignals():
                # clear the layout and rebuild
                _widgets = []

                # need to be removed if not using QObjectCleanupHandler before creating new layout
                while layout.count():
                    _widgets.append(layout.takeAt(0).widget())

                self._rebuildStrip(_widgets, layout)

            self.showAxes()
            self.setColumnStretches(stretchValue=True)

    def _rebuildStrip(self, _widgets, layout):
        """Rebuild the strip and insert the widgets
        """
        # remember necessary layout info and create a new layout - ensures clean for new widgets
        margins = layout.getContentsMargins()
        space = layout.spacing()
        QtWidgets.QWidget().setLayout(layout)
        layout = QtWidgets.QGridLayout()
        self.stripFrame.setLayout(layout)
        layout.setContentsMargins(*margins)
        layout.setSpacing(space)
        # reinsert strips in new order - reset minimum widths
        if self.stripArrangement == 'Y':

            # horizontal strip layout
            for m, widgStrip in enumerate(_widgets):
                # layout.addWidget(widgStrip, 0, m)

                tilePosition = widgStrip.tilePosition
                if True:  #tilePosition is None:
                    layout.addWidget(widgStrip, 0, m)
                    widgStrip.tilePosition = (0, m)
                else:
                    layout.addWidget(widgStrip, tilePosition[0], tilePosition[1])

        elif self.stripArrangement == 'X':

            # vertical strip layout
            for m, widgStrip in enumerate(_widgets):
                # layout.addWidget(widgStrip, m, 0)

                tilePosition = widgStrip.tilePosition
                if True:  #tilePosition is None:
                    layout.addWidget(widgStrip, m, 0)
                    widgStrip.tilePosition = (0, m)
                else:
                    layout.addWidget(widgStrip, tilePosition[1], tilePosition[0])

        elif self.stripArrangement == 'T':

            # NOTE:ED - Tiled plots not fully implemented yet
            getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(self.pid))

        else:
            getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(self.pid))

    def _removeStripFromLayout(self, strip):
        """Remove the current strip from the layout
        CCPN Internal
        """
        layout = self.stripFrame.getLayout()

        if layout and layout.count() > 1:

            with self.stripFrame.blockWidgetSignals():
                # clear the layout and rebuild
                _widgets = []

                # need to be removed if not using QObjectCleanupHandler before creating new layout
                while layout.count():
                    _widgets.append(layout.takeAt(0).widget())
                _widgets.remove(strip)
                strip.hide()
                strip.setParent(None)  # set widget parent to None to hide,
                # was previously handled by addWidget to tempStore

                self._rebuildStrip(_widgets, layout)

        else:
            raise RuntimeError('Error, stripFrame layout in invalid state')

    def _restoreStripToLayout(self, strip, currentIndex):
        """Restore the current strip to the layout
        CCPN Internal
        """
        layout = self.stripFrame.layout()
        if layout:

            with self.stripFrame.blockWidgetSignals():

                # clear the layout and rebuild
                # need to be removed if not using QObjectCleanupHandler before creating new layout
                _widgets = []
                while layout.count():
                    _widgets.append(layout.takeAt(0).widget())
                _widgets.insert(currentIndex, strip)
                strip.show()

                self._rebuildStrip(_widgets, layout)

                if strip not in self.strips:
                    for order, cStrip in enumerate(_widgets):
                        cStrip._setStripIndex(order)

        else:
            raise RuntimeError('Error, stripFrame layout in invalid state')

    @logCommand(get='self')
    def deleteStrip(self, strip):
        """Delete a strip from the spectrumDisplay

        :param strip: strip to delete as object or pid
        """
        strip = self.getByPid(strip) if isinstance(strip, str) else strip

        if strip is None:
            showWarning('Delete strip', 'Invalid strip')
            return

        if strip not in self.strips:
            showWarning('Delete strip', 'Selected strip "%s" is not part of SpectrumDisplay "%s"' \
                        % (strip.pid, self.pid))
            return

        if self.stripCount == 1:
            showWarning('Delete strip', 'Last strip of SpectrumDisplay "%s" cannot be removed' \
                        % (self.pid,))
            return

        # with undoBlockWithoutSideBar():
        with undoStackBlocking() as _:  # Do not add to undo/redo stack
            with undoStackBlocking() as addUndoItem:
                with self._hideWidget(self.stripFrame):
                    # retrieve list of created items from the api
                    # strangely, this modifies _wrappedData.orderedStrips, and 'removes' the boundStrip by changing the indexing
                    # if it is at the end of apiBoundStrips then it confuses the indexing
                    indexing = [st.stripIndex() for st in self.strips]

                    apiObjectsCreated = strip._getApiObjectTree()

                    # reset indexing again SHOULD now be okay; i.e. nothing has been 'removed' from apiBoundStrips yet
                    for ii, ind in enumerate(indexing):
                        self.strips[ii]._setStripIndex(ind)

                    index = strip.stripIndex()

                    # add layout handling to the undo stack
                    addUndoItem(undo=partial(self._redrawAxes, index))
                    addUndoItem(undo=partial(self._restoreStripToLayout, strip, index),
                                redo=partial(self._removeStripFromLayout, strip))
                    # add notifier handling for the strip
                    addUndoItem(undo=partial(strip.setBlankingAllNotifiers, False),
                                redo=partial(strip.setBlankingAllNotifiers, True))

                    self._removeStripFromLayout(strip)
                    strip.setBlankingAllNotifiers(True)

                    # add object delete/undelete to the undo stack
                    addUndoItem(undo=BlankedPartial(strip._wrappedData.root._unDelete,
                                                    topObjectsToCheck=(strip._wrappedData.topObject,),
                                                    obj=strip, trigger='create', preExecution=False,
                                                    objsToBeUnDeleted=apiObjectsCreated),
                                redo=BlankedPartial(strip._delete,
                                                    obj=strip, trigger='delete', preExecution=True)
                                )

                    marks = strip.marks
                    # delete the strip
                    strip._finaliseAction('delete')
                    with notificationBlanking():
                        strip._delete()

                        # this makes it unrecoverable
                        #   - okay, as strips not allowed to undo, note that it is not in the undo-list above
                        strip.close()

                    for mark in marks:
                        mark.delete()

                    addUndoItem(redo=partial(self._redrawAxes, deletingStrip=True))

            # do axis redrawing
            self._redrawAxes(deletingStrip=True)

    def _redrawAxesAddMode(self):
        self._stripAddMode = (self.strips[0]._CcpnGLWidget.pixelX, self.strips[0]._CcpnGLWidget.pixelY)
        self.strips[0]._CcpnGLWidget._emitAxisFixed()

    def _redrawAxes(self, index=-1, deletingStrip=False):
        """Redraw the axes for the stripFrame, and set the new current strip,
        will default to the last strip if not selected.
        """
        self.showAxes(stretchValue=True, deletingStrip=deletingStrip)
        if self.strips:
            self.current.strip = self.strips[index]
        self._stripAddMode = None

    def removeCurrentStrip(self):
        """Remove current.strip if it belongs to self.
        """
        if self.current.strip is None:
            showWarning('Remove current strip', 'Select first in SpectrumDisplay by clicking')
            return

        self.deleteStrip(self.current.strip)

    def setLastAxisOnly(self, lastAxisOnly: bool = True):
        self.lastAxisOnly = lastAxisOnly

    def showAxes(self, strips=None, stretchValue=False, widths=True, minimumWidth=STRIP_MINIMUMWIDTH, deletingStrip=False):
        # use the strips as they are ordered in the model
        currentStrips = self.orderedStrips

        if currentStrips:

            if self.stripArrangement == 'Y':

                # strips are arranged in a row
                if self.lastAxisOnly and len(currentStrips) > 1:
                    for ss in self.strips:
                        ss.setAxesVisible(rightAxisVisible=False, bottomAxisVisible=True)

                    # show _rightGLAxis
                else:
                    for ss in self.strips:
                        ss.setAxesVisible(rightAxisVisible=True, bottomAxisVisible=True)

            elif self.stripArrangement == 'X':

                # strips are arranged in a column
                if self.lastAxisOnly and len(currentStrips) > 1:
                    for ss in self.strips:
                        ss.setAxesVisible(rightAxisVisible=True, bottomAxisVisible=False)

                    # show _bottomGLAxis

                else:
                    for ss in self.strips:
                        ss.setAxesVisible(rightAxisVisible=True, bottomAxisVisible=True)

            elif self.stripArrangement == 'T':

                # NOTE:ED - Tiled plots not fully implemented yet
                getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(self.pid))

            else:
                getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(self.pid))

            self.setColumnStretches(stretchValue=stretchValue, widths=widths, minimumWidth=minimumWidth, deletingStrip=deletingStrip)

            # show the required _rightGLAxis/_bottomGLAxis
            self.setVisibleAxes()

        if hasattr(self, '_rightGLAxis'):
            self._rightGLAxis.redrawAxes()
        if hasattr(self, '_bottomGLAxis'):
            self._bottomGLAxis.redrawAxes()

    @logCommand(get='self')
    def increaseTraceScale(self):
        # self.mainWindow.traceScaleUp(self.mainWindow)
        if not self.is1D:
            for strip in self.strips:
                for spectrumView in strip.spectrumViews:
                    if spectrumView.traceScale is not None:
                        spectrumView.traceScale *= 1.4

                # spawn a redraw of the strip
                strip._updatePivot()

    @logCommand(get='self')
    def decreaseTraceScale(self):
        # self.mainWindow.traceScaleDown(self.mainWindow)
        if not self.is1D:
            for strip in self.strips:
                for spectrumView in strip.spectrumViews:
                    if spectrumView.traceScale is not None:
                        spectrumView.traceScale /= 1.4

                # spawn a redraw of the strip
                strip._updatePivot()

    def increaseStripSize(self):
        """Increase the width/height of the strips depending on the orientation
        """
        if self.stripArrangement == 'Y':

            # strips are arranged in a row
            self._increaseStripWidth()

        elif self.stripArrangement == 'X':

            # strips are arranged in a column
            self._increaseStripHeight()

        elif self.stripArrangement == 'T':

            # NOTE:ED - Tiled plots not fully implemented yet
            getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(self.pid))

        else:
            getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(self.pid))

    def decreaseStripSize(self):
        """Decrease the width/height of the strips depending on the orientation
        """
        if self.stripArrangement == 'Y':

            # strips are arranged in a row
            self._decreaseStripWidth()

        elif self.stripArrangement == 'X':

            # strips are arranged in a column
            self._decreaseStripHeight()

        elif self.stripArrangement == 'T':

            # NOTE:ED - Tiled plots not fully implemented yet
            getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(self.pid))

        else:
            getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(self.pid))

    def _increaseStripWidth(self):
        """Increase the widths of the strips
        """
        factor = (100.0 + self.application.preferences.general.stripWidthZoomPercent) / 100.0
        self._setStripWidths(factor)

    def _decreaseStripWidth(self):
        """decrease the widths of the strips
        """
        factor = 100.0 / (100.0 + self.application.preferences.general.stripWidthZoomPercent)
        self._setStripWidths(factor)

    def _setStripWidths(self, factor=1.0):
        """set the widths for the strips
        """
        self.stripFrame.hide()

        strips = self.orderedStrips
        newWidth = max(strips[0].width() * factor, STRIP_MINIMUMWIDTH)
        axisWidth = 0

        if len(strips) > 1:
            for strip in strips[:-1]:
                strip.setMinimumWidth(int(newWidth))
            strips[-1].setMinimumWidth(int(newWidth + axisWidth))
            self.stripFrame.setMinimumWidth(int((newWidth + STRIP_SPACING) * len(strips) + axisWidth - STRIP_SPACING))
        else:
            strips[0].setMinimumWidth(int(newWidth))
            self.stripFrame.setMinimumWidth(int(newWidth))

        self.stripFrame.show()

    def _increaseStripHeight(self):
        """Increase the heights of the strips
        """
        factor = (100.0 + self.application.preferences.general.stripWidthZoomPercent) / 100.0
        self._setStripHeights(factor)

    def _decreaseStripHeight(self):
        """decrease the heights of the strips
        """
        factor = 100.0 / (100.0 + self.application.preferences.general.stripWidthZoomPercent)
        self._setStripHeights(factor)

    def _setStripHeights(self, factor=1.0):
        """set the heights for the strips
        """
        self.stripFrame.hide()

        strips = self.orderedStrips
        newHeight = max(strips[0].height() * factor, STRIP_MINIMUMHEIGHT)
        axisHeight = 0

        if len(strips) > 1:
            for strip in strips[:-1]:
                strip.setMinimumHeight(int(newHeight))
            strips[-1].setMinimumHeight(int(newHeight + axisHeight))
            self.stripFrame.setMinimumHeight(int((newHeight + STRIP_SPACING) * len(strips) + axisHeight - STRIP_SPACING))
        else:
            strips[0].setMinimumHeight(int(newHeight))
            self.stripFrame.setMinimumHeight(int(newHeight))

        self.stripFrame.show()

    def _copyPreviousStripValues(self, fromStrip, toStrip):
        """Copy the trace settings to another strip in the spectrumDisplay.
        """
        traceScale = fromStrip.spectrumViews[0].traceScale
        toStrip.setTraceScale(traceScale)

        if self.phasingFrame.isVisible():
            toStrip.turnOnPhasing()

    @logCommand(get='self')
    def addStrip(self, strip=None) -> 'GuiStripNd':
        """Creates a new strip by cloning strip with index (default the last) in the display.
        """
        strip = self.getByPid(strip) if isinstance(strip, str) else strip
        index = strip.stripIndex() if strip else -1
        tilePosition = strip.tilePosition if strip else None
        if tilePosition is None:
            tilePosition = (0, 0)

        if self.phasingFrame.isVisible():
            showWarning(str(self.windowTitle()), 'Please disable Phasing Console before adding strips')
            return

        with undoStackBlocking():  # Do not add to undo/redo stack
            with undoStackBlocking() as addUndoItem:
                with self._hideWidget(self.stripFrame):
                    addUndoItem(undo=self._redrawAxes,
                                redo=self._redrawAxesAddMode)

                    with notificationBlanking():
                        # get the visibility of strip to be copied
                        copyVisible = self.strips[index].header.headerVisible

                        # inserts the strip into the stripFrame here
                        self._stripAddMode = (self.strips[0]._CcpnGLWidget.pixelX, self.strips[0]._CcpnGLWidget.pixelY)
                        result = self.strips[index]._clone()

                        if not isinstance(result, GuiStrip):
                            raise RuntimeError('Expected an object of class %s, obtained %s' % (GuiStrip, result.__class__))

                    # required because the above clone is wrapped in notificationBlanking
                    result._finaliseAction('create')

                    # copy the strip Header if needed
                    # result.header.headerVisible = copyVisible if copyVisible is not None else False
                    # result.header.setLabelVisible(visible=copyVisible if copyVisible is not None else False)

                    # retrieve list of created items from the api
                    # strangely, this modifies _wrappedData.orderedStrips
                    apiObjectsCreated = result._getApiObjectTree()
                    addUndoItem(undo=BlankedPartial(Undo._deleteAllApiObjects,
                                                    obj=result, trigger='delete', preExecution=True,
                                                    objsToBeDeleted=apiObjectsCreated),
                                redo=BlankedPartial(result._wrappedData.root._unDelete,
                                                    topObjectsToCheck=(result._wrappedData.topObject,),
                                                    obj=result, trigger='create', preExecution=False,
                                                    objsToBeUnDeleted=apiObjectsCreated)
                                )

                    index = result.stripIndex()

                    # add notifier handling to the stack
                    addUndoItem(undo=partial(result.setBlankingAllNotifiers, True),
                                redo=partial(result.setBlankingAllNotifiers, False))

                    # add layout handling to the undo stack
                    addUndoItem(undo=partial(self._removeStripFromLayout, result),
                                redo=partial(self._restoreStripToLayout, result, index))
                    addUndoItem(redo=partial(self._redrawAxes, index),
                                undo=self._redrawAxesAddMode)

            # do axis redrawing
            self._redrawAxes(index)  # this might be getting confused with the ordering

        return result

    def setColumnStretches(self, stretchValue=False, scaleFactor=1.0, widths=True, minimumWidth=None, deletingStrip=False):
        """Set the column widths of the strips so that the last strip accommodates the axis bar
                if necessary."""

        if self.stripArrangement == 'Y':

            # strips are arranged in a row
            self._setColumnStretches(stretchValue=stretchValue, scaleFactor=scaleFactor, widths=widths, minimumWidth=minimumWidth, deletingStrip=deletingStrip)

        elif self.stripArrangement == 'X':

            # strips are arranged in a column
            self._setRowStretches(stretchValue=stretchValue, scaleFactor=scaleFactor, heights=widths, minimumHeight=minimumWidth, deletingStrip=deletingStrip)

        elif self.stripArrangement == 'T':

            # NOTE:ED - Tiled plots not fully implemented yet
            getLogger().warning('Tiled plots not implemented for spectrumDisplay: %s' % str(self.pid))

        else:
            getLogger().warning('Strip direction is not defined for spectrumDisplay: %s' % str(self.pid))

    def _setColumnStretches(self, stretchValue=False, scaleFactor=1.0, widths=True, minimumWidth=STRIP_MINIMUMWIDTH, deletingStrip=False):
        """Set the column widths of the strips so that the last strip accommodates the axis bar
        if necessary."""
        widgets = self.stripFrame.children()

        # set the strip spacing and the visibility of the scroll bars
        layout = self.stripFrame.getLayout()
        layout.setHorizontalSpacing(STRIP_SPACING)
        layout.setVerticalSpacing(0)
        if self._stripFrameScrollArea:
            # scroll area for strips
            self._stripFrameScrollArea.setScrollBarPolicies(scrollBarPolicies=('asNeeded', 'never'))

        if widgets:

            AXIS_WIDTH = 1
            AXIS_PADDING = STRIP_SPACING

            thisLayout = self.stripFrame.layout()
            thisLayoutWidth = self.stripFrame.width() - (2 * STRIP_SPACING)

            if deletingStrip:
                thisLayoutWidth *= (self.stripCount / (self.stripCount + 1))

            if not thisLayout.itemAt(0):
                return

            self.stripFrame.hide()

            if self.strips:
                AXIS_WIDTH = self.orderedStrips[0].getRightAxisWidth()
                firstStripWidth = (thisLayoutWidth - AXIS_WIDTH) / self.stripCount
            else:
                firstStripWidth = thisLayoutWidth

            if minimumWidth:
                firstStripWidth = max(firstStripWidth, minimumWidth)
            firstStripWidth = max(firstStripWidth, STRIP_MINIMUMWIDTH)

            if True:  # not self.lastAxisOnly:
                maxCol = 0
                for wid in self.orderedStrips:
                    index = thisLayout.indexOf(wid)
                    if index >= 0:
                        row, column, cols, rows = thisLayout.getItemPosition(index)
                        maxCol = max(maxCol, column)

                for col in range(0, maxCol + 1):
                    if widths and thisLayout.itemAt(col):
                        thisLayout.itemAt(col).widget().setMinimumWidth(int(firstStripWidth))
                    thisLayout.setColumnStretch(col, 1 if stretchValue else 1)

                if minimumWidth:
                    self.stripFrame.setMinimumWidth(int((firstStripWidth + STRIP_SPACING) * len(self.orderedStrips) - STRIP_SPACING))
                else:
                    self.stripFrame.setMinimumWidth(self.stripFrame.minimumSizeHint().width())
                self.stripFrame.setMinimumHeight(STRIP_MINIMUMHEIGHT)
                try:
                    self._rightGLAxis.setMinimumHeight(STRIP_MINIMUMHEIGHT - self.strips[0]._stripToolBarWidget.height())
                    self._rightGLAxis._updateAxes = True
                    self._rightGLAxis.update()
                except:
                    pass

            self.stripFrame.show()

    def _setRowStretches(self, stretchValue=False, scaleFactor=1.0, heights=True, minimumHeight=STRIP_MINIMUMHEIGHT, deletingStrip=False):
        """Set the row heights of the strips so that the last strip accommodates the axis bar
        if necessary."""
        widgets = self.stripFrame.children()

        # set the strip spacing and the visibility of the scroll bars
        layout = self.stripFrame.getLayout()
        layout.setHorizontalSpacing(0)
        layout.setVerticalSpacing(STRIP_SPACING)
        if self._stripFrameScrollArea:
            # scroll area for strips
            self._stripFrameScrollArea.setScrollBarPolicies(scrollBarPolicies=('never', 'asNeeded'))

        if widgets:

            AXIS_HEIGHT = 1
            AXIS_PADDING = STRIP_SPACING

            thisLayout = self.stripFrame.layout()
            # thisLayoutHeight = self._stripFrameScrollArea.height()
            thisLayoutHeight = self.stripFrame.height() - (2 * STRIP_SPACING)

            if deletingStrip:
                thisLayoutHeight *= (self.stripCount / (self.stripCount + 1))

            if not thisLayout.itemAt(0):
                return

            self.stripFrame.hide()

            if self.strips:
                firstStripHeight = thisLayoutHeight / self.stripCount
                AXIS_HEIGHT = self.orderedStrips[0].getBottomAxisHeight()
            else:
                firstStripHeight = thisLayoutHeight

            if minimumHeight:
                firstStripHeight = max(firstStripHeight, minimumHeight)
            firstStripHeight = max(firstStripHeight, STRIP_MINIMUMHEIGHT)

            if True:  #not self.lastAxisOnly:
                maxRow = 0
                for wid in self.orderedStrips:
                    index = thisLayout.indexOf(wid)
                    if index >= 0:
                        row, column, cols, rows = thisLayout.getItemPosition(index)
                        maxRow = max(maxRow, row)

                for rr in range(0, maxRow + 1):
                    if heights and thisLayout.itemAt(rr):
                        thisLayout.itemAt(rr).widget().setMinimumHeight(int(firstStripHeight))
                    thisLayout.setRowStretch(rr, 1 if stretchValue else 1)

                if minimumHeight:
                    self.stripFrame.setMinimumHeight(int((firstStripHeight + STRIP_SPACING) * len(self.orderedStrips) - STRIP_SPACING))
                else:
                    self.stripFrame.setMinimumHeight(self.stripFrame.minimumSizeHint().height())
                self.stripFrame.setMinimumWidth(STRIP_MINIMUMWIDTH)
                if hasattr(self, '_bottomGLAxis'):
                    self._bottomGLAxis.setMinimumWidth(STRIP_MINIMUMWIDTH)
                    self._bottomGLAxis._updateAxes = True
                    self._bottomGLAxis.update()

            self.stripFrame.show()

    def autoRange(self):
        """Zooms Y axis of current strip to show entire region.
        """
        for strip in self.strips:
            strip.autoRange()

    def _resetYZooms(self):
        """Zooms Y axis of current strip to show entire region.
        """
        for strip in self.strips:
            strip._resetYZoom()

    def _resetXZooms(self):
        """Zooms X axis of current strip to show entire region.
        """
        for strip in self.strips:
            strip._resetXZoom()

    def _resetAllZooms(self):
        """Zooms X/Y axes of current strip to show entire region.
        """
        for strip in self.strips:
            strip._resetAllZoom()

    def _restoreZoom(self):
        """Restores last saved zoom of current strip.
        """
        if not self.strips:
            showWarning('Restore Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._restoreZoom()

    def _storeZoom(self):
        """Saves zoomed region of current strip."""
        if not self.strips:
            showWarning('Store Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._storeZoom()

    def _previousZoom(self):
        """Changes to the previous zoom of current strip."""
        if not self.strips:
            showWarning('Undo Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._previousZoom()

    def _nextZoom(self):
        """Changes to the next zoom of current strip."""
        if not self.strips:
            showWarning('Redo Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._nextZoom()

    def _setZoom(self):
        """Changes to the next zoom of current strip."""
        if not self.strips:
            showWarning('Set Zoom', 'SpectrumDisplay "%s" does not contain any strips' % self.pid)
            return
        strip = self.strips[0]
        strip._setZoomPopup()

    def _zoomIn(self):
        """zoom in to the current strip."""
        if not self.strips:
            showWarning('Restore Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._zoomIn()

    def _zoomOut(self):
        """zoom out of current strip."""
        if not self.strips:
            showWarning('Restore Zoom', 'SpectrumDisplay "%s" does not contain any strips' \
                        % self.pid)
            return

        for strip in self.strips:
            strip._zoomOut()

    def toggleGrid(self):
        """Toggles whether grid is displayed in all strips of spectrum display.
        """
        for strip in self.strips:
            strip.toggleGrid()

    def toggleSideBands(self):
        """Toggles whether sideBands are displayed in all strips of spectrum display.
        """
        for strip in self.strips:
            strip.toggleSideBands()

    def toggleCrosshair(self):
        """Toggles whether cross-hair is displayed in all strips of spectrum display.
        """
        for strip in self.strips:
            strip._toggleCrosshair()

    def _cycleSymbolLabelling(self):
        """Toggles peak labelling of current strip.
        """
        try:
            if not self.current.strip:
                showWarning('Cycle Peak Labelling', 'No strip selected')
                return

            for strip in self.strips:
                strip.cycleSymbolLabelling()

        except:
            getLogger().warning('Error cycling peak labelling')

    def _cyclePeakSymbols(self):
        """toggles peak labelling of current strip.
        """
        try:
            if not self.current.strip:
                showWarning('Cycle Peak Symbols', 'No strip selected')
                return

            for strip in self.strips:
                strip.cyclePeakSymbols()
        except:
            getLogger().warning('Error cycling peak symbols')

    @logCommand(get='self')
    def displaySpectrum(self, spectrum):
        """Display spectrum, with spectrum axes ordered according to display axisCodes
        :return SpectrumView instance or None
        """
        from ccpn.ui._implementation.SpectrumView import _newSpectrumView

        spectrum = self.getByPid(spectrum) if isinstance(spectrum, str) else spectrum
        if not isinstance(spectrum, Spectrum):
            raise TypeError('spectrum is not of type Spectrum')

        if self.is1D and spectrum.dimensionCount > 1:
            raise RuntimeError('Cannot display nD spectrum on %s' % self)

        if not self.is1D and spectrum.dimensionCount == 1:
            raise RuntimeError('Cannot display 1D spectrum on %s' % self)

        # check if not already here
        _specViews = self.getSpectrumViewFromSpectrum(spectrum)
        if len(_specViews) > 0:
            getLogger().debug('displaySpectrum: Spectrum %s already in display %s' % (spectrum, self))
            return _specViews[0]

        # keep this as may be needed for undo/redo gui operations
        # with undoStackBlocking() as _:  # Do not add to undo/redo stack
        #     # _getDimensionsMapping will check the match for axisCodes
        #     displayOrder = (1, 0) if self.is1D else self._getDimensionsMapping(spectrum)
        #     # check the isotopeCodes
        #     dims = displayOrder[0:1] if self.is1D else displayOrder
        #     # check the isotopeCodes exist and check compatibility
        #     for ic1, ic2 in zip(self.isotopeCodes or [], spectrum.getByDimensions('isotopeCodes', dims)):
        #         if ic1 != ic2:
        #             raise RuntimeError('Cannot display %s on %s; incompatible isotopeCodes' % (spectrum, self))

        # with undoStackRevert(self.application) as revertStack:
        with undoBlockWithoutSideBar(self.application):
            # push/pop ordering
            with undoStackBlocking(self.application) as addUndoItem:

                # _getDimensionsMapping will check the match for axisCodes
                displayOrder = (1, 0) if self.is1D else self._getDimensionsMapping(spectrum)
                # dimensions are 1-based and not defined for (1D) Intensity axis
                dims = [1] if self.is1D else displayOrder

                if not self._isNew:
                    # There is already a spectrum displayed; ie. the spectrumDisplay has definitions for
                    # its x,y, and z,a,.. plane(s) display axes

                    # check for matching dimension types
                    for dt1, dt2 in zip(self.dimensionTypes or [], spectrum.getByDimensions('dimensionTypes', dims)):
                        if dt1 != dt2:
                            raise RuntimeError('Cannot display %s on %s; incompatible dimensionTypes' % (spectrum, self))
                        # For now: no multiple spectra with time/sampled axes (current implementation limit)
                        if dt2 == DIMENSION_SAMPLED or dt2 == DIMENSION_TIME:
                            raise RuntimeError('Currently cannot display %s with "%s" axis on %s; SpectrumDisplay already contains other spectra with time/sampled axes' %
                                               (spectrum, dt2, self))

                    # check the isotopeCodes exist and check compatibility
                    for ic1, ic2 in zip(self.isotopeCodes or [], spectrum.getByDimensions('isotopeCodes', dims)):
                        if ic1 != ic2:
                            raise RuntimeError('Cannot display %s on %s; incompatible isotopeCodes' % (spectrum, self))

                # # add toolbar ordering to the undo stack
                # addUndoItem(undo=self.setToolbarButtons)  # keep for undo/redo

                # Make spectrumView
                if (spectrumView := _newSpectrumView(self, spectrum=spectrum, displayOrder=displayOrder)) \
                        is None:
                    # notify the stack to revert to the pre-context manager stack
                    # revertStack(True)
                    getLogger().warning(f'Could not create new spectrumView for {spectrum}')

                else:
                    self.setToolbarButtons()
                    # addUndoItem(redo=self.setToolbarButtons)  # keep for undo/redo

        if not self._isNew:
            # Now that the spectrum is added, we need to update the plane-related
            # axis values
            for strip in self.strips:
                strip._updatePlaneAxes()

        return spectrumView

    @logCommand(get='self')
    def removeSpectrum(self, spectrum):
        """Remove a spectrum from the spectrumDisplay
        """
        spectrum = self.project.getByPid(spectrum) if isinstance(spectrum, str) else spectrum
        if not isinstance(spectrum, Spectrum):
            raise TypeError('spectrum must be of type Spectrum/str')

        # get the spectrumViews from the first strip
        sv = [(spectrum, specView) for specView in self.strips[0].spectrumViews if specView.spectrum == spectrum]
        if len(sv) != 1:
            return

        _spectrum, specView = sv[0]
        uniqueViews = set(sv.spectrum for sv in self.spectrumViews)
        if len(uniqueViews) == 1 and spectrum in uniqueViews and \
                self.application.preferences.appearance.closeSpectrumDisplayOnLastSpectrum:
            self.close()
            return

        # # for debugger
        # _undo = self.application._getUndo()

        with undoStackBlocking() as _:  # NOTE:ED - Do not add to undo/redo stack

            # need undo waypoint here
            with waypointBlocking():
                with undoStackBlocking() as addUndoItem:
                    # refresh on undo - why was this here anyway :|
                    # _data = {Notifier.OBJECT:specView,
                    #          Notifier.TRIGGER:Notifier.CREATE
                    #          }
                    # addUndoItem(undo=partial(self._spectrumViewChanged, _data)
                    #             )

                    # push/pop ordering
                    addUndoItem(undo=self.setToolbarButtons)

                # delete the spectrumView -
                # for multiple strips will delete all spectrumViews attached to spectrum
                specView._delete()

                with undoStackBlocking() as addUndoItem:
                    # push ordering
                    self.setToolbarButtons()
                    addUndoItem(redo=self.setToolbarButtons)

        #end waypoint
        return

    def _setVisibleSpectrum(self, spectrum, visible: bool):
        """ Set visible the spectrumView of the spectrum in the spectrumDisplay.
        """
        for specView in self.strips[0].spectrumViews:
            if specView.spectrum == spectrum:
                specView.setVisible(visible)

    def setVisibleSpectrum(self, spectrum, visible):
        """
        Toggle on/off a spectrum from the visible spectra
        :param spectrum:
        :param visible: bool. True to show, False to hide
        :return:
        """
        with undoStackBlocking(self.application) as addUndoItem:
            self._setVisibleSpectrum(spectrum, visible)
            addUndoItem(
                    undo=partial(self._setVisibleSpectrum, spectrum, not visible),
                    redo=partial(self._setVisibleSpectrum, spectrum, visible))

    def setToolbarButtons(self):
        """Setup the buttons in the toolbar for each spectrum
        """
        if not self.isGrouped and self.strips:
            self.spectrumToolBar.setButtonsFromSpectrumViews(self.strips[0].getSpectrumViews())

    @logCommand(get='self')
    def makeStripPlot(self, peaks=None, nmrResidues=None,
                      autoClearMarks=True,
                      sequentialStrips=True,
                      markPositions=True,
                      widths=None):
        """Make a list of strips in the current spectrumDisplay based on the list of peaks or
        the list of nmrResidues passing in
        Can only choose either peaks or nmrResidues, peaks chosen will override any selected nmrResidues
        """
        pkList = makeIterableList(peaks)
        pks = []
        for peak in pkList:
            pks.append(self.project.getByPid(peak) if isinstance(peak, str) else peak)

        resList = makeIterableList(nmrResidues)
        nmrs = []
        for nmrRes in resList:
            if not nmrRes.relativeOffset:  # is not None and nmrResidue.relativeOffset
                nmrs.append(self.project.getByPid(nmrRes) if isinstance(nmrRes, str) else nmrRes)

        # need to clean up the use of GLNotifier - possibly into AbstractWrapperObject
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier
        # from functools import partial
        # from ccpn.ui.gui.lib.Strip import navigateToPositionInStrip, navigateToNmrAtomsInStrip
        from ccpn.ui.gui.lib.SpectrumDisplayLib import navigateToPeakInStrip, navigateToNmrResidueInStrip

        def _updateGl(self, spectrumList):
            GLSignals = GLNotifier(parent=self)
            GLSignals.emitPaintEvent()

        if pks or nmrs:

            GLSignals = GLNotifier(parent=self)
            _undo = self.project._undo

            project = self.project
            # with logCommandBlock(get='self') as log:
            #     peakStr = '[' + ','.join(["'%s'" % peak.pid for peak in pks]) + ']'
            #     nmrResidueStr = '[' + ','.join(["'%s'" % nmrRes.pid for nmrRes in nmrs]) + ']'
            #     log('addPeaks', peaks=peakStr, nmrResidues=nmrResidueStr)

            # with undoBlockWithoutSideBar():
            with undoStackBlocking() as _:  # Do not add to undo/redo stack
                # _undo._newItem(undoPartial=partial(_updateGl, self, []))

                if autoClearMarks:
                    self.mainWindow.clearMarks()

                # Make sure there are enough strips to display nmrAtomPairs
                stripCount = len(pks) if pks else len(nmrs)
                while len(self.strips) < stripCount:
                    self.addStrip()
                for strip in self.strips[stripCount:]:
                    self.deleteStrip(strip)

                # build the strips
                if pks:
                    for ii, pk in enumerate(pks):
                        strip = self.strips[ii]
                        navigateToPeakInStrip(self, strip, pk, markPositions=markPositions)

                elif nmrs:
                    for ii, nmr in enumerate(nmrs):
                        strip = self.strips[ii]
                        navigateToNmrResidueInStrip(self, strip, nmr, widths, markPositions=markPositions)

                # _undo._newItem(redoPartial=partial(_updateGl, self, []))

                # repaint - not sure whether needed here
                GLSignals.emitPaintEvent()

    @contextmanager
    def _hideWidget(self, widget):
        """ A decorator to hide/show the widget
        """
        # store visibility
        _visible = widget.isVisible()
        widget.setVisible(False)
        try:
            # transfer control to the calling function
            yield

        except Exception as es:
            raise es

        finally:
            widget.setVisible(_visible)

    def attachZPlaneWidgets(self):
        """Attach the strip zPlane navigation widgets for the strips to the correct containers
        """
        if self.is1D or len(self.axisCodes) <= 2:
            return

        try:
            _currentStrip = self.application.current.strip
        except:
            pass
        else:

            # update the settings widget
            self._spectrumDisplaySettings.setZPlaneButtons(self.zPlaneNavigationMode)

            with self._hideWidget(self.mainWidget):

                if self.zPlaneNavigationMode == ZPlaneNavigationModes.PERSPECTRUMDISPLAY.dataValue:

                    for strip in self.strips:
                        if strip and not strip.isDeleted:
                            strip.zPlaneFrame.setVisible(False)
                            strip.zPlaneFrame._strip = None
                            for pl in strip.planeAxisBars:
                                # reattach the widget to the in strip container
                                pl._attachButton('_axisSelector')
                                pl._hideAxisSelector()

                    _currentStrip = _currentStrip if _currentStrip in self.strips else (self.strips[0] if self.strips else None)
                    if _currentStrip:
                        self.zPlaneFrame.attachZPlaneWidgets(_currentStrip)
                    self.zPlaneFrame.setVisible(True)

                if self.zPlaneNavigationMode == ZPlaneNavigationModes.PERSTRIP.dataValue:
                    self.zPlaneFrame.setVisible(False)
                    self.zPlaneFrame._strip = None
                    for strip in self.strips:
                        if strip and not strip.isDeleted:
                            for pl in strip.planeAxisBars:
                                # reattach the widget to the in strip container
                                pl._attachButton('_axisSelector')
                                pl._hideAxisSelector()

                            strip.zPlaneFrame.attachZPlaneWidgets(strip)
                            strip.zPlaneFrame.setVisible(True)

                if self.zPlaneNavigationMode == ZPlaneNavigationModes.INSTRIP.dataValue:
                    for strip in self.strips:
                        if strip and not strip.isDeleted:
                            strip.zPlaneFrame.setVisible(False)
                            strip.zPlaneFrame._strip = None
                            for pl in strip.planeAxisBars:
                                # reattach the widget to the in strip container
                                pl._attachButton('_axisSelector')
                                pl._hideAxisSelector()

                    self.zPlaneFrame.setVisible(False)
                    self.zPlaneFrame._strip = None

        self.update()

    def _highlightAxes(self, strip, state):
        """Highlight the last row axis if strip
        """
        _row = self.stripRow(0)
        if _row and len(_row) > 1 and (_row[-1] == strip):
            self._rightGLAxis.highlightCurrentStrip(state)
            self._bottomGLAxis.highlightCurrentStrip(state)

    def clearContourAttributes(self):
        """Clear all the contour attributes associated with the spectrumViews in the spectrumDisplay
        Attributes will revert to the spectrum values
        """
        with undoBlockWithoutSideBar():
            for specView in self.spectrumViews:
                specView.clearContourAttributes()

    def copyContourAttributesFromSpectra(self):
        """Copy all the contour attributes associated with a spectrumView.spectrum
        to the spectrumView for all spectrumViews in the spectrumDisplay
        """
        with undoBlockWithoutSideBar():
            for specView in self.spectrumViews:
                specView.copyContourAttributesFromSpectrum()

    def adjustContours(self):
        """Initiate a popup to modify  settings
        """
        # GWV: Very strange (name for 1D!)
        # Should it be here?; called from GuiMainWindow TODO: move there?
        if self.is1D:
            from ccpn.ui.gui.popups.SpectrumPropertiesPopup import SpectrumDisplayPropertiesPopup1d as Popup

        else:
            from ccpn.ui.gui.popups.SpectrumPropertiesPopup import SpectrumDisplayPropertiesPopupNd as Popup

        if self.strips:
            popup = Popup(parent=self.mainWindow, mainWindow=self.mainWindow,
                          orderedSpectrumViews=self.strips[0].getSpectrumViews())
            popup.exec_()

    def _rebuildContours(self):
        """Rebuild the contours (nD only)
        """
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        if self.is1D:
            return

        GLSignals = GLNotifier(parent=self)

        for specViews in self.spectrumViews:
            specViews.buildContoursOnly = True

        # repaint
        GLSignals.emitPaintEvent()

    def _loopOverSpectrumViews(self):
        """A generator object to loop over all spectrumViews,
        visiting spectrum only once. Also initiates an undo block
        :yields SpectrumView instance
        """
        modifiedSpectra = set()
        with undoBlockWithoutSideBar():
            for spectrumView in self.spectrumViews:
                if spectrumView.isDisplayed:
                    spectrum = spectrumView.spectrum

                    # only increase once - duh
                    if spectrum in modifiedSpectra:
                        continue

                    else:
                        yield spectrumView

                    modifiedSpectra.add(spectrum)

    # @logCommand(get='self')
    def _raiseContourBase(self):
        """
        Increases contour base level for all spectra visible in the display (nD Only).
        """
        if self.is1D:
            return

        for spectrumView in self._loopOverSpectrumViews():
            spectrum = spectrumView.spectrum
            if spectrum.positiveContourBase == spectrumView.positiveContourBase:
                # We want to set the base for ALL spectra
                # and to ensure that any private settings are overridden for this display
                # setting to None forces the spectrumVIew to access the spectrum attributes
                spectrumView.positiveContourBase = None
                spectrumView.positiveContourFactor = None
                spectrum.positiveContourBase *= spectrum.positiveContourFactor
            else:
                # Display has custom contour base - change that one only
                spectrumView.positiveContourBase *= spectrumView.positiveContourFactor

            if spectrum.negativeContourBase == spectrumView.negativeContourBase:
                # We want to set the base for ALL spectra
                # and to ensure that any private settings are overridden for this display
                spectrumView.negativeContourBase = None
                spectrumView.negativeContourFactor = None
                spectrum.negativeContourBase *= spectrum.negativeContourFactor
            else:
                # Display has custom contour base - change that one only
                spectrumView.negativeContourBase *= spectrumView.negativeContourFactor

    # @logCommand(get='self')
    def _lowerContourBase(self):
        """
        Decreases contour base level for all spectra visible in the display (nD only).
        """
        if self.is1D:
            return

        for spectrumView in self._loopOverSpectrumViews():
            spectrum = spectrumView.spectrum

            if spectrum.positiveContourBase == spectrumView.positiveContourBase:
                # We want to set the base for ALL spectra
                # and to ensure that any private settings are overridden for this display
                spectrumView.positiveContourBase = None
                spectrumView.positiveContourFactor = None
                spectrum.positiveContourBase /= spectrum.positiveContourFactor
            else:
                # Display has custom contour base - change that one only
                spectrumView.positiveContourBase /= spectrumView.positiveContourFactor

            if spectrum.negativeContourBase == spectrumView.negativeContourBase:
                # We want to set the base for ALL spectra
                # and to ensure that any private settings are overridden for this display
                spectrumView.negativeContourBase = None
                spectrumView.negativeContourFactor = None
                spectrum.negativeContourBase /= spectrum.negativeContourFactor
            else:
                # Display has custom contour base - change that one only
                spectrumView.negativeContourBase /= spectrumView.negativeContourFactor

    # @logCommand(get='self')
    def _addContourLevel(self):
        """
        Increases number of contours by 1 for all spectra visible in the display (nD only).
        """
        if self.is1D:
            return

        for spectrumView in self._loopOverSpectrumViews():
            spectrum = spectrumView.spectrum

            if spectrum.positiveContourCount == spectrumView.positiveContourCount:
                # We want to set the base for ALL spectra
                # and to ensure that any private settings are overridden for this display
                spectrumView.positiveContourCount = None
                spectrum.positiveContourCount += 1
            else:
                # Display has custom contour count - change that one only
                spectrumView.positiveContourCount += 1

            if spectrum.negativeContourCount == spectrumView.negativeContourCount:
                # We want to set the base for ALL spectra
                # and to ensure that any private settings are overridden for this display
                spectrumView.negativeContourCount = None
                spectrum.negativeContourCount += 1
            else:
                # Display has custom contour count - change that one only
                spectrumView.negativeContourCount += 1

    # @logCommand(get='self')
    def _removeContourLevel(self):
        """
        Decreases number of contours by 1 for all spectra visible in the display (nD only).
        """
        if self.is1D:
            return

        for spectrumView in self._loopOverSpectrumViews():
            spectrum = spectrumView.spectrum

            if spectrum.positiveContourCount == spectrumView.positiveContourCount:
                # We want to set the base for ALL spectra
                # and to ensure that any private settings are overridden for this display
                spectrumView.positiveContourCount = None
                if spectrum.positiveContourCount:
                    spectrum.positiveContourCount -= 1
            else:
                # Display has custom contour count - change that one only
                if spectrumView.positiveContourCount:
                    spectrumView.positiveContourCount -= 1

            if spectrum.negativeContourCount == spectrumView.negativeContourCount:
                # We want to set the base for ALL spectra
                # and to ensure that any private settings are overridden for this display
                spectrumView.negativeContourCount = None
                if spectrum.negativeContourCount:
                    spectrum.negativeContourCount -= 1
            else:
                # Display has custom contour count - change that one only
                if spectrumView.negativeContourCount:
                    spectrumView.negativeContourCount -= 1

    def updateTraces(self):
        for strip in self.strips:
            strip._updateTraces()

    @logCommand(get='self')
    def newMark(self, colour: str, positions: Sequence[float], axisCodes: Sequence[str],
                style: str = 'simple', units: Sequence[str] = (), labels: Sequence[str] = ()):
        """Create new Mark in a strip.

        :param str colour: Mark colour.
        :param tuple/list positions: Position in unit (default ppm) of all lines in the mark.
        :param tuple/list axisCodes: Axis codes for all lines in the mark.
        :param str style: Mark drawing style (dashed line etc.) default: full line ('simple').
        :param tuple/list units: Axis units for all lines in the mark, Default: all ppm.
        :param tuple/list labels: Ruler labels for all lines in the mark. Default: None.
        :return a new Mark instance.
        """
        from ccpn.ui._implementation.Mark import _newMark, _removeMarkAxes

        with undoBlockWithoutSideBar():
            if marks := _removeMarkAxes(self, positions=positions, axisCodes=axisCodes, labels=labels):
                pos, axes, lbls = marks
                if not pos:
                    return

                result = _newMark(self.mainWindow, colour=colour, positions=pos, axisCodes=axes,
                                  style=style, units=units, labels=lbls,
                                  )
                # add spectrumDisplay to the new mark
                result.spectrumDisplays = [self]

                return result

#=========================================================================================


#GuiSpectrumDisplay.processSpectrum = GuiSpectrumDisplay.displaySpectrum  # ejb - from SpectrumDisplay
