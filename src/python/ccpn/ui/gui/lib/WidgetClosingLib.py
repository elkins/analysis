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
__dateModified__ = "$dateModified: 2025-01-07 16:33:51 +0000 (Tue, January 07, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2024-12-19 12:11:19 +0000 (Thu, December 19, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

import weakref
import gc
from functools import partial
from contextlib import contextmanager
from typing import TypeVar, Generator
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFrame
from ccpn.util.Logging import getLogger


_PRECLOSE = '_preClose'
_POSTCLOSE = '_postClose'
_NAME = '_name'


class _ConsoleStyle():
    """Colors class:reset all colors with colors.reset; two
    subclasses fg for foreground
    and bg for background; use as colors.subclass.colorname.
    i.e. colors.fg.red or colors.bg.greenalso, the generic bold, disable,
    underline, reverse, strike through,
    and invisible work with the main class i.e. colors.bold
    """
    # Smaller version of that defined in Common to remove any non-built-in imports
    reset = '\033[0m'


    class fg:
        darkred = '\033[31m'
        darkyellow = '\033[33m'
        darkblue = '\033[34m'
        darkgrey = '\033[90m'
        red = '\033[91m'
        lightgrey = '\033[37m'
        yellow = '\033[93m'
        white = '\033[97m'


TABWIDTH = 4
_DEBUG = False  # can be True/False (equivalent to 0, 1), or 0,1,2 - 2 is the most verbose
_closeBlockingLevel = 0  # garbage is only collected on the last exit
_GARBAGECOLLECT = False
_LOGGING = getLogger().debug
_WidgetRefStore = weakref.WeakKeyDictionary()
_WidgetRefContextStore = weakref.WeakKeyDictionary()

#=========================================================================================
# close handlers
#=========================================================================================

CloseHandlerType = TypeVar("CloseHandlerType", bound='CloseHandler')


def _debugAttrib(widget: QWidget, attrib: str) -> None:
    """
    Print debug statement for this widget and attrib.

    :param widget: The widget instance to process.
    :param attrib: The attribute name to look for in the widget.
    """
    if _DEBUG:
        # uses stacklevel=2 to allow for source-method calling _debugAttrib
        _LOGGING(f"{_getIndent(widget)}{_ConsoleStyle.fg.darkblue}{attrib} - "
                 f"{getattr(widget, _NAME, '')} {widget}{_ConsoleStyle.reset}", stacklevel=2)


def _getIndent(widget: QWidget) -> str:
    """
    Return a string of characters whose length is based on the depth of the specified
    widget in its qt-hierarchy.

    :param widget: The widget instance to process.
    :type widget: QtWidgets.QWidget
    :return: An indent string based on the widget's depth.
    :rtype: str
    """
    return (f"{_ConsoleStyle.fg.darkgrey}"
            f"{(_WidgetRefStore.get(widget) or 0) * ('-' + ' ' * (TABWIDTH - 1))}"
            f"{_ConsoleStyle.reset}")


def _processFunc(widget: QWidget, attrib: str) -> None:
    """
    Process a function attribute of a widget if it exists and is callable.

    :param widget: The widget instance to process.
    :type widget: QtWidgets.QWidget
    :param attrib: The attribute name to look for in the widget.
    """
    indent = _getIndent(widget)
    if (func := getattr(widget, attrib, None)) and callable(func):
        if int(_DEBUG) > 1:
            _LOGGING(f"{indent}{_ConsoleStyle.fg.lightgrey}here {getattr(widget, _NAME, '')} - "
                     f"{widget}{_ConsoleStyle.reset}")
        func()
    elif int(_DEBUG) > 1:
        _LOGGING(f"{indent}{_ConsoleStyle.fg.lightgrey}here {getattr(widget, _NAME, '')} - "
                 f"{widget} - no {attrib}{_ConsoleStyle.reset}")


