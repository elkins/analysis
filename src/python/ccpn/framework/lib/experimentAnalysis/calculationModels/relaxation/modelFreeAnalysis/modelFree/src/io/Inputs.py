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
__dateModified__ = "$dateModified: 2024-05-15 19:54:04 +0100 (Wed, May 15, 2024) $"
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
import pandas as pd
from ccpn.util.traits.CcpNmrJson import Constants, update, CcpNmrJson
from ccpn.util.traits.CcpNmrTraits import Unicode, Int, Float, Bool, List, RecursiveDict, Dict, RecursiveList, CTuple, CString
import ccpn.framework.lib.experimentAnalysis.SeriesAnalysisVariables as sv
from ccpn.framework.lib.experimentAnalysis.calculationModels.relaxation.modelFreeAnalysis.modelFree.src.io._inputDataLoader import Rates_Excel_DataLoader


class _Rates(CcpNmrJson):
    """
    Input handler for the ModelFree plugin
    """

    rates_path = Unicode(allow_none=True, default_value='rates.xlsx').tag(info='The abs excel Path for the file containing the rates')


class InputsHandler(CcpNmrJson):
    """
    Input handler for the ModelFree plugin
    """

    # _internal
    _JSON_FILE = None
    classVersion = 3.1
    saveAllTraitsToJson = True

    # general settings
    runName = Unicode(allow_none=False, default_value='ccpn_mf').tag(info='The name of the calculation run')
    comment = Unicode(allow_none=False, default_value='A text comment').tag(info='A text comment')
    useTimeStamp = Bool(default_value=True).tag(info='flag to indicate if a timestamp should be used in generating the run directory')
    timeStampFormat = Unicode(allow_none=True, default_value="%d-%m-%y_%H-%M").tag(info='The timestamp format. Default day-month-year_hour:minute')
    # rates settings
    rates_path = Unicode(allow_none=True, default_value='inputs/rates.xlsx').tag(info='The relative file Path (from the input json file) for the file containing the rates')
    # molecules
    molecularStructure_path = Unicode(allow_none=True, default_value='inputs/molecule.pdb').tag(info='The relative file Path (from the input json file) for the file containing the molecular structure information.')
    outputDir_path = Unicode(allow_none=True, default_value='outputs').tag(info='The relative file Path (from the input json file) or abs Path for the directory where to save the results.')

    def __init__(self, parent, inputsPath):
        super().__init__()
        self.parent = parent
        self._settingsHandler = self.parent.settingsHandler
        self._ratesData = None
        self._JSON_FILE = inputsPath
        self.loadFromFile(self._JSON_FILE )
        self._loadRates()

    def loadFromFile(self, filePath):
        if filePath is None:
            return
        self.restore(filePath)

    @property
    def ratesData(self):
        return self._ratesData

    def getGroupedRatesDataByFrequency(self) -> dict:
        """Return a dict with the spectrometer Frequency as key and DataFrame as value. """
        if self.ratesData.empty:
            return {}
        if sv.SF not in self.ratesData:
            raise RuntimeError(f'Error in handling the Rates data. Ensure the column {sv.SF} is present and filled.')
        sorted_df = self.ratesData.sort_values(by=sv.SF)
        ratesBySF = {name: group for name, group in sorted_df.groupby(sv.SF)}
        return ratesBySF

    def _validatePath(self, path):
        """
        Check if is a relative or abs path and if exists
        :param path:
        :return: the absolute path
        """
        inputJsonPathParent = aPath(self._JSON_FILE).parent #the dir for the json path

        _path = aPath(path)
        if not _path.is_absolute():
            fullPath = inputJsonPathParent / _path
        else:
            fullPath = _path
        if not fullPath.exists():
            raise ValueError(f'The given path is not valid: {path}')
        return fullPath


    def _loadRates(self):
        """Load the rates from the defined files in the input file. Implemented Only Excel so far"""
        ratesPath = self._validatePath(self.rates_path)
        if ratesPath.suffix in Rates_Excel_DataLoader.suffixes:
            reader = Rates_Excel_DataLoader(ratesPath)
            data = reader.load()
            self._ratesData = data

    def _validateRates(self):
        """
        Check if the required rates Columns are in the data
        :return: df
        """
        _useRates = self._settingsHandler.computingRates
        # TODO

    def getOutputDirPath(self):
        return self._validatePath(self.outputDir_path)
