"""This file contains ChemicalShiftTable class

modified by Geerten 1-7/12/2016
tertiary version by Ejb 9/5/17
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
__dateModified__ = "$dateModified: 2025-01-10 17:57:38 +0000 (Fri, January 10, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets, QtCore
from functools import partial, reduce
from types import SimpleNamespace
from operator import or_
import pandas as pd

from ccpn.core.ChemicalShift import ChemicalShift
from ccpn.core.ChemicalShiftList import ChemicalShiftList
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking
from ccpn.core.ChemicalShiftList import (CS_UNIQUEID, CS_ISDELETED, CS_PID, CS_STATIC, CS_STATE, CS_ORPHAN, CS_VALUE,
                                         CS_VALUEERROR, CS_FIGUREOFMERIT, CS_ATOMNAME, CS_NMRATOM, CS_CHAINCODE,
                                         CS_SEQUENCECODE, CS_RESIDUETYPE, CS_ALLPEAKS, CS_SHIFTLISTPEAKSCOUNT,
                                         CS_ALLPEAKSCOUNT, CS_COMMENT, CS_OBJECT, CS_TABLECOLUMNS, ChemicalShiftState)
from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.lib.DataFrameObject import DataFrameObject, DATAFRAME_OBJECT
from ccpn.core.lib.WeakRefLib import WeakRefDescriptor
from ccpn.ui.gui.modules.CcpnModule import CcpnTableModule
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget
from ccpn.ui.gui.widgets.PulldownListsForObjects import ChemicalShiftListPulldown
from ccpn.ui.gui.widgets.GuiTable import _getValueByHeader
from ccpn.ui.gui.widgets.Column import ColumnClass
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.MessageDialog import showYesNo, showWarning
from ccpn.ui.gui.widgets.SettingsWidgets import ALL
from ccpn.ui.gui.widgets.Column import COLUMN_COLDEFS, COLUMN_SETEDITVALUE, COLUMN_FORMAT
from ccpn.ui.gui.lib.StripLib import navigateToPositionInStrip, markNmrAtoms
from ccpn.ui.gui.widgets.table._ProjectTable import _ProjectTableABC
from ccpn.util.Logging import getLogger


logger = getLogger()
LINKTOPULLDOWNCLASS = 'linkToPulldownClass'

#=========================================================================================
# Chemical Shift Table Options
#=========================================================================================

_NAVIGATE_CST = 'Navigate to:'
_MERGE_CST = 'Merge NmrAtoms'
_EDIT_CST = 'Edit NmrAtom'
_REMOVE_CST = 'Remove assignments'
_REMOVEDEL_CST = 'Remove assignments and Delete'
_INTO_CSL = 'into'


#=========================================================================================
# ChemicalShiftTableModule
#=========================================================================================

class ChemicalShiftTableModule(CcpnTableModule):
    """This class implements the module by wrapping a ChemicalShift instance.
    """
    className = 'ChemicalShiftTableModule'
    includeSettingsWidget = True
    maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    settingsPosition = 'left'
    _allowRename = True
    activePulldownClass = None  # e.g., can make the table respond to current peakList

    def __init__(self, mainWindow=None, name='Chemical Shift Table',
                 chemicalShiftList=None, selectFirstItem=False):
        """Initialise the Module widgets.
        """
        super().__init__(mainWindow=mainWindow, name=name)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        self._table = None

        # add the widgets
        self._setWidgets()

        if chemicalShiftList is not None:
            self.selectTable(chemicalShiftList)
        elif selectFirstItem:
            self._modulePulldown.selectFirstItem()

    def _setWidgets(self):
        """Set up the widgets for the module.
        """
        # Put all the NmrTable settings in a widget, as there will be more added in the PickAndAssign, and
        # backBoneAssignment modules
        if self.includeSettingsWidget:
            self._settings = Widget(self.settingsWidget, setLayout=True,
                                    grid=(0, 0), vAlign='top', hAlign='left')

            # cannot set a notifier for displays, as these are not (yet?) implemented and the Notifier routines
            # underpinning the addNotifier call do not allow for it either
            colwidth = 140

            self.autoClearMarksWidget = CheckBoxCompoundWidget(
                    self._settings,
                    grid=(3, 0), vAlign='top', stretch=(0, 0), hAlign='left',
                    fixedWidths=(colwidth, 30),
                    orientation='left',
                    labelText='Auto clear marks:',
                    checked=True
                    )

        _topWidget = self.mainWidget

        # main widgets at the top
        row = 0
        Spacer(_topWidget, 5, 5,
               QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
               grid=(0, 0), gridSpan=(1, 1))
        row += 1

        self._modulePulldown = ChemicalShiftListPulldown(parent=_topWidget,
                                                         mainWindow=self.mainWindow, default=None,
                                                         grid=(row, 0), gridSpan=(1, 1), minimumWidths=(0, 100),
                                                         showSelectName=True,
                                                         sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                                         callback=self._selectionPulldownCallback,
                                                         )
        # fixed height
        self._modulePulldown.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)

        row += 1
        self.spacer = Spacer(_topWidget, 5, 5,
                             QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed,
                             grid=(2, 1), gridSpan=(1, 1))
        _topWidget.getLayout().setColumnStretch(1, 2)

        # main window
        _hidden = [CS_UNIQUEID, CS_ISDELETED, CS_FIGUREOFMERIT, CS_ALLPEAKS, CS_CHAINCODE,
                   CS_SEQUENCECODE, CS_STATE, CS_ORPHAN]

        row += 1
        self._tableWidget = _NewChemicalShiftTable(parent=_topWidget,
                                                   mainWindow=self.mainWindow,
                                                   moduleParent=self,
                                                   grid=(row, 0), gridSpan=(1, 6),
                                                   hiddenColumns=_hidden)

    @property
    def tableFrame(self):
        """Return the table frame
        """
        # a bit of a hack for this module as subclasses from CcpnTableModule
        getLogger().debug(f'{self.__class__.__name__}.tableFrame: '
                          f'a bit of a hack as subclasses from CcpnTableModule')
        return None

    def selectTable(self, table=None):
        """Manually select a table from the pull-down.
        """
        if table is None:
            self._modulePulldown.selectFirstItem()
        else:
            if not isinstance(table, self._tableWidget.tableClass):
                logger.warning(f'select: Object is not of type {self._tableWidget.tableName}')
                raise TypeError(f'select: Object is not of type {self._tableWidget.tableName}')
            else:
                self._modulePulldown.select(table.pid)

    def _selectionPulldownCallback(self, item):
        """Notifier Callback for selecting table from the pull-down menu.
        """
        self._table = self._modulePulldown.getSelectedObject()
        self._tableWidget._table = self._table

        if self._table is not None:
            self._tableWidget.populateTable(selectedObjects=self.current.chemicalShifts)
        else:
            self._tableWidget.populateEmptyTable()


#=========================================================================================
# New ChemicalShiftTable
#=========================================================================================

# define a simple class that can contains a simple id
blankId = SimpleNamespace(className='notDefined', serial=0)

OBJECT_CLASS = 0
OBJECT_PARENT = 1
MODULEIDS = {}
_TABLES = 'tables'
_HIDDENCOLUMNS = 'hiddenColumns'
# column-header mappings from dataFrame to visible-table
_COLUMNHEADERS = {CS_UNIQUEID           : 'ID',
                  CS_ISDELETED          : 'isDeleted',  # should never be visible
                  CS_PID                : 'ChemicalShift',
                  CS_VALUE              : 'Value\n(ppm)',
                  CS_VALUEERROR         : 'Value Error\n(ppm)',
                  CS_FIGUREOFMERIT      : 'Figure of Merit',
                  CS_NMRATOM            : 'NmrAtom',
                  CS_CHAINCODE          : 'ChainCode',
                  CS_SEQUENCECODE       : 'SequenceCode',
                  CS_RESIDUETYPE        : 'ResidueType',
                  CS_ATOMNAME           : 'AtomName',
                  CS_STATE              : 'State',
                  CS_ORPHAN             : 'Orphaned',
                  CS_ALLPEAKS           : 'Assigned\nPeaks',
                  CS_SHIFTLISTPEAKSCOUNT: 'Peak Count',
                  CS_ALLPEAKSCOUNT      : 'Total\nPeak Count',
                  CS_COMMENT            : 'Comment',
                  CS_OBJECT             : '_object'
                  }


class _NewChemicalShiftTable(_ProjectTableABC):
    """New chemicalShiftTable based on faster QTableView.
    Actually more like the original table but with pandas dataFrame.
    """
    className = 'ChemicalShiftTable'
    attributeName = 'chemicalShiftLists'

    OBJECTCOLUMN = CS_OBJECT  # column holding active objects (uniqueId/ChemicalShift for this table?)
    INDEXCOLUMN = CS_UNIQUEID  # column holding the index

    _defaultHidden_ = (CS_UNIQUEID, CS_ISDELETED, CS_PID, CS_FIGUREOFMERIT, CS_ALLPEAKS, CS_CHAINCODE,
                       CS_SEQUENCECODE, CS_STATE, CS_ORPHAN)
    _internalColumns_ = (CS_ISDELETED, CS_OBJECT)  # columns that are always hidden

    # define self._columns here
    # columnHeaders = {CS_UNIQUEID           : 'ID',
    #                  CS_ISDELETED          : 'isDeleted',  # should never be visible
    #                  CS_PID                : 'ChemicalShift',
    #                  CS_VALUE              : 'Value\n(ppm)',
    #                  CS_VALUEERROR         : 'Value Error\n(ppm)',
    #                  CS_FIGUREOFMERIT      : 'Figure of Merit',
    #                  CS_NMRATOM            : 'NmrAtom',
    #                  CS_CHAINCODE          : 'ChainCode',
    #                  CS_SEQUENCECODE       : 'SequenceCode',
    #                  CS_RESIDUETYPE        : 'ResidueType',
    #                  CS_ATOMNAME           : 'AtomName',
    #                  CS_STATE              : 'State',
    #                  CS_ORPHAN             : 'Orphaned',
    #                  CS_ALLPEAKS           : 'Assigned\nPeaks',
    #                  CS_SHIFTLISTPEAKSCOUNT: 'Peak Count',
    #                  CS_ALLPEAKSCOUNT      : 'Total\nPeak Count',
    #                  CS_COMMENT            : 'Comment',
    #                  CS_OBJECT             : '_object'
    #                  }
    defaultHidden = [_COLUMNHEADERS[col] for col in _defaultHidden_]
    _internalColumns = [_COLUMNHEADERS[col] for col in _internalColumns_]

    tipTexts = ('Unique identifier for the chemicalShift',
                'isDeleted',  # should never be visible
                'ChemicalShift.pid',
                'ChemicalShift value in ppm',
                'Error in the chemicalShift value in ppm',
                'Figure of merit, between 0 and 1',
                'Pid of nmrAtom if attached, or None',
                'ChainCode of attached nmrAtom, or None',
                'SequenceCode of attached nmrAtom, or None',
                'ResidueType of attached nmrAtom, or None',
                'AtomName of attached nmrAtom, or None',
                'Active state of chemicalShift:\nstatic - not linked to any spectra,\ndynamic - linked to at least one spectrum through a peak-assignment',
                'Orphaned state of chemicalShift.\nA Dynamic chemical-shift is orphaned if its nmrAtom is not\nused for any peak assignments in the linked spectra',
                'List of assigned peaks associated with this chemicalShift',
                'Number of assigned peaks attached to a chemicalShift\nbelonging to spectra associated with parent chemicalShiftList',
                'Total number of assigned peaks attached to a chemicalShift\nbelonging to any spectra',
                'Optional comment for each chemicalShift',
                'None',
                )

    # define the notifiers that are required for the specific table-type
    tableClass = ChemicalShiftList
    rowClass = ChemicalShift
    cellClass = None
    tableName = tableClass.className
    rowName = rowClass.className
    cellClassNames = None

    selectCurrent = True
    callBackClass = ChemicalShift
    search = False

    _enableSearch = True
    _enableDelete = True
    _enableExport = True
    _enableCopyCell = True
    _table = WeakRefDescriptor()

    # set the queue handling parameters
    _maximumQueueLength = 25

    def __init__(self, parent=None, mainWindow=None, moduleParent=None, **kwds):
        """Initialise the widgets for the module.
        """
        for key in ('multiSelect', 'showVerticalHeader', 'setLayout'):
            kwds.pop(key, None)
        # create the table; objects are added later via the displayTableForNmrChain method
        super().__init__(parent=parent,
                         mainWindow=mainWindow,
                         moduleParent=moduleParent,
                         multiSelect=True,
                         showVerticalHeader=False,
                         setLayout=True,
                         **kwds
                         )

    #-----------------------------------------------------------------------------------------
    # Widget callbacks
    #-----------------------------------------------------------------------------------------

    @staticmethod
    def _getValidChemicalShift4Callback(objs):
        if not objs or not all(objs):
            return
        if isinstance(objs, (tuple, list)):
            cShift = objs[-1]
        else:
            cShift = objs
        if not cShift:
            showWarning('Cannot perform action', 'No selected ChemicalShift')
            return

        return cShift

    def actionCallback(self, selection, lastItem):
        """Notifier DoubleClick action on item in table. Mark a chemicalShift based on attached nmrAtom.
        """

        try:
            if not (objs := list(lastItem[self._OBJECT])):
                return
        except Exception as es:
            getLogger().debug2(f'{self.__class__.__name__}.actionCallback: No selection\n{es}')
            return

        cShift = self._getValidChemicalShift4Callback(objs)
        if len(self.mainWindow.marks):
            if self.moduleParent.autoClearMarksWidget.checkBox.isChecked():
                self.mainWindow.clearMarks()
        if cShift and cShift.nmrAtom:
            markNmrAtoms(self.mainWindow, [cShift.nmrAtom])

    def selectionCallback(self, selected, deselected, selection, lastItem):
        """Notifier Callback for selecting rows in the table.
        """
        try:
            if not (objs := list(selection[self._OBJECT])):
                return
        except Exception as es:
            getLogger().debug2(f'{self.__class__.__name__}.selectionCallback: No selection\n{es}')
            return

        self.current.chemicalShifts = objs or []

        if objs:
            nmrResidues = tuple(set(cs.nmrAtom.nmrResidue for cs in objs if cs.nmrAtom))
        else:
            nmrResidues = []

        if nmrResidues:
            # set the associated nmrResidue and nmrAtoms
            nmrAtoms = tuple(set(nmrAtom for nmrRes in nmrResidues for nmrAtom in nmrRes.nmrAtoms))
            self.current.nmrAtoms = nmrAtoms
            self.current.nmrResidues = nmrResidues

        else:
            self.current.nmrAtoms = []
            self.current.nmrResidues = []

    #-----------------------------------------------------------------------------------------
    # Create table and row methods
    #-----------------------------------------------------------------------------------------

    def _newRowFromUniqueId(self, cslDf, obj, uniqueId):
        """Create a new row to insert into the dataFrame or replace row.
        """
        _row = cslDf.loc[uniqueId]
        # make the new row
        newRow = _row[:CS_ISDELETED].copy()
        _midRow = _row[CS_VALUE:CS_ATOMNAME]  # CS_STATIC
        _comment = _row[CS_COMMENT:]
        _pidCol = pd.Series(obj.pid, index=[CS_PID, ])
        _extraCols = pd.Series(self._derivedFromObject(obj),
                               index=[CS_STATE, CS_ORPHAN, CS_ALLPEAKS, CS_SHIFTLISTPEAKSCOUNT,
                                      CS_ALLPEAKSCOUNT])  # if state required

        # newRow = newRow.append([_pidCol, _midRow, _extraCols, _comment])  # deprecated
        newRow = pd.concat([newRow, _pidCol, _midRow, _extraCols, _comment])

        # append the actual object to the end - not sure whether this is required - check _highlightObjs
        newRow[CS_OBJECT] = obj

        # replace the visible nans with '' for comment column and string 'None' elsewhere
        newRow[CS_COMMENT:CS_COMMENT].fillna('', inplace=True)
        newRow.fillna('None', inplace=True)

        return list(newRow)

    @staticmethod
    def _derivedFromObject(obj):
        """Get a tuple of derived values from obj.
        Not very generic yet - column class now seems redundant.
        """
        _allPeaks = obj.allAssignedPeaks
        totalPeakCount = len(_allPeaks)
        peaks = [pp.pid for pp in _allPeaks if pp.spectrum.chemicalShiftList == obj.chemicalShiftList]
        peakCount = len(peaks)

        state = obj.state
        if state == ChemicalShiftState.ORPHAN:
            state = ChemicalShiftState.DYNAMIC
        state = state.description  # if state needed
        orphan = u'\u2713' if obj.orphan else ''  # unicode tick character

        return (state, orphan, str(peaks), peakCount, totalPeakCount)

    @staticmethod
    def _setComment(obj, value):
        """CCPN-INTERNAL: Insert a comment into object
        """
        obj.comment = value or None

    def buildTableDataFrame(self):
        """Return a Pandas dataFrame from an internal list of objects.
        The columns are based on the 'func' functions in the columnDefinitions.
        :return pandas dataFrame
        """
        # create the column objects
        _cols = [
            (_COLUMNHEADERS[col], lambda row: _getValueByHeader(row, col), self.tipTexts[ii], None, None)
            for ii, col in enumerate(CS_TABLECOLUMNS)
            ]

        # NOTE:ED - hack to add the comment editor to the comment column, decimal places to value/valueError/figureOfMerit
        _temp = list(_cols[CS_TABLECOLUMNS.index(CS_COMMENT)])
        _temp[COLUMN_COLDEFS.index(COLUMN_SETEDITVALUE)] = lambda obj, value: self._setComment(obj, value)
        _cols[CS_TABLECOLUMNS.index(CS_COMMENT)] = tuple(_temp)
        for col in [CS_VALUE, CS_VALUEERROR, CS_FIGUREOFMERIT]:
            _temp = list(_cols[CS_TABLECOLUMNS.index(col)])
            _temp[COLUMN_COLDEFS.index(COLUMN_FORMAT)] = '%0.3f'
            _cols[CS_TABLECOLUMNS.index(col)] = tuple(_temp)

        # set the table _columns
        self._columns = self._columnDefs = ColumnClass(_cols)  # Other tables are using _columnDefs :|

        _csl = self._table
        if _csl and _csl._data is not None:
            # is of type ChemicalShiftList->_ChemicalShiftListFrame - should move functionality to there
            df = _csl._data.copy()
            df = df[df[CS_ISDELETED] == False]
            df.drop(columns=[CS_STATIC], inplace=True)  # static not required

            df.set_index(df[CS_UNIQUEID], inplace=True, )  # drop=False)

            df.insert(CS_TABLECOLUMNS.index(CS_PID), CS_PID, None)
            df.insert(CS_TABLECOLUMNS.index(CS_STATE), CS_STATE, None)  # if state require
            df.insert(CS_TABLECOLUMNS.index(CS_ORPHAN), CS_ORPHAN, None)  # if state require
            df.insert(CS_TABLECOLUMNS.index(CS_ALLPEAKS), CS_ALLPEAKS, None)
            df.insert(CS_TABLECOLUMNS.index(CS_SHIFTLISTPEAKSCOUNT), CS_SHIFTLISTPEAKSCOUNT, None)
            df.insert(CS_TABLECOLUMNS.index(CS_ALLPEAKSCOUNT), CS_ALLPEAKSCOUNT, None)

            _objs = _csl._shifts
            if _objs:
                # append the actual objects as the last column - not sure whether this is required - check _highlightObjs
                df[CS_OBJECT] = _objs
                df[CS_PID] = [_shift.pid for _shift in _objs]

                _stats = [self._derivedFromObject(obj) for obj in _objs]
                df[[CS_STATE, CS_ORPHAN, CS_ALLPEAKS, CS_SHIFTLISTPEAKSCOUNT, CS_ALLPEAKSCOUNT]] = _stats

                # replace the visible nans with '' for comment column and string 'None' elsewhere
                df[CS_COMMENT].fillna('', inplace=True)
                df.fillna('None', inplace=True)
            else:
                df[CS_OBJECT] = []

        else:
            df = pd.DataFrame(columns=[_COLUMNHEADERS[val] for val in CS_TABLECOLUMNS])

        # update the columns to the visible headings
        df.columns = [_COLUMNHEADERS[val] for val in CS_TABLECOLUMNS]

        # set the table from the dataFrame
        _dfObject = DataFrameObject(dataFrame=df,
                                    columnDefs=self._columns or [],
                                    table=self,
                                    )

        return _dfObject

    def _updateTableCallback(self, data):
        """Respond to table notifier.
        """
        obj = data[Notifier.OBJECT]
        if obj != self._table:
            return

        # print(f'>>> _updateTableCallback  {self}')
        if self._table:
            # re-populate the table from the current pulldown
            self.populateTable(selectedObjects=self.current.chemicalShifts)
        else:
            self.populateEmptyTable()

    def _updateCellCallback(self, data):
        """Notifier callback for updating the table.
        :param data:
        """
        # print(f'>>> _updateCellCallback  {self}')
        pass

    def _updateRowCallback(self, data):
        """Notifier callback for updating the table for change in chemicalShifts.
        :param data: notifier content
        """
        # print(f'>>> _updateRowCallback  {self}')
        with self._blockTableSignals('_updateRowCallback'):
            obj = data[Notifier.OBJECT]
            uniqueId = obj.uniqueId

            # check that the dataframe and object are valid
            if self._df is None:
                getLogger().debug2(f'{self.__class__.__name__}._updateRowCallback: dataFrame is None')
                return
            if obj is None:
                getLogger().debug2(f'{self.__class__.__name__}._updateRowCallback: callback object is undefined')
                return

            # check that the object belongs to the list that is being displayed
            if obj.chemicalShiftList != self._table:
                return

            trigger = data[Notifier.TRIGGER]
            try:
                cslDf = self._table._data
                if cslDf is not None and not cslDf.empty:
                    cslDf = cslDf[cslDf[CS_ISDELETED] == False]  # not deleted - should be the only visible ones
                    objSet = set(cslDf[CS_UNIQUEID])
                else:
                    # current table is empty
                    objSet = set()
                if (visDf := self._df) is None or visDf.empty:
                    # the visible table may not have columns defined, if empty
                    tableSet = set()
                    _newVisDf = True
                else:
                    tableSet = set(visDf['ID'])  # must be table column name, not reference name
                    _newVisDf = False

                if trigger == Notifier.DELETE:
                    # uniqueIds in the visible table
                    if uniqueId in (tableSet - objSet):
                        # remove from the table
                        self.model()._deleteRow(uniqueId)

                elif trigger == Notifier.CREATE:
                    # uniqueIds in the visible table
                    if uniqueId in (objSet - tableSet):
                        if _newVisDf:
                            # create a new empty table, required to insert the first row
                            self.populateTable(setOnHeaderOnly=True)
                        # insert into the table
                        newRow = self._newRowFromUniqueId(cslDf, obj, uniqueId)
                        self.model()._insertRow(uniqueId, newRow)

                elif trigger == Notifier.CHANGE:
                    # uniqueIds in the visible table
                    if uniqueId in (objSet & tableSet):
                        # visible table dataframe update - object MUST be in the table
                        newRow = self._newRowFromUniqueId(cslDf, obj, uniqueId)
                        self.model()._updateRow(uniqueId, newRow)

                elif trigger == Notifier.RENAME:
                    # included for completeness, but shouldn't be required for chemical-shifts
                    if uniqueId in (objSet & tableSet):
                        # visible table dataframe update
                        newRow = self._newRowFromUniqueId(cslDf, obj, uniqueId)
                        self.model()._updateRow(uniqueId, newRow)

                    elif uniqueId in (objSet - tableSet):
                        # insert renamed object INTO the table
                        newRow = self._newRowFromUniqueId(cslDf, obj, uniqueId)
                        self.model()._insertRow(uniqueId, newRow)

                    elif uniqueId in (tableSet - objSet):
                        # remove renamed object OUT of the table
                        self.model()._deleteRow(uniqueId)

            except Exception as es:
                getLogger().debug2(f'Error updating row in table {es}')

    def _searchCallBack(self, data):
        # print(f'>>> _searchCallBack  {self}')
        pass

    def _selectCurrentCallBack(self, data):
        """Callback from a notifier to highlight the current objects.
        :param data:
        """
        if self._tableBlockingLevel:
            return

        objs = data['value']
        self._selectOnTableCurrent(objs)

    def _selectOnTableCurrent(self, objs):
        """Highlight the list of objects on the table.
        :param objs:
        """
        self.highlightObjects(objs)

    def queueFull(self):
        """Method that is called when the queue is deemed to be too big.
        Apply overall operation instead of all individual notifiers.
        """
        _selectedList = self.project.getByPid(self.moduleParent._modulePulldown.getText())

        if _selectedList:
            self.populateTable(selectedObjects=self.current.chemicalShifts)
        else:
            self.populateEmptyTable()

    #-----------------------------------------------------------------------------------------
    # Table context menu
    #-----------------------------------------------------------------------------------------

    def addTableMenuOptions(self, menu):
        """Add options to the right-mouse menu.
        """
        super().addTableMenuOptions(menu)

        self._mergeMenuAction = menu.addAction(_MERGE_CST, self._mergeNmrAtoms)
        self._editMenuAction = menu.addAction(_EDIT_CST, self._editNmrAtom)
        self._removeAssignmentsMenuAction = menu.addAction(_REMOVE_CST, partial(self._removeAssignments, delete=False))
        self._removeAssignmentsDeleteMenuAction = menu.addAction(_REMOVEDEL_CST,
                                                                 partial(self._removeAssignments, delete=True))

        if (_actions := menu.actions()):
            _topMenuItem = _actions[0]
            _topSeparator = menu.insertSeparator(_topMenuItem)

            # move new actions to the top of the list
            menu.insertAction(_topSeparator, self._removeAssignmentsDeleteMenuAction)
            menu.insertAction(self._removeAssignmentsDeleteMenuAction, self._removeAssignmentsMenuAction)
            menu.insertAction(self._removeAssignmentsMenuAction, self._mergeMenuAction)
            menu.insertAction(self._mergeMenuAction, self._editMenuAction)

        # add navigate option to the bottom
        menu.addSeparator()
        self._navigateMenu = menu.addMenu(_NAVIGATE_CST)

    def setTableMenuOptions(self, menu):
        """Update options in the right-mouse menu.
        """
        super().setTableMenuOptions(menu)

        selection = self.getSelectedObjects()
        data = self.getRightMouseItem()
        if (data is not None and not data.empty):
            cShift = data.get(DATAFRAME_OBJECT)
            currentNmrAtom = cShift.nmrAtom if cShift else None

            selection = [ch.nmrAtom for ch in selection or [] if ch.nmrAtom]
            _check = (currentNmrAtom and 1 < len(selection) and currentNmrAtom in selection) or False
            _option = f'{_INTO_CSL} {currentNmrAtom.id if currentNmrAtom else ""}' if _check else ''
            self._mergeMenuAction.setText(f'{_MERGE_CST} {_option}')
            self._mergeMenuAction.setEnabled(_check)

            current = True if (currentNmrAtom and selection) else False
            self._editMenuAction.setText(f'{_EDIT_CST} {currentNmrAtom.id if current else ""}')
            self._editMenuAction.setEnabled(True if current else False)
            self._addNavigationStripsToContextMenu()

            self._removeAssignmentsMenuAction.setEnabled(True if selection else False)
            self._removeAssignmentsDeleteMenuAction.setEnabled(True if selection else False)

        else:
            # disabled but visible lets user know that menu items exist
            self._mergeMenuAction.setText(_MERGE_CST)
            self._mergeMenuAction.setEnabled(False)
            self._editMenuAction.setText(_EDIT_CST)
            self._editMenuAction.setEnabled(False)
            self._removeAssignmentsMenuAction.setEnabled(False)
            self._removeAssignmentsDeleteMenuAction.setEnabled(False)

    #-----------------------------------------------------------------------------------------
    # Properties
    #-----------------------------------------------------------------------------------------

    pass

    #-----------------------------------------------------------------------------------------
    # Class methods
    #-----------------------------------------------------------------------------------------

    pass

    #-----------------------------------------------------------------------------------------
    # Table Implementation
    #-----------------------------------------------------------------------------------------

    def _mergeNmrAtoms(self):
        """Merge the nmrAtoms in the selection into the nmrAtom that has been right-clicked.
        """
        selection = self.getSelectedObjects()
        data = self.getRightMouseItem()
        if (data is not None and not data.empty) and selection:
            cShift = data.get(DATAFRAME_OBJECT)
            currentNmrAtom = cShift.nmrAtom if cShift else None

            matching = [ch.nmrAtom for ch in selection if ch and ch.nmrAtom and ch.nmrAtom != currentNmrAtom and
                        ch.nmrAtom.isotopeCode == currentNmrAtom.isotopeCode]
            nonMatching = [ch.nmrAtom for ch in selection if ch and ch.nmrAtom and ch.nmrAtom != currentNmrAtom and
                           ch.nmrAtom.isotopeCode != currentNmrAtom.isotopeCode]

            if len(matching) < 1:
                showWarning('Merge NmrAtoms', 'No matching isotope codes')
            else:
                ss = 's' if (len(nonMatching) > 1) else ''
                nonMatchingList = (f'\n\n\n({len(nonMatching)} nmrAtom{ss} with non-matching isotopeCode{ss})'
                                   if nonMatching else '')
                yesNo = showYesNo('Merge NmrAtoms',
                                  'Do you want to merge\n'
                                  '{}  into  {}{}'.format('\n'.join([ss.id for ss in matching]),
                                                          currentNmrAtom.id,
                                                          nonMatchingList),
                                  dontShowEnabled=True,
                                  defaultResponse=True,
                                  popupId=f'{self.__class__.__name__}Merge')
                if yesNo:
                    currentNmrAtom.mergeNmrAtoms(matching)

    def _editNmrAtom(self):
        """Show the edit nmrAtom popup for the clicked nmrAtom.
        """
        if (data := self.getRightMouseItem()) is not None and not data.empty:
            cShift = data.get(DATAFRAME_OBJECT)
            currentNmrAtom = cShift.nmrAtom if cShift else None

            if currentNmrAtom:
                from ccpn.ui.gui.popups.NmrAtomPopup import NmrAtomEditPopup

                popup = NmrAtomEditPopup(parent=self.mainWindow, mainWindow=self.mainWindow, obj=currentNmrAtom)
                popup.exec_()

    def _addNavigationStripsToContextMenu(self):
        if (data := self.getRightMouseItem()) is None or data.empty:
            return

        cShift = data.get(DATAFRAME_OBJECT)

        self._navigateMenu.clear()
        if cShift and cShift.nmrAtom:
            name = cShift.nmrAtom.name
            if cShift.value is None:
                return
            value = round(cShift.value, 3)
            if self._navigateMenu is not None:
                self._navigateMenu.addItem(f'All ({name}:{value})',
                                           callback=partial(self._navigateToChemicalShift,
                                                            chemicalShift=cShift,
                                                            stripPid=ALL))
                self._navigateMenu.addSeparator()
                for spectrumDisplay in self.mainWindow.spectrumDisplays:
                    for strip in spectrumDisplay.strips:
                        self._navigateMenu.addItem(f'{strip.pid} ({name}:{value})',
                                                   callback=partial(self._navigateToChemicalShift,
                                                                    chemicalShift=cShift,
                                                                    stripPid=strip.pid))
                    self._navigateMenu.addSeparator()

    def _navigateToChemicalShift(self, chemicalShift, stripPid):
        strips = []
        if stripPid == ALL:
            strips = self.mainWindow.strips
        else:
            strip = self.application.getByGid(stripPid)
            if strip:
                strips.append(strip)
        if strips:
            failedStripPids = []
            for strip in strips:

                try:
                    navigateToPositionInStrip(strip,
                                              positions=[chemicalShift.value],
                                              axisCodes=[chemicalShift.nmrAtom.name],
                                              widths=[])
                except:
                    failedStripPids.append(strip.pid)
            if len(failedStripPids) > 0:
                stripStr = 'strip' if len(failedStripPids) == 1 else 'strips'
                strips = ', '.join(failedStripPids)
                getLogger().warn(
                        f'Cannot navigate to position {round(chemicalShift.value, 3)} '
                        f'in {stripStr}: {strips} '
                        f'for nmrAtom {chemicalShift.nmrAtom.name}.')

    def _removeAssignments(self, delete=False):
        """Remove assignments from the selection and delete as required.
        """
        selection = self.getSelectedObjects()
        data = self.getRightMouseItem()
        _peaks = None

        if (data is not None and not data.empty) and selection:
            if (matching := [cs for cs in selection if cs and cs.nmrAtom]):

                # if there is a selection and the selection contains shift with nmrAtoms
                with undoBlockWithoutSideBar():
                    with notificationEchoBlocking():

                        # get the set of peaks that need updating, and corresponding set of nmrAtoms
                        _peaks = reduce(or_, [set(cs.assignedPeaks) for cs in matching])
                        nmrAtoms = set(cs.nmrAtom for cs in matching)
                        for peak in _peaks:
                            peakDimNmrAtoms = list(list(pp) for pp in peak.dimensionNmrAtoms)

                            # remove the required nmrAtoms from each assignment dimension
                            found = False
                            for peakDim in peakDimNmrAtoms:
                                pDims = set(peakDim)
                                diff = pDims - nmrAtoms
                                if diff != pDims:
                                    peakDim[:] = list(diff)
                                    found = True

                            if found:
                                # update the peak assignments
                                peak.dimensionNmrAtoms = peakDimNmrAtoms

                        if delete:
                            # delete the chemicalShift
                            for cs in matching:
                                cs.delete()


#=========================================================================================
# _CSLTableDelegate - handle editing the table, needs moving
#=========================================================================================

EDIT_ROLE = QtCore.Qt.EditRole
_EDITOR_SETTER = ('setColor', 'selectValue', 'setData', 'set', 'setValue', 'setText', 'setFile')
_EDITOR_GETTER = ('get', 'value', 'text', 'getFile')


class _CSLTableDelegate(QtWidgets.QStyledItemDelegate):
    """Handle the setting of data when editing the table.
    """
    _objectColumn = '_object'

    def __init__(self, parent):
        """Initialise the delegate.
        :param parent: link to the handling table
        """
        QtWidgets.QStyledItemDelegate.__init__(self, parent)
        self._parent = parent

    def setEditorData(self, widget, index) -> None:
        """Populate the editor widget when the cell is edited.
        """
        model = index.model()
        value = model.data(index, EDIT_ROLE)

        if not isinstance(value, (list, tuple)):
            value = (value,)

        for attrib in _EDITOR_SETTER:
            # get the method from the widget, and call with appropriate parameters
            if (func := getattr(widget, attrib, None)):
                if not callable(func):
                    raise TypeError(f"widget.{attrib} is not callable")

                func(*value)
                break

        else:
            raise Exception(f'Widget {widget} does not expose a set method; required for table editing')

    def setModelData(self, widget, mode, index):
        """Set the object to the new value.
        :param widget - typically a lineedit handling the editing of the cell
        :param mode - editing mode
        :param index - QModelIndex of the cell
        """
        for attrib in _EDITOR_GETTER:
            if (func := getattr(widget, attrib, None)):
                if not callable(func):
                    raise TypeError(f"widget.{attrib} is not callable")

                value = func()
                break

        else:
            raise Exception(f'Widget {widget} does not expose a get method; required for table editing')

        row, col = index.row(), index.column()
        try:
            # get the sorted element from the dataFrame
            df = self._parent._df
            iRow = self._parent.model()._sortOrder[row]
            iCol = df.columns.get_loc(self._objectColumn)
            # get the object
            obj = df.iat[iRow, iCol]

            # set the data which will fire notifiers to populate all tables (including this)
            func = self._parent._dataFrameObject.setEditValues[col]
            if func and obj:
                func(obj, value)

        except Exception as es:
            getLogger().debug('Error handling cell editing: %i %i - %s    %s    %s' % (
                row, col, str(es), self._parent.model()._sortOrder, value))


#=========================================================================================
# main
#=========================================================================================

def main():
    """Show the chemicalShiftTable module.
    """
    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # create a new test application
    app = newTestApplication(interface='Gui')
    application = getApplication()
    mainWindow = application.ui.mainWindow

    # add a module
    _module = ChemicalShiftTableModule(mainWindow=mainWindow)
    mainWindow.moduleArea.addModule(_module)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    main()
