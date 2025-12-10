from pygments.styles import get_style_by_name
from pyqode.core.api import TextBlockHelper, SyntaxHighlighter
from pyqode.core.api.mode import Mode
from PyQt5 import QtGui, QtCore


class StarHighlighter(SyntaxHighlighter):
    """
    Custom syntax highlighter for PyQode using Pygments.
    """

    def __init__(self, parent, lexer, style='monokai'):
        """
        :param parent: QTextDocument (provided by PyQode)
        :param lexer: Instance of a Pygments lexer
        :param style: Pygments style name
        """
        super().__init__(parent)

        self._lexer = lexer
        self._style = get_style_by_name(style)

    def highlight_block(self, text, block):
        """
        Applies syntax highlighting using Pygments.
        :param text: Current line of text
        :param block: QTextBlock (ignored)
        """
        offset = 0  # Tracks position in the text
        for tokenType, value in self._lexer.get_tokens(text):
            length = len(value)
            if length == 0:
                continue
            fmt = self._getTextCharFormat(tokenType)
            self.setFormat(offset, length, fmt)
            offset += length  # Move to next token

    def _getTextCharFormat(self, tokenType):
        """
        Converts a Pygments token type into a QTextCharFormat.
        """
        fmt = QtGui.QTextCharFormat()
        style = self._style.style_for_token(tokenType)

        if style['color']:
            fmt.setForeground(QtGui.QColor(f'#{style["color"]}'))
        if style['bold']:
            fmt.setFontWeight(QtGui.QFont.Bold)
        if style['italic']:
            fmt.setFontItalic(True)
        if style['underline']:
            fmt.setUnderlineStyle(QtGui.QTextCharFormat.SingleUnderline)

        return fmt
