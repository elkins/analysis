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
__dateModified__ = "$dateModified: 2024-09-05 11:44:15 +0100 (Thu, September 05, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2018-12-20 15:44:35 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

import contextlib
import operator as op
import numpy as np
import pandas as pd
from functools import partial
from PyQt5 import QtCore, QtWidgets, QtGui

from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.ScrollArea import ScrollArea
from ccpn.util.OrderedSet import OrderedSet
from ccpn.util.Logging import getLogger


VISIBLESEARCH = '<Visible Table>'

GreaterThan = '>'
LessThan = '<'
GreaterThanInclude = '>='
LessThanInclude = '<='
Equal = 'Equal'
NotEqual = 'Not-Equal'
Include = 'Include'
Exclude = 'Exclude'
Between = 'Between'
NotBetween = 'Not-Between'

SearchConditionsDict = {
    Equal             : op.eq,
    NotEqual          : op.eq,  # is negated later
    Include           : op.contains,
    Exclude           : op.contains,  # is negated later
    GreaterThan       : op.gt,
    GreaterThanInclude: op.ge,
    LessThan          : op.lt,
    LessThanInclude   : op.le,
    Between           : None,
    NotBetween        : None,
    }

CCTT = 'Filter and display only rows that '
SearchConditionsToolTips = [
    f'{CCTT} contain the exact match to the query.',
    f'{CCTT} do not contain the exact match to the query.',
    f'{CCTT} include at least a part of the query.',
    f'{CCTT} contain values greater than the query. (Only numbers)',
    f'{CCTT} contain values greater than the query, including limits. (Only numbers)',
    f'{CCTT} contain values less than the query. (Only numbers)',
    f'{CCTT} contain values less than the query, including limits. (Only numbers)',
    f'{CCTT} contain values between the queries, including the limits. (Only numbers)',
    f'{CCTT} contain values that are not between the queries, limits excluded. (Only numbers)',
    ]

RangeConditions = [Between, NotBetween]


def strTofloat(value):
    try:
        return float(value)
    except Exception:
        return None


def _compareKeys(a, b, condition):
    """
    :param a: first value
    :param b: second value
    :param condition: Any key of SearchConditionsDict.
    :return:
    """
    if condition not in list(SearchConditionsDict.keys()):
        getLogger().debug(f'Condition {condition} not available for table filters.')

    with contextlib.suppress(Exception):
        if condition in [Equal, NotEqual]:
            try:
                return SearchConditionsDict.get(condition)(float(a), float(b))
            except Exception:
                return SearchConditionsDict.get(condition)(a, b)
        elif condition not in [Include, Exclude]:
            a, b, = float(a), float(b)
        return SearchConditionsDict.get(condition)(a, b)
    return False


def _compareKeysInRange(originValue, queryRange, condition):
    value = strTofloat(originValue)
    _cond1 = strTofloat(queryRange[0])
    _cond2 = strTofloat(queryRange[1])
    if not all([value, _cond1, _cond2]):
        return False

    conds = [abs(_cond1), abs(_cond2)]
    cond1 = min(conds)
    cond2 = max(conds)
    a = np.array([value])

    if condition == NotBetween:
        result = np.any((a < cond1) | (a > cond2))
        # print(f' Checking if {value} is not between {cond1} and {cond2}. It is: {result}')
        return result
    if condition == Between:
        result = np.all((a >= cond1) & (a <= cond2))
        # print(f' Checking if {value} is between {cond1} and {cond2}. It is: {result}')
        return result
    return False


#=========================================================================================
# GuiTableFilter class use table._dataFrameObject as handler
#=========================================================================================

