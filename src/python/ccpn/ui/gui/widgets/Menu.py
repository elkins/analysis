"""Module Documentation here
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
__dateModified__ = "$dateModified: 2024-08-23 19:21:20 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtWidgets, QtCore
from ccpn.ui.gui.widgets.Action import Action
from ccpn.ui.gui.widgets.Base import Base
from ccpn.framework.Translation import translator


SHOWMODULESMENU = 'Show/hide Modules'
MACROSMENU = 'User Macros'
CCPNMACROSMENU = 'Run CCPN Macros'
USERMACROSMENU = 'Run User Macros'
TUTORIALSMENU = 'Tutorials'
HOWTOSMENU = 'How-Tos'
PLUGINSMENU = 'User Plugins'
CCPNPLUGINSMENU = 'CCPN Plugins'


class Menu(QtWidgets.QMenu, Base):
    _colourEnabled = False
    _actionGeometries = None

    def __init__(self, title, parent, isFloatWidget=False, **kwds):
        super().__init__(parent)
        Base._init(self, isFloatWidget=isFloatWidget, **kwds)

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)
        title = translator.translate(title)
        self.setTitle(title)
        self.isFloatWidget = isFloatWidget
        self.setToolTipsVisible(True)

    def addItem(self, text, shortcut=None, callback=None, checked=True, checkable=False, icon=None, toolTip=None,
                **kwargs):
        action = Action(self.getParent(), text, callback=callback, shortcut=shortcut,
                        checked=checked, checkable=checkable, icon=icon, toolTip=toolTip,
                        isFloatWidget=self.isFloatWidget, **kwargs)
        self.addAction(action)
        return action

    def _addSeparator(self, *args, **kwargs):
        separator = self.addSeparator()
        return separator

    def addMenu(self, title, **kwargs):
        menu = Menu(title, self)
        QtWidgets.QMenu.addMenu(self, menu)
        return menu

    def _addQMenu(self, menu):
        """This adds a normal QMenu.
        """
        QtWidgets.QMenu.addMenu(self, menu)
        return menu

    def getItems(self):
        dd = {i.text(): i for i in self.actions()}
        return dd

    def getActionByName(self, name):
        """Return the named menu action.
        """
        return self.getItems().get(name, None)

    def moveActionBelowName(self, action, targetActionName):
        """Move an action below a pre-existing name.
        """
        targetAction = self.getActionByName(targetActionName)
        if targetAction:
            self.insertAction(action, targetAction)

    def moveActionAboveName(self, action, targetActionName):
        """Move an action above a pre-existing name.
        """
        targetAction = self.getActionByName(targetActionName)
        if targetAction:
            self.insertAction(targetAction, action)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if self._colourEnabled:
            # if _colourEnabled defined for this menu then build a dict of the actionGeometry's
            # these can be used in the QProxyStyle to provide access the QAction
            self._actionGeometries = {str(self.actionGeometry(action)): action
                                      for action in self.actions()}

    def setColourEnabled(self, value):
        if not isinstance(value, bool):
            raise TypeError(f'{self.__class__.__name__}.setColourEnabled: value is not a bool')
        self._colourEnabled = value

    def isColourEnabled(self) -> bool:
        return self._colourEnabled


class MenuBar(QtWidgets.QMenuBar):
    def __init__(self, parent):
        QtWidgets.QMenuBar.__init__(self, parent)
