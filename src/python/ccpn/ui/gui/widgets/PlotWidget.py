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
__dateModified__ = "$dateModified: 2024-08-23 19:21:21 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Geerten Vuister"
__date__ = "$Date: 2018-12-20 15:44:35 +0000 (Thu, December 20, 2018) $"
__date__ = "$Date: 2024-08-07 14:49:14 +0000 (Wed, August 07, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

from typing import Sequence

import pyqtgraph as pg
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets, QtOpenGL

from ccpn.ui.gui.widgets.ViewBox import ViewBox
from ccpn.ui.gui.widgets.ViewBox import CrossHair
from ccpn.ui.gui.widgets.CcpnGridItem import CcpnGridItem
from ccpn.ui.gui.lib.mouseEvents import rightMouse
from ccpn.ui.gui.guiSettings import Theme
from ccpn.util.Constants import MOUSEDICTSTRIP
from ccpn.util.Colour import Colour
from ccpnmodel.ccpncore.api.ccpnmr.gui.Task import Ruler as ApiRuler
import pyqtgraph.opengl as gl


#TODO:WAYNE: This class should contain all the nitty-gritty of the displaying; including the axis labels and the like
# as it is only there and is just a small wrapper around a pyqtgraph class
# goes together with AxisTextItem (probably can be reduced to a function and included here.
#TODO:WAYNE: should this inherit from Base??


