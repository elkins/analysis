"""Module Documentation here

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
__dateModified__ = "$dateModified: 2024-08-07 13:10:49 +0100 (Wed, August 07, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from itertools import product
from PyQt5 import QtGui
from ccpn.ui.gui.lib.GuiSpectrumView import GuiSpectrumView, SpectrumCache
from ccpn.util.Colour import spectrumColours, colorSchemeTable


class GuiSpectrumView1d(GuiSpectrumView):
    hPhaseTrace = None
    buildContours = True
    buildContoursOnly = False

    def __init__(self):
        """ spectrumPane is the parent
            spectrum is the Spectrum name or object
            """
        GuiSpectrumView.__init__(self)

        self._application = self.strip.spectrumDisplay.mainWindow.application

        self.data = self.spectrum.positions, self.spectrum.intensities
        # print('>>>filePath', self.spectrum.filePath, self.spectrum.positions, self.spectrum.intensities)

        # for strip in self.strips:
        if self.spectrum.sliceColour is None:
            if len(self.strip.spectrumViews) < 12:
                self.spectrum.sliceColour = list(spectrumColours.keys())[len(self.strip.spectrumViews) - 1]
            else:
                self.spectrum.sliceColour = list(spectrumColours.keys())[(len(self.strip.spectrumViews) % 12) - 1]

        self.hPhaseTrace = None
        self.buildContours = True
        self.buildContoursOnly = False

    def getVisibleState(self, dimensionCount=None):
        """Get the visible state for the X/Y axes
        """
        return (self._getSpectrumViewParams(0),)

    def _turnOnPhasing(self):

        phasingFrame = self.strip.spectrumDisplay.phasingFrame
        if phasingFrame.isVisible():
            if self.hPhaseTrace:
                self.hPhaseTrace.setVisible(True)
            else:
                self._newPhasingTrace()

    def _turnOffPhasing(self):

        if self.hPhaseTrace:
            self.hPhaseTrace.setVisible(False)

    def refreshData(self):
        self.data = self.spectrum.positions, self.spectrum.intensities

        # spawn a rebuild in the openGL strip
        self.buildContours = True
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=self)
        GLSignals.emitPaintEvent()

    def _buildGLContours(self, glList, firstShow=False):
        # build a glList for the spectrum
        glList.clearArrays()

        numVertices = len(self.spectrum.positions)
        # glList.indices = numVertices
        glList.numVertices = numVertices
        # glList.indices = np.arange(numVertices, dtype=np.uint32)

        colour = self._getColour('sliceColour', '#AAAAAA')
        if not colour.startswith('#'):
            # get the colour from the gradient table or a single red
            colour = colorSchemeTable[colour][0] if colour in colorSchemeTable else '#FF0000'

        colR = int(colour.strip('# ')[0:2], 16) / 255.0
        colG = int(colour.strip('# ')[2:4], 16) / 255.0
        colB = int(colour.strip('# ')[4:6], 16) / 255.0

        glList.colors = np.array([colR, colG, colB, 1.0] * numVertices, dtype=np.float32)
        glList.vertices = np.zeros(numVertices * 2, dtype=np.float32)

        try:
            dim = self.strip.spectrumDisplay._flipped
            # may be empty
            glList.vertices[dim::2] = self.spectrum.positions
            glList.vertices[1 - dim::2] = self.spectrum.intensities
        except Exception:
            pass

    @staticmethod
    def _paintContoursNoClip(plotHeight=0.0):
        # NOTE:ED - not sure how to handle this :|
        pass

    @staticmethod
    def _getVisiblePlaneList(firstVisible=None, minimumValuePerPoint=None):
        # No visible planes for 1d
        return None, None, None

    def _getVisibleSpectrumViewParams(self, dimRange=None, delta=None, stacking=None) -> SpectrumCache:
        """Get parameters for axisDim'th axis (zero-origin) of spectrum in display-order.

        Returns SpectrumCache object of the form:

            dimensionIndices            visible order of dimensions

            pointCount                  number of points in the dimension
            ppmPerPoint                 ppm width spanning a point value
            ppmToPoint                  method to convert ppm to data-source point value

            minSpectrumFrequency        minimum spectrum frequency
            maxSpectrumFrequency        maximum spectrum frequency
                                        spectrum frequencies defined by the ppm positions of points [1] and [pointCount]
            spectralWidth               maxSpectrumFrequency - minSpectrumFrequency
            spectrometerFrequency       spectrometer frequency to give correct Hz/ppm/point conversion

            minAliasingFrequency        minimum aliasing frequency
            maxAliasingFrequency        maximum aliasing frequency
                                        aliasing frequencies define the span of the spectrum, beyond the range of the defined points
                                        for aliasingIndex (0, 0) this will correspond to points [0.5], [pointCount + 0.5]
            aliasingWidth               maxAliasingFrequency - minAliasingFrequency
            aliasingIndex               a tuple (min, max) defining how many integer multiples the aliasing frequencies span the spectrum
                                        (0, 0) implies the aliasing range matches the spectral range
                                        (s, t) implies:
                                            the minimum limit = minSpectrumFrequency - 's' spectral widths - should always be negative or zero
                                            the maximum limit = maxSpectrumFrequency + 't' spectral widths - should always be positive or zero
            axisDirection               1.0 if the point [pointCount] corresponds to the maximum spectrum-frequency
                                        else -1.0, i.e., ppm increases with point-count

            minFoldingFrequency         minimum folding frequency
            maxFoldingFrequency         maximum folding frequency
                                        folding frequencies define the ppm positions of points [0.5] and [pointCount + 0.5]
                                        currently the exact ppm at which the spectrum is folded
            foldingWidth                maxFoldingFrequency - minFoldingFrequency
            foldingMode                 the type of folding: 'circular', 'mirror' or None

            regionBounds                a tuple of ppm values (min, ..., max) in multiples of the spectral width from the lower aliasingLimit
                                        to the upper aliasingLimit
            isTimeDomain                True if the axis is a time domain, otherwise False

            delta                       multipliers for the axes, either -1.0|1.0
            scale                       scaling for each dimension
        """
        # points are not defined for the spectrum
        cache = SpectrumCache(dimensionIndices=[0, 1],

                              pointCount=[1, 1],
                              ppmPerPoint=[1.0, 1.0],
                              ppmToPoint=[lambda: 0.0, lambda: 0.0],

                              minSpectrumFrequency=[-1.0, -1.0],
                              maxSpectrumFrequency=[1.0, 1.0],
                              spectralWidth=[2.0, 2.0],
                              spectrometerFrequency=[0.0, 0.0],

                              minAliasedFrequency=[-1.0, -1.0],
                              maxAliasedFrequency=[1.0, 1.0],
                              aliasingWidth=[2.0, 2.0],
                              aliasingIndex=[[0, 0], [0, 0]],
                              axisDirection=[1.0, 1.0],

                              minFoldingFrequency=[-1.0, -1.0],
                              maxFoldingFrequency=[1.0, 1.0],
                              foldingWidth=[2.0, 2.0],
                              foldingMode=[0, 0],

                              regionBounds=[[-1.0, 1.0], [-1.0, 1.0]],
                              isTimeDomain=[False, False],
                              axisCode=['', ''],
                              isotopeCode=['', ''],

                              scale=[1.0, 1.0],
                              delta=delta,

                              stackedMatrixOffset=[0.0, 0.0],
                              matrix=np.array([1.0, 0.0, 0.0, 0.0,
                                               0.0, 1.0, 0.0, 0.0,
                                               0.0, 0.0, 1.0, 0.0,
                                               0.0, 0.0, 0.0, 1.0],
                                              dtype=np.float32),
                              stackedMatrix=np.array([1.0, 0.0, 0.0, 0.0,
                                                      0.0, 1.0, 0.0, 0.0,
                                                      0.0, 0.0, 1.0, 0.0,
                                                      0.0, 0.0, 0.0, 1.0],
                                                     dtype=np.float32),

                              spinningRate=0.0,
                              )

        if self.pointCounts[0]:
            # fill in the required values for the axis defined by whether the spectrum-display is to be flipped
            minFoldingFrequencies = [min(*val) for val in self.foldingLimits[:2]]
            spectralWidths = self.spectralWidths[:2]
            aliasingIndexes = self.aliasingIndexes[:2]
            regionBounds = [[minFoldingFrequency + ii * spectralWidth
                             for ii in range(aliasingIndex[0], aliasingIndex[1] + 2)]
                            for minFoldingFrequency, spectralWidth, aliasingIndex in
                            zip(minFoldingFrequencies, spectralWidths, aliasingIndexes)]

            minSpec = [min(*val) for val in self.spectrumLimits][:2]
            maxSpec = [max(*val) for val in self.spectrumLimits][:2]
            specWidth = list(self.spectralWidths[:2])

            # spectrum frequencies are not badly defined
            if abs(maxSpec[0] - minSpec[0]) < 1e-8:
                minSpec[0] = -1.0
                maxSpec[0] = 1.0
                specWidth[0] = 2.0

            dim = self.strip.spectrumDisplay._flipped  # dim is 0|1, 1 for 1d if flipped

            # intensity dimension
            if self.spectrum.intensities is not None and self.spectrum.intensities.size != 0:
                fMax = float(np.max(self.spectrum.intensities))
                fMin = float(np.min(self.spectrum.intensities))

                if (fMax, fMin) == (0.0, 0.0):
                    fMax, fMin = 1.0, -1.0
            else:
                fMax, fMin = 1.0, -1.0
            cache.minSpectrumFrequency[1 - dim] = fMin
            cache.maxSpectrumFrequency[1 - dim] = fMax
            cache.spectralWidth[1 - dim] = fMax - fMin
            cache.axisCode[1 - dim] = 'intensity'

            cache.minAliasedFrequency[1 - dim] = fMin
            cache.maxAliasedFrequency[1 - dim] = fMax
            cache.aliasingWidth[1 - dim] = fMax - fMin

            cache.minFoldingFrequency[1 - dim] = fMin
            cache.maxFoldingFrequency[1 - dim] = fMax
            cache.foldingWidth[1 - dim] = fMax - fMin

            # main spectrum dimension
            cache.dimensionIndices = [dim, 1 - dim]
            cache.pointCount[dim] = self.pointCounts[0]
            cache.ppmPerPoint[dim] = self.ppmPerPoints[0]
            cache.ppmToPoint[dim] = self.ppmToPoints[0]

            cache.minSpectrumFrequency[dim] = minSpec[0]
            cache.maxSpectrumFrequency[dim] = maxSpec[0]
            cache.spectralWidth[dim] = specWidth[0]
            cache.spectrometerFrequency[dim] = self.spectrometerFrequencies[0]

            cache.minAliasedFrequency[dim] = [val[0] for val in self.aliasingLimits][0]
            cache.maxAliasedFrequency[dim] = [val[1] for val in self.aliasingLimits][0]
            cache.aliasingWidth[dim] = self.aliasingWidths[0]
            cache.aliasingIndex[dim] = self.aliasingIndexes[0]
            cache.axisDirection[dim] = -1.0 if self.axesReversed[0] else 1.0

            cache.minFoldingFrequency[dim] = [min(*val) for val in self.foldingLimits][0]
            cache.maxFoldingFrequency[dim] = [max(*val) for val in self.foldingLimits][0]
            cache.foldingWidth[dim] = self.foldingWidths[0]
            cache.foldingMode[dim] = self.foldingModes[0]

            cache.regionBounds[dim] = regionBounds[0]
            cache.isTimeDomain[dim] = self.isTimeDomains[0]
            cache.axisCode[dim] = self.axisCodes[0]
            cache.isotopeCode[dim] = self.isotopeCodes[0]

            # cache.scale[dim] = delta[dim] * specWidth[0] / self.pointCounts[0]
            cache.scale[dim] = (-1.0 if self.axesReversed[0] else 1.0) * specWidth[0] / self.pointCounts[0]
            # cache.delta[dim] = delta[dim]

            cache.stackedMatrixOffset = np.array(stacking, dtype=np.float32)
            cache.matrix = np.array([cache.scale[0], 0.0, 0.0, 0.0,
                                     0.0, cache.scale[1], 0.0, 0.0,
                                     0.0, 0.0, 1.0, 0.0,
                                     cache.maxSpectrumFrequency[0], cache.maxSpectrumFrequency[1], 0.0, 1.0],
                                    dtype=np.float32)
            cache.stackedMatrix = np.array([1.0, 0.0, 0.0, 0.0,
                                            0.0, 1.0, 0.0, 0.0,
                                            0.0, 0.0, 1.0, 0.0,
                                            stacking[0], stacking[1], 0.0, 1.0],
                                           dtype=np.float32)

            cache.spinningRate = self.spectrum.spinningRate

            # # build the point->ppm matrices here for the display
            # foldX = 1.0 if self.axesReversed[0] else -1.0
            # foldXOffset = spectralWidths[0] if self.axesReversed[0] else 0
            # centreMatrix = None
            # mvMatrices = []
            # for ii, jj in product(range(aliasingIndexes[0][0], aliasingIndexes[0][1] + 1),
            #                       range(aliasingIndexes[1][0], aliasingIndexes[1][1] + 1)):
            #     # if folding[0] == 'mirror':
            #     #     # to be implemented correctly later
            #     #     foldX = pow(-1, ii)
            #     #     foldXOffset = -dxAF if foldX < 0 else 0
            #     # if folding[1] == 'mirror':
            #     #     foldY = pow(-1, jj)
            #     #     foldYOffset = -dyAF if foldY < 0 else 0
            #     mm = QtGui.QMatrix4x4()
            #     mm.translate(minSpec[0] + (ii * specWidth[0]) + foldXOffset,
            #                  minSpec[1] + (jj * specWidth[1]) + foldYOffset)
            #     mm.scale(xScale * foldX, yScale * foldY, 1.0)
            #     mvMatrices.append(mm)
            #     if ii == 0 and jj == 0:
            #         # SHOULD always be here
            #         centreMatrix = mm
            # if not centreMatrix:
            #     raise RuntimeError(f'{self.__class__.__name__}._getVisibleSpectrumViewParams: '
            #                        f'centre matrix not defined')

            return cache
