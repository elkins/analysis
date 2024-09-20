"""Module Documentation here

"""
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
__dateModified__ = "$dateModified: 2024-04-23 22:03:04 +0100 (Tue, April 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from contextlib import contextmanager
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
from ccpn.ui.gui.widgets.Base import Base


class Spinbox(QtWidgets.QSpinBox, Base):

    returnPressed = pyqtSignal(int)
    wheelChanged = pyqtSignal(int)
    highlightColour = None

    def __init__(self, parent, prefix=None, value=None, step=None, min=None, max=None,
                 showButtons=True, callback=None, editable=True, **kwds):

        super().__init__(parent)
        Base._init(self, **kwds)

        if min is not None:
            self.setMinimum(min)
        if max is not None:
            self.setMaximum(max)
        if value is not None:  #set Value only after you set min and max
            self.setValue(value)
        if step is not None:
            self.setSingleStep(step)
        if prefix:
            self.setPrefix(prefix + ' ')
        if showButtons is False:
            self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)

        self._callback = None
        self.setCallback(callback)

        lineEdit = self.lineEdit()
        lineEdit.returnPressed.connect(self._keyPressed)

        self._internalWheelEvent = True
        self._keyPressed = False

        # change focusPolicy so that spinboxes don't grab focus unless selected
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._setStyle()

    def _setStyle(self):
        _style = """QSpinBox {
                        padding: 3px 3px 3px 3px;
                        background-color: palette(base);
                    }
                    QSpinBox:disabled { background-color: palette(midlight); }
                    """
        self.setStyleSheet(_style)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """Process the wheelEvent for the spinBox
        """
        # emit the value when wheel event has occurred, only when hasFocus
        if self.hasFocus():
            super().wheelEvent(event)
            self.wheelChanged.emit(self.value())
        else:
            event.ignore()

    @contextmanager
    def _useExternalWheelEvent(self):
        try:
            self._internalWheelEvent = False
            yield
        finally:
            self._internalWheelEvent = True

    def _externalWheelEvent(self, event):
        with self._useExternalWheelEvent():
            self.wheelEvent(event)

    def stepBy(self, steps: int) -> None:
        if self._internalWheelEvent:
            super().stepBy(steps)
        else:
            super().stepBy(1 if steps > 0 else -1 if steps < 0 else steps)

    def get(self):
        return self.value()

    def set(self, p_int):
        self.setValue(p_int)

    def _keyPressed(self, *args):
        """emit the value when return has been pressed
        """
        self.returnPressed.emit(self.value())

    def setCallback(self, callback):
        """Sets callback; disconnects if callback=None
        """
        if self._callback is not None:
            self.valueChanged.disconnect()
        if callback:
            self.valueChanged.connect(callback)
        self._callback = callback

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.get()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.set(value)



if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog


    app = TestApplication()
    popup = CcpnDialog()
    sb = Spinbox(popup, step=10, grid=(0, 0))
    sb.setPrefix('H Weight ')

    popup.show()
    popup.raise_()

    app.start()
