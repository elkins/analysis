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
__dateModified__ = "$dateModified: 2024-05-20 09:41:35 +0100 (Mon, May 20, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"

import pandas as pd

#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.Path import aPath
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.DataLoaders.CsvDataLoader import CsvDataLoader
from ccpn.framework.lib.DataLoaders.NefDataLoader import NefDataLoader
from ccpn.framework.lib.DataLoaders.ExcelDataLoader import ExcelDataLoader
from ccpn.framework.lib.DataLoaders.PdbDataLoader import PdbDataLoader
from ccpn.framework.lib.DataLoaders.TextDataLoader import TextDataLoader


class Rates_CSV_DataLoader(CsvDataLoader):
    """The csv file data-loader.
    """
    loadFunction = (None, None)

    def load(self):
        try:
            data = pd.read_csv(self.path)
            return data
        except (ValueError, RuntimeError, RuntimeWarning) as es:
            raise RuntimeError(f'Error loading "{self.path}": {es}') from es


class Rates_NEF_DataLoader(ExcelDataLoader):
    """The NEF file data-loader for ModelFree plugin.
    """
    loadFunction = (None, None)

    def load(self):
        raise RuntimeError('Not Implemented')

class Rates_Excel_DataLoader(ExcelDataLoader):
    """The excel file data-loader.
    """
    loadFunction = (None, None)

    def load(self):
        """ Load the Excel file and concat all tables in one single dataFrame. """
        try:
            excelPath = aPath(self.path)
            pandasFile = pd.ExcelFile(excelPath)
            sheets = self._parseSheetNames(pandasFile)
            dataframes = []
            for sheetName, sf in sheets.items():
                dataFrame = pandasFile.parse(sheetName)
                dataFrame[sv.SF] = [sf]*len(dataFrame)
                dataframes.append(dataFrame)
            data = pd.concat(dataframes)
            data = data.reset_index(drop=True)
            return data
        except (ValueError, RuntimeError, RuntimeWarning) as es:
            raise RuntimeError(f'Error loading "{self.path}": {es}') from es

    def _parseSheetNames(self, pandasfile):
        """Get the field value from the sheet name. It has to be represented as a float. Sheet name should be called 600,800,900 etc not 600Mhz """
        sheetNames = pandasfile.sheet_names
        sheets = {}
        for sheetName in sheetNames:
            try:
                sf = float(sheetName)
                sheets[sheetName] = sf
            except Exception as err:
                #todo we need a logger
                print(f'Error parsing sheet {sheetName}. {err}. Ensure the sheet name is the field in MHz. E.g.: 600.12')
        return sheets

