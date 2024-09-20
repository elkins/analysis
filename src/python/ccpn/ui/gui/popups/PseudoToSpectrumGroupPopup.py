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
__dateModified__ = "$dateModified: 2024-04-17 12:03:18 +0100 (Wed, April 17, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: gvuister $"
__date__ = "$Date: 2022-11-14 11:28:58 +0100 (Mon, November 14, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

# import ccpn.core.lib.SpectrumLib as specLib
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.PulldownList import PulldownList
# from ccpn.ui.gui.widgets.DoubleSpinbox import ScientificDoubleSpinBox
from ccpn.ui.gui.widgets.MessageDialog import progressManager
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.popups.ExportDialog import ExportDialogABC
# from ccpn.util.Path import aPath


class PseudoToSpectrumGroupPopup(CcpnDialogMainWidget):
    FIXEDHEIGHT = True

    def __init__(self, parent=None, mainWindow=None, title='Pseudo-nD Spectrum to SpectrumGroup', **kwds):

        # for CcpnDialogMainWidget:
        super().__init__(parent=parent, setLayout=True, windowTitle=title,
                         **kwds)

        # self.errorFlag = False  # moved to base-class

        if mainWindow:
            self.mainWindow = mainWindow
            self.project = self.mainWindow.project
            self.application = self.mainWindow.application
        else:
            self.mainWindow = self.project = self.application = None

        self.validSpectra = None
        self.spectrum = None
        self.pseudoDimension = None
        self.actionButtons()

        if self.project:
            # Only select 3D's for now
            self.validSpectra = [sp for sp in self.project.spectra if sp._getPseudoDimension() != 0]

            if not self.validSpectra:
                from ccpn.ui.gui.widgets.MessageDialog import showWarning

                showWarning('No valid spectra', 'No pseudo nD spectra in current dataset')
                self.errorFlag = True
                return

        # for CcpnDialogMainWidget:
        self.initialise(self.mainWidget)
        self.populate(self.mainWidget)

    def actionButtons(self):
        self.setOkButton(callback=self.makeSpectrumGroup, text='Make SpectrumGroup', tipText='Extract spectra along pseudo dimensions and close dialog')
        self.setCloseButton(callback=self._rejectDialog, text='Close', tipText='Close')
        self.setDefaultButton(self.CLOSEBUTTON)

    def _rejectDialog(self):
        # NOTE:ED - not required for exportDialogABC
        self.reject()

    def initialise(self, userFrame):
        """Create the widgets for the userFrame
        """
        # spectrum selection
        row = 0
        Label(userFrame, 'Spectrum', grid=(row, 0), hAlign='r')
        self.spectrumPulldown = PulldownList(userFrame, grid=(row, 1), callback=self._setSpectrum, gridSpan=(1, 2))

        # pseudo dimensions
        row += 1
        Label(userFrame, 'Pseudo dimension', grid=(row, 0), hAlign='r')
        self.pseudoDimensionWidget = LineEdit(userFrame, grid=(row, 1), gridSpan=(1, 2), editable=False)

        # real dimensions
        row += 1
        Label(userFrame, 'Other dimensions', grid=(row, 0), hAlign='r')
        self.realDimensionsWidget = LineEdit(userFrame, grid=(row, 1), gridSpan=(1, 2), editable=False)

        # Contour colours checkbox
        row += 1
        Label(userFrame, 'Preserve contour settings', grid=(row, 0), hAlign='r')
        self.contourCheckBox = CheckBox(userFrame, checked=True, grid=(row, 1))

        row += 1
        userFrame.addSpacer(5, 5, grid=(row, 1), expandX=True, expandY=True)

        self.spectrum = None
        if self.project and self.validSpectra:
                self.spectrumPulldown.setData([s.pid for s in self.validSpectra])
                self.spectrum = self.validSpectra[0]

    def populate(self, userFrame):
        """populate the widgets
        """
        with self.blockWidgetSignals(userFrame):
            if self.spectrum:
                # update all widgets to correct settings
                self.spectrumPulldown.set(self.spectrum.pid)
                self._setSpectrum(self.spectrum.pid)

    def _setSpectrum(self, spectrumPid):
        """Callback for selecting spectrum
        """
        self.spectrum = self.project.getByPid(spectrumPid)
        self.pseudoDimension = self.spectrum._getPseudoDimension()
        pseudoAxisCode = self.spectrum.axisCodes[self.pseudoDimension-1]

        # pseudoDimension output widget
        self.pseudoDimensionWidget.set(f'({self.pseudoDimension},{pseudoAxisCode})')

        # real dimensions output widget
        ac = list(self.spectrum.axisCodes)
        ac.remove(pseudoAxisCode)
        dims = self.spectrum.getByAxisCodes('dimensions', ac)
        _tmp = [f'({dim},{ac})' for dim,ac in zip(dims,ac)]  # a list of '(dim,ac)' strings
        self.realDimensionsWidget.set(', '.join(_tmp))

    def makeSpectrumGroup(self):
        """Make projection from the specified spectrum.

        Spectrum is saved alongside the original spectrum, if this folder is not available then
        the spectrum is saved in the project/data/spectra folder.
        """
        if self.spectrum is not None:
            with progressManager(self, f'Making SpectrumGroup from "{self.spectrum.name}"'):
                spectrumGroup = self.spectrum.pseudoToSpectrumGroup()

                if not self.contourCheckBox.isChecked():
                    # values are copied by default
                    for sp in spectrumGroup.spectra:
                        sp._setDefaultContourValues()
                        sp._setDefaultContourColours()

            self.accept()
