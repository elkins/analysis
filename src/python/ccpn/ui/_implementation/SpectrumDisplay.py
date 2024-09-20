"""GUI SpectrumDisplay class

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
__dateModified__ = "$dateModified: 2024-03-21 16:17:11 +0000 (Thu, March 21, 2024) $"
__version__ = "$Revision: 3.2.4 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from typing import Sequence, Tuple, Optional

from ccpnmodel.ccpncore.api.ccp.nmr.Nmr import ResonanceGroup as ApiResonanceGroup
from ccpnmodel.ccpncore.api.ccpnmr.gui.Window import Window as ApiWindow
from ccpnmodel.ccpncore.api.ccpnmr.gui.Task import BoundDisplay as ApiBoundDisplay

from ccpn.core.NmrResidue import NmrResidue
from ccpn.core.Project import Project
from ccpn.core.Spectrum import Spectrum

from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.ui._implementation.Window import Window

import ccpn.core.lib.SpectrumLib as specLib
from ccpn.core.lib import Pid

from ccpn.util import Common as commonUtil
from ccpn.core.lib.ContextManagers import newObject, undoStackBlocking, renameObject
from ccpn.util.Logging import getLogger

from ccpn.core._implementation.updates.update_3_0_4 import _updateSpectumDisplay_3_0_4_to_3_1_0
from ccpn.core._implementation.Updater import updateObject, UPDATE_POST_OBJECT_INITIALISATION


@updateObject(fromVersion='3.0.4',
              toVersion='3.1.0',
              updateFunction=_updateSpectumDisplay_3_0_4_to_3_1_0,
              updateMethod=UPDATE_POST_OBJECT_INITIALISATION)
class SpectrumDisplay(AbstractWrapperObject):
    """Spectrum display for 1D or nD spectrum"""

    #: Short class name, for PID.
    shortClassName = 'GD'
    # Attribute it necessary as subclasses must use superclass className
    className = 'SpectrumDisplay'

    _parentClass = Window
    _parentClassName = Window.__class__.__name__

    #: Name of plural link to instances of class
    _pluralLinkName = 'spectrumDisplays'
    #: List of child classes.
    _childClasses = []

    _isGuiClass = True

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiBoundDisplay._metaclass.qualifiedName()

    # Internal namespace
    _ISOTOPECODES_KEY = '_isotopeCodes'
    _DIMENSIONTYPES_KEY = '_dimensionTypes'

    INTENSITY = 'intensity'  # used for 1D intensity (Y) axis

    #-----------------------------------------------------------------------------------------
    # Attributes of the data structure (incomplete?)
    #-----------------------------------------------------------------------------------------

    @property
    def orderedStrips(self):
        """Return the ccpn.Strips in displayed order"""
        ff = self._project._data2Obj.get
        return tuple(ff(x) for x in self._wrappedData.orderedStrips)

    #-----------------------------------------------------------------------------------------
    # property STUBS: hot-fixed later
    #-----------------------------------------------------------------------------------------

    @property
    def axes(self) -> list['Axis']:
        """STUB: hot-fixed later
        :return: a list of axes in the SpectrumDisplay
        """
        return []

    @property
    def integralListViews(self) -> list['IntegralListView']:
        """STUB: hot-fixed later
        :return: a list of integralListViews in the SpectrumDisplay
        """
        return []

    @property
    def integralViews(self) -> list['IntegralView']:
        """STUB: hot-fixed later
        :return: a list of integralViews in the SpectrumDisplay
        """
        return []

    @property
    def multipletListViews(self) -> list['MultipletListView']:
        """STUB: hot-fixed later
        :return: a list of multipletListViews in the SpectrumDisplay
        """
        return []

    @property
    def multipletViews(self) -> list['MultipletView']:
        """STUB: hot-fixed later
        :return: a list of multipletViews in the SpectrumDisplay
        """
        return []

    @property
    def peakListViews(self) -> list['PeakListView']:
        """STUB: hot-fixed later
        :return: a list of peakListViews in the SpectrumDisplay
        """
        return []

    @property
    def peakViews(self) -> list['PeakView']:
        """STUB: hot-fixed later
        :return: a list of peakViews in the SpectrumDisplay
        """
        return []

    @property
    def spectrumViews(self) -> list['SpectrumView']:
        """STUB: hot-fixed later
        :return: a list of spectrumViews in the SpectrumDisplay
        """
        return []

    @property
    def strips(self) -> list['Strip']:
        """STUB: hot-fixed later
        :return: a list of strips in the SpectrumDisplay
        """
        return []

    #-----------------------------------------------------------------------------------------
    # getter STUBS: hot-fixed later
    #-----------------------------------------------------------------------------------------

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

    #-----------------------------------------------------------------------------------------

    def __init__(self, project: Project, wrappedData):

        AbstractWrapperObject.__init__(self, project, wrappedData)
        self._isNew = False  # Only set by newSpectrumDisplay

    # @classmethod
    # def _restoreObject(cls, project, apiObj):
    #     """Subclassed to allow for initialisations on restore
    #     """
    #     result = super()._restoreObject(project, apiObj)
    #
    #     # debug
    #     _strips = result.strips
    #
    #     # getting value will induce an update in the internal parameters
    #     _tmp = result.isotopeCodes
    #     _tmp2 = result.dimensionTypes
    #
    #     # update the plane axes settings
    #     for strip in _strips:
    #         strip._updatePlaneAxes()
    #
    #     if not result.is1D:
    #         result.setVisibleAxes()
    #
    #     # check that the spectrumView indexing has been set, or is populated correctly
    #     if len(_strips) > 0 and \
    #        (specViews := _strips[0].getSpectrumViews()):
    #         indexing = [v._index for v in specViews]
    #         if None in indexing or len(indexing) != len(set(indexing)):
    #             # set new indexing
    #             for ind, sv in enumerate(specViews):
    #                 sv._index = ind
    #         result._spectrumViewVisibleChanged()
    #
    #     return result

    def _postRestore(self):
        """Handle post-initialising children after all children have been restored
        """
        # debug
        _strips = self.strips

        # getting value will spawn an update of the internal parameters
        _tmp = self.isotopeCodes
        _tmp2 = self.dimensionTypes

        # update the plane axes settings
        for strip in _strips:
            strip._updatePlaneAxes()

        if not self.is1D:
            self.setVisibleAxes()

        # check that the spectrumView indexing has been set, or is populated correctly
        if len(_strips) > 0 and \
                (specViews := _strips[0].getSpectrumViews()):
            indexing = [v._index for v in specViews]
            if None in indexing or len(indexing) != len(set(indexing)):
                # set new indexing
                for ind, sv in enumerate(specViews):
                    sv._index = ind
            self._spectrumViewVisibleChanged()

        super()._postRestore()

    #-----------------------------------------------------------------------------------------
    # CCPN properties
    #-----------------------------------------------------------------------------------------

    @property
    def _apiSpectrumDisplay(self) -> ApiBoundDisplay:
        """ CCPN SpectrumDisplay matching SpectrumDisplay"""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """short form of name, corrected to use for id"""
        return self._wrappedData.name.translate(Pid.remapSeparators)

    @property
    def title(self) -> str:
        """SpectrumDisplay.title
        (corresponds to its name, but the name 'name' is taken by PyQt)
        """
        return self._wrappedData.name

    @property
    def _parent(self) -> Project:
        """Project containing spectrumDisplay."""
        return self._project

    project = _parent

    # @property
    # def stripDirection(self) -> str:
    #     """Strip axis direction ('X', 'Y', None) - None only for non-strip plots"""
    #     getLogger().warning('StripDirection is deprecated. Used stripArrangement instead')
    #     return self.stripArrangement
    #
    #     # return self._wrappedData.stripDirection
    #
    # @stripDirection.setter
    # def stripDirection(self, value:str='Y'):
    #     """Set the new strip direction ('X', 'Y', None) - None only for non-strip plots
    #     """
    #     self.stripArrangement(value)
    #     getLogger().warning('StripDirection is deprecated. Used stripArrangement instead')
    #     # raise RuntimeError('deprecated: use stripArrangement') no need of raising an error!
    #
    #     # if not isinstance(value, str):
    #     #     raise TypeError('stripDirection must be a string')
    #     # elif value not in ['X', 'Y']:
    #     #     raise ValueError("stripDirection must be either 'X' or 'Y'")
    #     #
    #     # # override 'frozen' set
    #     # self._wrappedData.__dict__['stripDirection'] = value

    @property
    def stripCount(self) -> int:
        """Number of strips in the spectrumDisplay"""
        return self._wrappedData.stripCount

    @property
    def axisCodes(self) -> Tuple[str, ...]:
        """Fixed string Axis codes in display order (X, Y, Z1, Z2, ...)"""
        return tuple(self._wrappedData.axisCodes)

    @property
    def axisOrder(self) -> Tuple[str, ...]:
        """String Axis codes in display order (X, Y, Z1, Z2, ...), determine axis display order"""
        return tuple(self._wrappedData.axisOrder)

    @axisOrder.setter
    def axisOrder(self, value: Sequence):
        self._wrappedData.axisOrder = value

    @property
    def isotopeCodes(self) -> Tuple[str, ...]:
        """Fixed string isotope codes in display order (X, Y, Z1, Z2, ...)
        Defined by first spectrum used for initialisation
        """
        return self._isotopeCodes

    @property
    def _isotopeCodes(self) -> Tuple[str, ...]:
        """Fixed string isotope codes in display order (X, Y, Z1, Z2, ...)
        CCPN Internal
        """
        if (result := self._getInternalParameter(self._ISOTOPECODES_KEY)) is None:
            # Try to reconstruct from any possible spectrum
            result = [None] * self.dimensionCount
            for sv in self.spectrumViews:
                if sv.dimensionCount == self.dimensionCount:
                    result = sv.isotopeCodes
                    self._isotopeCodes = result
                    break
        return tuple(result)

    @_isotopeCodes.setter
    def _isotopeCodes(self, value):
        self._setInternalParameter(self._ISOTOPECODES_KEY, value)

    @property
    def dimensionCount(self) -> int:
        """Dimensionality of the SpectrumDisplay"""
        return 1 if self.is1D else len(self.axisCodes)

    @property
    def is1D(self) -> bool:
        """True if this is a 1D display."""
        tt = self.axisCodes
        return bool(tt and (tt[1] == self.INTENSITY or tt[0] == self.INTENSITY))

    @property
    def dimensionTypes(self):
        """dimension types ('Time' / 'Frequency' / 'Sampled') in display order;
        Values defined by the first spectrum used to initialise the SpectrumDisplay
        """
        return self._dimensionTypes

    @property
    def _dimensionTypes(self) -> Tuple[Optional[str], ...]:
        """local variable to hold dimension types ('Time' / 'Frequency' / 'Sampled')
        in display order;
        Values defined by the first spectrum used to initialise the SpectrumDisplay
        """
        if (result := self._getInternalParameter(self._DIMENSIONTYPES_KEY)) is None:
            # Try to reconstruct from any possible spectrum
            result = [None] * self.dimensionCount
            for sv in self.spectrumViews:
                if sv.dimensionCount == self.dimensionCount:
                    result = sv.dimensionTypes
                    self._dimensionTypes = result
                    break
        return tuple(result)

    @_dimensionTypes.setter
    def _dimensionTypes(self, value):
        if not commonUtil.isIterable(value):
            raise ValueError('Expected list/tuple for _dimensionTypes; got %r' % value)
        value = list(value)
        if self.is1D and len(value) != 1:
            raise ValueError('Expected list/tuple with length %d for _dimensionTypes; got %r' %
                             (1, value))
        elif not self.is1D and len(value) != self.dimensionCount:
            raise ValueError('Expected list/tuple with length %d for _dimensionTypes; got %r' %
                             (self.dimensionCount, value))
        for idx, val in enumerate(value):
            allowedTypes = specLib.DIMENSIONTYPES + [None]
            if val not in allowedTypes:
                raise ValueError('dimensionType[%d] should be one of %r' %
                                 (idx, allowedTypes))
        self._setInternalParameter(self._DIMENSIONTYPES_KEY, value)

    # @property
    # def window(self) -> Window:
    #     """Gui window showing SpectrumDisplay"""
    #     # This should be renamed, but that also requires refactoring
    #     # possibly with a model change that modifies the Task/Window/Module relationship
    #     return self._project._data2Obj.get(self._wrappedData.window)
    #
    # @window.setter
    # def window(self, value: Window):
    #     value = self.getByPid(value) if isinstance(value, str) else value
    #     self._wrappedData.window = value and value._wrappedData

    @property
    def nmrResidue(self) -> NmrResidue:
        """NmrResidue attached to SpectrumDisplay"""
        return self._project._data2Obj.get(self._wrappedData.resonanceGroup)

    @nmrResidue.setter
    def nmrResidue(self, value: NmrResidue):
        value = self.getByPid(value) if isinstance(value, str) else value
        self._wrappedData.resonanceGroup = value and value._wrappedData

    # @property
    # def positions(self) -> Tuple[float, ...]:
    #     """Axis centre positions, in display order"""
    #     return self._wrappedData.positions
    #
    # @positions.setter
    # def positions(self, value):
    #     self._wrappedData.positions = value
    #
    # @property
    # def widths(self) -> Tuple[float, ...]:
    #     """Axis display widths, in display order"""
    #     return self._wrappedData.widths
    #
    # @widths.setter
    # def widths(self, value):
    #     self._wrappedData.widths = value

    @property
    def units(self) -> Tuple[str, ...]:
        """Axis units, in display order"""
        return self.strips[0].units

    # @units.setter
    # def units(self, value):
    #     # local import to avoid cycles
    #     from ccpn.util.Constants import AXISUNITS, AXISUNIT_NUMBER
    #
    #     options = list(AXISUNITS) + [AXISUNIT_NUMBER]  # To allow for 1D intensity axis unit
    #     for idx, val in enumerate(value):
    #         if val not in options:
    #             raise ValueError('Invalid units[%d] %r; should be one of %r' % (idx, val, options))
    #         self.orderedAxes[idx].unit = val
    #     # assure the update of the widgets is done
    #     self._updateSettingsAxesUnits()
    #     # self._wrappedData.units = value

    @property
    def _unitIndices(self) -> Tuple[str, ...]:
        """Axis unit indicess, in display order"""
        return self.strips[0]._unitIndices

    # def _getUnitsIndices(self):
    #     """Conveniance function to get units as an index
    #     CCPNINTERNAL: used CcpnOpenGl.initialiseAxes()
    #     """
    #     from ccpn.util.Constants import AXISUNITS, AXISUNIT_NUMBER
    #
    #     options = list(AXISUNITS) + [AXISUNIT_NUMBER]  # To allow for 1D intensity axis unit
    #     return [options.index(unit) for unit in self.units]

    def _getSpectra(self):
        if len(self.strips) > 0:  # strips
            return self.strips[0].getSpectra()

    @renameObject()
    def rename(self, name):
        """
        Rename the Spectrum Display core object.
        Note to rename the GuiModule GuiSpectrumDisplay object use the method "renameModule".
        Renaming from the GuiSpectrumDisplay ensures all graphical objects are updated correctly.
        """
        oldName = self.title
        # self._oldPid = self.pid

        if name != self.id and self._project.getSpectrumDisplay(name):
            getLogger().warning('Cannot rename spectrum Display', 'Name Already Taken')
            return (oldName,)

        try:
            self._validateStringValue('name', name)
            del self.project._pid2Obj[self.shortClassName][self._id]
            apiDisplay = self._wrappedData
            apiTask = apiDisplay.parent
            apiModules = apiTask.__dict__.get('modules')
            apiModules[name] = apiModules.pop(self._id)
            apiDisplay.__dict__['name'] = name
            self._id = name
            return (oldName,)

        except Exception as err:
            getLogger().warning('Cannot rename spectrum Display', err)
            getLogger().exception(str(err))

        return (oldName,)

    def _rescaleSpectra(self):
        """Reorder the buttons and spawn a redraw event
        """
        self.spectrumToolBar.reorderButtons(self.strips[0].getSpectrumViews())

        # spawn the required event to reordered the spectrumViews in openGL
        from ccpn.ui.gui.lib.OpenGL.CcpnOpenGL import GLNotifier

        GLSignals = GLNotifier(parent=None)
        GLSignals._emitAxisUnitsChanged(source=None, strip=self.strips[0], dataDict={})

    def moveSpectrumByIndex(self, startInd, endInd):
        """Move spectrum in spectrumDisplay list from index startInd to endInd
        startInd/endInd are the order as seen in the spectrumToolbar
        """
        if not self.strips:
            getLogger().warning(f'SpectrumDisplay {self} does not contain strips')
            return

        specViews = self.strips[0].getSpectrumViews()
        if not (0 <= startInd < len(specViews) and 0 <= endInd < len(specViews)):
            raise ValueError('startInd/endInd out of range')
        if startInd == endInd:
            getLogger().warning('SpectrumDisplay.moveSpectrumByIndex: startInd = endInd')
            return

        with undoStackBlocking():  # Do not add to undo/redo stack
            # rebuild the display when the ordering has changed
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=self._rescaleSpectra)

            orderedSV = list(self.strips[0].getSpectrumViews())
            last = orderedSV.pop(startInd)
            orderedSV.insert(endInd, last)
            self.strips[0]._setSpectrumViews(orderedSV)

            # rebuild the displays
            self._rescaleSpectra()

            # rebuild the display when the ordering has changed
            with undoStackBlocking() as addUndoItem:
                addUndoItem(redo=self._rescaleSpectra)

    def _setOrderedSpectrumViewsIndex(self, spectrumIndex: Tuple[int]):
        """
        Set the new indexing of the spectrumViews attached to the strip/spectrumDisplay
        :param spectrumIndex - tuple of integers
        """
        if not all(isinstance(val, int) and val >= 0 for val in spectrumIndex):
            raise ValueError("spectrum indexing values must be non-negative Int")
        if len(spectrumIndex) != len(set(spectrumIndex)) or max(spectrumIndex) != len(spectrumIndex) - 1:
            raise ValueError("spectrum indexing values badly defined")
        if not self.strips:
            getLogger().warning(f'SpectrumDisplay {self} does not contain strips')
            return

        with undoStackBlocking():  # Do not add to undo/redo stack
            # rebuild the display when the ordering has changed
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=self._rescaleSpectra)  # keep for the minute, may need for gui undo/redo

            specViews = self.strips[0].getSpectrumViews()
            specViews = [specViews[ii] for ii in spectrumIndex]
            self.strips[0]._setSpectrumViews(specViews)

            self._rescaleSpectra()

            # rebuild the display when the ordering has changed
            with undoStackBlocking() as addUndoItem:
                addUndoItem(redo=self._rescaleSpectra)

    def findAxis(self, axisCode):
        """Find axis """
        return self._project._data2Obj.get(self._wrappedData.findAxis(axisCode))

    # def appendSpectrumView(self, spectrumView):
    #   """
    #   Append a SpectrumView to the end of the ordered spectrumviews
    #   :param spectrumView - new SpectrumView:
    #   """
    #   if not self._orderedSpectrumViews:
    #     self._orderedSpectrumViews = OrderedSpectrumViews(parent=self)
    #   self._orderedSpectrumViews.appendSpectrumView(spectrumView)
    #
    # def removeSpectrumView(self, spectrumView):
    #   """
    #   Remove a SpectrumView from the ordered spectrumviews
    #   :param spectrumView - SpectrumView to be removed:
    #   """
    #   if not self._orderedSpectrumViews:
    #     self._orderedSpectrumViews = OrderedSpectrumViews(parent=self)
    #   self._orderedSpectrumViews.removeSpectrumView(spectrumView)

    # GWV 07/01/2022: moved up
    # @property
    # def orderedStrips(self):
    #     """Return the ccpn.Strips in displayed order"""
    #     ff = self._project._data2Obj.get
    #     return tuple(ff(x) for x in self._wrappedData.orderedStrips)

    @property
    def marks(self) -> tuple:
        """Return the associated marks for the spectrumDisplay.
        These are marks that are common to all strips in a given spectrumDisplay.
        """
        try:
            refHandler = self._project._crossReferencing
            return refHandler.getValues(self, '_MarkSpectrumDisplay', 1)  # index of 1 for strips

        except Exception:
            return ()

    @marks.setter
    def marks(self, values):
        """Set the associated marks for the spectrumDisplay.
        """
        if not isinstance(values, (tuple, list, type(None))):
            raise TypeError(f'{self.__class__.__name__}.marks must be a list or tuple, or None')
        values = values or []

        try:
            refHandler = self._project._crossReferencing
            refHandler.setValues(self, '_MarkSpectrumDisplay', 1, values)

        except Exception as es:
            raise RuntimeError(f'{self.__class__.__name__}.marks: Error setting marks {es}') from es

    #=========================================================================================
    # Implementation functions
    #=========================================================================================

    @classmethod
    def _getAllWrappedData(cls, parent: Window) -> list:
        """get wrappedData (ccp.gui.Module) for all SpectrumDisplay children of Project
        """
        # hike from mainWindow to project to find GuiTasks
        apiGuiTask = (parent.project._wrappedData.findFirstGuiTask(nameSpace='user', name='View') or
                      parent.project._wrappedData.root.newGuiTask(nameSpace='user', name='View'))
        return [x for x in apiGuiTask.sortedModules() if isinstance(x, ApiBoundDisplay)]

    #=========================================================================================
    # CCPN functions
    #=========================================================================================

    def _getDimensionsMapping(self, spectrum: Spectrum) -> list:
        """Get the spectrum dimensions in display order
        """
        # For now: do not allow spectrum mapping with higher dimensionality than the display
        if spectrum.dimensionCount > self.dimensionCount:
            raise RuntimeError(f'Cannot display {spectrum} onto {self}; dimensionality mismatch')

        try:
            spectrumAxisCodes = spectrum._mapAxisCodes(self.axisCodes)[:spectrum.dimensionCount]
        except Exception as es:
            raise RuntimeError(f'Cannot display {spectrum} on {self}; incompatible axisCodes') from es
        if None in spectrumAxisCodes:
            raise RuntimeError(f'Cannot display {spectrum} on {self}; incompatible axisCodes')

        dimensionOrder = spectrum.getByAxisCodes('dimensions', spectrumAxisCodes, exactMatch=True)

        return dimensionOrder

    def _getAxesMapping(self, spectrum: Spectrum) -> list:
        """Get the spectrum dimensionIndices in display order
        CCPNMRINTERNAL: used in _newSpectrumDisplay
        """
        return [dim - 1 for dim in self._getDimensionsMapping(spectrum)]

    @property
    def isIdle(self):
        return all(ss._scheduler.isIdle for ss in self.strips)

    def _finaliseAction(self, action: str, **actionKwds):
        """Notifiers on creation/deletion.
        """
        if not super()._finaliseAction(action, **actionKwds):
            return

        if action in {'create', 'delete'}:
            for strip in self.strips:
                # notify the strips to create their cross-references
                strip._finaliseAction(action, **actionKwds)

    #===========================================================================================
    # new<Object> and other methods
    # Call appropriate routines in their respective locations
    #===========================================================================================

    def copyStrip(self, strip: 'Strip', newIndex=None) -> 'Strip':
        """Make copy of strip in self, at position newIndex - or rightmost.
        """
        from ccpn.ui._implementation.Strip import _copyStrip

        return _copyStrip(self, strip=strip, newIndex=newIndex)