class GuiTableFilter(ScrollArea):
    def __init__(self, table, parent=None, **kwds):
        # super().__init__(parent, setLayout=True, showBorder=False, **kwds)
        super().__init__(parent, scrollBarPolicies=('never', 'never'), **kwds)

        self.table = table
        self._parent = parent

        # self._widgetScrollArea = ScrollArea(parent=parent, scrollBarPolicies=('never', 'never'), **kwds)
        self.setWidgetResizable(True)
        self._widget = Frame(self, setLayout=True, showBorder=False)
        self.getLayout().setHorizontalSpacing(0)
        self.getLayout().setVerticalSpacing(0)
        self.setWidget(self._widget)
        self._widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)

        self.conditionWidget = PulldownList(self._widget, texts=list(SearchConditionsDict.keys()),
                                            toolTips=SearchConditionsToolTips,
                                            callback=self._conditionWidgetCallback,
                                            grid=(0, 0))
        self.condition1 = LineEdit(self._widget, grid=(0, 1), backgroundText='Insert value')
        self.condition2 = LineEdit(self._widget, grid=(0, 2), backgroundText='Insert value 2')
        self._conditionWidgetCallback(self.conditionWidget.getText())

        #  second row
        labelColumn = Label(self._widget, 'Filter in', grid=(1, 0))
        self.columnOptions = PulldownList(self._widget, grid=(1, 1))
        self.columnOptions.setMinimumWidth(40)

        self.searchButtons = ButtonList(self._widget, texts=['Search ', 'Reset', 'Close'],
                                        icons=[Icon('icons/edit-find'), None, None],
                                        tipTexts=['Search in selected Columns', 'Restore Table', 'Close Filter'],
                                        callbacks=[partial(self.findOnTable, self.table),
                                                   partial(self.restoreTable, self.table),
                                                   self.hideSearch],
                                        grid=(1, 2), )

        Spacer(self._widget, 5, 5, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed,
               grid=(0, 2), gridSpan=(1, 1))

        # self.condition1.returnPressed.connect(partial(self.findOnTable, self.table))

        self.searchButtons.getButton('Reset').setEnabled(False)

        # fix the sizes of the widgets
        self.setFixedHeight(self.sizeHint().height() + 10)

        labelColumn.setFixedWidth(labelColumn.sizeHint().width())
        self.searchButtons.setFixedWidth(self.searchButtons.sizeHint().width())

        self.setColumnOptions()

        self.setContentsMargins(0, 0, 0, 0)

        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Minimum)

        # initialise search list
        self._listRows = None

    def setColumnOptions(self):
        # columns = self.table._dataFrameObject.columns
        # texts = [c.heading for c in columns]
        # objectsRange = range(len(columns))

        texts = self.table._dataFrameObject.userHeadings
        objectsRange = range(len(texts))

        self.columnOptions.clear()
        self.columnOptions.clearObjects()
        self.columnOptions.addItem(VISIBLESEARCH, item=None)
        for i, text in enumerate(texts):
            self.columnOptions.addItem(text, objectsRange[i])
        self.columnOptions.setIndex(0)

    def _conditionWidgetCallback(self, value):

        if value not in RangeConditions:
            self.condition2.hide()
        else:
            self.condition2.show()

    def updateSearchWidgets(self, table):
        self.table = table
        self.setColumnOptions()
        self.searchButtons.getButton('Reset').setEnabled(False)

    def hideSearch(self):
        self.restoreTable(self.table)
        # if self.table.searchWidget is not None:
        self.table.hideSearchWidget()

    def restoreTable(self, table):
        self.table.refreshTable()
        # self.condition1.clear()
        self.searchButtons.getButton('Reset').setEnabled(False)
        self._listRows = None

    def findOnTable(self, table, matchExactly=False, ignoreNotFound=False):
        if self.condition1.text() == '' or None:
            self.restoreTable(table)
            return

        self.table = table
        condition1Value = self.condition1.text()
        condition2Value = self.condition2.text()
        condition = self.conditionWidget.getText()

        # check using the actual table - not the underlying dataframe
        df = self.table._dataFrameObject.dataFrame
        rows = OrderedSet()

        searchColumn = self.columnOptions.getText()
        visHeadings = self.table._dataFrameObject.visibleColumnHeadings \
            if (searchColumn == VISIBLESEARCH) else searchColumn

        _compareErrorCount = 0
        for row in range(self.table.rowCount()):

            for column in range(self.table.columnCount()):
                if self.table.horizontalHeaderItem(column).text() in visHeadings:
                    item = table.item(row, column)
                    cellText = item.data(QtCore.Qt.DisplayRole)
                    if condition in RangeConditions:
                        match = _compareKeysInRange(cellText, (condition1Value, condition2Value), condition)
                    else:
                        match = _compareKeys(cellText, condition1Value, condition)
                        if match is None:
                            _compareErrorCount += 1

                    if match:
                        if self._listRows is not None:
                            rows.add(list(self._listRows)[item.index])
                        else:
                            rows.add(item.index)
        if _compareErrorCount > 0:
            getLogger().debug('Error in comparing values for GuiTable filters, use debug2 for details')

        try:
            self._searchedDataFrame = df.iloc[list(rows)]
        except Exception as es:
            getLogger().warning(f'Encountered a problem searching the table {es}')

        else:
            self._listRows = rows

            if not self._searchedDataFrame.empty:

                with self.table._guiTableUpdate(self.table._dataFrameObject):
                    self.table.setDataFromSearchWidget(self._searchedDataFrame)
                    self.table._setDefaultRowHeight()

                self.searchButtons.getButton('Reset').setEnabled(True)
            else:
                self.searchButtons.getButton('Reset').setEnabled(False)
                self.restoreTable(table)
                if not ignoreNotFound:
                    MessageDialog.showWarning('Not found', 'Query value(s) not found in selected columns.'
                                                           'Try by filtering in a specific column or double check your query.')

    def selectSearchOption(self, sourceTable, columnObject, value):
        try:
            self.columnOptions.setCurrentText(columnObject.__name__)
            self.condition1.setText(value)
            self.findOnTable(self.table, matchExactly=False, ignoreNotFound=True)
        except Exception as es:
            getLogger().debug('column not found in table')


