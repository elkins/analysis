"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2025-01-14 15:29:18 +0000 (Tue, January 14, 2025) $"
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
from ccpn.ui.gui.widgets.HLine import LabeledHLine
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.core.lib.DataFrameObject import DataFrameObject
from ccpn.ui.gui.widgets.Spacer import Spacer
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
    """
    Custom proxy style for handling resizing of icons in menus.
    """

    def drawPrimitive(self,
                      element: QtWidgets.QStyle.PrimitiveElement,
                      option: QtWidgets.QStyleOption,
                      painter: QtGui.QPainter,
                      widget: QtWidgets.QWidget | None = None
                      ) -> None:
        """
        Draws primitive elements with custom handling for checkboxes.

        :param element: The type of primitive element to draw.
        :type element: QtWidgets.QStyle.PrimitiveElement
        :param option: The style options for the element.
        :type option: QtWidgets.QStyleOption
        :param painter: The painter used to draw the element.
        :type painter: QtGui.QPainter
        :param widget: The widget to which the style is applied, or None.
        :type widget: QtWidgets.QWidget | None
        """
        if element in {QtWidgets.QStyle.PE_IndicatorCheckBox}:
            # Fix the background and border for transparent tables
            # in QTableView and QTreeView.
            option.palette.setColor(
                    option.palette.Base, QtGui.QPalette().base().color()
                    )
            option.palette.setColor(
                    option.palette.Background, QtGui.QPalette().dark().color()
                    )
        super().drawPrimitive(element, option, painter, widget)


#=========================================================================================
# ColumnViewSettings
#=========================================================================================


class ColumnViewSettings(Frame):
    """
    A tree view of checkboxes corresponding to the table columns.

    This widget allows users to select which columns in a table to display or hide,
    with additional functionality for linked columns in multi-index tables.
    """
    _tableView: TableABC = None
    _tableHandler: TableHeaderMenuColumns = None
    buttonFrame: Frame = None

    def __init__(self, parent,
                 view: TableABC = None, tableHandler: TableHeaderMenuColumns = None,
                 dfObject: pd.DataFrame | DataFrameObject = None,
                 **kwds):
        """
        Initialize the ColumnViewSettings widget.

        :param parent: Parent widget.
        :type parent: QWidget
        :param view: The associated table view.
        :type view: TableABC
        :param tableHandler: The table handler for managing columns.
        :type tableHandler: TableHeaderMenuColumns
        :param dfObject: The DataFrame or DataFrameObject containing the table data.
        :type dfObject: pd.DataFrame | DataFrameObject
        :param kwds: Additional keyword arguments for the frame.
        """
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
        """
        Set up the widget's components and layout.
        """
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
        row += 1
        _frame = self.buttonFrame = Frame(self, setLayout=True,
                                          grid=(row, 0), gridSpan=(1, 2))
        Spacer(_frame, 5, 5, 'minimumExpanding', 'fixed', grid=(0, 3))
        _frame.getLayout().setColumnStretch(1, 5)
        _frame.getLayout().setColumnStretch(2, 10)  # tweak the column-widths to fit the buttons
        _frame.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)

        txts = ['Check All', 'Uncheck All']
        tips = ['Check all columns',
                'Uncheck all columns']
        callbacks = [partial(self._tree._checkAll, True), partial(self._tree._checkAll, False), ]
        fRow = 0
        self._buttonList = ButtonList(_frame, texts=txts, callbacks=callbacks, tipTexts=tips,
                                      grid=(fRow, 0), gridSpan=(1, 2))  # allow for 2 buttons

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
        """
        Initialize the checkboxes based on the table's visible columns.
        """
        self._userColumns = OrderedDict([(col, rr) for col, rr in enumerate(self._df.columns)
                                         if not self._tableView.isColumnInternal(col)])
        for idx, (col, colName) in enumerate(self._userColumns.items()):
            self._tree._setCheckState(idx, not self._tableView.horizontalHeader().isSectionHidden(col))

    def _itemChecked(self, item):
        """
        Handle changes to item check state.

        :param item: The tree item whose state has changed.
        :type item: QTreeWidgetItem
        """
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
        """
        Get the state of the 'Link similar columns' checkbox.

        :return: True if linked, False otherwise.
        :rtype: bool
        """
        return self._linkedColumns.isChecked()

    @linkedColumns.setter
    def linkedColumns(self, value):
        """
        Set the state of the 'Link similar columns' checkbox.

        :param value: The new state.
        :type value: bool
        """
        self._linkedColumns.setChecked(value)


#=========================================================================================
# ColumnViewSettingsPopup
#=========================================================================================

