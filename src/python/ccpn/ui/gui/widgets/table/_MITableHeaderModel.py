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
__dateModified__ = "$dateModified: 2024-10-16 18:41:25 +0100 (Wed, October 16, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-01-27 14:46:16 +0100 (Fri, January 27, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
import pandas as pd

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.table._TableCommon import USER_ROLE, DISPLAY_ROLE, \
    TOOLTIP_ROLE, ICON_ROLE, SIZE_ROLE, ENABLED, SELECTABLE, ORIENTATIONS


#=========================================================================================
# _MITableHeaderModelABC
#=========================================================================================

class _MITableHeaderModelABC(QtCore.QAbstractTableModel):
    """A model/view to show pandas DataFrames as a table.
    Allows for the use of single/multiIndex columns and indexes.

    The HeaderModel defines the communication between the cells in the header
    and the underlying pandas dataFrame.
    """
    _CHECKROWS = 10
    _MINCHARS = 4
    _MAXCHARS = 100
    _chrWidth = 12
    _chrHeight = 12
    _chrPadding = 8

    showEditIcon = True
    defaultFlags = SELECTABLE | ENABLED
    _defaultEditable = False

    _guiState = None

    def __init__(self, parent, *, df=None, orientation='horizontal'):
        super().__init__()

        if not isinstance(df, pd.DataFrame):
            raise ValueError('df must be a pd.DataFrame')
        orientation = ORIENTATIONS.get(orientation)
        if orientation is None:
            raise ValueError(f'orientation not in {list(ORIENTATIONS.keys())}')

        self._parent = parent
        self._df = df
        self.orientation = orientation

        if parent:
            fontMetric = QtGui.QFontMetricsF(parent.font())
            bbox = fontMetric.boundingRect

            # get an estimate for an average character width/height - must be floats for estimate-column-widths
            test = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,./;\<>?:|!@£$%^&*()'
            self._chrWidth = 1 + bbox(test).width() / len(test)
            self._chrHeight = bbox('A').height() + self._chrPadding

        # create a pixmap for the editable icon (currently a pencil)
        self._editableIcon = Icon('icons/editable').pixmap(int(self._chrHeight), int(self._chrHeight))

        self.clearSpans()

    @property
    def df(self):
        """Return the current dataFrame (not a copy).
        """
        return self._df

    @df.setter
    def df(self, value):
        """Replace the dataFrame and update the model.

        :param value: pandas dataFrame
        :return:
        """
        self.beginResetModel()

        # set the dataFrame
        self._df = value

        # notify that the data has changed
        self.endResetModel()

    def rowCount(self, parent=None):
        """Number of rows in the header.
        """
        if self.orientation == Qt.Horizontal:
            return self._df.columns.nlevels
        else:
            return self._df.shape[0]

    def columnCount(self, parent=None):
        """Number of columns in the header.
        """
        if self.orientation == Qt.Horizontal:
            return self._df.shape[1]
        else:
            return self._df.index.nlevels

    def data(self, index, role=None):
        if not (index.isValid()):
            return

        if role in [DISPLAY_ROLE, TOOLTIP_ROLE]:

            if self.orientation == Qt.Horizontal:
                # get the source cell
                row, col = index.row(), index.column()

                if type(self._df.columns) == pd.MultiIndex:
                    return str(self._df.columns.values[col][row])
                else:
                    return str(self._df.columns.values[col])

            else:
                # get the source cell from the sort-indexing to get the correct cell data
                _sortIndex = self._parent.model()._sortIndex
                row, col = _sortIndex[index.row()], index.column()

                if type(self._df.index) == pd.MultiIndex:
                    return str(self._df.index.values[row][col])
                else:
                    return str(self._df.index.values[row])

        elif role == USER_ROLE:
            if self.orientation == Qt.Horizontal:
                # get the source cell
                row, col = index.row(), index.column()

            else:
                # get the source cell from the sort-indexing to get the correct cell data
                _sortIndex = self._parent.model()._sortIndex
                row, col = _sortIndex[index.row()], index.column()

            return self._spanTopLeft[row, col]

    def headerData(self, section, orientation, role=None):
        # The headers of this table will show the level names of the MultiIndex
        if role in [DISPLAY_ROLE, TOOLTIP_ROLE]:

            if self.orientation == Qt.Horizontal and orientation == Qt.Vertical:
                if type(self._df.columns) == pd.MultiIndex:
                    return str(self._df.columns.names[section])
                else:
                    return str(self._df.columns.name)

            elif self.orientation == Qt.Vertical and orientation == Qt.Horizontal:
                if type(self._df.index) == pd.MultiIndex:
                    return str(self._df.index.names[section])
                else:
                    return str(self._df.index.name)

    def flags(self, index):
        # return the default-state for the table
        return self.defaultFlags

    def _isColumnEditable(self, index):
        """Return whether the column number is editable.
        """
        try:
            # return True if the column contains an edit function and table is editable
            # NOTE:ED - need to read these from the main table-object
            return False
        except Exception:
            return self._defaultEditable

    def clearSpans(self):
        """Clear the span information
        """
        # create numpy arrays to match the data that will hold background colour
        self._spanTopLeft = np.empty((self.rowCount(), self.columnCount()), dtype=object)


