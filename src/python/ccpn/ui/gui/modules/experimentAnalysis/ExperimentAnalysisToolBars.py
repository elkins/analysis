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
__dateModified__ = "$dateModified: 2024-11-11 16:35:33 +0000 (Mon, November 11, 2024) $"
__version__ = "$Revision: 3.2.10 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-05-20 12:59:02 +0100 (Fri, May 20, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================
from collections import OrderedDict as od
from PyQt5 import QtCore, QtWidgets
from ccpn.ui.gui.widgets.Action import Action
from ccpn.ui.gui.widgets.ToolBar import ToolBar
from ccpn.util.Logging import getLogger
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiPanel import GuiPanel
import ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiNamespaces as guiNameSpaces
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.util.DataEnum import DataEnum


class PanelUpdateState(DataEnum):
    """
    updateState = 0 # status: done, no need to update. icon Green
    updateState = 1 # status: to be done, on the queue and need to update. icon Orange
    updateState = 2 # status: suspended, Might be updates. icon red
    """

    DONE        = 0, 'icons/update_done'
    DETECTED    = 1, 'icons/update_detected'
    SUSPENDED   = 2, 'icons/update_suspended'

class ToolBarPanel(GuiPanel):
    """
    A GuiPanel containing the ToolBar Widgets for the Experimental Analysis Module
    """

    position = 0
    panelName = guiNameSpaces.ToolbarPanel
    toolButtons = {}

    updateRequested = QtCore.pyqtSignal(object)

    updateState = 0

    def __init__(self, guiModule, *args, **Framekwargs):
        GuiPanel.__init__(self, guiModule, *args , **Framekwargs)
        self.setMaximumHeight(100)
        self._updateState = PanelUpdateState.DONE

    def initWidgets(self):

        toolButtonsDefs = {
            guiNameSpaces.FilterButton: {
                'text': '',
                'icon': 'icons/filter',
                'tipText': 'Apply filters as defined in settings',
                'toggle': False,
                'callback': f'_{guiNameSpaces.FilterButton}{guiNameSpaces.Callback}',  # the exact name as the function def
                'objectName': guiNameSpaces.FilterButton,
                'enabled': False,
                'visible':False,
            },

            guiNameSpaces.UpdateButton: {
                'text': '',
                'icon': 'icons/update',
                'tipText': 'Update all data and GUI',
                'toggle': None,
                'callback': f'_{guiNameSpaces.UpdateButton}{guiNameSpaces.Callback}',
                'objectName': guiNameSpaces.UpdateButton,
            },
            guiNameSpaces.ShowStructureButton: {
                'text': '',
                'icon': 'icons/showStructure',
                'tipText': 'Show on Molecular Viewer',
                'toggle': None,
                'callback': f'_{guiNameSpaces.ShowStructureButton}{guiNameSpaces.Callback}',
                'objectName':guiNameSpaces.ShowStructureButton,
                'enabled': True,
            }}

        colPos = 0
        for i, buttonName in enumerate(toolButtonsDefs, start=1):
            colPos+=i
            callbackAtt = toolButtonsDefs.get(buttonName).pop('callback')
            isVisible =  toolButtonsDefs.get(buttonName).pop('visible', True)
            button = Button(self, **toolButtonsDefs.get(buttonName), grid=(0, colPos))
            callback = getattr(self, callbackAtt or '', None)
            button.setCallback(callback)
            button.setMaximumHeight(25)
            button.setMaximumWidth(25)
            button.setVisible(isVisible)
            setattr(self, buttonName, button)
            self.toolButtons.update({buttonName:button})

        self.getLayout().setAlignment(QtCore.Qt.AlignLeft)

    def getButton(self, name):
        return self.toolButtons.get(name)

    def _filterButtonCallback(self):
        getLogger().warn('Not implemented. Clicked _filterButtonCallback')

    def _updateButtonCallback(self):
        """ Update all panels."""
        self.guiModule.updateAll()

    def _showStructureButtonCallback(self):
        from ccpn.ui.gui.modules.PyMolUtil import _CSMSelection2PyMolFileNew
        import subprocess
        import os
        from ccpn.util.Path import aPath, fetchDir
        from ccpn.ui.gui.widgets.MessageDialog import showOkCancelWarning, showWarning
        scriptsPath = self.application.scriptsPath
        pymolScriptsPath = fetchDir(scriptsPath, guiNameSpaces.PYMOL)
        settingsDict = self.guiModule.settingsPanelHandler.getAllSettings().get(guiNameSpaces.Label_GeneralAppearance,  {})
        mainPlotPanel = self.guiModule.panelHandler.getPanel(guiNameSpaces.MainPlotPanel)
        moleculeFilePath = settingsDict.get(guiNameSpaces.WidgetVarName_MolStructureFile, '')
        moleculeFilePath = aPath(moleculeFilePath)
        pymolScriptsPath = aPath(pymolScriptsPath)
        scriptFilePath = pymolScriptsPath.joinpath(guiNameSpaces.PymolScriptName)

        pymolPath = self.application.preferences.externalPrograms.pymol
        moleculeFilePath.assureSuffix('.pdb')
        if not os.path.exists(moleculeFilePath):
            ok = showWarning('Molecular file not Set',
                             f'Provide a {guiNameSpaces.Label_MolStructureFile} on the Settings - Appearance Panel')

        if not os.path.exists(pymolPath):
            ok = showOkCancelWarning('Molecular Viewer not Set', 'Select the executable file on preferences')
            if ok:
                from ccpn.ui.gui.popups.PreferencesPopup import PreferencesPopup
                pp = PreferencesPopup(parent=self.mainWindow, mainWindow=self.mainWindow)
                pp.tabWidget.setCurrentIndex(pp.tabWidget.count() - 1)
                pp.exec_()
                return

        import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
        # get the match  index-residueCode so that can be mapped to the PDB and pymol
        df = self.guiModule.getVisibleDataFrame(includeHiddenColumns=True)
        if df is None or df.empty:
            showWarning('No Data available', f'To start calculations, set the input Data from the Settings Panel')
            return
        dataFrame = mainPlotPanel._setColoursByThreshold(df)
        seqCodes = dataFrame[sv.NMRRESIDUECODE].values
        colours = dataFrame[guiNameSpaces.BRUSHLABEL].values
        coloursDict =  dict(zip(seqCodes, colours))
        selection = "+".join([str(x.sequenceCode) for x in self.current.nmrResidues])  # FIXME this is broken
        scriptPath = _CSMSelection2PyMolFileNew(scriptFilePath, moleculeFilePath, coloursDict, selection)
        try:
            self.pymolProcess = subprocess.Popen(str(pymolPath) + ' -r ' + str(scriptPath),
                                                 shell=True,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
        except Exception as e:
            getLogger().warning('Pymol not started. Check executable.', e)

    def getUpdateState(self):
        return self._updateState

    def setUpdateState(self, value):

        dataEnum = None
        if isinstance(value, DataEnum):
            dataEnum = value
        else:
            for i in PanelUpdateState:
                if i.value == value:
                    dataEnum = value

        if dataEnum:
            self._updateState = dataEnum.value
            updateButton = self.getButton(guiNameSpaces.UpdateButton)
            if updateButton:
                iconValue = dataEnum.description
                updateButton.setIcon(Icon(iconValue))

class ExperimentAnalysisPlotToolBar(ToolBar):
    toolButtons = {}

    def __init__(self, parent, plotItem, guiModule, **kwds):
        super().__init__(parent=parent, **kwds)
        self.plotItem = plotItem
        self.plotItem.toolbar = self
        self.guiModule = guiModule
        self.setToolActions(self.getToolBarDefs())
        self.setMaximumHeight(30)


    def setToolActions(self, actionDefinitions):
        for name, dd in actionDefinitions.items():
            if isinstance(dd, od):
                action = Action(self, **dd)
                action.setObjectName(name)
                self.addAction(action)
                self.toolButtons.update({name: action})
            else:
                self.addSeparator()

    def getToolBarDefs(self):
        toolBarDefs = od((
            ('Zoom-All', od((
                ('text', 'Zoom-All'),
                ('toolTip', 'Zoom All Axes'),
                ('icon', Icon('icons/zoom-full')),
                ('callback', self.plotItem.zoomFull),
                ('enabled', True)
                ))),
            ('Zoom-X', od((
                ('text', 'Zoom-X-axis'),
                ('toolTip', 'Reset X-axis to fit view'),
                ('icon', Icon('icons/zoom-full-1d')),
                ('callback', self.plotItem.fitXZoom),
                ('enabled', True)
            ))),
            ('Zoom-Y', od((
                ('text', 'Zoom-Y-axis'),
                ('toolTip', 'Reset Y-axis to fit view'),
                ('icon', Icon('icons/zoom-best-fit-1d')),
                ('callback', self.plotItem.fitYZoom),
                ('enabled', True)
            ))),
            ('Sep', ()),
            ))
        return toolBarDefs

    def getButton(self, name):
        return self.toolButtons.get(name)

class MainPlotToolBar(ExperimentAnalysisPlotToolBar):

    def __init__(self, parent, plotItem, guiModule, **kwds):
        super().__init__(parent, plotItem=plotItem, guiModule=guiModule, **kwds)

        self.parentPanel = parent

    def getToolBarDefs(self):
        toolBarDefs = super().getToolBarDefs()
        extraDefs = (
            (guiNameSpaces.BARITEM, od((
                ('text', 'Toggle Bars'),
                ('toolTip', 'Toggle the Bars from the plot'),
                ('icon', Icon('icons/bars-icon')),
                ('callback', self._toggleBars),
                ('enabled', False),
                ('checkable', True),
                ('checked', False)
                ))),
            (guiNameSpaces.SCATTERITEM, od((
                ('text', 'Toggle Scatters'),
                ('toolTip', 'Toggle the Scatters from the plot'),
                ('icon', Icon('icons/Scatters')),
                ('callback', self._toggleScatters),
                ('enabled', False),
                ('checkable', True),
                ('checked', False)
                ))),
            (guiNameSpaces.ERRORBARITEM, od((
                ('text', 'Toggle ErrorBars'),
                ('toolTip', 'Toggle the Error Bars from the plot'),
                ('icon', Icon('icons/errorBars')),
                ('callback', self._toggleErrorBars),
                ('enabled', True),
                ('checkable', True),
                ('checked', True)
                ))),
            (guiNameSpaces.ROLLINGLINEITEM, od((
                ('text', 'Toggle Rolling Average Line'),
                ('toolTip',  'Toggle the Rolling Average Line from the plot'),
                ('icon', Icon('icons/rollingAverage-icon')),
                ('callback', self._toggleRollingAverage),
                ('enabled', False),
                ('checkable', True),
                ('checked',False),
                ))),
            )
        toolBarDefs.update(extraDefs)
        return toolBarDefs

    def _toggleErrorBars(self):
        self.parentPanel._toggleErrorBars(self.sender().isChecked())

    def _toggleBars(self):
        self.parentPanel._toggleBars(self.sender().isChecked())

    def _toggleScatters(self):
        self.parentPanel._toggleScatters(self.sender().isChecked())

    def _toggleRollingAverage(self):
        self.parentPanel._toggleRollingAverage(self.sender().isChecked())

    def _isErrorBarChecked(self):
        return self._isToolButtonChecked(guiNameSpaces.ERRORBARITEM)

    def _isRollingAverageChecked(self):
        return self._isToolButtonChecked(guiNameSpaces.ROLLINGLINEITEM)

    def _isScatterOptionChecked(self):
        return self._isToolButtonChecked(guiNameSpaces.SCATTERITEM)

    def _isBarOptionChecked(self):
        return self._isToolButtonChecked(guiNameSpaces.BARITEM)

    def _isToolButtonChecked(self, name):
        button = self.getButton(name)
        if button:
            return button.isChecked()
        return False
