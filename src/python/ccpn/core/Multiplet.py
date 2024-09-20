"""
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
__dateModified__ = "$dateModified: 2024-05-22 14:42:25 +0100 (Wed, May 22, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: Ed Brooksbank $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"

from itertools import chain

#=========================================================================================
# Start of code
#=========================================================================================

import numpy as np
from typing import Optional, Tuple, Any, Union, Sequence, List

from ccpnmodel.ccpncore.api.ccp.nmr import Nmr
from ccpnmodel.ccpncore.api.ccp.nmr.Nmr import Multiplet as ApiMultiplet
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core.Project import Project
from ccpn.core.Peak import Peak
from ccpn.core.MultipletList import MultipletList
from ccpn.core.lib.ContextManagers import newObject, ccpNmrV3CoreSetter, undoBlock
from ccpn.util.Common import makeIterableList
from ccpn.util.decorators import logCommand


MULTIPLET_TYPES = ['singlet', 'doublet', 'triplet', 'quartet', 'quintet', 'sextet', 'septet', 'octet', 'nonet',
                   'doublet of doublets', 'doublet of triplets', 'triplet of doublets',
                   'doublet of doublet of doublets']


def _calculateCenterOfMass(multiplet):
    """Calculate the centre of mass of the multiplet peaks
    :param multiplet: multiplet obj containing peaks.
    :return: the center of mass of the multiplet that can be used as peak position
             if you consider the multiplet as a single peak
    """

    try:
        _peaks = multiplet.peaks
        _lenPeaks = len(_peaks)
        if _lenPeaks > 0:
            position = ()
            dim = multiplet.multipletList.spectrum.dimensionCount
            if dim > 1:
                for d in range(dim):
                    peakPositions = [peak.position[d] for peak in _peaks]
                    # peakIntensities = [peak.height or 1 for peak in peaks]
                    # numerator = []
                    # for p, i in zip(peakPositions, peakIntensities):
                    #     numerator.append(p * i)
                    # centerOfMass = sum(numerator) / sum(peakIntensities)
                    # position += (centerOfMass,)

                    position += (sum(peakPositions) / _lenPeaks,)
            else:
                position = (sum(peak.position[0] for peak in _peaks) / _lenPeaks,
                            sum(peak.height for peak in _peaks) / _lenPeaks,)
            return position
    except Exception:
        return None


def _calculateCenterOfMassPoints(multiplet):
    """Calculate the centre of mass of the multiplet peaks (in points)
    :param multiplet: multiplet obj containing peaks.
    :return: the center of mass of the multiplet that can be used as peak position
             if you consider the multiplet as a single peak
    """

    try:
        pks = multiplet.peaks
        if len(pks) > 0:
            position = ()
            dim = multiplet.multipletList.spectrum.dimensionCount
            if dim > 1:
                for d in range(dim):
                    peakPoints = list(filter(lambda vv: vv is not None, [peak.pointPositions[d] for peak in pks]))
                    position += (sum(peakPoints) / len(peakPoints),)
            else:
                # 1d multiplet - add the height for the other dimension
                peakPoints = list(filter(lambda vv: vv is not None, [peak.pointPositions[0] for peak in pks]))
                heights = list(filter(lambda vv: vv is not None, [peak.height for peak in pks]))
                position = (sum(peakPoints) / len(peakPoints),
                            sum(heights) / len(heights))
            return position
    except Exception:
        return None


def _getMultipletHeight(multiplet):
    """Derive the highest peak intensity from the multiplet peaks"""
    # NOTE:ED - a more accurate method may be needed here
    if len(multiplet.peaks) > 0:
        heights = [(peak.height or 0.0) for peak in multiplet.peaks]
        return np.sum(heights)


def _getMultipletHeightError(multiplet):
    """Derive the height error from the multiplet peaks"""
    if len(multiplet.peaks) > 0:
        heightErrors = [(peak.heightError or 0.0) for peak in multiplet.peaks]
        return np.sum(heightErrors)


class Multiplet(AbstractWrapperObject):
    """Multiplet object, holding position, intensity, and assignment information

    Measurements that require more than one NmrAtom for an individual assignment
    (such as  splittings, J-couplings, MQ dimensions, reduced-dimensionality
    experiments etc.) are not supported (yet). Assignments can be viewed and set
    either as a list of assignments for each dimension (dimensionNmrAtoms) or as a
    list of all possible assignment combinations (assignedNmrAtoms)"""

    #: Short class name, for PID.
    shortClassName = 'MT'
    # Attribute it necessary as subclasses must use superclass className
    className = 'Multiplet'

    _parentClass = MultipletList

    #: Name of plural link to instances of class
    _pluralLinkName = 'multiplets'

    #: List of child classes.
    _childClasses = []

    # Qualified name of matching API class
    _apiClassQualifiedName = ApiMultiplet._metaclass.qualifiedName()

    # the attribute name used by current
    _currentAttributeName = 'multiplets'

    # CCPN properties
    @property
    def _apiMultiplet(self) -> ApiMultiplet:
        """API multiplets matching Multiplet."""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """id string - serial number converted to string."""
        return str(self._wrappedData.serial)

    @property
    def serial(self) -> int:
        """serial number of Multiplet, used in Pid and to identify the Multiplet."""
        return self._wrappedData.serial

    @property
    def _parent(self) -> Optional[MultipletList]:
        """parent containing multiplet."""
        return self._project._data2Obj[self._wrappedData.multipletList]

    multipletList = _parent

    @property
    def spectrum(self):
        """Convenience property to get the spectrum, equivalent to peak.peakList.spectrum
        """
        return self.multipletList.spectrum

    @property
    def height(self) -> Optional[float]:
        """height of Multiplet."""
        try:
            if pks := self.peaks:
                heights = [peak.height for peak in pks]
                return sum(heights)

        except TypeError:
            # peaks contains values that are None
            return None

    # # cannot set the height - derived from peaks
    # @height.setter
    # def height(self, value: float):
    #     self._wrappedData.height = value

    @property
    def heightError(self) -> Optional[float]:
        """height error of Multiplet."""
        try:
            if pks := self.peaks:
                errors = [peak.heightError for peak in pks]
                return sum(errors)

        except TypeError:
            # peaks contains values that are None
            return None

    # # cannot set the heightError - derived from peaks
    # @heightError.setter
    # def heightError(self, value: float):
    #     self._wrappedData.heightError = value

    @property
    def volume(self) -> Optional[float]:
        """Volume of multiplet."""
        try:
            if pks := self.peaks:
                errors = [peak.volume for peak in pks]
                return sum(errors)

        except TypeError:
            # peaks contains values that are None
            return None

    # @property
    # def volume(self) -> Optional[float]:
    #     """volume of Multiplet."""
    #     if self._wrappedData.volume is None:
    #         return None
    #
    #     scale = self.multipletList.spectrum.scale
    #     scale = scale if scale is not None else 1.0
    #     if -SCALETOLERANCE < scale < SCALETOLERANCE:
    #         getLogger().warning(
    #             f'Scaling {self}.volume by minimum tolerance (±{SCALETOLERANCE})'
    #         )
    #
    #     return self._wrappedData.volume * scale
    #
    # @volume.setter
    # @logCommand(get='self', isProperty=True)
    # def volume(self, value: Union[float, int, None]):
    #     if not isinstance(value, (float, int, type(None))):
    #         raise TypeError('volume must be a float, integer or None')
    #     elif value is not None and (value - value) != 0.0:
    #         raise TypeError('volume cannot be NaN or Infinity')
    #
    #     if value is None:
    #         self._wrappedData.volume = None
    #     else:
    #         scale = self.multipletList.spectrum.scale
    #         scale = scale if scale is not None else 1.0
    #         if -SCALETOLERANCE < scale < SCALETOLERANCE:
    #             getLogger().warning(
    #                 f'Scaling {self}.volume by minimum tolerance (±{SCALETOLERANCE})'
    #             )
    #             self._wrappedData.volume = None
    #         else:
    #             self._wrappedData.volume = float(value) / scale

    @property
    def offset(self) -> Optional[float]:
        """offset of Multiplet."""
        return self._wrappedData.offset

    @offset.setter
    @logCommand(get='self', isProperty=True)
    def offset(self, value: float):
        self._wrappedData.offset = value

    @property
    def constraintWeight(self) -> Optional[float]:
        """constraintWeight of Multiplet."""
        return self._wrappedData.constraintWeight

    @constraintWeight.setter
    @logCommand(get='self', isProperty=True)
    def constraintWeight(self, value: float):
        self._wrappedData.constraintWeight = value

    @property
    def volumeError(self) -> Optional[float]:
        """volume error of Multiplet."""
        try:
            if pks := self.peaks:
                errors = [peak.volumeError for peak in pks]
                return sum(errors)

        except TypeError:
            # peaks contains values that are None
            return None

    # @property
    # def volumeError(self) -> Optional[float]:
    #     """volume error of Multiplet."""
    #     if self._wrappedData.volumeError is None:
    #         return None
    #
    #     scale = self.multipletList.spectrum.scale
    #     scale = scale if scale is not None else 1.0
    #     if -SCALETOLERANCE < scale < SCALETOLERANCE:
    #         getLogger().warning(
    #             f'Scaling {self}.volumeError by minimum tolerance (±{SCALETOLERANCE})'
    #         )
    #
    #     return self._wrappedData.volumeError * scale
    #
    # @volumeError.setter
    # @logCommand(get='self', isProperty=True)
    # def volumeError(self, value: Union[float, int, None]):
    #     if not isinstance(value, (float, int, type(None))):
    #         raise TypeError('volumeError must be a float, integer or None')
    #     elif value is not None and (value - value) != 0.0:
    #         raise TypeError('volumeError cannot be NaN or Infinity')
    #
    #     if value is None:
    #         self._wrappedData.volumeError = None
    #     else:
    #         scale = self.multipletList.spectrum.scale
    #         scale = scale if scale is not None else 1.0
    #         if -SCALETOLERANCE < scale < SCALETOLERANCE:
    #             getLogger().warning(
    #                 f'Scaling {self}.volumeError by minimum tolerance (±{SCALETOLERANCE})'
    #             )
    #             self._wrappedData.volumeError = None
    #         else:
    #             self._wrappedData.volumeError = float(value) / scale

    @property
    def figureOfMerit(self) -> Optional[float]:
        """figureOfMerit of Multiplet, between 0.0 and 1.0 inclusive."""
        return self._wrappedData.figOfMerit

    @figureOfMerit.setter
    @logCommand(get='self', isProperty=True)
    def figureOfMerit(self, value: float):
        self._wrappedData.figOfMerit = value

    @property
    def annotation(self) -> Optional[str]:
        """Multiplet text annotation."""
        return self._wrappedData.annotation

    @annotation.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def annotation(self, value: Optional[str]):
        if not isinstance(value, (str, type(None))):
            raise ValueError("annotation must be a string or None")
        else:
            self._wrappedData.annotation = value

    @property
    def slopes(self) -> List[float]:
        """slope (in dimension order) used in calculating multiplet value."""
        return self._wrappedData.slopes

    @slopes.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def slopes(self, value):
        self._wrappedData.slopes = value

    @property
    def limits(self) -> List[Tuple[float, float]]:
        """limits (in dimension order) of the multiplet."""
        return self._wrappedData.limits

    @limits.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def limits(self, value):
        self._wrappedData.limits = value

    @property
    def pointLimits(self) -> List[Tuple[float, float]]:
        """pointLimits (in dimension order) of the multiplet."""
        return self._wrappedData.pointLimits

    @pointLimits.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def pointLimits(self, value):
        self._wrappedData.pointLimits = value

    @property
    def axisCodes(self) -> Tuple[str, ...]:
        """Spectrum axis codes in dimension order matching position."""
        return self.multipletList.spectrum.axisCodes

    @property
    def peaks(self) -> Tuple[Any, ...]:
        """List of peaks attached to the multiplet."""
        if self._wrappedData:
            _data2Obj = self._project._data2Obj
            return tuple(
                    _data2Obj[pk]
                    for pk in self._wrappedData.sortedPeaks()
                    if pk in _data2Obj
                    )
        else:
            return ()

    @peaks.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def peaks(self, ll: list):
        if not ll:
            return

        pll = makeIterableList(ll)
        pks = [self.project.getByPid(peak) if isinstance(peak, str) else peak for peak in pll]
        for pp in pks:
            if not isinstance(pp, Peak):
                raise TypeError(f'{pp} is not of type Peak')

        toRemove = [pk for pk in self.peaks if pk not in pks]
        toAdd = [pk for pk in pks if pk not in self.peaks]
        self.removePeaks(toRemove)
        self.addPeaks(toAdd)

    @property
    def numPeaks(self) -> int:
        """return number of peaks in the multiplet."""
        return len(self._wrappedData.sortedPeaks())

    @property
    def position(self) -> Optional[Tuple[float, ...]]:
        """Multiplet position in ppm (or other relevant unit) in dimension order calculated as Center Of Mass.
        """
        return _calculateCenterOfMass(self)

    ppmPositions = position

    # @property
    # def ppmPositions(self) -> Optional[Tuple[float, ...]]:
    #     """Peak position in ppm (or other relevant unit) in dimension order calculated as Center Of Mass."""
    #     result = None
    #     try:
    #         pks = self.peaks
    #         # pksPos = [pp.position for pp in pks]
    #         if pks:
    #             # self._position = tuple(sum(item) for item in zip(*pksPos))
    #             self._position = _calculateCenterOfMass(self)
    #             result = self._position
    #
    #     finally:
    #         return result

    @property
    def positionError(self) -> Tuple[Optional[float], ...]:
        """Peak position error in ppm (or other relevant unit)."""
        # TODO:LUCA calculate this :)
        return ()  # tuple(x.valueError for x in self._wrappedData.sortedPeaks())

    @property
    def pointPositions(self) -> Optional[Tuple[float, ...]]:
        """Multiplet position in points (or other relevant unit) in dimension order calculated as Center Of Mass.
        """
        return _calculateCenterOfMassPoints(self)

    @property
    def boxWidths(self) -> Tuple[Optional[float], ...]:
        """The full width of the peak footprint in points for each dimension,
        i.e. the width of the area that should be considered for integration, fitting, etc. ."""
        return tuple(x.boxWidth for x in self._wrappedData.sortedPeaks())

    @property
    def lineWidths(self) -> Tuple[Optional[float], ...]:
        """Full-width-half-height of peak/multiplet for each dimension.
        """
        result = ()
        pks = self.peaks
        pksWidths = [pp.lineWidths for pp in pks]
        try:
            result = tuple(sum(item) for item in zip(*pksWidths))
        except Exception:
            if pks:
                result = list(pksWidths[0])
                for otherPks in pksWidths[1:]:
                    for ii in range(len(result)):
                        result[ii] += otherPks[ii]
            else:
                result = self._wrappedData.lineWidths
        finally:
            return result

    @lineWidths.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def lineWidths(self, value):
        # NOTE:ED - check value is a tuple, etc.
        self._wrappedData.lineWidths = value

    # check what the peak is doing
    ppmLineWidths = lineWidths

    @property
    def pointLineWidths(self) -> Tuple[Optional[float], ...]:
        """Full-width-half-height of peak for each dimension, in points."""
        # assumes that internal storage is in ppm
        result = ()
        pks = self.peaks
        pksWidths = [pp.pointLineWidths for pp in pks]
        try:
            result = tuple(sum(item) for item in zip(*pksWidths))
        except Exception:
            if pks:
                result = list(pksWidths[0])
                for otherPks in pksWidths[1:]:
                    for ii in range(len(result)):
                        result[ii] += otherPks[ii]
            else:
                result = self._wrappedData.lineWidths
        finally:
            return result

    @property
    def aliasing(self) -> Tuple[Optional[float], ...]:
        """Aliasing."""
        # Returns the aliasing for first connected peak
        # quickest for the moment - need to imagine case where peaks are not from the same aliased region
        if self.peaks:
            return self.peaks[0].aliasing

    @property
    def multipletViews(self) -> list:
        """STUB: hot-fixed later"""
        return []

    #=========================================================================================
    # Implementation functions
    #=========================================================================================

    # from ccpnmodel.ccpncore.api.memops import Implementation as ApiImplementation
    #
    # def __init__(self, project: 'Project', wrappedData: ApiImplementation.DataObject):
    #     super().__init__(project, wrappedData)
    #
    #     # attach a notifier to the peaks
    #     from ccpn.core.lib.Notifiers import Notifier
    #
    #     for pp in self.peaks:
    #         Notifier(pp, ['observe'], Notifier.ANY,
    #                  callback=self._propagateAction,
    #                  onceOnly=True, debug=True)

    @classmethod
    def _getAllWrappedData(cls, parent: MultipletList) -> list[ApiMultiplet]:
        """get wrappedData (Multiplets) for all Multiplet children of parent MultipletList"""
        return parent._wrappedData.sortedMultiplets()

    def _finaliseAction(self, action: str, **actionKwds):
        """Subclassed to handle associated multiplets
        """
        if not super()._finaliseAction(action, **actionKwds):
            return

        # use fromPeak/Multiplet to stop infinite loops
        actionKwds['fromMultiplet'] = self
        if action in {'change', 'create', 'delete'} and not actionKwds.get('fromPeak'):
            for pk in self.peaks:
                pk._finaliseAction('change', **actionKwds)

    # @classmethod
    # def _restoreObject(cls, project, apiObj):
    #     """Restore the object and update peaks.
    #     """
    #     from functools import reduce
    #     from operator import add
    #
    #     result = super()._restoreObject(project, apiObj)
    #
    #     dims = result.spectrum.dimensionCount
    #     try:
    #         print(f'assignments   {result}    {[pk.assignedNmrAtoms for pk in result.peaks]}')
    #         if any(pk.assignedNmrAtoms for pk in result.peaks):
    #         # ss = [reduce(add, (pk.assignedNmrAtoms[ind] for pk in result.peaks if pk.assignedNmrAtoms)) for ind in range(dims)]
    #             print(f'{result}    {dims}  {result.peaks}')
    #     except Exception as es:
    #         print(es)

    #=========================================================================================
    # CCPN functions
    #=========================================================================================

    @logCommand(get='self')
    def addPeaks(self, peaks: Sequence[Union['Peak', str]]):
        """
        Add a peak or list of peaks to the Multiplet.
        The peaks must belong to the spectrum containing the multipletList.

        :param peaks: single peak or list of peaks as objects or pids.
        """
        spectrum = self._parent.spectrum
        peakList = makeIterableList(peaks)
        pks = [
            self.project.getByPid(peak) if isinstance(peak, str) else peak
            for peak in peakList
            ]
        for pp in pks:
            if not isinstance(pp, Peak):
                raise TypeError(f'addPeaks: {pp} is not of type Peak')
            if pp not in spectrum.peaks:
                raise ValueError(f'addPeaks: {pp.pid} does not belong to spectrum: {spectrum.pid}')
            if pp.multiplets:
                raise ValueError(f'addPeaks: {pp.pid} is already in a multiplet')

        with undoBlock():
            for pk in pks:
                if pk not in self.peaks:
                    # ignore duplicates
                    self._wrappedData.addPeak(pk._wrappedData)

    @logCommand(get='self')
    def _forcePeaks(self, peaks: Sequence[Union['Peak', str]]):
        """
        Add a peak or list of peaks to the Multiplet.
        The peaks must belong to the spectrum containing the multipletList.

        :param peaks: single peak or list of peaks as objects or pids.
        """
        spectrum = self._parent.spectrum
        peakList = makeIterableList(peaks)
        pks = [
            self.project.getByPid(peak) if isinstance(peak, str) else peak
            for peak in peakList
            ]
        for pp in pks:
            if not isinstance(pp, Peak):
                raise TypeError(f'addPeaks: {pp} is not of type Peak')
            if pp not in spectrum.peaks:
                raise ValueError(f'addPeaks: {pp.pid} does not belong to spectrum: {spectrum.pid}')

        with undoBlock():
            for pk in pks:
                if pk not in self.peaks:
                    # ignore duplicates
                    self._wrappedData.addPeak(pk._wrappedData)

    @logCommand(get='self')
    def _forcePeaks(self, peaks: Sequence[Union['Peak', str]]):
        """
        Add a peak or list of peaks to the Multiplet.
        The peaks must belong to the spectrum containing the multipletList.

        :param peaks: single peak or list of peaks as objects or pids.
        """
        spectrum = self._parent.spectrum
        peakList = makeIterableList(peaks)
        pks = [
            self.project.getByPid(peak) if isinstance(peak, str) else peak
            for peak in peakList
            ]
        for pp in pks:
            if not isinstance(pp, Peak):
                raise TypeError(f'addPeaks: {pp} is not of type Peak')
            if pp not in spectrum.peaks:
                raise ValueError(f'addPeaks: {pp.pid} does not belong to spectrum: {spectrum.pid}')

        with undoBlock():
            for pk in pks:
                if pk not in self.peaks:
                    # ignore duplicates
                    self._wrappedData.addPeak(pk._wrappedData)

    @logCommand(get='self')
    def removePeaks(self, peaks: Sequence[Union['Peak', str]]):
        """
        Remove a peak or list of peaks from the Multiplet.
        The peaks must belong to the multiplet.

        :param peaks: single peak or list of peaks as objects or pids
        """
        spectrum = self._parent.spectrum
        peakList = makeIterableList(peaks)
        pks = [
            self.project.getByPid(peak) if isinstance(peak, str) else peak
            for peak in peakList
            ]
        for pp in pks:
            if not isinstance(pp, Peak):
                raise TypeError(f'removePeaks: {pp} is not of type Peak')
            if pp not in self.peaks:
                raise ValueError(f'removePeaks: {pp.pid} does not belong to multiplet: {self.pid}')
            if pp not in spectrum.peaks:
                raise ValueError(f'removePeaks: {pp.pid} does not belong to spectrum: {spectrum.pid}')

        with undoBlock():
            for pk in pks:
                self._wrappedData.removePeak(pk._wrappedData)

            # leaves single component multiplet (however makes GUI interaction impossible)
            if self.numPeaks < 1:
                self.delete()

    def _propagateAction(self, data):
        from ccpn.core.lib.Notifiers import Notifier

        trigger = data[Notifier.TRIGGER]

        trigger = 'change' if trigger == 'observe' else trigger
        if trigger in ['change']:
            self._finaliseAction(trigger)

    @logCommand(get='self')
    def mergeOnlyMultiplets(self, multiplets: list['Multiplet']):
        """Merge a list of multiplets and their peaks into this multiplet

        Note: All multiplets other than this one is deleted after merging
        all the peaks.

        :param multiplets: a list of peaks to be merged into the multiplet.
        """
        with undoBlock():
            for mp in multiplets:
                if mp is not self:
                    pkAdd = mp.peaks
                    mp.removePeaks(mp.peaks)  # empty multiplet should be deleted here.
                    self.addPeaks(pkAdd)

    @logCommand(get='self')
    def mergeMultiplets(self, peaks : list[Peak], multiplets : list['Multiplet']):
        """Merge any combination of multiplet and peak objects together.

        Note: if a peak is currently in another multiplet it will not merge unless
        that multiplet is also selected.

        :param peaks: a list of peaks to be merged into the multiplet
        :param multiplets: a lift of multiplets to merged into the current multiplet
        """
        alonePeaks = [pk for pk in peaks if not pk.multiplets]

        with undoBlock():
            self.mergeOnlyMultiplets(multiplets)
            self.addPeaks(alonePeaks)
            self._unifyAssignments()

    #===========================================================================================
    # new<Object> and other methods
    # Call appropriate routines in their respective locations
    #===========================================================================================

    def _unifyAssignments(self):
        """Force all peaks in the multiplet to share assignments"""
        # if 1 peak or less, then there is nothing to unify.
        if len(self.peaks) <= 1:
            return

        axisCodes = self.axisCodes
        assignments = [[] for _ in axisCodes]
        for pk in self.peaks:
            dimensionMapping = pk.spectrum.getByAxisCodes('dimensions', axisCodes, exactMatch=False)
            if pk.assignedNmrAtoms:
                a = pk.getByDimensions('assignedNmrAtoms', dimensionMapping)
                for ll in a:
                    for dim, assign in enumerate(assignments):
                        if ll[dim] not in assign and ll[dim] is not None:
                            assign.append(ll[dim])

        for pk in self.peaks:
            pk.assignDimensions(axisCodes, assignments)

