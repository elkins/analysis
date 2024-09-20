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
__dateModified__ = "$dateModified: 2023-12-20 15:19:07 +0000 (Wed, December 20, 2023) $"
__version__ = "$Revision: 3.2.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-12-14 14:19:05 +0100 (Thu, December 14, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from PyQt5 import QtGui
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLShader import ShaderProgramABC
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import getAliasSetting


class TextShader(ShaderProgramABC):
    """
    Main Text shader

    Shader for plotting text, uses a billboard technique by using an offset to determine pixel positions
    Colour of the pixel is set by glColorPointer array.
    Alpha value is grabbed from the texture to give antialiasing and modified by the 'alpha' attribute to
    affect overall transparency.
    """

    name = 'textShader'
    CCPNSHADER = True

    # shader attribute/uniform constants
    _PMATRIX = 'pMatrix'
    _AXISSCALE = 'axisScale'
    _STACKOFFSET = 'stackOffset'
    _VIEWPORT = 'viewport'
    _GLCOLOR = 'glColor'
    _GLMULTITEXCOORD = 'glMultiTexCoord'
    _OFFSET = 'offset'
    _TEXTURE = 'texture'
    _BACKGROUND = 'background'
    _BLENDENABLED = 'blendEnabled'
    _ALPHA = 'alpha'

    # attribute/uniform lists for shaders
    attributes = {_GLCOLOR        : None,
                  _GLMULTITEXCOORD: None,
                  _OFFSET         : None,
                  }
    uniforms = {_PMATRIX     : (16, np.float32),
                _AXISSCALE   : (2, np.float32),
                _STACKOFFSET : (2, np.float32),
                _VIEWPORT    : (4, np.float32),
                _TEXTURE     : (1, np.uint32),
                _BACKGROUND  : (4, np.float32),
                _BLENDENABLED: (1, np.uint32),
                _ALPHA       : (1, np.float32),
                }

    # shader for plotting anti-aliased text to the screen
    vertexShader = """
        #version 120

        uniform   mat4  pMatrix;
        uniform   vec4  axisScale;
        uniform   vec2  stackOffset;
        uniform   vec4  viewport;
        varying   vec4  fragCol;
        varying   vec2  texCoord;
        attribute vec4  offset;

        void main()
        {
            gl_Position = pMatrix * vec4(gl_Vertex.xy * axisScale.xy + offset.xy + stackOffset, 0.0, 1.0);

            texCoord = gl_MultiTexCoord0.st;
            fragCol = gl_Color;
        }
        """

    # fragment shader to determine shading from the texture alpha value and the 'alpha' attribute
    fragmentShader = """
        #version 120

        uniform sampler2D texture;
        uniform vec4      background;
        uniform int       blendEnabled;
        uniform float     alpha;
        varying vec4      fragCol;
        varying vec2      texCoord;
                vec4      texFilter;
                float     opacity;

        void main()
        {
            texFilter = texture2D(texture, texCoord);  // returns float due to glTexImage2D creation as GL_ALPHA
            // colour for blending enabled
            opacity = texFilter.a * alpha;  // only has .alpha component

            if (blendEnabled != 0)
                // multiply the character fade by the color fade to give the actual transparency
                gl_FragColor = vec4(fragCol.xyz, fragCol.w * opacity);

            else   
                // plot a background box around the character
                gl_FragColor = vec4((fragCol.xyz * opacity) + (1.0 - opacity) * background.xyz, 1.0);
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

    def setPMatrixToIdentity(self):
        """Reset the contents of viewport mvMatrix to the identity-matrix
        """
        self._shader.setUniformValue(self.locations[self._PMATRIX], QtGui.QMatrix4x4())

    def setAxisScale(self, axisScale):
        """Set the axisScale values
        :param axisScale: consisting of 4 float32 elements
        """
        self._shader.setUniformValue(self.locations[self._AXISSCALE], axisScale)

    def setStackOffset(self, stackOffset):
        """Set the stacking value for the 1d widget
        :param stackOffset: consisting of 2 float32 elements, the stacking offset in thje X, Y dimensions
        """
        self._shader.setUniformValue(self.locations[self._STACKOFFSET], stackOffset)

    def setTextureID(self, textureID):
        """Set the texture ID, determines which texture the text bitmaps are taken from
        :param textureID: uint32
        """
        self._shader.setUniformValue(self.locations[self._TEXTURE], textureID)

    def setBackground(self, colour):
        """Set the background colour, for use with the solid text
        :param colour: consisting of 4 float32 elements
        """
        self._shader.setUniformValue(self.locations[self._BACKGROUND], colour)

    def setBlendEnabled(self, blendEnabled):
        """Set the blend enabled flag, determines whether the characters are
        surrounded with a solid background block
        :param blendEnabled: single uint32
        """
        if not isinstance(blendEnabled, bool):
            raise TypeError('blendEnabled must be a bool')
        value = 1 if blendEnabled else 0

        self._shader.setUniformValue(self.locations[self._BLENDENABLED], value)

    def setAlpha(self, alpha):
        """Set the alpha value, a multiplier to the transparency 0 - completely transparent; 1 - solid
        alpha to clipped to value [0.0, 1.0]
        :param alpha: single float32
        """
        if not isinstance(alpha, (float, np.float32)):
            raise TypeError('value must be a float')
        value = float(np.clip(alpha, 0.0, 1.0))

        self._shader.setUniformValue(self.locations[self._ALPHA], value)

    def setViewport(self, viewport):
        """Set the viewport pixel-sizes and devicePixelRatio
        """
        self._shader.setUniformValue(self.locations[self._VIEWPORT], viewport)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Text shader for displaying text in aliased regions
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class AliasedTextShader(TextShader):
    """
    Text shader for displaying text in aliased regions

    Shader for plotting text, uses a billboard technique by using an offset to determine pixel positions
    Colour of the pixel is set by glColorPointer array.
    Alpha value is grabbed from the texture to give antialiasing and modified by the 'alpha' attribute to
    affect overall transparency.
    """

    name = 'aliasedTextShader'
    CCPNSHADER = True

    # shader attribute/uniform constants
    _MVMATRIX = 'mvMatrix'
    _ALIASPOSITION = 'aliasPosition'
    _ALIASSHADE = 'aliasShade'
    _ALIASENABLED = 'aliasEnabled'

    # additional attribute/uniform lists for shader
    uniforms = dict(TextShader.uniforms)

    uniforms |= {_MVMATRIX     : (16, np.float32),
                 _ALIASPOSITION: (1, np.float32),
                 _ALIASSHADE   : (1, np.float32),
                 _ALIASENABLED : (1, np.uint32),
                 }

    # shader for plotting smooth text to the screen in aliased Regions
    vertexShader = """
        #version 120

        uniform   mat4  pMatrix;
        uniform   mat4  mvMatrix;
        uniform   vec4  axisScale;
        uniform   vec2  stackOffset;
        uniform   vec4  viewport;
        uniform   float aliasPosition;
        varying   float aliased;
        varying   vec4  fragCol;
        varying   vec2  texCoord;
        attribute vec4  offset;

        void main()
        {
            gl_Position = pMatrix * mvMatrix * vec4(gl_Vertex.xy * axisScale.xy + offset.xy + stackOffset, 0.0, 1.0);

            texCoord = gl_MultiTexCoord0.st;
            fragCol = gl_Color;
            aliased = (aliasPosition - gl_Vertex.z);
        }
        """

    # fragment shader to determine shading from the texture alpha value and the 'alpha' attribute
    fragmentShader = """
        #version 120

        uniform sampler2D texture;
        uniform vec4      background;
        uniform int       blendEnabled;
        uniform float     alpha;
        uniform float     aliasShade;
        uniform int       aliasEnabled;
        varying vec4      fragCol;
        varying vec2      texCoord;
                vec4      texFilter;
                float     opacity;
        varying float     aliased;

        void main()
        {
            texFilter = texture2D(texture, texCoord);  // returns float due to glTexImage2D creation as GL_ALPHA
            // colour for blending enabled
            opacity = texFilter.a * alpha;  // only has .alpha component

            // set the pixel colour
            if (abs(aliased) < 0.5)
                if (blendEnabled != 0)
                    // multiply the character fade by the color fade to give the actual transparency
                    gl_FragColor = vec4(fragCol.xyz, fragCol.w * opacity);

                else   
                    // plot a background box around the character
                    gl_FragColor = vec4((fragCol.xyz * opacity) + (1.0 - opacity) * background.xyz, 1.0);

            else if (aliasEnabled != 0) {
                // modify the opacity
                opacity *= aliasShade;

                if (blendEnabled != 0)
                    // multiply the character fade by the color fade to give the actual transparency
                    gl_FragColor = vec4(fragCol.xyz, fragCol.w * opacity);

                else   
                    // plot a background box around the character
                    gl_FragColor = vec4((fragCol.xyz * opacity) + (1.0 - opacity) * background.xyz, 1.0);
            }
            else
                // skip the pixel
                discard;
        }
        """

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # methods available
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

    def setMVMatrixToIdentity(self):
        """Reset the contents of viewport mvMatrix to the identity-matrix
        """
        self._shader.setUniformValue(self.locations[self._MVMATRIX], QtGui.QMatrix4x4())

    def setAliasPosition(self, aliasX, aliasY):
        """Set the alias position:
        Used to calculate whether the current peak is in the aliased region
        :param aliasX: X alias region
        :param aliasY: Y alias region
        """
        self._shader.setUniformValue(self.locations[self._ALIASPOSITION], float(getAliasSetting(aliasX, aliasY)))

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
