"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
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
__dateModified__ = "$dateModified: 2025-01-03 12:44:56 +0000 (Fri, January 03, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.core.NmrChain import Chain
from ccpn.ui.gui.popups.AttributeEditorPopupABC import AttributeEditorPopupABC
from ccpn.ui.gui.widgets.MessageDialog import showMulti
from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget
from ccpn.ui.gui.widgets.CompoundWidgets import EntryCompoundWidget

_NAME = 'name'

class ChainPopup(AttributeEditorPopupABC):
    """Chain attributes editor popup
    """
    @staticmethod
    def _getNmrChainName(obj, *args):
        # safely convert the pid to a string for the entry-widget (which should be disabled)
        return str(obj.pid)

    klass = Chain
    attributes = [('Name', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '> Enter name <'}),
                  ('Comment', EntryCompoundWidget, getattr, setattr, None, None, {'backgroundText': '> Optional <'}),
                  ('Compound Name', EntryCompoundWidget, getattr, None, None, None, {}),
                  ('NmrChain', EntryCompoundWidget, _getNmrChainName, None, None, None, {}),
                  ('isCyclic', CheckBoxCompoundWidget, getattr, None, None, None, {}),
                  ]

    _CANCEL = 'Cancel'
    _OK = 'Ok'
    _DONT_SAVE = "Don't Change"

    def _applyAllChanges(self, changes):
        """Apply all changes - update atom name
        """
        # why is this different from SimpleAttributeEditorPopupABC?
        compWidget, _attSet, _attItem = self.edits[_NAME]
        name = compWidget.getText()
        if self.obj.nmrChain is not None and name != self.obj.name:

            reply = showMulti('Edit Chain',
                              'You are changing the name of your Chain.\n'
                              'Do you want to change the name of the associated NmrChain as well?',
                              texts=[self._OK, self._CANCEL, self._DONT_SAVE],
                              okText=self._OK, cancelText=self._CANCEL,
                              parent=self,
                              dontShowEnabled=True,
                              defaultResponse=self._OK,
                              popupId=f'{self.__class__.__name__}')
            if reply == self._CANCEL:
                return
            elif reply == self._OK:
                # also rename the nmrChain
                nmrChain = self.obj.nmrChain
                super()._applyAllChanges(changes)
                nmrChain.name = name
                return

        super()._applyAllChanges(changes)
