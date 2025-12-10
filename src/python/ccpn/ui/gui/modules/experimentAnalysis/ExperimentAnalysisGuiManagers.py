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
__dateModified__ = "$dateModified: 2024-12-12 13:56:43 +0000 (Thu, December 12, 2024) $"
__version__ = "$Revision: 3.2.11 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Luca Mureddu $"
__date__ = "$Date: 2022-05-20 12:59:02 +0100 (Fri, May 20, 2022) $"
#=========================================================================================
# Start of code
#=========================================================================================

from collections import defaultdict
from PyQt5 import QtCore, QtWidgets
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiPanel import PanelPositions, TopFrame, BottomFrame,\
    LeftFrame, RightFrame
import ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiNamespaces as guiNameSpaces
from ccpn.ui.gui.modules.experimentAnalysis.ExperimentSelectors import _registerExperimentSelectors, ExperimentSelectorHandler
from ccpn.ui.gui.widgets.Tabs import Tabs
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Splitter import Splitter


class ExperimentAnalysisHandlerABC(object):
    """
    This object manages a dedicated part of a ExperimentAnalysis GuiModule instance e.g:
        - Backend   (ExperimentAnalysis base class)
        - Notifiers (core and current)
        - Settings  (Tab containing setting widgets)
        - Panels    (Frame containing tables, plotting etc)
        - Files     (I/O)

    Handlers are created internally when you create a ExperimentAnalysis GuiModule.
    You interact with them later, e.g. when you want to start the backend
    process or when you want to install/retrieve a panel.

    example:
        experimentAnalysis = ExperimentAnalysis()
        # use the backendHandler to interact to the backend built-in methods
        experimentAnalysis.backend.start(...)
        experimentAnalysis.backend.fitInputData(...)
        # use the panelsHandler to install a panel
        experimentAnalysis.panels.install(MyPanel(name))
        panel = experimentAnalysis.panels.get(name)
        # etc
    """

    @property
    def guiModule(self):
        """
        Return a reference to the parent code edit widget.
        """
        return self._guiModule

    def __init__(self, guiModule, autoStart=True):
        """
        :param guiModule: The GuiModule instance to control
        :param autoStart: bool. True to start the handler processes.
        """
        self._guiModule = guiModule
        if autoStart:
            self.start()

    def start(self):
        pass

    def close(self):
        pass

    def updateAll(self):
        pass

####################################################################################
#########################      The Various Handlers        #########################
####################################################################################

TOOLBARFRAME = 'toolbarFrame' # reserved
MAINFRAME = 'mainFrame' # reserved


class PanelHandler(ExperimentAnalysisHandlerABC):
    """
    Manages the list of Gui Panels and adds them to the GuiModule.
    """
    gridPositions = {
        TopFrame :   ((0, 0), (1, 2)), #grid and gridSpan
        LeftFrame:   ((1, 0), (1, 1)),
        RightFrame:  ((1, 1), (1, 1)),
        BottomFrame: ((2, 0), (2, 2)),
    }

    def __init__(self, guiModule):
        super(PanelHandler, self).__init__(guiModule)
        self._marginSizes = (0, 0, 0, 0)
        self.panels = defaultdict()
        self._panelsByFrame = {k:[] for k in PanelPositions}
        self._toolBarPanel = None

    def start(self):
        """ Set up the 2 main Frames:
        1) toolbar. reserved for Buttons etc
        2) main panels: Top, Bottom, Left, Right. Used for anything"""

        setattr(self, TOOLBARFRAME, Frame(self.guiModule.mainWidget, setLayout=True, grid=(0, 0)))
        setattr(self, MAINFRAME, Frame(self.guiModule.mainWidget, setLayout=True, grid=(1,0)))

        for frameName, gridDefs in self.gridPositions.items():
            grid, gridSpan = gridDefs
            setattr(self, frameName, Frame(self.getFrame(MAINFRAME), setLayout=True, grid=grid, gridSpan=gridSpan))
        self._setupSplitters()
        self.guiModule.mainWidget.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self._setupFrameGeometries()

    def addPanel(self, panel, **kwargs):
        """
        Installs a panel in the proper frame of the MainWidget .
        :param panel: Panel to install
        :return: The installed panel
        """
        panel.onInstall()
        self._addToLayout(panel, **kwargs)
        return panel

    def getPanel(self, name):
        """Get an installed Panel by its name"""
        panel = self.panels.get(name)
        return panel

    def getFrame(self, name):
        frame = getattr(self, name)
        return frame

    def getToolBarPanel(self):
        return self._toolBarPanel

    def addToolBar(self, toolBarPanel):
        """ Install the toolBarPanel in the reserved frame inside the main layout"""
        frame = self.getFrame(TOOLBARFRAME)
        toolBarPanel.onInstall()
        frame.getLayout().addWidget(toolBarPanel)
        self._toolBarPanel = toolBarPanel
        return toolBarPanel

    def clear(self):
        """
        Removes all panel from the Module.
        """
        pass

    def close(self):
        for name, panel in self.panels.items():
            panel.close()

    ######## Private methods ######

    def _addToLayout(self, panel, **kwargs):
        frameAttr = panel._panelPositionData.description
        frame = getattr(self, frameAttr, None)
        if frame is not None:
            frame.getLayout().addWidget(panel, **kwargs)
            self._panelsByFrame[frameAttr].append(panel)
            self.panels.update({panel.panelName:panel})

    def _setupSplitters(self):
        """
        Create splitters and add frames to them. There are two splitters:
         - one "vertical" as it divides vertically the Top/Bottom frames,
         - one "horizontal" between the Left/Right frames .
        The Vertical is the primary splitter that contains the horizontal.
        The Vertical splitter is added to the mainWidget layout.
        (Line-ordering is crucial for the correct layout)
        """
        self._horizontalSplitter = Splitter()
        self._verticalSplitter = Splitter(horizontal=False)
        ## add frames to splitters
        self._horizontalSplitter.addWidget(self.getFrame(LeftFrame))
        self._horizontalSplitter.addWidget(self.getFrame(RightFrame))
        self._verticalSplitter.addWidget(self._horizontalSplitter) # Important: add horizontalSplitter to the Vertical!
        self._verticalSplitter.addWidget(self.getFrame(BottomFrame))
        ## add all to main Layout
        self.guiModule.mainWidget.getLayout().addWidget(self._verticalSplitter)

    def _setupFrameGeometries(self):
        """Setup layout policy etc """
        panelFrame = self.getFrame(MAINFRAME)
        for ff in PanelPositions:
            frame = self.getFrame(ff)
            frame.getLayout().setAlignment(QtCore.Qt.AlignTop)
            frame.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)

    def __iter__(self):
        lst = []
        for name, panel in self.panels.items():
            lst.append(panel)
        return iter(lst)

    def __len__(self):
        lst = []
        for name, panel in self.panels.items():
            lst.append(panel)
        return len(lst)


