"""
I/O module
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
__dateModified__ = "$dateModified: 2024-06-28 10:33:01 +0100 (Fri, June 28, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
from ccpn.util.traits.CcpNmrJson import Constants, update, CcpNmrJson
from ccpn.util.traits.CcpNmrTraits import Unicode, Dict, List, Bool, Int, Float
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv



class SettingsHandler(CcpNmrJson):
    """
    Input handler for the ModelFree plugin
    """

    # _internal
    _JSON_FILE = None
    classVersion = 3.1
    saveAllTraitsToJson = True
    _availableDiffusionModels = [sv.ISOTROPIC, sv.AXIALLY_SYMMETRIC, sv.ANISOTROPIC]

    # calculation settings
    errorCalculationMethod = Unicode(allow_none=False, default_value='MonteCarlo').tag(info='The name of the error Calculation Method. Allowed: MonteCarlo, BootStrapping')
    errorCalculationIterations = Int(allow_none=False, default_value=20).tag(info='The number of iterations to compute for the error Calculation Method')
    spectralDensityFuncModels = List(allow_none=False, default_value=[1,2,3,4]).tag(info='The Spectral density function models to be evaluated. See docs.')
    minimisationAccuracy = Unicode(allow_none=False, default_value='high').tag(info='The level of minimisation accuracy to reach the convergence. Allowed: low, medium, high')
    modelSelectionMethod = Unicode(allow_none=False, default_value='bic').tag(info='The name of the (Spectral Density Functions) model selection method. Allowed: aic, aicc, bic, bicc')
    useExtendedSpectralDensityFuncModels = Bool(allow_none=False, default_value=False).tag(info='Include the Extended Spectral density function models. See docs.')
    diffusionModel = Unicode(allow_none=False, default_value='Axially-Symmetric').tag(info='''The name of the diffusion Model to be evaluated.  Allowed: auto, Isotropic, Axially-Symmetric, Fully-Anisotropic''')
    minimisationAlgorithm = Unicode(allow_none=False, default_value='differential_evolution').tag(info='The name of the minimisation Algorithm. Allowed: Differential_evolution, grid_search')
    computingRates = List(allow_none=False, default_value=[sv.R1, sv.R2, sv.HETNOE]).tag(info='The default rates to use in the calculations.')
    computingRateErrors = List(allow_none=False, default_value=[sv.R1_ERR, sv.R2_ERR, sv.HETNOE_ERR]).tag(info='The default rates to use in the calculations.')

    def __init__(self, settingsPath):
        super().__init__()
        self._JSON_FILE = settingsPath
        self.loadFromFile(self._JSON_FILE )

    def loadFromFile(self, filePath):
        if filePath is None:
            return
        self.restore(filePath)

    def saveToFile(self, filePath=None):
        """
        :param filePath: A valid path
        :return: the filepath where the json has been saved
        """
        self.save(filePath)
        return filePath

SettingsHandler.register()

