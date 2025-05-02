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
__date__ = "$Date: 2018-12-20 14:07:55 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

from imageio.v3 import imread
import numpy as np
import math
from dataclasses import dataclass, field
from collections import namedtuple
from ccpn.core.lib.WeakRefLib import WeakRefDescriptor, _WeakRefDataClassMeta
from ccpn.ui.gui.lib.OpenGL import GL
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLArrays import GLVertexArray, GLRENDERMODE_DRAW
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import LEFTBORDER, RIGHTBORDER, TOPBORDER, BOTTOMBORDER
from ccpn.util.Colour import hexToRgbRatio


FONT_FILE = 0
FULL_FONT_NAME = 1

GLGlyphTuple = namedtuple('GLGlyphTuple', 'xPos yPos width height xOffset yOffset origW origH kerns '
                                          'TX0 TY0 TX1 TY1 PX0 PY0 PX1 PY1')


@dataclass
class GlyphData(metaclass=_WeakRefDataClassMeta):
    """
    Small class to store glyph data per font.

    :param parent: Weak reference to the parent object.
    :type parent: WeakRefDescriptor
    :param fontName: Name of the font.
    :type fontName: str
    :param fontSize: Size of the font.
    :type fontSize: int
    :param glyphs: List of glyphs, defaulting to a list of 256 None values.
    :type glyphs: list[GLGlyphTuple | None]
    :param width: Width of the glyph.
    :type width: int
    :param height: Height of the glyph.
    :type height: int
    :param spaceWidth: Width of the space character.
    :type spaceWidth: int
    :param charWidth: Width of the character.
    :type charWidth: int
    :param charHeight: Height of the character.
    :type charHeight: int
    :param base: Base value for the glyph.
    :type base: int
    :param _unscaled: Tuple containing unscaled glyph parameters.
    :type _unscaled: tuple[int, ...]
    :param fontTransparency: Transparency of the font, defaulting to 0.0.
    :type fontTransparency: float
    """

    parent: WeakRefDescriptor = field(default_factory=WeakRefDescriptor)
    fontName: str = None
    fontSize: int = 0
    glyphs: list[GLGlyphTuple | None] = field(default_factory=lambda: [None] * 256)
    width: int = 0
    height: int = 0
    spaceWidth: int = 0
    charWidth: int = 0
    charHeight: int = 0
    base: int = 0
    _unscaled: tuple[int, ...] = None
    # scale_width: int = 0
    # scale_height: int = 0
    # scale_charWidth: int = 0
    # scale_charHeight: int = 0
    # scale_base: int = 0
    # scale_spaceWidth: int = 0
    fontTransparency: float = field(default=0.0)

    def updateFromScale(self, scale: int):
        """
        Update glyph parameters based on the given scale.

        :param scale: Scale to apply to the glyph parameters.
        :type scale: int
        :raises RuntimeError: If _unscaled parameters are undefined.
        """
        # HACK:ED - don't like this much :|
        if not self._unscaled:
            raise RuntimeError('Parameters are undefined')
        # devicePixelRatio uses a font that is twice the size for the high-res display
        gw, gh, tx, ty, base = self._unscaled
        self.width = gw // scale
        self.height = gh // scale
        self.charWidth = tx // scale
        self.charHeight = ty // scale
        self.base = base // scale

    def setGlyphSize(self, width: int, height: int, charWidth: int, charHeight: int, base: int):
        """
        Set the main glyph parameters.

        :param width: Width of the glyph.
        :type width: int
        :param height: Height of the glyph.
        :type height: int
        :param charWidth: Width of the character.
        :type charWidth: int
        :param charHeight: Height of the character.
        :type charHeight: int
        :param base: Base value for the glyph.
        :type base: int
        """
        self.width = width
        self.height = height
        self.charWidth = charWidth
        self.charHeight = charHeight
        self.base = base
        self._unscaled = width, height, charWidth, charHeight, base  # might be redundant now :)
        self.updateFromScale(1)

    def setGlyph(self, num: int, value: GLGlyphTuple):
        """
        Set the glyph tuple at the specified index with validation.

        :param num: Index of the glyph (must be between 0 and 255).
        :type num: int
        :param value: Glyph value (must be of type GLGlyphTuple).
        :type value: GLGlyphTuple
        :raises ValueError: If num is not between 0 and 255 or value is not a GLGlyphTuple.
        """
        if not (0 <= num <= 255):
            raise ValueError("num must be between 0 and 255")
        if not isinstance(value, GLGlyphTuple):
            raise ValueError("value must be of type GLGlyphTuple")
        self.glyphs[num] = value

    @property
    def textureId(self) -> int:
        """
        Return the texture ID defined by the current parent.

        :raises RuntimeError: If the parent is not defined.
        :return: The texture ID from the parent.
        :rtype: int
        """
        parent = self.parent
        if parent:
            return parent.textureId
        raise RuntimeError('textureId: parent is not defined')


