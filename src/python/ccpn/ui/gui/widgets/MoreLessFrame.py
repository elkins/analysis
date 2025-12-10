"""
Module Documentation here
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
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-05-27 16:32:49 +0000 (Wed, May 27, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Label import ActiveLabel
from ccpn.ui.gui.widgets.Font import getFontHeight
from ccpn.ui.gui.widgets.Spacer import Spacer


class MoreLessFrame(Frame):
    """
    Widget that contains a button to expand/contract show more/less subframe containing more options
    """
    DEFAULTMARGINS = (0, 2, 0, 0)  # l, t, r, b

    def __init__(self, parent, name=None, showMore=True,
                 scrollable=False, closable=False,
                 showBorder=True, borderColour=None, frameMargins=DEFAULTMARGINS, **kwds):
        """Initialise the widget
        """
        kwds.pop('setLayout', None)
        super().__init__(parent=parent, setLayout=True, **kwds)
        self._name = name
        self._showMore = showMore
        self._callback = None
        self._showBorder = showBorder
        self._borderColour = borderColour
        self._closable = closable
        self._minusIcon = Icon('icons/minus-large')
        self._plusIcon = Icon('icons/plus-large')
        self._closeIcon = Icon('icons/reset-2')  # close-icon, to the right of text
        self.PIXMAPWIDTH = getFontHeight()
        self._setWidgets(frameMargins, kwds, name, scrollable)
        self._showContents(showMore)
        self._lastSize = QtCore.QSize(self.sizeHint())

    def _setWidgets(self, frameMargins, kwds, name, scrollable):
        row = 0
        self._openButton = ActiveLabel(self, grid=(row, 0))
        self._openButton.setFixedSize(self.PIXMAPWIDTH + 3, self.PIXMAPWIDTH + 3)
        self._openButton.setPixmap(self._minusIcon.pixmap(self.PIXMAPWIDTH, self.PIXMAPWIDTH))
        bold = kwds.get('bold', False)
        self._label = ActiveLabel(self, text=name or '', grid=(row, 1), bold=bold)
        # fix to the size of its text
        self._label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        if self._closable:
            self._closeButton = ActiveLabel(self, grid=(row, 2))
            self._closeButton.setFixedSize(self.PIXMAPWIDTH, self.PIXMAPWIDTH)
            self._closeButton.setPixmap(self._closeIcon.pixmap(self.PIXMAPWIDTH - 5, self.PIXMAPWIDTH - 5))
            self._closeButton.sigClicked.connect(self.close)  # noqa: pycharm can't see qt

        row += 1
        self._openButton.setSelectionCallback(self._toggleContents)
        self._label.setSelectionCallback(self._toggleContents)

        if scrollable:
            # add a frame with scroll-bars
            self._contentsFrame = ScrollableFrame(self, setLayout=True, grid=(row, 0), gridSpan=(1, 4))
            self.scrollArea = self._contentsFrame.scrollArea
        else:
            self._contentsFrame = Frame(self, setLayout=True, showBorder=False, grid=(row, 0), gridSpan=(1, 4))
            self.scrollArea = None

        Spacer(self, 5, 5,
               QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding,
               grid=(row, 0), gridSpan=(1, 4))
        self.setContentsMargins(*frameMargins)

    def _showContents(self, visible):
        """Toggle visibility of the contents-widget.
        """
        self._contentsFrame.setVisible(visible)
        if visible:
            self._openButton.setPixmap(self._minusIcon.pixmap(self.PIXMAPWIDTH, self.PIXMAPWIDTH))
            # arbitrary large height
            self.setMaximumHeight(2000)
        else:
            self._openButton.setPixmap(self._plusIcon.pixmap(self.PIXMAPWIDTH, self.PIXMAPWIDTH))
            # collapse the contents
            self.setMaximumHeight(self.sizeHint().height())

        if self._callback:
            self._callback(self)

    def setCallback(self, callback):
        """Set a callback to the frame from the parent.
        """
        self._callback = callback

    def _toggleContents(self):
        """Toggle visibility of the contents.
        """
        visible = not self._contentsFrame.isVisible()
        self._showContents(visible)

    @property
    def contentsVisible(self):
        """Return True if the contents are visible.
        """
        return self._contentsFrame.isVisible()

    def setContentsVisible(self, state: bool):
        """Open/Close the frame.
        """
        self._showContents(state)

    @property
    def name(self):
        """Set/get the name of the widget.
        """
        return self._label.get()

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError(f'name {value} must be a string')
        self._name = value
        self._label.setText(value)

    @property
    def contentsFrame(self):
        """Get the contents frame.
        """
        return self._contentsFrame

    def paintEvent(self, ev):
        """Paint the border.
        """
        if not self._showBorder:
            return
        # create a painter over the widget - shrink by 1 pixel to draw correctly
        p = QtGui.QPainter(self)
        rgn = self.rect().adjusted(0, 0, -1, -1)
        # get the size of the box to draw in and define the point list
        _size = self._label.sizeHint()
        h, w = _size.height(), (_size.width() +
                                self._openButton.sizeHint().width() +
                                (self._closeButton.sizeHint().width() if self._closable else 0))
        offset = w
        points0 = [QtCore.QPoint(0, 1),
                   QtCore.QPoint(offset + 2, 1),
                   QtCore.QPoint(offset + 2, 1),
                   QtCore.QPoint(offset + h, h - 1),
                   QtCore.QPoint(offset + h + 1, h - 1),
                   QtCore.QPoint(rgn.width() + 1, h - 1),
                   ]
        points1 = [QtCore.QPoint(offset + 3, 2),
                   QtCore.QPoint(offset + h - 1, h - 2),
                   ]
        # draw the lines - use defined colour (or from palette to follow theme correctly)
        p.setPen(QtGui.QPen(self._borderColour or self.palette().dark().color(), 1))
        # add a little smoothing
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.drawLines(*points1)
        p.setRenderHint(QtGui.QPainter.Antialiasing, False)
        p.drawLines(*points0)
        p.end()

    def closeEvent(self, event):
        """Clean-up and close.
        """
        from ccpn.ui.gui.lib.WidgetClosingLib import CloseHandler

        with CloseHandler(self):
            super().closeEvent(event)
