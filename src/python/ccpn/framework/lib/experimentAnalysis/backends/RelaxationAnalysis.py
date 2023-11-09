"""
This module defines base classes for Series Analysis
"""
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
__dateModified__ = "$dateModified: 2023-11-09 09:49:31 +0000 (Thu, November 09, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.experimentAnalysis.backends.SeriesAnalysisABC import SeriesAnalysisABC
from ccpn.framework.lib.experimentAnalysis.fittingModels.relaxation.RelaxationModels import FittingModels, CalculationModels
from ccpn.framework.lib.experimentAnalysis.fittingModels.others.BlankModels import BlankFittingModel, BlankCalculationModel

class RelaxationAnalysisBC(SeriesAnalysisABC):
    """
    Relaxation Analysis Non-Gui module.
    """
    seriesAnalysisName = sv.RelaxationAnalysis
    _allowedPeakProperties = [sv._HEIGHT, sv._VOLUME]
    _minimisedProperty = sv._HEIGHT

    def __init__(self):
        super().__init__()
        self.fittingModels = self._registerModels([BlankFittingModel] + FittingModels)
        self.calculationModels = self._registerModels([BlankCalculationModel] + CalculationModels)
        fittingModel = self.getFittingModelByName(sv.OnePhaseDecay) or self._getFirstModel(self.fittingModels)
        calculationModel = self._getFirstModel(self.calculationModels)
        if fittingModel:
            self._currentFittingModel = fittingModel()
        if calculationModel:
            self._currentCalculationModel = calculationModel()

    def fitInputData(self):
        """
        Perform calculation using the currentFittingModel and currentCalculationModel
        """
        return super().fitInputData()
