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
__dateModified__ = "$dateModified: 2024-08-23 19:21:56 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-05-20 12:59:02 +0100 (Fri, May 20, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, QtGui
from ccpn.util.Logging import getLogger
from ccpn.core.lib.Notifiers import Notifier
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiNamespaces as guiNameSpaces
from ccpn.util.Colour import colorSchemeTable, hexToRgb, rgbaRatioToHex, colourNameToHexDict
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiPanel import GuiPanel
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisToolBars import MainPlotToolBar
from ccpn.ui.gui.widgets.BarGraphWidget import BarGraphWidget, TICKOPTIONS, AllTicks, MinimalTicks
from ccpn.ui.gui.guiSettings import CCPNGLWIDGET_HEXBACKGROUND, GUISTRIP_PIVOT, CCPNGLWIDGET_HIGHLIGHT, CCPNGLWIDGET_LABELLING
from ccpn.ui.gui.guiSettings import getColours, DIVIDER
from ccpn.ui.gui.widgets.Font import getFont
from ccpn.ui.gui.widgets.Label import Label
from pyqtgraph import functions as fn
import numpy as np
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as seriesVariables
from ccpn.ui.gui.widgets.MessageDialog import showMessage
import pandas as pd
from functools import partial
from ccpn.util.Colour import hexToRgb, splitDataByColours
from ccpn.ui.gui.modules.experimentAnalysis.MainPlotWidgetBC import MainPlotWidget, PlotType


