"""Module Documentation here

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-08-27 15:33:12 +0100 (Tue, August 27, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtWidgets
from pyqtgraph.widgets.VerticalLabel import VerticalLabel as pyqtVerticalLabel

from ccpn.ui.gui.widgets.Base import Base
from ccpn.framework.Translation import translator
import ccpn.ui.gui.guiSettings as guiSettings
from ccpn.ui.gui.widgets.Icon import Icon
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

#
# def maTex2Pixmap(mathTex, fontSize=15):
#     """
#     https://matplotlib.org/3.5.0/tutorials/text/mathtext.html
#     Convert a str with  Matplotlib-laTex syntax to a Pixmap.
#     :param mathTex: A string with  Matplotlib-laTex syntax
#     :param fontSize: int
#     :return: QPixmap
#     """
#     #####  set up a mpl figure instance
#     fig = plt.figure()
#     fig.patch.set_facecolor('none')
#     fig.set_canvas(FigureCanvasAgg(fig))
#     renderer = fig.canvas.get_renderer()
#
#     ##### plot the mathTex expression ----
#     ax = fig.add_axes([0, 0, 1, 1])
#     ax.axis('off')
#     ax.patch.set_facecolor('none')
#     t = ax.text(0, 0, mathTex, ha='left', va='bottom', fontsize=fontSize)
#
#     ##### fit figure size to text artist
#     fwidth, fheight = fig.get_size_inches()
#     fig_bbox = fig.get_window_extent(renderer)
#     text_bbox = t.get_window_extent(renderer)
#     tight_fwidth = text_bbox.width * fwidth / fig_bbox.width
#     tight_fheight = text_bbox.height * fheight / fig_bbox.height
#     fig.set_size_inches(tight_fwidth, tight_fheight)
#
#     ##### convert mpl figure to QPixmap
#     buf, size = fig.canvas.print_to_buffer()
#     qimage = QtGui.QImage.rgbSwapped(QtGui.QImage(buf, size[0], size[1], QtGui.QImage.Format_ARGB32))
#     plt.close(fig)  # Close the figure to release resources
#     qpixmap = QtGui.QPixmap(qimage)
#     return qpixmap
#
#
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_agg import FigureCanvasAgg
# from PyQt5 import QtGui


