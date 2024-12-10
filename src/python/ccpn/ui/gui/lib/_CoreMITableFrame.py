"""
Multi-index pandas dataFrame based widget.
There is no subclassed _CoreMITableFrameABC, separate class not required.

See: _CoreTableFrameABC
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
__dateModified__ = "$dateModified: 2024-11-28 14:13:57 +0000 (Thu, November 28, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-02-07 16:38:53 +0100 (Tue, February 07, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
from collections import OrderedDict
from abc import ABC, abstractmethod
from ccpn.core.lib.DataFrameObject import DataFrameObject
from ccpn.core.lib.Notifiers import Notifier
from ccpn.ui.gui.widgets.table.MIProjectTable import _MIProjectTableABC
from ccpn.ui.gui.widgets.table.TableABC import _TableABCMeta
from ccpn.ui.gui.widgets.table._TableModel import _TableModel
from ccpn.util.Logging import getLogger


_DEBUG = False


#=========================================================================================
# _CoreMITableWidgetABC
#=========================================================================================

class _CoreMITableWidgetMeta(_TableABCMeta, type(ABC)):
    """Metaclass implementing a post-initialise hook, ALWAYS called after __init__ has finished
    """
    # required to resolve metaclass conflict due to the addition of ABC
    ...


class _CoreMITableWidgetABC(_MIProjectTableABC, ABC, metaclass=_CoreMITableWidgetMeta):
    """Class to present a multi-index table for core objects
    """
    # define overriding attributes here for subclassing - not setting will default to these
    _enableSearch = True
    _enableDelete = True
    _enableExport = True
    _enableCopyCell = True

    def __init__(self, parent, *,
                 showHorizontalHeader=True, showVerticalHeader=False,
                 **kwds):
        """Initialise the widgets for the module.
        """
        super().__init__(parent,
                         multiSelect=True,
                         showHorizontalHeader=showHorizontalHeader,
                         showVerticalHeader=showVerticalHeader,
                         setLayout=True,
                         **kwds)

    #-----------------------------------------------------------------------------------------
    # Properties
    #-----------------------------------------------------------------------------------------

    @property
    @abstractmethod
    def _sourceObjects(self):
        """Return the list of source objects, e.g., _table.peaks/_table.nmrResidues.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._sourceObjects not implemented')

    @_sourceObjects.setter
    @abstractmethod
    def _sourceObjects(self, value):
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._sourceObjects not implemented')

    @property
    @abstractmethod
    def _sourceCurrent(self):
        """Return the list of source objects in the current list, e.g., current.peaks/current.nmrResidues
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._sourceCurrent not implemented')

    @_sourceCurrent.setter
    @abstractmethod
    def _sourceCurrent(self, value):
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._sourceCurrent not implemented')

    #-----------------------------------------------------------------------------------------
    # Selection/Action callbacks
    #-----------------------------------------------------------------------------------------

    def selectionCallback(self, selected, deselected, selection, lastItem):
        """set as current the selected core-objects on the table.
        """
        try:
            objs = list(selection[self._OBJECT])
            self._sourceCurrent = objs
        except Exception as es:
            getLogger().debug2(f'{self.__class__.__name__}.selectionCallback: No selection\n{es}')

    #-----------------------------------------------------------------------------------------
    # Create table and row methods
    #-----------------------------------------------------------------------------------------

    def _newRowFromUniqueId(self, df, obj, uniqueId):
        """Create a new row to insert into the dataFrame or replace row.
        """
        # generate a new row
        listItem = OrderedDict()
        for header in self._columnDefs.columns:
            try:
                listItem[header.headerText] = header.getValue(obj)
            except Exception as es:
                # NOTE:ED - catch any nasty surprises in tables - empty string stops tables changing column-type
                listItem[header.headerText] = ''

        return list(listItem.values())

    def _derivedFromObject(self, obj):
        """Get a tuple of derived values from obj.
        Not very generic yet - column class now seems redundant.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._derivedFromObject not implemented')

    def buildTableDataFrame(self) -> DataFrameObject:
        """Return a Pandas dataFrame from an internal list of objects.
        The columns are based on the 'func' functions in the columnDefinitions.
        :return pandas dataFrame
        """
        allItems = []
        if self._table:
            self._columnDefs = self._getTableColumns(self._table)

            objects = []
            for col, obj in enumerate(self._sourceObjects):
                listItem = OrderedDict()
                for header in self._columnDefs.columns:
                    try:
                        listItem[header.headerText] = header.getValue(obj)
                    except Exception as es:
                        # NOTE:ED - catch any nasty surprises in tables
                        getLogger().debug2(f'Error creating table information {es}')
                        listItem[header.headerText] = None
                allItems.append(listItem)
                objects.append(obj)
            df = pd.DataFrame(allItems, columns=self._columnDefs.headings)
        else:
            self._columnDefs = self._getTableColumns()
            df = pd.DataFrame(columns=self._columnDefs.headings)

        # use the object as the index, object always exists even if isDeleted
        df.set_index(df[self.OBJECTCOLUMN], inplace=True, )

        return DataFrameObject(dataFrame=df,
                               columnDefs=self._columnDefs or [],
                               table=self)

    def getCellToRows(self, cellItem, attribute=None):
        """Get the list of objects which cellItem maps to for this table.
        To be subclassed as required.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}.getCellToRows not implemented')

    def _updateCellCallback(self, data):
        """Notifier callback for updating the table.
        :param data:
        """
        # print(f'>>> _updateCellCallback')
        with self._blockTableSignals('_updateCellCallback'):
            cellData = data[Notifier.OBJECT]

            rowObjs = []
            _triggerType = Notifier.CHANGE
            if (attr := self.cellClassNames.get(type(cellData))):
                rowObjs, _triggerType = self.getCellToRows(cellData, attr)
            # update the correct row by calling row handler
            for rowObj in rowObjs:
                rowData = {Notifier.OBJECT : rowObj,
                           Notifier.TRIGGER: _triggerType or data[Notifier.TRIGGER],
                           }
                self._updateRowCallback(rowData)

    def _updateRowCallback(self, data):
        """Notifier callback for updating the table for change in chemicalShifts.
        :param data: notifier content.
        """
        # print(f'>>> _updateRowCallback')
        with self._blockTableSignals('_updateRowCallback'):
            obj = data[Notifier.OBJECT]
            model: _TableModel = self.model()

            # check that the dataframe and object are valid
            if self._df is None:
                getLogger().debug2(f'{self.__class__.__name__}._updateRowCallback: dataFrame is None')
                return
            if obj is None:
                getLogger().debug2(f'{self.__class__.__name__}._updateRowCallback: callback object is undefined')
                return

            trigger = data[Notifier.TRIGGER]
            try:
                df = self._df
                objSet = set(self._sourceObjects)  # objects in the list
                tableSet = set() if (df is None or df.empty) else set(df[self.OBJECTCOLUMN])

                if trigger == Notifier.DELETE:
                    # uniqueIds in the visible table
                    if obj in (tableSet - objSet):
                        # remove from the table
                        model._deleteRow(obj)
                        self._reindexTable()
                elif trigger == Notifier.CREATE:
                    # uniqueIds in the visible table
                    if obj in (objSet - tableSet):
                        if df is None or df.empty:
                            # create a new table from the list - should only be a single item
                            #   required here as the peak tables can be different widths
                            self.populateTable()
                        else:
                            # insert into the table
                            newRow = self._newRowFromUniqueId(df, obj, None)
                            model._insertRow(obj, newRow)
                            self._reindexTable()
                        # highlight the new row
                        self._highlightRow(obj)
                elif trigger == Notifier.CHANGE:
                    # uniqueIds in the visible table
                    if obj in (objSet & tableSet):
                        # visible table dataframe update - object MUST be in the table
                        newRow = self._newRowFromUniqueId(df, obj, None)
                        model._updateRow(obj, newRow)
                elif trigger == Notifier.RENAME:
                    if obj in (objSet & tableSet):
                        # visible table dataframe update
                        newRow = self._newRowFromUniqueId(df, obj, None)
                        model._updateRow(obj, newRow)
                    elif obj in (objSet - tableSet):
                        # insert renamed object INTO the table
                        newRow = self._newRowFromUniqueId(df, obj, None)
                        model._insertRow(obj, newRow)
                        self._reindexTable()
                        # highlight the new row
                        self._highlightRow(obj)
                    elif obj in (tableSet - objSet):
                        # remove renamed object OUT of the table
                        model._deleteRow(obj)
                        self._reindexTable()

            except Exception as es:
                getLogger().debug2(f'{self.__class__.__name__}._updateRowCallback: Error updating row in table - {es}')

    def _highlightRow(self, obj):
        """Highlight the new row if in selection.
        """
        # probably not the fastest checking for current
        if obj in self._sourceCurrent:
            # highlight the row
            selectionModel = self.selectionModel()
            model = self.model()
            _sortIndex = model._sortIndex
            try:
                if (row := self._df.index.get_loc(obj)) is not None:
                    rowIndex = model.index(_sortIndex.index(row), 0)
                    selectionModel.select(rowIndex, selectionModel.Select | selectionModel.Rows)
            except Exception:
                getLogger().debug2(f'{self.__class__.__name__}._highlightRow: Error highlighting row')

    def _reindexTable(self):
        """Reset the index column for the table.
        Not required for most core-object tables, but residues and nmrResidues have an order.
        """
        if self._INDEX is not None:
            # must be done after the insert/delete as the object-column will have changed
            df = self._df
            objs = tuple(self._sourceObjects)  # objects in the list
            tableObjs = tuple(df[self.OBJECTCOLUMN])  # objects currently in the table

            # table will automatically replace this on the update
            df[self._INDEX] = [objs.index(obj) if obj in objs else 0 for obj in tableObjs]

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

    #-----------------------------------------------------------------------------------------
    # Table context menu
    #-----------------------------------------------------------------------------------------

    #-----------------------------------------------------------------------------------------
    # Table functions
    #-----------------------------------------------------------------------------------------

    #-----------------------------------------------------------------------------------------
    # Updates
    #-----------------------------------------------------------------------------------------

    def _updateAllModule(self, data=None):
        """Updates the table and the settings widgets.
        """
        self._update()

    def _update(self):
        """Display the objects on the table for the selected list.
        """
        if self._table and self._sourceObjects:
            self.populateTable(selectedObjects=self._sourceCurrent)
        else:
            self.populateEmptyTable()

    def queueFull(self):
        """Method that is called when the queue is deemed to be too big.
        Apply overall operation instead of all individual notifiers.
        """
        self._update()

    #-----------------------------------------------------------------------------------------
    # object properties
    #-----------------------------------------------------------------------------------------

    ...


#=========================================================================================
# _CoreMITableFrameABC
#=========================================================================================

# class shouldn't be needed
...
