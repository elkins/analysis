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
__dateModified__ = "$dateModified: 2024-10-02 16:39:51 +0100 (Wed, October 02, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2021-04-26 11:53:10 +0100 (Mon, April 26, 2021) $"

#=========================================================================================
# Start of code
#=========================================================================================

from functools import reduce, partial
from PyQt5 import QtWidgets, QtGui, QtCore
from collections import OrderedDict
from operator import add
import re

from ccpn.core.PeakList import PeakList
from ccpn.core.RestraintTable import RestraintTable
from ccpn.core.ViolationTable import ViolationTable
from ccpn.core.StructureData import StructureData
from ccpn.core.StructureEnsemble import StructureEnsemble
from ccpn.core.Collection import Collection
from ccpn.core.lib.Notifiers import Notifier
from ccpn.ui.gui.modules.CcpnModule import CcpnTableModule
from ccpn.ui.gui.modules.lib.RestraintAITableCommon import (_ModuleHandler,
                                                            _COLLECTION, _COLLECTIONBUTTON, _SPECTRUMDISPLAYS,
                                                            _RESTRAINTTABLE, _RESTRAINTTABLES,
                                                            _VIOLATIONTABLES, _VIOLATIONRESULT, _DEFAULTMEANTHRESHOLD,
                                                            ALL, _CLEARBUTTON, _COMPARISONSETS, SearchModes)
from ccpn.ui.gui.modules.lib.RestraintAITable import RestraintFrame
from ccpn.ui.gui.widgets.PulldownListsForObjects import CollectionPulldown, SELECT
from ccpn.ui.gui.widgets.CompoundWidgets import (DoubleSpinBoxCompoundWidget, ButtonCompoundWidget,
                                                 RadioButtonsCompoundWidget)
# from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.SettingsWidgets import (ModuleSettingsWidget,
                                                 RestraintTableSelectionWidget, SpectrumDisplaySelectionWidget,
                                                 ViolationTableSelectionWidget, SelectToAdd)
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.HLine import HLine
from ccpn.ui.gui.widgets.Frame import ScrollableFrame
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.Label import Label
# from ccpn.ui.gui.widgets.Splitter import Splitter
from ccpn.ui.gui.lib.alignWidgets import alignWidgets
from ccpn.util.Logging import getLogger
from ccpn.util.Path import fetchDir
from ccpn.util import Common
from ccpn.util.OrderedSet import OrderedSet
from ccpn.framework.Application import getProject

from ccpn.ui.gui.widgets.ProjectTreeCheckBoxes import ProjectTreeCheckBoxes, _StoredTreeWidgetItem


logger = getLogger()

LINKTOPULLDOWNCLASS = 'linkToPulldownClass'
DEFAULT_COLOR = QtGui.QColor('black')
CHECKABLE = QtCore.Qt.ItemIsUserCheckable
CHECKED = QtCore.Qt.Checked
UNCHECKED = QtCore.Qt.Unchecked

_HINT = """New comparison-set
Drop items into each box:
    single collection, containing at least one restraintTable, or
    single structureData, or
    many restraintTables.
Drop items into gearbox area;
    these can be a combination of:
        structureData,
        collections,
        restraintTables.
Items not compatible with a single comparison-set
will be separated into comparison-sets
"""


#=========================================================================================
# _ComparisonTree
#=========================================================================================

