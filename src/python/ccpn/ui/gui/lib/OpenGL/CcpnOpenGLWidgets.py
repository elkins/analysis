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
__dateModified__ = "$dateModified: 2024-07-23 15:05:05 +0100 (Tue, July 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2018-12-20 13:28:13 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

import traceback
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal
from ccpn.util.Logging import getLogger
import numpy as np
from ccpn.core.Integral import Integral
from ccpn.ui.gui.lib.OpenGL import GL
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLNotifier import GLNotifier
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import GLREGIONTYPE, GLLINETYPE
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLArrays import GLRENDERMODE_REBUILD, GLRENDERMODE_DRAW, GLVertexArray
from ccpn.ui.gui.guiSettings import CCPNGLWIDGET_REGIONSHADE, CCPNGLWIDGET_INTEGRALSHADE


REGION_COLOURS = {
    'green'      : (0, 1.0, 0.1, CCPNGLWIDGET_REGIONSHADE),
    'yellow'     : (0.9, 1.0, 0.05, CCPNGLWIDGET_REGIONSHADE),
    'blue'       : (0.2, 0.1, 1.0, CCPNGLWIDGET_REGIONSHADE),
    'transparent': (1.0, 1.0, 1.0, 0.01),
    'grey'       : (1.0, 1.0, 1.0, CCPNGLWIDGET_REGIONSHADE),
    'red'        : (1.0, 0.1, 0.2, CCPNGLWIDGET_REGIONSHADE),
    'purple'     : (0.7, 0.4, 1.0, CCPNGLWIDGET_REGIONSHADE),
    None         : (0.2, 0.1, 1.0, CCPNGLWIDGET_REGIONSHADE),
    'highlight'  : (0.5, 0.5, 0.5, CCPNGLWIDGET_REGIONSHADE)
    }


#=========================================================================================
# GLRegion
#=========================================================================================

