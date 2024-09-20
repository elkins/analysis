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
__dateModified__ = "$dateModified: 2024-08-07 13:10:49 +0100 (Wed, August 07, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-12-11 17:47:59 +0000 (Fri, December 11, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.ui.gui.guiSettings import getColours, CCPNGLWIDGET_FOREGROUND, CCPNGLWIDGET_INTEGRALSHADE
from ccpn.ui.gui.lib.OpenGL import CcpnOpenGLDefs as GLDefs
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLArrays import GLRENDERMODE_REBUILD, GLRENDERMODE_DRAW, GLRENDERMODE_RESCALE
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLFonts import GLString
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLLabelling import GL1dLabelling, GLLabelling
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLWidgets import GLIntegralRegion
from ccpn.util.Colour import getAutoColourRgbRatio
from ccpn.util.Logging import getLogger


class GLintegralListMethods():
    """Class of methods common to 1d and Nd integrals
    This is added to the Integral Classes below and doesn't require an __init__
    """

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # List handlers
    #   The routines that have to be changed when accessing different named
    #   lists.
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _isSelected(self, integral):
        """return True if the obj in the defined object list
        """
        if getattr(self, '_caching', False):
            if self._objCache is None:
                self._objCache = list(id(obj) for obj in self.current.integrals)  # this is faster than using __eq__
            return id(integral) in self._objCache

        else:
            objs = self.current.integrals
            return integral in objs

    @staticmethod
    def objects(obj):
        """return the integrals attached to the object
        """
        return obj.integrals

    @staticmethod
    def objectList(obj):
        """return the integralList attached to the integral
        """
        return obj.integralList

    @staticmethod
    def listViews(integralList):
        """Return the integralListViews attached to the integralList
        """
        return integralList.integralListViews

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # List specific routines
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    @staticmethod
    def getLabelling(obj, parent=None):
        """get the object label based on the current labelling method
        """
        return obj.id + '\n' + str(obj.value)

    @staticmethod
    def extraIndicesCount(integral):
        """Calculate how many indices to add
        """
        return 0

    @staticmethod
    def appendExtraIndices(*args):
        """Add extra indices to the index list
        """
        return 0, 0

    @staticmethod
    def extraVerticesCount(integral):
        """Calculate how many vertices to add
        """
        return 0

    @staticmethod
    def appendExtraVertices(*args):
        """Add extra vertices to the vertex list
        """
        return 0

    @staticmethod
    def insertExtraIndices(*args):
        """Insert extra indices into the vertex list
        """
        return 0, 0

    @staticmethod
    def insertExtraVertices(*args):
        """Insert extra vertices into the vertex list
        """
        return 0

    def rescaleIntegralLists(self):
        for il in self._GLSymbols.values():
            il._rescale()

    @staticmethod
    def getViewFromListView(integralListView, obj):
        """Get the integralView from the IntegralListView.
        """
        return obj.getIntegralView(integralListView)


#=========================================================================================
# GLintegralNdLabelling
#=========================================================================================

