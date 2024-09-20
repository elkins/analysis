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
__dateModified__ = "$dateModified: 2024-07-30 18:35:26 +0100 (Tue, July 30, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-12-11 17:51:39 +0000 (Fri, December 11, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from ccpn.core.lib.peakUtils import _getScreenPeakAnnotation, _getPeakAnnotation, _getPeakClusterId
from ccpn.ui.gui.guiSettings import getColours, CCPNGLWIDGET_MULTIPLETLINK
from ccpn.ui.gui.lib.OpenGL import CcpnOpenGLDefs as GLDefs
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLLabelling import DEFAULTLINECOLOUR, GLLabelling, GL1dLabelling
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import getAliasSetting
from ccpn.util.Colour import getAutoColourRgbRatio


class GLmultipletListMethods():
    """Class of methods common to 1d and Nd multiplets
    This is added to the Multiplet Classes below and doesn't require an __init__
    """

    LENSQ = GLDefs.LENSQMULT
    LENSQ2 = GLDefs.LENSQ2MULT
    LENSQ4 = GLDefs.LENSQ4MULT
    POINTCOLOURS = GLDefs.POINTCOLOURSMULT

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Predefined indices/vertex lists
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    _circleVertices = np.array((7, 9, 9, 10, 10, 6, 6, 11, 11, 12, 12, 8,
                                8, 13, 13, 14, 14, 5, 5, 15, 15, 16, 16, 7), dtype=np.uint32)

    _squareMultSymbol = ((np.append(np.array((0, 1, 2, 3), dtype=np.uint32), _circleVertices),
                          np.append(np.array((0, 1, 2, 3, 0, 2, 2, 1, 0, 3, 3, 1), dtype=np.uint32), _circleVertices)),
                         (np.append(np.array((0, 4, 4, 3, 3, 0), dtype=np.uint32), _circleVertices),
                          np.append(np.array((0, 4, 4, 3, 3, 0, 0, 2, 2, 1, 3, 1), dtype=np.uint32), _circleVertices)),
                         (np.append(np.array((2, 4, 4, 1, 1, 2), dtype=np.uint32), _circleVertices),
                          np.append(np.array((2, 4, 4, 1, 1, 2, 0, 2, 0, 3, 3, 1), dtype=np.uint32), _circleVertices)))

    _squareMultSymbolLen = tuple(tuple(len(sq) for sq in squareList) for squareList in _squareMultSymbol)

    _plusMultSymbol = ((np.append(np.array((5, 6, 7, 8), dtype=np.uint32), _circleVertices),
                        np.append(np.array((5, 6, 7, 8, 0, 2, 2, 1, 0, 3, 3, 1), dtype=np.uint32), _circleVertices)),
                       (np.append(np.array((6, 4, 4, 5, 4, 8), dtype=np.uint32), _circleVertices),
                        np.append(np.array((6, 4, 4, 5, 4, 8, 0, 2, 2, 1, 3, 1, 0, 3), dtype=np.uint32), _circleVertices)),
                       (np.append(np.array((6, 4, 4, 5, 4, 7), dtype=np.uint32), _circleVertices),
                        np.append(np.array((6, 4, 4, 5, 4, 7, 0, 2, 2, 1, 3, 1, 0, 3), dtype=np.uint32), _circleVertices)))

    _plusMultSymbolLen = tuple(tuple(len(pl) for pl in plusList) for plusList in _plusMultSymbol)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # List handlers
    #   The routines that have to be changed when accessing different named
    #   lists.
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _isSelected(self, multiplet):
        """return True if the obj in the defined object list
        """
        if getattr(self, '_caching', False):
            if self._objCache is None:
                self._objCache = list(id(obj) for obj in self.current.multiplets)  # this is faster than using __eq__
            return id(multiplet) in self._objCache

        else:
            objs = self.current.multiplets
            return multiplet in objs

    @staticmethod
    def objects(obj):
        """return the multiplets attached to the object
        """
        return obj.multiplets

    @staticmethod
    def objectList(obj):
        """return the multipletList attached to the multiplet
        """
        if not obj.isDeleted:
            return obj.multipletList

    @staticmethod
    def listViews(multipletList):
        """Return the multipletListViews attached to the multipletList
        """
        if multipletList.isDeleted:
            return ()

        return multipletList.multipletListViews

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # List specific routines
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def getLabelling(obj, parent):
        """get the object label based on the current labelling method
        """
        labelType = parent._multipletLabelling

        text = '---'
        if pks := obj.peaks:

            # grab the information from the first peak (they should all be the same)
            pk = pks[0]
            if labelType == 0:
                # return the short code form
                text = _getScreenPeakAnnotation(pk, useShortCode=True)
            elif labelType == 1:
                # return the long form
                text = _getScreenPeakAnnotation(pk, useShortCode=False)
            elif labelType == 2:
                # return the original pid
                # text = _getPeakAnnotation(obj)
                text = _getScreenPeakAnnotation(pk, useShortCode=False, usePid=True)
            elif labelType == 3:
                # return the minimal form
                text = _getScreenPeakAnnotation(pk, useShortCode=True, useMinimalCode=True)
            elif labelType == 4:
                # return the pid for the multiplet rather than the id - clearer when mixed
                text = obj.pid
            elif labelType == 5:
                text = _getPeakClusterId(pk)
            elif labelType == 6:
                # return the peak annotation
                text = _getPeakAnnotation(obj)

        # no peak assignment from here
        elif labelType == 4:
            # return the minimal form
            text = obj.pid
        elif labelType == 6:
            # return the multiplet annotation
            text = _getPeakAnnotation(obj)

        return text

    @staticmethod
    def extraIndicesCount(multiplet):
        """Calculate how many indices to add
        Returns the size of array needed to hold the indices, see insertExtraIndices
        """
        return 2 * len(multiplet.peaks) if multiplet.peaks else 0

    @staticmethod
    def extraVerticesCount(multiplet):
        """Calculate how many vertices to add
        """
        return (len(multiplet.peaks) + 1) if multiplet.peaks else 0

    @staticmethod
    def appendExtraIndices(drawList, index, multiplet):
        """Add extra indices to the index list
        Returns the number of unique indices NOT the length of the appended list
        """
        if not multiplet.peaks:
            return 0, 0

        insertNum = len(multiplet.peaks)
        drawList.indices = np.append(drawList.indices, np.array(tuple(val for ii in range(insertNum)
                                                                      for val in (index, 1 + index + ii)), dtype=np.uint32))
        return 2 * insertNum, insertNum + 1

    @staticmethod
    def insertExtraIndices(drawList, indexPtr, index, multiplet):
        """insert extra indices into the index list
        Returns (len, ind)
            len: length of the inserted array
            ind: number of unique indices
        """
        if not multiplet.peaks:
            return 0, 0

        insertNum = len(multiplet.peaks)
        drawList.indices[indexPtr:indexPtr + 2 * insertNum] = tuple(val for ii in range(insertNum)
                                                                    for val in (index, 1 + index + ii))
        return 2 * insertNum, insertNum + 1

    def _getSquareSymbolCount(self, planeIndex, obj):
        """returns the number of indices required for the symbol based on the planeIndex
        type of planeIndex - currently 0/1/2 indicating whether normal, infront or behind
        currently visible planes
        """
        return self._squareMultSymbolLen[planeIndex % 3][self._isSelected(obj)]

    def _makeSquareSymbol(self, drawList, indexEnd, vertexStart, planeIndex, obj):
        """Make a new square symbol based on the planeIndex type.
        """
        _selected = self._isSelected(obj)
        _indices = self._squareMultSymbol[planeIndex % 3][_selected] + vertexStart
        iCount = len(_indices)
        drawList.indices[indexEnd:indexEnd + iCount] = _indices

        return iCount, _selected

    def _appendSquareSymbol(self, drawList, vertexStart, planeIndex, obj):
        """Append a new square symbol based on the planeIndex type.
        """
        _selected = self._isSelected(obj)
        _indices = self._squareMultSymbol[planeIndex % 3][_selected] + vertexStart
        iCount = len(_indices)
        drawList.indices = np.append(drawList.indices, _indices)

        return iCount, _selected

    def _getPlusSymbolCount(self, planeIndex, obj):
        """returns the number of indices required for the symbol based on the planeIndex
        type of planeIndex - currently 0/1/2 indicating whether normal, infront or behind
        currently visible planes
        """
        return self._plusMultSymbolLen[planeIndex % 3][self._isSelected(obj)]

    def _makePlusSymbol(self, drawList, indexEnd, vertexStart, planeIndex, obj):
        """Make a new plus symbol based on the planeIndex type.
        """
        _selected = self._isSelected(obj)
        _indices = self._plusMultSymbol[planeIndex % 3][_selected] + vertexStart
        iCount = len(_indices)
        drawList.indices[indexEnd:indexEnd + iCount] = _indices

        return iCount, _selected

    def _appendPlusSymbol(self, drawList, vertexStart, planeIndex, obj):
        """Append a new plus symbol based on the planeIndex type.
        """
        _selected = self._isSelected(obj)
        _indices = self._plusMultSymbol[planeIndex % 3][_selected] + vertexStart
        iCount = len(_indices)
        drawList.indices = np.append(drawList.indices, _indices)

        return iCount, _selected

    def _rescaleSymbolOffsets(self, r, w):
        return np.array([-r, -w, 0, 0,
                         +r, +w,  0, 0,
                         +r, -w,  0, 0,
                         -r, +w,  0, 0,
                         0, 0,  0, 0,
                         0, -w,  0, 0,
                         0, +w,  0, 0,
                         +r, 0,  0, 0,
                         -r, 0, 0, 0,
                         r * 0.85, w * 0.50, 0, 0,
                         r * 0.5, w * 0.85, 0, 0,
                         - r * 0.5, w * 0.85, 0, 0,
                         - r * 0.85, w * 0.50, 0, 0,
                         - r * 0.85, - w * 0.50, 0, 0,
                         - r * 0.5, - w * 0.85, 0, 0,
                         + r * 0.5, - w * 0.85, 0, 0,
                         + r * 0.85, - w * 0.50,  0, 0], np.float32), self.LENSQ4

    # class GLmultipletNdLabelling(GLmultipletListMethods, GLLabelling):  #, GLpeakNdLabelling):
    #     """Class to handle symbol and symbol labelling for Nd displays
    #     """
    #
    #     def __init__(self, parent=None, strip=None, name=None, resizeGL=False):
    #         """Initialise the class
    #         """
    #         super(GLmultipletNdLabelling, self).__init__(parent=parent, strip=strip, name=name, resizeGL=resizeGL)
    #
    #         self.autoColour = self._GLParent.SPECTRUMNEGCOLOUR

    def appendExtraVertices(self, drawList, pIndex, multiplet, pxy, colour, fade):
        """Add extra vertices to the vertex list
        """
        if not multiplet.peaks:
            return 0

        col = multiplet.multipletList.lineColour
        cols = getAutoColourRgbRatio(col or DEFAULTLINECOLOUR, multiplet.multipletList.spectrum, self.autoColour,
                                     getColours()[CCPNGLWIDGET_MULTIPLETLINK])

        try:
            peakAlias = multiplet.peaks[0].aliasing
            alias = getAliasSetting(peakAlias[pIndex[0]], peakAlias[pIndex[1]])
        except Exception:
            alias = 0

        posList = (pxy[0], pxy[1], alias, 0.0)  # p0[:]  # copy
        for peak in multiplet.peaks:
            # get the correct coordinates based on the axisCodes
            pp = peak.pointPositions
            try:
                _x, _y = pp[pIndex[0]] - 1.0, pp[pIndex[1]] - 1.0
                posList += (_x, _y, alias, 0.0)
            except Exception:
                posList += (0, 0, alias, 0)  # add the bad-point

        numVertices = len(multiplet.peaks) + 1
        drawList.vertices = np.append(drawList.vertices, np.array(posList, dtype=np.float32))
        drawList.colors = np.append(drawList.colors, np.array((*cols, fade) * numVertices, dtype=np.float32))
        drawList.attribs = np.append(drawList.attribs, np.array((alias, 0.0, 0.0, 0.0) * numVertices, dtype=np.float32))
        drawList.offsets = np.append(drawList.offsets, np.array((pxy[0], pxy[1], 0.0, 0.0) * numVertices, dtype=np.float32))

        return numVertices

    def insertExtraVertices(self, drawList, vertexPtr, pIndex, multiplet, pxy, colour, fade):
        """insert extra vertices into the vertex list
        """
        if not multiplet.peaks:
            return 0

        col = multiplet.multipletList.lineColour
        cols = getAutoColourRgbRatio(col or DEFAULTLINECOLOUR, multiplet.multipletList.spectrum, self.autoColour,
                                     getColours()[CCPNGLWIDGET_MULTIPLETLINK])

        try:
            peakAlias = multiplet.peaks[0].aliasing
            alias = getAliasSetting(peakAlias[pIndex[0]], peakAlias[pIndex[1]])
        except Exception:
            alias = 0

        posList = (pxy[0], pxy[1], alias, 0.0)  # p0[:]  # copy
        for peak in multiplet.peaks:
            # get the correct coordinates based on the axisCodes
            pp = peak.pointPositions
            try:
                _x, _y = pp[pIndex[0]] - 1.0, pp[pIndex[1]] - 1.0
                posList += (_x, _y, alias, 0.0)
            except Exception:
                posList += (0, 0, alias, 0.0)  # add the bad-point

        numVertices = len(multiplet.peaks) + 1
        st, end = vertexPtr, vertexPtr + 4 * numVertices
        drawList.vertices[st: end] = posList
        drawList.colors[st: end] = (*cols, fade) * numVertices
        drawList.attribs[st: end] = (alias, 0.0, 0.0, 0.0) * numVertices
        drawList.offsets[st: end] = (pxy[0], pxy[1], 0.0, 0.0) * numVertices

        return numVertices

    def _insertSymbolItemVertices(self, _isInFlankingPlane, _isInPlane, _selected, cols, drawList, fade, iCount, indexing, obj,
                                  objNum, pxy, pIndex, planeIndex, r, vertexPtr, w, alias):

        st, end = vertexPtr, vertexPtr + self.LENSQ4
        drawList.vertices[st: end] = (pxy[0] - r, pxy[1] - w, alias, 0.0,
                                      pxy[0] + r, pxy[1] + w, alias, 0.0,
                                      pxy[0] + r, pxy[1] - w, alias, 0.0,
                                      pxy[0] - r, pxy[1] + w, alias, 0.0,
                                      pxy[0], pxy[1], alias, 0.0,
                                      pxy[0], pxy[1] - w, alias, 0.0,
                                      pxy[0], pxy[1] + w, alias, 0.0,
                                      pxy[0] + r, pxy[1], alias, 0.0,
                                      pxy[0] - r, pxy[1], alias, 0.0,
                                      pxy[0] + (r * 0.85), pxy[1] + (w * 0.50), alias, 0.0,
                                      pxy[0] + (r * 0.5), pxy[1] + (w * 0.85), alias, 0.0,
                                      pxy[0] - (r * 0.5), pxy[1] + (w * 0.85), alias, 0.0,
                                      pxy[0] - (r * 0.85), pxy[1] + (w * 0.50), alias, 0.0,
                                      pxy[0] - (r * 0.85), pxy[1] - (w * 0.50), alias, 0.0,
                                      pxy[0] - (r * 0.5), pxy[1] - (w * 0.85), alias, 0.0,
                                      pxy[0] + (r * 0.5), pxy[1] - (w * 0.85), alias, 0.0,
                                      pxy[0] + (r * 0.85), pxy[1] - (w * 0.50), alias, 0.0,
                                      )
        drawList.colors[st: end] = (*cols, fade) * self.LENSQ
        drawList.attribs[st: end] = (alias, 0.0, 0.0, 0.0) * self.LENSQ
        drawList.offsets[st: end] = (pxy[0], pxy[1], 0.0, 0.0) * self.LENSQ

        # add extra indices
        extraIndices, extraIndexCount = self.insertExtraIndices(drawList, indexing.end + iCount, indexing.start + self.LENSQ, obj)
        # add extra vertices for the multiplet
        extraVertices = self.insertExtraVertices(drawList, vertexPtr + self.LENSQ4, pIndex, obj,
                                                 pxy, (*cols, fade), fade)
        # keep a pointer to the obj
        drawList.pids[objNum:objNum + GLDefs.LENPID] = (obj, drawList.numVertices, (self.LENSQ + extraVertices),
                                                        _isInPlane, _isInFlankingPlane, _selected,
                                                        indexing.end, indexing.end + iCount + extraIndices,
                                                        planeIndex, 0, 0, 0)

        indexing.start += (self.LENSQ + extraIndexCount)
        indexing.end += (iCount + extraIndices)
        drawList.numVertices += (self.LENSQ + extraVertices)
        indexing.objNum += GLDefs.LENPID
        indexing.vertexPtr += (4 * (self.LENSQ + extraVertices))
        indexing.vertexStart += (self.LENSQ + extraVertices)

    def _appendSymbolItemVertices(self, _isInFlankingPlane, _isInPlane, _selected, cols, drawList, fade, iCount, indexing, obj, pxy, pIndex,
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
                                                                   pxy[0] + (r * 0.85), pxy[1] + (w * 0.50), alias, 0.0,
                                                                   pxy[0] + (r * 0.5), pxy[1] + (w * 0.85), alias, 0.0,
                                                                   pxy[0] - (r * 0.5), pxy[1] + (w * 0.85), alias, 0.0,
                                                                   pxy[0] - (r * 0.85), pxy[1] + (w * 0.50), alias, 0.0,
                                                                   pxy[0] - (r * 0.85), pxy[1] - (w * 0.50), alias, 0.0,
                                                                   pxy[0] - (r * 0.5), pxy[1] - (w * 0.85), alias, 0.0,
                                                                   pxy[0] + (r * 0.5), pxy[1] - (w * 0.85), alias, 0.0,
                                                                   pxy[0] + (r * 0.85), pxy[1] - (w * 0.50), alias, 0.0,
                                                                   ), dtype=np.float32))
        # drawList.vertices = np.append(drawList.vertices, np.array((- r, - w, 0.0, 0.0,
        #                                                            + r, + w, 0.0, 0.0,
        #                                                            + r, - w, 0.0, 0.0,
        #                                                            - r, + w, 0.0, 0.0,
        #                                                            0.0, 0.0, 0.0, 0.0,
        #                                                            0.0, - w, 0.0, 0.0,
        #                                                            0.0, + w, 0.0, 0.0,
        #                                                            + r, 0.0, 0.0, 0.0,
        #                                                            - r, 0.0, 0.0, 0.0,
        #                                                            + (r * 0.85), + (w * 0.50), 0.0, 0.0,
        #                                                            + (r * 0.5), + (w * 0.85), 0.0, 0.0,
        #                                                            - (r * 0.5), + (w * 0.85), 0.0, 0.0,
        #                                                            - (r * 0.85), + (w * 0.50), 0.0, 0.0,
        #                                                            - (r * 0.85), - (w * 0.50), 0.0, 0.0,
        #                                                            - (r * 0.5), - (w * 0.85), 0.0, 0.0,
        #                                                            + (r * 0.5), - (w * 0.85), 0.0, 0.0,
        #                                                            + (r * 0.85), - (w * 0.50), 0.0, 0.0,
        #                                                            ), dtype=np.float32))
        drawList.colors = np.append(drawList.colors, np.array((*cols, fade) * self.LENSQ, dtype=np.float32))
        drawList.attribs = np.append(drawList.attribs, np.array((alias, 0.0, 0.0, 0.0) * self.LENSQ, dtype=np.float32))
        drawList.offsets = np.append(drawList.offsets, np.array((pxy[0], pxy[1], 0.0, 0.0) * self.LENSQ, dtype=np.float32))

        # add extra indices
        _indexCount, extraIndices = self.appendExtraIndices(drawList, indexing.vertexStart + self.LENSQ, obj)
        # add extra vertices for the multiplet
        extraVertices = self.appendExtraVertices(drawList, pIndex, obj,
                                                 pxy, (*cols, fade), fade)
        # keep a pointer to the obj
        drawList.pids = np.append(drawList.pids, (obj, drawList.numVertices, (self.LENSQ + extraVertices),
                                                  _isInPlane, _isInFlankingPlane, _selected,
                                                  indexing.end, indexing.end + iCount + _indexCount,
                                                  planeIndex, 0, 0, 0))

        indexing.start += (self.LENSQ + extraIndices)
        indexing.end += (iCount + _indexCount)
        drawList.numVertices += (self.LENSQ + extraVertices)
        indexing.vertexStart += (self.LENSQ + extraVertices)

    @staticmethod
    def getViewFromListView(multipletListView, obj):
        """Get the multipletView from the MultipletListView.
        """
        return obj.getMultipletView(multipletListView)


