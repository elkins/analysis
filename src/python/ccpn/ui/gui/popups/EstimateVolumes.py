"""
Module Documentation here
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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-10-10 15:45:27 +0100 (Thu, October 10, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-03-16 17:34:13 +0000 (Mon, March 16, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
from ccpn.core.Spectrum import Spectrum
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.ListWidget import ListWidget
from ccpn.ui.gui.widgets.PulldownListsForObjects import SpectrumPulldown
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget


SHOWALLSPECTRA = True


#=========================================================================================
# EstimateVolumesABC - abstract base class
#=========================================================================================

class EstimateVolumesABC(CcpnDialogMainWidget):
    """
    Popup to estimate volumes of peaks in peakList from selected spectrum.
    Spectra are all those in the project.
    A spectrum is selected from the spectra in the current.strip if current.strip exists.
    """
    FIXEDWIDTH = True
    FIXEDHEIGHT = True

    TITLE = 'Estimate Volumes'

    def __init__(self, parent=None, mainWindow=None, title=None, spectra=None, **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title or self.TITLE, **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.application = mainWindow.application
            self.current = self.application.current
            self.project = mainWindow.project
            self.spectra = spectra if spectra else self.project.spectra
        else:
            self.mainWindow = None
            self.application = None
            self.current = None
            self.project = None

        self._createWidgets()

        # enable the buttons
        self.setOkButton(callback=self._estimateVolumes, tipText='Estimate Volumes', text='Estimate Volumes', enabled=False)
        self.setCloseButton(callback=self.reject, tipText='Close')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self._okButton = self.dialogButtons.button(self.OKBUTTON)

        self._populateWidgets()
        self._okButton.setEnabled(True)

    def _createWidgets(self):
        """Create the widgets for the popup
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: function {repr(sys._getframe().f_code.co_name)} not implemented')

    def _populateWidgets(self):
        """Populate the tipTexts and peakList
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: function {repr(sys._getframe().f_code.co_name)} not implemented')

    def _cleanupDialog(self):
        """Clean up notifiers for closing
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError(f'Code error: function {repr(sys._getframe().f_code.co_name)} not implemented')


#=========================================================================================
# EstimatePeakListVolumes
#=========================================================================================

class EstimatePeakListVolumes(EstimateVolumesABC):
    """
    Popup to estimate volumes of peaks in peakList from selected spectrum.
    Spectra are all those in the project.
    A spectrum is selected from the spectra in the current.strip if current.strip exists.
    """
    FIXEDWIDTH = True
    FIXEDHEIGHT = True

    TITLE = 'Estimate PeakList Volumes'

    def __init__(self, parent, *args, **kwds):
        super().__init__(parent, *args, **kwds)

        # select the first spectrum from the current spectrumDisplay
        if self.current is not None and self.current.strip is not None and \
                not self.current.strip.isDeleted and len(self.current.strip.spectra) > 0:
            self.spectrumPullDown.select(self.current.strip.spectra[0].pid)

    def _createWidgets(self):
        """Create the widgets for the popup
        """
        row = 0
        self.peakListFrame = Frame(self.mainWidget, setLayout=True, grid=(row, 0))

        pRow = 0
        self.spectrumPullDown = SpectrumPulldown(self.peakListFrame, self.mainWindow, grid=(pRow, 0), gridSpan=(1, 3),
                                                 callback=self._changePeakLists,
                                                 filterFunction=self._filterToStrip)

        pRow += 1
        self._label = Label(self.peakListFrame, grid=(pRow, 0), gridSpan=(1, 3), text='Select PeakLists:')

        pRow += 1
        self.peakListWidget = ListWidget(self.peakListFrame, multiSelect=True, callback=self._selectPeakLists, tipText='Select PeakLists',
                                         grid=(pRow, 0), gridSpan=(1, 3))
        self.peakListWidget.selectionModel().selectionChanged.connect(self._selectionChanged)

        pRow += 1
        self.peakSelectionRefit = CheckBoxCompoundWidget(self.peakListFrame,
                                                         grid=(pRow, 0), gridSpan=(1, 3), stretch=(0, 0), hAlign='left',
                                                         # fixedWidths=(None, 30),
                                                         orientation='right',
                                                         labelText='Refit peaks without lineWidths (this may change peak positions)',
                                                         checked=True
                                                         )

        self.peakListWidget.setSelectContextMenu()

    def _populateWidgets(self):
        """Populate the tipTexts and peakList
        """
        with self.blockWidgetSignals():
            self._changePeakLists()

    def _changePeakLists(self, *args):
        """Update the peakLists in the table from the current spectrum in the pulldown.
        """
        obj = self.spectrumPullDown.getSelectedObject()

        if isinstance(obj, Spectrum):
            self.peakListWidget.setObjects(obj.peakLists, name='pid')
            self.checkPeakListSelection()

    def _filterToStrip(self, values):
        """Filter the pulldown list to the spectra in the current strip;
        however, need to be able to select all spectra
        (this is currently overriding self.spectra)
        """
        if not SHOWALLSPECTRA and self.current.strip:
            return [specView.spectrum.pid for specView in self.current.strip.spectrumDisplay.spectrumViews]
        else:
            return values

    def _selectPeakLists(self, *args):
        """Respond to click on the peakList widget
        """
        self._okButton.setEnabled(True)

    def checkPeakListSelection(self):
        """Check whether there is only one peakList and select
        """
        objs = self.peakListWidget.getObjects()
        if objs and len(objs) == 1:
            self.peakListWidget.selectObject(objs[0])
            self._selectPeakLists(objs[0])
            self._okButton.setEnabled(True)
        else:
            self._okButton.setEnabled(False)

    def _selectionChanged(self, *args):
        """Callback when the selection in the listWidget has changed
        """
        # enable/disable the ok button
        objs = self.peakListWidget.getSelectedTexts()
        self._okButton.setEnabled(True if objs else False)

    def _estimateVolumes(self):
        """Estimate the volumes for the peaks in the peakLists highlighted in the listWidget
        """
        peakLists = self.peakListWidget.getSelectedObjects()
        if not peakLists:
            showWarning('Estimate PeakList Volumes', 'No peakLists selected')

        else:
            volumeIntegralLimit = self.application.preferences.general.volumeIntegralLimit

            # estimate the volumes for the peakLists
            with undoBlockWithoutSideBar(self.application):

                if self.peakSelectionRefit.isChecked():
                    badPks = []
                    for peakList in peakLists:
                        for pk in peakList.peaks:
                            height = pk.height
                            lineWidths = pk.lineWidths
                            if lineWidths is None or None in lineWidths or height is None:
                                badPks.append(pk)

                    if badPks:
                        # refit the peaks
                        fitMethod = self.application.preferences.general.peakFittingMethod
                        singularMode = False
                        peakList.fitExistingPeaks(badPks, fitMethod=fitMethod, singularMode=singularMode)

                # okay to estimate the volumes
                for peakList in peakLists:
                    peakList.estimateVolumes(volumeIntegralLimit=volumeIntegralLimit, noWarning=True)

                self.peakListWidget._disableLabels([pp.pid for pp in peakLists])
                self.accept()

    def _cleanupDialog(self):
        """Clean up notifiers for closing
        """
        if self.spectrumPullDown:
            self.spectrumPullDown.unRegister()


