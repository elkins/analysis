"""
The module implements widget and scrollable widget class

Widget(parent=None, setLayout=False, **kwds)

ScrollableWidget(parent=None, setLayout=False,
                 minimumSizes=(50,50), scrollBarPolicies=('asNeeded','asNeeded'), **kwds)


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
__dateModified__ = "$dateModified: 2025-02-25 15:04:59 +0000 (Tue, February 25, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtWidgets
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.ScrollArea import ScrollArea
from ccpn.util.Colour import rgbRatioToHex


class Widget(QtWidgets.QWidget, Base):
    """
    Class to handle a simple widget item
    """

    def __init__(self, parent=None, setLayout=False, acceptDrops=False, **kwds):
        """General widget; default accepts drops (for now)
        """

        # print('DEBUG Widget: acceptDrops=%s, setLayout=%s, **kwds=%s' % (setLayout, acceptDrops, kwds))

        super().__init__(parent=parent)
        Base._init(self, acceptDrops=acceptDrops, setLayout=setLayout, **kwds)

        self.setContentsMargins(0, 0, 0, 0)


class WidgetCorner(Widget):
    """
    Class to handle a simple widget item with a constant painted background
    Item is to be resized by parent handler
    """

    def __init__(self, parent, spectrumDisplay=None, mainWindow=None, setLayout=False, acceptDrops=False,
                 background=None, **kwds):
        """Initialise the widget
        """
        super().__init__(parent=parent, setLayout=setLayout, acceptDrops=acceptDrops, **kwds)
        self._parent = parent
        self.spectrumDisplay = spectrumDisplay
        self.mainWindow = mainWindow
        self._background = None

        if background:
            self.setBackground(background)

    def setBackground(self, colour):
        """Set the background colour (or None)
        """
        try:
            # try a QColor first
            self._background = QtGui.QColor(colour)
        except:
            # otherwise assume to be a tuple (0..1, 0..1, 0..1, 0..1, 0..1)
            if type(colour) != tuple or len(colour) != 4 or any(not (0 <= col <= 1) for col in colour):
                raise TypeError("colour must be a tuple(r, g, b, alpha)")

            self._background = QtGui.QColor(rgbRatioToHex(*colour[:3]))

    def paintEvent(self, a0: QtGui.QPaintEvent):
        """Paint the background in the required colour
        """
        if self._background is not None:
            p = QtGui.QPainter(self)
            rgn = self.rect()
            p.fillRect(rgn, self._background)
            p.end()


class ScrollableWidget(Widget):
    """A scrollable Widget"""

    def __init__(self, parent=None, setLayout=False,
                 minimumSizes=(50, 50), scrollBarPolicies=('asNeeded', 'asNeeded'), **kwds):

        # define a scroll area; check kwds if these apply to grid
        kw1 = {}
        for key in 'grid gridSpan stretch hAlign vAlign'.split():
            if key in kwds:
                kw1[key] = kwds[key]
                del (kwds[key])
        kw1['setLayout'] = True  ## always assure a layout for the scroll-area

        self.scrollArea = ScrollArea(parent=parent,
                                     scrollBarPolicies=scrollBarPolicies, minimumSizes=minimumSizes,
                                     **kw1
                                     )
        # initialise the frame
        Widget.__init__(self, parent=self.scrollArea, setLayout=setLayout, **kwds)
        # self.setMinimumSizes(minimumSizes) ## This make things go wrong!?
        # add it to the _sequenceGraphScrollArea
        self.scrollArea.setWidget(self)
        #self._sequenceGraphScrollArea.getLayout().addWidget(self)

        # configure the scroll area to allow all available space without margins
        self.scrollArea.setContentsMargins(0, 0, 0, 0)
        self.scrollArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.scrollArea.setWidgetResizable(True)
        self.setScrollBarPolicies(scrollBarPolicies)

    def setMinimumSizes(self, minimumSizes):
        """Set (minimumWidth, minimumHeight)"""
        self.setMinimumWidth(minimumSizes[0])
        self.setMinimumHeight(minimumSizes[1])

    def getScrollArea(self):
        """return scroll area (for external usage)"""
        return self.scrollArea

    def setScrollBarPolicies(self, scrollBarPolicies=('asNeeded', 'asNeeded')):
        """Set the scrolbar policy: always, never, asNeeded"""
        self.scrollArea.setScrollBarPolicies(scrollBarPolicies)


def main():
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.widgets.BasePopup import BasePopup
    from ccpn.ui.gui.widgets.Label import Label

    class TestPopup(BasePopup):
        def body(self, parent):
            # parent doesn't have a layout
            widget = Widget(parent, grid=(0, 0), setLayout=True)
            policyDict = dict(
                    hAlign='c',
                    stretch=(1, 0),
                    setLayout=True,
                    #hPolicy = 'center',
                    #vPolicy = 'center'
                    )

            #TODO: find the cause of the empty space between the widgets
            #frame3 = ScrollableFrame(parent=parent, showBorder=True, bgColor=(255, 0, 255), grid=(2,0))
            frame1 = Widget(parent=widget, grid=(0, 0), bgColor=(255, 255, 0), **policyDict)
            Label(parent=frame1, grid=(0, 0), text="WIDGET-1", bold=True, textColour='black', textSize=32)

            frame2 = Widget(parent=widget, grid=(1, 0), bgColor=(255, 0, 0), **policyDict)
            Label(parent=frame2, grid=(0, 0), text="WIDGET-2", bold=True, textColour='black', textSize=32)

            scroll4 = ScrollableWidget(parent=widget, grid=(2, 0), **policyDict)
            Label(parent=scroll4, text="ScrollableWidget", grid=(1, 0),
                  bold=True, textColour='black', textSize=32)


    app = TestApplication()
    popup = TestPopup(title='Test Frame')
    popup.resize(200, 400)
    app.start()


if __name__ == '__main__':
    main()
