"""Module Documentation here

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
__dateModified__ = "$dateModified: 2025-04-16 12:49:01 +0100 (Wed, April 16, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtWidgets, QtCore, QtPrintSupport

from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Action import Action
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Label import ActiveLabel
from ccpn.ui.gui.widgets.Font import setWidgetFont, getFontHeight
from ccpn.util.Path import aPath


ATTRIBUTE_CHECK_LIST = ('_mouseStart', '_minimumWidth', '_widthStart', '_minimumHeight', '_heightStart')
ATTRIBUTE_HEIGHT_LIST = ('_minimumHeight')
_GRIPSIZE = 20


class TextEditor(QtWidgets.QTextEdit, Base):
    editingFinished = QtCore.pyqtSignal()
    receivedFocus = QtCore.pyqtSignal()
    mouseLeft = QtCore.pyqtSignal()

    _minimumHeight = 25
    MINIMUM_CHARS_WIDTH = 8
    MINIMUM_CHARS_HEIGHT = 3

    def __init__(self, parent=None, filename=None,
                 editable=True, backgroundText='<default>',
                 acceptRichText=False, _addGrip=False, addWordWrap=False, wordWrap=False,
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
        self.document().contentsChanged.connect(self._updateHeight)

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
        layout = self.getLayout()
        if addWordWrap:
            self._wrapIconOn = Icon('icons/wordwrap-on')
            self._wrapIconOff = Icon('icons/wordwrap-off')
            self._label = ActiveLabel(self)
            layout.addWidget(self._label, 0, 0, 0, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
            self._label.setContentsMargins(0, 0, 16 if _addGrip else 0, 0)
            self._label.setSelectionCallback(self._toggleWordWrap)
            self._setWrapIcon(wordWrap)
            self._label.setToolTip('Enable/disable Word-wrap')
        if _addGrip:
            gripper = QtWidgets.QSizeGrip(self)
            layout.addWidget(gripper, 0, 0, 0, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        self._enableWebLinks = enableWebLinks

        self._setStyle()

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
                self.setToolTip('')
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

    def _updateHeight(self):
        # Override the resize event to fit to contents
        if self._fitToContents:
            rowHeight = getFontHeight()
            lineCount = min(self.document().lineCount(),
                            self._maximumRows) if self._maximumRows is not None else self.document().lineCount()

            if lineCount != self._lastRowCount:
                minHeight = (rowHeight + 1) * (lineCount + 1)
                self._maxHeight = max(2 * rowHeight, minHeight)
                # self.setMaximumHeight(self._maxHeight)
                self._lastRowCount = lineCount

    def _setStyle(self):
        """Set the focus/noFocus colours for the widget
        """
        _gripIcon = Icon('icons/grip')
        _style = """
                    QTextEdit {
                        border: 1px solid palette(mid);
                        border-radius: 2px;
                    }
                    QTextEdit:focus {
                        border: 1px solid palette(highlight);
                        border-radius: 2px;
                    }
                    QSizeGrip {
                        image: url(%s);
                        width: 20px; height: 20px;
                    }
                    """
        self.setStyleSheet(_style % aPath(_gripIcon._filePath).as_posix())

    def context_menu(self):
        a = self.createStandardContextMenu()
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
        self._updateHeight()

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
        from ccpn.ui.gui.widgets.FileDialog import MacrosFileDialog

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


#=========================================================================================
# TextBrowser
#=========================================================================================

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


#=========================================================================================
# PlainTextEditor
#=========================================================================================

class PlainTextEditor(QtWidgets.QPlainTextEdit, Base):
    editingFinished = QtCore.pyqtSignal()
    receivedFocus = QtCore.pyqtSignal()

    _minimumHeight = 25

    def __init__(self, parent=None, filename=None, fitToContents=False, editable=True,
                 backgroundText='<default>', wordWrap=False, addWrapButton=False, _addGrip=False,
                 **kwds):

        super().__init__(parent)
        Base._init(self, **kwds)

        self.filename = filename
        self._fitToContents = fitToContents
        self._changed = False
        self._wrapButtonEnabled = addWrapButton
        self._gripEnabled = _addGrip
        if not editable:
            self.setReadOnly(True)
            self.setEnabled(False)
        self._backgroundText = backgroundText
        if self._backgroundText:
            self.setPlaceholderText(str(backgroundText))

        setWidgetFont(self, )

        self.setTabChangesFocus(True)
        self.document().contentsChanged.connect(self._updateHeight)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)

        palette = self.viewport().palette()
        self._background = palette.color(self.viewport().backgroundRole())
        self._setStyle()

        if addWrapButton:
            self._wrapIconOn = Icon('icons/wordwrap-on')
            self._wrapIconOff = Icon('icons/wordwrap-off')
            self._label = ActiveLabel(self)  # NOT inserted into a layout
            self._label.setContentsMargins(0, 0, 0, 0)
            self._label.setSelectionCallback(self._toggleWordWrap)
            self._label.setToolTip('Enable/disable Word-wrap')
            self._setWrapIcon(wordWrap)  # set the initial state of the wrap icon
        if _addGrip:  # need to check this as not always appearing
            self._gripper = QtWidgets.QSizeGrip(self)

        self._maxWidth = 0
        self._maxHeight = 0
        # add eventFilter to tie the wrap-button position to the bottom-right of the viewport
        self.viewport().installEventFilter(self)
        # force alignment of the wrap-button on first show
        QtCore.QTimer.singleShot(0, self._onUpdateRequest)

    def eventFilter(self, obj, event):
        """Event filter to reposition the wrap icon to the bottom-right of widget."""
        if event.type() == QtCore.QEvent.Resize and not isinstance(obj, QtWidgets.QScrollBar):
            # can ignore the scrollBar resize events
            self._onUpdateRequest()
        return super().eventFilter(obj, event)

    def _onUpdateRequest(self):
        """Position the wrap icon to the bottom-right of the widget."""
        vPort = self.viewport()
        if self._wrapButtonEnabled:
            self._label.move(vPort.width() - self._label.width() - (_GRIPSIZE if self._gripEnabled else 0),
                             vPort.height() - self._label.height())
        if self._gripEnabled:
            self._gripper.move(vPort.width() - _GRIPSIZE, vPort.height() - _GRIPSIZE)  # hard-coded in stylesheet

    def _setStyle(self):
        """Set the focus/noFocus colours for the widget.
        """
        _gripIcon = Icon('icons/grip')
        _style = """
                    QPlainTextEdit {
                        border: 1px solid palette(mid);
                        border-radius: 2px;
                    }
                    QPlainTextEdit:focus {
                        border: 1px solid palette(highlight);
                        border-radius: 2px;
                    }
                    QSizeGrip {
                        image: url(%s);
                        width: 20px; height: 20px;
                    }
                    """
        self.setStyleSheet(_style % aPath(_gripIcon._filePath).as_posix())

    def _toggleWordWrap(self):
        wordWrap = (self.lineWrapMode() != QtWidgets.QTextEdit.WidgetWidth)
        self._setWrapIcon(wordWrap)

    def _setWrapIcon(self, wordWrap):
        if wordWrap:
            self._label.setPixmap(self._wrapIconOn.pixmap(20, 20))
        else:
            self._label.setPixmap(self._wrapIconOff.pixmap(20, 20))
        self.setLineWrapMode(self.WidgetWidth if wordWrap else self.NoWrap)

    def context_menu(self):
        a = self.createStandardContextMenu()
        actions = a.actions()
        edit = Action(a, text='Fonts', callback=self._setFont)
        try:
            # need to find why this is using '3'
            a.insertAction(actions[3], edit)
        except Exception:
            a.addAction(edit)
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
            self._changed = False
        super().focusOutEvent(event)

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
        from ccpn.ui.gui.widgets.FileDialog import MacrosFileDialog

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
            width = max(self.minimumWidth(), self._widthStart + delta.x(), _size.width())
            height = max(self.minimumWidth(), self._heightStart + delta.y(), _size.height())

            self.setMinimumSize(width, height)
            self.updateGeometry()

    def _updateHeight(self):
        self._changed = True
        # Override the resize event to fit to contents
        if self._fitToContents:
            rowHeight = QtGui.QFontMetrics(self.document().defaultFont()).height()
            lineCount = self.document().lineCount()
            minHeight = (rowHeight + 1) * (lineCount + 1)
            self._maxHeight = max(self._minimumHeight, minHeight)
            self.setMaximumHeight(self._maxHeight)


#=========================================================================================
# main
#=========================================================================================

def main():
    import ccpn.core  # noqa
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog

    app = TestApplication()  # noqa

    popup = CcpnDialog(windowTitle='Test widget', setLayout=True)
    PlainTextEditor(parent=popup, grid=(0, 0), addWrapButton=True)
    popup.exec_()


if __name__ == '__main__':
    main()
