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
__dateModified__ = "$dateModified: 2024-09-09 19:03:26 +0100 (Mon, September 09, 2024) $"
__version__ = "$Revision: 3.2.6 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2018-12-20 15:44:35 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from PyQt5 import QtGui
from itertools import zip_longest, product

from ccpn.core.lib.AxisCodeLib import getAxisCodeMatchIndices
from ccpn.core.lib.peakUtils import movePeak
from ccpn.core.lib.SpectrumLib import CoherenceOrder
from ccpn.ui.gui.lib.OpenGL import CcpnOpenGLDefs as GLDefs, GL
from ccpn.ui.gui.lib.mouseEvents import getCurrentMouseMode, PICK
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import CcpnGLWidget, GLVertexArray, GLRENDERMODE_DRAW, \
    GLRENDERMODE_RESCALE
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import YAXISUNITS1D, SPECTRUM_VALUEPERPOINT
import ccpn.util.Phasing as Phasing
from ccpn.util.Constants import MOUSEDICTSTRIP, AXIS_FULLATOMNAME, AXIS_MATCHATOMTYPE
from ccpn.util.Logging import getLogger


class GuiNdWidget(CcpnGLWidget):
    is1D = False
    XDIRECTION = -1.0
    YDIRECTION = -1.0
    SPECTRUMPOSCOLOUR = 'positiveContourColour'
    SPECTRUMNEGCOLOUR = 'negativeContourColour'
    AXIS_INSIDE = False

    def __init__(self, strip=None, mainWindow=None, stripIDLabel=None):
        super().__init__(strip=strip, mainWindow=mainWindow, stripIDLabel=stripIDLabel)

    def _mouseInPeak(self, xPosition, yPosition, firstOnly=False):
        """Find the peaks under the mouse.
        If firstOnly is true, return only the first item, else an empty list
        """
        xPositions = [xPosition - self.symbolX, xPosition + self.symbolX]
        yPositions = [yPosition - self.symbolY, yPosition + self.symbolY]
        if len(self._orderedAxes) > 2:
            zPositions = self._orderedAxes[2].region
        else:
            zPositions = None

        peaks = []
        _data2Obj = self.strip.project._data2Obj
        pixX, pixY = self.strip._CcpnGLWidget.pixelX, self.strip._CcpnGLWidget.pixelY
        sgnX, sgnY = np.sign(pixX), np.sign(pixY)

        for spectrumView in self.strip.spectrumViews:
            dimX, dimY = spectrumView.dimensionIndices[:2]

            for peakListView in spectrumView.peakListViews:
                if not (spectrumView.isDisplayed and
                        peakListView.isDisplayed and
                        (labelling := self._GLPeaks._GLLabels.get(peakListView))):
                    continue

                for drawList in labelling.stringList:
                    try:
                        peak = drawList.stringObject
                        pView = peak.getPeakView(peakListView)
                        _pos = peak.ppmPositions
                        px, py = float(_pos[dimX]), float(_pos[dimY])
                        tx, ty = pView.textOffset
                        if not tx and not ty:
                            # pixels
                            tx, ty = self._symbolSize, self._symbolSize
                            # ppm
                            # tx, ty = self.symbolX, self.symbolY

                        # find the bounds of the label
                        # pixels
                        # minX, maxX = min(_ll := px + tx * pixX, _rr := px + (tx + drawList.width) * pixX), max(_ll, _rr)
                        # minY, maxY = min(_ll := py + ty * pixY, _rr := py + (ty + drawList.height) * pixY), max(_ll, _rr)
                        # ppm
                        minX, maxX = min(_ll := px + tx * sgnX,
                                         _rr := px + tx * sgnX + drawList.width * pixX), max(_ll, _rr)
                        minY, maxY = min(_ll := py + ty * sgnY,
                                         _rr := py + ty * sgnY + drawList.height * pixY), max(_ll, _rr)

                        if len(peak.axisCodes) > 2 and zPositions is not None:
                            # zAxis = spectrumIndices[2]
                            if (xPositions[0] < px < xPositions[1]
                                and yPositions[0] < py < yPositions[1]) or \
                                    (minX < xPosition < maxX and minY < yPosition < maxY):

                                # within the XY bounds so check whether inPlane
                                _isInPlane, _isInFlankingPlane, planeIndex, fade = \
                                    self._GLPeaks.objIsInVisiblePlanes(spectrumView, peak)
                                if _isInPlane or _isInFlankingPlane:
                                    peaks.append(peak)

                        elif (xPositions[0] < px < xPositions[1]
                              and yPositions[0] < py < yPositions[1]) or \
                                (minX < xPosition < maxX and minY < yPosition < maxY):
                            peaks.append(peak)

                    except Exception:
                        continue

        # put the selected peaks to the front of the list
        currentPeaks = set(self.current.peaks)
        peaks = [pk for pk in peaks if pk in currentPeaks] + [pk for pk in peaks if pk not in currentPeaks]

        return peaks[:1] if firstOnly else peaks

    def _mouseInPeakLabel(self, xPosition, yPosition, firstOnly=False):
        """Find the peaks under the mouse.
        If firstOnly is true, return only the first item, else an empty list
        """
        # xPositions = [xPosition - self.symbolX, xPosition + self.symbolX]
        # yPositions = [yPosition - self.symbolY, yPosition + self.symbolY]
        if len(self._orderedAxes) > 2:
            zPositions = self._orderedAxes[2].region
        else:
            zPositions = None

        peaks = []
        _data2Obj = self.strip.project._data2Obj
        pixX, pixY = self.strip._CcpnGLWidget.pixelX, self.strip._CcpnGLWidget.pixelY
        sgnX, sgnY = np.sign(pixX), np.sign(pixY)

        for spectrumView in self.strip.spectrumViews:
            dimX, dimY = spectrumView.dimensionIndices[:2]

            for peakListView in spectrumView.peakListViews:
                if not (spectrumView.isDisplayed and
                        peakListView.isDisplayed and
                        (labelling := self._GLPeaks._GLLabels.get(peakListView))):
                    continue

                for drawList in labelling.stringList:
                    try:
                        peak = drawList.stringObject
                        pView = peak.getPeakView(peakListView)
                        _pos = peak.position
                        px, py = float(_pos[dimX]), float(_pos[dimY])
                        tx, ty = pView.textOffset
                        if not tx and not ty:
                            # pixels
                            tx, ty = self._symbolSize, self._symbolSize
                            # ppm
                            # tx, ty = self.symbolX, self.symbolY

                        # find the bounds of the label
                        # pixels
                        # minX, maxX = min(_ll := px + tx * pixX, _rr := px + (tx + drawList.width) * pixX), max(_ll, _rr)
                        # minY, maxY = min(_ll := py + ty * pixY, _rr := py + (ty + drawList.height) * pixY), max(_ll, _rr)
                        # ppm
                        minX, maxX = min(_ll := px + tx * sgnX,
                                         _rr := px + tx * sgnX + drawList.width * pixX), max(_ll, _rr)
                        minY, maxY = min(_ll := py + ty * sgnY,
                                         _rr := py + ty * sgnY + drawList.height * pixY), max(_ll, _rr)

                        if len(peak.axisCodes) > 2 and zPositions is not None:
                            if (minX < xPosition < maxX and minY < yPosition < maxY):
                                # within the XY bounds so check whether inPlane
                                _isInPlane, _isInFlankingPlane, planeIndex, fade = \
                                    self._GLPeaks.objIsInVisiblePlanes(spectrumView, peak)
                                if _isInPlane or _isInFlankingPlane:
                                    peaks.append(peak)

                        elif (minX < xPosition < maxX and minY < yPosition < maxY):
                            peaks.append(peak)

                    except Exception:
                        continue

        # put the selected peaks to the front of the list
        currentPeaks = set(self.current.peaks)
        peaks = [pk for pk in peaks if pk in currentPeaks] + [pk for pk in peaks if pk not in currentPeaks]

        return peaks[:1] if firstOnly else peaks

    def _mouseInMultiplet(self, xPosition, yPosition, firstOnly=False):
        """Find the multiplets under the mouse.
        If firstOnly is true, return only the first item, else an empty list
        """
        xPositions = [xPosition - self.symbolX, xPosition + self.symbolX]
        yPositions = [yPosition - self.symbolY, yPosition + self.symbolY]
        if len(self._orderedAxes) > 2:
            zPositions = self._orderedAxes[2].region
        else:
            zPositions = None

        multiplets = []
        _data2Obj = self.strip.project._data2Obj
        pixX, pixY = self.strip._CcpnGLWidget.pixelX, self.strip._CcpnGLWidget.pixelY
        sgnX, sgnY = np.sign(pixX), np.sign(pixY)

        for spectrumView in self.strip.spectrumViews:
            dimX, dimY = spectrumView.dimensionIndices[:2]

            for multipletListView in spectrumView.multipletListViews:
                if not (spectrumView.isDisplayed and
                        multipletListView.isDisplayed and
                        (labelling := self._GLMultiplets._GLLabels.get(multipletListView))):
                    continue

                for drawList in labelling.stringList:
                    try:
                        multiplet = drawList.stringObject
                        # NOTE:ED - need to speed this up
                        pView = multiplet.getMultipletView(multipletListView)
                        _pos = multiplet.position
                        px, py = float(_pos[dimX]), float(_pos[dimY])
                        tx, ty = pView.textOffset
                        if not tx and not ty:
                            # pixels
                            tx, ty = self._symbolSize, self._symbolSize
                            # ppm
                            # tx, ty = self.symbolX, self.symbolY

                        # find the bounds of the label
                        # pixels
                        # minX, maxX = min(_ll := px + tx * pixX, _rr := px + (tx + drawList.width) * pixX), max(_ll, _rr)
                        # minY, maxY = min(_ll := py + ty * pixY, _rr := py + (ty + drawList.height) * pixY), max(_ll, _rr)
                        # ppm
                        minX, maxX = min(_ll := px + tx * sgnX,
                                         _rr := px + tx * sgnX + drawList.width * pixX), max(_ll, _rr)
                        minY, maxY = min(_ll := py + ty * sgnY,
                                         _rr := py + ty * sgnY + drawList.height * pixY), max(_ll, _rr)

                        if len(multiplet.axisCodes) > 2 and zPositions is not None:
                            if (xPositions[0] < px < xPositions[1]
                                and yPositions[0] < py < yPositions[1]) or \
                                    (minX < xPosition < maxX and minY < yPosition < maxY):
                                # within the XY bounds so check whether inPlane
                                _isInPlane, _isInFlankingPlane, planeIndex, fade = \
                                    self._GLMultiplets.objIsInVisiblePlanes(spectrumView, multiplet)
                                if _isInPlane or _isInFlankingPlane:
                                    multiplets.append(multiplet)
                                    if firstOnly:
                                        return multiplets

                        elif (xPositions[0] < px < xPositions[1]
                              and yPositions[0] < py < yPositions[1]) or \
                                (minX < xPosition < maxX and minY < yPosition < maxY):
                            multiplets.append(multiplet)
                            if firstOnly:
                                return multiplets if multiplet in self.current.multiplets else []

                    except Exception:
                        continue

        return multiplets

    def _mouseInMultipletLabel(self, xPosition, yPosition, firstOnly=False):
        """Find the multiplets under the mouse.
        If firstOnly is true, return only the first item, else an empty list
        """
        # xPositions = [xPosition - self.symbolX, xPosition + self.symbolX]
        # yPositions = [yPosition - self.symbolY, yPosition + self.symbolY]
        if len(self._orderedAxes) > 2:
            zPositions = self._orderedAxes[2].region
        else:
            zPositions = None

        multiplets = []
        _data2Obj = self.strip.project._data2Obj
        pixX, pixY = self.strip._CcpnGLWidget.pixelX, self.strip._CcpnGLWidget.pixelY
        sgnX, sgnY = np.sign(pixX), np.sign(pixY)

        for spectrumView in self.strip.spectrumViews:
            dimX, dimY = spectrumView.dimensionIndices[:2]

            for multipletListView in spectrumView.multipletListViews:
                if not (spectrumView.isDisplayed and
                        multipletListView.isDisplayed and
                        (labelling := self._GLMultiplets._GLLabels.get(multipletListView))):
                    continue

                for drawList in labelling.stringList:

                    try:
                        multiplet = drawList.stringObject
                        pView = multiplet.getMultipletView(multipletListView)
                        _pos = multiplet.position
                        px, py = float(_pos[dimX]), float(_pos[dimY])
                        tx, ty = pView.textOffset
                        if not tx and not ty:
                            # pixels
                            tx, ty = self._symbolSize, self._symbolSize
                            # ppm
                            # tx, ty = self.symbolX, self.symbolY

                        # find the bounds of the label
                        # pixels
                        # minX, maxX = min(_ll := px + tx * pixX, _rr := px + (tx + drawList.width) * pixX), max(_ll, _rr)
                        # minY, maxY = min(_ll := py + ty * pixY, _rr := py + (ty + drawList.height) * pixY), max(_ll, _rr)
                        # ppm
                        minX, maxX = min(_ll := px + tx * sgnX,
                                         _rr := px + tx * sgnX + drawList.width * pixX), max(_ll, _rr)
                        minY, maxY = min(_ll := py + ty * sgnY,
                                         _rr := py + ty * sgnY + drawList.height * pixY), max(_ll, _rr)

                        if len(multiplet.axisCodes) > 2 and zPositions is not None:
                            if (minX < xPosition < maxX and minY < yPosition < maxY):
                                # within the XY bounds so check whether inPlane
                                _isInPlane, _isInFlankingPlane, planeIndex, fade = \
                                    self._GLMultiplets.objIsInVisiblePlanes(spectrumView, multiplet)
                                if _isInPlane or _isInFlankingPlane:
                                    multiplets.append(multiplet)
                                    if firstOnly:
                                        return multiplets

                        elif (minX < xPosition < maxX and minY < yPosition < maxY):
                            multiplets.append(multiplet)
                            if firstOnly:
                                return multiplets if multiplet in self.current.multiplets else []

                    except Exception:
                        continue

        return multiplets

    def _mouseInIntegral(self, xPosition, yPosition, firstOnly=False):
        """Find the integrals under the mouse.
        If firstOnly is true, return only the first item, else an empty list
        Currently not-defined for Nd integrals
        """
        return []

    def _updateVisibleSpectrumViews(self):
        """Update the list of visible spectrumViews when change occurs
        """

        # make the list of ordered spectrumViews
        self._ordering = self.strip.getSpectrumViews()

        # GWV: removed as new data reader returns zeros; blank spectra can be displayed
        # self._ordering = [specView for specView in self._ordering if specView.spectrum.hasValidPath()]

        for specView in tuple(self._spectrumSettings.keys()):
            if specView not in self._ordering:
                getLogger().debug(f'>>>_updateVisibleSpectrumViews GLWidgets  nD   delete {specView} {id(specView)}')
                getLogger().debug(f'>>> _ordering {[id(spec) for spec in self._ordering]}')
                if specView in self._spectrumSettings:
                    del self._spectrumSettings[specView]
                if specView in self._contourList:
                    self._contourList[specView]._delete()
                    del self._contourList[specView]
                if specView in self._visibleOrdering:
                    self._visibleOrdering.remove(specView)
                for k in self._visibleOrderingDict:
                    sp, _dd = k
                    if sp == specView:
                        self._visibleOrderingDict.remove(k)
                        break
                self._GLPeaks._delete()
                self._GLIntegrals._delete()
                self._GLMultiplets._delete()

                # delete the 1d string relating to the spectrumView
                self._spectrumLabelling.removeString(specView)

        # make a list of the visible and not-deleted spectrumViews
        # visibleSpectra = [specView.spectrum for specView in self._ordering if not specView.isDeleted and specView.isDisplayed]
        visibleSpectrumViews = [specView for specView in self._ordering
                                if not specView.isDeleted and specView.isDisplayed]

        self._visibleOrdering = visibleSpectrumViews

        # set the first visible, or the first in the ordered list
        self._firstVisible = (visibleSpectrumViews[0]
                              if visibleSpectrumViews else
                              self._ordering[0] if self._ordering and not self._ordering[0].isDeleted else None)
        self.visiblePlaneList = {}
        self.visiblePlaneListPointValues = {}
        self.visiblePlaneDimIndices = {}

        # generate the new axis labels based on the visible spectrum axisCodes
        self._buildAxisCodesWithWildCards()

        minList = [self._spectrumSettings[sp].ppmPerPoint
                   for sp in self._ordering if sp in self._spectrumSettings]

        minimumValuePerPoint = None

        # check the length of the min values, may have lower dimension spectra overlaid
        for val in minList:
            if minimumValuePerPoint and val is not None:
                minimumValuePerPoint = [min(ii, jj) for ii, jj in zip_longest(minimumValuePerPoint, val, fillvalue=0.0)]
            elif minimumValuePerPoint:
                # val is None so ignore
                pass
            else:
                # set the first value
                minimumValuePerPoint = val

        for visibleSpecView in self._ordering:
            visValues = visibleSpecView._getVisiblePlaneList(
                    firstVisible=self._firstVisible,
                    minimumValuePerPoint=minimumValuePerPoint)

            self.visiblePlaneList[visibleSpecView], \
                self.visiblePlaneListPointValues[visibleSpecView], \
                self.visiblePlaneDimIndices[visibleSpecView] = visValues

        # update the labelling lists
        self._GLPeaks.setListViews(self._ordering)
        self._GLIntegrals.setListViews(self._ordering)
        self._GLMultiplets.setListViews(self._ordering)

    def getPeakPositionFromMouse(self, peak, lastStartCoordinate, cursorPosition=None):
        """Get the centre position of the clicked peak
        """
        indices = getAxisCodeMatchIndices(self._axisCodes, peak.axisCodes)
        for ii, ind in enumerate(indices[:2]):
            if ind is not None:
                lastStartCoordinate[ii] = peak.position[ind]
            else:
                lastStartCoordinate[ii] = cursorPosition[ii]

    def _movePeak(self, peak, deltaPosition):
        """Move the peak to new position
        """
        indices = getAxisCodeMatchIndices(self.axisCodes, peak.axisCodes)

        # get the correct coordinates based on the axisCodes
        p0 = list(peak.position)
        if not p0 or None in p0:
            return

        for ii, ind in enumerate(indices[:2]):
            if ind is not None:
                # update the peak position
                p0[ind] += deltaPosition[ii]

        aliasInds = peak.spectrum.aliasingIndexes
        lims = peak.spectrum.spectrumLimits
        widths = peak.spectrum.spectralWidths

        for dim, pos in enumerate(p0):
            # update the aliasing so that the peak stays within the bounds of the spectrumLimits/aliasingLimits
            minSpectrumFrequency, maxSpectrumFrequency = sorted(lims[dim])
            regionBounds = (minSpectrumFrequency + aliasInds[dim][0] * widths[dim],
                            maxSpectrumFrequency + aliasInds[dim][1] * widths[dim])
            p0[dim] = (pos - regionBounds[0]) % (regionBounds[1] - regionBounds[0]) + regionBounds[0]

        movePeak(peak, p0, updateHeight=True)

    def _tracesNeedUpdating(self, spectrumView=None):
        """Check if traces need updating on _lastTracePoint, use spectrumView to see
        if cursor has moved sufficiently far to warrant an update of the traces
        """

        cursorCoordinate = self.getCurrentCursorCoordinate()
        if spectrumView not in self._lastTracePoint:
            numDim = len(spectrumView.strip.axes)
            self._lastTracePoint[spectrumView] = [-1] * numDim

        lastTrace = self._lastTracePoint[spectrumView]

        ppm2point = spectrumView.spectrum.ppm2point

        # get the correct ordering for horizontal/vertical
        planeDims = self._spectrumSettings[spectrumView].dimensionIndices

        point = [0] * len(cursorCoordinate)
        for n in range(2):
            point[planeDims[n]] = ppm2point(cursorCoordinate[n], dimension=planeDims[n] + 1) - 1

        point = [round(p) for p in point]

        if None in planeDims:
            getLogger().warning(f'bad planeDims {planeDims}')
            return
        if None in point:
            getLogger().warning(f'bad point {point}')
            return

        # numPoints = spectrumView.spectrum.pointCounts
        # xNumPoints, yNumPoints = numPoints[planeDims[0]], numPoints[planeDims[1]]
        # if point[planeDims[0]] >= xNumPoints or point[planeDims[1]] >= yNumPoints:
        #     # Extra check whether the new point is out of range if numLimits
        #     return False

        if self._updateHTrace and not self._updateVTrace and point[planeDims[1]] == lastTrace[planeDims[1]]:
            # Only HTrace, an y-point has not changed
            return False
        elif not self._updateHTrace and self._updateVTrace and point[planeDims[0]] == lastTrace[planeDims[0]]:
            # Only VTrace and x-point has not changed
            return False
        elif self._updateHTrace and self._updateVTrace and point[planeDims[0]] == lastTrace[planeDims[0]] \
                and point[planeDims[1]] == lastTrace[planeDims[1]]:
            # both HTrace and Vtrace, both x-point an y-point have not changed
            return False
        # We need to update; save this point as the last point
        self._lastTracePoint[spectrumView] = point

        return True

    def drawAliasedLabels(self):
        """Draw all the labels that require aliasing to multiple regions
        """
        shader = self._shaderTextAlias.bind()
        # set the scale to the axis limits, needs addressing correctly, possibly same as grid
        self._axisScale = QtGui.QVector4D(self.pixelX, self.pixelY, 1.0, 1.0)
        shader.setProjection(self.axisL, self.axisR, self.axisB, self.axisT, -1.0, 1.0)
        shader.setAxisScale(self._axisScale)
        shader.setStackOffset(QtGui.QVector2D(0.0, 0.0))

        shader.setAliasEnabled(self._aliasEnabled and self._aliasLabelsEnabled)

        # change to correct value for shader
        shader.setAliasShade(self._aliasShade / 100.0)

        for specView in self._ordering:

            if specView.isDeleted:
                continue

            if specView.isDisplayed and specView in self._spectrumSettings.keys():
                # set correct transform when drawing this contour
                specSettings = self._spectrumSettings[specView]
                # specMatrix = np.array(specSettings.matrix, dtype=np.float32)

                # fxMax, fyMax = specSettings.maxSpectrumFrequency
                dxAF, dyAF = specSettings.spectralWidth
                xScale, yScale = specSettings.scale
                alias = specSettings.aliasingIndex
                folding = specSettings.foldingMode

                for idx, (ii, jj) in enumerate(product(range(alias[0][0], alias[0][1] + 1),
                                                       range(alias[1][0], alias[1][1] + 1))):
                    foldX = foldY = 1.0
                    # foldXOffset = foldYOffset = 0
                    if folding[0] == 'mirror':
                        foldX = pow(-1, ii)
                        # foldXOffset = -dxAF if foldX < 0 else 0
                    if folding[1] == 'mirror':
                        foldY = pow(-1, jj)
                        # foldYOffset = -dyAF if foldY < 0 else 0

                    self._axisScale = QtGui.QVector4D(foldX * self.pixelX / xScale, foldY * self.pixelY / yScale,
                                                      1.0, 1.0)
                    shader.setAxisScale(self._axisScale)

                    # specMatrix[:16] = [xScale * foldX, 0.0, 0.0, 0.0,
                    #                    0.0, yScale * foldY, 0.0, 0.0,
                    #                    0.0, 0.0, 1.0, 0.0,
                    #                    fxMax + (ii * dxAF) + foldXOffset, fyMax + (jj * dyAF) + foldYOffset, 0.0, 1.0]

                    # mm = QtGui.QMatrix4x4()
                    # mm.translate(fxMax + (ii * dxAF) + foldXOffset, fyMax + (jj * dyAF) + foldYOffset)
                    # mm.scale(xScale * foldX, yScale * foldY, 1.0)
                    # shader.setMV(mm)

                    shader.setMV(specSettings.mvMatrices[idx])
                    # flipping in the same GL region -  xScale = -xScale
                    #                                   offset = fx0-dxAF
                    # circular -    offset = fx0 + dxAF*alias, alias = min->max
                    # shader.setMVMatrix(specMatrix)
                    shader.setAliasPosition(ii, jj)

                    if self._peakLabelsEnabled:
                        self._GLPeaks.drawLabels(specView)
                    if self._multipletLabelsEnabled:
                        self._GLMultiplets.drawLabels(specView)

    def drawAliasedSymbols(self, peakSymbolsEnabled, peakArrowsEnabled, multipletSymbolsEnabled,
                           multipletArrowsEnabled):
        """Draw all the symbols that require aliasing to multiple regions
        """
        shader = self._shaderPixelAlias.bind()
        # set the scale to the axis limits, needs addressing correctly, possibly same as grid
        shader.setProjection(self.axisL, self.axisR, self.axisB, self.axisT, -1.0, 1.0)

        lineThickness = self._symbolThickness
        GL.glLineWidth(lineThickness * self.viewports.devicePixelRatio)
        shader.setAliasEnabled(self._aliasEnabled)

        # change to correct value for shader
        shader.setAliasShade(self._aliasShade / 100.0)

        for specView in self._ordering:

            if specView.isDeleted:
                continue

            if specView.isDisplayed and specView in self._spectrumSettings.keys():
                specSettings = self._spectrumSettings[specView]
                # specMatrix = np.array(specSettings.matrix, dtype=np.float32)

                # fxMax, fyMax = specSettings.maxSpectrumFrequency
                # dxAF, dyAF = specSettings.spectralWidth
                # xScale, yScale = specSettings.scale
                alias = specSettings.aliasingIndex
                # folding = specSettings.foldingMode

                for idx, (ii, jj) in enumerate(product(range(alias[0][0], alias[0][1] + 1),
                                                       range(alias[1][0], alias[1][1] + 1))):
                    # foldX = foldY = 1.0
                    # foldXOffset = foldYOffset = 0
                    # if folding[0] == 'mirror':
                    #     foldX = pow(-1, ii)
                    #     foldXOffset = -dxAF if foldX < 0 else 0
                    # if folding[1] == 'mirror':
                    #     foldY = pow(-1, jj)
                    #     foldYOffset = -dyAF if foldY < 0 else 0
                    #
                    # # specMatrix[:16] = [xScale * foldX, 0.0, 0.0, 0.0,
                    # #                    0.0, yScale * foldY, 0.0, 0.0,
                    # #                    0.0, 0.0, 1.0, 0.0,
                    # #                    fxMax + (ii * dxAF) + foldXOffset, fyMax + (jj * dyAF) + foldYOffset, 0.0, 1.0]
                    #
                    # mm = QtGui.QMatrix4x4()
                    # mm.translate(fxMax + (ii * dxAF) + foldXOffset, fyMax + (jj * dyAF) + foldYOffset)
                    # mm.scale(xScale * foldX, yScale * foldY, 1.0)
                    # shader.setMV(mm)

                    shader.setMV(specSettings.mvMatrices[idx])
                    # flipping in the same GL region -  xScale = -xScale
                    #                                   offset = fx0-dxAF
                    # circular -    offset = fx0 + dxAF*alias, alias = min->max
                    # _shader.setMVMatrix(specMatrix)
                    shader.setAliasPosition(ii, jj)

                    if peakArrowsEnabled:
                        self._GLPeaks.drawArrows(specView)
                    if multipletArrowsEnabled:
                        self._GLMultiplets.drawArrows(specView)
                    if peakSymbolsEnabled:
                        self._GLPeaks.drawSymbols(specView)
                    if multipletSymbolsEnabled:
                        self._GLMultiplets.drawSymbols(specView)

        GL.glLineWidth(GLDefs.GLDEFAULTLINETHICKNESS * self.viewports.devicePixelRatio)

    def drawIntegralLabels(self):
        """Draw all the integral labels
        """
        pass

    def drawBoundingBoxes(self):
        if self.strip.isDeleted:
            return

        shader = self._shaderPixel

        # set transform to identity - ensures only the pMatrix is applied
        shader.setMVMatrixToIdentity()

        drawList = self.boundingBoxes

        # NOTE:ED - shouldn't need to build this every time :|
        drawList.clearArrays()

        # if self._preferences.showSpectrumBorder:
        if self.strip.spectrumBordersVisible:
            # build the bounding boxes
            index = 0
            for spectrumView in self._ordering:

                if spectrumView.isDeleted:
                    continue

                if spectrumView.isDisplayed and spectrumView.spectrum.dimensionCount > 1 and spectrumView in self._spectrumSettings.keys():
                    specSettings = self._spectrumSettings[spectrumView]

                    fxMin, fyMin = specSettings.minFoldingFrequency
                    dxAF, dyAF = specSettings.spectralWidth
                    alias = specSettings.aliasingIndex

                    try:
                        _posColour = spectrumView.posColours[0]
                        col = *_posColour[:3], 0.5
                    except Exception as es:
                        col = (0.9, 0.1, 0.2, 0.5)

                    for ii in range(alias[0][0], alias[0][1] + 2, 1):
                        # draw the vertical lines
                        x0 = fxMin + (ii * dxAF)
                        y0 = fyMin + (alias[1][0] * dyAF)
                        y1 = fyMin + ((alias[1][1] + 1) * dyAF)
                        drawList.indices = np.append(drawList.indices, np.array((index, index + 1), dtype=np.uint32))
                        drawList.vertices = np.append(drawList.vertices, np.array((x0, y0, x0, y1), dtype=np.float32))
                        drawList.colors = np.append(drawList.colors, np.array(col * 2, dtype=np.float32))
                        drawList.numVertices += 2
                        index += 2

                    for jj in range(alias[1][0], alias[1][1] + 2, 1):
                        # draw the horizontal lines
                        y0 = fyMin + (jj * dyAF)
                        x0 = fxMin + (alias[0][0] * dxAF)
                        x1 = fxMin + ((alias[0][1] + 1) * dxAF)
                        drawList.indices = np.append(drawList.indices, np.array((index, index + 1), dtype=np.uint32))
                        drawList.vertices = np.append(drawList.vertices, np.array((x0, y0, x1, y0), dtype=np.float32))
                        drawList.colors = np.append(drawList.colors, np.array(col * 2, dtype=np.float32))
                        drawList.numVertices += 2
                        index += 2

            # define and draw the boundaries
            drawList.defineIndexVBO()

            for _ in self._disableGLAliasing():
                GL.glEnable(GL.GL_BLEND)

                # use the viewports.devicePixelRatio for retina displays
                GL.glLineWidth(self._contourThickness * self.viewports.devicePixelRatio)

                drawList.drawIndexVBO()

                # reset lineWidth
                GL.glLineWidth(GLDefs.GLDEFAULTLINETHICKNESS * self.viewports.devicePixelRatio)

    def drawSpectra(self):
        if self.strip.isDeleted:
            return

        shader = self._shaderPixel

        GL.glLineWidth(self._contourThickness * self.viewports.devicePixelRatio)
        GL.glDisable(GL.GL_BLEND)

        for spectrumView in self._ordering:

            if spectrumView.isDeleted or not spectrumView._showContours:
                continue
            if spectrumView.spectrum is None or (spectrumView.spectrum and spectrumView.spectrum.isDeleted):
                continue

            if spectrumView.isDisplayed and spectrumView in self._spectrumSettings.keys():

                # set correct transform when drawing this contour
                if spectrumView.spectrum.displayFoldedContours:
                    specSettings = self._spectrumSettings[spectrumView]
                    contours = self._contourList[spectrumView]

                    pIndex = specSettings.dimensionIndices
                    if None in pIndex:
                        continue

                    for mv in specSettings.mvMatrices:
                        shader.setMV(mv)
                        contours.drawIndexVBO()

                    # # fxMax, fyMax = specSettings.maxSpectrumFrequency
                    # fxMin, fyMin = specSettings.minSpectrumFrequency
                    # xReverse, yReverse = specSettings.axisReversed
                    # dxAF, dyAF = specSettings.spectralWidth
                    # xScale, yScale = specSettings.scale
                    # alias = specSettings.aliasingIndex
                    # folding = specSettings.foldingMode
                    # # specMatrix = np.array(specSettings.matrix, dtype=np.float32)
                    #
                    # print(f'==> {specSettings.scale}   {xReverse} {yReverse}')
                    # foldX = 1.0 if xReverse else -1.0
                    # foldY = 1.0 if yReverse else -1.0
                    # foldXOffset = dxAF if xReverse else 0
                    # foldYOffset = dyAF if yReverse else 0
                    # for ii, jj in product(range(alias[0][0], alias[0][1] + 1), range(alias[1][0], alias[1][1] + 1)):
                    #     # if folding[0] == 'mirror':
                    #     #     # to be implemented correctly later
                    #     #     foldX = pow(-1, ii)
                    #     #     foldXOffset = -dxAF if foldX < 0 else 0
                    #     # if folding[1] == 'mirror':
                    #     #     foldY = pow(-1, jj)
                    #     #     foldYOffset = -dyAF if foldY < 0 else 0
                    #
                    #     # specMatrix[:16] = [xScale * foldX, 0.0, 0.0, 0.0,
                    #     #                    0.0, yScale * foldY, 0.0, 0.0,
                    #     #                    0.0, 0.0, 1.0, 0.0,
                    #     #                    fxMax + (ii * dxAF) + foldXOffset, fyMax + (jj * dyAF) + foldYOffset, 0.0, 1.0]
                    #
                    #     mm = QtGui.QMatrix4x4()
                    #     mm.translate(fxMin + (ii * dxAF) + foldXOffset, fyMin + (jj * dyAF) + foldYOffset)
                    #     mm.scale(xScale * foldX, yScale * foldY, 1.0)
                    #     shader.setMV(mm)
                    #
                    #     # flipping in the same GL region -  xScale = -xScale
                    #     #                                   offset = fxMax-dxAF
                    #     # circular -    offset = fxMax + dxAF*alias, alias = min->max
                    #     # shader.setMVMatrix(specMatrix)
                    #
                    #     self._contourList[spectrumView].drawIndexVBO()
                else:
                    # set the scaling/offset for a single spectrum GL contour
                    # shader.setMVMatrix(self._spectrumSettings[spectrumView].matrix)
                    shader.setMV(self._spectrumSettings[spectrumView].matrix)
                    self._contourList[spectrumView].drawIndexVBO()

        # reset lineWidth
        GL.glLineWidth(GLDefs.GLDEFAULTLINETHICKNESS * self.viewports.devicePixelRatio)

    @staticmethod
    def _drawDiagonalLineV2(x0, x1, y0, y1):
        """Generate a simple diagonal mapped to (0..1/0..1)
        """
        yy0 = float(x0 - y0) / (y1 - y0)
        yy1 = float(x1 - y0) / (y1 - y0)

        return (0, yy0, 1, yy1)

    def _addDiagonalLine(self, drawList, x0, x1, y0, y1, col):
        """Add a diagonal line to the drawList
        """
        index = len(drawList.indices)
        drawList.indices = np.append(drawList.indices, np.array((index, index + 1), dtype=np.uint32))
        drawList.vertices = np.append(drawList.vertices,
                                      np.array(self._drawDiagonalLineV2(x0, x1, y0, y1), dtype=np.float32))
        drawList.colors = np.append(drawList.colors, np.array(col * 2, dtype=np.float32))
        drawList.numVertices += 2

    def _buildDiagonalList(self):
        """Build a list containing the diagonal and the spinningRate lines for the sidebands
        """
        # get spectral width in X and Y
        # get max number of diagonal lines to draw in each axis
        # map to the valueToRatio screen
        # zoom should take care in bounding to the viewport

        # draw the diagonals for the visible spectra
        if self.strip.isDeleted:
            return

        # build the bounding boxes
        drawList = self.diagonalGLList
        drawList.clearArrays()
        drawListSideBands = self.diagonalSideBandsGLList
        drawListSideBands.clearArrays()

        x0 = self.axisL
        x1 = self.axisR
        y0 = self.axisB
        y1 = self.axisT
        col = (0.5, 0.5, 0.5, 0.5)

        diagonalCount = 0
        for spectrumView in self._ordering:  #self._ordering:                             # strip.spectrumViews:

            if spectrumView.isDeleted:
                continue

            if spectrumView.isDisplayed and spectrumView in self._spectrumSettings.keys():
                specSettings = self._spectrumSettings[spectrumView]
                pIndex = specSettings.dimensionIndices

                xco = yco = 1.0
                if not diagonalCount:
                    # add lines to drawList
                    if self._matchingIsotopeCodes:
                        # mTypes = spectrumView.spectrum.measurementTypes
                        mTypes = [CoherenceOrder[co] for co in spectrumView.spectrum.coherenceOrders]
                        xaxisType = mTypes[pIndex[0]]
                        yaxisType = mTypes[pIndex[1]]

                        # # extra multiple-quantum diagonals
                        # if xaxisType == 'MQShift' and yaxisType == 'Shift':
                        #     self._addDiagonalLine(drawList, x0, x1, 2 * y0, 2 * y1, col)
                        # elif xaxisType == 'Shift' and yaxisType == 'MQShift':
                        #     self._addDiagonalLine(drawList, 2 * x0, 2 * x1, y0, y1, col)

                        # extra multiple-quantum diagonals
                        if 0 < yaxisType.value < xaxisType.value:
                            yco = xaxisType.value / yaxisType.value
                            self._addDiagonalLine(drawList, x0, x1, yco * y0, yco * y1, col)
                        elif 0 < xaxisType.value < yaxisType.value:
                            xco = yaxisType.value / xaxisType.value
                            self._addDiagonalLine(drawList, xco * x0, xco * x1, y0, y1, col)

                        else:
                            # add the standard diagonal
                            self._addDiagonalLine(drawList, x0, x1, y0, y1, col)
                    diagonalCount += 1

                if spinningRate := spectrumView.spectrum.spinningRate:
                    sFreqs = spectrumView.spectrum.spectrometerFrequencies
                    spinningRate /= sFreqs[pIndex[0]]  # might need to pick the correct axis here

                    nmin = -int(self._preferences.numSideBands)
                    nmax = int(self._preferences.numSideBands)

                    for n in range(nmin, nmax + 1):
                        if n:
                            # add lines to drawList
                            if xco > yco:
                                self._addDiagonalLine(drawListSideBands, (xco * x0) + n * spinningRate,
                                                      (xco * x1) + n * spinningRate, yco * y0, yco * y1, col)
                            else:
                                self._addDiagonalLine(drawListSideBands, xco * x0, xco * x1,
                                                      (yco * y0) + n * spinningRate, (yco * y1) + n * spinningRate, col)

        drawList.defineIndexVBO()
        drawListSideBands.defineIndexVBO()

    def buildDiagonals(self):
        # determine whether the isotopeCodes of the first two visible axes are matching
        self._matchingIsotopeCodes = False

        for specView in self._ordering:

            # check whether the spectrumView is still active
            if specView.isDeleted:
                continue

            # inside the paint event, so sometimes specView may not exist
            if specView in self._spectrumSettings:
                pIndex = self._spectrumSettings[specView].dimensionIndices

                if pIndex and None not in pIndex:
                    spec = specView.spectrum

                    if spec.isotopeCodes[pIndex[0]] == spec.isotopeCodes[pIndex[1]]:
                        self._matchingIsotopeCodes = True

                    # build the diagonal list here from the visible spectra - each may have a different spinning rate
                    # remove from _build axe - not needed there
                    self._buildDiagonalList()
                    break

    def _buildSpectrumSetting(self, spectrumView, stackCount=0):
        # if spectrumView.spectrum.headerSize == 0:
        #     return

        # delta = [-1.0 if self.XDIRECTION else 1.0,
        #          -1.0 if self.YDIRECTION else 1.0]
        delta = [self.XDIRECTION, self.YDIRECTION]
        self._spectrumSettings[spectrumView] = specVals = spectrumView._getVisibleSpectrumViewParams(delta=delta)

        self._minXRange = min(self._minXRange,
                              GLDefs.RANGEMINSCALE * specVals.spectralWidth[0] / specVals.pointCount[0])
        self._maxXRange = max(self._maxXRange, specVals.spectralWidth[0])
        self._minYRange = min(self._minYRange,
                              GLDefs.RANGEMINSCALE * specVals.spectralWidth[1] / specVals.pointCount[1])
        self._maxYRange = max(self._maxYRange, specVals.spectralWidth[1])

        self._rangeXDefined = True
        self._rangeYDefined = True
        self._maxX = max(self._maxX, specVals.maxSpectrumFrequency[0])
        self._minX = min(self._minX, specVals.minSpectrumFrequency[0])
        self._maxY = max(self._maxY, specVals.maxSpectrumFrequency[1])
        self._minY = min(self._minY, specVals.minSpectrumFrequency[1])

        self._buildAxisCodesWithWildCards()

    def buildCursors(self):
        """Build and draw the cursors/doubleCursors
        """
        if self._disableCursorUpdate or not self._crosshairVisible:
            return

        # get the next cursor drawList
        self._advanceGLCursor()
        drawList = self._glCursorQueue[self._glCursorHead]
        vertices = []
        indices = []
        index = 0

        # map the cursor to the ratio coordinates - double cursor is flipped about the line x=y, or depends on SQ-DQ-TQ status
        cursorCoordinate = self.getCurrentCursorCoordinate()
        newCoords = self._scaleAxisToRatio(cursorCoordinate[:2])
        # doubleCoords = self._scaleAxisToRatio(self.getCurrentDoubleCursorCoordinates()[0:2])

        if getCurrentMouseMode() == PICK and self.underMouse():

            x = self.deltaX * 8
            y = self.deltaY * 8

            vertices = [newCoords[0] - x, newCoords[1] - y,
                        newCoords[0] + x, newCoords[1] - y,
                        newCoords[0] + x, newCoords[1] - y,
                        newCoords[0] + x, newCoords[1] + y,
                        newCoords[0] + x, newCoords[1] + y,
                        newCoords[0] - x, newCoords[1] + y,
                        newCoords[0] - x, newCoords[1] + y,
                        newCoords[0] - x, newCoords[1] - y
                        ]
            indices = [0, 1, 2, 3, 4, 5, 6, 7]
            col = self.mousePickColour
            index = 8

        else:
            col = self.foreground

        # dx = dy = 1.0
        # if self._firstVisible:
        #     idx = self._firstVisible.dimensionIndices
        #     spec = self._firstVisible.spectrum
        #
        #     mTypes = [CoherenceOrder[co] for co in spec.coherenceOrders]
        #     xaxisType = mTypes[idx[0]]
        #     yaxisType = mTypes[idx[1]]
        #     dx = max(dx, xaxisType.value)
        #     dy = max(dy, yaxisType.value)

        if not self.spectrumDisplay.phasingFrame.isVisible() and (coords := self.current.mouseMovedDict):
            # NOTE:ED - new bit
            xaxisType = yaxisType = 1
            if self._firstVisible and not self._firstVisible.isDeleted:
                idx = self._firstVisible.dimensionIndices
                spec = self._firstVisible.spectrum

                mTypes = [CoherenceOrder[co] for co in spec.coherenceOrders]
                xaxisType = mTypes[idx[0]]
                yaxisType = mTypes[idx[1]]

            # read values from isotopeCode or axisCode
            if self.underMouse() and self._matchingIsotopeCodes and \
                    ((0 < xaxisType.value < yaxisType.value < 3) or (0 < yaxisType.value < xaxisType.value < 3)):
                xPosList = [cursorCoordinate[0]]
                yPosList = [cursorCoordinate[1]]

            elif self._preferences.matchAxisCode == 0:  # default - match atom type
                atomTypes = self.spectrumDisplay.isotopeCodes
                xPosList = list(coords[AXIS_MATCHATOMTYPE].get(atomTypes[0], []))
                yPosList = list(coords[AXIS_MATCHATOMTYPE].get(atomTypes[1], []))

            else:
                atCodes = self._orderedAxes
                xPosList = list(coords[AXIS_FULLATOMNAME].get(atCodes[0].code, []))
                yPosList = list(coords[AXIS_FULLATOMNAME].get(atCodes[1].code, []))

            foundX = []
            foundY = []
            # if dx > 1:
            #     dx /= len(xPosList)
            #     xPosList = [sum(xPosList)]
            # if dy > 1:
            #     dy /= len(yPosList)
            #     yPosList = [sum(yPosList)]

            if not self._updateVTrace and newCoords[0] is not None:
                for pos in xPosList:
                    x, _y = self._scaleAxisToRatio([pos, 0])
                    if all(abs(x - val) > self.deltaX for val in foundX):
                        # store the found value so that overlaying lines are not drawn - OpenGL uses an XOR draw mode
                        foundX.append(x)
                        vertices.extend([x, 1.0, x, 0.0])
                        indices.extend([index, index + 1])
                        index += 2

                    # if self._matchingIsotopeCodes:
                    #     # draw the cursor reflected about the x=y line (need to check gammaRatio)
                    #     _x, y = self._scaleAxisToRatio([0, pos])
                    #     if all(abs(y - val) > self.deltaY for val in foundY):
                    #         foundY.append(y)
                    #         vertices.extend([0.0, y, 1.0, y])
                    #         indices.extend([index, index + 1])
                    #         index += 2

            if not self._updateHTrace and newCoords[1] is not None:
                for pos in yPosList:
                    _x, y = self._scaleAxisToRatio([0, pos])
                    if all(abs(y - val) > self.deltaY for val in foundY):
                        foundY.append(y)
                        vertices.extend([0.0, y, 1.0, y])
                        indices.extend([index, index + 1])
                        index += 2

                    # if self._matchingIsotopeCodes:
                    #     # draw the cursor reflected about the x=y line (need to check gammaRatio)
                    #     x, _y = self._scaleAxisToRatio([pos, 0])
                    #     if all(abs(x - val) > self.deltaX for val in foundX):
                    #         foundX.append(x)
                    #         vertices.extend([x, 1.0, x, 0.0])
                    #         indices.extend([index, index + 1])
                    #         index += 2

                    # mTypes = [CoherenceOrder[co] for co in spectrumView.spectrum.coherenceOrders]
                    # xaxisType = mTypes[pIndex[0]]
                    # yaxisType = mTypes[pIndex[1]]

            # if self._firstVisible and self._matchingIsotopeCodes and len(yPosList) == 2:
            #     idx = self._firstVisible.dimensionIndices
            #     spec = self._firstVisible.spectrum
            #
            #     mTypes = [CoherenceOrder[co] for co in spec.coherenceOrders]
            #     xaxisType = mTypes[idx[0]]
            #     yaxisType = mTypes[idx[1]]
            #
            #     # extra multiple-quantum axes
            #     if 0 < yaxisType.value < xaxisType.value:
            #         x, _y = self._scaleAxisToRatio([sum(yPosList), 0])
            #         if all(abs(x - val) > self.deltaX for val in foundX):
            #             foundX.append(x)
            #             vertices.extend([x, 1.0, x, 0.0])
            #             indices.extend([index, index + 1])
            #             index += 2
            #
            #     elif 0 < xaxisType.value < yaxisType.value:
            #         _x, y = self._scaleAxisToRatio([0, sum(xPosList)])
            #         if all(abs(y - val) > self.deltaY for val in foundY):
            #             foundY.append(y)
            #             vertices.extend([0.0, y, 1.0, y])
            #             indices.extend([index, index + 1])
            #             index += 2

            # NOTE:ED - new bit
            self.mouseCoordDQ = None
            if self._firstVisible and self._matchingIsotopeCodes:
                # idx = self._firstVisible.dimensionIndices
                # spec = self._firstVisible.spectrum
                #
                # mTypes = [CoherenceOrder[co] for co in spec.coherenceOrders]
                # xaxisType = mTypes[idx[0]]
                # yaxisType = mTypes[idx[1]]

                # extra zero/double-quantum axes
                if (0 < xaxisType.value < yaxisType.value < 3):                # single double quantum (double y coord)
                    if len(xPosList) == 1 and len(yPosList) == 1:              # should always be true? (sanity check)
                        xPosList.append(yPosList[0])                           # y position to list
                    if len(xPosList) == 2:                                     # should always be true? (sanity check)
                        # y is the double-quantum axis
                        xx = xPosList[1] - xPosList[0]                         # y-x (y added prev)
                        self.mouseCoordDQ = (xx, yPosList[0], 0)               # create dqCoord flags
                        x, _y = self._scaleAxisToRatio([xx, 0])                # openGL scaling
                        if all(abs(x - val) > self.deltaX for val in foundX):  # checks not overlapping
                            foundX.append(x)                                   # previous cursor flag
                            vertices.extend([x, 1.0, x, 0.0])                  # add the line to the array
                            indices.extend([index, index + 1])                 # indices array update
                            index += 2                                         # vertArray index

                elif (0 < yaxisType.value < xaxisType.value < 3):
                    if len(xPosList) == 1 and len(yPosList) == 1:
                        yPosList.insert(0, xPosList[0])
                    if len(yPosList) == 2:
                        # x is the double-quantum axis
                        yy = yPosList[0] - yPosList[1]
                        self.mouseCoordDQ = (xPosList[0], yy, 1)
                        print(self.mouseCoordDQ)
                        _x, y = self._scaleAxisToRatio([0, yy])
                        if all(abs(y - val) > self.deltaY for val in foundY):
                            foundY.append(y)
                            vertices.extend([0.0, y, 1.0, y])
                            indices.extend([index, index + 1])
                            index += 2

        drawList.vertices = np.array(vertices, dtype=np.float32)
        drawList.indices = np.array(indices, dtype=np.int32)
        drawList.numVertices = len(vertices) // 2
        drawList.colors = np.array(col * drawList.numVertices, dtype=np.float32)

        # build and draw the VBO
        drawList.defineIndexVBO()

    def _updateMouseDict(self, cursorCoordinate):
        try:
            mouseMovedDict = self.current.mouseMovedDict
        except Exception:
            # initialise a new mouse moved dict
            mouseMovedDict = {MOUSEDICTSTRIP    : self.strip,
                              AXIS_MATCHATOMTYPE: {},
                              AXIS_FULLATOMNAME : {},
                              }

        xPos = yPos = 0
        atTypes = mouseMovedDict[AXIS_MATCHATOMTYPE] = {}
        atCodes = mouseMovedDict[AXIS_FULLATOMNAME] = {}

        # transfer the mouse position from the coords to the mouseMovedDict for the other displays
        for n, (atomType, axis) in enumerate(zip(self.spectrumDisplay.isotopeCodes, self._orderedAxes)):
            ats = atTypes.setdefault(atomType, [])
            atcs = atCodes.setdefault(axis.code, [])
            if n == 0:
                xPos = pos = cursorCoordinate[0]
            elif n == 1:
                yPos = pos = cursorCoordinate[1]
            else:
                # for other Nd dimensions
                pos = axis.position

            ats.append(pos)
            atcs.append(pos)

        # if self._matchingIsotopeCodes:
        #     # add a copy to show the reflected ppm values
        #     for n, (atomType, axis) in enumerate(zip(self.spectrumDisplay.isotopeCodes, self._orderedAxes)):
        #         ats = atTypes.setdefault(atomType, [])
        #         atcs = atCodes.setdefault(axis.code, [])
        #         if n == 0:
        #             xPos = pos = cursorCoordinate[1]
        #         elif n == 1:
        #             yPos = pos = cursorCoordinate[0]
        #         else:
        #             # can ignore the rest
        #             break
        #
        #         ats.append(pos)
        #         atcs.append(pos)

        # if self._firstVisible and self._matchingIsotopeCodes:
        #     idx = self._firstVisible.dimensionIndices
        #     spec = self._firstVisible.spectrum
        #
        #     mTypes = [CoherenceOrder[co] for co in spec.coherenceOrders]
        #     xaxisType = mTypes[idx[0]]
        #     yaxisType = mTypes[idx[1]]
        #
        #     # add a copy to show the reflected ppm values
        #     for n, (atomType, axis) in enumerate(zip(self.spectrumDisplay.isotopeCodes, self._orderedAxes)):
        #         ats = atTypes.setdefault(atomType, [])
        #         atcs = atCodes.setdefault(axis.code, [])
        #         if n == 0 and 0 < xaxisType.value < xaxisType.value:
        #             # x-axis and y-axis is DQ or more
        #             ats.append(xPos-yPos)
        #             atcs.append(xPos-yPos)
        #         elif n == 1 and 0 < xaxisType.value < yaxisType.value:
        #             # y-axis and x-axis is DQ or more
        #             ats.append(yPos-xPos)
        #             atcs.append(yPos-xPos)

        self.current.cursorPosition = (xPos, yPos)
        self.current.mouseMovedDict = mouseMovedDict

        return mouseMovedDict

    # def initialiseTraces(self):
    #     # set up the arrays and dimension for showing the horizontal/vertical traces
    #     for spectrumView in self._ordering:  # strip.spectrumViews:
    #
    #         if spectrumView.isDeleted:
    #             continue
    #
    #         self._spectrumSettings[spectrumView] = {}
    #         visSpec = spectrumView.getVisibleState(dimensionCount=2)
    #
    #         # get the bounding box of the spectra
    #         dx = self.sign(self.axisR - self.axisL)
    #         fxMax, fxMin = visSpec[0].maxSpectrumFrequency, visSpec[0].minSpectrumFrequency
    #
    #         # check tolerances
    #         if not self._widthsChangedEnough((fxMax, 0.0), (fxMin, 0.0), tol=1e-10):
    #             fxMax, fxMin = 1.0, -1.0
    #
    #         dxAF = fxMax - fxMin
    #         xScale = dx * dxAF / visSpec[0].pointCount
    #
    #         dy = self.sign(self.axisT - self.axisB)
    #         fyMax, fyMin = visSpec[1].maxSpectrumFrequency, visSpec[1].minSpectrumFrequency
    #
    #         # check tolerances
    #         if not self._widthsChangedEnough((fyMax, 0.0), (fyMin, 0.0), tol=1e-10):
    #             fyMax, fyMin = 1.0, -1.0
    #
    #         dyAF = fyMax - fyMin
    #         yScale = dy * dyAF / visSpec[1].pointCount
    #
    #         # create model-view matrix for the spectrum to be drawn
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_MATRIX] = np.zeros((16,), dtype=np.float32)
    #
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_MATRIX][:16] = [xScale, 0.0, 0.0, 0.0,
    #                                                                              0.0, yScale, 0.0, 0.0,
    #                                                                              0.0, 0.0, 1.0, 0.0,
    #                                                                              fxMax, fyMax, 0.0, 1.0]
    #         # setup information for the horizontal/vertical traces
    #         # self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_XLIMITS] = (fxMin, fxMax)
    #         # self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_YLIMITS] = (fyMin, fyMax)
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_LIMITS] = (fxMin, fxMax), (fyMin, fyMax)
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_AF] = (dxAF, dyAF)
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_SCALE] = (xScale, yScale)
    #
    #         indices = getAxisCodeMatchIndices(self.strip.axisCodes, spectrumView.spectrum.axisCodes)
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_POINTINDEX] = indices


