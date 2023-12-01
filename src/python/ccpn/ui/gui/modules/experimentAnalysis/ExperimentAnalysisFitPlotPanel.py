#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2023"
__credits__ = ("Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2023-12-01 17:34:21 +0000 (Fri, December 01, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-05-20 12:59:02 +0100 (Fri, May 20, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from collections import OrderedDict as od
from ccpn.util.Common import percentage
from ccpn.util.floatUtils import numZeros
from ccpn.util.Logging import getLogger
from ccpn.core.Peak import Peak
from ccpn.core.lib.Notifiers import Notifier
from ccpn.util.Colour import hexToRgb, rgbaRatioToHex
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import pyqtgraph as pg
from pyqtgraph.graphicsItems.ROI import Handle
from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.ui.gui.guiSettings import CCPNGLWIDGET_HEXBACKGROUND, CCPNGLWIDGET_LABELLING
from ccpn.ui.gui.guiSettings import getColours
from ccpn.ui.gui.widgets.Font import getFont
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiPanel import GuiPanel
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisToolBars import ExperimentAnalysisPlotToolBar
from ccpn.ui.gui.widgets.ViewBox import CrossHair
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.CustomExportDialog import CustomExportDialog
from ccpn.ui.gui.widgets.MessageDialog import showWarning, showInfo

class FittingPlotToolBar(ExperimentAnalysisPlotToolBar):

    def __init__(self, parent, plotItem, guiModule, **kwds):
        super().__init__(parent, plotItem=plotItem, guiModule=guiModule, **kwds)

        self.fittingPanel = parent

    def getToolBarDefs(self):
        toolBarDefs = super().getToolBarDefs()
        extraDefs = (
            ('FittedCurve', od((
                ('text', 'Toggle Fitted Curve'),
                ('toolTip', 'Toggle the Fitted Curve'),
                ('icon', Icon('icons/curveFit')),
                ('callback', self._toggleFittedCurve),
                ('enabled', True),
                ('checkable', True)
                ))),
            ('RawData', od((
                ('text', 'ToggleRawDataScatter'),
                ('toolTip', 'Toggle the RawData Scatter Plot'),
                ('icon', Icon('icons/curveFitScatter')),
                ('callback', self._toggleRawDataScatter),
                ('enabled', True),
                ('checkable', True)
            ))))
        toolBarDefs.update(extraDefs)
        return toolBarDefs

    def _toggleFittedCurve(self):
        action = self.sender()
        self.fittingPanel._toggleFittedData(action.isChecked())

    def _toggleRawDataScatter(self):
        action = self.sender()
        self.fittingPanel.toggleRawData(action.isChecked())

class FitPlotPanel(GuiPanel):

    position = 2
    panelName = 'FitPlotPanel'

    def __init__(self, guiModule, *args, **Framekwargs):
        GuiPanel.__init__(self, guiModule, showBorder=True, *args , **Framekwargs)
        self.fittedCurve = None #not sure if this var should Exist
        self.rawDataScatterPlot = None

    def initWidgets(self):

        self.backgroundColour = getColours()[CCPNGLWIDGET_HEXBACKGROUND]
        self._setExtraWidgets()
        self._selectCurrentCONotifier = Notifier(self.current, [Notifier.CURRENT], targetName='collections',
                                                 callback=self._currentCollectionCallback, onceOnly=True)
        self._setXLabel(label='X')
        self._setYLabel(label='Y')
        self.labels = []

    def updatePanel(self, *args, **kwargs):
        try:
            self.plotCurrentData()
        except Exception as error:
            getLogger().warning(f'Cannot plot fitted data. {error}')

    def plotCurrentData(self, *args):
        """ Plot a curve based on Current Collection.
         Get Plotting data from the Output-GUI-dataTable (getSelectedOutputDataTable)"""

        self.clearData()

        backend = self.guiModule.backendHandler
        ## Get the raw data from the output DataTable if any or return
        outputData = backend.resultDataTable
        if outputData is None:
            return

        ## Check if the current Collection pids are in the Table. If Pids not on table, return.
        dataFrame = backend._resultDataFrameWithExclusions
        pids = [co.pid for co in self.current.collections]
        filtered = dataFrame.getByHeader(sv.COLLECTIONPID, pids)
        if filtered.empty:
            return

        ## Consider only the last selected Collection.
        lastCollectionPid = filtered[sv.COLLECTIONPID].values[-1]
        filteredDf = dataFrame[dataFrame[sv.COLLECTIONPID] == lastCollectionPid]

        ## Grab the Fitting Model from the dataTable and NOT from the module. The model is needed to recreate the fitted Curve from the fitting results.
        if not sv.MODEL_NAME in filteredDf.columns:
            self.bindingPlot.setTitle(f'Fitting not available')
            return

        modelName = filteredDf.modelName.values[-1]
        fittingModelClass = backend.getFittingModelByName(modelName)
        if fittingModelClass:
            model = fittingModelClass()
            isModelRestored = True
        else:
            showWarning('Cannot show fitting line', f'No model found with name {modelName}')
            model = backend.currentFittingModel
            isModelRestored = False
            yf = None

        ## Grab the Pids/Objs for each spot in the scatter plot. Peaks
        peakPids = filteredDf[sv.PEAKPID].values
        objs = [self.project.getByPid(pid) for pid in peakPids]

        ## Grab the columns to plot the raw data, the header name from the model
        Xs = filteredDf[model.xSeriesStepHeader].values
        Ys = filteredDf[model.ySeriesStepHeader].values

        ## Grab the Fitting function from the model and its needed Args from the DataTable. (I.e. Kd, Decay etc)
        func = model.getFittingFunc(model)
        funcArgs = model.modelArgumentNames
        argsFit = filteredDf.iloc[0][funcArgs]
        fittingArgs = argsFit.astype(float).to_dict()

        ## Add and extra of filling data at the end of the fitted curve to don't just sharp end on the last raw data Point
        extra = percentage(50, max(Xs))
        initialPoint = min(Xs)
        finalPoint = max(Xs) #+ extra

        ## Build the fitted curve arrays
        if isModelRestored:
            xf = np.linspace(initialPoint, finalPoint, 3000)
            yf = func(xf, **fittingArgs)

        ## Grab the axes label
        seriesUnits = filteredDf[sv.SERIESUNIT].values
        if len(seriesUnits) > 0:
            seriesUnit = seriesUnits[0]
        else:
            seriesUnit = 'X (Series Unit Not Given)'
        xAxisLabel = seriesUnit
        yAxisLabel =  backend._minimisedProperty or 'Y'
        ## Setup the various labels.
        self.currentCollectionLabel.setText('')
        self._setXLabel(label=xAxisLabel)
        self._setYLabel(label=yAxisLabel)
        labelText = f'{lastCollectionPid}'
        if len(self.current.collections) > 1:
            labelText += f' - (Last selected)'
        self.currentCollectionLabel.setText(labelText)

        ## Plot the fittedCurve
        if yf is None:
            yf = [0]*len(xf)
        self.fittedCurve = self.bindingPlot.plot(xf, yf, pen=self.bindingPlot.gridPen)

        ## Plot the Raw Data
        spots = []
        self.labels = []
        for obj, x, y in zip(objs, Xs, Ys):
            brush = pg.mkBrush(255, 0, 0)
            dd = {'pos': [0, 0], 'data': 'obj', 'brush': brush, 'symbol': 'o', 'size': 10, 'pen': None}
            dd['pos'] = [x, y]
            dd['data'] = obj
            if obj is None:
                continue
            if hasattr(obj.spectrum, 'positiveContourColour'):  # colour from the spectrum.
                brush = pg.functions.mkBrush(hexToRgb(obj.spectrum.positiveContourColour))
                dd['brush'] = brush
            spots.append(dd)
            label = _CustomLabel(obj=obj, textProperty='id')
            self.bindingPlot.addItem(label)
            label.setPos(x, y)
            self.labels.append(label)

        self.rawDataScatterPlot = pg.ScatterPlotItem(spots)
        self.bindingPlot.addItem(self.rawDataScatterPlot)
        self.bindingPlot.scene().sigMouseMoved.connect(self.bindingPlot.mouseMoved)
        self.bindingPlot.setTitle(f'Fitting Model: {modelName}')
        self.bindingPlot.zoomFull()

        if sv.EXCLUDED_NMRRESIDUEPID in filteredDf:
            isResidueExcluded = filteredDf[sv.EXCLUDED_NMRRESIDUEPID].values
            if any(isResidueExcluded):
                self.bindingPlot.setTitle(f'Fitting not available. Selected NmrResidue is excluded from Fittings')

    def _isOkToPlot(self):
        """ Do the initial check if is ok to continue ith the plotting """
        ## Get the current Collections if any or return
        collections = self.current.collections
        if not collections:
            return False
        backend = self.guiModule.backendHandler
        ## Grab the Fitting Model, to recreate the fitted Curve from the fitting results.
        model = backend.currentFittingModel
        calcModel = backend.currentCalculationModel
        if model.modelName == sv.BLANKMODELNAME:
            getLogger().info(f'Fitting results not displayed/permitted on Calculation Model: {calcModel.modelName} and Fitting Model: {model.modelName}')
            return False
        if calcModel is not None:
            if calcModel._disableFittingModels:
                getLogger().info(f'Fitting results not displayed/permitted on Calculation Model: {calcModel.modelName} and Fitting Model: {model.modelName}')
                return False
        return True

    def _setXLabel(self, label=''):
        self.bindingPlot.setLabel('bottom', label)

    def _setYLabel(self, label=''):
        self.bindingPlot.setLabel('left', label)

    def _setExtraWidgets(self):
        ###  Plot setup
        self._bindingPlotView = pg.GraphicsLayoutWidget()
        self._bindingPlotView.setBackground(self.backgroundColour)
        self.bindingPlot = _FittingPlot(parentWidget=self)
        self.toolbar = FittingPlotToolBar(parent=self, plotItem=self.bindingPlot, guiModule=self.guiModule,
                                          grid=(0, 0), gridSpan=(1, 2), hAlign='l', hPolicy='preferred')
        self.currentCollectionLabel = Label(self, text='', grid=(0, 2), hAlign='r',)
        self._bindingPlotView.addItem(self.bindingPlot)
        self.getLayout().addWidget(self._bindingPlotView, 1,0,1,3)

    def _currentCollectionCallback(self, *args):
        if self.current.collection is None:
            self.clearData()
            return
        df = self.guiModule.getVisibleDataFrame(includeHiddenColumns=True)
        if df is None or df.empty:
            self.clearData()
            return
        pids = [co.pid for co in self.current.collections]
        filtered = df.getByHeader(sv.COLLECTIONPID, pids)
        if not filtered.empty:
            self.updatePanel()

    def clearData(self):
        self.bindingPlot.clear()
        self.currentCollectionLabel.clear()

    def _toggleRawDataLabels(self, setVisible=True):
        for la in self.labels:
            la.setVisible(setVisible)

    def toggleRawData(self, setVisible=True):
        """Show/Hide the raw data from the plot Widget """
        if self.rawDataScatterPlot is not None:
            self.rawDataScatterPlot.setVisible(setVisible)
            self._toggleRawDataLabels(setVisible)

    def _toggleFittedData(self, setVisible=True):
        """Show/Hide the fitted data from the plot Widget """
        if self.fittedCurve is not None:
            self.fittedCurve.setVisible(setVisible)

    def close(self):
        self._selectCurrentCONotifier.unRegister()

#### Implementation widgets

class _LeftAxisItem(pg.AxisItem):
    """ Overridden class for the left axis to show minimal decimals and stop resizing to massive space.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(orientation='left', *args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        """ Overridden method to show minimal decimals.
        """
        newValues = []
        for val in values:
            try:
                maxDecimalToShow = 3
                if abs(val) > 1e6:  # make it scientific annotation if a huge/tiny number
                    value = f'{val:.{maxDecimalToShow}e}'
                elif numZeros(val) >= maxDecimalToShow:
                    #e.g.:  if is 0.0001 will show as 1e-4 instead of 0.000
                    value = f'{val:.{maxDecimalToShow}e}'
                else:
                    # just rounds to the third decimal
                    value = f'{val:.{maxDecimalToShow}f}'
            except Exception:
                value = str(val)

            newValues.append(value)
        return newValues

class _FittingPlot(pg.PlotItem):
    # TO be replaced with a multiplot instance.

    def __init__(self, parentWidget, *args, **kwargs):
        pg.PlotItem.__init__(self, axisItems={'left': _LeftAxisItem()}, **kwargs)
        self.parentWidget = parentWidget

        colour = rgbaRatioToHex(*getColours()[CCPNGLWIDGET_LABELLING])
        self.gridPen = pg.functions.mkPen(colour, width=1, style=QtCore.Qt.SolidLine)
        self.gridFont = getFont()
        self.toolbar = None
        self.setMenuEnabled(False)
        self.getAxis('bottom').setPen(self.gridPen)
        self.getAxis('left').setPen(self.gridPen)
        self.getAxis('bottom').tickFont = self.gridFont
        self.getAxis('left').tickFont = self.gridFont
        self.exportDialog = None
        self._bindingPlotViewbox = self.vb
        self._bindingPlotViewbox.mouseClickEvent = self._viewboxMouseClickEvent
        self.autoBtn.mode = None
        self.buttonsHidden = True
        self.autoBtn.hide()
        self.crossHair = CrossHair(plotWidget=self)

    def clear(self):
        """
        Remove all items from the ViewBox.
        """
        for i in self.items[:]:
            if not isinstance(i, (pg.InfiniteLine,Handle)):
                self.removeItem(i)
        self.avgCurves = {}

    def setToolbar(self, toolbar):
        self.toolbar = toolbar

    def zoomFull(self):
        self.fitXZoom()
        self.fitYZoom()

    def fitXZoom(self):
        xs,ys = self._getPlotData()
        if xs is not None and len(xs)>0:
            x,y = xs[-1], ys[-1]
            if len(x) > 0:
                xMin, xMax = min(x), max(x)
                try:
                    self.setXRange(xMin, xMax, padding=None, update=True)
                except:
                    getLogger().debug2('Cannot fit XZoom')

    def fitYZoom(self):
        xs, ys = self._getPlotData()
        if xs is not None and len(xs) > 0:
            x, y = xs[-1], ys[-1]
            if len(y) > 0:
                yMin, yMax = min(y), max(y)
                try:
                    self.setYRange(yMin, yMax, padding=None, update=True)
                except:
                    getLogger().debug2('Cannot fit XZoom')

    def _getPlotData(self):
        xs = []
        ys = []
        for item in self.dataItems:
            if hasattr(item, 'getData'):
                x,y = item.getData()
                xs.append(x)
                ys.append(y)
        return xs,ys

    def _viewboxMouseClickEvent(self, event, *args):
        if event.button() == QtCore.Qt.RightButton:
            event.accept()
            self._raiseContextMenu(event)

    def mouseMoved(self, event):
        position = event
        mousePoint = self._bindingPlotViewbox.mapSceneToView(position)
        x = mousePoint.x()
        y = mousePoint.y()
        self.crossHair.setPosition(x, y)
        label = f'x:{round(x,3)} \ny:{round(y,3)}'
        self.crossHair.hLine.label.setText(label)

    def _getContextMenu(self):
        self.contextMenu = Menu('', None, isFloatWidget=True)
        self.contextMenu.addAction('Export', self.showExportDialog)
        return self.contextMenu

    def _raiseContextMenu(self, event):
        contextMenu = self._getContextMenu()
        contextMenu.exec_(QtGui.QCursor.pos())

    def showExportDialog(self):
        if self.exportDialog is None:
            scene =  self._bindingPlotViewbox.scene()
            self.exportDialog = CustomExportDialog(scene, titleName='Exporting')
        self.exportDialog.show(self)

class _CustomLabel(QtWidgets.QGraphicsSimpleTextItem):
    """ A text annotation of a scatterPlot.
        """
    def __init__(self, obj, brush=None, textProperty='pid', labelRotation = 0, application=None):
        QtWidgets.QGraphicsSimpleTextItem.__init__(self)
        self.textProperty = textProperty
        self.obj = obj
        self.displayProperty(self.textProperty)
        self.setRotation(labelRotation)
        # self.setDefaultFont() #this oddly set the font to everything in the program!
        if brush:
            self.setBrush(brush)
        else:
            self.setBrushByObject()
        self.setFlag(self.ItemIgnoresTransformations + self.ItemIsSelectable)
        self.application = application

    def setDefaultFont(self):
        font = getFont()
        # height = getFontHeight(size='SMALL') #SMALL is still to large
        font.setPointSize(10)
        self.setFont(font) #this oddly set the font to everything in the program!

    def setBrushByObject(self):
        brush = None
        if isinstance(self.obj, Peak):
            brush = pg.functions.mkBrush(hexToRgb(self.obj.peakList.textColour))
        if brush:
            self.setBrush(brush)

    def displayProperty(self, theProperty):
        text = getattr(self.obj, theProperty)
        self.setText(str(text))
        self.setToolTip(f'Displaying {theProperty} for {self.obj}')

    def setObject(self, obj):
        self.obj = obj

    def getCustomObject(self):
        return self.customObject

    def paint(self, painter, option, widget):
        # self._selectCurrent()
        QtWidgets.QGraphicsSimpleTextItem.paint(self, painter, option, widget)
