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
__dateModified__ = "$dateModified: 2024-08-23 19:23:56 +0100 (Fri, August 23, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2020-06-15 10:06:31 +0000 (Mon, June 15, 2020) $"
#=========================================================================================
# Start of code
#=========================================================================================

from PyQt5 import QtGui, QtCore
from functools import partial
from collections import Counter
from ccpn.core.MultipletList import MultipletList
from ccpn.core.Spectrum import Spectrum
from ccpn.core.PeakList import PeakList
from ccpn.core.ChemicalShiftList import ChemicalShiftList
from ccpn.core.SpectrumGroup import SpectrumGroup
from ccpn.core.Note import Note
from ccpn.core.Sample import Sample
from ccpn.core.IntegralList import IntegralList
from ccpn.core.NmrChain import NmrChain
from ccpn.core.NmrResidue import NmrResidue, MoveToEnd
from ccpn.core.NmrAtom import NmrAtom
from ccpn.core.Chain import Chain
from ccpn.core.StructureEnsemble import StructureEnsemble
from ccpn.core.RestraintTable import RestraintTable
from ccpn.core.DataTable import DataTable
from ccpn.core.ViolationTable import ViolationTable
from ccpn.core.Collection import Collection
from ccpn.ui.gui.popups.SpectrumGroupEditor import SpectrumGroupEditor
from ccpn.ui.gui.widgets.Menu import Menu
from ccpn.ui.gui.widgets.MessageDialog import showInfo, showWarning, showYesNoWarning
from ccpn.ui.gui.widgets.Font import setWidgetFont
from ccpn.ui.gui.widgets.Icon import Icon
from ccpn.ui.gui.popups.ChainPopup import ChainPopup
from ccpn.ui.gui.popups.ChemicalShiftListPopup import ChemicalShiftListEditor
from ccpn.ui.gui.popups.ComplexEditorPopup import ComplexEditorPopup
from ccpn.ui.gui.popups.CreateChainPopup import CreateChainPopup
from ccpn.ui.gui.popups.CreateNmrChainPopup import CreateNmrChainPopup
from ccpn.ui.gui.popups.StructureDataPopup import StructureDataPopup
from ccpn.ui.gui.popups.IntegralListPropertiesPopup import IntegralListPropertiesPopup
from ccpn.ui.gui.popups.MultipletListPropertiesPopup import MultipletListPropertiesPopup
from ccpn.ui.gui.popups.NmrAtomPopup import NmrAtomEditPopup, NmrAtomNewPopup
from ccpn.ui.gui.popups.NmrChainPopup import NmrChainPopup
from ccpn.ui.gui.popups.AtomPopup import AtomNewPopup, AtomEditPopup
from ccpn.ui.gui.popups.NmrResiduePopup import NmrResidueEditPopup, NmrResidueNewPopup
from ccpn.ui.gui.popups.NotesPopup import NotesPopup
from ccpn.ui.gui.popups.PeakListPropertiesPopup import PeakListPropertiesPopup
from ccpn.ui.gui.popups.RestraintTablePopup import RestraintTableEditPopup, RestraintTableNewPopup
from ccpn.ui.gui.popups.SampleComponentPropertiesPopup import SampleComponentPopup
from ccpn.ui.gui.popups.SamplePropertiesPopup import SamplePropertiesPopup
from ccpn.ui.gui.popups.SpectrumPropertiesPopup import SpectrumPropertiesPopup
from ccpn.ui.gui.popups.StructureEnsemblePopup import StructureEnsemblePopup
from ccpn.ui.gui.popups.SubstancePropertiesPopup import SubstancePropertiesPopup
from ccpn.ui.gui.popups.DataTablePopup import DataTablePopup
from ccpn.ui.gui.popups.ViolationTablePopup import ViolationTablePopup
from ccpn.ui.gui.popups.CollectionEditorPopup import CollectionEditorPopup
from ccpn.core.lib.ContextManagers import notificationEchoBlocking, \
    undoBlockWithoutSideBar, undoStackBlocking
from ccpn.util.OrderedSet import OrderedSet
from ccpn.util.Logging import getLogger
from ccpn.framework.Application import getProject


MAXITEMLOGGING = 2
_NEW_COLLECTION = 'New Collection'
_ADD_TO_COLLECTION = 'Add to Collection'
_REMOVE_FROM_COLLECTION = 'Remove from Collection'
_ITEMS_COLLECTION = 'Items'
_CLASH_COLOUR = QtGui.QColor('darkgoldenrod')


class CreateNewObjectABC():
    """
    An ABC to implement an abstract callback function to create new object
    The __call__(self, dataPid, node) method acts as the callback function
    """

    # These should be subclassed
    parentMethodName = None  # The name of the method in the parent class

    # This can be subclassed
    def getObj(self):
        """returns obj from node or None"""
        return self.node.obj

    def __init__(self, **kwds):
        # store keyword as attributes and as dict; acts as partial to popupClass
        for key, value in kwds.items():
            setattr(self, key, value)
        self.kwds = kwds
        # these get set upon callback
        self.node = None
        self.dataPid = None

    def __call__(self, mainWindow, dataPid, node):
        self.node = node
        self.dataPid = dataPid
        obj = self.getObj()
        # generate the new object
        func = getattr(obj, self.parentMethodName)
        if func is None:
            raise RuntimeError(f'Undefined function; cannot create new object ({dataPid})')
        newObj = func(**self.kwds)
        return newObj


class _createNewStructureData(CreateNewObjectABC):
    parentMethodName = 'newStructureData'


class _createNewPeakList(CreateNewObjectABC):
    parentMethodName = 'newPeakList'


class _createNewChemicalShiftList(CreateNewObjectABC):
    parentMethodName = 'newChemicalShiftList'


class _createNewMultipletList(CreateNewObjectABC):
    parentMethodName = 'newMultipletList'


class _createNewNmrResidue(CreateNewObjectABC):
    parentMethodName = 'newNmrResidue'


class _createNewNmrAtom(CreateNewObjectABC):
    parentMethodName = 'newNmrAtom'


class _createNewComplex(CreateNewObjectABC):
    parentMethodName = 'newComplex'


class _createNewRestraintTable(CreateNewObjectABC):
    parentMethodName = 'newRestraintTable'


class _createNewNote(CreateNewObjectABC):
    parentMethodName = 'newNote'


class _createNewIntegralList(CreateNewObjectABC):
    parentMethodName = 'newIntegralList'


class _createNewSample(CreateNewObjectABC):
    parentMethodName = 'newSample'


class _createNewSampleComponent(CreateNewObjectABC):
    parentMethodName = 'newSampleComponent'


class _createNewSubstance(CreateNewObjectABC):
    parentMethodName = 'newSubstance'