class GLRegion(QtWidgets.QWidget):
    valuesChanged = pyqtSignal(list)
    editingFinished = pyqtSignal(dict)

    def __init__(self, parent, glList, values=(0, 0), axisCode=None, orientation='h',
                 brush=None, colour='blue',
                 movable=True, visible=True, bounds=None,
                 obj=None, objectView=None, lineStyle='dashed', lineWidth=1.0,
                 regionType=GLREGIONTYPE):

        super().__init__(parent)

        self._parent = parent
        self._glList = glList
        self._values = values
        self._axisCode = axisCode
        self._orientation = orientation
        self._brush = brush
        self._colour = colour
        self.movable = movable
        self._visible = visible
        self._bounds = bounds
        self._object = obj
        self._objectView = objectView
        self._lineStyle = lineStyle
        self._lineWidth = lineWidth
        self.regionType = regionType
        self.pid = obj.pid if hasattr(obj, 'pid') else None
        # create a notifier for updating
        self.GLSignals = GLNotifier(parent=None)
        self._valuesChangedEnabled = True

    def setVisible(self, value):
        self.visible = value

    @property
    def values(self):
        return list(self._values)

    @values.setter
    def values(self, values):
        from ccpn.core.lib.ContextManagers import notificationEchoBlocking, undoStackBlocking

        # with notificationBlanking():
        self._values = tuple(values)
        if self._glList:
            self._glList.renderMode = GLRENDERMODE_REBUILD
        if self._valuesChangedEnabled:
            self.valuesChanged.emit(list(values))

        # change the limits in the integral object
        # with notificationBlanking():
        if self._object and not self._object.isDeleted:
            with notificationEchoBlocking():
                with undoStackBlocking():
                    self._object.limits = [(min(values), max(values))]

        # emit notifiers to repaint the GL windows
        self.GLSignals.emitPaintEvent()

    def setValue(self, val, emitValuesChanged=True):
        # use the region to simulate an infinite line - calls setter above
        oldValue = self._valuesChangedEnabled
        self._valuesChangedEnabled = emitValuesChanged
        self.values = val  # (val, val)  NOTE:ED - why tuple?
        self._valuesChangedEnabled = oldValue

    @property
    def axisCode(self):
        return self._axisCode

    @axisCode.setter
    def axisCode(self, axisCode):
        self._axisCode = axisCode
        if self._glList:
            self._glList.renderMode = GLRENDERMODE_REBUILD
        # emit notifiers to repaint the GL windows
        self.GLSignals.emitPaintEvent()

    @property
    def orientation(self):
        return self._orientation

    @orientation.setter
    def orientation(self, value):
        self._orientation = value
        if value == 'h':
            self._axisCode = self._parent.axisCodes[1]
        elif value == 'v':
            self._axisCode = self._parent.axisCodes[0]
        else:
            if not self._axisCode:
                axisIndex = None
                for ps, psCode in enumerate(self._parent.axisCodes[0:2]):
                    if self._parent._preferences.matchAxisCode == 0:  # default - match atom type
                        if self._axisCode[0] == psCode[0]:
                            axisIndex = ps
                    elif self._parent._preferences.matchAxisCode == 1:  # match full code
                        if self._axisCode == psCode:
                            axisIndex = ps
                if not axisIndex:
                    getLogger().warning('Axis code %s not found in current strip' % self._axisCode)

        if self._glList:
            self._glList.renderMode = GLRENDERMODE_REBUILD
        # emit notifiers to repaint the GL windows
        self.GLSignals.emitPaintEvent()

    @property
    def brush(self):
        return self._brush

    @brush.setter
    def brush(self, value):
        self._brush = value
        if self._glList:
            self._glList.renderMode = GLRENDERMODE_REBUILD
        # emit notifiers to repaint the GL windows
        self.GLSignals.emitPaintEvent()

    @property
    def colour(self):
        return self._colour

    @colour.setter
    def colour(self, value):
        self._colour = value
        if value in REGION_COLOURS.keys():
            self._brush = REGION_COLOURS[value]
        if self._glList:
            self._glList.renderMode = GLRENDERMODE_REBUILD
        # emit notifiers to repaint the GL windows
        self.GLSignals.emitPaintEvent()

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value
        if self._glList:
            self._glList.renderMode = GLRENDERMODE_REBUILD
        # emit notifiers to repaint the GL windows
        self.GLSignals.emitPaintEvent()

    @property
    def lineStyle(self):
        return self._lineStyle

    @lineStyle.setter
    def lineStyle(self, style):
        self._lineStyle = style
        if self._glList:
            self._glList.renderMode = GLRENDERMODE_REBUILD
        # emit notifiers to repaint the GL windows
        self.GLSignals.emitPaintEvent()

    @property
    def lineWidth(self):
        return self._lineWidth

    @lineWidth.setter
    def lineWidth(self, width):
        self._lineWidth = width
        if self._glList:
            self._glList.renderMode = GLRENDERMODE_REBUILD
        # emit notifiers to repaint the GL windows
        self.GLSignals.emitPaintEvent()

    @property
    def bounds(self):
        return self._bounds

    @bounds.setter
    def bounds(self, value):
        self._bounds = value
        if self._glList:
            self._glList.renderMode = GLRENDERMODE_REBUILD
        # emit notifiers to repaint the GL windows
        self.GLSignals.emitPaintEvent()

    def _rebuildIntegral(self):
        """Build the VBO containing the polygons for the IntegralRegion
        """
        if isinstance(self._object, Integral):

            if self._object.integralList.spectrum.intensities is not None and self._object.integralList.spectrum.intensities.size != 0:

                if not hasattr(self, '_integralArea'):
                    self._integralArea = GLVertexArray(numLists=1,
                                                       renderMode=GLRENDERMODE_DRAW, blendMode=False,
                                                       drawMode=GL.GL_QUAD_STRIP, fillMode=GL.GL_FILL,
                                                       dimension=2, GLContext=self._parent)
                intArea = self._integralArea
                thisRegion = self._object._1Dregions

                if thisRegion:
                    intArea.numVertices = len(thisRegion[1]) * 2
                    intArea.vertices = np.empty(intArea.numVertices * 2, dtype=np.float32)

                    if not self._parent.spectrumDisplay._flipped:
                        # 1D region in normal orientation
                        intArea.vertices[::4] = thisRegion[1]
                        intArea.vertices[2::4] = thisRegion[1]
                        intArea.vertices[1::4] = thisRegion[0]
                        intArea.vertices[3::4] = thisRegion[2]
                    else:
                        # 1D region flipped
                        intArea.vertices[::4] = thisRegion[0]
                        intArea.vertices[2::4] = thisRegion[2]
                        intArea.vertices[1::4] = thisRegion[1]
                        intArea.vertices[3::4] = thisRegion[1]

                    if self._object and self._object in self._glList._parent.current.integrals:
                        solidColour = list(self._glList._parent.highlightColour)
                    else:
                        solidColour = list(self._brush)
                    solidColour[3] = 1.0
                    intArea.colors = np.array(solidColour * intArea.numVertices, dtype=np.float32)
                    intArea.defineVertexColorVBO()


