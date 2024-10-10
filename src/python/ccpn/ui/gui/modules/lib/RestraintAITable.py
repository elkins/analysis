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
__date__ = "$Date: 2023-01-20 16:18:53 +0100 (Fri, January 20, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

from functools import partial
import numpy as np
import pandas as pd
import warnings
from PyQt5 import QtCore, QtWidgets

from ccpn.core.Peak import Peak
from ccpn.core.PeakList import PeakList
from ccpn.core.RestraintTable import RestraintTable
from ccpn.ui._implementation.Strip import Strip
from ccpn.core.StructureData import StructureData
from ccpn.core.StructureEnsemble import StructureEnsemble
from ccpn.core.lib.CcpnSorting import universalSortKey
from ccpn.core.lib.Notifiers import Notifier
from ccpn.ui.gui.lib._CoreMITableFrame import _CoreMITableWidgetABC
from ccpn.ui.gui.lib._CoreTableFrame import _CoreTableFrameABC
import ccpn.ui.gui.modules.PyMolUtil as pyMolUtil
from ccpn.ui.gui.modules.lib.RestraintAITableCommon import (_RestraintOptions, UNITS, HeaderIndex, HeaderMatch,
                                                            HeaderObject, HeaderRestraint,
                                                            HeaderAtoms, HeaderViolation, HeaderTarget,
                                                            HeaderLowerLimit, HeaderUpperLimit,
                                                            HeaderMin, HeaderMax, HeaderMean, HeaderStd,
                                                            HeaderCount1, HeaderCount2, _OLDHEADERS, _VIOLATIONRESULT,
                                                            ALL, PymolScriptName, _RestraintAITableFilter,
                                                            INDEXCOL, PEAKSERIALCOL, OBJCOL)
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Column import ColumnClass, Column
from ccpn.ui.gui.widgets.GuiTable import _getValueByHeader
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.PulldownListsForObjects import PeakListPulldown
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.VLine import VLine
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.guiSettings import getColours, DIVIDER
from ccpn.util.Common import flattenLists
from ccpn.util.Logging import getLogger
from ccpn.util.Path import joinPath
from ccpn.util.OrderedSet import OrderedSet
from ccpn.ui.gui.widgets.table._MITableModel import _MITableModel
from ccpn.ui.gui.widgets.table._MITableDelegates import _ExpandVerticalCellDelegate
from ccpn.framework.Application import getProject


SELECT = '< Select >'
PULLDOWNSEPARATOR = '------'


#=========================================================================================
# _MultiSort
#=========================================================================================

class _MultiSort(_MITableModel):
    """Subclass of the basic table-model to allow sorting into groups
    """

    def _setSortOrder(self, column: int, order: QtCore.Qt.SortOrder = ...):
        """Get the new sort order based on the sort column and sort direction
        """
        self._oldSortIndex = self._sortIndex
        col = self._df.columns[column]

        # ignore multi-column sort on the first column, possibly an index or row number
        if self._view.enableMultiColumnSort and column > 0:
            with warnings.catch_warnings():
                warnings.filterwarnings(action='error', category=FutureWarning)

                try:
                    vp = self._df[self._df.columns[self._view.PIDCOLUMN]].apply(lambda val: universalSortKey(val))
                    vVal = self._df[col]  # .apply(lambda val: universalSortKey(val)) <- fails new[DIFF] calculation
                    newDf = pd.DataFrame([vp, vVal]).T
                    newDf.reset_index(drop=True, inplace=True)

                    groupCol = newDf.columns[0]  # first column should be the grouped column from source dataFrame
                    MAX, MIN, DIFF = 'max', 'min', 'diff'

                    if self._view.applySortToGroups:
                        # ascending/descending - group and subgroup
                        if self._view.horizontalHeader().sortIndicatorOrder() == QtCore.Qt.AscendingOrder:
                            newDf[MIN] = newDf.groupby([groupCol])[[col]].transform(MIN)
                            newDf = newDf.sort_values([MIN, groupCol, col], ascending=True).drop(MIN, axis=1)

                        else:
                            newDf[MAX] = newDf.groupby([groupCol])[[col]].transform(MAX)
                            newDf = newDf.sort_values([MAX, groupCol, col], ascending=False).drop(MAX, axis=1)

                    elif self._view.horizontalHeader().sortIndicatorOrder() == QtCore.Qt.AscendingOrder:
                        # ascending - min->max of each group / subgroup always max->min
                        newDf[MAX] = newDf.groupby([groupCol])[[col]].transform(MAX)
                        newDf[DIFF] = newDf[MAX] - newDf[col]
                        newDf = newDf.sort_values([MAX, groupCol, DIFF], ascending=True).drop([MAX, DIFF], axis=1)

                    else:
                        # descending - max->min of each group / subgroup always max->min
                        newDf[MAX] = newDf.groupby([groupCol])[[col]].transform(MAX)
                        newDf = newDf.sort_values([MAX, groupCol, col], ascending=False).drop(MAX, axis=1)

                        """
                        # KEEP THIS BIT! this is the opposite of the min->max / max->min (3rd option above)
                        max->min of each group / min->max within group
                        newDf[MIN] = newDf.groupby([groupCol])[[col]].transform(MIN)
                        newDf[DIFF] = newDf[MIN] - newDf[col]
                        newDf = newDf.sort_values([MIN, groupCol, DIFF], ascending=False).drop([MIN, DIFF], axis=1)
                        """

                    self._sortIndex = list(newDf.index)

                except Exception as es:
                    # log warning and drop-out to default sorting
                    getLogger().debug2(f'issue sorting table: probably unsortable column - {es}')

                    newDf = self._universalSort(self._df[col])
                    self._sortIndex = list(newDf.sort_values(ascending=(order == QtCore.Qt.AscendingOrder)).index)

        else:
            # single column sort on the specified column
            newDf = self._universalSort(self._df[col])
            self._sortIndex = list(newDf.sort_values(ascending=(order == QtCore.Qt.AscendingOrder)).index)

        # map the old sort-order to the new sort-order
        if self._filterIndex is not None:
            self._oldFilterIndex = self._filterIndex
            self._filterIndex = sorted([self._sortIndex.index(self._oldSortIndex[fi]) for fi in self._filterIndex])


