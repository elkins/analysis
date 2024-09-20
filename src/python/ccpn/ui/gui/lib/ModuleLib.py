"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-05-17 13:37:45 +0100 (Fri, May 17, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2024-05-16 11:17:23 +0100 (Thu, May 16, 2024) $"

#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5.QtWidgets import QDialog
from ccpn.framework.Application import getApplication
from ccpn.ui.gui.widgets.SpeechBalloon import SpeechBalloon
from ccpn.util.Logging import getLogger


BLOCKINGDIALOGS = (QDialog, SpeechBalloon)
_DEBUG = False


def getBlockingDialogs(msg: str = None) -> list | None:
    """Return the list of dialogs that are visible and considered as blocking the mainWindow event-loop.
    """
    if not isinstance(msg, str):
        raise TypeError(f'msg must be a str')
    app = getApplication()
    if app and app.hasGui:
        dialogs = list(filter(lambda pp: isinstance(pp, BLOCKINGDIALOGS) and pp.isVisible(),
                              app.ui.qtApp.allWidgets()))
        if _DEBUG: getLogger().debug(f'==> found dialogs {msg} {dialogs}')
        return dialogs