class _createNewStructureEnsemble(CreateNewObjectABC):
    parentMethodName = 'newStructureEnsemble'


class _createNewDataTable(CreateNewObjectABC):
    parentMethodName = 'newDataTable'


class _createNewViolationTable(CreateNewObjectABC):
    parentMethodName = 'newViolationTable'


class _createNewCollection(CreateNewObjectABC):
    parentMethodName = 'newCollection'


class RaisePopupABC():
    """
    An ABC to implement an abstract popup class
    The __call__(self, dataPid, node) method acts as the callback function
    """

    # These should be subclassed
    popupClass = None  # a subclass of CcpNmrDialog; used to generate a popup
    objectArgumentName = 'obj'  # argument name set to obj passed to popupClass instantiation
    parentObjectArgumentName = None  # parent argument name set to obj passed to popupClass instantiation when useParent==True

    # This can be subclassed
    def getObj(self):
        """returns obj from node or None
        """
        obj = None if self.useNone else self.node.obj
        return obj

    def __init__(self, useParent=False, useNone=False, **kwds):
        """store kwds; acts as partial to popupClass
        useParent: use parentObjectArgumentName for passing obj to popupClass
        useNone: set obj to None
        """
        self.useParent = useParent  # Use parent of object
        if useParent and self.parentObjectArgumentName is None:
            raise RuntimeError(f'useParent==True requires definition of parentObjectArgumentName ({self})')

        self.useNone = useNone
        self.kwds = kwds
        # these get set upon callback
        self.node = None
        self.dataPid = None

    def __call__(self, mainWindow, dataPid, node):
        self.node = node
        self.dataPid = dataPid
        obj = self.getObj()
        if self.useParent:
            self.kwds[self.parentObjectArgumentName] = obj
        else:
            self.kwds[self.objectArgumentName] = obj

        popup = self.popupClass(parent=node.sidebar, mainWindow=mainWindow,
                                **self.kwds)
        # popup.raise_()
        popup.exec_()


class _raiseNewChainPopup(RaisePopupABC):
    popupClass = CreateChainPopup
    parentObjectArgumentName = 'project'


class _raiseChainPopup(RaisePopupABC):
    popupClass = ChainPopup


class _raiseComplexEditorPopup(RaisePopupABC):
    popupClass = ComplexEditorPopup


class _raiseStructureDataPopup(RaisePopupABC):
    popupClass = StructureDataPopup
    # objectArgumentName = 'obj'


class _raiseChemicalShiftListPopup(RaisePopupABC):
    popupClass = ChemicalShiftListEditor
    # objectArgumentName = 'chemicalShiftList'


class _raisePeakListPopup(RaisePopupABC):
    popupClass = PeakListPropertiesPopup
    objectArgumentName = 'peakList'
    parentObjectArgumentName = 'spectrum'


class _raiseMultipletListPopup(RaisePopupABC):
    popupClass = MultipletListPropertiesPopup
    objectArgumentName = 'multipletList'
    parentObjectArgumentName = 'spectrum'


class _raiseCreateNmrChainPopup(RaisePopupABC):
    popupClass = CreateNmrChainPopup
    objectArgumentName = 'project'


class _raiseNmrChainPopup(RaisePopupABC):
    popupClass = NmrChainPopup
    # objectArgumentName = 'nmrChain'


class _raiseNmrResiduePopup(RaisePopupABC):
    popupClass = NmrResidueEditPopup
    # objectArgumentName = 'nmrResidue'


class _raiseNmrResidueNewPopup(RaisePopupABC):
    popupClass = NmrResidueNewPopup
    # objectArgumentName = 'nmrResidue'


class _raiseNmrAtomPopup(RaisePopupABC):
    popupClass = NmrAtomEditPopup
    # objectArgumentName = 'nmrAtom'


class _raiseNmrAtomNewPopup(RaisePopupABC):
    popupClass = NmrAtomNewPopup
    # objectArgumentName = 'nmrAtom'


class _raiseAtomPopup(RaisePopupABC):
    popupClass = AtomEditPopup
    # objectArgumentName = 'Atom'


class _raiseAtomNewPopup(RaisePopupABC):
    popupClass = AtomNewPopup
    # objectArgumentName = 'Atom'


class _raiseNotePopup(RaisePopupABC):
    popupClass = NotesPopup
    # objectArgumentName = 'obj'


class _raiseIntegralListPopup(RaisePopupABC):
    popupClass = IntegralListPropertiesPopup
    objectArgumentName = 'integralList'
    parentObjectArgumentName = 'spectrum'


class _raiseRestraintTableEditPopup(RaisePopupABC):
    popupClass = RestraintTableEditPopup
    # objectArgumentName = 'restraintTable'
    parentObjectArgumentName = 'structureData'


class _raiseRestraintTableNewPopup(_raiseRestraintTableEditPopup):
    popupClass = RestraintTableNewPopup


class _raiseSamplePopup(RaisePopupABC):
    popupClass = SamplePropertiesPopup
    objectArgumentName = 'sample'


class _raiseSampleComponentPopup(RaisePopupABC):
    popupClass = SampleComponentPopup
    # NB This popup is structured slightly different, passing in different arguments
    objectArgumentName = 'sampleComponent'
    parentObjectArgumentName = 'sample'


class _raiseSpectrumPopup(RaisePopupABC):
    popupClass = SpectrumPropertiesPopup
    objectArgumentName = 'spectrum'


class _raiseSpectrumGroupEditorPopup(RaisePopupABC):
    popupClass = SpectrumGroupEditor

    def _execOpenItem(self, mainWindow):
        """Acts as the entry point for opening items in ccpnModuleArea
        """
        popup = self.popupClass(parent=mainWindow, mainWindow=mainWindow,
                                **self.kwds)
        popup.exec()
        popup.raise_()


class _raiseStructureEnsemblePopup(RaisePopupABC):
    popupClass = StructureEnsemblePopup
    # objectArgumentName = 'obj'


class _raiseSubstancePopup(RaisePopupABC):
    popupClass = SubstancePropertiesPopup
    objectArgumentName = 'substance'


class _raiseDataTablePopup(RaisePopupABC):
    popupClass = DataTablePopup
    # objectArgumentName = 'obj'


class _raiseViolationTablePopup(RaisePopupABC):
    popupClass = ViolationTablePopup
    # objectArgumentName = 'obj'
    parentObjectArgumentName = 'structureData'


class _raiseCollectionPopup(RaisePopupABC):
    popupClass = CollectionEditorPopup
    # objectArgumentName = 'obj'


