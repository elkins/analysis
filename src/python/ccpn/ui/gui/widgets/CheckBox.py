"""
CheckBox widget

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
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.Widget import Widget


class CheckBox(QtWidgets.QCheckBox, Base):

    highlightColour = None

    def __init__(self, parent=None, checked=False, text='', callback=None, checkable=True, **kwds):

        super().__init__(parent)
        Base._init(self, **kwds)
        self._object = None

        self.setChecked(checked)
        if text:
            self.setText(str(text))
        if callback:
            self.setCallback(callback)
        if not self.objectName():
            self.setObjectName(str(text))

        self.setEnabled(checkable)

    def get(self):
        return self.isChecked()

    def set(self, checked):
        self.setChecked(checked)

    def setCallback(self, callback):
        self.clicked.connect(callback)

    def getText(self):
        """Get the text of the button"""
        return self.text()

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.get()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.setChecked(value)

    def getObject(self):
        """Get/Set an attached object
        """
        return self._object

    def setObject(self, value):
        self._object = value


class EditableCheckBox(Widget):
    def __init__(self, parent, text=None, checked=False, callback=None, **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        self.checkBox = CheckBox(self, checked=checked, grid=(0, 0), hAlign='c', )
        self.lineEdit = LineEdit(self, text=text, grid=(0, 1), hAlign='c', )
        if callback:
            self.checkBox.setCallback(callback)

    def text(self):
        return self.lineEdit.text()

    def setText(self, value):
        self.lineEdit.setText(value)

    def isChecked(self):
        return self.checkBox.isChecked()

    def setChecked(self, value):
        return self.checkBox.setChecked(value)


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog


    app = TestApplication()


    def callback():
        print('callback')


    popup = CcpnDialog(setLayout=True)

    checkBox1 = EditableCheckBox(parent=popup, text="test", callback=callback, grid=(0, 0)
                                 )
    popup.show()
    popup.raise_()
    app.start()
