"""
Module Documentation Here
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
__dateModified__ = "$dateModified: 2024-04-18 17:29:10 +0100 (Thu, April 18, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:40 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtWidgets
from subprocess import PIPE, Popen, CalledProcessError
import contextlib
import html
from functools import partial

# don't remove this import!
import ccpn.core
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.Font import getFontHeight
from ccpn.ui.gui.lib.DynamicSizeAdjust import dynamicSizeAdjust
from ccpn.util.Update import UpdateAgent, FAIL_UNEXPECTED
from ccpn.util.Common import isWindowsOS
from ccpn.framework.Version import applicationVersion, VersionString, _lastApplicationVersion
from ccpn.framework.PathsAndUrls import ccpnBinPath, ccpnBatchPath


REFRESHBUTTONTEXT = 'Refresh Updates Information'
DOWNLOADBUTTONTEXT = 'Download/Install Updates'
UPDATELICENCEKEYTEXT = 'Update LicenceKey'
CLOSEEXITBUTTONTEXT = 'Close and Exit'

_rTexts = [(' ', '&nbsp;'),
           ('\t', '&nbsp;&nbsp;&nbsp;&nbsp;'),
           ]


class _Worker(QtCore.QThread):
    """Worker to read from OS process and write to text-box.
    """
    logout = QtCore.pyqtSignal(str, object)

    def __init__(self, process, outLog):
        super().__init__(None)
        self._procstd = process
        self._outLog = outLog

    def run(self):
        # thread to read output from process
        for line in self._procstd:
            # emit signal to send message to the textBox, must be on main thread
            self.logout.emit(line, self._outLog)


#=========================================================================================
# UpdatePopup
#=========================================================================================

class UpdatePopup(CcpnDialogMainWidget):
    FIXEDWIDTH = True
    FIXEDHEIGHT = False

    def __init__(self, parent=None, mainWindow=None, title='Update CCPN code', **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        # keep focus on this window
        self.setModal(True)
        self._initialised = False

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.preferences = mainWindow.application.preferences
        else:
            self.application = self.project = self.preferences = None

        version = applicationVersion
        self._updatePopupAgent = UpdateAgent(version, dryRun=False,
                                             showInfo=self._showInfo, showError=self._showError,
                                             )
        self.setWindowTitle(title)
        self._setWidgets()

        # initialise the popup
        self._updatesInstalled = False
        self._updateCount = 0
        self._updateVersion = None
        self._lastMsgWasError = None
        self._showBoxes = False

        self._threads = []
        self._process = None
        self._threadCount = 0

        self._resetButton = self.buttonList.buttons[0]
        self._downloadButton = self.buttonList.buttons[1]
        self._closeButton = self.buttonList.buttons[2]
        self._updateButton.setEnabled(self._updatePopupAgent._check())
        self._downloadButton.setEnabled(self._updateCount > 0)

        # initialise the buttons and dialog size
        self.setDefaultButton(None)

    def _postInit(self):
        super()._postInit()

        self._defaultHeight = self.minimumSizeHint().height()
        self.resetFromServer()
        self._downloadButton.setEnabled(self._updateCount > 0)

        # set the popup constraints
        QtCore.QTimer().singleShot(0, self._finalise)
        self._lock = QtCore.QMutex()

    def _finalise(self):
        """Set the minimum/maximum height of the popup based on which text-boxes are visible.
        """
        if self._showBoxes:
            self.setMaximumHeight(self._defaultHeight * 5)
            self.setMinimumHeight(self.minimumSizeHint().height())
        else:
            self.setFixedHeight(self.minimumSizeHint().height())

        self._initialised = True

    def _setWidgets(self):
        """Set the widgets.
        """
        row = 0
        # label = Label(self, 'Server location:', grid=(row, 0))
        # label = Label(self, self.server, grid=(row, 1))
        # row += 1
        # align all widgets to the top
        self.mainWidget.getLayout().setAlignment(QtCore.Qt.AlignTop)
        Label(self.mainWidget, 'Installation location:', grid=(row, 0), gridSpan=(1, 2))
        Label(self.mainWidget, text=self._updatePopupAgent.installLocation, grid=(row, 2))
        row += 1
        Label(self.mainWidget, 'Version:', grid=(row, 0), gridSpan=(1, 2))
        self.versionLabel = Label(self.mainWidget, text='TBD', grid=(row, 2))
        row += 1
        Label(self.mainWidget, 'Updates available:', grid=(row, 0), gridSpan=(1, 2))
        self.updatesLabel = Label(self.mainWidget, text='TBD', grid=(row, 2))
        row += 1
        Label(self.mainWidget, 'Installing updates will require a restart of the program.', grid=(row, 0), gridSpan=(1, 3))
        row += 1
        self._updateButton = Button(self.mainWidget, text=UPDATELICENCEKEYTEXT, tipText='Update LicenceKey from the server',
                                    callback=self._doUpdate, icon='icons/Filetype-Docs-icon.png', grid=(row, 0))
        row += 1
        texts = (REFRESHBUTTONTEXT, DOWNLOADBUTTONTEXT, self.CLOSEBUTTONTEXT)
        callbacks = (self._resetClicked, self._install, self._accept)
        tipTexts = ('Refresh the updates information by querying server and comparing with what is installed locally',
                    'Install the updates from the server',
                    'Close update dialog')
        icons = ('icons/redo.png', 'icons/dialog-apply.png', 'icons/window-close.png')
        self.buttonList = ButtonList(self.mainWidget, texts=texts, tipTexts=tipTexts, callbacks=callbacks, icons=icons, grid=(row, 0), gridSpan=(1, 3),
                                     setMinimumWidth=False)
        # set some padding for the buttons
        self.fontHeight = getFontHeight()
        # _style = f'QPushButton {{padding-left: {self.fontHeight}px; padding-right: {self.fontHeight}px; padding-top: 1px; padding-bottom: 1px;}}'
        # for button in self.buttonList.buttons:
        #     button.setStyleSheet(_style)
        # self._updateButton.setStyleSheet(_style)
        row += 1
        if self.preferences:
            CheckBoxCompoundWidget(self.mainWidget,
                                   grid=(row, 0), hAlign='left', gridSpan=(1, 3),
                                   # fixedWidths=(None, 30),
                                   orientation='right',
                                   labelText='Check for updates at startup',
                                   checked=self.preferences.general.checkUpdatesAtStartup,
                                   callback=self._checkAtStartupCallback)
            row += 1

        # why does this not resize correctly in self.mainWidget?
        self.changeLogBox = TextEditor(self.mainWidget, grid=(row, 0), gridSpan=(1, 3),
                                       enableWebLinks=True)  # don't set valign here
        self.changeLogBox.setVisible(False)
        self.changeLogBox.setEnabled(True)
        self.changeLogBox.setReadOnly(True)
        row += 1

        # why does this not resize correctly in self.mainWidget?
        self.infoBox = TextEditor(self.mainWidget, grid=(row, 0), gridSpan=(1, 3))  # don't set valign here
        self.infoBox.setVisible(False)
        self.infoBox.setEnabled(True)
        self.infoBox.setReadOnly(True)

        # why???
        self.mainWidget.setMaximumSize(QtCore.QSize(3000, 3000))

    def _resetClicked(self):
        """Reset button clicked,update the count and reset the download button
        """
        self.resetFromServer()
        self._downloadButton.setEnabled(self._updateCount > 0)

    def _install(self):
        """The update button has been clicked. Install updates and flag that files have been changed
        """
        self._showInfoBox()
        self._handleUpdates()

    def _handleUpdates(self):
        """Call external script to perform update, may require several iterations.
        """
        # temporarily disable buttons until end of process
        for btn in self.buttonList.buttons:
            btn.setEnabled(False)

        cmd = [ccpnBatchPath / 'update.bat'] if isWindowsOS() else [ccpnBinPath / 'update']
        self._process = Popen(cmd, stdout=PIPE, stderr=PIPE,
                              text=True, bufsize=1, universal_newlines=True)

        # create threads to handle stdout/err from the OS process
        self._threads = []
        for proc, log in ((self._process.stdout, self._showInfo),
                          (self._process.stderr, self._showError)):
            thr = _Worker(proc, log)
            self._threads.append(thr)
            thr.logout.connect(self._threadOut)
            thr.finished.connect(self._threadFinish)

        self._threadCount = len(self._threads)
        for thr in self._threads:
            thr.start()
        # now wait for the threads to finish...

    @staticmethod
    def _threadOut(line, log):
        """Write line to the textBox.
        This must be on the main thread to safely print to the textbox.
        """
        log(line)

    def _threadFinish(self):
        """Handle processing the finished threads.
        """
        self._threadCount -= 1
        if self._threadCount > 0:
            return

        # Finish handling the update process.
        try:
            exitCode = self._process.wait()
            if exitCode >= FAIL_UNEXPECTED:
                CalledProcessError(exitCode, self._process.args)
        except Exception:
            exitCode = -1

        self._updatesInstalled = True

        # release the fixed-width so the popup can resize
        self.setFixedSize(QtWidgets.QWIDGETSIZE_MAX, QtWidgets.QWIDGETSIZE_MAX)
        self._closeButton.setText(CLOSEEXITBUTTONTEXT)
        self._updateButton.setEnabled(self._updatePopupAgent._check())
        self._resetButton.setEnabled(True)
        self._downloadButton.setEnabled(bool(exitCode != 0))
        self._closeButton.setEnabled(True)

        self.resetFromServer()

    def _closeProgram(self):
        """Call the mainWindow close function giving user option to save, then close program
        """
        if self._threadCount:
            for thr in self._threads:
                thr.terminate()

        self.accept()

    def _accept(self):
        """Close button has been clicked, close if files have been updated or close dialog
        """
        if self._updatesInstalled:
            self._closeProgram()
        else:
            self.accept()

    def _doUpdate(self):
        self._updatePopupAgent._resetMd5()
        self._updateButton.setEnabled(False)

    def reject(self):
        """Dialog-frame close button has been clicked, close if files have been updated or close dialog
        """
        if self._updatesInstalled:
            self._closeProgram()
        else:
            super(UpdatePopup, self).reject()

    @staticmethod
    def _runProcess(command, text=False, shell=False):
        """Run a system process and return any stdout/stderr.
        """
        if not isinstance(command, list) and all(isinstance(val, str) for val in command):
            raise TypeError(f'Invalid command structure - {command}')

        query = Popen(command, stdout=PIPE, stderr=PIPE, text=text,
                      bufsize=1, universal_newlines=True)
        status, error = query.communicate()
        if query.poll() == 0:
            with contextlib.suppress(Exception):
                return status

    def resetFromServer(self):
        """Get current number of updates from the server
        """
        count = 0
        version = '-'
        cmd = [ccpnBatchPath / 'update.bat', '--count', '--version'] if isWindowsOS() else \
            [ccpnBinPath / 'update', '--count', '--version']
        if (response := self._runProcess(cmd, text=True, shell=False)) is not None:
            with contextlib.suppress(Exception):
                _countVer = [val.strip() for val in response.split(',')]
                count = int(_countVer[0])
                version = VersionString(_countVer[1])

        self._updateCount = count
        self.updatesLabel.set(f'{"yes" if count else "-"}')
        self.versionLabel.set(f'{version}')

        self._updatePopupAgent.resetFromServer()
        self._updateChangeLog()

        self._resizeWidget()

    def _updateChangeLog(self):
        """Read the current change-log and print the required mesages.
        """
        from datetime import datetime

        timeformat = '%Y-%m-%d %H:%M'

        changeLog = self._updatePopupAgent.fetchChangeLog()

        if changeLog and (records := changeLog.get("records", {})):
            clb = ''
            timeformat = '%Y-%m-%d %H:%M'

            for version, rec in reversed(sorted(records.items(), key=lambda dd: VersionString(dd[0]))):
                # make a simple header for each update section
                if not(applicationVersion <= VersionString(version) <= _lastApplicationVersion):
                    # skip updates that are too old
                    continue

                # check that timestamp is defined correctly
                heading = [version]
                if (ts := rec.get("timestamp", 0)):
                    tt = datetime.utcfromtimestamp(float(ts)).strftime(timeformat)
                    heading.append(tt)

                clb += f'<h3>Changes in version {": ".join(heading)} (utc)</h3>'
                # print the explicit html-string - need to watch quotes, need leading backslash
                clb += rec.get('info', '')

            if clb:
                self.changeLogBox.setHtml(clb)
                self._showChangeLogBox()

    def closeEvent(self, event) -> None:
        self.reject()

    def _showInfoBox(self):
        self._showBoxes = True
        if not self.infoBox.isVisible():
            self.resize(self.width(), self.height() + (self.fontHeight * 12))
            self.infoBox.show()
            self._resizeWidget()

    def _showChangeLogBox(self):
        self._showBoxes = True
        if not self.changeLogBox.isVisible():
            self.resize(self.width(), self.height() + (self.fontHeight * 12))
            self.changeLogBox.show()
            self._resizeWidget()

    def _showInfo(self, *args):
        """Add text to the html-box in default colour or green if the last message was an error.
        """
        with QtCore.QMutexLocker(self._lock):
            # need to check the default theme colour
            col = '#20d040' if self._lastMsgWasError else 'solid'  # green or default
            self._lastMsgWasError = False
            self._addMessage(args, col)

    def _showError(self, *args):
        """Add text to the html-box in red.
        """
        with QtCore.QMutexLocker(self._lock):
            col = '#ff1008'  # red
            self._lastMsgWasError = True
            self._addMessage(args, col)

    def _addMessage(self, args, col):
        self._showInfoBox()
        for arg in args:
            if arg:
                # make the text html-safe
                arg = html.escape(arg)
                for rr in _rTexts:
                    arg = arg.replace(*rr)
                txt = f'<span style="color:{col};" >{arg}</span>'
                self.infoBox.append(txt)

    def _resizeWidget(self):
        """change the width to the selected tab
        """
        QtCore.QTimer().singleShot(0, self._finalise)
        if self._initialised:
            # create a single-shot - waits until gui is up-to-date before firing first iteration of size-adjust
            QtCore.QTimer().singleShot(0, partial(dynamicSizeAdjust, self, sizeFunction=self._targetSize,
                                                  adjustWidth=True, adjustHeight=True))

    def _targetSize(self) -> tuple | None:
        """Get the size of the widget to match the popup to.

        Returns the size of mainWidget, or None if there is an error.
        Size is modified by visibility of text-boxes.
        None will terminate the iteration.

        :return: size of target widget, or None.
        """
        try:
            hh = 0 + (200 if self.changeLogBox.isVisible() else 0) + (200 if self.infoBox.isVisible() else 0)
            # get the size of mainWidget
            targetSize = self.minimumSizeHint() + QtCore.QSize(0, hh)
            # match against the popup
            sourceSize = self.size()

            return targetSize, sourceSize

        except Exception:
            return None

    @staticmethod
    def _refreshQT():
        # force a refresh of the popup - makes the updating look a little cleaner
        # self.updateGeometry()
        QtWidgets.QApplication.processEvents()

    def _checkAtStartupCallback(self, value):
        if self.preferences:
            self.preferences.general.checkUpdatesAtStartup = value


#=========================================================================================
# main
#=========================================================================================

def main():
    # QApplication must be persistent until end of main
    qtApp = QtWidgets.QApplication(['Update'])

    QtCore.QCoreApplication.setApplicationName('Update')
    QtCore.QCoreApplication.setApplicationVersion('3.2.0')

    # patch for icon sizes in menus, etc.
    styles = QtWidgets.QStyleFactory()
    qtApp.setStyle(styles.create('fusion'))

    popup = UpdatePopup()
    popup.exec_()


if __name__ == '__main__':
    main()
