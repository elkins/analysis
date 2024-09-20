"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2024-08-23 19:21:17 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QTimer
from ccpn.util.Logging import getLogger


logger = getLogger()

##QT_MAC_WANTS_LAYER: Patch for MacOS >= 11. Without this flag, Testing widgets/windows from PyQt5 don't show at all.
# Edit: 26-06-2023 With this flag set the QtWebEngine doesn't show/load the html page.
os.environ['QT_MAC_WANTS_LAYER'] = '1'


class Application(QtWidgets.QApplication):
    progressAboutToChangeSignal = QtCore.pyqtSignal(int)
    progressChangedSignal = QtCore.pyqtSignal(int)
    # application light/dark/auto, colour-name, spectrumDisplay theme
    sigPaletteChanged = QtCore.pyqtSignal(object, str, str, str)
    _sigPaletteChanged = QtCore.pyqtSignal(object, str, str, str)

    def __init__(self, applicationName, applicationVersion, organizationName='CCPN', organizationDomain='ccpn.ac.uk'):
        super().__init__([applicationName, ])

        self.setApplicationVersion(applicationVersion)
        self.setOrganizationName(organizationName)
        self.setOrganizationDomain(organizationDomain)

    def start(self):
        self.exec_()

    @QtCore.pyqtSlot(object)
    def runFunctionOnThread(self, func):
        logger.debug3(f'run function on main thread {func}')
        func()

    @QtCore.pyqtSlot(object)
    def runFunctionOnThreadAtIdle(self, func):
        logger.debug3(f'run function on main thread at idle {func}')
        timer = QTimer(self)
        timer.timeout.connect(func)
        timer.setSingleShot(True)
        timer.start(0)


class TestApplication(Application):

    def __init__(self):
        Application.__init__(self, 'testApplication', '1.0')


def newTestApplication(projectPath=None, useTestProjects=False, skipUserPreferences=True,
                       noLogging=False, noDebugLogging=False, noEchoLogging=False,
                       interface='NoUi', debug=True,
                       noApplication=False):
    """Create a full application for testing.
    This will contain an empty project and preferences.

    If interface is specified as 'NoUi' no mainWindow will be created,
    but a full application and project will be created.

    if interface is specified as 'Gui' a mainWindow will be created,
    but the event execution loop will not be started.

    Popups can be instantiated with exec_ which will automatically show the mainWindow.

    The mainWindow can be instantiated manually with app.start(); however, any code after this cannot be guaranteed to
    run after closing mainWindow.

    Set noApplication=True for a basic test that only creates a QApplication; a Ccpn application will not be created.

    :param projectPath: str or Path object, path of project to load on startup
    :param useTestProjects: bool, True uses the Ccpn testing folder as the root for the project to load
    :param noLogging: bool, enable or disable logging to file
    :param noDebugLogging: bool, enable or disable logging debug statements
    :param noEchoLogging: bool, enable or disable logging all statements debug/info/warning
    :param interface: 'NoUi' or 'Gui', determines whether mainWindow is created
    :param debug: bool, enable/disable debugging
    :param noApplication: bool, enable/disable creation of CCpn application
    :return: instance of new application
    """
    app = None

    def _makeApp():
        # create a new application
        _app = TestApplication()
        _app.colourScheme = 'light'

        return _app

    # don't create anything else - for the fastest testing
    if noApplication:
        return _makeApp()

    from ccpn.framework import Framework
    from ccpn.util.Path import Path, aPath
    from ccpnmodel.ccpncore.testing.CoreTesting import TEST_PROJECTS_PATH

    app = _makeApp()

    if not isinstance(useTestProjects, bool):
        raise TypeError('useProjects must be a bool')
    if not isinstance(skipUserPreferences, bool):
        raise TypeError('skipUserPreferences must be a bool')
    if not isinstance(noLogging, bool):
        raise TypeError('noLogging must be a bool')
    if not isinstance(noDebugLogging, bool):
        raise TypeError('noDebugLogging must be a bool')
    if not isinstance(noEchoLogging, bool):
        raise TypeError('noEchoLogging must be a bool')

    if interface not in ['NoUi', 'Gui']:
        raise TypeError('interface must be NoUi|Gui')
    if not isinstance(debug, bool):
        raise TypeError('debug must be a bool')

    # check if a projectPath has been specified
    if projectPath is not None:
        if not isinstance(projectPath, (str, Path)):
            raise TypeError('projectPath must be str or Path object')
        projectPath = aPath(projectPath)

        if useTestProjects:
            # if useTestProjects is True then prefix with the test project folder
            projectPath = TEST_PROJECTS_PATH / projectPath

    if interface == 'Gui':
        # store temporary variable so that the qtApp event execution loop can be skipped
        # allows flow to continue after creation of mainWindow
        import builtins

        builtins._skipExecuteLoop = True

    # build new ccpn application/project
    app._framework = Framework.createFramework(projectPath=projectPath, noLogging=noLogging,
                                               noDebugLogging=noDebugLogging,
                                               noEchoLogging=noEchoLogging,
                                               _skipUpdates=True,
                                               skipUserPreferences=skipUserPreferences,
                                               interface=interface, debug=debug,
                                               lightColourScheme=True, darkColourScheme=False)
    _project = app._framework.project
    if _project is None:
        raise RuntimeError(f"No project found for project path {projectPath}")

    # initialise the undo stack
    _project._resetUndo(debug=True, application=app._framework)
    _project._undo.debug = True

    # app.project = _project  # why? just store framework
    # return the new project
    return app


if __name__ == '__main__':
    qtApp = TestApplication()
    w = QtWidgets.QWidget()
    w.resize(250, 150)
    w.move(300, 300)
    w.setWindowTitle('testApplication')
    w.show()

    qtApp.start()