#=========================================================================================
# _NewRestraintWidget - main widget for table, will need to change to _MultiIndex
#=========================================================================================

def _getContributions(restraint):
    # create a table of the cross-links for speed - does not update!
    return [' - '.join(sorted(ri)) for rc in restraint.restraintContributions
            for ri in rc.restraintItems]


def _checkRestraintFloat(offset, value, row, col):
    """Display the contents of the cell if the restraint-pid is valid - float
    Assumes multi-index
    """
    # row is a pandas-series, with the column-headers as the index
    # row.index[col][0] is the name of restraint in the top row of the table-header
    #   e.g. ('run1_xplor', 'Mean') or ('run2_xplor', 'Mean')
    if row[(row.index[col][0], HeaderRestraint)] not in [None, '', '-']:
        try:
            return f'{value:.3f}' if (1e-6 < value < 1e6) or value == 0.0 else f'{value:.3e}'
        except Exception:
            return str(value)

    return '-'


def _checkRestraintInt(offset, value, row, col):
    """Display the contents of the cell if the restraint-pid is valid - int
    Assumes multi-index
    """
    if row[(row.index[col][0], HeaderRestraint)] not in [None, '', '-']:
        return int(value)

    return '-'


class _NewRestraintTableWidget(_CoreMITableWidgetABC):
    """Class to present a peak-driven Restraint Analysis Inspector Table
    """
    className = '_NewRestraintWidget'
    attributeName = 'peakLists'

    _OBJECT = ('_object', '_object')
    OBJECTCOLUMN = ('_object', '_object')

    defaultHidden = [(HeaderIndex, HeaderIndex), OBJECTCOLUMN]
    _internalColumns = ['isDeleted', (HeaderIndex, HeaderIndex), OBJECTCOLUMN]  # columns that are always hidden

    defaultHiddenSubgroup = ['#',
                             # 'Restraint Pid',
                             'Target Value',
                             'Lower Limit',
                             'Upper Limit',
                             'Min',
                             'Max',
                             'STD',
                             'Count > 0.5',
                             'Count > 0.3',
                             ]

    # define the functions applied to the columns
    _subgroupColumns = [(HeaderRestraint, lambda val: str(val or '')),
                        (HeaderAtoms, lambda val: str(val or '')),
                        (HeaderViolation, None),
                        (HeaderTarget, partial(_checkRestraintFloat, 1)),
                        (HeaderLowerLimit, partial(_checkRestraintFloat, 2)),
                        (HeaderUpperLimit, partial(_checkRestraintFloat, 3)),
                        (HeaderMin, partial(_checkRestraintFloat, 4)),
                        (HeaderMax, partial(_checkRestraintFloat, 5)),
                        (HeaderMean, partial(_checkRestraintFloat, 6)),
                        (HeaderStd, partial(_checkRestraintFloat, 7)),
                        (HeaderCount1, partial(_checkRestraintInt, 8)),
                        (HeaderCount2, partial(_checkRestraintInt, 9)),
                        ]

    # define self._columns here - these are wrong
    columnHeaders = {'#'      : '#',
                     'Pid'    : 'Pid',
                     '_object': '_object',
                     'Comment': 'Comment',
                     }

    tipTexts = ('Peak serial number',
                'Pid of the Peak',
                'Object',
                'Optional user comment'
                )

    # define the notifiers that are required for the specific table-type
    tableClass = PeakList
    rowClass = Peak
    cellClass = None
    tableName = tableClass.className
    rowName = rowClass.className
    cellClassNames = None
    selectCurrent = True
    callBackClass = Peak
    search = False

    positionsUnit = UNITS[0]  # default

    # set the queue handling parameters
    _maximumQueueLength = 10

    # _autoExpand = False
    _selectedPeakList = None
    _defaultEditable = False

    # define _columns for multi-column sorting
    # NOTE:ED - check and remove redundant
    MERGECOLUMN = 1
    PIDCOLUMN = 1
    EXPANDERCOLUMN = 1
    SPANCOLUMNS = (1,)
    MINSORTCOLUMN = 0

    tableModelClass = _MultiSort
    enableMultiColumnSort = True
    # subgroups are always max->min
    applySortToGroups = False

    def __init__(self, parent, *args, **kwds):
        """Initialise the table
        """
        # override with fixed state
        kwds['showVerticalHeader'] = False
        kwds['showGrid'] = True
        kwds['alternatingRows'] = True
        super().__init__(parent, *args, **kwds)

        self.setTextElideMode(QtCore.Qt.ElideMiddle)

        delegate = _ExpandVerticalCellDelegate(parent=self.verticalHeader(), table=self)
        for col in self.SPANCOLUMNS:
            # add delegates to show expand/collapse icon
            self.setItemDelegateForColumn(col, delegate)

        # requires a special filter based in the table displayRole
        self.searchMenu.setFilterKlass(_RestraintAITableFilter)

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _sourceObjects(self):
        """Get/set the list of source objects
        """
        return (self._table and self._table.peaks) or []

    @_sourceObjects.setter
    def _sourceObjects(self, value):
        # shouldn't need this
        self._table.peaks = value

    @property
    def _sourceCurrent(self):
        """Get/set the associated list of current objects
        """
        return self.current.peaks

    @_sourceCurrent.setter
    def _sourceCurrent(self, value):
        if value:
            self.current.peaks = value
        else:
            self.current.clearPeaks()

    @property
    def _restraintTables(self):
        """Link to the parent containing the restraintTables
        """
        return self.resources._restraintTables

    @_restraintTables.setter
    def _restraintTables(self, value):
        self.resources._restraintTables = value

    @property
    def _outputTables(self):
        """Link to the parent containing the outputTables
        """
        return self.resources._outputTables

    @_outputTables.setter
    def _outputTables(self, value):
        self.resources._outputTables = value

    # @property
    # def _sourcePeaks(self):
    #     """Link to the parent containing the sourcePeaks
    #     """
    #     return self.resources._sourcePeaks
    #
    # @_sourcePeaks.setter
    # def _sourcePeaks(self, value):
    #     self.resources._sourcePeaks = value

    @property
    def _resTableWidget(self):
        """Link to the parent containing the _resTableWidget
        """
        return self.resources._resTableWidget

    @property
    def _outTableWidget(self):
        """Link to the parent containing the _outTableWidget
        """
        return self.resources._outTableWidget

    #=========================================================================================
    # Widget callbacks
    #=========================================================================================

    def selectionCallback(self, selected, deselected, selection, lastItem):
        """Handle item selection has changed in table - call user callback
        :param selected: table indexes selected
        :param deselected: table indexes deselected
        """
        # NOTE:ED - feedback loop? seems a little slow
        try:
            if not (objs := list(selection[self._OBJECT])):
                return
        except Exception as es:
            getLogger().debug2(f'{self.__class__.__name__}.selectionCallback: No selection\n{es}')
            return

        if objs is None:
            self.current.clearPeaks()
            self.current.clearRestraints()
        else:
            self.current.peaks = list(filter(lambda obj: isinstance(obj, Peak), selection[self._OBJECT]))
            # get all the restraint-pid columns
            resPids = OrderedSet(selection.loc[:, (slice(None), HeaderRestraint)].values.flatten())
            # get all the valid core-restraints
            getByPid = getProject().getByPid
            newRes = list(filter(None, map(lambda x: getByPid(x), resPids)))
            self.current.restraints = newRes

    def actionCallback(self, selection, lastItem):
        """Handle item selection has changed in table - call user callback
        """
        getLogger().debug(f'{self.__class__.__name__}.actionCallback')

        # If current strip contains the double-clicked peak will navigateToPositionInStrip
        from ccpn.ui.gui.lib.StripLib import navigateToPositionInStrip, _getCurrentZoomRatio

        # multi-selection table will return a list of objects
        if not (objs := list(selection[self._OBJECT])):
            return

        peak = objs[0] if isinstance(objs, (tuple, list)) else objs

        # optionally clear the marks
        if self.resources._autoClearMarks.isChecked():
            self.mainWindow.clearMarks()

        if dpObjs := self.resources._displayListWidget.getDisplays():
            # check which spectrumDisplays to navigate to - could be spectrumDisplay or strip
            for dp in dpObjs:
                if strp := dp if isinstance(dp, Strip) else (dp.strips and dp.strips[0]):

                    validPeakListViews = [pp.peakList for pp in strp.peakListViews if isinstance(pp.peakList, PeakList)]

                    if peak and peak.peakList in validPeakListViews:
                        widths = None

                        if peak.spectrum.dimensionCount <= 2:
                            widths = _getCurrentZoomRatio(strp.viewRange())
                        navigateToPositionInStrip(strip=strp,
                                                  positions=peak.position,
                                                  axisCodes=peak.axisCodes,
                                                  widths=widths,
                                                  markPositions=self.resources._markPositions.isChecked())
        else:
            getLogger().warning('Impossible to navigate to peak position. Set spectrumDisplays first')

    #=========================================================================================
    # Create table and row methods
    #=========================================================================================

    def _updateTableCallback(self, data):
        """Respond to table notifier.
        """
        obj = data[Notifier.OBJECT]
        if obj != self._table:
            # discard the wrong object
            return

        self._update()

    #=========================================================================================
    # Table context menu
    #=========================================================================================

    def addTableMenuOptions(self, menu):
        self.restraintMenu = _RestraintOptions(self, True)
        self._tableMenuOptions.append(self.restraintMenu)

        super().addTableMenuOptions(menu)

    #=========================================================================================
    # Table functions
    #=========================================================================================

    def _getTableColumns(self, source=None):
        """Add default columns plus the ones according to peakList.spectrum dimension
        format of column = ( Header Name, value, tipText, editOption)
        editOption allows the user to modify the value content by doubleclick
        """

        # NOTE:ED - don't think this is being used :|

        _restraintColumns = [((HeaderRestraint, HeaderRestraint), lambda rt: ''),
                             ((HeaderAtoms, HeaderAtoms), lambda rt: ''),
                             ((HeaderViolation, HeaderViolation), lambda rt: ''),
                             ((HeaderTarget, HeaderTarget), lambda rt: 0.0),
                             ((HeaderLowerLimit, HeaderLowerLimit), lambda rt: 0.0),
                             ((HeaderUpperLimit, HeaderUpperLimit), lambda rt: 0.0),
                             ((HeaderMin, HeaderMin), lambda rt: 0.0),
                             ((HeaderMax, HeaderMax), lambda rt: 0.0),
                             ((HeaderMean, HeaderMean), lambda rt: 0.0),
                             ((HeaderStd, HeaderStd), lambda rt: 0.0),
                             ((HeaderCount1, HeaderCount1), lambda rt: 0.0),
                             ((HeaderCount2, HeaderCount2), lambda rt: 0.0),
                             ]

        # define self._columns here
        # create the column objects
        _cols = [
            ((HeaderIndex, HeaderIndex), lambda row: _getValueByHeader(row, HeaderIndex), 'TipTex1', None, None),
            ((HeaderMatch, HeaderMatch), lambda row: _getValueByHeader(row, HeaderMatch), 'TipTex2', None, None),
            ((HeaderObject, HeaderObject), lambda row: _getValueByHeader(row, HeaderObject), 'TipTex3', None, None),
            ]

        # cSetLists = self._restraintTables
        # outTables = self._outputTables

        # column-headers
        cSetLists = list(filter(None, (cs.comparisonSet for cs in self.resources.comparisonSets)))

        if violationResults := [cSet for cSet in cSetLists if cSet.getTreeTables(depth=2, selected=True)]:
            for cSet in cSetLists:
                if cSet in violationResults:
                    # _right = violationResults[resList]
                    name = cSet.comparisonSetName

                    # create new column headings
                    newCols = [
                        ((name, f'{_colID}'), lambda row: _getValueByHeader(row, f'{_colID}'), f'{_colID}', None, None)
                        for _colID in (HeaderRestraint, HeaderAtoms, HeaderViolation,
                                       HeaderTarget, HeaderLowerLimit, HeaderUpperLimit,
                                       HeaderMin, HeaderMax, HeaderMean, HeaderStd,
                                       HeaderCount1, HeaderCount2)
                        ]

                else:
                    # create new column headings
                    newCols = [
                        ((name, f'{_colID}'), lambda row: _getValueByHeader(row, f'{_colID}'), f'{_colID}', None, None)
                        for _colID in (HeaderRestraint, HeaderAtoms)
                        ]

                _cols.extend(newCols)

        else:
            # only show the restraints
            for cSet in cSetLists:
                name = cSet.comparisonSetName

                # create new column headings
                newCols = [
                    ((name, f'{_colID}'), lambda row: _getValueByHeader(row, f'{_colID}'), f'{_colID}', None, None)
                    for _colID in (HeaderRestraint, HeaderAtoms)
                    ]

                _cols.extend(newCols)

        # return the table _columns
        return ColumnClass(_cols)

    def buildTableDataFrame(self):
        """Return a Pandas dataFrame from an internal list of objects.
        The columns are based on the 'func' functions in the columnDefinitions.
        :return pandas dataFrame
        """

        rss = self.resources
        # get the target peakLists
        # pks = (self._table and self._table.peaks) or []  # ._sourcePeaks
        # pks = self.project.peaks
        # resLists = self._restraintTables  # all restraint-tables to be displayed

        # column-headers
        cSetLists = [cSet for cSet in rss.comparisonSets if not cSet.isEmpty]
        extraDefaultHiddenColumns = []

        # need to remove the 'str' and use pd.MultiIndex.from_tuples(list[tuple, ...])

        # set the default column information
        self._columnDefs = [
            Column(INDEXCOL, lambda row: _getValueByHeader(row, HeaderIndex), tipText='TipTex1', format=int),
            Column(PEAKSERIALCOL, lambda row: _getValueByHeader(row, HeaderMatch), tipText='TipTex2'),
            Column(OBJCOL, lambda row: _getValueByHeader(row, HeaderObject), tipText='TipTex3'),
            ]

        if cSetLists:
            # make references for quicker access later
            allResLists = list(OrderedSet(rList
                                          for cSet in cSetLists
                                          for rList in cSet.getTreeTables(depth=1, selected=True)))
            contribs = {res: _getContributions(res) for rList in allResLists for res in rList.restraints}

            # make a dict of peak.restraints as this is reverse generated by the api every call to peak.restraints
            pkRestraints = {}
            pks = set()
            for resList in allResLists:
                for res in resList.restraints:
                    for pk in res.peaks:
                        pks.add(pk)
                        pkRestraints.setdefault(pk.pid, set()).add(res)

            pks = sorted(pks)
            resLists = {cSet: cSet.getTreeTables(depth=1, selected=True)
                        for cSet in cSetLists}
            # get the maximum number of restraintItems from each restraint list
            counts = [np.array([sum(len(contribs[res]) for res in (pkRestraints.get(pk.pid) or ()) if
                                    res and res.restraintTable in resLists[cSet]
                                    )
                                for pk in pks])
                      for cSet in cSetLists]
            maxCount = np.max(counts, axis=0)

            allPkSerials = pd.DataFrame([pk.pid for pk, count in zip(pks, maxCount) for _ in range(count)],
                                        columns=[PEAKSERIALCOL, ])
            index = pd.DataFrame(list(range(1, len(allPkSerials) + 1)),
                                 columns=[INDEXCOL, ])
            allPks = pd.DataFrame([(pk.pid, pk) for pk, count in zip(pks, maxCount) for _ in range(count)],
                                  columns=[PEAKSERIALCOL, OBJCOL])

            # make matching length tables for each of the restraintTables for each peak so the rows match up in the table
            #   must be a pandas way of doing this
            dfs = {}
            dfsAll = {}
            for lCount, cSet in enumerate(cSetLists):
                resLists = cSet.getTreeTables(depth=1, selected=True)
                if not resLists:
                    continue

                cSetName = cSet.comparisonSetName
                ll = [(None, None)] * sum(maxCount)
                head = 0
                for pk, cc, maxcc in zip(pks, counts[lCount], maxCount):
                    # ensure that the atoms are sorted so that they are matched correctly
                    _res = [(res.pid,
                             ' - '.join(sorted(_atom.split(' - '), key=universalSortKey)) if _atom else None,
                             res.targetValue,
                             res.lowerLimit,
                             res.upperLimit,
                             )
                            for res in (pkRestraints.get(pk.pid) or ()) if res.restraintTable in resLists
                            for _atom in contribs[res]]
                    if _res:
                        ll[head:head + len(_res)] = _res
                    head += maxcc

                COLS = [(cSetName, f'{HeaderRestraint}'),
                        (cSetName, 'Atoms'),
                        (cSetName, f'{HeaderTarget}'),
                        (cSetName, f'{HeaderLowerLimit}'),
                        (cSetName, f'{HeaderUpperLimit}'),
                        ]
                _ll = pd.DataFrame(ll)
                _ll.columns = COLS[:len(_ll.columns)]  # may not contain headerTarget, etc.

                # NOTE:ED - nasty hack to get the includeNonPeaks state :|
                if rss._includeNonPeaksCheckBox.isChecked():
                    # get the restraints without peaks?
                    nonPeaks = [(res.pid,
                                 ' - '.join(sorted(_atom.split(' - '), key=universalSortKey)) if _atom else None,
                                 res.targetValue,
                                 res.lowerLimit,
                                 res.upperLimit,
                                 )
                                for resList in resLists
                                for res in resList.restraints if not res.peaks
                                for _atom in contribs[res]]
                    if nonPeaks:
                        allPLen = len(index) + 1
                        index = pd.concat([index,
                                           pd.DataFrame(list(range(allPLen, allPLen + len(nonPeaks))),
                                                        columns=[INDEXCOL, ]
                                                        )],
                                          axis=0, ignore_index=True)
                        _np = pd.DataFrame(nonPeaks)
                        _np.columns = COLS[:len(_np.columns)]
                        _ll = pd.concat([_ll, _np], axis=0, ignore_index=True)

                # put the serial and atoms into another table to be concatenated to the right, lCount = index in resLists
                dd = pd.concat([allPkSerials, _ll], axis=1)
                dfsAll[cSetName] = dd.dropna(how='all', axis=1)
                # just keeping the pid/Atoms
                dfs[cSetName] = dd.drop(columns=COLS[2:], errors='ignore')  # ignore missing columns

            # # get the dataSets that contain data with a matching 'result' name - should be violations
            # violationResults = {resList: viols.data.copy() if viols is not None else None
            #                     for resList in allResLists
            #                     for viols in self._outputTables
            #                     if resList.pid == viols.getMetadata(_RESTRAINTTABLE) and viols.getMetadata(_VIOLATIONRESULT) is True
            #                     }
            #
            violationResults = {cSet.comparisonSetName: [viols.data.copy()
                                                         for viols in cSet.getTreeTables(depth=2, selected=True) if
                                                         viols is not None]
                                for cSet in cSetLists if cSet.getTreeTables(depth=1, selected=True)
                                }

            if sum(len(viols) for viols in violationResults.values()):
                # merge all the tables for each restraintTable
                _out = [index, allPks]
                zeroCols = []
                # rename the columns to match the order in visible list
                for ii, (cSetName, resViols) in enumerate(violationResults.items()):
                    for resViol in resViols:
                        # ind = allResLists.index(rl)

                        # change old columns to new columns
                        newCols = [_OLDHEADERS.get(cc, None) or cc for cc in resViol.columns]
                        # resViol.columns = [vv + f'_{ind + 1}' for vv in resViol.columns]
                        # resViol.columns = [vv + f'_{ind + 1}' for vv in newCols]
                        resViol.columns = [(cSetName, vv) for vv in newCols]

                for ii, cSet in enumerate(cSetLists):
                    cSetName = cSet.comparisonSetName
                    # if not cSet.getTreeTables(depth=1, selected=True):
                    #     continue
                    HEADERSCOL = (cSetName, HeaderRestraint)
                    ATOMSCOL = (cSetName, HeaderAtoms)
                    HEADERMEANCOL = (cSetName, HeaderMean)
                    HEADERVIOLATION = (cSetName, HeaderViolation)

                    if violationResults.get(cSetName):
                        extraDefaultHiddenColumns.append(HEADERVIOLATION)
                        _left = dfs[cSetName]
                        try:
                            _vResults = []
                            for vTable in violationResults[cSetName]:
                                # remove any duplicated violations - these add bad rows
                                _right = vTable.drop_duplicates([HEADERSCOL, ATOMSCOL])

                                if (HEADERSCOL in _left.columns and ATOMSCOL in _left.columns) and \
                                        (HEADERSCOL in _right.columns and ATOMSCOL in _right.columns):
                                    # _new = pd.merge(_left, _right, on=[HEADERSCOL, ATOMSCOL], how='left').drop(columns=[PEAKSERIALCOL]).fillna(0.0)

                                    # TODO: CHECK overlapping peak-lists?
                                    _vResults.append(pd.merge(_left, _right, on=[HEADERSCOL, ATOMSCOL], how='right'))

                                zeroCols.append(HEADERMEANCOL)

                            if _vResults:
                                _vMerge = pd.concat(_vResults, axis=0).drop_duplicates([HEADERSCOL, ATOMSCOL])
                                _vMerge.insert(3, HEADERVIOLATION, True)
                                _new = pd.merge(_left, _vMerge, how='left').drop(columns=[PEAKSERIALCOL])
                                # fill the blank spaces with the correct types
                                _new = _new.fillna({HEADERSCOL: '-', ATOMSCOL: '-', HEADERVIOLATION: False})
                                _new = _new.fillna(0.0)

                                _out.append(_new)

                                self._addColumnDefs(_new, cSetName, ii)

                        #~~~~~~~~~~~~~~~~~~~~~~~~~~

                        # try:
                        #     # remove any duplicated violations - these add bad rows
                        #     _right = violationResults[cSet].drop_duplicates([HEADERSCOL, ATOMSCOL])
                        #
                        #     # NOTE:ED - hmm, seems to be restraint_id, atom_name_1, etc.
                        #
                        # except Exception:
                        #     continue

                        # if (HEADERSCOL in _left.columns and ATOMSCOL in _left.columns) and \
                        #         (HEADERSCOL in _right.columns and ATOMSCOL in _right.columns):
                        #     _new = pd.merge(_left, _right, on=[HEADERSCOL, ATOMSCOL], how='left').drop(columns=[PEAKSERIALCOL]).fillna(0.0)
                        #     _out.append(_new)
                        #
                        #     zeroCols.append(HEADERMEANCOL)

                        except Exception:
                            continue

                        # _right = violationResults[resList].drop_duplicates([f'{HeaderRestraint}_{ii + 1}', f'Atoms_{ii + 1}'])
                        # if (f'{HeaderRestraint}_{ii + 1}' in _left.columns and f'Atoms_{ii + 1}' in _left.columns) and \
                        #         (f'{HeaderRestraint}_{ii + 1}' in _right.columns and f'Atoms_{ii + 1}' in _right.columns):
                        #     _new = pd.merge(_left, _right, on=[f'{HeaderRestraint}_{ii + 1}', f'Atoms_{ii + 1}'], how='left').drop(columns=[PEAKSERIALCOL]).fillna(0.0)
                        #     _out.append(_new)
                        #
                        #     zeroCols.append(f'{HeaderMean}_{ii + 1}')
                        #
                        # for _colID in (HeaderRestraint, HeaderAtoms,
                        #                HeaderTarget, HeaderLowerLimit, HeaderUpperLimit,
                        #                HeaderMin, HeaderMax, HeaderMean, HeaderStd,
                        #                HeaderCount1, HeaderCount2):
                        #     if (name, _colID) in list(_new.columns):
                        #         # check whether all the columns exist - discard otherwise
                        #         # columns should have been renamed and post-fixed with _<num>. above
                        #         _cols.append(((name, _colID), lambda row: _getValueByHeader(row, f'{_colID}_{ii + 1}'), f'{_colID}_Tip{ii + 1}', None, None))

                    elif cSetName in dfsAll:
                        # lose the PeakSerial column for each
                        _new = dfsAll[cSetName].drop(columns=[PEAKSERIALCOL], errors='ignore')
                        # fill the blank spaces with the correct types
                        _new = _new.fillna({HEADERSCOL: '-', ATOMSCOL: '-', HEADERVIOLATION: False})
                        _new = _new.fillna(0.0)

                        _out.append(_new)

                        # # create new column headings
                        # for _colID in (HeaderRestraint, HeaderAtoms):
                        #     _cols.append((f'{_colID}_{ii + 1}', lambda row: _getValueByHeader(row, f'{_colID}_{ii + 1}'), f'{_colID}_Tip{ii + 1}', None, None))

                        self._addColumnDefs(_new, cSetName, ii)

                # concatenate the final dataFrame
                # _table = pd.concat([index, allPks, *_out.values()], axis=1)
                _table = pd.concat(_out, axis=1)
                # # purge all rows that contain all means == 0, the fastest method
                # _table = _table[np.count_nonzero(_table[zeroCols].values, axis=1) > 0]
                # process all row that have means > 0.3, keep only rows that contain at least one valid mean
                if zeroCols and rss._meanLowerLimit:
                    _table = _table[(_table[zeroCols] >= rss._meanLowerLimit).sum(axis=1) > 0]

            else:
                # only show the restraints

                _out = [index, allPks]
                # no results - just show the table
                for ii, cSet in enumerate(cSetLists):
                    cSetName = cSet.comparisonSetName
                    if (not cSet.getTreeTables(depth=1, selected=True) or cSetName not in dfsAll):
                        continue

                    HEADERSCOL = (cSetName, HeaderRestraint)
                    ATOMSCOL = (cSetName, HeaderAtoms)
                    HEADERVIOLATION = (cSetName, HeaderViolation)
                    # lose the PeakSerial column for each
                    _new = dfsAll[cSetName].drop(columns=[PEAKSERIALCOL], errors='ignore')
                    # fill the blank spaces with the correct types
                    _new = _new.fillna({HEADERSCOL: '-', ATOMSCOL: '-', HEADERVIOLATION: False})
                    _new = _new.fillna(0.0)
                    _out.append(_new)
                    self._addColumnDefs(_new, cSetName, ii)

                # concatenate to give the final table
                _table = pd.concat(_out, axis=1)
        else:
            # # get the target peakLists
            # pks = (self._table and self._table.peaks) or []  # ._sourcePeaks
            #
            # # make a table that only has peaks
            # index = pd.DataFrame(list(range(1, len(pks) + 1)), columns=[INDEXCOL])
            # allPks = pd.DataFrame([(pk.pid, pk) for pk in pks], columns=[PEAKSERIALCOL, OBJCOL])
            #
            # _table = pd.concat([index, allPks], axis=1)

            _table = pd.DataFrame({}, columns=[INDEXCOL, PEAKSERIALCOL, OBJCOL])

        _table.columns = pd.MultiIndex.from_tuples(_table.columns)
        if rss._includeNonPeaksCheckBox.isChecked():
            _table = (_table
                      .fillna({PEAKSERIALCOL: '-'})
                      .loc[~_table.loc[:, (slice(None), HeaderRestraint)].isna().all(axis=1)]
                      .fillna('-')
                      )
        _objects = list(_table.itertuples())
        self._objects = _objects
        if extraDefaultHiddenColumns:
            hCols = self.headerColumnMenu._internalColumns
            self.headerColumnMenu.setInternalColumns(set(hCols) | set(extraDefaultHiddenColumns))

        return _table

    def _addColumnDefs(self, _new, cSetName, ii):
        """Add column-definitions for the new restraints.
        """
        for _colID, fmt in self._subgroupColumns:
            if (cSetName, _colID) in list(_new.columns):
                # check whether all the columns exist - discard otherwise
                # columns should have been renamed and post-fixed with _<num>. above
                self._columnDefs.append(Column((cSetName, _colID),
                                               # lambda row: _getValueByHeader(row, f'{_colID}_{ii + 1}'),
                                               None,
                                               tipText=f'{_colID}_Tip{ii + 1}',
                                               format=fmt
                                               ))

    #=========================================================================================
    # Updates
    #=========================================================================================

    def postUpdateDf(self):
        # update the visible columns
        self.headerColumnMenu.saveColumns([col for col in self._df.columns
                                           if isinstance(col, tuple) and col[1] in self.defaultHiddenSubgroup])
        self.headerColumnMenu.refreshHiddenColumns()
        self.searchMenu.refreshFilter()

    # NOTE:ED - not done yet
    # def refreshTable(self):
    #     # subclass to refresh the groups
    #     self.setTableFromDataFrameObject(self._dataFrameObject)
    #     self.updateTableExpanders()
    #
    # def setDataFromSearchWidget(self, dataFrame):
    #     """Set the data for the table from the search widget
    #     """
    #     self.setData(dataFrame.values)
    #     self._updateGroups(dataFrame)
    #     self.updateTableExpanders()

    @staticmethod
    def _getSortedContributions(restraint):
        """
        CCPN-INTERNAL: Return number of peaks assigned to NmrAtom in Experiments and PeakLists
        using ChemicalShiftList
        """
        return [sorted(ri) for rc in restraint.restraintContributions for ri in rc.restraintItems if ri]

    def _update(self):
        """Display the objects on the table for the selected list.
        """
        # if self._table:
        #     # NOTE:ED - check whether to use _table or resources
        #     # self.resources._sourcePeaks = self._table
        #     self.populateTable()
        # else:
        #     self.populateEmptyTable()

        # ignore _modulePulldown
        self.populateTable()

    def _updateTable(self, useSelectedPeakList=True, peaks=None, peakList=None):
        """Display the restraints on the table for the selected PeakList.
        Obviously, If the restraint has not been previously deleted
        """
        rss = self.resources

        # rss._sourcePeaks = self.project.getByPid(rss._modulePulldown.getText())
        self._groups = None
        self.hide()

        # get the correct restraintTables/violationTables from the settings
        rTables = rss._resTableWidget.getTexts()
        if ALL in rTables:
            rTables = self.project.restraintTables
        else:
            rTables = [self.project.getByPid(rList) for rList in rTables]
            rTables = [rList for rList in rTables if rList is not None and isinstance(rList, RestraintTable)]

        vTables = rss._outTableWidget.getTexts()
        if ALL in vTables:
            vTables = [vt for vt in self.project.violationTables if vt.getMetadata(_VIOLATIONRESULT)]
        else:
            vTables = [self.project.getByPid(rList) for rList in vTables]
            vTables = list(filter(None, vTables))
        rss.guiModule._updateCollectionButton(True)

        rss._restraintTables = rTables
        rss._outputTables = vTables

        if useSelectedPeakList:
            if self._table:  # rss._sourcePeaks:
                self.populateTable(rowObjects=self._table.peaks,
                                   selectedObjects=self.current.peaks
                                   )
            else:
                self.populateEmptyTable()

        else:
            if peaks:
                if peakList:
                    self.populateTable(rowObjects=peaks,
                                       selectedObjects=self.current.peaks
                                       )
            else:
                self.populateEmptyTable()

        self.updateTableExpanders()
        self.show()

    #=========================================================================================
    # Widgets callbacks
    #=========================================================================================

    ...

    #=========================================================================================
    # Signal responses
    #=========================================================================================

    def _postChangeSelectionOrderCallback(self, *args):
        super()._postChangeSelectionOrderCallback(*args)

        self.updateTableExpanders()

    #=========================================================================================
    # object properties
    #=========================================================================================

    def updateTableExpanders(self, expandState=None):
        """Update the state of the expander buttons
        """
        if not isinstance(expandState, (bool, type(None))):
            raise TypeError('expandState must be bool or None')

        if self.MERGECOLUMN >= self.columnCount():
            return

        rows = self.rowCount()
        _order = [self.model().index(ii, self.MERGECOLUMN).data() for ii in range(rows)]
        if not _order:
            return

        self.clearSpans()

        row = rowCount = 0
        lastRow = _order[row]
        _expand = self.resources._autoExpand if expandState is None else expandState

        for i in range(rows):

            nextRow = _order[i + 1] if i < (rows - 1) else None  # catch the last group, otherwise need try/except
            if lastRow == nextRow:
                rowCount += 1

            elif rowCount > 0:

                for col in self.SPANCOLUMNS:
                    self.setSpan(row, col, rowCount + 1, 1)
                self.setRowHidden(row, False)
                for rr in range(row + 1, row + rowCount):
                    self.setRowHidden(rr, not _expand)
                self.setRowHidden(row + rowCount, not _expand)

                rowCount = 0
                row = i + 1

            else:
                self.setRowHidden(i, False)
                row = i + 1

            lastRow = nextRow

        self.resizeRowsToContents()


