"""
This file contains StructureTableModule and StructureTable classes
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
__dateModified__ = "$dateModified: 2024-12-09 14:19:10 +0000 (Mon, December 09, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import pandas as pd
from collections import OrderedDict

from ccpn.core.StructureEnsemble import StructureEnsemble as KlassTable
from ccpn.core.DataTable import DataTable
from ccpn.core.lib.DataFrameObject import DataFrameObject
from ccpn.core.lib.Notifiers import Notifier
from ccpn.ui.gui.modules.CcpnModule import CcpnTableModule
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.PulldownListsForObjects import StructureEnsemblePulldown as KlassPulldown
from ccpn.ui.gui.widgets.Column import ColumnClass
from ccpn.ui.gui.widgets.SettingsWidgets import ModuleSettingsWidget
from ccpn.ui.gui.lib._CoreTableFrame import _CoreTableWidgetABC, _CoreTableFrameABC
from ccpn.util.Logging import getLogger


ALL = '<all>'
LINKTOPULLDOWNCLASS = 'linkToPulldownClass'


class StructureTableModule(CcpnTableModule):
    """This class implements the module by wrapping a StructureTable instance
    """
    className = 'StructureTableModule'
    includeSettingsWidget = True
    maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    settingsPosition = 'top'
    activePulldownClass = KlassTable
    _allowRename = True

    # we are subclassing this Module, hence some more arguments to the init
    def __init__(self, mainWindow=None, name='Structure Table',
                 structureEnsemble=None, selectFirstItem=False):
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
        self._table = None

        # add the widgets
        self._setWidgets(self.settingsWidget, self.mainWidget, structureEnsemble, selectFirstItem)
        self._setCallbacks()

    def _setWidgets(self, settingsWidget, mainWidget, structureEnsemble, selectFirstItem):
        """Set up the widgets for the module
        """
        self._settings = None
        if self.activePulldownClass:
            # add to settings widget - see sequenceGraph for more detailed example
            settingsDict = OrderedDict(((LINKTOPULLDOWNCLASS, {'label'   : f'Link to current {self.activePulldownClass.className}',
                                                               'tipText' : f'Set/update current {self.activePulldownClass.className} when selecting from pulldown',
                                                               'callBack': None,
                                                               'enabled' : True,
                                                               'checked' : False,
                                                               '_init'   : None}),))

            self._settings = ModuleSettingsWidget(parent=settingsWidget, mainWindow=self.mainWindow,
                                                  settingsDict=settingsDict,
                                                  grid=(0, 0))

        # add the frame containing the pulldown and table
        self._mainFrame = StructureTableFrame(parent=mainWidget,
                                              mainWindow=self.mainWindow,
                                              moduleParent=self,
                                              structureEnsemble=structureEnsemble, selectFirstItem=selectFirstItem,
                                              grid=(0, 0))

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
                                                   checkBox=self._settings.checkBoxes[LINKTOPULLDOWNCLASS]['widget'])

        # set the dropped callback through mainWidget
        self.mainWidget._dropEventCallback = self._mainFrame._processDroppedItems

    def selectTable(self, table):
        """Select the object in the table
        """
        self._mainFrame.selectTable(table)

    def _closeModule(self):
        """CCPN-INTERNAL: used to close the module
        """
        if self.activePulldownClass:
            if self._setCurrentPulldown:
                self._setCurrentPulldown.unRegister()
                self._setCurrentPulldown = None
            if self._settings:
                self._settings._cleanupWidget()
                self._settings = None
        if self.tableFrame:
            self.tableFrame._cleanupWidget()
            self._mainFrame = None
        super()._closeModule()


#=========================================================================================
# _NewStructureTableWidget
#=========================================================================================

class _NewStructureTableWidget(_CoreTableWidgetABC):
    """Class to present a StructureTable
    """
    className = '_NewStructureTableWidget'
    attributeName = KlassTable._pluralLinkName

    defaultHidden = ['Pid', 'altLocationCode', 'element', 'occupancy']
    _internalColumns = ['isDeleted', '_object']  # columns that are always hidden

    # define self._columns here
    columnHeaders = {}
    tipTexts = ()

    # define the notifiers that are required for the specific table-type
    tableClass = KlassTable
    rowClass = None
    cellClass = None
    tableName = tableClass.className
    rowName = None
    cellClassNames = None
    selectCurrent = False
    callBackClass = None
    search = False

    _defaultEditable = False

    # set the queue handling parameters
    _maximumQueueLength = 10

    # define self._columnHeaders here
    _columnHeaders = {'index'          : '#',
                      'modelNumber'    : 'Model Number',
                      'chainCode'      : 'Chain Code',
                      'sequenceId'     : 'Sequence ID',
                      'insertionCode'  : 'Insertion Code',
                      'residueName'    : 'Residue Name',
                      'atomName'       : 'Atom Name',
                      'altLocationCode': 'altLocation Code',
                      'element'        : 'Element',
                      'x'              : 'X',
                      'y'              : 'Y',
                      'z'              : 'Z',
                      'occupancy'      : 'Occupancy',
                      'bFactor'        : 'bFactor',
                      'nmrChainCode'   : 'nmrChain Code',
                      'nmrSequenceCode': 'nmrSequence Code',
                      'nmrResidueName' : 'nmrResidue Name',
                      'nmrAtomName'    : 'nmrAtom Name',
                      'comment'        : 'Comment'
                      }

    _columnTypes = {'index'          : 'int',
                    'modelNumber'    : 'int',
                    'chainCode'      : 'str',
                    'sequenceId'     : 'int',
                    'insertionCode'  : 'str',
                    'residueName'    : 'str',
                    'atomName'       : 'str',
                    'altLocationCode': 'str',
                    'element'        : 'str',
                    'x'              : 'float',
                    'y'              : 'float',
                    'z'              : 'float',
                    'occupancy'      : 'float',
                    'bFactor'        : 'float',
                    'nmrChainCode'   : 'str',
                    'nmrSequenceCode': 'str',
                    'nmrResidueName' : 'str',
                    'nmrAtomName'    : 'str',
                    'comment'        : 'str'
                    }

    displayMode = 0

    #=========================================================================================
    # Properties
    #=========================================================================================

    #=========================================================================================
    # Selection/Action callbacks
    #=========================================================================================

    def selectionCallback(self, selected, deselected, selection, lastItem):
        """Handle item selection has changed in table - call user callback
        :param selected: table indexes selected
        :param deselected: table indexes deselected
        """
        pass

    def actionCallback(self, selection, lastItem):
        """Handle item selection has changed in table - call user callback
        """
        pass

    #=========================================================================================
    # Create table and row methods
    #=========================================================================================

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

    #=========================================================================================
    # Table functions
    #=========================================================================================

    def _getTableColumns(self, structureEnsemble=None):
        """Add default columns plus the ones according to structureEnsemble
         format of column = ( Header Name, value, tipText, editOption)
         editOption allows the user to modify the value content by doubleclick
         """
        # create the column objects
        self._columnObjects = [
            ('index', lambda row: self._stLamInt(row, 'Index'), 'Index', None, None),
            ('modelNumber', lambda row: self._stLamInt(row, 'modelNumber'), 'modelNumber', None, None),
            ('chainCode', lambda row: self._stLamStr(row, 'chainCode'), 'chainCode', None, None),
            ('sequenceId', lambda row: self._stLamInt(row, 'sequenceId'), 'sequenceId', None, None),
            ('insertionCode', lambda row: self._stLamStr(row, 'insertionCode'), 'insertionCode', None, None),
            ('residueName', lambda row: self._stLamStr(row, 'residueName'), 'residueName', None, None),
            ('atomName', lambda row: self._stLamStr(row, 'atomName'), 'atomName', None, None),
            ('altLocationCode', lambda row: self._stLamStr(row, 'altLocationCode'), 'altLocationCode', None, None),
            ('element', lambda row: self._stLamStr(row, 'element'), 'element', None, None),
            ('x', lambda row: self._stLamFloat(row, 'x'), 'x', None, '%0.3f'),
            ('y', lambda row: self._stLamFloat(row, 'y'), 'y', None, '%0.3f'),
            ('z', lambda row: self._stLamFloat(row, 'z'), 'z', None, '%0.3f'),
            ('occupancy', lambda row: self._stLamFloat(row, 'occupancy'), 'occupancy', None, None),
            ('bFactor', lambda row: self._stLamFloat(row, 'bFactor'), 'bFactor', None, None),
            ('nmrChainCode', lambda row: self._stLamStr(row, 'nmrChainCode'), 'nmrChainCode', None, None),
            ('nmrSequenceCode', lambda row: self._stLamStr(row, 'nmrSequenceCode'), 'nmrSequenceCode', None, None),
            ('nmrResidueName', lambda row: self._stLamStr(row, 'nmrResidueName'), 'nmrResidueName', None, None),
            ('nmrAtomName', lambda row: self._stLamStr(row, 'nmrAtomName'), 'nmrAtomName', None, None),
            ('comment', lambda row: self._getCommentText(row), 'Notes', lambda row, value: self._setComment(row, 'comment', value), None)
            ]  # [Column(colName, func, tipText, editValue, columnFormat)

        return ColumnClass(self._columnObjects)

    def buildTableDataFrame(self):
        """Return a Pandas dataFrame from an internal list of objects.
        The columns are based on the 'func' functions in the columnDefinitions.
        :return pandas dataFrame
        """
        return self._buildStructureTable() if self.displayMode == 0 else self._buildAverageTable()

    def _buildStructureTable(self):
        """Return the dataFrame for the structure table
        """
        if self._table:
            self._columnDefs = self._getTableColumns(self._table)

            df = pd.DataFrame(self._table.data).astype({k: v for k, v in self._columnTypes.items() if k in self._table.data.columns})

        else:
            self._columnDefs = self._getTableColumns()
            df = pd.DataFrame(columns=self._columnDefs.headings)

        # change to more readable column headers
        df.columns = [self._columnHeaders.get(col) or col for col in list(df.columns)]

        # create the dataFrame object
        return DataFrameObject(dataFrame=df,
                               columnDefs=self._columnDefs or [],
                               table=self)

    def _buildAverageTable(self):
        """Return the dataFrame for the ensemble-average table
        """
        if self._table:
            # read the dataFrame from the value stored in the DataTable
            df = pd.DataFrame(self.thisDataSet)

        else:
            df = pd.DataFrame(columns=self.AVcolumns.headings)

        # change to more readable column headers
        df.columns = [self._columnHeaders.get(col) or col for col in list(df.columns)]

        # create the dataFrame object
        return DataFrameObject(dataFrame=df,
                               columnDefs=self._columnDefs or [],
                               table=self)

    def getSelectedObjects(self, fromSelection=None):
        """Return the selected core objects.

        :param fromSelection:
        :return: get a list of table objects. If the table has a header called pid, the object is a ccpn Core obj like Peak,
        otherwise is a Pandas-series object corresponding to the selected row(s).
        """
        model = self.selectionModel()
        if selection := fromSelection or model.selectedRows():
            _sortIndex = self.model()._sortIndex

            return list(self._df.iloc[[_sortIndex[idx.row()] for idx in selection if idx.row() in _sortIndex]].iterrows())

    #=========================================================================================
    # Updates
    #=========================================================================================

    def _update(self):
        """Display the objects on the table for the selected list.
        """
        if self._table:
            self.populateTable()
        else:
            self.populateEmptyTable()

    #=========================================================================================
    # object properties
    #=========================================================================================

    @staticmethod
    def _stLamInt(row, name):
        """
        CCPN-INTERNAL: Insert an int into ObjectTable
        """
        try:
            return int(getattr(row, name))
        except Exception:
            return None

    @staticmethod
    def _stLamFloat(row, name):
        """
        CCPN-INTERNAL: Insert a float into ObjectTable
        """
        try:
            return float(getattr(row, name))
        except Exception:
            return None

    @staticmethod
    def _stLamStr(row, name):
        """
        CCPN-INTERNAL: Insert a str into ObjectTable
        """
        try:
            return str(getattr(row, name))
        except Exception:
            return None


#=========================================================================================
# StructureTableFrame
#=========================================================================================

class StructureTableFrame(_CoreTableFrameABC):
    """Frame containing the pulldown and the table widget
    """
    _TableKlass = _NewStructureTableWidget
    _PulldownKlass = KlassPulldown

    def __init__(self, parent, mainWindow=None, moduleParent=None,
                 structureEnsemble=None, selectFirstItem=False, **kwds):
        super().__init__(parent, mainWindow=mainWindow, moduleParent=moduleParent,
                         obj=structureEnsemble, selectFirstItem=selectFirstItem, **kwds)

        # create widget for selection of ensemble-average
        self.stButtons = RadioButtons(self, texts=['Ensemble', 'Average'],
                                      selectedInd=0,
                                      callback=self._selectionButtonCallback,
                                      direction='h',
                                      tipTexts=None,
                                      )

        self.addWidgetToTop(self.stButtons, 2)
        self.stButtons.radioButtons[1].setEnabled(False)
        self._setNotifiers()

    def _setNotifiers(self):
        """
        Set a Notifier to call when an object is created/deleted/renamed/changed.
        rename calls on name.
        change calls on any other attribute.
        """
        # there is no CHANGE notifier on tableClass yet
        self._ensembleNotifier = Notifier(self.project,
                                          [Notifier.CHANGE],
                                          KlassTable.__name__,
                                          self._updateEnsembleCallback,
                                          onceOnly=True)

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _tableCurrent(self):
        """Return the list of source objects, e.g., _table.peaks/_table.nmrResidues
        """
        return self.current.structureEnsemble

    @_tableCurrent.setter
    def _tableCurrent(self, value):
        self.current.structureEnsemble = value

    #=========================================================================================
    # Widgets callbacks
    #=========================================================================================

    def _selectionButtonCallback(self):
        """Notifier Callback for selecting Structure Ensemble or average
        """
        item = self.stButtons.get()
        getLogger().debug('>selectionPulldownCallback>', item, type(item))

        if self.table is None:
            self._tableWidget.populateEmptyTable()

        elif item == 'Ensemble':
            self._tableWidget.displayMode = 0
            self._tableWidget._update()

        elif item == 'Average':
            self._tableWidget.displayMode = 1
            self._tableWidget._update()

    def _selectionPulldownCallback(self, item):
        """Selection table from the pulldown and calculate the ensemble-average
        """
        self._tableWidget.displayMode = 0
        self.stButtons.setIndex(0, blockSignals=True)

        super()._selectionPulldownCallback(item)

        if self.table is not None:
            self._getAttachedDataSet()
        elif len(self.stButtons.radioButtons) > 0:
            # disable the 'average' button
            self.stButtons.radioButtons[1].setEnabled(False)

    def _getAttachedDataSet(self):
        """Get the StructureData object attached to this StructureEnsemble
        """
        if len(self.stButtons.radioButtons) > 0:
            self.stButtons.radioButtons[1].setEnabled(False)

        try:
            avName = f'{self.table.name}-average'
            if (found := self.project.getObjectsByPartialId(DataTable.className, avName)):
                found = found[0]  # select the first found item

                self._tableWidget.thisDataSet = found.data

                # set the new columns
                AVheadings = list(self._tableWidget.thisDataSet)
                self.guiTable.AVcolumns = ColumnClass([col for col in self._tableWidget._columnObjects if col[0] in AVheadings or col[0] == '#'])

                if len(self.stButtons.radioButtons) > 0:
                    self.stButtons.radioButtons[1].setEnabled(True)

            else:
                self._tableWidget.thisDataSet = None

        except Exception:
            self._tableWidget.thisDataSet = None

    #=========================================================================================
    # Notifier callbacks
    #=========================================================================================

    def _updateEnsembleCallback(self, data):
        """
        Notifier Callback for updating the table.
        """
        obj = data[Notifier.OBJECT]
        if obj != self.table:
            return

        self._tableWidget._update()

    def _cleanupWidget(self):
        if self._ensembleNotifier:
            self._ensembleNotifier.unRegister()

        super()._cleanupWidget()


#=========================================================================================
# main
#=========================================================================================

def main():
    """Show the IntegralTableModule
    """
    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # create a new test application
    app = newTestApplication(interface='Gui')
    application = getApplication()
    mainWindow = application.ui.mainWindow

    # add a module
    _module = StructureTableModule(mainWindow=mainWindow)
    mainWindow.moduleArea.addModule(_module)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    """Call the test function
    """
    main()
