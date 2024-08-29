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

"""
This module contains the Experiment Selector base and subclasses and the handler.
"""

from ccpn.util.traits.TraitBase import TraitBase
from collections import OrderedDict as od
from ccpn.util.Logging import getLogger
import numpy as np
from ccpn.util.traits.CcpNmrTraits import Unicode, Int, Float, Bool

######## gui/ui imports ########
from PyQt5 import QtCore, QtWidgets, QtGui
from ccpn.ui.gui.widgets.MessageDialog import showInfo, showWarning
import ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiNamespaces as guiNameSpaces
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv


class _ExperimentSelectorBC(TraitBase):
    """ An Experiment  Selector base class used  to pre-populate widgets depending on a selected  name"""

    name = Unicode(allow_none=True,  default_value=None, read_only=True).tag(info='The name of the Experiment Selector')
    analysisType = Unicode(allow_none=True, default_value=None, read_only=True).tag(info='The analysisType (defined in the module) where this can be used. E.g.: Relaxation or ChemicalShiftMapping')
    spectrumGroup = Unicode(allow_none=True,  default_value=None, read_only=False).tag(info='The spectrum Group Name to pre-populate the relevant widget')
    inputCollection = Unicode(allow_none=True,  default_value=None, read_only=False).tag(info='The inputCollection Name to pre-populate the relevant widget')
    inputDataTable = Unicode(allow_none=True,  default_value=None, read_only=False).tag(info='The inputDataTable Name to pre-populate the relevant widget')
    resultDataTable = Unicode(allow_none=True,  default_value=None, read_only=False).tag(info='The  resultDataTable Name to pre-populate the relevant widget')
    calculationOption = Unicode(allow_none=True,  default_value=None, read_only=True).tag(info='The calculationOption Name to pre-populate the relevant widget')
    fittingOption = Unicode(allow_none=True,  default_value=None, read_only=True).tag(info='The fittingOption Name to pre-populate the relevant widget')

    def __init__(self,  *args, **kwargs):
        super().__init__()
        self._setDefaultNames()

    def _setDefaultNames(self):
        name = self.name
        for k, v in self.items():
            trait = self.getTrait(k)
            if not trait.read_only:
                self.setTraitValue(k, f'{name}_{k}')

    def _makeTipText(self):
        """Create a tiptext to display on the GUI """
        ll = [
            'Pre-populate widgets with the following parameters:',
            f' \r\n - SpectrumGroup: {self.spectrumGroup} (if available);',
            f' \r\n - InputCollection: {self.inputCollection};',
            f' \r\n - InputDataTable: {self.inputDataTable};',
            f' \r\n - InputDataTable: {self.inputDataTable};',
            f' \r\n - Calculation Model: {self.calculationOption};',
            f' \r\n - Fitting Model: {self.fittingOption};',
            f'\nNote: this selection will override existing settings and disable some options.\nFor enabling all available options select: {sv.USERDEFINEDEXPERIMENT}.'
            ]
        return ''.join(ll)

