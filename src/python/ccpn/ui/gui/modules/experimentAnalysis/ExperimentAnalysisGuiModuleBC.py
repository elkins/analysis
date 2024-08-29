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
__dateModified__ = "$dateModified: 2024-08-29 16:53:21 +0100 (Thu, August 29, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-05-20 12:59:02 +0100 (Fri, May 20, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

######## core imports ########
from PyQt5.QtCore import pyqtSignal
from ccpn.framework.Application import getApplication, getCurrent, getProject
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisNotifierHandler import CoreNotifiersHandler
from ccpn.framework.lib.experimentAnalysis.backends.SeriesAnalysisABC import SeriesAnalysisABC
from ccpn.util.Logging import getLogger
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
import numpy as np
import pandas as pd

######## gui/ui imports ########
from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiManagers import PanelHandler,\
    SettingsPanelHandler, IOHandler, PluginsHandler
import ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiNamespaces as guiNameSpaces
import ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiSettingsPanel as settingsPanel
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisToolBars import ToolBarPanel, PanelUpdateState
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiTable import TablePanel
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisMainPlotPanel import MainPlotPanel
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisFitPlotPanel import FitPlotPanel

#####################################################################
#######################  The main GUI Module ########################
#####################################################################

class ExperimentAnalysisGuiModuleBC(CcpnModule):
    """
    Top class for the Experiment analysis module.
    This module is controlled by several handlers.
    Currently, they are:
        - backendHandler              -->  Link to the No-UI module containing data, calculation and fitting models
        - settingsPanelHandler      -->  Link to the settings widgets, getter and setters
        - panelHandler                   -->  Link to the main panels and widgets
        - ioHandler                         -->  Link to Input-Output from-to external programs. (Not yet implemented, NYI)
        - pluginsHandler                -->  Link to the Plugins  (Not yet implemented, NYI)

    The settingsPanelHandler contains tabs.
        The easiest way to get the selected values from the widgets is to get all as a dictionary.
        Use  settingsPanelHandler.getAllSettings() or see the class for more info.

    The panelHandler contains GUI panels.
        Each represents a frame and contains particular widget(s) such as the mainTable or mainPlot widget.
        See the handler for more information or add/create panels in a plugin.

    """

    includeSettingsWidget = True
    maxSettingsState = 2
    settingsPosition = 'left'
    className = 'ExperimentAnalysis'
    analysisType = None
    _includeInLastSeen = False
    settingsChanged = pyqtSignal(dict)
    mainTableSortingChanged = pyqtSignal()
    mainTableChanged = pyqtSignal()

    def __init__(self, mainWindow, name='Experiment Analysis', backendHandler=None, **kwds):
        super(ExperimentAnalysisGuiModuleBC, self)
        CcpnModule.__init__(self, mainWindow=mainWindow, name=name)

        self.project = getProject()
        self.application = getApplication()
        self.current = getCurrent()

        ## link to the Non-Gui backend
        self.backendHandler = backendHandler or SeriesAnalysisABC()

        ## link to Gui Setting-Panels. Needs to be before the GuiPanels
        self.settingsPanelHandler = SettingsPanelHandler(self)
        self.addSettingsPanels()

        ## link to Gui Panels
        self.panelHandler = PanelHandler(self)
        self.addPanels()

        ## link to Core Notifiers (Project/Current)
        self.coreNotifiersHandler = CoreNotifiersHandler(guiModule=self)

        ## link to Input/output. (NYI)
        self.ioHandler = IOHandler(guiModule=self)

        ## link to user plugins - external programs. (NYI)
        self.pluginsHandler = PluginsHandler(guiModule=self)

        ## fire any post init callback from panels
        self._postInitPanels()

    ##########################################################
    #####################      Data       ###########################
    ##########################################################

    ### Get the input/output dataTables via the backendHandler.
    @property
    def inputDataTables(self) -> list:
        return self.backendHandler.inputDataTables

    def getVisibleDataFrame(self, includeHiddenColumns=False):
        """ Get the dataframe displayed on the mainTable. """
        table = self._getMainTableWidget()
        tableModel = table.model()
        if tableModel is not None:
            dataFrame = tableModel._getVisibleDataFrame(includeHiddenColumns=includeHiddenColumns)
            dataFrame[sv.INDEX] = np.arange(1, len(dataFrame) + 1)
            return dataFrame
        return pd.DataFrame()

    def getSettings(self, grouped=True) -> dict:
        """
        Get all settings set in the Settings panel
        :param grouped: Bool. True to get a dict of dict, key: tabName; value: dict of settings per tab.
                              False to get a flat dict with all settings in it.
        :return:  dict of dict as default, dict if grouped = False.
        """
        return self.settingsPanelHandler.getAllSettings(grouped)

    #################################################################
    #####################      Widgets    ###########################
    #################################################################

    def addPanels(self):
        """ Add the Gui Panels to the panelHandler.
        Each Panel is a stand-alone frame with information where about to be added on the general GUI.
        Override in Subclasses"""
        self._addCommonPanels()

    def addSettingsPanels(self):
        """
        Add the Settings Panels to the Gui. To retrieve a Panel use/see the settingsPanelsManager.
        Override in Subclasses
        """
        self._addCommonSettingsPanels()

    def _addCommonPanels(self):
        """ Add the Common Gui Panels to the panelHandler."""
        self.panelHandler.addToolBar(ToolBarPanel(self))
        self.panelHandler.addPanel(TablePanel(self))
        self.panelHandler.addPanel(FitPlotPanel(self))
        self.panelHandler.addPanel(MainPlotPanel(self))

    def _addCommonSettingsPanels(self):
        """
        Add the Common Settings Panels to the settingsPanelsManager.
        """
        self.settingsPanelHandler.append(settingsPanel.GuiInputDataPanel(self))
        self.settingsPanelHandler.append(settingsPanel.AppearancePanel(self))

    #####################################################################
    #####################  Widgets callbacks  ###########################
    #####################################################################

    def updateAll(self, refit=False, rebuildInputData=False):
        """ Update all Gui panels"""
        getLogger().info(f'{self}. Updating data and GUI items...')
        currentCollections = self.current.collections #grab the current collection to reset later the same selections
        self. _updateBackendHandler(refit=refit, rebuildInputData=rebuildInputData)
        self._updatePanels()
        self.current.collections = currentCollections ## make sure all is selected as before the update
        self._setUpdateDone()

    def _updateBackendHandler(self, refit=False, rebuildInputData=False):
        """
        _internal called ONLY from _updateAll
        :return:
        """
        if rebuildInputData or self.backendHandler._needsRebuildingInputDataTables:
            self.backendHandler._rebuildInputData()
            self.backendHandler._needsRebuildingInputDataTables = False
        if refit or self.backendHandler._needsRefitting and len(self.backendHandler.inputDataTables) > 0:
            getLogger().info(f'{self}. Nothing to refit. Skipping...')
            self.backendHandler.fitInputData()
            self.backendHandler._needsRefitting = False

    def _postInitPanels(self):
        for _, panel in self.settingsPanelHandler._panels.items():
            panel.postInitWidgets()

        for _, panel in self.panelHandler.panels.items():
            panel.postInitWidgets()

    def _updatePanels(self):
        """
        _internal called ONLY from _updateAll
        :return:
        """
        allSettings = self.settingsPanelHandler.getAllSettings()
        for panelName, panel in self.panelHandler.panels.items():
            panel.updatePanel(**{guiNameSpaces.SETTINGS: allSettings})

    def setNeedRefitting(self):
        self.backendHandler._needsRefitting = True
        self._setUpdateDetected()

    def setNeedRebuildingInputDataTables(self):
        self.backendHandler._needsRebuildingInputDataTables = True
        self._setUpdateDetected()

    def _setUpdateDetected(self):
        toolbar = self.panelHandler.getToolBarPanel()
        if toolbar:
            toolbar.setUpdateState(PanelUpdateState.DETECTED)

    def _setUpdateDone(self):
        """ Set the update completed icon on toolbar"""
        toolbar = self.panelHandler.getToolBarPanel()
        if toolbar:
            toolbar.setUpdateState(PanelUpdateState.DONE)

    def _getMainTableWidget(self):
        tablePanel = self.panelHandler.getPanel(guiNameSpaces.TablePanel)
        if tablePanel is not None:
            table = tablePanel.mainTable
            return table

    def _getSortingHeaderFromMainTable(self):
        _sortColumn = ''
        _sortOrder = 0
        table = self._getMainTableWidget()
        if not table:
            return _sortColumn, _sortOrder

        model = table.model()
        _sortColumn = model._sortColumn
        if _sortColumn:
            _sortColumn =  table.headerColumnMenu.columnTexts[_sortColumn]
            _sortOrder = model._sortOrder
        return _sortColumn, _sortOrder

    def restoreWidgetsState(self, **widgetsState):
        # with self.blockWidgetSignals():
        super().restoreWidgetsState(**widgetsState)
        ## restore and apply filters correctly
        self._setUpdateDone()

    def _closeModule(self):
        ## de-register/close all notifiers. Handler
        self.backendHandler.close()
        self.coreNotifiersHandler.close()
        self.panelHandler.close()
        self.pluginsHandler.close()
        self.settingsPanelHandler.close()
        super()._closeModule()

def _navigateToPeak(guiModule, peak):
    from ccpn.ui.gui.lib.StripLib import navigateToPositionInStrip, _getCurrentZoomRatio
    if peak is None:
        return
    # get the display from settings
    appearanceTab = guiModule.settingsPanelHandler.getTab(guiNameSpaces.Label_GeneralAppearance)
    displayWidget = appearanceTab.getWidget(guiNameSpaces.WidgetVarName_SpectrumDisplSelection)
    if displayWidget is None:
        getLogger().debug(f'Not found widget in Appearance tab {guiNameSpaces.WidgetVarName_SpectrumDisplSelection}')
        return
    displays = displayWidget.getDisplays()
    for display in displays:
        for strip in display.strips:
            widths = _getCurrentZoomRatio(strip.viewRange())
            navigateToPositionInStrip(strip=strip, positions=peak.position, widths=widths)

def getPeaksFromCollection(collection):
    from ccpn.core.Peak import Peak
    if collection is None:
        return []
    peaks = set()
    for item in collection.items:
        if isinstance(item, Peak):
            peaks.add(item)
    return list(peaks)
