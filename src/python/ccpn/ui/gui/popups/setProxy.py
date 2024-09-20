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
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2023-10-30 11:44:25 +0100 (Mon, October 30, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

from functools import partial

from ccpn.framework import Version
from ccpn.framework.Preferences import Preferences
from ccpn.core.lib.ContextManagers import queueStateChange
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit, PasswordEdit
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.popups.Dialog import _verifyPopupApply
from ccpn.ui.gui.lib.ChangeStateHandler import ChangeDict, changeState
from ccpn.util.UserPreferences import UserPreferences


LineEditsMinimumWidth = 195


def _makeLabel(parent, text, grid, **kwds) -> Label:
    """Convenience routine to make a Label with uniform settings
    :return Label instance
    """
    kwds.setdefault('hAlign', 'r')
    kwds.setdefault('margins', (0, 3, 10, 3))
    label = Label(parent, text=text, grid=grid, **kwds)
    return label


def _makeCheckBox(parent, row, text, callback, toolTip=None, **kwds):
    """Convenience routine to make a row with a label and a checkbox
    :return CheckBox instance
    """
    _label = _makeLabel(parent, text=text, grid=(row, 0), **kwds)
    _checkBox = CheckBox(parent, grid=(row, 1), hAlign='l', hPolicy='minimal', spacing=(0, 0))
    _checkBox.toggled.connect(callback)
    if toolTip is not None:
        _label.setToolTip(toolTip)
        _checkBox.setToolTip(toolTip)
    return _checkBox


#=========================================================================================
# _SetProxy
#=========================================================================================

class _SetProxy(CcpnDialogMainWidget):
    """Small dialog to edit the proxy settings of the preferences.
    """
    FIXEDHEIGHT = False
    FIXEDWIDTH = False

    def __init__(self, parent=None, mainWindow=None, title='Set Proxy-Preferences', **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, size=None, **kwds)

        self.mainWindow = mainWindow
        if self.mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
        else:
            self.application = None
            self.project = None
        self._changes = ChangeDict()

        self._setWidgets()

        # grab the class with the preferences methods
        self.preferences = Preferences(Version)
        self.preferences._getUserPreferences()

        # grab the class with the preferences methods to store unedited version
        self._userPreferences = UserPreferences(readPreferences=False)

        self._populate()

        # enable the buttons
        self.setOkButton(callback=self._okClicked)
        self.setCancelButton(callback=self._cancelClicked)
        self.setRevertButton(callback=self._revertClicked, enabled=False)
        self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

        # initialise the buttons and dialog size
    def _postInit(self):
        super()._postInit()

        self._okButton = self.getButton(self.OKBUTTON)
        self._revertButton = self.getButton(self.RESETBUTTON)

    def _setWidgets(self):
        """Set up the widgets for the dialog.
        """
        parent = self.mainWidget

        row = 0
        Label(parent, grid=(row, 0), text="Proxy Settings", gridSpan=(1, 2), bold=True)

        row += 1
        self.useProxyBox = _makeCheckBox(parent, row=row, text="Use proxy settings",
                                         callback=self._queueSetUseProxy)

        row += 1
        self.verifySSLBox = _makeCheckBox(parent, row=row, text="Verify SSL certificates",
                                          callback=self._queueSetVerifySSL)

        row += 1
        self.proxyAddressLabel = _makeLabel(parent, text="Proxy server", grid=(row, 0))
        self.proxyAddressData = LineEdit(parent, grid=(row, 1), hAlign='l')
        self.proxyAddressData.setMinimumWidth(LineEditsMinimumWidth)
        self.proxyAddressData.textEdited.connect(self._queueSetProxyAddress)

        row += 1
        self.proxyPortLabel = _makeLabel(parent, text="Port", grid=(row, 0))
        self.proxyPortData = LineEdit(parent, grid=(row, 1), hAlign='l')
        self.proxyPortData.setMinimumWidth(LineEditsMinimumWidth)
        self.proxyPortData.textEdited.connect(self._queueSetProxyPort)

        row += 1
        self.useProxyPasswordBox = _makeCheckBox(parent, row=row, text="Server requires password",
                                                 callback=self._queueSetUseProxyPassword)

        row += 1
        self.proxyUsernameLabel = _makeLabel(parent, text="Username", grid=(row, 0))
        self.proxyUsernameData = LineEdit(parent, grid=(row, 1), hAlign='l')
        self.proxyUsernameData.setMinimumWidth(LineEditsMinimumWidth)
        self.proxyUsernameData.textEdited.connect(self._queueSetProxyUsername)

        row += 1
        self.proxyPasswordLabel = _makeLabel(parent, text="Password", grid=(row, 0))
        self.proxyPasswordData = PasswordEdit(parent, grid=(row, 1), hAlign='l')
        self.proxyPasswordData.setMinimumWidth(LineEditsMinimumWidth)
        self.proxyPasswordData.textEdited.connect(self._queueSetProxyPassword)

    def _populate(self):
        # clear all changes
        self._changes.clear()

        with self._changes.blockChanges():
            self.verifySSLBox.setChecked(self.preferences.proxySettings.verifySSL)
            self.useProxyBox.setChecked(self.preferences.proxySettings.useProxy)
            self.proxyAddressData.setText(str(self.preferences.proxySettings.proxyAddress))
            self.proxyPortData.setText(str(self.preferences.proxySettings.proxyPort))
            self.useProxyPasswordBox.setChecked(self.preferences.proxySettings.useProxyPassword)
            self.proxyUsernameData.setText(str(self.preferences.proxySettings.proxyUsername))
            self.proxyPasswordData.setText(self._userPreferences.decodeValue(str(self.preferences.proxySettings.proxyPassword)))

            # set the enabled state of some settings boxes
            self._enableProxyButtons()

    def _getChangeState(self):
        """Get the change state from the _changes dict
        """
        if not self._changes.enabled:
            return None

        applyState = True
        revertState = False
        allChanges = True if self._changes else False

        return changeState(self, allChanges, applyState, revertState, self._okButton, None, self._revertButton, 0)

    def _applyChanges(self):
        """The apply button has been clicked.
        Return True unless any errors occurred.
        """
        if not bool(self._changes):
            return True

        try:
            # apply all changes - only to self.preferences
            self._applyAllChanges(self._changes)

        except Exception:
            # re-populate popup from self.preferences on error
            self._populate()
            return False

        else:
            # save the preferences
            self.preferences._saveUserPreferences()
            return True

    #=========================================================================================
    # handle popup callbacks
    #=========================================================================================

    @queueStateChange(_verifyPopupApply)
    def _queueSetVerifySSL(self, _value):
        value = self.verifySSLBox.get()
        if value != self.preferences.proxySettings.verifySSL:
            return partial(self._setVerifySSL, value)

    def _setVerifySSL(self, value):
        self.preferences.proxySettings.verifySSL = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetUseProxy(self, _value):
        value = self.useProxyBox.get()
        # set the state of the other buttons
        self._enableProxyButtons()
        if value != self.preferences.proxySettings.useProxy:
            return partial(self._setUseProxy, value)

    def _setUseProxy(self, value):
        self.preferences.proxySettings.useProxy = value

    @queueStateChange(_verifyPopupApply)
    def _queueUseSystemProxy(self):
        value = self.useSystemProxyBox.get()
        # set the state of the other buttons
        self._enableProxyButtons()
        if value != self.preferences.proxySettings.useSystemProxy:
            return partial(self._setUseSystemProxy, value)

    def _setUseSystemProxy(self, value):
        self.preferences.proxySettings.useSystemProxy = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetProxyAddress(self, _value):
        value = self.proxyAddressData.get()
        if value != self.preferences.proxySettings.proxyAddress:
            return partial(self._setProxyAddress, value)

    def _setProxyAddress(self, value):
        self.preferences.proxySettings.proxyAddress = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetProxyPort(self, _value):
        value = self.proxyPortData.get()
        if value != self.preferences.proxySettings.proxyPort:
            return partial(self._setProxyPort, value)

    def _setProxyPort(self, value):
        self.preferences.proxySettings.proxyPort = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetUseProxyPassword(self, _value):
        value = self.useProxyPasswordBox.get()
        # set the state of the other buttons
        self._enableProxyButtons()
        if value != self.preferences.proxySettings.useProxyPassword:
            return partial(self._setUseProxyPassword, value)

    def _setUseProxyPassword(self, value):
        self.preferences.proxySettings.useProxyPassword = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetProxyUsername(self, _value):
        value = self.proxyUsernameData.get()
        if value != self.preferences.proxySettings.proxyUsername:
            return partial(self._setProxyUsername, value)

    def _setProxyUsername(self, value):
        self.preferences.proxySettings.proxyUsername = value

    @queueStateChange(_verifyPopupApply)
    def _queueSetProxyPassword(self, _value):
        value = self._userPreferences.encodeValue(str(self.proxyPasswordData.get()))
        if value != self.preferences.proxySettings.proxyPassword:
            return partial(self._setProxyPassword, value)

    def _setProxyPassword(self, value):
        self.preferences.proxySettings.proxyPassword = value

    def _enableProxyButtons(self):
        """Enable/disable proxy widgets based on check boxes
        """
        usePW = self.useProxyPasswordBox.get()
        useProxy = self.useProxyBox.get()

        self.proxyAddressData.enableWidget(useProxy)
        self.proxyPortData.enableWidget(useProxy)
        self.useProxyPasswordBox.enableWidget(useProxy)
        self.proxyUsernameData.enableWidget(useProxy and usePW)
        self.proxyPasswordData.enableWidget(useProxy and usePW)


#=========================================================================================
# main
#=========================================================================================

def main():
    """Make a default-application and show the proxy-popup.
    """
    from ccpn.framework.Version import applicationVersion
    from ccpn.ui.gui.widgets.Application import TestApplication

    app = TestApplication()
    app.setApplicationName('UpdateAdmin')
    app.setApplicationVersion(applicationVersion)

    popup = _SetProxy()
    popup.exec_()


if __name__ == '__main__':
    main()