#=========================================================================================
# _HorizontalMITableHeaderModel
#=========================================================================================

class _HorizontalMITableHeaderModel(_MITableHeaderModelABC):
    """A model/view to show pandas DataFrames as a table.
    Allows for the use of single/multiIndex columns and indexes.

    The HeaderModel defines the communication between the cells in the header
    and the underlying pandas dataFrame.
    This is the horizontal-header-model.
    """

    def rowCount(self, parent=None):
        """Number of rows in the header.
        """
        return self._df.columns.nlevels

    def columnCount(self, parent=None):
        """Number of columns in the header.
        """
        return self._df.shape[1]

    def data(self, index, role=None):
        if not (index.isValid()):
            return

        # get the source cell
        row, col = index.row(), index.column()

        if role in [DISPLAY_ROLE, TOOLTIP_ROLE]:
            if type(self._df.columns) == pd.MultiIndex:
                return str(self._df.columns.values[col][row])
            else:
                return str(self._df.columns.values[col])

        elif role == USER_ROLE:
            return self._spanTopLeft[row, col]

        elif role == ICON_ROLE and self._isColumnEditable(index) and self.showEditIcon:
            # return the pixmap
            return self._editableIcon

        # this is the value that is queried when calling sizeHintForRow/Column for the header
        # not required
        # elif role == SIZE_ROLE:
        #     print(f'=>> header beep   {index.row()} {index.column()}')
        #     # return QtCore.QSize(16, 24)

    def headerData(self, section, orientation, role=None):
        # The headers of this table will show the level names of the MultiIndex
        if role in [DISPLAY_ROLE, TOOLTIP_ROLE] and orientation == Qt.Vertical:
            if type(self._df.columns) is pd.MultiIndex:
                return str(self._df.columns.names[section])
            else:
                return str(self._df.columns.name)

        # possibly not needed, but slightly quicker than the default bbox
        # elif role == SIZE_ROLE:
        #     print(f'==> header column size  {section}, {orientation}')
            # return super().headerData(section, orientation, role)
        #     # process the heights/widths of the headers
        #     if orientation == QtCore.Qt.Vertical:
        #         # print(f'size-hz   {section}    {self._parent._indexHeader.sizeHintForRow(section)}')
        #         try:
        #             # vertical-height of horizontal header
        #             if type(self._df.columns) is pd.MultiIndex:
        #                 txts = [col[section] for col in self._df.columns.values]
        #             else:
        #                 txts = list(self._df.columns)
        #             height = int(max(len(txt.split('\n') * self._chrHeight) for txt in txts))
        #
        #             # return the height of the maximum text in the row, width is discarded
        #             return QtCore.QSize(int(self._chrWidth), height)
        #
        #         except Exception:
        #             # return the size
        #             return QtCore.QSize(int(self._chrWidth), int(self._chrHeight))
        #
        #     # print(f'size-hz   {section}    {self._parent._columnHeader.sizeHintForColumn(section)}')
        #     # column-width, return the default QSize
        #     return QtCore.QSize(int(self._chrWidth), int(self._chrHeight))

    def _isColumnEditable(self, index):
        try:
            # get the source cell
            row, col = index.row(), index.column()
            rowSpan, _colSpan = self._parent._columnHeader.rowSpan(row, col), self._parent._columnHeader.columnSpan(row, col)

            return self._defaultEditable and rowSpan + row == self.rowCount()

        except Exception:
            return self._defaultEditable

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
        except Exception:
            maxLen = 0

        maxLen = max(maxLen + 3, self._MINCHARS)  # never smaller than 4 characters

        # for _count in range(self._CHECKROWS):
        # # for ss in range(min(self.rowCount(), self._CHECKROWS)):
        #     row = random.randint(0, self.rowCount() - 1)

        # iterate over a few rows to get an estimate
        for row in range(min(self.rowCount(), self._CHECKROWS)):
            data = self._df.iat[row, col]

            # float/np.float - round to 3 decimal places
            if isinstance(data, (float, np.floating)):
                newLen = len(f'{data:.3f}')
            else:
                data = str(data)
                if '\n' in data:
                    # get the longest row from the cell
                    dataRows = data.split('\n')
                    newLen = max(len(_chrs) for _chrs in dataRows)
                else:
                    newLen = len(data)

            # update the current maximum
            maxLen = max(newLen, maxLen)

        return round(min(self._MAXCHARS, maxLen) * self._chrWidth)