#=========================================================================================
# CcpnGLFont
#=========================================================================================

class CcpnGLFont:
    def __init__(self, fileName=None, base=0, fontTransparency=None, activeTexture=0, scale=None):
        self.fontName = None
        self.fontGlyph = {}  #[None] * 256
        self.base = base
        self.scale = scale

        if scale is None:
            raise ValueError(f'scale must be defined for font {fileName} ')
        with open(fileName, 'r') as op:
            self.fontInfo = op.read().split('\n')

        # no checking yet
        self.fontFile = self.fontInfo[FONT_FILE].replace('textures: ', '')
        self.fontPNG = imread(fileName.filepath / self.fontFile)
        self._fontArray = np.array(self.fontPNG * (fontTransparency if fontTransparency is not None else 1.0),
                                   dtype=np.uint8)[:, :, 3]

        fontRows = []
        fontID = ()

        for ii, row in enumerate(self.fontInfo):
            if ii and row and row[0].isalpha():
                # assume that this is a font name
                if not row.startswith('kerning'):
                    fontID = (ii, row)
                else:
                    fontID += (ii,)
                    fontRows.append(fontID)
        fontRows.append((len(self.fontInfo) - 1, None, None))

        for _font, _nextFont in zip(fontRows, fontRows[1:]):
            _startRow, _fontName, _kerningRow = _font
            _nextRow = _nextFont[0]

            self._buildFont(_fontName, _startRow, _kerningRow, _nextRow, scale, fontTransparency)

        _foundFonts = [glyph.fontName for glyph in self.fontGlyph.values()]
        if len(set(_foundFonts)) != 1:
            raise RuntimeError('font file should only contain a single font type')
        self.fontName = _foundFonts[0]

        self.activeTexture = GL.GL_TEXTURE0 + activeTexture
        self.activeTextureNum = activeTexture

        # self._bindFontTexture  # causing threading error on Windows?

    def _bindFontTexture(self):
        """Bind the texture to font
        MUST be called inside GL current context, i.e., after GL.makeCurrent or inside initializeGL, paintGL
        """
        self.textureId = GL.glGenTextures(1)
        # GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glActiveTexture(self.activeTexture)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.textureId)

        # need to map ALPHA-ALPHA and use the alpha channel (.a) in the shader
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_ALPHA,
                        self._fontArray.shape[1], self._fontArray.shape[0],
                        0,
                        GL.GL_ALPHA, GL.GL_UNSIGNED_BYTE, self._fontArray)

        # nearest is the quickest gl plotting and gives a slightly brighter image
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)

        # # the following 3 lines generate a multi-texture mipmap - shouldn't need here
        # GL.glTexParameteri( GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR_MIPMAP_NEAREST )
        # GL.glTexParameteri( GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST )
        # GL.glGenerateMipmap( GL.GL_TEXTURE_2D )
        GL.glDisable(GL.GL_TEXTURE_2D)

    def _buildFont(self, _fontID, _startRow, _kerningRow, _nextRow, scale, fontTransparency):

        fullFontNameString = _fontID
        fontSizeString = fullFontNameString.split()[-1]

        _fontSize = int(int(fontSizeString.replace('pt', '')) / scale)
        _glyphs = self.fontGlyph[_fontSize] = GlyphData(parent=self,
                                                        fontName=fullFontNameString.replace(fontSizeString, '').strip(),
                                                        fontSize=_fontSize,
                                                        fontTransparency=fontTransparency)

        # texture sizes
        dx = 1.0 / float(self.fontPNG.shape[1])
        dy = 1.0 / float(self.fontPNG.shape[0])

        for row in range(_startRow + 1, _kerningRow):
            line = self.fontInfo[row]

            lineVals = [int(ll) for ll in line.split()]
            if len(lineVals) == 9:
                chrNum, x, y, tx, ty, px, py, gw, gh = lineVals

                # only keep the ascii chars
                if chrNum < 256:
                    w = tx + LEFTBORDER + RIGHTBORDER
                    h = ty + TOPBORDER + BOTTOMBORDER
                    _kerns = [0] * 256
                    _glyphs.setGlyph(chrNum, GLGlyphTuple(x, y, tx, ty, px, py, gw, gh, _kerns,
                                                          # coordinates in the texture
                                                          x * dx,
                                                          (y + h) * dy,
                                                          (x + w) * dx,
                                                          y * dy,
                                                          # coordinates mapped to the quad
                                                          px,
                                                          gh - (py + h),
                                                          px + (w),
                                                          gh - py
                                                          ))
                    if chrNum == 32:
                        # store the width of the space character
                        _glyphs.spaceWidth = gw
                    elif chrNum == 71:  # A = 65, G = 71
                        # use 'G' for the referencing the tab size
                        _glyphs.setGlyphSize(gw, gh, tx, ty, base=gh - ty - py)

        # fill the kerning lists
        for row in range(_kerningRow + 1, _nextRow):
            line = self.fontInfo[row]

            lineVals = [int(float(ll)) for ll in line.split()]
            chrNum, chrNext, val = lineVals

            # set the kerning for valid values
            if (32 < chrNum < 256) and (32 < chrNext < 256):
                _glyphs.glyphs[chrNum].kerns[chrNext] = val

    @staticmethod
    def get_kerning(fromChar, prevChar, glyphs):
        """Get the kerning required between the characters
        """
        return _glyph.kerns[ord(prevChar)] if (_glyph := glyphs[ord(fromChar)]) else 0

    def __str__(self):
        """Information string for the font
        """
        string = super().__str__()
        _fontSizes = [','.join(_glyph.fontSize for _glyph in self.fontGlyph.values())]
        string = f'{string}; name = {self.fontName}; size = {_fontSizes}; file = {self.fontFile}'
        return string

    def closestFont(self, size):
        """Get the closest font to the required size
        """
        _size = min(list(self.fontGlyph.keys()), key=lambda x: abs(x - size))
        return self.fontGlyph[_size]


