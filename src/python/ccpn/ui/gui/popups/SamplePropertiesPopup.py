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
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from functools import partial
from ccpn.ui.gui.popups.AttributeEditorPopupABC import ComplexAttributeEditorPopupABC, \
    VList, HList, Item, Separator
from ccpn.core.Sample import Sample, DEFAULTAMOUNTUNITS, DEFAULTIONICSTRENGTHUNITS
from ccpn.ui.gui.widgets.CompoundWidgets import EntryCompoundWidget, ScientificSpinBoxCompoundWidget, \
    SpinBoxCompoundWidget, PulldownListCompoundWidget
from ccpn.util.Constants import AMOUNT_UNITS, amountUnits, IONICSTRENGTH_UNITS


class SamplePropertiesPopup(ComplexAttributeEditorPopupABC):
    """
    Sample attributes editor popup
    """

    def _get(self, attr, default):
        """change the value from the sample object into an index for the radioButton
        """
        value = getattr(self, attr, default)
        return amountUnits.index(value) if value and value in amountUnits else 0

    def _set(self, attr, index):
        """change the index from the radioButtons into the string for the sample object
        """
        value = amountUnits[index if index and 0 <= index < len(amountUnits) else 0]
        setattr(self, attr, value)

    def _getUnits(self, obj, unitType=None, unitList=None):
        """Populate the units pulldowns
        """
        units = [val for val in unitList]
        value = getattr(self.obj, unitType)
        newUnit = str(value) if value else ''
        if newUnit and newUnit not in units:
            units.append(newUnit)
        getattr(self, unitType).modifyTexts(units)
        getattr(self, unitType).select(newUnit or '')

    def _setUnits(self, attr, value):
        """Set the units type with None replacing empty string
        """
        value = value if value else None
        setattr(self, attr, value)

    klass = Sample  # The class whose properties are edited/displayed
    HWIDTH = 50
    SHORTWIDTH = 140

    attributes = VList(Item('Name', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '> Enter name <'}),
                       Item('Comment', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '> Optional <'}),
                       Separator(),
                       HList(VList(Item('Amount', ScientificSpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0}),
                                   Item('Ionic Strength', ScientificSpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0}),
                                   hWidth=None,
                                   group=1,
                                   ),
                             VList(Item('Amount Units', PulldownListCompoundWidget,
                                        getattr, _setUnits, partial(_getUnits, unitType='amountUnits', unitList=('',) + AMOUNT_UNITS), None,
                                        {'editable': False}),
                                   Item('Ionic Strength Units', PulldownListCompoundWidget,
                                        getattr, _setUnits, partial(_getUnits, unitType='ionicStrengthUnits', unitList=('',) + IONICSTRENGTH_UNITS), None,
                                        {'editable': False}),
                                   hWidth=None,
                                   group=2,
                                   ),
                             hWidth=None,
                             ),
                       Separator(),
                       Item('pH', ScientificSpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'max': 14, 'decimals': 2}),
                       Item('Batch Identifier', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': ''}),
                       Item('Plate Identifier', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': ''}),
                       Item('Row Number', SpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'step': 1}),
                       Item('Column Number', SpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0, 'step': 1}),
                       hWidth=None,
                       group=3,
                       )

    FIXEDWIDTH = True
    FIXEDHEIGHT = True
    ENABLEREVERT = True

    def __init__(self, parent=None, mainWindow=None, obj=None,
                 sample=None, **kwds):
        obj = sample
        super().__init__(parent=parent, mainWindow=mainWindow, obj=obj, **kwds)

    def _applyAllChanges(self, changes):
        """Apply all changes - add new sample
        """
        super()._applyAllChanges(changes)
        if not self.EDITMODE:
            # use the blank container as a dict for creating the new sample
            self.project.newSample(**self.obj)

    def _populateInitialValues(self):
        super(SamplePropertiesPopup, self)._populateInitialValues()

        # set the defaults for the units pulldowns
        self.obj.amountUnits = DEFAULTAMOUNTUNITS
        self.obj.ionicStrengthUnits = DEFAULTIONICSTRENGTHUNITS