class ColumnViewSettingsPopup(CcpnDialogMainWidget):
    """
    Popup containing a column-view-settings widget to show or hide table columns.

    This popup allows users to configure column visibility for a table view and
    remembers the state of hidden columns between sessions.
    """

    FIXEDHEIGHT = False
    FIXEDWIDTH = True

    _ColumnViewKlass = ColumnViewSettings

    def __init__(self, tableHandler: TableHeaderMenuColumns, dataFrameObject: pd.DataFrame | DataFrameObject = None,
                 parent: QtWidgets.QTableView = None,
                 title: str = 'Column Settings', **kwds):
        """
        Initialize the ColumnViewSettingsPopup.

        :param tableHandler: Handler for managing table column settings.
        :type tableHandler: TableHeaderMenuColumns
        :param dataFrameObject: DataFrame object containing table data.
        :type dataFrameObject: pd.DataFrame | DataFrameObject
        :param parent: Parent table view.
        :type parent: QtWidgets.QTableView
        :param title: Title of the popup window.
        :type title: str
        :param kwds: Additional keyword arguments for the dialog.
        """
        super().__init__(parent, setLayout=True, windowTitle=title, minimumSize=(250, 250), **kwds)

        self._tableView = parent
        self._setWidgets(tableHandler, dataFrameObject)  # dataFrameObject needs to go! :|

        self.setCloseButton(callback=self._close, tipText='Close')
        self.setDefaultButton(self.CLOSEBUTTON)

    def _setWidgets(self, tableHandler: TableHeaderMenuColumns, dataFrameObject: pd.DataFrame):
        """
        Set up the widgets for the popup.

        :param tableHandler: Handler for managing table column settings.
        :type tableHandler: TableHeaderMenuColumns
        :param dataFrameObject: DataFrame object containing table data.
        :type dataFrameObject: pd.DataFrame
        """
        self._columnViewSettingsWidget = self._ColumnViewKlass(self.mainWidget,
                                                               view=self._tableView,
                                                               tableHandler=tableHandler,
                                                               dfObject=dataFrameObject,
                                                               grid=(0, 0))

    def _close(self):
        """
        Save hidden columns to the table class so they persist between popups.
        """
        self.accept()

    def _cleanupDialog(self):
        """
        Clean up widgets to prevent segmentation faults during garbage collection.
        """
        # Prevents threading errors if not deleted
        self._columnViewSettingsWidget.deleteLater()

    def storeWidgetState(self):
        """
        Store the state of widgets between popup sessions.
        """
        linked = self._columnViewSettingsWidget.linkedColumns
        ColumnViewSettingsPopup._storedState[_LINK_COLUMNS] = linked

    def restoreWidgetState(self):
        """
        Restore the state of widgets between popup sessions.
        """
        self._columnViewSettingsWidget.linkedColumns = ColumnViewSettingsPopup._storedState.get(_LINK_COLUMNS, False)


#=========================================================================================
# ColumnViewCoreSettings
#=========================================================================================


class ColumnViewCoreSettings(ColumnViewSettings):
    """
    A tree view of checkboxes corresponding to the table columns, with additional
    functionality to allow save, restore, and reset to preferences.
    """

    _tableView: _CoreTableWidgetABC = None
    _tableHandler: TableHeaderMenuCoreColumns = None

    def _setWidgets(self):
        """
        Set up the widgets for the column view.

        This includes default buttons, a labeled horizontal line for user preferences,
        and buttons to save, restore, or clear column preferences.
        """
        row = super()._setWidgets()

        fRow = self.buttonFrame.getLayout().rowCount()
        self._defaultButton = ButtonList(self.buttonFrame, texts=['Default'],
                                         callbacks=[self._resetToDefault],
                                         tipTexts=['Reset the visible/hidden columns to the '
                                                   'default state for this table.'],
                                         grid=(fRow, 0))

        # Divider
        row += 1
        LabeledHLine(self, text='User preferences', colour=QtGui.QColor('#7f7f7f'),
                     grid=(row, 0), gridSpan=(1, 3))

        txts = ['Save', 'Restore', 'Clear']
        tips = ['Save the current visible columns to user-preferences;\n'
                'new tables will open from the saved state.',
                'Restore the visible/hidden columns from the\n'
                'saved state for this table',
                'Clear the current saved visible/hidden columns;\n'
                'new tables will open with the default state for this table']
        callbacks = [self._saveHiddensColumns, self._restoreHiddenColumns, self._resetHiddenColumns]
        row += 1
        self._columnsButtonList = ButtonList(self, texts=txts, callbacks=callbacks, tipTexts=tips,
                                             grid=(row, 0), gridSpan=(1, 2))
        self._check()

    def _saveHiddensColumns(self):
        """
        Save the currently visible columns to user preferences.
        """
        self._tableView.saveToPreferences()
        self._check()

    def _restoreHiddenColumns(self):
        """
        Restore the visible/hidden columns from user preferences.
        """
        self._tableView.restoreFromPreferences()
        # Repopulate the checkboxes
        self._initCheckBoxes()
        self._check()

    def _resetHiddenColumns(self):
        """
        Clear the saved visible/hidden column preferences.
        """
        self._tableView.resetPreferences()
        # Repopulate the checkboxes
        self._initCheckBoxes()
        self._check()

    def _itemChecked(self, item):
        """
        Handle the event when a checkbox item is toggled.

        :param item: The tree view item that was checked or unchecked.
        :type item: QTreeWidgetItem
        """
        super()._itemChecked(item)
        self._check()

    def _check(self):
        """
        Update the state of the save, restore, and reset buttons based on the current
        column preferences.
        """
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

    def _resetToDefault(self):
        """
        Reset the visible/hidden columns to the default state for this table.
        """
        self._tableView.resetHiddenColumns()
        self._initCheckBoxes()
        self._check()


#=========================================================================================
# ColumnViewCoreSettingsPopup
#=========================================================================================

class ColumnViewCoreSettingsPopup(ColumnViewSettingsPopup):
    """
    Popup containing the column-view-settings widget to show or hide columns,
    with additional functionality to allow save, restore, and reset to preferences.
    """

    _ColumnViewKlass = ColumnViewCoreSettings