class GLmultipletNdLabelling(GLmultipletListMethods, GLLabelling):  #, GLpeakNdLabelling):
    """Class to handle symbol and symbol labelling for Nd displays
    """

    def __init__(self, parent=None, strip=None, name=None, enableResize=False):
        """Initialise the class
        """
        super().__init__(parent=parent, strip=strip, name=name, enableResize=enableResize)

        # use different colouring
        self.autoColour = self._GLParent.SPECTRUMNEGCOLOUR

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # List specific routines
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def objIsInVisiblePlanes(self, spectrumView, multiplet, viewOutOfPlaneMultiplets=True):
        """Return whether in plane or flanking plane

        :param spectrumView: current spectrumView containing multiplets
        :param multiplet: multiplet to test
        :param viewOutOfPlaneMultiplets: whether to show outofplane multiplets, defaults to true
        :return: inPlane - true/false
                inFlankingPlane - true/false
                type of outofplane - currently 0/1/2 indicating whether normal, infront or behind
                fade for colouring
        """
        try:
            # try to read from the cache
            return self._objIsInVisiblePlanesCache[spectrumView][multiplet]
        except Exception:
            # calculate and store the new value
            value = self._objIsInVisiblePlanes(spectrumView, multiplet, viewOutOfPlaneMultiplets=viewOutOfPlaneMultiplets)
            if spectrumView not in self._objIsInVisiblePlanesCache:
                self._objIsInVisiblePlanesCache[spectrumView] = {multiplet: value}
            else:
                self._objIsInVisiblePlanesCache[spectrumView][multiplet] = value
            return value

    def _objIsInVisiblePlanes(self, spectrumView, multiplet, viewOutOfPlaneMultiplets=True):
        """Return whether in plane or flanking plane

        :param spectrumView: current spectrumView containing multiplets
        :param multiplet: multiplet to test
        :param viewOutOfPlaneMultiplets: whether to show outofplane multiplets, defaults to true
        :return: inPlane - true/false
                inFlankingPlane - true/false
                type of outofplane - currently 0/1/2 indicating whether normal, infront or behind
                fade for colouring
        """
        pntPos = multiplet.pointPositions
        if not pntPos:
            return False, False, 0, 1.0

        displayIndices = self._GLParent.visiblePlaneDimIndices[spectrumView]
        if displayIndices is None:
            return False, False, 0, 1.0

        inPlane = True
        endPlane = 0

        for ii, displayIndex in enumerate(displayIndices[2:]):
            if displayIndex is not None:

                # If no axis matches the index may be None
                zPosition = pntPos[displayIndex]
                if not zPosition:
                    return False, False, 0, 1.0
                actualPlane = int(zPosition + 0.5) - (1 if zPosition >= 0 else 2)

                # settings = self._spectrumSettings[spectrumView]
                # actualPlane = int(settings[GLDefs.SPECTRUM_VALUETOPOINT][ii](zPosition) + 0.5) - 1
                # planes = (self._GLParent.visiblePlaneList[spectrumView])[ii]

                thisVPL = self._GLParent.visiblePlaneList[spectrumView]
                if not thisVPL:
                    return False, False, 0, 1.0

                planes = thisVPL[ii]
                if not (planes and planes[0]):
                    return False, False, 0, 1.0

                visiblePlaneList = planes[0]
                vplLen = len(visiblePlaneList)

                if actualPlane in visiblePlaneList[1:vplLen - 1]:
                    inPlane &= True

                # exit if don't want to view outOfPlane multiplets
                elif not viewOutOfPlaneMultiplets:
                    return False, False, 0, 1.0

                elif actualPlane == visiblePlaneList[0]:
                    inPlane = False
                    endPlane = 1

                elif actualPlane == visiblePlaneList[vplLen - 1]:
                    inPlane = False
                    endPlane = 2

                else:
                    # catch any stray conditions
                    return False, False, 0, 1.0

        return inPlane, (not inPlane), endPlane, GLDefs.INPLANEFADE if inPlane else GLDefs.OUTOFPLANEFADE


