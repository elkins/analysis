"""Spectrum View in a specific SpectrumDisplay

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

import operator
from typing import Tuple

from ccpnmodel.ccpncore.api.ccpnmr.gui.Task import SpectrumView as ApiSpectrumView
from ccpnmodel.ccpncore.api.ccpnmr.gui.Task import StripSpectrumView as ApiStripSpectrumView
from ccpn.core.Project import Project
from ccpn.core.Spectrum import Spectrum
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core.lib import Pid
from ccpn.core.lib.ContextManagers import deleteWrapperWithoutSideBar, \
    ccpNmrV3CoreUndoBlock, ccpNmrV3CoreSetter, newV3Object
from ccpn.ui._implementation.Strip import Strip
from ccpn.util.decorators import logCommand


class SpectrumView(AbstractWrapperObject):
    """Spectrum View for 1D or nD spectrum"""

    #: Short class name, for PID.
    shortClassName = 'GV'
    # Attribute it necessary as subclasses must use superclass className
    className = 'SpectrumView'

    _parentClassName = 'Strip'
    _parentClass = Strip

    #: Name of plural link to instances of class
    _pluralLinkName = 'spectrumViews'

    #: List of child classes.
    _childClasses = []

    _isGuiClass = True

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiStripSpectrumView._metaclass.qualifiedName()

    _CONTOURATTRIBUTELIST = """negativeContourBase negativeContourCount negativeContourFactor
                               displayNegativeContours negativeContourColour
                               positiveContourBase positiveContourCount positiveContourFactor
                               displayPositiveContours positiveContourColour
                               sliceColour
                            """

    #=========================================================================================

    # __init__ not required

    @classmethod
    def _restoreObject(cls, project, apiObj):
        """Subclassed to allow for initialisations on restore
        """
        result = super()._restoreObject(project, apiObj)

        # check that the index is not None
        if result._index is None:
            result._index = 0

        return result

    #=========================================================================================
    # CCPN properties
    #=========================================================================================

    @property
    def _apiStripSpectrumView(self) -> ApiStripSpectrumView:
        """ CCPN SpectrumView matching SpectrumView"""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """id string - spectrumName"""
        return self._wrappedData.spectrumView.spectrumName.translate(Pid.remapSeparators)

    @property
    def spectrumName(self) -> str:
        """Name of connected spectrum"""
        return self._wrappedData.spectrumView.spectrumName

    @property
    def _parent(self) -> Strip:
        """Strip containing stripSpectrumView."""
        return self._project._data2Obj.get(self._wrappedData.strip)

    strip = _parent

    def delete(self):
        """trap this delete
        """
        raise RuntimeError('Please use spectrumDisplay.removeSpectrum()')

    @deleteWrapperWithoutSideBar()
    def _delete(self):
        """Delete SpectrumView from strip, should be unique.
        """
        # import gc
        # import ctypes
        #
        # print(f'  spectrumView count:  {len(gc.get_referrers(self))}   {ctypes.c_long.from_address(id(self)).value}')

        self._wrappedData.spectrumView.delete()

    @property
    def isDisplayed(self) -> bool:
        """True if this spectrum is displayed."""
        return self._wrappedData.spectrumView.isDisplayed

    @isDisplayed.setter
    def isDisplayed(self, value: bool):
        self._wrappedData.spectrumView.isDisplayed = value

    @property
    def positiveContourColour(self) -> str:
        """Colour identifier for positive contours.

        If not set for SpectrumView gives you the value for Spectrum.
        If set for SpectrumView overrides Spectrum value.
        Set SpectrumView value to None to return to non-local value"""
        wrappedData = self._wrappedData.spectrumView
        result = wrappedData.positiveContourColour
        if result is None:
            obj = wrappedData.dataSource
            result = obj and obj.positiveContourColour
        return result

    @positiveContourColour.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def positiveContourColour(self, value: str):
        if not isinstance(value, (str, type(None))):
            raise ValueError("positiveContourColour must be a string/None.")

        self._guiChanged = True
        self._wrappedData.spectrumView.positiveContourColour = value

    @property
    def positiveContourCount(self) -> int:
        """Number of positive contours.

        If not set for SpectrumView gives you the value for Spectrum.
        If set for SpectrumView overrides Spectrum value.
        Set SpectrumView value to None to return to non-local value"""
        wrappedData = self._wrappedData.spectrumView
        result = wrappedData.positiveContourCount
        if result is None:
            obj = wrappedData.dataSource
            result = obj and obj.positiveContourCount
        return result

    @positiveContourCount.setter
    def positiveContourCount(self, value: int):
        if self.positiveContourCount != value:
            self._wrappedData.spectrumView.positiveContourCount = value

    @property
    def positiveContourBase(self) -> float:
        """Base level for positive contours.

        If not set for SpectrumView gives you the value for Spectrum.
        If set for SpectrumView overrides Spectrum value.
        Set SpectrumView value to None to return to non-local value"""
        wrappedData = self._wrappedData.spectrumView
        result = wrappedData.positiveContourBase
        if result is None:
            obj = wrappedData.dataSource
            result = obj and obj.positiveContourBase
        return result

    @positiveContourBase.setter
    def positiveContourBase(self, value: float):
        if self.positiveContourBase != value:
            self._wrappedData.spectrumView.positiveContourBase = value

    @property
    def positiveContourFactor(self) -> float:
        """Level multiplication factor for positive contours.

        If not set for SpectrumView gives you the value for Spectrum.
        If set for SpectrumView overrides Spectrum value.
        Set SpectrumView value to None to return to non-local value"""
        wrappedData = self._wrappedData.spectrumView
        result = wrappedData.positiveContourFactor
        if result is None:
            obj = wrappedData.dataSource
            result = obj and obj.positiveContourFactor
        return result

    @positiveContourFactor.setter
    def positiveContourFactor(self, value: float):
        if self.positiveContourFactor != value:
            self._wrappedData.spectrumView.positiveContourFactor = value

    @property
    def displayPositiveContours(self) -> bool:
        """True if positive contours are displayed?"""
        return self._wrappedData.spectrumView.displayPositiveContours

    @displayPositiveContours.setter
    def displayPositiveContours(self, value: bool):
        self._wrappedData.spectrumView.displayPositiveContours = value

    @property
    def negativeContourColour(self) -> str:
        """Colour identifier for negative contours.

        If not set for SpectrumView gives you the value for Spectrum.
        If set for SpectrumView overrides Spectrum value.
        Set SpectrumView value to None to return to non-local value"""
        wrappedData = self._wrappedData.spectrumView
        result = wrappedData.negativeContourColour
        if result is None:
            obj = wrappedData.dataSource
            result = obj and obj.negativeContourColour
        return result

    @negativeContourColour.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def negativeContourColour(self, value: str):
        if not isinstance(value, (str, type(None))):
            raise ValueError("negativeContourColour must be a string/None.")

        self._guiChanged = True
        self._wrappedData.spectrumView.negativeContourColour = value

    @property
    def negativeContourCount(self) -> int:
        """Number of negative contours.

        If not set for SpectrumView gives you the value for Spectrum.
        If set for SpectrumView overrides Spectrum value.
        Set SpectrumView value to None to return to non-local value"""
        wrappedData = self._wrappedData.spectrumView
        result = wrappedData.negativeContourCount
        if result is None:
            obj = wrappedData.dataSource
            result = obj and obj.negativeContourCount
        return result

    @negativeContourCount.setter
    def negativeContourCount(self, value: int):
        if self.negativeContourCount != value:
            self._wrappedData.spectrumView.negativeContourCount = value

    @property
    def negativeContourBase(self) -> float:
        """Base level for negative contours.

        If not set for SpectrumView gives you the value for Spectrum.
        If set for SpectrumView overrides Spectrum value.
        Set SpectrumView value to None to return to non-local value"""
        wrappedData = self._wrappedData.spectrumView
        result = wrappedData.negativeContourBase
        if result is None:
            obj = wrappedData.dataSource
            result = obj and obj.negativeContourBase
        return result

    @negativeContourBase.setter
    def negativeContourBase(self, value: float):
        if self.negativeContourBase != value:
            self._wrappedData.spectrumView.negativeContourBase = value

    @property
    def negativeContourFactor(self) -> float:
        """Level multiplication factor for negative contours.

        If not set for SpectrumView gives you the value for Spectrum.
        If set for SpectrumView overrides Spectrum value.
        Set SpectrumView value to None to return to non-local value"""
        wrappedData = self._wrappedData.spectrumView
        result = wrappedData.negativeContourFactor
        if result is None:
            obj = wrappedData.dataSource
            result = obj and obj.negativeContourFactor
        return result

    @negativeContourFactor.setter
    def negativeContourFactor(self, value: float):
        if self.negativeContourFactor != value:
            self._wrappedData.spectrumView.negativeContourFactor = value

    @property
    def displayNegativeContours(self) -> bool:
        """True if negative contours are displayed?"""
        return self._wrappedData.spectrumView.displayNegativeContours

    @displayNegativeContours.setter
    def displayNegativeContours(self, value: bool):
        self._wrappedData.spectrumView.displayNegativeContours = value

    @property
    def positiveLevels(self) -> Tuple[float, ...]:
        """Positive contouring levels from lowest to highest"""
        number = self.positiveContourCount
        if number < 1:
            return tuple()

        result = [self.positiveContourBase]
        factor = self.positiveContourFactor
        result.extend(factor * result[-1] for _ in range(1, number))
        #
        return tuple(result)

    @property
    def negativeLevels(self) -> Tuple[float, ...]:
        """Negative contouring levels from lowest to highest"""
        number = self.negativeContourCount
        if number < 1:
            return tuple()

        result = [self.negativeContourBase]
        factor = self.negativeContourFactor
        result.extend(factor * result[-1] for _ in range(1, number))
        #
        return tuple(result)

    @property
    def sliceColour(self) -> str:
        """Colour for 1D slices and 1D spectra.

        If not set for SpectrumView gives you the value for Spectrum.
        If set for SpectrumView overrides Spectrum value.
        Set SpectrumView value to None to return to non-local value"""
        wrappedData = self._wrappedData.spectrumView
        result = wrappedData.sliceColour
        if result is None:
            obj = wrappedData.dataSource
            result = obj and obj.sliceColour
        return result

    @sliceColour.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def sliceColour(self, value: str):
        if not isinstance(value, (str, type(None))):
            raise ValueError("sliceColour must be a string/None.")

        self._guiChanged = True
        self._wrappedData.spectrumView.sliceColour = value

    #=========================================================================================
    # Spectrum properties in displayOrder; convenience methods
    #=========================================================================================

    @property
    def spectrum(self) -> Spectrum:
        """Spectrum that SpectrumView refers to"""
        return self._project._data2Obj.get(self._wrappedData.spectrumView.dataSource)

    @property
    def displayOrder(self) -> tuple:
        """A tuple of dimensions (1-based) in display order; 0 indicates a 1D 'intensity' dimension
        """
        return tuple(self._wrappedData.spectrumView.dimensionOrdering)

    @property
    def dimensions(self) -> tuple:
        """Spectrum dimensions in display order"""
        return tuple(dim for dim in self.displayOrder if dim > 0)

    @property
    def dimensionCount(self) -> int:
        """The number of displayed dimensions of spectrum"""
        return len(self.dimensions)

    @property
    def spectrumDimensions(self) -> tuple:
        """spectrumDimension objects in display order"""
        return tuple(self.spectrum.spectrumDimensions[idx] for idx in self.dimensionIndices)

    @property
    def dimensionIndices(self) -> tuple:
        """Spectrum dimension indices (0-based) in display order"""
        return tuple(dim - 1 for dim in self.dimensions)

    # deprecated
    # axisIndices = dimensionIndices
    # axes = axisIndices
    # dimensionOrdering = axisIndices

    @property
    def dimensionTypes(self) -> list:
        """Spectrum dimensionTypes in display order"""
        return [self.spectrum.dimensionTypes[idx] for idx in self.dimensionIndices]

    @property
    def axisCodes(self) -> list:
        """Spectrum axisCodes in display order"""
        return [self.spectrum.axisCodes[idx] for idx in self.dimensionIndices]

    @property
    def axesReversed(self) -> list:
        """Spectrum axesReversed in display order"""
        return [self.spectrum.axesReversed[idx] for idx in self.dimensionIndices]

    @property
    def isotopeCodes(self) -> list:
        """Spectrum isotopeCodes in display order"""
        return [self.spectrum.isotopeCodes[idx] for idx in self.dimensionIndices]

    @property
    def spectrumLimits(self) -> list:
        """Spectrum limits in display order"""
        _tmp = self.spectrum.spectrumLimits
        return [_tmp[idx] for idx in self.dimensionIndices]

    @property
    def aliasingLimits(self) -> list:
        """Spectrum aliasing limits in display order"""
        _tmp = self.spectrum.aliasingLimits
        return [_tmp[idx] for idx in self.dimensionIndices]

    @property
    def aliasingWidths(self) -> list:
        """Spectrum aliasing widths in display order"""
        _tmp = self.spectrum.aliasingLimits
        return [max(_tmp[idx]) - min(_tmp[idx]) for idx in self.dimensionIndices]

    @property
    def aliasingIndexes(self) -> list:
        """Spectrum aliasing indexes in display order"""
        _tmp = self.spectrum.aliasingIndexes
        return [_tmp[idx] for idx in self.dimensionIndices]

    @property
    def foldingLimits(self) -> list:
        """Spectrum folding limits in display order"""
        _tmp = self.spectrum.foldingLimits
        return [_tmp[idx] for idx in self.dimensionIndices]

    @property
    def foldingWidths(self) -> list:
        """Spectrum folding widths in display order"""
        _tmp = self.spectrum.foldingLimits
        return [max(_tmp[idx]) - min(_tmp[idx]) for idx in self.dimensionIndices]

    @property
    def foldingModes(self) -> list:
        """Spectrum folding modes in display order"""
        _tmp = self.spectrum.foldingModes
        return [_tmp[idx] for idx in self.dimensionIndices]

    @property
    def ppmPerPoints(self) -> list:
        """Spectrum ppm-per-points values in display order"""
        _tmp = self.spectrum.ppmPerPoints
        return [_tmp[idx] for idx in self.dimensionIndices]

    @property
    def ppmToPoints(self) -> list:
        """Spectrum ppm-to-points methods in display order"""
        _tmp = self.spectrum.ppmToPoints
        return [_tmp[idx] for idx in self.dimensionIndices]

    @property
    def isTimeDomains(self) -> list:
        """Spectrum isTimeDomains in display order"""
        _tmp = self.spectrum.isTimeDomains
        return [_tmp[idx] for idx in self.dimensionIndices]

    @property
    def spectralWidths(self):
        """Spectrum widths in display order"""
        _tmp = self.spectrum.spectralWidths
        return [_tmp[idx] for idx in self.dimensionIndices]

    @property
    def spectrometerFrequencies(self):
        """SpectrometerFrequencies in display order"""
        _tmp = self.spectrum.spectrometerFrequencies
        return [_tmp[idx] for idx in self.dimensionIndices]

    @property
    def pointCounts(self):
        """Spectrum point counts in display order"""
        _tmp = self.spectrum.pointCounts
        return [_tmp[idx] for idx in self.dimensionIndices]

    def _getByDisplayOrder(self, parameterName) -> list:
        """Return parameter in displayOrder"""
        # dims = [d for d in self.dimensions if d > 0]  # Filter the '0' dimension of 1D
        return list(self.spectrum.getByDimensions(parameterName=parameterName, dimensions=self.dimensions))

    def _getPointPosition(self, ppmPostions) -> tuple:
        """Convert the ppm-positions vector (in display order) to a position (1-based) vector
        in spectrum-dimension order, suitable to be used with getPlaneData
        """
        position = [1] * self.spectrum.dimensionCount
        for dim, ppmValue in zip(self.dimensions, ppmPostions):
            if dim > 0:
                # Intensity dimensions have dim=0, or axis=-1;
                p = self.spectrum.ppm2point(value=ppmValue, dimension=dim)
                position[dim - 1] = int(p + 0.5)

        return tuple(position)

    def _extractXYplaneToFile(self, ppmPositions):
        """Extract an XY (display order) plane
        :return Spectrum instance
        """
        position = self._getPointPosition(ppmPositions)
        axisCodes = self.axisCodes[:2]
        return self.spectrum.extractPlaneToFile(axisCodes=axisCodes, position=position)

    #=========================================================================================
    # property STUBS: hot-fixed later
    #=========================================================================================

    @property
    def integralListViews(self) -> list['IntegralListView']:
        """STUB: hot-fixed later
        :return: a list of integralListViews in the SpectrumView
        """
        return []

    @property
    def integralViews(self) -> list['IntegralView']:
        """STUB: hot-fixed later
        :return: a list of integralViews in the SpectrumView
        """
        return []

    @property
    def multipletListViews(self) -> list['MultipletListView']:
        """STUB: hot-fixed later
        :return: a list of multipletListViews in the SpectrumView
        """
        return []

    @property
    def multipletViews(self) -> list['MultipletView']:
        """STUB: hot-fixed later
        :return: a list of multipletViews in the SpectrumView
        """
        return []

    @property
    def peakListViews(self) -> list['PeakListView']:
        """STUB: hot-fixed later
        :return: a list of peakListViews in the SpectrumView
        """
        return []

    @property
    def peakViews(self) -> list['PeakView']:
        """STUB: hot-fixed later
        :return: a list of peakViews in the SpectrumView
        """
        return []

    #=========================================================================================
    # getter STUBS: hot-fixed later
    #=========================================================================================

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

    #=========================================================================================
    # Implementation methods
    #=========================================================================================

    @classmethod
    def _getAllWrappedData(cls, parent: Strip) -> list:
        """get wrappedData (ccpnmr.gui.Task.SpectrumView) in serial number order
        """
        return sorted(parent._wrappedData.stripSpectrumViews,
                      key=operator.attrgetter('spectrumView.spectrumName'))

    @ccpNmrV3CoreUndoBlock()
    def clearContourAttributes(self):
        """Clear all the contour attributes associated with the spectrumView
        Attributes will revert to the spectrum values
        """
        _spectrum = self.spectrum
        for param in self._CONTOURATTRIBUTELIST.split():
            if hasattr(_spectrum, param):
                setattr(self, param, None)

    @ccpNmrV3CoreUndoBlock()
    def copyContourAttributesFromSpectrum(self):
        """Copy all the contour attributes associated with the spectrumView.spectrum
        to the spectrumView
        """
        _spectrum = self.spectrum
        for param in self._CONTOURATTRIBUTELIST.split():
            if hasattr(_spectrum, param):
                value = getattr(_spectrum, param)
                setattr(self, param, value)

    @property
    def _index(self):
        """Return the index of the spectrumView in display order
        """
        return self._wrappedData.spectrumView.index

    @_index.setter
    def _index(self, value):
        if not (isinstance(value, int) and value >= 0):
            raise ValueError('_index must be a non-negative int')
        self._wrappedData.spectrumView.index = value


#=========================================================================================
# New method
#=========================================================================================

# @newObject(SpectrumView)
# Cannot use the decorator
# """
#   File "/Users/geerten/Code/CCPNv3/CcpNmr/src/python/ccpn/core/lib/ContextManagers.py", line 638, in theDecorator
#     apiObjectsCreated = result._getApiObjectTree()
#   File "/Users/geerten/Code/CCPNv3/CcpNmr/src/python/ccpn/core/_implementation/AbstractWrapperObject.py", line 683, in _getApiObjectTree
#     obj._checkDelete(apiObjectlist, objsToBeChecked, linkCounter, topObjectsToCheck)  # This builds the list/set
#   File "/Users/geerten/Code/CCPNv3/CcpNmr/src/python/ccpnmodel/ccpncore/api/ccpnmr/gui/Task.py", line 28366, in _checkDelete
#     raise ApiError("StripSpectrumView %s: StripSpectrumViews can only be deleted when the SpectrumView or Strip is deleted." % self)
# ccpnmodel.ccpncore.memops.ApiError.ApiError: StripSpectrumView <ccpnmr.gui.Task.StripSpectrumView ['user', 'View', '1D_H', 1, <ccpnmr.gui.Task.SpectrumView ['user', 'View', '1D_H', 'AcetatePE', 0]>]>: StripSpectrumViews can only be deleted when the SpectrumView or Strip is deleted.
# """


