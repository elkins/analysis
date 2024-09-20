"""
A macro to create an "artificial" NOESY PeakList for a structure calculation from a NOESY peak list which
 contains multiplets.
 Any single peaks in the NOESY PeakList will be copied over as they are. Any peaks in multiplets will copied as
 a single peak at the position of the multiplet (which is the average position of the peaks contained in the
 multiplet), with the height of the multiplet (which is the sum of the heights of the peaks contained in the
 multiplet) and with the volume of the multiplet (which is the sum of the volumes of the peaks contained in the
 multiplet).
 This peakList can then be exported in NEF format for use in structure calculation programs such as ARIA, CYANA or
 XPLOR-NIH.

Run the macro to launch a GUI pop-up where you can select the source and target PeakLists.
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
_copyright_ = ""
_credits_ = ""
_licence_ = ("")
_reference_ = ("")
#=========================================================================================
# Last code modification:
#=========================================================================================
_modifiedBy_ = "$modifiedBy: 2024-05-02 14:18:50 +0100 (Thu, May 2, 2024) $"
_dateModified_ = "$dateModified: Vicky Higman $"
_version_ = "$Revision: 3.2.4 $"
#=========================================================================================
# Created:
#=========================================================================================
_author_ = "$Author: 2024-05-02 14:18:50 +0100 (Thu, May 2, 2024) $"
_date_ = "$Date: Vicky Higman $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.PulldownListsForObjects import PeakListPulldown
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.Label import Label
from ccpn.core.lib.ContextManagers import undoBlock
from ccpn.ui.gui.widgets.Font import getFontHeight


class createNoesyPeakListFromMultiplets(CcpnDialogMainWidget):
    title = 'Create NOESY PeakList from Multiplets'

    def __init__(self, parent=None, mainWindow=None, title=title,  **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        # set up the popup
        self._setWidgets()

        # enable the buttons
        self.setOkButton(text='Create NOESY Peaks', callback=self._createPeakList, tipText='Create NOESY Peaks from '
                                                                                           'a PeakList containing Multiplets')
        self.setCancelButton(callback=self.reject)
        self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

    def _setWidgets(self):

        row = 0
        Label(self.mainWidget, text='Select source PeakList:', grid = (row, 0))
        self.sourcePLPulldown = PeakListPulldown(self.mainWidget, labelText='', grid = (row,1))

        row += 1
        self.mainWidget.addSpacer(0, 10, grid=(row, 0))

        row += 1
        Label(self.mainWidget, text='Select PeakList type:', grid = (row, 0))
        self.targetPLOptions = RadioButtons(self.mainWidget, texts=['New',
                                                               'Use existing'],
                                            callback=self._plOptionsCallback, direction='h', grid=(row, 1))
        self.useNewPL, self.useExistingPL = self.targetPLOptions.radioButtons


        row += 1
        self.mainWidget.addSpacer(5, int(1.3 * getFontHeight()), grid=(row, 0))  # EJB hack from CreateNmrChain popup

        self.targetPLPulldownLabel = Label(self.mainWidget, text='Select target PeakList:', grid = (row, 0))
        self.targetPLPulldown = PeakListPulldown(self.mainWidget, labelText='', grid = (row,1))
        self.targetPLPulldownLabel.hide()
        self.targetPLPulldown.hide()

        row += 1
        self.mainWidget.addSpacer(0, 10, grid=(row, 0))


    def _plOptionsCallback(self):
        if self.useNewPL.isChecked():
            self.targetPLPulldownLabel.hide()
            self.targetPLPulldown.hide()
        elif self.useExistingPL.isChecked():
            self.targetPLPulldownLabel.show()
            self.targetPLPulldown.show()


    def _createPeakList(self):
        with undoBlock():
            multiplets = []
            sourcePL = self.sourcePLPulldown.getSelectedObject()
            if self.useExistingPL.isChecked():
                targetPL = self.targetPLPulldown.getSelectedObject()
            else:
                targetPL = sourcePL.spectrum.newPeakList()
            # copy peaks that are not in multiplets and save multiplets into list
            for pk in sourcePL.peaks:
                if not pk.multiplets:
                    pk.copyTo(targetPL)
                else:
                    for mt in pk.multiplets:
                        multiplets.append(mt)

            # remove duplicate multiplets
            multiplets = list(dict.fromkeys(multiplets))
            # create "artificial" peaks at multiplet positions with multiplet height, volume and assignments
            for mt in multiplets:
                pk = targetPL.newPeak(ppmPositions=mt.ppmPositions, height=mt.height, volume=mt.volume)
                if mt.peaks[0].assignmentsByDimensions:
                    pk.assignmentsByDimensions = mt.peaks[0].assignmentsByDimensions

        return self.accept()


if __name__ == "__main__":
    popup = createNoesyPeakListFromMultiplets(mainWindow=mainWindow)
    popup.show()
    popup.raise_()








