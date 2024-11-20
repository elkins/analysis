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
__dateModified__ = "$dateModified: 2024-11-20 13:19:03 +0000 (Wed, November 20, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-05-20 12:59:02 +0100 (Fri, May 20, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np

from ccpn.core.lib.OrderedSpectrumViews import mainTest
from ccpn.util.DataEnum import DataEnum
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.util.Logging import getLogger
from ccpn.core.lib.Notifiers import Notifier
import numpy as np
from functools import partial
######## gui/ui imports ########
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiPanel import GuiPanel
import ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiNamespaces as guiNameSpaces
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as seriesVariables
from ccpn.ui.gui.widgets.table.Table import Table
from ccpn.ui.gui.widgets.MessageDialog import showWarning


class _NavigateTrigger(DataEnum):
    """
    _NavigateTrigger = 0 # status: No callback, don't navigate to SpectrumDisplay.
    _NavigateTrigger = 1 # status: Callback on single click, navigate to SpectrumDisplay at each table selection.
    _NavigateTrigger = 2 # status: Callback on double click, navigate only with a doubleClick on a table row.
    """
    DISABLED = 0, guiNameSpaces.Disabled
    SINGLECLICK = 1, guiNameSpaces.SingleClick
    DOUBLECLICK = 2, guiNameSpaces.DoubleClick


#=========================================================================================
# _ExperimentalAnalysisTableABC
#=========================================================================================

