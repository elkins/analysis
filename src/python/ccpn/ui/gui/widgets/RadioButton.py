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
__dateModified__ = "$dateModified: 2024-09-06 11:32:59 +0100 (Fri, September 06, 2024) $"
__version__ = "$Revision: 3.2.6 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtWidgets, QtCore
from ccpn.ui.gui.widgets.Base import Base
from ccpn.framework.Translation import translator
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame

class RadioButton(QtWidgets.QRadioButton, Base):

    highlightColour = None

    def __init__(self, parent, text='', textColor=None, textSize=None, squared=False, callback=None, **kwds):

        super().__init__(parent)
        Base._init(self, **kwds)

        text = translator.translate(text)
        self.setText(text)

        # if textColor:
        #     self.setStyleSheet('QRadioButton {color: {}; font-size: 12pt;}'.format(textColor))
        # if textSize:
        #     self.setStyleSheet('QRadioButton {font-size: {};}'.format(textSize))
        if callback:
            self.setCallback(callback)
        if not self.objectName():
            self.setObjectName(text)

        # self.setStyleSheet('QRadioButton::disabled { color: #7f88ac; }')
        if False: #squared:
            self.setStyleSheet('''
                    QRadioButton::indicator {{
                        border: {border}px solid black; 
                        height: {size}px;
                        width: {size}px;
                        border-radius: {radius}px;
                    }}
                    QRadioButton::indicator:checked {{
                        color: black;
                        background: black;
                        border-width: {border}px;
                        border-style: solid;
                        border-radius: {radius}px;
                        border-color: white;
                    }}
                    QRadioButton::disabled {{
                        color: #7f88ac
                    }}
                '''.format(size=10, border=1, radius=0.1))

    def get(self):
        return self.text()

    def set(self, text=''):
        if len(text) > 0:
            text = translator.translate(text)
        self.setText(text)

    def getText(self):
        "Get the text of the button"
        return self.get()

    def setCallback(self, callback):
        if callback:
            self.clicked.connect(callback)

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.isChecked()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.setChecked(value)


class EditableRadioButton(Widget):
    def __init__(self, parent, text=None, backgroundText=None, callback=None, tipText=None,
                 editable=True, callbackOneditingFinished=True, **kwds):

        """editingFinishedCallback = True. it will re-fired the radioButton callback
        """
        super().__init__(parent, setLayout=True, )
        # Base._init(self, setLayout=True, **kwds)
        # self.setEnabled(False)
        self.radioButton = RadioButton(self, callback=callback, tipText=tipText, grid=(0, 0))
        self.lineEdit = LineEdit(self, text=text, backgroundText=backgroundText, grid=(0, 1))  #  hAlign='l',)
        self.lineEdit.hide()
        self.editable = editable
        if editable:
            self.lineEdit.show()
        else:
            self.radioButton.setText(text)
        # self.lineEdit.setContentsMargins(0,0,0,0)
        # self.lineEdit.setMinimumWidth(250)
        # self.setMinimumHeight(30)
        self.callbackOneditingFinished = callbackOneditingFinished
        self.callback = callback
        # self.radioButton.setText = self._setText
        if self.callbackOneditingFinished:
            self.lineEdit.editingFinished.connect(self._editingFinishedCallback)

        # self.__class__ = QtWidgets.QAbstractButton

    def text(self):
        if self.editable:
            return self.lineEdit.text()
        else:
            return self.radioButton.text()

    def get(self):
        return self.text()

    def set(self, value):
        self.setText(value)

    def setText(self, value):
        if self.editable:
            self.lineEdit.setText(value)
        else:
            self.radioButton.setText(value)

    def isChecked(self):
        return self.radioButton.isChecked()

    def setChecked(self, value):
        return self.radioButton.setChecked(value)

    def _editingFinishedCallback(self):
        self.radioButton.setChecked(True)
        if self.callback:
            self.callback()


def _fillMissingValuesInSecondList(aa, bb, value):
    if not value:
        value = ''
    if bb is None:
        bb = [value] * len(aa)
    if len(aa) != len(bb):
        if len(aa) > len(bb):
            m = len(aa) - len(bb)
            bb += [value] * m
        else:
            raise NameError('Lists are not of same length.')
    return aa, bb


