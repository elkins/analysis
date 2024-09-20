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
__dateModified__ = "$dateModified: 2024-04-04 15:19:23 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.util.Constants import concentrationUnits
from ccpn.ui.gui.popups.AttributeEditorPopupABC import ComplexAttributeEditorPopupABC, \
    VList, _complexAttribContainer, Item, Separator
from ccpn.core.SampleComponent import SampleComponent
from ccpn.ui.gui.widgets.CompoundWidgets import EntryCompoundWidget, ScientificSpinBoxCompoundWidget, \
    RadioButtonsCompoundWidget, PulldownListCompoundWidget


SELECT = '> Select <'
TYPECOMPONENT = [SELECT, 'Compound', 'Solvent', 'Buffer', 'Target', 'Inhibitor ', 'Other']
C_COMPONENT_UNIT = (SELECT,) + concentrationUnits
TYPENEW = 'Type_New'
LABELLING = ['', TYPENEW, '15N', '15N,13C', '15N,13C,2H', 'ILV', 'ILVA', 'ILVAT', 'SAIL', '1,3-13C-_and_2-13C-Glycerol']
BUTTONSTATES = ['New', 'From Substances']
WIDTH = 150


class SampleComponentPopup(ComplexAttributeEditorPopupABC):
    """
    SampleComponent attributes editor popup
    """

    LABELEDITING = True

    def _get(self, attr, default):
        """change the value from the sample object into an index for the radioButton
        """
        value = getattr(self, attr, default)
        return TYPECOMPONENT.index(value) if value and value in TYPECOMPONENT else 0

    def _set(self, attr, index):
        """change the index from the radioButtons into the string for the sample object
        """
        value = TYPECOMPONENT[index if index and 0 <= index < len(TYPECOMPONENT) else 0]
        setattr(self, attr, value)

    def _getRoleTypes(self, sampleComponent):
        """Populate the role pulldown
        """
        self.role.modifyTexts(TYPECOMPONENT)
        self.role.select(self.obj.role or SELECT)

    def _getConcentrationUnits(self, sampleComponent):
        """Populate the concentrationUnit pulldown
        """
        self.concentrationUnit.modifyTexts(C_COMPONENT_UNIT)
        self.concentrationUnit.select(self.obj.role or SELECT)

    def _setSampleComponentAttrib(self, attr, value):
        """Set the valid attrib from pulldown
        Remove the 'Select item' and replace with None
        """
        value = value if value != SELECT else None
        setattr(self, attr, value)

    def _getLabelling(self, sampleComponent):
        """Populate the labelling pulldown
        """
        labels = LABELLING.copy()
        newLabel = str(self.obj.labelling or '')
        if newLabel not in labels:
            labels.append(newLabel)
        self.labelling.modifyTexts(labels)
        self.labelling.select(newLabel or '')

    def _getCurrentSubstances(self, sampleComponent):
        """Populate the current substances pulldown
        """
        substancePulldownData = [SELECT]
        for substance in self.project.substances:
            substancePulldownData.append(str(substance.id))
        self.currentSubstances.pulldownList.setData(substancePulldownData)

    def _setLabelling(self, attr, value):
        """Set the labelling with None replacing empty string from the pulldown
        """
        value = value if value else None
        setattr(self, attr, value)

    klass = SampleComponent  # The class whose properties are edited/displayed
    HWIDTH = 150
    attributes = VList(VList(Item('Select Source', RadioButtonsCompoundWidget, None, None, None, None, {'texts'      : BUTTONSTATES,
                                                                                                        'selectedInd': 1,
                                                                                                        'direction'  : 'h',
                                                                                                        'hAlign'     : 'l'}),
                             Item('Current Substances', PulldownListCompoundWidget, None, None, _getCurrentSubstances, None, {'editable': False}),
                             queueStates=False,
                             hWidth=None,
                             group=1,
                             ),
                       (_separator := Separator()),  # a bit of a cheat :)
                       Item('Name', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '> Enter name <'}),
                       Item('Labelling', PulldownListCompoundWidget, getattr, _setLabelling, _getLabelling, None, {'editable'      : True,
                                                                                                                   'backgroundText': '> Enter user label <'}),
                       Item('Comment', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '> Optional <'}),
                       Item('Role', PulldownListCompoundWidget, getattr, _setSampleComponentAttrib, _getRoleTypes, None, {'editable': False}),
                       Item('Concentration Unit', PulldownListCompoundWidget, getattr, _setSampleComponentAttrib, _getConcentrationUnits, None, {'editable': False}),
                       Item('Concentration', ScientificSpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0}),
                       hWidth=None,
                       group=1,
                       )

    FIXEDWIDTH = True
    FIXEDHEIGHT = True
    ENABLEREVERT = True

    def __init__(self, parent=None, mainWindow=None, obj=None,
                 sample=None, sampleComponent=None, newSampleComponent=False, **kwds):
        """
        Initialise the widget
        """
        self.EDITMODE = not newSampleComponent
        self.WINDOWPREFIX = 'New ' if newSampleComponent else 'Edit '

        if sample is None and sampleComponent is not None:
            sample = sampleComponent.sample
        self.sample = sample
        self.sampleComponent = sampleComponent

        if newSampleComponent:
            obj = _complexAttribContainer(self)
        else:
            obj = sampleComponent

        # initialise the widgets in the popup
        super().__init__(parent=parent, mainWindow=mainWindow, obj=obj, **kwds)

        # attach callbacks to the new/fromSubstances radioButton
        if self.EDITMODE:
            self.selectSource.setEnabled(False)
            self.currentSubstances.setEnabled(False)
            self.selectSource.setVisible(False)
            self.currentSubstances.setVisible(False)
            self.name.setEnabled(False)
            self.labelling.setEnabled(False)
            self._separator.setVisible(False)
        else:
            self.selectSource.radioButtons.buttonGroup.buttonClicked.connect(self._changeSource)
            self.currentSubstances.pulldownList.activated.connect(self._fillInfoFromSubstance)

        self.labelling.pulldownList.activated.connect(self._labellingSpecialCases)

        # possibly for later if gray 'Select' preferred
        # self.role.pulldownList._highlightCurrentText()
        # self.concentrationUnit.pulldownList._highlightCurrentText()

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
                self.labelling.pulldownList.set(newLabel)
                self.labelling.setEnabled(self.LABELEDITING)
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
        if not self.EDITMODE:
            self.labelling.setEnabled(True)
            self.labelling.pulldownList.setEditable(self.LABELEDITING)

    def _applyAllChanges(self, changes):
        if self.EDITMODE:
            super()._applyAllChanges(changes)

        if not self.EDITMODE:
            # if new sampleComponent then call the new method - self.obj is container of new attributes
            super()._applyAllChanges(changes)

            for item in list(self.obj.keys()):
                # remove items that are not required in newSampleComponent parameters
                if item not in self._VALIDATTRS:
                    del self.obj[item]
            self.sample.newSampleComponent(**self.obj)
