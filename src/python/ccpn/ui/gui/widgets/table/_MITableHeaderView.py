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
__dateModified__ = "$dateModified: 2024-09-05 18:12:52 +0100 (Thu, September 05, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-01-27 14:45:57 +0100 (Fri, January 27, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import itertools
import typing
import numpy as np
import pandas as pd
from functools import partial
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, QItemSelectionModel, QSize
from PyQt5.QtWidgets import QSizePolicy

from ccpn.ui.gui.guiSettings import getColours, GUITABLEHEADER_GROUP_GRIDLINES, GUITABLE_GRIDLINES
from ccpn.ui.gui.widgets.table._TableCommon import MOUSE_MARGIN, ORIENTATIONS
from ccpn.ui.gui.widgets.Font import setWidgetFont, TABLEFONT

from ccpn.ui.gui.widgets.table._MITableDelegates import (_ExpandHorizontalDelegate, _ExpandVerticalDelegate,
                                                         _GridDelegate)
from ccpn.ui.gui.widgets.table._MITableHeaderModel import _HorizontalMITableHeaderModel, _VerticalMITableHeaderModel


#=========================================================================================
# _MITableHeaderViewABC
#=========================================================================================

class _MITableHeaderViewABC(QtWidgets.QTableView):
    """A model/view to show pandas DataFrames as a table.
    Allows for the use of single/multiIndex columns and indexes.

    The HeaderView defines the communication between the cells in the header and the model.
    """
    sectionClicked = QtCore.pyqtSignal(int)

    styleSheet = """QTableView {
                        background: qlineargradient(
                                        x1: 0, y1: -350, x2: 0, y2: 50,
                                        stop: 0 #8f8f8f, 
                                        stop: 1 palette(light)
                                    );
                        border: 0px;
                        border-radius: 0px;
                        gridline-color: %(_GRID_COLOR)s;
                        selection-background-color: qlineargradient(
                                                        x1: 0, y1: -350, x2: 0, y2: 50,
                                                        stop: 0 #8f8f8f, 
                                                        stop: 1 palette(light)
                                                    );;
                        selection-color: palette(text);
                        color: palette(text);
                        outline: 0px;
                    }
                    QTableView[selectionField=true] {
                        background: qlineargradient(
                                        x1: 0, y1: -350, x2: 0, y2: 50,
                                        stop: 0 #8f8f8f, 
                                        stop: 1 palette(light)
                                    );
                        border: 0px;
                        border-radius: 0px;
                        gridline-color: transparent;
                        /* use #f8f088 for yellow selection, or palette(highlight) */
                        selection-background-color: qlineargradient(
                                                        x1: 0, y1: -300, x2: 0, y2: 200,
                                                        stop: 0 palette(highlight), 
                                                        stop: 1 palette(light)
                                                    ); 
                        selection-color: palette(text);
                        color: palette(text);
                        outline: 0px;
                    }
                    QTableView::item {
                        padding: %(_CELL_PADDING)spx;
                        border-top: 1px solid qlineargradient(
                                        x1: 0, y1: -200, x2: 0, y2: 150,
                                        stop: 0 #8f8f8f, 
                                        stop: 1 palette(light)
                                    );
                        border-left: 1px solid qlineargradient(
                                        x1: 0, y1: -200, x2: 0, y2: 150,
                                        stop: 0 #8f8f8f, 
                                        stop: 1 palette(light)
                                    );
                    }
                    """

    headerModelClass = None
    headerDelegateClass = None

    showGroupDividers = True
    _dividerColour = None
    _horizontalDividers = None
    _verticalDividers = None

    def __init__(self, parent: 'MITableABC', table: '_MITableView', df, orientation=Qt.Horizontal, dividerColour=None,
                 gridColour=None):
        super().__init__(parent)

        # Setup
        if not isinstance(df, pd.DataFrame):
            raise ValueError('df must be a pd.DataFrame')
        orientation = ORIENTATIONS.get(orientation)
        if orientation is None:
            raise ValueError(f'orientation not in {list(ORIENTATIONS.keys())}')

        self.orientation = orientation
        # self._df = df

        self._parent = parent
        self.table = table
        self.setModel(self.headerModelClass(self.table, df=df, orientation=orientation))

        # These are used during row/column resizing
        self.header_being_resized = None
        self.resize_start_position = None
        self.initial_header_size = None
        self._lastCells = None
        self._lastSelected = None
        self._lastDeSelected = None
        self._lastIndex = None
        self._lastIndexChanged = None
        self._mousePressed = False

        self.viewport().setMouseTracking(True)

        # set selection behaviour to only items
        self.setSelectionBehavior(self.SelectItems)
        self.setAlternatingRowColors(False)

        # Settings
        self.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum))
        self.setWordWrap(False)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)

        # Link selection to DataTable
        self.selectionModel().selectionChanged.connect(self._headerSelectionChangedCallback)

        # add border-width/cell-padding options
        cols = self._colours = {}  #getColours()
        self._borderWidth = cols['_BORDER_WIDTH'] = 0
        # self._frameBorderWidth = 1
        self._cellPadding = cols['_CELL_PADDING'] = 2  # the extra padding for the selected cell-item
        try:
            col = QtGui.QColor(gridColour).name() if gridColour else 'palette(mid)'
        except Exception:
            # grid colour may be ill-defined
            col = 'palette(mid)'
        self._gridColour = cols['_GRID_COLOR'] = col
        self._checkPalette()
        setWidgetFont(self, name=TABLEFONT)

        if self.headerDelegateClass:
            # single delegate handles both sort-icon and horizontal expand-icons
            delegate = self.headerDelegateClass(self, table=table, focusBorderWidth=0)
            self.setItemDelegate(delegate)

        self._dividerColour = (dividerColour and QtGui.QColor(dividerColour)) or QtGui.QColor(
                getColours()[GUITABLEHEADER_GROUP_GRIDLINES])

        # property works here and allows stylesheet to apply selection colour
        self.setProperty('selectionField', False)
        QtWidgets.QApplication.instance().sigPaletteChanged.connect(
                partial(QtCore.QTimer.singleShot, 0, self._checkPalette))

    def _checkPalette(self):
        """Update palette in response to palette change event.
        """
        self.setStyleSheet(self.styleSheet % self._colours)

    @property
    def _df(self):
        """Return the dataFrame associated with the table.
        """
        return self.model()._df

    def _init(self):
        self.setSpans()
        self.initSize()
        self.setDelegates()

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
                model = self.headerModelClass(self.table, df, self.orientation)

                self.setModel(model)
            else:
                model.df = df

        else:
            # set a default empty model
            df = pd.DataFrame({})
            if newModel or not (model := self.model()):
                # create a new model if required
                model = self.headerModelClass(self.table, df, self.orientation)

                self.setModel(model)
            else:
                model.df = df

        self._init()

        return model

    def _finalise(self):
        """Finalise handling the header selection.
        """
        # unblock signals
        self.blockSignals(False)
        self.selectionModel().blockSignals(False)
        self._blocking = False

        # refresh the display
        self.repaint()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """handle key-presss events
        """
        # reset the last-index changed to respond to selection change
        self._lastIndex = None
        self._lastIndexChanged = True

        super().keyPressEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle the mouse-press event.
        """
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        """Handle mouse-release event
        """
        super().mouseReleaseEvent(e)

        # reset the last-index changed to respond to selection change
        self._mousePressed = False
        self.header_being_resized = None
        self.setSelectionMode(self._lastMode)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle the mouse-move event
        """
        super().mouseMoveEvent(event)

    def initSize(self):
        """Fit rows/columns to contents
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def setDelegates(self):
        """Set delegates for the header
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def _setSpans(self, headers):
        self.clearSpans()

        self._horizontalDividers = []
        self._verticalDividers = []

        # find the horizontal spans
        for ii in range(headers.shape[0] - 1):
            startCol = 0
            for col in range(1, headers.shape[1]):
                if headers[ii, col] == headers[ii, col - 1]:
                    if col == headers.shape[1] - 1:
                        # last column
                        if self.orientation == Qt.Horizontal:
                            self.setSpan(ii, startCol, 1, col - startCol + 1)
                            if ii == 0:
                                self._horizontalDividers.extend([startCol, col + 1])
                        else:
                            self.setSpan(startCol, ii, col - startCol + 1, 1)
                            if ii == 0:
                                self._verticalDividers.extend([startCol, col + 1])
                else:
                    if col - startCol > 1:
                        if self.orientation == Qt.Horizontal:
                            self.setSpan(ii, startCol, 1, col - startCol)
                            if ii == 0:
                                self._horizontalDividers.extend([startCol, col])
                        else:
                            self.setSpan(startCol, ii, col - startCol, 1)
                            if ii == 0:
                                self._verticalDividers.extend([startCol, col])
                    startCol = col

        # find the vertical spans
        for ii in range(headers.shape[1]):
            startRow = 0
            for row in range(1, headers.shape[0]):
                if headers[row, ii] == headers[row - 1, ii]:
                    if row == headers.shape[0] - 1:
                        # last column
                        if self.orientation == Qt.Vertical:
                            self.setSpan(ii, startRow, 1, row - startRow + 1)
                        else:
                            self.setSpan(startRow, ii, row - startRow + 1, 1)
                else:
                    if row - startRow > 1:
                        if self.orientation == Qt.Vertical:
                            self.setSpan(ii, startRow, 1, row - startRow)
                        else:
                            self.setSpan(startRow, ii, row - startRow, 1)
                    startRow = row

    def setSpan(self, row: int, column: int, rowSpan: int, columnSpan: int) -> None:
        """Set the span and set the top-left index for each cell in the span
        """
        super().setSpan(row, column, rowSpan, columnSpan)

        model = self.model()
        for rr, cc in itertools.product(range(rowSpan), range(columnSpan)):
            # store the top-left cell in all the cells of the group
            model._spanTopLeft[row + rr, column + cc] = (row, column)

    def clearSpans(self) -> None:
        """Clear the spans
        """
        super().clearSpans()

        # clear the span information held in the header
        self.model().clearSpans()

    def overHeaderEdge(self, mouse_position, margin=MOUSE_MARGIN):
        """Check whether the mouse is over a row/column-divider
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def sizeHint(self):
        """Return the size of the header to match the corresponding DataTableView.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def minimumSizeHint(self):
        """Return the minimum size for the widget.
        This is needed, otherwise, when the horizontal header is a single row it will add whitespace to be bigger.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")


#=========================================================================================
# _HorizontalMITableHeaderView
#=========================================================================================

class _HorizontalMITableHeaderView(_MITableHeaderViewABC):
    """A model/view to show pandas DataFrames as a table.
    Allows for the use of single/multiIndex columns and indexes.

    The HeaderView defines the communication between the cells in the header and the model.
    This is the horizontal-header
    """
    headerModelClass = _HorizontalMITableHeaderModel
    headerDelegateClass = _ExpandHorizontalDelegate

    def __init__(self, parent: 'MITableABC', table: '_MITableView', df: typing.Optional[pd.DataFrame],
                 dividerColour=None):
        super().__init__(parent, table, df, orientation=Qt.Horizontal, dividerColour=dividerColour)

        # Setup
        if type(df.columns) == pd.MultiIndex and df.columns.nlevels <= 1:
            raise ValueError('Cannot have multiIndex header with only one level')

        # add delegates to show sort indicator
        self.setDelegates()

        # don't need to see my own headers
        self.horizontalHeader().hide()
        self.horizontalHeader().setDisabled(True)
        self.verticalHeader().hide()
        self.verticalHeader().setDisabled(True)
        self.verticalHeader().setHighlightSections(False)  # Selection lags a lot without this

        # Toggle level names
        if not (any(df.columns.names) or df.columns.name):
            self.verticalHeader().setFixedWidth(0)

        # Scrolling in headers also scrolls the main-table - hidden scroll-bars still contain the positional information
        self.horizontalScrollBar().valueChanged.connect(self._parent.horizontalScrollBar().setValue)

        # constrain the size of the header
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

    def setDelegates(self):
        """Set the delegates for the rows.
        Upper rows need to show the expand-icons, last row needs to hold the editable and sort icons
        """
        ...

    def _headerSelectionChangedCallback(self, selected, deSelected):
        """Handle when columns/rows are selected in the headers.
        Select items in dataView as necessary.
        """
        if self.hasFocus():
            selModel = self.selectionModel()

            # Horizontal column/multiIndex header
            if self.table.selectionBehavior() != self.SelectColumns:
                # skip the horizontal header if not in SelectColumns mode
                return

            try:
                # block signals from the header table
                self.blockSignals(True)
                selModel.blockSignals(True)

                self._processColumnSelection()

            finally:
                # re-enable the table
                QtCore.QTimer.singleShot(0, self._finalise)

    def _processColumnSelection(self):
        """Update the main table selection from the horizontalHeader selection.
        Selections are columns.
        """
        selModel = self.selectionModel()
        dataView = self._parent

        # Get the header's selected columns
        indexes = [ind for ind in selModel.selectedIndexes()
                   if not self.horizontalHeader().isSectionHidden(ind.column())]

        if sCol := {idx.column() for idx in indexes}:
            lastIdx = self._df.columns.nlevels - 1
            newSel = QtCore.QItemSelection()

            # find all the selected cell spans
            found = set()
            for idx in indexes:
                row, col = idx.row(), idx.column()
                if (row, col) not in found:
                    rowSpan, colSpan = self.rowSpan(row, col), self.columnSpan(row, col)
                    found |= {(row + rr, col + cc) for rr in range(rowSpan) for cc in range(colSpan)
                              if not self.horizontalHeader().isSectionHidden(col + cc)}

            # create a merged selection of indexes
            foundCols = {col for row, col in found}
            for col in foundCols:
                idx = self.model().index(lastIdx, col)
                newSel.merge(QtCore.QItemSelection(idx, idx), QItemSelectionModel.Select)

            # set the header selection
            for row, col in found:
                for rr in range(row + 1, lastIdx + 1):
                    idx2 = self.model().index(rr, col)
                    self.setSelection(self.visualRect(idx2), QItemSelectionModel.Select)

            # Select the cells in the data view - spawns single change event
            dataView.selectionModel().select(newSel, QItemSelectionModel.Columns | QItemSelectionModel.ClearAndSelect)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle double-click to minimise/maximise the width of clicked column
        """
        super().mouseDoubleClickEvent(event)

        posX, posY = event.pos().x(), event.pos().y()
        if (self.rowAt(posY) == self._df.columns.nlevels - 1) and (index := self.columnAt(posX)) >= 0:
            if self._parent.columnWidth(index) > self.horizontalHeader().minimumSectionSize():
                self._parent.setColumnWidth(index, self.horizontalHeader().minimumSectionSize())
            else:
                self._parent.resizeColumnToContents(index)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle the mouse-press event.
        """
        # reset the last-index changed to respond to selection change
        self._lastIndex = None
        self._lastIndexChanged = True
        self._mousePressed = True
        self._lastMode = self.selectionMode()

        # initialise mouse-press for resizing rows/columns
        mouse_position = event.pos()

        if (overEdge := self.overHeaderEdge(mouse_position)) is not None:
            # mouse is over an edge
            self.header_being_resized = overEdge

            # get the mouse-position for the header orientation
            pos = mouse_position.x()
            self.resize_start_position = pos
            self.initial_header_size = self.columnWidth(self.header_being_resized)

            # remember the last mode to handle press/release selection
            self.setSelectionMode(self.NoSelection)
            self.sectionClicked.emit(overEdge)

        else:
            self.header_being_resized = None

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle the mouse-move event
        """
        # get the mouse-position for the header orientation
        mouse_position = event.pos()

        # If this is None, there is no drag resize happening
        if self.header_being_resized is not None:

            # get the mouse-position for the header orientation
            pos = mouse_position.x()

            size = self.initial_header_size + (pos - self.resize_start_position)
            if size > 10:
                self._parent.setColumnWidth(self.header_being_resized, size)

        # Set the cursor shape
        if self.overHeaderEdge(mouse_position) is None:
            self.viewport().setCursor(QtGui.QCursor(Qt.ArrowCursor))
        else:
            self.viewport().setCursor(QtGui.QCursor(Qt.SplitHCursor))

        ind = self.indexAt(event.pos())
        if ind != self._lastIndex:
            if self._mousePressed:
                self._lastIndex = ind
                self._lastIndexChanged = True

            # required to handle the mouse-drag for selection, but only if cell-index has changed
            super().mouseMoveEvent(event)

    def _processSelectionFromColumns(self, columns: typing.List[int]):
        """Update the horizontal-header selection from the main-table selection.

        Selection is defined by the list of integers.
        Columns outside the range of the table are discarded.

        :param columns: list of columns to select.
        :return:
        """
        if not columns:
            self.clearSelection()
            return

        if not (isinstance(columns, list) and all(isinstance(val, int) for val in columns)):
            raise TypeError(
                    f'{self.__class__.__name__}._processSelectionFromColumns: columns is not a list of integers')

        # get the valid visible items
        sCol = {col for col in columns if
                0 <= col < self.model().columnCount() and not self.horizontalHeader().isSectionHidden(col)}

        self.clearSelection()
        if sCol:
            lastIdx = self._df.columns.nlevels - 1

            # find all the selected cell spans
            found = set()
            for col in sCol:
                row = lastIdx
                if (row, col) not in found:
                    rowSpan, colSpan = self.rowSpan(row, col), self.columnSpan(row, col)
                    found |= {(row + rr, col + cc) for rr in range(rowSpan) for cc in range(colSpan)
                              if not self.horizontalHeader().isSectionHidden(col + cc)}

            for row in range(lastIdx - 1, -1, -1):
                for col in sCol:
                    if (cellSpan := (self.model()._spanTopLeft[row, col] or (row, col))):
                        _, cellCol = cellSpan
                        _, colSpan = self.rowSpan(row, col), self.columnSpan(row, col)

                        cells = {(row + 1, cellCol + cc) for cc in range(colSpan)}
                        if all(cell in found for cell in cells):
                            found |= {(row, cellCol + cc) for cc in range(colSpan)}

            # set the header selection
            for row, col in found:
                for rr in range(row, lastIdx + 1):
                    idx2 = self.model().index(rr, col)
                    self.setSelection(self.visualRect(idx2), QItemSelectionModel.Select)

    def initSize(self):
        """Fit columns to contents
        """
        self.resizeRowsToContents()

    def setSpans(self):
        """Group together all identical items in the column/index multiIndex.
        The structure of the index/column is preserved.
        """
        # signal that the header has changed
        self.model().layoutAboutToBeChanged.emit()

        df = self.model().df

        # Find how many levels the MultiIndex has
        cols = len(df.columns[0]) if type(df.columns) == pd.MultiIndex else 1
        headers = np.empty((cols, len(df.columns)), dtype=object)
        for level in range(cols):  # Iterates over the levels
            # Find how many segments the MultiIndex has
            headers[level, :] = [df.columns[i][level] for i in range(len(df.columns))] if type(
                    df.columns) == pd.MultiIndex else df.columns

        self._setSpans(headers)

        # signal that the header has changed
        self.model().layoutChanged.emit()

    def overHeaderEdge(self, mouse_position, margin=MOUSE_MARGIN):
        """Check whether the mouse is over a column-divider
        """
        # get the mouse-position
        x, y = mouse_position.x(), mouse_position.y()
        model = self.model()

        # Return the index of the column this x position is on the right edge of
        row, col1, col2 = self.rowAt(y), self.columnAt(x - margin), self.columnAt(x + margin)

        if (col1 != col2 and col2 == 0) or col1 == col2:
            # We're at the left edge of the first column
            return None

        # check that the adjacent cells are from the same cell-span and one of the middle edges
        #  - this accounts for hidden sections
        _cellRow1, cellCol1 = model._spanTopLeft[row, col1] or (row, col1)
        _cellRow2, cellCol2 = model._spanTopLeft[row, col2] or (row, col2)
        _rowSpan, colSpan = self.rowSpan(row, col2), self.columnSpan(row, col2)

        if (cellCol1 == cellCol2) and (0 < col2 < cellCol2 + colSpan):
            return None

        return self.columnAt(x - margin)

    def sizeHint(self):
        """Return the size of the header needed to match the corresponding DataTableView.
        """
        _model = self.model()

        # Width of DataTableView
        width = self.table.sizeHint().width() + self.verticalHeader().width()
        # Height
        height = 2 * self.frameWidth()  # Account for border & padding
        for i in range(_model.rowCount()):
            height += self.rowHeight(i)

        return QSize(width, height)

    def updateDf(self, df, resize=True, setHeightToRows=False, setWidthToColumns=False, setOnHeaderOnly=False,
                 newModel=False):
        """Initialise the dataFrame
        """
        super().updateDf(df, resize, setHeightToRows, setWidthToColumns, setOnHeaderOnly, newModel)

        self._parent.resizeRowsToContents()
        h = sum(self.rowHeight(row) for row in range(df.shape[0]))

        # strange - but this is needed here :|
        self.setFixedHeight(h)

    def minimumSizeHint(self):
        """Return the minimum size for the widget.
        This is needed because otherwise when the horizontal header is a single row it will add whitespace to be bigger.
        """
        return QSize(0, self.sizeHint().height())

    def _vs(self, row, col):
        """Return True if the icon can be displayed, i.e., the span is larger than one.
        """
        _rowSpan, colSpan = self.rowSpan(row, col), self.columnSpan(row, col)
        count = 0
        # count how may columns are visible
        for cc in range(colSpan):
            count += (0 if self.horizontalHeader().isSectionHidden(col + cc) else 1)

        # return - can maximise/minimise
        return (count < colSpan), (count > 1)

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        """Paint the border to the screen
        """
        super().paintEvent(e)
        if not self.showGroupDividers:
            return

        if self._horizontalDividers:
            # create a rectangle and painter over the widget - shrink by 1 pixel to draw correctly
            p = QtGui.QPainter(self.viewport())
            p.translate(0.5, 0.5)
            offset = -self.horizontalScrollBar().value() if self.horizontalScrollBar() else 0
            h = self.rect().height()
            p.setPen(QtGui.QPen(self._dividerColour, 1))
            pos = offset - 1
            for col in range(self.model().columnCount()):
                if col in self._horizontalDividers:
                    p.drawLine(pos, 0, pos, h)
                pos += self.columnWidth(col)
            p.end()


