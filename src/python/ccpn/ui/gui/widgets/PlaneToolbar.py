"""
This module defines a specific Toolbar class for the strip display 
The NmrResidueLabel allows drag and drop of the ids displayed in them

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
__dateModified__ = "$dateModified: 2024-08-23 19:21:21 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import contextlib
from functools import partial
from PyQt5.QtCore import pyqtSlot
# import json
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.DoubleSpinbox import DoubleSpinbox
from ccpn.ui.gui.widgets.Label import Label, ActiveLabel
from ccpn.ui.gui.widgets.Spinbox import Spinbox
# from ccpn.ui.gui.widgets.ToolBar import ToolBar
# from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.Frame import Frame, OpenGLOverlayFrame
from ccpn.ui.gui.guiSettings import HIGHLIGHT, HEXFOREGROUND, ZPlaneNavigationModes
# from ccpn.ui.gui.guiSettings import textFont, textFontLarge
from ccpn.ui.gui.widgets.Font import getFontHeight
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.lib.mouseEvents import getMouseEventDict
from PyQt5 import QtWidgets, QtCore
from ccpn.core.Peak import Peak
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.lib.Notifiers import Notifier
from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier
from ccpn.ui.gui.lib.mouseEvents import makeDragEvent
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.util.Logging import getLogger
from ccpn.util.Constants import AXISUNIT_POINT
from ccpn.core.lib.SpectrumLib import DIMENSION_TIME


STRIPLABEL_CONNECTDIR = '_connectDir'
STRIPLABEL_CONNECTNONE = 'none'
SINGLECLICK = 'click'
DOUBLECLICK = 'doubleClick'


class _StripLabel(ActiveLabel):  #  VerticalLabel): could use Vertical label so that the strips can flip
    """
    Specific Label to be used in Strip displays
    """

    # ED: This class contains the best current method for handling single and double click events
    # without any clashes between events, and creating a dragged item
    DOUBLECLICKENABLED = False

    def __init__(self, parent, mainWindow, strip=None, text=None, dragKey=DropBase.PIDS, stripArrangement=None, **kwds):

        super().__init__(parent, text, **kwds)
        # The text of the label can be dragged; it will be passed on in the dict under key dragKey

        self._parent = parent
        self.strip = strip
        self.spectrumDisplay = self.strip.spectrumDisplay if strip else None
        self.mainWindow = mainWindow
        self.application = mainWindow.application
        self.project = mainWindow.project

        self._dragKey = dragKey
        self.setAcceptDrops(True)
        # self.setDragEnabled(True)           # not possible for Label

        self._lastClick = None
        self._mousePressed = False
        self.stripArrangement = stripArrangement
        # self.setOrientation('vertical' if stripArrangement == 'X' else 'horizontal')

        # disable any drop event callback's until explicitly defined later
        self.setDropEventCallback(None)

    def _createDragEvent(self, mouseDict):
        """
        Re-implementation of the mouse press event to enable a NmrResidue label to be dragged as a json object
        containing its id and a modifier key to encode the direction to drop the strip.
        """
        if not self.project.getByPid(self.text()):
            # label does not point to an object
            getLogger().warning(f'{self.text()} is not a draggable object')
            return

        # mimeData = QtCore.QMimeData()
        # create the dataDict
        dataDict = {self._dragKey: [self.text()],
                    DropBase.TEXT: self.text()
                    }
        connectDir = self._connectDir if hasattr(self, STRIPLABEL_CONNECTDIR) else STRIPLABEL_CONNECTNONE
        dataDict[STRIPLABEL_CONNECTDIR] = connectDir

        # update the dataDict with all mouseEvents{"controlRightMouse": false, "text": "NR:@-.@27.", "leftMouse": true, "controlShiftMiddleMouse": false, "middleMouse": false, "controlMiddleMouse": false, "controlShiftLeftMouse": false, "controlShiftRightMouse": false, "shiftMiddleMouse": false, "_connectDir": "isRight", "controlLeftMouse": false, "rightMouse": false, "shiftLeftMouse": false, "shiftRightMouse": false}
        dataDict.update(mouseDict)

        makeDragEvent(self, dataDict, [self.text()], self.text())

    def event(self, event):
        """
        Process all events in the event handler
        Not sure if this is the best solution, but doesn't interfere with _processDroppedItems
        and allows changing of the cursor (cursor not always changing properly in pyqt5) - ejb
        """
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # process the single click event
            self._mousePressEvent(event)
            return True

        if event.type() == QtCore.QEvent.MouseButtonDblClick:
            # process the doubleClick event
            self._mouseButtonDblClick(event)
            return True

        if event.type() == QtCore.QEvent.MouseButtonRelease:
            # process the mouse release event
            self._mouseReleaseEvent(event)
            return True

        return super().event(event)

    def _mousePressEvent(self, event):
        """Handle mouse press event for single click and beginning of mouse drag event
        """
        self._mousePressed = True
        if not self._lastClick:
            self._lastClick = SINGLECLICK

        if self._lastClick == SINGLECLICK:
            mouseDict = getMouseEventDict(event)

            # set up a singleShot event, but a bit quicker than the normal interval (which seems a little long)
            QtCore.QTimer.singleShot(QtWidgets.QApplication.instance().doubleClickInterval() // 2,
                                     partial(self._handleMouseClicked, mouseDict))

        elif self._lastClick == DOUBLECLICK:
            self._lastClick = None

    def _mouseButtonDblClick(self, event):
        """Handle mouse doubleCLick
        """
        self._lastClick = DOUBLECLICK
        if self.DOUBLECLICKENABLED:
            self._processDoubleClick(self.text())

    def _mouseReleaseEvent(self, event):
        """Handle mouse release
        """
        self._mousePressed = False
        if event.button() == QtCore.Qt.RightButton:
            # NOTE:ED - popup 'close headers' not required now
            self._rightButtonPressed(event)

        elif event.button() == QtCore.Qt.LeftButton:
            # get the keyboard state
            keyModifiers = QtWidgets.QApplication.keyboardModifiers()
            if (keyModifiers & QtCore.Qt.ShiftModifier):
                # toggle the pin state
                self._pinStripToggle()

    def _handleMouseClicked(self, mouseDict):
        """handle a single mouse event, but ignore double click events
        """
        if self._lastClick == SINGLECLICK and self._mousePressed:
            self._createDragEvent(mouseDict)
        self._lastClick = None

    def _processDoubleClick(self, obj):
        """Process the doubleClick event, action the clicked stripHeader in the selected strip
        """
        from ccpn.ui.gui.lib.SpectrumDisplayLib import navigateToPeakInStrip, navigateToNmrResidueInStrip

        obj = self.project.getByPid(obj) if isinstance(obj, str) else obj
        if obj:
            spectrumDisplays = self.spectrumDisplay._spectrumDisplaySettings.displaysWidget._getDisplays()
            for specDisplay in spectrumDisplays:

                if specDisplay.strips:
                    if isinstance(obj, Peak):
                        navigateToPeakInStrip(specDisplay, specDisplay.strips[0], obj)

                    elif isinstance(obj, NmrResidue):
                        navigateToNmrResidueInStrip(specDisplay, specDisplay.strips[0], obj)

    def _rightButtonPressed(self, event):
        """Handle pressing the right mouse button
        """
        menu = self._createContextMenu(self)
        if menu:
            menu.move(event.globalPos().x(), event.globalPos().y() + 10)
            menu.exec()

    def _createContextMenu(self, button: QtWidgets.QToolButton):
        """Creates a context menu to close headers.
        """
        contextMenu = Menu('', self, isFloatWidget=True)

        contextMenu.addSeparator()
        contextMenu.addAction('Pin/Unpin Strip', self._pinStripToggle)
        contextMenu.addAction('Unpin Other Strips', self._removePins)
        contextMenu.addAction('Unpin All Strips', self._removeAllPins)

        contextMenu.addSeparator()
        contextMenu.addAction('Close Strip', self._closeStrip)
        contextMenu.addAction('Close Other Strips', partial(self._closeOther, left=True, right=True))
        contextMenu.addAction('Close Strips to the Left', partial(self._closeOther, left=True))
        contextMenu.addAction('Close Strips to the Right', partial(self._closeOther, right=True))
        contextMenu.addAction('Close All but Pinned', self._closeUnpinned)

        return contextMenu

    def _pinStripToggle(self):
        """Toggle the pinned state of the strip.
        """
        if this := self._parent.strip:
            this.pinned = not this.pinned

    def _closeStrip(self):
        """Close this strip.
        """
        if this := self._parent.strip:
            this.spectrumDisplay.deleteStrip(self._parent.strip)

    def _closeOther(self, left=False, right=False):
        """Close strips to the left or right.
        """
        if this := self._parent.strip:
            spDisplay = this.spectrumDisplay
            strips = spDisplay.orderedStrips
            ind = strips.index(this)
            leftStrips = strips[:ind]
            rightStrips = strips[ind + 1:]

            if left:
                for strip in leftStrips:
                    spDisplay.deleteStrip(strip)
            if right:
                for strip in rightStrips:
                    spDisplay.deleteStrip(strip)

    def _closeUnpinned(self):
        """Close the unpinned strips in the spectrumDisplay.
        """
        if this := self._parent.strip:
            spDisplay = this.spectrumDisplay
            for strip in spDisplay.strips:
                if not strip.pinned:
                    spDisplay.deleteStrip(strip)

    def _removePins(self):
        """Remove pins from all other strips.
        """
        if this := self._parent.strip:
            for st in self.project.strips:
                if st != this:
                    st.pinned = False

    def _removeAllPins(self):
        """Remove pins from all strips.
        """
        if self._parent.strip:
            for st in self.project.strips:
                st.pinned = False


#TODO:GEERTEN: complete this and replace
class PlaneSelectorWidget(Frame):
    """
    This widget contains the buttons and entry boxes for selection of the plane
    """

    def __init__(self, qtParent, mainWindow=None, strip=None, axis=None, **kwds):
        """Setup the buttons and callbacks for axis
        """
        super().__init__(parent=qtParent, setLayout=True, **kwds)

        self.mainWindow = mainWindow
        self.project = mainWindow.project
        self.strip = strip
        self.axis = axis

        self._linkedSpinBox = None
        self._linkedPlaneCount = None

        _size = getFontHeight(size='MEDIUM')

        self._mainWidget = Frame(self, setLayout=True, showBorder=False, grid=(0, 0))

        self.previousPlaneButton = Button(parent=self._mainWidget, text='<', grid=(0, 0),
                                          callback=self._previousPlane)

        self.spinBox = DoubleSpinbox(parent=self._mainWidget, showButtons=False, grid=(0, 1), decimals=3,
                                     objectName='PlaneSelectorWidget_planeDepth',
                                     )
        self.spinBox.setFixedWidth(_size * 5)

        self.spinBox.returnPressed.connect(self._spinBoxChanged)
        self.spinBox.wheelChanged.connect(self._spinBoxChanged)

        self.nextPlaneButton = Button(parent=self._mainWidget, text='>', grid=(0, 2),
                                      callback=self._nextPlane)

        self.planeCountSpinBox = Spinbox(parent=self._mainWidget, showButtons=False, grid=(0, 3), min=1, max=1000,
                                         objectName='PlaneSelectorWidget_planeCount'
                                         )
        self.planeCountSpinBox.setFixedWidth(int(_size * 2.5))

        self.planeCountSpinBox.returnPressed.connect(self._planeCountChanged)
        self.planeCountSpinBox.wheelChanged.connect(self._planeCountChanged)

        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

    def _initialise(self, strip=None, axis=None):
        """Set the initial values for the plane selector
        """
        from ccpn.ui.gui.lib.GuiStrip import GuiStrip

        strip = self.project.getByPid(strip) if isinstance(strip, str) else strip
        if not isinstance(strip, GuiStrip):
            raise TypeError(f"{str(strip)} is not of type Strip")
        if not isinstance(axis, int):
            raise TypeError(f"{str(axis)} is not of type int")
        if not (0 <= axis < len(strip.axisCodes)):
            raise ValueError("axis %s is out of range (0, %i)" % (str(axis), len(self.axisCodes) - 1))

        self.strip = strip
        self.axis = axis

        self.spinBox.setToolTip(str(self.strip.axisCodes[self.axis]))

    def setCallbacks(self, callbacks):
        """callbacks a dict with (key, callbackFunction) items."""
        self._callbacks = callbacks

    def _planeCountChanged(self, value: int = 1):
        """Changes the number of planes displayed simultaneously.
        """
        if self.strip:
            self._callbacks['_planeCountChanged'](value)

    def _nextPlane(self, *args):
        """Increases axis ppm position by one plane
        """
        self.project._buildWithProfile = False
        if self.strip:
            self._callbacks['_nextPlane'](*args)

    def _previousPlane(self, *args):
        """Decreases axis ppm position by one plane
        """
        if self.strip:
            self._callbacks['_previousPlane'](*args)

    def _spinBoxChanged(self, value: float):
        """Sets the value of the axis plane position box if the specified value is within the displayable limits.
        """
        if self.strip:
            self._callbacks['_spinBoxChanged'](value)

    def _wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            if self.strip.prevPlaneCallback:
                self.strip.prevPlaneCallback(self.axis)
        else:
            if self.strip.nextPlaneCallback:
                self.strip.nextPlaneCallback(self.axis)

        self.strip.refresh()

    def setPosition(self, ppmPosition, ppmWidth):
        """Set the new ppmPosition/ppmWidth
        """
        with self.blockWidgetSignals():
            self.spinBox.setValue(ppmPosition)

    def setPlaneValues(self, planeSize=None, minValue=None, maxValue=None, value=None, unit=None):
        """Set new values for the plane selector
        """
        with self.blockWidgetSignals(root=self._mainWidget):
            # block signals while setting contents
            self.spinBox.setSingleStep(planeSize)
            if maxValue is not None:
                self.spinBox.setMaximum(maxValue)
            if minValue is not None:
                self.spinBox.setMinimum(minValue)

            # override the spinBox to only allow integer points
            self.spinBox.setDecimals(0 if unit == AXISUNIT_POINT else 3)
            if value is not None:
                self.spinBox.setValue(value)

    def getPlaneValues(self):
        """Return the current settings for this axis
        :returns: (minValue, maxValue, stepSize, value, planeCount) tuple
        """
        return self.spinBox.minimum(), self.spinBox.maximum(), self.spinBox.singleStep(), self.spinBox.value(), self.planeCount

    @property
    def planeCount(self):
        """Return the plane count for this axis
        """
        return self.planeCountSpinBox.value()


class _OpenGLFrameABC(OpenGLOverlayFrame):
    """
    OpenGL ABC for items to overlay the GL frame (until a nicer way can by found)

    BUTTONS is a tuple of tuples of the form:

        ((attributeName, widgetType, init function, set attrib function)
         ...
         )

        attributeName is a string defining the attribute in the container
        widgetType is the type of widget, e.g. see PlaneAxisWidget
        init functions are called after instantiation of widgets
            - typically static functions of the form <name>(self, widget, ...)
                self is the container class, widget is the widget object
        attrib functions are called from _populate to populate the widgets after changes
            (or possibly revert - not fully implemented yet)

    """
    BUTTONS = ()
    AUTOFILLBACKGROUND = True

    def __init__(self, qtParent, mainWindow, *args, **kwds):

        super().__init__(parent=qtParent, setLayout=True, **kwds)

        self.mainWindow = mainWindow
        self.project = mainWindow.project
        self._initFuncList = ()
        self._setFuncList = ()

        if not self.BUTTONS:
            # MUST BE SUBCLASSED
            raise NotImplementedError("Code error: BUTTONS not implemented")

        # build the list of widgets in frame
        row = col = 0
        for buttonDef in self.BUTTONS:

            if buttonDef:
                widgetName, widgetType, initFunc, setFunc, grid, gridSpan = buttonDef

                if not widgetType:
                    raise TypeError('Error: button widget not defined')

                # if widget is given then add to the container
                widget = widgetType(self, mainWindow=mainWindow, grid=grid, gridSpan=gridSpan)  #grid=(row, col), gridSpan=(1, 1))
                self._setStyle(widget)
                if initFunc:
                    self._initFuncList += ((initFunc, self, widget),)
                if setFunc:
                    self._setFuncList += ((setFunc, self, widget),)

                # add the widget here
                setattr(self, widgetName, widget)
                col += 1
            else:

                # else, move to the next row (simple newLine)
                row += 1
                col = 0

        # add an expanding widget to the end of the row
        Spacer(self, 2, 2, QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum,
               grid=(0, col + 1), gridSpan=(1, 1))

        # initialise the widgets
        for func, klass, widget in self._initFuncList:
            func(klass, widget, *args)

        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

    def _attachButton(self, buttonName):
        """Reattach a button to the parent widget
        """
        for buttonDef in self.BUTTONS:

            if buttonDef:
                widgetName, widgetType, initFunc, setFunc, grid, gridSpan = buttonDef

                if not widgetType:
                    raise TypeError('Error: button widget not defined')

                if widgetName == buttonName:
                    button = getattr(self, buttonName, None)
                    if button:
                        button.layout().addWidget(button._mainWidget, 0, 0)
                        button._mainWidget.setParent(button)

    def _populate(self):
        for pp, klass, widget in self._setFuncList:
            pp(self, klass, widget)


EMITSOURCE = 'source'
EMITCLICKED = 'clicked'
EMITIGNORESOURCE = 'ignoreSource'


class PlaneAxisWidget(_OpenGLFrameABC):
    """
    Need Frame:
        AxisCode label

        AxisValue

            Frame

                Change arrow
                value box
                Change arrow

                planes box

    """

    def _setAxisCode(self, *args):
        pass

    def _setAxisPosition(self, *args):
        pass

    def _setPlaneCount(self, *args):
        pass

    def _setPlaneSelection(self, *args):
        pass

    def _initAxisCode(self, widget, strip, axis):
        pass

    def _initAxisPosition(self, widget, strip, axis):
        pass

    def _initPlaneCount(self, widget, strip, axis):
        pass

    def _initPlaneSelection(self, widget, strip, axis):
        self._postInit(widget, strip, axis)

    # define the buttons for the Plane axis widget
    BUTTONS = (('_axisLabel', ActiveLabel, _initAxisCode, _setAxisCode, (0, 0), (1, 1)),
               ('_axisPpmPosition', ActiveLabel, _initAxisPosition, _setAxisPosition, (0, 1), (1, 1)),
               ('_axisPlaneCount', ActiveLabel, _initPlaneCount, _setPlaneCount, (0, 2), (1, 1)),
               ('_axisSelector', PlaneSelectorWidget, _initPlaneSelection, _setPlaneSelection, (0, 3), (2, 1))
               )

    def __init__(self, qtParent, mainWindow, strip, axis, **kwds):
        super().__init__(qtParent, mainWindow, strip, axis, **kwds)

        self.strip = strip
        self.axis = axis

        axisButtons = (self._axisLabel, self._axisPpmPosition, self._axisPlaneCount, self._axisSelector)

        axisButtons[0].setSelectionCallback(partial(self._selectAxisCallback, axisButtons))
        for button in axisButtons[1:3]:
            button.setSelectionCallback(partial(self._selectPositionCallback, axisButtons))

        self._axisLabel.setVisible(True)
        self._axisPpmPosition.setVisible(True)
        self._axisPlaneCount.setVisible(True)
        self._axisSelector.setVisible(False)

        # self._axisSelector.spinBox.installEventFilter(self)

        # connect strip changed events to here
        self.strip.optionsChanged.connect(self._optionsChanged)
        self.mainWindow = mainWindow

    def _postInit(self, widget, strip, axis):
        """post-initialise functions
        CCPN-Internal to be called at the end of __init__
        Seems an awkward way of getting a generic post-init function but can't think of anything else yet
        """
        # assume that nothing has been set yet
        self._axisSelector._initialise(strip, axis)
        self._axisLabel.setText(f'{strip.axisCodes[axis]}:')
        self._axisLabel.setToolTip(strip.axisCodes[axis])
        callbacks = {
            '_previousPlane'    : self._previousPlane,
            '_spinBoxChanged'   : self._spinBoxChanged,
            '_nextPlane'        : self._nextPlane,
            '_planeCountChanged': self._planeCountChanged,
            '_wheelEvent'       : self._wheelEvent
            }
        self._axisSelector.setCallbacks(callbacks)
        # self._axisSelector.setCallbacks((self._previousPlane,
        #                                  self._spinBoxChanged,
        #                                  self._nextPlane,
        #                                  self._planeCountChanged,
        #                                  self._wheelEvent
        #                                  ))
        self._resize()

    def scrollPpmPosition(self, event):
        """Pass the wheel mouse event to the ppmPosition widget
        """
        self._axisSelector.spinBox._externalWheelEvent(event)

    @pyqtSlot(dict)
    def _optionsChanged(self, aDict):
        """Respond to signals from other frames in the strip
        """
        # may be required to select/de-select rows
        source = aDict.get(EMITSOURCE)
        ignore = aDict.get(EMITIGNORESOURCE)
        if source and not ((source == self) and ignore):
            # change settings here
            self._setLabelBorder(source == self)

    def _setLabelBorder(self, value):
        for label in (self._axisLabel, self._axisPpmPosition, self._axisPlaneCount):
            if value:
                self._setStyle(label, foregroundColour=HIGHLIGHT)
            else:
                self._setStyle(label, foregroundColour=HEXFOREGROUND)
            label.highlighted = value

    def _hideAxisSelector(self):
        widgets = (self._axisLabel, self._axisPpmPosition, self._axisPlaneCount, self._axisSelector)
        widgets[3].setVisible(False)
        widgets[2].setVisible(True)
        widgets[1].setVisible(True)
        self._resize()

    def _showAxisSelector(self):
        widgets = (self._axisLabel, self._axisPpmPosition, self._axisPlaneCount, self._axisSelector)
        widgets[3].setVisible(True)
        widgets[2].setVisible(False)
        widgets[1].setVisible(False)
        self._resize()

    def _selectAxisCallback(self, widgets):
        # if the first widget is clicked then change the selected axis
        if self.strip.spectrumDisplay.zPlaneNavigationMode == ZPlaneNavigationModes.INSTRIP.dataValue:
            if widgets[3].isVisible():
                widgets[3].setVisible(False)
                widgets[2].setVisible(True)
                widgets[1].setVisible(True)

        self._setLabelBorder(True)
        self.strip.activePlaneAxis = self.axis
        self.strip.optionsChanged.emit({EMITSOURCE      : self,
                                        EMITCLICKED     : True,
                                        EMITIGNORESOURCE: True})
        self._resize()

    def _selectPositionCallback(self, widgets):
        # if the other widgets are clicked then toggle the planeToolbar buttons
        if self.strip.spectrumDisplay.zPlaneNavigationMode == ZPlaneNavigationModes.INSTRIP.dataValue:
            if widgets[3].isVisible():
                widgets[3].setVisible(False)
                widgets[2].setVisible(True)
                widgets[1].setVisible(True)
            else:
                widgets[1].setVisible(False)
                widgets[2].setVisible(False)
                widgets[3].setVisible(True)

        self._setLabelBorder(True)
        self.strip.activePlaneAxis = self.axis
        self.strip.optionsChanged.emit({EMITSOURCE      : self,
                                        EMITCLICKED     : True,
                                        EMITIGNORESOURCE: True})
        self._resize()

    def setPosition(self, ppmPosition, ppmWidth):
        """Set the new ppmPosition/ppmWidth
        """
        self._axisSelector.setPosition(ppmPosition, ppmWidth)
        self._axisPpmPosition.setText('%.3f' % ppmPosition)

    def getPlaneValues(self):
        """Return the current settings for this axis
        :returns: ppmValue, maximum ppmValue, ppmStepSize, ppmPosition, planeCount
        """
        # self._axisSelector is a PlaneSelectorWidget
        return self._axisSelector.getPlaneValues()

    def setPlaneValues(self, planeSize=None, minValue=None, maxValue=None, value=None, unit=None):
        """Set new values for the plane selector
        """
        # self._axisSelector is a PlaneSelectorWidget
        planeSelectorWidget = self._axisSelector
        planeSelectorWidget.setPlaneValues(planeSize, minValue, maxValue, value, unit)

        self._axisPpmPosition.setText('%.3f' % value)
        self._axisPlaneCount.setText('[' + str(planeSelectorWidget.planeCount) + ']')

    @property
    def planeCount(self) -> int:
        return self._axisSelector.planeCount

    def _planeCountChanged(self, value: int = 1):
        """Changes the number of planes displayed simultaneously.
        """
        if self.strip:
            self.strip._changePlane(self.axis, planeIncrement=0, planeCount=self.planeCount)

    def _nextPlane(self, *args):
        """Increases axis position by one plane
        """
        with contextlib.suppress(Exception):
            if self.strip:
                # check the dimension-type of the current z-plane for the spectrum-display
                specView = self.strip.spectrumDisplay.spectrumViews[0]
                planeType = specView.dimensionTypes[self.axis]
                axisReversed = specView.spectrum.axesReversed[specView.dimensionIndices[self.axis]]

                # NOTE:ED - HACK for time-domain until slider is implemented, should it be the other direction?
                # decimals = self._axisSelector.spinBox.decimals()  <- more generic with decimals?
                step = 1 if planeType == DIMENSION_TIME else (-1 if axisReversed else 1)

                self.strip._changePlane(self.axis, planeIncrement=step, planeCount=self.planeCount,
                                        isTimeDomain=planeType == DIMENSION_TIME)

    def _previousPlane(self, *args):
        """Decreases axis position by one plane
        """
        with contextlib.suppress(Exception):
            if self.strip:
                # check the dimension-type of the current z-plane for the spectrum-display
                specView = self.strip.spectrumDisplay.spectrumViews[0]
                planeType = specView.dimensionTypes[self.axis]
                axisReversed = specView.spectrum.axesReversed[specView.dimensionIndices[self.axis]]

                # NOTE:ED - HACK for time-domain until slider is implemented
                step = -1 if planeType == DIMENSION_TIME else (1 if axisReversed else -1)

                self.strip._changePlane(self.axis, planeIncrement=step, planeCount=self.planeCount,
                                        isTimeDomain=planeType == DIMENSION_TIME)

    def _spinBoxChanged(self, *args):
        """Sets the value of the axis plane position box if the specified value is within the displayable limits.
        """
        if self.strip:
            planeLabel = self._axisSelector.spinBox
            value = planeLabel.value()

            if planeLabel.minimum() <= value <= planeLabel.maximum():
                self.strip._setAxisPositionAndWidth(self.axis, position=value)

    def _wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            if self.strip.prevPlaneCallback:
                self.strip.prevPlaneCallback(self.axis)
        else:
            if self.strip.nextPlaneCallback:
                self.strip.nextPlaneCallback(self.axis)

        self.strip.refresh()

    def hideWidgets(self):
        """Hide the planeToolbar if opened
        """
        if self.strip.spectrumDisplay.zPlaneNavigationMode == ZPlaneNavigationModes.INSTRIP.dataValue:
            axisButtons = (self._axisLabel, self._axisPpmPosition, self._axisPlaneCount, self._axisSelector)

            # if the other widgets are clicked then toggle the planeToolbar buttons
            if axisButtons[3].isVisible():
                axisButtons[3].setVisible(False)
                axisButtons[2].setVisible(True)
                axisButtons[1].setVisible(True)

            self._resize()


class ZPlaneToolbar(Frame):
    """
    Class to contain the widgets for zPlane navigation
    """

    def __init__(self, qtParent, mainWindow, displayOrStrip, showHeader=False, showLabels=False, **kwds):

        super().__init__(parent=qtParent, setLayout=True, **kwds)

        self._strip = None
        self.getLayout().setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.setVisible(False)
        self.mainWindow = mainWindow
        self._header = Label(self, text='zPlaneWidget', grid=(0, 0))
        self._header.setVisible(showHeader)

        self.labels = []
        # axisCodes = spectrumDisplay.axisCodes
        # _axisCount = len(axisCodes) - 2
        for ii, axisCode in enumerate(displayOrStrip.axisCodes[2:]):
            lbl = Label(self, text=axisCode, grid=(0, 1 + (ii * 2)), bold=True)
            lbl.setVisible(showLabels)
            self.labels.append(lbl)

    def setHeaderText(self, value):
        """Set the header text
        """
        if not isinstance(value, str):
            raise TypeError('{} is not a string'.format(value))
        self._header.setText(value)

    def setLabels(self, value):
        """Set the labels for the dimensions
        """
        if not isinstance(value, (tuple, list)):
            raise TypeError('{} must be tuple/list'.format(value))
        if len(value) != len(self._strip.axisCodes) - 2:
            raise TypeError('{} must be tuple/list of length {}'.format(value, len(self._strip) - 2))
        if not all(isinstance(val, str) for val in value):
            raise TypeError('{} must be tuple/list of strings'.format(value))

        for lbl, val in zip(self.labels, value):
            lbl.setText(value)

    def setHeaderVisible(self, value):
        """Set the visibility of the header
        """
        if not isinstance(value, bool):
            raise TypeError('{} must be a True/False')
        self._header.setVisible(value)

    def setLabelsVisible(self, value):
        """Set the visibility of the labels
        """
        if not isinstance(value, bool):
            raise TypeError('{} must be a True/False')
        for lbl in self.labels:
            lbl.setVisible(value)

    def attachZPlaneWidgets(self, strip):
        """Attach new widgets to the zPlane toolbar
        """
        layout = self.getLayout()

        # if strip != self._strip: - causing it to skip on undo/redo
        self.removeZPlaneWidgets()

        for col, fr in enumerate(strip.planeAxisBars):
            index = layout.indexOf(fr._axisSelector)
            if index == -1:
                layout.addWidget(fr._axisSelector._mainWidget, 0, 2 + col * 2, 1, 1)
                fr._axisSelector._mainWidget.setParent(self)
                fr._axisSelector.setVisible(True)
                fr._resize()

        self._header.setText(strip.pid)
        self._strip = strip

        self.setVisible(True)
        self.update()

    def removeZPlaneWidgets(self):
        """Remove existing widgets from the zPlane toolbar
        """
        layout = self.getLayout()

        if self._strip and hasattr(self._strip, 'planeAxisBars'):
            for pl in self._strip.planeAxisBars:
                # reattach the widget to the in strip container
                pl._attachButton('_axisSelector')
                pl._hideAxisSelector()


# class ZPlaneToolbar(Frame):
#     """
#     Class to contain the widgets for zPlane navigation
#     """
#
#     def __init__(self, qtParent, mainWindow, strip, showHeader=False, showLabels=False, **kwds):
#
#         super().__init__(parent=qtParent, setLayout=True, **kwds)
#
#         self._strip = None
#         self.getLayout().setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
#         self.setVisible(False)
#         self.mainWindow = mainWindow
#         self._header = Label(self, text='zPlaneWidget', grid=(0, 0))
#         self._header.setVisible(showHeader)
#
#         self.labels = []
#         axisCodes = strip.axisCodes
#         _axisCount = len(axisCodes) - 2
#         for ii in range(_axisCount):
#             lbl = Label(self, text=axisCodes[ii + 2], grid=(0, 1 + (ii * 2)), bold=True)
#             lbl.setVisible(showLabels)
#             self.labels.append(lbl)
#
#     def setHeaderText(self, value):
#         """Set the header text
#         """
#         if not isinstance(value, str):
#             raise TypeError('{} is not a string'.format(value))
#         self._header.setText(value)
#
#     def setLabels(self, value):
#         """Set the labels for the dimensions
#         """
#         if not isinstance(value, (tuple, list)):
#             raise TypeError('{} must be tuple/list'.format(value))
#         if len(value) != len(self._strip.axisCodes) - 2:
#             raise TypeError('{} must be tuple/list of length {}'.format(value, len(self._strip) - 2))
#         if not all(isinstance(val, str) for val in value):
#             raise TypeError('{} must be tuple/list of strings'.format(value))
#
#         for lbl, val in zip(self.labels, value):
#             lbl.setText(value)
#
#     def setHeaderVisible(self, value):
#         """Set the visibility of the header
#         """
#         if not isinstance(value, bool):
#             raise TypeError('{} must be a True/False')
#         self._header.setVisible(value)
#
#     def setLabelsVisible(self, value):
#         """Set the visibility of the labels
#         """
#         if not isinstance(value, bool):
#             raise TypeError('{} must be a True/False')
#         for lbl in self.labels:
#             lbl.setVisible(value)
#
#     def attachZPlaneWidgets(self, strip):
#         """Attach new widgets to the zPlane toolbar
#         """
#         layout = self.getLayout()
#
#         # if strip != self._strip: - causing it to skip on undo/redo
#         self.removeZPlaneWidgets()
#
#         for col, fr in enumerate(strip.planeAxisBars):
#             index = layout.indexOf(fr._axisSelector)
#             if index == -1:
#                 layout.addWidget(fr._axisSelector._mainWidget, 0, 2 + col * 2, 1, 1)
#                 fr._axisSelector._mainWidget.setParent(self)
#                 fr._axisSelector.setVisible(True)
#                 fr._resize()
#
#         self._header.setText(strip.pid)
#         self._strip = strip
#
#         self.setVisible(True)
#         self.update()
#
#     def removeZPlaneWidgets(self):
#         """Remove existing widgets from the zPlane toolbar
#         """
#         layout = self.getLayout()
#
#         if self._strip and hasattr(self._strip, 'planeAxisBars'):
#             for pl in self._strip.planeAxisBars:
#                 # reattach the widget to the in strip container
#                 pl._attachButton('_axisSelector')
#                 pl._hideAxisSelector()


