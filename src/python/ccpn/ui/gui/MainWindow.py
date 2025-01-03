"""
This file contains the MainWindow class
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
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
__dateModified__ = "$dateModified: 2025-01-03 18:50:58 +0000 (Fri, January 03, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: gvuister $"
__date__ = "$Date: 2023-01-24 10:28:48 +0000 (Tue, January 24, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
import time
from functools import partial, partialmethod

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import QKeySequence
from PyQt5.QtCore import pyqtSlot

from ccpn.core.lib.WeakRefLib import WeakRefDescriptor
from ccpn.util import Logging
from ccpn.core.Project import Project

from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.lib.ContextManagers import undoBlock, undoBlockWithoutSideBar, notificationEchoBlocking

## MainWindow class
from ccpn.ui._implementation.Window import Window as _CoreClassMainWindow

from ccpn.ui.gui import guiSettings

from ccpn.ui.gui.lib.mouseEvents import SELECT, PICK, MouseModes, \
    setCurrentMouseMode, getCurrentMouseMode
from ccpn.ui.gui.lib import GuiStrip
from ccpn.ui.gui.lib.Shortcuts import Shortcuts
from ccpn.ui.gui.guiSettings import (getColours, GUITABLE_SELECTED_BACKGROUND, consoleStyle)

from ccpn.ui.gui.modules.MacroEditor import MacroEditor

from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.PlotterWidget import plotter
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.Action import Action
from ccpn.ui.gui.widgets.IpythonConsole import IpythonConsole
from ccpn.ui.gui.widgets.Menu import Menu, MenuBar, SHOWMODULESMENU, CCPNMACROSMENU, \
    USERMACROSMENU, TUTORIALSMENU, PLUGINSMENU, CCPNPLUGINSMENU, HOWTOSMENU
from ccpn.ui.gui.widgets.SideBar import SideBar  #,SideBar
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.CcpnModuleArea import CcpnModuleArea
from ccpn.ui.gui.widgets.Splitter import Splitter
from ccpn.ui.gui.widgets.Font import setWidgetFont, getFontHeight
from ccpn.ui.gui.widgets.Label import Label, ActiveLabel
from ccpn.ui.gui.widgets.MessageDialog import showWarning, progressManager, showInfo, showError
from ccpn.util.Common import camelCaseToString
from ccpn.util.Logging import getLogger
from ccpn.util.decorators import logCommand
from ccpn.util.Colour import colorSchemeTable

#from collections import OrderedDict
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.lib.MenuActions import _openItemObject

from ccpn.framework.lib.DataLoaders.DirectoryDataLoader import DirectoryDataLoader


# For readability there should be a class:
# _MainWindowMenus which (Only!) has menu instantiations, the callbacks to initiate them, + relevant methods
# The latter should all be private methods!
#
# The docstring of GuiMainWindow should detail how this setup is

MAXITEMLOGGING = 4
KEY_DELAY = 0.75

_PEAKS = 1
_INTEGRALS = 2
_MULTIPLETS = 4
_INTEGRAL_PEAKS = 8
_MULTIPLET_PEAKS = 16

READONLYCHANGED = 'readOnlyChanged'
_transparent = QtGui.QColor('orange')


# def _paintEvent(widget: QtWidgets.QWidget, event: QtGui.QPaintEvent, func=None) -> None:
#     result = func(widget, event)
#     if widget.hasFocus():
#         p = QtGui.QPainter(widget)
#         p.translate(0.5, 0.5)  # move to pixel-centre
#         p.setRenderHint(QtGui.QPainter.Antialiasing, True)
#         col = QtGui.QColor('dodgerblue')  # Base._highlightVivid
#         col.setAlpha(255)
#         pen = QtGui.QPen(col)
#         p.setPen(pen)
#         p.drawRoundedRect(widget.rect().adjusted(0, 0, -1, -1), 2, 2)
#         col.setAlpha(40)
#         p.setPen(col)
#         p.drawRoundedRect(widget.rect().adjusted(1, 1, -2, -2), 1.7, 1.7)
#         p.end()
#     return result
#

# _paintQLineEdit = QtWidgets.QLineEdit.paintEvent
# QtWidgets.QLineEdit.paintEvent = partialmethod(_paintEvent, func=_paintQLineEdit)
# _paintQSpinBox = QtWidgets.QSpinBox.paintEvent
# QtWidgets.QSpinBox.paintEvent = partialmethod(_paintEvent, func=_paintQSpinBox)
# _paintQDoubleSpinBox = QtWidgets.QDoubleSpinBox.paintEvent
# QtWidgets.QDoubleSpinBox.paintEvent = partialmethod(_paintEvent, func=_paintQDoubleSpinBox)
# _pp = QtWidgets.QToolButton.paintEvent
# QtWidgets.QToolButton.paintEvent = partialmethod(_paintEvent, func=_pp)


class GuiMainWindow(QtWidgets.QMainWindow, Shortcuts):
    # inherits NotifierBase from _Implementation.Window

    WindowMaximiseMinimise = QtCore.pyqtSignal(bool)

    # allows type-checking to recognise attributes
    application = WeakRefDescriptor()
    current = WeakRefDescriptor()

    def __init__(self, application=None):

        # Shortcuts only inserts methods
        super().__init__()

        # format = QtGui.QSurfaceFormat()  # I think these can be removed now
        # format.setSwapInterval(0)
        # QtGui.QSurfaceFormat.setDefaultFormat(format)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        # Layout
        layout = self.layout()

        logger = getLogger()
        logger.debug('GuiMainWindow: layout: %s' % layout)

        if layout is not None:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        self.setGeometry(200, 40, 1100, 900)

        # GuiWindow.__init__(self, application)
        self.application = application
        self.current = application.current
        # self._project set by model; and there is a property self.project

        # Module area
        self.moduleArea = CcpnModuleArea(mainWindow=self)
        self.pythonConsoleModule = None  # Python console module; defined upon first time Class initialisation. Either by toggleConsole or Restoring layouts
        self.namespace = None

        logger.debug('GuiMainWindow.moduleArea: layout: %s' % self.moduleArea.layout)  ## pyqtgraph object
        self.moduleArea.setGeometry(0, 0, 1000, 800)
        # GST can't seem to do this with style sheets...
        self.moduleArea.setContentsMargins(0, 2, 2, 0)
        self.setCentralWidget(self.moduleArea)
        self._shortcutsDict = {}

        setWidgetFont(self, )

        self._setupWindow()
        self._setupMenus()
        self._initProject()
        self._setShortcuts(mainWindow=self)
        self._setUserShortcuts(preferences=self.application.preferences, mainWindow=self)
        self._setMouseMode(SELECT)
        # Notifiers
        self._setupNotifiers()

        self.feedbackPopup = None
        self._previousStrip = None
        self._currentStrip = None

        self.setWindowIcon(Icon('icons/ccpn-icon'))
        # self.fileIcon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon, None, self)
        # self.disabledFileIcon = self.makeDisabledFileIcon(self.fileIcon)

        # blank display opened later by the _initLayout if there is nothing to show otherwise
        self.statusBar().showMessage('Ready')
        setCurrentMouseMode(SELECT)

        self._project._undo.undoChanged.add(self._undoChangeCallback)

        # self.setUnifiedTitleAndToolBarOnMac(True) #uncomment this to remove the extra title bar on osx 10.14+

        self._initKeyTimer()
        self._initReadOnlyIcon()

        # hide the window here and make visible later
        self.hide()

    @property
    def moduleArea(self):
        return self._moduleAreaRef()

    @moduleArea.setter
    def moduleArea(self, value):
        import weakref

        def remove(wref, selfref=weakref.ref(self)):
            getLogger().debug(f'{consoleStyle.fg.darkred}Clearing moduleArea '
                              f'{wref}:{selfref()} {consoleStyle.reset}')

        self._moduleAreaRef = weakref.ref(value, remove)
        getLogger().debug(f'{consoleStyle.fg.darkgreen}Setting moduleArea '
                          f'{self._moduleAreaRef()}{consoleStyle.reset}')

    def show(self):
        # self._checkPalette(self.palette())
        # self.application.ui._changeThemeInstant()
        # catch the initial palette-changed signal
        QtWidgets.QApplication.instance().sigPaletteChanged.connect(self._checkPalette)
        super().show()
        # install handler to resize when moving between displays
        #   cannot be done in __init__ as crashes on linux/windows :O
        self.window().windowHandle().screenChanged.connect(self._screenChangedEvent)

    def _checkPalette(self, pal: QtGui.QPalette, theme: str = None, themeColour: str = None, themeSD: str = None):
        # test the stylesheet of the QTableView
        styleSheet = """QPushButton { color: palette(text); }
                        QToolTip {
                            background-color: %(TOOLTIP_BACKGROUND)s;
                            color: %(TOOLTIP_FOREGROUND)s;
                            font-size: %(_fontSize)spt;
                            border: 1px solid %(TOOLTIP_FOREGROUND)s;
                            qproperty-margin: 4; 
                        }
                        QMenu::item:disabled { color: palette(dark); }
                        QMenu::separator {
                            height: 1px;
                            background: qlineargradient(
                                            x1: 0, y1: -1, x2: 0, y2: 8,
                                            stop: 0 palette(base),
                                            stop: 1 palette(text)
                                        );
                        }
                        QMenuBar { color: palette(text); }
                        QMenuBar::item:disabled { color: palette(dark); }
                        QProgressBar { text-align: center; }
                        """
        # there is also some weird stuff with the qprogressbar text-colour:
        #   the left-edge of the text-label is its local 0%, the right-edge its local 100%,
        #   and the text-label is coloured highlighttedtext|text based on the progress %
        #   it doesn't follow the edge of the progress-chunk :|
        #   ... but I think the stylesheet sometimes overwrites this
        # set stylesheet
        base = pal.base().color().lightness()  # use as a guide for light/dark theme
        colours = getColours()
        highlight = pal.highlight().color()
        colours[GUITABLE_SELECTED_BACKGROUND] = highlight.fromHslF(highlight.hueF(),
                                                                   0.55 if base > 127 else 0.65,
                                                                   0.80 if base > 127 else 0.35,
                                                                   ).name()
        colours['_fontSize'] = self.font().pointSize()
        colours['_BORDER_WIDTH'] = 2  # need to grab from the table-instance :|
        self.ui.qtApp.setStyleSheet(styleSheet % colours)

        # store the colours in the baseclass, is this the best place?
        Base._highlight = highlight
        Base._highlightMid = QtGui.QColor.fromHslF(highlight.hueF(), 0.75, 0.65)
        Base._basePalette = pal
        Base._transparent = pal.highlight().color()  # grab again to stop overwrite
        Base._transparent.setAlpha(40)
        # pass through the palette-changed to other widgets
        self.ui.qtApp._sigPaletteChanged.emit(pal, theme, themeColour, themeSD)
        getLogger().debug(f'{consoleStyle.fg.darkblue}qtApp changePalette event{consoleStyle.reset}')

    def _initReadOnlyIcon(self):
        """Add icon to the statusBar that reflects the read-only state of the current project
        The icon can be clicked to lock/unlock the project.
        """
        self._lockedIcon = Icon('icons/locked')
        self._unlockedIcon = Icon('icons/unlocked')
        self._pixmapWidth = getFontHeight()

        self._readOnlyState = ActiveLabel(self, mainWindow=self)
        self._readOnlyState.setFixedSize(self._pixmapWidth + 4, self._pixmapWidth + 4)
        self._readOnlyState.setPixmap(self._unlockedIcon.pixmap(self._pixmapWidth, self._pixmapWidth))
        self._readOnlyState.setToolTip('The read-only status of the project')
        self._readOnlyState.setEnabled(False)  # will enable with the state of the project once it has loaded

        self.statusBar().addPermanentWidget(self._readOnlyState, 0)

        self._readOnlyState.setSelectionCallback(self._toggleReadOnlyState)
        # need notifier on changing the setting in the project

    def _toggleReadOnlyState(self, readOnly=None):
        """Toggle the read-only status of the current project
        """
        if self.application.isApplicationReadOnly:
            showWarning('Set readOnly',
                        'Cannot change the readOnly state of the project as application is in readOnly mode.\n'
                        'This has probably been set with the --read-only flag at startup.\n'
                        'To allow unlocking, enter the following command in the python-console:\n'
                        '    application.setApplicationReadOnly(False)')
            return
        if readOnly is None:
            # toggle the state
            readOnly = not self.project.readOnly  # includes the application state
        self.project.setReadOnly(readOnly)
        QtCore.QTimer.singleShot(0, self._setReadOnlyIcon)

    def _setReadOnlyIcon(self):
        """Set the read-only icon to locked/unlocked.
        """
        readOnly = self.project.readOnly
        if readOnly:
            self._readOnlyState.setPixmap(self._lockedIcon.pixmap(self._pixmapWidth, self._pixmapWidth))
            self._readOnlyState.setToolTip('The project is marked as read-only.\n'
                                           'Click here to unlock, or use the command:\n'
                                           'project.setReadOnly(False)\n'
                                           'from the python-console.')
        else:
            self._readOnlyState.setPixmap(self._unlockedIcon.pixmap(self._pixmapWidth, self._pixmapWidth))
            self._readOnlyState.setToolTip('The project is unlocked.\n'
                                           'Click here to lock, or use the command:\n'
                                           'project.setReadOnly(True)\n'
                                           'from the python-console.')

        self._readOnlyState.setEnabled(True)
        self._readOnlyState.updateGeometry()

    def _projectNotifierCallback(self, data):
        """Notifier responds to change in the read-only state of the current project,
        and updates the read-only icon.
        """
        if (specifiers := data.get(Notifier.SPECIFIERS)) and specifiers.get(READONLYCHANGED) is not None:
            QtCore.QTimer.singleShot(0, self._setReadOnlyIcon)

    def _initKeyTimer(self):
        """
        Create a timer to reset the keysequences by simulating an escape key if nothing pressed for a second
        only affects this widget, runs every 0.5s
        add a small label to the statusBar to show the last keys pressed
        """
        # create timer, repeats every 500ms
        self._lastKeyTimer = QtCore.QTimer()
        self._lastKeyTimer.timeout.connect(self._lastKeyTimerCallback)
        self._lastKeyTimer.setInterval(500)
        self._lastKeyTimer.start()
        self._lastKey = 0
        self._lastKeyTime = 0
        self._lastKeyList = []

        # label for the statusBar, with grey text
        self._lastKeyStatus = Label(textColour='grey')
        self.statusBar().addPermanentWidget(self._lastKeyStatus, 0)

    @property
    def ui(self):
        """The application.ui instance; eg. the gui
        """
        return self.application.ui

    @property
    def project(self) -> Project:
        """The current project"""
        #NB this linkage is set by the model (for now)
        return self._project

    def makeDisabledFileIcon(self, icon):
        return icon

    def _undoChangeCallback(self, message):

        amDirty = self._project._undo.isDirty()
        self.setWindowModified(amDirty)

        if not self.project.isTemporary:
            self.setWindowFilePath(self.application.project.path)
        else:
            self.setWindowFilePath("")

        ## Why do we need to set this icons? Very odd behaviour.
        # if self.project.isTemporary:
        #     self.setWindowIcon(QtGui.QIcon())
        # elif amDirty:
        #     self.setWindowIcon(self.disabledFileIcon)
        # else:
        #     self.setWindowIcon(self.fileIcon)

    @pyqtSlot()
    def _screenChangedEvent(self, *args):
        self._screenChanged(*args)
        self.update()

    def _screenChanged(self, *args):
        getLogger().debug2('mainWindow screenchanged')
        project = self.application.project
        for spectrumDisplay in project.spectrumDisplays:
            for strip in spectrumDisplay.strips:
                strip.refreshDevicePixelRatio()

            # NOTE:ED - set pixelratio for extra axes
            if hasattr(spectrumDisplay, '_rightGLAxis'):
                spectrumDisplay._rightGLAxis.refreshDevicePixelRatio()
            if hasattr(spectrumDisplay, '_bottomGLAxis'):
                spectrumDisplay._bottomGLAxis.refreshDevicePixelRatio()

    @property
    def modules(self):
        """Return tuple of modules currently displayed
        """
        return tuple(self.moduleArea.ccpnModules)

    def _setupNotifiers(self):
        """Setup notifiers connecting gui to current and project
        """
        # Marks
        self.setNotifier(self.application.project, [Notifier.CREATE, Notifier.DELETE, Notifier.CHANGE],
                         'Mark', GuiStrip._updateDisplayedMarks)
        # current notifiers
        self.setNotifier(self.application.current, [Notifier.CURRENT], 'strip', self._highlightCurrentStrip)
        self.setNotifier(self.application.current, [Notifier.CURRENT], 'peaks', GuiStrip._updateSelectedPeaks)
        self.setNotifier(self.application.current, [Notifier.CURRENT], 'integrals', GuiStrip._updateSelectedIntegrals)
        self.setNotifier(self.application.current, [Notifier.CURRENT], 'multiplets', GuiStrip._updateSelectedMultiplets)
        self.setNotifier(self.application.project, [Notifier.CHANGE], 'SpectrumDisplay', self._spectrumDisplayChanged)
        self.setNotifier(self.application.project, [Notifier.CHANGE], 'Strip', self._stripPinnedChanged)

        self.setNotifier(self.application.project, [Notifier.CHANGE], 'Project', self._projectNotifierCallback)

    # def _activatedkeySequence(self, ev):
    #     key = ev.key()
    #     self.statusBar().showMessage('key: %s' % str(key))
    #
    # def _ambiguouskeySequence(self, ev):
    #     key = ev.key()
    #     self.statusBar().showMessage('key: %s' % str(key))

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            if self.windowState() & QtCore.Qt.WindowMinimized:

                self.WindowMaximiseMinimise.emit(False)
                # don't do anything on minimising
                pass

            elif event.oldState() & QtCore.Qt.WindowMinimized:

                self.WindowMaximiseMinimise.emit(True)
                # TODO:ED changeEvent: Normal/Maximised/FullScreen - call populate all modules
                pass

        event.ignore()

    def _initProject(self):
        """
        Puts relevant information from the project into the appropriate places in the main window.
        """
        project = self.application.project
        isNew = project.isNew

        path = project.path
        self.namespace['project'] = project
        self.namespace['runMacro'] = self.pythonConsole._runMacro

        msg = path + (' created' if isNew else ' opened')
        self.statusBar().showMessage(msg)
        msg2 = 'project = %sProject("%s")' % (('new' if isNew else 'open'), path)

        self.application._getRecentProjectFiles()
        self._fillRecentProjectsMenu()
        self.pythonConsole.setProject(project)
        self._updateWindowTitle()
        if self.application.project.isTemporary:
            self.getMenuAction('File->Archive').setEnabled(False)
        else:
            self.getMenuAction('File->Archive').setEnabled(True)

        # sets working path to current path if required
        if (genPrefs := self.application.preferences.general).useProjectPath == 'Alongside':
            genPrefs.userWorkingPath = project.projectPath.parent.asString()
        elif genPrefs.useProjectPath == 'Inside':
            genPrefs.userWorkingPath = project.projectPath.asString()

        # if temporary file set working path to user defined
        if project.isTemporary:
            genPrefs.userWorkingPath = genPrefs.userSetWorkingPath

        from copy import deepcopy

        self._spectrumModuleLayouts = self.moduleLayouts = None

        # get the project layout as soon as mainWindow is initialised
        if self.application.preferences.general.restoreLayoutOnOpening:
            try:
                if _mLayouts := self.application._getUserLayout():
                    self.moduleLayouts = _mLayouts
                    self._spectrumModuleLayouts = deepcopy(self.moduleLayouts)

            except (PermissionError, FileNotFoundError):
                getLogger().debug('Folder may be read-only')

    def _updateWindowTitle(self):
        """
        #CCPN INTERNAL - called in saveProject method of Framework
        """
        applicationName = self.application.applicationName
        version = self.application.applicationVersion

        #GST certainly on osx i would even remove the app name as it should be in the menu
        #GST switched order file name first its the most important info and on osx it
        # appears next to the proxy icon
        if not self.project.isTemporary:
            filename = self.application.project.name
            windowTitle = '{} - {}[{}][*]'.format(filename, applicationName, version)
        else:
            windowTitle = '{}[{}][*]'.format(applicationName, version)

        self.setWindowTitle(windowTitle)

    def getMenuAction(self, menuString, topMenuAction=None):
        from ccpn.framework.Translation import translator

        if topMenuAction is None:
            topMenuAction = self._menuBar
        splitMenuString = menuString.split('->')
        splitMenuString = [translator.translate(text) for text in splitMenuString]
        if len(splitMenuString) > 1:
            topMenuAction = self.getMenuAction('->'.join(splitMenuString[:-1]), topMenuAction)
        for a in topMenuAction.actions():
            # print ('>>>', menuString, a.text())
            if a.text() == splitMenuString[-1]:
                return a.menu() or a
        raise ValueError('Menu item %r not found' % menuString)

    def searchMenuAction(self, menuString, topMenuAction=None):
        from ccpn.framework.Translation import translator

        found = None
        if topMenuAction is None:
            topMenuAction = self._menuBar
        splitMenuString = menuString.split('->')
        splitMenuString = [translator.translate(text) for text in splitMenuString]
        if len(splitMenuString) > 1:
            topMenuAction = self.getMenuAction('->'.join(splitMenuString[:-1]), topMenuAction)
        for a in topMenuAction.actions():
            # print ('>>>', menuString, a.text())
            if a.text() == splitMenuString[-1]:
                found = a.menu() or a
                break
            else:
                if a.menu():
                    found = self.searchMenuAction(menuString, topMenuAction=a.menu())
                    if found:
                        break
        return found

    def _setupWindow(self):
        """
        Sets up SideBar, python console and splitters to divide up main window properly.

        """
        self.namespace = {'application'             : self.application,
                          'current'                 : self.application.current,
                          'preferences'             : self.application.preferences,
                          'redo'                    : self.application.redo,
                          'undo'                    : self.application.undo,
                          'get'                     : self.application.get,
                          'getByPid'                : self.application.get,
                          'getByGid'                : self.application.ui.getByGid,
                          'ui'                      : self.application.ui,
                          'mainWindow'              : self,
                          'project'                 : self.application.project,
                          'loadProject'             : self.application.loadProject,
                          # 'newProject' : self.application.newProject, this is a crash!
                          'info'                    : getLogger().info,
                          'warning'                 : getLogger().warning,
                          'showWarning'             : showWarning,
                          'showInfo'                : showInfo,
                          'showError'               : showError,

                          #### context managers
                          'undoBlock'               : undoBlockWithoutSideBar,
                          'notificationEchoBlocking': notificationEchoBlocking,
                          'plotter'                 : plotter
                          }
        self.pythonConsole = IpythonConsole(self)

        # create the sidebar
        self._sideBarFrame = Frame(self, setLayout=True)  # in this frame is inserted the search widget
        self._sideBarFrame.setContentsMargins(4, 2, 0, 0)

        # create a splitter for the sidebar
        self._sidebarSplitter = Splitter(self._sideBarFrame, horizontal=False)
        self._sidebarSplitter.setContentsMargins(0, 0, 0, 0)
        self._sideBarFrame.getLayout().addWidget(self._sidebarSplitter, 0, 0)  # must be inserted this way

        # create 2 more containers for the search bar and the results
        self.searchWidgetContainer = Frame(self._sideBarFrame, setLayout=True,
                                           grid=(1, 0))  # in this frame is inserted the search widget
        self.searchResultsContainer = Frame(self, setLayout=True)  # in this frame is inserted the search widget
        self.searchResultsContainer.setMinimumHeight(100)

        # create a SideBar pointing to the required containers
        self.sideBar = SideBar(parent=self, mainWindow=self,
                               searchWidgetContainer=self.searchWidgetContainer,
                               searchResultsContainer=self.searchResultsContainer)

        # insert into the splitter
        self._sidebarSplitter.insertWidget(0, self.sideBar)
        self._sidebarSplitter.insertWidget(1, self.searchResultsContainer)
        self._sidebarSplitter.setChildrenCollapsible(False)

        # # GST resizing the splitter by hand causes problems so currently disable it!
        # for i in range(self._sidebarSplitter.count()):
        #     self._sidebarSplitter.handle(i).setEnabled(False)

        # create a splitter to put the sidebar on the left
        self._horizontalSplitter = Splitter(horizontal=True, mouseDoubleClickResize=False)

        self._horizontalSplitter.addWidget(self._sideBarFrame)
        self._horizontalSplitter.addWidget(self.moduleArea)
        self.setCentralWidget(self._horizontalSplitter)

        self._temporaryWidgetStore = Frame(parent=self, showBorder=None, setLayout=False)
        self._temporaryWidgetStore.hide()

        # set the background/fontSize for the tooltips
        # self.setStyleSheet('QToolTip {{ background-color: {TOOLTIP_BACKGROUND}; '
        #                    'color: {TOOLTIP_FOREGROUND}; '
        #                    'font-size: {_size}pt ; }}'.format(_size=self.font().pointSize(), **getColours()))

    def _setupMenus(self):
        """
        Creates menu bar for main window and creates the appropriate menus according to the arguments
        passed at startup.

        This currently pulls info on what menus to create from Framework.  Once GUI and Project are
        separated, Framework should be able to call a method to set the menus.
        """

        self._menuBar = self.menuBar()
        for m in self.application._menuSpec:
            self._createMenu(m)
        self._menuBar.setNativeMenuBar(self.application.preferences.general.useNativeMenus)

        self._fillRecentProjectsMenu()
        self._fillPredefinedLayoutMenu()
        self._fillRecentMacrosMenu()
        #TODO:ED needs fixing
        self._reloadCcpnPlugins()
        # self._fillCcpnPluginsMenu()
        # self._fillUserPluginsMenu()

        self._attachModulesMenuAction()
        self._attachCCPNMacrosMenuAction()
        # self._attachUserMacrosMenuAction()
        self._attachTutorialsMenuAction()

        # hide this option for now
        modulesMenu = self.searchMenuAction(SHOWMODULESMENU)
        modulesMenu.setVisible(False)

    def _attachModulesMenuAction(self):
        # add a connect to call _fillModulesMenu when the menu item is about to show
        # so it is always up-to-date
        modulesMenu = self.searchMenuAction(SHOWMODULESMENU)
        modulesMenu.aboutToShow.connect(self._fillModulesMenu)

    def _attachCCPNMacrosMenuAction(self):
        # add a connect to call _fillCCPNMacrosMenu when the menu item is about to show
        # so it is always up-to-date
        modulesMenu = self.searchMenuAction(CCPNMACROSMENU)
        modulesMenu.aboutToShow.connect(self._fillCCPNMacrosMenu)

    def _attachUserMacrosMenuAction(self):
        # add a connect to call _fillUserMacrosMenu when the menu item is about to show
        # so it is always up-to-date
        modulesMenu = self.searchMenuAction(USERMACROSMENU)
        modulesMenu.aboutToShow.connect(self._fillUserMacrosMenu)

    def _attachTutorialsMenuAction(self):
        # add a connect to call _fillTutorialsMenu when the menu item is about to show
        # so it is always up-to-date
        modulesMenu = self.searchMenuAction(TUTORIALSMENU)
        modulesMenu.aboutToShow.connect(self._fillTutorialsMenu)

    def _createMenu(self, spec, targetMenu=None):
        menu = self._addMenu(spec[0], targetMenu)
        setWidgetFont(menu)
        self._addMenuActions(menu, spec[1])

    def _addMenu(self, menuTitle, targetMenu=None):
        if targetMenu is None:
            targetMenu = self._menuBar
        if isinstance(targetMenu, MenuBar):
            menu = Menu(menuTitle, self)
            targetMenu.addMenu(menu)
        else:
            menu = targetMenu.addMenu(menuTitle)
        return menu

    def _storeShortcut(self, twoLetters, thecallable):
        if twoLetters is not None:
            twoLetters = twoLetters.replace(', ', '')
            twoLetters = twoLetters.lower()
            if twoLetters not in self._shortcutsDict:
                self._shortcutsDict[twoLetters] = thecallable
            else:
                alreadyUsed = self._shortcutsDict.get(twoLetters)
                getLogger().warning(
                        " Ambiguous shortcut overload: %s. \n Assigning to: %s. \nAlready in use for: \n %s." %
                        (twoLetters, thecallable, alreadyUsed))

    def _storeMainMenuShortcuts(self, actions):
        for action in actions:
            if len(action) == 3:
                name, thecallable, shortCutDefs = action
                kwDict = dict(shortCutDefs)
                twoLetters = kwDict.get('shortcut')
                self._storeShortcut(twoLetters, thecallable)

    def _addMenuActions(self, menu, actions):
        self._storeMainMenuShortcuts(actions)
        for action in actions:
            if len(action) == 0:
                menu.addSeparator()
            elif len(action) == 2:
                if callable(action[1]):
                    _action = Action(self, action[0], callback=action[1])
                    menu.addAction(_action)
                else:
                    self._createMenu(action, menu)
            elif len(action) == 3:
                kwDict = dict(action[2])
                for k, v in kwDict.items():
                    if (k == 'shortcut') and v.startswith('⌃'):  # Unicode U+2303, NOT the carrot on your keyboard.
                        kwDict[k] = QKeySequence('Ctrl+{}'.format(v[1:]))
                menuAction = Action(self, action[0], callback=action[1], **kwDict)
                menu.addAction(menuAction)

    def _checkForBadSpectra(self, project):
        """Report bad spectra in a popup
        """
        from ccpn.ui.gui.popups.Dialog import showWarning

        badSpectra = [str(spectrum.pid) for spectrum in project.spectra if not spectrum.hasValidPath()]

        if badSpectra:
            msg = 'Use menu "Spectrum --> Validate paths..." Or "VP" shortcut to correct\n\n'
            details = 'Please inspect file path(s) for:\n'
            for sp in badSpectra:  # these can be >1000 lines message. Added in a scrollable area.
                details += f'{str(sp)}\n'
            basicText = 'Detected invalid Spectrum file paths'
            title = 'Invalid Spectra'
            showWarning(title, basicText, msg, detailedText=details, parent=self,
                        dontShowEnabled=True, defaultResponse=None,
                        popupId=f'{self.__class__.__name__}BadSpectra')

    def _showNefPopup(self, dataLoader):
        """Helper function; it allows the user to select the elements
        and set the dataLoader._nefReader instance accordingly

        :return False in case of 'cancel'
        """
        from ccpn.ui.gui.popups.ImportNefPopup import ImportNefPopup

        dialog = ImportNefPopup(parent=self,
                                mainWindow=self,
                                project=self.project,
                                dataLoader=dataLoader,
                                )
        if dialog.exec_():
            _nefReader = dialog.getActiveNefReader()
            dataLoader.createNewProject = False
            dataLoader._nefReader = _nefReader
            return True

        return False

    def showNefPopup(self, path=None):
        """
        Query for a Nef file if path is None
        Opens the Nef import popup
        If path specified then opens popup to the file otherwise opens load dialog
        """
        from ccpn.ui.gui.widgets.FileDialog import NefFileDialog
        from ccpn.framework.lib.DataLoaders.NefDataLoader import NefDataLoader

        if path is None:
            _filter = '*.nef'
            dialog = NefFileDialog(parent=self.ui.mainWindow, acceptMode='import', fileFilter=_filter)
            dialog._show()
            path = dialog.selectedFile()

        if path is None:
            return

        # try and open with the NefDataloader
        dataLoader = NefDataLoader(path)
        if not dataLoader.isValid:
            txt = f"_getDataLoader: Loading '{path}' unsuccessful; unrecognised type, should be '{NefDataLoader.dataFormat}'"
            getLogger().debug(txt)
            return

        dataLoader.createNewProject = False
        if self._showNefPopup(dataLoader):
            with MessageDialog.progressManager(self, 'Loading Nef file %s ... ' % dataLoader.path):
                dataLoader.load()

    def _clearRecentProjects(self):
        self.application.preferences.recentFiles = []
        self._fillRecentProjectsMenu()

    def _fillRecentProjectsMenu(self):
        """
        Populates recent projects menu with 10 most recently loaded projects
        specified in the preferences file.
        """
        recentFileLocations = self.application._getRecentProjectFiles()
        recentFileMenu = self.getMenuAction('File->Open Recent')
        recentFileMenu.clear()
        for recentFile in recentFileLocations:
            # action = Action(self, text=recentFile, translate=False,
            #                callback=partial(self.application.loadProject, path=recentFile))

            action = Action(self, text=recentFile, translate=False,
                            callback=partial(self.ui.loadProject, path=recentFile))
            recentFileMenu.addAction(action)
        recentFileMenu.addSeparator()
        recentFileMenu.addAction(Action(recentFileMenu, text='Clear',
                                        callback=self._clearRecentProjects))

    def _fillPredefinedLayoutMenu(self):
        """
        Populates predefined Layouts
        """
        from ccpn.ui.gui import Layout
        from ccpn.framework.PathsAndUrls import predefinedLayouts

        userDefinedLayoutDirPath = self.application.preferences.general.get('userLayoutsPath')
        prelayouts = Layout._dictLayoutsNamePath(Layout._getPredefinedLayouts(predefinedLayouts))
        prelayoutMenu = self.getMenuAction('File->Layout->Open pre-defined')
        prelayoutMenu.clear()
        for name, path in prelayouts.items():
            action = Action(self, text=name, translate=False,
                            callback=partial(self.application._restoreLayoutFromFile, path))
            prelayoutMenu.addAction(action)
        prelayoutMenu.addSeparator()
        userLayouts = Layout._dictLayoutsNamePath(Layout._getPredefinedLayouts(userDefinedLayoutDirPath))
        for name, path in userLayouts.items():
            action = Action(self, text=name, translate=False,
                            callback=partial(self.application._restoreLayoutFromFile, path))
            prelayoutMenu.addAction(action)
        prelayoutMenu.addSeparator()
        action = Action(self, text='Update', translate=False,
                        callback=self._fillPredefinedLayoutMenu)
        prelayoutMenu.addAction(action)

    def _fillMacrosMenu(self):
        """
        Populates recent macros menu with last ten macros ran.
        """
        #TODO: make sure that running a macro adds it to the prefs and calls this function

        recentMacrosMenu = self.getMenuAction('Macro->Run Recent')
        recentMacrosMenu.clear()

        from ccpn.framework.PathsAndUrls import macroPath as ccpnMacroPath

        try:
            ccpnMacros = os.listdir(ccpnMacroPath)
            ccpnMacros = [f for f in ccpnMacros if
                          os.path.isfile(os.path.join(ccpnMacroPath, f))]
            ccpnMacros = [f for f in ccpnMacros if f.split('.')[-1] == 'py']
            ccpnMacros = [f for f in ccpnMacros if not f.startswith('.')]
            ccpnMacros = [f for f in ccpnMacros if not f.startswith('_')]
            ccpnMacros = sorted(ccpnMacros)

            recentMacrosMenu.clear()
            for macro in ccpnMacros:
                action = Action(self, text=macro, translate=False,
                                callback=partial(self.runMacro,
                                                 macroFile=os.path.join(ccpnMacroPath, macro)))
                recentMacrosMenu.addAction(action)
            if len(ccpnMacros) > 0:
                recentMacrosMenu.addSeparator()
        except FileNotFoundError:
            pass

    def _clearRecentMacros(self):
        self.application.preferences.recentMacros = []
        self._fillRecentMacrosMenu()

    def _fillRecentMacrosMenu(self):
        """
        Populates recent macros menu with last ten macros ran.
        TODO: make sure that running a macro adds it to the prefs and calls this function
        """
        recentMacrosMenu = self.getMenuAction('Macro->Run Recent')
        recentMacros = self.application.preferences.recentMacros
        if len(recentMacros) < 0:
            self._fillMacrosMenu()  #uses the default Macros

        else:
            recentMacros = recentMacros[-10:]
            recentMacrosMenu.clear()
            for recentMacro in sorted(recentMacros, reverse=True):
                action = Action(self, text=recentMacro, translate=False,
                                callback=partial(self.application.runMacro, macroFile=recentMacro))
                recentMacrosMenu.addAction(action)
            recentMacrosMenu.addSeparator()

        recentMacrosMenu.addAction(Action(recentMacrosMenu, text='Refresh',
                                          callback=self._fillRecentMacrosMenu))
        recentMacrosMenu.addAction(Action(recentMacrosMenu, text='Browse...',
                                          callback=self.application.runMacro))
        recentMacrosMenu.addAction(Action(recentMacrosMenu, text='Clear',
                                          callback=self._clearRecentMacros))

    def _addPluginSubMenu(self, MENU, Plugin):
        targetMenu = pluginsMenu = self.searchMenuAction(MENU)
        if '...' in Plugin.PLUGINNAME:
            package, name = Plugin.PLUGINNAME.split('...')
            try:
                targetMenu = self.getMenuAction(package, topMenuAction=pluginsMenu)
            except ValueError:
                targetMenu = self._addMenu(package, targetMenu=pluginsMenu)
        else:
            name = Plugin.PLUGINNAME
        action = Action(self, text=name, translate=False,
                        callback=partial(self.startPlugin, Plugin=Plugin))
        targetMenu.addAction(action)

    def _fillModulesMenu(self):
        modulesMenu = self.searchMenuAction(SHOWMODULESMENU)
        modulesMenu.clear()

        moduleSize = self.sideBar.size()
        visible = moduleSize.width() != 0 and moduleSize.height() != 0 and self.sideBar.isVisible()
        modulesMenu.addAction(Action(modulesMenu, text='Sidebar',
                                     checkable=True, checked=visible,
                                     # callback=partial(self._showSideBarModule, self._sideBarFrame, self, visible)))
                                     callback=partial(self._showSideBarModule, self._sideBarFrame, self, visible)))

        for module in self.moduleArea.ccpnModules:
            visible = module.isVisible()
            modulesMenu.addAction(Action(modulesMenu, text=module.name(),
                                         checkable=True, checked=visible,
                                         callback=partial(self._showModule, module)))

    def _showModule(self, module):
        try:
            menuItem = self.searchMenuAction(module.name())
            if menuItem:
                module.setVisible(not module.isVisible())

        except Exception as es:
            getLogger().warning('Error expanding module: %s', module.name())

    def _fillCCPNMacrosMenu(self):
        modulesMenu = self.searchMenuAction(CCPNMACROSMENU)
        modulesMenu.clear()

        from ccpn.framework.PathsAndUrls import macroPath
        from os import walk

        # read the macros file directory - all levels, but sectioned by sub-folder
        startpath = None
        for (dirpath, dirnames, filenames) in walk(os.path.expanduser(macroPath)):
            startpath = startpath or dirpath

            macroFiles = []
            for filename in filenames:
                if filename.startswith('_'):
                    continue
                elif filename.startswith('_'):
                    continue
                if filename.endswith('.py'):
                    _macroName = os.path.join(dirpath, filename)
                    macroFiles.append(_macroName)

            thispath = dirpath[len(startpath):]
            if any(thispath.startswith(nn) for nn in ['/old', '/ideas']):
                continue
            # remove underscores
            if macroFiles:
                if thispath:
                    dirname = modulesMenu.addAction(f'---  {thispath}  ---')
                    dirname.setEnabled(False)

                for file in sorted(macroFiles):
                    filename, fileExt = os.path.splitext(file)

                    modulesMenu.addAction(Action(modulesMenu, text=os.path.basename(filename),
                                                 callback=partial(self._runCCPNMacro, file, self)))

    def _fillUserMacrosMenu(self):
        modulesMenu = self.searchMenuAction(USERMACROSMENU)
        modulesMenu.clear()

        macroPath = self.application.preferences.general.userMacroPath
        from os import walk

        # read the macros file directory - only top level
        macroFiles = []
        for (dirpath, dirnames, filenames) in walk(os.path.expanduser(macroPath)):
            macroFiles.extend([os.path.join(dirpath, filename) for filename in filenames])
            break

        for file in macroFiles:
            filename, fileExt = os.path.splitext(file)

            if fileExt == '.py':
                modulesMenu.addAction(Action(modulesMenu, text=os.path.basename(filename),
                                             callback=partial(self._runUserMacro, file, self)))

    def _runCCPNMacro(self, filename, modulesMenu):
        """Run a CCPN macro from the populated menu
        """
        try:
            self.application.runMacro(filename)

        except Exception as es:
            getLogger().warning('Error running CCPN Macro: %s' % str(filename))

    def _runUserMacro(self, filename, modulesMenu):
        """Run a User macro from the populated menu
        """
        try:
            self.application.runMacro(filename)

        except Exception as es:
            getLogger().warning('Error running User Macro: %s' % str(filename))

    def _fillTutorialsMenu(self):
        modulesMenu = self.searchMenuAction(TUTORIALSMENU)
        modulesMenu.clear()
        import ccpn.framework.PathsAndUrls as pa
        from ccpn.util.Path import aPath

        importantList = (('Beginners Tutorial', pa.beginnersTutorialPath),
                         ('Backbone Assignment Tutorial', pa.backboneAssignmentTutorialPath),
                         ('Chemical Shift Perturbation Tutorial', pa.cspTutorialPath),
                         ('Solid State Peptide Tutorial', pa.solidStatePeptideTutorialPath),
                         ('Solid State SH3 Tutorial', pa.solidStateSH3TutorialPath),
                         ('Solid State HETs Tutorial', pa.solidStateHETsTutorialPath),
                         ('Macro Writing Tutorial', pa.macroWritingTutorialPath),
                         ('Screen Tutorial', pa.screeningTutorialPath))

        # add link to website videos
        modulesMenu.addAction(Action(modulesMenu, text='Video Tutorials && Manual', callback=self._showCCPNTutorials))
        modulesMenu.addAction(Action(modulesMenu, text='Tutorial Data', callback=self._showTutorialData))
        modulesMenu.addSeparator()

        # add the main tutorials
        for text, file in importantList:
            filePath = aPath(file)
            if filePath.exists() and filePath.suffix == '.pdf':
                modulesMenu.addAction(Action(modulesMenu, text=text, callback=partial(self._showTutorial, file, self)))
        modulesMenu.addSeparator()

        # add the remaining tutorials from the tutorials top directory
        tutorialsFiles = aPath(pa.tutorialsPath).listDirFiles('pdf')
        for filePath in sorted(tutorialsFiles, key=lambda ff: ff.basename):
            if filePath not in [ff[1] for ff in importantList]:
                _label = camelCaseToString(filePath.basename)
                _label = _label.replace('Chem Build', 'ChemBuild')
                modulesMenu.addAction(Action(modulesMenu, text=_label,
                                             callback=partial(self._showTutorial, filePath, self)))
        modulesMenu.addSeparator()

        # add the How-Tos submenu
        howtosMenu = self._addMenu(HOWTOSMENU, modulesMenu)
        howtosFiles = aPath(pa.howTosPath).listDirFiles('pdf')
        for filePath in sorted(howtosFiles, key=lambda ff: ff.basename):
            _label = camelCaseToString(filePath.basename)
            howtosMenu.addAction(Action(howtosMenu, text=_label, callback=partial(self._showTutorial, filePath, self)))

    def _showCCPNTutorials(self):
        from ccpn.framework.PathsAndUrls import ccpnVideos

        # import webbrowser

        # webbrowser.open(ccpnVideos)
        self.application._showHtmlFile('Video Tutorials', ccpnVideos)

    def _showTutorial(self, filename, modulesMenu):
        """Run a CCPN macro from the populated menu
        """
        try:
            self.application._systemOpen(filename)

        except Exception as es:
            getLogger().warning('Error opening tutorial: %s' % str(filename))

    def _showTutorialData(self):
        from ccpn.framework.PathsAndUrls import ccpnTutorials

        self.application._showHtmlFile("Tutorial Data", ccpnTutorials)

    def _showSideBarModule(self, module, modulesMenu, visible):
        try:
            # if module.size().height() != 0 and module.size().width() != 0:  #menuItem.isChecked():    # opposite as it has toggled

            if visible:
                module.hide()
            else:
                module.show()
        except Exception as es:
            getLogger().warning('Error expanding module: sideBar')

    def keyReleaseEvent(self, event: QtGui.QKeyEvent) -> None:
        # this MUST be a keyRelease event (isAutoRepeat MUST be false for keysequence-actions)
        key = event.key()
        if key == QtCore.Qt.Key_Escape:
            # Reset Mouse Mode
            mode = getCurrentMouseMode()
            if mode != SELECT:
                self._setMouseMode(SELECT)

        self._addKeyToStatusBar(key)

        return super().keyReleaseEvent(event)

    def _addKeyToStatusBar(self, key):

        # remember the last key that was pressed for reset keySequence timer below
        self._lastKeyTime = time.perf_counter()
        self._lastKey = key
        try:
            if key in [QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab]:
                self._lastKeyList.append('Tab')
            elif chr(key).isascii():
                if chr(key) == ' ':
                    self._lastKeyList.append('Space')
                else:
                    self._lastKeyList.append(chr(key))
            if len(self._lastKeyList) > 2:
                self._lastKeyList.pop(0)
        except Exception:
            self._lastKeyList = []

        self._lastKeyStatus.setText(''.join(self._lastKeyList))

    def _setStatusBarKeys(self, keys: str):
        """Set the statusBar and update the timer
        """
        if isinstance(keys, str):
            msg = ''.join(self._lastKeyList)
            if msg.endswith(keys) or (keys == '  ' and msg.endswith('SpaceSpace')):
                self._lastKeyList = []
        self._lastKey = 0
        self._lastKeyTime = time.perf_counter()
        self._lastKeyStatus.setText(keys)

    def _lastKeyTimerCallback(self):
        """QTimer event that fires every 500ms
        """
        deltaT = time.perf_counter() - self._lastKeyTime
        if deltaT > KEY_DELAY and self._lastKey not in [QtCore.Qt.Key_Escape, 0]:
            self._lastKey = 0
            # simulate an exit-key to clear keySequences - MUST be KeyPress
            event = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Exit, QtCore.Qt.NoModifier)
            QtCore.QCoreApplication.sendEvent(self, event)
            # clear the statusBar
            self._lastKeyList = []
            self._lastKeyStatus.setText('')

    def _fillCcpnPluginsMenu(self):

        from ccpn.plugins import loadedPlugins

        pluginsMenu = self.searchMenuAction(CCPNPLUGINSMENU)
        pluginsMenu.clear()
        for Plugin in loadedPlugins:
            self._addPluginSubMenu(CCPNPLUGINSMENU, Plugin)
        pluginsMenu.addSeparator()
        pluginsMenu.addAction(Action(pluginsMenu, text='Reload',
                                     callback=self._reloadCcpnPlugins))

    def _reloadCcpnPlugins(self):
        from ccpn import plugins
        from importlib import reload
        from ccpn.util.Path import aPath

        reload(plugins)

        pluginUserPath = self.application.preferences.general.userPluginPath
        import importlib.util

        filePaths = [(aPath(r) / file) for r, d, f in os.walk(aPath(pluginUserPath)) for file in f if
                     os.path.splitext(file)[1] == '.py']

        for filePath in filePaths:
            # iterate and load the .py files in the plugins directory
            spec = importlib.util.spec_from_file_location(".", filePath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        self._fillCcpnPluginsMenu()
        self._fillUserPluginsMenu()

    def _fillUserPluginsMenu(self):

        from ccpn.plugins import loadedUserPlugins

        pluginsMenu = self.searchMenuAction(PLUGINSMENU)
        pluginsMenu.clear()
        for Plugin in loadedUserPlugins:
            self._addPluginSubMenu(PLUGINSMENU, Plugin)
        pluginsMenu.addSeparator()
        pluginsMenu.addAction(Action(pluginsMenu, text='Reload',
                                     callback=self._reloadUserPlugins))

    def _reloadUserPlugins(self):
        self._reloadCcpnPlugins()

    def startPlugin(self, Plugin):
        plugin = Plugin(application=self.application)
        self.application._plugins.append(plugin)
        if plugin.guiModule is None:
            if not plugin.UiPlugin:
                plugin.run()
                return
            else:
                from ccpn.ui.gui.modules.PluginModule import AutoGeneratedPluginModule

                pluginModule = AutoGeneratedPluginModule(mainWindow=self,
                                                         plugin=plugin,
                                                         application=self.application)  # ejb

        else:
            pluginModule = plugin.guiModule(name=plugin.PLUGINNAME, parent=self,
                                            plugin=plugin, application=self.application,
                                            mainWindow=self)
        plugin.ui = pluginModule
        if not pluginModule.aborted:
            self.application.ui.pluginModules.append(pluginModule)
            self.moduleArea.addModule(pluginModule)
        # TODO: open as pop-out, not as part of MainWindow
        # self.moduleArea.moveModule(pluginModule, position='above', neighbor=None)

    def _updateRestoreArchiveMenu(self):

        action = self.getMenuAction('File->Restore From Archive...')
        action.setEnabled(bool(self._project._getArchivePaths()))

    def undo(self):
        self._project._undo.undo()

    def redo(self):
        self._project._undo.redo()

    def saveLogFile(self):
        pass

    def clearLogFile(self):
        pass

    def _closeMainWindowModules(self):
        """Close modules in main window;
        CCPNINTERNAL: also called from Framework
        """
        for module in self.moduleArea.ccpnModules:
            getLogger().debug('Closing module: %s' % module)
            try:
                module.setVisible(False)  # GWV not sure why, but this was the effect of prior code
                module.close()
            except Exception as es:
                # wrapped C/C++ object of type StripDisplay1d has been deleted
                getLogger().debug(f'_closeMainWindowModules: {es}')

    def _closeExtraWindowModules(self):
        """Close modules in any extra window;
        CCPNINTERNAL: also called from Framework
        """
        for module in self.moduleArea.tempAreas:
            getLogger().debug('Closing module: %s' % module)
            try:
                module.setVisible(False)  # GWV not sure why, but this was the effect of prior code
                module.close()
            except Exception as es:
                # wrapped C/C++ object of type StripDisplay1d has been deleted
                getLogger().debug(f'_closeExtraWindowModules: {es}')

    def _stopPythonConsole(self):
        if self.pythonConsoleModule:
            self.pythonConsoleModule.pythonConsoleWidget._stopChannels()

    def _closeWindowFromUpdate(self, event=None, disableCancel=True):
        # set the active window to mainWindow so that the quit popup centres correctly.
        self._closeWindow(event=event, disableCancel=disableCancel)
        os._exit(0)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """handle close event from the X button
        """
        event.ignore()
        # pass control to _closeEvent - this cleans up the focus between windows/popups
        QtCore.QTimer.singleShot(0, self._closeWindow)

    def _closeEvent(self, event=None, disableCancel=False):
        """Handle close event from other methods
        """
        self._closeWindow(event=event, disableCancel=disableCancel)

    def _closeWindow(self, event=None, disableCancel=False):
        """
        Saves application preferences. Displays message box asking user to save project or not.
        Closes Application.
        """

        undos = self.application.project._undo

        # set the active window to mainWindow so that the quit popup centres correctly.
        QtWidgets.QApplication.setActiveWindow(self)

        QUIT = 'Quit Program'
        SAVE_QUIT = 'Save and Quit'
        SAVE = 'Save'
        MESSAGE = QUIT
        CANCEL = 'Cancel'
        QUIT_WITHOUT_SAVING = 'Quit without saving'
        DONT_SAVE = "Don't Save"
        SAVE_DATA = 'Save changes'
        DETAIL = "Do you want to save changes before quitting?"
        # add to preferences SAVE_DATA .
        if disableCancel:
            if undos.isDirty():
                # reply = MessageDialog.showMulti(MESSAGE, DETAIL, [QUIT], checkbox=SAVE_DATA, okText=QUIT,
                #                                 checked=True)
                reply = MessageDialog.showMulti(MESSAGE, DETAIL, [SAVE, DONT_SAVE], parent=self, okText=SAVE)
            else:
                # reply = QUIT_WITHOUT_SAVING
                reply = DONT_SAVE

        else:
            if undos.isDirty():
                # reply = MessageDialog.showMulti(MESSAGE, DETAIL, [QUIT, CANCEL], checkbox=SAVE_DATA, okText=QUIT,
                #                                 checked=True)
                reply = MessageDialog.showMulti(MESSAGE, DETAIL, texts=[SAVE, DONT_SAVE, CANCEL], parent=self,
                                                okText=SAVE)
            else:
                # reply = QUIT_WITHOUT_SAVING
                reply = DONT_SAVE

        # if (QUIT in reply) and (SAVE_DATA in reply or SAVE_QUIT in reply):
        if (reply in [SAVE_QUIT, SAVE_DATA, SAVE]):
            if event:
                event.accept()

            self.application._savePreferences()
            success = self.application.saveProject()
            if success is True:
                # Close and clean up project
                self.deleteAllNotifiers()
                self.application._closeProject()  # close if saved
                QtWidgets.QApplication.quit()
                os._exit(0)  # HARSH! actually crash issue only seems to affect newTestApplication :|

            else:
                if event:  # ejb - don't close the project
                    event.ignore()

        # elif (QUIT in reply and SAVE_DATA not in reply) or (reply == QUIT_WITHOUT_SAVING):
        elif (reply in [QUIT, QUIT_WITHOUT_SAVING, DONT_SAVE]):
            if event:
                event.accept()

            self.application._savePreferences()
            self.deleteAllNotifiers()
            self.application._closeProject()
            QtWidgets.QApplication.quit()
            os._exit(0)  # HARSH! actually crash issue only seems to affect newTestApplication :|

        else:
            if event:
                event.ignore()

    def newMacroFromLog(self):
        """
        Displays macro editor with contents of the log.
        """
        editor = MacroEditor(self.moduleArea, self, "Macro Editor")
        with open(self.project._logger.logPath, 'r') as fp:
            l = fp.readlines()
        text = ''.join([line.strip().split(':', 6)[-1] + '\n' for line in l])
        editor.textBox.setText(text)

    def _highlightCurrentStrip(self, data: Notifier):
        """Callback on current to highlight the strip
        """
        previousStrip = data[Notifier.PREVIOUSVALUE]
        currentStrip = data[Notifier.VALUE]

        if previousStrip == currentStrip:
            return

        if previousStrip and not previousStrip.isDeleted:
            previousStrip._highlightStrip(False)
            previousStrip.spectrumDisplay._highlightAxes(previousStrip, False)
            if previousStrip != currentStrip:
                self._previousStrip = previousStrip
        else:
            self._previousStrip = None

        if currentStrip and not currentStrip.isDeleted:
            currentStrip._highlightStrip(True)
            currentStrip._attachZPlaneWidgets()
            currentStrip.spectrumDisplay._highlightAxes(currentStrip, True)

    def _spectrumDisplayChanged(self, data):
        """Callback on spectrumDisplay change
        """
        trigger = data[Notifier.TRIGGER]
        spectrumDisplay = data[Notifier.OBJECT]

        if trigger == Notifier.CHANGE:
            getLogger().debug(f'>>> SpectrumDisplay changed - {spectrumDisplay}')
            for strip in self.strips:
                strip._updatePlaneAxes()
            # spectrumDisplay._setPlaneAxisWidgets()

    def _stripPinnedChanged(self, data):
        """Callback on strip pinned state change
        """
        trigger = data[Notifier.TRIGGER]
        strip = data[Notifier.OBJECT]

        if trigger == Notifier.CHANGE and data[Notifier.SPECIFIERS].get('pinnedChanged'):
            getLogger().debug(f'>>> Strip changed - {strip} {strip.pinned}')
            strip._updateStripLabelState()

            # disable the other pinned strips - only allow one strip to be pinned
            # if strip.pinned:
            #     for st in self.project.strips:
            #         if st != strip:
            #             st.pinned = False

    def printToFile(self):
        self.application.showPrintSpectrumDisplayPopup()

    def _mousePositionMoved(self, strip: GuiStrip.GuiStrip, position: QtCore.QPointF):
        """ CCPN INTERNAL: called from ViewBox
        This is called when the mouse cursor position has changed in some strip
        :param strip: The strip the mouse cursor is hovering over
        :param position: The cursor position in "natural" (e.g. ppm) units
        :return: None
        """
        assert 0 == 1

    def _scanDataLoaders(self, dataLoaders, func: callable = lambda _: True, result=None, depth=0) -> list:
        """Replace the list comprehension below to allow nested tree of dataLoaders.
        Assumes that recursive==True in the DirectoryDataLoader __init__
        """
        if result is None:
            result = []
        for loader in dataLoaders:
            url, _, createNew, ignore = loader.path, loader, loader.createNewProject, loader.ignore
            if ignore:
                continue
            if getattr(loader, 'dataLoaders', None) is not None and getattr(loader, 'recursive', None) is True:
                self._scanDataLoaders(loader.dataLoaders, result=result, func=func, depth=depth + 1)
            elif loader and func(loader):
                result.append((url, loader, createNew))
        return result

    def _getStats(self, dataLoaders: list) -> tuple[int, int]:
        """Get the maximum  count/depth of items in the dataLoader-tree to
        check before loading.
        """
        maxCount, maxDepth = 0, 0
        for loader in dataLoaders:
            if isinstance(loader, DirectoryDataLoader):
                mc, md = self._getStats(loader.dataLoaders)
                maxCount = max(mc, loader.count)
                maxDepth = max(md, loader.depth)
        return maxCount, maxDepth

    def _processDroppedItems(self, data) -> list:
        """Handle the dropped urls
        :return list of loaded objects
        """
        # CCPNINTERNAL. Called also from module area and GuiStrip. They should have same behaviour
        # use an undoBlockWithoutSideBar, and ignore logging if MAXITEMLOGGING or more items
        # to stop overloading of the log

        from ccpn.framework.lib.DataLoaders.DataLoaderABC import _getPotentialDataLoaders

        urls = [str(url) for url in data.get(DropBase.URLS, []) if len(url) > 0]
        if urls is None:
            return []

        # dataLoaders: A list of (url, dataLoader, createsNewProject, ignore) tuples.
        # createsNewProject: to evaluate later call _loadProject; e.g. for NEF
        # ignore: user opted to skip this one; e.g. a spectrum already present
        dataLoaders = []
        _loaders = []
        # analyse the Urls
        for url in urls:
            # try finding a data loader, catch any errors for recognised but
            # incomplete/invalid url's (i.e. incomplete spectral data)
            try:
                dataLoader, createsNewProject, ignore = self.ui._getDataLoader(url)
                dataLoaders.append((url, dataLoader, createsNewProject, ignore))
                # NOTE:ED - hack to get recursive dataLoaders to check valid new-projects first
                _loaders.append(dataLoader)

            except (RuntimeError, ValueError) as es:
                MessageDialog.showError(f'Loading "{url}"',
                                        f'{es}',
                                        parent=self)
        if not self._scanDataLoaders(_loaders):
            # return if everything is empty
            return []
        getLogger().info('Handling urls ...')

        # All ignored urls
        urlsToIgnore = self._scanDataLoaders(_loaders, func=lambda dl: dl.ignore)
        # All valid urls
        allUrlsToLoad = self._scanDataLoaders(_loaders, func=lambda dl: not dl.ignore)
        # Error urls
        errorUrls = self._scanDataLoaders(_loaders, func=lambda dl: dl is None)
        # Project urls
        newProjectUrls = self._scanDataLoaders(_loaders, func=lambda dl: (dl is not None and
                                                                          dl.createNewProject))
        # Data urls
        dataUrls = self._scanDataLoaders(_loaders, func=lambda dl: (dl is not None and not
        dl.createNewProject))

        # Check for the different (potential) errors
        if len(urlsToIgnore) == len(dataLoaders):
            # ignore all; just return
            return []

        if len(allUrlsToLoad) == 1:
            # We only dropped one item
            if len(errorUrls) == 1:
                url = errorUrls[0][0]
                MessageDialog.showError('Load Data', f'Dropped item {url!r} failed to load\n'
                                                     f'Check console/log for details', parent=self)
                return []
        else:
            # We dropped multiple items
            if len(errorUrls) == len(allUrlsToLoad):
                # We only found errors; nothing to load
                MessageDialog.showError('Load Data', 'No dropped items were recognised\n'
                                                     'Check console/log for details', parent=self)
                return []

            elif len(errorUrls) >= 1:
                # We found 1 or more errors
                MessageDialog.showError('Load Data', f'{len(errorUrls):d} dropped items were not recognised\n'
                                                     f'Check console/log for details', parent=self)
                return []

        if len(newProjectUrls) > 1:
            # We found more than one dataLoader that would create a new project; not allowed
            MessageDialog.showError('Load Data',
                                    f'Only one new project can be created at a time;\n'
                                    f'this action will try to create {len(newProjectUrls):d} new projects',
                                    parent=self)
            return []

        if len(newProjectUrls) + len(dataUrls) == 0:
            MessageDialog.showError('Load Data', 'No dropped items can be loaded', parent=self)
            return []

        _dLoaders = [dl for url, dl, createNew in allUrlsToLoad]
        try:
            result = self.application._loadData(_dLoaders)
            return result

        except (RuntimeError, ValueError) as es:
            MessageDialog.showError('Error loading data', f'{es}', parent=self)
            return []

    def _processPids(self, data, position=None, relativeTo=None):
        """Handle the urls passed to the drop event
        """
        # CCPNINTERNAL. Called also from CcpnModule and CcpnModuleArea. They should have same behaviour

        pids = data[DropBase.PIDS]
        if pids and len(pids) > 0:
            getLogger().debug('>>> dropped pids...')

            objs = [self.project.getByPid(pid) for pid in pids]

            # check whether a new spectrumDisplay is needed, check axisOrdering
            # add show popup for ordering if required
            from ccpn.ui.gui.popups.AxisOrderingPopup import checkSpectraToOpen

            checkSpectraToOpen(self, objs)
            _openItemObject(self, objs, position=position, relativeTo=relativeTo)

    #-----------------------------------------------------------------------------------------
    # Code moved from previously lib.GuiWindow
    #-----------------------------------------------------------------------------------------

    @logCommand('mainWindow.')
    def deassignPeaks(self):
        """Deassign all from selected peaks
        """
        if self.current.peaks:
            with undoBlockWithoutSideBar():
                for peak in self.current.peaks:
                    assignedDims = list(peak.dimensionNmrAtoms)
                    assignedDims = tuple([] for dd in assignedDims)
                    peak.dimensionNmrAtoms = assignedDims

    def deleteSelectedItems(self, parent=None):
        """Delete peaks/integrals/multiplets from the project
        """
        # show simple delete items popup
        from ccpn.ui.gui.popups.DeleteItems import DeleteItemsPopup

        foundSets = 0
        if self.current.peaks or self.current.multiplets or self.current.integrals:
            deleteItems = []
            if self.current.peaks:
                deleteItems.append(('Peaks', self.current.peaks, True))
                foundSets += _PEAKS
            if self.current.integrals:
                deleteItems.append(('Integrals', self.current.integrals, True))
                foundSets += _INTEGRALS
            if self.current.multiplets:
                deleteItems.append(('Multiplets', self.current.multiplets, True))
                foundSets += _MULTIPLETS

            # add integrals attached peaks
            attachedIntegrals = set()
            for peak in self.current.peaks:
                if peak.integral:
                    attachedIntegrals.add(peak.integral)
            attachedIntegrals = list(attachedIntegrals - set(self.current.integrals))

            if attachedIntegrals:
                deleteItems.append(('Additional Peak-Integrals', attachedIntegrals, False))
                foundSets += _INTEGRAL_PEAKS

            # add peaks attached multiplets
            attachedPeaks = set()
            for multiplet in self.current.multiplets:
                for peak in multiplet.peaks:
                    attachedPeaks.add(peak)
            attachedPeaks = list(attachedPeaks - set(self.current.peaks))

            if attachedPeaks:
                deleteItems.append(('Additional Multiplet-Peaks', attachedPeaks, False))
                foundSets += _MULTIPLET_PEAKS

            ## Please always show the popup! Because we could have selected current objects that are not obviously displayed as selected in tables/or displays and
            ## could delete objects without being aware of this operation.
            ## This shortcut should be removed from here, and enabled only on displays/tables as a localised shortcut
            popup = DeleteItemsPopup(parent=self, mainWindow=self, items=deleteItems)
            popup.exec()

    @logCommand('mainWindow.')
    def propagateAssignments(self):
        from ccpn.core.lib.AssignmentLib import propagateAssignments

        # need another way to select this :| get from preferences?
        tol = {}
        peaks = self.application.current.peaks
        if not peaks:
            return
        # specify one of the tolerances to enable tolerance-checking
        propagateAssignments(peaks=peaks, tolerancesByIsotope=tol)

    @logCommand('mainWindow.')
    def copyAssignments(self):
        from ccpn.core.lib.AssignmentLib import copyAssignments

        peaks = self.application.current.peaks
        if not peaks:
            return
        copyAssignments(peaks=peaks)

    @logCommand('mainWindow.')
    def propagateAssignmentsFromReference(self):
        from ccpn.core.lib.AssignmentLib import propagateAssignmentsFromReference

        # need another way to select this :| get from preferences?
        tol = {}
        cStrip = self.application.current.strip
        peak = ((cStrip and cStrip._lastClickedObjects and cStrip._lastClickedObjects[0]) or
                self.application.current.peak)
        if not peak:
            return
        # specify one of the tolerances to enable tolerance-checking
        propagateAssignmentsFromReference(None, referencePeak=peak,
                                          tolerancesByIsotope=tol)

    @logCommand('mainWindow.')
    def copyAssignmentsFromReference(self):
        from ccpn.core.lib.AssignmentLib import copyAssignmentsFromReference

        cStrip = self.application.current.strip
        peak = ((cStrip and cStrip._lastClickedObjects and cStrip._lastClickedObjects[0]) or
                self.application.current.peak)
        if not peak:
            return
        copyAssignmentsFromReference(None, referencePeak=peak)

    def _openCopySelectedPeaks(self):
        from ccpn.ui.gui.popups.CopyPeaksPopup import CopyPeaks

        popup = CopyPeaks(parent=self, mainWindow=self)
        peaks = self.current.peaks
        popup._selectPeaks(peaks)
        popup.exec_()

    def setPeakAliasing(self):
        """Set the aliasing for the currently selected peaks
        """
        if self.current.peaks:
            from ccpn.ui.gui.popups.SetPeakAliasing import SetPeakAliasingPopup

            popup = SetPeakAliasingPopup(parent=self, mainWindow=self, peaks=self.current.peaks)
            popup.exec_()

    def centreOnSelectedPeak(self):
        """Centre the current strip on the first selected peak
        """
        if self.current.peaks and self.current.strip:
            from ccpn.ui.gui.lib.SpectrumDisplayLib import navigateToCurrentPeakPosition

            navigateToCurrentPeakPosition(self.application, selectClickedPeak=True, allStrips=False)

    def calibrateFromPeaks(self):
        """Calibrate the current strip from the selected peaks
        """
        if self.current.strip:
            self.current.strip.calibrateFromPeaks()

    def getCurrentPositionAndStrip(self):
        current = self.application.current
        # """
        # # this function is called as a shortcut macro ("w1") but
        # # with the code commented out that is pretty pointless.
        # # current.strip and current.cursorPosition are now set by
        # # clicking on a position in the strip so this commented
        # # out code is no longer useful, and this function might
        # # be more generally useful, so leave the brief version
        # current.strip = current.viewBox.parentObject().parent
        # cursorPosition = (current.viewBox.position.x(),
        #                   current.viewBox.position.y())
        # # if len(current.strip.axisOrder) > 2:
        # #   for axis in current.strip.orderedAxes[2:]:
        # #     position.append(axis.position)
        # # current.position = tuple(position)
        # current.cursorPosition = cursorPosition
        # """
        return current.strip, current.cursorPosition

    def _getPeaksParams(self, peaks):
        params = []
        for peak in peaks:
            params.append((peak.height, peak.position, peak.lineWidths))
        return params

    def _setPeaksParams(self, peaks, params):
        for n, peak in enumerate(peaks):
            height, position, lineWidths = params[n]
            peak.height = height
            peak.position = position
            peak.lineWidths = lineWidths

    def add1DIntegral(self, peak=None):
        """Peak: take self.application.currentPeak as default
        """

        from ccpn.core.lib.ContextManagers import undoBlock, notificationEchoBlocking, undoBlockWithoutSideBar

        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                strip = self.application.current.strip
                peak = self.project.getByPid(peak) if isinstance(peak, str) else peak

                if strip is not None:
                    if strip.spectrumDisplay.is1D:
                        cursorPosition = self.application.current.cursorPosition
                        if cursorPosition is not None and len(cursorPosition) > 1:
                            pos = cursorPosition[strip.spectrumDisplay._flipped]
                            limits = [pos, pos + 0.01]

                            validViews = [sv for sv in strip.spectrumViews if sv.isDisplayed]
                            currentIntegrals = list(self.current.integrals)
                            for spectrumView in validViews:

                                if not spectrumView.spectrum.integralLists:
                                    spectrumView.spectrum.newIntegralList()

                                # stupid bug! mixing views and lists
                                validIntegralLists = [ilv.integralList for ilv in spectrumView.integralListViews if
                                                      ilv.isDisplayed]

                                for integralList in validIntegralLists:

                                    # set the limits of the integral with a default baseline of 0.0
                                    integral = integralList.newIntegral(value=None, limits=[limits, ])
                                    integral.baseline = 0.0
                                    currentIntegrals.append(integral)
                                    if peak:
                                        integral.peak = peak
                                    else:
                                        if len(self.application.current.peaks) == 1:
                                            if self.application.current.peak.peakList.spectrum == integral.integralList.spectrum:
                                                integral.peak = self.application.current.peak
                            self.current.integrals = currentIntegrals

                else:
                    getLogger().warning('Current strip is not 1D')

    @logCommand('mainWindow.')
    def refitCurrentPeaks(self, singularMode=False):
        from ccpn.core.lib import AssignmentLib

        peaks = self.application.current.peaks
        if not peaks:
            return

        fitMethod = self.application.preferences.general.peakFittingMethod
        with undoBlockWithoutSideBar():
            AssignmentLib.refitPeaks(peaks, fitMethod=fitMethod, singularMode=singularMode)

    def recalculateCurrentPeakHeights(self):
        """
        Recalculates the peak height without changing the ppm position
        """
        from ccpn.core.lib.peakUtils import estimateVolumes, updateHeight

        getLogger().info('Recalculating peak height(s).')

        current = self.application.current
        peaks = current.peaks

        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                list(map(lambda x: updateHeight(x), peaks))

        getLogger().info('Recalculating peak height(s) completed.')

    def estimateVolumes(self):
        """Estimate volumes of peaks selected by right-mouse menu
        If clicking on a selected peak then apply to all selected, otherwise apply to clicked peaks
        """
        from ccpn.core.lib.peakUtils import estimateVolumes, updateHeight

        current = self.application.current
        peaks = current.peaks
        clickedPeaks = current.strip._lastClickedObjects if current.strip else None

        # return if both the lists are empty
        if not (peaks or clickedPeaks):
            return

        with undoBlockWithoutSideBar():
            if (set(peaks or []) & set(clickedPeaks or [])):
                # if any of clickedPeaks are in current.peaks then apply to all selected
                estimateVolumes(peaks)
            else:
                estimateVolumes(clickedPeaks)

        # project = peaks[0].project
        # undo = project._undo
        #
        # project.newUndoPoint()
        # undo.increaseBlocking()
        #
        # currentParams = self._getPeaksParams(peaks)
        # try:
        #     AssignmentLib.refitPeaks(peaks)
        # finally:
        #     undo.decreaseBlocking()
        #     undo.newItem(self._setPeaksParams, self._setPeaksParams, undoArgs=[peaks, currentParams],
        #                  redoArgs=[peaks, self._getPeaksParams(peaks)])

    def reorderPeakListAxes(self):
        """Reorder axes of all peaks in peakList of first selected peak by right-mouse menu
        """
        current = self.application.current
        peaks = current.peaks
        clickedPeaks = current.strip._lastClickedObjects if current.strip else None

        # return if both the lists are empty
        if not (peaks or clickedPeaks):
            return

        with undoBlockWithoutSideBar():
            if set(clickedPeaks or []):
                from ccpn.ui.gui.popups.ReorderPeakListAxes import ReorderPeakListAxes as ReorderPeakListAxesPopup

                popup = ReorderPeakListAxesPopup(parent=self, mainWindow=self, peakList=clickedPeaks[0].peakList)
                popup.exec_()

    def arrangeLabels(self, selected: bool = False):
        """Auto-arrange the peak/multiplet labels to minimise any overlaps, in the current spectrumDisplay.
        :param selected:
        """
        current = self.application.current

        if current.strip:
            with undoBlockWithoutSideBar():
                current.strip.spectrumDisplay.arrangeLabels(selected=selected)

    def resetLabels(self, selected: bool = False):
        """Reset arrangement of peak/multiplet labels, in the current spectrumDisplay.
        :param selected:
        """
        current = self.application.current

        if current.strip:
            with undoBlockWithoutSideBar():
                current.strip.spectrumDisplay.resetLabels(selected=selected)

    def selectAllPeaks(self, strip=None):
        """selects all peaks in the strip or current strip if any and if the spectrum is toggled on.
        """
        if strip is None and self.application.current.strip:
            strip = self.application.current.strip

        if strip and not strip.isDeleted:
            spectra = [spectrumView.spectrum for spectrumView in strip.spectrumViews
                       if spectrumView.isDisplayed]
            listOfPeaks = [peakList.peaks for spectrum in spectra for peakList in spectrum.peakLists]

            self.application.current.peaks = [peak for peaks in listOfPeaks for peak in peaks]

    def addMultiplet(self):
        """add current peaks to a new multiplet"""
        strip = self.application.current.strip

        with undoBlockWithoutSideBar():
            if strip and strip.spectrumDisplay:
                spectra = [spectrumView.spectrum for spectrumView in
                           strip.spectrumViews if spectrumView.isDisplayed]
                for spectrum in spectra:
                    if len(spectrum.multipletLists) < 1:
                        multipletList = spectrum.newMultipletList()
                    else:
                        multipletList = spectrum.multipletLists[-1]
                    peaks = [peak for peakList in spectrum.peakLists for peak in peakList.peaks if
                             peak in self.application.current.peaks]
                    if peaks:
                        # only create a multiplet that contains peaks
                        multiplet = multipletList.newMultiplet(peaks=peaks)
                        self.application.current.multiplet = multiplet

    def mergeCurrentMultiplet(self):
        """Merge current peaks into current multiplet

        mouseMultiplet: multiplet to be merged into, if there is no current multiplet object under
        the mouse then default to first multiplet currently selected.
        """
        mouseMultiplet = self.application.current.strip.getObjectsUnderMouse().get('multiplets')

        allPeaks = self.application.current.peaks
        allMultiplets = self.application.current.multiplets
        multiplet = self.application.current.multiplet if mouseMultiplet is None else mouseMultiplet

        multiplet.mergeMultiplets(peaks=allPeaks, multiplets=allMultiplets)

    def newCollectionOfCurrentPeaks(self):
        """add current peaks to a new collection"""
        from ccpn.util.Common import flattenLists
        from ccpn.core.lib.PeakCollectionLib import _getCollectionNameForAssignments, _getCollectionNameFromPeakPosition

        strip = self.application.current.strip
        with undoBlockWithoutSideBar():
            if strip and strip.spectrumDisplay:
                spectra = [spectrumView.spectrum for spectrumView in strip.spectrumViews if spectrumView.isDisplayed]
                peaks = [peak for peak in self.application.current.peaks if peak.spectrum in spectra]
                nmrAtoms = set(flattenLists([peak.assignedNmrAtoms for peak in peaks]))
                name = _getCollectionNameForAssignments(list(nmrAtoms))  # get a name from assigned peaks
                if not name:
                    name = _getCollectionNameFromPeakPosition(peaks[0])  # alternatively get a name from ppm position
                # we need to check if ordering is crucial here. For series is taking care by the SG where peaks belong.
                collection = self.application.project.newCollection(items=list(set(peaks)), name=name)
                self.application.current.collection = collection

    def traceScaleScale(self, window: 'GuiWindow', scale: float):
        """
        Changes the scale of a trace in all spectrum displays of the window.
        """
        # for spectrumDisplay in window.spectrumDisplays:

        if self.application.current.strip:
            spectrumDisplay = self.application.current.strip.spectrumDisplay

            if not spectrumDisplay.is1D:
                for strip in spectrumDisplay.strips:
                    _update = False
                    for spectrumView in strip.spectrumViews:
                        if spectrumView.traceScale is not None:
                            # may not have been initialised as no trace
                            spectrumView.traceScale *= scale
                            _update = True

                    if _update:
                        # spawn a redraw of the strip
                        strip._updatePivot()

    def traceScaleUp(self, window: 'GuiWindow', scale=1.4):
        """
        Doubles the scale for all traces in the specified window.
        """
        self.traceScaleScale(window, scale=scale)

    def traceScaleDown(self, window: 'GuiWindow', scale=(1.0 / 1.4)):
        """
        Halves the scale for all traces in the specified window.
        """
        self.traceScaleScale(window, scale=scale)

    def toggleHTrace(self, window: 'GuiWindow'):
        """
        Toggles whether horizontal traces are displayed in the specified window.
        """
        if self.application.current.strip:
            self.application.current.strip.spectrumDisplay.toggleHTrace()

    def toggleVTrace(self, window: 'GuiWindow'):
        """
        Toggles whether vertical traces are displayed in the specified window.
        """
        if self.application.current.strip:
            self.application.current.strip.spectrumDisplay.toggleVTrace()

    def toggleLastAxisOnly(self, window: 'GuiWindow'):
        """
        Toggles whether the axis is displayed in the last strip of the display
        """
        if self.application.current.strip:
            self.application.current.strip.toggleLastAxisOnly()

    def togglePhaseConsole(self, window: 'GuiWindow'):
        """
        Toggles whether the phasing console is displayed in the specified window.
        """
        for spectrumDisplay in window.spectrumDisplays:
            spectrumDisplay.togglePhaseConsole()

    def newPhasingTrace(self):
        strip = self.application.current.strip
        if strip:  # and (strip.spectrumDisplay.window is self):
            strip._newPhasingTrace()

    def stackSpectra(self):
        strip = self.application.current.strip
        if strip:  # and (strip.spectrumDisplay.window is self):
            strip._toggleStackPhaseFromShortCut()

    def setPhasingPivot(self):

        strip = self.application.current.strip
        if strip:  # and (strip.spectrumDisplay.window is self):
            strip._setPhasingPivot()

    def removePhasingTraces(self):
        """
        Removes all phasing traces from all strips.
        """
        strip = self.application.current.strip
        if strip:  # and (strip.spectrumDisplay.window is self):
            # strip.removePhasingTraces()
            for strip in strip.spectrumDisplay.strips:
                strip.removePhasingTraces()

    def _clearCurrentPeaks(self):
        """
        Sets current.peaks to an empty list.
        """
        # self.application.current.peaks = []
        self.application.current.clearPeaks()

    def filterOnCurrentTable(self):
        if hasattr(self.current, 'guiTable'):
            currentGuiTable = self.current.guiTable
            if currentGuiTable is not None:
                currentGuiTable.showSearchSettings()

    def setContourLevels(self):
        """
        Open the contour settings popup for the current strip
        """
        strip = self.application.current.strip
        if strip:
            strip.spectrumDisplay.adjustContours()

    # def toggleCrosshairAll(self):
    #     """
    #     Toggles whether crosshairs are displayed in all windows.
    #     """
    #     for window in self.project.windows:
    #         window.toggleCrosshair()

    def toggleCrosshair(self):
        """
        Toggles whether crosshairs are displayed in all spectrum displays
        """
        # toggle crosshairs for the spectrum displays in this window
        for spectrumDisplay in self.spectrumDisplays:
            spectrumDisplay.toggleCrosshair()

    def showEstimateNoisePopup(self):
        """estimate the noise in the visible region of the current strip
        """
        strip = self.application.current.strip
        if strip:
            strip._showEstimateNoisePopup()

    def createMark(self, axisIndex=None):
        """
        Creates a mark at the current cursor position in the current strip.
        """
        strip = self.application.current.strip
        if strip:
            strip._createMarkAtCursorPosition(axisIndex)

    def createPeakAxisMarks(self, axisIndex=None):
        """
        Creates marks at the selected peak positions.
        """
        strip = self.application.current.strip
        if strip:
            strip._markSelectedPeaks(axisIndex)

    def createMultipletAxisMarks(self, axisIndex=None):
        """
        Creates marks at the selected multiplet positions.
        """
        strip = self.application.current.strip
        if strip:
            strip._markSelectedMultiplets(axisIndex)

    @logCommand('mainWindow.')
    def clearMarks(self):
        """
        Clears all marks in all windows for the current task.
        """
        self.project.deleteObjects(*self.project.marks)

    def markPositions(self, axisCodes, chemicalShifts, strips=None):
        """
        Create marks based on the axisCodes and adds annotations where appropriate.

        :param axisCodes: The axisCodes making a mark for
        :param chemicalShifts: A list or tuple of ChemicalShifts at whose values the marks should be made
        """
        project = self.application.project

        # colourDict = guiSettings.MARK_LINE_COLOUR_DICT  # maps atomName --> colour
        for ii, axisCode in enumerate(axisCodes):
            for chemicalShift in chemicalShifts[ii]:
                atomId = chemicalShift.nmrAtom.id
                atomName = chemicalShift.nmrAtom.name
                # TODO: the below fails, for example, if nmrAtom.name = 'Hn', can that happen?

                # colour = colourDict.get(atomName[:min(2,len(atomName))])
                colourMarks = guiSettings.getColours().get(guiSettings.MARKS_COLOURS)
                # colour = colourMarks[atomName[:min(2,len(atomName))]]
                colour = colourMarks.get(atomName[:min(2, len(atomName))])
                if not colour:
                    colour = colourMarks.get(guiSettings.DEFAULT)

                # exit if mark exists
                found = any(
                        atomName in mm.labels
                        and colour == mm.colour
                        and abs(chemicalShift.value - mm.positions[0]) < 1e-6
                        for mm in project.marks
                        )
                if found:
                    continue

                # with logCommandBlock(get='self') as log:
                #     log('markPositions')
                with undoBlockWithoutSideBar():
                    # GWV 20181030: changed from atomName to id
                    if colour:
                        self.newMark(colour, [chemicalShift.value], [axisCode], labels=[atomId], strips=strips)
                    else:
                        # just use default mark colour rather than checking colourScheme
                        defaultColour = self.application.preferences.general.defaultMarksColour

                        try:
                            _prefsGeneral = self.application.preferences.general
                            defaultColour = _prefsGeneral.defaultMarksColour
                            if not defaultColour.startswith('#'):
                                colourList = colorSchemeTable[defaultColour] if defaultColour in colorSchemeTable else [
                                    '#FF0000']
                                _prefsGeneral._defaultMarksCount = _prefsGeneral._defaultMarksCount % len(colourList)
                                defaultColour = colourList[_prefsGeneral._defaultMarksCount]
                                _prefsGeneral._defaultMarksCount += 1
                        except Exception:
                            defaultColour = '#FF0000'

                        try:
                            self.newMark(defaultColour, [chemicalShift.value], [atomId], strips=strips)
                        except Exception as es:
                            getLogger().warning('Error setting mark at position')
                            raise (es)

    def markPpmPositions(self, axisCodes, positions, strips=None):
        """
        Create marks based on the axisCodes and adds annotations where appropriate.

        :param axisCodes: The axisCodes making a mark for.
        :param positions: A list or tuple of positions at whose values the marks should be made.
        """
        with undoBlockWithoutSideBar():

            for ii, (axisCode, position) in enumerate(zip(axisCodes, positions)):

                if position is None:
                    continue

                try:
                    _prefsGeneral = self.application.preferences.general
                    defaultColour = _prefsGeneral.defaultMarksColour
                    if not defaultColour.startswith('#'):
                        colourList = colorSchemeTable[defaultColour] if defaultColour in colorSchemeTable else [
                            '#FF0000']
                        _prefsGeneral._defaultMarksCount = _prefsGeneral._defaultMarksCount % len(colourList)
                        defaultColour = colourList[_prefsGeneral._defaultMarksCount]
                        _prefsGeneral._defaultMarksCount += 1
                except Exception:
                    defaultColour = '#FF0000'

                try:
                    self.newMark(defaultColour, [position], [axisCode], strips=strips)
                except Exception:
                    getLogger().warning(f'Error setting mark at position {position}')

    def toggleGridAll(self):
        """
        Toggles grid display in all windows
        """
        for window in self.project.windows:
            window.toggleGrid()

    def toggleGrid(self):
        """
        toggle grid for the spectrum displays in this window.
        """
        for spectrumDisplay in self.spectrumDisplays:
            spectrumDisplay.toggleGrid()

    def toggleSideBandsAll(self):
        """
        Toggles sideBand display in all windows
        """
        for window in self.project.windows:
            window.toggleSideBands()

    def toggleSideBands(self):
        """
        toggle sideBands for the spectrum displays in this window.
        """
        for spectrumDisplay in self.spectrumDisplays:
            spectrumDisplay.toggleSideBands()

    def moveToNextSpectrum(self):
        """
        moves to next spectrum on the current strip, Toggling off the currently displayed spectrum.
        """
        if self.current.strip:
            self.current.strip._moveToNextSpectrumView()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def moveToPreviousSpectrum(self):
        """
        moves to next spectrum on the current strip, Toggling off the currently displayed spectrum.
        """
        if self.current.strip:
            self.current.strip._moveToPreviousSpectrumView()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def showAllSpectra(self):
        """
        shows all spectra in the spectrum display.
        """
        if self.current.strip:
            self.current.strip._showAllSpectrumViews(True)
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def hideAllSpectra(self):
        """
        hides all spectra in the spectrum display.
        """
        if self.current.strip:
            self.current.strip._showAllSpectrumViews(False)
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def invertSelectedSpectra(self):
        """
        invertes the selected spectra in the spectrum display. The toggled in will be hided and the hidden spectra will be displayed.
        """
        if self.current.strip:
            self.current.strip._invertSelectedSpectra()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    @logCommand('mainWindow.')
    def snapCurrentPeaksToExtremum(self):
        """
        Snaps selected peaks. If more than one, pops up a Yes/No.
        Uses the minDropFactor from the preferences, and applies a parabolic fit to give first-estimate of lineWidths
        """
        peaks = list(self.current.peaks)
        if not peaks:
            return

        # get the default from the preferences
        minDropFactor = self.application.preferences.general.peakDropFactor
        searchBoxMode = self.application.preferences.general.searchBoxMode
        searchBoxDoFit = self.application.preferences.general.searchBoxDoFit
        fitMethod = self.application.preferences.general.peakFittingMethod

        with undoBlockWithoutSideBar():
            n = len(peaks)

            if n == 1:
                try:
                    peak = peaks[0]
                    peak.snapToExtremum(halfBoxSearchWidth=4, halfBoxFitWidth=4,
                                        minDropFactor=minDropFactor, searchBoxMode=searchBoxMode,
                                        searchBoxDoFit=searchBoxDoFit, fitMethod=fitMethod)
                    if peak.spectrum.dimensionCount == 1 and peak.figureOfMerit < 1:
                        showWarning(f'Cannot snap peak', f'Figure of merit below the snapping threshold of 1.')
                except Exception as es:
                    showWarning('Snap to Extremum', str(es))

            elif n > 1:
                with progressManager(self, 'Snapping peaks to extrema'):

                    # try:
                    _is1Ds = [p.spectrum.dimensionCount == 1 for p in peaks]
                    if all(_is1Ds):
                        from ccpn.core.lib.PeakPickers.PeakSnapping1D import snap1DPeaks

                        snap1DPeaks(peaks)
                        nonSnappingPeaks = [pk for pk in peaks if pk.figureOfMerit < 1]

                        msg = 'one of the selected peak' if len(nonSnappingPeaks) == 1 else 'some of the selected peaks'
                        if len(nonSnappingPeaks) > 0:
                            showWarning(f'Cannot snap {msg}',
                                        f'Figure of merit below the snapping threshold of 1 for {nonSnappingPeaks}')
                    else:
                        peaks.sort(key=lambda x: x.position[0] if x.position and None not in x.position else 0,
                                   reverse=False)  # reorder peaks by position
                        for peak in peaks:
                            peak.snapToExtremum(halfBoxSearchWidth=4, halfBoxFitWidth=4,
                                                minDropFactor=minDropFactor, searchBoxMode=searchBoxMode,
                                                searchBoxDoFit=searchBoxDoFit, fitMethod=fitMethod)

                # except Exception as es:
                #     showWarning('Snap to Extremum', str(es))

            else:
                getLogger().warning('No selected peak/s. Select a peak first.')

    def storeZoom(self):
        """
        store the zoom of the currently selected strip
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay._storeZoom()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def restoreZoom(self):
        """
        restore the zoom of the currently selected strip
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay._restoreZoom()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def previousZoom(self):
        """
        change to the previous stored zoom
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay._previousZoom()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def nextZoom(self):
        """
        change to the next stored zoom
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay._nextZoom()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def zoomIn(self):
        """
        zoom in to the currently selected strip
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay._zoomIn()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def zoomOut(self):
        """
        zoom out of the currently selected strip
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay._zoomOut()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def panSpectrum(self, direction: str = 'up'):
        """
        Pan/Zoom the current strip with the cursor keys
        """
        if self.current.strip:
            self.current.strip._panSpectrum(direction)
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def movePeaks(self, direction: str = 'up'):
        """
        Move the peaks in the current strip with the cursors
        """
        if self.current.strip:
            self.current.strip._movePeaks(direction)
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def resetAllZoom(self):
        """
        zoom out of the currently selected strip
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay._resetAllZooms()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def cycleSymbolLabelling(self):
        """
        restore the zoom of the currently selected strip to the top item of the queue
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay._cycleSymbolLabelling()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def cyclePeakSymbols(self):
        """
        restore the zoom of the currently selected strip to the top item of the queue
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay._cyclePeakSymbols()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def _setMouseMode(self, mode):
        if mode in MouseModes:
            # self.mouseMode = mode
            setCurrentMouseMode(mode)
            for sd in self.project.spectrumDisplays:
                for strp in sd.strips:
                    strp.mouseModeAction.setChecked(mode == PICK)
            mouseModeText = ' Mouse Mode: '
            self.statusBar().showMessage(mouseModeText + mode)

    def switchMouseMode(self):
        # mode = self.mouseMode
        modesCount = len(MouseModes)
        mode = getCurrentMouseMode()
        if mode in MouseModes:
            i = MouseModes.index(mode)
            if i + 1 < modesCount:
                mode = MouseModes[i + 1]
                self._setMouseMode(mode)
            else:
                i = 0
                mode = MouseModes[i]
                self._setMouseMode(mode)

    def _findMenuAction(self, menubarText, menuText):
        # not sure if this function will be needed more widely or just in console context
        # CCPN internal: now also used in SequenceModule._closeModule
        # Should be stored in a dictionary upon initialisation!

        for menuBarAction in self._menuBar.actions():
            if menuBarAction.text() == menubarText:
                break
        else:
            return None

        for menuAction in menuBarAction.menu().actions():
            if menuAction.text() == menuText:
                return menuAction

        return None

    def toggleConsole(self):
        """

        - Opens a new pythonConsole module if none available.
        - Show/hide the pythonConsole module if already one available.
        """
        from ccpn.ui.gui.modules.PythonConsoleModule import PythonConsoleModule

        _justCreated = False
        if self.pythonConsoleModule is None:  # No pythonConsole module detected, so create one.
            self.moduleArea.addModule(PythonConsoleModule(self), 'bottom')
            _justCreated = True
        if self.pythonConsoleModule:
            if self.pythonConsoleModule.isHidden():
                self.pythonConsoleModule.show()
            elif not _justCreated:
                self.pythonConsoleModule.hide()

    def _lowerContourBaseCallback(self):
        """Callback to lower the contour level for the currently
        selected strip
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay.lowerContourBase()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def _raiseContourBaseCallback(self):
        """Callback to increase the contour level for the currently
        selected strip
        """
        if self.current.strip:
            self.current.strip.spectrumDisplay.raiseContourBase()
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def previousZPlane(self):
        """
        navigate to the previous Z plane for the currently selected strip
        """
        if self.current.strip:
            self.current.strip._changePlane(stripAxisIndex=2, planeIncrement=-1)
        else:
            getLogger().warning('No current strip. Select a strip first.')

    def nextZPlane(self):
        """
        navigate to the next Z plane for the currently selected strip
        """
        if self.current.strip:
            self.current.strip._changePlane(stripAxisIndex=2, planeIncrement=1)
        else:
            getLogger().warning('No current strip. Select a strip first.')

    @logCommand('mainWindow.')
    def markSelectedPeaks(self, axisIndex=None):
        """Mark the positions of all selected peaks
        """
        if self.current.strip:
            with undoBlockWithoutSideBar():
                for peak in self.current.peaks:
                    self.current.strip._createObjectMark(peak, axisIndex)

    @logCommand('mainWindow.')
    def markSelectedMultiplets(self, axisIndex=None):
        """Mark the positions of all selected multiplets
        """
        if self.current.strip:
            with undoBlockWithoutSideBar():
                for multiplet in self.current.multiplets:
                    self.current.strip._createObjectMark(multiplet, axisIndex)

    def makeStripPlot(self, includePeakLists=True, includeNmrChains=True, includeSpectrumTable=False):
        """Make a strip plot in the current spectrumDisplay
        """
        if self.current.strip and not self.current.strip.isDeleted:
            from ccpn.ui.gui.popups.StripPlotPopup import StripPlotPopup

            popup = StripPlotPopup(parent=self, mainWindow=self, spectrumDisplay=self.current.strip.spectrumDisplay,
                                   includePeakLists=includePeakLists, includeNmrChains=includeNmrChains,
                                   includeSpectrumTable=includeSpectrumTable)
            popup.exec_()
        else:
            showWarning('Make Strip Plot', 'No selected spectrumDisplay')


class MainWindow(_CoreClassMainWindow, GuiMainWindow):
    """GUI main window, corresponds to OS window"""

    def __init__(self, project: Project, wrappedData: 'ApiWindow'):
        logger = Logging.getLogger()
        logger.debug(f'MainWindow>> project: {project}')
        logger.debug(f'MainWindow>> project.application: {project.application}')

        _CoreClassMainWindow.__init__(self, project, wrappedData)

        application = project.application
        GuiMainWindow.__init__(self, application=application)

        # patches for now:
        project._mainWindow = self
        application._mainWindow = self
        application.ui.mainWindow = self
