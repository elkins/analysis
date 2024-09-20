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
__dateModified__ = "$dateModified: 2024-09-04 18:51:19 +0100 (Wed, September 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-05-28 10:28:42 +0000 (Sun, May 28, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================


from PyQt5 import QtGui, QtWidgets, QtCore
from functools import partial
from typing import Optional
from ccpn.ui.gui.widgets.Base import Base
from ccpn.core.Chain import Chain
from ccpn.core.ChemicalShiftList import ChemicalShiftList
from ccpn.core.RestraintTable import RestraintTable
from ccpn.core.PeakList import PeakList
from ccpn.core.IntegralList import IntegralList
from ccpn.core.MultipletList import MultipletList
from ccpn.core.Sample import Sample
from ccpn.core.Substance import Substance
from ccpn.core.NmrChain import NmrChain
from ccpn.core.StructureData import StructureData
from ccpn.core.ViolationTable import ViolationTable
from ccpn.core.Complex import Complex
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.core.Note import Note
from ccpn.core.Project import Project
from ccpn.core.DataTable import DataTable
from ccpn.core.Collection import Collection
from ccpn.ui.gui.guiSettings import getColours, BORDERFOCUS, BORDERNOFOCUS
from ccpn.util.nef import StarIo
from ccpn.util.OrderedSet import OrderedSet
from ccpn.framework.lib.ccpnNef.CcpnNefCommon import _traverse, nef2CcpnMap, _isALoop, nef2CcpnClassNames
from ccpn.ui.gui.widgets.Menu import Menu


# TODO These should maybe be consolidated with the same constants in CcpnNefIo
# (and likely those in Project)
CHAINS = 'chains'
NMRCHAINS = 'nmrChains'
RESTRAINTTABLES = 'restraintTables'
CCPNTAG = 'ccpn'
SKIPPREFIXES = 'skipPrefixes'
EXPANDSELECTION = 'expandSelection'
INCLUDEORPHANS = 'includeOrphans'
SPECTRA = 'spectra'
RENAMEACTION = 'rename'
BADITEMACTION = 'badItem'


