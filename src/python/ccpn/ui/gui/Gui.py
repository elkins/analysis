"""
The top-level Gui class for all user interactions
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
__dateModified__ = "$dateModified: 2024-10-04 11:47:18 +0100 (Fri, October 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Wayne Boucher $"
__date__ = "$Date: 2017-03-16 18:20:01 +0000 (Thu, March 16, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
import typing
import re
import json
from PyQt5 import QtWidgets, QtCore, QtGui
from functools import partial
from ccpn.core.Project import Project

from ccpn.framework.Application import getApplication
from ccpn.framework.PathsAndUrls import CCPN_EXTENSION
from ccpn.framework.lib.DataLoaders.DataLoaderABC import _checkPathForDataLoader

from ccpn.core.lib.ContextManagers import (
    notificationEchoBlocking, catchExceptions,
    logCommandManager, undoStackBlocking, busyHandler)

from ccpn.ui.Ui import Ui
from ccpn.ui.gui.popups.RegisterPopup import RegisterPopup, NewTermsConditionsPopup
from ccpn.ui.gui.widgets.Application import Application
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets import FileDialog
from ccpn.ui.gui.widgets.Font import getSystemFonts
# from ccpn.ui.gui.widgets.Frame import ScrollableFrame
from ccpn.ui.gui.popups.ImportStarPopup import StarImporterPopup

# This import initializes relative paths for QT style-sheets.  Do not remove! GWV ????
from ccpn.ui.gui.guiSettings import (FontSettings, consoleStyle, getTheme,
                                     getColours, PALETTE, Theme, setColourScheme)
# from ccpn.ui.gui.widgets.Font import getFontHeight
from ccpn.ui.gui.widgets.Icon import Icon

from ccpn.util.Logging import getLogger
from ccpn.util import Logging
from ccpn.util import Register
from ccpn.util.Path import aPath
from ccpn.util.decorators import logCommand

from ccpnmodel.ccpncore.memops.ApiError import ApiError


#-----------------------------------------------------------------------------------------
# Subclass the exception hook fpr PyQT
#-----------------------------------------------------------------------------------------

def _ccpnExceptionhook(ccpnType, value, tback):
    """This because PyQT raises and catches exceptions,
    but doesn't pass them along instead makes the program crashing miserably.
    """
    if (application := getApplication()):
        if application._isInDebugMode:
            sys.stderr.write('_ccpnExceptionhook: type = %s\n' % ccpnType)
            sys.stderr.write('_ccpnExceptionhook: value = %s\n' % value)
            sys.stderr.write('_ccpnExceptionhook: tback = %s\n' % tback)

        # # this is crashing on Windows 10 Enterprise :|
        # if application.hasGui:
        #     title = f'{str(ccpnType)[8:-2]}:'
        #     text = str(value)
        #     MessageDialog.showError(title=title, message=text)

        if application.project and not application.project.readOnly:
            application.project._updateLoggerState(readOnly=False, flush=True)

    sys.__excepthook__(ccpnType, value, tback)


sys.excepthook = _ccpnExceptionhook


#-----------------------------------------------------------------------------------------


def qtMessageHandler(*errors):
    for err in errors:
        Logging.getLogger().warning(f'{consoleStyle.fg.red}QT error: {err}{consoleStyle.reset}')


# un/suppress messages
QtCore.qInstallMessageHandler(qtMessageHandler)

# REMOVEDEBUG = r'\(\w+\.\w+:\d+\)$'
REMOVEDEBUG = r'\(\S+\.\w+:\d+\)$'

MAXITEMLOGGING = 4
MAXITEMLOADING = 5
MAXITEMDEPTH = 5


#=========================================================================================
# _MyAppProxyStyle
#=========================================================================================

class _MyAppProxyStyle(QtWidgets.QProxyStyle):
    """Class to handle resizing icons in menus
    """

    # def drawPrimitive(self, element: QtWidgets.QStyle.PrimitiveElement,
    #                   option: QtWidgets.QStyleOption,
    #                   painter: QtGui.QPainter,
    #                   widget: typing.Optional[QtWidgets.QWidget] = ...) -> None:
    #     focus = False
    #     if element in {QtWidgets.QStyle.PE_FrameLineEdit,
    #                    QtWidgets.QStyle.PE_FrameFocusRect,
    #                    QtWidgets.QStyle.PE_PanelButtonCommand,
    #                    }:
    #         focus = option.state & QtWidgets.QStyle.State_HasFocus
    #         option.state &= ~(QtWidgets.QStyle.State_HasFocus | QtWidgets.QStyle.State_Selected)
    #         # Customise the highlight color for a soft background
    #         if Base._highlightMid is not None:
    #             option.palette.setColor(option.palette.Highlight, Base._highlightMid)
    #     if element == QtWidgets.QStyle.PE_FrameFocusRect and isinstance(widget, QtWidgets.QPushButton):
    #         # replace the QPushButton focus with just a border
    #         if (efb := getattr(widget, '_enableFocusBorder', None)) is None or efb is True:
    #             self._drawBorder(element, painter, widget, col=Base._highlightVivid)
    #         return
    #     super().drawPrimitive(element, option, painter, widget)
    #     if focus and element in {QtWidgets.QStyle.PE_FrameLineEdit,
    #                              }:
    #         # draw new focus-border
    #         self._drawBorder(element, painter, widget, col=Base._highlightVivid)

    def drawControl(self, element, option, painter, widget=None):
        # if element in {QtWidgets.QStyle.CE_TabBarTab,
        #                }:
        #     # Customise the highlight color for the tab-widget
        #     if Base._highlightVivid is not None:
        #         option.palette.setColor(option.palette.Highlight, Base._highlightVivid)
        if (element in {QtWidgets.QStyle.CE_MenuItem,} and
              isinstance(option, QtWidgets.QStyleOptionMenuItem) and
                (_actionGeometries := getattr(widget, '_actionGeometries', None)) and
                (action := _actionGeometries.get(str(option.rect))) and
                (colour := getattr(action, '_foregroundColour', None))):
            # Customise the foreground colour for the menu-item from the QAction
            # - menu-items don't have a stylesheet or palette
            option.palette.setColor(option.palette.Text, colour)
        super().drawControl(element, option, painter, widget)
        # if element in {QtWidgets.QStyle.CE_ItemViewItem, } and (option.state & QtWidgets.QStyle.State_HasFocus):
        #     # draw border inside the listWidget/listView/TreeView
        #     #   - draws border inside pulldowns though, shame :(
        #     self._drawBorder(element, painter, widget, col=Base._highlightVivid)

    def drawComplexControl(self, control: QtWidgets.QStyle.ComplexControl,
                           option: QtWidgets.QStyleOptionComplex,
                           painter: QtGui.QPainter,
                           widget: typing.Optional[QtWidgets.QWidget] = ...) -> None:
        focus = None
        if control in {QtWidgets.QStyle.CC_ComboBox,
                       QtWidgets.QStyle.CC_SpinBox,
                       }:
            focus = option.state & QtWidgets.QStyle.State_HasFocus
            option.state &= ~QtWidgets.QStyle.State_HasFocus
            if control in {QtWidgets.QStyle.CC_ComboBox,}:
                # hack to set the drop-arrow colour
                # using window-text allows setting the text colour on non-editable combobox
                option.palette.setColor(option.palette.ButtonText,
                                        option.palette.color(QtGui.QPalette.Active,
                                                             QtGui.QPalette.ColorRole(QtGui.QPalette.WindowText)))
        # elif control in {QtWidgets.QStyle.CC_Slider,} and Base._highlightVivid is not None:
        #     option.palette.setColor(option.palette.Highlight, Base._highlightVivid)
        super().drawComplexControl(control, option, painter, widget)
        if focus:
            # draw new focus-border
            self._drawBorder(control, painter, widget,
                             col=option.palette.highlight().color())

    @staticmethod
    def _drawBorder(control, p, widget, col=None):
        p.save()
        try:
            wind = widget.rect()
            if control == QtWidgets.QStyle.CC_SpinBox:
                # not sure why the border is off slightly
                wind = wind.adjusted(0, 1, 0, -1)  # x1, y1 - x2, y2
            elif control == QtWidgets.QStyle.CE_ItemViewItem:
                # border is off because the border-width is outside the widget :|
                wind = wind.adjusted(-1, -1, -1, -1)
            # paint the new border
            p.translate(0.5, 0.5)  # move to pixel-centre
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            col = col or QtGui.QColor('red')
            col.setAlpha(40)  # feint must be done first so that QSlider draws correctly
            p.setPen(col)
            p.drawRoundedRect(wind.adjusted(1, 1, -2, -2), 1.7, 1.7)
            col.setAlpha(255)
            p.setPen(col)
            p.drawRoundedRect(wind.adjusted(0, 0, -1, -1), 2, 2)
        except Exception:
            ...
        finally:
            p.translate(-0.5, -0.5)
            p.restore()

    def standardIcon(self, standardIcon, option=None, widget=None) -> QtGui.QIcon:
        # change the close-button of the line-edit to a cleaner icon, set by setClearButtonEnabled
        if standardIcon == QtWidgets.QStyle.SP_LineEditClearButton:
            return Icon('icons/close-lineedit')
        return super().standardIcon(standardIcon, option, widget)


#=========================================================================================
# Gui
#=========================================================================================

class Gui(Ui):
    """Top class for the GUI interface
    """

    def __init__(self, application):

        # sets self.mainWindow (None), self.application and self.pluginModules
        Ui.__init__(self, application)

        # GWV: this is not ideal and needs to move into the Gui class
        application._fontSettings = FontSettings(application.preferences)
        application._setColourSchemeAndStyleSheet()
        application._setupMenus()

        self._initQtApp()

    def _initQtApp(self):
        # On the Mac (at least) it does not matter what you set the applicationName to be,
        # it will come out as the executable you are running (e.g. "python3")

        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

        # NOTE:ED - this is essential for multi-window applications
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts, True)
        # experimental - makes a mess!
        # QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseStyleSheetPropagationInWidgetStyles, True)

        # fm = QtGui.QSurfaceFormat()
        # fm.setSamples(4)
        # # NOTE:ED - Do not do this, they cause QT to exhibit strange behaviour
        # #     - think is QT bug when recompiling :|
        # # fm.setSwapInterval(0)  # disable VSync
        # # fm.setSwapBehavior(QtGui.QSurfaceFormat.DoubleBuffer)
        # QtGui.QSurfaceFormat.setDefaultFormat(fm)

        self.qtApp = Application(self.application.applicationName,
                                 self.application.applicationVersion,
                                 organizationName='CCPN', organizationDomain='ccpn.ac.uk')
        # patch for icon sizes in menus, etc.
        styles = QtWidgets.QStyleFactory()
        myStyle = _MyAppProxyStyle(styles.create('fusion'))
        self.qtApp.setStyle(myStyle)

        # override the dark/light theme
        self._changeThemeInstant()

        # read the current system-fonts
        getSystemFonts()
        # # original - no patch for icon sizes
        # styles = QtWidgets.QStyleFactory()
        # self.qtApp.setStyle(styles.create('fusion'))

    def _changeThemeInstant(self, theme: str=None, colour: str=None, themeSD: str=None):
        """Set the light/dark palette in single step.
        0 - dark, 1 - light, 2 - default = follow OS/application
        """
        prefsApp = self.application.preferences.appearance
        prefsGen = self.application.preferences.general

        _th, _col, _thSD = getTheme()  # should have been set on creation
        if theme is None: theme = _th.dataValue
        if themeSD is None: themeSD = _thSD.dataValue
        if colour is None: colour = _col

        if not isinstance(theme, Theme) and theme not in Theme.dataValues():
            raise ValueError(f'{self.__class__.__name__}._changeThemeInstant: theme not in {Theme.dataValues()}')
        if not isinstance(themeSD, Theme) and themeSD not in Theme.dataValues():
            raise ValueError(f'{self.__class__.__name__}._changeThemeInstant: themeSD not in {Theme.dataValues()}')
        if not isinstance(colour, str):
            raise TypeError(f'{self.__class__.__name__}._changeThemeInstant: colour not of type str')
        try:
            # test the colour
            QtGui.QColor(colour)
        except Exception:
            raise ValueError(f'{self.__class__.__name__}._changeThemeInstant: colour {colour!r} not valid')

        getLogger().debug(f'{consoleStyle.fg.darkblue}==> start palette-change event.{consoleStyle.reset}')
        # set highlight to the required highlighting colour
        # set the theme in preferences
        th = Theme.getByDataValue(theme)
        thSD = Theme.getByDataValue(themeSD)
        prefsApp.themeStyle = th.dataValue  # application theme
        prefsApp.themeColour = colour
        prefsGen.colourScheme = thSD.dataValue  # spectrumDisplay theme

        if pal := setColourScheme(th, colour, thSD):
            self.qtApp.setPalette(pal)
            # QtCore.QTimer.singleShot(0, partial(self.qtApp.setPalette, pal))
            QtCore.QTimer.singleShot(0, partial(self.qtApp.sigPaletteChanged.emit, pal,
                                              prefsApp.themeStyle,
                                              prefsApp.themeColour,
                                              prefsGen.colourScheme)
                                     )
        getLogger().debug(f'{consoleStyle.fg.darkblue}==> end palette-change event.{consoleStyle.reset}')

        # pal = setColourScheme(th, colour, thSD)
        # groups = [QtGui.QPalette.Active, QtGui.QPalette.Inactive, QtGui.QPalette.Disabled]
        # if (colours := getColours()) and (theme := colours.get(PALETTE)):
        #     for role, cols in theme.items():
        #         for group, col in zip(groups, cols):
        #             pal.setColor(group, role, QtGui.QColor(col))
        #
        #     base = pal.base().color().lightness()  # use as a guide for light/dark theme
        #     highlight = QtGui.QColor(prefsApp.themeColour)
        #     newCol = highlight.fromHslF(highlight.hueF(),
        #                                 0.95,
        #                                 highlight.lightnessF()**(0.5 if base > 127 else 2.0))
        #     for group in groups:
        #         pal.setColor(group, QtGui.QPalette.Highlight, newCol)
        #
        #     self.qtApp.setPalette(pal)
        #     QtCore.QTimer.singleShot(0, partial(self.qtApp.sigPaletteChanged.emit, pal,
        #                                       prefsApp.themeStyle,
        #                                       prefsApp.themeColour,
        #                                       prefsGen.colourScheme)
        #                              )
        #     getLogger().debug(f'{consoleStyle.fg.darkblue}==> end palette-change event.{consoleStyle.reset}')

    # def _changeTheme(self, state: int=0):
    #     """Set the light/dark palette in multiple-steps.
    #     Not useful at the moment - redraw between steps taking too long.
    #     0 - dark, 1 - light.
    #     """
    #     getLogger().debug(f'{consoleStyle.fg.darkblue}==> start palette-change event.{consoleStyle.reset}')
    #     self._lastPalette = self.qtApp.palette()
    #     self._nextPalette = lightPalette if state else darkPalette
    #     self._paletteStep = 0
    #     self._paletteTimer = QtCore.QTimer()
    #     self._paletteTimer.timeout.connect(self._updatePalette)
    #     self._paletteTimer.start(25)
    #     getLogger().debug(f'{consoleStyle.fg.darkblue}==> end palette-change event.{consoleStyle.reset}')

    @staticmethod
    def _interpolateColor(color1, color2, factor):
        """Interpolate between two QColor objects.
        """
        r = color1.red() + (color2.red() - color1.red()) * factor
        g = color1.green() + (color2.green() - color1.green()) * factor
        b = color1.blue() + (color2.blue() - color1.blue()) * factor
        a = color1.alpha() + (color2.alpha() - color1.alpha()) * factor
        return QtGui.QColor(int(r), int(g), int(b), int(a))

    def _updatePalette(self):
        MAXSTEPS = 3
        if self._paletteStep > MAXSTEPS:
            self._paletteTimer.stop()
            self._paletteTimer = None
            getLogger().debug(f'{consoleStyle.fg.darkblue}==> end palette-change event.{consoleStyle.reset}')
            return
        # if self._paletteStep >= MAXSTEPS:
        #     self.mainWindow._blockPaletteChange = 0
        # set highlight to the required highlighting colour
        groups = [QtGui.QPalette.Active, QtGui.QPalette.Inactive, QtGui.QPalette.Disabled]
        pal = self.qtApp.palette()
        for role, cols in self._nextPalette.items():
            for group, col in zip(groups, cols):
                newCol = self._interpolateColor(pal.color(group, role),
                                                QtGui.QColor(col),
                                                self._paletteStep / MAXSTEPS)
                pal.setColor(group, role, newCol)
        self.qtApp.setPalette(pal)
        self._paletteStep += 1

    @property
    def theme(self):
        """Return the current theme as dark/light.
        """
        pal = self.qtApp.palette()
        base = pal.base().color().lightness()  # use as a guide for light/dark theme
        return 'dark' if base < 127 else 'light'

    def setTheme(self, theme: str | int = 'light'):
        """Set the new light/dark theme.
        theme = 0|'dark' for dark, 1|'light' for light.
        """
        themeStates = {'dark': 0,
                       'light': 1,
                       0 : 0,
                       1 : 1}
        if theme not in themeStates:
            raise ValueError(f'{self.__class__.__name__}.setTheme: '
                             f'theme must be in {json.dumps(list(themeStates.keys()))}')
        pal = self.qtApp.palette()
        base = pal.base().color().lightness()  # use as a guide for light/dark theme
        if int(base > 127) != themeStates[theme]:
            self._changeThemeInstant(themeStates[theme])

    def initialize(self, mainWindow):
        """UI operations done after every project load/create
        """
        if mainWindow is None:
            raise ValueError('Gui.initialize: Undefined mainWindow')

        with notificationEchoBlocking():
            with undoStackBlocking():
                # Set up mainWindow
                self.mainWindow = self._setupMainWindow(mainWindow)
                self.application._initGraphics()
                self.mainWindow._updateRestoreArchiveMenu()
                self.application._updateCheckableMenuItems()

    def startUi(self):
        """Start the UI
        """
        self.mainWindow.show()
        QtWidgets.QApplication.setActiveWindow(self.mainWindow)

        # check whether to skip the execution loop for testing with mainWindow
        import builtins

        if not (_skip := getattr(builtins, '_skipExecuteLoop', False)):
            self.qtApp.start()

    def _registerDetails(self, registered=False, acceptedTerms=False):
        """Display registration popup"""
        days = Register._graceCounter(Register._fetchGraceFile(self.application))
        # check valid internet connection first
        if not Register.checkInternetConnection():
            msg = 'Could not connect to the registration server, please check your internet connection. ' \
                  'Register within %s day(s) to continue using the software' % str(days)
            MessageDialog.showError('Registration', msg)

        else:
            if registered and not acceptedTerms:
                popup = NewTermsConditionsPopup(self.mainWindow, trial=days,
                                                version=self.application.applicationVersion, modal=True)
            else:
                popup = RegisterPopup(self.mainWindow, trial=days, version=self.application.applicationVersion,
                                      modal=True)

            self.mainWindow.show()
            popup.exec_()
            self.qtApp.processEvents()

    def _setupMainWindow(self, mainWindow):
        # Set up mainWindow

        project = self.application.project
        mainWindow.sideBar.buildTree(project, clear=True)

        # mainWindow.raise_()  # whaaaaaat? causes the menu-bar to be unresponsive
        mainWindow.namespace['current'] = self.application.current
        return mainWindow

    def echoCommands(self, commands: typing.List[str]):
        """Echo commands strings, one by one, to logger
        and store them in internal list for perusal
        """
        logger = Logging.getLogger()
        for command in commands:
            logger.echoInfo(command)

        if self.application.ui is not None and \
                self.application.ui.mainWindow is not None and \
                self.application._enableLoggingToConsole:

            console = self.application.ui.mainWindow.pythonConsole
            for command in commands:
                command = re.sub(REMOVEDEBUG, '', command)
                console._write(command + '\n')

    def getByGid(self, gid):

        from ccpn.ui.gui.modules.CcpnModule import PidShortClassName, PidLongClassName
        from ccpn.core.lib.Pid import Pid

        pid = Pid(gid)
        if pid is not None and pid.type in [PidLongClassName, PidShortClassName]:
            # get the GuiModule object By its Gid
            return self.application.mainWindow.moduleArea.modules.get(pid.id)

        return self.application.getByGid(gid)

    def _execUpdates(self):
        """Use the Update popup to execute any updates
        """
        return self.application._showUpdatePopup()

    #-----------------------------------------------------------------------------------------
    # Helper methods
    #-----------------------------------------------------------------------------------------

    def _queryChoices(self, dataLoader):
        """Query the user about his/her choice to import/new/cancel
        """
        choices = ('Import', 'New project', 'Cancel')
        choice = MessageDialog.showMulti(
                f'Load {dataLoader.dataFormat}',
                f'How do you want to handle "{dataLoader.path}":',
                choices,
                parent=self.mainWindow,
                )

        if choice == choices[0]:  # import
            dataLoader.createNewProject = False
            createNewProject = False
            ignore = False

        elif choice == choices[1]:  # new project
            dataLoader.createNewProject = True
            createNewProject = True
            ignore = False

        else:  # cancel
            dataLoader = None
            createNewProject = False
            ignore = True

        return (dataLoader, createNewProject, ignore)

    def _getDataLoader(self, path, formatFilter=None):
        """Get dataLoader for path (or None if not present), optionally only testing for
        dataFormats defined in filter.
        Allows for reporting or checking through popups.
        Does not do the actual loading.

        :param path: the path to get a dataLoader for
        :param formatFilter: a list/tuple of optional dataFormat strings; filter optional dataLoaders for this
        :returns a tuple (dataLoader, createNewProject, ignore)

        :raises RuntimeError in case of failure to define a proper dataLoader
        """
        # local import here
        from ccpn.framework.lib.DataLoaders.CcpNmrV2ProjectDataLoader import CcpNmrV2ProjectDataLoader
        from ccpn.framework.lib.DataLoaders.CcpNmrV3ProjectDataLoader import CcpNmrV3ProjectDataLoader
        from ccpn.framework.lib.DataLoaders.NefDataLoader import NefDataLoader
        from ccpn.framework.lib.DataLoaders.SparkyDataLoader import SparkyDataLoader
        from ccpn.framework.lib.DataLoaders.StarDataLoader import StarDataLoader
        from ccpn.framework.lib.DataLoaders.DirectoryDataLoader import DirectoryDataLoader

        _path = aPath(path)
        if not _path.exists():
            raise RuntimeError(f'Path "{path}" does not exist')

        _loaders = _checkPathForDataLoader(path=path, formatFilter=formatFilter)
        dataLoader = None
        # log errors
        errMsg = None

        if len(_loaders) > 0 and _loaders[-1].isValid:
            # there is a valid one; use that
            dataLoader = _loaders[-1]

        elif len(_loaders) > 0:
            # We always get a loader back; report it here
            errMsg = f'{_loaders[-1].dataFormat} loader reported:\n\n{_loaders[-1].errorString}'

        else:
            raise RuntimeError(f'Unknown error finding a loader for {path}')

        # raise error if needed
        if errMsg:
            getLogger().warning(errMsg)
            raise RuntimeError(errMsg)

        createNewProject = dataLoader.createNewProject
        ignore = False

        path = dataLoader.path

        # Check that the path does not contain a bottom-level space
        if dataLoader.dataFormat in [CcpNmrV2ProjectDataLoader.dataFormat, CcpNmrV3ProjectDataLoader.dataFormat] and \
                ' ' in aPath(dataLoader.path).basename:
            MessageDialog.showWarning('Load Project', 'Encountered a problem loading:\n"%s"\n\n'
                                                      'Cannot load project folders where the project-name contains spaces.\n\n'
                                                      'Please rename the folder without spaces and try loading again.' % dataLoader.path)
            # skip loading bad projects
            ignore = True

        elif dataLoader.dataFormat == CcpNmrV2ProjectDataLoader.dataFormat:
            createNewProject = True
            dataLoader.createNewProject = True
            ok = MessageDialog.showYesNoWarning('Load Project',
                                                f'Project "{path.name}" was created with version-2 Analysis.\n'
                                                '\n'
                                                'CAUTION:\n'
                                                'The project will be converted to a version-3 project and saved as a new directory with .ccpn extension.\n'
                                                '\n'
                                                'Do you want to continue loading?')

            if not ok:
                # skip loading so that user can back-up/copy project
                getLogger().info(f'==> Cancelled loading ccpn project "{path}"')
                ignore = True

        elif dataLoader.dataFormat == CcpNmrV3ProjectDataLoader.dataFormat and Project._needsUpgrading(path):
            createNewProject = True
            dataLoader.createNewProject = True

            DONT_OPEN = "Don't Open"
            CONTINUE = 'Continue'
            MAKE_ARCHIVE = 'Make a backup archive (.tgz) of the project'

            dataLoader.makeArchive = False
            ok = MessageDialog.showMulti('Load Project',
                                         f'You are opening an older project (version 3.0.x) - {path.name}\n'
                                         '\n'
                                         'When you save, it will be upgraded and will not be readable by version 3.0.4\n',
                                         texts=[DONT_OPEN, CONTINUE],
                                         checkbox=MAKE_ARCHIVE, checked=False,
                                         )

            if all(ss not in ok for ss in [DONT_OPEN, MAKE_ARCHIVE, CONTINUE]):
                # there was an error from the dialog
                getLogger().debug(f'==> Cancelled loading ccpn project "{path}" - error in dialog')
                ignore = True
            if DONT_OPEN in ok:
                # user selection not to load
                getLogger().info(f'==> Cancelled loading ccpn project "{path}"')
                ignore = True
            elif MAKE_ARCHIVE in ok:
                # flag to make a backup archive
                dataLoader.makeArchive = True

        elif dataLoader.dataFormat == NefDataLoader.dataFormat:
            (dataLoader, createNewProject, ignore) = self._queryChoices(dataLoader)
            if dataLoader and not createNewProject and not ignore:
                # we are importing; popup the import window
                ok = self.mainWindow._showNefPopup(dataLoader)
                if not ok:
                    ignore = True

        elif dataLoader.dataFormat == SparkyDataLoader.dataFormat:
            (dataLoader, createNewProject, ignore) = self._queryChoices(dataLoader)

        elif dataLoader.isSpectrumLoader and dataLoader.existsInProject():
            ok = MessageDialog.showYesNoWarning('Loading Spectrum',
                                                f'"{dataLoader.dataSource.path}"\n'
                                                f'"{dataLoader.path}"\n'
                                                f'already exists in the project\n'
                                                '\n'
                                                'do you want to load?'
                                                )
            if not ok:
                ignore = True

        elif dataLoader.dataFormat == StarDataLoader.dataFormat and dataLoader:
            (dataLoader, createNewProject, ignore) = self._queryChoices(dataLoader)
            if dataLoader and not ignore:
                title = 'New project from NmrStar' if createNewProject else \
                    'Import from NmrStar'
                dataLoader.getDataBlock()  # this will read and parse the file
                popup = StarImporterPopup(dataLoader=dataLoader,
                                          parent=self.mainWindow,
                                          size=(700, 1000),
                                          title=title
                                          )
                popup.exec_()
                ignore = (popup.result == popup.CANCEL_PRESSED)

        elif dataLoader.dataFormat == DirectoryDataLoader.dataFormat:

            msg = None
            if dataLoader.count > MAXITEMLOADING or dataLoader.depth > MAXITEMDEPTH:
                _nSpectra = len([dl for dl in dataLoader.dataLoaders if dl.isSpectrumLoader and dl.isValid])
                _spectra = f', of which {_nSpectra} are spectra' if _nSpectra>0 else ''
                msg =  f'CAUTION: You are trying to load {dataLoader.count:d} items{_spectra}.\n'

                if dataLoader.depth > MAXITEMDEPTH:
                    msg += f'The folder is {dataLoader.depth}-subfolders deep.\n\n'

                msg += (f'It may take some time to load.\n\n'
                        f'Do you want to continue?')

            ignore = (bool(msg) and not MessageDialog.showYesNoWarning(f'Directory {dataLoader.path!r}\n', msg))

        dataLoader.createNewProject = createNewProject
        dataLoader.ignore = ignore
        return (dataLoader, createNewProject, ignore)

    #-----------------------------------------------------------------------------------------
    # Project and loading data related methods
    #-----------------------------------------------------------------------------------------

    @logCommand('application.')
    def newProject(self, name: str = 'default') -> Project | None:
        """Create a new project instance with name; create default project if name=None
        :return a Project instance or None
        """
        from ccpn.core.lib.ProjectLib import checkProjectName

        oldMainWindowPos = self.mainWindow.pos()
        if self.project and (self.project._undo is None or self.project._undo.isDirty()):
            # if not self.project.isTemporary:
            if self.project._undo is None or self.project._undo.isDirty():
                _CANCEL = 'Cancel'
                _OK = 'Discard and New'
                _SAVE = 'Save'
                msg = (f"The current project has been modified and requires saving. Do you want save the current "
                       f"project first, or discard the changes and continue creating a new project?")
                reply = MessageDialog.showMulti('New Project...', msg,
                                                texts=[_OK, _CANCEL, _SAVE],
                                                okText=_OK, cancelText=_CANCEL,
                                                parent=self.mainWindow)
                if reply == _CANCEL:
                    # cancel the new-operation
                    return
                elif reply == _SAVE:
                    # save first
                    if not self.saveProject():
                        # cancel the new-operation if there was an issue saving
                        return

        if (_name := checkProjectName(name, correctName=True)) != name:
            MessageDialog.showInfo('New Project',
                                   f'Project name changed from "{name}" to "{_name}"\nSee console/log for details',
                                   parent=self)

        with catchExceptions(errorStringTemplate='Error creating new project: %s'):
            if self.mainWindow:
                self.mainWindow.moduleArea._closeAll()
            newProject = self.application._newProject(name=_name)
            if newProject is None:
                raise RuntimeError('Unable to create new project')
            newProject._mainWindow.show()
            QtWidgets.QApplication.setActiveWindow(newProject._mainWindow)
            self.mainWindow.move(oldMainWindowPos)

            return newProject

    def _loadProject(self, dataLoader=None, path=None) -> Project | bool | None:
        """Helper function, loading project from dataLoader instance
        check and query for closing current project
        build the project Gui elements
        attempts to restore on failure to load a project

        :returns project instance or None
        """
        from ccpn.framework.lib.DataLoaders.DataLoaderABC import checkPathForDataLoader
        from ccpn.framework.lib.DataLoaders.CcpNmrV3ProjectDataLoader import CcpNmrV3ProjectDataLoader

        if dataLoader is None and path is not None:
            dataLoader = checkPathForDataLoader(path)
        if dataLoader is None:
            getLogger().error('No suitable dataLoader found')
            return None
        if not dataLoader.createNewProject:
            raise RuntimeError(f'DataLoader {dataLoader} does not create a new project')

        oldProjectLoader = None
        oldProjectIsTemporary = True
        oldMainWindowPos = self.mainWindow and self.mainWindow.pos()
        if self.project:
            # if not self.project.isTemporary:
            if self.project._undo is None or self.project._undo.isDirty():
                _CANCEL = 'Cancel'
                _OK = 'Discard and Load'
                _SAVE = 'Save'
                msg = (f"The current project has been modified and requires saving. Do you want save the current "
                       f"project first, or discard the changes and continue loading?")
                reply = MessageDialog.showMulti('Load Project...', msg,
                                                texts=[_OK, _CANCEL, _SAVE],
                                                okText=_OK, cancelText=_CANCEL,
                                                parent=self.mainWindow)
                if reply == _CANCEL:
                    # cancel the load-operation
                    return None
                elif reply == _SAVE:
                    # save first
                    if not self.saveProject():
                        # cancel the load-operation if there was an issue saving
                        return None

            # Some error recovery; store info to re-open the current project (or a new default)
            oldProjectLoader = CcpNmrV3ProjectDataLoader(self.project.path)
            oldProjectIsTemporary = self.project.isTemporary

        try:
            if self.project:
                # NOTE:ED - getting a strange QT bug disabling the menu-bar from here
                #  I think because the main-window isn't visible on the first load :|
                with busyHandler(self.mainWindow, title='Loading',
                                 text=f'Loading project {dataLoader.path} ...', closeDelay=1000):
                    _loaded = dataLoader.load()
            else:
                # busy-status not required on the first load
                _loaded = dataLoader.load()

            # NOTE:ED - another one here, if the message-dialog appears BEFORE the window-modal busy popup
            #   then the window containing the busy-popup takes control (but is still mouse-blocked)
            #   and the message-dialog doesn't close or doesn't pass modality back to the parent :|
            #   solution -  make sure busy popups are already visible,
            #               or show dialogs outside the busy context-manager
            if _loaded is None or len(_loaded) == 0:
                MessageDialog.showWarning('Loading Project',
                                          f'There was a problem loading project {dataLoader.path}\n'
                                          f'Please check the log for more information.',
                                          parent=self.mainWindow)
                return None

            newProject = _loaded[0]
            # # Note that the newProject has its own MainWindow; i.e. it is not self
            # newProject._mainWindow.sideBar.buildTree(newProject)
            # The next two lines are essential to have the QT main event loop associated
            # with the new window; without these, the programs just terminates
            newProject._mainWindow.show()
            QtWidgets.QApplication.setActiveWindow(newProject._mainWindow)

            # if the new project contains invalid spectra then open the popup to see them
            self.mainWindow._checkForBadSpectra(newProject)
            if oldMainWindowPos:
                self.mainWindow.move(oldMainWindowPos)

        except (RuntimeError, ValueError, ApiError) as es:
            MessageDialog.showError('Error loading Project:', f'{es}', parent=self.mainWindow)
            return None

        except NotImplementedError as es:
            MessageDialog.showError('Error loading Project:', f'{es}', parent=self.mainWindow)

            # Try to restore the state
            newProject = None
            if oldProjectIsTemporary:
                newProject = self.application._newProject()
            elif oldProjectLoader:
                newProject = oldProjectLoader.load()[0]  # dataLoaders return a list

            if newProject:
                # The next two lines are essential to have the QT main event loop associated
                # with the new window; without these, the programs just terminates
                newProject._mainWindow.show()
                QtWidgets.QApplication.setActiveWindow(newProject._mainWindow)

        return newProject

    # @logCommand('application.') # eventually decorated by  _loadData()
    def loadProject(self, path=None) -> Project | None:
        """Loads project defined by path
        :return a Project instance or None
        """
        if path is None:
            dialog = FileDialog.ProjectFileDialog(parent=self.mainWindow, acceptMode='open')
            dialog._show()

            if (path := dialog.selectedFile()) is None:
                return None

        with self.application.pauseAutoBackups():
            with catchExceptions(errorStringTemplate='Error loading project: %s'):
                dataLoader, createNewProject, ignore = self._getDataLoader(path)
                if ignore or dataLoader is None or not createNewProject:
                    return None

                # load the project using the dataLoader;
                # We'll ask framework who will pass it back to ui._loadProject
                if (objs := self.application._loadData([dataLoader])):
                    if len(objs) == 1:
                        return objs[0]

        return None

    def _closeProject(self):
        """Do all gui-related stuff when closing a project
        CCPNINTERNAL: called from Framework._closeProject()
        """
        if self.mainWindow:
            # ui/gui cleanup
            self.mainWindow.deleteAllNotifiers()
            self.mainWindow._closeMainWindowModules()
            self.mainWindow._closeExtraWindowModules()
            self.mainWindow._stopPythonConsole()
            self.mainWindow.sideBar.clearSideBar()
            self.mainWindow.sideBar.deleteLater()
            self.mainWindow.deleteLater()
            self.mainWindow = None

    @logCommand('application.')
    def saveProjectAs(self, newPath=None, overwrite: bool = False) -> bool:
        """Opens save Project to newPath.
        Optionally open file dialog.
        :param newPath: new path to save project (str | Path instance)
        :param overwrite: flag to indicate overwriting of existing path
        :return True if successful
        """
        from ccpn.core.lib.ProjectLib import checkProjectName

        oldPath = self.project.path
        if newPath is None:
            if (newPath := _getSaveDirectory(self.mainWindow)) is None:
                return False

        newPath = aPath(newPath).assureSuffix(CCPN_EXTENSION)
        title = 'Project SaveAs'

        if (not overwrite and
                newPath.exists() and
                (newPath.is_file() or (newPath.is_dir() and len(newPath.listdir(excludeDotFiles=False)) > 0))
        ):
            # should not really need to check the second and third condition above, only
            # the Qt dialog stupidly insists a directory exists before you can select it
            # so if it exists but is empty then don't bother asking the question
            msg = f'Path "{newPath}" already exists; overwrite?'
            if not MessageDialog.showYesNo(title, msg):
                return False

        # check the project name derived from path
        newName = newPath.basename
        if (_name := checkProjectName(newName, correctName=True)) != newName:
            newPath = (newPath.parent / _name).assureSuffix(CCPN_EXTENSION)
            MessageDialog.showInfo(title,
                                   f'Project name changed from "{newName}" to "{_name}"\nSee console/log for details',
                                   parent=self.mainWindow)

        with catchExceptions(errorStringTemplate='Error saving project: %s'):
            with MessageDialog.progressManager(self.mainWindow, f'Saving project as {newPath} ... '):
                try:
                    if not self.application._saveProjectAs(newPath=newPath, overwrite=True):
                        txt = f"Saving project to {newPath} aborted"
                        MessageDialog.showError("Project SaveAs", txt, parent=self.mainWindow)
                        return False

                except (PermissionError, FileNotFoundError):
                    msg = f'Folder {newPath} may be read-only'
                    MessageDialog.showWarning('Save project', msg)
                    return False

                except RuntimeWarning as es:
                    msg = f'Error saving {newPath}:\n{es}'
                    MessageDialog.showWarning('Save project', msg)
                    return False

        self.mainWindow._updateWindowTitle()
        self.application._getRecentProjectFiles()  # this will update the preferences-list
        self.mainWindow._fillRecentProjectsMenu()  # Update the menu

        successMessage = f'Project successfully saved to "{self.project.path}"'
        # MessageDialog.showInfo("Project SaveAs", successMessage, parent=self.mainWindow)
        self.mainWindow.statusBar().showMessage(successMessage)
        getLogger().info(successMessage)

        return True

    @logCommand('application.')
    def saveProject(self) -> bool:
        """Save project.
        :return True if successful
        """
        if self.project.isTemporary:
            return self.saveProjectAs()

        if self.project.readOnly and not MessageDialog.showYesNo(
                'Save Project',
                'The project is marked as read-only.\n'
                'This can be changed by clicking the lock-icon in the bottom-right.\n\n'
                'Do you want to continue saving?\n',
                ):
            return True

        with catchExceptions(errorStringTemplate='Error saving project: %s'):
            with MessageDialog.progressManager(self.mainWindow, 'Saving project ... '):
                try:
                    if not self.application._saveProject(force=True):
                        return False
                except (PermissionError, FileNotFoundError):
                    msg = 'Folder may be read-only'
                    MessageDialog.showWarning('Save project', msg)
                    return True

        successMessage = f'Project successfully saved to {self.project.path!r}'
        # MessageDialog.showInfo("Project Save", successMessage, parent=self.mainWindow) # This popup has been flagged as annoying by users
        self.mainWindow.statusBar().showMessage(successMessage)
        getLogger().info(successMessage)

        return True

    def _loadData(self, dataLoader) -> list:
        """Load the data defined by dataLoader instance, catching errors
        and suspending sidebar.
        :return a list of loaded opjects
        """
        from ccpn.framework.lib.DataLoaders.StarDataLoader import StarDataLoader
        from ccpn.framework.lib.DataLoaders.NefDataLoader import NefDataLoader

        result = []  # the load may fail
        errorStringTemplate = f'Loading "{dataLoader.path}" failed:\n\n%s'
        with catchExceptions(errorStringTemplate=errorStringTemplate):
            # For data loads that are possibly time-consuming, use progressManager
            if isinstance(dataLoader, (StarDataLoader, NefDataLoader)):
                with MessageDialog.progressManager(self.mainWindow, 'Importing data ... '):
                    result = dataLoader.load()
            else:
                result = dataLoader.load()
        return result

    # @logCommand('application.') # eventually decorated by  _loadData()
    def loadData(self, *paths, formatFilter: (list, tuple) = None) -> list:
        """Loads data from paths; query if none supplied
        Optionally filter for dataFormat(s)
        :param *paths: argument list of path's (str or Path instances)
        :param formatFilter: list/tuple of dataFormat strings
        :returns list of loaded objects
        """
        if not paths:
            dialog = FileDialog.DataFileDialog(parent=self.mainWindow, acceptMode='load')
            dialog._show()
            if (path := dialog.selectedFile()) is None:
                return []
            paths = [path]

        dataLoaders = []
        for path in paths:

            _path = aPath(path)
            if not _path.exists():
                txt = f'"{path}" does not exist'
                getLogger().warning(txt)
                MessageDialog.showError('Load Data', txt, parent=self)
                continue

            try:
                dataLoader, createNewProject, ignore = self._getDataLoader(path, formatFilter=formatFilter)

            except RuntimeError as es:
                MessageDialog.showError(f'Loading "{_path}"',
                                        f'{es}',
                                        parent=self.mainWindow)
                if len(paths) == 1:
                    return []
                else:
                    continue

            if ignore:
                continue

            dataLoaders.append(dataLoader)

        # load the project using the dataLoaders;
        # We'll ask framework who will pass it back as ui._loadData calls
        objs = self.application._loadData(dataLoaders)
        if len(objs) == 0:
            _pp = ','.join(f'"{p}"' for p in paths)
            txt = f'No objects were loaded from {_pp}'
            getLogger().warning(txt)
            MessageDialog.showError('Load Data', txt, parent=self.mainWindow)

        return objs

    def loadSpectra(self, *paths) -> list:
        """Load all the spectra found in paths.
        Query in case path is empty.

        :param paths: list of paths
        :return a list of Spectra instances
        """
        from ccpn.framework.lib.DataLoaders.DataLoaderABC import getSpectrumLoaders, checkPathForDataLoader
        from ccpn.framework.lib.DataLoaders.DirectoryDataLoader import DirectoryDataLoader

        if not paths:
            # This only works with non-native file dialog; override the default behavior
            dialog = FileDialog.SpectrumFileDialog(parent=self.mainWindow, acceptMode='load',
                                                   useNative=False)
            dialog._show()
            paths = dialog.selectedFiles()

        if not paths:
            return []

        formatFilter = list(getSpectrumLoaders().keys())

        spectrumLoaders = []
        count = 0
        # Recursively search all paths
        for path in paths:
            _path = aPath(path)
            if _path.is_dir():
                dirLoader = DirectoryDataLoader(path, recursive=False, formatFilter=formatFilter)
                spectrumLoaders.append(dirLoader)
                count += len(dirLoader)

            elif (sLoader := checkPathForDataLoader(path, formatFilter=formatFilter)) is not None:
                spectrumLoaders.append(sLoader)
                count += 1

        if count > MAXITEMLOGGING:
            okToOpenAll = MessageDialog.showYesNo('Load data', 'You selected %d items.'
                                                               ' Do you want to open all?' % count)
            if not okToOpenAll:
                return []

        with logCommandManager('application.', 'loadSpectra', *paths):
            result = self.application._loadData(spectrumLoaders)

        return result


#-----------------------------------------------------------------------------------------
# Helper code
#-----------------------------------------------------------------------------------------

def _getSaveDirectory(mainWindow):
    """Opens save Project as dialog box and gets directory specified in
    the file dialog.
    :return path instance or None
    """

    dialog = FileDialog.ProjectSaveFileDialog(parent=mainWindow, acceptMode='save')
    dialog._show()
    newPath = dialog.selectedFile()

    # if not iterable then ignore - dialog may return string or tuple(<path>, <fileOptions>)
    if isinstance(newPath, tuple) and len(newPath) > 0:
        newPath = newPath[0]

    # ignore if empty
    if not newPath:
        return None

    return newPath
