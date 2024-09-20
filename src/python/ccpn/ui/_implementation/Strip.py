"""
GUI Display Strip class
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
__dateModified__ = "$dateModified: 2024-08-28 18:22:04 +0100 (Wed, August 28, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

from typing import Sequence, Tuple

from ccpnmodel.ccpncore.api.ccpnmr.gui.Task import BoundStrip as ApiBoundStrip
from ccpn.core.Spectrum import Spectrum
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core.lib.AxisCodeLib import _axisCodeMapIndices
from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, ccpNmrV3CoreSetter
from ccpn.core._implementation.updates.update_3_0_4 import _updateStrip_3_0_4_to_3_1_0
from ccpn.core._implementation.Updater import updateObject, UPDATE_POST_OBJECT_INITIALISATION
from ccpn.ui._implementation.SpectrumDisplay import SpectrumDisplay
from ccpn.util.decorators import logCommand
from ccpn.util.Constants import AXISUNIT_PPM, AXISUNIT_HZ, AXISUNIT_POINT


@updateObject(fromVersion='3.0.4',
              toVersion='3.1.0',
              updateFunction=_updateStrip_3_0_4_to_3_1_0,
              updateMethod=UPDATE_POST_OBJECT_INITIALISATION)
class Strip(AbstractWrapperObject):
    """Display Strip for 1D or nD spectrum"""

    #: Short class name, for PID.
    shortClassName = 'GS'
    # Attribute it necessary as subclasses must use superclass className
    className = 'Strip'

    _parentClass = SpectrumDisplay

    #: Name of plural link to instances of class
    _pluralLinkName = 'strips'

    # the attribute name used by current
    _currentAttributeName = 'strip'

    #: List of child classes.
    _childClasses = []

    _isGuiClass = True

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiBoundStrip._metaclass.qualifiedName()

    # internal namespace
    _STRIPTILEPOSITION = '_stripTilePosition'
    _PINNED = '_pinned'

    #-----------------------------------------------------------------------------------------

    def __init__(self, project, wrappedData):
        super().__init__(project=project, wrappedData=wrappedData)

    #-----------------------------------------------------------------------------------------
    # Attributes and methods related to the data structure
    #-----------------------------------------------------------------------------------------

    @property
    def spectrumDisplay(self) -> SpectrumDisplay:
        """SpectrumDisplay containing strip."""
        return self._project._data2Obj.get(self._wrappedData.spectrumDisplay)

    _parent = spectrumDisplay

    #GWV: moved here from _implementation/Axis.py
    @property
    def orderedAxes(self) -> Tuple:
        """Axes in display order (X, Y, Z1, Z2, ...) """
        apiStrip = self._wrappedData
        ff = self._project._data2Obj.get
        return tuple(ff(apiStrip.findFirstStripAxis(axis=x)) for x in apiStrip.orderedAxes)

    # GWV 23/12: There should not be a setter! Created by SpectrumDisplay/Strip
    # @orderedAxes.setter
    # def orderedAxes(self, value: Sequence):
    #     value = [self.getByPid(x) if isinstance(x, str) else x for x in value]
    #     #self._wrappedData.orderedAxes = tuple(x._wrappedData.axis for x in value)
    #     self._wrappedData.axisOrder = tuple(x.code for x in value)

    #-----------------------------------------------------------------------------------------
    # Functional attributes of the class
    #-----------------------------------------------------------------------------------------

    @property
    def axisCodes(self) -> Tuple[str, ...]:
        """Fixed string Axis codes in original display order (X, Y, Z1, Z2, ...)"""
        return self._wrappedData.axisCodes

    @property
    def axisOrder(self) -> Tuple[str, ...]:
        """String Axis codes in display order (X, Y, Z1, Z2, ...), determine axis display order"""
        return self._wrappedData.axisOrder

    @axisOrder.setter
    def axisOrder(self, value: Sequence):
        self._wrappedData.axisOrder = value

    @property
    def positions(self) -> Tuple[float, ...]:
        """Axis centre positions, in display order"""
        return self._wrappedData.positions

    @positions.setter
    def positions(self, value):
        self._wrappedData.positions = value

    @property
    def widths(self) -> Tuple[float, ...]:
        """Axis display widths, in display order"""
        return self._wrappedData.widths

    @widths.setter
    def widths(self, value):
        self._wrappedData.widths = value

    @property
    def units(self) -> Tuple[str, ...]:
        """Axis units, in display order"""
        # return self._wrappedData.units
        return tuple(ax.unit for ax in self.orderedAxes)

    @property
    def _unitIndices(self) -> Tuple[int, ...]:
        """Axis units indices, in display order"""
        return tuple(ax._unitIndex for ax in self.orderedAxes)

    @property
    def spectra(self) -> Tuple[Spectrum, ...]:
        """The spectra attached to the strip (whether display is currently turned on or not)"""
        return tuple(x.spectrum for x in self.spectrumViews)

    def getSpectra(self) -> Tuple[Spectrum, ...]:
        """The spectra attached to the strip (whether display is currently turned on or not) in displayed order"""
        return tuple(sv.spectrum for sv in self.getSpectrumViews())

    def getVisibleSpectra(self) -> Tuple[Spectrum, ...]:
        """Return a tuple of spectra currently visible in the strip in displayed order
        """
        return tuple(sv.spectrum for sv in self.getSpectrumViews() if sv.isDisplayed)

    def getSpectrumViews(self) -> Tuple['SpectrumView', ...]:
        """The spectrumViews attached to the strip (whether display is currently turned on or not) in display order"""
        dd = [(sv._index, sv) for sv in self.spectrumViews]
        return tuple(val[1] for val in sorted(dd))

    def _setSpectrumViews(self, spectrumViews):
        """Set the new ordering for the spectrumViews.
        Must be the original spectrumViews"""
        if set(self.getSpectrumViews()) != set(spectrumViews):
            raise ValueError('bad spectrumViews')
        with undoBlockWithoutSideBar():
            for ind, sv in enumerate(spectrumViews):
                # update the spectrumView indexing
                sv._index = ind

    @property
    def spectrumGroups(self) -> Tuple[Spectrum, ...]:
        """The spectra attached to the strip (whether display is currently turned on or not)"""
        pids = self.spectrumDisplay._getSpectrumGroups()
        return tuple(self.project.getByPid(x) for x in pids)

    @property
    def marks(self) -> tuple:
        """Return the associated marks for the strip.
        """
        # NOTE:ED - these could be place-holders that are generated by the cross-referencing handler
        try:
            refHandler = self._project._crossReferencing
            return refHandler.getValues(self, '_MarkStrip', 1)  # index of 1 for strips

        except Exception:
            # NOTE:ED - need to check why this is being called too early the first time
            return ()

    @marks.setter
    def marks(self, values):
        """Set the associated marks for the strip.
        """
        if not isinstance(values, (tuple, list, type(None))):
            raise TypeError(f'{self.__class__.__name__}.marks must be a list or tuple, or None')
        values = values or []

        try:
            refHandler = self._project._crossReferencing
            refHandler.setValues(self, '_MarkStrip', 1, values)

        except Exception as es:
            raise RuntimeError(f'{self.__class__.__name__}.marks: Error setting marks {es}') from es

    #=========================================================================================
    # CCPN properties
    #=========================================================================================

    @property
    def _displayedSpectra(self) -> tuple:
        """Return a tuple of DisplayedSpectrum instances, in order of the spectrumDisplay
        toolbar, if currently visible
        """
        result = [DisplayedSpectrum(strip=self, spectrumView=specView) \
                  for specView in self.getSpectrumViews() if specView.isDisplayed]
        return tuple(result)

    @property
    def _minAxisLimitsByUnit(self) -> list:
        """:return a list of the min(axis-limits-by-type) (ie. depending on axis.unit) in display-axis order
        """
        _allSpecs = [DisplayedSpectrum(strip=self, spectrumView=sv)
                     for sv in self.spectrumViews
                     ]
        _valsPerSpecView = [ds.minAxisLimitsByUnit
                            for ds in _allSpecs]

        # now get the values per axis
        result = []
        for axisIndex, axis in enumerate(self.axes):
            _tmp = [val[axisIndex] for val in _valsPerSpecView
                    if val[axisIndex] is not None
                    ]
            _minVal = min(_tmp, default=None)
            result.append(_minVal)

        return result

    @property
    def _maxAxisLimitsByUnit(self) -> list:
        """:return a list of the max(axis-limits-by-unit) (ie. depending on axis.unit) in display-axis order
        """
        _allSpecs = [DisplayedSpectrum(strip=self, spectrumView=sv)
                     for sv in self.spectrumViews
                     ]
        _valsPerSpecView = [ds.maxAxisLimitsByUnit
                            for ds in _allSpecs]

        # now get the values per axis
        result = []
        for axisIndex, axis in enumerate(self.axes):
            _tmp = [val[axisIndex] for val in _valsPerSpecView
                    if val[axisIndex] is not None
                    ]
            _maxVal = max(_tmp, default=None)
            result.append(_maxVal)

        return result

    @property
    def _minAxisIncrementByUnit(self) -> list:
        """:return a list of the min(axis-increment-by-unit) (ie. depending on axis.unit) in display-axis order
        """
        _allSpecs = [DisplayedSpectrum(strip=self, spectrumView=sv)
                     for sv in self.spectrumViews
                     ]
        _valsPerSpecView = [ds.axisIncrementsByUnit
                            for ds in _allSpecs]

        # now get the values per axis
        result = []
        for axisIndex, axis in enumerate(self.axes):
            _tmp = [val[axisIndex] for val in _valsPerSpecView
                    if val[axisIndex] is not None
                    ]
            _minVal = min(_tmp, default=None)
            result.append(_minVal)

        return result

    #=========================================================================================
    # API-related properties
    #=========================================================================================

    @property
    def _apiStrip(self) -> ApiBoundStrip:
        """ CCPN Strip matching Strip"""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """id string - serial number converted to string"""
        return str(self._wrappedData.serial)

    @property
    def serial(self) -> int:
        """serial number of Strip, used in Pid and to identify the Strip. """
        return self._wrappedData.serial

    #=========================================================================================
    # Implementation functions
    #=========================================================================================

    @classmethod
    def _getAllWrappedData(cls, parent: SpectrumDisplay) -> list:
        """Get wrappedData (ccpnmr.gui.Task.Strip) in serial number order.
        """
        return parent._wrappedData.sortedStrips()

    def _finaliseAction(self, action: str, **actionKwds):
        """Spawn _finaliseAction notifiers for spectrumView tree attached to this strip.
        """
        if not super()._finaliseAction(action, **actionKwds):
            return

        if action in {'create', 'delete'}:
            for sv in self.spectrumViews:
                sv._finaliseAction(action, **actionKwds)

                for plv in sv.peakListViews:
                    plv._finaliseAction(action, **actionKwds)
                for ilv in sv.integralListViews:
                    ilv._finaliseAction(action, **actionKwds)
                for mlv in sv.multipletListViews:
                    mlv._finaliseAction(action, **actionKwds)

    # @deleteObject()         # - doesn't work here
    def _delete(self):
        """delete the wrappedData.
        CCPN Internal
        """
        self._wrappedData.delete()

    def _setStripIndex(self, index):
        """Set the index of the current strip in the wrapped data.
        CCPN Internal
        """
        ccpnStrip = self._wrappedData
        ccpnStrip.__dict__['index'] = index  # this is the api creation of orderedStrips

    def stripIndex(self):
        """Return the index of the current strip in the spectrumDisplay.
        """
        # original api indexing
        ccpnStrip = self._wrappedData
        # spectrumDisplay = self.spectrumDisplay
        # index = spectrumDisplay.strips.index(self)
        indx = ccpnStrip.index
        return indx

    # from ccpn.util.decorators import profile
    # @profile
    def _clear(self):
        for spectrumView in self.spectrumViews:
            spectrumView.delete()

    def delete(self):
        """trap this delete
        """
        raise RuntimeError('Please use spectrumDisplay.deleteStrip()')

    # def _removeOrderedSpectrumViewIndex(self, index):
    #     self.spectrumDisplay.removeOrderedSpectrumView(index)

    @property
    def tilePosition(self) -> Tuple[int, int]:
        """Returns a tuple of the tile coordinates (from top-left)
        tilePosition = (x, y)
        """
        return self._getInternalParameter(self._STRIPTILEPOSITION) or (0, 0)

    @tilePosition.setter
    def tilePosition(self, value):
        """Setter for tilePosition.
        tilePosition must be a tuple of int (x, y)
        """
        if not isinstance(value, tuple):
            raise ValueError('Expected a tuple for tilePosition')
        if len(value) != 2:
            raise ValueError('Tuple must be (x, y)')
        if any(type(vv) != int for vv in value):
            raise ValueError('Tuple must be of type int')

        self._setInternalParameter(self._STRIPTILEPOSITION, value)

    @property
    def pinned(self) -> Tuple[int, int]:
        """Get/set the pinned state of the strip.
        This facilitates marking a strip of interest.
        """
        return self._getInternalParameter(self._PINNED) or False

    @pinned.setter
    @ccpNmrV3CoreSetter(pinnedChanged=True)
    def pinned(self, value):
        """Setter for pinned.
        """
        if not isinstance(value, bool):
            raise ValueError('Expected a bool')

        self._setInternalParameter(self._PINNED, value)

    #=========================================================================================
    # CCPN functions
    #=========================================================================================

    def _clone(self):
        """create new strip that duplicates this one, appending it at the end
        """
        apiStrip = self._wrappedData.clone()
        result = self._project._data2Obj.get(apiStrip)
        if result is None:
            raise RuntimeError('Unable to generate new Strip item')

        return result

    @logCommand(get='self')
    def moveStrip(self, newIndex: int):
        """Move strip to index newIndex in orderedStrips
        """
        if not isinstance(newIndex, int):
            raise TypeError(f'newIndex {newIndex} is not of type Int')

        currentIndex = self._wrappedData.index
        if currentIndex == newIndex:
            return

        # get the current order
        stripCount = self.spectrumDisplay.stripCount

        if newIndex >= stripCount:
            # Put strip at the right, which means newIndex should be stripCount - 1
            if newIndex > stripCount:
                raise TypeError(
                        f"Attempt to copy strip to position {newIndex} in display with only {stripCount} strips"
                        )
            newIndex = stripCount - 1

        # move the strip
        self._wrappedData.moveTo(newIndex)

    #=========================================================================================
    # property STUBS: hot-fixed later
    #=========================================================================================

    @property
    def axes(self) -> list['Axis']:
        """STUB: hot-fixed later
        :return: a list of axes in the Strip
        """
        return []

    @property
    def integralListViews(self) -> list['IntegralListView']:
        """STUB: hot-fixed later
        :return: a list of integralListViews in the Strip
        """
        return []

    @property
    def integralViews(self) -> list['IntegralView']:
        """STUB: hot-fixed later
        :return: a list of integralViews in the Strip
        """
        return []

    @property
    def multipletListViews(self) -> list['MultipletListView']:
        """STUB: hot-fixed later
        :return: a list of multipletListViews in the Strip
        """
        return []

    @property
    def multipletViews(self) -> list['MultipletView']:
        """STUB: hot-fixed later
        :return: a list of multipletViews in the Strip
        """
        return []

    @property
    def peakListViews(self) -> list['PeakListView']:
        """STUB: hot-fixed later
        :return: a list of peakListViews in the Strip
        """
        return []

    @property
    def peakViews(self) -> list['PeakView']:
        """STUB: hot-fixed later
        :return: a list of peakViews in the Strip
        """
        return []

    @property
    def spectrumViews(self) -> list['SpectrumView']:
        """STUB: hot-fixed later
        :return: a list of spectrumViews in the Strip
        """
        return []

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

    def getSpectrumView(self, relativeId: str) -> 'SpectrumView | None':
        """STUB: hot-fixed later
        :return: an instance of SpectrumView, or None
        """
        return None


#=========================================================================================
# CCPN functions
#=========================================================================================

def _copyStrip(self: SpectrumDisplay, strip: Strip, newIndex=None) -> Strip:
    """Make copy of strip in self, at position newIndex - or rightmost.
    """
    strip = self.getByPid(strip) if isinstance(strip, str) else strip
    if not isinstance(strip, Strip):
        raise TypeError('strip is not of type Strip')

    stripCount = self.stripCount
    if newIndex and newIndex >= stripCount:
        # Put strip at the right, which means newIndex should be None
        if newIndex > stripCount:
            # warning
            self._project._logger.warning(
                    f"Attempt to copy strip to position {newIndex} in display with only {stripCount} strips"
                    )
        newIndex = None

    # with logCommandBlock(prefix='newStrip=', get='self') as log:
    #     log('copyStrip', strip=repr(strip.pid))
    with undoBlockWithoutSideBar():

        if strip.spectrumDisplay is self:
            # Within same display. Not that useful, but harmless
            # newStrip = strip.clone()

            # clone the last strip
            newStrip = strip.spectrumDisplay.addStrip(strip)

            if newIndex is not None:
                newStrip.moveTo(newIndex)

        else:
            mapIndices = _axisCodeMapIndices(strip.axisOrder, self.axisOrder)
            if mapIndices is None:
                raise ValueError(f"Strip {strip.pid} not compatible with window {self.pid}")

            positions = strip.positions
            widths = strip.widths
            # newStrip = self.orderedStrips[0].clone()

            # clone the first strip
            newStrip = strip.spectrumDisplay.addStrip(self.orderedStrips[0])

            if newIndex is not None:
                newStrip.moveTo(newIndex)
            for ii, axis in enumerate(newStrip.orderedAxes):
                ind = mapIndices[ii]
                if ind is not None and axis._wrappedData.axis.stripSerial != 0:
                    # Override if there is a mapping and axis is not shared for all strips
                    axis.position = positions[ind]
                    axis.widths = widths[ind]

    return newStrip


# GWV 10/12/21: in SpectrumDisplay
# SpectrumDisplay.copyStrip = _copyStrip
# del _copyStrip


#=========================================================================================
# DisplayedSpectrum
#=========================================================================================

class DisplayedSpectrum(object):
    """GWV; a class to hold SpectrumView and strip objects
    Used to map any data/axis/parameter actions in a SpectrumView dependent fashion
    Only to be used internally
    """

    def __init__(self, strip, spectrumView):
        self.strip = strip
        self.spectrumView = spectrumView

    @property
    def spectrum(self):
        return self.spectrumView.spectrum

    @property
    def spectrumDimensions(self):
        """Return a tuple of spectrumDimensions in axis display order
        Assure that the len always is dimensionCount of the spectrumDisplay
        by adding None's if necessary. This compensates for lower dimensional
        spectra (e.g. a 2D mapped onto a 3D)
        """
        result = self.spectrumView.spectrumDimensions
        result.extend(
                None
                for _ in range(len(result), self.strip.spectrumDisplay.dimensionCount)
                )
        return tuple(result)

    @property
    def ppmPerPoints(self) -> tuple:
        """Return tuple of ppm-per-point values in axis display order.
        Assure that the len always is dimensionCount of the spectrumDisplay
        by adding None's if necessary. This compensates for lower dimensional
        spectra (e.g. a 2D mapped onto a 3D)
        """
        result = self.spectrumView.ppmPerPoints
        result.extend(
                None
                for _ in range(len(result), self.strip.spectrumDisplay.dimensionCount)
                )
        return tuple(result)

    @property
    def currentPositionsInPpm(self) -> tuple:
        """Return a tuple of current positions (i.e. the centres) for axes
        in display order.
        The length is always dimensionCount of the spectrumDisplay
        """
        axes = self.strip.orderedAxes
        result = [ax.position for ax in axes]
        result.extend(
                None
                for _ in range(len(result), self.strip.spectrumDisplay.dimensionCount)
                )
        return tuple(result)

    @property
    def currentWidthsInPpm(self) -> tuple:
        """Return a tuple of the current widths for axes in display order.
        The length is always dimensionCount of the spectrumDisplay
        """
        axes = self.strip.orderedAxes
        result = [ax.width for ax in axes]
        result.extend(
                None
                for _ in range(len(result), self.strip.spectrumDisplay.dimensionCount)
                )
        return tuple(result)

    @property
    def currentRegionsInPpm(self) -> tuple:
        """Return a tuple of (leftPpm,rightPpm) for current regions for axes
        in display order.
        """
        axes = self.strip.orderedAxes
        result = [ax.region for ax in axes]
        result.extend(
                (None, None)
                for _ in range(len(result), self.strip.spectrumDisplay.dimensionCount)
                )
        return tuple(result)

    def _getRegionsInPoints(self, regions):
        """Helper function"""
        spectrumDimensions = self.spectrumView.spectrumDimensions
        result = []
        for indx, specDim in enumerate(spectrumDimensions):
            minPpm, maxPpm = regions[indx]
            minPoint = specDim.ppmToPoint(minPpm)
            maxPoint = specDim.ppmToPoint(maxPpm)
            result.append(tuple(sorted((minPoint, maxPoint))))
        result.extend(
                (None, None)
                for _ in range(len(result), self.strip.spectrumDisplay.dimensionCount)
                )
        return tuple(result)

    @property
    def currentRegionsInPoints(self) -> tuple:
        """Return a tuple of (minPoint,maxPoint) tuples corresponding to
        current regions for axes in display order.
        Assure that the len always is dimensionCount of the spectrumDisplay
        by adding None's if necessary. This compensates for lower dimensional
        spectra (e.g. a 2D mapped onto a 3D)
        """
        return self._getRegionsInPoints(self.currentRegionsInPpm)

    @property
    def axisIncrementsByUnit(self) -> tuple:
        """Return axis increments by unit for axes in display order.
        Assure that the len always is dimensionCount of the spectrumDisplay
        by adding None's if necessary. This compensates for lower dimensional
        spectra (e.g. a 2D mapped onto a 3D)
        """
        result = []
        for axis, ppmPerPoint, specFreq, points in zip(self.strip.orderedAxes,
                                                       self.spectrumView.ppmPerPoints,
                                                       self.spectrumView.spectrometerFrequencies,
                                                       self.spectrumView.pointCounts
                                                       ):

            if axis.unit == AXISUNIT_PPM:
                result.append(ppmPerPoint)

            elif axis.unit == AXISUNIT_POINT:
                result.append(1.0)

            elif axis.unit == AXISUNIT_HZ:
                result.append(ppmPerPoint * specFreq)

            else:
                raise RuntimeError(f'axisIncrementsByUnit: undefined axis unit "{axis.unit}"')

        result.extend(None for _ in range(len(result), self.strip.spectrumDisplay.dimensionCount))

        return tuple(result)

    @property
    def axisLimitsByUnit(self) -> tuple:
        """Return a tuple of (minVal,maxVal) tuples corresponding to the
        limits by unit for axes in display order.
        Assure that the len always is dimensionCount of the spectrumDisplay
        by adding None's if necessary. This compensates for lower dimensional
        spectra (e.g. a 2D mapped onto a 3D)
        """
        result = []
        for axis, specDim, limits, specFreq, points in zip(self.strip.orderedAxes,
                                                           self.spectrumView.spectrumDimensions,
                                                           self.spectrumView.aliasingLimits,
                                                           self.spectrumView.spectrometerFrequencies,
                                                           self.spectrumView.pointCounts
                                                           ):

            if axis.unit == AXISUNIT_PPM:
                result.append((min(limits), max(limits)))

            elif axis.unit == AXISUNIT_POINT:
                result.append((1.0, float(points)))

            elif axis.unit == AXISUNIT_HZ:
                limits = [val * specFreq for val in limits]
                result.append((min(limits), max(limits)))

            else:
                raise RuntimeError(f'axisLimitsByUnit: undefined axis unit "{axis.unit}"')

        result.extend(
                (None, None)
                for _ in range(len(result), self.strip.spectrumDisplay.dimensionCount)
                )
        return tuple(result)

    @property
    def minAxisLimitsByUnit(self) -> tuple:
        """Return a tuple corresponding to the minimum limits by type for axes in
        display order.
        Assure that the len always is dimensionCount of the spectrumDisplay
        by adding None's if necessary. This compensates for lower dimensional
        spectra (e.g. a 2D mapped onto a 3D)
        """
        result = [val[0] for val in self.axisLimitsByUnit]
        return tuple(result)

    @property
    def maxAxisLimitsByUnit(self) -> tuple:
        """Return a tuple corresponding to the maximum limits by unit for axes in
        display order.
        Assure that the len always is dimensionCount of the spectrumDisplay
        by adding None's if necessary. This compensates for lower dimensional
        spectra (e.g. a 2D mapped onto a 3D)
        """
        result = [val[1] for val in self.axisLimitsByUnit]
        return tuple(result)

    @property
    def aliasingLimits(self) -> tuple:
        """Return a tuple of aliasingLimits (in ppm) in display order.
        Assure that the len always is dimensionCount of the spectrumDisplay
        by adding None's if necessary. This compensates for lower dimensional
        spectra (e.g. a 2D mapped onto a 3D).
        """
        result = list(self.spectrumView.aliasingLimits)
        result.extend(
                (None, None)
                for _ in range(len(result), self.strip.spectrumDisplay.dimensionCount)
                )
        return tuple(result)

    def getSliceTuples(self, regions) -> list:
        """Return a list of (startPoint,endPoint) slice tuples for regions in spectrum order.
        """
        regionInPoints = [list(rp) for rp in self._getRegionsInPoints(regions)]
        # first assemble the result in display order
        # result = []
        # for points in regionInPoints[:self.spectrumView.dimensionCount]:
        #     for i in (0, 1):
        #         points[i] = int(points[i] + 0.5)
        #     result.append(tuple(points))
        # find the upper/lower limits to reduce rounding errors
        result = [[min(int(points[0] + 1), int(points[1])), int(points[1])]
                  for points in regionInPoints[:self.spectrumView.dimensionCount]]
        # create a mapping dict to reorder in spectrum order
        mapping = dict([(dimIdx, idx) for idx, dimIdx in enumerate(self.spectrumView.dimensionIndices)])
        sliceTuples = [result[mapping[idx]] for idx in self.spectrumView.spectrum.dimensionIndices]
        return sliceTuples

    @staticmethod
    def checkForRegionsOutsideLimits(regions, strip, spectrumView) -> tuple:
        """check if regions are fully outside the aliasing limits of spectrum.
        :return a tuple of booleans in display order
        """
        result = []
        minL = strip._CcpnGLWidget._spectrumSettings[spectrumView].minAliasedFrequency
        maxL = strip._CcpnGLWidget._spectrumSettings[spectrumView].maxAliasedFrequency

        # for region, limits in zip(regions, self.spectrumView.aliasingLimits):
        for region, minLimit, maxLimit in zip(regions, minL, maxL):
            # to not be dependent on order of low,high values in region or limits:
            minVal = min(region)
            maxVal = max(region)
            # minLimit = min(limits)
            # maxLimit = max(limits)
            if maxVal < minLimit or minVal > maxLimit:
                result.append(True)
            else:
                result.append(False)

        return tuple(result)

    def __str__(self):
        return f"<DisplayedSpectrum: strip: {self.strip.pid}; spectrumView: {self.spectrumView.pid}>"

    __repr__ = __str__
