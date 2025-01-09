"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
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
__dateModified__ = "$dateModified: 2025-01-09 15:50:10 +0000 (Thu, January 09, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2025-01-09 15:25:55 +0100 (Thu, January 09, 2025) $"

#=========================================================================================
# Start of code
#=========================================================================================

from functools import partial
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QPushButton, QApplication

from ccpn.ui.gui.lib.WidgetClosingLib import (_getIndent,
                                              _ConsoleStyle, CloseHandler, closeWidget,
                                              _temporaryOverrideDebugging)


class BaseWidget(QWidget):
    def __init__(self, name):
        super().__init__()
        self._name = name
        self.setStyleSheet("""QWidget {
                                border: 2px solid palette(highlight);
                                border-radius: 2px;
                            }""")

    def _preClose(self):
        from ccpn.ui.gui.lib.WidgetClosingLib import _LOGGING, _DEBUG

        if _DEBUG:
            _LOGGING(f"{_getIndent(self)}{_ConsoleStyle.fg.darkred}Pre-closing "
                     f"{self._name}{_ConsoleStyle.reset}")

    def _postClose(self):
        from ccpn.ui.gui.lib.WidgetClosingLib import _LOGGING, _DEBUG

        if _DEBUG:
            _LOGGING(f"{_getIndent(self)}{_ConsoleStyle.fg.darkblue}Post-closing "
                     f"{self._name}{_ConsoleStyle.reset}")

    def closeEvent(self, event):
        from ccpn.ui.gui.lib.WidgetClosingLib import _LOGGING, _DEBUG

        if _DEBUG: _LOGGING(
                f"{_getIndent(self)}{_ConsoleStyle.fg.darkyellow}closeEvent {self._name}{_ConsoleStyle.reset}")
        with CloseHandler(self):
            super().closeEvent(event)

    def close(self):
        from ccpn.ui.gui.lib.WidgetClosingLib import _LOGGING, _DEBUG

        if _DEBUG: _LOGGING(f"{_getIndent(self)}{_ConsoleStyle.fg.yellow}==> {self._name}{_ConsoleStyle.reset}")
        super().close()
        if _DEBUG: _LOGGING(f"{_getIndent(self)}{_ConsoleStyle.fg.yellow}<== {self._name}{_ConsoleStyle.reset}")


class ChildWidget(BaseWidget):
    def __init__(self, name):
        super().__init__(name)
        label = QtWidgets.QLabel(name)
        label._name = f'_{name}_'
        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)


class FrameWidget(BaseWidget):
    def __init__(self, name):
        super().__init__(name)
        self.child1 = ChildWidget('4')
        self.child2 = ChildWidget('5')
        layout = QVBoxLayout()
        layout.addWidget(self.child1)
        layout.addWidget(self.child2)
        self.setLayout(layout)

        self.frame1 = frame1 = QFrame()
        frame1._name = '6'
        layout.addWidget(frame1)
        frLayout = QVBoxLayout()
        child1 = ChildWidget('7')
        child2 = ChildWidget('8')
        frLayout.addWidget(child1)
        frLayout.addWidget(child2)
        frame1.setLayout(frLayout)

        self.frame2 = frame1 = QFrame()
        frame1._name = '9'
        layout.addWidget(frame1)
        frLayout = QVBoxLayout()
        child1 = ChildWidget('10')
        child2 = ChildWidget('11')
        frLayout.addWidget(child1)
        frLayout.addWidget(child2)
        frame1.setLayout(frLayout)


class ParentWidget(BaseWidget):
    def __init__(self, name):
        super().__init__(name)
        self.frame = FrameWidget('1')
        self.child1 = ChildWidget('2')
        self.child2 = ChildWidget('3')
        layout = QVBoxLayout()
        close_button: QtWidgets.QPushButton = QPushButton("Close Parent")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        close_button = QPushButton("Close Frame")
        # close_button.clicked.connect(partial(close_all_children, self.frame.frame2))
        close_button.clicked.connect(partial(closeWidget, self.frame.frame2))
        layout.addWidget(close_button)
        close_button = QPushButton("Close child")
        close_button.clicked.connect(self.frame.child1.close)
        layout.addWidget(close_button)
        layout.addWidget(self.frame)
        layout.addWidget(self.child1)
        layout.addWidget(self.child2)
        self.setLayout(layout)


def mainWidgetClosing():
    # override the global settings for local running

    _temporaryOverrideDebugging(lambda msg, stacklevel=None: print(msg), 2)
    # make a main-window and show the widget
    app = QApplication([])
    parent = ParentWidget('TOP')
    parent.show()
    app.exec_()


#=========================================================================================
# main
#=========================================================================================

if __name__ == '__main__':
    # call the main code
    mainWidgetClosing()
