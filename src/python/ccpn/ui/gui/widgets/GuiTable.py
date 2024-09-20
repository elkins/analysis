"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-05-17 13:37:45 +0100 (Fri, May 17, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2018-12-20 15:44:35 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

import random
import time

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QAbstractItemView
import pandas as pd
import os
from time import time_ns
from pyqtgraph import TableWidget
from pyqtgraph.widgets.TableWidget import _defersort
from ccpn.core.lib.CallBack import CallBack
from ccpn.core.lib.DataFrameObject import DataFrameObject, DATAFRAME_OBJECT, \
    DATAFRAME_INDEX, DATAFRAME_PID, DATAFRAME_ISDELETED

from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.guiSettings import getColours
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.FileDialog import TablesFileDialog
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.ColumnViewSettings import ColumnViewSettingsPopup
from ccpn.ui.gui.widgets.SearchWidget import attachSearchWidget
from ccpn.ui.gui.widgets.TableSorting import CcpnTableWidgetItem
from ccpn.core.lib.Notifiers import Notifier
from ccpn.util.Common import makeIterableList
from functools import partial
from ccpn.util.OrderedSet import OrderedSet
from collections import OrderedDict, defaultdict
from ccpn.util.Logging import getLogger
from types import SimpleNamespace
from contextlib import contextmanager
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar
from ccpn.core.lib.Util import getParentObjectFromPid
from ccpn.core.lib.ContextManagers import catchExceptions
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.Font import setWidgetFont, getFontHeight, TABLEFONT
from ccpn.util.AttrDict import AttrDict
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.RowExpander import RowExpander
from ccpn.ui.gui.guiSettings import getColours, BORDERFOCUS, GREEN1, GUITABLE_DROP_BORDER
from ccpn.ui.gui.widgets.SideBar import SideBar
from ccpn.ui.gui.widgets.DropBase import DropBase
import math
from ccpn.util.Path import aPath
from ccpn.ui.gui.lib.ModuleLib import getBlockingDialogs


OBJECT_CLASS = 0
OBJECT_PARENT = 1


def __sortByColumn__(self, col, newOrder):
    try:
        super(QtWidgets.QTableWidget, self).sortByColumn(col, newOrder)
    except Exception as es:
        pass


# define a simple class that can contains a simple id
blankId = SimpleNamespace(className='notDefined', serial=0)

MODULEIDS = {}
NAME    = 'name'
GETTER  = 'getter'
SETTER  = 'setter'
TIPTEXT = 'tipText'
FORMAT  = 'format'
WIDTH   = 'width'
HIDDEN  = 'hidden'

def _moduleId(module):
    return MODULEIDS[id(module)] if id(module) in MODULEIDS else -1


# Exporters

def dataFrameToExcel(dataFrame, path, sheet_name='Table', columns=None):
    if dataFrame is not None:
        path = aPath(path)
        path = path.assureSuffix('xlsx')
        if columns is not None and isinstance(columns, list):  #this is wrong. columns can be a 1d array
            dataFrame.to_excel(path, sheet_name=sheet_name, columns=columns)
        else:
            dataFrame.to_excel(path, sheet_name=sheet_name)


def dataFrameToCsv(dataFrame, path, *args):
    dataFrame.to_csv(path)


def dataFrameToTsv(dataFrame, path, *args):
    dataFrame.to_csv(path, sep='\t')


def dataFrameToJson(dataFrame, path, *args):
    dataFrame.to_json(path, orient='split', default_handler=str)


def findExportFormats(path, dataFrame, sheet_name='Table', filterType=None, columns=None):
    formatTypes = OrderedDict([
        ('.xlsx', dataFrameToExcel),
        ('.csv', dataFrameToCsv),
        ('.tsv', dataFrameToTsv),
        ('.json', dataFrameToJson)
        ])

    extension = os.path.splitext(path)[1]
    if not extension:
        extension = '.xlsx'
    if extension in formatTypes.keys():
        formatTypes[extension](dataFrame, path, sheet_name, columns)
        return
    else:
        try:
            findExportFormats(str(path) + filterType, sheet_name)
        except:
            showWarning('Could not export', 'Format file not supported or not provided.'
                                            '\nUse one of %s' % ', '.join(formatTypes))
            getLogger().warning('Format file not supported')


def exportTableDialog(dataFrame, columns=None, path='~/table.xlsx'):
    """Open the ExportDialog to export any dataFrame to different formats """
    if dataFrame is None:
        return

    from ccpn.util.Path import aPath

    path = aPath(path)
    saveDialog = TablesFileDialog(parent=None, acceptMode='save', selectFile=path, directory=path.parent,
                                  fileFilter=".xlsx;; .csv;; .tsv;; .json ")
    saveDialog._show()

    path = saveDialog.selectedFile()
    filterType = saveDialog.selectedNameFilter()
    if path:
        findExportFormats(path, dataFrame, filterType=filterType, columns=columns)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# GUI Convenient (Private) Functions
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def _selectRowsOnTable(table, values=[], rows=None, doCallback=False, scrollToSelection=True):
    """ccpn internal """
    model = table.model()
    selectionModel = table.selectionModel()
    selectionModel.clearSelection()
    rows = rows or []
    for value in values:
        for i in table.items:
            try:
                if i.text() == value:
                    row = i.row()
                    rows.append(row)
            except Exception as e:
                getLogger().debug('Error in selecting a table row. %s' % e)
                return
    rows = list(set(rows))
    if len(rows) > 0:
        rows.sort(key=lambda c: int(c))
        rowIndex = model.index(rows[0], 0)
        table.setCurrentIndex(rowIndex)
        for row in rows[1:]:
            rowIndex = model.index(row, 0)
            selectionModel.select(rowIndex, selectionModel.Select | selectionModel.Rows)
        if scrollToSelection and not table._scrollOverride:
            table.scrollToSelectedIndex()
        if doCallback:
            table._selectionTableCallback(None)


def _colourTableByValue(table, values, removeValueFromTable=True):
    """ccpn internal """
    # values = {'pid': 'colourCode'}
    for value in values:
        try:
            for i in table.items:
                if i.text() == value:
                    if removeValueFromTable:
                        i.setValue('')
                    colour = QtGui.QColor(value)
                    i.setBackground(colour)
        except Exception as e:
            getLogger().debug('Error setting colour on table row. %s' % e)

def _oneLiner(theString):
    """ Remove returns from string. E.g. the one in column Headers"""
    return theString.replace("\n", " ")


def _makeTipText(columName, tipText):
    """Make a TipText by joining Column name and tipText to same string """
    return f'{_oneLiner(columName)}\n{tipText}'


def _getHiddenColumns(table):
    hidden =[]
    for i in table._columnsDefs:
        if table._columnsDefs[i].get(HIDDEN):
            hidden.append(i)
    return hidden


def _resizeColumnWidths(table):
    columnsWidths = {}
    for i in table._columnsDefs:
        columnsWidths.update({i: table._columnsDefs[i].get(WIDTH)})
    table._setColumnWidths(columnsWidths)


