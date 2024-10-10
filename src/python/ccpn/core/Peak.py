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
__dateModified__ = "$dateModified: 2024-10-04 12:05:03 +0100 (Fri, October 04, 2024) $"
__version__ = "$Revision: 3.2.5 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import itertools
import operator
import numpy as np
from functools import partial
from typing import Optional, Tuple, Union, Sequence, Any, List
import pandas as pd
from ccpn.util import Common as commonUtil
from ccpn.core._implementation.AbstractWrapperObject import AbstractWrapperObject
from ccpn.core.Project import Project
from ccpn.core.PeakList import PeakList, PARABOLICMETHOD
from ccpn.core.NmrAtom import NmrAtom
from ccpnmodel.ccpncore.api.ccp.nmr import Nmr
from ccpn.core.lib.peakUtils import _getPeakSNRatio, snapToExtremum as peakUtilsSnapToExtremum
from ccpn.util.decorators import logCommand
from ccpn.core.lib.ContextManagers import newObject, ccpNmrV3CoreSetter, \
    undoBlock, undoBlockWithoutSideBar, undoStackBlocking, ccpNmrV3CoreUndoBlock
from ccpn.util.Logging import getLogger
from ccpn.util.Common import makeIterableList
# from ccpn.util.Constants import SCALETOLERANCE
from ccpn.core.NmrAtom import UnknownIsotopeCode