#=========================================================================================
# Connections to parents
#=========================================================================================

@newObject(Multiplet)
def _newAPIMultiplet(self: MultipletList,
                     height: float = 0.0, heightError: float = 0.0,
                     volume: float = 0.0, volumeError: float = 0.0,
                     offset: float = 0.0, constraintWeight: float = 0.0,
                     figureOfMerit: float = 1.0, annotation: str = None, comment: str = None,
                     limits: Sequence[Tuple[float, float]] = (), slopes: List[float] = (),
                     pointLimits: Sequence[Tuple[float, float]] = (),
                     peaks: Sequence[Union['Peak', str]] = ()) -> Multiplet:
    """Create a new api Multiplet within a multipletList
    Note: does not do assignments for peaks (see _newMultiplet)
    mostly exists to allow proper undo blocking for _newMultiplet

    See the Multiplet class for details.

    :param height:
    :param heightError:
    :param volume:
    :param volumeError:
    :param offset:
    :param constraintWeight:
    :param figureOfMerit:
    :param annotation:
    :param comment:
    :param limits:
    :param slopes:
    :param pointLimits:
    :param peaks:
    :return: a new Multiplet instance.
    """

    spectrum = self.spectrum
    peakList = makeIterableList(peaks)
    pks = [self.project.getByPid(peak) if isinstance(peak, str) else peak
           for peak in peakList]

    for pp in pks:
        if not isinstance(pp, Peak):
            raise TypeError(f'newMultiplet: {pp} is not of type Peak')
        if pp not in spectrum.peaks:
            raise ValueError(f'newMultiplet: {pp.pid} does not belong to spectrum {spectrum.pid}')
        if pp.multiplets:
            raise ValueError(f'newMultiplet: {pp.pid} is already in a multiplet')

    dd = {'height'    : height, 'heightError': heightError,
          'volume'    : volume, 'volumeError': volumeError, 'offset': offset, 'slopes': slopes,
          'figOfMerit': figureOfMerit, 'constraintWeight': constraintWeight,
          'annotation': annotation, 'details': comment,
          'limits'    : limits, 'pointLimits': pointLimits}
    if pks:
        dd['peaks'] = [pk._wrappedData for pk in pks]

    # remove items that can't be set to None in the model
    if not offset:
        del dd['offset']
    if not constraintWeight:
        del dd['constraintWeight']

    apiParent = self._apiMultipletList
    apiMultiplet = apiParent.newMultiplet(multipletType='multiplet', **dd)
    result = self._project._data2Obj.get(apiMultiplet)
    if result is None:
        raise RuntimeError('Unable to generate new Multiplet item')

    return result

