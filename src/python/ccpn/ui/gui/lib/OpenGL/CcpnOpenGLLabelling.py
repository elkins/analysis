"""
Classes to handle drawing of symbols and symbol labelling to the openGL window
Currently this is peaks and multiplets
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
__dateModified__ = "$dateModified: 2024-09-06 15:02:43 +0100 (Fri, September 06, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2018-12-20 13:28:13 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

import math
import numpy as np

from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.Multiplet import Multiplet
from ccpn.core.MultipletList import MultipletList
from ccpn.core.Integral import Integral
from ccpn.core.NmrAtom import NmrAtom
from ccpn.util.Colour import getAutoColourRgbRatio
from ccpn.util.AttrDict import AttrDict
from ccpn.ui.gui.guiSettings import CCPNGLWIDGET_FOREGROUND, getColours
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLFonts import GLString
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLArrays import GLRENDERMODE_DRAW, GLRENDERMODE_RESCALE, GLRENDERMODE_REBUILD, \
    GLREFRESHMODE_NEVER, GLREFRESHMODE_REBUILD, GLSymbolArray, GLLabelArray
import ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs as GLDefs
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import getAliasSetting
from ccpn.ui.gui.lib.PeakListLib import line_rectangle_intersection

# NOTE:ED - remember these for later, may create larger vertex arrays for symbols, but should be quicker
#       --
#       x = np.array([1, 2, 3, -1, 5, 0, 3, 4, 4, 7, 3, 5, 9, 0, 5, 4, 3], dtype=np.uint32)
#       seems to be the fastest way of getting masked values
#           SKIPINDEX = np.uint32(-1) = 4294967295
#           i.e. max index number, use as fill
#           timeit.timeit('import numpy as np; x = np.array([1, 2, 3, -1, 5, 0, 3, 4, 4, 7, 3, 5, 9, 0, 5, 4, 3], dtype=np.uint32); x[np.where(x != 3)]', number=200000)
#       fastest way to create filled arrays
#           *** timeit.timeit('import numpy as np; x = np.array([1, 2, 3, -1, 5, 0, 3, 4, 4, 7, 3, 5, 9, 0, 5, 4, 3], dtype=np.uint32); a = x[x != SKIPINDEX]', number=200000)
#               timeit.timeit('import numpy as np; x = np.array([1, 2, 3, -1, 5, 0, 3, 4, 4, 7, 3, 5, 9, 0, 5, 4, 3], dtype=np.uint32); mx = np.full(200000, SKIPINDEX, dtype=np.uint32)', number=20000)
#       --
#       np.take(x, np.where(x != 3))
#       mx = np.ma.masked_values(x, 3)
#       a = x[np.where(x != 3)]
#       *** a = x[x != SKIPINDEX]

from ccpn.ui.gui.lib.OpenGL import GL


OBJ_ISINPLANE = 0
OBJ_ISINFLANKINGPLANE = 1
OBJ_LINEWIDTHS = 2
OBJ_SPECTRALFREQUENCIES = 3
OBJ_OTHER = 4
OBJ_STORELEN = 5

_totalTime = 0.0
_timeCount = 0
_numTimes = 12

DEFAULTLINECOLOUR = '#7f7f7f'


#=========================================================================================
# GLLabelling
#=========================================================================================

class GLLabelling():
    """Base class to handle symbol and symbol labelling
    """

    LENSQ = GLDefs.LENSQ
    LENSQ2 = GLDefs.LENSQ2
    LENSQ4 = GLDefs.LENSQ4
    POINTCOLOURS = GLDefs.POINTCOLOURS

    LENARR = GLDefs.LENARR
    LENARR2 = GLDefs.LENARR2
    LENARR4 = GLDefs.LENARR4
    ARROWCOLOURS = GLDefs.ARROWCOLOURS

    def __init__(self, parent=None, strip=None, name=None, enableResize=False):
        """Initialise the class
        """
        self._GLParent = parent
        self.strip = strip
        self.name = name
        self._resizeEnabled = enableResize
        self._threads = {}
        self._threadupdate = False
        self.current = self.strip.current if self.strip else None
        self._objectStore = {}

        self._GLSymbols = {}
        self._GLArrows = {}
        self._GLLabels = {}
        self._ordering = ()
        self._visibleOrdering = ()
        self._listViews = ()
        self._visibleListViews = ()
        self._objIsInVisiblePlanesCache = {}

        self.autoColour = self._GLParent.SPECTRUMPOSCOLOUR

    def enableResize(self, value):
        """enable resizing for labelling
        """
        if not isinstance(value, bool):
            raise TypeError('enableResize must be a bool')

        self._resizeEnabled = value

    def rescale(self):
        if self._resizeEnabled:
            for pp in self._GLSymbols.values():
                pp.renderMode = GLRENDERMODE_RESCALE
            for pp in self._GLLabels.values():
                pp.renderMode = GLRENDERMODE_RESCALE
            for pp in self._GLArrows.values():
                pp.renderMode = GLRENDERMODE_RESCALE

    def setListViews(self, spectrumViews):
        """Return a list of tuples containing the visible lists and the containing spectrumView
        """
        self._listViews = [(lv, specView) for specView in spectrumViews
                           for lv in self.listViews(specView)
                           if not lv.isDeleted]
        self._visibleListViews = [(lv, specView) for lv, specView in self._listViews
                                  if lv.isDisplayed
                                  and specView.isDisplayed]
        # and lv in self._GLSymbols.keys()]
        self._ordering = spectrumViews

    # def _handleNotifier(self, triggers, obj):
    #     if Notifier.DELETE in triggers:
    #         self._deleteSymbol(obj, None, None)
    #         self._deleteLabel(obj, None, None)
    #
    #     if Notifier.CREATE in triggers:
    #         self._createSymbol(obj)
    #         self._createLabel(obj)
    #
    #     if Notifier.CHANGE in triggers:
    #         self._changeSymbol(obj)
    #         self._changeLabel(obj)

    def _processNotifier(self, data):
        """Process notifiers
        """
        trigger = data[Notifier.TRIGGER]
        obj = data[Notifier.OBJECT]

        if isinstance(obj, (Multiplet, Integral)):
            # update the multiplet labelling
            if trigger == Notifier.DELETE:
                self._deleteSymbol(obj, data.get('_list'), data.get('_spectrum'))
                self._deleteLabel(obj, data.get('_list'), data.get('_spectrum'))
                self._deleteArrow(obj, data.get('_list'), data.get('_spectrum'))

            if trigger == Notifier.CREATE:
                self._createSymbol(obj)
                self._createLabel(obj)
                self._createArrow(obj)

            if trigger == Notifier.CHANGE and not obj.isDeleted:
                self._changeSymbol(obj)
                self._changeLabel(obj)
                self._changeArrow(obj)

        elif isinstance(obj, NmrAtom):  # and not obj.isDeleted:
            if obj.isDeleted:
                # update the labels on the peaks
                for peak in obj._oldAssignedPeaks:  # use the deleted attribute
                    for mlt in peak.multiplets:
                        self._changeSymbol(mlt)
                        self._changeLabel(mlt)
                        self._changeArrow(mlt)
            else:
                for peak in obj.assignedPeaks:
                    for mlt in peak.multiplets:
                        # should only be one now
                        self._changeSymbol(mlt)
                        self._changeLabel(mlt)
                        self._changeArrow(mlt)

        elif isinstance(obj, MultipletList):
            if trigger in [Notifier.DELETE]:

                # clear the vertex arrays
                for pList, glArray in self._GLSymbols.items():
                    if pList.isDeleted:
                        glArray.clearArrays()
                # clear the vertex arrays
                for pList, glArray in self._GLArrows.items():
                    if pList.isDeleted:
                        glArray.clearArrays()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Clean up for deletion
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _delete(self):
        """Clean up the object ready for deletion
        """
        for olv, vArray in list(self._GLLabels.items()):
            if olv.isDeleted:
                vArray.stringList = None
                vArray._delete()
                del self._GLLabels[olv]
        for olv, vArray in list(self._GLSymbols.items()):
            if olv.isDeleted:
                vArray._delete()
                del self._GLSymbols[olv]
        for olv, vArray in list(self._GLArrows.items()):
            if olv.isDeleted:
                vArray._delete()
                del self._GLArrows[olv]

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # New Arrow list - separate from symbols and labels, more control
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _deleteArrow(self, obj, parentList, spectrum):
        if pls := parentList:
            # spectrum = pls.spectrum

            for objListView in self.listViews(pls):
                if objListView in self._GLArrows.keys():
                    for spectrumView in spectrum.spectrumViews:
                        if spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            self._removeArrow(spectrumView, objListView, obj)
                            # self._updateHighlightedArrows(spectrumView, objListView)
                            self._GLArrows[objListView].pushAliasedIndexVBO()
                            break

    # from ccpn.util.decorators import profile
    # @profile
    def _createArrow(self, obj):
        if pls := self.objectList(obj):
            spectrum = pls.spectrum

            for objListView in self.listViews(pls):
                if objListView in self._GLArrows.keys():
                    for spectrumView in spectrum.spectrumViews:
                        if spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            self._appendArrow(spectrumView, objListView, obj)
                            # self._updateHighlightedArrows(spectrumView, objListView)
                            self._GLArrows[objListView].pushAliasedIndexVBO()
                            break

    def _changeArrow(self, obj):
        if pls := self.objectList(obj):
            spectrum = pls.spectrum

            for objListView in self.listViews(pls):
                if objListView in self._GLArrows.keys():
                    for spectrumView in spectrum.spectrumViews:
                        if spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            self._removeArrow(spectrumView, objListView, obj)
                            self._appendArrow(spectrumView, objListView, obj)
                            # self._updateHighlightedArrows(spectrumView, objListView)
                            self._GLArrows[objListView].pushAliasedIndexVBO()
                            break

    def _removeArrow(self, spectrumView, objListView, delObj):
        """Remove an arrow from the list
        """
        # arrowType = self.strip.arrowType

        drawList = self._GLArrows[objListView]
        self.objIsInVisiblePlanesRemove(spectrumView, delObj)  # probably only needed in create/change

        indexOffset = 0
        numPoints = 0

        pp = 0
        while (pp < len(drawList.pids)):
            # check whether the peaks still exists
            obj = drawList.pids[pp]

            if obj == delObj:
                offset = drawList.pids[pp + 1]
                numPoints = drawList.pids[pp + 2]

                # if arrowType != 0 and arrowType != 3:  # not a cross/plus
                #     numPoints = 2 * numPoints + 5

                # _isInPlane = drawList.pids[pp + 3]
                # _isInFlankingPlane = drawList.pids[pp + 4]
                # _selected = drawList.pids[pp + 5]
                indexStart = drawList.pids[pp + 6]
                indexEnd = drawList.pids[pp + 7]
                indexOffset = indexEnd - indexStart

                st, end = 4 * offset, 4 * (offset + numPoints)
                drawList.indices = np.delete(drawList.indices, np.s_[indexStart:indexEnd])
                drawList.vertices = np.delete(drawList.vertices, np.s_[st: end])
                drawList.attribs = np.delete(drawList.attribs, np.s_[st: end])
                drawList.offsets = np.delete(drawList.offsets, np.s_[st: end])
                drawList.colors = np.delete(drawList.colors, np.s_[st: end])

                drawList.pids = np.delete(drawList.pids, np.s_[pp:pp + GLDefs.LENPID])
                drawList.numVertices -= numPoints

                # subtract the offset from all the higher indices to account for the removed points
                drawList.indices[np.where(drawList.indices >= offset)] -= numPoints
                break

            else:
                pp += GLDefs.LENPID

        # clean up the rest of the list
        while (pp < len(drawList.pids)):
            drawList.pids[pp + 1] -= numPoints
            drawList.pids[pp + 6] -= indexOffset
            drawList.pids[pp + 7] -= indexOffset
            pp += GLDefs.LENPID

    def _appendArrow(self, spectrumView, objListView, obj):
        """Append a new arrow to the end of the list
        """
        spectrum = spectrumView.spectrum
        drawList = self._GLArrows[objListView]
        if obj in drawList.pids[0::GLDefs.LENPID]:
            return

        self.objIsInVisiblePlanesRemove(spectrumView, obj)

        # find the correct scale to draw square pixels
        # don't forget to change when the axes change

        _, _, arrowType, arrowSize, arrowMinimum, arrowWidth, r, w = self._getArrowWidths(spectrumView)

        # change the ratio on resize
        drawList.refreshMode = GLREFRESHMODE_REBUILD
        drawList.drawMode = GL.GL_LINES
        drawList.fillMode = None

        # build the peaks VBO
        indexing = AttrDict()
        indexing.start = len(drawList.indices)
        indexing.end = len(drawList.indices)
        indexing.vertexStart = drawList.numVertices

        pls = self.objectList(objListView)

        if objListView.meritEnabled and obj.figureOfMerit < objListView.meritThreshold:
            objCol = objListView.meritColour or GLDefs.DEFAULTCOLOUR
        else:
            objCol = objListView.arrowColour or GLDefs.DEFAULTCOLOUR

        listCol = getAutoColourRgbRatio(objCol, pls.spectrum,
                                        self.autoColour,
                                        getColours()[CCPNGLWIDGET_FOREGROUND])

        spectrumFrequency = spectrum.spectrometerFrequencies

        strip = spectrumView.strip
        self._appendArrowItem(strip, obj, listCol, indexing, r, w,
                              spectrumFrequency, arrowType, arrowSize, arrowMinimum, drawList, spectrumView,
                              objListView)

    def _appendArrowItem(self, strip, obj, listCol, indexing, r, w,
                         spectrumFrequency, arrowType, arrowSize, arrowMinimum, drawList, spectrumView, objListView):
        """append a single arrow to the end of the arrow list
        """
        # indexStart, indexEnd are indexes into the drawList.indices for the indices for this arrow
        # indexStart = indexing.start  # indexList[0]
        indexEnd = indexing.end  #indexList[1]
        vertexStart = indexing.vertexStart

        # get visible/plane status
        _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

        # skip if not visible
        if not _isInPlane and not _isInFlankingPlane:
            return

        specSet = self._spectrumSettings[spectrumView]
        vPPX, vPPY = specSet.ppmPerPoint
        delta = specSet.delta
        ar = specSet.axisDirection
        dims = specSet.dimensionIndices
        try:
            # fix the pointPositions
            objPos = obj.pointPositions
            pxy = (objPos[dims[0]] - 1, objPos[dims[1]] - 1)
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        rx, ry = 0.0, 0.0
        tnx, tny = 0.0, 0.0
        inr, inw = r, w
        try:
            # nightmare to find the intersections between the symbol box and the bounding-box of the text
            pView = self.getViewFromListView(objListView, obj)
            tx, ty = pView.getIntersect((0, 0))  # ppm intersect
            pixX, pixY = objListView.pixelSize
            tx, ty = tx * delta[0] * ar[0], ty * delta[1] * ar[1]
            pixX, pixY = abs(pixX), abs(pixY)
            r, w = tx / vPPX, ty / vPPY  # ppm->points
            sx, sy = line_rectangle_intersection((0, 0),
                                                 (tx / vPPX, ty / vPPY),
                                                 (-inr, -inw),
                                                 (inr, inw))
            px, py = (tx - (sx * vPPX)) / pixX, (ty - (sy * vPPY)) / pixY
            _ll = px**2 + py**2
            if _ll < arrowMinimum:
                # line is too short
                sx, sy = 0, 0
                r, w = 0.0, 0.0
            else:
                # generate the end-vector perpendicular to the line
                rx, ry = -ty * pixX, tx * pixY  # back to pixels, rotated 90-degrees
                denom = (rx**2 + ry**2)**0.5
                rx = (arrowSize * rx / denom) * pixX / vPPX  # pixels->points for display
                ry = (arrowSize * ry / denom) * pixY / vPPY
                # generate the end-vector parallel to the line
                tnx, tny = tx / pixX, ty / pixY  # back to pixels, rotated 90-degrees
                denom = (tnx**2 + tny**2)**0.5
                tnx = (arrowSize * tnx / denom) * pixX / vPPX  # pixels->points for display
                tny = (arrowSize * tny / denom) * pixY / vPPY
        except Exception:
            sx, sy = 0, 0
            r, w = 0.0, 0.0

        # try:
        #     # fix the lineWidths
        #     objLineWidths = obj.pointLineWidths
        #     pointLineWidths = (objLineWidths[dims[0]], objLineWidths[dims[1]])
        # except Exception:
        #     pointLineWidths = (None, None)

        if self._isSelected(obj):
            cols = self._GLParent.highlightColour[:3]
        elif _badPos:
            cols = [1.0, 0.2, 0.1]  # red for bad position
        else:
            cols = listCol

        # frequency = (spectrumFrequency[dims[0]], spectrumFrequency[dims[1]])
        try:
            _alias = obj.aliasing
            alias = getAliasSetting(_alias[dims[0]], _alias[dims[1]])
        except Exception:
            alias = 0

        # draw an arrow
        _selected = False
        iCount = 0
        if _isInPlane or _isInFlankingPlane:
            iCount, _selected = self._appendArrowIndices(drawList, vertexStart, planeIndex, obj, arrowType)

        self._appendArrowItemVertices(_isInFlankingPlane, _isInPlane, _selected, cols, drawList, fade, iCount, indexing,
                                      obj, pxy, dims, planeIndex, r, w, alias, sx, sy, rx, ry, tnx, tny)

    def _appendArrowItemVertices(self, _isInFlankingPlane, _isInPlane, _selected, cols,
                                 drawList, fade, iCount, indexing, obj, pxy, pIndex,
                                 planeIndex, r, w, alias, sx, sy, rx, ry, tnx, tny):

        try:
            drawList.vertices = np.append(drawList.vertices, np.array((pxy[0] + sx, pxy[1] + sy, alias, 0.0,
                                                                       pxy[0] + r + rx, pxy[1] + w + ry, alias, 0.0,
                                                                       pxy[0] + r - rx, pxy[1] + w - ry, alias, 0.0,
                                                                       pxy[0] + r, pxy[1] + w, alias, 0.0,
                                                                       pxy[0] + sx + rx + 2 * tnx,
                                                                       pxy[1] + sy + ry + 2 * tny, alias, 0.0,
                                                                       pxy[0] + sx - rx + 2 * tnx,
                                                                       pxy[1] + sy - ry + 2 * tny, alias, 0.0,
                                                                       ),
                                                                      dtype=np.float32))
        except Exception as es:
            print(es)
        drawList.colors = np.append(drawList.colors, np.array((*cols, fade) * self.LENARR, dtype=np.float32))
        drawList.attribs = np.append(drawList.attribs, np.array((alias, 0.0, 0.0, 0.0) * self.LENARR, dtype=np.float32))
        drawList.offsets = np.append(drawList.offsets,
                                     np.array((pxy[0], pxy[1], 0.0, 0.0) * self.LENARR, dtype=np.float32))

        # called extraIndices, extraIndexCount above
        # add extra indices
        _indexCount, extraIndices = self.appendExtraIndices(drawList, indexing.vertexStart + self.LENARR, obj)
        # add extra vertices for the multiplet
        extraVertices = self.appendExtraVertices(drawList, pIndex, obj, pxy, (*cols, fade), fade)
        # keep a pointer to the obj
        drawList.pids = np.append(drawList.pids, (obj, drawList.numVertices, (self.LENARR + extraVertices),
                                                  _isInPlane, _isInFlankingPlane, _selected,
                                                  indexing.end, indexing.end + iCount + _indexCount, planeIndex, 0, 0,
                                                  0))

        indexing.start += (self.LENARR + extraIndices)
        indexing.end += (iCount + _indexCount)
        drawList.numVertices += (self.LENARR + extraVertices)
        indexing.vertexStart += (self.LENARR + extraVertices)

    # _arrow = ((np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32), np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32)),
    #           (np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32), np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32)),
    #           (np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32), np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32)))  # no difference
    _arrow = (
        # strange bug, need to pad with zeros for the minute :|
        #   must be re-allocating to new smaller size, but trying to fill as previous size
        ((np.array((0, 3, 0, 0, 0, 0), dtype=np.uint32), np.array((0, 3, 0, 0, 0, 0), dtype=np.uint32)),
         (np.array((0, 3, 0, 0, 0, 0), dtype=np.uint32), np.array((0, 3, 0, 0, 0, 0), dtype=np.uint32)),
         (np.array((0, 3, 0, 0, 0, 0), dtype=np.uint32), np.array((0, 3, 0, 0, 0, 0), dtype=np.uint32))),
        ((np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32), np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32)),
         (np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32), np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32)),
         (np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32), np.array((0, 1, 1, 2, 2, 0), dtype=np.uint32))),
        ((np.array((0, 3, 0, 4, 0, 5), dtype=np.uint32), np.array((0, 3, 0, 4, 0, 5), dtype=np.uint32)),
         (np.array((0, 3, 0, 4, 0, 5), dtype=np.uint32), np.array((0, 3, 0, 4, 0, 5), dtype=np.uint32)),
         (np.array((0, 3, 0, 4, 0, 5), dtype=np.uint32), np.array((0, 3, 0, 4, 0, 5), dtype=np.uint32))),
        )
    _arrowLen = tuple(tuple(tuple(len(sym) for sym in symList) for symList in symType) for symType in _arrow)

    def _getArrowCount(self, planeIndex, obj, arrowType):
        """returns the number of indices required for the arrow based on the planeIndex
        type of planeIndex - currently 0/1/2 indicating whether normal, infront or behind
        currently visible planes
        """
        return self._arrowLen[arrowType][planeIndex % 3][self._isSelected(obj)]

    def _makeArrowIndices(self, drawList, indexEnd, vertexStart, planeIndex, obj, arrowType):
        """Make a new square arrow based on the planeIndex type.
        """
        _selected = self._isSelected(obj)
        _indices = self._arrow[arrowType][planeIndex % 3][_selected] + vertexStart
        iCount = len(_indices)
        drawList.indices[indexEnd:indexEnd + iCount] = _indices

        return iCount, _selected

    def _appendArrowIndices(self, drawList, vertexStart, planeIndex, obj, arrowType):
        """Append a new square arrow based on the planeIndex type.
        """
        _selected = self._isSelected(obj)
        _indices = self._arrow[arrowType][planeIndex % 3][_selected] + vertexStart
        iCount = len(_indices)
        drawList.indices = np.append(drawList.indices, _indices)

        return iCount, _selected

    def _buildArrows(self, spectrumView, objListView):
        spectrum = spectrumView.spectrum

        if objListView not in self._GLArrows:
            # creates a new GLArrowArray set to rebuild for below
            self._GLArrows[objListView] = GLSymbolArray(GLContext=self,
                                                        spectrumView=spectrumView,
                                                        objListView=objListView)

        drawList = self._GLArrows[objListView]

        if drawList.renderMode == GLRENDERMODE_RESCALE:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode
            self._rescaleArrows(spectrumView=spectrumView, objListView=objListView)
            # self._rescaleLabels(spectrumView=spectrumView,
            #                     objListView=objListView,
            #                     drawList=self._GLLabels[objListView])

            drawList.defineAliasedIndexVBO()

        elif drawList.renderMode == GLRENDERMODE_REBUILD:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode

            # find the correct scale to draw square pixels
            # don't forget to change when the axes change

            _, _, arrowType, arrowSize, arrowMinimum, arrowWidth, r, w = self._getArrowWidths(spectrumView)

            # change the ratio on resize
            drawList.refreshMode = GLREFRESHMODE_REBUILD
            drawList.drawMode = GL.GL_LINES
            drawList.fillMode = None

            # build the peaks VBO
            indexing = AttrDict()
            indexing.start = 0
            indexing.end = 0
            indexing.vertexPtr = 0
            indexing.vertexStart = 0
            indexing.objNum = 0

            pls = self.objectList(objListView)
            listCol = getAutoColourRgbRatio(objListView.arrowColour or GLDefs.DEFAULTCOLOUR, pls.spectrum,
                                            self.autoColour,
                                            getColours()[CCPNGLWIDGET_FOREGROUND])
            meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, pls.spectrum,
                                             self.autoColour,
                                             getColours()[CCPNGLWIDGET_FOREGROUND])
            meritEnabled = objListView.meritEnabled
            meritThreshold = objListView.meritThreshold

            spectrumFrequency = spectrum.spectrometerFrequencies
            strip = spectrumView.strip

            ind, vert = self._buildArrowsCount(spectrumView, objListView, drawList)
            if ind:
                for tCount, obj in enumerate(self.objects(pls)):

                    if meritEnabled and obj.figureOfMerit < meritThreshold:
                        cols = meritCol
                    else:
                        cols = listCol

                    self._insertArrowItem(strip, obj, cols, indexing, r, w,
                                          spectrumFrequency, arrowType, arrowSize, arrowMinimum, drawList,
                                          spectrumView, objListView, tCount)

            drawList.defineAliasedIndexVBO()

    def buildArrows(self):
        if self.strip.isDeleted:
            return

        for olv in [(spectrumView, objListView)
                    for spectrumView in self._ordering if not spectrumView.isDeleted
                    for objListView in self.listViews(spectrumView)
                    if objListView.isDeleted and self._objIsInVisiblePlanesCache.get(objListView)
                    ]:
            del self._objIsInVisiblePlanesCache[olv]

        objListViews = [(spectrumView, objListView) for spectrumView in self._ordering if not spectrumView.isDeleted
                        for objListView in self.listViews(spectrumView) if not objListView.isDeleted
                        ]

        for spectrumView, objListView in objListViews:
            if objListView.buildArrows:
                objListView.buildArrows = False

                # generate the planeVisibility list here - need to integrate with labels
                self._buildObjIsInVisiblePlanesList(spectrumView, objListView)

                # set the interior flags for rebuilding the GL-display
                if (dList := self._GLArrows.get(objListView)):
                    dList.renderMode = GLRENDERMODE_REBUILD

                self._buildArrows(spectrumView, objListView)

            elif (dList := self._GLArrows.get(objListView)) and dList.renderMode == GLRENDERMODE_RESCALE:
                self._buildArrows(spectrumView, objListView)

    def _getArrowWidths(self, spectrumView):
        """return the required r, w, symbolWidth for the current screen scaling.
        """
        arrowType = self.strip.arrowType
        arrowSize = self.strip.arrowSize
        arrowMinimum = self.strip.arrowMinimum**2  # a bit quicker
        symbolWidth = self.strip.symbolSize / 2.0

        specSet = self._spectrumSettings[spectrumView]
        vPP = specSet.ppmPerPoint
        delta = specSet.delta
        ar = specSet.axisDirection
        try:
            r = self._GLParent.symbolX * delta[0] * ar[0]  #self._GLParent.XDIRECTION  # np.sign(self._GLParent.pixelX)
            pr = r / vPP[0]
        except Exception:
            pr = r
        try:
            w = self._GLParent.symbolY * delta[1] * ar[1]  #self._GLParent.YDIRECTION  # np.sign(self._GLParent.pixelY)
            pw = w / vPP[1]
        except Exception:
            pw = w

        return r, w, arrowType, arrowSize, arrowMinimum, symbolWidth, pr, pw

    def _buildArrowsCountItem(self, strip, spectrumView, obj, arrowType, tCount):
        """return the number of indices and vertices for the object
        """
        # get visible/plane status
        _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

        # skip if not visible
        if not _isInPlane and not _isInFlankingPlane:
            return 0, 0

        ind = self._getArrowCount(planeIndex, obj, arrowType)
        # ind += self.extraIndicesCount(obj)
        extraVertices = 0  # self.extraVerticesCount(obj)

        vert = (self.LENARR + extraVertices)
        return ind, vert

    def _buildArrowsCount(self, spectrumView, objListView, drawList):
        """count the number of indices and vertices for the label list
        """

        pls = self.objectList(objListView)

        # reset the object pointers
        self._objectStore = {}

        indCount = 0
        vertCount = 0
        objCount = 0
        for tCount, obj in enumerate(self.objects(pls)):
            ind, vert = self._buildArrowsCountItem(self.strip, spectrumView, obj, self.strip.arrowType, tCount)
            indCount += ind
            vertCount += vert
            if ind:
                objCount += 1

        # set up arrays
        vc = vertCount * 4
        drawList.indices = np.empty(indCount, dtype=np.uint32)
        drawList.vertices = np.empty(vc, dtype=np.float32)
        drawList.colors = np.empty(vc, dtype=np.float32)
        drawList.attribs = np.empty(vc, dtype=np.float32)
        drawList.offsets = np.empty(vc, dtype=np.float32)
        drawList.pids = np.empty(objCount * GLDefs.LENPID, dtype=np.object_)
        drawList.numVertices = 0

        return indCount, vertCount

    def _insertArrowItem(self, strip, obj, listCol, indexing, r, w,
                         spectrumFrequency, arrowType, arrowSize, arrowMinimum, drawList, spectrumView, objListView,
                         tCount):
        """insert a single arrow to the end of the arrow list
        """

        # indexStart = indexing.start
        indexEnd = indexing.end
        objNum = indexing.objNum
        vertexPtr = indexing.vertexPtr
        vertexStart = indexing.vertexStart

        # get visible/plane status
        _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

        # skip if not visible
        if not _isInPlane and not _isInFlankingPlane:
            return

        specSet = self._spectrumSettings[spectrumView]
        vPPX, vPPY = specSet.ppmPerPoint
        delta = specSet.delta
        ar = specSet.axisDirection
        dims = specSet.dimensionIndices
        try:
            # fix the pointPositions
            objPos = obj.pointPositions
            pxy = (objPos[dims[0]] - 1, objPos[dims[1]] - 1)
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        # sx, sy = 0, 0
        rx, ry = 0, 0
        tnx, tny = 0.0, 0.0
        inr, inw = r, w
        try:
            pView = self.getViewFromListView(objListView, obj)
            tx, ty = pView.getIntersect((0, 0))
            pixX, pixY = objListView.pixelSize
            tx, ty = tx * delta[0] * ar[0], ty * delta[1] * ar[1]
            pixX, pixY = abs(pixX), abs(pixY)
            r, w = tx / vPPX, ty / vPPY  # pixel->points
            sx, sy = line_rectangle_intersection((0, 0),
                                                 (tx / vPPX, ty / vPPY),
                                                 (-inr, -inw),
                                                 (inr, inw))
            px, py = (tx - (sx * vPPX)) / pixX, (ty - (sy * vPPY)) / pixY
            _ll = px**2 + py**2
            if _ll < arrowMinimum:
                # line is too short
                sx, sy = 0, 0
                r, w = 0.0, 0.0
            else:
                # generate the end-vector perpendicular to the line
                rx, ry = -ty * pixX, tx * pixY  # back to pixels, rotated 90-degrees
                denom = (rx**2 + ry**2)**0.5
                rx = (arrowSize * rx / denom) * pixX / vPPX  # pixels->points for display
                ry = (arrowSize * ry / denom) * pixY / vPPY
                # generate the end-vector parallel to the line
                tnx, tny = tx / pixX, ty / pixY  # back to pixels, rotated 90-degrees
                denom = (tnx**2 + tny**2)**0.5
                tnx = (arrowSize * tnx / denom) * pixX / vPPX  # pixels->points for display
                tny = (arrowSize * tny / denom) * pixY / vPPY
        except Exception:
            sx, sy = 0, 0
            r, w = 0.0, 0.0

        if self._isSelected(obj):
            cols = self._GLParent.highlightColour[:3]
        elif _badPos:
            cols = [1.0, 0.2, 0.1]  # red for bad position
        else:
            cols = listCol

        try:
            # fix the lineWidths
            objLineWidths = obj.pointLineWidths
            pointLineWidths = (objLineWidths[dims[0]], objLineWidths[dims[1]])
        except Exception:
            pointLineWidths = (None, None)

        # frequency = (spectrumFrequency[dims[0]], spectrumFrequency[dims[1]])
        try:
            _alias = obj.aliasing
            alias = getAliasSetting(_alias[dims[0]], _alias[dims[1]])
        except Exception:
            alias = 0

        # draw an arrow
        _selected = False
        iCount = 0
        # unselected
        if _isInPlane or _isInFlankingPlane:
            iCount, _selected = self._makeArrowIndices(drawList, indexEnd, vertexStart, planeIndex, obj, arrowType)

        # add extra indices
        self._insertArrowItemVertices(_isInFlankingPlane, _isInPlane, _selected, cols, drawList, fade, iCount, indexing,
                                      obj, objNum, pxy, dims, planeIndex, r, vertexPtr, w, alias,
                                      sx, sy, rx, ry, tnx, tny)

    def _insertArrowItemVertices(self, _isInFlankingPlane, _isInPlane, _selected, cols,
                                 drawList, fade, iCount, indexing, obj,
                                 objNum, pxy, pIndex, planeIndex, r, vertexPtr, w, alias, sx, sy, rx, ry, tnx, tny):

        st, end = vertexPtr, vertexPtr + self.LENARR4
        drawList.vertices[st:end] = (pxy[0] + sx, pxy[1] + sy, alias, 0.0,
                                     pxy[0] + r + rx, pxy[1] + w + ry, alias, 0.0,
                                     pxy[0] + r - rx, pxy[1] + w - ry, alias, 0.0,
                                     pxy[0] + r, pxy[1] + w, alias, 0.0,
                                     pxy[0] + sx + rx + 2 * tnx, pxy[1] + sy + ry + 2 * tny, alias, 0.0,
                                     pxy[0] + sx - rx + 2 * tnx, pxy[1] + sy - ry + 2 * tny, alias, 0.0,
                                     )
        drawList.colors[st:end] = (*cols, fade) * self.LENARR
        drawList.attribs[st:end] = (alias, 0.0, 0.0, 0.0) * self.LENARR
        drawList.offsets[st:end] = (pxy[0], pxy[1], 0.0, 0.0) * self.LENARR

        # # add extra indices
        # extraIndices, extraIndexCount = self.insertExtraIndices(drawList, indexing.end + iCount, indexing.start + self.LENARR, obj)
        # # add extra vertices for the multiplet
        # extraVertices = self.insertExtraVertices(drawList, vertexPtr + self.LENARR2, pIndex, obj, p0, (*cols, fade), fade)
        extraIndices, extraIndexCount, extraVertices = 0, 0, 0

        # keep a pointer to the obj
        drawList.pids[objNum:objNum + GLDefs.LENPID] = (obj, drawList.numVertices, (self.LENARR + extraVertices),
                                                        _isInPlane, _isInFlankingPlane, _selected,
                                                        indexing.end, indexing.end + iCount + extraIndices,
                                                        planeIndex, 0, 0, 0)

        indexing.start += (self.LENARR + extraIndexCount)
        indexing.end += (iCount + extraIndices)  # len(drawList.indices)
        drawList.numVertices += (self.LENARR + extraVertices)
        indexing.objNum += GLDefs.LENPID
        indexing.vertexPtr += (4 * (self.LENARR + extraVertices))
        indexing.vertexStart += (self.LENARR + extraVertices)

    def drawArrows(self, spectrumView):
        """Draw the arrows to the screen
        """
        if self.strip.isDeleted:
            return

        for objListView, specView in self._visibleListViews:
            if specView == spectrumView and not objListView.isDeleted and objListView in self._GLArrows.keys():
                self._GLArrows[objListView].drawAliasedIndexVBO()

    def _rescaleArrowOffsets(self, r, w):
        return np.array([0, 0, 0, 0,
                         r, w, 0, 0,
                         r, w, 0, 0,
                         0, 0, 0, 0,
                         r, w, 0, 0,
                         r, w, 0, 0], np.float32), self.LENARR4

    def _rescaleArrows(self, spectrumView, objListView):
        """rescale arrows when the screen dimensions change
        """
        return

        # drawList = self._GLArrows[objListView]
        #
        # if not drawList.numVertices:
        #     return
        #
        # # if drawList.refreshMode == GLREFRESHMODE_REBUILD:
        # _, _, arrowType, arrowSize, arrowMinimum, arrowWidth, r, w = self._getArrowWidths(spectrumView)
        #
        # vPP = spectrumView.spectrum.ppmPerPoints
        # dOrder = spectrumView.dimensionIndices
        # pView = drawList.pids[0].getPeakView(objListView)
        # try:
        #     tx, ty = pView.textOffset
        #     pixX, pixY = objListView.pixelSize
        #     r, w = tx * abs(pixX) / vPP[dOrder[0]], ty * abs(pixY) / vPP[dOrder[1]]
        # except Exception:
        #     r, w = 0.0, 0.0
        # offsets, offLen = self._rescaleArrowOffsets(r, w)
        #
        # for pp in range(0, len(drawList.pids), GLDefs.LENPID):
        #     indexStart = 4 * drawList.pids[pp + 1]
        #     drawList.vertices[indexStart:indexStart + offLen] = \
        #         drawList.offsets[indexStart:indexStart + offLen] + offsets

    def _updateHighlightedArrows(self, spectrumView, objListView):
        """update the highlighted arrows
        """
        # strip = self.strip
        # symbolType = strip.symbolType

        drawList = self._GLArrows[objListView]
        drawList.indices = np.empty(0, dtype=np.uint32)

        indexStart = 0
        indexEnd = 0
        vertexStart = 0

        pls = self.objectList(objListView)
        listCol = getAutoColourRgbRatio(objListView.arrowColour or GLDefs.DEFAULTCOLOUR, pls.spectrum, self.autoColour,
                                        getColours()[CCPNGLWIDGET_FOREGROUND])
        meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, pls.spectrum, self.autoColour,
                                         getColours()[CCPNGLWIDGET_FOREGROUND])
        meritEnabled = objListView.meritEnabled
        meritThreshold = objListView.meritThreshold

        _, _, arrowType, arrowSize, arrowMinimum, arrowWidth, r, w = self._getArrowWidths(spectrumView)

        _indexCount = 0
        for pp in range(0, len(drawList.pids), GLDefs.LENPID):

            # check whether the peaks still exists
            obj = drawList.pids[pp]
            offset = drawList.pids[pp + 1]
            numPoints = drawList.pids[pp + 2]

            if not obj.isDeleted:
                _selected = False
                iCount = 0

                # get visible/plane status
                _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

                if _isInPlane or _isInFlankingPlane:
                    iCount, _selected = self._appendArrowIndices(drawList, vertexStart, planeIndex, obj, arrowType)

                    if _selected:
                        cols = self._GLParent.highlightColour[:3]
                    elif obj.pointPositions and None in obj.pointPositions:
                        cols = [1.0, 0.2, 0.1]  # red if the position is bad
                    else:
                        if meritEnabled and obj.figureOfMerit < meritThreshold:
                            cols = meritCol
                        else:
                            cols = listCol

                    # _indexCount, extraIndices = self.appendExtraIndices(drawList, indexStart + self.LENARR, obj)
                    drawList.colors[offset * 4:(offset + self.ARROWCOLOURS) * 4] = (*cols,
                                                                                    fade) * self.ARROWCOLOURS  #numPoints

                # list MAY contain out of plane peaks
                drawList.pids[pp + 3:pp + 9] = (_isInPlane, _isInFlankingPlane, _selected,
                                                indexEnd, indexEnd + iCount + _indexCount, planeIndex)
                indexEnd += (iCount + _indexCount)

            indexStart += numPoints
            vertexStart += numPoints

        drawList.pushIndexVBOIndices()
        drawList.pushTextArrayVBOColour()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Handle notifiers
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _deleteSymbol(self, obj, parentList, spectrum):
        pls = parentList  # self.objectList(obj)
        if pls:
            # spectrum = pls.spectrum

            for objListView in self.listViews(pls):
                if objListView in self._GLSymbols.keys():
                    for spectrumView in spectrum.spectrumViews:
                        if spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            self._removeSymbol(spectrumView, objListView, obj)
                            # self._updateHighlightedSymbols(spectrumView, objListView)
                            self._GLSymbols[objListView].pushAliasedIndexVBO()
                            break

    # from ccpn.util.decorators import profile
    # @profile
    def _createSymbol(self, obj):
        pls = self.objectList(obj)
        if pls:
            spectrum = pls.spectrum

            for objListView in self.listViews(pls):
                if objListView in self._GLSymbols.keys():
                    for spectrumView in spectrum.spectrumViews:
                        if spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            self._appendSymbol(spectrumView, objListView, obj)
                            # self._updateHighlightedSymbols(spectrumView, objListView)
                            self._GLSymbols[objListView].pushAliasedIndexVBO()
                            break

    def _changeSymbol(self, obj):
        pls = self.objectList(obj)
        if pls:
            spectrum = pls.spectrum

            for objListView in self.listViews(pls):
                if objListView in self._GLSymbols.keys():
                    for spectrumView in spectrum.spectrumViews:
                        if spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            self._removeSymbol(spectrumView, objListView, obj)
                            self._appendSymbol(spectrumView, objListView, obj)
                            # self._updateHighlightedSymbols(spectrumView, objListView)
                            self._GLSymbols[objListView].pushAliasedIndexVBO()
                            break

    def _deleteLabel(self, obj, parentList, spectrum):
        for pll in self._GLLabels.keys():
            drawList = self._GLLabels[pll]

            for drawStr in drawList.stringList:
                if drawStr.stringObject == obj:
                    drawList.stringList.remove(drawStr)
                    break

    def _changeLabel(self, obj):
        # NOTE:ED - not the nicest way of changing a label - needs work
        self._deleteLabel(obj, None, None)
        self._createLabel(obj)

    def _createLabel(self, obj):
        pls = self.objectList(obj)
        if pls:
            spectrum = pls.spectrum

            for objListView in self.listViews(pls):
                if objListView in self._GLLabels.keys():
                    for spectrumView in spectrum.spectrumViews:
                        if spectrumView in self._ordering:  # strip.spectrumViews:

                            if spectrumView.isDeleted:
                                continue

                            drawList = self._GLLabels[objListView]
                            self._appendLabel(spectrumView, objListView, drawList.stringList, obj)
                            self._rescaleLabels(spectrumView, objListView, drawList)

    def _getSymbolWidths(self, spectrumView):
        """return the required r, w, symbolWidth for the current screen scaling.
        """
        symbolType = self.strip.symbolType
        symbolWidth = self.strip.symbolSize / 2.0

        specSet = self._spectrumSettings[spectrumView]
        vPP = specSet.ppmPerPoint
        delta = specSet.delta
        ar = specSet.axisDirection
        try:
            r = self._GLParent.symbolX * delta[0] * ar[0]  # change from pixels to ppm
            pr = r / vPP[0]
        except Exception:
            pr = r
        try:
            w = self._GLParent.symbolY * delta[1] * ar[1]
            pw = w / vPP[1]
        except Exception:
            pw = w

        return r, w, symbolType, symbolWidth, pr, pw

    def _getLabelOffsets(self, spectrumView, tx, ty):
        """return the required r, w, symbolWidth for the current screen scaling.
        """
        symbolType = self.strip.symbolType
        symbolWidth = self.strip.symbolSize / 2.0

        specSet = self._spectrumSettings[spectrumView]
        vPP = specSet.ppmPerPoint
        delta = specSet.delta
        ar = specSet.axisDirection
        # try:
        #     r = tx * abs(self._GLParent.pixelX)  # change from pixels to ppm
        #     pr = r / vPP[pIndex[0]]  # change from ppm to points
        # except Exception:
        #     pr = r
        # try:
        #     w = ty * abs(self._GLParent.pixelY)
        #     pw = w / vPP[pIndex[1]]
        # except Exception:
        #     pw = w
        try:
            r = tx * delta[0] * ar[0]  # change from pixels to ppm
            pr = r / vPP[0]  # change from ppm to points
        except Exception:
            pr = r
        try:
            w = ty * delta[1] * ar[1]
            pw = w / vPP[1]
        except Exception:
            pw = w
        return r, w, symbolType, symbolWidth, pr, pw

    def _appendLabel(self, spectrumView, objListView, stringList, obj):
        """Append a new label to the end of the list
        """
        if obj.isDeleted:
            return
        if stringList and obj in (sl.stringObject for sl in stringList):
            return

        # spectrum = spectrumView.spectrum
        # spectrumFrequency = spectrum.spectrometerFrequencies
        # pls = peakListView.peakList
        pls = self.objectList(objListView)

        pIndex = self._spectrumSettings[spectrumView].dimensionIndices
        try:
            # fix the pointPositions
            objPos = obj.pointPositions
            pxy = (objPos[pIndex[0]] - 1, objPos[pIndex[1]] - 1)
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        try:
            # fix the lineWidths
            objLineWidths = obj.pointLineWidths
            pointLineWidths = (objLineWidths[pIndex[0]], objLineWidths[pIndex[1]])
        except Exception:
            pointLineWidths = (None, None)

        # frequency = (spectrumFrequency[pIndex[0]], spectrumFrequency[pIndex[1]])
        try:
            _alias = obj.aliasing
            alias = getAliasSetting(_alias[pIndex[0]], _alias[pIndex[1]])
        except Exception:
            alias = 0

        stringOffset = None
        if textOffset := obj.getTextOffset(objListView):
            tx, ty = textOffset
            _, _, symbolType, symbolWidth, r, w = self._getLabelOffsets(spectrumView, tx, ty)
        else:
            _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

            if symbolType in (1, 2):
                # put to the top-right corner of the lineWidth
                if pointLineWidths[0] and pointLineWidths[1]:
                    r = GLDefs.STRINGSCALE * 0.5 * pointLineWidths[0]  #/ frequency[0]
                    w = GLDefs.STRINGSCALE * 0.5 * pointLineWidths[1]  #/ frequency[1]
                    stringOffset = (r, w)
                else:
                    r = GLDefs.STRINGSCALE * r
                    w = GLDefs.STRINGSCALE * w

        if True:  # pIndex:
            # get visible/plane status
            _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

            # skip if not visible
            if not _isInPlane and not _isInFlankingPlane:
                return

            if self._isSelected(obj):
                listCol = self._GLParent.highlightColour[:3]
            elif _badPos:
                listCol = [1.0, 0.2, 0.1]  # red if the position is bad
            else:
                if objListView.meritEnabled and obj.figureOfMerit < objListView.meritThreshold:
                    objCol = objListView.meritColour or GLDefs.DEFAULTCOLOUR
                else:
                    objCol = objListView.textColour or GLDefs.DEFAULTCOLOUR

                listCol = getAutoColourRgbRatio(objCol, pls.spectrum,
                                                self.autoColour,
                                                getColours()[CCPNGLWIDGET_FOREGROUND])

            text = self.getLabelling(obj, self._GLParent)

            newString = GLString(text=text,
                                 font=self._GLParent.getSmallFont(),
                                 x=pxy[0], y=pxy[1],
                                 ox=r, oy=w,
                                 colour=(*listCol, fade),
                                 GLContext=self._GLParent,
                                 obj=obj, clearArrays=False,
                                 alias=alias)
            newString.stringOffset = stringOffset
            stringList.append(newString)

            try:
                # update the size in the peakView
                # pView = obj.getPeakView(objListView)
                pView = self.getViewFromListView(objListView, obj)
                pView.size = (newString.width, newString.height)
            except Exception as es:
                pass

    def _fillLabels(self, spectrumView, objListView, pls, objectList):
        """Append all labels to the new list
        """
        # use the first object for referencing
        obj = objectList(pls)[0]

        pIndex = self._spectrumSettings[spectrumView].dimensionIndices
        try:
            # fix the pointPositions
            objPos = obj.pointPositions
            pxy = (objPos[pIndex[0]] - 1, objPos[pIndex[1]] - 1)
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        try:
            # fix the lineWidths
            objLineWidths = obj.pointLineWidths
            pointLineWidths = (objLineWidths[pIndex[0]], objLineWidths[pIndex[1]])
        except Exception:
            pointLineWidths = (None, None)

        try:
            _alias = obj.aliasing
            alias = getAliasSetting(_alias[pIndex[0]], _alias[pIndex[1]])
        except Exception:
            alias = 0

        stringOffset = None
        if textOffset := obj.getTextOffset(objListView):
            tx, ty = textOffset
            _, _, symbolType, symbolWidth, r, w = self._getLabelOffsets(spectrumView, tx, ty)
        else:
            _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

            if symbolType in (1, 2):
                # put to the top-right corner of the lineWidth
                if pointLineWidths[0] and pointLineWidths[1]:
                    r = - GLDefs.STRINGSCALE * 0.5 * pointLineWidths[0]  #/ frequency[0]
                    w = - GLDefs.STRINGSCALE * 0.5 * pointLineWidths[1]  #/ frequency[1]
                    stringOffset = (r, w)
                else:
                    r = GLDefs.STRINGSCALE * r
                    w = GLDefs.STRINGSCALE * w

        if True:  # pIndex:
            # get visible/plane status
            _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

            # skip if not visible
            if not _isInPlane and not _isInFlankingPlane:
                return

            if self._isSelected(obj):
                listCol = self._GLParent.highlightColour[:3]
            elif _badPos:
                listCol = [1.0, 0.2, 0.1]  # red if the position is bad
            else:
                if objListView.meritEnabled and obj.figureOfMerit < objListView.meritThreshold:
                    objCol = objListView.meritColour or GLDefs.DEFAULTCOLOUR
                else:
                    objCol = objListView.textColour or GLDefs.DEFAULTCOLOUR

                listCol = getAutoColourRgbRatio(objCol, pls.spectrum,
                                                self.autoColour,
                                                getColours()[CCPNGLWIDGET_FOREGROUND])

            text = self.getLabelling(obj, self._GLParent)

            outString = GLString(text=text,
                                 font=self._GLParent.getSmallFont(),
                                 x=pxy[0], y=pxy[1],
                                 ox=r, oy=w,
                                 colour=(*listCol, fade),
                                 GLContext=self._GLParent,
                                 obj=obj, clearArrays=False,
                                 alias=alias)
            outString.stringOffset = stringOffset

            try:
                # pView = obj.getPeakView(objListView)
                pView = self.getViewFromListView(objListView, obj)
                pView.size = (outString.width, outString.height)
            except Exception as es:
                pass

            return outString

    def _removeSymbol(self, spectrumView, objListView, delObj):
        """Remove a symbol from the list
        """
        symbolType = self.strip.symbolType

        drawList = self._GLSymbols[objListView]
        self.objIsInVisiblePlanesRemove(spectrumView, delObj)  # probably only needed in create/change

        indexOffset = 0
        numPoints = 0

        pp = 0
        while (pp < len(drawList.pids)):
            # check whether the peaks still exists
            obj = drawList.pids[pp]

            if obj == delObj:
                offset = drawList.pids[pp + 1]
                numPoints = drawList.pids[pp + 2]

                if symbolType != 0 and symbolType != 3:  # not a cross/plus
                    numPoints = 2 * numPoints + 5

                # _isInPlane = drawList.pids[pp + 3]
                # _isInFlankingPlane = drawList.pids[pp + 4]
                # _selected = drawList.pids[pp + 5]
                indexStart = drawList.pids[pp + 6]
                indexEnd = drawList.pids[pp + 7]
                indexOffset = indexEnd - indexStart

                st, end = 4 * offset, 4 * (offset + numPoints)
                drawList.indices = np.delete(drawList.indices, np.s_[indexStart:indexEnd])
                drawList.vertices = np.delete(drawList.vertices, np.s_[st: end])
                drawList.attribs = np.delete(drawList.attribs, np.s_[st: end])
                drawList.offsets = np.delete(drawList.offsets, np.s_[st: end])
                drawList.colors = np.delete(drawList.colors, np.s_[st: end])

                drawList.pids = np.delete(drawList.pids, np.s_[pp:pp + GLDefs.LENPID])
                drawList.numVertices -= numPoints

                # subtract the offset from all the higher indices to account for the removed points
                drawList.indices[np.where(drawList.indices >= offset)] -= numPoints
                break

            else:
                pp += GLDefs.LENPID

        # clean up the rest of the list
        while (pp < len(drawList.pids)):
            drawList.pids[pp + 1] -= numPoints
            drawList.pids[pp + 6] -= indexOffset
            drawList.pids[pp + 7] -= indexOffset
            pp += GLDefs.LENPID

    _squareSymbol = (
    (np.array((0, 1, 2, 3), dtype=np.uint32), np.array((0, 1, 2, 3, 0, 2, 2, 1, 0, 3, 3, 1), dtype=np.uint32)),
    (np.array((0, 4, 4, 3, 3, 0), dtype=np.uint32), np.array((0, 4, 4, 3, 3, 0, 0, 2, 2, 1, 3, 1), dtype=np.uint32)),
    (np.array((2, 4, 4, 1, 1, 2), dtype=np.uint32), np.array((2, 4, 4, 1, 1, 2, 0, 2, 0, 3, 3, 1), dtype=np.uint32)))
    _squareSymbolLen = tuple(tuple(len(sym) for sym in symList) for symList in _squareSymbol)

    def _getSquareSymbolCount(self, planeIndex, obj):
        """returns the number of indices required for the symbol based on the planeIndex
        type of planeIndex - currently 0/1/2 indicating whether normal, infront or behind
        currently visible planes
        """
        return self._squareSymbolLen[planeIndex % 3][self._isSelected(obj)]

    def _makeSquareSymbol(self, drawList, indexEnd, vertexStart, planeIndex, obj):
        """Make a new square symbol based on the planeIndex type.
        """
        _selected = self._isSelected(obj)
        _indices = self._squareSymbol[planeIndex % 3][_selected] + vertexStart
        iCount = len(_indices)
        drawList.indices[indexEnd:indexEnd + iCount] = _indices

        return iCount, _selected

    def _appendSquareSymbol(self, drawList, vertexStart, planeIndex, obj):
        """Append a new square symbol based on the planeIndex type.
        """
        _selected = self._isSelected(obj)
        _indices = self._squareSymbol[planeIndex % 3][_selected] + vertexStart
        iCount = len(_indices)
        drawList.indices = np.append(drawList.indices, _indices)

        return iCount, _selected

    _plusSymbol = (
    (np.array((5, 6, 7, 8), dtype=np.uint32), np.array((5, 6, 7, 8, 0, 2, 2, 1, 0, 3, 3, 1), dtype=np.uint32)),
    (np.array((6, 4, 4, 5, 4, 8), dtype=np.uint32),
     np.array((6, 4, 4, 5, 4, 8, 0, 2, 2, 1, 3, 1, 0, 3), dtype=np.uint32)),
    (np.array((6, 4, 4, 5, 4, 7), dtype=np.uint32),
     np.array((6, 4, 4, 5, 4, 7, 0, 2, 2, 1, 3, 1, 0, 3), dtype=np.uint32)))
    _plusSymbolLen = tuple(tuple(len(sym) for sym in symList) for symList in _plusSymbol)

    def _getPlusSymbolCount(self, planeIndex, obj):
        """returns the number of indices required for the symbol based on the planeIndex
        type of planeIndex - currently 0/1/2 indicating whether normal, infront or behind
        currently visible planes
        """
        return self._plusSymbolLen[planeIndex % 3][self._isSelected(obj)]

    def _makePlusSymbol(self, drawList, indexEnd, vertexStart, planeIndex, obj):
        """Make a new plus symbol based on the planeIndex type.
        """
        _selected = self._isSelected(obj)
        _indices = self._plusSymbol[planeIndex % 3][_selected] + vertexStart
        iCount = len(_indices)
        drawList.indices[indexEnd:indexEnd + iCount] = _indices

        return iCount, _selected

    def _appendPlusSymbol(self, drawList, vertexStart, planeIndex, obj):
        """Append a new plus symbol based on the planeIndex type.
        """
        _selected = self._isSelected(obj)
        _indices = self._plusSymbol[planeIndex % 3][_selected] + vertexStart
        iCount = len(_indices)
        drawList.indices = np.append(drawList.indices, _indices)

        return iCount, _selected

    def _insertSymbolItem(self, strip, obj, listCol, indexing, r, w,
                          spectrumFrequency, symbolType, drawList, spectrumView, tCount):
        """insert a single symbol to the end of the symbol list
        """

        # indexStart = indexing.start
        indexEnd = indexing.end
        objNum = indexing.objNum
        vertexPtr = indexing.vertexPtr
        vertexStart = indexing.vertexStart

        # get visible/plane status
        _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

        # skip if not visible
        if not _isInPlane and not _isInFlankingPlane:
            return

        pIndex = self._spectrumSettings[spectrumView].dimensionIndices
        try:
            _alias = obj.aliasing
            alias = getAliasSetting(_alias[pIndex[0]], _alias[pIndex[1]])
        except Exception:
            alias = 0

        try:
            # fix the pointPositions
            objPos = obj.pointPositions
            pxy = (objPos[pIndex[0]] - 1, objPos[pIndex[1]] - 1)
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        if self._isSelected(obj):
            cols = self._GLParent.highlightColour[:3]
        elif _badPos:
            cols = [1.0, 0.2, 0.1]  # red for bad position
        else:
            cols = listCol

        try:
            # fix the lineWidths
            objLineWidths = obj.pointLineWidths
            pointLineWidths = (objLineWidths[pIndex[0]], objLineWidths[pIndex[1]])
        except Exception:
            pointLineWidths = (None, None)

        # frequency = (spectrumFrequency[pIndex[0]], spectrumFrequency[pIndex[1]])
        if False:  # not pIndex:
            return

        else:
            if symbolType == 0 or symbolType == 3:

                # draw a cross
                # keep the cross square at 0.1ppm

                _selected = False
                iCount = 0
                # unselected
                if _isInPlane or _isInFlankingPlane:
                    if symbolType == 0:  # cross
                        iCount, _selected = self._makeSquareSymbol(drawList, indexEnd, vertexStart, planeIndex, obj)
                    else:
                        iCount, _selected = self._makePlusSymbol(drawList, indexEnd, vertexStart, planeIndex, obj)

                # add extra indices
                self._insertSymbolItemVertices(_isInFlankingPlane, _isInPlane, _selected, cols, drawList, fade, iCount,
                                               indexing, obj, objNum, pxy, pIndex, planeIndex,
                                               r, vertexPtr, w, alias)

            elif symbolType == 1:  # draw an ellipse at lineWidth

                if pointLineWidths[0] and pointLineWidths[1]:
                    # draw 24 connected segments
                    r = 0.5 * pointLineWidths[0]
                    w = 0.5 * pointLineWidths[1]
                    numPoints = 24
                    angPlus = 2.0 * np.pi
                    skip = 1
                else:
                    # draw 12 disconnected segments (dotted)
                    # r = symbolWidth
                    # w = symbolWidth
                    numPoints = 12
                    angPlus = np.pi
                    skip = 2

                np2 = 2 * numPoints
                ang = list(range(numPoints))
                _selected = False

                # # need to subclass the different point types a lot better :|
                # _numPoints = 24
                # _angPlus = 2.0 * np.pi
                # _skip = 1
                # _ang = list(range(numPoints))
                # _indicesLineWidth = np.array(tuple(val for an in _ang for val in ((2 * an), (2 * an) + 1)), dtype=np.uint32)
                # _np1 = len(_indicesLineWidth)
                # _indicesLineWidthSelect = _indicesLineWidth + np.array((_np1, _np1 + 2,
                #                                                         _np1 + 2, _np1 + 1,
                #                                                         _np1, _np1 + 3,
                #                                                         _np1 + 3, _np1 + 1), dtype=np.uint32)
                # _np2 = len(_indicesLineWidthSelect)
                #
                # _vertexLineWidth = np.array(tuple(val for an in _ang
                #                                   for val in (- r * math.sin(_skip * an * _angPlus / _numPoints),
                #                                               - w * math.cos(_skip * an * _angPlus / _numPoints),
                #                                               - r * math.sin((_skip * an + 1) * _angPlus / _numPoints),
                #                                               - w * math.cos((_skip * an + 1) * _angPlus / _numPoints))), dtype=np.float32) + \
                #                    np.array((- r, - w, + r, + w, + r, - w, - r, + w, 0, 0), dtype=np.float32)
                # _vp1 = len(_vertexLineWidth)
                # _vp2 = _vp1 // 2
                #
                # if self._isSelected(obj):
                #     iCount = _np1
                #     drawList.indices[indexEnd:indexEnd + _np1] = _indicesLineWidth + indexStart
                # else:
                #     iCount = _np2
                #     drawList.indices[indexEnd:indexEnd + _np2] = _indicesLineWidthSelect + indexStart
                #
                # _pos = (p0[0], p0[1]) * _vp2
                # drawList.vertices[vertexPtr:vertexPtr + _vp1] = _vertexLineWidth + _pos

                _vertexStart = indexing.vertexStart
                if _isInPlane or _isInFlankingPlane:
                    drawList.indices[indexEnd:indexEnd + np2] = tuple(val for an in ang
                                                                      for val in (_vertexStart + (2 * an),
                                                                                  _vertexStart + (2 * an) + 1))

                    iCount = np2
                    if self._isSelected(obj):
                        _selected = True
                        drawList.indices[indexEnd + np2:indexEnd + np2 + 8] = (
                            _vertexStart + np2, _vertexStart + np2 + 2,
                            _vertexStart + np2 + 2, _vertexStart + np2 + 1,
                            _vertexStart + np2, _vertexStart + np2 + 3,
                            _vertexStart + np2 + 3, _vertexStart + np2 + 1)
                        iCount += 8

                # add extra indices
                extraIndices = 0  #self.appendExtraIndices(drawList, indexStart + np2, obj)

                # draw an ellipse at lineWidth
                st, end, step, xtra = vertexPtr, vertexPtr + (4 * np2), np2 + 5, 20
                # don't include the extra 5 points here
                drawList.vertices[st:end] = tuple(val for an in ang
                                                  for val in (pxy[0] - r * math.sin(skip * an * angPlus / numPoints),
                                                              pxy[1] - w * math.cos(skip * an * angPlus / numPoints),
                                                              alias, 0.0,
                                                              pxy[0] - r * math.sin(
                                                                      (skip * an + 1) * angPlus / numPoints),
                                                              pxy[1] - w * math.cos(
                                                                      (skip * an + 1) * angPlus / numPoints),
                                                              alias, 0.0)
                                                  )
                drawList.vertices[end:end + xtra] = (pxy[0] - r, pxy[1] - w, alias, 0.0,
                                                     pxy[0] + r, pxy[1] + w, alias, 0.0,
                                                     pxy[0] + r, pxy[1] - w, alias, 0.0,
                                                     pxy[0] - r, pxy[1] + w, alias, 0.0,
                                                     pxy[0], pxy[1], alias, 0.0,
                                                     )

                drawList.colors[st:end + xtra] = (*cols, fade) * step
                drawList.attribs[st:end + xtra] = (alias, 0.0, 0.0, 0.0) * step
                drawList.offsets[st:end + xtra] = (pxy[0], pxy[1], 0.0, 0.0) * step

                # add extra vertices
                extraVertices = 0  #self.appendExtraVertices(drawList, obj, p0, [*cols, fade], fade)

                # keep a pointer to the obj
                drawList.pids[objNum:objNum + GLDefs.LENPID] = (obj, drawList.numVertices, (numPoints + extraVertices),
                                                                _isInPlane, _isInFlankingPlane, _selected,
                                                                indexEnd, indexEnd + iCount + extraIndices,
                                                                planeIndex, 0, 0, 0)

                indexing.start += (step + extraIndices)
                indexing.end += (iCount + extraIndices)  # len(drawList.indices)
                drawList.numVertices += (step + extraVertices)
                indexing.objNum += GLDefs.LENPID
                indexing.vertexPtr += (4 * (step + extraVertices))
                indexing.vertexStart += (step + extraVertices)

            elif symbolType == 2:  # draw a filled ellipse at lineWidth

                if pointLineWidths[0] and pointLineWidths[1]:
                    # draw 24 connected segments
                    r = 0.5 * pointLineWidths[0]  # / frequency[0]
                    w = 0.5 * pointLineWidths[1]  # / frequency[1]
                    numPoints = 24
                    angPlus = 2 * np.pi
                    skip = 1
                else:
                    # draw 12 disconnected segments (dotted)
                    # r = symbolWidth
                    # w = symbolWidth
                    numPoints = 12
                    angPlus = 1.0 * np.pi
                    skip = 2

                np2 = 2 * numPoints
                ang = list(range(numPoints))
                _selected = False

                _vertexStart = indexing.vertexStart
                if _isInPlane or _isInFlankingPlane:
                    drawList.indices[indexEnd:indexEnd + 3 * numPoints] = tuple(val for an in ang
                                                                                for val in (_vertexStart + (2 * an),
                                                                                            _vertexStart + (2 * an) + 1,
                                                                                            _vertexStart + np2 + 4))
                    iCount = 3 * numPoints

                # add extra indices
                extraIndices = 0  #self.appendExtraIndices(drawList, indexStart + np2 + 4, obj)

                # draw an ellipse at lineWidth
                st, end, step, xtra = vertexPtr, vertexPtr + (4 * np2), np2 + 5, 20
                drawList.vertices[st:end] = tuple(val for an in ang
                                                  for val in (pxy[0] - r * math.sin(skip * an * angPlus / numPoints),
                                                              pxy[1] - w * math.cos(skip * an * angPlus / numPoints),
                                                              alias, 0.0,
                                                              pxy[0] - r * math.sin(
                                                                      (skip * an + 1) * angPlus / numPoints),
                                                              pxy[1] - w * math.cos(
                                                                      (skip * an + 1) * angPlus / numPoints),
                                                              alias, 0.0)
                                                  )
                drawList.vertices[end:end + xtra] = (pxy[0] - r, pxy[1] - w, alias, 0.0,
                                                     pxy[0] + r, pxy[1] + w, alias, 0.0,
                                                     pxy[0] + r, pxy[1] - w, alias, 0.0,
                                                     pxy[0] - r, pxy[1] + w, alias, 0.0,
                                                     pxy[0], pxy[1], alias, 0.0,
                                                     )

                drawList.colors[st:end + xtra] = (*cols, fade) * step
                drawList.attribs[st:end + xtra] = (alias, 0.0, 0.0, 0.0) * step
                drawList.offsets[st:end + xtra] = (pxy[0], pxy[1], 0.0, 0.0) * step

                # add extra vertices for the multiplet
                extraVertices = 0  #self.appendExtraVertices(drawList, obj, p0, [*cols, fade], fade)

                # keep a pointer to the obj
                drawList.pids[objNum:objNum + GLDefs.LENPID] = (obj, drawList.numVertices, (numPoints + extraVertices),
                                                                _isInPlane, _isInFlankingPlane, _selected,
                                                                indexEnd, indexEnd + iCount + extraIndices,
                                                                planeIndex, 0, 0, 0)

                indexing.start += (step + extraIndices)
                indexing.end += (iCount + extraIndices)  # len(drawList.indices)
                drawList.numVertices += (step + extraVertices)
                indexing.objNum += GLDefs.LENPID
                indexing.vertexPtr += (4 * (step + extraVertices))
                indexing.vertexStart += (step + extraVertices)

            else:
                raise ValueError('GL Error: bad symbol type')

    def _insertSymbolItemVertices(self, _isInFlankingPlane, _isInPlane, _selected, cols,
                                  drawList, fade, iCount, indexing, obj,
                                  objNum, pxy, pIndex, planeIndex, r, vertexPtr, w, alias):

        st, end = vertexPtr, vertexPtr + self.LENSQ4
        drawList.vertices[st:end] = (pxy[0] - r, pxy[1] - w, alias, 0.0,
                                     pxy[0] + r, pxy[1] + w, alias, 0.0,
                                     pxy[0] + r, pxy[1] - w, alias, 0.0,
                                     pxy[0] - r, pxy[1] + w, alias, 0.0,
                                     pxy[0], pxy[1], alias, 0.0,
                                     pxy[0], pxy[1] - w, alias, 0.0,
                                     pxy[0], pxy[1] + w, alias, 0.0,
                                     pxy[0] + r, pxy[1], alias, 0.0,
                                     pxy[0] - r, pxy[1], alias, 0.0,
                                     )
        drawList.colors[st:end] = (*cols, fade) * self.LENSQ
        drawList.attribs[st:end] = (alias, 0.0, 0.0, 0.0) * self.LENSQ
        drawList.offsets[st:end] = (pxy[0], pxy[1], 0.0, 0.0) * self.LENSQ

        # add extra indices
        extraIndices, extraIndexCount = self.insertExtraIndices(drawList, indexing.end + iCount,
                                                                indexing.start + self.LENSQ, obj)
        # add extra vertices for the multiplet
        extraVertices = self.insertExtraVertices(drawList, vertexPtr + self.LENSQ4, pIndex, obj, pxy,
                                                (*cols, fade), fade)
        # keep a pointer to the obj
        drawList.pids[objNum:objNum + GLDefs.LENPID] = (obj, drawList.numVertices, (self.LENSQ + extraVertices),
                                                        _isInPlane, _isInFlankingPlane, _selected,
                                                        indexing.end, indexing.end + iCount + extraIndices,
                                                        planeIndex, 0, 0, 0)

        indexing.start += (self.LENSQ + extraIndexCount)
        indexing.end += (iCount + extraIndices)  # len(drawList.indices)
        drawList.numVertices += (self.LENSQ + extraVertices)
        indexing.objNum += GLDefs.LENPID
        indexing.vertexPtr += (4 * (self.LENSQ + extraVertices))
        indexing.vertexStart += (self.LENSQ + extraVertices)

    # NOTE:ED - new pre-defined indices/vertex lists
    # # indices for lineWidth symbols, not selected/selected in different number of points
    # _lineWidthIndices = {numPoints: ((np.append(np.array(tuple(val for an in range(numPoints) for val in ((2 * an), (2 * an) + 1)), dtype=np.uint32),
    #                                             np.array((0, 1, 2, 3), dtype=np.uint32)),
    #                                   np.append(np.array(tuple(val for an in range(numPoints) for val in ((2 * an), (2 * an) + 1)), dtype=np.uint32),
    #                                             np.array((0, 1, 2, 3, 0, 2, 2, 1, 0, 3, 3, 1), dtype=np.uint32))))
    #                      for numPoints in (12, 18, 24, 36)}
    #
    # # vertices for lineWidth symbols
    # _lineWidthVertices = {numPoints: np.append(np.array(tuple(val for an in range(numPoints)
    #                                                           for val in (- math.sin(skip * an * angPlus / numPoints),
    #                                                                       - math.cos(skip * an * angPlus / numPoints),
    #                                                                       - math.sin((skip * an + 1) * angPlus / numPoints),
    #                                                                       - math.cos((skip * an + 1) * angPlus / numPoints)))),
    #                                            np.array((-1, -1, 1, 1, 1, -1, -1, 1, 0, 0), dtype=np.float32))
    #                       for numPoints, skip, angPlus in ((12),
    #                                                        (18),
    #                                                        (24),
    #                                                        (36))}

    def _appendSymbolItem(self, strip, obj, listCol, indexing, r, w,
                          spectrumFrequency, symbolType, drawList, spectrumView):
        """append a single symbol to the end of the symbol list
        """
        # indexStart, indexEnd are indexes into the drawList.indices for the indices for this symbol
        # indexStart = indexing.start  # indexList[0]
        indexEnd = indexing.end  #indexList[1]
        vertexStart = indexing.vertexStart

        # get visible/plane status
        _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

        # skip if not visible
        if not _isInPlane and not _isInFlankingPlane:
            return

        pIndex = self._spectrumSettings[spectrumView].dimensionIndices
        try:
            # fix the pointPositions
            objPos = obj.pointPositions
            pxy = (objPos[pIndex[0]] - 1, objPos[pIndex[1]] - 1)
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        try:
            # fix the lineWidths
            objLineWidths = obj.pointLineWidths
            pointLineWidths = (objLineWidths[pIndex[0]], objLineWidths[pIndex[1]])
        except Exception:
            pointLineWidths = (None, None)

        if self._isSelected(obj):
            cols = self._GLParent.highlightColour[:3]
        elif _badPos:
            cols = [1.0, 0.2, 0.1]  # red for bad position
        else:
            cols = listCol

        # frequency = (spectrumFrequency[pIndex[0]], spectrumFrequency[pIndex[1]])
        try:
            _alias = obj.aliasing
            alias = getAliasSetting(_alias[pIndex[0]], _alias[pIndex[1]])
        except Exception:
            alias = 0

        if False:  # not pIndex:
            return

        else:
            if symbolType == 0 or symbolType == 3:

                # draw a cross
                # keep the cross square at 0.1ppm

                _selected = False
                iCount = 0
                if _isInPlane or _isInFlankingPlane:
                    if symbolType == 0:  # cross
                        iCount, _selected = self._appendSquareSymbol(drawList, vertexStart, planeIndex, obj)
                    else:  # plus
                        iCount, _selected = self._appendPlusSymbol(drawList, vertexStart, planeIndex, obj)

                self._appendSymbolItemVertices(_isInFlankingPlane, _isInPlane, _selected, cols, drawList, fade, iCount,
                                               indexing, obj, pxy, pIndex, planeIndex, r, w, alias)

            elif symbolType == 1:  # draw an ellipse at lineWidth

                if pointLineWidths[0] and pointLineWidths[1]:
                    # draw 24 connected segments
                    r = 0.5 * pointLineWidths[0]  # / frequency[0]
                    w = 0.5 * pointLineWidths[1]  # / frequency[1]
                    numPoints = 24
                    angPlus = 2.0 * np.pi
                    skip = 1
                else:
                    # draw 12 disconnected segments (dotted)
                    # r = symbolWidth
                    # w = symbolWidth
                    numPoints = 12
                    angPlus = np.pi
                    skip = 2

                np2 = 2 * numPoints
                ang = list(range(numPoints))
                _selected = False
                iCount = 0

                _vertexStart = indexing.vertexStart
                if _isInPlane or _isInFlankingPlane:
                    drawList.indices = np.append(drawList.indices, np.array(tuple(val for an in ang
                                                                                  for val in ((2 * an), (2 * an) + 1)),
                                                                            dtype=np.uint32) + _vertexStart)

                    iCount = np2
                    if self._isSelected(obj):
                        _selected = True
                        drawList.indices = np.append(drawList.indices,
                                                     np.array((0, 2, 2, 1, 0, 3, 3, 1), dtype=np.uint32) + (
                                                                 _vertexStart + np2))
                        iCount += 8

                # add extra indices for the multiplet
                extraIndices = 0  #self.appendExtraIndices(drawList, indexStart + np2, obj)

                # draw an ellipse at lineWidth
                drawList.vertices = np.append(drawList.vertices, np.array(tuple(val for an in ang
                                                                                for val in (pxy[0] - r * math.sin(
                        skip * an * angPlus / numPoints),
                                                                                            pxy[1] - w * math.cos(
                                                                                                    skip * an * angPlus / numPoints),
                                                                                            alias, 0.0,
                                                                                            pxy[0] - r * math.sin((
                                                                                                                          skip * an + 1) * angPlus / numPoints),
                                                                                            pxy[1] - w * math.cos((
                                                                                                                          skip * an + 1) * angPlus / numPoints),
                                                                                            alias, 0.0)
                                                                                ),
                                                                          dtype=np.float32)
                                              )
                drawList.vertices = np.append(drawList.vertices, np.array((pxy[0] - r, pxy[1] - w, alias, 0.0,
                                                                           pxy[0] + r, pxy[1] + w, alias, 0.0,
                                                                           pxy[0] + r, pxy[1] - w, alias, 0.0,
                                                                           pxy[0] - r, pxy[1] + w, alias, 0.0,
                                                                           pxy[0], pxy[1], alias, 0.0,
                                                                           ), dtype=np.float32)
                                              )

                step = np2 + 5
                drawList.colors = np.append(drawList.colors, np.array((*cols, fade) * step, dtype=np.float32))
                drawList.attribs = np.append(drawList.attribs,
                                             np.array((alias, 0.0, 0.0, 0.0) * step, dtype=np.float32))
                drawList.offsets = np.append(drawList.offsets,
                                             np.array((pxy[0], pxy[1], 0.0, 0.0) * step, dtype=np.float32))

                # add extra vertices for the multiplet
                extraVertices = 0  #self.appendExtraVertices(drawList, obj, p0, [*cols, fade], fade)

                # keep a pointer to the obj
                drawList.pids = np.append(drawList.pids, (obj, drawList.numVertices, (numPoints + extraVertices),
                                                          _isInPlane, _isInFlankingPlane, _selected,
                                                          indexEnd, indexEnd + iCount + extraIndices,
                                                          planeIndex, 0, 0, 0))
                # indexEnd = len(drawList.indices)

                # indexList[0] += (step + extraIndices)
                # indexList[1] = len(drawList.indices)
                indexing.start += (step + extraIndices)
                indexing.end += (iCount + extraIndices)  # len(drawList.indices)
                drawList.numVertices += (step + extraVertices)
                indexing.vertexStart += (step + extraVertices)

            elif symbolType == 2:  # draw a filled ellipse at lineWidth

                if pointLineWidths[0] and pointLineWidths[1]:
                    # draw 24 connected segments
                    r = 0.5 * pointLineWidths[0]  # / frequency[0]
                    w = 0.5 * pointLineWidths[1]  # / frequency[1]
                    numPoints = 24
                    angPlus = 2 * np.pi
                    skip = 1
                else:
                    # draw 12 disconnected segments (dotted)
                    # r = symbolWidth
                    # w = symbolWidth
                    numPoints = 12
                    angPlus = 1.0 * np.pi
                    skip = 2

                np2 = 2 * numPoints
                ang = list(range(numPoints))
                _selected = False
                iCount = 0

                _vertexStart = indexing.vertexStart
                if _isInPlane or _isInFlankingPlane:
                    drawList.indices = np.append(drawList.indices,
                                                 np.array(tuple(val for an in ang
                                                                for val in ((2 * an), (2 * an) + 1, np2 + 4)),
                                                          dtype=np.uint32) + _vertexStart)
                    iCount = 3 * numPoints

                # add extra indices for the multiplet
                extraIndices = 0  #self.appendExtraIndices(drawList, indexStart + np2 + 4, obj)

                # draw an ellipse at lineWidth
                drawList.vertices = np.append(drawList.vertices, np.array(tuple(val for an in ang
                                                                                for val in (pxy[0] - r * math.sin(skip * an * angPlus / numPoints),
                                                                                            pxy[1] - w * math.cos(skip * an * angPlus / numPoints),
                                                                                            alias, 0.0,
                                                                                            pxy[0] - r * math.sin((skip * an + 1) * angPlus / numPoints),
                                                                                            pxy[1] - w * math.cos((skip * an + 1) * angPlus / numPoints),
                                                                                            alias, 0.0,)
                                                                                ),
                                                                          dtype=np.float32)
                                              )

                drawList.vertices = np.append(drawList.vertices, np.array((pxy[0] - r, pxy[1] - w, alias, 0.0,
                                                                           pxy[0] + r, pxy[1] + w, alias, 0.0,
                                                                           pxy[0] + r, pxy[1] - w, alias, 0.0,
                                                                           pxy[0] - r, pxy[1] + w, alias, 0.0,
                                                                           pxy[0], pxy[1], alias, 0.0,
                                                                           ), dtype=np.float32)
                                              )

                step = np2 + 5
                drawList.colors = np.append(drawList.colors, np.array((*cols, fade) * step, dtype=np.float32))
                drawList.attribs = np.append(drawList.attribs,
                                             np.array((alias, 0.0, 0.0, 0.0) * step, dtype=np.float32))
                drawList.offsets = np.append(drawList.offsets,
                                             np.array((pxy[0], pxy[1], 0.0, 0.0) * step, dtype=np.float32))

                # add extra vertices for the multiplet
                extraVertices = 0  #self.appendExtraVertices(drawList, obj, p0, [*cols, fade], fade)

                # keep a pointer to the obj
                drawList.pids = np.append(drawList.pids, (obj, drawList.numVertices, (numPoints + extraVertices),
                                                          _isInPlane, _isInFlankingPlane, _selected,
                                                          indexEnd, indexEnd + iCount + extraIndices,
                                                          planeIndex, 0, 0, 0))

                indexing.start += (step + extraIndices)
                indexing.end += (iCount + extraIndices)
                drawList.numVertices += (step + extraVertices)
                indexing.vertexStart += (step + extraVertices)

            else:
                raise ValueError('GL Error: bad symbol type')

    def _appendSymbolItemVertices(self, _isInFlankingPlane, _isInPlane, _selected, cols,
                                  drawList, fade, iCount, indexing, obj, pxy, pIndex,
                                  planeIndex, r, w, alias):

        drawList.vertices = np.append(drawList.vertices, np.array((pxy[0] - r, pxy[1] - w, alias, 0.0,
                                                                   pxy[0] + r, pxy[1] + w, alias, 0.0,
                                                                   pxy[0] + r, pxy[1] - w, alias, 0.0,
                                                                   pxy[0] - r, pxy[1] + w, alias, 0.0,
                                                                   pxy[0], pxy[1], alias, 0.0,
                                                                   pxy[0], pxy[1] - w, alias, 0.0,
                                                                   pxy[0], pxy[1] + w, alias, 0.0,
                                                                   pxy[0] + r, pxy[1], alias, 0.0,
                                                                   pxy[0] - r, pxy[1], alias, 0.0,
                                                                   ), dtype=np.float32))
        drawList.colors = np.append(drawList.colors, np.array((*cols, fade) * self.LENSQ, dtype=np.float32))
        drawList.attribs = np.append(drawList.attribs, np.array((alias, 0.0, 0.0, 0.0) * self.LENSQ, dtype=np.float32))
        drawList.offsets = np.append(drawList.offsets,
                                     np.array((pxy[0], pxy[1], 0.0, 0.0) * self.LENSQ, dtype=np.float32))

        # called extraIndices, extraIndexCount above
        # add extra indices
        _indexCount, extraIndices = self.appendExtraIndices(drawList, indexing.vertexStart + self.LENSQ, obj)
        # add extra vertices for the multiplet
        extraVertices = self.appendExtraVertices(drawList, pIndex, obj,
                                                 pxy, (*cols, fade), fade, alias)
        # keep a pointer to the obj
        drawList.pids = np.append(drawList.pids, (obj, drawList.numVertices, (self.LENSQ + extraVertices),
                                                  _isInPlane, _isInFlankingPlane, _selected,
                                                  indexing.end, indexing.end + iCount + _indexCount, planeIndex,
                                                  0, 0, 0))

        indexing.start += (self.LENSQ + extraIndices)
        indexing.end += (iCount + _indexCount)
        drawList.numVertices += (self.LENSQ + extraVertices)
        indexing.vertexStart += (self.LENSQ + extraVertices)

    def _appendSymbol(self, spectrumView, objListView, obj):
        """Append a new symbol to the end of the list
        """
        spectrum = spectrumView.spectrum
        drawList = self._GLSymbols[objListView]
        if obj in drawList.pids[0::GLDefs.LENPID]:
            return

        self.objIsInVisiblePlanesRemove(spectrumView, obj)

        # find the correct scale to draw square pixels
        # don't forget to change when the axes change

        _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

        if symbolType == 0 or symbolType == 3:  # a cross/plus

            # change the ratio on resize
            drawList.refreshMode = GLREFRESHMODE_REBUILD
            drawList.drawMode = GL.GL_LINES
            drawList.fillMode = None

        elif symbolType == 1:  # draw an ellipse at lineWidth

            # fix the size to the axes
            drawList.refreshMode = GLREFRESHMODE_NEVER
            drawList.drawMode = GL.GL_LINES
            drawList.fillMode = None

        elif symbolType == 2:  # draw a filled ellipse at lineWidth

            # fix the size to the axes
            drawList.refreshMode = GLREFRESHMODE_NEVER
            drawList.drawMode = GL.GL_TRIANGLES
            drawList.fillMode = GL.GL_FILL

        else:
            raise ValueError('GL Error: bad symbol type')

        # build the peaks VBO
        indexing = AttrDict()
        indexing.start = len(drawList.indices)
        indexing.end = len(drawList.indices)
        indexing.vertexStart = drawList.numVertices

        pls = self.objectList(objListView)

        if objListView.meritEnabled and obj.figureOfMerit < objListView.meritThreshold:
            objCol = objListView.meritColour or GLDefs.DEFAULTCOLOUR
        else:
            objCol = objListView.symbolColour or GLDefs.DEFAULTCOLOUR

        listCol = getAutoColourRgbRatio(objCol, pls.spectrum,
                                        self.autoColour,
                                        getColours()[CCPNGLWIDGET_FOREGROUND])

        spectrumFrequency = spectrum.spectrometerFrequencies

        strip = spectrumView.strip
        self._appendSymbolItem(strip, obj, listCol, indexing, r, w,
                               spectrumFrequency, symbolType, drawList, spectrumView)

    def _updateHighlightedLabels(self, spectrumView, objListView):
        if objListView not in self._GLLabels:
            return

        drawList = self._GLLabels[objListView]

        pls = self.objectList(objListView)
        listCol = getAutoColourRgbRatio(objListView.textColour or GLDefs.DEFAULTCOLOUR, pls.spectrum, self.autoColour,
                                        getColours()[CCPNGLWIDGET_FOREGROUND])
        meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, pls.spectrum, self.autoColour,
                                         getColours()[CCPNGLWIDGET_FOREGROUND])
        meritEnabled = objListView.meritEnabled
        meritThreshold = objListView.meritThreshold

        for drawStr in drawList.stringList:

            obj = drawStr.stringObject

            if obj and not obj.isDeleted:
                # get visible/plane status
                _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

                if _isInPlane or _isInFlankingPlane:

                    if self._isSelected(obj):
                        drawStr.setStringColour((*self._GLParent.highlightColour[:3], fade))
                    elif obj.pointPositions and None in obj.pointPositions:
                        drawStr.setStringColour((1.0, 0.2, 0.1, fade))
                    else:

                        if meritEnabled and obj.figureOfMerit < meritThreshold:
                            cols = meritCol
                        else:
                            cols = listCol

                        drawStr.setStringColour((*cols, fade))
                    drawStr.pushTextArrayVBOColour()

    def updateHighlightSymbols(self):
        """Respond to an update highlight notifier and update the highlighted symbols/labels
        """
        for spectrumView in self._ordering:

            if spectrumView.isDeleted:
                continue

            for objListView in self.listViews(spectrumView):

                if objListView in self._GLSymbols.keys():
                    self._updateHighlightedSymbols(spectrumView, objListView)
                    self._updateHighlightedLabels(spectrumView, objListView)
                if objListView in self._GLArrows.keys():
                    self._updateHighlightedArrows(spectrumView, objListView)

    def updateAllSymbols(self):
        """Respond to update all notifier
        """
        for spectrumView in self._ordering:

            if spectrumView.isDeleted:
                continue

            for objListView in self.listViews(spectrumView):

                if objListView in self._GLSymbols.keys():
                    objListView.buildSymbols = True
                    objListView.buildLabels = True
                    objListView.buildArrows = True

    def _updateHighlightedSymbols(self, spectrumView, objListView):
        """update the highlighted symbols
        """
        strip = self.strip
        symbolType = strip.symbolType

        drawList = self._GLSymbols[objListView]
        drawList.indices = np.empty(0, dtype=np.uint32)

        indexStart = 0
        indexEnd = 0
        vertexStart = 0

        pls = self.objectList(objListView)
        listCol = getAutoColourRgbRatio(objListView.symbolColour or GLDefs.DEFAULTCOLOUR, pls.spectrum, self.autoColour,
                                        getColours()[CCPNGLWIDGET_FOREGROUND])
        meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, pls.spectrum, self.autoColour,
                                         getColours()[CCPNGLWIDGET_FOREGROUND])
        meritEnabled = objListView.meritEnabled
        meritThreshold = objListView.meritThreshold

        if symbolType == 0 or symbolType == 3:

            for pp in range(0, len(drawList.pids), GLDefs.LENPID):

                # check whether the peaks still exists
                obj = drawList.pids[pp]
                offset = drawList.pids[pp + 1]
                numPoints = drawList.pids[pp + 2]

                if not obj.isDeleted:
                    _selected = False
                    iCount = 0
                    _indexCount = 0

                    # get visible/plane status
                    _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

                    if _isInPlane or _isInFlankingPlane:
                        if symbolType == 0:  # cross
                            iCount, _selected = self._appendSquareSymbol(drawList, vertexStart, planeIndex, obj)
                        else:  # plus
                            iCount, _selected = self._appendPlusSymbol(drawList, vertexStart, planeIndex, obj)

                        if _selected:
                            cols = self._GLParent.highlightColour[:3]
                        elif obj.pointPositions and None in obj.pointPositions:
                            cols = [1.0, 0.2, 0.1]  # red if the position is bad
                        else:
                            if meritEnabled and obj.figureOfMerit < meritThreshold:
                                cols = meritCol
                            else:
                                cols = listCol

                        # make sure that links for the multiplets are added
                        _indexCount, extraIndices = self.appendExtraIndices(drawList, indexStart + self.LENSQ, obj)
                        drawList.colors[offset * 4:(offset + self.POINTCOLOURS) * 4] = (*cols,
                                                                                        fade) * self.POINTCOLOURS  #numPoints

                    # list MAY contain out of plane peaks
                    drawList.pids[pp + 3:pp + 9] = (_isInPlane, _isInFlankingPlane, _selected,
                                                    indexEnd, indexEnd + iCount + _indexCount, planeIndex)
                    indexEnd += (iCount + _indexCount)

                indexStart += numPoints
                vertexStart += numPoints

        elif symbolType == 1:

            for pp in range(0, len(drawList.pids), GLDefs.LENPID):

                # check whether the peaks still exists
                obj = drawList.pids[pp]
                offset = drawList.pids[pp + 1]
                numPoints = drawList.pids[pp + 2]
                np2 = 2 * numPoints

                if not obj.isDeleted:
                    ang = list(range(numPoints))

                    _selected = False
                    # get visible/plane status
                    _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

                    if _isInPlane or _isInFlankingPlane:
                        drawList.indices = np.append(drawList.indices, np.array(tuple(val for an in ang
                                                                                      for val in (indexStart + (2 * an),
                                                                                                  indexStart + (2 * an) + 1)),
                                                                                dtype=np.uint32))

                        if self._isSelected(obj):
                            _selected = True
                            cols = self._GLParent.highlightColour[:3]
                            drawList.indices = np.append(drawList.indices,
                                                         np.array((indexStart + np2, indexStart + np2 + 2,
                                                                   indexStart + np2 + 2, indexStart + np2 + 1,
                                                                   indexStart + np2, indexStart + np2 + 3,
                                                                   indexStart + np2 + 3, indexStart + np2 + 1),
                                                                  dtype=np.uint32))
                        elif obj.pointPositions and None in obj.pointPositions:
                            cols = [1.0, 0.2, 0.1]  # red if the position is bad
                        else:
                            if objListView.meritEnabled and obj.figureOfMerit < objListView.meritThreshold:
                                cols = meritCol
                            else:
                                cols = listCol

                        drawList.colors[offset * 4:(offset + np2 + 5) * 4] = (*cols, fade) * (np2 + 5)

                    drawList.pids[pp + 3:pp + 9] = (_isInPlane, _isInFlankingPlane, _selected,
                                                    indexEnd, len(drawList.indices), planeIndex)
                    indexEnd = len(drawList.indices)

                indexStart += np2 + 5

        elif symbolType == 2:

            for pp in range(0, len(drawList.pids), GLDefs.LENPID):

                # check whether the peaks still exists
                obj = drawList.pids[pp]
                offset = drawList.pids[pp + 1]
                numPoints = drawList.pids[pp + 2]
                np2 = 2 * numPoints

                if not obj.isDeleted:
                    ang = list(range(numPoints))

                    _selected = False
                    # get visible/plane status
                    _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

                    if _isInPlane or _isInFlankingPlane:
                        drawList.indices = np.append(drawList.indices, np.array(tuple(val for an in ang
                                                                                      for val in
                                                                                      (2 * an, (2 * an) + 1, np2 + 4)),
                                                                                dtype=np.uint32) + indexStart)
                        if self._isSelected(obj):
                            _selected = True
                            cols = self._GLParent.highlightColour[:3]
                        elif obj.pointPositions and None in obj.pointPositions:
                            cols = [1.0, 0.2, 0.1]  # red if the position is bad
                        else:
                            if objListView.meritEnabled and obj.figureOfMerit < objListView.meritThreshold:
                                cols = meritCol
                            else:
                                cols = listCol

                        drawList.colors[offset * 4:(offset + np2 + 5) * 4] = (*cols, fade) * (np2 + 5)

                    drawList.pids[pp + 3:pp + 9] = (_isInPlane, _isInFlankingPlane, _selected,
                                                    indexEnd, len(drawList.indices), planeIndex)
                    indexEnd = len(drawList.indices)

                indexStart += np2 + 5

        else:
            raise ValueError('GL Error: bad symbol type')

        drawList.pushIndexVBOIndices()
        drawList.pushTextArrayVBOColour()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Rescaling
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _rescaleSymbolOffsets(self, r, w):
        return np.array([-r, -w, 0, 0,
                         +r, +w, 0, 0,
                         +r, -w, 0, 0,
                         -r, +w, 0, 0,
                         0, 0, 0, 0,
                         0, -w, 0, 0,
                         0, +w, 0, 0,
                         +r, 0, 0, 0,
                         -r, 0, 0, 0], np.float32), \
            self.LENSQ4

    def _rescaleSymbols(self, spectrumView, objListView):
        """rescale symbols when the screen dimensions change
        """
        drawList = self._GLSymbols[objListView]

        if not drawList.numVertices:
            return

        # if drawList.refreshMode == GLREFRESHMODE_REBUILD:
        _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

        if symbolType == 0 or symbolType == 3:  # a cross/plus
            offsets, offLen = self._rescaleSymbolOffsets(r, w)
            for pp in range(0, len(drawList.pids), GLDefs.LENPID):
                indexStart = 4 * drawList.pids[pp + 1]
                drawList.vertices[indexStart:indexStart + offLen] = \
                    drawList.offsets[indexStart:indexStart + offLen] + offsets

        elif symbolType == 1:  # an ellipse
            numPoints = 12
            angPlus = 1.0 * np.pi
            skip = 2

            np2 = 2 * numPoints
            ang = list(range(numPoints))

            offsets = np.empty(56)
            for an in ang:
                offsets[4 * an:4 * an + 4] = [- r * math.sin(skip * an * angPlus / numPoints),
                                              - w * math.cos(skip * an * angPlus / numPoints),
                                              - r * math.sin((skip * an + 1) * angPlus / numPoints),
                                              - w * math.cos((skip * an + 1) * angPlus / numPoints)]
                offsets[48:56] = [-r, -w, +r, +w, +r, -w, -r, +w]

            for pp in range(0, len(drawList.pids), GLDefs.LENPID):
                if drawList.pids[pp + 2] == 12:
                    indexStart = 2 * drawList.pids[pp + 1]
                    drawList.vertices[indexStart:indexStart + 56] = drawList.offsets[
                                                                    indexStart:indexStart + 56] + offsets

        elif symbolType == 2:  # filled ellipse
            numPoints = 12
            angPlus = 1.0 * np.pi
            skip = 2

            np2 = 2 * numPoints
            ang = list(range(numPoints))

            offsets = np.empty(48)
            for an in ang:
                offsets[4 * an:4 * an + 4] = [- r * math.sin(skip * an * angPlus / numPoints),
                                              - w * math.cos(skip * an * angPlus / numPoints),
                                              - r * math.sin((skip * an + 1) * angPlus / numPoints),
                                              - w * math.cos((skip * an + 1) * angPlus / numPoints)]

            for pp in range(0, len(drawList.pids), GLDefs.LENPID):
                if drawList.pids[pp + 2] == 12:
                    indexStart = 2 * drawList.pids[pp + 1]
                    drawList.vertices[indexStart:indexStart + 48] = drawList.offsets[
                                                                    indexStart:indexStart + 48] + offsets

        else:
            raise ValueError('GL Error: bad symbol type')

    def _rescaleLabels(self, spectrumView=None, objListView=None, drawList=None):
        """Rescale all labels to the new dimensions of the screen
        """
        _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

        # NOTE:ED - could add in the peakItem offset at this point

        if symbolType == 0 or symbolType == 3:  # a cross/plus

            for drawStr in drawList.stringList:
                if textOffset := drawStr.stringObject.getTextOffset(objListView):
                    tx, ty = textOffset
                    _, _, _, _, tr, tw = self._getLabelOffsets(spectrumView, tx, ty)
                    drawStr.setStringOffset((tr, tw))
                else:
                    drawStr.setStringOffset((r, w))
                drawStr.pushTextArrayVBOAttribs()

        elif symbolType == 1:
            for drawStr in drawList.stringList:
                if textOffset := drawStr.stringObject.getTextOffset(objListView):
                    tx, ty = textOffset
                    _, _, _, _, tr, tw = self._getLabelOffsets(spectrumView, tx, ty)
                    drawStr.setStringOffset((tr, tw))
                elif drawStr.stringOffset:
                    lr, lw = drawStr.stringOffset
                    drawStr.setStringOffset((lr, lw))
                else:
                    drawStr.setStringOffset((GLDefs.STRINGSCALE * r, GLDefs.STRINGSCALE * w))
                drawStr.pushTextArrayVBOAttribs()

        elif symbolType == 2:
            for drawStr in drawList.stringList:
                if textOffset := drawStr.stringObject.getTextOffset(objListView):
                    tx, ty = textOffset
                    _, _, _, _, tr, tw = self._getLabelOffsets(spectrumView, tx, ty)
                    drawStr.setStringOffset((tr, tw))
                elif drawStr.stringOffset:
                    lr, lw = drawStr.stringOffset
                    drawStr.setStringOffset((lr, lw))
                else:
                    drawStr.setStringOffset((GLDefs.STRINGSCALE * r, GLDefs.STRINGSCALE * w))
                drawStr.pushTextArrayVBOAttribs()

        else:
            raise ValueError('GL Error: bad symbol type')

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Building
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _buildSymbolsCountItem(self, strip, spectrumView, obj, symbolType, tCount):
        """return the number of indices and vertices for the object
        """
        # get visible/plane status
        _isInPlane, _isInFlankingPlane, planeIndex, fade = self.objIsInVisiblePlanes(spectrumView, obj)

        # skip if not visible
        if not _isInPlane and not _isInFlankingPlane:
            return 0, 0

        if symbolType == 0:  # draw a cross symbol

            ind = self._getSquareSymbolCount(planeIndex, obj)
            ind += self.extraIndicesCount(obj)
            extraVertices = self.extraVerticesCount(obj)

            vert = (self.LENSQ + extraVertices)
            return ind, vert

        elif symbolType == 3:  # draw a plus symbol

            ind = self._getPlusSymbolCount(planeIndex, obj)
            ind += self.extraIndicesCount(obj)
            extraVertices = self.extraVerticesCount(obj)

            vert = (self.LENSQ + extraVertices)
            return ind, vert

        elif symbolType == 1:  # draw an ellipse at lineWidth

            if obj.pointLineWidths[0] and obj.pointLineWidths[1]:
                numPoints = 24
            else:
                numPoints = 12

            np2 = 2 * numPoints
            ind = np2
            if self._isSelected(obj):
                ind += 8
            vert = (np2 + 5)
            return ind, vert

        elif symbolType == 2:  # draw a filled ellipse at lineWidth

            if obj.pointLineWidths[0] and obj.pointLineWidths[1]:
                numPoints = 24
            else:
                numPoints = 12

            ind = 3 * numPoints
            vert = ((2 * numPoints) + 5)
            return ind, vert

        else:
            raise ValueError('GL Error: bad symbol type')

    def _buildSymbolsCount(self, spectrumView, objListView, drawList):
        """count the number of indices and vertices for the label list
        """

        pls = self.objectList(objListView)

        # reset the object pointers
        self._objectStore = {}

        indCount = 0
        vertCount = 0
        objCount = 0
        for tCount, obj in enumerate(self.objects(pls)):
            ind, vert = self._buildSymbolsCountItem(self.strip, spectrumView, obj, self.strip.symbolType, tCount)
            indCount += ind
            vertCount += vert
            if ind:
                objCount += 1

        # set up arrays
        vc = vertCount * 4
        drawList.indices = np.empty(indCount, dtype=np.uint32)
        drawList.vertices = np.empty(vc, dtype=np.float32)
        drawList.colors = np.empty(vc, dtype=np.float32)
        drawList.attribs = np.empty(vc, dtype=np.float32)
        drawList.offsets = np.empty(vc, dtype=np.float32)
        drawList.pids = np.empty(objCount * GLDefs.LENPID, dtype=np.object_)
        drawList.numVertices = 0

        return indCount, vertCount

    def _buildObjIsInVisiblePlanesList(self, spectrumView, objListView):
        """Build the dict of all object is visible values
        """

        objList = self.objectList(objListView)

        # clear the old list for this spectrumView
        if spectrumView in self._objIsInVisiblePlanesCache:
            del self._objIsInVisiblePlanesCache[spectrumView]

        for obj in self.objects(objList):
            self.objIsInVisiblePlanes(spectrumView, obj)

    # from ccpn.util.decorators import profile
    # @profile
    def _buildSymbols(self, spectrumView, objListView):
        spectrum = spectrumView.spectrum

        if objListView not in self._GLSymbols:
            # creates a new GLSymbolArray set to rebuild for below
            self._GLSymbols[objListView] = GLSymbolArray(GLContext=self,
                                                         spectrumView=spectrumView,
                                                         objListView=objListView)

        drawList = self._GLSymbols[objListView]

        if drawList.renderMode == GLRENDERMODE_RESCALE:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode
            self._rescaleSymbols(spectrumView=spectrumView, objListView=objListView)
            # self._rescaleLabels(spectrumView=spectrumView,
            #                     objListView=objListView,
            #                     drawList=self._GLLabels[objListView])

            drawList.defineAliasedIndexVBO()

        elif drawList.renderMode == GLRENDERMODE_REBUILD:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode

            # find the correct scale to draw square pixels
            # don't forget to change when the axes change

            _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

            if symbolType == 0 or symbolType == 3:  # a cross/plus

                # change the ratio on resize
                drawList.refreshMode = GLREFRESHMODE_REBUILD
                drawList.drawMode = GL.GL_LINES
                drawList.fillMode = None

            elif symbolType == 1:  # draw an ellipse at lineWidth

                # fix the size to the axes
                drawList.refreshMode = GLREFRESHMODE_NEVER
                drawList.drawMode = GL.GL_LINES
                drawList.fillMode = None

            elif symbolType == 2:  # draw a filled ellipse at lineWidth

                # fix the size to the axes
                drawList.refreshMode = GLREFRESHMODE_NEVER
                drawList.drawMode = GL.GL_TRIANGLES
                drawList.fillMode = GL.GL_FILL

            else:
                raise ValueError('GL Error: bad symbol type')

            # build the peaks VBO
            indexing = AttrDict()
            indexing.start = 0
            indexing.end = 0
            indexing.vertexPtr = 0
            indexing.vertexStart = 0
            indexing.objNum = 0

            pls = self.objectList(objListView)
            listCol = getAutoColourRgbRatio(objListView.symbolColour or GLDefs.DEFAULTCOLOUR, pls.spectrum,
                                            self.autoColour,
                                            getColours()[CCPNGLWIDGET_FOREGROUND])
            meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, pls.spectrum,
                                             self.autoColour,
                                             getColours()[CCPNGLWIDGET_FOREGROUND])
            meritEnabled = objListView.meritEnabled
            meritThreshold = objListView.meritThreshold

            spectrumFrequency = spectrum.spectrometerFrequencies
            strip = spectrumView.strip

            ind, vert = self._buildSymbolsCount(spectrumView, objListView, drawList)
            if ind:

                for tCount, obj in enumerate(self.objects(pls)):

                    if meritEnabled and obj.figureOfMerit < meritThreshold:
                        cols = meritCol
                    else:
                        cols = listCol

                    self._insertSymbolItem(strip, obj, cols, indexing, r, w,
                                           spectrumFrequency, symbolType, drawList,
                                           spectrumView, tCount)

            drawList.defineAliasedIndexVBO()

    def buildSymbols(self):
        if self.strip.isDeleted:
            return

        for olv in [(spectrumView, objListView) for spectrumView in self._ordering if not spectrumView.isDeleted
                    for objListView in self.listViews(spectrumView) if
                    objListView.isDeleted and self._objIsInVisiblePlanesCache.get(objListView)
                    ]:
            del self._objIsInVisiblePlanesCache[olv]

        objListViews = [(spectrumView, objListView) for spectrumView in self._ordering if not spectrumView.isDeleted
                        for objListView in self.listViews(spectrumView) if not objListView.isDeleted
                        ]

        for spectrumView, objListView in objListViews:

            # # list through the valid peakListViews attached to the strip - including undeleted
            # for spectrumView in self._ordering:  # strip.spectrumViews:
            #
            #     if spectrumView.isDeleted:
            #         continue
            #
            #     # for peakListView in spectrumView.peakListViews:
            #     for objListView in self.listViews(spectrumView):  # spectrumView.peakListViews:
            #
            #         if objListView.isDeleted:
            #             if objListView in self._objIsInVisiblePlanesCache:
            #                 del self._objIsInVisiblePlanesCache[objListView]
            #             continue

            if objListView.buildSymbols:
                objListView.buildSymbols = False

                # generate the planeVisibility list here - need to integrate with labels
                self._buildObjIsInVisiblePlanesList(spectrumView, objListView)

                # set the interior flags for rebuilding the GLdisplay
                if (dList := self._GLSymbols.get(objListView)):
                    dList.renderMode = GLRENDERMODE_REBUILD

                self._buildSymbols(spectrumView, objListView)

            elif (dList := self._GLSymbols.get(objListView)) and dList.renderMode == GLRENDERMODE_RESCALE:
                self._buildSymbols(spectrumView, objListView)

    def buildLabels(self):
        if self.strip.isDeleted:
            return

        _buildList = []
        objListViews = [(spectrumView, objListView) for spectrumView in self._ordering if not spectrumView.isDeleted
                        for objListView in self.listViews(spectrumView) if not objListView.isDeleted
                        ]

        for sView, olv in objListViews:
            # spectrumView not deleted
            # objListView not deleted

            if olv.buildLabels:
                # print(f'   building objList  {olv}')
                olv.buildLabels = False
                if (dList := self._GLLabels.get(olv)):
                    dList.renderMode = GLRENDERMODE_REBUILD

                # self._buildPeakListLabels(spectrumView, peakListView)
                _buildList.append([sView, olv])

            elif (dList := self._GLLabels.get(olv)) and dList.renderMode == GLRENDERMODE_RESCALE:
                # print(f'   rescaling objList  {olv}')
                self._rescaleLabels(sView, olv, dList)
                dList.renderMode = GLRENDERMODE_DRAW

        if _buildList:
            self._buildAllLabels(_buildList)
            # self._rescalePeakListLabels(spectrumView, peakListView, self._GLPeakListLabels[peakListView])

    def _buildAllLabels(self, viewList):
        for ii, view in enumerate(viewList):
            spectrumView = view[0]
            objListView = view[1]
            if objListView not in self._GLLabels.keys():
                self._GLLabels[objListView] = GLLabelArray(GLContext=self,
                                                           spectrumView=spectrumView,
                                                           objListView=objListView)
                drawList = self._GLLabels[objListView]
                drawList.stringList = []

        buildQueue = (viewList, self._GLParent, self._GLLabels)

        # not calling as a thread because it's not multiprocessing AND its slower
        self._threadBuildAllLabels(*buildQueue)

        # buildPeaks = Thread(name=str(self.strip.pid),
        #                     target=self._threadBuildAllLabels,
        #                     args=buildQueue)
        # buildPeaks.start()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Threads
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _threadBuildLabels(self, spectrumView, objListView, drawList, glStrip):

        global _totalTime
        global _timeCount
        global _numTimes

        tempList = []
        pls = self.objectList(objListView)

        # append all labels separately
        for obj in self.objects(pls):
            self._appendLabel(spectrumView, objListView, tempList, obj)

        # # # append all labels in one go
        # # self._fillLabels(spectrumView, objListView, tempList, pls, self.objects)
        # print(f'>>> building {len(tempList)} labels')
        # try:
        #     self._tempMax = max(self._tempMax, len(tempList))
        #     print(f'>>> building {len(tempList)} labels  -  {self._tempMax}')
        # except:
        #     self._tempMax = len(tempList)
        #     print(f'>>> building {len(tempList)} labels  -  {self._tempMax}')

        drawList.stringList = tempList
        # drawList.renderMode = GLRENDERMODE_RESCALE

    def _threadBuildAllLabels(self, viewList, glStrip, _outList):
        # def _threadBuildAllPeakListLabels(self, threadQueue):#viewList, glStrip, _outList):
        #   print ([obj for obj in threadQueue])
        #   viewList = threadQueue[0]
        #   glStrip = threadQueue[1]
        #   _outList = threadQueue[2]
        #   stringList = threadQueue[3]

        for ii, view in enumerate(viewList):
            spectrumView = view[0]
            objListView = view[1]
            self._threadBuildLabels(spectrumView, objListView,
                                    _outList[objListView],
                                    glStrip)

        glStrip.GLSignals.emitPaintEvent(source=glStrip)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Drawing
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def drawSymbols(self, spectrumView):
        """Draw the symbols to the screen
        """
        if self.strip.isDeleted:
            return

        for objListView, specView in self._visibleListViews:
            if specView == spectrumView and not objListView.isDeleted and objListView in self._GLSymbols.keys():
                self._GLSymbols[objListView].drawAliasedIndexVBO()

    def drawLabels(self, spectrumView):
        """Draw the labelling to the screen
        """
        if self.strip.isDeleted:
            return

        # self._spectrumSettings = spectrumSettings
        # self.buildLabels()

        # # loop through the attached peakListViews to the strip
        # for spectrumView in self._GLParent._ordering:  #self._parent.spectrumViews:
        #         if spectrumView.isDeleted:
        #             continue
        #     # for peakListView in spectrumView.peakListViews:
        #     for objListView in self.listViews(spectrumView):
        #         if spectrumView.isVisible() and objListView.isVisible():

        for objListView, specView in self._visibleListViews:
            if specView == spectrumView and not objListView.isDeleted and objListView in self._GLLabels.keys():
                for drawString in self._GLLabels[objListView].stringList:
                    # if shader and stackingMode:
                    #     # use the stacking matrix to offset the 1D spectra
                    #     shader.setStackOffset(spectrumSettings[specView][GLDefs.SPECTRUM_STACKEDMATRIXOFFSET])

                    # draw text
                    drawString.drawTextArrayVBO()

    def objIsInVisiblePlanesReset(self):
        """Reset the object visibility cache
        """
        self._objIsInVisiblePlanesCache = {}

    def objIsInVisiblePlanesClear(self):
        """clear the object visibility cache for each peak in the spectrumViews
        """
        for specView in self._objIsInVisiblePlanesCache:
            self._objIsInVisiblePlanesCache[specView] = {}

    def objIsInVisiblePlanesRemove(self, spectrumView, obj):
        """Remove a single object from the cache
        """
        try:
            # try to remove from the nested dict
            del self._objIsInVisiblePlanesCache[spectrumView][obj]
        except:
            # nothing needed here
            pass


#=========================================================================================
# GL1dLabelling
#=========================================================================================

class GL1dLabelling():
    """Class to handle symbol and symbol labelling for generic 1d displays
    """

    def _appendArrow(self, spectrumView, objListView, obj):
        """Append a new arrow to the end of the list
        """
        drawList = self._GLArrows[objListView]
        if obj in drawList.pids[0::GLDefs.LENPID]:
            return

        # find the correct scale to draw square pixels
        # don't forget to change when the axes change

        _, _, arrowType, arrowSize, arrowMinimum, arrowWidth, r, w = self._getArrowWidths(spectrumView)

        # change the ratio on resize
        drawList.refreshMode = GLREFRESHMODE_REBUILD
        drawList.drawMode = GL.GL_LINES
        drawList.fillMode = None

        # build the peaks VBO
        indexing = AttrDict()
        indexing.start = len(drawList.indices)
        indexing.end = len(drawList.indices)
        indexing.vertexStart = drawList.numVertices

        pls = self.objectList(objListView)

        listCol = getAutoColourRgbRatio(objListView.arrowColour or GLDefs.DEFAULTCOLOUR, pls.spectrum, self.autoColour,
                                        getColours()[CCPNGLWIDGET_FOREGROUND])
        meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, pls.spectrum, self.autoColour,
                                         getColours()[CCPNGLWIDGET_FOREGROUND])
        meritEnabled = objListView.meritEnabled
        meritThreshold = objListView.meritThreshold

        specSet = self._spectrumSettings[spectrumView]
        vPPX, vPPY = specSet.ppmPerPoint
        delta = specSet.delta
        ar = specSet.axisDirection
        dims = specSet.dimensionIndices
        try:
            _pos = (obj.pointPositions[0] - 1, obj.height if obj.height is not None else 0)
            pxy = [_pos[dim] for dim in dims]
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        rx, ry = 0.0, 0.0
        tnx, tny = 0.0, 0.0
        inr, inw = r, w
        try:
            pView = self.getViewFromListView(objListView, obj)
            tx, ty = pView.getIntersect((0, 0))  # ppm intersect
            pixX, pixY = objListView.pixelSize
            tx, ty = tx * delta[0] * ar[0], ty * delta[1] * ar[1]
            pixX, pixY = abs(pixX), abs(pixY)
            r, w = tx / vPPX, ty / vPPY  # ppm->points
            sx, sy = line_rectangle_intersection((0, 0),
                                                 (tx / vPPX, ty / vPPY),
                                                 (-inr, -inw),
                                                 (inr, inw))
            px, py = (tx - (sx * vPPX)) / pixX, (ty - (sy * vPPY)) / pixY
            _ll = px**2 + py**2
            if _ll < arrowMinimum:
                # line is too short
                sx, sy = 0, 0
                r, w = 0.0, 0.0
            else:
                # generate the end-vector perpendicular to the line
                rx, ry = -ty * pixX, tx * pixY  # back to pixels, rotated 90-degrees
                denom = (rx**2 + ry**2)**0.5
                rx = (arrowSize * rx / denom) * pixX / vPPX  # pixels->points for display
                ry = (arrowSize * ry / denom) * pixY / vPPY
                # generate the end-vector parallel to the line
                tnx, tny = tx / pixX, ty / pixY  # back to pixels, rotated 90-degrees
                denom = (tnx**2 + tny**2)**0.5
                tnx = (arrowSize * tnx / denom) * pixX / vPPX  # pixels->points for display
                tny = (arrowSize * tny / denom) * pixY / vPPY
        except Exception:
            sx, sy = 0, 0
            r, w = 0.0, 0.0

        if self._isSelected(obj):
            cols = self._GLParent.highlightColour[:3]
        elif _badPos:
            cols = [1.0, 0.2, 0.1]  # red if the position is bad
        else:
            if meritEnabled and obj.figureOfMerit < meritThreshold:
                cols = meritCol
            else:
                cols = listCol

        try:
            _alias = obj.aliasing
            alias = getAliasSetting(_alias[0], 0)
        except Exception:
            alias = 0

        iCount, _selected = self._appendArrowIndices(drawList, indexing.vertexStart, 0, obj, arrowType)
        self._appendArrowItemVertices(True, True, _selected, cols, drawList, 1.0, iCount, indexing, obj, pxy, dims,
                                      0, r, w, alias, sx, sy, rx, ry, tnx, tny)

    def _insertArrowItem(self, strip, obj, listCol, indexing, r, w,
                         spectrumFrequency, arrowType, arrowSize, arrowMinimum, drawList, spectrumView, objListView):
        """insert a single arrow to the end of the arrow list
        """

        # indexStart = indexing.start
        indexEnd = indexing.end
        objNum = indexing.objNum
        vertexPtr = indexing.vertexPtr
        vertexStart = indexing.vertexStart

        if not obj:
            return

        specSet = self._spectrumSettings[spectrumView]
        vPPX, vPPY = specSet.ppmPerPoint
        delta = specSet.delta
        ar = specSet.axisDirection
        dims = specSet.dimensionIndices
        try:
            objPos = obj.pointPositions
            _pos = (objPos[0] - 1, obj.height if obj.height is not None else 0)
            pxy = [_pos[dim] for dim in dims]
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        rx, ry = 0.0, 0.0
        tnx, tny = 0.0, 0.0
        inr, inw = r, w
        try:
            pView = self.getViewFromListView(objListView, obj)
            tx, ty = pView.getIntersect((0, 0))  # ppm intersect
            pixX, pixY = objListView.pixelSize
            tx, ty = tx * delta[0] * ar[0], ty * delta[1] * ar[1]
            pixX, pixY = abs(pixX), abs(pixY)
            r, w = tx / vPPX, ty / vPPY  # ppm->points
            sx, sy = line_rectangle_intersection((0, 0),
                                                 (tx / vPPX, ty / vPPY),
                                                 (-inr, -inw),
                                                 (inr, inw))
            px, py = (tx - (sx * vPPX)) / pixX, (ty - (sy * vPPY)) / pixY
            _ll = px**2 + py**2
            if _ll < arrowMinimum:
                # line is too short
                sx, sy = 0, 0
                r, w = 0.0, 0.0
            else:
                # generate the end-vector perpendicular to the line
                rx, ry = -ty * pixX, tx * pixY  # back to pixels, rotated 90-degrees
                denom = (rx**2 + ry**2)**0.5
                rx = (arrowSize * rx / denom) * pixX / vPPX  # pixels->points for display
                ry = (arrowSize * ry / denom) * pixY / vPPY
                # generate the end-vector parallel to the line
                tnx, tny = tx / pixX, ty / pixY  # back to pixels, rotated 90-degrees
                denom = (tnx**2 + tny**2)**0.5
                tnx = (arrowSize * tnx / denom) * pixX / vPPX  # pixels->points for display
                tny = (arrowSize * tny / denom) * pixY / vPPY
        except Exception:
            sx, sy = 0, 0
            r, w = 0.0, 0.0

        if self._isSelected(obj):
            cols = self._GLParent.highlightColour[:3]
        elif _badPos:
            cols = [1.0, 0.2, 0.1]  # red if the position is bad
        else:
            cols = listCol

        try:
            _alias = obj.aliasing
            alias = getAliasSetting(_alias[0], 0)
        except Exception:
            alias = 0

        iCount, _selected = self._makeArrowIndices(drawList, indexEnd, vertexStart, 0, obj, arrowType)
        self._insertArrowItemVertices(True, True, _selected, cols, drawList, 1.0, iCount,
                                      indexing, obj, objNum, pxy, dims, 0, r, vertexPtr, w, alias, sx, sy, rx, ry, tnx,
                                      tny)

    def _removeArrow(self, spectrumView, objListView, delObj):
        """Remove an arrow from the list
        """

        drawList = self._GLArrows[objListView]

        indexOffset = 0
        numPoints = 0

        pp = 0
        while (pp < len(drawList.pids)):
            # check whether the peaks still exists
            obj = drawList.pids[pp]

            if obj and obj == delObj:
                offset = drawList.pids[pp + 1]
                numPoints = drawList.pids[pp + 2]

                indexStart = drawList.pids[pp + 6]
                indexEnd = drawList.pids[pp + 7]
                indexOffset = indexEnd - indexStart

                st, end = 4 * offset, 4 * (offset + numPoints)
                drawList.indices = np.delete(drawList.indices, np.s_[indexStart:indexEnd])
                drawList.vertices = np.delete(drawList.vertices, np.s_[st: end])
                drawList.attribs = np.delete(drawList.attribs, np.s_[st: end])
                drawList.offsets = np.delete(drawList.offsets, np.s_[st: end])
                drawList.colors = np.delete(drawList.colors, np.s_[st: end])

                drawList.pids = np.delete(drawList.pids, np.s_[pp:pp + GLDefs.LENPID])
                drawList.numVertices -= numPoints

                # subtract the offset from all the higher indices to account for the removed points
                drawList.indices[np.where(drawList.indices >= offset)] -= numPoints
                break

            else:
                pp += GLDefs.LENPID

        # clean up the rest of the list
        while (pp < len(drawList.pids)):
            drawList.pids[pp + 1] -= numPoints
            drawList.pids[pp + 6] -= indexOffset
            drawList.pids[pp + 7] -= indexOffset
            pp += GLDefs.LENPID

    def _updateHighlightedArrows(self, spectrumView, objListView):
        """update the highlighted arrows
        """

        # strip = self.strip
        # arrowType = strip.arrowType

        drawList = self._GLArrows[objListView]
        drawList.indices = np.array([], dtype=np.uint32)

        indexStart = 0
        indexEnd = 0
        vertexStart = 0

        listView = self.objectList(objListView)
        listCol = getAutoColourRgbRatio(objListView.arrowColour or GLDefs.DEFAULTCOLOUR, listView.spectrum,
                                        self.autoColour,
                                        getColours()[CCPNGLWIDGET_FOREGROUND])
        meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, listView.spectrum,
                                         self.autoColour,
                                         getColours()[CCPNGLWIDGET_FOREGROUND])
        meritEnabled = objListView.meritEnabled
        meritThreshold = objListView.meritThreshold

        _, _, arrowType, arrowSize, arrowMinimum, arrowWidth, r, w = self._getArrowWidths(spectrumView)

        _indexCount = 0
        for pp in range(0, len(drawList.pids), GLDefs.LENPID):

            # check whether the peaks still exists
            obj = drawList.pids[pp]
            offset = drawList.pids[pp + 1]
            numPoints = drawList.pids[pp + 2]

            if not obj.isDeleted:

                iCount, _selected = self._appendArrowIndices(drawList, vertexStart, 0, obj, arrowType)
                if _selected:
                    cols = self._GLParent.highlightColour[:3]
                elif obj.pointPositions and None in obj.pointPositions:
                    cols = [1.0, 0.2, 0.1]  # red if the position is bad
                else:
                    if meritEnabled and obj.figureOfMerit < meritThreshold:
                        cols = meritCol
                    else:
                        cols = listCol

                # called extraIndices, extraIndexCount above
                # make sure that links for the multiplets are added

                # _indexCount, extraIndices = 0, 0  # self.appendExtraIndices(drawList, indexStart + self.LENARR, obj)
                drawList.colors[offset * 4:(offset + self.ARROWCOLOURS) * 4] = (*cols,
                                                                                1.0) * self.ARROWCOLOURS  # numPoints

                drawList.pids[pp + 3:pp + 9] = (True, True, _selected,
                                                indexEnd, indexEnd + iCount + _indexCount,
                                                0)  # don't need to change planeIndex, but keep space for it
                indexEnd += (iCount + _indexCount)

            indexStart += numPoints
            vertexStart += numPoints

        drawList.pushIndexVBOIndices()
        drawList.pushTextArrayVBOColour()

    def _buildArrows(self, spectrumView, objListView):
        spectrum = spectrumView.spectrum

        if objListView not in self._GLArrows:
            self._GLArrows[objListView] = GLSymbolArray(GLContext=self,
                                                        spectrumView=spectrumView,
                                                        objListView=objListView)

        drawList = self._GLArrows[objListView]

        if drawList.renderMode == GLRENDERMODE_RESCALE:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode
            self._rescaleArrows(spectrumView=spectrumView, objListView=objListView)
            # self._rescaleLabels(spectrumView=spectrumView,
            #                     objListView=objListView,
            #                     drawList=self._GLLabels[objListView])

            drawList.defineAliasedIndexVBO()

        elif drawList.renderMode == GLRENDERMODE_REBUILD:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode

            # drawList.refreshMode = GLRENDERMODE_DRAW

            # find the correct scale to draw square pixels
            # don't forget to change when the axes change

            _, _, arrowType, arrowSize, arrowMinimum, arrowWidth, r, w = self._getArrowWidths(spectrumView)

            # change the ratio on resize
            drawList.refreshMode = GLREFRESHMODE_REBUILD
            drawList.drawMode = GL.GL_LINES
            drawList.fillMode = None

            # build the peaks VBO
            indexing = AttrDict()
            indexing.start = 0
            indexing.end = 0
            indexing.objNum = 0
            indexing.vertexPtr = 0
            indexing.vertexStart = 0

            pls = self.objectList(objListView)
            if not pls:
                return

            listCol = getAutoColourRgbRatio(objListView.arrowColour or GLDefs.DEFAULTCOLOUR, pls.spectrum,
                                            self.autoColour,
                                            getColours()[CCPNGLWIDGET_FOREGROUND])
            meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, pls.spectrum,
                                             self.autoColour,
                                             getColours()[CCPNGLWIDGET_FOREGROUND])
            meritEnabled = objListView.meritEnabled
            meritThreshold = objListView.meritThreshold

            spectrumFrequency = spectrum.spectrometerFrequencies
            strip = spectrumView.strip

            ind, vert = self._buildArrowsCount(spectrumView, objListView, drawList)
            if ind:
                for tcount, obj in enumerate(self.objects(pls)):

                    if meritEnabled and obj.figureOfMerit < meritThreshold:
                        cols = meritCol
                    else:
                        cols = listCol

                    self._insertArrowItem(strip, obj, cols, indexing, r, w,
                                          spectrumFrequency, arrowType, arrowSize, arrowMinimum, drawList,
                                          spectrumView, objListView)

            drawList.defineAliasedIndexVBO()

    #=================================================================================

    def _updateHighlightedSymbols(self, spectrumView, objListView):
        """update the highlighted symbols
        """

        strip = self.strip
        symbolType = strip.symbolType

        drawList = self._GLSymbols[objListView]
        drawList.indices = np.array([], dtype=np.uint32)

        indexStart = 0
        indexEnd = 0
        vertexStart = 0

        if symbolType == 0 or symbolType == 3:
            listView = self.objectList(objListView)
            listCol = getAutoColourRgbRatio(objListView.symbolColour or GLDefs.DEFAULTCOLOUR, listView.spectrum,
                                            self.autoColour,
                                            getColours()[CCPNGLWIDGET_FOREGROUND])
            meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, listView.spectrum,
                                             self.autoColour,
                                             getColours()[CCPNGLWIDGET_FOREGROUND])
            meritEnabled = objListView.meritEnabled
            meritThreshold = objListView.meritThreshold

            for pp in range(0, len(drawList.pids), GLDefs.LENPID):

                # check whether the peaks still exists
                obj = drawList.pids[pp]
                offset = drawList.pids[pp + 1]
                numPoints = drawList.pids[pp + 2]

                if not obj.isDeleted:

                    if symbolType == 0:  # cross
                        iCount, _selected = self._appendSquareSymbol(drawList, vertexStart, 0, obj)
                    else:  # plus
                        iCount, _selected = self._appendPlusSymbol(drawList, vertexStart, 0, obj)

                    if _selected:
                        cols = self._GLParent.highlightColour[:3]
                    elif obj.pointPositions and None in obj.pointPositions:
                        cols = [1.0, 0.2, 0.1]  # red if the position is bad
                    else:
                        if meritEnabled and obj.figureOfMerit < meritThreshold:
                            cols = meritCol
                        else:
                            cols = listCol

                    # called extraIndices, extraIndexCount above
                    # make sure that links for the multiplets are added

                    _indexCount, extraIndices = self.appendExtraIndices(drawList, indexStart + self.LENSQ, obj)
                    drawList.colors[offset * 4:(offset + self.POINTCOLOURS) * 4] = (*cols,
                                                                                    1.0) * self.POINTCOLOURS  # numPoints

                    drawList.pids[pp + 3:pp + 9] = (True, True, _selected,
                                                    indexEnd, indexEnd + iCount + _indexCount,
                                                    0)  # don't need to change planeIndex, but keep space for it
                    indexEnd += (iCount + _indexCount)

                indexStart += numPoints
                vertexStart += numPoints

            drawList.pushIndexVBOIndices()
            drawList.pushTextArrayVBOColour()

        elif symbolType == 1 or symbolType == 2:
            pass

        else:
            raise ValueError('GL Error: bad symbol type')

    def _insertSymbolItem(self, strip, obj, listCol, indexing, r, w,
                          spectrumFrequency, symbolType, drawList, spectrumView):
        """insert a single symbol to the end of the symbol list
        """

        # indexStart = indexing.start
        indexEnd = indexing.end
        objNum = indexing.objNum
        vertexPtr = indexing.vertexPtr
        vertexStart = indexing.vertexStart

        if not obj:
            return

        dims = self._spectrumSettings[spectrumView].dimensionIndices
        try:
            _pos = (obj.pointPositions[0] - 1, obj.height if obj.height is not None else 0)
            pxy = [_pos[dim] for dim in dims]
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        if self._isSelected(obj):
            cols = self._GLParent.highlightColour[:3]
        elif _badPos:
            cols = [1.0, 0.2, 0.1]  # red if the position is bad
        else:
            cols = listCol

        try:
            _alias = obj.aliasing
            if dims[0]:
                alias = getAliasSetting(0, _alias[0])
            else:
                alias = getAliasSetting(_alias[0], 0)
        except Exception:
            alias = 0

        if symbolType == 0:  # cross
            iCount, _selected = self._makeSquareSymbol(drawList, indexEnd, vertexStart, 0, obj)
        else:
            iCount, _selected = self._makePlusSymbol(drawList, indexEnd, vertexStart, 0, obj)

        self._insertSymbolItemVertices(True, True, _selected, cols, drawList, 1.0, iCount,
                                       indexing, obj, objNum, pxy, dims, 0, r, vertexPtr, w, alias)

    def _buildSymbols(self, spectrumView, objListView):
        spectrum = spectrumView.spectrum

        if objListView not in self._GLSymbols:
            self._GLSymbols[objListView] = GLSymbolArray(GLContext=self,
                                                         spectrumView=spectrumView,
                                                         objListView=objListView)

        drawList = self._GLSymbols[objListView]

        if drawList.renderMode == GLRENDERMODE_RESCALE:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode
            self._rescaleSymbols(spectrumView=spectrumView, objListView=objListView)
            # self._rescaleLabels(spectrumView=spectrumView,
            #                     objListView=objListView,
            #                     drawList=self._GLLabels[objListView])

            drawList.defineAliasedIndexVBO()

        elif drawList.renderMode == GLRENDERMODE_REBUILD:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode

            # drawList.refreshMode = GLRENDERMODE_DRAW

            # find the correct scale to draw square pixels
            # don't forget to change when the axes change

            _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

            # change the ratio on resize
            drawList.refreshMode = GLREFRESHMODE_REBUILD
            drawList.drawMode = GL.GL_LINES
            drawList.fillMode = None

            # build the peaks VBO
            indexing = AttrDict()
            indexing.start = 0
            indexing.end = 0
            indexing.objNum = 0
            indexing.vertexPtr = 0
            indexing.vertexStart = 0

            pls = self.objectList(objListView)
            if not pls:
                return

            listCol = getAutoColourRgbRatio(objListView.symbolColour or GLDefs.DEFAULTCOLOUR, pls.spectrum,
                                            self.autoColour,
                                            getColours()[CCPNGLWIDGET_FOREGROUND])
            meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, pls.spectrum,
                                             self.autoColour,
                                             getColours()[CCPNGLWIDGET_FOREGROUND])
            meritEnabled = objListView.meritEnabled
            meritThreshold = objListView.meritThreshold

            spectrumFrequency = spectrum.spectrometerFrequencies
            strip = spectrumView.strip

            ind, vert = self._buildSymbolsCount(spectrumView, objListView, drawList)
            if ind:
                for tcount, obj in enumerate(self.objects(pls)):

                    if meritEnabled and obj.figureOfMerit < meritThreshold:
                        cols = meritCol
                    else:
                        cols = listCol

                    self._insertSymbolItem(strip, obj, cols, indexing, r, w,
                                           spectrumFrequency, symbolType, drawList,
                                           spectrumView)

            drawList.defineAliasedIndexVBO()

    def _rescaleSymbols(self, spectrumView, objListView):
        """rescale symbols when the screen dimensions change
        """
        drawList = self._GLSymbols[objListView]
        if not drawList.numVertices:
            return

        # if drawList.refreshMode == GLREFRESHMODE_REBUILD:
        _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

        if symbolType == 0 or symbolType == 3:  # a cross/plus
            offsets, offLen = self._rescaleSymbolOffsets(r, w)
            for pp in range(0, len(drawList.pids), GLDefs.LENPID):
                indexStart = 4 * drawList.pids[pp + 1]
                drawList.vertices[indexStart:indexStart + offLen] = \
                    drawList.offsets[indexStart:indexStart + offLen] + offsets

        elif symbolType == 1 or symbolType == 2:
            pass
        else:
            raise ValueError('GL Error: bad symbol type')

    def _appendSymbol(self, spectrumView, objListView, obj):
        """Append a new symbol to the end of the list
        """
        drawList = self._GLSymbols[objListView]
        if obj in drawList.pids[0::GLDefs.LENPID]:
            return

        # find the correct scale to draw square pixels
        # don't forget to change when the axes change

        _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

        if symbolType == 0 or symbolType == 3:  # a cross/plus

            # change the ratio on resize
            drawList.refreshMode = GLREFRESHMODE_REBUILD
            drawList.drawMode = GL.GL_LINES
            drawList.fillMode = None

        # build the peaks VBO
        indexing = AttrDict()
        indexing.start = len(drawList.indices)
        indexing.end = len(drawList.indices)
        indexing.vertexStart = drawList.numVertices

        pls = self.objectList(objListView)

        listCol = getAutoColourRgbRatio(objListView.symbolColour or GLDefs.DEFAULTCOLOUR, pls.spectrum, self.autoColour,
                                        getColours()[CCPNGLWIDGET_FOREGROUND])
        meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, pls.spectrum, self.autoColour,
                                         getColours()[CCPNGLWIDGET_FOREGROUND])
        meritEnabled = objListView.meritEnabled
        meritThreshold = objListView.meritThreshold

        dims = self._spectrumSettings[spectrumView].dimensionIndices
        try:
            _pos = (obj.pointPositions[0] - 1, obj.height if obj.height is not None else 0)
            pxy = [_pos[dim] for dim in dims]
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        if self._isSelected(obj):
            cols = self._GLParent.highlightColour[:3]
        elif _badPos:
            cols = [1.0, 0.2, 0.1]  # red if the position is bad
        else:
            if meritEnabled and obj.figureOfMerit < meritThreshold:
                cols = meritCol
            else:
                cols = listCol

        try:
            _alias = obj.aliasing
            if dims[0]:
                alias = getAliasSetting(0, _alias[0])
            else:
                alias = getAliasSetting(_alias[0], 0)
        except Exception:
            alias = 0

        if symbolType == 0 or symbolType == 3:  # a cross/plus

            if symbolType == 0:  # cross
                iCount, _selected = self._appendSquareSymbol(drawList, indexing.vertexStart, 0, obj)
            else:  # plus
                iCount, _selected = self._appendPlusSymbol(drawList, indexing.vertexStart, 0, obj)

            self._appendSymbolItemVertices(True, True, _selected, cols, drawList, 1.0, iCount, indexing, obj, pxy, dims,
                                           0, r, w, alias)

    def _removeSymbol(self, spectrumView, objListView, delObj):
        """Remove a symbol from the list
        """

        drawList = self._GLSymbols[objListView]

        indexOffset = 0
        numPoints = 0

        pp = 0
        while (pp < len(drawList.pids)):
            # check whether the peaks still exists
            obj = drawList.pids[pp]

            if obj and obj == delObj:
                offset = drawList.pids[pp + 1]
                numPoints = drawList.pids[pp + 2]

                indexStart = drawList.pids[pp + 6]
                indexEnd = drawList.pids[pp + 7]
                indexOffset = indexEnd - indexStart

                st, end = 4 * offset, 4 * (offset + numPoints)
                drawList.indices = np.delete(drawList.indices, np.s_[indexStart:indexEnd])
                drawList.vertices = np.delete(drawList.vertices, np.s_[st: end])
                drawList.attribs = np.delete(drawList.attribs, np.s_[st: end])
                drawList.offsets = np.delete(drawList.offsets, np.s_[st: end])
                drawList.colors = np.delete(drawList.colors, np.s_[st: end])

                drawList.pids = np.delete(drawList.pids, np.s_[pp:pp + GLDefs.LENPID])
                drawList.numVertices -= numPoints

                # subtract the offset from all the higher indices to account for the removed points
                drawList.indices[np.where(drawList.indices >= offset)] -= numPoints
                break

            else:
                pp += GLDefs.LENPID

        # clean up the rest of the list
        while (pp < len(drawList.pids)):
            drawList.pids[pp + 1] -= numPoints
            drawList.pids[pp + 6] -= indexOffset
            drawList.pids[pp + 7] -= indexOffset
            pp += GLDefs.LENPID

    def _appendLabel(self, spectrumView, objListView, stringList, obj):
        """Append a new label to the end of the list
        """
        # spectrum = spectrumView.spectrum
        # spectrumFrequency = spectrum.spectrometerFrequencies

        # pls = peakListView.peakList
        pls = self.objectList(objListView)
        if stringList and obj in (sl.stringObject for sl in stringList):
            return

        if textOffset := obj.getTextOffset(objListView):
            tx, ty = textOffset
            _, _, symbolType, symbolWidth, r, w = self._getLabelOffsets(spectrumView, round(tx), round(ty))
        else:
            _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

        dims = self._spectrumSettings[spectrumView].dimensionIndices
        try:
            _pos = (obj.pointPositions[0] - 1, obj.height if obj.height is not None else 0)
            pxy = [_pos[dim] for dim in dims]
            _badPos = False
        except Exception:
            pxy = (0.0, 0.0)
            _badPos = True

        try:
            _alias = obj.aliasing
            if dims[0]:
                alias = getAliasSetting(0, _alias[0])
            else:
                alias = getAliasSetting(_alias[0], 0)
        except Exception:
            alias = 0

        if self._isSelected(obj):
            cols = self._GLParent.highlightColour[:3]
        elif _badPos:
            cols = [1.0, 0.2, 0.1]  # red for bad position
        else:
            listCol = getAutoColourRgbRatio(objListView.textColour or GLDefs.DEFAULTCOLOUR, pls.spectrum,
                                            self.autoColour,
                                            getColours()[CCPNGLWIDGET_FOREGROUND])
            meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR, pls.spectrum,
                                             self.autoColour,
                                             getColours()[CCPNGLWIDGET_FOREGROUND])
            meritEnabled = objListView.meritEnabled
            meritThreshold = objListView.meritThreshold

            if meritEnabled and obj.figureOfMerit < meritThreshold:
                cols = meritCol
            else:
                cols = listCol

        text = self.getLabelling(obj, self._GLParent)

        newString = GLString(text=text,
                             font=self._GLParent.getSmallFont(),
                             x=pxy[0], y=pxy[1],
                             ox=r, oy=w,
                             # ox=symbolWidth, oy=symbolWidth,
                             # x=self._screenZero[0], y=self._screenZero[1]
                             colour=(*cols, 1.0),
                             GLContext=self._GLParent,
                             obj=obj,
                             alias=alias)
        newString.stringOffset = None

        try:
            # pView = obj.getPeakView(objListView)
            pView = self.getViewFromListView(objListView, obj)
            pView.size = (newString.width, newString.height)
        except Exception as es:
            pass

        stringList.append(newString)

    def _rescaleLabels(self, spectrumView=None, objListView=None, drawList=None):
        """Rescale all labels to the new dimensions of the screen
        """
        symbolType = self.strip.symbolType

        if symbolType == 0 or symbolType == 3:  # a cross/plus

            _, _, symbolType, symbolWidth, r, w = self._getSymbolWidths(spectrumView)

            for drawStr in drawList.stringList:
                if textOffset := drawStr.stringObject.getTextOffset(objListView):
                    tx, ty = textOffset
                    _, _, _, _, tr, tw = self._getLabelOffsets(spectrumView, tx, ty)
                    drawStr.setStringOffset((tr, tw))
                else:
                    drawStr.setStringOffset((r, w))
                drawStr.pushTextArrayVBOAttribs()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Drawing
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
