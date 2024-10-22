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
__dateModified__ = "$dateModified: 2024-10-18 14:24:18 +0100 (Fri, October 18, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-09-08 17:27:34 +0100 (Thu, September 08, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
import pandas as pd
from pandas.api.types import is_float_dtype
from PyQt5 import QtCore, QtGui
from ccpn.util.floatUtils import numZeros
from ccpn.core.lib.CcpnSorting import universalSortKey
from ccpn.ui.gui.guiSettings import getColours, GUITABLE_ITEM_FOREGROUND, consoleStyle
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.table._TableCommon import (
    EDIT_ROLE, DISPLAY_ROLE, TOOLTIP_ROLE,
    BACKGROUND_ROLE, FOREGROUND_ROLE, CHECK_ROLE, ICON_ROLE, SIZE_ROLE,
    ALIGNMENT_ROLE, FONT_ROLE, CHECKABLE, ENABLED, SELECTABLE, EDITABLE, CHECKED,
    UNCHECKED, VALUE_ROLE, INDEX_ROLE, BORDER_ROLE, ORIENTATIONS
    )
from ccpn.util.Logging import getLogger


#=========================================================================================
# Attribute handling
#=========================================================================================

def _getDisplayRole(self, row, col):
    # need to discard columns that include check-boxes
    val = self._df.iat[row, col]
    try:
        # try and get the function from the column-definitions
        fmt = self._view._columnDefs._columns[col].format
        return fmt % val
    except Exception:
        # fallback - float/np.float - round to 3 decimal places. This should be settable, ideally even by the user,
        if isinstance(val, float | np.floating):
            if not (val - val == 0.0):
                return None
            elif abs(val) > 1e6 or numZeros(val) >= 3:
                # make it scientific annotation if a huge/tiny number
                #e.g.:  if is 0.0001 will show as 1e-4 instead of 0.000
                val = f'{val:.3e}'
            else:
                # just rounds to the third decimal
                val = f'{val:.3f}'
        elif isinstance(val, bool) and self._enableCheckBoxes:
            # an empty cell with a checkbox - allow other text?
            return None
    return str(val)


def _getValueRole(self, row, col):
    val = self._df.iat[row, col]
    try:
        # convert np.types to python types
        return val.item()  # type np.generic
    except Exception:
        return val


def _getBackgroundRole(self, row, col):
    if (indexGui := self._guiState[row, col]):
        # get the colour from the dict
        return indexGui.get(BACKGROUND_ROLE)


def _getForegroundRole(self, row, col):
    if (indexGui := self._guiState[row, col]):
        # get the colour from the dict
        return indexGui.get(FOREGROUND_ROLE)


def _getBorderRole(self, row, col):
    if (indexGui := self._guiState[row, col]):
        # get the colour from the dict
        return bool(indexGui.get(BORDER_ROLE))


def _getToolTipRole(self, row, col):
    if self._view._toolTipsEnabled:
        return str(self._df.iat[row, col])


def _getEditRole(self, row, col):
    data = self._df.iat[row, col]
    # float/np.float - return float
    if isinstance(data, (float, np.floating)):
        return float(data)
    elif isinstance(data, bool):
        # need to check before int - int also includes bool :|
        return data
    # int/np.integer - return int
    elif isinstance(data, (int, np.integer)):
        return int(data)
    return data


def _getIndexRole(self, row, col):
    # return a dict of item-data?
    return (row, col)


def _getFontRole(self, row, col):
    if (indexGui := self._guiState[row, col]):
        # get the font from the dict
        return indexGui.get(FONT_ROLE)


def _getCheckRole(self, row, col):
    # need flags to include CHECKABLE and return QtCore.Qt.checked/unchecked/PartiallyChecked here
    if isinstance((val := self._df.iat[row, col]), bool):
        # bool to checkbox state
        return CHECKED if val else UNCHECKED


def _getIconRole(self, row, col):
    # return the pixmap - this works, transfer to _MultiHeader
    return self._editableIcon


def _getAlignmentRole(self, row, col):
    # return the pixmap - this works, transfer to _MultiHeader
    ...


#=========================================================================================
# _TableModel
#=========================================================================================