#=========================================================================================
# Connections to parents:
#=========================================================================================

@newObject(SpectrumDisplay)
def _newSpectrumDisplay(window: Window, spectrum: Spectrum, axisCodes: (str,),
                        stripDirection: str = 'Y', name: str = None,
                        zPlaneNavigationMode: str = None,
                        isGrouped: bool = False, flip1D=False):
    """Create new SpectrumDisplay.

    :param window:
    :param spectrum: a Spectrum instance to be displayed.
    :param axisCodes: display order of the dimensions of spectrum.
    :param stripDirection: stripDirection: if 'X' or 'Y' set strip axis.
    :param name: optional name.
    :param zPlaneNavigationMode:

    :return: a new SpectrumDisplay instance.
    """
    # local import to avoid cycles
    from ccpn.util.Constants import AXISUNIT_NUMBER, AXISUNIT_POINT, AXISUNIT_PPM

    if window is None or not isinstance(window, Window):
        raise ValueError('Expected window argument; got %r' % window)
    apiWindow = window._wrappedData
    if not (apiTask := apiWindow.getGuiTask()):
        # fix for bad project with bad guiTasks
        #   - make sure there is a correctly attached guiTask to the window
        getLogger().warning(f'--> project contains badly defined guiTask')
        apiTask = apiWindow.root.findFirstGuiTask(nameSpace='user', name='View') or \
                  apiWindow.root.newGuiTask(nameSpace='user', name='View')
        if apiWindow not in apiTask.windows:
            getLogger().warning(f'--> repairing window/guiTask')
            apiTask.addWindow(apiWindow)
    project = window.project

    if (spectrum := project.getByPid(spectrum) if isinstance(spectrum, str) else spectrum) is None:
        raise ValueError('_newSpectrumDisplay: undefined spectrum')
    is1D = (spectrum.dimensionCount == 1)

    if not is1D and flip1D:
        raise ValueError('_newSpectrumDisplay: flid1D does not alpply to nD spectra')

    # set api-parameters for display generation
    displayPars = dict(
            stripDirection=stripDirection,
            window=apiWindow,
            )

    if is1D:
        # build axes for 1D display
        if flip1D:
            axisCodes = [SpectrumDisplay.INTENSITY] + spectrum.axisCodes
        else:
            axisCodes = spectrum.axisCodes + [SpectrumDisplay.INTENSITY]

    if len(axisCodes) < 2:
        raise ValueError("New SpectrumDisplay must have at least two axisCodes")
    displayPars['axisCodes'] = displayPars['axisOrder'] = axisCodes

    # Add name, setting and insuring uniqueness if necessary
    if name is None:
        excludedNames = [SpectrumDisplay.INTENSITY]
        name = ''.join(['%dD_' % spectrum.dimensionCount]
                       + [str(x)[:1] for x in axisCodes if x not in excludedNames])
    name = SpectrumDisplay._uniqueApiName(project, name)
    displayPars['name'] = name

    # Create Boundstrip/Nostrip display and first strip
    apiSpectrumDisplay = apiTask.newBoundDisplay(**displayPars)
    if (display := project._data2Obj.get(apiSpectrumDisplay)) is None:
        raise RuntimeError('Unable to generate new SpectrumDisplay')

    # may need to set other values here, guarantees before strip generation
    display.stripArrangement = stripDirection
    if zPlaneNavigationMode:
        display.zPlaneNavigationMode = zPlaneNavigationMode
    # GWV: no idea what these are for; just adapted from original code
    # it gets crazy on 1D-displays
    # display._useFirstDefault = (False if is1D else True)
    display.isGrouped = isGrouped

    # Create first strip; looks like we need this before other things, otherwise the api goes crazy
    apiStrip = apiSpectrumDisplay.newBoundStrip()
    if (strip := project._data2Obj.get(apiStrip)) is None:
        raise RuntimeError(f'Unable to generate new Strip for {display}')

    # Create axes
    if is1D:
        if flip1D:
            # SpectrumDisplay X; i.e. Intensity
            apiSpectrumDisplay.newIntensityAxis(code=SpectrumDisplay.INTENSITY, stripSerial=1, unit=AXISUNIT_NUMBER)

            # SpectrumDisplay Y
            if spectrum.dimensionTypes[0] == specLib.DIMENSION_FREQUENCY:
                apiSpectrumDisplay.newFrequencyAxis(code=axisCodes[1], stripSerial=1, unit=AXISUNIT_PPM)
            elif spectrum.dimensionTypes[0] == specLib.DIMENSION_TIME:
                apiSpectrumDisplay.newFidAxis('time', stripSerial=1, unit=AXISUNIT_POINT)

            # we need these to do the checks
            # display._isotopeCodes = tuple(spectrum.isotopeCodes)

        else:
            # SpectrumDisplay X
            if spectrum.dimensionTypes[0] == specLib.DIMENSION_FREQUENCY:
                apiSpectrumDisplay.newFrequencyAxis(code=axisCodes[0], stripSerial=1, unit=AXISUNIT_PPM)
            elif spectrum.dimensionTypes[0] == specLib.DIMENSION_TIME:
                apiSpectrumDisplay.newFidAxis('time', stripSerial=1, unit=AXISUNIT_POINT)

            # SpectrumDisplay Y; i.e. Intensity
            apiSpectrumDisplay.newIntensityAxis(code=SpectrumDisplay.INTENSITY, stripSerial=1, unit=AXISUNIT_NUMBER)

            # we need these to do the checks
            # display._isotopeCodes = tuple(spectrum.isotopeCodes)

    else:
        # nD
        spectrumAxesInDisplayOrder = display._getAxesMapping(spectrum)
        # display._isotopeCodes = tuple(spectrum.isotopeCodes[axis] for axis in spectrumAxesInDisplayOrder)

        for ii, dimIndex in enumerate(spectrumAxesInDisplayOrder):
            displayAxisCode = axisCodes[ii]  # axisCodes are passed in and thus in displayOrder

            # # if (ii == 0 and stripDirection == 'X' or ii == 1 and stripDirection == 'Y' or
            # #    not stripDirection):
            # # Reactivate this code if we reintroduce non-strip displays (stripDirection == None)
            # if (ii == 0 and stripDirection == 'X' or ii == 1 and stripDirection == 'Y'):
            #     stripSerial = 0
            # else:
            #     stripSerial = 1
            #
            # # NOTE: ED setting to 1 notifies api to create a full axis set for each additional spectrum
            # #       required for dynamic switching of strip arrangement
            # #       stripDirection is no longer used in the api
            # stripSerial = 1

            dimType = spectrum.dimensionTypes[dimIndex]
            if dimType == specLib.DIMENSION_FREQUENCY:
                apiAxis = apiSpectrumDisplay.newFrequencyAxis(code=displayAxisCode, stripSerial=1, unit=AXISUNIT_PPM)
                _unit = apiAxis.unit

            elif dimType == specLib.DIMENSION_TIME:
                # Cannot do newFidAxis; all falls apart
                # apiSpectrumDisplay.newFidAxis(code=axisCode, stripSerial=1, unit=AXISUNIT_POINT)
                apiAxis = apiSpectrumDisplay.newFrequencyAxis(code=displayAxisCode, stripSerial=1, unit=AXISUNIT_POINT)
                _unit = apiAxis.unit

            elif dimType == specLib.DIMENSION_SAMPLED:
                apiAxis = apiSpectrumDisplay.newFrequencyAxis(code=displayAxisCode, stripSerial=1, unit=AXISUNIT_POINT)
                _unit = apiAxis.unit

            else:
                raise RuntimeError('Invalid dimensionType "%s"' % dimType)

    # display the spectrum, this will also create a new spectrumView
    # Define the display as new, to avoid the isotopeCode and dimensionTypes checks
    display._isNew = True
    spectrumView = display.displaySpectrum(spectrum=spectrum)
    display._isNew = False
    # We now can set the isotopeCode and dimensionTypes parameters to define the
    # spectrumDisplay
    display._dimensionTypes = spectrumView.dimensionTypes
    display._isotopeCodes = spectrumView.isotopeCodes

    # call any post initialise routines
    display.setToolbarButtons()

    # initialise the strip axes, using the values from spectrumView
    # this will also update any Strip.planeToolbar widgets and the GL
    strip._initAxesValues(spectrumView)

    # having initialised the strip axes, we can update the display
    # settings widget
    display._updateSettingsAxesUnits()

    return display


