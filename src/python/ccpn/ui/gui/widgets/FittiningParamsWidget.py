"""
A widget to handle the  Fitting Parameters in the series Analysis Settings.

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
__dateModified__ = "$dateModified: 2024-11-12 13:25:38 +0000 (Tue, November 12, 2024) $"
__version__ = "$Revision: 3.2.10 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date:2024-07-30 17:22:58 +0100 (Tue, July 30, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================


import pandas as pd
import numpy as np
from ccpn.ui.gui.widgets.Icon import Icon
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
import lmfit
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.table.Table import Table
from ccpn.ui.gui.widgets.table._TableCommon import (EDIT_ROLE, DISPLAY_ROLE, TOOLTIP_ROLE,
                                                    BACKGROUND_ROLE, FOREGROUND_ROLE, CHECK_ROLE, ICON_ROLE, SIZE_ROLE,
                                                    FONT_ROLE, CHECKABLE, ENABLED, SELECTABLE, CHECKED, UNCHECKED,
                                                    VALUE_ROLE,
                                                    INDEX_ROLE, BORDER_ROLE)
from ccpn.ui.gui.widgets.table._TableModel import _TableModel
from ccpn.ui.gui.popups.Dialog import CcpnDialog
from ccpn.util.floatUtils import numZeros


MAX_ROWS = 7
LOCKED = 'Locked'
NAME = 'Name'
VALUE = 'Value'
FIXED = 'Fixed'
VARY = 'Vary'
MIN = 'Min'
MAX = 'Max'
AUTO = 'Auto'
DESCRIPTION = 'Description'


class _ParamTableModel(_TableModel):
    """
    """
    _MAXCHARS = 1000

    def data(self, index, role=DISPLAY_ROLE):
        """Return the data/roles for the model.
        """
        if not index.isValid():
            return None

        try:
            # get the source cell
            fRow = self._filterIndex[index.row()] if self._filterIndex is not None and 0 <= index.row() < len(
                    self._filterIndex) else index.row()
            row, col = self._sortIndex[fRow], index.column()

            if role == DISPLAY_ROLE:
                # need to discard columns that include check-boxes
                val = self._df.iat[row, col]
                try:
                    # try and get the function from the column-definitions
                    fmt = self._view._columnDefs._columns[col].format
                    return fmt % val
                except Exception:
                    # fallback - float/np.float - round to 3 decimal places. This should be settable, ideally even by the user,
                    if isinstance(val, (float, np.floating)):
                        try:
                            maxDecimalToShow = 3
                            if abs(val) > 1e6:  # make it scientific annotation if a huge/tiny number
                                value = f'{val:.{maxDecimalToShow}e}'
                            elif numZeros(val) >= maxDecimalToShow:
                                #e.g.:  if is 0.0001 will show as 1e-4 instead of 0.000
                                value = f'{val:.{maxDecimalToShow}e}'
                            else:
                                # just rounds to the third decimal
                                value = f'{val:.{maxDecimalToShow}f}'
                        except Exception:
                            value = str(val)
                    elif isinstance(val, bool) and self._enableCheckBoxes:
                        # an empty cell with a checkbox - allow other text?
                        return None
                    else:
                        value = str(val)
                return value

            elif role == ICON_ROLE and col == 0 and self._df.at[row, LOCKED]:
                return self._view.lockIcon  # Return the lock icon for the first column

            elif role == ICON_ROLE and col == 0 and not self._df.at[row, LOCKED]:
                return self._view.unLockIcon  # Return the lock icon for the first column

            elif role == VALUE_ROLE:
                val = self._df.iat[row, col]
                try:
                    # convert np.types to python types
                    return val.item()  # type np.generic
                except Exception:
                    return val

            elif role == BACKGROUND_ROLE:
                if (indexGui := self._guiState[row, col]):
                    # get the colour from the dict
                    return indexGui.get(role)

            elif role == FOREGROUND_ROLE:
                if (indexGui := self._guiState[row, col]):
                    # get the colour from the dict
                    return indexGui.get(role)
                # return the default foreground colour
                return self._defaultForegroundColour

            elif role == BORDER_ROLE:
                if (indexGui := self._guiState[row, col]):
                    # get the colour from the dict
                    return bool(indexGui.get(BACKGROUND_ROLE))

            elif role == TOOLTIP_ROLE:
                if self._view._toolTipsEnabled:
                    data = self._df.iat[row, col]
                    return str(data)

            elif role == EDIT_ROLE:
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

            elif role == INDEX_ROLE:
                # return a dict of item-data?
                return (row, col)

            elif role == FONT_ROLE:
                if (indexGui := self._guiState[row, col]):
                    # get the font from the dict
                    return indexGui.get(role)

            elif role == CHECK_ROLE and self._enableCheckBoxes:
                if isinstance((val := self._df.iat[row, col]), bool):
                    # bool to checkbox state
                    return CHECKED if val else UNCHECKED
                return None

            elif role == SIZE_ROLE:
                # this is required to disable the bbox calculation for the default QT functionality
                return QtCore.QSize(16, 24)

        except Exception:
            pass

        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return str(self._df.columns[section])

        if role == QtCore.Qt.SizeHintRole and orientation == QtCore.Qt.Horizontal:
            header_name = str(self._df.columns[section])
            if header_name in self._view.columnsMinWidths:
                return QtCore.QSize(self._view.columnsMinWidths[header_name], -1)

        return super().headerData(section, orientation, role)

    def flags(self, index):
        """Return the item flags for the given index."""
        if not index.isValid():
            return Qt.NoItemFlags

        # Get the row and column indices
        fRow = self._filterIndex[index.row()] if self._filterIndex is not None and 0 <= index.row() < len(
                self._filterIndex) else index.row()
        row = self._sortIndex[fRow]
        col = index.column()

        # Get the column name from the DataFrame
        column_name = self._df.columns[col]

        # List of column names that should be non-editable
        non_editable_columns = [NAME, LOCKED, DESCRIPTION]  # Add column names that should not be editable

        # Disable editing for rows that are locked or specific columns
        if self._df.at[row, LOCKED] or column_name in non_editable_columns:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled  # Non-editable

        # Default flags for editable items
        return super().flags(index)


class _ParamsTable(Table):
    _defaultEditable = False
    _enableSearch = False
    _enableDelete = False
    _enableExport = False
    _enableCopyCell = False
    _columnDefs = None
    _enableSelectionCallback = False
    _enableActionCallback = False
    _tableMenuEnabled = False
    _toolTipsEnabled = True
    tableModelClass = _ParamTableModel
    showEditIcon = True
    columnsMinWidths = {
        NAME : 100,
        VALUE: 80,
        FIXED: 50
        }

    def __init__(self, parent, dataFrame, dataChangedCallback=None, **kwds):
        super().__init__(parent, df=dataFrame, focusBorderWidth=0, cellPadding=10, showGrid=False,
                         setWidthToColumns=False, setHeightToRows=False, _resize=True,
                         showVerticalHeader=False,
                         **kwds)

        self.model()._enableCheckBoxes = True  # make boolean appear as checkboxes (disables double-click on boolean)
        self.model().defaultFlags = ENABLED | SELECTABLE | CHECKABLE  # checkboxes are clickable
        self.setEditable(True)  # double-clicking disabled (doesn't affect checkboxes)
        self.setAlternatingRowColors(False)
        # set the horizontalHeader information
        header = self.horizontalHeader()
        # header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setStretchLastSection(False)
        header.setSectionsClickable(False)
        header.setSortIndicatorShown(False)

        # verticalHeader = self.verticalHeader()
        # verticalHeader.hide()
        self.setSelectionMode(QtWidgets.QTableView.NoSelection)
        self.lockIcon = Icon('icons/locked').pixmap(int(self.model()._chrHeight), int(self.model()._chrHeight))
        self.unLockIcon = Icon('icons/unlocked').pixmap(int(self.model()._chrHeight), int(self.model()._chrHeight))
        self.headerColumnMenu.setInternalColumns([LOCKED])
        if dataChangedCallback is not None:
            self.model().dataChanged.connect(dataChangedCallback)

    def getDataFrame(self, includeHiddenColumns=False):
        return self.model()._getVisibleDataFrame(includeHiddenColumns=includeHiddenColumns)

    def _raiseTableContextMenu(self, pos):
        """Bypass the table menu
        """
        return


class FittingParamWidget(Frame):

    def __init__(self, parent, fittingModel, callback=None, **kwds):
        super().__init__(parent, minimumSizes=(50, 150), margins=(0, 10, 0, 10), setLayout=True, **kwds)

        self._fittingParamWrapper = FittingParamWrapper(fittingModel)
        df = self._fittingParamWrapper.getDataFrameFromParams()
        df[FIXED] = df[FIXED].astype(object)  #need to be object to enable the checkboxes on the table
        self.table = _ParamsTable(self, df, dataChangedCallback=self._tableHasChanged, grid=[0, 0])
        self._callback = callback

    def getDataFrame(self):
        return self.table.getDataFrame()

    def getUpdatedParams(self):
        """Get the Params object from the Gui Table """
        df = self.getDataFrame()
        return self._fittingParamWrapper.getParamsFromDataFrame(df)

    def _tableHasChanged(self, *args):
        params = self.getUpdatedParams()
        if self._callback:
            self._callback(params)
        return params


class FittingParamWrapper(object):

    def __init__(self, fittingModel):
        self.fittingModel = fittingModel
        self._minimiser = self.fittingModel.Minimiser
        self.params = self._minimiser.fetchParams(self._minimiser)
        self._userParams = self._minimiser._userParams
        self._userParamNames = self._minimiser.getUserParamNames(self._minimiser)
        self._fixedParamNames = self._minimiser.getFixedParamNames(self._minimiser)

    def getDataFrameFromParams(self):
        """
        Convert  lmfit.Parameters object to a pandas DataFrame to be displayed on the Gui Object

        Returns:
        pd.DataFrame: DataFrame with parameter names and their attributes
        """

        df = pd.DataFrame([])
        params = self._minimiser._mergeUserParams(self.params, self._minimiser._userParams)
        for i, (name, param) in enumerate(params.items()):
            _min, _max = self._getMinMaxFromParam(name, param)
            vary = param.vary if param.vary is not None else True  # fetch the information from the existing param. it could have set previously by the user.
            fixed = not vary
            description = self._minimiser.paramsDescription.get(name, '')
            df.loc[i, NAME] = name
            df.loc[i, VALUE] = param.value if name in self._userParamNames else AUTO
            df.loc[i, FIXED] = fixed
            df.loc[i, MIN] = _min
            df.loc[i, MAX] = _max
            df.loc[i, DESCRIPTION] = description
            df.loc[i, LOCKED] = name not in self._userParamNames

        # apply a sorting . Show the User editable at the top and sort alphabetically
        key = lambda x: pd.Categorical(x, categories=sorted(self._userParamNames) + sorted(
                x[~x.isin(self._userParamNames)]), ordered=True)
        df = df.sort_values(by=NAME, key=key).reset_index(drop=True)
        return df

    @staticmethod
    def getParamsFromDataFrame(df):
        params = lmfit.Parameters()
        for ix, row in df.iterrows():
            name = row[NAME]
            value = row[VALUE]
            vary = not row[FIXED]
            if isinstance(value, str):
                value = -np.inf
            _max = row[MAX]
            if isinstance(_max, str):
                _max = np.inf
            _min = row[MIN]
            if isinstance(_min, str):
                _min = -np.inf
            param = lmfit.Parameter(name=name, value=value, min=_min, max=_max, vary=vary)
            params.add(param)
        return params

    def _getMinMaxFromParam(self, name, param, ):
        """Get the min amd Max from the params if conditions apply. Most likely to be Auto or Inf """
        minMax = ()
        for att in ['min', 'max']:
            _att = getattr(param, att, None)
            if _att is None:
                if name in self._userParamNames:
                    value = np.inf
                else:
                    value = AUTO
            else:
                if name in self._userParamNames:
                    value = _att
                else:
                    value = AUTO
            minMax += (value,)
        return minMax[0], minMax[1]


#=========================================================================================
# main
#=========================================================================================

def main():
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.framework.lib.experimentAnalysis.fittingModels.binding.SaturationModels import \
        FractionBindingWithVariableTargetConcentrationModel

    model = FractionBindingWithVariableTargetConcentrationModel

    app = TestApplication()
    popup = CcpnDialog(windowTitle='Test', setLayout=True)
    popup.setGeometry(200, 200, 200, 200)

    widget = FittingParamWidget(popup, model, editableParamNames=['constant'], grid=(0, 0))
    params = widget.getUpdatedParams()
    popup.exec_()


if __name__ == '__main__':
    main()
