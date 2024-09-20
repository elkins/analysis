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
__dateModified__ = "$dateModified: 2024-04-23 22:03:03 +0100 (Tue, April 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
import re
import typing
from functools import partial
from contextlib import contextmanager, suppress
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
from ccpn.ui.gui.widgets.Base import Base
from math import floor, log10, isclose


SPINBOXSTEP = 10
KEYVALIDATELIST = (QtCore.Qt.Key_Return,
                   QtCore.Qt.Key_Enter,
                   QtCore.Qt.Key_Tab,
                   QtCore.Qt.Key_Up,
                   QtCore.Qt.Key_Down,
                   QtCore.Qt.Key_Left,
                   QtCore.Qt.Key_Right,
                   QtCore.Qt.Key_0,
                   QtCore.Qt.Key_1,
                   QtCore.Qt.Key_2,
                   QtCore.Qt.Key_3,
                   QtCore.Qt.Key_4,
                   QtCore.Qt.Key_5,
                   QtCore.Qt.Key_6,
                   QtCore.Qt.Key_7,
                   QtCore.Qt.Key_8,
                   QtCore.Qt.Key_9,
                   # QtCore.Qt.Key_Minus,
                   # QtCore.Qt.Key_Plus,
                   # QtCore.Qt.Key_E,
                   # QtCore.Qt.Key_Period,
                   )
KEYVALIDATEDECIMAL = (QtCore.Qt.Key_0,)  # need to discard if after decimal
KEYVALIDATEDIGIT = (QtCore.Qt.Key_0,
                    QtCore.Qt.Key_1,
                    QtCore.Qt.Key_2,
                    QtCore.Qt.Key_3,
                    QtCore.Qt.Key_4,
                    QtCore.Qt.Key_5,
                    QtCore.Qt.Key_6,
                    QtCore.Qt.Key_7,
                    QtCore.Qt.Key_8,
                    QtCore.Qt.Key_9,
                    )

KEYVALIDATECURSOR = (QtCore.Qt.Key_Up,
                     QtCore.Qt.Key_Down,
                     QtCore.Qt.Key_Return,
                     QtCore.Qt.Key_Enter,
                     QtCore.Qt.Key_Tab,
                     )


#=========================================================================================
# Double spinbox
#=========================================================================================