class _TableModel(QtCore.QAbstractTableModel):
    """A simple table-model to view pandas DataFrames.
    """

    _defaultForegroundColour = None
    _CHECKROWS = 5
    _MINCHARS = 4
    _MAXCHARS = 100
    _chrWidth = 12
    _chrHeight = 12
    _chrPixelPadding = 6
    _chrPadding = 3
    _cellRightBorder = 32.0
    _cellBorder = QtCore.QSizeF(_cellRightBorder, 0.0)

    showEditIcon = False
    defaultFlags = ENABLED | SELECTABLE  # add CHECKABLE to enable check-boxes
    _defaultEditable = True
    _enableCheckBoxes = False

    _guiState = None

    #=========================================================================================
    # Attribute handling
    #=========================================================================================

    getAttribRole = {DISPLAY_ROLE   : _getDisplayRole,
                     VALUE_ROLE     : _getValueRole,
                     BACKGROUND_ROLE: _getBackgroundRole,
                     FOREGROUND_ROLE: _getForegroundRole,
                     BORDER_ROLE    : _getBorderRole,
                     TOOLTIP_ROLE   : _getToolTipRole,
                     EDIT_ROLE      : _getEditRole,
                     INDEX_ROLE     : _getIndexRole,
                     FONT_ROLE      : _getFontRole,
                     CHECK_ROLE     : _getCheckRole,
                     # ICON_ROLE      : _getIconRole,
                     # ALIGNMENT_ROLE : _getAlignmentRole,
                     }

    #=========================================================================================
    # Class definitions
    #=========================================================================================

    def __init__(self, df, parent=None, view=None):
        """Initialise the pandas model.
        Allocates space for foreground/background colours.
        :param df: pandas DataFrame
        """
        super().__init__(parent)

        self.df = df
        self._view = view
        if view:
            fontMetric = QtGui.QFontMetricsF(view.font())
            self._bbox = bbox = fontMetric.boundingRect
            self._hAdvance = fontMetric.horizontalAdvance  # just returns the width, 25% faster?
            # get an estimate for an average character width/height - must be floats for estimate-column-widths
            test = 'WMB'  # Selection of wider letters to prevent collapsing column
            self._chrWidth = bbox(test).width() / len(test)
            self._chrHeight = bbox('A').height() + self._chrPixelPadding

        # set default colours
        # self._defaultForegroundColour = QtGui.QColor(getColours()[GUITABLE_ITEM_FOREGROUND])

        # initialise sorting/filtering
        self._sortColumn = None
        self._sortOrder = None
        self._filterIndex = None

        # create a pixmap for the editable icon (currently a pencil)
        self._editableIcon = Icon('icons/editable').pixmap(int(self._chrHeight), int(self._chrHeight))

    @property
    def df(self):
        """Return the underlying Pandas-dataFrame.
        """
        return self._df

    @df.setter
    def df(self, value):
        """Replace the dataFrame and update the model.

        :param value: pandas dataFrame
        :return:
        """
        self.beginResetModel()

        # set the initial sort-order
        self._oldSortIndex = list(range(value.shape[0]))
        self._sortIndex = list(range(value.shape[0]))
        self._filterIndex = None

        # create numpy arrays to match the data that will hold fore/background-colour, and other info
        self._guiState = np.full(value.shape, None, dtype=object)
        self._headerToolTips = {orient: np.empty(value.shape[ii], dtype=object)
                                for ii, orient in enumerate([QtCore.Qt.Vertical, QtCore.Qt.Horizontal])}

        # set the dataFrame
        self._df = value

        # notify that the data has changed
        self.endResetModel()

    @property
    def filteredDf(self):
        """Return the filtered dataFrame
        """
        if self._filterIndex is not None:
            # the filtered df
            return self._df.iloc[self._filterIndex]
        else:
            return self._df

    @property
    def displayedDf(self):
        """Return the visible dataFrame as displayed, sorted and filtered
        """
        return self._getVisibleDataFrame(includeHiddenColumns=False)

    def _getVisibleDataFrame(self, includeHiddenColumns=False):
        """Return the visible dataFrame as displayed, sorted and filtered.
        includeHiddenColumns: True to return the dataFrame containing  all columns.
        """
        from ccpn.util.OrderedSet import OrderedSet

        df = self._df
        table = self._view
        rows, cols = df.shape[0], df.shape[1]

        if df.empty:
            return df

        if includeHiddenColumns:
            colList = list(df.columns)
        else:
            colList = [col for ii, col, in enumerate(list(df.columns)) if
                       not table.horizontalHeader().isSectionHidden(ii)]

        if self._filterIndex is None:
            rowList = [self._sortIndex[row] for row in range(rows)]
        else:
            #  map to sorted indexes
            rowList = list(OrderedSet(self._sortIndex[row] for row in range(rows)) &
                           OrderedSet(self._sortIndex[ii] for ii in self._filterIndex))

        df = df[colList]
        return df[:].iloc[rowList]

    def setToolTips(self, orientation, values):
        """Set the tooltips for the horizontal/vertical headers.

        Orientation can be defined as: 'h', 'horizontal', 'v', 'vertical', QtCore.Qt.Horizontal, or QtCore.Qt.Vertical.

        :param orientation: str or Qt constant
        :param values: list of str containing new headers
        :return:
        """
        if not (orientation := ORIENTATIONS.get(orientation)):
            raise ValueError(f'orientation not in {list(ORIENTATIONS.keys())}')
        if not (isinstance(values, (list, tuple)) and all(isinstance(val, (type(None), str)) for val in values)):
            raise ValueError('values must be a list|tuple of str|None')

        try:
            self._headerToolTips[orientation] = values

        except Exception as es:
            raise ValueError(
                    f'{self.__class__.__name__}.setToolTips: Error setting values {orientation} -> {values}\n{es}') from es

    def _insertRow(self, row, newRow):
        """Insert a new row into the table.

        :param row: index of row to be inserted
        :param newRow: new row as pandas-dataFrame or list of items
        :return:
        """
        if self._view.isSortingEnabled():
            # notify that the table is about to be changed
            self.layoutAboutToBeChanged.emit()

            # keep sorted
            self._df.loc[row] = newRow  # dependent on the index
            self._df.sort_index(inplace=True)
            iLoc = self._df.index.get_loc(row)

            # update the sorted list
            self._sortIndex[:] = [(val if val < iLoc else val + 1) for val in self._sortIndex]

            # sLoc = self._sortIndex[iLoc]  # signals?
            # self.beginInsertRows(QtCore.QModelIndex(), sLoc, sLoc)
            self._guiState = np.insert(self._guiState, iLoc, np.empty((self.columnCount()), dtype=object), axis=0)
            self._setSortOrder(self._sortColumn, self._sortOrder)
            # self.endInsertRows()

            # NOTE:ED insert into the unfiltered df?
            # connect to signals in the view?

            # emit a signal to spawn an update of the table and notify headers to update
            self.layoutChanged.emit()

        else:
            # NOTE:ED - not checked, keep for reference
            pass
            # self._df.loc[row] = newRow
            # iLoc = self._df.index.get_loc(row)
            # self.beginInsertRows(QtCore.QModelIndex(), iLoc, iLoc)
            # self._guiState = np.insert(self._guiState, iLoc, np.empty((self.columnCount()), dtype=object), axis=0)
            # self.endInsertRows()
            # indexA = model.index(0, 0)
            # indexB = model.index(n - 1, c - 1)
            # model.dataChanged.emit(indexA, indexB)  # all visible cells

    def _updateRow(self, row, newRow):
        """Update a row in the table.

        :param row: index of row to be updated
        :param newRow: new row as pandas-dataFrame or list of items
        :return:
        """
        try:
            iLoc = self._df.index.get_loc(row)  # will give a keyError if the row is not found

        except KeyError:
            getLogger().debug(f'row {row} not found')

        else:
            if self._view.isSortingEnabled():
                # notify that the table is about to be changed
                self.layoutAboutToBeChanged.emit()

                self._df.iloc[iLoc] = newRow
                self._setSortOrder(self._sortColumn, self._sortOrder)

                # emit a signal to spawn an update of the table and notify headers to update
                self.layoutChanged.emit()

            else:
                # NOTE:ED - not checked
                pass
                # # print(f'>>>   _updateRow    {newRow}')
                # iLoc = self._df.index.get_loc(row)
                # if iLoc >= 0:
                #     # self.beginResetModel()
                #
                #     # notify that the table is about to be changed
                #     self.layoutAboutToBeChanged.emit()
                #
                #     self._df.loc[row] = newRow  # dependent on the index
                #     self._setSortOrder()
                #
                #     # emit a signal to spawn an update of the table and notify headers to update
                #     self.layoutChanged.emit()
                #
                #     # self.endResetModel()
                #
                #     # # print(f'>>>      _updateRow    {iLoc}')
                #     # self._df.loc[row] = newRow
                #     #
                #     # # notify change to cells
                #     # _sortedLoc = self._sortIndex.index(iLoc)
                #     # startIdx, endIdx = self.index(_sortedLoc, 0), self.index(_sortedLoc, self.columnCount() - 1)
                #     # self.dataChanged.emit(startIdx, endIdx)

    def _deleteRow(self, row):
        """Delete a row from the table.

        :param row: index of the row to be deleted
        :return:
        """
        try:
            iLoc = self._df.index.get_loc(row)

        except KeyError:
            getLogger().debug(f'row {row} not found')

        else:
            if self._view.isSortingEnabled():
                sortedLoc = self._sortIndex.index(iLoc)
                self.beginRemoveRows(QtCore.QModelIndex(), sortedLoc, sortedLoc)

                # remove the row from the dataFrame
                self._df.drop([row], inplace=True)

                if self._filterIndex is not None:
                    # remove from the filtered list - undo?
                    filt = self._sortIndex.index(iLoc)
                    self._filterIndex[:] = [(val if val < filt else val - 1) for val in self._filterIndex if
                                            val != filt]

                # remove from the sorted list
                self._sortIndex[:] = [(val if val < iLoc else val - 1) for val in self._sortIndex if val != iLoc]

            else:
                # NOTE:ED - not checked
                # notify rows are going to be inserted
                self.beginRemoveRows(QtCore.QModelIndex(), iLoc, iLoc)

                self._df.drop([row], inplace=True)

            self._guiState = np.delete(self._guiState, iLoc, axis=0)
            self.endRemoveRows()

    def rowCount(self, parent=None):
        """Return the row-count for the dataFrame.
        """
        if self._filterIndex is not None:
            return len(self._filterIndex)
        else:
            return self._df.shape[0]

    def columnCount(self, parent=None):
        """Return the column-count for the dataFrame.
        """
        return 1 if type(self._df) == pd.Series else self._df.shape[1]

    def data(self, index, role=DISPLAY_ROLE):
        """Return the data/roles for the model.
        """
        # usual roles {0, 1, 3, 4, 6, 7, 8, 9, 10, 13}
        if not index.isValid():
            return
        row = index.row()
        if role == SIZE_ROLE:
            val = self._df.iat[row, index.column()]
            # sorting filter not really important, just need to grab a few rows
            return QtCore.QSizeF(self._cellRightBorder +
                                 self._hAdvance(f'{val:.3f}'
                                                if isinstance(val, float | np.floating) else
                                                str(val)),
                                 self._chrHeight)
        if func := self.getAttribRole.get(role):
            # get the source cell
            fRow = (self._filterIndex[row]
                    if self._filterIndex is not None and 0 <= row < len(self._filterIndex) else row)
            return func(self, self._sortIndex[fRow], index.column())

    # def data(self, index, role=DISPLAY_ROLE):
    #     """Return the data/roles for the model.
    #     """
    #     if not index.isValid():
    #         return
    #     row = index.row()
    #     if role == SIZE_ROLE:
    #         # sorting filter not really important, just need to grab a few rows
    #         return QtCore.QSizeF(self._cellRightBorder +
    #                              self._hAdvance(str(self._df.iat[row, index.column()])),
    #                              self._chrHeight)
    #
    #     # try:
    #     # get the source cell
    #     fRow = self._filterIndex[row] if self._filterIndex is not None and 0 <= row < len(
    #             self._filterIndex) else row
    #     row, col = self._sortIndex[fRow], index.column()
    #
    #     if role == DISPLAY_ROLE:
    #         # need to discard columns that include check-boxes
    #         val = self._df.iat[row, col]
    #         try:
    #             # try and get the function from the column-definitions
    #             fmt = self._view._columnDefs._columns[col].format
    #             return fmt % val
    #         except Exception:
    #             # fallback - float/np.float - round to 3 decimal places. This should be settable, ideally even by the user,
    #             if isinstance(val, (float, np.floating)):
    #                 if abs(val) > 1e6 or numZeros(val) >= 3:
    #                     # make it scientific annotation if a huge/tiny number
    #                     #e.g.:  if is 0.0001 will show as 1e-4 instead of 0.000
    #                     val = f'{val:.3e}'
    #                 else:
    #                     # just rounds to the third decimal
    #                     val = f'{val:.3f}'
    #             elif isinstance(val, bool) and self._enableCheckBoxes:
    #                 # an empty cell with a checkbox - allow other text?
    #                 return None
    #         return str(val)
    #
    #     elif role == VALUE_ROLE:
    #         val = self._df.iat[row, col]
    #         try:
    #             # convert np.types to python types
    #             return val.item()  # type np.generic
    #         except Exception:
    #             return val
    #
    #     elif role == BACKGROUND_ROLE:
    #         if (indexGui := self._guiState[row, col]):
    #             # get the colour from the dict
    #             return indexGui.get(role)
    #
    #     elif role == FOREGROUND_ROLE:
    #         if (indexGui := self._guiState[row, col]):
    #             # get the colour from the dict
    #             return indexGui.get(role)
    #
    #     elif role == BORDER_ROLE:
    #         if (indexGui := self._guiState[row, col]):
    #             # get the colour from the dict
    #             return bool(indexGui.get(role))
    #
    #     elif role == TOOLTIP_ROLE:
    #         if self._view._toolTipsEnabled:
    #             data = self._df.iat[row, col]
    #             return str(data)
    #
    #     elif role == EDIT_ROLE:
    #         data = self._df.iat[row, col]
    #         # float/np.float - return float
    #         if isinstance(data, (float, np.floating)):
    #             return float(data)
    #         elif isinstance(data, bool):
    #             # need to check before int - int also includes bool :|
    #             return data
    #         # int/np.integer - return int
    #         elif isinstance(data, (int, np.integer)):
    #             return int(data)
    #         return data
    #
    #     elif role == INDEX_ROLE:
    #         # return a dict of item-data?
    #         return (row, col)
    #
    #     elif role == FONT_ROLE:
    #         if (indexGui := self._guiState[row, col]):
    #             # get the font from the dict
    #             return indexGui.get(role)
    #
    #     elif role == CHECK_ROLE and self._enableCheckBoxes:
    #         if isinstance((val := self._df.iat[row, col]), bool):
    #             # bool to checkbox state
    #             return CHECKED if val else UNCHECKED
    #         return None

    def setData(self, index, value, role=EDIT_ROLE) -> bool:
        """Set data in the DataFrame. Required if table is editable.
        """
        if not index.isValid():
            return False

        if role == EDIT_ROLE:
            # get the source cell
            fRow = self._filterIndex[index.row()] if self._filterIndex is not None else index.row()
            row, col = self._sortIndex[fRow], index.column()
            try:
                if self._df.iat[row, col] != value:
                    self._df.iat[row, col] = value
                    self.dataChanged.emit(index, index)
                    return True
            except Exception as es:
                getLogger().debug2(f'error accessing cell {index}  ({row}, {col})   {es}')

        elif role == CHECK_ROLE and self._enableCheckBoxes:
            # set state in cell/object
            # get the source cell
            fRow = self._filterIndex[index.row()] if self._filterIndex is not None else index.row()
            row, col = self._sortIndex[fRow], index.column()
            try:
                # checkbox state to bool
                val = True if (value == CHECKED) else False
                if self._df.iat[row, col] != val:
                    self._df.iat[row, col] = val
                    self.dataChanged.emit(index, index)
                    return True
            except Exception as es:
                getLogger().debug2(f'error accessing cell {index}  ({row}, {col})   {es}')

        return False

    def headerData(self, col, orientation, role=None):
        """Return the information for the row/column headers
        """
        if role == DISPLAY_ROLE and orientation == QtCore.Qt.Horizontal:
            try:
                # quickest way to get the column-header
                return self._df.columns[col]
            except Exception:
                return None

        elif role == DISPLAY_ROLE and orientation == QtCore.Qt.Vertical:
            try:
                # quickest way to get the row-number
                return col + 1
            except Exception:
                return None

        elif role == TOOLTIP_ROLE and orientation == QtCore.Qt.Horizontal:
            try:
                # quickest way to get the column tooltip
                return self._headerToolTips[orientation][col]
            except Exception:
                return None

        elif role == ICON_ROLE and self._isColumnEditable(col) and self.showEditIcon:
            # return the pixmap
            return self._editableIcon

        # NOTE:ED - if SIZE_ROLE is defined in both data and headerData, the larger of the two is used for the row/column/cell size
        #           assuming that both always return a QSize, otherwise QT defaults to calculating the bbox for the cell
        # elif role == SIZE_ROLE:
        #     print('==> HELP')
        #     # process the heights/widths of the headers
        #     if orientation == QtCore.Qt.Horizontal:
        #         try:
        #             # get the cell height from the number of lines in the header data
        #             txt = str(self.headerData(col, orientation, role=DISPLAY_ROLE))
        #             height = len(txt.split('\n')) * int(self._chrHeight)
        #
        #             # get the estimated width of the column, also for the last visible column
        #             if (self._view._columnDefs and self._view._columnDefs._columns):
        #                 colObj = self._view._columnDefs._columns[col]
        #                 width = colObj.columnWidth
        #                 if width is not None:
        #                     return QtCore.QSize(width, height)
        #
        #             width = self._estimateColumnWidth(col) + \
        #                     (self._editableIcon.width() if (self._isColumnEditable(col) and self.showEditIcon) else 0)
        #
        #             # return the size
        #             return QtCore.QSize(width, height)
        #
        #         except Exception:
        #             # return the default QSize
        #             return QtCore.QSize(int(self._chrWidth), int(self._chrHeight))
        #
        #     # vertical-header
        #     # get the cell height from the number of lines in the header data
        #     txts = str(self.headerData(col, orientation, role=DISPLAY_ROLE)).split('\n')
        #     height = int(len(txts) * self._chrHeight)
        #
        #     maxLen = max(len(txt) for txt in txts) + 1
        #     width = int(min(self._MAXCHARS, maxLen) * self._chrWidth) + 2
        #
        #     # return the default QSize for vertical header
        #     return QtCore.QSize(width, height)

    def _estimateColumnWidth(self, col):
        """Estimate the width for the column from the header and fixed number of rows
        """
        # get the width of the header
        try:
            # quickest way to get the column
            if type(self._df.columns) is pd.MultiIndex:
                txts = list(self._df.columns)[col][-1].split('\n')
            else:
                txts = list(self._df.columns)[col].split('\n')

            maxLen = max(len(txt) for txt in txts)
            maxLen = max(maxLen, self._MINCHARS)

        except Exception:
            maxLen = self._MINCHARS

        try:
            dType = self._df.dtypes[col]
            # get the maximum number of characters in the required column
            if is_float_dtype(dType):
                max_length = self._df.iloc[:, col].apply(lambda x: len(f'{x:.6g}')).max()
            else:
                # should implement line-splitting here
                max_length = self._df.iloc[:, col].apply(str).apply(len).max()
            maxLen = max(maxLen, max_length) + self._chrPadding

            return int(min(self._MAXCHARS, maxLen) * self._chrWidth)

        except Exception:
            # iterate over a few rows to get an estimate
            for row in range(min(self.rowCount(), self._CHECKROWS)):
                data = self._df.iat[row, col]

                # float/np.float - round to 3 decimal places
                if isinstance(data, (float, np.floating)):
                    newLen = len(f'{data:.6g}')
                else:
                    data = str(data)
                    if '\n' in data:
                        # get the longest row from the cell
                        dataRows = data.split('\n')
                        newLen = max(len(_chrs) for _chrs in dataRows)
                    else:
                        newLen = len(data)

                # update the current maximum
                maxLen = max(newLen, maxLen) + self._chrPadding

        return int(min(self._MAXCHARS, maxLen) * self._chrWidth)

    def setForeground(self, row, column, colour):
        """Set the foreground colour for dataFrame cell at position (row, column).

        :param row: row as integer
        :param column: column as integer
        :param colour: colour compatible with QtGui.QColor
        :return:
        """
        if not (0 <= row < self.rowCount() and 0 <= column < self.columnCount()):
            raise ValueError(f'({row}, {column}) must be less than ({self.rowCount()}, {self.columnCount()})')

        if not (indexGui := self._guiState[row, column]):
            indexGui = self._guiState[row, column] = {}
        if colour:
            indexGui[FOREGROUND_ROLE] = QtGui.QColor(colour)
        else:
            indexGui.pop(FOREGROUND_ROLE, None)

    def setBackground(self, row, column, colour):
        """Set the background colour for dataFrame cell at position (row, column).

        :param row: row as integer
        :param column: column as integer
        :param colour: colour compatible with QtGui.QColor
        """
        if not (0 <= row < self.rowCount() and 0 <= column < self.columnCount()):
            raise ValueError(f'({row}, {column}) must be less than ({self.rowCount()}, {self.columnCount()})')

        if not (indexGui := self._guiState[row, column]):
            indexGui = self._guiState[row, column] = {}
        if colour:
            indexGui[BACKGROUND_ROLE] = QtGui.QColor(colour)
        else:
            indexGui.pop(BACKGROUND_ROLE, None)

    def setBorderVisible(self, row: int, column: int, enabled: bool):
        """Enable the border for dataFrame cell at position (row, column).

        :param int row: row as integer
        :param int column: column as integer
        :param bool enabled: True/False or None
        """
        if not (0 <= row < self.rowCount() and 0 <= column < self.columnCount()):
            raise ValueError(f'({row}, {column}) must be less than ({self.rowCount()}, {self.columnCount()})')

        if not (indexGui := self._guiState[row, column]):
            indexGui = self._guiState[row, column] = {}
        indexGui[BORDER_ROLE] = bool(enabled)

    def setCellFont(self, row, column, font):
        """Set the font for dataFrame cell at position (row, column).

        :param row: row as integer
        :param column: column as integer
        :param font: font compatible with QtGui.QFont
        :return:
        """
        if not (0 <= row < self.rowCount() and 0 <= column < self.columnCount()):
            raise ValueError(f'({row}, {column}) must be less than ({self.rowCount()}, {self.columnCount()})')

        if not (indexGui := self._guiState[row, column]):
            indexGui = self._guiState[row, column] = {}
        if font:
            indexGui[FONT_ROLE] = font
        else:
            indexGui.pop(FONT_ROLE, None)

    @staticmethod
    def _universalSort(values):
        """Method to apply sorting.
        """
        # generate the universal sort key values for the column
        return pd.Series(universalSortKey(val) for val in values)

    def _setSortOrder(self, column: int, order: QtCore.Qt.SortOrder = ...):
        """Get the new sort order based on the sort column and sort direction
        """
        self._oldSortIndex = self._sortIndex
        col = self._df.columns[column]
        newData = self._universalSort(self._df[col])

        self._sortIndex = list(newData.sort_values(ascending=(order == QtCore.Qt.AscendingOrder)).index)

        # map the old sort-order to the new sort-order
        if self._filterIndex is not None:
            self._oldFilterIndex = self._filterIndex
            self._filterIndex = sorted([self._sortIndex.index(self._oldSortIndex[fi]) for fi in self._filterIndex])

    def sort(self, column: int, order: QtCore.Qt.SortOrder = ...) -> None:
        """Sort the underlying pandas DataFrame.
        Required as there is no proxy model to handle the sorting.
        """
        # remember the current sort settings
        self._sortColumn = column
        self._sortOrder = order

        # notify that the table is about to be changed
        self.layoutAboutToBeChanged.emit()

        self._setSortOrder(column, order)

        # emit a signal to spawn an update of the table and notify headers to update
        self.layoutChanged.emit()

    def mapToSource(self, indexes):
        """Map the cell index to the co-ordinates in the pandas dataFrame.
        Return list of tuples of dataFrame positions.
        """
        mapped = []
        for idx in indexes:
            if not idx.isValid():
                mapped.append((None, None))
            else:
                fRow = self._filterIndex[idx.row()] if self._filterIndex is not None and 0 <= idx.row() < len(
                        self._filterIndex) else idx.row()
                mapped.append((self._sortIndex[fRow], idx.column()))

        return mapped

    def flags(self, index):
        # Set the table to be editable - need the editable columns here
        if self._isColumnEditable(index.column()):
            return EDITABLE | self.defaultFlags
        else:
            return self.defaultFlags

    def _isColumnEditable(self, col):
        """Return whether the column number is editable.
        """
        try:
            # return True if the column contains an edit function and table is editable
            # NOTE:ED - need to remove _dataFrameObject, move options to TableABC? BUT Column class is still good
            return self._defaultEditable and self._view._dataFrameObject.setEditValues[col] is not None
        except Exception:
            return self._defaultEditable

    def resetFilter(self):
        """Reset the table to unsorted
        """
        if self._filterIndex is not None:
            self.beginResetModel()
            self._filterIndex = None
            self.endResetModel()