class OpenItemABC:
    """
    An ABC to implement an abstract openItem in moduleArea class
    The __call__(self, dataPid, node) method acts as the callback function
    """

    # These should be subclassed
    openItemMethod = None  # a method to open the item in ccpnModuleArea
    objectArgumentName = 'obj'  # argument name set to obj passed to openItemClass instantiation
    objectClassName = None
    openItemDirectMethod = None  # parent argument name set to obj passed to openItemClass instantiation when useParent==True
    useApplication = True
    hasOpenMethod = True
    contextMenuText = 'Open as a Module'

    validActionTargets = (Spectrum, PeakList, MultipletList, IntegralList,
                          NmrChain, Chain, SpectrumGroup, Sample, ChemicalShiftList,
                          RestraintTable, Note, StructureEnsemble, DataTable, ViolationTable, Collection
                          )

    # This can be subclassed
    def getObj(self):
        """returns obj from node or None
        """
        obj = None if self.useNone else self.node.obj
        return obj

    def __init__(self, useNone=False, **kwds):
        """store kwds; acts as partial to openItemClass
        useApplication: if true, use the method attached to application
                     : if false, use openItemDirectMethod for opening object in ccpnModuleArea
        useNone: set obj to None
        """
        if self.useApplication is False and self.openItemDirectMethod is None:
            raise RuntimeError(f'useApplication==False requires definition of openItemDirectMethod ({self})')

        self.objectClassName = self.objectArgumentName[0].upper() + self.objectArgumentName[1:]
        self.useNone = useNone
        self.kwds = kwds
        # these get set upon callback
        self.node = None
        self.dataPid = None
        self.mainWindow = None
        self.openAction = None

    def __call__(self, mainWindow, dataPid, node, position, objs):
        """__Call__ acts is the execute entry point for the callback.
        """
        self.node = node
        self.dataPid = dataPid
        thisObj = self.getObj()
        self.kwds[self.objectArgumentName] = thisObj
        self.mainWindow = mainWindow

        self._initialise(dataPid, objs)
        self._openContextMenu(node.sidebar, position, thisObj, objs)

    def _execOpenItem(self, mainWindow, obj):
        """Acts as an entry point for opening items in ccpnModuleArea
        """
        self.node = None
        self.dataPid = obj.pid
        self.kwds[self.objectArgumentName] = obj
        self.mainWindow = mainWindow

        self._initialise(obj.pid, [obj])
        return self.openAction()

    def _initialise(self, dataPid, objs):
        """Initialise settings for the object.
        """
        self.application = self.mainWindow.application
        openableObjs = [obj for obj in objs if isinstance(obj, self.validActionTargets)]

        if self.hasOpenMethod and openableObjs:
            if self.useApplication:
                func = getattr(self.application, self.openItemMethod)
            else:
                func = self.openItemDirectMethod

            if func is None:
                raise RuntimeError(f'Undefined function; cannot open object ({dataPid})')

            self.openAction = partial(func, **self.kwds)

    def _openContextMenu(self, parentWidget, position, thisObj, objs, deferExec=False):
        """Open a context menu.
        """
        contextMenu = Menu('', parentWidget, isFloatWidget=True)
        if self.openAction:
            contextMenu.addAction(self.contextMenuText, self.openAction)

        spectra = [obj for obj in objs if isinstance(obj, Spectrum)]
        if spectra:
            contextMenu.addAction('Make SpectrumGroup From Selected',
                                  partial(_raiseSpectrumGroupEditorPopup(useNone=True, editMode=False,
                                                                         defaultItems=spectra),
                                          self.mainWindow, self.getObj(), self.node))
        if any(any(sp.isTimeDomains) for sp in spectra):  # 3.1.0 alpha feature from macro.
            contextMenu.addAction('Split Planes to SpectrumGroup', partial(self._splitPlanesToSpectrumGroup, objs))
        contextMenu.addAction('Copy Pid to Clipboard', partial(self._copyPidsToClipboard, objs))
        self._addCollectionMenu(contextMenu, objs)
        contextMenu.addAction('Delete', partial(self._deleteItemObject, thisObj, objs))
        canBeCloned = all(hasattr(obj, 'clone') for obj in objs)
        if canBeCloned:
            contextMenu.addAction('Clone', partial(self._cloneObject, objs))

        contextMenu.addSeparator()
        contextMenu.addAction('Edit Properties', partial(parentWidget._raiseObjectProperties, self.node.widget))

        contextMenu.move(position)

        if not deferExec:
            # may want to defer the exec in a subclass
            contextMenu.exec()

        return contextMenu

    @staticmethod
    def _cloneObject(objs):
        """Clones the specified objects.
        """
        for obj in objs:
            obj.clone()

    @staticmethod
    def _deleteItemObject(thisObj, objs):
        """Delete items from the project.
        """

        try:
            if len(objs) > 0:
                getLogger().info(f"Deleting: {', '.join(map(str, objs))}")
                project = objs[-1].project
                with undoBlockWithoutSideBar():
                    with notificationEchoBlocking():
                        project.deleteObjects(*objs)

        except Exception as es:
            showWarning('Delete', str(es))

    @staticmethod
    def _copyPidsToClipboard(objs):
        """
        :param objs:
        Copy to clipboard quoted pids
        """
        from ccpn.util.Common import copyToClipboard

        copyToClipboard(objs)

    def _addCollectionMenu(self, menu, objs):
        """Add a quick submenu containing a list of collections
        """
        # add item to a new collection
        _action = menu.addItem(_NEW_COLLECTION,
                               callback=partial(self._makeNewCollection, selectionWidget=menu, objs=objs))

        # create subMenu for adding selected items to a single collection
        subMenu = menu.addMenu(_ADD_TO_COLLECTION)
        subMenu.setColourEnabled(True)  # enable foreground-colours for this menu
        collections = self.mainWindow.application.project.collections
        ttOk = 'Collection contains 1 or more of the selected objects;\nadd the remaining objects to the collection.'
        ttGood = 'Add all objects to the collection.'
        ttBad = 'All objects in selection are already contained in this collection.'
        _count = 0
        for col in collections:
            colSet, selSet = set(col.items), set(objs)
            diff = selSet - colSet
            # only select items that are in the collection
            _objs = [obj for obj in objs if obj not in col.items and obj != col]
            _action = subMenu.addAction(col.pid, partial(col.addItems, _objs))
            # add action to add to the collection
            if diff and diff != selSet:
                # flag that some of the selection may already be in this collection
                # Needs cleaning-up, probably needs to be an attribute of subclassed action
                _action._foregroundColour = QtGui.QColor('darkorange')
                _action.setToolTip(ttOk)
            elif _objs:
                _action.setToolTip(ttGood)
            else:
                _action.setToolTip(ttBad)
            if not _objs:
                # do these want to be disabled AND hidden?
                _action.setEnabled(False)
                # _action.setVisible(False)
                _count += 1
        if not len(subMenu.actions()) or _count == len(collections):
            # disable menu if empty
            subMenu.setEnabled(False)

        # create subMenu for removing selected items from a single collection - items are not deleted
        subMenu = menu.addMenu(_REMOVE_FROM_COLLECTION)
        subMenu.setColourEnabled(True)  # enable foreground-colours for this menu
        collections = self.mainWindow.application.project.collections
        ttOk = 'Collection contains 1 or more of the selected objects;\nremove the remaining objects from the ' \
               'collection.'
        ttGood = 'Remove all obects from the collection.'
        ttBad = 'None of the selected objects are in this collection.'
        _count = 0
        for col in collections:
            colSet, selSet = set(col.items), set(objs)
            diff = selSet - colSet
            # only select items that are in the collection
            _objs = [obj for obj in objs if obj in col.items and obj != col]
            # add action to remove from the collection
            _action = subMenu.addAction(col.pid, partial(col.removeItems, _objs))
            if diff and diff != selSet:
                # flag that some of the selection may already be in this collection
                _action._foregroundColour = QtGui.QColor('darkorange')
                _action.setToolTip(ttOk)
            elif _objs:
                _action.setToolTip(ttGood)
            else:
                _action.setToolTip(ttBad)
            if not _objs:
                # do these want to be disabled AND hidden?
                _action.setEnabled(False)
                # _action.setVisible(False)
                _count += 1
        if not len(subMenu.actions()) or _count == len(collections):
            # disable menu if empty
            subMenu.setEnabled(False)

    def _addToCollection(self, objs):
        """Add the objects to a collection
        Show popup to allow adding objects to specified collection
        For later when a more complex selector is required

        :param objs: list of sidebar objects
        """
        collectionPopup = AddToCollectionPopup(mainWindow=self.mainWindow, project=None, on_top=True)
        collectionPopup.hide()

        # show the collection popup
        pos = QtGui.QCursor().pos()
        mouse_screen = next((screen for screen in QtGui.QGuiApplication.screens() if screen.geometry().contains(pos)),
                            None)
        collectionPopup.showAt(pos, preferred_side=Side.RIGHT,
                               side_priority=(Side.TOP, Side.BOTTOM, Side.RIGHT, Side.LEFT),
                               target_screen=mouse_screen)

    @staticmethod
    def _splitPlanesToSpectrumGroup(objs):
        from ccpn.core.lib.SpectrumLib import splitPseudo3DSpectrumIntoPlanes

        for obj in objs:
            if not any(obj.isTimeDomains):
                showWarning('3.1.0 Alpha version',
                            'This functionality has been implemented for Time Domain spectra only.')
                return
            splitPseudo3DSpectrumIntoPlanes(obj)

    @staticmethod
    def _createNewCollection(pulldown, popup, items=None):
        """Create a new collection, or add to existing collection
        and close the editPopup.
        """
        collection = pulldown.getText()
        popup.hide()
        popup.deleteLater()

        _project = getProject()
        if (coll := _project.getObjectsById(className=Collection.__name__, id=collection)):

            # only select items that are not in the collection to stop duplicate-error
            items = list(OrderedSet(items) - set(coll[0].items))

            # add to the existing collection
            coll[0].addItems(items)

        else:
            try:
                # create a new collection
                _project.newCollection(name=collection, items=items)
            except (ValueError, TypeError) as es:
                showWarning('Create New Collection', str(es))

    @staticmethod
    def _newPulldown(parent, allowEmpty=True, name=Collection.__name__, **kwds):
        """Create a new pulldown-list to insert ino the new-collections widget
        """
        from ccpn.ui.gui.lib.Validators import LineEditValidator
        from ccpn.ui.gui.widgets.PulldownList import PulldownList

        combo = PulldownList(parent, editable=True, **kwds)
        combo.setMinimumWidth(50)
        _validator = LineEditValidator(parent=combo, allowSpace=False,
                                       allowEmpty=allowEmpty)
        combo.setValidator(_validator)
        combo.lineEdit().setPlaceholderText(f'<{name} Name>')

        combo.setToolTip('Select existing collection, or enter a name to create new collection.\n'
                         'Press <enter> to confirm, clicking outside the popup will cancel.')
        combo.setCompleter(None)

        return combo

    def _makeNewCollection(self, selectionWidget, objs):
        """Make a small popup to enter a new collection name
        """
        from ccpn.util.OrderedSet import OrderedSet
        from ccpn.ui.gui.widgets.ButtonList import Button

        # make a simple popup for editing collection
        class EditCollection(SpeechBalloon):
            """Balloon to hold the pulldown list for editing/selecting the collection name
            """
            _blockEscapeFlag = None
            _callback = None

            def __init__(self, parent, newPulldown, selectionWidget, *args, **kwds):
                """Initialise the class

                :param parent: parent class from which popup is instanciated
                :param newPulldown: func to create a new pulldown
                :param args: values to pass on to SpeechBalloon
                :param kwds: values to pass on to SpeechBalloon
                """
                super().__init__(*args, **kwds)

                self._parent = parent
                self._newPulldown = newPulldown
                self._selectionWidget = selectionWidget
                setWidgetFont(self)

                # simplest way to make the popup function as modal and disappear as required
                self.setWindowFlags(int(self.windowFlags()) | QtCore.Qt.Popup)
                self._metrics.corner_radius = 1
                self._metrics.pointer_height = 0

                # add the widgets
                _frame = Frame(self, setLayout=True, margins=(10, 10, 10, 10))
                title = 'New Collection/Add to Existing'
                _label = Label(_frame, text=title, grid=(0, 0), gridSpan=(1, 2))
                self._pulldownWidget = self._newPulldown(_frame, grid=(1, 0), gridSpan=(1, 9), )
                self._acceptButton = Button(_frame, grid=(2, 8), text='Accept', enabled=False)

                # set to the class central widget
                self.setCentralWidget(_frame)
                self._pulldownWidget.view().setObjectName('_PULLDOWNVIEW')
                self._pulldownWidget.view().installEventFilter(self)
                self._pulldownWidget.setObjectName('_PULLDOWN')
                self._pulldownWidget.installEventFilter(self)

            # add methods for setting pulldown options
            def setDefaultName(self, name):
                self._pulldownWidget.lineEdit().setText(name)

            def setPulldownData(self, texts):
                self._pulldownWidget.setData(texts=texts)

            def setPulldownCallback(self, callback):
                self._callback = partial(callback,
                                         pulldown=self._pulldownWidget,
                                         popup=self)
                self._acceptButton.setCallback(self._callback)
                self._acceptButton.setEnabled(True)

            @property
            def centralWidgetSize(self):
                """Return the sizeHint for the central widget
                """
                return self._central_widget_size()

            def _filterCollections(self, selectedObjs):
                if not (project := getProject()):
                    return
                combo = self._pulldownWidget
                # accounts for any separators
                for ind in range(self._pulldownWidget.count()):
                    itm = combo.model().item(ind)
                    if collection := project.getByPid('CO:' + itm.text()):
                        colSet, selSet = set(collection.items), set(selectedObjs)
                        diff = selSet - colSet
                        itm.setEnabled(bool(diff))
                        if diff and diff != selSet:
                            # flag that some of the selection may already be in this collection
                            itm.setData(_CLASH_COLOUR, QtCore.Qt.ForegroundRole)
                combo.repaint()

            def _resetPulldown(self):
                # release the block on the pulldown
                # so that enter-key works correctly on the lineEdit
                self._pulldownWidget.lineEdit().setFocus()
                self._blockEscapeFlag = None

            def eventFilter(self, source: 'QObject', event: 'QEvent') -> bool:
                if source.objectName() in {'_PULLDOWN'}:
                    if event.type() == QtCore.QEvent.KeyPress and event.key() in {QtCore.Qt.Key_Escape}:
                        QtCore.QTimer.singleShot(0, source.setFocus)
                        if source.view().isVisible():
                            source.hidePopup()
                            return True
                        if self._blockEscapeFlag:
                            self._blockEscapeFlag = None
                            return True
                    elif event.type() == QtCore.QEvent.KeyPress and event.key() in {QtCore.Qt.Key_Return,
                                                                                    QtCore.Qt.Key_Enter}:
                        if self._blockEscapeFlag:
                            self._blockEscapeFlag = None
                        else:
                            self._callback()
                elif source.objectName() in {'_PULLDOWNVIEW'}:
                    if event.type() in {QtCore.QEvent.Hide}:
                        # temporary block to enter-key closing the whole speech-balloon
                        self._blockEscapeFlag = True
                        QtCore.QTimer.singleShot(0, self._resetPulldown)
                    elif event.type() == QtCore.QEvent.KeyPress and event.key() in {QtCore.Qt.Key_Escape}:
                        return True
                return super().eventFilter(source, event)


        _project = getProject()
        # get the collection names from the project
        colData = _project.collections
        colNames = OrderedSet(['', ] + [co.name for co in colData])

        # create a small editor
        editPopup = EditCollection(parent=None, newPulldown=self._newPulldown,
                                   selectionWidget=selectionWidget,
                                   on_top=True)
        editPopup.setPulldownData(list(colNames))
        editPopup.setPulldownCallback(partial(self._createNewCollection, items=objs))
        editPopup.setDefaultName(Collection._uniqueName(_project))
        editPopup._filterCollections(objs)

        # get the desired position of the popup
        pos = QtGui.QCursor().pos()
        _size = editPopup.centralWidgetSize / 2
        popupPos = pos - QtCore.QPoint(_size.width(), _size.height())

        # show the editPopup near the mouse position
        editPopup.showAt(popupPos)
        # set the focus to the pulldown-list
        editPopup._pulldownWidget.setFocus()


