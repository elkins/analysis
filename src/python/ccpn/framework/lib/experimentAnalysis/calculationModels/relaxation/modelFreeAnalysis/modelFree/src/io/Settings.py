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
__dateModified__ = "$dateModified: 2024-04-15 15:38:25 +0100 (Mon, April 15, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.Path import aPath
from ccpn.util.traits.CcpNmrJson import Constants, update, CcpNmrJson
from ccpn.util.traits.CcpNmrTraits import Unicode, Dict, List, Bool, Int
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv



class SettingsHandler(CcpNmrJson):
    """
    Input handler for the ModelFree plugin
    """

    # _internal
    _JSON_FILE = None
    classVersion = 3.1
    saveAllTraitsToJson = True

    # calculation settings
    errorCalculationMethod = Unicode(allow_none=False, default_value='MonteCarlo').tag(info='The name of the error Calculation Method. Allowed: MonteCarlo, BootStrapping')
    errorCalculationIterations = Int(allow_none=False, default_value=20).tag(info='The number of iterations to compute for the error Calculation Method')
    initialFittingIterations = Int(allow_none=False, default_value=2).tag(info='The number of  initial fitting iterations to compute for determine the Spectral density function model.')
    spectralDensityFuncModels = List(allow_none=False, default_value=[1,2,3,4]).tag(info='The Spectral density function models to be evaluated. See docs.')
    useExtendedSpectralDensityFuncModels = Bool(allow_none=False, default_value=False).tag(info='Include the Extended Spectral density function models. See docs.')
    diffusionModel = Unicode(allow_none=False, default_value='auto').tag(info='''The name of the diffusion Model to be evaluated. 
                                                                                                                                Allowed: auto, Isotropic, Axially-Symmetric, Fully-Anisotropic, Partially-Anisotropic.''')
    minimisationAlgorithm = Unicode(allow_none=False, default_value='differential_evolution').tag(info='The name of the minimisation Algorithm. Allowed: Differential_evolution, grid_search')

    # rates column definitions for tabular input data.
    _useRates = List(allow_none=False, default_value=[sv.R1, sv.R2, sv.HETNOE]).tag(info='The default rates to use in the calculations.')
    _R1ColumnName = Unicode(allow_none=True, default_value=sv.R1).tag(info='The column name where the R1 data is described')
    _R2ColumnName = Unicode(allow_none=True, default_value=sv.R2).tag(info='The column name where the R2 data is described')
    _HETNOEColumnName = Unicode(allow_none=True, default_value=sv.HETNOE).tag(info='The column name where the HetNoe data is described')
    _ETAXYColumnName = Unicode(allow_none=True, default_value=sv.ETAXY).tag(info='The column name where the ETAyx data is described')
    _ETAZColumnName = Unicode(allow_none=True, default_value=sv.ETAZ).tag(info='The column name where the ETAz data is described')

    _R1errColumnName = Unicode(allow_none=False, default_value=sv.R1_ERR).tag(info='The column name where the R1 error data is described')
    _R2errColumnName = Unicode(allow_none=True, default_value=sv.R2_ERR).tag(info='The column name where the R2 data error is described')
    _HETNOEerrColumnName = Unicode(allow_none=True, default_value=sv.HETNOE_ERR).tag(info='The column name where the HetNoe error data is described')
    _ETAXYerrColumnName = Unicode(allow_none=True, default_value=sv.ETAXY).tag(info='The column name where the ETAyx error data is described')
    _ETAZerrColumnName = Unicode(allow_none=True, default_value=sv.ETAZ).tag(info='The column name where the ETAz error data is described')

    def __init__(self, parent, settingsPath):
        super().__init__()
        self.parent = parent
        self._JSON_FILE = settingsPath
        self.loadFromFile(self._JSON_FILE )

        self.print()

    def loadFromFile(self, filePath):
        if filePath is None:
            return
        self.restore(filePath)

SettingsHandler.register()

