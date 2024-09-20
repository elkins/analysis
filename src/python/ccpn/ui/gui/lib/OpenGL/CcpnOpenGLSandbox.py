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
__dateModified__ = "$dateModified: 2024-01-19 14:47:20 +0000 (Fri, January 19, 2024) $"
__version__ = "$Revision: 3.2.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2018-12-20 13:28:13 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

pass

# fov = math.radians(45.0)
# f = 1.0 / math.tan(fov / 2.0)
# zNear = 0.1
# zFar = 100.0
# aspect = glutGet(GLUT_WINDOW_WIDTH) / float(glutGet(GLUT_WINDOW_HEIGHT))
# aspect = w / float(h)
# perspective
# pMatrix = np.array([
#   f / aspect, 0.0, 0.0, 0.0,
#   0.0, f, 0.0, 0.0,
#   0.0, 0.0, (zFar + zNear) / (zNear - zFar), -1.0,
#   0.0, 0.0, 2.0 * zFar * zNear / (zNear - zFar), 0.0], np.float32)
#
# GL.glViewport(0, 0, self.width(), self.height())
# of = 1.0
# on = -1.0
# oa = 2.0/(self.axisR-self.axisL)
# ob = 2.0/(self.axisT-self.axisB)
# oc = -2.0/(of-on)
# od = -(of+on)/(of-on)
# oe = -(self.axisT+self.axisB)/(self.axisT-self.axisB)
# og = -(self.axisR+self.axisL)/(self.axisR-self.axisL)
# # orthographic
# self._uPMatrix[0:16] = [oa, 0.0, 0.0,  0.0,
#                         0.0,  ob, 0.0,  0.0,
#                         0.0, 0.0,  oc,  0.0,
#                         og, oe, od, 1.0]
#
# # create modelview matrix
# self._uMVMatrix[0:16] = [1.0, 0.0, 0.0, 0.0,
#                         0.0, 1.0, 0.0, 0.0,
#                         0.0, 0.0, 1.0, 0.0,
#                         0.0, 0.0, 0.0, 1.0]
#
# if (self._contourList.renderMode == GLRENDERMODE_REBUILD):
#   self._contourList.renderMode = GLRENDERMODE_DRAW
#
#   # GL.glNewList(self._contourList[0], GL.GL_COMPILE)
#   #
#   # # GL.glUniformMatrix4fv(self.uPMatrix, 1, GL.GL_FALSE, pMatrix)
#   # # GL.glUniformMatrix4fv(self.uMVMatrix, 1, GL.GL_FALSE, mvMatrix)
#   #
#   # GL.glEnable(GL.GL_BLEND)
#   # GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
#   #
#   # # pastel pink - # df2950
#   # GL.glColor4f(0.8745, 0.1608, 0.3137, 1.0)
#   #
#   # GL.glBegin(GL.GL_TRIANGLES)
#
#   step = 0.05
#   ii=0
#   elements = (2.0/step)**2
#   self._contourList.indices = np.zeros(int(elements*6), dtype=np.uint32)
#   self._contourList.vertices = np.zeros(int(elements*12), dtype=np.float32)
#   self._contourList.colors = np.zeros(int(elements*16), dtype=np.float32)
#
#   for x0 in np.arange(-1.0, 1.0, step):
#     for y0 in np.arange(-1.0, 1.0, step):
#       x1 = x0+step
#       y1 = y0+step
#
#       index = ii*4
#       indices = [index, index + 1, index + 2, index, index + 2, index + 3]
#       vertices = [x0, y0, self.mathFun(x0, y0),
#                    x0, y1, self.mathFun(x0, y1),
#                    x1, y1, self.mathFun(x1, y1),
#                    x1, y0, self.mathFun(x1, y0)]
#       # texcoords = [[u0, v0], [u0, v1], [u1, v1], [u1, v0]]
#       colors = [0.8745, 0.1608, 0.3137, 1.0] * 4
#
#       self._contourList.indices[ii * 6:ii * 6 + 6] = indices
#       self._contourList.vertices[ii * 12:ii * 12 + 12] = vertices
#       self._contourList.colors[ii * 16:ii * 16 + 16] = colors
#       ii += 1
#
#       # self._contourList.indices = np.append(self._contourList.indices, indices)
#       # self._contourList.vertices = np.append(self._contourList.vertices, vertices)
#       # self._contourList.colors = np.append(self._contourList.colors, colors)
#
#       # GL.glVertex3f(ii,     jj,     self.mathFun(ii,jj))
#       # GL.glVertex3f(ii+step, jj,     self.mathFun(ii+step, jj))
#       # GL.glVertex3f(ii+step, jj+step, self.mathFun(ii+step, jj+step))
#       #
#       # GL.glVertex3f(ii,     jj,     self.mathFun(ii,jj))
#       # GL.glVertex3f(ii+step, jj+step, self.mathFun(ii+step, jj+step))
#       # GL.glVertex3f(ii,     jj+step, self.mathFun(ii, jj+step))
#   self._contourList.numVertices = index
#   # self._contourList.bindBuffers()
#
#   # GL.glEnd()
#   # GL.glDisable(GL.GL_BLEND)
#   # GL.glEndList()
#
# don't need the above bit
# if self._testSpectrum.renderMode == GLRENDERMODE_DRAW:
#   GL.glUseProgram(self._shaderProgram2.program_id)
#
#   # must be called after glUseProgram
#   # GL.glUniformMatrix4fv(self.uPMatrix, 1, GL.GL_FALSE, self._uPMatrix)
#   # GL.glUniformMatrix4fv(self.uMVMatrix, 1, GL.GL_FALSE, self._uMVMatrix)
#
#   of = 1.0
#   on = -1.0
#   oa = 2.0 / (self.axisR - self.axisL)
#   ob = 2.0 / (self.axisT - self.axisB)
#   oc = -2.0 / (of - on)
#   od = -(of + on) / (of - on)
#   oe = -(self.axisT + self.axisB) / (self.axisT - self.axisB)
#   og = -(self.axisR + self.axisL) / (self.axisR - self.axisL)
#   # orthographic
#   self._uPMatrix[0:16] = [oa, 0.0, 0.0, 0.0,
#                           0.0, ob, 0.0, 0.0,
#                           0.0, 0.0, oc, 0.0,
#                           og, oe, od, 1.0]
#
#   # create modelview matrix
#   self._uMVMatrix[0:16] = [1.0, 0.0, 0.0, 0.0,
#                            0.0, 1.0, 0.0, 0.0,
#                            0.0, 0.0, 1.0, 0.0,
#                            0.0, 0.0, 0.0, 1.0]
#
#   self._shaderProgram2.setPMatrix(self._uPMatrix)
#   self._shaderProgram2.setMVMatrix(self._uMVMatrix)
#
#   self.set2DProjectionFlat()
#   self._testSpectrum.drawIndexArray()
#   # GL.glUseProgram(0)
# #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# self.swapBuffers()
# GLUT.glutSwapBuffers()