# changed after multiplet discussion feb 2 2024
# def _assignNewMultipletPeaks(self, peaks):
#     peakList = makeIterableList(peaks)
#     pks = [self.project.getByPid(peak) if isinstance(peak, str) else peak
#            for peak in peakList]
#
#     for pp in pks:
#         if not isinstance(pp, Peak):
#             raise TypeError(f'newMultiplet: {pp} is not of type Peak')
#
#     assignment = []
#     doAssign = False
#     for pk in pks:
#         tempAssign = pk.assignedNmrAtoms
#         if not assignment:  # nothing assigned yet
#             assignment = tempAssign
#             assignPeak = pk
#             doAssign = True
#             # assignPeak = {'peak': pk, 'assigns': pk.assignedNmrAtoms}
#         elif assignment != tempAssign and len(tempAssign) != 0:  # if non matching assigned that isnt empty
#             doAssign = False
#             break
#
#     if doAssign:
#         for pk in pks:
#             assignPeak.copyAssignmentTo(pk)


def _newMultiplet(self: MultipletList,
                  height: float = 0.0, heightError: float = 0.0,
                  volume: float = 0.0, volumeError: float = 0.0,
                  offset: float = 0.0, constraintWeight: float = 0.0,
                  figureOfMerit: float = 1.0, annotation: str = None, comment: str = None,
                  limits: Sequence[Tuple[float, float]] = (), slopes: List[float] = (),
                  pointLimits: Sequence[Tuple[float, float]] = (),
                  peaks: Sequence[Union['Peak', str]] = ()) -> Multiplet:
    """
    Create a new Multiplet within a multiplet list

    Note: If there is only one assigned peak or if multiple assigned peaks
    have the same assignment, then copy that assignment to any other non-assigned
    constituent peaks.

    :param self:
    :param height:
    :param heightError:
    :param volume:
    :param volumeError:
    :param offset:
    :param constraintWeight:
    :param figureOfMerit:
    :param annotation:
    :param comment:
    :param limits:
    :param slopes:
    :param pointLimits:
    :param peaks:
    :return:
    """
    with undoBlock():
        result = _newAPIMultiplet(**locals())
        result._unifyAssignments()
        return result


# EJB 20181127: removed
# Multiplet._parentClass.newMultiplet = _newMultiplet
# del _newMultiplet

# EJB 20181128: removed, to be added to multiplet __init__?
# Notify Multiplets when the contents of peaks have changed
# i.e. PeakDim references
Project._apiNotifiers.append(
        ('_notifyRelatedApiObject', {'pathToObject': 'peak.multiplets', 'action': 'change'},
         Nmr.PeakDim._metaclass.qualifiedName(), '')
        )
