"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Daniel Thompson $"
__dateModified__ = "$dateModified: 2024-10-03 10:41:26 +0100 (Thu, October 03, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: rhfogh $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
import os
from PyQt5 import QtWidgets, QtCore
from ccpn.util.Path import aPath
from ccpn.util.Common import makeIterableList
from ccpn.util.AttrDict import AttrDict
from ccpn.util.Logging import getLogger
from ccpn.util.decorators import singleton
from ccpn.framework.Application import getApplication


USERDEFAULTPATH = 'userDefaultPath'
USERPROJECTPATH = 'userProjectPath'
USERWORKINGPATH = 'userWorkingPath'
USERDATAPATH = 'dataPath'
USERLAYOUTSPATH = 'userLayoutsPath'
USERMACROPATH = 'userMacroPath'
USERPLUGINPATH = 'userPluginPath'
USERPIPESPATH = 'userPipesPath'
USERAUXILIARYFILESPATH = 'auxiliaryFilesPath'

# keep for the minute - so I can search for it again
# USEREXPORTPATH = 'userExportPath'


ACCEPTMODEDICT = {
    'open'  : QtWidgets.QFileDialog.AcceptOpen,  # 0
    'load'  : QtWidgets.QFileDialog.AcceptOpen,  # 0
    'save'  : QtWidgets.QFileDialog.AcceptSave,  # 1
    'import': QtWidgets.QFileDialog.AcceptOpen,  # 0
    'export': QtWidgets.QFileDialog.AcceptSave,  # 1
    'select': QtWidgets.QFileDialog.AcceptOpen,  # 0
    'run'   : QtWidgets.QFileDialog.AcceptOpen,  # 0
    }

FILEMODESDICT = {
    'anyFile'      : QtWidgets.QFileDialog.AnyFile,  # 0
    'existingFile' : QtWidgets.QFileDialog.ExistingFile,  # 1
    'directory'    : QtWidgets.QFileDialog.Directory,  # 2
    'directoryOnly': QtWidgets.QFileDialog.Directory,  # 2
    'existingFiles': QtWidgets.QFileDialog.ExistingFiles,  # 3
    }

STATICFUNCTIONDICT = {
    (0, 0)                                                                 : 'getOpenFileName',
    (0, 1)                                                                 : 'getOpenFileName',
    (0, 2)                                                                 : 'getExistingDirectory',
    (0, 3)                                                                 : 'getOpenFileNames',
    (1, 0)                                                                 : 'getSaveFileName',
    (1, 1)                                                                 : 'getSaveFileName',
    (1, 2)                                                                 : 'getSaveFileName',
    (1, 3)                                                                 : 'getSaveFileName',
    (QtWidgets.QFileDialog.AcceptOpen, QtWidgets.QFileDialog.AnyFile)      : 'getOpenFileName',
    (QtWidgets.QFileDialog.AcceptOpen, QtWidgets.QFileDialog.ExistingFile) : 'getOpenFileName',
    (QtWidgets.QFileDialog.AcceptOpen, QtWidgets.QFileDialog.Directory)    : 'getExistingDirectory',
    (QtWidgets.QFileDialog.AcceptOpen, QtWidgets.QFileDialog.ExistingFiles): 'getOpenFileNames',
    (QtWidgets.QFileDialog.AcceptSave, QtWidgets.QFileDialog.AnyFile)      : 'getSaveFileName',
    (QtWidgets.QFileDialog.AcceptSave, QtWidgets.QFileDialog.ExistingFile) : 'getSaveFileName',
    (QtWidgets.QFileDialog.AcceptSave, QtWidgets.QFileDialog.Directory)    : 'getSaveFileName',
    (QtWidgets.QFileDialog.AcceptSave, QtWidgets.QFileDialog.ExistingFiles): 'getSaveFileName',
    }


