"""

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
__dateModified__ = "$dateModified: 2024-12-03 00:25:21 +0000 (Tue, December 03, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: TJ Ragan $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from abc import ABC
from abc import abstractmethod
from typing import List
import numpy as np
import pandas as pd
from ccpn.framework.Application import ANALYSIS_SCREEN, ANALYSIS_ASSIGN, ANALYSIS_METABOLOMICS, ANALYSIS_STRUCTURE

PIPE_ANALYSIS = 'Analysis'
PIPE_ASSIGN = ANALYSIS_ASSIGN
PIPE_SCREEN = ANALYSIS_SCREEN
PIPE_METABOLOMICS = ANALYSIS_METABOLOMICS
PIPE_STRUCTURE = ANALYSIS_STRUCTURE

PIPE_PROCESSING = 'Processing'
PIPE_POSTPROCESSING = 'Post-Processing'
PIPE_GENERIC = 'Generic'
PIPE_OUTPUTS = 'Outputs'
PIPE_USER = 'User'

PIPE_CATEGORY = 'pipeCategory'
PIPE_CATEGORIES = [PIPE_ANALYSIS,
                   PIPE_ASSIGN,
                   PIPE_SCREEN,
                   PIPE_METABOLOMICS,
                   PIPE_STRUCTURE,
                   PIPE_PROCESSING,
                   PIPE_POSTPROCESSING,
                   PIPE_GENERIC,
                   PIPE_OUTPUTS,
                   PIPE_USER]


class Pipe(object):
    """
    Pipeline step base class.

    """

    guiPipe = None  #Only the class. it will be init later on the GuiPipeline
    autoGuiParams = None
    pipeName = ''
    isActive = False
    pipeCategory = PIPE_GENERIC

    @classmethod
    def register(cls):
        """
        method to register the pipe in the loaded pipes to appear in the pipeline
        """
        from ccpn.pipes import loadedPipes
        loadedPipes.append(cls)

    def __init__(self, application=None):
        self._kwargs = {}
        self.inputData = None
        self.spectrumGroups = None
        self.pipeline = None
        self.project = None
        if self.pipeline is not None:
            self.inputData = self.pipeline.inputData
            self.spectrumGroups = self.pipeline.spectrumGroups

        if application is not None:
            self.application = application
            self.current = self.application.current
            self.preferences = self.application.preferences
            self.ui = self.application.ui
            self.project = self.application.project
            try:
                self.mainWindow = self.ui.mainWindow
            except AttributeError:
                pass

        self.customizeSetup()

    def _getSpectrumGroup(self, pid):
        if self.project is not None:
            return self.project.getByPid(pid)

    @abstractmethod
    def runPipe(self, data, **kwargs):
        return data

    def customizeSetup(self):
        """
        Override this method to customize the UI auto-generation attributes
        """
        pass

    def _updateRunArgs(self, arg, value):
        self._kwargs[arg] = value


class PandasPipe(Pipe):
    """
    A pipe where the run method accepts a pandas dataframe and returns a pandas dataframe
    """

    @abstractmethod
    def runPipe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        return dataframe


class SpectraPipe(Pipe):
    """
    A pipe where the run method accepts a list of spectra and returns a list of spectra
    """

    @abstractmethod
    def runPipe(self, spectra, **kwargs) -> List['Spectrum']:
        return spectra


class NumpyPipe(Pipe):
    """
    A pipe where the run method accepts a numpy Array and returns a numpy Array
    """

    @abstractmethod
    def runPipe(self, npArray: np.array) -> np.array:
        return npArray