#=========================================================================================
# _TableFilterABC class uses QTableView and model to access data
#=========================================================================================

class _TableFilterABC(ScrollArea):

    def __init__(self, parent, table, **kwds):
        # super().__init__(parent, setLayout=True, showBorder=False, **kwds)
        super().__init__(parent, scrollBarPolicies=('never', 'never'), **kwds)

        self._parent = parent
        self.tableHandler = table

        # self._widgetScrollArea = ScrollArea(parent=parent, scrollBarPolicies=('never', 'never'), **kwds)
        self.setWidgetResizable(True)
        self._widget = Frame(self, setLayout=True, showBorder=False)
        self.getLayout().setHorizontalSpacing(0)
        self.getLayout().setVerticalSpacing(0)
        self.setWidget(self._widget)
        self._widget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)

        self.conditionWidget = PulldownList(self._widget, texts=list(SearchConditionsDict.keys()),
                                            toolTips=SearchConditionsToolTips,
                                            callback=self._conditionWidgetCallback,
                                            grid=(0, 0))
        self.condition1 = LineEdit(self._widget, grid=(0, 1), backgroundText='Insert value')
        self.condition2 = LineEdit(self._widget, grid=(0, 2), backgroundText='Insert value 2')
        self._conditionWidgetCallback(self.conditionWidget.getText())

        #  second row
        labelColumn = Label(self._widget, 'Filter in', grid=(1, 0))
        self.columnOptions = PulldownList(self._widget, grid=(1, 1))
        self.columnOptions.setMinimumWidth(40)

        self.searchButtons = ButtonList(self._widget, texts=['Search ', 'Reset', 'Close'],
                                        icons=[Icon('icons/edit-find'), None, None],
                                        tipTexts=['Search in selected Columns', 'Restore Table', 'Close Filter'],
                                        callbacks=[partial(self.findOnTable, self.tableHandler),
                                                   partial(self.restoreTable, self.tableHandler),
                                                   self.hideSearch],
                                        grid=(1, 2), )

        Spacer(self._widget, 5, 5, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed,
               grid=(0, 2), gridSpan=(1, 1))

        # self.condition1.returnPressed.connect(partial(self.findOnTable, self.table))

        self.searchButtons.getButton('Reset').setEnabled(False)

        # fix the sizes of the widgets
        self.setFixedHeight(self.sizeHint().height() + 10)

        labelColumn.setFixedWidth(labelColumn.sizeHint().width())
        self.searchButtons.setFixedWidth(self.searchButtons.sizeHint().width())

        self.setColumnOptions()

        self.setContentsMargins(0, 0, 0, 0)

        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Minimum)

        # set the local tab-order for the search widgets
        self._tabOrder = (self.conditionWidget, self.condition1, self.condition2,
                          self.columnOptions, *self.searchButtons.buttons,)
        for widg in self._tabOrder:
            # add filter to capture the tab/backtab event
            widg.installEventFilter(self)

        # initialise search list
        self._listRows = None

    def eventFilter(self, source, event):
        """Handle foward/backward tabbing in a small group of widgets.
        """
        tp = event.type()
        if tp in [QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease]:
            key = event.key()
            if (tp, key) in [(QtCore.QEvent.KeyRelease, QtCore.Qt.Key_Tab),
                             (QtCore.QEvent.KeyPress, QtCore.Qt.Key_Backtab), ]:
                ind = (self._tabOrder.index(source) + (1 if key == QtCore.Qt.Key_Tab else -1)) % len(self._tabOrder)
                count = 0
                while not (self._tabOrder[ind].isEnabled() and self._tabOrder[ind].isVisible()):
                    ind = (ind + (1 if key == QtCore.Qt.Key_Tab else -1)) % len(self._tabOrder)
                    count += 1
                    if count > len(self._tabOrder):
                        # have cycled through all the tabs at least once
                        break
                else:
                    self._tabOrder[ind].setFocus()
                return True
            if key in [QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab]:
                # simulate an escape-key to clear keySequences
                escape = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape, QtCore.Qt.NoModifier)
                QtCore.QCoreApplication.sendEvent(self, escape)
                return True
            if key in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
                if source in self.searchButtons.buttons:
                    ...
        return super().eventFilter(source, event)

    def searchRows(self, df, rows):
        """Return the subset of the df based on rows
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    @property
    def columns(self):
        """Return the full list of columns
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def visibleColumns(self, searchColumn=None):
        """Return the list of visible columns
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    @property
    def df(self):
        """Return the Pandas-dataFrame
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def setColumnOptions(self):
        # columns = self.table._dataFrameObject.columns
        # texts = [c.heading for c in columns]
        # objectsRange = range(len(columns))

        texts = self._parent._df.columns
        objectsRange = range(len(texts))

        self.columnOptions.clear()  # doesn't clear the objects :|
        self.columnOptions.clearObjects()
        self.columnOptions.addItem(VISIBLESEARCH, item=None)
        for i, text in enumerate(texts):
            self.columnOptions.addItem(text, objectsRange[i])
        self.columnOptions.setIndex(0)

    def _conditionWidgetCallback(self, value):

        if value not in RangeConditions:
            self.condition2.hide()
        else:
            self.condition2.show()

    def updateSearchWidgets(self, table):
        self.tableHandler = table
        self.setColumnOptions()
        self.searchButtons.getButton('Reset').setEnabled(False)

    def refreshFilter(self):
        self.setColumnOptions()
        self.searchButtons.getButton('Reset').setEnabled(False)

    def hideSearch(self):
        self.restoreTable(self.tableHandler)
        # if self.table.searchWidget is not None:
        self.tableHandler.hideSearchWidget()

    def restoreTable(self, table):
        self.tableHandler.refreshTable()
        # self.condition1.clear()
        self.searchButtons.getButton('Reset').setEnabled(False)
        self._listRows = None

    @staticmethod
    def preFilterTableDf(df: pd.DataFrame) -> pd.DataFrame:
        """Apply pre-search filtering to the pandas-dataFrame.

        Round visible floats to 3-decimal places.

        :param pd.DataFrame df: source dataFrame
        :return: filtered dataFrame
        :rtype: pd.DataFrame
        """
        return df.applymap(lambda val: (f'{val:.3f}'
                                        if isinstance(val, (float, np.floating)) else
                                        str(val)))

    @staticmethod
    def postFilterTableDf(df: pd.DataFrame, dfFound: pd.Series, condition: str) -> pd.Series:
        """Apply post-search filtering to the pandas-dataFrame.

        No operation.
        To be subclassed.

        :param pd.DataFrame df: source dataFrame
        :param pd.Series dfFound: found mask
        :param str condition: search criterion
        :return: post-filtered dataFrame
        :rtype: pd.Series mask
        """
        return dfFound

    def findOnTable(self, table, matchExactly=False, ignoreNotFound=False):
        if self.condition1.text() == '' or None:
            self.restoreTable(table)
            return

        self.tableHandler = table
        condition1Value = self.condition1.text()
        condition2Value = self.condition2.text()
        condition = self.conditionWidget.getText()
        searchColNum = self.columnOptions.getObject()
        visHeadings = self.visibleColumns(searchColNum)
        _compareErrorCount = 0
        _model = self.tableHandler.model()
        df = self.preFilterTableDf(self.df)

        # Exclude needs to remove values from the list
        rows = OrderedSet(iter(range(df.shape[0]))) if condition in [Exclude, NotEqual] else OrderedSet()
        if condition in RangeConditions:
            # assume that string manipulation has been done by preFilterTableDf
            # or f'{cellText:.3f}' if isinstance(cellText, (float, np.floating)) else str(cellText)
            dfFound = (df[visHeadings]
                       .applymap(lambda val: _compareKeysInRange(val,
                                                                 (condition1Value, condition2Value),
                                                                 condition))
                       .select_dtypes(include='bool')
                       .fillna(False)
                       .any(axis=1))
        else:
            dfFound = (df[visHeadings]
                       .applymap(lambda val: _compareKeys(val, condition1Value, condition))
                       .select_dtypes(include='bool')
                       .fillna(False)
                       .any(axis=1))

        dfFound = self.postFilterTableDf(df, dfFound, condition)
        # the .index may not be integer
        foundSet = set(dfFound.index.get_loc(idx) for idx in dfFound[dfFound].index)
        if condition in [Exclude, NotEqual]:
            # remove the found sorted rows from the list - allows negated condition on multiple columns
            rows -= foundSet
        else:
            # add the found sorted rows to the found list
            rows |= foundSet

        self._listRows = rows
        if len(rows) and (_model._filterIndex is None or (set(rows) & set(_model._filterIndex))):
            self.tableHandler.setDataFromSearchWidget(rows)
            self.searchButtons.getButton('Reset').setEnabled(True)
        elif not ignoreNotFound:
            MessageDialog.showWarning('Not found', 'Query value(s) not found in selected columns.'
                                                   'Try by filtering in a specific column or double check your query.')

    def selectSearchOption(self, sourceTable, columnObject, value):
        try:
            self.columnOptions.setCurrentText(columnObject.__name__)
            self.condition1.setText(value)
            self.findOnTable(self.tableHandler, matchExactly=False, ignoreNotFound=True)
        except Exception:
            getLogger().debug('column not found in table')