class ExperimentSelectorHandler():
    """ An Experiment  manager to pre-populate widgets depending on a selected Experiment name"""

    ExperimentSelectors = {}

    def __init__(self, guiModule, *args, **kwargs):

        self.guiModule = guiModule
        self.project = self.guiModule.project
        self._experimentSelector = None

    def _getSetupTab(self):
        return self.guiModule.settingsPanelHandler.getTab(guiNameSpaces.Label_SetupTab)

    def _getCalculationTab (self):
        return self.guiModule.settingsPanelHandler.getTab(guiNameSpaces.Label_Calculation)

    def _getFittingTab(self):
        return self.guiModule.settingsPanelHandler.getTab(guiNameSpaces.Label_Fitting)

    @staticmethod
    def registerExperimentSelector(obj):
        ExperimentSelectorHandler.ExperimentSelectors.update({obj.name:obj})

    @property
    def experimentSelector(self):
        return self._experimentSelector

    @experimentSelector.setter
    def experimentSelector(self, name):
        # get The ExperimentSelector Obj
        _experimentSelectorObj = self.ExperimentSelectors.get(name, None)
        self._experimentSelector = _experimentSelectorObj
        getLogger().info('Populating Widgets...')
        self._populateAll()

    def _setSpectrumGroupWidgets(self):
        """
        :return:
        """
        from ccpn.core.lib.Pid import createPid
        from ccpn.core.SpectrumGroup import SpectrumGroup
        spectrumGroupName = self._getSpectrumGroupName()
        _setupTab = self._getSetupTab()
        widget = _setupTab.getWidget(guiNameSpaces.WidgetVarName_SpectrumGroupsSelection)
        # widget is a compound listWidget  of type SpectrumGroupSelectionWidget
        if widget is None:
            return

        # try to select the spectrumGroup if the name is found
        if len(self.project.spectrumGroups) > 0:
            pid = createPid(SpectrumGroup.shortClassName, spectrumGroupName)
            widget.clearList()
            widget.select(pid)

    def _getSpectrumGroupName(self):
        """Get the spectrumGroup selection by the communality between the selector name and group name.
         This is not optimal. Better  to define a spectrum group with an identifiable tag, e,.g. T1 T2 etc
         """
        experimentSelector = self.experimentSelector
        if not experimentSelector:
            return

        spectrumGroupName = experimentSelector.spectrumGroup

        if len(self.project.spectrumGroups)==0:
            return spectrumGroupName

        # try a regex based on the selector name
        experimentSelectorName = experimentSelector.name
        for sg in self.project.spectrumGroups:
            if sg.name.startswith(experimentSelectorName):
                return sg.name

    def _getInputCollectionName(self):
        """Get the Input Collection selection by the communality between the selector name and Collection name.
         """
        experimentSelector = self.experimentSelector
        if not experimentSelector:
            return
        inputCollectionName = experimentSelector.inputCollection
        if len(self.project.collections)==0:
            return inputCollectionName
        # try a regex based on the selector name
        experimentSelectorName = experimentSelector.name
        for co in self.project.collections:
            if co.name.startswith(experimentSelectorName):
                return co.name

    def _setInputCollectionWidgets(self):
        """
        :return:
        """
        from ccpn.core.lib.Pid import createPid
        from ccpn.core.Collection import Collection
        inputCollectionName = self._getInputCollectionName()
        _setupTab = self._getSetupTab()
        widget = _setupTab.getWidget(guiNameSpaces.WidgetVarName_InputCollectionSelection)
        # widget is a  listWidget
        if widget is None:
            return

        # try to select the spectrumGroup if the name is found
        if len(self.project.collections) > 0:
            pid = createPid(Collection.shortClassName, inputCollectionName)
            widget.select(pid)

    def _setInputDataTableWidgets(self):
        _setupTab = self._getSetupTab()
        widget = _setupTab.getWidget(guiNameSpaces.WidgetVarName_DataTableName)
        if widget is not None and self.experimentSelector is not None:
            widget.setText(self.experimentSelector.inputDataTable)

    def _setResultDataTableWidgets(self):
        _setupTab = self._getSetupTab()
        widget = _setupTab.getWidget(guiNameSpaces.WidgetVarName_OutPutDataTableName)
        if widget is not None and self.experimentSelector is not None:
            widget.setText(self.experimentSelector.resultDataTable)

    def _setCalculationWidgets(self):
        _calculationTab = self._getCalculationTab()
        widget = _calculationTab.getWidget(guiNameSpaces.WidgetVarName_CalcMode)
        if widget is not None and self.experimentSelector is not None:
            widget.setByText(self.experimentSelector.calculationOption, silent=False)

    def _setFittingWidgets(self):
        _fittingTab = self._getFittingTab()
        widget = _fittingTab.getWidget(guiNameSpaces.WidgetVarName_FittingModel)
        if widget is not None and self.experimentSelector is not None:
            widget.setByText(self.experimentSelector.fittingOption, silent=False)

    def _populateAll(self):
        if self.experimentSelector is not None:
            self._setSpectrumGroupWidgets()
            self._setInputCollectionWidgets()
            self._setInputDataTableWidgets()
            self._setResultDataTableWidgets()
            self._setCalculationWidgets()
            self._setFittingWidgets()

