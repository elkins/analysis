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
__dateModified__ = "$dateModified: 2024-10-02 09:30:47 +0100 (Wed, October 02, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import contextlib
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from ccpn.ui.gui.widgets.CompoundWidgets import ListCompoundWidget
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.CheckBoxes import CheckBoxes
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.Font import getTextDimensionsFromFont, getFontHeight
from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget, DoubleSpinBoxCompoundWidget
from ccpn.ui.gui.widgets.DoubleSpinbox import ScientificDoubleSpinBox
from ccpn.ui.gui.widgets.Slider import Slider
from ccpn.ui.gui.guiSettings import getColours, DIVIDER, SOFTDIVIDER, ZPlaneNavigationModes
from ccpn.ui.gui.widgets.HLine import HLine, LabeledHLine
from ccpn.ui.gui.widgets.PulldownListsForObjects import NmrChainPulldown, SpectrumDisplayPulldown
from ccpn.core.lib.Notifiers import Notifier
from ccpn.ui._implementation.SpectrumView import SpectrumView
from functools import partial
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLNotifier import GLNotifier
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGLDefs import AXISXUNITS, AXISYUNITS, \
    SYMBOLTYPE, SYMBOLSIZE, SYMBOLTHICKNESS, ARROWTYPES, ARROWSIZE, ARROWMINIMUM, \
    ANNOTATIONTYPE, AXISASPECTRATIOS, \
    AXISASPECTRATIOMODE, ALIASENABLED, ALIASSHADE, ALIASLABELSENABLED, CONTOURTHICKNESS, \
    PEAKSYMBOLSENABLED, PEAKLABELSENABLED, PEAKARROWSENABLED, \
    MULTIPLETSYMBOLSENABLED, MULTIPLETLABELSENABLED, MULTIPLETARROWSENABLED, MULTIPLETANNOTATIONTYPE, MULTIPLETTYPE
from ccpn.ui.gui.widgets.Spinbox import Spinbox
from ccpn.core.lib.AxisCodeLib import getAxisCodeMatchIndices
from ccpn.ui.gui.widgets.Base import SignalBlocking
from ccpn.core.Spectrum import Spectrum
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.core.Chain import Chain
from ccpn.core.PeakList import PeakList
from ccpn.core.NmrChain import NmrChain
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.RestraintTable import RestraintTable
from ccpn.core.DataTable import DataTable
from ccpn.core.ViolationTable import ViolationTable
from ccpn.ui._implementation.SpectrumDisplay import SpectrumDisplay


ALL = '<Use all>'
UseCurrent = '<Use active>'
IncludeCurrent = '<Current Strip>'
UseLastOpened = '<Use last opened>'  # used for last opened display

StandardSelections = [ALL, UseCurrent, UseLastOpened]

SelectToAdd = '> select-to-add <'

STRIPPLOT_PEAKS = 'peaks'
STRIPPLOT_NMRRESIDUES = 'nmrResidues'
STRIPPLOT_NMRCHAINS = 'nmrChains'
STRIPPLOT_NMRATOMSFROMPEAKS = 'nmrAtomsPeaks'
NO_STRIP = 'noStrip'
LineEditsMinimumWidth = 195


