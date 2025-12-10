"""Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
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
__dateModified__ = "$dateModified: 2025-01-06 17:46:56 +0000 (Mon, January 06, 2025) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets, QtCore
from collections import OrderedDict
from dataclasses import dataclass
from functools import partial
import contextlib

from ccpn.core.MultipletList import MultipletList
from ccpn.core.Multiplet import Multiplet
from ccpn.ui.gui.modules.CcpnModule import CcpnTableModule
from ccpn.ui.gui.modules.MultipletPeakTable import MultipletPeakTableWidget
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.PulldownListsForObjects import MultipletListPulldown
from ccpn.ui.gui.widgets.Column import ColumnClass
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Font import getFontHeight
from ccpn.ui.gui.widgets.Splitter import Splitter
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.lib.peakUtils import getPeakLinewidth, getMultipletPosition
from ccpn.ui.gui.widgets.SettingsWidgets import ModuleSettingsWidget
from ccpn.ui.gui.lib._CoreTableFrame import _CoreTableWidgetABC, _CoreTableFrameABC
from ccpn.util.OrderedSet import OrderedSet
from ccpn.util.Logging import getLogger


logger = getLogger()

UNITS = ['ppm', 'Hz', 'point']
ALL = '<all>'
LINKTOPULLDOWNCLASS = 'linkToPulldownClass'


# simple class to show items on the multipletPeakTable
@dataclass
class _PeakList:
    peaks = []
    spectrum = None


#=========================================================================================
# MultipletTableModule
#=========================================================================================

class MultipletTableModule(CcpnTableModule):
    """This class implements the module by wrapping a MultipletTable instance
    """
    className = 'MultipletTableModule'
    includeSettingsWidget = True
    maxSettingsState = 2
    settingsPosition = 'top'
    activePulldownClass = MultipletList
    _allowRename = True

    def __init__(self, mainWindow=None, name='Multiplet Table',
                 multipletList=None, selectFirstItem=False):
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

        # set the widgets and callbacks
        self._setWidgets(self.settingsWidget, self.mainWidget, multipletList, selectFirstItem)
        self._setCallbacks()

    def _setWidgets(self, settingsWidget, mainWidget, multipletList, selectFirstItem):
        """Set up the widgets for the module
        """
        self._settings = None
        if self.activePulldownClass:
            # add to settings widget - see sequenceGraph for more detailed example
            settingsDict = OrderedDict(
                    ((LINKTOPULLDOWNCLASS, {'label'   : 'Link to current %s' % self.activePulldownClass.className,
                                            'tipText' : 'Set/update current %s when selecting from pulldown' % self.activePulldownClass.className,
                                            'callBack': None,
                                            'enabled' : True,
                                            'checked' : False,
                                            '_init'   : None,
                                            }),
                     ))
            self._settings = ModuleSettingsWidget(parent=settingsWidget, mainWindow=self.mainWindow,
                                                  settingsDict=settingsDict,
                                                  grid=(0, 0))

        # add a splitter for the multiplet-peak table
        outerFrame = Frame(mainWidget, setLayout=True, grid=(0, 0), gridSpan=(1, 1))
        splitter = Splitter(horizontal=False, collapsible=False)

        outerFrame.getLayout().addWidget(splitter)

        # add the frame containing the pulldown and table
        self._mainFrame = _MultipletTableFrame(parent=mainWidget,
                                               mainWindow=self.mainWindow,
                                               moduleParent=self,
                                               multipletList=multipletList, selectFirstItem=selectFirstItem,
                                               grid=(0, 0))

        # # make the table expand to fill the frame
        # self._tableWidget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        # add the peak-table to the right
        self.peaksFrame = Frame(mainWidget, setLayout=True, grid=(0, 1))
        self.peakListTableLabel = Label(self.peaksFrame, 'Peaks:', grid=(0, 0), gridSpan=(1, 2))
        self.peakListTableLabel.setFixedHeight(getFontHeight())

        self.peakListTable = MultipletPeakTableWidget(parent=self.peaksFrame,
                                                      mainWindow=self.mainWindow,
                                                      moduleParent=self,
                                                      grid=(1, 1))
        self.spacer = Spacer(self.peaksFrame, 12, 5,
                             QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
                             grid=(1, 0))

        # make the table expand to fill the frame
        self.peakListTable.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.MinimumExpanding)

        # put the frames into the splitter
        splitter.addWidget(self._mainFrame)
        splitter.addWidget(self.peaksFrame)

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
            self.setNotifier(self.current,
                             [Notifier.CURRENT],
                             targetName=self.activePulldownClass._pluralLinkName,
                             callback=self._mainFrame._selectCurrentPulldownClass)

            # set the active callback from the pulldown
            self._mainFrame.setActivePulldownClass(coreClass=self.activePulldownClass,
                                                   checkBox=self._settings.checkBoxes[LINKTOPULLDOWNCLASS]['widget'])

        # set the dropped callback through mainWidget
        self.mainWidget._dropEventCallback = self._mainFrame._processDroppedItems

        # connect the signals for the cross-table linking
        self._tableWidget.updateLinkedTable.connect(self._updatePeakTable)
        self.tableFrame.unitsChanged.connect(self._pulldownUnitsCallback)

    def selectTable(self, table):
        """Select the object in the table
        """
        self._mainFrame.selectTable(table)

    def _postRestoreWidgetsState(self, **widgetsState):
        """Restore the widgets for multiplet-table, and attached peak-table.
        """
        try:
            hColumns: list[list[str]] | None
            if (hColumns := widgetsState.get('_hiddenColumns', None)) is not None:
                self._tableWidget.setHiddenColumns(hColumns[0])
                self.peakListTable.setHiddenColumns(hColumns[1])
        except Exception as es:
            getLogger().debug(f'{self.__class__.__name__}: Could not restore hidden-column widget-state: {es}')

    @property
    def _hiddenColumns(self) -> list[list[str]] | None:
        """Return the hidden-columns for the multiplet-table and the attached peak-table.
        If undefined, returns None.
        """
        with contextlib.suppress(Exception):
            return [self._tableWidget.hiddenColumns,
                    self.peakListTable.hiddenColumns]

    @QtCore.pyqtSlot(str)
    def _pulldownUnitsCallback(self, unit):
        """Update both tables with the new units
        """
        self._tableWidget._setPositionUnit(unit)
        self._tableWidget._updateAllModule()
        self.peakListTable._setPositionUnit(unit)
        self.peakListTable._updateAllModule()

    @QtCore.pyqtSlot(_PeakList)
    def _updatePeakTable(self, newTable):
        """Update the multiplet-peak table with a new table, signalled from the multiplet selection
        """
        self.peakListTable._table = newTable
        self.peakListTable._update()


#=========================================================================================
# _NewMultipletTableWidget
#=========================================================================================

class _NewMultipletTableWidget(_CoreTableWidgetABC):
    """Class to present an multipletList Table
    """
    updateLinkedTable = QtCore.pyqtSignal(_PeakList)

    className = '_NewMultipletTableWidget'
    attributeName = 'multipletLists'
    defaultHidden = ['Pid', 'Spectrum', 'MultipletList', 'Id']
    _internalColumns = ['isDeleted', '_object']  # columns that are always hidden

    # define self._columns here
    columnHeaders = {}
    tipTexts = ()

    # define the notifiers that are required for the specific table-type
    tableClass = MultipletList
    rowClass = Multiplet
    cellClass = None
    tableName = tableClass.className
    rowName = rowClass.className
    cellClassNames = None
    selectCurrent = True
    callBackClass = Multiplet
    search = False

    # set the queue handling parameters
    _maximumQueueLength = 25

    positionsUnit = UNITS[0]  # default
    _lastPeaks = None

    #-----------------------------------------------------------------------------------------
    # Properties
    #-----------------------------------------------------------------------------------------

    @property
    def _sourceObjects(self):
        """Get/set the list of source objects
        """
        return (self._table and self._table.multiplets) or []

    @_sourceObjects.setter
    def _sourceObjects(self, value):
        # shouldn't need this
        self._table.multiplets = value

    @property
    def _sourceCurrent(self):
        """Get/set the associated list of current objects
        """
        return self.current.multiplets

    @_sourceCurrent.setter
    def _sourceCurrent(self, value):
        if value:
            self.current.multiplets = value
        else:
            self.current.clearMultiplets()

    #-----------------------------------------------------------------------------------------
    # Widget callbacks
    #-----------------------------------------------------------------------------------------

    def actionCallback(self, selection, lastItem):
        """Notifier DoubleClick action on item in table
        If current strip contains the double-clicked multiplet will navigateToPositionInStrip
        """
        from ccpn.core.PeakList import PeakList
        from ccpn.ui.gui.lib.StripLib import navigateToPositionInStrip, _getCurrentZoomRatio

        objs: Multiplet | list[Multiplet]
        try:
            if not (objs := list(lastItem[self._OBJECT])):
                return
        except Exception as es:
            getLogger().debug2(f'{self.__class__.__name__}.actionCallback: No selection\n{es}')
            return

        if isinstance(objs, (tuple, list)):
            multiplet: Multiplet = objs[0]
        else:
            multiplet: Multiplet = objs

        if multiplet:
            if len(multiplet.peaks) > 0:
                peak = multiplet.peaks[-1]
                if self.current.strip is not None:
                    validPeakListViews = [pp.peakList for pp in self.current.strip.peakListViews if
                                          isinstance(pp.peakList, PeakList)]
                    if peak.peakList in validPeakListViews:
                        widths = None
                        if peak.peakList.spectrum.dimensionCount <= 2:
                            widths = _getCurrentZoomRatio(self.current.strip.viewRange())
                        navigateToPositionInStrip(strip=self.current.strip,
                                                  positions=list(multiplet.position),
                                                  widths=widths)
            else:
                logger.warning('Impossible to navigate to peak position. No peaks in multiplet')
        else:
            logger.warning('Impossible to navigate to peak position. Set a current strip first')

    def _selectCurrentCallBack(self, data):
        super()._selectCurrentCallBack(data)
        # update the multiplet-peak table on internal selection
        self._updateMultipletPeaksOnTable()

    def _updateMultipletPeaksOnTable(self):
        """Populate the multiplet-peak-table with the multiplet-peaks
        """
        # eed to validate whether the table as changed :|
        selection = self.getSelectedObjects() or []
        # select the peaks base on the current highlighted multiplets
        peaks = tuple(OrderedSet(peak for mt in selection for peak in mt.peaks))
        if peaks == self._lastPeaks:
            return
        # create a dummy structure to hold the list of peaks
        newTable = _PeakList()
        newTable.peaks = peaks
        self._lastPeaks = peaks  # cache for changes
        newTable.spectrum = peaks[0].spectrum if peaks else None
        # signal the multiplet-peak table to update
        func = partial(self.updateLinkedTable.emit, newTable)
        if self._tableBlockingLevel == 0:
            # if not blocked then emit otherwise defer
            func()
        else:
            self._deferredFuncs.append(func)

    def _update(self):
        super()._update()
        # update the multiplet-peak table on changing the pulldown
        self._updateMultipletPeaksOnTable()

    #-----------------------------------------------------------------------------------------
    # Create table and row methods
    #-----------------------------------------------------------------------------------------

    def getCellToRows(self, cellItem, attribute=None):
        """Get the list of objects which cellItem maps to for this table
        To be subclassed as required
        """
        raise RuntimeError(f'{self.__class__.__name__}.getCellToRows not callable')

    #-----------------------------------------------------------------------------------------
    # Table context menu
    #-----------------------------------------------------------------------------------------

    # def _setContextMenu(self):
    #     """Subclass guiTable to add new items to context menu
    #     """
    #     super()._setContextMenu()
    #     # add edit multiplet to the menu
    #     self._tableMenu.insertSeparator(self._tableMenu.actions()[0])
    #     a = self._tableMenu.addAction('Edit Multiplet...', self._editMultiplets)
    #     self._tableMenu.insertAction(self._tableMenu.actions()[0], a)

    def _editMultiplets(self):
        """Raise the edit multiplet popup
        """
        from ccpn.ui.gui.popups.EditMultipletPopup import EditMultipletPopup

        multiplets = self.current.multiplets
        if len(multiplets) > 0:
            multiplet = multiplets[-1]
            popup = EditMultipletPopup(parent=self.mainWindow, mainWindow=self.mainWindow, multiplet=multiplet)
        else:
            popup = EditMultipletPopup(parent=self.mainWindow, mainWindow=self.mainWindow)
        popup.exec_()

    #-----------------------------------------------------------------------------------------
    # Table functions
    #-----------------------------------------------------------------------------------------

    def _getTableColumns(self, multipletList=None):
        """Add default columns plus the ones according to multipletList.spectrum dimension
         format of column = ( Header Name, value, tipText, editOption)
         editOption allows the user to modify the value content by doubleclick
         """

        columnDefs = [('#', 'serial', 'Multiplet serial number', None, None),
                      ('Pid', lambda ml: ml.pid, 'Pid of the Multiplet', None, None),
                      ('_object', lambda ml: ml, 'Object', None, None),
                      ('Spectrum', lambda multiplet: multiplet.multipletList.spectrum.id,
                       'Spectrum containing the Multiplet', None, None),
                      ('MultipletList', lambda multiplet: multiplet.multipletList.serial,
                       'MultipletList containing the Multiplet', None, None),
                      # ('Id', lambda multiplet: multiplet.serial, 'Multiplet serial', None, None)
                      ]

        # Serial column

        # # Assignment column
        # for i in range(multipletList.spectrum.dimensionCount):
        #     assignTipText = 'NmrAtom assignments of multiplet in dimension %s' % str(i + 1)
        #     columnDefs.append(
        #             ('Assign F%s' % str(i + 1), lambda ml, dim=i: getPeakAnnotation(ml, dim), assignTipText, None, None))

        if multipletList:
            # Multiplet positions column
            for i in range(multipletList.spectrum.dimensionCount):
                positionTipText = 'Multiplet position in dimension %s' % str(i + 1)
                columnDefs.append(('Pos F%s' % str(i + 1),
                                   lambda ml, dim=i, unit=self.positionsUnit: getMultipletPosition(ml, dim, unit),
                                   positionTipText, None, '%0.3f'))

            # line-width column
            for i in range(multipletList.spectrum.dimensionCount):
                linewidthTipTexts = 'Multiplet line width %s' % str(i + 1)
                columnDefs.append(('LW F%s' % str(i + 1),
                                   lambda ml, dim=i: getPeakLinewidth(ml, dim),
                                   linewidthTipTexts, None, '%0.3f'))
        # height column
        heightTipText = 'Magnitude of spectrum intensity at multiplet center (interpolated), unless user edited'
        columnDefs.append(('Height', lambda ml: ml.height, heightTipText, None, None))

        # volume column
        volumeTipText = 'Integral of spectrum intensity around multiplet location, according to chosen volume method'
        columnDefs.append(('Volume', lambda ml: ml.volume, volumeTipText, None, None))

        # numPeaks column
        numPeaksTipText = 'Peaks count'
        columnDefs.append(('Peaks count', lambda ml: ml.numPeaks, numPeaksTipText, None, None))

        # figureOfMerit column
        figureOfMeritTipText = 'Figure of merit'
        columnDefs.append(('Merit', lambda ml: ml.figureOfMerit, figureOfMeritTipText,
                           lambda ml, value: self._setFigureOfMerit(ml, value), None))

        # comment column
        commentsTipText = 'Optional user comment'
        columnDefs.append(('Comment', lambda ml: self._getCommentText(ml), commentsTipText,
                           lambda ml, value: self._setComment(ml, value), None))

        return ColumnClass(columnDefs)

    #-----------------------------------------------------------------------------------------
    # Updates
    #-----------------------------------------------------------------------------------------

    #-----------------------------------------------------------------------------------------
    # Widgets callbacks
    #-----------------------------------------------------------------------------------------

    def _navigateToPosition(self):
        """If current strip contains the double-clicked peak will navigateToPositionInStrip
        """
        from ccpn.ui.gui.lib.StripLib import navigateToPositionInStrip, _getCurrentZoomRatio

        multiplet = self.current.multiplet
        if self.current.strip is not None:
            # widths = None
            try:
                widths = _getCurrentZoomRatio(self.current.strip.viewRange())
                if len(multiplet.limits) == 1:
                    positions = multiplet.limits[0]
                    navigateToPositionInStrip(strip=self.current.strip, positions=positions, widths=widths)
            except Exception as es:
                logger.warning('Impossible to navigate to peak position.', es)
        else:
            logger.warning('Impossible to navigate to peak position. Set a current strip first')

    def _setPositionUnit(self, value):
        if value in UNITS:
            self.positionsUnit = value

    #-----------------------------------------------------------------------------------------
    # object properties
    #-----------------------------------------------------------------------------------------

    @staticmethod
    def _setFigureOfMerit(obj, value):
        """CCPN-INTERNAL: Set figureOfMerit from table
        Must be a floatRatio in range [0.0, 1.0]
        """
        # clip and set the figure of merit
        obj.figureOfMerit = min(max(float(value), 0.0), 1.0) if value is not None else None

    @staticmethod
    def _setBaseline(obj, value):
        """CCPN-INTERNAL: Edit baseline of multiplet
        """
        obj.baseline = float(value) if value is not None else None

    @staticmethod
    def _getHigherLimit(multiplet):
        """Returns HigherLimit
        """
        if multiplet is not None:
            if len(multiplet.limits) > 0:
                limits = multiplet.limits[0]
                if limits is not None:
                    return float(max(limits))

    @staticmethod
    def _getLowerLimit(multiplet):
        """Returns Lower Limit
        """
        if multiplet is not None:
            if len(multiplet.limits) > 0:
                limits = multiplet.limits[0]
                if limits:
                    return float(min(limits))