from ccpn.ui.gui.widgets.SpeechBalloon import SpeechBalloon, Side
from ccpn.ui.gui.widgets.Frame import Frame
from ccpn.ui.gui.widgets.Label import Label


class AddToCollectionPopup(SpeechBalloon):
    """Balloon to hold the collection list
    For later when a more complex selector is required
    """

    def __init__(self, mainWindow=None, project=None, *args, **kwds):
        super().__init__(*args, **kwds)

        # simplest way to make the popup function as modal and disappear as required
        self.setWindowFlags(int(self.windowFlags()) | QtCore.Qt.Popup)
        self._mainWindow = mainWindow
        self._project = project

        # hide the speech pointer
        self._metrics.pointer_height = 0
        self._metrics.pointer_width = 0
        self._metrics.corner_radius = 2

        # add a small widget to the centre
        fr = Frame(self, setLayout=True)
        Label(fr, text='Test collection popup', grid=(0, 0))
        self.setCentralWidget(fr)


class _openItemChemicalShiftListTable(OpenItemABC):
    openItemMethod = 'showChemicalShiftTable'
    objectArgumentName = 'chemicalShiftList'

    def _openContextMenu(self, parentWidget, position, thisObj, objs, deferExec=False):
        """Open a context menu.
        """
        contextMenu = Menu('', parentWidget, isFloatWidget=True)
        if self.openAction:
            contextMenu.addAction(self.contextMenuText, self.openAction)
        contextMenu.addSeparator()
        contextMenu.addAction('Create Synthetic PeakList', partial(self._openCreateSyntheticPeakListFromCSLPopup, objs))
        contextMenu.addSeparator()
        contextMenu.addAction('Copy Pid to Clipboard', partial(self._copyPidsToClipboard, objs))
        self._addCollectionMenu(contextMenu, objs)
        contextMenu.addAction('Duplicate', partial(self._duplicateAction, objs))
        contextMenu.addAction('Delete', partial(self._deleteItemObject, thisObj, objs))

        contextMenu.addSeparator()
        contextMenu.addAction('Edit Properties', partial(parentWidget._raiseObjectProperties, self.node.widget))

        contextMenu.move(position)
        contextMenu.exec()

    @staticmethod
    def _duplicateAction(objs):
        for obj in objs:
            obj.duplicate()

    @staticmethod
    def _openCreateSyntheticPeakListFromCSLPopup(objs):
        if len(objs) > 1:
            showWarning('Create Synthetic PeakList from ChemicalShift', 'Please select only one ChemicalShift list')
            # Might think of merging multiple lists ?
            return
        if len(objs) > 0:
            from ccpn.ui.gui.popups.ChemicalShiftList2PeakListPopup import ChemicalShiftList2SpectrumPopup

            popup = ChemicalShiftList2SpectrumPopup(chemicalShiftList=objs[0])
            popup.show()
            popup.raise_()

    @staticmethod
    def _collectSpectra(objs):
        # check the spectra of chemical-shift-lists
        specs = {sp for obj in objs if isinstance(obj, ChemicalShiftList)
                 for sp in obj.spectra
                 }

        return specs

    def _deleteItemObject(self, thisObj, objs):
        if self._collectSpectra(objs):
            count = Counter(map(type, objs))
            plural = 's' if count[type(thisObj)] > 1 else ''
            msg = f'It is not possible to delete {self.objectClassName}s with associated Spectra,\n' \
                  f'please move the Spectra to alternative {self.objectClassName}s before deleting.'
            if len(count) > 1:
                msg += '\n\nPlease note that you have selected other objects that will also be deleted.\n'
                title = 'Delete...'
            else:
                title = f'Delete {self.objectClassName}{plural}'
            showWarning(title, msg)

        else:
            super()._deleteItemObject(thisObj, objs)