class FileDialogABC(QtWidgets.QFileDialog):
    """
    Class to implement open/save dialogs
    """
    _initialPaths = {}  # for saving last opened directory
    _lastPreferencePaths = {}  # for checking if prefs have changed
    _fileMode = 'anyFile'
    _text = None
    _updatePathOnReject = True
    _multiSelect = False
    restrictDirToFilter = False,

    # path attribute to read from preferences.general dict in __new__
    _initialPath = USERWORKINGPATH

    def __init__(self, parent=None,
                 acceptMode='open',
                 selectFile=None, fileFilter=None, directory=None,
                 useNative=None,
                 _useDirectoryOnly=False,
                 confirmOverwrite=True,
                 **kwds):
        """
        Initialise the dialog widget

        :param parent:
        :param acceptMode: 'open' or 'save'
        :param selectFile: default filename to select - without path
        :param fileFilter: file filter, e.g. '*.zip'
        :param directory: default folder to select
        :param useNative: True/False - use native dialog
        :param confirmOverwrite: True/False - request overwrite if file exists
        :param kwds:
        """

        if _useDirectoryOnly:
            # allow the setting of the directory from the preferences popup
            self._fileMode = 'directoryOnly'
            self._text = ' '.join([self._text, 'Path'])

        # check that the subclass attributes has been defined
        if self._fileMode is None and not self._text:
            raise RuntimeError(f'{self.__class__.__name__} not defined correctly')

        _fm = FILEMODESDICT.get(self._fileMode)
        if _fm is None:
            raise RuntimeError(f'{self.__class__.__name__}: _fileMode \'{self._fileMode}\' not defined')

        _am = ACCEPTMODEDICT.get(acceptMode)
        if _am is None:
            raise TypeError(f'{self.__class__.__name__}: acceptMode \'{acceptMode}\' not defined')

        try:
            # read the preferences from the application
            application = getApplication()
            self._preferences = application.preferences
            _general = self._preferences.general
        except:
            if directory is None:  # Directory can be set correctly in the Widget. Use default only if everything else fails.
                directory = aPath('~')
                # raise RuntimeError('application is not defined')
                getLogger().debug('application is not defined')

        if directory is None:
            _path = aPath(_general.get(self._initialPath))
            if not _path:
                raise RuntimeError(f'preferences.general.{self._initialPath} not defined correctly')

            # set the current working path if this is the first time the dialog has been opened
            if self._clsID not in self._initialPaths:
                self._initialPaths[self._clsID] = _path
                self._lastPreferencePaths[self._clsID] = _path

            # added in rare case that clsID exists for _initalPaths but not _lastPreferencePaths.
            if self._clsID not in self._lastPreferencePaths:
                self._lastPreferencePaths[self._clsID] = _path

            directory = self._initialPaths[self._clsID]
            self._setDirectory = False

            if self._lastPreferencePaths[self._clsID] != _path:
                self._initialPaths[self._clsID] = _path
                self._lastPreferencePaths[self._clsID] = _path
                directory = self._initialPaths[self._clsID]

        else:
            directory = directory
            # not sure why I put this flag in
            self._setDirectory = True

        self._directory = directory

        _txt = self._text.format(acceptMode) if '{}' in self._text else self._text
        _txt = _txt[0].capitalize() + _txt[1:]
        super().__init__(parent, caption=_txt, directory=str(directory), **kwds)

        if not confirmOverwrite:
            self.setOption(QtWidgets.QFileDialog.DontConfirmOverwrite)

        try:
            if self._fileMode == 'directoryOnly':
                # fix obsolete DirectoryOnly
                self.setOption(self.ShowDirsOnly, True)
        except:
            pass

        self._kwds = kwds
        self._selectFile = aPath(selectFile).name if selectFile else None

        self.setFileMode(_fm)
        self._customMultiSelectedFiles = []  #used to multiselect directories and files at the same time. Available only on Non Native
        # self._multiSelect = multiSelection

        self._acceptMode = ACCEPTMODEDICT.get(acceptMode)
        self.setAcceptMode(self._acceptMode)

        if fileFilter is not None:
            self.setNameFilter(fileFilter)
        if selectFile is not None:
            # populates fileDialog with the suggested filename
            self.selectFile(self._selectFile)

        if useNative is not None:
            self.useNative = useNative
        else:
            try:
                self.useNative = self._preferences.general.useNative
            except:
                self.useNative = True

        # need to do this before setting DontUseNativeDialog (only for non-native?)
        if self.restrictDirToFilter:
            self.filterSelected.connect(self._predir)
            self.directoryEntered.connect(self._dir)
            self._restrictedType = fileFilter

        # self.result is '' (first case) or 0 (second case) if Cancel button selected
        if self.useNative and not sys.platform.lower() == 'linux':

            pass

            # # get the function name from the dict above
            # funcName = self.staticFunctionDict[(acceptMode, fileMode)]
            # self.result = getattr(self, funcName)(caption=text, **kwds)
            # if isinstance(self.result, tuple):
            #     self.result = self.result[0]
        else:
            self.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, not self.useNative)

            # add a multi-selection option - only for non-native dialogs
            for view in self.findChildren((QtWidgets.QListView, QtWidgets.QTreeView)):
                if isinstance(view.model(), QtWidgets.QFileSystemModel):

                    # set the selection mode for the dialog
                    if self._multiSelect:
                        view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
                    else:
                        view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

            btns = self.findChildren(QtWidgets.QPushButton)
            if btns:
                # search for the open button and connect to the clicked signal
                self.openBtn = [x for x in btns if 'open' in str(x.text()).lower()]
                if self.openBtn:
                    self.openBtn[0].clicked.disconnect()
                    self.openBtn[0].clicked.connect(self._openClicked)

        # NOTE:ED - exec separated from the _init__ to stop threading issues with Windows 10
        #           _show or exec_ must be called after creating a subclassed FileDialogABC object

    @property
    def _clsID(self):
        # returns an id for the current class type for use in storing path
        return self.__class__.__name__

    def getCurrentWorkingPath(self):
        # get the current stored path for this dialog type
        if self._clsID in self._initialPaths:
            return self._initialPaths[self._clsID]

    @property
    def initialPath(self):
        """The initial path that the dialog will be set to on opening.
        Path is stored between instances, and is unique to the subclassed type.
        """
        if self._clsID in self._initialPaths:
            return self._initialPaths[self._clsID]

    @initialPath.setter
    def initialPath(self, value):
        if self._clsID in self._initialPaths:
            self._initialPaths[self._clsID] = value

    def _storePaths(self):
        """Store the current path set - possibly for undo/redo cancelled
        """
        self._tempPaths = self._initialPaths.copy()

    def _restorePaths(self):
        """Restore the current path set - possibly for undo/redo cancelled
        """
        if getattr(self, '_tempPaths', None):
            # keeps the original pointer
            self._initialPaths.clear()
            self._initialPaths.update(self._tempPaths)

    def _show(self):
        """Separated from the _init__ to stop threading issues with Windows 10.
        Must be called after creating a subclassed FileDialogABC object.
        """
        if self.useNative and not sys.platform.lower() == 'linux':
            _fm = FILEMODESDICT.get(self._fileMode)
            funcName = STATICFUNCTIONDICT[(self._acceptMode, _fm)]

            self.result = getattr(self, funcName)(caption=self._text, directory=str(self._directory), **self._kwds)
            if isinstance(self.result, tuple):
                self.result = self.result[0]
        else:
            self.setOption(QtWidgets.QFileDialog.DontUseNativeDialog)
            self.result = self.exec_()

        if self.selectedFiles():
            # empty assumes that the dialog has been rejected
            self._updateCurrentPath()

    def _updateCurrentPath(self):
        """Update the current path
        """
        # accept the dialog and set the current selected folder for next time if directory not originally set
        if self._fileMode == 'directoryOnly':
            absPath = aPath(self.selectedFile())
        else:
            absPath = aPath(self.directory().absolutePath())
        self._initialPaths[self._clsID] = absPath

    def accept(self):
        """Update the current path and exit the dialog.
        """
        self._updateCurrentPath()
        super().accept()

    def reject(self):
        """Update the current path (if required) and exit the dialog.
        """
        self.selectedFiles = lambda: None  # needs to clear the selection when closing
        if self._updatePathOnReject:
            self._updateCurrentPath()
        super().reject()

    def _predir(self, file: str):
        if file.endswith(str(self._restrictedType)):
            self.fileSelected = None

    def _dir(self, directory: str):
        if directory.endswith(str(self._restrictedType)):
            return False

        return True

    def _openClicked(self):
        """Custom action to multiselect files and dir at the same time or just Dirs or just Files. Needed to open a top dir
        containing the spectra. Eg 10 Brukers at once.
        """
        self.tree = self.findChild(QtWidgets.QTreeView)
        if self.tree:
            inds = self.tree.selectionModel().selectedIndexes()
            files = []
            for i in inds:
                if i.column() == 0:
                    files.append(os.path.join(str(self.directory().absolutePath()), str(i.data())))
            self._customMultiSelectedFiles = files

            # NOTE:ED - does this need to hide here?
            self.hide()

    # overrides Qt function, which does not pay any attention to whether Cancel button selected
    def selectedFiles(self):
        """Return the list of selected files
        """
        if self.useNative and not sys.platform.lower() == 'linux':
            # get the selected files from the native dialog
            if self.result:
                return makeIterableList(self.result)
            else:
                return []
        else:
            # use our ccpn dialog
            files = super().selectedFiles()
            if files is None:
                files = []
            return files

    def selectedFile(self):
        """Return the first selected file.
        """
        # Qt does not have this but useful if you know you only want one file
        files = self.selectedFiles()
        if files and len(files) > 0:
            return files[0]
        else:
            return None


