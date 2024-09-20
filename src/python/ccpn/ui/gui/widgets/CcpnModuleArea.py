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
__dateModified__ = "$dateModified: 2024-06-26 11:56:03 +0100 (Wed, June 26, 2024) $"
__version__ = "$Revision: 3.2.4 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import contextlib

from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import pyqtSlot
from pyqtgraph.dockarea.Dock import Dock
from pyqtgraph.dockarea.DockArea import DockArea, DockDrop
from pyqtgraph.dockarea.Container import Container

from ccpn.core.Project import Project
from ccpn.core.Spectrum import Spectrum

from ccpn.ui.gui.lib.GuiSpectrumDisplay import GuiSpectrumDisplay
from ccpn.ui.gui.modules.CcpnModule import CcpnModule, MODULENAME, WIDGETSTATE
from ccpn.ui.gui.widgets.DropBase import DropBase
from ccpn.ui.gui.widgets.Label import Label
from ccpn.ui.gui.widgets.SideBar import SideBar, SideBarSearchListView
from ccpn.ui.gui.lib.MenuActions import _openItemObject
from ccpn.ui.gui.widgets.Font import Font, getFontHeight, getFont
from ccpn.ui.gui.widgets.MainWindow import MainWindow
# from ccpn.ui.gui.lib.GuiWindow import GuiWindow
from ccpn.ui.gui.lib.Shortcuts import Shortcuts
from ccpn.ui.gui.guiSettings import getColours, LABEL_FOREGROUND
from ccpn.ui.gui.lib.mouseEvents import SELECT, PICK, MouseModes, setCurrentMouseMode
from ccpn.ui.gui.widgets.ToolBar import ToolBar
from ccpn.ui.gui.widgets.PlaneToolbar import _StripLabel
from ccpn.ui.gui.widgets.GuiTable import GuiTable
from ccpn.ui.gui.widgets.table.TableABC import TableABC
from ccpn.ui.gui.widgets.Icon import Icon

from ccpn.framework.Application import getApplication, getMainWindow
from ccpn.util.Colour import hexToRgb
from ccpn.util.Common import incrementName
from ccpn.util.Path import aPath
from ccpn.util.Logging import getLogger


ModuleArea = DockArea
Module = Dock
DropAreaLabel = 'Drop Area'
Failed = 'Failed'
MODULEAREA_IGNORELIST = (ToolBar, _StripLabel, GuiTable, TableABC)


