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
__dateModified__ = "$dateModified: 2024-11-26 10:38:15 +0000 (Tue, November 26, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets, QtCore
from ccpn.ui.gui.widgets.Widget import Widget


class BasePopup(Widget):

    def __init__(self, parent=None, title='', location=None, hide=False,
                 modal=False, tipText=None, **kwds):

        super().__init__(parent, **kwds)

        if modal:  # Set before visible
            self.setWindowModality(QtCore.Qt.ApplicationModal)
        if tipText:
            self.setToolTip(tipText)

        parent = self.getParent()
        if parent and not location:
            x = parent.x() + 50
            y = parent.y() + 50
            rect = self.rect()
            w = rect.width()
            h = rect.height()

            location = (x, y, w, h)

        if location:
            self.show()  # TBD: is this needed?
            # self.setGeometry(*location)

        self.setWindowTitle(title)

        self.body(self)

        if hide:
            self.hide()
        else:
            self.show()
            self.raise_()

    def open(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def body(self, master):
        pass  # this method can be overridden in subclass


if __name__ == '__main__':

    from ccpn.ui.gui.widgets.Button import Button
    from ccpn.ui.gui.widgets.Label import Label
    from ccpn.ui.gui.widgets.Application import TestApplication


    app = TestApplication()


    class TestPopup(BasePopup):

        def __init__(self, parent=None):
            BasePopup.__init__(self, parent, 'Test Popup', modal=False, setLayout=True)

            self.setGeometry(600, 400, 50, 50)

            label = Label(self, text='label 1', grid=(0, 0))
            label = Label(self, text='label 2', grid=(1, 0))
            button = Button(self, text='close', callback=self.close, grid=(3, 0))


    popup = None
    window = QtWidgets.QWidget()
    layout = QtWidgets.QGridLayout()
    window.setLayout(layout)


    def new():

        global popup
        popup = TestPopup()
        popup.show()


    def lift():

        if popup:
            popup.raise_()


    def close():

        if popup:
            popup.hide()


    def open_():

        if popup:
            popup.open()


    button = Button(window, text='new popup', grid=(0, 0), callback=new)

    button = Button(window, text='lift popup', grid=(1, 0), callback=lift)

    button = Button(window, text='open popup', grid=(2, 0), callback=open_)

    button = Button(window, text='close popup', grid=(3, 0), callback=close)

    button = Button(window, text='quit', grid=(4, 0), callback=app.quit)

    window.show()
    window.raise_()

    app.start()
