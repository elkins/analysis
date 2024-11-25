"""
This module defines base classes for Series Analysis
"""
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
__dateModified__ = "$dateModified: 2024-11-25 19:36:00 +0000 (Mon, November 25, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"

#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.Logging import getLogger
from ccpn.framework.lib.experimentAnalysis.backends.SeriesAnalysisABC import SeriesAnalysisABC
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.experimentAnalysis.calculationModels.binding.CSPerturbationCalculationModels import EuclideanCalculationModel

class ChemicalShiftPerturbationAnalysisBC(SeriesAnalysisABC):
    """
    Chemical Shift Perturbation Analysis Non-Gui module.
    # needed settings:
    """
    seriesAnalysisName = sv.ChemicalShiftPerturbationAnalysis
    _allowedPeakProperties = [sv._PPMPOSITION, sv._LINEWIDTH]


    def __init__(self):
        super().__init__()

        self._filteringAtoms = sv.DEFAULT_FILTERING_ATOMS
        self._alphaFactors = sv.DEFAULT_ALPHA_FACTORS
        self._excludedResidueTypes = sv.DEFAULT_EXCLUDED_RESIDUES
        self._untraceableValue = 1.0  # default value for replacing NaN values in the DeltaDeltas column


    def getAlphaFactor(self, isotopeCode):
        """Get the Alpha Factor for the DeltaDeltas calculation
        :param isotopeCode =  str, one of 1H, 15N, 13C or Other"""
        if isotopeCode not in self._alphaFactors:
            getLogger().warning(f'Cannot find alphaFactor for {isotopeCode}. Use one of "1H", "15N", "13C" or "Other"')
            return 1
        return self._alphaFactors.get(isotopeCode)

    def setAlphaFactor(self, _1H=None, _15N=None, _13C=None, _Other=None):
        """Set the Alpha Factor for the DeltaDeltas calculation by IsotopeCode.
             Factors are usually values between 0.1-1
        """
        if isinstance(_1H, (float, int)):
            self._alphaFactors.update({sv._1H: _1H})
        if isinstance(_15N, (float, int)):
            self._alphaFactors.update({sv._15N: _15N})
        if isinstance(_13C, (float, int)):
            self._alphaFactors.update({sv._13C: _13C})
        if isinstance(_Other, (float, int)):
            self._alphaFactors.update({sv._OTHER: _Other})

    def fitInputData(self, *args, **kwargs):
        """
        Perform calculation using the currentFittingModel and currentCalculationModel
        """
        if hasattr(self.currentCalculationModel, 'setAlphaFactors'):
            self.currentCalculationModel.setAlphaFactors(self._alphaFactors)

        if len(self.inputDataTables) == 0:
            raise RuntimeError('Cannot run any fitting models. Add a valid inputData first')

        calculationFrame = self.currentCalculationModel.calculateValues(self.inputDataTables)
        fittingFrame = self.currentFittingModel.fitSeries(calculationFrame)
        fittingFrame.joinNmrResidueCodeType()
        outputDataTable = self._fetchOutputDataTable(name=self._outputDataTableName)
        outputDataTable.data = fittingFrame
        self._setMinimisedPropertyFromModels()
        return outputDataTable
