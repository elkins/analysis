"""
Module containing functions for defining GLSL shaders.
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
__dateModified__ = "$dateModified: 2024-01-19 13:51:02 +0000 (Fri, January 19, 2024) $"
__version__ = "$Revision: 3.2.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2018-12-20 13:28:13 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
import os
from PyQt5 import QtGui
from ccpn.ui.gui.lib.OpenGL import GL
from ccpn.util.Logging import getLogger
from ccpn.ui.gui.guiSettings import consoleStyle


_DEBUG = False


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ShaderProgramABC - Class defining a GL shader program
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ShaderProgramABC(object):
    """
    Class defining a GL shader program
    A shader is defined by the following objects
    vertexShader, a string object containg the code to be compiled for the vertex shader.
    e.g.
    
    vertexShader = '''
                    #version 120
                    
                    varying vec4 fragCol;
                    
                    void main()
                    {
                      fragCol = gl_Color;
                    }
                    '''
    fragmentShader is similarly defined
    
    attributes is a list of the attributes that can be accessed from the shader
    e.g.
    
    attributes = {'pMatrix' : (16, np.float32),
                  }
                  
                  pMatrix is a block of 16 np.float32 objects


    Version Tags for OpenGL and GLSL Versions
    OpenGL  GLSL        #version tag
    1.2 	none 	    none
    2.0 	1.10.59 	110
    2.1 	1.20.8 	    120 <- should be the lowest needed
    3.0 	1.30.10 	130
    3.1 	1.40.08 	140
    3.2 	1.50.11 	150 <- can now get it to work from here :)
    3.3 	3.30.6  	330
    4.0 	4.00.9 	    400
    4.1 	4.10.6 	    410
    4.2 	4.20.6  	420
    4.3 	4.30.6  	430

    (On MacOS, anything above 2.1 causes problems - I think solved now)
    """

    name = None
    CCPNSHADER = False

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # shaders

    vertexShader = None
    geometryShader = None
    fragmentShader = None

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # dicts containing the attributes/uniforms that can be accessed in the shader

    attributes = {}
    uniforms = {}

    def __init__(self):
        """
        Initialise the shaderProgram with vertex/geometry/fragment shaders, and attributes/uniforms
        """

        # check that the required fields have been set
        if not (self.vertexShader or self.fragmentShader):
            raise RuntimeError('ShaderProgram is not correctly defined')

        try:
            self._shader = shader = QtGui.QOpenGLShaderProgram()
            self.vs_id = shader.addShaderFromSourceCode(QtGui.QOpenGLShader.Vertex,
                                                        self.vertexShader) if self.vertexShader else None
            self.geom_id = shader.addShaderFromSourceCode(QtGui.QOpenGLShader.Geometry,
                                                          self.geometryShader) if self.geometryShader else None
            self.frag_id = shader.addShaderFromSourceCode(QtGui.QOpenGLShader.Fragment,
                                                          self.fragmentShader) if self.fragmentShader else None
            shader.link()

            self.program_id = shader.programId()

        except Exception as es:
            esType, esValue, esTraceback = sys.exc_info()
            _ver = QtGui.QOpenGLVersionProfile()
            self._GLVersion = GL.glGetString(GL.GL_VERSION)
            self._GLShaderVersion = GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION)
            _format = QtGui.QSurfaceFormat()
            msg = f"OpenGL: {self._GLVersion.decode('utf-8')}\n" \
                  f"GLSL: {self._GLShaderVersion.decode('utf-8')}\n" \
                  f"Surface: {_format.version()}\n\n" \
                  f"{es}\n" \
                  f"{esType}\n" \
                  f"{esTraceback}"
            raise RuntimeError(msg)

        if _DEBUG:
            getLogger().debug(f'{self.name} - {self.vs_id} {self.geom_id} {self.frag_id} ~~~~~~~~~~~~~~~')

        self.locations = {}

        # define attributes to be passed to the shaders
        for att in self.attributes:
            if (val := shader.attributeLocation(att)) == -1:
                getLogger().debug2(f'--> {self.name:20} attribute {att} is not defined')
            self.locations[att] = val

        # define uniforms to be passed to the shaders
        for uni in self.uniforms:
            if (val := shader.uniformLocation(uni)) == -1:
                getLogger().debug2(f'--> {self.name:20} uniform {uni} is not defined')
            self.locations[uni] = val

        if _DEBUG:
            getLogger().debug('\n'.join(f'   {k:20}  :  {v}' for k, v in self.locations.items()))

    @staticmethod
    def _addGLShader(source, shader_type):
        """Function for compiling a GLSL shader

        :param source: String containing shader source code
        :param shader_type: valid OpenGL shader type: GL_VERTEX_SHADER or GL_FRAGMENT_SHADER
        :return: int; Identifier for shader if compilation is successful
        """
        shader_id = 0
        try:
            shader_id = GL.glCreateShader(shader_type)
            GL.glShaderSource(shader_id, source)
            GL.glCompileShader(shader_id)
            if GL.glGetShaderiv(shader_id, GL.GL_COMPILE_STATUS) != GL.GL_TRUE:
                info = GL.glGetShaderInfoLog(shader_id)

                # raise an error and hard exit
                getLogger().warning(f'Shader compilation failed: {info}')
                getLogger().warning(f'source: {source}')
                os._exit(0)
            return shader_id

        except:
            GL.glDeleteShader(shader_id)
            raise

    @classmethod
    def _register(cls):
        """method to register the shader - not required yet
        """
        pass

    def bind(self):
        """Make self the current shader
        """
        if _DEBUG:
            getLogger().debug(f'{consoleStyle.fg.darkyellow}-->  {self.__class__.__name__}.bind   -   {id(self)}'
                              f'{consoleStyle.reset}')
        self._shader.bind()
        return self

    def release(self):
        """Unbind the current shader
        """
        if _DEBUG:
            getLogger().debug(f'{consoleStyle.fg.darkyellow}-->  {self.__class__.__name__}.release   -   {id(self)}'
                              f'{consoleStyle.reset}')
        self._shader.release()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Common methods
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def getViewportMatrix(left, right, bottom, top, near, far):
        """Set the contents of the viewport matrix
        """
        # return the viewport transformation matrix - mapping screen to NDC (normalised device coordinates)
        #   this is equivalent to - identity-translate-scale
        viewMat = QtGui.QMatrix4x4()
        viewMat.viewport(left, bottom, right - left, top - bottom, near, far)

        return viewMat

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Methods available - Common attributes sizes
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def uniformLocation(self, name):
        """Function to get location of an OpenGL uniform variable

        :param name: String, name of the variable for which location is to be returned
        :return: int; integer describing location
        """
        return GL.glGetUniformLocation(self.program_id, name)

    def attributeLocation(self, name):
        """Function to get location of an OpenGL attribute variable

        :param name: String, name of the variable for which location is to be returned
        :return: int; integer describing location
        """
        return GL.glGetAttribLocation(self.program_id, name)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Implementation
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def define(self, arrayObject):
        """Define the required vertex-array-objects and vertex-buffer-objects needed to buffer data
        to the graphics card.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: function {repr(sys._getframe().f_code.co_name)} not implemented')

    def push(self, arrayObject):
        """Push vertex-buffers to graphics card
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: function {repr(sys._getframe().f_code.co_name)} not implemented')

    def draw(self, arrayObject):
        """Draw the vertex-buffers in array mode. Arrays are drawn from buffers already bound to graphics card memory.
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: function {repr(sys._getframe().f_code.co_name)} not implemented')