STRIPCONNECT_LEFT = 'isLeft'
STRIPCONNECT_RIGHT = 'isRight'
STRIPCONNECT_NONE = 'noneConnect'
STRIPCONNECT_DIRS = (STRIPCONNECT_NONE, STRIPCONNECT_LEFT, STRIPCONNECT_RIGHT)

STRIPPOSITION_MINUS = 'minus'
STRIPPOSITION_PLUS = 'plus'
STRIPPOSITION_LEFT = 'l'
STRIPPOSITION_CENTRE = 'c'
STRIPPOSITION_RIGHT = 'r'
STRIPPOSITIONS = (STRIPPOSITION_MINUS, STRIPPOSITION_PLUS, STRIPPOSITION_LEFT, STRIPPOSITION_CENTRE, STRIPPOSITION_RIGHT)

# STRIPDICT = 'stripHeaderDict'
STRIPTEXT = 'stripText'
STRIPCOLOUR = 'stripColour'
STRIPLABELPOS = 'StripLabelPos'
STRIPICONNAME = 'stripIconName'
STRIPICONSIZE = 'stripIconSize'
STRIPOBJECT = 'stripObject'
STRIPCONNECT = 'stripConnect'
STRIPVISIBLE = 'stripVisible'
STRIPENABLED = 'stripEnabled'
STRIPTRUE = 1
STRIPFALSE = 0
STRIPSTOREINDEX = [STRIPTEXT, STRIPOBJECT, STRIPCONNECT, STRIPVISIBLE, STRIPENABLED]
STRIPHEADERVISIBLE = 'stripHeaderVisible'
STRIPHANDLE = 'stripHandle'
DEFAULTCOLOUR = HEXFOREGROUND


