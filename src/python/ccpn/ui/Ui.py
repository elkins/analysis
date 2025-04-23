"""Default application no-user-interface UI implementation
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
__dateModified__ = "$dateModified: 2025-04-23 14:49:29 +0100 (Wed, April 23, 2025) $"
__version__ = "$Revision: 3.2.12 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: TJ Ragan $"
__date__ = "$Date: 2017-03-22 13:00:57 +0000 (Wed, March 22, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
import typing
import re
import os

from ccpn.framework.Version import applicationVersion
from ccpn.framework.PathsAndUrls import CCPN_EXTENSION

from ccpn.core.Project import Project
from ccpn.core.lib.Notifiers import NotifierBase
from ccpn.core.lib.ContextManagers import catchExceptions

from ccpn.util import Register
from ccpn.util.Update import installUpdates, UpdateAgent
from ccpn.util.Logging import getLogger
from ccpn.util.Path import aPath
from ccpn.util.decorators import logCommand


class Ui(NotifierBase):
    """Superclass for all user interface classes"""

    # Factory functions for UI-specific instantiation of wrapped graphics classes
    _factoryFunctions = {}

    def __init__(self, application):

        self.application = application
        self.mainWindow = None
        self.pluginModules = []

    @property
    def project(self):
        return self.application.project

    def initialize(self, mainWindow):
        """UI operations done after every project load/create"""
        pass

    def startUi(self):
        """Start the ui execution
        """
        sys.stderr.write('==> %s interface is ready\n' % self.__class__.__name__)

    def _checkRegistration(self) -> bool:
        """Check if registered and if not popup registration and if still
        no good then exit
        :return True if properly registered
        """

        # checking the registration; need to have the app running, but before the splashscreen, as it will hang
        # in case the popup is needed.
        # We want to give some feedback; sometimes this takes a while (e.g. poor internet)
        # sys.stderr.write('==> Checking registration ... \n')
        sys.stderr.flush()  # It seems to be necessary as without the output comes after the registration screen
        sys.stderr.write('==> Checking registration on server\n')

        # check local registration details
        if not (self._isRegistered and self._termsConditions):
            # call the subclassed register method
            self._registerDetails(self._isRegistered, self._termsConditions)
            if not (self._isRegistered and self._termsConditions):

                if not self._isRegistered:
                    days = Register._graceCounter(Register._fetchGraceFile(self.application))
                    if days > 0:
                        sys.stderr.write('\n### Please register within %s day(s)\n' % days)
                        return True
                    else:
                        sys.stderr.write('\n### INVALID REGISTRATION, terminating\n')
                        return False
                else:
                    if not self._termsConditions:
                        sys.stderr.write('\n### Please accept the terms and conditions, terminating\n')
                        return False

        # check whether your registration details are on the server (and match)
        check = Register.checkServer(self.application._registrationDict, self.application.applicationVersion)
        if check is None:
            # possibly an error trying to locate the server
            return True
        if check is False:
            # invalid registration details, either wrong licenceKey or wrong version, etc.
            self._registerDetails(self._isRegistered, self._termsConditions)
            check = Register.checkServer(self.application._registrationDict, self.application.applicationVersion)

        return check if check is not None else True

    def echoCommands(self, commands: typing.List[str]):
        """Echo commands strings, one by one, to logger.
        Overwritten in subclasses to handle e.g. console output
        """
        logger = getLogger()
        for command in commands:
            logger.echoInfo(command)

    def _execUpdates(self):
        raise NotImplementedError('ERROR: ..to be subclassed by ui types')

    def _checkForUpdates(self):
        """Check for updates
        """
        # applicationVersion = __version__.split()[1]  # ejb - read from the header
        _version = applicationVersion  # .withoutRelease()
        updateAgent = UpdateAgent(_version, dryRun=False)
        numUpdates = updateAgent.checkNumberUpdates()
        getLogger().debug(f'_checkUpdates: {numUpdates} updates available')
        if numUpdates > 0:
            return self._execUpdates()

    @property
    def _isRegistered(self):
        """return True if registered"""
        self.application._registrationDict = Register.loadDict()
        return not Register.isNewRegistration(self.application._registrationDict)

    @property
    def _termsConditions(self):
        """return True if latest terms and conditions have been accepted
        """
        regDict = Register.loadDict()
        self.application._registrationDict = regDict

        from ccpn.framework.PathsAndUrls import licensePath
        from ccpn.util.Update import calcHashCode, TERMSANDCONDITIONS

        md5 = regDict.get(TERMSANDCONDITIONS)
        if os.path.exists(licensePath):
            currentHashCode = calcHashCode(licensePath)
            return (currentHashCode == md5)

    def _checkUpdateTermsConditions(self, registered, acceptedTerms):
        """Update the registration file if fully registered and accepted
        """
        from ccpn.framework.PathsAndUrls import licensePath
        from ccpn.util.Update import calcHashCode, TERMSANDCONDITIONS

        regDict = Register.loadDict()

        md5 = regDict.get(TERMSANDCONDITIONS)
        if registered and acceptedTerms and os.path.exists(licensePath):
            currentHashCode = calcHashCode(licensePath)
            latestTerms = (currentHashCode == md5)
            if not latestTerms:
                # write the updated md5
                regDict[TERMSANDCONDITIONS] = md5
                Register.saveDict(regDict)

    def loadProject(self, path) -> Project | None:
        """Just a stub for now; calling MainWindow methods as it initialises the Gui
        """
        return self._loadProject(path=path)

    def _loadProject(self, dataLoader=None, path=None) -> Project | None:
        """Load a project either from a dataLoader instance or from path;
        build the project Gui elements
        :returns project instance or None
        """
        from ccpn.framework.lib.DataLoaders.DataLoaderABC import checkPathForDataLoader
        from ccpn.framework.Application import getApplication

        _app = getApplication()

        if dataLoader is None and path is not None:
            dataLoader = checkPathForDataLoader(path)
        if dataLoader is None:
            getLogger().error('No suitable dataLoader found')
            return None
        if not dataLoader.createNewProject:
            getLogger().error('"%s" does not yield a new project' % dataLoader.path)
            return None

        # Check that the path does not contain a bottom-level space
        if ' ' in aPath(path).basename:
            getLogger().error('"%s" does not yield a valid project\n'
                              'Cannot load project folders where the project-name contains spaces.\n'
                              'Please rename the folder without spaces and try loading again.' % dataLoader.path)
            return None

        if _app and _app.project:
            # Some error recovery; store info to re-open the current project (or a new default)
            oldProjectPath = _app.project.path
            oldProjectIsTemporary = _app.project.isTemporary
        else:
            oldProjectPath = oldProjectIsTemporary = None

        try:
            _loaded = dataLoader.load()
            if not _loaded:
                return
            newProject = _loaded[0]
        except RuntimeError as es:
            getLogger().error('"%s" did not yield a valid new project (%s)' % (dataLoader.path, str(es)))

            if _app:
                # First get to a defined state
                _app._newProject()
                if not oldProjectIsTemporary:
                    _app.loadProject(oldProjectPath)
                return None
        else:
            # if the new project contains invalid spectra then open the popup to see them
            self._checkForBadSpectra(newProject)

            return newProject

    @staticmethod
    def _checkForBadSpectra(project):
        """Report bad spectra in a popup
        """
        if badSpectra := [str(spectrum) for spectrum in project.spectra if not spectrum.hasValidPath()]:
            text = 'Detected invalid Spectrum file path(s) for:\n\n'
            for sp in badSpectra:
                text += '%s\n' % str(sp)
            text += '\nUse menu "Spectrum --> Validate paths.." or "VP" shortcut to correct\n'
            getLogger().warning(f'Spectrum file paths: {text}')

    @staticmethod
    def getProgressHandler():
        """Return the context-manager to handle dsplaying progress-bar
        """
        from ccpn.ui.gui.widgets.ProgressWidget import ProgressDialog

        return ProgressDialog

    def _closeProject(self):
        """Cleanup before closing project
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")


