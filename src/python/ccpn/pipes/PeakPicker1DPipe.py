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
__dateModified__ = "$dateModified: 2024-12-02 17:02:45 +0000 (Mon, December 02, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-05-20 10:28:42 +0000 (Sun, May 28, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================


#### GUI IMPORTS
from ccpn.ui.gui.widgets.PipelineWidgets import GuiPipe

#### NON GUI IMPORTS
from ccpn.framework.lib.pipeline.PipeBase import SpectraPipe, PIPE_ANALYSIS
from ccpn.util.Logging import getLogger
from tqdm import tqdm


########################################################################################################################
###   Attributes:
###   Used in setting the dictionary keys on _kwargs either in GuiPipe and Pipe
########################################################################################################################

PipeName = 'Peak Picker 1D'
ExcludeRegions = 'Exclude_Regions'
NoiseThreshold = 'Noise_Threshold'
DefaultNoiseThreshold = [0.0, 0.0]
DefaultExcludeRegions = [[0.0, 0.0], [0.0, 0.0]]
DefaultPeakListIndex = -1


########################################################################################################################
##########################################      ALGORITHM       ########################################################
########################################################################################################################

# see in ccpn.core.PeakList.py function peakFinder1D
# This algorithm uses noise threshold and excluded regions in ppm. Set these using other pipes

########################################################################################################################
##########################################     GUI PIPE    #############################################################
########################################################################################################################


class PeakDetector1DGuiPipe(GuiPipe):
    preferredPipe = True
    pipeName = PipeName

    def __init__(self, name=pipeName, parent=None, project=None, **kwds):
        super(PeakDetector1DGuiPipe, self)
        GuiPipe.__init__(self, parent=parent, name=name, project=project, **kwds)
        self._parent = parent





########################################################################################################################
##########################################       PIPE      #############################################################
########################################################################################################################


class PeakPicker1DPipe(SpectraPipe):
    guiPipe = PeakDetector1DGuiPipe
    pipeName = PipeName
    pipeCategory = PIPE_ANALYSIS

    _kwargs = {
               ExcludeRegions  : DefaultExcludeRegions,
              }

    def runPipe(self, spectra, **kwargs):
        """
        :param data:
        :return:
        """
        if ExcludeRegions in self.pipeline._kwargs:
            excludeRegions = self.pipeline._kwargs[ExcludeRegions]
        else:
            self._kwargs.update({ExcludeRegions: DefaultExcludeRegions})
            excludeRegions = self._kwargs[ExcludeRegions]
        from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking
        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                for spectrum in tqdm(self.inputData):
                    if len(spectrum.peakLists) > 0:
                        pl = spectrum.peakLists[DefaultPeakListIndex]
                        ppmRegions = dict(zip(spectrum.axisCodes, spectrum.spectrumLimits))
                        peakPicker = spectrum._getPeakPicker()
                        peakPicker._excludePpmRegions[spectrum.axisCodes[0]] = excludeRegions
                        spectrum.pickPeaks(peakList=pl,
                                           positiveThreshold=spectrum.positiveContourBase,
                                           negativeThreshold=spectrum.negativeContourBase,
                                           **ppmRegions)
                    else:
                        getLogger().warning('Error: PeakList not found for Spectrum: %s. Add a new PeakList first' % spectrum.pid)
        return spectra


PeakPicker1DPipe.register()  # Registers the pipe in the pipeline
