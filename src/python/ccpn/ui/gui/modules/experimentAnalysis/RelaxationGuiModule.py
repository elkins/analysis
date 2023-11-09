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
__dateModified__ = "$dateModified: 2023-11-09 09:49:32 +0000 (Thu, November 09, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-05-20 12:59:02 +0100 (Fri, May 20, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

######## core imports ########
from ccpn.framework.lib.experimentAnalysis.backends.RelaxationAnalysis import RelaxationAnalysisBC
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
######## gui/ui imports ########
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiModuleBC import ExperimentAnalysisGuiModuleBC
import ccpn.ui.gui.modules.experimentAnalysis.RelaxationSettingsPanel as settingsPanel

#####################################################################
#######################  The main GUI Module ########################
#####################################################################

class RelaxationGuiModule(ExperimentAnalysisGuiModuleBC):

    className = 'Relaxation'
    analysisType = sv.RelaxationAnalysis

    def __init__(self, mainWindow, name='Relaxation Analysis (Beta)', **kwds):
        super(ExperimentAnalysisGuiModuleBC, self)

        ## link to the Non-Gui backend and its Settings
        backendHandler = RelaxationAnalysisBC()
        ExperimentAnalysisGuiModuleBC.__init__(self, mainWindow=mainWindow, name=name, backendHandler=backendHandler)

    #################################################################
    #####################      Widgets    ###########################
    #################################################################

    def addPanels(self):
        """ Add the Gui Panels to the panelHandler."""
        super().addPanels()

    def addSettingsPanels(self):
        """
        Add the Settings Panels to the Gui. To retrieve a Panel use/see the settingsPanelsManager.
        """
        self.settingsPanelHandler.append(settingsPanel.RelaxationGuiInputDataPanel(self))
        self.settingsPanelHandler.append(settingsPanel.RelaxationCalculationPanel(self))
        self.settingsPanelHandler.append(settingsPanel.RelaxationFittingPanel(self))
        self.settingsPanelHandler.append(settingsPanel.RelaxationAppearancePanel(self))