#=========================================================================================
# _DFTableFilter class uses QTableView and model to access data
#=========================================================================================

class _DFTableFilter(_TableFilterABC):

    def searchRows(self, df, rows):
        """Return the subset of the df based on rows
        """
        return df.iloc[list(rows)].copy()

    @property
    def columns(self):
        """Return the full list of columns
        """
        return self.tableHandler._dataFrameObject.userHeadings

    def visibleColumns(self, searchColumn=None):
        """Return the list of visible columns
        """
        return self.tableHandler._dataFrameObject.visibleColumnHeadings if (searchColumn == VISIBLESEARCH) else [
            searchColumn]

    @property
    def df(self):
        """Return the Pandas-dataFrame
        """
        return self.tableHandler._dataFrameObject.dataFrame


#=========================================================================================
# _DFTableFilter class uses QTableView and model to access data
#=========================================================================================

class _SimplerDFTableFilter(_TableFilterABC):

    def searchRows(self, df, rows):
        """Return the subset of the df based on rows
        """
        return df.loc[list(rows)]

    @property
    def columns(self):
        """Return the full list of columns
        """
        return list(self.df.columns)

    def visibleColumns(self, columnIndex=None):
        """Return the list of visible columns
        """
        headerMenu = self._parent.headerColumnMenu

        return ([col for col in self.df.columns if col not in headerMenu._allHiddenColumns]
                if (columnIndex is None) else [self.df.columns[columnIndex]])

    @property
    def df(self):
        """Return the Pandas-dataFrame
        """
        return self._parent._df


