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
__dateModified__ = "$dateModified: 2024-09-20 19:28:10 +0100 (Fri, September 20, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from collections import OrderedDict

from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.RestraintTable import RestraintTable
from ccpn.core.Restraint import Restraint
from ccpn.ui.gui.modules.CcpnModule import CcpnTableModule
from ccpn.ui.gui.widgets.Column import ColumnClass
from ccpn.ui.gui.widgets.PulldownListsForObjects import RestraintTablePulldown
from ccpn.ui.gui.widgets.SettingsWidgets import SpectrumDisplaySelectionWidget
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.ui.gui.widgets.SettingsWidgets import ModuleSettingsWidget
from ccpn.ui.gui.widgets.table._TableAdditions import TableMenuABC

import ccpn.ui.gui.modules.PyMolUtil as pyMolUtil
from ccpn.ui.gui.lib._CoreTableFrame import _CoreTableWidgetABC, _CoreTableFrameABC

from ccpn.util.Common import makeIterableList
from ccpn.util.Path import fetchDir, joinPath
from ccpn.util.Logging import getLogger


logger = getLogger()
ALL = '<all>'
LINKTOPULLDOWNCLASS = 'linkToPulldownClass'
PymolScriptName = 'Restraint_Pymol_Template.py'
_DISPLAYS = 'Displays'
_MARKPOSITIONS = 'markPositions'
_AUTOCLEARMARKS = 'autoClearMarks'


#=========================================================================================
# CORRECT TABLE
#=========================================================================================

class RestraintTableModule(CcpnTableModule):
    """Class implements the module by wrapping a restaintTable instance.
    """
    className = 'RestraintTableModule'
    includeSettingsWidget = True
    maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    settingsPosition = 'left'

    includeRestraintTables = False
    includeNmrChains = False
    includeSpectrumTable = False

    activePulldownClass = RestraintTable
    _allowRename = True

    # we are subclassing this Module, hence some more arguments to the init
    def __init__(self, mainWindow=None, name=f'{RestraintTable.className}',
                 restraintTable=None, selectFirstItem=True):
        """Initialise the Module widgets.
        """
        super().__init__(mainWindow=mainWindow, name=name)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
            self.scriptsPath = self.application.scriptsPath
            self.pymolScriptsPath = fetchDir(self.scriptsPath, 'pymol')
        else:
            self.application = self.project = self.current = None

        # set the widgets and callbacks
        self._setWidgets(self.settingsWidget, self.mainWidget, restraintTable, selectFirstItem)
        self._setCallbacks()

    def _setWidgets(self, settingsWidget, mainWidget, restraintTable, selectFirstItem):
        """Set up the widgets for the module
        """
        # add the settings widgets defined from the following orderedDict
        # need to make this more accessible
        settingsDict = OrderedDict(((_DISPLAYS, {'label'   : '',
                                                 'tipText' : '',
                                                 'callBack': None,  #self.restraintTablePulldown,
                                                 'enabled' : True,
                                                 '_init'   : None,
                                                 'type'    : SpectrumDisplaySelectionWidget,
                                                 'kwds'    : {'texts'      : [],
                                                              'displayText': [],
                                                              'defaults'   : [],
                                                              'objectName' : 'SpectrumDisplaysSelection'},
                                                 #objectName is used to save to layout
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
                                                    'checked' : False,
                                                    '_init'   : None,
                                                    }),
                             )))
        settings = self._settings = ModuleSettingsWidget(parent=settingsWidget, mainWindow=self.mainWindow,
                                                         settingsDict=settingsDict,
                                                         grid=(0, 0))

        # add the frame containing the pulldown and table
        self._mainFrame = _RestraintTableFrame(parent=mainWidget,
                                               mainWindow=self.mainWindow,
                                               moduleParent=self,
                                               restraintTable=restraintTable, selectFirstItem=selectFirstItem,
                                               grid=(0, 0))

        # get the widgets from the settings
        self._displaysWidget = settings.getWidget(_DISPLAYS)
        self._markPositions = settings.getWidget(_MARKPOSITIONS)
        self._autoClearMarks = settings.getWidget(_AUTOCLEARMARKS)

    @property
    def tableFrame(self):
        """Return the table-frame.
        """
        return self._mainFrame

    @property
    def _tableWidget(self):
        """Return the table widget in the table-frame.
        """
        return self._mainFrame._tableWidget

    def _setCallbacks(self):
        """Set the active callbacks for the module.
        """
        if self.activePulldownClass:
            self.setNotifier(self.current,
                             [Notifier.CURRENT],
                             targetName=self.activePulldownClass._pluralLinkName,
                             callback=self._mainFrame._selectCurrentPulldownClass)

            # set the active callback from the pulldown
            self._mainFrame.setActivePulldownClass(coreClass=self.activePulldownClass,
                                                   checkBox=self._settings.checkBoxes[LINKTOPULLDOWNCLASS]['widget'])

        # set the dropped callback through mainWidget
        self.mainWidget._dropEventCallback = self._mainFrame._processDroppedItems

    def selectTable(self, table):
        """Select the object in the table.
        """
        self._mainFrame.selectTable(table)

    def selectPeaks(self, peaks):
        """Select the peaks in the table.
        """
        pids = self.project.getPidsByObjects(peaks)
        self._mainFrame.guiTable.selectRowsByValues(pids, 'Pid')

    def _closeModule(self):
        """CCPN-INTERNAL: used to close the module.
        """
        if self.activePulldownClass:
            if self._settings:
                self._settings._cleanupWidget()
        if self.tableFrame:
            self.tableFrame._cleanupWidget()

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
            getLogger().debug2(f'Could not remove the pulldown state from PeakTable module. {err}')
        return widgetsState