#=========================================================================================
# _TableObjectModel
#=========================================================================================

def _getCheckedDisplayRole(colDef, obj):
    return None if isinstance((value := colDef.getFormatValue(obj)), bool) else value


def _getCheckedRole(colDef, obj):
    if isinstance((value := colDef.getValue(obj)), bool):
        return CHECKED if value else UNCHECKED

    return None


class _TableObjectModel(_TableModel):
    """Table-model that supports defining a list of objects for the table.

    Objects are defined as a list, and table is populated with information from the Column classes.
    """
    # NOTE:ED - not properly tested

    defaultFlags = ENABLED | SELECTABLE | CHECKABLE

    getAttribRole = {DISPLAY_ROLE   : _getCheckedDisplayRole,
                     CHECK_ROLE     : _getCheckedRole,
                     ICON_ROLE      : lambda colDef, obj: colDef.getIcon(obj),
                     EDIT_ROLE      : lambda colDef, obj: colDef.getEditValue(obj),
                     TOOLTIP_ROLE   : lambda colDef, obj: colDef.tipText,
                     BACKGROUND_ROLE: lambda colDef, obj: colDef.getColor(obj),
                     ALIGNMENT_ROLE : lambda colDef, obj: colDef.alignment
                     }

    setAttribRole = {EDIT_ROLE : lambda colDef, obj, value: colDef.setEditValue(obj, value),
                     CHECK_ROLE: lambda colDef, obj, value: colDef.setEditValue(obj,
                                                                                True if (value == CHECKED) else False)
                     }

    # def _setSortOrder(self, column: int, order: QtCore.Qt.SortOrder = ...):
    #     """Sort the object-list
    #     """
    #     colDef = self._view._columnDefs._columns
    #     getValue = colDef[column].getValue
    #     self._view._objects.sort(key=getValue, reverse=False if order == QtCore.Qt.AscendingOrder else True)

    def data(self, index, role=DISPLAY_ROLE):
        result = None  # super(AdminModel, self).data(index, role)  # super not required?

        # special control over the object properties
        if index.isValid():
            # get the source cell
            fRow = self._filterIndex[index.row()] if self._filterIndex is not None else index.row()
            row, col = self._sortIndex[fRow], index.column()

            obj = self._view._objects[row]
            colDef = self._view._columnDefs._columns[col]

            if (func := self.getAttribRole.get(role)):
                return func(colDef, obj)

        return result

    def setData(self, index, value, role=EDIT_ROLE) -> bool:
        # super(AdminModel, self).setData(index, role, value)  # super not required?

        if index.isValid():
            fRow = self._filterIndex[index.row()] if self._filterIndex is not None else index.row()
            row, col = self._sortIndex[fRow], index.column()

            obj = self._view._objects[row]
            colDef = self._view._columnDefs._columns[col]

            if (func := self.setAttribRole.get(role)):
                func(colDef, obj, value)
                self.dataChanged.emit(index, index)

                self._view.viewport().update()  # repaint the view
                return True

        return False


