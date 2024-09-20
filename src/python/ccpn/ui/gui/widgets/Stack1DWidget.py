"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2024-04-04 15:19:25 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-07-25 11:28:58 +0100 (Tue, July 25, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================


from PyQt5 import QtWidgets
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.DoubleSpinbox import ScientificDoubleSpinBox, DoubleSpinbox
from ccpn.ui.gui.widgets.Spacer import Spacer


OffsetLabel = '{} Offset: '


class Offset1DWidget(Frame):
    def __init__(self, parent=None, mainWindow=None, strip1D=None, **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.project = self.mainWindow.project
            self.application = self.mainWindow.application
            self.current = self.application.current
        else:
            # allow opening the popup for testing
            self.mainWindow = self.project = self.application = self.current = None

        self.offset = None
        self.strip1D = strip1D

        self._setWidgets()

    def _setWidgets(self):
        """Set up the widget.
        """
        flip = self.strip1D.spectrumDisplay._flipped

        ii = 0
        self.boxOffsets = []
        for axis in range(2):
            ii += 1
            lbl = OffsetLabel.format(self.strip1D.axisCodes[axis])
            Label(self, lbl, grid=(0, ii))
            ii += 1
            if axis == flip:
                self.boxOffsets.append(box := DoubleSpinbox(self, step=0.001, grid=(0, ii), min=-10000, max=10000, decimals=3))
                box.setFixedWidth(100)
            else:
                self.boxOffsets.append(box := ScientificDoubleSpinBox(self, step=0.1, grid=(0, ii), min=-1e100, max=1e100))
                box.setFixedWidth(150)

        ii += 1
        Spacer(self, 2, 2,
               QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum,
               grid=(0, ii), gridSpan=(1, 1))
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Minimum)

        if self.strip1D is not None:
            for axis, bx in enumerate(self.boxOffsets):
                bx.setValue(self.strip1D.offsetValue[axis])

        for bx in self.boxOffsets:
            bx.valueChanged.connect(self._applyOffset)

    def _applyOffset(self):
        if self.strip1D is not None:
            self.strip1D._stack1DSpectra(offSet=[bx.value() for bx in self.boxOffsets])

    def value(self):
        return tuple(bx.value() for bx in self.boxOffsets)

    def setValue(self, value):
        for bx, val in zip(self.boxOffsets, value):
            bx.set(val)

    def setInitialIntensity(self, value):
        """Set the initial value from the intensity.
        """
        if self.strip1D.spectrumDisplay._flipped:
            self.setValue((value, 0.0))
        else:
            self.setValue((0.0, value))

#=========================================================================================
# main
#=========================================================================================

def main():
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog

    app = TestApplication()
    popup = CcpnDialog()
    f = Offset1DWidget(popup)

    popup.show()
    popup.raise_()

    app.start()


if __name__ == '__main__':
    main()
