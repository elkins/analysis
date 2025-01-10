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
__dateModified__ = "$dateModified: 2025-01-10 16:43:05 +0000 (Fri, January 10, 2025) $"
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
from contextlib import contextmanager
from typing import Generator, Callable
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QWidget
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
def CloseHandler(container: QtWidgets.QWidget, _stacklevelOffset: int = 0) -> Generator[None, None, None]:
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
        closeAllChildren(container, depth=_WidgetRefStore.get(container) or 0)
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


def closeAllChildren(parent: QtWidgets.QWidget, *, depth: int = 0) -> None:
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
        closeAllChildren(child, depth=depth + 1)
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
# testing
#=========================================================================================

def _temporaryOverrideDebugging(logging: Callable[..., None], debug: bool | int) -> None:
    """
    Temporarily override the global debugging and logging behaviour.

    This function updates the global `_LOGGING` and `_DEBUG` variables to the provided values.
    It is typically used to adjust the debugging and logging settings dynamically within a
    specific scope or context.

    :param logging: The logging function to temporarily override `_LOGGING`.
                    This should be a callable that accepts logging messages.
    :type logging: Callable[..., None]
    :param debug: The debug flag to temporarily override `_DEBUG`.
                  Set to True or 1 to enable debug mode, or False or 0 to disable it.
                  Set to 2 for more verbose debugging.
    :type debug: bool | int
    """
    # Declare the globals to be modified within this function.
    global _LOGGING
    global _DEBUG

    # Override the global logging function.
    _LOGGING = logging
    # Override the global debugging flag.
    _DEBUG = debug
