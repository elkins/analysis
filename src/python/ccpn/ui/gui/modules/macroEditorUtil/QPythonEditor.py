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
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2020-05-15 09:30:25 +0000 (Fri, May 15, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

import sys
from PyQt5 import QtGui, QtWidgets
from PyQt5 import QtPrintSupport

from ccpn.ui.gui.modules.macroEditorUtil.StarPyQodeModes import StarHighlighter
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.FileDialog import MacrosFileDialog
from pyqode.python.widgets import PyCodeEditBase
from pyqode.core.api import ColorScheme
# from pyqode.python.widgets import PyCodeEdit # DO NOT  USE/IMPORT THIS - There is a bug in the SearchAndReplace panel that prevents to use the PyCharm Debugger.
from pyqode.python import modes as pymodes
from pyqode.python import panels as pypanels
from ccpn.ui.gui.modules.macroEditorUtil import MacroEditorServer
from ccpn.ui.gui.modules.macroEditorUtil import MacroEditorNativeServer, StarLexer
from pyqode.core import modes
from pyqode.core import panels
from pyqode.core import api
from ccpn.ui.gui.modules.macroEditorUtil.workers import CcpnQuickDocPanel, CcpnCalltipsMode
from pyqode.core.modes.code_completion import CodeCompletionMode
from ccpn.ui.gui.modules.macroEditorUtil.CompletionProviders import CcpnNameSpacesProvider
from pyqode.core.cache import Cache
from pyqode.python.backend.workers import defined_names
from pygments.lexers import load_lexer_from_file


marginColour = QtGui.QColor('lightgrey')
marginPosition = 100
SEL_BACKGROUND_COLOUR = (255, 219, 179)

class PyCodeEditor(PyCodeEditBase, Base):

    useNativeCompletion = False # use the original completion without Ccpn Namespace
    mimetypes = ['text/x-python']

    def __init__(self, parent=None, application=None, interpreter=sys.executable, **kwds):

        if self.useNativeCompletion:
            serverScript = MacroEditorNativeServer.__file__
        else:
            serverScript = MacroEditorServer.__file__

        super().__init__(parent, create_default_actions=True)
        self._starHighlighter = None
        self.modes.append(modes.SmartBackSpaceMode())
        # install those modes first as they are required by other modes/panels
        self.modes.append(modes.OutlineMode(defined_names))

        # panels
        # Do Not add  the SearchAndReplace Panel. There is a bug in it that prevents to use the PyCharm Debugger.
        # self.panels.append(panels.FoldingPanel()) There is  a bug in this panel creating lots of warning as you type.
        self.panels.append(panels.LineNumberPanel())
        self.panels.append(panels.CheckerPanel())
        self.panels.append(panels.GlobalCheckerPanel(),  panels.GlobalCheckerPanel.Position.RIGHT)
        self.add_separator()
        # modes
        # generic

        self.modes.append(modes.ExtendedSelectionMode())
        self.modes.append(modes.CaseConverterMode())
        self.modes.append(modes.CaretLineHighlighterMode())
        self.modes.append(modes.FileWatcherMode())
        self.modes.append(modes.RightMarginMode())
        self.modes.append(modes.ZoomMode())
        self.modes.append(modes.SymbolMatcherMode())
        self.modes.append(modes.CodeCompletionMode())
        self.modes.append(modes.OccurrencesHighlighterMode())
        self.modes.append(modes.SmartBackSpaceMode())
        # python specifics
        self.modes.append(pymodes.PyAutoIndentMode())
        self.modes.append(pymodes.PyAutoCompleteMode())
        self.modes.append(pymodes.PyFlakesChecker())
        self.modes.append(pymodes.PEP8CheckerMode())
        self.modes.append(pymodes.CalltipsMode())
        self.modes.append(pymodes.PyIndenterMode())
        self.modes.append(pymodes.GoToAssignmentsMode())
        self.modes.append(pymodes.CommentsMode())
        self.pythonSyntax = None
        # self.pythonSyntax = pymodes.PythonSH(self.document(), color_scheme=ColorScheme('qt'))
        # self.modes.append(self.pythonSyntax)
        # self.syntax_highlighter.fold_detector = PythonFoldDetector()
        self.panels.append(pypanels.QuickDocPanel(), api.Panel.Position.BOTTOM)
        self.panels.append(panels.EncodingPanel(), api.Panel.Position.TOP)
        self.panels.append(panels.ReadOnlyPanel(), api.Panel.Position.TOP)
        self.setLineWrapMode(self.NoWrap)

        Base._init(self, **kwds)
        self.rightMarginMode = self.modes.get('RightMarginMode')
        if self.rightMarginMode:
            self.rightMarginMode.color = marginColour
            self.rightMarginMode.position = marginPosition

        self.application = application
        self.completionMode = self.modes.get(CodeCompletionMode.__name__)
        self.maxCompletionWaiting = 1 # seconds before aborting a completion request (avoid long waiting)
        if self.application and not self.useNativeCompletion:
            # self.backend.stop()
            self.completionMode.request_completion = self._requestCompletion
            self.completionMode._insert_completion = self._insertCompletion
        else:
            self.backend.start(serverScript, interpreter, args=None, reuse=False)

        # Add Custom Ccpn Panel/models
        self.docPanel = CcpnQuickDocPanel()
        self.panels.append(self.docPanel, api.Panel.Position.BOTTOM)
        self.modes.append(CcpnCalltipsMode())

        # TODO add signal to detect a colourScheme change and modify the palette
        # QtWidgets.QApplication.instance()._sigPaletteChanged.connect(self._checkPalette)


    def _init_style(self):
        """ Refactor to keep consistent with Ccpn style """
        self._background = QtGui.QColor('white')
        self._foreground = QtGui.QColor('black')
        self._whitespaces_foreground = QtGui.QColor('light gray')
        app = QtWidgets.QApplication.instance()
        self._sel_background = QtGui.QColor(*SEL_BACKGROUND_COLOUR)
        self._sel_foreground = app.palette().highlightedText().color()
        self._font_size = 10
        self.font_name = ""

    def _loadStarSynthax(self):
        if self._starHighlighter is None:
            self._starLexer = load_lexer_from_file(StarLexer.__file__, lexername='StarLexer')
            self._starHighlighter = StarHighlighter(self.document(), self._starLexer, style='friendly')
            self.modes.append(self._starHighlighter)
        else:
            modeNames = [mo.name for mo in self.modes]
            if self._starHighlighter.name not in modeNames:
                self.modes.append(self._starHighlighter)

        self._starHighlighter.rehighlight()

    def _unloadStarSynthax(self):
        if self._starHighlighter is not None:
            modeNames = [mo.name for mo in self.modes]
            if self._starHighlighter.name in modeNames:
                self.modes.remove(self._starHighlighter.name)

    def _loadPySynthax(self):
        if self.pythonSyntax is None:
            self.pythonSyntax = pymodes.PythonSH(self.document(), color_scheme=ColorScheme('qt'))
            self.modes.append(self.pythonSyntax)
        else:
            modeNames = [mo.name for mo in self.modes]
            if self.pythonSyntax.name not in modeNames:
                self.modes.append(self.pythonSyntax)

        self.pythonSyntax.rehighlight()

    def _unloadPySynthax(self):
        if self.pythonSyntax is not None:
            modeNames = [mo.name for mo in self.modes]
            if self.pythonSyntax.name in modeNames:
                self.modes.remove(self.pythonSyntax.name)

    def _requestCompletion(self, *args, **kwargs):
        """
        re-implemetation of completion to insert ccpn Namespaces from application
        without sending requests to threads.
        """
        from ccpn.core.lib.ContextManagers import Timeout as timeout
        completionMode = self.completionMode
        line = completionMode._helper.current_line_nbr()
        column = completionMode._helper.current_column_nbr() - len(completionMode.completion_prefix)
        same_context = (line == completionMode._last_cursor_line and column == completionMode._last_cursor_column)
        if same_context:
            if completionMode._request_id - 1 == completionMode._last_request_id:
                completionMode._show_popup()
            else:
                # same context but result not yet available
                pass
            return True
        else:
            try:
                code = completionMode.editor.toPlainText()
                line = line
                column = column
                path = completionMode.editor.file.path
                encoding = completionMode.editor.file.encoding
                prefix = completionMode.completion_prefix
                request_id = completionMode._request_id
                results = [(line, column, request_id), []]
                with timeout(seconds=self.maxCompletionWaiting,
                             timeoutMessage='MacroEditor: Completion aborted\n',
                             loggingType='debug3'):
                    cw = CcpnNameSpacesProvider()
                    completions = cw.complete(code, line, column, path, encoding, prefix)
                    results = [(line, column, request_id), completions]
            except (Exception, TimeoutError) as es:
                return False
            else:
                completionMode._last_cursor_column = column
                completionMode._last_cursor_line = line
                completionMode._request_id += 1
                completionMode._on_results_available(results)
                return True

    def _insertCompletion(self, completion):
        completionMode = self.completionMode
        cursor = completionMode._helper.word_under_cursor(select_whole_word=False)
        cursor.insertText(completion)
        self.setTextCursor(cursor)
        if self.docPanel.isVisible():
            self.docPanel._on_action_quick_doc_triggered()

    def get(self):
        return self.toPlainText()

    def set(self, value):
        self.setPlainText(value)

    def saveToPDF(self, fileName=None):
        fType = '*.pdf'
        dialog = MacrosFileDialog(parent=self, acceptMode='save', selectFile=fileName, fileFilter=fType)
        dialog.exec()
        urls = dialog.selectedUrls()
        filenames = [url.toLocalFile() for url in urls]
        if len(filenames)>0:
            printer = QtPrintSupport.QPrinter(QtPrintSupport.QPrinter.HighResolution)
            printer.setPageSize(QtPrintSupport.QPrinter.A4)
            printer.setColorMode(QtPrintSupport.QPrinter.Color)
            printer.setOutputFileName(filenames[0])
            self.document().print_(printer)

    def enterEvent(self, event):
        self.setFocus()
        super(PyCodeEditor, self).enterEvent(event)

    def close(self, clear=False):

        """
        Closes the editor, stops the backend and removes any installed
        mode/panel.

        This is also where we cache the cursor position.

        :param clear: True to clear the editor content before closing.
        """
        if self._tooltips_runner:
            self._tooltips_runner.cancel_requests()
            self._tooltips_runner = None
        self.decorations.clear()
        self.backend.stop()
        Cache().set_cursor_position(
                self.file.path, self.textCursor().position())


if __name__ == '__main__':
  from ccpn.ui.gui.widgets.Application import TestApplication
  from ccpn.ui.gui.popups.Dialog import CcpnDialog

  app = TestApplication()
  popup = CcpnDialog(windowTitle='Test widget', setLayout=True)
  editor = PyCodeEditor(popup, grid=[0,0])
  editor.set('print("Hello")')
  editor.get()


  popup.show()
  popup.raise_()
  app.start()



