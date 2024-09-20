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
__dateModified__ = "$dateModified: 2024-08-27 16:07:11 +0100 (Tue, August 27, 2024) $"
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

from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.ValidatorBase import ValidatorBase


# from ccpn.ui.gui.guiSettings import helveticaItalic12
# from ccpn.framework.Translation import translator


TextAlignment = {
    'c'     : QtCore.Qt.AlignHCenter,
    'l'     : QtCore.Qt.AlignLeft,
    'r'     : QtCore.Qt.AlignRight,
    'center': QtCore.Qt.AlignHCenter,
    'centre': QtCore.Qt.AlignHCenter,
    'left'  : QtCore.Qt.AlignLeft,
    'right' : QtCore.Qt.AlignRight
    }


class LineEdit(QtWidgets.QLineEdit, Base):
    highlightColour = None

    def __init__(self, parent, text='', textAlignment='c', backgroundText=None,
                 textColor=None, editable=True, **kwds):
        """

        :param parent:
        :param text:
        :param textAlignment:
        :param backgroundText: a transparent text that will disapear as soon as you click to type.
        :param minimumWidth:
        :param textColor:
        :param kwds:
        """
        #text = translator.translate(text)

        super().__init__(parent)
        Base._init(self, **kwds)

        self.setText(text)

        # if textColor:
        #     self.setStyleSheet('QLabel {color: %s;}' % textColor)

        self.backgroundText = backgroundText
        if self.backgroundText:
            self.setPlaceholderText(str(self.backgroundText))

        self.setAlignment(TextAlignment[textAlignment])

        # if 'minimumWidth' in kwds:
        #     self.setMinimumWidth(kwds['minimumWidth'])

        if not editable:
            self.setReadOnly(True)
            self.setEnabled(False)

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
        # check for Windows and Linux
        QtWidgets.QApplication.instance()._sigPaletteChanged.connect(self._revalidate)

    def _revalidate(self, palette):
        if val := self.validator():
            if hasattr(val, 'baseColour'):
                # update the base-colour for change of theme
                val.baseColour = palette.base().color()
            # force repaint of the widget
            val.validate(self.text(), 0)

    def get(self):
        return self.text()

    def set(self, text=''):

        #text = translator.translate(text)
        self.setText(text)

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

    # def paintEvent(self, ev):
    #     #p.setBrush(QtGui.QBrush(QtGui.QColor(100, 100, 200)))
    #     #p.setPen(QtGui.QPen(QtGui.QColor(50, 50, 100)))
    #     #p.drawRect(self.rect().adjusted(0, 0, -1, -1))
    #
    #     #p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
    #     self._text = self.text()
    #     self.setText('')
    #     super(LineEdit, self).paintEvent(ev)
    #
    #     p = QtGui.QPainter(self)
    #     if self.orientation == QtCore.Qt.Vertical:
    #         p.rotate(-90)
    #         rgn = QtCore.QRect(-self.height(), 0, self.height(), self.width())
    #     else:
    #         rgn = self.contentsRect()
    #     align = self.alignment()
    #     #align  = QtCore.Qt.AlignTop|QtCore.Qt.AlignHCenter
    #
    #     self.hint = p.drawText(rgn, align, self._text)
    #     self.setText(self._text)
    #     p.end()
    #
    #     if self.orientation == QtCore.Qt.Vertical:
    #         self.setMaximumWidth(self.hint.height())
    #         self.setMinimumWidth(0)
    #         self.setMaximumHeight(16777215)
    #     else:
    #         self.setMaximumHeight(self.hint.height())
    #         self.setMinimumHeight(0)
    #         self.setMaximumWidth(16777215)
    #
    # def sizeHint(self):
    #     if self.orientation == QtCore.Qt.Vertical:
    #         if hasattr(self, 'hint'):
    #             return QtCore.QSize(self.hint.height(), self.hint.width())
    #         else:
    #             return QtCore.QSize(19, 50)
    #     else:
    #         if hasattr(self, 'hint'):
    #             return QtCore.QSize(self.hint.width(), self.hint.height())
    #         else:
    #             return QtCore.QSize(50, 19)


class FloatLineEdit(LineEdit):

    def get(self):

        result = LineEdit.get(self)
        if result:
            return float(result)
        else:
            return None

    def set(self, text=''):

        LineEdit.set(str(text))

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


class ValidatedLineEdit(LineEdit, ValidatorBase):
    """A class that implements a validated LineEdit
    """
    WIDGET_VALUE_FUNCTION = LineEdit.get

    def __init__(self, parent, validatorCallback, **kwds):
        """
        :param parent: parent widget
        :param validatorCallback: a function def validatorCallback(value) -> bool
                                  which is called upon changes to the value of the Widget.
                                  It should return True/False.
        """
        LineEdit.__init__(self, parent=parent, **kwds)
        ValidatorBase.__init__(self, widget=self, validatorCallback=validatorCallback)


class PasswordEdit(LineEdit):
    """Subclass of LineEdit to handle passwords to be shown as **
    """

    def __init__(self, parent, text='', textAlignment='c', backgroundText=None,
                 minimumWidth=100, textColor=None, editable=True, **kwds):
        """
        Initialise the lineEdit to password mode
        """
        super().__init__(parent, text=text, textAlignment=textAlignment, backgroundText=backgroundText,
                         minimumWidth=minimumWidth, textColor=textColor, editable=editable, **kwds)
        Base._init(self, **kwds)

        # set password mode
        self.setEchoMode(QtWidgets.QLineEdit.Password)


def main():
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.widgets.Widget import Widget
    from ccpn.ui.gui.widgets.Spacer import Spacer

    class Popup(QtWidgets.QMainWindow):
        def __init__(self, title):
            super().__init__()
            self.layout().setContentsMargins(9, 9, 9, 9)

            self.setWindowTitle(title)
            mainWidget = Widget(self, setLayout=True)
            self.setCentralWidget(mainWidget)
            LineEdit(parent=mainWidget, name='Widget-1', grid=(0, 0), text='Enabled - text')
            LineEdit(parent=mainWidget, name='Widget-2', grid=(1, 0), text='Disabled - text', enabled=False)
            widget3 = LineEdit(parent=mainWidget, name='Widget-3', grid=(2, 0), text='Read-only - text')
            widget3.setReadOnly(True)
            widget4 = LineEdit(parent=mainWidget, name='Widget-4', grid=(3, 0), text='Disabled|read-only - text',
                               enabled=False)
            widget4.setReadOnly(True)
            Spacer(mainWidget, 1, 1,
                   QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding,
                   grid=(9, 9))


    app = TestApplication()
    # patch for icon sizes in menus, etc.
    styles = QtWidgets.QStyleFactory()
    app.setStyle(styles.create('fusion'))
    popup = Popup(title='Testing enabled/read-only lineEdits')
    popup.show()

    app.start()


if __name__ == '__main__':
    main()
