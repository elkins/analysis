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
__dateModified__ = "$dateModified: 2024-10-02 16:39:51 +0100 (Wed, October 02, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-01-20 15:57:58 +0100 (Fri, January 20, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

from dataclasses import dataclass, field
from PyQt5 import QtWidgets
import pandas as pd
from ccpn.ui.gui.lib.GuiStripContextMenus import (_selectedPeaksMenuItem, _addMenuItems,
                                                  _getNdPeakMenuItems, _setEnabledAllItems)
from ccpn.ui.gui.widgets.table._TableAdditions import TableMenuABC
from ccpn.ui.gui.widgets.SearchWidget import _TableFilterABC, Exclude, NotEqual
from ccpn.util.DataEnum import DataEnum


UNITS = ['ppm', 'Hz', 'point']
HeaderRow = 'Row'
HeaderIndex = '#'
HeaderMatch = 'Match'
HeaderObject = '_object'
HeaderExpand = 'Expand'
HeaderRestraint = 'Restraint Pid'  # needs to match the column-heading in the violation-table
HeaderAtoms = 'Atoms'
HeaderViolation = '_isViolated'
HeaderTarget = 'Target Value'
HeaderLowerLimit = 'Lower Limit'
HeaderUpperLimit = 'Upper Limit'
HeaderMin = 'Min'
HeaderMax = 'Max'
HeaderMean = 'Mean'
HeaderStd = 'STD'
HeaderCount1 = 'Count > 0.3'
HeaderCount2 = 'Count > 0.5'
nefHeaders = ['restraintpid', 'atoms', 'is_violated',
              'target_value', 'lower_limit', 'upper_limit',
              'min', 'max', 'mean', 'std',
              'count_0_3', 'count_0_5']
Headers = [HeaderRestraint,
           HeaderAtoms,
           HeaderViolation,
           HeaderTarget,
           HeaderLowerLimit,
           HeaderUpperLimit,
           HeaderMin,
           HeaderMax,
           HeaderMean,
           HeaderStd,
           HeaderCount1,
           HeaderCount2]
_OLDHEADERS = {'RestraintPid': HeaderRestraint,
               'Count>0.3'   : HeaderCount1,
               'Count>0.5'   : HeaderCount2}
INDEXCOL = (HeaderRow, HeaderRow)
PEAKSERIALCOL = (HeaderMatch, HeaderMatch)
OBJCOL = (HeaderObject, HeaderObject)

PymolScriptName = 'Restraint_Pymol_Template.py'
_COLLECTION = 'Collection'
_COLLECTIONBUTTON = 'CollectionButton'
_SPECTRUMDISPLAYS = 'SpectrumDisplays'
_RESTRAINTTABLES = 'RestraintTables'
_VIOLATIONTABLES = 'ViolationTables'
_RESTRAINTTABLE = 'restraintTable'
_VIOLATIONRESULT = 'violationResult'
_CLEARBUTTON = 'ClearButton'
_COMPARISONSETS = 'ComparisonSets'

_DEFAULTMEANTHRESHOLD = 0.0
ALL = '<Use all>'


class SearchModes(DataEnum):
    # name, value, description, dataValue
    INCLUDE = 0, 'Include partial', 'Include peak-groups that match on at least one row.'
    EXCLUDE = 1, 'Exclude partial', 'Exclude peak-groups that do not match on all rows.'
    EXACT = 2, 'Exact', 'Ignore peak-groups, only return rows matching search.'


#=========================================================================================
# _ModuleHandler - information common to all classes/widgets in the module
#=========================================================================================

@dataclass
class _ModuleHandler(QtWidgets.QWidget):
    # Use a QWidget as it can handle signals - maybe for later

    # gui resources
    guiModule = None
    guiFrame = None

    # non-gui resources
    _restraintTables: list = field(default_factory=list)
    _outputTables: list = field(default_factory=list)
    _thisPeakList = None

    # don't like this holding on to widgets :|
    _collectionPulldown = None
    _collectionButton = None
    _displayListWidget = None
    _resTableWidget = None
    _outTableWidget = None
    _modulePulldown = None
    _searchModeRadio = None
    _includeNonPeaksCheckBox = None

    _meanLowerLimitSpinBox = None
    _autoExpandCheckBox = None
    _autoExpand = False
    _markPositions = False
    _autoClearMarks = False

    _restraintTableFilter: dict = field(default_factory=dict)
    _outputTableFilter: dict = field(default_factory=dict)
    _modulePulldownFilter: list = field(default_factory=list)
    _meanLowerLimit = 0.0

    comparisonSets: list = field(default_factory=list)


#=========================================================================================
# _RestraintOptions - additions to the right-mouse menu
#=========================================================================================

