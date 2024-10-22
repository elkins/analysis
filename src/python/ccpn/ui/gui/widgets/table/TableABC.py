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
__dateModified__ = "$dateModified: 2024-10-16 18:41:24 +0100 (Wed, October 16, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2022-09-08 17:12:49 +0100 (Thu, September 08, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
from PyQt5 import QtWidgets, QtCore, QtGui
from dataclasses import dataclass
from contextlib import contextmanager, suppress
import typing
from functools import partial

from ccpn.ui.gui.widgets.Font import setWidgetFont, TABLEFONT, getFontHeight
from ccpn.ui.gui.widgets.Frame import ScrollableFrame
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.table._TableModel import _TableModel
from ccpn.ui.gui.widgets.table._TableCommon import INDEX_ROLE
from ccpn.ui.gui.widgets.table._TableAdditions import TableHeaderColumns, \
    TableCopyCell, TableExport, TableSearchMenu, TableDelete, TableMenuABC, TableHeaderABC
from ccpn.ui.gui.widgets.table._TableDelegates import _TableDelegateABC
from ccpn.util.OrderedSet import OrderedSet
from ccpn.util.Logging import getLogger
from ccpn.util.Common import NOTHING


# simple class to store the blocking state of the table
@dataclass
class _BlockingContent:
    modelBlocker = None
    rootBlocker = None


#=========================================================================================
# TableABC
#=========================================================================================

