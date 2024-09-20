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
__dateModified__ = "$dateModified: 2024-09-13 15:20:23 +0100 (Fri, September 13, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtWidgets, QtCore
from itertools import product
import pandas as pd
from ccpn.core.Chain import Chain
from ccpn.core.lib.CallBack import CallBack
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar
from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.lib.AssignmentLib import CCP_CODES
from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Spacer import Spacer
from ccpn.ui.gui.widgets.Widget import Widget
from ccpn.ui.gui.widgets.PulldownList import PulldownList
from ccpn.ui.gui.widgets.ScrollArea import ScrollArea
from ccpn.ui.gui.widgets.Splitter import Splitter
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.SettingsWidgets import StripPlot
from ccpn.ui.gui.widgets.MessageDialog import showWarning
from ccpn.ui.gui.widgets.PulldownListsForObjects import ChainPulldown
from ccpn.ui.gui.widgets.SequenceWidget import SequenceWidget
from ccpn.ui.gui.widgets.table.Table import Table
from ccpn.ui.gui.widgets.table._TableDelegates import _TableDelegateABC
from ccpn.ui.gui.lib.StripLib import navigateToNmrResidueInDisplay, navigateToNmrAtomsInStrip
from ccpn.util.Logging import getLogger
from ccpn.util.UpdateScheduler import UpdateScheduler
from ccpn.util.UpdateQueue import UpdateQueue


ALL = '<all>'
LINKTOPULLDOWNCLASS = 'linkToPulldownClass'


