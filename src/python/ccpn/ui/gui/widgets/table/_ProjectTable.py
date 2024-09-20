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
__dateModified__ = "$dateModified: 2024-09-13 20:32:53 +0100 (Fri, September 13, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-09-08 17:13:11 +0100 (Thu, September 08, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
from PyQt5 import QtWidgets, QtCore, QtGui
from collections import defaultdict
from functools import partial
from time import time_ns
from types import SimpleNamespace

from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, catchExceptions
from ccpn.core.lib.Notifiers import Notifier
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.table.TableABC import TableABC
from ccpn.ui.gui.widgets.table._TableCommon import INDEX_ROLE
from ccpn.ui.gui.widgets.table._TableDelegates import _TableDelegate
from ccpn.ui._implementation.QueueHandler import QueueHandler
from ccpn.util.Logging import getLogger
from ccpn.util.OrderedSet import OrderedSet
from ccpn.util.Common import NOTHING


#=========================================================================================
# _ProjectTableABC project specific
#=========================================================================================

# define a simple class that can contain a simple id
blankId = SimpleNamespace(className='notDefined', serial=0)

OBJECT_CLASS = 0
OBJECT_PARENT = 1
MODULEIDS = {}

_TABLE_KWDS = ('parent', 'df',
               'multiSelect', 'selectRows',
               'showHorizontalHeader', 'showVerticalHeader',
               'borderWidth', 'cellPadding', 'focusBorderWidth', 'gridColour',
               '_resize', 'setWidthToColumns', 'setHeightToRows',
               'setOnHeaderOnly', 'showGrid', 'wordWrap',
               'alternatingRows',
               'selectionCallback', 'selectionCallbackEnabled',
               'actionCallback', 'actionCallbackEnabled',
               'enableExport', 'enableDelete', 'enableSearch', 'enableCopyCell',
               'tableMenuEnabled', 'toolTipsEnabled',
               'ignoreStyleSheet',
               'mainWindow', 'moduleParent'
               )


