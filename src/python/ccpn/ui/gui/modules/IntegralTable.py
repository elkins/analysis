"""Module Documentation
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
__dateModified__ = "$dateModified: 2024-11-15 19:34:28 +0000 (Fri, November 15, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:42 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================


from collections import OrderedDict

from ccpn.core.IntegralList import IntegralList
from ccpn.core.Integral import Integral
from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.lib.CallBack import CallBack
from ccpn.ui.gui.modules.CcpnModule import CcpnTableModule
from ccpn.ui.gui.widgets.Column import ColumnClass
from ccpn.ui.gui.widgets.PulldownListsForObjects import IntegralListPulldown
from ccpn.ui.gui.widgets.SettingsWidgets import ModuleSettingsWidget
from ccpn.ui.gui.lib._CoreTableFrame import _CoreTableWidgetABC, _CoreTableFrameABC
from ccpn.util.Logging import getLogger


logger = getLogger()

ALL = '<all>'
LINKTOPULLDOWNCLASS = 'linkToPulldownClass'


class IntegralTableModule(CcpnTableModule):
    """This class implements the module by wrapping a integralTable instance
    """
    className = 'IntegralTableModule'
    includeSettingsWidget = True
    maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    settingsPosition = 'top'
    activePulldownClass = IntegralList
    _allowRename = True

    # we are subclassing this Module, hence some more arguments to the init
    def __init__(self, mainWindow=None, name='Integral Table',
                 integralList=None, selectFirstItem=False):
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
        self._setWidgets(self.settingsWidget, self.mainWidget, integralList, selectFirstItem)
        self._setCallbacks()

    def _setWidgets(self, settingsWidget, mainWidget, integralList, selectFirstItem):
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

        # add the frame containing the pulldown and table
        self._mainFrame = _IntegralTableFrame(parent=mainWidget,
                                              mainWindow=self.mainWindow,
                                              moduleParent=self,
                                              integralList=integralList, selectFirstItem=selectFirstItem,
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
                                                   # checkBox=getattr(self.nmrResidueTableSettings, LINKTOPULLDOWNCLASS, None)
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
        if self.tableFrame:
            self.tableFrame._cleanupWidget()
        if self.activePulldownClass and self._setCurrentPulldown:
            self._setCurrentPulldown.unRegister()
        super()._closeModule()


#=========================================================================================
# _NewIntegralTableWidget
#=========================================================================================

class _NewIntegralTableWidget(_CoreTableWidgetABC):
    """Class to present an integralList Table
    """
    className = '_NewIntegralTableWidget'
    attributeName = 'integralLists'

    defaultHidden = ['Pid', 'Spectrum', 'IntegralList', 'Id']
    _internalColumns = ['isDeleted', '_object']  # columns that are always hidden

    # define self._columns here
    columnHeaders = {}
    tipTexts = ()

    # define the notifiers that are required for the specific table-type
    tableClass = IntegralList
    rowClass = Integral
    cellClass = None
    tableName = tableClass.className
    rowName = rowClass.className
    cellClassNames = None
    selectCurrent = True
    callBackClass = Integral
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
        return (self._table and self._table.integrals) or []

    @_sourceObjects.setter
    def _sourceObjects(self, value):
        # shouldn't need this
        self._table.integrals = value

    @property
    def _sourceCurrent(self):
        """Get/set the associated list of current objects
        """
        return self.current.integrals

    @_sourceCurrent.setter
    def _sourceCurrent(self, value):
        if value:
            self.current.integrals = value
        else:
            self.current.clearIntegrals()

    #=========================================================================================
    # Widget callbacks
    #=========================================================================================

    def actionCallback(self, selection, lastItem):
        """Notifier DoubleClick action on item in table
        """
        try:
            if not (objs := list(lastItem[self._OBJECT])):
                return
        except Exception as es:
            getLogger().debug2(f'{self.__class__.__name__}.actionCallback: No selection\n{es}')
            return

        if isinstance(objs, (tuple, list)):
            integral = objs[0]
        else:
            integral = objs

        # self._showRegions()
        self._navigateToPosition()

    #=========================================================================================
    # Create table and row methods
    #=========================================================================================

    #=========================================================================================
    # Table context menu
    #=========================================================================================

    #=========================================================================================
    # Table functions
    #=========================================================================================

    def _getTableColumns(self, integralList=None):
        """Define the columns for the table
        """
        figureOfMeritTipText = 'Figure of merit'
        commentsTipText = 'Textual notes about the integral'

        columnDefs = ColumnClass([
            ('#', lambda il: il.serial, 'Integral serial', None, None),
            ('Pid', lambda il: il.pid, 'Pid of integral', None, None),
            ('_object', lambda il: il, 'Object', None, None),

            ('Spectrum', lambda il: il.integralList.spectrum.id, 'Spectrum containing the Integral', None, None),
            ('IntegralList', lambda il: il.integralList.serial, 'IntegralList containing the Integral', None, None),
            # ('Id', lambda il: il.serial, 'Integral serial', None, None),

            ('Value', lambda il: il.value, '', None, None),
            ('Lower Limit', lambda il: self._getLowerLimit(il), '', None, None),
            ('Higher Limit', lambda il: self._getHigherLimit(il), '', None, None),
            ('ValueError', lambda il: il.valueError, '', None, None),
            ('Bias', lambda il: il.bias, '', None, None),
            ('FigureOfMerit', lambda il: il.figureOfMerit, figureOfMeritTipText,
             lambda il, value: self._setFigureOfMerit(il, value), None),
            ('Baseline', lambda il: il.baseline, 'Baseline for the integral area',
             lambda il, value: self._setBaseline(il, value), None),
            ('Slopes', lambda il: il.slopes, '', None, None),
            # ('Annotation', lambda il: il.annotation, '', None, None),
            ('Comment', lambda il: self._getCommentText(il), commentsTipText,
             lambda il, value: self._setComment(il, value), None), ]
                )  #      [Column(colName, func, tipText=tipText, setEditValue=editValue, format=columnFormat)

        return columnDefs

    #=========================================================================================
    # Updates
    #=========================================================================================

    #=========================================================================================
    # Widgets callbacks
    #=========================================================================================

    def _navigateToPosition(self):
        """If current strip contains the double-clicked peak will navigateToPositionInStrip
        """
        from ccpn.ui.gui.lib.StripLib import navigateToPositionInStrip, _getCurrentZoomRatio

        integral = self.current.integral
        if self.current.strip is not None:
            try:
                widths = _getCurrentZoomRatio(self.current.strip.viewRange())
                if len(integral.limits) == 1:
                    positions = integral.limits[0]
                    navigateToPositionInStrip(strip=self.current.strip, positions=positions, widths=widths)
            except Exception as es:
                logger.warning('Impossible to navigate to peak position.', es)
        else:
            logger.warning('Impossible to navigate to peak position. Set a current strip first')

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
    def _setBaseline(obj, value):
        """CCPN-INTERNAL: Edit baseline of integral
        """
        obj.baseline = float(value) if value is not None else None

    @staticmethod
    def _getHigherLimit(integral):
        """Returns HigherLimit
        """
        if integral is not None:
            if len(integral.limits) > 0:
                limits = integral.limits[0]
                if limits is not None:
                    return float(max(limits))

    @staticmethod
    def _getLowerLimit(integral):
        """Returns Lower Limit
        """
        if integral is not None:
            if len(integral.limits) > 0:
                limits = integral.limits[0]
                if limits:
                    return float(min(limits))


#=========================================================================================
# IntegralTableFrame
#=========================================================================================

class _IntegralTableFrame(_CoreTableFrameABC):
    """Frame containing the pulldown and the table widget
    """
    _TableKlass = _NewIntegralTableWidget
    _PulldownKlass = IntegralListPulldown

    def __init__(self, parent, mainWindow=None, moduleParent=None,
                 integralList=None, selectFirstItem=False, **kwds):
        super().__init__(parent, mainWindow=mainWindow, moduleParent=moduleParent,
                         obj=integralList, selectFirstItem=selectFirstItem, **kwds)

    #=========================================================================================
    # Properties
    #=========================================================================================

    @property
    def _tableCurrent(self):
        """Return the list of source objects, e.g., _table.peaks/_table.nmrResidues
        """
        return self.current.integralList

    @_tableCurrent.setter
    def _tableCurrent(self, value):
        self.current.integralList = value


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
    _module = IntegralTableModule(mainWindow=mainWindow)
    mainWindow.moduleArea.addModule(_module)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    """Call the test function
    """
    main()
