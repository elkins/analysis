"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2024-12-20 11:37:54 +0000 (Fri, December 20, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2024-05-16 11:17:23 +0100 (Thu, May 16, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets, QtCore, sip
from ccpn.framework.Application import getApplication
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.SpeechBalloon import SpeechBalloon
from ccpn.ui.gui.guiSettings import consoleStyle
from ccpn.util.Logging import getLogger


BLOCKINGDIALOGS = (QtWidgets.QDialog, QtWidgets.QMenu, SpeechBalloon)
_DEBUG = True
_RAISEERROR = False


def getBlockingDialogs(msg: str = None) -> bool:
    """
    Check if there is any blocking dialog in the application.

    This function checks if there is any QDialog, QMenu, or SpeechBalloon
    currently blocking the main window of the application.

    :param msg: Optional message for debugging purposes.
    :type msg: str, optional
    :raises TypeError: If `msg` is not a string.
    :return: True if a blocking dialog is present, False otherwise.
    :rtype: bool
    """
    if not isinstance(msg, str):
        raise TypeError(f'msg must be a str')
    app = getApplication()
    if app and app.hasGui:
        state = (QtWidgets.QApplication.activePopupWidget() or
                 QtWidgets.QApplication.activeModalWidget() or
                 QtWidgets.QApplication.activeWindow())
        blocked = isinstance(state, BLOCKINGDIALOGS)
        if _DEBUG:
            getLogger().debug(f'{consoleStyle.fg.yellow}==> {msg} {state}:{blocked}'
                              f'{consoleStyle.reset}')
        return blocked


def _closeAllChildren(widget: QtWidgets.QWidget, *, depth: int = 4):
    """
    Recursively close all child widgets of a given widget.

    This function closes all child widgets of the specified widget up to a certain depth.
    It can optionally ignore closing the widget itself.

    :param widget: The parent widget whose children will be closed.
    :type widget: QtWidgets.QWidget
    :param depth: The depth level for indentation in debug messages, defaults to 4.
    :type depth: int, optional
    """
    _msg = f'{consoleStyle.fg.lightgrey}{" " * depth}=> {widget}'
    for child in widget.findChildren(QtWidgets.QWidget, options=QtCore.Qt.FindDirectChildrenOnly):
        _closeAllChildren(child, depth=depth + 4)
        try:
            if issubclass(child.__class__, Base):
                child._close(depth=depth + 4)
                _msg += f'{consoleStyle.fg.darkgreen} closed'
        except AttributeError:
            _msg += f'{consoleStyle.fg.red} error'
            if _RAISEERROR:
                raise
        finally:
            if not sip.isdeleted(child):
                child.setParent(None)
                child.deleteLater()
    if _DEBUG: print(_msg, f'{consoleStyle.reset}')