# Define the subclasses for each dialog

class ProjectFileDialog(FileDialogABC):
    _fileMode = 'directory'
    _text = '{} Project'

    def _updateCurrentPath(self):
        """Update the current path for here and the ProjectSaveFileDialog
        """
        # accept the dialog and set the current selected folder for next time,
        # if directory not originally set
        super()._updateCurrentPath()

        # copy the value to the ProjectSaveFileDialog
        absPath = aPath(self.directory().absolutePath())
        self._initialPaths[ProjectSaveFileDialog()._clsID] = absPath


class ProjectSaveFileDialog(FileDialogABC):
    # _fileMode = 'directory'
    _text = '{} Project'

    def _updateCurrentPath(self):
        """Update the current path for here and the ProjectFileDialog
        """
        # accept the dialog and set the current selected folder for next time,
        # if directory not originally set
        super()._updateCurrentPath()

        # copy the value to the ProjectFileDialog
        absPath = aPath(self.directory().absolutePath())
        self._initialPaths[ProjectFileDialog()._clsID] = absPath


class DataFileDialog(FileDialogABC):
    _text = '{} Data'


class LayoutsFileDialog(FileDialogABC):
    _initialPath = USERLAYOUTSPATH
    _text = '{} Layout'


class MacrosFileDialog(FileDialogABC):
    _initialPath = USERMACROPATH
    _text = '{} Macro'


