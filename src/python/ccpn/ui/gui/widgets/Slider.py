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
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtCore, QtWidgets
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Spinbox import Spinbox


class Slider(QtWidgets.QSlider, Base):

    highlightColour = None

    def __init__(self, parent, startVal=0, endVal=100, value=None,
                 direction='h', step=1, bigStep=None, callback=None,
                 tracking=True, showNumber=True, tickInterval=None,
                 tickPosition=None, listener=None, spinbox=False, **kwds):

        super().__init__(parent)
        Base._init(self, **kwds)

        self.callback = callback

        if value is None:
            value = startVal

        if not bigStep:
            bigStep = step

        if tickInterval:
            if not tickPosition:
                if 'h' in direction.lower():
                    tickPosition = self.TicksBelow
                else:
                    tickPosition = self.TicksRight

            self.setTickInterval(tickInterval)
            self.setTickPosition(tickPosition)

        self.showNumber = showNumber
        self.setRange(startVal, endVal)
        self.setStep(step, bigStep)
        self.set(value)
        self.fontMetric = QtGui.QFontMetricsF(self.font())

        if 'h' in direction.lower():
            self.setOrientation(QtCore.Qt.Horizontal)
        else:
            self.setOrientation(QtCore.Qt.Vertical)

        # Callback continuously (True)
        # Or only at intervals (False)
        self.setTracking(tracking)

        if showNumber and not tracking:
            # self.connect(self, QtCore.PYQT_SIGNAL('sliderMoved(int)'), self._redraw)
            self.sliderMoved.connect(self._redraw)

        if showNumber:
            # self.connect(self, QtCore.PYQT_SIGNAL('sliderReleased()'), self.update)
            self.sliderReleased.connect(self.update)

        # self.connect(self, QtCore.PYQT_SIGNAL('valueChanged(int)'), self._callback)
        self.valueChanged.connect(self._callback)

        if listener:
            if isinstance(listener, (set, list, tuple)):
                for signal in listener:
                    signal.connect(self.setValue)

            else:
                listener.connect(self.setValue)

    # def paintEvent(self, ev: QtGui.QPaintEvent) -> None:
    #     if Base._highlightVivid is not None:
    #         # change the highlight colour in response to theme change
    #         #   - bit of a hack as QT is doing something weird here
    #         thisPal = self.palette()
    #         thisPal.setColor(QtGui.QPalette.Highlight, Base._highlightVivid)
    #         self.setPalette(thisPal)
    #     super().paintEvent(ev)

    def setRange(self, startVal, endVal):

        startVal = int(startVal)
        endVal = int(endVal)

        assert startVal != endVal

        if startVal > endVal:
            self.setInvertedAppearance(True)
            startVal, endVal = endVal, startVal
        else:
            self.setInvertedAppearance(False)

        value = self.get()

        if startVal <= value <= endVal:
            callback = self.callback
            self.callback = None
            QtWidgets.QSlider.setRange(self, startVal, endVal)
            self.callback = callback

        else:
            QtWidgets.QSlider.setRange(self, startVal, endVal)

    def setStep(self, step, bigStep=None):

        self.setSingleStep(step)

        if bigStep:
            self.setPageStep(bigStep)

    def set(self, value, doCallback=True):

        if not doCallback:
            callback = self.callback
            self.callback = None
            self.setValue(int(value))
            self.callback = callback

        else:
            self.setValue(int(value))

    def get(self):

        return self.value()

    def _callback(self, callback):

        if self.callback:
            self.callback(self.value())

    def disable(self):

        self.setDisabled(True)

    def enable(self):

        self.setEnabled(True)

    def setState(self, state):

        self.setEnabled(state)

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.get()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.setValue(value)


class SliderSpinBox(QtWidgets.QWidget, Base):
    def __init__(self, parent, startVal=0, endVal=100, value=None, step=1, bigStep=5, **kwds):

        super().__init__(parent)
        Base._init(self, setLayout=True, **kwds)

        if value is None:
            value = startVal

        if not bigStep:
            bigStep = step

        slider = Slider(self, value=value, startVal=startVal, endVal=endVal, bigStep=bigStep, grid=(0, 1))
        self.spinBox = Spinbox(self, value=value, min=startVal, max=endVal, grid=(0, 0))
        slider.valueChanged.connect(self.spinBox.setValue)
        self.spinBox.valueChanged.connect(slider.setValue)

    def getValue(self):
        return self.spinBox.value()

    def set(self, value):
        self.spinBox.setValue(value)


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.widgets.BasePopup import BasePopup


    app = TestApplication()
    popup = BasePopup(title='Test slider')
    popup.resize(250, 50)
    slider = SliderSpinBox(parent=popup, startVal=0, endVal=100, value=5)
    app.start()