#=========================================================================================
# GLInfiniteLine
#=========================================================================================

class GLInfiniteLine(GLRegion):
    valuesChanged = pyqtSignal(float)
    editingFinished = pyqtSignal(dict)

    def __init__(self, parent, glList, values=(0, 0), axisCode=None, orientation='h',
                 brush=None, colour='blue',
                 movable=True, visible=True, bounds=None,
                 obj=None, objectView=None, lineStyle='dashed', lineWidth=1.0,
                 regionType=GLLINETYPE):

        super(GLInfiniteLine, self).__init__(parent, glList, values=values, axisCode=axisCode, orientation=orientation,
                                             brush=brush, colour=colour,
                                             movable=movable, visible=visible, bounds=bounds,
                                             obj=obj, objectView=objectView, lineStyle=lineStyle, lineWidth=lineWidth,
                                             regionType=regionType)

    # same as GLRegion, but _values is a singular item
    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, value):
        self._values = value
        if self._glList:
            self._glList.renderMode = GLRENDERMODE_REBUILD
        if self._valuesChangedEnabled:
            self.valuesChanged.emit(value)
        # change the limits in the integral object
        if self._object and not self._object.isDeleted:
            self._object.limits = [(value, value)]
        # emit notifiers to repaint the GL windows
        self.GLSignals.emitPaintEvent()

    def setValue(self, val, emitValuesChanged=True):
        # use the region to simulate an infinite line - calls setter above
        oldValue = self._valuesChangedEnabled
        self._valuesChangedEnabled = emitValuesChanged
        self.values = val
        self._valuesChangedEnabled = oldValue


#=========================================================================================
# GLExternalRegion
#=========================================================================================

