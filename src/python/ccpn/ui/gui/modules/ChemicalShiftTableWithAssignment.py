"""This file contains AssignmentInspectorModule class

modified by Geerten 1-9/12/2016:
- intialisation with 'empty' settings possible,
- now responsive to current.nmrResidues
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
__dateModified__ = "$dateModified: 2024-11-26 10:38:14 +0000 (Tue, November 26, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: geertenv $"
__date__ = "$Date: 2016-07-09 14:17:30 +0100 (Sat, 09 Jul 2016) $"
#=========================================================================================
# Start of code
#=========================================================================================

# from PyQt5 import QtCore
# from ccpn.ui.gui.modules.CcpnModule import CcpnModule
# from ccpn.ui.gui.widgets.Frame import Frame
# from ccpn.ui.gui.widgets.Label import Label
# from ccpn.ui.gui.widgets.ListWidget import ListWidget
# # from ccpn.ui.gui.widgets.Table import ObjectTable, Column
# from ccpn.ui.gui.widgets.GuiTable import GuiTable
# from ccpn.ui.gui.widgets.Column import ColumnClass, Column
# from ccpn.util.Logging import getLogger
# from ccpn.ui.gui.widgets.CompoundWidgets import CheckBoxCompoundWidget
# from ccpn.ui.gui.widgets.CompoundWidgets import ListCompoundWidget
# from ccpn.ui.gui.widgets.Widget import Widget
# from ccpn.core.lib.peakUtils import getPeakPosition, getPeakAnnotation
# from ccpn.core.lib.Notifiers import Notifier
# from ccpn.core.NmrAtom import NmrAtom, NmrResidue
# from ccpn.core.Peak import Peak
# from ccpn.ui.gui.modules.ChemicalShiftTable import ChemicalShiftTable
# from ccpn.ui.gui.widgets.Splitter import Splitter
# from ccpn.ui.gui.widgets.MessageDialog import showWarning
# from ccpn.core.lib.CallBack import CallBack
# from ccpn.ui.gui.lib.StripLib import navigateToPositionInStrip, _getCurrentZoomRatio
# from ccpn.core.PeakList import PeakList
# from ccpn.ui.gui.widgets.SettingsWidgets import SpectrumDisplaySelectionWidget
#
#
# logger = getLogger()
# ALL = '<all>'
#
#
# # NOTE:ED - currently not used
# #  broken with updates to the ChemicalShiftTable
#
# class ChemicalShiftTableWithAssignment(CcpnModule):
#     """
#     This Module allows inspection of the NmrAtoms of a selected NmrResidue
#     It responds to current.nmrResidues, taking the last added residue to this list
#     The NmrAtom listWidget allows for selection of the nmrAtom; subsequently its assignedPeaks
#     are displayed.
#     """
#
#     # override in specific module implementations
#     className = 'AssignmentInspectorModule'
#     attributeName = 'peaks'
#
#     includeSettingsWidget = True
#     maxSettingsState = 2  # states are defined as: 0: invisible, 1: both visible, 2: only settings visible
#     Position = 'top'
#     _allowRename = True
#
#     def __init__(self, mainWindow, name='Chemical Shift Table',
#                  chemicalShiftList=None, selectFirstItem=False):
#         # CcpnModule.__init__(self, parent=mainWindow.moduleArea, name=name)
#         CcpnModule.__init__(self, mainWindow=mainWindow, name=name)  # ejb
#
#         # Derive application, project, and current from mainWindow
#         self.mainWindow = mainWindow
#         self.application = mainWindow.application
#         self.project = mainWindow.application.project
#         self.current = mainWindow.application.current
#
#         self.sampledDims = {}  #GWV: not sure what this is supposed to do
#         self.ids = []  # list of currently displayed NmrAtom ids + <all>
#
#         policies = dict(vAlign='top')
#
#         # settings window
#
#         self.splitter = Splitter(QtCore.Qt.Vertical)
#         self._chemicalShiftFrame = Frame(self.splitter,
#                                          setLayout=True)  # ejb    # self.splitter.addWidget(self.nmrResidueTable)
#         self._assignmentFrame = Frame(self.splitter,
#                                       setLayout=True)  # ejb    # self.splitter.addWidget(self.nmrResidueTable)
#         self.mainWidget.getLayout().addWidget(self.splitter)
#
#         self._AIwidget = Widget(self.settingsWidget, setLayout=True,
#                                 grid=(0, 0), vAlign='top', hAlign='left')
#
#         # cannot set a notifier for displays, as these are not (yet?) implemented and the Notifier routines
#         # underpinning the addNotifier call do not allow for it either
#         colwidth = 140
#         self.displaysWidget = SpectrumDisplaySelectionWidget(self._AIwidget, mainWindow=self.mainWindow,
#                                                              grid=(0, 0), vAlign='top', stretch=(0, 0), hAlign='left',
#                                                              vPolicy='minimal',
#                                                              #minimumWidths=(colwidth, 0, 0),
#                                                              fixedWidths=(colwidth, 2 * colwidth, None),
#                                                              orientation='left',
#                                                              labelText='Display(s)',
#                                                              tipText='SpectrumDisplay modules to respond to double-click',
#                                                              texts=[ALL] + [display.pid for display in
#                                                                             self.application.ui.mainWindow.spectrumDisplays]
#                                                              )
#         self.displaysWidget.setFixedHeights((None, None, 40))
#
#         self.sequentialStripsWidget = CheckBoxCompoundWidget(
#                 self._AIwidget,
#                 grid=(1, 0), vAlign='top', stretch=(0, 0), hAlign='left',
#                 #minimumWidths=(colwidth, 0),
#                 fixedWidths=(colwidth, 30),
#                 orientation='left',
#                 labelText='Show sequential strips',
#                 checked=False
#                 )
#
#         self.markPositionsWidget = CheckBoxCompoundWidget(
#                 self._AIwidget,
#                 grid=(2, 0), vAlign='top', stretch=(0, 0), hAlign='left',
#                 #minimumWidths=(colwidth, 0),
#                 fixedWidths=(colwidth, 30),
#                 orientation='left',
#                 labelText='Mark positions',
#                 checked=True
#                 )
#         self.autoClearMarksWidget = CheckBoxCompoundWidget(
#                 self._AIwidget,
#                 grid=(3, 0), vAlign='top', stretch=(0, 0), hAlign='left',
#                 #minimumWidths=(colwidth, 0),
#                 fixedWidths=(colwidth, 30),
#                 orientation='left',
#                 labelText='Auto clear marks',
#                 checked=True
#                 )
#
#         # main window
#         # Frame-1: NmrAtoms
#         width = 130
#         self.frame1 = Frame(self._assignmentFrame, grid=(0, 0), **policies, fShape='styledPanel', fShadow='plain',
#                             setLayout=True)  # ejb
#         self.frame1.setFixedWidth(width)
#         self.nmrAtomLabel = Label(self.frame1, 'NmrAtom(s)', bold=True,
#                                   grid=(0, 0), gridSpan=(1, 1), vAlign='center', margins=[2, 5, 2, 5])
#
#         self.attachedNmrAtomsList = ListWidget(self.frame1,
#                                                callback=self._updatePeakTableCallback, contextMenu=False,
#                                                grid=(1, 0), gridSpan=(1, 1), **policies
#                                                )
#         self.attachedNmrAtomsList.setFixedWidth(width - 2)
#
#         self.frame1.hide()
#
#         # Frame-2: peaks
#         self.frame2 = Frame(self._assignmentFrame, grid=(0, 1), gridSpan=(1, 5), **policies, fShape='styledPanel',
#                             fShadow='plain', setLayout=True)  # ejb
#         self.peaksLabel = Label(self.frame2, 'Peaks assigned to NmrAtom(s)', bold=True,
#                                 grid=(0, 0), gridSpan=(1, 1), vAlign='center', margins=[2, 5, 2, 5])
#
#         # initialise the currently attached dataFrame
#         self._hiddenColumns = ['Pid']
#         self.dataFrameObject = None
#
#         # self.assignedPeaksTable = ObjectTable(self.frame2, self.getColumns(),
#         #                                       selectionCallback=self._setCurrentPeak,
#         #                                       actionCallback=self._navigateToPeak,
#         #                                       objects=[], autoResize=True,
#         #                                       grid=(1, 0), gridSpan=(1, 5), **policies
#         #                                       )
#
#         self.assignedPeaksTable = GuiTable(parent=self.frame2,
#                                            mainWindow=self.mainWindow,
#                                            dataFrameObject=None,
#                                            setLayout=True,
#                                            autoResize=True, multiSelect=False,
#                                            selectionCallback=self._setCurrentPeak,
#                                            actionCallback=self._navigateToPeak,
#                                            grid=(1, 0), gridSpan=(1, 5),
#                                            enableDelete=False, enableSearch=False,
#                                            **policies)
#
#         #self.attachedNmrAtomsList.setFixedHeight(200)
#         #self.assignedPeaksTable.setFixedHeight(200)
#
#         # self._registerNotifiers()
#
#         self.assignedPeaksTable._peakList = None
#         # update if current.nmrResidue is defined
#         if self.application.current.nmrResidue is not None:
#             self._updateModuleCallback([self.application.current.nmrResidue])
#
#         # set the required table notifiers
#         self.assignedPeaksTable.setTableNotifiers(tableClass=None,
#                                                   rowClass=Peak,
#                                                   cellClassNames=None,
#                                                   tableName='peakList', rowName='peak',
#                                                   changeFunc=self._refreshTable,
#                                                   className=self.attributeName,
#                                                   updateFunc=self._refreshTable,
#                                                   tableSelection='_peakList',
#                                                   pullDownWidget=None,  #self.ncWidget
#                                                   callBackClass=NmrResidue,
#                                                   selectCurrentCallBack=self._updateModuleCallback,
#                                                   moduleParent=self.moduleParent)  #self._selectOnTableCurrentNmrResiduesNotifierCallback)
#
#         # main window
#         self.chemicalShiftTable = ChemicalShiftTable(parent=self._chemicalShiftFrame,
#                                                      mainWindow=self.mainWindow,
#                                                      moduleParent=self,
#                                                      setLayout=True,
#                                                      grid=(0, 0))
#         # settingsWidget
#
#         if chemicalShiftList is not None:
#             self.selectChemicalShiftList(chemicalShiftList)
#         elif selectFirstItem:
#             self.chemicalShiftTable._chemicalShiftListPulldown.selectFirstItem()
#
#     def _refreshTable(self, *args):
#         self.assignedPeaksTable.update()
#
#     def _closeModule(self):
#         """
#         CCPN-INTERNAL: used to close the module
#         """
#         self.assignedPeaksTable._close()
#         self.chemicalShiftTable._close()
#         super()._closeModule()
#
#     def _updateModuleCallback(self, data: dict):
#         """
#         Callback function: Module responsive to nmrResidues; updates the list widget with nmrAtoms and updates peakTable if
#         current.nmrAtom belongs to nmrResidue
#         """
#         if data and 'value' in data:
#             nmrResidues = data['value']
#             self.attachedNmrAtomsList.clear()
#             if nmrResidues is not None and len(nmrResidues) > 0 and len(nmrResidues[-1].nmrAtoms) > 0:
#                 # get the pids and append <all>
#                 self.ids = [atm.id for atm in nmrResidues[-1].nmrAtoms] + [ALL]
#                 self.attachedNmrAtomsList.addItems(self.ids)
#
#                 # # clear and fill the peak table
#                 # self.assignedPeaksTable.setObjects([])
#                 if self.application.current.nmrAtom is not None and self.application.current.nmrAtom.id in self.ids:
#                     self._updatePeakTable(self.application.current.nmrAtom.id)
#                 else:
#                     self._updatePeakTable(ALL)
#
#                 # new to populate table
#             else:
#                 logger.debug('No valid nmrAtom/nmrResidue defined')
#
#     def _updatePeakTableCallback(self, item):
#         """
#         Update the peakTable using item.text (which contains a NmrAtom pid or <all>)
#         """
#         if item is not None:
#             text = item.text()
#             self._updatePeakTable(text)
#         else:
#             logger.error('No valid item selected')
#
#
#     class _emptyObject():
#         def __init__(self):
#             pass
#
#
#     def _updatePeakTable(self, id):
#         """
#         Update peak table depending on value of id;
#         clears peakTable if pid is None
#         """
#         if id is None:
#             # self.assignedPeaksTable.setObjects([])
#             self.assignedPeaksTable.clearTable()
#             return
#
#         if id == ALL:
#             self.assignedPeaksTable._peakList = self._emptyObject()
#
#             self.assignedPeaksTable._peakList.peaks = list(
#                     set([pk for nmrAtom in self.application.current.nmrResidue.nmrAtoms for pk in
#                          nmrAtom.assignedPeaks]))
#
#             self.assignedPeaksTable.populateTable(rowObjects=self.assignedPeaksTable._peakList.peaks,
#                                                   columnDefs=self.getColumns()
#                                                   )
#
#             # self.project.blankNotification()
#             # objs = self.assignedPeaksTable.getSelectedObjects()
#             # self._dataFrameObject = self.assignedPeaksTable.getDataFrameFromList(table=self.assignedPeaksTable,
#             #                                                                      buildList=self.assignedPeaksTable._peakList.peaks,
#             #                                                                      colDefs=self.getColumns(),
#             #                                                                      hiddenColumns=self._hiddenColumns)
#             #
#             # # populate from the Pandas dataFrame inside the dataFrameObject
#             # self.assignedPeaksTable.setTableFromDataFrameObject(dataFrameObject=self._dataFrameObject)
#             # self.assignedPeaksTable._highLightObjs(objs)
#             # self.project.unblankNotification()
#
#             # self.assignedPeaksTable.setObjects(peaks)
#             # highlight current.nmrAtom in the list widget
#             self.attachedNmrAtomsList.setCurrentRow(self.ids.index(id))
#             self.peaksLabel.setText('Assigned peaks of NmrAtoms(s): %s' % ALL)
#         else:
#             pid = 'NA:' + id
#             nmrAtom = self.application.project.getByPid(pid)
#             #print('>>', pid, nmrAtom)
#             if nmrAtom is not None:
#                 self.assignedPeaksTable.populateTable(rowObjects=nmrAtom.assignedPeaks,
#                                                       columnDefs=self.getColumns()
#                                                       )
#
#                 # self.project.blankNotification()
#                 # objs = self.assignedPeaksTable.getSelectedObjects()
#                 # self._dataFrameObject = self.assignedPeaksTable.getDataFrameFromList(table=self.assignedPeaksTable,
#                 #                                                                      buildList=nmrAtom.assignedPeaks,
#                 #                                                                      colDefs=self.getColumns(),
#                 #                                                                      hiddenColumns=self._hiddenColumns)
#                 #
#                 # # populate from the Pandas dataFrame inside the dataFrameObject
#                 # self.assignedPeaksTable.setTableFromDataFrameObject(dataFrameObject=self._dataFrameObject)
#                 # self.assignedPeaksTable._highLightObjs(objs)
#                 # self.project.unblankNotification()
#
#                 # self.assignedPeaksTable.setObjects(nmrAtom.assignedPeaks)
#                 # highlight current.nmrAtom in the list widget
#
#                 self.attachedNmrAtomsList.setCurrentRow(self.ids.index(id))
#                 self.peaksLabel.setText('Assigned peaks of NmrAtom: %s' % nmrAtom.id)
#
#     def getColumns(self):
#         "get columns for initialisation of table"
#         columns = ColumnClass([('Peak', lambda pk: pk.serial, '', None, None),
#                                ('Pid', lambda pk: pk.pid, 'Pid of peak', None, None),
#                                ('_object', lambda pk: pk, 'Object', None, None),
#                                ('id', lambda pk: pk.serial, '', None, None)])
#         tipTexts = []
#         # get the maxmimum number of dimensions from all spectra in the project
#         numDim = max([sp.dimensionCount for sp in self.application.project.spectra] + [1])
#
#         for i in range(numDim):
#             j = i + 1
#             c = Column('Assign F%d' % j,
#                        lambda pk, dim=i: getPeakAnnotation(pk, dim),
#                        'NmrAtom assignments of peak in dimension %d' % j,
#                        None,
#                        None)
#             columns._columns.append(c)
#
#             # columns.append(c)
#             # tipTexts.append('NmrAtom assignments of peak in dimension %d' % j)
#
#             sampledDim = self.sampledDims.get(i)
#             if sampledDim:
#                 text = 'Sampled\n%s' % sampledDim.conditionVaried
#                 tipText = 'Value of sampled plane'
#                 unit = sampledDim
#
#             else:
#                 text = 'Pos F%d' % j
#                 tipText = 'Peak position in dimension %d' % j
#                 unit = 'ppm'
#
#             c = Column(text,
#                        lambda pk, dim=i, unit=unit: getPeakPosition(pk, dim, unit),
#                        tipText,
#                        None,
#                        '%0.3f')
#             columns._columns.append(c)
#
#             # columns.append(c)
#             # tipTexts.append(tipText)
#
#         return columns
#
#     # def _setCurrentPeak(self, peak, row, col):
#     def _setCurrentPeak(self, data):
#         """
#         PeakTable select callback
#         """
#         from ccpn.core.lib.CallBack import CallBack
#
#         peak = data[CallBack.OBJECT]
#         # multiselection not allowed, sot only return the first object in list
#         if peak:
#             self.application.current.peak = peak[0]
#
#     # def _navigateToPeak(self, peak, row, col):
#     def _navigateToPeak(self, data):
#         """
#         PeakTable double-click callback; navigate in to peak in current.strip
#         """
#         displays = self.displaysWidget.getDisplays()
#         if len(displays) == 0:
#             logger.warning('Undefined display module(s); select in settings first')
#             showWarning('startAssignment', 'Undefined display module(s);\nselect in settings first')
#             return
#
#         peak = data[CallBack.OBJECT]
#         if peak:
#             self.current.peak = peak
#
#             from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar
#
#             with undoBlockWithoutSideBar():
#                 # optionally clear the marks
#                 if self.autoClearMarksWidget.checkBox.isChecked():
#                     self.application.ui.mainWindow.clearMarks()
#
#                 # navigate the displays
#                 for display in displays:
#                     for strip in display.strips:
#
#                         validPeakListViews = [pp.peakList for pp in strip.peakListViews if
#                                               isinstance(pp.peakList, PeakList)]
#
#                         if peak.peakList in validPeakListViews:
#                             widths = None
#                             if peak.peakList.spectrum.dimensionCount <= 2:
#                                 widths = _getCurrentZoomRatio(strip.viewRange())
#
#                             navigateToPositionInStrip(strip=strip, positions=peak.position, widths=widths)
#
#         # peak = data[CallBack.OBJECT]
#         #
#         # from ccpn.ui.gui.lib.Strip import navigateToPositionInStrip
#         # #print('>peakTableDoubleClick>', peak)
#         # if peak is not None and self.application.current.strip is not None:
#         #   self.application.current.peak = peak
#         #   navigateToPositionInStrip(strip=self.application.current.strip, positions=peak.position)
#
#     def _getPeakHeight(self, peak):
#         """
#         Returns the height of the specified peak as formatted string or 'None' if undefined
#         """
#         if peak.height:
#             return '%7.2E' % float(peak.height)
#         else:
#             return '%s' % None
#
#     # def _getSearchWidget(self):
#     #   """
#     #   CCPN-INTERNAL: used to get searchWidget
#     #   """
#     #   return self.searchWidget