# GWV 20210807: moved to _implementation.Window
# # Window.spectrumDisplays property
# def getter(window: Window):
#     ll = [x for x in window._wrappedData.sortedModules() if isinstance(x, ApiBoundDisplay)]
#     return tuple(window._project._data2Obj[x] for x in ll if x in window._project._data2Obj)
#
#
# Window.spectrumDisplays = property(getter, None, None,
#                                    "SpectrumDisplays shown in Window")
# del getter

# Notifiers:

# crosslinks window, nmrResidue
Project._apiNotifiers.append(
        ('_modifiedLink', {'classNames': ('Window', 'SpectrumDisplay')},
         ApiBoundDisplay._metaclass.qualifiedName(), 'setWindow'),
        )
Project._apiNotifiers.append(
        ('_modifiedLink', {'classNames': ('NmrResidue', 'SpectrumDisplay')},
         ApiBoundDisplay._metaclass.qualifiedName(), 'setResonanceGroup'),
        )
className = ApiWindow._metaclass.qualifiedName()
Project._apiNotifiers.extend(
        (('_modifiedLink', {'classNames': ('SpectrumDisplay', 'Window')}, className, 'addModule'),
         ('_modifiedLink', {'classNames': ('SpectrumDisplay', 'Window')}, className, 'removeModule'),
         ('_modifiedLink', {'classNames': ('SpectrumDisplay', 'Window')}, className, 'setModules'),
         )
        )

# WARNING link notifiers for both Window <-> Module and Window<->SpectrumDisplay
# are triggered together when  the change is on the Window side.
# Programmer take care that your notified function will work for both inputs !!!
className = ApiResonanceGroup._metaclass.qualifiedName()
Project._apiNotifiers.extend(
        (('_modifiedLink', {'classNames': ('SpectrumDisplay', 'NmrResidue')}, className,
          'addSpectrumDisplay'),
         ('_modifiedLink', {'classNames': ('SpectrumDisplay', 'NmrResidue')}, className,
          'removeSpectrumDisplay'),
         ('_modifiedLink', {'classNames': ('SpectrumDisplay', 'NmrResidue')}, className,
          'setSpectrumDisplays'),
         )
        )
