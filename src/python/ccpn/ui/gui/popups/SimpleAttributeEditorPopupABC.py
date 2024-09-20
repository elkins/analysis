"""
Abstract base class to easily implement a popup to edit attributes of V3 layer objects
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
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from functools import partial
from ccpn.ui.gui.lib.ChangeStateHandler import changeState
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget, _verifyPopupApply
from ccpn.core.lib.ContextManagers import queueStateChange
from ccpn.ui.gui.popups.AttributeEditorPopupABC import getAttributeTipText
from ccpn.util.Common import stringToCamelCase


class SimpleAttributeEditorPopupABC(CcpnDialogMainWidget):
    """
    Abstract base class to implement a popup for editing simple properties
    """
    klass = None  # The class whose properties are edited/displayed
    attributes = []  # A list of (attributeName, getFunction, setFunction, kwds) tuples;

    # get/set-Function have getattr, setattr profile
    # if setFunction is None: display attribute value without option to change value
    # kwds: optional kwds passed to LineEdit constructor

    hWidth = None
    FIXEDWIDTH = True
    FIXEDHEIGHT = True

    def __init__(self, parent=None, mainWindow=None, obj=None, size=None, **kwds):
        """
        Initialise the widget
        """
        super().__init__(parent, setLayout=True,
                         windowTitle='Edit ' + self.klass.className, size=size, **kwds)

        self.mainWindow = mainWindow
        self.application = mainWindow.application
        self.project = mainWindow.application.project
        self.current = mainWindow.application.current

        self.obj = obj

        row = 0
        self.labels = {}  # An (attributeName, Label-widget) dict
        self.edits = {}  # An (attributeName, LineEdit-widget) dict

        for _label, getFunction, setFunction, kwds in self.attributes:
            # value = getFunction(self.obj, attr)
            attr = stringToCamelCase(_label)

            editable = setFunction is not None
            self.labels[attr] = Label(self.mainWidget, _label, grid=(row, 0))
            self.edits[attr] = LineEdit(self.mainWidget, textAlignment='left', editable=editable,
                                        vAlign='t', grid=(row, 1), **kwds)
            self.edits[attr].textChanged.connect(partial(self._queueSetValue, attr, getFunction, setFunction, row))
            if self.hWidth:
                self.labels[attr].setFixedWidth(self.hWidth)

            tipText = getAttributeTipText(self.klass, attr)
            self.labels[attr].setToolTip(tipText)

            row += 1

        # set up the required buttons for the dialog
        self.setOkButton(callback=self._okClicked, enabled=False)
        self.setCancelButton(callback=self._cancelClicked)
        self.setHelpButton(callback=self._helpClicked, enabled=False)
        if self.EDITMODE:
            self.setRevertButton(callback=self._revertClicked, enabled=False)
        self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

        # populate the widgets
        self._populate()

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self._okButton = self.dialogButtons.button(self.OKBUTTON)
        self._cancelButton = self.dialogButtons.button(self.CANCELBUTTON)
        self._helpButton = self.dialogButtons.button(self.HELPBUTTON)
        self._revertButton = self.dialogButtons.button(self.RESETBUTTON)

    def _populate(self):
        """Populate the widgets while blocking the queue changes dict
        """
        self._changes.clear()
        with self._changes.blockChanges():
            for _label, getFunction, _, _ in self.attributes:
                attr = stringToCamelCase(_label)

                if getFunction and attr in self.edits:
                    value = getFunction(self.obj, attr)
                    self.edits[attr].setText(str(value) if value is not None else '')

    def _getChangeState(self):
        """Get the change state from the _changes dict
        """
        if not self._changes.enabled:
            return None

        applyState = True
        revertState = False
        allChanges = True if self._changes else False

        return changeState(self, allChanges, applyState, revertState, self._okButton, None, self._revertButton, self._currentNumApplies)

    @queueStateChange(_verifyPopupApply)
    def _queueSetValue(self, attr, getFunction, setFunction, dim, _value):
        """Queue the function for setting the attribute in the calling object
        """
        value = self.edits[attr].text()
        oldValue = str(getFunction(self.obj, attr))
        if value != oldValue:
            return partial(self._setValue, attr, setFunction, value)

    def _setValue(self, attr, setFunction, value):
        """Function for setting the attribute, called by _applyAllChanges
        """
        setFunction(self.obj, attr, value)

    def _refreshGLItems(self):
        """emit a signal to rebuild any required GL items
        Not required here
        """
        pass
