"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-05-17 13:37:45 +0100 (Fri, May 17, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-05-04 17:15:05 +0000 (Mon, May 04, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

import os
from functools import partial
from collections import OrderedDict
import json
import pandas as pd

from PyQt5 import QtGui, QtWidgets, QtCore
from contextlib import contextmanager
from dataclasses import dataclass

from ccpn.ui.gui.popups.Dialog import CcpnDialogMainWidget
from ccpn.ui.gui.widgets.ProjectTreeCheckBoxes import ImportTreeCheckBoxes, RENAMEACTION, BADITEMACTION
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Splitter import Splitter
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.SpeechBalloon import SpeechBalloon
from ccpn.ui.gui.widgets.Font import getFontHeight
from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame
from ccpn.ui.gui.widgets.TextEditor import TextEditor
from ccpn.ui.gui.widgets.VLine import VLine
from ccpn.ui.gui.widgets.table.Table import Table
from ccpn.ui.gui.widgets.table._TableModel import _TableModel, DISPLAY_ROLE
from ccpn.ui.gui.lib.Validators import LineEditValidator, LineEditValidatorWhiteSpace
from ccpn.ui.gui.guiSettings import getColours, BORDERNOFOCUS

from ccpn.framework.lib.ccpnNef import CcpnNefIo
from ccpn.framework.lib.ccpnNef.CcpnNefIo import DATANAME
from ccpn.framework.lib.ccpnNef.CcpnNefCommon import nef2CcpnClassNames

from ccpn.core.lib.ContextManagers import catchExceptions  #, busyHandler
from ccpn.core.lib.Pid import Pid, IDSEP
from ccpn.core.Project import Project
from ccpn.core.StructureData import StructureData
from ccpn.core.Collection import Collection
from ccpn.util.nef import StarIo, NefImporter as Nef
from ccpn.util.Logging import getLogger
from ccpn.util.PrintFormatter import PrintFormatter
from ccpn.util.AttrDict import AttrDict
from ccpn.util.OrderedSet import OrderedSet


INVALIDTEXTROWCHECKCOLOUR = QtGui.QColor('crimson')
INVALIDTEXTROWNOCHECKCOLOUR = QtGui.QColor('darkorange')
INVALIDBUTTONCHECKCOLOUR = QtGui.QColor('lightpink')
INVALIDBUTTONNOCHECKCOLOUR = QtGui.QColor('navajowhite')
INVALIDTABLEFILLCHECKCOLOUR = QtGui.QColor('lightpink')
INVALIDTABLEFILLNOCHECKCOLOUR = QtGui.QColor('navajowhite')

CHAINS = 'chains'
NMRCHAINS = 'nmrChains'
RESTRAINTTABLES = 'restraintTables'
CCPNTAG = 'ccpn'
SKIPPREFIXES = 'skipPrefixes'
EXPANDSELECTION = 'expandSelection'
INCLUDEORPHANS = 'includeOrphans'

PulldownListsMinimumWidth = 200
LineEditsMinimumWidth = 195
NotImplementedTipText = 'This option has not been implemented yet'
DEFAULTSPACING = (3, 3)
TABMARGINS = (1, 10, 10, 1)  # l, t, r, b
ZEROMARGINS = (0, 0, 0, 0)  # l, t, r, b
COLOURALLCOLUMNS = False

NEFFRAMEKEY_IMPORT = 'nefObject'
NEFFRAMEKEY_ENABLECHECKBOXES = 'enableCheckBoxes'
NEFFRAMEKEY_ENABLERENAME = 'enableRename'
NEFFRAMEKEY_ENABLEFILTERFRAME = 'enableFilterFrame'
NEFFRAMEKEY_ENABLEMOUSEMENU = 'enableMouseMenu'
NEFFRAMEKEY_PATHNAME = 'pathName'

NEFDICTFRAMEKEYS = {NEFFRAMEKEY_IMPORT           : (Nef.NefImporter, Project),
                    NEFFRAMEKEY_ENABLECHECKBOXES : bool,
                    NEFFRAMEKEY_ENABLERENAME     : bool,
                    NEFFRAMEKEY_ENABLEFILTERFRAME: bool,
                    NEFFRAMEKEY_ENABLEMOUSEMENU  : bool,
                    NEFFRAMEKEY_PATHNAME         : str,
                    }
NEFDICTFRAMEKEYS_REQUIRED = (NEFFRAMEKEY_IMPORT,)
REMOVEENTRY = '<Remove from Collections>'
STRUCTUREDATA = 'StructureData'
COLLECTION = 'Collection'
STRUCTUREDATA_ATTRIB = STRUCTUREDATA.lower()
COLLECTION_ATTRIB = COLLECTION.lower()


# simple class to export variables from the contextmanager
@dataclass
class _TreeValues:
    item = None
    itemName = None
    itemPid = None
    saveFrame = None
    mappingCode = None
    errorCode = None
    mapping = None
    _content = None
    _errors = None
    _fillColour = None
    plural = None
    singular = None
    row = None
    parentGroup = None
    ccpnClassName = None
    pHandler = None
    newVal = None


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# _NefTableModel/NefTable
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class _NefTableModel(_TableModel):
    """Modified model to display '.' insteaad of 'None' to match nef specification.
    """

    def data(self, index, role=DISPLAY_ROLE):
        """Return the data/roles for the model.
        """
        if not index.isValid():
            return None

        result = super().data(index, role)
        if role == DISPLAY_ROLE:
            # change table occurrences of 'None' to '.'
            if result == 'None':
                return '.'

        return result


class NefTable(Table):
    """Modified model - using modified model above - to display '.' insteaad of 'None' to match nef specification.
    """
    tableModelClass = _NefTableModel