class ResidueInformation(CcpnModule):
    """
    This class implements the module for a residue table and sequence module
    """
    includeSettingsWidget = True
    maxSettingsState = 2
    settingsPosition = 'left'
    className = 'ResidueInformation'

    includeDisplaySettings = False
    includeSequentialStrips = False
    includePeakLists = False
    includeNmrChains = False
    includeSpectrumTable = False
    activePulldownClass = Chain

    _residueWidth = '3'
    _textOptions = ['1', '3', '5', '7']

    def __init__(self, mainWindow, name='Residue Information', chain=None, **kwds):
        CcpnModule.__init__(self, mainWindow=mainWindow, name=name)

        # Derive application, project, and current from mainWindow
        self.mainWindow = mainWindow
        if self.mainWindow:
            self.application = mainWindow.application
            self.project = mainWindow.application.project
            self.current = mainWindow.application.current
        else:
            self.application = self.project = self.current = None

        self._setWidgets(kwds, mainWindow)

        if chain is not None:
            self._selectChain(chain)
        self._getResidues()

        # set the notifies for current chain
        self._activePulldownClass = None
        self._activeCheckbox = None
        # self._setCurrentPulldownNotifier = None

        if self.activePulldownClass:
            # self.setCurrentNotifier(targetName=self.activePulldownClass._pluralLinkName,
            #                         callback=self._selectCurrentPulldownClass)
            self.setNotifier(self.current,
                             [Notifier.CURRENT],
                             targetName=self.activePulldownClass._pluralLinkName,
                             callback=self._selectCurrentPulldownClass)

        # put these in a smaller additional class
        if self.activePulldownClass:
            self._activePulldownClass = self.activePulldownClass
            self._activeCheckbox = getattr(self._moduleSettings, LINKTOPULLDOWNCLASS, None)

        # don't need a handle to these now,
        # but would recommend a weak-ref to stop threading issue when closing
        self.setNotifier(self.project, [Notifier.RENAME], 'Residue', self._queueNotifier),
        self.setNotifier(self.project, [Notifier.CHANGE], 'Residue', self._queueNotifier),
        self.setNotifier(self.project, [Notifier.DELETE], 'Residue', self._queueNotifier),
        self.setNotifier(self.project, [Notifier.CREATE], 'Residue', self._queueNotifier)

        # notifier queue handling - should be in base-class
        self._scheduler = UpdateScheduler(self.project, self._queueProcess,
                                          name=f'ResidueInformationNotifier-{self}',
                                          log=False, completeCallback=self.update)
        self._queuePending = UpdateQueue()
        self._queueActive = None
        self._lock = QtCore.QMutex()

    def _setWidgets(self, kwds, mainWindow):
        """Set up the widgets
        """
        self._moduleSettings = StripPlot(parent=self.settingsWidget, mainWindow=self.mainWindow,
                                         includeDisplaySettings=self.includeDisplaySettings,
                                         includeSequentialStrips=self.includeSequentialStrips,
                                         includePeakLists=self.includePeakLists,
                                         includeNmrChains=self.includeNmrChains,
                                         includeSpectrumTable=self.includeSpectrumTable,
                                         activePulldownClass=self.activePulldownClass,
                                         grid=(0, 0))
        # add a splitter to contain the residue table and the sequence module
        self.splitter = Splitter(self.mainWidget, horizontal=False)
        self._sequenceWidgetFrame = Frame(None, setLayout=True)
        self.mainWidget.getLayout().addWidget(self.splitter, 1, 0)
        # initialise the sequence module
        self.thisSequenceWidget = SequenceWidget(moduleParent=self,
                                                 parent=self._sequenceWidgetFrame,
                                                 mainWindow=mainWindow,
                                                 chains=self.project.chains)
        # add a scroll area to contain the residue table
        self._widgetScrollArea = ScrollArea(parent=self.mainWidget, grid=(0, 0),
                                            scrollBarPolicies=('asNeeded', 'asNeeded'), **kwds)
        self._widgetScrollArea.setWidgetResizable(True)
        self._scrollWidget = Widget(parent=self._widgetScrollArea, setLayout=True)
        self._widgetScrollArea.setWidget(self._scrollWidget)
        self._scrollWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # insert into the mainWidget
        self.splitter.addWidget(self._widgetScrollArea)
        self.splitter.addWidget(self._sequenceWidgetFrame)
        self.splitter.setStretchFactor(0, 5)
        self.splitter.setChildrenCollapsible(False)
        # make a frame to contain the pulldown widgets
        self._pulldownFrame = Frame(self._scrollWidget, setLayout=True, showBorder=False,
                                    grid=(0, 0), gridSpan=(1, 2), hAlign='l')
        self.chainPulldown = ChainPulldown(parent=self._pulldownFrame,
                                           mainWindow=self.mainWindow, default=None,
                                           #first Chain in project (if present)
                                           grid=(0, 0), gridSpan=(1, 1), minimumWidths=(0, 100),
                                           showSelectName=True,
                                           sizeAdjustPolicy=QtWidgets.QComboBox.AdjustToContents,
                                           callback=self._selectionPulldownCallback
                                           )
        self.selectedChain = None
        self.residueLabel = Label(self._pulldownFrame, text='Residue', grid=(0, 3))
        self.residuePulldown = PulldownList(self._pulldownFrame, callback=self._setCurrentResidue,
                                            grid=(0, 4))
        self._residueWidthLabel = Label(self._pulldownFrame, text='Residue window width', grid=(0, 5))
        self._residueWidthData = PulldownList(self._pulldownFrame, grid=(0, 6))
        self._residueWidthData.setData(texts=self._textOptions)
        self._residueWidthData.set(self._residueWidth)
        self.residuePulldown.setData(sorted(CCP_CODES))
        self.selectedResidueType = self.residuePulldown.currentText()
        # set the callback after populating
        self._residueWidthData.setCallback(self._setResidueWidth)
        self._residueTable = _ResidueTable(self._scrollWidget, grid=(2, 0), gridSpan=(1, 1),
                                           selectionCallback=self._selection,
                                           actionCallback=self._action,
                                           )

        self.spacer = Spacer(self._scrollWidget, 5, 5,
                             QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding,
                             grid=(3, 1), gridSpan=(1, 1))
        self._pulldownFrame.setContentsMargins(0, 5, 5, 5)
        self._scrollWidget.setContentsMargins(5, 0, 5, 0)

    def _selection(self, *args):
        """Selection callback - single-click on item in table.
        """
        if indx := self._residueTable.selectedIndexes():
            # assume table is single-selection
            pid = indx[0].data()
            if (objs := self.project.getObjectsByPartialId(className='Residue', idStartsWith=pid)):
                self._residueClicked(objs[0])

    def _action(self, *args):
        """Action callback - double-click on item in table.
        """
        if indx := self._residueTable.selectedIndexes():
            # assume table is single-selection
            pid = indx[0].data()
            if (objs := self.project.getObjectsByPartialId(className='Residue', idStartsWith=pid)):
                self._residueDoubleClicked(objs[0])

    def _selectCurrentPulldownClass(self, data):
        """Respond to change in current activePulldownClass
        """
        if self.activePulldownClass and self._activeCheckbox and self._activeCheckbox.isChecked() and self.current.chain:
            self._selectChain(self.current.chain)

    def _selectChain(self, chain=None):
        """Manually select a Chain from the pullDown
        """
        if chain is None:
            self.chainPulldown.selectFirstItem()
        elif not isinstance(chain, Chain):
            getLogger().warning('select: Object is not of type Chain')
            raise TypeError('select: Object is not of type Chain')
        else:
            for widgetObj in self.chainPulldown.textList:
                if chain.pid == widgetObj:
                    self.selectedChain = chain
                    self.chainPulldown.select(self.selectedChain.pid)

    def _setResidueWidth(self, *args):
        self._residueWidth = self._residueWidthData.get()
        self._getResidues()

    def _selectionPulldownCallback(self, item):
        """Sets the selected chain to the specified value and updates the module.
        """
        if item == ALL:
            self.selectedChain = 'All'
        else:
            self.selectedChain = self.project.getByPid(item)
            if self._activePulldownClass and self._activeCheckbox and \
                    self.selectedChain != self.current.chain and self._activeCheckbox.isChecked():
                self.current.chain = self.selectedChain
        self._getResidues()

    def _setCurrentResidue(self, value: str):
        """Sets the selected residue to the specified value and updates the module.
        """
        self.selectedResidueType = value
        self._getResidues()

    def _updateTable(self, data):
        """Process notifier from core objects.
        """
        # too generic
        residue = data[Notifier.OBJECT]
        if residue.chain == self.selectedChain:
            # without a 'marked-for-delete' the deleted residues need to be passed to the update-table
            self._getResidues(deletedResidues=[residue] if data[Notifier.TRIGGER] == 'delete' else None)

    def _getResidues(self, deletedResidues=None):
        """Finds all residues of the selected type along with one flanking residue either side and displays
        this information in the module.
        """
        deletedResidues = deletedResidues or []
        foundResidues = []
        if self.selectedChain == 'All':
            residues = self.project.residues
        else:
            if self.selectedChain is not None:
                residues = self.selectedChain.residues
            else:
                residues = []

        # this depends on the calling method
        # immediate needs the deleted residues, queued implies deferred, and the objects are already deleted
        if residues := [res for res in residues if res not in deletedResidues and not res.isDeleted]:
            width = int(self._residueWidthData.get()) // 2
            for resInd, residue in enumerate(residues):
                if residue.residueType == self.selectedResidueType.upper():
                    # add the previous and next residue chains to the visible list for this residue
                    resList = [residue]
                    leftRes = residue.previousResidue
                    for count in range(width):
                        if leftRes and leftRes not in deletedResidues and not leftRes.isDeleted:
                            resList.insert(0, leftRes)
                            leftRes = leftRes.previousResidue
                        else:
                            resList.insert(0, None)
                    rightRes = residue.nextResidue
                    for count in range(width):
                        if rightRes and rightRes not in deletedResidues and not rightRes.isDeleted:
                            resList.append(rightRes)
                            rightRes = rightRes.nextResidue
                        else:
                            resList.append(None)
                    foundResidues.append(resList)

            self._residueTable.updateDf(pd.DataFrame([[res.id if res else '' for res in ress]
                                                      for ress in foundResidues]),
                                        resize=True, setHeightToRows=True, setWidthToColumns=True,
                                        )
            for rr, (i, checkResidues) in product(range(int(self._residueWidth)), enumerate(foundResidues)):
                if 0 <= rr < len(checkResidues):
                    if checkResidues[rr] is not None:
                        if checkResidues[rr].nmrResidue is not None:
                            self._residueTable.setBackground(i, rr, QtGui.QColor('seagreen'))

    def _residueClicked(self, residue):
        """Handle cicking a residue in the table
        """
        self.current.residue = residue

    def _residueDoubleClicked(self, residue):
        """Handle double-cicking a residue in the table
        """
        if not (residue and (nmrResidue := residue.nmrResidue)):
            return

        data = CallBack(theObject=self.project,
                        object=nmrResidue,
                        targetName=nmrResidue.className,
                        trigger=CallBack.DOUBLECLICK,
                        )
        # handle a single nmrResidue - should always contain an object
        objs = data[CallBack.OBJECT]
        if not objs:
            return
        if isinstance(objs, (tuple, list)):
            nmrResidue = objs[0]
        else:
            nmrResidue = objs

        getLogger().debug('nmrResidue=%s' % str(nmrResidue.id if nmrResidue else None))
        _settings = self._moduleSettings
        displays = []
        if self.current.strip:
            displays.append(self.current.strip.spectrumDisplay)
        if len(displays) == 0 and self._moduleSettings.displaysWidget:
            getLogger().warning('Undefined display module(s); select in settings first')
            showWarning('startAssignment', 'Undefined display module(s);\nselect in settings first')
            return

        with undoBlockWithoutSideBar():
            # optionally clear the marks
            if _settings.autoClearMarksWidget.checkBox.isChecked():
                self.application.ui.mainWindow.clearMarks()
            newWidths = []
            for specDisplay in displays:
                if self.current.strip in specDisplay.strips:

                    # just navigate to this strip
                    navigateToNmrAtomsInStrip(self.current.strip,
                                              nmrResidue.nmrAtoms,
                                              widths=newWidths,
                                              markPositions=_settings.markPositionsWidget.checkBox.isChecked(),
                                              setNmrResidueLabel=True)
                else:
                    #navigate to the specDisplay (and remove excess strips)
                    if len(specDisplay.strips) > 0:
                        newWidths = []
                        navigateToNmrResidueInDisplay(nmrResidue, specDisplay, stripIndex=0,
                                                      widths=newWidths,  #['full'] * len(display.strips[0].axisCodes),
                                                      showSequentialResidues=(len(specDisplay.axisCodes) > 2) and
                                                                             self.includeSequentialStrips and
                                                                             _settings.sequentialStripsWidget.checkBox.isChecked(),
                                                      markPositions=_settings.markPositionsWidget.checkBox.isChecked()
                                                      )
                # open the other headers to match
                for strip in specDisplay.strips:
                    if strip != self.current.strip and not strip.header.headerVisible:
                        strip.header.reset()
                        strip.header.headerVisible = True

    def _closeModule(self):
        """CCPN-INTERNAL: used to close the module
        """
        if self.chainPulldown:
            self.chainPulldown.unRegister()
        if self._residueTable:
            self._residueTable._close()
        super()._closeModule()

    #=========================================================================================
    # Notifier queue handling
    # SHOULD add some base-class methods
    #=========================================================================================

    def _queueNotifier(self, data):
        """Add the notifier to the queue handler
        """
        self._queueAppend(data)

    def _queueProcess(self):
        """Process current items in the queue
        """
        with QtCore.QMutexLocker(self._lock):
            # protect the queue switching
            self._queueActive = self._queuePending
            self._queuePending = UpdateQueue()

        try:
            getLogger().debug2(f'{self.__class__.__name__} queue update')
            self._getResidues()
        except Exception as es:
            getLogger().debug(f'Error in {self.__class__.__name__} queue update - {es}')

    def _queueAppend(self, itm):
        """Append a new item to the queue
        """
        self._queuePending.put(itm)
        if not self._scheduler.isActive and not self._scheduler.isBusy:
            self._scheduler.start()

        elif self._scheduler.isBusy:
            # caught during the queue processing event, need to restart
            self._scheduler.signalRestart()