#=========================================================================================
# Core Table for peak-list driven restraints
#=========================================================================================

class RestraintFrame(_CoreTableFrameABC):
    """Frame containing the pulldown and the table widget
    """
    # signal emitted when the manually changing the pulldown
    aboutToUpdate = QtCore.pyqtSignal(str)

    _TableKlass = _NewRestraintTableWidget
    _PulldownKlass = PeakListPulldown

    def __init__(self, parent, mainWindow=None, moduleParent=None, resources=None,
                 peakList=None, selectFirstItem=False, **kwds):
        super().__init__(parent, mainWindow=mainWindow, moduleParent=moduleParent,
                         obj=peakList, selectFirstItem=False, showGrid=True,
                         **kwds)

        # create widgets for expand/collapse, etc.
        self.refreshButton = Button(self, text=' Refresh',
                                    tipText='Refresh the table from the selected comparison sets',
                                    icon=Icon('icons/redo'),
                                    enabled=False,
                                    callback=self._refreshAll)

        self.expandButtons = ButtonList(parent=self, texts=[' Expand all', ' Collapse all'],
                                        callbacks=[partial(self._expandAll, True), partial(self._expandAll, False), ])

        vLine = VLine(self, colour=getColours()[DIVIDER], width=16)

        self.pdbSelect = PulldownList(self, tipText='Select PDB Source',
                                      # clickToShowCallback=self._selectPDBAboutToShow,
                                      callback=self._selectPDBSource)
        self.pdbSelect.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

        self.showOnViewerButton = Button(self, tipText='Show on Molecular Viewer',
                                         icon=Icon('icons/showStructure'),
                                         callback=self._showOnMolecularViewer,
                                         hAlign='l')

        # move to the correct positions
        self.addWidgetToTop(self.refreshButton, 2)
        self.addWidgetToTop(self.expandButtons, 3)
        self.addWidgetToTop(vLine, 4)
        self.addWidgetToTop(self.pdbSelect, 5)
        self.addWidgetToTop(self.showOnViewerButton, 6)

        self._modulePulldown.setDisabled(True)
        self._modulePulldown.setVisible(False)

        # NOTE:ED - bit of a hack for the minute
        self.resources = resources
        self._tableWidget.resources = resources

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _tableCurrent(self):
        """Return the list of source objects, e.g., _table.peaks/_table.nmrResidues
        """
        # should be redundant now
        return self.current.peakList

    @_tableCurrent.setter
    def _tableCurrent(self, value):
        self.current.peakList = value

    #=========================================================================================
    # Widgets callbacks
    #=========================================================================================

    def _expandAll(self, expand):
        """Expand/collapse all groups
        """
        self._tableWidget.updateTableExpanders(expand)

    def _showOnMolecularViewer(self):
        """Show the structure in the viewer
        """
        selected = self.pdbSelect.getObject()
        selectedPeaks = self._tableWidget.getSelectedObjects() or []

        # get the restraints to display
        restraints = flattenLists([pk.restraints for pk in selectedPeaks])

        if isinstance(selected, StructureData):
            if (pdbPath := selected.moleculeFilePath):
                getLogger().info(f'Using pdb file {pdbPath} for displaying violation on Molecular viewer.')

                # run Pymol
                pymolSPath = joinPath(self.moduleParent.pymolScriptsPath, PymolScriptName)

                pymolScriptPath = pyMolUtil._restraintsSelection2PyMolFile(pymolSPath, pdbPath, restraints)
                pyMolUtil.runPymolWithScript(self.application, pymolScriptPath)

            else:
                MessageDialog.showWarning('No Molecule File found',
                                          f'PDB filepath not set for {selected.pid}\n'
                                          'To add a molecule file path: Find the StructureData on sideBar,'
                                          'open the properties popup, add a full PDB filepath in the entry widget.')
                return

        elif isinstance(selected, StructureEnsemble):
            MessageDialog.showNotImplementedMessage()

    def _selectionPulldownCallback(self, item):
        """Notifier Callback for selecting object from the pull down menu
        """
        if self._modulePulldown.underMouse():
            # tell the parent to clear its lists
            self.aboutToUpdate.emit(self._modulePulldown.getText())

        super(RestraintFrame, self)._selectionPulldownCallback(item)

    def _refreshAll(self):
        """Refresh the contents of the table
        """
        self._tableWidget._update()
        self.refreshButton.setEnabled(False)

    def _selectPDBSource(self, *args, **kwds):
        """Select PDB source from the pulldown
        """
        ...

    def _updatePulldown(self, data=None):
        """Update the pulldown after receiving notifier
        """
        combo = self.pdbSelect

        # add the comparison sets from the settings
        cSets = [cSet.comparisonSet for cSet in self.resources.comparisonSets
                 if isinstance(cSet.comparisonSet, StructureData)]

        objects = [None] + cSets + [None]
        texts = [SELECT] + [cSet.comparisonSet.pid for cSet in self.resources.comparisonSets
                            if isinstance(cSet.comparisonSet, StructureData)] + [PULLDOWNSEPARATOR]

        # # add the structureEnsembles
        # objects.extend(self.project.structureEnsembles)
        # texts.extend(se.pid for se in self.project.structureEnsembles)

        current = combo.getText()
        with self.blockWidgetSignals():
            # populate
            combo.clear()
            combo.setData(texts=texts, objects=objects)
            combo.select(current)

        combo.disableLabelsOnPullDown([PULLDOWNSEPARATOR])
        combo.update()

    #=========================================================================================
    # Other
    #=========================================================================================

    def setRefreshButtonEnabled(self, value):
        """Enable/disable the refresh-button
        """
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}.setRefreshButtonEnabled: value if not True/False')

        self.refreshButton.setEnabled(value)
