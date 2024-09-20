"""
This file contains CcpnModule base class
modified by Geerten 1-12/12/2016
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
__modifiedBy__ = "$modifiedBy: Daniel Thompson $"
__dateModified__ = "$dateModified: 2024-09-05 15:47:46 +0100 (Thu, September 05, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister $"
__date__ = "$Date: 2016-07-09 14:17:30 +0100 (Sat, 09 Jul 2016) $"
#=========================================================================================
# Start of code
#=========================================================================================

import re
import contextlib
import itertools
import collections
from functools import partial
from PyQt5 import QtCore, QtGui, QtWidgets
from pyqtgraph.dockarea.Container import Container
from pyqtgraph.dockarea.DockDrop import DockDrop
from pyqtgraph.dockarea.Dock import DockLabel, Dock
from pyqtgraph.dockarea.DockArea import DockArea
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.Splitter import Splitter
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.SideBar import SideBar, SideBarSearchListView
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.Font import setWidgetFont, getWidgetFontHeight, getFont, DEFAULTFONT
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.guiSettings import (getColours, BORDERNOFOCUS, CCPNMODULELABEL_BACKGROUND, CCPNMODULELABEL_FOREGROUND,
                                     CCPNMODULELABEL_BACKGROUND_ACTIVE, CCPNMODULELABEL_FOREGROUND_ACTIVE,
                                     CCPNMODULELABEL_BORDER, CCPNMODULELABEL_BORDER_ACTIVE,
                                     BORDERNOFOCUS_COLOUR)
from ccpn.ui.gui.lib.ModuleLib import getBlockingDialogs
from ccpn.core.lib.Notifiers import NotifierBase
from ccpn.core.lib.Pid import Pid, createPid
from ccpn.util.Path import aPath
from ccpn.util import Logging
from ccpn.util.Logging import getLogger


settingsWidgetPositions = {
    'top'   : {'settings': (0, 0), 'widget': (1, 0)},
    'bottom': {'settings': (1, 0), 'widget': (0, 0)},
    'left'  : {'settings': (0, 0), 'widget': (0, 1)},
    'right' : {'settings': (0, 1), 'widget': (0, 0)},
    }
ALL = '<all>'
DoubleUnderscore = '__'

PidLongClassName = 'Module'
PidShortClassName = 'MO'

MODULENAME = 'moduleName'
WIDGETSTATE = 'widgetsState'

MIN_PIXMAP = 32
MAX_PIXMAP = 128


#=========================================================================================
# CcpnModule
#=========================================================================================

class CcpnModule(Dock, DropBase, NotifierBase):
    """
    Base class for CCPN modules
    sets self.application, self.current, self.project and self.mainWindow

    Overide parameters for settings widget as needed

    Usage:
      __init__    initialises the module according to the settings given below:

      _closeModule    closing of the module.

                      If addition functionality is required, the correct
                      procedure is to override this method within your class
                      and end your method with super()._closeModule()

                      e.q.
                            def _closeModule(self):
                              # your functions here
                              super(<YourModule>, self)._closeModule()

                      OR __init__ with closeFunc=<your close function>
    """
    className = None  # used for restoring GUI layouts
    shortClassName = PidShortClassName  # used to create the pid
    longClassName = PidLongClassName  # used to create the long pid
    HORIZONTAL = 'horizontal'
    VERTICAL = 'vertical'
    labelOrientation = HORIZONTAL  # toplabel orientation

    # override in specific module implementations
    includeSettingsWidget = False
    maxSettingsState = 3  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    defaultSettingsState = 0  # default state of the settings widget
    settingsPosition = 'top'
    settingsMinimumSizes = (100, 50)
    _restored = False
    _onlySingleInstance = False
    _includeInLastSeen = False  # whether to restore or not after closing it (in the same project)
    _allowRename = False
    _defaultName = MODULENAME  # used only when renaming is allowed, so that its original name is stored in the lastSeen widgetsState.
    _helpFilePath = None

    # After closing a renamed module, any new instance will be named as default.

    # _instances = set()

    def __init__(self, mainWindow, name, closable=True, closeFunc=None,
                 settingsScrollBarPolicies=('asNeeded', 'asNeeded'), **kwds):

        self.maximised = False
        self.maximiseRestoreState = None
        self._defaultName = name
        if self.className is None:
            # get the class-name from the class
            self.className = self.__class__.__name__

        self.area = None
        self.mainWindow = mainWindow
        if self.mainWindow is not None:
            self.area = mainWindow.moduleArea
        super().__init__(name=name, area=self.area,
                         autoOrientation=False,
                         closable=closable)
        DropBase._init(self, acceptDrops=True)

        self.hStyle = """
                  Dock > QWidget {
                      border: 1px solid palette(mid);
                      border-radius: 2px;
                      border-top-left-radius: 0px;
                      border-top-right-radius: 0px;
                      border-top-width: 0px;
                  }"""
        self.vStyle = """
                  Dock > QWidget {
                      border: 1px solid palette(mid);
                      border-radius: 0px;
                      border-top-left-radius: 0px;
                      border-bottom-left-radius: 0px;
                      border-left-width: 0px;
                  }"""
        self.nStyle = """
                  Dock > QWidget {
                      border: 0px solid #000;
                      border-radius: 0px;
                  }"""
        self.dragStyle = """
                  Dock > QWidget {
                      border: 0px solid #00F;
                      border-radius: 0px;
                  }"""
        self._selectedOverlay = DropAreaSelectedOverlay(self)
        self._selectedOverlay.raise_()
        # new border to clean up the edges of the module
        self._borderOverlay = BorderOverlay(self)
        self._borderOverlay.raise_()

        Logging.getLogger().debug(f'CcpnModule>>> {type(self)} {mainWindow}')

        # Logging.getLogger().debug('module:"%s"' % (name,))
        self.closeFunc = closeFunc
        self._nameSplitter = '_'  # used to get the serial number.

        setWidgetFont(self, )

        self.widgetArea.setContentsMargins(0, 0, 0, 0)

        # remove old label, so it can be redefined
        self.topLayout.removeWidget(self.label)
        # GST this wasn't deleting the widget it was leaving it still attached to the qt hierrchy which was causing all
        # sorts of graphical hickups later on

        # _dock = self.label.dock  # not carried across from original label
        self.label.deleteLater()
        del self.label

        # GST other way to do this would be to
        # 1. replace the super class init with our own and not call it 2. replace the methods of DockLabel we have
        # problems with 3. ask the pyqtgraph guys to add a factory method...
        self.label = CcpnModuleLabel(name, self,
                                     showCloseButton=closable, closeCallback=self._closeModule,
                                     enableSettingsButton=self.includeSettingsWidget,
                                     settingsCallback=self._settingsCallback,
                                     helpButtonCallback=self._helpButtonCallback,
                                     )
        # self.label.dock = self  # not

        self.topLayout.addWidget(self.label, 0, 1)  # ejb - swap out the old widget, keeps hierarchy
        # except it doesn't work properly
        self.setOrientation(o='horizontal')
        self.setAutoFillBackground(True)

        # main widget area
        self.mainWidget = Frame(parent=None, setLayout=True, acceptDrops=True)

        # optional settings widget area
        self.settingsWidget = None
        if self.includeSettingsWidget:
            self.settingsWidget = ScrollableFrame(parent=self.widgetArea,
                                                  showBorder=False, setLayout=True,
                                                  scrollBarPolicies=settingsScrollBarPolicies)
            self._settingsScrollArea = self.settingsWidget._scrollArea

            # set the new borders for the settings scroll area - border not needed at the top
            # self._settingsScrollArea.setStyleSheet('ScrollArea { border-left: 1px solid %s;'
            #                                        'border-right: 1px solid %s;'
            #                                        'border-bottom: 1px solid %s;'
            #                                        'background: transparent; }' % (
            #                                            BORDERNOFOCUS_COLOUR, BORDERNOFOCUS_COLOUR,
            #                                            BORDERNOFOCUS_COLOUR))
            self._settingsScrollArea.setStyleSheet('ScrollArea { border-left: 1px solid palette(mid);'
                                                   'border-right: 1px solid palette(mid);'
                                                   'border-bottom: 1px solid palette(mid);'
                                                   'background: transparent; }')
            self.settingsWidget.insertCornerWidget()

            if self.settingsPosition in settingsWidgetPositions:
                hSettings, vSettings = settingsWidgetPositions[self.settingsPosition]['settings']
                hWidget, vWidget = settingsWidgetPositions[self.settingsPosition]['widget']
                self.addWidget(self._settingsScrollArea, hSettings, vSettings)
                self.addWidget(self.mainWidget, hWidget, vWidget)
            else:  #default as settings on top and widget below
                self.addWidget(self._settingsScrollArea, 0, 0)
                self.addWidget(self.mainWidget, 1, 0)

            self._settingsScrollArea.hide()

            self.layout.removeWidget(self._settingsScrollArea)
            self.layout.removeWidget(self.mainWidget)

            if self.settingsPosition == 'left':
                self._splitter = Splitter(setLayout=True, horizontal=True)
                self._splitter.addWidget(self._settingsScrollArea)
                self._splitter.addWidget(self.mainWidget)
            elif self.settingsPosition == 'right':
                self._splitter = Splitter(setLayout=True, horizontal=True)
                self._splitter.addWidget(self.mainWidget)
                self._splitter.addWidget(self._settingsScrollArea)
            elif self.settingsPosition == 'top':
                self._splitter = Splitter(setLayout=True, horizontal=False)
                self._splitter.addWidget(self._settingsScrollArea)
                self._splitter.addWidget(self.mainWidget)
            elif self.settingsPosition == 'bottom':
                self._splitter = Splitter(setLayout=True, horizontal=False)
                self._splitter.addWidget(self.mainWidget)
                self._splitter.addWidget(self._settingsScrollArea)

            self.addWidget(self._splitter, 0, 0)
            # self._splitter.setStretchFactor(1, 5)

        else:
            self.settingsWidget = None
            self.addWidget(self.mainWidget, 0, 0)

        # set the flag so that the gearbox settings widget expands to the required size on the first click
        self.setExpandSettingsFlag(True)

        # add an event filter to check when the dock has been floated - it needs to have a callback
        # that fires when the window has been maximised
        self._maximiseFunc = None
        self._closeFunc = None
        CcpnModule._lastActionWasDrop = False

        # always explicitly show the mainWidget and/or settings widget
        # default state (increased by one by settingsCallback)
        self.settingsState = self.defaultSettingsState - 1
        self.mainWidget.show()
        self._settingsCallback()

        # set parenting relations
        if self.mainWindow is not None:
            self.setParent(self.mainWindow.moduleArea)  # ejb
        self.widgetArea.setParent(self)

        # stop the blue overlay popping up when dragging over a spectrum (no central region)
        self.allowedAreas = ['top', 'left', 'right', 'bottom']

        self.update()  # make sure that the widgetArea starts the correct size
        # set the constraints so the module contracts to the correct size
        self.mainWidget.getLayout().setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.setMinimumSize(6 * self.label.labelSize, 5 * self.label.labelSize)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

    #=========================================================================================
    # CCPN Properties
    #=========================================================================================

    def __repr__(self):
        return f'<{self.pid}>'

    @property
    def pid(self) -> Pid:
        """
        Identifier for the object, unique within the project - added to give label to ccpnModules
        """
        return createPid(self.shortClassName, self.id)

    @property
    def gid(self) -> Pid:
        return self.pid

    @property
    def longPid(self) -> Pid:
        """
        Identifier for the object, unique within the project - added to give label to ccpnModules
        """
        return createPid(self.longClassName, self.id)

    @property
    def id(self):
        """
        The module name without  the pid-prefix  but including the serial number (if any)
        """
        return self.name()

    @property
    def titleName(self):
        """
        module name without the pid-prefix and serial number (if any)
        """
        pidPrefix, moduleName, serialName = self.pidFields
        return moduleName

    @property
    def moduleName(self):
        """
        Module name as appear on the GUI, without the pid identifier (e.g.: MO:, Module: or GD:, SpectrumDisplay:).
        """
        return self._name

    @moduleName.setter
    def moduleName(self, name):
        self._name = name

    @property
    def pidFields(self):
        """
        get the three parts of a Pid
        """
        pidPrefix, moduleName, serialName = self._getModulePidFields()
        return (pidPrefix, moduleName, serialName)

    @property
    def widgetsState(self):
        return self._widgetsState

    @widgetsState.getter
    def widgetsState(self):
        """return  {"variableName":"value"}  of all gui Variables.
        """
        widgetsState = collections.OrderedDict()

        wDict = self._setNestedWidgetsAttrToModule()
        for varName, widget in wDict.items():
            try:  # try because widgets can be dynamically deleted
                value = widget._getSaveState()
                if value is not None:  # Nones come from non-storable widgets: Splitters, tabs etc..
                    widgetsState[varName] = value
            except Exception as es:
                getLogger().debug2(f'state getter not implemented for {varName}: {es}')

        return widgetsState

    def _getLastSeenWidgetsState(self):
        """ Internal. Used to restore last closed module in the same program instance. """
        return self.widgetsState

    #=========================================================================================
    # Widget Methods
    #=========================================================================================

    def _getModulePidFields(self):
        """

        split name in the blocks:
            Pid-prefix (short or long)
            Name
            Serial
        return a tuple

        """
        pid = self.pid
        pidPrefix = pid.type
        moduleName = pid.id
        serialName = ''

        splits = moduleName.split(self._nameSplitter)
        if len(splits) > 1:
            try:
                serialName = str(int(splits[-1]))  # consider a serial only if can be an int.
                moduleName = self._nameSplitter.join(splits[:-1])
            except:
                serialName = ''
                moduleName = self._nameSplitter.join(
                        splits)  # this is when there is a splitter but not a serial. eg 2D_HN

        return (pidPrefix, moduleName, serialName)

    def renameModule(self, newName):
        """ rename the Gui module a  """
        from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, nullContext

        context = undoBlockWithoutSideBar if self.mainWindow else nullContext

        with context():
            if self.area:
                validator = self.label.nameEditor.validator()
                validator.validate(newName, 0, )
                _isValidState, _messageState = validator._isValidState, validator._messageState
                if _isValidState:
                    self._name = newName  # gui is handled by notifier
                    self.moduleName = self._name
                    return True

                else:
                    showWarning(f'Cannot rename module {self.titleName}', _messageState)
                    self.label.nameEditor.set(self._name)  # reset the original name

            return False

    def _isNameAvailable(self, name):

        return self.area._isNameAvailable(name)

    def restoreWidgetsState(self, **widgetsState):
        """
        Restore the gui params. To Call it: _setParams(**{"variableName":"value"})

        This is automatically called after every restoration and after the module has been initialised.
        Subclass this for a custom behaviour. for example custom callback after the widgets have been restored.
        Subclass like this:
               def restoreWidgetsState(self, **widgetsState):
                  super(TheModule, self).restoreWidgetsState(**widgetsState) #First restore as default
                  #  do some stuff

        :param widgetsState:
        """
        wDict = self._setNestedWidgetsAttrToModule()

        widgetsState = collections.OrderedDict(sorted(widgetsState.items()))
        for variableName, value in widgetsState.items():
            try:
                # set parameter if it exists in the module's named widgets
                if widget := wDict.get(str(variableName)):
                    widget._setSavedState(value)

            except Exception as es:
                getLogger().debug(
                        f'Impossible to restore {variableName} value for {self.name()}. {es}'
                        )

    def _closeModule(self):
        """Close the module
        """
        with contextlib.suppress(Exception):
            if self.closeFunc:
                self.closeFunc()
        # delete any notifiers initiated with this Module
        self.deleteAllNotifiers()

        getLogger().debug(f'Closing {str(self.container())}')

        if self.maximised:
            self.toggleMaximised()

        if not self._container:
            if (area := self.mainWindow.moduleArea) and area._container is None:
                for i in area.children():
                    if isinstance(i, Container):
                        self._container = i

        if self._includeInLastSeen and self.area:
            self.area._seenModuleStates[self.className] = {MODULENAME : self._defaultName,
                                                           WIDGETSTATE: self._getLastSeenWidgetsState()}

        self.mainWindow.application._cleanGarbageCollector()
        try:
            super().close()
        except Exception:
            """Remove this dock from the DockArea it lives inside."""
            self._container = None
            self.sigClosed.emit(self)

    def _detach(self):
        """"Remove the module from the Drop-Area into a new window
        """
        self.float()

    #=========================================================================================
    # Super class Methods
    #=========================================================================================

    def getDockArea(self, target=None):
        current = self if target is None else target

        while current.parent() is not None and not isinstance(current, DockArea):
            current = current.parent()
        return current

    def _setNestedWidgetsAttrToModule(self):
        """
        :return: nestedWidgets
        """
        # get all the children that are of ccpn-core Base classes
        allChildren = list(filter(lambda widg: isinstance(widg, Base), self.findChildren(QtWidgets.QWidget)))
        grouped = [list(v) for k, v in itertools.groupby(allChildren, lambda x: str(type(x)), )]

        # order the groups, appending numbers if required, and remove any whitespaces
        _stateWidgets = collections.OrderedDict((re.sub(r"\s+", "", widg.objectName()) if widg.objectName() else
                                                 (DoubleUnderscore + re.sub(r"\s+", "",
                                                                            widg.objectName()) + widg.__class__.__name__ + (
                                                      str(count) if count > 0 else '')),
                                                 widg)
                                                for grp in grouped
                                                for count, widg in enumerate(grp))

        return _stateWidgets

    def event(self, event):
        """
        CCPNInternal
        Handle events for switching transparency of modules.
        Modules become transparent when dragging to another module.
        Ensure that the dropAreas become active
        """
        if event.type() == QtCore.QEvent.ParentChange and self._maximiseFunc:
            try:
                found = False
                searchWidget = self.parent()

                # while searchWidget is not None and not found:
                #   # print (searchWidget)
                #   if isinstance(searchWidget, TempAreaWindow):
                #     searchWidget.eventFilter = self._tempAreaWindowEventFilter
                #     searchWidget.installEventFilter(searchWidget)
                #     found = True
                #   else:
                #     searchWidget = searchWidget.parent()

            except Exception as es:
                getLogger().warning('Error setting maximiseFunc', str(es))

        return super(CcpnModule, self).event(event)

    def installMaximiseEventHandler(self, maximiseFunc, closeFunc):
        """
        Attach a maximise function to the parent window.
        This is called when the WindowStateChanges to maximises

        :param maximiseFunc:
        """
        return

        # self._maximiseFunc = maximiseFunc
        # self._closeFunc = closeFunc

    def removeMaximiseEventHandler(self):
        """
        Clear the attached maximise function
        :return:
        """
        self._maximiseFunc = None
        self._closeFunc = None

    def _tempAreaWindowEventFilter(self, obj, event):
        """
        Window manager event filter to call the attached maximise function.
        This is required to re-populate the window when it has been maximised
        """
        try:
            if event.type() == QtCore.QEvent.WindowStateChange:
                if (
                        event.oldState() & QtCore.Qt.WindowMinimized
                        and self._maximiseFunc
                ):
                    self._maximiseFunc()

            elif event.type() == QtCore.QEvent.Close:

                # catch whether the close event is from closing the tempWindow or moving back to a different module area
                if self._closeFunc and not CcpnModule._lastActionWasDrop:
                    self._closeFunc()
                else:
                    CcpnModule._lastActionWasDrop = False

        except Exception as es:
            getLogger().debug('TempWindow Error %s; %s; %s', obj, event, str(es))
        finally:
            return False

    def setHelpFilePath(self, htmlFilePath):
        self._helpFilePath = htmlFilePath

    def _helpButtonCallback(self):
        """
        Add a new module displaying its help file
        :return:
        """
        from ccpn.ui.gui.modules.HelpModule import HelpModule

        htmlFilePath = self._helpFilePath
        if htmlFilePath is not None:
            moduleArea = self.mainWindow.moduleArea
            helpModule = moduleArea._getHelpModule(self.moduleName)
            if not helpModule:
                helpModule = HelpModule(mainWindow=self.mainWindow,
                                        name=f'Help Browser: {self.moduleName}',
                                        parentModuleName=self.moduleName,
                                        htmlFilePath=htmlFilePath)
                moduleArea.addModule(helpModule, position='top', relativeTo=self)

    def _settingsCallback(self):
        """
        Toggles display of settings widget in module.
        """
        if self.includeSettingsWidget:
            self.settingsState = (self.settingsState + 1) % self.maxSettingsState
            if self.settingsState == 0:
                self.mainWidget.show()
                self._settingsScrollArea.hide()
            elif self.settingsState == 1:
                self.mainWidget.show()
                self._settingsScrollArea.show()
                self._setSettingsWidgetSize()
            elif self.settingsState == 2:
                self._settingsScrollArea.hide()
                self.mainWidget.hide()
        else:
            RuntimeError(
                    'Settings widget inclusion is false, please set includeSettingsWidget boolean to True at class level ')

    def setExpandSettingsFlag(self, value):
        """Set the expand flag to the True/False
        """
        self._expandSettingsFlag = value

    def _setSettingsWidgetSize(self):
        """Set the size of the gearbox settings to the sizeHint if the flag is True
        Size is stored for next open/close unless flag is reset to True
        """
        if self._expandSettingsFlag:
            self._expandSettingsFlag = False

            sizes = self._splitter.sizes()
            total = sizes[0] + sizes[1]

            if self.settingsPosition == 'left':
                settingsSize = self._settingsScrollArea.sizeHint().width()
                sizes[0] = settingsSize
                sizes[1] = total - settingsSize
            elif self.settingsPosition == 'right':
                settingsSize = self._settingsScrollArea.sizeHint().width()
                sizes[0] = total - settingsSize
                sizes[1] = settingsSize
            elif self.settingsPosition == 'top':
                settingsSize = self._settingsScrollArea.sizeHint().height()
                sizes[0] = settingsSize
                sizes[1] = total - settingsSize
            elif self.settingsPosition == 'bottom':
                settingsSize = self._settingsScrollArea.sizeHint().height()
                sizes[0] = total - settingsSize
                sizes[1] = settingsSize

            self._splitter.setSizes(sizes)

    def _hideModule(self):
        self.setVisible(not self.isVisible())

    def close(self):
        """Close the module from the commandline
        """
        self._closeModule()

    def enterEvent(self, event):
        super().enterEvent(event)
        if not getBlockingDialogs('enter-event'):
            if self.mainWindow.application.preferences.general.focusFollowsMouse:
                if self.area is not None:
                    if not self.area._isNameEditing():
                        self.setFocus()
                self.label.setModuleHighlight(True)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if not getBlockingDialogs('leave-event'):
            if (self.mainWindow and self.mainWindow.application.preferences.general.focusFollowsMouse):
                self.label.setModuleHighlight(False)

    def dragMoveEvent(self, *args):
        ev = args[0]
        if self.isDragToMaximisedModule(ev):
            self.handleDragToMaximisedModule(ev)
            return
        DockDrop.dragMoveEvent(self, *args)

    def dragLeaveEvent(self, *args):
        ev = args[0]
        DockDrop.dragLeaveEvent(self, *args)

    def dragEnterEvent(self, *args):
        ev = args[0]

        if self.isDragToMaximisedModule(ev):
            self.handleDragToMaximisedModule(ev)
            return

        if args:

            # print ('>>>', ev.source())
            data = self.parseEvent(ev)
            if DropBase.PIDS in data and isinstance(data['event'].source(), (SideBar, SideBarSearchListView)):
                if self.widgetArea:

                    ld = ev.pos().x()
                    rd = self.width() - ld
                    td = ev.pos().y()
                    bd = self.height() - td

                    mn = min(ld, rd, td, bd)
                    if mn > 30:
                        self.dropArea = "center"
                        self.area._dropArea = "center"

                    elif (ld == mn or td == mn) and mn > self.height() / 3.:
                        self.dropArea = "center"
                        self.area._dropArea = "center"
                    elif (rd == mn or ld == mn) and mn > self.width() / 3.:
                        self.dropArea = "center"
                        self.area._dropArea = "center"

                    elif rd == mn:
                        self.dropArea = "right"
                        self.area._dropArea = "right"
                        ev.accept()
                    elif ld == mn:
                        self.dropArea = "left"
                        self.area._dropArea = "left"
                        ev.accept()
                    elif td == mn:
                        self.dropArea = "top"
                        self.area._dropArea = "top"
                        ev.accept()
                    elif bd == mn:
                        self.dropArea = "bottom"
                        self.area._dropArea = "bottom"
                        ev.accept()

                    if ev.source() is self and self.dropArea == 'center':
                        # print "  no self-center"
                        self.dropArea = None
                        ev.ignore()
                    elif self.dropArea not in self.allowedAreas:
                        # print "  not allowed"
                        self.dropArea = None
                        ev.ignore()
                    else:
                        # print "  ok"
                        ev.accept()
                    self.overlay.setDropArea(self.dropArea)

                    # self.widgetArea.setStyleSheet(self.dragStyle)
                    self.update()
                    # # if hasattr(self, 'drag'):
                    # self.raiseOverlay()
                    # self.updateStyle()
                    # ev.accept()

            src = ev.source()
            if hasattr(src, 'implements') and src.implements('dock'):
                DockDrop.dragEnterEvent(self, *args)

    def dropEvent(self, event):
        if self.inDragToMaximisedModule:
            return

        if event:
            source = event.source()
            data = self.parseEvent(event)
            if hasattr(source, 'implements') and source.implements('dock'):
                CcpnModule._lastActionWasDrop = True
                DockDrop.dropEvent(self, event)
            elif DropBase.PIDS in data and len(data[DropBase.PIDS]) > 0:
                # process Pids
                self.mainWindow._processPids(data, position=self.dropArea, relativeTo=self)
                event.accept()

                # reset the dock area
                self.dropArea = None
                self.overlay.setDropArea(self.dropArea)
                self._selectedOverlay.setDropArea(self.dropArea)
            else:
                event.ignore()
                return

    def findWindow(self):
        current = self
        while current.parent() is not None:
            current = current.parent()
        return current

    def flashMessage(self, message):
        def center(window, rect):
            # https://wiki.qt.io/How_to_Center_a_Window_on_the_Screen

            window.setGeometry(
                    QtWidgets.QStyle.alignedRect(
                            QtCore.Qt.LeftToRight,
                            QtCore.Qt.AlignCenter,
                            window.size(),
                            rect,
                            )
                    )

        messageBox = QtWidgets.QMessageBox(self)
        messageBox.setText(message)
        messageBox.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        for button in messageBox.findChildren(QtWidgets.QDialogButtonBox):
            button.setVisible(False)

        messageBox.update()

        globalRect = QtCore.QRect(self.mapToGlobal(self.rect().topLeft()), self.rect().size())
        wrapper = partial(center, messageBox, globalRect)
        QtCore.QTimer.singleShot(0, wrapper)

        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(messageBox.close)
        timer.start(1500)

        messageBox.exec()

    def startDrag(self):

        self.drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        self.drag.setMimeData(mime)
        dragPixmap = self.grab()
        # make sure that the dragPixmap is not too big
        self.drag.setPixmap(dragPixmap.scaledToWidth(max(MIN_PIXMAP, min(MAX_PIXMAP, dragPixmap.width())))
                            if dragPixmap.width() < dragPixmap.height() else
                            dragPixmap.scaledToHeight(max(MIN_PIXMAP, min(MAX_PIXMAP, dragPixmap.height()))))
        self.widgetArea.setStyleSheet(self.dragStyle)
        self._raiseSelectedOverlay()
        self.updateStyle()
        self.update()

        self.drag.destroyed.connect(self._destroyed)

        # GST doesn't work in the current version but should work in 5.13, OS cursors don't have pixmaps :|
        # forbiddenCursorPixmap = QtGui.QCursor(QtCore.Qt.ForbiddenCursor).pixmap()
        # self.drag.setDragCursor(forbiddenCursorPixmap, QtCore.Qt.IgnoreAction)

        dragResult = self.drag.exec_()
        endPosition = QtGui.QCursor.pos()

        self.updateStyle()

        # GST we have to assume the drag succeeded currently as we don't get any events
        # that report on whether the drag has failed. Indeed this effectively a failed drag...
        globalDockRect = self.getDockArea().frameGeometry()

        targetWidget = QtWidgets.QApplication.instance().widgetAt(endPosition)
        if (
                (self.drag.target() is None)
                and (not globalDockRect.contains(endPosition))
                and targetWidget is None
        ):
            self.float()
            window = self.findWindow()
            window.move(endPosition)

            # this is because we could have dragged into another application
            # this may not work under windows
            originalWindow = self.findWindow()
            originalWindow.raise_()
            originalWindow.show()
            originalWindow.activateWindow()

            window.raise_()
            window.show()
            window.activateWindow()

    def _destroyed(self, ev):
        self._selectedOverlay.setDropArea(None)

    def _raiseSelectedOverlay(self):
        self._selectedOverlay.setDropArea(True)
        self._selectedOverlay.raise_()

    def _hideHelpButton(self):
        self.label.helpButton.hide()

    def resizeEvent(self, ev):
        self._selectedOverlay._resize()
        self._borderOverlay._resize()
        super().resizeEvent(ev)


#=========================================================================================
# CcpnModuleLabel
#=========================================================================================

class CcpnModuleLabel(DockLabel):
    """
    Subclassing DockLabel to modify appearance and functionality
    """

    labelSize = 16
    TOP_LEFT = 'TOP_LEFT'
    TOP_RIGHT = 'TOP_RIGHT'

    # TODO:GEERTEN check colours handling
    # defined here, as the updateStyle routine is called from the
    # DockLabel instantiation; changed later on

    sigDragEntered = QtCore.pyqtSignal(object, object)

    @staticmethod
    def getMaxIconSize(icon):
        iconSizes = [max((size.height(), size.width())) for size in icon.availableSizes()]
        return max(iconSizes)

    def __init__(self, name, module, showCloseButton=True, closeCallback=None, enableSettingsButton=False,
                 settingsCallback=None,
                 helpButtonCallback=None, ):

        self.buttonBorderWidth = 1
        self.buttonIconMargin = 1
        self.buttonCornerRadius = 3
        self.labelRadius = 3

        self.labelSize = (getWidgetFontHeight(size='MEDIUM') or 12) + 2
        self._fontSize = self.labelSize - 4
        super().__init__(name, closable=showCloseButton, )  # fontSize=_fontSize)
        # super().__init__(name, module, showCloseButton=showCloseButton, )  # fontSize=_fontSize)

        self.module = module
        self.dock = module
        self.fixedWidth = True

        setWidgetFont(self, size='MEDIUM')

        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        # self.closeButton.setStyleSheet(
        #         f'border: 0px solid {BORDERNOFOCUS_COLOUR};border-radius: 1px;background-color: transparent;'
        #         )

        from ccpn.ui._implementation.SpectrumDisplay import SpectrumDisplay

        allowSpace = not isinstance(self.module, SpectrumDisplay)
        self.nameEditor = NameEditor(self, text=self.labelName, allowSpace=allowSpace)
        self.nameEditor.hide()

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLineWidth(0)

        if showCloseButton:
            # button is already there because of the DockLabel init
            self.closeButton.setIconSize(QtCore.QSize(self._fontSize, self._fontSize))

            if closeCallback is None:
                raise RuntimeError('Requested closeButton without callback')
            else:
                self.closeButton.clicked.connect(closeCallback)
            self.setupLabelButton(self.closeButton, 'close-module', CcpnModuleLabel.TOP_RIGHT)

        # Settings
        self.settingsButtons = ButtonList(self, texts=['', ''],
                                          icons=['icons/gearbox', 'icons/system-help'],
                                          callbacks=[settingsCallback, helpButtonCallback],
                                          enableFocusBorder=False,
                                          )
        self.settingsButtons.getLayout().setSpacing(0)  # remove any gaps
        self.settingsButton = self.settingsButtons.buttons[0]
        self.helpButton = self.settingsButtons.buttons[1]
        self.setupLabelButton(self.settingsButton, position=CcpnModuleLabel.TOP_LEFT)
        self.setupLabelButton(self.helpButton, position=CcpnModuleLabel.TOP_LEFT)
        if self.module._helpFilePath is None or not aPath(self.module._helpFilePath).exists():
            self.helpButton.setEnabled(False)
        self.settingsButton.setEnabled(enableSettingsButton)

        self.updateStyle()

        # flag to disable dragMoveEvent during a doubleClick
        self._inDoubleClick = False

        QtWidgets.QApplication.instance()._sigPaletteChanged.connect(self._checkPalette)

    def _checkPalette(self, pal: QtGui.QPalette, *args):
        self.updateStyle()

    @property
    def labelName(self):
        return self.module.id

    def _showNameEditor(self):
        """
        show the name editor and give full focus to start typing.
        """

        self.nameEditor.show()

    def _renameLabel(self, name=None):
        name = name or self.nameEditor.get()
        self.nameEditor.hide()
        self.module.renameModule(name)

    def setupLabelButton(self, button, iconName=None, position=None):
        if iconName:
            icon = Icon(f'icons/{iconName}')
            button.setIcon(icon)
        # retinaIconSize = self.getMaxIconSize(icon) // 2
        # retinaIconSize = self.labelSize - 4

        button.setIconSize(QtCore.QSize(self._fontSize, self._fontSize))

        if position == CcpnModuleLabel.TOP_RIGHT:
            styleInfo = (self.buttonBorderWidth, 0, self.buttonCornerRadius)
        elif position == CcpnModuleLabel.TOP_LEFT:
            styleInfo = (self.buttonBorderWidth, self.buttonCornerRadius, 0)
        else:
            raise TypeError(
                    f"button position must be one of {', '.join([CcpnModule.TOP_LEFT, CcpnModule.TOP_RIGHT])}"
                    )

        # GST colours are hard coded... help please I need  a central source for
        # these presumably a color palette or scheme
        # button.setStyleSheet(""" border: %ipx solid #a9a9a9 ;
        #                          border-top-left-radius: %ipx;
        #                          border-top-right-radius: %ipx;
        #                          border-bottom-left-radius: 0px;
        #                          border-bottom-right-radius: 0px;
        #                          background-color: #ececec ;  """ % styleInfo)
        buttonSize = self.labelSize + 4
        # button.setMinimumSize(QtCore.QSize(buttonSize, buttonSize))
        button.setMaximumSize(
                QtCore.QSize(buttonSize, buttonSize))  # just let the button expand a little to fit the label
        button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def setModuleHighlight(self, hightlighted=False):
        self.setDim(hightlighted)

    def updateStyle(self):
        # get the colours from the colourScheme
        if self.dim:
            fg = getColours()[CCPNMODULELABEL_FOREGROUND]
            bg = getColours()[CCPNMODULELABEL_BACKGROUND]
            border = getColours()[CCPNMODULELABEL_BORDER]
        else:
            fg = getColours()[CCPNMODULELABEL_FOREGROUND_ACTIVE]
            bg = getColours()[CCPNMODULELABEL_BACKGROUND_ACTIVE]
            border = getColours()[CCPNMODULELABEL_BORDER_ACTIVE]

        if self.orientation == 'vertical':
            self.vStyle = """DockLabel {
                background-color : %s;
                color : %s;
                border-top-right-radius: 2px;
                border-top-left-radius: %s;
                border-bottom-right-radius: 2px;
                border-bottom-left-radius: %s;
            }""" % (bg, fg, self.labelRadius, self.labelRadius)
            self.setStyleSheet(self.vStyle)
        else:
            self.hStyle = """DockLabel {
                background-color : %s;
                color : %s;
                border-top-right-radius: %s;
                border-top-left-radius: %s;
                border-bottom-right-radius: 0px;
                border-bottom-left-radius: 0px;
            }""" % (bg, fg, self.labelRadius, self.labelRadius)
            self.setStyleSheet(self.hStyle)

    def _copyPidToClipboard(self):
        self.module.pid.toClipboard()

    def _createContextMenu(self):
        # avoiding circular imports
        from ccpn.ui.gui.widgets.Menu import Menu

        contextMenu = Menu('', self, isFloatWidget=True)
        contextMenu.setToolTipsVisible(True)
        renameAction = contextMenu.addAction('Rename', self._showNameEditor)
        detachAction = contextMenu.addAction('Detach from Drop Area', self.module._detach)
        contextMenu.addSeparator()
        contextMenu.addAction('Close', self.module._closeModule)
        if len(self.module.area.ccpnModules) > 1:
            contextMenu.addAction('Close Others', partial(self.module.area._closeOthers, self.module))
            contextMenu.addAction('Close All', self.module.area._closeAll)
        contextMenu.addSeparator()

        gidAction = contextMenu.addAction('Copy Gid to clipboard', self._copyPidToClipboard)
        gidAction.setToolTip('Usage, On Python Console type: ui.getByGid(Pasted_Gid) to get this module as an object')

        renameAction.setEnabled(self.module._allowRename)
        # numDocks = len(self.module.getDocksInParentArea())
        #
        # if not self.module.maximised and numDocks > 1:
        #     contextMenu.addAction('Maximise', self.module.toggleMaximised)
        # elif self.module.maximised:
        #     contextMenu.addAction('Restore', self.module.toggleMaximised)
        #
        # contextMenu.addAction('Float', self.module.float)

        return contextMenu

    def _modulesMenu(self, menuName, module):
        # avoiding circular imports
        from ccpn.ui.gui.widgets.Menu import Menu

        menu = Menu(menuName.title(), self, isFloatWidget=True)
        if module and module.area:
            toAll = menu.addAction('All', partial(self.module.area.moveModule, module, menuName, None))
            for availableModule in self.module.area.ccpnModules:
                if availableModule != module:
                    toModule = menu.addAction(str(availableModule.name()),
                                              partial(self.module.area.moveModule, module, menuName, availableModule))
            return menu

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """
        Re-implementation of the  mouse event so a right mouse context menu can be raised.
        """
        if self.module and self.module.area:
            self.module.area._finaliseAllNameEditing()  # so to close the on-going operation

        if event.button() == QtCore.Qt.RightButton:
            if menu := self._createContextMenu():
                menu.move(event.globalPos().x(), event.globalPos().y() + 10)
                menu.exec()
        else:
            super(CcpnModuleLabel, self).mousePressEvent(event)

    def paintEvent(self, ev):
        """
        Copied from the parent VerticalLabel class to allow for modification in StyleSheet
        """
        p = QtGui.QPainter(self)

        # GWV: this moved the label in vertical mode and horizontal, after some trial and error
        # NOTE: A QRect can be constructed with a set of left, top, width and height integers
        if self.orientation == 'vertical':
            added = 2
            p.rotate(-90)
            rgn = QtCore.QRect(-self.height(), 0, self.height(), self.width() + added)
        else:
            rgn = self.contentsRect()
            added = 4
            rgn = QtCore.QRect(rgn.left(), rgn.top(), rgn.width(), rgn.height() + added)

        #align = self.alignment()
        # GWV adjusted
        align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter
        label = self.labelName
        self.hint = p.drawText(rgn, align, label)
        p.end()

        if self.orientation == 'vertical':
            self.setMinimumWidth(self.labelSize)
            self.setMaximumWidth(self.labelSize)
        else:
            self.setMinimumHeight(self.labelSize)
            self.setMaximumHeight(self.labelSize)

    def mouseMoveEvent(self, ev):
        """Handle the mouse move event to spawn a drag event - copied from super-class
        """
        if hasattr(self, 'pressPos') and not self._inDoubleClick:
            if not self.mouseMoved:
                lpos = ev.position() if hasattr(ev, 'position') else ev.localPos()
                self.mouseMoved = (lpos - self.pressPos).manhattanLength() > QtWidgets.QApplication.startDragDistance()

            if self.mouseMoved and ev.buttons() == QtCore.Qt.MouseButton.LeftButton:
                # emit a drag started event
                self.sigDragEntered.emit(self.parent(), ev)
                self.dock.startDrag()

            ev.accept()

    def mouseDoubleClickEvent(self, ev):
        """Handle the double click event
        """
        # start a small timer when doubleClicked
        # disables the dragMoveEvent whilst in a doubleClick
        self._inDoubleClick = True
        QtCore.QTimer.singleShot(QtWidgets.QApplication.instance().doubleClickInterval() * 2,
                                 self._resetDoubleClick)

        super(CcpnModuleLabel, self).mouseDoubleClickEvent(ev)

        # if ev.button() == QtCore.Qt.LeftButton:
        #     self.dock.toggleMaximised()

    def _resetDoubleClick(self):
        """reset the double click flag
        """
        self._inDoubleClick = False

    def resizeEvent(self, ev):
        if hasattr(self, 'closeButton') and self.closeButton:
            if self.orientation == 'vertical':
                self.layout().addWidget(self.closeButton, 0, 0, alignment=QtCore.Qt.AlignTop)
            else:
                self.layout().addWidget(self.closeButton, 0, 3, alignment=QtCore.Qt.AlignRight)

        if hasattr(self, 'settingsButtons') and self.settingsButtons:
            if self.orientation == 'vertical':
                self.layout().addWidget(self.settingsButtons, 0, 0, alignment=QtCore.Qt.AlignBottom)
            else:
                self.layout().addWidget(self.settingsButtons, 0, 0, alignment=QtCore.Qt.AlignLeft)

        if hasattr(self, 'nameEditor') and self.nameEditor:
            self.layout().addWidget(self.nameEditor, 0, 1, alignment=QtCore.Qt.AlignCenter)

        super(DockLabel, self).resizeEvent(ev)