class NefDictFrame(Frame):
    """
    Class to handle a nef dictionary editor
    """
    EDITMODE = True
    handleSaveFrames = {}
    handleParentGroups = {}
    _setBadSaveFrames = {}
    applyCheckBoxes = {}

    DEFAULTMARGINS = (8, 8, 8, 8)  # l, t, r, b

    def __init__(self, parent, mainWindow, nefLoader, dataBlock, pathName,
                 enableCheckBoxes=False, enableRename=False,
                 enableFilterFrame=False, enableMouseMenu=False,
                 showBorder=True, borderColour=None, _splitterMargins=DEFAULTMARGINS,
                 **kwds):
        """Initialise the widget"""
        super().__init__(parent, setLayout=True, spacing=DEFAULTSPACING, **kwds)

        self._parent = parent
        self.mainWindow = mainWindow
        if mainWindow:
            self.mainWindow = mainWindow
            self.application = mainWindow.application
            self.project = mainWindow.project
            self._nefReader = CcpnNefIo.CcpnNefReader(self.application)
            self._nefWriter = CcpnNefIo.CcpnNefWriter(self.project)
        # else:
        #     # to @ED: do not write code that
        #     self.mainWindow = None
        #     self.application = None
        #     self.project = None
        #     self._nefReader = None
        #     self._nefWriter = None

        self._primaryProject = True
        self.showBorder = showBorder
        self._borderColour = borderColour or QtGui.QColor(getColours()[BORDERNOFOCUS])
        self._enableCheckBoxes = enableCheckBoxes
        self._enableRename = enableRename
        self._enableFilterFrame = enableFilterFrame
        self._enableMouseMenu = enableMouseMenu
        self._pathName = pathName
        self._collections = {}
        self._collectionsTable = None

        self._structureData = {}
        self._structureDataTable = None

        # self._nefImporterClass = nefImporterClass
        # set the nef object - nefLoader/nefDict
        # self._initialiseNefLoader(nefObject, _ignoreError=True)
        self._nefLoader = nefLoader
        self._nefDict = dataBlock
        self._primaryProject = False

        # set up the widgets
        self._setWidgets()
        self._setCallbacks()

        # additional settings
        self._minusIcon = Icon('icons/minus.png')
        self._plusIcon = Icon('icons/plus.png')
        self._nefWidgets = []
        self.valid = None
        self._nefImporterOpenFirstTable = self.application.preferences.appearance.nefImporterOpenFirstTable

        # needs to be done this way otherwise _splitterMargins is 'empty' or clashes with frame stylesheet
        self.setContentsMargins(*_splitterMargins)

        # define the list of dicts for comparing object names
        self._contentCompareDataBlocks = ()

        # this is not very generic :|

        # add the rename action to the treeview actions
        self.nefTreeView.setActionCallback(RENAMEACTION, self._autoRenameItem)

        # add the rename action to the treeview actions
        self.nefTreeView.setActionCallback(BADITEMACTION, self._checkBadItem)

        # add the collection fill option to the bottom of the menu
        self.nefTreeView.setPostMenuAction(partial(self._addToCollectionsMenu, selectionWidget=self.nefTreeView))

    def paintEvent(self, ev):
        """Paint the border to the screen
        """
        if not self.showBorder:
            return

        # create a rectangle and painter over the widget - shrink by 1 pixel to draw correctly
        p = QtGui.QPainter(self)
        rgn = self.rect()
        rgn = QtCore.QRect(rgn.x(), rgn.y(), rgn.width() - 1, rgn.height() - 1)

        p.setPen(QtGui.QPen(self._borderColour, 1))
        p.drawRect(rgn)
        p.end()

    # def _initialiseProject(self, mainWindow, application, project):
    #     """Initialise the project setting - ONLY REQUIRED FOR TESTING when mainWindow doesn't exist
    #     """
    #     # set the project
    #     self.mainWindow = mainWindow
    #     self.application = application
    #     self.project = project
    #     if mainWindow is None:
    #         self.mainWindow = AttrDict()
    #
    #     # set the new values for application and project
    #     self.mainWindow.application = application
    #     self.mainWindow.project = project
    #
    #     # initialise the base structure from the project
    #     self.nefTreeView._populateTreeView(project)
    #
    #     self._nefReader = CcpnNefIo.CcpnNefReader(self.application)
    #     self._nefWriter = CcpnNefIo.CcpnNefWriter(self.project)

    # def _initialiseNefLoader(self, nefObject=None, _ignoreError=False):
    #     if not (nefObject or _ignoreError):
    #         raise TypeError('nefObject must be defined')
    #
    #     self._nefLoader = None
    #     self._nefDict = None
    #     if isinstance(nefObject, self._nefImporterClass):
    #         self._nefLoader = nefObject
    #         self._nefDict = nefObject._nefDict
    #         self._primaryProject = False
    #     elif isinstance(nefObject, Project):
    #         self.project = nefObject
    #         self._nefLoader = self._nefImporterClass(errorLogging=Nef.el.NEF_STANDARD, hidePrefix=True)
    #         self._nefWriter = CcpnNefIo.CcpnNefWriter(self.project)
    #         self._nefDict = self._nefLoader._nefDict = self._nefWriter.exportProject(expandSelection=True, includeOrphans=False, pidList=None)

    def _setCallbacks(self):
        """Set the mouse callback for the treeView

        Only fires if an item of the tree is clicked without moving/dragging to another item
        """
        # self.nefTreeView.itemClicked.connect(self._nefTreeClickedCallback)
        self.nefTreeView.mouseRelease.connect(self._mouseReleaseCallback)
        self.nefTreeView.itemChanged.connect(self._mouseChecked)

    def _setWidgets(self):
        """Set up the unpopulated widgets for the frame
        """
        self._headerFrameOuter = Frame(self, setLayout=True, showBorder=False, grid=(0, 0),
                                       hAlign='left', hPolicy='ignored', vPolicy='fixed')
        self.headerFrame = Frame(self._headerFrameOuter, setLayout=True,
                                 grid=(1, 0))

        self.headerLabel = Label(self._headerFrameOuter, text='FRAMEFRAME', grid=(0, 0), gridSpan=(1, 3))
        self.verifyButton = Button(self.headerFrame, text='Verify Now', grid=(1, 0),
                                   callback=self._verifyPopulate)
        self.verifyButton.setVisible(not self._primaryProject)

        _verifyLabel = Label(self.headerFrame, 'always verify', grid=(1, 1), hPolicy='minimum', vPolicy='minimum')
        self.verifyCheckBox = CheckBox(self.headerFrame, grid=(1, 2), checked=False, checkable=True)
        _verifyLabel.setVisible(not self._primaryProject)
        self.verifyCheckBox.setVisible(not self._primaryProject)
        self.headerFrame.getLayout().setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.verifyCheckBox.clicked.connect(self._verifyChecked)

        self.headerFrame.setVisible(False)
        self.headerFrame.setEnabled(False)

        # add the pane for the treeview/tables
        self._paneSplitter = Splitter(self, setLayout=True, horizontal=True)

        # add the pane for the treeview/tables
        self._treeSplitter = Splitter(self, setLayout=True, horizontal=False)

        # set the top frames
        self._treeFrame = Frame(self, setLayout=True, showBorder=False, grid=(0, 0))
        self._infoFrame = Frame(self, setLayout=True, showBorder=False, grid=(0, 0))

        # must be added this way to fill the frame
        self.getLayout().addWidget(self._paneSplitter, 1, 0)
        self._paneSplitter.addWidget(self._treeSplitter)
        self._paneSplitter.addWidget(self._infoFrame)
        self._paneSplitter.setChildrenCollapsible(False)

        self._treeSplitter.addWidget(self._treeFrame)
        self._treeSplitter.setChildrenCollapsible(False)
        self._treeSplitter.setStretchFactor(0, 1)
        self._treeSplitter.setStretchFactor(1, 2)
        # self._treeSplitter.setStyleSheet("QSplitter::handle { background-color: gray }")
        self._treeSplitter.setSizes([10000, 15000])

        self.nefTreeView = ImportTreeCheckBoxes(self._treeFrame, project=self.project, grid=(1, 0),
                                                includeProject=True, enableCheckBoxes=self._enableCheckBoxes,
                                                enableMouseMenu=self._enableMouseMenu,
                                                pathName=os.path.basename(self._pathName) if self._pathName else None,
                                                multiSelect=True)

        # info frame (right frame)
        self._optionsSplitter = Splitter(self._infoFrame, setLayout=True, horizontal=False)
        self._infoFrame.getLayout().addWidget(self._optionsSplitter, 0, 0)
        VLine(self._infoFrame, grid=(0, 1), width=16)

        self.tablesFrame = Frame(self._optionsSplitter, setLayout=True, showBorder=False, grid=(0, 0))
        self._optionsFrame = Frame(self._optionsSplitter, setLayout=True, showBorder=False, grid=(1, 0))
        self._optionsSplitter.addWidget(self.tablesFrame)

        # self._optionsSplitter.addWidget(self._optionsFrame)
        self._paneSplitter.addWidget(self._optionsFrame)

        self._frameOptionsNested = Frame(self._optionsFrame, setLayout=True, showBorder=False, grid=(1, 0))
        self.frameOptionsFrame = Frame(self._frameOptionsNested, setLayout=True, showBorder=False, grid=(2, 0))
        self.fileFrame = Frame(self._optionsFrame, setLayout=True, showBorder=False, grid=(2, 0))

        self._filterLogFrame = MoreLessFrame(self._optionsFrame, name='Filter Log', showMore=False, grid=(3, 0),
                                             gridSpan=(1, 1))
        self._treeSplitter.addWidget(self._filterLogFrame)

        _frame, self._structureDataTable = self._addTableToFrame(
                pd.DataFrame({STRUCTUREDATA: self._structureData.keys(),
                              'Items'      : ['\n'.join(vv for vv in val) for val in self._structureData.values()]}),
                _name=f'{STRUCTUREDATA}',
                ignoreFrame=True, showMore=True)
        self._frameOptionsNested.getLayout().addWidget(_frame, 0, 0)
        _frame, self._collectionsTable = self._addTableToFrame(pd.DataFrame({COLLECTION: self._collections.keys(),
                                                                             'Items'   : ['\n'.join(vv for vv in val)
                                                                                          for val in
                                                                                          self._collections.values()]}),
                                                               _name=f'{COLLECTION}s',
                                                               ignoreFrame=True, showMore=True)
        self._frameOptionsNested.getLayout().addWidget(_frame, 1, 0)

        _row = 0
        self.logData = TextEditor(self._filterLogFrame.contentsFrame, grid=(_row, 0), gridSpan=(1, 3), addWordWrap=True)
        self.logData.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self.logData.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)

        # tables frame
        # add a splitter
        self._tableSplitter = Splitter(self, setLayout=True, horizontal=False)
        self._tableSplitter.setChildrenCollapsible(False)
        self.tablesFrame.getLayout().addWidget(self._tableSplitter, 0, 0)
        Spacer(self.tablesFrame, 3, 3,
               QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding,
               grid=(1, 0))
        # increase the stretch for the splitter to make it fill the widget, unless all others are fixed height :)
        self.tablesFrame.getLayout().setRowStretch(0, 2)

        # set the subframe to be ignored and minimum to stop the widgets overlapping - remember this for other places
        # self._frameOptionsNested.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Minimum)
        # self._frameOptionsNested.setMinimumWidth(100)
        # self.frameOptionsFrame.getLayout().setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self._frameOptionsNested.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum)

        # options frame
        pass

        # file frame
        pass

        self._paneSplitter.setStretchFactor(0, 1)
        self._paneSplitter.setStretchFactor(1, 2)
        self._paneSplitter.setStretchFactor(2, 2)
        # self._paneSplitter.setStyleSheet("QSplitter::handle { background-color: gray }")
        self._paneSplitter.setSizes([10000, 12000, 18000])

    def _populate(self):
        """Fill the treeView from the nef dictionary
        """
        if self.project:
            with self.blockWidgetSignals():
                if self._nefLoader:
                    # populate from the _nefLoader
                    self.nefTreeView.fillTreeView(self._nefLoader._nefDict)
                    self.nefTreeView.expandAll()
                elif self._nefDict:
                    # populate from dict
                    self.nefTreeView.fillTreeView(self._nefLoader._nefDict)
                    self.nefTreeView.expandAll()

                if self._pathName:
                    self.headerLabel.setText(self._pathName)
                elif self.project:
                    self.headerLabel.setText(self.project.name)
                else:
                    self.headerLabel.setText('')

                self._colourTreeView()

                # clean parentGroups that have no children
                _dd = []
                self._traverseTree(self.nefTreeView.headerItem, func=self._removeParentTreeState, data=_dd)
                for itm in _dd:
                    itm.parent() and itm.parent().removeChild(itm)

        # force an event to show/resize the horizontal-scrollbar correctly
        self.nefTreeView.resizeColumnToContents(0)

    def _colourTreeView(self):
        projectSections = self.nefTreeView.nefToTreeViewMapping
        saveFrameLists = self.nefTreeView.nefProjectToSaveFramesMapping

        projectColour = self.nefTreeView._foregroundColour
        _projectError = False
        treeRoot = self.nefTreeView.invisibleRootItem()
        if not treeRoot.childCount():
            return
        projectItem = treeRoot.child(0)

        # iterate through all the groups in the tree, e.g., chains/samples/peakLists
        for section, (plural, singular) in projectSections.items():
            # find item in treeItem
            pluralItem = self.nefTreeView.findSection(plural)
            if pluralItem:
                pluralItem = pluralItem[0] if isinstance(pluralItem, list) else pluralItem

                sectionColour = self.nefTreeView._foregroundColour

                # iterate through the items in the group, e.g., peakList/integralList/sample
                _sectionError = False
                child_count = pluralItem.childCount()
                for i in range(child_count):
                    childItem = pluralItem.child(i)
                    childColour = self.nefTreeView._foregroundColour

                    # get the saveFrame associated with this item
                    itemName, saveFrame, parentGroup, pHandler, ccpnClassName = childItem.data(1, 0)

                    # NOTE:ED - need a final check on this
                    _errorName = getattr(saveFrame, '_rowErrors', None) and saveFrame._rowErrors.get(
                            saveFrame['sf_category'])
                    if _errorName and itemName in _errorName:  # itemName
                        _sectionError = True

                    loops = self._nefReader._getLoops(self.project, saveFrame)
                    _rowError = False
                    for loop in loops:

                        # get the group name add fetch the correct mapping
                        mapping = self.nefTreeView.nefProjectToSaveFramesMapping.get(parentGroup)
                        if mapping and loop.name not in mapping:
                            continue

                        # NOTE:ED - if there are no loops then _sectionError is never set
                        if hasattr(saveFrame, '_rowErrors') and \
                                loop.name in saveFrame._rowErrors and \
                                saveFrame._rowErrors[loop.name]:
                            # _rowError = True
                            _sectionError = True
                            # _projectError = True

                    primaryHandler = self.nefTreeView.nefProjectToHandlerMapping.get(parentGroup) or saveFrame.get(
                            'sf_category')
                    if primaryHandler:
                        if primaryHandler in self._setBadSaveFrames:
                            handler = self._setBadSaveFrames[primaryHandler]
                            if handler is not None:
                                _rowError = handler(self, name=itemName, saveFrame=saveFrame, parentGroup=parentGroup)

                    if _rowError:
                        childColour = INVALIDTEXTROWCHECKCOLOUR if childItem.checkState(
                                0) else INVALIDTEXTROWNOCHECKCOLOUR
                    self.nefTreeView.setForegroundForRow(childItem, childColour)

                if _sectionError:
                    sectionColour = INVALIDTEXTROWCHECKCOLOUR if pluralItem.checkState(
                            0) else INVALIDTEXTROWNOCHECKCOLOUR
                    if pluralItem.checkState(0):
                        _projectError = True
                self.nefTreeView.setForegroundForRow(pluralItem, sectionColour)

        if _projectError:
            projectColour = INVALIDTEXTROWCHECKCOLOUR if projectItem.checkState(0) else INVALIDTEXTROWNOCHECKCOLOUR
        self.nefTreeView.setForegroundForRow(projectItem, projectColour)

    def table_nef_molecular_system(self, saveFrame, item):
        itemName = item.data(0, 0)
        primaryCode = 'nef_sequence_chain_code'
        _content = getattr(saveFrame, '_content', None)
        _errors = getattr(saveFrame, '_rowErrors', {})

        numPrimary = _content.get(primaryCode)
        if numPrimary and len(numPrimary) <= 1:
            return

        if _errors:
            _fillColour = INVALIDTABLEFILLCHECKCOLOUR if item.checkState(0) else INVALIDTABLEFILLNOCHECKCOLOUR

            # colour rows by extra colour
            chainErrors = _errors.get('nef_sequence_' + itemName)
            if chainErrors:
                table = self._nefTables.get('nef_sequence')

                with self._tableColouring(table) as setRowBackgroundColour:
                    for rowIndex in chainErrors:
                        setRowBackgroundColour(rowIndex, _fillColour)

    def table_ccpn_assignment(self, saveFrame, item, listName=None):
        tables = ['nmr_chain', 'nmr_residue', 'nmr_atom']
        primaryCode = 'nmr_chain'
        itemName = item.data(0, 0)
        _content = getattr(saveFrame, '_content', None)
        _errors = getattr(saveFrame, '_rowErrors', {})

        numPrimary = _content.get(primaryCode)
        if numPrimary and len(numPrimary) <= 1:
            return

        if _errors:
            _fillColour = INVALIDTABLEFILLCHECKCOLOUR if item.checkState(0) else INVALIDTABLEFILLNOCHECKCOLOUR

            for tableName in tables:
                # colour rows by extra colour
                chainErrors = _errors.get('_'.join([tableName, itemName]))
                if chainErrors:
                    table = self._nefTables.get(tableName)

                    with self._tableColouring(table) as setRowBackgroundColour:
                        for rowIndex in chainErrors:
                            setRowBackgroundColour(rowIndex, _fillColour)

    def table_lists(self, saveFrame, item, listName, postFix='list'):
        itemName = item.data(0, 0)
        primaryCode = '_'.join([listName, postFix])
        _content = getattr(saveFrame, '_content', None)
        _errors = getattr(saveFrame, '_rowErrors', {})

        numPrimary = _content.get(primaryCode)
        if numPrimary and len(numPrimary) <= 1:
            return

        if _errors:
            _fillColour = INVALIDTABLEFILLCHECKCOLOUR if item.checkState(0) else INVALIDTABLEFILLNOCHECKCOLOUR

            # colour rows by extra colour
            chainErrors = _errors.get('_'.join([listName, itemName]))
            if chainErrors:
                table = self._nefTables.get(listName)

                with self._tableColouring(table) as setRowBackgroundColour:
                    for rowIndex in chainErrors:
                        setRowBackgroundColour(rowIndex, _fillColour)
            chainErrors = _errors.get('_'.join([listName, postFix, itemName]))
            if chainErrors:
                table = self._nefTables.get('_'.join([listName, postFix]))

                with self._tableColouring(table) as setRowBackgroundColour:
                    for rowIndex in chainErrors:
                        setRowBackgroundColour(rowIndex, _fillColour)

    def table_peak_lists(self, saveFrame, item, listName=None):
        listItemName = 'nef_peak'
        listName = 'ccpn_peak'
        primaryCode = 'nef_peak'
        itemName = item.data(0, 0)
        _content = getattr(saveFrame, '_content', None)
        _errors = getattr(saveFrame, '_rowErrors', {})

        numPrimary = _content.get(primaryCode)
        if numPrimary and len(numPrimary) <= 1:
            return

        if _errors:
            _fillColour = INVALIDTABLEFILLCHECKCOLOUR if item.checkState(0) else INVALIDTABLEFILLNOCHECKCOLOUR

            # colour rows by extra colour
            chainErrors = _errors.get('_'.join([listItemName, itemName]))
            if chainErrors:
                table = self._nefTables.get(listItemName)

                with self._tableColouring(table) as setRowBackgroundColour:
                    for rowIndex in chainErrors:
                        setRowBackgroundColour(rowIndex, _fillColour)
            chainErrors = _errors.get('_'.join([listName, 'list', itemName]))
            if chainErrors:
                table = self._nefTables.get('_'.join([listName, 'list']))

                with self._tableColouring(table) as setRowBackgroundColour:
                    for rowIndex in chainErrors:
                        setRowBackgroundColour(rowIndex, _fillColour)

    # def table_peak_clusters(self, saveFrame, item, listName=None):
    #     listItemName = 'ccpn_peak_cluster'
    #     listName = 'ccpn_peak_cluster'
    #     primaryCode = 'ccpn_peak_cluster'
    #     itemName = item.data(0, 0)
    #     _content = getattr(saveFrame, '_content', None)
    #     _errors = getattr(saveFrame, '_rowErrors', {})
    #
    #     numPrimary = _content.get(primaryCode)
    #     if numPrimary and len(numPrimary) <= 1:
    #         return
    #
    #     if _errors:
    #         _fillColour = INVALIDTABLEFILLCHECKCOLOUR if item.checkState(0) else INVALIDTABLEFILLNOCHECKCOLOUR
    #
    #         # colour rows by extra colour
    #         chainErrors = _errors.get('_'.join([listItemName, itemName]))
    #         if chainErrors:
    #             table = self._nefTables.get(listItemName)
    #
    #             with self._tableColouring(table) as setRowBackgroundColour:
    #                 for rowIndex in chainErrors:
    #                     setRowBackgroundColour(rowIndex, _fillColour)
    #         chainErrors = _errors.get('_'.join([listName, 'peaks', itemName]))
    #         if chainErrors:
    #             table = self._nefTables.get('_'.join([listName, 'peaks']))
    #
    #             with self._tableColouring(table) as setRowBackgroundColour:
    #                 for rowIndex in chainErrors:
    #                     setRowBackgroundColour(rowIndex, _fillColour)

    def table_ccpn_notes(self, saveFrame, item):
        itemName = item.data(0, 0)
        primaryCode = 'ccpn_notes'
        _content = getattr(saveFrame, '_content', None)
        _errors = getattr(saveFrame, '_rowErrors', {})

        numPrimary = _content.get(primaryCode)
        if numPrimary and len(numPrimary) <= 1:
            return

        if _errors:
            _fillColour = INVALIDTABLEFILLCHECKCOLOUR if item.checkState(0) else INVALIDTABLEFILLNOCHECKCOLOUR

            # colour rows by extra colour
            chainErrors = _errors.get('ccpn_note_' + itemName)
            if chainErrors:
                table = self._nefTables.get('ccpn_note')

                with self._tableColouring(table) as setRowBackgroundColour:
                    for rowIndex in chainErrors:
                        setRowBackgroundColour(rowIndex, _fillColour)

    def table_ccpn_collections(self, saveFrame, item):
        itemName = item.data(0, 0)
        primaryCode = 'ccpn_collections'
        _content = getattr(saveFrame, '_content', None)
        _errors = getattr(saveFrame, '_rowErrors', {})

        numPrimary = _content.get(primaryCode)
        if numPrimary and len(numPrimary) <= 1:
            return

        if _errors:
            _fillColour = INVALIDTABLEFILLCHECKCOLOUR if item.checkState(0) else INVALIDTABLEFILLNOCHECKCOLOUR

            # colour rows by extra colour
            chainErrors = _errors.get('ccpn_collection_' + itemName)
            if chainErrors:
                table = self._nefTables.get('ccpn_collection')

                with self._tableColouring(table) as setRowBackgroundColour:
                    for rowIndex in chainErrors:
                        setRowBackgroundColour(rowIndex, _fillColour)

    def table_ccpn_additional_data(self, saveFrame, item):
        itemName = item.data(0, 0)
        primaryCode = 'ccpn_additional_data'
        _content = getattr(saveFrame, '_content', None)
        _errors = getattr(saveFrame, '_rowErrors', {})

        numPrimary = _content.get(primaryCode)
        if numPrimary and len(numPrimary) <= 1:
            return

        if _errors:
            _fillColour = INVALIDTABLEFILLCHECKCOLOUR if item.checkState(0) else INVALIDTABLEFILLNOCHECKCOLOUR

            # colour rows by extra colour
            chainErrors = _errors.get('ccpn_internal_data_' + itemName)
            if chainErrors:
                table = self._nefTables.get('ccpn_internal_data')

                with self._tableColouring(table) as setRowBackgroundColour:
                    for rowIndex in chainErrors:
                        setRowBackgroundColour(rowIndex, _fillColour)

    def _set_bad_saveframe(self, name=None, saveFrame=None, parentGroup=None, prefix=None, mappingCode=None,
                           errorCode=None, tableColourFunc=None):
        # check if the current saveFrame exists; i.e., category exists as row = [0]
        item = self.nefTreeView.findSection(name, parentGroup)
        if not item:
            getLogger().debug2('>>> not found {} {} {}'.format(name, saveFrame, parentGroup))
            return
        if isinstance(item, list):
            # find the correct one from the saveframe
            for itm in item:
                itemName, sFrame, parentGroup, pHandler, ccpnClassName = itm.data(1, 0)
                # if itm.data(1, 0) == saveFrame:
                if sFrame == saveFrame:
                    item = itm
                    break
            else:
                getLogger().debug2('>>> not found {} {} {}'.format(name, saveFrame, parentGroup))
                return

        itemName = item.data(0, 0)

        mappingCode = mappingCode or ''
        errorCode = errorCode or ''
        mapping = self.nefTreeView.nefToTreeViewMapping.get(mappingCode)

        _content = getattr(saveFrame, '_content', None)
        _errors = getattr(saveFrame, '_rowErrors', {})
        _bad = False
        if _content and mapping:
            if errorCode in _errors and itemName in _errors[errorCode]:
                _bad = True

        return _bad

    def apply_checkBox_item(self, name=None, saveFrame=None, parentGroup=None, prefix=None, mappingCode=None,
                            checkID='_importRows'):
        # check if the current saveFrame exists; i.e., category exists as row = [0]
        item = self.nefTreeView.findSection(name, parentGroup)
        if not item:
            getLogger().debug2('>>> not found {} {} {}'.format(name, saveFrame, parentGroup))
            return
        if isinstance(item, list):
            # find the correct one from the saveframe
            for itm in item:
                itemName, sFrame, parentGroup, pHandler, ccpnClassName = itm.data(1, 0)
                # if itm.data(1, 0) == saveFrame:
                if sFrame == saveFrame:
                    item = itm
                    break
            else:
                getLogger().debug2('>>> not found {} {} {}'.format(name, saveFrame, parentGroup))
                return

        itemName = item.data(0, 0)

        _importList = self._nefReader._importDict.get(saveFrame.name)
        if not _importList:
            _importList = self._nefReader._importDict[saveFrame.name] = {}

        if not _importList.get(checkID):
            _importList[checkID] = (itemName,)
        else:
            _importList[checkID] += (itemName,)

    def _checkParentGroup(self, name, parentGroup, saveFrame):
        """Search for the parentGroup in the treeView
        :return: treeItem
        """
        # check if the current saveFrame exists; i.e., category exists as row = [0]
        item = self.nefTreeView.findSection(name, parentGroup)
        if not item:
            getLogger().debug2('>>> not found {} {} {}'.format(name, saveFrame, parentGroup))
            return
        if isinstance(item, list):
            # find the correct one from the saveframe
            for itm in item:
                itemName, sFrame, parentGroup, pHandler, ccpnClassName = itm.data(1, 0)
                # if itm.data(1, 0) == saveFrame:
                if sFrame == saveFrame:
                    item = itm
                    break
            else:
                getLogger().debug2('>>> not found {} {} {}'.format(name, saveFrame, parentGroup))
                return

        return item

    def _handleTreeView(self, name=None, saveFrame=None, parentGroup=None, prefix=None, mappingCode=None,
                        errorCode=None, tableColourFunc=None, _handleAutoRename=False):
        # this is treated as a generator

        # check if the current saveFrame exists; i.e., category exists as row = [0]
        if not (item := self._checkParentGroup(name, parentGroup, saveFrame)):
            return

        if _handleAutoRename:
            self._handleItemRename(item, mappingCode, saveFrame)
            return

        vals = _TreeValues()
        vals.item = item

        _data = item.data(1, 0)
        itemName, sFrame, parentGroup, pHandler, ccpnClassName = _data
        vals.itemName = itemName
        vals.saveFrame = sFrame
        vals.parentGroup = parentGroup

        vals.mappingCode = mappingCode or ''
        vals.errorCode = errorCode or ''
        vals.mapping = self.nefTreeView.nefToTreeViewMapping.get(mappingCode)
        vals.ccpnClassName = ccpnClassName

        vals._content = getattr(saveFrame, '_content', None)
        vals._errors = getattr(saveFrame, '_rowErrors', {})
        vals.row = 0

        if vals._content and vals.mapping:
            vals._fillColour = INVALIDBUTTONCHECKCOLOUR if item.checkState(0) else INVALIDBUTTONNOCHECKCOLOUR
            vals.plural, vals.singular = vals.mapping

            # return the values as a generator - only returns once, skipped if no item
            yield vals

            # add comment widgets
            vals.row = self._addCommentWidgets(item, vals.plural, vals.row, saveFrame)

            self._colourTables(item, saveFrame, tableColourFunc)

        self.frameOptionsFrame.setVisible(self._enableRename)
        self._finaliseSelection(vals._content, vals._errors)

    def _handleTreeViewParent(self, parentItem=None, parentItemName=None, mappingCode=None, _handleAutoRename=False):
        # this is treated as a generator

        if _handleAutoRename:
            return

        vals = _TreeValues()
        vals.parentItem = parentItem
        vals.parentItemName = parentItemName
        vals.mappingCode = mappingCode or ''
        vals.mapping = self.nefTreeView.nefToTreeViewMapping.get(mappingCode)
        vals.ccpnClassName = nef2CcpnClassNames.get(mappingCode)
        vals.row = 0

        # return the values as a generator - only returns once, skipped if no item
        yield vals

        self.frameOptionsFrame.setVisible(self._enableRename)

    def handleTreeViewParentGeneral(self, parentItem=None, parentItemName=None, mappingCode=None,
                                    _handleAutoRename=False):

        for vals in self._handleTreeViewParent(parentItem, parentItemName, mappingCode, _handleAutoRename):
            self._makeCollectionParentPulldown(vals)
            vals.row += 1

    def handleTreeViewParentGeneralStructureData(self, parentItem=None, parentItemName=None, mappingCode=None,
                                                 _handleAutoRename=False):

        for vals in self._handleTreeViewParent(parentItem, parentItemName, mappingCode, _handleAutoRename):
            self._makeCollectionParentStructureDataPulldown(vals)
            vals.row += 1

    def handleTreeViewSelectionGeneral(self, name=None, saveFrame=None, parentGroup=None, prefix=None, mappingCode=None,
                                       errorCode=None, tableColourFunc=None, _handleAutoRename=False, allowPeriod=True):

        for vals in self._handleTreeView(name, saveFrame, parentGroup, prefix, mappingCode, errorCode, tableColourFunc,
                                         _handleAutoRename):
            vals.row, saveFrameData = self._addRenameWidgets(vals.item,
                                                             vals.itemName,
                                                             vals.plural,
                                                             vals.row,
                                                             saveFrame,
                                                             vals.singular,
                                                             allowPeriod=allowPeriod)
            self._colourRenameWidgets(vals._errors, vals._fillColour, errorCode, vals.itemName, saveFrameData)

            self._makeCollectionPulldown(vals)
            vals.row += 1

    def handleTreeViewSelectionGeneralNoCollection(self, name=None, saveFrame=None, parentGroup=None, prefix=None,
                                                   mappingCode=None,
                                                   errorCode=None, tableColourFunc=None, _handleAutoRename=False,
                                                   allowPeriod=True):

        for vals in self._handleTreeView(name, saveFrame, parentGroup, prefix, mappingCode, errorCode, tableColourFunc,
                                         _handleAutoRename):
            vals.row, saveFrameData = self._addRenameWidgets(vals.item, vals.itemName, vals.plural, vals.row,
                                                             saveFrame, vals.singular, allowPeriod=allowPeriod)
            self._colourRenameWidgets(vals._errors, vals._fillColour, errorCode, vals.itemName, saveFrameData)

    def handleTreeViewSelectionCcpnList(self, name=None, saveFrame=None, parentGroup=None, prefix=None,
                                        mappingCode=None,
                                        errorCode=None, tableColourFunc=None, _handleAutoRename=False):

        for vals in self._handleTreeView(name, saveFrame, parentGroup, prefix, mappingCode, errorCode, tableColourFunc,
                                         _handleAutoRename):
            vals.row, saveFrameData = self._addRenameWidgets(vals.item, vals.itemName, vals.plural, vals.row, saveFrame,
                                                             vals.singular)
            self._colourRenameWidgets(vals._errors, vals._fillColour, errorCode, vals.itemName, saveFrameData)

            self._makeCollectionPulldown(vals)
            vals.row += 1

    def handleTreeViewSelectionAssignment(self, name=None, saveFrame=None, parentGroup=None, prefix=None,
                                          mappingCode=None,
                                          errorCode=None, tableColourFunc=None, _handleAutoRename=False,
                                          allowPeriod=True):

        for vals in self._handleTreeView(name, saveFrame, parentGroup, prefix, mappingCode, errorCode, tableColourFunc,
                                         _handleAutoRename):
            vals.row, saveFrameData = self._addRenameWidgets(vals.item, vals.itemName, vals.plural, vals.row,
                                                             saveFrame, vals.singular, allowPeriod=allowPeriod)
            self._colourRenameWidgets(vals._errors, vals._fillColour, errorCode, vals.itemName, saveFrameData)

            # add widgets to handle assignments
            vals.row = self._addAssignmentWidgets(vals.item, vals.plural, vals.row, saveFrame, saveFrameData)

            self._makeCollectionPulldown(vals)
            vals.row += 1

    def handleTreeViewSelectionStructureDataParent(self, name=None, saveFrame=None, parentGroup=None, prefix=None,
                                                   mappingCode=None,
                                                   errorCode=None, tableColourFunc=None, _handleAutoRename=False):

        for vals in self._handleTreeView(name, saveFrame, parentGroup, prefix, mappingCode, errorCode, tableColourFunc,
                                         _handleAutoRename):
            vals.row, saveFrameData = self._addRenameWidgets(vals.item, vals.itemName, vals.plural, vals.row, saveFrame,
                                                             vals.singular)
            self._colourRenameWidgets(vals._errors, vals._fillColour, errorCode, vals.itemName, saveFrameData)

            # add widgets to handle linking to structureData parent
            vals.row = self._addStructureDataWidgets(vals.item, vals.plural, vals.row, saveFrame)

            self._makeCollectionStructurePulldown(vals)
            vals.row += 1

    def handleTreeViewSelectionStructureDataParentNoCollection(self, name=None, saveFrame=None, parentGroup=None,
                                                               prefix=None, mappingCode=None,
                                                               errorCode=None, tableColourFunc=None,
                                                               _handleAutoRename=False):

        for vals in self._handleTreeView(name, saveFrame, parentGroup, prefix, mappingCode, errorCode, tableColourFunc,
                                         _handleAutoRename):
            vals.row, saveFrameData = self._addRenameWidgets(vals.item, vals.itemName, vals.plural, vals.row, saveFrame,
                                                             vals.singular)
            self._colourRenameWidgets(vals._errors, vals._fillColour, errorCode, vals.itemName, saveFrameData)

            # add widgets to handle linking to structureData parent
            vals.row = self._addStructureDataWidgets(vals.item, vals.plural, vals.row, saveFrame)

    def _addAssignmentWidgets(self, item, plural, row, saveFrame, saveFrameData):

        texts = ('Auto Rename SequenceCodes',)
        callbacks = (
            partial(self._renameSequenceCode, item=item, parentName=plural, lineEdit=saveFrameData, saveFrame=saveFrame,
                    autoRename=True),)
        tipTexts = ('Automatically rename to the next available',)
        ButtonList(self.frameOptionsFrame, texts=texts, tipTexts=tipTexts, callbacks=callbacks,
                   grid=(row, 1), gridSpan=(1, 2), direction='v',
                   setLastButtonFocus=False)
        row += 1

        return row

    def _addStructureDataWidgets(self, item, plural, row, saveFrame):

        self._makeStructureDataPulldown(item, plural, row, saveFrame, DATANAME)
        row += 1

        if saveFrame.get('sf_category') in ['ccpn_parameter', ]:
            self._makeSetButton(item, plural, row, saveFrame, 'ccpn_parameter_name', self._editParameterName)
            row += 1

        return row

    def _finaliseSelection(self, _content, _errors):
        self.logData.clear()
        pretty = PrintFormatter()
        self.logData.append(('CONTENTS DICT'))
        self.logData.append(pretty(_content))
        self.logData.append(('ERROR DICT'))
        self.logData.append(pretty(_errors))

    def _colourTables(self, item, saveFrame, tableColourFunc):
        if tableColourFunc is not None:
            tableColourFunc(self, saveFrame, item)

    def _colourRenameWidgets(self, _errors, _fillColour, errorCode, itemName, saveFrameData):
        if saveFrameData and errorCode in _errors and itemName in _errors[errorCode]:
            try:
                palette = saveFrameData.palette()
                palette.setColor(QtGui.QPalette.Base, _fillColour)
                saveFrameData.setPalette(palette)
                # saveFrameData.setToolTip('HELP!')  # can set a toolTip message here for bad names
            except Exception as es:
                getLogger().debug(f'error setting colours {es}')

    def _addCommentWidgets(self, item, plural, row, saveFrame):
        Label(self.frameOptionsFrame, text='Comment', grid=(row, 0), enabled=False)
        self._commentData = TextEditor(self.frameOptionsFrame, grid=(row, 1), gridSpan=(1, 2), enabled=True,
                                       addWordWrap=True)
        _comment = saveFrame.get('ccpn_comment')
        if _comment:
            self._commentData.set(_comment)
        self._commentData.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)
        self._commentData.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        _height = getFontHeight()
        self._commentData.setMinimumHeight(_height * 3)
        row += 1
        texts = ('Set Comment',)
        callbacks = (
            partial(self._editComment, item=item, parentName=plural, lineEdit=self._commentData, saveFrame=saveFrame),)
        tipTexts = ('Set the comment for the saveFrame',)
        ButtonList(self.frameOptionsFrame, texts=texts, tipTexts=tipTexts, callbacks=callbacks,
                   grid=(row, 2), gridSpan=(1, 1), direction='v',
                   setLastButtonFocus=False)
        row += 1
        return row

    def _addRenameWidgets(self, item, itemName, plural, row, saveFrame, singular, allowPeriod=True):
        saveFrameData = None
        if self._renameValid(item=item, saveFrame=saveFrame):
            Label(self.frameOptionsFrame, text=singular, grid=(row, 0))
            saveFrameData = LineEdit(self.frameOptionsFrame, text=str(itemName), grid=(row, 1), gridSpan=(1, 2))
            row += 1

            # texts = ('Rename', 'Auto Rename')
            # callbacks = (partial(self._rename, item=item, parentName=plural, lineEdit=saveFrameData, saveFrame=saveFrame),
            #              partial(self._rename, item=item, parentName=plural, lineEdit=saveFrameData, saveFrame=saveFrame, autoRename=True))
            # tipTexts = ('Rename', 'Automatically rename to the next available\n - dependent on saveframe type')
            # ButtonList(self.frameOptionsFrame, texts=texts, tipTexts=tipTexts, callbacks=callbacks,
            #            grid=(row, 2), gridSpan=(1, 1), direction='v',
            #            setLastButtonFocus=False)

            texts = ('Auto Rename')
            _renameCallback = partial(self._rename, item=item, parentName=plural, lineEdit=saveFrameData,
                                      saveFrame=saveFrame)
            _autoRenameCallback = partial(self._rename, item=item, parentName=plural, lineEdit=saveFrameData,
                                          saveFrame=saveFrame, autoRename=True)
            tipText = 'Automatically rename to the next available\n - dependent on saveframe type'
            Button(self.frameOptionsFrame, text=texts, tipText=tipText, callback=_autoRenameCallback,
                   grid=(row, 2), gridSpan=(1, 1))

            _validator = LineEditValidatorWhiteSpace(parent=saveFrameData, allowSpace=False, allowEmpty=False,
                                                     allowPeriod=allowPeriod)
            saveFrameData.setValidator(_validator)
            saveFrameData.returnPressed.connect(_renameCallback)
            row += 1

        return row, saveFrameData

    def _handleItemRename(self, item, mappingCode, saveFrame):
        mappingCode = mappingCode or ''
        mapping = self.nefTreeView.nefToTreeViewMapping.get(mappingCode)
        if mapping:
            plural, singular = mapping
            _auto = partial(self._rename, item=item, parentName=plural, lineEdit=None, saveFrame=saveFrame,
                            autoRename=True)
            _auto()

    def _makeSetButton(self, item, plural, row, saveFrame, attribName, func):
        Label(self.frameOptionsFrame, text=attribName, grid=(row, 0))

        # extract the ccpn_parameter_name
        _attrib = saveFrame.get(attribName)
        dataSetData = LineEdit(self.frameOptionsFrame, text=str(_attrib), grid=(row, 1), gridSpan=(1, 2))
        row += 1

        texts = ('Set',)
        callbacks = (partial(func, item=item, parentName=plural, lineEdit=dataSetData, saveFrame=saveFrame),)
        tipTexts = (f'Set the {attribName} for the saveFrame',)
        ButtonList(self.frameOptionsFrame, texts=texts, tipTexts=tipTexts, callbacks=callbacks,
                   grid=(row, 2), gridSpan=(1, 1), direction='v',
                   setLastButtonFocus=False)
        dataSetData.returnPressed.connect(callbacks[0])

    def _makeStructureDataPulldown(self, item, plural, row, saveFrame, attribName):

        if not (_data := item.data(1, 0)):
            return
        _itmName, _, _itmParentName, _, _ = _data
        Label(self.frameOptionsFrame, text=STRUCTUREDATA, grid=(row, 0))

        structurePulldown = self._newPulldown(self.frameOptionsFrame, name=STRUCTUREDATA,
                                              grid=(row, 1), gridSpan=(1, 2), allowEmpty=False)

        callbackSelect = partial(self._selectStructureDataId, item=item, itemName=_itmName,
                                 itemParentName=_itmParentName, parentName=plural,
                                 pulldownList=structurePulldown, saveFrame=saveFrame)
        structurePulldown.activated.connect(callbackSelect)

        self._populateStructureDataPulldown([_data], structurePulldown)

    def _makeCollectionPulldown(self, values):

        if not (_data := values.item.data(1, 0)):
            return
        _itmName, _, _itmParentName, _, _ = _data
        Label(self.frameOptionsFrame, text=COLLECTION, grid=(values.row, 0))

        # map the className to a pid for the collection
        _itmName = '' if _itmName in ['.', None] else _itmName
        _itmPid = Pid._join(values.ccpnClassName, _itmName) if values.ccpnClassName else _itmName
        values.itemPid = _itmPid

        collectionPulldown = self._newPulldown(self.frameOptionsFrame,
                                               grid=(values.row, 1), gridSpan=(1, 2))

        callbackSelect = partial(self._selectCollectionId, values=values, pulldownList=collectionPulldown,
                                 saveFrame=values.saveFrame)
        collectionPulldown.activated.connect(callbackSelect)

        self._populateCollectionStructurePulldown([_data], collectionPulldown)

    def _makeCollectionParentPulldown(self, values):

        Label(self.frameOptionsFrame, text=COLLECTION_ATTRIB, grid=(values.row, 0))
        collectionPulldown = self._newPulldown(self.frameOptionsFrame,
                                               grid=(values.row, 1), gridSpan=(1, 2))

        callbackSelect = partial(self._selectCollectionParentId, values=values, pulldownList=collectionPulldown,
                                 parent=self.nefTreeView)
        collectionPulldown.activated.connect(callbackSelect)

        _children = self._getSelectedChildren(self.nefTreeView)
        self._populateCollectionStructurePulldown(_children, collectionPulldown)

        self._updateTables()

    @staticmethod
    def _getSelectedChildren(parent):
        selection = parent.selectionModel().selectedIndexes()
        newItms = [parent.itemFromIndex(itm) for itm in selection]
        values = [itm.data(1, 0) for itm in newItms if itm.data(1, 0)]

        return values

    @staticmethod
    def _getSelectedChildItems(parent):
        selection = parent.selectionModel().selectedIndexes()
        newItms = [parent.itemFromIndex(itm) for itm in selection]
        values = [(itm, itm.data(1, 0)) for itm in newItms if itm.data(1, 0)]

        return values

    def _getAllChildren(self):
        # grab the tree state
        items = []
        self._traverseTree(self.nefTreeView.headerItem, self._getAllItemState, items)

        return items

    def _populateCollectionPulldown(self, _children, collectionPulldown):

        colData = self.project.collections
        colNames = OrderedSet([''] + [co.name for co in colData])

        # read the collections not defined in the project
        for col in self._collections.keys():
            colNames.add(col)
            self._collections.setdefault(col, [])

        # get the list of common collections for the selection, to set the pulldown
        _indexing = set()
        for (itmName, sFrame, parentGroup, primaryHandler, ccpnClassName) in _children:
            _itmPid = Pid._join(ccpnClassName, itmName) if ccpnClassName else itmName
            _count = 0
            for k, v in self._collections.items():
                if _itmPid in v:
                    _indexing.add(list(colNames).index(k))
                    _count += 1
            if not _count:
                _indexing.add(list(colNames).index(''))

        collectionPulldown.setData(list(colNames))
        if len(_indexing) == 1:
            collectionPulldown.setIndex(list(_indexing)[0])
        else:
            collectionPulldown.setIndex(0)

    def _populateCollectionStructurePulldown(self, _children, collectionPulldown):

        colData = self.project.collections
        colNames = OrderedSet([''] + [co.name for co in colData])

        # read the collections not defined in the project
        for col in self._collections.keys():
            colNames.add(col)
            self._collections.setdefault(col, [])

        # get the list of common collections for the selection, to set the pulldown
        _indexing = set()
        for (itmName, sFrame, parentGroup, primaryHandler, ccpnClassName) in _children:

            itmName = '' if itmName in ['.', None] else itmName

            if parentGroup in ['restraintTables', 'violationTables']:
                _itmStructureData = sFrame.get(DATANAME) or ''  # make sure isn't None
                _itmPid = Pid._join(ccpnClassName, _itmStructureData, itmName) if ccpnClassName else itmName
            else:
                _itmPid = Pid._join(ccpnClassName, itmName) if ccpnClassName else itmName

            _count = 0
            for k, v in self._collections.items():
                if _itmPid in v:
                    _indexing.add(list(colNames).index(k))
                    _count += 1
            if not _count:
                _indexing.add(list(colNames).index(''))

        collectionPulldown.setData(list(colNames))
        if len(_indexing) == 1:
            collectionPulldown.setIndex(list(_indexing)[0])
        else:
            collectionPulldown.setIndex(0)

    def _populateStructureDataPulldown(self, _children, structurePulldown):

        # get the structureData names from the project
        sData = self.project.structureData
        sdIds = OrderedSet([''] + [sd.id for sd in sData])

        # search through the saveframes for occurrences of DATANAME - add to choices
        _sfNames = self._nefLoader.getSaveFrameNames()
        for sf in _sfNames:
            sFrame = self._nefLoader.getSaveFrame(sf)
            if sFrame is not None and sFrame._nefFrame and DATANAME in sFrame._nefFrame:
                if (_id := sFrame._nefFrame.get(DATANAME)):
                    sdIds.add(_id)

        # get the list of common structureData for the selection, to set the pulldown
        _indexing = set()
        for (itmName, saveFrame, _, _, _) in _children:
            _itmPid = saveFrame.get(DATANAME)
            if _itmPid in sdIds:
                _indexing.add(list(sdIds).index(_itmPid))

        structurePulldown.setData(list(sdIds))
        if len(_indexing) == 1:
            structurePulldown.setIndex(list(_indexing)[0])
        else:
            structurePulldown.setIndex(0)

    def _makeCollectionParentStructureDataPulldown(self, values):

        Label(self.frameOptionsFrame, text=STRUCTUREDATA, grid=(values.row, 0))
        structurePulldown = self._newPulldown(self.frameOptionsFrame, name=STRUCTUREDATA,
                                              grid=(values.row, 1), gridSpan=(1, 2), allowEmpty=False)

        values.row += 1
        callbackSelect = partial(self._selectStructureDataParentId, values=values, pulldownList=structurePulldown,
                                 parent=self.nefTreeView)
        structurePulldown.activated.connect(callbackSelect)

        #~~~~~~~~~~~~~~~~~

        Label(self.frameOptionsFrame, text=COLLECTION, grid=(values.row, 0))
        collectionPulldown = self._newPulldown(self.frameOptionsFrame,
                                               grid=(values.row, 1), gridSpan=(1, 2))

        callbackSelect = partial(self._selectCollectionParentStructureId, values=values,
                                 pulldownList=collectionPulldown, parent=self.nefTreeView)
        collectionPulldown.activated.connect(callbackSelect)

        _children = self._getSelectedChildren(self.nefTreeView)
        self._populateStructureDataPulldown(_children, structurePulldown)
        self._populateCollectionStructurePulldown(_children, collectionPulldown)

        self._updateTables()

    def _makeCollectionStructurePulldown(self, values):

        Label(self.frameOptionsFrame, text=COLLECTION, grid=(values.row, 0))

        # extract the ccpn_parameter_name
        _att = str(values.saveFrame.get(COLLECTION_ATTRIB) or '')

        if not (_data := values.item.data(1, 0)):
            return
        _itmName, _, _itmParentName, _, _ = _data

        colData = self.project.collections
        colNames = OrderedSet([''] + [co.name for co in colData])

        # read the collections not defined in the project
        for col in self._collections.keys():
            colNames.add(col)

        # use the saveFrame loop to store?
        _itmStructureData = values.saveFrame.get(DATANAME) or ''  # make sure isn't None
        _itmPid = Pid._join(values.ccpnClassName, _itmStructureData, _itmName) if values.ccpnClassName else _itmName
        values.itemPid = _itmPid

        _indexing = set()
        # need a saveFrame name to ccpn pid mapping
        for k, v in self._collections.items():
            if _itmPid in v:
                _indexing.add(list(colNames).index(k))

        # also need list of all dataset_id in nef
        collectionPulldown = self._newPulldown(self.frameOptionsFrame,
                                               index=list(_indexing)[0] if len(_indexing) == 1 else 0,
                                               texts=list(colNames),
                                               grid=(values.row, 1), gridSpan=(1, 2))

        callbackSelect = partial(self._selectCollectionId, values=values, pulldownList=collectionPulldown,
                                 saveFrame=values.saveFrame)
        collectionPulldown.activated.connect(callbackSelect)

    def _renameInCollections(self, item, data, newName):
        """rename items in the collections for import
        """
        import re

        itmName, sFrame, parentGroup, primaryHandler, ccpnClassName = data

        exact = True
        if parentGroup in ['restraintTables', 'violationTables']:
            _itmStructureData = sFrame.get(DATANAME) or ''  # make sure isn't None
            _itmPids = [Pid._join(ccpnClassName, _itmStructureData, itmName) if ccpnClassName else itmName]
            _newPids = [Pid._join(ccpnClassName, _itmStructureData, newName) if ccpnClassName else newName]
        elif parentGroup in ['peakLists', 'integralLists', 'multipletLists']:
            spec, _ = itmName.split(IDSEP)
            newSpec, _ = newName.split(IDSEP)
            _itmPids = [Pid._join(cn, spec) for cn in ['SP', 'PL', 'IL', 'ML']]
            _newPids = [Pid._join(cn, newSpec) for cn in ['SP', 'PL', 'IL', 'ML']]
            exact = False

        else:
            _itmPids = [Pid._join(ccpnClassName, itmName) if ccpnClassName else itmName]
            _newPids = [Pid._join(ccpnClassName, newName) if ccpnClassName else newName]

        # remove from previous self._collections
        for k, pids in list(self._collections.items()):
            for itm, newItm in zip(_itmPids, _newPids):
                if exact:
                    # match the pid exactly
                    if itm in pids:
                        pids.insert(pids.index(itm), newItm)
                        pids.remove(itm)

                else:
                    # should be a spectrum-based name
                    for pid in list(pids):
                        # match by pid, or pid.<n>
                        if (newVal := re.sub(f'({itm})([.]\d+)$', f'{newItm}\g<2>', pid)) != pid:
                            pids.insert(pids.index(pid), newVal)
                            pids.remove(pid)

                if not pids:
                    # remove any empty collections
                    self._collections.pop(k)

    def _renameValid(self, item=None, saveFrame=None):
        if not item:
            return

        if not (_data := item.data(1, 0)):
            return
        itemName, sFrame, parentGroup, primaryHandler, ccpnClassName = _data

        func = self._nefReader.renames.get(primaryHandler)

        return func

    def _rename(self, item=None, parentName=None, lineEdit=None, saveFrame=None, autoRename=False):
        """Handle clicking a rename button
        """
        if not item:
            return

        if not (_data := item.data(1, 0)):
            return
        itemName, sFrame, parentGroup, primaryHandler, ccpnClassName = _data

        func = self._nefReader.renames.get(primaryHandler)
        if func is not None:

            # take from lineEdit if exists, otherwise assume auto-rename (for the minute)
            newName = lineEdit.get() if lineEdit else None

            # with busyHandler(title='Busy...', text=f'Renaming {parentGroup[:-1] if parentGroup.endswith("s") else parentGroup}: {itemName}'):
            dd = {}
            # grab the tree state
            self._traverseTree(self.nefTreeView.headerItem, self._getTreeState, dd)

            try:
                # call the correct rename function based on the item clicked
                newName = func(self._nefReader, self.project,
                               self._nefDict, self._contentCompareDataBlocks,
                               saveFrame,
                               itemName=itemName, newName=None if autoRename else newName)

            except Exception as es:
                showWarning('Rename SaveFrame', str(es))
            else:

                if itemName:
                    # rename in the nef collections - empty named objects should not be in collections
                    self._renameInCollections(item, _data, newName)

                # everything okay - rebuild all for now, could make selective later
                self._repopulateview(itemName, newName, parentName)

                # restore the tree state
                self._traverseTree(self.nefTreeView.headerItem, self._setTreeState, dd)
                self._setCheckedItem(newName, parentGroup)

    def _renameSequenceCode(self, item=None, parentName=None, lineEdit=None, saveFrame=None, autoRename=False):
        """Handle clicking a rename button
        """
        if not item:
            return

        if not (_data := item.data(1, 0)):
            return
        itemName, sFrame, parentGroup, primaryHandler, ccpnClassName = _data

        func = self._nefReader.renames.get('nmr_sequence_code')
        if func is not None:

            dd = {}
            # grab the tree state
            self._traverseTree(self.nefTreeView.headerItem, self._getTreeState, dd)

            # take from lineEdit if exists, otherwise assume autorename (for the minute)
            newName = lineEdit.get() if lineEdit else None
            try:
                # call the correct rename function based on the item clicked
                newName = func(self._nefReader, self.project,
                               self._nefDict, self._contentCompareDataBlocks,
                               saveFrame,
                               itemName=itemName, newName=newName if not autoRename else None)
            except Exception as es:
                showWarning('Rename Sequence SaveFrame', str(es))
            else:

                # everything okay - rebuild all for now, could make selective later
                self._repopulateview(itemName, newName, parentName)

                # restore the tree state
                self._traverseTree(self.nefTreeView.headerItem, self._setTreeState, dd)
                self._setCheckedItem(newName, parentGroup)

    @contextmanager
    def _editSaveFrameItem(self, item=None, parentName=None, lineEdit=None, saveFrame=None, autoRename=False,
                           parameter=None):
        """Handler for editing values in main saveFrame
        """
        if not item:
            return

        newEdit = _TreeValues()
        newEdit.itemName, _, newEdit.parentGroup, _, _ = item.data(1, 0)
        newEdit.newVal = lineEdit.get() if lineEdit else None

        dd = {}
        # grab the tree state
        self._traverseTree(self.nefTreeView.headerItem, self._getTreeState, dd)

        # add item to saveframe
        try:
            yield newEdit

        except Exception as es:
            showWarning(f'Error editing {parameter}', str(es))
        else:
            # everything okay - rebuild all for now, could make selective later
            self._repopulateview(newEdit.itemName, None, parentName)

            # restore the tree state
            self._traverseTree(self.nefTreeView.headerItem, self._setTreeState, dd)
            self._setCheckedItem(newEdit.itemName, newEdit.parentGroup)

    @contextmanager
    def _editSaveFramePulldown(self, itemName=None, itemParentName=None, parentName=None, pulldownList=None,
                               saveFrame=None, autoRename=False, parameter=None):
        """Handler for editing values in main saveFrame
        """
        if not itemName:
            return

        newEdit = _TreeValues()
        newEdit.itemName = itemName
        newEdit.parentGroup = itemParentName
        newEdit.newVal = pulldownList.getText() if pulldownList else None

        dd = {}
        # grab the tree state
        self._traverseTree(self.nefTreeView.headerItem, self._getTreeState, dd)

        # add item to saveframe
        try:
            yield newEdit

        except Exception as es:
            showWarning(f'Error editing {parameter}', str(es))
        else:
            # everything okay - rebuild all for now, could make selective later
            self._repopulateview(newEdit.itemName, None, parentName)

            # restore the tree state
            self._traverseTree(self.nefTreeView.headerItem, self._setTreeState, dd)
            self._setCheckedItem(newEdit.itemName, newEdit.parentGroup)

    def _selectStructureDataId(self, item=None, itemName=None, itemParentName=None, parentName=None,
                               pulldownList=None, saveFrame=None, autoRename=False):
        """Handle clicking rename structureData button
        """

        with self._editSaveFramePulldown(itemName, itemParentName, parentName, pulldownList, saveFrame, autoRename,
                                         DATANAME) as _edit:
            # reads a non-empty string for a value
            if not _edit.newVal and DATANAME in saveFrame:
                if saveFrame.get('sf_category') in ['ccpn_parameter', ]:
                    raise ValueError(f'{DATANAME} cannot be empty')
                else:
                    if self._checkAlreadyInStructureData(None, item, itemName):
                        return
                    del saveFrame[DATANAME]

            else:
                _oldName = saveFrame.get(DATANAME) or ''
                _newName = str(_edit.newVal)
                if self._checkAlreadyInStructureData(_newName, item, itemName):
                    return
                saveFrame[DATANAME] = str(_edit.newVal)

                # rename itemName if a ccpn_parameter
                if saveFrame.get('sf_category') in ['ccpn_parameter', ]:
                    if _edit.itemName and _oldName and _edit.itemName.startswith(_oldName):
                        _edit.itemName = _edit.newVal + _edit.itemName[len(_oldName):]

                for k, v in self._collections.items():
                    if v:
                        ll = []
                        for val in v:
                            ll.append(val.replace(':' + _oldName + '.', ':' + _edit.newVal + '.'))
                        self._collections[k] = ll

        self._setCheckedItem(itemName, itemParentName)
        self._updateTables()

    def _checkAlreadyInStructureData(self, _newName, item, itemName):
        if _newName in self._structureData:
            _, _, _, _, ccpnClassName = item.data(1, 0)
            _itmPid = Pid._join(ccpnClassName, _newName or '', itemName)
            if (_itmPid in self._structureData[_newName]):
                showWarning('Selecting StructureData', f"'{itemName}' already exists in '{_newName}'")
                return True

    def _selectStructureDataParentId(self, values=None, pulldownList=None, parent=None):
        """Handle clicking rename structureData button
        """

        if not (pulldownList and pulldownList.hasFocus()):
            return

        newName = pulldownList.getText() or None
        if not newName:
            return

        _children = self._getSelectedChildItems(parent)
        for itm, (itmName, saveFrame, parentGroup, _pHandler, _ccpnClassName) in _children:

            if parentGroup in ['restraintTables', 'violationTables']:
                _oldName = saveFrame.get(DATANAME) or ''
                if self._checkAlreadyInStructureData(newName, itm, itmName):
                    continue
                saveFrame[DATANAME] = newName

                # TODO:ED - check this
                # if saveFrame.get('sf_category') in ['ccpn_parameter', ]:
                #     if _edit.itemName and _oldName and _edit.itemName.startswith(_oldName):
                #         _edit.itemName = _edit.newVal + _edit.itemName[len(_oldName):]

                for k, v in self._collections.items():
                    if v:
                        ll = []
                        for val in v:
                            ll.append(val.replace(':' + _oldName + '.', ':' + newName + '.'))
                        self._collections[k] = ll

                self._setCheckedItem(itmName, parentGroup)

        self._updateTables()

    def _selectStructureDataGroup(self, values=None, pulldownList=None, parent=None):
        """Handle clicking rename structureData button
        """

        if not (pulldownList and pulldownList.hasFocus()):
            return

        newName = pulldownList.getText() or None
        if not newName:
            return

        _children = self._getSelectedChildItems(parent)
        for itm, (itmName, saveFrame, parentGroup, _pHandler, _ccpnClassName) in _children:

            if parentGroup in ['restraintTables', 'violationTables']:
                _oldName = saveFrame.get(DATANAME) or ''
                if self._checkAlreadyInStructureData(newName, itm, itmName):
                    continue
                saveFrame[DATANAME] = newName

                # TODO:ED - check this

                # if saveFrame.get('sf_category') in ['ccpn_parameter', ]:
                #     if _edit.itemName and _oldName and _edit.itemName.startswith(_oldName):
                #         _edit.itemName = _edit.newVal + _edit.itemName[len(_oldName):]

                for k, v in self._collections.items():
                    if v:
                        ll = []
                        for val in v:
                            ll.append(val.replace(':' + _oldName + '.', ':' + newName + '.'))
                        self._collections[k] = ll

                self._setCheckedItem(itmName, parentGroup)

        self._updateTables()

    def _selectCollectionId(self, values=None, pulldownList=None, saveFrame=None):
        """Handle collection pulldown
        """
        # print(f'   CALL    _selectCollectionId')

        if not (pulldownList and pulldownList.hasFocus()):
            return

        newCol = pulldownList.getText()

        # remove from previous self._collections
        for k, v in list(self._collections.items()):
            if values.itemPid in v:
                v.remove(values.itemPid)
            if not v:
                self._collections.pop(k)

        if newCol:
            self._collections.setdefault(newCol, [])
            self._collections[newCol].append(values.itemPid)

        self._updateTables()
        self._setCheckedItem(values.itemName, values.parentGroup)

    def _selectCollectionParentId(self, values=None, pulldownList=None, parent=None):
        """Handle collection pulldown
        """

        if not (pulldownList and pulldownList.hasFocus()):
            return

        newCol = pulldownList.getText()

        _children = self._getSelectedChildren(parent)
        for (itmName, saveFrame, parentGroup, _pHandler, _ccpnClassName) in _children:
            _itmPid = Pid._join(_ccpnClassName, itmName) if _ccpnClassName else itmName

            # remove from previous self._collections
            for k, v in list(self._collections.items()):
                if _itmPid in v:
                    v.remove(_itmPid)
                if not v:
                    self._collections.pop(k)

            if newCol:
                self._collections.setdefault(newCol, [])
                self._collections[newCol].append(_itmPid)

            self._setCheckedItem(itmName, parentGroup)

        self._updateTables()

    def _selectCollectionParentStructureId(self, values=None, pulldownList=None, parent=None):
        """Handle collection pulldown
        """

        if not (pulldownList and pulldownList.hasFocus()):
            return

        newCol = pulldownList.getText()

        _children = self._getSelectedChildren(parent)
        for (itmName, saveFrame, parentGroup, _pHandler, _ccpnClassName) in _children:

            _itmStructureData = saveFrame.get(DATANAME) or ''  # make sure isn't None
            _itmPid = Pid._join(_ccpnClassName, _itmStructureData, itmName) if _ccpnClassName else itmName

            # remove from previous self._collections
            for k, v in list(self._collections.items()):
                if _itmPid in v:
                    v.remove(_itmPid)
                if not v:
                    self._collections.pop(k)

            if newCol:
                self._collections.setdefault(newCol, [])
                self._collections[newCol].append(_itmPid)

            self._setCheckedItem(itmName, parentGroup)

        self._updateTables()

    def _selectCollectionStructureGroup(self, values=None, pulldownList=None, parent=None):
        """Handle collection pulldown
        """

        if not (pulldownList and pulldownList.hasFocus()):
            return

        newCol = pulldownList.getText()

        _children = self._getSelectedChildren(parent)
        for (itmName, saveFrame, parentGroup, _pHandler, _ccpnClassName) in _children:

            if parentGroup in ['restraintTables', 'violationTables']:
                _itmStructureData = saveFrame.get(DATANAME) or ''  # make sure isn't None
                _itmPid = Pid._join(_ccpnClassName, _itmStructureData, itmName) if _ccpnClassName else itmName
            else:
                _itmPid = Pid._join(_ccpnClassName, itmName) if _ccpnClassName else itmName

            # remove from previous self._collections
            for k, v in list(self._collections.items()):
                if _itmPid in v:
                    v.remove(_itmPid)
                if not v:
                    self._collections.pop(k)

            if newCol:
                self._collections.setdefault(newCol, [])
                self._collections[newCol].append(_itmPid)

            self._setCheckedItem(itmName, parentGroup)

        self._updateTables()

    def _editComment(self, item=None, parentName=None, lineEdit=None, saveFrame=None, autoRename=False):
        """Handle clicking Set Comment button
        """
        with self._editSaveFrameItem(item, parentName, lineEdit, saveFrame, autoRename, 'ccpn_comment') as _edit:
            # reads a non-empty string for a value
            if not _edit.newVal and 'ccpn_comment' in saveFrame:
                del saveFrame['ccpn_comment']
            else:
                saveFrame['ccpn_comment'] = str(_edit.newVal)

    def _editParameterName(self, item=None, parentName=None, lineEdit=None, saveFrame=None, autoRename=False):
        """Handle clicking Set Parameter Name button
        """
        with self._editSaveFrameItem(item, parentName, lineEdit, saveFrame, autoRename, 'ccpn_parameter_name') as _edit:
            # reads a non-empty string for a value
            if not _edit.newVal and 'ccpn_parameter_name' in saveFrame:
                raise ValueError('ccpn_parameter_name cannot be empty')
            else:
                _oldName = saveFrame.get('ccpn_parameter_name')
                saveFrame['ccpn_parameter_name'] = str(_edit.newVal)

                if saveFrame.get('sf_category') in ['ccpn_parameter', ]:
                    if _edit.itemName and _oldName and _edit.itemName.endswith(_oldName):
                        _edit.itemName = _edit.itemName[:-len(_oldName)] + _edit.newVal

    def _repopulateview(self, itemName, newName, parentName):

        self.nefTreeView._populateTreeView(self.project)
        self._fillPopup(self._nefDict)

        _parent = self.nefTreeView.findSection(parentName)
        if _parent:
            # should be a single item
            if (newItem := self.nefTreeView.findSection(newName or itemName, _parent)):
                newItem = newItem[0] if isinstance(newItem, list) else newItem
                self._nefTreeClickedCallback(newItem, 0)

    def _setCheckedItem(self, itemName, parentName):

        if (_parent := self.nefTreeView.findSection(parentName)):
            _parent = _parent[0] if isinstance(_parent, list) else _parent

            # should be a single item
            itm = self.nefTreeView.findSection(itemName, _parent)
            if itm:
                itm = itm[0] if isinstance(itm, list) else itm
                itm.setCheckState(0, QtCore.Qt.Checked)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    handleParentGroups = {'chains'               : partial(handleTreeViewParentGeneral,
                                                           mappingCode='nef_sequence_chain_code'),
                          'chemicalShiftLists'   : partial(handleTreeViewParentGeneral,
                                                           mappingCode='nef_chemical_shift_list'),
                          'restraintTables'      : partial(handleTreeViewParentGeneralStructureData,
                                                           mappingCode='nef_distance_restraint_list'),
                          'peakLists'            : partial(handleTreeViewParentGeneral, mappingCode='nef_peak'),
                          'integralLists'        : partial(handleTreeViewParentGeneral,
                                                           mappingCode='ccpn_integral_list'),
                          'multipletLists'       : partial(handleTreeViewParentGeneral,
                                                           mappingCode='ccpn_multiplet_list'),
                          'samples'              : partial(handleTreeViewParentGeneral, mappingCode='ccpn_sample'),
                          'substances'           : partial(handleTreeViewParentGeneral, mappingCode='ccpn_substance'),
                          'nmrChains'            : partial(handleTreeViewParentGeneral, mappingCode='nmr_chain'),
                          'structureData'        : partial(handleTreeViewParentGeneral, mappingCode='ccpn_dataset'),
                          'complexes'            : partial(handleTreeViewParentGeneral, mappingCode='ccpn_complex'),
                          'spectrumGroups'       : partial(handleTreeViewParentGeneral,
                                                           mappingCode='ccpn_spectrum_group'),
                          'notes'                : partial(handleTreeViewParentGeneral, mappingCode='ccpn_notes'),
                          # 'peakClusters'         : partial(handleTreeViewParentGeneral, mappingCode='ccpn_peak_cluster_list'),
                          'restraintLinks'       : None,
                          'violationTables'      : partial(handleTreeViewParentGeneralStructureData,
                                                           mappingCode='ccpn_distance_restraint_violation_list'),
                          'dataTables'           : partial(handleTreeViewParentGeneral, mappingCode='ccpn_datatable'),
                          'additionalData'       : None,
                          'ccpnDataSetParameters': None,
                          'ccpnLogging'          : None,
                          }

    handleSaveFrames['nef_sequence'] = partial(handleTreeViewSelectionGeneral,
                                               prefix='nef_sequence_',
                                               mappingCode='nef_sequence_chain_code',
                                               errorCode='nef_sequence_chain_code',
                                               tableColourFunc=table_nef_molecular_system,
                                               allowPeriod=False)

    handleSaveFrames['nef_chemical_shift_list'] = partial(handleTreeViewSelectionGeneral,
                                                          prefix='nef_chemical_shift_',
                                                          mappingCode='nef_chemical_shift_list',
                                                          errorCode='nef_chemical_shift_list',
                                                          tableColourFunc=None,
                                                          allowPeriod=False)

    handleSaveFrames['nef_distance_restraint_list'] = partial(handleTreeViewSelectionStructureDataParent,
                                                              prefix='nef_distance_restraint_',
                                                              mappingCode='nef_distance_restraint_list',
                                                              errorCode='nef_distance_restraint_list',
                                                              tableColourFunc=None)

    handleSaveFrames['nef_dihedral_restraint_list'] = partial(handleTreeViewSelectionStructureDataParent,
                                                              prefix='nef_dihedral_restraint_',
                                                              mappingCode='nef_dihedral_restraint_list',
                                                              errorCode='nef_dihedral_restraint_list',
                                                              tableColourFunc=None)

    handleSaveFrames['nef_rdc_restraint_list'] = partial(handleTreeViewSelectionStructureDataParent,
                                                         prefix='nef_rdc_restraint_',
                                                         mappingCode='nef_rdc_restraint_list',
                                                         errorCode='nef_rdc_restraint_list',
                                                         tableColourFunc=None)

    handleSaveFrames['ccpn_restraint_list'] = partial(handleTreeViewSelectionGeneral,
                                                      prefix='ccpn_restraint_',
                                                      mappingCode='ccpn_restraint_list',
                                                      errorCode='ccpn_restraint_list',
                                                      tableColourFunc=None)

    handleSaveFrames['nef_peak_restraint_links'] = partial(handleTreeViewSelectionGeneralNoCollection,
                                                           prefix='nef_peak_restraint_',
                                                           mappingCode='nef_peak_restraint_links',
                                                           errorCode='nef_peak_restraint_links',
                                                           tableColourFunc=None)

    handleSaveFrames['ccpn_sample'] = partial(handleTreeViewSelectionGeneral,
                                              prefix='ccpn_sample_component_',
                                              mappingCode='ccpn_sample',
                                              errorCode='ccpn_sample',
                                              tableColourFunc=None,
                                              allowPeriod=False)

    handleSaveFrames['ccpn_complex'] = partial(handleTreeViewSelectionGeneral,
                                               prefix='ccpn_complex_chain_',
                                               mappingCode='ccpn_complex',
                                               errorCode='ccpn_complex',
                                               tableColourFunc=None,
                                               allowPeriod=False)

    handleSaveFrames['ccpn_spectrum_group'] = partial(handleTreeViewSelectionGeneral,
                                                      prefix='ccpn_group_spectrum_',
                                                      mappingCode='ccpn_spectrum_group',
                                                      errorCode='ccpn_spectrum_group',
                                                      tableColourFunc=None)

    handleSaveFrames['ccpn_note'] = partial(handleTreeViewSelectionGeneral,
                                            prefix='ccpn_note_',
                                            mappingCode='ccpn_notes',
                                            errorCode='ccpn_notes',
                                            tableColourFunc=table_ccpn_notes,
                                            allowPeriod=False)

    handleSaveFrames['ccpn_peak_list'] = partial(handleTreeViewSelectionCcpnList,
                                                 prefix='nef_peak_',
                                                 mappingCode='nef_peak',
                                                 errorCode='ccpn_peak_list_serial',
                                                 tableColourFunc=table_peak_lists)

    handleSaveFrames['ccpn_integral_list'] = partial(handleTreeViewSelectionCcpnList,
                                                     prefix='ccpn_integral_',
                                                     mappingCode='ccpn_integral_list',
                                                     errorCode='ccpn_integral_list_serial',
                                                     tableColourFunc=partial(table_lists, listName='ccpn_integral'))

    handleSaveFrames['ccpn_multiplet_list'] = partial(handleTreeViewSelectionCcpnList,
                                                      prefix='ccpn_multiplet_',
                                                      mappingCode='ccpn_multiplet_list',
                                                      errorCode='ccpn_multiplet_list_serial',
                                                      tableColourFunc=partial(table_lists, listName='ccpn_multiplet'))

    # handleSaveFrames['ccpn_peak_cluster_list'] = partial(handleTreeViewSelectionGeneralNoCollection,
    #                                                      prefix='ccpn_peak_cluster_',
    #                                                      mappingCode='ccpn_peak_cluster',
    #                                                      errorCode='ccpn_peak_cluster_serial',
    #                                                      tableColourFunc=table_peak_clusters)

    handleSaveFrames['nmr_chain'] = partial(handleTreeViewSelectionAssignment,
                                            prefix='nmr_chain_',
                                            mappingCode='nmr_chain',
                                            errorCode='nmr_chain_serial',
                                            tableColourFunc=table_ccpn_assignment,
                                            allowPeriod=False)

    handleSaveFrames['ccpn_substance'] = partial(handleTreeViewSelectionGeneral,
                                                 prefix='ccpn_substance_synonym_',
                                                 mappingCode='ccpn_substance',
                                                 errorCode='ccpn_substance',
                                                 tableColourFunc=None)

    handleSaveFrames['ccpn_internal_data'] = partial(handleTreeViewSelectionGeneralNoCollection,
                                                     prefix='ccpn_internal_data_',
                                                     mappingCode='ccpn_additional_data',
                                                     errorCode='ccpn_additional_data',
                                                     # tableColourFunc=table_ccpn_additional_data)
                                                     tableColourFunc=None)

    handleSaveFrames['ccpn_distance_restraint_violation_list'] = partial(handleTreeViewSelectionStructureDataParent,
                                                                         prefix='ccpn_distance_restraint_violation_',
                                                                         mappingCode='ccpn_distance_restraint_violation_list',
                                                                         errorCode='ccpn_distance_restraint_violation_list',
                                                                         tableColourFunc=None)

    handleSaveFrames['ccpn_dihedral_restraint_violation_list'] = partial(handleTreeViewSelectionStructureDataParent,
                                                                         prefix='ccpn_dihedral_restraint_violation_',
                                                                         mappingCode='ccpn_dihedral_restraint_violation_list',
                                                                         errorCode='ccpn_dihedral_restraint_violation_list',
                                                                         tableColourFunc=None)

    handleSaveFrames['ccpn_rdc_restraint_violation_list'] = partial(handleTreeViewSelectionStructureDataParent,
                                                                    prefix='ccpn_rdc_restraint_violation_',
                                                                    mappingCode='ccpn_rdc_restraint_violation_list',
                                                                    errorCode='ccpn_rdc_restraint_violation_list',
                                                                    tableColourFunc=None)

    handleSaveFrames['ccpn_datatable'] = partial(handleTreeViewSelectionGeneral,
                                                 prefix='ccpn_datatable_data_',
                                                 mappingCode='ccpn_datatable',
                                                 errorCode='ccpn_datatable',
                                                 tableColourFunc=None,
                                                 allowPeriod=False)

    handleSaveFrames['ccpn_collection'] = partial(handleTreeViewSelectionGeneralNoCollection,
                                                  prefix='ccpn_collection_',
                                                  mappingCode='ccpn_collections',
                                                  errorCode='ccpn_collections',
                                                  tableColourFunc=table_ccpn_collections,
                                                  allowPeriod=False)

    handleSaveFrames['ccpn_logging'] = partial(handleTreeViewSelectionGeneralNoCollection,
                                               prefix='ccpn_history_',
                                               mappingCode='ccpn_logging',
                                               errorCode='ccpn_logging',
                                               tableColourFunc=None)

    handleSaveFrames['ccpn_dataset'] = partial(handleTreeViewSelectionGeneral,
                                               prefix='ccpn_calculation_step_',
                                               mappingCode='ccpn_dataset',
                                               errorCode='ccpn_dataset',
                                               tableColourFunc=None)

    handleSaveFrames['ccpn_parameter'] = partial(handleTreeViewSelectionStructureDataParentNoCollection,
                                                 prefix='ccpn_dataframe_',
                                                 mappingCode='ccpn_parameter',
                                                 errorCode='ccpn_parameter',
                                                 tableColourFunc=None)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    _setBadSaveFrames['nef_sequence'] = partial(_set_bad_saveframe,
                                                prefix='nef_sequence_',
                                                mappingCode='nef_sequence_chain_code',
                                                errorCode='nef_sequence_chain_code',
                                                tableColourFunc=table_nef_molecular_system)

    _setBadSaveFrames['nef_chemical_shift_list'] = partial(_set_bad_saveframe,
                                                           prefix='nef_chemical_shift_',
                                                           mappingCode='nef_chemical_shift_list',
                                                           errorCode='nef_chemical_shift_list',
                                                           tableColourFunc=None)

    _setBadSaveFrames['nef_distance_restraint_list'] = partial(_set_bad_saveframe,
                                                               prefix='nef_distance_restraint_',
                                                               mappingCode='nef_distance_restraint_list',
                                                               errorCode='nef_distance_restraint_list',
                                                               tableColourFunc=None)

    _setBadSaveFrames['nef_dihedral_restraint_list'] = partial(_set_bad_saveframe,
                                                               prefix='nef_dihedral_restraint_',
                                                               mappingCode='nef_dihedral_restraint_list',
                                                               errorCode='nef_dihedral_restraint_list',
                                                               tableColourFunc=None)

    _setBadSaveFrames['nef_rdc_restraint_list'] = partial(_set_bad_saveframe,
                                                          prefix='nef_rdc_restraint_',
                                                          mappingCode='nef_rdc_restraint_list',
                                                          errorCode='nef_rdc_restraint_list',
                                                          tableColourFunc=None)

    _setBadSaveFrames['ccpn_restraint_list'] = partial(_set_bad_saveframe,
                                                       prefix='ccpn_restraint_',
                                                       mappingCode='ccpn_restraint_list',
                                                       errorCode='ccpn_restraint_list',
                                                       tableColourFunc=None)

    _setBadSaveFrames['nef_peak_restraint_links'] = partial(_set_bad_saveframe,
                                                            prefix='nef_peak_restraint_',
                                                            mappingCode='nef_peak_restraint_links',
                                                            errorCode='nef_peak_restraint_links',
                                                            tableColourFunc=None)

    _setBadSaveFrames['ccpn_sample'] = partial(_set_bad_saveframe,
                                               prefix='ccpn_sample_component_',
                                               mappingCode='ccpn_sample',
                                               errorCode='ccpn_sample',
                                               tableColourFunc=None)

    _setBadSaveFrames['ccpn_complex'] = partial(_set_bad_saveframe,
                                                prefix='ccpn_complex_chain_',
                                                mappingCode='ccpn_complex',
                                                errorCode='ccpn_complex',
                                                tableColourFunc=None)

    _setBadSaveFrames['ccpn_spectrum_group'] = partial(_set_bad_saveframe,
                                                       prefix='ccpn_group_spectrum_',
                                                       mappingCode='ccpn_spectrum_group',
                                                       errorCode='ccpn_spectrum_group',
                                                       tableColourFunc=None)

    _setBadSaveFrames['ccpn_note'] = partial(_set_bad_saveframe,
                                             prefix='ccpn_note_',
                                             mappingCode='ccpn_notes',
                                             errorCode='ccpn_notes',
                                             tableColourFunc=table_ccpn_notes)

    _setBadSaveFrames['ccpn_peak_list'] = partial(_set_bad_saveframe,
                                                  prefix='nef_peak_',
                                                  mappingCode='nef_peak',
                                                  errorCode='ccpn_peak_list_serial',
                                                  tableColourFunc=table_peak_lists)

    _setBadSaveFrames['ccpn_integral_list'] = partial(_set_bad_saveframe,
                                                      prefix='ccpn_integral_',
                                                      mappingCode='ccpn_integral_list',
                                                      errorCode='ccpn_integral_list_serial',
                                                      tableColourFunc=partial(table_lists, listName='ccpn_integral'))

    _setBadSaveFrames['ccpn_multiplet_list'] = partial(_set_bad_saveframe,
                                                       prefix='ccpn_multiplet_',
                                                       mappingCode='ccpn_multiplet_list',
                                                       errorCode='ccpn_multiplet_list_serial',
                                                       tableColourFunc=partial(table_lists, listName='ccpn_multiplet'))

    # _setBadSaveFrames['ccpn_peak_cluster_list'] = partial(_set_bad_saveframe,
    #                                                       prefix='ccpn_peak_cluster_',
    #                                                       mappingCode='ccpn_peak_cluster',
    #                                                       errorCode='ccpn_peak_cluster_serial',
    #                                                       tableColourFunc=table_peak_clusters)

    _setBadSaveFrames['nmr_chain'] = partial(_set_bad_saveframe,
                                             prefix='nmr_chain_',
                                             mappingCode='nmr_chain',
                                             errorCode='nmr_chain_serial',
                                             tableColourFunc=table_ccpn_assignment)

    _setBadSaveFrames['ccpn_substance'] = partial(_set_bad_saveframe,
                                                  prefix='ccpn_substance_synonym_',
                                                  mappingCode='ccpn_substance',
                                                  errorCode='ccpn_substance',
                                                  tableColourFunc=None)

    _setBadSaveFrames['ccpn_internal_data'] = partial(_set_bad_saveframe,
                                                      prefix='ccpn_internal_data_',
                                                      mappingCode='ccpn_additional_data',
                                                      errorCode='ccpn_additional_data',
                                                      # tableColourFunc=table_ccpn_additional_data)
                                                      tableColourFunc=None)

    _setBadSaveFrames['ccpn_distance_restraint_violation_list'] = partial(_set_bad_saveframe,
                                                                          prefix='ccpn_distance_restraint_violation_',
                                                                          mappingCode='ccpn_distance_restraint_violation_list',
                                                                          errorCode='ccpn_distance_restraint_violation_list',
                                                                          tableColourFunc=None)

    _setBadSaveFrames['ccpn_dihedral_restraint_violation_list'] = partial(_set_bad_saveframe,
                                                                          prefix='ccpn_dihedral_restraint_violation_',
                                                                          mappingCode='ccpn_dihedral_restraint_violation_list',
                                                                          errorCode='ccpn_dihedral_restraint_violation_list',
                                                                          tableColourFunc=None)

    _setBadSaveFrames['ccpn_rdc_restraint_violation_list'] = partial(_set_bad_saveframe,
                                                                     prefix='ccpn_rdc_restraint_violation_',
                                                                     mappingCode='ccpn_rdc_restraint_violation_list',
                                                                     errorCode='ccpn_rdc_restraint_violation_list',
                                                                     tableColourFunc=None)

    _setBadSaveFrames['ccpn_datatable'] = partial(_set_bad_saveframe,
                                                  prefix='ccpn_datatable_data_',
                                                  mappingCode='ccpn_datatable',
                                                  errorCode='ccpn_datatable',
                                                  tableColourFunc=None)

    _setBadSaveFrames['ccpn_collection'] = partial(_set_bad_saveframe,
                                                   prefix='ccpn_collection_',
                                                   mappingCode='ccpn_collections',
                                                   errorCode='ccpn_collections',
                                                   tableColourFunc=table_ccpn_collections)
    _setBadSaveFrames['ccpn_logging'] = partial(_set_bad_saveframe,
                                                prefix='ccpn_history_',
                                                mappingCode='ccpn_logging',
                                                errorCode='ccpn_logging',
                                                tableColourFunc=None)

    _setBadSaveFrames['ccpn_dataset'] = partial(_set_bad_saveframe,
                                                prefix='ccpn_calculation_step_',
                                                mappingCode='ccpn_dataset',
                                                errorCode='ccpn_dataset',
                                                tableColourFunc=None)

    _setBadSaveFrames['ccpn_parameter'] = partial(_set_bad_saveframe,
                                                  prefix='ccpn_dataframe_',
                                                  mappingCode='ccpn_parameter',
                                                  errorCode='ccpn_parameter',
                                                  tableColourFunc=None)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    applyCheckBoxes['nef_sequence'] = partial(apply_checkBox_item,
                                              prefix='nef_sequence_',
                                              mappingCode='nef_sequence_chain_code',
                                              )

    applyCheckBoxes['nef_chemical_shift_list'] = partial(apply_checkBox_item,
                                                         prefix='nef_chemical_shift_',
                                                         mappingCode='nef_chemical_shift_list',
                                                         )

    applyCheckBoxes['nef_distance_restraint_list'] = partial(apply_checkBox_item,
                                                             prefix='nef_distance_restraint_',
                                                             mappingCode='nef_distance_restraint_list',
                                                             )

    applyCheckBoxes['nef_dihedral_restraint_list'] = partial(apply_checkBox_item,
                                                             prefix='nef_dihedral_restraint_',
                                                             mappingCode='nef_dihedral_restraint_list',
                                                             )

    applyCheckBoxes['nef_rdc_restraint_list'] = partial(apply_checkBox_item,
                                                        prefix='nef_rdc_restraint_',
                                                        mappingCode='nef_rdc_restraint_list',
                                                        )

    applyCheckBoxes['ccpn_restraint_list'] = partial(apply_checkBox_item,
                                                     prefix='ccpn_restraint_',
                                                     mappingCode='ccpn_restraint_list',
                                                     )

    applyCheckBoxes['nef_peak_restraint_links'] = partial(apply_checkBox_item,
                                                          prefix='nef_peak_restraint_',
                                                          mappingCode='nef_peak_restraint_links',
                                                          )

    applyCheckBoxes['ccpn_sample'] = partial(apply_checkBox_item,
                                             prefix='ccpn_sample_component_',
                                             mappingCode='ccpn_sample',
                                             )

    applyCheckBoxes['ccpn_complex'] = partial(apply_checkBox_item,
                                              prefix='ccpn_complex_chain_',
                                              mappingCode='ccpn_complex',
                                              )

    applyCheckBoxes['ccpn_spectrum_group'] = partial(apply_checkBox_item,
                                                     prefix='ccpn_group_spectrum_',
                                                     mappingCode='ccpn_spectrum_group',
                                                     )

    applyCheckBoxes['ccpn_note'] = partial(apply_checkBox_item,
                                           prefix='ccpn_note_',
                                           mappingCode='ccpn_notes',
                                           )

    applyCheckBoxes['ccpn_peak_list'] = partial(apply_checkBox_item,
                                                prefix='nef_peak_',
                                                mappingCode='nef_peak',
                                                checkID='_importPeaks',
                                                )

    applyCheckBoxes['ccpn_integral_list'] = partial(apply_checkBox_item,
                                                    prefix='ccpn_integral_',
                                                    mappingCode='ccpn_integral_list',
                                                    checkID='_importIntegrals',
                                                    )

    applyCheckBoxes['ccpn_multiplet_list'] = partial(apply_checkBox_item,
                                                     prefix='ccpn_multiplet_',
                                                     mappingCode='ccpn_multiplet_list',
                                                     checkID='_importMultiplets',
                                                     )

    # applyCheckBoxes['ccpn_peak_cluster_list'] = partial(apply_checkBox_item,
    #                                                     prefix='ccpn_peak_cluster_',
    #                                                     mappingCode='ccpn_peak_cluster',
    #                                                     )

    applyCheckBoxes['nmr_chain'] = partial(apply_checkBox_item,
                                           prefix='nmr_chain_',
                                           mappingCode='nmr_chain',
                                           )

    applyCheckBoxes['ccpn_substance'] = partial(apply_checkBox_item,
                                                prefix='ccpn_substance_synonym_',
                                                mappingCode='ccpn_substance',
                                                )

    applyCheckBoxes['nef_peak_restraint_link'] = partial(apply_checkBox_item,
                                                         prefix='nef_peak_restraint_',
                                                         mappingCode='nef_peak_restraint_link',
                                                         )

    applyCheckBoxes['ccpn_internal_data'] = partial(apply_checkBox_item,
                                                    prefix='ccpn_internal_data_',
                                                    mappingCode='ccpn_additional_data',
                                                    )

    applyCheckBoxes['ccpn_distance_restraint_violation_list'] = partial(apply_checkBox_item,
                                                                        prefix='ccpn_distance_restraint_violation_',
                                                                        mappingCode='ccpn_distance_restraint_violation_list',
                                                                        )

    applyCheckBoxes['ccpn_dihedral_restraint_violation_list'] = partial(apply_checkBox_item,
                                                                        prefix='ccpn_dihedral_restraint_violation_',
                                                                        mappingCode='ccpn_dihedral_restraint_violation_list',
                                                                        )

    applyCheckBoxes['ccpn_rdc_restraint_violation_list'] = partial(apply_checkBox_item,
                                                                   prefix='ccpn_rdc_restraint_violation_',
                                                                   mappingCode='ccpn_rdc_restraint_violation_list',
                                                                   )

    applyCheckBoxes['ccpn_datatable'] = partial(apply_checkBox_item,
                                                prefix='ccpn_datatable_data_',
                                                mappingCode='ccpn_datatable',
                                                )

    applyCheckBoxes['ccpn_collection'] = partial(apply_checkBox_item,
                                                 prefix='ccpn_collection_',
                                                 mappingCode='ccpn_collections',
                                                 )

    applyCheckBoxes['ccpn_logging'] = partial(apply_checkBox_item,
                                              prefix='ccpn_history_',
                                              mappingCode='ccpn_logging',
                                              )

    applyCheckBoxes['ccpn_dataset'] = partial(apply_checkBox_item,
                                              prefix='ccpn_calculation_step_',
                                              mappingCode='ccpn_dataset',
                                              )

    applyCheckBoxes['ccpn_parameter'] = partial(apply_checkBox_item,
                                                prefix='ccpn_dataframe_',
                                                mappingCode='ccpn_parameter',
                                                )

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _autoRenameItem(self, name, saveFrame, parentGroup):
        if not saveFrame:
            return

        primaryHandler = self.nefTreeView.nefProjectToHandlerMapping.get(parentGroup) or saveFrame.get('sf_category')
        if primaryHandler:
            handler = self.handleSaveFrames.get(primaryHandler)
            if handler is not None:
                handler(self, name=name, saveFrame=saveFrame, parentGroup=parentGroup, _handleAutoRename=True)  #, item)

    def _checkBadItem(self, name, saveFrame, parentGroup):
        if not saveFrame:
            return

        primaryHandler = self.nefTreeView.nefProjectToHandlerMapping.get(parentGroup) or saveFrame.get('sf_category')
        if primaryHandler:
            handler = self._setBadSaveFrames.get(primaryHandler)
            if handler is not None:
                return handler(self, name=name, saveFrame=saveFrame, parentGroup=parentGroup, )  #, item)

    def _nefTreeClickedCallback(self, item=None, column=0):
        """Handle clicking on an item in the nef tree
        """
        itemName = item.data(0, 0)
        if item.data(1, 0):
            # item at bottom of the tree selected
            _, saveFrame, _, _, _ = item.data(1, 0)
            if saveFrame and hasattr(saveFrame, '_content'):
                self._itemSelected(item, itemName, saveFrame)

        else:
            # parent item selected
            self._parentSelected(item, itemName)

        self._updateTables()

    def _itemSelected(self, item, itemName, saveFrame):
        with self._tableSplitter.blockWidgetSignals(recursive=False):
            self._tableSplitter.setVisible(False)

            # reuse the widgets?
            for widg in self._nefWidgets:
                self._removeWidget(widg, removeTopWidget=True)
            self._nefWidgets = []
            self._removeWidget(self.frameOptionsFrame, removeTopWidget=False)

            _fillColour = INVALIDTABLEFILLNOCHECKCOLOUR if item.checkState(0) else INVALIDTABLEFILLNOCHECKCOLOUR

            parentGroup = item.parent().data(0, 0) if item.parent() else repr(None)

            # add the first table from the saveframe attributes
            loop = StarIo.NmrLoop(name=saveFrame.name, columns=('attribute', 'value'))
            for k, v in saveFrame.items():
                if not (k.startswith('_') or isinstance(v, StarIo.NmrLoop)):
                    loop.newRow((k, v))
            _name, _data = saveFrame.name, loop.data

            self._nefTables = {}

            frame, table = self._addTableToFrame(_data, _name.upper(), newWidgets=True,
                                                 showMore=self._nefImporterOpenFirstTable)
            table.resizeColumnsToContents()

            # get the group name add fetch the correct mapping
            mapping = self.nefTreeView.nefProjectToSaveFramesMapping.get(parentGroup)
            primaryHandler = self.nefTreeView.nefProjectToHandlerMapping.get(parentGroup) or saveFrame.get(
                    'sf_category')

            # add tables from the loops in the saveframe
            loops = self._nefReader._getLoops(self.project, saveFrame)
            for loop in loops:

                if mapping and loop.name not in mapping:
                    continue

                _name, _data = loop.name, loop.data
                frame, table = self._addTableToFrame(_data, _name, showMore=False)

                if loop.name in saveFrame._content and \
                        hasattr(saveFrame, '_rowErrors') and \
                        loop.name in saveFrame._rowErrors:
                    badRows = list(saveFrame._rowErrors[loop.name])

                    with self._tableColouring(table) as setRowBackgroundColour:
                        for rowIndex in badRows:
                            setRowBackgroundColour(rowIndex, _fillColour)

            if primaryHandler:
                handler = self.handleSaveFrames.get(primaryHandler)
                if handler is not None:
                    # handler(self, saveFrame, item)
                    handler(self, name=itemName, saveFrame=saveFrame, parentGroup=parentGroup)

            # clicking the checkbox also comes here - above loop may set item._badName
            self._colourTreeView()

            self._filterLogFrame.setVisible(self._enableFilterFrame)
            # self.nefTreeView.setCurrentItem(item)

        for colInd, st in enumerate([1, 100, 1]):
            self.frameOptionsFrame.getLayout().setColumnStretch(colInd, st)
        self._tableSplitter.setVisible(True)

    @staticmethod
    def _depth(item):
        depth = 0
        while item:
            item = item.parent()
            depth += 1
        return depth

    def _parentSelected(self, parentItem, parentItemName):

        with self._tableSplitter.blockWidgetSignals(recursive=False):
            self._tableSplitter.setVisible(False)

            # depth = 1 -> project
            # depth = 2 -> groups
            # depth = 3 -> saveFrames - either item or object, e.g., restraintList, note

            # reuse the widgets?
            for widg in self._nefWidgets:
                self._removeWidget(widg, removeTopWidget=True)
            self._nefWidgets = []
            self._removeWidget(self.frameOptionsFrame, removeTopWidget=False)

            if self._depth(parentItem) != 2:
                return

            _count = parentItem.childCount()
            if _count:
                # call the correct parent handler to add the correct widgets
                parentHandler = self.handleParentGroups.get(parentItemName)
                if parentHandler is not None:
                    parentHandler(self, parentItem=parentItem, parentItemName=parentItemName, _handleAutoRename=False)

        for colInd, st in enumerate([1, 100, 1]):
            self.frameOptionsFrame.getLayout().setColumnStretch(colInd, st)
        self._tableSplitter.setVisible(True)

    def _multiParentSelected(self, groups, structureGroups):

        with self._tableSplitter.blockWidgetSignals(recursive=False):
            self._tableSplitter.setVisible(False)

            # depth = 1 -> project
            # depth = 2 -> groups
            # depth = 3 -> saveFrames - either item or object, e.g., restraintList, note

            # reuse the widgets?
            for widg in self._nefWidgets:
                self._removeWidget(widg, removeTopWidget=True)
            self._nefWidgets = []
            self._removeWidget(self.frameOptionsFrame, removeTopWidget=False)

            # parent handler here
            row = 0

            # structures
            if structureGroups:
                _names = '\n'.join([nn for nn in structureGroups.keys()])
                _frame = MoreLessFrame(self.frameOptionsFrame, name=_names, showMore=True, grid=(row, 0),
                                       gridSpan=(1, 3))
                row += 1

                _iRow = 0
                Label(_frame.contentsFrame, text=STRUCTUREDATA, grid=(_iRow, 0))
                structurePulldown = self._newPulldown(_frame.contentsFrame, name=STRUCTUREDATA,
                                                      grid=(_iRow, 1), gridSpan=(1, 2), allowEmpty=False)

                _iRow += 1
                values = [itm for val in structureGroups.values() for itm in val]
                callbackSelect = partial(self._selectStructureDataGroup, values=values, pulldownList=structurePulldown,
                                         parent=self.nefTreeView)
                structurePulldown.activated.connect(callbackSelect)

                self._populateStructureDataPulldown(values, structurePulldown)

            # collections
            if groups:
                if len(groups) > 5:
                    # restrict the number shown for clarity
                    _subset = list(groups.keys())[:2] + ['...'] + list(groups.keys())[-2:]
                    _names = '\n'.join(_subset)
                else:
                    _names = '\n'.join([nn for nn in groups.keys()])
                _frame = MoreLessFrame(self.frameOptionsFrame, name=_names, showMore=True, grid=(row, 0),
                                       gridSpan=(1, 3))
                row += 1

                _iRow = 0
                Label(_frame.contentsFrame, text=COLLECTION, grid=(_iRow, 0))
                collectionPulldown = self._newPulldown(_frame.contentsFrame,
                                                       grid=(_iRow, 1), gridSpan=(1, 2))

                _iRow += 1
                values = [itm for val in groups.values() for itm in val]
                callbackSelect = partial(self._selectCollectionStructureGroup, values=values,
                                         pulldownList=collectionPulldown, parent=self.nefTreeView)
                collectionPulldown.activated.connect(callbackSelect)

                self._populateCollectionStructurePulldown(values, collectionPulldown)

            self._updateTables()
            self.frameOptionsFrame.setVisible(self._enableRename)

        for colInd, st in enumerate([1, 100, 1]):
            self.frameOptionsFrame.getLayout().setColumnStretch(colInd, st)
        self._tableSplitter.setVisible(True)

    @contextmanager
    def _tableColouring(self, table):
        # not sure if this is needed now - handled by the _SimplePandasTableModel indexing
        def _setRowBackgroundColour(row, colour):
            # set the colour for the items in the model colour table
            for j in _cols:
                model.setBackground(row, j, colour)

        model = table.model()
        _cols = range(model.columnCount())

        yield _setRowBackgroundColour

    def _addTableToFrame(self, _data, _name, newWidgets=False, _table=None, ignoreFrame=False, showMore=False):
        """Add a new gui table into a moreLess frame to hold a nef loop
        """
        frame = MoreLessFrame(self, name=_name, showMore=showMore, grid=(0, 0))

        # table = _newSimplePandasTable(frame.contentsFrame, pd.DataFrame(_data))
        table = NefTable(frame.contentsFrame, df=pd.DataFrame(_data),
                         selectionCallbackEnabled=False, actionCallbackEnabled=False,
                         enableDelete=False)
        table.setEditable(False)

        frame.contentsFrame.getLayout().addWidget(table, 0, 0)
        frame.contentsFrame.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        frame.contentsFrame.setMinimumSize(100, 100)
        table.setVisible(True)

        if not ignoreFrame:
            self._nefTables[_name] = table
            self._tableSplitter.addWidget(frame)
            if newWidgets:
                self._nefWidgets = [frame, ]
            else:
                if not self._nefWidgets:
                    self._nefWidgets = []
                self._nefWidgets.append(frame)

        return frame, table

    def _updateTables(self):

        # update the collections table
        if self._collectionsTable and self._collections:
            _df = pd.DataFrame({COLLECTION: self._collections.keys(),
                                'Items'   : ['\n'.join(val) for val in self._collections.values()]})
            # _updateSimplePandasTable(self._collectionsTable, _df, _resize=True)
            self._collectionsTable.updateDf(_df, resize=True)

            _model = self._collectionsTable.model()
            # colour the structureData if exist in the project
            for row, col in enumerate(self._collections.keys()):
                if self.project.getByPid(Pid._join(Collection.shortClassName, col)):
                    _model.setForeground(row, 0, INVALIDTEXTROWNOCHECKCOLOUR)
        else:
            _df = pd.DataFrame({COLLECTION: [], 'Items': []})
            # _updateSimplePandasTable(self._collectionsTable, _df)
            self._collectionsTable.updateDf(_df)

        # rebuild the list of structureData
        _itms = self._getAllChildren()
        # self._structureData = OrderedDict((sd.id, []) for sd in self.project.structureData)
        self._structureData = {}
        for itm in _itms:
            itmName, sFrame, parentGroup, primaryHandler, _ccpnClassName = itm

            if parentGroup in ['restraintTables', 'violationTables']:
                _itmStructureData = sFrame.get(DATANAME) or ''  # make sure isn't None
                _itmPid = Pid._join(_ccpnClassName, _itmStructureData, itmName) if _ccpnClassName else itmName
                # _sdPid = Pid._join(StructureData.shortClassName, _itmStructureData)

                # add the structure to the dict by shortClassName
                self._structureData.setdefault(_itmStructureData, [])
                self._structureData[_itmStructureData].append(_itmPid)

            elif parentGroup in ['structureData']:
                # _itmPid = Pid._join(_ccpnClassName, itmName) if _ccpnClassName else itmName
                self._structureData.setdefault(itmName, [])

        # update the structureData table
        if self._structureDataTable and self._structureData:
            _df = pd.DataFrame({STRUCTUREDATA: self._structureData.keys(),
                                'Items'      : ['\n'.join(val) for val in self._structureData.values()]})
            # _updateSimplePandasTable(self._structureDataTable, _df, _resize=True)
            self._structureDataTable.updateDf(_df, resize=True)

            _model = self._structureDataTable.model()
            # colour the structureData if exist in the project
            for row, sd in enumerate(self._structureData.keys()):
                if self.project.getByPid(Pid._join(StructureData.shortClassName, sd)):
                    _model.setForeground(row, 0, INVALIDTEXTROWNOCHECKCOLOUR)
        else:
            _df = pd.DataFrame({STRUCTUREDATA: [], 'Items': []})
            # _updateSimplePandasTable(self._structureDataTable, _df)
            self._structureDataTable.updateDf(_df)

    def _fillPopup(self, nefObject=None):
        """Initialise the project setting - only required for testing
        Assumes that the nef loaders may not be initialised if called from outside of Analysis
        """
        if not self._nefLoader:
            self._nefLoader = self._nefImporterClass(errorLogging=Nef.el.NEF_STANDARD, hidePrefix=True)

            if not self.project:
                raise TypeError('Project is not defined')
            self._nefWriter = CcpnNefIo.CcpnNefWriter(self.project)
            self._nefDict = self._nefLoader._nefDict = self._nefWriter.exportProject(expandSelection=True,
                                                                                     includeOrphans=False, pidList=None)

        # attach the import/verify/content methods
        self._nefLoader._attachVerifier(self._nefReader.verifyProject)
        self._nefLoader._attachReader(self._nefReader.importExistingProject)
        self._nefLoader._attachContent(self._nefReader.contentNef)
        self._nefLoader._attachClear(self._nefReader.clearSaveFrames)

        # process the contents and verify
        self._nefLoader._clearNef(self.project, self._nefDict)
        self._nefLoader._contentNef(self.project, self._nefDict, selection=None)

        # changed to verify with the button
        # if not self._primaryProject and self.verifyCheckBox.isChecked():
        warnings, errors = self._nefLoader._verifyNef(self.project, self._nefDict, selection=None)

        try:
            self.valid = self._nefLoader.isValid
        except Exception as es:
            getLogger().warning(str(es))

        self._populate()

    def _verifyChecked(self, state=False):
        """Respond to clicking the verify checkbox
        """
        if state:
            self._verifyPopulate()

    def _removeParentTreeState(self, item, data=[], prefix=''):
        """Remove parents from the tree that have no children
        """
        if (self._depth(item) == 2) and item.childCount() == 0:
            data.append(item)

    def _getTreeState(self, item, data: dict, prefix=''):
        """Add the name of expanded item to the data list
        """
        if item:
            # store the expanded/checked state in the dict
            expandedState = item.isExpanded()
            checkedState = item.checkState(0)
            data[prefix + item.data(0, 0)] = (expandedState, checkedState)

    def _getAllItemState(self, item, data: [], prefix=''):
        """Add the name of expanded item to the data list
        """
        if item:
            if (_data := item.data(1, 0)):
                data.append(_data)

    def _setTreeState(self, item, data: dict, prefix=''):
        """Set the expanded flag if item is in data
        """
        if item:
            try:
                # restore the expanded/checked state from the dict
                expandedState, checkedState = data[prefix + item.data(0, 0)]
                item.setCheckState(0, checkedState)
                item.setExpanded(expandedState)
            except Exception as es:
                getLogger().debug2(f' {es}')

    def _traverseTree(self, node=None, func=None, data=None, prefix=''):
        """Traverse the tree, applying <func> to all nodes

        :param func: function to perform on this element
        :param data: optional data storage to pass to <func>
        """
        prefix = prefix + node.data(0, 0)  # concatenate the prefixes to give unique key
        _count = node.childCount()
        for i in range(_count):
            child = node.child(i)
            self._traverseTree(child, func=func, data=data, prefix=prefix)

        if func:
            # process the node
            func(node, data, prefix)

    def _verifyPopulate(self):
        """Respond to clicking the verify button
        """
        from ccpn.core.lib.ContextManagers import notificationEchoBlocking

        if not self._primaryProject:
            with notificationEchoBlocking():

                dd = {}
                # grab the tree state
                self._traverseTree(self.nefTreeView.headerItem, self._getTreeState, dd)

                self.nefTreeView._populateTreeView(self.project)
                warnings, errors = self._nefLoader._verifyNef(self.project, self._nefDict, selection=None)

                try:
                    self.valid = self._nefLoader.isValid
                except Exception as es:
                    getLogger().warning(str(es))

                self._populate()

                # restore the tree state
                self._traverseTree(self.nefTreeView.headerItem, self._setTreeState, dd)

    def getItemsToImport(self):
        self._nefReader.setImportAll(False)
        treeItems = [item for item in self.nefTreeView.traverseTree() if item.checkState(0) == QtCore.Qt.Checked]
        # selection = [item.data(1, 0)[1] for item in treeItems if item.data(1, 0)] or [None]  # saveFrame
        selection = []
        for item in treeItems:
            if (_data := item.data(1, 0)):
                _, sFrame, _, _, _ = _data
                selection.append(sFrame)
        selection = selection or [None]
        # NOTE:ED - should use a namedtuple

        if not (handlerMapping := self.nefTreeView.nefProjectToHandlerMapping):
            return

        self._nefReader._importDict = {}
        for item in treeItems:

            if (_data := item.data(1, 0)):
                itemName, saveFrame, parentGroup, _, _ = _data
                if saveFrame:
                    if primaryHandler := handlerMapping.get(parentGroup) or saveFrame.get('sf_category'):
                        handler = self.applyCheckBoxes.get(primaryHandler)
                        if handler is not None:
                            handler(self, name=itemName, saveFrame=saveFrame, parentGroup=parentGroup)  #, item)

        return selection

    def _addToCollectionsMenu(self, contextMenu, selectionWidget):
        """Add options to the bottom of the menu
        """
        if contextMenu:
            enable = any(kls
                         for itm in selectionWidget.selectedItems()
                         if (dta := itm.data(1, 0)) and (kls := dta[4]) and kls
                         )
            contextMenu.addSeparator()
            menu = contextMenu.addMenu('Add to Collection ...')
            removeMenu = contextMenu.addItem('Remove from Collections',
                                             callback=partial(self._removeFromCollection,
                                                              selectionWidget=selectionWidget))
            menu.setEnabled(enable)
            removeMenu.setEnabled(enable)
            if enable:
                menu.addItem('<New Collection>',
                             callback=partial(self._makeNewCollection, selectionWidget=selectionWidget))
                colNames = OrderedSet(
                        [col.name for col in self.project.collections]
                        + list(self._collections.keys())
                        )
                for col in colNames:
                    menu.addItem(col, callback=partial(self._addToCollection, col, selectionWidget=selectionWidget))

            itm = self.nefTreeView.currentItem()
            if itm and self._depth(itm) == 1:
                # show extra options for the top item
                contextMenu.addSeparator()
                contextMenu.addItem('Expand All', callback=partial(self._setExpandState, state=True))
                contextMenu.addItem('Collapse All', callback=partial(self._setExpandState, state=False))

    def _removeFromCollection(self, selectionWidget):
        """Remove the selected items from any collection
        """
        # pass None to remove from collections
        self._addToCollection(None, selectionWidget=selectionWidget)

    @staticmethod
    def _newPulldown(parent, allowEmpty=True, name=COLLECTION, **kwds):
        combo = PulldownList(parent, editable=True, **kwds)
        combo.setMinimumWidth(50)
        _validator = LineEditValidator(parent=combo, allowSpace=False,
                                       allowEmpty=allowEmpty)
        combo.setValidator(_validator)
        combo.lineEdit().setPlaceholderText(f'<{name} Name>')

        if name == COLLECTION:
            combo.setToolTip(f'Select existing collection, or edit to create new collection.\n'
                             f'Choose {REMOVEENTRY} to remove selection from all collections.')
        else:
            combo.setToolTip('Select existing structureData, or edit to create new structureData.')
        combo.setCompleter(None)

        return combo

    def _makeNewCollection(self, selectionWidget):
        """Make a small popup to enter a new collection name
        """


        # make a simple popup for editing collection
        class EditCollection(SpeechBalloon):
            """Balloon to hold the pulldown list for editing/selecting the collection name
            """

            def __init__(self, parent, newPulldown, selectionWidget, *args, **kwds):
                """Initialise the class

                :param parent: parent class from which popup is instanciated
                :param newPulldown: func to create a new pulldown
                :param args: values to pass on to SpeechBalloon
                :param kwds: values to pass on to SpeechBalloon
                """
                super().__init__(*args, **kwds)

                self._parent = parent
                self._newPulldown = newPulldown
                self._selectionWidget = selectionWidget

                # simplest way to make the popup function as modal and disappear as required
                self.setWindowFlags(int(self.windowFlags()) | QtCore.Qt.Popup)
                self._metrics.corner_radius = 1
                self._metrics.pointer_height = 0

                # set the background/fontSize for the tooltips
                self.setStyleSheet('QToolTip {{ background-color: {TOOLTIP_BACKGROUND}; '
                                   'color: {TOOLTIP_FOREGROUND}; '
                                   'font-size: {_size}pt ; }}'.format(_size=self.font().pointSize(), **getColours()))

                # add the widgets
                _frame = Frame(self, setLayout=True, margins=(10, 10, 10, 10))
                _label = Label(_frame, text=COLLECTION, grid=(0, 0), gridSpan=(1, 2))
                self._pulldownWidget = self._newPulldown(_frame, grid=(1, 0), gridSpan=(1, 2), )

                # set to the class central widget
                self.setCentralWidget(_frame)

            # add methods for setting pulldown options
            def setDefaultName(self, name):
                self._pulldownWidget.lineEdit().setText(name)

            # add methods for setting pulldown options
            def setPulldownData(self, texts):
                self._pulldownWidget.setData(texts=texts)

            def setPulldownCallback(self, callback):
                self._pulldownWidget.activated.connect(
                        partial(callback, self._pulldownWidget, self, selectionWidget=self._selectionWidget))

            @property
            def centralWidgetSize(self):
                """Return the sizeHint for the central widget
                """
                return self._central_widget_size()


        # get the collection names from the project
        colData = self.project.collections
        colNames = OrderedSet(['', REMOVEENTRY] + [co.name for co in colData])

        # get the collections in the importer - not defined in the project
        for col in self._collections.keys():
            colNames.add(col)
            self._collections.setdefault(col, [])

        # create a small editor
        editPopup = EditCollection(parent=self, newPulldown=self._newPulldown,
                                   selectionWidget=selectionWidget,
                                   on_top=True)
        editPopup.setPulldownData(list(colNames))
        editPopup.setPulldownCallback(self._createNewCollection)
        editPopup.setDefaultName(Collection._uniqueName(self.project))

        # get the desired position of the popup
        pos = QtGui.QCursor().pos()
        _size = editPopup.centralWidgetSize / 2
        popupPos = pos - QtCore.QPoint(_size.width(), _size.height())

        # show the editPopup near the mouse position
        editPopup.showAt(popupPos)
        # set the focus to the pulldown-list
        editPopup._pulldownWidget.setFocus()

    def _createNewCollection(self, pulldown, popup, selectionWidget):
        """Creat a new collection, or remove from collections
        and close the editPopup"""
        collection = pulldown.getText()
        popup.hide()
        popup.deleteLater()
        self._addToCollection(collection, selectionWidget=selectionWidget)

    def _addToCollection(self, collection, selectionWidget):

        selection = selectionWidget.selectedItems()
        _updates = []
        for obj in selection:

            if isinstance(obj, QtWidgets.QListWidgetItem):
                if not (obj.data(QtCore.Qt.UserRole) and selectionWidget.objects[obj.data(QtCore.Qt.UserRole)]):
                    continue

                itemName, saveFrame, parentGroup, primaryHandler, ccpnClassName = selectionWidget.objects[
                    obj.data(QtCore.Qt.UserRole)]

            elif isinstance(obj, QtWidgets.QTreeWidgetItem):
                if not obj.data(1, 0):
                    # skip if not a child object
                    continue

                itemName, saveFrame, parentGroup, primaryHandler, ccpnClassName = obj.data(1, 0)
            else:
                continue

            if saveFrame:
                if saveFrame and primaryHandler:
                    # add to collection
                    if ccpnClassName:
                        # process pid
                        # if DATANAME in saveFrame:
                        if parentGroup in ['restraintTables', 'violationTables']:
                            #   until saveFrames are subclassed from an ABC
                            _itmStructureData = saveFrame.get(DATANAME) or ''  # make sure isn't None
                            _itmPid = Pid._join(ccpnClassName, _itmStructureData,
                                                itemName) if ccpnClassName else itemName
                        else:
                            _itmPid = Pid._join(ccpnClassName, itemName) if ccpnClassName else itemName

                        # remove from previous self._collections
                        for k, v in list(self._collections.items()):
                            if _itmPid in v:
                                v.remove(_itmPid)
                            if not v:
                                self._collections.pop(k)

                        if collection and collection != REMOVEENTRY:
                            self._collections.setdefault(collection, [])
                            self._collections[collection].append(_itmPid)

                        _updates.append((itemName, parentGroup))

        self._updateTables()
        for itemName, parentGroup in _updates:
            self._setCheckedItem(itemName, parentGroup)

    def _setExpandState(self, state=True):
        """Set the expanded state of the children of the clicked item
        """
        itm = self.nefTreeView.currentItem()
        _children = [itm.child(ii) for ii in range(itm.childCount())]
        for child in _children:
            child.setExpanded(state)

    # def _selectionChanged(self, selected, deselected):
    #     print(f'selectionChanged')
    #     newItms = [self.nefTreeView.itemFromIndex(itm).data(0, 0) for ind in [ii for ii in selected] for itm in ind.indexes()]
    #     oldItms = [self.nefTreeView.itemFromIndex(itm).data(0, 0) for ind in [ii for ii in deselected] for itm in ind.indexes()]
    #     print(f'selected    - {newItms}')
    #     print(f'deselected  - {oldItms}')

    def _mouseChecked(self, item, column: int) -> None:
        """Check what has been checked and update other check boxes as required
        """
        if item.checkState(0) == QtCore.Qt.Checked:
            if (_data := item.data(1, 0)):
                itemName, saveFrame, parentGroup, pHandler, ccpnClassName = _data
                if parentGroup in ['restraintTables']:
                    # automatically check the restraintLinks group
                    self._setCheckedItem('restraintLinks', 'restraintLinks')

    def _mouseReleaseCallback(self):
        """Handle multi-selection when releasing the mouse
        """

        selection = self.nefTreeView.selectionModel().selectedIndexes()
        if (newItms := [self.nefTreeView.itemFromIndex(itm) for itm in selection]):

            # print(f'selected    - {[itm.data(0, 0) for itm in newItms]}')
            if len(newItms) == 1:
                # clicked a single item
                # print(f'   SINGLE  {newItms[0]}')
                self._nefTreeClickedCallback(newItms[0], 0)

            elif len(newItms) > 1:
                # clicked multiple - need to handle differently
                if parents := list({itm.data(1, 0)[2] for itm in newItms if itm.data(1, 0)}):
                    if (parentItm := self.nefTreeView.findSection(parents[0])):

                        if isinstance(parentItm, (list, tuple)):
                            # make sure that only one parent has been found - common names may cause duplicates
                            parentItm = [itm for itm in parentItm if not itm.data(1, 0)]
                            parentItm = parentItm[0]

                        if len(parents) == 1:
                            # print(f'   MULTI-SELECT  SINGLE GROUP {parents}')

                            # clicked group of only one type
                            self._nefTreeClickedCallback(parentItm, 0)
                        else:
                            # print(f'   MULTI-SELECT  MANY {parents}')
                            # call either collection or collection/structureData depending on selection

                            # make the selected groups
                            groups = OrderedDict()
                            for itm in newItms:
                                if (_data := itm.data(1, 0)):
                                    # item exists
                                    itemName, sFrame, parentGroup, primaryHandler, ccpnClassName = _data

                                    group = groups.setdefault(parentGroup, [])
                                    group.append(_data)

                            # print(f' groups')
                            # print('\n'.join([k+'-'+itm[0] for k, val in groups.items() for itm in val]))

                            structureGroups = OrderedDict([(k, val) for k, val in groups.items()
                                                           if k in ['restraintTables', 'violationTables']])
                            # print(f' SDgroups')
                            # print('\n'.join(['sd-'+k+'-'+itm[0] for k, val in structureGroups.items() for itm in val]))

                            self._multiParentSelected(groups=groups, structureGroups=structureGroups)

                            self._updateTables()

    def exitNefDictFrame(self):
        """Finalise the state of the nefDictFrame ready for the actual loading
        """

        # remove content not to be imported
        # possibly need new set of code :|

        # add a new collections saveFrame
        if not self._collections:
            return

        category = 'ccpn_collections'

        # get a new name
        name = StarIo.string2FramecodeString('fromnefimporter')
        if name != category:
            name = f'{category}_{name}'

        # Set up new collections saveFrame
        result = StarIo.NmrSaveFrame(name=name, category=category)
        result.addItem('sf_category', category)
        result.addItem('sf_framecode', name)

        # find the loops
        frameMap = CcpnNefIo.nef2CcpnMap.get(category) or {}
        for tag, itemvalue in frameMap.items():
            if not isinstance(itemvalue, (str, type(None))):  # a loop
                result.newLoop(tag, CcpnNefIo.nef2CcpnMap.get(tag) or {})

        # make a new loop row mapping
        loopName = 'ccpn_collection'
        loop = result[loopName]
        _mapping = CcpnNefIo.nef2CcpnMap.get(loopName) or {}
        rowdata = {neftag: None for neftag, attrstring in _mapping.items()}

        # fill the import dict so contents of saveframe is loaded
        _importDict = self._nefReader._importDict.setdefault(name, {})
        _importDict.setdefault('_importRows', tuple(self._collections.keys()))

        # add rows for each new collection
        for ii, (col, itms) in enumerate(self._collections.items()):
            row = loop.newRow(rowdata)
            row['uniqueId'] = ii
            row['name'] = col
            row['items'] = json.dumps(itms)
            row['comment'] = 'from NefImporter'

        # add to the datablock
        self._nefDict.addItem(result['sf_framecode'], result)


