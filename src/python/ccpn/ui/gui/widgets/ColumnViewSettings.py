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
__dateModified__ = "$dateModified: 2024-11-15 19:34:29 +0000 (Fri, November 15, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2018-12-20 15:44:35 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
from PyQt5 import QtGui, QtCore, QtWidgets
from functools import partial
from collections import OrderedDict

from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.ProjectTreeCheckBoxes import ColumnTreeView
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.core.lib.DataFrameObject import DataFrameObject
from ccpn.ui.gui.widgets.table.TableABC import TableABC
from ccpn.ui.gui.widgets.table._TableAdditions import TableHeaderMenuColumns, TableHeaderMenuCoreColumns
from ccpn.ui.gui.lib._CoreTableFrame import _CoreTableWidgetABC


_LINK_COLUMNS = 'linkColumns'

#=========================================================================================
# ColumnViewSettings - handlers/proxies/etc.
#=========================================================================================

SEARCH_MODES = ['Literal', 'Case Sensitive Literal', 'Regular Expression']
CheckboxTipText = 'Select column to be visible on the table.'


class _TreeProxyStyle(QtWidgets.QProxyStyle):
    """Class to handle resizing icons in menus
    """

    def drawPrimitive(self, element: QtWidgets.QStyle.PrimitiveElement,
                      option: QtWidgets.QStyleOption,
                      painter: QtGui.QPainter,
                      widget: QtWidgets.QWidget | None = ...) -> None:
        if element in {QtWidgets.QStyle.PE_IndicatorCheckBox}:
            # need to fix the background and border if tables are transparent
            #   - in QTableView and QTreeView
            option.palette.setColor(option.palette.Base, QtGui.QPalette().base().color())
            option.palette.setColor(option.palette.Background, QtGui.QPalette().dark().color())
        super().drawPrimitive(element, option, painter, widget)


#=========================================================================================
# ColumnViewSettings
#=========================================================================================