INVALIDROWCOLOUR = QtGui.QColor('lightpink')
WARNINGROWCOLOUR = QtGui.QColor('palegoldenrod')

EXTRA_CHARACTERS_ALLOWED = [' ',  # extra characters allowed when renaming a Module (except spectrumDisplays)
                            '_',
                            '(',
                            ')',
                            ':'
                            ]


#=========================================================================================
# LabelNameValidator
#=========================================================================================

class LabelNameValidator(QtGui.QValidator):
    """ Make sure the newly typed module name on a GUI is unique.
    """

    def __init__(self, parent, labelObj, allowSpace=True):
        super().__init__(parent=parent)
        self.baseColour = self.parent().palette().color(QtGui.QPalette.Base)
        self._parent = parent
        self._labelObj = labelObj
        self._isNameAvailableFunc = str  # str as placeholder.
        self._allowSpace = allowSpace
        self._isValidState = True
        self._messageState = ''

    def _setNameValidFunc(self, func):
        """
        set a custom validation function to perform during the built-in validate method, like isNameAvailable...
        """
        self._isNameAvailableFunc = func

    def _isValidInput(self, value):
        extras = ''.join(EXTRA_CHARACTERS_ALLOWED)
        notAllowedSequences = {
            'No_strings'        : '^\s*$',
            'Space_At_Start'    : '^\s',
            'Space_At_End'      : '\s$',
            'Empty_Spaces'      : '\s',
            'Non-Alphanumeric'  : '\W',
            'Illegal_Characters': f'[^A-Za-z0-9{extras}]+',
            }
        valids = [True]
        if value is None:
            valids.append(False)
            self._isValidState, self._messageState = False, 'Contains None'
        if self._allowSpace:
            notAllowedSequences.pop('Empty_Spaces')
            notAllowedSequences.pop('Non-Alphanumeric')
        for key, seq in notAllowedSequences.items():
            if re.findall(seq, value):
                valids.append(False)
                self._isValidState, self._messageState = False, 'Name cannot include:\n%s' % key.replace('_', ' ')
        return all(valids)

    def _setIntermediateStatus(self):
        palette = self.parent().palette()
        palette.setColor(QtGui.QPalette.Base, INVALIDROWCOLOUR)
        state = QtGui.QValidator.Intermediate  # entry is NOT valid, but can continue editing
        self.parent().setPalette(palette)
        return state

    def _setAcceptableStatus(self):
        palette = self.parent().palette()
        palette.setColor(QtGui.QPalette.Base, self.baseColour)
        state = QtGui.QValidator.Acceptable
        self.parent().setPalette(palette)
        return state

    def _getMessageState(self):
        return self._messageState

    def validate(self, name, p_int):

        startingName = self._labelObj.module.id
        state = QtGui.QValidator.Acceptable

        if startingName == name:
            state = self._setAcceptableStatus()
            self._isValidState, self._messageState = True, 'Same name as original'
            return state, name, p_int

        if self._isNameAvailableFunc(name):
            self._isValidState, self._messageState = True, 'Name available'
            state = self._setAcceptableStatus()

        if not self._isValidInput(name):
            state = self._setIntermediateStatus()

        if not self._isNameAvailableFunc(name):
            state = self._setIntermediateStatus()
            self._isValidState, self._messageState = False, 'Name already taken'

        return state, name, p_int

    def clearValidCheck(self):
        palette = self.parent().palette()
        palette.setColor(QtGui.QPalette.Base, self.baseColour)
        self.parent().setPalette(palette)

    def resetCheck(self):
        self.validate(self.parent().text(), 0)

    @property
    def checkState(self):
        state, _, _ = self.validate(self.parent().text(), 0)
        return state


