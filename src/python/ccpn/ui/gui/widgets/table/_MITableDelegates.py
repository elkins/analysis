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
__dateModified__ = "$dateModified: 2024-09-13 15:20:23 +0100 (Fri, September 13, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-01-18 15:25:31 +0100 (Wed, January 18, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt

from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.table._TableCommon import EDIT_ROLE, BORDER_ROLE, _EDITOR_SETTER, _EDITOR_GETTER
from ccpn.util.Logging import getLogger


#=========================================================================================
# Table delegates - _ExpandDelegate
#=========================================================================================

class _ExpandDelegateABC(QtWidgets.QStyledItemDelegate):
    """Class to add an expand/collapse icon to the right-hand-side of a QTableView cell.

    A delegate that can be used in subclassed pandas dataFrame tables that have single or multi-level columns/indexes.
    Icon is visible for all cells that have a cell-span.
    Clicking the icon opens/closes the extra cells in the span.
    """
    buttonClicked = QtCore.pyqtSignal(QtCore.QModelIndex, int)

    _ICONSIZE = 16
    _HBORDER = 4
    _VBORDER = 4

    _focusBorderWidth = 1
    _focusPen = None

    def __init__(self, parent, *, table=None, focusBorderWidth=1):
        """Initialise the class.

        parent is the subclassed QTableView - controls the multi-level view capability for the table header.
        table is the subclassed QTableView - controls the view for the main table.

        Assumes that the orientation is horizontal - vertical not required yet.

        :param parent: QtWidgets.QTableView.
        :param table: QtWidgets.QTableView.
        """
        super().__init__(parent)

        self._parent = parent
        self._table = table
        self._mousePress = False
        self._expandedSections = {}

        # define expand/collapse icons for the active cell
        self._minusIcon = Icon('icons/minus-large')
        self._plusIcon = Icon('icons/plus-large')

        # set the colours
        self._focusPen = QtGui.QPen(QtGui.QPalette().highlight().color(), 2)
        # double the line-widths accounts for the device-pixel-ratio
        self._focusBorderWidth = focusBorderWidth
        self._focusPen.setWidthF(focusBorderWidth * 2.0)
        self._focusPen.setJoinStyle(QtCore.Qt.MiterJoin)  # square ends

    def editorEvent(self, event, model, option, index):
        """Handle clicking the icon.
        """
        # If the event is a click event
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # check of the mouse-press is on the icon
            if self._iconRect(option).contains(event.pos()):
                self._mousePress = True

        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            self._mousePress = False

            buttonOffset = 0
            # search through the buttons to find which is pressed
            for visibleButton, state in enumerate(self._validSpans(index)):
                if state:
                    # check if the mouse-press is on the icon
                    if self._iconRect(option, buttonOffset).contains(event.pos()):
                        self._iconCallback(index, visibleButton)
                        return True

                    buttonOffset += 1

        return super().editorEvent(event, model, option, index)

    def _iconRect(self, option, buttonOffset=0):
        """Get the co-ordinates of the icon at the button position.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def _iconCallback(self, index, visibleButton):
        """Process the clicked icon.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")

    def _validSpans(self, index):
        """Return True if the icon can be displayed, i.e., the span is larger than one.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")


class _ExpandHorizontalDelegate(_ExpandDelegateABC):
    """Class to add an expand/collapse icon to the right-hand-side of a QTableView cell.

    A delegate that can be used in subclassed pandas dataFrame tables that have single or multi-level columns/indexes.
    Icon is visible for all cells that have a cell-span.
    Clicking the icon opens/closes the extra cells in the span.
    """
    _SORTICONSIZE = 12
    _HBORDER = 4
    _VBORDER = 4

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

        self._sortedColumns = {}
        self._sortEnabled = True

        self._downIcon = Icon('icons/caret-grey-down')
        self._upIcon = Icon('icons/caret-grey-up')
        self._downIconLight = Icon('icons/caret-light-down')
        self._upIconLight = Icon('icons/caret-light-up')

    def editorEvent(self, event, model, option, index):
        """Handle clicking the icon.
        """
        # If the event is a click event
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # check of the mouse-press is on the icon
            if self._iconRect(option).contains(event.pos()):
                self._mousePress = True

        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            self._mousePress = False

            buttonOffset = 0
            if self._validSort(index) and self._sortEnabled:
                # general mouse-press, if not resizing row/column
                if self._parent and self._parent.selectionMode() and self._changeSortColumnCallback(index):
                    return True

                # check of the mouse-press is on the icon
                if self._iconRect(option).contains(event.pos()):
                    self._sortIconCallback(index)
                    return True

                buttonOffset = 1

            # search through the buttons to find which is pressed
            for visibleButton, state in enumerate(self._validSpans(index)):
                if state:
                    # check if the mouse-press is on the icon
                    if self._iconRect(option, buttonOffset).contains(event.pos()):
                        self._iconCallback(index, visibleButton)
                        return True

                    buttonOffset += 1

        return super().editorEvent(event, model, option, index)

    def paint(self, painter, option, index):
        """Paint the contents of the cell.
        """
        sortOrder = self._table.horizontalHeader().sortIndicatorOrder()
        sortColumn = self._table.horizontalHeader().sortIndicatorSection()
        option.state = option.state & ~QtWidgets.QStyle.State_HasFocus

        super().paint(painter, option, index)

        # set a slightly larger clip-rect
        painter.save()
        rect = option.rect.adjusted(0, 0, 1, 1)
        painter.setClipRect(rect)

        state = QtGui.QIcon.On if (option.state & QtWidgets.QStyle.State_Open) else QtGui.QIcon.Off
        if int(option.state & QtWidgets.QStyle.State_Selected):
            backCol = option.palette.highlight()
        else:
            backCol = option.palette.base()
        buttonOffset = 0
        if sortColumn == index.column() and self._validSort(index) and self._sortEnabled:
            buttonOffset = 1

            # draw a clipped button on the right-hand-side if this is the active sorting column/index
            pr = QtCore.QRect(0, 0, self._SORTICONSIZE, self._SORTICONSIZE)
            pr.moveCenter(option.rect.center())
            pr.moveRight(option.rect.right() - self._HBORDER)
            painter.fillRect(pr, backCol)

            # need to use the generic-base as the cell-base may be a qlineargradient
            # which has no defined color but can be used for painting
            base = QtGui.QPalette().base().color().valueF()
            if sortOrder == Qt.AscendingOrder:
                # paint the icon - can use different mode from above if required
                if base > 0.5:
                    self._upIcon.paint(painter, pr, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, state)
                else:
                    self._upIconLight.paint(painter, pr, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, state)
            else:
                if base > 0.5:
                    self._downIcon.paint(painter, pr, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, state)
                else:
                    self._downIconLight.paint(painter, pr, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, state)

        # draw buttons on the right-hand-side if the states are valid
        for validSpan, buttonPix in zip(self._validSpans(index), [self._plusIcon, self._minusIcon]):
            if validSpan:
                pr = QtCore.QRect(0, 0, self._ICONSIZE, self._ICONSIZE)
                pr.moveCenter(option.rect.center())
                pr.moveRight(option.rect.right() - self._HBORDER - (buttonOffset * self._ICONSIZE))
                painter.fillRect(pr, backCol)
                # paint the icon - can use different mode from above if required
                buttonPix.paint(painter, pr, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, state)
                buttonOffset += 1

        # align the new grid-border with the pixel-centres
        painter.translate(0.5, 0.5)
        _pen = QtGui.QPen(option.palette.mid(), 1)
        painter.setPen(_pen)
        painter.drawLine(rect.topRight(), rect.bottomRight())
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.restore()

    def _iconCallback(self, index, visibleButton):
        """Process the clicked icon.
        """
        row, col = index.row(), index.column()
        _rowSpan, colSpan = self._parent.rowSpan(row, col), self._parent.columnSpan(row, col)
        if colSpan <= 1:
            # exit if the cell has no span in the required dimension
            return

        storeState = [self._table.isColumnHidden(col + cc) for cc in range(colSpan)]
        hiddenCount = storeState.count(True)
        topLeft = self._parent.model()._spanTopLeft[row, col]
        internalCount = [self._table.isColumnInternal(col + cc) for cc in range(colSpan)].count(True)

        hide = (visibleButton == 1)
        prevState = [False] + [hide] * (colSpan - 1)
        if not hide:
            for cc in range(1, colSpan):
                if self._table.isColumnInternal(col + cc):
                    # hide any internal-columns if expanding to full
                    prevState[cc] = True

        # columns my have changed from the stored values
        if topLeft is not None:
            if hide:
                if hiddenCount == internalCount:
                    prevState = self._expandedSections.get(topLeft, prevState)
                elif 0 <= (ind := storeState.index(False)) < colSpan:
                    # remember the first visible column, if there was only one
                    prevState = [True] * colSpan
                    prevState[ind] = False

            elif not hide:
                if hiddenCount == (colSpan - 1):
                    prevState = self._expandedSections.get(topLeft, prevState)

        for cc in range(colSpan):
            # toggle the visible state of the columns
            self._table.setColumnHidden(col + cc,
                                        prevState[cc],  # if prevState is not None else hide,
                                        skipUpdateWidth=True)

        if topLeft is not None and 1 < hiddenCount < (colSpan - 1):
            # only store when at least 2 visible/hidden
            self._expandedSections[topLeft] = storeState
        else:
            self._expandedSections.pop(topLeft, None)

    def _iconRect(self, option, buttonOffset=0):
        """"Get the co-ordinates of the icon at the button position.
        """
        # get the rect containing the expand/collapse icon at buttonOffset
        iRect = QtCore.QRect(0, 0, self._ICONSIZE, self._ICONSIZE)
        iRect.moveCenter(option.rect.center())
        iRect.moveRight(option.rect.right() - self._HBORDER - (buttonOffset * self._ICONSIZE))

        return iRect

    def _validSpans(self, index):
        """Return True if the icon can be displayed, i.e., the span is larger than one.
        """
        row, col = index.row(), index.column()
        _rowSpan, colSpan = self._parent.rowSpan(row, col), self._parent.columnSpan(row, col)

        count = [self._table.isColumnHidden(col + cc) for cc in range(colSpan)].count(False)
        # account for the internal-columns which should always be hidden
        internalCount = [self._table.isColumnInternal(col + cc) for cc in range(colSpan)].count(True)

        # return - can maximise/minimise
        return (count < colSpan - internalCount), (count > 1)

    def _validSort(self, index):
        """Return True if the sort-icon can be displayed, i.e., the vertical-span is larger than one.
        """
        row, col = index.row(), index.column()
        rowSpan, _colSpan = self._parent.rowSpan(row, col), self._parent.columnSpan(row, col)

        return rowSpan + row == self._parent.model().rowCount()

    def _changeSortColumnCallback(self, index):
        """Change to sorted column to the clicked column.
        """
        col = index.column()
        if col != self._table.horizontalHeader().sortIndicatorSection():
            # sort the selected column by the last value if available
            newOrder = self._sortedColumns.get(col, Qt.AscendingOrder)
            self._table.horizontalHeader().setSortIndicator(col, newOrder)

            # repaint to clean up the icons
            self._parent.repaint()
            return True

    def _sortIconCallback(self, index):
        """Process the clicked icon.
        """
        # get the column sorting status
        sortOrder = self._table.horizontalHeader().sortIndicatorOrder()
        col = index.column()

        # get the opposite order and sort the column
        newOrder = Qt.AscendingOrder if sortOrder != Qt.AscendingOrder else Qt.DescendingOrder
        self._sortedColumns[col] = newOrder
        self._table.horizontalHeader().setSortIndicator(col, newOrder)


class _ExpandVerticalDelegate(_ExpandDelegateABC):
    """Class to add an expand/collapse icon to the right-hand-side of a QTableView cell.

    A delegate that can be used in subclassed pandas dataFrame tables that have single or multi-level columns/indexes.
    Icon is visible for all cells that have a cell-span.
    Clicking the icon opens/closes the extra cells in the span.
    """
    alignBottom = False
    allowIconSpace = False
    drawGrid = True

    def editorEvent(self, event, model, option, index):
        """Handle clicking the icon.
        """
        # If the event is a click event
        if event.type() == QtCore.QEvent.MouseButtonPress:
            # check of the mouse-press is on the icon
            if self._iconRect(option).contains(event.pos()):
                self._mousePress = True

        elif event.type() == QtCore.QEvent.MouseButtonRelease:
            self._mousePress = False

            buttonOffset = 0
            # search through the buttons to find which is pressed
            for visibleButton, state in enumerate(self._validSpans(index)
                                                  if self.alignBottom else reversed(self._validSpans(index))):
                if state:
                    # check if the mouse-press is on the icon
                    if self._iconRect(option, buttonOffset).contains(event.pos()):
                        self._iconCallback(index, visibleButton)
                        return True

                    buttonOffset += 1

        return super().editorEvent(event, model, option, index)

    def paint(self, painter, option, index):
        """Paint the contents of the cell.
        """
        focus = (option.state & QtWidgets.QStyle.State_HasFocus)
        option.state = option.state & ~QtWidgets.QStyle.State_HasFocus

        super().paint(painter, option, index)

        # set a slightly larger clip-rect
        painter.save()
        rect = option.rect.adjusted(0, 0, 1, 1)
        painter.setClipRect(rect)

        # set the mode and state for the icons
        state = QtGui.QIcon.On if (option.state & QtWidgets.QStyle.State_Open) else QtGui.QIcon.Off
        if int(option.state & QtWidgets.QStyle.State_Selected):
            backCol = option.palette.highlight()
        elif index.row() % 2 and (
                self._parent if isinstance(self._parent, QtWidgets.QTableView) else self._table).alternatingRowColors():
            backCol = option.palette.alternateBase()
        else:
            backCol = option.palette.base()

        buttonOffset = 0
        if self.alignBottom:
            # draw buttons on the right-hand-side if the states are valid
            for validSpan, buttonPix in zip(self._validSpans(index), [self._plusIcon, self._minusIcon]):
                if validSpan:
                    pr = QtCore.QRect(0, 0, self._ICONSIZE, self._ICONSIZE)
                    pr.moveRight(option.rect.right() - self._HBORDER)
                    pr.moveBottom(option.rect.bottom() - self._VBORDER - (buttonOffset * self._ICONSIZE))
                    painter.fillRect(pr, backCol)
                    # paint the icon - can use different mode from above if required
                    buttonPix.paint(painter, pr, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, state)
                    buttonOffset += 1
        else:
            # draw buttons on the right-hand-side if the states are valid
            for validSpan, buttonPix in zip(reversed(self._validSpans(index)), [self._minusIcon, self._plusIcon]):
                if validSpan:
                    pr = QtCore.QRect(0, 0, self._ICONSIZE, self._ICONSIZE)
                    pr.moveRight(option.rect.right() - self._HBORDER)
                    pr.moveTop(option.rect.top() + self._VBORDER + (buttonOffset * self._ICONSIZE))
                    painter.fillRect(pr, backCol)
                    # paint the icon - can use different mode from above if required
                    buttonPix.paint(painter, pr, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, state)
                    buttonOffset += 1

        if self.drawGrid:
            # draw new grid-lines that don't have the QT grid-bug -> draws extra pixels :|
            _pen = QtGui.QPen(option.palette.mid(), 1)
            painter.setPen(_pen)
            painter.drawLine(rect.topRight(), rect.bottomRight())
            painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        if focus and self._focusBorderWidth:
            # draw new focus rect - can't catch the overlay colour from the fusion theme
            painter.translate(-0.5, -0.5)
            self._focusPen.setColor(QtGui.QPalette().highlight().color())
            painter.setPen(self._focusPen)
            painter.drawRect(option.rect)
        painter.restore()

    def _iconCallback(self, index, visibleButton):
        """Process the clicked icon.
        """
        row, col = index.row(), index.column()
        rowSpan, _colSpan = self._parent.rowSpan(row, col), self._parent.columnSpan(row, col)
        if rowSpan <= 1:
            # exit if the cell has no span in the required dimension
            return

        hidden = (visibleButton == (1 if self.alignBottom else 0))
        for rr in range(1, rowSpan):
            # toggle the visible state of the columns
            self._table.setRowHidden(row + rr, hidden, skipUpdateWidth=True)

        self._parent.repaint()

    def _iconRect(self, option, buttonOffset=0):
        """Get the co-ordinates of the icon at the button position.
        """
        # get the rect containing the expand/collapse icon at buttonOffset
        iRect = QtCore.QRect(0, 0, self._ICONSIZE, self._ICONSIZE)
        # iRect.moveCenter(option.rect.center())
        iRect.moveRight(option.rect.right() - self._HBORDER)

        if self.alignBottom:
            iRect.moveBottom(option.rect.bottom() - self._VBORDER - (buttonOffset * self._ICONSIZE))
        else:
            iRect.moveTop(option.rect.top() + self._VBORDER + (buttonOffset * self._ICONSIZE))

        return iRect

    def _validSpans(self, index):
        """Return True if the icon can be displayed, i.e., the span is larger than one.
        """
        row, col = index.row(), index.column()
        rowSpan, _colSpan = self._parent.rowSpan(row, col), self._parent.columnSpan(row, col)

        count = sum((0 if self._table.isRowHidden(row + rr) else 1) for rr in range(rowSpan))

        # return - can maximise/minimise
        return (count < rowSpan), (count > 1)


class _ExpandVerticalCellDelegate(_ExpandVerticalDelegate):
    """Class to add an expand/collapse icon to the right-hand-side of a QTableView cell.

    A delegate that can be used in subclassed pandas dataFrame tables that have single or multi-level columns/indexes.
    Icon is visible for all cells that have a cell-span.
    Clicking the icon opens/closes the extra cells in the span.
    """
    _HBORDER = 2
    _VBORDER = 2

    alignBottom = False
    allowIconSpace = True
    drawGrid = False

    def _iconCallback(self, index, visibleButton):
        """Process the clicked icon.
        """
        row, col = index.row(), index.column()
        rowSpan, _colSpan = self._table.rowSpan(row, col), self._table.columnSpan(row, col)
        if rowSpan <= 1:
            # exit if the cell has no span in the required dimension
            return

        hidden = (visibleButton == (1 if self.alignBottom else 0))
        for rr in range(1, rowSpan):
            # toggle the visible state of the columns
            self._table.setRowHidden(row + rr, hidden, skipUpdateWidth=True)

        self._parent.repaint()

    def _validSpans(self, index):
        """Return True if the icon can be displayed, i.e., the span is larger than one.
        """
        row, col = index.row(), index.column()
        rowSpan, _colSpan = self._table.rowSpan(row, col), self._table.columnSpan(row, col)
        count = sum((0 if self._table.isRowHidden(row + rr) else 1) for rr in range(rowSpan))

        # return - can maximise/minimise
        return (count < rowSpan), (count > 1)


#=========================================================================================
# _SortDelegate
#=========================================================================================

class _SortDelegate(QtWidgets.QStyledItemDelegate):
    """Class to add a sort-indicator icon to the right-hand-side of a QTableView cell.
    Adds an edit icon to the left-hand-side if editable is True.

    A delegate that can be used in subclassed pandas dataFrame tables that have single or multi-level columns/indexes.
    This replicates the standard QHeaderView functionality.
    Icon is visible for the active sorted column.
    Clicking the icon reorders as Qt.Ascending/Qt.Descending
    """
    buttonClicked = QtCore.pyqtSignal(QtCore.QModelIndex, int)

    _EDITICONSIZE = 24
    _SORTICONSIZE = 12
    _HBORDER = 4
    _VBORDER = 4

    def __init__(self, parent, *, table=None, editable=True):
        """Initialise the class.

        parent is the subclassed QTableView - controls the multi-level view capability for the table header.
        table is the subclassed QTableView - controls the view for the main table.

        :param parent: QtWidgets.QTableView.
        :param table: QtWidgets.QTableView.
        """
        super().__init__(parent)

        self._table = table
        self._parent = parent
        self._mousePress = False
        self._sortedColumns = {}
        self._editable = editable

        self._downIcon = Icon('icons/caret-grey-down')
        self._upIcon = Icon('icons/caret-grey-up')
        self._editableIcon = Icon('icons/editable')

    def paint(self, painter, option, index):
        """Paint the contents of the cell.
        """
        super().paint(painter, option, index)

        sortOrder = self._table.horizontalHeader().sortIndicatorOrder()
        sortColumn = self._table.horizontalHeader().sortIndicatorSection()

        # set the clip-rect to not paint outside the widget
        painter.save()
        painter.setClipRect(option.rect)

        # # set the mode and state for the icons
        state = QtGui.QIcon.On if (option.state & QtWidgets.QStyle.State_Open) else QtGui.QIcon.Off
        if sortColumn == index.column():
            # draw a clipped button on the right-hand-side if this is the active sorting column/index
            pr = QtCore.QRect(0, 0, self._SORTICONSIZE, self._SORTICONSIZE)
            pr.moveCenter(option.rect.center())
            pr.moveRight(option.rect.right() - self._HBORDER)

            if sortOrder == Qt.AscendingOrder:
                # paint the icon - can use different mode from above if required
                self._upIcon.paint(painter, pr, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, state)
            else:
                self._downIcon.paint(painter, pr, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, state)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        """Handle clicking the icon.
        """
        if event.button() == QtCore.Qt.LeftButton:
            # If the event is a click event
            if event.type() == QtCore.QEvent.MouseButtonPress:
                # check if the mouse-press is on the icon
                if self._iconRect(option).contains(event.pos()):
                    self._mousePress = True

            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                self._mousePress = False

                # general mouse-press, if not resizing row/column
                if self._parent and self._parent.selectionMode() and self._changeSortColumnCallback(index):
                    return True

                # check of the mouse-press is on the icon
                if self._iconRect(option).contains(event.pos()):
                    self._iconCallback(index)
                    return True

        return super().editorEvent(event, model, option, index)

    def _iconRect(self, option):
        """Get the co-ordinates of the right-justified icon.
        """
        # get the rect containing the sort indicator
        iRect = QtCore.QRect(0, 0, self._SORTICONSIZE, self._SORTICONSIZE)
        iRect.moveCenter(option.rect.center())
        iRect.moveRight(option.rect.right() - self._HBORDER)

        return iRect

    def _changeSortColumnCallback(self, index):
        """Change to sorted column to the clicked column.
        """
        col = index.column()
        if col != self._table.horizontalHeader().sortIndicatorSection():
            # sort the selected column by the last value if available
            newOrder = self._sortedColumns.get(col, Qt.AscendingOrder)
            self._table.horizontalHeader().setSortIndicator(col, newOrder)

            # repaint to clean up the icons
            self._parent.repaint()
            return True

    def _iconCallback(self, index):
        """Process the clicked icon.
        """
        # get the column sorting status
        sortOrder = self._table.horizontalHeader().sortIndicatorOrder()
        col = index.column()

        # get the opposite order and sort the column
        newOrder = Qt.AscendingOrder if sortOrder != Qt.AscendingOrder else Qt.DescendingOrder
        self._sortedColumns[col] = newOrder
        self._table.sortByColumn(col, newOrder)
        self._parent.repaint()


#=========================================================================================
# _EditableDelegate
#=========================================================================================

class _EditableDelegate(QtWidgets.QStyledItemDelegate):
    """Class to add an edit icon to the left-hand-side of a QTableView cell.

    A delegate that can be used in subclassed pandas dataFrame tables that have single or multi-level columns/indexes.
    This replicates the standard QHeaderView functionality.
    Icon is visible for editable columns.
    """
    _EDITICONSIZE = 24
    _HBORDER = 4
    _VBORDER = 4

    def __init__(self, parent, *, table=None, editable=True):
        """Initialise the class.

        parent is the subclassed QTableView - controls the multi-level view capability for the table header.
        table is the subclassed QTableView - controls the view for the main table.

        :param parent: QtWidgets.QTableView.
        :param table: QtWidgets.QTableView.
        """
        super().__init__(parent)

        self._table = table
        self._parent = parent
        self._editable = editable
        self._editableIcon = Icon('icons/editable')

    def paint(self, painter, option, index):
        """Paint the contents of the cell.
        """
        super().paint(painter, option, index)

        if self._editable:
            # set the clip-rect to not paint outside the widget
            painter.save()
            painter.setClipRect(option.rect)

            # set the mode and state for the icons
            state = QtGui.QIcon.On if (option.state & QtWidgets.QStyle.State_Open) else QtGui.QIcon.Off

            # paint the icon - can use different mode from above if required
            pr = QtCore.QRect(0, 0, self._EDITICONSIZE, self._EDITICONSIZE)
            pr.moveCenter(option.rect.center())
            pr.moveRight(option.rect.right() - self._HBORDER)

            self._editableIcon.paint(painter, pr, QtCore.Qt.AlignCenter, QtGui.QIcon.Normal, state)

            painter.restore()


#=========================================================================================
# _ColourDelegate
#=========================================================================================

class _ColourDelegate(QtWidgets.QStyledItemDelegate):
    """Class to change to colour of selection highlights.
    Subclasses the paint method to remove the focus dotted outline,
    and adds a colour overlay for background coloured cells.
    """
    _focusBorderWidth = 1
    _focusPen = None

    def __init__(self, parent, *, table=None, focusBorderWidth=1):
        """Initialise the class.

        parent is the subclassed QTableView - controls the multi-level view capability for the table header.
        table is the subclassed QTableView - controls the view for the main table.

        :param parent: QtWidgets.QTableView.
        :param table: QtWidgets.QTableView.
        :param focusBorderWidth: int, width of focussed cell border.
        """
        super().__init__(parent)

        self._table = table
        self._parent = parent

        # set the colours
        self._focusPen = QtGui.QPen(QtGui.QPalette().highlight().color(), 2)

        # double the line-widths accounts for the device-pixel-ratio
        self._focusBorderWidth = focusBorderWidth
        self._focusPen.setWidthF(focusBorderWidth * 2.0)
        self._focusPen.setJoinStyle(QtCore.Qt.MiterJoin)  # square ends

    def paint(self, painter, option, index):
        """Paint the contents of the cell.
        """
        focus = (option.state & QtWidgets.QStyle.State_HasFocus)
        # option.state = option.state & ~QtWidgets.QStyle.State_HasFocus

        super().paint(painter, option, index)

        # # alternative method to add selection border to the focussed cell
        # if (brush := index.data(QtCore.Qt.BackgroundRole)) and (option.state & QtWidgets.QStyle.State_Selected):
        #     # fade the background and paint over the top of selected cell
        #     # - ensures that different coloured backgrounds are still visible
        #     # - does, however, modify the foreground colour :|
        #     painter.setClipRect(option.rect)
        #     brush.setAlphaF(0.20)
        #     painter.setCompositionMode(painter.CompositionMode_SourceOver)
        #     painter.fillRect(option.rect, brush)
        #
        #     if focus:
        #         painter.setPen(self._focusPen)
        #         painter.drawRect(option.rect)
        #     elif not focus and index.data(BORDER_ROLE):
        #         # move the focus rectangle drawing to after, otherwise, alternative-background-color is used
        #         painter.setPen(self._noFocusPen)
        #         painter.setRenderHint(QtGui.QPainter.Antialiasing)
        #         painter.drawRoundedRect(option.rect, 4, 4)

        painter.save()
        if focus:
            painter.setClipRect(option.rect)
            painter.setPen(QtGui.QPen(QtGui.QPalette().highlight(), 2))
            painter.drawRect(option.rect)
        elif not focus and index.data(BORDER_ROLE):
            # move the focus rectangle drawing to after, otherwise, alternative-background-color is used
            painter.setClipRect(option.rect)
            painter.setPen(QtGui.QPen(QtGui.QPalette().dark(), 2))
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.drawRoundedRect(option.rect, 4, 4)
        painter.restore()

    def setEditorData(self, widget, index) -> None:
        """populate the editor widget when the cell is edited
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
            raise RuntimeError(f'Widget {widget} does not expose a set method; required for table editing')

    def updateEditorGeometry(self, widget, itemStyle, index):
        """Fit editor geometry to the index
        """
        cellRect = itemStyle.rect
        widget.move(cellRect.topLeft())
        widget.setGeometry(cellRect)


