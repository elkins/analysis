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
__dateModified__ = "$dateModified: 2024-09-13 15:20:23 +0100 (Fri, September 13, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-04-16 12:14:50 +0000 (Thu, April 16, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
from PyQt5 import QtGui, QtWidgets

from ccpn.util.Path import aPath
from ccpn.ui.gui.widgets.LineEdit import LineEdit

from ccpn.ui.gui.guiSettings import COLOUR_BLIND_LIGHTGREEN, COLOUR_BLIND_MEDIUM, COLOUR_BLIND_DARKGREEN, \
    COLOUR_BLIND_RED, COLOUR_BLIND_ORANGE


VALIDROWCOLOUR = COLOUR_BLIND_LIGHTGREEN
ACCEPTROWCOLOUR = COLOUR_BLIND_DARKGREEN
REJECTROWCOLOUR = COLOUR_BLIND_ORANGE
INVALIDROWCOLOUR = COLOUR_BLIND_RED


def _validPath(path) -> bool:
    "Return True if path is valid"
    # catch any anomalies in expanding or testing _path
    try:
        _path = aPath(path)
        result = _path.exists()
    except RuntimeError:
        result = False
    return result


def _validFile(path) -> bool:
    "Return True if path is valid and a file"
    # catch any anomalies in expanding or testing _path
    try:
        _path = aPath(path)
        result = _path.exists() and _path.is_file()
    except RuntimeError:
        result = False
    return result


VALIDFILE = 'File'
VALIDPATH = 'Path'
VALIDMODES = (VALIDFILE, VALIDPATH)
VALIDFUNCS = (_validFile, _validPath)


class PathValidator(QtGui.QValidator):

    def __init__(self, parent=None, fileMode=VALIDPATH):
        super().__init__(parent=parent)

        if fileMode not in VALIDMODES:
            raise NotImplemented("Error, fileMode %s not supported, use %s" % (str(fileMode), str(VALIDMODES)))
        self.fileMode = fileMode
        self._func = VALIDFUNCS[VALIDMODES.index(fileMode)]

    def validate(self, p_str, p_int):
        # filePath = p_str.strip()
        # filePath = os.path.expanduser(filePath)

        palette = self.parent().palette()

        if not p_str or self._func(p_str):
            palette.setColor(QtGui.QPalette.Base, QtGui.QPalette().base().color())
            state = QtGui.QValidator.Acceptable  # entry is valid
        else:
            palette.setColor(QtGui.QPalette.Base, INVALIDROWCOLOUR)
            state = QtGui.QValidator.Intermediate  # entry is NOT valid, but can continue editing
        self.parent().setPalette(palette)

        return state, p_str, p_int

    def clearValidCheck(self):
        palette = self.parent().palette()
        palette.setColor(QtGui.QPalette.Base, QtGui.QPalette().base().color())
        self.parent().setPalette(palette)

    def resetCheck(self):
        self.validate(self.parent().text(), 0)

    @property
    def checkState(self):
        state, _, _ = self.validate(self.parent().text(), 0)
        return state


class PathEdit(LineEdit):
    """LineEdit widget that contains validator for checking filePaths exists
    """

    def __init__(self, parent, fileMode=VALIDPATH, **kwds):
        kwds.setdefault('textAlignment', 'l')
        super().__init__(parent=parent, **kwds)

        if fileMode not in VALIDMODES:
            raise ValueError("Error, fileMode %s not supported, use %s" % (str(fileMode), str(VALIDMODES)))

        self.setValidator(PathValidator(parent=self, fileMode=fileMode))
        self.validator().resetCheck()
