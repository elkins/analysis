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
__dateModified__ = "$dateModified: 2024-11-26 10:34:53 +0000 (Tue, November 26, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2017-04-07 10:28:42 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import math
from functools import partial
import collections
import json
import time
import os
from datetime import datetime
from ccpn.core.lib.ContextManagers import undoBlock, notificationEchoBlocking, undoBlockWithoutSideBar
from collections import OrderedDict as od
from ccpn.util.Logging import getLogger
from ccpn.core.lib.Notifiers import Notifier
from ccpn.core.Spectrum import Spectrum
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.framework.lib.pipeline.PipelineBase import Pipeline
from PyQt5 import QtCore, QtGui, QtWidgets
from ccpn.ui.gui.modules.CcpnModule import CcpnModule
from ccpn.ui.gui.widgets.Button import Button
from ccpn.ui.gui.widgets.ButtonList import ButtonList
from ccpn.ui.gui.widgets.CheckBox import CheckBox
from ccpn.ui.gui.widgets.FileDialog import LineEditButtonDialog, PipelineFileDialog, TablesFileDialog
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.LineEdit import LineEdit
from ccpn.ui.gui.widgets.PipelineWidgets import PipelineDropArea
from ccpn.ui.gui.widgets.RadioButtons import RadioButtons
from ccpn.ui.gui.widgets.ScrollArea import ScrollArea
from ccpn.ui.gui.widgets.ListWidget import ListWidget
from ccpn.ui.gui.popups.Dialog import CcpnDialog
from ccpn.ui.gui.widgets.SpectraSelectionWidget import SpectraSelectionWidget
from ccpn.ui.gui.widgets.PipelineWidgets import GuiPipe, PipesTree
from ccpn.ui.gui.widgets.MessageDialog import showWarning, showInfo, _stoppableProgressBar, progressManager
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.pipes import loadedPipes as LP
from ccpn.util.Path import aPath, joinPath
from ccpn.ui.gui.widgets import MessageDialog
from ccpn.core.lib.ContextManagers import progressHandler
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QProgressBar
from PyQt5.QtCore import QThread, pyqtSignal, QObject
import threading


Qt = QtCore.Qt
Qkeys = QtGui.QKeySequence
DropHereLabel = 'Drop SP or SG here'
# styleSheets
transparentStyle = "background-color: transparent; border: 0px solid transparent"
selectPipeLabel = '< Select Pipe >'
preferredPipeLabel = '-- Preferred Pipes --'
applicationPipeLabel = '-- Application Pipes --'
otherPipeLabel = '-- General Pipes --'
PipelineName = 'NewPipeline'
PipelinePath = 'PipelinePath'


