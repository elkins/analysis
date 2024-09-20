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
__dateModified__ = "$dateModified: 2024-04-04 15:19:25 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:42 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtCore, QtWidgets
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.Label import VerticalLabel
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.util.Colour import hexToRgb


MINWIDTH = 12


class VLine(Widget):
    SOLID_LINE = 'SolidLine'
    DASH_LINE = 'DashLine'
    DASH_DOT_LINE = 'DashDotLine'
    DASH_DOT_DOT_LINE = 'DashDotDotLine'

    _styles = {
        SOLID_LINE       : QtCore.Qt.SolidLine,
        DASH_LINE        : QtCore.Qt.DashLine,
        DASH_DOT_LINE    : QtCore.Qt.DashDotLine,
        DASH_DOT_DOT_LINE: QtCore.Qt.DashDotDotLine,
        }

    def __init__(self, parent=None, style=SOLID_LINE, colour=QtCore.Qt.black, width=None, lineWidth=2, **kwds):
        """
        :param style: Options:
                              'SolidLine';
                               'DashLine';
                               'DashDotLine';
                               'DashDotDotLine'
        """

        super().__init__(parent, **kwds)
        self._parent = parent
        self._style = style
        self._colour = colour
        self._lineWidth = lineWidth
        self.setMinimumWidth(max(MINWIDTH, width or MINWIDTH))

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawLine(qp, self._style)
        qp.end()

    def drawLine(self, qp, style=None):

        geomRect = self.rect()
        linePos = (geomRect.left() + geomRect.right() + 2) // 2

        if style in self._styles:
            style = self._styles[style]
            try:
                pen = QtGui.QPen(self._colour, self._lineWidth, style)
            except:
                pen = QtGui.QPen(QtGui.QColor(*hexToRgb(self._colour)), self._lineWidth, style)

            qp.setPen(pen)
            qp.drawLine(linePos, geomRect.top(), linePos, geomRect.bottom())


class LabeledVLine(Frame):
    """A class to make a Frame with a VLine - Label - VLine
    """

    def __init__(self, parent=None, width=None, text=None, bold=False, sides='both',
                 style=VLine.SOLID_LINE, colour=QtCore.Qt.black, lineWidth=2,
                 **kwds):
        """
        Draw a horizontal line and a label
        :param parent:
        :param width:
        :param text:
        :param bold:
        :param sides: either of 'both', 'top', 'bottom'
        :param style:
        :param colour:
        :param lineWidth:
        :param kwds:
        """
        if sides not in ['top', 'bottom', 'both']:
            raise RuntimeError('sides not defined correctly')
        self._sides = sides

        super().__init__(parent=parent, setLayout=True, showBorder=True, **kwds)

        # the label with text
        self._line1 = VLine(parent=self, grid=(2, 0), style=style, colour=colour, lineWidth=lineWidth, width=width,
                            vPolicy='expanding', hPolicy='minimumexpanding')
        self._label = VerticalLabel(parent=self, grid=(1, 0), text=text, bold=bold, orientation='vertical', vPolicy='fixed')
        self._line2 = VLine(parent=self, grid=(0, 0), style=style, colour=colour, lineWidth=lineWidth, width=width,
                            vPolicy='expanding', hPolicy='minimumexpanding')

        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)

        self._updateLines()

    @property
    def sides(self):
        return self._sides

    @sides.setter
    def sides(self, value):
        if value not in ['top', 'bottom', 'both']:
            raise RuntimeError('sides not defined correctly')
        self._sides = value

        self._updateLines()

    def _updateLines(self):
        """Update the visibility of the top/bottom lines.
        """
        if self._sides == 'bottom':
            self._line1.show()
            self._line2.hide()
        elif self._sides == 'top':
            self._line1.hide()
            self._line2.show()
        else:
            self._line1.show()
            self._line2.show()
        if not (txt := bool(self._label.get())):
            if self._sides == 'bottom':
                self._line2.hide()
            else:
                self._line1.hide()

        self._label.setVisible(txt)

    def setText(self, text):
        """Set the text of the widget.
        """
        self._label.setText(text)
        self._updateLines()


def main():
    # required import
    import ccpn.core
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog

    # app needs to be referenced until termination of main
    app = TestApplication()
    popup = CcpnDialog(windowTitle='Test HLine', setLayout=True)
    VLine(parent=popup, grid=(0, 0))
    LabeledVLine(parent=popup, grid=(0, 1), text='a line with text')
    VLine(parent=popup, grid=(0, 2), vPolicy='expanding', spacing=(0, 0))
    LabeledVLine(parent=popup, grid=(0, 3), text='another line with text', sides='top')
    popup.exec_()


if __name__ == '__main__':
    main()
