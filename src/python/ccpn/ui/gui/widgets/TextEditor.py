"""Module Documentation here

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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-06-28 10:33:21 +0100 (Fri, June 28, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtWidgets, QtCore, QtPrintSupport
from ccpn.ui.gui.widgets.FileDialog import MacrosFileDialog
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Action import Action
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Label import Label, ActiveLabel
from ccpn.ui.gui.guiSettings import getColours, BORDERFOCUS, BORDERNOFOCUS
from ccpn.ui.gui.widgets.Font import setWidgetFont, getFontHeight
from ccpn.util.Path import aPath


ATTRIBUTE_CHECK_LIST = ('_mouseStart', '_minimumWidth', '_widthStart', '_minimumHeight', '_heightStart')
ATTRIBUTE_HEIGHT_LIST = ('_minimumHeight')


class TextEditor(QtWidgets.QTextEdit, Base):
    editingFinished = QtCore.pyqtSignal()
    receivedFocus = QtCore.pyqtSignal()
    mouseLeft = QtCore.pyqtSignal()

    _minimumHeight = 25
    MINIMUM_CHARS_WIDTH = 8
    MINIMUM_CHARS_HEIGHT = 3

    def __init__(self, parent=None, filename=None, callback=None,
                 listener=None, stripEndWhitespace=True, editable=True,
                 backgroundText='<default>',
                 acceptRichText=False, addGrip=False, addWordWrap=False, wordWrap=False,
                 fitToContents=False, maximumRows=None, enableWebLinks=False,
                 **kwds):
        super().__init__(parent)
        Base._init(self, setLayout=True, **kwds)

        self.filename = filename
        self.setAcceptRichText(acceptRichText)

        setWidgetFont(self, )
        self._minimumHeight = self._height = getFontHeight()
        self._maximumRows = maximumRows

        self._changed = False
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        palette = self.viewport().palette()
        self._background = palette.color(self.viewport().backgroundRole())

        self.backgroundText = backgroundText
        if self.backgroundText:
            self.setPlaceholderText(str(self.backgroundText))

        if not editable:
            self.setReadOnly(True)
            self.setEnabled(False)

        self._fitToContents = fitToContents
        self._lastRowCount = 0
        # layout = QtWidgets.QHBoxLayout(self)
        layout = self.getLayout()
        if addWordWrap:
            self._wrapIconOn = Icon('icons/wordwrap-on')
            self._wrapIconOff = Icon('icons/wordwrap-off')
            self._label = ActiveLabel(self)
            layout.addWidget(self._label, 0, 0, 0, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
            self._label.setContentsMargins(0, 0, 16 if addGrip else 0, 0)
            self._label.setSelectionCallback(self._toggleWordWrap)
            self._setWrapIcon(wordWrap)
            self._label.setToolTip('Enable/disable Word-wrap')

        if addGrip:
            _gripIcon = Icon('icons/grip')

            gripper = QtWidgets.QSizeGrip(self)
            # layout.addWidget(gripper, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
            layout.addWidget(gripper, 0, 0, 0, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
            gripper.setStyleSheet("""QSizeGrip {
                            image: url(%s);
                            width: 20px; height: 20px;
            }""" % (_gripIcon._filePath))

        self._enableWebLinks = enableWebLinks

        self._setFocusColour()

    def mousePressEvent(self, e):
        """Get the web-link under the mouse.
        """
        if self._enableWebLinks:
            self._anchor = self.anchorAt(e.pos())

        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        """Change the cursor if there is a link under the mouse.
        """
        if self._enableWebLinks:
            if _anchor := self.anchorAt(e.pos()):
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.PointingHandCursor)
                self.setToolTip(_anchor)
            else:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.ArrowCursor)
                self.setToolTip(None)

        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        """Open a new web-page to the link under the mouse.
        """
        if self._enableWebLinks and self._anchor:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(self._anchor))
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.ArrowCursor)
            self._anchor = None

        super().mouseReleaseEvent(e)

    def leaveEvent(self, event):
        self.mouseLeft.emit()
        super().leaveEvent(event)

    def _toggleWordWrap(self):
        wordWrap = (self.lineWrapMode() != QtWidgets.QTextEdit.WidgetWidth)
        self._setWrapIcon(wordWrap)

    def _setWrapIcon(self, wordWrap):
        if wordWrap:
            self._label.setPixmap(self._wrapIconOn.pixmap(20, 20))
        else:
            self._label.setPixmap(self._wrapIconOff.pixmap(20, 20))
        self.setLineWrapMode(QtWidgets.QTextEdit.WidgetWidth if wordWrap else QtWidgets.QTextEdit.NoWrap)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        hBar = self.horizontalScrollBar()
        vBar = self.verticalScrollBar()
        dy = hBar.height() if hBar.isVisible() else 0
        dx = vBar.width() if vBar.isVisible() else 0
        layout = self.getLayout()
        layout.setContentsMargins(0, 0, dx, dy)

        self._updateheight()
        super(TextEditor, self).resizeEvent(a0)

    def _updateheight(self):
        # Override the resize event to fit to contents
        if self._fitToContents:
            rowHeight = getFontHeight()
            lineCount = min(self.document().lineCount(), self._maximumRows) if self._maximumRows is not None else self.document().lineCount()

            if lineCount != self._lastRowCount:
                minHeight = (rowHeight + 1) * (lineCount + 1)
                self._maxHeight = max(2 * rowHeight, minHeight)
                self.setFixedHeight(self._maxHeight)
                self._lastRowCount = lineCount

    def _setFocusColour(self, focusColour=None, noFocusColour=None):
        """Set the focus/noFocus colours for the widget
        """
        focusColour = getColours()[BORDERFOCUS]
        noFocusColour = getColours()[BORDERNOFOCUS]
        styleSheet = "QTextEdit { " \
                     "border: 1px solid;" \
                     "border-radius: 3px;" \
                     "border-color: %s;" \
                     "} " \
                     "QTextEdit:focus { " \
                     "border: 1px solid %s; " \
                     "border-radius: 3px; " \
                     "}" % (noFocusColour, focusColour)
        self.setStyleSheet(styleSheet)

    # def _addGrip(self):
    #     # an idea to add a grip handle - can't thing of any other way
    #     self._gripIcon = Icon('icons/grip')
    #     self._gripLabel = Label(self)
    #     self._gripLabel.setPixmap(self._gripIcon.pixmap(16))
    #     self._gripLabel.mouseMoveEvent = self._mouseMoveEvent
    #     self._gripLabel.mousePressEvent = self._mousePressEvent
    #     self._gripLabel.mouseReleaseEvent = self._mouseReleaseEvent
    #
    #     layout = QtWidgets.QHBoxLayout(self)
    #     layout.setContentsMargins(0, 0, 0, 0)
    #     layout.addWidget(self._gripLabel, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)

    def context_menu(self):
        a = self.createStandardContextMenu()
        actions = a.actions()
        # edit = Action(a, text='Fonts', callback=self._setFont)
        # a.insertAction(actions[-1], edit)
        a.exec_(QtGui.QCursor.pos())

    def _setFont(self):
        font, ok = QtWidgets.QFontDialog.getFont(self.font(), self)
        if ok:
            self.setFont(font)

    def focusInEvent(self, event):
        super(TextEditor, self).focusInEvent(event)
        self.receivedFocus.emit()

    def focusOutEvent(self, event):
        if self._changed:
            self.editingFinished.emit()
        super(TextEditor, self).focusOutEvent(event)

    def _handle_text_changed(self):
        self._changed = True
        self._updateheight()

    def setTextChanged(self, state=True):
        self._changed = state

    def setHtml(self, html):
        super().setHtml(html)
        self._changed = False

    def get(self):
        return self.toPlainText()

    def set(self, value):
        self.setText(value)

    def zoom(self, delta):
        if delta < 0:
            self.zoomOut(1)
        elif delta > 0:
            self.zoomIn(5)

    def saveToPDF(self, fileName=None):

        fType = '*.pdf'
        dialog = MacrosFileDialog(parent=self, acceptMode='save', fileFilter=fType, selectFile=fileName)
        dialog._show()
        filename = dialog.selectedFile()
        if filename:
            printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.HighResolution)
            printer.setPageSize(QtPrintSupport.QPrinter.A4)
            printer.setColorMode(QtPrintSupport.QPrinter.Color)
            printer.setOutputFormat(QtPrintSupport.QPrinter.PdfFormat)
            printer.setOutputFileName(filename)
            self.document().print_(printer)

    # def _mousePressEvent(self, event):
    #     """Handle mouse press in the grip
    #     """
    #     super().mousePressEvent(event)
    #     self._resizing = True
    #     self._widthStart = self.width()
    #     self._heightStart = self.height()
    #     self._mouseStart = event.globalPos()
    #
    # def _mouseReleaseEvent(self, event):
    #     """Handle mouse release in the grip
    #     """
    #     super().mouseReleaseEvent(event)
    #     self._resizing = False
    #
    # def _mouseMoveEvent(self, event):
    #     """Update widget size as the grip is dragged
    #     """
    #     super().mouseMoveEvent(event)
    #     if self._resizing and all(hasattr(self, att) for att in ATTRIBUTE_CHECK_LIST):
    #         delta = event.globalPos() - self._mouseStart
    #         width = max(self._minimumWidth, self._widthStart + delta.x())
    #         height = max(self._minimumHeight, self._heightStart + delta.y())
    #         self.setMinimumSize(width, height)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(self._height * self.MINIMUM_CHARS_WIDTH, self._height * self.MINIMUM_CHARS_HEIGHT)

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(self._height * self.MINIMUM_CHARS_WIDTH, self._height * self.MINIMUM_CHARS_HEIGHT)

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.get()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.set(value)


