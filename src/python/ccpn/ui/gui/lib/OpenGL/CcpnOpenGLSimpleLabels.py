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
__dateModified__ = "$dateModified: 2023-12-14 15:20:38 +0000 (Thu, December 14, 2023) $"
__version__ = "$Revision: 3.2.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-01-23 15:34:14 +0000 (Thu, January 23, 2020) $"

#=========================================================================================
# Start of code
#=========================================================================================

import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.util.Colour import hexToRgbRatio, colorSchemeTable, ERRORCOLOUR
from ccpn.util.Logging import getLogger

from . import GL

from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLFonts import GLString
import ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs as GLDefs
from ccpn.core.lib.AxisCodeLib import getAxisCodeMatchIndices


class GLSimpleStrings():
    """
    Class to handle grouped labels with an optional infinite line if required
    Labels can be locked to screen co-ordinates or top/bottom, left/right justified
    """

    def __init__(self, parent=None, strip=None, name=None, resizeGL=False,
                 blendMode=False, drawMode=GL.GL_LINES, dimension=2):
        """Initialise the class
        """
        self._GLParent = parent
        self.strip = strip
        self.name = name
        self.resizeGL = resizeGL
        self.axisCodes = self.strip.axisCodes
        self.current = self.strip.current if self.strip else None

        self.strings = {}

    def buildStrings(self):
        for spectrumView in self._GLParent._ordering:  # strip.spectrumViews:

            if spectrumView.isDeleted:
                continue

            if spectrumView not in self.strings:

                _posColours = (ERRORCOLOUR,)
                _posCol = spectrumView.spectrum.sliceColour
                if _posCol and _posCol.startswith('#'):
                    _posColours = (_posCol,)
                elif _posCol in colorSchemeTable:
                    _posColours = colorSchemeTable[_posCol]

                self.addString(spectrumView, (0, 0), colour=_posColours[0], alpha=1.0,
                               lock=GLDefs.LOCKAXIS | GLDefs.LOCKLEFT | GLDefs.LOCKBOTTOM, axisCodes=('intensity',))

    def drawStrings(self):
        if self.strip.isDeleted:
            return

        self.buildStrings()

        # iterate over and draw all strings for visible spectrumViews
        for specView, string in self.strings.items():
            if specView in self._GLParent._visibleOrdering and string.stringObject and not string.stringObject.isDeleted:
                string.drawTextArrayVBO()

    def objectText(self, obj):
        """return the string to be used for the label
        To be subclassed as required
        """
        return str(obj.spectrum.id)

    def objectInstance(self, obj):
        """return the object instance to insert into the string
        To be subclassed as required
        """
        return obj.spectrum

    def objectSettings(self, string, obj):
        """Set up class specific settings for the new string
        To be subclassed as required
        """
        string.spectrumView = obj
        if string.axisCodes:
            string.axisIndices = getAxisCodeMatchIndices(string.axisCodes, self.axisCodes)

    def addString(self, obj, position=(0, 0), axisCodes=None, colour="#FF0000", alpha=1.0,
                  lock=GLDefs.LOCKNONE, serial=0):
        """Add a new string to the list
        """
        GLp = self._GLParent
        col = hexToRgbRatio(colour)

        # NOTE:ED check axis units - assume 'ppm' for the minute

        # fixed ppm position - rescale will do the rest
        textX = position[0]
        textY = position[1]

        # create new label, should be ready to draw
        newLabel = GLString(text=self.objectText(obj),
                            font=GLp.getSmallFont(),  #.globalGL.glSmallFont,
                            x=textX,
                            y=textY,
                            colour=(*col, alpha),
                            GLContext=GLp,
                            obj=self.objectInstance(obj),
                            serial=serial)
        newLabel.position = position
        newLabel.axisCodes = axisCodes
        newLabel.lock = lock

        # set up class specific settings, to be subclassed as required
        self.objectSettings(newLabel, obj)

        # shouldn't be necessary but here for completeness
        self._rescaleString(newLabel)

        # assume objects are only used once, will replace a previous object
        self.strings[obj] = newLabel

        # return the new created GLstring
        return newLabel

    def renameString(self, obj):
        """Rename a string in the list, if it exists
        """
        strings = [(specView, string) for specView, string in self.strings.items() if string.stringObject is obj]

        for specView, string in strings:
            string.text = self.objectText(specView)
            string.buildString()
            self._rescaleString(string)

    def removeString(self, obj):
        """Remove a string from the list, if it exists
        """
        if obj in self.strings:
            del self.strings[obj]

    def _rescaleString(self, obj):
        vertices = obj.numVertices

        if vertices:
            # check the lock type to determine how to rescale

            lock = obj.lock
            GLp = self._GLParent
            position = list(obj.position)

            # move the axes to account for the stacking
            if self._GLParent._stackingMode:
                if obj.spectrumView not in GLp._spectrumSettings:
                    return

                _, position[1] = GLp._spectrumSettings[obj.spectrumView].stackedMatrixOffset

            if lock == GLDefs.LOCKNONE:

                # lock to the correct axisCodes if exist - not tested yet
                if obj.axisIndices[0] and obj.axisIndices[1]:
                    offsets = [position[obj.axisIndices[0]],
                               position[obj.axisIndices[1]],
                               0.0, 0.0]

                else:
                    offsets = [position[0],
                               position[1],
                               0.0, 0.0]

            elif lock == GLDefs.LOCKSCREEN:

                # fixed screen co-ordinates
                offsets = [GLp.axisL + position[0] * GLp.pixelX,
                           GLp.axisB + position[1] * GLp.pixelY,
                           0.0, 0.0]

            # not locking to an axisCode
            elif lock == GLDefs.LOCKLEFT:

                # lock to the left margin
                offsets = [GLp.axisL + 3.0 * GLp.pixelX,
                           position[1],
                           0.0, 0.0]

            elif lock == GLDefs.LOCKRIGHT:

                # lock to the right margin
                offsets = [GLp.axisR - (3.0 + obj.width) * GLp.pixelX,
                           position[1],
                           0.0, 0.0]

            elif lock == GLDefs.LOCKBOTTOM:

                # lock to the bottom margin - updated in resize
                offsets = [position[0],
                           GLp.axisB + 3.0 * GLp.pixelY,
                           0.0, 0.0]

            elif lock == GLDefs.LOCKTOP:

                # lock to the top margin - updated in resize
                offsets = [position[0],
                           GLp.axisT - (3.0 + obj.height) * GLp.pixelY,
                           0.0, 0.0]

            elif lock & GLDefs.LOCKAXIS:

                # locking to a named axisCodes
                if len(obj.axisIndices) == 1:

                    # match to a single axisCode
                    if obj.axisIndices[0] == 1:

                        if lock & GLDefs.LOCKRIGHT:

                            # lock to the right margin
                            offsets = [GLp.axisR - (3.0 + obj.width) * GLp.pixelX,
                                       position[1],
                                       0.0, 0.0]

                        else:

                            # lock to the left margin
                            offsets = [GLp.axisL + 3.0 * GLp.pixelX,
                                       position[1],
                                       0.0, 0.0]

                    elif obj.axisIndices[0] == 0:

                        if lock & GLDefs.LOCKTOP:

                            # lock to the top margin - updated in resize
                            offsets = [position[0],
                                       GLp.axisT - (3.0 + obj.height) * GLp.pixelY,
                                       0.0, 0.0]

                        else:

                            # lock to the bottom margin - updated in resize
                            offsets = [position[0],
                                       GLp.axisB + 3.0 * GLp.pixelY,
                                       0.0, 0.0]

                else:
                    # can't match more than 1
                    return

            else:
                return

            # for pp in range(0, 2 * vertices, 2):
            #     obj.attribs[pp:pp + 2] = offsets
            obj.attribs[:] = offsets * vertices

            # redefine the string's position VBOs
            obj.pushTextArrayVBOAttribs()

            try:
                _posColours = (ERRORCOLOUR,)
                _posCol = obj.spectrumView.spectrum.sliceColour
                if _posCol and _posCol.startswith('#'):
                    _posColours = (_posCol,)
                elif _posCol in colorSchemeTable:
                    _posColours = colorSchemeTable[_posCol]

                # reset the colour, may have changed due to spectrum colour change, but not caught anywhere else yet
                obj.setStringHexColour(_posColours[0], alpha=1.0)

                # redefine the string's colour VBOs
                obj.pushTextArrayVBOColour()

            except Exception as es:
                getLogger().warning('error setting string colour')

    def rescale(self):
        """rescale the objects
        """
        for string in self.strings.values():
            self._rescaleString(string)