class _openItemPeakListTable(OpenItemABC):
    openItemMethod = 'showPeakTable'
    objectArgumentName = 'peakList'


class _openItemIntegralListTable(OpenItemABC):
    openItemMethod = 'showIntegralTable'
    objectArgumentName = 'integralList'


class _openItemMultipletListTable(OpenItemABC):
    openItemMethod = 'showMultipletTable'
    objectArgumentName = 'multipletList'


class _openItemNmrClass(OpenItemABC):

    @staticmethod
    def _collectShifts(objs):
        # check all the mmrAtoms of the selected nmrChain/nmrResidues/nmrAtoms
        shs = {sh for obj in objs if isinstance(obj, NmrAtom)
               for sh in obj.chemicalShifts
               }
        shs |= {sh for obj in objs if isinstance(obj, NmrResidue)
                for nmrRes in (obj,) + obj.offsetNmrResidues
                for nmrAt in nmrRes.nmrAtoms
                for sh in nmrAt.chemicalShifts
                }
        shs |= {sh for obj in objs if isinstance(obj, NmrChain)
                for res in obj.nmrResidues
                for nmrRes in (res,) + res.offsetNmrResidues
                for nmrAt in nmrRes.nmrAtoms
                for sh in nmrAt.chemicalShifts
                }

        return shs

    def _deleteItemObject(self, thisObj, objs):
        if self._collectShifts(objs):
            count = Counter(map(type, objs))
            plural = 's' if count[type(thisObj)] > 1 else ''
            notPlural = '' if count[type(thisObj)] > 1 else 's'
            msg = f'The selected {self.objectClassName}{plural} contain{notPlural} assignments.\n' \
                  f'Deleting {self.objectClassName}s will delete their chemicalShifts and deassign any associated peaks.\n' \
                  'Do you want to continue?'
            if len(count) > 1:
                msg += '\n\nPlease note that you have selected other objects that will also be deleted.\n'
                title = 'Delete...'
            else:
                title = f'Delete {self.objectClassName}{plural}'
            ok = showYesNoWarning(title, msg, dontShowEnabled=True, defaultResponse=True,
                                  popupId=self.__class__.__name__)

            if not ok:
                return

        super()._deleteItemObject(thisObj, objs)


