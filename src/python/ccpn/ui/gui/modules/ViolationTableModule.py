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
__dateModified__ = "$dateModified: 2024-12-12 13:43:35 +0000 (Thu, December 12, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2021-10-29 16:38:09 +0100 (Fri, October 29, 2021) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtWidgets, QtGui
import pandas as pd
from collections import OrderedDict

from ccpn.core.ViolationTable import ViolationTable as KlassTable
from ccpn.ui.gui.modules.CcpnModule import CcpnTableModule
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.PulldownListsForObjects import ViolationTablePulldown as KlassPulldown, RestraintTablePulldown
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Splitter import Splitter
from ccpn.ui.gui.widgets.MoreLessFrame import MoreLessFrame
from ccpn.ui.gui.widgets.SettingsWidgets import ModuleSettingsWidget
from ccpn.ui.gui.widgets.table.Table import Table
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar
from ccpn.core.lib.Notifiers import Notifier
from ccpn.util.Logging import getLogger
from ccpn.util.Common import camelCaseToString, NOTHING


ALL = '<all>'
_RESTRAINTTABLE = 'restraintTable'
LINKTOPULLDOWNCLASS = 'linkToPulldownClass'
_TABLES = 'tables'
_HIDDENCOLUMNS = 'hiddenColumns'


#=========================================================================================
# ViolationTableModule
#=========================================================================================