class TempAreaWindow(Shortcuts, MainWindow):
    def __init__(self, area, mainWindow=None, **kwargs):
        MainWindow.__init__(self, **kwargs)
        self.setCentralWidget(area)
        self.tempModuleArea = area
        self.mainModuleArea = self.tempModuleArea.home

        self.mainWindow = mainWindow
        self.application = mainWindow.application
        self.project = mainWindow.application.project
        self.current = mainWindow.application.current

        self._setShortcuts(mainWindow=mainWindow)
        self._setMouseMode(SELECT)

        # install handler to resize when moving between displays
        self.window().windowHandle().screenChanged.connect(self._screenChangedEvent)

        _height = max(5, (getFontHeight(size='SMALL') or 15) // 3)
        _vName = Icon('icons/vertical-split')
        _hName = Icon('icons/horizontal-split')
        path1 = aPath(_vName._filePath).as_posix()
        path2 = aPath(_hName._filePath).as_posix()

        self.setStyleSheet("""QSplitter {background-color: transparent; }
                            QSplitter::handle:vertical {background-color: transparent; height: %dpx; image: url(%s); }
                            QSplitter::handle:horizontal {background-color: transparent; width: %dpx; image: url(%s); }
                            """ % (_height, path1, _height, path2))

    def _setMouseMode(self, mode):
        if mode in MouseModes:
            # self.mouseMode = mode
            setCurrentMouseMode(mode)
            for sd in self.project.spectrumDisplays:
                for strp in sd.strips:
                    strp.mouseModeAction.setChecked(mode == PICK)
            mouseModeText = ' Mouse Mode: '
            self.mainWindow.statusBar().showMessage(mouseModeText + mode)

    @pyqtSlot()
    def _screenChangedEvent(self, *args):
        self._screenChanged(*args)
        self.update()

    def _screenChanged(self, *args):
        getLogger().debug2('tempAreaWindow screenchanged')
        project = self.application.project

        for spectrumDisplay in project.spectrumDisplays:
            if spectrumDisplay.isDeleted:
                continue

            for strip in spectrumDisplay.strips:
                if not strip.isDeleted:
                    strip.refreshDevicePixelRatio()

            # NOTE:ED - set pixel-ratio for extra axes
            if hasattr(spectrumDisplay, '_rightGLAxis'):
                spectrumDisplay._rightGLAxis.refreshDevicePixelRatio()
            if hasattr(spectrumDisplay, '_bottomGLAxis'):
                spectrumDisplay._bottomGLAxis.refreshDevicePixelRatio()

    def closeEvent(self, *args, **kwargs):
        from ccpn.ui.gui.modules.PythonConsoleModule import PythonConsoleModule

        for module in self.tempModuleArea.ccpnModules:
            if isinstance(module, PythonConsoleModule):
                # move the PythonConsole back to the main ModuleArea or get a C++ error
                # strange case - IPython in popped-out window, close IPython module,
                #   new project, window remains behind with bad link to original mainWindow?
                #   need to dynamically grab the current mainWindow
                _mainWindow = getMainWindow()
                mainArea = _mainWindow.moduleArea
                mainArea.addModule(module)
                module.hide()
            else:
                module._closeModule()
        if self.tempModuleArea in self.mainModuleArea.tempAreas:
            self.mainModuleArea.tempAreas.remove(self.tempModuleArea)

        # minimise event required here to notify Qt to exit from fullscreen mode
        self.showNormal()
        self.close()


class CcpnModuleArea(ModuleArea, DropBase):

    def __init__(self, mainWindow, **kwargs):

        super().__init__(mainWindow, **kwargs)
        DropBase._init(self, acceptDrops=True)

        self.mainWindow = mainWindow  # a link back to the parent MainWindow
        self.application = getApplication()  # this will enable to create testing ModuleArea/Modules without mainWindow/project/application
        self.preferences = None
        if self.application:
            self.preferences = self.application.preferences

        self.moveModule = self.moveDock
        self.setContentsMargins(0, 0, 0, 0)
        self.currentModuleNames = []
        self._modulesNames = {}
        self._ccpnModules = []
        self._modules = {}  # don't use self.docks, is not updated when removing docks
        self._openedSpectrumDisplays = []  # keep track of the order of opened spectrumDisplays
        self._seenModuleStates = {}  # {className: {moduleName:'', state:widgetsState}}
        # self.setAcceptDrops(True) GWV not needed; handled by DropBase init

        self.textLabel = DropAreaLabel
        self.fontLabel = getFont(size='MAXIMUM')
        # if self.mainWindow:
        #     self.fontLabel = self.mainWindow.application._fontSettings.helveticaBold36
        # else: #can be None. for example for testing when developing new GUI modules. Cannot crash just for a font label!
        #     self.fontLabel = Font('Helvetica', 36, bold=False)

        colours = getColours()
        self.colourLabel = (121, 142, 200) #hexToRgb(colours[LABEL_FOREGROUND])

        self._dropArea = None  # Needed to know where to add a newmodule when dropping a pid from sideBar
        if self._container is None:
            for i in self.children():
                if isinstance(i, Container):
                    self._container = i

    # def moveDock(self, module, position, neighbor, initTime=False):
    #     """
    #     Move an existing Dock to a new location.
    #     """
    #
    #     if not initTime:
    #         previousArea =  module.getDockArea()
    #         if previousArea != self:
    #             if module.maximised:
    #                 module.toggleMaximised()
    #
    #     super().moveDock(module,position,neighbor)

    def dropEvent(self, event, *args):
        data = self.parseEvent(event)
        source = event.source()

        # drop an item from the sidebar onto the drop area
        if DropBase.PIDS in data and isinstance(data['event'].source(), (SideBar, SideBarSearchListView)):
            # process Pids
            self.mainWindow._processPids(data, position=self.dropArea)

        elif DropBase.URLS in data:
            objs = self.mainWindow._processDroppedItems(data)
            # discard opening any further items if project loaded (may be inconsistent with mainWindow)
            if list(filter(lambda obj: isinstance(obj, Project), objs)):
                return
            # dropped spectra will automatically open from here
            spectra = list(filter(lambda obj: isinstance(obj, Spectrum), objs))
            _openItemObject(self.mainWindow, spectra, position=self.dropArea)

        if hasattr(source, 'implements') and source.implements('dock'):
            DockArea.dropEvent(self, event, *args)

        # reset the dock area
        self.dropArea = None
        self.overlay.setDropArea(self.dropArea)

        event.accept()

    @staticmethod
    def _maximisedAttrib(widget):
        try:
            getattr(widget, 'maximised')
            return True
        except Exception:
            return False

    def findMaximisedDock(self, event):
        result = None
        targetWidgets = [widget for widget in self.findChildren(QtWidgets.QWidget) if self._maximisedAttrib(widget)]
        maximisedWidgets = [widget for widget in targetWidgets if widget.maximised == True]
        if len(maximisedWidgets) > 0:
            result = maximisedWidgets[0]
        return result

    def dragEnterEvent(self, *args):
        event = args[0]
        maximisedModule = self.findMaximisedDock(event)
        if maximisedModule is not None:
            source = event.source()
            sourceParentModule = None
            with contextlib.suppress(Exception):
                sourceParentModule = source._findModule()

            if sourceParentModule is not maximisedModule:
                maximisedModule.handleDragToMaximisedModule(event)

            return

        event = args[0]
        data = self.parseEvent(event)

        if DropBase.PIDS in data and isinstance(data['event'].source(), (SideBar, SideBarSearchListView)):
            DockArea.dragEnterEvent(self, *args)
            event.accept()
        elif isinstance(data['source'], MODULEAREA_IGNORELIST):
            event.ignore()
        else:
            DockDrop.dragEnterEvent(self, *args)
            event.accept()

    def dragLeaveEvent(self, *args):
        event = args[0]

        maximisedWidget = self.findMaximisedDock(event)
        if maximisedWidget is not None:
            maximisedWidget.finishDragToMaximisedModule(event)

        DockArea.dragLeaveEvent(self, *args)
        event.accept()

    def dragMoveEvent(self, *args):
        event = args[0]
        maximisedWidget = self.findMaximisedDock(event)
        if maximisedWidget is not None:
            maximisedWidget.handleDragToMaximisedModule(event)
            return

        event = args[0]
        DockArea.dragMoveEvent(self, *args)
        event.accept()

    def _paint(self, ev):
        p = QtGui.QPainter(self)
        # set font
        p.setFont(self.fontLabel)
        # set colour
        p.setPen(QtGui.QColor(*self.colourLabel))

        # set size
        rgn = self.contentsRect()
        rgn = QtCore.QRect(rgn.left(), rgn.top(), rgn.width(), rgn.height())
        align = QtCore.Qt.AlignVCenter | QtCore.Qt.AlignHCenter
        self.hint = p.drawText(rgn, align, DropAreaLabel)
        p.end()

    def paintEvent(self, ev):
        """
        Draws central label
        """
        if not self.ccpnModules:
            self._paint(ev)

        elif len(self.ccpnModules) == len(self._tempModules()):
            # means all modules are pop-out, so paint the label in the main module area
            self._paint(ev)

        elif all(m.isHidden() for m in self.ccpnModules):
            # means all modules are hidden
            self._paint(ev)

    def _isNameAvailable(self, name):
        """
        Check if the name is not already taken
        """
        return name not in self.modules.keys()

    def _incrementModuleName(self, name, splitter):
        """ fetch an incremented name if not already taken. """
        names = list(self.modules.keys())
        while name in names:
            name = incrementName(name, splitter)
        return name

    @property
    def ccpnModules(self) -> list:
        """return all current modules in area"""
        return self._ccpnModules

    @ccpnModules.getter
    def ccpnModules(self):
        if self is not None:
            ccpnModules = list(self.findAll()[1].values())
            return ccpnModules

    @property
    def modules(self) -> dict:
        """return all current modules in area as a dictionary. Don't use self.docks"""
        return self._modules

    @ccpnModules.getter
    def modules(self):
        if self is not None:
            modules = self.findAll()[1]
            return modules
        return {}

    @property
    def spectrumDisplays(self):
        """
        Return the list of opened spectrumDisplays in the order of their opening.
        Contrary to mainWindow.spectrumDisplays that return in alphabetical order.
        """
        return [x for x in self._openedSpectrumDisplays if not x.isDeleted]

    def repopulateModules(self):
        """
        Repopulate all modules to globally refresh all pulldowns, etc.
        """
        modules = self.ccpnModules
        for module in modules:
            if hasattr(module, '_repopulateModule'):
                module._repopulateModule()

    def _tempModules(self):
        """:return list of modules in temp Areas """
        return [a.ccpnModules for a in self.tempAreas]

    def addModule(self, module, position=None, relativeTo=None, **kwds):
        """With these settings the user can close all the modules from the label 'close module' or pop up and
         when re-add a new module it makes sure there is a container available.
        """
        if module is None:
            raise RuntimeError('No module given')

        wasMaximised = False

        # seems to add too many containers if relativeTo is None
        if not relativeTo:
            relativeTo = self

        for oldModule in self.modules.values():
            if oldModule.maximised:
                oldModule.toggleMaximised()
                wasMaximised = True

        if not module._restored:
            if not isinstance(module, GuiSpectrumDisplay):  #

                if not module._onlySingleInstance:
                    nextAvailableName = self._incrementModuleName(module.titleName, module._nameSplitter)
                    module.renameModule(nextAvailableName)
                    ## reset  widgets  as last time the module was opened
                    self._restoreAsTheLastSeenModule(module)


            else:
                self._openedSpectrumDisplays.append(module)

        # test that only one instance of the module is opened
        if hasattr(type(module), '_alreadyOpened'):
            _alreadyOpened = getattr(type(module), '_alreadyOpened')

            if _alreadyOpened is True:
                if hasattr(type(module), '_onlySingleInstance'):
                    getLogger().warning('Only one instance of %s allowed' % str(module.name))
                    return
            setattr(type(module), '_alreadyOpened', True)
            setattr(type(module), '_currentModule', module)  # remember the module

        if position is None:
            position = 'top'

        # store original area that the dock will return to when un-floated (not strictly necessary here)
        if not self.temporary:
            module.orig_area = self

        ## Determine the container to insert this module into.
        ## If there is no neighbor, then the container is the top.
        if relativeTo is None or relativeTo is self:
            if self.topContainer is None:
                container = self
                neighbor = None
            else:
                container = self.topContainer
                neighbor = None
        else:
            if isinstance(relativeTo, str):
                relativeTo = self.docks[relativeTo]
            container = self.getContainer(relativeTo)
            if container is None:
                raise TypeError(f"Dock {relativeTo} is not contained in a DockArea; "
                                f"cannot add another dock relative to it.")
            neighbor = relativeTo

        ## what container type do we need?
        neededContainer = {
            'bottom': 'vertical',
            'top'   : 'vertical',
            'left'  : 'horizontal',
            'right' : 'horizontal',
            'above' : 'tab',
            'below' : 'tab'
            }[position]

        if neededContainer != container.type() and container.type() == 'tab':
            neighbor = container
            container = container.container()

        ## Decide if the container we have is suitable.
        ## If not, insert a new container inside.
        if neededContainer != container.type():
            if neighbor is None:
                container = self.addContainer(neededContainer, self.topContainer)
            else:
                container = self.addContainer(neededContainer, neighbor)

        ## Insert the new dock before/after its neighbor
        insertPos = {
            'bottom': 'after',
            'top'   : 'before',
            'left'  : 'before',
            'right' : 'after',
            'above' : 'before',
            'below' : 'after'
            }[position]

        module.area = self
        old = module.container()
        container.insert(module, insertPos, neighbor)
        if old is not None:
            old.apoptose()

        self.docks[module.moduleName] = module

        #module.label.sigDragEntered.connect(self._dragEntered)
        if wasMaximised:
            module.toggleMaximised()
        return module

    def _getHelpModule(self, parentModuleName):
        """
        Get the HelpModule for a particular module if already present
        :return:
        """
        from ccpn.ui.gui.modules.HelpModule import HelpModule

        helpModule = None
        for modName, module in self.modules.items():
            if isinstance(module, HelpModule):
                if module.parentModuleName == parentModuleName:
                    helpModule = module
        return helpModule

    def _restoreAsTheLastSeenModule(self, module):
        """
        internal.
        Called when adding a new module to the mainArea, but not on restoring from a disk state.
        """
        if self.preferences:
            if self.preferences.appearance.rememberLastClosedModuleState:
                seenModule = self._seenModuleStates.get(module.className)
                if seenModule:
                    name = seenModule.get(MODULENAME, module.titleName)
                    state = seenModule.get(WIDGETSTATE, {})
                    nextAvailableName = self._incrementModuleName(name, module._nameSplitter)
                    module.renameModule(nextAvailableName)
                    module.restoreWidgetsState(**state)

    def _getModulesOnActiveNameEditing(self):
        modules = []
        for module in self.ccpnModules:
            if hasattr(module.label, 'nameEditor'):
                if module.label.nameEditor.isVisible():
                    modules.append(module)
        return modules

    def _updateSpectrumDisplays(self):
        self._openedSpectrumDisplays = [x for x in self._openedSpectrumDisplays if
                                        x in self.mainWindow.spectrumDisplays]

    def _isNameEditing(self):
        """
        True if any module is being renamed
        """
        return len(self._getModulesOnActiveNameEditing()) > 0

    def _finaliseAllNameEditing(self):
        for module in self._getModulesOnActiveNameEditing():
            module.label._renameLabel()

    def moveDock(self, dock, position, neighbor):
        """
        Move an existing Dock to a new location.
        """
        ## Moving to the edge of a tabbed dock causes a drop outside the tab box
        if (position in ['left', 'right', 'top', 'bottom'] and
                neighbor is not None and neighbor.container() is not None and
                neighbor.container().type() == 'tab'):
            neighbor = neighbor.container()
        self.addModule(dock, position, neighbor)

    moveModule = moveDock

    def makeContainer(self, typ):
        # stop the child containers from collapsing
        new = super(CcpnModuleArea, self).makeContainer(typ)
        new.setChildrenCollapsible(False)
        return new

    def getContainer(self, obj):
        if obj is None:
            return self
        if obj.container() is None:
            for i in self.children():
                if isinstance(i, Container):
                    self._container = i
        return obj.container()

    def apoptose(self, propagate=True):
        # remove top container if possible, close this area if it is temporary.
        if self.topContainer is None or self.topContainer.count() == 0:
            self.topContainer = None
            if self.temporary and self.home:
                self.home.removeTempArea(self)

    def _closeOthers(self, moduleToClose):
        modules = [module for module in self.ccpnModules if module != moduleToClose]
        for module in modules:
            module._closeModule()

    def _closeAll(self):
        for module in self.ccpnModules:
            module._closeModule()

    ## docksOnly is used for in memory save and restore for the module maximise save and restore system
    ## if docksOnly we are saving state to memory and are maximising or restoring docks
    def saveState(self, docksOnly=False):
        """
        Return a serialized (storable) representation of the state of
        all Docks in this DockArea."""

        state = {}
        try:
            getLogger().info('Saving V3.1 Layout')
            state = {'main'   : ('area', self.childState(self.topContainer, docksOnly), {'id': id(self)}), 'floats': [],
                     'version': "3.1", 'inMemory': docksOnly}

            for a in self.tempAreas:
                if a is not None:
                    geo = a.win.geometry()
                    geo = (geo.x(), geo.y(), geo.width(), geo.height())
                    areaState = ('area', self.childState(a.topContainer, docksOnly), {'geo': geo, 'id': id(a)})
                    state['floats'].append(areaState)
        except Exception as e:
            getLogger().warning(f'Impossible to save layout. {e}')
        return state

    def childState(self, obj, docksOnly=False):

        if isinstance(obj, Dock):
            # GST for maximise restore syste
            # maximiseState = {'maximised' : obj.maximised, 'maximiseRestoreState' : obj.maximiseRestoreState, 'titleBarHidden' : obj.titleBarHidden}
            maximiseState = {}
            # if docksOnly:
            #     objWidgetsState = maximiseState
            # else:
            objWidgetsState = dict(obj.widgetsState, **maximiseState)
            return ('dock', obj.name(), objWidgetsState)
        else:
            childs = []
            if obj is not None:
                for i in range(obj.count()):
                    try:
                        widg = obj.widget(i)
                        if not docksOnly or (docksOnly and isinstance(widg, (Dock, Container))):
                            if not widg.isHidden():
                                childList = self.childState(widg, docksOnly)
                                childs.append(childList)
                    except Exception as es:
                        getLogger().warning(f'Error accessing widget: {str(es)} - {widg} - {obj}')

                return (obj.type(), childs, obj.saveState())

    def addTempArea(self):
        if self.home is None:
            area = CcpnModuleArea(mainWindow=self.mainWindow)
            area.temporary = True
            area.home = self
            self.tempAreas.append(area)
            win = TempAreaWindow(area, mainWindow=self.mainWindow)
            area.win = win
            win.show()
        else:
            area = self.home.addTempArea()
        # print "added temp area", area, area.window()
        return area

    def restoreState(self, state, restoreSpectrumDisplay=False):
        """
        Restore Dock configuration as generated by saveState.

        Note that this function does not create any Docks--it will only
        restore the arrangement of an existing set of Docks.

        """
        modulesNames = [m.name() for m in self.ccpnModules]

        version = "3.0"
        floatContainer = 'float'
        if 'version' in state:
            version = state['version']
            floatContainer = 'floats'
            getLogger().debug('Reading from V%s layout format.' % version)

        if 'main' in state:
            ## 1) make dict of all docks and list of existing containers
            containers, docks = self.findAll()

            # GST this appears to be important for the in memory save and restore code
            if self.home is None:
                oldTemps = self.tempAreas[:]
            else:
                oldTemps = self.home.tempAreas[:]

            if state['main'] is not None:
                # 2) create container structure, move docks into new containers
                self._buildFromState(modulesNames, state['main'], docks, self,
                                     restoreSpectrumDisplay=restoreSpectrumDisplay)

            ## 3) create floating areas, populate
            for s in state[floatContainer]:
                a = None

                # for maximise and restore code
                if version == "3.1":
                    stateId = s[2]['id']

                    if state['inMemory']:
                        for temp in oldTemps:
                            if id(temp) == stateId:
                                a = temp
                                oldTemps.remove(temp)
                                break
                if a is None:
                    a = self.addTempArea()

                # GST this indicates a new format file
                if version == "3.1":
                    a._buildFromState(modulesNames, s, docks, a, restoreSpectrumDisplay=restoreSpectrumDisplay)
                    a.win.setGeometry(*s[2]['geo'])
                else:
                    a._buildFromState(modulesNames, s[0]['main'], docks, a,
                                      restoreSpectrumDisplay=restoreSpectrumDisplay)
                    a.win.setGeometry(*s[1])

            ## 4) Add any remaining docks to the bottom
            for d in docks.values():
                self.moveDock(d, 'below', None)  #, initTime=True)

            ## 5) kill old containers
            # if is not none  delete
            if state['main'] is not None:
                for c in containers:
                    if c is not None:
                        c.close()
            for a in oldTemps:
                if a is not None:
                    a.apoptose()

            for d in self.ccpnModules:
                if d:
                    if d.className == Failed:
                        d.close()
                        getLogger().warning('Failed to restore: %s' % d.name())

    def _buildFromState(self, openedModulesNames, state, docks, root, depth=0, restoreSpectrumDisplay=False):
        typ, contents, state = state

        if typ == 'dock':
            # try:
            if contents in openedModulesNames:
                obj = docks[contents]
                if not isinstance(obj, GuiSpectrumDisplay) or \
                        (isinstance(obj, GuiSpectrumDisplay) and restoreSpectrumDisplay):
                    obj.restoreWidgetsState(**state)
                del docks[contents]
            else:
                obj = CcpnModule(self.mainWindow, contents)
                obj.className = Failed
                label = Label(obj, 'Failed to restore %s' % contents)
                obj.addWidget(label)
                self.addModule(obj)

        # GST only present in v 3.1 layouts
        elif typ == 'area':
            if contents is not None:
                self._buildFromState(openedModulesNames, contents, docks, root, depth,
                                     restoreSpectrumDisplay=restoreSpectrumDisplay)
            obj = None

            # except KeyError:
            #   raise Exception('Cannot restore dock state; no dock with name "%s"' % contents)
        else:
            obj = self.makeContainer(typ)

        if obj is not None:
            if hasattr(root, 'type'):
                root.insert(obj)

            if typ != 'dock':
                for o in contents:
                    self._buildFromState(openedModulesNames, o, docks, obj, depth + 1,
                                         restoreSpectrumDisplay=restoreSpectrumDisplay)
                obj.apoptose(propagate=False)
                obj.restoreState(state)  ## this has to be done later?

    def restoreModuleState(self, layout, module, discard=False):
        """Search the restore tree for a given module
        """
        if 'layoutState' in layout:
            # Very important step:
            # Checks if the all the modules opened are present in the layout state. If not, will not restore the geometries
            state = layout.get('layoutState')

            if 'version' in state:
                version = state['version']
                getLogger().debug('Reading from V%s layout format.' % version)

            if 'main' in state and state['main'] is not None:
                return self._searchState(module, state['main'], discard)

    def _searchState(self, module, state, discard):
        """Traverse through the tree to find the module
        """
        try:
            typ, contents, state = state
        except Exception:
            typ, contents = state

        if typ == 'dock':
            # check the longPid for modules other than spectrumDisplay
            if contents == module.longPid:
                # found matching module so restore
                module.restoreWidgetsState(**state)
                return True

        elif typ == 'area':
            if contents is not None:
                return self._searchState(module, contents, discard)

        else:
            if contents is not None:
                found = None
                for ii, o in enumerate(contents):
                    if self._searchState(module, o, discard):
                        found = ii
                        break
                if found is not None:
                    if discard:
                        # remove from the list
                        contents.pop(ii)
                    return True