class _openItemNmrChainTable(_openItemNmrClass):
    openItemMethod = 'showNmrResidueTable'
    objectArgumentName = 'nmrChain'


class _openItemNmrResidueItem(_openItemNmrClass):
    objectArgumentName = 'nmrResidue'
    hasOpenMethod = False

    def _openContextMenu(self, parentWidget, position, thisObj, objs, deferExec=False):
        """Open a context menu.
        """
        moveToHeadIcon = Icon('icons/move-to-head')
        moveToTailIcon = Icon('icons/move-to-tail')

        nmrResidue = thisObj
        contextMenu = super()._openContextMenu(parentWidget, position, thisObj, objs, deferExec=True)

        # add new actions to move the nmrResidue to the head/tail
        actionToHead = contextMenu.addAction(moveToHeadIcon, 'Move NmrResidue to Front',
                                             partial(nmrResidue.mainNmrResidue.moveToEnd, MoveToEnd.HEAD))
        actionToTail = contextMenu.addAction(moveToTailIcon, 'Move NmrResidue to End',
                                             partial(nmrResidue.mainNmrResidue.moveToEnd, MoveToEnd.TAIL))

        if (_actions := contextMenu.actions()) and len(_actions) > 2:
            _topMenuItem = _actions[0]
            _topSeparator = contextMenu.insertSeparator(_topMenuItem)

            # move new actions to the top of the existing actions
            contextMenu.insertActions(_topMenuItem, [actionToHead, actionToTail, _topSeparator])

        actionToHead.setEnabled(False)
        actionToTail.setEnabled(False)
        if nmrResidue.nmrChain.isConnected:
            mainRess = nmrResidue.nmrChain.mainNmrResidues
            if len(mainRess) > 1 and nmrResidue.mainNmrResidue in mainRess:
                ind = mainRess.index(nmrResidue.mainNmrResidue)

                # enable if the first/last mainNmrResidue
                if ind == 0:
                    actionToTail.setEnabled(True)
                elif ind == len(mainRess) - 1:
                    actionToHead.setEnabled(True)

        contextMenu.move(position)
        contextMenu.exec_()


class _openItemNmrAtomItem(_openItemNmrClass):
    objectArgumentName = 'nmrAtom'
    hasOpenMethod = False


class _openItemAtomItem(OpenItemABC):
    objectArgumentName = 'Atom'
    hasOpenMethod = False

    def _openContextMenu(self, parentWidget, position, thisObj, objs, deferExec=False):
        """Open a context menu.
        """
        contextMenu = Menu('', parentWidget, isFloatWidget=True)
        if self.openAction:
            contextMenu.addAction(self.contextMenuText, self.openAction)
        contextMenu.addAction('Copy Pid to Clipboard', partial(self._copyPidsToClipboard, objs))
        self._addCollectionMenu(contextMenu, objs)

        contextMenu.addSeparator()
        contextMenu.addAction('Edit Properties', partial(parentWidget._raiseObjectProperties, self.node.widget))

        contextMenu.move(position)
        contextMenu.exec()


class _openItemChainTable(OpenItemABC):
    openItemMethod = 'showResidueTable'
    objectArgumentName = 'chain'

    def _openContextMenu(self, parentWidget, position, thisObj, objs, deferExec=False):
        """Open a context menu.
        """
        contextMenu = super()._openContextMenu(parentWidget, position, thisObj, objs, deferExec=True)
        newFromAction = contextMenu.addAction('New Chain from selected...', partial(self._newFromSelected, objs))
        contextMenu.moveActionBelowName(newFromAction, 'Clone')
        contextMenu.move(position)
        contextMenu.exec()

    def _cloneObject(self, objs):
        objs = [obj for obj in objs if isinstance(obj, Chain)]
        if len(objs) > 1:
            showWarning('New Chain from selected', 'Creating a from is available for only a single selection')
            return
        if len(objs) == 1:
            obj = objs[0]
            chain = obj
            try:
                chain.clone()
            except Exception as error:
                showWarning('Clone Chain Failed', f'{error}')

    def _newFromSelected(self, objs):
        """Open a new popup prefilled from the current object"""
        objs = [obj for obj in objs if isinstance(obj, Chain)]
        if len(objs) > 1:
            showWarning('New Chain from selected', 'Creating a from is available for only a single selection')
            return
        if len(objs) == 1:
            obj = objs[0]
            popup = CreateChainPopup(mainWindow=self.mainWindow)
            popup.setWindowTitle(f'New Chain from {obj.pid}')
            # popup.obj.compoundName = obj.compoundName #this could be set but needs to ensure a unique name
            popup.obj.comment = obj.comment
            popup.obj.startNumber = obj.startNumber
            popup.obj.sequenceCcpCodes = obj.sequenceCcpCodes
            popup.obj.isCyclic = obj.isCyclic
            popup.obj.molType = obj.chainType
            popup._populate()
            popup.exec()


