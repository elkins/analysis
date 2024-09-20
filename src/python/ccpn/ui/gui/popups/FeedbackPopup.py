"""Module Documentation here
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
__dateModified__ = "$dateModified: 2024-04-04 15:19:22 +0100 (Thu, April 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import random
from ccpn.framework.PathsAndUrls import ccpn2Url
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.widgets.Font import getFontHeight
from ccpn.util import Logging
from ccpn.util import Register
from ccpn.util import Url
from ccpn.util.Path import aPath
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget


LOG_FILE_TEXT = 'Log file'
PROJECT_DIR_TEXT = 'Project directory'
SCRIPT_URL = ccpn2Url + '/cgi-bin/feedback/submitFeedback.py'


# code below has to be synchronised with code in SCRIPT_URL

class FeedbackPopup(CcpnDialogMainWidget):
    # parent mandatory and that needs to have attribute application

    FIXEDHEIGHT = False
    FIXEDWIDTH = False

    def __init__(self, parent=None, title='Feedback Form', **kwds):

        raise RuntimeError('This Popup is deprecated. To submit a feedback, please visit the CcpnForum instead')

        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)
        self.setContentsMargins(5, 5, 5, 5)
        self._registrationDict = Register.loadDict()

        _height = getFontHeight()

        row = 0
        message = 'For bug reports please submit precise information, including any error message left on the console'
        label = Label(self.mainWidget, message, grid=(row, 0), gridSpan=(1, 2))

        for key in ('name', 'organisation', 'email'):
            row += 1
            Label(self.mainWidget, text='%s: ' % key.capitalize(), grid=(row, 0))
            Label(self.mainWidget, text=self._registrationDict.get(key), grid=(row, 1))

        row += 1
        label = Label(self.mainWidget, text='Include: ', grid=(row, 0))
        includeFrame = Frame(self.mainWidget, grid=(row, 1), setLayout=True)
        self.includeLogBox = CheckBox(includeFrame, text=LOG_FILE_TEXT, checked=True, grid=(0, 0))
        self.includeProjectBox = CheckBox(includeFrame, text=PROJECT_DIR_TEXT, checked=False, grid=(0, 1))

        row += 1
        label = Label(self.mainWidget, text='Feedback: ', grid=(row, 0), vAlign='t')
        self.textEditor = TextEditor(self.mainWidget, grid=(row, 1))
        self.textEditor.setMinimumHeight(_height * 4)

        # enable the buttons
        self.setOkButton(callback=self._submitFeedback, text='Submit', tipText='Submit feedback')
        self.setCloseButton(callback=self.reject, tipText='Close Popup')
        self.setDefaultButton(self.CLOSEBUTTON)

    def _submitFeedback(self):
        includeLog = self.includeLogBox.get()
        includeProject = self.includeProjectBox.get()
        feedback = self.textEditor.get().strip()

        if not feedback:
            return

        application = self.getParent().application

        if includeProject:
            fileName = application.project.makeArchive()

            # # cannot use tempfile because that always hands back open object and tarfile needs actual path
            # filePrefix = 'feedback%s' % random.randint(1, 10000000)
            # project = application.project
            # projectPath = aPath(project.path)
            # directory = projectPath.parent
            # filePrefix = directory / filePrefix
            #
            # fileName = project.packageProject(filePrefix, includeBackups=True, includeLogs=includeLog)

        elif includeLog:
            logger = Logging.getLogger()
            if not hasattr(logger, 'logPath'):
                return
            fileName = aPath(logger.logPath)
        else:
            fileName = None

        data = {}
        data['version'] = application.applicationVersion
        data['feedback'] = feedback

        for key in ('name', 'organisation', 'email'):
            data[key] = self._registrationDict.get(key, 'None')

        if fileName:
            try:
                response = Url.uploadFile(SCRIPT_URL, fileName, data)
            finally:
                if includeProject:
                    fileName.removeFile()
        else:
            try:
                response = Url.fetchUrl(SCRIPT_URL, data)
            except:
                response = []

        if 'Data successfully uploaded' in response:
            title = 'Success'
            msg = 'Feedback successfully submitted'
        else:
            title = 'Failure'
            msg = 'Problem submitting feedback'

        MessageDialog.showInfo(title, msg)
        self.accept()


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication


    _modal = True
    app = TestApplication()
    popup = FeedbackPopup()

    popup.show()

    if _modal:
        app.exec_()
    else:
        popup.raise_()
        app.start()
