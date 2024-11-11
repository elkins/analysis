# =========================================================================================
# Licence, Reference and Credits
# =========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2022"
__credits__ = ("Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, http://doi.org/10.1007/s10858-016-0060-y")
# =========================================================================================
# Last code modification
# =========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2022-08-09 15:59:57 +0100 (Tue, August 09, 2022) $"
__version__ = "$Revision: 3.1.0 $"
# =========================================================================================
# Created
# =========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-05-20 12:59:02 +0100 (Fri, May 20, 2022) $"
# =========================================================================================
# Start of code
# =========================================================================================

"""
This module contains the GUI Settings panels for the CSM module.
"""

from collections import OrderedDict as od
from ccpn.util.Logging import getLogger
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv

from ccpn.util.isotopes import name2IsotopeCode
######## gui/ui imports ########
import ccpn.ui.gui.widgets.CompoundWidgets as compoundWidget
import ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiNamespaces as guiNameSpaces
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as seriesVariables
from ccpn.ui.gui.guiSettings import COLOUR_SCHEMES, getColours, DIVIDER
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiSettingsPanel import GuiSettingPanel, \
    GuiInputDataPanel, GuiCalculationPanel, GuiFittingPanel, AppearancePanel


SettingsWidgeMinimumWidths = (180, 180, 180)
SettingsWidgetFixedWidths = (200, 350, 350)
DividerColour = getColours()[DIVIDER]


#####################################################################
#####################   InputData Panel   ###########################
#####################################################################

class CSMGuiInputDataPanel(GuiInputDataPanel):

    def __init__(self, guiModule, *args, **Framekwargs):
        GuiInputDataPanel.__init__(self, guiModule, *args, **Framekwargs)

#####################################################################
#####################  Calculation Panel  ###########################
#####################################################################

class CSMCalculationPanel(GuiCalculationPanel):
    """ Add CSM-widget-specific to the general calculation panel """

    tabTipText = guiNameSpaces.TipText_CSMCalculationPanelPanel

    def setWidgetDefinitions(self):
        """CSM specific"""
        self.widgetDefinitions = super().setWidgetDefinitions()

        ## add the weighting Factor widgets. Autogenerate labels/tiptext from DEFAULT_ALPHA_FACTORS defs.
        factorsWidgetDefinitions = od(())
        for atomName, factorValue in seriesVariables.DEFAULT_ALPHA_FACTORS.items():
            label = guiNameSpaces.Label_Factor.format(**{guiNameSpaces.AtomName: atomName})
            att = guiNameSpaces.WidgetVarName_Factor.format(**{guiNameSpaces.AtomName: atomName})
            tipText = guiNameSpaces.TipText_Factor.format(
                **{guiNameSpaces.AtomName: atomName, guiNameSpaces.FactorValue: factorValue})
            factorsWidgetDefinitions[att] = {'label': label,
                                'tipText': guiNameSpaces.TipText_Factor,
                                'type': compoundWidget.DoubleSpinBoxCompoundWidget,
                                'callBack': self._setCalculationOptionsToBackend,
                                'kwds': {'labelText': label,
                                         'tipText': tipText,
                                         'value': factorValue,
                                         'minimum': 0.001, 'maximum': 1,
                                         'step': 0.01, 'decimals': 4,
                                         'fixedWidths': SettingsWidgetFixedWidths}}
        # untraceableWidgetDefinitions = od((
        #                     (guiNameSpaces.WidgetVarName_UntraceablePeak,
        #                      {'label': guiNameSpaces.Label_UntraceablePeak,
        #                       'tipText': guiNameSpaces.TipText_UntraceablePeak,
        #                       'enabled': False,
        #                       'type': compoundWidget.DoubleSpinBoxCompoundWidget,
        #                       'callBack': self._setCalculationOptionsToBackend,
        #                       '_init': None,
        #                       'kwds': {'labelText': guiNameSpaces.Label_UntraceablePeak,
        #                                'tipText': guiNameSpaces.TipText_UntraceablePeak,
        #                                'value': 1,
        #                                'fixedWidths': SettingsWidgetFixedWidths}}),
        #                     ))
        ## add the new items to the main dict
        self.widgetDefinitions.update(factorsWidgetDefinitions)
        # self.widgetDefinitions.update(untraceableWidgetDefinitions)
        return self.widgetDefinitions

    def _calculationModePostInit(self, widget):
        pass

    def _getAlphaFactors(self):
        factors = {}
        for atomName, factorValue in seriesVariables.DEFAULT_ALPHA_FACTORS.items():
            att = guiNameSpaces.WidgetVarName_Factor.format(**{guiNameSpaces.AtomName: atomName})
            widget = self.getWidget(att)
            if widget is not None:
                if atomName == seriesVariables._OTHER:
                    factors.update({seriesVariables._OTHER: widget.getValue()})
                else:
                    factors.update({name2IsotopeCode(atomName): widget.getValue()})
        return factors

    def getSettingsAsDict(self):
        """Add the Factors in a dict, instead of single entries for each atom """
        extraSettings = {guiNameSpaces.ALPHA_FACTORS: self._getAlphaFactors()}
        settings = super(CSMCalculationPanel, self).getSettingsAsDict()
        settings.update(extraSettings)
        return settings

    def _setCalculationOptionsToBackend(self):
        """ Update the backend """
        getLogger().info('_setCalculationOptionsToBackend...')
        calculationSettings = self.getSettingsAsDict()
        _filteringAtoms = calculationSettings.get(guiNameSpaces.WidgetVarName_IncludeAtoms, [])
        _alphaFactors = calculationSettings.get(guiNameSpaces.ALPHA_FACTORS, {})
        _excludedTypes = calculationSettings.get(guiNameSpaces.WidgetVarName_ExcludeResType, [])
        _untraceablePeakValue = calculationSettings.get(guiNameSpaces.WidgetVarName_UntraceablePeak, 1)
        ## update the backend
        backend = self.guiModule.backendHandler
        backend.setAlphaFactor(_1H=_alphaFactors.get(seriesVariables._1H),
                               _15N=_alphaFactors.get(seriesVariables._15N),
                               _13C=_alphaFactors.get(seriesVariables._13C),
                               _Other=_alphaFactors.get(seriesVariables._OTHER))
        backend._excludedResidueTypes = _excludedTypes
        backend._filteringAtoms = _filteringAtoms
        backend._untraceableValue = _untraceablePeakValue
        # set update detected.
        backend._needsRefitting = True
        self._setUpdatedDetectedState()

##############################################################
#####################    Fitting Panel    ###########################
##############################################################

class CSMGuiFittingPanel(GuiFittingPanel):
    tabName = guiNameSpaces.Label_Fitting
    tabTipText = 'Set the various Fitting modes and options'

#################################################################
#####################   Appearance Panel  ###########################
#################################################################

class CSMAppearancePanel(AppearancePanel):

    pass

##############################################################
#####################   Filtering Panel   ###########################
##############################################################

## Not yet Implemeted