class _openItemResidueTable(OpenItemABC):
    objectArgumentName = 'residue'
    hasOpenMethod = False

    def _openContextMenu(self, parentWidget, position, thisObj, objs, deferExec=False):
        """Open a context menu.
        """
        contextMenu = Menu('', parentWidget, isFloatWidget=True)
        if self.openAction:
            contextMenu.addAction(self.contextMenuText, self.openAction)
        contextMenu.addAction('Copy Pid to Clipboard', partial(self._copyPidsToClipboard, objs))
        self._addCollectionMenu(contextMenu, objs)

        contextMenu.addSeparator()
        contextMenu.addAction('Edit Properties', partial(parentWidget._raiseObjectProperties, self.node.widget))

        contextMenu.move(position)
        contextMenu.exec()


class _openItemNoteTable(OpenItemABC):
    openItemMethod = 'showNotesEditor'
    objectArgumentName = 'note'


class _openItemRestraintTable(OpenItemABC):
    openItemMethod = 'showRestraintTable'
    objectArgumentName = 'restraintTable'


class _openItemStructureDataTable(OpenItemABC):
    objectArgumentName = 'structureData'
    hasOpenMethod = False


class _openItemComplexTable(OpenItemABC):
    objectArgumentName = 'complex'
    hasOpenMethod = False


class _openItemSubstanceTable(OpenItemABC):
    objectArgumentName = 'substance'
    hasOpenMethod = False


class _openItemSampleComponentTable(OpenItemABC):
    objectArgumentName = 'sampleComponent'
    hasOpenMethod = False


class _openItemSampleDisplay(OpenItemABC):
    openItemMethod = None
    useApplication = False
    objectArgumentName = 'sample'
    contextMenuText = 'Open linked spectra'

    @staticmethod
    def _openSampleSpectraOnDisplay(sample, spectrumDisplay, autoRange=False):
        # with undoBlockWithoutSideBar():
        with undoStackBlocking() as _:  # Do not add to undo/redo stack
            with notificationEchoBlocking():
                if len(sample.spectra) > 0 and len(spectrumDisplay.strips) > 0:
                    # spectrumDisplay.clearSpectra()
                    for sampleComponent in sample.sampleComponents:
                        if sampleComponent.substance is not None:
                            for spectrum in sampleComponent.substance.referenceSpectra:
                                spectrumDisplay.displaySpectrum(spectrum)
                    for spectrum in sample.spectra:
                        spectrumDisplay.displaySpectrum(spectrum)
                    if autoRange:
                        spectrumDisplay.autoRange()

    def _openSampleSpectra(self, sample, position=None, relativeTo=None):
        """Add spectra linked to sample and sampleComponent. Particularly used for screening
        """
        if len(sample.spectra) > 0:
            mainWindow = self.mainWindow

            spectrumDisplay = mainWindow.newSpectrumDisplay(sample.spectra[0])
            mainWindow.moduleArea.addModule(spectrumDisplay, position=position, relativeTo=relativeTo)
            self._openSampleSpectraOnDisplay(sample, spectrumDisplay, autoRange=True)
            mainWindow.application.current.strip = spectrumDisplay.strips[0]

    openItemDirectMethod = _openSampleSpectra


# def _setSpectrumDisplayNotifiers(spectrumDisplay, value):
#     """Blank all spectrumDisplay and contained strip notifiers
#     """
#     spectrumDisplay.setBlankingAllNotifiers(value)
#     for strip in spectrumDisplay.strips:
#         strip.setBlankingAllNotifiers(value)


class _openItemSpectrumDisplay(OpenItemABC):
    openItemMethod = None
    useApplication = False
    objectArgumentName = 'spectrum'

    def _openSpectrumDisplay(self, spectrum=None, position=None, relativeTo=None):
        mainWindow = self.mainWindow
        current = mainWindow.application.current

        # check whether a new spectrumDisplay is needed, and check axisOrdering
        from ccpn.ui.gui.popups.AxisOrderingPopup import checkSpectraToOpen

        checkSpectraToOpen(mainWindow, [spectrum])

        spectrumDisplay = mainWindow.newSpectrumDisplay(spectrum, position=position, relativeTo=relativeTo)
        if spectrumDisplay and len(spectrumDisplay.strips) > 0:
            current.strip = spectrumDisplay.strips[0]

        return spectrumDisplay

    openItemDirectMethod = _openSpectrumDisplay


class _openItemSpectrumGroupDisplay(OpenItemABC):
    openItemMethod = None
    useApplication = False
    objectArgumentName = 'spectrumGroup'

    def _openSpectrumGroup(self, spectrumGroup, position=None, relativeTo=None):
        """Displays spectrumGroup on spectrumDisplay. It creates the display based on the first spectrum of the group.
        Also hides the spectrumToolBar and shows spectrumGroupToolBar.
        """
        mainWindow = self.mainWindow

        if len(spectrumGroup.spectra) > 0:

            # check whether a new spectrumDisplay is needed, and check axisOrdering
            from ccpn.ui.gui.popups.AxisOrderingPopup import checkSpectraToOpen

            checkSpectraToOpen(mainWindow, [spectrumGroup])

            current = mainWindow.application.current
            # with undoBlockWithoutSideBar():
            with undoStackBlocking() as _:  # Do not add to undo/redo stack
                with notificationEchoBlocking():

                    spectrumDisplay = mainWindow.newSpectrumDisplay(spectrumGroup, position=position,
                                                                    relativeTo=relativeTo)

                    # set the spectrumView colours
                    # spectrumDisplay._colourChanged(spectrumGroup)
                    if len(spectrumDisplay.strips) > 0:

                        # with undoBlockWithoutSideBar():
                        #     with notificationEchoBlocking():
                        for spectrum in spectrumGroup.spectra[1:]:  # Add the other spectra
                            spectrumDisplay.displaySpectrum(spectrum)

                        current.strip = spectrumDisplay.strips[0]
                    # if any([sp.dimensionCount for sp in spectrumGroup.spectra]) == 1:
                    spectrumDisplay.autoRange()
            return spectrumDisplay

    openItemDirectMethod = _openSpectrumGroup