#=========================================================================================

def main():
    # Create a Pandas DataFrame.
    import pandas as pd

    technologies = {
        'Courses': ['a', 'b', 'b', 'c', 'd', 'c', 'a', 'b', 'd', 'd', 'a', 'c', 'e', 'f'],
        'Fee'    : [1, 8, 3, 6, 12, 89, 12, 5, 9, 34, 15, 65, 60, 20],
        }
    df = pd.DataFrame(technologies)
    print(df)

    # print('Group by: Courses, Fee')
    # df2=df.sort_values(['Courses','Fee'], ascending=False).groupby('Courses').head()
    # print(df2)

    print('Group by: Courses, Fee  -  max->min by max of each group')
    # max->min by max of each group
    df2 = df.copy()
    df2['max'] = df2.groupby('Courses')['Fee'].transform('max')
    df2 = df2.sort_values(['max', 'Fee'], ascending=False).drop('max', axis=1)
    print(df2)

    print('Group by: Courses, Fee  -  min->max by min of each group')
    # min->max by min of each group
    df2 = df.copy()
    df2['min'] = df2.groupby('Courses')['Fee'].transform('min')
    df2 = df2.sort_values(['min', 'Fee'], ascending=True).drop('min', axis=1)
    print(df2)

    print('Group by: Courses, Fee  -  min->max of each group / max->min within group')
    # min->max of each group / max->min within group
    df2 = df.copy()
    df2['max'] = df2.groupby('Courses')['Fee'].transform('max')
    df2['diff'] = df2['max'] - df2['Fee']
    df2 = df2.sort_values(['max', 'diff'], ascending=True)  # .drop(['max', 'diff'], axis=1)
    print(df2)

    print('Group by: Courses, Fee  -  max->min of each group / min->max within group')
    # max->min of each group / min->max within group
    df2 = df.copy()
    df2['min'] = df2.groupby('Courses')['Fee'].transform('min')
    df2['diff'] = df2['min'] - df2['Fee']
    df2 = df2.sort_values(['min', 'diff'], ascending=False).drop(['min', 'diff'], axis=1)
    print(df2)


if __name__ == '__main__':
    main()
