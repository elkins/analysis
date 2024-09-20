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
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2019-12-04 12:29:28 +0000 (Wed, December 04, 2019) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.ui.gui.popups.AttributeEditorPopupABC import AttributeEditorPopupABC
from ccpn.ui.gui.widgets.CompoundWidgets import RadioButtonsCompoundWidget, ScientificSpinBoxCompoundWidget
from ccpn.util.Constants import concentrationUnits


class _ConcentrationUnitsObject():
    """Dummy class to hold a className for the attributeEditorPopup
    """
    className = None

    def __init__(self, name='empty'):
        self.className = name


class ConcentrationUnitsPopup(AttributeEditorPopupABC):
    EDITMODE = True
    WINDOWPREFIX = 'Setup '

    # an object just to get the classname
    klass = _ConcentrationUnitsObject('ConcentrationUnits')

    def __init__(self, parent=None, mainWindow=None, obj=None,
                 names=[], values=None, unit=None, **kwds):

        self.EDITMODE = True

        self._parent = parent
        if not parent:
            raise TypeError('Error: ConcentrationUnitsPopup - parent not defined')

        # check that the parent methods are defined
        _methodlist = ('_addConcentrationsFromSpectra', '_kDunit', 'bindingPlot', 'fittingPlot')
        for method in _methodlist:
            if not hasattr(self._parent, method):
                raise TypeError('Error: ConcentrationUnitsPopup - parent does not contain %s' % str(method))

        self._names = names
        self._values = values
        self._unit = unit

        # set up the widget klass and attributes here
        # dummy object to hold the concentrations
        self._obj = _ConcentrationUnitsObject()
        self._obj.molType = concentrationUnits.index(unit)

        # add the first attribute for the molType
        self.attributes = [('molType', RadioButtonsCompoundWidget, getattr, setattr, None, None, {'texts': concentrationUnits}), ]

        # add attributes for each of the spectra
        for name, value in zip(names, values):
            self.attributes.append((name, ScientificSpinBoxCompoundWidget, getattr, setattr, None, None, {'minimum': 0.0}))
            setattr(self._obj, name, value)  #obj[name] = value

        super().__init__(parent=parent, mainWindow=mainWindow, obj=self._obj, **kwds)

    def _applyAllChanges(self, changes):
        """Doesn't use the queued values but uses the mechanism for reverting to the pre-popup values
        (should really check _changes and only update those values)
        """
        # call the super class to update the object
        super()._applyAllChanges(changes)

        # get the list of selected spectra
        spectra = self._parent.spectraSelectionWidget.getSelections()
        vs, u = [getattr(self._obj, name, None) for name in self._names], concentrationUnits[self._obj.molType]

        # apply to the spectra
        self._parent._addConcentrationsFromSpectra(spectra, vs, u)
        self._parent._kDunit = u
        self._parent.bindingPlot.setLabel('bottom', u)
        self._parent.fittingPlot.setLabel('bottom', u)


from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.ConcentrationsWidget import ConcentrationWidget
from ccpn.util.Common import isIterable

# import re
# from ccpn.core.lib.AssignmentLib import CCP_CODES_SORTED, getNmrResiduePrediction
# from ccpn.ui.gui.widgets.CompoundWidgets import EntryCompoundWidget, PulldownListCompoundWidget
# from ccpn.ui.gui.widgets.PulldownListsForObjects import NmrChainPulldown
# from ccpn.ui.gui.popups.AttributeEditorPopupABC import AttributeEditorPopupABC
# from ccpn.util.OrderedSet import OrderedSet
# from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.lib.ContextManagers import undoBlock, undoBlockWithoutSideBar

# class ConcentrationUnitsPopup(CcpnDialogMainWidget):
#
#     def __init__(self, parent=None, mainWindow=None,
#                  names=[], values=None, unit=None,
#                  title='Setup Concentrations', **kwds):
#
#         super().__init__(parent, setLayout=True, windowTitle=title, **kwds)
#
#         self._parent = parent
#
#         if not parent:
#             raise TypeError('Error: ConcentrationUnitsPopup - parent not defined')
#
#         # check that the parent methods are defined
#         _methodlist = ('_addConcentrationsFromSpectra', '_kDunit', 'bindingPlot', 'fittingPlot')
#         for method in _methodlist:
#             if not hasattr(self._parent, method):
#                 raise TypeError('Error: ConcentrationUnitsPopup - parent does not contain %s' % str(method))
#
#         self._names = names
#         self._values = values
#         self._unit = unit
#         self.concentrationWidget = ConcentrationWidget(self.mainWidget, mainWindow=mainWindow,
#                                                        names=names, grid=(0, 0))
#
#         # enable the buttons
#         self.setOkButton(callback=self._okClicked)
#         self.setApplyButton(callback=self._applyClicked)
#         self.setCancelButton(callback=self._cancelClicked)
#         self.setRevertButton(callback=self._revertClicked)
#         self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)
#
#     def _postInit(self):
#         """post initialise functions - setting up buttons and populating the widgets
#         """
#         super()._postInit()
#         self._populate()
#
#     def _populate(self):
#         if self._values and isIterable(self._values):
#             self.concentrationWidget.setValues(self._values)
#         self.concentrationWidget.setUnit(self._unit)
#
#     def _okClicked(self):
#         self._applyClicked()
#         self.accept()
#
#     def _applyClicked(self):
#         # get the list of selected spectra
#         spectra = self._parent.spectraSelectionWidget.getSelections()
#
#         # get the current values from the concentration widget spinboxes
#         vs, u = self.concentrationWidget.getValues(), self.concentrationWidget.getUnit()
#
#         # apply to the spectra
#         self._parent._addConcentrationsFromSpectra(spectra, vs, u)
#         self._parent._kDunit = u
#         self._parent.bindingPlot.setLabel('bottom', self._kDunit)
#         self._parent.fittingPlot.setLabel('bottom', self._kDunit)
#
#     def _cancelClicked(self):
#         self.reject()
#
#     def _revertClicked(self):
#         self._populate()
#         self._applyClicked()
