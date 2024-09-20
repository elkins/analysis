"""GUI window class

"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2024"
__credits__ = ("Ed Brooksbank, Joanna Fox, Morgan Hayward, Victoria A Higman, Luca Mureddu",
               "Eliza Płoskoń, Timothy J Ragan, Brian O Smith, Gary S Thompson & Geerten W Vuister")
__licence__ = ("CCPN licence. See https://ccpn.ac.uk/software/licensing/")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, https://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2024-05-10 16:28:56 +0100 (Fri, May 10, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from functools import partial
from typing import Sequence, Tuple, List, Union

from ccpnmodel.ccpncore.api.ccpnmr.gui.Window import Window as ApiWindow
from ccpn.core.Project import Project
from ccpn.core.Spectrum import Spectrum
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.core.lib import Pid
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core.lib.ContextManagers import newObject, undoBlockWithoutSideBar, undoStackBlocking, \
    logCommandManager
from ccpn.util.decorators import logCommand
from ccpn.util.Logging import getLogger


class Window(AbstractWrapperObject):
    """UI window, corresponds to OS window
    The _factoryFunction is inserted from ui.gui.MainWindow
    """

    #: Short class name, for PID.
    shortClassName = 'GW'
    # Attribute it necessary as subclasses must use superclass className
    className = 'Window'

    _parentClass = Project

    #: Name of plural link to instances of class
    _pluralLinkName = 'windows'

    #: List of child classes.
    _childClasses = []

    _isGuiClass = True

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiWindow._metaclass.qualifiedName()

    #=========================================================================================

    def __init__(self, project, wrappedData):
        super().__init__(project=project, wrappedData=wrappedData)
        getLogger().debug(f'Initialised {self.pid}')

    #=========================================================================================
    # CCPN properties
    #=========================================================================================

    @property
    def _apiWindow(self) -> ApiWindow:
        """ CCPN Window matching Window"""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """short form of name, corrected to use for id"""
        return self._wrappedData.title.translate(Pid.remapSeparators)

    @property
    def _localCcpnSortKey(self) -> Tuple:
        """Local sorting key, in context of parent."""
        return (self._wrappedData.title,)

    @property
    def title(self) -> str:
        """Window display title (not used in PID)."""
        return self._wrappedData.title

    @property
    def _parent(self) -> Project:
        """Parent (containing) object."""
        return self._project

    @property
    def position(self) -> tuple:
        """Window X,Y position in integer pixels"""
        return self._wrappedData.position

    @position.setter
    def position(self, value: Sequence):
        self._wrappedData.position = value

    @property
    def size(self) -> tuple:
        """Window X,Y size in integer pixels"""
        return self._wrappedData.size

    @size.setter
    def size(self, value: Sequence):
        self._wrappedData.size = value

    # marks are now contained in project, but groups are accessed through mainWindow/spectrumDisplays
    @property
    def marks(self) -> tuple:
        """Return the associated marks for the mainWindow.
        There are marks that are common to all spectrumDisplay/strips.
        SpectrumDisplays/strips also have specific marks.
        """
        try:
            refHandler = self._project._crossReferencing
            return refHandler.getValues(self, '_MarkWindow', 1)  # index of 1 for strips

        except Exception:
            return ()

    @marks.setter
    def marks(self, values):
        """Set the associated marks for the mainWindow.
        """
        if not isinstance(values, (tuple, list, type(None))):
            raise TypeError(f'{self.__class__.__name__}.marks must be a list or tuple, or None')
        values = values or []

        try:
            refHandler = self._project._crossReferencing
            refHandler.setValues(self, '_MarkWindow', 1, values)

        except Exception as es:
            raise RuntimeError(f'{self.__class__.__name__}.marks: Error setting marks {es}') from es

    @property
    def strips(self):
        """Return a list of strips in the MainWindow.
        :return: a list of strips.
        """
        return tuple(strip for display in self.spectrumDisplays for strip in display.strips)

    #=========================================================================================
    # property STUBS: hot-fixed later
    #=========================================================================================

    @property
    def axes(self) -> list['Axis']:
        """STUB: hot-fixed later
        :return: a list of axes in the MainWindow
        """
        return []

    @property
    def integralListViews(self) -> list['IntegralListView']:
        """STUB: hot-fixed later
        :return: a list of integralListViews in the MainWindow
        """
        return []

    @property
    def integralViews(self) -> list['IntegralView']:
        """STUB: hot-fixed later
        :return: a list of integralViews in the MainWindow
        """
        return []

    @property
    def multipletListViews(self) -> list['MultipletListView']:
        """STUB: hot-fixed later
        :return: a list of multipletListViews in the MainWindow
        """
        return []

    @property
    def multipletViews(self) -> list['MultipletView']:
        """STUB: hot-fixed later
        :return: a list of multipletViews in the MainWindow
        """
        return []

    @property
    def peakListViews(self) -> list['PeakListView']:
        """STUB: hot-fixed later
        :return: a list of peakListViews in the MainWindow
        """
        return []

    @property
    def peakViews(self) -> list['PeakView']:
        """STUB: hot-fixed later
        :return: a list of peakViews in the MainWindow
        """
        return []

    @property
    def spectrumDisplays(self) -> list['SpectrumDisplay']:
        """STUB: hot-fixed later
        :return: a list of spectrumDisplays in the MainWindow
        """
        return []

    @property
    def spectrumViews(self) -> list['SpectrumView']:
        """STUB: hot-fixed later
        :return: a list of spectrumViews in the MainWindow
        """
        return []

    # replaced above
    # @property
    # def strips(self) -> list['Strip']:
    #     """STUB: hot-fixed later
    #     :return: a list of strips in the MainWindow
    #     """
    #     return []

    #=========================================================================================
    # getter STUBS: hot-fixed later
    #=========================================================================================

    def getAxis(self, relativeId: str) -> 'Axis | None':
        """STUB: hot-fixed later
        :return: an instance of Axis, or None
        """
        return None

    def getIntegralListView(self, relativeId: str) -> 'IntegralListView | None':
        """STUB: hot-fixed later
        :return: an instance of IntegralListView, or None
        """
        return None

    def getIntegralView(self, relativeId: str) -> 'IntegralView | None':
        """STUB: hot-fixed later
        :return: an instance of IntegralView, or None
        """
        return None

    def getMultipletListView(self, relativeId: str) -> 'MultipletListView | None':
        """STUB: hot-fixed later
        :return: an instance of MultipletListView, or None
        """
        return None

    def getMultipletView(self, relativeId: str) -> 'MultipletView | None':
        """STUB: hot-fixed later
        :return: an instance of MultipletView, or None
        """
        return None

    def getPeakListView(self, relativeId: str) -> 'PeakListView | None':
        """STUB: hot-fixed later
        :return: an instance of PeakListView, or None
        """
        return None

    def getPeakView(self, relativeId: str) -> 'PeakView | None':
        """STUB: hot-fixed later
        :return: an instance of PeakView, or None
        """
        return None

    def getSpectrumDisplay(self, relativeId: str) -> 'SpectrumDisplay | None':
        """STUB: hot-fixed later
        :return: an instance of SpectrumDisplay, or None
        """
        return None

    def getSpectrumView(self, relativeId: str) -> 'SpectrumView | None':
        """STUB: hot-fixed later
        :return: an instance of SpectrumView, or None
        """
        return None

    def getStrip(self, relativeId: str) -> 'Strip | None':
        """STUB: hot-fixed later
        :return: an instance of Strip, or None
        """
        return None

    #=========================================================================================
    # Core methods
    #=========================================================================================

    @property
    def pinnedStrips(self):
        """Return the list of pinned strips.
        """
        return list(filter(lambda st: st.pinned, self.strips))

    def _getModuleInsertList(self, moduleArea):
        """Generate the list of .moveDock instructions that are required to move all modules back to their
        original positions in the layout
        """
        from collections import OrderedDict

        # initialise lists
        cntrsDict = OrderedDict()
        cntrsDict[moduleArea.topContainer] = None
        nodes = []
        insertsDict = OrderedDict()

        def _setContainerWidget(cntr):
            """Label the containers with the attached display

                   A/\
                   /  \
                  /    \            Tree traversed from left-right, i.e. iterating through widget(ii) of containers
                 /      \           items will always be either to the right, or below previous modules
               A/        \C
               /\        /\         A found first, and propagated up to the containers which
              /  \      /  \            are located at the forks
             /    \E   /    \G      E propagated up, but only one fork not allocated
            A     /\  C     /\      F has nothing
                 /  \      /  \     C propagated up, but only one fork not allocated
                /    \    /    \    G&H nothing to set
               E     F   G     H

            """
            count = cntr.count()
            for ww in range(count):
                widget = cntr.widget(ww)

                if not hasattr(widget, 'type'):
                    # widget is a module, add to list
                    nodes.append(widget)

                    # find the chain of containers to the topContainer/moduleArea that have not been set
                    # and set to the current module
                    parentContainer = cntr
                    while parentContainer is not moduleArea:
                        if parentContainer not in cntrsDict:
                            cntrsDict[parentContainer] = None

                        if cntrsDict[parentContainer] is None:
                            cntrsDict[parentContainer] = widget
                            parentContainer = parentContainer.container()
                        else:
                            break
                else:
                    _setContainerWidget(widget)

        def _insertWidgets(cntr, root=None):
            """Get the ordering for inserting the new containers
            Iterate through the modue structure of containers and modules

            If a container found (a fork shown above) then add to the list
                position will always be to the right, below or 'top' if the first item
                relativeTo will be the node labelled at the fork, or
                    None if the first item - all following items will be referenced to this

            If a module found then and to the list
                position will always be to the right or below
                relativeTo will be the node labelled at the fork.
            """
            count = cntr.count()
            reorderedWidgets = [cntr.widget(0)] + [cntr.widget(ii) for ii in range(count - 1, 0, -1)]

            for ww in range(count):
                widget = reorderedWidgets[ww]

                vv = cntrsDict[widget] if widget in cntrsDict else widget
                if vv not in insertsDict:
                    parent = cntrsDict[cntr]
                    typ = cntr.type()
                    position = 'bottom' if typ == 'vertical' else 'right'
                    insertsDict[vv] = (position, parent)

            # go through the next depth
            for ww in range(count):
                widget = cntr.widget(ww)

                if widget in cntrsDict:
                    _insertWidgets(widget, cntrsDict[widget])

        if moduleArea.topContainer:
            _setContainerWidget(moduleArea.topContainer)
            insertsDict[nodes[0]] = ('top', None)
            _insertWidgets(moduleArea.topContainer, None)
            return insertsDict

        return {}

    def _restoreModules(self, moduleList):
        """Recover modules to their original positions
        """
        # NOTE:ED currently recovers all modules, not just spectrumDisplays
        # needs to handle different moduleAreas
        for mods, (pos, rel) in moduleList.items():
            # may need to have a dock.float() in here somewhere if from a deleted moduleArea
            self.moduleArea.moveDock(mods, pos, rel)
            # recover sizes?

    @staticmethod
    def _recoverSpectrumToolbar(display, specViewList):
        """Re-insert the spectra into the spectrumToolbar
        """
        for specView, selected in specViewList:
            if action := display.spectrumToolBar._addSpectrumViewToolButtons(specView):
                action.setChecked(selected)

    @staticmethod
    def _setBlankingSpectrumDisplayNotifiers(display, value):
        """Blank all spectrumDisplay and contained strip notifiers
        """
        display.setBlankingAllNotifiers(value)
        for strip in display.strips:
            strip.setBlankingAllNotifiers(value)

            # stop events when the display is being closed
            strip._CcpnGLWidget._blankDisplay = True

    #=========================================================================================
    # Implementation functions
    #=========================================================================================

    @classmethod
    def _getAllWrappedData(cls, parent: Project) -> list:
        """get wrappedData (ccp.gui.windows) for all Window children of parent NmrProject.windowStore"""
        windowStore = parent._wrappedData.windowStore

        return [] if windowStore is None else windowStore.sortedWindows()

    #=========================================================================================
    # 'new' methods
    #=========================================================================================

    @logCommand('mainWindow.')
    def newMacroEditor(self, path=None, position='top', relativeTo=None):
        """Open a new Module to edit macros
        """
        # local to prevent circular import
        from ccpn.ui.gui.modules.MacroEditor import MacroEditor

        path = str(path) if path is not None else None
        macroEditor = MacroEditor(mainWindow=self, filePath=path, restore=False)
        self.moduleArea.addModule(macroEditor, position=position, relativeTo=relativeTo)
        return macroEditor

    # @logCommand('mainWindow.')
    # def newHtmlModule(self, urlPath, position='top', relativeTo=None):
    #     """Open a new Module to display urlPath
    #     """
    #     # local to prevent circular imports
    #     from ccpn.ui.gui.widgets.CcpnWebView import CcpnWebView
    #
    #     htmlModule = CcpnWebView(mainWindow=self, urlPath=urlPath)
    #     self.moduleArea.addModule(htmlModule, position=position, relativeTo=relativeTo)
    #     return htmlModule

    #Command logging done inside the method
    def newSpectrumDisplay(self, spectra, axisCodes: Sequence[str] = (), stripDirection: str = 'Y',
                           position='right', relativeTo=None, flip1D=False):
        """Create new SpectrumDisplay.

        :param spectra: a Spectrum or SpectrumGroup instance, or a list,tuple of Spectrum Instances to be displayed.
        :param axisCodes: display order of the dimensions of spectrum (defaults to spectrum.preferredAxisOrdering).
        :param stripDirection: stripDirection: if 'X' or 'Y' sets strip axis.

        :return: a new SpectrumDisplay instance.
        """

        from ccpn.ui._implementation.SpectrumDisplay import _newSpectrumDisplay
        from ccpn.ui.gui.lib.GuiSpectrumDisplay import STRIPDIRECTIONS
        from ccpn.ui.gui.guiSettings import ZPlaneNavigationModes

        if isinstance(spectra, str):
            spectra = self.project.getByPid(spectra)

        if not isinstance(spectra, (Spectrum, SpectrumGroup, list, tuple)):
            raise ValueError(
                    f'Invalid spectra argument, expected Spectrum, list of Spectra or SpectrumGroup; got "{spectra}"')

        if isinstance(spectra, Spectrum):
            isGrouped = False
            isList = False
            spectrum = spectra
        elif isinstance(spectra, SpectrumGroup) and len(spectra.spectra) > 0:
            isGrouped = True
            isList = False
            spectrum = spectra.spectra[0]
        elif isinstance(spectra, (list, tuple)) and len(spectra) > 0:
            isGrouped = False
            isList = True
            spectrum = spectra[0]
            if not isinstance(spectrum, Spectrum):
                raise ValueError(f'Invalid spectra argument, expected list to contain Spectra; got "{spectra}"')
        else:
            raise ValueError(f'{spectra} has no spectra')

        if not axisCodes:
            if len(spectrum.axisCodes) > 1:
                axisCodes = tuple(spectrum.axisCodes[ac] for ac in spectrum._preferredAxisOrdering)
            else:
                # disregard the preferred ordering for 1d spectra and set the flipped flag instead
                axisCodes = tuple(spectrum.axisCodes)
                flip1D = spectrum._preferredAxisOrdering[0] == 1

        # change string names to objects
        if isinstance(relativeTo, str):
            modules = [module for module in self.modules if module.pid == relativeTo]
            if len(modules) > 1:
                raise ValueError("Error, not a unique module")
            relativeTo = modules[0] if modules else None

        with logCommandManager('mainWindow.', 'newSpectrumDisplay',
                               spectra, axisCodes=axisCodes, stripDirection=stripDirection,
                               position=position, relativeTo=relativeTo):
            # with undoBlockWithoutSideBar():
            with undoStackBlocking() as _:  # Do not add to undo/redo stack

                try:
                    zPlaneNavigationMode = ZPlaneNavigationModes(0).dataValue

                    # default to preferences if not set
                    _stripDirection = self.project.application.preferences.general.stripArrangement
                    stripDirection = stripDirection or STRIPDIRECTIONS[_stripDirection]
                    _zPlaneNavigationMode = self.project.application.preferences.general.zPlaneNavigationMode
                    zPlaneNavigationMode = ZPlaneNavigationModes(_zPlaneNavigationMode).dataValue
                except Exception as es:
                    getLogger().warning(f'newSpectrumDisplay {es}')

                # create the new spectrumDisplay
                display = _newSpectrumDisplay(self,
                                              spectrum=spectrum,
                                              axisCodes=axisCodes,
                                              stripDirection=stripDirection,
                                              zPlaneNavigationMode=zPlaneNavigationMode,
                                              isGrouped=isGrouped,
                                              flip1D=flip1D,
                                              )

                # add the new module to mainWindow at the required position
                self.moduleArea.addModule(display, position=position, relativeTo=relativeTo)
                display._insertPosition = (position, relativeTo)

                with undoStackBlocking() as addUndoItem:
                    # disable all notifiers in spectrumDisplays
                    addUndoItem(undo=partial(self._setBlankingSpectrumDisplayNotifiers, display, True),
                                redo=partial(self._setBlankingSpectrumDisplayNotifiers, display, False))

                    # add/remove spectrumDisplay from module Area - use moveDock not addModule, otherwise introduces extra splitters
                    addUndoItem(undo=partial(self._hiddenModules.moveDock, display, position='top', neighbor=None),
                                redo=partial(self.moduleArea.moveDock, display, position=position, neighbor=relativeTo))

                # if not positions and not widths:
                #     display.autoRange()

                if isGrouped:
                    display._colourChanged(spectra)
                    display.spectrumToolBar.hide()
                    display.spectrumGroupToolBar.show()
                    display.spectrumGroupToolBar._addAction(spectra)

                if isList:
                    for sp in spectra[1:]:
                        display.displaySpectrum(sp)

        return display

    # deprecated
    createSpectrumDisplay = newSpectrumDisplay

    def _deleteSpectrumDisplay(self, display):
        """Delete a spectrumDisplay from the moduleArea
        Removes the display to a hidden moduleArea of mainWindow, deletes the _wrappedData, and disables all notifiers
        Object is recovered through the deleteObject decorator
        """
        # with undoBlockWithoutSideBar():
        with undoStackBlocking() as _:  # Do not add to undo/redo stack
            # # get the current state of the layout
            # _list = self._getModuleInsertList(moduleArea=display.area)

            # # get the list of spectra currently displayed in the spectrumDisplay
            # specViewList = [(specView, action.isChecked()) for specView in display.spectrumViews
            #                 for action in display.spectrumToolBar.actions()
            #                 if action.objectName() == specView.spectrum.pid]
            #
            # with undoStackBlocking() as addUndoItem:
            #     # re-insert spectrumToolbar
            #     addUndoItem(undo=partial(self._recoverSpectrumToolbar, display, specViewList), )
            #
            #     # disable all notifiers in spectrumDisplays
            #     addUndoItem(undo=partial(self._setBlankingSpectrumDisplayNotifiers, display, False),
            #                 redo=partial(self._setBlankingSpectrumDisplayNotifiers, display, True))
            #
            #     # add/remove spectrumDisplay from module Area - using moveDock method
            #     addUndoItem(undo=partial(self._restoreModules, _list),
            #                 redo=partial(self._hiddenModules.moveDock, display, position='top', neighbor=None), )

            # disable the spectrumDisplay notifiers
            self._setBlankingSpectrumDisplayNotifiers(display, True)

            # move to the hidden module area
            self._hiddenModules.moveDock(display, position='top', neighbor=None)

            _strips = list(display.strips)
            # delete the spectrumDisplay
            display.delete()

            # this makes it unrecoverable - okay, as strips not allowed to undo
            for st in _strips:
                # marks are not automatically deleted by the model when deleting strips
                for mark in st.marks:
                    mark.delete()
            # marks are not automatically deleted by the model when deleting strips
            for mark in display.marks:
                mark.delete()

                st.close()

            # Update the list of opened GUI SpectrumDisplays modules
            self.moduleArea._updateSpectrumDisplays()

    @logCommand('mainWindow.')
    def newMark(self, colour: str, positions: Sequence[float], axisCodes: Sequence[str],
                style: str = 'simple', units: Sequence[str] = (), labels: Sequence[str] = (),
                strips: List[Union[str, 'Strip']] = None,
                ):
        """Create new Mark.

        :param str colour: Mark colour.
        :param tuple/list positions: Position in unit (default ppm) of all lines in the mark.
        :param tuple/list axisCodes: Axis codes for all lines in the mark.
        :param str style: Mark drawing style (dashed line etc.) default: full line ('simple').
        :param tuple/list units: Axis units for all lines in the mark, Default: all ppm.
        :param tuple/list labels: Ruler labels for all lines in the mark. Default: None.
        :param tuple/list strips: List of strips or pids.
        :return Mark instance.
        """
        from ccpn.ui._implementation.Mark import _newMark, _removeMarkAxes

        with undoBlockWithoutSideBar():
            if marks := _removeMarkAxes(self, positions=positions, axisCodes=axisCodes, labels=labels):
                pos, axes, lbls = marks
                if not pos:
                    return

                result = _newMark(self, colour=colour, positions=pos, axisCodes=axes,
                                  style=style, units=units, labels=lbls,
                                  )
                # add spectrumDisplay to the new mark
                result.windows = [self]

                return result

        # with undoBlockWithoutSideBar():
        #     marks = []
        #     for specDisplay in self.spectrumDisplays:
        #         marks.extend(
        #                 specDisplay.newMark(
        #                         colour=colour,
        #                         positions=positions,
        #                         axisCodes=axisCodes,
        #                         style=style,
        #                         units=units,
        #                         labels=labels,
        #                         ))
        #
        #     return tuple(marks)


