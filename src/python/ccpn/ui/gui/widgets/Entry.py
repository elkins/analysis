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
__dateModified__ = "$dateModified: 2024-10-09 14:37:08 +0100 (Wed, October 09, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import contextlib
import re
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtWidgets import QStyle
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Label import Label


SPLIT_REG_EXP = re.compile(',?\s*')
SEPARATOR = ', '
MAXINT = 2**31 - 1
INFINITY = float('Inf')
VALIDATEASICON = 'validateAsIcon'


class Entry(QtWidgets.QLineEdit, Base):

    def __init__(self, parent, text='', callback=None, maxLength=1000,
                 listener=None, stripEndWhitespace=True, editable=True,
                 backgroundText='<default>', validateAsIcon=False,
                 validator=None, **kwds):

        super().__init__(parent)
        Base._init(self, **kwds)

        self.setText(self.convertInput(text))
        self.setMaxLength(maxLength)

        self._isAltered = False
        self._stripEndWhitespace = stripEndWhitespace
        self.callback = callback

        self.textChanged.connect(self._changed)
        self.returnPressed.connect(self._callback)
        self.editingFinished.connect(self._callback)

        if listener:
            if isinstance(listener, (set, list, tuple)):
                for signal in listener:
                    signal.connect(self.set)

            else:
                listener.connect(self.set)

        # self.setStyleSheet('padding: 3px 3px 3px 3px;')

        self.backgroundText = backgroundText
        if self.backgroundText:
            self.setPlaceholderText(str(self.backgroundText))

        if not editable:
            self.setReadOnly(True)
            self.setEnabled(False)

        icon = self.style().standardIcon(getattr(QStyle, 'SP_MessageBoxCritical'))
        self._validator = None
        self._validateAsIcon = None
        self._validateAction = self.addAction(icon, self.TrailingPosition)

        self.validateAsIcon = validateAsIcon
        self.setValidator(validator)
        self._showIconState(None)

        self._setStyle()

    def _setStyle(self):
        _style = """QLineEdit {
                    padding: 3px 3px 3px 3px;
                    background-color: palette(norole);
                }
                QLineEdit:disabled {
                    color: #808080;
                    background-color: palette(midlight);
                }
                QLineEdit:read-only {
                    color: #808080;
                }
                """
        self.setStyleSheet(_style)
        QtWidgets.QApplication.instance()._sigPaletteChanged.connect(self._revalidate)

    def _revalidate(self, palette):
        if val := (self.validator() or self._validator):
            if hasattr(val, 'baseColour'):
                # update the base-colour for change of theme
                val.baseColour = palette.base().color()
            # force repaint of the widget
            val.validate(self.text(), 0)

    def setValidator(self, validator: QtGui.QValidator | None):
        """Overrides the traditional Validator to allow
        the user to write what they want, however if the input is not
        allowed and feedback is enabled then a feedback icon will appear.

        .. NOTE:: validateAsIcon must be true for this to work.
        """
        if self.validateAsIcon:
            if not isinstance(validator, QtGui.QValidator | type(None)):
                raise TypeError(f'{self.__class__.__name__}.setValidator: {validator} is not a valid validator')
            if validator:
                self.validate()
            self.textEdited.connect(self.validate)
            self._validator = validator
            super().setValidator(None)
        else:
            with contextlib.suppress(TypeError, ValueError):
                self.textEdited.disconnect(self.validate)
            self._validator = None
            super().setValidator(validator)

    def validate(self):
        """If there is a validator set add corresponding feedback for the box"""
        # removes the feedback if box is empty
        # or there is no validator set
        if not self.text() or not self._validator:
            self._showIconState(False)
            return

        validity = self._validator.validate(self.text(), 0)[0]
        if validity != self._validator.Acceptable:
            self._showIconState(True)
        else:
            self._showIconState(False)

    def _showIconState(self, value: bool | None):
        """Sets current feedback response - icon visibility.
        """
        if not self.validateAsIcon or value is None:
            self._validateAction.setVisible(False)
            return

        self._validateAction.setVisible(value)
        self._feedback = value

    @property
    def validateAsIcon(self) -> bool:
        # NOTE:ED - this property name is used in validators, search VALIDATEASICON
        return self._validateAsIcon

    @validateAsIcon.setter
    def validateAsIcon(self, value: bool | None):
        if value == self._validateAsIcon:
            return
        self._validateAsIcon = value

        if value is None or value is False:
            self._showIconState(False)
            self._validateAction.setVisible(False)

        self.setValidator(self.validator() or self._validator)

    def _callback(self):

        if self.callback and self._isAltered:
            self.callback(self.get())
            self._isAltered = False

    def _changed(self):
        self._isAltered = True

    def convertText(self, text):
        # Overwritten in subclasses to make float, int etc
        if self._stripEndWhitespace:
            text = text.strip()
        return text or None

    def convertInput(self, value):
        # Overwritten in subclasses to convert float, int

        return value or ''

    def get(self):

        return self.convertText(self.text())

    #gwv 20181101; some consistency
    getText = get

    def set(self, value, doCallback=True):

        self.setText(self.convertInput(value))

        if doCallback:
            self._callback()

    @staticmethod
    def _split(text: str):
        return [x.strip() for x in text.split(',')]