class ViolationTableModule(CcpnTableModule):
    """This class implements the module by wrapping a ViolationTable instance.
    """
    className = 'ViolationTableModule'
    includeSettingsWidget = True
    maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
    settingsPosition = 'top'
    _allowRename = True
    activePulldownClass = KlassTable
    _includeInLastSeen = False

    def __init__(self, mainWindow=None, name=NOTHING,
                 table=None, selectFirstItem=False):
        """Initialise the Module widgets.
        """
        if name is NOTHING:
            name=camelCaseToString(KlassTable.className)
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
        self._setWidgets()
        self._setCallbacks()

        if table is not None:
            self._selectTable(table)
        elif selectFirstItem:
            self._modulePulldown.selectFirstItem()

    def _setWidgets(self):
        """Set up the widgets for the module.
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
            self._settings = ModuleSettingsWidget(parent=self.settingsWidget, mainWindow=self.mainWindow,
                                                  settingsDict=settingsDict,
                                                  grid=(0, 0))

        # make the main splitter
        self._splitter = Splitter(None, horizontal=False, grid=(0, 0), isFloatWidget=True)
        self._splitter.setContentsMargins(0, 0, 0, 0)
        self.mainWidget.getLayout().addWidget(self._splitter, 0, 0)  # MUST be inserted this way

        _topWidget = self._topFrame = Frame(None, setLayout=True,  #grid=(0, 0),
                                            )  #scrollBarPolicies=('never', 'asNeeded'))
        _bottomWidget = self._bottomFrame = Frame(None, setLayout=True,  #grid=(1, 0),
                                                  )  #scrollBarPolicies=('never', 'asNeeded'))
        self._splitter.addWidget(self._topFrame)
        self._splitter.addWidget(_bottomWidget)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setStretchFactor(1, 10)
        # self._splitter.setSizes([1000, 2000])

        # add the guiTable to the bottom
        self._tableWidget = _ViolationTableWidget(parent=_bottomWidget,
                                                  mainWindow=self.mainWindow,
                                                  moduleParent=self,
                                                  setLayout=True,
                                                  showVerticalHeader=False,
                                                  grid=(0, 0))

        Spacer(_topWidget, 5, 5,
               QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed,
               grid=(0, 0), gridSpan=(1, 1))

        row = 1
        self._modulePulldown = KlassPulldown(parent=_topWidget,
                                             mainWindow=self.mainWindow, default=None,
                                             grid=(row, 0), gridSpan=(1, 2), minimumWidths=(0, 100),
                                             showSelectName=True,
                                             sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                             callback=self._selectionPulldownCallback,
                                             )
        # fixed height
        self._modulePulldown.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)

        # row += 1
        self.labelComment = Label(_topWidget, text='comment', grid=(row, 2), hAlign='r')
        self.lineEditComment = LineEdit(_topWidget, grid=(row, 3), gridSpan=(1, 1),
                                        textAlignment='l', backgroundText='> Optional <')
        self.lineEditComment.editingFinished.connect(self._applyComment)

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        # hide the metadata in a more-less-frame
        row += 1
        self._mlFrame = MoreLessFrame(_topWidget, name='Metadata', showMore=False, grid=(row, 0), gridSpan=(1, 4))
        MLContent = self._mlFrame.contentsFrame

        mlrow = 0
        self.rtWidget = RestraintTablePulldown(parent=MLContent,
                                               mainWindow=self.mainWindow, default=None,
                                               labelText='Associated RestraintTable',
                                               grid=(mlrow, 0), gridSpan=(1, 2), minimumWidths=(0, 100),
                                               showSelectName=True,
                                               sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                               callback=self._rtPulldownCallback,
                                               )
        self.rtWidget.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)

        mlrow += 1
        Label(MLContent, text='\nmetadata', grid=(mlrow, 0), hAlign='r', vAlign='t')
        self._metadata = Table(MLContent, showVerticalHeader=False, grid=(mlrow, 1), gridSpan=(1, 3))
        self._metadata.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        self._metadata._enableSelectionCallback = False
        self._metadata._enableActionCallback = False
        self._metadata.setEditable(False)

        mlrow += 1
        Spacer(MLContent, 5, 5,
               QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed,
               grid=(mlrow, 3), gridSpan=(1, 1))
        _topWidget.getLayout().setColumnStretch(3, 1)

        row += 1
        self._mlSpacer = Spacer(_topWidget, 5, 5,
                                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding,
                                grid=(row, 3), gridSpan=(1, 1))
        _topWidget.getLayout().setColumnStretch(3, 1)

        # set the closed size of the more-less-frame
        self._baseSize = self._mlFrame.sizeHint()
        for item in self._mlFrame.findChildren(MoreLessFrame):
            self._baseSize -= item.sizeHint()
        self._mlFrame.setMaximumHeight(self._baseSize.height())
        self._splitter.setSizes([1, 10])

        self._mlFrame.setCallback(self._moreLessCallback)
        # assume all are initially closed

    def _setCallbacks(self):
        """Set the active callbacks for the module.
        """
        self._activeCheckbox = None
        if self.activePulldownClass:
            self.setNotifier(self.current,
                             [Notifier.CURRENT],
                             targetName=self.activePulldownClass._pluralLinkName,
                             callback=self._selectCurrentPulldownClass)

            # set the active callback from the pulldown
            self._activeCheckbox = self._settings.checkBoxes[LINKTOPULLDOWNCLASS]['widget']
        self.setNotifier(self.project, [Notifier.CHANGE, Notifier.DELETE],
                         KlassTable.__name__, self._updateViolationTable, onceOnly=True)

    def _closeModule(self):
        """CCPN-INTERNAL: used to close the module.
        """
        if self._modulePulldown:
            self._modulePulldown.unRegister()
        if self._tableWidget:
            self._tableWidget._close()
        if self.rtWidget:
            self.rtWidget.unRegister()
        if self._metadata:
            self._metadata.close()
        self._activeCheckbox = None
        super()._closeModule()

    def _selectTable(self, table=None):
        """Manually select a ViolationTable from the pull-down.
        """
        if not isinstance(table, KlassTable):
            getLogger().warning(f'select: Object {table} is not of type {KlassTable.className}')
            return
        else:
            for widgetObj in self._modulePulldown.textList:
                if table.pid == widgetObj:
                    self._table = table
                    self._modulePulldown.select(self._table.pid)

    def _selectionPulldownCallback(self, item):
        """Notifier Callback for selecting violationTable from the pull-down menu.
        """
        if item is not None:
            self._table = self.project.getByPid(item)
            if self._table is not None:
                self._update()
                if self.activePulldownClass and self._activeCheckbox and self._activeCheckbox.isChecked():
                    self._tableCurrent = self._table

            else:
                self._updateEmptyTable()
                if self.activePulldownClass and self._activeCheckbox and self._activeCheckbox.isChecked():
                    self._tableCurrent = None

    def _rtPulldownCallback(self, item):
        """Notifier Callback for selecting restraintTable from the pull-down menu.
        """
        try:
            if not self._table:
                return
            with undoBlockWithoutSideBar():
                self._table._restraintTableLink = item
            _df = pd.DataFrame({'name'     : self._table.metadata.keys(),
                                'parameter': self._table.metadata.values()})
            self._metadata.updateDf(_df, resize=True, setOnHeaderOnly=True)
        except Exception as es:
            # need to immediately set back to stop error on loseFocus which also fires editingFinished
            showWarning('Violation Table', str(es))

    def _update(self):
        """Update the table.
        """
        if not self._table:
            getLogger().debug(f'no table to update {self}')
            return

        df = self._table.data
        if df is not None and len(df) > 0:
            self._tableWidget.updateDf(df)
        else:
            self._tableWidget.updateDf(pd.DataFrame({}))

        _rTable = self._table._restraintTableLink
        with self.rtWidget.blockWidgetSignals():
            try:
                self.rtWidget.select(_rTable.pid)
            except Exception:
                self.rtWidget.setIndex(0)

        with self.lineEditComment.blockWidgetSignals():
            self.lineEditComment.setText(self._table.comment or '')

        _df = pd.DataFrame({'name'     : self._table.metadata.keys(),
                            'parameter': self._table.metadata.values()})
        self._metadata.updateDf(_df, resize=True, setOnHeaderOnly=True)
        self._tableWidget.postUpdateDf()  # populateTable is skipped

    def _updateEmptyTable(self):
        """Update with an empty table.
        """
        self._tableWidget.updateDf(pd.DataFrame({}))
        self.rtWidget.setIndex(0, blockSignals=True)
        self.lineEditComment.setText('')

        _df = pd.DataFrame({'name'     : [],
                            'parameter': []})
        self._metadata.updateDf(_df, resize=True, setOnHeaderOnly=True)
        self._tableWidget.postUpdateDf()  # populateEmptyTable is skipped

    def _applyComment(self):
        """Set the values in the violationTable.
        """
        if self._table:
            comment = self.lineEditComment.text()
            try:
                with undoBlockWithoutSideBar():
                    self._table.comment = comment

            except Exception as es:
                # need to immediately set back to stop error on loseFocus which also fires editingFinished
                showWarning('Data Table', str(es))

    def _selectCurrentPulldownClass(self, data):
        """Respond to change in current activePulldownClass.
        """
        if self.activePulldownClass and self._activeCheckbox and self._activeCheckbox.isChecked():
            _table = self._table = self._tableCurrent
            if _table:
                self._modulePulldown.select(_table.pid, blockSignals=True)
                self._update()

            else:
                self._modulePulldown.setIndex(0, blockSignals=True)
                self._updateEmptyTable()

    def _updateViolationTable(self, data):
        """Respond to change in violationTable.
        """
        if data:
            trigger = data.get(Notifier.TRIGGER)
            obj = data.get(Notifier.OBJECT)
            if trigger in [Notifier.DELETE, Notifier.CREATE]:
                # update pulldown
                pass

            elif trigger == Notifier.CHANGE and data[Notifier.SPECIFIERS].get('metadata'):
                # update pulldown and table
                if obj.pid == self._modulePulldown.getText():
                    self._update()

    #-----------------------------------------------------------------------------------------
    # Properties
    #-----------------------------------------------------------------------------------------

    @property
    def _tableCurrent(self):
        """Return the current object, e.g., current.multiplet/current.nmrResidue.
        """
        return self.current.violationTable

    @_tableCurrent.setter
    def _tableCurrent(self, value):
        self.current.violationTable = value

    @property
    def tableFrame(self):
        # a bit of a hack as subclasses from CcpnTableModule
        getLogger().debug(f'{self.__class__.__name__}.tableFrame: '
                          f'a bit of a hack as subclasses from CcpnTableModule')
        return None

    #-----------------------------------------------------------------------------------------
    # Callbacks
    #-----------------------------------------------------------------------------------------

    def _moreLessCallback(self, moreLessFrame):
        """Resize the opened/closed moreLessFrame.
        """
        if self._mlFrame.contentsVisible:
            # set an arbitrarily large height and remove size-constraint from spacer
            self._mlFrame.setMaximumHeight(2000)
            self._mlSpacer.changeSize(5, 5, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Ignored)
        else:
            # set to minimum height and enable size-constraint for spacer
            self._mlFrame.setMaximumHeight(self._baseSize.height())
            self._mlSpacer.changeSize(5, 5, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding)

            # force the splitter to minimise the top-section
            self._splitter.setSizes([1, 10])


#=========================================================================================
# _TableWidget
#=========================================================================================

class _ViolationTableWidget(Table):
    """Class to present a ViolationTable.
    """
    className = '_ViolationTableWidget'
    attributeName = KlassTable._pluralLinkName

    defaultHidden = []
    _internalColumns = []

    _defaultEditable = False
    _enableCopyCell = True
    _enableExport = True
    _enableSearch = True

    _rowHeightScale = 1.0

    def __init__(self, parent=None, mainWindow=None, moduleParent=None, showVerticalHeader=True, **kwds):
        """Initialise the widgets for the module.
        """
        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = self.project = self.current = None
        kwds['setLayout'] = True

        # Initialise the scroll widget and common settings
        self._initTableCommonWidgets(parent, **kwds)
        # initialise the currently attached dataFrame
        self.dataFrameObject = None

        # initialise the table
        super().__init__(parent=parent, acceptDrops=True,
                         grid=(3, 0), gridSpan=(1, 6), showVerticalHeader=showVerticalHeader,
                         )
        self.moduleParent = moduleParent

    def _postInit(self):
        from ccpn.ui.gui.widgets.DropBase import DropBase
        from ccpn.ui.gui.lib.GuiNotifier import GuiNotifier

        super()._postInit()

        # add a dropped notifier
        if self.moduleParent is not None:
            # set the dropEvent to the mainWidget of the module, otherwise the event gets stolen by Frames
            self.moduleParent.mainWidget._dropEventCallback = self._processDroppedItems
            self.moduleParent.setGuiNotifier(self,
                                             [GuiNotifier.DROPEVENT], [DropBase.PIDS],
                                             self._processDroppedItems)

    #-----------------------------------------------------------------------------------------
    # Selection/action callbacks
    #-----------------------------------------------------------------------------------------

    def selectionCallback(self, selected, deselected, selection, lastItem):
        pass

    def actionCallback(self, selection, lastItem):
        pass

    #-----------------------------------------------------------------------------------------
    # Handle drop events
    #-----------------------------------------------------------------------------------------

    def _processDroppedItems(self, data):
        """CallBack for drop-events.
        """
        pids = data.get('pids', [])
        self._handleDroppedItems(pids, KlassTable, self.moduleParent._modulePulldown)

    def _handleDroppedItems(self, pids, objType, pulldown):
        """Handle items dropped onto the table.

        :param pids: the selected objects pids
        :param objType: the instance of the obj to handle, E.g. PeakList
        :param pulldown: the pulldown of the module wich updates the table
        :return: Actions: Select the dropped item on the table or/and open a new modules if multiple drops.
        If multiple different obj instances, then asks first.
        """
        from ccpn.ui.gui.lib.MenuActions import _openItemObject

        objs = [self.project.getByPid(pid) for pid in pids]

        selectableObjects = [obj for obj in objs if isinstance(obj, objType)]
        others = [obj for obj in objs if not isinstance(obj, objType)]

        if selectableObjects:
            _openItemObject(self.mainWindow, selectableObjects[1:])
            pulldown.select(selectableObjects[0].pid)

        else:
            from ccpn.ui.gui.widgets.MessageDialog import showYesNo

            if othersClassNames := list({obj.className for obj in others if hasattr(obj, 'className')}):
                if len(othersClassNames) == 1:
                    title, msg = 'Dropped wrong item.', f"Do you want to open the {''.join(othersClassNames)} in a new module?"
                else:
                    title, msg = 'Dropped wrong items.', 'Do you want to open items in new modules?'

                if showYesNo(title, msg):
                    _openItemObject(self.mainWindow, others)

    #-----------------------------------------------------------------------------------------
    # Table context menu
    #-----------------------------------------------------------------------------------------

    # add edit/add parameters to meta-data table

    #-----------------------------------------------------------------------------------------
    # Implementation
    #-----------------------------------------------------------------------------------------

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        super(_ViolationTableWidget, self).mousePressEvent(e)

        self.setCurrent()

    def setCurrent(self):
        """Set self to current.guiTable.
        """
        if self.current is not None:
            self.current.guiTable = self


#=========================================================================================
# main
#=========================================================================================

def main():
    """Show the dataTableModule.
    """
    from ccpn.ui.gui.widgets.Application import newTestApplication
    from ccpn.framework.Application import getApplication

    # create a new test application
    app = newTestApplication(interface='Gui')
    application = getApplication()
    mainWindow = application.ui.mainWindow

    # add a module
    _module = ViolationTableModule(mainWindow=mainWindow)
    mainWindow.moduleArea.addModule(_module)

    # show the mainWindow
    app.start()


if __name__ == '__main__':
    main()
