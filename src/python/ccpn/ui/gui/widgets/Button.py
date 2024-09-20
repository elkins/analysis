"""
This module implements the Button class
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
__dateModified__ = "$dateModified: 2024-08-23 19:21:18 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtWidgets, QtGui

from ccpn.framework.Translation import translator
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Font import getFontHeight
from ccpn.ui.gui.guiSettings import getColours


CHECKED = QtCore.Qt.Checked
UNCHECKED = QtCore.Qt.Unchecked


class Button(QtWidgets.QPushButton, Base):

    def __init__(self, parent=None, text='', callback=None, icon=None, toggle=None, enabled=True,
                 enableFocusBorder=True, **kwds):

        #text = translator.translate(text): not needed as it calls setText which does the work

        super().__init__(parent)
        Base._init(self, **kwds)

        self.setText(text)
        self._enableFocusBorder = enableFocusBorder

        # polish/unpolish required if these fields change outside __init__
        self.setProperty('iconField', bool(icon))
        self.setProperty('focusBorderField', bool(enableFocusBorder))
        self.setProperty('toggleField', bool(toggle))
        if icon:  # filename or pixmap
            self.setIcon(Icon(icon))
            # this causes the button to reset its stylesheet
            fontHeight = (getFontHeight() or 12) + 4
            self.setIconSize(QtCore.QSize(fontHeight, fontHeight))

        self.toggle = toggle
        if toggle is not None:
            self.setCheckable(True)
            self.setSelected(toggle)

        self._callback = None
        self.setCallback(callback)

        # set the initial enabled state of the button
        self.setEnabled(enabled)
        self._setStyle()

    def _setStyle(self):
        self._checkPalette(self.palette())
        self.style().unpolish(self)
        self.style().polish(self)

    def _checkPalette(self, *args):
        _style = """QPushButton[iconField=true] { padding: 1px 3px 1px 3px; }
                    QPushButton { padding: 3px; }
                    QPushButton:focus[focusBorderField=true] {
                        padding: 0px;
                        border-color: palette(highlight);
                        border-style: solid;
                        border-width: 1px;
                        border-radius: 2px;
                    }
                    QPushButton:focus {
                        padding: 0px;
                    }
                    QPushButton:disabled {
                        color: palette(dark);
                        background-color: palette(midlight);
                    }
                    QPushButton:checked[toggleField=true] { background-color: palette(highlight) }
                """
        self.setStyleSheet(_style)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        if event.key() in [QtCore.Qt.Key_Space]:
            # simulate an exit-key to clear keySequences
            escape = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Exit, QtCore.Qt.NoModifier)
            QtCore.QCoreApplication.sendEvent(self, escape)
            # perform button action
            self.click()

        return super().keyReleaseEvent(event)

    def setSelected(self, selected):
        if self.isCheckable():
            self.setChecked(selected)

    def setCallback(self, callback=None):
        """Sets callback; disconnects if callback=None"""
        if self._callback is not None:
            self.clicked.disconnect()
        if callback:
            self.clicked.connect(callback)
            # self.clicked.connect doesn't work with lambda, yet...
        self._callback = callback

    def setText(self, text):
        """Set the text of the button, applying the translator first"""
        self._text = translator.translate(text)
        QtWidgets.QPushButton.setText(self, self._text)

    def getText(self):
        """Get the text of the button"""
        return self._text

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        if self.toggle:
            return self.isChecked()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        if not value:
            return

        if self.toggle:
            return self.set(value)


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication


    app = TestApplication()

    window = QtWidgets.QWidget()
    window.setLayout(QtWidgets.QGridLayout())


    def click():
        print("Clicked")


    b1 = Button(window, text='Click Me', callback=click,
                tipText='Click for action',
                grid=(0, 0))

    b2 = Button(window, text='I am inactive', callback=click,
                tipText='Cannot click',
                grid=(0, 1))

    b2.setEnabled(False)

    b3 = Button(window, text='I am green', callback=click,
                tipText='Mmm, green',  #bgColor='#80FF80',
                grid=(0, 2))

    b4 = Button(window, icon='icons/system-help.png', callback=click,
                tipText='A toggled icon button', toggle=True,
                grid=(0, 3))

    window.show()
    window.raise_()

    app.start()
