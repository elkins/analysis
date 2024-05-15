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

import datetime
import pandas as pd
from ccpn.util.decorators import singleton
from ccpn.util.Path import aPath, fetchDir, joinPath
from .Logger import MFLogger
from .Logger import getLogger

@singleton
class OutputContainer():
    """A singleton class used to register output Paths and other output related object.
    """
    outputHandler = None

    def register(self, outputHandler):
        self.outputHandler = outputHandler


def getOutputHandler():
    container = OutputContainer()
    if container.outputHandler is not None:
        return container.outputHandler
    else:
        raise RuntimeError('The OutputsHandler was never instantiated.')


class OutputsHandler(object):

    _sep = '_'
    TABLES = 'tables'
    PLOTS = 'plots'

    def __init__(self, parent):
        """
        :param parent: The main parent object (ModelFree Object).
        """
        self._parent = parent
        self._settingsHandler = self._parent.settingsHandler
        self._inputsHandler = self._parent.inputsHandler
        self.outputDirPath = aPath(self._inputsHandler.getOutputDirPath()) # this is the top directory where the individual runs will be saved. It is provided by the User's input and must be validated.
        self.runDirPath = None # the subdir of the outputDirPath, usually with the added timestamp.

        # get some general preference from the input handler
        self._runName = self._inputsHandler.runName
        self._useTimeStamp = self._inputsHandler.useTimeStamp
        self._timeStampFormat = self._inputsHandler.timeStampFormat
        self._runTime = datetime.datetime.now().strftime(self._timeStampFormat)

        # register the Singleton
        _container = OutputContainer().register(self)

        # start the logger
        self.runDirPath = self._fetchRunDirPath()
        self._loggerName = 'log.txt'
        self._loggerWrapper = MFLogger(self._loggerPath)
        self._writeSettingsToLog()

    def _fetchRunDirPath(self):
        """
        Get the full output dir path, if exists or create a new one, relative to the top output dir path.
        :return: the newly created Working outputPath.
        """
        if self.runDirPath is not None:
            return self.runDirPath
        name = self._runName
        if self._useTimeStamp:
            name = f'{name}{self._sep}{self._runTime}'
        newDir = aPath(fetchDir(self.outputDirPath, name))
        self.runDirPath = newDir
        return self.runDirPath

    def _fetchTablesDirPath(self, diffusionModelName):
        """Fetch the path where to save tables """
        wodp = self._fetchRunDirPath()
        dmdp = fetchDir(wodp, diffusionModelName)
        return fetchDir(dmdp, self.TABLES)

    def _fetchPlotsDirPath(self, diffusionModelName):
        """Fetch the path where to save Plots """
        wodp = self._fetchRunDirPath()
        dmdp = fetchDir(wodp, diffusionModelName)
        return fetchDir(dmdp, self.PLOTS)

    @property
    def _loggerPath(self):
        """The logger path"""
        return joinPath(self.runDirPath, self._loggerName)

    def _getHandlerRepr(self, handler):
        """
        :param handler: A traitLet obj for Settings or Inputs Handler
        :return: str. A table representation of the handler for the logger
        """
        df = pd.DataFrame.from_dict(handler.asDict(), orient='index', columns=[self])
        table = df.to_string(index=True, header=False)
        strTable = '\n'.join([' ' * 3 + row for row in table.split('\n')])  #This will add a space character before each row in the logger output, providing some separation from the left margin of the log file.
        return strTable

    def _writeSettingsToLog(self):
        """Write the initial lines of the log, include input, output and calculation settings."""

        msg = '''User's Inputs:\n'''
        msg += self._getHandlerRepr(self._inputsHandler)
        msg += '\n'
        getLogger().info(msg)

        msg = '''User's Settings:\n'''
        msg += self._getHandlerRepr(self._settingsHandler)
        msg += '\n'
        getLogger().info(msg)


