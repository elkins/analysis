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
__dateModified__ = "$dateModified: 2024-05-15 19:54:03 +0100 (Wed, May 15, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================


from ccpn.framework.lib.experimentAnalysis import ExperimentConstants as constants
from ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation import spectralDensityLib as sdl

class SDMConstants:
    """
    A container for the Spectral density mapping Constants and factors  needed during the minimisations.
    This object is represented as a Dict.
    Note, spectrometerFrequency is necessary as some factors are field-dependent.
    """

    def __init__(self, spectrometerFrequency=600.05):
        self._spectrometerFrequency = spectrometerFrequency
        self._calculate_factors()

    def _calculate_factors(self):
        self.omegaH = sdl.calculateOmegaH(self._spectrometerFrequency, scalingFactor=1e6)
        self.omegaN = sdl.calculateOmegaN(self._spectrometerFrequency, scalingFactor=1e6)
        self.omegaC = sdl.calculateOmegaC(self._spectrometerFrequency, scalingFactor=1e6)
        self.gammaHN = constants.GAMMA_H / constants.GAMMA_N
        self.dFactor = sdl.calculate_d_factor(constants.rNH)
        self.cFactor = sdl.calculate_c_factor(self.omegaN, constants.N15_CSA)

    def __iter__(self):
        for key, value in vars(self).items():
            if not key.startswith('_'):
                yield key, value

    def __getitem__(self, key):
        return getattr(self, key)

    def __repr__(self):
        return repr(dict(self))

    def __str__(self):
        return str(dict(self))