class SpectrumDisplaySettings(Widget, SignalBlocking):
    # signal for parentWidgets to respond to changes in the widget
    settingsChanged = pyqtSignal(dict)
    symbolsChanged = pyqtSignal(dict)
    stripArrangementChanged = pyqtSignal(int)
    zPlaneNavigationModeChanged = pyqtSignal(int)

    def __init__(self, parent=None,
                 mainWindow=None,
                 spectrumDisplay=None,
                 callback=None, returnCallback=None, applyCallback=None,
                 xAxisUnits=0, xTexts=None, showXAxis=True,
                 yAxisUnits=0, yTexts=None, showYAxis=True,
                 symbolType=0, annotationType=0, symbolSize=0, symbolThickness=0,
                 arrowType=0, arrowSize=0, arrowMinimum=0,
                 multipletAnnotationType=0, multipletType=0,
                 aliasEnabled=False, aliasShade=0,
                 aliasLabelsEnabled=False,
                 peakSymbolsEnabled=False,
                 peakLabelsEnabled=False,
                 peakArrowsEnabled=False,
                 multipletSymbolsEnabled=False,
                 multipletLabelsEnabled=False,
                 multipletArrowsEnabled=False,
                 stripArrangement=0,
                 _baseAspectRatioAxisCode='H', _aspectRatios=None,
                 _aspectRatioMode=0, contourThickness=0, zPlaneNavigationMode=0,
                 **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        self._parent = parent
        self._spectrumDisplay = spectrumDisplay

        xTexts = xTexts or []
        yTexts = yTexts or []
        _aspectRatios = _aspectRatios or {}

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
            self.preferences = mainWindow.application.preferences
        else:
            self.application = None
            self.project = None
            self.current = None
            self.preferences = None

        # store callbacks
        self.callback = callback
        self.returnCallback = returnCallback or self.doCallback
        self.applyCallback = applyCallback

        # set up the widgets
        self._setWidgets(parent, _aspectRatios.keys(), _baseAspectRatioAxisCode, showXAxis, showYAxis, xTexts, yTexts)

        # populate the widgets
        self._populateWidgets(_aspectRatioMode, _aspectRatios, annotationType, stripArrangement,
                              symbolSize, symbolThickness, symbolType, arrowType, arrowSize, arrowMinimum,
                              multipletAnnotationType, multipletType,
                              xAxisUnits, yAxisUnits,
                              aliasEnabled, aliasShade, aliasLabelsEnabled,
                              peakSymbolsEnabled, peakLabelsEnabled, peakArrowsEnabled,
                              multipletSymbolsEnabled, multipletLabelsEnabled, multipletArrowsEnabled,
                              contourThickness, zPlaneNavigationMode)

        # connect to the lock/symbol/ratio changed pyqtSignals
        self._GLSignals = GLNotifier(parent=self._parent)
        self._GLSignals.glAxisLockChanged.connect(self._lockAspectRatioChangedInDisplay)
        self._GLSignals.glSymbolsChanged.connect(self._symbolsChangedInDisplay)
        self._GLSignals.glXAxisChanged.connect(self._aspectRatioChangedInDisplay)
        self._GLSignals.glYAxisChanged.connect(self._aspectRatioChangedInDisplay)

    def _setWidgets(self, parent, aspectCodes, baseAspectCode, showXAxis, showYAxis, xTexts, yTexts):
        """Set up the widgets for the module
        """
        # insert widgets into the parent widget
        row = 0
        self.xAxisUnits = Label(parent, text="X-axis units", grid=(row, 0))
        self.xAxisUnitsData = RadioButtons(parent, texts=xTexts,
                                           objectNames=[f'xUnitsSDS_{text}' for text in xTexts],
                                           callback=self._settingsChanged,
                                           direction='h',
                                           grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                           tipTexts=None,
                                           )
        self.xAxisUnits.setVisible(showXAxis)
        self.xAxisUnitsData.setVisible(showXAxis)

        row += 1
        self.yAxisUnits = Label(parent, text="Y-axis units", grid=(row, 0))
        self.yAxisUnitsData = RadioButtons(parent, texts=yTexts,
                                           objectNames=[f'yUnitsSDS_{text}' for text in xTexts],
                                           callback=self._settingsChanged,
                                           direction='h',
                                           grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                           tipTexts=None)
        self.yAxisUnits.setVisible(showYAxis)
        self.yAxisUnitsData.setVisible(showYAxis)

        row += 1
        HLine(parent, grid=(row, 0), gridSpan=(1, 5), colour=getColours()[DIVIDER], height=15)

        row += 1
        _height = getFontHeight(size='VLARGE') or 24
        self.stripArrangementLabel = Label(parent, text="Strip Arrangement", grid=(row, 0))
        self.stripArrangementButtons = RadioButtons(parent, texts=['    ', '    ', '    '],
                                                    objectNames=['stripSDS_Row', 'stripSDS_Column', 'stripSDS_Tile'],
                                                    direction='horizontal',
                                                    grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                                    tipTexts=None,
                                                    icons=[('icons/strip-row', (_height, _height)),
                                                           ('icons/strip-column', (_height, _height)),
                                                           ('icons/strip-tile', (_height, _height))
                                                           ],
                                                    )
        # NOTE:ED - temporarily disable/hide the Tile button
        self.stripArrangementButtons.radioButtons[2].setEnabled(False)
        self.stripArrangementButtons.radioButtons[2].setVisible(False)
        self.stripArrangementButtons.setCallback(self._stripArrangementChanged)

        # if self._spectrumDisplay.is1D:
        #     # not currently required for 1D
        #     self.stripArrangementLabel.setVisible(False)
        #     self.stripArrangementButtons.setVisible(False)
        #     self.stripArrangementButtons.setEnabled(False)

        row += 1
        self.zPlaneNavigationModeLabel = Label(parent, text="Plane Navigation Mode", grid=(row, 0))
        self.zPlaneNavigationModeData = RadioButtons(parent, texts=[val.description for val in ZPlaneNavigationModes],
                                                     objectNames=[f'zPlaneSDS_{val.dataValue}' for val in
                                                                  ZPlaneNavigationModes],
                                                     callback=self._zPlaneNavigationModeChanged,
                                                     direction='h',
                                                     grid=(row, 1), hAlign='l', gridSpan=(1, 2),
                                                     tipTexts=(
                                                         'Plane navigation tools are located at the bottom of the spectrumDisplay,\nand will operate on the selected strip in that spectrumDisplay',
                                                         'Plane navigation tools are located at the bottom of each strip',
                                                         'Plane navigation tools are displayed in the upper-left corner of each strip'),
                                                     )
        self.zPlaneNavigationModeLabel.setToolTip('Select where the Plane navigation tools are located')

        if len(self._spectrumDisplay.axisCodes) < 3:
            self.zPlaneNavigationModeLabel.setVisible(False)
            self.zPlaneNavigationModeData.setVisible(False)
            self.zPlaneNavigationModeData.setEnabled(False)

        row += 1
        HLine(parent, grid=(row, 0), gridSpan=(1, 5), colour=getColours()[DIVIDER], height=15)

        row += 1
        Label(parent, text="Aspect Ratio", grid=(row, 0))

        row += 1
        self.useAspectRatioModeLabel = Label(parent, text="Mode", hAlign='r', grid=(row, 0))
        self.useAspectRatioModeButtons = RadioButtons(parent, texts=['Free', 'Locked', 'Fixed'],
                                                      objectNames=['armSDS_Free', 'armSDS_Locked', 'armSDS_Fixed'],
                                                      callback=self._aspectRatioModeChanged,
                                                      direction='horizontal',
                                                      grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                                      tipTexts=None,
                                                      )

        row += 1
        Label(parent, text='Current values', hAlign='r', grid=(row, 0))
        Label(parent, text='Fixed', grid=(row, 1))
        Label(parent, text='Screen', grid=(row, 2))

        row += 1
        self.aspectLabel = {}
        self.aspectData = {}
        self.aspectScreen = {}
        self.aspectLabelFrame = Frame(parent, setLayout=True, showBorder=False, grid=(row, 0))
        self.aspectDataFrame = Frame(parent, setLayout=True, showBorder=False, grid=(row, 1))
        self.aspectScreenFrame = Frame(parent, setLayout=True, showBorder=False, grid=(row, 2))
        self._removeWidget(self.aspectLabelFrame)
        self._removeWidget(self.aspectDataFrame)
        self._removeWidget(self.aspectScreenFrame)
        for ii, aspect in enumerate(sorted(aspectCodes)):
            # aspectValue = _aspectRatios[aspect]
            self.aspectLabel[aspect] = Label(self.aspectLabelFrame, text=aspect, grid=(ii, 0), hAlign='r')

            self.aspectData[aspect] = ScientificDoubleSpinBox(self.aspectDataFrame, min=0.01, grid=(ii, 0), hAlign='l',
                                                              decimals=2,
                                                              objectName=f'aspectSDS_{aspect}')
            # self.aspectData[aspect].setValue(aspectValue)
            self.aspectData[aspect].setMinimumWidth(LineEditsMinimumWidth)
            if aspect[0] == baseAspectCode[0]:
                self.aspectData[aspect].setEnabled(False)
            else:
                self.aspectData[aspect].setEnabled(True)
                self.aspectData[aspect].valueChanged.connect(partial(self._settingsChangeAspect, aspect))

            self.aspectScreen[aspect] = Label(self.aspectScreenFrame, text=aspect, grid=(ii, 0), hAlign='l')
            # self.aspectScreen[aspect].setText(self.aspectData[aspect].textFromValue(aspectValue))

        row += 1
        _buttonFrame = Frame(parent, setLayout=True, grid=(row, 1), gridSpan=(1, 3), hAlign='l')
        self.setFromDefaultsButton = Button(_buttonFrame, text='Defaults', grid=(0, 0),
                                            callback=self.updateFromDefaults)
        self.setFromScreenButton = Button(_buttonFrame, text='Set from screen', grid=(0, 1),
                                          callback=self._setAspectFromScreen)

        row += 1
        HLine(parent, grid=(row, 0), gridSpan=(1, 5), colour=getColours()[DIVIDER], height=15)

        row += 1
        self.contourThicknessLabel = Label(parent, text="Contour thickness (pixel)", grid=(row, 0))
        self.contourThicknessData = Spinbox(parent, step=1,
                                            min=1, max=20, grid=(row, 1), hAlign='l', objectName='SDS_contour')
        self.contourThicknessData.setMinimumWidth(LineEditsMinimumWidth)
        self.contourThicknessData.valueChanged.connect(self._symbolsChanged)

        row += 1
        HLine(parent, grid=(row, 0), gridSpan=(1, 5), colour=getColours()[DIVIDER], height=15)

        row += 1
        Label(parent, text="Peaks", hAlign='l', grid=(row, 0))

        if self._spectrumDisplay.MAXPEAKLABELTYPES:
            row += 1
            _texts = ['Short', 'Full', 'NmrAtom Pid', 'Minimal', 'Peak Pid', 'ClusterId', 'Annotation']
            _names = ['annSDS_Short', 'annSDS_Full', 'annSDS_Pid', 'annSDS_Minimal', 'annSDS_Id', 'annSDS_ClusterId',
                      'annSDS_Annotation']
            _texts = _texts[:self._spectrumDisplay.MAXPEAKLABELTYPES]
            _names = _names[:self._spectrumDisplay.MAXPEAKLABELTYPES]

            self.annotationsLabel = Label(parent, text="Label", hAlign='r', grid=(row, 0))
            self.annotationsData = RadioButtons(parent, texts=_texts,
                                                objectNames=_names,
                                                callback=self._symbolsChanged,
                                                direction='v',
                                                grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                                tipTexts=None,
                                                )

        if self._spectrumDisplay.MAXPEAKSYMBOLTYPES:
            # if not self._spectrumDisplay.is1D:
            row += 1
            _texts = ['Cross', 'lineWidths', 'Filled lineWidths', 'Plus']
            _names = ['symSDS_Cross', 'symSDS_lineWidths', 'symSDS_Filled lineWidths', 'symSDS_Plus']
            _texts = _texts[:self._spectrumDisplay.MAXPEAKSYMBOLTYPES]
            _names = _names[:self._spectrumDisplay.MAXPEAKSYMBOLTYPES]

            self.symbolsLabel = Label(parent, text="Symbol", hAlign='r', grid=(row, 0))
            self.symbol = RadioButtons(parent, texts=_texts,
                                       objectNames=_names,
                                       callback=self._symbolsChanged,
                                       direction='h',
                                       grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                       tipTexts=None,
                                       )

            if self._spectrumDisplay.is1D:
                self.symbol.radioButtons[1].setEnabled(False)
                self.symbol.radioButtons[2].setEnabled(False)
                self.symbol.radioButtons[1].setVisible(False)
                self.symbol.radioButtons[2].setVisible(False)

        row += 1
        self.symbolSizePixelLabel = Label(parent, text="Size (pixel)", hAlign='r', grid=(row, 0))
        self.symbolSizePixelData = Spinbox(parent, step=1,
                                           min=2, max=50, grid=(row, 1), hAlign='l', objectName='SDS_symbolSize')
        self.symbolSizePixelData.setMinimumWidth(LineEditsMinimumWidth)
        # self.symbolSizePixelData.setValue(int(symbolSize))
        self.symbolSizePixelData.valueChanged.connect(self._symbolsChanged)

        row += 1
        self.symbolThicknessLabel = Label(parent, text="Thickness (pixel)", hAlign='r', grid=(row, 0))
        self.symbolThicknessData = Spinbox(parent, step=1,
                                           min=1, max=20, grid=(row, 1), hAlign='l', objectName='SDS_symbolThickness')
        self.symbolThicknessData.setMinimumWidth(LineEditsMinimumWidth)
        # self.symbolThicknessData.setValue(int(symbolThickness))
        self.symbolThicknessData.valueChanged.connect(self._symbolsChanged)

        row += 1
        HLine(parent, grid=(row, 0), gridSpan=(1, 5), colour=getColours()[DIVIDER], height=15)

        row += 1
        Label(parent, text="Multiplets", hAlign='l', grid=(row, 0))

        if self._spectrumDisplay.MAXMULTIPLETLABELTYPES:
            row += 1
            _texts = ['Short', 'Full', 'NmrAtom Pid', 'Minimal', 'Multiplet Pid', 'ClusterId', 'Annotation']
            _names = ['annMDS_Short', 'annMDS_Full', 'annMDS_Pid', 'annMDS_Minimal', 'annMDS_Id', 'annMDS_ClusterId',
                      'annMDS_Annotation']
            _texts = _texts[:self._spectrumDisplay.MAXMULTIPLETLABELTYPES]
            _names = _names[:self._spectrumDisplay.MAXMULTIPLETLABELTYPES]

            self.multipletAnnotationLabel = Label(parent, text="Label", hAlign='r', grid=(row, 0))
            self.multipletAnnotationData = RadioButtons(parent, texts=_texts,
                                                        objectNames=_names,
                                                        callback=self._symbolsChanged,
                                                        direction='v',
                                                        grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                                        tipTexts=None,
                                                        )
        self.multipletAnnotationData.radioButtons[2].setVisible(False)
        self.multipletAnnotationData.radioButtons[5].setVisible(False)

        if self._spectrumDisplay.MAXMULTIPLETSYMBOLTYPES:
            # if not self._spectrumDisplay.is1D:
            row += 1
            _texts = ['Cross']
            _names = ['symMDS_Cross']
            _texts = _texts[:self._spectrumDisplay.MAXMULTIPLETSYMBOLTYPES]
            _names = _names[:self._spectrumDisplay.MAXMULTIPLETSYMBOLTYPES]

            self.multipletLabel = Label(parent, text="Symbol", hAlign='r', grid=(row, 0))
            self.multipletSymbol = RadioButtons(parent, texts=_texts,
                                                objectNames=_names,
                                                callback=self._symbolsChanged,
                                                direction='h',
                                                grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                                tipTexts=None,
                                                )

        self.multipletLabel.setVisible(False)
        self.multipletSymbol.setVisible(False)

        row += 1
        HLine(parent, grid=(row, 0), gridSpan=(1, 5), colour=getColours()[DIVIDER], height=15)

        row += 1
        self.peakSymbolsEnabledLabel = Label(parent, text="Show peak symbols", grid=(row, 0))
        self.peakSymbolsEnabledData = CheckBox(parent,
                                               # checked=peakSymbolsEnabled,
                                               grid=(row, 1), objectName='SDS_peakSymbolsEnabled')
        self.peakSymbolsEnabledData.clicked.connect(self._symbolsChanged)

        row += 1
        self.peakLabelsEnabledLabel = Label(parent, text="Show peak labels", grid=(row, 0))
        self.peakLabelsEnabledData = CheckBox(parent,
                                              # checked=peakLabelsEnabled,
                                              grid=(row, 1), objectName='SDS_peakLabelsEnabled')
        self.peakLabelsEnabledData.clicked.connect(self._symbolsChanged)

        row += 1
        self.multipletSymbolsEnabledLabel = Label(parent, text="Show multiplet symbols", grid=(row, 0))
        self.multipletSymbolsEnabledData = CheckBox(parent,
                                                    # checked=multipletSymbolsEnabled,
                                                    grid=(row, 1), objectName='SDS_multipletSymbolsEnabled')
        self.multipletSymbolsEnabledData.clicked.connect(self._symbolsChanged)

        row += 1
        self.multipletLabelsEnabledLabel = Label(parent, text="Show multiplet labels", grid=(row, 0))
        self.multipletLabelsEnabledData = CheckBox(parent,
                                                   # checked=multipletLabelsEnabled,
                                                   grid=(row, 1), objectName='SDS_multipletLabelsEnabled')
        self.multipletLabelsEnabledData.clicked.connect(self._symbolsChanged)

        row += 1
        Label(parent, text="Aliased peaks", hAlign='l', grid=(row, 0))

        row += 1
        self.aliasEnabledLabel = Label(parent, text="Show peaks", hAlign='r', grid=(row, 0))
        self.aliasEnabledData = CheckBox(parent,
                                         # checked=aliasEnabled,
                                         grid=(row, 1), objectName='SDS_aliasEnabled')
        self.aliasEnabledData.clicked.connect(self._symbolsChanged)

        row += 1
        self.aliasLabelsEnabledLabel = Label(parent, text="Show labels", hAlign='r', grid=(row, 0))
        self.aliasLabelsEnabledData = CheckBox(parent,
                                               # checked=aliasLabelsEnabled,
                                               grid=(row, 1), objectName='SDS_aliasLabelsEnabled')
        self.aliasLabelsEnabledData.clicked.connect(self._symbolsChanged)

        row += 1
        self.aliasShadeLabel = Label(parent, text="Opacity", hAlign='r', grid=(row, 0))
        _sliderBox = Frame(parent, setLayout=True, grid=(row, 1), hAlign='l')
        self.aliasShadeData = Slider(_sliderBox, grid=(0, 1), hAlign='l', objectName='SDS_aliasShade')
        Label(_sliderBox, text="0", grid=(0, 0), hAlign='l')
        Label(_sliderBox, text="100%", grid=(0, 2), hAlign='l')
        self.aliasShadeData.setMinimumWidth(LineEditsMinimumWidth)
        # self.aliasShadeData.set(aliasShade)
        self.aliasShadeData.valueChanged.connect(self._symbolsChanged)

        row += 1
        self.peakArrowsEnabledLabel = Label(parent, text="Show peak arrows", grid=(row, 0))
        self.peakArrowsEnabledData = CheckBox(parent,
                                              # checked=peakArrowsEnabled,
                                              grid=(row, 1), objectName='SDS_peakArrowsEnabled')
        self.peakArrowsEnabledData.clicked.connect(self._symbolsChanged)

        row += 1
        self.multipletArrowsEnabledLabel = Label(parent, text="Show multiplet arrows", grid=(row, 0))
        self.multipletArrowsEnabledData = CheckBox(parent,
                                                   # checked=multipletArrowsEnabled,
                                                   grid=(row, 1), objectName='SDS_multipletArrowsEnabled')
        self.multipletArrowsEnabledData.clicked.connect(self._symbolsChanged)

        if self._spectrumDisplay.MAXARROWTYPES:
            # if not self._spectrumDisplay.is1D:
            row += 1
            _texts = ['Line', 'Wedge', 'Arrow']
            _names = ['arrSDS_Line', 'arrSDS_Wedge', 'arrSDS_Arrow']
            _texts = _texts[:self._spectrumDisplay.MAXARROWTYPES]
            _names = _names[:self._spectrumDisplay.MAXARROWTYPES]

            self.arrowsLabel = Label(parent, text="Arrow", hAlign='r', grid=(row, 0))
            self.arrow = RadioButtons(parent, texts=_texts,
                                      objectNames=_names,
                                      callback=self._symbolsChanged,
                                      direction='h',
                                      grid=(row, 1), gridSpan=(1, 3), hAlign='l',
                                      tipTexts=None,
                                      )

        row += 1
        self.arrowSizeLabel = Label(parent, text="Size (pixels)", hAlign='r', grid=(row, 0))
        self.arrowSizeData = Spinbox(parent, step=1,
                                     min=1, max=20, grid=(row, 1), hAlign='l', objectName='SDS_arrowSize')
        self.arrowSizeData.setMinimumWidth(LineEditsMinimumWidth)
        # self.arrowSizeData.setValue(int(arrowSize))
        self.arrowSizeData.valueChanged.connect(self._symbolsChanged)

        row += 1
        self.arrowMinimumLabel = Label(parent, text="Minimum length (pixels)", hAlign='r', grid=(row, 0))
        self.arrowMinimumData = Spinbox(parent, step=1,
                                        min=1, max=100, grid=(row, 1), hAlign='l', objectName='SDS_arrowMinimum')
        self.arrowMinimumData.setMinimumWidth(LineEditsMinimumWidth)
        # self.arrowMinimumData.setValue(int(arrowMinimum))
        self.arrowMinimumData.valueChanged.connect(self._symbolsChanged)

        row += 1
        self._spacer = Spacer(parent, 5, 5,
                              QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding,
                              grid=(row, 4), gridSpan=(1, 1))
        self._parent.setContentsMargins(5, 5, 5, 5)

    def _populateWidgets(self, aspectRatioMode, aspectRatios, annotationType, stripArrangement,
                         symbolSize, symbolThickness, symbolType, arrowType, arrowSize, arrowMinimum,
                         multipletAnnotationType, multipletType,
                         xAxisUnits, yAxisUnits,
                         aliasEnabled, aliasShade, aliasLabelsEnabled,
                         peakSymbolsEnabled, peakLabelsEnabled, peakArrowsEnabled,
                         multipletSymbolsEnabled, multipletLabelsEnabled, multipletArrowsEnabled,
                         contourThickness, zPlaneNavigationMode):
        """Populate the widgets
        """
        with self._parent.blockWidgetSignals():

            # put the values into the correct widgets

            self._setAxesUnits(xAxisUnits, yAxisUnits)

            self.useAspectRatioModeButtons.setIndex(aspectRatioMode)
            for aspect in sorted(aspectRatios.keys()):
                aspectValue = aspectRatios[aspect]
                self.aspectData[aspect].setValue(aspectValue)
                self.aspectScreen[aspect].setText(self.aspectData[aspect].textFromValue(aspectValue))

            if self._spectrumDisplay.MAXPEAKLABELTYPES:
                self.annotationsData.setIndex(annotationType)
            if self._spectrumDisplay.MAXPEAKSYMBOLTYPES:
                self.symbol.setIndex(symbolType)
            if self._spectrumDisplay.MAXMULTIPLETLABELTYPES:
                self.multipletAnnotationData.setIndex(multipletAnnotationType)
            if self._spectrumDisplay.MAXMULTIPLETSYMBOLTYPES:
                self.multipletSymbol.setIndex(multipletType)

            self.symbolSizePixelData.setValue(int(symbolSize))
            self.symbolThicknessData.setValue(int(symbolThickness))
            self.contourThicknessData.setValue(int(contourThickness))

            self.stripArrangementButtons.setIndex(stripArrangement)
            self.zPlaneNavigationModeData.setIndex(zPlaneNavigationMode)

            self.aliasEnabledData.setChecked(aliasEnabled)
            self.aliasShadeData.setValue(aliasShade)
            self.aliasLabelsEnabledData.setChecked(aliasLabelsEnabled)
            self.aliasLabelsEnabledData.setEnabled(aliasEnabled)
            self.aliasShadeData.setEnabled(aliasEnabled)

            self.peakSymbolsEnabledData.set(peakSymbolsEnabled)
            self.peakLabelsEnabledData.set(peakLabelsEnabled)
            self.peakArrowsEnabledData.set(peakArrowsEnabled)
            self.multipletSymbolsEnabledData.set(multipletSymbolsEnabled)
            self.multipletLabelsEnabledData.set(multipletLabelsEnabled)
            self.multipletArrowsEnabledData.set(multipletArrowsEnabled)

            if self._spectrumDisplay.MAXARROWTYPES:
                self.arrow.setIndex(arrowType)
            self.arrowSizeData.setValue(int(arrowSize))
            self.arrowMinimumData.setValue(int(arrowMinimum))

    def _setAxesUnits(self, xAxisUnits, yAxisUnits):
        """Set the unit's checkboxes
        CCPNINTERNAL: used in GuiSpectrumDisplay
        """
        if xAxisUnits is not None:
            self.xAxisUnitsData.setIndex(xAxisUnits)
        if yAxisUnits is not None:
            self.yAxisUnitsData.setIndex(yAxisUnits)

    def getValues(self):
        """Return a dict containing the current settings
        """
        aspectRatios = {axis: data.get() for axis, data in self.aspectData.items()}

        # NOTE:ED - should really use an intermediate data structure here
        return {AXISXUNITS             : self.xAxisUnitsData.getIndex(),
                AXISYUNITS             : self.yAxisUnitsData.getIndex(),
                AXISASPECTRATIOMODE    : self.useAspectRatioModeButtons.getIndex(),
                AXISASPECTRATIOS       : aspectRatios,
                SYMBOLTYPE             : self.symbol.getIndex(),  # if not self._spectrumDisplay.is1D else 0,
                ANNOTATIONTYPE         : self.annotationsData.getIndex(),  # if not self._spectrumDisplay.is1D else 0,
                SYMBOLSIZE             : self.symbolSizePixelData.value(),
                SYMBOLTHICKNESS        : self.symbolThicknessData.value(),
                CONTOURTHICKNESS       : self.contourThicknessData.value(),
                MULTIPLETANNOTATIONTYPE: self.multipletAnnotationData.getIndex(),
                # if not self._spectrumDisplay.is1D else 0,
                MULTIPLETTYPE          : self.multipletSymbol.getIndex(),  # if not self._spectrumDisplay.is1D else 0,
                ALIASENABLED           : self.aliasEnabledData.isChecked(),
                ALIASSHADE             : int(self.aliasShadeData.get()),
                ALIASLABELSENABLED     : self.aliasLabelsEnabledData.isChecked(),
                PEAKSYMBOLSENABLED     : self.peakSymbolsEnabledData.isChecked(),
                PEAKLABELSENABLED      : self.peakLabelsEnabledData.isChecked(),
                PEAKARROWSENABLED      : self.peakArrowsEnabledData.isChecked(),
                MULTIPLETSYMBOLSENABLED: self.multipletSymbolsEnabledData.isChecked(),
                MULTIPLETLABELSENABLED : self.multipletLabelsEnabledData.isChecked(),
                MULTIPLETARROWSENABLED : self.multipletArrowsEnabledData.isChecked(),
                ARROWTYPES             : self.arrow.getIndex(),  # if not self._spectrumDisplay.is1D else 0,
                ARROWSIZE              : self.arrowSizeData.value(),
                ARROWMINIMUM           : self.arrowMinimumData.value(),
                }

    def _aspectRatioModeChanged(self):
        """Set the current aspect ratio mode
        """
        self._updateLockedSettings()
        self._settingsChanged()

    def _updateLockedSettings(self, always=False):
        if self.useAspectRatioModeButtons.getIndex() == 2 or always:
            with self.aspectScreenFrame.blockWidgetSignals():
                for aspect, data in self.aspectData.items():
                    if aspect in self.aspectScreen:
                        self.aspectScreen[aspect].setText(data.text())

    def _settingsChangeAspect(self, *args):
        """Set the aspect ratio for the axes
        """
        self._updateLockedSettings()
        self._settingsChanged()

    def _setAspectFromScreen(self, *args):
        with self.aspectDataFrame.blockWidgetSignals():
            for aspect, label in self.aspectScreen.items():
                if aspect in self.aspectData:
                    self.aspectData[aspect].setValue(self.aspectData[aspect].valueFromText(label.text()))

        self._settingsChanged()

    def setStripArrangementButtons(self, value):
        """Update the state of the stripArrangement radioButtons
        """
        self.blockSignals(True)
        self.stripArrangementButtons.setIndex(value)
        self.blockSignals(False)

    def setZPlaneButtons(self, value):
        """Update the state of the zPlaneNavigation radioButtons
        """
        self.blockSignals(True)
        labels = [val.dataValue for val in ZPlaneNavigationModes]
        if value in labels:
            self.zPlaneNavigationModeData.setIndex(labels.index(value))
        self.blockSignals(False)

    def updateFromDefaults(self, *args):
        """Update the defaults from preferences
        """
        with self.aspectDataFrame.blockWidgetSignals():
            for aspect, label in self.aspectScreen.items():
                if aspect in self.preferences.general.aspectRatios:
                    value = self.preferences.general.aspectRatios[aspect]
                    self.aspectData[aspect].setValue(value)

        self.blockSignals(True)
        self.useAspectRatioModeButtons.setIndex(int(self.preferences.general.aspectRatioMode))
        self._updateLockedSettings()
        self.xAxisUnitsData.setIndex(self.preferences.general.xAxisUnits)
        self.yAxisUnitsData.setIndex(self.preferences.general.yAxisUnits)
        self.blockSignals(False)

        self._settingsChanged()

    @pyqtSlot()
    def _settingsChanged(self):
        """Handle changing the X axis units
        """
        self.settingsChanged.emit(self.getValues())

    @pyqtSlot(dict)
    def _lockAspectRatioChangedInDisplay(self, aDict):
        """Respond to an external change in the lock status of a strip
        """
        if aDict[GLNotifier.GLSPECTRUMDISPLAY] == self._spectrumDisplay:
            self.blockSignals(True)

            self.useAspectRatioModeButtons.setIndex(aDict[GLNotifier.GLVALUES][0])
            self._updateLockedSettings()

            self.blockSignals(False)

    @pyqtSlot(dict)
    def _aspectRatioChangedInDisplay(self, aDict):
        """Respond to an external change in the aspect ratio of a strip
        """
        if aDict[GLNotifier.GLSPECTRUMDISPLAY] != self._spectrumDisplay:
            return
        if not (_aspectRatios := aDict[GLNotifier.GLAXISVALUES][GLNotifier.GLASPECTRATIOS]):
            return

        self.blockSignals(True)

        for aspect in _aspectRatios.keys():
            if aspect in self.aspectScreen and aspect in self.aspectData:
                aspectValue = _aspectRatios[aspect]
                self.aspectScreen[aspect].setText(self.aspectData[aspect].textFromValue(aspectValue))

        self.blockSignals(False)

    @pyqtSlot()
    def _symbolsChanged(self):
        """Handle changing the symbols
        """
        self.symbolsChanged.emit(self.getValues())

        _enabled = self.aliasEnabledData.get()
        self.aliasLabelsEnabledData.setEnabled(_enabled)
        self.aliasShadeData.setEnabled(_enabled)

    @pyqtSlot(dict)
    def _symbolsChangedInDisplay(self, aDict):
        """Respond to an external change in symbol settings
        """
        if aDict[GLNotifier.GLSPECTRUMDISPLAY] == self._spectrumDisplay:
            values = aDict[GLNotifier.GLVALUES]
            self.blockSignals(True)

            # if not self._spectrumDisplay.is1D:
            # only update if Nd
            self.symbol.setIndex(values[SYMBOLTYPE])
            self.annotationsData.setIndex(values[ANNOTATIONTYPE])
            self.symbolSizePixelData.set(values[SYMBOLSIZE])
            self.symbolThicknessData.set(values[SYMBOLTHICKNESS])
            self.contourThicknessData.set(values[CONTOURTHICKNESS])

            self.aliasEnabledData.set(values[ALIASENABLED])
            self.aliasShadeData.set(values[ALIASSHADE])
            self.aliasLabelsEnabledData.set(values[ALIASLABELSENABLED])

            self.peakSymbolsEnabledData.set(values[PEAKSYMBOLSENABLED])
            self.peakLabelsEnabledData.set(values[PEAKLABELSENABLED])
            self.peakArrowsEnabledData.set(values[PEAKARROWSENABLED])
            self.multipletSymbolsEnabledData.set(values[MULTIPLETSYMBOLSENABLED])
            self.multipletLabelsEnabledData.set(values[MULTIPLETLABELSENABLED])
            self.multipletArrowsEnabledData.set(values[MULTIPLETARROWSENABLED])

            self.arrow.setIndex(values[ARROWTYPES])
            self.arrowSizeData.set(values[ARROWSIZE])
            self.arrowMinimumData.set(values[ARROWMINIMUM])

            _enabled = self.aliasEnabledData.get()
            self.aliasLabelsEnabledData.setEnabled(_enabled)
            self.aliasShadeData.setEnabled(_enabled)

            self.mainWindow.statusBar().showMessage(f"Cycle Symbol Labelling: {self.annotationsData.get()} ")

            self.blockSignals(False)

    def _stripArrangementChanged(self):
        """Emit a signal if the strip arrangement buttons have been pressed
        """
        self.stripArrangementChanged.emit(self.stripArrangementButtons.getIndex())

    def _zPlaneNavigationModeChanged(self):
        """Emit a signal if the zPlane navigation buttons have been pressed
        """
        self.zPlaneNavigationModeChanged.emit(self.zPlaneNavigationModeData.getIndex())

    def doCallback(self):
        """Handle the user callback
        """
        if self.callback:
            self.callback()

    def _returnCallback(self):
        """Handle the return from widget callback
        """
        pass

    def updateRatiosInDisplay(self, ratios):
        """Manually update the settings in the display
        """
        with self.aspectScreenFrame.blockWidgetSignals():
            for aspect in sorted(ratios.keys()):
                aspectValue = ratios[aspect]
                if aspect in self.aspectScreen and aspect in self.aspectData:
                    self.aspectData[aspect].setText(aspectValue)


class _commonSettings():
    """
    Not to be used as a stand-alone class
    """

    # separated from settings widgets below, but only one seems to use it now

    def _getSpectraFromDisplays(self, displays, data=None):
        """Get the list of active spectra from the spectrumDisplays
        """
        if not self.application or not displays or len(displays) > 1:
            return 0, None, None, None

        from ccpn.core.lib.AxisCodeLib import getAxisCodeMatch, getAxisCodeMatchIndices

        validSpectrumViews = {}

        # loop through all the selected displays/spectrumViews that are visible
        for dp in displays:

            # ignore undefined displays
            if not dp or dp.is1D:
                continue

            if dp.strips:
                for sv in dp.strips[0].spectrumViews:

                    if sv.isDeleted:
                        continue
                    if data and data[Notifier.OBJECT] == sv and data[Notifier.TRIGGER] == Notifier.DELETE:
                        # ignore spectrumView if it about to be deleted - should re-introduce the flag :|
                        continue

                    if sv.spectrum not in validSpectrumViews:
                        validSpectrumViews[sv.spectrum] = sv.isDisplayed
                    else:
                        validSpectrumViews[sv.spectrum] = validSpectrumViews[sv.spectrum] or sv.isDisplayed

        if not validSpectrumViews:
            return 0, None, None, None

        # maxLen = 0
        # refAxisCodes = None

        # need a list of all unique axisCodes in the spectra in the selected spectrumDisplays
        from ccpn.util.OrderedSet import OrderedSet

        # have to assume that there is only one display it this point
        activeDisplay = displays[0]

        # get list of unique axisCodes
        visibleAxisCodes = {}
        spectrumIndices = {}
        for spectrum in validSpectrumViews:
            indices = getAxisCodeMatchIndices(spectrum.axisCodes, activeDisplay.axisCodes)
            spectrumIndices[spectrum] = indices
            for ii, axis in enumerate(spectrum.axisCodes):
                ind = indices[ii]
                if ind is not None:
                    if ind in visibleAxisCodes:
                        visibleAxisCodes[ind].add(axis)
                    else:
                        visibleAxisCodes[ind] = OrderedSet([axis])

        ll = len(activeDisplay.axisCodes)
        axisLabels = [None] * ll
        for ii in range(ll):
            axisLabels[ii] = ', '.join(visibleAxisCodes[ii])

        return ll, axisLabels, spectrumIndices, validSpectrumViews

        # if not validSpectrumViews:
        # from ccpn.util.OrderedSet import OrderedSet
        #
        # # get list of unique axisCodes
        # visibleAxisCodes = OrderedSet()
        # for spectrum, visible in validSpectrumViews.items():
        #     for axis in spectrum.axisCodes:
        #         visibleAxisCodes.add(axis)
        #
        # # get mapping of each spectrum onto this list
        # spectrumIndices = {}
        # for spectrum, visible in validSpectrumViews.items():
        #     indices = getAxisCodeMatchIndices(spectrum.axisCodes, visibleAxisCodes, exactMatch=False)  #True)
        #     spectrumIndices[spectrum] = indices
        #     maxLen = max(spectrum.dimensionCount, maxLen)
        #
        # # return if nothing to process
        # if not maxLen:
        #     return 0, None, None, None
        #
        # axisLabels = [', '.join(ax) for ax in visibleAxisCodes]
        #
        # return maxLen, tuple(visibleAxisCodes), spectrumIndices, validSpectrumViews

        # for spectrum, visible in validSpectrumViews.items():
        #
        #     # get the max length of the axisCodes for the displayed spectra
        #     if len(spectrum.axisCodes) > maxLen:
        #         maxLen = len(spectrum.axisCodes)
        #         refAxisCodes = list(spectrum.axisCodes)
        #
        # mappings = {}
        # for spectrum, visible in validSpectrumViews.items():
        #
        #     matchAxisCodes = spectrum.axisCodes
        #
        #     foundMap = getAxisCodeMatch(matchAxisCodes, refAxisCodes, allMatches=True)
        #     mappings.update(foundMap)
        #
        #     # for refAxisCode in refAxisCodes:
        #     #     for matchAxisCode in matchAxisCodes:
        #     #         mapping = getAxisCodeMatch([matchAxisCode], [refAxisCode])
        #     #         for k, v in mapping.items():
        #     #             if v not in mappings:
        #     #                 mappings[v] = set([k])
        #     #             else:
        #     #                 mappings[v].add(k)
        #
        # # example of mappings dict
        # # ('Hn', 'C', 'Nh')
        # # {'Hn': {'Hn'}, 'Nh': {'Nh'}, 'C': {'C'}}
        # # {'Hn': {'H', 'Hn'}, 'Nh': {'Nh'}, 'C': {'C'}}
        # # {'CA': {'C'}, 'Hn': {'H', 'Hn'}, 'Nh': {'Nh'}, 'C': {'CA', 'C'}}
        # # {'CA': {'C'}, 'Hn': {'H', 'Hn'}, 'Nh': {'Nh'}, 'C': {'CA', 'C'}}
        #
        # # far too complicated!
        # axisLabels = [set() for ii in range(len(mappings))]
        #
        # spectrumIndex = {}
        # # go through the spectra again
        # for spectrum, visible in validSpectrumViews.items():
        #
        #     spectrumIndex[spectrum] = [0 for ii in range(len(spectrum.axisCodes))]
        #
        #     # get the spectrum dimension axisCode, and see if is already there
        #     for spectrumDim, spectrumAxis in enumerate(spectrum.axisCodes):
        #
        #         axisTestCodes = tuple(mappings.keys())
        #         if spectrumAxis in axisTestCodes:
        #             spectrumIndex[spectrum][spectrumDim] = axisTestCodes.index(spectrumAxis)
        #             axisLabels[spectrumIndex[spectrum][spectrumDim]].add(spectrumAxis)
        #
        #         else:
        #             # if the axisCode is not in the reference list then find the mapping from the dict
        #             for k, v in mappings.items():
        #                 if spectrumAxis in v:
        #                     # refAxisCodes[dim] = k
        #                     spectrumIndex[spectrum][spectrumDim] = axisTestCodes.index(k)
        #                     axisLabels[axisTestCodes.index(k)].add(spectrumAxis)
        #
        # axisLabels = [', '.join(ax) for ax in axisLabels]
        #
        # return maxLen, axisLabels, spectrumIndex, validSpectrumViews
        # # self.axisCodeOptions.setCheckBoxes(texts=axisLabels, tipTexts=axisLabels)
        #
        # else:
        #     return 0, None, None, None

    @staticmethod
    def _removeWidget(widget, removeTopWidget=False):
        """Destroy a widget and all it's contents
        """

        def deleteItems(layout):
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.setVisible(False)
                        widget.setParent(None)
                        del widget

        deleteItems(widget.getLayout())
        if removeTopWidget:
            del widget

    # Depreciated, replaced by _fillAllSpectrumFrame
    # def _fillSpectrumFrame(self, displays, data=None):
    #     """Populate the spectrumFrame with the selectable spectra
    #     """
    #     if self._spectraWidget:
    #         self._spectraWidget.hide()
    #         self._spectraWidget.setParent(None)
    #         self._removeWidget(self._spectraWidget, removeTopWidget=True)
    #
    #     self._spectraWidget = Widget(parent=self.spectrumDisplayOptionsFrame, setLayout=True, hPolicy='minimal',
    #                                  grid=(1, 0), gridSpan=(self._spectraRows, 1), vAlign='top', hAlign='left')
    #
    #     # calculate the maximum number of axes
    #     self.maxLen, self.axisLabels, specInd, self.validSpectrumViews = self._getSpectraFromDisplays(displays, data)
    #     self.spectrumIndex = [specInd]
    #     if not self.maxLen:
    #         return
    #
    #     # modifier for atomCode
    #     spectraRow = 0
    #     self.atomCodeFrame = Frame(self._spectraWidget, setLayout=True, showBorder=False, fShape='noFrame',
    #                                grid=(spectraRow, 0), gridSpan=(1, self.maxLen + 1),
    #                                vAlign='top', hAlign='left')
    #     self.axisCodeLabel = Label(self.atomCodeFrame, 'Restricted Axes', grid=(0, 0))
    #
    #     # remember current selection so can be set after redefining checkboxes
    #     currentSelection = None
    #     if self.axisCodeOptions:
    #         currentSelection = self.axisCodeOptions.getSelectedText()
    #
    #     self.axisCodeOptions = CheckBoxes(self.atomCodeFrame, selectedInd=None, texts=[],
    #                                       callback=self._changeAxisCode, grid=(0, 1))
    #     self.axisCodeOptions.setCheckBoxes(texts=self.axisLabels, tipTexts=self.axisLabels)
    #
    #     # set current selection back to the checkboxes
    #     # if currentSelection:
    #     #     self.axisCodeOptions.setSelectedByText(currentSelection, True, presetAll=True)
    #
    #     # just clear the 'C' axes - this is the usual configuration
    #     self.axisCodeOptions.selectAll()
    #     for ii, box in enumerate(self.axisCodeOptions.checkBoxes):
    #         if box.text().upper().startswith('C'):
    #             self.axisCodeOptions.clearIndex(ii)
    #
    #     # put in a divider
    #     spectraRow += 1
    #     HLine(self._spectraWidget, grid=(spectraRow, 0), gridSpan=(1, 4),
    #           colour=getColours()[SOFTDIVIDER], height=15)
    #
    #     # add labels for the columns
    #     spectraRow += 1
    #     Label(self._spectraWidget, 'Spectrum', grid=(spectraRow, 0))
    #
    #     # for ii in range(self.maxLen):
    #     #     Label(self._spectraWidget, 'Tolerance', grid=(spectraRow, ii + 1))
    #     Label(self._spectraWidget, '(double-width tolerances)', grid=(spectraRow, 1), gridSpan=(1, self.maxLen))
    #
    #     self.spectraStartRow = spectraRow + 1
    #
    #     if self.application:
    #         spectraWidgets = {}  # spectrum.pid, frame dict to show/hide
    #         for row, spectrum in enumerate(self.validSpectrumViews.keys()):
    #             spectraRow += 1
    #             f = _SpectrumRow(parent=self._spectraWidget,
    #                              application=self.application,
    #                              spectrum=spectrum,
    #                              spectrumDisplay=displays[0],
    #                              row=spectraRow, startCol=0,
    #                              setLayout=True,
    #                              visible=self.validSpectrumViews[spectrum])
    #
    #             spectraWidgets[spectrum.pid] = f

    def _fillAllSpectrumFrame(self, displays):
        """Populate all spectrumFrames into a moreLessFrame
        """
        def _codeDictUpdate(displayKey : str = None, checkBox : CheckBox = None):
            """update axisCode dict when check boxes are changed.
            """
            if (display is None) or (box is None):
                return

            if not self.axisCodeOptionsDict.get(displayKey):
                self.axisCodeOptionsDict[displayKey] = {}
            self.axisCodeOptionsDict[displayKey] = checkBox.parent().getSelectedIndexes()

        from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame

        if self._spectraWidget:
            self._spectraWidget.hide()
            self._spectraWidget.setParent(None)
            self._removeWidget(self._spectraWidget, removeTopWidget=True)

        self._spectraWidget = Widget(parent=self.spectrumDisplayOptionsFrame, setLayout=True,
                                     grid=(1, 0), gridSpan=(1, 2), vAlign='top')

        if not displays:
            return

        self.spectrumIndex = []
        for num, display in enumerate(displays):
            maxLen, axisLabels, specInd, validSpectrumViews = self._getSpectraFromDisplays([display])
            self.spectrumIndex.append(specInd)

            curFrame = MoreLessFrame(self._spectraWidget, name=display.pid, showMore=True, grid=(num, 0), gridSpan=(1,4))

            _frame = curFrame.contentsFrame
            f_row = 0
            Label(_frame, text='Restricted Axes', grid=(f_row, 0))

            axisCodeOptions = CheckBoxes(_frame, selectedInd=None, texts=[],
                                         callback=self._changeAxisCode, grid=(f_row,1))
            axisCodeOptions.setCheckBoxes(texts=axisLabels, tipTexts=axisLabels)
            for box in axisCodeOptions.checkBoxes:
                box.stateChanged.connect(partial(_codeDictUpdate, f'{display}', box))

            if (displayDict := self.axisCodeOptionsDict.get(f'{display}')) is not None:
                # if checkboxes previously existed set to same state
                axisCodeOptions.selectAll()
                for ii, box in enumerate(axisCodeOptions.checkBoxes):
                    if ii not in displayDict:
                        box.setChecked(False)
            else:
                # just clear the 'C' axes - this is the usual configuration
                axisCodeOptions.selectAll()
                for ii, box in enumerate(axisCodeOptions.checkBoxes):
                    if box.text().upper().startswith('C'):
                        axisCodeOptions.clearIndex(ii)

            # Label(_frame, '(double-width tolerances)', grid=(f_row, 1), gridSpan=(1, maxLen))
            f_row += 1
            LabeledHLine(_frame, text='Tolerances', grid=(f_row, 1), gridSpan=(1, maxLen),
                         colour=getColours()[SOFTDIVIDER], height=15)
            f_row += 1
            if self.application:
                spectraWidgets = {}  # spectrum.pid, frame dict to show/hide
                for row, spectrum in enumerate(validSpectrumViews.keys()):
                    f_row += 1
                    f = _SpectrumRow(parent=_frame,
                                     application=self.application,
                                     spectrum=spectrum,
                                     spectrumDisplay=displays[0],
                                     row=f_row, startCol=0,
                                     setLayout=True,
                                     visible=validSpectrumViews[spectrum])
                    spectraWidgets[spectrum.pid] = f

    def _spectrumDisplaySelectionPulldownCallback(self, data=None):
        """Notifier Callback for selecting a spectrumDisplay
        """
        texts = self.spectrumDisplayPulldown.getTexts()
        if ALL in texts:
            gids = self.project.spectrumDisplays
        else:
            gids = [self.application.getByGid(gid) for gid in texts if gid not in [ALL, SelectToAdd]]

        # check if display is deleted, removes from list if it has been. Data passed by notifier
        if data is not None and data.get(Notifier.TRIGGER) == 'delete':
            obj = data.get(Notifier.OBJECT)
            gids = [gg for gg in gids if gg and gg != obj]
        self._fillAllSpectrumFrame(gids)

        # if gid == '> All <':
        #     gids = [self.application.getByGid(gid) for gid in self.spectrumDisplayPulldown.getTexts() if gid not in ['> All <', '> Select <']]
        #     self._fillAllSpectrumFrame(gids)
        # else:
        #     self._fillSpectrumFrame([self.application.getByGid(gid)])


LINKTOPULLDOWNCLASS = 'linkToPulldownClass'
LINKTOACTIVESTATE = True

STOREDISPLAY = 'displaySettings'
STORESEQUENTIAL = 'sequentialStripsWidget'
STOREMARKS = 'markPositionsWidget'
STORECLEAR = 'autoClearMarksWidget'
STOREACTIVE = 'activePulldownClass'
STORELIST = 'listButtons'
STORENMRCHAIN = 'includeNmrChainPullSelection'


class StripPlot(Widget, _commonSettings, SignalBlocking):
    _storedState = {}

    def __init__(self, parent=None,
                 mainWindow=None,
                 callback=None,
                 returnCallback=None,
                 applyCallback=None,
                 includeDisplaySettings=True,
                 includeSequentialStrips=True,
                 includePeakLists=True, includeNmrChains=True, includeNmrChainPullSelection=False,
                 includeSpectrumTable=True,
                 defaultSpectrum=None,
                 activePulldownClass=None,
                 activePulldownInitialState=True,
                 labelText='Display(s) ',
                 **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
            displayText = [display.pid for display in self.application.ui.mainWindow.spectrumDisplays]
        else:
            self.application = None
            self.project = None
            self.current = None
            displayText = []

        self.callback = callback
        self.returnCallback = returnCallback or self.doCallback
        self.applyCallback = applyCallback

        self.includePeakLists = includePeakLists
        self.includeNmrChains = includeNmrChains
        self.includeNmrChainPullSelection = includeNmrChainPullSelection
        self.includeSpectrumTable = includeSpectrumTable
        self.activePulldownClass = activePulldownClass
        self.nmrChain = None

        # cannot set a notifier for displays, as these are not (yet?) implemented and the Notifier routines
        # underpinning the addNotifier call do not allow for it either
        row = 0
        colwidth = 180

        texts = [defaultSpectrum.pid] if (defaultSpectrum and defaultSpectrum is not NO_STRIP) else (
                [ALL] + displayText)

        if includeDisplaySettings:
            row += 1
            self.displaysWidget = SpectrumDisplaySelectionWidget(self, mainWindow=self.mainWindow, grid=(row, 0),
                                                                 gridSpan=(1, 1), texts=texts, displayText=[],
                                                                 objectWidgetChangedCallback=self._displayWidgetChanged,
                                                                 labelText=labelText)
        else:
            self.displaysWidget = None

        optionTexts = ['Show sequential strips',
                       'Mark positions',
                       'Auto clear marks']
        if self.activePulldownClass is not None:
            optionTexts += [f'Link to current {self.activePulldownClass.className}']
        _, maxDim = getTextDimensionsFromFont(textList=optionTexts)
        colwidth = maxDim.width()

        if includeSequentialStrips:
            row += 1
            self.sequentialStripsWidget = CheckBoxCompoundWidget(
                    self,
                    grid=(row, 0), vAlign='top', stretch=(0, 0), hAlign='left',
                    #minimumWidths=(colwidth, 0),
                    fixedWidths=(colwidth, None),
                    orientation='left',
                    labelText=optionTexts[0],
                    checked=False
                    )
        else:
            self.sequentialStripsWidget = None

        row += 1
        self.markPositionsWidget = CheckBoxCompoundWidget(
                self,
                grid=(row, 0), vAlign='top', stretch=(0, 0), hAlign='left',
                #minimumWidths=(colwidth, 0),
                fixedWidths=(colwidth, None),
                orientation='left',
                labelText=optionTexts[1],
                checked=True
                )

        row += 1
        self.autoClearMarksWidget = CheckBoxCompoundWidget(
                self,
                grid=(row, 0), vAlign='top', stretch=(0, 0), hAlign='left',
                #minimumWidths=(colwidth, 0),
                fixedWidths=(colwidth, None),
                orientation='left',
                labelText=optionTexts[2],
                checked=True
                )

        if self.activePulldownClass is not None:
            row += 1
            setattr(self, LINKTOPULLDOWNCLASS,
                    CheckBoxCompoundWidget(self, grid=(row, 0), vAlign='top', stretch=(0, 0), hAlign='left',
                                           fixedWidths=(colwidth, None),
                                           orientation='left',
                                           labelText=optionTexts[3],
                                           tipText=f'Set/update current {self.activePulldownClass.className} when selecting from pulldown',
                                           checked=activePulldownInitialState
                                           ))

        row += 1
        texts = []
        tipTexts = []
        callbacks = []
        buttonTypes = []

        # put hLine and text here

        self.NMRCHAINBUTTON = None

        if includePeakLists and includeNmrChains and includeNmrChainPullSelection:
            HLine(self, grid=(row, 0), gridSpan=(1, 4),
                  colour=getColours()[DIVIDER], height=15)
            row += 1
            Label(self, text='Strip Selection', grid=(row, 0), gridSpan=(1, 4))

        if includePeakLists:
            texts += ['use Peak selection']
            tipTexts += ['Use current selected peaks']
            callbacks += [partial(self._buttonClick, STRIPPLOT_PEAKS)]
            buttonTypes += [STRIPPLOT_PEAKS]

            texts += ['use NmrAtoms from Peak selection']
            tipTexts += ['Use all nmrAtoms from current selected peaks']
            callbacks += [partial(self._buttonClick, STRIPPLOT_NMRATOMSFROMPEAKS)]
            buttonTypes += [STRIPPLOT_NMRATOMSFROMPEAKS]

        if includeNmrChains:
            texts += ['use nmrResidue selection']
            tipTexts += ['Use current selected nmrResidues']
            callbacks += [partial(self._buttonClick, STRIPPLOT_NMRRESIDUES)]
            buttonTypes += [STRIPPLOT_NMRRESIDUES]

        if includeNmrChainPullSelection:
            # get the index of this button and set the required fields
            self.NMRCHAINBUTTON = len(texts)
            texts += ['use nmrChain']
            tipTexts += ['Use nmrResidues in selected nmrChain']
            callbacks += [partial(self._buttonClick, STRIPPLOT_NMRCHAINS)]
            buttonTypes += [STRIPPLOT_NMRCHAINS]

        row += 1
        self.listButtons = RadioButtons(self, texts=texts, tipTexts=tipTexts, callback=self._buttonClick,
                                        grid=(row, 0), direction='v') if texts else None
        if self.listButtons:
            self.listButtons.buttonTypes = buttonTypes

        if self.includeNmrChainPullSelection:
            # add a pulldown to select an nmrChain
            row += 1

            self.ncWidget = NmrChainPulldown(parent=self,
                                             mainWindow=self.mainWindow, default=None,
                                             #first NmrChain in project (if present)
                                             grid=(row, 0), gridSpan=(1, 1), minimumWidths=(0, 100),
                                             showSelectName=True,
                                             sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                             callback=self._selectionPulldownCallback
                                             )

        self._spectraWidget = None
        self.axisCodeOptions = None
        self.axisCodeOptionsDict = {}
        row += 1
        if includeSpectrumTable:
            HLine(self, grid=(row, 0), gridSpan=(1, 2),
                  colour=getColours()[DIVIDER], height=15)
            row += 1

            # create row's of spectrum information
            self._spectraRows = row + len(texts)

            self.spectrumDisplayOptionsFrame = Frame(self, setLayout=True, showBorder=False, fShape='noFrame',
                                                     grid=(row, 0), gridSpan=(row + 2, 0),
                                                     vAlign='top', hAlign='left')
            # Spectrum Display Options Frame
            # important part
            # add a new pullDown to select the active spectrumDisplay
            # self.spectrumDisplayPulldown = SpectrumDisplayPulldown(parent=self.spectrumDisplayOptionsFrame,
            #                                                        mainWindow=self.mainWindow, default=None,
            #                                                        grid=(0, 0), gridSpan=(1, 0),
            #                                                        minimumWidths=(0, colwidth),
            #                                                        showSelectName=True,
            #                                                        sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
            #                                                        callback=self._spectrumDisplaySelectionPulldownCallback,
            #                                                        labelText='Pick Peaks in Display'
            #                                                        )

            self.spectrumDisplayPulldown = SpectrumDisplaySelectionWidget(
                    parent=self.spectrumDisplayOptionsFrame,
                    mainWindow=self.mainWindow, grid=(0, 0),
                    gridSpan=(1, 0), texts=texts, displayText=[],
                    objectWidgetChangedCallback=self._spectrumDisplaySelectionPulldownCallback,
                    labelText='Pick Peaks in\n'
                              'Display')

            # self.spectrumDisplayPulldown.setTexts(['> All <'] + list(self.spectrumDisplayPulldown.getTexts()))

        # add a spacer in the bottom-right corner to stop everything moving
        rows = self.getLayout().rowCount()
        cols = self.getLayout().columnCount()
        Spacer(self, 5, 5,
               QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding,
               grid=(rows + 20, cols + 1), gridSpan=(1, 1))

        self.maxRows = rows
        self._registerNotifiers()

    def storeWidgetState(self):
        """Store the state of the checkBoxes between popups
        """
        if self.displaysWidget:
            StripPlot._storedState[STOREDISPLAY] = self.displaysWidget.getTexts()
        if self.sequentialStripsWidget:
            StripPlot._storedState[STORESEQUENTIAL] = self.sequentialStripsWidget.get()
        StripPlot._storedState[STOREMARKS] = self.markPositionsWidget.get()
        StripPlot._storedState[STORECLEAR] = self.autoClearMarksWidget.get()
        if self.activePulldownClass is not None:
            checked = getattr(self, LINKTOPULLDOWNCLASS).get()
            StripPlot._storedState[STOREACTIVE] = checked
        StripPlot._storedState[STORELIST] = self.listButtons.getIndex()
        if self.includeNmrChainPullSelection:
            StripPlot._storedState[STORENMRCHAIN] = self.ncWidget.getIndex()

    def restoreWidgetState(self):
        """Restore the state of the checkBoxes
        """
        with self.blockWidgetSignals():
            if self.displaysWidget:
                value = StripPlot._storedState.get(STOREDISPLAY, [])
                self.displaysWidget.setTexts(value)
            if self.sequentialStripsWidget:
                value = StripPlot._storedState.get(STORESEQUENTIAL, False)
                self.sequentialStripsWidget.set(value)
            value = StripPlot._storedState.get(STOREMARKS, True)
            self.markPositionsWidget.set(value)
            value = StripPlot._storedState.get(STORECLEAR, True)
            self.autoClearMarksWidget.set(value)
            if self.activePulldownClass is not None:
                value = StripPlot._storedState.get(STOREACTIVE, LINKTOACTIVESTATE)
                getattr(self, LINKTOPULLDOWNCLASS).set(value)
            value = StripPlot._storedState.get(STORELIST, 0)

            # with contextlib.suppress(Exception):
            if value < len(self.listButtons):
                self.listButtons.setIndex(value)

            if self.includeNmrChainPullSelection:
                value = StripPlot._storedState.get(STORENMRCHAIN, self.includeNmrChainPullSelection)
                self.ncWidget.setIndex(value)

    def setLabelText(self, label):
        """Set the text for the label attached to the list widget
        """
        self.displaysWidget.setLabelText(label) if self.displaysWidget else None

    def _displayWidgetChanged(self, data=None):
        """Handle adding/removing items from display selection
        """
        pass

        # if self.includeSpectrumTable:
        #     self._fillSpectrumFrame(self.displaysWidget._getDisplays())

    def _changeAxisCode(self):
        """Handle clicking the axis code buttons
        """
        pass

    def _buttonClick(self):
        """Handle clicking the peak/nmrChain buttons
        """
        if self.includeNmrChainPullSelection:
            self.ncWidget.setIndex(0, blockSignals=True)

    def _registerNotifiers(self):
        """Notifiers for responding to spectrumViews
        """
        # # can't use setNotifier as not guaranteed a parent abstractWrapperObject
        # self._spectrumViewNotifier = Notifier(self.project,
        #                                       [Notifier.CREATE, Notifier.DELETE, Notifier.CHANGE],  # DELETE not registering
        #                                       SpectrumView.className,
        #                                       self._spectrumViewChanged,
        #                                       onceOnly=True)
        ...

    def _unRegisterNotifiers(self):
        """Unregister notifiers
        """
        # if self._spectrumViewNotifier:
        #     self._spectrumViewNotifier.unRegister()
        if self.includeNmrChainPullSelection:
            self.ncWidget.unRegister()
        if self.includeSpectrumTable:
            self.spectrumDisplayPulldown._close()

    # not required as never called, now uses SpectrumDisplaySelectionWidget notifiers
    # def _spectrumViewChanged(self, data):
    #     """Respond to spectrumViews being created/deleted, update contents of the spectrumWidgets frame
    #     """
    #     if self.includeSpectrumTable:
    #         gid = self.spectrumDisplayPulldown.getText()
    #         # self._fillSpectrumFrame([self.application.getByGid(gid)], data)
    #         self._spectrumDisplaySelectionPulldownCallback({f'{self.application.getByGid(gid)}': data})
    #
    # def _spectrumViewVisibleChanged(self):
    #     """Respond to a visibleChanged in one of the spectrumViews
    #     """
    #     if self.includeSpectrumTable:
    #         # self._fillSpectrumFrame(self.displaysWidget._getDisplays())
    #         # gid = self.spectrumDisplayPulldown.getText()
    #         # self._fillSpectrumFrame([self.application.getByGid(gid)])
    #         self._spectrumDisplaySelectionPulldownCallback()

    def doCallback(self):
        """Handle the user callback
        """
        if self.callback:
            self.callback()

    def _returnCallback(self):
        """Handle the return from widget callback
        """
        pass

    def _cleanupWidget(self):
        """Cleanup the notifiers that are left behind after the widget is closed
        """
        self._unRegisterNotifiers()
        if self.displaysWidget:
            self.displaysWidget._close()

    def _selectionPulldownCallback(self, item):
        """Notifier Callback for selecting NmrChain
        """
        self.nmrChain = self.project.getByPid(item)
        if self.nmrChain is not None and self.NMRCHAINBUTTON is not None:
            # select the nmrChain here
            self.listButtons.setIndex(self.NMRCHAINBUTTON)


class _SpectrumRow(Frame):
    """Class to make a spectrum row
    """

    def __init__(self, parent, application, spectrum, spectrumDisplay, row=0, startCol=0, visible=True, **kwds):
        super().__init__(parent, **kwds)

        # col = 0
        # self.checkbox = CheckBoxCompoundWidget(self, grid=(0, col), gridSpan=(1, 1), hAlign='left',
        #                                        checked=True, labelText=spectrum.pid,
        #                                        fixedWidths=[100, 50])

        self.checkbox = Label(parent, spectrum.pid, grid=(row, startCol), gridSpan=(1, 1), hAlign='right')
        self.checkbox.setEnabled(visible)

        self.spinBoxes = []

        indices = getAxisCodeMatchIndices(spectrum.axisCodes, spectrumDisplay.axisCodes)
        _height = getFontHeight()

        for ii, axisCode in enumerate(spectrum.axisCodes):
            decimals, step = (2, 0.01) if axisCode[0:1] == 'H' else (1, 0.1)
            # col += 1
            if indices[ii] is None:
                continue

            ds = DoubleSpinBoxCompoundWidget(
                    parent, grid=(row, startCol + indices[ii] + 1), gridSpan=(1, 1), hAlign='left',
                    fixedWidths=(None, _height * 4),
                    labelText=axisCode,
                    value=spectrum.assignmentTolerances[ii],
                    decimals=decimals, step=step, minimum=step
                    )
            ds.setObjectName(str(spectrum.pid + axisCode))
            ds.setToolTip('Full width half height (ppm)')
            self.spinBoxes.append(ds)

            ds.setEnabled(visible)
            ds.setCallback(partial(self._setAssignmentTolerances, ds, spectrum, ii))

        # brush = (*hexToRgbRatio(spectrum.positiveContourColour), CCPNGLWIDGET_REGIONSHADE)
        # self.guiRegion = GLTargetButtonSpinBoxes(parent, application=application,
        #                                          orientation='v', brush=brush,
        #                                          grid=(row, col))

    def _setAssignmentTolerances(self, spinBox, spectrum, ii):
        """Set the tolerance in the attached spectrum from the spinBox value
        """
        assignment = list(spectrum.assignmentTolerances)
        assignment[ii] = float(spinBox.getValue())
        spectrum.assignmentTolerances = tuple(assignment)


SETTINGSCHECKBOX = 'checkBox'
SETTINGSWIDGET = 'widget'


class ModuleSettingsWidget(Widget):  #, _commonSettings):

    def __init__(self, parent=None,
                 mainWindow=None,
                 settingsDict=None,
                 callback=None,
                 returnCallback=None,
                 applyCallback=None,
                 defaultListItem=None,
                 **kwds):
        super().__init__(parent, setLayout=True, **kwds)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
            # displayText = [display.pid for display in self.application.ui.mainWindow.spectrumDisplays]
        else:
            self.application = self.project = self.current = None
            # displayText = []

        self.callback = callback
        self.returnCallback = returnCallback or self.doCallback
        self.applyCallback = applyCallback
        self.widgetsDict = {}

        # texts = [ALL] + defaultListItem.pid if defaultListItem else ([ALL] + displayText)
        # self.displaysWidget = SpectrumDisplaySelectionWidget(self, mainWindow=self.mainWindow, grid=(row, 0), gridSpan=(1, 1), texts=[ALL], displayText=[])
        # row += 1
        # self.chainsWidget = ChainSelectionWidget(self, mainWindow=self.mainWindow, grid=(row, 0), gridSpan=(1, 1), texts=[ALL], displayText=[], defaults=[ALL])

        self.checkBoxes = {}
        useInsideSpacer = False
        if settingsDict:
            optionTexts = [data['label'] for item, data in settingsDict.items()]
            _, maxDim = getTextDimensionsFromFont(textList=optionTexts)
            colwidth = maxDim.width()

            for row, (item, data) in enumerate(settingsDict.items(), start=1):

                # this is a fix to allow large widgets to expand with the settings-widget
                useInsideSpacer |= data.get('useInsideSpacer', False)

                if 'type' in data:
                    widgetType = data['type']
                    kws = {}
                    if widgetType == HLine:
                        # hack for a divider
                        if 'kwds' in data:
                            kws.update(data['kwds'])
                        newItem = widgetType(self, grid=(row, 0), colour=getColours()[DIVIDER], **kws, )

                    else:
                        if 'callBack' in data:  # this avoids a crash if the widget init doesn't have a callback/mainWindow arg
                            kws['callback'] = data['callBack']
                        kws['mainWindow'] = self.mainWindow
                        if 'kwds' in data:
                            kws.update(data['kwds'])
                            newItem = widgetType(self, grid=(row, 0), **kws, )
                        else:
                            newItem = widgetType(self, self.mainWindow, grid=(row, 0), **kws)

                else:
                    newItem = CheckBoxCompoundWidget(
                            self,
                            grid=(row, 0), vAlign='top', stretch=(0, 0), hAlign='left',
                            #minimumWidths=(colwidth, 0),
                            fixedWidths=(colwidth, None),
                            orientation='left',
                            labelText=data['label'] if 'label' in data else '',
                            tipText=data['tipText'] if 'tipText' in data else '',
                            checked=data['checked'] if 'checked' in data else False,
                            callback=data['callBack'] if 'callBack' in data else None,
                            # enabled=data['enabled']
                            )
                    # newItem.setCallback(data['callBack'] if 'callBack' in data else None)
                if 'enabled' in data:
                    newItem.setEnabled(data['enabled'])
                if 'visible' in data:
                    newItem.setVisible(data['visible'])
                self.widgetsDict[item] = newItem

                # need to check this - is confusing mix of widgets
                self.checkBoxes[item] = {'widget'    : newItem,
                                         'item'      : item,
                                         'signalFunc': None
                                         }
                if 'postInit' in data:
                    if func := data['postInit']:
                        func(newItem)

                # if data['_init']:
                #     # attach a one-off signal to the checkBox
                #     signalFunc = partial(self._checkInit, newItem, item, data)
                #     self.checkBoxes[item]['signalFunc'] = signalFunc
                #
                #     # connected = newItem.checkBox.connectNotify.connect(self._checkNotifier)
                #     stuff = newItem.checkBox.stateChanged.connect(signalFunc)
                #     print('>>>', stuff, id(stuff))

        # add a spacer in the bottom-right corner to stop everything moving
        rows = self.getLayout().rowCount()
        cols = self.getLayout().columnCount()
        Spacer(self, 5, 5,
               QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding,
               grid=(rows, cols - int(useInsideSpacer)), gridSpan=(1, 1))
        if useInsideSpacer:
            self.getLayout().setColumnStretch(cols - int(useInsideSpacer), 100)

        self.setMinimumWidth(self.sizeHint().width())
        self._registerNotifiers()

    def _changeAxisCode(self):
        """Handle clicking the axis code buttons
        """
        pass

    def _checkInit(self, checkBoxItem, item, data):
        """This is a hack so that the state changes when the layout loads
        After the layout initialise, this function is removed
        """
        # remove the one-off signal
        for vals in self.checkBoxes.values():
            if vals['item'] == item:
                checkBoxItem.checkBox.stateChanged.disconnect(vals['signalFunc'])
                # print('>>>_checkInit removed')

        # call the initialise function
        initFunc = data['_init']
        initFunc()

    def _registerNotifiers(self):
        """Notifiers for responding to spectrumViews
        """
        pass

    def _unRegisterNotifiers(self):
        """Unregister notifiers
        """
        pass

    def doCallback(self):
        """Handle the user callback
        """
        if self.callback:
            self.callback()

    def _returnCallback(self):
        """Handle the return from widget callback
        """
        pass

    def _cleanupWidget(self):
        """Cleanup the notifiers that are left behind after the widget is closed
        """
        self._unRegisterNotifiers()

    # def _getCheckBox(self, widgetName):
    #     """Get the required widget from the new setting Widget class
    #     Should be moved to a new settings class
    #     """
    #     if widgetName in self.checkBoxes and SETTINGSCHECKBOX in self.checkBoxes[widgetName]:
    #         return self.checkBoxes[widgetName][SETTINGSCHECKBOX]

    def getWidget(self, widgetName):
        """Get the required widget from the new setting Widget class
        Should be moved to a new settings class
        """
        if widgetName in self.checkBoxes and SETTINGSWIDGET in self.checkBoxes[widgetName]:
            return self.checkBoxes[widgetName][SETTINGSWIDGET]

        widget = self.widgetsDict.get(widgetName, None)
        return widget


class ObjectSelectionWidget(ListCompoundWidget):
    KLASS = None
    listChanged = pyqtSignal()

    def __init__(self, parent=None, mainWindow=None, vAlign='top', stretch=(0, 0), hAlign='left',
                 vPolicy='minimal', fixedWidths=(None, None, None), orientation='left',
                 labelText=None, tipText=None,
                 texts=None, callback=None, objectWidgetChangedCallback=None,
                 defaultListItem=None, displayText=None,
                 standardListItems=None,
                 **kwds):

        if not self.KLASS:
            raise RuntimeError('Klass must be specified')

        if displayText is None:
            displayText = []
        if standardListItems is None:
            standardListItems = [ALL]

        if not texts:
            texts = standardListItems + defaultListItem.pid if defaultListItem \
                else (standardListItems + displayText)

        if mainWindow:
            self.mainWindow = mainWindow
            self.application = mainWindow.application
            self.project = mainWindow.application.project
        else:
            self.mainWindow = self.application = self.project = None

        self._objectWidgetChangedCallback = objectWidgetChangedCallback
        self._selectObjectInListCallback = callback
        self.standardListItems = standardListItems
        labelName = self.KLASS._pluralLinkName[0].upper() + self.KLASS._pluralLinkName[1:]  #Keep CamelCase intact
        labelText = labelText or 'Select {}'.format(labelName)
        tipText = tipText or 'Set active {} for module'.format(labelName)

        super().__init__(parent=parent,
                         vAlign=vAlign, stretch=stretch, hAlign=hAlign, vPolicy=vPolicy,
                         fixedWidths=fixedWidths, orientation=orientation,
                         labelText=labelText, tipText=tipText, texts=texts,
                         callback=self._selectObjectInList, **kwds)

        # default to 5 rows
        self.setFixedHeights((None, None, 5 * getFontHeight()))
        self.setPreSelect(self._fillPulldownListWidget)

        # handle signals when the items in the displaysWidget have changed
        model = self.listWidget.model()
        # QT Lists add a default arg so needs Data=None (otherwise crashes)
        model.rowsInserted.connect(partial(self._objectWidgetChanged, data=None))
        model.rowsRemoved.connect(partial(self._objectWidgetChanged, data=None))
        self.listWidget.cleared.connect(partial(self._objectWidgetChanged, data=None))
        self.listWidget.changed.connect(self._passThroughListChanged)

        # Notifiers
        if self.project:
            self._notifierRename = Notifier(theObject=self.project,
                                            triggers=[Notifier.RENAME],
                                            targetName=self.KLASS.className,
                                            callback=self._objRenamedCallback)

            self._notifierDelete = Notifier(theObject=self.project,
                                            triggers=[Notifier.DELETE],
                                            targetName=self.KLASS.className,
                                            callback=self._objDeletedCallback)

            self._notifierCreate = Notifier(theObject=self.project,
                                            triggers=[Notifier.CREATE],
                                            targetName=self.KLASS.className,
                                            callback=self._objCreatedCallback)

        else:
            self._notifierRename = self._notifierDelete = None

    def _passThroughListChanged(self, *args, **kwds):
        """Pass through the signal from the listWidget."""
        self.listChanged.emit()

    def _close(self):
        """Unregister notifiers and close."""
        if self._notifierRename:
            self._notifierRename.unRegister()
            self._notifierRename = None
        if self._notifierDelete:
            self._notifierDelete.unRegister()
            self._notifierDelete = None

    def select(self, item, blockSignals=False):
        """Convenience: Set item in Pulldown; works with text or item"""

        # update the pulldown first. It could be it still not populated (e.g. only populates after you click in)
        self.updatePulldown()
        super().select(item, blockSignals)

    def setIndex(self, index, blockSignals=False):
        """Convenience: set item in Pulldown by index"""
        # update the pulldown first. It could be it still not populated (e.g. only populates after you click in)
        self.updatePulldown()
        super().select(index, blockSignals)

    def _selectObjectInList(self):
        """Handle clicking items in object selection
        """
        if self._selectObjectInListCallback:
            self._selectObjectInListCallback()

    def _objectWidgetChanged(self, data=None):
        """Handle adding/removing items from object selection
        """
        if self._objectWidgetChangedCallback:
            self._objectWidgetChangedCallback()

    def _objRenamedCallback(self, data):
        obj = data.get(Notifier.OBJECT)
        if obj:
            oldPid = data.get(Notifier.OLDPID)
            # get the old pid and replace with the new
            self.renameText(oldPid, obj.pid)

    def _objCreatedCallback(self, data):
        """
        Add the created object to listWidget
        """
        obj = data.get(Notifier.OBJECT)
        if obj:
            if ALL in self.getTexts():
                self._objectWidgetChanged()

    def _objDeletedCallback(self, data):
        """
        Remove the deleted object from listWidget
        """
        obj = data.get(Notifier.OBJECT)
        if obj:
            self.removeTexts([obj.pid])

    def _changeAxisCode(self):
        """Handle clicking the axis code buttons
        """
        pass

    def updatePulldown(self):
        self._fillPulldownListWidget()

    def _fillPulldownListWidget(self):
        """Fill the pulldownList with the currently available objects
        """
        ll = [SelectToAdd] + self.standardListItems
        pulldownObjs = [None] * len(ll)
        if self.project:
            objects = list(getattr(self.project, self.KLASS._pluralLinkName, []))
            ll += [obj.pid for obj in objects]
            pulldownObjs += objects
        self.pulldownList.setData(texts=ll, )  # objects=pulldownObjs)

    def _getObjects(self):
        """Return list of objects in the listWidget selection
        """
        if not self.project:
            return []
        pids = self.getTexts()
        objects = self.project.getObjectsByPids(pids)
        return objects

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.getTexts()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.setTexts(value)


class ChainSelectionWidget(ObjectSelectionWidget):
    KLASS = Chain


class SpectrumSelectionWidget(ObjectSelectionWidget):
    KLASS = Spectrum


class SpectrumGroupSelectionWidget(ObjectSelectionWidget):
    KLASS = SpectrumGroup


class NmrChainSelectionWidget(ObjectSelectionWidget):
    KLASS = NmrChain


class PeakListSelectionWidget(ObjectSelectionWidget):
    KLASS = PeakList


class UniqueNmrAtomNamesSelectionWidget(ObjectSelectionWidget):
    KLASS = NmrAtom

    def _fillPulldownListWidget(self):
        """Fill the pulldownList with the currently available objects
        """
        from ccpn.util.Common import sortByPriorityList

        priorityAtomNames = ['H', 'Hn' 'HA', 'HB', 'C', 'CA', 'CB', 'N', 'Nh', 'NE', 'ND']
        ll = [SelectToAdd] + self.standardListItems
        uniqueNames = set()
        if self.project:
            for obj in getattr(self.project, self.KLASS._pluralLinkName, []):
                uniqueNames.add(obj.name)
        uniqueNames = sortByPriorityList(list(uniqueNames), priorityAtomNames)
        complete = ll + uniqueNames
        self.pulldownList.setData(texts=complete)


class UniqueNmrResidueTypeSelectionWidget(ObjectSelectionWidget):
    KLASS = NmrResidue

    def _fillPulldownListWidget(self):
        """Fill the pulldownList with the currently available objects
        """
        from ccpn.util.Common import sortByPriorityList

        ## could add some priority list to show on top.
        ll = [SelectToAdd] + self.standardListItems
        uniqueNames = set()
        if self.project:
            for obj in getattr(self.project, self.KLASS._pluralLinkName, []):
                uniqueNames.add(obj.residueType)
        uniqueNames = list(uniqueNames)
        uniqueNames.sort(reverse=False)
        complete = ll + list(uniqueNames)
        self.pulldownList.setData(texts=complete)


class RestraintTableSelectionWidget(ObjectSelectionWidget):
    KLASS = RestraintTable


class DataTableSelectionWidget(ObjectSelectionWidget):
    KLASS = DataTable


class _SeriesInputDataTableSelectionWidget(ObjectSelectionWidget):
    KLASS = DataTable

    def _fillPulldownListWidget(self):
        """ Override original behavior to allow only the right dataType """

        import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
        from ccpn.framework.lib.experimentAnalysis.SeriesTables import InputSeriesFrameBC, ALL_SERIES_DATA_TYPES

        pulldown = self.pulldownList
        ll = [SelectToAdd] + self.standardListItems
        allowedDTs = []
        if self.project:
            for obj in getattr(self.project, self.KLASS._pluralLinkName, []):
                dataTable = obj
                dataTypeStr = dataTable.metadata.get(sv.SERIESFRAMETYPE, None)
                if dataTypeStr is not None:
                    allowedDTs.append(obj.pid)
        complete = ll + list(allowedDTs)
        pulldown.setData(texts=complete)


class ViolationTableSelectionWidget(ObjectSelectionWidget):
    KLASS = ViolationTable


class SpectrumDisplaySelectionWidget(ObjectSelectionWidget):
    """
    Spectrum Display Object Selection Widget
    .. Note:: Method for callback requires a data argument.
    """
    KLASS = SpectrumDisplay

    def getDisplays(self):
        """
        Return list of selected displays
        """
        if not self.application:
            return []

        displays = []
        gids = self.getTexts()
        if len(gids) == 0:
            return displays
        if ALL in gids:
            return self.mainWindow.spectrumDisplays
        if UseCurrent in gids:
            strip = self.application.current.strip
            if strip is not None:
                spectrumDisplay = strip.spectrumDisplay
                if spectrumDisplay:
                    return [spectrumDisplay]
        if UseLastOpened in gids:
            spectrumDisplay = self.mainWindow.moduleArea.spectrumDisplays[-1]
            return [spectrumDisplay]
        else:
            displays = self._getObjects()
            if IncludeCurrent in gids:
                if (strip := self.application.current.strip):
                    displays += [strip]  # fix for the minute - must check return type

        return displays

    def _objRenamedCallback(self, data):
        self._spectrumDisplayRenamed(data)

    def _spectrumDisplayRenamed(self, dataDict, **kwargs):
        # This method has been implemented only because
        # oldPid argument in data is not yet available for SpectrumDisplay
        obj = dataDict.get(Notifier.OBJECT)
        currentTexts = self.getTexts()
        toRemoveTexts = []
        for i in currentTexts:
            if i not in self.standardListItems and not self.application.getByGid(i):
                toRemoveTexts.append(i)
        self.removeTexts(toRemoveTexts)
        self.addText(obj.pid)

    def unRegister(self):
        """Unregister the notifiers; needs to be called when disgarding a instance
        """
        self.deleteNotifiers()

    def _objectWidgetChanged(self, data=None):
        """
        Handle adding/removing items from object selection
        Data will be passed to _objectWidgetChanged method
        """
        if self._objectWidgetChangedCallback:
            self._objectWidgetChangedCallback(data)

    def _objCreatedCallback(self, data):
        """
        Add the created object to listWidget
        Data will be passed to _objectWidgetChanged method
        """
        obj = data.get(Notifier.OBJECT)
        if obj:
            if ALL in self.getTexts():
                self._objectWidgetChanged(data)

    def _objDeletedCallback(self, data):
        """
        Remove the deleted object from listWidget
        Data will be passed to _objectWidgetChanged method
        """
        obj = data.get(Notifier.OBJECT)
        if obj:
            # when <Use All> in texts
            if ALL in (tt := self.getTexts()):
                if obj.pid in tt:
                    self.removeTexts([obj.pid])  # remove text if is also in listWidget
                else:
                    self._objectWidgetChanged(data)  # ensure update even if text isn't in listWidget
            else:
                self.removeTexts([obj.pid])


def main():
    import os
    import sys

    def myCallback(ph0, ph1, pivot, direction):
        print(ph0, ph1, pivot, direction)

    qtApp = QtWidgets.QApplication(['Test Phase Frame'])

    #QtCore.QCoreApplication.setApplicationName('TestPhasing')
    #QtCore.QCoreApplication.setApplicationVersion('0.1')

    widget = QtWidgets.QWidget()
    frame = StripPlot(widget, callback=myCallback)
    widget.show()
    widget.raise_()

    os._exit(qtApp.exec_())


if __name__ == '__main__':
    main()