class Peak(AbstractWrapperObject):
    """Peak object, holding position, intensity, and assignment information

    Measurements that require more than one NmrAtom for an individual assignment
    (such as  splittings, J-couplings, MQ dimensions, reduced-dimensionality
    experiments etc.) are not supported (yet). Assignments can be viewed and set
    either as a list of assignments for each dimension (dimensionNmrAtoms) or as a
    list of all possible assignment combinations (assignedNmrAtoms)"""

    #: Short class name, for PID.
    shortClassName = 'PK'
    # Attribute it necessary as subclasses must use superclass className
    className = 'Peak'

    _parentClass = PeakList

    #: Name of plural link to instances of class
    _pluralLinkName = 'peaks'

    # the attribute name used by current
    _currentAttributeName = 'peaks'

    #: List of child classes.
    _childClasses = []

    # Qualified name of matching API class
    _apiClassQualifiedName = Nmr.Peak._metaclass.qualifiedName()

    # Internal. Used as temporary holder during time-consuming and recursive peak routines.
    _tempAssignment = 0
    _SNAPFLAG = '_snapFlag'

    # CCPN properties
    @property
    def _apiPeak(self) -> Nmr.Peak:
        """API peaks matching Peak"""
        return self._wrappedData

    @property
    def _key(self) -> str:
        """id string - serial number converted to string."""
        return str(self._wrappedData.serial)

    @property
    def serial(self) -> int:
        """serial number of Peak, used in Pid and to identify the Peak."""
        return self._wrappedData.serial

    @property
    def _parent(self) -> Optional[PeakList]:
        """PeakList containing Peak."""
        return self._project._data2Obj[self._wrappedData.peakList] \
            if self._wrappedData.peakList in self._project._data2Obj else None

    peakList = _parent

    @property
    def spectrum(self):
        """Convenience property to get the spectrum, equivalent to peak.peakList.spectrum
        """
        return self.peakList.spectrum

    @property
    def chemicalShiftList(self):
        """Convenience property to get the spectrum, equivalent to peak.peakList.chemicalShiftList
        """
        return self.peakList.chemicalShiftList

    @property
    def restraints(self) -> tuple:
        """Restraints corresponding to Peak"""
        # placeholder, hot-fixed later
        pass

    @property
    def height(self) -> Optional[float]:
        """height of Peak."""
        if self._wrappedData.height is None:
            return None

        scale = self.peakList.spectrum.scale
        # GWV: done in setter of Spectrum.scale
        # scale = scale if scale is not None else 1.0
        # if -SCALETOLERANCE < scale < SCALETOLERANCE:
        #     getLogger().warning('Scaling {}.height by minimum tolerance (±{})'.format(self, SCALETOLERANCE))

        return self._wrappedData.height * scale

    @height.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def height(self, value: Union[float, int, None]):
        if not isinstance(value, (float, int, type(None))):
            raise TypeError('height must be a float, integer or None')
        elif value is not None and (value - value) != 0.0:
            raise TypeError('height cannot be NaN or Infinity')

        if value is None:
            self._wrappedData.height = None
        else:
            scale = self.peakList.spectrum.scale
            # scale = scale if scale is not None else 1.0
            # if -SCALETOLERANCE < scale < SCALETOLERANCE:
            #     getLogger().warning('Scaling {}.height by minimum tolerance (±{})'.format(self, SCALETOLERANCE))
            #     self._wrappedData.height = None
            # else:
            self._wrappedData.height = float(value) / scale

    @property
    def heightError(self) -> Optional[float]:
        """height error of Peak."""
        if self._wrappedData.heightError is None:
            return None

        scale = self.peakList.spectrum.scale
        # scale = scale if scale is not None else 1.0
        # if -SCALETOLERANCE < scale < SCALETOLERANCE:
        #     getLogger().warning('Scaling {}.heightError by minimum tolerance (±{})'.format(self, SCALETOLERANCE))
        #
        return self._wrappedData.heightError * scale

    @heightError.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def heightError(self, value: Union[float, int, None]):
        if not isinstance(value, (float, int, type(None))):
            raise TypeError('heightError must be a float, integer or None')
        elif value is not None and (value - value) != 0.0:
            raise TypeError('heightError cannot be NaN or Infinity')

        if value is None:
            self._wrappedData.heightError = None
        else:
            scale = self.peakList.spectrum.scale
            # scale = scale if scale is not None else 1.0
            # if -SCALETOLERANCE < scale < SCALETOLERANCE:
            #     getLogger().warning('Scaling {}.heightError by minimum tolerance (±{})'.format(self, SCALETOLERANCE))
            #     self._wrappedData.heightError = None
            # else:
            self._wrappedData.heightError = float(value) / scale

    @property
    def volume(self) -> Optional[float]:
        """volume of Peak."""
        if self._wrappedData.volume is None:
            return None

        scale = self.peakList.spectrum.scale
        # scale = scale if scale is not None else 1.0
        # if -SCALETOLERANCE < scale < SCALETOLERANCE:
        #     getLogger().warning('Scaling {}.volume by minimum tolerance (±{})'.format(self, SCALETOLERANCE))

        return self._wrappedData.volume * scale

    @volume.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def volume(self, value: Union[float, int, None]):
        if not isinstance(value, (float, int, type(None))):
            raise TypeError('volume must be a float, integer or None')
        elif value is not None and (value - value) != 0.0:
            raise TypeError('volume cannot be NaN or Infinity')

        if value is None:
            self._wrappedData.volume = None
        else:
            scale = self.peakList.spectrum.scale
            # scale = scale if scale is not None else 1.0
            # if -SCALETOLERANCE < scale < SCALETOLERANCE:
            #     getLogger().warning('Scaling {}.volume by minimum tolerance (±{})'.format(self, SCALETOLERANCE))
            #     self._wrappedData.volume = None
            # else:
            self._wrappedData.volume = float(value) / scale

    @property
    def volumeError(self) -> Optional[float]:
        """volume error of Peak."""
        if self._wrappedData.volumeError is None:
            return None

        scale = self.peakList.spectrum.scale
        # scale = scale if scale is not None else 1.0
        # if -SCALETOLERANCE < scale < SCALETOLERANCE:
        #     getLogger().warning('Scaling {}.volumeError by minimum tolerance (±{})'.format(self, SCALETOLERANCE))

        return self._wrappedData.volumeError * scale

    @volumeError.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def volumeError(self, value: Union[float, int, None]):
        if not isinstance(value, (float, int, type(None))):
            raise TypeError('volumeError must be a float, integer or None')
        elif value is not None and (value - value) != 0.0:
            raise TypeError('volumeError cannot be NaN or Infinity')

        if value is None:
            self._wrappedData.volumeError = None
        else:
            scale = self.peakList.spectrum.scale
            # scale = scale if scale is not None else 1.0
            # if -SCALETOLERANCE < scale < SCALETOLERANCE:
            #     getLogger().warning('Scaling {}.volumeError by minimum tolerance (±{})'.format(self, SCALETOLERANCE))
            #     self._wrappedData.volumeError = None
            # else:
            self._wrappedData.volumeError = float(value) / scale

    @property
    def figureOfMerit(self) -> Optional[float]:
        """figureOfMerit of Peak, between 0.0 and 1.0 inclusive."""
        return self._wrappedData.figOfMerit

    @figureOfMerit.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def figureOfMerit(self, value: float):
        if self._wrappedData.figOfMerit == value:
            return
        self._wrappedData.figOfMerit = value

        # recalculate the shifts
        assigned = set(makeIterableList(self.assignments))
        shifts = {
            cs
            for nmrAt in assigned
            for cs in nmrAt.chemicalShifts
            if cs and not cs.isDeleted
            }

        self._childActions.extend(sh._recalculateShiftValue for sh in shifts)
        self._finaliseChildren.extend((sh, 'change') for sh in shifts)

    @property
    def annotation(self) -> Optional[str]:
        """Peak text annotation."""
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
    def axisCodes(self) -> Tuple[str, ...]:
        """Spectrum axis codes in dimension order matching position."""
        return self.spectrum.axisCodes

    @property
    def position(self) -> Tuple[float, ...]:
        """Peak position in ppm (or other relevant unit) in dimension order."""
        return tuple(x.value for x in self._wrappedData.sortedPeakDims())

    @position.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def position(self, value: Sequence):
        # call api changes
        shifts = set()
        ff = self._project._data2Obj.get

        dims = self._wrappedData.sortedPeakDims()
        # if value is not None and len(value) != len(dims):
        #     raise ValueError(f'{self.__class__.__name__}.ppmPositions must be None or tuple|list of length {len(dims)}')

        for ii, peakDim in enumerate(dims):
            if value and ii >= len(value):
                # skip dims outside current peak range
                continue

            _old = peakDim.position  # the current pointPosition, quick to get
            peakDim.value = value[ii] if value else None
            peakDim.realValue = None

            # log any peak assignments that have moved in this axis
            if peakDim.position != _old:
                assigned = {ff(pdc.resonance) for pdc in peakDim.mainPeakDimContribs if hasattr(pdc, 'resonance')}
                shifts |= {sh for nmrAt in assigned for sh in nmrAt.chemicalShifts}

        self._childActions.extend(sh._recalculateShiftValue for sh in shifts)
        self._finaliseChildren.extend((sh, 'change') for sh in shifts)

    ppmPositions = position

    # @property
    # def ppmPositions(self) -> Tuple[float, ...]:
    #     """Peak position in ppm (or other relevant unit) in dimension order."""
    #     return tuple(x.value for x in self._wrappedData.sortedPeakDims())
    #
    # @ppmPositions.setter
    # @logCommand(get='self', isProperty=True)
    # @ccpNmrV3CoreSetter()
    # def ppmPositions(self, value: Sequence):
    #     # call api changes
    #     for ii, peakDim in enumerate(self._wrappedData.sortedPeakDims()):
    #         peakDim.value = value[ii]
    #         peakDim.realValue = None

    @property
    def positionError(self) -> Tuple[Optional[float], ...]:
        """Peak position error in ppm (or other relevant unit)."""
        return tuple(x.valueError for x in self._wrappedData.sortedPeakDims())

    @positionError.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def positionError(self, value: Sequence):
        for ii, peakDim in enumerate(self._wrappedData.sortedPeakDims()):
            peakDim.valueError = value[ii]

    @property
    def pointPositions(self) -> Tuple[float, ...]:
        """Peak position in points."""
        return tuple(x.position for x in self._wrappedData.sortedPeakDims())

    @pointPositions.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def pointPositions(self, value: Sequence):
        shifts = set()
        ff = self._project._data2Obj.get

        for ii, peakDim in enumerate(self._wrappedData.sortedPeakDims()):
            _old = peakDim.position  # the current pointPositions
            peakDim.position = value[ii]

            # log any peak assignments that have moved in this axis
            if peakDim.position != _old:
                assigned = {
                    ff(pdc.resonance)
                    for pdc in peakDim.mainPeakDimContribs
                    if hasattr(pdc, 'resonance')
                    }
                shifts |= {sh for nmrAt in assigned for sh in nmrAt.chemicalShifts}

        self._childActions.extend(sh._recalculateShiftValue for sh in shifts)
        self._finaliseChildren.extend((sh, 'change') for sh in shifts)

    @property
    def boxWidths(self) -> Tuple[Optional[float], ...]:
        """The full width of the peak footprint in points for each dimension,
        i.e. the width of the area that should be considered for integration, fitting, etc."""
        return tuple(x.boxWidth for x in self._wrappedData.sortedPeakDims())

    @boxWidths.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def boxWidths(self, value: Sequence):
        if value is None:
            # set all dimensions to None
            for peakDim in self._wrappedData.sortedPeakDims():
                peakDim.boxWidth = None
        else:
            for ii, peakDim in enumerate(self._wrappedData.sortedPeakDims()):
                peakDim.boxWidth = value[ii]

    @property
    def lineWidths(self) -> Tuple[Optional[float], ...]:
        """Full-width-half-height of peak for each dimension, in Hz/ppm.
        """
        return tuple(x.lineWidth for x in self._wrappedData.sortedPeakDims())

    @lineWidths.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def lineWidths(self, value: Optional[Sequence]):
        if value is None:
            # set all dimensions to None
            for peakDim in self._wrappedData.sortedPeakDims():
                peakDim.lineWidth = None
        else:
            for ii, peakDim in enumerate(self._wrappedData.sortedPeakDims()):
                peakDim.lineWidth = value[ii]

    # @property
    # def ppmLineWidths(self) -> Tuple[Optional[float], ...]:
    #     """Full-width-half-height of peak for each dimension, in ppm."""
    #     return tuple(peakDim.lineWidth * peakDim.dataDim.valuePerPoint if peakDim.lineWidth is not None else None
    #                  for peakDim in self._wrappedData.sortedPeakDims())
    #
    # @ppmLineWidths.setter
    # @logCommand(get='self', isProperty=True)
    # @ccpNmrV3CoreSetter()
    # def ppmLineWidths(self, value: Sequence):
    #     for ii, peakDim in enumerate(self._wrappedData.sortedPeakDims()):
    #         peakDim.lineWidth = value[ii] / peakDim.dataDim.valuePerPoint if value[ii] is not None else None

    ppmLineWidths = lineWidths

    @property
    def pointLineWidths(self) -> Tuple[Optional[float], ...]:
        """Full-width-half-height of peak for each dimension, in points.
        """
        # currently assumes that internal storage is in ppm's; GWV thinks Hz????

        result = []
        for peakDim, valuePerPoint in zip(self._wrappedData.sortedPeakDims(), self.spectrum._valuePerPoints):
            val = peakDim.lineWidth / valuePerPoint if peakDim.lineWidth is not None else None
            result.append(val)

        return tuple(result)

    @pointLineWidths.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def pointLineWidths(self, value: Sequence):
        for val, peakDim, valuePerPoint in zip(value,
                                               self._wrappedData.sortedPeakDims(),
                                               self.spectrum._valuePerPoints):
            peakDim.lineWidth = val * valuePerPoint if val is not None else None

    @property
    def aliasing(self) -> Tuple[Optional[float], ...]:
        """Aliasing for the peak in each dimension.
        Defined as integer number of spectralWidths added or subtracted along each dimension
        """
        aliasing = []
        for peakDim in self._wrappedData.sortedPeakDims():
            axisReversed = -1
            if expDimRef := peakDim.dataDim.expDim.findFirstExpDimRef(serial=1):
                axisReversed = -1 if expDimRef.isAxisReversed else 1

            aliasing.append(axisReversed * peakDim.numAliasing)
        return tuple(aliasing)

    @aliasing.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def aliasing(self, value: Sequence):
        if len(value) != len(self._wrappedData.sortedPeakDims()):
            raise ValueError(f"Length of {str(value)} does not match number of dimensions.")
        if not all(isinstance(dimVal, int) for dimVal in value):
            raise ValueError("Aliasing values must be integer.")

        # call api changes
        shifts = set()
        ff = self._project._data2Obj.get
        for ii, peakDim in enumerate(self._wrappedData.sortedPeakDims()):
            # log any peak assignments that have moved in this axis
            if peakDim.numAliasing != -1 * value[ii]:
                assigned = {
                    ff(pdc.resonance)
                    for pdc in peakDim.mainPeakDimContribs
                    if hasattr(pdc, 'resonance')
                    }
                peakDim.numAliasing = -1 * value[ii]

                shifts |= {sh for nmrAt in assigned for sh in nmrAt.chemicalShifts}

        self._childActions.extend(sh._recalculateShiftValue for sh in shifts)
        self._finaliseChildren.extend((sh, 'change') for sh in shifts)

    @property
    def dimensionNmrAtoms(self) -> Tuple[Tuple['NmrAtom', ...], ...]:
        """Peak dimension assignment - a tuple of tuples with the assigned NmrAtoms for each dimension.
        One of two alternative views on the Peak assignment.

        Example, for a 13C HSQC:
          ((<NA:A.127.LEU.HA>, <NA:A.127.LEU.HBX>, <NA:A.127.LEU.HBY>, <NA:A.127.LEU.HG>,

           (<NA:A.127.LEU.CA>, <NA:A.127.LEU.CB>)
           )

        Assignments as a list of individual combinations is given in 'assignedNmrAtoms'.
        Note that by setting dimensionAssignments you tell the program that all combinations are
        possible - in the example that all four protons could be bound to either of the carbons

        To (re)set the assignment for a single dimension, use the Peak.assignDimension method."""
        result = []
        for peakDim in self._wrappedData.sortedPeakDims():
            mainPeakDimContribs = peakDim.mainPeakDimContribs
            # Done this way as a quick way of sorting the values
            mainPeakDimContribs = [x for x in peakDim.sortedPeakDimContribs() if x in mainPeakDimContribs]

            data2Obj = self._project._data2Obj
            dimResults = [data2Obj[pdc.resonance] for pdc in mainPeakDimContribs
                          if hasattr(pdc, 'resonance')]
            result.append(tuple(sorted(dimResults)))
        #
        return tuple(result)

    @property
    def _dimensionNmrAtoms(self) -> Tuple[Tuple['NmrAtom', ...], ...]:
        """Transparent method to control notifiers"""
        return self.dimensionNmrAtoms

    @_dimensionNmrAtoms.setter
    @ccpNmrV3CoreUndoBlock()
    def _dimensionNmrAtoms(self, value: Sequence):
        """Assign by Dimensions
        Ccpn Internal:used by assignDimension/dimensionNmrAtoms - not to be called elsewhere
        Doesn't need undoBlock/CoreSetter as this is taken care of by calling method
        """

        if not isinstance(value, Sequence):
            raise ValueError("dimensionNmrAtoms must be sequence of list/tuples")

        isotopeCodes = self.peakList.spectrum.isotopeCodes

        apiPeak = self._wrappedData
        dimResonances = []
        for ii, atoms in enumerate(value):
            if atoms is None:
                dimResonances.append(None)

            else:

                isotopeCode = isotopeCodes[ii]

                if isinstance(atoms, str):
                    raise ValueError("dimensionNmrAtoms cannot be set to a sequence of strings")
                if not isinstance(atoms, Sequence):
                    raise ValueError("dimensionNmrAtoms must be sequence of list/tuples")

                atoms = tuple(self.getByPid(x) if isinstance(x, str) else x for x in atoms)
                resonances = tuple(x._wrappedData for x in atoms if x is not None)
                if isotopeCode and isotopeCode != UnknownIsotopeCode:
                    # check for isotope match
                    for x in resonances:
                        if x.isotopeCode not in (isotopeCode, UnknownIsotopeCode, None):
                            msg = f"""IsotopeCodes mismatch between NmrAtom {x.name} and Spectrum. 
                                  Consider changing NmrAtom isotopeCode from {x.isotopeCode} to {isotopeCode}, None, or {UnknownIsotopeCode}
                                  to avoid future warnings."""
                            getLogger().warning(msg)  # don't raise errors. NmrAtoms are just labels and can be assigned to anything if user wants so.

                dimResonances.append(resonances)

        apiPeak.assignByDimensions(dimResonances)

    @property
    def _snapFlag(self) -> int:
        """ An enumerated flag set to a peak after a snapping routine, indicating the quality of the snap.
        A positive value will indicate a successful snap to a new maximum and/or position; a negative value will suggest a failure.
        See ccpn/core/lib/PeakPickers/PeakSnapping1D._SnapFlag.
        _internal. Used mainly in Screening, where the peak.figureOfMerit is already used for other purposes"""

        return self._getInternalParameter(self._SNAPFLAG)

    @_snapFlag.setter
    def _snapFlag(self, value):
        """Set the peak  _snapFlag. positive or negative int
        """
        self._setInternalParameter(self._SNAPFLAG, value)


    @staticmethod
    def _recalculatePeakShifts(nmrResidues, shifts):
        # update the assigned nmrAtom chemical shift values - notify the nmrResidues and chemicalShifts
        for sh in shifts:
            sh._recalculateShiftValue()
        for nmr in nmrResidues:
            nmr._finaliseAction('change')
        for sh in shifts:
            sh._finaliseAction('change')

    @dimensionNmrAtoms.setter
    @logCommand(get='self', isProperty=True)
    def dimensionNmrAtoms(self, value: Sequence):

        _pre = set(makeIterableList(self.assignedNmrAtoms))
        _post = set(makeIterableList(value))
        nmrResidues = {nmr.nmrResidue for nmr in (_pre | _post)}
        shifts = list({cs for nmrAt in (_pre | _post) for cs in nmrAt.chemicalShifts})
        newShifts = list(shifts)

        chemShiftList = self.spectrum.chemicalShiftList
        _thisNmrPids = chemShiftList._getNmrAtomPids()
        _pre = {atm.pid for atm in _pre}
        _post = {atm.pid for atm in _post}

        with undoBlock():
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=partial(self._recalculatePeakShifts, nmrResidues, shifts))

            # set the value
            self._dimensionNmrAtoms = value

            # add those that are not already in the list - otherwise recalculate
            newShifts.extend(chemShiftList.newChemicalShift(nmrAtom=nmrAtom) for nmrAtom in (_post - _pre - _thisNmrPids))

            # update the chemicalShift value/valueError
            self._recalculatePeakShifts(nmrResidues, newShifts)
            with undoStackBlocking() as addUndoItem:
                addUndoItem(redo=partial(self._recalculatePeakShifts, nmrResidues, newShifts))

            self._copyDimAssignment(value)

    def _copyDimAssignment(self, value):
        """Copy the assignment to the other peaks in the multiplet.
        """
        if not self.multiplets or self._tempAssignment:
            # stop recursion
            return

        pks = {pk for mlt in self.multiplets for pk in mlt.peaks if pk != self}
        for pk in pks:
            pk._tempAssignment += 1
        for pk in pks:
            pk.dimensionNmrAtoms = value
        for pk in pks:
            pk._tempAssignment -= 1
        if any(pk._tempAssignment < 0 for pk in pks):
            raise RuntimeError(f'{self}:  Counter below 0')

    @property
    def assignedNmrAtoms(self) -> Tuple[Tuple[Optional['NmrAtom'], ...], ...]:
        """Peak assignment - a tuple of tuples of NmrAtom combinations.
        (e.g. a tuple of triplets for a 3D spectrum).
        One of two alternative views on the Peak assignment.
        Missing assignments are entered as None.

        Example, for 13H HSQC::
          ((<NA:A.127.LEU.HA>, <NA:A.127.LEU.CA>),

          (<NA:A.127.LEU.HBX>, <NA:A.127.LEU.CB>),

          (<NA:A.127.LEU.HBY>, <NA:A.127.LEU.CB>),

          (<NA:A.127.LEU.HG>, None),)

        To add a single assignment tuple, use the Peak.addAssignment method

        See also dimensionNmrAtoms, which gives assignments per dimension."""

        data2Obj = self._project._data2Obj
        apiPeak = self._wrappedData
        peakDims = apiPeak.sortedPeakDims()
        mainPeakDimContribs = [sorted(x.mainPeakDimContribs, key=operator.attrgetter('serial'))
                               for x in peakDims]
        result = []
        for peakContrib in apiPeak.sortedPeakContribs():
            allAtoms = []
            peakDimContribs = peakContrib.peakDimContribs
            for ii, peakDim in enumerate(peakDims):
                nmrAtoms = [data2Obj.get(x.resonance) for x in mainPeakDimContribs[ii]
                            if x in peakDimContribs and hasattr(x, 'resonance')]
                if not nmrAtoms:
                    nmrAtoms = [None]
                allAtoms.append(nmrAtoms)

            # NB this gives a list of tuples
            # Remove all-None tuples
            result.extend(tt for tt in itertools.product(*allAtoms)
                          if any(x is not None for x in tt))
            # result += itertools.product(*allAtoms)

        return tuple(sorted(result))

    @property
    def _assignedNmrAtoms(self) -> Tuple[Tuple[Optional['NmrAtom'], ...], ...]:
        """Transparent method to control notifiers"""
        return self.assignedNmrAtoms

    @_assignedNmrAtoms.setter
    @ccpNmrV3CoreUndoBlock()
    def _assignedNmrAtoms(self, value: Sequence):
        """Assign by Contributions
        Ccpn Internal: used by assignedNmrAtoms - not to be called elsewhere
        Doesn't need undoBlock/CoreSetter as this is taken care of by calling method
        """
        if not isinstance(value, Sequence):
            raise ValueError("assignedNmrAtoms must be set to a sequence of list/tuples")

        isotopeCodes = tuple(None if x == UnknownIsotopeCode else x for x in self.peakList.spectrum.isotopeCodes)

        #TODO: this needs to be implemented in V3 terms, using NmrAtom instances (and its attributes, methods) only
        apiPeak = self._wrappedData
        peakDims = apiPeak.sortedPeakDims()
        dimensionCount = len(peakDims)

        # get resonance, all tuples and per dimension
        resonances = []
        for tt in value:
            ll = dimensionCount * [None]
            resonances.append(ll)
            for ii, atom in enumerate(tt):
                atom = self.getByPid(atom) if isinstance(atom, str) else atom
                if isinstance(atom, NmrAtom):
                    resonance = atom._wrappedData
                    if isotopeCodes[ii] and resonance.isotopeCode not in (isotopeCodes[ii], UnknownIsotopeCode, None):
                        raise ValueError(
                                f"NmrAtom {atom}, isotope {resonance.isotopeCode}, assigned to dimension {ii + 1} must have isotope {isotopeCodes[ii]} or {UnknownIsotopeCode}"
                                )

                    ll[ii] = resonance

                elif atom is not None:
                    raise TypeError(f'Error assigning NmrAtom {str(atom)} to dimension {ii + 1}')

        # store the currently attached nmrAtoms
        _assigned = set(makeIterableList(self.assignedNmrAtoms))

        # set assignments
        apiPeak.assignByContributions(resonances)

    @assignedNmrAtoms.setter
    @logCommand(get='self', isProperty=True)
    def assignedNmrAtoms(self, value: Sequence):

        _pre = set(makeIterableList(self.assignedNmrAtoms))
        _post = set(makeIterableList(value))
        nmrResidues = {nmr.nmrResidue for nmr in (_pre | _post)}
        shifts = list({cs for nmrAt in (_pre | _post) for cs in nmrAt.chemicalShifts})
        newShifts = shifts.copy()

        _thisNmrPids = self.spectrum.chemicalShiftList._getNmrAtomPids()
        _pre = {atm.pid for atm in _pre}
        _post = {atm.pid for atm in _post}

        with undoBlock():
            with undoStackBlocking() as addUndoItem:
                addUndoItem(undo=partial(self._recalculatePeakShifts, nmrResidues, shifts))

            # set the value
            self._assignedNmrAtoms = value

            # add those that are not already in the list - otherwise recalculate
            newShifts.extend(
                    self.spectrum.chemicalShiftList.newChemicalShift(nmrAtom=nmrAtom)
                    for nmrAtom in (_post - _pre - _thisNmrPids)
                    )
            # update the chemicalShift value/valueError
            self._recalculatePeakShifts(nmrResidues, newShifts)
            with undoStackBlocking() as addUndoItem:
                addUndoItem(redo=partial(self._recalculatePeakShifts, nmrResidues, newShifts))

            self._copyAssignment(value)

    # alternativeNames
    assignments = assignedNmrAtoms
    assignmentsByDimensions = dimensionNmrAtoms

    def _copyAssignment(self, value):
        """Copy the assignment to the other peaks in the multiplet.
        """
        if not self.multiplets or self._tempAssignment:
            # stop recursion
            return

        pks = {pk for mlt in self.multiplets for pk in mlt.peaks if pk != self}
        for pk in pks:
            pk._tempAssignment += 1
        for pk in pks:
            pk.assignedNmrAtoms = value
        for pk in pks:
            pk._tempAssignment -= 1
        if any(pk._tempAssignment < 0 for pk in pks):
            raise RuntimeError(f'{self}:  Counter below 0')

    @property
    def multiplets(self) -> tuple['Multiplet', ...]:
        """List of multiplets containing the Peak."""
        return tuple(
                self._project._data2Obj[mt]
                for mt in self._wrappedData.sortedMultiplets()
                if mt in self._project._data2Obj
                )

    @logCommand(get='self')
    def addAssignment(self, value: Sequence[Union[str, 'NmrAtom']]):
        """Add a peak assignment - a list of one NmrAtom or Pid for each dimension"""

        if len(value) != self.peakList.spectrum.dimensionCount:
            raise ValueError(
                    f"Length of assignment value {value} does not match peak dimensionality {self.peakList.spectrum.dimensionCount}"
                    )

        # Convert to tuple and check for non-existing pids
        ll = []
        for val in value:
            if isinstance(val, str):
                vv = self.getByPid(val)
                if vv is None:
                    raise ValueError(f"No NmrAtom matching string pid {val}")
                else:
                    ll.append(vv)
            else:
                ll.append(val)
        value = tuple(value)

        assignedNmrAtoms = list(self.assignedNmrAtoms)
        if value in assignedNmrAtoms:
            self._project._logger.warning(
                    f"Attempt to add already existing Peak Assignment: {value} - ignored"
                    )
        else:
            assignedNmrAtoms.append(value)
            self.assignedNmrAtoms = assignedNmrAtoms

    nmrSeq = list[str | NmrAtom] | tuple[str | NmrAtom, ...]
    listtuple = list[str | NmrAtom | None | nmrSeq] | tuple[str | NmrAtom | None | nmrSeq, ...] | None

    @logCommand(get='self')
    def assignDimension(self, axisCode: list[str] | tuple[str, ...],
                        value: nmrSeq | None = None):
        """Assign dimension with axisCode to value (NmrAtom, or Pid or sequence of either, or None).
        """

        axisCodes = self.spectrum.axisCodes
        try:
            axis = axisCodes.index(axisCode)
        except ValueError:
            raise ValueError(f"axisCode {axisCode} not recognised") from None

        if value is None:
            value = []
        elif isinstance(value, str):
            value = [self.getByPid(value)]
        elif isinstance(value, list | tuple):
            value = [(self.getByPid(x) if isinstance(x, str) else x) for x in value]
        else:
            value = [value]
        if not all(isinstance(val, NmrAtom) for val in value):
            raise TypeError(f'{self.__class__.__name__}.assignDimension: value contains bad objects {value}')
        dimensionNmrAtoms = list(self.dimensionNmrAtoms)
        dimensionNmrAtoms[axis] = value

        with undoBlockWithoutSideBar():
            # set all the nmrAtoms
            self.dimensionNmrAtoms = dimensionNmrAtoms
            dimIso = self.spectrum.isotopeCodes[axis]
            # isotopeCode. if not defined, assign to the nmrAtoms from the spectrum isotopeCodes
            for nmrAtm in value:
                if nmrAtm.isotopeCode in [UnknownIsotopeCode, self._UNKNOWN_VALUE_STRING, None]:
                    try:
                        # multiQuantum are accessed from mqIsotopeCodes
                        nmrAtm._setIsotopeCode(dimIso)
                    except Exception as err:
                        getLogger().debug(f'{self.__class__.__name__}.assignDimension: '
                                          f'Impossible to set isotopeCode to {nmrAtm}. {err}')

    @logCommand(get='self')
    def assignDimensions(self, values: listtuple = None,
                         *, axisCodes: list[str] | tuple[str, ...] = None
                         ):
        """Assign dimensions with axisCode to values (NmrAtom, or Pid or sequence of either, or None).

        :param values:
        :param axisCodes:
        """
        specAxisCodes = self.spectrum.axisCodes
        if values is None:
            # clear the current assignments
            self.dimensionNmrAtoms = [[] for _ in specAxisCodes]
            return
        if not isinstance(values, list | tuple):
            raise TypeError(f'{self.__class__.__name__}.assignDimensions: values is not a list|tuple')
        if axisCodes is None:
            axisCodes = specAxisCodes
        elif not isinstance(axisCodes, list | tuple):
            raise TypeError(f'{self.__class__.__name__}.assignDimensions: axisCodes is not a list|tuple')
        if len(axisCodes) != len(specAxisCodes) or len(values) != len(specAxisCodes):
            raise TypeError(f'{self.__class__.__name__}.assignDimensions: axisCodes or values are not the correct length')
        if badAxisCodes := list(set(specAxisCodes) - set(axisCodes)):
            raise ValueError(f'{self.__class__.__name__}.assignDimensions: axisCodes {badAxisCodes} not recognised')

        dimensionNmrAtoms = [[] for _ in specAxisCodes]
        for axis, value in zip(axisCodes, values):
            if axis not in specAxisCodes:
                raise ValueError(f'{self.__class__.__name__}.assignDimensions: axisCode {axis} not recognised')
            if value is None:
                value = []
            elif isinstance(value, str):
                value = [self.getByPid(value)]
            elif isinstance(value, list | tuple):
                value = [(self.getByPid(x) if isinstance(x, str) else x) for x in value]
            else:
                value = [value]
            if not all(isinstance(val, NmrAtom) for val in value):
                raise TypeError(f'{self.__class__.__name__}.assignDimensions: values contains bad objects {value}')
            dimensionNmrAtoms[specAxisCodes.index(axis)] = value

        with undoBlockWithoutSideBar():
            # set all the nmrAtoms
            self.dimensionNmrAtoms = dimensionNmrAtoms

            for axis, nmrAtms, dimIso in zip(specAxisCodes, dimensionNmrAtoms, self.spectrum.isotopeCodes):
                # isotopeCode. if not defined, assign to the nmrAtoms from the spectrum isotopeCodes
                for nmrAtm in nmrAtms:
                    if nmrAtm.isotopeCode in [UnknownIsotopeCode, self._UNKNOWN_VALUE_STRING, None]:
                        try:
                            # multiQuantum are accessed from mqIsotopeCodes
                            nmrAtm._setIsotopeCode(dimIso)
                        except Exception as err:
                            getLogger().debug(f'{self.__class__.__name__}.assignDimensions: '
                                              f'Impossible to set isotopeCode to {nmrAtm}. {err}')

    def getByAxisCodes(self, parameterName: str, axisCodes: Sequence[str] = None,
                       exactMatch: bool = False) -> list:
        """Return a list of values defined by parameterName in order defined by axisCodes (default order if None).
        Perform a mapping if exactMatch=False (e.g. 'H' to 'Hn')

        :param parameterName: a str denoting a Spectrum dimensional attribute
        :param axisCodes: a tuple or list of axisCodes
        :param exactMatch: a boolean optional testing for an exact match with the instance axisCodes
        :return: the values defined by parameterName in axisCode order

        Related:
        Use getByDimensions() for dimensions (1..dimensionCount) based access of dimensional parameters of the
            Peak class.
        """
        from ccpn.core.lib.SpectrumLib import _getParameterValues

        if axisCodes is None:
            dimensions = self.spectrum.dimensions
        else:
            dimensions = self.spectrum.orderByAxisCodes(self.spectrum.dimensions, axisCodes=axisCodes, exactMatch=exactMatch)

        try:
            newValues = _getParameterValues(self, parameterName,
                                            dimensions=dimensions, dimensionCount=self.spectrum.dimensionCount)
        except ValueError as es:
            raise ValueError(f'{self.__class__.__name__}.getByAxisCodes: {str(es)}') from es

        return newValues

    def setByAxisCodes(self, parameterName: str, values: Sequence, axisCodes: Sequence[str] = None, exactMatch: bool = False) -> list:
        """Set attributeName to values in order defined by axisCodes (default order if None)
        Perform a mapping if exactMatch=False (eg. 'H' to 'Hn')

        :param parameterName: a str denoting a Spectrum dimensional attribute
        :param values: an iterable with values
        :param axisCodes: a tuple or list of axisCodes
        :param exactMatch: a boolean optional testing for an exact match with the instance axisCodes
        :return: a list of newly set values of parameterName (in default order)

        Related:
        Use setByDimensions() for dimensions (1..dimensionCount) based setting of dimensional parameters of the
            Peak class.
        """
        from ccpn.core.lib.SpectrumLib import _setParameterValues

        if axisCodes is None:
            dimensions = self.spectrum.dimensions
        else:
            dimensions = self.spectrum.orderByAxisCodes(self.spectrum.dimensions, axisCodes=axisCodes, exactMatch=exactMatch)

        try:
            newValues = _setParameterValues(self, parameterName, values,
                                            dimensions=dimensions, dimensionCount=self.spectrum.dimensionCount)
        except ValueError as es:
            raise ValueError(f'{self.__class__.__name__}.setByAxisCodes: {str(es)}') from es

        return newValues

    def getByDimensions(self, parameterName: str, dimensions: Sequence[int] = None) -> list:
        """Return a list of values of Peak dimensional attribute parameterName in order defined
        by dimensions (default order if None).

        :param parameterName: a str denoting a Spectrum dimensional attribute
        :param dimensions: a tuple or list of dimensions (1..dimensionCount)
        :return: the values defined by parameterName in dimensions order

        Related:
        Use getByAxisCodes() for axisCode based access of dimensional parameters of the Spectrum class.
        """
        from ccpn.core.lib.SpectrumLib import _getParameterValues

        if dimensions is None:
            dimensions = self.spectrum.dimensions

        try:
            newValues = _getParameterValues(self, parameterName,
                                            dimensions=dimensions, dimensionCount=self.spectrum.dimensionCount)
        except ValueError as es:
            raise ValueError(
                    f'{self.__class__.__name__}.getByDimensions: {str(es)}'
                    ) from es

        return newValues

    def setByDimensions(self, parameterName: str, values: Sequence, dimensions: Sequence[int] = None) -> list:
        """Set Spectrum dimensional attribute parameterName to values in the order as defined by
        dimensions (1..dimensionCount)(default order if None)

        :param parameterName: a str denoting a Spectrum dimensional attribute
        :param dimensions: a tuple or list of dimensions (1..dimensionCount)
        :return: a list of newly set values of parameterName (in default order)

        Related:
        Use setByAxisCodes() for axisCode based setting of dimensional parameters of the Spectrum class.
        """
        from ccpn.core.lib.SpectrumLib import _setParameterValues

        if dimensions is None:
            dimensions = self.spectrum.dimensions

        try:
            newValues = _setParameterValues(self, parameterName, values, dimensions=dimensions, dimensionCount=self.spectrum.dimensionCount)
        except ValueError as es:
            raise ValueError(f'{self.__class__.__name__}.setByDimensions: {str(es)}') from es

        return newValues

    @property
    def clusterId(self):
        """Get/set the clusterId for the peak
        """
        return self._wrappedData.clusterId

    @clusterId.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def clusterId(self, value):
        if not isinstance(value, (int, type(None))):
            raise ValueError('Peak.clusterId must be of type int >= 0, None')
        if value is not None and value < 0:
            raise ValueError('Peak.clusterId must be >= 0')

        self._wrappedData.clusterId = value

    @property
    def peakViews(self) -> list:
        """STUB: hot-fixed later"""
        return []

    #=========================================================================================
    # Implementation functions
    #=========================================================================================

    @classmethod
    def _getAllWrappedData(cls, parent: PeakList) -> Tuple[Nmr.Peak, ...]:
        """Get wrappedData (Peaks) for all Peak children of parent PeakList."""
        return parent._wrappedData.sortedPeaks()

    def _finaliseAction(self, action: str, **actionKwds):
        """Subclassed to handle associated multiplets
        """
        if not super()._finaliseAction(action, **actionKwds):
            return

        # if this peak is changed or deleted then it's multiplets/integral need to CHANGE
        # create required as undo may return peak to a multiplet list
        # use fromPeak/Multiplet to stop infinite loops
        actionKwds['fromPeak'] = self
        if action in {'change', 'create', 'delete'} and not actionKwds.get('fromMultiplet'):
            for mt in self.multiplets:
                mt._finaliseAction('change', **actionKwds)
            # NOTE:ED does integral need to be notified? - and reverse notifiers in multiplet/integral

    def delete(self):
        """Delete a peak."""
        assigned = tuple(() for _ in range(self.peakList.spectrum.dimensionCount))

        with undoBlockWithoutSideBar():
            # remove from any associated multiplets
            if mp := self.multiplets:
                for m in mp:
                    m.removePeaks([self])

            self.dimensionNmrAtoms = assigned
            self._delete()

    def __str__(self):
        """Readable string representation;
        """
        _digits = {'1H': 3, '15N': 2, '13C': 2, '19F': 3}
        # _digits.get(iCode,2)
        ppms = tuple(round(p, _digits.get(iCode, 2)) if p is not None else None
                     for p, iCode in zip(self.ppmPositions, self.spectrum.isotopeCodes))
        return "<%s: @%r>" % (self.pid, ppms)

    #=========================================================================================
    # CCPN functions
    #=========================================================================================

    def isPartlyAssigned(self):
        """Whether peak is partly assigned."""
        return any(self.dimensionNmrAtoms)

    def isFullyAssigned(self):
        """Whether peak is fully assigned."""
        return all(self.dimensionNmrAtoms)

    @logCommand(get='self')
    def copyTo(self, targetPeakList: PeakList, includeAllProperties: bool = True) -> 'Peak':
        """Make (and return) a copy of the Peak in targetPeakList.
        IncludeAll, True to copy all properties from origin to target Peak. False will copy
        only position and assignments (if available)"""

        if includeAllProperties:
            singleValueTags = ['height', 'volume', 'heightError', 'volumeError', 'figureOfMerit',
                               'annotation', 'comment', 'clusterId']
            dimensionValueTags = ['ppmPositions', 'positionError', 'boxWidths', 'lineWidths', ]
        else:
            singleValueTags = []
            dimensionValueTags = ['ppmPositions', 'positionError']

        peakList = self.peakList
        dimensionCount = peakList.spectrum.dimensionCount

        if dimensionCount < targetPeakList.spectrum.dimensionCount:
            raise ValueError(
                    f"Cannot copy {dimensionCount}D {self.longPid} to {targetPeakList.spectrum.dimensionCount}D {targetPeakList.longPid}. Incompatible dimensionality."
                    )

        destinationAxisCodes = targetPeakList.spectrum.axisCodes
        dimensionMapping = peakList.spectrum.getByAxisCodes('dimensions', destinationAxisCodes, exactMatch=False)

        if None in dimensionMapping:
            raise ValueError(
                    f"{self} axisCodes {peakList.spectrum.axisCodes} not compatible with targetSpectrum axisCodes {targetPeakList.spectrum.axisCodes}"
                    )

        with undoBlockWithoutSideBar():
            params = {tag: getattr(self, tag) for tag in singleValueTags}
            for tag in dimensionValueTags:
                value = self.getByDimensions(tag, dimensions=dimensionMapping)
                params[tag] = value

            newPeak = targetPeakList.newPeak(**params)

            if assignments := self.getByDimensions('assignedNmrAtoms', dimensionMapping):
                newPeak.assignedNmrAtoms = assignments

            return newPeak

    @logCommand(get='self')
    def copyAssignmentTo(self, targetPeak, exactMatch=False):
        """Copy the assignment to a target peak with matching AxisCodes
        :return tuple of tuple. The assignedNmrAtoms """
        destinationAxisCodes = targetPeak.spectrum.axisCodes
        dimensionMapping = self.spectrum.getByAxisCodes('dimensions', destinationAxisCodes, exactMatch=exactMatch)
        assignments = self.getByDimensions('assignedNmrAtoms', dimensionMapping)
        targetPeak.assignedNmrAtoms = assignments
        return assignments

    def reorderValues(self, values, newAxisCodeOrder):
        """Reorder values in spectrum dimension order to newAxisCodeOrder
        by matching newAxisCodeOrder to spectrum axis code order."""
        return commonUtil.reorder(values, self._parent._parent.axisCodes, newAxisCodeOrder)

    def getInAxisOrder(self, attributeName: str, axisCodes: Sequence[str] = None):
        """Get attributeName in order defined by axisCodes :
           (default order if None)"""
        if not hasattr(self, attributeName):
            raise AttributeError(f'Peak object does not have attribute "{attributeName}"')

        values = getattr(self, attributeName)
        if axisCodes is None:
            return values
        else:
            # change to order defined by axisCodes
            return self.reorderValues(values, axisCodes)

    def setInAxisOrder(self, attributeName: str, values: Sequence[Any], axisCodes: Sequence[str] = None):
        """Set attributeName from values in order defined by axisCodes
           (default order if None)"""
        if not hasattr(self, attributeName):
            raise AttributeError(f'Peak object does not have attribute "{attributeName}"')

        if axisCodes is not None:
            # change values to the order appropriate for spectrum
            values = self.reorderValues(values, axisCodes)
        setattr(self, attributeName, values)

    def snapToExtremum(self, halfBoxSearchWidth: int = 4, halfBoxFitWidth: int = 4,
                       minDropFactor: float = 0.1, fitMethod: str = PARABOLICMETHOD,
                       searchBoxMode=False, searchBoxDoFit=False):
        """Snap the Peak to the closest local extrema, if within range."""
        peakUtilsSnapToExtremum(self, halfBoxSearchWidth=halfBoxSearchWidth, halfBoxFitWidth=halfBoxFitWidth,
                                minDropFactor=minDropFactor, fitMethod=fitMethod,
                                searchBoxMode=searchBoxMode, searchBoxDoFit=searchBoxDoFit)

    # def fitPositionHeightLineWidths(self):
    #     """Set the position, height and lineWidth of the Peak."""
    #     LibPeak.fitPositionHeightLineWidths(self._apiPeak)

    @property
    def integral(self):
        """Return the integral attached to the peak."""
        return self._project._data2Obj[self._wrappedData.integral] if self._wrappedData.integral else None

    @integral.setter
    @logCommand(get='self', isProperty=True)
    @ccpNmrV3CoreSetter()
    def integral(self, value: Union['Integral'] = None):
        """Link an integral to the peak.
        The peak must belong to the spectrum containing the peakList.
        :param value: single integral.
        """
        if value:
            from ccpn.core.Integral import Integral

            if not isinstance(value, Integral):
                raise TypeError(f'{value} is not of type Integral')

            spectrum = self._parent.spectrum
            if value not in spectrum.integrals:
                raise ValueError(f'{value.pid} does not belong to spectrum: {spectrum.pid}')

        self._wrappedData.integral = value._wrappedData if value else None

    @property
    def signalToNoiseRatio(self):
        """
        :return: float. Estimated  Signal to Noise ratio based on the spectrum noiseLevel values.
        SNratio = |factor*(height/DeltaNoise)|
                height: peak height
                DeltaNoise: spectrum noise levels
                factor: multiplication factor. Default: 2.5
        """
        return _getPeakSNRatio(self)

    @logCommand(get='self')
    def estimateVolume(self, volumeIntegralLimit=2.0):
        """Estimate the volume of the peak from a gaussian distribution.
        The width of the volume integral in each dimension is the lineWidth (FWHM) * volumeIntegralLimit,
        the default is 2.0 * FWHM of the peak.
        :param volumeIntegralLimit: integral width as a multiple of lineWidth (FWHM)
        """

        def sigma2fwhm(sigma):
            """Convert sigma to FWHM for gaussian distribution
            """
            return sigma * np.sqrt(8 * np.log(2))

        def fwhm2sigma(fwhm):
            """Convert FWHM to sigma for gaussian distribution
            """
            return fwhm / np.sqrt(8 * np.log(2))

        def make_gauss(N, sigma, mu, height):
            """Generate a gaussian distribution from given parameters
            """
            k = height  # 1.0 / (sigma * np.sqrt(2 * np.pi)) - to give unit area at infinite bounds
            s = -1.0 / (2 * sigma * sigma)
            return k * np.exp(s * (N - mu) * (N - mu))

        lineWidths = self.lineWidths
        if not lineWidths or None in lineWidths:
            raise ValueError('cannot estimate volume, lineWidths not defined or contain None.')
        if not self.height:
            raise ValueError('cannot estimate volume, height not defined.')

        # parameters for a unit height/sigma gaussian
        sigmaX = 1.0
        mu = 0.0
        height = 1.0
        numPoints = 39  # area estimate area < 1e-8 for this number of points

        # calculate integral limit from FWHM - only need positive half
        FWHM = sigma2fwhm(sigmaX)
        lim = volumeIntegralLimit * FWHM / 2.0
        xxSig = np.linspace(0, lim, numPoints)
        vals = make_gauss(xxSig, sigmaX, mu, height)
        area = 2.0 * np.trapz(vals, xxSig)

        # note that negative height will give negative volume
        vol = 1.0
        for lw in lineWidths:
            # multiply the values for the gaussian in each dimension
            vol *= (area * (lw / FWHM))

        self.volume = self.height * abs(vol)

        # do I need to set the volume error?
        # self.volumeError = 1e-8

    def fit(self, fitMethod=None, halfBoxSearchWidth=4, keepPosition=False, iterations=10):
        """
        Fit the peak to recalculate position and lineWidths.
        Use peak.estimateVolume to recalculate the volume.

        :param fitMethod: str, one of ['gaussian', 'lorentzian', 'parabolic']
               Default: the fitting method defined in the general preferences.
               If not given or not included in the available options, it uses the default.
        :param halfBoxSearchWidth: int. Default: 4.
               Used to increase the searching area limits from the initial position.
        :param keepPosition: bool. Default: False.
               if True, reset to the original position after applying the fitting method.
               Height is calculated using spectrum.getHeight()
        :param iterations: int. Default: 3.
               How many times the fitting method will run before it converges.
        :return: None.
        """
        from ccpn.core.PeakList import PICKINGMETHODS
        from ccpn.core.lib.ContextManagers import undoBlockWithoutSideBar, notificationEchoBlocking

        if fitMethod not in PICKINGMETHODS:
            fitMethod = self._project.application.preferences.general.peakFittingMethod
        peak = self
        peakList = peak.peakList
        originalPosition = peak.position
        lastLWsFound = []
        consecutiveSameLWsCount = 0
        maxSameLWsCount = 3  # if the same values are found in the last x iterations, then it breaks the loop.
        with undoBlockWithoutSideBar():
            with notificationEchoBlocking():
                while iterations > 0 and consecutiveSameLWsCount <= maxSameLWsCount:
                    peakList.fitExistingPeaks([peak], fitMethod=fitMethod,
                                              halfBoxSearchWidth=halfBoxSearchWidth, singularMode=True)
                    if keepPosition:
                        peak.position = originalPosition
                        peak.height = peakList.spectrum.getHeight(peak.ppmPositions)
                    if np.array_equal(lastLWsFound, peak.lineWidths):
                        consecutiveSameLWsCount += 1
                    else:
                        consecutiveSameLWsCount = 0
                    lastLWsFound = peak.lineWidths
                    iterations -= 1
        getLogger().info(f'Peak fit completed for {peak}')

    def getAsDataFrame(self) -> pd.DataFrame:
        """Get the peak properties as a dataframe """
        df = pd.DataFrame()
        ix = self.serial
        dimHeaderPrefix = '_F'
        # do assignments (complex case)
        for i, nmrAtoms in enumerate(self.assignmentsByDimensions, start=1):
            values = ','.join([na.pid for na in nmrAtoms])
            df.loc[ix, f'Assign{dimHeaderPrefix}{i}'] = values
        for header, values in self.getAsDict().items():
            if isinstance(values, (list, tuple)):
                for i, value in enumerate(values, start=1):
                    if isinstance(value, (int, float, str)):
                        df.loc[ix, f'{header.strip("s")}{dimHeaderPrefix}{i}'] = value
            if isinstance(values, (int, float, str)):
                df.loc[ix, f'{header}'] = values
        return df

    # def _checkAliasing(self):
    #     """Recalculate the aliasing range for all peaks in the parent spectrum
    #     """
    #     spectrum = self.peakList.spectrum
    #     alias = spectrum._getAliasingRange()
    #     if alias is not None:
    #         spectrum.aliasingRange = alias

    #===========================================================================================
    # new<Object> and other methods
    # Call appropriate routines in their respective locations
    #===========================================================================================