class _RestraintOptions(TableMenuABC):
    """Class to handle peak-driven Restraint Analysis options from a right-mouse menu.
    """

    def addMenuOptions(self, menu):
        """Add options to the right-mouse menu
        """
        parent = self._parent

        menu.addSeparator()
        _peakItem = _selectedPeaksMenuItem(None)
        _addMenuItems(parent, menu, [_peakItem])

        # _selectedPeaksMenu submenu - add to Strip._selectedPeaksMenu
        items = _getNdPeakMenuItems(menuId='Main')
        # attach to the _selectedPeaksMenu submenu
        _addMenuItems(parent, parent._selectedPeaksMenu, items)

    def setMenuOptions(self, menu):
        """Update options in the right-mouse menu
        """
        parent = self._parent
        submenu = parent._selectedPeaksMenu

        # Enable/disable menu items as required
        parent._navigateToPeakMenuMain.setEnabled(False)
        _setEnabledAllItems(submenu, bool(parent.current.peaks))

    #=========================================================================================
    # Properties
    #=========================================================================================

    ...

    #=========================================================================================
    # Class methods
    #=========================================================================================

    ...

    #=========================================================================================
    # Implementation
    #=========================================================================================

    ...


#=========================================================================================
# _DFTableFilter class uses QTableView and model to access data
#=========================================================================================

class _RestraintAITableFilter(_TableFilterABC):

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

    @staticmethod
    def preFilterTableDf(df: pd.DataFrame) -> pd.DataFrame:
        """Apply pre-search filtering to the pandas-dataFrame.

        Change visible ints/floats in the dataFrame to '-' if restraint-pids are not defined in the row.
        Allows '-' to be searched.

        :param pd.DataFrame df: source dataFrame
        :return: filtered dataFrame
        :rtype: pd.DataFrame
        """
        dfCache = df.copy()
        # apply functions to retrieve displayRole for all columns
        for colNum, colName in enumerate(dfCache.columns):
            if colName[1] == HeaderRestraint:
                colPid = colName[0]

                # process the following columns based on the restraint-pid
                # a little hardcoded?
                mask = dfCache.iloc[:, colNum].apply(lambda val: val not in [None, '', '-'])

                # clean the str for the first columns
                for colSub in [HeaderRestraint, HeaderAtoms]:
                    colCheck = (colPid, colSub)
                    if colCheck in dfCache.columns:
                        dfCache.loc[:, colCheck].apply(lambda value: str(value or ''))
                # clean the float values - hide with a '-' if the restraint-pid is missing
                for colSub in [HeaderTarget, HeaderLowerLimit, HeaderUpperLimit,
                               HeaderMin, HeaderMax, HeaderMean, HeaderStd]:
                    colCheck = (colPid, colSub)
                    if colCheck in dfCache.columns:
                        # True state
                        dfCache.loc[mask, colCheck].apply(lambda value: (f'{value:.3f}'
                                                                         if (1e-6 < value < 1e6) or value == 0.0 else
                                                                         f'{value:.3e}'))
                        # False state - use dash for cleaner table
                        dfCache.loc[~mask, colCheck] = '-'
                # clean the int values - hide with a '-' if the restraint-pid is missing
                for colSub in [HeaderCount1, HeaderCount2]:
                    colCheck = (colPid, colSub)
                    if colCheck in dfCache.columns:
                        # True state
                        dfCache.loc[mask, colCheck].apply(lambda value: int(value))
                        # False state - use dash for cleaner table
                        dfCache.loc[~mask, colCheck] = '-'
        return dfCache

    def postFilterTableDf(self, df: pd.DataFrame, dfFound: pd.Series, condition: str) -> pd.Series:
        """Apply post-search filtering to the pandas-dataFrame.

        Search for peaks in df, there are multiple occurrences, that appear in dfFound.
        Keep all peaks in the same group even if the search applies to a subset of the group.

        :param pd.DataFrame df: source dataFrame
        :param pd.Series dfFound: found mask
        :param str condition: search criterion
        :return: post-filtered dataFrame
        :rtype: pd.Series mask
        """
        if PEAKSERIALCOL not in df.columns:
            # can't filter on missing column
            return dfFound
        try:
            # NOTE:ED - nasty hack to get searchMode from parent :|
            idx = self._parent.resources._searchModeRadio.getIndex()
            searchMode = SearchModes(idx)
        except Exception:
            return dfFound

        if searchMode == SearchModes.EXACT:
            # return only the required rows, with no peak-grouping
            return dfFound

        xor = (searchMode == SearchModes.INCLUDE) ^ (condition in [Exclude, NotEqual])
        if xor:
            return (df[PEAKSERIALCOL]
                    .isin(df.loc[dfFound, PEAKSERIALCOL])
                    .where(df[PEAKSERIALCOL] != '-', other=dfFound)
                    )
        else:
            return ((~df[PEAKSERIALCOL]
                     .isin(df.loc[~dfFound, PEAKSERIALCOL]))
                    .where(df[PEAKSERIALCOL] != '-', other=dfFound)
                    )
