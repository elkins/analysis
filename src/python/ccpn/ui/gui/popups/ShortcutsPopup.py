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
__dateModified__ = "$dateModified: 2024-10-03 12:47:18 +0100 (Thu, October 03, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
from functools import reduce, partial
from PyQt5 import QtWidgets
from ccpn.ui.gui.widgets.Frame import ScrollableFrame, Frame
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.FileDialog import MacrosFileDialog
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.ScrollArea import ScrollArea
from ccpn.ui.gui.popups.Dialog import CcpnDialog, CcpnDialogMainWidget
from ccpn.util.Logging import getLogger


class ShortcutsPopup(CcpnDialogMainWidget):
    USESCROLLWIDGET = True

    def __init__(self, parent=None, mainWindow=None, title='Define User Shortcuts', **kwds):
        super().__init__(parent, setLayout=True, windowTitle=title, **kwds)

        # define the common attributes
        self.mainWindow = mainWindow
        self.application = self.mainWindow.application
        self.preferences = self.application.preferences

        self._shortcutWidget = ShortcutWidget(self.mainWidget, mainWindow=mainWindow, setLayout=True,
                                              grid=(0, 0))  # ejb
        self.setMinimumSize(400, 400)

        # add close/save/saveAndClose buttons (close/apply/OK)
        self.setCloseButton(callback=self.close)
        self.setApplyButton(callback=self.save, text='Save')
        self.setOkButton(callback=self.saveAndQuit, text='Save and Close')
        self.setDefaultButton(CcpnDialogMainWidget.CLOSEBUTTON)

    def save(self):
        newShortcuts = self._shortcutWidget.getShortcuts()
        self.preferences.shortcuts = newShortcuts
        if hasattr(self.application, '_userShortcuts') and self.application._userShortcuts:
            for shortcut in newShortcuts:
                self.application._userShortcuts.addUserShortcut(shortcut, newShortcuts[shortcut])

    def saveAndQuit(self):
        self.save()
        self.close()

    def addToFirstAvailableShortCut(self, filePath):
        self._shortcutWidget._addToFirstAvailableShortCut(filePath)


class ShortcutWidget(Frame):

    def __init__(self, parent, mainWindow=None, setLayout=True, **kwds):
        super().__init__(parent, setLayout=setLayout, **kwds)
        from functools import partial

        self.mainWindow = mainWindow
        self.application = self.mainWindow.application
        self.preferences = self.application.preferences

        i = 0
        self.widgets = []
        for shortcut in sorted(self.preferences.shortcuts):
            shortcutLabel = Label(self, grid=(i, 0), text=shortcut)
            self.shortcutLineEdit = LineEdit(self, grid=(i, 1))
            self.shortcutLineEdit.setText(self.preferences.shortcuts[shortcut])
            # self.shortcutLineEdit.editingFinished.connect(partial(self.validateFunction, i))
            pathButton = Button(self, grid=(i, 2), icon='icons/applications-system',
                                callback=partial(self._getMacroFile, i))
            self.widgets.append([shortcutLabel, self.shortcutLineEdit, pathButton])
            i += 1

    def getShortcuts(self):
        shortcutDict = {}
        layout = self.layout()
        for i in range(layout.rowCount()):
            shortcut = layout.itemAtPosition(i, 0).widget().text()
            function = layout.itemAtPosition(i, 1).widget().text()
            shortcutDict[shortcut] = function
        return shortcutDict

    def _addToFirstAvailableShortCut(self, filePath):
        command = 'runMacro("%s")' % filePath
        layout = self.layout()
        if command not in self.getShortcuts().values():
            for i in range(layout.rowCount()):
                functionWidget = layout.itemAtPosition(i, 1).widget()
                if functionWidget.get() == '':
                    functionWidget.set(command)
                    return

    def _getMacroFile(self, index):
        shortcutLineEdit = self.widgets[index][1]
        if os.path.exists('/'.join(shortcutLineEdit.text().split('/')[:-1])):
            currentDirectory = '/'.join(shortcutLineEdit.text().split('/')[:-1])
        else:
            currentDirectory = os.path.expanduser(self.preferences.general.userMacroPath)
        dialog = MacrosFileDialog(parent=self, acceptMode='select', directory=currentDirectory)
        dialog._show()
        directory = dialog.selectedFiles()
        if directory and len(directory) > 0:
            shortcutLineEdit.setText('runMacro("%s")' % directory[0])

    def validateFunction(self, i):
        # check if function for shortcut is a .py file or exists in the CcpNmr V3 namespace
        path = self.widgets[i][1].text()
        namespace = self.mainWindow.namespace

        if path == '':
            return

        if path.startswith('/'):

            if os.path.exists(path) and path.split('/')[-1].endswith('.py'):
                getLogger().debug(f'ShortcutWidget.validateFunction: path is valid')
                return True

            elif not os.path.exists(path) or not path.split('/')[-1].endswith('.py'):
                if not os.path.exists(path):
                    showWarning('Invalid macro path', 'Macro path: %s is not a valid path' % path)
                    return False

                if not path.split('/')[-1].endswith('.py'):
                    showWarning('Invalid macro file', 'Macro files must be valid python files and end in .py' % path)
                    return False

        else:
            stub = namespace.get(path.split('.')[0])
            if not stub:
                showWarning('Invalid function', 'Function: %s is not a valid CcpNmr function' % path)
                return False
            else:
                try:
                    reduce(getattr, path.split('.')[1:], stub)
                    return True
                except:
                    showWarning('Invalid function', 'Function: %s is not a valid CcpNmr function' % path)
                    return False


class UserShortcuts():
    def __init__(self, mainWindow=None):
        self.mainWindow = mainWindow
        self.namespace = self.mainWindow.namespace
        self._userShortcutFunctions = {}
        self._numUserShortcutFunctions = 0

    def addUserShortcut(self, funcName, funcStr):
        self._userShortcutFunctions[funcName] = funcStr

    def runUserShortcut(self, funcStr):
        if funcStr in self._userShortcutFunctions:
            function = self._userShortcutFunctions[funcStr]

            if funcStr and function:
                if function.split('(')[0] == 'runMacro':
                    func = partial(self.namespace['runMacro'], function.split('(')[1].split(')')[0])
                    if func:
                        getLogger().info(function)
                        try:
                            func()
                        except:
                            getLogger().warning('Error executing macro: %s ' % function)

                    # QtWidgets.QShortcut(QtGui.QKeySequence("%s, %s" % (shortcut[0], shortcut[1])),
                    #                 self, partial(self.namespace['runMacro'], function.split('(')[1].split(')')[0]),
                    #                 context=context)

                else:
                    stub = self.namespace.get(function.split('.')[0])
                    func = reduce(getattr, function.split('.')[1:], stub)
                    if func:
                        getLogger().info(function)
                        try:
                            func()
                        except:
                            getLogger().warning('Error executing user shortcut: %s ' % function)

                    # QtWidgets.QShortcut(QtGui.QKeySequence("%s, %s" % (shortcut[0], shortcut[1])), self,
                    #                 reduce(getattr, function.split('.')[1:], stub), context=context)
