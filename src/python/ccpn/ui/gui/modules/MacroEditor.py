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
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2025-02-14 17:36:57 +0000 (Fri, February 14, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
import os
import datetime
import tempfile
from collections import OrderedDict as od

from pyqode.python.widgets import PyInteractiveConsole
from pyqode.core.api import TextHelper
from ccpn.core.lib.ContextManagers import undoBlock, notificationEchoBlocking
from ccpn.framework.PathsAndUrls import macroPath as ccpnMacroPath
from ccpn.util.Path import aPath
from ccpn.util.Logging import getLogger
from ccpn.ui.gui.modules.CcpnModule import CcpnModule, MODULENAME, WIDGETSTATE
from ccpn.ui.gui.widgets.FileDialog import MacrosFileDialog
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.IpythonConsole import IpythonConsole
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.modules.macroEditorUtil.QPythonEditor import PyCodeEditor
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.ToolBar import ToolBar
from ccpn.ui.gui.widgets.Action import Action
from collections import OrderedDict


DoubleUnderscore = '__'
_filenameLineEdit = 'filenameLineEdit'
SaveMsgTipText = 'Note: Files are automatically saved after every change if this option is enabled in General Preferences.'


PROFILING_SORTINGS = OrderedDict([ # (arg to go on script, tipText)
                ('time'         , 'internal time'       ),
                ('calls'        , 'call count'          ),
                ('cumulative'   , 'cumulative time'     ),
                ('file'         , 'file name'           ),
                ('module'       , 'file name'           ),
                ('pcalls'       , 'primitive call count'),
                ('line'         , 'line number'         ),
                ('name'         , 'function name'       ),
                ('nfl'          , 'name/file/line'      ),
                ('stdname'      , 'standard name'       ),
                ])

ProfileSufixName = '-profile'
DefaultProfileLines = .2       # % of tot lines to be printed when profiling
DefaultProfileMaxNoLines = 10  # Max number of lines to be printed when profiling
ShowMaxLines = OrderedDict([
                             ('Minimal' , DefaultProfileMaxNoLines),
                             ('Top'     , DefaultProfileLines),
                             ('Half'    , 0.5),
                             ('All'     , 1.0)
                            ])

'''
    Ideas for future development:
    
    - add local history of files.
     E.g.: dumping to json every xMinutes
     This is not "simply" an undo. But will allow to add a GUI with a preview to older states and recover it. (bit like Pycharm)
        macros_dir 
            myMacro.py
            myMacro_history.json
                  {
                  timeStamp1:"the text at timeStamp1";
                  timeStamp2:"the text at timeStamp2"
                  }
    - add pre-defined code blocks. E.g.: ccpn common commands or common imports
'''


class MacroEditor(CcpnModule):
    """
    Macro editor will run Python Files only.
    """
    includeSettingsWidget = True
    maxSettingsState = 2
    settingsPosition = 'left'

    className = 'MacroEditor'
    _includeInLastSeen = False

    def __init__(self, mainWindow=None, name='MacroEditor', filePath=None, restore=True):


        CcpnModule.__init__(self, mainWindow=mainWindow, name=name)

        self.mainWindow = mainWindow
        self.application = None
        self.project = None
        self.current = None
        self.preferences = None
        self._pythonConsole = None
        self.ccpnMacroPath = ccpnMacroPath
        self._genericFile = False
        self._editor_windows = []  # used when running the macro externally on Analysis
        self.autoOpenPythonConsole = False  # When run: always open the PythonConsole module to see the output.
        self._preEditorText = ''  # text as appeared the first time the file was opened
        self._lastTimestp = None  # used to check if the file has been changed externally
        self._lastSaved = None
        self.filePath = filePath  # working filePath. If None, it will be created
        self._tempFile = None  # a temp file holder, used when the filePath is not specified
        self._restore = restore  # will not restore the widget state if opened from a menu.
        self.userMacroDirPath = None  # dir path containing user Macros. from preferences if defined otherwise from .ccpn/macros
        self.macroSaveProfile = True
        self.autoOpenPythonConsole = True
        self.macroAutosave = True

        if self.mainWindow:  # is running in Analysis
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
            self.preferences = self.application.preferences
            self._pythonConsole = self.mainWindow.pythonConsole
            if self._pythonConsole is None:
                self._pythonConsole = IpythonConsole(self.mainWindow)

        if self.preferences:
            self.userMacroDirPath = self.preferences.general.userMacroPath
            self.macroSaveProfile = self.preferences.general.macroSaveProfile
            self.autoOpenPythonConsole = self.preferences.appearance.autoOpenPythonConsoleOnMacroEditor
            self.macroAutosave = self.preferences.general.macroAutosave
        if self.userMacroDirPath is None and self.application:
            self.userMacroDirPath = self.application.tempMacrosPath

        if self.mainWindow:
            paths = [aPath(path) for path in mainWindow.current.macroFiles]
            if aPath(filePath) in paths:
                MessageDialog.showMessage('Already Opened.', 'This file is already opened in the project')
                raise TypeError('This File is already opened in the project')

        if not self.filePath:
            if self.userMacroDirPath is None:
                self._tempFile = tempfile.NamedTemporaryFile(suffix='.py')
                self._tempFile.close()
                self.filePath = self._tempFile.name
            else:
                if not os.path.exists(aPath(self.userMacroDirPath)):
                    from ccpn.ui.gui.widgets.MessageDialog import showYesNo

                    title, msg = "User macro path doesn't exist", "Do you want to create the folder?\n(no will revert to a temporary folder)"
                    openNew = showYesNo(title, msg)
                    if openNew:
                        # recursively create folder
                        os.makedirs(aPath(self.userMacroDirPath))

                if os.path.exists(aPath(self.userMacroDirPath)):
                    self._tempFile = tempfile.NamedTemporaryFile(prefix='macro_', dir=aPath(self.userMacroDirPath), suffix='.py')
                else:
                    self._tempFile = tempfile.NamedTemporaryFile(suffix='.py')

                # within AnalysisV3
                self._tempFile.close()
                self.filePath = self._tempFile.name

            try:
                with open(aPath(self.filePath), 'w'):
                    pass
            except (PermissionError, FileNotFoundError):
                getLogger().debug2('folder may be read-only')

        self._setupWidgets()
        self.openPath(self.filePath)
        self._setFileName()
        self._setToolBar()
        self._createWidgetSettings()
        self.setGuiNotifier(self.textEditor,
                            [GuiNotifier.DROPEVENT], [DropBase.URLS],
                            callback=self._processDroppedItems,
                            )

    def _setupWidgets(self):
        """Set up the main widgets
        """
        _spacing = 4
        self.mainWidget.getLayout().setSpacing(_spacing)
        self.mainWidget.getLayout().setContentsMargins(_spacing, _spacing, _spacing, _spacing)
        hGrid = 0
        self.toolbar = ToolBar(self.mainWidget, grid=(hGrid, 0), gridSpan=(1, 2), hAlign='l', hPolicy='preferred')
        hGrid += 1
        self.filePathLabel = Label(self.mainWidget, tipText='Macro filePath. ' + SaveMsgTipText, hAlign='l', grid=(hGrid, 0))
        self._filenameLineEdit = LineEdit(self.mainWidget, grid=(hGrid, 1), objectName=_filenameLineEdit)
        self._filenameLineEdit.hide()
        # setattr(self, _filenameLineEdit, LineEdit(self.mainWidget, grid=(hGrid, 1)))
        # getattr(self, _filenameLineEdit).hide()  #  this is used only to store and restore the widgets
        hGrid += 1
        # macro editing area
        self.textEditor = PyCodeEditor(self.mainWidget, application=self.application, grid=(hGrid, 0), acceptDrops=True, gridSpan=(1, 2))
        self.fileWatcher = self.textEditor.modes.get('FileWatcherMode')
        if self.fileWatcher:
            self.fileWatcher.on_state_changed(False)
        self.textEditor.focused_in.connect(self._focusInEvent)
        self.textEditor.textChanged.connect(self._textedChanged)

        ## editor pointers
        self._backend = self.textEditor.backend

    def _createWidgetSettings(self):
        hGrid = 0
        from ccpn.ui.gui.widgets import CompoundWidgets as CW
        self.safeProfileFileCheckBox = CW.CheckBoxCompoundWidget(self.settingsWidget,
                                                       labelText='Save Profiler to disk',
                                                       checked=self.macroSaveProfile, # True,
                                                       orientation='left', hAlign='left',
                                                       tipText='When running with the Profiler, save the stats to disk '
                                                               '(in the same dir as the running macro)',
                                                       grid=(hGrid, 0), gridSpan=(1, 1))
        hGrid += 1
        self.autoSaveCheckBox = CW.CheckBoxCompoundWidget(self.settingsWidget,
                                                       labelText='Autosave',
                                                       checked=self.macroAutosave,  # True,
                                                       orientation='left', hAlign='left',
                                                       tipText='Code written in the macro editor will automatically save',
                                                       grid=(hGrid, 0), gridSpan=(1, 1))
        self.autoSaveCheckBox.checkBox.stateChanged.connect(self.saveMacro)
        hGrid +=1
        sortingModes = PROFILING_SORTINGS.keys()
        sortingModesTt = [f'Sort by: {x}' for x in PROFILING_SORTINGS.values()]
        self.sortProfileFilePulldown = CW.PulldownListCompoundWidget(self.settingsWidget,
                                                                 labelText='Profiler output sorting',
                                                                 orientation='left', hAlign='left',
                                                                 tipText='When running with the Profiler, '
                                                                         'sort results by the selected option)',
                                                                texts= sortingModes,
                                                                toolTips = sortingModesTt,
                                                                     compoundKwds={'hAlign': 'left' },
                                                                grid=(hGrid, 0), gridSpan=(1, 1))
        showLinesText = ShowMaxLines.keys()
        showLinesTipText = [f'Show {x} of the total Lines' for x in showLinesText]
        hGrid += 1
        self.showLinesPulldown = CW.PulldownListCompoundWidget(self.settingsWidget,
                                                                     labelText='Profiler output limits  ',
                                                                     orientation='left', hAlign='left',
                                                                     tipText='When running with the Profiler, '
                                                                             'set how many line to show',
                                                                     texts=showLinesText,
                                                                     toolTips=showLinesTipText,
                                                                     compoundKwds={'hAlign':'left',},
                                                                     grid=(hGrid, 0), gridSpan=(1, 1))
        hGrid += 1

        self.warningLabel = Label(parent=self.settingsWidget,
                                  text="Settings only apply to this instance\nof the macro editor",
                                  vAlign='centre',
                                  grid=(hGrid, 0))

    def run(self):
        """Runs the macro.
        .. note::
            This method calls _run, and wraps it with notification and
            undo blocking.
        """
        self.application.ui.echoCommands([f'macroEditor.run(\'{os.path.basename(self.filePath)}\')'])
        with undoBlock():
            with notificationEchoBlocking():
                if self._isDirty():
                    self._runAsTemp()
                else:
                    self._run(self.filePath)
                    self.preferences.recentMacros.append(self.filePath)

    def _run(self, path):
        """Private method that runs the macro, called by run.

        .. warning::
            This function runs without any notification or undo blocking,
            and so should only be ran by users who wish to exploit that
            behaviour
        """
        if self._pythonConsole is not None:
            if self.autoOpenPythonConsole:
                self._openPythonConsoleModule()
            self._pythonConsole._runMacro(path)
        else:
            # Used when running the editor outside of Analysis. Run from an external IpythonConsole
            self._runOnTempIPythonConsole()

    def _runAsTemp(self):
        """Method to run unsaved macros by creating temporary files."""
        tempDir = tempfile.TemporaryDirectory(dir=ccpnMacroPath, prefix='TempMacro_')
        with tempfile.NamedTemporaryFile(suffix='.py', dir=tempDir.name, delete=False) as trf:
            trf.write(str.encode(self.textEditor.toPlainText()))
            trf.close()
            self._run(trf.name)
        tempDir.cleanup()

    def _getProfilerArgs(self):
        """
        Get the arguments to execute the profile command.
        More info https://ipython.readthedocs.io/en/stable/interactive/magics.html
        """
        sortMode = self.sortProfileFilePulldown.getText()
        saveToFile = self.safeProfileFileCheckBox.get()
        showLines = ShowMaxLines.get(self.showLinesPulldown.getText(), DefaultProfileLines)
        _i = f'-i'               # -i interactive
        _p = f'-p'               # -p profile
        _s = f'-s {sortMode}'    # -s sort keyword
        _l = f'-l {showLines}'   # -l limits keyword 0-1 float for % of output to show
        _f = f'-T {self.filePath}{ProfileSufixName}' if saveToFile else '' # -T filepath to dump the profile
        return [_i, _p, _s, _l, _f]

    def runProfiler(self):
        if self._pythonConsole is not None:
            if self.autoOpenPythonConsole:
                self._openPythonConsoleModule()
            if self.filePath:
                self.preferences.recentMacros.append(self.filePath)
                profileCommands = self._getProfilerArgs()
                try:
                    self._pythonConsole._runMacroProfiler(macroFile=self.filePath, extraCommands=profileCommands)
                except Exception as er:
                    getLogger().warning('Cannot run profiler. Fallback to normal execution.')
                    self._pythonConsole._runMacro(self.filePath)

        else:
            # Used when running the editor outside of Analysis. Run from an external IpythonConsole
            getLogger().warning('Profiler not implemented yet outside Assign')
            self._runOnTempIPythonConsole()

    def saveMacro(self):
        """
        Saves the text inside the textbox to a file, if a file path is not specified, a save file dialog
        appears for specification of the file path.
        """
        if not self.filePath:
            self.saveMacroAs()

        else:
            self._saveTextToFile()

    def saveMacroAs(self):
        """
        Opens a save file dialog and saves the text inside the textbox to a file specified in the dialog.
        """
        fType = '*.py' if not self._genericFile else None
        dialog = MacrosFileDialog(parent=self, acceptMode='save', selectFile=self.filePath, fileFilter=fType)
        dialog._show()
        filePath = dialog.selectedFile()
        if filePath is not None:
            if not filePath.endswith('.py') and not self._genericFile:
                filePath += '.py'
            if self.filePath != filePath:
                self._removeMacroFromCurrent()
                self._deleteTempFile()
            self.filePath = filePath
            self._saveTextToFile()
            self.openPath(filePath)
        else:
            self._checkFileStatus()

    def exportToPdf(self):
        self.textEditor.saveToPDF()

    def _toggleRunActions(self, enabled):
        actionNames = ['Run', 'Run-Profile', 'Add to shortcut']
        for actionName in actionNames:
            if action := self._getToolbarAction(actionName):
                action.setEnabled(enabled)

    def openPath(self, filePath):
        if filePath.endswith('.py'):
            self._genericFile = False
            self._toggleRunActions(True)
            self.textEditor._unloadStarSynthax()
            self.textEditor._loadPySynthax()

        elif filePath.endswith('.nef'):
            self.textEditor._unloadPySynthax()
            self.textEditor._loadStarSynthax()
            self._genericFile = True
            self._toggleRunActions(False)
        else:
            self._genericFile = True
            self._toggleRunActions(False)
            self.textEditor._unloadStarSynthax()
            self.textEditor._loadPySynthax()

        with open(aPath(filePath), 'r') as f:
            try:
                self.textEditor.textChanged.disconnect()
            except TypeError:
                getLogger().debug3('textEditor has no connected signals')
            self.textEditor.setUndoRedoEnabled(False)
            self.textEditor.clear()
            # for line in f.readlines():  # changed to f.read() instead of line by line.
            #     self.textEditor.insertPlainText(line)
            self.textEditor.insertPlainText(f.read())
            self.textEditor.setUndoRedoEnabled(True)
            # self.macroFile = f
            self._removeMacroFromCurrent()
            self.filePath = filePath
            self._preEditorText = self.textEditor.get()
            self._lastTimestp = None
            self._setCurrentMacro()
            self._setFileName()
            self.textEditor.textChanged.connect(self._textedChanged)
            self._lastSaved = self.textEditor.toPlainText()
            self.textEditor.syntax_highlighter.rehighlight()

    def revertChanges(self):
        # revert to initial text. If the initial state is empty. a pop-up will ask to confirm.
        proceed = True
        if not self._preEditorText and self.textEditor.get():
            proceed =  MessageDialog.showYesNoWarning('Revert to initial state',
                                                      'This file does not contain an initial state. '
                                                      'Reverting will cause to delete all text! Do you want to continue?')
        elif self._preEditorText != self.textEditor.get():
            proceed =  MessageDialog.showYesNoWarning('Revert to initial state',
                                                      'Do you want revert to the initial state and discard all changes?')
        if proceed:
            self.textEditor.clear()
            self.textEditor.insertPlainText(self._preEditorText)

    def _textedChanged(self, *args):
        if self.macroAutosave:
            self.saveMacro()
            self.textEditor._on_text_changed()
            self._lastTimestp = os.stat(self.filePath).st_mtime

    def _focusInEvent(self, *ags):
        self._checkFileStatus(*ags)

    def _checkFileStatus(self, *args):
        nf = 'File not found. Deleted or renamed externally. It will be recreated automatically'
        if not os.path.exists(self.filePath):
            getLogger().warning(nf)
            self.saveMacro()
            return
        if self.filePath is None:
            getLogger().warning(nf)
            self.saveMacro()
            return
        if os.path.exists(self.filePath):
            now = os.stat(self.filePath).st_mtime
            kc = "Keep current version"
            sa = "Save as..."
            rf = "Reload file"
            if self._lastTimestp:
                if now != self._lastTimestp:
                    self._lastTimestp = now
                    reply = MessageDialog.showMulti(title='Warning', message='Detected an external change to the file.'
                                                    , texts=[kc, sa, rf])
                    if kc in reply:
                        self.saveMacro()
                    if sa in reply:
                        self.saveMacroAs()
                    if rf in reply:
                        self._removeMacroFromCurrent()
                        self.openPath(self.filePath)
                return

    def _getToolBarDefs(self):

        toolBarDefs = (
            ('Open', od((
                ('text', 'Open'),
                ('toolTip', 'Open a Python File'),
                ('icon', Icon('icons/document_open_recent')),
                ('callback', self._openMacroFile),
                ('enabled', True)
                ))),
            ('Save', od((
                ('text', 'Save'),
                ('toolTip', 'Save file'),
                ('icon', Icon('icons/save')),
                ('callback', self.saveMacro),
                ('enabled', True)
                ))),
            ('Save as', od((
                ('text', 'SaveAs'),
                ('toolTip', 'Save file with a new name to a new location. '),
                ('icon', Icon('icons/saveAs')),
                ('callback', self.saveMacroAs),
                ('enabled', True)
                ))),
            ('Export', od((
                ('text', 'Export'),
                ('toolTip', 'Export code to PDF'),
                ('icon', Icon('icons/pdf')),
                ('callback', self.exportToPdf),
                ('enabled', True)
                ))),
            ('Add to shortcut', od((
                ('text', 'Add to shortcut'),
                ('toolTip', 'Add macro to a shortcut'),
                ('icon', Icon('icons/shortcut')),
                ('callback', self._addToShortcuts),
                ('enabled', True)
                ))),
            (),
            ('Undo', od((
                ('text', 'Undo'),
                ('toolTip', ''),
                ('icon', Icon('icons/undo')),
                ('callback', self.textEditor.undo),
                ('enabled', True)
                ))),
            ('Redo', od((
                ('text', 'Redo'),
                ('toolTip', ''),
                ('icon', Icon('icons/redo')),
                ('callback', self.textEditor.redo),
                ('enabled', True)
                ))),
            ('Revert', od((
                ('text', 'Revert'),
                ('toolTip', 'Revert all changes to initial state'),
                ('icon', Icon('icons/revert4')),
                ('callback', self.revertChanges),
                ('enabled', True)
                ))),
            (),
            ('Run', od((
                ('text', 'Run'),
                ('toolTip', 'Run the macro in the IpythonConsole.\nShortcut: cmd(ctrl)+r'),
                ('icon', Icon('icons/play')),
                ('callback', self.run),
                ('enabled', True),
                ('shortcut', '⌃r')
                ))),
            ('Run-Profile', od((
                ('text', 'Run with a profiler'),
                ('toolTip', 'Run the macro in the IpythonConsole with a profiler.\nShortcut: cmd(ctrl)+p'),
                ('icon', Icon('icons/profiler')),
                ('callback', self.runProfiler),
                ('enabled', True),
                ('shortcut', '⌃t')
                ))),
            )
        return toolBarDefs

    def _setToolBar(self):
        for v in self._getToolBarDefs():
            if len(v) == 2:
                if isinstance(v[1], od):
                    action = Action(self, **v[1])
                    action.setObjectName(v[0])
                    self.toolbar.addAction(action)
            else:
                self.toolbar.addSeparator()

    def _addToShortcuts(self):
        if self.application:
            from ccpn.ui.gui.popups.ShortcutsPopup import ShortcutsPopup

            sp = ShortcutsPopup(self, mainWindow=self.mainWindow)
            sp.addToFirstAvailableShortCut(self.filePath)
            sp.exec()
        else:
            MessageDialog.showMessage('Set shortcuts', 'This option is available only within Analysis')

    def _getToolbarAction(self, objectName):
        for a in self.toolbar.actions():
            if a.objectName() == objectName:
                return a

    def _processDroppedItems(self, data):
        """
        CallBack for Drop events
        """
        urls = data.get('urls', [])
        if len(urls) == 1:
            filePath = urls[0]
            if len(self.textEditor.get()) > 0:
                ok = MessageDialog.showYesNoWarning('Open new macro', 'Replace the current macro?')
                if ok:
                    if self.filePath != filePath:
                        self._removeMacroFromCurrent()
                        self._deleteTempFile()
                    self.openPath(filePath)
                    self._setFileName()
                else:
                    return
            else:
                if self.filePath != filePath:
                    self._removeMacroFromCurrent()
                    self._deleteTempFile()
                self.openPath(filePath)
                self._setFileName()
        else:
            MessageDialog.showMessage('', 'Drop only a file at the time')

    def _createTemporaryFile(self, name=None):
        if name is None:
            dateTime = datetime.datetime.now().strftime("%y-%m-%d-%H:%M:%S")
            tempName = f'Macro{dateTime}'
            name = tempName
        filePath = f'{self.application.tempMacrosPath}/{name}'
        if filePath:
            if not filePath.endswith('.py'):
                filePath += '.py'
            try:
                with open(filePath, 'w') as f:
                    f.write('')
            except (PermissionError, FileNotFoundError):
                getLogger().debug2('folder may be read-only')

        self.filePath = filePath
        return filePath

    def _openTemp(self, path, line):
        """
        used for navigating to error in the macro.
        """
        editor = self.textEditor
        editor.file.restore_cursor = False
        editor.file.open(path)
        TextHelper(editor).goto_line(line)
        editor.show()
        self._editor_windows.append(editor)

    def _runOnTempIPythonConsole(self):
        console = PyInteractiveConsole()
        console.open_file_requested.connect(self._openTemp)
        console.start_process(sys.executable, [os.path.join(os.getcwd(), self.filePath)])
        console.show()

    def _openPythonConsoleModule(self):
        from ccpn.ui.gui.modules.PythonConsoleModule import PythonConsoleModule

        if self.mainWindow.pythonConsoleModule is None:  # No pythonConsole module detected, so create one.
            self.mainWindow.moduleArea.addModule(PythonConsoleModule(self.mainWindow), 'bottom')

    def _deleteTempMacro(self, filePath):
        if os.path.exists(filePath):
            os.remove(filePath)
            self.filePath = None
        else:
            getLogger().debug("Trying to remove a temporary Macro file which does not exist")

    def _saveTextToFile(self):

        if not self.textEditor.get() and self._lastSaved:
            answer = MessageDialog.showMulti('You’re about to save an empty macro that was previously written.', 'Do you want to continue?', ['Clear Only', 'Save Empty', 'Undo'])
            if answer == 'Clear Only':
                return
            if answer == 'Undo':
                self.textEditor.undo()
                return

        sucess = False
        if filePath := self.filePath:
            if self._genericFile:
                try:
                    with open(aPath(filePath), 'w') as f:
                        f.write(self.textEditor.toPlainText())
                        sucess = True
                except (PermissionError, FileNotFoundError):
                    getLogger().debug2('folder may be read-only')
                    sucess = False
            else:
                if not filePath.endswith('.py'):
                    filePath += '.py'
                try:
                    with open(aPath(filePath), 'w') as f:
                        f.write(self.textEditor.toPlainText())
                        sucess = True

                except (PermissionError, FileNotFoundError):
                    getLogger().debug2('folder may be read-only')
                    sucess = False

        if self.filePath:
            self._lastSaved = self.textEditor.toPlainText()
            self._lastTimestp = os.stat(self.filePath).st_mtime
            self._setFileName()

    def _openMacroFile(self):
        """
        Opens a file dialog box at the macro path specified in the application preferences and loads the
        contents of the macro file into the textbox.
        """
        fType = '*.py'
        dialog = MacrosFileDialog(parent=self, acceptMode='open', fileFilter=fType)
        dialog._show()

        filePath = dialog.selectedFile()
        self.openPath(filePath)
        self._setFileName()

    def _setFileName(self):
        if self.filePath:
            self._filenameLineEdit.set(str(self.filePath))
            lastTime = self._lastTimestp
            self.filePathLabel.set(f'{self.filePath}')
            if lastTime:
                timestamp = datetime.datetime.fromtimestamp(lastTime).strftime('%d/%m/%y %H:%M:%S')
                saveMessage = f'Changes saved (Last at {timestamp})'
                self.filePathLabel.set(f'{self.filePath}\n{saveMessage}')

    def _isInCurrent(self, filePath):
        if self.current:
            if filePath in self.current.macroFiles:
                return True
        return False

    def _setCurrentMacro(self):
        if self.current:
            self.current.macroFiles += (self.filePath,)

    def _removeMacroFromCurrent(self):
        if self._isInCurrent(self.filePath):
            self.current.removeMacroFile(self.filePath)

    def _isDirty(self):
        if self._preEditorText != self.textEditor.get():
            return self._lastSaved != self.textEditor.get()
        return False

    def _deleteTempFile(self):
        if self._tempFile and self._tempFile.name == self.filePath:
            if self.textEditor.get() == '':  # delete empty temp
                if os.path.exists(self.filePath):
                    os.remove(self.filePath)

    def restoreWidgetsState(self, **widgetsState):
        """
        Restore the gui params. To Call it: _setParams(**{"variableName":"value"})
        :param widgetsState:
        """
        # self._setNestedWidgetsAttrToModule()
        # widgetsState = od(sorted(widgetsState.items()))
        # for variableName, value in widgetsState.items():
        #     try:
        #         widget = getattr(self, str(variableName))
        #         if variableName == _filenameLineEdit:
        #             if isinstance(widget, LineEdit):
        #                 if value is not None and value != '':
        #                     if self.filePath != value:
        #                         self._removeMacroFromCurrent()
        #                         self._deleteTempFile()
        #                     self.openPath(value)
        #                 continue
        #         else:
        #             widget._setSavedState(value)
        #
        #     except Exception as e:
        #         getLogger().debug('Impossible to restore %s value for %s. %s' % (variableName, self.name(), e))
        if self._restore:
            wDict = self._setNestedWidgetsAttrToModule()
            widgetsState = od(sorted(widgetsState.items()))
            for variableName, value in widgetsState.items():
                try:
                    widget = wDict.get(str(variableName))
                    if variableName and variableName.endswith(_filenameLineEdit):
                        if isinstance(widget, LineEdit):
                            if value is not None and value != '':
                                if self.filePath != value:
                                    self._removeMacroFromCurrent()
                                    self._deleteTempFile()
                                self.openPath(value)
                            continue
                    else:
                        widget._setSavedState(value)

                except Exception as e:
                    getLogger().debug('Impossible to restore %s value for %s. %s' % (variableName, self.name(), e))

    def _closeModule(self):
        """Re-implementation of closeModule"""
        if self._isDirty():
            ok = MessageDialog.showYesNoWarning('Close Macro', 'Do you want save?')
            if ok:
                self.saveMacro()
        self._deleteTempFile()
        self._removeMacroFromCurrent()
        try:
            self.textEditor.close()
        except Exception as err:
            getLogger().warning(f'error closing macro editor {err}')

        widgetsState = super().widgetsState
        # widgetsState[_filenameLineEdit] = '' # don't save the filename for next time you open a "last-seen" module

        self.area._seenModuleStates[self.className] = {MODULENAME: self.moduleName, WIDGETSTATE: widgetsState}
        self._includeInLastSeen = False # otherwise overrides the saved state.
        self._lastSaved = None
        super()._closeModule()


if __name__ == '__main__':
    from PyQt5 import QtWidgets
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.widgets.CcpnModuleArea import CcpnModuleArea


    app = TestApplication()
    win = QtWidgets.QMainWindow()

    moduleArea = CcpnModuleArea(mainWindow=None)
    tf = '/Users/luca/AnalysisV3/src/python/ccpn/ui/gui/widgets/TestModule.py'
    module = MacroEditor(mainWindow=None, filePath=None)

    moduleArea.addModule(module)

    win.setCentralWidget(moduleArea)
    win.resize(1000, 500)
    win.setWindowTitle(module.moduleName)
    win.show()

    app.start()
    win.close()

    if sys.platform[:3].lower() == 'win':
        os._exit(0)