class StripHeaderWidget(_OpenGLFrameABC):

    def _initIcon(self, widget, strip):
        self._postIconInit(widget, strip)

    def _initStripHeader(self, widget, strip):
        self._postHeaderInit(widget, strip)

    BUTTONS = (('_nmrChainLeft', _StripLabel, None, None, (0, 0), (2, 1)),
               ('_nmrChainRight', _StripLabel, _initIcon, None, (0, 5), (2, 1)),
               ('_stripDirection', _StripLabel, None, None, (0, 2), (1, 2)),
               ('_stripLabel', _StripLabel, None, None, (1, 2), (1, 1)),
               ('_stripPercent', _StripLabel, _initStripHeader, None, (1, 3), (1, 2)),
               )

    def _postIconInit(self, widget, strip):
        """Seems an awkward way of getting a generic post init function but can't think of anything else yet
        """
        # assume that nothing has been set yet
        pass

    def _postHeaderInit(self, widget, strip):
        """Seems an awkward way of getting a generic post init function but can't think of anything else yet
        """
        # assume that nothing has been set yet

        # add gui notifiers here instead of in backboneAssignment
        # NOTE:ED could replace this with buttons instead
        GuiNotifier(self._nmrChainLeft,
                    [GuiNotifier.DROPEVENT], [DropBase.TEXT],
                    self._processDroppedLabel,
                    toLabel=self._stripDirection,
                    plusChain=False)

        GuiNotifier(self._nmrChainRight,
                    [GuiNotifier.DROPEVENT], [DropBase.TEXT],
                    self._processDroppedLabel,
                    toLabel=self._stripDirection,
                    plusChain=True)

        self._resize()

    def _processDroppedLabel(self, data, toLabel=None, plusChain=None):
        """Not a very elegant way of running backboneAssignment code from the strip headers

        Should be de-coupled from the backboneAssignment module
        """
        if toLabel and toLabel.text():
            dest = toLabel.text()
            nmrResidue = self.project.getByPid(dest)

            if nmrResidue:

                guiModules = self.mainWindow.modules
                for guiModule in guiModules:
                    if guiModule.className == 'BackboneAssignmentModule':
                        guiModule._processDroppedNmrResidue(data, nmrResidue=nmrResidue, plusChain=plusChain)

    def __init__(self, qtParent, mainWindow, strip, stripArrangement=None, **kwds):
        super().__init__(qtParent, mainWindow, strip, **kwds)

        self._parent = qtParent
        self.mainWindow = mainWindow
        self.strip = strip
        self.setAutoFillBackground(False)

        self._labels = dict((strip, widget) for strip, widget in
                            zip(STRIPPOSITIONS,
                                (self._nmrChainLeft, self._nmrChainRight, self._stripLabel, self._stripDirection, self._stripPercent)))

        # set the visible state of the header
        self.strip._setInternalParameter(STRIPHEADERVISIBLE, False)
        self.setVisible(False)

        # labelsVisible = False
        for stripPos in STRIPPOSITIONS:
            # read the current strip header values
            headerText = self._getPositionParameter(stripPos, STRIPTEXT, '')

            headerIconName = self._getPositionParameter(stripPos, STRIPICONNAME, '')
            headerIconSize = self._getPositionParameter(stripPos, STRIPICONSIZE, (18, 18))

            # not sure this is required
            headerObject = self.strip.project.getByPid(self._getPositionParameter(stripPos, STRIPOBJECT, None))
            headerConnect = self._getPositionParameter(stripPos, STRIPCONNECT, STRIPCONNECT_NONE)

            # headerVisible = self._getPositionParameter(stripPos, STRIPVISIBLE, False)
            # headerEnabled = self._getPositionParameter(stripPos, STRIPENABLED, True)

            self._labels[stripPos].obj = headerObject
            self._labels[stripPos]._connectDir = headerConnect

            # self._labels[stripPos].setVisible(True if headerText else False)
            # self._labels[stripPos].setVisible(headerVisible)

            # labelsVisible = labelsVisible or headerVisible
            # self._labels[stripPos].setEnabled(headerEnabled)

            if headerIconName:
                self.setLabelIcon(headerIconName, headerIconSize, stripPos)
            else:
                self.setLabelText(headerText, stripPos)

        self._resize()

        # Notifier for change of stripLabel
        self._nmrResidueNotifier = Notifier(self.project,
                                            [Notifier.RENAME],
                                            'NmrResidue',
                                            self._processNotifier,
                                            onceOnly=True)

    def setEnabledLeftDrop(self, value):

        # set the icon the first time if not loaded
        iconLeft = self._getPositionParameter(STRIPPOSITION_MINUS, STRIPICONNAME, '')
        if value and not iconLeft:
            self.setLabelIcon('icons/down-left', (18, 18), STRIPPOSITION_MINUS)

        self._resize()

    def setEnabledRightDrop(self, value):

        # set the icon the first time if not loaded
        iconRight = self._getPositionParameter(STRIPPOSITION_PLUS, STRIPICONNAME, '')
        if value and not iconRight:
            self.setLabelIcon('icons/down-right', (18, 18), STRIPPOSITION_PLUS)

        self._resize()

    def _setPositionParameter(self, stripPos, subParameterName, value):
        """Set the item in the position dict
        """
        if self.strip.isDeleted:
            return

        params = self.strip._getInternalParameter(stripPos)
        if not params:
            params = {}

        # fix for bad characters in the XML
        if isinstance(value, str):
            if '<<<' in value:
                value = 'MINUS'
            elif '>>>' in value:
                value = 'PLUS'

        # currently writes directly into _ccpnInternal
        params.update({subParameterName: value})
        self.strip._setInternalParameter(stripPos, params)

    def _getPositionParameter(self, stripPos, subParameterName, default):
        """Return the item from the position dict
        """
        params = self.strip._getInternalParameter(stripPos)
        if params:
            if subParameterName in params:
                value = params.get(subParameterName)

                # fix for bad characters in the XML
                # Could ignore here, so that needs doubleClick in backboneAssignment to restart
                if isinstance(value, str):
                    if 'MINUS' in value:
                        # value = '<<<'
                        value = ''
                    elif 'PLUS' in value:
                        # value = '>>>'
                        value = ''

                return value

        return default

    def reset(self):
        """Clear all header labels
        """
        # self.setVisible(False)
        for stripPos in STRIPPOSITIONS:
            self._labels[stripPos].obj = None
            self._labels[stripPos]._connectDir = STRIPCONNECT_NONE
            self._labels[stripPos].setEnabled(True)
            self.setLabelVisible(stripPos, False)

            # clear the header store
            params = {STRIPTEXT    : '',
                      STRIPICONNAME: '',
                      STRIPOBJECT  : None,
                      STRIPCONNECT : STRIPCONNECT_NONE,
                      STRIPVISIBLE : False,
                      STRIPENABLED : True
                      }
            self.strip._setInternalParameter(stripPos, params)
        self.strip._setInternalParameter(STRIPHANDLE, None)
        self._resize()

    def getLabelObject(self, position=STRIPPOSITION_CENTRE):
        """Return the object attached to the header label at the given position
        """
        if position in STRIPPOSITIONS:
            return self._labels[position].obj
        else:
            raise ValueError(f'Error: {str(position)} is not a valid position')

    def setLabelObject(self, obj=None, position=STRIPPOSITION_CENTRE):
        """Set the object attached to the header label at the given position and store its pid
        """
        # NOTE:ED not sure I need this now - check rename nmrResidue, etc.
        self.show()
        if position not in STRIPPOSITIONS:
            raise ValueError(f'Error: {str(position)} is not a valid position')

        self._labels[position].obj = obj

        # SHOULD have a pid if an object
        if obj and hasattr(obj, 'pid'):
            self._setPositionParameter(position, STRIPOBJECT, str(obj.pid))
        self._resize()

    def getLabelText(self, position=STRIPPOSITION_CENTRE):
        """Return the text for header label at the given position
        """
        if position in STRIPPOSITIONS:
            return self._labels[position].text()
        else:
            raise ValueError(f'Error: {str(position)} is not a valid position')

    def setLabelText(self, text=None, position=STRIPPOSITION_CENTRE):
        """Set the text for header label at the given position
        """
        self.show()
        if position not in STRIPPOSITIONS:
            raise ValueError(f'Error: {str(position)} is not a valid position')

        self._labels[position].setText(str(text))
        self._setPositionParameter(position, STRIPTEXT, str(text))
        self.setLabelVisible(position, bool(text))
        self._resize()

    def getLabel(self, position=STRIPPOSITION_CENTRE):
        """Return the header label widget at the given position
        """
        if position in STRIPPOSITIONS:
            return self._labels[position]
        else:
            raise ValueError(f'Error: {str(position)} is not a valid position')

    def getLabelVisible(self, position=STRIPPOSITION_CENTRE):
        """Return if the widget at the given position is visible
        """
        if position in STRIPPOSITIONS:
            return self._labels[position].isVisible()
        else:
            raise ValueError(f'Error: {str(position)} is not a valid position')

    def setLabelVisible(self, position=STRIPPOSITION_CENTRE, visible: bool = True):
        """show/hide the header label at the given position
        """
        if position not in STRIPPOSITIONS:
            raise ValueError(f'Error: {str(position)} is not a valid position')

        self._labels[position].setVisible(visible)
        self._setPositionParameter(position, STRIPVISIBLE, visible)

        lv = [self._getPositionParameter(pp, STRIPVISIBLE, False) for pp in STRIPPOSITIONS]
        headerVisible = any(lv)
        self.strip._setInternalParameter(STRIPHEADERVISIBLE, headerVisible)
        self.setVisible(headerVisible)
        self._resize()

    def setLabelEnabled(self, position=STRIPPOSITION_CENTRE, enable: bool = True):
        """Enable/disable the header label at the given position
        """
        if position not in STRIPPOSITIONS:
            raise ValueError(f'Error: {str(position)} is not a valid position')

        self._labels[position].setEnabled(enable)
        self._setPositionParameter(position, STRIPENABLED, enable)
        self._resize()

    def getLabelEnabled(self, position=STRIPPOSITION_CENTRE):
        """Return if the widget at the given position is enabled
        """
        if position in STRIPPOSITIONS:
            return self._labels[position].isEnabled()
        else:
            raise ValueError(f'Error: {str(position)} is not a valid position')

    def getLabelConnectDir(self, position=STRIPPOSITION_CENTRE):
        """Return the connectDir attribute of the header label at the given position
        """
        if position in STRIPPOSITIONS:
            return self._labels[position]._connectDir
        else:
            raise ValueError(f'Error: {str(position)} is not a valid position')

    def setLabelConnectDir(self, position=STRIPPOSITION_CENTRE, connectDir: str = STRIPCONNECT_NONE):
        """set the connectDir attribute of the header label at the given position
        """
        if position not in STRIPPOSITIONS:
            raise ValueError(f'Error: {str(position)} is not a valid position')

        self._labels[position]._connectDir = connectDir
        self._setPositionParameter(position, STRIPCONNECT, connectDir)
        self._resize()

    def setLabelIcon(self, iconName=None, iconSize=(18, 18), position=STRIPPOSITION_CENTRE):
        """Set the text for header label at the given position
        """
        self.show()
        if position in STRIPPOSITIONS:
            self._labels[position].setPixmap(Icon(iconName).pixmap(*iconSize))
            self._setPositionParameter(position, STRIPICONNAME, str(iconName))
            self.setLabelVisible(position, bool(iconName))
        else:
            raise ValueError(f'Error: {str(position)} is not a valid position')

        self._resize()

    def _processNotifier(self, data):
        """Process the notifiers for the strip header
        """
        if self.strip.isDeleted:
            return

        trigger = data[Notifier.TRIGGER]
        obj = data[Notifier.OBJECT]

        if trigger == Notifier.RENAME:
            oldPid = data[Notifier.OLDPID]

            for stripPos in STRIPPOSITIONS:
                # change the label text
                if oldPid in self.getLabelText(stripPos):
                    self.setLabelText(position=stripPos, text=str(obj.pid))

                # change the object text
                if self.getLabelObject(stripPos) is obj:
                    self.setLabelObject(position=stripPos, obj=obj)

    @property
    def headerVisible(self):
        return self.strip._getInternalParameter(STRIPHEADERVISIBLE)

    @headerVisible.setter
    def headerVisible(self, visible):
        self.strip._setInternalParameter(STRIPHEADERVISIBLE, visible)
        self.setVisible(visible)
        self._resize()

    @property
    def handle(self):
        return self.strip._getInternalParameter(STRIPHANDLE)

    @handle.setter
    def handle(self, value):
        self.strip._setInternalParameter(STRIPHANDLE, value)
        self._resize()


