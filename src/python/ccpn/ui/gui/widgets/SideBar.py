"""
SideBar setup

This module is built on a definition of the sidebar tree that includes dynamic additions
and deletions initiated by notifiers on the various project objects.

The tree can be constructed using 4 item types:

SidebarTree: A static tree item, displaying either a name or the pid of the associated V3 core object
SidebarItem: A static item, displaying either a name or the pid of the associated V3 core object
SidebarClassItems: A number of dynamically added items of type V3 core 'klass'
SidebarClassTreeItems: A Tree with a number of dynamically added items of type V3 core 'klass'


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
__dateModified__ = "$dateModified: 2024-08-28 10:35:47 +0100 (Wed, August 28, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: gvuister $"
__date__ = "$Date: 2017-03-23 16:50:22 +0000 (Thu, March 23, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import json
import fnmatch
from contextlib import contextmanager
from PyQt5 import QtGui, QtWidgets, QtCore
from typing import Callable, Optional

from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core.Project import Project
from ccpn.core.Spectrum import Spectrum
from ccpn.core.PeakList import PeakList
from ccpn.core.MultipletList import MultipletList
from ccpn.core.IntegralList import IntegralList
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.core.NmrChain import NmrChain
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.Sample import Sample
from ccpn.core.SampleComponent import SampleComponent
from ccpn.core.Substance import Substance
from ccpn.core.Chain import Chain
from ccpn.core.Residue import Residue
from ccpn.core.Atom import Atom
from ccpn.core.StructureEnsemble import StructureEnsemble
from ccpn.core.Complex import Complex
from ccpn.core.ChemicalShiftList import ChemicalShiftList
from ccpn.core.StructureData import StructureData
from ccpn.core.Restraint import RestraintTable
from ccpn.core.Note import Note
from ccpn.core.DataTable import DataTable
from ccpn.core.ViolationTable import ViolationTable
# from ccpn.core._implementation.CollectionList import CollectionList
from ccpn.core.Collection import Collection


from ccpn.core.lib.Pid import Pid
# from ccpn.ui.gui.guiSettings import sidebarFont
from ccpn.ui.gui.widgets.Base import Base
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.widgets.MessageDialog import showInfo, showWarning
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Spacer import Spacer as CCPNSpacer
from ccpn.util.Constants import ccpnmrJsonData
from ccpn.util.Common import copyToClipboard
from ccpn.core.lib.Notifiers import Notifier, NotifierBase
from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier
from ccpn.ui.gui.lib.mouseEvents import makeDragEvent
from ccpn.ui.gui.widgets.Font import setWidgetFont, getFontHeight, getFont, SIDEBARFONT
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.guiSettings import getColours, LABEL_FOREGROUND
# from PyQt5.QtCore import QStringListModel
# from PyQt5.QtGui import QListView, QAbstractItemView

from ccpn.ui.gui.lib.MenuActions import _createNewStructureData, _createNewPeakList, _createNewChemicalShiftList, _createNewMultipletList, _createNewNmrResidue, \
    _createNewNmrAtom, _createNewComplex, _createNewRestraintTable, _createNewSampleComponent, _createNewSubstance, \
    _createNewNote, _createNewIntegralList, _createNewSample, _createNewStructureEnsemble, _raiseNewChainPopup, _raiseChainPopup, _raiseComplexEditorPopup, \
    _raiseStructureDataPopup, _raiseChemicalShiftListPopup, _raisePeakListPopup, _raiseMultipletListPopup, _raiseCreateNmrChainPopup, _raiseNmrChainPopup, \
    _raiseNmrResiduePopup, _raiseNmrResidueNewPopup, _raiseNmrAtomPopup, _raiseNmrAtomNewPopup, _raiseNotePopup, _raiseIntegralListPopup, \
    _raiseRestraintTableEditPopup, _raiseRestraintTableNewPopup, _raiseSamplePopup, _raiseAtomNewPopup, _raiseAtomPopup, \
    _raiseSampleComponentPopup, _raiseSpectrumPopup, _raiseSpectrumGroupEditorPopup, _raiseStructureEnsemblePopup, \
    _raiseSubstancePopup, _raiseDataTablePopup, _raiseViolationTablePopup, _raiseCollectionPopup

from ccpn.ui.gui.lib.MenuActions import _openItemNoteTable, _openItemChemicalShiftListTable, \
    _openItemIntegralListTable, _openItemMultipletListTable, _openItemNmrChainTable, \
    _openItemPeakListTable, _openItemChainTable, _openItemRestraintTable, \
    _openItemSpectrumGroupDisplay, _openItemStructureEnsembleTable, _openItemStructureDataTable, \
    _openItemSpectrumDisplay, _openItemSampleDisplay, _openItemComplexTable, _openItemResidueTable, \
    _openItemSubstanceTable, _openItemSampleComponentTable, _openItemNmrResidueItem, _openItemNmrAtomItem, \
    _openItemSpectrumInGroupDisplay, _openItemAtomItem, _openItemDataTable, _openItemViolationTable, _openItemCollectionModule

from ccpn.util.OrderedSet import OrderedSet
from ccpn.core.lib.ContextManagers import undoBlock, notificationEchoBlocking, \
    undoBlockWithoutSideBar, undoStackBlocking


ALL_NOTIFIERS = (Notifier.DELETE, Notifier.CREATE, Notifier.RENAME, Notifier.CHANGE)
DEFAULT_NOTIFIERS = (Notifier.DELETE, Notifier.CREATE, Notifier.RENAME)


#===========================================================================================================
# SideBar handling class for handling tree structure
#===========================================================================================================

class _sidebarWidgetItem(QtWidgets.QTreeWidgetItem):
    """TreeWidgetItem for the new sidebar structure.
    Contains a link to the sidebar item.
    """

    def __init__(self, treeWidgetItem, sidebarItem):
        """Initialise the widget and set the link to the sidebar item.
        """
        super().__init__(treeWidgetItem)
        self._parent = treeWidgetItem
        self.sidebarItem = sidebarItem


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# SidebarABC
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SidebarABC(NotifierBase):
    """
    Abstract base class defining various sidebar item types and methods
    """

    # subclassing
    itemType = None
    triggers = [Notifier.DELETE, Notifier.CREATE, Notifier.RENAME]

    # ids
    _nextIndx = 0

    REBUILD = 'rebuild'
    RENAME = 'rename'
    _postBlockingActions = [None, REBUILD, RENAME]

    def __init__(self, name=None, usePidForName=False, klass=None, addNotifier=False, closed=True, add2NodesUp=False,
                 rebuildOnRename=None, callback=None, menuAction=None, children=[], isDraggable=False, **kwds):
        super().__init__()

        self._indx = SidebarABC._nextIndx
        SidebarABC._nextIndx += 1

        if name is None and not usePidForName:
            raise ValueError('Either name needs to be defined or usePidForName needs to be True')
        self.name = name
        self.usePidForName = usePidForName  # flag; if True show pid rather then name

        self.klass = klass
        self.addNotifier = addNotifier  # flag to indicate adding notifier for rename, delete, create of klass
        self.callback = callback  # callback for double click
        self.menuAction = menuAction  # action for raising rightClickMenu
        self.kwds = kwds  # kwd arguments passed to callback

        self.widget = None  # widget object
        self.closed = closed  # State of the tree widget
        self.add2NodesUp = add2NodesUp  # flag to indicate a widget that needs adding two nodes up in the tree
        self._postBlockingAction = None  # attribute to indicate action required post blocking the sidebar
        self.rebuildOnRename = rebuildOnRename  # Name of node up in the tree to rebuild on rename; not used when None

        self.sidebar = None  # reference to SideBar instance; set by buildTree
        self.obj = None  # reference to obj, e.g. a Project, Spectrum, etc instance; set by buildTree
        self.children = children
        self._children = []  # used by SidebarClassTreeItems methods
        self._parent = None  # connection to parent node
        self.level = 0  # depth level of the sidebar tree; increased for every node down, except children of 'class' nodes
        self.isDraggable = isDraggable

        self._expandedState = []

    @property
    def givenName(self):
        """Return either obj.pid (depending on usePidForName), name or id (in that order)
        """
        if self.usePidForName and self.obj is not None:
            return self.obj.pid
        if self.name is not None:
            return self.name
        return self.id

    @property
    def id(self):
        """An unique identifier for self
        """
        id = '%s-%d' % (self.itemType, self._indx)
        return id

    @property
    def root(self):
        """Return the root of the tree
        """
        node = self
        while node._parent is not None:
            node = node._parent
        return node

    def get(self, *names):
        """traverse down the tree to get node defined by names.
        Skips over in 'class'-based nodes.
        """
        if len(names) == 0:
            return None

        if isinstance(self, (SidebarClassItems, SidebarClassTreeItems)):
            for child in self.children:
                if child.get(*names):
                    return child
            return None

        if self.name == names[0]:
            if len(names) == 1:
                return self
            elif len(names) >= 2:
                for child in self.children:
                    if child.get(*names[1:]):
                        return child

        return None

    def _getKlassChildren(self, obj, klass):
        """Get the children of <obj> by class type <klass>.
        """
        return obj._getChildrenByClass(klass)

    def _findParentNode(self, name):
        """Find the node up in the tree whose self.name == name or return self if name == 'self'
        """
        if name == 'self':
            return self
        # find the node
        node = self
        while node is not None and node.name != name:
            node = node._parent
        if node is None:
            raise RuntimeError('Failed to find parent node with name "%s" starting from %s' % (name, self))
        return node

    def _findChildNode(self, name):
        """Find the node across the tree whose self.name == name or return self if name == 'self'
        """
        if name == 'self' or self.name == name:
            return self

        # find the node
        for itm in self.children:
            node = itm._findChildNode(name)
            if node:
                return node

    def findChildNode(self, name):
        node = self._findChildNode(name)
        # if node is None:
        #     raise RuntimeError('Failed to find child node with name "%s" starting from %s' % (name, self))
        return node

    def _findChildNodeObject(self, obj):
        """Find the node across the tree whose self.name == name or return self if name == 'self'
        """
        # if name == 'self' or self.name == name:
        #     return self

        if self.obj is obj and self._parent.klass is type(obj):
            return self

        # find the node
        for itm in self.children:
            node = itm._findChildNodeObject(obj)
            if node:
                return node

    def findChildNodeObject(self, obj):
        node = self._findChildNodeObject(obj)
        # if node is None:
        #     raise RuntimeError('Failed to find child node with name "%s" starting from %s' % (obj.pid, self))
        return node

    def buildTree(self, parent, parentWidget, sidebar, obj, level=0):
        """Builds the tree from self downward
        """
        self._parent = parent
        self._parentWidget = parentWidget
        self.sidebar = sidebar
        self.obj = obj
        self.level = level

        if self.addNotifier and self.klass:
            # add the create/delete/rename notifiers to the parent
            triggers = self.kwds['triggers'] if 'triggers' in self.kwds else DEFAULT_NOTIFIERS
            self.setNotifier(parent.obj, triggers, targetName=self.klass.className, callback=self._update)

        # code like this needs to be implemented in the sub-classed objects:
        # # make the widget
        # self.widget = self.givenName
        #
        # for itm in self.children:
        #     itm.buildTree(parent=self, sidebar=self.sidebar, obj=self.obj, level=self.level+1)

    def rebuildTree(self, deleteNotifiers=True):
        """Rebuilds the tree starting from self
        """
        self.reset(deleteNotifiers=deleteNotifiers)
        self.buildTree(parent=self._parent, parentWidget=self._parentWidget, sidebar=self.sidebar, obj=self.obj, level=self.level)

    def printTree(self, string=None):
        """Print the tree from self downward
        """
        if string is not None:
            print(string)

        tabs = self._tabs
        name = self.givenName
        # Create a mark for 'characterization' of the node
        mark = ''
        if isinstance(self, (SidebarTree, SidebarClassTreeItems)):
            mark = '()' if self.closed else '(..)'
        if isinstance(self, (SidebarItem, SidebarClassItems)):
            mark = '&&'
        if isinstance(self, (SidebarClassItems, SidebarClassTreeItems)):
            mark = '>' + mark
            name = '[..%s..]' % name
        if self.add2NodesUp:
            mark = '^' + mark

        tabs = '    ' * len(tabs)
        string1 = '%s%3s %s' % (tabs, mark, name)
        print('(%1d) %-65s  %3d: %-14s obj=%-40s    widget=%s self=%s parent=%s' % (
            self.level, string1, self._indx, self.itemType, self.obj, self.widget, self, self._parent))
        for itm in self.children:
            itm.printTree()

    def _getExpanded(self, item, data: list):
        """Add the name of expanded item to the data list
        """
        if item.widget:
            expandedState = item.widget.isExpanded()
            item.closed = not expandedState
            if expandedState:
                data.append(item.widget.text(0))

    def _setExpanded(self, item, data: list):
        """Set the expanded flag if item is in data
        """
        if item.widget:
            if item.widget.text(0) in data:
                item.widget.setExpanded(True)
                item.closed = False

    def _storeExpandedStates(self):
        """Test storing the expanded items.
        """
        self._expandedState = []
        self._traverseTree(func=self._getExpanded, data=self._expandedState)

    def _restoreExpandedStates(self):
        """Test restoring the expanded items.
        """
        self._traverseTree(func=self._setExpanded, data=self._expandedState)
        self._expandedState = []

    def _setBlankingAllNotifiers(self, value):
        """Set the blanking state of all notifiers in the tree.
        """
        self.setBlankingAllNotifiers(value)

    def _traverseTree(self, sidebar=None, func=None, data=None):
        """Traverse the tree, applying <func> to all nodes

        :param sidebar: sidebar top level object
        :param func: function to perform on this element
        :param data: optional data storage to pass to <func>
        """
        if self.widget and func:
            # process the sidebarItem
            func(self, data)

        # if self._children:
        #     for child in self._children:
        #         child._traverseTree(sidebar, func, data)
        if self.children:
            for child in self.children:
                child._traverseTree(sidebar, func, data)

    def _traverseKlassTree(self, sidebar=None, func=None, data=None):
        """Traverse the tree, applying <func> to all nodes

        :param sidebar: sidebar top level object
        :param func: function to perform on this element
        :param data: optional data storage to pass to <func>
        """
        if self.klass and func:
            # process the sidebarItem
            func(self, data)

        if self.children:
            for child in self.children:
                child._traverseKlassTree(sidebar, func, data)

    def makeWidget(self, parentWidgetItem, givenName):
        """Create the required widget here
        """
        newItem = None

        # Creation of QTreeWidgetItems, needs to be commented out if testing from the __main__ function
        newItem = _sidebarWidgetItem(parentWidgetItem, self)

        _isDraggable = self._parent.isDraggable if self._parent else None
        if _isDraggable:
            newItem.setFlags(newItem.flags() & ~QtCore.Qt.ItemIsDropEnabled)
        else:
            newItem.setFlags(newItem.flags() ^ QtCore.Qt.ItemIsDragEnabled)

        newItem.setData(0, QtCore.Qt.DisplayRole, str(givenName))
        newItem.setData(1, QtCore.Qt.UserRole, self)
        newItem.setExpanded(not self.closed)

        return newItem if newItem else givenName

    def duplicate(self):
        """Return a duplicate of self
        """
        # Cannot use copy.copy() or deepcopy as it overwrites the indx
        result = self.__class__(name=self.name, usePidForName=self.usePidForName, klass=self.klass)

        for attr in 'addNotifier closed add2NodesUp callback menuAction sidebar obj _parent _postBlockingAction rebuildOnRename isDraggable'.split():
            value = getattr(self, attr)
            setattr(result, attr, value)

        # recursively copy children and _children
        result.children = []
        for child in self.children:
            result.children.append(child.duplicate())
        result._children = []
        for child in self._children:
            result._children.append(child.duplicate())

        return result

    def rename(self, newName=None):
        """This function needs to rename the widget
        """
        self.oldName = self.name
        if newName is None:
            newName = self.givenName
        # rename the widget
        # self.widget = newName
        self.widget.setData(0, QtCore.Qt.DisplayRole, str(newName))
        self.name = newName

    def _getChildWidgets(self, widgets=[]):
        for itm in self.children:
            widg = itm.widget

            if widg and widg not in widgets:
                widgets.append(widg)

            widgets = itm._getChildWidgets(widgets)

        return widgets

    def _getChildren(self, children):
        for itm in self.children:
            widg = itm.widget

            # only add children with widgets
            if widg and itm not in children:
                children.append(itm)

            # children = itm._getChildren(children)

        return children

    def _reorderClassObjs(self, classObjs):
        """Reorder the classObjs into the tree.
        To be subclassed as required.
        """
        return classObjs

    def reset(self, deleteNotifiers=True):
        """Resets the tree from self downward, deleting widget and
        optionally the notifiers; remove all children
        """
        if (self.children):

            # recurse into the tree, otherwise just delete the notifiers
            for itm in self.children:
                itm.reset()

            self.deleteAllNotifiers()

        # remove the widgets associated with the sidebar items
        if self.widget and self.widget.parent():
            self.widget.parent().removeChild(self.widget)
            self.widget = None

        self._postBlockingAction = None

    def _update(self, cDict):
        """Callback routine for updating the node
        """

        trigger = cDict[Notifier.TRIGGER]
        obj = cDict[Notifier.OBJECT]

        # Define the actions
        if trigger == Notifier.RENAME and self.rebuildOnRename in [None, 'self']:
            # Just rename the node

            node = self.findChildNodeObject(obj)
            if not node:
                return
            _action = self.RENAME

        elif trigger == Notifier.RENAME:
            # Find the node to rebuild
            node = self._findParentNode(self.rebuildOnRename)
            _action = self.REBUILD

        elif trigger == Notifier.DELETE:
            # For now: we just rebuild from here on down the tree
            node = self
            _action = self.REBUILD

        elif trigger == Notifier.CREATE:
            # For now: we just rebuild from here on down the tree
            node = self
            _action = self.REBUILD

        elif trigger == Notifier.CHANGE:
            # For now: we just rebuild from here on down the tree
            node = self
            _action = self.REBUILD

        else:
            raise RuntimeError('Update callback: invalid trigger "%s"' % trigger)

        # do the action or tag the node for later
        _isBlocked = self.sidebar.isBlocked  # explicit for debugging purpose
        if _isBlocked:
            node._postBlockingAction = _action
            return

        elif _action == self.REBUILD:
            # rebuild the tree starting from node
            with self.sidebar.sideBarBlocking(node):
                node.rebuildTree(deleteNotifiers=True)

        elif _action == self.RENAME:
            # rename node
            with self.sidebar.sideBarBlocking(node):
                node.rename()

    def _postBlockingUpdate(self):
        """Do the required action post-blocking; uses self._postBlockingAction
        """

        if self._postBlockingAction == self.REBUILD:
            self.rebuildTree()
            self._postBlockingAction = None
            return  # all the children have been visited, reset and rebuild; we are done

        elif self._postBlockingAction == self.RENAME:
            self.rename()
            self._postBlockingAction = None

        elif self._postBlockingAction is None:
            pass

        else:
            raise RuntimeError('Invalid postBlockingAction %r' % self._postBlockingAction)

        # check the children
        for child in self.children:
            child._postBlockingUpdate()

        return

    @property
    def _tabs(self):
        "Number of tabs depending in self.level"
        return '\t' * self.level

    def __str__(self):
        return '<%s:%r>' % (self.id, self.name)

    def __repr__(self):
        return str(self)


class SidebarTree(SidebarABC):
    """
    A tree item that is fixed, displaying either a name or the pid of the associated V3 core object
    """
    itemType = 'Tree'

    def buildTree(self, parent, parentWidget, sidebar, obj, level=0):
        """Builds the tree from self downward
        """
        super().buildTree(parent=parent, parentWidget=parentWidget, sidebar=sidebar, obj=obj, level=level)  # this will do all the common things
        # make the widget
        # self.widget = self.givenName
        self.widget = self.makeWidget(parentWidget, self.givenName)

        # Build the children
        for itm in self.children:
            itm.buildTree(parent=self, parentWidget=self.widget, sidebar=self.sidebar, obj=self.obj, level=self.level + 1)


class SidebarItem(SidebarTree):
    """
    A static item, displaying either a name or the pid of the associated V3 core object
    Similar to Tree above, but different label
    """
    itemType = 'Item'


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# SidebarClassABC
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SidebarClassABC(SidebarABC):
    """
    ABC to dynamically add type klass items
    """

    def buildTree(self, parent, parentWidget, sidebar, obj=None, level=0):
        """Builds the tree from self downward
        """
        super().buildTree(parent=parent, parentWidget=parentWidget, sidebar=sidebar, obj=obj, level=level)  # this will do all the common things

        # The node does not make a widget but adds the classobjects
        # classObjs = obj._getChildrenByClass(self.klass)
        classObjs = self._getKlassChildren(obj, self.klass)

        # Now dynamically change the tree and add and build the children
        self.children = []
        for classObj in classObjs:

            if 'ClassTreeItems' in self.itemType:
                # if isinstance(self, SidebarClassTreeItems):
                # make a duplicate of the stored children to pass to the new SidebarItem
                children = [child.duplicate() for child in self._children]
                itm = SidebarTree(
                        name=classObj.pid, usePidForName=True, addNotifier=False,
                        callback=self.callback, menuAction=self.menuAction, add2NodesUp=True, children=children
                        )

            else:
                itm = SidebarItem(
                        name=classObj.pid, usePidForName=True, addNotifier=False,
                        callback=self.callback, menuAction=self.menuAction, add2NodesUp=True, children=[]
                        )
            self.children.append(itm)

            # pass the parent widget down the tree
            itm.buildTree(parent=self, parentWidget=self._parentWidget, sidebar=self.sidebar, obj=classObj, level=level)  # class items get same level as parent

    def reset(self, deleteNotifiers=True):
        """Resets the tree from self downward
        """
        super().reset(deleteNotifiers=deleteNotifiers)
        self.children = []


class SidebarClassItems(SidebarClassABC):
    """A number of dynamically added items of type V3 core 'klass'
    """
    itemType = 'ClassItems'

    def __init__(self, name=None, klass=None, addNotifier=True, closed=True,
                 rebuildOnRename='self', callback=None, menuAction=None, children=[], isDraggable=False, **kwds):
        if klass is None:
            raise ValueError('Undefined klass; definition is required for %s to function' % self.__class__.__name__)
        if len(children) > 0:
            raise ValueError('Sidebar "%s" cannot have children' % self.__class__.__name__)

        name = '%s-ClassItems' % klass.className
        super().__init__(name=name, klass=klass, addNotifier=addNotifier, closed=closed, rebuildOnRename=rebuildOnRename,
                         callback=callback, menuAction=menuAction, children=children, isDraggable=isDraggable, **kwds)

    # def reset(self, deleteNotifiers=True):
    #     super().reset(deleteNotifiers=deleteNotifiers)


class SidebarClassTreeItems(SidebarClassABC):
    """A Tree with a number of dynamically added items of type V3 core 'klass'
    """
    itemType = 'ClassTreeItems'

    def __init__(self, name=None, klass=None, addNotifier=True, closed=True,
                 rebuildOnRename='self', callback=None, menuAction=None, children=[], isDraggable=False, **kwds):
        if klass is None:
            raise ValueError('Undefined klass; is required for %s item' % self.__class__.__name__)

        name = '%s-ClassTreeItems' % klass.className
        super().__init__(name=name, klass=klass, addNotifier=addNotifier, closed=closed, rebuildOnRename=rebuildOnRename,
                         callback=callback, menuAction=menuAction, children=children, isDraggable=isDraggable, **kwds)
        self._children = self.children  # Save them for reset/create, as we will dynamically change the tree on building


# class SidebarClassSpectrumGroupTreeItems(SidebarClassTreeItems):
#     """A Tree with a number of dynamically added items of type V3 core 'klass'
#     Modified to respond to changing the list of spectra in a spectrumGroup, subclassed from SidebarClassTreeItems above
#     """
#     itemType = 'SpectrumGroupClassTreeItems'
#     triggers = [Notifier.DELETE, Notifier.CREATE, Notifier.RENAME, Notifier.CHANGE]