class GLSimpleLegend(GLSimpleStrings):
    """
    Class to handle drawing the legend to the screen
    """

    def buildStrings(self):
        for spectrumView in self._GLParent._ordering:  # strip.spectrumViews:

            if spectrumView.isDeleted:
                continue

            if spectrumView not in self.strings:

                _posColours = (ERRORCOLOUR,)
                _posCol = spectrumView.spectrum.sliceColour
                if _posCol and _posCol.startswith('#'):
                    _posColours = (_posCol,)
                elif _posCol in colorSchemeTable:
                    _posColours = colorSchemeTable[_posCol]

                self.addString(spectrumView, (0, 0), colour=_posColours[0], alpha=1.0)

    def drawStrings(self):
        if self.strip.isDeleted:
            return

        self.buildStrings()

        # iterate over and draw all strings for visible spectrumViews
        for specView, string in self.strings.items():
            if specView in self._GLParent._visibleOrdering and string.stringObject and not string.stringObject.isDeleted:
                string.drawTextArrayVBO()

    def objectText(self, obj):
        """return the string to be used for the label
        To be subclassed as required
        """
        return str(obj.id)

    def objectInstance(self, obj):
        """return the object instance to insert into the string
        To be subclassed as required
        """
        return obj

    def objectSettings(self, string, obj):
        """Set up class specific settings for the new string
        To be subclassed as required
        """
        string.spectrum = obj

    def addString(self, obj, position=(0, 0), axisCodes=None, colour="#FF0000", alpha=1.0,
                  lock=GLDefs.LOCKNONE, serial=0):
        """Add a new string to the list
        """
        GLp = self._GLParent
        col = hexToRgbRatio(colour)

        # fixed ppm position - rescale will do the rest
        textX = position[0]
        textY = position[1]

        # create new label, should be ready to draw
        newLabel = GLString(text=self.objectText(obj),
                            font=GLp.getSmallFont(),  #.globalGL.glSmallFont,
                            x=textX,
                            y=textY,
                            colour=(*col, alpha),
                            GLContext=GLp,
                            obj=self.objectInstance(obj),
                            serial=serial)
        newLabel.position = position
        newLabel.axisCodes = axisCodes
        newLabel.lock = lock

        # set up class specific settings, to be subclassed as required
        self.objectSettings(newLabel, obj)

        # shouldn't be necessary but here for completeness
        self._rescaleString(newLabel)

        # assume objects are only used once, will replace a previous object
        self.strings[obj] = newLabel

        # return the new created GLstring
        return newLabel

    def _rescaleString(self, stringObj):
        vertices = stringObj.numVertices

        if vertices:

            GLp = self._GLParent
            position = list(stringObj.position)

            # fixed screen co-ordinates from top-left
            offsets = [GLp.axisL + position[0] * GLp.pixelX,
                       GLp.axisB + position[1] * GLp.pixelY,
                       0.0, 0.0]

            # for pp in range(0, 2 * vertices, 2):
            #     stringObj.attribs[pp:pp + 2] = offsets
            stringObj.attribs[:] = offsets * vertices

            # redefine the string's position VBOs
            stringObj.pushTextArrayVBOAttribs()

            try:
                _posColours = (ERRORCOLOUR,)
                _posCol = stringObj.stringObject.sliceColour
                if _posCol and _posCol.startswith('#'):
                    _posColours = (_posCol,)
                elif _posCol in colorSchemeTable:
                    _posColours = colorSchemeTable[_posCol]

                # reset the colour, may have changed due to spectrum colour change, but not caught anywhere else yet
                stringObj.setStringHexColour(_posColours[0], alpha=1.0)

                # redefine the string's colour VBOs
                stringObj.pushTextArrayVBOColour()

            except Exception as es:
                getLogger().warning('error setting legend string colour')

    def rescale(self):
        """rescale the objects
        """
        for string in self.strings.values():
            self._rescaleString(string)