class _ExperimentalAnalysisTableABC(Table):
    """
    A table to display results from the series Analysis DataTables and interact to source spectra on SpectrumDisplays.
    """
    className = '_TableWidget'
    defaultHidden = []
    _internalColumns = []
    _hiddenColumns = []
    _defaultEditable = False
    _enableDelete = False
    _enableSearch = True
    _enableCopyCell = True
    _enableExport = True

    _OBJECT = sv.COLLECTIONPID

    def __init__(self, parent, mainWindow=None, guiModule=None, **kwds):
        """Initialise the widgets for the module.
        """
        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow

        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = None
            self.project = None
            self.current = None

        kwds['setLayout'] = True

        # initialise the currently attached dataFrame
        # initialise the table
        super().__init__(parent=parent, **kwds)

        self._hiddenColumns = [sv._ROW_UID, sv.COLLECTIONID, sv.PEAKPID, sv.NMRRESIDUEPID, sv.NMRCHAINNAME,
                               sv.NMRRESIDUETYPE, sv.NMRATOMNAMES, sv.SERIESUNIT, sv.SPECTRUMPID,
                               sv.VALUE, sv.VALUE_ERR,
                               sv.SERIES_STEP_X, sv.SERIES_STEP_Y, sv.MINIMISER_METHOD, sv.MINIMISER_MODEL, sv.CHISQR,
                               sv.REDCHI, sv.AIC, sv.BIC,
                               sv.MODEL_NAME, sv.NMRRESIDUECODETYPE]
        self._internalColumns = [sv.INDEX]
        errCols = [tt for tt in self.columns if sv._ERR in tt]
        self._hiddenColumns += errCols
        self.setDefaultColumns(self._hiddenColumns)
        self.guiModule = guiModule
        self.moduleParent = guiModule
        self._selectionHeader = sv.COLLECTIONPID

    def _postInit(self):
        super()._postInit()
        # Initialise the notifier for processing dropped items
        self._navigateTrigger = _NavigateTrigger.SINGLECLICK  # Default Behaviour
        navigateTriggerName = self.guiModule.getSettings(grouped=False).get(guiNameSpaces.WidgetVarName_NavigateToOpt)
        self.setNavigateToPeakTrigger(navigateTriggerName)
        self._selectCurrentCONotifier = Notifier(self.current, [Notifier.CURRENT], targetName='collections',
                                                 callback=self._currentCollectionCallback, onceOnly=True)
        self.sortingChanged.connect(self._tableSortingChangedCallback)
        self.tableChanged.connect(self._tableChangedCallback)

    #-----------------------------------------------------------------------------------------
    # dataFrame
    #-----------------------------------------------------------------------------------------

    def _tableSortingChangedCallback(self, *args):
        """   Fire a notifier for other widgets to refresh their ordering (if needed). """
        self.guiModule.mainTableSortingChanged.emit()

    def _tableChangedCallback(self, *args):
        """   Fire a notifier for other widgets to refresh their ordering (if needed). """
        self.guiModule.mainTableSortingChanged.emit()

    @property
    def dataFrame(self):
        return self._dataFrame

    @dataFrame.setter
    def dataFrame(self, dataFrame):
        selectedRows = self.getSelectedData()
        self._dataFrame = dataFrame
        self.build(dataFrame)
        if self._selectionHeader in self.columns and len(selectedRows) > 0:
            selPids = selectedRows[sv.COLLECTIONPID].values
            self.selectRowsByValues(selPids, sv.COLLECTIONPID, scrollToSelection=True, doCallback=True)

    def build(self, dataFrame):
        if dataFrame is not None:
            self.updateDf(df=dataFrame)
            self.setDefaultColumns(self._hiddenColumns)
            self._setBlankModelColumns()
            self._hideExcludedColumns()
            self._setExclusionColours()

    #-----------------------------------------------------------------------------------------
    # Selection/action callbacks
    #-----------------------------------------------------------------------------------------

    def selectionCallback(self, selected, deselected, selection, lastItem):
        """Set the current collection and navigate to SpectrumDisplay if the trigger is enabled as singleClick. """
        from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiModuleBC import _navigateToPeak, \
            getPeaksFromCollection

        collections = self.getSelectedCollections()
        if len(collections) == 0:
            return
        peaks = getPeaksFromCollection(collections[-1])
        self.current.collections = collections
        self.current.peaks = peaks
        if len(peaks) == 0:
            return
        if self._navigateTrigger == _NavigateTrigger.SINGLECLICK:
            _navigateToPeak(self.guiModule, self.current.peaks[-1])

    def actionCallback(self, selection, lastItem):
        """Perform a navigate to SpectrumDisplay if the trigger is enabled as doubleClick"""
        if self._navigateTrigger == _NavigateTrigger.DOUBLECLICK:
            from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiModuleBC import _navigateToPeak

            _navigateToPeak(self.guiModule, self.current.peaks[-1])

    def setNavigateToPeakTrigger(self, trigger):
        """
        Set the navigation Trigger to single/Double click or Disabled when selecting a row on the table.
        :param trigger: int or str, one of _NavigateTrigger value or name. See _NavigateTrigger for details.
        :return: None
        """
        for enumTrigger in _NavigateTrigger:
            if enumTrigger == trigger or enumTrigger.description == trigger:
                self._navigateTrigger = enumTrigger
                return

    #-----------------------------------------------------------------------------------------
    # Handle drop events
    #-----------------------------------------------------------------------------------------

    def _processDroppedItems(self, data):
        """
        CallBack for Drop events
        """
        pids = data.get('pids', [])
        # self._handleDroppedItems(pids, KlassTable, self.moduleParent._modulePulldown)
        getLogger().warning('Drop not yet implemented for this module.')

    #-----------------------------------------------------------------------------------------
    # Table context menu
    #-----------------------------------------------------------------------------------------

    def _raiseTableContextMenu(self, pos):
        """
        Re-implementation to dynamically grey-out items before popping
        """
        outputData = self.guiModule.backendHandler.resultDataTable
        if outputData is None:
            super()._raiseTableContextMenu(pos)

        if (menu := self._thisTableMenu):
            excludeNmrResidueAction = menu.getActionByName(guiNameSpaces.EXCLUDE_NMRRESIDUES)
            includeNmrResidueAction = menu.getActionByName(guiNameSpaces.INCLUDE_NMRRESIDUES)
            selectedNmrResidues = self.getSelectedNmrResidues()
            enable = len(selectedNmrResidues) > 0
            includeNmrResidueAction.setEnabled(enable)
            excludeNmrResidueAction.setEnabled(enable)
        super()._raiseTableContextMenu(pos)

    # add edit/add parameters to meta-data table
    def addTableMenuOptions(self, menu):
        super().addTableMenuOptions(menu)
        editCollection = menu.addAction('Edit Collection', self._editCollection)
        refitSingular = menu.addAction('Refit Collection(s) Individually...', partial(self._refitSeletected, False))
        refitGroup = menu.addAction('Refit Collections Globally...', partial(self._refitSeletected, True))
        _separator = menu.insertSeparator(editCollection)
        excludeNmrResidue = menu.addAction(guiNameSpaces.EXCLUDE_NMRRESIDUES, self._excludeNmrResidues)
        includeNmrResidue = menu.addAction(guiNameSpaces.INCLUDE_NMRRESIDUES, self._includeNmrResidues)
        excludeNmrResidue.setEnabled(False)
        includeNmrResidue.setEnabled(False)
        _separator = menu.insertSeparator(excludeNmrResidue)

    def _refitSeletected(self, globally=False):
        from ccpn.ui.gui.popups._RefitSeriesPopup import RefitIndividualPopup, RefitGloballyPopup

        collections = self.getSelectedCollections()
        if len(collections) > 0:
            if globally:
                popup = RefitGloballyPopup(self, seriesAnalysisModule=self.guiModule, globalFit=False,
                                           collectionsData=self.getSelectedData())
            else:
                popup = RefitIndividualPopup(self, seriesAnalysisModule=self.guiModule, globalFit=False,
                                             collectionsData=self.getSelectedData())
            popup.show()
            popup.raise_()
        else:
            showWarning('Cannot refit', 'Nothing selected')

    def _editCollection(self):
        from ccpn.ui.gui.popups.CollectionPopup import CollectionPopup

        collections = self.getSelectedCollections()
        if len(collections) > 0:
            co = collections[-1]
            if co is not None:
                popup = CollectionPopup(self, mainWindow=self.mainWindow, obj=co, editMode=True)
                popup.exec()
                popup.raise_()

    def _excludeNmrResidues(self):
        nmrResidues = self.getSelectedNmrResidues()
        if len(nmrResidues) > 0:
            exclusionHandler = self.guiModule.backendHandler.exclusionHandler
            outputData = self.guiModule.backendHandler.resultDataTable
            excludedNmrResidues = exclusionHandler.getExcludedNmrResidues(dataTable=outputData)
            newExclusion = set(excludedNmrResidues + nmrResidues)
            exclusionHandler.setExcludedNmrResidues(newExclusion, dataTable=outputData)
            self.guiModule.updateAll()

    def _includeNmrResidues(self):
        nmrResidues = self.getSelectedNmrResidues()
        if len(nmrResidues) > 0:
            exclusionHandler = self.guiModule.backendHandler.exclusionHandler
            outputData = self.guiModule.backendHandler.resultDataTable
            excludedNmrResidues = exclusionHandler.getExcludedNmrResidues(dataTable=outputData)
            newExclusion = [nr for nr in excludedNmrResidues if nr not in nmrResidues]
            exclusionHandler.setExcludedNmrResidues(newExclusion, dataTable=outputData)
            self.guiModule.updateAll()

    def getSelectedData(self):
        return self.selectedRows()

    def getSelectedCollections(self):
        selectedRowsDf = self.getSelectedData()
        collections = set()
        for ix, selectedRow in selectedRowsDf.iterrows():
            coPid = selectedRow[sv.COLLECTIONPID]
            co = self.project.getByPid(coPid)
            collections.add(co)
        return list(collections)

    def getSelectedNmrResidues(self):
        selectedRowsDf = self.getSelectedData()
        nmrResidues = set()
        # if not sv.NMRRESIDUEPID in selectedRowsDf:
        #     showWarning(f'This table does not contain the requeired field {sv.NMRRESIDUEPID}',
        #                 'You might need to recreate this dataTable for some features to be available.' )

        for ix, selectedRow in selectedRowsDf.iterrows():
            if sv.NMRRESIDUEPID in selectedRowsDf:
                nmrResiduePid = selectedRow[sv.NMRRESIDUEPID]
                nmrResidue = self.project.getByPid(nmrResiduePid)
                nmrResidues.add(nmrResidue)
        return list(nmrResidues)

    def _currentCollectionCallback(self, *args):
        # select collection on table.
        if self.current.collection is None:
            self.clearSelection()
            return
        df = self.guiModule.getVisibleDataFrame(includeHiddenColumns=True)
        if df is None:
            return
        pids = [co.pid for co in self.current.collections]
        self.selectRowsByValues(pids, headerName=sv.COLLECTIONPID)

    def _hideExcludedColumns(self):
        """Remove columns from table which contains the prefix excluded_ """
        headers = []
        columnTexts = self.columns
        for columnText in columnTexts:
            columnText = str(columnText)
            if columnText.startswith(sv.EXCLUDED_):
                headers.append(columnText)
        self._setVisibleColumns(headers, False)

    def _setExclusionColours(self):

        self.setRowsForegroundByValues(['True'], sv.EXCLUDED_NMRRESIDUEPID, '#8c0307')

    def setRowsForegroundByValues(self, values, headerName, hexColour):
        """
        Select rows if the given values are present in the table.
        :param values: list of value to select
        :param headerName: the column name for the column where to search the values
        :param scrollToSelection: navigate to the table to show the result
        :return: None
        """
        if self._df is None or self._df.empty:
            return
        if headerName not in self._df.columns:
            return

        model = self.model()
        columnTextIx = self.columns.index(headerName)
        for i in model._sortIndex:
            cell = model.index(i, columnTextIx)
            if cell is None:
                continue
            tableValue = cell.data()
            for valueToSelect in values:
                if tableValue == valueToSelect:
                    rowIndex = model.index(i, 0)
                    if rowIndex is None:
                        continue
                    for columnIndex, value in enumerate(self.columns):
                        self.setForeground(i, columnIndex, hexColour)

    def _setBlankModelColumns(self):
        # if a blank model: toggle the columns from table (no point in showing empty columns)
        fitModel = self.guiModule.backendHandler.currentFittingModel
        calModel = self.guiModule.backendHandler.currentCalculationModel
        apperanceTab = self.guiModule.settingsPanelHandler.getTab(guiNameSpaces.Label_GeneralAppearance)
        tableHeaderWidget = apperanceTab.getWidget(guiNameSpaces.WidgetVarName_TableView)
        if tableHeaderWidget is not None:
            if fitModel and fitModel.modelName == sv.BLANKMODELNAME:
                # tableHeaderWidget.untickTexts([guiNameSpaces._Fitting, guiNameSpaces._Stats])
                self._toggleFittingHeaders(False)
                self._toggleStatsHeaders(False)
                self._toggleFittingErrorsHeaders(False)
            if calModel and calModel.modelName == sv.BLANKMODELNAME:
                # tableHeaderWidget.untickTexts([guiNameSpaces._Calculation])
                self._toggleCalculationHeaders(False)
                self._toggleCalculationErrorsHeaders(False)

    def _setVisibleColumns(self, headers, setVisible):
        cols = self.columns
        for header in headers:
            if header not in cols:
                continue
            self.setColumnHidden(cols.index(str(header)), not setVisible)

    ## Convient Methods to toggle groups of header: toggle---Header
    ## TableGrouppingHeaders = [_Assignments, _SeriesSteps, _Calculation, _Fitting, _Stats, _Errors]
    ## Called from settings Pannel in an autogenerated fashion, don't change signature.
    def _toggleSeriesStepsHeaders(self, setVisible=True):
        """
        Show/Hide the rawData columns"""
        headers = self.guiModule.backendHandler._getSeriesStepValues()
        # need to include also the headers which are duplicates and include an _ (underscore at the end)
        extraHeaders = []
        for header in headers:
            for columnHeader in self.columns:
                if str(columnHeader).startswith(str(header)) and sv.SEP in columnHeader:
                    extraHeaders.append(columnHeader)
        headers += extraHeaders
        self._setVisibleColumns(headers, setVisible)

    def _toggleAssignmentsHeaders(self, setVisible=True):
        """ Show/Hide the assignments columns"""
        headers = sv.AssignmentPropertiesHeaders
        self._setVisibleColumns(headers, setVisible)

    def _toggleErrorsHeaders(self, setVisible=True):
        """ Show/Hide the Fitting/Calculation error columns"""
        headers = [tt for tt in self.columns if sv._ERR in tt]
        self._setVisibleColumns(headers, setVisible)

    def _toggleCalculationErrorsHeaders(self, setVisible=True):
        """ Show/Hide the Calculation error columns"""
        headers = []
        calcModel = self.guiModule.backendHandler.currentCalculationModel
        if calcModel is not None:
            headers = calcModel.modelArgumentErrorNames
            headers = calcModel.modelArgumentErrorNames
        self._setVisibleColumns(headers, setVisible)

    def _toggleFittingErrorsHeaders(self, setVisible=True):
        """ Show/Hide the Fitting error columns"""
        headers = []
        fittingModel = self.guiModule.backendHandler.currentFittingModel
        if fittingModel is not None:
            headers = fittingModel.modelArgumentErrorNames
        self._setVisibleColumns(headers, setVisible)

    def _toggleCalculationHeaders(self, setVisible=True):
        """ Show/Hide the Calculation columns"""
        headers = []
        calcModel = self.guiModule.backendHandler.currentCalculationModel
        if calcModel is not None:
            headers = calcModel.modelArgumentNames
        self._setVisibleColumns(headers, setVisible)

    def _toggleFittingHeaders(self, setVisible=True):
        """ Show/Hide the Fitting columns"""
        headers = []
        fittingModel = self.guiModule.backendHandler.currentFittingModel
        if fittingModel is not None:
            headers = fittingModel.modelArgumentNames
        self._setVisibleColumns(headers, setVisible)

    def _toggleStatsHeaders(self, setVisible=True):
        """ Show/Hide the Fitting stats columns"""
        headers = []
        fittingModel = self.guiModule.backendHandler.currentFittingModel
        if fittingModel is not None:
            headers = fittingModel.modelStatsNames
        self._setVisibleColumns(headers, setVisible)

    def clearSelection(self):
        super().clearSelection()
        self.current.collections = []
        self.guiModule.updateAll()