#=========================================================================================
# Restraint table menu
#=========================================================================================


class _RestraintTableOptions(TableMenuABC):
    """Class to handle restraint-table options from a right-mouse menu.
    Not required at this time.
    """

    def addMenuOptions(self, menu):
        """Add options to the right-mouse menu
        """
        ...

    def setMenuOptions(self, menu):
        """Update options in the right-mouse menu
        """
        ...

    #=========================================================================================
    # Properties
    #=========================================================================================

    ...

    #=========================================================================================
    # Class methods
    #=========================================================================================

    ...

    #=========================================================================================
    # Implementation
    #=========================================================================================

    ...


#=========================================================================================
# _NewRestraintTableWidget
#=========================================================================================

class _NewRestraintTableWidget(_CoreTableWidgetABC):
    """Class to present a restraintTable Table
    """
    className = '_NewRestraintTableWidget'
    attributeName = 'restraintTables'

    defaultHidden = ['Pid']
    _internalColumns = ['isDeleted', '_object']

    # define self._columns here
    columnHeaders = {'#'           : '#',
                     'Pid'         : 'Pid',
                     '_object'     : '_object',
                     'Atoms'       : 'Atoms',
                     'Target Value': 'Target Value',
                     'Upper Limit' : 'Upper Limit',
                     'Lower Limit' : 'Lower Limit',
                     'Error'       : 'Error',
                     'Peaks'       : 'Peaks',
                     'Comment'     : 'Comment',
                     }

    tipTexts = ('Restraint Id',
                'Pid of the Restraint',
                'Object',
                'Atoms defining the restraint',
                'Target value for the restraint',
                'Upper limit for the restraint',
                'Lower limit for the restraint',
                'Error on the restraint',
                'Number of peaks used to derive the restraint',
                'Optional user comment'
                )

    # define the notifiers that are required for the specific table-type
    tableClass = RestraintTable
    rowClass = Restraint
    cellClass = None
    tableName = tableClass.className
    rowName = rowClass.className
    cellClassNames = None
    selectCurrent = True
    callBackClass = Restraint
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
        return (self._table and self._table.restraints) or []

    @_sourceObjects.setter
    def _sourceObjects(self, value):
        # shouldn't need this
        self._table.restraints = value

    @property
    def _sourceCurrent(self):
        """Get/set the associated list of current objects
        """
        return self.current.restraints

    @_sourceCurrent.setter
    def _sourceCurrent(self, value):
        if value:
            self.current.restraints = value
        else:
            self.current.clearRestraints()

    #=========================================================================================
    # Widget callbacks
    #=========================================================================================

    def actionCallback(self, selection, lastItem):
        """Notifier DoubleClick action on item in table
        """
        from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar
        from ccpn.ui.gui.lib.StripLib import _getCurrentZoomRatio, navigateToPositionInStrip

        try:
            if not (objs := list(lastItem[self._OBJECT])):
                return
        except Exception as es:
            getLogger().debug2(f'{self.__class__.__name__}.actionCallback: No selection\n{es}')
            return
        restraint = objs[0] if isinstance(objs, (tuple, list)) else objs

        self.current.peaks = restraint.peaks
        pk = restraint.peaks[0]
        displays = self.moduleParent._displaysWidget.getDisplays()
        autoClear = self.moduleParent._autoClearMarks.isChecked()
        markPositions = self.moduleParent._markPositions.isChecked()

        with undoBlockWithoutSideBar():
            # optionally clear the marks
            if autoClear:
                self.mainWindow.clearMarks()
            # navigate the displays
            for display in displays:
                if display and len(display.strips) > 0 and display.strips[0].spectrumViews:
                    widths = None
                    if pk.spectrum.dimensionCount <= 2:
                        widths = _getCurrentZoomRatio(display.strips[0].viewRange())
                    navigateToPositionInStrip(strip=display.strips[0],
                                              positions=pk.position,
                                              axisCodes=pk.axisCodes,
                                              widths=widths)
                    if markPositions:
                        display.strips[0]._markSelectedPeaks()

    #=========================================================================================
    # Create table and row methods
    #=========================================================================================

    def getCellToRows(self, cellItem, attribute=None):
        """Get the list of objects which cellItem maps to for this table
        To be subclassed as required
        """
        # this is a step towards making guiTableABC and subclass for each table
        # return makeIterableList(getattr(cellItem, attribute, [])), Notifier.CHANGE

        return makeIterableList(cellItem._oldAssignedRestraints) if cellItem.isDeleted \
            else makeIterableList(cellItem.assignedRestraints), \
            Notifier.CHANGE

    def _updateTableCallback(self, data):
        """Respond to table notifier.
        """
        obj = data[Notifier.OBJECT]
        if obj != self._table:
            # discard the wrong object
            return

        self._update()

    #=========================================================================================
    # Table context menu
    #=========================================================================================

    # currently in _RestraintTableOptions

    ...

    #=========================================================================================
    # Table functions
    #=========================================================================================

    def _getTableColumns(self, restraintTable=None):
        """Add default columns plus the ones according to restraintTable.spectrum dimension
        format of column = ( Header Name, value, tipText, editOption)
        editOption allows the user to modify the value content by doubleclick
        """
        # create the column objects
        columnDefs = [('#', '_key', 'Restraint Id', None, None),
                      ('Pid', lambda restraint: restraint.pid, 'Pid of integral', None, None),
                      ('_object', lambda restraint: restraint, 'Object', None, None),
                      ('Atoms', lambda restraint: self._getContributions(restraint),
                       'Atoms involved in the restraint', None, None),
                      ('Target Value', 'targetValue', 'Target value for the restraint', None, None),
                      ('Upper Limit', 'upperLimit', 'Upper limit for the restraint', None, None),
                      ('Lower Limit', 'lowerLimit', 'Lower limit or the restraint', None, None),
                      ('Error', 'error', 'Error on the restraint', None, None),
                      ('Peaks', lambda restraint: '%3d ' % self._getRestraintPeakCount(restraint),
                       'Number of peaks used to derive this restraint', None, None),
                      ('Comment', lambda restraint: self._getCommentText(restraint), 'Notes',
                       lambda restraint, value: self._setComment(restraint, value), None)
                      ]  # [Column(colName, func, tipText=tipText, setEditValue=editValue, format=columnFormat)
        colDefs = ColumnClass(columnDefs)

        return colDefs

    #=========================================================================================
    # Updates
    #=========================================================================================

    ...

    #=========================================================================================
    # Widgets callbacks
    #=========================================================================================

    ...

    #=========================================================================================
    # object properties
    #=========================================================================================

    @staticmethod
    def _getContributions(restraint):
        """
        CCPN-INTERNAL:  Get the first pair of atoms Ids from the first restraintContribution of a restraint.
        Empty str if not atoms.
        """
        atomPair = _NewRestraintTableWidget.getFirstRestraintAtomsPair(restraint)
        if atomPair and None not in atomPair:
            return ' - '.join([a.id for a in atomPair])
        else:
            return ''

    @staticmethod
    def getFirstRestraintAtomsPair(restraint):
        """ Get the first pair of atoms from the first restraintContribution of a restraint."""
        atomPair = []
        if len(restraint.restraintContributions) > 0 and len(restraint.restraintContributions[0].restraintItems) > 0:
            atomPair = [restraint.project.getAtom(x) for x in restraint.restraintContributions[0].restraintItems[0]]
            if all(atomPair):
                return atomPair

        return atomPair

    @staticmethod
    def _getRestraintPeakCount(restraint):
        """
        CCPN-INTERNAL: Return number of peaks assigned to NmrAtom in Experiments and RestraintTables
        using ChemicalShiftList
        """
        return len(peaks) if (peaks := restraint.peaks) else 0