class GuiPipeline(CcpnModule, Pipeline):
    includeSettingsWidget = True
    _includeInLastSeen = False
    maxSettingsState = 2
    settingsPosition = 'left'
    className = 'GuiPipeline'
    moduleName = 'Pipeline'

    def __init__(self, mainWindow, name=moduleName, pipes=None, templates=None, **kwds):

        # this guarantees to open the module as Gui testing
        self.project = None
        self.application = None
        self.savingDataPath = ''
        self._runAsThread = False
        # set project related variables
        if mainWindow is not None:
            self.mainWindow = mainWindow
            self.project = self.mainWindow.project
            self.application = self.mainWindow.application
            self.moduleArea = self.mainWindow.moduleArea
            self.preferences = self.application.preferences
            self.current = self.application.current

            self.generalPreferences = self.application.preferences.general
            self.templatePath = self.generalPreferences.auxiliaryFilesPath
            self.savingDataPath = self.application.pipelinePath
        if pipes is None:
            pipes = LP

        self.rebuildTemplates = True
        self._loadUserPipes()

        # init the CcpnModule
        CcpnModule.__init__(self, mainWindow=mainWindow, name=name)

        # init the Pipeline
        Pipeline.__init__(self, application=self.application, pipelineName=PipelineName, pipes=pipes)

        # set pipeline variables
        self.guiPipes = self._getGuiFromPipes(self.pipes)
        self.currentRunningPipeline = []
        self.currentGuiPipesNames = []
        self.pipelineTemplates = templates

        # set the graphics
        self._setIcons()
        self._setMainLayout()

        # set notifier
        if self.project is not None:
            self.setNotifier(self.project, [Notifier.DELETE], 'Spectrum', self._updateInputDataFromNotifier)
            # add for SpectrumGroup

    @property
    def widgetsState(self):
        return self._widgetsState

    @widgetsState.getter
    def widgetsState(self):
        """Special case of saving widgets for this module. the only thing to be saved is the filePath of the pipeline.
        The guiPipeline has its own mechanism for restoring """
        savePath = self.filePath
        self.pipeline2Json(savePath)
        return {PipelinePath: savePath}

    def restoreWidgetsState(self, **widgetsState):
        """ Overriden method from ccpnModule
            Special case of restoring widgets for this module.
          the only thing to be saved is the filePath of the pipeline. The guiPipeline has its own mechanism for restoring
        """
        if PipelinePath in widgetsState:
            if widgetsState[PipelinePath]:
                path = aPath(widgetsState[PipelinePath])
                path = path.assureSuffix('.json')
                self._openSavedPipeline(path)

    @staticmethod
    def _getGuiFromPipes(pipes):
        allGuiPipes = []
        for pipe in pipes:
            if pipe:
                if pipe.guiPipe is not None:
                    guiPipe = pipe.guiPipe
                    guiPipe.pipe = pipe
                    allGuiPipes.append(guiPipe)
                else:  #deal with pipes without Gui -> Creates just an empty GuiPipe
                    newEmptyPipe = GuiPipe
                    pipe.guiPipe = newEmptyPipe
                    newEmptyPipe.pipe = pipe
                    newEmptyPipe.pipeName = pipe.pipeName
                    newEmptyPipe.preferredPipe = False
                    allGuiPipes.append(newEmptyPipe)

        return allGuiPipes

    @property
    def guiPipes(self):
        return self._guiPipes

    @guiPipes.setter
    def guiPipes(self, guiPipes):
        """
        Set the guiPipes to the guiPipeline
        :param guiPipes:  GuiPipe class
        """

        if guiPipes is not None:
            allGuiPipes = []
            for guiPipe in guiPipes:
                allGuiPipes.append(guiPipe)
            self._guiPipes = allGuiPipes
        else:
            self._guiPipes = []

    def currentGuiPipes(self):
        """
        currently displayed pipes
        """
        return self.pipelineArea.currentGuiPipes

    def _loadUserPipes(self):

        from ccpn.framework.lib.pipeline.PipesLoader import _fetchUserPipesPath, loadPipeSysModules
        from ccpn.framework.lib.pipeline.PipesLoader import _fetchDemoPipe

        userPipesPath = _fetchUserPipesPath(self.application)
        if userPipesPath:
            getLogger().info('Loading user Pipes from: %s' % userPipesPath)
            if self.rebuildTemplates:
                _fetchDemoPipe()
            modules = loadPipeSysModules([userPipesPath])

    @property
    def pipelineTemplates(self):
        return self._pipelineTemplates

    @pipelineTemplates.setter
    def pipelineTemplates(self, pipelineTemplates):
        """
        Set the pipelineTemplates to the guiPipeline
        :param pipelineTemplates:  [{templateName: templateClass}]
        """

        if pipelineTemplates is not None:
            self._pipelineTemplates = pipelineTemplates
        else:
            self._pipelineTemplates = []

            #  TODO put notifier to update the pulldown when guiPipes change

    ####################################_________ GUI SETUP ____________###########################################
    def _setIcons(self):
        self.settingIcon = Icon('icons/applications-system')
        self.saveIcon = Icon('icons/save')
        self.openRecentIcon = Icon('icons/document_open_recent')
        self.goIcon = Icon('icons/play')
        self.filterIcon = Icon('icons/edit-find')

    def _setMainLayout(self):
        self.mainFrame = Frame(self.mainWidget, setLayout=False)
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainFrame.setLayout(self.mainLayout)
        self.inputFrame = Frame(self.mainWidget, setLayout=True)
        self.inputFrameLayout = self.inputFrame.getLayout()
        self.inputFrameLayout.setContentsMargins(10, 15, 10, 10)
        self.inputFrame.setMaximumWidth(410)

        self.mainWidget.getLayout().addWidget(self.inputFrame, 0, 0)
        self.mainWidget.getLayout().addWidget(self.mainFrame, 0, 1)

        self.saveOpenFrameLayout = QtWidgets.QHBoxLayout()
        self.goAreaLayout = QtWidgets.QHBoxLayout()
        self.pipelineAreaLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.addLayout(self.saveOpenFrameLayout)
        self.mainLayout.addLayout(self.goAreaLayout)
        self.mainLayout.addLayout(self.pipelineAreaLayout)

        self._createSaveOpenButtonGroup()
        self._addPipelineDropArea()
        self._createInputWidgets()
        self._createSettingsWidgets()

    def _createInputWidgets(self):
        #
        row = 0
        self.pipelineReNameLabel = Label(self.inputFrame, 'Name', grid=(row, 0))
        self.pipelineReNameTextEdit = LineEdit(self.inputFrame, PipelineName, grid=(row, 1))
        self.pipelineReNameTextEdit.editingFinished.connect(self._renamePipelineCallback)
        row += 1
        self.inputDataLabel = Label(self.inputFrame, 'Input Data', grid=(row, 0))
        self.inputDataList = ListWidget(self.inputFrame, acceptDrops=True, grid=(row, 1), emptyText=DropHereLabel)
        contextMenu = self._inputDataContextMenu
        self.inputDataList.setContextMenu(contextMenu)
        self.inputDataList.setMaximumHeight(100)
        self.inputDataList.setAcceptDrops(True)
        # self.inputDataList.addItem(self._getInputDataHeaderLabel())
        self.inputDataList.dropped.connect(self._itemsDropped)
        row += 1
        # PIPES SELECTION:
        self.pipesLabel = Label(self.inputFrame, 'Pipes', grid=(row, 0))
        self.pipeTreeWidget = PipesTree(self.inputFrame, guiPipeline=self, grid=(row, 1))
        self.pipeTreeWidget._addPipesToTree()
        # search widget
        row += 1
        self._resultWidget = ListWidget(self.inputFrame, contextMenu=False, callback=self.callbackResultWidget,
                                        grid=(row, 1))
        self._resultWidget.itemDoubleClicked.connect(self._resultItemDoubleClickCallback)
        self._resultWidget.keyPressEvent = self._pipesResultskeyPressEvent
        self._resultWidget.hide()
        # self._resultWidget.setContentsMargins(10, 11, 10, 10)
        # self._resultWidget.setStyleSheet('QListWidget {border: 1px;}')
        row += 1
        self._addPipesSearchWidget(row)

    def _createSaveOpenButtonGroup(self):
        # self.pipelineNameLabel = Label(self, PipelineName)
        self.saveOpenButtons = ButtonList(self, texts=['', ''],
                                          callbacks=[self._openSavedPipeline, self._savePipeline],
                                          icons=[self.openRecentIcon, self.saveIcon],
                                          tipTexts=['', ''], direction='H')
        # self.saveOpenFrameLayout.addWidget(self.pipelineNameLabel)
        self.goButton = Button(self, text='', icon=self.goIcon, callback=self._runPipeline)
        self.pipelineProgressLabel = Label(self)

        self._addMenuToOpenButton()
        self.saveOpenButtons.setStyleSheet(transparentStyle)
        self.saveOpenFrameLayout.addWidget(self.goButton)
        self.saveOpenFrameLayout.addWidget(self.pipelineProgressLabel)
        self.saveOpenFrameLayout.addStretch(1)
        self.saveOpenFrameLayout.addWidget(self.saveOpenButtons)

    def _addMenuToOpenButton(self):
        openButton = self.saveOpenButtons.buttons[0]
        menu = QtWidgets.QMenu()
        templatesItem = menu.addAction('Templates')
        subMenu = QtWidgets.QMenu()
        if self.pipelineTemplates is not None:
            for item in self.pipelineTemplates:
                templatesSubItem = subMenu.addAction(item)
            openItem = menu.addAction('Open...', self._openSavedPipeline)
            templatesItem.setMenu(subMenu)
        openButton.setMenu(menu)

    def _addPipesSearchWidget(self, row):
        bText = 'Search Pipe. Return to add selected'

        self._searchWidget = LineEdit(self.inputFrame, backgroundText=bText, grid=(row, 1), )
        self._searchWidget.textChanged.connect(self._searchWidgetCallback)
        self._searchWidget.keyPressEvent = self._pipeSearchkeyPressEvent
        self._searchWidget.setMinimumWidth(300)

    def _searchNameInList(self, ll, searchText):
        import fnmatch

        found = set()
        if not searchText.endswith('*'):
            searchText = searchText + '*'
        if not searchText.startswith('*'):
            searchText = '*' + searchText
        for ln, nn in zip([x.lower() for x in ll], ll):
            if fnmatch.fnmatch(ln, searchText):
                found.add(nn)
            elif fnmatch.fnmatch(ln, searchText.lower()):
                found.add(nn)
        return list(found)

    def _searchWidgetCallback(self):
        self.pipeTreeWidget.clearSelection()
        self._resultWidget.clear()
        text = self._searchWidget.get()
        if text != '':

            pipeNames = self._searchNameInList(self.pipeTreeWidget._availablePipeNames, text)
            # items = (self.pipeTreeWidget.findItems(text, Qt.MatchContains | Qt.MatchRecursive))
            if pipeNames:
                self._resultWidget.show()
                self._resultWidget.addItems(pipeNames)
                # b = self._resultWidget.sizeHintForRow(0) * self._resultWidget.count() + 2 * self._resultWidget.frameWidth() #this make the search of dynamic sizes
                # self._resultWidget.setMaximumHeight(b)
                self._resultWidget.setMaximumHeight(
                        abs(self._resultWidget.sizeHintForRow(0)) * 4)  # fix height by num of rows
                self._searchWidget.setClearButtonEnabled(True)

            else:
                self._resultWidget.hide()
        else:
            self._resultWidget.hide()

    def _resultItemDoubleClickCallback(self):
        if len(self._resultWidget.getSelectedTexts()) == 1:
            self.addPipe(self._resultWidget.getSelectedTexts()[-1])

    def callbackResultWidget(self):
        selectedTreeItems = self.pipeTreeWidget.selectedItems()
        self.pipeTreeWidget.selectItems(self._resultWidget.getSelectedTexts())

    def _addPipelineDropArea(self):
        self.pipelineArea = PipelineDropArea(self, guiPipeline=self, mainWindow=self.mainWindow)
        # self.pipelineArea.dropEvent = self._pipelineDropEvent
        scroll = ScrollArea(self)
        scroll.setWidget(self.pipelineArea)
        scroll.setWidgetResizable(True)
        self.pipelineAreaLayout.addWidget(scroll)

    def _closeAllGuiPipes(self):
        guiPipes = self.pipelineArea.currentGuiPipes
        if guiPipes:
            for guiPipe in guiPipes:
                guiPipe._closePipe()

        self.pipelineArea.currentGuiPipes.clear()
        self.currentGuiPipesNames.clear()

    def _pipeSearchkeyPressEvent(self, keyEvent):
        """ Run the pipeline by pressing the enter key """
        if keyEvent.key() == Qt.Key_Enter or keyEvent.key() == Qt.Key_Return:
            if self._searchWidget.get():
                selectedList = self.pipeTreeWidget.selectedItems()
                names = [i.pipeName for i in selectedList]
                if len(names) > 0:
                    for name in names:
                        self.addPipe(name)
                    self._searchWidget.clear()
                    self.pipeTreeWidget.clearSelection()

        elif keyEvent.key() == Qt.Key_Escape or keyEvent.key() == Qt.Key_Delete:
            self._searchWidget.clear()
            self.pipeTreeWidget.clearSelection()

        elif keyEvent.key() == Qt.Key_Up:
            if len(self._resultWidget.getTexts()) > 0:
                self._resultWidget.selectItems(self._resultWidget.getTexts()[:1])
                self._resultWidget.setFocus()

        else:
            LineEdit.keyPressEvent(self._searchWidget, keyEvent)

    def _pipesResultskeyPressEvent(self, keyEvent):
        """ Run the pipeline by pressing the enter key """
        if keyEvent.key() == Qt.Key_Enter or keyEvent.key() == Qt.Key_Return:
            if self._searchWidget.get():
                names = self._resultWidget.getSelectedTexts()
                if len(names) > 0:
                    for name in names:
                        self.addPipe(name)
        elif keyEvent.key() == Qt.Key_Escape or keyEvent.key() == Qt.Key_Delete:
            self._resultWidget.clearSelection()

        else:
            ListWidget.keyPressEvent(self._resultWidget, keyEvent)

    def _getSerialName(self, guiPipeName):
        self.currentGuiPipesNames.append(guiPipeName)
        counter = collections.Counter(self.currentGuiPipesNames)
        return str(guiPipeName) + '-' + str(counter[str(guiPipeName)])
        # return str(guiPipeName)

    #-----------------------------------------------------------------------------------------
    # GUI CallBacks

    def _selectPipe(self, selected):

        guiPipeName = self._getSerialName(str(selected))
        self._addGuiPipe(guiPipeName, selected)

    def addPipe(self, pipeName):
        guiPipeName = self._getSerialName(str(pipeName))
        self._addGuiPipe(guiPipeName, pipeName)

    def getPipeFromName(self, pipeName):
        for pipe in self.pipes:
            if pipe.pipeName == pipeName:
                return pipe

    def _addGuiPipe(self, serialName, pipeName, position=None, relativeTo=None):
        for guiPipe in self.guiPipes:
            if guiPipe.pipeName == pipeName:
                if guiPipe._alreadyOpened:
                    getLogger().warning('GuiPipe already opened. Impossible to open this pipe more then once.')
                    return
                else:
                    if not position:
                        position = self.addBoxPosition.get()
                    newGuiPipe = guiPipe(parent=self, application=self.application, name=serialName,
                                         project=self.project)
                    newGuiPipe.setMaximumHeight(newGuiPipe.sizeHint().height())
                    self.pipelineArea.addDock(newGuiPipe, position=position, relativeTo=relativeTo)
                    autoActive = self.autoActiveCheckBox.get()
                    newGuiPipe.label.checkBox.setChecked(autoActive)
                    newGuiPipe._formatLabelWidgets()
                    return

    @property
    def openGuiPipes(self):
        if len(self.pipelineArea.findAll()[1]) > 0:
            return self.pipelineArea.orderedBoxes(self.pipelineArea.topContainer)
        return []

    def _getActivePipes(self):
        activePipes = []
        guiPipes = self.openGuiPipes
        if len(guiPipes) > 0:
            for cc, guiPipe in enumerate(guiPipes):
                if guiPipe.isActive:
                    activePipes.append(guiPipe)
        return activePipes

    def _runPipeline(self):

        initialTime = time.time()
        getLogger().info(f'Pipeline: Started on {datetime.now()}')
        self.queue = []
        if not self.inputData:
            getLogger().info('Pipeline: No input data.')
            showWarning('Pipeline', 'No input data')
            return
        guiPipes = self.openGuiPipes
        self._kwargs = {}
        if len(guiPipes) > 0:
            for cc, guiPipe in enumerate(guiPipes):
                pipe = guiPipe.pipe
                if guiPipe.isActive:
                    pipe.isActive = True
                    pipe._kwargs = guiPipe.widgetsState
                    self.queue.append(pipe)
                else:
                    pipe.isActive = False
        self.runPipeline()
        if self.updateInputData:
            self._updateGuiInputData()
        finalTime = time.time()
        getLogger().info(f'Pipeline: Completed in {int(finalTime - initialTime)}s')

    #-----------------------------------------------------------------------------------------
    # others

    def _getGuiPipeClassFromClassName(self, name):
        for guiPipe in self.guiPipes:
            if guiPipe.__name__ == name:
                return guiPipe

    def _getGuiPipeClass(self, name):
        for guiPipe in self.guiPipes:
            if guiPipe.pipeName == name:
                return guiPipe

    #-----------------------------------------------------------------------------------------
    # Saving Restoring  SETUP

    def _openJsonFile(self, path):
        if path is not None:
            with open(str(path), 'r') as jf:
                data = json.load(jf)
            return data

    def _getPathFromDialogBox(self):
        dialog = PipelineFileDialog(parent=self, acceptMode='open')
        dialog._show()
        return dialog.selectedFile()

    def _getGuiPipesFromFile(self, params, guiPipesNames):
        pipelineBoxes = []
        for i in params:
            for key, value in i.items():
                if value[0].upper() in guiPipesNames:
                    guiPipe = self._getGuiPipeClassFromClassName(key)
                    pipelineBox = guiPipe(parent=self, application=self.application, name=value[0], params=value[1])
                    pipelineBox.setActive(value[2])
                    pipelineBoxes.append(pipelineBox)
        return pipelineBoxes

    def _getSettingsDict(self):

        dd = od([
            ('name', [self.pipelineReNameTextEdit, self.pipelineReNameTextEdit.get, self.pipelineReNameTextEdit.set]),
            ('inputData', [self.inputDataList, self.inputDataList.getTexts, self.inputDataList.setTexts]),
            ('autoActive', [self.autoActiveCheckBox, self.autoActiveCheckBox.get, self.autoActiveCheckBox.set]),
            ('addPosit', [self.addBoxPosition, self.addBoxPosition.get, self.addBoxPosition.set])
            ])
        return dd

    def _setSavedWidgetParameters(self, values: dict = {}):
        """
        sets the extra widget which are saved in a pipeline file:
        name
        inputData
        savePath
        autoActive
        addPosit
        """
        for key, value in values.items():
            widgetList = self._getSettingsDict().get(key)
            if widgetList is not None:
                widget, getValue, setValue = widgetList
                setValue(value)

    def _getSavingWidgetParameters(self):
        """
        get the extra widget values to save in a pipeline file:
        name
        inputData
        savePath
        autoActive
        addPosit
        """
        dd = od([(x, None) for x in self._getSettingsDict()])
        for key, widgetList in self._getSettingsDict().items():
            widget, getValue, setValue = widgetList
            dd[key] = getValue()
        return dd

    def _openSavedPipeline(self, path=None):
        if not path:
            path = self._getPathFromDialogBox()
        state, guiPipesState, others = self._openJsonFile(path)
        self._closeAllGuiPipes()
        self._setSavedWidgetParameters(od(others))

        for item in guiPipesState:
            guiPipeClassName, guiPipeName, widgetsState, isActive = item
            guiPipeClass = self._getGuiPipeClassFromClassName(guiPipeClassName)
            if guiPipeClass:
                guiPipe = guiPipeClass(parent=self, application=self.application, name=guiPipeName)
                guiPipe.restoreWidgetsState(**widgetsState)
                guiPipe.setActive(isActive)

                self.pipelineArea.addBox(guiPipe)
        self.pipelineArea._restoreState(state)
        self.setDataSelection()

    def _getPipelineData(self):
        """jsonData = [{pipelineArea.state}, [guiPipesState]]   """
        guiPipesState = self.pipelineArea.guiPipesState
        # if len(guiPipesState)>0:
        jsonData = []
        jsonData.append(self.pipelineArea.saveState())
        jsonData.append(guiPipesState)
        jsonData.append(list(self._getSavingWidgetParameters().items()))
        return jsonData

    def _savePipeline(self):
        pipelineName = str(self.pipelineReNameTextEdit.get())

        self.saveDialog = TablesFileDialog(parent=None, acceptMode='save', selectFile=pipelineName,
                                           fileFilter=".json ")
        self.saveDialog._show()
        path = self.saveDialog.selectedFile()
        self.pipeline2Json(path)

    def pipeline2Json(self, path):
        """
        save the pipeline state to json file.
        path: absolute path for a json file
        """
        if path:
            path = aPath(path)
            pipelineFilePath = path.assureSuffix('.json')
            jsonData = self._getPipelineData()
            with open(pipelineFilePath, 'w') as fp:
                json.dump(jsonData, fp, indent=2)
                fp.close()
                getLogger().info('Pipeline File saved in: ' + str(pipelineFilePath))

    #-----------------------------------------------------------------------------------------
    # GUI PIPELINE SETTINGS

    def _pipelineBoxesWidgetParams(self, currentGuiPipesName):
        self.savePipelineParams = []
        for guiPipeName in currentGuiPipesName:
            guiPipe = self.pipelineArea.docks[str(guiPipeName)]
            guiPipeClassName = guiPipe.__class__.__name__
            state = guiPipe.isActive
            params = guiPipe.widgetsState
            newDict = {guiPipeClassName: (guiPipeName, params, state)}
            self.savePipelineParams.append(newDict)
        return self.savePipelineParams

    # def _getInputDataHeaderLabel(self):
    #     # color = QtGui.QColor('green')
    #     header = QtWidgets.QListWidgetItem(DropHereLabel)
    #     header.setFlags(QtCore.Qt.NoItemFlags)
    #     # header.setBackground(color)
    #     return header

    def _inputDataContextMenu(self):
        contextMenu = Menu('', self, isFloatWidget=True)
        contextMenu.addItem('Add Spectra/SpectrumGroups', callback=self._addSpectraPopup)
        contextMenu.addItem('Remove Selected', callback=self._removeSelectedInputData)
        contextMenu.addSeparator()
        contextMenu.addItem('Clear All', callback=self._clearInputData)
        return contextMenu

    def _createSettingsWidgets(self):

        row = 0
        self.addBoxLabel = Label(self.settingsWidget, 'Add Pipes', grid=(row, 0))
        self.addBoxPosition = RadioButtons(self.settingsWidget, texts=['top', 'bottom'],
                                           callback=self._addPipeDirectionCallback, selectedInd=1, direction='v',
                                           grid=(row, 1))
        self.addBoxPosition.setMaximumHeight(20)
        row += 1
        self.autoActiveLabel = Label(self.settingsWidget, 'Auto active', grid=(row, 0))
        self.autoActiveCheckBox = CheckBox(self.settingsWidget, callback=self._autoActiveCallback, grid=(row, 1))
        self.autoActiveCheckBox.setChecked(True)
        self.settingsWidget.getLayout().setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

    def _itemsDropped(self):
        self.setDataSelection()

    def _popupInputCallback(self, w):
        selected = w.getSelections()
        pids = [x.pid for x in selected]
        self.inputDataList.setTexts(pids)
        self.setDataSelection()
        w.parent().reject()

    def _removeSelectedInputData(self):
        self.inputDataList.removeItem()
        self.setDataSelection()

    def _clearInputData(self):
        self.inputDataList.clear()
        # self.inputDataList.addItem(self._getInputDataHeaderLabel())
        self.setDataSelection()

    def _addSpectraPopup(self):
        popup = CcpnDialog(parent=self.mainWindow, setLayout=True)
        spectraSelectionWidget = SpectraSelectionWidget(popup, mainWindow=self.mainWindow, grid=(0, 0))
        okCancel = ButtonList(popup, texts=['Cancel', 'Ok'],
                              callbacks=[popup.reject, partial(self._popupInputCallback, spectraSelectionWidget)],
                              grid=(1, 0))
        popup.exec_()

    def _updateInputDataWidgets(self):
        'update the gui pipe widget if the input data has changed'
        if len(self.pipelineArea.findAll()[1]) > 0:
            guiPipes = self.openGuiPipes
            for guiPipe in guiPipes:
                guiPipe._updateWidgets()

    def _renamePipelineCallback(self, ):
        self.pipelineName = self.pipelineReNameTextEdit.get()

    def _addPipeDirectionCallback(self):
        value = self.addBoxPosition.getSelectedText()

    def _autoActiveCallback(self):
        value = self.autoActiveCheckBox.get()

    def _setThreadStyle(self, active=True):

        for guiPipe in self.openGuiPipes:
            if active:
                guiPipe._setStandbyStyle()
            else:
                guiPipe._setNonThreadStyle()

    def _displayStopButton(self):
        if self.autoCheckBox.isChecked():
            self.threadButtons.buttons[0].show()
            self.threadButtons.buttons[1].show()
            self.threadButtons.buttons[2].hide()
        else:
            self.threadButtons.buttons[0].hide()
            self.threadButtons.buttons[1].hide()
            self.threadButtons.buttons[2].show()

    def _addWidgetsToLayout(self, widgets, layout):
        count = int(len(widgets) / 2)
        self.positions = [[i + 1, j] for i in range(count) for j in range(2)]
        for position, widget in zip(self.positions, widgets):
            i, j = position
            layout.addWidget(widget, i, j)

    def setDataSelection(self):

        dataTexts = self.inputDataList.getTexts()
        self.inputData.clear()
        self.spectrumGroups.clear()
        self.inputData = set(self.inputData)
        if self.project is not None:
            if len(dataTexts) == 0:
                # self.threadButtons.setEnabled(False)
                # self.inputDataList.addItem(self._getInputDataHeaderLabel())
                return
            for text in dataTexts:
                obj = self.project.getByPid(text)
                if object is not None:
                    if isinstance(obj, Spectrum):
                        self.inputData.update([obj])
                    elif isinstance(obj, SpectrumGroup):
                        self.inputData.update(obj.spectra)
                        self.spectrumGroups.update([obj])
                    # else:
                    #     getLogger().warning('Check input data. Data not available.')
        self._updateInputDataWidgets()

    def _updateInputDataFromNotifier(self, data):
        ''
        dataTexts = self.inputDataList.getTexts()
        sp = data['object']
        item = sp.pid
        self.inputDataList.clearSelection()
        self.inputDataList.select(item)
        self.inputDataList.removeItem()
        self.setDataSelection()

    def _updateGuiInputData(self):
        'updates the InputData list widget if more data are added in the pipeline inputData'
        spectGroupPids = []
        spectraPids = []
        for item in self.inputDataList.getTexts():
            if item.startswith('SG'):
                spectGroupPids.append(item)
            if item.startswith('SP'):
                spectraPids.append(item)

        self.inputDataList.clear()
        if len(self.spectrumGroups) >= len(spectGroupPids):
            for sg in self.spectrumGroups:
                if sg is not None:
                    self.inputDataList.addItem(sg.pid)
        inputspectGroupSpectra = [sp for sg in self.spectrumGroups for sp in sg.spectra]
        inputDataSpectra = [sp for sp in self.inputData if sp not in inputspectGroupSpectra]
        for sp in inputDataSpectra:
            if sp is not None:
                self.inputDataList.addItem(sp.pid)

        self.setDataSelection()


#=========================================================================================
# RUN GUI TESTING
#=========================================================================================

def main():
    from ccpn.ui.gui.widgets.Application import TestApplication
    from ccpn.ui.gui.widgets.CcpnModuleArea import CcpnModuleArea

    # analysis specific
    from ccpn.pipes import loadedPipes

    app = TestApplication()
    win = QtWidgets.QMainWindow()

    moduleArea = CcpnModuleArea(mainWindow=None, )
    pipeline = GuiPipeline(mainWindow=None, pipes=loadedPipes)
    # pipeline = GuiPipeline(mainWindow=None, pipes=pipeExamples)
    pipeline._loadUserPipes()
    moduleArea.addModule(pipeline)
    # pipeline._openAllPipes()

    win.setCentralWidget(moduleArea)
    win.resize(1000, 500)
    win.setWindowTitle('Testing %s' % pipeline.moduleName)
    win.show()

    app.start()


if __name__ == '__main__':
    main()