class GLExternalRegion(GLVertexArray):
    def __init__(self, project=None, GLContext=None, spectrumView=None, integralListView=None):
        super().__init__(renderMode=GLRENDERMODE_REBUILD, blendMode=True,
                         GLContext=GLContext, drawMode=GL.GL_QUADS,
                         dimension=2)
        self.project = project
        self._regions = []
        self.spectrumView = spectrumView
        self.integralListView = integralListView
        self.GLContext = GLContext

    def drawIndexImmediate(self):
        # draw twice to highlight the outline
        self.fillMode = GL.GL_LINE
        super().drawIndexImmediate()
        self.fillMode = GL.GL_FILL
        super().drawIndexImmediate()

    def defineIndexVBO(self):
        super().defineIndexVBO()

    def drawIndexVBO(self):
        # draw twice to highlight the outline
        self.fillMode = GL.GL_LINE
        super().drawIndexVBO()
        self.fillMode = GL.GL_FILL
        super().drawIndexVBO()

    def _clearRegions(self):
        self._regions = []

    def addIntegral(self, integral, integralListView, colour='blue', brush=None):
        """Add an integral region to the spectrumDisplay.
        """
        lims = integral.limits[0] if integral.limits else (0.0, 0.0)

        if self._parent.spectrumDisplay.is1D and self._parent.spectrumDisplay._flipped:
            ornt = 'h'
        else:
            ornt = 'v'

        return self._addRegion(values=lims, orientation=ornt, movable=True,
                               obj=integral, objectView=integralListView, colour=colour, brush=brush)

    def _removeRegion(self, region):
        if region in self._regions:
            self._regions.remove(region)

    def _addRegion(self, values=None, axisCode=None, orientation=None,
                   brush=None, colour='blue',
                   movable=True, visible=True, bounds=None,
                   obj=None, objectView=None):

        if colour in REGION_COLOURS.keys() and not brush:
            brush = REGION_COLOURS[colour]

        if orientation == 'h':
            axisCode = self._parent._axisCodes[1]
        elif orientation == 'v':
            axisCode = self._parent._axisCodes[0]
        else:
            if axisCode:
                axisIndex = None
                for ps, psCode in enumerate(self._parent._axisCodes[0:2]):
                    if self._parent._preferences.matchAxisCode == 0:  # default - match atom type

                        if axisCode[0] == psCode[0]:
                            axisIndex = ps
                    elif self._parent._preferences.matchAxisCode == 1:  # match full code
                        if axisCode == psCode:
                            axisIndex = ps

                    if axisIndex == 0:
                        orientation = 'v'
                    elif axisIndex == 1:
                        orientation = 'h'

                if not axisIndex:
                    getLogger().warning('Axis code %s not found in current strip' % axisCode)
                    return None
            else:
                axisCode = self._parent._axisCodes[0]
                orientation = 'v'

        newRegion = GLRegion(self._parent, self,
                             values=values,
                             axisCode=axisCode,
                             orientation=orientation,
                             brush=brush,
                             colour=colour,
                             movable=movable,
                             visible=visible,
                             bounds=bounds,
                             obj=obj,
                             objectView=objectView)
        self._regions.append(newRegion)

        axisIndex = 0
        for ps, psCode in enumerate(self._parent.axisOrder[0:2]):
            if self._parent._preferences.matchAxisCode == 0:  # default - match atom type

                if axisCode[0] == psCode[0]:
                    axisIndex = ps
            elif self._parent._preferences.matchAxisCode == 1:  # match full code
                if axisCode == psCode:
                    axisIndex = ps

        # assume 'ppm' axis units
        if axisIndex == 0:
            # vertical ruler
            pos0 = x0 = values[0]
            pos1 = x1 = values[1]
            y0 = self._parent.axisT + self._parent.pixelY
            y1 = self._parent.axisB - self._parent.pixelY
        else:
            # horizontal ruler
            pos0 = y0 = values[0]
            pos1 = y1 = values[1]
            x0 = self._parent.axisL - self._parent.pixelX
            x1 = self._parent.axisR + self._parent.pixelX

        colour = brush
        index = self.numVertices

        if self.indices.size:
            self.indices = np.append(self.indices, np.array((index, index + 1, index + 2, index + 3,
                                                             index, index + 1, index, index + 1,
                                                             index + 1, index + 2, index + 1, index + 2,
                                                             index + 2, index + 3, index + 2, index + 3,
                                                             index, index + 3, index, index + 3), dtype=np.uint32))
            self.vertices = np.append(self.vertices, np.array((x0, y0, x0, y1, x1, y1, x1, y0), dtype=np.float32))
            self.colors = np.append(self.colors, np.array(colour * 4, dtype=np.float32))
            self.attribs = np.append(self.attribs, (axisIndex, pos0, axisIndex, pos1, axisIndex, pos0, axisIndex, pos1))
        else:
            self.indices = np.array((index, index + 1, index + 2, index + 3,
                                     index, index + 1, index, index + 1,
                                     index + 1, index + 2, index + 1, index + 2,
                                     index + 2, index + 3, index + 2, index + 3,
                                     index, index + 3, index, index + 3), dtype=np.uint32)
            self.vertices = np.array((x0, y0, x0, y1, x1, y1, x1, y0), dtype=np.float32)
            self.colors = np.array(colour * 4, dtype=np.float32)
            self.attribs = np.append(self.attribs, (axisIndex, pos0, axisIndex, pos1, axisIndex, pos0, axisIndex, pos1))

        index += 4
        self.numVertices += 4

        return newRegion

    def _rebuildIntegralAreas(self):
        self._rebuild(checkBuild=True)

        return

        # for reg in self._regions:
        #     if reg._integralArea.renderMode == GLRENDERMODE_REBUILD:
        #         reg._integralArea.renderMode = GLRENDERMODE_DRAW
        #         reg._rebuildIntegral()

    def _rescale(self):
        vertices = self.numVertices
        axisT = self._parent.axisT
        axisB = self._parent.axisB
        axisL = self._parent.axisL
        axisR = self._parent.axisR
        pixelX = self._parent.pixelX
        pixelY = self._parent.pixelY

        if vertices:
            for pp in range(0, 2 * vertices, 8):
                axisIndex = int(self.attribs[pp])
                axis0 = self.attribs[pp + 1]
                axis1 = self.attribs[pp + 3]

                if axisIndex == 0:
                    offsets = [axis0, axisT + pixelY, axis0, axisB - pixelY,
                               axis1, axisB - pixelY, axis1, axisT + pixelY]
                else:
                    offsets = [axisL - pixelX, axis0, axisL - pixelX, axis1,
                               axisR + pixelX, axis1, axisR + pixelX, axis0]

                self.vertices[pp:pp + 8] = offsets

        self.defineIndexVBO()

    def _resize(self):
        axisT = self._parent.axisT
        axisB = self._parent.axisB
        axisL = self._parent.axisL
        axisR = self._parent.axisR
        pixelX = self._parent.pixelX
        pixelY = self._parent.pixelY

        pp = 0
        for reg in self._regions:
            try:
                axisIndex = int(self.attribs[pp])
            except Exception:
                axisIndex = 0

            try:
                values = reg._object.limits[0]
            except Exception:
                values = reg.values

            axis0 = values[0]
            axis1 = values[1]
            reg._values = values

            if axisIndex == 0:
                offsets = [axis0, axisT + pixelY, axis0, axisB - pixelY,
                           axis1, axisB - pixelY, axis1, axisT + pixelY]
            else:
                offsets = [axisL - pixelX, axis0, axisL - pixelX, axis1,
                           axisR + pixelX, axis1, axisR + pixelX, axis0]

            self.vertices[pp:pp + 8] = offsets
            self.attribs[pp + 1] = axis0
            self.attribs[pp + 3] = axis1
            self.attribs[pp + 5] = axis0
            self.attribs[pp + 7] = axis1
            pp += 8

        self.defineIndexVBO()

    def _rebuild(self, checkBuild=False):
        axisT = self._parent.axisT
        axisB = self._parent.axisB
        axisL = self._parent.axisL
        axisR = self._parent.axisR
        pixelX = self._parent.pixelX
        pixelY = self._parent.pixelY

        self.clearArrays()
        for reg in self._regions:
            if not reg.visible:
                continue
            axisIndex = 0
            for ps, psCode in enumerate(self._parent.axisOrder[0:2]):
                if self._parent._preferences.matchAxisCode == 0:  # default - match atom type

                    if reg.axisCode[0] == psCode[0]:
                        axisIndex = ps
                elif self._parent._preferences.matchAxisCode == 1:  # match full code
                    if reg.axisCode == psCode:
                        axisIndex = ps

            # assume 'ppm' axis units
            if axisIndex == 0:
                # vertical ruler
                pos0 = x0 = reg.values[0]
                pos1 = x1 = reg.values[1]
                y0 = axisT + pixelY
                y1 = axisB - pixelY
            else:
                # horizontal ruler
                pos0 = y0 = reg.values[0]
                pos1 = y1 = reg.values[1]
                x0 = axisL - pixelX
                x1 = axisR + pixelX

            colour = reg.brush
            index = self.numVertices
            if self.indices.size:
                self.indices = np.append(self.indices, np.array((index, index + 1, index + 2, index + 3,
                                                                 index, index + 1, index, index + 1,
                                                                 index + 1, index + 2, index + 1, index + 2,
                                                                 index + 2, index + 3, index + 2, index + 3,
                                                                 index, index + 3, index, index + 3), dtype=np.uint32))
                self.vertices = np.append(self.vertices, np.array((x0, y0, x0, y1, x1, y1, x1, y0), dtype=np.float32))
                self.colors = np.append(self.colors, np.array(colour * 4, dtype=np.float32))
                self.attribs = np.append(self.attribs, (axisIndex, pos0, axisIndex, pos1, axisIndex, pos0, axisIndex, pos1))
            else:
                self.indices = np.array((index, index + 1, index + 2, index + 3,
                                         index, index + 1, index, index + 1,
                                         index + 1, index + 2, index + 1, index + 2,
                                         index + 2, index + 3, index + 2, index + 3,
                                         index, index + 3, index, index + 3), dtype=np.uint32)
                self.vertices = np.array((x0, y0, x0, y1, x1, y1, x1, y0), dtype=np.float32)
                self.colors = np.array(colour * 4, dtype=np.float32)
                self.attribs = np.append(self.attribs, (axisIndex, pos0, axisIndex, pos1, axisIndex, pos0, axisIndex, pos1))

            index += 4
            self.numVertices += 4


