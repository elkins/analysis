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
__dateModified__ = "$dateModified: 2024-11-01 19:40:51 +0000 (Fri, November 01, 2024) $"
__version__ = "$Revision: 3.2.9 $"
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


_LINK_COLUMNS = 'linkColumns'


class ColumnViewSettingsPopup(CcpnDialogMainWidget):
    FIXEDHEIGHT = False
    FIXEDWIDTH = True

    def __init__(self, table, dataFrameObject=None, parent=None, hiddenColumns=None, title='Column Settings', **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, minimumSize=(250, 250), **kwds)

        self.tableHandler = table
        self._setWidgets(table, dataFrameObject)

        self.setCloseButton(callback=self._close, tipText='Close')
        self.setDefaultButton(self.CLOSEBUTTON)

    def _setWidgets(self, table, dataFrameObject):
        """Set up the widgets.
        """
        self.widgetColumnViewSettings = ColumnViewSettings(self.mainWidget, table=table,
                                                           dfObject=dataFrameObject,
                                                           grid=(0, 0))

    def getHiddenColumns(self):
        return self.widgetColumnViewSettings.hiddenColumns

    def _close(self):
        """Save the hidden-columns to the table class, so it remembers when you re-open the popup.
        """
        self.accept()
        return self.getHiddenColumns()

    def _cleanupDialog(self):
        """Clean up widgets that are causing seg-fault on garbage-collection.
        """
        # these NEED to be cleaned, one causes a threading error if not deleted :|
        self.tableHandler = None
        self.widgetColumnViewSettings.deleteLater()

    def storeWidgetState(self):
        """Store the state of widgets between popups.
        """
        linked = self.widgetColumnViewSettings.linkedColumns
        ColumnViewSettingsPopup._storedState[_LINK_COLUMNS] = linked

    def restoreWidgetState(self):
        """Restore the state of widgets.
        """
        self.widgetColumnViewSettings.linkedColumns = ColumnViewSettingsPopup._storedState.get(_LINK_COLUMNS, False)


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
    """ hide show check boxes corresponding to the table columns """

    def __init__(self, parent=None, table=None, dfObject=None, direction='v', **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        self.direction = direction

        # only need the pd.DataFrame
        if isinstance(dfObject, DataFrameObject):  # need to get rid of DataFrameObject :|
            self._df = dfObject.dataFrame
        elif isinstance(dfObject, pd.DataFrame):
            self._df = dfObject
        else:
            raise ValueError(f'dfObject is the wrong type - {type(dfObject)}')

        self.tableHandler = table
        self.checkBoxes = []
        self._hideColumnWidths = {}
        self._setWidgets()

    def _setWidgets(self):

        self._userColumns = OrderedDict([(col, rr) for col, rr in enumerate(self._df.columns)
                                         if not self.tableHandler.isColumnInternal(col)])
        dfCol = pd.DataFrame(self._userColumns.values())

        row = 0
        self.filterLabel = Label(self, text='Display Columns', grid=(row, 0))
        row += 1
        self._tree = ColumnTreeView(parent=self, df=dfCol,
                                    multiSelect=True, enableMouseMenu=True, enableCheckBoxes=True,
                                    grid=(row, 0), gridSpan=(1, 2)
                                    )
        self._tree.checkStateChanged.connect(self._itemChecked)
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
        # NOTE:ED - hide until the column-save/restore to user-preferences is properly functioning :|
        self._columnsButtonList.setVisible(False)
        self._initCheckBoxes()

    @property
    def hiddenColumns(self):
        return self.tableHandler.hiddenColumns

    def _saveHiddensColumns(self):
        ...

    def _restoreHiddenColumns(self):
        ...

    def _resetHiddenColumns(self):
        ...

    def _initCheckBoxes(self):

        self._userColumns = OrderedDict([(col, rr) for col, rr in enumerate(self._df.columns)
                                         if not self.tableHandler.isColumnInternal(col)])
        for idx, (col, colName) in enumerate(self._userColumns.items()):
            self._tree._setCheckState(idx, not self.tableHandler.horizontalHeader().isSectionHidden(col))

    def _itemChecked(self, item, column=0):
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
                self.tableHandler._showColumnName(self._df.columns[idx])
        else:
            # visibility of last remaining column is handled by the tree-widget
            for idx in idxs:
                self.tableHandler._hideColumnName(self._df.columns[idx])

        # refresh tree-view from columns
        if len(idxs) > 1:
            # more columns may have been shown/hidden
            self._initCheckBoxes()

    def _checkLastCheckbox(self):
        """Check whether there is a single checkbox remaining and disable as necessary.
        """
        checkedBoxes = list(filter(lambda ch: ch.isChecked(), self.checkBoxes))

        if len(checkedBoxes) == 1:
            # always display at least one column, disables the last checkbox
            checkedBoxes[0].setEnabled(False)
            checkedBoxes[0].setChecked(True)

    def updateWidgets(self, table):
        self.tableHandler = table
        if self.checkBoxes:
            for cb in self.checkBoxes:
                cb.deleteLater()
        self.checkBoxes = []
        self._initCheckBoxes()

    def refreshHiddenColumns(self):
        # show/hide the columns in the list
        columns = self.tableHandler.columnTexts

        for i, colName in enumerate(columns):
            if colName in self.tableHandler._hiddenColumns:
                self.tableHandler._hideColumnName(colName)
            else:
                self.tableHandler._showColumnName(colName)

    @property
    def linkedColumns(self):
        return self._linkedColumns.isChecked()

    @linkedColumns.setter
    def linkedColumns(self, value):
        self._linkedColumns.setChecked(value)