#=========================================================================================
# _VerticalMITableHeaderView
#=========================================================================================

class _VerticalMITableHeaderView(_MITableHeaderViewABC):
    """A model/view to show pandas DataFrames as a table.
    Allows for the use of single/multiIndex columns and indexes.

    The HeaderView defines the communication between the cells in the header and the model.
    This is the vertical-header
    """
    headerModelClass = _VerticalMITableHeaderModel

    def __init__(self, parent: 'MITableABC', table: '_MITableView', df: typing.Optional[pd.DataFrame],
                 dividerColour=None):
        super().__init__(parent, table, df, orientation=Qt.Vertical, dividerColour=dividerColour)

        # Setup
        if type(df.index) == pd.MultiIndex and df.index.nlevels <= 1:
            raise ValueError('Cannot have multiIndex header with only one level')

        self.setDelegates()

        # don't need to see my own headers
        self.verticalHeader().hide()
        self.verticalHeader().setDisabled(True)
        self.horizontalHeader().hide()
        self.horizontalHeader().setDisabled(True)
        self.horizontalHeader().setHighlightSections(False)  # Selection lags a lot without this

        # Toggle level names
        if not (any(df.index.names) or df.index.name):
            self.horizontalHeader().setFixedHeight(0)

        # Scrolling in headers also scrolls the main-table - hidden scroll-bars still contain the positional information
        self.verticalScrollBar().valueChanged.connect(self._parent.verticalScrollBar().setValue)

        # constrain the size of the header
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        # change ordering of the header if the row-order has changed
        self.model().layoutChanged.connect(self._changeSelectionOrderCallback)

    def setDelegates(self):
        """Set the delegates for the rows.
        """
        df = self._df
        lastIdx = (df.index.nlevels - 1) if type(df.index) == pd.MultiIndex else 0

        if lastIdx:
            table = self.table

            delegate = _ExpandVerticalDelegate(self, table=table, focusBorderWidth=0)
            for col in range(lastIdx):
                # add delegates to show expand/collapse icon
                self.setItemDelegateForColumn(col, delegate)

            delegate = _GridDelegate(self)
            # add delegate to show modified grid-lines
            self.setItemDelegateForColumn(lastIdx, delegate)

    def _headerSelectionChangedCallback(self, selected, deSelected):
        """Handle when columns/rows are selected in the headers.
        Select items in dataView as necessary.
        """
        selected = sorted({(ind.row(), ind.column()) for ind in self.selectionModel().selectedIndexes()})

        if self.hasFocus():
            selModel = self.selectionModel()

            # Vertical index/multiIndex header
            if self.table.selectionBehavior() != self.SelectRows:
                # skip the vertical header if not in SelectRows mode
                return

            try:
                if getattr(self, '_lastIndexChanged', None):
                    self._lastIndexChanged = False
                    self._processRowSelection(selected, deSelected)

            finally:
                # re-enable the table
                QtCore.QTimer.singleShot(QtWidgets.QApplication.instance().doubleClickInterval(), self._finalise)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle double-click to minimise/maximise the width of clicked column
        """
        super().mouseDoubleClickEvent(event)

        posX, posY = event.pos().x(), event.pos().y()
        if (self.columnAt(posX) == self._df.index.nlevels - 1) and (index := self.rowAt(posY)) >= 0:
            if self._parent.rowHeight(index) > self.verticalHeader().minimumSectionSize():
                self._parent.setRowHeight(index, self.verticalHeader().minimumSectionSize())
            else:
                self._parent.resizeRowToContents(index)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle the mouse-press event.
        """
        # reset the last-index changed to respond to selection change
        self._lastIndex = None
        self._lastIndexChanged = True
        self._mousePressed = True
        self._lastMode = self.selectionMode()

        # initialise mouse-press for resizing rows/columns
        mouse_position = event.pos()

        if (overEdge := self.overHeaderEdge(mouse_position)) is not None:
            # mouse is over an edge
            self.header_being_resized = overEdge

            # get the mouse-position for the header orientation
            pos = mouse_position.y()
            self.resize_start_position = pos

            self.initial_header_size = self.rowHeight(self.header_being_resized)

            # remember the last mode to handle press/release selection
            self.setSelectionMode(self.NoSelection)
            self.sectionClicked.emit(overEdge)

        else:
            self.header_being_resized = None

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle the mouse-move event
        """
        # get the mouse-position for the header orientation
        mouse_position = event.pos()  # .x() if self.orientation == Qt.Horizontal else event.pos().y()

        # If this is None, there is no drag resize happening
        if self.header_being_resized is not None:

            # get the mouse-position for the header orientation
            pos = mouse_position.y()

            size = self.initial_header_size + (pos - self.resize_start_position)
            if size > 10:
                self._parent.setRowHeight(self.header_being_resized, size)

        # Set the cursor shape
        if self.overHeaderEdge(mouse_position) is None:
            self.viewport().setCursor(QtGui.QCursor(Qt.ArrowCursor))
        else:
            self.viewport().setCursor(QtGui.QCursor(Qt.SplitVCursor))

        ind = self.indexAt(event.pos())
        if ind != self._lastIndex:
            if self._mousePressed:
                self._lastIndex = ind
                self._lastIndexChanged = True

            # required to handle the mouse-drag for selection, but only if cell-index has changed
            super().mouseMoveEvent(event)

    def _processRowSelection(self, selected, deSelected):
        """Update the main table selection from the verticalHeader selection.
        Selections are rows.

        selected/deSelected are lists of (row, col) tuples for the clicked cells.

        :param selected: selected indexes
        :param deSelected: deselected indexes
        :return:
        """
        selModel = self.selectionModel()
        dataView = self._parent
        lastIdx = self._df.index.nlevels - 1

        indexes = {(ind.row(), ind.column()) for ind in selModel.selectedIndexes() if
                   not self.verticalHeader().isSectionHidden(ind.row())}

        if sRow := {row for row, _col in indexes}:
            dataViewSel = QtCore.QItemSelection()
            selfSel = QtCore.QItemSelection()

            # find all the selected cell spans
            found = set()
            for row, col in indexes:
                cellSpan = self.model()._spanTopLeft[row, col] or (row, col)
                cellRow, cellCol = cellSpan
                rowSpan, colSpan = self.rowSpan(row, col), self.columnSpan(row, col)
                newCells = {(cellRow + rr, cc) for rr in range(rowSpan) for cc in range(cellCol, lastIdx + 1)
                            if not self.verticalHeader().isSectionHidden(cellRow + rr)}
                found |= newCells

            for col in range(lastIdx - 1, -1, -1):
                for row in sRow:
                    if (cellSpan := (self.model()._spanTopLeft[row, col] or (row, col))):
                        cellRow, _cellCol = cellSpan
                        rowSpan, _rowCol = self.rowSpan(row, col), self.columnSpan(row, col)

                        cells = {(cellRow + rr, col + 1) for rr in range(rowSpan)}
                        if all(cell in found for cell in cells):
                            found |= {(cellRow + rr, col) for rr in range(rowSpan)}

            # create a merged selection of indexes for the data-view (main table)
            for row, col in found:
                idx = dataView.model().index(row, col)
                dataViewSel.merge(QtCore.QItemSelection(idx, idx), QItemSelectionModel.Select)

            # set the header selection
            for row, col in found:
                for cc in range(col, lastIdx + 1):
                    idx = self.model().index(row, cc)
                    selfSel.merge(QtCore.QItemSelection(idx, idx), QItemSelectionModel.Select)

            # select in a single operation
            selModel.select(selfSel, QItemSelectionModel.ClearAndSelect)

            # Select the cells in the data-view - spawns single change event
            dataView.selectionModel().select(dataViewSel, QItemSelectionModel.Rows | QItemSelectionModel.ClearAndSelect)

        else:
            self.clearSelection()
            dataView.clearSelection()

    def _processSelectionFromRows(self, rows: typing.List[int]):
        """Update the vertical-header selection from the main-table selection.

        Selection is defined by the list of integers.
        Rows outside the range of the table are discarded.

        :param rows: list of rows to select.
        :return:
        """
        if not rows:
            self.clearSelection()
            return

        if not (isinstance(rows, list) and all(isinstance(val, int) for val in rows)):
            raise TypeError(f'{self.__class__.__name__}._processSelectionFromRows: rows is not a list of integers')

        # get the valid visible items
        sRow = {row for row in rows if
                0 <= row < self.model().rowCount() and not self.verticalHeader().isSectionHidden(row)}

        self.clearSelection()
        if sRow:
            lastIdx = self._df.index.nlevels - 1

            # find all the selected cell spans
            found = set()
            for row in sRow:
                col = lastIdx
                if (row, col) not in found:
                    rowSpan, colSpan = self.rowSpan(row, col), self.columnSpan(row, col)
                    found |= {(row + rr, col + cc) for rr in range(rowSpan) for cc in range(colSpan)
                              if not self.verticalHeader().isSectionHidden(row + rr)}

            for col in range(lastIdx - 1, -1, -1):
                for row in sRow:
                    if (cellSpan := (self.model()._spanTopLeft[row, col] or (row, col))):
                        cellRow, _ = cellSpan
                        rowSpan, _ = self.rowSpan(row, col), self.columnSpan(row, col)

                        cells = {(cellRow + rr, col + 1) for rr in range(rowSpan)}
                        if all(cell in found for cell in cells):
                            found |= {(cellRow + rr, col) for rr in range(rowSpan)}

            # set the header selection
            for row, col in found:
                for cc in range(col, lastIdx + 1):
                    idx2 = self.model().index(row, cc)
                    self.setSelection(self.visualRect(idx2), QItemSelectionModel.Select)

    def _changeSelectionOrderCallback(self):
        """Handle the change of order of items in the dataView.
        """
        model = self.model()
        selModel = self.selectionModel()
        pSelModel = self._parent.selectionModel()
        if self.table.selectionBehavior() != self.SelectRows:
            # skip the vertical header if not in SelectRows mode
            return

        # block signals from the header table
        self.blockSignals(True)
        selModel.blockSignals(True)

        # # Get the main dataView selected rows
        # indexes = [ind for ind in pSelModel.selectedIndexes()
        #            if not self.verticalHeader().isSectionHidden(ind.row())]

        # find all the cells highlighted in the lowest level of the multiIndex
        lastIdx = (self._df.index.nlevels - 1) if type(self._df.index) == pd.MultiIndex else 0
        indexes = [ind for ind in pSelModel.selectedIndexes() if ind.column() == lastIdx]

        if found := {(idx.row(), lastIdx) for idx in indexes}:
            # find all the higher groups that contain all selected children
            for col in range(lastIdx - 1, -1, -1):
                for row in range(self._df.shape[0]):
                    rowSpan, colSpan = self.rowSpan(row, col), self.columnSpan(row, col)
                    if all((row + rr, lastIdx) in found for rr in range(rowSpan) if
                           not self.verticalHeader().isSectionHidden(row + rr)):
                        found.add((row, col))
                        found |= {(row + rr, lastIdx) for rr in range(rowSpan) if
                                  not self.verticalHeader().isSectionHidden(row + rr)}

            # create a merged selection of indexes
            newSel = QtCore.QItemSelection()
            for row, col in found:
                idx = model.index(row, col)
                newSel.merge(QtCore.QItemSelection(idx, idx), QItemSelectionModel.Select)

            # Select the cells in the data view
            selModel.select(newSel, QItemSelectionModel.ClearAndSelect)

        QtCore.QTimer.singleShot(0, self._finalise)

    def initSize(self):
        self.resizeColumnsToContents()

    def setSpans(self):
        """Group together all identical items in the column/index multiIndex.
        The structure of the index/column is preserved.
        """
        # signal that the header has changed
        self.model().layoutAboutToBeChanged.emit()

        df = self.model().df

        _sortIndex = self.table.model()._sortIndex

        # Find how many levels the MultiIndex has
        rows = len(df.index[0]) if type(df.index) == pd.MultiIndex else 1
        headers = np.empty((rows, len(df.index)), dtype=object)
        for level in range(rows):  # Iterates over the levels
            # Find how many segments the MultiIndex has
            headers[level, :] = [df.index[_sortIndex[i]][level] for i in range(len(df.index))] if type(
                    df.index) == pd.MultiIndex else df.index

        self._setSpans(headers)

        # signal that the header has changed
        self.model().layoutChanged.emit()

    def overHeaderEdge(self, mouse_position, margin=MOUSE_MARGIN):
        """Check whether the mouse is over a row-divider
        """
        # get the mouse-position
        x, y = mouse_position.x(), mouse_position.y()
        model = self.model()

        # Return the index of the row this x position is above
        row1, row2, col = self.rowAt(y - margin), self.rowAt(y + margin), self.columnAt(x)

        if (row1 != row2 and row2 == 0) or row1 == row2:
            # We're at the top edge of the first row
            return None

        # check that the adjacent cells are from the same cell-span and one of the middle edges
        #  - this accounts for hidden sections
        cellRow1, _cellCol1 = model._spanTopLeft[row1, col] or (row1, col)
        cellRow2, _cellCol2 = model._spanTopLeft[row2, col] or (row2, col)
        rowSpan, _colSpan = self.rowSpan(row2, col), self.columnSpan(row2, col)

        if (cellRow1 == cellRow2) and (0 < row2 < cellRow2 + rowSpan):
            return None

        return self.rowAt(y - margin)

    def sizeHint(self):
        """Return the size of the header needed to match the corresponding DataTableView.
        """
        _model = self.model()

        # Height of DataTableView
        height = self.table.sizeHint().height() + self.horizontalHeader().height()
        # Width
        width = 2 * self.frameWidth()  # Account for border & padding
        for i in range(_model.columnCount()):
            width += self.columnWidth(i)

        return QSize(width, height)

    def minimumSizeHint(self):
        """Return the minimum size for the widget.
        This is needed because otherwise when the horizontal header is a single row it will add whitespace to be bigger.
        """
        return QSize(self.sizeHint().width(), 0)

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        """Paint the border to the screen
        """
        super().paintEvent(e)
        if not self.showGroupDividers:
            return

        if self._verticalDividers:
            # create a rectangle and painter over the widget - shrink by 1 pixel to draw correctly
            p = QtGui.QPainter(self.viewport())
            offset = -self.verticalScrollBar().value() if self.verticalScrollBar() else 0
            w = self.rect().width()

            p.setPen(QtGui.QPen(self._dividerColour, 1))
            pos = offset - 1
            for row in range(self.model().rowCount()):
                if row in self._verticalDividers:
                    p.drawLine(0, pos, w, pos)
                pos += self.rowHeight(row)

            p.end()