class MainPlotPanel(GuiPanel):

    position = 3
    panelName = guiNameSpaces.MainPlotPanel
    mainPlotWidget = None # created on the initWidgets

    def __init__(self, guiModule, *args, **Framekwargs):
        GuiPanel.__init__(self, guiModule,*args , **Framekwargs)
        self._appearancePanel = self.guiModule.settingsPanelHandler.getTab(guiNameSpaces.Label_GeneralAppearance)
        self._toolbarPanel = self.guiModule.panelHandler.getToolBarPanel()
        self._viewMode = guiNameSpaces.PlotViewMode_Mirrored
        self._lastViewMode = None
        self._plotType = PlotType.BAR.description
        self._plottedDf = None
        self._plotTitle = None

        ## Brush
        self._aboveBrush = guiNameSpaces.BAR_aboveBrushHex
        self._belowBrush = guiNameSpaces.BAR_belowBrushHex
        self._untraceableBrush = guiNameSpaces.BAR_untracBrushHex
        self._gradientbrushes = []
        self._tresholdLineBrush = None
        self._gradientbrushes = []

        _thresholdValueW = self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_ThreshValue)
        self._hThresholdValue = 1
        if _thresholdValueW:
            self._hThresholdValue = _thresholdValueW.getValue()

        #     current
        self._selectCurrentCONotifier = Notifier(self.current, [Notifier.CURRENT], targetName='collections',
                                                 callback=self._currentCollectionCallback, onceOnly=True)

        self.guiModule.mainTableChanged.connect(partial(self._mainTableChanged, False))
        self.guiModule.mainTableSortingChanged.connect(partial(self._mainTableChanged, False))
        self._setStyle()

    def _setStyle(self):
        QtWidgets.QApplication.instance()._sigPaletteChanged.connect(self._checkPalette)

    def _checkPalette(self, pal: QtGui.QPalette, *args):
        self._setColours()

    def _setColours(self):
        self.penColour = rgbaRatioToHex(*getColours()[CCPNGLWIDGET_LABELLING])
        self.backgroundColour = getColours()[CCPNGLWIDGET_HEXBACKGROUND]
        self.gridPen = pg.functions.mkPen(self.penColour, width=1, style=QtCore.Qt.SolidLine)
        self.gridFont = getFont()
        self.originAxesPen = pg.functions.mkPen(hexToRgb(getColours()[GUISTRIP_PIVOT]), width=1, style=QtCore.Qt.DashLine)
        self.scatterPen = pg.functions.mkPen(self.penColour, width=0.5, style=QtCore.Qt.SolidLine)
        self.selectedPointPen = pg.functions.mkPen(rgbaRatioToHex(*getColours()[CCPNGLWIDGET_HIGHLIGHT]), width=4)
        self.selectedLabelPen = pg.functions.mkBrush(rgbaRatioToHex(*getColours()[CCPNGLWIDGET_HIGHLIGHT]), width=4)
        if self.mainPlotWidget:
            self.mainPlotWidget.setBackgroundColour(self.backgroundColour)
            self.mainPlotWidget.plotItem.getAxis('bottom').setPen(self.gridPen)
            self.mainPlotWidget.plotItem.getAxis('left').setPen(self.gridPen)

    def initWidgets(self):
        ## this colour def could go in a higher position as they are same for all possible plots
        self._setColours()
        self.mainPlotWidget = MainPlotWidget(self,
                                             application=self.application,
                                             actionCallback=self._actionCallback,
                                             selectionCallback=self._selectionCallback,
                                             hoverCallback=self._mouseHoverCallbackEvent,
                                             lineMovedCallback = self._lineMovedCallback,
                                             grid=(1,0), gridSpan=(1, 2))


        self.toolbar = MainPlotToolBar(parent=self, plotItem=self.mainPlotWidget, guiModule=self.guiModule, grid=(0, 0), hAlign='l', hPolicy='preferred')
        self.currentCollectionLabel = Label(self , text='', grid=(0, 1), hAlign='r',)

    ###################################################################
    #########################     Public methods     #########################
    ###################################################################

    def updatePanel(self, keepZoom=False, *args, **kwargs):
        getLogger().debug('Updating  barPlot panel')
        dataFrame = self.guiModule.getVisibleDataFrame(includeHiddenColumns=True)
        plotType = self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_PlotType).getByText()
        self._plotType = plotType
        self._plotTitle = None # to reset
        if dataFrame is None:
            self.mainPlotWidget.clear()
            return
        vr = self.mainPlotWidget._viewRect
        self._appearancePanel._setThresholdValueForData()

        if self.viewMode == guiNameSpaces.PlotViewMode_Backbone:
            chainWidget = self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_Chain)
            if chainWidget is not None:
                pid = chainWidget.getText()
                chain = self.project.getByPid(pid)
                if chain is None:
                    msg = f'Changed view mode. Impossible to display by {self.viewMode}. No chains available in the project.'
                    getLogger().warning(msg)
                    showMessage('', msg)
                    plotTypeW = self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_PlotViewMode)
                    _lastViewMode = self._lastViewMode
                    if _lastViewMode is None:
                        _lastViewMode = guiNameSpaces.PlotViewMode_Mirrored
                    plotTypeW.setByText(_lastViewMode)
                    return
                dataFrame =  self._filterBySecondaryStructure(dataFrame, chain)
        self._plotDataFrame(dataFrame)
        if keepZoom:
            # restore the range as it was before the update
            self.mainPlotWidget._setViewRect(vr)
        else:
            self.fitXYZoom()

    @property
    def plotType(self):
        return self._plotType

    def setPlotType(self, plotType):

        if plotType not in self.mainPlotWidget.allowedPlotTypes:
            raise RuntimeError(f'Plot type {plotType} not implemented')
        self._plotType = plotType
        self.updatePanel(keepZoom=True)

    @property
    def plotTitle(self):
        if not self._plotTitle:
            resultDataTable = self.guiModule.backendHandler.resultDataTable
            if resultDataTable:
                self._plotTitle = resultDataTable.pid
        return self._plotTitle

    @plotTitle.setter
    def plotTitle(self, title:str):
        self._plotTitle = title

    @property
    def viewMode(self):
        return self._viewMode

    def setViewMode(self, mode):
        if mode not in guiNameSpaces.PlotViewModes:
            raise RuntimeError(f'View Mode {mode} not implemented')
        self._lastViewMode = self._viewMode
        self._viewMode = mode

    @property
    def xColumnName(self):
        """Returns selected X axis  Column  name from the settings widget """
        w = self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_MainPlotXcolumnName)
        selected = w.getText()
        tableDf = self.guiModule.getVisibleDataFrame(True)
        if not str(selected) in tableDf.columns:
            txt = f'No data for the selected item "{"Empty" if not selected else selected}". Selected a valid entry for plotting the the X Axis values '
            getLogger().warning(txt)
            return
        return selected

    @property
    def yColumnName(self):
        """Returns selected y Column name """
        w = self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_MainPlotYcolumnName)
        selected = w.getText()
        tableDf = self.guiModule.getVisibleDataFrame(True)
        if not str(selected) in tableDf.columns:
            txt = f'No data for the selected item "{"Empty" if not selected else selected}". Selected a valid entry for plotting the the Y Axis values '
            getLogger().warning(txt)
        return selected

    @property
    def thresholdValue(self):
        return self._hThresholdValue

    @thresholdValue.setter
    def thresholdValue(self, value):
        self._hThresholdValue = value

    def setYLabel(self, label=''):
        self.mainPlotWidget.plotWidget.setLabel('left', label)

    def setXLabel(self, label='', includeSortingLabel=True):
        htmlLabel = f'''<p><strong>{label}</strong></p> '''
        if includeSortingLabel:
            sortingLabel, sortOrder = self.guiModule._getSortingHeaderFromMainTable()
            if self.viewMode == guiNameSpaces.PlotViewMode_Backbone:
                sortingLabel, sortOrder = sv.NMRRESIDUECODE, 0  # this viewmode is only sorted by ResidueCode (ascending)
            if sortingLabel not in [label, '', ' ', None]:
                upSymbol = guiNameSpaces.TRIANGLE_UP_HTML
                downSymbol = guiNameSpaces.TRIANGLE_DOWN_HTML
                sortOrderIcon = upSymbol if sortOrder == 0 else downSymbol
                sortingLabel = f' (Sorted by {sortingLabel} {sortOrderIcon})'
                htmlLabel = f''' <p><strong>{label}</strong> <em>{sortingLabel}</em></p> '''  #Use HTML to have different fonts in the same label.

        self.mainPlotWidget.plotWidget.setLabel('bottom', htmlLabel)


    ####################################################################
    #########################     Private methods     #########################
    ####################################################################

    def _plotDataFrame(self, dataFrame):
        """ Plot the dataframe using information from the settings panel.
            Data is plotted in exactly the same sorting order as given as it usually mirrored to the main table view.
            See/use updatePanel.
         """
        if not self.xColumnName:
            return
        if not self.yColumnName:
            return
        if dataFrame is None or len(dataFrame)==0:
            return
        dataFrame.set_index(sv.INDEX, drop=False, inplace=True)
        # add threshold values/colours  to the dataframe  on-the-fly .
        dataFrame = self._setColoursByThreshold(dataFrame)
        dataFrame.loc[dataFrame.index, sv.INDEX] = dataFrame.index
        self._plottedDf = dataFrame
        hideThresholdLines = False
        if abs(self.thresholdValue) > np.abs(np.max(dataFrame[self.yColumnName]))*10:
            hideThresholdLines = True
            getLogger().warning(f'Threshold value of {self.thresholdValue} is too large to be displayed for the currently plotted data. Please reset from settings to re-enable the threshold line.' )

        self.mainPlotWidget.plotData(dataFrame,
                                     plotName=self.plotType,
                                     plotType=self.plotType,
                                     indicesColumnName=sv.INDEX,
                                     xColumnName= self.xColumnName,
                                     yColumnName=self.yColumnName,
                                     yErrColumnName=f'{self.yColumnName}{seriesVariables._ERR}',
                                     thresholdColumnName = guiNameSpaces.XTHRESHOLD,
                                     objectColumnName=seriesVariables.COLLECTIONPID,
                                     colourColumnName=guiNameSpaces.BRUSHLABEL,
                                     clearPlot=True,
                                     hideThresholdLines = hideThresholdLines,
                                     plotTitle = self.plotTitle
                                     )

        thresholdColour = dataFrame[guiNameSpaces.XthresholdBrush].values[-1]
        self.mainPlotWidget.thresholdsLineHandler.setColour(thresholdColour)
        self._updateAxisLabels()

    def _isItemToggledOn(self, itemName):
        action = self.toolbar.getButton(itemName)
        if action is not None:
            return action.isChecked()
        return False

    def _checkColumnType(self, selected):
        """Checks the column name from the settings and the main data. Returns the selected X axis data type.
        :return:  one of  float, int, str, None  """
        tableDf = self.guiModule.getVisibleDataFrame(True)
        if not str(selected) in tableDf.columns:
            txt = f'No data for the selected item "{"Empty" if not selected else selected}". Selected a valid entry for plotting the the X Axis values '
            getLogger().warning(txt)
            return
        return tableDf[selected].values.dtype

    @property
    def _xColumnType(self):
        """Checks the column name from the settings and the main data. Returns the selected X axis data type.
        :return:  one of  float, int, str, None  """
        return self._checkColumnType(self.xColumnName)

    @property
    def _yColumnType(self):
        """Checks the column name from the settings and the main data. Returns the selected X axis data type.
        :return:  one of  float, int, str, None  """
        return self._checkColumnType(self.yColumnName)

    def _mainTableChanged(self, keepZoom=False):
        if self.viewMode == guiNameSpaces.PlotViewMode_Backbone:
            getLogger().debug2(f'Plot view {self.viewMode}: Sorting/Filtering on the main table does not change the plot.')
            return
        self.updatePanel(keepZoom=keepZoom)  # zoom must be reset as data may have changed order

    @property
    def _aboveThresholdBrushColour(self):
        """Returns selected colour name """
        return self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_AboveThrColour).getText()

    @_aboveThresholdBrushColour.setter
    def _aboveThresholdBrushColour(self, colourName):
            w = self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_AboveThrColour)
            if w:
                w.select(colourName)

    @property
    def _belowThresholdBrushColour(self):
        """Returns selected colour name"""
        return self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_BelowThrColour).getText()

    @_belowThresholdBrushColour.setter
    def _belowThresholdBrushColour(self, colourName):
        w = self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_BelowThrColour)
        if w:
            w.select(colourName)

    @property
    def _untraceableBrushColour(self):
        """Returns selected colour name"""
        return self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_UntraceableColour).getText()

    @_untraceableBrushColour.setter
    def _untraceableBrushColour(self, colourName):
            w = self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_UntraceableColour)
            if w:
                w.select(colourName)

    @property
    def _thresholdBrushColour(self):
        """Returns selected colour name"""
        return self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_ThrColour).getText()

    @_thresholdBrushColour.setter
    def _thresholdBrushColour(self, colourName):
        if self._appearancePanel:
            w = self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_ThrColour)
            if w:
                w.select(colourName)

    @property
    def _rollingAverageBrushColour(self):
        """Returns selected colour name"""
        return self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_RALColour).getText()


    def _setCurrentCollectionsFromPids(self, pids):
        collections = self.project.getByPids(pids)
        self.current.collections = collections
        return collections

    def _actionCallback(self, data,  *args, **kwargs):
        """
        As Selection:
        Set Current Collection.
        Set current peaks from collection items,
        Navigate to first peak in collection if any,
        :param args:
        :param kwargs:
        :return:
        """
        self._selectionCallback(data, *args, **kwargs) #not sure if necessary
        if len(self.current.peaks) > 0:
            from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiModuleBC import _navigateToPeak
            _navigateToPeak(self.guiModule, self.current.peaks[-1])

    def _selectionCallback(self, data, *args, **kwargs):
        """
        Set Current Collection.
        Set current peaks from collection items"""
        pids = data.get('pids',[])
        collections = self._setCurrentCollectionsFromPids(pids)
        if len(collections)>0:
            collection = collections[0]
            if self.current.collection != collection:
                from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiModuleBC import getPeaksFromCollection
                peaks = getPeaksFromCollection(collection)
                self.current.peaks = peaks
                self.current.collection = collection

    def _mouseHoverCallbackEvent(self, data, *args, **kwargs):
        """ Feature disabled"""
        return
        mousePos =  data.get('mousePos', ['', ''])
        pids = data.get('pids', [])
        xs = data.get('xs', [])
        ys = data.get('xs', [])
        if len(pids)>0:
            pid = pids[0]
            x = xs[0]
            y = ys[0]
            txt = f'{pid}'
            self.currentCollectionLabel.setText(txt)
        else:
            self.currentCollectionLabel.clear()

    def _lineMovedCallback(self, position, name, *args, **kwargs):

        self.thresholdValue = float(position)
        self.updatePanel(keepZoom=True)
        # update the widgets as well
        tw =  self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_ThreshValue)
        optw =  self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_ThreshValueCalcOptions)

        if tw is not None:
            with tw.blockWidgetSignals():
                tw.setValue(float(position))
        if optw is not None:
            with optw.blockWidgetSignals():
                optw.select(guiNameSpaces.SELECT)

    def _updateAxisLabels(self):
        self.setXLabel(label=self.xColumnName)
        self.setYLabel(label=self.yColumnName)

    def fitYZoom(self):
        self.mainPlotWidget.setBestFitYZoom()

    def fitXZoom(self):
        self.mainPlotWidget.setBestFitXZoom()

    def fitXYZoom(self):
        self.mainPlotWidget.setBestFitXYZoom()

    def _setColoursByThreshold(self, dataFrame, ):
        """
        Add the colour definitions necessary for the plotting
        :param dataFrame:
        :return:
        """
        aboveDf = dataFrame[dataFrame[self.yColumnName] >= self.thresholdValue]
        belowDf = dataFrame[dataFrame[self.yColumnName] < self.thresholdValue]
        untraceableDd = dataFrame[dataFrame[self.yColumnName].isnull()]

        ## Brushes
        self._aboveBrush = colourNameToHexDict.get(self._aboveThresholdBrushColour, guiNameSpaces.BAR_aboveBrushHex)
        self._belowBrush = colourNameToHexDict.get(self._belowThresholdBrushColour, guiNameSpaces.BAR_belowBrushHex)
        self._untraceableBrush = colourNameToHexDict.get(self._untraceableBrushColour, guiNameSpaces.BAR_untracBrushHex)
        self._tresholdLineBrush = colourNameToHexDict.get(self._thresholdBrushColour, guiNameSpaces.BAR_thresholdLineHex)
        self._gradientbrushes = colorSchemeTable.get(self._aboveThresholdBrushColour, []) #in case there is one.
        if len(self._gradientbrushes)>0:
            aboveValues = aboveDf[self.yColumnName].values
            _aboveBrush = splitDataByColours(aboveValues, self._gradientbrushes)
        else:
            _aboveBrush = self._aboveBrush
        dataFrame.loc[aboveDf.index, guiNameSpaces.BRUSHLABEL] = _aboveBrush
        dataFrame.loc[belowDf.index, guiNameSpaces.BRUSHLABEL] = self._belowBrush
        dataFrame.loc[untraceableDd.index, guiNameSpaces.BRUSHLABEL] = self._untraceableBrush
        dataFrame.loc[dataFrame.index, guiNameSpaces.XTHRESHOLD] = self.thresholdValue
        dataFrame.loc[dataFrame.index, guiNameSpaces.XthresholdBrush] = self._tresholdLineBrush

        return dataFrame


        # windowRollingAverage =  self._appearancePanel.getWidget(guiNameSpaces.WidgetVarName_WindowRollingAverage).getValue()
        # rollingAverage = calculateRollingAverage(y, windowRollingAverage)
        # self._rollingAverageBrush = colourNameToHexDict.get(self.rollingAverageBrushColour, guiNameSpaces.BAR_rollingAvLine)
        # xR = np.arange(1,len(rollingAverage)+1)
        # self.rollingAverageLine = self.barGraphWidget.plotWidget.plotItem.plot(xR, rollingAverage, pen=self._rollingAverageBrush)

    def _updateThresholdValueFromSettings(self, value, *args):
        self.thresholdValue = value

    def _filterBySecondaryStructure(self, dataFrame, chain):
        df = dataFrame
        backboneAtomsComb = ['H,N', 'Hn,Nh']  # hack while developing the feature. This has to be replaced with information from the MoleculeDefinitions
        codes = chain._sequenceCodesAsIntegers
        expandedSequenceResCodes = np.arange(min(codes), max(codes) + 1)  #make sure we have all residues codes ( chain can have gaps if altered by the users)
        filteredDf = pd.DataFrame()
        bbRows = []
        # filterDataFrame by the chain code first
        if not seriesVariables.NMRCHAINNAME in df:
            return filteredDf
        chainCode = chain.name
        df = df[df[seriesVariables.NMRCHAINNAME] == chainCode]
        for resCode in expandedSequenceResCodes:
            availableResiduesCodes = df[seriesVariables.NMRRESIDUECODE].values
            if not str(resCode) in availableResiduesCodes:
                filteredDf.loc[resCode, df.columns] = 0
                filteredDf.loc[resCode, seriesVariables.NMRRESIDUECODE] = str(resCode)
                filteredDf.loc[resCode, seriesVariables.NMRCHAINNAME] = chainCode
                continue
            nmrResiduesCodeDF = df[df[seriesVariables.NMRRESIDUECODE] == str(resCode)]
            # search for the BB atoms
            for ix, row in nmrResiduesCodeDF.iterrows():
                atomNames = row[seriesVariables.NMRATOMNAMES]
                if not isinstance(atomNames, str):
                    continue
                if atomNames in backboneAtomsComb:
                    bbRows.append(row)
                    filteredDf.loc[resCode, df.columns] = row.values
        filteredDf[sv.INDEX] = np.arange(1, len(filteredDf) + 1)
        return filteredDf

    def _setXAxisTickOption(self, value):
        self.mainPlotWidget._setTickOption(value)

    def _toggleBars(self, setVisible=True):
        self.mainPlotWidget.barsHandler.setItemsVisible(setVisible)

    def _toggleScatters(self, setVisible=True):
        self.mainPlotWidget.scattersHandler.setItemsVisible(setVisible)

    def _toggleErrorBars(self, setVisible=True):
        self.mainPlotWidget.errorBarsHandler.setItemsVisible(setVisible)

    def _toggleRollingAverage(self, setVisible=True):
        self.rollingAverageLine.setVisible(setVisible)

    def _currentCollectionCallback(self, *args):
        # select collection on table.
        backendHandler = self.guiModule.backendHandler
        df = self._plottedDf
        if df is None:
            return
        pids = [co.pid for co in self.current.collections]
        # tablePids =  df[df[sv.COLLECTIONPID].isin(pids)]
        # if tablePids.empty:
        #     return

        self.mainPlotWidget.selectByPids(pids)