class GuiTable(TableWidget, Base):
    _tableSelectionChanged = QtCore.pyqtSignal(list)

    ICON_FILE = os.path.join(os.path.dirname(__file__), 'icons', 'editable.png')

    styleSheet = """GuiTable {
                        background-color: %(GUITABLE_BACKGROUND)s;
                        alternate-background-color: %(GUITABLE_ALT_BACKGROUND)s;
                        border: 2px solid %(BORDER_NOFOCUS)s;
                        border-radius: 2px;
                    }
                    GuiTable::focus {
                        background-color: %(GUITABLE_BACKGROUND)s;
                        alternate-background-color: %(GUITABLE_ALT_BACKGROUND)s;
                        border: 2px solid %(BORDER_FOCUS)s;
                        border-radius: 2px;
                    }
                    GuiTable::item {
                        padding: 2px;
                        color: %(GUITABLE_ITEM_FOREGROUND)s;
                    }
                    GuiTable::item::selected {
                        background-color: %(GUITABLE_SELECTED_BACKGROUND)s;
                        color: %(GUITABLE_SELECTED_FOREGROUND)s;
                    }
                    """

    # define the class for the table widget items
    ITEMKLASS = CcpnTableWidgetItem
    MERGECOLUMN = 0
    PIDCOLUMN = 0
    EXPANDERCOLUMN = 0
    SPANCOLUMNS = ()
    MINSORTCOLUMN = 0
    enableMultiColumnSort = False
    applySortToGroups = False

    PRIMARYCOLUMN = 'Pid'

    _internalColumns = [DATAFRAME_ISDELETED, DATAFRAME_OBJECT]  # columns that are always hidden.
    _hiddenColumns = []

    def __init__(self, parent=None,
                 mainWindow=None,
                 dataFrameObject=None,  # collate into a single object that can be changed quickly
                 actionCallback=None, selectionCallback=None, checkBoxCallback=None,
                 _pulldownKwds=None, enableMouseMoveEvent=True,
                 allowRowDragAndDrop=False,
                 multiSelect=False, selectRows=True, numberRows=False, autoResize=False,
                 enableExport=True, enableDelete=True, enableSearch=True,
                 hideIndex=True, stretchLastSection=True,
                 **kwds):
        """
        Create a new instance of a TableWidget with an attached Pandas dataFrame
        :param parent:
        :param mainWindow:
        :param dataFrameObject:
        :param actionCallback:
        :param selectionCallback:
        :param multiSelect:
        :param selectRows:
        :param numberRows:
        :param autoResize:
        :param enableExport:
        :param enableDelete:
        :param hideIndex:
        :param kwds:
        """
        super().__init__(parent)
        Base._init(self, **kwds)

        self.itemClass = self.ITEMKLASS

        self._parent = parent

        # set the application specific links
        self.mainWindow = mainWindow
        self.application = None
        self.project = None
        self.current = None

        if self.mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
            self.setCurrent()
        self.moduleParent = None

        # initialise the internal data storage
        self._dataFrameObject = dataFrameObject
        self._tableBlockingLevel = 0

        # set stylesheet
        self.colours = getColours()
        self._defaultStyleSheet = self.styleSheet % self.colours
        self.setStyleSheet(self._defaultStyleSheet)
        self.setAlternatingRowColors(True)

        # set the preferred scrolling behaviour
        self.setHorizontalScrollMode(self.ScrollPerPixel)
        self.setVerticalScrollMode(self.ScrollPerItem)

        # define the multiselection behaviour
        self.multiSelect = multiSelect
        if multiSelect:
            self.setSelectionMode(self.ExtendedSelection)
        else:
            self.setSelectionMode(self.SingleSelection)

        # define the set selection behaviour
        self.selectRows = selectRows
        if selectRows:
            self.setSelectionBehavior(self.SelectRows)
        else:
            self.setSelectionBehavior(self.SelectItems)

        self._checkBoxCallback = checkBoxCallback
        # set all the elements to the same size
        self._pulldownKwds = _pulldownKwds or {}
        self.hideIndex = hideIndex
        self._setDefaultRowHeight()

        # enable sorting and sort on the first column
        self.setSortingEnabled(True)
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)

        # enable drag and drop operations on the table
        self.allowRowDragAndDrop = allowRowDragAndDrop
        self.setDragEnabled(self.allowRowDragAndDrop)
        self.setAcceptDrops(self.allowRowDragAndDrop)
        self.viewport().setAcceptDrops(self.allowRowDragAndDrop)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(self.allowRowDragAndDrop)
        self._seenTables = set()

        # stretchLastSection = False

        _header = self.horizontalHeader()
        # set Interactive and last column to expanding
        _header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        _header.setStretchLastSection(stretchLastSection)
        # only look at visible section
        _header.setResizeContentsPrecision(0)
        _header.setDefaultAlignment(QtCore.Qt.AlignLeft)
        _header.setMinimumSectionSize(20)
        # self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustIgnored)
        # _header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        # enable the right click menu
        self.searchWidget = None
        self._setHeaderContextMenu()
        self._enableExport = enableExport
        self._enableDelete = enableDelete
        self._setContextMenu()
        self._enableSearch = enableSearch
        self._rightClickedTableItem = None  # last selected item in a table before raising the context menu. Enabled with mousePress event filter

        # populate if a dataFrame has been passed in
        if dataFrameObject:
            self.setTableFromDataFrame(dataFrameObject.dataFrame)

        # enable callbacks
        self._actionCallback = actionCallback
        self._selectionCallback = selectionCallback
        self._lastSelection = (None,)
        #self._silenceCallback = False

        if self._actionCallback:
            self.doubleClicked.connect(self._doubleClickCallback)
        else:
            self.doubleClicked.connect(self._defaultDoubleClick)

        # set the delegate for editing
        delegate = GuiTableDelegate(self)
        self.setItemDelegate(delegate)

        # set internal flags
        self._mousePressedPos = None
        self._userKeyPressed = False
        self._selectOverride = False
        self._scrollOverride = False

        self._lastClick = None
        self._tableData = {}
        self._rawData = None  # this is set when called setData()
        self._tableNotifier = None
        self._rowNotifier = None
        self._cellNotifiers = []
        self._selectCurrentNotifier = None
        self._searchNotifier = None
        self._droppedNotifier = None
        self._icons = [self.ICON_FILE]
        self._stretchLastSection = stretchLastSection
        self._defaultHeadings = []
        self._clickedInTable = False

        # set the minimum size the table can collapse to
        _height = getFontHeight(name=TABLEFONT, size='VLARGE')
        self.setMinimumSize(2 * _height, _height + self.horizontalScrollBar().height())
        self.searchWidget = None

        self.setDefaultTableData()

        self._currentSorted = False
        self._newSorted = False

        _header.setHighlightSections(self.font().bold())
        setWidgetFont(self, name=TABLEFONT)
        setWidgetFont(_header, name=TABLEFONT)
        setWidgetFont(self.verticalHeader(), name=TABLEFONT)

        selectionModel = self.selectionModel()
        selectionModel.selectionChanged.connect(self._tableSelectionChangedCallback)

        self._lastMouseItem = None
        self._mousePressed = False
        self._lastTimeClicked = time_ns()
        self._clickInterval = QtWidgets.QApplication.instance().doubleClickInterval() * 1e6
        self._tableSelectionBlockingLevel = 0
        self._currentRow = None

        self.itemSelectionChanged.connect(self._itemSelectionChanged)

        self._downIcon = Icon('icons/caret-grey-down')
        self._rightIcon = Icon('icons/caret-grey-right')

    def _tableSelectionChangedCallback(self, selected, deselected):
        self._tableSelectionChanged.emit(self.getSelectedObjects() or [])

    def _initTableCommonWidgets(self, parent, height=35, setGuiNotifier=None, **kwds):
        """Initialise the common table elements
        """
        # strange, need to do this when using scrollArea, but not a widget
        parent.getLayout().setHorizontalSpacing(0)

        self._widget = ScrollableFrame(parent=parent, scrollBarPolicies=('never', 'never'), **kwds)
        self._widgetScrollArea = self._widget._scrollArea
        self._widgetScrollArea.setStyleSheet('''
                    margin-left : 2px;
                    margin-right : 2px;''')

    def _postInitTableCommonWidgets(self):
        from ccpn.ui.gui.widgets.DropBase import DropBase
        from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier
        from ccpn.ui.gui.widgets.ScrollBarVisibilityWatcher import ScrollBarVisibilityWatcher

        # add a dropped notifier to all tables
        if self.moduleParent is not None:
            # set the dropEvent to the mainWidget of the module, otherwise the event gets stolen by Frames
            self.moduleParent.mainWidget._dropEventCallback = self._processDroppedItems

        self._droppedNotifier = GuiNotifier(self,
                                           [GuiNotifier.DROPEVENT], [DropBase.PIDS],
                                           self._processDroppedItems)

        # add a widget handler to give a clean corner widget for the scroll area
        self._cornerDisplay = ScrollBarVisibilityWatcher(self)

        try:
            # may refactor the remaining modules so this isn't needed
            self._widgetScrollArea.setFixedHeight(self._widgetScrollArea.sizeHint().height())
        except:
            getLogger().debug2(f'{self.__class__.__name__} has no _widgetScrollArea')

    def _blockTableEvents(self, blanking=True, _disableScroll=False, _widgetState=None):
        """Block all updates/signals/notifiers in the table.
        """
        # block on first entry
        if self._tableBlockingLevel == 0:
            if _disableScroll:
                self._scrollOverride = True

            # use the Qt widget to block signals - selectionModel must also be blocked
            _widgetState.modelBlocker = QtCore.QSignalBlocker(self.selectionModel())
            _widgetState.rootBlocker = QtCore.QSignalBlocker(self)
            # _widgetState.enabledState = self.updatesEnabled()
            # self.setUpdatesEnabled(False)

            if blanking and self.project:
                if self.project:
                    self.project.blankNotification()

        self._tableBlockingLevel += 1

    def _unblockTableEvents(self, blanking=True, _disableScroll=False, _widgetState=None):
        """Unblock all updates/signals/notifiers in the table.
        """
        if self._tableBlockingLevel > 0:
            self._tableBlockingLevel -= 1

            # unblock all signals on last exit
            if self._tableBlockingLevel == 0:
                if blanking and self.project:
                    if self.project:
                        self.project.unblankNotification()

                _widgetState.modelBlocker = None
                _widgetState.rootBlocker = None
                # self.setUpdatesEnabled(_widgetState.enabledState)
                # _widgetState.enabledState = None

                if _disableScroll:
                    self._scrollOverride = False

                self.update()
        else:
            raise RuntimeError('Error: tableBlockingLevel already at 0')

    @contextmanager
    def _tableBlockSignals(self, callerId='', blanking=True, _disableScroll=False):
        """Block all signals from the table
        """
        _widgetState = AttrDict()
        self._blockTableEvents(blanking, _disableScroll=_disableScroll, _widgetState=_widgetState)
        try:
            yield  # yield control to the calling process

        except Exception as es:
            raise es
        finally:
            self._unblockTableEvents(blanking, _disableScroll=_disableScroll, _widgetState=_widgetState)

    @staticmethod
    def _getCommentText(obj):
        """
        CCPN-INTERNAL: Get a comment from GuiTable
        """
        try:
            if obj.comment == '' or not obj.comment:
                return ''
            else:
                return obj.comment
        except:
            return ''

    @staticmethod
    def _setComment(obj, value):
        """
        CCPN-INTERNAL: Insert a comment into object
        """
        obj.comment = value if value else None

    @staticmethod
    def _getAnnotation(obj):
        """
        CCPN-INTERNAL: Get an annotation from GuiTable
        """
        try:
            if obj.annotation == '' or not obj.annotation:
                return ''
            else:
                return obj.annotation
        except:
            return ''

    @staticmethod
    def _setAnnotation(obj, value):
        """
        CCPN-INTERNAL: Insert an annotation into object
        """
        obj.annotation = value if value else None

    @staticmethod
    def _setClusterId(obj, value):
        """
        CCPN-INTERNAL: Set clusterId from table
        Must be a positive integer
        """
        try:
            v = int(value)
            obj.clusterId = v
        except Exception as err:
            getLogger().warning('Could not set clusterID.', err)

    def setActionCallback(self, actionCallback):
        # enable callbacks
        self._actionCallback = actionCallback

        for act in [self._doubleClickCallback, self._defaultDoubleClick]:
            try:
                self.doubleClicked.disconnect(act)
            except Exception:
                getLogger().debug2('nothing to disconnect')

        if self._actionCallback:
            self.doubleClicked.connect(self._doubleClickCallback)
        else:
            self.doubleClicked.connect(self._defaultDoubleClick)

    def setSelectionCallback(self, selectionCallback):
        # enable callbacks
        self._selectionCallback = selectionCallback

    def setCheckBoxCallback(self, checkBoxCallback):
        # enable callback on the checkboxes
        self._checkBoxCallback = checkBoxCallback

    def _handleDroppedItems(self, pids, objType, pulldown):
        """
        :param pids: the selected objects pids
        :param objType: the instance of the obj to handle. Eg. PeakList
        :param pulldown: the pulldown of the module wich updates the table
        :return: Actions: Select the dropped item on the table or/and open a new modules if multiple drops.
        If multiple different obj instances, then asks first.
        """
        from ccpn.ui.gui.lib.MenuActions import _openItemObject

        objs = [self.project.getByPid(pid) for pid in pids]

        selectableObjects = [obj for obj in objs if isinstance(obj, objType)]
        others = [obj for obj in objs if not isinstance(obj, objType)]
        if len(selectableObjects) > 0:
            _openItemObject(self.mainWindow, selectableObjects[1:])
            pulldown.select(selectableObjects[0].pid)

        else:
            from ccpn.ui.gui.widgets.MessageDialog import showYesNo

            othersClassNames = list(set([obj.className for obj in others if hasattr(obj, 'className')]))
            if len(othersClassNames) > 0:
                if len(othersClassNames) == 1:
                    title, msg = 'Dropped wrong item.', 'Do you want to open the %s in a new module?' % ''.join(othersClassNames)
                else:
                    title, msg = 'Dropped wrong items.', 'Do you want to open items in new modules?'
                openNew = showYesNo(title, msg)
                if openNew:
                    _openItemObject(self.mainWindow, others)

    # def dropEvent(self, event):
    #     print('~~~ dropped. ', event)

    def _checkBoxCallback(self, data):
        getLogger().info('>>> %s _checkBoxCallback' % _moduleId(self.moduleParent))

        pass

    def _defaultDoubleClick(self, itemSelection):

        self._lastClick = 'doubleClick'
        model = self.selectionModel()

        # selects all the items in the row
        selection = model.selectedIndexes()

        if selection:
            row = itemSelection.row()
            col = itemSelection.column()
            if self._dataFrameObject:
                if self._dataFrameObject.columnDefinitions.setEditValues[col]:  # ejb - editable fields don't actionCallback:

                    item = self.item(row, col)
                    item.setEditable(True)
                    # self.itemDelegate().closeEditor.connect(partial(self._changeMe, row, col))
                    # item.textChanged.connect(partial(self._changeMe, item))
                    # self.editItem(item)

    def _doubleClickCallback(self, itemSelection):

        # if not a _dataFrameObject is a normal guiTable.
        if not self._dataFrameObject:
            item = self.currentItem()
            if item is not None:
                data = CallBack(value=item.value,
                                theObject=None,
                                object=None,
                                index=item.index,
                                targetName=None,
                                trigger=CallBack.CLICK,
                                row=item.row(),
                                col=item.column(),
                                rowItem=item)
                self._actionCallback(data)
            return

        self._lastClick = 'doubleClick'
        with self._tableBlockSignals('_doubleClickCallback', blanking=False, _disableScroll=True):

            item = self.currentItem()

            # get the current selected objects from the table - objects now persistent after single-click
            objList = []
            if self._lastSelection is not None:
                objList = self._lastSelection  #['selection']
            # objList = self.getSelectedObjects()

            if item:
                row = item.row()
                col = item.column()

                # get the row data corresponding to the row clicked
                model = self.selectionModel()
                selection = [iSelect for iSelect in model.selectedIndexes() if iSelect.row() == row]
                obj = self.getSelectedObjects(selection)
                obj = obj[0] if obj else None

                # if objList:
                #     # return the highlight to the previous selection
                #     self._highLightObjs(objList)

                if obj is not None and objList:
                    # store the data for the clicked row
                    data = {}
                    for cc in range(self.columnCount()):
                        colName = self.horizontalHeaderItem(cc).text()
                        data[colName] = self.item(row, cc).value
                    targetName = None
                    if hasattr(obj, 'className'):
                        targetName = obj.className

                    objIndex = item.index
                    data = CallBack(theObject=self._dataFrameObject,
                                    object=objList if self.multiSelect else obj,  # single object or multi-selection
                                    index=objIndex,
                                    targetName=targetName,
                                    trigger=CallBack.DOUBLECLICK,
                                    row=row,
                                    col=col,
                                    rowItem=data,
                                    rowObject=obj)

                    if self._actionCallback and self._dataFrameObject and not \
                            self._dataFrameObject.columnDefinitions.setEditValues[col]:  # ejb - editable fields don't actionCallback
                        self._actionCallback(data)

                    elif self._dataFrameObject and self._dataFrameObject.columnDefinitions.setEditValues[col]:  # ejb - editable fields don't actionCallback:
                        # item = self.item(row, col)
                        # item.setEditable(True)
                        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
                        # self.itemDelegate().closeEditor.connect(partial(self._changeMe, row, col))
                        # item.textChanged.connect(partial(self._changeMe, item))
                        # self.editItem(item)  # enter the editing mode

                        # editItem entry is handled by the delegate
                    else:
                        if self._actionCallback:
                            self._actionCallback(data)

    @_defersort
    def setRow(self, row, vals):
        if row > self.rowCount() - 1:
            self.setRowCount(row + 1)
        for col in range(len(vals)):
            val = vals[col]
            item = self.itemClass(val, row)
            item.setEditable(self.editable)
            item.setDraggable(self.allowRowDragAndDrop)
            sortMode = self.sortModes.get(col, None)
            if sortMode is not None:
                item.setSortMode(sortMode)
            format = self._formats.get(col, self._formats[None])
            item.setFormat(format)
            self.items.append(item)

            # item.setValue(val)  # Required--the text-change callback is invoked
            # when we call setItem.
            if isinstance(val, bool):  # this will create a check box if the value is a bool
                item.setCheckable(True)  # Very important: Set Flag so that user cannot check/uncheck directly the checkbox otherwise there are two parallel callbacks.
                # TODO Make sure it works with more testing. The checkbox state is set automatically from the data.
                state = 2 if val else 0
                item.setCheckState(state)
                self.setItem(row, col, item)
                item.setValue('')  # errors in getting this in sync with bools or any value
                item._format = bool

            elif isinstance(val, list or tuple):

                pulldown = PulldownList(None, **self._pulldownKwds)
                pulldown.setMaximumWidth(300)
                pulldown.setData(*val)

                pulldown.setObjectName(str((row, col)))
                pulldown.item = item
                model = self.selectionModel()
                # selects all the items in the row
                selection = model.selectedIndexes()

                self.setCellWidget(row, col, pulldown)
                self.setItem(row, col, item)
                item.setValue('')  # values are in the pulldown. Otherwise they are inserted inside the cell as str in a long list

            elif isinstance(val, Icon) and val in (self._downIcon, self._rightIcon):

                # add a RowExpander widget to the cell - requires setting up after sorting the table
                _expander = RowExpander(self, item)
                self.setCellWidget(row, col, _expander)
                self.setItem(row, col, item)
                item.setValue('')

            elif isinstance(val, RowExpander):

                # add a RowExpander widget to the cell - requires setting up after sorting the table
                # need to update the rowExpander parent
                self.setCellWidget(row, col, val)
                val._tableItem = item
                self.setItem(row, col, item)
                item.setValue('')

            else:
                self.setItem(row, col, item)
                item.setValue(val)

    def _expandCell(self, itemWidget, item):
        _itemRow = item.row()
        row = itemWidget._activeRow
        span = self.rowSpan(_itemRow, 0)  # 0)
        if row is None:
            return

        if span > 1:
            # a group of rows
            if self.isRowHidden(row + 1):  # (row + 1)
                _hidden = False
                itemWidget.setPixmap(self._downIcon.pixmap(12, 12))
            else:
                _hidden = True
                itemWidget.setPixmap(self._rightIcon.pixmap(12, 12))

            for rr in range(row + 1, row + span):
                # for rr in range(row - span + 2, row + 1):
                self.setRowHidden(rr, _hidden)

    def _selectionTableCallback(self, itemSelection, mouseDrag=True):
        """Handler when selection has changed on the table
        This user changed only
        """
        # if not a _dataFrameObject is a normal guiTable.
        if not self._dataFrameObject:
            item = self.currentItem()
            if item is not None and self._selectionCallback:
                data = CallBack(value=item.value,
                                theObject=None,
                                object=None,
                                index=item.index,
                                targetName=None,
                                trigger=CallBack.CLICK,
                                row=item.row(),
                                col=item.column(),
                                rowItem=item)

                delta = time_ns() - self._tableSelectionBlockingLevel
                # if interval large enough then reset timer and return True
                if delta > self._clickInterval:
                    self._selectionCallback(data)
            return

        objList = self.getSelectedObjects()
        if objList and isinstance(objList[0], pd.Series):
            pass
        else:
            if self._clickedInTable:
                if not objList:
                    return
                if set(objList or []) == set(self._lastSelection or []):  # pd.Series should never reach here or will crash here. Cannot use set([series])== because Series are mutable, thus they cannot be hashed
                    return

        self._lastSelection = objList

        with self._tableBlockSignals('_selectionTableCallback', blanking=False, _disableScroll=True):

            # get whether current row is defined
            item = self.currentItem()
            targetName = ''

            # if objList is not None:
            if objList and len(objList) > 0 and hasattr(objList[0], 'className'):
                targetName = objList[0].className

            if item and self._selectionCallback:
                data = CallBack(theObject=self._dataFrameObject,
                                object=objList,
                                index=0,
                                targetName=targetName,
                                trigger=CallBack.CLICK,
                                row=0,
                                col=0,
                                rowItem=None)

                delta = time_ns() - self._tableSelectionBlockingLevel
                # if interval large enough then reset timer and return True
                if delta > self._clickInterval:
                    self._selectionCallback(data)

    def _checkBoxTableCallback(self, itemSelection):

        state = True if itemSelection.checkState() == 2 else False
        state = not state  # as to be opposite before catches the event before you clicked
        selection = [self.model().index(itemSelection.row(), cc) for cc in range(self.columnCount())]

        obj = self.getSelectedObjects(selection)
        obj = obj[0] if obj else None
        targetName = None
        if hasattr(obj, 'className'):
            targetName = obj.className
        if obj is not None:
            data = CallBack(theObject=self._dataFrameObject,
                            object=obj,
                            index=0,
                            targetName=targetName,
                            trigger=CallBack.CLICK,
                            row=itemSelection.row(),
                            col=itemSelection.column(),
                            rowItem=itemSelection,
                            checked=state)
            textHeader = self.horizontalHeaderItem(itemSelection.column()).text()
            if textHeader:
                if not isinstance(obj, pd.Series):
                    self._dataFrameObject.setObjAttr(textHeader, obj, state)

        else:
            data = CallBack(theObject=self._dataFrameObject,
                            object=None,
                            index=0,
                            targetName=None,
                            trigger=CallBack.CLICK,
                            row=itemSelection.row(),
                            col=itemSelection.column(),
                            rowItem=itemSelection,
                            checked=state)
        if self._checkBoxCallback:
            self._checkBoxCallback(data)

    def getHiddenColumns(self):
        """
        get a list of currently hidden columns
        """
        hiddenColumns = self._hiddenColumns
        ll = list(set(hiddenColumns))
        return [x for x in ll if x in self.columnTexts]

    def setHiddenColumns(self, texts, update=True):
        """
        set a list of columns headers to be hidden from the table.
        """
        ll = [x for x in texts if x in self.columnTexts and x not in self._internalColumns]
        self._hiddenColumns = ll
        if update:
            self.showColumns(self._dataFrameObject)

    def hideDefaultColumns(self):
        """If the table is empty then check visible headers against the last header hidden list
        """
        for i, columnName in enumerate(self.columnTexts):
            # remember to hide the special column
            if columnName in self._internalColumns:
                self.hideColumn(i)

    @property
    def columns(self):
        """
        return a list of column objs.
        """
        if self._dataFrameObject:
            return self._dataFrameObject.columnDefinitions.columns
        else:
            return [self.horizontalHeaderItem(i) for i in range(self.columnCount())]

    @property
    def columnTexts(self):
        """
        return a list of column texts.
        """
        if self._dataFrameObject:
            return self._dataFrameObject.headings
        else:
            return [self.horizontalHeaderItem(i).text() for i in range(self.columnCount())]

    @property
    def columnDefinitions(self):
        """
        return a ccpn ColumnClass obj if _dataFrameObject is set.
        """
        if self._dataFrameObject:
            return self._dataFrameObject.columnDefinitions
        else:
            return None

    def showColumns(self, dataFrameObject):
        # show the columns in the list
        hiddenColumns = self.getHiddenColumns()

        for i, colName in enumerate(self.columnTexts):
            # always hide the internal columns
            if colName in (hiddenColumns + self._internalColumns):
                self._hideColumn(colName)
            else:
                self._showColumn(colName)

                if self.columnDefinitions and self.columnDefinitions.setEditValues[i]:
                    # need to put it into the header
                    header = self.horizontalHeaderItem(i)
                    if header:
                        icon = QtGui.QIcon(self._icons[0])
                        header.setIcon(icon)

    def _showColumn(self, name):
        if name not in self.columnTexts:
            return
        if name in self._hiddenColumns:
            self._hiddenColumns.remove(name)
        i = self.columnTexts.index(name)
        self.showColumn(i)

    def _hideColumn(self, name):
        if name not in self.columnTexts:
            return
        if name not in (self._hiddenColumns + self._internalColumns):
            self._hiddenColumns.append(name)
        i = self.columnTexts.index(name)
        self.hideColumn(i)

    def _setDefaultRowHeight(self):
        # set a minimum height to the rows based on the fontMetrics of a generic character
        self.fontMetric = QtGui.QFontMetricsF(self.font())
        self.bbox = self.fontMetric.boundingRect
        rowHeight = self.bbox('A').height() + 8

        headers = self.verticalHeader()
        headers.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        headers.setDefaultSectionSize(int(rowHeight))

        # and hide the row labels
        if self.hideIndex:
            headers.hide()

    def _setColumnWidths(self, columnsWidths):
        """
        Set the columns widths based on the columnHeader name
        :param columnsWidths: Dict  {ColumnName:width}
        :return: None
        """
        for i, column in enumerate(self.columns):
            width = columnsWidths.get(column.headerText)
            if width is not None:
                self.setColumnWidth(i, width)

    def pressingModifiers(self):
        """Is the user clicking while holding a modifier
        """
        allKeyModifers = [QtCore.Qt.ShiftModifier, QtCore.Qt.ControlModifier, QtCore.Qt.AltModifier, QtCore.Qt.MetaModifier]
        keyMod = QtWidgets.QApplication.keyboardModifiers()

        return keyMod in allKeyModifers

    def keyPressEvent(self, event):
        """Handle keyPress events on the table
        """
        super().keyPressEvent(event)

        cursors = [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down, QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]
        enter = [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]
        allKeyModifers = [QtCore.Qt.ShiftModifier, QtCore.Qt.ControlModifier, QtCore.Qt.AltModifier, QtCore.Qt.MetaModifier]

        # for MacOS ControlModifier is 'cmd' and MetaModifier is 'ctrl'
        addSelectionMod = [QtCore.Qt.ControlModifier]

        key = event.key()
        if key in enter:

            # enter/return pressed - select/deselect current item
            keyMod = QtWidgets.QApplication.keyboardModifiers()

            if keyMod in addSelectionMod:
                item = self.currentItem()
                if item:
                    # set the item, which toggles selection of the row
                    self.setCurrentItem(item)

            elif keyMod not in allKeyModifers:
                # fire the action callback (double-click on selected)
                if self._actionCallback:
                    self._doubleClickCallback(self.currentItem())
                else:
                    self._defaultDoubleClick(self.currentItem())

    ####################################################################################################################
    ######################################       Drop Events         ###################################################
    ####################################################################################################################

    def enterEvent(self, event):
        self.setStyleSheet(self._defaultStyleSheet)
        try:
            if not getBlockingDialogs('guiTable enter-event'):
                # basic tables may not have preferences defined
                if self.mainWindow:
                    if self.mainWindow.application.preferences.general.focusFollowsMouse:
                        self.setFocus()
        except:
            pass

        finally:
            super(GuiTable, self).enterEvent(event)

    def _clearTableOverlays(self):
        # make sure to remove border highlights from seen tables.
        _seenTables = self._seenTables.copy()
        for seenTable in _seenTables:
            seenTable.setStyleSheet(seenTable._defaultStyleSheet)
            self._seenTables.remove(seenTable)

    def leaveEvent(self, event):
        self.setStyleSheet(self._defaultStyleSheet)
        super(GuiTable, self).leaveEvent(event)

    def dragMoveEvent(self, event):
        data = self.parseEvent(event)
        source = data.get('source')
        data.update(self._getDraggedDataDict(source))
        if self._dragMoveEventCallback:
            self._dragMoveEventCallback(data)
        super(GuiTable, self).dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self._clearTableOverlays()
        super(GuiTable, self).dragLeaveEvent(event)

    def dragEnterEvent(self, event):
        data = self.parseEvent(event)
        source = data.get('source')

        if isinstance(source, GuiTable):  # do this to set the overlay border and allow proper clean-up on other events
            if self != source:  # this is the target table. Where we are dropping to.
                if self.allowRowDragAndDrop:
                    source._seenTables.add(self)
                    self._seenTables.add(self)
                    # self._setDraggingStyleSheet(GREEN1)
                else:  # DROP NOT ALLOWED
                    event.ignore()

        data.update(self._getDraggedDataDict(source))  #get the selectedObjects and update the datadict for emitting the callback
        if self._enterEventCallback:
            self._enterEventCallback(data)

        super(GuiTable, self).dragEnterEvent(event)

    def dropEvent(self, event):
        """
        Extension to the dropEvent of DropBase.
        To setup this event in a module/table see the gui.lib.GuiNotifier.GuiNotifier class
        example: module.setGuiNotifier(table, [GuiNotifier.DROPEVENT], [DropBase.PIDS], callback=module.theCallback)
        """
        data = self.parseEvent(event)
        source = data.get('source')
        if source == self:  # DROPPING on same table. Ignore
            self.setStyleSheet(self._defaultStyleSheet)
            event.ignore()
            return
        if source != self:
            self.setStyleSheet(self._defaultStyleSheet)
            source.setStyleSheet(source._defaultStyleSheet)
            draggedDataDict = self._getDraggedDataDict(source)
            data.update(draggedDataDict)
            if self._dropEventCallback is not None:
                self._dropEventCallback(data)
            event.accept()
        super().dropEvent(event)

    def _getDraggedDataDict(self, source):
        dataDict = {}
        pids = []
        dfs = []
        if not hasattr(source, 'getSelectedObjects'):
            getLogger().debug(f'Cannot get selected items from {source}.'
                              ' Object class needs to have implemented a "getSelectedObject" method ')
            return dataDict
        objs = source.getSelectedObjects()
        if objs is None:
            return dataDict
        for obj in objs:
            if isinstance(obj, AbstractWrapperObject):
                pids.append(obj.pid)
            if isinstance(obj, (pd.DataFrame, pd.Series)):
                dfs.append(obj)

        dataDict[DropBase.PIDS] = pids
        dataDict[DropBase.DFS] = dfs
        return dataDict

    def setCurrent(self):
        """Set self to current.guiTable"""
        if self.current is not None:
            self.current.guiTable = self
            self._setCurrentStyleSheet()

    def unsetCurrent(self):
        """Set self to current.guiTable"""
        if self.current is not None:
            self.current.guiTable = None
            self.setStyleSheet(self._defaultStyleSheet)

    def _setCurrentStyleSheet(self):
        styleSheet = """GuiTable {
                            background-color: %(GUITABLE_BACKGROUND)s;
                            alternate-background-color: %(GUITABLE_ALT_BACKGROUND)s;
                            border: 2px solid %(BORDER_FOCUS)s;
                            border-radius: 2px;
                        }
                        GuiTable::focus {
                            background-color: %(GUITABLE_BACKGROUND)s;
                            alternate-background-color: %(GUITABLE_ALT_BACKGROUND)s;
                            border: 2px solid %(BORDER_FOCUS)s;
                            border-radius: 2px;
                        }
                        GuiTable::item {
                            padding: 2px;
                            color: %(GUITABLE_ITEM_FOREGROUND)s;
                        }
                        GuiTable::item::selected {
                            background-color: %(GUITABLE_SELECTED_BACKGROUND)s;
                            color: %(GUITABLE_SELECTED_FOREGROUND)s;
                        }
                        """
        self.setStyleSheet(styleSheet % getColours())

    def _setDraggingStyleSheet(self):
        """Set the focus/noFocus colours for the widget
        """
        styleSheet = """GuiTable {
                            background-color: %(GUITABLE_BACKGROUND)s;
                            alternate-background-color: %(GUITABLE_ALT_BACKGROUND)s;
                            border: 2px solid %(BORDER_NOFOCUS)s;
                            border-radius: 2px;
                        }
                        GuiTable::focus {
                            background-color: %(GUITABLE_BACKGROUND)s;
                            alternate-background-color: %(GUITABLE_ALT_BACKGROUND)s;
                            border: 2px solid %(BORDER_FOCUS)s;
                            border-radius: 2px;
                        }
                        GuiTable::item {
                            padding: 2px;
                            color: %(GUITABLE_ITEM_FOREGROUND)s;
                        }
                        GuiTable::item::selected {
                            background-color: %(GUITABLE_SELECTED_BACKGROUND)s;
                            color: %(GUITABLE_SELECTED_FOREGROUND)s;
                        }
                        """
        self.setStyleSheet(styleSheet % getColours())

    ####################################################################################################################
    ####################################################################################################################

    def handleItemChanged(self, item):
        # print('itemChanged===>', item)
        # item.itemChanged()
        pass

    def setTimeDelay(self):
        # set a blocking waypoint if required - will disable selectionCallback in the following doubleClick interval
        self._tableSelectionBlockingLevel = time_ns()

    def _checkMousePressAllowed(self):
        """Check whether a mouse click is allowed
        """
        # get delta between now and last mouse click
        _lastTime = self._lastTimeClicked
        _thisTime = time_ns()
        delta = _thisTime - _lastTime

        # if interval large enough then reset timer and return True
        if delta > self._clickInterval:
            self._lastTimeClicked = _thisTime
            return True

    def _itemSelectionChanged(self):
        """Handle item selection as changed in table - call user callback
        Includes checking for clicking below last row
        """
        self._selectionTableCallback(None, mouseDrag=False)

    def _handleCellClicked(self, eventPos):
        """handle a single click event, but ignore double click events,
        with special case for clicking on an already selected item

        The best way is to disable the selection model and then re-enable after a small time interval
        """
        self._selectionTableCallback(None, mouseDrag=False)

    def _setHeaderContextMenu(self):
        """Set up the context menu for the table header
        """
        headers = self.horizontalHeader()
        headers.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        headers.customContextMenuRequested.connect(self._raiseHeaderContextMenu)

    def _getAsDataFrame(self):
        if self._dataFrameObject is not None:
            df = self._dataFrameObject.dataFrame
            return df

    def _getExportDataColums(self):
        if self._dataFrameObject is not None:
            visCol = self._dataFrameObject.visibleColumnHeadings
            return visCol

    def _setContextMenu(self):
        self.tableMenu = Menu('', self, isFloatWidget=True)
        setWidgetFont(self.tableMenu, )
        self.tableMenu.addAction("Copy clicked cell value", self._copySelectedCell)
        if self._enableExport:
            self.tableMenu.addAction("Export Visible Table", partial(self.exportTableDialog, exportAll=False))
            self.tableMenu.addAction("Export All Columns", partial(self.exportTableDialog, exportAll=True))

        self.tableMenu.addSeparator()

        if self._enableDelete:
            self.tableMenu.addAction("Delete Selection", self.deleteObjFromTable)

        # ejb - added these but don't think they are needed
        # self.tableMenu.addAction("Select All", self.selectAllObjects)
        self.tableMenu.addAction("Clear Selection", self._clearSelectionCallback)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._raiseTableContextMenu)

    def _raiseTableContextMenu(self, pos):
        """Create a new menu and popup at cursor position
        """
        pos = QtCore.QPoint(pos.x() + 10, pos.y() + 10)
        self.tableMenu.exec_(self.mapToGlobal(pos))

    def initSearchWidget(self):
        if self._enableSearch and self.searchWidget is None:
            if not attachSearchWidget(self._parent, self):
                getLogger().warning('Filter option not available')

    def hideSearchWidget(self):
        if self.searchWidget is not None:
            self.searchWidget.hide()

    def _raiseHeaderContextMenu(self, pos):

        if not self._dataFrameObject:
            return

        self.initSearchWidget()
        pos = QtCore.QPoint(pos.x(), pos.y() + 10)  #move the popup a bit down. Otherwise can trigger an event if the pointer is just on top the first item

        self.headerContextMenumenu = QtWidgets.QMenu()
        setWidgetFont(self.headerContextMenumenu, )
        columnsSettings = self.headerContextMenumenu.addAction("Column Settings...")
        searchSettings = None
        if self._enableSearch and self.searchWidget is not None:
            searchSettings = self.headerContextMenumenu.addAction("Filter...")
        action = self.headerContextMenumenu.exec_(self.mapToGlobal(pos))

        if action == columnsSettings:
            settingsPopup = ColumnViewSettingsPopup(parent=self._parent, table=self,
                                                    dataFrameObject=self._dataFrameObject,
                                                    hiddenColumns=self.getHiddenColumns(),
                                                    )
            hiddenColumns = settingsPopup.getHiddenColumns()
            self.setHiddenColumns(texts=hiddenColumns, update=False)
            settingsPopup.raise_()
            settingsPopup.exec_()  # exclusive control to the menu and return _hiddencolumns

        if action == searchSettings:
            self.showSearchSettings()

    def showSearchSettings(self):
        """ Display the search frame in the table"""

        self.initSearchWidget()

        if self.searchWidget is not None:
            if not self.searchWidget.isVisible():
                self.searchWidget.show()
            else:
                self.searchWidget.hideSearch()

    def _copySelectedCell(self):
        from ccpn.util.Common import copyToClipboard

        i = self.currentItem()
        if i is not None:
            text = i.text().strip()
            copyToClipboard([text])

    def deleteObjFromTable(self):
        selected = self.getSelectedObjects()
        if selected:
            n = len(selected)

            # make a list of the types of objects to delete
            objNames = OrderedSet()
            for obj in selected:
                if hasattr(obj, 'pid'):
                    objNames.add('%s%s' % (obj.className, '' if n == 1 else 's'))
            objStr = ', '.join(objNames)

            # put into the dialog message
            title = 'Delete Item%s' % ('' if n == 1 else 's')
            if objStr:
                msg = 'Delete %s %s from the project?' % ('' if n == 1 else '%d' % n, objStr)
            else:
                msg = 'Delete %sselected item%s from the project?' % ('' if n == 1 else '%d ' % n, '' if n == 1 else 's')
            if MessageDialog.showYesNo(title, msg):

                with catchExceptions(application=self.application, errorStringTemplate='Error deleting objects from table; "%s"'):
                    if hasattr(selected[0], 'project'):
                        thisProject = selected[0].project

                        with undoBlockWithoutSideBar():
                            # echo [sI.pid for sI in selected])
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

    def refreshTable(self):
        self.setTableFromDataFrameObject(self._dataFrameObject)

    def refreshHeaders(self):
        self.hide()
        #self._silenceCallback = True
        # self.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        self.setHorizontalHeaderLabels(self._dataFrameObject.headings)
        self.showColumns(self._dataFrameObject)
        # self.resizeColumnsToContents()
        # self.horizontalHeader().setStretchLastSection(self._stretchLastSection)
        self.setColumnCount(self._dataFrameObject.numColumns)

        self.show()
        #self._silenceCallback = False
        self.resizeColumnsToContents()

        self.update()

    def setData(self, data):
        """Set the data displayed in the table.
        Allowed formats are:

        * numpy arrays
        * numpy record arrays
        * metaarrays
        * list-of-lists  [[1,2,3], [4,5,6]]
        * dict-of-lists  {'x': [1,2,3], 'y': [4,5,6]}
        * list-of-dicts  [{'x': 1, 'y': 4}, {'x': 2, 'y': 5}, ...]
        * Pandas Dataframes

        """
        if isinstance(data, pd.DataFrame):
            dataFrame = data.transpose()
            data = dataFrame.to_dict(into=OrderedDict)

        self.clear()
        self.appendData(data)
        self._rawData = data

    def setDataFromSearchWidget(self, dataFrame):
        """Set the data for the table from the search widget
        """
        self.setData(dataFrame.values)

    @contextmanager
    def _guiTableUpdate(self, dataFrameObject, resize=True):
        """Context manager to ensure the headers are defined correctly after performing
        table operations
        """
        # keep the original sorting method
        sortOrder = self.horizontalHeader().sortIndicatorOrder()
        sortColumn = self.horizontalHeader().sortIndicatorSection()
        _visible = self.isVisible()

        try:
            self.hide()
            yield

        finally:
            if self._dataFrameObject:
                # needed after setting the column headings
                self.setHorizontalHeaderLabels(dataFrameObject.headings)
                self.showColumns(dataFrameObject)

                # required to make the header visible
                self.setColumnCount(dataFrameObject.numColumns)
                self._reindexTableObjects()

                # re-sort the table
                if sortColumn < self.columnCount():
                    self.sortByColumn(sortColumn, sortOrder)

                # clear the dummy row
                if dataFrameObject.dataFrame.empty:
                    self.setRowCount(0)
            elif self._rawData:
                if sortColumn < self.columnCount():
                    self.sortByColumn(sortColumn, sortOrder)


            else:
                # usually called when clicking on a table header when an empty table
                self.hideDefaultColumns()
                self.setHiddenColumns(self._hiddenColumns)
                self.setRowCount(0)

            # resize the columns if required (true by default)
            if resize:
                # self.horizontalHeader().setStretchLastSection(self._stretchLastSection)
                self.resizeColumnsToContents()

            # reshow table, which will ensure column widths are updated
            self.setVisible(_visible)

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
            self.clearSelection()

    def populateTable(self, rowObjects=None, columnDefs=None,
                      selectedObjects=None):
        """Populate the table with a set of objects to highlight, or keep current selection highlighted
        with the first item visible.

        Use selectedObjects = [] to clear the selected items

        :param rowObjects: list of objects to set each row
        """
        self.project.blankNotification()

        # if nothing passed in then keep the current highlighted objects
        objs = selectedObjects if selectedObjects is not None else self.getSelectedObjects()

        try:
            _dataFrameObject = self.getDataFrameFromList(table=self,
                                                         buildList=rowObjects,
                                                         colDefs=columnDefs)

            # populate from the Pandas dataFrame inside the dataFrameObject
            self.setTableFromDataFrameObject(dataFrameObject=_dataFrameObject, columnDefs=columnDefs)

        except Exception as es:
            getLogger().warning('Error populating table', str(es))
            raise es

        finally:
            self._highLightObjs(objs)
            self.project.unblankNotification()

    def setTableFromDataFrameObject(self, dataFrameObject, columnDefs=None):
        """Populate the table from a Pandas dataFrame
        """

        with self._tableBlockSignals('setTableFromDataFrameObject'):

            # get the currently selected objects
            objs = self.getSelectedObjects()

            self._dataFrameObject = dataFrameObject

            with self._guiTableUpdate(dataFrameObject):
                if not dataFrameObject.dataFrame.empty:
                    self.setData(dataFrameObject.dataFrame.values)
                else:
                    # set a dummy row of the correct length
                    self.setData([list(range(len(dataFrameObject.headings)))])

                # store the current headings, in case table is cleared, to stop table jumping
                self._defaultHeadings = dataFrameObject.headings
                self.setHiddenColumns(self.getHiddenColumns())

                if columnDefs:
                    for col, colFormat in enumerate(columnDefs.formats):
                        if colFormat is not None:
                            self.setFormat(colFormat, column=col)

            try:
                # set the tipTexts
                for col, colText in enumerate(columnDefs.tipTexts):
                    _item = self.horizontalHeaderItem(col)
                    if _item:
                        _item.setToolTip(colText)
            except Exception as es:
                # ignore if no tipTexts
                pass

            # highlight them back again
            self._highLightObjs(objs)

        # outside of the with to spawn a repaint
        self.show()

    def _getDataFromFrame(self, table, df, colDefs, columnsMap):
        """
        columnsMap a dictionary, key = the columnName as in the raw dataFrame and value = the columnName
        to show in the new Guitable
        """
        objects = []
        defDict = defaultdict(list)
        newColumns = []
        for rawDFColumnName, newDFcolumnName in columnsMap.items():
            if rawDFColumnName in df.columns:
                theSeries = df[rawDFColumnName]
                defDict[newDFcolumnName] = theSeries
                objects.append(theSeries)
                newColumns.append(newDFcolumnName)
        newDf = pd.DataFrame(defDict, columns=newColumns)
        return DataFrameObject(dataFrame=newDf,
                               objectList=objects or [],
                               columnDefs=colDefs or [],
                               table=table)

    def getDataFromFrame(self, table, df, colDefs, columnsMap=None):
        """
        """
        if columnsMap:
            return self._getDataFromFrame(table, df, colDefs, columnsMap)

        objects = []
        allItems = []
        for index, row in df.iterrows():
            listItem = OrderedDict()
            for header in colDefs.columns:
                listItem[header.headerText] = header.getValue(row)
            allItems.append(listItem)
            objects.append(row)

        return DataFrameObject(dataFrame=pd.DataFrame(allItems, columns=colDefs.headings),
                               objectList=objects or [],
                               columnDefs=colDefs or [],
                               table=table)

    def getDataFrameFromList(self, table=None,
                             buildList=None,
                             colDefs=None):
        """
        Return a Pandas dataFrame from an internal list of objects
        The columns are based on the 'func' functions in the columnDefinitions

        :param buildList:
        :param colDefs:
        :return pandas dataFrameObject:
        """
        allItems = []
        objects = []

        if buildList:
            for col, obj in enumerate(buildList):
                listItem = OrderedDict()
                for header in colDefs.columns:
                    try:
                        listItem[header.headerText] = header.getValue(obj)
                    except Exception as es:
                        # NOTE:ED - catch any nasty surprises in tables
                        getLogger().debug2(f'Error creating table information {es}')
                        listItem[header.headerText] = None

                allItems.append(listItem)
                objects.append(obj)

        return DataFrameObject(dataFrame=pd.DataFrame(allItems, columns=colDefs.headings),
                               objectList=objects or [],
                               columnDefs=colDefs or [],
                               table=table)

    def getDataFrameFromRows(self, table=None,
                             dataFrame=None,
                             colDefs=None):
        """
        Return a Pandas dataFrame from the internal rows of an internal Pandas dataFrame
        The columns are based on the 'func' functions in the columnDefinitions

        :param buildList:
        :param colDefs:
        :return pandas dataFrame:
        """
        allItems = []
        objects = []

        buildList = dataFrame.as_namedtuples()
        for ind, obj in enumerate(buildList):
            listItem = OrderedDict()
            for header in colDefs.columns:
                listItem[header.headerText] = header.getValue(obj)

            allItems.append(listItem)

        return DataFrameObject(dataFrame=pd.DataFrame(allItems, columns=colDefs.headings),
                               objectList=objects,
                               columnDefs=colDefs,
                               table=table)

    def rawDataToDF(self):
        try:
            df = pd.DataFrame(self._rawData)
            return df
        except:
            return pd.DataFrame()

    def tableToDataFrame(self, exportAll=True):
        """Extract the table as a dataframe for later printing
        The actual data values are exported, not the visible items which may be rounded due to the table settings

        :param exportAll: True/False - True implies export whole table - but in visible order
                                    False, export only the visible table
        """
        if not (self._dataFrameObject and self._dataFrameObject.dataFrame is not None):
            if self._rawData:
                return self.rawDataToDF()
            else:
                showWarning('Table to dataFrame', 'Table does not contain a dataFrame')

        else:
            rowList = None
            if exportAll:
                colList = self._dataFrameObject.userHeadings
                rowList = list(self._dataFrameObject.dataFrame.index)

            else:
                colList = self._dataFrameObject.visibleColumnHeadings

                # export contents of dataFrame based on the visible rows and columns
                # if self.searchWidget and self.searchWidget._listRows and self.columnCount():
                #
                #     # retrieve the correct item, checking that it is in the bounds of the table
                #     count = min(len(self.searchWidget._listRows), self.rowCount())
                #     rowList = [list(self.searchWidget._listRows)[self.item(row, 0).index] for row in range(count)]
                # else:

                if self.rowCount() and self.columnCount():
                    rowList = [self.item(row, 0).index for row in range(self.rowCount())]

            return self._tableToDataFrame(self._dataFrameObject.dataFrame, rowList=rowList, colList=colList)

    def _tableToDataFrame(self, dataFrame, rowList=None, colList=None):
        if dataFrame is not None:

            if colList:
                dataFrame = dataFrame[colList]  # returns a new dataFrame
            if rowList:
                dataFrame = dataFrame[:].iloc[rowList]

            return dataFrame

        else:
            if self._rawData is not None:
                try:
                    return pd.DataFrame(self._rawData).transpose()
                except Exception as e:
                    getLogger().warning(e)

    def exportTableDialog(self, exportAll=True):
        """export the contents of the table to a file
        The actual data values are exported, not the visible items which may be rounded due to the table settings

        :param exportAll: True/False - True implies export whole table - but in visible order
                                    False, export only the visible table
        """
        if not (self._dataFrameObject and self._dataFrameObject.dataFrame is not None):
            if self._rawData:
                self._exportTableDialog(self.rawDataToDF())
            else:
                showWarning('Export Table to File', 'Table does not contain a dataFrame')

        else:
            rowList = None
            if exportAll:
                colList = self._dataFrameObject.userHeadings
                rowList = list(self._dataFrameObject.dataFrame.index)

            else:
                colList = self._dataFrameObject.visibleColumnHeadings

                # export contents of dataFrame based on the visible rows and columns
                if self.searchWidget and self.searchWidget._listRows and self.columnCount():

                    # retrieve the correct item, checking that it is in the bounds of the table
                    count = min(len(self.searchWidget._listRows), self.rowCount())
                    rowList = [list(self.searchWidget._listRows)[self.item(row, 0).index] for row in range(count)]
                else:
                    if self.rowCount() and self.columnCount():
                        rowList = [self.item(row, 0).index for row in range(self.rowCount())]

            self._exportTableDialog(self._dataFrameObject.dataFrame, rowList=rowList, colList=colList)

    def _exportTableDialog(self, dataFrame, rowList=None, colList=None):

        self.saveDialog = TablesFileDialog(parent=None, acceptMode='save', selectFile='ccpnTable.xlsx',
                                           fileFilter=".xlsx;; .csv;; .tsv;; .json ")
        self.saveDialog._show()
        path = self.saveDialog.selectedFile()
        if path:
            sheet_name = 'Table'
            if dataFrame is not None:

                if colList:
                    dataFrame = dataFrame[colList]  # returns a new dataFrame
                if rowList:
                    dataFrame = dataFrame[:].iloc[rowList]

                ft = self.saveDialog.selectedNameFilter()

                findExportFormats(path, dataFrame, sheet_name=sheet_name, filterType=ft, columns=colList)

            else:
                if self._rawData is not None:
                    try:
                        df = pd.DataFrame(self._rawData).transpose()
                        findExportFormats(path, df, sheet_name=sheet_name)

                        # df.to_excel(path, sheet_name=sheet_name)
                    except Exception as e:
                        getLogger().warning(e)

    def scrollToSelectedIndex(self):
        h = self.horizontalHeader()
        for i in range(h.count()):
            if not h.isSectionHidden(i) and h.sectionViewportPosition(i) >= 0:
                if self.getSelectedRows():
                    self.scrollTo(self.model().index(self.getSelectedRows()[0], i),
                                  self.EnsureVisible)  # doesn't dance around so much
                    # self.PositionAtCenter)
                    break

    def getSelectedRows(self):

        model = self.selectionModel()

        # selects all the items in the row
        selection = model.selectedRows()
        rows = [i.row() for i in selection]

        return rows

    def mousePressEvent(self, event):
        """handle mouse press events
        Clicking is handled on the mouse release
        """
        if event.button() == QtCore.Qt.RightButton:
            # stops the selection from the table when the right button is clicked
            self._rightClickedTableItem = self.itemAt(event.pos())

        # user can click in the blank area below the last row
        self._clickedInTable = True if self.itemAt(event.pos()) else False
        self.setCurrent()
        super().mousePressEvent(event)

    def getRightMouseItem(self):
        if self._rightClickedTableItem:
            row = self._rightClickedTableItem.row()
            data = {}
            for cc in range(self.columnCount()):
                colName = self.horizontalHeaderItem(cc).text()
                data[colName] = self.item(row, cc).value

            return data

    def getSelectedObjects(self, fromSelection=None):
        """

        :param fromSelection:
        :return: get a list of table objects. If the table has a header called pid, the object is a ccpn Core obj like Peak,
         otherwise is a Pandas series object corresponding to the selected row(s).
        """

        model = self.selectionModel()
        # selects all the items in the row
        selection = fromSelection if fromSelection else model.selectedIndexes()

        if selection:
            selectedObjects = []
            rows = []
            valuesDict = defaultdict(list)
            for iSelect in selection:
                row = iSelect.row()
                col = iSelect.column()
                if self._dataFrameObject:
                    if len(self._dataFrameObject._objects) > 0:
                        if isinstance(self._dataFrameObject._objects[0], pd.Series):
                            _header = self.horizontalHeaderItem(col)
                            if _header:
                                h = _header.text()
                                v = self.item(row, col).text()
                                valuesDict[h].append(v)

                        else:
                            _header = self.horizontalHeaderItem(col)
                            if _header:
                                colName = _header.text()
                                if colName == self.PRIMARYCOLUMN:
                                    if row not in rows:
                                        rows.append(row)
                                        objIndex = model.model().data(iSelect)

                                        # NOTE:ED - fix for now - Pid or _object column?
                                        obj = self.project.getByPid(objIndex.strip('<>'))
                                        if obj:
                                            selectedObjects.append(obj)
            if valuesDict:
                selectedObjects = [row for i, row in pd.DataFrame(valuesDict).iterrows()]

            return selectedObjects
        else:
            return None

    def getFirstObject(self):

        data = {}
        if self._dataFrameObject:
            if len(self._dataFrameObject._objects) > 0:

                for cc in range(self.columnCount()):
                    colName = self.horizontalHeaderItem(cc).text()
                    data[colName] = self.item(0, cc).value

                return data

    def _clearSelectionCallback(self):
        """Callback for the context menu clear;
        For now just a placeholder
        """
        self.clearSelection()

    def clearSelection(self):
        """Clear the current selection in the table
        and remove objects from the current list
        """
        with self._tableBlockSignals('clearSelection'):

            # objList = self.getSelectedObjects()
            selectionModel = self.selectionModel()
            selectionModel.clearSelection()

            # remove from the current list
            multiple = self._tableData['classCallBack']

            if self._dataFrameObject:
                tableObjs = self._dataFrameObject.objects

                if multiple:  # None if no table callback defined
                    multipleAttr = getattr(self.current, multiple)
                    if len(multipleAttr) > 0:
                        # need to remove objList from multipleAttr - fires only one current change
                        setattr(self.current, multiple, tuple(set(multipleAttr) - set(tableObjs)))

            self._lastSelection = [None]
        self._tableSelectionChanged.emit([])

    def selectObjects(self, objList: list, setUpdatesEnabled: bool = False):
        """Select the object in the table
        """
        # skip if the table is empty
        if not self._dataFrameObject:
            return

        with self._tableBlockSignals('selectObjects'):

            selectionModel = self.selectionModel()
            if objList is not None:
                selectionModel.clearSelection()
                for obj in objList:
                    if hasattr(obj, 'pid'):
                        row = self._dataFrameObject.find(self, str(obj.pid))
                        if row is not None:
                            selectionModel.select(self.model().index(row, 0),
                                                  selectionModel.Select | selectionModel.Rows)

                    else:
                        return

    def selectIndex(self, idx, doCallback=True):
        model = self.model()
        selectionModel = self.selectionModel()
        selectionModel.clearSelection()
        rowIndex = model.index(idx, 0)
        self.setCurrentIndex(rowIndex)
        selectionModel.select(rowIndex, selectionModel.Select | selectionModel.Rows)
        if doCallback:
            self._selectionTableCallback(None)

    def _highLightObjs(self, selection, scrollToSelection=True):

        # skip if the table is empty
        if not self._dataFrameObject:
            return

        with self._tableBlockSignals('_highLightObjs'):

            selectionModel = self.selectionModel()
            model = self.model()

            itm = self.currentItem()

            selectionModel.clearSelection()
            if selection:
                if len(selection) > 0:
                    if isinstance(selection[0], pd.Series):
                        # not sure how to handle this
                        return
                uniqObjs = set(selection)

                rows = [self._dataFrameObject.find(self, str(obj.pid)) for obj in uniqObjs if obj in self._dataFrameObject.objects]
                rows = [row for row in rows if row is not None]
                if rows:
                    rows.sort(key=lambda c: int(c))

                    # remember the current cell so that cursor work correctly
                    if itm and itm.row() in rows:
                        self.setCurrentItem(itm)
                        _row = itm.row()
                    else:
                        _row = rows[0]
                        rowIndex = model.index(_row, 0)
                        self.setCurrentIndex(rowIndex)

                    for row in rows:
                        if row != _row:
                            rowIndex = model.index(row, 0)
                            selectionModel.select(rowIndex, selectionModel.Select | selectionModel.Rows)

                    if scrollToSelection and not self._scrollOverride:
                        self.scrollToSelectedIndex()

    def selectLastRow(self):
        selectionModel = self.selectionModel()
        model = self.model()
        rowCount = model.rowCount()
        selectionModel.clearSelection()
        rowIndex = model.index(rowCount - 1, 0)
        selectionModel.select(rowIndex, selectionModel.Select | selectionModel.Rows)
        self.setCurrentIndex(rowIndex)
        self.scrollToSelectedIndex()

    def selectFirstRow(self, doCallback=True):
        self.selectIndex(0, doCallback=doCallback)

    def getSelectedRowAsDataFrame(self):
        values = []
        headers = []
        rowDf = None
        if self.currentRow() is not None:
            for i in range(self.model().columnCount()):
                headers.append(self.horizontalHeaderItem(i).text())
                if self.item(self.currentRow(), i) is not None:
                    values.append(self.item(self.currentRow(), i).text())
                else:
                    return rowDf
            rowDf = pd.DataFrame([values, ], columns=headers)
        return rowDf

    def clearTable(self):
        """remove all objects from the table"""
        with self._tableBlockSignals('clearTable'):
            self.clearTableContents()

    def clearTableContents(self, dataFrameObject=None):
        self.clearContents()
        self.verticalHeadersSet = True
        self.horizontalHeadersSet = True
        self.sortModes = {}

        self._dataFrameObject = dataFrameObject if dataFrameObject else None

        if self._dataFrameObject:
            # there must be something in the table to set the headers against
            self.setData([list(range(self._dataFrameObject.numColumns)), ])

            self.setHorizontalHeaderLabels(self._dataFrameObject.headings)
            self.showColumns(self._dataFrameObject)
            # self.resizeColumnsToContents()
            # self.horizontalHeader().setStretchLastSection(self._stretchLastSection)

            # required to make the header visible
            self.setColumnCount(self._dataFrameObject.numColumns)

        self.setRowCount(0)
        self.items = []

    def getIndexList(self, classItems, attribute):
        """Get the list of objects on which to before the indexing
        To be subclassed as required
        """
        # classItem is usually a type such as PeakList, MultipletList
        # with an attribute such as peaks/peaks

        # this is a step towards making guiTableABC and subclass for each table
        return getattr(classItems, attribute, [])

    def _reindexTableObjects(self):
        """updating to make sure that the index of the item in the table matches the index of the item in the actual list
        """
        # this is for those objects that undo returns back to the table
        # because items are just given the next available 'Index' when re-inserted
        # so need to be corrected - should be done in each rename, change routine
        if self._tableData['tableSelection']:
            tSelect = getattr(self, self._tableData['tableSelection'])
            if tSelect:

                # may need a special getter here
                # e.g. a Multiplet has Multiplet.peaks
                # but may want to list peaks from a list of multiplets, so need a new object
                # currently just error check and skip
                # OR just subclass this routine!

                multiple = self._tableData['classCallBack']
                multipleAttr = self.getIndexList(tSelect, multiple)

                if multipleAttr:
                    # newIndex = [multipleAttr.index(rr) for rr in self._objects]

                    # find the columns containing the objects and the indexing
                    objCol = indCol = None
                    for cc in range(self.columnCount()):
                        _header = self.horizontalHeaderItem(cc)
                        if _header:
                            colName = _header.text()
                            if colName == DATAFRAME_INDEX:
                                indCol = cc
                                # print (DATAFRAME_INDEX, cc)
                            elif colName == DATAFRAME_OBJECT:
                                objCol = cc
                                # print (DATAFRAME_OBJECT, cc)
                    if objCol and indCol:
                        # print ('INDEXING')
                        # print (multipleAttr)
                        for rr in range(self.rowCount()):

                            thisObj = self.item(rr, objCol).value
                            if thisObj in multipleAttr:
                                # this could be slow in some cases - nmrChain.index(nmrResidue)?
                                self.item(rr, indCol).setValue(multipleAttr.index(thisObj))

    def _updateTableCallback(self, data):
        """
        Notifier callback for updating the table
        """

        with self._tableBlockSignals('_updateTableCallback'):

            table = data[Notifier.OBJECT]
            tableSelect = self._tableData['tableSelection']

            currentTable = getattr(self, tableSelect) if tableSelect else None

            if currentTable and currentTable == table:
                trigger = data[Notifier.TRIGGER]

                if trigger == Notifier.RENAME:

                    # keep the original sorting method
                    sortOrder = self.horizontalHeader().sortIndicatorOrder()
                    sortColumn = self.horizontalHeader().sortIndicatorSection()

                    # self.displayTableForNmrTable(table)
                    if self._tableData['changeFunc']:
                        self._tableData['changeFunc'](table)

                    # re-sort the table
                    if sortColumn < self.columnCount():
                        self.sortByColumn(sortColumn, sortOrder)

                    # self.horizontalHeader().setStretchLastSection(self._stretchLastSection)
                    self.resizeColumnsToContents()

        getLogger().debug2('<updateTableCallback>', data['notifier'],
                           tableSelect,
                           data['trigger'], data['object'])

    def _updateRowCallback(self, data):
        """
        Notifier callback for updating the table for change in nmrRows
        :param data:
        """

        with self._tableBlockSignals('_updateRowCallback'):
            row = data[Notifier.OBJECT]

            if not self._dataFrameObject or row is None:
                return
            _update = False

            trigger = data[Notifier.TRIGGER]
            if trigger == Notifier.DELETE:

                # remove item from self._dataFrameObject and table
                if row in self._dataFrameObject._objects:
                    self._dataFrameObject.removeObject(row)
                    _update = True

            elif trigger == Notifier.CREATE:

                # insert item into self._dataFrameObject
                if self._tableData['tableSelection']:
                    tSelect = getattr(self, self._tableData['tableSelection'])
                    if tSelect:

                        # check that the object created is in the list viewed in this table
                        # e.g. row.peakList == tSelect then add - older test
                        # if tSelect == getattr(row, self._tableData['tableName']):

                        # multiple attribute name, i.e. added 's' - and get tSelect.objs
                        multiple = self._tableData['classCallBack']
                        # multipleAttr = getattr(tSelect, multiple)
                        multipleAttr = self.getIndexList(tSelect, multiple)

                        # if item is in the list, then create
                        if row in multipleAttr:
                            # add the row to the dataFrame and table
                            self._dataFrameObject.appendObject(row)
                            _update = True

            elif trigger == Notifier.CHANGE:

                # modify the line in the table
                try:
                    _update = self._dataFrameObject.changeObject(row)

                    # TODO:ED it may not already be in the list - check indexing
                    if not _update and '_calledFromCell' not in data:
                        if self._tableData['tableSelection']:
                            tSelect = getattr(self, self._tableData['tableSelection'])
                            if tSelect:

                                # check that the object created is in the list viewed in this table
                                # e.g. row.peakList == tSelect then add
                                if tSelect == getattr(row, self._tableData['tableName']):
                                    # add the row to the dataFrame and table

                                    # get the array containing the objects displayed in the table
                                    multiple = self._tableData['classCallBack']
                                    # print(tSelect, multiple)
                                    multipleAttr = getattr(tSelect, multiple)

                                    self._dataFrameObject.appendObject(row, multipleAttr=multipleAttr)
                                    _update = True

                    # else:
                    #
                    #     # delete from the table?
                    #     if row in self._dataFrameObject._objects:
                    #         self._dataFrameObject.removeObject(row)
                    #         _update = True

                except Exception as es:
                    getLogger().debug2(f'Error updating row in table   {es}')

            elif trigger == Notifier.RENAME:
                # get the old pid before the rename
                oldPid = data[Notifier.OLDPID]

                if row in self._dataFrameObject._objects:

                    # modify the oldPid in the objectList, change to newPid
                    _update = self._dataFrameObject.renameObject(row, oldPid)

                    # TODO:ED check whether the new object is still in the active list - remove otherwise
                    if self._tableData['tableSelection']:
                        tSelect = getattr(self, self._tableData['tableSelection'])  # eg self.nmrChain
                        if tSelect and not tSelect.isDeleted:  # eg self.nmrChain.nmrResidues
                            objList = getattr(tSelect, self._tableData['rowClass']._pluralLinkName)

                            if objList and row not in objList:
                                # TODO:ED Check current deletion
                                getLogger().debug2('>>> deleting spare object %s' % row, oldPid)
                                self._dataFrameObject.removeObject(row)

                            else:
                                getLogger().debug2('>>> creating spare object %s' % row, oldPid)
                                self._dataFrameObject.appendObject(row)
                        else:
                            self.clearTable()

                        _update = True

        if _update:
            getLogger().debug2('<updateRowCallback>', data['notifier'],
                               self._tableData['tableSelection'],
                               data['trigger'], data['object'])
            _val = self.getSelectedObjects() or []
            self._tableSelectionChanged.emit(_val)

        return _update

    def getCellToRows(self, cellItem, attribute):
        """Get the list of objects which cellItem maps to for this table
        To be subclassed as required
        """
        # classItem is usually a type such as PeakList, MultipletList
        # with an attribute such as peaks/peaks

        # this is a step towards making guiTableABC and subclass for each table
        return getattr(cellItem, attribute, []), Notifier.CHANGE

    def _updateCellCallback(self, attr, data):
        """
        Notifier callback for updating the table
        :param data:
        """
        with self._tableBlockSignals('_updateCellCallback'):
            cellData = data[Notifier.OBJECT]
            # row = getattr(cell, self._tableData['rowName'])
            # cells = getattr(cellData, attr)
            cells = makeIterableList(cellData)

            _update = False
            for cell in cells:
                callbacktypes = self._tableData['cellClassNames']
                rowObj = None
                _triggerType = Notifier.CHANGE
                if isinstance(callbacktypes, list):

                    for cBack in callbacktypes:

                        # check if row is the correct type of class
                        if isinstance(cell, cBack[OBJECT_CLASS]):
                            # rowObj = getattr(cell, cBack[OBJECT_PARENT])
                            rowCallback = cBack[OBJECT_PARENT]
                            rowObj, _triggerType = self.getCellToRows(cell, rowCallback)
                            break
                else:
                    try:
                        rowCallback = callbacktypes[OBJECT_PARENT]
                        rowObj, _triggerType = self.getCellToRows(cell, rowCallback)
                    except Exception as es:
                        pass

                # concatenate the list - will always return a list
                rowObjs = makeIterableList(rowObj)
                # rowObjs = [obj for obj in rowObjs if obj and not obj.isDeleted]

                # update the correct row by calling row handler
                for rowObj in rowObjs:
                    newData = data.copy()
                    newData[Notifier.OBJECT] = rowObj
                    newData[Notifier.TRIGGER] = _triggerType or data[Notifier.TRIGGER]  # Notifier.CHANGE
                    newData['_calledFromCell'] = cell

                    # check whether we are the row object or still a cell object
                    cellType = self._tableData['rowClass']
                    if type(rowObj) is cellType:

                        self._updateRowCallback(newData)

                        if data[Notifier.TRIGGER] == 'rename':
                            #update the original object from getParentfromPartialPid...

                            # find the original parent row object from the oldPid
                            oldPid = data[Notifier.OLDPID]
                            cellParent = getParentObjectFromPid(self.project, oldPid)
                            if cellParent is not rowObj:
                                # if it has changed then update the original row
                                newData[Notifier.OBJECT] = cellParent
                                self._updateRowCallback(newData)

                    else:
                        self._updateCellCallback(rowCallback, newData)

        #self._silenceCallback = False
        getLogger().debug2('<updateCellCallback>', data['notifier'],
                           self._tableData['tableSelection'],
                           data['trigger'], data['object'])

    def _searchCallBack(self, data):
        """
        Callback to populate the search bar with the selected item
        """

        value = getattr(data[CallBack.OBJECT], self._tableData['searchCallBack']._pluralLinkName, None)
        if value and self.searchWidget and self.searchWidget.isVisible():
            self.searchWidget.selectSearchOption(self, self._tableData['searchCallBack'], value[0].id)

    def _selectCurrentCallBack(self, data):
        """
        Callback to handle selection on the table, linked to user defined function
        :param data:
        """
        if not self._tableBlockingLevel and 'selectCurrentCallBack' in self._tableData:
            func = self._tableData['selectCurrentCallBack']
            if func:
                func(data)

    def clearCurrentCallback(self):
        """Clear the callback function for current object/list change
        """
        self._tableData['selectCurrentCallBack'] = None

    def setTableNotifiers(self, tableClass=None, rowClass=None, cellClassNames=None,
                          tableName=None, rowName=None, className=None,
                          changeFunc=None, updateFunc=None,
                          tableSelection=None, pullDownWidget=None,
                          callBackClass=None, selectCurrentCallBack=None,
                          searchCallBack=None, moduleParent=blankId):
        """
        Set a Notifier to call when an object is created/deleted/renamed/changed
        rename calls on name
        change calls on any other attribute

        :param tableClass - class of table object, selected by pulldown:
        :param rowClass - class identified by a row in the table:
        :param cellClassNames - list of tuples (cellClass, cellClassName):
                                class that affects row when changed
        :param tableName - name of attribute for parent name of row:
        :param rowName - name of attribute for parent name of cell:
        :param changeFunc:
        :param updateFunc:
        :param tableSelection:
        :param pullDownWidget:
        :return:
        """
        self._initialiseTableNotifiers()

        if tableClass:
            self._tableNotifier = Notifier(self.project,
                                           [Notifier.CREATE, Notifier.DELETE, Notifier.RENAME],
                                           tableClass.__name__,
                                           self._updateTableCallback,
                                           onceOnly=True)

        if rowClass:
            # 'i-1' residue spawns a rename but the 'i' residue only fires a change
            self._rowNotifier = Notifier(self.project,
                                         [Notifier.CREATE, Notifier.DELETE, Notifier.RENAME, Notifier.CHANGE],
                                         rowClass.__name__,
                                         self._updateRowCallback,
                                         onceOnly=True)  # should be True, but doesn't work

        if isinstance(cellClassNames, list):
            for cellClass in cellClassNames:
                self._cellNotifiers.append(Notifier(self.project,
                                                    [Notifier.CHANGE, Notifier.CREATE, Notifier.DELETE, Notifier.RENAME],
                                                    cellClass[OBJECT_CLASS].__name__,
                                                    partial(self._updateCellCallback, cellClass[OBJECT_PARENT]),
                                                    onceOnly=True))
        else:
            if cellClassNames:
                self._cellNotifiers.append(Notifier(self.project,
                                                    [Notifier.CHANGE, Notifier.CREATE, Notifier.DELETE, Notifier.RENAME],
                                                    cellClassNames[OBJECT_CLASS].__name__,
                                                    partial(self._updateCellCallback, cellClassNames[OBJECT_PARENT]),
                                                    onceOnly=True))

        if selectCurrentCallBack:
            self._selectCurrentNotifier = Notifier(self.current,
                                                   [Notifier.CURRENT],
                                                   callBackClass._pluralLinkName,
                                                   self._selectCurrentCallBack)

        if searchCallBack:
            self._searchNotifier = Notifier(self.current,
                                            [Notifier.CURRENT],
                                            searchCallBack._pluralLinkName,
                                            self._searchCallBack)

        self._tableData = {'updateFunc'           : updateFunc,
                           'changeFunc'           : changeFunc,
                           'tableSelection'       : tableSelection,
                           'pullDownWidget'       : pullDownWidget,
                           'tableClass'           : tableClass,
                           'rowClass'             : rowClass,
                           'cellClassNames'       : cellClassNames,
                           'tableName'            : tableName,
                           'className'            : className,
                           'classCallBack'        : callBackClass._pluralLinkName if callBackClass else None,
                           'selectCurrentCallBack': selectCurrentCallBack,
                           'searchCallBack'       : searchCallBack,
                           'moduleParent'         : moduleParent
                           }

        # add a cleaner id to the opened guiTable list
        self.moduleParent = moduleParent
        MODULEIDS[id(moduleParent)] = len(MODULEIDS)

    def setDefaultTableData(self):
        """Populate an empty table data object
        """
        self._tableData = {'updateFunc'           : None,
                           'changeFunc'           : None,
                           'tableSelection'       : None,
                           'pullDownWidget'       : None,
                           'tableClass'           : None,
                           'rowClass'             : None,
                           'cellClassNames'       : None,
                           'tableName'            : None,
                           'className'            : None,
                           'classCallBack'        : None,
                           'selectCurrentCallBack': None,
                           'searchCallBack'       : None,
                           'moduleParent'         : blankId
                           }

    def _initialiseTableNotifiers(self):
        """Set the initial notifiers to empty
        """
        self._tableNotifier = None
        self._rowNotifier = None
        self._cellNotifiers = []
        self._selectCurrentNotifier = None
        self._droppedNotifier = None
        self._searchNotifier = None

    def _close(self):
        self._clearTableNotifiers()
        self.unsetCurrent()
        self._clearItems()
        if self.application:
            self.application._cleanGarbageCollector()

    def _clearItems(self):
        """Force deleting these items to be garbage-collected on closing"""
        for i in self.items:
            del i
        self.items = []

    def _clearTableNotifiers(self):
        """Clean up the notifiers
        """
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

        if self._droppedNotifier is not None:
            self._droppedNotifier.unRegister()
            self._droppedNotifier = None

        if self._searchNotifier is not None:
            self._searchNotifier.unRegister()
            self._searchNotifier = None

    def setRowBackgroundColour(self, row, colour, columnList=None):
        """Set the background colour for the row

        :param row: row to be coloured
        :param colour: colour of type QtGui.Brush/QtGui.Color
        :param columnList: None, or list of column numbers, out-of-range columns are ignored
        :return:
        """
        # NOTE:ED - need colour/row checking, ignore for the minute
        try:
            # model = self.model()
            _rowMapping = [self.item(xx, 0).index for xx in range(self.rowCount())]
            _rowIndex = _rowMapping.index(row)
            # rowIndex = model.index(row, 0).row()

            if not isinstance(columnList, (type(None), list, tuple)):
                raise TypeError('columnList must be None, or a list of integers')

            if columnList:
                cols = [col for col in columnList if 0 <= col < self.columnCount()]
            else:
                cols = range(self.columnCount())
            for j in cols:
                self.item(_rowIndex, j).setBackground(colour)
        except Exception as es:
            getLogger().debug(f'error setting background colour: {es}')

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.getHiddenColumns()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.setHiddenColumns(value)


