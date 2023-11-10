"""
This module defines Blank Models for Series Analysis
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
__dateModified__ = "$dateModified: 2023-11-10 15:58:40 +0000 (Fri, November 10, 2023) $"
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
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC, MinimiserModel, MinimiserResult
from ccpn.framework.lib.experimentAnalysis.calculationModels.CalculationModelABC import CalculationModel


class BlankCalculationModel(CalculationModel):
    """
    Blank Calculation model for Series Analysis
    """

    ModelName = sv.BLANKMODELNAME
    TargetSeriesAnalyses = [sv.RelaxationAnalysis,
                                            sv.JCouplingAnalysis,
                                            sv.RDCAnalysis,
                                            sv.PREAnalysis,
                                            sv.PCSAnalysis
                                            ]
    Info = 'Blank Model'
    Description = 'A blank model containing no calculation. This will show only raw data.'
    _minimisedProperty = None

    def calculateValues(self, inputDataTables):
        """Return a frame with Collection Pids and value/error as Nones"""
        inputData = self._getFirstInputDataTable(inputDataTables)
        if inputData is None:
            return # should these better return an empty table
        if len(inputData) == 0 or sv.ISOTOPECODE not in inputData.columns:
            return inputData
        outputFrame = inputData[inputData[sv.ISOTOPECODE] == inputData[sv.ISOTOPECODE].iloc[0]]
        outputFrame.loc[outputFrame.index, self.modelArgumentNames] = None
        return outputFrame

    @property
    def modelArgumentNames(self):
        """ The list of parameters as str used in the calculation model.
          These names will appear as column headers in the output result frames. """
        return [sv.VALUE, sv.VALUE_ERR]