class _ProjectTableABC(TableABC, Base):
    className = '_ProjectTableABC'
    attributeName = '_ProjectTableABC'

    _OBJECT = '_object'
    _ISDELETED = 'isDeleted'

    OBJECTCOLUMN = '_object'
    INDEXCOLUMN = 'index'
    _INDEX = None

    columnHeaders = {}
    tipTexts = ()

    # define the notifiers that are required for the specific table-type
    tableClass = None
    rowClass = None
    cellClass = None
    tableName = None
    rowName = None
    cellClassNames = None

    selectCurrent = True
    callBackClass = None
    search = False
    enableEditDelegate = True

    _enableSelectionCallback = True
    _enableActionCallback = True

    # set the queue handling parameters
    _maximumQueueLength = 0
    _logQueue = False

    _rowHeightScale = 1.0

    def __init__(self, parent, *, df=None,
                 multiSelect=True, selectRows=True,
                 showHorizontalHeader=True, showVerticalHeader=True,
                 borderWidth=2, cellPadding=2, focusBorderWidth=1, gridColour=None,
                 _resize=False, setWidthToColumns=False, setHeightToRows=False,
                 setOnHeaderOnly=False, showGrid=False, wordWrap=False,
                 alternatingRows=True,
                 selectionCallback=NOTHING, selectionCallbackEnabled=NOTHING,
                 actionCallback=NOTHING, actionCallbackEnabled=NOTHING,
                 enableExport=NOTHING, enableDelete=NOTHING, enableSearch=NOTHING, enableCopyCell=NOTHING,
                 tableMenuEnabled=NOTHING, toolTipsEnabled=NOTHING,
                 # local parameters
                 ignoreStyleSheet=True,
                 mainWindow=None, moduleParent=None,
                 **kwds):
        """Initialise the widgets for the module.

        :param parent:
        :param df:
        :param multiSelect:
        :param selectRows:
        :param showHorizontalHeader:
        :param showVerticalHeader:
        :param borderWidth:
        :param cellPadding:
        :param focusBorderWidth:
        :param gridColour:
        :param _resize:
        :param setWidthToColumns:
        :param setHeightToRows:
        :param setOnHeaderOnly:
        :param showGrid:
        :param wordWrap:
        :param alternatingRows:
        :param selectionCallback:
        :param selectionCallbackEnabled:
        :param actionCallback:
        :param actionCallbackEnabled:
        :param enableExport:
        :param enableDelete:
        :param enableSearch:
        :param enableCopyCell:
        :param tableMenuEnabled:
        :param toolTipsEnabled:
        :param ignoreStyleSheet:
        :param mainWindow:
        :param moduleParent:
        :param kwds:
        """
        super().__init__(parent, df=df,
                         multiSelect=multiSelect, selectRows=selectRows,
                         showHorizontalHeader=showHorizontalHeader, showVerticalHeader=showVerticalHeader,
                         borderWidth=borderWidth, cellPadding=cellPadding, focusBorderWidth=focusBorderWidth,
                         gridColour=gridColour,
                         _resize=_resize, setWidthToColumns=setWidthToColumns, setHeightToRows=setHeightToRows,
                         setOnHeaderOnly=setOnHeaderOnly, showGrid=showGrid, wordWrap=wordWrap,
                         alternatingRows=alternatingRows,
                         selectionCallback=selectionCallback, selectionCallbackEnabled=selectionCallbackEnabled,
                         actionCallback=actionCallback, actionCallbackEnabled=actionCallbackEnabled,
                         enableExport=enableExport, enableDelete=enableDelete, enableSearch=enableSearch,
                         enableCopyCell=enableCopyCell,
                         tableMenuEnabled=tableMenuEnabled, toolTipsEnabled=toolTipsEnabled,
                         )
        # Base messes up styleSheets defined in superclass
        baseKwds = {k: v for k, v in kwds.items() if k not in _TABLE_KWDS}
        Base._init(self, ignoreStyleSheet=ignoreStyleSheet, **baseKwds)

        # Derive application, project, and current from mainWindow
        if mainWindow:
            self.mainWindow = mainWindow
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
            # excellent - this can work here :)
            # self.application.ui.qtApp.paletteChanged.connect(self._printPalette)

        self.moduleParent = moduleParent
        self._table = None
        self._dataFrameObject = None

        self._setTableNotifiers()

        self._lastMouseItem = None
        self._mousePressed = False
        self._lastTimeClicked = time_ns()
        self._clickInterval = QtWidgets.QApplication.instance().doubleClickInterval() * 1e6
        self._tableSelectionBlockingTime = 0
        self._currentRow = None
        self._lastSelection = [None]

        # set internal flags
        self._mousePressedPos = None
        self._userKeyPressed = False
        self._selectOverride = False
        self._scrollOverride = False

        self._rightClickedTableIndex = None  # last selected item in a table before raising the context menu. Enabled with mousePress event filter

        # notifier queue handling
        self._queueHandler = QueueHandler(self,
                                          completeCallback=self.update,
                                          queueFullCallback=self.queueFull,
                                          name=f'PandasTableNotifierHandler-{self}',
                                          maximumQueueLength=self._maximumQueueLength,
                                          log=self._logQueue)

        if self.enableEditDelegate:
            # set the delegate for editing
            delegate = _TableDelegate(self, objectColumn=self.OBJECTCOLUMN)
            self.setItemDelegate(delegate)

    @staticmethod
    def _printPalette(pal: QtGui.QPalette):
        # print the colours from the updated palette - only 'highlight' seems to be effective
        # QT modifies this to give different selection shades depending on the widget
        print('Palette ~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        colNames = ['windowText',  # 0
                    'button',  # 1
                    'light',  # 2
                    'midlight',  # 3
                    'dark',  # 4
                    'mid',  # 5
                    'text',  # 6
                    'brightText',  # 7
                    'buttonText',  # 8
                    'base',  # 9
                    'window',  # 10
                    'shadow',  # 11
                    'highlight',  # 12
                    'highlightedText',  # 13
                    'link',  # 14
                    'linkVisited',  # 15
                    'alternateBase',  # 16
                    'noRole',  # 17
                    'toolTipBase',  # 18
                    'toolTipText',  # 19
                    'placeholderText',  # 20
                    ]
        for colnum, colname in enumerate(colNames):
            color = pal.color(QtGui.QPalette.Active, QtGui.QPalette.ColorRole(colnum)).name()
            print(f"  Role: {colname:20}  {color}")

    def setModel(self, model: QtCore.QAbstractItemModel) -> None:
        """Set the model for the view
        """
        super().setModel(model)
        model.showEditIcon = True

    #=========================================================================================
    # Mouse/Keyboard handling
    #=========================================================================================

    def mousePressEvent(self, event):
        """handle mouse press events
        Clicking is handled on the mouse release
        """
        if event.button() == QtCore.Qt.RightButton:
            # stops the selection from the table when the right button is clicked
            self._rightClickedTableIndex = self.indexAt(event.pos())
        else:
            self._rightClickedTableIndex = None

        super().mousePressEvent(event)

        self.setCurrent()

    def getRightMouseItem(self):
        if self._rightClickedTableIndex:
            try:
                row, _col = self._rightClickedTableIndex.data(INDEX_ROLE)
                return self._df.iloc[row]
            except Exception:
                return None

    def setCurrent(self):
        """Set self to current.guiTable"""
        if self.current is not None:
            self.current.guiTable = self
            # self._setCurrentStyleSheet()

    def unsetCurrent(self):
        """Set self to current.guiTable"""
        if self.current is not None:
            self.current.guiTable = None
            # self.setStyleSheet(self._defaultStyleSheet)

    #=========================================================================================
    # Table functions
    #=========================================================================================

    def deleteSelectionFromTable(self):
        """Delete all objects in the selection from the project
        """
        if not (selected := self.getSelectedObjects()):
            return

        n = len(selected)

        # make a list of the types of objects to delete
        objNames = OrderedSet(f"{obj.className}{'' if n == 1 else 's'}" for obj in selected if hasattr(obj, 'pid'))

        # put into the dialog message
        title = f"Delete Item{'' if n == 1 else 's'}"
        if objStr := ', '.join(objNames):
            msg = f"Delete {'' if n == 1 else '%d' % n} {objStr} from the project?"
        else:
            msg = f"Delete {'' if n == 1 else '%d ' % n}selected item{'' if n == 1 else 's'} from the project?"

        if MessageDialog.showYesNo(title, msg):

            with catchExceptions(application=self.application,
                                 errorStringTemplate='Error deleting objects from table; "%s"'):
                if hasattr(selected[0], 'project'):
                    with undoBlockWithoutSideBar():
                        # echo [sI.pid for sI in selected]
                        for obj in selected:
                            if hasattr(obj, 'pid'):
                                obj.delete()

                else:
                    # TODO:ED this is deleting from PandasTable, check for another way to get project
                    for obj in selected:
                        if hasattr(obj, 'pid'):
                            obj.delete()

            self.clearSelection()
            return True

    #=========================================================================================
    # Header context menu
    #=========================================================================================

    #=========================================================================================
    # Search methods
    #=========================================================================================

    #=========================================================================================
    # Handle dropped items
    #=========================================================================================

    def _processDroppedItems(self, data):
        """CallBack for Drop events
        """
        if self.tableClass and data:
            pids = data.get('pids', [])
            self._handleDroppedItems(pids, self.tableClass, self.moduleParent._modulePulldown)

    def _handleDroppedItems(self, pids, objType, pulldown):
        """Handle dropping an item onto the module.
        :param pids: the selected objects pids
        :param objType: the instance of the obj to handle. Eg. PeakList
        :param pulldown: the pulldown of the module wich updates the table
        :return: Actions: Select the dropped item on the table or/and open a new modules if multiple drops.
        If multiple different obj instances, then asks first.
        """
        # import here to stop circular import
        from ccpn.ui.gui.lib.MenuActions import _openItemObject

        objs = [self.project.getByPid(pid) for pid in pids]

        selectableObjects = [obj for obj in objs if isinstance(obj, objType)]
        others = [obj for obj in objs if not isinstance(obj, objType)]

        if selectableObjects:
            _openItemObject(self.mainWindow, selectableObjects[1:])
            pulldown.select(selectableObjects[0].pid)

        elif othersClassNames := list({obj.className for obj in others if hasattr(obj, 'className')}):
            title, msg = (('Dropped wrong item.',
                           f"Do you want to open the {''.join(othersClassNames)} in a new module?")
                          if len(othersClassNames) == 1 else
                          ('Dropped wrong items.', 'Do you want to open items in new modules?'))
            if MessageDialog.showYesNo(title, msg):
                _openItemObject(self.mainWindow, others)

    #=========================================================================================
    # Table updates
    #=========================================================================================

    def _getTableColumns(self, source=None):
        """format of column = ( Header Name, value, tipText, editOption)
        editOption allows the user to modify the value content by doubleclick
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._getTableColumns not implemented')

    def populateTable(self, rowObjects=None, columnDefs=None,
                      selectedObjects=None, setOnHeaderOnly=False):
        """Populate the table with a set of objects to highlight, or keep current selection highlighted
        with the first item visible.

        Use selectedObjects = [] to clear the selected items

        :param rowObjects: list of objects to set each row
        """
        self.project.blankNotification()

        # if nothing passed in then keep the current highlighted objects
        objs = selectedObjects if selectedObjects is not None else self.getSelectedObjects()

        try:
            self._dataFrameObject = self.buildTableDataFrame()
            _df = self._dataFrameObject.dataFrame

            # remember the old sorting-values
            sortColumn, sortOrder = None, None
            if (oldModel := self.model()):
                sortColumn = oldModel._sortColumn
                sortOrder = oldModel._sortOrder

            # check with the table default
            if sortColumn is None:
                sortColumn = self.defaultSortColumn
            if sortOrder is None:
                sortOrder = self.defaultSortOrder

            # update model to the new _df
            model = self.updateDf(_df, setOnHeaderOnly=setOnHeaderOnly)

            self.resizeColumnsToContents()

            try:
                # get a valid column from integer or string/tuple[multi-index]
                intCol = sortColumn if isinstance(sortColumn, int) else _df.columns.get_loc(sortColumn)
            except Exception:
                intCol = 0

            # re-sort the table
            if oldModel and (0 <= intCol < model.columnCount()) and self.isSortingEnabled():
                model._sortColumn = sortColumn
                model._sortOrder = sortOrder
                self.sortByColumn(intCol, sortOrder)

            self.postUpdateDf()
            self._highLightObjs(objs)

            # set the tipTexts
            if self._columnDefs is not None:
                model.setToolTips('horizontal', self._columnDefs.tipTexts)

        except Exception as es:
            getLogger().warning('Error populating table', str(es))
            self.populateEmptyTable()
            if self.application and self.application._isInDebugMode:
                raise

        finally:
            self.project.unblankNotification()

    def populateEmptyTable(self):
        """Populate with an empty dataFrame containing the correct column headers.
        """
        self._dataFrameObject = None
        _df = pd.DataFrame({val: [] for val in self.columnHeaders.values()})
        if self.OBJECTCOLUMN in _df.columns:
            # use the object as the index, object always exists even if isDeleted
            _df.set_index(_df[self.OBJECTCOLUMN], inplace=True, )
        self.updateDf(_df, resize=True)
        self.headerColumnMenu.resetToDefaultHiddenColumns()

    #=========================================================================================
    # Build the dataFrame for the table
    #=========================================================================================

    def buildTableDataFrame(self):
        """Return a Pandas dataFrame from an internal list of objects
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}.buildTableDataFrame not implemented')

    #=========================================================================================
    # Notifiers
    #=========================================================================================

    def _initialiseTableNotifiers(self):
        """Set the initial notifiers to empty
        """
        self._tableNotifier = None
        self._rowNotifier = None
        self._cellNotifiers = []
        self._selectCurrentNotifier = None
        self._searchNotifier = None

    def _setTableNotifiers(self):
        """Set a Notifier to call when an object is created/deleted/renamed/changed
        rename calls on name
        change calls on any other attribute
        """
        self._initialiseTableNotifiers()

        if self.tableClass:
            self._tableNotifier = Notifier(self.project,
                                           [Notifier.CREATE, Notifier.DELETE, Notifier.RENAME],
                                           self.tableClass.__name__,
                                           partial(self._queueGeneralNotifier, self._updateTableCallback),
                                           onceOnly=True)

        if self.rowClass:
            # 'i-1' residue spawns rename but the 'i' residue only fires a change
            self._rowNotifier = Notifier(self.project,
                                         [Notifier.CREATE, Notifier.DELETE, Notifier.RENAME, Notifier.CHANGE],
                                         self.rowClass.__name__,
                                         partial(self._queueGeneralNotifier, self._updateRowCallback),
                                         onceOnly=True)  # should be True, but doesn't work

        if self.cellClassNames:
            for cellClass, attr in self.cellClassNames.items():
                self._cellNotifiers.append(Notifier(self.project,
                                                    [Notifier.CHANGE, Notifier.CREATE, Notifier.DELETE,
                                                     Notifier.RENAME],
                                                    cellClass.__name__,
                                                    partial(self._queueGeneralNotifier, self._updateCellCallback),
                                                    onceOnly=True))

        if self.selectCurrent:
            self._selectCurrentNotifier = Notifier(self.current,
                                                   [Notifier.CURRENT],
                                                   self.callBackClass._pluralLinkName,
                                                   self._selectCurrentCallBack,  # strange behaviour if deferred
                                                   # partial(self._queueGeneralNotifier, self._selectCurrentCallBack),
                                                   )

        if self.search:
            self._searchNotifier = Notifier(self.current,
                                            [Notifier.CURRENT],
                                            self.search._pluralLinkName,
                                            self._searchCallBack
                                            )

        # add a cleaner id to the opened guiTable list
        MODULEIDS[id(self.moduleParent)] = len(MODULEIDS)

    def _queueGeneralNotifier(self, func, data):
        """Add the notifier to the queue handler
        """
        self._queueHandler.queueAppend([func, data])

    def _clearTableNotifiers(self):
        """Clean up the notifiers
        """
        getLogger().debug(f'Clearing table notifiers {self}')

        if self._tableNotifier is not None:
            self._tableNotifier.unRegister()
            self._tableNotifier = None

        if self._rowNotifier is not None:
            self._rowNotifier.unRegister()
            self._rowNotifier = None

        if self._cellNotifiers:
            for cell in self._cellNotifiers:
                if cell is not None:
                    cell.unRegister()
            self._cellNotifiers = []

        if self._selectCurrentNotifier is not None:
            self._selectCurrentNotifier.unRegister()
            self._selectCurrentNotifier = None

        if self._searchNotifier is not None:
            self._searchNotifier.unRegister()
            self._searchNotifier = None

    def _close(self):
        self._clearTableNotifiers()
        super()._close()

    def clearCurrentCallback(self):
        """Clear the callback function for current object/list change
        """
        self.selectCurrent = False
        if self._selectCurrentNotifier is not None:
            self._selectCurrentNotifier.unRegister()
            self._selectCurrentNotifier = None

    #=========================================================================================
    # Notifier callbacks
    #=========================================================================================

    def _updateTableCallback(self, data):
        """Notifier callback when the table has changed
        :param data: notifier content
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._updateTableCallback not implemented')

    def _updateRowCallback(self, data):
        """Notifier callback to update a row in the table
        :param data: notifier content
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._updateRowCallback not implemented')

    def _updateCellCallback(self, data):
        """Notifier callback to update a cell in the table
        :param data: notifier content
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._updateCellCallback not implemented')

    def _selectCurrentCallBack(self, data):
        """Callback from a current changed notifier to highlight the current objects
        :param data
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._selectCurrentCallBack not implemented')

    def _searchCallBack(self, data):
        """Callback to populate the search bar with the selected item
        :param data: notifier content
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}._searchCallBack not implemented')

    def selectionCallback(self, selected, deselected, selection, lastRow):
        """Handle item selection has changed in table - call user callback
        :param selected: table indexes selected
        :param deselected: table indexes deselected
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}.selectionCallback not implemented')

    def actionCallback(self, selection, lastItem):
        """Handle item selection has changed in table - call user callback
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}.actionCallback not implemented')

    # def setActionCallback(self, actionCallback=None):
    #     # enable callbacks
    #     if not (actionCallback is None or callable(actionCallback)):
    #         raise ValueError(f'{self.__class__.__name__}.setActionCallback: actionCallback is not None|callable')
    #
    #     self.actionCallback = actionCallback

    def setCheckBoxCallback(self, checkBoxCallback):
        # enable callback on the checkboxes
        self._checkBoxCallback = checkBoxCallback

    #=========================================================================================
    # Table methods
    #=========================================================================================

    def getSelectedObjects(self, fromSelection=None):
        """Return the selected core objects
        :param fromSelection:
        :return: get a list of table objects. If the table has a header called pid, the object is a ccpn Core obj like Peak,
        otherwise is a Pandas-series object corresponding to the selected row(s).
        """
        model = self.selectionModel()

        # selects all the items in the row - may need to check selectionMode
        if selection := (fromSelection or model.selectedRows()):
            selectedObjects = []

            valuesDict = defaultdict(list)
            col = self._df.columns.get_loc(self.OBJECTCOLUMN)
            for idx in selection:
                # it may be a bad index - returns None
                if loc := idx.data(INDEX_ROLE):
                    row, _col = loc

                    # col = idx.column()
                    # if self._objects and len(self._objects) > 0:
                    #     if isinstance(self._objects[0], pd.Series):
                    #         h = self.horizontalHeaderItem(col).text()
                    #         v = self.item(row, col).text()
                    #         valuesDict[h].append(v)
                    #
                    #     else:

                    objIndex = self._df.iat[row, col]
                    if (obj := self.project.getByPid(objIndex.strip('<>')) if isinstance(objIndex, str) else objIndex):
                        selectedObjects.append(obj)

            if valuesDict:
                selectedObjects = [row for i, row in pd.DataFrame(valuesDict).iterrows()]

            return selectedObjects

    def clearSelection(self):
        """Clear the current selection in the table
        and remove objects from the current list
        """
        with self._blockTableSignals('clearSelection'):
            # get the selected objects from the table
            objList = self.getSelectedObjects() or []
            super().clearSelection()  # no signals
            # remove from the current list
            multiple = self.callBackClass._pluralLinkName if self.callBackClass else None
            if (self._df is not None and not self._df.empty) and multiple:
                if multipleAttr := getattr(self.current, multiple, []):
                    # need to remove objList from multipleAttr - fires only one current change
                    setattr(self.current, multiple, tuple(set(multipleAttr) - set(objList)))
            self._lastSelection = [None]

    #=========================================================================================
    # Highlight objects in table
    #=========================================================================================

    def _highLightObjs(self, selection, scrollToSelection=True):

        # skip if the table is empty
        if self._df is None or self._df.empty:
            return
        with self._blockTableSignals('_highLightObjs'):
            selectionModel = self.selectionModel()
            model = self.model()
            selectionModel.clearSelection()
            if selection:
                if len(selection) > 0 and isinstance(selection[0], pd.Series):
                    # not sure how to handle this
                    return
                uniqObjs = set(selection)
                _sortIndex = model._sortIndex
                dfTemp = self._df.reset_index(drop=True)
                data = [dfTemp[dfTemp[self._OBJECT] == obj] for obj in uniqObjs]
                if rows := [_sortIndex.index(_dt.index[0]) for _dt in data if not _dt.empty]:
                    minInd = model.index(min(rows), 0)
                    for row in rows:
                        rowIndex = model.index(row, 0)
                        selectionModel.select(rowIndex, selectionModel.Select | selectionModel.Rows)
                    if scrollToSelection and not self._scrollOverride and minInd is not None:
                        self.scrollTo(minInd, self.EnsureVisible)

    def highlightObjects(self, objectList, scrollToSelection=True):
        """Highlight a list of objects in the table
        """
        objs = []
        if objectList:
            # get the list of objects, exclude deleted
            for obj in objectList:
                if isinstance(obj, str):
                    objFromPid = self.project.getByPid(obj)
                    if objFromPid and not objFromPid.isDeleted:
                        objs.append(objFromPid)
                else:
                    objs.append(obj)
        if objs:
            self._highLightObjs(objs, scrollToSelection=scrollToSelection)
        else:
            with self._blockTableSignals('highlightObjects'):
                # clear the selection with no object updates
                self.selectionModel().clearSelection()

    #=========================================================================================
    # Notifier queue handling
    #=========================================================================================

    def queueFull(self):
        """Method that is called when the queue is deemed to be too big.
        Apply overall operation instead of all individual notifiers.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: {self.__class__.__name__}.queueFull not implemented')

    #=========================================================================================
    # Common object properties
    #=========================================================================================

    @staticmethod
    def _getCommentText(obj):
        """
        CCPN-INTERNAL: Get a comment from GuiTable
        """
        try:
            return '' if obj.comment == '' or not obj.comment else obj.comment
        except Exception:
            return ''

    @staticmethod
    def _setComment(obj, value):
        """
        CCPN-INTERNAL: Insert a comment into object
        """
        obj.comment = value or None

    @staticmethod
    def _getAnnotation(obj):
        """
        CCPN-INTERNAL: Get an annotation from GuiTable
        """
        try:
            return '' if obj.annotation == '' or not obj.annotation else obj.annotation
        except Exception:
            return ''

    @staticmethod
    def _setAnnotation(obj, value):
        """
        CCPN-INTERNAL: Insert an annotation into object
        """
        obj.annotation = value or None
