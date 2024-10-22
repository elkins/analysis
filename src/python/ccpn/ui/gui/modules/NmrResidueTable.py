"""
This file contains NmrResidueTableModule and NmrResidueTable classes

The NmrResidueModule allows for selection of displays, after which double-clicking a row 
navigates the displays to the relevant positions and marks the NmrAtoms of the selected 
NmrResidue.

Geerten 1-7/12/2016; 11/04/2017
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
__dateModified__ = "$dateModified: 2024-10-14 11:49:19 +0100 (Mon, October 14, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from ccpn.core.NmrChain import NmrChain
from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.lib import CcpnSorting
from ccpn.core.lib.DataFrameObject import DATAFRAME_OBJECT
from ccpn.core.lib.Notifiers import Notifier
from ccpn.ui.gui.widgets.PulldownListsForObjects import NmrChainPulldown
from ccpn.ui.gui.widgets.MessageDialog import showWarning, showYesNo
from ccpn.ui.gui.widgets.Column import ColumnClass
from ccpn.ui.gui.widgets.SettingsWidgets import StripPlot
from ccpn.ui.gui.modules.CcpnModule import CcpnTableModule
from ccpn.ui.gui.lib.StripLib import navigateToNmrResidueInDisplay, navigateToNmrAtomsInStrip, markNmrAtoms
from ccpn.ui.gui.lib._CoreTableFrame import _CoreTableWidgetABC, _CoreTableFrameABC
from ccpn.util.Logging import getLogger


logger = getLogger()

ALL = '<all>'
LINKTOPULLDOWNCLASS = 'linkToPulldownClass'
_MERGE_OPTION = 'Merge NmrResidues'
_EDIT_OPTION = 'Edit NmrResidue'
_MARK_OPTION = 'Mark Position'
_INTO = 'into'


#=========================================================================================
# NmrResidueTableModule
#=========================================================================================

class NmrResidueTableModule(CcpnTableModule):
    """This class implements the module by wrapping a NmrResidueTable instance
    """
    className = 'NmrResidueTableModule'
    includeSettingsWidget = True
    maxSettingsState = 2
    settingsPosition = 'left'

    includeDisplaySettings = False
    includePeakLists = False
    includeNmrChains = False
    includeSpectrumTable = False
    activePulldownClass = NmrChain
    activePulldownInitialState = False

    _allowRename = True

    # we are subclassing this Module, hence some more arguments to the init
    def __init__(self, mainWindow=None, name='NmrResidue Table',
                 nmrChain=None, selectFirstItem=False):
        """Initialise the Module widgets
        """
        super().__init__(mainWindow=mainWindow, name=name)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = self.project = self.current = None

        # set the widgets and callbacks
        self._setWidgets(self.settingsWidget, self.mainWidget, nmrChain, selectFirstItem)
        self._setCallbacks()

    def _setWidgets(self, settingsWidget, mainWidget, nmrChain, selectFirstItem):
        """Set up the widgets for the module
        """
        # add to settings widget
        self.nmrResidueTableSettings = StripPlot(parent=settingsWidget, mainWindow=self.mainWindow,
                                                 includeDisplaySettings=self.includeDisplaySettings,
                                                 includePeakLists=self.includePeakLists,
                                                 includeNmrChains=self.includeNmrChains,
                                                 includeSpectrumTable=self.includeSpectrumTable,
                                                 activePulldownClass=self.activePulldownClass,
                                                 activePulldownInitialState=self.activePulldownInitialState,
                                                 grid=(0, 0))

        # add the frame containing the pulldown and table
        self._mainFrame = NmrResidueTableFrame(parent=mainWidget,
                                               mainWindow=self.mainWindow,
                                               moduleParent=self,
                                               nmrChain=nmrChain, selectFirstItem=selectFirstItem,
                                               grid=(0, 0))

        # link the table to the mainWidget - needs refactoring
        self._mainFrame._tableWidget._autoClearMarksCheckBox = self.nmrResidueTableSettings.autoClearMarksWidget.checkBox
        self._mainFrame.nmrResidueTableSettings = self.nmrResidueTableSettings

    @property
    def tableFrame(self):
        """Return the table frame
        """
        return self._mainFrame

    @property
    def _tableWidget(self):
        """Return the table widget in the table frame
        """
        return self._mainFrame._tableWidget

    def _setCallbacks(self):
        """Set the active callbacks for the module
        """
        if self.activePulldownClass:
            self._setCurrentPulldown = Notifier(self.current,
                                                [Notifier.CURRENT],
                                                targetName=self.activePulldownClass._pluralLinkName,
                                                callback=self._mainFrame._selectCurrentPulldownClass)

            # set the active callback from the pulldown
            self._mainFrame.setActivePulldownClass(coreClass=self.activePulldownClass,
                                                   checkBox=getattr(self.nmrResidueTableSettings, LINKTOPULLDOWNCLASS,
                                                                    None))

        # set the dropped callback through mainWidget
        self.mainWidget._dropEventCallback = self._mainFrame._processDroppedItems

    def selectTable(self, table):
        """Select the object in the table
        """
        self._mainFrame.selectTable(table)

    def _closeModule(self):
        if self.activePulldownClass:
            if self._setCurrentPulldown:
                self._setCurrentPulldown.unRegister()
            if self.nmrResidueTableSettings:
                self.nmrResidueTableSettings._cleanupWidget()
        if self.tableFrame:
            self.tableFrame._cleanupWidget()
        super()._closeModule()


KD = 'Kd'
Deltas = 'Ddelta'


#=========================================================================================
# _NewNmrResidueTableWidget
#=========================================================================================

class _NewNmrResidueTableWidget(_CoreTableWidgetABC):
    """Class to present a nmrResidue Table
    """
    className = '_NewNmrResidueTableWidget'
    attributeName = 'nmrChains'

    defaultHidden = ['Pid', 'NmrChain']
    _internalColumns = ['isDeleted', '_object']  # columns that are always hidden
    _INDEX = 'Index'

    # define self._columns here
    columnHeaders = {}
    tipTexts = ()

    # define the notifiers that are required for the specific table-type
    tableClass = NmrChain
    rowClass = NmrResidue
    cellClass = None
    tableName = tableClass.className
    rowName = rowClass.className
    cellClassNames = {NmrAtom: 'nmrResidue'}  # , _OldChemicalShift: 'nmrAtom'}
    selectCurrent = True
    callBackClass = NmrResidue
    search = False

    # set the queue handling parameters
    _maximumQueueLength = 25

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _sourceObjects(self):
        """Get/set the list of source objects
        """
        return (self._table and self._table.nmrResidues) or []

    @_sourceObjects.setter
    def _sourceObjects(self, value):
        # shouldn't need this
        self._table.nmrResidues = value

    @property
    def _sourceCurrent(self):
        """Get/set the associated list of current objects
        """
        return self.current.nmrResidues

    @_sourceCurrent.setter
    def _sourceCurrent(self, value):
        if value:
            self.current.nmrResidues = value
        else:
            self.current.clearNmrResidues()

    #=========================================================================================
    # Selection/Action callbacks
    #=========================================================================================

    def _updateTableCallback(self, data):
        pass

    def actionCallback(self, selection, lastItem):
        """If current strip contains the double-clicked peak will navigateToPositionInStrip
        """
        from ccpn.ui.gui.lib.StripLib import _getCurrentZoomRatio

        try:
            if not (objs := list(lastItem[self._OBJECT])):
                return
        except Exception as es:
            getLogger().debug2(f'{self.__class__.__name__}.actionCallback: No selection\n{es}')
            return

        nmrResidue = objs[0] if isinstance(objs, (list, tuple)) else objs

        if self.current.strip is not None:
            self.application.ui.mainWindow.clearMarks()
            strip = self.current.strip
            newWidths = _getCurrentZoomRatio(strip.viewRange())
            navigateToNmrResidueInDisplay(nmrResidue, strip.spectrumDisplay, stripIndex=0,
                                          widths=None)
            # widths=['default'] * len(strip.axisCodes))

        else:
            logger.warning('Impossible to navigate to position. Set a current strip first')

    #=========================================================================================
    # Create table and row methods
    #=========================================================================================

    def getCellToRows(self, cellItem, attribute=None):
        """Get the list of objects which cellItem maps to for this table
        To be subclassed as required
        """
        # classItem is usually a type such as PeakList, MultipletList
        # with an attribute such as peaks/peaks
        try:
            return [cellItem._oldNmrResidue] if cellItem.isDeleted else [cellItem.nmrResidue], Notifier.CHANGE
        except Exception:
            # this USUALLY happens when an offsetNmrResidue is deleted, not spotted any other cases yet
            #   shouldn't be an issue as the nmrResidue should already have been removed from the table
            return [], Notifier.CHANGE

    #=========================================================================================
    # Table context menu
    #=========================================================================================

    def addTableMenuOptions(self, menu):
        """Add options to the right-mouse menu
        """
        super(_NewNmrResidueTableWidget, self).addTableMenuOptions(menu)

        # add extra items to the menu
        self._mergeMenuAction = menu.addAction(_MERGE_OPTION, self._mergeNmrResidues)
        self._editMenuAction = menu.addAction(_EDIT_OPTION, self._editNmrResidue)
        self._markMenuAction = menu.addAction(_MARK_OPTION, self._markNmrResidue)

        if (_actions := menu.actions()):
            _topMenuItem = _actions[0]
            _topSeparator = menu.insertSeparator(_topMenuItem)

            # move new actions to the top of the list
            menu.insertAction(_topSeparator, self._markMenuAction)
            menu.insertAction(self._markMenuAction, self._mergeMenuAction)
            menu.insertAction(self._mergeMenuAction, self._editMenuAction)

    def setTableMenuOptions(self, menu):
        """Update options in the right-mouse menu
        """
        super(_NewNmrResidueTableWidget, self).setTableMenuOptions(menu)

        selection = self.getSelectedObjects()
        data = self.getRightMouseItem()
        if data is not None and not data.empty:
            currentNmrResidue = data.get(DATAFRAME_OBJECT)

            selection = selection or []
            _check = (currentNmrResidue and (1 < len(selection) < 5) and currentNmrResidue in selection)
            _option = f' {_INTO} {currentNmrResidue.id if currentNmrResidue else ""}' if _check else ''
            self._mergeMenuAction.setText(f'{_MERGE_OPTION} {_option}')
            self._mergeMenuAction.setEnabled(_check)

            self._editMenuAction.setText(f'{_EDIT_OPTION} {currentNmrResidue.id if currentNmrResidue else ""}')
            self._editMenuAction.setEnabled(True if currentNmrResidue else False)

        else:
            # disabled but visible lets user know that menu items exist
            self._mergeMenuAction.setText(_MERGE_OPTION)
            self._mergeMenuAction.setEnabled(False)
            self._editMenuAction.setText(_EDIT_OPTION)
            self._editMenuAction.setEnabled(False)

    def _mergeNmrResidues(self):
        """Merge the nmrResidues in the selection into the nmrResidue that has been right-clicked
        """
        selection = self.getSelectedObjects()
        data = self.getRightMouseItem()
        if data is not None and not data.empty and selection:
            currentNmrResidue = data.get(DATAFRAME_OBJECT)
            matching = [ch for ch in selection if ch and ch != currentNmrResidue]
            if len(matching):
                yesNo = showYesNo('Merge NmrResidues',
                                  "Do you want to merge\n"
                                  "{}   into   {}".format('\n'.join([ss.id for ss in matching]),
                                                          currentNmrResidue.id),
                                  dontShowEnabled=True,
                                  defaultResponse=True,
                                  popupId=f'{self.__class__.__name__}Merge')
                if yesNo:
                    currentNmrResidue.mergeNmrResidues(matching)

    def _editNmrResidue(self):
        """Show the edit nmrResidue popup for the clicked nmrResidue
        """
        data = self.getRightMouseItem()
        if data is not None and not data.empty:
            currentNmrResidue = data.get(DATAFRAME_OBJECT)

            if currentNmrResidue:
                from ccpn.ui.gui.popups.NmrResiduePopup import NmrResidueEditPopup

                popup = NmrResidueEditPopup(parent=self.mainWindow, mainWindow=self.mainWindow, obj=currentNmrResidue)
                popup.exec_()

    def _markNmrResidue(self):
        """Mark the position of the nmrResidue
        """
        data = self.getRightMouseItem()
        if data is not None and not data.empty:
            currentNmrResidue = data.get(DATAFRAME_OBJECT)

            if currentNmrResidue:

                # optionally clear the marks
                # if self.moduleParent.nmrResidueTableSettings.autoClearMarksWidget.checkBox.isChecked():
                if self._autoClearMarksCheckBox.isChecked():
                    self.mainWindow.clearMarks()

                markNmrAtoms(self.mainWindow, currentNmrResidue.nmrAtoms)

    def buildTableDataFrame(self):
        # create a simple speed-cache for the current nmrResidue indexing
        self._caching = True
        self._objCache = None

        result = super().buildTableDataFrame()

        self._caching = False
        self._objCache = None

        return result

    #=========================================================================================
    # Table functions
    #=========================================================================================

    def _getTableColumns(self, nmrChain=None):
        """format of column = ( Header Name, value, tipText, editOption)
        editOption allows the user to modify the value content by doubleclick
        """
        cols = ColumnClass([
            ('#', lambda nmrResidue: nmrResidue.serial, 'NmrResidue serial number', None, None),
            ('Index', lambda nmrResidue: self._nmrIndex(nmrResidue), 'Index of NmrResidue in the NmrChain', None, None),
            # ('Index', lambda nmrResidue: NmrResidueTable._nmrLamInt(nmrResidue, 'Index'), 'Index of NmrResidue in the NmrChain', None, None),

            # ('Index',      lambda nmrResidue: nmrResidue.nmrChain.nmrResidues.index(nmrResidue), 'Index of NmrResidue in the NmrChain', None, None),
            # ('NmrChain',   lambda nmrResidue: nmrResidue.nmrChain.id, 'NmrChain id', None, None),
            ('Pid', lambda nmrResidue: nmrResidue.pid, 'Pid of NmrResidue', None, None),
            ('_object', lambda nmrResidue: nmrResidue, 'Object', None, None),
            ('NmrChain', lambda nmrResidue: nmrResidue.nmrChain.id, 'NmrChain containing the nmrResidue', None, None),
            # just add the nmrChain for clarity
            ('Sequence', lambda nmrResidue: nmrResidue.sequenceCode, 'Sequence code of NmrResidue', None, None),
            ('Type', lambda nmrResidue: nmrResidue.residueType, 'NmrResidue type', None, None),
            ('NmrAtoms', lambda nmrResidue: self._getNmrAtomNames(nmrResidue), 'NmrAtoms in NmrResidue', None, None),
            ('Peak count', lambda nmrResidue: '%3d ' % self._getNmrResiduePeakCount(nmrResidue),
             'Number of peaks assigned to NmrResidue', None, None),
            ('Comment', lambda nmr: self._getCommentText(nmr), 'Notes',
             lambda nmr, value: self._setComment(nmr, value), None)
            ])

        return cols

    #=========================================================================================
    # Updates
    #=========================================================================================

    #=========================================================================================
    # object properties
    #=========================================================================================

    # @staticmethod
    def _nmrIndex(self, nmrRes):
        """CCPN-INTERNAL: Insert an index into ObjectTable
        """
        try:
            if getattr(self, '_caching', False):
                if self._objCache is None:
                    self._objCache = [id(pp) for pp in nmrRes.nmrChain.nmrResidues]
                return self._objCache.index(id(nmrRes))

            else:
                from ccpnc.clibrary import Clibrary

                _getNmrIndex = Clibrary.getNmrResidueIndex

                return _getNmrIndex(nmrRes)
                # return nmrRes.nmrChain.nmrResidues.index(nmrRes)  # ED: THIS IS VERY SLOW
        except Exception:
            return None

    @staticmethod
    def _nmrLamInt(row, name):
        """CCPN-INTERNAL: Insert an int into ObjectTable
        """
        try:
            return int(getattr(row, name))
        except Exception:
            return None

    @staticmethod
    def _getNmrAtomNames(nmrResidue):
        """Returns a sorted list of NmrAtom names
        """
        return ', '.join(sorted({atom.name for atom in nmrResidue.nmrAtoms if not atom.isDeleted},
                                key=CcpnSorting.stringSortKey))

    @staticmethod
    def _getNmrResiduePeakCount(nmrResidue):
        """Returns peak list count
        """
        l1 = [peak for atom in nmrResidue.nmrAtoms if not atom.isDeleted for peak in atom.assignedPeaks if
              not peak.isDeleted]
        return len(set(l1))


#=========================================================================================
# NmrResidueTableFrame
#=========================================================================================

class NmrResidueTableFrame(_CoreTableFrameABC):
    """Frame containing the pulldown and the table widget
    """
    _TableKlass = _NewNmrResidueTableWidget
    _PulldownKlass = NmrChainPulldown

    def __init__(self, parent, mainWindow=None, moduleParent=None,
                 nmrChain=None, selectFirstItem=False, **kwds):
        super().__init__(parent, mainWindow=mainWindow, moduleParent=moduleParent,
                         obj=nmrChain, selectFirstItem=selectFirstItem, **kwds)

        self._tableWidget.setActionCallback(self.navigateToNmrResidueCallBack)

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _tableCurrent(self):
        """Return the list of source objects, e.g., _table.peaks/_table.nmrResidues
        """
        return self.current.nmrChain

    @_tableCurrent.setter
    def _tableCurrent(self, value):
        self.current.nmrChain = value

    def navigateToNmrResidueCallBack(self, selection, lastItem):
        """Navigate in selected displays to nmrResidue; skip if none defined
        """
        try:
            if not (objs := list(lastItem[self._tableWidget._OBJECT])):
                return
        except Exception as es:
            getLogger().debug2(f'{self.__class__.__name__}.navigateToNmrResidueCallBack: No selection\n{es}')
            return

        nmrResidue = objs[0] if isinstance(objs, (tuple, list)) else objs
        if nmrResidue is None or nmrResidue.isDeleted:
            return

        logger.debug(f'nmrResidue={str(nmrResidue.id if nmrResidue else None)}')
        displays = []
        if self.nmrResidueTableSettings.displaysWidget:
            displays = self.nmrResidueTableSettings.displaysWidget.getDisplays()
        elif self.current.strip:
            displays = [self.current.strip.spectrumDisplay]

        if not displays and self.nmrResidueTableSettings.displaysWidget:
            logger.warning('Undefined display module(s); select in settings first')
            showWarning('startAssignment', 'Undefined display module(s);\nselect in settings first')
            return

        from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar

        with undoBlockWithoutSideBar():
            # optionally clear the marks
            if self.nmrResidueTableSettings.autoClearMarksWidget.checkBox.isChecked():
                self.application.ui.mainWindow.clearMarks()

            newWidths = []

            # follow the previous/next nmrResidues to navigate to the correct position
            offset = nmrResidue.relativeOffset
            nmrResidue = nmrResidue.mainNmrResidue
            if offset is not None:
                if offset < 0:
                    for _next in range(-offset):
                        _adjacent = nmrResidue.previousNmrResidue
                        if not (_adjacent and _adjacent.mainNmrResidue):
                            break
                        nmrResidue = _adjacent.mainNmrResidue

                elif offset > 0:
                    for _next in range(offset):
                        _adjacent = nmrResidue.nextNmrResidue
                        if not (_adjacent and _adjacent.mainNmrResidue):
                            break
                        nmrResidue = _adjacent.mainNmrResidue

            for specDisplay in displays:
                if ((optDict := self.nmrResidueTableSettings.axisCodeOptionsDict) and
                        (options := optDict.get(f'{specDisplay}')) and
                        specDisplay.axes):
                    # use a mask if specified in displays-to-pick
                    axisMask = self.axisMaskFromAxisCode(specDisplay.axes, options)
                else:
                    axisMask = None

                if self.current.strip in specDisplay.strips:
                    # just navigate to this strip
                    navigateToNmrAtomsInStrip(self.current.strip,
                                              nmrResidue.nmrAtoms,
                                              widths=newWidths,
                                              markPositions=self.nmrResidueTableSettings.markPositionsWidget.checkBox.isChecked(),
                                              setNmrResidueLabel=True,
                                              axisMask=axisMask
                                              )

                else:
                    #navigate to the specDisplay (and remove excess strips)
                    if len(specDisplay.strips) > 0:
                        newWidths = []
                        navigateToNmrResidueInDisplay(nmrResidue, specDisplay, stripIndex=0,
                                                      widths=newWidths,  #['full'] * len(display.strips[0].axisCodes),
                                                      showSequentialResidues=(len(specDisplay.axisCodes) > 2) and
                                                                             self.nmrResidueTableSettings.sequentialStripsWidget.checkBox.isChecked(),
                                                      markPositions=self.nmrResidueTableSettings.markPositionsWidget.checkBox.isChecked(),
                                                      axisMask=axisMask
                                                      )

                # open the other headers to match
                for strip in specDisplay.strips:
                    if strip != self.current.strip and not strip.header.headerVisible:
                        strip.header.reset()
                        strip.header.headerVisible = True

    @staticmethod
    def axisMaskFromAxisCode(axes, axisCode) -> list:
        """Create a mask for axes based on which are ticked in settings"""
        return [True if num in axisCode else None for num, axis in enumerate(axes)]


#=========================================================================================
# _NewCSMNmrResidueTable
#=========================================================================================

class _NewCSMNmrResidueTableWidget(_NewNmrResidueTableWidget):
    """Custom nmrResidue Table with extra columns used in the ChemicalShiftsMapping Module
    """
    className = '_NewCSMNmrResidueTableWidget'

    def setCheckBoxCallback(self, checkBoxCallback):
        # enable callback on the checkboxes
        self._checkBoxCallback = checkBoxCallback

    #=========================================================================================
    # Table functions
    #=========================================================================================

    def _getTableColumns(self, nmrChain):
        """format of column = ( Header Name, value, tipText, editOption)
        editOption allows the user to modify the value content by doubleclick
        """
        cols = ColumnClass([
            ('#', lambda nmrResidue: nmrResidue.serial, 'NmrResidue serial number', None, None),
            ('Pid', lambda nmrResidue: nmrResidue.pid, 'Pid of NmrResidue', None, None),
            ('_object', lambda nmrResidue: nmrResidue, 'Object', None, None),
            ('Index', lambda nmrResidue: self._nmrIndex(nmrResidue), 'Index of NmrResidue in the NmrChain', None, None),
            ('Sequence', lambda nmrResidue: nmrResidue.sequenceCode, 'Sequence code of NmrResidue', None, None),
            ('Type', lambda nmrResidue: nmrResidue.residueType, 'NmrResidue type', None, None),
            ('Selected', lambda nmrResidue: self._getSelectedNmrAtomNames(nmrResidue),
             'NmrAtoms selected in NmrResidue', None, None),
            ('Spectra', lambda nmrResidue: self._getNmrResidueSpectraCount(nmrResidue),
             'Number of spectra selected for calculating the deltas', None, None),
            (Deltas, lambda nmrResidue: nmrResidue._delta, '', None, None),
            (KD, lambda nmrResidue: nmrResidue._estimatedKd, '', None, None),
            ('Include', lambda nmrResidue: nmrResidue._includeInDeltaShift,
             'Include this residue in the Mapping calculation',
             lambda nmr, value: self._setChecked(nmr, value), None),
            # ('Flag', lambda nmrResidue: nmrResidue._flag,  '',  None, None),
            ('Comment', lambda nmr: self._getCommentText(nmr), 'Notes', lambda nmr, value: self._setComment(nmr, value),
             None)
            ])  #[Column(colName, func, tipText=tipText, setEditValue=editValue, format=columnFormat)

        return cols

    #=========================================================================================
    # object properties
    #=========================================================================================

    @staticmethod
    def _setChecked(obj, value):
        """CCPN-INTERNAL: Insert a comment into GuiTable
        """
        obj._includeInDeltaShift = value
        obj._finaliseAction('change')

    @staticmethod
    def _getNmrResidueSpectraCount(nmrResidue):
        """CCPN-INTERNAL: Insert an index into ObjectTable
        """
        try:
            return nmrResidue.spectraCount
        except Exception:
            return None

    @staticmethod
    def _getSelectedNmrAtomNames(nmrResidue):
        """CCPN-INTERNAL: Insert an index into ObjectTable
        """
        try:
            return ', '.join(nmrResidue.selectedNmrAtomNames)
        except Exception:
            return None

    def _selectPullDown(self, value):
        """Used for automatic restoring of widgets
        """
        self.moduleParent._modulePulldown.select(value)
        try:
            if self.chemicalShiftsMappingModule is not None:
                self.chemicalShiftsMappingModule._updateModule()
        except Exception as es:
            getLogger().warning(f'Impossible update chemicalShiftsMappingModule from restoring {es}')


#=========================================================================================
# NmrResidueTableFrame
#=========================================================================================

class _CSMNmrResidueTableFrame(NmrResidueTableFrame):
    """Frame containing the pulldown and the table widget
    """
    _TableKlass = _NewCSMNmrResidueTableWidget


#=========================================================================================
# main
#=========================================================================================

def main():
    """Show the NmrResidueTable module
    """
    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # create a new test application
    app = newTestApplication(interface='Gui')
    application = getApplication()
    mainWindow = application.ui.mainWindow

    # add a module
    _module = NmrResidueTableModule(mainWindow=mainWindow)
    mainWindow.moduleArea.addModule(_module)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    """Call the test function
    """
    main()