#=========================================================================================
# NameEditor
#=========================================================================================

class NameEditor(LineEdit):
    """LineEdit widget that contains validator for checking filePaths exists
    """

    def __init__(self, parent, allowSpace=True, **kwds):
        super().__init__(parent=parent, **kwds)

        self._parent = parent  # the LabelObject
        self.setValidator(LabelNameValidator(parent=self, labelObj=self._parent, allowSpace=allowSpace))
        self.validator().resetCheck()
        self.validator()._setNameValidFunc(self._parent.module._isNameAvailable)
        self.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter)
        self.setMaximumHeight(self._parent.labelSize)
        # self.editingFinished.connect(self._parent._renameLabel)
        self.returnPressed.connect(self._parent._renameLabel)
        self.setStyleSheet('LineEdit { padding: 0px 0px 0px 0px; }')
        self.setMinimumWidth(200)

    def show(self):
        self._setFocus()
        self.set(self._parent.labelName)
        super(LineEdit, self).show()

    def _setFocus(self):
        # self.setFocusPolicy(QtCore.Qt.StrongFocus) # this is not enough to show the cursor and give focus.
        pos = QtCore.QPointF(25, 10)
        # Transfer focus, otherwise the click does not seem to be handled
        qc = QtCore.Qt
        self.setFocus(qc.OtherFocusReason)
        pressEv = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, pos, qc.LeftButton, qc.LeftButton, qc.NoModifier)
        self.mousePressEvent(pressEv)
        releaseEv = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, pos, qc.LeftButton, qc.LeftButton,
                                      qc.NoModifier)
        self.mouseReleaseEvent(releaseEv)

    def focusOutEvent(self, ev):
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        super(LineEdit, self).focusOutEvent(ev)


