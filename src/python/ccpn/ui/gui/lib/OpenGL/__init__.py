"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2023"
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
__dateModified__ = "$dateModified: 2023-12-14 15:20:39 +0000 (Thu, December 14, 2023) $"
__version__ = "$Revision: 3.2.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2018-12-20 13:28:13 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
import sys
from PyQt5 import QtWidgets
from ctypes import util
from ccpn.util.Common import isLinux, isUbuntuVersion


_OpenGLLibraryPathOSX11 = '/System/Library/Frameworks/%s.framework/%s'
util_find_library_bk = util.find_library


def util_find_library_OSX11Patch(name):
    res = util_find_library_bk(name)
    if res:
        return res
    return _OpenGLLibraryPathOSX11 % (name, name)


try:
    try:
        # if isLinux() and isUbuntuVersion('22.04'):
        # NOTE:ED - this now needs to be set BEFORE execution :|
        #     # fix needed for openGL to work on 22.04
        #     os.environ['PYOPENGL_PLATFORM'] = 'x11'
        from OpenGL import GL
        from OpenGL.arrays.vbo import VBO
    except ImportError:
        # Patching for OS X 11.x
        util_find_library_bk = util.find_library
        util.find_library = util_find_library_OSX11Patch
        # now do the imports
        from OpenGL import GL
        from OpenGL.arrays.vbo import VBO


        # restore the util find_library
        util.find_library = util_find_library_bk

except ImportError:
    app = QtWidgets.QApplication(sys.argv)
    QtWidgets.QMessageBox.critical(None, "Error importing OpenGL.",
                                   "OpenGL must be installed to run CcpNmrAnalysis correctly.")
    sys.exit(1)
