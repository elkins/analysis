"""
This file contains the routines for message dialogues
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
__dateModified__ = "$dateModified: 2024-10-11 18:50:23 +0100 (Fri, October 11, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import textwrap
import math
import sys
import re
from contextlib import suppress
from functools import partial
from dataclasses import dataclass
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QEvent, pyqtSlot
from ccpn.ui.gui.widgets.Font import setWidgetFont
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.guiSettings import getColours
from ccpn.util.Logging import getLogger


def _isDarwin():
    return 'darwin' in QtCore.QSysInfo().kernelType().lower()


Ok = QtWidgets.QMessageBox.Ok
Cancel = QtWidgets.QMessageBox.Cancel
Yes = QtWidgets.QMessageBox.Yes
No = QtWidgets.QMessageBox.No
Retry = QtWidgets.QMessageBox.Retry
Ignore = QtWidgets.QMessageBox.Ignore
Abort = QtWidgets.QMessageBox.Abort
Close = QtWidgets.QMessageBox.Close
Information = QtWidgets.QMessageBox.Information
Warning = QtWidgets.QMessageBox.Warning
Question = QtWidgets.QMessageBox.Question
Critical = QtWidgets.QMessageBox.Critical
Save = QtWidgets.QMessageBox.Save
Discard = QtWidgets.QMessageBox.Discard

default_icons = (Information, Question, Warning, Critical)

if _isDarwin():
    Question = Warning

LINELENGTH = 100
WRAPBORDER = 5
WRAPSCALE = 1.05
_STARTMAXWIDTH = 50

_DONTSHOWMESSAGE = "Don't show this again"
_DONTSHOWPOPUP = 'dontShowPopup'
_POPUPS = 'popups'


def _wrapString(text, lineLength=LINELENGTH):
    """Wrap a line of text to the desired width of the dialog
    Returns list of individual lines and the concatenated string for dialog
    """
    newWrapped = []
    splt = '<br>' if '<br>' in text else '\n'
    _text = text.split(splt)
    for text in _text:
        wrapped = textwrap.wrap(text, width=lineLength, replace_whitespace=False, break_long_words=False)
        if not text:
            newWrapped.append('')
        for mm in wrapped:
            if len(mm) > LINELENGTH:
                for chPos in range(0, len(mm), lineLength):
                    newWrapped.append(mm[chPos:chPos + lineLength])
            else:
                newWrapped.append(mm)
    return newWrapped, splt.join(newWrapped)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# MessageDialog
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class MessageDialog(QtWidgets.QMessageBox):
    """
    Base class for all dialogues
    Using the 'multiline' to emulate the windowTitle, as on Mac the windows do not get their title
    """
    _dontShowEnabled = False
    _defaultResponse = None
    _popupId = None

    def __init__(self, title, basicText, message, icon=Information, iconPath=None, parent=None,
                 detailedText=None, dontShowEnabled=False, defaultResponse=None, popupId=None):
        super().__init__(parent=parent)

        # set modality to take control
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)
        self._parent = parent
        self.setWindowTitle(title)
        self._setWrappedText(basicText, message, detailedText)
        self._setFonts()
        self.setIcon(icon)
        if iconPath:
            image = QtGui.QPixmap(iconPath)
            scaledImage = image.scaled(48, 48, QtCore.Qt.KeepAspectRatio)
            self.setIconPixmap(scaledImage)
        if dontShowEnabled:
            if not popupId:
                raise RuntimeError(f'{self.__class__.__name__}.__init__: popupId is not specified')
            self._dontShowEnabled = dontShowEnabled
            self._defaultResponse = defaultResponse
            self._popupId = popupId
        self._setDontShow()

    def _setFonts(self):
        """Set the fonts for the message widgets.
        """
        # Adapted from the best solution so far from: http://apocalyptech.com/linux/qt/qmessagebox/
        # set the fonts for the labels (pushButtons are set later)
        widgets = self.findChildren((QtWidgets.QLabel, QtWidgets.QTextEdit))
        for widg in widgets:
            setWidgetFont(widg, )
        layout = self.layout()
        for (rr, cc) in ((0, 1), (0, 2)):
            # not sure whether it is column 1 or 2, but it might change?
            if (item := layout.itemAtPosition(rr, cc)) and (widg := item.widget()) and (widg in widgets):
                # change the header to bold-font
                setWidgetFont(widg, bold=True)

    def _setWrappedText(self, basicText, message, detailedText):
        """Split the text by \n and fix the width of the widgets.
        This does not currently work with richText.
        """
        basicTextWrap, basicText = _wrapString(basicText)
        messageWrap, message = _wrapString(message)
        self.setText(basicText)
        self.setInformativeText(message)
        if detailedText:
            # adds the 'Show Details...' button - style is not correct though
            self.setDetailedText(detailedText)
        layout = self.layout()
        maxTextWidth = _STARTMAXWIDTH
        widgetSet = set()
        for (rr, cc) in ((0, 1), (0, 2)):
            maxTextWidth = self._checkLineLength(cc, layout, maxTextWidth, basicTextWrap, rr, widgetSet)
        for (rr, cc) in ((1, 1), (1, 2)):
            maxTextWidth = self._checkLineLength(cc, layout, maxTextWidth, messageWrap, rr, widgetSet)
        for widg in widgetSet:
            widg.setFixedWidth(maxTextWidth)

    def _checkLineLength(self, cc, layout, maxTextWidth, msg, rr, widgetSet):
        if (item := layout.itemAtPosition(rr, cc)) and (widg := item.widget()):
            widgetSet.add(widg)
            # get the bounding rectangle for each line of basicText
            for wrapLine in msg:
                wrapLine = re.sub(r'^<a[^>]*>', '', wrapLine)  # remove the '<a..> tag
                tWidth = int((QtGui.QFontMetrics(self.font()).boundingRect(
                        wrapLine).width() + WRAPBORDER) * WRAPSCALE)
                maxTextWidth = max(maxTextWidth, tWidth)
        return maxTextWidth

    # def _setScrollWidget(self, scrollableMessage=False):
    #     """Move main message into scroll-area as required.
    #     """
    #     layout = self.layout()
    #     if scrollableMessage:  # and ((item := layout.itemAtPosition(1, 2)) and (widg := item.widget())):
    #         # insert the Label widgetMessage inside a scrollArea.
    #         # Could be done automatically if len(text) > someValue...
    #         scrollArea = QtWidgets.QScrollArea(self)
    #         scrollArea.setWidgetResizable(True)
    #         widg.setWordWrap(True)
    #         scrollArea.setWidget(widg)
    #         layout.addWidget(scrollArea, 1, 2)

    def _setDontShow(self):
        # put a Don't Show checkbox at the bottom of the dialog if needed
        if not self._dontShowEnabled:
            return
        try:
            from ccpn.framework.Application import getApplication

            # retrieve from preferences
            app = getApplication()
            popup = app.preferences.popups[self._popupId]
            state = bool(popup[_DONTSHOWPOPUP])
        except Exception:
            # any error should hide the checkbox
            self._dontShowCheckBox = None
            return
        layout = self.layout()
        # add a checkbox below the buttons - looks a little cleaner
        # - just use simple widgets for the minute to stop cyclic imports
        self._frame = _frame = Frame(self)
        innerLayout = QtWidgets.QHBoxLayout()
        _frame.setLayout(innerLayout)
        # set the background/fontSize for the tooltips, fraction slower but don't need to import the colour-names
        # _frame.setStyleSheet('QToolTip {{ background-color: {TOOLTIP_BACKGROUND}; '
        #                      'color: {TOOLTIP_FOREGROUND}; '
        #                      'font-size: {_size}pt ; }}'.format(_size=_frame.font().pointSize(), **getColours()))

        _msg = 'This popup can be enabled again from preferences->appearance'
        dsc = self._dontShowCheckBox = CheckBox(_frame, text=_DONTSHOWMESSAGE)
        dsc.setToolTip(_msg)
        dsc.setContentsMargins(0, 0, 0, 0)
        dsc.setChecked(state)
        innerLayout.addWidget(dsc, 0, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.accepted.connect(self._accept)
        self.rejected.connect(self._reject)

        _frame.setFixedSize(_frame.minimumSizeHint())
        hs = _frame.height() - layout.verticalSpacing() - self.contentsMargins().bottom() // 2

        _spacer = QtWidgets.QSpacerItem(0, max(1, hs), QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        layout.addItem(_spacer, layout.rowCount(), 0, 1, layout.columnCount())

        self._setStyle()

    def _getStandardIcon(self):
        # NOTE:ED - how to grab the standardIcons as pixmaps for our own message-widget
        icon = QtWidgets.QProxyStyle().standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
        pixmap = icon.pixmap(QtCore.QSize(48, 48))
        ll = QtWidgets.QLabel('Resizing')
        ll.setFixedSize(48, 48)
        self.layout().addWidget(ll, 0, 0)
        ll.setPixmap(pixmap)

    def _setStyle(self):
        _style = """QPushButton {
                    padding: 2px 5px 2px 5px;
                }
                QPushButton:focus {
                    padding: 0px;
                    border-color: palette(highlight);
                    border-style: solid;
                    border-width: 1px;
                    border-radius: 2px;
                }
                QPushButton:disabled {
                    color: palette(dark);
                    background-color: palette(midlight);
                }
                """
        self.setStyleSheet(_style)
        # check the other buttons in the dialog
        for button in self.buttons():
            button.setStyleSheet(_style)

    def event(self, event):
        """
        handler to make dialogs modal but at the sametime accept the correct keys for default actions
        """
        # accepted events apple-delete, apple-c apple-v, esc, return, spacebar, command period, apple-z apple-y,
        # apple-shift-z  apple-h, apple-option-h, control tab, tab, shift tab, arrow keys, contol arrow keys
        # control-shift-arrows, apple-a

        ACCEPTED_MODAL_KEYS = (
            (Qt.NoModifier, Qt.Key_Space,),
            (Qt.ControlModifier, Qt.Key_Delete),
            (Qt.ControlModifier, Qt.Key_Backspace),
            (Qt.ControlModifier, Qt.Key_C),
            (Qt.ControlModifier, Qt.Key_V),
            (Qt.NoModifier, Qt.Key_Escape,),
            (Qt.NoModifier, Qt.Key_Return,),
            (Qt.NoModifier, Qt.Key_Space,),
            (Qt.ControlModifier, Qt.Key_Period),
            (Qt.ControlModifier, Qt.Key_Z),
            (Qt.ControlModifier, Qt.Key_Y),
            (Qt.ControlModifier | Qt.ShiftModifier, Qt.Key_Z),
            (Qt.ControlModifier, Qt.Key_H),
            (Qt.ControlModifier | Qt.AltModifier, Qt.Key_H),
            (Qt.MetaModifier, Qt.Key_Tab),
            (Qt.NoModifier, Qt.Key_Tab,),
            (Qt.ShiftModifier, Qt.Key_Tab),
            (Qt.NoModifier, Qt.Key_Left,),
            (Qt.NoModifier, Qt.Key_Right,),
            (Qt.NoModifier, Qt.Key_Up,),
            (Qt.NoModifier, Qt.Key_Down,),
            (Qt.MetaModifier, Qt.Key_Left),
            (Qt.MetaModifier, Qt.Key_Right),
            (Qt.MetaModifier, Qt.Key_Up),
            (Qt.MetaModifier, Qt.Key_Down),
            (Qt.MetaModifier | Qt.ShiftModifier, Qt.Key_Left),
            (Qt.MetaModifier | Qt.ShiftModifier, Qt.Key_Right),
            (Qt.MetaModifier | Qt.ShiftModifier, Qt.Key_Up),
            (Qt.MetaModifier | Qt.ShiftModifier, Qt.Key_Down),
            (Qt.ControlModifier, Qt.Key_A)
            )

        result = False
        if event.type() == QEvent.ShortcutOverride:
            test = (event.modifiers(), event.key())
            if test in ACCEPTED_MODAL_KEYS:
                event.accept()
                result = True
        else:
            result = super(MessageDialog, self).event(event)
        return result

    def resizeEvent(self, ev):
        """
        required to set the initial position of the message box on the centre of the screen
        """
        # set the font of the push buttons, must be here after __init__ has completed
        for child in self.findChildren(QtWidgets.QPushButton):
            setWidgetFont(child, )
        # must be the first event outside the __init__ otherwise frameGeometries are not valid
        super(MessageDialog, self).resizeEvent(ev)
        if activeWindow := QtWidgets.QApplication.activeWindow():
            point = activeWindow.rect().center()
            global_point = activeWindow.mapToGlobal(point)
            self.move(global_point
                      - self.frameGeometry().center()
                      + self.frameGeometry().topLeft())
        if self._dontShowEnabled:
            with suppress(AttributeError):
                # strange error on the first paint of the widget
                self._frame.move(self.contentsMargins().left() // 2,
                                 self.geometry().height() - self._frame.height() - self.contentsMargins().bottom() // 2)

    def runFunc(self, func):
        QtCore.QTimer().singleShot(0, partial(self._runFunc, func))
        self.exec_()
        return self._funcResult

    def _runFunc(self, func):
        """Run the function and quit
        """
        self._funcResult = func()
        self.close()

    def dontShowPopup(self):
        """Check the exec state from the stored don't-show preferences
        """
        if self._dontShowEnabled:
            try:
                from ccpn.framework.Application import getApplication

                # store in preferences
                app = getApplication()
                popup = app.preferences.popups[self._popupId]
                state = popup[_DONTSHOWPOPUP]
            except Exception:
                state = False
            # what is the default response for this dialog?
            # needs to be defined/set in the subclass of __init__
            return state
        return False

    def _accept(self):
        # store the current state of the checkbox in preferences
        if self._dontShowEnabled:
            with suppress(Exception):
                from ccpn.framework.Application import getApplication

                # store in preferences
                if app := getApplication():
                    popups = app.preferences.setdefault(_POPUPS, {})
                    popup = popups.setdefault(self._popupId, {})
                    # should really get from a property rather than a widget
                    #  - if widget does not show then the initial state may not be set
                    popup[_DONTSHOWPOPUP] = self._dontShowCheckBox.isChecked()

    def _reject(self):
        # store False in preferences - popup still opens
        if self._dontShowEnabled:
            with suppress(Exception):
                from ccpn.framework.Application import getApplication

                # store in preferences
                if app := getApplication():
                    popups = app.preferences.setdefault(_POPUPS, {})
                    popup = popups.setdefault(self._popupId, {})
                    # should really get from a property rather than a widget
                    #  - if widget does not show then the initial state may not be set
                    popup[_DONTSHOWPOPUP] = False


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# MessageDialog subclasses
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def showInfo(title, message, parent=None, iconPath=None,
             dontShowEnabled=False, defaultResponse=None, popupId=None):
    """Display an info message
    """
    dialog = MessageDialog('Information', title, message, Information, iconPath, parent,
                           dontShowEnabled=dontShowEnabled, defaultResponse=defaultResponse, popupId=popupId)
    if dialog.dontShowPopup():
        getLogger().debug(f'Popup {popupId!r} skipped with response={defaultResponse}')
    else:
        dialog.setStandardButtons(Ok)
        dialog.exec_()


def showNotImplementedMessage():
    showInfo('Not implemented yet!',
             'This function has not been implemented in the current version')


def showOkCancel(title, message, parent=None, iconPath=None,
                 dontShowEnabled=False, defaultResponse=None, popupId=None):
    dialog = MessageDialog('Query', title, message, Question, iconPath, parent,
                           dontShowEnabled=dontShowEnabled, defaultResponse=defaultResponse, popupId=popupId)
    if dialog.dontShowPopup():
        getLogger().debug(f'Popup {popupId!r} skipped with response={defaultResponse}')
        return defaultResponse
    dialog.setStandardButtons(Ok | Cancel)
    dialog.setDefaultButton(Ok)
    return dialog.exec_() == Ok


def showYesNo(title, message, parent=None, iconPath=None,
              dontShowEnabled=False, defaultResponse=None, popupId=None):
    dialog = MessageDialog('Query', title, message, Question, iconPath, parent,
                           dontShowEnabled=dontShowEnabled, defaultResponse=defaultResponse, popupId=popupId)
    if dialog.dontShowPopup():
        getLogger().debug(f'Popup {popupId!r} skipped with response={defaultResponse}')
        return defaultResponse
    dialog.setStandardButtons(Yes | No)
    dialog.setDefaultButton(Yes)
    return dialog.exec_() == Yes


def showRetryIgnoreCancel(title, message, parent=None, iconPath=None):
    dialog = MessageDialog('Retry', title, message, Question, iconPath, parent)
    dialog.setStandardButtons(Retry | Ignore | Cancel)
    dialog.setDefaultButton(Retry)
    result = dialog.exec_()
    if result == Retry:
        return True
    elif result == Cancel:
        return False

    else:
        return None


def showSaveDiscardCancel(title, message, parent=None, iconPath=None):
    """Save, Discard, Cancel query box.

    :param title: title of the widget
    :param message: message to be displayed
    :param parent: parent widget
    :param iconPath: optional icon to display
    :return: True for Save, False for Discard or None for Cancel
    """

    dialog = MessageDialog('Query', title, message, Question, iconPath, parent)
    dialog.setStandardButtons(Save | Discard | Cancel)
    dialog.setDefaultButton(Save)
    result = dialog.exec_()
    if result == Save:
        return True
    elif result == Discard:
        return False
    else:
        return None


def showYesNoCancel(title, message, parent=None, iconPath=None):
    """Yes, No, Cancel query box.

    :param title: title of the widget
    :param message: message to be displayed
    :param parent: parent widget
    :param iconPath: optional icon to display
    :return: True for Yes, False for No or None for Cancel
    """
    dialog = MessageDialog('Query', title, message, Question, iconPath, parent)
    dialog.setStandardButtons(Yes | No | Cancel)
    dialog.setDefaultButton(Yes)
    result = dialog.exec_()
    if result == Yes:
        return True
    elif result == No:
        return False
    else:
        return None


def showWarning(title, message, parent=None, iconPath=None, detailedText=None,
                dontShowEnabled=False, defaultResponse=None, popupId=None):
    dialog = MessageDialog(title='Warning', basicText=title, message=message, icon=Warning, iconPath=iconPath,
                           parent=parent, detailedText=detailedText,
                           dontShowEnabled=dontShowEnabled, defaultResponse=defaultResponse, popupId=popupId)

    if dialog.dontShowPopup():
        getLogger().debug(f'Popup {popupId!r} skipped with response={defaultResponse}')
        return defaultResponse

    # don't show checkbox required an 'accepted' response to work
    dialog.setStandardButtons(Close if not dontShowEnabled else Ok)
    dialog.exec_()
    return


def showNYI(parent=None):
    text = 'Not yet implemented'
    dialog = MessageDialog(title=text, basicText=text, message='Sorry!', icon=Warning, iconPath=None, parent=parent)
    dialog.setStandardButtons(Close)
    dialog.exec_()
    return


def showOkCancelWarning(title, message, parent=None, iconPath=None,
                        dontShowEnabled=False, defaultResponse=None, popupId=None):
    dialog = MessageDialog('Warning', title, message, Warning, iconPath, parent,
                           dontShowEnabled=dontShowEnabled, defaultResponse=defaultResponse, popupId=popupId)
    if dialog.dontShowPopup():
        getLogger().debug(f'Popup {popupId!r} skipped with response={defaultResponse}')
        return defaultResponse
    dialog.setStandardButtons(Ok | Cancel)
    dialog.setDefaultButton(Cancel)
    return dialog.exec_() == Ok


def showYesNoWarning(title, message, parent=None, iconPath=None,
                     dontShowEnabled=False, defaultResponse=None, popupId=None):
    dialog = MessageDialog('Warning', title, message, Warning, iconPath, parent,
                           dontShowEnabled=dontShowEnabled, defaultResponse=defaultResponse, popupId=popupId)
    if dialog.dontShowPopup():
        getLogger().debug(f'Popup {popupId!r} skipped with response={defaultResponse}')
        return defaultResponse
    dialog.setStandardButtons(Yes | No)
    dialog.setDefaultButton(No)
    return dialog.exec_() == Yes


def showYesNoCancelWarning(title, message, parent=None, iconPath=None):
    dialog = MessageDialog('Warning', title, message, Warning, iconPath, parent)
    dialog.setStandardButtons(Yes | No | Cancel)
    dialog.setDefaultButton(Cancel)
    return dialog.exec_()


def showMulti(title, message, texts, objects=None, parent=None, iconPath=None, okText='OK', cancelText='Cancel',
              destructive=(), checkbox=None, checked=True,
              dontShowEnabled=False, defaultResponse=None, popupId=None):
    if objects:
        assert len(objects) == len(texts)
    dialog = MessageDialog('Query', title, message, Question, iconPath, parent,
                           dontShowEnabled=dontShowEnabled, defaultResponse=defaultResponse, popupId=popupId)
    if dialog.dontShowPopup():
        getLogger().debug(f'Popup {popupId!r} skipped with response={defaultResponse}')
        return defaultResponse

    _checkbox = None
    for text in texts:
        lower_text = text.strip().lower()
        if checkbox and (lower_text in checkbox or checkbox in lower_text):
            raise Exception('Checkboxes and buttons cannot have the same name!')
        else:
            role = QtWidgets.QMessageBox.ActionRole
            if lower_text == 'cancel' or lower_text == cancelText.strip().lower():
                role = QtWidgets.QMessageBox.RejectRole
            if not isinstance(destructive, str):
                destructive = [item.strip().lower() for item in destructive]
            else:
                destructive = destructive.strip().lower()
            if lower_text in destructive:
                role = QtWidgets.QMessageBox.DestructiveRole
            if lower_text == 'ok' or lower_text == okText.strip().lower():
                role = QtWidgets.QMessageBox.AcceptRole
            button = dialog.addButton(text, role)
            if lower_text == 'ok' or lower_text == okText.strip().lower():
                dialog.setDefaultButton(button)

        if checkbox is not None:
            _checkbox = CheckBox(parent=dialog, text=checkbox, checked=checked)
            dialog.setCheckBox(_checkbox)
    if _checkbox is not None:
        _checkbox.setFocus()

    index = dialog.exec_()
    result = ''
    if dialog.clickedButton() is not None:
        if objects:
            result = objects[index]

        else:
            result = texts[index]
    if checkbox is not None and _checkbox.isChecked():
        result = ' %s %s ' % (result, checkbox)

    return result


def showError(title, message, parent=None, iconPath=None):
    dialog = MessageDialog('Error', title, message, Critical, iconPath, parent)
    dialog.setStandardButtons(Close)
    dialog.exec_()
    return


def showMessage(title, message, parent=None, iconPath=None):
    dialog = MessageDialog('Message', title, message, Information, iconPath, parent)
    dialog.setStandardButtons(Close)
    dialog.exec_()
    return


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# progressPopup dialog
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# testing simple progress/busy popup

# from PyQt5 import QtCore
# from PyQt5 import QtGui, QtWidgets
# from PyQt5.QtCore import pyqtSlot
from ccpn.ui.gui.popups.Dialog import CcpnDialog
from ccpn.ui.gui.widgets.Label import Label
from contextlib import contextmanager
from time import sleep, time


class progressPopup(CcpnDialog):
    """
    Open a small popup to allow changing the name of a Note
    """

    def __init__(self, parent=None, mainWindow=None, title='busy', busyFunc=None, progressMax=1,
                 **kwds):
        """
        Initialise the widget
        """
        super().__init__(parent, setLayout=True, windowTitle='busy', **kwds)

        # self.mainWindow = mainWindow
        # self.application = mainWindow.application
        # self.project = mainWindow.application.project
        # self.current = mainWindow.application.current

        self.setParent(parent)
        self.busyFunc = busyFunc

        # progress bar
        self.progressbar = QtWidgets.QProgressBar()
        self.progressbar.reset()  # resets the progress bar
        self.progressbar.setAlignment(Qt.AlignCenter)  # centers the text
        # 'valueChanged()' signal
        self.progressbar.valueChanged.connect(self.progress_changed)
        self.progressbar.setMinimum(0)
        self.progressbar.setMaximum(progressMax)
        # # 'start' button
        # self.btn_start = QtWidgets.QPushButton('Start')
        # # 'clicked()' signal
        # self.btn_start.clicked.connect(self.start)
        #
        # timer
        self.timer = QtCore.QTimer()
        # 'timeout()' signal
        self.timer.timeout.connect(self.progress_simulation)

        self.label = Label(self, title, grid=(0, 0))

        # from ccpn.framework.Application import getApplication
        # getApp = getApplication()
        # if getApp and hasattr(getApp, '_fontSettings'):
        #     self.label.setFont(getApp._fontSettings.messageFont)
        #     self.setFont(getApp._fontSettings.messageFont)
        setWidgetFont(self, )

        # self.layout().addWidget(self.progressbar)

        # vlayout.addWidget(self.btn_start)
        # vlayout.addStretch()
        # self.setLayout(vlayout)

        # self.setWindowFlags(QtCore.Qt.WindowTitleHint)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self.show()
        self.raise_()
        self.setModal(True)

    # 'progress_simulation()' slot
    @pyqtSlot()
    def progress_simulation(self):
        value = self.progressbar.value()  # gets the current value of the progress bar
        self.progressbar.setValue(value + 1)  # adds 1 to the current value
        self.progressbar.update()

    # 'start()' slot
    # @pyqtSlot()
    # def start(self):
    #     self.progressbar.reset()  # resets the progress bar
    #     self.timer.start(40)  # interval of 40 milliseconds

    # 'progress_changed()' slot
    @pyqtSlot(int)
    def progress_changed(self, value):
        # stops the timer if the progress bar reaches its maximum value
        if value == self.progressbar.maximum():
            self.timer.stop()


# small object to facilitate passing data to progressManager - could use 'send' but only needed once
@dataclass
class _progressStore:
    newWindow = None


@contextmanager
def progressManager(parent, title=None, progressMax=100):
    thisProg = progressPopup(parent=parent, title=title, progressMax=progressMax)
    _prog = _progressStore()
    try:
        thisProg.progress_simulation()
        thisProg.update()
        QtWidgets.QApplication.processEvents()  # still doesn't catch all the paint events
        sleep(0.1)
        yield _prog  # yield control to the main process
    finally:
        thisProg.update()
        QtWidgets.QApplication.processEvents()  # hopefully it will redraw the popup
        thisProg.close()
        if win := (_prog.newWindow or parent):
            # return correct focus control to the parent
            QtWidgets.QApplication.setActiveWindow(win)


@contextmanager
def busyDialog(parent, title=None, progressMax=100):
    thisProg = progressPopup(parent=parent, title=title, progressMax=progressMax)
    _prog = _progressStore()
    try:
        thisProg.progress_simulation()
        thisProg.update()
        QtWidgets.QApplication.processEvents()  # still doesn't catch all the paint events
        sleep(0.1)
        yield thisProg  # yield control to the main process
    finally:
        thisProg.update()
        QtWidgets.QApplication.processEvents()  # hopefully it will redraw the popup
        thisProg.close()
        if win := (_prog.newWindow or parent):
            # return correct focus control to the parent
            QtWidgets.QApplication.setActiveWindow(win)


def _stoppableProgressBar(data, title='Calculating...', buttonText='Cancel'):
    """ Use this for opening a _stoppableProgressBar before time-consuming operations. the cancel button allows
     the user to stop the loop manually.
    eg:
    for i in _stoppableProgressBar(range(10), title, buttonText):
        # do stuff
        pass
    for use in a zip loop, wrap with 'list':
    eg for (cs, ts) in _stoppableProgressBar(list(zip(controlSpectra, targetSpectra)))
    """
    widget = QtWidgets.QProgressDialog(title, buttonText, 0, len(data))
    widget.setAutoClose(True)
    widget.raise_()
    for c, v in enumerate(iter(data), start=1):
        QtCore.QCoreApplication.instance().processEvents()
        if widget.wasCanceled():
            raise RuntimeError('Stopped by user')
        widget.setValue(c)
        yield (v)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# busyOverlay
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class busyOverlay(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        palette = QtGui.QPalette(self.palette())
        palette.setColor(palette.Background, Qt.transparent)
        self.setPalette(palette)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(event.rect(), QtGui.QBrush(QtGui.QColor(255, 255, 255, 127)))
        painter.setPen(QtGui.QPen(Qt.NoPen))
        for i in range(6):
            if (self.counter / 5) % 6 == i:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(127 + (self.counter % 5) * 32, 127, 127)))
            else:
                painter.setBrush(QtGui.QBrush(QtGui.QColor(127, 127, 127)))
            painter.drawEllipse(
                    int(self.width() / 2 + 30 * math.cos(2 * math.pi * i / 6.0) - 10),
                    int(self.height() / 2 + 30 * math.sin(2 * math.pi * i / 6.0) - 10),
                    20, 20)

    def showEvent(self, event):
        self.timer = self.startTimer(50)
        self.counter = 0

    def timerEvent(self, event):
        self.counter += 1
        self.update()
        if self.counter == 60:
            self.killTimer(self.timer)
            self.hide()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)


    def callback():
        print(showWarning('Another Warning',
                          'Test for a basic popup with a long line of text as the basic text and a path:\n/Users/ejb66/PycharmProjects/Git/AnalysisV3/internal/scripts/something/filename.txt'))
        print(showWarning('Another Warning and Test for a basic popup with a long line of text as the basic text',
                          'Test for a basic popup with a long line of text as the basic text and a path\n/Users/ejb66/PycharmProjects/Git/AnalysisV3/internal/scripts/something/filename.txt '
                          'and text with no spaces qwertyuiopasdfghjklzxcvbnm0123456789_qwertyuiopasdfghjklzxcvbnm0123456789_qwertyuiopasdfghjklzxcvbnm0123456789_qwertyuiopasdfghjklzxcvbnm0123456789'))
        print(showWarning(
                'Another Warning and Test qwertyuiopasdfghjklzxcvbnm0123456789_qwertyuiopasdfghjklzxcvbnm0123456789_qwertyuiopasdfghjklzxcvbnm0123456789_qwertyuiopasdfghjklzxcvbnm0123456789\n for a basic popup with a long line of text as the basic text',
                'Test for a basic popup with a long line of text as the basic text and a path\n/Users/ejb66/PycharmProjects/Git/AnalysisV3/internal/scripts/something/filename.txt '
                'and text with no spaces qwertyuiopasdfghjklzxcvbnm0123456789_qwertyuiopasdfghjklzxcvbnm0123456789_qwertyuiopasdfghjklzxcvbnm0123456789_qwertyuiopasdfghjklzxcvbnm0123456789 something\n else'))


    callback()