class SidebarClassSpectrumTreeItems(SidebarClassABC):
    """A Tree with a number of dynamically added Spectrum instances'
    """
    itemType = 'SpectrumClassTreeItems'

    def __init__(self, name=None, klass=None, addNotifier=True, closed=True,
                 rebuildOnRename='self', callback=None, menuAction=None, children=[], isDraggable=False, **kwds):
        if klass is None:
            raise ValueError('Undefined klass; is required for %s item' % self.__class__.__name__)

        name = '%s-%s' % (self.itemType, klass.className)
        super().__init__(name=name, klass=klass, addNotifier=addNotifier, closed=closed, rebuildOnRename=rebuildOnRename,
                         callback=callback, menuAction=menuAction, children=children, isDraggable=isDraggable, **kwds)
        self._children = self.children  # Save them for reset/create, as we will dynamically change the tree on building

    def setNotifier(self, theObject: 'AbstractWrapperObject', triggers: list, targetName: str, callback: Callable[..., Optional[str]], **kwds) -> Notifier:
        """subclass setNotifier to override classType for spectrumGroups.
        """
        if type(theObject) is SpectrumGroup:

            # special case needs to put the notifier on <project> for <spectra> belonging to spectrumGroups
            theObject = self.sidebar.project
            targetName = self.klass.className
            return super().setNotifier(theObject=theObject, triggers=triggers, targetName=targetName, callback=callback, **kwds)
        else:
            raise RuntimeError('Object is not of type SpectrumGroup')

    def _getKlassChildren(self, obj, klass):
        """Get the children of <obj> by class type <klass>.
        Get the spectra belonging to spectrumGroup.
        """
        return obj._getSpectrumGroupChildrenByClass(klass) if not obj.isDeleted else []


