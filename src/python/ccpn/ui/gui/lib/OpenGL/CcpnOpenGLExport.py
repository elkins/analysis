"""
Code for exporting OpenGL stripDisplay to pdf and svg files.
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
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2018-12-20 13:28:13 +0000 (Thu, December 20, 2018) $"
#=========================================================================================
# Start of code
#=========================================================================================

# import sys
# import os
import io
import numpy as np
import math
# import glob
import contextlib
from itertools import product
from dataclasses import dataclass
from collections import OrderedDict
from collections.abc import Iterable
from PyQt5 import QtGui
# from PyQt5.QtCore import QStandardPaths
# from PyQt5.QtGui import QFontDatabase
# from PyQt5.QtWidgets import QApplication
from reportlab.platypus import SimpleDocTemplate, Paragraph, Flowable
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
# from reportlab.graphics import renderSVG, renderPS, renderPM
# from reportlab.graphics.renderPM import renderScaledDrawing, PMCanvas, draw
from reportlab.graphics.shapes import Drawing, Rect, String, PolyLine, Group, Path, Polygon
# from reportlab.graphics.shapes import definePath
# from reportlab.graphics.renderSVG import draw, renderScaledDrawing, SVGCanvas
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import portrait, landscape, letter, A0, A1, A2, A3, A4, A5, A6
from reportlab.platypus.tables import Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ccpn.ui.gui.widgets.Font import getSystemFonts
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLViewports import viewportDimensions
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import GLLINE_STYLES_ARRAY, getAliasSetting

from ccpn.ui.gui.lib.OpenGL import GL
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import GLGRIDLINES, GLAXISLABELS, GLAXISMARKS, \
    GLINTEGRALLABELS, GLINTEGRALSYMBOLS, GLMARKLABELS, GLMARKLINES, GLMULTIPLETLABELS, GLREGIONS, \
    GLMULTIPLETSYMBOLS, GLOTHERLINES, GLPEAKLABELS, GLPEAKSYMBOLS, GLPEAKARROWS, GLMULTIPLETARROWS, \
    GLPRINTTYPE, GLSELECTEDPIDS, \
    GLSPECTRUMBORDERS, GLSPECTRUMCONTOURS, GLSPECTRUMLABELS, \
    GLSTRIP, GLSTRIPLABELLING, GLTRACES, GLACTIVETRACES, GLPLOTBORDER, \
    GLPAGETYPE, GLPAGESIZE, GLSPECTRUMDISPLAY, GLBACKGROUND, GLBASETHICKNESS, GLSYMBOLTHICKNESS, \
    GLCONTOURTHICKNESS, GLFOREGROUND, GLSHOWSPECTRAONPHASE, \
    GLAXISTITLES, GLAXISUNITS, GLSTRIPDIRECTION, GLSTRIPPADDING, GLEXPORTDPI, \
    GLCURSORS, GLDIAGONALLINE, GLDIAGONALSIDEBANDS, \
    MAINVIEW, MAINVIEWFULLHEIGHT, MAINVIEWFULLWIDTH, \
    RIGHTAXIS, RIGHTAXISBAR, FULLRIGHTAXIS, FULLRIGHTAXISBAR, \
    BOTTOMAXIS, BOTTOMAXISBAR, FULLBOTTOMAXIS, FULLBOTTOMAXISBAR, FULLVIEW, BLANKVIEW, \
    GLALIASSHADE, GLSTRIPREGIONS, \
    GLSCALINGMODE, GLSCALINGPERCENT, GLSCALINGBYUNITS, \
    GLPRINTFONT, GLUSEPRINTFONT, GLSCALINGAXIS
# from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import GLFILENAME, GLWIDGET, GLAXISLINES, GLAXISMARKSINSIDE, \
#     GLFULLLIST, GLEXTENDEDLIST, GLALIASENABLED, GLALIASLABELSENABLED
from ccpn.ui.gui.popups.ExportStripToFile import PAGEPORTRAIT, DEFAULT_FONT, PAGESIZEA6, PAGESIZEA5, \
    PAGESIZEA4, PAGESIZEA3, PAGESIZEA2, PAGESIZEA1, PAGESIZEA0, PAGESIZELETTER, PAGESIZES
# from ccpn.ui.gui.popups.ExportStripToFile import EXPORTPDF, EXPORTSVG, EXPORTTYPES, \
#     PAGELANDSCAPE, PAGETYPES
from ccpn.ui.gui.popups.ExportStripToFile import EXPORTPNG
# from ccpn.util.Colour import colorSchemeTable
from ccpn.core.lib.ContextManagers import catchExceptions
from ccpn.util.Report import Report
from ccpn.util.Constants import SCALE_PERCENT, SCALE_UNIT_CM, SCALE_UNIT_INCH, SCALE_INCH_UNIT, SCALE_CM_UNIT, \
    SCALING_MODES
from ccpn.util.Common import isLinux, isMacOS, isWindowsOS
from ccpn.util.Path import aPath
from ccpn.util.Logging import getLogger


PLOTLEFT = 'plotLeft'
PLOTBOTTOM = 'plotBottom'
PLOTWIDTH = 'plotWidth'
PLOTHEIGHT = 'plotHeight'

PDFSTROKEWIDTH = 'strokeWidth'
PDFSTROKECOLOR = 'strokeColor'
PDFSTROKELINECAP = 'strokeLineCap'
PDFFILLCOLOR = 'fillColor'
PDFFILL = 'fill'
PDFFILLMODE = 'fillMode'
PDFSTROKE = 'stroke'
PDFSTROKEDASHARRAY = 'strokeDashArray'
PDFSTROKEDASHOFFSET = 'strokeDashOffset'
PDFCLOSEPATH = 'closePath'
PDFLINES = 'lines'
FRAMEPADDING = 13
PAGEREFERENCE = {PAGESIZEA0    : A0,
                 PAGESIZEA1    : A1,
                 PAGESIZEA2    : A2,
                 PAGESIZEA3    : A3,
                 PAGESIZEA4    : A4,
                 PAGESIZEA5    : A5,
                 PAGESIZEA6    : A6,
                 PAGESIZELETTER: letter}


def alphaClip(value):
    # return np.clip(float(value), 0.0, 1.0)
    return float(value)


class GLExporter():
    """
    Class container for exporting OpenGL stripDisplay to a file or object
    """

    def __init__(self, parent, strip, filename, params):
        """
        Initialise the exporter
        :param filename - not required
        :param params - parameter dict from the exporter dialog

        Need to have different settingsif the output is to a .png file
        This needs a multiplier based on (output dpi / 72) and scale = (output dpi / 72)
         - a thickness modifier on all drawing output
        Fonts need a 0.5 scaling for .png
        """
        self._parent = parent
        self.strip = strip
        self.project = self.strip.project
        self.filename = filename
        self.params = params

        # set the page orientation
        pageType = portrait if self.params[GLPAGETYPE] == PAGEPORTRAIT else landscape
        _pageSize = PAGEREFERENCE.get(self.params[GLPAGESIZE]) or A4

        self._report = Report(self, self.project, filename, pagesize=pageType(_pageSize),
                              leftMargin=1, rightMargin=1, topMargin=1, bottomMargin=1)

        self._ordering = []
        self._importFonts()

        self._printType = self.params[GLPRINTTYPE]

        if self._printType == EXPORTPNG:
            # need to set the scaling for a PNG file and alter baseThickness/font size
            self._dpiScale = self.params[GLEXPORTDPI] / 72

            self.baseThickness = self.params[GLBASETHICKNESS] * self._dpiScale
            self.symbolThickness = self.params[GLSYMBOLTHICKNESS]
            self.contourThickness = self.params[GLCONTOURTHICKNESS]

            self._pngScale = 0.5
        else:
            self.baseThickness = self.params[GLBASETHICKNESS]
            self.symbolThickness = self.params[GLSYMBOLTHICKNESS]
            self.contourThickness = self.params[GLCONTOURTHICKNESS]

            self._pngScale = 1.0
            self._dpiScale = 1.0

        # set default colours
        self.backgroundColour = colors.Color(*self.params[GLBACKGROUND], alpha=alphaClip(1.0))
        self.foregroundColour = colors.Color(*self.params[GLFOREGROUND], alpha=alphaClip(1.0))

        # build all the sections of the pdf
        self.stripReports = []
        self.stripWidths = []
        self.stripHeights = []
        self.stripSpacing = 0

        # keep track of the individual _mainPlots to build the png/ps/svg files
        self._mainPlots = []

        if self.params[GLSPECTRUMDISPLAY]:
            # print the whole spectrumDisplay
            spectrumDisplay = self.params[GLSPECTRUMDISPLAY]

            _ratios = self._getStripUpdateRatios(spectrumDisplay.orderedStrips)

            self._selectedStrip = self.strip
            self.numStrips = len(spectrumDisplay.strips)
            self._buildPageDimensions(spectrumDisplay.strips, _ratios)

            for strNum, strip in enumerate(spectrumDisplay.orderedStrips):
                self.stripNumber = strNum
                self._linkedAxisStrip = None
                self._createStrip(strip, singleStrip=False, axesOnly=False)
                self._lastMainView = self.mainView
                if strNum < self.numStrips - 1:
                    if self.params[GLSTRIPDIRECTION] == 'Y':
                        if self._parent and not self._parent._drawRightAxis:
                            self._createSpacerStrip()
                    elif self._parent and not self._parent._drawBottomAxis:
                        self._createSpacerStrip()

            # build strip for the floating axis
            self.stripNumber = self.numStrips
            self._linkedAxisStrip = spectrumDisplay.orderedStrips[-1]

            # self._parent still points to the last strip - check not to double up the last axis
            if self.params[GLSTRIPDIRECTION] == 'Y':
                if self._parent and not self._parent._drawRightAxis:
                    self._createStrip(strip, spectrumDisplay._rightGLAxis, singleStrip=False, axesOnly=True)
            elif self._parent and not self._parent._drawBottomAxis:
                self._createStrip(strip, spectrumDisplay._bottomGLAxis, singleStrip=False, axesOnly=True)

            # reset after creating the other strips
            # NOTE:ED - need to store the previous values
            self._resetStripRightBottomAxes()

        else:
            # print a single strip
            strip = self.params[GLSTRIP]
            spectrumDisplay = strip.spectrumDisplay

            _ratios = self._getStripUpdateRatios([strip])

            self._selectedStrip = strip
            self.numStrips = 1
            self._buildPageDimensions([strip], _ratios)

            self.stripNumber = 0
            self._linkedAxisStrip = None
            self._createStrip(strip, singleStrip=True, axesOnly=False)
            self._lastMainView = self.mainView

            self._linkedAxisStrip = strip
            if self.params[GLSTRIPDIRECTION] == 'Y':
                if self._parent and not self._parent._drawRightAxis:
                    self._createStrip(strip, spectrumDisplay._rightGLAxis, singleStrip=True, axesOnly=True)
            elif self._parent and not self._parent._drawBottomAxis:
                self._createStrip(strip, spectrumDisplay._bottomGLAxis, singleStrip=True, axesOnly=True)

            # reset after creating the other strips
            self._resetStripRightBottomAxes()

        self._addTableToStory()

        # this generates the buffer to write to the file
        self._report.buildDocument()

    def _createStrip(self, strip, _parent=None, singleStrip=False, axesOnly=False):
        # point to the correct strip
        self.strip = strip
        self._parent = self.strip._CcpnGLWidget if _parent is None else _parent

        self._buildPage(singleStrip=singleStrip, strip=strip, axesOnly=axesOnly)
        self._setStripAxes()
        self._modifyScaling()
        self._buildStrip(axesOnly=axesOnly)
        self._resetStripAxes()

        # self._addDrawingToStory()
        report = self.report(self.pixWidth, self.pixHeight, self._mainPlot)
        self.stripReports.append(report)
        self.stripWidths.append(report.width)
        self.stripHeights.append(report.height)

    def _createSpacerStrip(self):
        """Create a spacer strip
        """
        rows = (self.params[GLSTRIPDIRECTION] == 'Y')
        if rows:
            h = self.pixHeight
            spacer = Drawing(self.stripSpacing, h)
            self._makeStripSpacingBox(spacer, self.stripSpacing, h)
        else:
            w = self.pixWidth
            spacer = Drawing(w, self.stripSpacing)
            self._makeStripSpacingBox(spacer, w, self.stripSpacing)

        self._mainPlots.append(spacer)

        if self.params[GLSTRIPDIRECTION] == 'Y':
            report = self.report(self.stripSpacing, self.pixHeight, spacer)
        else:
            report = self.report(self.pixWidth, self.stripSpacing, spacer)
        self.stripReports.append(report)
        self.stripWidths.append(report.width)
        self.stripHeights.append(report.height)

    def _importFonts(self):
        from ccpn.framework.PathsAndUrls import fontsPath
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLGlobal import GLFONT_SUBSTITUTE

        # load all system fonts to find matches with OpenGl fonts
        for glFonts in self._parent.globalGL.fonts.values():
            pdfmetrics.registerFont(TTFont(glFonts.fontName, fontsPath / 'open-sans' / GLFONT_SUBSTITUTE + '.ttf'))

        self._printFont = None
        if self.params[GLUSEPRINTFONT]:
            _fontName, _fontSize = self.params[GLPRINTFONT]

            _paths = getSystemFonts().get(_fontName, [])
            for _path in _paths:
                with contextlib.suppress(Exception):
                    pdfmetrics.registerFont(TTFont(_fontName, _path))

        # set a default fontName
        self.fontName = self._parent.getSmallFont().fontName

        # load a .pfb/.afm font for the png exporter
        afmdir = fontsPath / 'open-sans'
        pfbdir = fontsPath / 'open-sans'
        afmFile = afmdir / 'OpenSans-Regular.afm'
        pfbFile = pfbdir / 'OpenSans-Regular.pfb'

        justFace = pdfmetrics.EmbeddedType1Face(afmFile, pfbFile)
        faceName = 'OpenSans'  # pulled from AFM file
        pdfmetrics.registerTypeFace(justFace)

        # this needs to have a space
        justFont = pdfmetrics.Font('Open Sans', faceName, 'WinAnsiEncoding')
        pdfmetrics.registerFont(justFont)

    def _buildPageDimensions(self, strips, ratios):
        """Calculate the scaling required for the whole page
        """
        st = strips[0]._CcpnGLWidget
        xr, yr = ratios
        if self.params[GLSTRIPDIRECTION] == 'Y':
            fh = st.height() * yr[st.strip.id]
            _widths = [st._CcpnGLWidget.width() * xr[st.id] for st in strips]
            if self.numStrips > 1:
                _widths.append((self.numStrips - 1) * self.params[GLSTRIPPADDING])
            if st and not st._drawRightAxis:
                _widths.append(strips[0].spectrumDisplay._rightGLAxis.width() * xr['axis'])
            fw = sum(_widths)
        else:
            fw = st.width() * xr[st.strip.id]
            _heights = [st._CcpnGLWidget.height() * yr[st.id] for st in strips]
            if self.numStrips > 1:
                _heights.append((self.numStrips - 1) * self.params[GLSTRIPPADDING])
            if st and not st._drawBottomAxis:
                _heights.append(self.strip.spectrumDisplay._bottomGLAxis.height() * yr['axis'])
            fh = sum(_heights)

        # dimensions of the strip list - should be ints
        _parentH = self.fh = fh
        _parentW = self.fw = fw

        _doc = self._report.doc
        self.docWidth = docWidth = _doc.width  # _doc.pagesize[0]  # - FRAMEPADDING
        self.docHeight = docHeight = _doc.height  # pagesize[1]  # - (2 * FRAMEPADDING)

        # translate to size of drawing Flowable
        self.modRatio = 1.0

        _pageRatio = docHeight / docWidth
        _stripRatio = fh / fw

        if _stripRatio > _pageRatio:
            # strips are taller than relative page - fit to height
            _scale = fh / docHeight
            fh = docHeight
            fw /= _scale
        else:
            _scale = fw / docWidth
            # fw = docWidth
            fh /= _scale

        self.modRatio = 1.0
        self._displayScale = fh / _parentH
        self._fontScale = self._pngScale / self._parent.viewports.devicePixelRatio

        # read the strip spacing from the params
        self._stripSpacing = self.params[GLSTRIPPADDING]  #* self._displayScale

    def _buildPage(self, singleStrip=True, strip=None, axesOnly=False):
        """Build the main sections of the pdf file from a drawing object
        and add the drawing object to a reportlab document
        """
        # NOTE:ED - dpi = 72  # drawing object and documents are hard-coded to this

        # keep aspect ratio of the original screen
        self.margin = 2.0 * cm

        self.main = True
        self.rAxis = self._parent._drawRightAxis
        self.bAxis = self._parent._drawBottomAxis

        # get the method for retrieving the viewport sizes
        getView = self._parent.viewports.getViewportFromWH

        _parentH = self._parent.h
        _parentW = self._parent.w

        # more scale here :|
        if axesOnly:
            if (sc := self._updateScalesX.get('axis', 0.0)) > 0.01:
                # hard-limit so there are no division-by-zeroes
                _parentW = int(_parentW * sc)
            if (sc := self._updateScalesY.get('axis', 0.0)) > 0.01:
                _parentH = int(_parentH * sc)
        else:
            if (sc := self._updateScalesX.get(strip.id, 0.0)) > 0.01:
                # hard-limit so there are no division-by-zeroes
                _parentW = int(_parentW * sc)
            if (sc := self._updateScalesY.get(strip.id, 0.0)) > 0.01:
                _parentH = int(_parentH * sc)

        if not self.rAxis and not self.bAxis:
            # no axes visible
            self.mainView = viewportDimensions(*getView(FULLVIEW, _parentW, _parentH))
            self.rAxisMarkView = viewportDimensions(*getView(BLANKVIEW, _parentW, _parentH))
            self.rAxisBarView = viewportDimensions(*getView(BLANKVIEW, _parentW, _parentH))
            self.bAxisMarkView = viewportDimensions(*getView(BLANKVIEW, _parentW, _parentH))
            self.bAxisBarView = viewportDimensions(*getView(BLANKVIEW, _parentW, _parentH))

        elif self.rAxis and not self.bAxis:
            # right axis visible
            self.mainView = viewportDimensions(*getView(MAINVIEWFULLHEIGHT, _parentW, _parentH))
            if self._parent._fullHeightRightAxis:
                self.rAxisMarkView = viewportDimensions(*getView(FULLRIGHTAXIS, _parentW, _parentH))
                self.rAxisBarView = viewportDimensions(*getView(FULLRIGHTAXISBAR, _parentW, _parentH))
            else:
                self.rAxisMarkView = viewportDimensions(*getView(RIGHTAXIS, _parentW, _parentH))
                self.rAxisBarView = viewportDimensions(*getView(RIGHTAXISBAR, _parentW, _parentH))
            self.bAxisMarkView = viewportDimensions(*getView(BLANKVIEW, _parentW, _parentH))
            self.bAxisBarView = viewportDimensions(*getView(BLANKVIEW, _parentW, _parentH))

        elif not self.rAxis and self.bAxis:
            # bottom axis visible
            self.mainView = viewportDimensions(*getView(MAINVIEWFULLWIDTH, _parentW, _parentH))
            self.rAxisMarkView = viewportDimensions(*getView(BLANKVIEW, _parentW, _parentH))
            self.rAxisBarView = viewportDimensions(*getView(BLANKVIEW, _parentW, _parentH))
            if self._parent._fullWidthBottomAxis:
                self.bAxisMarkView = viewportDimensions(*getView(FULLBOTTOMAXIS, _parentW, _parentH))
                self.bAxisBarView = viewportDimensions(*getView(FULLBOTTOMAXISBAR, _parentW, _parentH))
            else:
                self.bAxisMarkView = viewportDimensions(*getView(BOTTOMAXIS, _parentW, _parentH))
                self.bAxisBarView = viewportDimensions(*getView(BOTTOMAXISBAR, _parentW, _parentH))

        else:
            # both axes visible
            self.mainView = viewportDimensions(*getView(MAINVIEW, _parentW, _parentH))
            self.rAxisMarkView = viewportDimensions(*getView(RIGHTAXIS, _parentW, _parentH))
            self.rAxisBarView = viewportDimensions(*getView(RIGHTAXISBAR, _parentW, _parentH))
            self.bAxisMarkView = viewportDimensions(*getView(BOTTOMAXIS, _parentW, _parentH))
            self.bAxisBarView = viewportDimensions(*getView(BOTTOMAXISBAR, _parentW, _parentH))

        # self.pixWidth = math.floor(_parentW * self.displayScale)
        # self.pixHeight = math.floor(_parentH * self.displayScale)
        # self.fontScale = self._pngScale * self.pixWidth * self.displayScale / _parentW

        self._pixWidth = _parentW
        self._pixHeight = _parentH

        self.fontXOffset = 0.75
        self.fontYOffset = 3.0

    def _modifyScaling(self):

        # modify by the print dialog scaling factor
        _scaleMode = self.params[GLSCALINGMODE]
        _scalePercent = self.params[GLSCALINGPERCENT]
        if _scaleMode == SCALING_MODES.index(SCALE_PERCENT):

            # modify the displayScale
            self.displayScale = (self._displayScale * (_scalePercent / 100.0)) if (
                    0 <= _scalePercent <= 100) else self._displayScale
            self.pixWidth = self._pixWidth * self.displayScale
            self.pixHeight = self._pixHeight * self.displayScale
            self.fontScale = self._fontScale * self.displayScale
            self.stripSpacing = self._stripSpacing * self.displayScale

        else:
            _newScale = 1.0
            _scale = self.params[GLSCALINGBYUNITS]
            try:
                # scales are ratios
                # based on self.mainView dimensions and ranges
                if self._linkedAxisStrip:
                    _axisL = self._linkedAxisStrip._CcpnGLWidget.axisL
                    _axisR = self._linkedAxisStrip._CcpnGLWidget.axisR
                    _axisT = self._linkedAxisStrip._CcpnGLWidget.axisT
                    _axisB = self._linkedAxisStrip._CcpnGLWidget.axisB
                    _width = self._lastMainView.width
                    _height = self._lastMainView.height
                else:
                    _axisL = self._axisL
                    _axisR = self._axisR
                    _axisT = self._axisT
                    _axisB = self._axisB
                    _width = self.mainView.width
                    _height = self.mainView.height

                if _scaleMode == SCALING_MODES.index(SCALE_CM_UNIT):
                    # this is scaled to 72dpi
                    if self.params[GLSCALINGAXIS] == 0:
                        _cms = (self._displayScale * _width * 2.54) / 72.0
                        _axisScale = abs(_axisL - _axisR)
                    else:
                        _cms = (self._displayScale * _height * 2.54) / 72.0
                        _axisScale = abs(_axisT - _axisB)
                    _newScale = _scale / (_cms / _axisScale)

                elif _scaleMode == SCALING_MODES.index(SCALE_UNIT_CM):
                    if self.params[GLSCALINGAXIS] == 0:
                        _cms = (self._displayScale * _width * 2.54) / 72.0
                        _axisScale = abs(_axisL - _axisR)
                    else:
                        _cms = (self._displayScale * _height * 2.54) / 72.0
                        _axisScale = abs(_axisT - _axisB)
                    _newScale = (_axisScale / _cms) / _scale

                elif _scaleMode == SCALING_MODES.index(SCALE_INCH_UNIT):
                    if self.params[GLSCALINGAXIS] == 0:
                        _cms = (self._displayScale * _width) / 72.0
                        _axisScale = abs(_axisL - _axisR)
                    else:
                        _cms = (self._displayScale * _height) / 72.0
                        _axisScale = abs(_axisT - _axisB)
                    _newScale = _scale / (_cms / _axisScale)

                else:
                    if self.params[GLSCALINGAXIS] == 0:
                        _cms = (self._displayScale * _width) / 72.0
                        _axisScale = abs(_axisL - _axisR)
                    else:
                        _cms = (self._displayScale * _height) / 72.0
                        _axisScale = abs(_axisT - _axisB)
                    _newScale = (_axisScale / _cms) / _scale

            except Exception:
                # default to full page
                _newScale = 1.0

            finally:
                # clip to the percentage range
                _newScale = max(0.01, min(_newScale, 1.0))

                self.displayScale = self._displayScale * _newScale
                self.pixWidth = self._pixWidth * self.displayScale
                self.pixHeight = self._pixHeight * self.displayScale
                self.fontScale = self._fontScale * self.displayScale
                self.stripSpacing = self._stripSpacing * self.displayScale

    def _addBackgroundBox(self, thisPlot):
        """Make a background box to cover the plot area
        """
        gr = Group()
        # paint a background box
        ll = [0.0, 0.0,
              0.0, self.pixHeight,
              self.pixWidth, self.pixHeight,
              self.pixWidth, 0.0]

        pl = Path(fillColor=self.backgroundColour, stroke=None, strokeColor=None)
        pl.moveTo(ll[0], ll[1])
        for vv in range(2, len(ll), 2):
            pl.lineTo(ll[vv], ll[vv + 1])
        pl.closePath()
        gr.add(pl)

        # add to the drawing object
        thisPlot.add(gr, name='mainPlotBox')

        # gr = Group()
        # # paint a background box
        # ll = [0.0, 0.0,
        #       0.0, self.pixHeight,
        #       self.pixWidth, self.pixHeight,
        #       self.pixWidth, 0.0]
        # if ll:
        #     pl = Path(fillColor=self.backgroundColour, stroke=None, strokeColor=None)
        #     pl.moveTo(ll[0], ll[1])
        #     for vv in range(2, len(ll), 2):
        #         pl.lineTo(ll[vv], ll[vv + 1])
        #     pl.closePath()
        #     gr.add(pl)

        # # frame the top-left of the main plot area
        # ll = [self.displayScale * self.mainView.left, self.displayScale * self.mainView.bottom,
        #       self.displayScale * self.mainView.left, self.pixHeight,
        #       self.displayScale * self.mainView.width, self.pixHeight]
        # # ll = [self.displayScale * self.mainL, self.displayScale * self.mainB,
        # #       self.displayScale * self.mainL, self.pixHeight,
        # #       self.displayScale * self.mainW, self.pixHeight]
        #
        # if ll and self.params[GLPLOTBORDER]:
        #     pl = Path(strokeColor=self.foregroundColour, strokeWidth=0.5)
        #     pl.moveTo(ll[0], ll[1])
        #     for vv in range(2, len(ll), 2):
        #         pl.lineTo(ll[vv], ll[vv + 1])
        #     gr.add(pl)
        # # add to the drawing object
        # self._mainPlot.add(gr, name='mainPlotBox')

    def _makeStripSpacingBox(self, thisPlot, w, h):
        """Make a strip spacing box
        """
        gr = Group()
        # paint a background box
        ll = [0.0, 0.0,
              0.0, h,
              w, h,
              w, 0.0]

        # add a solid white background
        pl = Path(fillColor=self.backgroundColour, stroke=None, strokeColor=None)
        pl.moveTo(ll[0], ll[1])
        for vv in range(2, len(ll), 2):
            pl.lineTo(ll[vv], ll[vv + 1])
        pl.closePath()
        gr.add(pl)

        if self.params[GLPLOTBORDER]:
            # add the top or left border for the pdf plotting
            # need to sort out the border tolerances at some point
            pl = Path(fillColor=None,
                      strokeColor=self.foregroundColour,
                      strokeWidth=0.5 * self.baseThickness)
            if self.params[GLSTRIPDIRECTION] == 'Y':
                pl.moveTo(0, h)
                pl.lineTo(0, self.displayScale * self.mainView.bottom)
            else:
                pl.moveTo(0, h)
                pl.lineTo(self.displayScale * self.mainView.width, h)
            gr.add(pl)

        # add to the drawing object
        thisPlot.add(gr, name='stripSpacingPlot')

    def _addPlotBorders(self, thisPlot):
        """Add requires borders to the plot area
        """
        # frame the top-left of the main plot area - after other plotting
        gr = Group()
        ll = [self.displayScale * self.mainView.left, self.displayScale * self.mainView.bottom,
              self.displayScale * self.mainView.left, self.pixHeight,
              self.displayScale * self.mainView.width, self.pixHeight,
              self.displayScale * self.mainView.width, self.displayScale * self.mainView.bottom,
              self.displayScale * self.mainView.left, self.displayScale * self.mainView.bottom]

        pl = Path(fillColor=None,
                  strokeColor=self.foregroundColour if self.params[GLPLOTBORDER] else self.backgroundColour,
                  strokeWidth=0.5 * self.baseThickness)
        pl.moveTo(ll[0], ll[1])
        for vv in range(2, len(ll), 2):
            pl.lineTo(ll[vv], ll[vv + 1])
        gr.add(pl)

        thisPlot.add(gr, name='mainPlotBox')

    def _getStripUpdateRatios(self, strips):
        """Get the ratios for keeping the aspect if strips have _updateAxes set
        """
        strip = None
        self._updateScalesX = {}
        self._updateScalesY = {}
        for strip in strips:
            self._updateAxes = False
            _dd = self.params[GLSTRIPREGIONS][strip.id]
            if _dd.useRegion:
                # set the range for the display
                yt, yb = _axisT, _axisB = round(strip._CcpnGLWidget.axisT, 2), round(strip._CcpnGLWidget.axisB, 2)
                xl, xr = _axisL, _axisR = round(strip._CcpnGLWidget.axisL, 2), round(strip._CcpnGLWidget.axisR, 2)
                for ii, ddAxis in enumerate(_dd.axes):
                    # if _dd.minMaxMode == 0:
                    if ii == 0:
                        _axisL, _axisR = ddAxis['Min'], ddAxis['Max']
                    else:
                        _axisT, _axisB = ddAxis['Min'], ddAxis['Max']

                    # elif ii == 0:
                    #     _axisL, _axisR = ddAxis['Centre'] + ddAxis['Width'] / 2, ddAxis['Centre'] - ddAxis['Width'] / 2
                    # else:
                    #     _axisT, _axisB = ddAxis['Centre'] + ddAxis['Width'] / 2, ddAxis['Centre'] - ddAxis['Width'] / 2

                self._updateScalesX[strip.id] = abs((_axisR - _axisL) / (xr - xl))
                self._updateScalesY[strip.id] = abs((_axisT - _axisB) / (yt - yb))

            else:
                self._updateScalesX[strip.id] = 1.0
                self._updateScalesY[strip.id] = 1.0

        if strip:
            # repeat the last value depending on strip-direction
            if self.params[GLSTRIPDIRECTION] == 'Y':
                self._updateScalesX['axis'] = 1.0
                self._updateScalesY['axis'] = self._updateScalesY[strip.id]
            else:
                self._updateScalesX['axis'] = self._updateScalesX[strip.id]
                self._updateScalesY['axis'] = 1.0

            return (self._updateScalesX, self._updateScalesY)

    def _setStripAxes(self):

        # set the range for the display
        self._oldValues = (self.strip._CcpnGLWidget.axisL, self.strip._CcpnGLWidget.axisR,
                           self.strip._CcpnGLWidget.axisT, self.strip._CcpnGLWidget.axisB)
        self._oldSize = (self.strip._CcpnGLWidget.w, self.strip._CcpnGLWidget.h)
        try:
            self._updateAxes = False
            _dd = self.params[GLSTRIPREGIONS][self.strip.id]
            self._updateAxes = _dd.useRegion
            if self._updateAxes:
                for ii, ddAxis in enumerate(_dd.axes):

                    # if _dd.minMaxMode == 0:
                    self.strip.setAxisRegion(ii, (ddAxis['Min'], ddAxis['Max']), rescale=False, update=False)

                    if self.params[GLSTRIPDIRECTION] == 'Y':
                        if not self.rAxis:
                            self.strip.spectrumDisplay._rightGLAxis._setAxisRegion(ii, (ddAxis['Min'], ddAxis['Max']),
                                                                                   rescale=False, update=False)
                    elif not self.bAxis:
                        self.strip.spectrumDisplay._bottomGLAxis._setAxisRegion(ii, (ddAxis['Min'], ddAxis['Max']),
                                                                                rescale=False, update=False)
                    # else:
                    #     self.strip.setAxisPosition(ii, ddAxis['Centre'], rescale=False, update=False)
                    #     self.strip.setAxisWidth(ii, ddAxis['Width'], rescale=False, update=False)
                    #
                    #     if self.params[GLSTRIPDIRECTION] == 'Y':
                    #         if not self.rAxis:
                    #             self.strip.spectrumDisplay._rightGLAxis._setAxisPosition(ii, ddAxis['Centre'], rescale=False, update=False)
                    #             self.strip.spectrumDisplay._rightGLAxis._setAxisWidth(ii, ddAxis['Width'], rescale=False, update=False)
                    #     elif not self.bAxis:
                    #         self.strip.spectrumDisplay._bottomGLAxis._setAxisPosition(ii, ddAxis['Centre'], rescale=False, update=False)
                    #         self.strip.spectrumDisplay._bottomGLAxis._setAxisWidth(ii, ddAxis['Width'], rescale=False, update=False)

                self._setAxisValues()

                # self.strip._CcpnGLWidget.w *= (self._updateScalesX.get(self.strip.id, 1.0) / self._updateScalesY.get(self.strip.id, 1.0))
                self.strip._CcpnGLWidget.w *= self._updateScalesX.get(self.strip.id, 1.0)
                self.strip._CcpnGLWidget.h *= self._updateScalesY.get(self.strip.id, 1.0)

                self._rebuildGL(self.strip._CcpnGLWidget)
                if self.params[GLSTRIPDIRECTION] == 'Y':
                    if not self.rAxis:
                        self._rebuildGL(self.strip.spectrumDisplay._rightGLAxis)
                elif not self.bAxis:
                    self._rebuildGL(self.strip.spectrumDisplay._bottomGLAxis)

            else:
                self._setAxisValues()

        except Exception as es:
            getLogger().debug(f'_setStripAxes: problem creating page {es}')

    @staticmethod
    def _rebuildGL(GLWidget):
        """Rebuild the GL-widget
        """
        GLWidget._rescaleAllAxes(update=False)
        GLWidget._buildGL()
        GLWidget.buildAxisLabels(refresh=True)

    def _setAxisValues(self):
        """Set the axis values from the strip
        """
        self._axisL = self.strip._CcpnGLWidget.axisL
        self._axisR = self.strip._CcpnGLWidget.axisR
        self._axisT = self.strip._CcpnGLWidget.axisT
        self._axisB = self.strip._CcpnGLWidget.axisB

    def _buildStrip(self, axesOnly=False):
        # create an object that can be added to a report
        self._mainPlot = Drawing(self.pixWidth, self.pixHeight)

        # keep a history of the _mainPlot objects to build the png/ps/svg files
        self._mainPlots.append(self._mainPlot)

        self._addBackgroundBox(self._mainPlot)

        # get the list of required spectra
        self._ordering = self.strip.getSpectrumViews()
        self._phasingOn = self.strip._isPhasingOn
        self._is1D = self._parent.spectrumDisplay.is1D
        self._stackingMode = self._parent._stackingMode

        # print the grid objects
        if self.params[GLGRIDLINES]: self._addGridLines()

        if not axesOnly:
            if self.params[GLDIAGONALLINE]: self._addDiagonalLine()
            if self.params[GLDIAGONALSIDEBANDS]: self._addDiagonalSideBands()

            # check parameters to decide what to print

            # if not self._parent.spectrumDisplay.is1D or \
            #         not self._parent.spectrumDisplay.phasingFrame.isVisible() or \
            #         self.params[GLSHOWSPECTRAONPHASE]:
            if (not self._is1D or
                    not self._phasingOn or
                    self.params[GLSHOWSPECTRAONPHASE]):

                if self.params[GLSPECTRUMCONTOURS]: self._addSpectrumContours()
                if self.params[GLSPECTRUMBORDERS]: self._addSpectrumBoundaries()

            if not self._stackingMode:
                if not (self._is1D and self._phasingOn):
                    if self.params[GLINTEGRALSYMBOLS]:
                        self._addIntegralAreas()
                        self._addIntegralLines()
                if self.params[GLPEAKARROWS]: self._addPeakArrows()
                if self.params[GLMULTIPLETARROWS]: self._addMultipletArrows()
                if self.params[GLPEAKSYMBOLS]: self._addPeakSymbols()
                if self.params[GLMULTIPLETSYMBOLS]: self._addMultipletSymbols()
                if self.params[GLMARKLINES]: self._addMarkLines()
                if not (self._is1D and self._phasingOn):
                    if self.params[GLREGIONS]: self._addRegions()
                if self.params[GLPEAKLABELS]: self._addPeakLabels()
                if not (self._is1D and self._phasingOn):
                    if self.params[GLINTEGRALLABELS]: self._addIntegralLabels()
                if self.params[GLMULTIPLETLABELS]: self._addMultipletLabels()
                if self.params[GLMARKLABELS]: self._addMarkLabels()
            else:
                if self.params[GLPEAKARROWS]: self._addPeakArrows()
                if self.params[GLMULTIPLETARROWS]: self._addMultipletArrows()
                if self.params[GLPEAKSYMBOLS]: self._addPeakSymbols()
                if self.params[GLMULTIPLETSYMBOLS]: self._addMultipletSymbols()
                if self.params[GLPEAKLABELS]: self._addPeakLabels()
                if self.params[GLMULTIPLETLABELS]: self._addMultipletLabels()
                if self.params[GLSPECTRUMLABELS]: self._addSpectrumLabels()

            if self.params[GLTRACES]: self._addTraces()
            if self._selectedStrip == self.strip and self.params[GLACTIVETRACES]:
                self._addLiveTraces()
            if not self._parent._stackingMode and self.params[GLOTHERLINES]:
                self._addInfiniteLines()
            if self.params[GLSTRIPLABELLING]: self._addOverlayText()

            self.strip.printer.emit(self, self.strip)

            # frame the top-left of the main plot area - after other plotting
            self._addPlotBorders(self._mainPlot)

            # add the axis labels which requires a mask to clean the edges
            self._addAxisMask()

        self._addGridTickMarks()

        if not axesOnly and self.params[GLCURSORS]:
            self._addCursors()
            if self._selectedStrip == self.strip:
                self._addCursorText()

        if self.params[GLAXISLABELS] or self.params[GLAXISUNITS] or self.params[GLAXISTITLES]: self._addGridLabels()

    def _resetStripAxes(self):
        try:
            if self._updateAxes:
                # reset the strip to the original values
                self.strip._CcpnGLWidget.axisL, self.strip._CcpnGLWidget.axisR, self.strip._CcpnGLWidget.axisT, self.strip._CcpnGLWidget.axisB = self._oldValues
                self.strip._CcpnGLWidget.w, self.strip._CcpnGLWidget.h = self._oldSize

                self.strip._CcpnGLWidget._rescaleAllZoom()
                self.strip._CcpnGLWidget._buildGL()
                self.strip._CcpnGLWidget.buildAxisLabels()
        except Exception:
            getLogger().debug('There was an issue resetting the strip')

    def _resetStripRightBottomAxes(self):
        with contextlib.suppress(Exception):
            if self.params[GLSTRIPDIRECTION] == 'Y':
                if self._parent and self._parent._drawRightAxis:
                    # reset the strip to the original values
                    sdr = self.strip.spectrumDisplay._rightGLAxis
                    sdr.axisL, sdr.axisR, sdr.axisT, sdr.axisB = self._oldValues
                    sdr._rescaleAllZoom()
                    sdr._buildGL()
                    sdr.buildAxisLabels(refresh=True)
            elif self._parent and self._parent._drawBottomAxis:
                # reset the strip to the original values
                sdb = self.strip.spectrumDisplay._bottomGLAxis
                sdb.axisL, sdb.axisR, sdb.axisT, sdb.axisB = self._oldValues
                sdb._rescaleAllZoom()
                sdb._buildGL()
                sdb.buildAxisLabels(refresh=True)

    def _addGridLines(self):
        """
        Add grid lines to the main drawing area.
        """
        if self._parent._gridVisible and self._parent.gridList[0]:
            colourGroups = OrderedDict()
            self._appendIndexLineGroup(indArray=self._parent.gridList[0],
                                       colourGroups=colourGroups,
                                       plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
                                                PLOTBOTTOM: self.displayScale * self.mainView.bottom,
                                                PLOTWIDTH : self.displayScale * self.mainView.width,
                                                PLOTHEIGHT: self.displayScale * self.mainView.height},
                                       name='grid',
                                       ratioLine=True,
                                       lineWidth=0.5 * self.baseThickness,
                                       vStep=2)
            self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='grid')

    def _addDiagonalSideBands(self):
        """
        Add the diagonal sideBand lines to the main drawing area.
        """
        if self._parent.diagonalSideBandsGLList and self._parent._matchingIsotopeCodes:
            colourGroups = OrderedDict()
            self._appendIndexLineGroup(indArray=self._parent.diagonalSideBandsGLList,
                                       colourGroups=colourGroups,
                                       plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
                                                PLOTBOTTOM: self.displayScale * self.mainView.bottom,
                                                PLOTWIDTH : self.displayScale * self.mainView.width,
                                                PLOTHEIGHT: self.displayScale * self.mainView.height},
                                       name='diagonal',
                                       ratioLine=True,
                                       lineWidth=0.5 * self.baseThickness,
                                       vStep=2)
            self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='diagonal')

    def _addDiagonalLine(self):
        """
        Add the diagonal line to the main drawing area.
        """
        if self._parent.diagonalGLList and self._parent._matchingIsotopeCodes:
            colourGroups = OrderedDict()
            self._appendIndexLineGroup(indArray=self._parent.diagonalGLList,
                                       colourGroups=colourGroups,
                                       plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
                                                PLOTBOTTOM: self.displayScale * self.mainView.bottom,
                                                PLOTWIDTH : self.displayScale * self.mainView.width,
                                                PLOTHEIGHT: self.displayScale * self.mainView.height},
                                       name='diagonal',
                                       ratioLine=True,
                                       lineWidth=0.5 * self.baseThickness,
                                       vStep=2)
            self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='diagonal')

    def _addCursors(self):
        """
        Add cursors/double cursor to the main drawing area.
        """
        if not (self._parent._glCursorQueue and self._parent._glCursorHead < len(self._parent._glCursorQueue)):
            return

        if _drawList := self._parent._glCursorQueue[self._parent._glCursorHead]:
            colourGroups = OrderedDict()
            self._appendIndexLineGroup(indArray=_drawList,
                                       colourGroups=colourGroups,
                                       plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
                                                PLOTBOTTOM: self.displayScale * self.mainView.bottom,
                                                PLOTWIDTH : self.displayScale * self.mainView.width,
                                                PLOTHEIGHT: self.displayScale * self.mainView.height},
                                       name='cursors',
                                       ratioLine=True,
                                       lineWidth=0.5 * self.baseThickness,
                                       vStep=2)
            self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='cursors')

    def _addCursorText(self):
        """
        Add the cursor text.
        """
        colourGroups = OrderedDict()

        if not self._parent.mouseString:
            return

        drawString = self._parent.mouseString

        if drawString.vertices is None or drawString.vertices.size == 0:
            return

        col = drawString.colors[0]
        if not isinstance(col, Iterable):
            col = drawString.colors[:4]
        colour = colors.Color(*col[:3], alpha=alphaClip(col[3]))
        colourPath = f'cursorText{colour.red}{colour.green}{colour.blue}{colour.alpha}'

        newLine = self._scaleRatioToWindow([drawString.attribs[0] + (self.fontXOffset * self._parent.deltaX),
                                            drawString.attribs[1] + (self.fontYOffset * self._parent.deltaY)])
        if self.pointVisible(self._parent, newLine,
                             x=self.displayScale * self.mainView.left,
                             y=self.displayScale * self.mainView.bottom,
                             width=self.displayScale * self.mainView.width,
                             height=self.displayScale * self.mainView.height):
            if colourPath not in colourGroups:
                colourGroups[colourPath] = Group()

            textGroup = drawString.text.split('\n')
            textLine = len(textGroup) - 1
            for text in textGroup:
                self._addString(colourGroups, colourPath,
                                drawString,
                                (newLine[0], newLine[1]),
                                colour,
                                text=text,
                                offset=textLine
                                )
                textLine -= 1

        for colourGroup in colourGroups.values():
            self._mainPlot.add(colourGroup)

    def _addSpectrumViewManager(self, groupName):
        """
        Add the spectrum objects to the main drawing area.
        Generator function to iterate over all the aliasing regions of all
        spectrumViews in the strip and execute user code each iteration

        e.g.

        >>> for data in self._addSpectrumViewManager('spectrumContours'):
        >>>     print(data.spectrum)
        """


        # simple class to export variables from the generator function
        @dataclass
        class _editValues:
            colourGroups = OrderedDict()
            GLObject = None
            specSettings = None
            spectrum = None
            dimensionCount = 0
            matrix = None
            matrixSymbols = None
            spectrumView = None
            x = 0
            y = 0
            width = 0
            height = 0
            index = 0
            alias = None


        data = _editValues()
        # set the display parameters
        data.x = _x = self.displayScale * self.mainView.left
        data.y = _y = self.displayScale * self.mainView.bottom
        data.width = _width = self.displayScale * self.mainView.width
        data.height = _height = self.displayScale * self.mainView.height
        data.index = 0

        for spectrumView in self._ordering:

            if spectrumView.isDeleted:
                continue

            if spectrumView.spectrum.pid in self.params[GLSELECTEDPIDS]:

                # get the contour list
                data.GLObject = self._parent._contourList[spectrumView] \
                    if spectrumView in self._parent._contourList else None

                if spectrumView in self._parent._spectrumSettings.keys():

                    # get the spectrum settings for the spectrumView
                    data.specSettings = specSettings = self._parent._spectrumSettings[spectrumView]
                    data.spectrumView = spectrumView
                    data.spectrum = spectrumView.spectrum
                    data.dimensionCount = spectrumView.spectrum.dimensionCount

                    if spectrumView.spectrum.dimensionCount > 1:
                        # draw nD spectra
                        fxMax, fyMax = specSettings.maxSpectrumFrequency
                        dxAF, dyAF = specSettings.spectralWidth
                        xScale, yScale = specSettings.scale
                        alias = specSettings.aliasingIndex
                        folding = specSettings.foldingMode

                        for ii, jj in product(range(alias[0][0], alias[0][1] + 1),
                                              range(alias[1][0], alias[1][1] + 1)):
                            foldX = foldY = 1.0
                            foldXOffset = foldYOffset = 0
                            if folding[0] == 'mirror':
                                foldX = pow(-1, ii)
                                foldXOffset = -dxAF if foldX < 0 else 0
                            if folding[1] == 'mirror':
                                foldY = pow(-1, jj)
                                foldYOffset = -dyAF if foldY < 0 else 0

                            # build the spectrum transformation matrix
                            mm = QtGui.QMatrix4x4()
                            mm.translate(fxMax + (ii * dxAF) + foldXOffset,
                                         fyMax + (jj * dyAF) + foldYOffset)
                            mm.scale(xScale * foldX, yScale * foldY)
                            data.matrix = mm
                            data.matrixSymbols = mm
                            data.alias = getAliasSetting(ii, jj)

                            yield data  # pass object

                            data.index += 1

                    else:
                        # draw 1D spectra
                        fxMax, fyMax = specSettings.maxSpectrumFrequency
                        dxAF, dyAF = specSettings.spectralWidth
                        xScale, yScale = specSettings.scale
                        alias = specSettings.aliasingIndex
                        folding = specSettings.foldingMode
                        stackX, stackY = specSettings.stackedMatrixOffset
                        dimX, _ = specSettings.dimensionIndices

                        for ii, jj in product(range(alias[0][0], alias[0][1] + 1),
                                              range(alias[1][0], alias[1][1] + 1)):
                            foldX = 1.0
                            foldXOffsetSym = foldXOffset = 0
                            if folding[0] == 'mirror':
                                foldX = pow(-1, ii)
                                foldXOffset = (2 * fxMax - dxAF) if foldX < 0 else 0
                                foldXOffsetSym = -dxAF if foldX < 0 else 0
                            foldY = 1.0
                            foldYOffsetSym = foldYOffset = 0
                            if folding[1] == 'mirror':
                                foldY = pow(-1, jj)
                                foldYOffset = (2 * fyMax - dyAF) if foldY < 0 else 0
                                foldYOffsetSym = -dyAF if foldY < 0 else 0

                            # build the spectrum transformation matrix
                            mm = QtGui.QMatrix4x4()
                            if self._parent._stackingMode:
                                mm.translate(stackX, stackY)
                            mmSym = QtGui.QMatrix4x4()
                            if self._parent._stackingMode:
                                mmSym.translate(stackX, stackY)

                            if dimX:  # quick way to check if 1D is flipped
                                # build the 1D spectrum transformation matrices
                                mm.translate(0, (jj * dyAF) + foldYOffset)
                                mm.scale(1.0, foldY, 1.0)
                                mmSym.translate(0, fyMax + (jj * dyAF) + foldYOffsetSym)
                                mmSym.scale(1.0, yScale * foldY, 1.0)
                            else:
                                mm.translate((ii * dxAF) + foldXOffset, 0)
                                mm.scale(foldX, 1.0, 1.0)
                                mmSym.translate(fxMax + (ii * dxAF) + foldXOffsetSym, 0)
                                mmSym.scale(xScale * foldX, 1.0, 1.0)

                            data.matrix = mm
                            data.matrixSymbols = mmSym
                            data.alias = getAliasSetting(ii, jj)

                            yield data  # pass object back to the calling method

                            data.index += 1

        if data.colourGroups:
            self._appendGroup(drawing=self._mainPlot, colourGroups=data.colourGroups, name=groupName)

    @staticmethod
    def addLine(colourPath, line):
        """Append a line to the colourGoup if not too close
        """
        # NOTE:ED - would be quicker if done on the whole list at the end
        rnd = np.append(np.round(line, 2).reshape([len(line) // 2, 2]), [[None, None]], axis=0)
        ll = [pp for p0, p1 in zip(rnd, rnd[1:]) if not np.array_equal(p0, p1) for pp in p0]
        if len(ll) > 2:
            colourPath.append(ll)

    def _addSpectrumContours(self):
        """
        Add the spectrum contours to the main drawing area.
        """
        for data in self._addSpectrumViewManager('spectrumContours'):
            if data.dimensionCount > 1:
                for ppInd in range(0, len(data.GLObject.indices), 2):
                    ppInd0 = int(data.GLObject.indices[ppInd])
                    ppInd1 = int(data.GLObject.indices[ppInd + 1])

                    vectStart = QtGui.QVector4D(data.GLObject.vertices[ppInd0 * 2],
                                                data.GLObject.vertices[ppInd0 * 2 + 1], 0.0, 1.0)
                    vectStart = data.matrix * vectStart
                    vectEnd = QtGui.QVector4D(data.GLObject.vertices[ppInd1 * 2],
                                              data.GLObject.vertices[ppInd1 * 2 + 1], 0.0, 1.0)
                    vectEnd = data.matrix * vectEnd

                    newLine = [vectStart[0], vectStart[1], vectEnd[0], vectEnd[1]]

                    colour = colors.Color(*data.GLObject.colors[ppInd0 * 4:ppInd0 * 4 + 3],
                                          alpha=alphaClip(data.GLObject.colors[ppInd0 * 4 + 3]))
                    colourPath = f'spectrumContours{data.spectrumView.pid}{data.index}' \
                                 f'{colour.red}{colour.green}{colour.blue}{colour.alpha}'

                    if newLine := self.lineVisible(self._parent, newLine, x=data.x, y=data.y, width=data.width,
                                                   height=data.height):
                        if colourPath not in data.colourGroups:
                            data.colourGroups[colourPath] = {PDFLINES      : [],
                                                             PDFSTROKEWIDTH: 0.5 * self.baseThickness * self.contourThickness,
                                                             PDFSTROKECOLOR: colour, PDFSTROKELINECAP: 1}
                        # data.colourGroups[colourPath][PDFLINES].append(newLine)
                        self.addLine(data.colourGroups[colourPath][PDFLINES], newLine)

            else:
                # drawVertexColor
                self._appendVertexLineGroup(indArray=data.GLObject,
                                            colourGroups=data.colourGroups,
                                            plotDim={PLOTLEFT  : data.x,
                                                     PLOTBOTTOM: data.y,
                                                     PLOTWIDTH : data.width,
                                                     PLOTHEIGHT: data.height},
                                            name=f'spectrumContours{data.spectrumView.pid}{data.index}',
                                            mat=data.matrix,
                                            lineWidth=0.5 * self.baseThickness * self.contourThickness)

    def _addSpectrumBoundaries(self):
        """
        Add the spectrum boundaries to the main drawing area.
        """
        colourGroups = OrderedDict()
        self._appendIndexLineGroup(indArray=self._parent.boundingBoxes,
                                   colourGroups=colourGroups,
                                   plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
                                            PLOTBOTTOM: self.displayScale * self.mainView.bottom,
                                            PLOTWIDTH : self.displayScale * self.mainView.width,
                                            PLOTHEIGHT: self.displayScale * self.mainView.height},
                                   name='boundary',
                                   lineWidth=0.5 * self.baseThickness,
                                   vStep=2)
        self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='boundaries')

    def _addPeakSymbols(self):
        """
        Add the peak symbols to the main drawing area.
        """
        _symbols = self._parent._GLPeaks._GLSymbols

        # iterate through the visible regions with the viewManager
        for data in self._addSpectrumViewManager('peakSymbols'):
            attribList = data.spectrumView.peakListViews
            validListViews = [_symbols[pp] for pp in attribList
                              if pp in _symbols.keys()
                              and pp.isDisplayed
                              and data.spectrumView.isDisplayed
                              and pp.peakList.pid in self.params[GLSELECTEDPIDS]
                              ]

            for GLObject in validListViews:
                self._appendIndexLineGroup(indArray=GLObject,
                                           colourGroups=data.colourGroups,
                                           plotDim={PLOTLEFT  : data.x,
                                                    PLOTBOTTOM: data.y,
                                                    PLOTWIDTH : data.width,
                                                    PLOTHEIGHT: data.height},
                                           name=f'spectrumViewpeakSymbols{data.index}{data.spectrumView.pid}',
                                           mat=data.matrixSymbols,
                                           fillMode=None,
                                           splitGroups=False,
                                           lineWidth=0.5 * self.baseThickness * self.symbolThickness,
                                           alias=data.alias,
                                           vStep=4)

    def _addPeakArrows(self):
        """
        Add the peak arrows to the main drawing area.
        """
        _arrows = self._parent._GLPeaks._GLArrows

        # iterate through the visible regions with the viewManager
        for data in self._addSpectrumViewManager('peakArrows'):
            attribList = data.spectrumView.peakListViews
            validListViews = [_arrows[pp] for pp in attribList
                              if pp in _arrows.keys()
                              and pp.isDisplayed
                              and data.spectrumView.isDisplayed
                              and pp.peakList.pid in self.params[GLSELECTEDPIDS]
                              ]

            for GLObject in validListViews:
                self._appendIndexLineGroup(indArray=GLObject,
                                           colourGroups=data.colourGroups,
                                           plotDim={PLOTLEFT  : data.x,
                                                    PLOTBOTTOM: data.y,
                                                    PLOTWIDTH : data.width,
                                                    PLOTHEIGHT: data.height},
                                           name=f'spectrumViewpeakArrows{data.index}{data.spectrumView.pid}',
                                           mat=data.matrixSymbols,
                                           fillMode=None,
                                           splitGroups=False,
                                           lineWidth=0.5 * self.baseThickness,
                                           alias=data.alias,
                                           vStep=4)

    def _addMultipletSymbols(self):
        """
        Add the multiplet symbols to the main drawing area.
        """
        _symbols = self._parent._GLMultiplets._GLSymbols

        # iterate through the visible regions with the viewManager
        for data in self._addSpectrumViewManager('multipletSymbols'):
            attribList = data.spectrumView.multipletListViews
            validListViews = [_symbols[pp] for pp in attribList
                              if pp in _symbols.keys()
                              and pp.isDisplayed
                              and data.spectrumView.isDisplayed
                              and pp.multipletList.pid in self.params[GLSELECTEDPIDS]]

            for GLObject in validListViews:
                self._appendIndexLineGroup(indArray=GLObject,
                                           colourGroups=data.colourGroups,
                                           plotDim={PLOTLEFT  : data.x,
                                                    PLOTBOTTOM: data.y,
                                                    PLOTWIDTH : data.width,
                                                    PLOTHEIGHT: data.height},
                                           name=f'spectrumViewmultipletSymbols{data.index}{data.spectrumView.pid}',
                                           mat=data.matrixSymbols,
                                           fillMode=None,
                                           splitGroups=False,
                                           lineWidth=0.5 * self.baseThickness * self.symbolThickness,
                                           alias=data.alias,
                                           vStep=4)

    def _addMultipletArrows(self):
        """
        Add the multiplet arrows to the main drawing area.
        """
        _arrows = self._parent._GLMultiplets._GLArrows

        # iterate through the visible regions with the viewManager
        for data in self._addSpectrumViewManager('multipletArrows'):
            attribList = data.spectrumView.multipletListViews
            validListViews = [_arrows[pp] for pp in attribList
                              if pp in _arrows.keys()
                              and pp.isDisplayed
                              and data.spectrumView.isDisplayed
                              and pp.multipletList.pid in self.params[GLSELECTEDPIDS]
                              ]

            for GLObject in validListViews:
                self._appendIndexLineGroup(indArray=GLObject,
                                           colourGroups=data.colourGroups,
                                           plotDim={PLOTLEFT  : data.x,
                                                    PLOTBOTTOM: data.y,
                                                    PLOTWIDTH : data.width,
                                                    PLOTHEIGHT: data.height},
                                           name=f'spectrumViewmultipletArrows{data.index}{data.spectrumView.pid}',
                                           mat=data.matrixSymbols,
                                           fillMode=None,
                                           splitGroups=False,
                                           lineWidth=0.5 * self.baseThickness,
                                           alias=data.alias,
                                           vStep=4)

    def _addMarkLines(self):
        """
        Add the mark lines to the main drawing area.
        """
        colourGroups = OrderedDict()
        self._appendIndexLineGroup(indArray=self._parent._marksList,
                                   colourGroups=colourGroups,
                                   plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
                                            PLOTBOTTOM: self.displayScale * self.mainView.bottom,
                                            PLOTWIDTH : self.displayScale * self.mainView.width,
                                            PLOTHEIGHT: self.displayScale * self.mainView.height},
                                   name='marks',
                                   lineWidth=0.5 * self.baseThickness,
                                   vStep=2)
        self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='marks')

    def _addIntegralLines(self):
        """
        Add the integral lines to the main drawing area.
        """
        colourGroups = OrderedDict()
        self._appendIndexLineGroupFill(indArray=self._parent._GLIntegrals._GLSymbols,
                                       listView='integralList',
                                       colourGroups=colourGroups,
                                       plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
                                                PLOTBOTTOM: self.displayScale * self.mainView.bottom,
                                                PLOTWIDTH : self.displayScale * self.mainView.width,
                                                PLOTHEIGHT: self.displayScale * self.mainView.height},
                                       name='IntegralListsFill',
                                       fillMode=GL.GL_FILL,
                                       splitGroups=True,
                                       lineWidth=0.5 * self.baseThickness,
                                       vStep=2)
        self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='integralLists')

    def _addIntegralAreas(self):
        """
        Add the integral filled areas to the main drawing area.
        """
        colourGroups = OrderedDict()
        for spectrumView in self._ordering:
            if spectrumView.isDeleted:
                continue

            validIntegralListViews = [pp for pp in spectrumView.integralListViews
                                      if pp.isDisplayed
                                      and spectrumView.isDisplayed
                                      and pp in self._parent._GLIntegrals._GLSymbols.keys()
                                      and pp.integralList.pid in self.params[GLSELECTEDPIDS]]

            _x = self.displayScale * self.mainView.left
            _y = self.displayScale * self.mainView.bottom
            _width = self.displayScale * self.mainView.width
            _height = self.displayScale * self.mainView.height

            for integralListView in validIntegralListViews:  # spectrumView.integralListViews:
                mat = None
                integralSymbols = self._parent._GLIntegrals._GLSymbols[integralListView]
                if spectrumView.spectrum.dimensionCount > 1:
                    if spectrumView in self._parent._spectrumSettings.keys():
                        # draw
                        pass

                elif spectrumView in self._parent._contourList.keys():
                    # assume that the vertexArray is a GL_LINE_STRIP
                    if spectrumView in self._parent._contourList.keys():
                        if self._parent._stackingMode:
                            mat = QtGui.QMatrix4x4(self._parent._spectrumSettings[spectrumView].stackedMatrix)
                        else:
                            mat = None

                self._appendIndexLineGroup(indArray=integralSymbols,
                                           colourGroups=colourGroups,
                                           plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
                                                    PLOTBOTTOM: self.displayScale * self.mainView.bottom,
                                                    PLOTWIDTH : self.displayScale * self.mainView.width,
                                                    PLOTHEIGHT: self.displayScale * self.mainView.height},
                                           name=f'integralSymbols{integralListView.pid}Fill',
                                           lineWidth=0.5 * self.baseThickness,
                                           fillMode=GL.GL_FILL,
                                           vStep=2)
                self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups,
                                  name=f'fillRegions{integralListView.pid}')
                self._appendIndexLineGroup(indArray=integralSymbols,
                                           colourGroups=colourGroups,
                                           plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
                                                    PLOTBOTTOM: self.displayScale * self.mainView.bottom,
                                                    PLOTWIDTH : self.displayScale * self.mainView.width,
                                                    PLOTHEIGHT: self.displayScale * self.mainView.height},
                                           name=f'integralSymbols{integralListView.pid}Line',
                                           lineWidth=0.5 * self.baseThickness,
                                           fillMode=GL.GL_LINE,
                                           vStep=2)
                self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups,
                                  name=f'lineRegions{integralListView.pid}')

                # draw the integralAreas if they exist
                for integralArea in integralSymbols._regions:
                    if hasattr(integralArea, '_integralArea'):
                        thisSpec = integralArea._integralArea
                        for vv in range(0, len(thisSpec.vertices) - 4, 2):

                            if mat is not None:
                                vectStart = QtGui.QVector4D(thisSpec.vertices[vv], thisSpec.vertices[vv + 1], 0.0, 1.0)
                                vectStart = mat * vectStart
                                vectMid = QtGui.QVector4D(thisSpec.vertices[vv + 2], thisSpec.vertices[vv + 3], 0.0,
                                                          1.0)
                                vectMid = mat * vectMid
                                vectEnd = QtGui.QVector4D(thisSpec.vertices[vv + 4], thisSpec.vertices[vv + 5], 0.0,
                                                          1.0)
                                vectEnd = mat * vectEnd

                                newLine = [vectStart[0], vectStart[1],
                                           vectMid[0], vectMid[1],
                                           vectEnd[0], vectEnd[1]]
                            else:
                                newLine = list(thisSpec.vertices[vv:vv + 6])

                            colour = colors.Color(*thisSpec.colors[vv * 2:vv * 2 + 3],
                                                  alpha=alphaClip(thisSpec.colors[vv * 2 + 3]))
                            colourPath = f'spectrumViewIntegralFill{spectrumView.pid}' \
                                         f'{colour.red}{colour.green}{colour.blue}{colour.alpha}'

                            if newLine := self.lineVisible(self._parent, newLine, x=_x, y=_y, width=_width,
                                                           height=_height):
                                if colourPath not in colourGroups:
                                    colourGroups[colourPath] = {PDFLINES      : [], PDFFILLCOLOR: colour,
                                                                # PDFSTROKE: None,
                                                                PDFSTROKEWIDTH: 0.5,
                                                                PDFSTROKECOLOR: colour,
                                                                }
                                self.addLine(colourGroups[colourPath][PDFLINES], newLine)

        self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='integralListsAreaFill')

    def _addRegions(self):
        """
        Add the regions to the main drawing area.
        """
        colourGroups = OrderedDict()
        self._appendIndexLineGroup(indArray=self._parent._externalRegions,
                                   colourGroups=colourGroups,
                                   plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
                                            PLOTBOTTOM: self.displayScale * self.mainView.bottom,
                                            PLOTWIDTH : self.displayScale * self.mainView.width,
                                            PLOTHEIGHT: self.displayScale * self.mainView.height},
                                   name='regions',
                                   lineWidth=0.5 * self.baseThickness,
                                   vStep=2)
        self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='regions')

    def _addPeakLabels(self):
        """
        Add the peak labels to the main drawing area.
        """
        colourGroups = OrderedDict()

        # iterate through the visible regions with the viewManager
        for data in self._addSpectrumViewManager('peakLabels'):

            validPeakListViews = [pp for pp in data.spectrumView.peakListViews
                                  if pp.isDisplayed
                                  and data.spectrumView.isDisplayed
                                  and pp in self._parent._GLPeaks._GLLabels.keys()
                                  and pp.peakList.pid in self.params[GLSELECTEDPIDS]]

            for peakListView in validPeakListViews:  # spectrumView.peakListViews:
                for drawString in self._parent._GLPeaks._GLLabels[peakListView].stringList:

                    if drawString.vertices is None or drawString.vertices.size == 0:
                        continue

                    col = drawString.colors[0]
                    if not isinstance(col, Iterable):
                        col = drawString.colors[:4]
                    _alias = 1.0
                    if data.alias is not None and drawString._alias is not None and \
                            abs(data.alias - drawString._alias) > 0.5:
                        _alias = self.params[GLALIASSHADE] / 100.0

                    colour = colors.Color(*col[:3], alpha=_alias * alphaClip(col[3]))
                    colourPath = f'spectrumViewPeakLabels{data.spectrumView.pid}{data.index}' \
                                 f'{colour.red}{colour.green}{colour.blue}{colour.alpha}'

                    if data.matrixSymbols is not None:
                        newLine = QtGui.QVector4D(drawString.attribs[0], drawString.attribs[1], 0.0, 1.0)
                        newLine = data.matrixSymbols * newLine
                        newLine = [newLine.x(), newLine.y()]

                    else:
                        newLine = [drawString.attribs[0], drawString.attribs[1]]

                    if self.pointVisible(self._parent, newLine,
                                         x=data.x,
                                         y=data.y,
                                         width=data.width,
                                         height=data.height):
                        if colourPath not in colourGroups:
                            colourGroups[colourPath] = Group()
                        textGroup = drawString.text.split('\n')
                        textLine = len(textGroup) - 1
                        for text in textGroup:
                            self._addString(colourGroups, colourPath,
                                            drawString,
                                            (newLine[0], newLine[1]),
                                            # + (textLine * drawString.font.fontSize * self.fontScale)),
                                            colour,
                                            text=text,
                                            offset=textLine
                                            )
                            textLine -= 1

        for colourGroup in colourGroups.values():
            self._mainPlot.add(colourGroup)

    def _addIntegralLabels(self):
        """
        Add the integral labels to the main drawing area.
        """
        colourGroups = OrderedDict()
        for spectrumView in self._ordering:
            if spectrumView.isDeleted:
                continue

            validIntegralListViews = [pp for pp in spectrumView.integralListViews
                                      if pp.isDisplayed
                                      and spectrumView.isDisplayed
                                      and pp in self._parent._GLIntegrals._GLLabels.keys()
                                      and pp.integralList.pid in self.params[GLSELECTEDPIDS]]

            for integralListView in validIntegralListViews:  # spectrumView.integralListViews:
                for drawString in self._parent._GLIntegrals._GLLabels[integralListView].stringList:

                    if drawString.vertices is None or drawString.vertices.size == 0:
                        continue

                    col = drawString.colors[0]
                    if not isinstance(col, Iterable):
                        col = drawString.colors[:4]
                    colour = colors.Color(*col[:3], alpha=alphaClip(col[3]))
                    colourPath = f'spectrumViewIntegralLabels{spectrumView.pid}' \
                                 f'{colour.red}{colour.green}{colour.blue}{colour.alpha}'

                    newLine = [drawString.attribs[0], drawString.attribs[1]]
                    if self.pointVisible(self._parent, newLine,
                                         x=self.displayScale * self.mainView.left,
                                         y=self.displayScale * self.mainView.bottom,
                                         width=self.displayScale * self.mainView.width,
                                         height=self.displayScale * self.mainView.height):
                        if colourPath not in colourGroups:
                            colourGroups[colourPath] = Group()
                        textGroup = drawString.text.split('\n')
                        textLine = len(textGroup) - 1
                        for text in textGroup:
                            self._addString(colourGroups, colourPath,
                                            drawString,
                                            (newLine[0], newLine[1]),
                                            # + (textLine * drawString.font.fontSize * self.fontScale)),
                                            colour,
                                            text=text,
                                            offset=textLine
                                            )
                            textLine -= 1

        for colourGroup in colourGroups.values():
            self._mainPlot.add(colourGroup)

    def _addMultipletLabels(self):
        """
        Add the multiplet labels to the main drawing area.
        """
        colourGroups = OrderedDict()

        # iterate through the visible regions with the viewManager
        for data in self._addSpectrumViewManager('multipletLabels'):

            validMultipletListViews = [pp for pp in data.spectrumView.multipletListViews
                                       if pp.isDisplayed
                                       and data.spectrumView.isDisplayed
                                       and pp in self._parent._GLMultiplets._GLLabels.keys()
                                       and pp.multipletList.pid in self.params[GLSELECTEDPIDS]]

            for multipletListView in validMultipletListViews:  # spectrumView.multipletListViews:
                for drawString in self._parent._GLMultiplets._GLLabels[multipletListView].stringList:

                    if drawString.vertices is None or drawString.vertices.size == 0:
                        continue

                    col = drawString.colors[0]
                    if not isinstance(col, Iterable):
                        col = drawString.colors[:4]
                    _alias = 1.0
                    if data.alias is not None and drawString._alias is not None and \
                            abs(data.alias - drawString._alias) > 0.5:
                        _alias = self.params[GLALIASSHADE] / 100.0

                    colour = colors.Color(*col[:3], alpha=_alias * alphaClip(col[3]))
                    colourPath = f'spectrumViewMultipletLabels' \
                                 f'{data.spectrumView.pid}{data.index}' \
                                 f'{colour.red}{colour.green}{colour.blue}{colour.alpha}'

                    if data.matrixSymbols is not None:
                        newLine = QtGui.QVector4D(drawString.attribs[0], drawString.attribs[1], 0.0, 1.0)
                        newLine = data.matrixSymbols * newLine
                        newLine = [newLine.x(), newLine.y()]

                    else:
                        newLine = [drawString.attribs[0], drawString.attribs[1]]

                    if self.pointVisible(self._parent, newLine,
                                         x=data.x,
                                         y=data.y,
                                         width=data.width,
                                         height=data.height):
                        if colourPath not in colourGroups:
                            colourGroups[colourPath] = Group()
                        textGroup = drawString.text.split('\n')
                        textLine = len(textGroup) - 1
                        for text in textGroup:
                            self._addString(colourGroups, colourPath,
                                            drawString,
                                            (newLine[0], newLine[1]),
                                            # + (textLine * drawString.font.fontSize * self.fontScale)),
                                            colour,
                                            text=text,
                                            offset=textLine
                                            )
                            textLine -= 1

        for colourGroup in colourGroups.values():
            self._mainPlot.add(colourGroup)

    def _addMarkLabels(self):
        """
        Add the mark labels to the main drawing area.
        """
        colourGroups = OrderedDict()
        for drawString in self._parent._marksAxisCodes:

            if drawString.vertices is None or drawString.vertices.size == 0:
                continue

            col = drawString.colors[0]
            if not isinstance(col, Iterable):
                col = drawString.colors[:4]
            colour = colors.Color(*col[:3], alpha=alphaClip(col[3]))
            colourPath = f'projectMarks{colour.red}{colour.green}{colour.blue}{colour.alpha}'

            newLine = [drawString.attribs[0], drawString.attribs[1]]
            if self.pointVisible(self._parent, newLine,
                                 x=self.displayScale * self.mainView.left,
                                 y=self.displayScale * self.mainView.bottom,
                                 width=self.displayScale * self.mainView.width,
                                 height=self.displayScale * self.mainView.height):
                if colourPath not in colourGroups:
                    colourGroups[colourPath] = Group()
                self._addString(colourGroups, colourPath, drawString, newLine, colour, boxed=False)

        for colourGroup in colourGroups.values():
            self._mainPlot.add(colourGroup)

    def _addSpectrumLabels(self):
        """
        Add the (stacked) spectrum labels to the main drawing area.
        """
        colourGroups = OrderedDict()

        if not (self._parent._spectrumLabelling and self._parent._spectrumLabelling.strings):
            return

        for drawString in self._parent._spectrumLabelling.strings.values():

            if drawString.vertices is None or drawString.vertices.size == 0:
                continue

            col = drawString.colors[0]
            if not isinstance(col, Iterable):
                col = drawString.colors[:4]
            colour = colors.Color(*col[:3], alpha=alphaClip(col[3]))
            colourPath = f'projectSpectrumLabels{colour.red}{colour.green}{colour.blue}{colour.alpha}'

            newLine = [drawString.attribs[0], drawString.attribs[1]]
            if self.pointVisible(self._parent, newLine,
                                 x=self.displayScale * self.mainView.left,
                                 y=self.displayScale * self.mainView.bottom,
                                 width=self.displayScale * self.mainView.width,
                                 height=self.displayScale * self.mainView.height):
                if colourPath not in colourGroups:
                    colourGroups[colourPath] = Group()
                self._addString(colourGroups, colourPath, drawString, newLine, colour, boxed=True)

        for colourGroup in colourGroups.values():
            self._mainPlot.add(colourGroup)

    def _addSingleTrace(self, traceName, trace, spectrumView, colourGroups):
        # if spectrumView and not spectrumView.isDeleted and spectrumView.isDisplayed:
        #     # drawVertexColor
        #
        #     if self._parent._stackingMode:
        #         mat = QtGui.QMatrix4x4(self._parent._spectrumSettings[spectrumView].stackedMatrix)
        #     else:
        #         mat = None
        #
        #     self._appendVertexLineGroup(indArray=trace,
        #                                 colourGroups=colourGroups,
        #                                 plotDim={PLOTLEFT  : self.displayScale * self.mainView.left,
        #                                          PLOTBOTTOM: self.displayScale * self.mainView.bottom,
        #                                          PLOTWIDTH : self.displayScale * self.mainView.width,
        #                                          PLOTHEIGHT: self.displayScale * self.mainView.height},
        #                                 name=f'{traceName}{spectrumView.pid}',
        #                                 includeLastVertex=not self._parent.is1D,
        #                                 mat=mat,
        #                                 lineWidth=2.5 * self.baseThickness * self.contourThickness)

        for data in self._addSpectrumViewManager(f'traceContours{traceName}'):
            if data.alias == 0 and spectrumView == data.spectrumView:
                self._appendVertexLineGroup(indArray=trace,
                                            colourGroups=colourGroups,
                                            plotDim={PLOTLEFT  : data.x,
                                                     PLOTBOTTOM: data.y,
                                                     PLOTWIDTH : data.width,
                                                     PLOTHEIGHT: data.height},
                                            name=f'{traceName}{data.spectrumView.pid}',
                                            includeLastVertex=not self._parent.is1D,
                                            mat=data.matrix,
                                            lineWidth=0.5 * self.baseThickness * self.contourThickness)

    def _addTraces(self):
        """
        Add the traces to the main drawing area.
        """
        colourGroups = OrderedDict()
        for hTrace in self._parent._staticHTraces:
            self._addSingleTrace('hTrace', hTrace, hTrace.spectrumView, colourGroups)
        for vTrace in self._parent._staticVTraces:
            self._addSingleTrace('vTrace', vTrace, vTrace.spectrumView, colourGroups)

        self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='traces')

    def _addLiveTraces(self):
        """
        Add the live traces to the main drawing area.
        """
        colourGroups = OrderedDict()
        if self._parent.showActivePhaseTrace or not self._parent.spectrumDisplay.phasingFrame.isVisible():

            if self._parent._updateHTrace:
                for spectrumView, hTrace in self._parent._hTraces.items():
                    self._addSingleTrace('hTrace', hTrace, spectrumView, colourGroups)
            if self._parent._updateVTrace:
                for spectrumView, vTrace in self._parent._vTraces.items():
                    self._addSingleTrace('vTrace', vTrace, spectrumView, colourGroups)

        self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='traces')

    def _addInfiniteLines(self):
        """
        Add the infinite lines to the main drawing area.
        """
        colourGroups = OrderedDict()
        _x = self.displayScale * self.mainView.left
        _y = self.displayScale * self.mainView.bottom
        _width = self.displayScale * self.mainView.width
        _height = self.displayScale * self.mainView.height

        for infLine in self._parent._infiniteLines:
            if infLine.visible:
                colour = colors.Color(*infLine.brush[:3], alpha=alphaClip(infLine.brush[3]))
                colourPath = f'infiniteLines{colour.red}{colour.green}{colour.blue}{colour.alpha}{infLine.lineStyle}'

                if infLine.orientation == 'h':
                    newLine = [self._axisL, infLine.values, self._axisR, infLine.values]
                else:
                    newLine = [infLine.values, self._axisT, infLine.values, self._axisB]

                if newLine := self.lineVisible(self._parent, newLine, x=_x, y=_y, width=_width, height=_height):
                    if colourPath not in colourGroups:
                        colourGroups[colourPath] = {PDFLINES          : [],
                                                    PDFSTROKEWIDTH    : 0.5 * infLine.lineWidth * self.baseThickness,
                                                    PDFSTROKECOLOR    : colour,
                                                    PDFSTROKELINECAP  : 1, PDFCLOSEPATH: False,
                                                    PDFSTROKEDASHARRAY: GLLINE_STYLES_ARRAY[infLine.lineStyle]}
                    # colourGroups[colourPath][PDFLINES].append(newLine)
                    self.addLine(colourGroups[colourPath][PDFLINES], newLine)

        self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='infiniteLines')

    def _scaleRatioToWindow(self, values):
        return [values[0] * (self._axisR - self._axisL) + self._axisL,
                values[1] * (self._axisT - self._axisB) + self._axisB]

    def _addOverlayText(self):
        """
        Add the overlay text to the main drawing area.
        """
        colourGroups = OrderedDict()
        drawString = self._parent.stripIDString

        if drawString.vertices is None or drawString.vertices.size == 0:
            return

        colour = self.foregroundColour
        colourPath = f'overlayText{colour.red}{colour.green}{colour.blue}{colour.alpha}'

        newLine = self._scaleRatioToWindow([drawString.attribs[0] + (self.fontXOffset * self._parent.deltaX),
                                            drawString.attribs[1] + (self.fontYOffset * self._parent.deltaY)])

        if self.pointVisible(self._parent, newLine,
                             x=self.displayScale * self.mainView.left,
                             y=self.displayScale * self.mainView.bottom,
                             width=self.displayScale * self.mainView.width,
                             height=self.displayScale * self.mainView.height):
            pass

        if colourPath not in colourGroups:
            colourGroups[colourPath] = Group()
        self._addString(colourGroups, colourPath, drawString, newLine, colour, boxed=True)

        for colourGroup in colourGroups.values():
            self._mainPlot.add(colourGroup)

    def _addAxisMask(self):
        """
        Add a mask to clean the right/bottom axis areas.
        """
        ll1 = None
        ll2 = None
        if self.rAxis and self.bAxis:
            ll1 = [0.0, 0.0,
                   0.0, self.displayScale * self.mainView.bottom,
                   self.displayScale * self.mainView.width, self.displayScale * self.mainView.bottom,
                   self.displayScale * self.mainView.width, self.pixHeight,
                   self.pixWidth, self.pixHeight,
                   self.pixWidth, 0.0]
            ll2 = [0.0, 0.0, self.pixWidth, 0.0, self.pixWidth, self.pixHeight]

        elif self.rAxis:
            ll1 = [self.displayScale * self.mainView.width, 0.0,
                   self.displayScale * self.mainView.width, self.pixHeight,
                   self.pixWidth, self.pixHeight,
                   self.pixWidth, 0.0]
            ll2 = [self.pixWidth, 0.0, self.pixWidth, self.pixHeight]

        elif self.bAxis:
            ll1 = [0.0, 0.0,
                   0.0, self.displayScale * self.mainView.bottom,
                   self.pixWidth, self.displayScale * self.mainView.bottom,
                   self.pixWidth, 0.0]
            ll2 = [0.0, 0.0, self.pixWidth, 0.0]

        if ll1:
            pl = Path(fillColor=self.backgroundColour, stroke=None, strokeColor=None)
            pl.moveTo(ll1[0], ll1[1])
            for vv in range(2, len(ll1), 2):
                pl.lineTo(ll1[vv], ll1[vv + 1])
            pl.closePath()
            self._mainPlot.add(pl)

            pl = Path(fillColor=None, strokeColor=self.backgroundColour, strokeWidth=1.0)
            pl.moveTo(ll2[0], ll2[1])
            for vv in range(2, len(ll2), 2):
                pl.lineTo(ll2[vv], ll2[vv + 1])
            self._mainPlot.add(pl)

    def _addGridTickMarks(self):
        """
        Add tick marks to the main drawing area.
        """
        if self.rAxis or self.bAxis:
            colourGroups = OrderedDict()

            # add the right axis if visible
            if self.rAxis and self.params[GLAXISMARKS]:
                indArray = self._parent.gridList[1]

                if indArray.indices is not None and indArray.indices.size != 0:
                    # add the vertices for the grid lines
                    self._appendIndexLineGroup(indArray=indArray,
                                               colourGroups=colourGroups,
                                               plotDim={PLOTLEFT  : self.displayScale * self.rAxisMarkView.left,
                                                        PLOTBOTTOM: self.displayScale * self.rAxisMarkView.bottom,
                                                        PLOTWIDTH : self.displayScale * self.rAxisMarkView.width,
                                                        PLOTHEIGHT: self.displayScale * self.rAxisMarkView.height},
                                               name='gridAxes',
                                               setColour=self.foregroundColour,
                                               ratioLine=True,
                                               lineWidth=0.5 * self.baseThickness,
                                               vStep=2)

            # # add the right axis border-line if needed
            # if self.params[GLPLOTBORDER] or (self.rAxis and self.params[GLAXISLINES]):
            #     from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLArrays import GLVertexArray
            #
            #     # dummy list with non-visible line
            #     tempVertexArray = GLVertexArray(numLists=1, drawMode=GL.GL_LINE, dimension=2)
            #     tempVertexArray.indices = [0, 1]
            #     tempVertexArray.vertices = [0.0, 0.0, 0.0, 0.0]
            #
            #     # return the colour list defined by self.foreColour - needs setColour to be defined in the function call
            #     setGroup = self._appendIndexLineGroup(indArray=tempVertexArray,
            #                                           colourGroups=colourGroups,
            #                                           plotDim={PLOTLEFT  : self.displayScale * self.rAxisMarkView.left,
            #                                                    PLOTBOTTOM: self.displayScale * self.rAxisMarkView.bottom,
            #                                                    PLOTWIDTH : self.displayScale * self.rAxisMarkView.width,
            #                                                    PLOTHEIGHT: self.displayScale * self.rAxisMarkView.height},
            #                                           name='gridAxes',
            #                                           setColour=self.foregroundColour,
            #                                           ratioLine=True,
            #                                           lineWidth=0.5 * self.baseThickness)
            #     if setGroup in colourGroups:
            #         colourGroups[setGroup][PDFLINES].append([self.displayScale * self.mainView.width, self.displayScale * self.mainView.bottom,
            #                                                  self.displayScale * self.mainView.width, self.pixHeight])

            # add the bottom axis if visible
            if self.bAxis and self.params[GLAXISMARKS]:
                indArray = self._parent.gridList[2]

                if indArray.indices is not None and indArray.indices.size != 0:
                    # add the vertices for the grid lines
                    self._appendIndexLineGroup(indArray=indArray,
                                               colourGroups=colourGroups,
                                               plotDim={PLOTLEFT  : self.displayScale * self.bAxisMarkView.left,
                                                        PLOTBOTTOM: self.displayScale * self.bAxisMarkView.bottom,
                                                        PLOTWIDTH : self.displayScale * self.bAxisMarkView.width,
                                                        PLOTHEIGHT: self.displayScale * self.bAxisMarkView.height},
                                               name='gridAxes',
                                               setColour=self.foregroundColour,
                                               ratioLine=True,
                                               lineWidth=0.5 * self.baseThickness,
                                               vStep=2)

            # # add the bottom axis border line if needed
            # if self.params[GLPLOTBORDER] or (self.bAxis and self.params[GLAXISLINES]):
            #     from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLArrays import GLVertexArray
            #
            #     tempVertexArray = GLVertexArray(numLists=1, drawMode=GL.GL_LINE, dimension=2)
            #     tempVertexArray.indices = [0, 1]
            #     tempVertexArray.vertices = [0.0, 0.0, 0.0, 0.0]
            #
            #     # dummy list with non-visible line
            #     setGroup = self._appendIndexLineGroup(indArray=tempVertexArray,
            #                                           colourGroups=colourGroups,
            #                                           plotDim={PLOTLEFT  : self.displayScale * self.bAxisMarkView.left,
            #                                                    PLOTBOTTOM: self.displayScale * self.bAxisMarkView.bottom,
            #                                                    PLOTWIDTH : self.displayScale * self.bAxisMarkView.width,
            #                                                    PLOTHEIGHT: self.displayScale * self.bAxisMarkView.height},
            #                                           name='gridAxes',
            #                                           setColour=self.foregroundColour,
            #                                           ratioLine=True,
            #                                           lineWidth=0.5 * self.baseThickness)
            #
            #     if setGroup in colourGroups:
            #         colourGroups[setGroup][PDFLINES].append([self.displayScale * self.mainView.left, self.displayScale * self.mainView.bottom,
            #                                                  self.displayScale * self.mainView.width, self.displayScale * self.mainView.bottom])

            self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name='gridAxes')

    def _addString(self, colourGroups, colourPath, drawString, position, colour, boxed=False, text=None, offset=0):

        if self.params[GLUSEPRINTFONT]:
            _fontName, _fontSize = self.params[GLPRINTFONT]

            # allows the user to set the font size
            if _fontName == DEFAULT_FONT:
                _fontName = drawString.font.fontName

            # _fontSize = self._printFont.pointSize()
            # if _fontSize < 0:
            #     _fontSize = self._printFont.pixelSize()
            # _fontName = self._printFont.family()
        else:
            _fontSize = drawString.font.fontSize * self.fontScale
            _fontName = drawString.font.fontName

        newStr = String(position[0], position[1] + (offset * _fontSize),
                        text or drawString.text,
                        fontSize=_fontSize,
                        fontName=_fontName,
                        fillColor=colour)

        with contextlib.suppress(KeyError):
            # sometimes reportlab can't find the font :|
            bounds = newStr.getBounds()
            if boxed:
                # arbitrary scaling
                dx = _fontSize * 0.11
                dy = _fontSize * 0.125
                colourGroups[colourPath].add(Rect(bounds[0] - dx, bounds[1] - dy,
                                                  (bounds[2] - bounds[0]) + 5 * dx, (bounds[3] - bounds[1]) + 2.0 * dy,
                                                  strokeColor=None,
                                                  fillColor=self.backgroundColour))

            colourGroups[colourPath].add(newStr)

    def _addGridLabels(self):
        """
        Add labels/titles/units to the right/bottom axis areas.
        """
        if not (self.rAxis or self.bAxis):
            return

        colourGroups = OrderedDict()
        if self.rAxis:
            numStrs = len(self._parent._axisYLabelling)

            for strNum, drawString in enumerate(self._parent._axisYLabelling):

                # skip empty strings
                if not drawString.text:
                    continue

                # drawTextArray
                colour = self.foregroundColour
                colourPath = f'axisLabels{colour.red}{colour.green}{colour.blue}{colour.alpha}'

                # add (0, 3) to mid-point
                # mid = self._axisL + (0 + drawString.attribs[0]) * (self._axisR - self._axisL) / self._parent.AXIS_MARGINRIGHT
                # newLine = [mid, drawString.attribs[1] + (3 * self._parent.pixelY)]
                # mid = self._axisL + drawString.attribs[0] * (self._axisR - self._axisL) * self._parent.pixelX
                # newLine = [mid, drawString.attribs[1] + (3 * self._parent.deltaY)]

                attribPos = (0.0, 0.0) if drawString.attribs.size < 2 else drawString.attribs[:2]
                newLine = self._scaleRatioToWindow([(self.fontXOffset + attribPos[0]) / self._parent.AXIS_MARGINRIGHT,
                                                    attribPos[1] + (self.fontYOffset * self._parent.deltaY)])

                if self.pointVisible(self._parent, newLine,
                                     x=self.displayScale * self.rAxisBarView.left,
                                     y=self.displayScale * self.rAxisBarView.bottom,
                                     width=self.displayScale * self.rAxisBarView.width,
                                     height=self.displayScale * self.rAxisBarView.height):
                    if colourPath not in colourGroups:
                        colourGroups[colourPath] = Group()

                    # set box around the last 2 elements (axis title and units), and skip if not needed
                    if strNum == numStrs - 1 and self.params[GLAXISUNITS]:
                        # draw units
                        self._addString(colourGroups, colourPath, drawString, newLine, colour,
                                        boxed=True)
                    elif strNum == numStrs - 2 and self.params[GLAXISTITLES]:
                        # draw axis title
                        self._addString(colourGroups, colourPath, drawString, newLine, colour,
                                        boxed=True)
                    elif strNum < numStrs - 2 and self.params[GLAXISLABELS]:
                        # draw labels
                        self._addString(colourGroups, colourPath, drawString, newLine, colour,
                                        boxed=False)

        if self.bAxis:
            numStrs = len(self._parent._axisXLabelling)

            for strNum, drawString in enumerate(self._parent._axisXLabelling):

                # skip empty strings
                if not drawString.text:
                    continue

                # drawTextArray
                colour = self.foregroundColour
                colourPath = f'axisLabels{colour.red}{colour.green}{colour.blue}{colour.alpha}'

                # add (0, 3) to mid
                # mid = self._axisB + (3 + drawString.attribs[1]) * (self._axisT - self._axisB) / self._parent.AXIS_MARGINBOTTOM
                # newLine = [drawString.attribs[0] + (0 * self._parent.pixelX), mid]
                # mid = self._axisB + drawString.attribs[1] * (self._axisT - self._axisB)
                # newLine = [drawString.attribs[0] + (0 * self._parent.deltaX), mid]

                attribPos = (0.0, 0.0) if drawString.attribs.size < 2 else drawString.attribs[:2]
                newLine = self._scaleRatioToWindow([attribPos[0] + (self.fontXOffset * self._parent.deltaX),
                                                    (self.fontYOffset + attribPos[1]) / self._parent.AXIS_MARGINBOTTOM])

                if self.pointVisible(self._parent, newLine,
                                     x=self.displayScale * self.bAxisBarView.left,
                                     y=self.displayScale * self.bAxisBarView.bottom,
                                     width=self.displayScale * self.bAxisBarView.width,
                                     height=self.displayScale * self.bAxisBarView.height):
                    if colourPath not in colourGroups:
                        colourGroups[colourPath] = Group()

                    # set box around the last 2 elements (axis title and units), and skip if not needed
                    if strNum == numStrs - 1 and self.params[GLAXISUNITS]:
                        # draw units
                        self._addString(colourGroups, colourPath, drawString, newLine, colour,
                                        boxed=True)
                    elif strNum == numStrs - 2 and self.params[GLAXISTITLES]:
                        # draw axis title
                        self._addString(colourGroups, colourPath, drawString, newLine, colour,
                                        boxed=True)
                    elif strNum < numStrs - 2 and self.params[GLAXISLABELS]:
                        # draw labels
                        self._addString(colourGroups, colourPath, drawString, newLine, colour,
                                        boxed=False)

        for colourGroup in colourGroups.values():
            self._mainPlot.add(colourGroup)

    @staticmethod
    def report(w, h, plot):
        """
        Return the current report for the GL widget.
        This is the vector image for the current strip containing the GL widget,
        it is a reportlab Flowable type object that can be added to reportlab documents.
        :return reportlab.platypus.Flowable:
        """
        return Clipped_Flowable(width=w, height=h,
                                mainPlot=plot,  #self._mainPlot,
                                mainDim={PLOTLEFT  : 0,  #scale*view.left,
                                         PLOTBOTTOM: 0,  #scale*view.bottom,
                                         PLOTWIDTH : w,  #scale*self.mainView.width,
                                         PLOTHEIGHT: h  #scale*self.mainView.height
                                         }
                                )

    # def _addDrawingToStory(self):
    #     """
    #     Add the current drawing the story of a document
    #     """
    #     print('add drawing to story of document')
    #     report = self.report(self.pixWidth, self.pixHeight)
    #     self.stripReports.append(report)
    #     self._appendStripSize(report)
    #
    # def _addSpacerToStory(self):
    #     """
    #     Add the current drawing the story of a document
    #     """
    #     if self.params[GLSTRIPDIRECTION] == 'Y':
    #         report = self.report(self.stripSpacing, self.pixHeight)
    #     else:
    #         report = self.report(self.pixWidth, self.stripSpacing)
    #     self.stripReports.append(report)
    #     self._appendStripSize(report)

    def _appendStripSize(self, report):

        _val = 1.0

        self.stripWidths.append(report.width * _val)
        self.stripHeights.append(report.height * _val)

    def _addTableToStory(self):
        _style = TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                             ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                             ('TOPPADDING', (0, 0), (-1, -1), 0),
                             ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                             ('LEFTPADDING', (0, 0), (-1, -1), 0),
                             ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                             ('LEADING', (0, 0), (-1, -1), 0),
                             ]
                            )

        _minSpace = 2.0 * cm  # self.docHeight / 2.0

        if self.params[GLSTRIPDIRECTION] == 'Y':
            # arrange as a row
            table = (self.stripReports,)
            _spacing = min(_minSpace, max(0.0, (self.docHeight - self.stripHeights[0]) / 2.0))
            _table = Table(table,
                           colWidths=self.stripWidths, rowHeights=self.stripHeights[0],
                           )

        else:
            # arrange as a column
            table = tuple((rep,) for rep in self.stripReports)
            _spacing = min(_minSpace, max(0.0, (self.docHeight - sum(self.stripHeights)) / 2.0))
            _table = Table(table,
                           rowHeights=self.stripHeights, colWidths=self.stripWidths[0],
                           )
        self._report.doc.topMargin = math.floor(_spacing)
        # NOTE:ED - same for left/bottom margin?

        _table.setStyle(_style)
        self._report.addItemToStory(_table)

    def writePNGFile(self):
        """
        Output a PNG file for the GL widget.
        """
        from reportlab.graphics.renderPM import PMCanvas, draw

        with catchExceptions(errorStringTemplate='Error writing PNG file: "%s"', printTraceBack=False):
            dpi = self.params[GLEXPORTDPI]

            if (rows := (self.params[GLSTRIPDIRECTION] == 'Y')):
                w, h = sum(self.stripWidths), self.stripHeights[0]
                x = y = 0
            else:
                w, h = self.stripWidths[0], sum(self.stripHeights)
                x, y = 0, h

            # create a canvas to contain all the strips/spacers/axes
            c = PMCanvas(w, h, dpi=dpi)
            for plt, dx, dy in zip(self._mainPlots, self.stripWidths, self.stripHeights):

                if not rows:
                    y -= dy

                # scale and translate each plot to the correct place in the canvas
                plt.scale(dpi / 72, dpi / 72)
                plt.translate(x, y)

                # draw into the common canvas
                # originally used renderPM.drawToFile
                draw(plt, c, 0, 0, showBoundary=False)

                # update the co-ordinates for the next plot
                if rows:
                    x += dx

            c.saveToFile(self.filename, fmt='PNG')

    def writeSVGFile(self):
        """
        Output an SVG file for the GL widget.
        """
        from reportlab.graphics.renderSVG import SVGCanvas, draw

        with catchExceptions(errorStringTemplate='Error writing SVG file: "%s"', printTraceBack=False):

            if (rows := (self.params[GLSTRIPDIRECTION] == 'Y')):
                w, h = sum(self.stripWidths), self.stripHeights[0]
                x = y = 0
            else:
                w, h = self.stripWidths[0], sum(self.stripHeights)
                x, y = 0, h

            # create a canvas to contain all the strips/spacers/axes
            c = SVGCanvas((w, h))
            for plt, dx, dy in zip(self._mainPlots, self.stripWidths, self.stripHeights):

                if not rows:
                    y -= dy

                # translate each plot to the correct place in the canvas
                plt.translate(x, y)

                # draw into the common canvas
                # originally used renderSVG.drawToFile
                draw(plt, c, 0, 0, showBoundary=False)

                # update the co-ordinates for the next plot
                if rows:
                    x += dx

            c.save(self.filename)

    def writePDFFile(self):
        """
        Output a PDF file for the GL widget.
        """
        with catchExceptions(errorStringTemplate='Error writing PDF document: "%s"', printTraceBack=False):
            self._report.writeDocument()

    def writePSFile(self):
        """
        Output a PS file for the GL widget.
        """
        from reportlab.graphics.renderPS import PSCanvas, draw

        with catchExceptions(errorStringTemplate='Error writing PS file: "%s"', printTraceBack=False):

            if (rows := (self.params[GLSTRIPDIRECTION] == 'Y')):
                w, h = sum(self.stripWidths), self.stripHeights[0]
                x = y = 0
            else:
                w, h = self.stripWidths[0], sum(self.stripHeights)
                x, y = 0, h

            # create a canvas to contain all the strips/spacers/axes
            c = PSCanvas((w, h))
            for plt, dx, dy in zip(self._mainPlots, self.stripWidths, self.stripHeights):

                if not rows:
                    y -= dy

                # translate each plot to the correct place in the canvas
                plt.translate(x, y)

                # draw into the common canvas
                # originally used renderPS.drawToFile
                draw(plt, c, 0, 0, showBoundary=False)

                # update the co-ordinates for the next plot
                if rows:
                    x += dx

            c.save(self.filename)

    def _appendVertexLineGroup(self, indArray, colourGroups, plotDim, name, mat=None,
                               includeLastVertex=False, lineWidth=0.5):
        _x = plotDim[PLOTLEFT]
        _y = plotDim[PLOTBOTTOM]
        _width = plotDim[PLOTWIDTH]
        _height = plotDim[PLOTHEIGHT]

        for vv in range(0, len(indArray.vertices) - 2, 2):

            if mat is not None:
                vectStart = QtGui.QVector4D(indArray.vertices[vv], indArray.vertices[vv + 1], 0.0, 1.0)
                vectStart = mat * vectStart
                vectEnd = QtGui.QVector4D(indArray.vertices[vv + 2], indArray.vertices[vv + 3], 0.0, 1.0)
                vectEnd = mat * vectEnd
                newLine = [vectStart[0], vectStart[1], vectEnd[0], vectEnd[1]]
            else:
                newLine = list(indArray.vertices[vv:vv + 4])

            colour = colors.Color(*indArray.colors[vv * 2:vv * 2 + 3], alpha=alphaClip(indArray.colors[vv * 2 + 3]))
            colourPath = f'{name}{colour.red}{colour.green}{colour.blue}{colour.alpha}'
            if colourPath not in colourGroups:
                cc = colourGroups[colourPath] = {}
                if (indArray.fillMode or GL.GL_LINE) == GL.GL_LINE:
                    cc[PDFLINES] = []
                    cc[PDFSTROKEWIDTH] = lineWidth
                    cc[PDFSTROKECOLOR] = colour
                    cc[PDFSTROKELINECAP] = 1
                else:
                    # assume that it is GL.GL_FILL
                    cc[PDFLINES] = []
                    cc[PDFFILLCOLOR] = colour
                    cc[PDFSTROKE] = None
                    cc[PDFSTROKECOLOR] = None

            if newLine := self.lineVisible(self._parent, newLine, x=_x, y=_y, width=_width, height=_height):
                # colourGroups[colourPath][PDFLINES].append(newLine)
                self.addLine(colourGroups[colourPath][PDFLINES], newLine)

    @staticmethod
    def _colourID(name, colour):
        return f'spectrumView{name}{colour.red}{colour.green}{colour.blue}{colour.alpha}'

    def _appendIndexLineGroup(self, indArray, colourGroups, plotDim, name, mat=None,
                              fillMode=None, splitGroups=False,
                              setColour=None, lineWidth=0.5, ratioLine=False, alias=None, vStep=4):
        if indArray.drawMode == GL.GL_TRIANGLES:
            indexLen = 3
        elif indArray.drawMode == GL.GL_QUADS:
            indexLen = 4
        else:
            indexLen = 2

        # override so that each element is a new group
        if splitGroups:
            colourGroups = OrderedDict()

        _x = plotDim[PLOTLEFT]
        _y = plotDim[PLOTBOTTOM]
        _width = plotDim[PLOTWIDTH]
        _height = plotDim[PLOTHEIGHT]

        for ii in range(0, len(indArray.indices), indexLen):
            ii0 = [int(ind) for ind in indArray.indices[ii:ii + indexLen]]

            newLine = []
            for vv in ii0:
                if mat is not None:
                    _vec = QtGui.QVector4D(indArray.vertices[vv * vStep], indArray.vertices[vv * vStep + 1], 0.0, 1.0)
                    _vec = mat * _vec

                    if ratioLine:
                        newLine.extend(self._scaleRatioToWindow([_vec.x(), _vec.y()]))
                    else:
                        newLine.extend([_vec.x(), _vec.y()])

                elif ratioLine:
                    # convert ratio to axis coordinates
                    # newLine.extend([self._scaleRatioToWindow(indArray.vertices[vv * 2], (self._axisR - self._axisL), self._axisL),
                    #                 self._scaleRatioToWindow(indArray.vertices[vv * 2 + 1], (self._axisT - self._axisB), self._axisB)])
                    newLine.extend(self._scaleRatioToWindow(indArray.vertices[vv * vStep:vv * vStep + vStep]))
                else:
                    newLine.extend([indArray.vertices[vv * vStep], indArray.vertices[vv * vStep + 1]])

            _alias = 1.0
            if alias is not None and \
                    indArray.attribs is not None and \
                    indArray.attribs.size != 0 and \
                    abs(indArray.attribs[ii0[0]] - alias) > 0.5:
                _alias = self.params[GLALIASSHADE] / 100.0
            colour = (setColour or colors.Color(*indArray.colors[ii0[0] * 4:ii0[0] * 4 + 3],
                                                alpha=_alias * alphaClip(indArray.colors[ii0[0] * 4 + 3])))
            colourPath = self._colourID(name, colour)  # 'spectrumView%s%s%s%s%s' % (name,
            # colour.red, colour.green, colour.blue, colour.alpha)

            # # override so that each element is a new group
            # if splitGroups:
            #     colourGroups = OrderedDict()

            if colourPath not in colourGroups:
                cc = colourGroups[colourPath] = {}
                if (fillMode or indArray.fillMode or GL.GL_LINE) == GL.GL_LINE:
                    cc[PDFLINES] = []
                    cc[PDFSTROKEWIDTH] = lineWidth
                    cc[PDFSTROKECOLOR] = colour
                    cc[PDFSTROKELINECAP] = 1
                    cc[PDFFILL] = None
                    cc[PDFFILLCOLOR] = None  # need to disable fill
                else:
                    # assume that it is GL.GL_FILL
                    cc[PDFLINES] = []
                    cc[PDFFILLCOLOR] = colour
                    cc[PDFSTROKE] = None
                    cc[PDFSTROKECOLOR] = None  # need to disable outline

            if newLine := self.lineVisible(self._parent, newLine, x=_x, y=_y, width=_width, height=_height):
                # colourGroups[colourPath][PDFLINES].append(newLine)
                self.addLine(colourGroups[colourPath][PDFLINES], newLine)

        # override so that each element is a new group
        if splitGroups:
            self._appendGroup(drawing=self._mainPlot, colourGroups=colourGroups, name=name)

        if setColour is not None:
            return self._colourID(name, setColour)

    def _appendIndexLineGroupFill(self, indArray=None, listView=None, colourGroups=None,
                                  plotDim=None, name=None, mat=None,
                                  fillMode=None, splitGroups=False, lineWidth=0.5, vStep=4):
        for spectrumView in self._ordering:
            if spectrumView.isDeleted:
                continue
            # specSettings = self._parent._spectrumSettings[spectrumView]

            # get the transformation matrix from the spectrumView
            mat = QtGui.QMatrix4x4(self._parent._spectrumSettings[spectrumView].matrix)

            attribList = getattr(spectrumView, f'{listView}Views')
            validListViews = [pp for pp in attribList
                              if pp.isDisplayed
                              and spectrumView.isDisplayed
                              and getattr(pp, listView).pid in self.params[GLSELECTEDPIDS]]

            for thisListView in validListViews:
                if thisListView in indArray.keys():
                    thisSpec = indArray[thisListView]

                    self._appendIndexLineGroup(indArray=thisSpec,
                                               colourGroups=colourGroups,
                                               plotDim=plotDim,
                                               name=f'spectrumView{name}{spectrumView.pid}',
                                               mat=mat,
                                               fillMode=fillMode,
                                               splitGroups=splitGroups,
                                               lineWidth=lineWidth,
                                               vStep=vStep)

    @staticmethod
    def _appendGroup(drawing: Drawing = None, colourGroups: dict = None, name: str = None):
        """
        Append a group of polylines to the current drawing object
        :param drawing - drawing to append groups to
        :param colourGroups - OrderedDict of polylines
        :param name - name for the group
        """
        gr = Group()
        for colourItem in colourGroups.values():
            wanted_keys = [PDFSTROKEWIDTH,
                           PDFSTROKECOLOR,
                           PDFSTROKELINECAP,
                           PDFFILLCOLOR,
                           PDFFILL,
                           PDFFILLMODE,
                           PDFSTROKE,
                           PDFSTROKEDASHARRAY,
                           PDFSTROKEDASHOFFSET
                           ]

            newColour = {k: colourItem[k] for k in wanted_keys if k in colourItem}

            for ll in colourItem[PDFLINES]:
                if len(ll) < 4:
                    continue
                try:
                    if len(ll) > 4 and colourItem.get(PDFCLOSEPATH) is not False:
                        pl = Polygon(points=ll, **newColour)
                    else:
                        pl = PolyLine(points=ll, **newColour)
                    # add to the group if path contains at least 1 valid line
                    gr.add(pl)
                except Exception:
                    pass

        drawing.add(gr, name=name)

    @staticmethod
    def between(val, l, r):
        return (l - val) * (r - val) <= 0

    def pointVisible(self, _parent, lineList, x=0.0, y=0.0, width=0.0, height=0.0):
        """return true if the line has visible endpoints
        """
        axisL, axisR, axisT, axisB = self._axisL, self._axisR, self._axisT, self._axisB

        if (self.between(lineList[0], axisL, axisR) and
                (self.between(lineList[1], axisT, axisB))):
            lineList[0] = x + width * (lineList[0] - axisL) / (axisR - axisL)
            lineList[1] = y + height * (lineList[1] - axisB) / (axisT - axisB)
            return True

    def lineVisible(self, _parent, lineList, x=0.0, y=0.0, width=0.0, height=0.0):
        """return the list of visible lines
        """
        # make into a list of tuples
        newList = []
        newLine = [[lineList[ll], lineList[ll + 1]] for ll in range(0, len(lineList), 2)]
        if len(newLine) > 2:
            newList = self.clipPoly(_parent, newLine)
        elif len(newLine) == 2:
            newList = self.clipLine(_parent, newLine)

        with contextlib.suppress(Exception):
            if newList:
                axisL, axisR, axisT, axisB = self._axisL, self._axisR, self._axisT, self._axisB

                newList = [pp for outPoint in newList for pp in (x + width * (outPoint[0] - axisL) / (axisR - axisL),
                                                                 y + height * (outPoint[1] - axisB) / (axisT - axisB))]
        return newList

    def clipPoly(self, _parent, subjectPolygon):
        """Apply Sutherland-Hodgman algorithm for clipping polygons
        """
        axisL, axisR, axisT, axisB = self._axisL, self._axisR, self._axisT, self._axisB

        if self._parent.XDIRECTION != self._parent.YDIRECTION:
            clipPolygon = [[axisL, axisB],
                           [axisL, axisT],
                           [axisR, axisT],
                           [axisR, axisB]]
        else:
            clipPolygon = [[axisL, axisB],
                           [axisR, axisB],
                           [axisR, axisT],
                           [axisL, axisT]]

        def inside(p):
            return (cp2[0] - cp1[0]) * (p[1] - cp1[1]) > (cp2[1] - cp1[1]) * (p[0] - cp1[0])

        def get_intersect():
            """Returns the point of intersection of the lines passing through a2,a1 and b2,b1.
            """
            pp = np.vstack([s, e, cp1, cp2])  # s for stacked

            h = np.hstack((pp, np.ones((4, 1))))  # h for homogeneous
            l1 = np.cross(h[0], h[1])  # get first line
            l2 = np.cross(h[2], h[3])  # get second line
            x, y, z = np.cross(l1, l2)  # point of intersection
            return (float('inf'), float('inf')) if z == 0 else (x / z, y / z)

        outputList = subjectPolygon
        cLen = len(clipPolygon)
        cp1 = clipPolygon[cLen - 1]

        for clipVertex in clipPolygon:
            cp2 = clipVertex
            inputList = outputList
            outputList = []
            if not inputList:
                break

            ilLen = len(inputList)
            s = inputList[ilLen - 1]

            for e in inputList:
                if inside(e):
                    if not inside(s):
                        outputList.append(get_intersect())
                    outputList.append(e)
                elif inside(s):
                    outputList.append(get_intersect())
                s = e
            cp1 = cp2
        return outputList

    def clipLine(self, _parent, subjectPolygon):
        """Apply clipping to single line
        """
        axisL, axisR, axisT, axisB = self._axisL, self._axisR, self._axisT, self._axisB

        if self._parent.XDIRECTION != self._parent.YDIRECTION:
            clipPolygon = [[axisL, axisB],
                           [axisL, axisT],
                           [axisR, axisT],
                           [axisR, axisB]]
        else:
            clipPolygon = [[axisL, axisB],
                           [axisR, axisB],
                           [axisR, axisT],
                           [axisL, axisT]]

        def inside(p):
            return (cp2[0] - cp1[0]) * (p[1] - cp1[1]) > (cp2[1] - cp1[1]) * (p[0] - cp1[0])

        def get_intersect():
            """Returns the point of intersection of the lines passing through a2,a1 and b2,b1.
            """
            pp = np.vstack([s, e, cp1, cp2])  # s for stacked

            h = np.hstack((pp, np.ones((4, 1))))  # h for homogeneous
            l1 = np.cross(h[0], h[1])  # get first line
            l2 = np.cross(h[2], h[3])  # get second line
            x, y, z = np.cross(l1, l2)  # point of intersection
            return (float('inf'), float('inf')) if z == 0 else (x / z, y / z)

        outputList = subjectPolygon
        cLen = len(clipPolygon)
        cp1 = clipPolygon[cLen - 1]

        for clipVertex in clipPolygon:
            cp2 = clipVertex
            inputList = outputList
            outputList = []
            if not inputList:
                break
            s, e = inputList[0], inputList[1]
            if inside(e):
                if inside(s):
                    outputList.append(s)
                else:
                    outputList.append(get_intersect())
                outputList.append(e)
            elif inside(s):
                outputList.append(s)
                outputList.append(get_intersect())
            # iterate to next clip-boundary
            cp1 = cp2
        return outputList

    def lineFit(self, _parent, lineList, x=0.0, y=0.0, width=0.0, height=0.0, checkIntegral=False):
        axisL, axisR, axisT, axisB = self._axisL, self._axisR, self._axisT, self._axisB

        fit = next((True for pp in range(0, len(lineList), 2)
                    if (self.between(lineList[pp], axisL, axisR) and
                        (self.between(lineList[pp + 1], axisT, axisB) or
                         checkIntegral))),
                   False)

        for pp in range(0, len(lineList), 2):
            lineList[pp] = x + width * (lineList[pp] - axisL) / (axisR - axisL)
            lineList[pp + 1] = y + height * (lineList[pp + 1] - axisB) / (axisT - axisB)
        return fit