class ProjectTreeCheckBoxes(QtWidgets.QTreeWidget, Base):
    """Class to handle a tree view created from a project
    """
    checkStateChanged = QtCore.pyqtSignal(QtWidgets.QTreeWidgetItem, int)

    # set the items in the project that can be exported
    checkList = [
        Chain._pluralLinkName,
        ChemicalShiftList._pluralLinkName,
        RestraintTable._pluralLinkName,
        PeakList._pluralLinkName,
        IntegralList._pluralLinkName,
        MultipletList._pluralLinkName,
        Sample._pluralLinkName,
        Substance._pluralLinkName,
        NmrChain._pluralLinkName,
        StructureData._pluralLinkName,
        ViolationTable._pluralLinkName,
        Complex._pluralLinkName,
        SpectrumGroup._pluralLinkName,
        Note._pluralLinkName,
        # _PeakCluster._pluralLinkName,
        DataTable._pluralLinkName,
        Collection._pluralLinkName
        ]

    # set which items can be selected/deselected, others are automatically set
    selectableItems = [
        Chain._pluralLinkName,
        ChemicalShiftList._pluralLinkName,
        RestraintTable._pluralLinkName,
        NmrChain._pluralLinkName,
        PeakList._pluralLinkName,
        IntegralList._pluralLinkName,
        MultipletList._pluralLinkName,
        # _PeakCluster._pluralLinkName,
        ]

    lockedItems = {
        # Sample._pluralLinkName       : QtCore.Qt.Checked,
        # Substance._pluralLinkName    : QtCore.Qt.Checked,
        # StructureData._pluralLinkName: QtCore.Qt.Checked,
        # Complex._pluralLinkName      : QtCore.Qt.Checked,
        # SpectrumGroup._pluralLinkName: QtCore.Qt.Checked,
        # Note._pluralLinkName         : QtCore.Qt.Checked
        }

    mouseRelease = QtCore.pyqtSignal()

    def __init__(self, parent=None, project=None, maxSize=(250, 300),
                 includeProject=False, enableCheckBoxes=True, multiSelect=False,
                 enableMouseMenu=False, pathName=None,
                 **kwds):
        """Initialise the widget
        """
        super().__init__(parent)
        Base._init(self, setLayout=False, **kwds)

        # self.setMaximumSize(*maxSize)
        self.headerItem = self.invisibleRootItem()  # QtWidgets.QTreeWidgetItem()
        self.projectItem = None
        self.project = project
        self.includeProject = includeProject
        self._enableCheckBoxes = enableCheckBoxes
        self._enableMouseMenu = enableMouseMenu
        self._pathName = pathName
        self._currentContextMenu = None
        self._postMenuSetup = None

        self.multiSelect = multiSelect
        if self.multiSelect:
            self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.header().hide()
        self.populate(self.project)

        self.itemClicked.connect(self._clicked)
        self.itemChanged.connect(self._itemChanged)

        self._actionCallbacks = {}

        self._setStyle()
        self._backgroundColour = self.invisibleRootItem().background(0)
        self._foregroundColour = self.invisibleRootItem().foreground(0)

    @staticmethod
    def _depth(item):
        depth = 0
        while item:
            item = item.parent()
            depth += 1
        return depth

    def setActionCallback(self, name, func=None):
        """Add an action to the callback dict
        """
        if name:
            if func:
                self._actionCallbacks[name] = func
            else:
                if name in self._actionCallbacks:
                    del self._actionCallbacks[name]

    def setPostMenuAction(self, func):
        self._postMenuSetup = func

    def clearActionCallbacks(self):
        """Clear the action callback dict
        """
        self._actionCallback = {}

    def setBackgroundForRow(self, item, colour):
        """Set the background colour for all items in the row
        """
        # NOTE:ED - this works for most of the row, not the left-hand side yet
        for col in range(self.columnCount()):
            item.setBackground(col, colour)

    def setForegroundForRow(self, item, colour):
        """Set the foreground colour for all items in the row
        """
        # NOTE:ED - this works for most of the row, not the left-hand side yet
        for col in range(self.columnCount()):
            item.setForeground(col, colour)

    def populate(self, project=None):
        """Populate the contents of the treeView from the project
        """
        if not isinstance(project, (Project, type(None))):
            raise TypeError('project must be of type Project or None')

        self.clear()
        if project:
            with self.blockWidgetSignals():
                # disable events while populating
                self._populateTreeView(project)

    def _populateTreeView(self, project=None):
        if project:
            # set the new project if required
            self.project = project

        checkable = QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable
        if self.includeProject:
            # add the project as the top of the tree - allows to un/select all

            self.projectItem = _StoredTreeWidgetItem(self.invisibleRootItem())
            self.projectItem.setText(0, self.project.name)
            if self._enableCheckBoxes:
                self.projectItem.setFlags(self.projectItem.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
            else:
                self.projectItem.setFlags(self.projectItem.flags() & ~(QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable))
            self.projectItem.setExpanded(True)
            self.headerItem = self.projectItem

        for name in self.checkList:
            if hasattr(self.project, name):  # just to be safe

                item = _StoredTreeWidgetItem(self.headerItem)
                item.setText(0, name)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)

                for obj in getattr(self.project, name):

                    child = _StoredTreeWidgetItem(item)
                    if self._enableCheckBoxes:
                        child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                    else:
                        child.setFlags(child.flags() & ~QtCore.Qt.ItemIsUserCheckable)
                    child.setData(1, 0, obj)
                    child.setText(0, obj.pid)
                    if self._enableCheckBoxes:
                        child.setCheckState(0, QtCore.Qt.Unchecked)

                item.setExpanded(False)
                if name in self.lockedItems:
                    item.setDisabled(True)
                    if self._enableCheckBoxes:
                        item.setCheckState(0, self.lockedItems[name])
                else:
                    if self._enableCheckBoxes:
                        item.setCheckState(0, QtCore.Qt.Checked)

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

    def getObjects(self, includeRoot=False):
        """Get all objects from the tree
        """
        allObjects = []

        for item in self.findItems('', QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive):
            obj = item.data(1, 0)

            # return items in the tree that have a pid
            if hasattr(obj, 'pid'):
                if self.projectItem and item == self.projectItem and not includeRoot:
                    continue

                allObjects += [obj]

        return allObjects

    def getSelectedObjects(self, includeRoot=False):
        """Get selected objects from the check-boxes
        """
        selectedObjects = []

        for item in self.findItems('', QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive):
            if item.checkState(0) == QtCore.Qt.Checked:
                obj = item.data(1, 0)

                # return items in the tree that have a pid
                if hasattr(obj, 'pid'):
                    if self.projectItem and item == self.projectItem and not includeRoot:
                        continue

                    selectedObjects += [obj]

        return selectedObjects

    def getSelectedItems(self, includeRoot=False):
        """Get selected objects from the check-boxes
        """
        selectedItems = []

        for item in self.findItems('', QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive):
            if item.checkState(0) == QtCore.Qt.Checked:
                obj = item.data(1, 0)

                # return items in the tree that are group labels (bottom level should be objects with pids)
                if not hasattr(obj, 'pid'):
                    if self.projectItem and item == self.projectItem and not includeRoot:
                        continue
                    selectedItems += [item.text(0)]

        return selectedItems

    def getSelectedPids(self, includeRoot=False):
        """Get checked text items from the tree for items that have a Pid
        """
        selectedItems = []

        for item in self.findItems('', QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive):
            if item.checkState(0) == QtCore.Qt.Checked:
                obj = item.data(1, 0)

                # return items in the tree that are group labels (bottom level should be objects with pids)
                if hasattr(obj, 'pid'):
                    if self.projectItem and item == self.projectItem and not includeRoot:
                        continue
                    selectedItems += [item.text(0)]

        return selectedItems

    def getCheckStateItems(self, includeRoot=False):
        """Get checked state of objects
        """
        return {val.text(0): val.checkState(0) for val in self.findItems('', QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive)
                }

    def getSelectedObjectsPids(self, includeRoot=False):
        """Get the pids of the selected objects
        """
        pids = []
        for item in self.getSelectedObjects(includeRoot=includeRoot):
            pids += [item.pid]
        return pids

    def selectObjects(self, pids):
        """Handle changing the state of check-boxes
        """
        if self._enableCheckBoxes:
            items = self.findItems('', QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive)
            for item in items:
                if item.text(0) in pids:
                    item.setCheckState(0, QtCore.Qt.Checked)

    def _clicked(self, item, *args):
        if self._enableCheckBoxes:
            for _item in self.findItems('', QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive):
                if _item.text(0) in self.lockedItems:
                    _item.setCheckState(0, self.lockedItems[_item.text(0)])

    def _itemChanged(self, item, column: int) -> None:
        if column == 0 and hasattr(item, 'storedCheckedState') and item.storedCheckedState != item.checkState(0):
            item.storedCheckedState = item.checkState(0)
            self.checkStateChanged.emit(item, column)

    def _uncheckAll(self, includeRoot=False):
        """Clear all selection
        """
        if self._enableCheckBoxes:
            for itemTree in self.findItems('', QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive):
                for i in range(itemTree.childCount()):
                    itemTree.child(i).setCheckState(0, QtCore.Qt.Unchecked)

    def traverseTree(self, root=None, preOrder=True, childrenOnly=True):
        """Traverse the tree items in preOrder/postOrder
        InOrder does not apply as the tree currently does not have left/right branches

        :param root: root of the tree, if None defaults to the invisibleRootItem
        :param preOrder: True/False; True yields the nodes first
        :param childrenOnly: True/False; only yield items that are at the bottom of a branch,
                            i.e., no further descendents
        :return: yields tree items at each iteration
        """

        def recurse(parent):
            for chCount in range(parent.childCount()):
                child = parent.child(chCount)
                # if preOrder then yield the node first
                if preOrder and (child.childCount() == 0 or not childrenOnly):
                    yield child
                if child.childCount():
                    yield from recurse(child)
                # if preOrder then yield the node last
                if not preOrder and (child.childCount() == 0 or not childrenOnly):
                    yield child

        root = root or self.invisibleRootItem()
        if root is not None:
            yield from recurse(root)

    def mouseReleaseEvent(self, event):
        """Re-implementation of the mouse press event so right click can be used to delete items from the
        sidebar.
        """
        if event.button() == QtCore.Qt.RightButton and self._enableMouseMenu:
            self.raiseContextMenu(event)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

            self.mouseRelease.emit()

    def raiseContextMenu(self, ev):
        """Handle raising  context menu for a treeview object
        """
        # MUST BE SUBCLASSED
        raise NotImplementedError("Code error: function not implemented")


