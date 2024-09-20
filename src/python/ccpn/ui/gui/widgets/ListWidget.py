"""
List widget

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
__author__ = "$Author: Geerten Vuister $"
__date__ = "$Date: 2017-04-18 15:19:30 +0100 (Tue, April 18, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.lib.mouseEvents import _getMimeQVariant
from ccpn.util.Constants import ccpnmrModelDataList, INTERNALQTDATA
from ccpn.ui.gui.guiSettings import getColours, BORDERFOCUS, BORDERNOFOCUS
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.Widget import Widget

# GST is this really a WrapperObject ListWidget because there appear to be some
# methods and features that are possibly quite coupled to them or some defined
# object e.g objects with text() methods and which have items associated with them
# maybe needs a refactoring or a rename (or both)... or of course I maybe reading this wrong...
class ListWidget(QtWidgets.QListWidget, Base):
    dropped = pyqtSignal(list)
    cleared = pyqtSignal()
    changed = pyqtSignal()

    def __init__(self, parent=None, objects=None, callback=None,
                 rightMouseCallback=None,
                 contextMenu=True,
                 multiSelect=True,
                 acceptDrops=False,
                 sortOnDrop=False,
                 allowDuplicates=False,
                 allowSelections =True,
                 copyDrop=True,
                 infiniteHeight=False,
                 minRowsVisible=4,
                 emptyText=None,
                 **kwds):

        super().__init__(parent)
        Base._init(self, acceptDrops=acceptDrops, **kwds)

        self.setDragDropMode(self.DragDrop)

        self.setAcceptDrops(acceptDrops)
        self.contextMenu = contextMenu
        self.callback = callback
        # GST why dow we keep our own list of items and objects when we could add them as user data
        # to the ListWidgetItem... this st seems like a way for things to get out of sync
        self.objects = {id(obj): obj for obj in objects} if objects else {}  # list(objects) or [])
        self._items = list(objects or [])
        self.multiSelect = multiSelect
        self.dropSource = None

        # GST this only works for sorting on drops... it doesn't allow for sorting on moving items
        # with double clicks or menus
        self.sortOnDrop = sortOnDrop
        self.copyDrop = copyDrop
        self.allowDuplicates = allowDuplicates
        if not self.copyDrop:
            self.setDefaultDropAction(QtCore.Qt.MoveAction)

        self.rightMouseCallback = rightMouseCallback
        if callback is not None:
            self.itemClicked.connect(callback)

        if self.multiSelect:
            self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        else:
            self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.contextMenuItem = 'Remove'
        self.currentContextMenu = self.getContextMenu
        self.infinitleyTallVerically = infiniteHeight
        self.minRowsVisible = minRowsVisible
        self._emptyText = str(emptyText)
        self._setStyle()
        self._setChangedConnections()
        self.setAllowSelections(allowSelections)

    def setAllowSelections(self, value):
        if value:
            if self.multiSelect:
                self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            else:
                self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        else:
            self.setSelectionMode(QtWidgets.QListWidget.NoSelection)

    def _setStyle(self):
        """Set the focus/noFocus colours for the widget
        """
        _style = """QListWidget {
                        border: 1px solid palette(mid);
                        border-radius: 2px;
                    }
                    QListWidget:focus {
                        border: 1px solid palette(highlight);
                        border-radius: 2px;
                    }
                    QListWidget:disabled { background-color: palette(midlight); }
                    """
        self.setStyleSheet(_style)

    def _setChangedConnections(self):
        self.model().dataChanged.connect(lambda val: self.changed.emit())
        self.model().rowsRemoved.connect(lambda val: self.changed.emit())
        self.model().rowsInserted.connect(lambda val: self.changed.emit())
        self.model().rowsMoved.connect(lambda val: self.changed.emit())

    def minimumSizeHint(self) -> QtCore.QSize:
        result = super().minimumSizeHint()
        if self.count() > 0:
            result.setHeight(self.sizeHintForRow(0) * self.minRowsVisible)
        else:
            result.setHeight(self.fontMetrics().height() * self.minRowsVisible)
        return result

    def sizeHint(self):
        result = super().sizeHint()

        if self.infinitleyTallVerically:
            result.setHeight(QtWidgets.QWIDGETSIZE_MAX)
        return result

    def contextCallback(self, remove=True):

        if remove:
            self.removeItem()
        self.rightMouseCallback()

    def setTexts(self, texts, clear=True):
        if clear:
            self.clear()
            self.cleared.emit()

            # GST why don't we clear self._items and self.objects
            # GST why don't we add to self.objects
            # self.items = []
        for text in texts:
            item = QtWidgets.QListWidgetItem(str(text))
            self.addItem(item)

    def setObjects(self, objects, name='pid'):
        self.clear()
        self.cleared.emit()

        self.objects = {id(obj): obj for obj in objects}  # list(objects)
        for obj in objects:
            if hasattr(obj, name):
                item = QtWidgets.QListWidgetItem(getattr(obj, name), self)
                item.setData(QtCore.Qt.UserRole, id(obj))
                obj.item = item
                self.addItem(item)
                #GST why do we store items when a list widget stores them as well...
                self._items.append(item)

            else:
                item = QtWidgets.QListWidgetItem(str(obj))
                item.setData(QtCore.Qt.UserRole, id(obj))
                self.addItem(item)

    def getObjects(self):
        return list(self.objects.values())

    def addItem(self, item):
        if self.allowDuplicates:
            super(ListWidget, self).addItem(item)
        else:
            if isinstance(item, str):
                if not item in self.getTexts():
                    super(ListWidget, self).addItem(item)
            else:
                if not item.text() in self.getTexts():
                    super(ListWidget, self).addItem(item)

    def hideAllItems(self):
        for i in range(self.count()):
            item = self.item(i)
            item.setHidden(True)

    def showAllItems(self):
        for i in range(self.count()):
            item = self.item(i)
            item.setHidden(False)

    def showItems(self, items, select=False):
        """ Shows specific items and hides the rest"""

        for i in range(self.count()):
            item = self.item(i)
            if item.text() in items:
                item.setHidden(False)
                if select:
                    item.setSelected(True)
            else:
                item.setHidden(True)
                item.setSelected(False)

    def _getDroppedObjects(self, project):
        """This will return obj if the items text is a ccpn pid. This is used when the objects inside a listWidget are being dragged and dropped across widgets"""
        items = []
        objs = []

        for index in range(self.count()):
            items.append(self.item(index))
        for item in items:
            obj = project.getByPid(item.text())
            objs.append(obj)
        return objs

    def getSelectedObjects(self):
        indexes = self.selectedIndexes()
        objects = []
        for item in indexes:
            objId = item.data(QtCore.Qt.UserRole)
            if objId in self.objects:
                obj = self.objects[objId]
                if obj is not None:
                    objects.append(obj)
        return objects

    def selectItems(self, names):
        for index in range(self.count()):
            item = self.item(index)
            if item.text() in names:
                item.setSelected(True)

    def select(self, name):
        for index in range(self.count()):
            item = self.item(index)
            if item.text() == name:
                self.setCurrentItem(item)

    def clearSelection(self):
        for i in range(self.count()):
            item = self.item(i)
            # self.setItemSelected(item, False)
            item.setSelected(False)

    def getItems(self):
        items = []
        for index in range(self.count()):
            items.append(self.item(index))
        return items

    def _getItemsFromText(self, text):
        items = []
        for item in self.getItems():
            if item.text() == text:
                items.append(item)
        return items

    def getTexts(self):
        items = []
        for index in range(self.count()):
            items.append(self.item(index))
        return [i.text() for i in items]

    def getSelectedTexts(self):
        return [i.text() for i in self.selectedItems()]

    def selectObject(self, obj):
        try:
            obj.item.setSelected(True)
        except Exception as e:
            # Error wrapped C/C++ object of type QListWidgetItem has been deleted
            pass

    def selectObjects(self, objs):
        self.clearSelection()
        for obj in objs:
            self.selectObject(obj)

    def removeItem(self):
        for selectedItem in self.selectedItems():
            self.takeItem(self.row(selectedItem))
            # self.takeItem(self.currentRow())

    def removeTexts(self, texts):
        for text in texts:
            for item in self.getItems():
                if item.text() == text:
                    self.takeItem(self.row(item))

    def renameItem(self, oldName, newName):
        for item in self.getItems():
            if item.text() == oldName:
                item.setText(newName)

    def scrollToFirstSelected(self):
        for selectedItem in self.selectedItems():
            self.scrollToItem(selectedItem, QtWidgets.QAbstractItemView.PositionAtCenter)
            break

    def mousePressEvent(self, event):
        self._mouse_button = event.button()
        if event.button() == QtCore.Qt.RightButton:
            if self.contextMenu:
                self.raiseContextMenu(event)
        elif event.button() == QtCore.Qt.LeftButton:
            if self.itemAt(event.pos()) is None:
                self.clearSelection()
            else:
                super(ListWidget, self).mousePressEvent(event)

    def raiseContextMenu(self, event):
        """
        Raise the context menu and return the action clicked
        """
        if menu := self.currentContextMenu():
            # store the texts and objects as required for signals
            self._preContent = self.getTexts(), self.getObjects()

            menu.move(event.globalPos().x(), event.globalPos().y() + 10)
            return menu.exec_()

    def getContextMenu(self):
        # FIXME this context menu must be more generic and editable
        contextMenu = Menu('', self, isFloatWidget=True)
        if self.rightMouseCallback is None:
            contextMenu.addItem("Remove", callback=self.removeItem)
            contextMenu.addItem("Remove All", callback=self._deleteAll)
        else:
            contextMenu.addItem("Remove", callback=self.contextCallback)
        return contextMenu

    def setContextMenu(self, menu):
        self.currentContextMenu = menu
        return menu

    # TODO:ED these are not very generic yet
    def setSelectContextMenu(self):
        self.currentContextMenu = self._getSelectContextMenu

    def _getSelectContextMenu(self):
        # FIXME this context menu must be more generic and editable
        contextMenu = Menu('', self, isFloatWidget=True)
        contextMenu.addItem("Select All", callback=self._selectAll)
        contextMenu.addItem("Clear Selection", callback=self._selectNone)
        return contextMenu

    def setSelectDeleteContextMenu(self):
        self.currentContextMenu = self._getSelectDeleteContextMenu

    def _getSelectDeleteContextMenu(self):
        # FIXME this context menu must be more generic and editable
        contextMenu = Menu('', self, isFloatWidget=True)
        contextMenu.addItem("Select All", callback=self._selectAll)
        contextMenu.addItem("Clear Selection", callback=self._selectNone)
        contextMenu.addItem("Remove", callback=self.removeItem)
        return contextMenu

    def _selectAll(self):
        """
        Select all items in the list
        """
        for i in range(self.count()):
            item = self.item(i)
            item.setSelected(True)

    def _selectNone(self):
        """
        Clear item selection
        """
        self.clearSelection()

    def _deleteAll(self):
        self.clear()
        self.cleared.emit()
        self.changed.emit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        elif event.mimeData().hasFormat(INTERNALQTDATA):
            super(ListWidget, self).dragEnterEvent(event)
        else:
            event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        elif event.mimeData().hasFormat(INTERNALQTDATA):
            super(ListWidget, self).dragMoveEvent(event)
        else:
            event.accept()

    def dropEvent(self, event):
        mimeData = event.mimeData()

        if mimeData.hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in mimeData.urls():
                links.append(str(url.toLocalFile()))

            self.dropped.emit(links)
            if self.sortOnDrop is True:
                self.sortItems()
            event.accept()

        else:
            data = [self.parseEvent(event)]
            if event.source() != self:  # otherwise duplicates
                if self.dropSource is None:  # allow event drops from anywhere
                    if self.copyDrop:
                        event.setDropAction(QtCore.Qt.CopyAction)
                    else:
                        event.setDropAction(QtCore.Qt.MoveAction)

                    if mimeData.hasFormat(INTERNALQTDATA):
                        # process listType to listType drag/drop - before the emit
                        super(ListWidget, self).dropEvent(event)

                    elif mimeData.hasFormat(ccpnmrModelDataList):
                        # respond to manual drag item (possibly created by mouseEvents.makeDragEvent)
                        texts = _getMimeQVariant(mimeData.data(ccpnmrModelDataList)) or []
                        if texts is not None:
                            if isinstance(texts, list):
                                for text in texts:
                                    self.addItem(str(text))
                            else:
                                raise TypeError('mimeData.{} must be a list/None: {}'.format(ccpnmrModelDataList, repr(texts)))

                    self.dropped.emit(data)
                    if not self.allowDuplicates:
                        self._removeDuplicate()
                    if self.sortOnDrop is True:
                        self.sortItems()
                    event.accept()

                elif event.source() is self.dropSource:
                    # check that the drop comes from only the permitted widget
                    event.setDropAction(QtCore.Qt.MoveAction)

                    if mimeData.hasFormat(INTERNALQTDATA):
                        # process listType to listType drag/drop - before the emit
                        super(ListWidget, self).dropEvent(event)

                    elif mimeData.hasFormat(ccpnmrModelDataList):
                        # respond to manual drag item (possibly created by mouseEvents.makeDragEvent)
                        texts = _getMimeQVariant(mimeData.data(ccpnmrModelDataList)) or []
                        if texts is not None:
                            if isinstance(texts, list):
                                for text in texts:
                                    self.addItem(str(text))
                            else:
                                raise TypeError('mimeData.{} must be a list/None: {}'.format(ccpnmrModelDataList, repr(texts)))

                    self.dropped.emit(data)
                    if self.sortOnDrop is True:
                        self.sortItems()
                    event.accept()

    def _removeDuplicate(self):
        """ Removes duplicates from listwidget on dropping. Could be implemented to don't add in first place but difficult
        to know where the items are added from, eg from different drop event sources (sidebar, other List or outside urls etc).
        which didn't work well when duplicates  were dropped as a group and also qt as different signatures for each item on same function!.
        Don't use the ccpn parse data for pids as this is not a widget where you use always pids!
        """

        seen = set()
        uniq = [i for i in self.getItems() if i.text() not in seen and not seen.add(i.text())]
        removeDuplicates = [self.model().removeRow(self.row(i)) for i in self.getItems() if i not in uniq]

    def _disableLabels(self, labels):
        items = self.getItems()
        for item in items:
            if item.text() in labels:
                item.setFlags(QtCore.Qt.NoItemFlags)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.count() == 0 and self._emptyText:
            # paint the emptyText string in the empty widget
            self._paintEmpty(event)

    def _paintEmpty(self, event):
        """If the widget is empty then write the emptyText string
        """
        p = QtGui.QPainter(self.viewport())
        pen = QtGui.QPen(QtGui.QColor("grey"))
        oldPen = p.pen()
        p.setPen(pen)
        p.drawText(self.rect(), QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, " " + self._emptyText)
        p.setPen(oldPen)
        p.end()

    def _getSaveState(self):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.getTexts()

    def _setSavedState(self, value):
        """
        Internal. Called for saving/restoring the widget state.
        """
        return self.setTexts(value)



class ListWidgetPair(Widget):
    """
    Define a pair of listWidgets such that information can be copied from one side
    to the other and vise-versa
    """

    def __init__(self,  parent=None,
                 leftObjects=None,
                 rightObjects=None,
                 callback=None,
                 rightMouseCallback=None,
                 contextMenu=True,
                 multiSelect=True,
                 acceptDrops=True,
                 showMoveArrows=False,
                 showMoveText=False,
                 leftLabel='Not included',
                 rightLabel='Included',
                 setLayout=True,
                 copyDrop=False,
                 objAttr = 'pid',
                 **kwds):
        """
        """
        Widget.__init__(self, parent, setLayout=setLayout, **kwds)


        self.leftLabel = Label(self, text=leftLabel, grid=(0, 0),  hAlign='l')
        self.leftList = ListWidget(self, contextMenu=contextMenu,
                                   acceptDrops=acceptDrops,
                                   copyDrop=copyDrop,
                                   sortOnDrop=False, multiSelect=multiSelect, grid=(1, 0),)

        self.rightLabel = Label(self, text=rightLabel,  grid=(0, 1),  hAlign='l')
        self.rightList = ListWidget(self, contextMenu=contextMenu, grid=(1, 1),
                                    acceptDrops=acceptDrops,
                                    copyDrop=copyDrop,
                                    sortOnDrop=False,
                                    multiSelect=multiSelect)

        # set the drop source
        self.leftList.dropSource = self.rightList
        self.rightList.dropSource = self.leftList

        self.leftList.setSelectContextMenu()
        self.rightList.setSelectContextMenu()
        # self.rightList.setSelectDeleteContextMenu()

        self.leftList.itemDoubleClicked.connect(self._moveRight)
        self.rightList.itemDoubleClicked.connect(self._moveLeft)

        self.leftIcon = Icon('icons/yellow-arrow-left')
        self.rightIcon = Icon('icons/yellow-arrow-right')

        if showMoveArrows:
            moveText = ['', '']
            if showMoveText:
                moveText = ['move left', 'move right']

            self.buttons = ButtonList(self, texts=moveText,
                                      icons=[self.leftIcon, self.rightIcon],
                                      callbacks=[self._moveLeft, self._moveRight],
                                      direction='v',
                                      grid=(3, 3), hAlign='c')
            self.buttons.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            transparentStyle = "background-color: transparent; border: 0px solid transparent"
            self.buttons.setStyleSheet(transparentStyle)
        if leftObjects:
            self._populate(self.leftList, leftObjects, objAttr=objAttr)
        if rightObjects:
            self._populate(self.rightList, rightObjects, objAttr=objAttr)

        # self.leftList.dropped.connect(self._itemDropped)
        # self.rightList.dropped.connect(self._itemDropped)

    def setListObjects(self, left):
        # self.leftObjects = left
        # self._populate(self.leftList, self.objects)

        self.objects = left
        self._populate(self.rightList, self.objects)

    def _populate(self, listWiget, objs, objAttr='pid'):
        """
        List the Pids of the objects in the listWidget
        :param list: target listWidget
        :param objs: list of objects with Pids
        """
        listWiget.clear()
        if objs:
            for obj in objs:
                itemStr = None
                if isinstance(obj, str):
                    itemStr = str(obj)
                else:
                    if objAttr:
                        att = getattr(obj, objAttr, None)
                        itemStr = str(att)
                if itemStr:
                    item = QtWidgets.QListWidgetItem(itemStr)
                    listWiget.addItem(item)
        listWiget.sortItems()

    def _itemDropped(self, data):

        # onleftTexts = self.leftList.getTexts()

        self.leftList._removeDuplicate()
        self.rightList._removeDuplicate()


    def _moveLeft(self):  # not needed now
        """
        Move contents of the right window to the left window
        """
        for item in self.rightList.selectedItems():
            leftItem = QtWidgets.QListWidgetItem(item)
            self.leftList.addItem(leftItem)
            self.rightList.takeItem(self.rightList.row(item))
        self.leftList.sortItems()

    def _moveRight(self):  # not needed now
        """
        Move contents of the left window to the right window
        """
        for item in self.leftList.selectedItems():
            rightItem = QtWidgets.QListWidgetItem(item)
            self.rightList.addItem(rightItem)
            self.leftList.takeItem(self.leftList.row(item))
        self.rightList.sortItems()

    def _moveItemLeft(self):
        """
        Move contents of the right window to the left window
        """
        rightItem = QtWidgets.QListWidgetItem(self.rightList.selectedItems())
        self.leftList.addItem(rightItem)
        self.rightList.takeItem(self.rightList.row(rightItem))
        self.leftList.sortItems()

    def _moveItemRight(self):
        """
        Move contents of the left window to the right window
        """
        leftItem = QtWidgets.QListWidgetItem(self.leftList.selectedItem)
        self.rightList.addItem(leftItem)
        self.leftList.takeItem(self.leftList.row(leftItem))
        self.rightList.sortItems()

    def _copyRight(self):
        """
        Copy selection of the left window to the right window
        """
        for item in self.leftList.selectedItems():
            rightItem = QtWidgets.QListWidgetItem(item)
            self.rightList.addItem(rightItem)
        self.rightList.sortItems()

    def getLeftList(self):
        return self.leftList.getTexts()

    def getRightList(self):
        return self.rightList.getTexts()



class ListWidgetSelector(Frame):
    """
    Define a pair of listWidgets such that information can be cpoied from one side
    to the other and vise-versa
    """
    residueTypes = [('Alanine', 'ALA', 'A'),
                    ('Arginine', 'ARG', 'R'),
                    ('Asparagine', 'ASN', 'N'),
                    ('Aspartic acid', 'ASP', 'D'),
                    ('ASP/ASN ambiguous', 'ASX', 'B'),
                    ('Cysteine', 'CYS', 'C'),
                    ('Glutamine', 'GLN', 'Q'),
                    ('Glutamic acid', 'GLU', 'E'),
                    ('GLU/GLN ambiguous', 'GLX', 'Z'),
                    ('Glycine', 'GLY', 'G'),
                    ('Histidine', 'HIS', 'H'),
                    ('Isoleucine', 'ILE', 'I'),
                    ('Leucine', 'LEU', 'L'),
                    ('Lysine', 'LYS', 'K'),
                    ('Methionine', 'MET', 'M'),
                    ('Phenylalanine', 'PHE', 'F'),
                    ('Proline', 'PRO', 'P'),
                    ('Serine', 'SER', 'S'),
                    ('Threonine', 'THR', 'T'),
                    ('Tryptophan', 'TRP', 'W'),
                    ('Tyrosine', 'TYR', 'Y'),
                    ('Unknown', 'UNK', ''),
                    ('Valine', 'VAL', 'V')]

    def __init__(self, parent=None, objects=None, callback=None,
                 rightMouseCallback=None,
                 contextMenu=True,
                 multiSelect=True,
                 acceptDrops=False,
                 title='Copy Items', **kwds):
        """
        Initialise the pair of listWidgets
        :param parent:
        :param objects:
        :param callback:
        :param rightMouseCallback:
        :param contextMenu:
        :param multiSelect:
        :param acceptDrops:
        :param pairName:
        :param kwds:
        """
        Frame.__init__(self, parent, **kwds)

        self.title = Label(self, text=title, setLayout=True, grid=(0, 0), gridSpan=(1, 7), hAlign='l')
        self.leftList = ListWidget(self, setLayout=True, grid=(1, 1), gridSpan=(5, 1), acceptDrops=True,
                                   sortOnDrop=True)
        self.rightList = ListWidget(self, setLayout=True, grid=(1, 5), gridSpan=(5, 1), acceptDrops=True,
                                    sortOnDrop=True)

        # set the drop source
        self.leftList.dropSource = self.rightList
        self.rightList.dropSource = self.leftList

        self.leftList.setSelectContextMenu()
        self.rightList.setSelectContextMenu()
        # self.rightList.setSelectDeleteContextMenu()

        self.leftList.itemDoubleClicked.connect(self._moveRight)
        self.rightList.itemDoubleClicked.connect(self._moveLeft)

        # self.leftIcon = Icon('icons/yellow-arrow-left')
        # self.rightIcon = Icon('icons/yellow-arrow-right')
        #
        # self.buttons = ButtonList(self, texts=['move left', 'move right'],
        #                          icons=[self.leftIcon, self.rightIcon],
        #                          callbacks=[self._moveLeft, self._moveRight],
        #                          direction='v',
        #                          grid=(3,3), hAlign='c')
        # self.buttons.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        # transparentStyle = "background-color: transparent; border: 0px solid transparent"
        # self.buttons.setStyleSheet(transparentStyle)

        # self.button = Button(self, text='',
        #                          icon=self.rightIcon,
        #                          callback=self._copyRight,
        #                          grid=(3,3)),
        # self.button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        self.spacer1 = Spacer(self, 5, 5,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(0, 2), gridSpan=(1, 1))
        self.spacer2 = Spacer(self, 10, 10,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(2, 2), gridSpan=(1, 1))
        self.spacer3 = Spacer(self, 10, 10,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(4, 4), gridSpan=(1, 1))
        self.spacer4 = Spacer(self, 5, 5,
                              QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                              grid=(6, 4), gridSpan=(1, 1))

        for i, cs in enumerate([2, 6, 1, 1, 1, 6, 2]):
            self.getLayout().setColumnStretch(i, cs)

        # self.showBorder=True
        # self.leftList.setContentsMargins(15,15,15,15)
        # self.rightList.setContentsMargins(15,15,15,15)

    def setListObjects(self, left):
        # self.leftObjects = left
        # self._populate(self.leftList, self.objects)

        self.objects = left
        self._populate(self.rightList, self.objects)

    def _populate(self, list, objs):
        """
        List the Pids of the objects in the listWidget
        :param list: target listWidget
        :param objs: list of objects with Pids
        """
        list.clear()
        if objs:
            for item in objs:
                item = QtWidgets.QListWidgetItem(str(item.pid))
                list.addItem(item)
        list.sortItems()

    def _moveLeft(self):  # not needed now
        """
        Move contents of the right window to the left window
        """
        for item in self.rightList.selectedItems():
            leftItem = QtWidgets.QListWidgetItem(item)
            self.leftList.addItem(leftItem)
            self.rightList.takeItem(self.rightList.row(item))
        self.leftList.sortItems()

    def _moveRight(self):  # not needed now
        """
        Move contents of the left window to the right window
        """
        for item in self.leftList.selectedItems():
            rightItem = QtWidgets.QListWidgetItem(item)
            self.rightList.addItem(rightItem)
            self.leftList.takeItem(self.leftList.row(item))
        self.rightList.sortItems()

    def _moveItemLeft(self):
        """
        Move contents of the right window to the left window
        """
        rightItem = QtWidgets.QListWidgetItem(self.rightList.selectedItems())
        self.leftList.addItem(rightItem)
        self.rightList.takeItem(self.rightList.row(rightItem))
        self.leftList.sortItems()

    def _moveItemRight(self):
        """
        Move contents of the left window to the right window
        """
        leftItem = QtWidgets.QListWidgetItem(self.leftList.selectedItem)
        self.rightList.addItem(leftItem)
        self.leftList.takeItem(self.leftList.row(leftItem))
        self.rightList.sortItems()

    def _copyRight(self):
        """
        Copy selection of the left window to the right window
        """
        for item in self.leftList.selectedItems():
            rightItem = QtWidgets.QListWidgetItem(item)
            self.rightList.addItem(rightItem)
        self.rightList.sortItems()

    def getLeftList(self):
        return self.leftList.getTexts()

    def getRightList(self):
        return self.rightList.getTexts()


#===================================================================================================
# __main__
#===================================================================================================

if __name__ == '__main__':
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.popups.Dialog import CcpnDialog
    from ccpn.ui.gui.widgets.Widget import Widget
    from collections import namedtuple


    lst = ['pid', 'comment', ]
    MockPeakList = namedtuple('PeakList', lst)
    peakLists = [MockPeakList('PL:%s'%i, 'comment_%s' %i)  for i in range(10)]


    def droppedCallback(*r):
        print(r)


    app = TestApplication()

    texts = ['Int', 'Float', 'String', '']
    objects = [int, float, str, 'Green']

    popup = CcpnDialog(windowTitle='Test widget', setLayout=True)
    # widget = ListWidget(parent=popup, allowDuplicates=True, acceptDrops=True, grid=(0, 0))
    # widget2 = ListWidget(parent=popup, allowDuplicates=False, acceptDrops=True, grid=(0, 1))
    # widget2.dropped.connect(droppedCallback)
    #
    # for i in ['a', 'a', 'c']:
    #     widget.addItem(i)

    w= ListWidgetPair(popup, leftObjects = peakLists, grid=(1,0))
    popup.show()
    popup.raise_()
    app.start()