class PlotWidget(pg.PlotWidget):

    def __init__(self, strip, useOpenGL=False):
        #def __init__(self, strip, useOpenGL=False, showDoubleCrosshair=False):

        # Be sure to use explicit arguments to ViewBox as the call order is different in the __init__
        self.viewBox = ViewBox(strip)
        pg.PlotWidget.__init__(self, parent=strip,
                               viewBox=self.viewBox,
                               axes=None, enableMenu=True)

        self.strip = strip

        self.plotItem.setAcceptHoverEvents(True)
        self.setInteractive(True)
        self.plotItem.setAcceptDrops(True)
        self.plotItem.setMenuEnabled(enableMenu=True, enableViewBoxMenu=False)

        self.rulerLineDict = {}  # ruler --> line for that ruler
        self.rulerLabelDict = {}  # ruler --> label for that ruler

        self.xAxisAtomLabels = []
        self.yAxisAtomLabels = []

        self.xAxisTextItem = None
        self.yAxisTextItem = None

        self.hideButtons()

        if useOpenGL and QtOpenGL.QGLFormat.hasOpenGL():
            # TODO:ED The OpenGL needs to be optimised

            self.setViewport(QtWidgets.QOpenGLWidget())
            # need FullViewportUpdate below, otherwise ND windows do not update when you pan/zoom
            # (BoundingRectViewportUpdate might work if you can implement boundingRect suitably)
            # (NoViewportUpdate might work if you could explicitly get the view to repaint when needed)
            self.setViewportUpdateMode(QtWidgets.QGraphicsView.BoundingRectViewportUpdate)
            # self.setOptimizationFlags(QtWidgets.QGraphicsView.DontSavePainterState)
            # self.setCacheMode(QtWidgets.QGraphicsView.CacheBackground)
            # not sure if these change anything

        # strip.spectrumDisplay.mainWindow._mouseMovedSignal.connect(self._mousePositionChanged)

        #TODO:GEERTEN: Fix with proper stylesheet
        # Also used in AxisTextItem
        # NOTE: self.highlightColour is also being used in GuiPeakListView for selected peaks
        if strip.spectrumDisplay.mainWindow.application._themeStyle == Theme.LIGHT:
            self.background = '#f7ffff'
            self.foreground = '#080000'
            self.gridColour = '#080000'
            self.highlightColour = '#3333ff'
            self._labellingColour = (10, 10, 10)
        else:
            self.background = '#080000'
            self.foreground = '#f7ffff'
            self.gridColour = '#f7ffff'
            self.highlightColour = '#00ff00'
            self._labellingColour = (255, 255, 255)

        self.setBackground(self.background)
        #self.setForeground(self.foreground) # does not seem to have this (or typo?)

        # axes
        self.plotItem.axes['left']['item'].hide()
        self.plotItem.axes['right']['item'].show()
        for orientation in ('left', 'top'):
            axisItem = self.plotItem.axes[orientation]['item']
            axisItem.hide()
        for orientation in ('right', 'bottom'):
            axisItem = self.plotItem.axes[orientation]['item']
            axisItem.setPen(color=self.foreground)
            # axisItem = self.plotItem.axes[orientation]['item']
            # axisItem.hide()

        # add grid
        self.grid = CcpnGridItem(gridColour=self.gridColour)
        self.addItem(self.grid, ignoreBounds=False)

        # Add two crosshairs
        self.crossHair1 = CrossHair(self, show=True, colour=self.foreground)
        self.crossHair2 = CrossHair(self, show=False, colour=self.foreground)

        # add label to show mouse coordinates at the position of the cursor
        self.mouseLabel = pg.TextItem(text='', color=self._labellingColour, anchor=(0, 1))
        self.mouseLabel.hide()
        self.addItem(self.mouseLabel)
        self.mouseLabel.setZValue(1.0)  # brings the item to the top (I assume everything else is 0)

        # add label to show stripID in the top corner
        self.stripIDLabel = pg.TextItem(text='BOX LABEL', color=self._labellingColour)
        self.stripIDLabel.show()
        self.addItem(self.stripIDLabel)
        self.stripIDLabel.setZValue(1.0)

    def highlightAxes(self, state=False):
        "Highlight the axes on/of"
        if state:
            for orientation in ('right', 'bottom'):
                axisItem = self.plotItem.axes[orientation]['item']
                axisItem.setPen(color=self.highlightColour)
                self.stripIDLabel.setColor(color=self.highlightColour)
        else:
            for orientation in ('right', 'bottom'):
                axisItem = self.plotItem.axes[orientation]['item']
                axisItem.setPen(color=self.foreground)
                self.stripIDLabel.setColor(color=self.foreground)

    def toggleGrid(self):
        "Toggle grid state"
        newState = not self.grid.isVisible()
        self.grid.setVisible(not self.grid.isVisible())

    # def cycleSymbolLabelling(self):
    #   "Toggle grid state"
    #   self.symbolLabelling = not self.symbolLabelling
    # TODO:ED update peaks here

    def __getattr__(self, attr):
        """
        Wrap pyqtgraph PlotWidget __getattr__, which raises wrong error and so makes hasattr fail.
        """
        try:
            return super().__getattr__(attr)
        except NameError:
            raise AttributeError(attr)

    def addItem(self, item: QtWidgets.QGraphicsObject):
        """
        Adds specified graphics object to the Graphics Scene of the PlotWidget.
        """
        self.scene().addItem(item)

    # copied from GuiStripNd!
    def _mouseDragEvent(self, event):
        """
        Re-implemented mouse event to enable smooth panning.
        """
        if rightMouse(event):
            pass
        else:
            self.viewBox.mouseDragEvent(self, event)

    def _crosshairCode(self, axisCode):
        # determines what axisCodes are compatible as far as drawing crosshair is concerned
        # TBD: the naive approach below should be improved
        return axisCode  # if axisCode[0].isupper() else axisCode

    @QtCore.pyqtSlot(dict)
    def _mousePositionChanged(self, mouseMovedDict):
        """
          This is called when the mouse position is changed in some strip
          It means the crosshair(s) position should be updated
        :param mouseMovedDict: 'strip'->strip and axisCode->position for each axisCode in strip
        :return:  None
        """
        strip = self.strip
        if strip.isDeleted: return

        axes = strip.orderedAxes

        # TODO:ED sometimes set to None
        if not axes[0] or not axes[1]:
            return

        xPos = mouseMovedDict.get(self._crosshairCode(axes[0].code))
        yPos = mouseMovedDict.get(self._crosshairCode(axes[1].code))
        #print('>>', strip, xPos, yPos)
        self.crossHair1.setPosition(xPos, yPos)

        strip.axisPositionDict[axes[0].code] = xPos
        strip.axisPositionDict[axes[1].code] = yPos

        #TODO:SOLIDS This is clearly not correct; it should take the offset as defined for spectrum
        #xPos = mouseMovedDict.get(self._crosshairCode(axes[1].code))
        #yPos = mouseMovedDict.get(self._crosshairCode(axes[0].code))
        #self.crossHair2.setPosition(xPos, yPos)
        if strip.spectra:
            spectrumView = strip.spectrumViews[0]  # use the first spectrum
            spectrum = spectrumView.spectrum
            if spectrum.showDoubleCrosshair:
                #if strip.spectrumDisplay.mainWindow.application.preferences.general.doubleCrossHair:
                offsets = spectrum.doubleCrosshairOffsets
                displayIndices = spectrumView.dimensionIndices
                xOffset = offsets[displayIndices[0]]
                yOffset = offsets[displayIndices[1]]
                if xPos is None or xOffset == 0:
                    self.crossHair2.vLine.hide()
                else:
                    # TBD: below assumes that axis is in ppm
                    xOffset /= spectrum.spectrometerFrequencies[displayIndices[0]]  # convert from Hz to ppm
                    self.crossHair2.setVline(xPos + xOffset)
                    self.crossHair2.vLine.show()
                if yPos is None or yOffset == 0:
                    self.crossHair2.hLine.hide()
                else:
                    # TBD: below assumes that axis is in ppm
                    yOffset /= spectrum.spectrometerFrequencies[displayIndices[1]]  # convert from Hz to ppm
                    self.crossHair2.setHline(yPos + yOffset)
                    self.crossHair2.hLine.show()

        if self.strip != mouseMovedDict[MOUSEDICTSTRIP]:
            # hide the mouse label if the event comes form a different window
            self.mouseLabel.hide()

    # NBNB TODO code uses API object. REFACTOR

    def _addRulerLine(self, apiRuler: ApiRuler):
        """CCPN internal
           Called from GuiStrip when a ruler is created
           This adds a line into the PlotWidget"""

        axisCode = apiRuler.axisCode  # TODO: use label and unit
        position = apiRuler.position
        label = apiRuler.label
        if apiRuler.mark.colour[0] == '#':  # TODO: why this restriction???
            colour = Colour(apiRuler.mark.colour)  # TODO: this is a CCPN object, does it work to set pen=colour below
        else:
            colour = self.foreground
        strip = self.strip
        axisOrder = strip.axisOrder

        # TODO: is the below correct (so the correct axes)?
        if axisCode == axisOrder[0]:
            angle = 90
            y = self.plotItem.vb.mapSceneToView(strip.viewBox.boundingRect().bottomLeft()).y()
            textPosition = (position, y)
            textAnchor = 1
            labels = self.xAxisAtomLabels
        elif axisCode == axisOrder[1]:
            angle = 0
            x = strip.plotWidget.plotItem.vb.mapSceneToView(strip.viewBox.boundingRect().bottomLeft()).x()
            textPosition = (x, position)
            textAnchor = 0
            labels = self.yAxisAtomLabels
        else:
            return

        line = pg.InfiniteLine(angle=angle, movable=False, pen=colour)
        line.setPos(position)
        self.addItem(line, ignoreBounds=True)
        self.rulerLineDict[apiRuler] = line
        if label:
            textItem = pg.TextItem(label, color=colour)
            textItem.anchor = pg.Point(0, textAnchor)
            textItem.setPos(*textPosition)
            self.addItem(textItem)
            labels.append(textItem)
            self.rulerLabelDict[apiRuler] = textItem

    def _removeRulerLine(self, apiRuler: ApiRuler):
        """CCPN internal
           Called from GuiStrip when a ruler is deleted
           This removes a line into the PlotWidget"""

        if apiRuler in self.rulerLineDict:
            line = self.rulerLineDict.pop(apiRuler)
            self.removeItem(line)
        if apiRuler in self.rulerLabelDict:
            label = self.rulerLabelDict.pop(apiRuler)
            self.removeItem(label)

    # TODO:WAYNE: Make this part of PlotWidget [done], pass axes label strings on init [??]
    def _moveAxisCodeLabels(self):
        """CCPN internal
           Called from a notifier in GuiStrip
           Puts axis code labels in the correct place on the PlotWidget
        """
        return

        self.xAxisTextItem.setPos(self.viewBox.boundingRect().bottomLeft())
        self.yAxisTextItem.setPos(self.viewBox.boundingRect().topRight())
        for item in self.xAxisAtomLabels:
            y = self.plotItem.vb.mapSceneToView(self.strip.viewBox.boundingRect().bottomLeft()).y()
            x = item.pos().x()
            item.setPos(x, y)
        for item in self.yAxisAtomLabels:
            x = self.plotItem.vb.mapSceneToView(self.strip.viewBox.boundingRect().bottomLeft()).x()
            y = item.pos().y()
            item.setPos(x, y)

        # ejb - move the stripIDLabel to be fixed in the top-left corner if the plotWidget
        k = self.strip.viewBox.boundingRect().topLeft()
        self.stripIDLabel.setPos(self.plotItem.vb.mapSceneToView(k).x(),
                                 self.plotItem.vb.mapSceneToView(k).y())

    def _initTextItems(self):
        """CCPN internal
           Called from GuiStrip when axes are ready
        """
        axisOrder = self.strip.axisOrder
        self.xAxisTextItem = AxisTextItem(self, orientation='top', axisCode=axisOrder[0])
        self.yAxisTextItem = AxisTextItem(self, orientation='left', axisCode=axisOrder[1])

    # TODO:ED this does override but acnnot change the zoom centre
    # def wheelEvent(self, ev, axis=None):
    #   mask = np.array(self.state['mouseEnabled'], dtype=np.float)
    #   if axis is not None and axis >= 0 and axis < len(mask):
    #     mv = mask[axis]
    #     mask[:] = 0
    #     mask[axis] = mv
    #   s = ((mask * 0.02) + 1) ** (
    #       ev.delta() * self.state['wheelScaleFactor'])  # actual scaling factor
    #
    #   center = None   # Point(fn.invertQTransform(self.childGroup.transform()).map(ev.pos()))
    #   # center = ev.pos()
    #
    #   self._resetTarget()
    #   self.scaleBy(s, center)
    #   self.sigRangeChangedManually.emit(self.state['mouseEnabled'])
    #   ev.accept()


class AxisTextItem(pg.TextItem):

    def __init__(self, plotWidget, orientation, axisCode=None, units=None, mappedDim=None):

        self.plotWidget = plotWidget
        self.orientation = orientation
        self.axisCode = axisCode
        self.units = units
        self.mappedDim = mappedDim
        pg.TextItem.__init__(self, text=axisCode, color=plotWidget.gridColour)
        if orientation == 'top':
            self.setPos(plotWidget.plotItem.vb.boundingRect().bottomLeft())
            self.anchor = pg.Point(0, 1)
        else:
            self.setPos(plotWidget.plotItem.vb.boundingRect().topRight())
            self.anchor = pg.Point(1, 0)
        plotWidget.scene().addItem(self)

    def _setUnits(self, units):
        self.units = units

    def _setAxisCode(self, axisCode):
        self.axisCode = str(axisCode)