#=========================================================================================
# GLIntegralRegion
#=========================================================================================

class GLIntegralRegion(GLExternalRegion):
    def __init__(self, project=None, GLContext=None, spectrumView=None, integralListView=None):
        super().__init__(project=project, GLContext=GLContext,
                         spectrumView=spectrumView, integralListView=integralListView)

    def _addRegion(self, values=None, axisCode=None, orientation=None,
                   brush=None, colour='blue',
                   movable=True, visible=True, bounds=None,
                   obj=None, objectView=None):

        if colour in REGION_COLOURS.keys() and not brush:
            brush = REGION_COLOURS[colour]

        # reconstructed region is already flipped here for 1D :|
        if orientation == 'h':
            axisCode = self._parent._axisCodes[1]
        elif orientation == 'v':
            axisCode = self._parent._axisCodes[0]
        else:
            if axisCode:
                axisIndex = None
                for ps, psCode in enumerate(self._parent._axisCodes[0:2]):
                    if self._parent._preferences.matchAxisCode == 0:  # default - match atom type

                        if axisCode[0] == psCode[0]:
                            axisIndex = ps
                    elif self._parent._preferences.matchAxisCode == 1:  # match full code
                        if axisCode == psCode:
                            axisIndex = ps

                    if axisIndex == 0:
                        orientation = 'v'
                    elif axisIndex == 1:
                        orientation = 'h'

                if not axisIndex:
                    getLogger().warning('Axis code %s not found in current strip' % axisCode)
                    return None
            else:
                axisCode = self._parent._axisCodes[0]
                orientation = 'v'

        # get the new added region
        newRegion = GLRegion(self._parent, self,
                             values=values,
                             axisCode=axisCode,
                             orientation=orientation,
                             brush=brush,
                             colour=colour,
                             movable=movable,
                             visible=visible,
                             bounds=bounds,
                             obj=obj,
                             objectView=objectView)
        self._regions.append(newRegion)

        axisIndex = 0
        for ps, psCode in enumerate(self._parent.axisOrder[0:2]):
            if self._parent._preferences.matchAxisCode == 0:  # default - match atom type

                if axisCode[0] == psCode[0]:
                    axisIndex = ps
            elif self._parent._preferences.matchAxisCode == 1:  # match full code
                if axisCode == psCode:
                    axisIndex = ps

        # assume 'ppm' axis units
        if axisIndex == 0:
            # vertical ruler
            pos0 = x0 = values[0]
            pos1 = x1 = values[1]
            y0 = self._parent.axisT + self._parent.pixelY
            y1 = self._parent.axisB - self._parent.pixelY
        else:
            # horizontal ruler
            pos0 = y0 = values[0]
            pos1 = y1 = values[1]
            x0 = self._parent.axisL - self._parent.pixelX
            x1 = self._parent.axisR + self._parent.pixelX

        # # get the new added region
        # newRegion = self._regions[-1]

        if obj and obj in self._parent.current.integrals:

            # draw integral bars if in the current list
            colour = list(self._parent.highlightColour)
            colour[3] = CCPNGLWIDGET_INTEGRALSHADE

            index = self.numVertices
            if self.indices.size:
                self.indices = np.append(self.indices, np.array((index, index + 1, index + 2, index + 3,
                                                                 index, index + 1, index, index + 1,
                                                                 index + 1, index + 2, index + 1, index + 2,
                                                                 index + 2, index + 3, index + 2, index + 3,
                                                                 index, index + 3, index, index + 3), dtype=np.uint32))
                self.vertices = np.append(self.vertices, np.array((x0, y0, x0, y1, x1, y1, x1, y0), dtype=np.float32))
                self.colors = np.append(self.colors, np.array(colour * 4, dtype=np.float32))
                self.attribs = np.append(self.attribs, (axisIndex, pos0, axisIndex, pos1, axisIndex, pos0, axisIndex, pos1))
            else:
                self.indices = np.array((index, index + 1, index + 2, index + 3,
                                         index, index + 1, index, index + 1,
                                         index + 1, index + 2, index + 1, index + 2,
                                         index + 2, index + 3, index + 2, index + 3,
                                         index, index + 3, index, index + 3), dtype=np.uint32)
                self.vertices = np.array((x0, y0, x0, y1, x1, y1, x1, y0), dtype=np.float32)
                self.colors = np.array(colour * 4, dtype=np.float32)
                self.attribs = np.append(self.attribs, (axisIndex, pos0, axisIndex, pos1, axisIndex, pos0, axisIndex, pos1))

            index += 4
            self.numVertices += 4

            newRegion.visible = True
            newRegion._pp = (self.numVertices - 4) * 2
        else:

            # Need to put the normal regions in here
            newRegion.visible = False
            newRegion._pp = None

        self.defineIndexVBO()
        newRegion._rebuildIntegral()

        return newRegion

    def _resize(self):
        axisT = self._parent.axisT
        axisB = self._parent.axisB
        axisL = self._parent.axisL
        axisR = self._parent.axisR
        pixelX = self._parent.pixelX
        pixelY = self._parent.pixelY

        for reg in self._regions:
            pp = reg._pp
            if not pp:
                continue

            if not reg.isVisible:
                continue

            try:
                axisIndex = int(self.attribs[pp])
            except Exception:
                axisIndex = 0

            try:
                values = reg._object.limits[0]
            except Exception:
                values = reg.values

            axis0 = values[0]
            axis1 = values[1]
            reg._values = values

            if axisIndex == 0:
                offsets = [axis0, axisT + pixelY, axis0, axisB - pixelY,
                           axis1, axisB - pixelY, axis1, axisT + pixelY]
            else:
                offsets = [axisL - pixelX, axis0, axisL - pixelX, axis1,
                           axisR + pixelX, axis1, axisR + pixelX, axis0]

            self.vertices[pp:pp + 8] = offsets
            self.attribs[pp + 1] = axis0
            self.attribs[pp + 3] = axis1
            self.attribs[pp + 5] = axis0
            self.attribs[pp + 7] = axis1

        self.defineIndexVBO()

    def _rebuild(self, checkBuild=False):
        axisT = self._parent.axisT
        axisB = self._parent.axisB
        axisL = self._parent.axisL
        axisR = self._parent.axisR
        pixelX = self._parent.pixelX
        pixelY = self._parent.pixelY

        self.clearArrays()
        for reg in self._regions:

            if reg._object.isDeleted:
                return

            axisIndex = 0
            for ps, psCode in enumerate(self._parent.axisOrder[0:2]):
                if self._parent._preferences.matchAxisCode == 0:  # default - match atom type

                    if reg.axisCode[0] == psCode[0]:
                        axisIndex = ps
                elif self._parent._preferences.matchAxisCode == 1:  # match full code
                    if reg.axisCode == psCode:
                        axisIndex = ps

            lims = reg._object.limits[0] if reg._object.limits else (0.0, 0.0)
            # assume 'ppm' axis units
            if axisIndex == 0:  # self._parent.spectrumDisplay._flipped:
                # vertical ruler
                pos0 = x0 = lims[0]  # reg.values[0]
                pos1 = x1 = lims[1]  # reg.values[1]
                reg._values = (pos0, pos1)  # not nice, but feed back in to current _values
                y0 = axisT + pixelY
                y1 = axisB - pixelY
            else:
                # horizontal ruler - 1D flipped
                pos0 = y0 = lims[0]  # reg.values[0]
                pos1 = y1 = lims[1]  # reg.values[1]
                reg._values = (pos0, pos1)  # not nice, but feed back in to current _values
                x0 = axisL - pixelX
                x1 = axisR + pixelX

            if reg._object in self._parent.current.integrals:
                solidColour = list(self._parent.highlightColour)
                solidColour[3] = CCPNGLWIDGET_INTEGRALSHADE

                index = self.numVertices
                if self.indices.size:
                    self.indices = np.append(self.indices, np.array((index, index + 1, index + 2, index + 3,
                                                                     index, index + 1, index, index + 1,
                                                                     index + 1, index + 2, index + 1, index + 2,
                                                                     index + 2, index + 3, index + 2, index + 3,
                                                                     index, index + 3, index, index + 3), dtype=np.uint32))
                    self.vertices = np.append(self.vertices, np.array((x0, y0, x0, y1, x1, y1, x1, y0), dtype=np.float32))
                    self.colors = np.append(self.colors, np.array(solidColour * 4, dtype=np.float32))
                    self.attribs = np.append(self.attribs, (axisIndex, pos0, axisIndex, pos1, axisIndex, pos0, axisIndex, pos1))
                else:
                    self.indices = np.array((index, index + 1, index + 2, index + 3,
                                             index, index + 1, index, index + 1,
                                             index + 1, index + 2, index + 1, index + 2,
                                             index + 2, index + 3, index + 2, index + 3,
                                             index, index + 3, index, index + 3), dtype=np.uint32)
                    self.vertices = np.array((x0, y0, x0, y1, x1, y1, x1, y0), dtype=np.float32)
                    self.colors = np.array(solidColour * 4, dtype=np.float32)
                    self.attribs = np.append(self.attribs, (axisIndex, pos0, axisIndex, pos1, axisIndex, pos0, axisIndex, pos1))

                index += 4
                self.numVertices += 4

                reg.visible = True
                reg._pp = (self.numVertices - 4) * 2
            else:
                reg.visible = False
                reg._pp = None

            if not checkBuild:
                reg._rebuildIntegral()
            else:
                if hasattr(reg, '_integralArea') and reg._integralArea.renderMode == GLRENDERMODE_REBUILD:
                    reg._integralArea.renderMode = GLRENDERMODE_DRAW
                    reg._rebuildIntegral()

            # rebuild VBO for the integral shape
            # reg._integralArea.defineVertexColorVBO()

        # redefined VBO for the highlighting
        self.defineIndexVBO()