class ImportNefPopup(CcpnDialogMainWidget):
    """
    Nef management class
    """
    USESCROLLWIDGET = True
    FIXEDWIDTH = False
    FIXEDHEIGHT = False
    DEFAULTMARGINS = (5, 5, 5, 5)

    def __init__(self, parent, mainWindow, project, dataLoader, **kwds):
        """
        Initialise the main form

        :param parent: calling widget
        :param mainWindow: gui mainWindow class for the application
        :param project: a Project instance
        :param dataLoader: A NefDataLoader instance
        :param kwds: additional parameters to pass to the window
        """
        size = (1000, 700)
        super().__init__(parent, setLayout=True, windowTitle='Import Nef', size=size, **kwds)
        self._size = size  # GWV: this seems to fail if I make this a class attribute

        # nefObjects=({NEFFRAMEKEY_IMPORT: project,
        #             },
        #             {NEFFRAMEKEY_IMPORT           : nefImporter,
        #              NEFFRAMEKEY_ENABLECHECKBOXES : True,
        #              NEFFRAMEKEY_ENABLERENAME     : True,
        #              NEFFRAMEKEY_ENABLEFILTERFRAME: True,
        #              NEFFRAMEKEY_ENABLEMOUSEMENU  : True,
        #              NEFFRAMEKEY_PATHNAME         : str(path),
        #              }
        #             )

        self.mainWindow = mainWindow
        self.application = mainWindow.application
        self.project = project

        self._dataLoader = dataLoader
        self._nefImporter = dataLoader.nefImporter
        self._path = str(dataLoader.path)

        # if not isinstance(nefImporterClass, (type(Nef.NefImporter), type(None))):
        #     raise RuntimeError(f'{nefImporterClass} must be of type {Nef.NefImporter}')
        # self._nefImporterClass = nefImporterClass if nefImporterClass else Nef.NefImporter

        # # create a list of nef dictionary objects
        # self.setNefObjects(nefObjects)

        # object to contain items that are to be imported
        self._saveFrameSelection = []
        self._activeImportWindow = None

        # set up the widgets
        self.setWidgets()

        # enable the buttons
        self.setOkButton(callback=self._okClicked, text='Import', tipText='Import nef file over existing project')
        self.setCancelButton(callback=self.reject, tipText='Cancel import')
        self.setDefaultButton(CcpnDialogMainWidget.CANCELBUTTON)

    def _postInit(self):
        # initialise the buttons and dialog size
        super()._postInit()

        self._okButton = self.getButton(self.OKBUTTON)
        self._cancelButton = self.getButton(self.CANCELBUTTON)

        # populate the widgets
        self.fillPopup()

    def setWidgets(self):
        """Initialise the main widgets for the form
        """
        self.paneSplitter = Splitter(self.mainWidget, setLayout=True, horizontal=True)
        self.paneSplitter.setChildrenCollapsible(False)
        self.mainWidget.getLayout().addWidget(self.paneSplitter, 0, 0)

        self._nefWindows = OrderedDict()
        # for nefObj in self.nefObjects:
        #     # for obj, enableCheckBoxes, enableRename in self.nefObjects:
        #
        #     # add a new nefDictFrame for each of the objects in the list (project or nefImporter)
        #     newWindow = NefDictFrame(parent=self,
        #                              mainWindow=self.mainWindow,
        #                              nefLoader=self._nefImporter,
        #                              pathName=self._path,
        #                              grid=(0, 0), showBorder=True,
        #                              **nefObj)
        #
        #     self._nefWindows[nefObj[NEFFRAMEKEY_IMPORT]] = newWindow
        #     self.paneSplitter.addWidget(newWindow)
        _options = {NEFFRAMEKEY_ENABLECHECKBOXES : True,
                    NEFFRAMEKEY_ENABLERENAME     : True,
                    NEFFRAMEKEY_ENABLEFILTERFRAME: True,
                    NEFFRAMEKEY_ENABLEMOUSEMENU  : True,
                    }
        _dataBlock = self._dataLoader.dataBlock  # This will also assure data have been read
        newWindow = NefDictFrame(parent=self,
                                 mainWindow=self.mainWindow,
                                 nefLoader=self._nefImporter,
                                 dataBlock=_dataBlock,
                                 pathName=self._path,
                                 grid=(0, 0), showBorder=True,
                                 **_options
                                 )

        self._nefWindows[self._nefImporter.getName(prePend=True)] = newWindow
        self.paneSplitter.addWidget(newWindow)
        self.setActiveNefWindow(0)

    def _populate(self):
        """Populate all frames
        """
        for nefWindow in self._nefWindows.values():
            nefWindow._populate()

    def accept(self):
        """Accept the dialog
        """
        # if the mouse is over the ok button and it has focus
        if self._okButton.hasFocus() and self._okButton.underMouse():
            super().accept()

    def setNefObjects(self, nefObjects):
        # create a list of nef dictionary objects here and add to splitter
        # self.nefObjects = tuple(obj for obj in nefObjects if isinstance(obj, tuple)
        #                         and len(obj) == 3
        #                         and isinstance(obj[0], (Nef.NefImporter, Project))
        #                         and isinstance(obj[1], bool)
        #                         and isinstance(obj[2], bool))
        self.nefObjects = ()
        if not isinstance(nefObjects, (tuple, list)):
            raise TypeError(f'nefObjects {nefObjects} must be a list/tuple')
        for checkObj in nefObjects:
            if not isinstance(checkObj, dict):
                raise TypeError(f'nefDictFrame object {checkObj} must be a dict')

            for k, val in checkObj.items():
                if k not in NEFDICTFRAMEKEYS.keys():
                    raise TypeError(f'nefDictFrame object {checkObj} contains a bad key {k}')
                if not isinstance(val, (NEFDICTFRAMEKEYS[k])):
                    raise TypeError(f'nefDictFrame key {k} must be of type {NEFDICTFRAMEKEYS[k]}')
            if missingKeys := [kk for kk in NEFDICTFRAMEKEYS_REQUIRED if kk not in checkObj.keys()]:
                raise TypeError(f'nefDictFrame missing keys {repr(missingKeys)}')

            self.nefObjects += (checkObj,)

        if len(self.nefObjects) != len(nefObjects):
            getLogger().warning(f'nefObjects contains bad items {nefObjects}')

    def setActiveNefWindow(self, value):
        """Set the number of the current active nef window for returning values from the dialog
        """
        if isinstance(value, int) and 0 <= value < len(self._nefWindows):
            self._activeImportWindow = value
        else:
            ll = len(self._nefWindows)
            raise TypeError(
                    f"Invalid window number, must be 0{'-' if ll > 1 else ''}{ll - 1 if ll > 1 else ''}"
                    )

    def getActiveNefReader(self):
        """Get the current active nef reader for the dialog
        """
        return list(self._nefWindows.values())[self._activeImportWindow]._nefReader

    def getNewCollections(self):
        """Get the dict of new collections to create after loading
        """
        return list(self._nefWindows.values())[self._activeImportWindow]._collections

    def _initialiseProject(self, mainWindow, application, project):
        """Initialise the project setting - only required for testing
        """
        self.mainWindow = mainWindow
        self.application = application
        self.project = project
        if mainWindow is None:
            self.mainWindow = AttrDict()

        # set the new values for application and project
        self.mainWindow.application = application
        self.mainWindow.project = project

        # set the projects for the windows
        for nefWindow in self._nefWindows.values():
            nefWindow._initialiseProject(mainWindow, application, project)

    def fillPopup(self):
        # set the projects for the windows
        for obj, nefWindow in self._nefWindows.items():
            nefWindow._fillPopup(obj)

            for itm in nefWindow.nefTreeView.traverseTree():
                if itm.data(0, 0) not in nefWindow.nefTreeView.nefProjectToSaveFramesMapping:
                    nefWindow._nefTreeClickedCallback(itm, 0)
                    nefWindow.nefTreeView.setCurrentItem(itm)
                    break

        # NOTE:ED - temporary function to create a contentCompare from the two nef windows
        nefDictTuple = ()
        for obj, nefWindow in self._nefWindows.items():
            nefDictTuple += (nefWindow._nefDict,)
        if nefDictTuple:
            for obj, nefWindow in self._nefWindows.items():
                nefWindow._contentCompareDataBlocks = nefDictTuple

    def exec_(self) -> int:
        # NOTE:ED - this will do for the moment
        self.resize(*self._size)
        return super(ImportNefPopup, self).exec_()

    def _createContentCompare(self):
        pass

    def _okClicked(self):
        """Accept the dialog, set the selection list _selectedSaveFrames to the required items
        """
        if self._okButton.hasFocus():
            self._saveFrameSelection = list(self._nefWindows.values())[self._activeImportWindow].getItemsToImport()

            # set the collections to import in the nefImporter
            self._nefImporter.collections = list(self._nefWindows.values())[self._activeImportWindow]._collections

            for _window in self._nefWindows.values():
                _window.exitNefDictFrame()

        self.accept()