class DoubleSpinbox(QtWidgets.QDoubleSpinBox, Base):
    returnPressed = pyqtSignal(float)
    wheelChanged = pyqtSignal(float)
    minimizeSignal = pyqtSignal()

    _showValidation = True
    _validationValid = QtGui.QColor('lightseagreen')
    _validationIntermediate = QtGui.QColor('lightpink')
    _validationInvalid = QtGui.QColor('lightcoral')
    highlightColour = None

    DEFAULTDECIMALS = 6

    def __init__(self, parent, value=None, min=None, max=None, step=None, prefix=None, suffix=None,
                 showButtons=True, decimals=None, callback=None, editable=True, locale=None, **kwds):
        """
        From the QTdocumentation
        Constructs a spin box with a step value of 1.0 and a precision of 2 decimal places.
        Change the default 0.0 minimum value to -sys.float_info.max
        Change the default 99.99  maximum value to sys.float_info.max
        The value is default set to 0.00.

        The spin box has the given parent.
        """
        self._keyPressed = None
        self.validator = QtGui.QDoubleValidator()

        super().__init__(parent)
        Base._init(self, **kwds)

        lineEdit = self.lineEdit()
        lineEdit.returnPressed.connect(self._returnPressed)
        lineEdit.setValidator(self.validator)
        self.baseColour = lineEdit.palette().color(QtGui.QPalette.Base)

        self._qLocale = locale or QtCore.QLocale()
        self.setLocale(self._qLocale)

        if min is not None:
            self.setMinimum(min)
        else:
            self.setMinimum(-1.0 * sys.float_info.max)
        if max is not None:
            self.setMaximum(max)
        else:
            self.setMaximum(sys.float_info.max)

        self.isSelected = False
        self._internalWheelEvent = True

        if step is not None:
            self.setSingleStep(step)
        if decimals is not None:
            self.setDecimals(decimals)
        else:
            self.setDecimals(self.DEFAULTDECIMALS)

        if showButtons is False:
            self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        if prefix:
            self.setPrefix(f'{prefix} ')
        if suffix:
            self.setSuffix(f' {suffix}')

        if value is not None:
            value = value
            self.setValue(value)

        # must be set after setting value/limits
        self._callback = None
        self.setCallback(callback)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        # change focusPolicy so that spin-boxes don't grab focus unless selected
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._setStyle()

    def _setStyle(self):
        _style = """QDoubleSpinBox {
                    padding: 3px 3px 3px 3px;
                    background-color: palette(base);
                }
                QDoubleSpinBox:disabled { background-color: palette(midlight); }
                """
        self.setStyleSheet(_style)

    def contextMenuEvent(self, event):
        # add an event to add extra items to the menu
        # I think this came from
        #   https://github.com/eyllanesc/stackoverflow/tree/master/questions/53496605
        QtCore.QTimer.singleShot(0, self._addActions)
        super().contextMenuEvent(event)

    def _addActions(self):
        # find the correct menu-widget
        if widg := next((widg for widg in QtWidgets.QApplication.topLevelWidgets()
                         if isinstance(widg, QtWidgets.QMenu) and widg.objectName() == "qt_edit_menu"), None):
            ...
            # # add menu items
            # widg.addSeparator()
            # widg.addAction(..., method)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        """Process the wheelEvent for the doubleSpinBox
        """
        # emit the value when wheel event has occurred, only when hasFocus
        if self.hasFocus() or not self._internalWheelEvent:
            super().wheelEvent(event)
            value = self.value()
            self.wheelChanged.emit(value)
        else:
            event.ignore()

    @contextmanager
    def _useExternalWheelEvent(self):
        # temporarily disable the stepping of the wheel-event
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
            super().stepBy(min(steps, SPINBOXSTEP) if steps > 0 else max(steps, -SPINBOXSTEP))
        else:
            # disable multiple stepping for wheelMouse events in a spectrumDisplay
            super().stepBy(1 if steps > 0 else -1 if steps < 0 else steps)

    def _returnPressed(self, *args):
        """emit the value when return has been pressed
        """
        self.returnPressed.emit(self.value())

    def get(self):
        return self.value()

    def set(self, value):
        self.setValue(value)

    def setSelected(self):
        self.isSelected = True

    def focusInEvent(self, event):
        self.setSelected()

        super().focusInEvent(event)

    def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
        # Ensure that the background colour is updated on focus-out
        super().focusOutEvent(event)

        self.validate(self.text(), 0)

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        super().keyPressEvent(e)

        if e.key() in KEYVALIDATECURSOR:
            # ensure that the background colour is updated correctly
            self.validate(self.text(), 0)

    def setCallback(self, callback):
        """Sets callback; disconnects if callback=None
        """
        if self._callback is not None:
            self.valueChanged.disconnect()
        if callback:
            self.valueChanged.connect(callback)
        self._callback = callback

    def textFromValue(self, v: typing.Union[float, int]) -> str:
        """Subclass to remove extra zeroes
        """
        if isinstance(v, int):
            return super(DoubleSpinbox, self).textFromValue(v)

        string = self._qLocale.toString(round(v, self.decimals()), 'g', QtCore.QLocale.FloatingPointShortest).replace("e+", "e")
        string = re.sub("e(-?)0*(\d+)", r"e\1\2", string)
        return string

    def validate(self, text: str, pos: int) -> typing.Tuple[QtGui.QValidator.State, str, int]:
        """Validate the spinbox contents
        """
        _state = super().validate(text, pos)

        if self._showValidation:
            # change the colour depending on the state
            self._checkState(_state)

        return _state

    def _checkState(self, _state):
        """Update the colour of the background to reflect the validate-state of the spinbox
        """
        state, text, position = _state
        for obj in (self, self.lineEdit()):
            # paint both the line edit and the padding
            palette = obj.palette()
            try:
                # set the validate-colours for the object
                if state == QtGui.QValidator.Acceptable:
                    palette.setColor(QtGui.QPalette.Active, QtGui.QPalette.Base, self.baseColour)
                elif state == QtGui.QValidator.Intermediate:
                    palette.setColor(QtGui.QPalette.Active, QtGui.QPalette.Base, self._validationIntermediate)

                else:  # Invalid
                    palette.setColor(QtGui.QPalette.Active, QtGui.QPalette.Base, self._validationInvalid)

            finally:
                obj.setPalette(palette)
                obj.update()

    def setMinimumCharacters(self, value):
        from ccpn.ui.gui.widgets.Font import getTextDimensionsFromFont

        _, maxDim = getTextDimensionsFromFont(textList=['_' * value])
        self.setMinimumWidth(maxDim.width())

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

    def _flashColour(self, colour):
        with suppress(Exception):
            # set the background colour for the line-edit and the padding
            for obj in (self, self.lineEdit()):
                # set the colours for the object
                palette = obj.palette()
                palette.setColor(QtGui.QPalette.Active, QtGui.QPalette.Base, colour)
                obj.setPalette(palette)

                obj.update()

    def _flashError(self, timer=300):
        # set the warning colour and then set back to background colour
        self._flashColour(self._validationInvalid)
        QtCore.QTimer.singleShot(timer, partial(self._flashColour, self.baseColour))


# Regular expression to find floats. Match groups are the whole string, the
# whole coefficient, the decimal part of the coefficient, and the exponent
# part. (decimal point, not decimal comma)
_float_re = re.compile(r'(([+-]?\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)')


def fexp(f):
    return int(floor(log10(abs(f)))) if f != 0 else 0


#=========================================================================================
# Scientific spinbox
#=========================================================================================

class ScientificDoubleSpinBox(DoubleSpinbox):
    """Constructs a spinbox in which the values can be set using Scientific-notation,
    and increments based on the power of the number.
    Single-step is 0.1 * contents.
    """

    def __init__(self, *args, **kwargs):
        super(ScientificDoubleSpinBox, self).__init__(*args, **kwargs)

        # set step-type to power-1
        self.setStepType(self.AdaptiveDecimalStepType)


#=========================================================================================
# Scientific spinbox - variable power-step
#=========================================================================================

class VariableScientificSpinBox(DoubleSpinbox):
    """Constructs a spinbox in which the values can be set using Scientific-notation

    Spinbox increments in AdaptiveDecimalStepType based on the required step-size order.
    Increment will be 1e-<step> * contents.
    Default is step = -1

    A minimum-order can be specified below which the spinbox will go to zero, and then change sign.
    This can be set higher than the number of decimal places.

    The number will always change to scientific-notation outside +-1e6
    """
    _FORMATDECIMALS = 6

    def __init__(self, parent, minOrder=-4, *args, **kwargs):
        """Initialise the spinbox.

        :param parent:
        :param int minOrder: mininum order before rolling over to zero
        :param args: args to pass to superclass
        :param kwds: keywords to pass to superclass
        """
        self._minOrder = int(minOrder)
        self._exp = 10**minOrder

        # step if defined by 'step' relative to current power
        _decs = kwargs.pop('step', -1)
        if not isinstance(_decs, int) and _decs >= 0:
            raise ValueError('step must be a power < 0')
        self._decimalStep = 10**_decs

        super().__init__(parent, *args, **kwargs)

        self.setSingleStep(self._exp)
        self.setStepType(self.DefaultStepType)
        self.setDecimals(31)
        self._minDecimals = self.decimals()

        self._maxOrder = fexp(max(abs(self.maximum()), abs(self.minimum())))

        # spinbox to handle validate with variable precision
        self._textValidator = QtGui.QDoubleValidator(self.minimum(),
                                                     self.maximum(),
                                                     self.decimals()
                                                     )
        self.validate(self.text(), 0)

    def stepBy(self, steps):
        """Increment the current value.
        Step if 1/10th of the current rounded value * step
        Now defined by 'step' in kwargs, i.e., step=0.1, 0.01
        """
        # clip number of steps to SPINBOXSTEP as 10* will go directly to zero from 1 when Ctrl/Cmd pressed
        steps = min(steps, SPINBOXSTEP) if steps > 0 else max(steps, -SPINBOXSTEP)

        text = self.cleanText()
        decimal, valid = self._qLocale.toFloat(text)
        if valid:
            step = fexp(decimal * self._decimalStep)
            _stepdown = fexp((decimal - self.singleStep()) * self._decimalStep)
            _stepup = fexp((decimal + self.singleStep()) * self._decimalStep)
            if steps < 0 and _stepdown < step:
                # down key - decrease positive
                step = _stepdown
            elif steps > 0 and _stepup < step:
                # up key - increase negative
                step = _stepup

            if not isclose(decimal, 0.0, abs_tol=self._exp * 0.01):
                self.setSingleStep(max(10**step, self._exp))

        DoubleSpinbox.stepBy(self, steps)

        self.validate(self.text(), 0)

    def textFromValue(self, value):
        # fix the zero-state, sometimes expresses machine-tolerance
        if isclose(value, 0.0, abs_tol=1e-12):
            value = round(value, 12)

        return self.formatFloat(value)

    def formatFloat(self, value):
        """Modified form of the 'g' format specifier.
        """
        val = float(value)
        mag = fexp(abs(val))

        if mag >= self._FORMATDECIMALS:
            prec = self._FORMATDECIMALS + 3 - 1
            string = self._qLocale.toString(val, 'e', prec)

        elif mag >= 0:
            prec = self._FORMATDECIMALS + 3
            string = self._qLocale.toString(val, 'g', prec)

        else:
            prec = self._FORMATDECIMALS + 3 + mag + 1
            string = self._qLocale.toString(val, 'g', prec)

        # NOTE:ED - 'g' format handles this with correct locale
        # clean leading zeroes from the exponent
        return re.sub("e(-|\+?)0*(\d+)", r"e\1\2", string.replace("e+", "e"))

        # check for an exponent, removing leading/trailing zeroes
        # reg = r'^((?:\+?)|(\-?))(?:0*)(\d+)((((\.\d*[1-9])(?:0*)|(?:\.0+)|)((e)((?:\+?)|(\-?))((?:0*)([1-9]\d*)|(0)(?:0*))(?:$)|(?:$))|(?:$)))'
        # _string = re.sub(reg, r'\2\3\7\9\11\13\14', string)

    def validate(self, text, position):
        decimal = self.value()
        mag = fexp(decimal)

        if mag >= self._FORMATDECIMALS:
            self._textValidator.setDecimals(self._FORMATDECIMALS + 3 - 1)
        elif mag >= 0:
            self._textValidator.setDecimals(self._FORMATDECIMALS + 3 - mag - 1)
        else:
            self._textValidator.setDecimals(self._FORMATDECIMALS + 3)

        # use the hidden validator that the decimals can be changed without spurious events
        # and allows different decimals between 'e' and 'g' formatting
        _state = self._textValidator.validate(text, position)
        if self._showValidation:
            self._checkState(_state)

        return _state


v = float("{0:.3f}".format(0.024))
v1 = 24678.45


def main():
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog
    from ccpn.ui.gui.widgets.Frame import Frame

    app = TestApplication()

    popup = CcpnDialog()
    # test setting the dialog to French (different float format)
    # QtCore.QLocale.setDefault(QtCore.QLocale(QtCore.QLocale.French))

    fr = Frame(popup, setLayout=True)

    DoubleSpinbox(fr, value=v1, decimals=3, step=0.01, grid=(0, 0))
    ScientificDoubleSpinBox(fr, value=v1, grid=(1, 0), min=-1e8, max=1e10)
    VariableScientificSpinBox(fr, value=v1, grid=(3, 0), min=-1e11, max=1e11, minOrder=-4, step=-1)

    popup.show()
    popup.raise_()

    app.start()


if __name__ == '__main__':
    main()
