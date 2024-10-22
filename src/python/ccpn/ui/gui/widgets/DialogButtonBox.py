"""
Module Documentation here
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
__dateModified__ = "$dateModified: 2024-10-14 19:13:40 +0100 (Mon, October 14, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-05-26 14:50:42 +0000 (Tue, May 26, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtCore, QtWidgets
from operator import or_
from functools import reduce, partial
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Font import setWidgetFont


class DialogButtonBox(QtWidgets.QDialogButtonBox, Base):

    def __init__(self, parent=None, buttons=None, callbacks=None, texts=None, tipTexts=None,
                 icons=None, enabledStates=None, visibleStates=None, defaultButton=None, enableIcons=False,
                 orientation='horizontal', **kwds):

        super().__init__(parent)
        Base._init(self, **kwds)

        self._parent = parent

        buttons = buttons or []
        if not isinstance(buttons, (tuple, list)):
            raise TypeError('Error, buttons must be tuple/list')
        N = len(buttons)
        callbacks = callbacks or []
        texts = texts or []
        tipTexts = tipTexts or []
        icons = icons or []
        enabledStates = enabledStates or []
        visibleStates = visibleStates or []

        if not isinstance(callbacks, (tuple, list)):
            raise TypeError('Error, callbacks must be tuple/list')
        callbacks = (list(callbacks) + N * [None])[:N]

        if not isinstance(texts, (tuple, list)):
            raise TypeError('Error, texts must be tuple/list')
        texts = (list(texts) + N * [None])[:N]

        if not isinstance(tipTexts, (tuple, list)):
            raise TypeError('Error, tipTexts must be tuple/list')
        tipTexts = (list(tipTexts) + N * [None])[:N]

        if not isinstance(icons, (tuple, list)):
            raise TypeError('Error, icons must be tuple/list')
        icons = (list(icons) + N * [None])[:N]

        if not isinstance(enabledStates, (tuple, list)):
            raise TypeError('Error, enabledStates must be tuple/list')
        enabledStates = (list(enabledStates) + N * [None])[:N]

        if not isinstance(visibleStates, (tuple, list)):
            raise TypeError('Error, visibleStates must be tuple/list')
        visibleStates = (list(visibleStates) + N * [None])[:N]

        if defaultButton is not None and defaultButton not in buttons:
            raise TypeError(f"Error, defaultButton not in buttons")
        if not isinstance(orientation, str):
            raise TypeError("Error, orientation must be str: 'h' or 'v'")

        if 'h' in orientation.lower():
            self.setOrientation(QtCore.Qt.Horizontal)
        else:
            self.setOrientation(QtCore.Qt.Vertical)

        self._userButtonDict = {}
        if buttons:
            # set the standard buttons - will be in OS specific order
            buttonTypes = reduce(or_, [btn for btn in buttons if not isinstance(btn, str)])
            self.setStandardButtons(buttonTypes)

            for button in [btn for btn in buttons if isinstance(btn, str)]:
                # add 'AcceptRole' buttons for user defined buttons - store in user dict
                newButton = self.addButton(button, QtWidgets.QDialogButtonBox.AcceptRole)
                self._userButtonDict[button] = newButton
            self.clicked.connect(self._setButtonClicked)

            if callbacks:
                for button, callback, text, tipText, icon, enabledState, visibleState in \
                        zip(buttons, callbacks, texts, tipTexts, icons, enabledStates, visibleStates):

                    thisButton = self.button(button)
                    if thisButton:
                        if callback is not None:
                            thisButton.clicked.connect(callback)
                        if text is not None:
                            thisButton.setText(text)
                        if tipText is not None:
                            thisButton.setToolTip(tipText)

                        if enableIcons and icon is not None:  # filename or pixmap
                            thisButton.setIcon(Icon(icon))
                            # NOTE: sometimes this causes the button to reset its stylesheet
                            thisButton.setIconSize(QtCore.QSize(22, 22))

                        if enabledState is not None:
                            thisButton.setEnabled(enabledState)
                        if visibleState is not None:
                            thisButton.setVisible(visibleState)

                        thisButton.setMinimumHeight(24)
                        setWidgetFont(thisButton, )

            if defaultButton is not None:
                self._parent.setDefaultButton(self.button(defaultButton))

        self._setStyle()

    def _setButtonClicked(self, button):
        # Set which button has been pressed to close the dialog. Need to check that this fires before
        # individual callbacks (I think is okay), and user buttons (non-standard) are okay
        self._clickedButtonId = self.standardButton(button)

    def _setStyle(self):
        _style = """QPushButton { padding: 3px 5px 3px 5px; }
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
        for button in self.buttons():
            button.setStyleSheet(_style)

    def button(self, which: 'QtWidgets.QDialogButtonBox.StandardButton') -> QtWidgets.QPushButton:
        # subclass 'button' to allow searching for user buttons in _userButtonDict before standardButtons
        return (self._userButtonDict.get(which) if isinstance(which, str) else None) or super().button(which)