def main():
    """Testing code for the new nef manager
    """

    # from sandbox.Geerten.Refactored.framework import Framework
    # from sandbox.Geerten.Refactored.programArguments import Arguments

    from ccpn.framework.Framework import Framework
    from ccpn.framework.Application import Arguments

    _makeMainWindowVisible = False


    class MyProgramme(Framework):
        """My first app"""
        pass


    myArgs = Arguments()
    myArgs.interface = 'NoUi'
    myArgs.debug = True
    myArgs.darkColourScheme = False
    myArgs.lightColourScheme = True

    application = MyProgramme('MyProgramme', '3.0.1', args=myArgs)
    ui = application.ui
    ui.initialize(ui.mainWindow)  # ui.mainWindow not needed for refactored?

    if _makeMainWindowVisible:
        ui.mainWindow._updateMainWindow(newProject=True)
        ui.mainWindow.show()
        QtWidgets.QApplication.setActiveWindow(ui.mainWindow)

    # register the programme
    from ccpn.framework.Application import ApplicationContainer

    container = ApplicationContainer()
    container.register(application)
    application.useFileLogger = True

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # TESTNEF = '/Users/ejb66/Documents/nefTestProject.nef'
    # TESTNEF2 = '/Users/ejb66/Documents/nefTestProject0.nef'

    # TESTNEF = '/Users/ejb66/Documents/nefTestProject.nef'
    # TESTNEF2 = '/Users/ejb66/Documents/nefTestProject.nef'

    TESTNEF = '/Users/ejb66/Documents/CcpNmrData/nefTestProject.nef'
    TESTNEF2 = '/Users/ejb66/Documents/CcpNmrData/nefTestProject0.nef'

    # TESTNEF = '/Users/ejb66/Documents/TutorialProject2.nef'
    # TESTNEF2 = '/Users/ejb66/Documents/CcpNmrData/nefTestProject0.nef'

    # TESTNEF = '/Users/ejb66/Desktop/Ccpn_v2_testNef_a1.nef'
    # TESTNEF2 = '/Users/ejb66/Desktop/Ccpn_v2_testNef_a1.nef'

    # VALIDATEDICT = '/Users/ejb66/PycharmProjects/Git/AnalysisV3/src/python/ccpn/util/nef/NEF/specification/mmcif_nef_v1_1.dic'
    # VALIDATEDICT = '/Users/ejb66/Desktop/mmcif_nef_v1_1.dic'
    DEFAULTNAME = 'default'

    from ccpn.util.nef import NefImporter as Nef

    # load the file and the validate dict
    _loader = Nef.NefImporter(errorLogging=Nef.el.NEF_STRICT, hidePrefix=True)
    _loader.loadFile(TESTNEF)

    # load the file and the validate dict
    _loader2 = Nef.NefImporter(errorLogging=Nef.el.NEF_STRICT, hidePrefix=True)
    _loader2.loadFile(TESTNEF2)

    # validate
    valid = _loader.isValid
    if not valid:
        errLog = _loader.validErrorLog
        for k, val in errLog.items():
            if val:
                print(f'>>> {k} : {val}')

    valid = _loader2.isValid
    if not valid:
        errLog = _loader2.validErrorLog
        for k, val in errLog.items():
            if val:
                print(f'>>> {k} : {val}')

    # # simple test print of saveframes
    # names = _loader.getSaveFrameNames(returnType=Nef.NEF_RETURNALL)
    # for name in names:
    #     print(name)
    #     saveFrame = _loader.getSaveFrame(name)
    #     print(saveFrame)

    # create a list of which saveframes to load, with a parameters dict for each
    loadDict = {'nef_molecular_system'     : {},
                'nef_nmr_spectrum_cnoesy1' : {},
                'nef_chemical_shift_list_1': {},
                }

    # need a project
    name = _loader.getName()
    project = application.newProject(name or DEFAULTNAME)

    project.shiftAveraging = False

    nefReader = CcpnNefIo.CcpnNefReader(application)
    _loader._attachVerifier(nefReader.verifyProject)
    _loader._attachReader(nefReader.importExistingProject)
    _loader._attachContent(nefReader.contentNef)

    from ccpn.core.lib.ContextManagers import notificationEchoBlocking

    with notificationEchoBlocking():
        with catchExceptions(application=application, errorStringTemplate='Error loading Nef file: %s'):
            nefReader.setImportAll(True)
            _loader._importNef(project, _loader._nefDict, selection=None)

    nefReader.testPrint(project, _loader._nefDict, selection=None)
    nefReader.testErrors(project, _loader._nefDict, selection=None)

    app = QtWidgets.QApplication(['testApp'])
    # run the dialog
    dialog = ImportNefPopup(parent=ui.mainWindow, mainWindow=ui.mainWindow,
                            # nefObjects=(_loader,))
                            nefObjects=({NEFFRAMEKEY_IMPORT: project,
                                         },
                                        {NEFFRAMEKEY_IMPORT           : _loader2,
                                         NEFFRAMEKEY_ENABLECHECKBOXES : True,
                                         NEFFRAMEKEY_ENABLERENAME     : True,
                                         NEFFRAMEKEY_ENABLEFILTERFRAME: True,
                                         NEFFRAMEKEY_ENABLEMOUSEMENU  : True,
                                         NEFFRAMEKEY_PATHNAME         : TESTNEF2,
                                         }
                                        )
                            )

    dialog._initialiseProject(ui.mainWindow, application, project)
    dialog.fillPopup()
    dialog.setActiveNefWindow(1)

    # NOTE:ED - add routines here to set up the mapping between the different nef file loaded
    val = dialog.exec_()
    print(f'>>> dialog exit {val}')

    import ccpn.util.nef.nef as NefModule

    # NOTE:ED - by default pidList=None selects everything in the project
    # from ccpn.core.Chain import Chain
    # from ccpn.core.ChemicalShiftList import ChemicalShiftList
    # from ccpn.core.RestraintTable import RestraintTable
    # from ccpn.core.PeakList import PeakList
    # from ccpn.core.IntegralList import IntegralList
    # from ccpn.core.MultipletList import MultipletList
    # from ccpn.core._PeakCluster import _PeakCluster
    # from ccpn.core.Sample import Sample
    # from ccpn.core.Substance import Substance
    # from ccpn.core.NmrChain import NmrChain
    # from ccpn.core.StructureData import StructureData
    # from ccpn.core.Complex import Complex
    # from ccpn.core.SpectrumGroup import SpectrumGroup
    # from ccpn.core.Note import Note
    #
    # # set the items in the project that can be exported
    # checkList = [
    #     Chain._pluralLinkName,
    #     ChemicalShiftList._pluralLinkName,
    #     RestraintTable._pluralLinkName,
    #     PeakList._pluralLinkName,
    #     IntegralList._pluralLinkName,
    #     MultipletList._pluralLinkName,
    #     Sample._pluralLinkName,
    #     Substance._pluralLinkName,
    #     NmrChain._pluralLinkName,
    #     StructureData._pluralLinkName,
    #     Complex._pluralLinkName,
    #     SpectrumGroup._pluralLinkName,
    #     Note._pluralLinkName,
    #     _PeakCluster._pluralLinkName,
    #     ]
    # # build a complete list of items to grab from the project
    # pidList = []
    # for name in checkList:
    #     if hasattr(project, name):
    #         for obj in getattr(project, name):
    #             pidList.append(obj.pid)

    from ccpn.util.AttrDict import AttrDict

    options = AttrDict()
    options.identical = False
    options.ignoreCase = True
    options.almostEqual = True
    options.maxRows = 5
    options.places = 8

    nefWriter = CcpnNefIo.CcpnNefWriter(project)
    localNefDict = nefWriter.exportProject(expandSelection=True, includeOrphans=False, pidList=None)
    result = NefModule.compareDataBlocks(_loader._nefDict, localNefDict, options)
    # NefModule.printCompareList(result, 'LOADED', 'local', options)


if __name__ == '__main__':
    main()
