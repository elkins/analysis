"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-07-11 09:47:42 +0100 (Thu, July 11, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: gvuister $"
__date__ = "$Date: 2018-12-20 15:44:35 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.decorators import singleton
from ccpn.framework.Translation import languages, defaultLanguage
from ccpn.ui import interfaces, defaultInterface


ANALYSIS_ASSIGN = 'AnalysisAssign'
ANALYSIS_SCREEN = 'AnalysisScreen'
ANALYSIS_METABOLOMICS = 'AnalysisMetabolomics'
ANALYSIS_DYNAMICS = 'AnalysisDynamics'
ANALYSIS_STRUCTURE = 'AnalysisStructure'
applicationNames = (ANALYSIS_ASSIGN, ANALYSIS_SCREEN, ANALYSIS_METABOLOMICS, ANALYSIS_STRUCTURE)


def getApplication():
    """Return the application instance"""
    container = ApplicationContainer()
    return container.application


def getProject():
    """Return the active Project instance"""
    container = ApplicationContainer()
    if container.application is not None:
        return container.project


def getCurrent():
    """Return the Current instance"""
    container = ApplicationContainer()
    if container.application is not None:
        return container.current


def getMainWindow():
    """Return the MainWindow instance (if present
    """
    container = ApplicationContainer()
    if container.application is not None:
        return container.mainWindow


@singleton
class ApplicationContainer():
    """A singleton class used to register the application (eg AnalysisScreen)
    and properties defining the top objects application, project, current and
    mainWindow
    """
    application = None

    def register(self, application):
        self.application = application

    @property
    def project(self):
        return self.application.project

    @property
    def current(self):
        return self.application.current

    @property
    def mainWindow(self):
        return self.application.mainWindow


class Arguments:
    """Class for setting FrameWork input arguments directly"""
    language = defaultLanguage
    interface = 'NoUi'
    noLogging = True
    noDebugLogging = False
    noEchoLogging = False
    debug = False
    debug2 = False
    debug3 = False
    debug3_backup_thread = False
    skipUserPreferences = True
    projectPath = None
    _skipUpdates = False

    def __init__(self, projectPath=None, **kwds):

        # Dummy values; GWV: no idea as to what purpose
        for component in applicationNames:
            setattr(self, f'include{component}', None)

        self.projectPath = projectPath
        for tag, val in kwds.items():
            setattr(self, tag, val)


def defineProgramArguments():
    """Define the arguments of the program
    return argparse instance
    """
    import argparse

    parser = argparse.ArgumentParser(description='Process startup arguments')
    # for component in componentNames:
    #   parser.add_argument('--'+component.lower(), dest='include'+component, action='store_true',
    #                                               help='Show %s component' % component.lower())
    parser.add_argument('--language', help=f"Language for menus, etc.; valid options = ({'|'.join(languages)}); default={defaultLanguage}")
    parser.add_argument('--interface', help=f"User interface, to use; one of  = ({'|'.join(interfaces)}); default={defaultInterface}", default=defaultInterface)
    parser.add_argument('--skip-user-preferences', dest='skipUserPreferences', action='store_true',
                        help='Skip loading user preferences')
    parser.add_argument('--dark', dest='darkColourScheme', action='store_true',
                        help='Use dark colour scheme')
    parser.add_argument('--light', dest='lightColourScheme', action='store_true',
                        help='Use dark colour scheme')
    parser.add_argument('--no-logging', dest='noLogging', action='store_true', help='Do not log information to a file')
    parser.add_argument('--no-debug-logging', dest='noDebugLogging', action='store_true', help='Do not log debug information to the terminal')
    parser.add_argument('--no-echo-logging', dest='noEchoLogging', action='store_true', help='Do not log any debug/warning/info messages to the terminal')
    parser.add_argument('--debug', dest='debug', action='store_true', help='Set logging level to debug')
    parser.add_argument('--debug1', dest='debug', action='store_true', help='Set logging level to debug1 (=debug)')
    parser.add_argument('--debug2', dest='debug2', action='store_true', help='Set logging level to debug2')
    parser.add_argument('--debug3', dest='debug3', action='store_true', help='Set logging level to debug3')
    parser.add_argument('--debug3-backup-thread', dest='debug3_backup_thread', action='store_true', help='Display logging for the backup thread when debug3 is enabled')

    # Ccpn logging options - traceback can sometimes be masked in undo/redo
    # --disable-<option>-exception removes the try:except to allow full traceback to occur
    parser.add_argument('--disable-undo-exception', dest='disableUndoException', action='store_true', help='Disable exception wrapping undo/redo actions, reserved for high-level debugging.')
    parser.add_argument('--disable-module-exception', dest='disableModuleException', action='store_true', help='Disable exception wrapping in module updates, reserved for high-level debugging.')
    parser.add_argument('--disable-queue-exception', dest='disableQueueException', action='store_true', help='Disable exception wrapping undo/redo actions, reserved for high-level debugging.')

    parser.add_argument('--read-only', dest='readOnly', action='store_true', help='Set new/loaded projects to read-only.')

    # log information at end of undo/redo if exception occurs (not called if --disable-undo-exception set), calls _logObjects
    parser.add_argument('--ccpn-logging', dest='ccpnLogging', action='store_true', help='Additional logging of some ccpn objects, reserved for high-level debugging.')

    # skip the update check at start-up
    parser.add_argument('--skip-updates', dest='_skipUpdates', action='store_true',
                        help='Skip the initial checking for updates')

    parser.add_argument('projectPath', nargs='?', help='Project path')

    return parser