#=========================================================================================
# RestraintTableFrame
#=========================================================================================

class _RestraintTableFrame(_CoreTableFrameABC):
    """Frame containing the pulldown, the table-widget
    and any extra buttons in the frame header.
    """
    _TableKlass = _NewRestraintTableWidget
    _PulldownKlass = RestraintTablePulldown

    def __init__(self, parent, mainWindow=None, moduleParent=None,
                 restraintTable=None, selectFirstItem=False, **kwds):
        super().__init__(parent, mainWindow=mainWindow, moduleParent=moduleParent,
                         obj=restraintTable, selectFirstItem=selectFirstItem, **kwds)

        # create widget for the pyMol viewer
        self.showOnViewerButton = Button(parent=self, tipText='Show on Molecular Viewer',
                                         icon=Icon('icons/showStructure'),
                                         callback=self._showOnMolecularViewer,
                                         hAlign='l')
        self.addWidgetToTop(self.showOnViewerButton, 2)

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _tableCurrent(self):
        """Return the list of source objects, e.g., _table.restraints/_table.nmrResidues
        """
        return self.current.restraintTable

    @_tableCurrent.setter
    def _tableCurrent(self, value):
        self.current.restraintTable = value

    #=========================================================================================
    # Widgets callbacks
    #=========================================================================================

    def _showOnMolecularViewer(self):
        """Show the molecule on the attached viewer.
        """
        restraintTable = self._modulePulldown.getSelectedObject()
        restraints = self._tableWidget.getSelectedObjects() or []

        print(restraints)

        if restraintTable is not None:
            pymolScriptPath = joinPath(self.moduleParent.pymolScriptsPath, PymolScriptName)
            pdbPath = restraintTable.structureData.moleculeFilePath
            if pdbPath is None:
                MessageDialog.showWarning('No Molecule File found',
                                          'Add a molecule file path to the StructureData from SideBar.')
                return
            pymolScriptPath = pyMolUtil._restraintsSelection2PyMolFile(pymolScriptPath, pdbPath, restraints)
            pyMolUtil.runPymolWithScript(self.application, pymolScriptPath)

        if not restraintTable:
            MessageDialog.showWarning('Nothing to show', 'Select a RestraintTable first')


#=========================================================================================
# main
#=========================================================================================

def main():
    """Show the RestraintTable module
    """
    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # create a new test application
    app = newTestApplication(interface='Gui')
    application = getApplication()
    mainWindow = application.ui.mainWindow

    # add a module
    _module = RestraintTableModule(mainWindow=mainWindow)
    mainWindow.moduleArea.addModule(_module)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    """Call the test function
    
    This will remove the recent opened files and the reset your preferences!
    
    """
    main()