class Clipped_Flowable(Flowable):
    def __init__(self, width=0.0, height=0.0,
                 mainPlot=None, mainDim=None):
        Flowable.__init__(self)
        self.mainPlot = mainPlot
        self.mainDim = mainDim
        self.width = width
        self.height = height

    def draw(self):
        if self.mainPlot:
            self.canv.saveState()

            # make a clip-path for the mainPlot
            pl = self.canv.beginPath()
            pl.moveTo(self.mainDim[PLOTLEFT], self.mainDim[PLOTBOTTOM])
            pl.lineTo(self.mainDim[PLOTLEFT], self.mainDim[PLOTHEIGHT] + self.mainDim[PLOTBOTTOM])
            pl.lineTo(self.mainDim[PLOTLEFT] + self.mainDim[PLOTWIDTH],
                      self.mainDim[PLOTHEIGHT] + self.mainDim[PLOTBOTTOM])
            pl.lineTo(self.mainDim[PLOTLEFT] + self.mainDim[PLOTWIDTH], self.mainDim[PLOTBOTTOM])
            pl.close()
            self.canv.clipPath(pl, fill=0, stroke=0)

            # draw the drawing into the canvas
            self.mainPlot.drawOn(self.canv, self.mainDim[PLOTLEFT], self.mainDim[PLOTBOTTOM])

            # restore pre-clipping state
            self.canv.restoreState()