class TextBrowser(QtWidgets.QTextBrowser, Base):
    receivedFocus = QtCore.pyqtSignal()

    def __init__(self, parent=None, htmlFilePath=None, **kwds):
        super().__init__(parent)
        Base._init(self, setLayout=True, **kwds)
        self.htmlFilePath = htmlFilePath
        if self.htmlFilePath is not None:
            self.setHtmlFilePath(self.htmlFilePath)

    def setHtmlFilePath(self, htmlFilePath):
        from ccpn.ui.gui.widgets.MessageDialog import showMessage
        path = aPath(htmlFilePath)
        if not path.exists():
            showMessage('Path not found', f'Could not load {path}')
            return
        try:
            self.setSource(QtCore.QUrl.fromLocalFile(str(path)))
        except Exception as err:
            showMessage('Help file not available', f'Could not load the help browser:  {err}')


class PlainTextEditor(QtWidgets.QPlainTextEdit, Base):
    editingFinished = QtCore.pyqtSignal()
    receivedFocus = QtCore.pyqtSignal()

    _minimumHeight = 25

    def __init__(self, parent=None, filename=None, fitToContents=False, callback=None,
                 listener=None, stripEndWhitespace=True, editable=True,
                 backgroundText='<default>',
                 **kwds):

        super().__init__(parent)
        Base._init(self, **kwds)

        self.filename = filename
        self._fitToContents = fitToContents

        # from ccpn.framework.Application import getApplication
        # getApp = getApplication()
        # if getApp and hasattr(getApp, '_fontSettings'):
        #     self.setFont(getApp._fontSettings.fixedWidthFont)
        setWidgetFont(self, )

        self._changed = False
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        palette = self.viewport().palette()
        self._background = palette.color(self.viewport().backgroundRole())

        self._setFocusColour()

        self._maxWidth = 0
        self._maxHeight = 0

    def _setFocusColour(self, focusColour=None, noFocusColour=None):
        """Set the focus/noFocus colours for the widget
        """
        focusColour = getColours()[BORDERFOCUS]
        noFocusColour = getColours()[BORDERNOFOCUS]
        styleSheet = "QPlainTextEdit {" \
                     "border: 1px solid;" \
                     "border-radius: 1px;" \
                     "border-color: %s;" \
                     "} " \
                     "QPlainTextEdit:focus {" \
                     "border: 1px solid %s; " \
                     "border-radius: 1px;" \
                     "}" % (noFocusColour, focusColour)
        self.setStyleSheet(styleSheet)

    def _addGrip(self):
        # an idea to add a grip handle - can't thing of any other way
        self._gripIcon = Icon('icons/grip')
        self._gripLabel = Label(self)
        self._gripLabel.setPixmap(self._gripIcon.pixmap(16))
        self._gripLabel.mouseMoveEvent = self._mouseMoveEvent
        self._gripLabel.mousePressEvent = self._mousePressEvent
        self._gripLabel.mouseReleaseEvent = self._mouseReleaseEvent

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._gripLabel, 0, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)

    def context_menu(self):
        a = self.createStandardContextMenu()
        actions = a.actions()
        edit = Action(a, text='Fonts', callback=self._setFont)
        a.insertAction(actions[3], edit)
        a.exec_(QtGui.QCursor.pos())

    def _setFont(self):
        font, ok = QtWidgets.QFontDialog.getFont(self.font(), self)
        if ok:
            self.setFont(font)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.receivedFocus.emit()

    def focusOutEvent(self, event):
        if self._changed:
            self.editingFinished.emit()
        super().focusOutEvent(event)

    def _handle_text_changed(self):
        self._changed = True
        self._updateheight()

    def setTextChanged(self, state=True):
        self._changed = state

    def zoom(self, delta):
        if delta < 0:
            self.zoomOut(1)
        elif delta > 0:
            self.zoomIn(5)

    def get(self):
        return self.toPlainText()

    def set(self, value):
        self.setPlainText(value)

    def saveToPDF(self, fileName=None):

        fType = '*.pdf'
        dialog = MacrosFileDialog(parent=self.ui.mainWindow, acceptMode='save', fileFilter=fType, selectFile=fileName)
        dialog._show()
        filename = dialog.selectedFile()
        if filename:
            printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.HighResolution)
            printer.setPageSize(QtPrintSupport.QPrinter.A4)
            printer.setColorMode(QtPrintSupport.QPrinter.Color)
            printer.setOutputFormat(QtPrintSupport.QPrinter.PdfFormat)
            printer.setOutputFileName(filename)
            self.document().print_(printer)

    def _mousePressEvent(self, event):
        """Handle mouse press in the grip
        """
        super().mousePressEvent(event)
        self._resizing = True
        self._widthStart = self.width()
        self._heightStart = self.height()
        self._mouseStart = event.globalPos()

    def _mouseReleaseEvent(self, event):
        """Handle mouse release in the grip
        """
        super().mouseReleaseEvent(event)
        self._resizing = False

    def _mouseMoveEvent(self, event):
        """Update widget size as the grip is dragged
        """
        super().mouseMoveEvent(event)
        if self._resizing and all(hasattr(self, att) for att in ATTRIBUTE_CHECK_LIST) and self._fitToContents:
            delta = event.globalPos() - self._mouseStart
            _size = self.document().size().toSize()
            width = max(self._minimumWidth, self._widthStart + delta.x(), _size.width())
            height = max(self._minimumHeight, self._heightStart + delta.y(), _size.height())

            self.setMinimumSize(width, height)
            self.updateGeometry()

    def resizeEvent(self, e: QtGui.QResizeEvent) -> None:
        self._updateheight()
        super(PlainTextEditor, self).resizeEvent(e)

    def _updateheight(self):
        # Override the resize event to fit to contents
        if self._fitToContents:
            rowHeight = QtGui.QFontMetrics(self.document().defaultFont()).height()
            lineCount = self.document().lineCount()

            minHeight = (rowHeight + 1) * (lineCount + 1)
            self._maxHeight = max(self._minimumHeight, minHeight)
            self.setMaximumHeight(self._maxHeight)


