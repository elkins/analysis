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
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore
from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame
from ccpn.ui.gui.popups.AttributeEditorPopupABC import ComplexAttributeEditorPopupABC, VList, MoreLess, Item, _complexAttribContainer
from ccpn.ui.gui.widgets.CompoundWidgets import CompoundViewCompoundWidget
from ccpn.core.Substance import Substance


SEP = ', '
SELECT = '> Select <'
LESS_BUTTON = 'Show less'
MORE_BUTTON = 'Show more'
TYPENEW = 'Type_New'
LABELLING = ['', TYPENEW, '15N', '15N,13C', '15N,13C,2H', 'ILV', 'ILVA', 'ILVAT', 'SAIL', '1,3-13C-_and_2-13C-Glycerol']
BUTTONSTATES = ['New', 'From Existing']

from ccpn.ui.gui.widgets.CompoundWidgets import EntryCompoundWidget, ScientificSpinBoxCompoundWidget, \
    RadioButtonsCompoundWidget, PulldownListCompoundWidget, SpinBoxCompoundWidget, TextEditorCompoundWidget


class SubstancePropertiesPopup(ComplexAttributeEditorPopupABC):
    """
    Substance attributes editor popup
    """

    def _getLabelling(self, obj):
        """Populate the labelling pulldown
        """
        labels = LABELLING.copy()
        newLabel = str(self.obj.labelling or '')
        if newLabel not in labels:
            labels.append(newLabel)
        self.labelling.modifyTexts(labels)
        self.labelling.select(newLabel or '')

    def _getCurrentSubstances(self, obj):
        """Populate the current substances pulldown
        """
        substancePulldownData = [SELECT]
        for substance in self.project.substances:
            substancePulldownData.append(str(substance.id))
        self.currentSubstances.pulldownList.setData(substancePulldownData)

    def _getSpectrum(self, attr, default):
        """change the value from the substance object into a pid for the pulldown
        """
        value = getattr(self, attr, default)
        if value and len(value) > 0:
            return value[0].pid

    def _setSpectrum(self, attr, value):
        """change the pid for the pulldown into the tuple for the substance object
        """
        spectrum = self.project.getByPid(value)
        if spectrum:
            setattr(self, attr, (spectrum,))
        else:
            setattr(self, attr, [])

    def _getCurrentSpectra(self, obj):
        """Populate the spectrum pulldown
        """
        spectrumPulldownData = [SELECT]
        for spectrum in self.project.spectra:
            spectrumPulldownData.append(str(spectrum.pid))
        self.referenceSpectra.pulldownList.setData(spectrumPulldownData)

    def _getSynonym(self, attr, default):
        """change the value from the substance object into a str for the synonym
        """
        value = getattr(self, attr, default)
        if value and len(value) > 0:
            return str(value[0])

    def _setSynonym(self, attr, value):
        """change the str for the synonym into the tuple for the substance object
        """
        if value:
            setattr(self, attr, (str(value),))
        else:
            setattr(self, attr, [])

    def _setLabelling(self, attr, value):
        """Set the labelling with None replacing empty string from the pulldown
        """
        value = value if value else None
        setattr(self, attr, value)

    klass = Substance
    HWIDTH = 150
    attributes = VList(Item('Select Source', RadioButtonsCompoundWidget, None, None, None, None, {'texts'      : BUTTONSTATES,
                                                                                                  'selectedInd': 1,
                                                                                                  'direction'  : 'h',
                                                                                                  'hAlign'     : 'l',
                                                                                                  'addSpacer'  : True}),
                       Item('Current Substances', PulldownListCompoundWidget, None, None, _getCurrentSubstances, None, {'editable': False, 'addSpacer': True}),
                       Item('Name', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '> Enter name <', 'addSpacer': True}),
                       Item('Labelling', PulldownListCompoundWidget, getattr, _setLabelling, _getLabelling, None, {'editable': True, 'addSpacer': True}),
                       Item('Comment', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '> Optional <', 'addSpacer': True}),
                       # keep for the minute
                       # VList([('comment', TextEditorCompoundWidget, getattr, setattr, None, None, {'backgroundText': '> Optional <',
                       #                                                                             'addGrip': False, 'addWordWrap': True,
                       #                                                                             'fitToContents': True,
                       #                                                                             'maximumRows': 5}), ],
                       MoreLess(Item('Synonyms', EntryCompoundWidget, _getSynonym, _setSynonym, None, None, {'backgroundText': '', 'addSpacer': True}),
                                Item('Reference Spectra', PulldownListCompoundWidget, _getSpectrum, _setSpectrum, _getCurrentSpectra, None, {'editable': False, 'addSpacer': True}),
                                Item('Empirical Formula', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '', 'addSpacer': True}),
                                Item('Molecular Mass', ScientificSpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'addSpacer': True}),
                                Item('User Code', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '', 'addSpacer': True}),
                                Item('Cas Number', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '', 'addSpacer': True}),
                                Item('Atom Count', SpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'addSpacer': True}),
                                Item('Bond Count', SpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'addSpacer': True}),
                                Item('Ring Count', SpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'addSpacer': True}),
                                Item('hBond Donor Count', SpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'addSpacer': True}),
                                Item('hBond Acceptor Count', SpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'addSpacer': True}),
                                Item('Polar Surface Area', ScientificSpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'addSpacer': True}),
                                Item('Log Partition Coefficient', ScientificSpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'addSpacer': True}),
                                hWidth=None,
                                fieldWidth=250,
                                name='Advanced',
                                group=1,
                                ),
                       MoreLess(Item('Smiles', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '', 'addSpacer': False}),
                                Item('Compound View', CompoundViewCompoundWidget, None, None, None, None, {'addSpacer': False}),
                                hWidth=None,
                                name='Compound',
                                group=2,
                                ),
                       queueStates=False,
                       hWidth=None,  # redundant?
                       fieldWidth=250,
                       group=1,
                       )

    USESCROLLWIDGET = True
    FIXEDWIDTH = False
    FIXEDHEIGHT = False

    LABELEDITING = True

    def __init__(self, parent=None, mainWindow=None,
                 substance=None, sampleComponent=None, newSubstance=False, **kwds):
        """Initialise the widget
        """
        self.EDITMODE = not newSubstance
        self.WINDOWPREFIX = 'New ' if newSubstance else 'Edit '

        if newSubstance:
            obj = _complexAttribContainer(self)
        else:
            obj = substance

        self.sampleComponent = sampleComponent
        self.substance = substance

        # initialise the widgets in the popup
        super().__init__(parent=parent, mainWindow=mainWindow, obj=obj, **kwds)

        # attach callbacks to the new/fromSubstances radioButton
        if self.EDITMODE:
            self.selectSource.setEnabled(False)
            self.currentSubstances.setEnabled(False)
            self.selectSource.setVisible(False)
            self.currentSubstances.setVisible(False)
            self.name.setEnabled(True)  # False
            self.labelling.setEnabled(True)  # False
        else:
            self.selectSource.radioButtons.buttonGroup.buttonClicked.connect(self._changeSource)
            self.currentSubstances.pulldownList.activated.connect(self._fillInfoFromSubstance)

        self.labelling.pulldownList.activated.connect(self._labellingSpecialCases)
        self.smiles.entry.textEdited.connect(self._smilesChanged)
        self._initialiseCompoundView()

        self._moreLessFrames = []
        for item in self.findChildren(MoreLessFrame):
            item.setCallback(self._moreLessCallback)
            # assume all are initially closed
            self._moreLessFrames.append(item)

        # restrict the scroll-area to the minimum size of the initial widgets - helps to match the other popups
        self._scrollArea.setMinimumSize(self.mainWidget.sizeHint())

    def _postInit(self):
        super()._postInit()
        self._baseSize = self.sizeHint()
        for item in self._moreLessFrames:
            # these should be the closed size-hints
            self._baseSize -= item.sizeHint()

    def _setEnabledState(self, fromSubstances):
        if fromSubstances:
            self.currentSubstances.setEnabled(True)
        else:
            self.currentSubstances.setEnabled(False)
            self.labelling.setEnabled(True)

    def _changeSource(self, button):
        self._setEnabledState(True if button.get() == BUTTONSTATES[1] else False)

    def _fillInfoFromSubstance(self, index):
        selected = self.currentSubstances.getText()
        if selected != SELECT:
            substance = self.project.getByPid('SU:' + selected)
            if substance:
                self.name.setText(str(substance.name))
                newLabel = str(substance.labelling or '')
                if newLabel not in self.labelling.getTexts():
                    self.labelling.pulldownList.addItem(text=newLabel)
                self.labelling.pulldownList.set(newLabel or '')
                self.labelling.setEnabled(True)  # False
        else:
            self.name.setText('')
            self.labelling.pulldownList.setIndex(0)
            self.labelling.setEnabled(True)

        if hasattr(self.name, '_queueCallback'):
            self.name._queueCallback()
        if hasattr(self.labelling, '_queueCallback'):
            self.labelling._queueCallback()

    def _labellingSpecialCases(self, index):
        selected = self.labelling.pulldownList.currentText()
        if selected == TYPENEW:
            self.labelling.pulldownList.setEditable(True)
        else:
            self.labelling.pulldownList.setEditable(self.LABELEDITING)

    def _populate(self):
        super()._populate()
        self.labelling.setEnabled(True)
        self.labelling.pulldownList.setEditable(self.LABELEDITING)
        # populate the compoundView on a revert
        self._smilesChanged(self.obj.smiles)

    def _applyAllChanges(self, changes):
        if self.EDITMODE:
            super()._applyAllChanges(changes)
            name = self.name.getText()
            labelling = self.labelling.getText() or None
            if name != self.obj.name or labelling != self.obj.labelling:
                self.obj.rename(name=name, labelling=labelling)
        else:
            # if new substance then call the new method - self.obj is container of new attributes
            name = self.name.getText()
            labelling = self.labelling.getText() or None
            self.obj = self.project.newSubstance(name=name, labelling=labelling)

            # only apply items that are not in the _VALIDATTRS list - defined by queueStates=True in attributes
            super()._applyAllChanges(changes)

    def _initialiseCompoundView(self):
        view = self.compoundView.compoundView
        if self.obj and isinstance(self.obj, Substance):
            chemComps = self.obj._getChemComps()  # will take only if there is one. We don't want display a chain here!
            if len(chemComps) == 1:  # if chemComp give priority to the Smiles, as it preserves the atom nomenclature.
                from ccpn.ui.gui.widgets.CompoundView import importChemComp

                compound = importChemComp(chemComps[0])
                view.setCompound(compound)
                self.smiles.entry.setEnabled(False)  # otherwise will override the chemComp
                return
            if self.obj.smiles is not None:
                view.setSmiles(self.obj.smiles)
        else:
            view.setSmiles('')

    def _smilesChanged(self, value):
        view = self.compoundView.compoundView
        view.setSmiles(value or '')
        # resize to the new items
        view.updateAll()
        # view.scene().setSceneRect(view.scene().itemsBoundingRect())
        view.resetView()
        view.zoomLevel = 1.0

    def _moreLessCallback(self, moreLessFrame):
        """Resize the dialog to contain the opened/closed moreLessFrames
        """
        _size = QtCore.QSize(self._baseSize)
        for item in self._moreLessFrames:
            _size += item.sizeHint()

        _size.setWidth(self.width())
        self.resize(_size)