#=========================================================================================
# _VerticalMITableHeaderModel
#=========================================================================================

class _VerticalMITableHeaderModel(_MITableHeaderModelABC):
    """A model/view to show pandas DataFrames as a table.
    Allows for the use of single/multiIndex columns and indexes.

    The HeaderModel defines the communication between the cells in the header
    and the underlying pandas dataFrame.
    This is the vertical-header-model.
    """

    def rowCount(self, parent=None):
        """Number of rows in the header.
        """
        return self._df.shape[0]

    def columnCount(self, parent=None):
        """Number of columns in the header.
        """
        return self._df.index.nlevels

    def data(self, index, role=None):
        if not (index.isValid()):
            return

        # get the source cell from the sort-indexing to get the correct cell data
        _sortIndex = self._parent.model()._sortIndex
        row, col = _sortIndex[index.row()], index.column()

        if role in [DISPLAY_ROLE, TOOLTIP_ROLE]:
            if type(self._df.index) == pd.MultiIndex:
                return str(self._df.index.values[row][col])
            else:
                return str(self._df.index.values[row])

        elif role == QtCore.Qt.UserRole:
            return self._spanTopLeft[row, col]

    def headerData(self, section, orientation, role=None):
        # The headers of this table will show the level names of the MultiIndex
        if role in [DISPLAY_ROLE, TOOLTIP_ROLE] and orientation == Qt.Horizontal:
            if type(self._df.index) is pd.MultiIndex:
                return str(self._df.index.names[section])
            else:
                return str(self._df.index.name)

        # possibly not needed, but slightly quicker than the default bbox
        # elif role == SIZE_ROLE:
        #     # process the heights/widths of the headers
        #     if orientation == QtCore.Qt.Horizontal:
        #         try:
        #             # width of vertical-header
        #             print(f'size-vt   {section}    {self._parent._columnHeader.sizeHintForColumn(section)}')
        #             # horizontal-width of vertical header
        #             if type(self._df.index) is pd.MultiIndex:
        #                 txts = [row[section] for row in self._df.index.values]
        #             else:
        #                 txts = list(self._df.index)
        #
        #             width = max(len(splt) for txt in txts for splt in txt.split('\n'))
        #             _w = int(min(self._MAXCHARS, width) * self._chrWidth) + 2
        #
        #             # return the width of the maximum text in the row, height is discarded
        #             return QtCore.QSize(_w, int(self._chrHeight))
        #
        #         except Exception:
        #             # return the size
        #             return QtCore.QSize(int(self._chrWidth), int(self._chrHeight))
        #
        #     # print(f'size-vt   {section}    {self._parent._indexHeader.sizeHintForRow(section)}')
        #     # row-height, return the default QSize
        #     return QtCore.QSize(int(self._chrWidth), int(self._chrHeight))
