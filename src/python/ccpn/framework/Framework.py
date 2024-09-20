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
__dateModified__ = "$dateModified: 2024-09-16 15:51:34 +0100 (Mon, September 16, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================


import json
import os
import sys
import subprocess
import platform
import tempfile
import faulthandler
import contextlib
from datetime import datetime
import time

from ccpn.util.decorators import deprecated


try:
    # set the soft limits for the maximum number of open files
    if platform.system() == 'Windows':
        import win32file


        # set soft limit for Windows
        win32file._setmaxstdio(2048)

    else:
        import resource


        # soft limit imposed by the current configuration, hard limit imposed by the operating system.
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)

        # For the following line to run, you need to execute the Python script as root?
        resource.setrlimit(resource.RLIMIT_NOFILE, (2048, hard))

except Exception:
    sys.stderr.write('Error setting maximum number of files that can be open')

faulthandler.enable()

from typing import List

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from distutils.dir_util import copy_tree

from ccpn.core.IntegralList import IntegralList
from ccpn.core.PeakList import PeakList
from ccpn.core.MultipletList import MultipletList
from ccpn.core.Project import Project
from ccpn.core.lib.Notifiers import NotifierBase
from ccpn.core.lib.Pid import Pid
from ccpn.core.lib.ContextManagers import \
    logCommandManager, undoBlockWithSideBar, rebuildSidebar, inactivity

from ccpn.framework.Application import Arguments
from ccpn.framework import Version
from ccpn.framework.AutoBackup import AutoBackupHandler
from ccpn.framework.credits import printCreditsText
from ccpn.framework.Current import Current
from ccpn.framework.Translation import defaultLanguage
from ccpn.framework.Translation import translator
from ccpn.framework.Preferences import Preferences
from ccpn.framework.PathsAndUrls import \
    userCcpnMacroPath, \
    tipOfTheDayConfig, \
    ccpnCodePath, \
    CCPN_DIRECTORY_SUFFIX
from ccpn.framework.lib.resources.Resources import Resources
from ccpn.ui.gui.Gui import Gui
from ccpn.ui.gui.GuiBase import GuiBase
from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.modules.MacroEditor import MacroEditor
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.FileDialog import MacrosFileDialog
from ccpn.ui.gui.widgets.TipOfTheDay import TipOfTheDayWindow, MODE_KEY_CONCEPTS, loadTipsSetup
from ccpn.ui.gui.popups.RegisterPopup import RegisterPopup
from ccpn.ui.gui import Layout

from ccpn.util import Logging
from ccpn.util.Path import Path, aPath, fetchDir
from ccpn.util.AttrDict import AttrDict
from ccpn.util.Common import uniquify, isWindowsOS, isMacOS, isIterable, getProcess
from ccpn.util.Logging import getLogger
from ccpn.util.decorators import logCommand


logger = getLogger()

#-----------------------------------------------------------------------------------------
# how frequently to check if license dialog has closed when waiting to show the tip of the day
WAIT_EVENT_LOOP_EMPTY = 0
WAIT_LICENSE_DIALOG_CLOSE_TIME = 100

_DEBUG = False

interfaceNames = ('NoUi', 'Gui')
MAXITEMLOGGING = 4


# For @Ed: sys.excepthook PyQT related code now in Gui.py


#=========================================================================================
# Framework
#=========================================================================================

