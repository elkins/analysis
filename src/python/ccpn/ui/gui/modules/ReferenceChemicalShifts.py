"""
Module documentation here
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
__dateModified__ = "$dateModified: 2024-08-23 19:21:55 +0100 (Fri, August 23, 2024) $"
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
from functools import partial
import pyqtgraph as pg
from ccpn.ui.gui.guiSettings import (CCPNGLWIDGET_HIGHLIGHT, CCPNGLWIDGET_LABELLING,
                                     getColours, CCPNGLWIDGET_HEXBACKGROUND,
                                     CCPNGLWIDGET_HEXFOREGROUND)
from ccpn.ui.gui.widgets.Font import Font, getFont
# from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import PaintModes
from PyQt5 import QtWidgets, QtCore, QtGui
from ccpn.core.lib.AssignmentLib import CCP_CODES
from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.widgets.Label import Label, DividerLabel
from ccpn.ui.gui.widgets.PulldownList import PulldownList
# from ccpn.util.Colour import spectrumHexDarkColours, spectrumHexLightColours
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.ToolBar import ToolBar
from ccpn.ui.gui.widgets.Action import Action
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.Icon import Icon
# from ccpn.ui.gui.widgets.ListWidget import ListWidget
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLNotifier import GLNotifier
from ccpn.core.lib.Notifiers import Notifier
from collections import defaultdict
from ccpn.util.Colour import rgbaRatioToHex
from ccpn.AnalysisAssign.modules.NmrAtomAssigner import BACKBONEATOMS
from ccpn.util.isotopes import name2IsotopeCode
from ccpn.ui.gui.widgets.MessageDialog import progressManager


CCPCODES = sorted(CCP_CODES)

Hydrogen = 'Hydrogen'
Heavy = 'Heavy'
Other = 'Other'
H = 'H'
Backbone = 'Backbone'
SideChain = 'SideChain'
All = 'All'
H_ISOTOPECODES = ['1H', '2H', '3H']

CurveColours4LightDisplay = {'C'   : '#2b2a07',  ## BB
                             'CA'  : '#0c37f7',  ## BB
                             'CB'  : '#f70505',  ## BB
                             'CD'  : '#424242',
                             'CD1' : '#693737',
                             'CD2' : '#CD5C5C',
                             'CE'  : '#A52A2A',
                             'CE1' : '#B22222',
                             'CE2' : '#800000',
                             'CE3' : '#8B0000',
                             'CG'  : '#FF0000',
                             'CG1' : '#FA8072',
                             'CG2' : '#FF6347',
                             'CH2' : '#E9967A',
                             'CZ'  : '#FF7F50',
                             'CZ2' : '#FF4500',
                             'CZ3' : '#FFA07A',
                             'H'   : '#290f04',
                             'HA'  : '#23a634',  ## BB
                             'HA2' : '#8B4513',
                             'HA3' : '#F4A460',
                             'HB'  : '#802382',  ## BB
                             'HB*' : '#FF8C00',
                             'HB2' : '#DEB887',
                             'HB3' : '#D2B48C',
                             'HD1' : '#FFA500',
                             'HD1*': '#B8860B',
                             'HD2' : '#DAA520',
                             'HD2*': '#BDB76B',
                             'HD21': '#808000',
                             'HD22': '#6B8E23',
                             'HD3' : '#9ACD32',
                             'HE'  : '#556B2F',
                             'HE*' : '#228B22',
                             'HE1' : '#32CD32',
                             'HE2' : '#006400',
                             'HE21': '#008000',
                             'HE22': '#2E8B57',
                             'HE3' : '#3CB371',
                             'HG'  : '#66CDAA',
                             'HG1' : '#20B2AA',
                             'HG1*': '#48D1CC',
                             'HG12': '#2F4F4F',
                             'HG13': '#008080',
                             'HG2' : '#008B8B',
                             'HG2*': '#00CED1',
                             'HG3' : '#5F9EA0',
                             'HH'  : '#00BFFF',
                             'HH11': '#4682B4',
                             'HH12': '#1E90FF',
                             'HH2' : '#6495ED',
                             'HH21': '#4169E1',
                             'HH22': '#191970',
                             'HZ'  : '#000080',
                             'HZ*' : '#00008B',
                             'HZ2' : '#0000CD',
                             'HZ3' : '#0000FF',
                             'N'   : '#167311',  ## BB
                             'ND1' : '#483D8B',
                             'ND2' : '#7B68EE',
                             'NE'  : '#9370DB',
                             'NE1' : '#663399',
                             'NE2' : '#8A2BE2',
                             'NH1' : '#4B0082',
                             'NH2' : '#9932CC',
                             'NZ'  : '#9400D3',
                             }

CurveColours4DarkDisplay = {'C'   : '#b0f7ee',  ## BB
                            'CA'  : '#a6c8f5',  ## BB
                            'CB'  : '#a1f598',  ## BB
                            'CD'  : '#d5f2f7',
                            'CD1' : '#8fadb3',
                            'CD2' : '#DCDCDC',
                            'CE'  : '#F5F5F5',
                            'CE1' : '#FFFFFF',
                            'CE2' : '#F08080',
                            'CE3' : '#CD5C5C',
                            'CG'  : '#FF0000',
                            'CG1' : '#FA8072',
                            'CG2' : '#FF6347',
                            'CH2' : '#E9967A',
                            'CZ'  : '#FF7F50',
                            'CZ2' : '#FF4500',
                            'CZ3' : '#FFA07A',
                            'H'   : '#e8e4e3',  ##BB
                            'HA'  : '#a5abf2',  ##BB
                            'HA2' : '#8B4513',
                            'HA3' : '#F4A460',
                            'HB'  : '#fae769',  ##BB
                            'HB*' : '#FF8C00',
                            'HB2' : '#DEB887',
                            'HB3' : '#D2B48C',
                            'HD1' : '#FFDEAD',
                            'HD1*': '#FFA500',
                            'HD2' : '#B8860B',
                            'HD2*': '#DAA520',
                            'HD21': '#FFD700',
                            'HD22': '#F0E68C',
                            'HD3' : '#BDB76B',
                            'HE'  : '#808000',
                            'HE*' : '#FFFF00',
                            'HE1' : '#6B8E23',
                            'HE2' : '#9ACD32',
                            'HE21': '#556B2F',
                            'HE22': '#ADFF2F',
                            'HE3' : '#7FFF00',
                            'HG'  : '#7CFC00',
                            'HG1' : '#98FB98',
                            'HG1*': '#90EE90',
                            'HG12': '#228B22',
                            'HG13': '#32CD32',
                            'HG2' : '#008000',
                            'HG2*': '#00FF00',
                            'HG3' : '#2E8B57',
                            'HH'  : '#3CB371',
                            'HH11': '#00FF7F',
                            'HH12': '#00FA9A',
                            'HH2' : '#66CDAA',
                            'HH21': '#7FFFD4',
                            'HH22': '#40E0D0',
                            'HZ'  : '#20B2AA',
                            'HZ*' : '#48D1CC',
                            'HZ2' : '#008080',
                            'HZ3' : '#008B8B',
                            'N'   : '#9ca899',  ##BB
                            'ND1' : '#00CED1',
                            'ND2' : '#5F9EA0',
                            'NE'  : '#00BFFF',
                            'NE1' : '#87CEEB',
                            'NE2' : '#87CEFA',
                            'NH1' : '#4682B4',
                            'NH2' : '#1E90FF',
                            'NZ'  : '#6495ED', }

_ITEMDATA = '_itemData'
_CURRENTCOLOUR = '_currentColour'
_GRIDPEN = '_gridPen'
_GRIDCOLOUR = 'gridColour'


class ReferenceChemicalShifts(CcpnModule):  # DropBase needs to be first, else the drop events are not processed

    includeSettingsWidget = False
    maxSettingsState = 2
    settingsPosition = 'top'
    className = 'ReferenceChemicalShifts'

    def __init__(self, mainWindow, name='Reference Chemical Shifts', ):
        super().__init__(mainWindow=mainWindow, name=name)

        self.preferences = self.mainWindow.application.preferences

        self.mainWindow = mainWindow
        self.current = self.mainWindow.current
        self.project = self.mainWindow.project
        self.displayedAxisCodes = defaultdict(list)
        self._backboneAtoms = set()
        self._sideChainAtoms = set()
        self.lines = []
        self.currentColour = rgbaRatioToHex(*getColours()[CCPNGLWIDGET_HIGHLIGHT])
        self.gridColour = rgbaRatioToHex(*getColours()[CCPNGLWIDGET_LABELLING])
        self.gridPen = pg.functions.mkPen(self.gridColour, width=1, style=QtCore.Qt.SolidLine)
        self.backgroundColour = getColours()[CCPNGLWIDGET_HEXBACKGROUND]
        self.gridFont = getFont()

        self._RCwidgetFrame = Frame(self.mainWidget, setLayout=True,
                                    grid=(0, 0), gridSpan=(1, 1),
                                    hPolicy='ignored'
                                    )

        self._RCwidget = Frame(self._RCwidgetFrame, setLayout=True,
                               grid=(0, 0), gridSpan=(1, 1),
                               hAlign='l', margins=(5, 5, 5, 5))
        self._TBFrame = Frame(self._RCwidgetFrame, setLayout=True,
                              grid=(1, 0), gridSpan=(1, 1),
                              hAlign='l', margins=(5, 5, 5, 5))

        self._RCwidget.getLayout().setSizeConstraint(QtWidgets.QLayout.SetMinAndMaxSize)
        col = 0
        self.residueTypeLabel = Label(self._RCwidget, "Residue Type:", grid=(0, col))
        col += 1
        self.residueTypePulldown = PulldownList(self._RCwidget, index=1, callback=self._updateModule, hAlign='l',
                                                grid=(0, col))
        ccpnCodes = [All] + CCPCODES
        self.residueTypePulldown.setData(ccpnCodes)
        col += 1
        self.atomTypeLabel = Label(self._RCwidget, 'Atom Type:', grid=(0, col))
        col += 1
        self.atomTypeRadioButtons = RadioButtons(self._RCwidget, texts=[Hydrogen, Heavy],
                                                 callback=self._updateModule, selectedInd=1, grid=(0, col))
        col += 1
        DividerLabel(self._RCwidget, hAlign='l', grid=(0, col))

        col += 1
        Label(self._RCwidget, 'Atom Selection', grid=(0, col))
        col += 1
        self.atomOptionsRadioButtons = RadioButtons(self._RCwidget, texts=[Backbone, SideChain, All],
                                                    callback=self._updateModule, selectedInd=0, grid=(0, col))
        col += 1
        DividerLabel(self._RCwidget, hAlign='l', grid=(0, col))
        col += 1

        self.zoomAllButton = Button(self._RCwidget, icon=Icon('icons/zoom-full'), tipText='Reset zoom',
                                    callback=self._zoomAllCallback, hAlign='l', grid=(0, col))
        self.zoomAllButton.setFixedSize(25, 25)

        self.toolBar = ToolBar(self._TBFrame, grid=(0, 0))
        self.maxDimensionLines = 7

        self.plotWidget = pg.PlotWidget(background=self.backgroundColour)
        self.plotWidget.invertX()
        self.mainWidget.getLayout().addWidget(self.plotWidget, 2, 0, 1, 1)

        self.plots = {}
        self._setupPlot()

        # crosshair
        # create in advance line based on spectral dimensions up to maxDimensionLines (7)

        for i in range(1, self.maxDimensionLines):
            line = pg.InfiniteLine(angle=90, label='', movable=False, pen=self.gridPen,
                                   labelOpts={'color'   : self.currentColour,
                                              'position': 0.1,
                                              'anchors' : [0, 0.5],
                                              'border'  : self.currentColour,
                                              # 'fill':self.currentColour
                                              },
                                   name=str(i))
            setattr(line, _ITEMDATA, _CURRENTCOLOUR)
            self.plotWidget.addItem(line, ignoreBounds=True, )
            self.lines.append(line)
            line.hide()
        self.viewBox = self.plotWidget.plotItem.vb
        self.plotWidget.scene().sigMouseMoved.connect(self.mouseMoved)
        self.plotWidget.plotItem.autoBtn.setOpacity(0.0)
        self.plotWidget.plotItem.autoBtn.enabled = False
        self.viewBox.setMenuEnabled(enableMenu=False)

        # GL crossHair notifier
        self.mousePosNotifier = Notifier(self.current,
                                         [Notifier.CURRENT],
                                         targetName='cursorPositions',
                                         callback=self.mousePosNotifierCallback,
                                         onceOnly=True)
        self.GLSignals = GLNotifier(parent=self, strip=None)
        with progressManager(self, f'Loading all available reference spectra. Please wait...'):
            self._updateModule()

        QtWidgets.QApplication.instance()._sigPaletteChanged.connect(self._checkPalette)

    def _checkPalette(self, pal: QtGui.QPalette, *args):
        """Update the colour-palette in response to application theme change."""
        pw = self.plotWidget
        self.currentColour = rgbaRatioToHex(*getColours()[CCPNGLWIDGET_HIGHLIGHT])
        self.gridColour = rgbaRatioToHex(*getColours()[CCPNGLWIDGET_LABELLING])
        self.gridPen = pg.functions.mkPen(self.gridColour, width=1, style=QtCore.Qt.SolidLine)
        self.backgroundColour = getColours()[CCPNGLWIDGET_HEXBACKGROUND]
        pw.setBackground(self.backgroundColour)
        foreground = QtGui.QColor(getColours()[CCPNGLWIDGET_HEXFOREGROUND])
        # Set foreground color for text, axes, and grid
        pw.getAxis('left').setPen(foreground)
        pw.getAxis('bottom').setPen(foreground)
        pw.getAxis('left').setTextPen(foreground)
        pw.getAxis('bottom').setTextPen(foreground)

        colDict = {_GRIDCOLOUR   : self.gridColour,
                   _GRIDPEN      : self.gridColour,
                   _CURRENTCOLOUR: self.currentColour}
        self._updateModule()
        plotItem = pw.getPlotItem()
        for itm in plotItem.items:
            if (colName := getattr(itm, _ITEMDATA, None)) in {_GRIDPEN, _GRIDCOLOUR, _CURRENTCOLOUR}:
                col = colDict.get(colName)[:7]
                if isinstance(itm, pg.TextItem):
                    itm.setColor(QtGui.QColor(col))
                elif isinstance(itm, pg.InfiniteLine):
                    itm.setPen(QtGui.QColor(col))
                    # set label colour and border
                    label = itm.label
                    label.setColor(QtGui.QColor(col))
                    # this is a bit of a hack - doesn't seem to be a method to change
                    label.border = pg.functions.mkPen(QtGui.QColor(col))
        self.update()

    def _toggleByAtom(self):
        """Toggle spectra if the atom name is in Backbone atoms.
         Very ugly implemented but  all module should be replaced sooner than later... """
        value = self.atomOptionsRadioButtons.get()

        for item in self.viewBox.addedItems:

            atomName = getattr(item, 'atomName', None)
            if atomName:
                if value == Backbone:
                    item.setVisible(atomName in self._backboneAtoms)

                if value == SideChain:
                    item.setVisible(atomName in self._sideChainAtoms)

        for action in self.toolBar.actions():
            if value == Backbone:
                action.setChecked(action.objectName() in self._backboneAtoms)
            if value == SideChain:
                action.setChecked(action.objectName() in self._sideChainAtoms)

        if value == All:
            for item in self.viewBox.addedItems:
                item.setVisible(True)
            for action in self.toolBar.actions():
                action.setChecked(True)

    def _zoomAllCallback(self):
        self.plotWidget.plotItem.autoRange()

    def mousePosNotifierCallback(self, *args):
        """Set the vertical line based on current cursor position """
        self._hideLines()
        axisCodeDict = self.current.mouseMovedDict.get(0, {'': []})
        positions = {}
        atomType = self.atomTypeRadioButtons.get()
        for isotName, glCursorPositions in axisCodeDict.items():
            if atomType == Heavy and isotName in H_ISOTOPECODES:
                continue
            if atomType == Hydrogen and isotName not in H_ISOTOPECODES:
                continue
            for glCursorPosition in glCursorPositions:
                positions.update({glCursorPosition: isotName})

        if len(positions) < 1:
            return
        lines = self.lines[:len(positions)]

        for line, (position, isoName) in zip(lines, positions.items()):
            line.setPos(position)
            line.label.setText(f'{isoName}: {str(round(position, 3))}')
            line.show()

    def _getFirstLine(self):
        if len(self.lines) > 0:
            return self.lines[0]

    def _hideLines(self):
        for l in self.lines:
            l.hide()

    def mouseMoved(self, event):
        line = self._getFirstLine()
        if not line:
            return
        self._hideLines()
        line.show()

        position = event
        mousePoint = self.viewBox.mapSceneToView(position)
        x = mousePoint.x()
        # y = mousePoint.y()
        line.setPos(x)
        line.label.setText(str(round(x, 3)))
        atomPosDict = defaultdict(list)
        isotopeCodePosDict = defaultdict(list)
        ## find the item under the cursor position
        for item in self.viewBox.addedItems:
            if hasattr(item, 'getData') and hasattr(item, 'atomName'):
                xData, yData = item.getData()
                xDataMin, xDataMax = np.min(xData), np.max(xData)
                if (x > xDataMin) & (x < xDataMax):
                    atomPosDict[item.atomName].append(x)
                    isotope = name2IsotopeCode(item.atomName)
                    isotopeCodePosDict[isotope].append(x)

        mouseMovedDict = {0: isotopeCodePosDict,
                          1: atomPosDict}

        self.current.mouseMovedDict = mouseMovedDict
        self.GLSignals._emitMouseMoved(source=None, coords=None, mouseMovedDict=mouseMovedDict,
                                       mainWindow=self.mainWindow)

    def clearPlot(self):
        """ Clear plot but keep infinite lines"""
        for item in self.viewBox.addedItems:
            if not isinstance(item, pg.InfiniteLine):
                self.viewBox.removeItem(item)

        for ch in self.viewBox.childGroup.childItems():
            if not isinstance(ch, pg.InfiniteLine):
                self.viewBox.removeItem(ch)

    def _setupPlot(self):

        baxis = self.plotWidget.plotItem.getAxis('bottom')
        baxis.tickFont = self.gridFont
        baxis.setPen(self.gridPen)
        baxis.setLabel('[ppm]')
        lAxis = self.plotWidget.plotItem.getAxis('left')
        lAxis.setStyle(tickLength=0, showValues=False)
        lAxis.setLabel(' ')
        lAxis.setPen(self.gridPen)
        self.plotWidget.showGrid(x=False, y=False)

    def _getDistributionForResidue(self, ccpCode: str, atomType: str):
        """
        Takes a ccpCode and an atom type (Hydrogen or Heavy) and returns a dictionary of lists
        containing the chemical shift distribution for each atom of the specified type in the residue
        """
        dataSets = {}
        ccpData = self.project.getCcpCodeData(ccpCode, molType='protein', atomType=atomType)

        atomNames = list(ccpData.keys())

        for atomName in atomNames:
            distribution = ccpData[atomName].distribution
            refPoint = ccpData[atomName].refPoint
            refValue = ccpData[atomName].refValue
            valuePerPoint = ccpData[atomName].valuePerPoint
            x = []
            y = []
            # get the spectrumDisplay colour theme
            if self.preferences.general.colourScheme == 'dark':
                colour = CurveColours4DarkDisplay.get(atomName, '#f4f4f4')
            elif self.preferences.general.colourScheme == 'light':
                colour = CurveColours4LightDisplay.get(atomName, '#060606')
            else:
                # get the appearance->style colour-scheme
                if self.preferences.appearance.themeStyle == 'dark':
                    colour = CurveColours4DarkDisplay.get(atomName, '#f4f4f4')
                else:
                    colour = CurveColours4LightDisplay.get(atomName, '#060606')
            for i in range(len(distribution)):
                x.append(refValue + valuePerPoint * (i - refPoint))
                y.append(distribution[i])

            dataSets[atomName] = [np.array(x), np.array(y), colour, ]
            self.displayedAxisCodes[atomName[0]].append(atomName)
            if atomName in BACKBONEATOMS:
                self._backboneAtoms.add(atomName)
            else:
                self._sideChainAtoms.add(atomName)

        return dataSets

    def _addBaseline(self, atomType, offset, ccpCode):
        maxBaseline = 20 if atomType == Hydrogen else 300
        xBaseline = np.arange(0, maxBaseline)
        yBaseline = np.array([offset] * len(xBaseline))
        baselinePlot = self.plotWidget.plot(xBaseline, yBaseline, name=ccpCode, pen=self.gridPen)
        setattr(baselinePlot, _ITEMDATA, _GRIDPEN)
        return baselinePlot

    def _showAllResidues(self, offset=0.175):
        """
        """
        self.clearPlot()
        self.plots = {}
        self.toolBar.clear()
        self.displayedAxisCodes.clear()
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.plotWidget.showGrid(x=False, y=False)
        atomType = self.atomTypeRadioButtons.get()
        initialOffset = 0
        for i, ccpCode in enumerate(CCPCODES):
            dataSets = self._getDistributionForResidue(ccpCode, atomType)
            resCurves = []
            textItems = []
            baselinePlot = self._addBaseline(atomType, initialOffset, ccpCode)
            for atomName, dataSet in dataSets.items():
                xs = dataSet[0]
                ys = dataSet[1] + initialOffset
                color = dataSet[2]
                plotPen = pg.functions.mkPen(color, width=2, style=QtCore.Qt.SolidLine)
                plot = self.plotWidget.plot(xs, ys, pen=plotPen, name=atomName)
                plot.atomName = atomName
                anchor = (-0.3, 0.5)  # try to don't overlap labels
                textItem = pg.TextItem(atomName, color=color, anchor=anchor, angle=0)
                labelY = max(ys)
                labelposXs = xs[ys == labelY]
                labelX = labelposXs[0]
                textItem.setPos(labelX, labelY + (np.random.random() * 0.01))
                textItems.append(textItem)
                textItem.atomName = atomName
                resCurves.append(plot)
                self.plots.update({atomName: plot})
                self.plotWidget.addItem(textItem)

            ccpCodeTextItem = pg.TextItem(ccpCode, color=self.gridColour, angle=0, anchor=(-0.1, 0.5))
            ccpCodeTextItem.setPos(0, initialOffset)
            setattr(ccpCodeTextItem, _ITEMDATA, _GRIDCOLOUR)
            self.plotWidget.addItem(ccpCodeTextItem)

            action = Action(self, text=ccpCode,
                            callback=partial(self.residueToolbarActionCallback, resCurves, textItems, ccpCodeTextItem,
                                             baselinePlot),
                            checked=True, shortcut=None, checkable=True)
            action.setObjectName(ccpCode)
            action.setIconText(ccpCode)
            self.toolBar.addAction(action)
            widgetAction = self.toolBar.widgetForAction(action)
            widgetAction.setFixedSize(55, 30)
            self._styleSheet = """
                                /*  currentField is a property on the widgetAction
                                    that can be set to True to enable a highlighted border;
                                    otherwise defaults to the standard 'checked'
                                    section of the stylesheet.
                                    There are not many colouirs available in the palette;
                                    this uses a qlineargradient to pick a small range
                                    between window-colour and medium-grey.
                                    This is theme-agnostic, picks a shade always slightly lighter or
                                    darker than the current background.
                                    [(x1, y1), (x2, y2)] define the box over which the gradient is applied.
                                    The widget is interpolated from [(0, 0), (1, 1)] in this box.
                                    start, stop are normalised points for setting multiple colours in the gradient.
                                */
                                
                                QToolButton {
                                    color: palette(dark);
                                    padding: 0px;
                                }
                                QToolButton:checked[currentField=true] {
                                    color: palette(text);
                                    border: 0.5px solid palette(highlight);
                                    border-radius: 2px;
                                    background-color: qlineargradient(
                                                            x1: 0, y1: -1, x2: 0, y2: 6,
                                                            stop: 0 palette(window), stop: 1 #808080
                                                        );
                                }
                                QToolButton:checked {
                                    color: palette(text);
                                    border: 0.5px solid palette(dark);
                                    border-radius: 2px;
                                    background-color: qlineargradient(
                                                            x1: 0, y1: -1, x2: 0, y2: 6,
                                                            stop: 0 palette(window), stop: 1 #808080
                                                        );
                                }
                                """
            widgetAction.setStyleSheet(self._styleSheet)
            initialOffset += offset

        self._zoomAllCallback()
        self._toggleByAtom()
        for action in self.toolBar.actions():
            action.setChecked(True)

    def _updateModule(self, item=None):
        """
        Updates the information displayed in the module when either the residue type or the atom type
        selectors are changed.
        """
        self.viewBox._updatingRange = True

        ccpCode = self.residueTypePulldown.currentText()
        if ccpCode == All:
            self._showAllResidues()
            return
        atomType = self.atomTypeRadioButtons.get()
        self.clearPlot()
        self.plots = {}
        self.toolBar.clear()
        self.displayedAxisCodes.clear()
        self.plotWidget.showGrid(x=False, y=False)
        dataSets = self._getDistributionForResidue(ccpCode, atomType)
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        sortedAtomNames = sorted(dataSets.keys(), key=lambda x: x.lower())
        self._addBaseline(atomType, 0, ccpCode)
        for atomName in sortedAtomNames:
            dataSet = dataSets[atomName]
            xs = dataSet[0]
            ys = dataSet[1]
            color = dataSet[2]
            plotPen = pg.functions.mkPen(color, width=2, style=QtCore.Qt.SolidLine)
            plot = self.plotWidget.plot(xs, ys, pen=plotPen, name=atomName)
            plot.atomName = atomName
            anchor = (-0.3, 0.5)  # try to don't overlap labels
            textItem = pg.TextItem(atomName, color=color, anchor=anchor, angle=0, border='w', )
            labelY = max(ys)
            labelposXs = xs[ys == labelY]
            labelX = labelposXs[0]
            textItem.setPos(labelX, labelY + (np.random.random() * 0.01))
            textItem.atomName = atomName

            self.plots.update({atomName: plot})
            action = Action(self, text=atomName, callback=partial(self.toolbarActionCallback, plot, textItem),
                            checked=True, shortcut=None, checkable=True)
            action.setObjectName(atomName)
            action.setIconText(atomName)
            pixmap = QtGui.QPixmap(20, 5)
            pixmap.fill(QtGui.QColor(color))
            action.setIcon(QtGui.QIcon(pixmap))
            self.toolBar.addAction(action)
            self.plotWidget.addItem(textItem)
            widgetAction = self.toolBar.widgetForAction(action)
            widgetAction.setFixedSize(55, 30)
        self._zoomAllCallback()
        self._toggleByAtom()
        self.viewBox._updatingRange = False

    def residueToolbarActionCallback(self, plotItems, textItems, ccpCodeTextItem, baselinePlot):
        checked = self.sender().isChecked()
        for plotItem, textItem in zip(plotItems, textItems):
            if plotItem:
                # Need to check if is in backBone
                value = self.atomOptionsRadioButtons.get()
                atomName = getattr(plotItem, 'atomName', None)
                if atomName:
                    if value == Backbone:
                        if atomName in self._backboneAtoms:
                            plotItem.setVisible(checked)
                            textItem.setVisible(checked)

                    if value == SideChain:
                        if atomName in self._sideChainAtoms:
                            plotItem.setVisible(checked)
                            textItem.setVisible(checked)
                    else:
                        plotItem.setVisible(checked)
                        textItem.setVisible(checked)

        ccpCodeTextItem.setVisible(checked)
        baselinePlot.setVisible(checked)

    def toolbarActionCallback(self, plot, textItem):
        checked = self.sender().isChecked()
        if plot:
            plot.setVisible(checked)
            textItem.setVisible(checked)

    def _closeModule(self):
        """Clean up notifiers for closing
        """
        if self.mousePosNotifier:
            self.mousePosNotifier.unRegister()

        super()._closeModule()