# Capitalised for clarity because acts like a class
@contextmanager
def CloseHandler(container: QtWidgets.QWidget, *, _stacklevelOffset: int = 0) -> Generator[None, None, None]:
    """
    Context manager for handling the closing of a QWidget and its children.

    :param container: The QWidget container to manage.
    :type container: QtWidgets.QWidget
    :yield: None
    """
    global _closeBlockingLevel

    # keep a temporary handle to prevent garbage-collection until handler exits
    _strongRef = container
    _WidgetRefContextStore[container] = True
    indent = _getIndent(container)
    _closeBlockingLevel += 1
    try:
        if _DEBUG:
            # uses stacklevel=3 to allow for context-manager and source-method calling CloseHandler
            _LOGGING(f"{indent}{_ConsoleStyle.fg.white}CLOSEEVENT "
                     f"{getattr(container, _NAME, str(container))} - "
                     f"{_ConsoleStyle.reset}", stacklevel=3 + _stacklevelOffset)
        close_all_children(container, depth=_WidgetRefStore.get(container) or 0)
        yield
    except Exception as es:
        if _DEBUG:
            _LOGGING(f"{indent}An error occurred: {es}", stacklevel=3 + _stacklevelOffset)
        raise
    finally:
        # call the post-close method on the container, called AFTER all nested-children have closed
        _processFunc(container, _POSTCLOSE)
        # Schedule the widget for deletion
        container.deleteLater()

        if _closeBlockingLevel <= 0:
            raise RuntimeError('Error: CloseHandler blocking already at 0')
        _closeBlockingLevel -= 1
        # clean-up on last exit
        if _closeBlockingLevel == 0 and _GARBAGECOLLECT:
            if _DEBUG:
                _LOGGING(f"{_ConsoleStyle.fg.darkgrey}{indent}Garbage Collection{_ConsoleStyle.reset}",
                         stacklevel=3 + _stacklevelOffset)
            # remove blockers to release widgets
            gc.collect()


def close_all_children(parent: QtWidgets.QWidget, *, depth: int = 0) -> None:
    """
    Recursively close all children of a QWidget, processing pre-close and post-close functions.

    :param parent: The parent QWidget whose children are to be closed.
    :param depth: The current depth in the widget hierarchy.
    """
    if _WidgetRefStore.get(parent) is not None:
        return
    # store the depth for debugging
    _WidgetRefStore[parent] = depth
    # call the pre-close method on the container, called BEFORE all nested-children have closed
    _processFunc(parent, _PRECLOSE)
    for child in parent.findChildren(QWidget, options=QtCore.Qt.FindDirectChildrenOnly):
        close_all_children(child, depth=depth + 1)
        child.close()  # be careful, this calls the CloseHandler from the child closeEvent :|
        if not _WidgetRefContextStore.get(child):
            # QWidget has not called the closeHandler
            _processFunc(child, _POSTCLOSE)


#=========================================================================================
# close any widget with this if it doesn't have closeEvent
#=========================================================================================

def closeWidget(widget: QWidget):
    """
    Close the specified widget using a CloseHandler context manager.

    This function is used for closing other widgets. It logs the closing action if debugging is enabled.

    :param widget: The widget to be closed.
    :type widget: QtWidgets.QWidget
    """
    with CloseHandler(widget, _stacklevelOffset=1):
        if _DEBUG:
            _LOGGING(f'CLOSING... {widget}')
        widget.close()

    # for the same widget, subclass closeEvent as above


#=========================================================================================
# test classes
#=========================================================================================

class BaseWidget(QWidget):
    def __init__(self, name):
        super().__init__()
        self._name = name
        self.setStyleSheet("""QWidget {
                                border: 2px solid palette(highlight);
                                border-radius: 2px;
                            }""")

    def _preClose(self):
        if _DEBUG:
            _LOGGING(f"{_getIndent(self)}{_ConsoleStyle.fg.darkred}Pre-closing "
                     f"{self._name}{_ConsoleStyle.reset}")

    def _postClose(self):
        if _DEBUG:
            _LOGGING(f"{_getIndent(self)}{_ConsoleStyle.fg.darkblue}Post-closing "
                     f"{self._name}{_ConsoleStyle.reset}")

    def closeEvent(self, event):
        if _DEBUG: _LOGGING(
                f"{_getIndent(self)}{_ConsoleStyle.fg.darkyellow}closeEvent {self._name}{_ConsoleStyle.reset}")
        with CloseHandler(self):
            super().closeEvent(event)

    def close(self):
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


#=========================================================================================
# main
#=========================================================================================

def main():
    # override the global settings for local running
    global _LOGGING
    global _DEBUG

    _LOGGING = lambda msg, stacklevel=None: print(msg)
    _DEBUG = 2

    # make a main-window and show the widget
    app = QApplication([])
    parent = ParentWidget('TOP')
    parent.show()
    app.exec_()


if __name__ == '__main__':
    # call the main code
    main()
