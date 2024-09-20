"""
Module Documentation here
TODO More decision making on functionalities and subsequent code cleaning
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Morgan Hayward, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Daniel Thompson",
               "Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Luca Mureddu $"
__dateModified__ = "$dateModified: 2024-07-30 17:22:58 +0100 (Tue, July 30, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-03-30 11:28:58 +0100 (Thu, March 30, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from re import finditer
from collections import Counter, OrderedDict
from itertools import zip_longest
import copy
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QDataStream, Qt, QVariant
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.ListWidget import ListWidget
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.Font import getTextDimensionsFromFont
from ccpn.ui.gui.widgets.Frame import Frame, ScrollableFrame
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Tabs import Tabs
from ccpn.core.lib.ContextManagers import undoBlock
from ccpn.ui.gui.lib.ChangeStateHandler import changeState
from ccpn.util.Constants import INTERNALQTDATA
from ccpn.ui.gui.guiSettings import getColours, BORDERFOCUS, BORDERNOFOCUS
from ccpn.ui.gui.popups.AttributeEditorPopupABC import getAttributeTipText


DEFAULTSPACING = (3, 3)
TABMARGINS = (1, 10, 10, 1)  # l, t, r, b
ZEROMARGINS = (0, 0, 0, 0)  # l, t, r, b


def camelCaseSplit(identifier):
    matches = finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return ' '.join([m.group(0) for m in matches])


class FeedbackFrame(Frame):
    def __init__(self, *args, **kwds):
        super().__init__(setLayout=True, *args, **kwds)
        self.highlight(False)

    def highlight(self, enable):

        if enable:
            # GST rgb(88,88,192) is 'ccpn purple' which I guess should be defined somewhere
            self.setStyleSheet('FeedbackFrame {border: 2px solid rgb(88,88,192)}')
        else:
            # this is background grey which I guess should be defined somewhere
            self.setStyleSheet('FeedbackFrame {border: 2px solid transparent}')


class OrderedListWidgetItem(QtWidgets.QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __lt__(self, other):
        self_data = self.data(_ListWidget._searchRoleIndex)
        other_data = other.data(_ListWidget._searchRoleIndex)
        if not all([self_data, other_data]):
            return False
        return self_data < other_data


class DefaultItemFactory:

    def __init__(self, roleMap=None):

        self._roleMap = {}

        if roleMap is not None:
            for role in roleMap.values():
                if role == QtCore.Qt.UserRole:
                    raise RuntimeError('role QtCore.Qt.UserRole is reserved for ccpn use a value > QtCore.Qt.UserRole ')

            self._roleMap.update(roleMap)

        self._roleMap['USER_ROLE'] = QtCore.Qt.UserRole

    def instantiateItem(self, item, parent):
        return None if isinstance(item, QtWidgets.QListWidgetItem) else QtWidgets.QListWidgetItem(item, parent)

    def ensureItem(self, item, parent=None):

        result = self.instantiateItem(item, parent)

        if result is None:
            result = item

            if parent is not None:
                result.setParent(parent)

        return result

    # GST from https://wiki.python.org/moin/PyQt/Handling%20Qt%27s%20internal%20item%20MIME%20type
    # note the original has a bug! the items {} is declared too high and is aliased, this only appears
    # when multiple items are dragged
    def decodeDragData(self, bytearray):

        data = OrderedDict()

        ds = QDataStream(bytearray)
        while not ds.atEnd():
            item = {}
            row = ds.readInt32()
            column = ds.readInt32()
            key = (row, column)

            data[key] = item
            map_items = ds.readInt32()
            for i in range(map_items):
                key = ds.readInt32()

                value = QVariant()
                ds >> value
                item[Qt.ItemDataRole(key)] = value

        return data

    def createItemsFromMimeData(self, data):
        data = self.decodeDragData(data)

        result = []
        for item in data.values():
            string = item[0].value()
            del item[0]
            result.append(self.createItem(string, data=item))

        return result

    def createItem(self, string, data=None, parent=None):
        if data is None:
            data = []

        result = self.ensureItem(string, parent=parent)
        for role, value in data.items():
            result.setData(role, value)

        return result


class OrderedListWidgetItemFactory(DefaultItemFactory):

    def __init__(self):
        super().__init__({_ListWidget._searchRole: _ListWidget._searchRoleIndex})

    def instantiateItem(self, item, parent):
        return None if isinstance(item, OrderedListWidgetItem) else OrderedListWidgetItem(item, parent)


class _ListWidget(ListWidget):
    """Subclassed for dropEvent"""

    _roles = ('Left', 'Right')

    _searchRole = 'SEARCH'
    _searchRoleIndex = QtCore.Qt.UserRole + 1

    def __init__(self, *args, dragRole=None, feedbackWidget=None, rearrangeable=False, itemFactory=None,
                 sorted=False, emptyText=None, **kwds):

        super().__init__(*args, **kwds)

        if dragRole.capitalize() not in self._roles:
            raise ValueError('position must be one of left or right')

        self._rearrangeable = rearrangeable
        self.setDropIndicatorShown(self._rearrangeable)

        self._dragRole = dragRole
        clonedRoles = list(self._roles)
        clonedRoles.remove(self._dragRole.capitalize())
        self._oppositeRole = clonedRoles[0]

        self._emptyText = emptyText

        self._feedbackWidget = feedbackWidget
        self._partner = None

        self.itemDoubleClicked.connect(self._itemDoubleClickedCallback)
        self.setSortingEnabled(sorted)

        self._itemFactory = itemFactory
        if self._itemFactory is None:
            self._itemFactory = DefaultItemFactory()

        self._feedbackWidget.highlight(False)

    def startDrag(self, *args, **kwargs):
        super().startDrag(*args, **kwargs)

    def setTexts(self, texts, clear=True, data=None):
        # could use a sentinel for data
        if data is None:
            data = []

        if clear:
            self.clear()
            self.cleared.emit()

        if len(texts) < len(data):
            raise ValueError('more data than items!')

        self.insertItems(0, texts)  #this avoids the notification leakage of adding one at the time

        # for text, datum in zip_longest(texts, data, fillvalue={}):
        #     item = self._itemFactory.createItem(str(text), datum)
        #     self.addItem(item)

    @staticmethod
    def _buildItemData(objects, data):

        data = copy.deepcopy(data)
        for i, obj in enumerate(objects):

            if i < len(data):
                data[i]['USER_ROLE'] = id(obj)
            else:
                data.append({'USER_ROLE': id(obj)})

        return data

    def setObjects(self, objects, name='pid', data=None):
        # could use a sentinel for data
        if data is None:
            data = []

        self.clear()
        self.cleared.emit()

        self.objects = {id(obj): obj for obj in objects}  # list(objects)

        if len(objects) < len(data):
            raise ValueError('more data than items!')

        data = self._buildItemData(objects, data)
        for obj, datum in zip_longest(objects, data, fillvalue={}):
            if hasattr(obj, name):
                item = self._itemFactory.createItem(getattr(obj, name), data=datum, parent=self)
                # GST why does each object need to have an item associated with it?
                # this associates data with 'model items' which 'isn't good'
                obj.item = item
                self.addItem(item)
                self._items.append(item)

            else:
                item = self._itemFactory.createItem(str(obj), data=datum, parent=self)
                self.addItem(item)

    def setPartner(self, partner):
        self._partner = partner

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0:
            self.paintEmpty(event)

    def paintEmpty(self, event):

        p = QtGui.QPainter(self.viewport())
        pen = QtGui.QPen(QtGui.QColor("grey"))
        oldPen = p.pen()
        p.setPen(pen)
        p.drawText(self.rect(), QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, f" {self._emptyText}")
        p.setPen(oldPen)
        p.end()

    def _isAcceptableDrag(self, event):
        data = self.parseEvent(event)
        result = False

        if 'source' in data and data['source'] is not None:
            source = data['source']
            okEvent = 'GroupEditorPopupABC' in str(data['source'])
            okSide = False
            if self._rearrangeable and source == self:
                okSide = True
            elif source == self._partner:
                okSide = True

            result = okEvent and okSide
        return result

    def dragEnterEvent(self, event):
        if self._isAcceptableDrag(event):
            event.accept()
            if self._feedbackWidget:
                self._feedbackWidget.highlight(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        event.accept()
        self._dragReset()

    def dropMimeData(self, index, data, action):

        mimeData = data.data(INTERNALQTDATA)
        _data = self._itemFactory.decodeDragData(mimeData)
        strings = [item[0].value() for item in _data.values()]
        self.insertItems(index, strings)  #multi insert item or notification leakage
        return True

    def dropEvent(self, event):
        """Handle dropping items from left-to-right, right-to-left, or re-ordering the items in the right-hand list
        """
        if self._isAcceptableDrag(event):
            data = self.parseEvent(event)
            if self._rearrangeable and data['source'] == self:
                # re-ordering the list of items in the group
                event.setDropAction(Qt.CopyAction)  # required otherwise item disappears
                QtWidgets.QListWidget.dropEvent(self, event)

            else:
                # dropping left-to-right or right-to-left
                super().dropEvent(event=event)

            self._dragReset()
        else:
            event.ignore()

    def _dragReset(self):
        if self._feedbackWidget:
            self._feedbackWidget.highlight(False)

    def getContextMenu(self):

        # FIXME this context menu must be more generic and editable
        contextMenu = Menu('', self, isFloatWidget=True)

        enabled = self._itemsAvailable()
        enabledAll = True
        if self.count() == 0:
            enabledAll = False

        # Context temporarily disabled. Need to fix the signal block or risk of a massive signal-leakage
        # contextMenu.addItem("Move %s" % self._oppositeRole, callback=self.move, enabled=enabled)
        # contextMenu.addItem("Move All %s" % self._oppositeRole, callback=self.moveAll, enabled=enabledAll)

        return contextMenu

    def _itemsAvailable(self):
        result = False
        count = self.count()
        if count > 0 and self._partner is not None:
            selected = self.selectedItems()
            if len(selected) > 0:
                result = True
            else:
                item = self.itemAt(self._currentMousePos)
                if item:
                    result = True
        return result

    def move(self):
        # this needs to be handled with a context manager to disable the signals leakage
        count = self.count()
        if count > 0 and self._partner is not None:
            selected = self.selectedItems()
            if len(selected) > 0:
                rows = [self.row(item) for item in selected]
                for i in reversed(sorted(rows)):
                    item = self.takeItem(i)
                    self._partner.addItem(item)
            elif item := self.itemAt(self._currentMousePos):
                row = self.row(item)
                self.takeItem(row)
                self._partner.addItem(item)

    def moveAll(self):
        # this needs to be handled with a context manager to disable the signals leakage
        count = self.count()
        if count > 0 and self._partner is not None:
            for i in reversed(range(count)):
                item = self.takeItem(i)
                self._partner.addItem(item)

    def mousePressEvent(self, event):
        self._currentMousePos = event.pos()
        super().mousePressEvent(event)

    def _itemDoubleClickedCallback(self, item):
        if self._partner is not None:
            row = self.row(item)
            taken = self.takeItem(row)
            self._partner.addItem(item)


class _GroupEditorPopupABC(CcpnDialogMainWidget):
    """
    An abstract base class to create and manage popups for _class of the "grouping" kind

    NB: Note the left and right are interchanged in the actual display!
        i.e. "right" widgets appear on the left; "left" widgets on the right
    """
    # These need sub-classing

    # Definitions for the "grouping class"
    _class = None  #  e.g. SpectrumGroup
    _classPulldown = None  # SpectrumGroupPulldown
    _enableClassPulldown = False  # Enable the class pulldown widget

    # either define _projectNewMethod, _projectItemAttribute or subclass the newObject, getItems methods
    _projectNewMethod = None  # e.g. 'newSpectrumGroup'  # Method of Project to create new _class instance
    _projectItemAttribute = None  # e.g. 'spectra'  # Attribute of Project containing items

    # # define these
    # _pluralGroupName = None  # eg 'Spectrum Groups'
    # _singularGroupName = None  # eg'Spectrum Group'

    # Definitions for the Items of the group
    # either define _classItemAttribute or subclass the getObjectItems, setObjectItems methods
    _classItemAttribute = None  # e.g. 'spectra' # Attribute in _class containing items

    # define these; need specific definition as some use cases (e.g. Collection) will have
    # variable types of items
    _singularItemName = None  # eg 'Spectrum'
    _pluralItemName = None  # eg 'Spectra'

    # post init routine to populate any new values as necessary
    _groupEditorInitMethod = None

    _buttonFilter = 'Filter:'
    _buttonCancel = 'Cancel'
    _setRevertButton = False

    _useTab = None
    _numberTabs = 0

    FIXEDWIDTH = False
    FIXEDHEIGHT = False
    _FIXEDWIDTH = 120

    def __init__(self, parent=None, mainWindow=None, editMode=True, obj=None, defaultItems=None, size=(800, 500), **kwds):
        """
        Initialise the widget, note defaultItems is only used for create
        """
        title = f'Edit {self._class.className}' if editMode else f'New {self._class.className}'

        super().__init__(parent=parent, windowTitle=title, setLayout=True, margins=(0, 0, 0, 0),
                         spacing=(5, 5), size=size, **kwds)

        self._singularGroupName = camelCaseSplit(self._class.className)
        self._pluralGroupName = camelCaseSplit(self._class._pluralLinkName).capitalize()

        self._targetEmptyText = f'Drag or double click {self._singularItemName} to add here'
        self._sourceEmptyText = f"No {self._pluralItemName}: try 'Filter by' settings"
        self._acceptButtonText = 'Save'

        self.errorIcon = Icon('icons/exclamation_small')

        self.mainWindow = mainWindow
        self.application = mainWindow.application
        self.project = mainWindow.application.project
        self.current = mainWindow.application.current

        self.obj = obj
        self.EDITMODE = editMode
        self._modelsConnected = False
        self._initialState = None

        # set up the main widgets
        self._setWidgets(defaultItems)

        # enable the buttons
        self.setOkButton(callback=self._applyAndClose, text=self._acceptButtonText, tipText='Apply according to current settings and close')
        self.setCancelButton(callback=self._cancel, text=self._buttonCancel, tipText='Cancel the New/Edit operation')
        self.setRevertButton(callback=self._revertClicked, enabled=False)

        self.setDefaultButton(CcpnDialogMainWidget.OKBUTTON)

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self._applyButton = self.getButton(self.OKBUTTON)
        self._cancelButton = self.getButton(self.CANCELBUTTON)
        self._revertButton = self.getButton(self.RESETBUTTON)

        self._connectLists()
        self._allItems = self.getItems()
        self._populateLists()
        self._revertButton.setEnabled(False)

        # # one cannot be a copy of the other unless it's a deep copy...
        # # this is easier
        # self._previousState = self._getPreviousState()
        # self._updatedState = copy.deepcopy(self._getPreviousState())
        #
        # self._previousNames = {key: key for key in self._previousState}
        # self._updatedNames = dict(self._previousNames)
        #
        # self.connectModels()
        # self._updateStateOnSelection()
        # self.setMinimumSize(self.sizeHint())
        # self.resize(500, 350)  # change to a calculation rather than a guess

    #-----------------------------------------------------------------------------------
    # GWV: new methods; possible to subclass
    #-----------------------------------------------------------------------------------

    def getItems(self) -> list:
        """Get the items that can be included in the group
        :return A list of items

        NB Likely to be subclassed
        """
        if hasattr(self.project, self._projectItemAttribute):
            return getattr(self.project, self._projectItemAttribute)
        else:
            raise RuntimeError(f'Project.{self._projectItemAttribute} does not exists')

    def newObject(self, name, comment=None):
        """Create a new object
        :return The new object

        NB Can be subclassed
        """
        func = getattr(self.project, self._projectNewMethod)
        obj = func(name=name, comment=comment)
        return obj

    def getObjectItems(self) -> list:
        """Get the items from self.object; i.e. the items that form the group
        :return A list of items

        NB Likely to be subclassed
        """
        if (obj := self.obj) is not None:
            return getattr(obj, self._classItemAttribute)
        else:
            return []

    def setObjectItems(self, items):
        """Set the items of the object; i.e. the items that form the group

        NB Likely to be subclassed
        """
        if (obj := self.obj) is not None:
            setattr(obj, self._classItemAttribute, items)

    #-----------------------------------------------------------------------------------
    # GWV: end new methods; possible to subclass
    #-----------------------------------------------------------------------------------

    def _setWidgets(self, defaultItems):
        """Set up the main widgets for the dialog
        """
        # open popup with these items already added to target ListWidget. Ready to create the group.
        # assumes that defaultItems is a list of core objects (with pid)
        self.defaultItems = [itm.pid for itm in defaultItems] if defaultItems else None
        if self._useTab is None:
            # define the destination for the widgets - Dialog has mainWidget, will change for tabbed widgets
            # self._dialogWidget = self.mainWidget

            self._dialogWidget = ScrollableFrame(self.mainWidget, setLayout=True, grid=(0, 0),
                                                 spacing=DEFAULTSPACING, margins=TABMARGINS,
                                                 scrollBarPolicies=('asNeeded', 'asNeeded'))

        else:
            # hPolicy='expanding' gives weird results
            self._tabWidget = Tabs(self.mainWidget, grid=(0, 0))

            # define the new tab widget
            self._tabWidget.setContentsMargins(*ZEROMARGINS)
            for tabNum in range(self._numberTabs):
                fr = ScrollableFrame(self.mainWidget, setLayout=True, spacing=DEFAULTSPACING,
                                     scrollBarPolicies=('asNeeded', 'asNeeded'), margins=TABMARGINS)
                self._tabWidget.addTab(fr.scrollArea, str(tabNum))

            if isinstance(self._useTab, int) and self._useTab < self._tabWidget.count():
                self._dialogWidget = (self._tabWidget.widget(self._useTab))._scrollContents
            else:
                raise RuntimeError('self._tabWidget: invalid _useTab setting')

        self._setTargetWidgets()
        self._setSourceWidgets()

    def _populateLists(self):
        # one cannot be a copy of the other unless it's a deep copy...
        # this is easier
        self._previousState = self._getPreviousState()
        self._updatedState = copy.deepcopy(self._previousState)

        self._previousNames = {key: key for key in self._previousState}
        self._updatedNames = dict(self._previousNames)

        self._connectModels()
        self._updateStateOnSelection()

    def _populate(self, *args, **kwargs):
        self._populateLists()

    def _getChangeState(self):
        """Get the change state from the _changes dict
        """
        # changes not required here, just need to define which buttons to disable after revert
        return changeState(self, False, False, False, self._applyButton, None, self._revertButton, 0)

    def _getPreviousState(self):
        #TODO remove dependence on _pid2Obj
        result = {}
        beforeKeys = self.project._pid2Obj.get(self._class.shortClassName)
        if beforeKeys is not None:
            for key in beforeKeys:
                #GST do I need to filter object in an undo-state, if so could we add some interface for this...
                obj = self.project._pid2Obj.get(self._class.shortClassName)[key]
                items = [elem.pid for elem in self.getObjectItems()]
                comment = obj.comment or None
                result[key] = {'spectra': items,
                               'comment': comment}
        return result

    def _setTargetWidgets(self):

        # self.leftTopLabel = Label(self._dialogWidget, '', bold=True, grid=(0, 0), gridSpan=(1, 3))

        labelName = f'{self._singularGroupName} Name' if self.EDITMODE else f'New {self._singularGroupName} Name'

        optionTexts = [labelName, 'Comment', self._singularGroupName, 'Selection']
        _, maxDim = getTextDimensionsFromFont(textList=optionTexts)
        self._FIXEDWIDTH = maxDim.width()

        row = 1
        # if self.EDITMODE:
        #     self._leftPullDownLabel = Frame(self._dialogWidget, setLayout=True, showBorder=False, grid=(row, 1), gridSpan=(1, 2))
        #     self.leftPullDownLabel = Label(self._dialogWidget, self._singularGroupName, grid=(row, 0), hAlign='r')
        #
        #     self.leftPullDown = self._classPulldown(parent=self._leftPullDownLabel,
        #                                             mainWindow=self.mainWindow,
        #                                             showSelectName=False,
        #                                             default=self.obj,
        #                                             callback=self._leftPullDownCallback,
        #                                             fixedWidths=[0, None],
        #                                             hAlign='l', grid=(row, 1),
        #                                             )
        #     self.leftPullDown.setEnabled(self._enableClassPulldown)  ## Editing of different SG from the same popup is disabled.
        #     ## It is confusing and error-prone in notifying changes to the other tabs.

        # still needs to be in the correct place
        row += 1
        self.nameLabel = Label(self._dialogWidget, labelName, grid=(row, 0), hAlign='r',
                               tipText=f'Name for {self._singularGroupName}')
        self._nameEditFrame = Frame(self._dialogWidget, setLayout=True, showBorder=False, grid=(row, 1),
                                    gridSpan=(1, 2))
        self.nameEdit = LineEdit(self._nameEditFrame, backgroundText=f'{self._singularGroupName} Name', hAlign='l',
                                 textAlignment='left', grid=(row, 1))

        row += 1
        self.commentLabel = Label(self._dialogWidget, 'Comment', grid=(row, 0), hAlign='r',
                                  tipText=f'Comment for {self._singularGroupName}')
        self.commentEdit = LineEdit(self._dialogWidget, backgroundText='> Optional <',
                                    textAlignment='left', grid=(row, 1), gridSpan=(1, 2))

        # GST need something better than this..!
        # self.nameEdit.setFixedWidth(self._FIXEDWIDTH * 1.5)
        self.nameEdit.setFixedWidth(self._FIXEDWIDTH * 2)
        # self.nameEdit.setVisible(True)

        row += 2
        targetCol = 2
        Label(self._dialogWidget, 'Included', grid=(row, targetCol))

        row += 1
        self.selectionLabel = Label(self._dialogWidget, self._pluralItemName, grid=(row, 0), hAlign='r',
                                    tipText=f'{self._pluralItemName} included or not-included in {self._singularGroupName}')
        self.targetListFeedbackWidget = FeedbackFrame(self._dialogWidget, grid=(row, targetCol))
        self.targetListWidget = _ListWidget(self.targetListFeedbackWidget, feedbackWidget=self.targetListFeedbackWidget,
                                            grid=(0, 0), dragRole='right', acceptDrops=True, sortOnDrop=False, copyDrop=False,
                                            emptyText=self._targetEmptyText, rearrangeable=True, itemFactory=OrderedListWidgetItemFactory())

        self.targetListWidget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        # make this is primary expanding row
        self._dialogWidget.getLayout().setRowStretch(row, 2)

    def _connectModels(self):
        if not self._modelsConnected:
            self.nameEdit.textChanged.connect(self._updateNameOnEdit)
            self.commentEdit.textChanged.connect(self._updateCommentOnEdit)
            self.targetListWidget.model().dataChanged.connect(self._updateModelsOnEdit)
            self.targetListWidget.model().rowsRemoved.connect(self._updateModelsOnEdit)
            self.targetListWidget.model().rowsInserted.connect(self._updateModelsOnEdit)
            self.targetListWidget.model().rowsMoved.connect(self._updateModelsOnEdit)
            self._modelsConnected = True

    def _disconnectModels(self):
        if self._modelsConnected:
            self.nameEdit.textChanged.disconnect(self._updateNameOnEdit)
            self.commentEdit.textChanged.disconnect(self._updateCommentOnEdit)
            self.targetListWidget.model().dataChanged.disconnect(self._updateModelsOnEdit)
            self.targetListWidget.model().rowsRemoved.disconnect(self._updateModelsOnEdit)
            self.targetListWidget.model().rowsInserted.disconnect(self._updateModelsOnEdit)
            self.targetListWidget.model().rowsMoved.disconnect(self._updateModelsOnEdit)
            self._modelsConnected = False

    def _setSourceWidgets(self):

        row = 4
        self.addSpacer(0, 5, grid=(row, 0), gridSpan=(1, 3), parent=self._dialogWidget)

        row += 1
        sourceCol = 1
        Label(self._dialogWidget, 'Not Included', grid=(row, sourceCol))

        row += 1
        self.sourceListFeedbackWidget = FeedbackFrame(self._dialogWidget, grid=(row, sourceCol))
        self.sourceListWidget = _ListWidget(self.sourceListFeedbackWidget, feedbackWidget=self.sourceListFeedbackWidget,
                                            grid=(0, 0), dragRole='left', acceptDrops=True, sortOnDrop=False, copyDrop=False,
                                            emptyText=self._sourceEmptyText, sorted=True, itemFactory=OrderedListWidgetItemFactory())

        self.sourceListWidget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        # make this is primary expanding row
        self._dialogWidget.getLayout().setRowStretch(row, 2)

        # GWV insertion
        # create a search box at the bottom of the sidebar frame container
        row += 1
        self._searchWidgetContainer = Frame(self._dialogWidget, setLayout=True, showBorder=False, grid=(row, 1), gridSpan=(1, 1))

        Label(self._searchWidgetContainer, self._buttonFilter, hAlign='l', grid=(0, 0))
        txt = 'Filter for Pid/String e.g Sp:H*qC'
        self._searchWidget = LineEdit(self._searchWidgetContainer, backgroundText=txt, grid=(0, 1))
        self._searchWidget.textChanged.connect(self._searchWidgetCallback)

        # end GWV insertion

        # small frame for holding the pulldown list
        row += 1
        # self.rightListFilterFrame = Frame(self._dialogWidget, setLayout=True, showBorder=False, grid=(row, 1), gridSpan=(1, 2))
        # self.rightFilterLabel = Label(self.rightListFilterFrame, self._buttonFilter, hAlign='l', grid=(0, 0))
        # self.rightPullDown = self._classPulldown(parent=self.rightListFilterFrame,
        #                                          mainWindow=self.mainWindow,
        #                                          showSelectName=True,
        #                                          selectNoneText='none',
        #                                          callback=self._sourcePullDownCallback,
        #                                          fixedWidths=[0, None],
        #                                          filterFunction=self._rightPullDownFilter,
        #                                          hAlign='l', grid=(0, 1)
        #                                          )
        # # GWV
        # self.rightListFilterFrame.hide()
        # self.rightListFilterFrame.getLayout().setColumnStretch(2, 1)

        row += 1
        self.addSpacer(0, 5, grid=(row, 0), gridSpan=(1, 3), parent=self._dialogWidget)

        row += 1
        self.errorFrame = Frame(self._dialogWidget, setLayout=True, grid=(row, 1), gridSpan=(1, 2))

        row += 1
        self.addSpacer(0, 10, grid=(row, 0), gridSpan=(1, 3), parent=self._dialogWidget)

        # self.sourceListWidget.setFixedWidth(2*self.FIXEDWIDTH)

    def _searchWidgetCallback(self):
        """Private callback from search widget
        """
        self._updateSource()  # update the contents of the source list-widget

    # def _rightPullDownFilter(self, pids):
    #     if self._editedObject and self._editedObject.pid in pids:
    #         pids.remove(self._editedObject.pid)
    #     return pids

    def _connectLists(self):
        self.targetListWidget.setPartner(self.sourceListWidget)
        self.sourceListWidget.setPartner(self.targetListWidget)

    @property
    def _editedObject(self):
        """Convenience to get the edited object"""
        # return self.leftPullDown.getSelectedObject() if self.EDITMODE else None
        return self.obj if self.EDITMODE else None

    @property
    def _groupedObjects(self) -> list:
        result = self.targetListWidget.getTexts()
        if self._targetEmptyText in result:
            result.remove(self._targetEmptyText)
        return result

    @_groupedObjects.setter
    def _groupedObjects(self, vv):
        self.targetListWidget.setTexts(vv)

    @property
    def _editedObjectItems(self) -> [list, None]:
        """Convenience to get the list of items we are editing for object (e.g. spectra for SpectrumGroup)
        Returns list or None on error
        """
        obj = self._editedObject
        if obj is None:
            return None
        state = self._updatedState[obj.name]
        return state.get('spectra')

    @property
    def _editedObjectComment(self) -> [str, None]:
        """Convenience to get the comment
        Returns list or None on error
        """
        obj = self._editedObject
        if obj is None:
            return None
        state = self._updatedState[obj.name]
        return state.get('comment')

    def _setAcceptButtonState(self):
        if self.EDITMODE and self._dirty:
            # self.applyButtons.setButtonEnabled(self._acceptButtonText, True)
            self._applyButton.setEnabled(True)

    def _currentEditorState(self):
        if self.EDITMODE and self._editedObject:
            key = self._editedObject.name
        else:
            key = self.nameEdit.text()
        comment = self.commentEdit.text() or None
        items = self._groupedObjects

        return {key: {'spectra': items, 'comment': comment}} if len(key) > 0 else {}

    def _updateNameOnEdit(self):
        if self.EDITMODE and self._editedObject is not None:
            editedObjectName = self._editedObject.name
            newName = self.nameEdit.text()
            self._updatedNames[editedObjectName] = newName

        self._updateButton()

    def _updateModelsOnEdit(self, *args, **kwargs):

        currentEdits = self._currentEditorState()

        if self.EDITMODE and self._editedObject is not None:
            for idd, selections in currentEdits.items():
                self._updatedState[idd] = selections

            editedObjectName = self._editedObject.name
            newName = self.nameEdit.text()
            self._updatedNames[editedObjectName] = newName

        self._updateSource()
        self._updateButton()

    def _updateCommentOnEdit(self, *args, **kwargs):

        currentEdits = self._currentEditorState()

        if self.EDITMODE and self._editedObject is not None:
            for idd, selections in currentEdits.items():
                self._updatedState[idd] = selections

        self._updateButton()

    def _checkForEmptyNames(self):
        result = False
        badKeys = []
        for name in self._updatedState.keys():
            if len(name.strip()) == 0:
                raise ValueError(f'{self.__class__.__name__}._checkForEmptyNames: unexpected empty name')
                # result  = True

        for key, name in self._updatedNames.items():
            if len(name.strip()) == 0:
                badKeys.append(key)
                result = True

        resultString = ''
        if result:
            badKeys.sort()
            resultString = f"Some {self._pluralGroupName} have an empty name (original names: {','.join(badKeys)})"

        return result, resultString

    def _checkForDuplicatetNames(self):
        nameCount = Counter(self._updatedNames.values())
        duplicateNameCounts = list(filter(lambda i: i[1] > 1, nameCount.items()))
        result = len(duplicateNameCounts) > 0

        resultString = ''
        if result:
            duplicateNames = [item[0] for item in duplicateNameCounts]
            duplicateNameString = ','.join(duplicateNames)
            resultString = f'Duplicate Names: {duplicateNameString}'

        return result, resultString

    def _checkForSpacesInName(self):

        result = False
        badKeys = []
        for key, name in self._updatedNames.items():
            if len(name.strip()) != len(name) or len(name.split()) > 1:
                badKeys.append(key)
                result = True

        msg = 'Some %s names contain white-space\n (original names are: %s)'
        resultString = msg % (self._pluralGroupName, ','.join(badKeys))

        return result, resultString

    def _checkForExistingName(self):
        currentEdits = self._currentEditorState()
        result = False
        resultString = ''

        if currentEdits != {}:
            name = list(currentEdits.keys())[0]
            if name in self._previousState.keys():
                result = True

                # GST when i used 'The Spectrum Group %s already exists' % name igot an odd effect
                # the space and a in already were deleted...
                resultString = f'The {self._singularGroupName} {name} already exists'

        return result, resultString

    def filterEmptyText(self, items):
        if self._targetEmptyText in items:
            items.remove(self._targetEmptyText)
        return items

    def _checkForNoName_New(self):
        result = False
        resultString = ''

        noNameString = 'Name not set'

        currentEdits = self._currentEditorState()
        if currentEdits == {}:
            result = True
            resultString = noNameString
        else:
            name = list(currentEdits.keys())[0]
            if len(name.strip()) == 0:
                result = True
                resultString = noNameString

        return result, resultString

    def _checkForSpaceInName_New(self):
        result = False
        resultString = ''
        spacesString = f'The {self._pluralGroupName} name contains white-space'

        currentEdits = self._currentEditorState()
        if currentEdits != {}:
            name = list(currentEdits.keys())[0]
            if len(name.strip()) != len(name) or len(name.split()) > 1:
                result = True
                resultString = spacesString

        return result, resultString

    def _updateButton(self):

        self.errors = []
        self._initialState = self._initialState or self._currentEditorState()

        if not self.EDITMODE:

            enabled = True

            check, message = self._checkForNoName_New()
            if check:
                enabled = False
                self.errors.append(message)

            # check, message = self._checkForEmptyGroup_New()
            # if check:
            #     enabled = False
            #     self.errors.append(message)

            check, message = self._checkForSpaceInName_New()
            if check:
                enabled = False
                self.errors.append(message)

            check, message = self._checkForExistingName()
            if check:
                enabled = False
                self.errors.append(message)

            revertEnabled = (self._currentEditorState() != self._initialState)

        else:
            enabled = False

            if self._updatedState != self._previousState:
                enabled = True

            if self._updatedNames != self._previousNames:
                enabled = True

            check, message = self._checkForEmptyNames()
            if check:
                enabled = False
                self.errors.append(message)

            check, message = self._checkForDuplicatetNames()
            if check:
                enabled = False
                self.errors.append(message)

            # check, message = self._checkForEmptyGroups()
            # if check:
            #     enabled = False
            #     self.errors.append(message)

            check, message = self._checkForSpacesInName()
            if check:
                enabled = False
                self.errors.append(message)

            revertEnabled = enabled

        self._applyButton.setEnabled(enabled)

        if self._setRevertButton:
            self._revertButton.setEnabled(True)
        else:
            self._revertButton.setEnabled(revertEnabled)

        self._emptyErrorFrame()

        if self.errors:
            self.errorFrame.layout().setColumnStretch(0, 0)
            self.errorFrame.layout().setColumnStretch(1, 1000)
            for i, error in enumerate(self.errors):
                label = Label(self.errorFrame, error)
                iconLabel = Label(self.errorFrame)
                iconLabel.setPixmap(self.errorIcon.pixmap(16, 16))
                self.errorFrame.layout().addWidget(label, i, 1)
                self.errorFrame.layout().setAlignment(label, QtCore.Qt.AlignLeft)
                self.errorFrame.layout().addWidget(iconLabel, i, 0)
                self.errorFrame.layout().setAlignment(iconLabel, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def _emptyErrorFrame(self):
        for child in self.errorFrame.findChildren(QtWidgets.QWidget):
            self.errorFrame.getLayout().removeWidget(child)
            child.setParent(None)
            child.hide()
            del child

    def _updateStateOnSelection(self):
        """Update state
        """
        # Note well model updates must be off while the selected
        # group to edit is being changed else the changes applied
        # will trigger model changes

        self._disconnectModels()
        self._updateTarget()
        self._updateSource()
        self._updateButton()
        # self.rightPullDown._updatePulldownList()
        # if len(self.rightPullDown.getObjects()) < 2:
        #     self.rightPullDown.setEnabled(False)
        # else:
        #     self.rightPullDown.setEnabled(True)
        self._connectModels()

    # def _getItemPositions(self, items):
    #     orderedPids = [elem.pid for elem in self._allItems]
    #     return [{_ListWidget._searchRoleIndex: orderedPids.index(item)} for item in items]

    def _updateTarget(self):
        """Update target list
        """
        # block widget signals to stop feedback loops
        with self.blockWidgetSignals(recursive=False):
            if self.EDITMODE:

                # self.leftPullDownLabel.show()
                # self.leftPullDown.show()
                # self.rightPullDown.setEnabled(len(self.leftPullDown.getObjects()) > 0)

                obj = self._editedObject
                if obj is not None:
                    name = self._updatedNames[obj.name]
                    self.nameEdit.setText(name)
                    self.commentEdit.setText(self._editedObjectComment)
                    self._setTargetListWidgetItems(self._editedObjectItems)
                    self.nameEdit.setEnabled(True)
                    self.targetListWidget.setEnabled(True)
                    self.sourceListWidget.setEnabled(True)
                else:
                    self.nameEdit.setText('')
                    self.commentEdit.setText('')
                    self.targetListWidget.clear()
                    self.nameEdit.setEnabled(False)
                    self.targetListWidget.setEnabled(False)
                    self.sourceListWidget.setEnabled(False)

            else:
                self.targetListWidget.clear()
                if self.defaultItems is not None:
                    self._setTargetListWidgetItems(self.defaultItems)
                self.nameEdit.setText(self._class._uniqueName(self.project))
                self.commentEdit.setText('')

    def _updateSource(self):
        """Update Source list
        """
        # if (obj := self.rightPullDown.getSelectedObject()) is None:
        # if self.obj:
        #     self._setSourceListWidgetItems(self._allItems)
        # else:
        #     self.sourceListWidget.clear()
        #     self._setSourceListWidgetItems(self.getObjectItems())

        self._setSourceListWidgetItems(self._allItems)

    def _setTargetListWidgetItems(self, pids: list):
        """Convenience to set the items in the target ListWidget
        """
        # convert items to pids
        # data = self._getItemPositions(pids)
        self.targetListWidget.setTexts(pids, clear=True)  # , data=data)

    def _filterPids(self, pids) -> list:
        """
        :return: the list of filtered pids
        """
        from fnmatch import fnmatchcase

        filt = self._searchWidget.get()
        if len(filt) == 0:
            return pids
        pids = [pid for pid in pids if fnmatchcase(pid, filt)]
        return pids

    def _setSourceListWidgetItems(self, items: list):
        """Convenience to set the items in the source ListWidget
        """
        # convert items to pids
        pids = [s.pid for s in items]

        # filter for those pids already in the target
        targetPids = self.targetListWidget.getTexts()
        pids = [s for s in pids if s not in targetPids]

        # GWV addition; apply the search filter
        pids = self._filterPids(pids)

        # data = self._getItemPositions(pids)
        self.sourceListWidget.setTexts(pids, clear=True)  # , data=data)

    # def _targetPullDownCallback(self, value=None):
    #     """Callback when selecting the target spectrumGroup pulldown item"""
    #     if obj := self.project.getByPid(value):
    #         # set the new object
    #         self.obj = obj
    #     self._updateStateOnSelection()
    #
    # def _sourcePullDownCallback(self, value=None):
    #     """Callback when selecting the right spectrumGroup pulldown item"""
    #     self._updateSource()

    def _updatedStateToObjects(self):
        result = {}
        for key, state in self._updatedState.items():
            previousState = self._previousState[key]
            if state == previousState:
                continue
            result[key] = {'spectra': [self.project.getByPid(pid) for pid in (state.get('spectra') or [])],
                           'comment': state.get('comment')}
        return result

    def _getRenames(self):
        return {name: rename for name, rename in self._updatedNames.items() if name != rename}

    # def _revertClicked(self):
    #     super()._revertClicked()
    #     self._populate()

    def _applyChanges(self):
        """
        The apply button has been clicked
        Return True on success; False on failure
        """

        updateList = self._updatedStateToObjects()
        renameList = self._getRenames()

        with undoBlock():
            try:
                if self.EDITMODE:
                    # edit mode
                    if self.obj is None:
                        raise RuntimeError(f'Undefined object in edit mode')

                    for name, state in updateList.items():
                        items = state.get('spectra')
                        self.setObjectItems(items)
                        self.obj.comment = state.get('comment')

                    for name in renameList:
                        newName = renameList[name]
                        self.obj.rename(newName)

                    # call the post init routine to populate any new values as necessary
                    if self._groupEditorInitMethod:
                        self._groupEditorInitMethod()

                else:
                    # new mode
                    newState = self._currentEditorState()
                    if newState:
                        name = list(newState.keys())[0]
                        state = list(newState.values())[0]
                        items = state.get('spectra')
                        comment = state.get('comment')

                        # func = getattr(self.project, self._projectNewMethod)
                        # self.obj = func(name, items, comment=comment)
                        self.obj = self.newObject(name=name, comment=comment)
                        self.setObjectItems(items=items)

                        # call the post init routine to populate any new values as necessary - only the current object
                        if self._groupEditorInitMethod is not None:
                            self._groupEditorInitMethod()

            except Exception as es:
                showWarning(str(self.windowTitle()), str(es))
                if self.application._isInDebugMode:
                    raise es
                return False

        return True

    def unRegister(self):
        """Clean up notifiers on closing
        """
        # if self.EDITMODE:
        #     self.leftPullDown.unRegister()
        # self.rightPullDown.unRegister()
        self._disconnectModels()

    def _cancel(self):
        """Callback from cancel button
        """
        self.reject()

    def _applyAndClose(self):
        """Callback from apply-and-close button
        """
        if self._applyChanges() is True:
            self.accept()

    def accept(self):
        """Dialog accepted
        """
        self.unRegister()
        super().accept()

    def reject(self) -> None:
        """Dialog rejected
        """
        self.unRegister()
        super().reject()

    def _updateGl(self, spectra):
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=self)
        GLSignals.emitPaintEvent()