# def mathFun(self, aa, bb):
#     return math.sin(5.0 * aa) * math.cos(5.0 * bb ** 2)

# NOTE:ED - experimental stuff below, don't delete
# self._vertexShader1 = """
#     #version 120
#
#     uniform mat4 mvMatrix;
#     uniform mat4 pMatrix;
#
#     // data matrix is column major so dataMatrix[0] is the first 4 elements
#     uniform mat4 dataMatrix;
#
#     varying vec4 FC;
#     uniform vec4 axisScale;
#     attribute vec2 offset;
#
#     void main()
#     {
#       gl_Position = (pMatrix * mvMatrix) * gl_Vertex;
#
#     //  float denom = dataMatrix[0].
#     //  gl_Position = vec4(0.0, 1.0);
#
#     //  gl_Position = (pMatrix * gl_Vertex) + vec4(0.2, 0.3, 0.0, 0.0);
#
#     //  vec4 pos = pMatrix * gl_Vertex;
#     //  gl_Position = vec4(pos.xy, 0.0, 1.0);
#
#       FC = gl_Color;
#     }
#     """
#
# self._fragmentShader1 = """
#     #version 120
#
#     varying vec4  FC;
#     uniform vec4  background;
#     //uniform ivec4 parameterList;
#
#     void main()
#     {
#       gl_FragColor = FC;
#
#     //  if (FC.w < 0.05)
#     //    discard;
#     //  else if (parameterList.x == 0)
#     //    gl_FragColor = FC;
#     //  else
#     //    gl_FragColor = vec4(FC.xyz, 1.0) * FC.w + background * (1-FC.w);
#     }
#     """
#
# # shader for plotting antialiased text to the screen
# self._vertexShaderTex = """
#     #version 120
#
#     uniform mat4 mvTexMatrix;
#     uniform mat4 pMatrix;
#     uniform vec4 axisScale;
#     uniform vec4 viewport;
#     varying vec4 FC;
#     varying vec4 FO;
#     varying vec2 texCoord;
#     attribute vec2 offset;
#
#     void main()
#     {
#       // viewport is scaled to axis
#     //      vec4 pos = pMatrix * (gl_Vertex * axisScale + vec4(offset, 0.0, 0.0));
#                                // character_pos        // world_coord
#
#       // centre on the nearest pixel in NDC - shouldn't be needed but textures not correct yet
#     //      gl_Position = pos;       //vec4( pos.x,        //floor(0.5 + viewport.x*pos.x) / viewport.x,
#                                //pos.y,        //floor(0.5 + viewport.y*pos.y) / viewport.y,
#                                //pos.zw );
#
#       gl_Position = pMatrix * ((gl_Vertex * axisScale) + vec4(offset, 0.0, 0.0));
#
#     //      gl_Position = (pMatrix * vec4(offset, 0.0, 0.0)) + ((pMatrix * gl_Vertex) * axisScale);
#
#       texCoord = gl_MultiTexCoord0.st;
#       FC = gl_Color;
#     }
#     """
#
# self._fragmentShaderTex = """
#     #version 120
#
#     uniform sampler2D texture;
#     varying vec4 FC;
#     vec4    texFilter;
#     uniform vec4 background;
#     uniform int  blendEnabled;
#     varying vec4 FO;
#     varying vec2 texCoord;
#
#     void main()
#     {
#       texFilter = texture2D(texture, texCoord);
#       // colour for blending enabled
#       if (blendEnabled != 0)
#         // multiply the character fade by the color fade to give the actual transparency
#         gl_FragColor = vec4(FC.xyz, FC.w * texFilter.w);
#
#       else
#         // gives a background box around the character, giving a simple border
#         gl_FragColor = vec4((FC.xyz * texFilter.w) + (1 - texFilter.w) * background.xyz, 1.0);
#
#       // if (texFilter.w < 0.01)
#       //   discard;
#       // gl_FragColor = vec4(FC.xyz, texFilter.w);
#     }
#     """
#
# self._fragmentShaderTexNoBlend = """
#     #version 120
#
#     uniform sampler2D texture;
#     varying vec4 FC;
#     vec4    texFilter;
#     uniform vec4 background;
#     uniform uint blendEnabled;
#     varying vec4 FO;
#     varying vec4 texCoord;
#
#     void main()
#     {
#       texFilter = texture2D(texture, texCoord.xy);
#       gl_FragColor = vec4((FC.xyz * texFilter.w) + (1 - texFilter.w) * background.xyz, 1.0);
#     }
#     """
#
# #     # shader for plotting antialiased text to the screen
# #     self._vertexShaderTex = """
# #     #version 120
# #
# #     uniform mat4 mvMatrix;
# #     uniform mat4 pMatrix;
# #     varying vec4 FC;
# #     uniform vec4 axisScale;
# #     attribute vec2 offset;
# #
# #     void main()
# #     {
# #       gl_Position = pMatrix * mvMatrix * (gl_Vertex * axisScale + vec4(offset, 0.0, 0.0));
# #       gl_TexCoord[0] = gl_MultiTexCoord0;
# #       FC = gl_Color;
# #     }
# #     """
# #
# #     self._fragmentShaderTex = """
# # #version 120
# #
# # #ifdef GL_ES
# # precision mediump float;
# # #endif
# #
# # uniform sampler2D texture;
# # varying vec4 FC;
# # vec4    texFilter;
# #
# # varying vec4 v_color;
# # varying vec2 v_texCoord;
# #
# # const float smoothing = 1.0/16.0;
# #
# # void main() {
# #     float distance = texture2D(texture, v_texCoord).a;
# #     float alpha = smoothstep(0.5 - smoothing, 0.5 + smoothing, distance);
# #     gl_FragColor = vec4(v_color.rgb, v_color.a * alpha);
# # }
# # """
#
# # advanced shader for plotting contours
# self._vertexShader2 = """
#     #version 120
#
#     varying vec4  P;
#     varying vec4  C;
#     uniform mat4  mvMatrix;
#     uniform mat4  pMatrix;
#     uniform vec4  positiveContour;
#     uniform vec4  negativeContour;
#     //uniform float gsize = 5.0;      // size of the grid
#     //uniform float gwidth = 1.0;     // grid lines' width in pixels
#     //varying float   f = min(abs(fract(P.z * gsize) - 0.5), 0.2);
#
#     void main()
#     {
#       P = gl_Vertex;
#       C = gl_Color;
#     //  gl_Position = vec4(gl_Vertex.x, gl_Vertex.y, 0.0, 1.0);
#     //  vec4 glVect = pMatrix * mvMatrix * vec4(P, 1.0);
#     //  gl_Position = vec4(glVect.x, glVect.y, 0.0, 1.0);
#       gl_Position = pMatrix * mvMatrix * vec4(P.xy, 0.0, 1.0);
#     }
#     """
#
# self._fragmentShader2 = """
#     #version 120
#
#     //  uniform float gsize = 50.0;       // size of the grid
#     uniform float gwidth = 0.5;       // grid lines' width in pixels
#     uniform float mi = 0.0;           // mi=max(0.0,gwidth-1.0)
#     uniform float ma = 1.0;           // ma=max(1.0,gwidth);
#     varying vec4 P;
#     varying vec4 C;
#
#     void main()
#     {
#     //  vec3 f  = abs(fract (P * gsize)-0.5);
#     //  vec3 df = fwidth(P * gsize);
#     //  float mi=max(0.0,gwidth-1.0), ma=max(1.0,gwidth);//should be uniforms
#     //  vec3 g=clamp((f-df*mi)/(df*(ma-mi)),max(0.0,1.0-gwidth),1.0);//max(0.0,1.0-gwidth) should also be sent as uniform
#     //  float c = g.x * g.y * g.z;
#     //  gl_FragColor = vec4(c, c, c, 1.0);
#     //  gl_FragColor = gl_FragColor * gl_Color;
#
#       float   f = min(abs(fract(P.z)-0.5), 0.2);
#       float   df = fwidth(P.z);
#     //  float   mi=max(0.0,gwidth-1.0), ma=max(1.0,gwidth);                 //  should be uniforms
#       float   g=clamp((f-df*mi)/(df*(ma-mi)),max(0.0,1.0-gwidth),1.0);      //  max(0.0,1.0-gwidth) should also be sent as uniform
#     //  float   g=clamp((f-df*mi), 0.0, df*(ma-mi));  //  max(0.0,1.0-gwidth) should also be sent as uniform
#
#     //  g = g/(df*(ma-mi));
#     //  float   cAlpha = 1.0-(g*g);
#     //  if (cAlpha < 0.25)            //  this actually causes branches in the shader - bad
#     //    discard;
#     //  gl_FragColor = vec4(0.8-g, 0.3, 0.4-g, 1.0-(g*g));
#       gl_FragColor = vec4(P.w, P.w, P.w, 1.0-(g*g));
#     }
#     """
#
# self._vertexShader3 = """
#     #version 120
#
#     uniform mat4 u_projTrans;
#
#     attribute vec4 a_position;
#     attribute vec2 a_texCoord0;
#     attribute vec4 a_color;
#
#     varying vec4 v_color;
#     varying vec2 v_texCoord;
#
#     void main() {
#       gl_Position = u_projTrans * a_position;
#       v_texCoord = a_texCoord0;
#       v_color = a_color;
#     }
#     """
#
# self._fragmentShader3 = """
#     #version 120
#
#     #ifdef GL_ES
#     precision mediump float;
#     #endif
#
#     uniform sampler2D u_texture;
#
#     varying vec4 v_color;
#     varying vec2 v_texCoord;
#
#     const float smoothing = 1.0/16.0;
#
#     void main() {
#       float distance = texture2D(u_texture, v_texCoord).a;
#       float alpha = smoothstep(0.5 - smoothing, 0.5 + smoothing, distance);
#       gl_FragColor = vec4(v_color.rgb, v_color.a * alpha);
#     }
#     """