#=========================================================================================
# GLString
#=========================================================================================

class GLString(GLVertexArray):
    def __init__(self, text=None, font=None, obj=None, colour=(1.0, 1.0, 1.0, 1.0),
                 x=0.0, y=0.0,
                 ox=0.0, oy=0.0,
                 angle=0.0, width=None, height=None,
                 GLContext=None, blendMode=True,
                 clearArrays=False, serial=None, pixelScale=None,
                 alias=0):
        """
        Create a GLString object for drawing text to the GL window
        :param text:
        :param font:
        :param obj:
        :param colour:
        :param x:
        :param y:
        :param ox:
        :param oy:
        :param angle: angle in degrees, negative is anti-clockwise
        :param width:
        :param height:
        :param GLContext:
        :param blendMode:
        :param clearArrays:
        :param serial:
        :param pixelScale:
        """
        super().__init__(renderMode=GLRENDERMODE_DRAW, blendMode=blendMode,
                         GLContext=GLContext, drawMode=GL.GL_TRIANGLES,
                         dimension=4, clearArrays=clearArrays)
        if text is None:
            text = ''
        self.text = text
        self.font = font
        self.stringObject = obj
        # self.pid = obj.pid if hasattr(obj, 'pid') else None
        self.serial = serial
        self.colour = colour
        self._position = (x, y)
        self._offset = (ox, oy)
        self._angle = (3.1415926535 / 180) * angle
        self._scale = round(pixelScale or GLContext.viewports.devicePixelRatio) or 1
        # add scale here to render from a larger font?      may need different offsets
        #                                                   also need to modify getSmallFont
        self._alias = alias
        self.buildString()

    def buildString(self):
        """Build the string
        """
        text = self.text
        font = self.font
        colour = self.colour
        x, y = self._position
        ox, oy = self._offset
        # self.pid = self.stringObject.pid if hasattr(self.stringObject, 'pid') else None

        _glyphs = font.glyphs
        self.height = font.height
        self.width = 0

        _validText = [tt for tt in text if _glyphs[ord(tt)] and ord(tt) > 32]
        lenText = len(_validText)

        # allocate space for all the letters, bad are discarded, spaces/tabs are not stored
        self.indices = np.empty(lenText * 6, dtype=np.uint32)
        self.vertices = np.zeros(lenText * 16, dtype=np.float32)
        self.texcoords = np.empty(lenText * 8, dtype=np.float32)

        self.indexOffset = 0
        penX = 0
        penY = 0  # offset the string from (0, 0) and use (x, y) in shader
        prev = None

        if self._angle != 0.0:
            cs, sn = math.cos(self._angle), math.sin(self._angle)
        else:
            cs, sn = 1.0, 0.0
        # rotate = np.matrix([[cs, sn], [-sn, cs]])

        i = 0
        for charCode in text:
            c = ord(charCode)
            glyph = _glyphs[c]

            if not glyph and c not in [9, 10, 32]:
                # discard characters that are undefined
                continue

            if (c > 32):  # visible characters

                kerning = font.parent.get_kerning(charCode, prev, _glyphs) if (prev and ord(prev) > 32) else 0

                x0 = penX + glyph.PX0 + kerning
                y0 = penY + glyph.PY0
                x1 = penX + glyph.PX1 + kerning
                y1 = penY + glyph.PY1
                u0 = glyph.TX0
                v0 = glyph.TY0
                u1 = glyph.TX1
                v1 = glyph.TY1
                i4 = i * 4
                i6 = i * 6
                i8 = i * 8
                i16 = i * 16

                if self._angle == 0.0:
                    # horizontal text
                    self.vertices[i16:i16 + 16] = (x0, y0, self._alias, 0.0,
                                                   x0, y1, self._alias, 0.0,
                                                   x1, y1, self._alias, 0.0,
                                                   x1, y0, self._alias, 0.0,
                                                   )  # pixel coordinates in string
                else:
                    # apply rotation to the text
                    xbl, ybl = x0 * cs + y0 * sn, -x0 * sn + y0 * cs
                    xtl, ytl = x0 * cs + y1 * sn, -x0 * sn + y1 * cs
                    xtr, ytr = x1 * cs + y1 * sn, -x1 * sn + y1 * cs
                    xbr, ybr = x1 * cs + y0 * sn, -x1 * sn + y0 * cs

                    self.vertices[i16:i16 + 16] = (xbl, ybl, self._alias, 0.0,
                                                   xtl, ytl, self._alias, 0.0,
                                                   xtr, ytr, self._alias, 0.0,
                                                   xbr, ybr, self._alias, 0.0,
                                                   )  # pixel coordinates in string

                self.indices[i6:i6 + 6] = (i4, i4 + 1, i4 + 2, i4, i4 + 2, i4 + 3)
                self.texcoords[i8:i8 + 8] = (u0, v0, u0, v1, u1, v1, u1, v0)

                # # store the attribs and offsets
                # self.attribs[i * 4:i * 4 + 4] = attribs
                # self.offsets[i * 4:i * 4 + 4] = offsets

                penX += glyph.origW + kerning
                i += 1

            elif (c == 32):  # space
                penX += font.spaceWidth

            elif (c == 10):  # newline
                penX = 0
                penY = 0  # penY + font.height
                # for vt in self.vertices:
                #   vt[1] = vt[1] + font.height

                # move all characters up by font height, centred bottom-left
                self.vertices[1::4] += font.height * self._scale  # rebuilt when changing devicePixelRatio :|
                self.height += font.height * self._scale

            elif (c == 9):  # tab
                penX += 4 * font.spaceWidth

            self.width = max(self.width, penX)

            # penY = penY + glyph[GlyphHeight]
            prev = charCode

        # apply font scaling for hi-res displays - shader will do this soon
        self.vertices[::4] /= self._scale
        self.vertices[1::4] /= self._scale
        self.height /= self._scale
        self.width /= self._scale

        # set the offsets for the characters to the desired coordinates
        self.numVertices = len(self.vertices) // 4
        self.attribs = np.array((x + ox, y + oy, 0.0, 0.0) * self.numVertices, dtype=np.float32)
        self.offsets = np.array((x, y, 0.0, 0.0) * self.numVertices, dtype=np.float32)
        self.stringOffset = None  # (ox, oy)

        # set the colour for the whole string
        self.colors = np.array(colour * self.numVertices, dtype=np.float32)

        # create VBOs from the arrays
        self.defineTextArrayVBO()

        # total width of text - probably don't need
        # width = penX - glyph.advance[0] / 64.0 + glyph.size[0]

    def drawTextArrayImmediate(self):
        """Draw text array with textures
        MUST be called inside GL current context, i.e., after GL.makeCurrent or inside initializeGL, paintGL
        """
        super().drawTextArrayImmediate()

    def drawTextArrayVBO(self, enableClientState=False, disableClientState=False):
        """Draw text array with textures and VBO
        MUST be called inside GL current context, i.e., after GL.makeCurrent or inside initializeGL, paintGL
        """
        super().drawTextArrayVBO()

    def setStringColour(self, col):
        self.colour = col
        self.colors = np.array(self.colour * self.numVertices, dtype=np.float32)

    def setStringHexColour(self, hexColour, alpha=1.0):
        col = hexToRgbRatio(hexColour)
        self.colour = (*col, alpha)
        self.colors = np.array(self.colour * self.numVertices, dtype=np.float32)

    def setStringOffset(self, attrib):
        for pp in range(0, self.attribs.shape[0], 4):
            self.attribs[pp:pp + 2] = self.offsets[pp:pp + 2] + attrib