#=========================================================================================
# DropAreaSelectedOverlay
#=========================================================================================

class DropAreaSelectedOverlay(QtWidgets.QWidget):
    """Overlay widget that draws highlight over the current module during a drag-drop operation
    """

    def __init__(self, parent):
        """Initialise widget
        """
        QtWidgets.QWidget.__init__(self, parent)
        self.dropArea = None
        self.hide()
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.setAutoFillBackground(False)
        # colour from DockAreaOverlay so looks consistent
        self._highlightBrush = QtGui.QBrush(QtGui.QColor(100, 100, 255, 50))
        self._highlightPen = QtGui.QPen(QtGui.QColor(50, 50, 150), 3)


    def setDropArea(self, area):
        """Set the widget coverage, either hidden, or a rectangle covering the module
        """
        self.dropArea = area
        if area is None:
            self.hide()
        else:
            prgn = self.parent().rect()
            rgn = QtCore.QRect(prgn)

            self.setGeometry(rgn)
            self.show()

        self.update()

    def _resize(self):
        """Resize the overlay, sometimes the overlay is temporarily visible while the module is moving
        """
        # called from ccpnModule during resize to update rect()
        self.setDropArea(self.dropArea)

    def paintEvent(self, ev):
        """Paint the overlay to the screen
        """
        if self.dropArea is None:
            return
        # create a transparent rectangle and painter over the widget
        p = QtGui.QPainter(self)
        rgn = self.rect()
        p.setBrush(self._highlightBrush)
        p.setPen(self._highlightPen)
        p.drawRect(rgn)
        p.end()


