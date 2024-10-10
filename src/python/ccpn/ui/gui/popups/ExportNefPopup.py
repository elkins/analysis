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
__dateModified__ = "$dateModified: 2024-09-27 19:06:26 +0100 (Fri, September 27, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2017-07-06 15:51:11 +0000 (Thu, July 06, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.ui.gui.widgets.Spacer import Spacer
from PyQt5 import QtWidgets
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.ProjectTreeCheckBoxes import ExportTreeCheckBoxes
from ccpn.ui.gui.popups.ExportDialog import ExportDialogABC
from ccpn.ui.gui.widgets.FileDialog import NefFileDialog
from ccpn.ui.gui.widgets.MessageDialog import showError


CHAINS = 'chains'
NMRCHAINS = 'nmrChains'
RESTRAINTTABLES = 'restraintTables'
CCPNTAG = 'ccpn'
_SKIPPREFIXES = 'skipPrefixes'
_EXPANDSELECTION = 'expandSelection'
_INCLUDEORPHANS = 'includeOrphans'


class ExportNefPopup(ExportDialogABC):
    """
    Class to handle exporting Nef files
    """

    def __init__(self, parent=None, mainWindow=None, title='Export to File',
                 fileMode='anyFile',
                 acceptMode='export',
                 selectFile=None,
                 fileFilter='*.nef',
                 **kwds):
        """
        Initialise the widget
        """
        super().__init__(parent=parent, mainWindow=mainWindow, title=title,
                         fileMode=fileMode, acceptMode=acceptMode,
                         selectFile=selectFile,
                         fileFilter=fileFilter,
                         **kwds)

        self.setOkButton(callback=self.accept, tipText='Export Nef to File')
        self.setCancelButton(callback=self.reject, tipText='Cancel')

    def initialise(self, userFrame):
        row = 0
        self.buttonCCPN = CheckBox(userFrame, checked=True,
                                   text='include CCPN tags',
                                   grid=(row, 0), hAlign='l')
        row += 1
        self.buttonExpand = CheckBox(userFrame, checked=False,
                                     text='expand selection',
                                     grid=(row, 0), hAlign='l')
        row += 1
        self.buttonOrphans = CheckBox(userFrame, checked=True,
                                      text='include chemicalShift orphans',
                                      grid=(row, 0), hAlign='l')
        row += 1
        self.spacer = Spacer(userFrame, 3, 3,
                             QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                             grid=(row, 0), gridSpan=(1, 1))
        row += 1
        self.treeView = ExportTreeCheckBoxes(userFrame, project=None, grid=(row, 0), includeProject=True)

    def populate(self, userframe):
        """Populate the widgets with project
        """
        try:
            self.treeView.populate(self.project)
        except Exception as es:
            showError('{} Error' % self._dialogAcceptMode.capitalize(), str(es))

    def buildParameters(self):
        """build parameters dict from the user widgets, to be passed to the export method.
        :return: dict - user parameters
        """

        # build the export dict and flags
        self.flags = {_SKIPPREFIXES: []}
        if self.buttonCCPN.isChecked() is False:  # these are negated as they are skipped flags
            self.flags[_SKIPPREFIXES].append(CCPNTAG)
        self.flags[_EXPANDSELECTION] = self.buttonExpand.isChecked()
        self.flags[_INCLUDEORPHANS] = self.buttonOrphans.isChecked()

        # new bit to read all the checked pids (contain ':') from the checkboxtreewidget - don't include project name
        self.newList = self.treeView.getSelectedPids(includeRoot=False)

        # return the parameters
        params = {'filename': self.exitFilename,
                  'flags'   : self.flags,
                  'pidList' : self.newList}
        return params

    def updateDialog(self):
        """Create the Nef dialog
        """
        self.fileSaveDialog = NefFileDialog(self,
                                            acceptMode='export',
                                            selectFile=self._dialogSelectFile,
                                            fileFilter=self._dialogFilter,
                                            confirmOverwrite=False
                                            )

    def exportToFile(self, filename=None, params=None):
        """Export to file
        :param filename: filename to export
        :param params: dict - user defined parameters for export
        """

        # this is empty because the writing is done after
        pass


def main():
    # from sandbox.Geerten.Refactored.framework import Framework
    # from sandbox.Geerten.Refactored.programArguments import Arguments

    # from ccpn.framework.Framework import Framework
    # from ccpn.framework.Framework import Arguments
    #
    # _makeMainWindowVisible = False
    #
    #
    # class MyProgramme(Framework):
    #     """My first app"""
    #     pass
    #
    #
    # myArgs = Arguments()
    # myArgs.interface = 'NoUi'
    # myArgs.debug = True
    # myArgs.darkColourScheme = False
    # myArgs.lightColourScheme = True
    #
    # application = MyProgramme('MyProgramme', '3.0.1', args=myArgs)
    # ui = application.ui
    # ui.initialize(ui.mainWindow)  # ui.mainWindow not needed for refactored?
    #
    # if _makeMainWindowVisible:
    #     # ui.mainWindow._updateMainWindow(newProject=True)
    #     ui.mainWindow.show()
    #     QtWidgets.QApplication.setActiveWindow(ui.mainWindow)
    #
    # # register the programme
    # from ccpn.framework.Application import ApplicationContainer
    #
    #
    # container = ApplicationContainer()
    # container.register(application)
    # application.useFileLogger = True
    #
    # app = QtWidgets.QApplication(['testApp'])
    # # run the dialog
    # dialog = ExportNefPopup(parent=ui.mainWindow, mainWindow=ui.mainWindow)
    # result = dialog.exec_()

    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # need to keep a handle to the app, otherwise garbage collection removes it causing thread crash
    _app = newTestApplication(interface='NoUi')
    application = getApplication()

    dialog = ExportNefPopup(parent=application.ui.mainWindow if application else None)
    dialog.exec_()


if __name__ == '__main__':
    main()
