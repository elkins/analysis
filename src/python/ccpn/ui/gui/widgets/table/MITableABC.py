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
__date__ = "$Date: 2023-01-27 14:31:31 +0100 (Fri, January 27, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import contextlib
import pandas as pd
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QItemSelectionModel, QSize

from ccpn.ui.gui.widgets.ScrollArea import _ScrollWidgetCorner
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.table.TableABC import TableABC
from ccpn.ui.gui.widgets.table._TableCommon import SELECT_ROWS, _TableSelection
from ccpn.ui.gui.widgets.Font import setWidgetFont, TABLEFONT
from ccpn.util.Common import NOTHING

from ccpn.ui.gui.widgets.table._MITableDelegates import _ColourDelegate
from ccpn.ui.gui.widgets.table._MITableModel import _MITableModel
from ccpn.ui.gui.widgets.table._MITableHeaderView import _HorizontalMITableHeaderView, _VerticalMITableHeaderView


#=========================================================================================
# MITableABC
#=========================================================================================

class MITableABC(TableABC):
    """A model/view to show pandas DataFrames as a table.
    Allows for the use of single/multiIndex columns and indexes.

    The view defines the communication between the display and the model.
    """
    _tableSelectionChanged = QtCore.pyqtSignal(_TableSelection)
    className = None

    # define the default MultiIndex class
    tableModelClass = _MITableModel
    defaultTableDelegate = _ColourDelegate

    _columnHeader = None
    _indexHeader = None
    _topCornerWidget = None

    _horizontalHeader = None
    _verticalHeader = None
    _horizontalScrollbar = None
    _verticalScrollbar = None

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
                 dividerColour=None,
                 **kwds):
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
        :param tableMenuEnabled:
        :param toolTipsEnabled:
        :param dividerColour:
        :param kwds:
        """
        # Indicates whether the widget has been shown yet. Set to True later
        self._loaded = False
        self._tableArea = None
        self._dividerColour = dividerColour
        if self.className is None:
            self.className = self.__class__.__name__
        super().__init__(parent, df=df,
                         multiSelect=multiSelect, selectRows=selectRows,
                         showHorizontalHeader=False, showVerticalHeader=False,  # disable for the new headers
                         borderWidth=borderWidth, cellPadding=cellPadding, focusBorderWidth=focusBorderWidth, gridColour=gridColour,
                         _resize=_resize, setWidthToColumns=setWidthToColumns, setHeightToRows=setHeightToRows,
                         setOnHeaderOnly=setOnHeaderOnly, showGrid=showGrid, wordWrap=wordWrap,
                         alternatingRows=alternatingRows,
                         selectionCallback=selectionCallback, selectionCallbackEnabled=selectionCallbackEnabled,
                         actionCallback=actionCallback, actionCallbackEnabled=actionCallbackEnabled,
                         enableExport=enableExport, enableDelete=enableDelete, enableSearch=enableSearch, enableCopyCell=enableCopyCell,
                         tableMenuEnabled=tableMenuEnabled, toolTipsEnabled=toolTipsEnabled,
                         )
        # the last-section must match the new headers
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setStretchLastSection(False)
        self._indexHeader._init()
        self._columnHeader._init()

        # set visibility on new headers
        # NOTE:ED - check how this sets the SizeHint
        if not showVerticalHeader:
            self._indexHeader.setVisible(showVerticalHeader)
        if not showHorizontalHeader:
            self._columnHeader.setVisible(showHorizontalHeader)

        # connection to update the indexHeader
        self.model().layoutChanged.connect(self._indexHeader.setSpans)

        # Link selection to headers
        self.selectionModel().selectionChanged.connect(self._tableSelectionChangedCallback)

        # connection to _tableSelectionChanged signal - change header selection to match without other signals
        self._tableSelectionChanged.connect(self._updateHeaderSelection)

    def updateDf(self, df, resize=True, setHeightToRows=False, setWidthToColumns=False, setOnHeaderOnly=False, newModel=False):
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
        ...

    def setModel(self, model: QtCore.QAbstractItemModel) -> None:
        super().setModel(model)

        if self._indexHeader:
            # connection to update the indexHeader
            model.layoutChanged.connect(self._indexHeader.setSpans)

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        super().showEvent(a0)

        self._loaded = True

    def _updateHeaderSelection(self, headerData):
        """Update the rows/columns in the headers if the selection has changed in the main table

        :param headerData: _TableChanged object containing orientation and rows/columns
        :return:
        """
        if not headerData:
            return

        if headerData.orientation == SELECT_ROWS:
            self._indexHeader._processSelectionFromRows(headerData.rows)

        # elif headerData.orientation == SELECT_COLUMNS:
        #     # not implemented yet
        #     pass

    #=========================================================================================
    # Implementation from _MITableView (not needed anymore)
    #=========================================================================================

    def _preChangeSelectionOrderCallback(self, *args):
        """Handle updating the selection when the table is about to change, i.e., before sorting.
        """
        ...

    def _postChangeSelectionOrderCallback(self, *args):
        """Handle updating the selection when the table has been sorted.
        """
        model = self.model()
        selModel = self.selectionModel()
        selection = self.selectionModel().selectedIndexes()

        if model._sortIndex and model._oldSortIndex:
            # get the pre-sorted mapping
            if rows := {model._oldSortIndex[itm.row()] for itm in selection if itm.row() in model._oldSortIndex}:
                # block so nothing responds
                self.blockSignals(True)
                selModel.blockSignals(True)

                try:
                    newSel = QtCore.QItemSelection()
                    for row in rows:
                        if row in model._sortIndex:
                            # map to the new sort-order
                            idx = model.index(model._sortIndex.index(row), 0)
                            newSel.merge(QtCore.QItemSelection(idx, idx), QItemSelectionModel.Select)

                    # Select the cells in the data view - spawns single change event
                    self.selectionModel().select(newSel, QItemSelectionModel.Rows | QItemSelectionModel.ClearAndSelect)

                finally:
                    # unblock again
                    selModel.blockSignals(False)
                    self.blockSignals(False)

        self.blockSignals(True)
        try:
            # show all the hidden rows
            if hiddenRows := [row for row in range(self.rowCount()) if self.isRowHidden(row)]:
                for hRow in hiddenRows:
                    self.setRowHidden(hRow, False)

        finally:
            # unblock again
            self.blockSignals(False)

    def _tableSelectionChangedCallback(self):
        """Update columnHeader/indexheader when cells are selected in the main table.
        """
        columnHeader = self._columnHeader
        indexHeader = self._indexHeader

        if not columnHeader.hasFocus() and self.selectionBehavior() == self.SelectColumns:
            # select the columns in the horizontal-header
            selection = self.selectionModel().selectionIndexes()

            changed = _TableSelection(orientation=self.SelectColumns, rows=sorted({itm.col() for itm in selection}))
            self._tableSelectionChanged.emit(changed)

        if not indexHeader.hasFocus() and self.selectionBehavior() == self.SelectRows:
            # select the rows in the vertical-header
            selection = self.selectionModel().selectedIndexes()

            changed = _TableSelection(orientation=self.SelectRows, rows=sorted({itm.row() for itm in selection}))
            self._tableSelectionChanged.emit(changed)

    def sizeHint(self):
        # Set width and height based on number of columns in model
        # Width
        model = self.model()

        width = 2 * self.frameWidth()  # Account for border & padding
        # width += self.verticalScrollBar().width()  # Dark theme has scrollbars always shown
        for col in range(model.columnCount()):
            width += self.columnWidth(col)

        # Height
        height = 2 * self.frameWidth()  # Account for border & padding
        # height += self.horizontalScrollBar().height()  # Dark theme has scrollbars always shown
        for row in range(model.rowCount()):
            height += self.rowHeight(row)

        return QSize(width, height)

    #=========================================================================================
    # Implementation to match TableABC
    #=========================================================================================

    def showColumn(self, column, *args, **kwds):
        self.setColumnHidden(column, False)

    def hideColumn(self, column, *args, **kwds):
        self.setColumnHidden(column, True)

    def setRowHidden(self, row: int, hide: bool, skipUpdateWidth=False) -> None:
        """Set the row hidden for the table and the new header
        """
        super().setRowHidden(row, hide)

        self._indexHeader.setRowHidden(row, hide)
        if not hide:
            if skipUpdateWidth and self.rowHeight(row) > 0:
                return

            # resize and spawn paint-event
            self.resizeRowToContents(row)

    def setColumnHidden(self, column: int, hide: bool, skipUpdateWidth=False) -> None:
        """Set the column hidden for the table and the new header
        """
        super().setColumnHidden(column, hide)

        self._columnHeader.setColumnHidden(column, hide)
        if not hide:
            if skipUpdateWidth and self.columnWidth(column) > 0:
                return

            # resize and spawn paint-event
            self.resizeColumnToContents(column)

    def _columnChange(self, column: int, oldWidth: int, newWidth: int) -> None:
        # catch the column resize event and pass to the new header
        self._columnHeader.setColumnWidth(column, newWidth)

    def _rowChange(self, row: int, oldHeight: int, newHeight: int):
        # catch the row resize event and pass to the new header
        self._indexHeader.setRowHeight(row, newHeight)

    def _setHeaderWidgets(self, _height, showHorizontalHeader, showVerticalHeader, df):
        """Initialise the headers
        """
        # Create headers - was parent->self
        self._columnHeader = _HorizontalMITableHeaderView(parent=self, table=self, df=df, dividerColour=self._dividerColour)
        self._indexHeader = _VerticalMITableHeaderView(parent=self, table=self, df=df, dividerColour=self._dividerColour)

        # Link scrollbars
        # Scrolling in data table also scrolls the headers
        self.horizontalScrollBar().valueChanged.connect(self._columnHeader.horizontalScrollBar().setValue)
        self.horizontalScrollBar().rangeChanged.connect(self._columnHeader.horizontalScrollBar().setRange)
        self.horizontalHeader().sectionResized.connect(self._columnChange)

        self.verticalScrollBar().valueChanged.connect(self._indexHeader.verticalScrollBar().setValue)
        self.verticalScrollBar().rangeChanged.connect(self._indexHeader.verticalScrollBar().setRange)
        self.verticalHeader().sectionResized.connect(self._rowChange)

        # add widgets to fill the gaps around the sides - was parent->self
        self._topCornerWidget = _ScrollWidgetCorner(self, background='#F0F4F0')

        # set the horizontalHeader information
        for _parent in (self, self._columnHeader):
            _header = _parent.horizontalHeader()

            # set Interactive and last column to expanding
            _header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
            _header.setStretchLastSection(True)
            # only look at visible section
            _header.setResizeContentsPrecision(10)
            _header.setDefaultAlignment(QtCore.Qt.AlignLeft)
            _header.setMinimumSectionSize(20)
            _header.setVisible(False)

            setWidgetFont(_header, name=TABLEFONT)
            _header.setHighlightSections(self.font().bold())

        # set the verticalHeader information
        for _parent in (self, self._indexHeader):
            _header = _parent.verticalHeader()

            # set Interactive and last column to expanding
            _header.setStretchLastSection(False)
            # only look at visible section
            _header.setResizeContentsPrecision(5)
            _header.setDefaultAlignment(QtCore.Qt.AlignLeft)
            _header.setMinimumWidth(20)  # gives enough of a handle to resize if required
            _header.setVisible(False)

            setWidgetFont(_header, name=TABLEFONT)
            _header.setHighlightSections(self.font().bold())

            if self._rowHeightScale:
                # set the fixed row-height
                _header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
                _height *= self._rowHeightScale
            else:
                # otherwise user-changeable
                _header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)

            _header.setDefaultSectionSize(int(_height))
            _header.setMinimumSectionSize(int(_height))

    def setWidthToColumns(self):
        """Set the width of the table to the column widths
        """
        # need to get values from padding
        header = self._columnHeader  # horizontalHeader()
        width = -2  # left/right borders
        # +1 for cell border on right-hand-side
        width += sum((self.columnWidth(nn) + 1) for nn in range(header.count())
                     if not header.isSectionHidden(nn) and header.sectionViewportPosition(nn) >= 0)

        self.setFixedWidth(width)

    def setHeightToRows(self):
        """Set the height of the table to the row heights
        """
        height = 2 * self._columnHeader.height()

        header = self._indexHeader  # verticalHeader()
        for nn in range(header.count()):
            if not header.isSectionHidden(nn) and header.sectionViewportPosition(nn) >= 0:
                height += (self.rowHeight(nn) + 1)

        self.setFixedHeight(height)

    def setEditable(self, value):
        super(MITableABC, self).setEditable(value)

        with contextlib.suppress(Exception):
            # should use a proper method :|
            self._columnHeader.model()._defaultEditable = value

    #=========================================================================================
    # Header context menu
    #=========================================================================================

    def setHeaderMenu(self):
        """Set up the context menu for the table header
        """
        # need to pass to the new header
        self._thisTableHeaderMenu = menu = Menu('', self, isFloatWidget=True)
        setWidgetFont(menu, )

        # redirect the header to the new _columnHeader
        header = self._columnHeader
        header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._raiseHeaderContextMenu)

        self.addHeaderMenuOptions(menu)

        return menu

    #=========================================================================================
    # Other
    #=========================================================================================

    def updateGeometries(self) -> None:
        """Update the positions of the headers on resizing
        """
        super().updateGeometries()

        # set the left/top viewport to accommodate the new horizontal/vertical-headers
        ml, mt = self.contentsMargins().left(), self.contentsMargins().top()
        vw, vh = self.viewport().width(), self.viewport().height()
        iw = self._indexHeader.width() if self._indexHeader and self._indexHeader.isVisible() else 0
        ch = self._columnHeader.height() if self._columnHeader and self._columnHeader.isVisible() else 0

        geo = self.viewportMargins()
        geo.setTop(ch)
        geo.setLeft(iw)
        self.setViewportMargins(geo)

        # move the new headers to the correct positions in the viewport
        if self._indexHeader and iw:
            self._indexHeader.setGeometry(ml, ch + mt, iw, vh)

        if self._columnHeader and ch:
            self._columnHeader.setGeometry(iw + ml, mt, vw, ch)

        # move the top-left fill to the correct place, probably not strictly necessary
        if self._topCornerWidget not in [None, NOTHING]:
            self._topCornerWidget.setGeometry(ml, mt, iw, ch)
