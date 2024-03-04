"""Module Documentation here

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
__dateModified__ = "$dateModified: 2024-03-04 14:52:52 +0000 (Mon, March 04, 2024) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:42 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.Path import aPath, joinPath
import numpy as np

class Pipeline(object):
    '''
    Pipeline class.
    To run insert the pipes in the queue.

    '''
    className = 'Pipeline'

    def __init__(self, application, pipelineName=None, pipes=None):

        self.pipelineName = pipelineName
        self._kwargs = {}

        self.inputData = set()
        self.spectrumGroups = set()
        self.queue = []  # Pipes to be run
        self.updateInputData = False
        self.isRunning = False

        self._rawDataDict = None

        self.application = application
        if self.application:
            self.current = self.application.current
            self.preferences = self.application.preferences
            self.ui = self.application.ui
            self.project = self.application.project
            self.mainWindow = self.ui.mainWindow

        # ~~~ Instantiate all the Core Pipe Classes here ~~~
        if pipes is not None:
            self.pipes = [Pipe(application=application) for Pipe in pipes]
        else:
            self.pipes = []

    @property
    def pipes(self):
        return self._pipes

    @pipes.setter
    def pipes(self, pipes):
        '''
        '''

        if pipes is not None:
            allPipes = []
            for pipe in pipes:
                pipe.pipeline = self
                allPipes.append(pipe)
            self._pipes = allPipes
        else:
            self._pipes = []

    @property
    def filePath(self):
        return self._filePath

    @filePath.setter
    def filePath(self, filePath):
        self._filePath = filePath

    @filePath.getter
    def filePath(self):
        projectPipelinePath = aPath(self.application.pipelinePath)
        pipelineName = self.pipelineName
        savePath = joinPath(projectPipelinePath, pipelineName)
        self._filePath = str(savePath)
        return self._filePath

    @staticmethod
    def _updateTheNoiseSDBase(spectra, rawDataDict, force=True):
        for spectrum in spectra:
            if spectrum is None or spectrum.dimensionCount > 1:
                continue
            if spectrum not in rawDataDict:
                x, y = np.array(spectrum.positions), np.array(spectrum.intensities)
            else:
                x, y = rawDataDict.get(spectrum)
            if not spectrum._noiseSD or force:
                _noiseSD = float(np.median(y) + np.std(y))
                spectrum._noiseSD = _noiseSD
                if spectrum.noiseLevel is None:
                    spectrum.noiseLevel = _noiseSD * 2

    def _updateRunArgs(self, arg, value):
        self._kwargs[arg] = value

    def _set1DRawDataDict(self, force=True):
        from ccpn.core.lib.SpectrumLib import _1DRawDataDict
        if force or self._rawDataDict is None:
            self._rawDataDict = _1DRawDataDict(self.inputData)
        return self._rawDataDict

    def runPipeline(self):
        '''Run all pipes in the specified order '''
        from ccpn.core.lib.ContextManagers import undoBlock, notificationEchoBlocking, undoBlockWithoutSideBar

        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                self._kwargs = {}
                if len(self.queue) > 0:
                    self.isRunning = True

                    for i, pipe in enumerate(self.queue):
                        if pipe is not None:
                            self.updateInputData = False
                            pipe.inputData = self.inputData
                            pipe.spectrumGroups = self.spectrumGroups
                            result = pipe.runPipe(self.inputData, pipeIndex=i)
                            self.inputData = result or set()

        return self.inputData

    def stopPipeline(self):
        """ Set the stop Signal (to True)"""
        self.isRunning = False