class TableABC(QtWidgets.QTableView):
    """A model/view to show pandas DataFrames as a table.

    The view defines the communication between the display and the model.
    """
    tableChanged = QtCore.pyqtSignal()
    sortingChanged = QtCore.pyqtSignal(dict)
    className = None

    styleSheet = """QTableView {
                        border-color: palette(mid);
                        border-width: %(_BORDER_WIDTH)spx;
                        border-style: solid;
                        border-radius: 2px;
                        gridline-color: %(_GRID_COLOR)s;
                        /* use #f8f088/palette(highlight) for yellow selection */
                        selection-background-color: qlineargradient(
                                                        x1: 0, y1: -200, x2: 0, y2: 200,
                                                        stop: 0 palette(highlight),
                                                        stop: 1 palette(light)
                                                    );
                        selection-color: palette(text);
                        color: palette(text);  /* shadow */
                        outline: 0px;
                    }
                    QHeaderView {
                        color: palette(text);
                        outline: 0px;
                    }
                    QTableView:focus {
                        border-color: palette(highlight);
                    }
                    """

    # NOTE:ED overrides QtCore.Qt.ForegroundRole - keep
    # QTableView::item - color: %(GUITABLE_ITEM_FOREGROUND)s;
    # QTableView::item:selected - color: %(GUITABLE_SELECTED_FOREGROUND)s;
    # cell uses alternate-background-role for unselected-focused cell
    _tableMenuOptions = None
    searchMenu = None
    copyCellMenu = None
    deleteMenu = None
    exportMenu = None
    headerColumnMenu = None

    # define overriding attributes here for subclassing - not setting will default to these
    _enableSearch = False
    _enableDelete = False
    _enableExport = False
    _enableCopyCell = False

    _columnDefs = None
    _enableSelectionCallback = False
    _enableActionCallback = False
    _actionCallback = NOTHING
    _selectionCallback = NOTHING
    _defaultEditable = True
    _rowHeightScale = None
    _tableMenuEnabled = True
    _toolTipsEnabled = True
    _enableCheckBoxes = False

    # define the default TableModel class
    tableModelClass = _TableModel
    defaultTableDelegate = _TableDelegateABC

    _droppedNotifier = None

    defaultSortColumn = 0  # allow the use of integer or string/tuple values here
    defaultSortOrder = QtCore.Qt.AscendingOrder
    _newFocus = False
    _disableNewFocus = True  # allow instant click on table

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
                 **kwds
                 ):
        """Initialise the table.

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
        :param kwds:

        parameters that are NOTHING can be set on the subclass, these are ignored in the parameter-list
        """
        if self.className is None:
            self.className = self.__class__.__name__
        super().__init__(parent)
        self._parent = parent
        if df is None:
            # make sure it's not empty
            df = pd.DataFrame({})
        self._tableBlockingLevel = 0

        self.setShowGrid(showGrid)
        self.setWordWrap(wordWrap)
        self.setSortingEnabled(True)

        # set the preferred scrolling behaviour
        self.setHorizontalScrollMode(self.ScrollPerPixel)
        self.setVerticalScrollMode(self.ScrollPerPixel)
        if selectRows:
            self.setSelectionBehavior(self.SelectRows)

        self._setMenuProperties(enableCopyCell, enableDelete, enableExport, enableSearch)
        self._setStyling(borderWidth, cellPadding, focusBorderWidth, gridColour, alternatingRows)
        self._setSelectionBehaviour(multiSelect)
        self._setFonts(df, showHorizontalHeader, showVerticalHeader)
        self._setCallbacks(actionCallback, actionCallbackEnabled, selectionCallback, selectionCallbackEnabled)

        # set up the menus
        self.setTableMenu(tableMenuEnabled)
        self.setHeaderMenu()

        self.setToolTipsEnabled(toolTipsEnabled)

        self.setItemDelegate(self.defaultTableDelegate(parent=self, focusBorderWidth=focusBorderWidth))

        # initialise the table
        self.updateDf(df, _resize, setHeightToRows, setWidthToColumns, setOnHeaderOnly=setOnHeaderOnly)
        self._setStyle()

    # pyqt5.15 does not allow setting by float
    def setFixedHeight(self, p_int):
        super().setFixedHeight(int(p_int))

    def _setSelectionBehaviour(self, multiSelect):
        """Set the selection-behaiour
        """
        # define the multi-selection behaviour
        self.multiSelect = multiSelect
        if multiSelect:
            self._selectionMode = self.ExtendedSelection
        else:
            self._selectionMode = self.SingleSelection
        self.setSelectionMode(self._selectionMode)
        self._clickInterval = QtWidgets.QApplication.instance().doubleClickInterval() * 1e6  # change to ns
        self._clickedInTable = False
        self._currentIndex = None

    def _setFonts(self, df, showHorizontalHeader, showVerticalHeader):
        """Set the font-style
        """
        setWidgetFont(self, name=TABLEFONT)
        height = getFontHeight(name=TABLEFONT) - 2
        self._setHeaderWidgets(height, showHorizontalHeader, showVerticalHeader, df)
        self.setMinimumSize(2 * height, 2 * height + self.horizontalScrollBar().height())

    def _setCallbacks(self, actionCallback, actionCallbackEnabled, selectionCallback, selectionCallbackEnabled):
        """Set the action/selection callbacks
        """
        # set selection/action callbacks
        self.doubleClicked.connect(self._actionConnect)
        if selectionCallback is not NOTHING:
            self.setSelectionCallback(selectionCallback)  # can set to None
        if selectionCallbackEnabled is not NOTHING:
            self.setSelectionCallbackEnabled(selectionCallbackEnabled)
        if actionCallback is not NOTHING:
            self.setActionCallback(actionCallback)  # can be set to None
        if actionCallbackEnabled is not NOTHING:
            self.setActionCallbackEnabled(actionCallbackEnabled)

    def _setStyling(self, borderWidth, cellPadding, focusBorderWidth, gridColour, alternatingRows):
        """Set the stylesheet options
        """
        # set stylesheet
        cols = self._colours = {}  #getColours()
        # add border-width/cell-padding options
        self._borderWidth = cols['_BORDER_WIDTH'] = borderWidth
        self._cellPadding = cols['_CELL_PADDING'] = cellPadding  # the extra padding for the selected cell-item
        self._cellPaddingOffset = cols['_CELL_PADDING_OFFSET'] = cellPadding - focusBorderWidth
        try:
            col = QtGui.QColor(gridColour).name() if gridColour else 'palette(mid)'
        except Exception:
            col = 'palette(mid)'
        self._gridColour = cols['_GRID_COLOR'] = col
        self.setAlternatingRowColors(alternatingRows)

    def _setStyle(self):
        self._checkPalette()
        self._signalTarget = partial(QtCore.QTimer.singleShot, 0, self._checkPalette)
        QtWidgets.QApplication.instance().sigPaletteChanged.connect(self._signalTarget)

    def _checkPalette(self, *args):
        """Update palette in response to palette change event.
        """
        self.setStyleSheet(self.styleSheet % self._colours)

    def _setMenuProperties(self, enableCopyCell, enableDelete, enableExport, enableSearch):
        """Add the required menus to the table
        """
        # create the individual table-menu and table-header-menu options
        self.searchMenu = TableSearchMenu(self, enableSearch if enableSearch != NOTHING else self._enableSearch)
        self.copyCellMenu = TableCopyCell(self, enableCopyCell if enableCopyCell != NOTHING else self._enableCopyCell)
        self.deleteMenu = TableDelete(self, enableDelete if enableDelete != NOTHING else self._enableDelete)
        self.exportMenu = TableExport(self, enableExport if enableExport != NOTHING else self._enableExport)
        self.headerColumnMenu = TableHeaderColumns(self, True)

        # add options to the table-menu and table-header-menu
        self.tableMenuOptions = [self.searchMenu,
                                 self.copyCellMenu,
                                 self.deleteMenu,
                                 self.exportMenu,
                                 self.headerColumnMenu]

    def updateDf(self, df, resize=True, setHeightToRows=False, setWidthToColumns=False, setOnHeaderOnly=False,
                 newModel=False):
        """Initialise the dataFrame
        """
        if not isinstance(df, (type(None), pd.DataFrame)):
            raise ValueError(f'data is not of type pd.DataFrame - {type(df)}')

        if df is not None and (setOnHeaderOnly or not df.empty):
            # set the model
            if newModel or not (model := self.model()):
                # create a new model if required
                model = self.tableModelClass(df, view=self)
                self.setModel(model)
            else:
                model.df = df

            self.resizeColumnsToContents()
            maxLen = str(len(df))
            indexHeader = self.verticalHeader()
            px = indexHeader.fontMetrics().boundingRect(maxLen).width() + 5
            indexHeader.setMinimumWidth(px)
            if resize:
                # resize if required
                self.resizeRowsToContents()

            if setWidthToColumns:
                self.setWidthToColumns()
            if setHeightToRows:
                self.setHeightToRows()

        else:
            # set a default empty model
            df = pd.DataFrame({})
            if newModel or not (model := self.model()):
                # create a new model if required
                model = self.tableModelClass(df, view=self)
                self.setModel(model)
            else:
                model.df = df

        return model

    def postUpdateDf(self):
        """Actions to be performed after the dataFrame has been updated for the table
        """
        # update the visible columns
        self.headerColumnMenu.restoreColumns()

    def setModel(self, model: QtCore.QAbstractItemModel) -> None:
        """Set the model for the view
        """
        super().setModel(model)

        # attach a handler for updating the selection on sorting
        model.layoutAboutToBeChanged.connect(self._preChangeSelectionOrderCallback)
        model.layoutChanged.connect(self._postChangeSelectionOrderCallback)

        # set selection callback because the model has changed?
        self.selectionModel().selectionChanged.connect(self._selectionConnect)
        model._defaultEditable = self._defaultEditable
        model._enableCheckBoxes = self._enableCheckBoxes

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
        except Exception:
            getLogger().debug2(f'{self.__class__.__name__} has no _widgetScrollArea')

    def _setHeaderWidgets(self, _height, showHorizontalHeader, showVerticalHeader, df):
        """Initialise the headers
        """
        # set the horizontalHeader information
        _header = self.horizontalHeader()
        # set Interactive and last column to expanding
        _header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        _header.setStretchLastSection(True)
        # only look at visible section
        _header.setResizeContentsPrecision(10)
        _header.setDefaultAlignment(QtCore.Qt.AlignLeft)
        _header.setMinimumSectionSize(20)
        _header.setHighlightSections(self.font().bold())
        _header.setVisible(showHorizontalHeader)
        setWidgetFont(_header, name=TABLEFONT)
        _header.setDefaultAlignment(QtCore.Qt.AlignVCenter)

        # set the verticalHeader information
        _header = self.verticalHeader()
        # set Interactive and last column to expanding
        _header.setStretchLastSection(False)
        # only look at visible section
        _header.setResizeContentsPrecision(5)
        _header.setDefaultAlignment(QtCore.Qt.AlignLeft)
        _header.setMinimumWidth(25)  # gives enough of a handle to resize if required
        _header.setVisible(showVerticalHeader)
        _header.setHighlightSections(self.font().bold())

        setWidgetFont(_header, name=TABLEFONT)
        if self._rowHeightScale:
            # set the fixed row-height
            _header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
            _height *= self._rowHeightScale
        else:
            # otherwise user-changeable
            _header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

        _header.setDefaultSectionSize(int(_height))
        _header.setMinimumSectionSize(int(_height))

    def _preChangeSelectionOrderCallback(self, *args):
        """Handle updating the selection when the table is about to change, i.e., before sorting
        """
        pass

    def _postChangeSelectionOrderCallback(self, *args):
        """Handle updating the selection when the table has been sorted
        """
        model = self.model()
        selModel = self.selectionModel()
        selection = self.selectionModel().selectedIndexes()

        if model._sortIndex and model._oldSortIndex:
            # get the pre-sorted mapping
            itmRows = {itm.row() for itm in selection}
            if rows := [model._oldSortIndex[rr] for rr in itmRows if 0 <= rr < len(model._oldSortIndex)]:
                # block so no signals emitted
                self.blockSignals(True)
                selModel.blockSignals(True)

                try:
                    newSel = QtCore.QItemSelection()
                    for row in rows:
                        if row in model._sortIndex:
                            # map to the new sort-order
                            idx = model.index(model._sortIndex.index(row), 0)
                            newSel.merge(QtCore.QItemSelection(idx, idx), QtCore.QItemSelectionModel.Select)

                    # Select the cells in the data view - spawns single change event
                    self.selectionModel().select(newSel, (QtCore.QItemSelectionModel.Rows |
                                                          QtCore.QItemSelectionModel.ClearAndSelect))

                finally:
                    # unblock to enable again
                    selModel.blockSignals(False)
                    self.blockSignals(False)

            sortColumnName = None
            if model._sortColumn is not None:
                sortColumnName = self.headerColumnMenu.columnTexts[model._sortColumn]
            self.sortingChanged.emit({
                'sortColumnName' : sortColumnName,
                'sortColumnIndex': model._sortColumn,
                'oldSort'        : model._oldSortIndex,
                'newSort'        : model._sortIndex,
                'order'          : model._sortOrder,
                })

    def _close(self):
        self.close()

    def close(self):
        """Clean up the notifiers
        """
        if self._droppedNotifier:
            self._droppedNotifier.unRegister()
            self._droppedNotifier = None
        # remove signals from header/table
        if header := self.horizontalHeader():
            with suppress(Exception):
                header.customContextMenuRequested.disconnect(self._raiseHeaderContextMenu)
        with suppress(Exception):
            self.customContextMenuRequested.disconnect(self._raiseTableContextMenu)
        with suppress(Exception):
            QtWidgets.QApplication.instance().sigPaletteChanged.disconnect(self._signalTarget)
        super().close()

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _df(self):
        """Return the Pandas-dataFrame holding the data
        """
        return self.model().df

    @_df.setter
    def _df(self, value):
        self.model().df = value

    @property
    def _displayedDf(self):
        """Return the Pandas-dataFrame in exactly the same way as it is displayed: sorted and filtered.
        """
        return self.model().displayedDf

    def isEditable(self):
        """Return True if the default state of the table is editable
        """
        return self._defaultEditable

    def setEditable(self, value):
        """Set the default editable state of the table.
        Individual columns can be set in the columns-settings.
        """
        if not isinstance(value, bool):
            raise ValueError(f'{self.__class__.__name__}.setEditable: value is not True|False')
        self._defaultEditable = value
        if self.model():
            # keep the model in-sync with the view
            self.model()._defaultEditable = value

    #=========================================================================================
    # Selection callbacks
    #=========================================================================================

    def setSelectionCallback(self, selectionCallback):
        """Set the selection-callback for the table.
        """
        # update callbacks - overwrite method
        if not (selectionCallback is None or callable(selectionCallback)):
            raise ValueError(f'{self.__class__.__name__}.setSelectionCallback: selectionCallback is not None|callable')
        self._selectionCallback = selectionCallback

    def resetSelectionCallback(self):
        """Reset the selection-callback for the table back to the class-method.
        """
        self._selectionCallback = NOTHING

    def selectionCallbackEnabled(self):
        """Return True if selection-callback is enabled.
        """
        return self._enableSelectionCallback

    def setSelectionCallbackEnabled(self, value):
        """Enable/disable the selection-callback
        """
        if not isinstance(value, bool):
            raise ValueError(f'{self.__class__.__name__}.setSelectionCallbackEnabled: value is not True|False')
        self._enableSelectionCallback = value

    def _selectionConnect(self, selected, deselected):
        """Handle the callback for a selection.
        _selectionCallback is the controlling attribute defined on the class
        can be None, NOTHING or callable:
            _selectionCallback is None       callback is disabled, removes the user-setting
                                             this can be set with setSelectionCallback
            _selectionCallback is NOTHING    method selectionCallback on the class is called
                                             Cannot set to this explicitly,
                                             use resetSelectionCallback to return to this behaviour
            _selectionCallback is callable   use the callable,
                                             this can be set with setSelectionCallback
        _enableSelectionCallback disables the callback
        """
        if self._enableSelectionCallback and self._selectionCallback is not None:
            # get the unique df-rows from the selections
            newRows = OrderedSet((dd := idx.data(INDEX_ROLE)) is not None and dd[0]
                                 for sel in selected for idx in sel.indexes())
            oldRows = OrderedSet((dd := idx.data(INDEX_ROLE)) is not None and dd[0]
                                 for sel in deselected for idx in sel.indexes())
            sRows = OrderedSet((dd := idx.data(INDEX_ROLE)) is not None and dd[0] for idx in self.selectedIndexes())
            df = self._df
            # remove any bad rows
            new = df.iloc[(rr for rr in newRows if rr is not None and rr is not False)]
            old = df.iloc[(rr for rr in oldRows if rr is not None and rr is not False)]
            sel = df.iloc[(rr for rr in sRows if rr is not None and rr is not False)]
            try:
                last = df.iloc[[self.currentIndex().data(INDEX_ROLE)[0]]]
            except Exception:
                last = []
            with self._blockTableSignals('_selectionCallback', blanking=False, disableScroll=True):
                if self._selectionCallback is NOTHING:
                    # pass the dfs to the class-method callback
                    self.selectionCallback(new, old, sel, last)
                else:
                    self._selectionCallback(new, old, sel, last)

    #=========================================================================================
    # Action callbacks
    #=========================================================================================

    def setActionCallback(self, actionCallback):
        """Set the action-callback for the table.
        """
        # update callbacks - overwrite method
        if not (actionCallback is None or callable(actionCallback)):
            raise ValueError(f'{self.__class__.__name__}.setActionCallback: actionCallback is not None|callable')
        self._actionCallback = actionCallback

    def resetActionCallback(self):
        """Reset the action-callback for the table back to the class-method.
        """
        self._actionCallback = NOTHING

    def actionCallbackEnabled(self):
        """Return True if action-callback is enabled.
        """
        return self._enableActionCallback

    def setActionCallbackEnabled(self, value):
        """Enable/disable the action-callback
        """
        if not isinstance(value, bool):
            raise ValueError(f'{self.__class__.__name__}.setActionCallbackEnabled: value is not True|False')
        self._enableActionCallback = value

    def _actionConnect(self, modelIndex):
        """Handle the callback for an action, either return or mouse-double-click.
        _actionCallback is the controlling attribute defined on the class
        can be None, NOTHING or callable:
            _actionCallback is None       callback is disabled, removes the user-setting
                                          this can be set with setActionCallback
            _actionCallback is NOTHING    method actionCallback on the class is called
                                          Cannot set to this explicitly,
                                          use resetActionCallback to return to this behaviour
            _actionCallback is callable   use the callable,
                                          this can be set with setActionCallback
        _enableActionCallback disables the callback
        """
        if bool(modelIndex.flags() & QtCore.Qt.ItemIsEditable):
            # item is editable so skip the action
            return
        if self._enableActionCallback and self._actionCallback is not None:
            # get the df-rows from the selection
            sRows = OrderedSet((dd := idx.data(INDEX_ROLE)) is not None and dd[0] for idx in self.selectedIndexes())
            df = self._df
            # remove any bad rows
            sel = df.iloc[(rr for rr in sRows if rr is not None and rr is not False)]
            try:
                last = df.iloc[[self.currentIndex().data(INDEX_ROLE)[0]] if sRows else []]
            except Exception:
                last = []
            with self._blockTableSignals('_actionCallback', blanking=False, disableScroll=True):
                if self._actionCallback is NOTHING:
                    # pass the dfs to the class-method callback
                    self.actionCallback(sel, last)
                else:
                    self._actionCallback(sel, last)

    #=========================================================================================
    # Selection/Action methods
    #=========================================================================================

    def selectionCallback(self, selected, deselected, selection, lastItem):
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

    def selectedRows(self):
        """
        :return: a DataFrame with selected rows
        """
        sRows = OrderedSet((dd := idx.data(INDEX_ROLE)) is not None and dd[0] for idx in self.selectedIndexes())
        # remove any bad rows
        return self._df.iloc[(rr for rr in sRows if rr is not None and rr is not False)]

    def selectFirstRow(self, doCallback=True):
        from ccpn.core.lib.ContextManagers import nullContext

        context = nullContext if doCallback else self._blockTableSignals
        model = self.model()
        rowIndex = model.index(0, 0)  #First Row!
        with context('selectFirstRow'):
            selectionModel = self.selectionModel()
            selectionModel.clearSelection()
            selectionModel.select(rowIndex, selectionModel.Select | selectionModel.Rows)

    def selectRowsByValues(self, values, headerName, scrollToSelection=True, doCallback=True):
        """
        Select rows if the given values are present in the table.
        :param values: list of value to select
        :param headerName: the column name for the column where to search the values
        :param scrollToSelection: navigate to the table to show the result
        :return: None
        For obj table use the "highlightObjects" method.
        """
        if self._df is None or self._df.empty:
            return
        if headerName not in self._df.columns:
            return
        from ccpn.core.lib.ContextManagers import nullContext

        context = nullContext if doCallback else self._blockTableSignals

        with context('selectRowsByValues'):
            selectionModel = self.selectionModel()
            model = self.model()
            selectionModel.clearSelection()
            columnTextIx = self.headerColumnMenu.columnTexts.index(headerName)
            for i in model._sortIndex:
                cell = model.index(i, columnTextIx)
                if cell is None:
                    continue
                tableValue = cell.data()
                for valueToSelect in values:
                    if tableValue == valueToSelect:
                        rowIndex = model.index(i, 0)
                        if rowIndex is None:
                            continue
                        selectionModel.select(rowIndex, selectionModel.Select | selectionModel.Rows)
                        if scrollToSelection:
                            self.scrollTo(rowIndex, self.EnsureVisible)

    def clearSelection(self) -> None:
        """Clear the selection.
        Call selection callback of there were items selected.
        Required as selectionCallback signal does not fire for clicking in the blank section
        of a large table below the last row.
        """
        deselection = []
        if inds := self.selectedIndexes():
            # capture the last selection before clearing
            deselection = QtCore.QItemSelection()
            for indx in inds:
                deselection.append(QtCore.QItemSelectionRange(indx))
        # call the superclass
        super().clearSelection()
        if inds and not self.signalsBlocked():
            # simulate event clicked in the empty space, with last selection
            self._selectionConnect([], deselection)

    #=========================================================================================
    # keyboard and mouse handling - modified to allow double-click to keep current selection
    #=========================================================================================

    @staticmethod
    def _keyModifierPressed():
        """Is the user clicking while holding a modifier
        """
        allKeyModifers = [QtCore.Qt.ShiftModifier, QtCore.Qt.ControlModifier, QtCore.Qt.AltModifier,
                          QtCore.Qt.MetaModifier]
        keyMod = QtWidgets.QApplication.keyboardModifiers()

        return keyMod in allKeyModifers

    def focusInEvent(self, e: QtGui.QFocusEvent) -> None:
        """Handle grabbing focus - disable first mouse-click from clearing current selection.
        """
        self._newFocus = (self.viewport().underMouse() and
                          bool(QtGui.QGuiApplication.mouseButtons()) and
                          not self._disableNewFocus)
        super().focusInEvent(e)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle mouse-press event so that double-click keeps any multi-selection
        """
        if self._newFocus:
            return

        # doesn't respond in double-click interval - minor behaviour change to ExtendedSelection
        self._currentIndex = self.indexAt(event.pos())
        row, col = self.rowAt(event.pos().y()), self.columnAt(event.pos().x())

        # user can click in the blank space under the table
        self._clickedInTable = bool(self._currentIndex)
        super().mousePressEvent(event)
        if row < 0 or col < 0 and event.button() == QtCore.Qt.LeftButton:
            #     # clicked outside the valid cells of the table
            #     #   catches singleSelect if doesn't fire from super() - weird
            #     self.clearSelection()
            deselection = []
            if inds := self.selectedIndexes():
                # capture the last selection before clearing
                deselection = QtCore.QItemSelection()
                for indx in inds:
                    deselection.append(QtCore.QItemSelectionRange(indx))
            # call the superclass
            # super().clearSelection()
            # if inds and not self.signalsBlocked():
            #     # simulate event clicked in the empty space, with last selection
            #     self._selectionConnect([], deselection)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        """Handle mouse-release event, and discard first click if doesn't have focus.
        """
        if self._newFocus:
            self._newFocus = False
            return
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        """Handle mouse-move event, and discard if have just grabbed focus.
        """
        if self._newFocus:
            return
        super().mouseMoveEvent(e)

    def keyPressEvent(self, event):
        """Handle keyPress events on the table
        """
        super().keyPressEvent(event)

        # key = event.key()
        # cursors = [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down, QtCore.Qt.Key_Left, QtCore.Qt.Key_Right]
        enter = [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]
        allKeyModifers = [QtCore.Qt.ShiftModifier, QtCore.Qt.ControlModifier, QtCore.Qt.AltModifier,
                          QtCore.Qt.MetaModifier]

        # for MacOS ControlModifier is 'cmd' and MetaModifier is 'ctrl'
        addSelectionMod = [QtCore.Qt.ControlModifier]

        key = event.key()
        if key in enter:

            # enter/return pressed - select/deselect current item
            keyMod = QtWidgets.QApplication.keyboardModifiers()

            if keyMod in addSelectionMod:
                if idx := self.currentIndex():
                    # set the item, which toggles selection of the row
                    self.setCurrentIndex(idx)

            elif keyMod not in allKeyModifers:
                # fire the action callback (double-click on selected)
                self._actionConnect(self.currentIndex())

        elif key in [QtCore.Qt.Key_Escape]:
            # press the escape-key to clear the selection
            self.clearSelection()

    def _processDroppedItems(self, data):
        """CallBack for Drop events
        """
        pass

    def _handleDroppedItems(self, pids, objType, pulldown):
        """Handle dropped items.
        
        :param pids: the selected objects pids
        :param objType: the instance of the obj to handle, E.g. PeakList
        :param pulldown: the pulldown of the module wich updates the table
        :return: Actions: Select the dropped item on the table or/and open a new modules if multiple drops.
        If multiple different obj instances, then asks first.
        """
        pass

    def scrollToSelectedIndex(self):
        """Scroll table to show the nearest selected index
        """
        h = self.horizontalHeader()
        for i in range(h.count()):
            if not h.isSectionHidden(i) and h.sectionViewportPosition(i) >= 0:
                if (selection := self.selectionModel().selectedIndexes()):
                    self.scrollTo(selection[0], self.EnsureVisible)  # doesn't dance around so much
                    return

    #=========================================================================================
    # Block table signals
    #=========================================================================================

    def _blockTableEvents(self, blanking=True, disableScroll=False, tableState=None):
        """Block all updates/signals/notifiers in the table.
        """
        # block on first entry
        if self._tableBlockingLevel == 0:
            if disableScroll:
                self._scrollOverride = True

            # use the Qt widget to block signals - selectionModel must also be blocked
            tableState.modelBlocker = QtCore.QSignalBlocker(self.selectionModel())
            tableState.rootBlocker = QtCore.QSignalBlocker(self)
            # tableState.enabledState = self.updatesEnabled()
            # self.setUpdatesEnabled(False)

            if blanking and self.project:
                self.project.blankNotification()

            # list to store any deferred functions until blocking has finished
            self._deferredFuncs = []

        self._tableBlockingLevel += 1

    def _unblockTableEvents(self, blanking=True, disableScroll=False, tableState=None):
        """Unblock all updates/signals/notifiers in the table.
        """
        if self._tableBlockingLevel <= 0:
            raise RuntimeError('Error: tableBlockingLevel already at 0')

        self._tableBlockingLevel -= 1

        # unblock all signals on last exit
        if self._tableBlockingLevel == 0:
            if blanking and self.project:
                self.project.unblankNotification()

            tableState.modelBlocker = None
            tableState.rootBlocker = None
            # self.setUpdatesEnabled(tableState.enabledState)
            # tableState.enabledState = None

            if disableScroll:
                self._scrollOverride = False

            self.update()

            for func in self._deferredFuncs:
                # process simple deferred functions - required so that qt signals are not blocked
                func()
            self._deferredFuncs = []

    @contextmanager
    def _blockTableSignals(self, callerId='', blanking=True, disableScroll=False):
        """Block all signals from the table
        """
        tableState = _BlockingContent()
        self._blockTableEvents(blanking, disableScroll=disableScroll, tableState=tableState)
        try:
            yield  # yield control to the calling process
        except Exception as es:
            raise es
        finally:
            self._unblockTableEvents(blanking, disableScroll=disableScroll, tableState=tableState)

    #=========================================================================================
    # Other methods
    #=========================================================================================

    def rowCount(self):
        """Return the number of rows in the table
        """
        return (model := self.model()) and model.rowCount()

    def columnCount(self):
        """Return the number of columns in the table
        """
        return (model := self.model()) and model.columnCount()

    def setWidthToColumns(self):
        """Set the width of the table to the column widths
        """
        # need to get values from padding
        header = self.horizontalHeader()
        width = -2  # left/right borders
        # +1 for cell border on right-hand-side
        width += sum((self.columnWidth(nn) + 1) for nn in range(header.count())
                     if not header.isSectionHidden(nn) and header.sectionViewportPosition(nn) >= 0)

        self.setFixedWidth(width)

    def setHeightToRows(self):
        """Set the height of the table to the row heights
        """
        height = 2 * self.horizontalHeader().height()

        header = self.verticalHeader()
        for nn in range(header.count()):
            if not header.isSectionHidden(nn) and header.sectionViewportPosition(nn) >= 0:
                height += (self.rowHeight(nn) + 1)

        self.setFixedHeight(height)

    def mapToSource(self, positions=None):
        """Return a tuple of the locations of the specified visible-table positions in the dataFrame.

        positions must be an iterable of table-positions, each a list|tuple of the form [row, col].

        :param positions: iterable of list|tuples
        :return: tuple to tuples
        """
        if not isinstance(positions, typing.Iterable):
            raise TypeError(f'{self.__class__.__name__}.mapToSource: '
                            f'positions must be an iterable of list|tuples of the form [row, col]')
        if not all(isinstance(pos, (list, tuple)) and
                   len(pos) == 2 and isinstance(pos[0], int) and isinstance(pos[1], int) for pos in positions):
            raise TypeError(f'{self.__class__.__name__}.mapToSource: '
                            f'positions must be an iterable of list|tuples of the form [row, col]')

        sortIndex = self.model()._sortIndex
        df = self.model().df
        if not all((0 <= pos[0] < df.shape[0]) and (0 <= pos[1] < df.shape[1]) for pos in positions):
            raise TypeError(f'{self.__class__.__name__}.mapToSource: positions contains invalid values')

        return tuple((sortIndex[pos[0]], pos[1]) for pos in positions)

    def mapRowsToSource(self, rows=None) -> tuple:
        """Return a tuple of the source rows in the dataFrame.

        rows must be an iterable of integers, or None.
        None will return the source rows for the whole table.

        :param rows: iterable of ints
        :return: tuple of ints
        """
        sortIndex = self.model()._sortIndex
        if rows is None:
            return tuple(self.model()._sortIndex)

        if not isinstance(rows, typing.Iterable):
            raise TypeError(f'{self.__class__.__name__}.mapRowsToSource: rows must be an iterable of ints')
        if not all(isinstance(row, int) for row in rows):
            raise TypeError(f'{self.__class__.__name__}.mapRowsToSource: rows must be an iterable of ints')

        df = self.model().df
        if not all((0 <= row < df.shape[0]) for row in rows):
            raise TypeError(f'{self.__class__.__name__}.mapToSource: rows contains invalid values')

        return tuple(sortIndex[row] if 0 <= row < len(sortIndex) else None for row in rows)

    def setForeground(self, row: int, column: int, colour: QtGui.QColor | str):
        """Set the foreground colour for cell at position (row, column).

        :param int row: row as integer
        :param int column: column as integer
        :param colour: colour compatible with QtGui.QColor
        """
        if (model := self.model()):
            model.setForeground(row, column, colour)

    def setBackground(self, row: int, column: int, colour: QtGui.QColor | str):
        """Set the background colour for cell at position (row, column).

        :param int row: row as integer
        :param int column: column as integer
        :param colour: colour compatible with QtGui.QColor
        """
        if (model := self.model()):
            model.setBackground(row, column, colour)

    def setBorderVisible(self, row: int, column: int, enabled: bool):
        """Enable the border for cell at position (row, column).

        :param int row: row as integer
        :param int column: column as integer
        :param enabled: True/Falsse
        """
        if (model := self.model()):
            model.setBorderVisible(row, column, enabled)

    #=========================================================================================
    # Table context menu
    #=========================================================================================

    @property
    def tableMenuOptions(self):
        """Return the list of table options attached to the table
        """
        return self._tableMenuOptions

    @tableMenuOptions.setter
    def tableMenuOptions(self, value):
        for tt in value:
            if not isinstance(tt, (TableMenuABC, TableHeaderABC)):
                raise RuntimeError(f'{self.__class__.__name__}.tableMenuOptions are incorrect.')

        self._tableMenuOptions = value

    def setTableMenu(self, tableMenuEnabled=NOTHING) -> typing.Optional[Menu]:
        """Set up the context menu for the main table
        """
        if tableMenuEnabled is not NOTHING:
            self._tableMenuEnabled = bool(tableMenuEnabled)
        else:
            # revert to the super-class setting
            with suppress(AttributeError):
                del self._tableMenuEnabled

        if not self._tableMenuEnabled:
            self._thisTableMenu = None
            # disconnect any previous menus
            with suppress(TypeError):
                self.customContextMenuRequested.disconnect(self._raiseTableContextMenu)
            return

        self._thisTableMenu = menu = Menu('', self, isFloatWidget=True)
        setWidgetFont(menu, )

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._raiseTableContextMenu)

        self.addTableMenuOptions(menu)

        return menu

    def setToolTipsEnabled(self, toolTipsEnabled=NOTHING):
        """Enable/disable the individual tooltips for the items in the table.
        Call without parameters to revert to the class setting.
        :param toolTipsEnabled:
        """
        if toolTipsEnabled is not NOTHING:
            self._toolTipsEnabled = bool(toolTipsEnabled)
        else:
            # delete the local to revert to the super-class setting
            with suppress(AttributeError):
                del self._toolTipsEnabled

    def addTableMenuOptions(self, menu):
        """Add options to the right-mouse menu
        """
        # NOTE:ED - call additional addMenuOptions here to add options to the table menu
        for tableOption in self._tableMenuOptions:
            if isinstance(tableOption, TableMenuABC):
                # add the specific options to the menu
                tableOption.addMenuOptions(menu)

    def setTableMenuOptions(self, menu):
        """Update options in the right-mouse menu
        """
        # Subclass to add extra options
        pass

    def _raiseTableContextMenu(self, pos):
        """Create a new menu and popup at cursor position
        """
        if not (menu := self._thisTableMenu):
            getLogger().debug('menu is not defined')
            return

        # call the class setup
        self.setTableMenuOptions(menu)

        # NOTE:ED - call additional setMenuOptions here to add enable/disable/hide options in the table menu
        for tableOption in self._tableMenuOptions:
            if isinstance(tableOption, TableMenuABC):
                # add the specific options to the menu
                tableOption.setMenuOptions(menu)

        pos = QtCore.QPoint(pos.x() + 5, pos.y())
        menu.exec_(self.mapToGlobal(pos))

    def showSearchSettings(self):
        """Show the search-settings for the table
        """
        self.searchMenu and self.searchMenu.showSearchSettings()

    #=========================================================================================
    # Header context menu
    #=========================================================================================

    def setHeaderMenu(self) -> Menu:
        """Set up the context menu for the table header
        """
        self._thisTableHeaderMenu = menu = Menu('', self, isFloatWidget=True)
        setWidgetFont(menu, )

        headers = self.horizontalHeader()
        headers.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        headers.customContextMenuRequested.connect(self._raiseHeaderContextMenu)

        self.addHeaderMenuOptions(menu)

        return menu

    def addHeaderMenuOptions(self, menu):
        """Add options to the right-mouse menu
        """
        # NOTE:ED - call additional setHeaderMenu here to add options to the header menu
        for tableOption in self._tableMenuOptions:
            if isinstance(tableOption, TableHeaderABC):
                # add the specific options to the menu
                tableOption.addMenuOptions(menu)

    def setHeaderMenuOptions(self, menu):
        """Update options in the right-mouse menu
        """
        # Subclass to add extra options
        pass

    def _raiseHeaderContextMenu(self, pos):
        """Raise the menu on the header
        """
        if not (menu := self._thisTableHeaderMenu):
            getLogger().warning('header-menu is not defined')
            return
        if self._df is None or self._df.empty:
            return

        # move the popup a bit down; otherwise can trigger an event if the pointer is just on top the first item
        pos = QtCore.QPoint(pos.x() + 5, pos.y())

        # call the class setup
        self.setHeaderMenuOptions(menu)

        # NOTE:ED - call additional setHeaderMenuOptions here to add enable/disable/hide options in the header menu
        for tableOption in self._tableMenuOptions:
            if isinstance(tableOption, TableHeaderABC):
                # enable/disable/hide the specific options in the menu
                tableOption.setMenuOptions(menu)

        if len(menu.actions()):
            menu.exec_(self.mapToGlobal(pos))

    def isColumnInternal(self, column: int):
        """Return True if the column is internal and not for external viewing
        """
        return self.headerColumnMenu.isColumnInternal(column)

    def showColumn(self, column: int) -> None:
        width = self.columnWidth(column)
        super().showColumn(column)
        if not width:
            self.resizeColumnToContents(column)

    #=========================================================================================
    # Table functions
    #=========================================================================================

    def setSearchEnabled(self, value):
        """Enable/disable the search option in the right-mouse menu.

        :param bool value: enabled True/False
        """
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}.setSearchEnabled: value must be True/False')

        self.searchMenu.enabled = value

    def setExportEnabled(self, value):
        """Enable/disable the export option in the right-mouse menu.

        :param bool value: enabled True/False
        """
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}.setExportEnabled: value must be True/False')

        self.exportMenu.enabled = value

    def setDeleteEnabled(self, value):
        """Enable/disable the delete option in the right-mouse menu.

        :param bool value: enabled True/False
        """
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}.setDeleteEnabled: value must be True/False')

        self.deleteMenu.enabled = value

    def setCopyCellEnabled(self, value):
        """Enable/disable the copyCell option in the right-mouse menu.

        :param bool value: enabled True/False
        """
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}.setCopyCellEnabled: value must be True/False')

        self.copyCellMenu.enabled = value