class NoUi(Ui):

    def _registerDetails(self, registered=False, acceptedTerms=False):
        """Display registration information
        """

        # check valid internet connection first
        if not Register.checkInternetConnection():
            sys.stderr.write('Could not connect to the registration server, please check your internet connection.')
            sys.exit(0)

        from ccpn.framework.Version import applicationVersion
        # applicationVersion = __version__.split()[1]

        # sys.stderr.write('\n### Please register, using another application, or in Gui Mode\n')

        from ccpn.framework.PathsAndUrls import licensePath

        try:
            self.application._showLicense()
        except Exception:
            sys.stderr.write('The licence file can be found at %s\n' % licensePath)

        validEmailRegex = re.compile(r'^[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-_]+\.)+[A-Za-z]{2,63}$')

        sys.stderr.write('Please take a moment to read the licence\n')
        agree = None
        while agree is None:
            agreeIn = input('Do you agree to the terms and conditions of the Licence? [Yes/No]')
            if agreeIn.lower() in ['y', 'yes']:
                agree = True
            elif agreeIn.lower() in ['n', 'no']:
                agree = False
            else:
                sys.stderr.write("Enter 'yes' or 'no'\n")

        if agree:
            from ccpn.framework.PathsAndUrls import licensePath
            from ccpn.util.Update import calcHashCode, TERMSANDCONDITIONS

            # read teh existing registration details
            registrationDict = Register.loadDict()

            sys.stderr.flush()
            sys.stderr.write("Please enter registration details:\n")

            # ('name', 'organisation', 'email')
            for attr in Register.userAttributes:
                if 'email' in attr:
                    validEmail = False
                    while not validEmail:
                        oldVal = registrationDict.get(attr)
                        sys.stderr.flush()
                        if oldVal:
                            regIn = input(f'{str(attr)} [{oldVal}] >')
                            registrationDict[attr] = regIn or oldVal
                        else:
                            regIn = input(f'{attr} >')
                            registrationDict[attr] = regIn or ''

                        validEmail = bool(validEmailRegex.match(registrationDict.get(attr)))
                        if not validEmail:
                            sys.stderr.write(attr + ' is invalid, please try again\n')

                else:
                    sys.stderr.flush()
                    if oldVal := registrationDict.get(attr):
                        regIn = input(f'{str(attr)} [{oldVal}] >')
                        registrationDict[attr] = regIn or oldVal
                    else:
                        regIn = input(f'{attr} >')
                        registrationDict[attr] = regIn or ''

            # write the updated md5
            currentHashCode = calcHashCode(licensePath)
            registrationDict[TERMSANDCONDITIONS] = currentHashCode

            Register.setHashCode(registrationDict)
            Register.saveDict(registrationDict)
            Register.updateServer(registrationDict, applicationVersion)

        else:
            sys.stderr.write('You must agree to the licence to continue')
            sys.exit(0)

    def _execUpdates(self):
        sys.stderr.write('==> NoUi update\n')

        from ccpn.framework.Version import applicationVersion

        # applicationVersion = __version__.split()[1]  # ejb - read from the header
        exitCode = installUpdates(applicationVersion)  # .withoutRelease(), dryRun=False)

        sys.stderr.write('Please restart the program to apply the updates\n')
        sys.exit(exitCode)

    @staticmethod
    def getProgressHandler():
        """Return the context-manager to handle dsplaying progress-bar
        """
        from ccpn.ui.gui.widgets.ProgressWidget import ProgressTextBar

        return ProgressTextBar

    def _closeProject(self):
        """Cleanup before closing project
        """
        # nothing required?
        pass

    def _getDataLoader(self, path, pathFilter=None):
        """Get dataLoader for path (or None if not present), optionally only testing for
        dataFormats defined in filter.
        Allows for reporting or checking through popups.
        Does not do the actual loading.

        :param path: the path to get a dataLoader for
        :param pathFilter: a list/tuple of optional dataFormat strings; (defaults to all dataFormats)
        :returns a tuple (dataLoader, createNewProject, ignore)
        """
        # local import here
        from ccpn.framework.lib.DataLoaders.CcpNmrV2ProjectDataLoader import CcpNmrV2ProjectDataLoader
        from ccpn.framework.lib.DataLoaders.CcpNmrV3ProjectDataLoader import CcpNmrV3ProjectDataLoader
        from ccpn.framework.lib.DataLoaders.NefDataLoader import NefDataLoader
        from ccpn.framework.lib.DataLoaders.SparkyDataLoader import SparkyDataLoader
        from ccpn.framework.lib.DataLoaders.StarDataLoader import StarDataLoader
        from ccpn.framework.lib.DataLoaders.DirectoryDataLoader import DirectoryDataLoader
        from ccpn.framework.lib.DataLoaders.DataLoaderABC import _getPotentialDataLoaders

        from ccpn.framework.lib.DataLoaders.DataLoaderABC import getDataLoaders, _checkPathForDataLoader
        from ccpn.core.Project import Project

        if pathFilter is None:
            pathFilter = tuple(getDataLoaders().keys())

        _loaders = _checkPathForDataLoader(path=path, formatFilter=pathFilter)
        if len(_loaders) > 0 and _loaders[-1].isValid:
            # found a valid one; use that
            dataLoader = _loaders[-1]

        # log errors
        elif len(_loaders) == 0:
            dataLoader = None
            txt = f'No valid loader found for {path}'

        elif len(_loaders) == 1 and not _loaders[0].isValid:
            dataLoader = None
            txt = f'No valid loader: {_loaders[0].errorString}'

        else:
            dataLoader = None
            txt = f'No valid loader found for {path}; tried {[dl.dataFormat for dl in _loaders]}'

        if dataLoader is None:
            getLogger().warning(txt)
            return (None, False, False)

        # if (dataLoader :=  checkPathForDataLoader(path, pathFilter=pathFilter)) is None:
        #     dataFormats = [dl.dataFormat for dl in _getPotentialDataLoaders(path)]
        #     txt = f'Loading "{path}" unsuccessful; tried all of {dataFormats}, but failed'
        #     getLogger().warning(txt)
        #     return (None, False, False)

        createNewProject = dataLoader.createNewProject
        ignore = False

        path = dataLoader.path

        # Check that the path does not contain a bottom-level space
        if dataLoader.dataFormat in [CcpNmrV2ProjectDataLoader.dataFormat, CcpNmrV3ProjectDataLoader.dataFormat] and \
                ' ' in aPath(dataLoader.path).basename:
            getLogger().warning('Encountered a problem loading:\n"%s"\n\n'
                                'Cannot load project folders where the project-name contains spaces.\n\n'
                                'Please rename the folder without spaces and try loading again.' % dataLoader.path)
            # skip loading bad projects
            ignore = True

        elif dataLoader.dataFormat == CcpNmrV2ProjectDataLoader.dataFormat:
            createNewProject = True
            dataLoader.createNewProject = True
            # ok = MessageDialog.showYesNoWarning(f'Load Project',
            #                                     f'Project "{path.name}" was created with version-2 Analysis.\n'
            #                                     f'\n'
            #                                     f'CAUTION:\n'
            #                                     f'The project will be converted to a version-3 project and saved as a new directory with .ccpn extension.\n'
            #                                     f'\n'
            #                                     f'Do you want to continue loading?')
            #
            # if not ok:
            #     # skip loading so that user can backup/copy project
            #     getLogger().info('==> Cancelled loading ccpn project "%s"' % path)
            #     ignore = True

        elif dataLoader.dataFormat == CcpNmrV3ProjectDataLoader.dataFormat and Project._needsUpgrading(path):
            createNewProject = True
            dataLoader.createNewProject = True

            DONT_OPEN = "Don't Open"
            CONTINUE = 'Continue'
            MAKE_ARCHIVE = 'Make a backup archive (.tgz) of the project'

            dataLoader.makeArchive = False
            # ok = MessageDialog.showMulti(f'Load Project',
            #                              f'You are opening an older project (version 3.0.x) - {path.name}\n'
            #                              f'\n'
            #                              f'When you save, it will be upgraded and will not be readable by version 3.0.4\n',
            #                              texts=[DONT_OPEN, CONTINUE],
            #                              checkbox=MAKE_ARCHIVE, checked=False,
            #                              )
            #
            # if not any(ss in ok for ss in [DONT_OPEN, MAKE_ARCHIVE, CONTINUE]):
            #     # there was an error from the dialog
            #     getLogger().debug(f'==> Cancelled loading ccpn project "{path}" - error in dialog')
            #     ignore = True
            #
            # if DONT_OPEN in ok:
            #     # user selection not to load
            #     getLogger().info(f'==> Cancelled loading ccpn project "{path}"')
            #     ignore = True
            #
            # elif MAKE_ARCHIVE in ok:
            #     # flag to make a backup archive
            #     dataLoader.makeArchive = True

        elif dataLoader.dataFormat == NefDataLoader.dataFormat:
            (dataLoader, createNewProject, ignore) = self._queryChoices(dataLoader)
            if dataLoader and not createNewProject and not ignore:
                # we are importing; popup the import window
                ok = self.mainWindow._showNefPopup(dataLoader)
                if not ok:
                    ignore = True

        elif dataLoader.dataFormat == SparkyDataLoader.dataFormat:
            (dataLoader, createNewProject, ignore) = self._queryChoices(dataLoader)

        # elif dataLoader.isSpectrumLoader and dataLoader.existsInProject():
        #     ok = MessageDialog.showYesNoWarning('Loading Spectrum',
        #                                         f'"{dataLoader.path}"\n'
        #                                         f'already exists in the project\n'
        #                                         '\n'
        #                                         'do you want to load?'
        #                                         )
        #     if not ok:
        #         ignore = True

        # elif dataLoader.dataFormat == StarDataLoader.dataFormat and dataLoader:
        #     (dataLoader, createNewProject, ignore) = self._queryChoices(dataLoader)
        #     if dataLoader and not ignore:
        #         title = 'New project from NmrStar' if createNewProject else \
        #             'Import from NmrStar'
        #         dataLoader.getDataBlock()  # this will read and parse the file
        #         popup = StarImporterPopup(dataLoader=dataLoader,
        #                                   parent=self.mainWindow,
        #                                   size=(700, 1000),
        #                                   title=title
        #                                   )
        #         popup.exec_()
        #         ignore = (popup.result == popup.CANCEL_PRESSED)

        # elif dataLoader.dataFormat == DirectoryDataLoader.dataFormat and len(dataLoader) > MAXITEMLOGGING:
        #     ok = MessageDialog.showYesNoWarning('Directory "%s"\n' % dataLoader.path,
        #                                         f'\n'
        #                                         'CAUTION: You are trying to load %d items\n'
        #                                         '\n'
        #                                         'Do you want to continue?' % (len(dataLoader, ))
        #                                         )
        #
        #     if not ok:
        #         ignore = True

        return (dataLoader, createNewProject, ignore)

    def _loadData(self, dataLoader) -> list:
        """Load the data defined by dataLoader instance, catching errors
        and suspending sidebar.
        :return a list of loaded opjects
        """
        from ccpn.core.lib.ContextManagers import catchExceptions

        result = []
        errorStringTemplate = 'Loading "%s" failed:' % dataLoader.path + '\n%s'
        with catchExceptions(errorStringTemplate=errorStringTemplate):
            result = dataLoader.load()

        return result

    def loadData(self, *paths, pathFilter=None) -> list:
        """Loads data from paths; query if none supplied
        Optionally filter for dataFormat(s)
        :param *paths: argument list of path's (str or Path instances)
        :param pathFilter: keyword argument: list/tuple of dataFormat strings
        :returns list of loaded objects
        """
        if not paths:
            return []

        dataLoaders = []
        for path in paths:

            _path = aPath(path)
            if not _path.exists():
                txt = f'"{path}" does not exist'
                getLogger().warning(txt)
                if len(paths) == 1:
                    return []
                else:
                    continue

            dataLoader, createNewProject, ignore = self._getDataLoader(path, pathFilter=pathFilter)
            if ignore:
                continue

            if dataLoader is None:
                txt = f'Unable to load "{path}"'
                getLogger().warning(txt)
                if len(paths) == 1:
                    return []
                else:
                    continue

            dataLoaders.append(dataLoader)

        # load the project using the dataLoaders;
        # We'll ask framework who will pass it back as ui._loadData calls
        objs = self.application._loadData(dataLoaders)
        if len(objs) == 0:
            txt = f'No objects were loaded from {paths}'
            getLogger().warning(txt)

        return objs

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
            return False

        newPath = aPath(newPath).assureSuffix(CCPN_EXTENSION)

        if (not overwrite and
                newPath.exists() and
                (newPath.is_file() or (newPath.is_dir() and len(newPath.listdir(excludeDotFiles=False)) > 0))
        ):
            getLogger().warning(f'Path "{newPath}" already exists')
            return False

        # check the project name derived from path
        newName = newPath.basename
        if (_name := checkProjectName(newName, correctName=True)) != newName:
            newPath = (newPath.parent / _name).assureSuffix(CCPN_EXTENSION)
            getLogger().info(f'Project name changed from "{newName}" to "{_name}"\nSee console/log for details',
                             )

        with catchExceptions(errorStringTemplate='Error saving project: %s'):
            try:
                if not self.application._saveProjectAs(newPath=newPath, overwrite=True):
                    getLogger().warning(f"Saving project to {newPath} aborted")
                    return False

            except (PermissionError, FileNotFoundError):
                getLogger().debug(f'Folder {newPath} may be read-only')
                return False

        self.application._getRecentProjectFiles()  # this will update the preferences-list
        getLogger().info(f'Project successfully saved to "{self.project.path}"')

        return True

    @logCommand('application.')
    def saveProject(self) -> bool:
        """Save project.
        :return True if successful
        """
        if self.project.isTemporary:
            return self.saveProjectAs()

        if self.project.readOnly:
            getLogger().info('The project is marked as read-only.')
            return True

        with catchExceptions(errorStringTemplate='Error saving project: %s'):
            try:
                if not self.application._saveProject(force=True):
                    return False
            except (PermissionError, FileNotFoundError):
                getLogger().debug('Folder may be read-only')
                return True

        getLogger().info(f'Project successfully saved to "{self.project.path}"')

        return True


class TestUi(NoUi):

    def __init__(self, application):
        Ui.__init__(self, application)
        application._consoleOutput = []

    def echoCommands(self, commands: typing.List[str]):
        """Echo commands strings, one by one, to logger
        and store them in internal list for perusal
        """
        self.application._consoleOutput.extend(commands)
        logger = getLogger()
        for command in commands:
            logger.echoInfo(command)
