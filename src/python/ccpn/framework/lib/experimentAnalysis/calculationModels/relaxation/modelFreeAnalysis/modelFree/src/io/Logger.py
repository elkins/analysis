"""
logger module
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

import logging

class MFLogger:
    _instance = None
    _logFile = None

    def __new__(cls, logFile=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._logFile = logFile
            cls._instance._logger = cls._setupLogger(logFile)
        elif logFile is not None and cls._logFile != logFile:
            cls._instance._logger.warning("Ignoring logFile parameter since logger is already initialized with a different log file path.")
        return cls._instance

    @staticmethod
    def _setupLogger(logFile=None):
        logger = logging.getLogger('_MF_Logger')
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        if logFile:
            fileHandler = logging.FileHandler(logFile)
            fileHandler.setLevel(logging.DEBUG)
            fileHandler.setFormatter(formatter)
            logger.addHandler(fileHandler)
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(logging.INFO)
        consoleHandler.setFormatter(formatter)
        logger.addHandler(consoleHandler)

        return logger

    @property
    def logger(self):
        return self._logger

def getLogger():
    return MFLogger().logger