class _ComparisonTree(ProjectTreeCheckBoxes):
    """Class to handle core restraint/violation-tables associated with a comparison-set.
    i.e. restraint-tables that are connected to the same run, and are placed in the same
    column of the restraint module.
    """

    def __init__(self, parent, *, resources=None, **kwds):
        project = getProject()

        super().__init__(parent, project=project, **kwds)

        self.resources = resources
        self._parent = parent
        self.isEmpty = True
        self.comparisonItem = None

        # allow drops of items
        self.setAcceptDrops(True)
        self.setDropEventCallback(self._processDroppedItems)
        self.setSizeAdjustPolicy(self.AdjustToContents)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding)
        if self not in self.resources.comparisonSets:
            self.resources.comparisonSets.append(self)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.setSelectionMode(self.NoSelection)
        self.setToolTip(_HINT)

        self.checkStateChanged.connect(self._checked)

    def _populateTreeView(self, project=None):
        ...

    def _checked(self, item, column):
        """Respond to a checkbox state has changed
        """
        if item.isDisabled():
            return

        if item.depth == 1:
            # restraint-table level
            disabled = not bool(item.checkState(0))

            with self.blockWidgetSignals(self):
                if disabled:
                    # remember the disabled-state of the children, some may be non-output violation-tables
                    item._lastState = {}
                    for cc in range(item.childCount()):
                        child = item.child(cc)
                        item._lastState[id(child)] = child.isDisabled()
                        child.setDisabled(True)
                else:
                    for cc in range(item.childCount()):
                        child = item.child(cc)
                        child.setDisabled(item._lastState[id(child)])

        elif (parent := item.parent()) and item.depth == 2:
            with self.blockWidgetSignals(self):
                # uncheck the other items
                for cc in range(parent.childCount()):
                    child = parent.child(cc)
                    if child is not item:
                        child.setCheckState(0, UNCHECKED)

        self.resources.guiFrame.setRefreshButtonEnabled(True)
        self.update()

    #=========================================================================================
    # Handle dropped items
    #=========================================================================================

    def _processDroppedItems(self, data):
        """CallBack for Drop-events
        """
        if not data:
            return

        # rss = self.resources
        pids = data.get('pids', [])

        objs = [self.project.getByPid(pid) for pid in pids]
        sData = [obj for obj in objs if isinstance(obj, StructureData)]
        collections = [obj for obj in objs if isinstance(obj, Collection)]
        rTables = [obj for obj in objs if isinstance(obj, RestraintTable)]

        if len(sData) == 1:
            if len(objs) > 1:
                # MessageDialog.showWarning('Restraint Analysis Inspector', 'Please only drop one structureData')
                return True
            self._processStructureData(sData[0])
            return
        if len(rTables):
            if len(objs) != len(rTables):
                # MessageDialog.showWarning('Restraint Analysis Inspector', 'Please only drop restraintTables')
                return True
            self._processRestraintTables(rTables)
            return
        if len(collections) == 1:
            if len(objs) > 1:
                # MessageDialog.showWarning('Restraint Analysis Inspector', 'Please only drop one collection')
                return True
            # - this needs addressing in more detail
            return self._processCollection(collections[0])

        # return processing to the parent, signal to continue up dropEvent widget-tree
        return True

    def _addRestraintsToComparisonSet(self, rTables):

        top = self.comparisonItem
        self.isEmpty = False

        # add the restraint-tables
        for rTable in rTables:

            sData = rTable.structureData
            item = _StoredTreeWidgetItem(top, depth=1)
            item.setText(0, rTable.id)
            item.setData(1, 0, rTable)

            if self._enableCheckBoxes:
                item.setFlags(item.flags() | CHECKABLE)
                item.setCheckState(0, CHECKED)
            else:
                item.setFlags(item.flags() & ~CHECKABLE)

            validVTables = []
            for vTable in sData.violationTables:
                # add the violation-tables
                #   - search for the violationTables that are associated with the restraint-tables

                child = _StoredTreeWidgetItem(item, depth=2)
                if self._enableCheckBoxes:
                    child.setFlags(child.flags() | CHECKABLE)
                    child.setCheckState(0, UNCHECKED)
                else:
                    child.setFlags(child.flags() & ~CHECKABLE)
                child.setText(0, vTable.id)
                child.setData(1, 0, vTable)

                if validOutput := rTable.pid == vTable.getMetadata(_RESTRAINTTABLE) and vTable.getMetadata(
                        _VIOLATIONRESULT) is True:
                    validVTables.append(child)
                child.setDisabled(not validOutput)

            if validVTables:
                validVTables[0].setCheckState(0, CHECKED)

        self.expandAll()
        self.setItemsExpandable(False)

        self.resources.guiFrame.setRefreshButtonEnabled(True)
        self.resources.guiModule.addNewComparisonSet()
        QtCore.QTimer.singleShot(0, self.resources.guiFrame._updatePulldown)

    def _releaseColumn(self):
        self.setMinimumWidth(100)
        self.setMaximumWidth(max(self.sizeHintForColumn(col) + 24 for col in range(self.columnCount())))

    def getTreeTables(self, includeRoot=False, depth=0, selected=None):
        """Get objects from the tree at the specified depth.
        depth 0: structureData/collection/first restraint-table
        depth 1: restraint-tables
        depth 2: violation-tables
        """
        allObjects = []

        for item in self.findItems('', QtCore.Qt.MatchContains | QtCore.Qt.MatchRecursive):
            if selected is None or bool(item.checkState(0)) == selected:
                obj = item.data(1, 0)
                # return items in the tree that have a pid
                if hasattr(obj, 'pid') and item.depth == depth and \
                        (not self.projectItem or item != self.projectItem or includeRoot):
                    allObjects += [obj]

        return allObjects

    @property
    def comparisonSet(self):
        """Return the core object used to create the comparison-set
        """
        if not self.isEmpty and (obj := self.comparisonItem.data(1, 0)):
            return obj

    @property
    def comparisonSetName(self):
        """Return the name of the item used to create the comparison-set
        """
        if not self.isEmpty and self.comparisonItem.data(1, 0):
            return self.comparisonItem.text(0)

    def _processStructureData(self, structureData):
        """Drop a structureData in the comparison-set
        """
        name = structureData.id
        existing = [cs.comparisonSetName for cs in self.resources.comparisonSets]
        while name in existing:
            name = Common.incrementName(name)
        self.clear()

        # set the name from the structureData
        top = self.comparisonItem = _StoredTreeWidgetItem(self.invisibleRootItem(), depth=0)
        top.setText(0, name)
        top.setData(1, 0, structureData)
        top.setFlags(top.flags() & ~CHECKABLE)

        rTables = structureData.restraintTables

        self._addRestraintsToComparisonSet(rTables)

    def _processCollection(self, collection):
        """Drop a collection in the comparison-set
        """
        name = collection.id
        existing = [cs.comparisonSetName for cs in self.resources.comparisonSets]
        while name in existing:
            name = Common.incrementName(name)
        self.clear()

        # set the name from the structureData
        top = self.comparisonItem = _StoredTreeWidgetItem(self.invisibleRootItem(), depth=0)
        top.setText(0, name)
        top.setData(1, 0, collection)
        top.setFlags(top.flags() & ~CHECKABLE)

        rTables = [obj for obj in collection.items if isinstance(obj, RestraintTable)]
        if not rTables:
            # if no restraint-tables then let the parent decide
            return True

        self._addRestraintsToComparisonSet(rTables)

    def _processRestraintTables(self, restraintTables):
        if not restraintTables:
            return

        firstTable = restraintTables[0]
        name = firstTable.id
        existing = [cs.comparisonSetName for cs in self.resources.comparisonSets]
        while name in existing:
            name = Common.incrementName(name)

        if self.isEmpty:
            # set the name from the first restraint-table
            top = self.comparisonItem = _StoredTreeWidgetItem(self.invisibleRootItem(), depth=0)
            top.setText(0, name)
            top.setData(1, 0, firstTable)
            top.setFlags(top.flags() & ~CHECKABLE)

        # check against the restraint-tables already in the treeView
        thisRTables = [obj for obj in self.getTreeTables(depth=1) if isinstance(obj, RestraintTable)]
        rTables = [obj for obj in restraintTables if obj not in thisRTables]

        self._addRestraintsToComparisonSet(rTables)

    #=========================================================================================
    # Menu
    #=========================================================================================

    def raiseContextMenu(self, event: QtGui.QMouseEvent):
        """Creates and raises a context menu enabling items to be deleted from the sidebar.
        """
        if menu := self._getContextMenu():
            menu.move(event.globalPos().x(), event.globalPos().y() + 10)
            menu.exec_()

    def _getContextMenu(self) -> Menu:
        """Build a menu for renaming tree items
        """
        contextMenu = Menu('', self, isFloatWidget=True)
        contextMenu.addItem('Remove Comparison Set', callback=self._removeComparisonSet, enabled=True)
        # contextMenu.addItem('Duplicate Comparison Set', callback=self._duplicateComparisonSet, enabled=False)
        contextMenu.addSeparator()

        return contextMenu

    def _removeComparisonSet(self):
        """Remove the selected comparison-set from the list
        """
        rss = self.resources
        rss.comparisonSets.remove(self)
        rss.guiFrame.setRefreshButtonEnabled(True)
        self.setVisible(False)
        self.deleteLater()
        rss.guiModule.addNewComparisonSet()

    def _duplicateComparisonSet(self):
        """Duplicate the selected comparison-set to the end of the list
        """
        ...

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        super(_ComparisonTree, self).paintEvent(e)

        if self.isEmpty:
            # add information for dropping items
            p = QtGui.QPainter(self.viewport())
            pen = QtGui.QPen(QtGui.QColor('grey'))
            p.setPen(pen)
            rgn = self.rect().adjusted(8, 8, 0, 0)
            rgn = QtCore.QRect(rgn.left(), rgn.top(), rgn.width(), rgn.height())
            align = QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft
            self.hint = p.drawText(rgn, int(align), _HINT)
            p.end()

    def minimumSizeHint(self):
        size = super().minimumSizeHint()

        # Get the frame width using the current style of the widget
        frame_width = self.style().pixelMetric(QtWidgets.QStyle.PM_DefaultFrameWidth)
        # Initialize the total height with the height of the header and double the frame width
        height = self.header().height() + (2 * frame_width)

        # Iterate over all items in the QTreeWidget
        iterator = QtWidgets.QTreeWidgetItemIterator(self)
        while iterator.value():
            # Add the visual height of each item to the total height
            item = iterator.value()
            height += self.visualItemRect(item).height()
            # Move to the next item
            iterator += 1

        # Set the fixed height of the tree widget
        return QtCore.QSize(size.width(), max(height, 32))

    def _updateNotify(self, trigger, obj):
        """Refill the comparison-set on notifier
        """
        QtCore.QTimer.singleShot(0, partial(self._cleanup, trigger, obj))

    def _cleanup(self, trigger, obj):
        """Clean-up if set doesn't contain any items
        """
        toDelete = []
        for child in self.findItems('*', QtCore.Qt.MatchWrap | QtCore.Qt.MatchWildcard | QtCore.Qt.MatchRecursive):
            if coreObj := child.data(1, 0):
                if coreObj.isDeleted or (trigger == Notifier.DELETE and coreObj == obj):
                    child.setDisabled(True)
                    toDelete.append(child)
                else:
                    # rename event - need to keep the extension
                    if ext := re.search(r'_\d+$', child.text(0)):
                        child.setText(0, coreObj.id + ext.group())
                    else:
                        child.setText(0, coreObj.id)

        for itm in toDelete:
            try:
                if itm.parent():
                    itm.parent().removeChild(itm)
                else:
                    self.invisibleRootItem().removeChild(itm)
            except Exception as es:
                print(es)

        if not self.findItems('*', QtCore.Qt.MatchWrap | QtCore.Qt.MatchWildcard | QtCore.Qt.MatchRecursive):
            self.isEmpty = True

        self.resources.guiFrame.setRefreshButtonEnabled(True)
        self.repaint()