class SidebarClassNmrResidueTreeItems(SidebarClassABC):
    """A Tree with a number of dynamically added items of type V3 core 'klass'
    Objects in the nmrResidues sublist are sorted according to position in nmrChain
    """
    itemType = 'NmrResidueClassTreeItems'

    def __init__(self, name=None, klass=None, addNotifier=True, closed=True,
                 rebuildOnRename='self', callback=None, menuAction=None, children=[], isDraggable=False, **kwds):
        if klass is None:
            raise ValueError('Undefined klass; is required for %s item' % self.__class__.__name__)

        name = '%s-%s' % (self.itemType, klass.className)
        super().__init__(name=name, klass=klass, addNotifier=addNotifier, closed=closed, rebuildOnRename=rebuildOnRename,
                         callback=callback, menuAction=menuAction, children=children, isDraggable=isDraggable, **kwds)
        self._children = self.children  # Save them for reset/create, as we will dynamically change the tree on building

    def _getKlassChildren(self, obj, klass):
        """Get the children of <obj> by class type <klass>.
        Reorder the children according to the order in the nmrChain.
        """
        classObjs = obj._getChildrenByClass(klass)
        classObjs = self._reorderClassObjs(classObjs)

        return classObjs

    def _reorderClassObjs(self, classObjs):
        """Reorder the nmrResidues according to the order in the nmrChain.
        """
        if classObjs:
            nmrChain = classObjs[0].nmrChain
            return nmrChain.nmrResidues

        return classObjs


