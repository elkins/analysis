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
__dateModified__ = "$dateModified: 2024-08-23 19:21:19 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QRegularExpression
from PyQt5.QtWidgets import QStyle, QPushButton
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Font import setWidgetFont, getFontHeight

# Width?
# Allow setting of max length based on data model?

import re


SPLIT_REG_EXP = re.compile(',?\s*')
SEPARATOR = ', '
MAXINT = 2**31 - 1
INFINITY = float('Inf')


class Entry(QtWidgets.QLineEdit, Base):

    def __init__(self, parent, text='', callback=None, maxLength=1000,
                 listener=None, stripEndWhitespace=True, editable=True,
                 backgroundText='<default>', allowFeedback=False,
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
        self.feedbackAction = self.addAction(icon, self.TrailingPosition)
        self.textEdited.connect(self.validate)

        self.allowFeedback = allowFeedback
        self.validator = validator
        self.feedback = None

        self._setStyle()

    def _setStyle(self):
        _style = """QLineEdit {
                        padding: 3px;
                        border-color: palette(mid);
                        border-style: solid;
                        border-width: 1px;
                        border-radius: 2px;
                    }
                    QLineEdit:focus {
                        border-color: palette(highlight);
                    }
                    QLineEdit:disabled {
                        color: palette(dark);
                        background-color: palette(midlight);
                    }
                    """
        self.setStyleSheet(_style)

    def setValidator(self, a0):
        """Overrides the traditional Validator to allow
        the user to write what they want, however if the input is not
        allowed and feedback is enabled then a feedback icon will appear.

        .. NOTE:: allowFeedback must be true for this to work.
        """
        if self.allowFeedback:
            self.validator = a0
            self.validate()
        else:
            super().setValidator(a0)

    def validate(self):
        """If there is a validator set add corresponding feedback for the box"""
        # removes the feedback if box is empty
        # or there is no validator set
        if not self.text() or not self.validator:
            self.feedback = False
            return

        validity = self.validator.validate(self.text(), 0)[0]
        if validity != 2:
            self.feedback = True
        else:
            self.feedback = False

    @property
    def feedback(self) -> bool:
        return self._feedback

    @feedback.setter
    def feedback(self, value: bool | None):
        """Sets current feedback response."""
        if not self.allowFeedback or value is None:
            self.feedbackAction.setVisible(False)
            return

        self.feedbackAction.setVisible(value)
        self._feedback = value

    @property
    def allowFeedback(self) -> bool:
        return self._allowFeedback

    @allowFeedback.setter
    def allowFeedback(self, value: bool | None):
        self._allowFeedback = value

        if value is None or value is False:
            self.feedback = False
            self.feedbackAction.setVisible(False)

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

    def _split(self, text: str):
        return [x.strip() for x in text.split(',')]


class IntEntry(Entry):

    def __init__(self, parent, text=0, callback=None,
                 minValue=-MAXINT, maxValue=MAXINT, **kwds):

        Entry.__init__(self, parent, text, callback, **kwds)
        valid = QtGui.QIntValidator(minValue, maxValue, self)
        self.setValidator(valid)
        self.allowFeedback = True

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
        self.allowFeedback = True
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

        self.setValidator(QtGui.QRegExpValidator)


class ArrayEntry(Entry):

    def __init__(self, parent, text='', callback=None, **kwds):
        Entry.__init__(self, parent, text, callback, **kwds)
        self.allowFeedback = False

    def convertText(self, text):
        # return re.split(SPLIT_REG_EXP, text) or []
        return self._split(text) or []

    def convertInput(self, array):
        return SEPARATOR.join(array)


class IntArrayEntry(IntEntry):

    def __init__(self, parent, text='', callback=None, **kwds):
        IntEntry.__init__(self, parent, text, callback, **kwds)
        self.allowFeedback = False

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
        self.allowFeedback = False

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

    entry = Entry(frame, 'Fail Text', callback, backgroundText='Only Lowercase', grid=(1, 0), allowFeedback=True)

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