CheckBoxTexts = 'CheckBoxTexts'
CheckBoxTipTexts = 'CheckBoxTipTexts'
CheckBoxCheckedText = 'CheckBoxCheckedText'
CheckBoxCallbacks = 'CheckBoxCallbacks'

class RadioButtonWithSubSelection(QtWidgets.QWidget, Base):

    def __init__(self, parent, text=None, callback=None, checked=False, tipText=None, checkBoxDictionary=None,
                 autoHideCheckBoxes=True,
                  **kwds):

        """A radioButton with a list of sub CheckBoxes
        autoHideCheckBoxes: True to hide subcheckboxes if radioButton is not selected.
        """
        super().__init__(parent)
        Base._init(self, setLayout=True, **kwds)

        self.radioButton = RadioButton(self, text=text, callback=callback, tipText=tipText, grid=(0, 0))
        self.radioButton.setChecked(checked)
        self.checkBoxDictionary = checkBoxDictionary
        self.checkBoxes = []
        self.checkBoxesFrame = Frame(self, setLayout=True, grid=(1,1), )
        if self.checkBoxDictionary:
            checkBoxTexts = self.checkBoxDictionary.get(CheckBoxTexts, [])
            _checkBoxTipTexts = self.checkBoxDictionary.get(CheckBoxTipTexts, [])
            _checkBoxCallbacks = self.checkBoxDictionary.get(CheckBoxCallbacks, [])
            # just make sure all lists are of same length
            _, checkBoxTipTexts = _fillMissingValuesInSecondList(checkBoxTexts, _checkBoxTipTexts, value='')
            _, checkBoxCallbacks = _fillMissingValuesInSecondList(checkBoxTexts, _checkBoxCallbacks, value=None)
            checkBoxCheckedText = self.checkBoxDictionary.get(CheckBoxCheckedText, [])


            for i, checkBoxText in enumerate(checkBoxTexts):
                _callback = checkBoxCallbacks[i]
                _tipText = checkBoxTipTexts[i]
                _checked = checkBoxText in checkBoxCheckedText
                checkBox = CheckBox(self.checkBoxesFrame, text=checkBoxText, checked= _checked,
                                         callback=_callback, tipText=_tipText, grid=(i+1, 1), hAlign='l')
                self.checkBoxes.append(checkBox)

        # self._defaultCallback()
        # self.radioButton.clicked.connect(self._defaultCallback)

    def _defaultCallback(self):
        # hide checkboxes frame if not selected
        checked = self.isChecked()
        self.checkBoxesFrame.setVisible(checked)

    def get(self):
        return self.radioButton.text()

    def set(self, value):
        self.radioButton.setText(value)

    def getText(self):
        return self.get()

    def setText(self, value):
       self.radioButton.setText(value)

    def isChecked(self):
        return self.radioButton.isChecked()

    def setChecked(self, value):
        return self.radioButton.setChecked(value)

    def getSelectedCheckBoxesIndexes(self):
        return [ii for ii, checkBox in enumerate(self.checkBoxes) if checkBox.isChecked()]

    def getSelectedCheckBoxes(self):
        return [checkBox.text() for checkBox in self.checkBoxes if checkBox.isChecked()]

    def setSelectedCheckBoxes(self, texts):
        for checkBox in self.checkBoxes:
            if checkBox.text() in texts:
                checkBox.setChecked(True)
            else:
                checkBox.setChecked(False)



if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog


    app = TestApplication()


    def callback():
        print('callback ~~~~')



    popup = CcpnDialog(setLayout=True)
    checkBoxesDict = {
                    CheckBoxTexts: ['A','B','C'],
                    CheckBoxTipTexts: ['A','B','C'],
                    CheckBoxCheckedText:['B'],
                    CheckBoxCallbacks: [None, None, None]
                    }
    rb = RadioButtonWithSubSelection(parent=popup, text="test", checkBoxDictionary=None,
                                     callback=callback, grid=(0, 0))
    print(rb.getSelectedCheckBoxes())
    rb.setSelectedCheckBoxes(['A', 'C'])
    popup.show()
    popup.raise_()
    app.start()
