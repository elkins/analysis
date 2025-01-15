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
__dateModified__ = "$dateModified: 2025-01-03 18:15:19 +0000 (Fri, January 03, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2024-05-16 11:17:23 +0100 (Thu, May 16, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets
from ccpn.framework.Application import getApplication
from ccpn.ui.gui.widgets.SpeechBalloon import SpeechBalloon
from ccpn.ui.gui.guiSettings import consoleStyle
from ccpn.util.Logging import getLogger


BLOCKINGDIALOGS = (QtWidgets.QDialog, QtWidgets.QMenu, SpeechBalloon)
_DEBUG = False
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
