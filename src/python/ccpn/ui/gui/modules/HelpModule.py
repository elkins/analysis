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
__dateModified__ = "$dateModified: 2025-01-07 16:56:21 +0000 (Tue, January 07, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date:  2023-06-23 09:48:58 +0100 (Fri, June 23, 2023) $"

#=========================================================================================
# Start of code
#=========================================================================================

import ccpn.core
from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.widgets.TextEditor import  TextBrowser
from ccpn.util.Logging import getLogger

logger = getLogger()

DEFAULTSPACING = (0, 0)
DEFAULTMARGINS = (0, 0, 0, 0)  # l, t, r, b


class HelpModule(CcpnModule):
    """
    Warning: This module is under-development.
    """
    includeSettingsWidget = False
    maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    settingsPosition = 'top'

    className = 'HelpModule'
    _includeInLastSeen = False


    def __init__(self, mainWindow, parentModuleName, name='Help Browser',
                 htmlFilePath=None, ):
        """
        Initialise the widgets for the module.
        :param mainWindow: required
        :param parentModuleName: required. so that is the module is opened only once
        :param name: optional
        :param htmlFilePath: leave as None to let window handle item selection
        """
        super().__init__(mainWindow=mainWindow, name=name, htmlFilePath=htmlFilePath)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = None
            self.project = None
            self.current = None

        self.parentModuleName = parentModuleName
        self.htmlFilePath = htmlFilePath
        # setup the widgets
        self.webBrowserWidget = TextBrowser(self.mainWidget, htmlFilePath=self.htmlFilePath, grid=(0, 0), )

        #  No point in showing the help icon for the help module
        self._hideHelpButton()

    def setHtmlFilePath(self, htmlFilePath):
        self.htmlFilePath = htmlFilePath
        self.webBrowserWidget.setHtmlFilePath(self.htmlFilePath)

    # def goHome(self):
    #     self.webBrowserWidget.goHome()
    #
    # def forward(self):
    #     self.webBrowserWidget.forward()
    #
    # def back(self):
    #     self.webBrowserWidget.back()
    #
    # def reload(self):
    #     self.webBrowserWidget.reload()
    #
    # def stop(self):
    #     self.webBrowserWidget.stop()

    def _processDroppedItems(self, data):
        """
        CallBack for Drop events
        """
        pass


if __name__ == '__main__':

    from PyQt5 import QtGui, QtWidgets
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.widgets.CcpnModuleArea import CcpnModuleArea


    htmlFilePath = '/Users/luca/Projects/AnalysisV3/tutorials/html_files/MacroWritingObjectsMethods.html'
    app = TestApplication()
    win = QtWidgets.QMainWindow()
    moduleArea = CcpnModuleArea(mainWindow=None)
    module = HelpModule(mainWindow=None,  parentModuleName='ff')
    module.setHtmlFilePath(htmlFilePath)
    moduleArea.addModule(module)
    win.setCentralWidget(moduleArea)
    win.resize(1000, 500)
    win.setWindowTitle('Testing %s' % module.moduleName)
    win.show()
    app.start()