#=========================================================================================
# Connections to parents:
#=========================================================================================

@newObject(Window)
def _newWindow(self: Project, title: str = None, position: tuple = (), size: tuple = ()) -> Window:
    """Create new child Window.

    See the Window class for details.

    :param str title: window  title (optional, defaults to 'W1', 'W2', 'W3', ...
    :param tuple position: x,y position for new window in integer pixels.
    :param tuple size: x,y size for new window in integer pixels.
    :return: a new Window instance.
    """

    if title and Pid.altCharacter in title:
        raise ValueError(f"Character {Pid.altCharacter} not allowed in gui.core.Window.title")

    apiWindowStore = self._project._wrappedData.windowStore

    apiGuiTask = (apiWindowStore.root.findFirstGuiTask(nameSpace='user', name='View')
                  or apiWindowStore.root.newGuiTask(nameSpace='user', name='View'))
    newApiWindow = apiWindowStore.newWindow(title=title, guiTask=apiGuiTask)
    if position:
        newApiWindow.position = position
    if size:
        newApiWindow.size = size

    result = self._data2Obj.get(newApiWindow)
    if result is None:
        raise RuntimeError('Unable to generate new Window item')

    return result

#EJB 20181205: moved to Project
# Project.newWindow = _newWindow
# del _newWindow

# Notifiers: None