def main():
    buf = io.BytesIO()

    # Set up the document with paper size and margins
    doc = SimpleDocTemplate(
            buf,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            pagesize=A4,
            )

    # Styling paragraphs
    styles = getSampleStyleSheet()

    # Write things on the document
    paragraphs = [Paragraph('This is a paragraph testing CCPN pdf generation', styles['Normal']),
                  Paragraph('This is another paragraph', styles['Normal'])
                  ]

    dpi = 72
    mmwidth = 150
    mmheight = 150
    pixWidth = int(mmwidth * mm)
    pixHeight = int(mmheight * mm)

    # the width doesn't mean anything, but the height defines how much space is added to the story
    # co-ordinates are origin bottom-left
    d = Drawing(pixWidth, pixHeight, )

    d.add(Rect(0.0, 0.0, pixWidth, pixHeight, fillColor=colors.yellow, stroke=0, fill=0))
    d.add(String(150.0, 100.0, 'Hello World', fontSize=18, fillColor=colors.red))
    d.add(String(180.0, 86.0, 'Special characters \
                            \xc2\xa2\xc2\xa9\xc2\xae\xc2\xa3\xce\xb1\xce\xb2',
                 fillColor=colors.red))

    pl = PolyLine([120, 110, 130, 150],
                  strokeWidth=2,
                  strokeColor=colors.red)
    d.add(pl)

    # pl = definePath(isClipPath=1)
    # pl.moveTo(30.0, 30.0)
    # pl.lineTo(30.0, pixHeight/2)
    # pl.lineTo(pixWidth/2, pixHeight/2)
    # pl.lineTo(pixWidth/2, 30.0)
    # pl.closePath()
    # d.add(pl)

    gr = Group()
    gr.add(Rect(0.0, 0.0, 20.0, 20.0, fillColor=colors.yellow))
    gr.add(Rect(30.0, 30.0, 20.0, 20.0, fillColor=colors.blue))
    d.add(gr)
    # d.add(Rect(0.0, 0.0, 20.0, 20.0, fillColor=colors.yellow))
    # d.add(Rect(30.0, 30.0, 20.0, 20.0, fillColor=colors.blue))

    # paragraphs.append(d)

    fred = Clipped_Flowable()
    paragraphs.append(fred)

    doc.pageCompression = None
    # this generates the buffer to write to the file
    doc.build(paragraphs)

    c = canvas.Canvas(filename='/Users/ejb66/Desktop/testCCPNpdf3.pdf', pagesize=A4)

    # make a clip-path
    pl = c.beginPath()
    pl.moveTo(0, 0)
    pl.lineTo(0, 100)
    pl.lineTo(100, 100)
    pl.lineTo(100, 0)
    pl.close()
    c.clipPath(pl, fill=0, stroke=0)

    # draw the drawing to the canvas after clipping defined
    d.drawOn(c, 0, 0)
    c.save()

    # Write the PDF to a file
    with open('/Users/ejb66/Desktop/testCCPNpdf.pdf', 'wb') as fd:
        fd.write(buf.getvalue())

    c = canvas.Canvas(filename='/Users/ejb66/Desktop/testCCPNpdf2.pdf', pagesize=A4)

    # define a clipping path
    pageWidth = A4[0]
    pageHeight = A4[1]

    p = c.beginPath()
    p.moveTo(0, 0)
    p.lineTo(0, 200)
    p.lineTo(200, 200)
    p.lineTo(200, 0)
    p.close()
    c.clipPath(p, fill=0, stroke=0)

    red50transparent = colors.Color(100, 0, 0, alpha=alphaClip(0.5))
    c.setFillColor(colors.black)
    c.setFont('Helvetica', 10)
    c.drawString(25, 180, 'solid')
    c.setFillColor(colors.blue)
    c.rect(25, 25, 100, 100, fill=True, stroke=False)
    c.setFillColor(colors.red)
    c.rect(100, 75, 100, 100, fill=True, stroke=False)
    c.setFillColor(colors.black)
    c.drawString(225, 180, 'transparent')
    c.setFillColor(colors.blue)
    c.rect(225, 25, 100, 100, fill=True, stroke=False)
    c.setFillColor(red50transparent)
    c.rect(300, 75, 100, 100, fill=True, stroke=False)

    c.rect(0, 0, 100, 100, fill=True, stroke=False)

    # this is much better as it remembers the transparency and object grouping
    h = inch / 3.0
    k = inch / 2.0
    c.setStrokeColorRGB(0.2, 0.3, 0.5)
    c.setFillColorRGB(0.8, 0.6, 0.2)
    c.setLineWidth(4)
    p = c.beginPath()
    for i in (1, 2, 3, 4):
        for j in (1, 2):
            xc, yc = inch * i, inch * j
            p.moveTo(xc, yc)
            p.arcTo(xc - h, yc - k, xc + h, yc + k, startAng=0, extent=60 * i)
            # close only the first one, not the second one
            if j == 1:
                p.close()
    c.drawPath(p, fill=1, stroke=1)

    c.save()


if __name__ == '__main__':
    main()
