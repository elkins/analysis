"""
A macro to create a module which allows users to synchronise axes among different spectrumDisplays.

Requirements:
    - CcpNmrAnalysis 3.1.1 +
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
__dateModified__ = "$dateModified: 2024-08-23 19:23:55 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author:  Luca Mureddu $"
__date__ = "$Date: 2023-07-20 12:45:48 +0100 (Thu, July 20, 2023) $"
#=========================================================================================
__title__ = "Synchronise axes among different spectrumDisplays"

import time
# Start of code
#=========================================================================================


from itertools import combinations
import uuid
import pandas as pd
from functools import partial
from collections import defaultdict
from ccpn.util.decorators import singleton
from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.core.lib.Notifiers import Notifier
from ccpn.util.DataEnum import DataEnum
from ccpn.util.Logging import getLogger
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.CcpnModuleArea import CcpnModuleArea
from ccpn.ui.gui.widgets.MessageDialog import showWarning, showMessage, showError, showMulti, showYesNo
from ccpn.framework.Application import getApplication, getProject, getMainWindow, getCurrent
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Column import Column
from ccpn.ui.gui.widgets.table.CustomPandasTable import CustomDataFrameTable
import ccpn.ui.gui.widgets.CompoundWidgets as cw
from ccpn.ui.gui.widgets.table._TableDelegates import _SmallPulldown as PulldownDelegate
from ccpn.ui.gui.widgets.table._TableDelegates import _SimplePulldownTableDelegate as PulldownDelegateModel
from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.lib.Strip import Strip

# This block is for the macro while is under development - Avoid the singleton to reload the python module and have unexpected behaviours.
ccpnApplication = getApplication()
mainWindow = ccpnApplication.mainWindow
currentModules = [m for m in mainWindow.moduleArea.ccpnModules if m.className == 'SyncSpectrumDisplays']
if len(currentModules) > 0:
    showWarning('Already Opened.', 'Cannot open this module twice.')
    raise RuntimeError('already opened')


# ALPHA warning

msg = 'This module is an alpha version and there might be unexpected behaviours. These could require closing the compromised spectrumDisplay(s) or restarting the project.'
CANCEL = 'Cancel'
SAVE_AND_CONTINUE = 'Save project and continue'
CONTINUE = 'Continue without saving'
answer = showMulti('Warning', msg, [SAVE_AND_CONTINUE, CONTINUE, CANCEL])
if answer == CANCEL:
    raise RuntimeError('Operation cancelled by the users')
if answer == SAVE_AND_CONTINUE:
    application.saveProject()

ROWUID = 'UID'
SOURCESPECTRUMDISPLAYPID = 'sourceSpectrumDisplayPid'
TARGETSPECTRUMDISPLAYPID = 'targetSpectrumDisplayPid'
SOURCEAXISCODE = 'sourceAxisCode'
TARGETAXISCODE = 'targetAxisCode'
_SIGNALS = '_signal'
_CONNECTIONS = '_connections'
_SLOT = '_slots'

## GUI placeholder/variables
_DCTE = 'Double Click to edit'


@singleton
class SpectrumDisplaySyncHandler(object):
    """
    An object to handle the synchronisation of Axes between SpectrumDisplays through notifiers.
    This object will facilitate adding new syncs, removing them and avoiding circular feedbacks from notifiers.
    Data about which SpectrumDisplays/axes are being sync is stored inside a singleton dataFrame.

    DataFrame Columns:
    - sourceSpectrumDisplayPid
    - targetSpectrumDisplayPid
    - sourceAxisCode
    - targetAxisCode
    - ROWUID

    DataFrame Index: same as the ROWUID column
    Internal columns:
    - ROWUID: a unique random str of 13 characters for identify the row in the dataframe.

   IMPORTANT:  _signalsDict:
   _signalsDict is a dictionary of key:dict .
    _signalsDict = { ROWUID   : {
                                                'signals':[..., ],
                                                'connections':[..., ]
                                                 }
                            }
    Key: dataframe index.   inner dict: contains  the (GL) signals and  their active connections.
    This is required so that we can disconnect only what is required. It is not included in the main data, has is not serialisable and only needed at run time.

    Two options: Transitive or direct synchronisation:

    ** Transitive **
         - For a system composed of  A <-> B and B <-> C,
         - A is directly synced to B and B is directly synced to C.
         - C is indirectly synced to A.
          Any firing display will resul in all displays A,B, and C being synchronised.
         - If A is the firing display: A sets B, and B sets C
         - if B is the firing display: B sets A, and B sets C
         - if C is the firing display: C sets B, and B sets A

         - for a system composed of  A <-> B and B <-> C,  D<->E, E<->A
          Any firing display will resul in all displays A,B,C,D and E being synchronised.

    ** Direct **
          - for a system composed of  A <-> B and B <-> C,  D<->E, E<->A (as last example)
          - If A is the firing display: A sets B and E
          - If B is the firing display: B sets C and A
          - If C is the firing display: C sets B only
          - If D is the firing display: D sets E only
          - If E is the firing display: E sets D and A

    """

    columns = [
        SOURCESPECTRUMDISPLAYPID,
        TARGETSPECTRUMDISPLAYPID,
        SOURCEAXISCODE,
        TARGETAXISCODE,
        ROWUID
        ]

    def __init__(self):
        self._data = pd.DataFrame(columns=self.columns)
        self._isTransitive = True
        self.project = getProject()
        self._signalsDict = {}  ##

    @property
    def data(self):
        """The dataframe containing the syncs """
        return self._data

    @property
    def isEmpty(self):
        """Check if the data is empty and does not contain any syncs """
        return self.data.empty

    @property
    def isTransitive(self):
        """Return True if the synchronisation mode is transitive.
         If transitive,  if A is synced to B, and B is sync to C, then A is sync to C."""
        return self._isTransitive

    def setTransitive(self, value):
        if not isinstance(value, bool):
            raise ValueError(f'{self} setTransitive. Value must be of type boolean. Given {value}.')
        self._isTransitive = value

    def syncSpectrumDisplays(self, **kwargs):
        """
        :param kwargs: key-value. Key argument to be the column name  as defined in self.columns.
        E.g. usage:
            myKwargs = {
                                    SOURCESPECTRUMDISPLAYPID : 'theSourceSpectrumDisplayPid',
                                    TARGETSPECTRUMDISPLAYPID : 'theTargetSpectrumDisplayPid',
                                    SOURCEAXISCODE                      : 'theSourceSpectrumDisplayAxisCode',
                                    TARGETAXISCODE                      : 'theTargetSpectrumDisplayAxisCode',
                                    }
            # add the values to the handler:
            SpectrumDisplaySyncHandler().syncSpectrumDisplays(**myKwargs)
        :return: A Pandas Series object representing the new added row to the data.
        """
        newRow = self._addSyncToData(**kwargs)
        return newRow

    def unsyncSpectrumDisplay(self, spectrumDisplayPid):
        """ Remove the spectrumDisplay from any synchronisation (whether is a target or the source). """
        ## disconnect signals first

        data = self._getBySpectrumDisplay(spectrumDisplayPid)
        for i in list(data.index):
            self._unsyncByIndex(i)
        return self._data

    def fetchEmptyEntry(self, placeHolderValue: str = None):
        """ Get or create a row to use as placeholder to start a new sync"""
        df = self.data
        mask = df[SOURCESPECTRUMDISPLAYPID].eq(placeHolderValue) & \
               df[TARGETSPECTRUMDISPLAYPID].eq(placeHolderValue)
        if len(mask) > 0:
            filteredData = df[mask]
            if len(filteredData) > 0:
                index = list(filteredData.index)[-1]
                return self._data.loc[index]
        index = str(uuid.uuid4()).split('-')[-1]
        self._data.loc[index, self.columns] = [placeHolderValue] * len(self.columns)
        self._data.loc[index, ROWUID] = index
        return self._data.loc[index]

    def _removeEmptyEntry(self, placeHolderValue: str = None):
        row = self.fetchEmptyEntry(placeHolderValue)
        if row is not None:
            self._data.drop(index = row.name, inplace=True, errors='ignore')

    def cloneSync(self, index):
        row = self._data.loc[index]
        if row is None:
            getLogger().warn(f'Nothing to clone. {index} not in data')
            return
        newIndex = str(uuid.uuid4()).split('-')[-1]
        self._data.loc[newIndex, self.columns] = row.values
        self._data.loc[newIndex, ROWUID] = newIndex
        return self._data.loc[newIndex]

    def _syncAxesOnSpectrumDisplays(self, spectrumDisplays, axisIndex):
        """
        :param spectrumDisplays:  list of core objects
        :param axisIndex: index of the axis object to sync. 0 for the x Axis, 1 for the y Axis
        :return: None
        """
        if axisIndex > 1:
            raise ValueError('AxisIndex can only be 0 or 1')

        if len(spectrumDisplays)>1:
            sourceSpectrumDisplay = spectrumDisplays[0]
            xAxis = sourceSpectrumDisplay.strips[0].axisOrder[axisIndex] #should always be 1 strip and 2 axis
            for spectrumDisplay in spectrumDisplays[1:]:
                xTargetAxis = spectrumDisplay.strips[0].axisOrder[axisIndex]
                index = str(uuid.uuid4()).split('-')[-1]
                self._data.loc[index, [SOURCESPECTRUMDISPLAYPID, SOURCEAXISCODE]] = [sourceSpectrumDisplay.pid, xAxis]
                self._data.loc[index, [TARGETSPECTRUMDISPLAYPID, TARGETAXISCODE]] = [spectrumDisplay.pid, xTargetAxis]
                self._data.loc[index, ROWUID] = index
        else:
            getLogger().warning('Cannot sync spectrumDisplay, not enough displays.')


    def clearAll(self):
        """Remove all sync from the table.
        """
        self._removeGUIConnectionSignals(self.data)
        self._data.drop(index=self._data.index, inplace=True, errors='ignore')
        self._signalsDict.clear()
        return self._data

    ## Private helper methods  ##

    def _unsyncByIndex(self, rowIndex):
        """ Remove the row from the data and any signals. """
        ## disconnect signals first
        mask = self._data[ROWUID].eq(rowIndex)
        dataToDisconnect = self._data[mask]
        self._removeGUIConnectionSignals(dataToDisconnect)
        ## Remove defs from data
        self._data = self._data[~mask]
        return self._data

    def _addSyncToData(self, **kwargs):
        """Fill the dataFrame with the Column/Value definitions.
        This does NOT add the GUI signal. """
        dd = {k: kwargs[k] for k in self.columns if k in kwargs}  ## make sure we have only needed columns, discard the rest
        index = str(uuid.uuid4()).split('-')[-1]  ## random unique identifier
        self._data.loc[index, list(dd.keys())] = list(dd.values())
        return self._data.loc[index]

    def _inverseFilterByHeadValue(self, df, header, value):
        return df[~df[header].eq(value)]

    def _getBySpectrumDisplay(self, spectrumDisplayPid, axisCode=None):
        """ Get a  filtered dataframe where the spectrumDisplayPid is present or as a source or as a target. Optional : axisCode to filter even further."""
        df = self.data
        mask = df[SOURCESPECTRUMDISPLAYPID].eq(spectrumDisplayPid) | \
               df[TARGETSPECTRUMDISPLAYPID].eq(spectrumDisplayPid)
        if axisCode is not None:
            mask = (df[SOURCESPECTRUMDISPLAYPID].eq(spectrumDisplayPid) & df[SOURCEAXISCODE].eq(axisCode)) | \
                   (df[TARGETSPECTRUMDISPLAYPID].eq(spectrumDisplayPid) & df[TARGETAXISCODE].eq(axisCode))
        return df[mask].copy()

    def _isValidSignal(self, rowIndex, signal, callbackDict):
        valid = False
        if rowIndex not in self.data.index:
            connection = self._signalsDict.get(rowIndex)
            if connection is None:
                # not sure yet why we have left-over signals. But disconnecting here is very dangerous and causes unexpected behaviours.
                try:
                    signal.disconnect()
                except Exception as err:
                    getLogger().warning(f'Cannot disconnect {signal} for row {rowIndex}. Error: {err}')
            else:
                    try:
                        signal.disconnect(connection)
                    except Exception as err:
                        getLogger().warning(f'Cannot disconnect {signal} from connection: {connection}. Invalid row {rowIndex}. Error: {err}')
            self._signalsDict.pop(rowIndex, None)
            valid = False
        elif self._signalsDict is None or len(self._signalsDict.keys())==0:
            valid = False
        else:
            valid = True
        return valid

    def _getAxisByAxisCode(self, strip, axisCode):
        for axis in strip.axes:
            if axis.code == axisCode:
                return axis

    def _getAxisIndexByAxisCode(self, strip, axisCode):
        for i, axis in enumerate(strip.orderedAxes):
            if axis.code == axisCode:
                return i

    def _getTransitiveGroups(self, data):
        """ Given a list of tuples representing pairwise relationships, 
        find transitivity and re-assemble them in common groups
         e.g.:
         data = [['GD:A', 'GD:B'],
                    ['GD:C', 'GD:N'],
                    ['GD:P', 'GD:X'],
                    ['GD:B', 'GD:C']]
        result:
          >>  [ ('GD:A', 'GD:B', 'GD:C', 'GD:N'),
              ('GD:P', 'GD:X') ]
         """
        sets = [set(x) for x in data]
        done = False
        while not done:
            done = True
            for left, right in combinations(sets, 2):
                if left & right:                         # check if they intersect
                    left |= right                        # move items from rig ht to left
                    right ^= right                     # empty right
                    done = False
            sets = list(filter(None, sets))     # remove empty sets
        return [sorted(list(x)) for x in sets]

    def _getDirectConnections(self, data, firingSpectrumDisplayPid):
        ## get all direct coupled displayes to the firingSpectrumDisplay
        targetingByAxisCodes = defaultdict(list)
        for i, row in data.iterrows():
            aDisplayPid = row[SOURCESPECTRUMDISPLAYPID]
            bDisplayPid = row[TARGETSPECTRUMDISPLAYPID]
            aAxisCode = row[SOURCEAXISCODE]
            bAxisCode = row[TARGETAXISCODE]
            if firingSpectrumDisplayPid == aDisplayPid:
                targetingByAxisCodes[aAxisCode].append((bDisplayPid, bAxisCode))
            if firingSpectrumDisplayPid == bDisplayPid:
                targetingByAxisCodes[bAxisCode].append((aDisplayPid, aAxisCode))
        return targetingByAxisCodes

    def _getTransitiveConnections(self, data, firingSpectrumDisplay):
        """   """
        pairs = data[[SOURCESPECTRUMDISPLAYPID, TARGETSPECTRUMDISPLAYPID]].values
        transitiveGroups = self._getTransitiveGroups(pairs)
        filteredGroups = [g for g in transitiveGroups if firingSpectrumDisplay in g]
        return filteredGroups

    def _syncByTransitiveGroups(self, firingStrip):
        """
         For a system composed of  A <-> B and B <-> C,
         - A is directly synced to B and B is directly synced to C.
         - C is indirectly synced to A.
          If C is the firingSpectrumDisplay  it will resul in all displays A,B, and C being synchronised.
         Because C sets B, and B sets A
        :param data:
        :param firingSpectrumDisplay:
        :param axisCodes:
        :return:
        """
        firingSpectrumDisplay = firingStrip.spectrumDisplay
        firingSpectrumDisplayPid = firingSpectrumDisplay.pid

        firingDisplayAxisCodes = list(firingSpectrumDisplay.axisCodes)
        for i, axisCode in enumerate(firingDisplayAxisCodes):
            _dataByAxisCode = self._getBySpectrumDisplay(firingSpectrumDisplayPid, axisCode)
            if _dataByAxisCode.empty:
                firingDisplayAxisCodes.pop(i)

        transitiveGroups = self._getTransitiveConnections(self.data, firingSpectrumDisplayPid)

        for group in transitiveGroups:
            targetDisplays = [dd for dd in group if dd != firingSpectrumDisplayPid]
            for targetingDisplayPid in targetDisplays:
                # check the axisCode is in data
                for i, axisCode in enumerate(firingDisplayAxisCodes):
                    _dataByAxisCode = self._getBySpectrumDisplay(targetingDisplayPid, axisCode )
                    if _dataByAxisCode.empty:
                        continue # the axiscode is not in, so skip it
                    targetingDisplay = self.project.getByPid(targetingDisplayPid)
                    if targetingDisplay is None:
                        continue
                    allTargetingStrips = [s for s in firingSpectrumDisplay.strips if s != firingStrip]
                    allTargetingStrips += [s for s in targetingDisplay.strips if s != firingStrip]
                    firingAxis = self._getAxisByAxisCode(firingStrip, axisCode)
                    sourceRegion = firingAxis.region
                    for targetingStrip in allTargetingStrips:
                        targetingAxisIndex = self._getAxisIndexByAxisCode(targetingStrip, axisCode)
                        targetingStrip.setAxisRegion(targetingAxisIndex, sourceRegion)


    def _syncAxes(self, callbackDict, *, signal, rowIndex: str = None):
        """Callback from GLWidget signals. """
        if not self._isValidSignal(rowIndex, signal, callbackDict):
            # self._addGUIConnectionSignals(self.data)
            return
        firingStrip = callbackDict.get('strip')
        if firingStrip is None:
            firingSpectrumDisplay = callbackDict.get('spectrumDisplay')
            if firingSpectrumDisplay is  None: # but  the source could be the GL axis.
                return
            firingStrip = firingSpectrumDisplay.strips[0]


        if self.isTransitive:
            self._syncByTransitiveGroups(firingStrip)
        else:
            firingSpectrumDisplay = firingStrip.spectrumDisplay
            firingSpectrumDisplayPid = firingSpectrumDisplay.pid
            ## filter the data so we have only the displays of interest
            data = self._getBySpectrumDisplay(firingSpectrumDisplayPid)
            if data.empty:
                return
            ## group the targeting displays by axisCodes
            targetingByAxisCodes = self._getDirectConnections(data, firingSpectrumDisplayPid)
            ## Perform the synchronisation by setting the axis region from the firing strip to the targeting strips axis
            for firingAxisCode, targets in targetingByAxisCodes.items():
                for targetingDefs in targets:
                    targetingDisplayPid, targetingAxisCode = targetingDefs
                    targetingDisplay = self.project.getByPid(targetingDisplayPid)
                    if targetingDisplay is None:
                        continue
                    allTargetingStrips = [s for s in firingSpectrumDisplay.strips if s != firingStrip]
                    allTargetingStrips += [s for s in targetingDisplay.strips if s != firingStrip]
                    firingAxis = self._getAxisByAxisCode(firingStrip, firingAxisCode)
                    sourceRegion = firingAxis.region
                    for targetingStrip in allTargetingStrips:
                        targetingAxisIndex = self._getAxisIndexByAxisCode(targetingStrip, targetingAxisCode)
                        targetingStrip.setAxisRegion(targetingAxisIndex, sourceRegion)

    def _getStripsBySpectrumDisplayPid(self, spectrumDisplayPid):
        if spectrumDisplay := self.project.getByPid(spectrumDisplayPid):
            return spectrumDisplay.strips
        return []

    def _getAllAvailableStrips(self, data):
        """Get all strips based on the SpectrumDiplays Pids available in the dataFrame """
        strips = []
        for i, row in data.iterrows():
            targetDisplayPid = row[TARGETSPECTRUMDISPLAYPID]
            sourceDisplayPid = row[SOURCESPECTRUMDISPLAYPID]
            strips += self._getStripsBySpectrumDisplayPid(sourceDisplayPid)
            strips += self._getStripsBySpectrumDisplayPid(targetDisplayPid)
        return list(set(strips))

    def _addGUIConnectionSignals(self, data=None):
        """
        Connect the GL widget to a custom method to syncronise the spectrumDisplays.
        :return:
        """
        if data is None:
            data = self.data
        # add all the row id as identifier, so we can check for recycled SpectrumDisplay pids etc
        for index, row in data.iterrows():
            ## Could check is already connected and skip
            strips = self._getStripsBySpectrumDisplayPid(row[SOURCESPECTRUMDISPLAYPID])
            strips += self._getStripsBySpectrumDisplayPid(row[TARGETSPECTRUMDISPLAYPID])
            connections = []
            connectedSignals = []
            slots = []
            for strip in strips:
                #  RowIndex is extremely important so to ensure precise firing and avoid duplicates/circles.
                glWidget = strip.getGLWidget()
                signals = [glWidget.GLSignals._syncChanged]
                for signal in signals:
                    slot = partial(self._syncAxes, signal=signal, rowIndex=index)
                    connection = signal.connect(slot)
                    connections.append(connection)
                    connectedSignals.append(signal)
            self._signalsDict[index] = {
                                                    _SIGNALS               : connectedSignals,
                                                    _CONNECTIONS    : connections,
                                                    _SLOT                     : slots
                                                    }

    def _removeGUIConnectionSignals(self, data):
        """
        disconnect the GL widgets which synchronise the spectrumDisplays.
        :return:
        """

        for index, row in data.iterrows():
            signalDict = self._signalsDict.pop(index, None)
            if signalDict is not None:
                signals = signalDict.get(_SIGNALS)
                connections = signalDict.get(_CONNECTIONS)
                for signal, connection in zip(signals, connections):
                    try:  # it has to be a try/except because the signal might be already disconnected.
                        signal.disconnect(connection)
                    except Exception as err:
                        getLogger().warn(f'Sync Handler. Cannot disconnect {signal}, index: {index}. Signal might have been already disconnected. {err}')

    def __repr__(self):
        return f'<< SpectrumDisplays Sync Handler >>'


class _PulldownDelegate(PulldownDelegate):
    """ A delegate which fires a signal when the text is highlighted. (Note the native textHighlighted pyqtSignal doesn't work on Pull"""

    def __init__(self, parent, mainWindow=None, textHighlightedCallback=None, *args, **kwds):
        super().__init__(parent, *args, **kwds)
        self.textHighlightedCallback = textHighlightedCallback
        self._list.entered.connect(self._textHighlighted)

    def _textHighlighted(self, qitem):
        text = qitem.data()
        if self.textHighlightedCallback is not None:
            self.textHighlightedCallback(text)

    def hidePopup(self) -> None:
        """Hide the popup if event occurs after the double-click interval
        """
        if self.textHighlightedCallback is not None:
            self.textHighlightedCallback('')
        return super().hidePopup()


class SyncSpectrumDisplaysTable(CustomDataFrameTable):
    """A Gui table to contain the list of  synchronised SpectrumDisplays and axisCodes
    """
    defaultTableDelegate = PulldownDelegateModel
    INVALIDCOLOUR = '#f05454'
    VALIDCOLOUR = '#f7f2f2'

    def __init__(self, parent,  parentModule, *args, **kwds):
        super().__init__(parent, *args, **kwds)
        self.project = getProject()
        self.mainWindow = getMainWindow()
        self.application = getApplication()
        self.current = getCurrent()
        self.parentModule = parentModule
        # define the column definitions
        ## columnMap -> key: the rowdata column name. Value: the displayed text
        self.columnMap = {
            SOURCESPECTRUMDISPLAYPID: 'Source Display',
            TARGETSPECTRUMDISPLAYPID: 'Target Display',
            SOURCEAXISCODE          : 'Source AxisCode',
            TARGETAXISCODE          : 'Target AxisCode',
            }
        columns = [
            Column(headerText=self.columnMap[SOURCESPECTRUMDISPLAYPID],
                   getValue=SOURCESPECTRUMDISPLAYPID,
                   rawDataHeading=SOURCESPECTRUMDISPLAYPID,
                   editClass=_PulldownDelegate,
                   tipText='Double click to select the Source SpectrumDisplay from where you want to share an axis.',
                   editKw={
                       'texts'                  : [''],
                       'clickToShowCallback'    : partial(self._updateSpectrumDisplayPulldownCallback, SOURCESPECTRUMDISPLAYPID),
                       'callback'               : partial(self._tableSelectionChanged, SOURCESPECTRUMDISPLAYPID),
                       'textHighlightedCallback': self._selectionTextChanged,
                       'objectName'             : SOURCESPECTRUMDISPLAYPID,
                       },
                   columnWidth=200,
                   ),
            Column(headerText=self.columnMap[SOURCEAXISCODE],
                   getValue=SOURCEAXISCODE,
                   rawDataHeading=SOURCEAXISCODE,
                   editClass=_PulldownDelegate,
                   tipText='Double click to select the Source AxisCode you want to sync',
                   editKw={
                       'texts'              : [''],
                       'clickToShowCallback': partial(self._updateAxisCodeCallback, SOURCESPECTRUMDISPLAYPID, SOURCEAXISCODE),
                       'callback'           : partial(self._tableSelectionChanged, SOURCEAXISCODE),
                       'objectName'         : SOURCEAXISCODE,
                       },
                   columnWidth=150,
                   ),
            Column(headerText=self.columnMap[TARGETSPECTRUMDISPLAYPID],
                   getValue=TARGETSPECTRUMDISPLAYPID,
                   rawDataHeading=TARGETSPECTRUMDISPLAYPID,
                   editClass=_PulldownDelegate,
                   tipText='Double click to select the Target SpectrumDisplay you want to sync with the source SpectrumDisplay Axis.',
                   editKw={
                       'texts'                  : [''],
                       'clickToShowCallback'    : partial(self._updateSpectrumDisplayPulldownCallback, TARGETSPECTRUMDISPLAYPID),
                       'callback'               : partial(self._tableSelectionChanged, TARGETSPECTRUMDISPLAYPID),
                       'textHighlightedCallback': self._selectionTextChanged,
                       'objectName'             : TARGETSPECTRUMDISPLAYPID,
                       },
                   columnWidth=200,
                   ),
            Column(headerText=self.columnMap[TARGETAXISCODE],
                   getValue=TARGETAXISCODE,
                   rawDataHeading=TARGETAXISCODE,
                   editClass=_PulldownDelegate,
                   tipText='Double click to select the Target AxisCode you want to sync with the source',
                   editKw={
                       'texts'              : [''],
                       'clickToShowCallback': partial(self._updateAxisCodeCallback, TARGETSPECTRUMDISPLAYPID, TARGETAXISCODE),
                       'callback'           : partial(self._tableSelectionChanged, TARGETAXISCODE),
                       'objectName'         : TARGETAXISCODE,
                       },
                   columnWidth=100,
                   ),
            Column(headerText=ROWUID, getValue=ROWUID, rawDataHeading=ROWUID,
                   isInternal=False,
                   isHidden=True,
                   ),
            ]

        self._columnDefs.setColumns(columns)
        self._rightClickedTableIndex = None  # last selected item in a table before raising the context menu. Enabled with mousePress event filter

    @property
    def backend(self):
        return SpectrumDisplaySyncHandler()

    @property
    def dataFrame(self):
        """ Get the dataframe exactly as displayed on the Table. """
        data = self.model()._getVisibleDataFrame(includeHiddenColumns=True)
        if data.empty:
            return data
        data.set_index(ROWUID, inplace=True, drop=False)
        return data

    def updateTable(self):
        """
        Set the data on the table as it appears on the backend
        :return: the displayed dataframe
        """
        self.setDataFrame(self.backend.data)
        if self.parentModule._getSyncState == _SyncState.SUSPENDED:
            return self.dataFrame

        self.backend._addGUIConnectionSignals()
        return self.dataFrame

    #=========================================================================================
    # Callbacks from selections
    #=========================================================================================

    def _updateSpectrumDisplayPulldownCallback(self, header):
        currentSelected = self._getSelectedSeries()
        if currentSelected is None:
            return
        rowIndex = currentSelected.name
        pulldown = self.sender()
        selectedHeader = self.columnMap.get(header)
        sourceDisplayHeader = self.columnMap.get(SOURCESPECTRUMDISPLAYPID)
        targetDisplayHeader = self.columnMap.get(TARGETSPECTRUMDISPLAYPID)
        otherHeader = sourceDisplayHeader if selectedHeader == targetDisplayHeader else targetDisplayHeader
        currentSelection = self._getValueByHeader(rowIndex, selectedHeader)
        otherPulldownValue = self._getValueByHeader(rowIndex, otherHeader)
        data = self.project.getPidsByObjects(self.project.spectrumDisplays)
        alreadySelectedData = [dd for dd in data if dd == otherPulldownValue]
        filteredData = [dd for dd in data if dd != otherPulldownValue]
        ordered = filteredData + alreadySelectedData
        index = data.index(currentSelection) if currentSelection in data else None
        pulldown.setData(ordered, index=index, headerText=_DCTE, headerEnabled=False, )

        for pid in alreadySelectedData:
            i = pulldown.getItemIndex(pid)
            pulldown.insertSeparator(i)

    def _updateAxisCodeCallback(self, spectrumDisplayHeader, axisCodeHeader):
        """Callback when changed the axisCode pulldown from table """
        currentSelected = self._getSelectedSeries()
        if currentSelected is None:
            return
        rowIndex = currentSelected.name
        spectrumDisplayTableHeader = self.columnMap.get(spectrumDisplayHeader)
        axisCodeTableHeader = self.columnMap.get(axisCodeHeader)
        currentAc = self._getValueByHeader(rowIndex, axisCodeTableHeader)
        display = self._getDisplayByHeader(rowIndex, spectrumDisplayTableHeader)
        if display is None:
            return
        # update the data
        pulldown = self.sender()
        axisCodes = list(display.axisCodes)
        index = axisCodes.index(currentAc) if currentAc in axisCodes else None
        pulldown.setData(axisCodes, index=index, headerText=_DCTE, headerEnabled=False, )

    def _tableSelectionChanged(self, headerName, value, *args, **kwargs):
        """ Callback after any pulldown is changed.
        This interacts with the backend And amends the data """
        selection = self._getSelectedSeries()
        if selection is None:
            return
        self._amendBackendData(selection.name, headerName, value)
        self.tableChanged.emit()

    def _removeModuleOverlay(self):
        for mo in self.mainWindow.moduleArea.ccpnModules:
            mo._selectedOverlay.setDropArea(None)

    def _selectionTextChanged(self, text):
        self._removeModuleOverlay()
        spectrumDisplay = self.project.getByPid(text)
        if spectrumDisplay is None:
            return
        module = self.mainWindow.ui.getByGid(text)
        if module is not None:
            module._raiseSelectedOverlay()

    def _amendBackendData(self, index, header, value):
        """Given an index, header and value, amend the backend data. Index and header must obviously be in the dataframe"""
        backend = self.backend
        data = backend.data
        data.loc[index, header] = value

    def _getTableColumIndex(self, header, ):
        for columIndex, columClass in enumerate(self._columnDefs.columns):
            rawDataHeading = columClass.rawDataHeading
            if header == rawDataHeading:
                return columIndex

    def _validateTable(self):
        """Check if all entry in the table are correct.
         :return: tuple of lists, same length of dataFrame.
                    List one:  bools of True/False for valid/invalid rows;
                    List  two: list of error messages (if any) for each row.
        """
        allValues = []
        allMsgs = []
        for rowNumber, (rowIndex, row) in enumerate(self.dataFrame.iterrows()):
            isValid, msg = self._isValidRow(rowNumber, rowIndex)
            allValues.append(isValid)
            allMsgs.append(msg)
        return allValues, allMsgs

    def _isValidRow(self, rowNumber, rowIndex):
        """
        Check all entries are ok
        :return: tuple of two items: Bool and str. isValid and error text.
        """
        spectrumDisplayTableHeader = self.columnMap.get(SOURCESPECTRUMDISPLAYPID)
        targetDisplayTableHeader = self.columnMap.get(TARGETSPECTRUMDISPLAYPID)
        sourceAxisCodeTableHeader = self.columnMap.get(SOURCEAXISCODE)
        targetAxisCodeTableHeader = self.columnMap.get(TARGETAXISCODE)

        sourceDisplay = self._getDisplayByHeader(rowIndex, spectrumDisplayTableHeader)
        targetDisplay = self._getDisplayByHeader(rowIndex, targetDisplayTableHeader)
        sourceAxis = self._getValueByHeader(rowIndex, sourceAxisCodeTableHeader)
        targetAxis = self._getValueByHeader(rowIndex, targetAxisCodeTableHeader)

        sourceDisplayColumIndex = self._getTableColumIndex(SOURCESPECTRUMDISPLAYPID)
        targetDisplayColumIndex = self._getTableColumIndex(TARGETSPECTRUMDISPLAYPID)
        sourceAxisColumIndex = self._getTableColumIndex(SOURCEAXISCODE)
        targetAxisColumIndex = self._getTableColumIndex(TARGETAXISCODE)
        valids = []
        msg = f'Inspect Row: {rowNumber + 1} at Column(s): '
        ## Check the source Display Widgets
        if sourceDisplay is None:
            self.setBackground(rowNumber, sourceDisplayColumIndex, self.INVALIDCOLOUR)
            self.setBackground(rowNumber, sourceAxisColumIndex, self.INVALIDCOLOUR)
            valids += [False]
            msg += f' {spectrumDisplayTableHeader}, {sourceAxisCodeTableHeader}; '
        else:
            self.setBackground(rowNumber, sourceDisplayColumIndex, self.VALIDCOLOUR)
            if sourceAxis not in sourceDisplay.axisCodes:
                self.setBackground(rowNumber, sourceAxisColumIndex, self.INVALIDCOLOUR)
                valids += [False]
                msg += f'{sourceAxisCodeTableHeader}. '
            else:
                self.setBackground(rowNumber, sourceAxisColumIndex, self.VALIDCOLOUR)
                valids += [True]

        ## Check the target Display Widgets
        if targetDisplay is None:
            self.setBackground(rowNumber, targetDisplayColumIndex, self.INVALIDCOLOUR)
            self.setBackground(rowNumber, targetAxisColumIndex, self.INVALIDCOLOUR)
            valids += [False]
            msg += f'{targetDisplayTableHeader}, {targetAxisCodeTableHeader}; '
        else:
            self.setBackground(rowNumber, targetDisplayColumIndex, self.VALIDCOLOUR)
            if targetAxis not in targetDisplay.axisCodes:
                self.setBackground(rowNumber, targetAxisColumIndex, self.INVALIDCOLOUR)
                valids += [False]
                msg += f'{targetAxisCodeTableHeader}.'
            else:
                self.setBackground(rowNumber, targetAxisColumIndex, self.VALIDCOLOUR)
                valids += [True]
        return all(valids), msg

    #=========================================================================================
    # convenient methods
    #=========================================================================================

    def _getDisplayByHeader(self, index, header):
        if self.project is None:
            return
        pid = self._getValueByHeader(index, header)
        return self.project.getByPid(pid)

    def _getValueByHeader(self, index, header):
        if header not in self.dataFrame:
            return
        if index not in self.dataFrame.index:
            return
        return self.dataFrame.loc[index, header]

    def _getSelectedSeries(self):
        ll = self.getSelectedObjects()
        if len(ll) > 0:
            return ll[-1]
        return

    def populateTable(self):
        """Populate the table
        """
        df = self.backend.data
        self.setDataFrame(df)
        self.setTableEnabled(True)

    def setTableEnabled(self, value):
        """Enable/Disable the table.
        :param value: True/False.
        :return:
        """
        self.setEnabled(value)
        # not sure whether to disable the table or just disable the editing and menu items
        self.setEditable(value)
        for action in self._actions:
            action.setEnabled(value)

    def selectionCallback(self, selected, deselected, selection, lastItem):
        """
        Selection could highlight the sync-ed spectrumDisplays
        """
        row = self._getSelectedSeries()
        if row is None:
            self._removeModuleOverlay()
            return
        sourceDisplayPid = row[SOURCESPECTRUMDISPLAYPID]
        targetDisplayPid = row[TARGETSPECTRUMDISPLAYPID]
        sourceSpectrumDisplay = self.project.getByPid(sourceDisplayPid)
        targetSpectrumDisplay = self.project.getByPid(targetDisplayPid)

        if sourceSpectrumDisplay is not None and targetSpectrumDisplay is not None:
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self._removeTimer)
            self.timer.start(500)
            sourceSpectrumDisplay._raiseSelectedOverlay()
            targetSpectrumDisplay._raiseSelectedOverlay()

    def _removeTimer(self):
        self._removeModuleOverlay()
        self.timer.stop()

    #=========================================================================================
    # Table context menu
    #=========================================================================================

    def addTableMenuOptions(self, menu):
        """Add options to the right-mouse menu
        """
        menu = self._thisTableMenu
        self._actions = [
            menu.addAction('New Sync', self._newSync),
            menu.addAction('Duplicate Selected', self._duplicateSelectedSync),
            menu.addAction('Duplicate Opposite Axis', self._duplicateOppositeAxis),

            menu.addSeparator(),
            menu.addAction('Remove Selected', self._removeSelectedSync),
            menu.addAction('Remove All', self._removeAllSyncs),
            menu.addSeparator(),
            menu.addAction('Clear Selection', self.clearSelection),
            ]
        return menu

    def _newSync(self):
        """Add new sync to the table.
        """
        newRow = self.backend.fetchEmptyEntry(_DCTE)
        self.populateTable()
        self.selectRowsByValues(values=[_DCTE], headerName=SOURCESPECTRUMDISPLAYPID)

    def _duplicateSelectedSync(self):
        sel = self.getSelectedObjects()
        if len(sel) == 0:
            showWarning('Nothing to duplicate', 'Select a row first')
            return
        for i in sel:
            newRow = self.backend.cloneSync(i.name)
        self.updateTable()

    def _duplicateOppositeAxis(self):
        """Duplicate rows but with Opposite Axis """

        sel = self.getSelectedObjects()
        if len(sel) == 0:
            showWarning('Nothing to duplicate', 'Select a row first')
            return
        for i in sel:
            row = self.backend.cloneSync(i.name)
            sourceDisplayPid = row[SOURCESPECTRUMDISPLAYPID]
            targetDisplayPid = row[TARGETSPECTRUMDISPLAYPID]
            sourceAxisCode = row[SOURCEAXISCODE]
            targetAxisCode = row[TARGETAXISCODE]
            sourceDisplay = self.project.getByPid(sourceDisplayPid)
            targetDisplay = self.project.getByPid(targetDisplayPid)
            if sourceDisplay is not None:
                axes = sourceDisplay.axisCodes
                newAxis = [ax for ax in axes if ax != sourceAxisCode][0]
                self._amendBackendData(i.name, SOURCEAXISCODE, newAxis)
            if targetDisplay is not None:
                axes = targetDisplay.axisCodes
                newAxis = [ax for ax in axes if ax != targetAxisCode][0]
                self._amendBackendData(i.name, TARGETAXISCODE, newAxis)
        self.updateTable()


    def _removeSelectedSync(self):
        """Remove the selected sync from the table.
        """
        rows = self.getSelectedObjects()
        if len(rows) == 0:
            showWarning('Nothing to remove', 'Select a row first')
            return
        for row in rows:
            index = row.name
            self.backend._unsyncByIndex(index)
        self.updateTable()

    def _removeAllSyncs(self):
        """Remove all sync from the table.
        """
        yesRemoveAll = showYesNo('Delete All', 'Do you want delete all data?')
        if yesRemoveAll:
            self.backend.clearAll()
            self.updateTable()


