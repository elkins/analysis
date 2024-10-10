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
__dateModified__ = "$dateModified: 2024-10-02 10:04:24 +0100 (Wed, October 02, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2024-09-23 13:17:42 +0100 (Mon, September 23, 2024) $"

#=========================================================================================
# Start of code
#=========================================================================================

import os
from functools import partial
from PyQt5 import QtWidgets, QtGui, QtCore
# don't remove this import!
import ccpn.core
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.FileDialog import DataFileDialog
from ccpn.ui.gui.widgets.ListWidget import ListWidget
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.MessageDialog import showWarning, showYesNoWarning
from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget

from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.lib.GuiPath import PathEdit
from ccpn.framework.PathsAndUrls import CCPN_BACKUPS_DIRECTORY, CCPN_API_DIRECTORY

from ccpn.core.lib.XmlLoader import AUTOBACKUP_SUFFIX, BACKUP_SUFFIX, TEMPBACKUP_SUFFIX
from ccpn.util.Path import aPath
from ccpn.util.Logging import getLogger


COLWIDTH = 140
LineEditsMinimumWidth = 195
DEFAULTSPACING = 3
DEFAULTMARGINS = (14, 14, 14, 14)


class _ListWidget(ListWidget):
    """ListWidget with property that the stretch-factor is determined by the number of rows.
    Gives a cleaner set of listWidgets if one contains only a few items.
    """
    _parentLayout = None
    _parentRow = None
    maxCount = 12

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not ((layout := self.parent().layout()) and
                isinstance(layout, QtWidgets.QGridLayout)):
            # Make sure the correct layout exists
            return
        if (index := layout.indexOf(self)) != -1:
            # Make sure the widget is in the layout
            row, _, _, _ = layout.getItemPosition(index)
            self._parentRow = row
            self._parentLayout = layout

    def paintEvent(self, e):
        # update the stretch on repaint - easier way of signalling this?
        self._setParentStretch()
        super().paintEvent(e)

    def _setParentStretch(self, reset=False):
        """Update the stretch value for the parent-row containing self.
        """
        if not (self._parentLayout and self._parentRow):
            return
        # only update if parameters have been set
        self._parentLayout.setRowStretch(self._parentRow,
                                         0 if reset else max(min(self.count(), self.maxCount), 1))

    def setVisible(self, visible: bool):
        """Subclass to reset the stretch when self is hidden.
        Allows the parent layout to resize correctly.
        """
        if not visible:
            self._setParentStretch(reset=True)
        super().setVisible(visible)


#=========================================================================================
# InspectBackups
#=========================================================================================

