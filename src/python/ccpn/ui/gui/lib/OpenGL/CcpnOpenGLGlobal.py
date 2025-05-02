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
__dateModified__ = "$dateModified: 2025-05-02 11:23:07 +0100 (Fri, May 02, 2025) $"
__version__ = "$Revision: 3.3.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2018-12-20 13:28:13 +0000 (Thu, December 20, 2018) $"

#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets, QtGui
from typing import TypeVar, Union
from ccpn.ui.gui.lib.OpenGL import GL
from ccpn.ui.gui.lib.OpenGL.PixelShader import PixelShader, AliasedPixelShader
from ccpn.ui.gui.lib.OpenGL.TextShader import TextShader, AliasedTextShader
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLFonts import CcpnGLFont
from ccpn.framework.PathsAndUrls import openGLFontsPath
from ccpn.framework.Preferences import getPreferences
from ccpn.util.decorators import singleton
from ccpn.util.Logging import getLogger


GLFONT_DEFAULT = 'OpenSans-Regular'
GLFONT_SUBSTITUTE = 'OpenSans-Regular'
GLFONT_DEFAULTSIZE = 13  # moved to preferences.appearance
_OLDGLFONT_SIZES = [10, 11, 12, 13, 14, 16, 18, 20, 22, 24]
GLFONT_DICT = {}

GLFONT_FILE = 0
GLFONT_NAME = 1
GLFONT_SIZE = 2
GLFONT_SCALE = 3

GLFONT_TRANSPARENT = 'Transparent'
GLFONT_DEFAULTFONTFILE = 'glAllFonts.fnt'
GLPIXELSHADER = 'GLPixelShader'
GLTEXTSHADER = 'GLTextShader'

GLWidget = TypeVar('GLWidget',
                   bound=Union['ccpn.ui.gui.lib.OpenGL.CcpnOpenGL.CcpnGLWidget',
                   'ccpn.ui.gui.widgets.GLAxis.GuiNdWidgetAxis'])


#=========================================================================================
# Global data accessible by all shaders and GL-widgets
#=========================================================================================

@singleton
class GLGlobalData(QtWidgets.QWidget):
    """
    Class to handle the common information between all the GL-widgets.
    """

    def __init__(self, parent: GLWidget | None = None):
        """
        Initialise the global data.

        :param parent: The parent widget.
        """
        super().__init__(parent)

        self.fonts: dict[str, CcpnGLFont] = {}
        self.shaders: dict[str, PixelShader] | None = None
        self._texturesBound: bool = False
        self.loadFonts()

    def loadFonts(self) -> None:
        """
        Load all the necessary GLFonts.
        """
        if not (prefs := getPreferences()):
            raise RuntimeError('No preferences found')

        self.fonts[GLFONT_DEFAULT] = CcpnGLFont(openGLFontsPath / GLFONT_DEFAULTFONTFILE, activeTexture=0, scale=1.0)
        _foundFonts = self.fonts[GLFONT_DEFAULT].fontGlyph
        # find all the fonts in the list that have a matching 2* size, for double resolution retina displays
        self.GLFONT_SIZES = [_size for _size in _foundFonts.keys() if _size * 2 in _foundFonts.keys()]

        # set the current size from the preferences
        _size = prefs.appearance.spectrumDisplayFontSize
        if _size in self.GLFONT_SIZES:
            self.glSmallFontSize = _size
        else:
            self.glSmallFontSize = GLFONT_DEFAULTSIZE

        # set the current size from the preferences
        _size = prefs.appearance.spectrumDisplayAxisFontSize
        if _size in self.GLFONT_SIZES:
            self.glAxisFontSize = _size
        else:
            self.glAxisFontSize = GLFONT_DEFAULTSIZE

    def bindFonts(self) -> None:
        """
        Bind the font textures to the GL textures.
        MUST be called inside GL current context, i.e., after GL.makeCurrent or inside initializeGL, paintGL.
        """
        if not self._texturesBound:
            for name, fnt in self.fonts.items():
                fnt._bindFontTexture()
            self._texturesBound = True

    def initialiseShaders(self, glWidget: GLWidget) -> None:
        """
        Initialise the shaders for the specified glWidget.

        :param glWidget: The GL widget to initialise shaders for.
        """
        _ver = QtGui.QOpenGLVersionProfile()
        self._GLVersion = GL.glGetString(GL.GL_VERSION)
        self._GLShaderVersion = GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION)
        getLogger().debug(f"OpenGL: {self._GLVersion.decode('utf-8')}")
        getLogger().debug(f"GLSL: {self._GLShaderVersion.decode('utf-8')}")
        _format = QtGui.QSurfaceFormat()
        getLogger().debug(f"Surface: {_format.version()}")

        # add some shaders to the global data
        # not sure that this loop is required in this form, may need duplicates of the same type?
        glWidget.shaders = {}
        for _shader in (PixelShader, TextShader, AliasedPixelShader, AliasedTextShader):  # LineShader):
            _new = _shader()
            glWidget.shaders[_new.name] = _new

        glWidget._shaderPixel = glWidget.shaders[PixelShader.name]
        glWidget._shaderText = glWidget.shaders[TextShader.name]
        glWidget._shaderPixelAlias = glWidget.shaders[AliasedPixelShader.name]
        glWidget._shaderTextAlias = glWidget.shaders[AliasedTextShader.name]
        # self.glWidget._shaderLine = self.glWidget.shaders[LineShader.name]
