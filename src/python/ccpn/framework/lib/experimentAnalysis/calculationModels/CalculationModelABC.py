"""
This module defines base classes for Series Analysis Calculation Models

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
__dateModified__ = "$dateModified: 2023-11-10 16:40:18 +0000 (Fri, November 10, 2023) $"
__version__ = "$Revision: 3.2.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-02-02 14:08:56 +0000 (Wed, February 02, 2022) $"

from abc import abstractmethod
from ccpn.core.DataTable import TableFrame
from ccpn.framework.lib.experimentAnalysis.fittingModels.FittingModelABC import FittingModelABC


#=========================================================================================
# Start of code
#=========================================================================================

class CalculationModel(FittingModelABC):
    """
    Calculation model for Series Analysis
    """

    modelName   = 'Calculation'     ## The Model name.
    modelInfo        = 'the info'        ## A brief description of the fitting model.
    description = 'Description'     ## A simplified representation of the used equation(s).
    maTex       = r''               ## MaTex representation of the used equation(s). see https://matplotlib.org/3.5.0/tutorials/text/mathtext.html
    references  = 'References'      ## A list of journal article references that help to identify the employed calculation equations. E.g.: DOIs or title/authors/year/journal; web-pages.
    _disableFittingModels = False  # If True, a fitting models are not applied to the resulting calculation mode. E.g. for R2/R1 Model
    requiredInputData = 1
    _minimisedProperty = None


    @abstractmethod
    def calculateValues(self, inputDataTables) -> TableFrame:
        """
        Calculate the required values for an input SeriesTable.
        This method must be overridden in subclass'.
        Return one row for each collection pid. Index by collection pid
        :param inputDataTables: list of DataTables
        :return: outputFrame
        """
        raise RuntimeError('This method must be overridden in subclass')

    def fitSeries(self, inputData:TableFrame, *args, **kwargs) -> TableFrame:
        raise RuntimeError('This method cannot be used in this class. Use calculateValues instead ')
