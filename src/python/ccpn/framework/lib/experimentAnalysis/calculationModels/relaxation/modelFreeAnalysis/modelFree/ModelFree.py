"""
This module contains the main class for the ModelFree Plugin
It is the backend and defines the various handlers to settings and fittings
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-04-23 12:58:39 +0100 (Tue, April 23, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================




from abc import ABC
from ccpn.framework.Application import getApplication, getCurrent, getProject
from src.io.Settings import SettingsHandler
from src.io.Inputs import InputsHandler
from src.io.Outputs import OutputsHandler
from src.diffusionModels.DiffusionModelABC import DiffusionModelHandler


class ModelFree(object):

    def __init__(self, inputJsonPath,  outPutDirPath=None, settingsJsonPath=None, *args, **kwrgs):

        self.settingsHandler = SettingsHandler(self, settingsPath=settingsJsonPath)
        self.inputsHandler = InputsHandler(self, inputsPath=inputJsonPath)
        self.outputsHandler = OutputsHandler(self, outputDirPath=self.inputsHandler.outputDir_path)
        self.diffusionModelHandler = DiffusionModelHandler(settingsHandler=self.settingsHandler, inputsHandler=self.inputsHandler, outputsHandler=self.outputsHandler)

    def runFittings(self):
        # run the first iteration of fitting.
        # for each diffusion model
        # for each spectral density function
        result = self.diffusionModelHandler.startMinimisation()
        print('ratesData ===> ',result)

        pass