#=========================================================================================
# BorderOverlay
#=========================================================================================

class BorderOverlay(QtWidgets.QWidget):
    """Overlay widget that draws a border around the whole of the module
    ensuring a nice clean edge
    """

    def __init__(self, parent, borderColour=None):
        """Initialise widget
        """
        QtWidgets.QWidget.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        c1 = self._borderColour = borderColour or QtGui.QColor(getColours()[BORDERNOFOCUS])
        c2 = self._backgroundColour = parent.palette().color(parent.backgroundRole())
        self._blendColour = QtGui.QColor((c1.red() + c2.red()) // 2,
                                         (c1.green() + c2.green()) // 2,
                                         (c1.blue() + c2.blue()) // 2,
                                         (c1.alpha() + c2.alpha()) // 2
                                         )

    def _resize(self):
        """Resize the overlay
        """
        prgn = self.parent().rect()
        rgn = QtCore.QRect(prgn)
        self.setGeometry(rgn)

    def paintEvent(self, ev):
        """Paint the overlay to the screen
        """
        # clear the bottom corners, and draw a rounded rectangle to cover the edges
        p = QtGui.QPainter(self)
        p.translate(0.5, 0.5)  # move to pixel-centre
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rgn = self.rect().adjusted(0, 0, -1, -1)
        w = rgn.width()
        h = rgn.height()
        # clear and smooth the bottom corners
        pal = self.palette()
        p.setPen(QtGui.QPen(pal.window(), 3))  # background
        p.drawPoints(QtCore.QPoint(0, h),
                     QtCore.QPoint(w, h),
                     )
        # draw the new rectangle around the module
        p.setPen(QtGui.QPen(pal.mid(), 1))  # border
        p.drawRoundedRect(rgn, 2, 2)
        p.end()


