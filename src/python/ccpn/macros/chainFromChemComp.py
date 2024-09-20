"""
This macro opens a popup for creating a chain from a ChemComp saved as xml file.
A new chain containing only one residue corresponding to the small molecule and its atoms.
Atoms are named as defined in the ChemComp file.
Residue name is set from the chemComp ccpCode.
Note. Also a substance will be added in the project.

ChemComps are available from
    - https://github.com/VuisterLab/CcpNmr-ChemComps/tree/master/data/pdbe/chemComp/archive/ChemComp
    or
    - build your own using ChemBuild:
        - open chembuild
        - new compound
        - export CCPN ChemComp XML File

Run the macro and select the Xml file.

Alpha released in Version 3.0.3
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
__dateModified__ = "$dateModified: 2024-04-04 15:19:21 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2021-03-05 11:01:32 +0000 (Fri, March 05, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================


from ccpn.core.Chain import _fetchChemCompFromFile, _newChainFromChemComp, _checkChemCompExists
from ccpn.ui.gui.widgets.FileDialog import ChemCompFileDialog
from ccpn.util.Logging import getLogger
from ccpn.util.Path import aPath
from PyQt5 import QtCore, QtGui, QtWidgets
import ccpn.ui.gui.widgets.CompoundWidgets as cw
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.lib.GuiPath import PathEdit
from ccpn.ui.gui.widgets import MessageDialog
import traceback

A = str(u"\u212B")

AddAtomGroups = 'expandFromAtomSets'
AddPseudoAtoms = 'addPseudoAtoms'
RemoveDuplicateEquivalentAtoms = 'removeDuplicateEquivalentAtoms'
AddNonstereoAtoms = 'addNonstereoAtoms'
SetBoundsForAtomGroups = 'setBoundsForAtomGroups'
AtomNamingSystem = 'atomNamingSystem'
PseudoNamingSystem = 'pseudoNamingSystem'
ChainCode = 'chainCode'
Code3Letter = 'code3Letter'
ResNumber = 'ResNumber'

DefaultAddAtomGroups = True
DefaultAddPseudoAtoms = False
DefaultRemoveDuplicateEquivalentAtoms = False
DefaultAddNonstereoAtoms = False
DefaultSetBoundsForAtomGroups = False
DefaultAtomNamingSystem = 'PDB_REMED'
DefaultPseudoNamingSystem = 'AQUA'
DefaultChainCode = 'L'
DefaultCode3Letter = 'LIG'
DefaultResNumber = 1

DefaultOptions = {
                ChainCode: DefaultChainCode,
                Code3Letter: DefaultCode3Letter,
                ResNumber: DefaultResNumber,
                AddAtomGroups: DefaultAddAtomGroups,
                AddPseudoAtoms: DefaultAddPseudoAtoms,
                RemoveDuplicateEquivalentAtoms: DefaultRemoveDuplicateEquivalentAtoms,
                AddNonstereoAtoms: DefaultAddNonstereoAtoms,
                SetBoundsForAtomGroups: DefaultSetBoundsForAtomGroups,
                AtomNamingSystem: DefaultAtomNamingSystem,
                PseudoNamingSystem: DefaultPseudoNamingSystem,
                }


class NewChainFromChemComp(CcpnDialogMainWidget):
    """

    """
    FIXEDWIDTH = True
    FIXEDHEIGHT = False

    title = 'New Chain From ChemComp'
    def __init__(self, parent=None, mainWindow=None, title=title,  **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title,
                         size=(400, 200), minimumSize=None, **kwds)

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

        self._createWidgets()

        # enable the buttons
        self.tipText = 'Create a new Chain from a selected ChemComp'
        self.setOkButton(callback=self._okCallback, tipText =self.tipText, text='Ok', enabled=True)
        self.setCloseButton(callback=self.reject, tipText='Close')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def _createWidgets(self):

        row = 0
        self.filePathW = Widget(self.mainWidget, setLayout=True, grid=(row, 0))

        self.filePathLabel = Label(self.filePathW, text="ChemComp Path", grid=(0, 0),)

        self.filePathEntry = Widget(self.filePathW, setLayout=True, grid=(row, 1))
        self.filePathEdit = PathEdit(self.filePathEntry, backgroundText='myPath/other+code+ChemBuild.xml',
                                     grid=(0, 0), vAlign='t', tipText='Absolute path to the ChemComp file in .xml format')
        self.filePathButton = Button(self.filePathEntry, grid=(0, 1), callback=self._getUserPipesPath,
                                          icon='icons/directory', hPolicy='fixed')
        # self.userPipesPath.textChanged.connect(None)
        self.filePathEntry.setFixedWidth(300)


        row += 1
        self.chainCodeW = cw.EntryCompoundWidget(self.mainWidget, labelText='Chain Code',
                                                 entryText=DefaultOptions.get(DefaultChainCode),
                                                 grid=(row, 0), gridSpan=(1, 1))
        row += 1
        self.res3LettW = cw.EntryCompoundWidget(self.mainWidget, labelText='Residue 3 Letter Code',
                                                 entryText=DefaultOptions.get(Code3Letter),
                                                 grid=(row, 0), gridSpan=(1, 1))

        row += 1
        self.resNumW = cw.SpinBoxCompoundWidget(self.mainWidget, labelText='Residue Number',
                                                 value=DefaultOptions.get(ResNumber),
                                                 minimum=1, maximum=10000,
                                                 grid=(row, 0), gridSpan=(1, 1))

        row += 1
        self.addAtomGroupsW = cw.CheckBoxCompoundWidget(self.mainWidget,
                                                         labelText='Expand Atoms from Atom Groups',
                                                         checked=DefaultOptions.get(AddAtomGroups, True),
                                                         grid=(row, 0), gridSpan=(1, 1))

        row += 1

        self.addNonstereoAtomsW = cw.CheckBoxCompoundWidget(self.mainWidget,
                                                            labelText='Add Non Stereo-Specific Atom',
                                                            checked=DefaultOptions.get(AddNonstereoAtoms),
                                                            grid=(row, 0), gridSpan=(1, 1))

        self.mainWidget.getLayout().setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        self._populateWsFromProjectInfo()
        self._alignWidgets(self.mainWidget)

    def _alignWidgets(self, parent):
        if isinstance(parent, QtWidgets.QWidget):
            for w in parent.children():
                if isinstance(w, QtWidgets.QFrame):
                    for _sc in w.children():
                        if not isinstance(_sc, QtWidgets.QGridLayout):
                            if not isinstance(_sc,QtWidgets.QLabel):
                                _sc.setFixedWidth(300)

    def _populateWsFromProjectInfo(self):
        from ccpn.core.lib.MoleculeLib import _nextChainCode

        if self.project:
            chainCode = _nextChainCode(self.project)
            self.chainCodeW.setText(chainCode)

    def _getUserPipesPath(self):
        if self.project:
            dial = ChemCompFileDialog(self.mainWindow, acceptMode='select')
            dial._show()
            filePath = dial.selectedFile()
            if filePath:
                self.filePathEdit.setText(filePath)

    def _okCallback(self):
        if self.project:
            filePath = self.filePathEdit.get()
            if filePath:
                expandFromAtomSets =  self.addAtomGroupsW.get() or DefaultOptions[AddAtomGroups]
                addNonstereoAtoms = self.addNonstereoAtomsW.get() or DefaultOptions[AddNonstereoAtoms]
                code3Letter = self.res3LettW.getText() or DefaultOptions[Code3Letter]
                renumberFromResidue = self.resNumW.getValue() or DefaultOptions[ResNumber]
                try:
                    ccpCode = 'Ccp'
                    basename = aPath(filePath).basename
                    ll = basename.split('+') # assuming the file is an old xml type with + separators or created from Chembuild.
                    if len(ll) > 1:
                        ccpCode = ll[1]
                    prevChemComp = _checkChemCompExists(self.project, ccpCode)
                    if prevChemComp:
                        answ = MessageDialog.showYesNo('A ChemComp with the same ccpCode is already loaded',
                                                       'Do you want to create a new chain with the previously loaded ChemComp?')
                        if not answ:
                            MessageDialog.showError('Aborted', 'Please create a newChemComp with a different ccpCode, or use a different ChemComp file.')
                            return

                    chemComp = _fetchChemCompFromFile(self.project, filePath)
                    chemComp.__dict__['code3Letter'] = code3Letter

                    chain = _newChainFromChemComp(self.project, chemComp,
                                                  chainCode = self.chainCodeW.getText(),
                                                  expandFromAtomSets = expandFromAtomSets,
                                                  addNonstereoAtoms = addNonstereoAtoms
                                                  )

                    chain.renumberResidues(offset=renumberFromResidue-1, start=1)
                    getLogger().info("New Chain available from SideBar")
                except Exception as err:

                    MessageDialog.showError('Error creating Chain from File', str(err))

            else:
                getLogger().warning('No selected xml file. Chain from ChemComp Aborted')

        self.accept()

if __name__ == '__main__':

    def _start(mainWindow=None):
        popup = NewChainFromChemComp(mainWindow=mainWindow)
        popup.show()
        popup.raise_()

    from ccpn.framework.Application import getApplication
    ccpnApplication = getApplication()
    if ccpnApplication:
        _start(ccpnApplication.ui.mainWindow)
    else:
        from ccpn.ui.gui.widgets.Application import TestApplication
        app = TestApplication()
        _start()
        app.start()