class ColumnViewSettings(Frame):
    """A treeView of checkboxes corresponding to the table-columns.
    """
    _tableView: TableABC = None
    _tableHandler: TableHeaderMenuColumns = None

    def __init__(self, parent,
                 view: TableABC = None, tableHandler: TableHeaderMenuColumns = None,
                 dfObject: pd.DataFrame | DataFrameObject = None,
                 **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        # only need the pd.DataFrame
        if isinstance(dfObject, DataFrameObject):  # need to get rid of DataFrameObject :|
            self._df = dfObject.dataFrame
        elif isinstance(dfObject, pd.DataFrame):
            self._df = dfObject
        else:
            raise ValueError(f'dfObject is the wrong type - {type(dfObject)}')

        self._tableView = view
        self._tableHandler = tableHandler  # check this :|
        self._hideColumnWidths = {}
        self._userColumns = None
        self._setWidgets()

    def _setWidgets(self):

        self._userColumns = OrderedDict([(col, rr) for col, rr in enumerate(self._df.columns)
                                         if not self._tableView.isColumnInternal(col)])
        dfCol = pd.DataFrame(self._userColumns.values())

        row = 0
        self.filterLabel = Label(self, text='Display Columns', grid=(row, 0))
        row += 1
        self._tree = ColumnTreeView(parent=self, df=dfCol,
                                    multiSelect=True, enableMouseMenu=True, enableCheckBoxes=True,
                                    grid=(row, 0), gridSpan=(1, 2)
                                    )
        txts = ['Check All', 'Uncheck All']
        tips = ['Check all columns',
                'Uncheck all columns']
        callbacks = [partial(self._tree._checkAll, True), partial(self._tree._checkAll, False)]
        row += 1
        self._buttonList = ButtonList(self, texts=txts, callbacks=callbacks, toolTips=tips,
                                      grid=(row, 0), gridSpan=(1, 1))
        # self._buttonList.setContentsMargins(100, 16, 0, 0)
        row += 1
        self._linkedColumns = CheckBox(self, text='Link similar columns', grid=(row, 0), gridSpan=(1, 3))
        # only required for multi-index tables
        self._linkedColumns.setVisible(isinstance(self._df.columns, pd.MultiIndex))

        self._initCheckBoxes()
        # connect signal after teh checkboxes have been populated
        self._tree.checkStateChanged.connect(self._itemChecked)
        row += 1
        return row

    def _initCheckBoxes(self):

        self._userColumns = OrderedDict([(col, rr) for col, rr in enumerate(self._df.columns)
                                         if not self._tableView.isColumnInternal(col)])
        for idx, (col, colName) in enumerate(self._userColumns.items()):
            self._tree._setCheckState(idx, not self._tableView.horizontalHeader().isSectionHidden(col))

    def _itemChecked(self, item):
        if item.childCount():
            return
        # a child-item so corresponds to a real column in the table
        rr, _cc, _rSpan, _cSpan = item.data(0, QtCore.Qt.UserRole)
        idx, colName = list(self._userColumns.items())[rr]

        if self._linkedColumns.isChecked():
            # only allow linking of items at the bottom of a branch
            idxs = [_idx for _idx, _colName in self._userColumns.items()
                    if _colName[-1] == colName[-1]]
        else:
            idxs = [idx]
        if bool(item.checkState(0)):
            for idx in idxs:
                self._tableView.showColumn(idx)
        else:
            # visibility of last remaining column is handled by the tree-widget
            for idx in idxs:
                self._tableView.hideColumn(idx)

        # refresh tree-view from columns
        if len(idxs) > 1:
            # more columns may have been shown/hidden
            self._initCheckBoxes()

    @property
    def linkedColumns(self):
        return self._linkedColumns.isChecked()

    @linkedColumns.setter
    def linkedColumns(self, value):
        self._linkedColumns.setChecked(value)


#=========================================================================================
# ColumnViewSettingsPopup
#=========================================================================================

class ColumnViewSettingsPopup(CcpnDialogMainWidget):
    """Popup containing column-view-settings widget to show/hide columns.
    """
    FIXEDHEIGHT = False
    FIXEDWIDTH = True

    _ColumnViewKlass = ColumnViewSettings

    def __init__(self, tableHandler: TableHeaderMenuColumns, dataFrameObject: pd.DataFrame | DataFrameObject = None,
                 parent: QtWidgets.QTableView = None,
                 title='Column Settings', **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, minimumSize=(250, 250), **kwds)

        self._tableView = parent
        self._setWidgets(tableHandler, dataFrameObject)  # dataFrameObject needs to go! :|

        self.setCloseButton(callback=self._close, tipText='Close')
        self.setDefaultButton(self.CLOSEBUTTON)

    def _setWidgets(self, tableHandler: TableHeaderMenuColumns, dataFrameObject: pd.DataFrame):
        """Set up the widgets.
        """
        self._columnViewSettingsWidget = self._ColumnViewKlass(self.mainWidget,
                                                               view=self._tableView,
                                                               tableHandler=tableHandler,
                                                               dfObject=dataFrameObject,
                                                               grid=(0, 0))

    def _close(self):
        """Save the hidden-columns to the table class, so it remembers when you re-open the popup.
        """
        self.accept()

    def _cleanupDialog(self):
        """Clean up widgets that are causing seg-fault on garbage-collection.
        """
        # NEED to be cleaned, causes a threading error if not deleted :|
        self._columnViewSettingsWidget.deleteLater()

    def storeWidgetState(self):
        """Store the state of widgets between popups.
        """
        linked = self._columnViewSettingsWidget.linkedColumns
        ColumnViewSettingsPopup._storedState[_LINK_COLUMNS] = linked

    def restoreWidgetState(self):
        """Restore the state of widgets.
        """
        self._columnViewSettingsWidget.linkedColumns = ColumnViewSettingsPopup._storedState.get(_LINK_COLUMNS, False)


#=========================================================================================
# ColumnViewCoreSettings
#=========================================================================================


class ColumnViewCoreSettings(ColumnViewSettings):
    """A treeView of checkboxes corresponding to the table-columns.
    Additional functionality to allow save/restore/reset to preferences.
    """
    _tableView: _CoreTableWidgetABC = None
    _tableHandler: TableHeaderMenuCoreColumns = None

    def _setWidgets(self):
        row = super()._setWidgets()

        txts = ['Save', 'Restore', 'Clear']
        tips = ['Save the current visible columns to user-preferences;\n'
                'new tables will open from the saved state.',
                'Restore the visible/hidden columns from the\n'
                'saved state for this table',
                'Clear the current saved visible/hidden columns;\n'
                'new tables will open with the default state for this table']
        callbacks = [self._saveHiddensColumns, self._restoreHiddenColumns, self._resetHiddenColumns]
        row += 1
        self._columnsButtonList = ButtonList(self, texts=txts, callbacks=callbacks, toolTips=tips,
                                             grid=(row, 0), gridSpan=(1, 2))
        self._check()

    def _saveHiddensColumns(self):
        self._tableView.saveToPreferences()
        self._check()

    def _restoreHiddenColumns(self):
        self._tableView.restoreFromPreferences()
        # repopulate
        self._initCheckBoxes()

    def _resetHiddenColumns(self):
        self._tableView.resetPreferences()
        # repopulate
        self._initCheckBoxes()

    def _itemChecked(self, item):
        super()._itemChecked(item)
        self._check()

    def _check(self):
        save, restore, reset = self._columnsButtonList.buttons
        state = self._tableView.hasPreferenceState()
        if not state:
            save.setEnabled(True)
            restore.setEnabled(False)
            reset.setEnabled(False)
            return
        if (match := self._tableView.isMatchingPreferenceState()) is not None:
            save.setEnabled(not match)
            restore.setEnabled(not match)
            reset.setEnabled(True)
            return
        for btn in {save, restore, reset}:
            btn.setEnabled(False)


#=========================================================================================
# ColumnViewCoreSettingsPopup
#=========================================================================================

class ColumnViewCoreSettingsPopup(ColumnViewSettingsPopup):
    """Popup containing column-view-settings widget to show/hide columns.
    Additional functionality to allow save/restore/reset to preferences.
    """

    _ColumnViewKlass = ColumnViewCoreSettings
