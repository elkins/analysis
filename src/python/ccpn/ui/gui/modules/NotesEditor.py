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
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2025-01-06 17:41:27 +0000 (Mon, January 06, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets
from ccpn.core.Note import Note
from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar
from ccpn.core.lib.WeakRefLib import WeakRefDescriptor
from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.widgets.PulldownListsForObjects import NotePulldown
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.MainWindow import MainWindow
from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier
from ccpn.util.Logging import getLogger


logger = getLogger()

DEFAULTSPACING = (0, 0)
DEFAULTMARGINS = (0, 0, 0, 0)  # l, t, r, b


class NotesEditorModule(CcpnModule):
    """
    This class implements the module for editing the NotesList.
    """
    includeSettingsWidget = False
    maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    settingsPosition = 'top'

    className = 'NotesEditorModule'
    attributeName = 'notes'  # self.project.notes
    _includeInLastSeen = False

    note: Note | None = WeakRefDescriptor()
    noWidget: NotePulldown | None = WeakRefDescriptor()

    def __init__(self, mainWindow: MainWindow | None = None,
                 name: str = 'Notes Editor',
                 note: Note | None = None, selectFirstItem: bool = False):
        """
        Initialise the widgets for the module.

        :param mainWindow: The main window instance.
        :type mainWindow: QtWidgets.QMainWindow | None
        :param name: The name of the module.
        :type name: str
        :param note: The note to be selected initially.
        :type note: Note | None
        :param selectFirstItem: Whether to select the first item initially.
        :type selectFirstItem: bool
        """
        super().__init__(mainWindow=mainWindow, name=name)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            # defined as descriptor in superclass, so will default to None
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        self.note = None

        # set up the widgets/notifiers
        self._setupWidgets()
        self._setNotifiers()

        if note is not None:
            self.selectNote(note)
        elif selectFirstItem:
            self.noWidget.selectFirstItem()

    def _setupWidgets(self) -> None:
        """
        Set up the widgets in module.
        """
        self._widget = ScrollableFrame(self.mainWidget, setLayout=True, showBorder=False,
                                       scrollBarPolicies=('never', 'never'), spacing=DEFAULTSPACING,
                                       margins=DEFAULTMARGINS,
                                       grid=(2, 1))
        self._widgetScrollArea = self._widget._scrollArea

        row = 0
        Spacer(self._widget, 5, 5,
               QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
               grid=(row, 0), gridSpan=(1, 1))

        row += 1
        self.noWidget = NotePulldown(parent=self._widget,
                                     mainWindow=self.mainWindow, default=None,
                                     grid=(row, 0), gridSpan=(1, 1), minimumWidths=(0, 100),
                                     showSelectName=True,
                                     sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                     callback=self._selectionPulldownCallback)

        row += 1
        Spacer(self._widget, 5, 5,
               QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
               grid=(row, 0), gridSpan=(1, 1))

        #~~~~~~~~~~ define noteWidget box to contain main editing

        row += 1
        self.noteWidget = Frame(self._widget, grid=(row, 0), gridSpan=(4, 5), setLayout=True)
        self.noteWidget.hide()

        nRow = 1
        self.label1 = Label(self.noteWidget, text='name', grid=(nRow, 0), vAlign='c', hAlign='r')
        self.lineEdit1 = LineEdit(self.noteWidget, grid=(nRow, 1), gridSpan=(1, 2), vAlign='top', textAlignment='l',
                                  backgroundText='> Enter name <')
        self.lineEdit1.editingFinished.connect(self._applyNote)  # *1

        nRow += 1
        self.labelComment = Label(self.noteWidget, text='comment', grid=(nRow, 0), vAlign='c', hAlign='r')
        self.lineEditComment = LineEdit(self.noteWidget, grid=(nRow, 1), gridSpan=(1, 2), vAlign='top',
                                        textAlignment='l', backgroundText='> Optional <')
        self.lineEditComment.editingFinished.connect(self._applyNote)  # *1

        nRow += 1
        Spacer(self.noteWidget, 5, 5,
               QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed,
               grid=(nRow, 3), gridSpan=(1, 1))

        nRow += 1
        self.textBox = TextEditor(self.noteWidget, grid=(nRow, 0), gridSpan=(1, 6))
        self.textBox.editingFinished.connect(self._applyNote)  # *1

        # NOTE: *1 Automatically save the note when it loses the focus.
        #       Otherwise, is in danger of losing all the carefully written notes if you
        #       forget to press an apply button!
        #~~~~~~~~~~ end of noteWidget box

        row += 1
        # this spacer is expanding, will fill the space when the textbox is invisible
        Spacer(self._widget, 5, 5,
               QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding,
               grid=(row, 4), gridSpan=(1, 1))

    def _processDroppedItems(self, data: dict) -> None:
        """
        CallBack for Drop events.

        :param data: The data from the drop event.
        :type data: dict
        """
        pids = data.get('pids', [])
        from ccpn.ui.gui.lib.MenuActions import _openItemObject

        objs = [self.project.getByPid(pid) for pid in pids]

        selectableObjects = [obj for obj in objs if isinstance(obj, Note)]
        others = [obj for obj in objs if not isinstance(obj, Note)]
        if len(selectableObjects) > 0:
            self.selectNote(selectableObjects[0])
            _openItemObject(self.mainWindow, selectableObjects[1:])
        else:
            from ccpn.ui.gui.widgets.MessageDialog import showYesNo

            othersClassNames = list(set([obj.className for obj in others]))
            if len(othersClassNames) > 0:
                if len(othersClassNames) == 1:
                    title, msg = 'Dropped wrong item.', 'Do you want to open the %s in a new module?' % ''.join(
                            othersClassNames)
                else:
                    title, msg = 'Dropped wrong items.', 'Do you want to open items in new modules?'
                openNew = showYesNo(title, msg)
                if openNew:
                    _openItemObject(self.mainWindow, others)

    def selectNote(self, note: Note | None = None) -> None:
        """
        Manually select a Note from the pullDown.

        :param note: The note to be selected.
        :type note: Note | None
        """
        if not self.noWidget:
            return
        if note is None:
            # logger.warning('select: No Note selected')
            # raise ValueError('select: No Note selected')
            self.noWidget.selectFirstItem()
        else:
            if not isinstance(note, Note):
                logger.warning('select: Object is not of type Note')
                raise TypeError('select: Object is not of type Note')
            else:
                if note.pid in self.noWidget.textList:
                    self.note = note
                    self.noWidget.select(self.note.pid)

    def _setNotifiers(self) -> None:
        """
        Set a Notifier to call when a note is created/deleted/renamed/changed.
        Rename calls on name, change calls on any other attribute.
        """
        self.setNotifier(self.project,
                         [Notifier.CREATE, Notifier.DELETE, Notifier.RENAME, Notifier.CHANGE],
                         Note.__name__,
                         self._updateCallback)
        self.setGuiNotifier(self.mainWidget,
                            [GuiNotifier.DROPEVENT], [DropBase.PIDS],
                            self._processDroppedItems)

    def _applyNote(self) -> None:
        """
        Apply changes to the current note.

        Temporarily disables notifiers and groups changes into a single undo/redo event.
        """
        if not self.note:
            return

        self.setBlankingAllNotifiers(True)  # Disable notifiers while updating the object
        name: str = self.lineEdit1.text()
        text: str = self.textBox.toPlainText()
        comment: str = self.lineEditComment.text()

        try:
            if name != self.note.name or text != self.note.text or comment != self.note.comment:
                with undoBlockWithoutSideBar():
                    if name != self.note.name:
                        self.note.rename(name)
                    self.note.text = text
                    self.note.comment = comment

        except Exception as es:
            # Revert changes to prevent errors on loseFocus which also fires editingFinished
            self.lineEdit1.setText(self.note.name)
            showWarning('', str(es))

        self.noWidget.select(self.note.pid)
        self.setBlankingAllNotifiers(False)

    def _selectionPulldownCallback(self, item: str) -> None:
        """
        Notifier callback for selecting a note from the dropdown menu.

        :param item: The identifier of the selected note.
        :type item: str
        """
        self.note = self.project.getByPid(item)
        if self.note is not None:
            self._update(self.note)
        else:
            self.noteWidget.hide()

    def _updateCallback(self, data: dict) -> None:
        """
        Notifier callback for updating the module when a note is created, deleted, renamed, or changed.

        :param data: The data containing the updated notes list.
        :type data: dict
        """
        thisNoteList = getattr(data[Notifier.THEOBJECT], self.attributeName)  # Get the notes list

        if self.note in thisNoteList:
            self._update(self.note)
        else:
            self.noteWidget.hide()

    def _update(self, note: Note) -> None:
        """
        Update the note widgets with the current note's details.

        :param note: The note object to update the widgets with.
        :type note: Note
        """
        self.textBox.setText(note.text)
        self.lineEdit1.setText(note.name)
        self.lineEditComment.setText(note.comment or '')
        self.noteWidget.show()
        self.show()

    def _deleteNote(self) -> None:
        """
        Delete the current note.
        """
        if self.note:
            self.note.delete()