class CleanupBackups(CcpnDialogMainWidget):
    """Delete auto-/user-backups.
    """
    FIXEDWIDTH = False
    FIXEDHEIGHT = False

    def __init__(self, parent=None, mainWindow=None, currentProjectOnly=False, **kwds):
        """Initialise the popup.
        """
        super().__init__(parent, setLayout=True, windowTitle='View Backups', **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.project = self.mainWindow.project
            self.projectPath = aPath(self.project.path)
        else:
            self.mainWindow = self.project = self.projectPath = None
        self._currentProjectOnly = currentProjectOnly
        self._lastProject = None

        # set up the popup
        self._setWidgets()
        self._populate()
        self._populateProjectState(True)

        # enable the buttons
        self.setCloseButton(callback=self.reject, tipText='Close dialog')
        self.setDefaultButton(self.CLOSEBUTTON)

    def _setWidgets(self):
        """Set up the widgets for the popup.
        """
        widget = self.mainWidget
        widget.layout().setAlignment(QtCore.Qt.AlignTop)

        row = 0
        self._useCurrentProject = True
        self._validProjectOnly = CheckBoxCompoundWidget(
                widget,
                grid=(row, 0), gridSpan=(1, 2), hAlign='left',
                fixedWidths=(None, 30),
                orientation='left',
                labelText='View current project',
                checked=self._useCurrentProject,
                callback=self._populateProjectState
                )
        self._validProjectOnly.setVisible(not self._currentProjectOnly)

        row += 1
        self._projectLabel = Label(widget, "Project path", grid=(row, 0), )
        self._projectData = PathEdit(widget, grid=(row, 1), vAlign='t')
        self._projectData.setMinimumWidth(LineEditsMinimumWidth)
        self._projectButton = Button(widget, grid=(row, 2),
                                     callback=self._getUserWorkingPath,
                                     icon='icons/directory', hPolicy='fixed')
        self._projectData.textChanged.connect(self._setUserWorkingPath)
        if self._currentProjectOnly:
            self._projectLabel.setVisible(False)
            self._projectData.setVisible(False)
            self._projectButton.setVisible(False)
        self._projectData.setEnabled(not self._useCurrentProject)
        self._projectButton.setEnabled(not self._useCurrentProject)

        row += 1
        self._autoListLabel = Label(widget, "Auto backups", grid=(row, 0))
        self._autoList = _ListWidget(widget, grid=(row, 1), gridSpan=(1, 2), hPolicy='minimum', vPolicy='minimum')
        self._autoList.setDragEnabled(False)
        self._autoList.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum)
        self._autoListLabel.setFixedSize(self._autoListLabel.sizeHint())
        self._autoList.currentContextMenu = partial(self._getContextMenu, widget=self._autoList)
        self._autoList.setToolTip('Current auto-backups in the project.\n'
                                  'Auto-backups are created at regular intervals based on the settings in preferences.')
        self._autoList.setMinimumHeight(48)
        # listWidgets have strange initial sizePolicies
        self._autoList.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        row += 1
        self._userListLabel = Label(widget, "User backups", grid=(row, 0))
        self._userList = _ListWidget(widget, grid=(row, 1), gridSpan=(1, 2), hPolicy='minimum', vPolicy='minimum')
        self._userList.setDragEnabled(False)
        self._userList.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum)
        self._userListLabel.setFixedSize(self._userListLabel.sizeHint())
        self._userList.currentContextMenu = partial(self._getContextMenu, widget=self._userList)
        self._userList.setToolTip('Current user-backups in the project.\n'
                                  'User-backups are added when the project is saved, to the maximum \n'
                                  'number specified in preferences.')
        self._userList.setMinimumHeight(48)
        self._userList.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        row += 1
        self._tempListLabel = Label(widget, "Temporary\nbackups", grid=(row, 0))
        self._tempList = _ListWidget(widget, grid=(row, 1), gridSpan=(1, 2), hPolicy='minimum', vPolicy='minimum')
        self._tempList.setDragEnabled(False)
        self._tempList.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum)
        self._tempListLabel.setFixedSize(self._tempListLabel.sizeHint())
        self._tempList.currentContextMenu = partial(self._getContextMenu, widget=self._tempList)
        self._tempList.setToolTip('Temporary backups to ensure no loss of data when repairing projects.\n'
                                  'These are created from \'Repair from backup\'.\n'
                                  'The current ccpnv3 folder to copied as a temporary-backup to here, and\n'
                                  'the selected backup overwrites the original ccpnv3 folder.')
        self._tempList.setMinimumHeight(24)
        self._tempList.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._tempListLabel.setVisible(False)
        self._tempList.setVisible(False)

    def _populate(self):
        """Fill the lists with auto-/user-backups.
        """
        self._autoList.clear()
        self._userList.clear()
        self._tempList.clear()
        if self._validProject(self.projectPath):
            pp = self.projectPath / CCPN_BACKUPS_DIRECTORY
            auto = pp.listdir(suffix=AUTOBACKUP_SUFFIX)
            self._autoList.addItems([str(fp.name) for fp in sorted(auto)])
            user = pp.listdir(suffix=BACKUP_SUFFIX)
            self._userList.addItems([str(fp.name) for fp in sorted(user)])
            temp = pp.listdir(suffix=TEMPBACKUP_SUFFIX)
            self._tempList.addItems([str(fp.name) for fp in sorted(temp)])
            for idx in range(self._tempList.count()):
                itm = self._tempList.item(idx)
                itm.setForeground(QtGui.QColor('gray'))

        vis = bool(self._tempList.count())
        self._tempListLabel.setVisible(vis)
        self._tempList.setVisible(vis)

    def _populateProjectState(self, value: bool):
        """Respond to user pressing checkbox.
        """
        self._useCurrentProject = value
        self._projectData.setEnabled(not self._useCurrentProject)
        self._projectButton.setEnabled(not self._useCurrentProject)
        if value:
            self._lastProject = self._projectData.text()
            self._projectData.setText(str(self.project.path) if self.project else '')
        else:
            self._projectData.setText(self._lastProject)
        self._populate()

    def _getUserWorkingPath(self):
        """Return the current working path.
        """
        if os.path.exists(os.path.expanduser(self._projectData.text())):
            currentDataPath = os.path.expanduser(self._projectData.text())
        else:
            currentDataPath = os.path.expanduser('~')
        dialog = DataFileDialog(parent=self, directory=currentDataPath, _useDirectoryOnly=True)
        dialog._show()
        directory = dialog.selectedFiles()
        if directory and len(directory) > 0:
            self._projectData.setText(directory[0])

        self._setUserWorkingPath(self._projectData.get())

    def _setUserWorkingPath(self, value: str):
        """Set the current working path.
        """
        value = aPath(value)
        self.projectPath = value
        if self._projectData.validator().checkState == QtGui.QValidator.Acceptable:
            self._populate()

    @staticmethod
    def _validProject(value) -> bool:
        """Return True if the project contains the back-ups folder.
        """
        pth = aPath(value)
        return (pth / CCPN_BACKUPS_DIRECTORY).exists() and (pth / CCPN_BACKUPS_DIRECTORY).is_dir()

    def _getContextMenu(self, widget: ListWidget) -> Menu:
        """Create a new menu.
        Items are enabled as required based on the current selection.
        """
        contextMenu = Menu('', self, isFloatWidget=True)
        dd = contextMenu.addItem("Delete",
                                 callback=partial(self._removeItem, widget=widget))
        rb = contextMenu.addItem("Repair from backup",
                                 callback=partial(self._restoreItem, widget=widget))
        contextMenu.addSeparator()
        cs = contextMenu.addItem("Clear selection",
                                 callback=partial(self._clearSelection, widget=widget))
        selCount = len(widget.selectedItems())
        dd.setEnabled(selCount > 0)
        rb.setEnabled(selCount == 1)
        cs.setEnabled(selCount > 0)
        return contextMenu

    def _removeItem(self, widget: ListWidget):
        """Delete the selected backups from the backup folder.
        Items are NOT recoverable at this time.
        Could possibly use move-to-bin?
        """
        if not widget.selectedItems():
            return
        if not showYesNoWarning('Delete Selected Backups',
                                'Are you sure you want to delete the selected backups?\n'
                                'NOTE: these will be permanently removed.'):
            return

        try:
            for selectedItem in widget.selectedItems():
                fName = selectedItem.data(QtCore.Qt.DisplayRole)
                getLogger().debug(f'Deleting {fName}')
                fp = self.projectPath / CCPN_BACKUPS_DIRECTORY / fName
                getLogger().debug(str(fp))
                # DELETE
                fp.removeDir()
        except (PermissionError, FileNotFoundError):
            getLogger().debug('Delete Selected Backups: folder may be read-only')
        finally:
            self._populate()

    def _restoreItem(self, widget: ListWidget):
        """Repair the selected backup to the project.
        The current ccpnv3 folder is moved to the backups folder with
        suffix TEMPBACKUP_SUFFIX first.
        """
        if not widget.selectedItems():
            return
        if len(widget.selectedItems()) > 1:
            showWarning('Repair from Backup',
                        'Please select a single backup to repair from.')
            return

        if self._useCurrentProject:
            if not showYesNoWarning('Repair from Backup',
                                    'CAUTION: saving the '
                                    'current project will overwrite the repair; \n'
                                    'the project will be locked as a reminder.\n\n'
                                    'Do you want to continue?'):
                return
        else:
            if not showYesNoWarning('Repair from Backup',
                                    'CAUTION: the project ccpnv3 folder will be copied as a temporary-backup; '
                                    'the repair will overwrite the old folder with the selected backup.\n\n'
                                    'Do you want to continue?'):
                return

        try:
            self.project.setReadOnly(True)
            for selectedItem in widget.selectedItems():
                fName = selectedItem.data(QtCore.Qt.DisplayRole)
                getLogger().debug(f'Repairing {fName}')
                fp = self.projectPath / CCPN_BACKUPS_DIRECTORY / fName
                getLogger().debug(str(fp))
                # REPAIR
                # rename the current ccpnv3 folder
                ccpnv3 = self.projectPath / CCPN_API_DIRECTORY
                newCcpnv3 = (self.projectPath / CCPN_BACKUPS_DIRECTORY / CCPN_API_DIRECTORY +
                             TEMPBACKUP_SUFFIX).addTimeStamp()
                os.rename(ccpnv3, newCcpnv3)
                # copy the backup in its place
                fp.copyDir(ccpnv3)
        except (PermissionError, FileNotFoundError):
            getLogger().debug('Repair from Backup: folder may be read-only')
        finally:
            self._populate()

    @staticmethod
    def _clearSelection(widget: ListWidget):
        """Clear the selected rows.
        """
        widget.clearSelection()


#=========================================================================================
# Main
#=========================================================================================

def main():
    from ccpn.ui.gui.widgets.Application import TestApplication

    app = TestApplication()
    popup = CleanupBackups(mainWindow=None, currentProjectOnly=False)
    popup.exec_()


if __name__ == '__main__':
    main()