class SettingsPanelHandler(ExperimentAnalysisHandlerABC):
    """
    Manages the list of Tab settings and adds them to the GuiModule settingsWidget.
    """
    def __init__(self, guiModule):
        super(SettingsPanelHandler, self).__init__(guiModule)
        self._marginSizes = (5, 5, 5, 5)
        self._panels = {}
        self.tabs = defaultdict()
        _registerExperimentSelectors()
        self.experimentSelectorHandler = ExperimentSelectorHandler(guiModule)
        self.settingsWidget = self.guiModule.settingsWidget
        self.settingsWidget.setContentsMargins(*self._marginSizes)
        self.settingsTabWidget = Tabs(self.settingsWidget, setLayout=True, grid=(0, 0))

    def append(self, panel):
        # add tab to gui
        from ccpn.ui.gui.modules.experimentAnalysis.ExperimentAnalysisGuiSettingsPanel import GuiSettingPanel
        if not isinstance(panel, GuiSettingPanel):
            raise RuntimeError(f'{panel} is not of instance: {GuiSettingPanel}')
        self.settingsTabWidget.insertTab(panel.tabPosition, panel, panel.tabName)
        self._panels.update({panel.tabPosition:panel})
        self.tabs.update({panel.tabName: panel})

    def getTab(self, name):
        return self.tabs.get(name, None)

    def getAllSettings(self, grouped=True) -> dict:
        """
        Get all settings set in the Settings panel in a dict of dict dived by Tab.
        :param grouped: Bool. True to get a dict of dict. False to get a flat dict with all settings in it.
        :return:  dict of dict as default, dict if grouped = False.
        """
        settings = {}
        for tabName, tab in self.tabs.items():
            tabSettings = tab.getSettingsAsDict()
            if grouped:
                settings[tabName] = tabSettings
            else:
                settings.update(tabSettings)
        return settings

    def getInputDataSettings(self) -> dict:
        return self.getAllSettings().get(guiNameSpaces.Label_SetupTab, {})

    def _getSelectedSpectrumGroup(self):
        """ Get the SpectrumGroup Obj from the Widgets. """
        inputSettings = self.getInputDataSettings()
        sgPids = inputSettings.get(guiNameSpaces.WidgetVarName_SpectrumGroupsSelection, [None])
        if not sgPids:
            return
        spGroup = self.guiModule.project.getByPid(sgPids[-1])
        return spGroup

    def close(self):
        for tabName, tab in self.tabs.items():
            tab.close()


class IOHandler(ExperimentAnalysisHandlerABC):
    """
    Manages the I/O machinery of the GuiModule.
    """
    pass


class PluginsHandler(ExperimentAnalysisHandlerABC):
    """
    Manages plugins for  the GuiModule. NIY
    """
    pass
