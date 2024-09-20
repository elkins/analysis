"""
A macro to move all the Spectra in a SpectrumGroup into either
- separate new ChemicalShiftLists, each named with the Spectrum Name (suitable e.g. for a titration)
- a single new ChemicalShiftList with a user specified name (e.g. to move Dynamics data out of your main
    ChemicalShiftList)
- an existing ChemicalShiftList (e.g. to collect together all your Dynamics/RDC/etc. Spectra, so they do not contribute
    to your main ChemicalShiftList for BMRB deposition)

Run the macro to launch a GUI pop-up where you can make your selections.
"""



from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.PulldownListsForObjects import SpectrumGroupPulldown
from ccpn.ui.gui.widgets.PulldownListsForObjects import ChemicalShiftListPulldown
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets import Entry
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.core.lib.ContextManagers import undoBlock
from ccpn.ui.gui.widgets.Font import getFontHeight

class MoveSGSpectraIntoNewCLs(CcpnDialogMainWidget):
    title = 'Move SpectrumGroup Spectra to new Chemical Shift Lists'

    def __init__(self, parent=None, mainWindow=None, title=title,  **kwds):
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

        # enable the buttons
        self.setOkButton(text='Okay', callback=self._moveSpectra, tipText='Move Spectra into new Chemical Shift Lists')
        self.setCancelButton(callback=self.reject)
        self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

    def _setWidgets(self):
        row = 0
        Label(self.mainWidget, text='Select SpectrumGroup:', grid = (row, 0))
        self.SGPulldown = SpectrumGroupPulldown(self.mainWidget, labelText='', grid = (row,1),
                                                callback=self._sgSelectionCallback)

        row += 1
        self.mainWidget.addSpacer(0, 10, grid=(row, 0))

        row += 1
        Label(self.mainWidget, text='Move Spectra into:', grid=(row, 0))

        row += 1
        self.cslOptions = RadioButtons(self.mainWidget, texts=['separate new Chemical Shift Lists',
                                                               'same new Chemical Shift List',
                                                               'existing Chemical Shift List '],
                                       callback=self._cslOptionsCallback, direction='v', grid=(row, 0))
        self.checkBox1, self.checkBox2, self.checkBox3 = self.cslOptions.radioButtons

        row += 1
        self.mainWidget.addSpacer(5, int(1.3 * getFontHeight()), grid=(row, 0))  # EJB hack from CreateNmrChain popup

        self.newCLNameLabel = Label(self.mainWidget, text='New Chemical Shift List Name:', grid = (row, 0))
        self.newCLNameEntry = Entry.Entry(self.mainWidget, text=project.spectrumGroups[0].name, grid=(row, 1), editable=True)
        self.newCLNameLabel.hide()
        self.newCLNameEntry.hide()

        self.CLPulldownLabel = Label(self.mainWidget, text='Select Chemical Shift List:', grid = (row, 0))
        self.CLPulldown = ChemicalShiftListPulldown(self.mainWidget, labelText='', grid=(row, 1))
        self.CLPulldownLabel.hide()
        self.CLPulldown.hide()

    def _sgSelectionCallback(self, *args):
        selectedSG = self.SGPulldown.getSelectedObject()
        self.newCLNameEntry.set(selectedSG.name)

    def _cslOptionsCallback(self):
        if self.checkBox2.isChecked():
            self.newCLNameLabel.show()
            self.newCLNameEntry.show()
        else:
            self.newCLNameLabel.hide()
            self.newCLNameEntry.hide()
        if self.checkBox3.isChecked():
            self.CLPulldownLabel.show()
            self.CLPulldown.show()
        else:
            self.CLPulldownLabel.hide()
            self.CLPulldown.hide()

    def _moveIntoSeparateLists(self, sg):
        for sp in sg.spectra:
            csl = project.newChemicalShiftList(name=sp.name)
            csl.spectra = [sp]

    def _moveIntoSameList(self, sg, name):
        csl = project.newChemicalShiftList(name=name)
        csl.spectra = [sp for sp in sg.spectra]

    def _moveIntoExistingList(self, sg, exCL):
        exCL.spectra = list(exCL.spectra) + [sp for sp in sg.spectra]

    def _moveSpectra(self):
        with undoBlock():
            if self.checkBox1.isChecked():
                self._moveIntoSeparateLists(self.SGPulldown.getSelectedObject())
            elif self.checkBox2.isChecked():
                self._moveIntoSameList(self.SGPulldown.getSelectedObject(), self.newCLNameEntry.get())
            elif self.checkBox3.isChecked():
                self._moveIntoExistingList(self.SGPulldown.getSelectedObject(), self.CLPulldown.getSelectedObject())
        return self.accept()


if __name__ == "__main__":
    popup = MoveSGSpectraIntoNewCLs(mainWindow=mainWindow)
    popup.show()
    popup.raise_()