class StripLabelWidget(_OpenGLFrameABC):

    def _setStripLabel(self, *args):
        """Set the label of the strip, called from _populate.
        """
        self.setLabelText(self.strip.pid if self.strip else '')
        self._resize()

    BUTTONS = (('_stripPin', ActiveLabel, None, None, (0, 0), (1, 1)),
               ('_stripLabel', _StripLabel, None, _setStripLabel, (0, 1), (1, 1)),
               )

    def _processDroppedLabel(self, data, toLabel=None, plusChain=None):
        """Not a very elegant way of running backboneAssignment code from the strip headers

        Should be de-coupled from the backboneAssignment module
        """
        pass

    def __init__(self, qtParent, mainWindow, strip, **kwds):
        super().__init__(qtParent, mainWindow, strip, **kwds)

        self._parent = qtParent
        self.mainWindow = mainWindow
        self.strip = strip
        self.setAutoFillBackground(False)

        # read the current strip header values
        headerText = self._getPositionParameter(STRIPTEXT, '')
        headerColour = self._getPositionParameter(STRIPCOLOUR, DEFAULTCOLOUR)
        self.setLabel(headerText, headerColour)

        self._PIXMAPWIDTH = getFontHeight()
        self._icon = Icon('icons/pin-grey')
        self._stripPin.setVisible(strip.pinned)
        # self._stripPin.setFixedSize(self._PIXMAPWIDTH - 4, self._PIXMAPWIDTH - 4)
        self._stripPin.setPixmap(self._icon.pixmap(self._PIXMAPWIDTH - 4, self._PIXMAPWIDTH - 4))

        # get the visible state of the header
        self.setVisible(True)
        self._resize()

    def _setPositionParameter(self, subParameterName, value):
        """Set the item in the position dict
        """
        params = self.strip._getInternalParameter(STRIPLABELPOS)
        if not params:
            params = {}

        # currently writes directly into _ccpnInternal
        params.update({subParameterName: value})
        self.strip._setInternalParameter(STRIPLABELPOS, params)

    def _getPositionParameter(self, subParameterName, default):
        """Return the item from the position dict
        """
        if params := self.strip._getInternalParameter(STRIPLABELPOS):
            if subParameterName in params:
                return params.get(subParameterName)
        return default

    def reset(self):
        """Clear stripLabel
        """
        # clear the store
        params = {STRIPTEXT: '',
                  }
        self.strip._setInternalParameter(STRIPLABELPOS, params)
        self._resize()

    def setLabel(self, text='', colour=DEFAULTCOLOUR):
        """Set the text for stripLabel
        """
        self.show()
        self._stripLabel.setText(str(text))
        self._setStyle(self._stripLabel, foregroundColour=colour)
        self._setPositionParameter(STRIPTEXT, str(text))
        self._setPositionParameter(STRIPCOLOUR, colour)
        self._stripLabel.setVisible(bool(text))
        self._resize()

    def setLabelText(self, text=None):
        """Set the text for stripLabel
        """
        self.show()
        self._stripLabel.setText(str(text))
        self._setPositionParameter(STRIPTEXT, str(text))
        self._stripLabel.setVisible(bool(text))
        self._resize()

    def setLabelColour(self, colour=DEFAULTCOLOUR):
        """Set the colour for stripLabel
        """
        self.show()
        self._setStyle(self._stripLabel, foregroundColour=colour)
        self._setPositionParameter(STRIPCOLOUR, colour)
        self._resize()

    def setHighlighted(self, value):
        self._stripLabel.highlighted = value

    def setPinned(self, state):
        self._stripPin.setVisible(state)
        if state:
            self._resize()


class TestPopup(Frame):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.CustomizeWindowHint)
        self.setLayout(QtWidgets.QHBoxLayout())
        Button_close = QtWidgets.QPushButton('close')
        self.layout().addWidget(QtWidgets.QLabel("HI"))
        self.layout().addWidget(Button_close)
        Button_close.clicked.connect(self.close)
        self.exec_()
        print("clicked")

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QtCore.QPoint(event.globalPos() - self.oldPos)
        #print(delta)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()