class Framework(NotifierBase, GuiBase):
    """
    The Framework class is the base class for all applications.
    """
    #-----------------------------------------------------------------------------------------
    # to be sub-classed
    applicationName = None
    applicationVersion = None

    _applicationReadOnlyMode = None

    #-----------------------------------------------------------------------------------------

    def __init__(self, args=Arguments()):

        NotifierBase.__init__(self)
        GuiBase.__init__(self)

        printCreditsText(sys.stderr, self.applicationName, self.applicationVersion)

        #-----------------------------------------------------------------------------------------
        # register the program for later with the getApplication() call
        #-----------------------------------------------------------------------------------------
        from ccpn.framework.Application import ApplicationContainer

        container = ApplicationContainer()
        container.register(self)

        #-----------------------------------------------------------------------------------------
        # Key attributes related to the data structure
        #-----------------------------------------------------------------------------------------
        # Necessary as attribute is queried during initialisation:
        self._mainWindow = None

        # This is needed to make project available in NoUi (if nothing else)
        self._project = None
        self._current = None

        self._plugins = []  # Hack for now, how should we store these?
        # used in GuiMainWindow by startPlugin()

        # set to True to override the read-only status of a project
        #   required to use save/saveAs but keep the project.readOnly status until the next load
        self._saveOverrideState = False

        #-----------------------------------------------------------------------------------------
        # Initialisations
        #-----------------------------------------------------------------------------------------

        self._created = datetime.now().strftime("%H%M")  # adds the app creation time to the end of the logger filename

        self.args = args

        # NOTE:ED - what is revision for? there are no uses and causes a new error for sphinx documentation unless a string
        # self.revision = Version.revision

        self.useFileLogger = not getattr(self.args, 'noLogging', False)

        # map to 0-3, with 0 no debug
        _level = ([self.args.debug,
                   self.args.debug2,
                   self.args.debug3 or self.args.debug3_backup_thread,
                   True].index(True) + 1) % 4
        self.setDebug(_level)

        # self.preferences = Preferences(application=self)
        # if not self.args.skipUserPreferences:
        #     sys.stderr.write('==> Getting user preferences\n')
        #     self.preferences._getUserPreferences()
        if self.args.skipUserPreferences:
            sys.stderr.write('==> Getting default preferences\n')
            self.preferences = Preferences(application=self, userPreferences=False)
        else:
            sys.stderr.write('==> Getting user preferences\n')
            self.preferences = Preferences(application=self)

        self.layout = None  # initialised by self._getUserLayout

        # GWV these attributes should move to the GUI class (in 3.2x ??)
        # For now, they are set in GuiBase and initialised by calls in Gui.__init_
        # self._styleSheet = None
        # self._colourScheme = None
        # self._fontSettings = None
        # self._menuSpec = None

        # Blocking level for command echo and logging
        self._echoBlocking = int(getattr(self.args, 'noDebugLogging', False))
        self._enableLoggingToConsole = True
        logger.disabled = getattr(self.args, 'noEchoLogging', False)  # overrides noDebugLogging

        # Process info
        self._process = getProcess()

        self._autoBackupThread = None

        self._tip_of_the_day = None
        self._initial_show_timer = None
        self._key_concepts = None

        self._registrationDict = {}

        self._setLanguage()

        self._experimentClassifications = None  # initialised in _startApplication once a project has loaded

        self._disableUndoException = getattr(self.args, 'disableUndoException', False)
        self._disableModuleException = getattr(self.args, 'disableModuleException', False)
        self._disableQueueException = getattr(self.args, 'disableQueueException', False)
        self._applicationReadOnlyMode = getattr(self.args, 'readOnly', False)
        self._ccpnLogging = getattr(self.args, 'ccpnLogging', False)

        # Create a temporary directory; Need to hold on to the original temp-file object, as otherwise
        # gets garbage collected. Access path name by using the "name" attribute.
        self._temporaryDirectory = tempfile.TemporaryDirectory(prefix='CcpNmr_')

        # register dataLoaders for the first and only time
        from ccpn.framework.lib.DataLoaders.DataLoaderABC import getDataLoaders

        self._dataLoaders = getDataLoaders()

        # register SpectrumDataSource formats for the first and only time
        from ccpn.core.lib.SpectrumDataSources.SpectrumDataSourceABC import getDataFormats

        self._spectrumDataSourceFormats = getDataFormats()

        # Resources
        self.resources = Resources(self)

        # get a user interface; nb. ui.start() is called by the application
        self.ui = self._getUI()

    #-----------------------------------------------------------------------------------------
    # properties of Framework
    #-----------------------------------------------------------------------------------------

    @property
    def project(self) -> Project:
        """:return currently active project
        """
        return self._project

    @property
    def current(self) -> Current:
        """Current contains selected peaks, selected restraints, cursor position, etc.
        see Current.py for detailed descriptiom
        :return the Current object
        """
        return self._current

    @property
    def mainWindow(self):
        """:returns: MainWindow instance if application has a Gui or None otherwise
        """
        if self.hasGui:
            return self.ui.mainWindow
        return None

    @property
    def hasGui(self) -> bool:
        """:return True if application has a gui"""
        return isinstance(self.ui, Gui)

    @property
    def _saveOverride(self):
        """Return the save-override state, this allows the saving of projects that are marked as read-only
        """
        return self._saveOverrideState

    @_saveOverride.setter
    def _saveOverride(self, value):
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}._saveOverride must be a bool')

        self._saveOverrideState = value
        if self.project:
            self.project._updateReadOnlyState()
            self.project._updateLoggerState()
            if self.mainWindow:
                self.mainWindow._setReadOnlyIcon()

    @property
    def isApplicationReadOnly(self):
        """Return the application readOnly state for all projects.
        Set from the command-line switch --read-only
        Overrides project.readOnly except for using save/saveAs as necessary
        """
        return self._applicationReadOnlyMode

    def setApplicationReadOnly(self, value):
        """Set the global application readOnly state.
        """
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}.setApplicationReadOnly must be a bool')
        if value == self._applicationReadOnlyMode:
            return
        self._applicationReadOnlyMode = value
        if self.project:
            self.project._updateReadOnlyState()
            self.project._updateLoggerState()
            if self.mainWindow:
                self.mainWindow._setReadOnlyIcon()

    #-----------------------------------------------------------------------------------------
    # Useful (?) directories as Path instances
    #-----------------------------------------------------------------------------------------

    @property
    def statePath(self) -> Path:
        """
        :return: the absolute path to the state subdirectory of the current project
                 as a Path instance
        """
        return self.project.statePath

    @property
    def pipelinePath(self) -> Path:
        """
        :return: the absolute path to the state/pipeline subdirectory of
                 the current project as a Path instance
        """
        return self.project.pipelinePath

    @property
    def dataPath(self) -> Path:
        """
        :return: the absolute path to the data sub-directory of the current project
                 as a Path instance
        """
        return self.project.dataPath

    @property
    def spectraPath(self):
        """
        :return: the absolute path to the data sub-directory of the current project
                 as a Path instance
        """
        return self.project.spectraPath

    @property
    def pluginDataPath(self) -> Path:
        """
        :return: the absolute path to the data/plugins sub-directory of the
                 current project as a Path instance
        """
        return self.project.pluginDataPath

    @property
    def scriptsPath(self) -> Path:
        """
        :return: the absolute path to the script sub-directory of the current project
                 as a Path instance
        """
        return self.project.scriptsPath

    @property
    def archivesPath(self) -> Path:
        """
        :return: the absolute path to the archives sub-directory of the current project
                 as a Path instance
        """
        return self.project.archivesPath

    @property
    def tempMacrosPath(self) -> Path:
        """
        :return: the absolute path to the ~/.ccpn/macros directory
                 as a Path instance
        """
        return userCcpnMacroPath

    #-----------------------------------------------------------------------------------------
    # "get" methods
    #-----------------------------------------------------------------------------------------

    def get(self, identifier):
        """General method to obtain object (either gui or data) from identifier (pid, gid,
        obj-string)
        :param identifier: a Pid, Gid or string object identifier
        :return a Version-3 core data or graphics object
        """
        if identifier is None:
            raise ValueError('Expected str or Pid, got "None"')

        if not isinstance(identifier, (str, Pid)):
            raise ValueError('Expected str or Pid, got "%s" %s' % (identifier, type(identifier)))
        identifier = str(identifier)

        if len(identifier) == 0:
            raise ValueError('Expected str or Pid, got zero-length identifier')

        if len(identifier) >= 2 and identifier[0] == '<' and identifier[-1] == '>':
            identifier = identifier[1:-1]

        return self.project.getByPid(identifier)

    def getByPid(self, pid):
        """Legacy; obtain data object from identifier (pid or obj-string)
        replaced by get(identifier).
        :param pid: a Pid or string object identifier
        :return a Version-3 core data object
        """
        return self.get(pid)

    def getByGid(self, gid):
        """Legacy; obtain graphics object from identifier (gid or obj-string)
        replaced by get(identifier).
        :param gid: a Gid or string object identifier
        :return a Version-3 graphics object
        """
        return self.get(gid)

    #-----------------------------------------------------------------------------------------
    # Initialisations and cleanup
    #-----------------------------------------------------------------------------------------

    def _getUI(self):
        """Get the user interface
        :return a Ui instance
        """
        if self.args.interface == 'Gui':
            from ccpn.ui.gui.Gui import Gui

            ui = Gui(application=self)

        else:
            from ccpn.ui.Ui import NoUi

            ui = NoUi(application=self)

        return ui

    def _startApplication(self):
        """Start the program execution
        """

        # NOTE:ED - there are currently issues when loading projects from the command line, or from test cases
        #   There is no project.application and project is None
        #   The Logger instantiated is the default logger, required adding extra methods so that, e.g., echoInfo worked
        #   logCommand has no self.project.application, and requires getApplication() instead
        #   There is NoUi instantiated yet, so temporarily added loadProject to Ui class called by loadProject below)

        # Load / create project on start; this also initiates the ui/gui (unfortunately), so it meed to
        # be here before any other things can happen
        if (projectPath := self.args.projectPath) is not None:
            project = self.loadProject(projectPath)
        else:
            project = self._newProject()

        # Needed in case project load failed
        if not project:
            sys.stderr.write('==> No project, aborting ...\n')
            return

        if self.preferences.general.checkUpdatesAtStartup and not getattr(self.args, '_skipUpdates', False):
            self.ui._checkForUpdates()

        if not self.ui._checkRegistration():
            return

        self._experimentClassifications = project._getExperimentClassifications()
        self._updateAutoBackup()

        sys.stderr.write('==> Done, %s is starting\n' % self.applicationName)
        self.ui.startUi()
        # self._cleanup()

    def _cleanup(self):
        """Cleanup at the end of program execution; i.e. once the command loop
        has stopped
        """
        self._updateAutoBackup(kill=True)

    #-----------------------------------------------------------------------------------------
    # Backup (TODO: need refactoring in AutoBackupManager)
    #-----------------------------------------------------------------------------------------

    def _updateAutoBackup(self, disable=False, kill=False):
        # CCPNINTERNAL: also called from preferences popup
        # raise NotImplementedError('AutoBackup is not available in the current release')
        if not self.hasGui:
            # not required if not in an interactive mode
            return

        if self._autoBackupThread is None:
            self._setBackupModifiedTime()
            self._setLastBackupTime()
            self._autoBackupThread = AutoBackupHandler(eventFunction=self._backupProject,
                                                       eventInterval=self.preferences.general.autoBackupFrequency * 60
                                                       )
        if disable:
            # stores the remaining time
            self._autoBackupThread.stop()

        elif kill or not self.preferences.general.autoBackupEnabled:
            # ensures that the timer starts again
            self._autoBackupThread.kill()

        else:
            # start the thread - preferences is minutes
            self._autoBackupThread.setInterval(self.preferences.general.autoBackupFrequency * 60)
            self._autoBackupThread.start()

    @contextlib.contextmanager
    def pauseAutoBackups(self, delay=False):
        """Temporarily pause backups for loading/saving
        """
        if not self.hasGui:
            # not required if not in an interactive mode
            yield
            return

        try:
            if delay:
                # keep remaining interval for restart
                self._updateAutoBackup(disable=True)
            else:
                self._updateAutoBackup(kill=True)

            yield

        finally:
            self._updateAutoBackup()

    def _getBackupModifiedTime(self):
        return self._backupModifiedTime

    def _setBackupModifiedTime(self):
        """Set the last time that a core-object was modified.
        """
        self._backupModifiedTime = time.perf_counter()

    def _getLastBackupTime(self):
        return self._lastBackupTime

    def _setLastBackupTime(self):
        """Set the last time that a backup was performed.
        """
        self._lastBackupTime = time.perf_counter()

    def _backupProject(self):
        try:
            if self.project.readOnly:
                # skip if the project is read-only
                getLogger().debug('Backup skipped: Project is read-only')
                return
            if (self._getBackupModifiedTime() < self._getLastBackupTime()):
                # ignore if there were no modifications since the last backup, even if project is modified
                getLogger().debug('Backup skipped: Not modified since last backup')
                return

            if self.project._backup():
                # log the time that a backup was completed
                self._setLastBackupTime()

        except (PermissionError, FileNotFoundError):
            getLogger().info('Backup failed: Folder may be read-only')
        except Exception as es:
            getLogger().warning(f'Project backup failed with error {es}')

    #-----------------------------------------------------------------------------------------

    def _initialiseProject(self, newProject: Project):
        """Initialise a project and set up links and objects that involve it
        """

        # # Linkages; need to be here as downstream code depends on it
        self._project = newProject
        newProject._application = self

        newProject._resetUndo(debug=self._debugLevel <= Logging.DEBUG2,
                              application=self)

        # Logging
        logger = getLogger()
        Logging.setLevel(logger, self._debugLevel)
        logger.debug('Framework._initialiseProject>>>')

        # Set up current; we need it when restoring project graphics data below
        self._current = Current(project=newProject)

        # This wraps the underlying data, including the wrapped graphics data
        newProject._initialiseProject()

        # GWV: this really should not be here; moved to the_update_v2 method
        #      that already existed and gets called
        # if newProject._isUpgradedFromV2:
        #     getLogger().debug('initialising v2 noise and contour levels')
        #     with inactivity(application=self):
        #         for spectrum in newProject.spectra:
        #             # calculate the new noise level
        #             spectrum.noiseLevel = spectrum.estimateNoise()
        #
        #             # Check  contourLevels, contourColours
        #             spectrum._setDefaultContourValues()
        #
        #             # set the initial contour colours
        #             (spectrum.positiveContourColour, spectrum.negativeContourColour) = getDefaultSpectrumColours(spectrum)
        #             spectrum.sliceColour = spectrum.positiveContourColour
        #
        #             # set the initial axis ordering
        #             _getDefaultOrdering(spectrum)

        # the project is now ready to use

        # Now that all objects, including the graphics are there, restore current
        self.current._restoreStateFromFile(self.statePath)
        # Load project specific resources.
        self.resources._initProjectResources()

        if self.hasGui:
            self.ui.initialize(self._mainWindow)
            # Get the mainWindow out of the application top level once it's been transferred to ui
            del self._mainWindow
        else:
            # The NoUi version has no mainWindow
            self.ui.initialize(None)

        self._setLastBackupTime()
        newProject._setUnmodified()

    #-----------------------------------------------------------------------------------------
    # Utilities
    #-----------------------------------------------------------------------------------------

    def setDebug(self, level: int):
        """Set the debugging level
        :param level: 0: off, 1-3: debug level 1-3
        """
        if level == 3:
            self._debugLevel = Logging.DEBUG3
        elif level == 2:
            self._debugLevel = Logging.DEBUG2
        elif level == 1:
            self._debugLevel = Logging.DEBUG
        elif level == 0:
            self._debugLevel = Logging.INFO
        else:
            raise ValueError(f'Invalid debug level ({level}); should be 0-3')

    @property
    def _isInDebugMode(self) -> bool:
        """:return True if either of the debug flags has been set
        CCPNINTERNAL: used throughout to check
        """
        if self._debugLevel == Logging.DEBUG1 or \
                self._debugLevel == Logging.DEBUG2 or \
                self._debugLevel == Logging.DEBUG3:
            return True
        return False

    def _savePreferences(self):
        """Save the user preferences to file
        CCPNINTERNAL: used in PreferencesPopup and GuiMainWindow._close()
        """
        self.preferences._saveUserPreferences()

    def _setLanguage(self):
        # Language, check for command line override, or use preferences
        if self.args.language:
            language = self.args.language
        elif self.preferences.general.language:
            language = self.preferences.general.language
        else:
            language = defaultLanguage
        if not translator.setLanguage(language):
            self.preferences.general.language = language
        # translator.setDebug(True)
        sys.stderr.write('==> Language set to "%s"\n' % translator._language)

    @staticmethod
    def _cleanGarbageCollector():
        """ Force the garbageCollector to clean. See more at
        https://docs.python.org/3/library/gc.html"""
        import gc

        gc.collect()

    #-----------------------------------------------------------------------------------------

    def _correctColours(self):
        """Autocorrect all colours that are too close to the background colour
        """
        from ccpn.ui.gui.guiSettings import autoCorrectHexColour, getColours, CCPNGLWIDGET_HEXBACKGROUND

        if self.preferences.general.autoCorrectColours:
            project = self.project
            # change sp colours
            for sp in project.spectra:
                if len(sp.axisCodes) > 1:
                    if sp.positiveContourColour and sp.positiveContourColour.startswith('#'):
                        sp.positiveContourColour = autoCorrectHexColour(sp.positiveContourColour,
                                                                        getColours()[CCPNGLWIDGET_HEXBACKGROUND])
                    if sp.negativeContourColour and sp.negativeContourColour.startswith('#'):
                        sp.negativeContourColour = autoCorrectHexColour(sp.negativeContourColour,
                                                                        getColours()[CCPNGLWIDGET_HEXBACKGROUND])
                elif sp.sliceColour and sp.sliceColour.startswith('#'):
                    sp.sliceColour = autoCorrectHexColour(sp.sliceColour,
                                                          getColours()[CCPNGLWIDGET_HEXBACKGROUND])
            # change peakList colours
            for objList in project.peakLists:
                objList.textColour = autoCorrectHexColour(objList.textColour,
                                                          getColours()[CCPNGLWIDGET_HEXBACKGROUND])
                objList.symbolColour = autoCorrectHexColour(objList.symbolColour,
                                                            getColours()[CCPNGLWIDGET_HEXBACKGROUND])
            # change integralList colours
            for objList in project.integralLists:
                objList.textColour = autoCorrectHexColour(objList.textColour,
                                                          getColours()[CCPNGLWIDGET_HEXBACKGROUND])
                objList.symbolColour = autoCorrectHexColour(objList.symbolColour,
                                                            getColours()[CCPNGLWIDGET_HEXBACKGROUND])
            # change multipletList colours
            for objList in project.multipletLists:
                objList.textColour = autoCorrectHexColour(objList.textColour,
                                                          getColours()[CCPNGLWIDGET_HEXBACKGROUND])
                objList.symbolColour = autoCorrectHexColour(objList.symbolColour,
                                                            getColours()[CCPNGLWIDGET_HEXBACKGROUND])
            for mark in project.marks:
                mark.colour = autoCorrectHexColour(mark.colour,
                                                   getColours()[CCPNGLWIDGET_HEXBACKGROUND])

    def _initGraphics(self):
        """Set up graphics system after loading
        """
        from ccpn.ui.gui.lib import GuiStrip

        project = self.project
        mainWindow = self.ui.mainWindow

        # 20191113:ED Initial insertion of spectrumDisplays into the moduleArea
        try:
            insertPoint = mainWindow.moduleArea
            for spectrumDisplay in mainWindow.spectrumDisplays:
                mainWindow.moduleArea.addModule(spectrumDisplay,
                                                position='right',
                                                relativeTo=insertPoint)
                insertPoint = spectrumDisplay

        except Exception:
            getLogger().warning('Impossible to restore SpectrumDisplays')

        try:
            if self.preferences.general.restoreLayoutOnOpening and \
                    mainWindow.moduleLayouts:
                Layout.restoreLayout(mainWindow, mainWindow.moduleLayouts, restoreSpectrumDisplay=False)
        except Exception as e:
            getLogger().warning(f'Impossible to restore Layout {e}')

        # New LayoutManager implementation; awaiting completion
        # try:
        #     from ccpn.framework.LayoutManager import LayoutManager
        #     layout = LayoutManager(mainWindow)
        #     path = self.statePath / 'Layout.json'
        #     layout.restoreState(path)
        #     layout.saveState()
        #
        # except Exception as es:
        #     getLogger().warning('Error restoring layout: %s' % es)

        # check that the top moduleArea is correctly formed - strange special case when all modules have
        #   been moved to tempAreas
        mArea = self.ui.mainWindow.moduleArea
        if mArea.topContainer is not None and mArea.topContainer._container is None:
            getLogger().debug('Correcting empty topContainer')
            mArea.topContainer = None

        try:
            # Initialise colours
            # # for spectrumDisplay in project.windows[0].spectrumDisplays:  # there is exactly one window
            #
            # for spectrumDisplay in mainWindow.spectrumDisplays:  # there is exactly one window
            #     pass  # GWV: poor solution; removed the routine spectrumDisplay._resetRemoveStripAction()

            # initialise any colour changes before generating gui strips
            self._correctColours()
        except Exception as es:
            getLogger().warning(f'Impossible to restore colours - {es}')

        # Initialise Strips
        for spectrumDisplay in mainWindow.spectrumDisplays:
            try:
                for si, strip in enumerate(spectrumDisplay.orderedStrips):

                    # temporary to catch bad strips from ordering bug
                    if not strip:
                        continue

                    # get the new tilePosition of the strip - tilePosition is always (x, y) relative to screen stripArrangement
                    #                                       changing screen arrangement does NOT require flipping tilePositions
                    #                                       i.e. Y = (across, down); X = (down, across)
                    #                                       - check delete/undo/redo strips
                    tilePosition = strip.tilePosition

                    # move to the correct place in the widget - check stripDirection to display as row or column
                    if spectrumDisplay.stripArrangement == 'Y':
                        if True:  # tilePosition is None:
                            spectrumDisplay.stripFrame.layout().addWidget(strip, 0, si)  #stripIndex)
                            strip.tilePosition = (0, si)
                        # else:
                        #     spectrumDisplay.stripFrame.layout().addWidget(strip, tilePosition[0], tilePosition[1])

                    elif spectrumDisplay.stripArrangement == 'X':
                        if True:  #tilePosition is None:
                            spectrumDisplay.stripFrame.layout().addWidget(strip, si, 0)  #stripIndex)
                            strip.tilePosition = (0, si)
                        # else:
                        #     spectrumDisplay.stripFrame.layout().addWidget(strip, tilePosition[1], tilePosition[0])

                    elif spectrumDisplay.stripArrangement == 'T':
                        # NOTE:ED - Tiled plots not fully implemented yet
                        getLogger().warning(f'Tiled plots not implemented for spectrumDisplay: {str(spectrumDisplay)}')
                    else:
                        getLogger().warning(
                                f'Strip direction is not defined for spectrumDisplay: {str(spectrumDisplay)}')

                    if not spectrumDisplay.is1D:
                        for _strip in spectrumDisplay.strips:
                            _strip._updatePlaneAxes()

                if spectrumDisplay.isGrouped:
                    # set up the spectrumGroup toolbar

                    spectrumDisplay.spectrumToolBar.hide()
                    spectrumDisplay.spectrumGroupToolBar.show()

                    _spectrumGroups = [project.getByPid(pid) for pid in spectrumDisplay._getSpectrumGroups()]

                    for group in _spectrumGroups:
                        spectrumDisplay.spectrumGroupToolBar._forceAddAction(group)

                else:
                    # set up the spectrum toolbar

                    spectrumDisplay.spectrumToolBar.show()
                    spectrumDisplay.spectrumGroupToolBar.hide()
                    spectrumDisplay.setToolbarButtons()

                # some strips may not be instantiated at this point
                # resize the stripFrame to the spectrumDisplay - ready for first resize event
                # spectrumDisplay.stripFrame.resize(spectrumDisplay.width() - 2, spectrumDisplay.stripFrame.height())
                spectrumDisplay.showAxes(stretchValue=True, widths=True,
                                         minimumWidth=GuiStrip.STRIP_MINIMUMWIDTH)

            except Exception as e:
                getLogger().warning(f'Impossible to restore spectrumDisplay(s) {e}')

        try:
            if self.current.strip is None and len(mainWindow.strips) > 0:
                self.current.strip = mainWindow.strips[0]
        except Exception as e:
            getLogger().warning(f'Error restoring current.strip: {e}')

        # GST slightly complicated as we have to wait for any license or other
        # startup dialogs to close before we display tip of the day
        loadTipsSetup(tipOfTheDayConfig, [ccpnCodePath])
        self._tip_of_the_day_wait_dialogs = (RegisterPopup,)
        self._startupShowTipofTheDay()

    #-----------------------------------------------------------------------------------------

    def _startupShowTipofTheDay(self):
        if self._shouldDisplayTipOfTheDay():
            self._initial_show_timer = QTimer(parent=self._mainWindow)
            self._initial_show_timer.timeout.connect(self._startupDisplayTipOfTheDayCallback)
            self._initial_show_timer.setInterval(0)
            self._initial_show_timer.start()

    def _canTipOfTheDayShow(self):
        result = True
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, self._tip_of_the_day_wait_dialogs) and widget.isVisible():
                result = False
                break
        return result

    def _startupDisplayTipOfTheDayCallback(self):

        is_first_time_tip_of_the_day = self.preferences['general'].setdefault('firstTimeShowKeyConcepts', True)

        # GST this waits till any inhibiting dialogs aren't show and then awaits till the event loop is empty
        # effectively it swaps between waiting for WAIT_LICENSE_DIALOG_CLOSE_TIME or until the event loop is empty
        if not self._canTipOfTheDayShow() or self._initial_show_timer.interval() == WAIT_LICENSE_DIALOG_CLOSE_TIME:
            if self._initial_show_timer.interval() == WAIT_EVENT_LOOP_EMPTY:
                self._initial_show_timer.setInterval(WAIT_LICENSE_DIALOG_CLOSE_TIME)
            else:
                self._initial_show_timer.setInterval(WAIT_EVENT_LOOP_EMPTY)

            self._initial_show_timer.start()
        else:
            # this should only happen when the event loop is empty...
            if is_first_time_tip_of_the_day:
                self._displayKeyConcepts()
                self.preferences['general']['firstTimeShowKeyConcepts'] = False
            else:
                try:
                    self._displayTipOfTheDay()
                except Exception as e:
                    self._initial_show_timer.stop()
                    self._initial_show_timer.deleteLater()
                    self._initial_show_timer = None
                    raise e

            if self._initial_show_timer:
                self._initial_show_timer.stop()
                self._initial_show_timer.deleteLater()
                self._initial_show_timer = None

    def _displayKeyConcepts(self):
        if not self._key_concepts:
            self._key_concepts = TipOfTheDayWindow(mode=MODE_KEY_CONCEPTS)
        self._key_concepts.show()
        self._key_concepts.raise_()

    def _displayTipOfTheDay(self, standalone=False):

        # tip of the day allocated standalone already
        if self._tip_of_the_day and standalone and self._tip_of_the_day.isStandalone():
            self._tip_of_the_day.show()
            self._tip_of_the_day.raise_()

        # tip of the day hanging around from startup
        elif self._tip_of_the_day and standalone and not self._tip_of_the_day.isStandalone():

            self._tip_of_the_day.hide()
            self._tip_of_the_day.deleteLater()
            self._tip_of_the_day = None

        if not self._tip_of_the_day:
            dont_show_tips = not self.preferences['general']['showTipOfTheDay']

            seen_tip_list = []
            # if not standalone:
            seen_tip_list = self.preferences['general']['seenTipsOfTheDay']

            self._tip_of_the_day = TipOfTheDayWindow(dont_show_tips=dont_show_tips,
                                                     seen_perma_ids=seen_tip_list, standalone=standalone)
            self._tip_of_the_day.dont_show.connect(self._tip_of_the_day_dont_show_callback)
            # if not standalone:
            self._tip_of_the_day.seen_tips.connect(self._tip_of_the_day_seen_tips_callback)

            self._tip_of_the_day.show()
            self._tip_of_the_day.raise_()

    def _tip_of_the_day_dont_show_callback(self, dont_show):
        self.preferences['general']['showTipOfTheDay'] = not dont_show

    def _tip_of_the_day_seen_tips_callback(self, seen_tips):
        seen_tip_list = self.preferences['general']['seenTipsOfTheDay']
        previous_seen_tips = set(seen_tip_list)
        previous_seen_tips.update(seen_tips)
        seen_tip_list.clear()
        seen_tip_list.extend(previous_seen_tips)

    def _shouldDisplayTipOfTheDay(self):
        return self.preferences['general'].setdefault('showTipOfTheDay', True)

    #-----------------------------------------------------------------------------------------
    # Project related methods
    #-----------------------------------------------------------------------------------------

    def _getTemporaryPath(self, prefix, suffix=None) -> Path:
        """Return a temporary path in _temporaryDirectory with prefix and optional suffix.
        Use tempfile.NamedTemporyFile, but closing and deleting the file
        instantly, while returning the generated path name as a Path instance.
        :param prefix: prefix appended to the name
        :param suffix: suffix of the name
        """
        dir = self._temporaryDirectory.name
        with tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, dir=dir) as tFile:
            path = tFile.name
        return Path(path)

    def _cleanTemporaryDirectory(self):
        """Remove all files in the temporary path.
        the cleanup() method of the _temporaryDirectory instance seems not to do the job
        """
        for _path in [Path(p) for p in Path(self._temporaryDirectory.name).glob('*')]:
            try:
                # causes crash in Windows with temporary folder
                if _path.is_dir():
                    _path.removeDir()
                else:
                    _path.removeFile()
            except (PermissionError, FileNotFoundError):
                getLogger().debug('Folder may be read-only')

    def _newProject(self, name: str = 'default') -> Project:
        """Create new, empty project with name
        All new projects are created as temporary, to be saved later at another location
        :return a Project instance
        """
        # local import to avoid cycles
        from ccpn.core.Project import _newProject
        from ccpn.core.lib.ProjectLib import checkProjectName

        if name is None:
            raise ValueError('Undefined name for new project')
        if checkProjectName(name, correctName=False) is None:
            raise ValueError(f'Invalid project name "{name}"; check log/console for details')

        # Get a path in the temporary directory
        path = self._getTemporaryPath(prefix=f'{name}_', suffix=CCPN_DIRECTORY_SUFFIX)

        # NB _closeProject includes a gui cleanup call
        self._closeProject()
        result = _newProject(self, name=name, path=path, isTemporary=True)
        self._initialiseProject(result)  # This also set the linkages

        getLogger().debug(f'Opened project "{name}" at {result.path}')

        # update the logger read-only state
        self.project._updateReadOnlyState()
        self.project._updateLoggerState(readOnly=False, flush=True)
        if self.mainWindow:
            self.mainWindow._setReadOnlyIcon()

        return result

    # @logCommand('application.')  # decorated in ui class
    def newProject(self, name: str = 'default') -> Project:
        """Create new, empty project with name
        :return a Project instance
        """
        result = self.ui.newProject(name)
        getLogger().debug('--> NEW PROJECT')
        return result

    # @logCommand('application.') # eventually decorated by  _loadData()
    def loadProject(self, path=None) -> Project:
        """Load project defined by path
        :return a Project instance
        """
        result = self.ui.loadProject(path)
        getLogger().debug('--> LOADED PROJECT')

        return result

    def _saveProjectAs(self, newPath=None, overwrite=False) -> bool:
        """Save project to newPath (optionally overwrite)
        :return True if successful
        """
        if self.preferences.general.keepSpectraInsideProject:
            self.project.copySpectraToProject()

        with self._setSaveOverride(True):
            try:
                self.project.saveAs(newPath=newPath, overwrite=overwrite)
                Layout.saveLayoutToJson(self.ui.mainWindow)
                self.current._dumpStateToFile(self.statePath)
                self._getUndo().markSave()

            except (PermissionError, FileNotFoundError):
                failMessage = f'Folder {newPath} may be read-only'
                getLogger().warning(failMessage)
                raise

            except RuntimeWarning as es:
                failMessage = f'saveAs: unable to save {es}'
                getLogger().warning(failMessage)
                raise

            except Exception as es:
                failMessage = f'saveAs: unable to save {es}'
                getLogger().warning(failMessage)
                return False

        return True

    @contextlib.contextmanager
    def _setSaveOverride(self, state):
        """Temporarily set the save-override state for save/saveAs
        """
        lastState = self._saveOverride
        self._saveOverride = state
        try:
            yield

        finally:
            self._saveOverride = lastState

    def _saveProject(self, force=False) -> bool:
        """Save project to newPath and return True if successful
        """
        # ensure override flag is clean
        self._saveOverride = False

        with self._setSaveOverride(force):
            if self.project.readOnly:
                getLogger().warning('Project is read-only')
                return True

            if self.preferences.general.keepSpectraInsideProject:
                self.project.copySpectraToProject()

            try:
                self.project.save()
                Layout.saveLayoutToJson(self.ui.mainWindow)
                self.current._dumpStateToFile(self.statePath)
                self._getUndo().markSave()

            except (PermissionError, FileNotFoundError):
                failMessage = 'Folder may be read-only'
                getLogger().info(failMessage)
                raise

            except Exception as es:
                failMessage = f'save: unable to save {es}'
                getLogger().warning(failMessage)
                return False

        return True

    # @logCommand('application.')  # decorated in ui
    def saveProjectAs(self, newPath, overwrite: bool = False) -> bool:
        """Save project to newPath
        :param newPath: new path to save project (str | Path instance)
        :param overwrite: flag to indicate overwriting of existing path
        :return True if successful
        """
        return self.ui.saveProjectAs(newPath=newPath, overwrite=overwrite)

    # @logCommand('application.')  # decorated in ui
    def saveProject(self) -> bool:
        """Save project.
        :return True if successful
        """
        return self.ui.saveProject()

    def _closeProject(self):
        """Close project and clean up - when opening another or quitting application.
        Leaves the state of the whole programme as "transient", as there is no active project.
        Hence, need to be followed by initialising a new project or termination of the programme.
        """
        # NB: this function must clean up both wrapper and ui/gui

        self.deleteAllNotifiers()
        self.ui._closeProject()

        if self.current:
            self.current._unregisterNotifiers()
            self._current = None

        if self.project is not None:
            # Cleans up wrapper project, including graphics data objects (Window, Strip, etc.)
            _project = self.project
            _project._close()
            self._project = None
            del (_project)

        self.resources._deregisterProjectResources()
        # self._cleanTemporaryDirectory()
        self._cleanGarbageCollector()

    #-----------------------------------------------------------------------------------------
    # Data loaders
    #-----------------------------------------------------------------------------------------

    def _loadData(self, dataLoaders, maxItemLogging=MAXITEMLOGGING) -> list:
        """Helper function;
        calls ui._loadData or ui._loadProject for each dataLoader to load data;
        optionally suspend command logging

        :param dataLoaders: a list/tuple of dataLoader instances
        :param maxItemLogging: flag to set maximum items to log (0 denotes logging all)
        :return a list of loaded objects
        """
        objs = []
        _echoBlocking = (0 < maxItemLogging < len(dataLoaders))

        if _echoBlocking:
            getLogger().info('Loading %d objects, while suppressing command-logging' %
                             len(dataLoaders))
            self._increaseNotificationBlocking()

        # Check if there is a dataLoader that creates a new project: in that case, we only want one
        _createNew = [dl for dl in dataLoaders if dl.createNewProject]
        if len(_createNew) > 1:
            raise RuntimeError('Multiple dataLoaders create a new project; can\'t do that')

        elif len(_createNew) == 1:
            dataLoader = _createNew[0]

            with self.pauseAutoBackups():
                with logCommandManager('application.', 'loadProject', dataLoader.path):

                    # NOTE:ED - move inside ui._loadProject?
                    if self.project:
                        if self.project.readOnly and dataLoader.makeArchive:
                            MessageDialog.showWarning('Archive Project', 'Project is read-only',
                                                      parent=self.ui.mainWindow
                                                      )

                        elif dataLoader.makeArchive:
                            # make an archive in the project specific archive folder before loading
                            from ccpn.core.lib.ProjectArchiver import ProjectArchiver

                            archiver = ProjectArchiver(projectPath=dataLoader.path)
                            if archivePath := archiver.makeArchive():
                                getLogger().info(f'==> Project archived to {archivePath}')
                            else:
                                MessageDialog.showWarning('Archive Project',
                                                          f'There was a problem creating an archive for {dataLoader.path}',
                                                          parent=self.ui.mainWindow
                                                          )

                    if not (result := self.ui._loadProject(dataLoader=dataLoader)):
                        if self.project:
                            # may be run from the command-line, so no project yet
                            # update the logger read-only state
                            self.project._updateReadOnlyState()
                            self.project._updateLoggerState(flush=not self.project.readOnly)
                            if self.mainWindow:
                                self.mainWindow._setReadOnlyIcon()
                        return []

                    self._setLastBackupTime()
                    result._setUnmodified()
                    getLogger().info(f"==> Loaded project {result}")
                    if not isIterable(result):
                        result = [result]
                    objs.extend(result)
                dataLoaders.remove(dataLoader)

        with self.pauseAutoBackups(delay=True):
            # Now do the remaining ones; put in one undo block
            with undoBlockWithSideBar():
                for dataLoader in dataLoaders:
                    with logCommandManager('application.', 'loadData', dataLoader.path):
                        result = self.ui._loadData(dataLoader=dataLoader)
                    if not isIterable(result):
                        result = [result]
                    objs.extend(result)

        if _echoBlocking:
            self._decreaseNotificationBlocking()

        getLogger().debug(f'Loaded objects: {objs}')

        # update the logger read-only state
        self.project._updateReadOnlyState()
        self.project._updateLoggerState(flush=not self.project.readOnly)
        if self.mainWindow:
            self.mainWindow._setReadOnlyIcon()

        return objs

    # @logCommand('application.') # eventually decorated by  _loadData()
    def loadData(self, *paths, formatFilter=None) -> list:
        """Loads data from paths.
        Optionally filter for dataFormat(s)
        :param *paths: argument list of path's (str or Path instances)
        :param formatFilter: keyword argument: list/tuple of dataFormat strings
        :returns list of loaded objects
        """
        return self.ui.loadData(*paths)

    # @logCommand('application.') # decorated by  ui
    def loadSpectra(self, *paths) -> list:
        """Load all the spectra found in paths.

        :param paths: list of paths
        :return a list of Spectra instances
        """
        return self.ui.loadSpectra(*paths)

    @staticmethod
    def _finaliseV2Upgrade(project):
        """Final step of upgrading from v2 to v3 projects.
        """
        # Copy all the internal validationStores to v3-dataTables
        import pandas as pd
        from collections import OrderedDict
        from xml.sax.saxutils import escape

        getLogger().debug(f'Finalise upgrade v2-v3')
        fields = ['_ID', 'className', 'createdBy', 'guid', 'name',
                  'packageName', 'packageShortName',
                  'qualifiedName', 'structureEnsemble']
        columns = ['serial', 'context', 'keyword', 'keywordDefinition',
                   'figOfMerit', 'textValue', 'intValue', 'floatValue',
                   'booleanValue', 'details']
        wrp = project._wrappedData
        vStores = list(wrp.validationStores)
        for vs in vStores:
            out = []
            for vr in vs.validationResults:
                out.append([str(val) if not hasattr(val, '_ID') else val.name
                            for col in columns
                            for val in [getattr(vr, col, '')]])
            df = pd.DataFrame(out, columns=columns)
            dTable = project.newDataTable(name=vs.name, data=df)
            # think that internally is using a dict and losing order :|
            meta = [(k, str(val)) if not hasattr(val, '_ID') else (k, val.name)
                    for k in fields
                    for val in [getattr(vs, k, '')]]
            if sft := getattr(vs, 'software', ''):
                # try and convert the software information to something serializable
                meta.append(('software',
                             ':'.join(map(lambda _ss: escape(str(_ss)),
                                          filter(None, [sft.name, sft.version, sft.details, sft.tasks,
                                                        sft.vendorName, sft.vendorAddress,
                                                        sft.vendorWebAddress])))))
            dTable.updateMetadata(OrderedDict(meta))
            getLogger().debug(f'extracting dataTable {vs.name} for {vs.className}')
            vs.delete()

        columns = ['serial', 'name',
                   'generationType', 'nmrConstraintStore',
                   'details']
        out = []
        for sg in wrp.structureGenerations:
            out.append([str(val) if not hasattr(val, '_ID') else val.name
                        for col in columns
                        for val in [getattr(sg, col, '')]])
            sg.delete()
        df = pd.DataFrame(out, columns=columns)
        dTable = project.newDataTable(name='structureGenerations', data=df)
        dTable.updateMetadata({'name': 'structureGenerations'})
        getLogger().debug(f'extracting dataTable structureGenerations')

    def _loadV2Project(self, path) -> List[Project]:
        """Actual V2 project loader
        CCPNINTERNAL: called from CcpNmrV2ProjectDataLoader
        """
        from ccpn.core.Project import _loadProject

        try:
            project = _loadProject(application=self, path=str(path))
        except (ValueError, RuntimeError) as es:
            getLogger().warning(f'Error loading "{path}": {es}')
        else:
            self._closeProject()  # always close old project AFTER valid load
            self._initialiseProject(project)  # This also sets the linkages
            self._finaliseV2Upgrade(project)

            # Now that all has been restored and updated: save the result
            try:
                project.save()
                getLogger().info(f'==> Saved {project} as {project.path!r}')
            except (PermissionError, FileNotFoundError):
                getLogger().info('Folder may be read-only')
                raise
            except Exception as es:
                getLogger().warning(f'Failed saving {project} ({str(es)})')
            return [project]

    def _loadV3Project(self, path) -> List[Project]:
        """Actual V3 project loader
        CCPNINTERNAL: called from CcpNmrV3ProjectDataLoader
        """
        from ccpn.core.Project import _loadProject

        try:
            project = _loadProject(application=self, path=path)

        except (ValueError, RuntimeError) as es:
            getLogger().warning(f'Error loading "{path}": {es}')

        else:
            self._closeProject()  # always close old project AFTER valid load
            self._initialiseProject(project)  # This also sets the linkages
            return [project]

    def _loadSparkyFile(self, path: str, createNewProject=True) -> Project:
        """Load Project from Sparky file at path, and do necessary setup
        :return Project-instance (either existing or newly created)

        CCPNINTERNAL: called from SparkyDataLoader
        """
        from ccpn.core.lib.CcpnSparkyIo import SPARKY_NAME, CcpnSparkyReader

        sparkyReader = CcpnSparkyReader(self)
        dataBlock = sparkyReader.parseSparkyFile(str(path))
        sparkyName = dataBlock.getDataValues(SPARKY_NAME, firstOnly=True)

        if createNewProject and (dataBlock.getDataValues('sparky', firstOnly=True) == 'project file'):
            self._closeProject()
            project = self._newProject(sparkyName)
        else:
            project = self.project

        with self.pauseAutoBackups(delay=True):
            sparkyReader.importSparkyProject(project, dataBlock)

        return project

    def _loadStarFile(self, dataLoader) -> Project:
        """Load a Starfile, and do necessary setup
        :return Project-instance (either existing or newly created)

        CCPNINTERNAL: called from StarDataLoader
        """
        entryName = dataLoader.starReader.entryName

        if dataLoader.createNewProject:
            self._closeProject()
            project = self._newProject(entryName)
        else:
            project = self.project

        with rebuildSidebar(application=self):
            with self.pauseAutoBackups(delay=True):
                dataLoader._importIntoProject(project)

        return project

    def _loadPythonFile(self, path):
        """Load python file path into the macro editor
        CCPNINTERNAL: called from PythonDataLoader
        """
        mainWindow = self.mainWindow
        macroEditor = MacroEditor(mainWindow=mainWindow, filePath=str(path))
        mainWindow.moduleArea.addModule(macroEditor, position='top', relativeTo=mainWindow.moduleArea)
        return []

    def _loadHtmlFile(self, path):
        """Load html file path into a HtmlModule
        CCPNINTERNAL: called from HtmlDataLoader
        """
        # mainWindow = self.mainWindow
        # path = aPath(path)
        # mainWindow.newHtmlModule(urlPath=str(path), position='top', relativeTo=mainWindow.moduleArea)

        # non-native webview is currently disabled
        self._showHtmlFile('', str(path))
        return []

    #-----------------------------------------------------------------------------------------
    # NEF-related code
    #-----------------------------------------------------------------------------------------

    def _loadNefFile(self, dataLoader) -> Project:
        """Load NEF file defined by dataLoader instance
        :param dataLoader: a NefDataLoader instance
        :return Project instance (either newly created or the existing)
        CCPNINTERNAL: called from NefDataLoader.load()
        """
        from ccpn.core.Project import DEFAULT_CHEMICALSHIFTLIST
        from ccpn.core.lib.ProjectLib import checkProjectName

        TOBEDELETED = '_toBeDeleted'

        if _newProject := dataLoader.createNewProject:
            name = checkProjectName(dataLoader.nefImporter.getName(), correctName=True)
            project = self._newProject(name=name)
        else:
            project = self.project

        # TODO: find a different solution for this
        with rebuildSidebar(application=self):
            if _newProject and (ch := project.getChemicalShiftList(DEFAULT_CHEMICALSHIFTLIST)):
                # rename the existing chemical-shift-list, hopefully an unused name
                ch.rename(TOBEDELETED)

            with self.pauseAutoBackups(delay=True):
                # import the nef-file
                dataLoader._importIntoProject(project=project)

            if _newProject and ch:
                # rename chemical-shift-list back again, will add unique extension as required
                ch.rename(DEFAULT_CHEMICALSHIFTLIST)
                if len(project.chemicalShiftLists) > 1 and not ch.chemicalShifts:
                    # if still empty and more added, then not needed
                    ch._delete()

        return project

    def _exportNEF(self):
        """
        Export the current project as a Nef file
        Temporary routine because I don't know how else to do it yet
        """
        from ccpn.ui.gui.popups.ExportNefPopup import ExportNefPopup
        from ccpn.framework.lib.ccpnNef.CcpnNefIo import NEFEXTENSION

        _path = aPath(self.preferences.general.userWorkingPath or '~').filepath / (self.project.name + NEFEXTENSION)
        dialog = ExportNefPopup(self.ui.mainWindow,
                                mainWindow=self.ui.mainWindow,
                                selectFile=_path,
                                fileFilter='*.nef',
                                minimumSize=(400, 550))

        # an exclusion dict comes out of the dialog as it
        result = dialog.exec_()

        if not result:
            return

        nefPath = result['filename']
        flags = result['flags']
        pidList = result['pidList']

        # flags are skipPrefixes, expandSelection
        skipPrefixes = flags['skipPrefixes']
        expandSelection = flags['expandSelection']
        includeOrphans = flags['includeOrphans']

        self.project.exportNef(nefPath,
                               overwriteExisting=True,
                               skipPrefixes=skipPrefixes,
                               expandSelection=expandSelection,
                               includeOrphans=includeOrphans,
                               pidList=pidList)

    def _getRecentProjectFiles(self, oldPath=None) -> list:
        """Get and return a list of recent project files, setting reference to
           self as first element, unless it is a temp project
           update the preferences with the new list

           CCPNINTERNAL: called by MainWindow
        """
        project = self.project
        path = project.path
        recentFiles = self.preferences.recentFiles

        if not project.isTemporary:
            if path in recentFiles:
                recentFiles.remove(path)
            elif oldPath in recentFiles:
                recentFiles.remove(oldPath)
            elif len(recentFiles) >= 10:
                recentFiles.pop()
            recentFiles.insert(0, path)
        recentFiles = uniquify(recentFiles)
        self.preferences.recentFiles = recentFiles
        return recentFiles

    #-----------------------------------------------------------------------------------------
    # undo/redo
    #-----------------------------------------------------------------------------------------

    @logCommand('application.')
    def undo(self):
        from ccpn.core.lib.ContextManagers import busyHandler

        if self.project._undo.canUndo():
            if not self.project._undo.locked:
                # may need to put some more information in this busy popup
                with busyHandler(title='Busy', text='Undo ...', raiseErrors=True):
                    self.project._undo.undo()
        else:
            getLogger().warning('nothing to undo')

    @logCommand('application.')
    def redo(self):
        from ccpn.core.lib.ContextManagers import busyHandler

        if self.project._undo.canRedo():
            if not self.project._undo.locked:
                with busyHandler(title='Busy', text='Redo...', raiseErrors=True):
                    self.project._undo.redo()
        else:
            getLogger().warning('nothing to redo.')

    def _getUndo(self):
        """Return the undo object for the project
        """
        if self.project:
            return self.project._undo
        else:
            raise RuntimeError('Error: undefined project')

    def _increaseNotificationBlocking(self):
        self._echoBlocking += 1

    def _decreaseNotificationBlocking(self):
        if self._echoBlocking > 0:
            self._echoBlocking -= 1
        else:
            raise RuntimeError('Error: decreaseNotificationBlocking, already at 0')

    #-----------------------------------------------------------------------------------------
    # Archive code
    #-----------------------------------------------------------------------------------------

    @logCommand('application.')
    def saveToArchive(self) -> Path:
        """Archive the project.
        :return location of the archive as a Path instance
        """
        archivePath = self.project.saveToArchive()
        return archivePath

    @logCommand('application')
    def restoreFromArchive(self, archivePath) -> Project:
        """Restore a project from archive path
        :return the restored project or None on error
        """
        from ccpn.core.lib.ProjectArchiver import ProjectArchiver

        archiver = ProjectArchiver(projectPath=self.project.path)

        if (_newProjectPath := archiver.restoreArchive(archivePath=archivePath)) is not None and \
                (_newProject := self.loadProject(_newProjectPath)) is not None:

            getLogger().info('==> Restored archive %s as %s' % (archivePath, _newProject))

        else:
            getLogger().warning('Failed to restore archive %s' % (archivePath,))

        return _newProject

    #-----------------------------------------------------------------------------------------
    # Layouts
    #-----------------------------------------------------------------------------------------

    # def _getOpenLayoutPath(self):
    #     """Opens a saved Layout as dialog box and gets directory specified in the
    #     file dialog.
    #     :return selected path or None
    #     """
    #
    #     fType = 'JSON (*.json)'
    #     dialog = LayoutsFileDialog(parent=self.ui.mainWindow, acceptMode='open', fileFilter=fType)
    #     dialog._show()
    #     path = dialog.selectedFile()
    #     if not path:
    #         return None
    #     if path:
    #         return path
    #
    # def _getSaveLayoutPath(self):
    #     """Opens save Layout as dialog box and gets directory specified in the
    #     file dialog.
    #     """
    #
    #     jsonType = '.json'
    #     fType = 'JSON (*.json)'
    #     dialog = LayoutsFileDialog(parent=self.ui.mainWindow, acceptMode='save', fileFilter=fType)
    #     dialog._show()
    #     newPath = dialog.selectedFile()
    #     if not newPath:
    #         return None
    #
    #     newPath = aPath(newPath)
    #     if newPath.exists():
    #         # should not really need to check the second and third condition above, only
    #         # the Qt dialog stupidly insists a directory exists before you can select it
    #         # so if it exists but is empty then don't bother asking the question
    #         title = 'Overwrite path'
    #         msg = 'Path "%s" already exists, continue?' % newPath
    #         if not MessageDialog.showYesNo(title, msg):
    #             return None
    #
    #     newPath.assureSuffix(jsonType)
    #     return newPath

    def _getUserLayout(self, userPath=None):
        """defines the application.layout dictionary.
        For a saved project: uses the auto-generated during the saving process, if a user specified json file is given then
        is used that one instead.
        For a new project, it is used the default.
        """
        # try:
        if userPath:
            with open(userPath) as fp:
                layout = json.load(fp, object_hook=AttrDict)
                self.layout = layout

        else:
            # opens the autogenerated if an existing project
            savedLayoutPath = self._getAutogeneratedLayoutFile()
            if savedLayoutPath:
                with open(savedLayoutPath) as fp:
                    layout = json.load(fp, object_hook=AttrDict)
                    self.layout = layout

            else:  # opens the default
                if not self.project.readOnly:
                    Layout._createLayoutFile(self)
                    self._getUserLayout()

        # except Exception as e:
        #   getLogger().warning('No layout found. %s' %e)

        return self.layout

    # def _saveLayoutCallback(self):
    #     Layout.updateSavedLayout(self.ui.mainWindow)
    #     getLogger().info('Layout saved')
    #
    # def _saveLayoutAsCallback(self):
    #     path = self.getSaveLayoutPath()
    #     try:
    #         Layout.saveLayoutToJson(self.ui.mainWindow, jsonFilePath=path)
    #         getLogger().info('Layout saved')
    #     except Exception as es:
    #         getLogger().warning('Impossible to save layout. %s' % es)

    # def restoreLastSavedLayout(self):
    #     self.ui.mainWindow.moduleArea._closeAll()
    #     Layout.restoreLayout(self.ui.mainWindow, self.layout, restoreSpectrumDisplay=True)

    def _restoreLayoutFromFile(self, path):
        if path is None:
            raise ValueError('_restoreLayoutFromFile: undefined path')
        try:
            self._getUserLayout(path)
            self.ui.mainWindow.moduleArea._closeAll()
            Layout.restoreLayout(self.ui.mainWindow, self.layout, restoreSpectrumDisplay=True)

        except (PermissionError, FileNotFoundError):
            getLogger().debug('Folder may be read-only')

        except Exception as e:
            getLogger().warning(f'Impossible to restore layout. {e}')

    def _getAutogeneratedLayoutFile(self):
        if self.project:
            layoutFile = Layout.getLayoutFile(self)
            return layoutFile

    def _fetchAutogeneratedLayoutFile(self):
        if self.project:
            layoutFile = Layout.fetchLayoutFile(self)
            return layoutFile

    ###################################################################################################################
    ## MENU callbacks:  Spectrum
    ###################################################################################################################

    def showSpectrumGroupsPopup(self):
        if not self.project.spectra:
            getLogger().warning('Project has no Spectra. Spectrum groups cannot be displayed')
            MessageDialog.showWarning('Project contains no spectra.', 'Spectrum groups cannot be displayed')
        else:
            from ccpn.ui.gui.popups.SpectrumGroupEditor import SpectrumGroupEditor

            if not self.project.spectrumGroups:
                #GST This seems to have problems MessageDialog wraps it which looks bad...
                # MessageDialog.showWarning('Project has no Spectrum Groups.',
                #                           'Create them using:\nSidebar → SpectrumGroups → <New SpectrumGroup>\n ')
                SpectrumGroupEditor(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow, editMode=False).exec_()

            else:
                SpectrumGroupEditor(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow, editMode=True,
                                    obj=self.project.spectrumGroups[0]).exec_()

    def showPeakCollectionsPopup(self):
        if not self.project.spectra:
            getLogger().warning('Project has no Spectra. Spectrum groups cannot be displayed')
            MessageDialog.showWarning('Project contains no spectra.', 'Spectrum groups cannot be displayed')
        else:
            from ccpn.ui.gui.popups.SeriesPeakCollectionPopup import SeriesPeakCollectionPopup

            popup = SeriesPeakCollectionPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
            popup.exec_()
            return popup

    def showPseudoSpectrumPopup(self):
        if not self.project.spectra:
            getLogger().warning('Project has no Spectra. Pseudo Spectrum to SpectrumGroup Popup cannot be displayed')
            MessageDialog.showWarning('Project contains no spectra.',
                                      'Pseudo Spectrum to SpectrumGroup Popup cannot be displayed')
        else:
            from ccpn.ui.gui.popups.PseudoToSpectrumGroupPopup import PseudoToSpectrumGroupPopup

            popup = PseudoToSpectrumGroupPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
            popup.exec_()

    def showProjectionPopup(self):
        if not self.project.spectra:
            getLogger().warning('Project has no Spectra. Make Projection Popup cannot be displayed')
            MessageDialog.showWarning('Project contains no spectra.', 'Make Projection Popup cannot be displayed')
        else:
            from ccpn.ui.gui.popups.SpectrumProjectionPopup import SpectrumProjectionPopup

            popup = SpectrumProjectionPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
            popup.exec_()

    def showExperimentTypePopup(self):
        """
        Displays experiment type popup.
        """
        if not self.project.spectra:
            getLogger().warning('Experiment Type Selection: Project has no Spectra.')
            MessageDialog.showWarning('Experiment Type Selection', 'Project has no Spectra.')
        else:
            from ccpn.ui.gui.popups.ExperimentTypePopup import ExperimentTypePopup

            popup = ExperimentTypePopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
            popup.exec_()

    def showValidateSpectraPopup(self, spectra=None, defaultSelected=None):
        """
        Displays validate spectra popup.
        """
        if not self.project.spectra:
            getLogger().warning('Validate Spectrum Paths Selection: Project has no Spectra.')
            MessageDialog.showWarning('Validate Spectrum Paths Selection', 'Project has no Spectra.')
        else:
            from ccpn.ui.gui.popups.ValidateSpectraPopup import ValidateSpectraPopup

            popup = ValidateSpectraPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow, spectra=spectra,
                                         defaultSelected=defaultSelected)
            popup.exec_()

    def showPeakPick1DPopup(self):
        """
        Displays Peak Picking 1D Popup.
        """
        if not self.project.peakLists:
            getLogger().warning('Peak Picking: Project has no peakLists.')
            MessageDialog.showWarning('Peak Picking', 'Project has no peakLists.')
        else:
            spectra = [spec for spec in self.project.spectra if spec.dimensionCount == 1]
            if spectra:
                from ccpn.ui.gui.popups.PickPeaks1DPopup import PickPeak1DPopup

                popup = PickPeak1DPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
                popup.exec_()
            else:
                getLogger().warning('Peak Picking: Project has no 1d Spectra.')
                MessageDialog.showWarning('Peak Picking', 'Project has no 1d Spectra.')

    def showPeakPickNDPopup(self):
        """
        Displays Peak Picking ND Popup.
        """
        if not self.project.peakLists:
            getLogger().warning('Peak Picking: Project has no peakLists.')
            MessageDialog.showWarning('Peak Picking', 'Project has no peakLists.')
        else:
            spectra = [spec for spec in self.project.spectra if spec.dimensionCount > 1]
            if spectra:
                from ccpn.ui.gui.popups.PeakFind import PeakFindPopup

                popup = PeakFindPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
                popup.exec_()
            else:
                getLogger().warning('Peak Picking: Project has no Nd Spectra.')
                MessageDialog.showWarning('Peak Picking', 'Project has no Nd Spectra.')

    def showCopyPeakListPopup(self):
        if not self.project.peakLists:
            txt = 'Project has no PeakList\'s. Peak Lists cannot be copied'
            getLogger().warning(txt)
            MessageDialog.showWarning('Cannot perform a copy', txt)
            return
        else:
            from ccpn.ui.gui.popups.CopyPeakListPopup import CopyPeakListPopup

            popup = CopyPeakListPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
            popup.exec_()

    def showCopyPeaks(self):
        if not self.project.peakLists:
            getLogger().warning('Project has no Peak Lists. Peak Lists cannot be copied')
            MessageDialog.showWarning('Project has no Peak Lists.', 'Peak Lists cannot be copied')
            return
        else:
            from ccpn.ui.gui.popups.CopyPeaksPopup import CopyPeaks

            popup = CopyPeaks(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
            peaks = self.current.peaks
            popup._selectPeaks(peaks)
            popup.exec()
            popup.raise_()

    def showEstimateVolumesPopup(self):
        """
        Displays Estimate Volumes Popup.
        """
        if not self.project.peakLists:
            getLogger().warning('Estimate Volumes: Project has no peakLists.')
            MessageDialog.showWarning('Estimate Volumes', 'Project has no peakLists.')
        else:
            from ccpn.ui.gui.popups.EstimateVolumes import EstimatePeakListVolumes

            if self.current.strip and not self.current.strip.isDeleted:
                spectra = [specView.spectrum for specView in self.current.strip.spectrumDisplay.spectrumViews]
            else:
                spectra = self.project.spectra

            if spectra:
                popup = EstimatePeakListVolumes(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow,
                                                spectra=spectra)
                popup.exec_()
            else:
                getLogger().warning('Estimate Volumes: no specta selected.')
                MessageDialog.showWarning('Estimate Volumes', 'no specta selected.')

    def showEstimateCurrentVolumesPopup(self):
        """
        Calculate volumes for the currently selected peaks
        """
        # self.mainWindow.estimateVolumes()

        from ccpn.ui.gui.popups.EstimateVolumes import EstimateCurrentVolumes

        if self.current.peaks:
            popup = EstimateCurrentVolumes(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
            popup.exec_()
        else:
            getLogger().warning('Estimate Current Volumes: no current.peaks')
            MessageDialog.showWarning('Estimate Current Volumes', 'no current.peaks')

    def makeStripPlotPopup(self, includePeakLists=True, includeNmrChains=True, includeNmrChainPullSelection=True):
        if not self.project.peaks and not self.project.nmrResidues and not self.project.nmrChains:
            getLogger().warning('Cannot make strip plot, nothing to display')
            MessageDialog.showWarning('Cannot make strip plot,', 'nothing to display')
            return
        else:
            if self.current.strip and not self.current.strip.isDeleted:
                from ccpn.ui.gui.popups.StripPlotPopup import StripPlotPopup

                popup = StripPlotPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow,
                                       spectrumDisplay=self.current.strip.spectrumDisplay,
                                       includePeakLists=includePeakLists, includeNmrChains=includeNmrChains,
                                       includeNmrChainPullSelection=includeNmrChainPullSelection,
                                       includeSpectrumTable=False)
                popup.exec_()
            else:
                MessageDialog.showWarning('Make Strip Plot', 'No selected spectrumDisplay')

    ################################################################################################
    ## MENU callbacks:  Molecule
    ################################################################################################

    @logCommand('application.')
    def showCreateChainPopup(self):
        """
        Displays sequence creation popup.
        """
        from ccpn.ui.gui.popups.CreateChainPopup import CreateChainPopup

        popup = CreateChainPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
        popup.exec_()

    # @logCommand('application.')
    # def toggleSequenceModule(self):
    #     """
    #     Toggles whether Sequence Module is displayed or not
    #     """
    #     self.showSequenceModule()

    # @logCommand('application.')
    # def showSequenceModule(self, position='top', relativeTo=None):
    #     """
    #     Displays Sequence Module at the top of the screen.
    #     """
    #     from ccpn.ui.gui.modules.SequenceModule import SequenceModule
    #
    #     if SequenceModule._alreadyOpened is False:
    #         mainWindow = self.ui.mainWindow
    #         self.sequenceModule = SequenceModule(mainWindow=mainWindow)
    #         mainWindow.moduleArea.addModule(self.sequenceModule,
    #                                         position=position, relativeTo=relativeTo)
    #         action = self._findMenuAction('View', 'Show Sequence')
    #         if action:
    #             action.setChecked(True)
    #
    #         # set the colours of the currently highlighted chain in open sequenceGraph
    #         # should really be in the class, but doesn't fire correctly during __init__
    #         self.sequenceModule.populateFromSequenceGraphs()

    # @logCommand('application.')
    # def hideSequenceModule(self):
    #     """Hides sequence module"""
    #
    #     if hasattr(self, 'sequenceModule'):
    #         self.sequenceModule.close()
    #         delattr(self, 'sequenceModule')

    def inspectMolecule(self):
        pass

    @logCommand('application.')
    def showResidueInformation(self, position: str = 'bottom', relativeTo: CcpnModule = None):
        """Displays Residue Information module.
        """
        from ccpn.ui.gui.modules.ResidueInformation import ResidueInformation

        if not self.project.residues:
            getLogger().warning(
                    'No Residues in project. Residue Information Module requires Residues in the project to launch.')
            MessageDialog.showWarning('No Residues in project.',
                                      'Residue Information Module requires Residues in the project to launch.')
            return

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea  # ejb
        residueModule = ResidueInformation(mainWindow=mainWindow)
        mainWindow.moduleArea.addModule(residueModule, position=position, relativeTo=relativeTo)
        return residueModule

    @logCommand('application.')
    def showReferenceChemicalShifts(self, position='left', relativeTo=None):
        """Displays Reference Chemical Shifts module."""
        from ccpn.ui.gui.modules.ReferenceChemicalShifts import ReferenceChemicalShifts

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        refChemShifts = ReferenceChemicalShifts(mainWindow=mainWindow)
        mainWindow.moduleArea.addModule(refChemShifts, position=position, relativeTo=relativeTo)
        return refChemShifts

    @logCommand('gui.')
    def showMolecularBondsPopup(self):
        """Displays the molecular-bonds popup.
        """
        from ccpn.ui.gui.popups.MolecularBondsPopup import MolecularBondsPopup

        popup = MolecularBondsPopup(parent=self.mainWindow, mainWindow=self.mainWindow)
        popup.exec_()

    ###################################################################################################################
    ## MENU callbacks:  VIEW
    ###################################################################################################################

    @logCommand('application.')
    def showChemicalShiftTable(self,
                               position: str = 'bottom',
                               relativeTo: CcpnModule = None,
                               chemicalShiftList=None, selectFirstItem=False):
        """Displays Chemical Shift table.
        """
        from ccpn.ui.gui.modules.ChemicalShiftTable import ChemicalShiftTableModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        chemicalShiftTableModule = ChemicalShiftTableModule(mainWindow=mainWindow, selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(chemicalShiftTableModule, position=position, relativeTo=relativeTo)
        if chemicalShiftList:
            chemicalShiftTableModule.selectTable(chemicalShiftList)
        return chemicalShiftTableModule

    @logCommand('application.')
    def showNmrResidueTable(self, position='bottom', relativeTo=None,
                            nmrChain=None, selectFirstItem=False):
        """Displays Nmr Residue Table
        """
        from ccpn.ui.gui.modules.NmrResidueTable import NmrResidueTableModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        nmrResidueTableModule = NmrResidueTableModule(mainWindow=mainWindow, selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(nmrResidueTableModule, position=position, relativeTo=relativeTo)
        if nmrChain:
            nmrResidueTableModule.selectTable(nmrChain)
        return nmrResidueTableModule

    @logCommand('application.')
    def showResidueTable(self, position='bottom', relativeTo=None,
                         chain=None, selectFirstItem=False):
        """Displays  Residue Table
        """
        from ccpn.ui.gui.modules.ResidueTable import ResidueTableModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        residueTableModule = ResidueTableModule(mainWindow=mainWindow, selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(residueTableModule, position=position, relativeTo=relativeTo)
        if chain:
            residueTableModule.selectTable(chain)
        return residueTableModule

    @logCommand('application.')
    def showPeakTable(self, position: str = 'left', relativeTo: CcpnModule = None,
                      peakList: PeakList = None, selectFirstItem=False):
        """Displays Peak table on left of main window with specified list selected.
        """
        from ccpn.ui.gui.modules.PeakTable import PeakTableModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        peakTableModule = PeakTableModule(mainWindow, selectFirstItem=False)  #selection is done by the current peaks.
        if self.current.peak and not peakList:
            peakList = self.current.peak.peakList
        if peakList:
            peakTableModule.selectTable(peakList)
            peakTableModule.selectPeaks(self.current.peaks)

        mainWindow.moduleArea.addModule(peakTableModule, position=position, relativeTo=relativeTo)
        return peakTableModule

    @logCommand('application.')
    def showMultipletTable(self, position: str = 'left', relativeTo: CcpnModule = None,
                           multipletList: MultipletList = None, selectFirstItem=False):
        """Displays multipletList table on left of main window with specified list selected.
        """
        from ccpn.ui.gui.modules.MultipletTable import MultipletTableModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        multipletTableModule = MultipletTableModule(mainWindow, selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(multipletTableModule, position=position, relativeTo=relativeTo)
        if multipletList:
            multipletTableModule.selectTable(multipletList)
        return multipletTableModule

    @logCommand('application.')
    def showIntegralTable(self, position: str = 'left', relativeTo: CcpnModule = None,
                          integralList: IntegralList = None, selectFirstItem=False):
        """Displays integral table on left of main window with specified list selected.
        """
        from ccpn.ui.gui.modules.IntegralTable import IntegralTableModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        integralTableModule = IntegralTableModule(mainWindow=mainWindow, selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(integralTableModule, position=position, relativeTo=relativeTo)
        if integralList:
            integralTableModule.selectTable(integralList)
        return integralTableModule

    @logCommand('application.')
    def showRestraintTable(self, position: str = 'bottom', relativeTo: CcpnModule = None,
                           restraintTable=None, selectFirstItem=False):
        """Displays Peak table on left of main window with specified list selected.
        """
        from ccpn.ui.gui.modules.RestraintTableModule import RestraintTableModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        restraintTableModule = RestraintTableModule(mainWindow=mainWindow, selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(restraintTableModule, position=position, relativeTo=relativeTo)
        if restraintTable:
            restraintTableModule.selectTable(restraintTable)
        return restraintTableModule

    @logCommand('application.')
    def showStructureTable(self, position='bottom', relativeTo=None,
                           structureEnsemble=None, selectFirstItem=False):
        """Displays Structure Table
        """
        from ccpn.ui.gui.modules.StructureTable import StructureTableModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        structureTableModule = StructureTableModule(mainWindow=mainWindow, selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(structureTableModule, position=position, relativeTo=relativeTo)
        if structureEnsemble:
            structureTableModule.selectTable(structureEnsemble)
        return structureTableModule

    @logCommand('application.')
    def showDataTable(self, position='bottom', relativeTo=None,
                      dataTable=None, selectFirstItem=False):
        """Displays DataTable Table
        """
        # from ccpn.ui.gui.modules.DataTableModuleABC import DataTableModuleBC as _module
        from ccpn.ui.gui.modules.DataTableModule import DataTableModule as _module

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea

        _dataTableModule = _module(mainWindow=mainWindow, table=dataTable, selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(_dataTableModule, position=position, relativeTo=relativeTo)
        return _dataTableModule

    @logCommand('application.')
    def showViolationTable(self, position: str = 'bottom', relativeTo: CcpnModule = None,
                           violationTable=None, selectFirstItem=False):
        """Displays Violation table on left of main window with specified list selected.
        """
        from ccpn.ui.gui.modules.ViolationTableModule import ViolationTableModule as _module

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea

        _violationTableModule = _module(mainWindow=mainWindow, table=violationTable, selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(_violationTableModule, position=position, relativeTo=relativeTo)
        return _violationTableModule

    @logCommand('application.')
    def showCollectionModule(self, position='bottom', relativeTo=None,
                             collection=None, selectFirstItem=False):
        """Displays Collection Module
        """
        MessageDialog.showNYI(parent=self.mainWindow)
        # pass

    @logCommand('application.')
    def showNotesEditor(self, position: str = 'bottom', relativeTo: CcpnModule = None,
                        note=None, selectFirstItem=False):
        """Displays Notes Editing Table
        """
        from ccpn.ui.gui.modules.NotesEditor import NotesEditorModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea

        notesEditorModule = NotesEditorModule(mainWindow=mainWindow, selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(notesEditorModule, position=position, relativeTo=relativeTo)
        if note:
            notesEditorModule.selectNote(note)
        return notesEditorModule

    @logCommand('application.')
    def showRestraintAnalysisTable(self,
                                   position: str = 'bottom',
                                   relativeTo: CcpnModule = None,
                                   peakList=None, selectFirstItem=False):
        """Displays restraint analysis Inspector.
        """
        from ccpn.ui.gui.modules.RestraintAnalysisTable import RestraintAnalysisTableModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        restraintAnalysisTableModule = RestraintAnalysisTableModule(mainWindow=mainWindow,
                                                                    selectFirstItem=selectFirstItem)
        mainWindow.moduleArea.addModule(restraintAnalysisTableModule, position=position, relativeTo=relativeTo)
        if peakList:
            restraintAnalysisTableModule.selectPeakList(peakList)
        return restraintAnalysisTableModule

    def showPrintSpectrumDisplayPopup(self):
        """Show the print spectrumDisplay dialog
        """
        from ccpn.ui.gui.popups.ExportStripToFile import ExportStripToFilePopup

        if len(self.project.spectrumDisplays) == 0:
            MessageDialog.showWarning('', 'No SpectrumDisplay found')
        else:
            exportDialog = ExportStripToFilePopup(parent=self.ui.mainWindow,
                                                  mainWindow=self.ui.mainWindow,
                                                  strips=self.project.strips,
                                                  selectedStrip=self.current.strip
                                                  )
            exportDialog.exec_()

    def toggleToolbar(self):
        if self.current.strip is not None:
            self.current.strip.spectrumDisplay.toggleToolbar()
        else:
            getLogger().warning('No strip selected')

    def toggleSpectrumToolbar(self):
        if self.current.strip is not None:
            self.current.strip.spectrumDisplay.toggleSpectrumToolbar()
        else:
            getLogger().warning('No strip selected')

    def togglePhaseConsole(self):
        if self.current.strip is not None:
            self.current.strip.spectrumDisplay.togglePhaseConsole()
        else:
            getLogger().warning('No strip selected')

    def _setZoomPopup(self):
        if self.current.strip is not None:
            self.current.strip._setZoomPopup()
        else:
            getLogger().warning('No strip selected')

    def resetZoom(self):
        if self.current.strip is not None:
            self.current.strip.resetZoom()
        else:
            getLogger().warning('No strip selected')

    def copyStrip(self):
        if self.current.strip is not None:
            self.current.strip.copyStrip()
        else:
            getLogger().warning('No strip selected')

    def showFlipArbitraryAxisPopup(self, usePosition=False):
        if (strp := self.current.strip) is None:
            getLogger().warning('No strip selected')

        elif self.current.strip.spectrumDisplay.is1D:
            getLogger().warning('Function not permitted on 1D spectra')

        else:
            from ccpn.ui.gui.popups.CopyStripFlippedAxesPopup import CopyStripFlippedSpectraPopup

            try:
                mDict = usePosition and self.current.mouseMovedDict[1]
                positions = [poss[0] if (poss := mDict.get(ax)) else None
                             for ax in strp.axisCodes] if usePosition else None
                popup = CopyStripFlippedSpectraPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow,
                                                     strip=strp, label=strp.id,
                                                     positions=positions)
                popup.exec_()
            except Exception as es:
                getLogger().warning(f'Cannot show popup: {es}')

    def arrangeLabels(self):
        """Auto-arrange the peak/multiplet labels to minimise any overlaps.
        """
        if (strp := self.current.strip) is None:
            getLogger().warning('No strip selected')

        else:
            strp.spectrumDisplay.arrangeLabels()

    def resetLabels(self):
        """Reset arrangement of peak/multiplet labels.
        """
        if (strp := self.current.strip) is None:
            getLogger().warning('No strip selected')

        else:
            strp.spectrumDisplay.resetLabels()

    def showReorderPeakListAxesPopup(self):
        """
        Displays Reorder PeakList Axes Popup.
        """
        if not self.project.peakLists:
            getLogger().warning('Reorder PeakList Axes: Project has no peakLists.')
            MessageDialog.showWarning('Reorder PeakList Axes', 'Project has no peakLists.')
        else:
            from ccpn.ui.gui.popups.ReorderPeakListAxes import ReorderPeakListAxes

            popup = ReorderPeakListAxes(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow)
            popup.exec_()

    def _flipXYAxisCallback(self):
        """Callback to flip axes"""
        if self.current.strip is not None:
            self.current.strip.flipXYAxis()
        else:
            getLogger().warning('No strip selected')

    def _flipXZAxisCallback(self):
        """Callback to flip axes"""
        if self.current.strip is not None:
            self.current.strip.flipXZAxis()
        else:
            getLogger().warning('No strip selected')

    def _flipYZAxisCallback(self):
        """Callback to flip axes"""
        if self.current.strip is not None:
            self.current.strip.flipYZAxis()
        else:
            getLogger().warning('No strip selected')

    def _toggleConsoleCallback(self):
        """Toggles whether python console is displayed at bottom of the main window.
        """
        self.ui.mainWindow.toggleConsole()

    @deprecated('Use showChemicalShiftMappingModule to access the latest implementation')
    def showChemicalShiftMapping(self, position: str = 'top', relativeTo: CcpnModule = None):
        return self.showChemicalShiftMappingModule(position=position, relativeTo=relativeTo)

    def showChemicalShiftMappingModule(self, position: str = 'top', relativeTo: CcpnModule = None):
        from ccpn.ui.gui.modules.experimentAnalysis.ChemicalShiftMappingGuiModule import ChemicalShiftMappingGuiModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        cs = ChemicalShiftMappingGuiModule(mainWindow=mainWindow)
        mainWindow.moduleArea.addModule(cs, position=position, relativeTo=relativeTo)
        return cs

    def showRelaxationModule(self, position: str = 'top', relativeTo: CcpnModule = None):
        from ccpn.ui.gui.modules.experimentAnalysis.RelaxationGuiModule import RelaxationGuiModule

        mainWindow = self.ui.mainWindow
        if not relativeTo:
            relativeTo = mainWindow.moduleArea
        relGuiModule = RelaxationGuiModule(mainWindow=mainWindow)
        mainWindow.moduleArea.addModule(relGuiModule, position=position, relativeTo=relativeTo)
        return relGuiModule

    def toggleCrosshairAll(self):
        """Toggles whether crosshairs are displayed in all windows.
        """
        for window in self.project.windows:
            window.toggleCrosshair()

    #################################################################################################
    ## MENU callbacks:  Macro
    #################################################################################################

    @logCommand('application.')
    def _showMacroEditorCallback(self):
        """Displays macro editor. Just handing down to MainWindow for now
        """
        self.mainWindow.newMacroEditor()

    def _openMacroCallback(self, directory=None):
        """ Select macro file and on MacroEditor.
        """
        mainWindow = self.ui.mainWindow
        dialog = MacrosFileDialog(parent=mainWindow, acceptMode='open', fileFilter='*.py', directory=directory)
        dialog._show()
        path = dialog.selectedFile()
        if path is not None:
            self.mainWindow.newMacroEditor(path=path)

    def defineUserShortcuts(self):

        from ccpn.ui.gui.popups.ShortcutsPopup import ShortcutsPopup

        ShortcutsPopup(parent=self.ui.mainWindow, mainWindow=self.ui.mainWindow).exec_()

    def runMacro(self, macroFile: str = None, extraCommands=None):
        """
        Runs a macro if a macro is specified, or opens a dialog box for selection of a macro file and then
        runs the selected macro.
        """
        if macroFile is None:
            fType = '*.py'
            dialog = MacrosFileDialog(parent=self.ui.mainWindow, acceptMode='run', fileFilter=fType)
            dialog._show()
            macroFile = dialog.selectedFile()
            if not macroFile:
                return

        if not macroFile in self.preferences.recentMacros:
            if extraCommands is None:
                self.preferences.recentMacros.append(macroFile)
        self.ui.mainWindow.pythonConsole._runMacro(macroFile, extraCommands=extraCommands)

    #################################################################################################

    def _systemOpen(self, path):
        """Open path to pdf file on system
        """
        if isWindowsOS():
            os.startfile(path)
        elif isMacOS():
            subprocess.run(['open', path], check=True)
        else:
            linuxCommand = self.preferences.externalPrograms.PDFViewer
            # assume a linux and use the choice given in the preferences
            if linuxCommand and aPath(linuxCommand).is_file():
                from ccpn.framework.PathsAndUrls import ccpnRunTerminal

                try:
                    # NOTE:ED - this could be quite nasty, but can't think of another way to get Linux to open a pdf
                    subprocess.run([linuxCommand, path])

                except Exception as es:
                    getLogger().warning(f'Error opening PDFViewer. {es}')
                    MessageDialog.showWarning('Open File',
                                              f'Error opening PDFViewer. {es}\n'
                                              f'Check settings in Preferences->External Programs'
                                              )

            else:
                # raise TypeError('PDFViewer not defined for linux')
                MessageDialog.showWarning('Open File',
                                          'Please select PDFViewer in Preferences->External Programs')

    def __str__(self):
        return '<%s version:%s>' % (self.applicationName, self.applicationVersion)

    __repr__ = __str__


#-----------------------------------------------------------------------------------------
#end class
#-----------------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------------
# code for testing purposes
#-----------------------------------------------------------------------------------------

def createFramework(projectPath=None, **kwds):
    # stop circular import when run from main entry point
    from ccpn.AnalysisAssign.AnalysisAssign import Assign

    class MyProgramme(Assign):
        """My first app
        """
        applicationName = 'CcpNmr'
        applicationVersion = Version.applicationVersion


    args = Arguments(projectPath=projectPath, **kwds)
    result = MyProgramme(args)
    result._startApplication()
    #
    return result


def main():
    # stop circular import when run from main entry point
    from ccpn.AnalysisAssign.AnalysisAssign import Assign

    class MyProgramme(Assign):
        """My first app
        """
        applicationName = 'CcpNmr'
        applicationVersion = Version.applicationVersion


    _makeMainWindowVisible = False

    myArgs = Arguments()
    myArgs.noGui = False
    myArgs.debug = True

    application = MyProgramme(args=myArgs)
    ui = application.ui
    ui.initialize(ui.mainWindow)  # ui.mainWindow not needed for refactored?

    if _makeMainWindowVisible:
        ui.mainWindow._updateMainWindow(newProject=True)
        ui.mainWindow.show()
        QtWidgets.QApplication.setActiveWindow(ui.mainWindow)

    # register the programme
    from ccpn.framework.Application import ApplicationContainer

    container = ApplicationContainer()
    container.register(application)
    application.useFileLogger = True

    # show the mainWindow
    application.start()


if __name__ == '__main__':
    main()