class Gui1dWidget(CcpnGLWidget):
    AXIS_MARGINRIGHT = 80
    YAXISUSEEFORMAT = True
    XDIRECTION = -1.0
    YDIRECTION = 1.0
    AXISLOCKEDBUTTON = True
    AXISLOCKEDBUTTONALLSTRIPS = True
    is1D = True
    SPECTRUMPOSCOLOUR = 'sliceColour'
    SPECTRUMNEGCOLOUR = 'sliceColour'
    SPECTRUMXZOOM = 1.0e2
    SPECTRUMYZOOM = 1.0e6
    SHOWSPECTRUMONPHASING = False

    def __init__(self, strip=None, mainWindow=None, stripIDLabel=None):

        if strip.spectrumDisplay._flipped:
            self.YDIRECTION = -1.0
            self.XAXES = YAXISUNITS1D
        else:
            self.YAXES = YAXISUNITS1D

        super(Gui1dWidget, self).__init__(strip=strip,
                                          mainWindow=mainWindow,
                                          stripIDLabel=stripIDLabel)

    def _mouseInPeak(self, xPosition, yPosition, firstOnly=False):
        """Find the peaks under the mouse.
        If firstOnly is true, return only the first item, else an empty list
        """
        xPositions = [xPosition - self.symbolX, xPosition + self.symbolX]
        yPositions = [yPosition - self.symbolY, yPosition + self.symbolY]
        originalxPositions = xPositions
        originalyPositions = yPositions

        peaks = []
        _data2Obj = self.strip.project._data2Obj
        pixX, pixY = self.strip._CcpnGLWidget.pixelX, self.strip._CcpnGLWidget.pixelY
        sgnX, sgnY = np.sign(pixX), np.sign(pixY)

        for spectrumView in self.strip.spectrumViews:
            dims = self._spectrumSettings[spectrumView].dimensionIndices
            xOffset, yOffset = self._spectrumSettings[spectrumView].stackedMatrixOffset
            xPositions = np.array(originalxPositions) - xOffset
            yPositions = np.array(originalyPositions) - yOffset

            for peakListView in spectrumView.peakListViews:
                if not (spectrumView.isDisplayed and
                        peakListView.isDisplayed and
                        (labelling := self._GLPeaks._GLLabels.get(peakListView))):
                    continue

                for drawList in labelling.stringList:
                    try:
                        peak = drawList.stringObject
                        pView = peak.getPeakView(peakListView)
                        _pos = [float(peak.position[0]), float(peak.height)]
                        px, py = [_pos[ind] for ind in dims]
                        tx, ty = pView.textOffset  # always relative to the screen, doesn't need rotating
                        if not tx and not ty:
                            # pixels
                            tx, ty = self._symbolSize, self._symbolSize
                            # ppm
                            # tx, ty = self.symbolX, self.symbolY

                        # find the bounds of the label
                        # pixels
                        # minX, maxX = min(_ll := px + tx * pixX, _rr := px + (tx + drawList.width) * pixX), max(_ll, _rr)
                        # minY, maxY = min(_ll := py + ty * pixY, _rr := py + (ty + drawList.height) * pixY), max(_ll, _rr)
                        # ppm
                        minX, maxX = min(_ll := px + tx * sgnX,
                                         _rr := px + tx * sgnX + drawList.width * pixX), max(_ll, _rr)
                        minY, maxY = min(_ll := py + ty * sgnY,
                                         _rr := py + ty * sgnY + drawList.height * pixY), max(_ll, _rr)

                        if (xPositions[0] < px < xPositions[1]
                            and yPositions[0] < py < yPositions[1]) or \
                                (minX < xPosition - xOffset < maxX and minY < yPosition - yOffset < maxY):
                            peaks.append(peak)
                            # if firstOnly:
                            #     return peaks if peak in self.current.peaks else []

                    except Exception:
                        continue

        return peaks

    def _mouseInPeakLabel(self, xPosition, yPosition, firstOnly=False):
        """Find the peaks under the mouse.
        If firstOnly is true, return only the first item, else an empty list
        """
        peaks = []
        _data2Obj = self.strip.project._data2Obj
        pixX, pixY = self.strip._CcpnGLWidget.pixelX, self.strip._CcpnGLWidget.pixelY
        sgnX, sgnY = np.sign(pixX), np.sign(pixY)

        for spectrumView in self.strip.spectrumViews:
            dims = self._spectrumSettings[spectrumView].dimensionIndices

            for peakListView in spectrumView.peakListViews:
                xOffset, yOffset = self._spectrumSettings[spectrumView].stackedMatrixOffset
                if not (spectrumView.isDisplayed and
                        peakListView.isDisplayed and
                        (labelling := self._GLPeaks._GLLabels.get(peakListView))):
                    continue

                for drawList in labelling.stringList:
                    try:
                        peak = drawList.stringObject
                        pView = peak.getPeakView(peakListView)
                        _pos = [float(peak.position[0]), float(peak.height)]
                        px, py = [_pos[ind] for ind in dims]
                        tx, ty = pView.textOffset
                        if not tx and not ty:
                            # pixels
                            tx, ty = self._symbolSize, self._symbolSize
                            # ppm
                            # tx, ty = self.symbolX, self.symbolY

                        # find the bounds of the label
                        # pixels
                        # minX, maxX = min(_ll := px + tx * pixX, _rr := px + (tx + drawList.width) * pixX), max(_ll, _rr)
                        # minY, maxY = min(_ll := py + ty * pixY, _rr := py + (ty + drawList.height) * pixY), max(_ll, _rr)
                        # ppm
                        minX, maxX = min(_ll := px + tx * sgnX,
                                         _rr := px + tx * sgnX + drawList.width * pixX), max(_ll, _rr)
                        minY, maxY = min(_ll := py + ty * sgnY,
                                         _rr := py + ty * sgnY + drawList.height * pixY), max(_ll, _rr)

                        if (minX < xPosition - xOffset < maxX and minY < yPosition - yOffset < maxY):
                            peaks.append(peak)
                            if firstOnly:
                                return peaks if peak in self.current.peaks else []

                    except Exception:
                        continue

        return peaks

    def _mouseInIntegral(self, xPosition, yPosition, firstOnly=False):
        """Find the integrals under the mouse.
        If firstOnly is true, return only the first item, else an empty list
        """
        integrals = []

        if not self._stackingMode and not (self.is1D and self.strip._isPhasingOn):
            for reg in self._GLIntegrals._GLSymbols.values():
                if not reg.integralListView.isDisplayed or not reg.spectrumView.isDisplayed:
                    continue

                if integralPressed := self.mousePressIn1DArea(reg._regions):
                    for ilp in integralPressed:
                        obj = ilp[0]._object
                        integrals.append(obj)
                        if firstOnly:
                            return integrals if obj in self.current.integrals else []

        return integrals

    def _mouseInMultiplet(self, xPosition, yPosition, firstOnly=False):
        """Find the multiplets under the mouse.
        If firstOnly is true, return only the first item, else an empty list
        """
        xPositions = [xPosition - self.symbolX, xPosition + self.symbolX]
        yPositions = [yPosition - self.symbolY, yPosition + self.symbolY]
        originalxPositions = xPositions
        originalyPositions = yPositions

        multiplets = []
        _data2Obj = self.strip.project._data2Obj
        pixX, pixY = self.strip._CcpnGLWidget.pixelX, self.strip._CcpnGLWidget.pixelY
        sgnX, sgnY = np.sign(pixX), np.sign(pixY)

        for spectrumView in self.strip.spectrumViews:
            dims = self._spectrumSettings[spectrumView].dimensionIndices
            xOffset, yOffset = self._spectrumSettings[spectrumView].stackedMatrixOffset
            xPositions = np.array(originalxPositions) - xOffset
            yPositions = np.array(originalyPositions) - yOffset

            for multipletListView in spectrumView.multipletListViews:
                if not (spectrumView.isDisplayed and
                        multipletListView.isDisplayed and
                        (labelling := self._GLMultiplets._GLLabels.get(multipletListView))):
                    continue

                for drawList in labelling.stringList:
                    try:
                        multiplet = drawList.stringObject
                        pView = multiplet.getMultipletView(multipletListView)
                        _pos = [float(multiplet.position[0]), float(multiplet.height)]
                        px, py = [_pos[ind] for ind in dims]
                        tx, ty = pView.textOffset
                        if not tx and not ty:
                            # pixels
                            tx, ty = self._symbolSize, self._symbolSize
                            # ppm
                            # tx, ty = self.symbolX, self.symbolY

                        # find the bounds of the label
                        # pixels
                        # minX, maxX = min(_ll := px + tx * pixX, _rr := px + (tx + drawList.width) * pixX), max(_ll, _rr)
                        # minY, maxY = min(_ll := py + ty * pixY, _rr := py + (ty + drawList.height) * pixY), max(_ll, _rr)
                        # ppm
                        minX, maxX = min(_ll := px + tx * sgnX,
                                         _rr := px + tx * sgnX + drawList.width * pixX), max(_ll, _rr)
                        minY, maxY = min(_ll := py + ty * sgnY,
                                         _rr := py + ty * sgnY + drawList.height * pixY), max(_ll, _rr)

                        if (xPositions[0] < px < xPositions[1]
                            and yPositions[0] < py < yPositions[1]) or \
                                (minX < xPosition - xOffset < maxX and minY < yPosition - yOffset < maxY):

                            multiplets.append(multiplet)
                            if firstOnly:
                                return multiplets if multiplet in self.current.multiplets else []

                    except Exception:
                        continue

        return multiplets

    def _mouseInMultipletLabel(self, xPosition, yPosition, firstOnly=False):
        """Find the multiplets under the mouse.
        If firstOnly is true, return only the first item, else an empty list
        """
        multiplets = []
        _data2Obj = self.strip.project._data2Obj
        pixX, pixY = self.strip._CcpnGLWidget.pixelX, self.strip._CcpnGLWidget.pixelY
        sgnX, sgnY = np.sign(pixX), np.sign(pixY)

        for spectrumView in self.strip.spectrumViews:
            dims = self._spectrumSettings[spectrumView].dimensionIndices
            xOffset, yOffset = self._spectrumSettings[spectrumView].stackedMatrixOffset

            for multipletListView in spectrumView.multipletListViews:
                if not (spectrumView.isDisplayed and
                        multipletListView.isDisplayed and
                        (labelling := self._GLMultiplets._GLLabels.get(multipletListView))):
                    continue

                for drawList in labelling.stringList:
                    try:
                        multiplet = drawList.stringObject
                        pView = multiplet.getMultipletView(multipletListView)
                        _pos = [float(multiplet.position[0]), float(multiplet.height)]
                        px, py = [_pos[ind] for ind in dims]
                        tx, ty = pView.textOffset
                        if not tx and not ty:
                            # pixels
                            tx, ty = self._symbolSize, self._symbolSize
                            # ppm
                            # tx, ty = self.symbolX, self.symbolY

                        # find the bounds of the label
                        # pixels
                        # minX, maxX = min(_ll := px + tx * pixX, _rr := px + (tx + drawList.width) * pixX), max(_ll, _rr)
                        # minY, maxY = min(_ll := py + ty * pixY, _rr := py + (ty + drawList.height) * pixY), max(_ll, _rr)
                        # ppm
                        minX, maxX = min(_ll := px + tx * sgnX,
                                         _rr := px + tx * sgnX + drawList.width * pixX), max(_ll, _rr)
                        minY, maxY = min(_ll := py + ty * sgnY,
                                         _rr := py + ty * sgnY + drawList.height * pixY), max(_ll, _rr)

                        if (minX < xPosition - xOffset < maxX and minY < yPosition - yOffset < maxY):
                            multiplets.append(multiplet)
                            if firstOnly:
                                return multiplets if multiplet in self.current.multiplets else []

                    except Exception:
                        continue

        return multiplets

    def _newStatic1DTraceData(self, spectrumView, tracesDict, positionPixel,
                              ph0=None, ph1=None, pivot=None):
        """Create a new static 1D phase trace
        """
        try:
            # ignore for 1D if already in the traces list
            for thisTrace in tracesDict:
                if spectrumView == thisTrace.spectrumView:
                    return

            data = spectrumView.spectrum.intensities
            if ph0 is not None and ph1 is not None and pivot is not None:
                preData = Phasing.phaseRealData(data, ph0, ph1, pivot)
            else:
                preData = data

            x = spectrumView.spectrum.positions
            colour = spectrumView._getColour(self.SPECTRUMPOSCOLOUR, '#aaaaaa')
            colR = int(colour.strip('# ')[:2], 16) / 255.0
            colG = int(colour.strip('# ')[2:4], 16) / 255.0
            colB = int(colour.strip('# ')[4:6], 16) / 255.0

            tracesDict.append(GLVertexArray(numLists=1,
                                            renderMode=GLRENDERMODE_RESCALE,
                                            blendMode=False,
                                            drawMode=GL.GL_LINE_STRIP,
                                            dimension=2,
                                            GLContext=self))

            numVertices = len(x)
            trace = tracesDict[-1]
            trace.indices = numVertices
            trace.numVertices = numVertices
            trace.indices = np.arange(numVertices, dtype=np.uint32)

            if self._showSpectraOnPhasing:
                trace.colors = np.array(self._phasingTraceColour * numVertices, dtype=np.float32)
            else:
                trace.colors = np.array((colR, colG, colB, 1.0) * numVertices, dtype=np.float32)

            dim = self.strip.spectrumDisplay._flipped  # draw in the correct direction

            trace.vertices = np.empty(trace.numVertices * 2, dtype=np.float32)
            trace.vertices[dim::2] = x
            trace.vertices[1 - dim::2] = preData

            # store the pre-phase data
            trace.data = data
            trace.positionPixel = positionPixel
            trace.spectrumView = spectrumView

        except Exception as es:
            tracesDict = []

    @property
    def showSpectraOnPhasing(self):
        return self._showSpectraOnPhasing

    @showSpectraOnPhasing.setter
    def showSpectraOnPhasing(self, visible):
        self._showSpectraOnPhasing = visible
        self._updatePhasingColour()
        self.update()

    def toggleShowSpectraOnPhasing(self):
        self._showSpectraOnPhasing = not self._showSpectraOnPhasing
        self._updatePhasingColour()
        self.update()

    def _updatePhasingColour(self):
        for traces in [self._staticHTraces, self._staticVTraces]:
            for trace in traces:
                colour = trace.spectrumView._getColour(self.SPECTRUMPOSCOLOUR, '#aaaaaa')
                colR = int(colour.strip('# ')[:2], 16) / 255.0
                colG = int(colour.strip('# ')[2:4], 16) / 255.0
                colB = int(colour.strip('# ')[4:6], 16) / 255.0

                numVertices = trace.numVertices
                if self._showSpectraOnPhasing:
                    trace.colors = np.array(self._phasingTraceColour * numVertices, dtype=np.float32)
                else:
                    trace.colors = np.array((colR, colG, colB, 1.0) * numVertices, dtype=np.float32)

                trace.renderMode = GLRENDERMODE_RESCALE

    def buildSpectra(self):
        """set the GL flags to build spectrum contour lists
        """
        if self.strip.isDeleted:
            return

        stackCount = 0

        # self._spectrumSettings = {}
        rebuildFlag = False
        for stackCount, spectrumView in enumerate(self._ordering):
            if spectrumView.isDeleted:
                continue

            if spectrumView.buildContours or spectrumView.buildContoursOnly:

                # flag the peaks for rebuilding
                if not spectrumView.buildContoursOnly:
                    for peakListView in spectrumView.peakListViews:
                        peakListView.buildSymbols = True
                        peakListView.buildLabels = True
                        peakListView.buildArrows = True
                    for integralListView in spectrumView.integralListViews:
                        integralListView.buildSymbols = True
                        integralListView.buildLabels = True
                    for multipletListView in spectrumView.multipletListViews:
                        multipletListView.buildSymbols = True
                        multipletListView.buildLabels = True
                        multipletListView.buildArrows = True

                spectrumView.buildContours = False
                spectrumView.buildContoursOnly = False

                # rebuild the contours
                if spectrumView not in self._contourList.keys():
                    self._contourList[spectrumView] = GLVertexArray(numLists=1,
                                                                    renderMode=GLRENDERMODE_DRAW,
                                                                    blendMode=False,
                                                                    drawMode=GL.GL_LINE_STRIP,
                                                                    dimension=2,
                                                                    GLContext=self)
                spectrumView._buildGLContours(self._contourList[spectrumView])

                self._buildSpectrumSetting(spectrumView=spectrumView, stackCount=stackCount)
                # if self._stackingMode:
                #     stackCount += 1
                rebuildFlag = True

                # define the VBOs to pass to the graphics card
                self._contourList[spectrumView].defineIndexVBO()

        # rebuild the traces as the spectrum/plane may have changed
        if rebuildFlag:
            self.rebuildTraces()

    def _updateVisibleSpectrumViews(self):
        """Update the list of visible spectrumViews when change occurs
        """
        # make the list of ordered spectrumViews
        self._ordering = list(self.strip.getSpectrumViews())

        for specView in tuple(self._spectrumSettings.keys()):
            if specView not in self._ordering:
                getLogger().debug(f'>>>_updateVisibleSpectrumViews GLWidgets  1D   delete {specView} {id(specView)}')
                getLogger().debug(f'>>> _ordering {[id(spec) for spec in self._ordering]}')
                if specView in self._spectrumSettings:
                    del self._spectrumSettings[specView]
                if specView in self._contourList:
                    self._contourList[specView]._delete()
                    del self._contourList[specView]
                if specView in self._visibleOrdering:
                    self._visibleOrdering.remove(specView)
                for k in self._visibleOrderingDict:
                    sp, _dd = k
                    if sp == specView:
                        self._visibleOrderingDict.remove(k)
                        break
                self._GLPeaks._delete()
                self._GLIntegrals._delete()
                self._GLMultiplets._delete()

                # delete the 1d string relating to the spectrumView
                self._spectrumLabelling.removeString(specView)

        # make a list of the visible and not-deleted spectrumViews
        visibleSpectrumViews = [specView for specView in self._ordering
                                if not specView.isDeleted and specView.isDisplayed]

        self._visibleOrdering = visibleSpectrumViews

        # set the first visible, or the first in the ordered list
        self._firstVisible = (visibleSpectrumViews[0]
                              if visibleSpectrumViews else
                              self._ordering[0] if self._ordering and not self._ordering[0].isDeleted else None)

        # generate the new axis labels based on the visible spectrum axisCodes
        self._buildAxisCodesWithWildCards()

        # update the labelling lists
        self._GLPeaks.setListViews(self._ordering)
        self._GLIntegrals.setListViews(self._ordering)
        self._GLMultiplets.setListViews(self._ordering)

    def getPeakPositionFromMouse(self, peak, lastStartCoordinate, cursorPosition=None):
        """Get the centre position of the clicked 1d peak
        """
        indices = getAxisCodeMatchIndices(self._axisCodes, peak.axisCodes)

        # check that the mappings are okay
        for ii, ind in enumerate(indices[:2]):
            lastStartCoordinate[ii] = peak.height if ind is None else peak.position[ind]

    def _movePeak(self, peak, deltaPosition):
        """Move the peak to new position
        """
        if self.spectrumDisplay._flipped:
            peak.height += deltaPosition[0]
            position = peak.position[0]
            position += deltaPosition[1]
            peak.position = [position]
        else:
            peak.height += deltaPosition[1]
            position = peak.position[0]
            position += deltaPosition[0]
            peak.position = [position]
        peak.volume = None
        peak.lineWidths = None

    @staticmethod
    def _tracesNeedUpdating(spectrumView=None):
        """Check if traces need updating on _lastTracePoint, use spectrumView to see
        if cursor has moved sufficiently far to warrant an update of the traces
        """
        # for 1d spectra, traces never need updating, they never move with the cursor
        return False

    def drawAliasedLabels(self):
        """Draw all the labels that require aliasing to multiple regions
        """
        shader = self._shaderTextAlias.bind()
        # set the scale to the axis limits, needs addressing correctly, possibly same as grid
        self._axisScale = QtGui.QVector4D(self.pixelX, self.pixelY, 1.0, 1.0)
        shader.setProjection(self.axisL, self.axisR, self.axisB, self.axisT, -1.0, 1.0)
        shader.setAxisScale(self._axisScale)
        shader.setStackOffset(QtGui.QVector2D(0.0, 0.0))

        shader.setAliasEnabled(self._aliasEnabled and self._aliasLabelsEnabled)

        # change to correct value for shader
        shader.setAliasShade(self._aliasShade / 100.0)

        for specView in self._ordering:

            if specView.isDeleted:
                continue

            if specView.isDisplayed and specView in self._spectrumSettings.keys():
                specSettings = self._spectrumSettings[specView]

                fxMax, fyMax = specSettings.maxSpectrumFrequency
                dxAF, dyAF = specSettings.spectralWidth
                xScale, yScale = specSettings.scale
                alias = specSettings.aliasingIndex
                folding = specSettings.foldingMode

                for ii, jj in product(range(alias[0][0], alias[0][1] + 1), range(alias[1][0], alias[1][1] + 1)):
                    foldX = foldY = 1.0
                    foldXOffset = foldYOffset = 0
                    if folding[0] == 'mirror':
                        foldX = pow(-1, ii)
                        foldXOffset = -dxAF if foldX < 0 else 0
                    if folding[1] == 'mirror':
                        foldY = pow(-1, jj)
                        foldYOffset = -dyAF if foldY < 0 else 0

                    mm = QtGui.QMatrix4x4()
                    if self._stackingMode:
                        mm.translate(*specSettings.stackedMatrixOffset)

                    if self.spectrumDisplay._flipped:
                        mm.translate(0, fyMax + (jj * dyAF) + foldYOffset)
                        mm.scale(1.0, yScale * foldY, 1.0)
                        self._axisScale = QtGui.QVector4D(self.pixelX, foldY * self.pixelY / yScale,
                                                          0.0, 1.0)
                    else:
                        mm.translate(fxMax + (ii * dxAF) + foldXOffset, 0)
                        mm.scale(xScale * foldX, 1.0, 1.0)
                        self._axisScale = QtGui.QVector4D(foldX * self.pixelX / xScale, self.pixelY,
                                                          0.0, 1.0)

                    # flipping in the same GL region -  xScale = -xScale
                    #                                   offset = fx0-dxAF
                    # circular -    offset = fx0 + dxAF*alias, alias = min->max
                    shader.setMV(mm)
                    shader.setAxisScale(self._axisScale)
                    shader.setAliasPosition(ii, jj)

                    if self._peakLabelsEnabled:
                        self._GLPeaks.drawLabels(specView)
                    if self._multipletLabelsEnabled:
                        self._GLMultiplets.drawLabels(specView)

    def drawAliasedSymbols(self, peakSymbolsEnabled, peakArrowsEnabled, multipletSymbolsEnabled,
                           multipletArrowsEnabled):
        """Draw all the symbols that require aliasing to multiple regions
        """
        shader = self._shaderPixelAlias.bind()
        # set the scale to the axis limits, needs addressing correctly, possibly same as grid
        shader.setProjection(self.axisL, self.axisR, self.axisB, self.axisT, -1.0, 1.0)

        lineThickness = self._symbolThickness
        GL.glLineWidth(lineThickness * self.viewports.devicePixelRatio)
        shader.setAliasEnabled(self._aliasEnabled)

        # change to correct value for shader
        shader.setAliasShade(self._aliasShade / 100.0)

        for specView in self._ordering:

            if specView.isDeleted:
                continue

            if specView.isDisplayed and specView in self._spectrumSettings.keys():
                specSettings = self._spectrumSettings[specView]

                fxMax, fyMax = specSettings.maxSpectrumFrequency
                dxAF, dyAF = specSettings.spectralWidth
                xScale, yScale = specSettings.scale
                alias = specSettings.aliasingIndex
                folding = specSettings.foldingMode

                for ii, jj in product(range(alias[0][0], alias[0][1] + 1), range(alias[1][0], alias[1][1] + 1)):
                    foldX = foldY = 1.0
                    foldXOffset = foldYOffset = 0
                    if folding[0] == 'mirror':
                        foldX = pow(-1, ii)
                        foldXOffset = -dxAF if foldX < 0 else 0
                    if folding[1] == 'mirror':
                        foldY = pow(-1, jj)
                        foldYOffset = -dyAF if foldY < 0 else 0

                    mm = QtGui.QMatrix4x4()
                    if self._stackingMode:
                        mm.translate(*specSettings.stackedMatrixOffset)

                    if self.spectrumDisplay._flipped:
                        # NOTE:ED - still too much hard-coding :|
                        mm.translate(0, fyMax + (jj * dyAF) + foldYOffset)
                        mm.scale(1.0, yScale * foldY, 1.0)
                    else:
                        mm.translate(fxMax + (ii * dxAF) + foldXOffset, 0)
                        mm.scale(xScale * foldX, 1.0, 1.0)

                    # flipping in the same GL region -  xScale = -xScale
                    #                                   offset = fx0-dxAF
                    # circular -    offset = fx0 + dxAF*alias, alias = min->max
                    shader.setMV(mm)
                    shader.setAliasPosition(ii, jj)

                    if peakArrowsEnabled:
                        self._GLPeaks.drawArrows(specView)
                    if multipletArrowsEnabled:
                        self._GLMultiplets.drawArrows(specView)
                    if peakSymbolsEnabled:
                        # draw the symbols
                        self._GLPeaks.drawSymbols(specView)
                    if multipletSymbolsEnabled:
                        self._GLMultiplets.drawSymbols(specView)

        GL.glLineWidth(GLDefs.GLDEFAULTLINETHICKNESS * self.viewports.devicePixelRatio)

    def drawIntegralLabels(self):
        """Draw all the integral labels
        """
        for specView in self._ordering:

            if specView.isDeleted:
                continue

            if specView.isDisplayed:
                self._GLIntegrals.drawLabels(specView)

    def drawBoundingBoxes(self):
        """Draw all the bounding boxes
        """
        pass

    def KEEPdrawSpectra(self):
        if self.strip.isDeleted:
            return

        shader = self._shaderPixel

        # self.buildSpectra()

        GL.glLineWidth(self._contourThickness * self.viewports.devicePixelRatio)
        GL.glDisable(GL.GL_BLEND)

        # only draw the traces for the spectra that are visible
        specTraces = [trace.spectrumView for trace in self._staticHTraces]

        _visibleSpecs = [specView for specView in self._ordering
                         if not specView.isDeleted and
                         specView.isDisplayed and
                         specView._showContours and
                         specView in self._spectrumSettings.keys() and
                         specView in self._contourList.keys() and
                         (specView not in specTraces or self.showSpectraOnPhasing)]

        # for spectrumView in self._ordering:
        #
        #     if spectrumView.isDeleted:
        #         continue
        #     if not spectrumView._showContours:
        #         continue
        #
        #     if spectrumView.isDisplayed and spectrumView in self._spectrumSettings.keys():
        #         # set correct transform when drawing this contour
        #
        #         if spectrumView in self._contourList.keys() and \
        #                 (spectrumView not in specTraces or self.showSpectraOnPhasing):

        for spectrumView in _visibleSpecs:
            if self._stackingMode:
                # use the stacking matrix to offset the 1D spectra
                shader.setMVMatrix(self._spectrumSettings[spectrumView].stackedMatrix)
            # draw contours
            self._contourList[spectrumView].drawVertexColorVBO()

        # reset lineWidth
        GL.glLineWidth(GLDefs.GLDEFAULTLINETHICKNESS * self.viewports.devicePixelRatio)

    def drawSpectra(self):
        if self.strip.isDeleted:
            return
        if self.strip._isPhasingOn and not self.showSpectraOnPhasing:
            return

        shader = self._shaderPixel

        GL.glLineWidth(self._contourThickness * self.viewports.devicePixelRatio)
        GL.glDisable(GL.GL_BLEND)

        for spectrumView in self._ordering:

            if spectrumView.isDeleted:
                continue
            if spectrumView.spectrum is None or (spectrumView.spectrum and spectrumView.spectrum.isDeleted):
                continue
            if not spectrumView._showContours:
                continue

            # need to do this on the GPU
            if spectrumView.isDisplayed and spectrumView in self._spectrumSettings.keys():
                # only draw the traces for the spectra that are visible
                specTraces = [trace.spectrumView for trace in self._staticHTraces]

                # set correct transform when drawing this contour
                if spectrumView.spectrum.displayFoldedContours:
                    specSettings = self._spectrumSettings[spectrumView]

                    fxMax, fyMax = specSettings.maxSpectrumFrequency
                    dxAF, dyAF = specSettings.spectralWidth
                    alias = specSettings.aliasingIndex
                    folding = specSettings.foldingMode

                    for ii, jj in product(range(alias[0][0], alias[0][1] + 1), range(alias[1][0], alias[1][1] + 1)):
                        foldX = foldY = 1.0
                        foldXOffset = foldYOffset = 0
                        if folding[0] == 'mirror':
                            foldX = pow(-1, ii)
                            foldXOffset = (2 * fxMax - dxAF) if foldX < 0 else 0
                        if folding[1] == 'mirror':
                            foldY = pow(-1, jj)
                            foldYOffset = (2 * fyMax - dyAF) if foldY < 0 else 0

                        mm = QtGui.QMatrix4x4()
                        if self._stackingMode:
                            mm.translate(*specSettings.stackedMatrixOffset)

                        if self.spectrumDisplay._flipped:
                            mm.translate(0, (jj * dyAF) + foldYOffset)
                            mm.scale(1.0, foldY, 1.0)
                        else:
                            mm.translate((ii * dxAF) + foldXOffset, 0)
                            mm.scale(foldX, 1.0, 1.0)

                        shader.setMV(mm)

                        if spectrumView in self._contourList:
                            self._contourList[spectrumView].drawVertexColorVBO()

                else:
                    if spectrumView in self._contourList.keys() and \
                            (spectrumView not in specTraces or self.showSpectraOnPhasing):

                        # use the stacking matrix to offset the 1D spectra
                        mm = QtGui.QMatrix4x4()
                        if self._stackingMode:
                            mm.translate(*specSettings.stackedMatrixOffset)
                        shader.setMV(mm)
                        # draw contours
                        if spectrumView in self._contourList:
                            self._contourList[spectrumView].drawVertexColorVBO()

        # reset lineWidth
        GL.glLineWidth(GLDefs.GLDEFAULTLINETHICKNESS * self.viewports.devicePixelRatio)

    def buildDiagonals(self):
        """Build a list containing the diagonal and the spinningRate lines for the sidebands
        """
        pass

    def _buildSpectrumSetting(self, spectrumView, stackCount=0):
        # if spectrumView.spectrum.headerSize == 0:
        #     return

        # delta = [-1.0 if self.XDIRECTION else 1.0,
        #          -1.0 if self.YDIRECTION else 1.0]
        delta = [self.XDIRECTION, self.YDIRECTION]
        stack = [stackCount * self._stackingValue[0],
                 stackCount * self._stackingValue[1]]
        self._spectrumSettings[spectrumView] = specVals = spectrumView._getVisibleSpectrumViewParams(delta=delta,
                                                                                                     stacking=stack)

        self._minXRange = min(self._minXRange,
                              GLDefs.RANGEMINSCALE * specVals.spectralWidth[0] / specVals.pointCount[0])
        self._maxXRange = max(self._maxXRange, specVals.spectralWidth[0])
        self._minYRange = min(self._minYRange,
                              GLDefs.RANGEMINSCALE * specVals.spectralWidth[1] / specVals.pointCount[1])
        self._maxYRange = max(self._maxYRange, specVals.spectralWidth[1])

        self._rangeXDefined = True
        self._rangeYDefined = True
        self._maxX = max(self._maxX, specVals.maxSpectrumFrequency[0])
        self._minX = min(self._minX, specVals.minSpectrumFrequency[0])
        self._maxY = max(self._maxY, specVals.maxSpectrumFrequency[1])
        self._minY = min(self._minY, specVals.minSpectrumFrequency[1])

        self._buildAxisCodesWithWildCards()

    def buildCursors(self):
        """Build and draw the cursors/doubleCursors
        """
        if self._disableCursorUpdate or not self._crosshairVisible:
            return

        # get the next cursor drawList
        self._advanceGLCursor()
        drawList = self._glCursorQueue[self._glCursorHead]
        vertices = []
        indices = []
        index = 0

        # map the cursor to the ratio coordinates - double cursor is flipped about the line x=y
        cursorCoordinate = self.getCurrentCursorCoordinate()
        newCoords = self._scaleAxisToRatio(cursorCoordinate[:2])
        # doubleCoords = self._scaleAxisToRatio(self.getCurrentDoubleCursorCoordinates()[0:2])

        if getCurrentMouseMode() == PICK and self.underMouse():

            x = self.deltaX * 8
            y = self.deltaY * 8

            vertices = [newCoords[0] - x, newCoords[1] - y,
                        newCoords[0] + x, newCoords[1] - y,
                        newCoords[0] + x, newCoords[1] - y,
                        newCoords[0] + x, newCoords[1] + y,
                        newCoords[0] + x, newCoords[1] + y,
                        newCoords[0] - x, newCoords[1] + y,
                        newCoords[0] - x, newCoords[1] + y,
                        newCoords[0] - x, newCoords[1] - y
                        ]
            indices = [0, 1, 2, 3, 4, 5, 6, 7]
            col = self.mousePickColour
            index = 8

        else:
            col = self.foreground

        if not self.spectrumDisplay.phasingFrame.isVisible() and (coords := self.current.mouseMovedDict):
            # read values from isotopeCode or axisCode
            if self._preferences.matchAxisCode == 0:  # default - match atom type

                # add extra 'isotopeCode' so that 1D appears correctly
                if self.strip.spectrumDisplay._flipped:
                    atomTypes = ('intensity',) + self.spectrumDisplay.isotopeCodes
                else:
                    atomTypes = self.spectrumDisplay.isotopeCodes + ('intensity',)

                xPosList = coords[AXIS_MATCHATOMTYPE].get(atomTypes[0], [])
                yPosList = coords[AXIS_MATCHATOMTYPE].get(atomTypes[1], [])
            else:
                atCodes = self._orderedAxes
                xPosList = coords[AXIS_FULLATOMNAME].get(atCodes[0].code, [])
                yPosList = coords[AXIS_FULLATOMNAME].get(atCodes[1].code, [])

            foundX = []
            foundY = []
            if not self._updateVTrace and newCoords[0] is not None:
                for pos in xPosList:
                    x, _y = self._scaleAxisToRatio([pos, 0])
                    if all(abs(x - val) > self.deltaX for val in foundX):
                        # store the found value so that overlaying lines are not drawn - OpenGL uses an XOR draw mode
                        foundX.append(x)
                        vertices.extend([x, 1.0, x, 0.0])
                        indices.extend([index, index + 1])
                        index += 2

            if not self._updateHTrace and newCoords[1] is not None:
                for pos in yPosList:
                    _x, y = self._scaleAxisToRatio([0, pos])
                    if all(abs(y - val) > self.deltaY for val in foundY):
                        foundY.append(y)
                        vertices.extend([0.0, y, 1.0, y])
                        indices.extend([index, index + 1])
                        index += 2

        drawList.vertices = np.array(vertices, dtype=np.float32)
        drawList.indices = np.array(indices, dtype=np.int32)
        drawList.numVertices = len(vertices) // 2
        drawList.colors = np.array(col * drawList.numVertices, dtype=np.float32)

        # build and draw the VBO
        drawList.defineIndexVBO()

    def _updateMouseDict(self, cursorCoordinate):
        try:
            mouseMovedDict = self.current.mouseMovedDict
        except:
            # initialise a new mouse moved dict
            mouseMovedDict = {MOUSEDICTSTRIP    : self.strip,
                              AXIS_MATCHATOMTYPE: {},
                              AXIS_FULLATOMNAME : {},
                              }

        xPos = yPos = 0
        atTypes = mouseMovedDict[AXIS_MATCHATOMTYPE] = {}
        atCodes = mouseMovedDict[AXIS_FULLATOMNAME] = {}
        if self.strip.spectrumDisplay._flipped:
            isoCodes = ('intensity',) + self.spectrumDisplay.isotopeCodes
        else:
            isoCodes = self.spectrumDisplay.isotopeCodes + ('intensity',)

        # transfer the mouse position from the coords to the mouseMovedDict for the other displays
        for n, (atomType, axis) in enumerate(zip(isoCodes, self._orderedAxes)):
            ats = atTypes.setdefault(atomType, [])
            atcs = atCodes.setdefault(axis.code, [])
            if n == 0:
                xPos = pos = cursorCoordinate[0]
            elif n == 1:
                yPos = pos = cursorCoordinate[1]
            else:
                break

            ats.append(pos)
            atcs.append(pos)

        self.current.cursorPosition = (xPos, yPos)
        self.current.mouseMovedDict = mouseMovedDict

        return mouseMovedDict

    # def initialiseTraces(self):
    #     # set up the arrays and dimension for showing the horizontal/vertical traces
    #     for spectrumView in self._ordering:  # strip.spectrumViews:
    #
    #         if spectrumView.isDeleted:
    #             continue
    #
    #         self._spectrumSettings[spectrumView] = {}
    #         visSpec = spectrumView.getVisibleState(dimensionCount=2)
    #
    #         # get the bounding box of the spectra
    #         dx = self.sign(self.axisR - self.axisL)
    #         fxMax, fxMin = visSpec[0].maxSpectrumFrequency, visSpec[0].minSpectrumFrequency
    #
    #         # check tolerances
    #         if not self._widthsChangedEnough((fxMax, 0.0), (fxMin, 0.0), tol=1e-10):
    #             fxMax, fxMin = 1.0, -1.0
    #
    #         dxAF = fxMax - fxMin
    #         xScale = dx * dxAF / visSpec[0].pointCount
    #
    #         dy = self.sign(self.axisT - self.axisB)
    #         if spectrumView.spectrum.intensities is not None and spectrumView.spectrum.intensities.size != 0:
    #             fyMax = float(np.max(spectrumView.spectrum.intensities))
    #             fyMin = float(np.min(spectrumView.spectrum.intensities))
    #         else:
    #             fyMax, fyMin = 0.0, 0.0
    #
    #         # check tolerances
    #         if not self._widthsChangedEnough((fyMax, 0.0), (fyMin, 0.0), tol=1e-10):
    #             fyMax, fyMin = 1.0, -1.0
    #
    #         dyAF = fyMax - fyMin
    #         yScale = dy * dyAF / 1.0
    #
    #         # create model-view matrix for the spectrum to be drawn
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_MATRIX] = np.zeros((16,), dtype=np.float32)
    #
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_MATRIX][:16] = [xScale, 0.0, 0.0, 0.0,
    #                                                                              0.0, yScale, 0.0, 0.0,
    #                                                                              0.0, 0.0, 1.0, 0.0,
    #                                                                              fxMax, fyMax, 0.0, 1.0]
    #         # setup information for the horizontal/vertical traces
    #         # self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_XLIMITS] = (fxMin, fxMax)
    #         # self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_YLIMITS] = (fyMin, fyMax)
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_LIMITS] = (fxMin, fxMax), (fyMin, fyMax)
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_AF] = (dxAF, dyAF)
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_SCALE] = (xScale, yScale)
    #
    #         indices = getAxisCodeMatchIndices(self.strip.axisCodes, spectrumView.spectrum.axisCodes)
    #         self._spectrumSettings[spectrumView][GLDefs.SPECTRUM_POINTINDEX] = indices
