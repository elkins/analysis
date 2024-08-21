"""
A popup specific for the Experiment Analysis module
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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-08-21 13:51:14 +0100 (Wed, August 21, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from tqdm import tqdm
from ccpn.util.floatUtils import formatValue
from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.util.Logging import getLogger
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking
from ccpn.framework.Application import getApplication, getCurrent, getProject, getMainWindow
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.Label import Label
import ccpn.ui.gui.widgets.CompoundWidgets as cw
from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame


LastFittingResults = 'Last Fitting results'
ReCalculate = 'Re-Calculate'


class _RefitSelectedSeriesPopup(CcpnDialogMainWidget):
    """
    A popup specific for the Experiment Analysis module.
    """
    FIXEDWIDTH = False
    FIXEDHEIGHT = False
    TITLE = 'Refit Selected Series Popup'
    isGlobalFit = False
    _columnWidth = 200

    def __init__(self, parent, seriesAnalysisModule, collectionsData=None, **kwds):

        super().__init__(parent, setLayout=True, windowTitle=self.TITLE, **kwds)
        self.mainWindow = getMainWindow()
        self.application = getApplication()
        self.project = getProject()
        self.current = getCurrent()
        self.collectionsData = collectionsData
        self._paramsDicts = {}
        self.seriesAnalysisModule = seriesAnalysisModule
        self._backendHandler = self.seriesAnalysisModule.backendHandler
        self.setWidgets()
        self._populate()

        # enable the buttons
        self.setOkButton(callback=self._okClicked, text='Refit', tipText='Refit Series using the selected options')
        self.setCloseButton(callback=self.reject, tipText='Close popup')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)
        # initialise the buttons and dialog size
        self._postInit()
        self.getLayout().setSizeConstraint(QtWidgets.QLayout.SetNoConstraint)

    def getCollectionsPids(self):
        collectionsPids = set()
        for ix, selectedRow in self.collectionsData.iterrows():
            coPid = selectedRow[sv.COLLECTIONPID]
            collectionsPids.add(coPid)
        return list(collectionsPids)

    def getCollections(self):
        collections = [self.project.getByPid(coPid) for coPid in self.getCollectionsPids()]
        return collections

    def _getCurrentMinimiserMethod(self):
        method = self.collectionsData.get(sv.MINIMISER_METHOD, np.array([None]))[-1]
        return method

    def _getCurrentModelName(self):
        modelName = self.collectionsData.get(sv.MODEL_NAME, np.array([None]))[-1]
        if modelName is None:
            modelName =  self._backendHandler.currentFittingModel.modelName
        return modelName

    def _createFitWidget(self, frame):
        """Create the specific widget depending on the fitting approach (individual or global)."""

    def setWidgets(self):
        row  = 0
        self._maxSpanW = 3
        texts = self.getCollectionsPids()
        fText = '\n'.join(texts)
        self.collectionPidsWidgets = cw.PlainListCompoundWidget(self.mainWidget, labelText='Selected',
                                                            texts=texts, grid=(row, 0),  fixedWidths=(self._columnWidth, self._columnWidth), gridSpan=(1, 2),
                                                            compoundKwds={'allowSelections':False, 'contextMenu':False})

        row += 1
        self.fittingModelWidget = cw.PulldownListCompoundWidget(self.mainWidget, labelText='Fitting Model',
                                                              grid=(row, 0), fixedWidths=(self._columnWidth, self._columnWidth))
        self._fittingModelPullDown = self.fittingModelWidget.pulldownList
        row += 1
        self.minimiserMethodWidget = cw.PulldownListCompoundWidget(self.mainWidget, labelText='Minimiser Method',
                                                                   grid=(row, 0), fixedWidths=(self._columnWidth, self._columnWidth), callback=None)
        self._minimiserMethodPullDown = self.minimiserMethodWidget.pulldownList
        row += 1

        # Initial Values. Different widgets if we are in global or individual fit.
        row += 1
        _frame = MoreLessFrame(self.mainWidget, name='Initial Fitting Params',
                               showMore=False, grid=(row, 0),
                               _frameMargins=(10,10,10,10),  # l, t, r, b
                               gridSpan=(1, 2))
        self._fittingContentsFrame = _frame.contentsFrame
        self._createFitWidget(self._fittingContentsFrame)
        row += 1
        self.fittingModelWidget.pulldownList.activated.connect(self._populateFittingValues)
        self.mainWidget.getLayout().setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def _populate(self):
        ## add Fitting  models
        currentModelName = self._getCurrentModelName()
        models = self._backendHandler.fittingModels
        modelNames = list(models.keys())
        self._fittingModelPullDown.setData(modelNames)
        ## do initial selection given the current knowledge
        with self._fittingModelPullDown.blockWidgetSignals():
            self._fittingModelPullDown.select(currentModelName)

        ## add minimiserMethods
        currentMinimiserMethod= self._getCurrentMinimiserMethod()
        minimiserMethods = list(sv.MINIMISER_METHODS.keys())
        self._minimiserMethodPullDown.setData(minimiserMethods)
        with self._minimiserMethodPullDown.blockWidgetSignals():
            self._minimiserMethodPullDown.select(currentMinimiserMethod)

    def _populateFittingValues(self, value):
        self._fittingContentsFrame._clear()
        self._createFitWidget(self._fittingContentsFrame)

    def _getGlobalMeanValuesData(self):
        """ Get a DataFrame with the mean of all global Params (per column). """
        df = self.collectionsData
        model = self.fetchFittingModel()
        funcArgs = model.modelGlobalParamNames
        argsInDf = set(funcArgs).issubset(df.columns)
        if argsInDf:
            argsFit = df[funcArgs]
            meanRowDf = argsFit.mean().to_frame().T
            return meanRowDf

    def _getFixedValues(self):
        """
        Get the fixed Param Values
        :return:
        """
        df = self.collectionsData
        values = []
        for name in self._getFixedParamNames():
            if name in df:
                v = formatValue(df[name].values[-1])
            else:
                v = 'N/A'
            values.append(v)
        return values

    def fetchFittingModel(self):
        modelName = self._fittingModelPullDown.getText()
        fittingModelClass = self._backendHandler.getFittingModelByName(modelName)
        if fittingModelClass:
            fittingModel = fittingModelClass()
        else:
            fittingModel = self._backendHandler.currentFittingModel
        return fittingModel

    def getMinimiserMethod(self):
        return self._minimiserMethodPullDown.getText()

    def _getGlobalParamNames(self):
        return self.fetchFittingModel().modelGlobalParamNames

    def _getFixedParamNames(self):
        return self.fetchFittingModel().modelFixedParamNames

    def _getLocalParamNames(self):
        allParams =  self.fetchFittingModel().modelArgumentNames
        nonLocalParams = self._getGlobalParamNames() + self._getFixedParamNames()
        return [x for x in allParams if x not in nonLocalParams]

    def _updateParentModule(self):
        _needsRefitting = self._backendHandler._needsRefitting
        self._backendHandler._needsRefitting = False
        self.seriesAnalysisModule.updateAll(refit=False)
        self._backendHandler._needsRefitting = _needsRefitting

    def _okClicked(self):

        self._initialiseFit()
        self._updateParentModule()
        self.accept()

    def _initialiseFit(self):
        pass


class RefitIndividualPopup(_RefitSelectedSeriesPopup):
    """
    A popup specific for  Refitting Collection(s) Individually
    """

    TITLE = 'Refit Collection(s) Individually '
    isGlobalFit = False

    def __init__(self, parent, seriesAnalysisModule, collectionsData=None, **kwds):
        super().__init__(parent, seriesAnalysisModule, collectionsData=collectionsData, **kwds)

    # def _createFitWidget(self, row):
    #     row += 1
    #     return row

    def _initialiseFit(self):
        fittingModel = self.fetchFittingModel()
        with undoBlockWithoutSideBar():
            for collection in tqdm(self.getCollections()):
                self._backendHandler.refitSingularCollection(collection.pid,
                                                             fittingModel=fittingModel,
                                                             minimiserMethod=self.getMinimiserMethod(),
                                                             )


class RefitGloballyPopup(_RefitSelectedSeriesPopup):
    """
    A popup specific for  Refitting Collection(s) Individually
    """

    TITLE = 'Refit Collections Globally'
    isGlobalFit = True

    def __init__(self, parent, seriesAnalysisModule, collectionsData=None, **kwds):
        super().__init__(parent, seriesAnalysisModule, collectionsData=collectionsData, **kwds)



    def _createFitWidget(self, frame):
        fittingModel = self.fetchFittingModel()

        row = 0
        self.headerLabels = cw.LabelCompoundWidget(frame, labelText='Parameter',
                                                   label2Text='Value', grid=(row, 1), gridSpan=(1, 2),
                                                   fixedWidths=(100, self._columnWidth))
        row += 1
        globParams = self._getGlobalParamNames()
        if len(globParams)>0:
            paramsGlobalLabel = Label(frame, text='Global(s)', grid=(row, 0))
            for globName in self._getGlobalParamNames():
                globalMeanValuesData = self._getGlobalMeanValuesData()
                value = 'N/A'
                if globalMeanValuesData is not None:
                    value = formatValue(globalMeanValuesData[globName].values[-1])
                globalParams = cw.LabelCompoundWidget(frame, labelText=globName,
                                                           label2Text=value, grid=(row, 1), gridSpan=(1, 2),
                                                           fixedWidths=(100, self._columnWidth))
                row += 1
        ## do the locals
        locParams = self._getLocalParamNames()
        if len(locParams) > 0:
            paramsLocalLabel = Label(frame, text='Local(s)', grid=(row, 0))
            for localName in self._getLocalParamNames():
                value = 'N/A'
                paramLabel = cw.LabelCompoundWidget(frame, labelText=localName,
                                                      label2Text=value, grid=(row, 1), gridSpan=(1, 2),
                                                      fixedWidths=(100, self._columnWidth))
                row += 1
        ## do the Fixed
        fixParams = self._getFixedParamNames()
        if len(fixParams) > 0:
            paramsFixedLabel = Label(frame, text='Fixed', grid=(row, 0))
            for fixedParamName, value in zip(self._getFixedParamNames(), self._getFixedValues()):
                paramLabel = cw.LabelCompoundWidget(frame, labelText=fixedParamName,
                                                    label2Text=value, grid=(row, 1), gridSpan=(1, 2),
                                                    fixedWidths=(100, self._columnWidth))
                row += 1



    def _initialiseFit(self):

        with undoBlockWithoutSideBar():
             self._backendHandler.refitGlobalCollections(self.getCollectionsPids(),
                                                                globalParamNames=self._getGlobalParamNames(),
                                                                localParamNames=self._getLocalParamNames(),
                                                                fixedParamNames=self._getFixedParamNames(),
                                                                 fittingModel=self.fetchFittingModel(),
                                                                 minimiserMethod=self.getMinimiserMethod(),
                                                             )