#=========================================================================================
# attach methods
#=========================================================================================

def attachSearchWidget(parent, table):
    """
    Attach the search widget to the bottom of the table widget
    """
    returnVal = False
    try:
        parentLayout = table.parent().getLayout()

        if isinstance(parentLayout, QtWidgets.QGridLayout):
            idx = parentLayout.indexOf(table)
            location = parentLayout.getItemPosition(idx)
            if location is not None:
                if len(location) > 0:
                    row, column, rowSpan, columnSpan = location
                    table.searchWidget = GuiTableFilter(parent=parent, table=table, vAlign='b')
                    parentLayout.addWidget(table.searchWidget, row + 1, column, 1, columnSpan)
                    table.searchWidget.hide()

                returnVal = True

    except Exception as es:
        getLogger().warning(f'Error attaching search widget: {str(es)}')
    finally:
        return returnVal


def attachDFSearchWidget(parent, tableView):
    """Attach the search widget to the bottom of the table widget
    Search widget is applied to QTableView object
    """
    returnVal = False
    try:
        parentLayout = tableView.parent().layout()

        if isinstance(parentLayout, QtWidgets.QGridLayout):
            idx = parentLayout.indexOf(tableView)
            location = parentLayout.getItemPosition(idx)
            if location is not None:
                if len(location) > 0:
                    row, column, rowSpan, columnSpan = location
                    tableView.searchWidget = _DFTableFilter(parent=parent, table=tableView, vAlign='b')
                    parentLayout.addWidget(tableView.searchWidget, row + 1, column, 1, columnSpan)
                    tableView.searchWidget.hide()

                returnVal = True

    except Exception as es:
        getLogger().warning(f'Error attaching search widget: {str(es)}')
    finally:
        return returnVal


def attachSimpleSearchWidget(parent, table, searchWidget=None):
    """Attach the search widget to the bottom of the table widget
    Search widget is applied to QTableView object
    """
    try:
        # always assumes that the parent-table is contained within a frame
        parentLayout = parent.parent().layout()

        if isinstance(parentLayout, QtWidgets.QGridLayout):
            idx = parentLayout.indexOf(parent)
            location = parentLayout.getItemPosition(idx)
            if location is not None and len(location) > 0:
                row, column, rowSpan, columnSpan = location
                widget = _SimplerDFTableFilter(parent=parent, table=table, vAlign='b')

                # setattr(tableView, searchWidget or 'searchWidget', widget)  # not nice

                parentLayout.addWidget(widget, row + 1, column, 1, columnSpan)
                widget.hide()

                return widget

    except Exception as es:
        getLogger().warning(f'Error attaching search widget: {str(es)}')