class GLintegralNdLabelling(GL1dLabelling, GLintegralListMethods, GLLabelling):  #, GLpeakNdLabelling):
    """Class to handle symbol and symbol labelling for Nd displays
    """

    # def __init__(self, parent=None, strip=None, name=None, resizeGL=False):
    #     """Initialise the class
    #     """
    #     super(GLintegralNdLabelling, self).__init__(parent=parent, strip=strip, name=name, resizeGL=resizeGL)

    def _updateHighlightedSymbols(self, spectrumView, integralListView):
        drawList = self._GLSymbols[integralListView]
        drawList._rebuild()
        drawList.pushTextArrayVBOColour()

    def _updateHighlightedLabels(self, spectrumView, objListView):
        if objListView not in self._GLLabels:
            return

        drawList = self._GLLabels[objListView]
        strip = self.strip

        # pls = peakListView.peakList
        pls = self.objectList(objListView)

        listCol = getAutoColourRgbRatio(objListView.textColour or GLDefs.DEFAULTCOLOUR,
                                        pls.spectrum, self.autoColour,
                                        getColours()[CCPNGLWIDGET_FOREGROUND])
        meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR,
                                         pls.spectrum, self.autoColour,
                                         getColours()[CCPNGLWIDGET_FOREGROUND])
        meritEnabled = objListView.meritEnabled
        meritThreshold = objListView.meritThreshold

        for drawStr in drawList.stringList:

            obj = drawStr.stringObject

            if obj and not obj.isDeleted:

                if self._isSelected(obj):
                    drawStr.setStringColour((*self._GLParent.highlightColour[:3], GLDefs.INPLANEFADE))
                else:
                    if meritEnabled and obj.figureOfMerit < meritThreshold:
                        cols = meritCol
                    else:
                        cols = listCol
                    drawStr.setStringColour((*cols, GLDefs.INPLANEFADE))

                drawStr.pushTextArrayVBOColour()

    def drawSymbols(self, spectrumSettings, shader=None, stackingMode=True):
        if self.strip.isDeleted:
            return

        self._spectrumSettings = spectrumSettings
        self.buildSymbols()

        # why is this not initialising?
        shader.setMVMatrixToIdentity()

        for integralListView, specView in self._visibleListViews:
            if not integralListView.isDeleted and integralListView in self._GLSymbols.keys():

                # draw the integralAreas if they exist
                for integralArea in self._GLSymbols[integralListView]._regions:
                    if hasattr(integralArea, '_integralArea'):
                        if self._GLParent._stackingMode:
                            # use the stacking matrix to offset the 1D spectra
                            #   - not sure that they are actually drawn in stacking mode
                            shader.setMVMatrix(self._GLParent._spectrumSettings[specView].stackedMatrix)

                        # draw the actual integral areas
                        integralArea._integralArea.drawVertexColorVBO()

        shader.setMVMatrixToIdentity()

    def drawSymbolRegions(self, spectrumSettings):
        if self.strip.isDeleted:
            return

        self._spectrumSettings = spectrumSettings
        self.buildSymbols()

        for integralListView, specView in self._visibleListViews:
            if not integralListView.isDeleted and integralListView in self._GLSymbols.keys():
                # draw the boxes around the highlighted integral areas - multisampling not required here
                self._GLSymbols[integralListView].drawIndexVBO()

        self._GLParent._shaderPixel.setMVMatrixToIdentity()

    def _rescaleLabels(self, spectrumView=None, objListView=None, drawList=None):
        """Rescale all labels to the new dimensions of the screen
        """
        for drawStr in drawList.stringList:
            vertices = drawStr.numVertices

            if vertices:
                # axisIndex is set when creating the labels, based on _flipped
                if drawStr.axisIndex == 0:
                    _font = drawStr.font

                    # top-left of region, bound to top of screen
                    offsets = [drawStr.axisPosition + (3.0 * self._GLParent.pixelX),
                               self._GLParent.axisT - (2 * _font.charHeight * self._GLParent.pixelY),
                               0.0, 0.0]

                else:
                    # bottom-left of region, bound to left of screen - should be top-left of region?
                    offsets = [self._GLParent.axisL + (3.0 * self._GLParent.pixelX),
                               drawStr.axisPosition + (3.0 * self._GLParent.pixelY),
                               0.0, 0.0]

                drawStr.attribs[:] = offsets * vertices

                drawStr.pushTextArrayVBOAttribs()

    def _buildSymbols(self, spectrumView, integralListView):

        if integralListView not in self._GLSymbols:
            self._GLSymbols[integralListView] = GLIntegralRegion(project=self.strip.project,
                                                                 GLContext=self._GLParent,
                                                                 spectrumView=spectrumView,
                                                                 integralListView=integralListView)

        drawList = self._GLSymbols[integralListView]

        if drawList.renderMode == GLRENDERMODE_REBUILD:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode

            drawList.clearArrays()
            drawList._clearRegions()

            ils = integralListView.integralList
            listCol = getAutoColourRgbRatio(integralListView.symbolColour or GLDefs.DEFAULTCOLOUR,
                                            ils.spectrum, self.autoColour,
                                            getColours()[CCPNGLWIDGET_FOREGROUND])
            meritCol = getAutoColourRgbRatio(integralListView.meritColour or GLDefs.DEFAULTCOLOUR,
                                             ils.spectrum, self.autoColour,
                                             getColours()[CCPNGLWIDGET_FOREGROUND])
            meritEnabled = integralListView.meritEnabled
            meritThreshold = integralListView.meritThreshold

            for integral in ils.integrals:
                if meritEnabled and integral.figureOfMerit < meritThreshold:
                    cols = meritCol
                else:
                    cols = listCol

                drawList.addIntegral(integral, integralListView, colour=None,
                                     brush=(*cols, CCPNGLWIDGET_INTEGRALSHADE))

            drawList.defineIndexVBO()

        elif drawList.renderMode == GLRENDERMODE_RESCALE:
            drawList.renderMode = GLRENDERMODE_DRAW  # back to draw mode
            drawList._rebuildIntegralAreas()

            drawList.defineIndexVBO()

    def _deleteSymbol(self, integral, parentList, spectrum):
        for ils in self._GLSymbols.values():

            # if not ils.integralListView.isDeleted and integral.integralList == ils.integralListView.integralList:
            if not ils.integralListView.isDeleted and parentList == ils.integralListView.integralList:

                for reg in ils._regions:

                    if reg._object == integral:
                        ils._regions.remove(reg)
                        try:
                            ils._rebuild()
                        except Exception as es:
                            getLogger.warning(f'   ERROR HERE  {es}')
                        return

    def _createSymbol(self, integral):
        for ils in self._GLSymbols.values():

            if not ils.integralListView.isDeleted and integral.integralList == ils.integralListView.integralList:

                ilv = ils.integralListView
                listCol = getAutoColourRgbRatio(ilv.symbolColour or GLDefs.DEFAULTCOLOUR,
                                                ilv.integralList.spectrum, self._GLParent.SPECTRUMPOSCOLOUR,
                                                getColours()[CCPNGLWIDGET_FOREGROUND])
                meritCol = getAutoColourRgbRatio(ilv.meritColour or GLDefs.DEFAULTCOLOUR,
                                                 ilv.integralList.spectrum, self._GLParent.SPECTRUMPOSCOLOUR,
                                                 getColours()[CCPNGLWIDGET_FOREGROUND])
                meritEnabled = ilv.meritEnabled
                meritThreshold = ilv.meritThreshold
                if meritEnabled and integral.figureOfMerit < meritThreshold:
                    cols = meritCol
                else:
                    cols = listCol

                ils.addIntegral(integral, ilv, colour=None,
                                brush=(*cols, CCPNGLWIDGET_INTEGRALSHADE))
                return

    def _changeSymbol(self, integral):
        """update the vertex list attached to the integral
        """
        for ils in self._GLSymbols.values():
            for reg in ils._regions:
                if reg._object == integral:
                    if hasattr(reg, '_integralArea'):
                        # set the rebuild flag for this region
                        reg._integralArea.renderMode = GLRENDERMODE_REBUILD
                        ils._rebuildIntegralAreas()

                        return

    def _appendLabel(self, spectrumView, objListView, stringList, obj):
        """Append a new label to the end of the list
        """
        # spectrum = spectrumView.spectrum
        # spectrumFrequency = spectrum.spectrometerFrequencies

        # pls = peakListView.peakList
        pls = self.objectList(objListView)
        if stringList and obj in (sl.stringObject for sl in stringList):
            return

        # symbolWidth = self.strip.symbolSize / 2.0

        # get the correct coordinates based on the axisCodes
        p0 = [0.0] * 2  # len(self.axisOrder)
        lims = obj.limits[0] if obj.limits else (0.0, 0.0)

        dims = self._spectrumSettings[spectrumView].dimensionIndices
        for ps, psCode in enumerate(self._GLParent.axisOrder[0:2]):
            for pp, ppCode in enumerate(obj.axisCodes):

                if self._GLParent._preferences.matchAxisCode == 0:  # default - match atom type
                    if ppCode[0] == psCode[0]:

                        # need to put the position in here

                        if self._GLParent.XDIRECTION < 0:
                            p0[ps] = pos = max(lims)  # obj.position[pp]
                        else:
                            p0[ps] = pos = min(lims)  # obj.position[pp]
                    else:
                        p0[ps] = 0.0  #obj.height

                elif self._GLParent._preferences.matchAxisCode == 1:  # match full code
                    if ppCode == psCode:
                        if self._GLParent.XDIRECTION < 0:
                            p0[ps] = pos = max(lims)  # obj.position[pp]
                        else:
                            p0[ps] = pos = min(lims)  # obj.position[pp]
                    else:
                        p0[ps] = 0.0  #obj.height

        if None in p0:
            return

        if self._isSelected(obj):
            cols = self._GLParent.highlightColour[:3]
        else:

            listCol = getAutoColourRgbRatio(objListView.textColour or GLDefs.DEFAULTCOLOUR,
                                            pls.spectrum, self.autoColour,
                                            getColours()[CCPNGLWIDGET_FOREGROUND])
            meritCol = getAutoColourRgbRatio(objListView.meritColour or GLDefs.DEFAULTCOLOUR,
                                             pls.spectrum, self.autoColour,
                                             getColours()[CCPNGLWIDGET_FOREGROUND])
            meritEnabled = objListView.meritEnabled
            meritThreshold = objListView.meritThreshold
            if meritEnabled and obj.figureOfMerit < meritThreshold:
                cols = meritCol
            else:
                cols = listCol

        text = self.getLabelling(obj, self._GLParent)

        smallFont = self._GLParent.getSmallFont()
        if dims[0]:
            # 1D is flipped
            textX = self._GLParent.axisL + 3.0 * self._GLParent.pixelX
            textY = pos or 0.0
        else:
            textX = pos or 0.0 + (3.0 * self._GLParent.pixelX)
            textY = self._GLParent.axisT - (2 * smallFont.charHeight * self._GLParent.pixelY)

        newString = GLString(text=text,
                             font=smallFont,
                             # x=p0[0], y=p0[1],
                             x=textX,
                             y=textY,
                             # ox=symbolWidth, oy=symbolWidth,
                             # x=self._screenZero[0], y=self._screenZero[1]
                             colour=(*cols, 1.0),
                             GLContext=self._GLParent,
                             obj=obj)
        # this is in the attribs
        newString.axisIndex = dims[0]  # still hacking for the minute
        newString.axisPosition = pos or 0.0

        stringList.append(newString)

        # # this is in the attribs
        # stringList[-1].axisIndex = 0
        # stringList[-1].axisPosition = pos or 0.0

    def objIsInVisiblePlanes(self, spectrumView, obj, viewOutOfPlanePeaks=True):
        """Get the current object is in visible planes settings
        """
        return True, False, 0, 1.0


#=========================================================================================
# GLintegral1dLabelling
#=========================================================================================

class GLintegral1dLabelling(GLintegralNdLabelling):
    """Class to handle symbol and symbol labelling for 1d displays
    """
    # 20190607:ED Note, this is not quite correct, but there are no Nd regions yet

    pass

    # def __init__(self, parent=None, strip=None, name=None, resizeGL=False):
    #     """Initialise the class
    #     """
    #     super(GLintegral1dLabelling, self).__init__(parent=parent, strip=strip, name=name, resizeGL=resizeGL)

    def objIsInVisiblePlanes(self, spectrumView, obj, viewOutOfPlanePeaks=True):
        """Get the current object is in visible planes settings
        """
        return True, False, 0, 1.0