#=========================================================================================
# CcpnTableModule
#=========================================================================================

class CcpnTableModule(CcpnModule):
    """Module to be used for Table GUI's.
    Implemented to allow hiddenColumn saving.
    """
    def __init__(self, mainWindow, name, *args, **kwds):
        super().__init__(mainWindow=mainWindow, name=name, *args, **kwds)

    @CcpnModule.widgetsState.getter
    def widgetsState(self):
        """Add extra parameters to the state-dict for hidden-columns.
        """
        state = super().widgetsState
        if self._hiddenColumns is not None:
            state |= {'_hiddenColumns': self._hiddenColumns}
        return state

    @property
    def _hiddenColumns(self) -> list[str] | None:
        """Return the hidden-columns for the primary table-widget.
        If undefined, returns None.
        """
        with contextlib.suppress(Exception):
            return self._tableWidget.headerColumnMenu.hiddenColumns

    def _setHiddenColumns(self, value: list[str] | None = None):
        """Set the hidden-columns for the primary table-widget.
        """
        if value is not None:
            if not isinstance(value, list):
                raise TypeError(f'{self.__class__.__name__}.hiddenColumns must be list[str] of None')
        self._tableWidget.headerColumnMenu.hiddenColumns = value

    def _setClassDefaultHidden(self, hiddenColumns: list[str] | None):
        """Copy the hidden-columns to the class; to be set when the next table is opened.
        """
        self._tableWidget.setClassDefaultColumns(hiddenColumns)

    def _saveColumns(self, hiddenColumns: list[str] | None = None):
        """Allows hiddenColumns to be saved to widgetState

        Specifically saves to _seenModuleStates dict.
        Normally called by the closeModule method.

        :param list|None hiddenColumns: list of columns to save as hidden,
         if blank then will automatically try to use
         self._tableWidget.headerColumnMenu.hiddenColumns to find values
        """
        wState = self.widgetsState  # local state-dict
        if hiddenColumns is not None:
            # append hidden-column list
            wState['_hiddenColumns'] = hiddenColumns
        else:
            try:
                wState['_hiddenColumns'] = self._hiddenColumns
                self._setClassDefaultHidden(self._hiddenColumns)
            except Exception as es:
                getLogger().debug(f'Table Columns for {self.moduleName} unsaved: {es}')

    def _restoreColumns(self, hiddenColumns: list[str] | None):
        """Restore the hidden columns from the widgetState dict.
        """
        try:
            self._setHiddenColumns(hiddenColumns)
        except AssertionError as es:
            getLogger().debug(f'Could not restore table columns: {es}')

    def restoreWidgetsState(self, **widgetsState):
        """Subclassed version for tables
        """
        super().restoreWidgetsState(**widgetsState)
        try:
            if (hColumns := widgetsState.get('_hiddenColumns', None)) is not None:
                self._restoreColumns(hColumns)
        except Exception as es:
            print(es)

    def _closeModule(self):
        """
        CCPN-INTERNAL: used to close the module
        """
        self._saveColumns()
        super()._closeModule()