class CcpnMacrosFileDialog(FileDialogABC):
    _text = '{} CCPN Macro'


class NefFileDialog(FileDialogABC):
    _text = '{} Nef File'


class ArchivesFileDialog(FileDialogABC):
    _text = '{} Archive'


class PluginsFileDialog(FileDialogABC):
    _initialPath = USERPLUGINPATH
    _text = '{} Plugin'


class PreferencesFileDialog(FileDialogABC):
    _text = '{} Preferences'


class SpectrumFileDialog(FileDialogABC):
    # _initialPath = USERDATAPATH
    _text = '{} Spectra'
    _fileMode = 'existingFiles'
    _multiSelect = True


class TablesFileDialog(FileDialogABC):
    _text = '{} Table'


class BackupsFileDialog(FileDialogABC):
    _text = '{} Backup'


class AuxiliaryFileDialog(FileDialogABC):
    _initialPath = USERAUXILIARYFILESPATH
    _text = '{} Auxiliary File'


class PipelineFileDialog(FileDialogABC):
    _initialPath = USERPIPESPATH
    _text = '{} Pipeline'


class NMRStarFileDialog(FileDialogABC):
    _text = '{} NMRStar File'


class OtherFileDialog(FileDialogABC):
    _text = '{} File'


class PDFFileDialog(FileDialogABC):
    _text = '{} PDF Document'


class ExportFileDialog(FileDialogABC):
    _text = '{} as'


class ExcelFileDialog(FileDialogABC):
    _text = '{} Excel File'


class ChemCompFileDialog(FileDialogABC):
    _text = '{} Xml File'


class ExecutablesFileDialog(FileDialogABC):
    _text = '{} Executable'


class AdminFileDialog(FileDialogABC):
    _text = '{} Files'
    _fileMode = 'existingFiles'
    _multiSelect = True


class LineButtonFileDialog(FileDialogABC):
    """Special class for a lineEdit button in pipelines
    """

    def __init__(self, parent=None,
                 fileMode='anyFile',
                 dialogText=None,
                 directory=None,
                 fileFilter=None,
                 **kwds):
        self._fileMode = fileMode
        self._text = dialogText
        super().__init__(parent, fileFilter=fileFilter, directory=directory, **kwds)


from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.Widget import Widget
from os.path import expanduser


class LineEditButtonDialog(Widget):
    def __init__(self, parent, textDialog=None, textLineEdit=None, fileMode=None, fileFilter=None,
                 directory=None, lineEditMinimumWidth=100, **kwds):

        super().__init__(parent, setLayout=True, **kwds)
        self.openPathIcon = Icon('icons/directory')

        self.textDialog = 'Select File' if textDialog is None else textDialog
        self.textLineEdit = expanduser("~") if textLineEdit is None else textLineEdit
        self.fileMode = 'anyFile' if fileMode is None else fileMode
        self.fileFilter = fileFilter
        self.directory = directory

        tipText = 'Click the icon to select'
        self.lineEdit = LineEdit(parent=self, text=self.textLineEdit,
                                 textAlignment='l',
                                 tipText=tipText, grid=(0, 0))
        self.lineEdit.setEnabled(True)
        button = Button(parent=self, text='', icon=self.openPathIcon, callback=self._openFileDialog, grid=(0, 1),
                        )
        button.setStyleSheet("border: 0px solid transparent")

    def _openFileDialog(self):
        self.fileDialog = LineButtonFileDialog(self, fileMode=self.fileMode, dialogText=self.textDialog,
                                               directory=self.directory, fileFilter=self.fileFilter)
        self.fileDialog._show()
        selectedFile = self.fileDialog.selectedFile()
        if selectedFile:
            self.lineEdit.setText(str(selectedFile))
            return True
        else:
            return False

    def getText(self):
        return self.get()

    def get(self):
        return self.lineEdit.text()

    def set(self, text):
        self.setText(str(text))

    def setText(self, text):
        self.lineEdit.setText(str(text))

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.get()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.set(value)



if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog


    app = TestApplication()
    popup = CcpnDialog(windowTitle='Test LineEditButtonDialog')
    slider = OtherFileDialog(parent=popup)
    print(slider.selectedFile())

    popup.show()
    popup.raise_()
    app.start()