#=========================================================================================
# _TableEditorDelegate
#=========================================================================================

class _TableEditorDelegate(QtWidgets.QStyledItemDelegate):
    """handle the setting of data when editing the table
    """

    def __init__(self, parent, *, objectColumn=None):
        """Initialise the delegate
        :param parent - link to the handling table
        """
        super().__init__(self, parent)

        # self.customWidget = None
        self._parent = parent

        self._objectColumn = objectColumn

    def createEditor(self, parentWidget, itemStyle, index):  # returns the edit widget
        """Create the editor widget
        """
        col = index.column()
        objCol = self._parent._columnDefs.columns[col]

        if objCol.editClass:
            widget = objCol.editClass(None, *objCol.editArgs, **objCol.editKw)
            widget.setParent(parentWidget)
            # widget.activated.connect(partial(self._pulldownActivated, widget))

            self.customWidget = widget

            return widget

        else:
            self.customWidget = None

            return super().createEditor(parentWidget, itemStyle, index)

    def setEditorData(self, widget, index) -> None:
        """populate the editor widget when the cell is edited
        """
        model = index.model()
        value = model.data(index, EDIT_ROLE)

        if not isinstance(value, (list, tuple)):
            value = (value,)

        for attrib in _EDITOR_SETTER:
            if hasattr(widget, attrib):
                # get the method from the widget, and call with appropriate parameters
                func = getattr(widget, attrib, None)
                if not callable(func):
                    raise TypeError(f"widget.{attrib} is not callable")

                func(*value)
                break

        else:
            raise RuntimeError(f'Widget {widget} does not expose a set method; required for table editing')

    def setModelData(self, widget, mode, index):
        """Set the object to the new value
        :param widget - typically a lineedit handling the editing of the cell
        :param mode - editing mode:
        :param index - QModelIndex of the cell
        """
        for attrib in _EDITOR_GETTER:
            if hasattr(widget, attrib):
                # get the method from the widget, and call with appropriate parameters
                func = getattr(widget, attrib, None)
                if not callable(func):
                    raise TypeError(f"widget.{attrib} is not callable")
                value = func()
                break

        else:
            raise RuntimeError(f'Widget {widget} does not expose a get method; required for table editing')

        try:
            self._parent.model().setData(index, value)

        except Exception as es:
            getLogger().debug(f'Error handling cell editing: {index.row()} {index.column()} - '
                              f'{es}  {self._parent.model()._sortIndex}  {value}')

    def updateEditorGeometry(self, widget, itemStyle, index):  # ensures that the editor is displayed correctly
        """Update the geometry of the widget to fit the cell-index and the custom-widget
        :param widget: typically a lineedit handling the editing of the cell
        :param itemStyle:
        :param index: QModelIndex of the cell
        :return:
        """
        if not self.customWidget:
            return super().updateEditorGeometry(widget, itemStyle, index)

        cellRect = itemStyle.rect
        pos = widget.mapToGlobal(cellRect.topLeft())
        x, y = pos.x(), pos.y()
        hint = widget.sizeHint()
        width = max(hint.width(), cellRect.width())
        height = max(hint.height(), cellRect.height())

        # force the pulldownList to be a popup - will always close when clicking outside
        widget.setParent(self._parent, QtCore.Qt.Popup)
        widget.setGeometry(x, y, width, height)

    def _returnPressedCallback(self, widget):
        """Capture the returnPressed event from the widget, because the setModeData event seems to be a frame behind the widget
        when getting the text()
        """
        # check that it is a QLineEdit - check for other types later (see old table class)
        if isinstance(widget, QtWidgets.QLineEdit):
            self._editorValue = widget.text()
            self._returnPressed = True


#=========================================================================================
# _GridDelegate
#=========================================================================================

class _GridDelegate(QtWidgets.QStyledItemDelegate):
    """Class to draw modified grid-lines.
    """

    def paint(self, painter, option, index):
        """Paint the contents of the cell.
        """
        super().paint(painter, option, index)

        # set the clip-rect to not paint outside the widget
        painter.save()
        rect = option.rect.adjusted(0, 0, 1, 1)
        painter.setClipRect(rect)

        painter.translate(0.5, 0.5)
        _pen = QtGui.QPen(option.palette.mid(), 1)
        painter.setPen(_pen)
        painter.drawLine(rect.topRight(), rect.bottomRight())
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.restore()
