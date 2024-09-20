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
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.util.Colour import hexToRgb


MINHEIGHT = 12


class HLine(Widget):
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

    def __init__(self, parent=None, style=SOLID_LINE, colour=QtCore.Qt.black, height=None, lineWidth=2, **kwds):
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
        self.setMinimumHeight(max(MINHEIGHT, height or MINHEIGHT))

    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawLine(qp, self._style)
        qp.end()

    def drawLine(self, qp, style=None):

        geomRect = self.rect()
        linePos = (geomRect.top() + geomRect.bottom() + 2) // 2

        if style in self._styles:
            style = self._styles[style]
            try:
                pen = QtGui.QPen(self._colour, self._lineWidth, style)
            except:
                pen = QtGui.QPen(QtGui.QColor(*hexToRgb(self._colour)), self._lineWidth, style)

            qp.setPen(pen)
            qp.drawLine(geomRect.left(), linePos, geomRect.right(), linePos)


class LabeledHLine(Frame):
    """A class to make a Frame with an Hline - Label - Hline
    """

    def __init__(self, parent=None, height=None, text=None, bold=False, sides='both',
                 style=HLine.SOLID_LINE, colour=QtCore.Qt.black, lineWidth=2,
                 **kwds):
        """
        Draw a horizontal line and a label
        :param parent:
        :param height:
        :param text:
        :param bold:
        :param sides: either of 'both', 'left', 'right'
        :param style:
        :param colour:
        :param lineWidth:
        :param kwds:
        """
        if sides not in ['left', 'right', 'both']:
            raise RuntimeError('sides not defined correctly')
        self._sides = sides

        super(LabeledHLine, self).__init__(parent=parent, setLayout=True, showBorder=False, **kwds)

        # the label with text
        self._line1 = HLine(parent=self, grid=(0, 0), style=style, colour=colour, lineWidth=lineWidth, height=height,
                            hPolicy='expanding', vPolicy='minimumexpanding')
        self._label = Label(parent=self, grid=(0, 1), text=text, bold=bold, hPolicy='fixed')
        self._line2 = HLine(parent=self, grid=(0, 2), style=style, colour=colour, lineWidth=lineWidth, height=height,
                            hPolicy='expanding', vPolicy='minimumexpanding')

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self._updateLines()

    @property
    def sides(self):
        return self._sides

    @sides.setter
    def sides(self, value):
        if value not in ['left', 'right', 'both']:
            raise RuntimeError('sides not defined correctly')
        self._sides = value

        self._updateLines()

    def _updateLines(self):
        """Update the visibility of the left/right lines.
        """
        if self._sides == 'left':
            self._line1.show()
            self._line2.hide()
        elif self._sides == 'right':
            self._line1.hide()
            self._line2.show()
        else:
            self._line1.show()
            self._line2.show()
        if not (txt := bool(self._label.get())):
            if self._sides == 'left':
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
    Label(parent=popup, grid=(0, 0), text='Just some text')
    HLine(parent=popup, grid=(1, 0), hPolicy='expanding', spacing=(0, 0))
    Label(parent=popup, grid=(2, 0), text='Just some text to separate')
    LabeledHLine(parent=popup, grid=(3, 0), text='a line with text')
    popup.exec_()


if __name__ == '__main__':
    main()
