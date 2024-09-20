"""
Module Documentation here
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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-04-04 15:19:24 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2017-07-04 09:28:16 +0000 (Tue, July 04, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.SettingsWidgets import StripPlot, STRIPPLOT_PEAKS, STRIPPLOT_NMRRESIDUES, \
    STRIPPLOT_NMRCHAINS, NO_STRIP, STRIPPLOT_NMRATOMSFROMPEAKS
from ccpn.ui.gui.widgets.MessageDialog import progressManager, showWarning
from ccpn.util.Common import makeIterableList


STRIPPLOTMINIMUMWIDTH = 100


class StripPlotPopup(CcpnDialogMainWidget):
    def __init__(self, parent=None, mainWindow=None, spectrumDisplay=None, title='StripPlot',
                 includePeakLists=False,
                 includeNmrChains=False,
                 includeNmrChainPullSelection=False,
                 includeSpectrumTable=False, **kwds):
        """
        Initialise the widget
        """
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = None
            self.project = None
            self.current = None

        self.spectrumDisplay = spectrumDisplay
        # self.spectrumDisplayLabel = Label(self.mainWidget, f"Current spectrumDisplay: {spectrumDisplay.id}", grid=(0, 0))

        # import the new strip plot widget - also used in backbone assignment and pick and assign module
        self._newStripPlotWidget = StripPlot(parent=self.mainWidget, mainWindow=self.mainWindow,
                                             includePeakLists=includePeakLists,
                                             includeNmrChains=includeNmrChains,
                                             includeNmrChainPullSelection=includeNmrChainPullSelection,
                                             includeSpectrumTable=includeSpectrumTable,
                                             defaultSpectrum=NO_STRIP,
                                             grid=(1, 0), gridSpan=(1, 3))

        self.setOkButton(callback=self._accept, tipText='Create strip plot and close')
        self.setCloseButton(callback=self.reject, tipText='Close')

    def _accept(self, dummy=None):
        """OK button pressed
        """
        listType = self._newStripPlotWidget.listButtons.getIndex()
        spectrumDisplays = self._newStripPlotWidget.displaysWidget.getDisplays()

        msg = None
        if listType is not None and spectrumDisplays:
            buttonType = self._newStripPlotWidget.listButtons.buttonTypes[listType]

            if buttonType == STRIPPLOT_PEAKS:
                msg = self._popupStripPeaks(spectrumDisplays)

            elif buttonType == STRIPPLOT_NMRATOMSFROMPEAKS:
                msg = self._popupStripPeakNmrResidues(spectrumDisplays)

            elif buttonType == STRIPPLOT_NMRRESIDUES:
                msg = self._popupNmrResidues(spectrumDisplays)

            elif buttonType == STRIPPLOT_NMRCHAINS:
                msg = self._popupNmrChain(spectrumDisplays)

            if not msg:
                self.accept()
                return

        msg = msg or 'No selected spectrumDisplay'
        showWarning('Make Strip Plot', msg)

    def _popupNmrChain(self, spectrumDisplays):
        """Make strip from nmrResidues of selected nmrChain
        """
        if self._newStripPlotWidget.nmrChain:
            if (nmrRes := self._newStripPlotWidget.nmrChain.nmrResidues):
                with progressManager(self, 'Making Strip Plot...'):
                    self._buildStrips(nmrResidues=nmrRes, spectrumDisplays=spectrumDisplays)
            else:
                return 'NmrChain is empty'
        else:
            return 'No selected nmrChain'

    def _popupNmrResidues(self, spectrumDisplays):
        """Make strip from selected nmrResidues
        """
        if (nmrRes := self.current.nmrResidues):
            with progressManager(self, 'Making Strip Plot...'):
                self._buildStrips(nmrResidues=nmrRes, spectrumDisplays=spectrumDisplays)
        else:
            return 'No selected nmrResidues'

    def _popupStripPeakNmrResidues(self, spectrumDisplays):
        """Make strip from assigned nmrResidues of selected peaks
        """
        if (pks := self.current.peaks):
            with progressManager(self, 'Making Strip Plot...'):
                self._buildStripsFromPeaks(peaks=pks, spectrumDisplays=spectrumDisplays)
        else:
            return 'No selected peaks'

    def _popupStripPeaks(self, spectrumDisplays):
        """Make strip from selected peaks
        """
        if (pks := self.current.peaks):
            with progressManager(self, 'Making Strip Plot...'):
                self._buildStrips(peaks=pks, spectrumDisplays=spectrumDisplays)
        else:
            return 'No selected peaks'

    def storeWidgetState(self):
        """Store the state of the widgets between popups
        """
        self._newStripPlotWidget.storeWidgetState()

    def restoreWidgetState(self):
        """Restore the state of the widgets
        """
        self._newStripPlotWidget.restoreWidgetState()

    def _buildStripsFromPeaks(self, peaks=None, spectrumDisplays=None):
        """Build the strips in the selected spectrumDisplays for the nmrAtoms attached to the current peaks
        """
        if not (spectrumDisplays and peaks):
            return

        nmrResidues = set()
        for peak in peaks:
            atoms = makeIterableList(peak.assignedNmrAtoms)
            for atom in atoms:
                nmrResidues.add(atom.nmrResidue)

        if nmrResidues:
            self._buildStrips(nmrResidues=list(nmrResidues), spectrumDisplays=spectrumDisplays)

    def _buildStrips(self, spectrumDisplays=None, peaks=None, nmrResidues=None):
        """Build the strips in the selected spectrumDisplays
        """
        if not (spectrumDisplays and (peaks or nmrResidues)):
            return

        autoClearMarks = self._newStripPlotWidget.autoClearMarksWidget.isChecked()
        sequentialStrips = self._newStripPlotWidget.sequentialStripsWidget.isChecked()
        markPositions = self._newStripPlotWidget.markPositionsWidget.isChecked()

        # loop through the spectrumDisplays
        for specDisplay in spectrumDisplays:

            # with specDisplay.stripFrame.blockWidgetSignals():  # was blocking the hide/show events
            if peaks:
                specDisplay.makeStripPlot(peaks=peaks, nmrResidues=None,
                                          autoClearMarks=autoClearMarks,
                                          sequentialStrips=sequentialStrips,
                                          markPositions=markPositions
                                          )
            elif nmrResidues:
                specDisplay.makeStripPlot(peaks=None, nmrResidues=nmrResidues,
                                          autoClearMarks=autoClearMarks,
                                          sequentialStrips=sequentialStrips,
                                          markPositions=markPositions
                                          )

            specDisplay.setColumnStretches(stretchValue=True, widths=True, minimumWidth=STRIPPLOTMINIMUMWIDTH)

    def _cleanupDialog(self):
        """Cleanup the notifiers that are left behind after the widget is closed
        """
        self._newStripPlotWidget._cleanupWidget()
