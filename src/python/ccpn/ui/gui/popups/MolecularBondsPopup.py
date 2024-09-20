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
__dateModified__ = "$dateModified: 2024-04-04 15:19:22 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-05-22 15:42:58 +0100 (Mon, May 22, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets
from collections import OrderedDict
from ccpn.core.lib.ContextManagers import undoBlockWithSideBar
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.CompoundWidgets import PulldownListCompoundWidget, \
    ListCompoundWidget, ButtonCompoundWidget
from ccpn.util.OrderedSet import OrderedSet


BONDNAME = 'bondName'
VALIDATOMS = 'validAtoms'
VALIDBONDTYPES = 'validBondTypes'
NEWBONDTYPE = 'newBondType'


class MolecularBondsPopup(CcpnDialogMainWidget):
    FIXEDWIDTH = False
    FIXEDHEIGHT = False

    # could be replaced with a 'plugin' system
    options = [{BONDNAME      : '',
                VALIDATOMS    : None,
                VALIDBONDTYPES: [None, ],
                NEWBONDTYPE   : None,
                },
               {BONDNAME      : 'Disulfide Bonds',
                VALIDATOMS    : ['SG', ],
                VALIDBONDTYPES: ['disulfide', ],
                NEWBONDTYPE   : 'disulfide',
                },
               ]

    def __init__(self, parent=None, mainWindow=None, title='Edit Molecular-Bonds', **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        if mainWindow:
            self.mainWindow = mainWindow
            self.application = self.mainWindow.application
            self.project = self.mainWindow.project
            self.current = self.application.current
        else:
            self.mainWindow = self.application = self.project = self.current = None

        self.setWidgets()
        self._populate()

        # enable the buttons
        self.setCloseButton(callback=self.reject, tipText='Close popup')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def setWidgets(self):
        """Add the widgets to the main-widget area.
        """
        row = 0
        self._bondTypesPulldown = PulldownListCompoundWidget(parent=self.mainWidget,
                                                             mainWindow=self.mainWindow,
                                                             labelText="Bond type",
                                                             grid=(row, 0), gridSpan=(1, 2),
                                                             minimumWidths=(100, 100),
                                                             sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                                             callback=self._selectBondTypeCallback,
                                                             compoundKwds={'backgroundText': '> Select bond-type <'}
                                                             )

        row += 1
        self._group1Pulldown = PulldownListCompoundWidget(parent=self.mainWidget,
                                                          mainWindow=self.mainWindow,
                                                          labelText="Group 1",
                                                          grid=(row, 0), gridSpan=(1, 2),
                                                          minimumWidths=(100, 100),
                                                          sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                                          callback=self._selectGroup1Callback
                                                          )

        row += 1
        self._group2Pulldown = PulldownListCompoundWidget(parent=self.mainWidget,
                                                          mainWindow=self.mainWindow,
                                                          labelText="Group 2",
                                                          grid=(row, 0), gridSpan=(1, 2),
                                                          minimumWidths=(100, 100),
                                                          sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                                          callback=self._selectGroup2Callback
                                                          )

        row += 1
        self._addBondButton = ButtonCompoundWidget(parent=self.mainWidget,
                                                   text="Add Bond",
                                                   buttonAlignment='right',
                                                   grid=(row, 0), gridSpan=(1, 2),
                                                   minimumWidths=(100, 100),
                                                   callback=self._addBondCallback,
                                                   )

        row += 1
        self._bondsList = ListCompoundWidget(self.mainWidget,
                                             labelText='Bonds',
                                             grid=(row, 0), gridSpan=(1, 2),
                                             orientation='centreLeft',
                                             tipText='Current bonds in the project',
                                             texts=[],
                                             defaults=[],
                                             minimumWidths=(100, 100, 100),
                                             )
        self._bondsList.pulldownList.setVisible(False)

        row += 1
        self._deleteBondButton = ButtonCompoundWidget(parent=self.mainWidget,
                                                      text="Delete Bonds",
                                                      buttonAlignment='right',
                                                      grid=(row, 0), gridSpan=(1, 2),
                                                      minimumWidths=(100, 100),
                                                      callback=self._deleteBondsCallback,
                                                      )

        # should be in the widget :|
        self._bondsList.listWidget.changed.connect(self._removeBondsCallback)
        self._bondsList.listWidget.cleared.connect(self._removeBondsCallback)

    def _populate(self):
        """Populate the widget with the current settings
        """
        # set the bond-types, currently only disulfide types can be edited
        options = [opt.get(BONDNAME) for opt in self.options]

        self._bondTypesPulldown.modifyTexts(options)

        self._bondTypesPulldown.setIndex(1)

    def _selectBondTypeCallback(self, *args):
        """Callback for the bond-tyeos pulldown.
        """
        if not self.project:
            return

        if indx := self._bondTypesPulldown.getIndex():
            # only one option so far
            opt = self.options[indx]

            self._atoms = OrderedDict((atm.id, atm) for atm in self.project.atoms
                                      if opt.get(VALIDATOMS) is None or atm.name in opt.get(VALIDATOMS))

            # fill the atom pulldowns
            self._group1Pulldown.modifyTexts(list(self._atoms.keys()))
            self._group2Pulldown.modifyTexts(list(self._atoms.keys()))

            # fill the list-widget from the available project-bonds
            self._bonds = OrderedDict((' - '.join([atm.id for atm in bnd.atoms]), bnd) for bnd in self.project.bonds if bnd.bondType in opt.get(VALIDBONDTYPES))
            self._bondsList.modifyListWidgetTexts(list(self._bonds.keys()))

            # enable/disable pulldown options
            self._enablePulldownItems(self._group1Pulldown)
            self._enablePulldownItems(self._group2Pulldown)
            self._checkPulldownMatch(self._group1Pulldown, self._group2Pulldown)
            self._checkPulldownMatch(self._group2Pulldown, self._group1Pulldown)

        else:
            # set all as empty
            self._atoms = {}
            self._bonds = {}
            self._option = 0
            self._group1Pulldown.modifyTexts([])
            self._group2Pulldown.modifyTexts([])
            self._bondsList.modifyListWidgetTexts([])

    def _checkPulldownMatch(self, comboSource, comboTarget):
        """Disable the option in the target pulldown that matches the source pulldown-text.
        """
        ss = comboSource.getText()

        model = comboTarget.pulldownList.model()
        if ss in (ll := comboTarget.getTexts()):
            if itm := model.item(ll.index(ss)):
                itm.setEnabled(False)

        if comboTarget.getText() == ss:
            comboTarget.setIndex(-1)

    def _getEnabled(self, combo):
        """Get the list of enabled items in a pulldown.
        """
        model = combo.pulldownList.model()
        return [model.item(ii).text() for ii, (_id, _atm) in enumerate(self._atoms.items()) if model.item(ii).isEnabled() is False]

    def _setEnabled(self, combo, values):
        """Enable the required items in the specified pulldown.
        """
        model = combo.pulldownList.model()
        for ii, (_id, _atm) in enumerate(self._atoms.items()):
            state = model.item(ii).text()
            model.item(ii).setEnabled(state in values)

    def _enablePulldownItems(self, combo):
        """Enable/disable the required items in the selected pulldown based on the available project-bonds.
        """
        atomPairs = {bnd.atoms for bnd in self._bonds.values()}
        # atm1 = self._atoms.get(self._group1Pulldown.getText())
        model = combo.pulldownList.model()
        lastIndx = combo.getIndex()
        for ii, (_id, atm) in enumerate(self._atoms.items()):
            itm = model.item(ii)

            if any(atm in _atm for _atm in atomPairs):
                itm.setEnabled(False)
                if ii == lastIndx:
                    combo.setIndex(-1)

            else:
                itm.setEnabled(True)

    def _selectGroup1Callback(self, *args):
        """Handle the callback from the first atom-pulldown.
        """
        self._enablePulldownItems(self._group1Pulldown)
        self._enablePulldownItems(self._group2Pulldown)

        self._checkPulldownMatch(self._group1Pulldown, self._group2Pulldown)
        self._checkPulldownMatch(self._group2Pulldown, self._group1Pulldown)

    def _selectGroup2Callback(self, *args):
        """Handle the callback from the second atom-pulldown.
        (Could be merged as both pulldowns do the same thing.)
        """
        self._enablePulldownItems(self._group1Pulldown)
        self._enablePulldownItems(self._group2Pulldown)

        self._checkPulldownMatch(self._group2Pulldown, self._group1Pulldown)
        self._checkPulldownMatch(self._group1Pulldown, self._group2Pulldown)

    def _addBondCallback(self, *args):
        """Add a enw bond from the atom-pulldown selection.
        """
        # add new bond according to group1/group2 (if not exists)
        if not (indx := self._bondTypesPulldown.getIndex()):
            return

        # only one option so far
        opt = self.options[indx]

        atm1 = self._atoms.get(self._group1Pulldown.getText())
        atm2 = self._atoms.get(self._group2Pulldown.getText())
        if atm1 and atm2:
            with undoBlockWithSideBar():
                # create new bond from project
                self.project.newBond(atoms=(atm1, atm2), bondType=opt.get(NEWBONDTYPE))
                # remove existing HG atoms
                if atm := atm1.residue.getAtom('HG'):
                    atm.delete()
                if atm := atm2.residue.getAtom('HG'):
                    atm.delete()

        # repopulate the widgets
        self._selectBondTypeCallback()

    def _removeBondsCallback(self, *args):
        """Handle options deleted from list-widget.
        Deletes bonds from project.
        """
        preTexts, _objs = self._bondsList.listWidget._preContent
        preTexts = OrderedSet(preTexts)
        postTexts = OrderedSet(self._bondsList.getTexts())

        with undoBlockWithSideBar():
            for txt in preTexts - postTexts:
                if bnd := self._bonds.get(txt):

                    for atm in bnd.atoms:
                        if not atm.residue.getAtom('HG'):
                            # replace the HG atom in the CYS
                            atm.residue.newAtom('HG')
                    bnd.delete()

                    del self._bonds[txt]


        self._enablePulldownItems(self._group1Pulldown)
        self._enablePulldownItems(self._group2Pulldown)
        self._checkPulldownMatch(self._group1Pulldown, self._group2Pulldown)
        self._checkPulldownMatch(self._group2Pulldown, self._group1Pulldown)

    def _deleteBondsCallback(self, *args):
        """Handle callback fom delete-button.
        Deletes selected items from the list-widget.
        """
        selectedTexts = self._bondsList.listWidget.getSelectedTexts()

        with undoBlockWithSideBar():
            for txt in selectedTexts:
                if bnd := self._bonds.get(txt):

                    for atm in bnd.atoms:
                        if not atm.residue.getAtom('HG'):
                            # replace the HG atom in the CYS
                            atm.residue.newAtom('HG')
                    bnd.delete()

                    del self._bonds[txt]

        # remove items from list-widget without emitting spurious signals
        self._bondsList.removeTexts(selectedTexts, blockSignals=True)
        self._enablePulldownItems(self._group1Pulldown)
        self._enablePulldownItems(self._group2Pulldown)
        self._checkPulldownMatch(self._group1Pulldown, self._group2Pulldown)
        self._checkPulldownMatch(self._group2Pulldown, self._group1Pulldown)


def main():
    """Test the widget without a full project.
    """
    from ccpn.ui.gui.widgets.Application import TestApplication
    import ccpn.core.testing.WrapperTesting as WT

    app = TestApplication()

    thisWT = WT.WrapperTesting()
    thisWT.setUp()

    app.project = thisWT.project

    popup = MolecularBondsPopup()  # too many errors for testing here...

    popup.show()
    popup.raise_()

    app.start()

    WT.WrapperTesting.tearDown(thisWT)


if __name__ == '__main__':
    main()