#=========================================================================================
# EstimatePeakListVolumes
#=========================================================================================

class EstimateCurrentVolumes(EstimateVolumesABC):
    """
    Popup to estimate volumes of peaks in peakList from selected spectrum.
    Spectra are all those in the project.
    A spectrum is selected from the spectra in the current.strip if current.strip exists.
    """
    FIXEDWIDTH = True
    FIXEDHEIGHT = True

    TITLE = 'Estimate Current Volumes'

    def _createWidgets(self):
        """Create the widgets for the popup
        """
        row = 0
        self.peakSelectionFrame = Frame(self.mainWidget, setLayout=True, grid=(row, 0))

        pRow = 0
        self.peakSelectionLabel = Label(self.peakSelectionFrame, grid=(pRow, 0), gridSpan=(1, 3), text='Selected Peaks: <None>          ', tipText='Selected Peaks: <None>')

        pRow += 1
        self.peakSelectionRefit = CheckBoxCompoundWidget(self.peakSelectionFrame,
                                                         grid=(pRow, 0), gridSpan=(1, 3), stretch=(0, 0), hAlign='left',
                                                         # fixedWidths=(None, 30),
                                                         orientation='right',
                                                         labelText='Refit peaks without lineWidths (this may change peak positions)',
                                                         checked=True
                                                         )

    def _populateWidgets(self):
        """Populate the tipTexts and peakList
        """
        with self.blockWidgetSignals():
            peakTexts = [pk.pid for pk in self.current.peaks]
            if len(peakTexts) > 15:
                peakTexts = peakTexts[:12] + ['...', '...'] + peakTexts[-1:]
            tipText = 'Selected Peaks:\n' + '\n'.join(pk for pk in peakTexts)
            text = 'Selected Peaks: ' + \
                   (peakTexts[0] if peakTexts else '') + \
                   ('...' if len(peakTexts) > 1 else '')
            self.peakSelectionLabel.setText(text)
            self.peakSelectionLabel.setToolTip(tipText)

            if not self.current.peaks:
                self.peakSelectionButton.setEnabled(False)

    def _estimateVolumes(self):
        """Estimate the volumes for the selected peaks
        """
        from ccpn.core.lib.peakUtils import estimateVolumes

        # return if both the lists are empty
        if not self.current or not (currentPks := self.current.peaks):
            return

        with undoBlockWithoutSideBar():

            if self.peakSelectionRefit.isChecked():
                # sort bad peaks into peakLists
                badPks = {}
                for pk in currentPks:
                    height = pk.height
                    lineWidths = pk.lineWidths
                    if lineWidths is None or None in lineWidths or height is None:
                        _pks = badPks.setdefault(pk.peakList, [])
                        _pks.append(pk)

                if badPks:
                    # refit the peaks
                    fitMethod = self.application.preferences.general.peakFittingMethod
                    singularMode = False

                    for pkList, pks in badPks.items():
                        if pks:
                            pkList.fitExistingPeaks(pks, fitMethod=fitMethod, singularMode=singularMode)

            estimateVolumes(currentPks, noWarning=True)
            self.accept()

    def _cleanupDialog(self):
        """Clean up notifiers for closing
        """
        pass