class ExportTreeCheckBoxes(ProjectTreeCheckBoxes):
    """Class to handle exporting peaks/integrals/multiplets to nef files
    """

    def _populateTreeView(self, project=None):
        if project:
            # set the new project if required
            self.project = project

        checkable = QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable
        if self.includeProject:
            # add the project as the top of the tree - allows to un/select all

            self.projectItem = _StoredTreeWidgetItem(self.invisibleRootItem())
            self.projectItem.setText(0, self.project.name)
            if self._enableCheckBoxes:
                self.projectItem.setFlags(self.projectItem.flags() | checkable)
            else:
                self.projectItem.setFlags(self.projectItem.flags() & ~checkable)
            self.projectItem.setExpanded(True)
            self.headerItem = self.projectItem

        for name in self.checkList:
            if (projectItems := getattr(self.project, name, [])):
                item = _StoredTreeWidgetItem(self.headerItem)
                item.setText(0, name)
                item.setFlags(item.flags() | checkable)

                for obj in projectItems:  # getattr(self.project, name):

                    child = _StoredTreeWidgetItem(item)
                    if self._enableCheckBoxes:
                        child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                    else:
                        child.setFlags(child.flags() & ~QtCore.Qt.ItemIsUserCheckable)
                    child.setData(1, 0, obj)
                    child.setText(0, obj.pid)
                    if self._enableCheckBoxes:
                        child.setCheckState(0, QtCore.Qt.Unchecked)

                item.setExpanded(False)
                if name in self.lockedItems:
                    item.setDisabled(True)
                    if self._enableCheckBoxes:
                        item.setCheckState(0, self.lockedItems[name])
                else:
                    if self._enableCheckBoxes:
                        item.setCheckState(0, QtCore.Qt.Checked)

        # # extra tree item if needed later
        # self.emptyItem = _StoredTreeWidgetItem(self.invisibleRootItem())
        # self.emptyItem.setExpanded(True)
        # self.emptyItem.setDisabled(True)
        # self.setRowHidden(self.indexFromItem(self.emptyItem, 1).row(),
        #                   QtCore.QModelIndex(), True)

        for name in self.checkList:
            if not getattr(self.project, name, []):
                item = _StoredTreeWidgetItem(self.invisibleRootItem())

                item.setText(0, name + ' (empty)')
                item.setExpanded(False)
                item.setDisabled(True)


class _StoredTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, parent, depth=0):
        super().__init__(parent)
        self.storedCheckedState: QtCore.Qt.CheckState = self.checkState(0)
        self.depth: int = depth
        self._lastState = {}

    def setCheckState(self, column: int, state: QtCore.Qt.CheckState) -> None:
        # The check-box in the first column:
        if column == 0:
            self.storedCheckedState = state
        return super().setCheckState(column, state)


