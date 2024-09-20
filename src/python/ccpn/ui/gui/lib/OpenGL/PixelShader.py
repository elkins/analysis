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
__dateModified__ = "$dateModified: 2024-01-16 17:10:45 +0000 (Tue, January 16, 2024) $"
__version__ = "$Revision: 3.2.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-12-14 14:18:53 +0100 (Thu, December 14, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from PyQt5 import QtGui
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLShader import ShaderProgramABC
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import getAliasSetting


class PixelShader(ShaderProgramABC):
    """
    Pixel shader for contour plotting

    A very simple shader, uses the projection/viewport matrices to calculate the gl_Position,
    and passes through the gl_Color to set the pixel.
    """

    name = 'pixelShader'
    CCPNSHADER = True

    # shader attributes/uniform constants
    _PMATRIX = 'pMatrix'
    _MVMATRIX = 'mvMatrix'
    _VIEWPORT = 'viewport'

    # attribute/uniform lists
    attributes = {}
    uniforms = {_PMATRIX : (16, np.float32),
                _MVMATRIX: (16, np.float32),
                _VIEWPORT: (4, np.float32),
                }

    # vertex shader to determine the co-ordinates
    vertexShader = """
        #version 120

        uniform mat4 pMatrix;
        uniform mat4 mvMatrix;
        uniform vec4 viewport;
        varying vec4 fragCol;

        void main()
        {
            // calculate the position
            gl_Position = pMatrix * mvMatrix * gl_Vertex;
            fragCol = gl_Color;
        }
        """

    # fragment shader to set the colour
    fragmentShader = """
        #version 120

        varying vec4  fragCol;

        void main()
        {
            // set the pixel colour
            gl_FragColor = fragCol;
        }
        """

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # methods available
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def setProjection(self, left, right, bottom, top, near, far):
        """Set the contents of the projection matrix
        """
        att = QtGui.QMatrix4x4()
        att.ortho(left, right, bottom, top, near, far)
        self._shader.setUniformValue(self.locations[self._PMATRIX], att)

        return att

    def setPMatrix(self, matrix):
        """Set the contents of projection pMatrix
        :param matrix: consisting of 16 float32 elements
        """
        self._shader.setUniformValue(self.locations[self._PMATRIX], QtGui.QMatrix4x4(*matrix).transposed())

    def setMVMatrix(self, matrix):
        """Set the contents of viewport mvMatrix
        :param matrix: consisting of 16 float32 elements
        """
        self._shader.setUniformValue(self.locations[self._MVMATRIX], QtGui.QMatrix4x4(*matrix).transposed())

    def setMV(self, matrix):
        """Set the contents of viewport mvMatrix
        :param matrix: QtGui.QMatrix4x4
        """
        self._shader.setUniformValue(self.locations[self._MVMATRIX], matrix)

    def setPMatrixToIdentity(self):
        """Reset the contents of viewport mvMatrix to the identity-matrix
        """
        self._shader.setUniformValue(self.locations[self._PMATRIX], QtGui.QMatrix4x4())

    def setMVMatrixToIdentity(self):
        """Reset the contents of viewport mvMatrix to the identity-matrix
        """
        self._shader.setUniformValue(self.locations[self._MVMATRIX], QtGui.QMatrix4x4())

    def setViewport(self, viewport):
        """Set the viewport pixel-sizes and devicePixelRatio
        """
        self._shader.setUniformValue(self.locations[self._VIEWPORT], viewport)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Pixel shader for aliased peak plotting
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class AliasedPixelShader(PixelShader):
    """
    Pixel shader for aliased peak plotting

    Uses the projection/viewport matrices to calculate the gl_Position,
    and passes through the gl_Color to set the pixel.
    gl_Color is modified for peaks at different aliased positions
    """

    name = 'aliasedPixelShader'
    CCPNSHADER = True

    # shader attributes/uniform constants
    _ALIAS = 'alias'
    _ALIASPOSITION = 'aliasPosition'
    _BACKGROUND = 'background'
    _ALIASSHADE = 'aliasShade'
    _ALIASENABLED = 'aliasEnabled'

    # attribute/uniform lists for shader
    attributes = dict(PixelShader.attributes)
    attributes |= {_ALIAS: (1, np.float32)}
    uniforms = dict(PixelShader.uniforms)
    uniforms |= {_ALIASPOSITION: (1, np.float32),  # change to a set?
                 _BACKGROUND   : (4, np.float32),
                 _ALIASSHADE   : (1, np.float32),
                 _ALIASENABLED : (1, np.uint32),
                 }

    # vertex shader to determine the co-ordinates
    vertexShader = """
        #version 120

        uniform   mat4  pMatrix;
        uniform   mat4  mvMatrix;
        uniform   vec4  viewport;
        attribute vec4  alias;
        uniform   float aliasPosition;
        varying   float aliased;
        varying   vec4  fragCol;

        void main()
        {
            // calculate the position, set shading value
            gl_Position = pMatrix * mvMatrix * vec4(gl_Vertex.xy, 0.0, 1.0);
            fragCol = gl_Color;
            aliased = (aliasPosition - gl_Vertex.z);

            viewport;
        }
        """

    geometryShader = None

    # fragment shader to set the colour
    fragmentShader = """
        #version 120

        uniform vec4  background;
        uniform float aliasShade;
        uniform int   aliasEnabled;
        varying vec4  fragCol;
        varying float aliased;

        void main()
        {
            // set the pixel colour
            if (abs(aliased) < 0.5) {
                gl_FragColor = fragCol;
            }
            else if (aliasEnabled != 0) {
                // set the colour if aliasEnabled (set opaque or set the alpha)
                gl_FragColor = (aliasShade * fragCol) + (1 - aliasShade) * background;
                //gl_FragColor = vec4(fragCol.xyz, fragCol.w * aliasShade);
            }
            else {
                // skip the pixel
                discard;
            }
        }
        """

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # methods available
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def setAliasPosition(self, aliasX, aliasY):
        """Set the alias position:
        Used to calculate whether the current peak is in the aliased region
        :param aliasX: X alias region
        :param aliasY: Y alias region
        """
        self._shader.setUniformValue(self.locations[self._ALIASPOSITION], float(getAliasSetting(aliasX, aliasY)))

    def setBackground(self, colour):
        """Set the background colour, for use with the solid text
        colour is tuple/list of 4 float/np.float32 elements in range 0.0-1.0
        values outside range will be clipped
        :param colour: tuple/list
        """
        self._shader.setUniformValue(self.locations[self._BACKGROUND], colour)

    def setAliasShade(self, aliasShade):
        """Set the alias shade: a single float in range [0.0, 1.0]
        Used to determine visibility of aliased peaks, 0.0 -> background colour
        :param aliasShade: single float32
        """
        if not isinstance(aliasShade, (float, np.float32)):
            raise TypeError('aliasShade must be a float')
        value = float(np.clip(aliasShade, 0.0, 1.0))

        self._shader.setUniformValue(self.locations[self._ALIASSHADE], value)

    def setAliasEnabled(self, aliasEnabled):
        """Set the alias enabled: bool True/False
        Used to determine visibility of aliased peaks, using aliasShade
        False = disable visibility of aliased peaks
        :param aliasEnabled: bool
        """
        if not isinstance(aliasEnabled, bool):
            raise TypeError('aliasEnabled must be a bool')
        value = 1 if aliasEnabled else 0

        self._shader.setUniformValue(self.locations[self._ALIASENABLED], value)