# NOTE:ED - this is the less complicated decorator
#   newObject causes an api crash reading the apiTree :|
#   not strictly needed as the spectrumViews are not undoable, but requires the notifier
@newV3Object()
def _newSpectrumView(display, spectrum, displayOrder) -> SpectrumView:
    """Create new SpectrumView
    :param spectrum: A Spectrum instance
    :param displayOrder: A tuple/list of spectrum dimensions (1-based) or 0 (For intensity) in display order
    :returns: SpectrumView instance
    """
    # # Set stripSerial
    # if 'Free' in apiStrip.className:
    #     # Independent strips
    #     stripSerial = apiStrip.serial
    # else:
    #     stripSerial = 0

    if not isinstance(spectrum, Spectrum):
        raise ValueError('invalid spectrum; got %r' % spectrum)

    if not isinstance(displayOrder, (list, tuple)) or len(displayOrder) < 2:
        raise ValueError('invalid displayOrder; got %r' % displayOrder)

    obj = display._wrappedData.newSpectrumView(spectrumName=spectrum.name,
                                               stripSerial=0,
                                               dataSource=spectrum._wrappedData,
                                               dimensionOrdering=displayOrder)

    # 20191113:ED testing - doesn't work yet, _data2Obj not created in correct place
    # GWV: don't know why, but only querying via the FindFirstStripSpectrumView seems to allow to yield the V2 object
    apiSpectrumView = display.strips[0]._wrappedData.findFirstStripSpectrumView(spectrumView=obj)
    newSpecView = display.project._data2Obj.get(apiSpectrumView)

    if newSpecView is None:
        raise RuntimeError('Failed to generate new SpectrumView instance')

    # NOTE:ED - 2021oct25 - @GWV not sure why this is here as overrides the .getter logic
    #   replaced with method
    # newSpecView.copyContourAttributesFromSpectrum()

    return newSpecView


#=========================================================================================
# Notifiers:
#=========================================================================================

# Notify SpectrumView change when ApiSpectrumView changes (underlying object is StripSpectrumView)
Project._apiNotifiers.append(
        ('_notifyRelatedApiObject', {'pathToObject': 'stripSpectrumViews', 'action': 'change'},
         ApiSpectrumView._metaclass.qualifiedName(), '')
        )

#EJB 20181122: moved to Spectrum
# Notify SpectrumView change when Spectrum changes
# Bloody hell: as far as GWV understands the effect of this: a 'change' to a Spectrum object triggers
# a _finaliseAction('change') on each of the spectrum.spectrumViews objects, which then calls all
# ('SpectrumView','change') notifiers
# Spectrum._setupCoreNotifier('change', AbstractWrapperObject._finaliseRelatedObject,
#                             {'pathToObject': 'spectrumViews', 'action': 'change'})

# Links to SpectrumView and Spectrum are fixed after creation - any link notifiers should be put in
# create/destroy instead
