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
__author__ = "$Author: rhfogh $"
__date__ = "$Date: 2016-05-16 06:41:02 +0100 (Mon, 16 May 2016) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
import urllib
from ccpnmodel.ccpncore.memops.metamodel import Util as metaUtil
from ccpn.framework.PathsAndUrls import ccpn2Url
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.Entry import Entry
from ccpn.ui.gui.widgets.FileDialog import MacrosFileDialog
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.widgets.Font import getFontHeight
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.util import Register
from ccpn.util import Url


SCRIPT_URL = ccpn2Url + '/cgi-bin/macros/submitMacro.py'


# code below has to be synchronised with code in SCRIPT_URL

class SubmitMacroPopup(CcpnDialogMainWidget):

    FIXEDHEIGHT = False
    FIXEDWIDTH = False

    def __init__(self, parent=None, title='Submit Macro Form', **kwds):

        raise RuntimeError('This Popup is deprecated. To submit a macro, please visit the CcpnForum instead')

        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        self.setContentsMargins(5, 5, 5, 5)
        self._registrationDict = Register.loadDict()

        _height = getFontHeight()

        row = 0
        for key in ('name', 'organisation', 'email'):
            label = Label(self.mainWidget, text='%s: ' % metaUtil.upperFirst(key), grid=(row, 0))
            label = Label(self.mainWidget, text=self._registrationDict.get(key), grid=(row, 1))
            row += 1

        button = Button(self.mainWidget, 'Macro path:', callback=self._selectMacro, grid=(row, 0))
        self.pathEntry = Entry(self.mainWidget, maxLength=200, grid=(row, 1))
        row += 1

        label = Label(self.mainWidget, text='Keywords: ', grid=(row, 0), vAlign='t')
        self.keywordsEntry = Entry(self.mainWidget, grid=(row, 1))
        row += 1

        label = Label(self.mainWidget, text='Description: ', grid=(row, 0), vAlign='t')
        self.textEditor = TextEditor(self.mainWidget, grid=(row, 1))
        self.textEditor.setMinimumHeight(_height * 4)

        # enable the buttons
        self.setOkButton(callback=self._submitMacro, text='Submit', tipText='Submit Macro')
        self.setCloseButton(callback=self.reject, tipText='Close Popup')
        self.setDefaultButton(self.CLOSEBUTTON)

    def _selectMacro(self):

        parent = self.getParent()
        dialog = MacrosFileDialog(parent=parent, acceptMode='select')
        dialog._show()
        path = dialog.selectedFile()
        if path:
            self.pathEntry.set(path)

    def _submitMacro(self):

        application = self.getParent().application
        logger = application.project._logger

        filePath = self.pathEntry.get()
        if not filePath or not os.path.exists(filePath) or not os.path.isfile(filePath):
            dialog = MessageDialog.showError('Error',
                                             'Path does not exist or is not file')
            logger.error('Path specified for macro does not exist or is not file: %s' % filePath)
            return

        keywords = self.keywordsEntry.get()
        description = self.textEditor.get()

        if not keywords or not description:
            dialog = MessageDialog.showError('Error',
                                             'Both keywords and description required')
            logger.error('Both keywords and description required for macro')
            return

        keywords = keywords.strip()
        description = description.strip()

        data = {}
        data['version'] = application.applicationVersion
        data['keywords'] = keywords
        data['description'] = description

        for key in ('name', 'organisation', 'email'):
            data[key] = self._registrationDict.get(key, 'None')

        try:
            response = Url.uploadFile(SCRIPT_URL, filePath, data)
        except urllib.error.HTTPError as e:
            response = str(e)

        if response and 'Macro successfully uploaded' in response:
            title = 'Success'
            msg = loggerMsg = 'Macro successfully submitted'
        else:
            title = 'Failure'
            msg = 'Problem submitting macro, see log for details'
            loggerMsg = 'Problem submitting macro: %s' % response

        logger.info(loggerMsg)
        info = MessageDialog.showInfo(title, msg)

        self.hide()


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication


    app = TestApplication()
    popup = SubmitMacroPopup()

    popup.show()
    popup.raise_()

    app.start()
