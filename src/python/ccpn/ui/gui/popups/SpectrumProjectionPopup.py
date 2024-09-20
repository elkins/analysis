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
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.core.lib.SpectrumLib import PROJECTION_METHODS
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.DoubleSpinbox import ScientificDoubleSpinBox
from ccpn.ui.gui.widgets.MessageDialog import progressManager
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.popups.ExportDialog import ExportDialogABC
from ccpn.util.Path import aPath


class SpectrumProjectionPopup(CcpnDialogMainWidget):  # ExportDialogABC):
    FIXEDHEIGHT = True

    def __init__(self, parent=None, mainWindow=None, title='Spectrum Projection', **kwds):

        # for CcpnDialogMainWidget:
        super().__init__(parent=parent, setLayout=True, windowTitle=title,
                         **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.project = self.mainWindow.project
            self.application = self.mainWindow.application
        else:
            self.mainWindow = self.project = self.application = None

        self.validSpectra = None
        if self.project:
            # Only select 3D's for now
            self.validSpectra = [s for s in self.project.spectra if s.dimensionCount == 3]

            if len(self.validSpectra) == 0:
                from ccpn.ui.gui.widgets.MessageDialog import showWarning

                showWarning('No valid spectra', 'No 3D spectra in current dataset')
                self.reject()

        # for CcpnDialogMainWidget:
        self.initialise(self.mainWidget)
        self.populate(self.mainWidget)
        self.actionButtons()

    def actionButtons(self):
        self.setOkButton(callback=self.makeProjection, text='Make Projection', tipText='Export the projection to file and close dialog')
        self.setCloseButton(callback=self._rejectDialog, text='Close', tipText='Close')
        self.setDefaultButton(ExportDialogABC.CLOSEBUTTON)

    def _rejectDialog(self):
        # NOTE:ED - not required for exportDialogABC
        self.reject()

    def initialise(self, userFrame):
        """Create the widgets for the userFrame
        """
        # spectrum selection
        spectrumLabel = Label(userFrame, 'Spectrum', grid=(0, 0), hAlign='r')
        self.spectrumPulldown = PulldownList(userFrame, grid=(0, 1), callback=self._setSpectrum, gridSpan=(1, 2))

        # projection axis
        axisLabel = Label(userFrame, 'Projection axis', grid=(2, 0), hAlign='r')
        self.projectionAxisPulldown = PulldownList(userFrame, grid=(2, 1), gridSpan=(1, 2))

        # method
        methodLabel = Label(userFrame, 'Projection method', grid=(4, 0), hAlign='r')
        self.methodPulldown = PulldownList(userFrame, grid=(4, 1), gridSpan=(1, 2), callback=self._setMethod)
        self.methodPulldown.setData(PROJECTION_METHODS)

        # threshold
        thresholdLabel = Label(userFrame, 'Threshold', grid=(5, 0), hAlign='r')
        self.thresholdData = ScientificDoubleSpinBox(userFrame, grid=(5, 1), gridSpan=(1, 2), vAlign='t', min=0.1, max=1e12)

        # Contour colours checkbox
        contourLabel = Label(userFrame, 'Preserve contour colours', grid=(6, 0), hAlign='r')
        self.contourCheckBox = CheckBox(userFrame, checked=True, grid=(6, 1))

        userFrame.addSpacer(5, 5, grid=(7, 1), expandX=True, expandY=True)

        if self.project:
            if self.validSpectra:
                self.spectrumPulldown.setData([s.pid for s in self.validSpectra])

            # select a spectrum from current or validSpectra
            if self.application.current.strip is not None and \
                    not self.application.current.strip.isDeleted and \
                    len(self.application.current.strip.spectra) > 0 and \
                    self.application.current.strip.spectra[0].dimensionCount == 3:
                self.spectrum = self.application.current.strip.spectra[0]
            else:
                self.spectrum = self.validSpectra[0]

        else:
            self.spectrum = None

    def populate(self, userFrame):
        """populate the widgets
        """
        with self.blockWidgetSignals(userFrame):
            if self.spectrum:
                # update all widgets to correct settings
                self.spectrumPulldown.set(self.spectrum.pid)
                self._setSpectrum(self.spectrum.pid)
                self._setMethod(self.methodPulldown.currentText())

    def _setSpectrum(self, spectrumPid):
        """Callback for selecting spectrum"""
        spectrum = self.project.getByPid(spectrumPid)
        self.projectionAxisPulldown.setData(spectrum.axisCodes)
        self.thresholdData.set(spectrum.positiveContourBase)

    def _setMethod(self, method):
        """Callback when setting method"""
        if method.endswith('threshold'):
            self.thresholdData.setEnabled(True)
        else:
            self.thresholdData.setEnabled(False)

    @property
    def projectionAxisCode(self):
        return self.projectionAxisPulldown.currentText()

    @property
    def axisCodes(self):
        """Return axisCodes of projected spectra (as defined by self.projectionAxisCode)"""
        spectrum = self.project.getByPid(self.spectrumPulldown.currentText())
        ac = list(spectrum.axisCodes)
        ac.remove(self.projectionAxisCode)
        return ac

    def makeProjection(self):
        """Make projection from the specified spectrum.

        Spectrum is saved alongside the original spectrum, if this folder is not available then
        the spectrum is saved in the project/data/spectra folder.
        """
        # get options
        if (spectrum := self.project.getByPid(self.spectrumPulldown.currentText())):
            axisCodes = self.axisCodes
            method = self.methodPulldown.currentText()
            threshold = self.thresholdData.get()

            # default path is spectrum
            defaultPath = spectrum.dataSource.parentPath

            with progressManager(self, 'Making %s projection from %s' % ('-'.join(axisCodes), spectrum.name)):
                projectedSpectrum = spectrum.extractProjectionToFile(axisCodes, method=method, threshold=threshold)
                if not self.contourCheckBox.get():
                    # settings are copied by default from the originating spectrum
                    projectedSpectrum._setDefaultContourColours()

        else:
            raise RuntimeError(f'Error getting spectrum from pulldown')



def main():
    from ccpn.ui.gui.widgets.Application import newTestApplication

    app = newTestApplication()
    dialog = SpectrumProjectionPopup()
    dialog.exec_()


if __name__ == '__main__':
    main()
