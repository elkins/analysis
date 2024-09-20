"""Module Documentation here

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2023"
__credits__ = ("Ed Brooksbank, Joanna Fox, Victoria A Higman, Luca Mureddu, Eliza Płoskoń",
               "Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2023-11-10 18:27:12 +0000 (Fri, November 10, 2023) $"
__version__ = "$Revision: 3.2.2 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtGui, QtWidgets

from ccpn.framework.PathsAndUrls import ccpnUrl

from ccpn.ui.gui.widgets.Base import Base, FOCUS_DICT
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Button import Button
# from ccpn.ui.gui.widgets.WebBrowser import WebBrowser
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.util.Logging import getLogger


class ButtonListMixin:
    def getButton(self, buttonName: str):
        """
        Return the button with the given name or return None
        :param buttonName(str) - name of the button
        """
        if buttonName in self.buttonNames.keys():
            return self.buttons[self.buttonNames[buttonName]]

        else:
            getLogger().warning('Button %s not found in the list' % buttonName)

    def setButtonEnabled(self, buttonName: str, enable: bool = True):
        """
        Enable/Disable a button by name
        :param buttonName(str) - name of the button
        :param enable(bool) - True or False
        """
        if buttonName in self.buttonNames.keys():
            self.buttons[self.buttonNames[buttonName]].setEnabled(enable)
        else:
            getLogger().warning('Button %s not found in the list' % buttonName)

    def setButtonVisible(self, buttonName: str, visible: bool = True):
        """
        Show/hide a button by name
        :param buttonName(str) - name of the button
        :param visible(bool) - True or False
        """
        if buttonName in self.buttonNames.keys():
            if visible:
                self.buttons[self.buttonNames[buttonName]].show()
            else:
                self.buttons[self.buttonNames[buttonName]].hide()
        else:
            getLogger().warning('Button %s not found in the list' % buttonName)

    def _insertSpacer(self, index):
        from ccpn.ui.gui.widgets.Spacer import Spacer

        if not (0 <= index < len(self.buttons)):
            raise ValueError('Insert position out of range')

        j = len(self.buttons)
        for i, button in enumerate(self.buttons):
            pos = (i + (1 if i >= index else 0))
            if 'h' in self.direction:
                grid = (0, pos)
            else:
                grid = (pos, 0)

            self.getLayout().addWidget(self.buttons[i], *grid)

        if 'h' in self.direction:
            spacerGrid = (0, index)
            xExpand = QtWidgets.QSizePolicy.Expanding
            yExpand = QtWidgets.QSizePolicy.Fixed
        else:
            spacerGrid = (index, 0)
            xExpand = QtWidgets.QSizePolicy.Fixed
            yExpand = QtWidgets.QSizePolicy.Expanding

        Spacer(self, 25, 5, xExpand, yExpand, grid=spacerGrid)


# GST This uses the builtin Qt ButtonBox to make buttons for dialogs behave nicely
# e.g. select correct layout & behaviour for ok / cancel and dangerous buttons
# ButtonList should be treated as deprecated?
class ButtonBoxList(QtWidgets.QDialogButtonBox, Base, ButtonListMixin):

    def __init__(self, parent=None, texts=None, callbacks=None, icons=None,
                 tipTexts=None, direction='h', commands=None, ok='OK', cancel='cancel', destructive=("Discard", "Don't Save"),
                 images=None, **kwargs):

        super().__init__(parent)  # ejb - added setLayout
        Base._init(self, **kwargs)

        self._ok = ok.lower()
        self._cancel = cancel.lower()
        self._destructive = [item.lower() for item in destructive]
        self.buttonNames = {}

        if commands:
            getLogger().warning("qtgui.ButtonList.commands is deprecated; use .callbacks")
            callbacks = commands

        if images:
            getLogger().warning("qtgui.ButtonList.images is deprecated; use .icons")
            icons = images

        if texts is None:
            texts = []

        if callbacks is None:
            callbacks = []

        assert len(texts) == len(callbacks)

        direction = direction.lower()
        self.direction = direction

        if tipTexts is None:
            tipTexts = []

        if icons is None:
            icons = []

        while len(tipTexts) < len(texts):
            tipTexts.append(None)

        while len(icons) < len(texts):
            icons.append(None)

        self.buttons = []
        self.addButtons(texts, callbacks, icons, tipTexts)

        # set focus always on the last button (which is usually the ok, or run button)
        if len(self.buttons) > 0:
            lastButton = self.buttons[-1]
            lastButton.setFocus()

    def addButtons(self, texts, callbacks, icons=None, tipTexts=None):

        if tipTexts is None:
            tipTexts = []

        if icons is None:
            icons = []

        while len(tipTexts) < len(texts):
            tipTexts.append(None)

        while len(icons) < len(texts):
            icons.append(None)

        j = len(self.buttons)

        for i, text in enumerate(texts):
            button = Button(self, text, callbacks[i], icons[i],
                            tipText=tipTexts[i])

            extraWidth = button.fontMetrics().boundingRect('W' * 2).width()
            width = button.fontMetrics().boundingRect(text).width()
            height = button.fontMetrics().boundingRect(text).height() + 8
            button.setMinimumWidth(width + extraWidth)
            button.setMinimumHeight(height)
            button.setFocusPolicy(FOCUS_DICT['tab'])

            role = QtWidgets.QDialogButtonBox.ActionRole
            lowerText = text.lower()
            if lowerText == self._ok:
                role = QtWidgets.QDialogButtonBox.AcceptRole
            elif lowerText == self._cancel:
                role = QtWidgets.QDialogButtonBox.RejectRole
            elif lowerText in self._destructive:
                role = QtWidgets.QDialogButtonBox.DestructiveRole

            self.addButton(button, role)
            self.buttons.append(button)
            self.buttonNames[text] = i + j


# this should be treated as deprecated? No!
# see ButtonBoxList above
class ButtonList(Widget, ButtonListMixin):
    """
    A building block Widget used throughout. (Not just as ok/close in popups).
    """
    def __init__(self, parent=None, texts=None, callbacks=None, icons=None, setMinimumWidth=True,
                 tipTexts=None, direction='h', commands=None, images=None, setLastButtonFocus=True, enableFocusBorder=True, **kwds):

        super().__init__(parent, setLayout=True, **kwds)  # ejb - added setLayout

        self.buttonNames = {}

        if commands:
            getLogger().warning("qtgui.ButtonList.commands is deprecated; use .callbacks")
            callbacks = commands

        if images:
            getLogger().warning("qtgui.ButtonList.images is deprecated; use .icons")
            icons = images

        if texts is None:
            texts = []

        if callbacks is None:
            callbacks = []

        assert len(texts) == len(callbacks)

        direction = direction.lower()
        self.direction = direction
        self._enableFocusBorder = enableFocusBorder

        if tipTexts is None:
            tipTexts = []

        if icons is None:
            icons = []

        while len(tipTexts) < len(texts):
            tipTexts.append(None)

        while len(icons) < len(texts):
            icons.append(None)

        self.buttons = []
        self.addButtons(texts, callbacks, icons, tipTexts, setMinimumWidth)

        # set focus always on the last button (which is usually the ok, or run button) unless setLastButtonFocus flag == False
        if len(self.buttons) > 0 and setLastButtonFocus:
            lastButton = self.buttons[-1]
            lastButton.setFocus()

    def addButtons(self, texts, callbacks, icons=None, tipTexts=None, setMinimumWidth=True):

        if tipTexts is None:
            tipTexts = []

        if icons is None:
            icons = []

        while len(tipTexts) < len(texts):
            tipTexts.append(None)

        while len(icons) < len(texts):
            icons.append(None)

        j = len(self.buttons)

        for i, text in enumerate(texts):
            if 'h' in self.direction:
                grid = (0, i + j)
            else:
                grid = (i + j, 0)

            button = Button(self, text, callbacks[i], icons[i],
                            tipText=tipTexts[i], grid=grid,
                            enableFocusBorder=self._enableFocusBorder)

            width = button.fontMetrics().boundingRect(text).width() + 7
            if setMinimumWidth:
                button.setMinimumWidth(int(width * 1.5))

            self.buttons.append(button)
            self.buttonNames[text] = i + j


# class UtilityButtonList(ButtonList):
#
#     def __init__(self, parent,
#                  webBrowser=None, helpUrl=None, helpMsg=None,
#                  doClone=True, doHelp=True, doClose=True,
#                  cloneText=None, helpText=None, closeText=None,
#                  cloneCmd=None, helpCmd=None, closeCmd=None,
#                  cloneTip='Duplicate window', helpTip='Show help', closeTip='Close window',
#                  *args, **kwds):
#
#         ButtonList.__init__(self, parent)
#
#         self.helpUrl = helpUrl
#         self.helpMsg = helpMsg
#
#         self.popup = parent.window()
#         if not isinstance(self.popup, BasePopup):
#             self.popup = None
#
#         if self.popup and not webBrowser:
#             webBrowser = WebBrowser(self.popup)
#
#         self.webBrowser = webBrowser
#
#         _callbacks = []
#         _texts = []
#         _icons = []
#         _tipTexts = []
#
#         _doActions = [(doClone, cloneCmd, self.duplicatePopup, cloneText, 'icons/window-duplicate.png', cloneTip),
#                       (doHelp, helpCmd, self.launchHelp, helpText, 'icons/system-help.png', helpTip),
#                       (doClose, closeCmd, self.closePopup, closeText, 'icons/window-close.png', closeTip), ]
#
#         for doAction, userCmd, defaultCmd, text, image, tipText in _doActions:
#             if doAction:
#                 _callbacks.append(userCmd or defaultCmd)
#                 _tipTexts.append(tipText)
#                 _texts.append(text)
#
#                 if image:
#                     icon = Icon(image)
#                 else:
#                     icon = None
#
#                 _icons.append(icon)
#
#         self.addButtons(_texts, _callbacks, _icons, _tipTexts)
#
#     def duplicatePopup(self):
#
#         if self.popup:
#             try:
#                 newPopup = self.popup.__class__(self.popup.parent)
#                 x, y, w, h = self.getGeometry()
#                 newPopup.setGeometry(x + 25, y + 25, w, h)
#
#             except:
#                 pass
#
#     def launchHelp(self):
#
#         if self.helpUrl and self.webBrowser:
#             self.webBrowser.open(self.helpUrl)
#
#         elif self.popup:
#             from ccpn.ui.gui.widgets.WebView import WebViewPopup
#
#             popup = WebViewPopup(self.popup, url=self.helpMsg or ccpnUrl + '/documentation')
#
#     def closePopup(self):
#
#         if self.popup:
#             self.popup.close()
#
#         else:
#             self.destroy()


if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.widgets.BasePopup import BasePopup
    from ccpn.ui.gui.popups.Dialog import CcpnDialog


    def callback(text):
        print('callback', text)


    texts = ['abc', 'def', 'ghi']
    callbacks = [lambda t=text: callback(t) for text in texts]
    icons = [None, None, 'icons/applications-system.png']

    app = TestApplication()
    popup = CcpnDialog(windowTitle='Test ButtonList')

    # popup.setSize(200,200)
    popup.setGeometry(200, 200, 200, 200)

    buttons = ButtonList(parent=popup, texts=texts, callbacks=callbacks, icons=icons, grid=(2, 2))
    # utils = UtilityButtonList(parent=popup, texts=texts, callbacks=callbacks, helpUrl=ccpnUrl+"/software")

    popup.show()
    popup.raise_()

    app.start()