class GLmultiplet1dLabelling(GL1dLabelling, GLmultipletNdLabelling):
    """Class to handle symbol and symbol labelling for 1d displays
    """

    # def __init__(self, parent=None, strip=None, name=None, resizeGL=False):
    #     """Initialise the class
    #     """
    #     super(GLmultiplet1dLabelling, self).__init__(parent=parent, strip=strip, name=name, resizeGL=resizeGL)
    #
    #     self.autoColour = self._GLParent.SPECTRUMNEGCOLOUR

    def appendExtraVertices(self, drawList, pIndex, multiplet, pxy, colour, fade):
        """Add extra vertices to the vertex list
        """
        if not multiplet.peaks:
            return 0

        col = multiplet.multipletList.lineColour
        cols = getAutoColourRgbRatio(col or DEFAULTLINECOLOUR, multiplet.multipletList.spectrum, self.autoColour,
                                     getColours()[CCPNGLWIDGET_MULTIPLETLINK])

        try:
            peakAlias = multiplet.peaks[0].aliasing
            if pIndex[0]:  # check that the 1d-dimensions are reversed :|
                alias = getAliasSetting(0, peakAlias[0])
            else:
                alias = getAliasSetting(peakAlias[0], 0)
        except Exception:
            alias = 0

        posList = (pxy[0], pxy[1], alias, 0.0)  # p0[:]  # copy
        for peak in multiplet.peaks:
            # get the correct coordinates based on the axisCodes
            try:
                _pos = (peak.pointPositions[0] - 1, peak.height if peak.height is not None else 0)
                _p1 = [_pos[dim] for dim in pIndex]
                # posList += p1
                posList += (_p1[0], _p1[1], alias, 0.0)
            except Exception:
                posList += (0, 0, alias, 0)  # add the bad-point

        numVertices = len(multiplet.peaks) + 1
        drawList.vertices = np.append(drawList.vertices, np.array(posList, dtype=np.float32))
        drawList.colors = np.append(drawList.colors, np.array((*cols, fade) * numVertices, dtype=np.float32))
        drawList.attribs = np.append(drawList.attribs, np.array((alias, 0.0, 0.0, 0.0) * numVertices, dtype=np.float32))
        drawList.offsets = np.append(drawList.offsets, np.array((pxy[0], pxy[1], 0.0, 0.0) * numVertices, dtype=np.float32))

        return numVertices

    def insertExtraVertices(self, drawList, vertexPtr, pIndex, multiplet, pxy, colour, fade):
        """insert extra vertices into the vertex list
        """
        if not multiplet.peaks:
            return 0

        col = multiplet.multipletList.lineColour
        cols = getAutoColourRgbRatio(col or DEFAULTLINECOLOUR, multiplet.multipletList.spectrum, self.autoColour,
                                     getColours()[CCPNGLWIDGET_MULTIPLETLINK])

        try:
            peakAlias = multiplet.peaks[0].aliasing
            if pIndex[0]:  # check that the 1d-dimensions are reversed :|
                alias = getAliasSetting(0, peakAlias[0])
            else:
                alias = getAliasSetting(peakAlias[0], 0)
        except Exception:
            alias = 0

        posList = (pxy[0], pxy[1], alias, 0.0)  # p0[:]  # copy
        for peak in multiplet.peaks:
            # get the correct coordinates based on the axisCodes
            try:
                _pos = (peak.pointPositions[0] - 1, peak.height if peak.height is not None else 0)
                _p1 = [_pos[dim] for dim in pIndex]
                # posList += p1
                posList += (_p1[0], _p1[1], alias, 0.0)
            except Exception:
                posList += (0, 0, alias, 0.0)  # add the bad-point

        numVertices = len(multiplet.peaks) + 1
        st, end = vertexPtr, vertexPtr + 4 * numVertices
        drawList.vertices[st: end] = posList
        drawList.colors[st: end] = (*cols, fade) * numVertices
        drawList.attribs[st: end] = (alias, 0.0, 0.0, 0.0) * numVertices
        drawList.offsets[st: end] = (pxy[0], pxy[1], 0.0, 0.0) * numVertices

        return numVertices

    def objIsInVisiblePlanes(self, spectrumView, obj, viewOutOfPlanePeaks=True):
        """Get the current object is in visible planes settings
        """
        return True, False, 0, 1.0
