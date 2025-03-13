"""
Module Documentation here
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (https://www.ccpn.ac.uk) 2014 - 2025"
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
__dateModified__ = "$dateModified: 2025-03-13 18:50:05 +0000 (Thu, March 13, 2025) $"
__version__ = "$Revision: 3.3.1 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2023-03-02 11:18:54 +0000 (Thu, March 2, 2023) $"
#=========================================================================================
# Start of code
#=========================================================================================

from typing import Optional, Sequence, Tuple, Callable, TypeVar
from ccpnmodel.ccpncore.api.ccp.nmr.Nmr import AbstractDataDim, DataDimRef, ExpDim, ExpDimRef
import ccpn.core.lib.SpectrumLib as specLib
from ccpn.util.Common import isIterable
from ccpn.util.Logging import getLogger


SpectrumInstance = TypeVar('SpectrumInstance', bound='ccpn.core.Spectrum.Spectrum')


class SpectrumDimensionAttributes:
    """Spectrum dimensional attributes
    Inherited by SpectrumReference and PseudoDimension
    """
    # These SHOULD all be defined in SpectrumReference/PseudoDimension
    _dataDim: AbstractDataDim
    _dataDimRef: DataDimRef
    _expDim: ExpDim
    _expDimRef: ExpDimRef

    spectrum: SpectrumInstance
    pointToValue: Callable
    ppmToPoint: Callable
    _hasInternalParameter: Callable
    _getInternalParameter: Callable
    _setInternalParameter: Callable

    #-----------------------------------------------------------------------------------------
    # Spectrum-dimension related properties
    #-----------------------------------------------------------------------------------------

    @property
    def _isFrequencyDataDim(self) -> bool:
        """True if this is a frequency dimension; mainly used to implement code to upward compatible with v2"""
        return self._dataDim.className == 'FreqDataDim'

    @property
    def _isFidDataDim(self) -> bool:
        """True if this is a Fid dimension; mainly used to implement code to upward compatible with v2"""
        return self._dataDim.className == 'FidDataDim'

    @property
    def _isSampledDataDim(self) -> bool:
        """True if this is a sampled dimension; mainly used to implement code to upward compatible with v2"""
        return self._dataDim.className == 'SampledDataDim'

    @property
    def dimension(self) -> int:
        """dimension number"""
        return self._dataDim.dim

    @property
    def isAcquisition(self) -> bool:
        """True if dimension is acquisition"""
        return self._expDim.isAcquisition

    @isAcquisition.setter
    def isAcquisition(self, value):
        self._expDim.isAcquisition = value

    @property
    def pointCount(self):
        """Number of points in this dimension"""
        if self._isFidDataDim and hasattr(self._dataDim, 'numPointsValid'):
            # GWV: compatibility with v2?
            result = self._dataDim.numPointsValid
        else:
            result = self._dataDim.numPoints
        return result

    @pointCount.setter
    def pointCount(self, value):
        # To decouple pointCount from spectralWidth
        oldSw = self.spectralWidthHz
        if self._isFidDataDim:
            # GWV: compatibility with v2?
            self._dataDim.numPointsValid = value
        else:
            self._dataDim.numPoints = value
            self._dataDim.numPointsOrig = value

        self.spectralWidthHz = oldSw

    @property
    def isComplex(self):
        """Boolean indicating complex data for this dimension"""
        return self._dataDim.isComplex

    @isComplex.setter
    def isComplex(self, value):
        self._dataDim.isComplex = bool(value)

    @property
    def dimensionType(self) -> str:
        """Dimension type ('Time' / 'Frequency' / 'Sampled')"""
        if not self._hasInternalParameter('dimensionType'):
            result = specLib.DIMENSION_FREQUENCY
            # self._setInternalParameter('dimensionType', result)
        else:
            result = self._getInternalParameter('dimensionType')
        return result

    @dimensionType.setter
    def dimensionType(self, value):
        if value not in specLib.DIMENSIONTYPES:
            raise ValueError('dimensionType should be one of %r' % specLib.DIMENSIONTYPES)
        self._setInternalParameter('dimensionType', value)

    @property
    def isReversed(self) -> bool:
        """Set whether the axis is reversed - isReversed implies that ppm values decrease as point values increase
        deprecated!
        :return True if dimension is reversed
        """
        return self._expDimRef.isAxisReversed

    @isReversed.setter
    def isReversed(self, value):
        """Set whether the axis is reversed - isReversed implies that ppm values decrease as point values increase
        """
        self._expDimRef.__dict__['isAxisReversed'] = value

    @property
    def spectrometerFrequency(self) -> float:
        """Absolute frequency at carrier (or at splitting 0.0). In MHz or dimensionless."""
        return self._expDimRef.sf

    @spectrometerFrequency.setter
    def spectrometerFrequency(self, value):
        self._expDimRef.sf = value

    @property
    def measurementType(self) -> Optional[str]:
        """Type of NMR measurement referred to by this reference. Legal values are:
        'Shift','ShiftAnisotropy','JCoupling','Rdc','TROESY','DipolarCoupling',
        'MQShift','T1','T2','T1rho','T1zz' --- defined SpectrumLib.MEASUREMENT_TYPES
        """
        # TODO: Model-change to allow None
        return self._expDimRef.measurementType

    @measurementType.setter
    def measurementType(self, value):
        self._expDimRef.measurementType = value

    # GWV this was carried from the previous Spectrum implementation; no idea why, but it mattered
    # point1 = 1 - dataDim.pointOffset
    # result[ii] = tuple(sorted((ff(point1), ff(point1 + dataDim.numPointsOrig))

    @property
    def maxAliasedFrequency(self) -> float:
        """maximum possible frequency (in ppm) for this reference """
        if (result := self._expDimRef.maxAliasedFreq) is None:
            point_1 = 1 - self._dataDim.pointOffset - 0.5
            point_n = float(point_1 + self.pointCount)
            result = self.pointToValue((point_n))
        return result

    @maxAliasedFrequency.setter
    def maxAliasedFrequency(self, value):
        maxSpecLimits = max(self.spectrumLimits)
        if value is not None:
            if value < maxSpecLimits:
                raise ValueError('%s: dimension %d, maxAliasedFrequency: value %s < max(spectrumLimits) %s' % (
                                 self.spectrum, self.dimension, value, maxSpecLimits
                                )
                )
            if value > maxSpecLimits + self.spectralWidth*specLib.MAXALIASINGRANGE:
                value = maxSpecLimits +  self.spectralWidth*specLib.MAXALIASINGRANGE
                getLogger().warning('Setting %s, dimension %d maxAliasedFrequency: value clipped to %s' %
                                    (self.spectrum, self.dimension, value)
                                    )

        self._expDimRef.maxAliasedFreq = value

    @property
    def minAliasedFrequency(self) -> float:
        """minimum possible frequency (in ppm) for this dimension """
        if (result := self._expDimRef.minAliasedFreq) is None:
            point_1 = float(1 - self._dataDim.pointOffset) - 0.5
            result = self.pointToValue((point_1))
        return result

    @minAliasedFrequency.setter
    def minAliasedFrequency(self, value):
        minSpecLimits = min(self.spectrumLimits)
        if value is not None:
            if value > minSpecLimits:
                raise ValueError('%s dimension %d, minAliasedFrequency: value %s > min(spectrumLimits) %s' %
                                (self.spectrum, self.dimension, value, minSpecLimits)
                                )
            if value < minSpecLimits - self.spectralWidth*specLib.MAXALIASINGRANGE:
                value = minSpecLimits - self.spectralWidth*specLib.MAXALIASINGRANGE
                getLogger().warning('Setting %s, dimension %d minAliasedFrequency: value clipped to %s' %
                                    (self.spectrum, self.dimension, value)
                                    )

        self._expDimRef.minAliasedFreq = value

    @property
    def aliasingLimits(self) -> Tuple[float, float]:
        """tuple of sorted(minAliasingLimit, maxAliasingLimit).
        i.e. The actual ppm-limits of the full (including the aliased regions) limits.
        """
        val = [self.minAliasedFrequency, self.maxAliasedFrequency]
        return (min(val), max(val))

    @aliasingLimits.setter
    def aliasingLimits(self, value):
        if not isIterable(value) or len(value) != 2:
            raise ValueError('%s dimension %d, aliasingLimits; expected (minLimit, maxLimit) but got %r' %
                             (self.spectrum, self.dimension, value)
                             )
        # zero the values to silence api-errors until both values have been set
        self.minAliasedFrequency = None
        self.maxAliasedFrequency = None

        # first set the values
        self.minAliasedFrequency = min(value)
        self.maxAliasedFrequency = max(value)
        # now round them to integer times the spectral width, by getting the aliasingIndexes
        # and setting them again
        aliasingIndices = self.aliasingIndexes
        self.aliasingIndexes = aliasingIndices

    @property
    def aliasingPointLimits(self) -> Tuple[int, int]:
        """Return a tuple of sorted(minAliasingPointLimit, maxAliasingPointLimit).
        i.e. The actual point-limits of the full (including the aliased regions) limits.
        """
        mPoints = [int(self.ppmToPoint(self.minAliasedFrequency)+0.5),
                   int(self.ppmToPoint(self.maxAliasedFrequency)+0.5)]
        return (min(mPoints,), max(mPoints))

    @property
    def aliasingIndexes(self) -> Tuple[int, int]:
        """A property derived from aliasingLimits.
        Number of times the spectralWidth are folded.
        :returns tuple(minFoldingIndex, maxFoldingIndex)
        NB: minFoldingIndex <= 0
            maxFoldingIndex >= 0
        """
        aLimits = self.aliasingLimits
        sLimits = sorted(self.spectrumLimits)
        minIndex = round( (aLimits[0]-sLimits[0]) / self.spectralWidth)
        if minIndex > 0:
            minIndex *= -1
        maxIndex = round( (aLimits[1]-sLimits[1]) / self.spectralWidth)
        if maxIndex < 0:
            maxIndex *= -1
        return (minIndex, maxIndex)

    @aliasingIndexes.setter
    def aliasingIndexes(self, value):
        if not isIterable(value) or len(value) != 2:
            raise ValueError('%s dimension %d, aliasingIndexes; expected (minIndex, maxIndex) but got %r' %
                             (self.spectrum, self.dimension, value)
                             )
        value = list(value)
        if value[0] > 0 or value[1] < 0:
            raise ValueError('%s dimension %d, aliasingIndexes; expected (minIndex<=0, maxIndex>=0) but got %r' %
                             (self.spectrum, self.dimension, value))

        clipped = False
        if value[0] < -1*specLib.MAXALIASINGRANGE:
            value[0] = -1*specLib.MAXALIASINGRANGE
            clipped = True
        if value[1] > specLib.MAXALIASINGRANGE:
            value[1] = specLib.MAXALIASINGRANGE
            clipped = True
        if clipped:
            getLogger().warning('%s dimension %d, aliasingIndexes; clipped values to %r' %
                               (self.spectrum, self.dimension, value))

        # zero the values to silence api-errors until both values have been set
        self.minAliasedFrequency = None
        self.maxAliasedFrequency = None

        self.minAliasedFrequency = min(self.spectrumLimits) + value[0]*self.spectralWidth
        self.maxAliasedFrequency = max(self.spectrumLimits) + value[1]*self.spectralWidth

    @property
    def spectrumLimits(self) -> Tuple[float, float]:
        """Return the limits of this spectrum dimension as a tuple of floats
        i.e. the ppm values of the first and last point.
        """
        if self.dimensionType == specLib.DIMENSION_FREQUENCY:
            return (self.pointToValue(1.0), self.pointToValue(float(self.pointCount)))
        elif self.dimensionType == specLib.DIMENSION_TIME:
            return (self.pointToValue(1.0), self.pointToValue(float(self.pointCount)))
            # return (0.0, self._valuePerPoint * self.pointCount)
        else:
            raise RuntimeError('%s.spectrumLimits: not implemented' % self.__class__.__name__)

    @property
    def foldingLimits(self) -> Tuple[float, float]:
        """Return the foldingLimits of this dimension as a tuple of floats.
        This is the spectrumLimits ±0.5 extra points to the left and right.
        """
        # it is easier to define a new function here than mess about with limits
        if self.dimensionType == specLib.DIMENSION_FREQUENCY:
            return (self.pointToValue(0.5), self.pointToValue(float(self.pointCount) + 0.5))
        elif self.dimensionType == specLib.DIMENSION_TIME:
            return (self.pointToValue(0.5), self.pointToValue(float(self.pointCount) + 0.5))
        else:
            raise RuntimeError('%s.foldingLimits not implemented' % self.__class__.__name__)

    @property
    def isotopeCode(self) -> Optional[str]:
        """Isotope identification strings for isotopes.
        """
        if len(self._isotopeCodes) > 0:
            return self._isotopeCodes[0]
        return None

    @isotopeCode.setter
    def isotopeCode(self, value: str):
        self._isotopeCodes = [value]

    # GWV: moved this to a private attributes, as currently we only support one isotopeCode per dimension
    @property
    def _isotopeCodes(self) -> Tuple[str, ...]:
        """Isotope identification strings for isotopes.
        NB there can be several isotopes for e.g. J-coupling or multiple quantum coherence.
        """
        return self._expDimRef.isotopeCodes

    @_isotopeCodes.setter
    def _isotopeCodes(self, value: Sequence):
        self._expDimRef.isotopeCodes = value

    mqIsotopeCodes = _isotopeCodes

    @property
    def coherenceOrder(self) -> Optional[str]:
        """Coherence order matching reference (values: 'ZQ', 'SQ', 'DQ', 'TQ', None)
        """
        if not self._hasInternalParameter('coherenceOrder'):
            specLib.CoherenceOrder.get('SQ')
            result = specLib.CoherenceOrder.SQ.name  # default to single-quantum?
        else:
            idx = self._getInternalParameter('coherenceOrder')
            result = specLib.CoherenceOrder(idx).name if idx is not None and idx in specLib.CoherenceOrder.values() else None
        return result

    @coherenceOrder.setter
    def coherenceOrder(self, value):
        cohOrders = specLib.CoherenceOrder.names()
        if value not in list(cohOrders) + [None]:
            raise ValueError('coherenceOrder should be one of %r or None; got %r' % (cohOrders, value))
        self._setInternalParameter('coherenceOrder', value if value is None else cohOrders.index(value))

    mqIsotopecodes = _isotopeCodes

    @property
    def foldingMode(self) -> Optional[str]:
        """folding mode matching reference (values: 'circular', 'mirror', None)"""
        if not self._hasInternalParameter('foldingMode'):
            result = None
            self.foldingMode = result
        else:
            result = self._getInternalParameter('foldingMode')
        return result

    @foldingMode.setter
    def foldingMode(self, value):
        if value not in list(specLib.FOLDING_MODES) + [None]:
            raise ValueError('foldingMode should be one of %r or None; got %r' %
                             (specLib.FOLDING_MODES, value))
        self._setInternalParameter('foldingMode', value)

    @property
    def axisCode(self) -> str:
        """Reference axisCode """
        return self._expDimRef.axisCode

    @axisCode.setter
    def axisCode(self, value: str):
        self._expDimRef.axisCode = value

    @property
    def axisUnit(self) -> str:
        """unit for transformed data using their reference (most commonly 'ppm')"""
        return self._expDimRef.unit

    @axisUnit.setter
    def axisUnit(self, value: str):
        self._expDimRef.unit = value

    # Attributes belonging to DataDim/DataDimRef

    @property
    def referencePoint(self) -> float:
        """point used for axis (chemical shift) referencing."""
        return self._dataDimRef.refPoint

    @referencePoint.setter
    def referencePoint(self, value):
        self._dataDimRef.refPoint = value

    @property
    def referenceValue(self) -> float:
        """ppm-value used for axis (chemical shift) referencing."""
        return self._dataDimRef.refValue

    @referenceValue.setter
    def referenceValue(self, value: float):
        self._dataDimRef.refValue = value

    @property
    def spectralWidthHz(self) -> float:
        """spectral width in Hz"""
        return self._dataDim.spectralWidth

    @spectralWidthHz.setter
    def spectralWidthHz(self, value: float):
        swOld = self.spectralWidthHz
        # self._dataDim.spectralWidth = value # This is not allowed; it needs to go via valuePerPoint
        self._valuePerPoint *= (value / swOld)

    @property
    def spectralWidth(self) -> float:
        """spectral width in ppm"""
        return self._dataDimRef.spectralWidth

    @spectralWidth.setter
    def spectralWidth(self, value: float):
        swOld = self.spectralWidth
        # self._dataDimRef.spectralWidth = value  # This is not allowed; it needs to go via valuePerPoint
        self._valuePerPoint *= (value / swOld)

    @property
    def ppmPerPoint(self):
        """Convenience; ppm per point"""
        return self.spectralWidth / float(self.pointCount)

    # This is a crucial property that effectively governs the spectral width (both in Hz and ppm)
    #     # We assume that the number of points is constant, so setting SW changes valuePerPoint
    #     dataDimRef = self._wrappedData
    #     swOld = dataDimRef.spectralWidth
    #     if dataDimRef.localValuePerPoint:
    #         dataDimRef.localValuePerPoint *= (value / swOld)
    #     else:
    #         dataDimRef.dataDim.valuePerPoint *= (value / swOld)
    @property
    def _valuePerPoint(self) -> float:
        """Value per point: in Hz for Frequency domain data, in secs for time/fid domain data"""
        return self._dataDim.valuePerPoint

    @_valuePerPoint.setter
    def _valuePerPoint(self, value: float):
        self._dataDim.valuePerPoint = value

    # @property
    # def numPointsOrig(self) -> bool:
    #     """numPointsOrig"""
    #     return self._wrappedData.dataDim.numPointsOrig

    @property
    def phase0(self) -> Optional[float]:
        """Zero-order phase"""
        return (self._dataDim.phase0 if not self._isSampledDataDim else None)

    @phase0.setter
    def phase0(self, value):
        self._dataDim.phase0 = value

    @property
    def phase1(self) -> Optional[float]:
        """First-order phase"""
        return (self._dataDim.phase1 if not self._isSampledDataDim else None)

    @phase1.setter
    def phase1(self, value):
        self._dataDim.phase1 = value

    @property
    def windowFunction(self) -> Optional[str]:
        """Window function
        e.g. 'EM', 'GM', 'SINE', 'QSINE', .... (defined in SpectrumLib.WINDOW_FUNCTIONS)
        """
        return (self._dataDim.windowFunction if not self._isSampledDataDim else None)

    @windowFunction.setter
    def windowFunction(self, value):
        if not value in list(specLib.WINDOW_FUNCTIONS) + [None]:
            raise ValueError('windowFunction should be one of %r or None; got %r' % (specLib.WINDOW_FUNCTIONS, value))
        self._dataDim.windowFunction = value

    @property
    def lorentzianBroadening(self) -> Optional[float]:
        """Lorenzian broadening (in Hz)"""
        return (self._dataDim.lorentzianBroadening if not self._isSampledDataDim else None)

    @lorentzianBroadening.setter
    def lorentzianBroadening(self, value):
        self._dataDim.lorentzianBroadening = value

    @property
    def gaussianBroadening(self) -> Optional[float]:
        """Gaussian broadening"""
        return (self._dataDim.gaussianBroadening if not self._isSampledDataDim else None)

    @gaussianBroadening.setter
    def gaussianBroadening(self, value):
        self._dataDim.gaussianBroadening = value

    @property
    def sineWindowShift(self) -> Optional[float]:
        """Shift of sine/sine-square window function (in degrees)"""
        return (self._dataDim.sineWindowShift if not self._isSampledDataDim else None)

    @sineWindowShift.setter
    def sineWindowShift(self, value):
        self._dataDim.sineWindowShift = value

    @property
    def assignmentTolerance(self) -> float:
        """Assignment Tolerance (in ppm)"""
        tolerance = self._dataDimRef.assignmentTolerance
        if tolerance is None:
            tolerance = self.defaultAssignmentTolerance
        return tolerance

    @assignmentTolerance.setter
    def assignmentTolerance(self, value):
        # has to be > than 0.0
        if value is not None:
            value = max(value, 0.0)
        self._dataDimRef.assignmentTolerance = value or None

    @property
    def defaultAssignmentTolerance(self) -> float:
        """Default assignment tolerance (in ppm); isotopeCode dependent or
        overall defaultAssignmentTolerance (defined in specLib).
        The value is always >= than digitalResolution in ppm.
        """
        tolerance = specLib.getAssignmentTolerances(self.isotopeCode)
        tolerance = max(tolerance, self.spectralWidth / float(self.pointCount))
        return tolerance
