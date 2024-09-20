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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-08-23 19:25:21 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister$"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import contextlib
from PyQt5 import QtWidgets, QtCore, QtGui
from ccpn.ui.gui.widgets.Base import Base
from ccpn.util.Colour import rgbRatioToHex
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import BOTTOMAXIS


SCROLLBAR_POLICY_DICT = dict(
        always=QtCore.Qt.ScrollBarAlwaysOn,
        never=QtCore.Qt.ScrollBarAlwaysOff,
        asNeeded=QtCore.Qt.ScrollBarAsNeeded,
        )


class ScrollArea(QtWidgets.QScrollArea, Base):

    def __init__(self, parent, scrollBarPolicies=('asNeeded', 'asNeeded'),
                 setLayout=True, minimumSizes=(50, 50), scrollDirections=('horizontal', 'vertical'), resizable=True,
                 **kwds):
        super().__init__(parent)

        # kwds['setLayout'] = True  # A scrollable area always needs a layout to function
        Base._init(self, setLayout=setLayout, **kwds)

        self.setScrollBarPolicies(scrollBarPolicies)
        self.setMinimumSizes(minimumSizes)
        self._scrollDirections = scrollDirections
        self._minimumSizes = minimumSizes
        self.setWidgetResizable(resizable)

    def setMinimumSizes(self, minimumSizes):
        """Set (minimumWidth, minimumHeight)
        """
        self.setMinimumWidth(minimumSizes[0])
        self.setMinimumHeight(minimumSizes[1])

    def setScrollBarPolicies(self, scrollBarPolicies=('asNeeded', 'asNeeded')):
        """Set the scrollbar policy: always, never, asNeeded
        """
        hp = SCROLLBAR_POLICY_DICT.get(scrollBarPolicies[0])
        vp = SCROLLBAR_POLICY_DICT.get(scrollBarPolicies[1])
        self.setHorizontalScrollBarPolicy(hp)
        self.setVerticalScrollBarPolicy(vp)

    def setWidget(self, widget):
        """Set the scroll area contents
        """
        super(ScrollArea, self).setWidget(widget)
        self._scrollContents = widget

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if None in self._scrollDirections or len(self._scrollDirections) != 2:
            widget = self.widget()
            if 'horizontal' not in self._scrollDirections:
                widget.setMaximumWidth(self.viewport().width())

            if 'vertical' not in self._scrollDirections:
                widget.setMaximumHeight(self.viewport().height())


class SpectrumDisplayScrollArea(ScrollArea):
    """
    Class to implement a scroll area containing a viewport with margins.
    The margins are defined to accommodate the axis widgets within the scroll bars

    """

    def __init__(self, parent, scrollBarPolicies=('asNeeded', 'asNeeded'),
                 setLayout=True, minimumSizes=(50, 50),
                 spectrumDisplay=None, cornerWidget=False, **kwds):
        """Initialise the widget
        """
        super().__init__(parent=parent, scrollBarPolicies=scrollBarPolicies, setLayout=setLayout, minimumSizes=minimumSizes)
        self._spectrumDisplay = spectrumDisplay

        # grab the background from the container
        palette = self._spectrumDisplay.palette()
        role = self._spectrumDisplay.backgroundRole()
        _col = palette.color(role)
        if cornerWidget:
            self._cornerWidget = _ScrollWidgetCorner(self, background=_col)
            if len(spectrumDisplay.axisCodes) <= 2:
                self._cornerWidget.setVisible(False)
        else:
            self._cornerWidget = None

    def resizeEvent(self, event):
        """Handle resize event to re-position the axis widgets and corner widget as required
        """
        super(ScrollArea, self).resizeEvent(event)
        self._updateAxisWidgets()

    def _updateAxisWidgets(self):
        """Update the positioning of the widgets as required
        """
        rect = self.viewport().geometry()
        with contextlib.suppress(Exception):
            from ccpn.ui.gui.widgets.GLAxis import GuiNdWidgetAxis
            from ccpn.ui.gui.widgets.GLAxis import Gui1dWidgetAxis

            with contextlib.suppress(Exception):
                offset = 0
                if len(self._spectrumDisplay.axisCodes) > 2:
                    offset = self._spectrumDisplay.strips[0]._stripToolBarWidget.height()

            _width = max(rect.width(), self._minimumSizes[0])
            _height = max(rect.height(), self._minimumSizes[1]) - offset
            margins = self._viewportMargins

            if children := self.findChildren((Gui1dWidgetAxis, GuiNdWidgetAxis)):
                for child in children:
                    if child._axisType == BOTTOMAXIS:
                        # resize the X axis widgets - allow for frame-border
                        child.setGeometry(1, rect.height() + 1, _width, margins[3])
                    else:
                        # resize the Y axis widgets
                        child.setGeometry(rect.width() + 1, 1, margins[2], _height)

            if self._cornerWidget:
                self._cornerWidget.setGeometry(_width, _height, margins[2], offset)

    def refreshViewPort(self):
        from ccpn.ui.gui.widgets.GLAxis import GuiNdWidgetAxis
        from ccpn.ui.gui.widgets.GLAxis import Gui1dWidgetAxis

        self._updateAxisWidgets()

        if children := self.findChildren((Gui1dWidgetAxis, GuiNdWidgetAxis)):
            for child in children:
                child._updateAxes = True
                child.update()

    def setViewportMargins(self, *margins):
        """Set the viewport margins and keep a local copy
        """
        super().setViewportMargins(*margins)
        self._viewportMargins = margins

    def setCornerBackground(self, colour):
        """Set the background colour (or None)
        """
        if self._cornerWidget:
            self._cornerWidget.setBackGround(colour)


class _ScrollWidgetCorner(QtWidgets.QWidget):
    """
    Class to handle a simple widget item with a constant painted background
    Item is to be resized by parent handler
    """

    def __init__(self, parent, background=None, **kwds):
        """Initialise the widget
        """
        super().__init__(parent=parent, **kwds)
        self._parent = parent
        self._background = None
        if background:
            self.setBackground(background)

    def setBackground(self, colour):
        """Set the background colour (or None)
        """
        try:
            # try a QColor first
            self._background = QtGui.QColor(colour)
        except Exception:
            # otherwise assume to be a tuple (0..1, 0..1, 0..1, 0..1, 0..1)
            if type(colour) != tuple or \
                    len(colour) != 4 or \
                    any(not isinstance(val, float) for val in colour) or \
                    any(not (0 <= col <= 1) for col in colour):
                raise TypeError("colour must be a tuple(r, g, b, alpha)") from None

            self._background = QtGui.QColor(rgbRatioToHex(*colour[:3]))

            try:
                self._background = QtGui.QColor(rgbRatioToHex(*colour[:3]))
            except Exception:
                raise TypeError("colour must be a tuple(r, g, b, alpha)") from None

    def paintEvent(self, a0: QtGui.QPaintEvent):
        """Paint the background in the required colour
        """
        if self._background is not None:
            p = QtGui.QPainter(self)
            rgn = self.rect()
            p.fillRect(rgn, self._background)
            p.end()