class SidebarClassCollectionItems(SidebarClassItems):
    """A Tree with a number of dynamically added items of type V3 core 'klass'
    """
    itemType = 'CollectionClassItems'

    def _getKlassChildren(self, obj, klass):
        """Get the children of <obj> by class type <klass>.
        Reorder the children according to the order in the nmrChain.
        """
        classObjs = obj.collections

        return classObjs


#===========================================================================================================
# Callback routines
#===========================================================================================================

def NYI(*args, **kwds):
    info = showInfo('Not implemented yet!',
                    'This function has not been implemented in the current version')


#===========================================================================================================
# SideBar tree structure
#===========================================================================================================

class SideBarStructure(object):
    """
    A class to manage the sidebar
    """

    _sidebarData = (  # "(" just to be able to continue on a new line; \ seems not to work

        SidebarTree('Project', usePidForName=False, klass=Project, closed=False, children=[

            #------ Spectra, PeakLists, MultipletLists, IntegralLists ------
            SidebarTree('Spectra', closed=False, children=[
                SidebarClassTreeItems(klass=Spectrum, callback=_raiseSpectrumPopup(),
                                      menuAction=_openItemSpectrumDisplay(position='right', relativeTo=None), isDraggable=True, children=[
                        SidebarTree('PeakLists', closed=False, children=[
                            SidebarItem('<New PeakList>', callback=_raisePeakListPopup(editMode=False, useParent=True)),

                            SidebarClassItems(klass=PeakList, callback=_raisePeakListPopup(),
                                              menuAction=_openItemPeakListTable(position='left', relativeTo=None), isDraggable=True),
                            ]),
                        SidebarTree('MultipletLists', children=[
                            SidebarItem('<New MultipletList>', callback=_raiseMultipletListPopup(editMode=False, useParent=True)),

                            SidebarClassItems(klass=MultipletList, callback=_raiseMultipletListPopup(),
                                              menuAction=_openItemMultipletListTable(position='left', relativeTo=None), isDraggable=True),
                            ]),
                        SidebarTree('IntegralLists', children=[
                            SidebarItem('<New IntegralList>', callback=_raiseIntegralListPopup(editMode=False, useParent=True)),

                            SidebarClassItems(klass=IntegralList, callback=_raiseIntegralListPopup(),
                                              menuAction=_openItemIntegralListTable(position='left', relativeTo=None), isDraggable=True),
                            ]),
                        ]),
                ]),

            #------ SpectrumGroups ------
            SidebarTree('SpectrumGroups', closed=True, children=[
                SidebarItem('<New SpectrumGroup>', callback=_raiseSpectrumGroupEditorPopup(editMode=False, useNone=True)),

                SidebarClassTreeItems(klass=SpectrumGroup, callback=_raiseSpectrumGroupEditorPopup(),
                                      menuAction=_openItemSpectrumGroupDisplay(position='right', relativeTo=None),
                                      triggers=ALL_NOTIFIERS, isDraggable=True, children=[
                        SidebarClassSpectrumTreeItems(klass=Spectrum, callback=_raiseSpectrumPopup(),
                                                      menuAction=_openItemSpectrumInGroupDisplay(position='right', relativeTo=None), isDraggable=True),
                        ]),
                ]),

            #------ ChemicalShiftLists ------
            SidebarTree('ChemicalShiftLists', closed=True, children=[
                SidebarItem('<New ChemicalShiftList>', callback=_raiseChemicalShiftListPopup(editMode=False, useNone=True)),

                SidebarClassTreeItems(klass=ChemicalShiftList, callback=_raiseChemicalShiftListPopup(),
                                      menuAction=_openItemChemicalShiftListTable(position='left', relativeTo=None), isDraggable=True),
                ]),

            #------ NmrChains, NmrResidues, NmrAtoms ------
            SidebarTree('NmrChains', closed=True, children=[
                SidebarItem('<New NmrChain>', callback=_raiseCreateNmrChainPopup()),

                SidebarClassTreeItems(klass=NmrChain, rebuildOnRename='NmrChain-ClassTreeItems',
                                      callback=_raiseNmrChainPopup(),
                                      menuAction=_openItemNmrChainTable(position='left', relativeTo=None), isDraggable=True, children=[
                        SidebarItem('<New NmrResidue>', callback=_raiseNmrResidueNewPopup(editMode=False)),

                        SidebarClassNmrResidueTreeItems(klass=NmrResidue, rebuildOnRename='NmrChain-ClassTreeItems',
                                                        callback=_raiseNmrResiduePopup(),
                                                        menuAction=_openItemNmrResidueItem(position='left', relativeTo=None), isDraggable=True, children=[
                                SidebarItem('<New NmrAtom>', callback=_raiseNmrAtomNewPopup(editMode=False)),

                                SidebarClassItems(klass=NmrAtom, rebuildOnRename='NmrChain-ClassTreeItems',
                                                  callback=_raiseNmrAtomPopup(),
                                                  menuAction=_openItemNmrAtomItem(position='left', relativeTo=None), isDraggable=True),
                                ]),
                        ]),
                ]),

            #------ Samples, SampleComponents ------
            SidebarTree('Samples', closed=True, children=[
                SidebarItem('<New Sample>', callback=_raiseSamplePopup(editMode=False, useNone=True)),

                SidebarClassTreeItems(klass=Sample, rebuildOnRename='Sample-ClassTreeItems',
                                      callback=_raiseSamplePopup(),

                                      menuAction=_openItemSampleDisplay(position='right', relativeTo=None), isDraggable=True, children=[
                        SidebarItem('<New SampleComponent>', callback=_raiseSampleComponentPopup(useParent=True, newSampleComponent=True)),

                        SidebarClassItems(klass=SampleComponent, rebuildOnRename='Sample-ClassTreeItems',
                                          callback=_raiseSampleComponentPopup(newSampleComponent=False),
                                          menuAction=_openItemSampleComponentTable(position='right', relativeTo=None), isDraggable=True),
                        ]),
                ]),

            #------ Substances ------
            SidebarTree('Substances', closed=True, children=[
                SidebarItem('<New Substance>', callback=_raiseSubstancePopup(newSubstance=True, useNone=True)),

                SidebarClassItems(klass=Substance, callback=_raiseSubstancePopup(newSubstance=False),
                                  menuAction=_openItemSubstanceTable(position='bottom', relativeTo=None), isDraggable=True),
                ]),

            #------ Chains, Residues ------
            SidebarTree('Chains', closed=True, children=[
                SidebarItem('<New Chain>', callback=_raiseNewChainPopup(useParent=True)),

                SidebarClassTreeItems(klass=Chain, rebuildOnRename='Chain-ClassTreeItems',
                                      callback=_raiseChainPopup(),
                                      menuAction=_openItemChainTable(position='bottom', relativeTo=None), isDraggable=True, children=[
                        SidebarClassTreeItems(klass=Residue, rebuildOnRename='Chain-ClassTreeItems',
                                              callback=NYI, menuAction=_openItemResidueTable(position='bottom', relativeTo=None), isDraggable=True,
                                              children=[
                                                  # SidebarItem('<New Atom>', callback=_raiseAtomNewPopup(editMode=False)),

                                                  SidebarClassItems(klass=Atom, rebuildOnRename='Chain-ClassTreeItems',
                                                                    callback=_raiseAtomPopup(),
                                                                    menuAction=_openItemAtomItem(position='left', relativeTo=None), isDraggable=True),
                                                  ]),

                        ]),
                ]),

            #------ Complexes ------
            SidebarTree('Complexes', closed=True, children=[
                SidebarItem('<New Complex>', callback=_raiseComplexEditorPopup(editMode=False, useNone=True)),

                SidebarClassTreeItems(klass=Complex, rebuildOnRename='Complex-ClassTreeItems',
                                      callback=_raiseComplexEditorPopup(),
                                      menuAction=_openItemComplexTable(position='bottom', relativeTo=None),
                                      triggers=ALL_NOTIFIERS, isDraggable=True),
                ]),

            #------ StructureEnsembles ------
            SidebarTree('StructureEnsembles', closed=True, children=[
                SidebarItem('<New StructureEnsemble>', callback=_raiseStructureEnsemblePopup(editMode=False, useNone=True)),

                SidebarClassItems(klass=StructureEnsemble, callback=_raiseStructureEnsemblePopup(),
                                  menuAction=_openItemStructureEnsembleTable(position='bottom', relativeTo=None), isDraggable=True),
                ]),

            #------ StructureData ------
            SidebarTree('StructureData', closed=True, children=[
                SidebarItem('<New StructureData>', callback=_raiseStructureDataPopup(editMode=False, useNone=True)),

                SidebarClassTreeItems(klass=StructureData, rebuildOnRename='StructureData-ClassTreeItems',
                                      callback=_raiseStructureDataPopup(),
                                      menuAction=_openItemStructureDataTable(position='left', relativeTo=None), isDraggable=True, children=[
                        # SidebarItem('<New RestraintTable>', callback=_raiseRestraintTableNewPopup(editMode=False, useNone=False, useParent=True)),
                        # SidebarItem('<New ViolationTable>', callback=_raiseViolationTablePopup(editMode=False, useNone=False, useParent=True)),
                        #
                        # SidebarClassTreeItems(klass=RestraintTable, rebuildOnRename='StructureData-ClassTreeItems',
                        #                           callback=_raiseRestraintTableEditPopup(),
                        #                           menuAction=_openItemRestraintTable(position='left', relativeTo=None), isDraggable=True),
                        #
                        # SidebarClassItems(klass=ViolationTable, callback=_raiseViolationTablePopup(),
                        #                       menuAction=_openItemViolationTable(position='bottom', relativeTo=None), isDraggable=True),

                        SidebarTree('RestraintTables', closed=False, children=[
                            SidebarItem('<New RestraintTable>', callback=_raiseRestraintTableNewPopup(editMode=False, useNone=False, useParent=True)),

                            SidebarClassTreeItems(klass=RestraintTable, rebuildOnRename='StructureData-ClassTreeItems',
                                                  callback=_raiseRestraintTableEditPopup(),
                                                  menuAction=_openItemRestraintTable(position='left', relativeTo=None), isDraggable=True),
                            ]),
                        SidebarTree('ViolationTables', closed=False, children=[
                            SidebarItem('<New ViolationTable>', callback=_raiseViolationTablePopup(editMode=False, useNone=False, useParent=True)),

                            SidebarClassItems(klass=ViolationTable, callback=_raiseViolationTablePopup(),
                                              menuAction=_openItemViolationTable(position='bottom', relativeTo=None), isDraggable=True),
                            ]),
                        ]),
                ]),

            #------ DataTables ------
            SidebarTree('DataTables', closed=True, children=[
                SidebarItem('<New DataTable>', callback=_raiseDataTablePopup(editMode=False, useNone=True)),

                SidebarClassItems(klass=DataTable, callback=_raiseDataTablePopup(),
                                  menuAction=_openItemDataTable(position='bottom', relativeTo=None), isDraggable=True),
                ]),

            #------ Collections ------
            SidebarTree('Collections', closed=True, children=[
                SidebarItem('<New Collection>', callback=_raiseCollectionPopup(editMode=False, useNone=True)),

                SidebarClassCollectionItems(klass=Collection, callback=_raiseCollectionPopup(),
                                            menuAction=_openItemCollectionModule(position='bottom', relativeTo=None), isDraggable=True),
                ]),

            #------ Notes ------
            SidebarTree('Notes', closed=True, children=[
                SidebarItem('<New Note>', callback=_raiseNotePopup(editMode=False, useNone=True)),

                SidebarClassItems(klass=Note, callback=_raiseNotePopup(),
                                  menuAction=_openItemNoteTable(position='bottom', relativeTo=None), isDraggable=True),
                ]),
            ])

    )  # end _sidebarData

    def _init(self):
        self._sidebarBlockingLevel = 0
        self._project = None
        self._sidebar = None

    def reset(self, deleteNotifiers=True):
        """Resets all
        """
        self._sidebarData.reset(deleteNotifiers=deleteNotifiers)

    def clearSideBar(self):
        """Clear the sideBar if widgets and notifiers.
        """
        self._sidebarData.reset(deleteNotifiers=True)

    def buildTree(self, project, clear=True):
        """Builds the tree from project; returns self
        """
        self._project = project
        if clear:
            self.clearSideBar()
        self._sidebarData.buildTree(parent=None, parentWidget=self._sidebar, sidebar=self._sidebar, obj=self._project)  # This is the root

        # set the tree name to the id (not pid)
        self.setProjectName(project)
        return self

    def setProjectName(self, project: Project):
        """(re)Set project name in sidebar header.
        """
        self._sidebarData.widget.setText(0, project.name)
        self._sidebarData.name = project.name

    def rebuildTree(self):
        """Rebuilds the Tree
        """
        self.buildTree(self._project)

    def setSidebar(self, sidebar):
        """Set the sidebar widget
        """
        self._sidebar = sidebar

    def printTree(self, string=None):
        """prints the tree; optionally prints string
        """
        self._sidebarData.printTree(string=string)

    @property
    def isBlocked(self):
        """True if sidebar is blocked
        """
        return self._sidebarBlockingLevel > 0

    @contextmanager
    def sideBarBlocking(self, node):
        """Context manager to handle blocking of the sidebar events.
        """
        self.increaseSidebarBlocking(node)
        try:
            # pass control to the calling function
            yield

        except Exception as es:
            raise es
        finally:
            self.decreaseSidebarBlocking(node)

    def increaseSidebarBlocking(self, node=None, withSideBarUpdate=True):
        """increase level of blocking
        """
        # _tmp = self._sidebarBlockingLevel # just for debugging purpose
        if self._sidebarBlockingLevel == 0:
            self._blockSideBarEvents()
            if withSideBarUpdate:
                if node:
                    node._storeExpandedStates()
                else:
                    self._sidebarData._storeExpandedStates()

        self._sidebarBlockingLevel += 1
        # _tmp = self._sidebarBlockingLevel # just for debugging purpose

    def decreaseSidebarBlocking(self, node=None, withSideBarUpdate=True):
        """Reduce level of blocking - when level reaches zero, Sidebar is unblocked
        """
        # _tmp = self._sidebarBlockingLevel # just for debugging purpose

        if self._sidebarBlockingLevel == 0:
            raise RuntimeError('Error: cannot decrease sidebar blocking below 0')

        self._sidebarBlockingLevel -= 1
        # check if we arrived at level zero; if so call post-blocking update
        if self._sidebarBlockingLevel == 0:
            self._sidebarData._postBlockingUpdate()
            if withSideBarUpdate:
                if node:
                    node._restoreExpandedStates()
                else:
                    self._sidebarData._restoreExpandedStates()
            self._unblockSideBarEvents()

        # _tmp = self._sidebarBlockingLevel # just for debugging purpose

    def getSideBarItem(self, name):
        """Search for a named item in the tree
        """
        return self._sidebarData.get(name)

    @staticmethod
    def _setBlankingState(self, value):
        """Set the blanking state of the nodes.
        """
        self.setBlankingAllNotifiers(value)

    def setBlankingAllNotifiers(self, value):
        self._sidebarData._traverseKlassTree(self, self._setBlankingState, value)


