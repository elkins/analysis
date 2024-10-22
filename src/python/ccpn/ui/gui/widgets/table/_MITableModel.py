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
__date__ = "$Date: 2023-01-27 14:45:30 +0100 (Fri, January 27, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from PyQt5 import QtCore

from ccpn.ui.gui.widgets.table._TableCommon import DISPLAY_ROLE, TOOLTIP_ROLE, SIZE_ROLE, ICON_ROLE
from ccpn.ui.gui.widgets.table._TableModel import _TableModel


#=========================================================================================
# _MITableModel
#=========================================================================================

class _MITableModel(_TableModel):
    """A model/view to show pandas DataFrames as a table.
    Allows for the use of single/multiIndex columns and indexes.

    The Model defines the communication between the cells and the underlying Pandas-dataFrame.
    """

    # def flags(self, index):
    #     # Set the table to be editable
    #     return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
    #
    # def _isColumnEditable(self, col):
    #     """Return whether the column number is editable.
    #     """
    #     ...

    def data(self, index, role=DISPLAY_ROLE):
        """Return the data/roles for the model.
        """
        if not index.isValid():
            return None

        if role == DISPLAY_ROLE:
            try:
                # get the source cell
                fRow = (self._filterIndex[index.row()]
                        if self._filterIndex is not None and 0 <= index.row() < len(self._filterIndex) else
                        index.row())
                row, col = self._sortIndex[fRow], index.column()

                # need to discard columns that include check-boxes
                val = self._df.iat[row, col]

                if func := self._view._columnDefs and self._view._columnDefs[col].format:
                    # get the function from the column-definitions
                    try:
                        value = func(val, row=self._df.iloc[row], col=col)
                    except Exception:
                        # may be simple func
                        value = func(val)

                # default to a float or str
                elif isinstance(val, (float, np.floating)):

                    # make it scientific annotation if a huge/tiny number
                    try:
                        value = f'{val:.3f}' if (1e-6 < val < 1e6) or val == 0.0 else f'{val:.3e}'
                    except Exception:
                        value = str(val)
                else:
                    value = str(val)

                return value

            except Exception:
                return None

        # elif role == SIZE_ROLE:
        #     # get the source cell
        #     return self._bbox(str(self._df.iat[index.row(), index.column()])).size() + self._cellBorder

            # # float/np.float - round to 3 decimal places
            # if isinstance(data, (float, np.floating)):
            #     newLen = len(f'{data:.3f}') + 1
            # else:
            #     data = str(data)
            #     if '\n' in data:
            #         # get the longest row from the cell
            #         dataRows = data.split('\n')
            #         newLen = max(len(_chrs) for _chrs in dataRows) + 1
            #     else:
            #         newLen = len(data) + 1
            #
            # # update the current maximum
            # # maxLen = max(newLen, maxLen)
            # _w = int(min(self._MAXCHARS, max(newLen, self._MINCHARS)) * (self._chrWidth + 1)) + 1
            #
            # return QtCore.QSize(_w, int(self._chrHeight))

        # check the rest of the role-types
        return super().data(index, role)

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
                return self._view._columnDefs[col].toolTip
            except Exception:
                return None

        elif role == SIZE_ROLE:
            # print(f'==> row/column main-table  {col}  {orientation}')
            # return QtCore.QSize(12, 12)
            # return super().headerData(col, orientation, role)
            # process the heights/widths of the headers
            if orientation == QtCore.Qt.Horizontal:
                # allow for the width of the sort-icon
                return QtCore.QSize(self._view._columnHeader.sizeHintForColumn(col) + 16, int(self._chrHeight))
            return QtCore.QSize(int(self._chrWidth), self._view._indexHeader.sizeHintForRow(col))

                # try:
                #     # get the estimated width of the column, also for the last visible column
                #     if self._view._columnDefs and (width := self._view._columnDefs[col].columnWidth) is not None:
                #         # use the fixed-column width
                #         return QtCore.QSize(width, self._chrHeight)
                #
                #     width = self._estimateColumnWidth(col)
                #
                #     # return the size
                #     return QtCore.QSize(width, int(self._chrHeight))
                #
                # except Exception:
                #     # return the default QSize
                #     return QtCore.QSize(int(self._chrWidth), int(self._chrHeight))

            # return the default QSize for vertical header
            # return QtCore.QSize(int(self._chrWidth), int(self._chrHeight))

        elif role == ICON_ROLE and self._isColumnEditable(col) and self.showEditIcon:
            # return the pixmap
            return self._editableIcon

        return None