#=========================================================================================
# _ResidueTable
#=========================================================================================

class _HighlightDelegate(_TableDelegateABC):
    def paint(self, painter, option, index):
        """Paint the contents of the cell.
        """
        focus = (option.state & QtWidgets.QStyle.State_HasFocus)
        option.state = option.state & ~QtWidgets.QStyle.State_HasFocus

        painter.save()
        pal = QtGui.QPalette()
        if (option.state & QtWidgets.QStyle.State_Selected):
            # fade the background by modifying the background colour
            if back := index.data(QtCore.Qt.BackgroundRole):
                h, s, l, a = back.getHslF()
                back.setHslF(h, 1.0, l, a)
                # colour isn't defined if the background uses a qlineargradient :|
                back = self._mergeColors(back, pal.base().color(), 0.5, 0.5)
                option.palette.setColor(QtGui.QPalette.Highlight, back)

        # bypass any other subclasses
        QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)

        if focus:
            painter.setClipRect(option.rect)
            self._focusPen.setColor(pal.highlight().color())
            painter.setPen(self._focusPen)
            painter.drawRect(option.rect)
        painter.restore()


class _ResidueTable(Table):
    # strip the colours to make a transparent table
    styleSheet = """QTableView {
                        background-color: transparent;
                        alternate-background-color: transparent;
                        border-width: 0px;
                        border-radius: 2px;
                        selection-background-color: transparent;
                        selection-color: palette(text);
                        color: palette(text);
                    }
                    """
    defaultTableDelegate = _HighlightDelegate
    _disableNewFocus = True  # allow instant click on table

    def __init__(self, parent, grid, gridSpan, selectionCallback, actionCallback):
        super().__init__(parent, showVerticalHeader=False, showHorizontalHeader=False,
                         focusBorderWidth=1, setWidthToColumns=True, setHeightToRows=True,
                         multiSelect=False, selectRows=False,
                         grid=grid, gridSpan=gridSpan,
                         selectionCallback=selectionCallback,
                         actionCallback=actionCallback,
                         tableMenuEnabled=False,
                         )
        self.setEditable(False)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSortingEnabled(False)
        self.horizontalHeader().setStretchLastSection(False)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        # paint vertical dividers to highlight the selected residues
        super().paintEvent(event)
        painter = QtGui.QPainter(self.viewport())
        painter.translate(0.5, 0.5)
        col = QtGui.QColor.fromHslF(QtGui.QColor('#3050ff').hueF(), 0.9, 0.5)
        painter.setPen(QtGui.QPen(col, 2, QtCore.Qt.SolidLine))
        # Get geometry of the centre-column
        rectTop = self.visualRect(self.model().index(0, self._df.shape[1] // 2))
        rectBottom = self.visualRect(self.model().index(self._df.shape[0] - 1, self._df.shape[1] // 2))
        # Draw grid-lines
        painter.drawLine(rectTop.topLeft(), rectBottom.bottomLeft())
        painter.drawLine(rectTop.topRight(), rectBottom.bottomRight())