#===========================================================================================================
# New sideBar to handle new notifiers
#===========================================================================================================


from ccpn.ui.gui.widgets.ListView import ListView


SIDEBARROW = 0
RESULTSWIDGETROW = 1
SEARCHWIDGETROW = 2


class SideBar(QtWidgets.QTreeWidget, SideBarStructure, Base, NotifierBase):
    """
    New sideBar class with new sidebar tree handling
    """

    def __init__(self, parent=None, mainWindow=None, multiSelect=True,
                 searchWidgetContainer=None, searchResultsContainer=None, **kwds):

        super().__init__(parent)
        Base._init(self, acceptDrops=True, **kwds)
        SideBarStructure._init(self)

        self.multiSelect = multiSelect
        if self.multiSelect:
            self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.mainWindow = mainWindow
        self.application = self.mainWindow.application

        self._parent = parent

        # link to the frame containing ONLY the sideBar, assume at position (0,0)
        self._searchWidgetContainer = searchWidgetContainer
        self._searchResultsContainer = searchResultsContainer

        _height = getFontHeight()
        setWidgetFont(self, name=SIDEBARFONT)

        self.header().hide()
        self.setDragEnabled(True)
        self.setExpandsOnDoubleClick(False)
        self.setMinimumWidth(200)

        self.setDragDropMode(self.DragDrop)
        self.setAcceptDrops(True)

        self.setGuiNotifier(self, [GuiNotifier.DROPEVENT], [DropBase.URLS, DropBase.PIDS],
                            self.mainWindow._processDroppedItems)

        self.itemDoubleClicked.connect(self._raiseObjectProperties)

        # create a search box at the bottom of the sidebar frame container
        txt = 'Search Pid/String e.g Sp:H*qC'
        self._searchWidget = LineEdit(self._searchWidgetContainer, backgroundText=txt, grid=(SEARCHWIDGETROW, 0))
        self._searchWidget.textChanged.connect(self._searchWidgetCallback)

        # create a results box
        self._resultsFrame = self._searchResultsContainer

        self._resultsLabel = Label(self._resultsFrame, text='Search Results', grid=(0, 0))
        self._resultsLabel.setAlignment(QtCore.Qt.AlignCenter)
        self._resultsLabel.setContentsMargins(0, 0, 0, 0)
        self._resultsList = SideBarSearchListView(self._resultsFrame, mainWindow=self.mainWindow, grid=(0, 0), fitToContents=True,
                                                  listViewContainer=self._resultsFrame, multiSelect=True)

        # frame can collapse to nothing
        self._resultsFrame.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self._resultsList.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self._resultsFrame.getLayout().setSpacing(6)
        self._resultsFrame.getLayout().addWidget(self._resultsList, 2, 0)
        self._resultsFrame.setVisible(False)
        self._resultsFrame.setContentsMargins(2, 2, 0, 2)
        # self._resultsFrame.getLayout().setMargin(0)  # deprecated?

        self._results_model = QtCore.QStringListModel()
        self._results_list = []
        self._results_model.setStringList(self._results_list)

        self._resultsList.setModel(self._results_model)
        self._resultsList.selectionModel().selectionChanged.connect(self._resultsListSelection)
        self._resultsList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._resultsList.customContextMenuRequested.connect(self._resultsListMenuRequested)

        # set the new sidebar font
        setWidgetFont(self._searchWidget, name=SIDEBARFONT)
        setWidgetFont(self._resultsLabel, name=SIDEBARFONT)
        setWidgetFont(self._resultsList, name=SIDEBARFONT)

        self._searchSelection = []
        self._searchNotifiers = []
        self._setStyle()

    def _setStyle(self):
        """Set the focus/noFocus colours for the widget
        """
        _style = """QTreeWidget {
                        border: 1px solid palette(mid);
                        border-radius: 2px;
                    }
                    QTreeWidget:focus {
                        border: 1px solid palette(highlight);
                        border-radius: 2px;
                    }
                    """
        # set stylesheet - this seems to miss the first paint event
        self.setStyleSheet(_style)

    def _resultsListMenuRequested(self, position):

        dataPid = self._searchSelection[0]
        objs = [self.project.getByPid(dataPid)]

        sideBarObject = self._sidebarData.findChildNode(dataPid)

        menuAction = sideBarObject.menuAction
        if menuAction:
            globalPosition = self._resultsList.mapToGlobal(QtCore.QPoint(position.x(), position.y() + 10))

            # can't do menu action on anything other than main window as it looks for sub fields of main window...
            menuAction(self.mainWindow, dataPid, sideBarObject, globalPosition, objs)

    def _resultsListSelection(self, rowSelection, columnSelection):

        _selection = rowSelection.indexes()
        if _selection:
            row = _selection[0].row()
            pid = self._results_list[row]
            self._searchSelection.clear()
            self._searchSelection.append(pid)

            # call the original search selection
            self._searchWidgetSideBarCallback(pid)

    def _clearQTreeWidget(self, tree):
        """Clear contents of the sidebar.
        """
        iterator = QtWidgets.QTreeWidgetItemIterator(tree, QtWidgets.QTreeWidgetItemIterator.All)
        while iterator.value():
            iterator.value().takeChildren()
            iterator += 1
        i = tree.topLevelItemCount()
        while i > -1:
            tree.takeTopLevelItem(i)
            i -= 1

    def buildTree(self, project, clear=True):
        """Build the new tree structure from the project.
        """
        # self._clearQTreeWidget(self)
        if clear:
            self.clearSideBar()
        self.project = project
        self.setSidebar(sidebar=self)
        super().buildTree(project, clear=False)  # We optionally already did a clear

    def _raiseObjectProperties(self, item):
        """Get object from Pid and dispatch call depending on type.
        """
        dataPid = item.data(0, QtCore.Qt.DisplayRole)
        sideBarObject = item.data(1, QtCore.Qt.UserRole)
        callback = sideBarObject.callback

        if callback:
            callback(self.mainWindow, dataPid, sideBarObject)

    def getSelectedObjects(self):
        """
        Get a list of selected V3 Core objects
        """
        objs = []
        for item in self.selectedItems():
            if item is not None:
                dataPid = item.data(0, QtCore.Qt.DisplayRole)
                objFromPid = self.project.getByPid(dataPid)
                if objFromPid is not None:
                    objs.append(objFromPid)
        return objs

    def clearSideBar(self):
        """Completely clear and reset the sidebar of widgets and notifiers.
        """
        super().clearSideBar()
        self._clearQTreeWidget(self)

    def mouseReleaseEvent(self, event):
        """Re-implementation of the mouse press event so right click can be used to delete items from the
        sidebar.
        """
        if event.button() == QtCore.Qt.RightButton:
            self._raiseContextMenu(event)
            event.accept()
        elif event.button() == QtCore.Qt.MiddleButton:
            self._copyHoverPID()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

        self._dragStartPosition = None
        self._pids = None
        self._mouseButton = None

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Keep a list of the selected items when the left mouse button is pressed
        """

        def _treeOrder(item):
            try:
                _, data = item
                # should give a string of the form 'Tree-<n>'
                return int(data.id[5:])
            except:
                # default to go to the bottom of the list
                return 1e8

        # call superclass to update selected items
        super(SideBar, self).mousePressEvent(event)

        if event.button() == QtCore.Qt.LeftButton:
            # keep the list if left button pressed
            self._dragStartPosition = event.pos()
            pids = OrderedSet()

            _projectItem = self.invisibleRootItem().child(0)
            # get the list of items with ids and sort by order in tree
            _items = [(item, item.data(1, QtCore.Qt.UserRole)) for item in self.selectedItems()
                      if item and item.data(1, QtCore.Qt.UserRole) and isinstance(item.data(1, QtCore.Qt.UserRole).id, str)]
            _items = sorted(_items, key=lambda item: _treeOrder(item))
            for item, data in _items:
                if data and data.obj:
                    if not (item != _projectItem and isinstance(data.obj, Project)):
                        pids.add(str(data.obj.pid))

            self._pids = list(pids) or None
        else:
            self._dragStartPosition = None
            self._pids = None

        self._mouseButton = event.button()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        """Create a mouse drag event with the selected items when dragging with the left button
        """
        if self._mouseButton == QtCore.Qt.LeftButton and self._pids:
            if (event.pos() - self._dragStartPosition).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                makeDragEvent(self, {'pids': self._pids}, self._pids, '\n'.join(self._pids))

    # def dragEnterEvent(self, event):
    #     """Handle drag enter event to create a new drag/drag item.
    #     """
    #     if event.mimeData().hasUrls():
    #         event.accept()
    #     else:
    #         pids = []
    #         for item in self.selectedItems():
    #             if item is not None:
    #
    #                 dataPid = item.data(0, QtCore.Qt.DisplayRole)
    #                 sideBarObject = item.data(1, QtCore.Qt.UserRole)
    #
    #                 if sideBarObject.obj:
    #                     pids.append(str(sideBarObject.obj.pid))
    #
    #         itemData = json.dumps({'pids': pids})
    #
    #         tempData = QtCore.QByteArray()
    #         stream = QtCore.QDataStream(tempData, QtCore.QIODevice.WriteOnly)
    #         stream.writeQString(itemData)
    #         event.mimeData().setData(ccpnmrJsonData, tempData)
    #         event.mimeData().setText(itemData)
    #
    #         event.accept()

    def dragMoveEvent(self, event):
        """Required function to enable dragging and dropping within the sidebar.
        """
        if event.mimeData().hasUrls():
            # accept external events
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            if isinstance(event.source(), (SideBar, SideBarSearchListView)):
                # disable/ignore internal move events
                event.ignore()
            else:
                super().dragMoveEvent(event)

    def _displaySelectedSpectrum(self, text):
        if text is not None:
            objFromPid = self.project.getByPid(text)
            strip = self.application.current.strip

            # with undoBlockWithoutSideBar():
            with undoStackBlocking() as _:  # Do not add to undo/redo stack
                with notificationEchoBlocking():
                    if strip:
                        spectrumDisplay = strip.spectrumDisplay
                        spectrumDisplay.clearSpectra()
                        if isinstance(objFromPid, Spectrum):
                            spectrumDisplay.displaySpectrum(objFromPid)
                        if isinstance(objFromPid, SpectrumGroup):
                            if not strip.spectrumDisplay.isGrouped:
                                for sp in objFromPid.spectra:
                                    spectrumDisplay.displaySpectrum(sp)
                        if isinstance(objFromPid, Sample):
                            strip.setStackingMode(False)
                            _openItemSampleDisplay._openSampleSpectraOnDisplay(objFromPid, strip.spectrumDisplay)
                            # v = strip._getInitialOffset()
                            strip.setStackingMode(True)

    def keyPressEvent(self, e):
        """
        Re-implementation of key press events.
        N.B. Experimental: Ctrl+up/down to display previous/next compatible spectrum on current strip.
        """
        k = QtCore.Qt
        if e.modifiers() & QtCore.Qt.ControlModifier and e.key() in [k.Key_Up, k.Key_Down, k.Key_Left, k.Key_Right]:
            self.clearSelection()
            self.setCurrentItem(self.currentItem())
            if e.key() == QtCore.Qt.Key_Up:
                self._displaySelectedSpectrum(self.currentItem().text(0))
            if e.key() == QtCore.Qt.Key_Down:
                self._displaySelectedSpectrum(self.currentItem().text(0))
        super().keyPressEvent(e)

    def _cloneObject(self, objs):
        """Clones the specified objects.
        """
        for obj in objs:
            obj.clone()

    def _raiseContextMenu(self, event: QtGui.QMouseEvent):
        """Creates and raises a context menu enabling items to be deleted from the sidebar.
        """
        contextMenu = Menu('', self, isFloatWidget=True)

        objs = []
        # get the list of items selected
        for item in self.selectedItems():
            if item is not None:
                dataPid = item.data(0, QtCore.Qt.DisplayRole)
                objFromPid = self.project.getByPid(dataPid)
                if objFromPid is not None:
                    objs.append(objFromPid)

        # get the item clicked
        if objs and (_itemPressed := self.itemAt(event.pos())):
            dataPid = _itemPressed.data(0, QtCore.Qt.DisplayRole)
            sideBarObject = _itemPressed.data(1, QtCore.Qt.UserRole)

            menuAction = sideBarObject.menuAction
            if menuAction:
                menuAction(self.mainWindow, dataPid, sideBarObject,
                           QtCore.QPoint(event.globalPos().x(), event.globalPos().y() + 10),
                           objs)

    def _copyHoverPID(self):
        """Copies the PID object an object to the clipboard
        """
        for item in self.selectedItems():
            if item is not None:
                dataPid = item.data(0, QtCore.Qt.DisplayRole)
                if objFromPid := self.project.getByPid(dataPid):
                    copyToClipboard([objFromPid])


    # def _deleteItemObject(self, objs):
    #     """Removes the specified item from the sidebar and deletes it from the project.
    #     NB, the clean-up of the side bar is done through notifiers
    #     """
    #     from ccpn.core.lib.ContextManagers import undoBlock, undoBlockWithoutSideBar, notificationEchoBlocking
    #     from ccpn.util.Logging import getLogger
    #
    #     try:
    #         getLogger().info('Deleting: %s' % ', '.join(map(str, objs)))
    #         with undoBlockWithoutSideBar():
    #             with notificationEchoBlocking():
    #                 self.project.deleteObjects(*objs)
    #             # for obj in objs:
    #             #     if obj:
    #             #         # just delete the object
    #             #         obj.delete()
    #
    #     except Exception as es:
    #         showWarning('Delete', str(es))
    #
    #     #  Force repaint if GL windows
    #     from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier
    #
    #     GLSignals = GLNotifier(parent=self)
    #     GLSignals.emitEvent(triggers=[GLNotifier.GLALLPEAKS, GLNotifier.GLALLINTEGRALS, GLNotifier.GLALLMULTIPLETS])

    def _blockSideBarEvents(self):
        """Block all updates/signals/notifiers on the sidebar
        """
        # self.setUpdatesEnabled(False)
        self.blockSignals(True)
        # self.setBlankingAllNotifiers(True)

    def _unblockSideBarEvents(self):
        """Unblock all updates/signals/notifiers on the sidebar
        """
        # self.setBlankingAllNotifiers(False)
        self.blockSignals(False)
        # self.setUpdatesEnabled(True)

    def selectPid(self, pid):
        """Select the item in the sideBar with the given pid.
        """
        self.clearSelection()
        item = self._sidebarData.findChildNode(pid)
        if item and item.widget:
            self.setCurrentItem(item.widget)
            self.setFocus()
            self.expandItem(item.widget.parent())

    def _searchWidgetSideBarCallback(self, pid):
        """Private callback from search widget
        """
        # text = self._searchWidget.get()
        obj = self.project.getByPid(pid)
        if obj:
            self.selectPid(obj.pid)
        # else:
        #     showWarning('Search', 'Not found')

    def _searchWidgetCallback(self):
        """Private callback from search widget"""

        LOWER_TO_UPPER = 'lower_to_upper'
        SEARCH_LIST = 'search_list'

        text = self._searchWidget.get()

        self._results_list.clear()
        if len(text) == 0:
            self._searchWidget.setClearButtonEnabled(False)
            self._results_model.setStringList(self._results_list)
            self._resultsFrame.setVisible(False)
            return
        else:
            self._searchWidget.setClearButtonEnabled(True)

        if len(text) > 0 and text[-1] == ' ':
            new_text = text[:-1] + '␣'
            self._searchWidget.setText(new_text)
            return

        # seems to look at more objects than expected
        def _buildNameMapAndSearchList(wrapper, result):
            result[LOWER_TO_UPPER][wrapper.klass.shortClassName.lower()] = wrapper.klass.shortClassName
            result[LOWER_TO_UPPER][wrapper.klass.className.lower()] = wrapper.klass.className

            result[SEARCH_LIST].add(wrapper.klass.shortClassName.lower())
            result[SEARCH_LIST].add(wrapper.klass.className.lower())

        result = {SEARCH_LIST: OrderedSet(), LOWER_TO_UPPER: {}}

        self._sidebarData._traverseKlassTree(sidebar=self, func=_buildNameMapAndSearchList, data=result)

        searchables = OrderedSet()

        lower_text = text.lower()
        lower_text = lower_text.lstrip('*')

        if ':' in lower_text:
            fields = lower_text.split(':')
            lower_category = fields[0]
        else:
            cutoff = min(len(lower_text), 3)
            lower_category = '%s*' % lower_text[:cutoff]

        for key in result[SEARCH_LIST]:
            if fnmatch.fnmatch(key, lower_category):
                searchables.add(key)

        if len(searchables) == 0:
            searchables = result[SEARCH_LIST]

        lower_to_upper = result[LOWER_TO_UPPER]

        seen = set()

        if (len(lower_text) > 0) and (lower_text[-1] == '␣'):
            lower_text = '*%s' % lower_text.rstrip('␣')
        else:
            lower_text = '*%s*' % lower_text

        for key in searchables:
            pid_key = lower_to_upper[key]

            _pid2Obj = self.project._pid2Obj
            if pid_key in _pid2Obj:
                for elem in _pid2Obj[pid_key]:
                    elem_key = "%s:%s" % (key, str(elem))

                    if not _pid2Obj[pid_key][elem].isDeleted:
                        if fnmatch.fnmatch(elem_key.lower(), lower_text):
                            if elem not in seen:
                                self._results_list.append('%s:%s' % (pid_key, str(elem)))
                                seen.add(elem)

        self._results_model.setStringList(self._results_list)
        if len(self._results_list) > 0:
            self._resultsFrame.setVisible(True)
        else:
            self._resultsFrame.setVisible(False)

        # self._resultsFrame.setMaximumHeight(self._resultsFrame.sizeHint().height())
        # self._resultsFrame.updateGeometry()
        # self._resultsList.adjustSize()

    def _notify_pids_changed(self, *args, **kwargs):
        self._searchWidgetCallback()


