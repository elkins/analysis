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
__dateModified__ = "$dateModified: 2024-04-04 15:19:21 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank$"
__date__ = "$Date: 9/05/2017 $"
#=========================================================================================
# Start of code
#=========================================================================================

from dataclasses import dataclass
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget
from ccpn.ui.gui.popups.Dialog import handleDialogApply, CcpnDialogMainWidget
from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier
from ccpn.core.lib.ContextManagers import undoStackBlocking


_ALWAYS_CHECKLIST = ['peaks', 'Peaks', 'integrals', 'Integrals', 'multiplets', 'Multiplets']


@dataclass
class _ItemState:
    """Small class to handle checkboxes
    """
    itemName: str
    values: list
    checkState: bool
    checkBox: object


class DeleteItemsPopup(CcpnDialogMainWidget):
    """Open a small popup to allow deletion of selected 'current' items.
    Items is a tuple of tuples: indexed by the name of the items, containing a list of the items for deletion
    i.e. (('Peaks', peakList, checked), ('Multiplets', multipletList, checked))
    checked sets the state of the checkbox for the option.
    """

    def __init__(self, parent=None, mainWindow=None, title='Delete Items', items=None, **kwds):
        """Initialise the widget
        """
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = self.project = self.current = None
        self.deleteList = []
        self._items = []

        # initialise the content
        self._checkItems(items)
        self._setWidgets()

        self.setOkButton(callback=self._okClicked, tipText='Delete and close')
        self.setCloseButton(callback=self.reject, tipText='Close')

        self.GLSignals = GLNotifier(parent=self)

    def _setWidgets(self):
        """Add widgets to the popup
        """
        row = 0
        self.noteLabel = Label(self.mainWidget, "Delete selected items: ", grid=(row, 0))

        for item in self._items:
            itemName, values, checkState = item.itemName, item.values, item.checkState

            row += 1
            # add a checkbox for each item
            newCheckBox = CheckBoxCompoundWidget(self.mainWidget,
                                                 grid=(row, 0), vAlign='top', stretch=(0, 0), hAlign='left',
                                                 orientation='right',
                                                 # assume that the name is plural
                                                 labelText='{} {}{}'.format(len(values), itemName.rstrip('s'), 's' if len(values) > 1 else ''),
                                                 checked=checkState  # True if itemName in _ALWAYS_CHECKLIST else False
                                                 )
            newCheckBox.setToolTip('\n'.join(str(obj.pid) for obj in values))

            # self.deleteList.append(_ItemState(itemName, values, newCheckBox))
            item.checkBox = newCheckBox

            if len(self._items) == 1:
                # in the only item, so hide the checkboxes, rename the label
                self.noteLabel.setText(f'Do you want to delete {len(values)} {itemName.rstrip("s")}{"s" if len(values) > 1 else ""}?')
                newCheckBox.set(True)
                newCheckBox.setVisible(False)

    def _checkItems(self, items):
        """Check the items are valid
        """
        if not isinstance(items, list):
            raise ValueError('items must be a list')

        for itm in items:
            if not isinstance(itm, (list, tuple)):
                raise ValueError('items must be a list of list or tuple pairs: (name, items)')

            name, values, checkState = itm
            if not isinstance(name, str):
                raise ValueError(f'item {name} must be a str')
            if not isinstance(values, (list, tuple)):
                raise ValueError('values must be a list of list or tuple pairs: (name, items)')
            if not isinstance(checkState, bool):
                raise ValueError(f'checkState must be True/False')

            # get the valid core objects
            objs = self.project.getByPids(values)
            self._items.append(_ItemState(name, objs, checkState, None))

    def _refreshGLItems(self):
        # emit a signal to rebuild all peaks and multiplets
        self.GLSignals.emitEvent(triggers=[GLNotifier.GLALLPEAKS, GLNotifier.GLALLINTEGRALS, GLNotifier.GLALLMULTIPLETS])

    def _okClicked(self):
        """
        When ok button pressed: delete and exit
        """
        # get the list of checked items - do first to stop threading issue?
        itms = set()
        for delItem in self._items:
            if delItem.checkBox.isChecked():
                itms |= set(delItem.values)

        with handleDialogApply(self):

            # add item here to redraw items
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=self._refreshGLItems)

            # delete the items
            self.project.deleteObjects(*list(itms))

            # add item here to redraw items
            with undoStackBlocking() as addUndoItem:
                addUndoItem(redo=self._refreshGLItems)

            # redraw the items
            self._refreshGLItems()

        self.accept()