#=========================================================================================
# MultipletTableFrame
#=========================================================================================

class _MultipletTableFrame(_CoreTableFrameABC):
    """Frame containing the pulldown and the table widget
    """
    unitsChanged = QtCore.pyqtSignal(str)

    _TableKlass = _NewMultipletTableWidget
    _PulldownKlass = MultipletListPulldown

    def __init__(self, parent, mainWindow=None, moduleParent=None,
                 multipletList=None, selectFirstItem=False, **kwds):
        super().__init__(parent, mainWindow=mainWindow, moduleParent=moduleParent,
                         obj=multipletList, selectFirstItem=selectFirstItem, **kwds)

        # create widgets for selection of position units
        self.posUnitPulldownLabel = Label(parent=self, text=' Position Unit', )
        self.posUnitPulldown = PulldownList(parent=self, texts=UNITS, callback=self._pulldownUnitsCallback,
                                            objectName='posUnits_PT')

        self.addWidgetToTop(self.posUnitPulldownLabel, 2)
        self.addWidgetToTop(self.posUnitPulldown, 3)

    #-----------------------------------------------------------------------------------------
    # Properties
    #-----------------------------------------------------------------------------------------

    @property
    def _tableCurrent(self):
        """Return the list of source objects, e.g., _table.multiplets/_table.nmrResidues
        """
        return self.current.multipletList

    @_tableCurrent.setter
    def _tableCurrent(self, value):
        self.current.multipletList = value

    #-----------------------------------------------------------------------------------------
    # Widgets callbacks
    #-----------------------------------------------------------------------------------------

    def _pulldownUnitsCallback(self, unit):
        """Pass units change callback to the table
        """
        # signal parent to update the units of both tables
        self.unitsChanged.emit(unit)


#=========================================================================================
# main
#=========================================================================================

def main():
    """Show the MultipletTableModule
    """
    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # create a new test application
    app = newTestApplication(interface='Gui')
    application = getApplication()
    mainWindow = application.ui.mainWindow

    # add a module
    _module = MultipletTableModule(mainWindow=mainWindow)
    mainWindow.moduleArea.addModule(_module)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    """Call the test function
    """
    main()