class IntEntry(Entry):

    def __init__(self, parent, text=0, callback=None,
                 minValue=-MAXINT, maxValue=MAXINT, **kwds):

        Entry.__init__(self, parent, text, callback, **kwds)
        valid = QtGui.QIntValidator(minValue, maxValue, self)
        self.setValidator(valid)
        self.validateAsIcon = True

    def convertText(self, text):
        if not text:
            return None
        else:
            return int(text)

    def convertInput(self, value):

        if value is None:
            return ''
        else:
            return str(value)

    def setRange(self, minValue=-MAXINT, maxValue=MAXINT):

        valid = QtGui.QIntValidator(minValue, maxValue, self)
        self.setValidator(valid)


class FloatEntry(Entry):
    decimals = 4

    def __init__(self, parent, text=0.0, callback=None,
                 minValue=-INFINITY, maxValue=INFINITY,
                 decimals=4, **kwds):

        Entry.__init__(self, parent, text, callback, **kwds)

        self.decimals = decimals
        self.setText(self.convertInput(text))
        self.validateAsIcon = True
        valid = QtGui.QDoubleValidator(minValue, maxValue, decimals, self)
        self.setValidator(valid)

    def convertText(self, text):

        if not text:
            return None
        else:
            return float(text)

    def convertInput(self, value):

        if value is None:
            text = ''
        elif value == 0:
            text = '0.0'
        elif abs(value) > 999999 or abs(value) < 0.00001:
            textFormat = '%%.%de' % (self.decimals)
            text = textFormat % value
        else:
            textFormat = '%%.%df' % (self.decimals)
            text = textFormat % value

        return text

    def setRange(self, minValue=-MAXINT, maxValue=MAXINT):

        valid = QtGui.QIntValidator(minValue, maxValue, self)
        self.setValidator(valid)


class RegExpEntry(Entry):

    def __init__(self, parent, text='', callback=None, **kwds):
        Entry.__init__(self, parent, text, callback, **kwds)

        self.setValidator(QtGui.QRegExpValidator())


class ArrayEntry(Entry):

    def __init__(self, parent, text='', callback=None, **kwds):
        Entry.__init__(self, parent, text, callback, **kwds)
        self.validateAsIcon = False

    def convertText(self, text):
        # return re.split(SPLIT_REG_EXP, text) or []
        return self._split(text) or []

    def convertInput(self, array):
        return SEPARATOR.join(array)


class IntArrayEntry(IntEntry):

    def __init__(self, parent, text='', callback=None, **kwds):
        IntEntry.__init__(self, parent, text, callback, **kwds)
        self.validateAsIcon = False

    def convertText(self, text):
        # array = re.split(SPLIT_REG_EXP, text) or []
        array = self._split(text) or []
        return [IntEntry.convertText(self, x) for x in array]

    def convertInput(self, values):
        texts = [IntEntry.convertInput(self, x) for x in values]
        return SEPARATOR.join(texts)


