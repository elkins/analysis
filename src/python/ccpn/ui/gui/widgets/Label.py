"""Module Documentation here

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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-08-23 18:53:02 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtWidgets, QtCore
from pyqtgraph.widgets.VerticalLabel import VerticalLabel as pyqtVerticalLabel

from ccpn.ui.gui.widgets.Base import Base, HALIGN_DICT
from ccpn.framework.Translation import translator
import ccpn.ui.gui.guiSettings as guiSettings
from ccpn.ui.gui.widgets.Icon import Icon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg


def maTex2Pixmap(mathTex, fontSize=10):
    """
    https://matplotlib.org/3.5.0/tutorials/text/mathtext.html
    Convert a str with  Matplotlib-laTex syntax to a Pixmap.
    :param mathTex: A string with  Matplotlib-laTex syntax
    :param fontSize: int
    :return: QPixmap
    """
    #####  set up a mpl figure instance
    fig = plt.figure()
    fig.patch.set_facecolor('none')
    fig.set_canvas(FigureCanvasAgg(fig))
    renderer = fig.canvas.get_renderer()

    ##### plot the mathTex expression ----
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    ax.patch.set_facecolor('none')
    t = ax.text(0, 0, mathTex, ha='left', va='bottom', fontsize=fontSize)

    ##### fit figure size to text artist
    fwidth, fheight = fig.get_size_inches()
    fig_bbox = fig.get_window_extent(renderer)
    text_bbox = t.get_window_extent(renderer)
    tight_fwidth = text_bbox.width * fwidth / fig_bbox.width
    tight_fheight = text_bbox.height * fheight / fig_bbox.height
    fig.set_size_inches(tight_fwidth, tight_fheight)

    ##### convert mpl figure to QPixmap
    buf, size = fig.canvas.print_to_buffer()
    qimage = QtGui.QImage.rgbSwapped(QtGui.QImage(buf, size[0], size[1], QtGui.QImage.Format_ARGB32))
    # fig.close()
    qpixmap = QtGui.QPixmap(qimage)
    return qpixmap


class Label(QtWidgets.QLabel, Base):
    _styleSheet = """QLabel {
            color: %s;
            margin-left: %dpx;
            margin-top: %dpx;
            margin-right: %dpx;
            margin-bottom: %dpx;
            border: 0px;
            }"""

    def __init__(self, parent=None,
                 text='', textColour=None, textSize=None, bold=False, italic=False,
                 margins=[2, 1, 2, 1], icon=None, iconSize=(16, 16), **kwds):

        super().__init__(parent)
        Base._init(self, **kwds)

        text = translator.translate(text)
        self.setText(text)

        self._textSize = textSize
        self._bold = 'bold' if bold else 'normal'
        self._margins = margins

        if bold or textSize or italic:
            _font = self.font()
            if bold:
                _font.setBold(True)
            if italic:
                _font.setItalic(True)
            if textSize:
                _font.setPointSize(textSize)
            self.setFont(_font)

        colours = guiSettings.getColours()
        self._colour = textColour or colours[guiSettings.LABEL_FOREGROUND]
        self._setStyleSheet()

        if isinstance(icon, Icon):
            self.setPixmap(icon.pixmap(*iconSize))
        elif isinstance(icon, QtGui.QPixmap):
            self.setPixmap(icon)

    def get(self):
        """get the label text
        """
        return self.text()

    def set(self, text=''):
        """set label text, applying translator
        """
        text = translator.translate(text)
        self.setText(text)

    def _setStyleSheet(self):
        self.setStyleSheet(self._styleSheet % (  #self._textSize,
            # self._bold,
            self._colour,
            self._margins[0],
            self._margins[1],
            self._margins[2],
            self._margins[3],
            )
                           )

    def setTextColour(self, colour):
        """Set the text colour for the label.
        """
        self._colour = colour.name()
        self._setStyleSheet()


class DividerLabel(Label):

    def __init__(self, parent=None, text='', icon=None, iconSize=(25, 25), margins=[10, 1, 10, 1], hAlign='c', **kwds):
        super().__init__(parent=parent, text=text, icon=icon, iconSize=iconSize, margins=margins, hAlign=hAlign, **kwds)

        self.icon = icon
        if not self.icon:
            icon = Icon('icons/divider')
            self.setPixmap(icon.pixmap(*iconSize))


class ActiveLabel(Label):

    def __init__(self, parent=None, mainWindow=None,
                 text='', textColour=None, textSize=12, bold=False,
                 margins=[2, 1, 2, 1], selectionCallback=None, actionCallback=None, **kwds):
        super().__init__(parent=parent, text=text, textColour=textColour, textSize=textSize, bold=bold,
                         margins=margins, **kwds)

        self.mainWindow = mainWindow
        self._selectionCallback = selectionCallback
        self._actionCallback = actionCallback
        self._enterCallback = None
        self._leaveCallback = None

        # required highlighting flag for changing colour themes
        self.highlighted = False

    def setSelectionCallback(self, callback=None):
        """Sets callback on mouse click
        """
        self._selectionCallback = callback

    def setActionCallback(self, callback=None):
        """Sets callback on mouse double click
        """
        self._actionCallback = callback

    def mouseReleaseEvent(self, ev):
        """Handle double click and call _selectionCallback if set
        """
        if self._selectionCallback:
            self._selectionCallback()
        super().mouseReleaseEvent(ev)

    def mouseDoubleClickEvent(self, ev):
        """Handle double click and call _actionCallback if set
        """
        if self._actionCallback:
            self._actionCallback()
        super().mouseDoubleClickEvent(ev)

    def setEnterLeaveCallback(self, enterCallback, leaveCallback):
        self._enterCallback = enterCallback
        self._leaveCallback = leaveCallback

    def enterEvent(self, ev) -> None:
        super().enterEvent(ev)
        if self._enterCallback:
            self._enterCallback()

    def leaveEvent(self, ev) -> None:
        super().leaveEvent(ev)
        if self._leaveCallback:
            self._leaveCallback()


class VerticalLabel(pyqtVerticalLabel, Base):
    _styleSheet = """
    QLabel {
            font-size: %spt;
            font-weight: %s;
            color: %s;
            margin-left: %dpx;
            margin-top: %dpx;
            margin-right: %dpx;
            margin-bottom: %dpx;
            border: 0px;
            }
    """

    def __init__(self, parent=None, text='', textColour=None, textSize=12, bold=False,
                 margins=[2, 1, 2, 1], orientation='horizontal', **kwds):
        super().__init__(parent, orientation=orientation, forceWidth=False)
        Base._init(self, **kwds)

        text = translator.translate(text)
        self.setText(text)

        # if textColor:
        #   self.setStyleSheet('QLabel {color: %s}' % textColor)
        # if textSize and textColor:
        #   self.setStyleSheet('QLabel {font-size: %s; color: %s;}' % (textSize, textColor))
        # if bold:
        #   self.setStyleSheet('QLabel {font-weight: bold;}')

        self._textSize = textSize
        self._bold = 'bold' if bold else 'normal'
        self._margins = margins

        # this appears not to pick up the colour as set by the stylesheet!
        # self._colour = textColor if textColor else self.palette().color(QtGui.QPalette.WindowText).name()

        colours = guiSettings.getColours()
        self._colour = textColour if textColour else colours[guiSettings.LABEL_FOREGROUND]
        self._setStyleSheet()

    def get(self):
        "get the label text"
        return self.text()

    def set(self, text=''):
        "set label text, applying translator"
        text = translator.translate(text)
        self.setText(text)

    def _setStyleSheet(self):
        self.setStyleSheet(self._styleSheet % (self._textSize,
                                               self._bold,
                                               self._colour,
                                               self._margins[0],
                                               self._margins[1],
                                               self._margins[2],
                                               self._margins[3],
                                               )
                           )


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.widgets.Button import Button
    from ccpn.ui.gui.widgets.Icon import Icon
    from ccpn.ui.gui.popups.Dialog import CcpnDialog


    mathExamples = [
        r'$\sqrt{\frac{1}{N}\sum_{i=0}^N (\alpha_i*\delta_i)^2}$',
        '$k_{soil}=\\frac{\\sum f_j k_j \\theta_j}{\\sum f_j \\theta_j}$',
        '$\\lambda_{soil}=k_{soil} / C_{soil}$']

    app = TestApplication()
    pixmap = maTex2Pixmap(f'A test label with equation:  {mathExamples[0]}')
    popup = CcpnDialog(windowTitle='Test Table', setLayout=True)
    label = Label(popup, text='', icon=pixmap, grid=(0, 0))
    popup.show()
    popup.raise_()
    app.start()