EDIT_ROLE = QtCore.Qt.EditRole


class GuiTableDelegate(QtWidgets.QStyledItemDelegate):
    """
    handle the setting of data when editing the table
    """

    def __init__(self, parent):
        """
        Initialise the delegate
        :param parent - link to the handling table:
        """
        QtWidgets.QStyledItemDelegate.__init__(self, parent)
        self.customWidget = False
        self._parent = parent
        self._editorCreated = 0
        self._returnPressed = False

    def setEditorData(self, widget, index) -> None:
        """populate the editor widget when the cell is edited
        """
        # edits occur without actually calling editItem() - and occurs twice?

        if self._editorCreated == 1:  # only populate on the first event after creation
            self._editorCreated = 2

            # if self._editorCreated:
            model = index.model()
            value = model.data(index, EDIT_ROLE)

            if not isinstance(value, (list, tuple)):
                value = (value,)

            if hasattr(widget, 'setColor'):
                widget.setColor(*value)

            elif hasattr(widget, 'setData'):
                widget.setData(*value)

            elif hasattr(widget, 'set'):
                widget.set(*value)

            elif hasattr(widget, 'setValue'):
                widget.setValue(*value)

            elif hasattr(widget, 'setText'):
                widget.setText(*value)

            elif hasattr(widget, 'setFile'):
                widget.setFile(*value)

            else:
                msg = 'Widget %s does not expose "setData", "set" or "setValue" method; ' % widget
                msg += 'required for table proxy editing'
                raise Exception(msg)

        else:
            super(GuiTableDelegate, self).setEditorData(widget, index)

    def createEditor(self, parent: QtWidgets.QWidget, option: 'QtWidgets.QStyleOptionViewItem', index: QtCore.QModelIndex) -> QtWidgets.QWidget:

        # create the widget from the superClass
        widget = super(GuiTableDelegate, self).createEditor(parent, option, index)

        self._editorCreated = 1
        self._editorValue = None
        self._returnPressed = False

        if isinstance(widget, QtWidgets.QLineEdit):
            # add returnPressed capture signal - destroyed on widget destroy
            widget.returnPressed.connect(partial(self._returnPressedCallback, widget))

        return widget

    def _returnPressedCallback(self, widget):
        """Capture the returnPressed event from the widget, because the setModeData event seems to be a frame behind the widget
        when getting the text()
        """

        # check that it is a QLineEdit - check for other types later (see old table class)
        if isinstance(widget, QtWidgets.QLineEdit):
            self._editorValue = widget.text()
            self._returnPressed = True

    def setModelData(self, widget, mode, index):
        """
        Set the object to the new value
        :param widget - typically a lineedit handling the editing of the cell:
        :param mode - editing mode:
        :param index - QModelIndex of the cell:
        """

        # check the widget type
        if isinstance(widget, QtWidgets.QLineEdit):
            if self._returnPressed:
                # grab from the stored value - other value seems to be a frame behind the QLineEdit update
                text = self._editorValue
            else:
                text = widget.text()
        else:
            # cannot proceed without a widget
            return

        row = index.row()
        col = index.column()

        try:
            rowData = []
            # read the row from the table to get the pid
            for ii in range(self._parent.columnCount()):
                rowData.append(self._parent.item(row, ii).text())

            if DATAFRAME_PID in self._parent._dataFrameObject.headings:

                # get the object to apply the data to
                pidCol = self._parent._dataFrameObject.headings.index(DATAFRAME_PID)
                pid = rowData[pidCol]
                obj = self._parent.project.getByPid(pid)

                # set the data which will fire notifiers to populate all tables
                func = self._parent._dataFrameObject.setEditValues[col]
                if func and obj:
                    func(obj, text)
            else:
                func = self._parent._dataFrameObject.setEditValues[col]
                if len(self._parent._dataFrameObject._objects) > 0:
                    if isinstance(self._parent._dataFrameObject._objects[0], pd.Series):
                        df = self._parent._dataFrameObject.dataFrame
                        obj = df.iloc[row]
                        if func and obj is not None:
                            result = func(obj, text)
                            df.iloc[row] = result
                            self._parent._dataFrameObject.dataFrame = df
                            self._parent.setTableFromDataFrameObject(dataFrameObject=self._parent._dataFrameObject,
                                                                     columnDefs=self._parent._dataFrameObject._columnDefinitions)
                    else:
                        try:
                            # special case for chemicalShiftTable
                            df = self._parent._dataFrameObject.dataFrame
                            # get the ordering of the table and use the uniqueId, the index in this case, to get the correct row from the dataframe
                            _tableIds = tuple(self._parent.item(rr, 0).value for rr in range(self._parent.rowCount()))
                            obj = df['_object'].loc[_tableIds[row]]
                            if func and obj is not None:
                                # notifiers should take care of the rest
                                func(obj, text)

                        except Exception as es:
                            # just ignore for the minute
                            pass
                        finally:
                            return

                getLogger().debug('table %s does not contain a Pid' % self)
                # return super(GuiTableDelegate, self).setModelData(widget, mode, index)

        except Exception as es:
            getLogger().warning('Error handling cell editing: %i %i %s' % (row, col, str(es)))