class _SyncState(DataEnum):
    """
    _SyncState = 0 # status: done, no need to update. icon Green
    _SyncState = 1 # status: to be done, on the queue and need to update. icon Orange
    _SyncState = 2 # status: suspended, Might be updates. icon red
    """

    DONE        = 0, 'icons/link_done'
    DETECTED    = 1, 'icons/link_needsUpdate'
    SUSPENDED   = 2, 'icons/link_suspended'

class SpectrumDisplaysSyncEditorModule(CcpnModule):
    """
    """
    includeSettingsWidget = True
    maxSettingsState = 2
    settingsPosition = 'left'
    _includeInLastSeen = False  # whether to restore or not after closing it (in the same project)
    _allowRename = False
    className = 'SyncSpectrumDisplays'

    def __init__(self, mainWindow, name='SpectrumDisplay Sync Editor (Alpha)'):
        super().__init__(mainWindow=mainWindow, name=name)

        self.mainWindow = getMainWindow()
        self.application = getApplication()
        self.current = getCurrent()
        self.project = getProject()
        self._backend = SpectrumDisplaySyncHandler()
        self._syncState = _SyncState.DONE

        ## Add GUI
        hgrid = 0
        self.table = SyncSpectrumDisplaysTable(self.mainWidget, parentModule=self,  grid=(hgrid, 0), gridSpan=(2, 2))
        sx = 'Sync all open SpectrumDisplays on %s axes'
        self.editButtons = ButtonList(self.mainWidget, texts=['', '', '', ''],
                                      icons=['icons/list-add',  'icons/allXY','icons/allX','icons/allY'],
                                      tipTexts=['Add new sync', sx%'X/Y',sx%'X',sx%'Y', ],
                                      callbacks=[
                                          self.table._newSync,
                                          self._syncAllAxesOnOpenedSpectrumDisplays,
                                          partial(self._syncXAxesOnOpenedSpectrumDisplays, update=True),
                                          partial(self._syncYAxesOnOpenedSpectrumDisplays, update=True)
                                          ],
                                      direction='v',
                                      setMinimumWidth=False,
                                      grid=(hgrid, 2),
                                      vAlign='t')
        self.editButtons.setFixedWidth(30)
        hgrid += 1
        self.syncButtons = ButtonList(self.mainWidget, texts=['', ''],
                                      icons=['icons/link_done', 'icons/unlink'],
                                      tipTexts=['Re-Sync All SpectrumDisplays', 'Unsync All but keep data '],
                                      callbacks=[
                                          self._syncAll,
                                          self._unsyncAll
                                          ],
                                      direction='v',
                                      setMinimumWidth=False,
                                      grid=(hgrid, 2),
                                      vAlign='b')
        self._updateButton = self.syncButtons.buttons[0]

        self.table.setMinimumHeight(100)
        # self.table.setMinimumWidth(self._minimumWidth)
        self.table.tableChanged.connect(self._tableHasChanged)

        self.mainWidget.setContentsMargins(5, 5, 5, 5)

        # add settings:
        pRow = 0
        self._setTransitiveMode = cw.CheckBoxCompoundWidget(self.settingsWidget,
                                                            labelText='Transitive Mode',
                                                            tipText ='',
                                                            checked=True,
                                                            callback=self._setTransitiveModeCallback,
                                                            grid=(pRow, 0), stretch=(0, 0), hAlign='left',
                                                             # fixedWidths=(None, 30),

                                                         )
        self.settingsWidget.setContentsMargins(5, 5, 5, 5)
        ## Add core notifiers
        if self.project:
            self._spectrumDisplayNotifier = Notifier(self.project, [Notifier.DELETE], 'SpectrumDisplay', self._onSpectrumDisplayDeleted)

        self.setGuiNotifier(self.mainWidget, [GuiNotifier.DROPEVENT], [DropBase.PIDS],
                            callback=self._handleDrops)

    @property
    def backend(self):
        return self._backend

    ################################################
    ################ Notification callbacks ###############
    ################################################

    def _updateData(self):
        newData = self.table.dataFrame
        backend = self.backend
        backend._data = newData
        self.table.populateTable()

    def _syncXAxesOnOpenedSpectrumDisplays(self, update=True, **kwargs):
        self.backend._syncAxesOnSpectrumDisplays(self.project.spectrumDisplays, axisIndex=0)
        if update:
            self._tableHasChanged()
            self.updateTable()

    def _syncYAxesOnOpenedSpectrumDisplays(self, update=True, **kwargs):
        self.backend._syncAxesOnSpectrumDisplays(self.project.spectrumDisplays, axisIndex=1)
        if update:
            self._tableHasChanged()
            self.updateTable()

    def _syncAllAxesOnOpenedSpectrumDisplays(self, *args, **kwargs):
        self._syncXAxesOnOpenedSpectrumDisplays(update=False)
        self._syncYAxesOnOpenedSpectrumDisplays(update=False)
        self._tableHasChanged()
        self.updateTable()

    def updateTable(self):
        self.table.updateTable()

    def _handleDrops(self, dataDict, *args, **kwargs):

        objs = self.project.getObjectsByPids(dataDict.get(DropBase.PIDS))
        strips = [x for x in objs if isinstance(x, Strip)]
        if len(strips) == 0:
            return
        strip = strips[-1]
        axes = strip.axisCodes
        for axis in axes:
            newRow = self.backend.fetchEmptyEntry(_DCTE)
            self.backend.data.loc[newRow.name, SOURCESPECTRUMDISPLAYPID] = strip.spectrumDisplay.pid
            self.backend.data.loc[newRow.name, SOURCEAXISCODE] = axis
        self.table.updateTable()

    def _setTransitiveModeCallback(self, value):
        value = self._setTransitiveMode.get()
        self.backend.setTransitive(value)

    def _onSpectrumDisplayDeleted(self, callbackDict, *args):
        """Disconnect any existing signals from the deleted  spectrumDisplay"""
        spectrumDisplay = callbackDict.get(Notifier.OBJECT)
        backend = self.backend
        if self.table.dataFrame.empty:
            return
        if spectrumDisplay is None:
            return
        if not spectrumDisplay.pid in self.table.dataFrame.values:
            return
        backend.unsyncSpectrumDisplay(spectrumDisplay.pid)
        self.table.updateTable()

    def _tableHasChanged(self, *args, **kwargs):
        self._setSyncState(_SyncState.DETECTED)

    def _syncAll(self):
        if self.backend.isEmpty:
            showWarning('Nothing to sync', 'Add a row first')
            return
        allValid, msgs = self.table._validateTable()
        if all(allValid):
            self.backend._addGUIConnectionSignals()
            self._setSyncState(_SyncState.DONE)

        else:
            text = '\n'.join(msgs)
            showWarning('Could not sync', text)
            return

    def _unsyncAll(self):
        if self.backend.isEmpty:
            showWarning('Nothing to unsync', 'The table data is already empty')
            return
        self.backend._removeGUIConnectionSignals(self.backend.data)
        self._setSyncState(_SyncState.SUSPENDED)

    def _getSyncState(self):
        return self._syncState

    def _setSyncState(self, value):

        dataEnum = None
        if isinstance(value, DataEnum):
            dataEnum = value
        else:
            for i in _SyncState:
                if i.value == value:
                    dataEnum = value

        if dataEnum:
            self._updateState = dataEnum.value
            iconValue = dataEnum.description
            self._updateButton.setIcon(Icon(iconValue))

    def _closeModule(self):
        # Do all clean up
        # open a popup to close and remove all data or preserve for next time
        self.backend.clearAll()
        super()._closeModule()


from ccpn.framework.Application import getApplication


ccpnApplication = getApplication()
mainWindow = ccpnApplication.mainWindow
currentModules = [m for m in mainWindow.moduleArea.ccpnModules if m.className == SpectrumDisplaysSyncEditorModule.className]
if len(currentModules) > 0:
    showWarning('Already opened.', '')
    raise RuntimeError('already opened')
else:
    module = SpectrumDisplaysSyncEditorModule(mainWindow=mainWindow.moduleArea.mainWindow)
    mainWindow.moduleArea.addModule(module)
