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
__dateModified__ = "$dateModified: 2025-04-23 14:49:29 +0100 (Wed, April 23, 2025) $"
__version__ = "$Revision: 3.2.12 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
from PyQt5 import QtCore, QtGui
from functools import partial
import re

from ccpnmodel.ccpncore.memops.metamodel import Util as metaUtil
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.Entry import Entry
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Label import Label
from ccpn.framework.PathsAndUrls import ccpnUrl
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.util import Register


licenseUrl = ccpnUrl + '/license'
validEmailRegex = re.compile(r'^[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-_]+\.)+[A-Za-z]{2,63}$')


class RegisterPopup(CcpnDialogMainWidget):
    def __init__(self, parent=None, trial: int = 0, version='3', title='Register with CCPN',
                 modal=False, **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        self.version = version
        self.trial = trial

        if modal:  # Set before visible
            modality = QtCore.Qt.ApplicationModal
            self.setWindowModality(modality)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 350)

        self._setWidgets()

        txt = 'Later (%s day(s) left)' % self.trial
        # enable the buttons
        self.setOkButton(text='Register', callback=self._register)
        self.setCancelButton(text=txt, callback=self.reject)
        self.setDefaultButton(self.CANCELBUTTON)

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self.laterButton = self.getButton(self.CANCELBUTTON)
        self.laterButton.setEnabled(False)
        self.registerButton = self.getButton(self.OKBUTTON)
        self.registerButton.setEnabled(False)

    def _setWidgets(self, msg=None):
        frame = Frame(self, setLayout=True, grid=(0, 0))
        message = msg or '''To keep track of our users, which is important for grant applications,
we would like you to register your contact details with us.
This needs to be done once on every computer you use the programme on.
'''
        Label(frame, message, grid=(0, 0), gridSpan=(1, 2))
        row = 1
        self.entries = []
        self.validateEntries = []
        registrationDict = Register.loadDict()
        for attr in Register.userAttributes:
            Label(frame, metaUtil.upperFirst(attr), grid=(row, 0))
            text = registrationDict.get(attr, '')
            entry = Entry(frame, text=text, grid=(row, 1), maxLength=60)
            self.entries.append(entry)

            if 'email' in attr:
                currentBaseColour = entry.palette().color(QtGui.QPalette.Base)
                entry.textChanged.connect(partial(self._checkEmailValid, entry, currentBaseColour))
                self.validateEntries.append(entry)
            row += 1
        from ccpn.util import Data

        Label(frame, 'Build For:', grid=(row, 0))
        text = getattr(Data, ''.join([c for c in map(chr, (98, 117, 105, 108, 100, 70, 111, 114))]), '')
        entry = Entry(frame, text=text, grid=(row, 1), maxLength=60)
        entry.setEnabled(False)
        row += 1
        licenseFrame = Frame(frame, setLayout=True, grid=(row, 0), gridSpan=(1, 2))
        row += 1
        self.licenseCheckBox = CheckBox(licenseFrame,
                                        text='I have read and agree to the terms and conditions of the licence',
                                        callback=self._toggledCheckBox, grid=(0, 0))
        self.licenseCheckBox.setChecked(False)
        Button(licenseFrame, text='Show Licence', callback=self._showLicense, grid=(0, 1))

    @staticmethod
    def _checkEmailValid(entryBox, baseColour):
        palette = entryBox.palette()

        regIn = entryBox.text()
        validEmail = True if validEmailRegex.match(regIn) else False
        if validEmail:
            palette.setColor(QtGui.QPalette.Base, baseColour)
        else:
            palette.setColor(QtGui.QPalette.Base, QtGui.QColor('lightpink'))

        entryBox.setPalette(palette)

    def _toggledCheckBox(self):
        self.registerButton.setEnabled(self.licenseCheckBox.isChecked())
        self.laterButton.setEnabled(False if self.trial < 1 else self.licenseCheckBox.isChecked())

    @staticmethod
    def _showLicense():
        from ccpn.framework.Application import getApplication

        if not (app := getApplication()):
            sys.stderr.write('No application found\n')
            return

        app._showLicense()

    def _register(self):

        allValid = all([True if validEmailRegex.match(entry.text()) else False for entry in self.validateEntries])

        if allValid:
            from ccpn.framework.PathsAndUrls import licensePath
            from ccpn.util.Update import calcHashCode, TERMSANDCONDITIONS

            registrationDict = {}
            for n, attr in enumerate(Register.userAttributes):
                entry = self.entries[n]
                registrationDict[attr] = entry.get() or ''

            currentHashCode = calcHashCode(licensePath)
            registrationDict[TERMSANDCONDITIONS] = currentHashCode

            Register.setHashCode(registrationDict)
            Register.saveDict(registrationDict)
            Register.updateServer(registrationDict, self.version)

            if self.isModal():
                self.close()
        else:
            showWarning('', 'Please check all entries are valid')


#=========================================================================================
# NewTermsConditionsPopup
#=========================================================================================

class NewTermsConditionsPopup(RegisterPopup):
    def __init__(self, parent=None, trial: int = 0, version='3', title='Agree to Terms and Conditions',
                 modal=False, **kwds):
        # tweak the dialog title
        super().__init__(parent, trial=trial, version=version, title=title, modal=modal, **kwds)

    def _setWidgets(self, msg=None):
        # minor change to the dialog information
        message = msg or '''The terms and conditions of the licence have been amended.
Please read and accept to continue using the software.
'''
        super()._setWidgets(message)

        # disable all the entries
        for entry in self.entries:
            entry.setEnabled(False)

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        # tweak the ok-button text
        self.registerButton.setText('Accept Amendments')

    def _register(self):

        allValid = all([True if validEmailRegex.match(entry.text()) else False for entry in self.validateEntries])

        if allValid:
            from ccpn.framework.PathsAndUrls import licensePath
            from ccpn.util.Update import calcHashCode, TERMSANDCONDITIONS

            regDict = Register.loadDict()

            # write the updated md5
            currentHashCode = calcHashCode(licensePath)
            regDict[TERMSANDCONDITIONS] = currentHashCode
            Register.saveDict(regDict)

            if self.isModal():
                self.close()
        else:
            showWarning('', 'Please check all entries are valid')


def main():
    from ccpn.ui.gui.widgets.Application import TestApplication

    # need to keep a handle on the app otherwise gets instantly garbage-collected :|
    app = TestApplication()  # noqa

    popup = RegisterPopup()
    popup.exec_()
    popup = NewTermsConditionsPopup()
    popup.exec_()


if __name__ == '__main__':
    main()
