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
__dateModified__ = "$dateModified: 2024-05-09 15:50:51 +0100 (Thu, May 09, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2024-04-04 12:39:28 +0100 (Thu, April 04, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.decorators import singleton
from ccpn.util.Path import aPath, fetchDir

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
        :param parent: The main parent object.
        """
        self._parent = parent
        self._settingsHandler = self._parent.settingsHandler
        self._inputsHandler = self._parent.inputsHandler
        self.outputDirPath = aPath(self._inputsHandler.getOutputDirPath())
        self._workingOutputDirPath = None # the subdir of the outputDirPath, usually with the added timestamp.

        # get some general preference from the input handler
        self._runName = self._inputsHandler.runName
        self._useTimeStamp = self._inputsHandler.useTimeStamp
        self._timeStampFormat = self._inputsHandler.timeStampFormat

        # register the Singleton
        _container = OutputContainer().register(self)

    def _fetchWorkingOutputDirPath(self):
        """
        Get the full output dir path, if exists or create a new one, relative to the top output dir path.
        :return: the newly created Working outputPath.
        """
        name = self._runName
        newDir = aPath(fetchDir(self.outputDirPath, name))
        if self._useTimeStamp:
            newDir = newDir.addTimeStamp(timeFormat=self._timeStampFormat, sep=self._sep)
        self._workingOutputDirPath = newDir
        return self._workingOutputDirPath

    def _fetchTablesDirPath(self, diffusionModelName):
        wodp = self._fetchWorkingOutputDirPath()
        dmdp = fetchDir(wodp, diffusionModelName)
        return fetchDir(dmdp, self.TABLES)

    def _fetchPlotsDirPath(self, diffusionModelName):
        wodp = self._fetchWorkingOutputDirPath()
        dmdp = fetchDir(wodp, diffusionModelName)
        return fetchDir(dmdp, self.PLOTS)