#=========================================================================================
# Connections to parents:
#=========================================================================================

@newObject(Peak)
def _newPeak(self: PeakList, *, height: float = None, volume: float = None,
             heightError: float = None, volumeError: float = None,
             figureOfMerit: float = 1.0, annotation: str = None, comment: str = None,
             ppmPositions: Sequence[float] = (), position: Sequence[float] = None, positionError: Sequence[float] = (),
             pointPositions: Sequence[float] = (), boxWidths: Sequence[float] = (),
             lineWidths: Sequence[float] = (), ppmLineWidths: Sequence[float] = (), pointLineWidths: Sequence[float] = (),
             clusterId: int = None,
             ) -> Peak:
    """Create a new Peak within a peakList

    NB you must create the peak before you can assign it. The assignment attributes are:
    - assignedNmrAtoms - A tuple of all (e.g.) assignment triplets for a 3D spectrum
    - dimensionNmrAtoms - A tuple of tuples of assignments, one for each dimension

    See the Peak class for details.

    :param height: height of the peak (related attributes: volume, volumeError, lineWidths)
    :param volume:
    :param heightError:
    :param volumeError:
    :param figureOfMerit:
    :param annotation:
    :param comment: optional comment string
    :param ppmPositions: peak position in ppm for each dimension (related attributes: positionError, pointPositions)
    :param position: OLD: peak position in ppm for each dimension (related attributes: positionError, pointPositions)
    :param positionError:
    :param pointPositions:
    :param boxWidths:
    :param lineWidths:
    :param clusterId:
    :return: a new Peak instance.
    """

    if position is not None:
        ppmPositions = position  # Backward compatibility

    apiPeakList = self._apiPeakList
    apiPeak = apiPeakList.newPeak(height=height, volume=volume,
                                  heightError=heightError, volumeError=volumeError,
                                  figOfMerit=figureOfMerit, clusterId=clusterId,
                                  annotation=annotation, details=comment)
    result = self._project._data2Obj.get(apiPeak)
    if result is None:
        raise RuntimeError('Unable to generate new Peak item')

    apiPeakDims = apiPeak.sortedPeakDims()
    if ppmPositions:
        if len(ppmPositions) != len(apiPeakDims):
            raise ValueError(f'ppmPositions must be of length {len(apiPeakDims)}')

        for ii, peakDim in enumerate(apiPeakDims):
            peakDim.value = ppmPositions[ii]

    elif pointPositions:
        if len(pointPositions) != len(apiPeakDims):
            raise ValueError(f'pointPositions must be of length {len(apiPeakDims)}')

        pointCounts = result.spectrum.pointCounts
        for ii, peakDim in enumerate(apiPeakDims):
            # move the peak to the correct aliased position
            alias = int((pointPositions[ii] - 1) // pointCounts[ii])
            pos = float((pointPositions[ii] - 1) % pointCounts[ii]) + 1.0  # API position starts at 1
            peakDim.numAliasing = alias
            peakDim.position = pos

    if positionError:
        for ii, peakDim in enumerate(apiPeakDims):
            peakDim.valueError = positionError[ii]
    if boxWidths:
        for ii, peakDim in enumerate(apiPeakDims):
            peakDim.boxWidth = boxWidths[ii]

    # currently, lineWidths/ppmLineWidths are both in Hz/ppm
    if lineWidths:
        for ii, peakDim in enumerate(apiPeakDims):
            peakDim.lineWidth = lineWidths[ii]
    elif ppmLineWidths:
        for ii, peakDim in enumerate(apiPeakDims):
            peakDim.lineWidth = ppmLineWidths[ii]
    elif pointLineWidths:
        for peakDim, pointLineWidth in zip(apiPeakDims, pointLineWidths):
            peakDim.lineWidth = (pointLineWidth * peakDim.dataDim.valuePerPoint) if pointLineWidth else None

    result.height = height  # use the method to store the unit-scaled value
    result.volume = volume
    result.heightError = heightError
    result.volumeError = volumeError

    return result


@newObject(Peak)
def _newPickedPeak(self: PeakList, pointPositions: Sequence[float] = None, height: float = None,
                   lineWidths: Sequence[float] = (), fitMethod: str = 'gaussian') -> Peak:
    """Create a new Peak within a peakList from a picked peak

    See the Peak class for details.

    :param height: height of the peak (related attributes: volume, volumeError, lineWidths)
    :param pointPositions: peak position in points for each dimension (related attributes: positionError, pointPositions)
    :param fitMethod: type of curve fitting
    :param lineWidths:
    :return: a new Peak instance.
    """

    apiPeakList = self._apiPeakList
    apiPeak = apiPeakList.newPeak()
    result = self._project._data2Obj.get(apiPeak)
    if result is None:
        raise RuntimeError('Unable to generate new Peak item')

    apiDataSource = self.spectrum._apiDataSource
    apiDataDims = apiDataSource.sortedDataDims()
    apiPeakDims = apiPeak.sortedPeakDims()

    for i, peakDim in enumerate(apiPeakDims):
        dataDim = apiDataDims[i]

        if dataDim.className == 'FreqDataDim':
            dataDimRef = dataDim.primaryDataDimRef
        else:
            dataDimRef = None

        if dataDimRef:
            peakDim.numAliasing = int(divmod(pointPositions[i], dataDim.numPointsOrig)[0])
            peakDim.position = float(pointPositions[i] + 1 - peakDim.numAliasing * dataDim.numPointsOrig)  # API position starts at 1

        else:
            peakDim.position = float(pointPositions[i] + 1)

        if fitMethod and lineWidths and lineWidths[i] is not None:
            peakDim.lineWidth = dataDim.valuePerPoint * lineWidths[i]  # conversion from points to Hz

    # apiPeak.height = apiDataSource.scale * height
    # store the unit scaled value
    apiPeak.height = height

    return result


# Additional Notifiers:
#
# NB These API notifiers will be called for API peaks - which match both Peaks and Integrals
className = Nmr.PeakDim._metaclass.qualifiedName()
Project._apiNotifiers.append(
        ('_notifyRelatedApiObject', {'pathToObject': 'peak', 'action': 'change'}, className, ''),
        )
for clazz in Nmr.AbstractPeakDimContrib._metaclass.getNonAbstractSubtypes():
    className = clazz.qualifiedName()
    # NB - relies on PeakDimContrib.peakDim.peak still working for deleted peak. Should work.
    Project._apiNotifiers.extend((
        ('_notifyRelatedApiObject', {'pathToObject': 'peakDim.peak', 'action': 'change'},
         className, 'postInit'),
        ('_notifyRelatedApiObject', {'pathToObject': 'peakDim.peak', 'action': 'change'},
         className, 'delete'),
        )
            )

# EJB 20181122: moved to SpectrumReference
# Notify Peaks change when SpectrumReference changes
# (That means DataDimRef referencing information)
# SpectrumReference._setupCoreNotifier('change', AbstractWrapperObject._finaliseRelatedObject,
#                                      {'pathToObject': 'spectrum.peaks', 'action': 'change'})
