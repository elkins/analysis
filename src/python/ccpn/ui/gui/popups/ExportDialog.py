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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-04-04 15:19:22 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2017-07-06 15:51:11 +0000 (Thu, July 06, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore
from typing import Optional
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.FileDialog import ExportFileDialog
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.Spacer import Spacer
from PyQt5 import QtWidgets
from ccpn.ui.gui.widgets.MessageDialog import showYesNoWarning, showWarning, progressManager
from ccpn.ui.gui.guiSettings import getColours, DIVIDER
from ccpn.ui.gui.widgets.HLine import HLine
from ccpn.util.Path import Path, aPath


class ExportDialogABC(CcpnDialogMainWidget):
    """
    Class to handle printing strips to file
    """

    FIXEDHEIGHT = False
    FIXEDWIDTH = False

    _pathHistory = {}

    ACCEPTTEXT = 'Select'
    REJECTTEXT = None
    PATHTEXT = 'Filename'

    def __init__(self, parent=None, mainWindow=None, title='Export to File',
                 fileMode='anyFile',
                 acceptMode='export',
                 selectFile=None,
                 fileFilter='*',
                 **kwds):
        """
        Initialise the widget
        """
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            from ccpn.framework.Application import getApplication

            app = getApplication()
            if app:
                self.application = app
                self.project = app.project
                self.current = app.current
            else:
                self.application = None
                self.project = None
                self.current = None

        if selectFile:
            if not isinstance(selectFile, (str, Path)):
                raise TypeError('selectFile must be str or Path object')
            # change to a Path object
            selectFile = aPath(selectFile)

        self._selectFile = selectFile.name if selectFile else None

        self._dialogFileMode = fileMode
        self._dialogAcceptMode = acceptMode
        self._dialogSelectFile = selectFile
        self._dialogFilter = fileFilter
        self.params = {}
        self.title = title

        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        # the top frame to contain user defined widgets
        self.options = Frame(self.mainWidget, setLayout=True, grid=(0, 0))
        self.options.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # # initialise the frame - check subclassing
        # self.initialise(self.options)

        # add a spacer to separate from the common save widgets
        HLine(self.mainWidget, grid=(2, 0), gridSpan=(1, 1), colour=getColours()[DIVIDER], height=20)

        # file directory options here
        self.openPathIcon = Icon('icons/directory')

        self.saveFrame = Frame(self.mainWidget, setLayout=True, grid=(3, 0))

        self.openPathIcon = Icon('icons/directory')
        self.saveLabel = Label(self.saveFrame, text=f'{self.PATHTEXT}', grid=(0, 0), hAlign='c')
        self.saveText = LineEdit(self.saveFrame, grid=(0, 1), textAlignment='l')
        self.saveText.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.saveText.setDisabled(False)

        self.pathEdited = False
        self.saveText.textEdited.connect(self._editPath)

        self.spacer = Spacer(self.saveFrame, 13, 3,
                             QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                             grid=(0, 2), gridSpan=(1, 1))
        self.pathButton = Button(self.saveFrame, text='',
                                 icon=self.openPathIcon,
                                 callback=self._openFileDialog,
                                 grid=(0, 3), hAlign='c')

        self.buttonFrame = Frame(self.mainWidget, setLayout=True, grid=(9, 0))
        self.spacer = Spacer(self.buttonFrame, 3, 3,
                             QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed,
                             grid=(0, 0), gridSpan=(1, 1))

        # initialise the user frame
        self.initialise(self.options)

        # setup and enable buttons
        self.actionButtons()

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self.updateDialog()
        self._updateButtonText()
        self.setSave(self._dialogSelectFile)

        if self._dialogSelectFile is not None:
            self.setSaveTextWidget(self._dialogSelectFile)
        else:
            self.setSaveTextWidget('')

        # # initialise the user frame
        # self.initialise(self.options)
        # populate the user frame
        self.populate(self.options)

        self._saveState = True

    def actionButtons(self):
        """Set the cancel/export buttons
        """
        self.setOkButton(callback=self._acceptDialog, text=self._dialogAcceptMode.capitalize())
        self.setCancelButton(callback=self._rejectDialog)
        self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

    def getSaveTextWidget(self):
        """Read the contents of the saveText widget and return as a Path
        """
        return aPath(self.saveText.text())

    def setSaveTextWidget(self, value):
        """Write value to the saveText widget
        """
        if value:
            self.saveText.setText(aPath(value).asString())
        else:
            self.saveText.setText('')

    def setSave(self, fileName):
        """Set the save fileName in the dialog shown form the dialog button
        """
        if fileName:

            if not isinstance(fileName, (str, Path)):
                raise TypeError('fileName must be str or Path object')
            fileName = aPath(fileName)

            _currentPath = self.fileSaveDialog.initialPath
            if not _currentPath.is_file():
                if _currentPath:
                    self._dialogSelectFile = _currentPath / fileName.name

                    self._dialogSelectFile = self.setPathHistory(self._dialogSelectFile)
                    self._dialogPath = self._dialogSelectFile.filepath
                else:
                    _currentPath = aPath(self._dialogPreferences.general.userWorkingPath if self._dialogPreferences else '~')
                    self._dialogSelectFile = _currentPath / fileName.name

                    self._dialogSelectFile = self.setPathHistory(self._dialogSelectFile)
                    self._dialogPath = self._dialogSelectFile.filepath
                    self.fileSaveDialog.setInitialFile(self._dialogSelectFile)

                if hasattr(self, 'saveText'):
                    self.setSaveTextWidget(self._dialogSelectFile)
            else:
                raise RuntimeError('Path must be a file')

    def updateDialog(self):
        """Create the dialog for the file button
        To be subclassed as required.
        """
        self.fileSaveDialog = ExportFileDialog(self,
                                            acceptMode='export',
                                            selectFile=self._dialogSelectFile,
                                            fileFilter=self._dialogFilter,
                                            confirmOverwrite=False
                                            )

    def _updateButtonText(self):
        """Change the text of the accept button
        """
        if self.ACCEPTTEXT is not None:
            self.fileSaveDialog.setLabelText(self.fileSaveDialog.Accept, self.ACCEPTTEXT)
        if self.REJECTTEXT is not None:
            self.fileSaveDialog.setLabelText(self.fileSaveDialog.Reject, self.REJECTTEXT)

    def initialise(self, userFrame):
        """Initialise the frame containing the user widgets
        To be overridden when sub-classed by user

        :param userFrame: frame widget to insert user widgets into
        """
        pass

    def populate(self, userFrame):
        """Populate the user widgets
        To be overridden when sub-classed by user

        :param userFrame: user frame widget
        """
        pass

    def buildParameters(self):
        """build parameters dict from the user widgets, to be passed to the export method.
        To be overridden when sub-classed by user

        :return: dict - user parameters
        """
        params = {'filename': self.exitFilename}
        return params

    def exportToFile(self, filename=None, params=None):
        """Export to file
        To be overridden when sub-classed by user

        :param filename: filename to export
        :param params: dict - user defined parameters for export
        """
        pass

    def _acceptDialog(self):
        """save button has been clicked
        """
        self.exitFilename = self.getSaveTextWidget()

        if self.pathEdited is False:
            # user has not changed the path so we can accept()
            self.accept()
        else:
            # have edited the path so check the new file
            if self.exitFilename.is_file():
                yes = showYesNoWarning('%s already exists.' % self.exitFilename,
                                       'Do you want to replace it?')
                if yes:
                    self.accept()
            else:
                if self.exitFilename.is_dir():
                    showWarning('Export Error:', 'Filename must be a file')
                else:
                    self.accept()

    def _rejectDialog(self):
        self.exitFilename = None
        self.reject()

    def closeEvent(self, QCloseEvent):
        """Close the dialog
        """
        self._rejectDialog()

    def _exportToFile(self):
        # build the export dict
        with progressManager(self, 'Saving to file:\n%s' % self.exitFilename):
            params = self.buildParameters()

            # do the export
            if params:
                self.exportToFile(params=params)

            # return the filename
            return params

    def exec_(self) -> Optional[dict]:
        """Popup the dialog
        """
        if super().exec_():
            return self._exportToFile()

    def _openFileDialog(self):
        """Open the save dialog
        """
        # set the path, it may have been edited
        self.fileSaveDialog._selectFile = self._dialogSelectFile
        self.fileSaveDialog.selectFile(str(self._dialogSelectFile))

        self.fileSaveDialog._show()
        _filePath = self.fileSaveDialog.selectedFile()
        if _filePath:
            selectedFile = aPath(_filePath)
            selectedFile = self.setPathHistory(selectedFile)

            if selectedFile:
                self.setSaveTextWidget(selectedFile)
                self._dialogSelectFile = str(selectedFile)
                self.pathEdited = True

    def _save(self):
        self.accept()

    def _editPath(self):
        self.pathEdited = True
        self._dialogSelectFile = self.getSaveTextWidget()
        self._dialogSelectFile = self.setPathHistory(self._dialogSelectFile)

    def updateFilename(self, filename):
        self._dialogSelectFile = self.setPathHistory(filename)
        if hasattr(self, 'saveText'):
            self.setSaveTextWidget(self._dialogSelectFile)

    def getPathHistory(self):
        if self.title in ExportDialogABC._pathHistory:
            return ExportDialogABC._pathHistory[self.title]

        return ''

    def setPathHistory(self, filename: Path):
        if filename:
            filename = aPath(filename)
            if filename.basename:
                ExportDialogABC._pathHistory[self.title] = filename.basename
            else:
                if self.title in ExportDialogABC._pathHistory:
                    filename = ExportDialogABC._pathHistory[self.title] / filename
                else:
                    ExportDialogABC._pathHistory[self.title] = aPath('/')

        else:
            if self.title not in ExportDialogABC._pathHistory:
                ExportDialogABC._pathHistory[self.title] = aPath('/')

        return filename


if __name__ == '__main__':
    # from sandbox.Geerten.Refactored.framework import Framework
    # from sandbox.Geerten.Refactored.programArguments import Arguments
    #
    #
    # _makeMainWindowVisible = False
    #
    #
    # class MyProgramme(Framework):
    #     "My first app"
    #     pass
    #
    #
    # myArgs = Arguments()
    # myArgs.noGui = False
    # myArgs.debug = True
    #
    # application = MyProgramme('MyProgramme', '3.0.0-beta3', args=myArgs)
    # ui = application.ui
    # ui.initialize()
    #
    # if _makeMainWindowVisible:
    #     ui.mainWindow._updateMainWindow(newProject=True)
    #     ui.mainWindow.show()
    #     QtWidgets.QApplication.setActiveWindow(ui.mainWindow)
    #
    # dialog = ExportDialog(parent=application.mainWindow, mainWindow=application.mainWindow)
    # filename = dialog.exec_()

    from ccpn.ui.gui.widgets.Application import newTestApplication


    app = newTestApplication()
    dialog = ExportDialogABC()
    dialog.exec_()