class _ExperimentSelectorUserDefined(_ExperimentSelectorBC):
    """ An Experiment  Selector  for the UserDefined experiment"""
    name =  Unicode(allow_none=True, default_value=sv.USERDEFINEDEXPERIMENT,  read_only=True)
    analysisType = Unicode(allow_none=True, default_value=None, read_only=True)
    calculationOption = Unicode(allow_none=True,  default_value=sv.BLANKMODELNAME, read_only=True)
    fittingOption = Unicode(allow_none=True,  default_value=sv.BLANKMODELNAME, read_only=True)


#### ChemicalShiftMapping specific Selectors

class _ExperimentSelectorTitration(_ExperimentSelectorBC):
    """ An Experiment  Selector  for CSM titrations"""
    name =  Unicode(allow_none=True, default_value=sv.TITRATION,  read_only=True)
    analysisType = Unicode(allow_none=True, default_value=sv.ChemicalShiftMappingAnalysis, read_only=True)
    calculationOption = Unicode(allow_none=True,  default_value=sv.EUCLIDEAN_DISTANCE, read_only=True)
    fittingOption = Unicode(allow_none=True,  default_value=sv.FRACTION_BINDING_WITH_FIXED_TARGET_MODEL, read_only=True)

#### Relaxation specific Selectors

class _ExperimentSelectorT1(_ExperimentSelectorBC):
    """ An Experiment  Selector  for the T1 experiment"""
    name =  Unicode(allow_none=True, default_value=sv.T1,  read_only=True)
    analysisType = Unicode(allow_none=True, default_value=sv.RelaxationAnalysis, read_only=True)
    calculationOption = Unicode(allow_none=True,  default_value=sv.BLANKMODELNAME, read_only=True)
    fittingOption = Unicode(allow_none=True,  default_value=sv.OnePhaseDecay, read_only=True)

class _ExperimentSelectorT2(_ExperimentSelectorBC):
    """ An Experiment  Selector  for the T2 experiment"""
    name =  Unicode(allow_none=True, default_value=sv.T2,  read_only=True)
    analysisType = Unicode(allow_none=True, default_value=sv.RelaxationAnalysis, read_only=True)
    calculationOption = Unicode(allow_none=True,  default_value=sv.BLANKMODELNAME, read_only=True)
    fittingOption = Unicode(allow_none=True,  default_value=sv.OnePhaseDecay, read_only=True)

class _ExperimentSelectorHetNOE(_ExperimentSelectorBC):
    """ An Experiment  Selector  for the HetNOE experiment"""
    name =  Unicode(allow_none=True, default_value=sv.HETNOE,  read_only=True)
    analysisType = Unicode(allow_none=True, default_value=sv.RelaxationAnalysis, read_only=True)
    calculationOption = Unicode(allow_none=True,  default_value=sv.HETNOE, read_only=True)
    fittingOption = Unicode(allow_none=True,  default_value=sv.BLANKMODELNAME, read_only=True)

## Register an ExperimentSelector for enabling it on the gui
def _registerExperimentSelectors():
    ExperimentSelectorHandler.registerExperimentSelector(_ExperimentSelectorUserDefined())
    ExperimentSelectorHandler.registerExperimentSelector(_ExperimentSelectorTitration())
    ExperimentSelectorHandler.registerExperimentSelector(_ExperimentSelectorT1())
    ExperimentSelectorHandler.registerExperimentSelector(_ExperimentSelectorT2())
    ExperimentSelectorHandler.registerExperimentSelector(_ExperimentSelectorHetNOE())