# class Grip(QtWidgets.QLabel):
#     def __init__(self, parent, move_widget):
#         super(Grip, self).__init__(parent)
#         self.move_widget = move_widget
#
#         self._gripIcon = Icon('icons/grip')
#         self.setPixmap(self._gripIcon.pixmap(16))
#
#         self.min_height = 50
#
#         self.mouse_start = None
#         self.height_start = self.move_widget.height()
#         self.resizing = False
#         self.setMouseTracking(True)
#
#         self.setCursor(QtCore.Qt.SizeVerCursor)
#
#     def showEvent(self, event):
#         super(Grip, self).showEvent(event)
#         self.reposition()
#
#     def mousePressEvent(self, event):
#         super(Grip, self).mousePressEvent(event)
#         self.resizing = True
#         self.height_start = self.move_widget.height()
#         self.mouse_start = event.globalPos()
#
#     def mouseMoveEvent(self, event):
#         super(Grip, self).mouseMoveEvent(event)
#         if self.resizing:
#             delta = event.globalPos() - self.mouse_start
#             height = self.height_start + delta.y()
#             if height > self.min_height:
#                 self.move_widget.setFixedHeight(height)
#             else:
#                 self.move_widget.setFixedHeight(self.min_height)
#
#             self.reposition()
#
#     def mouseReleaseEvent(self, event):
#         super(Grip, self).mouseReleaseEvent(event)
#         self.resizing = False
#
#     def reposition(self):
#         rect = self.move_widget.geometry()
#         self.move(rect.width() - 18, rect.height() - 18)


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog
    from ccpn.ui.gui.widgets.Widget import Widget


    app = TestApplication()

    popup = CcpnDialog(windowTitle='Test widget', setLayout=True)
    widget = TextEditor(parent=popup, grid=(0, 0))

    popup.show()
    popup.raise_()
    app.start()