class _openItemSpectrumInGroupDisplay(_openItemSpectrumDisplay):
    """Modified class for spectra that are in sideBar under a spectrumGroup
    """

    def _openContextMenu(self, parentWidget, position, thisObj, objs, deferExec=False):
        """Open a context menu.
        """
        contextMenu = Menu('', parentWidget, isFloatWidget=True)
        if self.openAction:
            contextMenu.addAction(self.contextMenuText, self.openAction)

        if spectra := [obj for obj in objs if isinstance(obj, Spectrum)]:
            contextMenu.addAction('Make SpectrumGroup From Selected',
                                  partial(_raiseSpectrumGroupEditorPopup(useNone=True, editMode=False,
                                                                         defaultItems=spectra),
                                          self.mainWindow, self.getObj(), self.node))

            contextMenu.addAction('Remove from SpectrumGroup', partial(self._removeSpectrumObject, objs))
            self._addCollectionMenu(contextMenu, objs)
            contextMenu.addSeparator()

        contextMenu.addAction('Delete', partial(self._deleteItemObject, thisObj, objs))
        canBeCloned = all(hasattr(obj, 'clone') for obj in objs)
        if canBeCloned:
            contextMenu.addAction('Clone', partial(self._cloneObject, objs))

        contextMenu.addSeparator()
        contextMenu.addAction('Edit Properties', partial(parentWidget._raiseObjectProperties, self.node.widget))

        contextMenu.move(position)
        contextMenu.exec()

    def _removeSpectrumObject(self, objs):
        """Remove spectrum from spectrumGroup.
        """
        if not isinstance(objs, list):
            return

        try:
            # get parent spectrumGroup from current node
            specGroup = self.node._parent.obj
            spectra = list(specGroup.spectra)

            with undoBlockWithoutSideBar():
                for obj in objs:
                    if obj in spectra:
                        spectra.remove(obj)
                specGroup.spectra = tuple(spectra)

        except Exception as es:
            showWarning('Remove object from spectra', str(es))


class _openItemStructureEnsembleTable(OpenItemABC):
    openItemMethod = 'showStructureTable'
    objectArgumentName = 'structureEnsemble'


class _openItemDataTable(OpenItemABC):
    openItemMethod = 'showDataTable'
    objectArgumentName = 'dataTable'


class _openItemViolationTable(OpenItemABC):
    openItemMethod = 'showViolationTable'
    objectArgumentName = 'violationTable'


class _openItemCollectionModule(OpenItemABC):
    openItemMethod = 'showCollectionModule'
    objectArgumentName = 'collection'

    def _openContextMenu(self, parentWidget, position, thisObj, objs, deferExec=False):
        """Open a context menu for the Collection item in the sideBar.
        """
        contextMenu = super()._openContextMenu(parentWidget, position, thisObj, objs, deferExec=True)

        # disable the contextMenuText action
        if (actions := [act for act in contextMenu.actions() if act.text() == self.contextMenuText]):
            actions[0].setEnabled(False)

        # find the 'remove' action
        removeAction = actions[0] if (
            actions := [act for act in contextMenu.actions() if act.text() == _REMOVE_FROM_COLLECTION]) else None

        # create subMenu for listing items in the collection - temporary until a module can be designed
        itms = self.getObj().items
        if itms and removeAction:
            subMenu = contextMenu.addMenu(_ITEMS_COLLECTION)

            # find the inserted 'items' action
            if (subMenuAction := actions[0] if (actions := [act for act in contextMenu.actions()
                                                            if act.text() == _ITEMS_COLLECTION]) else None):
                # add the items to the menu as disabled
                for itm in itms:
                    _action = subMenu.addAction(itm.pid)
                    _action.setEnabled(False)

                # insert above and then swap - required to insert below an action
                contextMenu.insertAction(removeAction, subMenuAction)
                contextMenu.insertAction(subMenuAction, removeAction)

        # exec the menu
        contextMenu.exec()


OpenObjAction = {
    Spectrum         : _openItemSpectrumDisplay,
    PeakList         : _openItemPeakListTable,
    MultipletList    : _openItemMultipletListTable,
    NmrChain         : _openItemNmrChainTable,
    Chain            : _openItemChainTable,
    SpectrumGroup    : _openItemSpectrumGroupDisplay,
    Sample           : _openItemSampleDisplay,
    ChemicalShiftList: _openItemChemicalShiftListTable,
    RestraintTable   : _openItemRestraintTable,
    Note             : _openItemNoteTable,
    IntegralList     : _openItemIntegralListTable,
    StructureEnsemble: _openItemStructureEnsembleTable,
    DataTable        : _openItemDataTable,
    ViolationTable   : _openItemViolationTable,
    Collection       : _openItemCollectionModule,
    }


def _openItemObject(mainWindow, objs, **kwds):
    if len(objs) > 0:
        with undoBlockWithoutSideBar():

            # if 5 or more, then don't log, otherwise log may be overloaded
            if len(objs) > MAXITEMLOGGING:
                getLogger().info('Opening items...')
                with notificationEchoBlocking():
                    _openItemObjects(mainWindow, objs, **kwds)
            else:
                _openItemObjects(mainWindow, objs, **kwds)


def _openItemObjects(mainWindow, objs, **kwds):
    """
    Abstract routine to activate a module to display objs
    Builds on OpenObjAction dict, defined above, which defines the handling for the various
    obj classes
    """
    spectrumDisplay = None
    with undoBlockWithoutSideBar():
        for obj in objs:
            if obj:

                if obj.__class__ in OpenObjAction:

                    # if a spectrum object has already been opened then attach to that spectrumDisplay
                    if isinstance(obj, Spectrum) and spectrumDisplay:
                        try:
                            spectrumDisplay.displaySpectrum(obj)

                        except RuntimeError:
                            # process objects to open
                            func = OpenObjAction[obj.__class__](useNone=True, **kwds)
                            func._execOpenItem(mainWindow, obj)

                    elif isinstance(obj, SpectrumGroup) and spectrumDisplay:
                        try:
                            spectrumDisplay._handleSpectrumGroup(obj)

                        except RuntimeError:
                            # process objects to open
                            func = OpenObjAction[obj.__class__](useNone=True, **kwds)
                            func._execOpenItem(mainWindow, obj)

                    else:
                        # process objects to open
                        func = OpenObjAction[obj.__class__](useNone=True, **kwds)
                        returnObj = func._execOpenItem(mainWindow, obj)

                        # if the first spectrum then set the spectrumDisplay
                        if isinstance(obj, (Spectrum, SpectrumGroup)):
                            spectrumDisplay = returnObj

                else:
                    showInfo('Not implemented yet!',
                             'This function has not been implemented in the current version')
