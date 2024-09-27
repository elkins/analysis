"""Module Documentation here

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

from ccpn.core.PeakList import PeakList
from ccpn.core.Peak import Peak
from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.lib.peakUtils import getPeakPosition, getPeakAnnotation, getPeakLinewidth
from ccpn.core.lib.Notifiers import Notifier
from ccpn.ui.gui.modules.CcpnModule import CcpnTableModule
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.PulldownListsForObjects import PeakListPulldown
from ccpn.ui.gui.widgets.Column import ColumnClass
from ccpn.ui.gui.lib.GuiStripContextMenus import _selectedPeaksMenuItem, _addMenuItems, \
    _getNdPeakMenuItems, _setEnabledAllItems
from ccpn.ui.gui.widgets.SettingsWidgets import ModuleSettingsWidget
from ccpn.ui.gui.lib._CoreTableFrame import _CoreTableWidgetABC, _CoreTableFrameABC
from ccpn.ui.gui.widgets.table._TableAdditions import TableMenuABC
from ccpn.util.Common import makeIterableList
from ccpn.util.Logging import getLogger


logger = getLogger()

UNITS = ['ppm', 'Hz', 'point']
ALL = '<all>'
LINKTOPULLDOWNCLASS = 'linkToPulldownClass'


class PeakTableModule(CcpnTableModule):
    """This class implements the module by wrapping a PeakListTable instance
    """

    className = 'PeakTableModule'
    includeSettingsWidget = True
    maxSettingsState = 2
    settingsPosition = 'top'

    activePulldownClass = PeakList
    _allowRename = True

    def __init__(self, mainWindow=None, name='Peak Table',
                 peakList=None, selectFirstItem=False):
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
        self._setWidgets(self.settingsWidget, self.mainWidget, peakList, selectFirstItem)
        self._setCallbacks()

    def _setWidgets(self, settingsWidget, mainWidget, peakList, selectFirstItem):
        """Set up the widgets for the module
        """
        self._settings = None
        if self.activePulldownClass:
            # add to settings widget - see sequenceGraph for more detailed example
            settingsDict = OrderedDict(
                    ((LINKTOPULLDOWNCLASS, {'label'   : f'Link to current {self.activePulldownClass.className}',
                                            'tipText' : f'Set/update current {self.activePulldownClass.className} when selecting from pulldown',
                                            'callBack': None,
                                            'enabled' : True,
                                            'checked' : False,
                                            '_init'   : None}),
                     ))

            self._settings = ModuleSettingsWidget(parent=settingsWidget, mainWindow=self.mainWindow,
                                                  settingsDict=settingsDict,
                                                  grid=(0, 0))

        # add the frame containing the pulldown and table
        self._mainFrame = _PeakTableFrame(parent=mainWidget,
                                          mainWindow=self.mainWindow,
                                          moduleParent=self,
                                          peakList=peakList, selectFirstItem=selectFirstItem,
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
        """Select the object in the table
        """
        self._mainFrame.selectTable(table)

    def selectPeaks(self, peaks):
        """Select the peaks in the table
        """
        pids = self.project.getPidsByObjects(peaks)
        self._mainFrame.guiTable.selectRowsByValues(pids, 'Pid')

    def _closeModule(self):
        """CCPN-INTERNAL: used to close the module
        """
        if self.activePulldownClass:
            if self._settings:
                self._settings._cleanupWidget()
        if self.tableFrame:
            self.tableFrame._cleanupWidget()

        super()._closeModule()

    def _getLastSeenWidgetsState(self):
        """ Internal. Used to restore last closed module in the same program instance. """
        widgetsState = self.widgetsState
        try:
            # Don't restore the pulldown selection from last seen.
            pulldownSaveName = self.tableFrame._modulePulldown.pulldownList.objectName()
            widgetsState.pop(f'__{pulldownSaveName}', None)
        except Exception as err:
            getLogger().debug2(f'Could not remove the pulldown state from PeakTable module. {err}')
        return widgetsState


#=========================================================================================
# Peak table menu
#=========================================================================================


class _PeakTableOptions(TableMenuABC):
    """Class to handle peak-table options from a right-mouse menu.
    """

    def addMenuOptions(self, menu):
        """Add options to the right-mouse menu
        """
        parent = self._parent

        menu.addSeparator()
        _peakItem = _selectedPeaksMenuItem(None)
        _addMenuItems(parent, menu, [_peakItem])

        # _selectedPeaksMenu submenu - add to Strip._selectedPeaksMenu
        items = _getNdPeakMenuItems(menuId='Main')
        # attach to the _selectedPeaksMenu submenu
        _addMenuItems(parent, parent._selectedPeaksMenu, items)

    def setMenuOptions(self, menu):
        """Update options in the right-mouse menu
        """
        parent = self._parent
        submenu = parent._selectedPeaksMenu

        # Enable/disable menu items as required
        parent._navigateToPeakMenuMain.setEnabled(False)
        _setEnabledAllItems(submenu, bool(parent.current.peaks))

    #=========================================================================================
    # Properties
    #=========================================================================================

    pass

    #=========================================================================================
    # Class methods
    #=========================================================================================

    pass

    #=========================================================================================
    # Implementation
    #=========================================================================================

    pass


#=========================================================================================
# _NewPeakTableWidget
#=========================================================================================

class _NewPeakTableWidget(_CoreTableWidgetABC):
    """Class to present a peakList Table
    """
    className = '_NewPeakTableWidget'
    attributeName = 'peakLists'

    defaultHidden = ['Pid', 'Spectrum', 'PeakList', 'Id', 'HeightError', 'VolumeError']
    _internalColumns = ['isDeleted', '_object']  # columns that are always hidden

    # define self._columns here
    columnHeaders = {'#'          : '#',
                     'Pid'        : 'Pid',
                     '_object'    : '_object',
                     'Spectrum'   : 'Spectrum',
                     'PeakList'   : 'PeakList',
                     'Assign F1'  : 'Assign F1',
                     'Assign F2'  : 'Assign F2',
                     'Assign F3'  : 'Assign F3',
                     'Assign F4'  : 'Assign F4',
                     'Assign F5'  : 'Assign F5',
                     'Assign F6'  : 'Assign F6',
                     'Assign F7'  : 'Assign F7',
                     'Assign F8'  : 'Assign F8',
                     'Pos F1'     : 'Pos F1',
                     'Pos F2'     : 'Pos F2',
                     'Pos F3'     : 'Pos F3',
                     'Pos F4'     : 'Pos F4',
                     'Pos F5'     : 'Pos F5',
                     'Pos F6'     : 'Pos F6',
                     'Pos F7'     : 'Pos F7',
                     'Pos F8'     : 'Pos F8',
                     'LW F1 (Hz)' : 'LW F1 (Hz)',
                     'LW F2 (Hz)' : 'LW F2 (Hz)',
                     'LW F3 (Hz)' : 'LW F3 (Hz)',
                     'LW F4 (Hz)' : 'LW F4 (Hz)',
                     'LW F5 (Hz)' : 'LW F5 (Hz)',
                     'LW F6 (Hz)' : 'LW F6 (Hz)',
                     'LW F7 (Hz)' : 'LW F7 (Hz)',
                     'LW F8 (Hz)' : 'LW F8 (Hz)',
                     'Height'     : 'Height',
                     'HeightError': 'HeightError',
                     'S/N'        : 'S/N',
                     'Volume'     : 'Volume',
                     'VolumeError': 'VolumeError',
                     'ClusterId'  : 'ClusterId',
                     'Merit'      : 'Merit',
                     'Annotation' : 'Annotation',
                     'Comment'    : 'Comment',
                     }

    tipTexts = ('Peak serial number',
                'Pid of the Peak',
                'Object',
                'Spectrum containing the Peak',
                'PeakList containing the Peak',
                'NmrAtom assignments of peak in dimension 1',
                'NmrAtom assignments of peak in dimension 2',
                'NmrAtom assignments of peak in dimension 3',
                'NmrAtom assignments of peak in dimension 4',
                'NmrAtom assignments of peak in dimension 5',
                'NmrAtom assignments of peak in dimension 6',
                'NmrAtom assignments of peak in dimension 7',
                'NmrAtom assignments of peak in dimension 8',
                'Peak position in dimension 1',
                'Peak position in dimension 2',
                'Peak position in dimension 3',
                'Peak position in dimension 4',
                'Peak position in dimension 5',
                'Peak position in dimension 6',
                'Peak position in dimension 7',
                'Peak position in dimension 8',
                'Peak line width in dimension 1',
                'Peak line width in dimension 2',
                'Peak line width in dimension 3',
                'Peak line width in dimension 4',
                'Peak line width in dimension 5',
                'Peak line width in dimension 6',
                'Peak line width in dimension 7',
                'Peak line width in dimension 8',
                'Magnitude of spectrum intensity at peak center (interpolated), unless user edited',
                'Error of the height',
                'Signal to Noise Ratio',
                'Integral of spectrum intensity around peak location, according to chosen volume method',
                'Error of the volume',
                'The peak clusterId. ClusterIds are used for grouping peaks in fitting routines',
                'Figure of merit',
                'Any other peak label (excluded assignments)',
                'Optional user comment'
                )

    # define the notifiers that are required for the specific table-type
    tableClass = PeakList
    rowClass = Peak
    cellClass = None
    tableName = tableClass.className
    rowName = rowClass.className
    cellClassNames = {NmrAtom: 'assignedPeaks'}
    selectCurrent = True
    callBackClass = Peak
    search = False

    # set the queue handling parameters
    _maximumQueueLength = 25

    positionsUnit = UNITS[0]  # default

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _sourceObjects(self):
        """Get/set the list of source objects
        """
        return (self._table and self._table.peaks) or []

    @_sourceObjects.setter
    def _sourceObjects(self, value):
        # shouldn't need this
        self._table.peaks = value

    @property
    def _sourceCurrent(self):
        """Get/set the associated list of current objects
        """
        return self.current.peaks

    @_sourceCurrent.setter
    def _sourceCurrent(self, value):
        if value:
            self.current.peaks = value
        else:
            self.current.clearPeaks()

    #=========================================================================================
    # Widget callbacks
    #=========================================================================================

    def actionCallback(self, selection, lastItem):
        """If current strip contains the double-clicked peak will navigateToPositionInStrip
        """
        from ccpn.ui.gui.lib.StripLib import navigateToPositionInStrip, _getCurrentZoomRatio

        try:
            if not (objs := list(lastItem[self._OBJECT])):
                return
        except Exception as es:
            getLogger().debug2(f'{self.__class__.__name__}.actionCallback: No selection\n{es}')
            return

        peak = objs[0] if isinstance(objs, (tuple, list)) else objs

        if self.current.strip is not None:
            validPeakListViews = [pp.peakList for pp in self.current.strip.peakListViews if
                                  isinstance(pp.peakList, PeakList)]

            if peak and peak.peakList in validPeakListViews:
                widths = None

                if peak.peakList.spectrum.dimensionCount <= 2:
                    widths = _getCurrentZoomRatio(self.current.strip.viewRange())
                navigateToPositionInStrip(strip=self.current.strip,
                                          positions=peak.position,
                                          axisCodes=peak.axisCodes,
                                          widths=widths)
        else:
            logger.warning('Impossible to navigate to peak position. Set a current strip first')

    #=========================================================================================
    # Create table and row methods
    #=========================================================================================

    def getCellToRows(self, cellItem, attribute=None):
        """Get the list of objects which cellItem maps to for this table
        To be subclassed as required
        """
        # this is a step towards making guiTableABC and subclass for each table
        # return makeIterableList(getattr(cellItem, attribute, [])), Notifier.CHANGE

        return makeIterableList(cellItem._oldAssignedPeaks) if cellItem.isDeleted \
            else makeIterableList(cellItem.assignedPeaks), \
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

    # currently in _PeakTableOptions

    def addTableMenuOptions(self, menu):
        self.peakMenu = _PeakTableOptions(self, True)
        self._tableMenuOptions.append(self.peakMenu)

        super().addTableMenuOptions(menu)

    #=========================================================================================
    # Table functions
    #=========================================================================================

    def _getTableColumns(self, peakList=None):
        """Add default columns plus the ones according to peakList.spectrum dimension
        format of column = ( Header Name, value, tipText, editOption)
        editOption allows the user to modify the value content by doubleclick
        """

        columnDefs = [('#', lambda pk: pk.serial, 'Peak serial number', None, None),
                      ('Pid', lambda pk: pk.pid, 'Pid of the Peak', None, None),
                      ('_object', lambda pk: pk, 'Object', None, None),
                      ('Spectrum', lambda pk: pk.peakList.spectrum.id, 'Spectrum containing the Peak', None, None),
                      ('PeakList', lambda pk: pk.peakList.serial, 'PeakList containing the Peak', None, None),
                      # ('Id', lambda pk: pk.serial, 'Peak serial', None, None)
                      ]

        # Serial column

        if peakList and peakList.spectrum:
            # Assignment column
            for i in range(peakList.spectrum.dimensionCount):
                assignTipText = f'NmrAtom assignments of peak in dimension {str(i + 1)}'
                columnDefs.append((f'Assign F{str(i + 1)}', lambda pk, dim=i: getPeakAnnotation(pk, dim), assignTipText,
                                   None, None))

            # # Expanded Assignment columns
            # for i in range(peakList.spectrum.dimensionCount):
            #     assignTipText = 'NmrAtom assignments of peak in dimension %s' % str(i + 1)
            #     columnDefs.append(('Assign F%s' % str(i + 1), lambda pk, dim=i: self._getNmrChain(pk, dim), assignTipText, None, None))
            #     columnDefs.append(('Assign F%s' % str(i + 1), lambda pk, dim=i: self._getSequenceCode(pk, dim), assignTipText, None, None))
            #     columnDefs.append(('Assign F%s' % str(i + 1), lambda pk, dim=i: self._getResidueType(pk, dim), assignTipText, None, None))
            #     columnDefs.append(('Assign F%s' % str(i + 1), lambda pk, dim=i: self._getAtomType(pk, dim), assignTipText, None, None))

            # Peak positions column
            for i in range(peakList.spectrum.dimensionCount):
                positionTipText = f'Peak position in dimension {str(i + 1)}'
                columnDefs.append((f'Pos F{str(i + 1)}',
                                   lambda pk, dim=i, unit=self.positionsUnit: getPeakPosition(pk, dim, unit),
                                   positionTipText, None, '%0.3f'))

            # line-width column TODO remove hardcoded Hz unit
            for i in range(peakList.spectrum.dimensionCount):
                linewidthTipTexts = f'Peak line width {str(i + 1)}'
                columnDefs.append((f'LW F{str(i + 1)} (Hz)', lambda pk, dim=i: getPeakLinewidth(pk, dim),
                                   linewidthTipTexts, None, '%0.3f'))

        # height column
        heightTipText = 'Magnitude of spectrum intensity at peak center (interpolated), unless user edited'
        columnDefs.extend([('Height', lambda pk: pk.height or 'None', heightTipText, None, None),
                           ('HeightError', lambda pk: pk.heightError, 'Error of the height', None, None),
                           ('S/N', lambda pk: pk.signalToNoiseRatio, 'Signal to Noise Ratio', None, None)])

        # volume column
        volumeTipText = 'Integral of spectrum intensity around peak location, according to chosen volume method'
        columnDefs.extend([('Volume', lambda pk: pk.volume or 'None', volumeTipText, None, None),
                           ('VolumeError', lambda pk: pk.volumeError, 'Error of the volume', None, None)])

        # ClusterId column
        clusterIdTipText = 'The peak clusterId. ClusterIds are used for grouping peaks in fitting routines.'
        columnDefs.append(
                ('ClusterId', lambda pk: pk.clusterId if pk.clusterId is not None else 'None', clusterIdTipText,
                 lambda pk, value: self._setClusterId(pk, value), None))

        # figureOfMerit column
        figureOfMeritTipText = 'Figure of merit'
        columnDefs.append(('Merit', lambda pk: pk.figureOfMerit, figureOfMeritTipText,
                           lambda pk, value: self._setFigureOfMerit(pk, value), None)
                          )
        # annotation column
        annotationTipText = 'Any other peak label (excluded assignments)'
        columnDefs.append(('Annotation', lambda pk: self._getAnnotation(pk), annotationTipText,
                           lambda pk, value: self._setAnnotation(pk, value), None))

        # comment column
        commentsTipText = 'Textual notes about the peak'
        columnDefs.append(('Comment', lambda pk: self._getCommentText(pk), commentsTipText,
                           lambda pk, value: self._setComment(pk, value), None)
                          )

        colDefs = ColumnClass(columnDefs)
        idx = colDefs.headings.index('Merit')

        from ccpn.ui.gui.widgets.DoubleSpinbox import DoubleSpinbox

        # define the edit widget for the 'merit' column
        col = colDefs.columns[idx]
        col.editClass = DoubleSpinbox
        col.editKw = {'min': 0, 'max': 1, 'step': 0.1}

        return colDefs

    #=========================================================================================
    # Updates
    #=========================================================================================

    #=========================================================================================
    # Widgets callbacks
    #=========================================================================================

    def _pulldownUnitsCallback(self, unit):
        # update the table with new units
        self._setPositionUnit(unit)
        self._updateAllModule()

    def _pulldownPLcallback(self, data):
        self._updateAllModule()

    def _copyPeaks(self):
        from ccpn.ui.gui.popups.CopyPeaksPopup import CopyPeaks

        popup = CopyPeaks(parent=self.mainWindow, mainWindow=self.mainWindow)
        self._selectedPeakList = self.project.getByPid(self.pLwidget.getText())
        if self._selectedPeakList is not None:
            spectrum = self._selectedPeakList.spectrum
            popup._selectSpectrum(spectrum)
            popup._selectPeaks(self.current.peaks)
        popup.exec_()

    def _setPositionUnit(self, value):
        if value in UNITS:
            self.positionsUnit = value

    #=========================================================================================
    # object properties
    #=========================================================================================

    @staticmethod
    def _setFigureOfMerit(obj, value):
        """CCPN-INTERNAL: Set figureOfMerit from table
        Must be a floatRatio in range [0.0, 1.0]
        """
        # clip and set the figure of merit
        obj.figureOfMerit = min(max(float(value), 0.0), 1.0) if value is not None else None

    @staticmethod
    def _setClusterId(obj, value):
        """CCPN-INTERNAL: Set clusterId from table
        Must be a positive integer
        """
        try:
            if value == '':
                value = None
            v = int(value) if value is not None else None
            obj.clusterId = v
        except Exception as err:
            getLogger().warning('Could not set clusterID.', err)


#=========================================================================================
# PeakTableFrame
#=========================================================================================

class _PeakTableFrame(_CoreTableFrameABC):
    """Frame containing the pulldown and the table widget
    """
    _TableKlass = _NewPeakTableWidget
    _PulldownKlass = PeakListPulldown

    def __init__(self, parent, mainWindow=None, moduleParent=None,
                 peakList=None, selectFirstItem=False, **kwds):
        super().__init__(parent, mainWindow=mainWindow, moduleParent=moduleParent,
                         obj=peakList, selectFirstItem=selectFirstItem, **kwds)

        # create widgets for selection of position units
        self.posUnitPulldownLabel = Label(parent=self, text=' Position Unit', )
        self.posUnitPulldown = PulldownList(parent=self, texts=UNITS, callback=self._pulldownUnitsCallback,
                                            objectName='posUnits_PT')

        self.addWidgetToTop(self.posUnitPulldownLabel, 2)
        self.addWidgetToTop(self.posUnitPulldown, 3)

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _tableCurrent(self):
        """Return the list of source objects, e.g., _table.peaks/_table.nmrResidues
        """
        return self.current.peakList

    @_tableCurrent.setter
    def _tableCurrent(self, value):
        self.current.peakList = value

    #=========================================================================================
    # Widgets callbacks
    #=========================================================================================

    def _pulldownUnitsCallback(self, unit):
        """Pass units change callback to the table
        """
        self._tableWidget._pulldownUnitsCallback(unit)

    def _setPositionUnit(self, value):
        """Change the units in the table
        """
        self._tableWidget._setPositionUnit(value)


#=========================================================================================
# main
#=========================================================================================

def main():
    """Show the PeakTable module
    """
    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # create a new test application
    app = newTestApplication(interface='Gui')
    application = getApplication()
    mainWindow = application.ui.mainWindow

    # add a module
    _module = PeakTableModule(mainWindow=mainWindow)
    mainWindow.moduleArea.addModule(_module)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    """Call the test function
    """
    main()
