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
__dateModified__ = "$dateModified: 2024-09-16 10:12:12 +0100 (Mon, September 16, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Vicky Higman $"
__date__ = "$Date: 2024-07-01 14:47:20 +0100 (Mon, July 1, 2024) $"
#=========================================================================================
# Start of code
#=========================================================================================

# Still to do:
# - add Tolerances to pop-up
# - add ability to assign to new NmrChain
###############

from contextlib import suppress
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
import ccpn.ui.gui.widgets.PulldownListsForObjects as objectPulldowns
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Entry import Entry
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.ListWidget import ListWidgetPair
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.HLine import HLine
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.lib.ContextManagers import undoBlock


class peaksFromNmrResidues(CcpnDialogMainWidget):
    title = 'Peaks from NmrResidues'

    def __init__(self, parent=None, mainWindow=None, title=title, **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.application = mainWindow.application
            self.current = self.application.current
            self.project = mainWindow.project
        else:
            self.mainWindow = None
            self.application = None
            self.current = None
            self.project = None

        # set up the popup
        self._setWidgets()
        self._populateWidgets()

        # enable the buttons
        self.setOkButton(text='Create Peaks', callback=self._createPeaks, tipText='Create Peaks from '
                                                                                  'NmrResidue Chemical Shifts')
        self.setCancelButton(callback=self.reject)
        self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

    def _setWidgets(self):

        row = 0
        Label(self.mainWidget, text='Select NmrResidue:', grid=(row, 0))
        self.NRPulldown = objectPulldowns.NmrResiduePulldown(self.mainWidget, labelText='', grid=(row, 1),
                                                             callback=self._selectCSLfromNmrResidue,
                                                             mainWindow=self.mainWindow)

        row += 1
        Label(self.mainWidget, text='Select ChemicalShiftList:', grid=(row, 0))
        self.CLPulldown = objectPulldowns.ChemicalShiftListPulldown(self.mainWidget, labelText='', grid=(row, 1),
                                                                    mainWindow=self.mainWindow)

        row += 1
        Label(self.mainWidget, text='Select Spectra:', grid=(row, 0))
        # self.SPPulldown = objectPulldowns.SpectrumPulldown(self.mainWidget, labelText='', grid = (row,1))

        row += 1
        self.SPList = ListWidgetPair(self.mainWidget, grid=(row, 0), gridSpan=(1, 2))
        self._populateSPListFromProj()

        row += 1
        self.mainWidget.addSpacer(0, 10, grid=(row, 0))

        row += 1
        Label(self.mainWidget, text='Select PeakList:', grid=(row, 0))
        self.PLOptions = RadioButtons(self.mainWidget, texts=['First', 'Last', 'New'],
                                      direction='h', grid=(row, 1))
        self.useFirst, self.useLast, self.useNew = self.PLOptions.radioButtons

        row += 1
        self.mainWidget.addSpacer(0, 10, grid=(row, 0))

        row += 1
        Label(self.mainWidget, text='Peak creation method:', grid=(row, 0))
        self.PKOptions = RadioButtons(self.mainWidget, texts=['Place Peaks', 'Pick Picks'], direction='h',
                                      grid=(row, 1))
        self.placePeaks, self.areaPick = self.PKOptions.radioButtons

        row += 1
        self.mainWidget.addSpacer(0, 10, grid=(row, 0))

        row += 1
        self.aliphOnly = CheckBox(self.mainWidget, text='aliphatic Peaks only', checked=True, grid=(row, 0))

        row += 1
        self.mainWidget.addSpacer(0, 10, grid=(row, 0))

        row += 1
        self.checkForPeaks = CheckBox(self.mainWidget, text='check for existing Peaks', checked=True, grid=(row, 0))

        row += 1
        HLine(self.mainWidget, grid=(row, 0), gridSpan=(1, 2))

        row += 1
        self.assignToDifferentNmrResidue = CheckBox(self.mainWidget, text='assign Peaks to new NmrResidue',
                                                    checked=False, grid=(row, 0))

        row += 1
        Label(self.mainWidget, text='Select NmrChain :', grid=(row, 0))
        self.newNCPulldown = objectPulldowns.NmrChainPulldown(self.mainWidget, labelText='', grid=(row, 1),
                                                              mainWindow=self.mainWindow)

        row += 1
        Label(self.mainWidget, text='Set SequenceCode:', grid=(row, 0))
        self.seqCode = Entry(self.mainWidget, labelText='', grid=(row, 1))

    def _cleanupDialog(self):
        """Clean-up and unregister notifiers.
        """
        for ntfy in {self.NRPulldown, self.CLPulldown, self.newNCPulldown}:
            if ntfy:
                ntfy.unRegister()

    def _populateWidgets(self):
        # populate the CSL pulldown from the first selected nmrResidue
        self._selectCSLfromNmrResidue(self.NRPulldown.getText())

    def _populateSPListFromProj(self):
        if self.project:
            self.SPList._populate(self.SPList.leftList, self.project.spectra)

    @staticmethod
    def _isAliphatic(nmratm):
        nonAliphatics = [('PHE', 'G'), ('PHE', 'D'), ('PHE', 'E'), ('PHE', 'Z'),
                         ('TYR', 'G'), ('TYR', 'D'), ('TYR', 'E'), ('TYR', 'Z'),
                         ('HIS', 'G'), ('HIS', 'D'), ('HIS', 'E'),
                         ('TRP', 'G'), ('TRP', 'D'), ('TRP', 'E'), ('TRP', 'Z'), ('TRP', 'CH'), ('TRP', 'HH')]
        for aatype, atmtype in nonAliphatics:
            if aatype in nmratm.pid and atmtype in nmratm.name:
                return False
        if nmratm.name == 'C':
            return False
        else:
            return True

    @staticmethod
    def _areAssigned(nAtom1, nAtom2):
        if nAtom1.atom and nAtom2.atom:
            return True
        else:
            return False

    def _makeNmrAtomPairs(self, AxCdes, pkType):
        result = []
        nr = self.NRPulldown.getSelectedObject()
        for na in nr.nmrAtoms:
            if na.name.startswith(AxCdes[0][0]):
                if (self.aliphOnly and self._isAliphatic(na) is True) or (not self.aliphOnly):
                    for na2 in nr.nmrAtoms:
                        if na2.name.startswith(AxCdes[1][0]) and na2 != na:
                            if (self.aliphOnly and self._isAliphatic(na2) is True) or (not self.aliphOnly):
                                if pkType == 'relayed':
                                    result.append((na, na2))
                                elif pkType == 'bound':
                                    if self._areAssigned(na, na2):
                                        if na2 in na.boundNmrAtoms:
                                            result.append((na, na2))
        return result

    def _getChemShifts(self, atm1, atm2):
        result = []
        csl = self.CLPulldown.getSelectedObject()
        for cs1 in atm1.chemicalShifts:
            if cs1.chemicalShiftList == csl:
                for cs2 in atm2.chemicalShifts:
                    if cs2.chemicalShiftList == csl:
                        result = [cs1, cs2]
        return result

    @staticmethod
    def _getPeakToleranceLimits(atm1, atm2, chemShifts):
        tolerances = {'H': 0.025, 'C': 0.2, 'N': 0.2}  # Tolerances in ppm
        lims = [chemShifts[0].value - tolerances[atm1.name[0]],
                chemShifts[0].value + tolerances[atm1.name[0]],
                chemShifts[1].value - tolerances[atm2.name[0]],
                chemShifts[1].value + tolerances[atm2.name[0]]]
        return lims

    def _getPeakList(self, sp):
        pl = None
        if self.useFirst.isChecked():
            pl = sp.peakLists[0]
        elif self.useLast.isChecked():
            pl = sp.peakLists[-1]
        elif self.useNew.isChecked():
            pl = sp.newPeakList()
        return pl

    @staticmethod
    def _peakPresent(peakList, limits):
        for pk in peakList.peaks:
            if limits[0] < pk.ppmPositions[0] < limits[1] and limits[2] < pk.ppmPositions[1] < limits[3]:
                return True
        return False

    def _assignPeak(self, pk, atm1, atm2, axCodes):
        if self.assignToDifferentNmrResidue.isChecked():
            newnc = self.newNCPulldown.getSelectedObject()
            newnr = newnc.fetchNmrResidue(sequenceCode=self.seqCode.get(), residueType=atm1.nmrResidue.residueType)
            newna1 = newnr.fetchNmrAtom(name=atm1.name, isotopeCode=atm1.isotopeCode)
            newna2 = newnr.fetchNmrAtom(name=atm2.name, isotopeCode=atm2.isotopeCode)
        else:
            newna1 = atm1
            newna2 = atm2
        for axCode, na in zip(axCodes, [newna1, newna2]):
            pk.assignDimension(axCode, na)

    def _pickPeak(self, atm1, atm2, limits, peakList, axCdes):
        # peaks = peakList.pickPeaksRegion(regionToPick={axCdes[0]: [limits[0],limits[1]], axCdes[1]: [limits[2], limits[3]]},
        # 							   doPos=True, doNeg=True, minLinewidth=None, exclusionBuffer=None,
        # 							   minDropFactor=0.1, checkAllAdjacent=True, fitMethod='parabolic',
        # 							   excludedRegions=None, excludedDiagonalDims=None,
        # 							   excludedDiagonalTransform=None, estimateLineWidths=True)

        _regionToPick = {axCdes[0]: [limits[0], limits[1]], axCdes[1]: [limits[2], limits[3]]}
        _spectrum = peakList.spectrum
        # may create a peakPicker instance if not defined, subject to settings in preferences
        _peakPicker = _spectrum.peakPicker
        if _peakPicker:
            _peakPicker.dropFactor = 0.1
            _peakPicker.fitMethod = 'parabolic'
            _peakPicker.setLineWidths = True
            peaks = _spectrum.pickPeaks(peakList, _spectrum.positiveContourBase,
                                        _spectrum.negativeContourBase,
                                        **_regionToPick)

            for peak in peaks:
                self._assignPeak(peak, atm1, atm2, axCdes)
                # peak.assignDimension(axCdes[0], atm1)
                # peak.assignDimension(axCdes[1], atm2)

        else:
            showWarning('PickPeaks', f'peakPicker not found for peakList {peakList}')

    def _placePeak(self, atm1, atm2, spectrum, peakList, axCdes):
        peak = peakList.newPeak(ppmPositions=(atm1.chemicalShifts[0].value, atm2.chemicalShifts[0].value))
        self._assignPeak(peak, atm1, atm2, axCdes)
        # peak.assignDimension(axCdes[0], atm1)
        # peak.assignDimension(axCdes[1], atm2)
        peak.height = spectrum.getHeight((atm1.chemicalShifts[0].value, atm2.chemicalShifts[0].value))

    def _determineAndPickPeaks(self, peakList, axCdes, pkType):
        pairsList = self._makeNmrAtomPairs(axCdes, pkType)
        spectrum = peakList.spectrum
        for atm1, atm2 in pairsList:
            chemShifts = self._getChemShifts(atm1, atm2)
            if len(chemShifts) == 2:
                limits = self._getPeakToleranceLimits(atm1, atm2, chemShifts)
                if self.checkForPeaks.isChecked() and not self._peakPresent(peakList, limits):
                    if self.areaPick.isChecked():
                        self._pickPeak(atm1, atm2, limits, peakList, axCdes)
                    else:
                        self._placePeak(atm1, atm2, spectrum, peakList, axCdes)
                elif not self.checkForPeaks.isChecked():
                    if self.areaPick.isChecked():
                        self._pickPeak(atm1, atm2, limits, peakList, axCdes)
                    else:
                        self._placePeak(atm1, atm2, spectrum, peakList, axCdes)
            else:
                showWarning('No ChemicalShifts found', f'NmrResidue {self.NRPulldown.getSelectedObject()} does not '
                                                       f'contain Chemical Shifts in the '
                                                       f'{self.CLPulldown.getSelectedObject()} ChemicalShiftList.\n'
                                                       f'Please select a different combination of NmrResidue and'
                                                       f'ChemicalShiftList.')
                break

    def _createPeaks(self):
        with undoBlock():
            # sp = self.SPPulldown.getSelectedObject()
            spectrumPids = self.SPList.getRightList()
            for pid in spectrumPids:
                sp = self.project.getByPid(pid)
                if not sp.experimentType:
                    showWarning('Missing Experiment Type', 'Please make sure all your spectra have an Experiment Type '
                                                           'associated with them (use shortcut ET to set these)')
                    runMacro = False
                elif len(sp.axisCodes) != 2:
                    showWarning('Incorrect Dimensionality', 'This macro is only set up for 2D spectra.')
                    runMacro = False
                elif 'Jcoupling' in sp.experimentType or 'Jmultibond' in sp.experimentType:
                    showWarning('Experiment Type not implemented: ' + sp.experimentType,
                                'Sorry, this macro won\'t currently work on the experiment '
                                'type selected for spectrum ' + sp.name + '.')
                    runMacro = False
                else:
                    runMacro = True

                if runMacro:
                    if 'relayed' in sp.experimentType or 'through-space' in sp.experimentType:
                        pl = self._getPeakList(sp)
                        self._determineAndPickPeaks(pl, axCdes=sp.axisCodes, pkType='relayed')
                    else:
                        pl = self._getPeakList(sp)
                        self._determineAndPickPeaks(pl, axCdes=sp.axisCodes, pkType='bound')

        return self.accept()

    def _selectCSLfromNmrResidue(self, nmrResidue):
        from ccpn.util.OrderedSet import OrderedSet

        nmrResidue = self.project.getByPid(nmrResidue) if isinstance(nmrResidue, str) else nmrResidue
        print(f'=> {nmrResidue}')
        if not isinstance(nmrResidue, NmrResidue):
            raise TypeError(f'{nmrResidue} is not an NmrResidue')

        if CSLs := OrderedSet(cs.chemicalShiftList for nmrAtm in nmrResidue.nmrAtoms
                              for cs in nmrAtm.chemicalShifts):
            with suppress(Exception):
                self.CLPulldown.select(list(CSLs)[0].pid)


if __name__ == "__main__":
    popup = peaksFromNmrResidues(mainWindow=mainWindow)
    popup.show()
    popup.raise_()