class SideBarSearchListView(ListView):
    """
    Class that allows items from listView to be dropped into the dropArea
    """
    pass


#------------------------------------------------------------------------------------------------------------------
# Emulate V3 objects
#------------------------------------------------------------------------------------------------------------------

class Obj():
    def __init__(self, klass, *ids):
        self.klass = klass
        self.pid = Pid.new(klass.shortClassName, *ids)

    def _getChildrenByClass(self, klass):
        # emulate klass objs
        classObjs = []
        for i in range(2):
            id = '%s_%s' % (klass.className, i)
            classObjs.append(Obj(klass, self.pid.id, id))
        return classObjs

    def __str__(self):
        return '<Obj:%r>' % self.pid

    def __repr__(self):
        return str(self)


#------------------------------------------------------------------------------------------------------------------
# Testing
#------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    print('\n')

    # pid = Pid.new('PR','test')
    project = Obj(Project, 'test')

    sidebar = SideBarStructure()
    sidebar.printTree('\n==> before building')

    sidebar.buildTree(project)
    sidebar.printTree('\n==> after building')

    project.pid = Pid.new('PR', 'test2')
    sidebar._sidebarData.rename()
    sidebar.printTree('\n==> after project rename')

    # sidebar.reset()
    # sidebar.printTree('\n==> after reset')
    # sidebar.buildTree(project)

    subTree = sidebar._sidebarData.get('Project', 'Spectra')
    subTree.printTree('\n--- subtree ---')
    subTree.reset()
    sidebar.printTree('\n==> after subtree reset')
    sidebar.increaseSidebarBlocking()
    subTree._update({'trigger': 'create'})
    sidebar.printTree('\n==> after blocked update')
    sidebar.decreaseSidebarBlocking()
    sidebar.printTree('\n==> after decrease blocking')