class GuiTableFrame(Frame):
    def __init__(self, *args, **kwargs):
        super(GuiTableFrame, self).__init__(parent=self.mainWidget, setLayout=True, spacing=(0, 0),
                                            showBorder=False, fShape='noFrame',
                                            grid=(1, 0),
                                            hPolicy='expanding', vPolicy='expanding')

        self.guiTable = GuiTable(self, *args, **kwargs)
        self.searchWidget = None


def _getValueByHeader(row, header):
    """
    Called from a table built with series

    :param row: the Pandas series object
    :param header: str , column header
    :return: a value of type int, float, str. If  inf, nan or None, returns and empty str
    """
    try:
        value = row[header]
        if value is None:
            return ''
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return ''
            else:
                return value
        else:
            return value
    except Exception as e:
        getLogger().warn('GuiTable error in getting a value for header %s. Check dataframe Header %s' % (header, e))


def _setValueByHeader(row, header, value):
    """
    Called from a table built with series
    :param row: the Pandas series object
    :param header: str , column header

    """
    row = row.copy()
    row[header] = value
    return row


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog
    from ccpn.util import Colour
    from ccpn.ui.gui.widgets.Column import ColumnClass


    app = TestApplication()


    class mockObj(object):
        """Mock object to test the table widget editing properties"""

        def __init__(self, integer=3, exampleFloat=63.3, exampleBool=True):
            pid = ''
            self.integer = integer
            self.exampleFloat = exampleFloat  # This will create a double spin box
            self.exampleBool = exampleBool  # This will create a check box
            self.string = 'white'  # This will create a line Edit
            self.exampleList = [(' ', 'Mock', 'Test'), ]  # This will create a pulldown
            self.color = QtGui.QColor('Red')
            self.icon = Icon('icons/warning')
            r = Colour.colourNameToHexDict['red']
            y = Colour.colourNameToHexDict['yellow']
            b = Colour.colourNameToHexDict['blue']
            colouredIcons = [None, Icon(color=r), Icon(color=y), Icon(color=b)]

            flagsList = [[''] * len(colouredIcons), [Icon] * len(colouredIcons), 1, colouredIcons]  # This will create a pulldown. Make a list with the

            # same structure of pulldown setData function: (texts=None, objects=None, index=None,
            # icons=None, clear=True, headerText=None, headerEnabled=False, headerIcon=None)

        def editBool(self, value):
            self.exampleBool = value

        def editFloat(self, value):
            self.exampleFloat = value

        def editPulldown(self, value):
            self.exampleList = value

        def editFlags(self, value):
            print('EDIT VALUE', value)


    def _comboboxCallBack(value):
        print('called value =', value)


    def _checkBoxCallBack(data):
        s = data['checked']
        print('called value =', s)


    def table_pulldownCallback(value):
        print('NEW', value)


    def table_pulldownCallbackShow():
        print('NEW', dir(), )


    popup = CcpnDialog(windowTitle='Test Table', setLayout=True)

    columns = ColumnClass([
        (
            'Float',
            lambda i: mockObj.exampleFloat,
            'TipText: Float',
            lambda mockObj, value: mockObj.editFloat(mockObj, value),
            None,
            ),

        (
            'Bool',
            lambda i: mockObj.exampleBool,
            'TipText: Bool',
            lambda mockObj, value: mockObj.editBool(mockObj, value),
            None,
            ),

        (
            'Pulldown',
            lambda i: mockObj.exampleList,
            'TipText: Pulldown',
            lambda mockObj, value: mockObj.editPulldown(mockObj, value),
            None,
            ),

        (
            'Flags',
            lambda i: mockObj.flagsList,
            'TipText: Flags',
            lambda mockObj, value: mockObj.editFlags(mockObj, value),
            None,
            )
        ])
    table_pulldownCallbackDict = {'callback': table_pulldownCallback, 'clickToShowCallback': table_pulldownCallbackShow}
    table = GuiTable(parent=popup, dataFrameObject=None, _pulldownKwds=table_pulldownCallbackDict, checkBoxCallback=_checkBoxCallBack, grid=(0, 0))
    df = table.getDataFrameFromList(table, [mockObj], colDefs=columns)

    table.setTableFromDataFrameObject(dataFrameObject=df)
    table.item(0, 0).setBackground(QtGui.QColor(100, 100, 150))  #color the first item
    # combo = PulldownList(table, callback=_comboboxCallBack)
    # table.setCellWidget(0, 0, combo)
    # combo.addItem('DDD')
    # combo.addItem('TTTT')
    # table.item(0, 0).setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
    # table.item(0, 0).setCheckState(QtCore.Qt.Unchecked)
    # table.item(0,0).setFormat(float(table.item(0,0).format))
    # print(table.item(0,0)._format)
    print(table.horizontalHeaderItem(0).text())
    print(table.item(0, 1).text())
    table.horizontalHeaderItem(1).setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
    table.horizontalHeaderItem(1).setCheckState(QtCore.Qt.Unchecked)

    # popup.show()
    # popup.raise_()
    # app.start()