def maTex2Pixmap(mathTex, fontSize=14):
    """
    Converts a string with Matplotlib-LaTeX syntax to a QPixmap.

    :param mathTex: A string with Matplotlib-LaTeX syntax.
    :param fontSize: int, font size for the rendered text.
    :return: QPixmap containing the rendered LaTeX formula.
    """
    # Set up a matplotlib figure instance
    fig = plt.figure()
    fig.patch.set_facecolor('none')
    fig.set_canvas(FigureCanvasAgg(fig))
    renderer = fig.canvas.get_renderer()


    # Plot the mathTex expression
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    ax.patch.set_facecolor('none')

    # Render the text using the specified font size
    t = ax.text(0, 0, mathTex, ha='left', va='bottom', fontsize=fontSize, usetex=False)

    # Adjust the figure size to fit the text
    fwidth, fheight = fig.get_size_inches()
    fig_bbox = fig.get_window_extent(renderer)
    text_bbox = t.get_window_extent(renderer)
    tight_fwidth = text_bbox.width * fwidth / fig_bbox.width
    tight_fheight = text_bbox.height * fheight / fig_bbox.height
    fig.set_size_inches(tight_fwidth, tight_fheight)

    # Convert the matplotlib figure to a QPixmap
    buf, size = fig.canvas.print_to_buffer()
    qimage = QtGui.QImage.rgbSwapped(QtGui.QImage(buf, size[0], size[1], QtGui.QImage.Format_ARGB32))

    qpixmap = QtGui.QPixmap(qimage)
    plt.close(fig)  # Close the figure to release resources
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
                 margins=[2, 1, 2, 1], icon=None, iconSize=(16, 16),
                 **kwds):
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
        self._colour = textColour or None #colours[guiSettings.LABEL_FOREGROUND]
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
            self._colour or 'palette(windowText)',
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
    _styleSheet = """QLabel {
            color: %s;
            margin-left: %dpx;
            margin-top: %dpx;
            margin-right: %dpx;
            margin-bottom: %dpx;
            border: 0px;
            }
    """

    def __init__(self, parent=None,
                 text='', textColour=None, textSize=None, bold=False, italic=False,
                 margins=[1, 2, 1, 2], icon=None, iconSize=(16, 16),
                 orientation='vertical', **kwds):
        super().__init__(parent, orientation=orientation, forceWidth=False)
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
        self._colour = textColour or None #colours[guiSettings.LABEL_FOREGROUND]
        self._setStyleSheet()

        if isinstance(icon, Icon):
            self.setPixmap(icon.pixmap(*iconSize))
        elif isinstance(icon, QtGui.QPixmap):
            self.setPixmap(icon)

    def get(self):
        """get the label text"""
        return self.text()

    def set(self, text=''):
        """set label text, applying translator"""
        text = translator.translate(text)
        self.setText(text)

    def _setStyleSheet(self):
        self.setStyleSheet(self._styleSheet % (  #self._textSize,
            #self._bold,
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

def maTex2Pixmap2(mathTex, fontSize=10):
    """
    Convert a string with Matplotlib-LaTeX syntax to a QPixmap using Matplotlib's native mathtext.
    :param mathTex: A string with Matplotlib-LaTeX syntax
    :param fontSize: int
    :return: QPixmap
    """
    # Set up Matplotlib for consistent font sizes
    plt.rcParams['text.usetex'] = True

    # Set up a Matplotlib figure instance
    fig = plt.figure()
    fig.patch.set_facecolor('none')
    fig.set_canvas(FigureCanvasAgg(fig))
    renderer = fig.canvas.get_renderer()

    # Plot the mathTex expression
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    ax.patch.set_facecolor('none')
    t = ax.text(0, 0, mathTex, ha='left', va='bottom', fontsize=fontSize)

    # Fit figure size to text artist
    fwidth, fheight = fig.get_size_inches()
    fig_bbox = fig.get_window_extent(renderer)
    text_bbox = t.get_window_extent(renderer)
    tight_fwidth = text_bbox.width * fwidth / fig_bbox.width
    tight_fheight = text_bbox.height * fheight / fig_bbox.height
    fig.set_size_inches(tight_fwidth, tight_fheight)

    # Convert Matplotlib figure to QPixmap
    buf, size = fig.canvas.print_to_buffer()
    qimage = QtGui.QImage.rgbSwapped(QtGui.QImage(buf, size[0], size[1], QtGui.QImage.Format_ARGB32))
    qpixmap = QtGui.QPixmap(qimage)
    return qpixmap


if __name__ == '__main__':

    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog

    mathExamples = [
        r'$\sqrt{\frac{1}{N}\sum_{i=0}^N (\alpha_i*\delta_i)^2}$',
        '$k_{soil}=A\\frac{\\sum f_j k_j \\theta_j}{\\sum f_j \\theta_j}$',
        '$\\lambda_{soil}=k_{soil} / C_{soil}-k_{soil} / C_{soil} $',
        r'$Y = B +6+\frac{(A + x + B - \sqrt{(A + x + B)^2 - 4 A x})}{2 A}$',
        r'$Y = \mathregular{B} + \mathregular{6} + \frac{(A + x + B - \sqrt{(A + x + B)^2 - 4 A x})}{2 A}$'
        ]

    app = TestApplication()
    popup = CcpnDialog(windowTitle='Test Table', setLayout=True)
    fontSize = 14
    for i, mathExample in enumerate(mathExamples):
        pixmap = maTex2Pixmap(f'{mathExample}',fontSize=fontSize)
        label = Label(popup, text='', icon=pixmap, grid=(i, 0))
        pixmap2 = maTex2Pixmap2(f'{mathExample}', fontSize=fontSize)
        label2 = Label(popup, text='', icon=pixmap2, grid=(i, 1))
    popup.show()
    popup.raise_()
    app.start()