#=========================================================================================
# RestraintAnalysisTableModule
#=========================================================================================

_MEANLOWERLIMIT = 'meanLowerLimit'
_AUTOEXPAND = 'autoExpand'
_MARKPOSITIONS = 'markPositions'
_AUTOCLEARMARKS = 'autoClearMarks'
_SEQUENTIALSTRIPS = 'sequentialStrips'
_SEARCHMODE = 'searchMode'
_INCLUDENONPEAKS = 'includeNonPeaks'


class RestraintAnalysisTableModule(CcpnTableModule):
    """
    This class implements the module by wrapping a RestraintAnalysisTable instance
    """
    className = 'RestraintAnalysisTableModule'
    includeSettingsWidget = True
    maxSettingsState = 2
    settingsPosition = 'left'
    settingsMinimumSizes = (500, 200)

    includeDisplaySettings = True
    includePeakLists = False
    includeNmrChains = False
    includeSpectrumTable = False
    _allowRename = True

    activePulldownClass = None  # e.g., can make the table respond to current peakList

    def __init__(self, mainWindow=None, name='Restraint Analysis Inspector',
                 peakList=None, selectFirstItem=False):
        super().__init__(mainWindow=mainWindow, name=name)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            app = self.application = mainWindow.application
            self.project = app.project
            self.current = app.current
            self.scriptsPath = app.scriptsPath
            self.pymolScriptsPath = fetchDir(self.scriptsPath, 'pymol')
        else:
            self.application = self.project = self.current = None

        # a data-store for information that all widgets in module may access
        self.resources = _ModuleHandler()
        self.resources.guiModule = self

        # set the widgets and callbacks
        self._setWidgets(self.settingsWidget, self.mainWidget, peakList, selectFirstItem)
        self._setCallbacks()

    def _setWidgets(self, settingsWidget, mainWidget, peakList, selectFirstItem):
        """Set up the widgets for the module
        """
        self._settings = None

        # add the settings widgets defined from the following orderedDict - test for refactored
        settingsDict = OrderedDict(((_SPECTRUMDISPLAYS, {'label'   : '',
                                                         'tipText' : '',
                                                         'callBack': None,  # self.restraintTablePulldown,
                                                         'enabled' : True,
                                                         '_init'   : None,
                                                         'type'    : SpectrumDisplaySelectionWidget,
                                                         'kwds'    : {'texts'        : [],
                                                                      'displayText'  : [],
                                                                      'defaults'     : [],
                                                                      'objectName'   : 'SpectrumDisplaysSelection',
                                                                      'minimumWidths': (180, 100, 100)},
                                                         }),
                                    ('_divider', {'label': '',
                                                  'type' : HLine,
                                                  'kwds' : {'gridSpan'  : (1, 2),
                                                            'height'    : 15,
                                                            'objectName': '_divider'},
                                                  }),

                                    (_COLLECTION, {'label'   : '',
                                                   'tipText' : '',
                                                   'callBack': self._collectionPulldownCallback,
                                                   'enabled' : False,
                                                   'visible' : False,
                                                   '_init'   : None,
                                                   'type'    : CollectionPulldown,
                                                   'kwds'    : {'showSelectName': True,
                                                                'objectName'    : 'CollectionSelect',
                                                                'minimumWidths' : (180, 100, 100)},
                                                   }),
                                    (_COLLECTIONBUTTON, {'label'   : '',
                                                         'tipText' : 'Refresh the module from the first peakList in the collection',
                                                         'callBack': self._collectionPulldownReset,
                                                         'enabled' : False,
                                                         'visible' : False,
                                                         '_init'   : None,
                                                         'type'    : ButtonCompoundWidget,
                                                         'kwds'    : {'text'           : ' Refresh ',
                                                                      'buttonAlignment': 'right',
                                                                      'objectName'     : 'CollectionSelect',
                                                                      'icon'           : Icon('icons/redo'),
                                                                      'enabled'        : False,
                                                                      'minimumWidths'  : (180, 100, 100)},
                                                         }),
                                    (_RESTRAINTTABLES, {'label'   : '',
                                                        'tipText' : '',
                                                        'callBack': None,  # self.restraintTablePulldown,
                                                        'enabled' : True,
                                                        'visible' : False,
                                                        '_init'   : None,
                                                        'type'    : RestraintTableSelectionWidget,
                                                        'kwds'    : {'texts'        : [],
                                                                     'displayText'  : [],
                                                                     'defaults'     : [],
                                                                     'objectName'   : 'RestraintTablesSelection',
                                                                     'minimumWidths': (180, 100, 100)},
                                                        }),
                                    (_VIOLATIONTABLES, {'label'   : '',
                                                        'tipText' : '',
                                                        'callBack': None,
                                                        'enabled' : True,
                                                        'visible' : False,
                                                        '_init'   : None,
                                                        'type'    : ViolationTableSelectionWidget,
                                                        'kwds'    : {'texts'        : [],
                                                                     'displayText'  : [],
                                                                     'defaults'     : [],
                                                                     'objectName'   : 'RestraintTablesSelection',
                                                                     'minimumWidths': (180, 100, 100)},
                                                        }),
                                    ('_label1', {'label': '',
                                                 'type' : Label,
                                                 'kwds' : {'text'      : 'Comparison Sets',
                                                           'gridSpan'  : (1, 2),
                                                           'height'    : 15,
                                                           'objectName': '_label1'},
                                                 }),
                                    (_COMPARISONSETS, {'label'          : 'Comparison Sets',
                                                       'enabled'        : True,
                                                       'type'           : ScrollableFrame,
                                                       'useInsideSpacer': True,
                                                       'kwds'           : {'gridSpan' : (1, 2),
                                                                           'setLayout': True},
                                                       }),
                                    (_CLEARBUTTON, {'label'   : '',
                                                    'tipText' : 'Clear the comparison sets',
                                                    'callBack': self._clearComparisons,
                                                    'enabled' : True,
                                                    '_init'   : None,
                                                    'type'    : ButtonCompoundWidget,
                                                    'kwds'    : {'text'           : ' Clear ',
                                                                 'buttonAlignment': 'right',
                                                                 'objectName'     : 'CollectionSelect',
                                                                 'enabled'        : True,
                                                                 'minimumWidths'  : (180, 100, 100)},
                                                    }),
                                    (_MEANLOWERLIMIT, {'label'   : 'Mean Value Lower Limit',
                                                       'callBack': self._updateMeanLowerLimit,
                                                       'enabled' : True,
                                                       '_init'   : None,
                                                       'type'    : DoubleSpinBoxCompoundWidget,
                                                       'kwds'    : {'labelText'    : 'Mean Value Lower Limit',
                                                                    'tipText'      : 'Lower threshold for mean value of restraints',
                                                                    'minimum'      : 0.0,
                                                                    'maximum'      : 1.0,
                                                                    'decimals'     : 2,
                                                                    'step'         : 0.05,
                                                                    'value'        : _DEFAULTMEANTHRESHOLD,
                                                                    'minimumWidths': (180, 100, 100)},
                                                       }),
                                    (_SEARCHMODE, {'label'   : '',
                                                   'tipText' : '',
                                                   'enabled' : True,
                                                   '_init'   : None,
                                                   'type'    : RadioButtonsCompoundWidget,
                                                   'callBack': self._searchModeCallback,
                                                   'kwds'    : {
                                                       'labelText'    : 'Peak Group Behaviour',
                                                       'objectName'   : 'SearchMode',
                                                       'minimumWidths': (180, 100, 100),
                                                       'compoundKwds' : {
                                                           'texts'      : SearchModes.descriptions(),
                                                           'tipTexts'   : SearchModes.dataValues(),
                                                           'direction'  : 'v',
                                                           'selectedInd': 0,
                                                           }
                                                       }
                                                   }),
                                    (_INCLUDENONPEAKS, {'label'        : 'Include Restraints\nwithout Peaks',
                                                        'tipText'      : 'Include restraints that do not have any peaks.',
                                                        'callBack'     : self._updateIncludeNonPeaksCallback,
                                                        'enabled'      : True,
                                                        'checked'      : True,
                                                        'minimumWidths': (180, 30),
                                                        '_init'        : None,
                                                        }),
                                    (_AUTOEXPAND, {'label'   : 'Auto-expand Groups',
                                                   'tipText' : 'Automatically expand/collapse groups on\nadding new restraintTable, or sorting.',
                                                   'callBack': self._updateAutoExpand,
                                                   'enabled' : True,
                                                   'checked' : True,
                                                   '_init'   : None,
                                                   }),
                                    (_SEQUENTIALSTRIPS, {'label'   : 'Show sequential strips',
                                                         'tipText' : 'Show nmrResidue in all strips.',
                                                         'callBack': None,
                                                         'enabled' : True,
                                                         'checked' : False,
                                                         '_init'   : None,
                                                         }),
                                    (_MARKPOSITIONS, {'label'   : 'Mark positions',
                                                      'tipText' : 'Mark positions in all strips.',
                                                      'callBack': None,
                                                      'enabled' : True,
                                                      'checked' : True,
                                                      '_init'   : None,
                                                      }),
                                    (_AUTOCLEARMARKS, {'label'   : 'Auto clear marks',
                                                       'tipText' : 'Auto clear all previous marks',
                                                       'callBack': None,
                                                       'enabled' : True,
                                                       'checked' : True,
                                                       '_init'   : None,
                                                       }),
                                    ))

        if self.activePulldownClass:
            settingsDict.update(
                    OrderedDict(
                            ((LINKTOPULLDOWNCLASS, {'label'   : f'Link to current {self.activePulldownClass.className}',
                                                    'tipText' : f'Set/update current {self.activePulldownClass.className} when selecting from pulldown',
                                                    'callBack': None,
                                                    'enabled' : True,
                                                    'checked' : True,
                                                    '_init'   : None}),)))

        settings = self._settings = ModuleSettingsWidget(parent=self.settingsWidget, mainWindow=self.mainWindow,
                                                         settingsDict=settingsDict,
                                                         grid=(0, 0))

        # # add spacer to the settings-widget so that the right-hand-side stays aligned
        # Spacer(self.settingsWidget, 5, 5, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed, grid=(0, 1))

        # mainWidget
        self._mainFrame = RestraintFrame(parent=self.mainWidget,
                                         mainWindow=self.mainWindow,
                                         moduleParent=self, resources=self.resources,
                                         peakList=peakList, selectFirstItem=selectFirstItem,
                                         grid=(0, 0))

        # store in the resources class
        rss = self.resources
        rss._collectionPulldown = settings.getWidget(_COLLECTION)
        rss._collectionButton = settings.getWidget(_COLLECTIONBUTTON)
        rss._displayListWidget = settings.getWidget(_SPECTRUMDISPLAYS)

        rss._resTableWidget = settings.getWidget(_RESTRAINTTABLES)
        rss._resTableWidget.listChanged.connect(self._updateRestraintTables)
        rss._outTableWidget = settings.getWidget(_VIOLATIONTABLES)
        rss._outTableWidget.listChanged.connect(self._updateOutputTables)

        rss._meanLowerLimitSpinBox = settings.getWidget(_MEANLOWERLIMIT)
        rss._searchModeRadio = settings.getWidget(_SEARCHMODE)
        rss._includeNonPeaksCheckBox = settings.getWidget(_INCLUDENONPEAKS)
        rss._autoExpandCheckBox = settings.getWidget(_AUTOEXPAND)
        rss._markPositions = settings.getWidget(_MARKPOSITIONS)
        rss._autoClearMarks = settings.getWidget(_AUTOCLEARMARKS)

        rss._modulePulldown = self._mainFrame._modulePulldown
        rss.guiFrame = self._mainFrame

        # create a widget to hold the comparison-sets
        fr = self.comparisonFrame = settings.getWidget(_COMPARISONSETS)
        sa = self._scrollAreaWidget = fr._scrollArea
        sa.setScrollBarPolicies(('never', 'asNeeded'))
        # create the first empty tree
        self.addNewComparisonSet()

        # force the comparison-set widget to take up the most vertical space
        layout = self._settings.getLayout()
        if (indx := layout.indexOf(self._scrollAreaWidget)) >= 0:
            row, _col, _spanX, _spanY = layout.getItemPosition(indx)
            layout.setRowStretch(row, 100)

        alignWidgets(settings)

    @property
    def tableFrame(self):
        """Return the table frame
        """
        return self.resources.guiFrame

    @property
    def _tableWidget(self):
        """Return the table widget in the table frame
        """
        return self.resources.guiFrame._tableWidget

    @property
    def _dataFrame(self):
        """Return the pandas dataFrame - needs to be removed from dataFrameObject
        """
        if self.tableFrame._dataFrameObject:
            return self.tableFrame._dataFrameObject.dataFrame

    @property
    def dataFrame(self):
        """Return the pandas dataFrame - needs to be removed from dataFrameObject
        CHECK with above method
        """
        return self.tableFrame.dataFrame

    @dataFrame.setter
    def dataFrame(self, value):
        self.tableFrame.dataFrame = value

    def _setCallbacks(self):
        """Set the active callbacks for the module
        """
        rss = self.resources

        if self.activePulldownClass:
            self._setCurrentPulldown = Notifier(self.current,
                                                [Notifier.CURRENT],
                                                targetName=self.activePulldownClass._pluralLinkName,
                                                callback=self.tableFrame._selectCurrentPulldownClass)
            # set the active callback from the pulldown
            self._mainFrame.setActivePulldownClass(coreClass=self.activePulldownClass,
                                                   checkBox=self._settings.checkBoxes[LINKTOPULLDOWNCLASS]['widget'])

        # set the dropped callback through mainWidget
        self.mainWidget._dropEventCallback = self._processDroppedItems

        self.settingsWidget.setAcceptDrops(True)
        self.settingsWidget.setDropEventCallback(self._processDroppedItems)
        rss._resTableWidget.setPreSelect(self._applyRestraintTableFilter)
        rss._outTableWidget.setPreSelect(self._applyViolationTableFilter)

        self.tableFrame.aboutToUpdate.connect(self._changePeakList)
        rss._modulePulldown.pulldownList.popupAboutToBeShown.connect(self._applyPeakListFilter)

        self._registerNotifiers()

    def selectTable(self, table):
        """Select the object in the table
        """
        self._mainFrame.selectTable(table)

    def _closeModule(self):
        """CCPN-INTERNAL: used to close the module
        """
        rss = self.resources
        if self.activePulldownClass and self._setCurrentPulldown:
            self._setCurrentPulldown.unRegister()
        if self._settings:
            self._settings._cleanupWidget()
        if self.tableFrame:
            self.tableFrame._cleanupWidget()
        if rss._displayListWidget:
            rss._displayListWidget._close()
        if rss._resTableWidget:
            rss._resTableWidget._close()
        if rss._outTableWidget:
            rss._outTableWidget._close()
        self._unRegisterNotifiers()
        super()._closeModule()

    def _getLastSeenWidgetsState(self):
        """Internal. Used to restore last closed module in the same program instance.
        """
        widgetsState = self.widgetsState
        try:
            # Don't restore the pulldown selection from last seen.
            pulldownSaveName = self.tableFrame._modulePulldown.pulldownList.objectName()
            widgetsState.pop(f'__{pulldownSaveName}', None)
        except Exception as err:
            getLogger().debug2(f'Could not remove the pulldown state from RestraintAnalysisInspector module. {err}')
        return widgetsState

    #=========================================================================================
    # from guiTable
    #=========================================================================================

    def selectPeakList(self, peakList=None):
        """
        Manually select a peakList from the pullDown
        """
        rss = self.resources
        with rss._modulePulldown.blockWidgetSignals(blockUpdates=False):
            self._selectPeakList(peakList)
        self._updateSettings(rss._meanLowerLimitSpinBox.getValue(), rss._autoExpandCheckBox.get())

        # give the widgets time to refresh
        QtCore.QTimer.singleShot(0, self._tableWidget._updateTable)

    def restoreWidgetsState(self, **widgetsState):
        rss = self.resources
        super().restoreWidgetsState(**widgetsState)
        getLogger().debug(f'RestraintTableModule {self} - restoreWidgetsState')
        # need to set the values from the restored state
        self._updateSettings(rss._meanLowerLimitSpinBox.getValue(),
                             rss._autoExpandCheckBox.get())

    def _updateRestraintTables(self, *args):
        """Update the selected restraintTables
        """
        rss = self.resources
        restraintTables = rss._resTableWidget.getTexts()
        if ALL in restraintTables:
            restraintTables = self.project.restraintTables
        else:
            restraintTables = [self.project.getByPid(rList) for rList in restraintTables]
            restraintTables = [rList for rList in restraintTables if
                               rList is not None and isinstance(rList, RestraintTable)]

        self._updateCollectionButton(True)
        self._updateSettings(rss._meanLowerLimitSpinBox.getValue(), rss._autoExpandCheckBox.get())
        self.updateRestraintTables(restraintTables)

    def _updateOutputTables(self, *args):
        """Update the selected outputTables
        """
        rss = self.resources
        outputTables = rss._outTableWidget.getTexts()
        if ALL in outputTables:
            outputTables = [vt for vt in self.project.violationTables if vt.getMetadata(_VIOLATIONRESULT)]
        else:
            outputTables = [self.project.getByPid(rList) for rList in outputTables]
            outputTables = list(filter(None, outputTables))

        self._updateCollectionButton(True)
        self._updateSettings(rss._meanLowerLimitSpinBox.getValue(), rss._autoExpandCheckBox.get())
        self.updateOutputTables(outputTables)

    def _updateRestraintViolationTables(self, *args):
        """Update the selected restraintTables/outputTables
        """
        rss = self.resources
        restraintTables = rss._resTableWidget.getTexts()
        if ALL in restraintTables:
            restraintTables = self.project.restraintTables
        else:
            restraintTables = [self.project.getByPid(rList) for rList in restraintTables]
            restraintTables = [rList for rList in restraintTables if
                               rList is not None and isinstance(rList, RestraintTable)]

        outputTables = rss._outTableWidget.getTexts()
        if ALL in outputTables:
            outputTables = [vt for vt in self.project.violationTables if vt.getMetadata(_VIOLATIONRESULT)]
        else:
            outputTables = [self.project.getByPid(rList) for rList in outputTables]
            outputTables = list(filter(None, outputTables))

        self._updateCollectionButton(True)
        self._updateSettings(rss._meanLowerLimitSpinBox.getValue(), rss._autoExpandCheckBox.get())
        self.updateRestraintViolationTables(restraintTables, outputTables)

    def _updateAutoExpand(self, expand):
        self.resources._autoExpand = expand

    def _searchModeCallback(self):
        self._mainFrame.setRefreshButtonEnabled(True)

    def _updateIncludeNonPeaksCallback(self, nonPeaks):
        self._mainFrame.setRefreshButtonEnabled(True)

    def _updateMeanLowerLimit(self, value):
        self.resources._meanLowerLimit = value
        self._tableWidget._updateTable()

    def _registerNotifiers(self):
        """Register notifiers for the module
        """
        self._collectionNotifier = self.setNotifier(self.project, [Notifier.RENAME, Notifier.CREATE, Notifier.DELETE],
                                                    Collection.__name__, self._updatePulldownNotify, onceOnly=True)
        self._sDataNotifier = self.setNotifier(self.project, [Notifier.RENAME, Notifier.CREATE, Notifier.DELETE],
                                               StructureData.__name__, self._updatePulldownNotify, onceOnly=True)
        self._ensembleNotifier = self.setNotifier(self.project, [Notifier.RENAME, Notifier.CREATE, Notifier.DELETE],
                                                  StructureEnsemble.__name__, self._updatePulldownNotify, onceOnly=True)
        self._restraintTableNotifier = self.setNotifier(self.project,
                                                        [Notifier.RENAME, Notifier.CREATE, Notifier.DELETE],
                                                        RestraintTable.__name__, self._updatePulldownNotify,
                                                        onceOnly=True)
        self._violationTableNotifier = self.setNotifier(self.project,
                                                        [Notifier.RENAME, Notifier.CREATE, Notifier.DELETE],
                                                        ViolationTable.__name__, self._updatePulldownNotify,
                                                        onceOnly=True)

    def _unRegisterNotifiers(self):
        """Register notifiers for the module
        """
        rss = self.resources
        if rss._collectionPulldown:
            rss._collectionPulldown.unRegister()
        if self._collectionNotifier:
            self._collectionNotifier.unRegister()

    def updateRestraintTables(self, restraintTables):
        """Update the selected restraint lists from the parent module
        """
        self.resources._restraintTables = restraintTables
        self._tableWidget._updateTable()

    def updateOutputTables(self, outputTables):
        """Update the selected data lists from the parent module
        """
        self.resources._outputTables = outputTables
        self._tableWidget._updateTable()

    def updateRestraintViolationTables(self, restraintTables, outputTables):
        """Update all tables and re-populate
        """
        # must be done prior to the peakListPulldown callback
        self.resources._restraintTables = restraintTables
        self.resources._outputTables = outputTables

    def _expandAll(self, expand):
        """Expand/collapse all groups
        """
        self.updateTableExpanders(expand)

    def updateAutoExpand(self, expand):
        """Set the auto-expand/collapsed state for adding new restraintTables, or sorting table
        """
        self.resources._autoExpand = expand

    def updateMeanLowerLimit(self, value):
        """Set the lower limit for visible restraints
        """
        self.resources._meanLowerLimit = value
        self._tableWidget._updateTable()

    def _updateSettings(self, meanLowerLimit, expand):
        rss = self.resources
        rss._meanLowerLimit = meanLowerLimit
        rss._autoExpand = expand

    #=========================================================================================
    # Process dropped items
    #=========================================================================================

    # dropped here

    def _collectionPulldownCallback(self, value=None):
        """Handle manual collection pulldown selection
        """
        rss = self.resources
        if value == SELECT and rss._collectionPulldown.getIndex() == 0:
            # clear options - 'select' chosen from the pulldown
            self._resetPulldowns()
            self._clearFilters()
            self._updateSettings(rss._meanLowerLimitSpinBox.getValue(), rss._autoExpandCheckBox.get())
            # give the widgets time to refresh
            QtCore.QTimer.singleShot(0, self._tableWidget._updateTable)
            return

        # check the items in the dropped collection
        if not (collection := self.project.getByPid(value) if isinstance(value, str) else value):
            return
        if not isinstance(collection, Collection):
            MessageDialog.showWarning('Restraint Analysis Inspector', f'Object is not a collection {collection}')
            return

        # extract the linked objects in the collection
        objs = self.project.getObjectsByPids(collection.items,
                                             (PeakList, RestraintTable, ViolationTable, StructureData))
        plList = [obj for obj in objs if isinstance(obj, PeakList)]
        rTables = [obj for obj in objs if isinstance(obj, RestraintTable)]
        vTables = [obj for obj in objs if isinstance(obj, ViolationTable)]
        if (sData := [obj for obj in objs if isinstance(obj, StructureData)]):
            for sd in sData:
                rTables.extend(sd.restraintTables)
                vTables.extend(sd.violationTables)
            rTables = list(OrderedSet(rTables))
            vTables = list(OrderedSet(vTables))

        def validPKLs(rtl):
            return {pk.peakList for rst in rtl.restraints for pk in rst.peaks}

        if plList:
            for pl in plList:
                rss._restraintTableFilter[pl] = validRTL = [rtl for rtl in rTables if pl in validPKLs(rtl)]
                rss._outputTableFilter[pl] = validVTL = [vtl for vtl in vTables if vtl._restraintTableLink in validRTL]
            rss._modulePulldownFilter = plList

            # set up the texts in the restraint-tables listWidget
            with rss._resTableWidget.blockWidgetSignals(blockUpdates=False):
                if validRTL := rss._restraintTableFilter.get(plList[0]):
                    rss._resTableWidget.setTexts([obj.pid for obj in validRTL])
                else:
                    rss._resTableWidget.clearList()

            # set up the texts in the validation-tables listWidget
            with rss._outTableWidget.blockWidgetSignals(blockUpdates=False):
                if validVTL := rss._outputTableFilter.get(plList[0]):
                    rss._outTableWidget.setTexts([obj.pid for obj in validVTL])
                else:
                    rss._outTableWidget.clearList()

            self._updateRestraintViolationTables()
            if len(plList) == 1:
                # select the first-peakList
                rss._thisPeakList = plList[0]

                self.selectPeakList(plList[0])
                self._applyPeakListFilter()
            else:
                rss._thisPeakList = None
                with self.tableFrame.blockWidgetSignals(blockUpdates=False):
                    rss._modulePulldown.setIndex(0)

                self._applyPeakListFilter()
                self._updateCollectionButton(False)
                self._updateSettings(rss._meanLowerLimitSpinBox.getValue(), rss._autoExpandCheckBox.get())

                # give the widgets time to refresh
                QtCore.QTimer.singleShot(0, self._tableWidget._updateTable)

        else:
            self._resetPulldowns()
            self._clearFilters()
            self._updateCollectionButton(False)
            self._updateSettings(rss._meanLowerLimitSpinBox.getValue(), rss._autoExpandCheckBox.get())
            # give the widgets time to refresh
            QtCore.QTimer.singleShot(0, self._tableWidget._updateTable)

    def _changePeakList(self, pid):
        """Update the settings-widget depending on the peak selection
        """
        if not self.collectionSelected:
            return

        rss = self.resources
        getLogger().debug(f'>>> peaklist has changed to  {pid}')
        if (pkList := self.project.getByPid(pid)):
            if pkList in rss._modulePulldownFilter:
                rss._thisPeakList = pkList

                # set up the texts in the restraint-tables listWidget
                with rss._resTableWidget.blockWidgetSignals():
                    if validRTL := rss._restraintTableFilter.get(pkList):
                        rss._resTableWidget.setTexts([obj.pid for obj in validRTL])
                    else:
                        rss._resTableWidget.clearList()
                # set up the texts in the validation-tables listWidget
                with rss._outTableWidget.blockWidgetSignals():
                    if validVTL := rss._outputTableFilter.get(pkList):
                        rss._outTableWidget.setTexts([obj.pid for obj in validVTL])
                    else:
                        rss._outTableWidget.clearList()
                return

        rss._thisPeakList = None
        with rss._resTableWidget.blockWidgetSignals():
            rss._resTableWidget.clearList()
        with rss._outTableWidget.blockWidgetSignals():
            rss._outTableWidget.clearList()
        self._applyPeakListFilter()
        self._updateSettings(rss._meanLowerLimitSpinBox.getValue(), rss._autoExpandCheckBox.get())

        self._updateCollectionButton(True)

    def _resetPulldowns(self):
        rss = self.resources
        rss._thisPeakList = None
        with rss._modulePulldown.blockWidgetSignals():
            rss._modulePulldown.setIndex(0)
        with rss._resTableWidget.blockWidgetSignals():
            rss._resTableWidget.clearList()
        with rss._outTableWidget.blockWidgetSignals():
            rss._outTableWidget.clearList()
        self._applyPeakListFilter()

    def _clearFilters(self):
        rss = self.resources
        # clear the pulldown filters
        rss._restraintTableFilter = {}
        rss._outputTableFilter = {}
        rss._modulePulldownFilter = []

    def _collectionPulldownReset(self):
        """Reset the options from the current collection
        """
        value = self.resources._collectionPulldown.getText()
        self._collectionPulldownCallback(value)

    def _clearComparisons(self):
        """Remove all comparison-sets.
        """
        rss = self.resources
        for st in rss.comparisonSets:
            st.setVisible(False)
            st.deleteLater()
        rss.comparisonSets.clear()
        rss.guiFrame.setRefreshButtonEnabled(True)
        rss.guiModule.addNewComparisonSet()

    @property
    def collectionSelected(self) -> bool:
        """Return True if a collection has been selected in the settings
        """
        return self.resources._collectionPulldown.getIndex() > 0

    def _applyRestraintTableFilter(self, *args):
        """Filter the restraint-table pulldown when about to show
        """
        rss = self.resources
        table = rss._resTableWidget
        combo = table.pulldownList
        filt = rss._restraintTableFilter.get(rss._thisPeakList) or []
        objs = self.project.restraintTables
        filtAll = reduce(add, rss._restraintTableFilter.values(), [])
        filtOther = list(OrderedSet(filtAll) - set(filt))
        ll = [SelectToAdd] + table.standardListItems
        if self.collectionSelected:
            objs = filt + filtOther + list(OrderedSet(objs) - set(filtAll))

        table.modifyTexts(ll + [obj.pid for obj in objs])
        if filt:
            self._setPulldownColours(combo, [obj.pid for obj in filt], QtGui.QColor('green'))
        if filtOther:
            self._setPulldownColours(combo, [obj.pid for obj in filtOther], QtGui.QColor('blue'))

    def _applyViolationTableFilter(self, *args):
        """Filter the violation-table pulldown when about to show
        """
        rss = self.resources
        table = rss._outTableWidget
        combo = table.pulldownList
        filt = rss._outputTableFilter.get(rss._thisPeakList) or []
        objs = [vt for vt in self.project.violationTables if vt.getMetadata(_VIOLATIONRESULT)]
        filtAll = reduce(add, rss._outputTableFilter.values(), [])
        filtOther = list(OrderedSet(filtAll) - set(filt))
        ll = [SelectToAdd] + table.standardListItems
        if self.collectionSelected:
            objs = filt + list(OrderedSet(objs) - set(filt))

        table.modifyTexts(ll + [obj.pid for obj in objs])
        if filt:
            self._setPulldownColours(combo, [obj.pid for obj in filt], QtGui.QColor('seagreen'))
        if filtOther:
            self._setPulldownColours(combo, [obj.pid for obj in filtOther], QtGui.QColor('dodgerblue'))

    def _applyPeakListFilter(self):
        """Filter the peakList pulldown when about to show
        """
        rss = self.resources
        combo = rss._modulePulldown.pulldownList
        filt = [rss._thisPeakList] if rss._thisPeakList else []
        filtAll = rss._modulePulldownFilter
        filtOther = list(OrderedSet(filtAll) - set(filt))
        self._resetPulldownColours(combo)
        if filt:
            self._setPulldownColours(combo, [obj.pid for obj in filt], QtGui.QColor('seagreen'))
        if filtOther:
            self._setPulldownColours(combo, [obj.pid for obj in filtOther], QtGui.QColor('dodgerblue'))

    @staticmethod
    def _setPulldownColours(combo, pids, color=None):
        """Colour the pulldown items if they belong to the supplied list
        """
        color = color or QtGui.QColor('dodgerblue')
        model = combo.model()
        _inds = [ii for ii, val in enumerate(combo.texts) if val in pids]
        for ind in range(len(combo.texts)):
            itm = model.item(ind)
            if ind in _inds:
                itm.setData(color, QtCore.Qt.ForegroundRole)
        # update the pulldown to match the selected item
        combo.update()

    @staticmethod
    def _resetPulldownColours(combo):
        """Colour the pulldown items if they belong to the supplied list
        """
        model = combo.model()
        for ind in range(len(combo.texts)):
            itm = model.item(ind)
            itm.setData(None, QtCore.Qt.ForegroundRole)
        # update the pulldown to match the selected item
        combo.update()

    def _selectPeakList(self, peakList=None):
        """Manually select a PeakList from the pullDown
        """
        rss = self.resources
        if peakList is None:
            rss._modulePulldown.selectFirstItem()
        else:
            if not isinstance(peakList, PeakList):
                raise TypeError('select: Object is not of type PeakList')
            for widgetObj in rss._modulePulldown.textList:
                if peakList.pid == widgetObj:
                    self._tableWidget._selectedPeakList = peakList
                    rss._modulePulldown.select(peakList.pid)

    #=========================================================================================
    # Handle notifiers
    #=========================================================================================

    def _updateCollectionNotify(self, data):
        """Handle notifier for changed, deleted collection
        """
        rss = self.resources
        trigger = data[Notifier.TRIGGER]
        obj = data[Notifier.OBJECT]
        if obj and obj.pid == rss._collectionPulldown.getText() and trigger == Notifier.CHANGE:
            getLogger().info(f'Collection {obj.pid} in {self} needs refreshing')
            self._resetPulldowns()
            self._clearFilters()
            self._updateCollectionButton(True)
            self._updateSettings(rss._meanLowerLimitSpinBox.getValue(), rss._autoExpandCheckBox.get())
            self._tableWidget._updateTable()

    def _updatePulldownNotify(self, data):
        """Handle notifier for changed, deleted collection
        """
        rss = self.resources
        trigger = data[Notifier.TRIGGER]
        obj = data[Notifier.OBJECT]
        cSets = [cSet.comparisonSet for cSet in rss.comparisonSets]
        rTables = [rTable for cSet in rss.comparisonSets for rTable in cSet.getTreeTables(depth=1, selected=None)]
        vTables = [vTable for cSet in rss.comparisonSets for vTable in cSet.getTreeTables(depth=2, selected=None)]

        if obj in (cSets + rTables + vTables):
            getLogger().debug(f'notifier {obj}')
            for cSet in rss.comparisonSets:
                cSet._updateNotify(trigger, obj)
            self.tableFrame._updatePulldown()

    def _updateCollectionButton(self, value):
        """Enable/disable the collection button as required
        """
        self.resources._collectionButton.button.setEnabled(value and self.collectionSelected)

    #=========================================================================================
    # Process dropped items
    #=========================================================================================

    def _processDroppedItems(self, data):
        """CallBack for Drop events
        """
        pids = data.get('pids', [])
        objs = [self.project.getByPid(pid) for pid in pids]
        selectableObjects = [obj for obj in objs if isinstance(obj, Collection | StructureData | RestraintTable)]

        for grp in selectableObjects:
            if isinstance(grp, Collection):
                for itm in grp.items:
                    # get the last set
                    if not (compSet := self.resources.comparisonSets[-1]):
                        continue
                    # process item into the comparison-set tree, a bit of a hack
                    if isinstance(itm, StructureData):
                        compSet._processStructureData(itm)
                    elif isinstance(itm, RestraintTable):
                        compSet._processRestraintTables([itm])
            elif isinstance(grp, StructureData):
                # get the last set
                if not (compSet := self.resources.comparisonSets[-1]):
                    continue
                compSet._processStructureData(grp)
            elif isinstance(grp, RestraintTable):
                # get the last set
                if not (compSet := self.resources.comparisonSets[-1]):
                    continue
                compSet._processRestraintTables([grp])

    def _handleDroppedItems(self, pids, objType, pulldown):
        """handle dropping pids onto the table
        :param pids: the selected objects pids
        :param objType: the instance of the obj to handle, e.g. PeakList
        :param pulldown: the pulldown of the module wich updates the table
        :return: Actions: Select the dropped item on the table or/and open a new modules if multiple drops.
        If multiple different obj instances, then asks first.
        """
        from ccpn.ui.gui.lib.MenuActions import _openItemObject
        from ccpn.ui.gui.widgets.MessageDialog import showYesNo

        objs = [self.project.getByPid(pid) for pid in pids]
        selectableObjects = [obj for obj in objs if isinstance(obj, objType)]
        others = [obj for obj in objs if not isinstance(obj, objType)]
        if selectableObjects:
            _openItemObject(self.mainWindow, selectableObjects[1:])
            pulldown.select(selectableObjects[0].pid)
        elif othersClassNames := list({obj.className for obj in others if hasattr(obj, 'className')}):
            title, msg = (
                'Dropped wrong item.', f"Do you want to open the {''.join(othersClassNames)} in a new module?") if len(
                    othersClassNames) == 1 else ('Dropped wrong items.', 'Do you want to open items in new modules?')

            if showYesNo(title, msg):
                _openItemObject(self.mainWindow, others)

    def addNewComparisonSet(self):
        """Add a new comparison-set to the list
        """
        rss = self.resources
        newState = not any(cs.isEmpty for cs in rss.comparisonSets)
        if newState:
            fr = self.comparisonFrame
            _ComparisonTree(fr, grid=(fr.getLayout().rowCount(), 0),
                            enableMouseMenu=True, resources=rss)


#=========================================================================================
# Testing
#=========================================================================================

def main():
    # show the empty module
    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # create a new test application
    app = newTestApplication(interface='Gui')
    application = getApplication()
    mainWindow = application.ui.mainWindow

    # add the module to mainWindow
    _module = RestraintAnalysisTableModule(mainWindow=mainWindow)
    mainWindow.moduleArea.addModule(_module)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    main()