class ImportTreeCheckBoxes(ProjectTreeCheckBoxes):
    """Class to handle importing peaks/integrals/multiplets from nef files
    """
    # set which items can be selected/deselected, others are automatically set
    checkList = [
        Chain._pluralLinkName,
        ChemicalShiftList._pluralLinkName,
        RestraintTable._pluralLinkName,
        PeakList._pluralLinkName,
        IntegralList._pluralLinkName,
        MultipletList._pluralLinkName,
        Sample._pluralLinkName,
        Substance._pluralLinkName,
        NmrChain._pluralLinkName,
        StructureData._pluralLinkName,
        Complex._pluralLinkName,
        SpectrumGroup._pluralLinkName,
        Note._pluralLinkName,
        # _PeakCluster._pluralLinkName,
        'restraintLinks',
        ViolationTable._pluralLinkName,
        DataTable._pluralLinkName,
        Collection._pluralLinkName,
        'additionalData',
        'ccpnDataSetParameters',
        'ccpnLogging',
        ]

    lockedItems = {
        }

    nefToTreeViewMapping = {
        # 'nef_sequence': Chain._pluralLinkName,
        'nef_sequence_chain_code'               : (Chain._pluralLinkName, Chain.className),
        'nef_chemical_shift_list'               : (ChemicalShiftList._pluralLinkName, ChemicalShiftList.className),
        'nef_distance_restraint_list'           : (RestraintTable._pluralLinkName, RestraintTable.className),
        'nef_dihedral_restraint_list'           : (RestraintTable._pluralLinkName, RestraintTable.className),
        'nef_rdc_restraint_list'                : (RestraintTable._pluralLinkName, RestraintTable.className),
        'ccpn_restraint_list'                   : (RestraintTable._pluralLinkName, RestraintTable.className),
        # 'nef_nmr_spectrum': PeakList._pluralLinkName,XXXXX.className),
        'nef_peak'                              : (PeakList._pluralLinkName, PeakList.className),
        'ccpn_integral_list'                    : (IntegralList._pluralLinkName, IntegralList.className),
        'ccpn_multiplet_list'                   : (MultipletList._pluralLinkName, MultipletList.className),
        'ccpn_sample'                           : (Sample._pluralLinkName, Sample.className),
        'ccpn_substance'                        : (Substance._pluralLinkName, Substance.className),
        # 'ccpn_assignment': NmrChain._pluralLinkName,XXXXX.className),
        'nmr_chain'                             : (NmrChain._pluralLinkName, NmrChain.className),
        'ccpn_dataset'                          : (StructureData._pluralLinkName, StructureData.className),
        'ccpn_complex'                          : (Complex._pluralLinkName, Complex.className),
        'ccpn_spectrum_group'                   : (SpectrumGroup._pluralLinkName, SpectrumGroup.className),
        'ccpn_notes'                            : (Note._pluralLinkName, Note.className),
        # 'ccpn_peak_cluster'                     : (_PeakCluster._pluralLinkName, _PeakCluster.className),
        # 'ccpn_peak_cluster_serial'          : (PeakCluster._pluralLinkName, PeakCluster.className),
        'nef_peak_restraint_links'              : ('restraintLinks', 'RestraintLink'),
        'ccpn_distance_restraint_violation_list': (ViolationTable._pluralLinkName, ViolationTable.className),
        'ccpn_dihedral_restraint_violation_list': (ViolationTable._pluralLinkName, ViolationTable.className),
        'ccpn_rdc_restraint_violation_list'     : (ViolationTable._pluralLinkName, ViolationTable.className),
        'ccpn_datatable'                        : (DataTable._pluralLinkName, DataTable.className),
        'ccpn_collections'                      : (Collection._pluralLinkName, Collection.className),
        'ccpn_additional_data'                  : ('additionalData', 'internalData'),
        'ccpn_parameter'                        : ('ccpnDataSetParameters', 'ccpnDataFrame'),
        'ccpn_logging'                          : ('ccpnLogging', 'ccpnHistory'),
        }

    # defines the names of the saveframe loops that are displayed
    nefProjectToSaveFramesMapping = {
        # Chain._pluralLinkName : [],
        Chain._pluralLinkName            : ['nef_sequence'],
        ChemicalShiftList._pluralLinkName: ['nef_chemical_shift_list', 'nef_chemical_shift'],
        RestraintTable._pluralLinkName   : ['nef_distance_restraint_list', 'nef_distance_restraint',
                                            'nef_dihedral_restraint_list', 'nef_dihedral_restraint',
                                            'nef_rdc_restraint_list', 'nef_rdc_restraint',
                                            'ccpn_restraint_list', 'ccpn_restraint'
                                            ],
        PeakList._pluralLinkName         : ['ccpn_peak_list', 'nef_peak', 'nef_spectrum_dimension', 'nef_spectrum_dimension_transfer'],
        IntegralList._pluralLinkName     : ['ccpn_integral_list', 'ccpn_integral'],
        MultipletList._pluralLinkName    : ['ccpn_multiplet_list', 'ccpn_multiplet', 'ccpn_multiplet_peaks'],
        Sample._pluralLinkName           : ['ccpn_sample', 'ccpn_sample_component'],
        Substance._pluralLinkName        : ['ccpn_substance'],
        NmrChain._pluralLinkName         : ['nmr_chain', 'nmr_residue', 'nmr_atom'],
        # TODO:ED - not done yet
        StructureData._pluralLinkName    : ['ccpn_dataset', 'ccpn_calculation_step', 'ccpn_calculation_data'],
        Complex._pluralLinkName          : ['ccpn_complex', 'ccpn_complex_chain'],
        SpectrumGroup._pluralLinkName    : ['ccpn_spectrum_group', 'ccpn_group_spectrum'],
        Note._pluralLinkName             : ['ccpn_note'],
        # _PeakCluster._pluralLinkName  : ['ccpn_peak_cluster_list', 'ccpn_peak_cluster', 'ccpn_peak_cluster_peaks'],
        'restraintLinks'                 : ['nef_peak_restraint_link'],
        'additionalData'                 : ['ccpn_internal_data'],
        ViolationTable._pluralLinkName   : ['ccpn_distance_restraint_violation_list', 'ccpn_distance_restraint_violation',
                                            'ccpn_dihedral_restraint_violation_list', 'ccpn_dihedral_restraint_violation',
                                            'ccpn_rdc_restraint_violation_list', 'ccpn_rdc_restraint_violation',
                                            'ccpn_restraint_violation_list_metadata'
                                            ],
        DataTable._pluralLinkName        : ['ccpn_datatable', 'ccpn_datatable_data', 'ccpn_datatable_metadata'],
        Collection._pluralLinkName       : ['ccpn_collection'],
        'ccpnLogging'                    : ['ccpn_logging', 'ccpn_history'],
        'ccpnDataSetParameters'          : ['ccpn_parameter', 'ccpn_dataframe']
        }

    nefProjectToHandlerMapping = {
        # Chain._pluralLinkName : [],
        Chain._pluralLinkName            : 'nef_sequence',
        ChemicalShiftList._pluralLinkName: None,
        RestraintTable._pluralLinkName   : None,
        PeakList._pluralLinkName         : 'ccpn_peak_list',
        IntegralList._pluralLinkName     : 'ccpn_integral_list',
        MultipletList._pluralLinkName    : 'ccpn_multiplet_list',
        Sample._pluralLinkName           : None,
        Substance._pluralLinkName        : None,
        NmrChain._pluralLinkName         : 'nmr_chain',
        # TODO:ED - not done yet
        StructureData._pluralLinkName    : None,
        Complex._pluralLinkName          : None,
        SpectrumGroup._pluralLinkName    : None,
        Note._pluralLinkName             : 'ccpn_note',
        # _PeakCluster._pluralLinkName  : None,
        'restraintLinks'                 : None,
        'additionalData'                 : 'ccpn_internal_data',
        ViolationTable._pluralLinkName   : None,
        DataTable._pluralLinkName        : None,
        Collection._pluralLinkName       : 'ccpn_collection',
        'ccpnDataSetParameters'          : None,
        'ccpnLogging'                    : None,
        }

    contents = {}

    def _populateTreeView(self, project=None):
        # clear old items - needed for testing without mainWindow
        self.clear()

        if project:
            # set the new project if required
            self.project = project

        if self.includeProject:
            # add the project as the top of the tree - allows to un/select all
            self.projectItem = _StoredTreeWidgetItem(self.invisibleRootItem())

            if self._pathName:
                self.projectItem.setText(0, self._pathName)
            else:
                self.projectItem.setText(0, self.project.name)
            if self._enableCheckBoxes:
                self.projectItem.setFlags(self.projectItem.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
                # self.projectItem.setCheckState(0, QtCore.Qt.Unchecked)
            else:
                self.projectItem.setFlags(self.projectItem.flags() & ~(QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable))
            self.projectItem.setExpanded(True)
            self.headerItem = self.projectItem

        for name in self.checkList:
            if hasattr(self.project, name) or True:  # just to be safe
                item = _StoredTreeWidgetItem(self.headerItem)

                item.setText(0, name)
                if self._enableCheckBoxes:
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
                    # self.headerItem.setCheckState(0, QtCore.Qt.Unchecked)
                else:
                    item.setFlags(item.flags() & ~(QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable))

                # # keep for future reference
                # for obj in getattr(self.project, name):
                #     child = _StoredTreeWidgetItem(item)
                #     child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                #     child.setData(1, 0, obj)
                #     child.setText(0, obj.pid)
                #     child.setCheckState(0, QtCore.Qt.Unchecked)

                item.setExpanded(False)
                if name in self.lockedItems:
                    item.setDisabled(True)
                    if self._enableCheckBoxes:
                        item.setCheckState(0, self.lockedItems[name])
                else:
                    if self._enableCheckBoxes:
                        item.setCheckState(0, QtCore.Qt.Unchecked)

                # # hide the sections if required? not quite working
                # item.setHidden(True)
                # item.setDisabled(True)

    # NOTE:ED - define methods here to match CcpnNefIo
    def content_nef_molecular_system(self, project: Project, saveFrame: StarIo.NmrSaveFrame, saveFrameTag):
        self._contentLoops(project, saveFrame, saveFrameTag,  #name=spectrumName, itemLength=saveFrame['num_dimensions'],
                           )
        tag = 'nef_sequence_chain_code'
        content = self.contents[tag]
        content(self, project, saveFrame, tag)

    def content_nef_sequence(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame) -> OrderedSet:
        pass

    def content_nef_covalent_links(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame) -> OrderedSet:
        pass

    def _contentParent(self, project: Project, saveFrame: StarIo.NmrSaveFrame, saveFrameTag):
        try:
            category = saveFrameTag  #saveFrame['sf_category']
        except Exception as es:
            pass

        if hasattr(saveFrame, '_content') and category in saveFrame._content:
            thisList = saveFrame._content[category]
            treeItem, _ = self.nefToTreeViewMapping[category]
            found = self.findItems(treeItem, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
            if found:
                if len(found) == 1:
                    return found[0]

    def content_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame, saveFrameTag):
        try:
            category = saveFrameTag  #saveFrame['sf_category']
        except Exception as es:
            pass

        if hasattr(saveFrame, '_content') and category in saveFrame._content:
            thisList = saveFrame._content[category]
            treeItem, _ = self.nefToTreeViewMapping[category]
            found = self.findItems(treeItem, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
            if found and len(found) == 1:
                # add to the tree

                if self._enableCheckBoxes:
                    found[0].setCheckState(0, QtCore.Qt.Unchecked)

                # NOTE:ED - this defines the list of items that are added to each plural group in the tree
                #           i.e. Chains = saveFrame._content['chain_code'] from nefToTreeViewMapping
                if thisList:
                    for listItem in thisList:
                        child = _StoredTreeWidgetItem(found[0])
                        if self._enableCheckBoxes:
                            child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                        else:
                            child.setFlags(child.flags() & ~QtCore.Qt.ItemIsUserCheckable)
                        # child.setData(1, 0, saveFrame)

                        parentGroup = child.parent().data(0, 0) if child.parent() else repr(None)
                        pHandler = self.nefProjectToHandlerMapping.get(parentGroup) or saveFrame.get('sf_category')
                        ccpnClassName = nef2CcpnClassNames.get(pHandler)

                        # use '.' to match nef specification
                        lbl = '.' if listItem is None else str(listItem)
                        child.setData(1, 0, (lbl, saveFrame, parentGroup, pHandler, ccpnClassName))
                        child.setText(0, lbl)

                        if self._enableCheckBoxes:
                            child.setCheckState(0, QtCore.Qt.Unchecked)
                # else:
                # found[0].setHidden(False)
                # found[0].setDisabled(False)

    def _contentLoops(self, project: Project, saveFrame: StarIo.NmrSaveFrame, saveFrameTag=None,
                      addLoopAttribs=None, excludeList=(), **kwds):
        """Iterate over the loops in a saveFrame, and add to results"""
        result = {}
        mapping = nef2CcpnMap.get(saveFrame.category) or {}
        for tag, ccpnTag in mapping.items():
            if tag not in excludeList and ccpnTag == _isALoop:
                loop = saveFrame.get(tag)
                if loop and tag in self.contents:
                    content = self.contents[tag]
                    if addLoopAttribs:
                        dd = []
                        for name in addLoopAttribs:
                            dd.append(saveFrame.get(name))
                        content(self, project, saveFrame, tag, *dd, **kwds)
                    else:
                        content(self, project, saveFrame, tag, **kwds)

    def content_nef_chemical_shift(self, parent: ChemicalShiftList, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame) -> OrderedSet:
        # ll = parentFrame._content[parentFrame['sf_category']]
        pass

    def content_nef_restraint_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        pass

    def content_nef_restraint(self, restraintTable: RestraintTable, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                              itemLength: int = None) -> Optional[OrderedSet]:
        pass

    def content_nef_nmr_spectrum(self, project: Project, saveFrame: StarIo.NmrSaveFrame, saveFrameTag):
        self._contentLoops(project, saveFrame, saveFrameTag,  #name=spectrumName, itemLength=saveFrame['num_dimensions'],
                           )

    def content_ccpn_integral_list(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                   name=None, itemLength=None):
        pass

    def content_ccpn_multiplet_list(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                                    name=None, itemLength=None):
        pass

    def content_ccpn_integral(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                              name=None, itemLength=None):
        pass

    def content_ccpn_multiplet(self, project: Project, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                               name=None, itemLength=None):
        pass

    # def content_ccpn_peak_cluster_list(self, project: Project, saveFrame: StarIo.NmrSaveFrame, saveFrameTag):
    #     self._contentLoops(project, saveFrame, saveFrameTag,  #name=spectrumName, itemLength=saveFrame['num_dimensions'],
    #                        )

    def content_nef_peak(self, peakList: PeakList, loop: StarIo.NmrLoop, parentFrame: StarIo.NmrSaveFrame,
                         name=None, itemLength: int = None):
        pass

    def content_ccpn_spectrum_group(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        pass

    def content_ccpn_complex(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        pass

    def content_ccpn_sample(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        pass

    def content_ccpn_substance(self, project: Project, saveFrame: StarIo.NmrSaveFrame):
        pass

    def content_ccpn_assignment(self, project: Project, saveFrame: StarIo.NmrSaveFrame, saveFrameTag):
        self._contentLoops(project, saveFrame, saveFrameTag,  #name=spectrumName, itemLength=saveFrame['num_dimensions'],
                           )

    def content_ccpn_default(self, project: Project, saveFrame: StarIo.NmrSaveFrame, saveFrameTag):
        self._contentLoops(project, saveFrame, saveFrameTag,  #name=spectrumName, itemLength=saveFrame['num_dimensions'],
                           )

    contents['nef_molecular_system'] = content_nef_molecular_system
    # contents['nef_sequence'] = content_nef_sequence
    # NOTE:ED - to match nefmapping
    contents['nef_sequence_chain_code'] = content_list  # content_nef_sequence
    # contents['nef_covalent_links'] = content_nef_covalent_links
    contents['nef_chemical_shift_list'] = content_list  # content_nef_chemical_shift_list
    # contents['nef_chemical_shift'] = content_nef_chemical_shift

    contents['nef_distance_restraint_list'] = content_list  # content_nef_restraint_list  # could be _contentLoops
    contents['nef_dihedral_restraint_list'] = content_list  # content_nef_restraint_list
    contents['nef_rdc_restraint_list'] = content_list  # content_nef_restraint_list
    contents['ccpn_restraint_list'] = content_list  # content_nef_restraint_list

    # contents['nef_distance_restraint'] = partial(content_nef_restraint, itemLength=coreConstants.constraintListType2ItemLength.get('Distance'))
    # contents['nef_dihedral_restraint'] = partial(content_nef_restraint, itemLength=coreConstants.constraintListType2ItemLength.get('Dihedral'))
    # contents['nef_rdc_restraint'] = partial(content_nef_restraint, itemLength=coreConstants.constraintListType2ItemLength.get('Rdc'))
    # contents['ccpn_restraint'] = partial(content_nef_restraint, itemLength=coreConstants.constraintListType2ItemLength.get('Distance'))

    contents['nef_nmr_spectrum'] = content_ccpn_default  # content_nef_nmr_spectrum
    contents['nef_peak'] = content_list

    contents['ccpn_integral_list'] = content_list  # content_ccpn_integral_list
    contents['ccpn_multiplet_list'] = content_list  # content_ccpn_multiplet_list
    # contents['ccpn_integral'] = content_ccpn_integral
    # contents['ccpn_multiplet'] = content_ccpn_multiplet
    # contents['ccpn_peak_cluster_list'] = content_ccpn_peak_cluster_list
    # contents['ccpn_peak_cluster'] = content_list
    # NOTE:ED - to match nefmapping
    # contents['ccpn_peak_cluster_serial'] = content_list

    contents['ccpn_spectrum_group'] = content_list  # content_ccpn_spectrum_group
    contents['ccpn_complex'] = content_list  # content_ccpn_complex
    contents['ccpn_sample'] = content_list  # content_ccpn_sample
    contents['ccpn_substance'] = content_list  # content_ccpn_substance

    contents['ccpn_assignment'] = content_ccpn_default
    contents['nmr_chain'] = content_list

    contents['ccpn_notes'] = content_list  # content_ccpn_notes
    contents['ccpn_collections'] = content_list  # content_ccpn_collections

    contents['nef_peak_restraint_links'] = content_list

    contents['ccpn_additional_data'] = content_list

    contents['ccpn_distance_restraint_violation_list'] = content_list  # content_nef_restraint_list
    contents['ccpn_dihedral_restraint_violation_list'] = content_list  # content_nef_restraint_list
    contents['ccpn_rdc_restraint_violation_list'] = content_list  # content_nef_restraint_list

    contents['ccpn_datatable'] = content_list

    contents['ccpn_logging'] = content_list
    contents['ccpn_dataset'] = content_list
    contents['ccpn_parameter'] = content_list

    def _fillFunc(self, project, saveFrame, *args, **kwds):
        saveFrameName = saveFrame['sf_category']
        if saveFrameName in self.contents:
            content = self.contents[saveFrameName]
            content(self, project, saveFrame, saveFrame['sf_category'])

    def fillTreeView(self, nefDict):
        _traverse(self, self.project, nefDict, traverseFunc=self._fillFunc)

    def findSection(self, value, _parent=None):
        """Find the required section in the tree
        """
        found = self.findItems(value, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
        if _parent:
            found = [item for item in found
                     if (isinstance(_parent, str) and item.parent() and item.parent().data(0, 0) == _parent) or
                     (isinstance(_parent, QtWidgets.QTreeWidgetItem) and item.parent() == _parent)]
        if found:
            if len(found) == 1:
                return found[0]
            return found

    def getFirstChild(self):
        pass

    def raiseContextMenu(self, event: QtGui.QMouseEvent):
        """Creates and raises a context menu enabling items to be deleted from the sidebar.
        """
        menu = self._getContextMenu(event)
        if self._postMenuSetup:
            self._postMenuSetup(menu)  # add options from the parent

        if menu:
            menu.move(event.globalPos().x(), event.globalPos().y() + 10)
            menu.exec()

    def _getContextMenu(self, event):
        """Build a menu for renaming tree items
        """
        contextMenu = Menu('', self, isFloatWidget=True)

        selection = self.selectionModel().selectedIndexes()
        newItms = [self.itemFromIndex(itm) for itm in selection]
        items = [itm.data(1, 0) for itm in newItms if itm.data(1, 0)]

        _itemPressed = self.itemAt(event.pos())
        if len(items) > 1:
            contextMenu.addItem("Autorename All Conflicts in Selection", callback=self._autoRenameAllConflicts, enabled=True)
            contextMenu.addSeparator()
            contextMenu.addItem("Autorename All in Selection", callback=self._autoRenameAll)
            contextMenu.addItem("Autorename Checked in Selection", callback=self._autoRenameSelected)
            contextMenu.addSeparator()
        elif len(items) == 1:
            contextMenu.addItem("Autorename", callback=self._autoRenameSingle, enabled=True)
            contextMenu.addSeparator()

        if len(items) > 1:
            contextMenu.addItem("Check All Conflicts in Selection", callback=partial(self._checkSelected, True, conflictsOnly=True), enabled=True)
            contextMenu.addItem("Uncheck All Conflicts in Selection", callback=partial(self._checkSelected, False, conflictsOnly=True), enabled=True)
            contextMenu.addSeparator()
            contextMenu.addItem("Check Selected", callback=partial(self._checkSelected, True))
            contextMenu.addItem("Uncheck Selected", callback=partial(self._checkSelected, False))

        return contextMenu

    def _getSelectedItems(self, checked=None):
        """Get the selectedItems
        """
        selection = self.selectionModel().selectedIndexes()
        newItms = [self.itemFromIndex(itm) for itm in selection]
        if checked is None:
            items = [itm.data(1, 0) for itm in newItms if itm.data(1, 0)]
        else:
            items = [itm.data(1, 0) for itm in newItms if itm.data(1, 0) and
                     itm.checkState(0) == (QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)]

        return items

    def _autoRename(self, groupItems, conflictsOnly=False):
        """Call the rename action on the child nodes
        """
        if RENAMEACTION in self._actionCallbacks:
            for childItem in groupItems:
                name, saveFrame, treeParent, _, _ = childItem
                conflictCheck = True
                if conflictsOnly and BADITEMACTION in self._actionCallbacks:
                    conflictCheck = self._actionCallbacks[BADITEMACTION](name, saveFrame, treeParent)

                if conflictCheck:
                    self._actionCallbacks[RENAMEACTION](name, saveFrame, treeParent)

    def _autoRenameSingle(self):
        """Tree item autorename all conflicts in subtree
        """
        children = self._getSelectedItems()
        self._autoRename(children)

    def _autoRenameAllConflicts(self):
        """Tree item autorename all conflicts in subtree
        """
        children = self._getSelectedItems()
        self._autoRename(children, conflictsOnly=True)

    def _autoRenameAll(self):
        """Tree item autorename all in subtree
        """
        children = self._getSelectedItems()
        self._autoRename(children)

    def _autoRenameSelected(self):
        """Tree item autorename selected in subtree
        """
        children = self._getSelectedItems(checked=True)
        self._autoRename(children)

    def _checkSelected(self, checked, conflictsOnly=False):
        """Tree item check/uncheck selected
        """
        children = self._getSelectedItems()

        # for item in self.selectedItems():
        for _data in children:
            conflictCheck = True
            itemName, saveFrame, parentGroup, _, _ = _data
            if conflictsOnly and BADITEMACTION in self._actionCallbacks:
                conflictCheck = self._actionCallbacks[BADITEMACTION](itemName, saveFrame, parentGroup)

            if conflictCheck:
                if (item := self.findSection(itemName, parentGroup)):
                    item.setCheckState(0, QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)

    def _selectChildren(self, item, state=True):
        # select the children
        _children = [item.child(ii) for ii in range(item.childCount())]
        for child in _children:
            self._selectChildren(child, state)
            child.setSelected(state)

    def _clicked(self, item, *args):
        super(ImportTreeCheckBoxes, self)._clicked(item, *args)

        # select all the children of the clicked item
        self._selectChildren(item, True)


class PrintTreeCheckBoxes(ProjectTreeCheckBoxes):
    """Class to handle exporting peaks/integrals/multiplets to PDF or SVG files
    """

    # set the items in the project that can be printed
    checkList = []
    # SPECTRA,
    # PeakList._pluralLinkName,
    # IntegralList._pluralLinkName,
    # MultipletList._pluralLinkName,
    # ]

    # all items can be selected
    selectableItems = []

    # SPECTRA,
    # PeakList._pluralLinkName,
    # IntegralList._pluralLinkName,
    # MultipletList._pluralLinkName,
    # ]

    lockedItems = {}

    def __init__(self, parent=None, project=None, maxSize=(250, 300), **kwds):
        super(PrintTreeCheckBoxes, self).__init__(parent=parent, project=project, maxSize=maxSize, **kwds)