class FloatArrayEntry(FloatEntry):

    def __init__(self, parent, text='', callback=None, **kwds):
        FloatEntry.__init__(self, parent, text, callback, **kwds)
        self.validateAsIcon = False

    def convertText(self, text):
        # array = re.split(SPLIT_REG_EXP, text) or []
        array = self._split(text) or []
        return [FloatEntry.convertText(self, x) for x in array]

    def convertInput(self, values):
        texts = [FloatEntry.convertInput(self, x) for x in values]
        return SEPARATOR.join(texts)


class LabelledEntry(Frame):

    def __init__(self, parent, labelText, entryText='', callback=None, maxLength=32, tipText=None, **kwds):
        Frame.__init__(self, parent, tipText=tipText, **kwds)

        self.label = Label(self, labelText, tipText=tipText, grid=(0, 0))
        self.entry = Entry(self, entryText, callback, maxLength,
                           tipText=tipText, grid=(0, 1))

    def getLabel(self):
        return self.label.get()

    def setLabel(self, text):
        self.label.set(text)

    def getEntry(self):
        return self.entry.get()

    def setEntry(self, text):
        self.entry.set(text)


class LabelledIntEntry(LabelledEntry):

    def __init__(self, parent, labelText, entryText='', callback=None,
                 minValue=-MAXINT, maxValue=MAXINT, tipText=None, **kwds):
        Frame.__init__(self, parent, tipText=tipText, **kwds)

        self.label = Label(self, labelText, tipText=tipText, grid=(0, 0))
        self.entry = IntEntry(self, entryText, callback, minValue,
                              maxValue, tipText=tipText, grid=(0, 1))


class LabelledFloatEntry(LabelledEntry):

    def __init__(self, parent, labelText, entryText='', callback=None,
                 minValue=-MAXINT, maxValue=MAXINT, decimals=4, tipText=None, **kwds):
        Frame.__init__(self, parent, tipText=tipText, **kwds)

        self.label = Label(self, labelText, tipText=tipText, grid=(0, 0))
        self.entry = FloatEntry(self, entryText, callback, minValue,
                                maxValue, decimals, tipText=tipText, grid=(0, 1))


if __name__ == '__main__':
    # from memops.qtgui.Application import Application
    from ccpn.ui.gui.widgets.Application import Application


    app = Application('test', 'test1')

    window = QtWidgets.QWidget()
    frame = Frame(window, setLayout=True)
    window.resize(250, 500)


    def callback(value):
        print("Callback", value)


    Entry(frame, 'Start Text', callback, grid=(0, 0))

    entry = Entry(frame, 'Fail Text', callback, backgroundText='Only Lowercase', grid=(1, 0), validateAsIcon=True)

    # regex test that disallows any string that is not
    # all lower case - allows underscores.
    regexp = QtCore.QRegularExpression(r'^[a-z_]+([a-z_]+)*$', QtCore.QRegularExpression.UseUnicodePropertiesOption)
    validator = QtGui.QRegularExpressionValidator(regexp)
    entry.setValidator(validator)

    ArrayEntry(frame, ['A', 'C', 'D', 'C'], callback, grid=(2, 0))

    IntEntry(frame, 123, callback, backgroundText='Int Entry', grid=(3, 0))

    IntArrayEntry(frame, [4, 5, 6, 7], callback, grid=(4, 0))

    FloatEntry(frame, 2.818, callback, grid=(5, 0))

    e = FloatArrayEntry(frame, [1, 2, 4], callback, decimals=2, grid=(6, 0))
    e.set([1e12, -0.7e-5, 9.75])

    LabelledEntry(frame, 'Text:', 'Initial val', callback, setLayout=True, grid=(7, 0))

    LabelledIntEntry(frame, 'Int:', 0, callback, setLayout=True, grid=(8, 0))

    LabelledFloatEntry(frame, 'Float:', 0.7295, callback, decimals=8, setLayout=True, grid=(9, 0))

    window.show()

    app.start()