#=========================================================================================
# TablePanel
#=========================================================================================

class TablePanel(GuiPanel):
    position = 1
    panelName = 'TablePanel'
    TABLE = _ExperimentalAnalysisTableABC

    def __init__(self, guiModule, *args, **Framekwargs):
        GuiPanel.__init__(self, guiModule, *args, **Framekwargs)

    def initWidgets(self):
        row = 0
        # Label(self, 'TablePanel', grid=(row, 0))
        self.mainTable = self.TABLE(self,
                                    mainWindow=self.mainWindow,
                                    guiModule=self.guiModule,
                                    grid=(0, 0), gridSpan=(1, 2))

    def setInputData(self, dataFrame):
        """Provide the DataFrame to populate the table."""
        self.mainTable.dataFrame = dataFrame

    def updatePanel(self, *args, **kwargs):
        dataFrame = self.guiModule.backendHandler.getResultDataFrame(useFiltered=True)
        self.setInputData(dataFrame)
        # update here the X-Y selectors on the settings. Has to be done here because the mainplot has to be in sync with the table.
        appearance = self.guiModule.settingsPanelHandler.getTab(guiNameSpaces.Label_GeneralAppearance)
        appearance._setXYAxisSelectors()

    def close(self):
        if self.mainTable:
            self.mainTable.close()
        super().close()

    # def clearData(self):
    #     self.mainTable.dataFrame = None
    #     self.mainTable.clearTable()
