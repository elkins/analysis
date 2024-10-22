"""Spectrum-related definitions, functions and utilities
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
__dateModified__ = "$dateModified: 2024-10-10 15:45:26 +0100 (Thu, October 10, 2024) $"
__version__ = "$Revision: 3.2.7 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

import collections
import math
import random
import numpy as np
import decorator
from typing import Tuple, Optional, Sequence, Any
from itertools import permutations
from tqdm import tqdm
from ccpn.framework.Application import getApplication
from ccpn.core.lib.ContextManagers import notificationEchoBlocking, undoBlockWithoutSideBar
from ccpn.core.lib.AxisCodeLib import getAxisCodeMatchIndices
from ccpn.core.lib._DistanceRestraintsLib import _getBoundResonances, longRangeTransfers
# from ccpn.util.Common import percentage, isIterable # this causes circular imports. DO NOT USE HERE
from ccpn.util.Logging import getLogger
from ccpn.util.decorators import singleton
from ccpn.util.DataEnum import DataEnum


#=========================================================================================
# Dimension definitions
# Defined here to prevent cyclic import problems in other modules that need access to these definitions
#=========================================================================================
DIMENSION_TIME = 'Time'
DIMENSION_FREQUENCY = 'Frequency'
DIMENSION_SAMPLED = 'Sampled'
DIMENSIONTYPES = [DIMENSION_TIME, DIMENSION_FREQUENCY, DIMENSION_SAMPLED]
DIMENSIONFREQ = 'Freq'  # GWV: not sure why this is needed, used in the model??

MAXDIM = 8  # Maximum dimensionality

X_AXIS = 0
Y_AXIS = 1
Z_AXIS = 2
A_AXIS = 3
B_AXIS = 4
C_AXIS = 5
D_AXIS = 6
E_AXIS = 7
UNDEFINED_AXIS = 8
axisNames = {X_AXIS        : "x-axis", Y_AXIS: "y-axis", Z_AXIS: "z-axis", A_AXIS: "a-axis",
             B_AXIS        : "b-axis", C_AXIS: "c-axis", D_AXIS: "d-axis", E_AXIS: "e-axis",
             UNDEFINED_AXIS: "undefined-axis"
             }

INTENSITY_DIM = 0
X_DIM = 1
Y_DIM = 2
Z_DIM = 3
A_DIM = 4
B_DIM = 5
C_DIM = 6
D_DIM = 7
E_DIM = 8
UNDEFINED_DIM = 9
dimensionNames = {INTENSITY_DIM: "intensity",
                  X_DIM        : "x-dimension", Y_DIM: "y-dimension", Z_DIM: "z-dimension", A_DIM: "a-dimension",
                  B_DIM        : "b-dimension", C_DIM: "c-dimension", D_DIM: "d-dimension", E_DIM: "e-dimension",
                  UNDEFINED_DIM: "undefined-dimension"
                  }

X_DIM_INDEX = 0
Y_DIM_INDEX = 1
Z_DIM_INDEX = 2
A_DIM_INDEX = 3
B_DIM_INDEX = 4
C_DIM_INDEX = 5
D_DIM_INDEX = 6
E_DIM_INDEX = 7
UNDEFINED_DIM_INDEX = 8

# # data types
# DATA_TYPE_REAL    = 0  # real data points
# DATA_TYPE_COMPLEX = 1  # size/2 real and size/2 imag points
# DATA_TYPE_PN      = 2  # size/2 P and size/2 N points
# dataTypeMap = {DATA_TYPE_REAL:"real", DATA_TYPE_COMPLEX:"complex", DATA_TYPE_PN:"PN"}

DATA_TYPE_REAL         = 'nR' # n real data points; pointCount = n
DATA_TYPE_COMPLEX_nRnI = '(nR)(nI)' # n real followed by n imag points; pointCount = 2*n
DATA_TYPE_COMPLEX_nRI  = 'n(RI)'  # n (real, imag) pairs; pointCount = 2*n
DATA_TYPE_COMPLEX_PN   = 'n(PN)'   # n (P, N) pairs; pointCount = 2*n
DATA_TYPES = (DATA_TYPE_REAL, DATA_TYPE_COMPLEX_nRnI, DATA_TYPE_COMPLEX_nRI, DATA_TYPE_COMPLEX_PN)

MagnetisationTransferTypes = ('onebond', 'Jcoupling', 'Jmultibond', 'relayed', 'through-space', 'relayed-alternate')
MagnetisationTransferParameters = ('dimension1 dimension2 transferType isIndirect'.split())
MagnetisationTransferTuple = collections.namedtuple('MagnetisationTransferTuple', MagnetisationTransferParameters)
NoiseEstimateTuple = collections.namedtuple('NoiseEstimateTuple', 'mean std min max noiseLevel')

FOLDING_MODE_CIRCULAR = 'circular'
FOLDING_MODE_MIRROR = 'mirror'
FOLDING_MODES = (FOLDING_MODE_CIRCULAR, FOLDING_MODE_MIRROR)


class CoherenceOrder(DataEnum):
    # name, value, description, dataValue = number of isotope-codes per order
    ZQ = 0, 'Zero Quantum', 2
    SQ = 1, 'Single Quantum', 1
    DQ = 2, 'Double Quantum', 2
    TQ = 3, 'Triple Quantum', 3


WINDOW_FUNCTION_EM = 'EM'
WINDOW_FUNCTION_GM = 'GM'
WINDOW_FUNCTION_SINE = 'Sine'
WINDOW_FUNCTION_QSINE = 'squaredSine'
WINDOW_FUNCTIONS = (WINDOW_FUNCTION_EM, WINDOW_FUNCTION_GM, WINDOW_FUNCTION_SINE, WINDOW_FUNCTION_QSINE)

# These MUST match the model - ('Shift','ShiftAnisotropy','JCoupling','Rdc','TROESY','DipolarCoupling','MQShift','T1','T2','T1rho','T1zz','Time','None')
MEASUREMENT_TYPE_TIME = 'Time'
MEASUREMENT_TYPE_SHIFT = 'Shift'
MEASUREMENT_TYPES = (MEASUREMENT_TYPE_TIME, MEASUREMENT_TYPE_SHIFT, 'ShiftAnisotropy', 'JCoupling', 'Rdc', 'TROESY', 'DipolarCoupling',
                     'MQShift', 'T1', 'T2', 'T1rho', 'T1zz')

# Isotope-dependent assignment tolerances (in ppm)
defaultAssignmentTolerance = 0.4
isotope2Tolerance = {
    '1H' : 0.03,
    '13C': 0.4,
    '15N': 0.4,
    '19F': 0.03,
    }

SPECTRUM_POSITIONS = 'positions'
SPECTRUM_INTENSITIES = 'intensities'

MAXALIASINGRANGE = 6


def splitPseudo3DSpectrumIntoPlanes(spectrum, seriesUnits='ms'):
    if not 'Time' in spectrum.dimensionTypes:
        getLogger().warning('This functionality has been implemented for time pseudo-nD spectra only.')
        return
    timeDimension = spectrum.getByAxisCodes('dimensions', ['Time'])[0]
    timeDimensionSize = spectrum.pointCounts[timeDimension - 1]
    freqDims = [dim for dim in spectrum.dimensions if dim != timeDimension]
    freqAxisCodes = spectrum.getByDimensions('axisCodes', freqDims)
    seriesValue = 0.0
    seriesIncrement = 1.0 / spectrum.spectralWidths[timeDimension - 1]
    with notificationEchoBlocking():
        with undoBlockWithoutSideBar():
            spectrumGroup = spectrum.project.newSpectrumGroup(name=spectrum.name, seriesUnits=seriesUnits)
            position = [1] * spectrum.dimensionCount  # dims and positions are 1-based
            for timePoint in range(timeDimensionSize):
                position[timeDimension - 1] = timePoint + 1
                getLogger().info(f'==> extracting {freqAxisCodes} plane at {position}')
                sp = spectrum.extractPlaneToFile(axisCodes=freqAxisCodes, position=position)
                spectrumGroup.addSpectrum(sp, seriesValue)
                seriesValue += seriesIncrement


def getAssignmentTolerances(isotopeCode) -> float:
    """:return assignmentTolerance for isotopeCode or defaultAssignment tolerance if not defined
    """
    return isotope2Tolerance.get(isotopeCode, defaultAssignmentTolerance)


#=========================================================================================
# Decorators for Spectrum attributes
#=========================================================================================

@singleton
class _includeInCopyList(list):
    """Singleton class to store the attributes to be included when making a copy of object.
    Attributes can be modified and can be either non-dimensional or dimension dependent,
    Dynamically filled by two decorators
    Stored as list of (attributeName, isMultiDimensional) tuples
    """

    def getNoneDimensional(self):
        """return a list of one-dimensional attribute names"""
        return [attr for attr, isNd in self if isNd == False]

    def getMultiDimensional(self):
        """return a list of one-dimensional attribute names"""
        return [attr for attr, isNd in self if isNd == True]

    def appendItem(self, attribute, isMultidimensional):
        _t = (attribute, isMultidimensional)
        if _t not in self:
            super().append(_t)


def _includeInCopy(func):
    """Decorator to define that an non-dimensional attribute is to be included when making a copy of object
    """
    storage = _includeInCopyList()
    storage.appendItem(func.__name__, isMultidimensional=False)
    return func


def _includeInDimensionalCopy(func):
    """Decorator to define that a dimensional attribute is to be included when making a copy of object
    """
    storage = _includeInCopyList()
    storage.appendItem(func.__name__, isMultidimensional=True)
    return func


def checkSpectrumPropertyValue(iterable: bool, unique: bool = False, allowNone: bool = False, types: tuple = (),
                               enumerated: tuple = (), mapping=None):
    """Decorator to check values of the Spectrum class property setters

    :param iterable: True, False: indicates that value should be an iterable
    :param unique: True, False: indicates if iterable items should be unique
    :param allowNone: True, False indicates if None value is allowed
    :param types: a tuple of allowed types for value; value is cast into first type
    :param enumerated: a tuple/list indicating that value should be one of the items of the tuple
    :param mapping: an optional (originalValue, mappedValue) mapping dict; applied to
                    the value or values-items
    """

    if allowNone:
        types = tuple(list(types) + [type(None)])
        if len(enumerated) > 0:
            enumerated = list(enumerated) + [None]

    if mapping is None:
        mapping = {}

    def checkType(obj, attributeName, value):
        """Check and optional casts value
        :param obj: the object checked
        :param attributeName: the attribute of object
        :param value:
        :return: value cast into types[0]
        """
        checkedValue = value
        if not allowNone and value is None:
            raise ValueError('Value for "%s" of %s cannot be None)' %
                             (attributeName, obj))

        if len(types) > 0:
            if not isinstance(value, types):
                typeNames = tuple(t.__name__ for t in types)
                raise ValueError('Value for "%s" of %s needs to be of type %s; got %r (type %s)' %
                                 (attributeName, obj, typeNames, value, type(value).__name__))
            # cast into types[0]
            if value is not None:
                checkedValue = types[0](value)
        return checkedValue

    def checkIterable(obj, attributeName, value):
        """Check for iterable properties
        """
        if not isinstance(value, (list, tuple, set)):
            raise ValueError('Value for "%s" of %s needs to be one of (list, tuple, set); got %r (type %s)' %
                             (attributeName, obj, value, type(value).__name__))

        if len(value) != obj.dimensionCount:
            raise ValueError('Value for "%s" of %s needs to be an iterable of length %d; got %r' %
                             (attributeName, obj, obj.dimensionCount, value))

        if unique:
            vals = [val for val in value if val is not None]
            if len(vals) != len(set(vals)):
                raise ValueError('The items of "%s" of %s need to be unique; got %r' %
                                 (attributeName, obj, value))

    def checkEnumerate(obj, attributeName, value):
        """Check if values needs to be in enumerate
        """
        if len(enumerated) > 0 and value not in enumerated:
            raise ValueError('Value for "%s" of %s needs to be of %r; got %r' %
                             (attributeName, obj, enumerated, value))
        return value

    @decorator.decorator
    def theDecorator(*args, **kwds):
        func = args[0]
        self = args[1]
        value = args[2]

        # if func.__name__ == 'measurementTypes':
        #     print('>>>', isIterable, types, enumerated)

        if iterable:
            checkIterable(self, func.__name__, value)

            # check the individual elements
            checkedValue = []
            for idx, val in enumerate(value):
                if len(mapping) > 0:
                    val = mapping.get(val, val)

                _itemName = '%s[%d]' % (func.__name__, idx)
                val = checkType(self, _itemName, val)
                val = checkEnumerate(self, _itemName, val)
                checkedValue.append(val)

        else:
            if len(mapping) > 0:
                value = mapping.get(value, value)
            checkedValue = checkType(self, func.__name__, value)
            checkedValue = checkEnumerate(self, func.__name__, checkedValue)

        return func(self, checkedValue)

    return theDecorator

#------------------------------------------------------------------------------------------------------
# Routines dealing with getting data sources
#------------------------------------------------------------------------------------------------------

def getSpectrumDataSource(path, dataFormat):
    """Get a SpectrumDataSource instance of type dataFormat for path
    :param path: a path as string or Path instance, optionally with redirect ($DATA, $INSIDE, $ALONGSIDE)
    :param dataFormat: a dataFormat identifier or None (denoting auto-detect)
    :return A (DataStore, SpectrumDataSource) tuple.
            The DataStore instance is None in case of zero-length path (except EmptySpectrum)
            The SpectrumDataSource instance might not be valid (for dataFormat; check isValid!)
            or can be None if auto-detect failed

    raises ValueError if path is None or dataFormat is inValid
    """
    # avoiding cyclic import
    from ccpn.core.lib.SpectrumDataSources.SpectrumDataSourceABC import \
        getDataSourceClass, getDataFormats, SpectrumDataSourceSuffixDict
    from ccpn.core.lib.SpectrumDataSources.EmptySpectrumDataSource import EmptySpectrumDataSource
    from ccpn.core.lib.DataStore import DataStore

    if path is None:
        raise ValueError(f'Undefined path')

    if len(path) == 0 and dataFormat != EmptySpectrumDataSource.dataFormat:
        return (None, None)
    dataStore = DataStore.newFromPath(path=path, dataFormat=dataFormat)
    _path = dataStore.aPath()  # The path without optional redirections

    if dataFormat is not None:
        # Get the corresponding class
        if (klass := getDataSourceClass(dataFormat=dataFormat)) is None:
            validFormats = tuple(getDataFormats().keys())
            raise ValueError(f'invalid dataFormat "{dataFormat}"; should be one of {validFormats}')

        dataSource = klass(path=_path)
        dataStore.dataFormat = dataFormat
        return (dataStore, dataSource)

    else:
        dataSource = None
        # Auto detect dataFormat from path; limit options using suffix dict
        _suffixDict = SpectrumDataSourceSuffixDict()
        klasses = _suffixDict.get(_path.suffix)
        for klass in klasses:
            dataSource = klass(path=_path)
            if dataSource.isValid or dataSource.shouldBeValid:
                # we found a valid one, or one that should be valid (but had errors)
                dataStore.dataFormat = klass.dataFormat
                return (dataStore, dataSource)
        # haven't found a valid class; either none matched, or isValid/shouldBeValid of the
        # last one we tried is False
        return (dataStore, dataSource)

#------------------------------------------------------------------------------------------------------

def _calibrateX1D(spectrum, currentPosition, newPosition):
    shift = newPosition - currentPosition
    spectrum.referenceValues = [spectrum.referenceValues[0] + shift]
    spectrum.positions = spectrum.positions + shift


def _calibrateY1D(spectrum, currentPosition, newPosition):
    shift = newPosition - currentPosition
    spectrum.intensities = spectrum.intensities + shift


def _calibrateXND(spectrum, strip, currentPosition, newPosition):
    # map the X change to the correct spectrum axis
    spectrumReferencing = list(spectrum.referenceValues)
    indices = getAxisCodeMatchIndices(strip.axisCodes, spectrum.axisCodes)

    # as modifying the spectrum, spectrum needs to be the second argument of getAxisCodeMatchIndices
    spectrumReferencing[indices[0]] = float(spectrumReferencing[indices[0]] + (newPosition - currentPosition))
    spectrum.referenceValues = spectrumReferencing


def _calibrateNDAxis(spectrum, axisIndex, currentPosition, newPosition):
    # map the X change to the correct spectrum axis
    spectrumReferencing = list(spectrum.referenceValues)

    # as modifying the spectrum, spectrum needs to be the second argument of getAxisCodeMatchIndices
    spectrumReferencing[axisIndex] = float(spectrumReferencing[axisIndex] + (newPosition - currentPosition))
    spectrum.referenceValues = spectrumReferencing


def _calibrateYND(spectrum, strip, currentPosition, newPosition):
    # map the Y change to the correct spectrum axis
    spectrumReferencing = list(spectrum.referenceValues)
    indices = getAxisCodeMatchIndices(strip.axisCodes, spectrum.axisCodes)

    # as modifying the spectrum, spectrum needs to be the second argument of getAxisCodeMatchIndices
    spectrumReferencing[indices[1]] = float(spectrumReferencing[indices[1]] + (newPosition - currentPosition))
    spectrum.referenceValues = spectrumReferencing


def _set1DRawDataFromCcpnInternal(spectrum):
    _positions = spectrum._getInternalParameter(SPECTRUM_POSITIONS)
    _intensities = spectrum._getInternalParameter(SPECTRUM_INTENSITIES)
    if not (_positions or _intensities):
        return
    spectrum.positions = np.array(_positions)
    spectrum.intensities = np.array(_intensities)


def _negLogLikelihood(deltas, queryPeakPositions, kde):
    shifted = queryPeakPositions - deltas
    return -kde.logpdf(shifted.T)


def align2HSQCs(refSpectrum, querySpectrum, refPeakListIdx=-1, queryPeakListIdx=-1):
    # Get hold of the peakLists in the two spectra
    queryPeakList = querySpectrum.peakLists[queryPeakListIdx]
    refPeakList = refSpectrum.peakLists[refPeakListIdx]

    # Create numpy arrays containing the peak positions of
    # each peakList

    refPeakPositions = np.array([peak.position for peak in refPeakList.peaks])
    queryPeakPositions = np.array([peak.position for peak in queryPeakList.peaks])

    # Align the two numpy arrays by centre of mass
    refMean = np.mean(refPeakPositions, axis=0)
    queryMean = np.mean(queryPeakPositions, axis=0)
    roughShift = queryMean - refMean
    shiftedQueryPeakPositions = queryPeakPositions - roughShift

    # Define a log-likelihood target for fitting the query
    # peak positions
    from scipy.optimize import leastsq
    from scipy.stats import gaussian_kde

    # Create the Gaussian KDE
    kde = gaussian_kde(refPeakPositions.T, bw_method=0.1)

    # Get hold of the values to overlay the two spectra
    shifts, status = leastsq(_negLogLikelihood, roughShift,
                             args=(queryPeakPositions, kde))

    # Get hold of the reference values of the querySpectrum
    queryRefValues = queryPeakList.spectrum.referenceValues

    # Calculate the corrected reference values
    correctedValues = np.array(queryRefValues) - shifts

    return shifts, correctedValues




# refSpectrum = project.spectra[]
# querySpectrum = project.spectra[]
# a = align2HSQCs(refSpectrum, querySpectrum, refPeakListIdx=-1, queryPeakListIdx=-1)
#
# for peak in querySpectrum.peakLists[-1].peaks:
#     p1,p2  = peak.position[0], peak.position[1]
#     p1x = p1-(a[0][0])
#     p2x = p2-(a[0][1])
#     peak.position = (p1x,p2x)


#------------------------------------------------------------------------------------------------------
# Spectrum projection
# GWV: Adapted from DataSource.py
#------------------------------------------------------------------------------------------------------

PROJECTION_METHODS = ('max', 'max above threshold', 'min', 'min below threshold',
                      'sum', 'sum above threshold', 'sum below threshold')


def _getProjection(spectrum, axisCodes: tuple, method: str = 'max', threshold=None):
    """Get projected plane defined by axisCodes using method and optional threshold
    return projected data array

    NB Called by Spectrum.getProjection
    """

    if method not in PROJECTION_METHODS:
        raise ValueError('For spectrum projection, method must be one of %s' % (PROJECTION_METHODS,))

    if method.endswith('threshold') and threshold is None:
        raise ValueError('For spectrum projection method "%s", threshold parameter must be defined' % (method,))

    projectedData = None
    for position, planeData in spectrum.allPlanes(axisCodes, exactMatch=True):

        if method == 'sum above threshold' or method == 'max above threshold':
            lowIndices = planeData < threshold
            planeData[lowIndices] = 0
        elif method == 'sum below threshold' or method == 'min below threshold':
            lowIndices = planeData > -threshold
            planeData[lowIndices] = 0

        if projectedData is None:
            # first plane
            projectedData = planeData
        elif method == 'max' or method == 'max above threshold':
            projectedData = np.maximum(projectedData, planeData)
        elif method == 'min' or method == 'min below threshold':
            projectedData = np.minimum(projectedData, planeData)
        else:
            projectedData += planeData

    return projectedData


#------------------------------------------------------------------------------------------------------
#  Baseline Correction for 1D spectra
# 14/2/2017
#
# Baseline Correction for 1D spectra.
# Multiple algorithms comparison:
#
# -Asl
# -Whittaker Smooth
# -AirPls
# -ArPls
# -Lowess
# -Polynomial Fit
#
# NB: Yet To be tested the newest algorithm found in literature based on machine learning:
# “Estimating complicated baselines in analytical signals using the iterative training of
# Bayesian regularized artificial neural networks. Abolfazl Valadkhani et al.
# Analytica Chimica Acta. September 2016 DOI: 10.1016/j.aca.2016.08.046
#
#------------------------------------------------------------------------------------------------------

from scipy.sparse import csc_matrix, eye, diags
from scipy import sparse
from scipy.sparse.linalg import spsolve


def als(y, lam=10 ** 2, p=0.001, nIter=10):
    """Implements an Asymmetric Least Squares (Asl) Smoothing
    baseline correction algorithm
    H C Eilers, Paul & F M Boelens, Hans. (2005). Baseline Correction with Asymmetric Least Squares Smoothing. Unpubl. Manuscr. .

    y = signal
    lam = smoothness, 10**2 ≤ λ ≤ 10**9.
    p = asymmetry, 0.001 ≤ p ≤ 0.1 is a good choice for a signal with positive peaks.
    niter = Number of iteration, default 10.

    """
    nIter = max(1, nIter)
    L = len(y)
    D = sparse.csc_matrix(np.diff(np.eye(L), 2))
    w = np.ones(L)
    for i in range(nIter):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + lam * D.dot(D.transpose())
        z = spsolve(Z, w * y)
        w = p * (y > z) + (1 - p) * (y < z)
    return z


def WhittakerSmooth(y, w, lambda_, differences=1):
    """
    Whittaker Smooth algorithm
    no licence, source from web
    Penalized least squares algorithm for background fitting

    input
        x: input data (i.e. chromatogram of spectrum)
        w: binary masks (value of the mask is zero if a point belongs to peaks and one otherwise)
        lambda_: parameter that can be adjusted by user. The larger lambda is,  the smoother the resulting background
        differences: integer indicating the order of the difference of penalties

    output
        the fitted background vector
    """
    X = np.matrix(y)
    m = X.size
    i = np.arange(0, m)
    E = eye(m, format='csc')
    D = E[1:] - E[:-1]  # numpy.diff() does not work with sparse matrix. This is a workaround.
    W = diags(w, 0, shape=(m, m))
    A = csc_matrix(W + (lambda_ * D.T * D))
    B = csc_matrix(W * X.T)
    background = spsolve(A, B)
    return np.array(background)


def airPLS(y, lambda_=100, porder=1, itermax=15):
    """
    airPLS algorithm
    no licence, source from web
    Adaptive iteratively reweighted penalized least squares for baseline fitting

    input
        x: input data (i.e. chromatogram of spectrum)
        lambda_: parameter that can be adjusted by user. The larger lambda is,  the smoother the resulting background, z
        porder: adaptive iteratively reweighted penalized least squares for baseline fitting

    output
        the fitted background vector
    """
    itermax = max(1, itermax)
    m = y.shape[0]
    w = np.ones(m)
    for i in range(1, itermax + 1):
        z = WhittakerSmooth(y, w, lambda_, porder)
        d = y - z
        dssn = np.abs(d[d < 0].sum())
        if (dssn < 0.001 * (abs(y)).sum() or i == itermax):
            if (i == itermax):
                getLogger().warning('max iteration reached!')
            break
        w[d >= 0] = 0  # d>0 means that this point is part of a peak, so its weight is set to 0 in order to ignore it
        w[d < 0] = np.exp(i * np.abs(d[d < 0]) / dssn)
        w[0] = np.exp(i * (d[d < 0]).max() / dssn)
        w[-1] = w[0]
    return z


def polynomialFit(x, y, order: int = 3):
    """
    polynomial Fit algorithm
    :param x: x values
    :param y: y values
    :param order: polynomial order
    :return: fitted baseline
    """
    fit = np.polyval(np.polyfit(x, y, deg=order), x)
    return fit


def arPLS(y, lambda_=5.e5, ratio=1.e-6, itermax=50):
    """
    arPLS algorithm
    Baseline correction using asymmetrically reweighted penalized least squares
    smoothing.
    http://pubs.rsc.org/en/Content/ArticleLanding/2015/AN/C4AN01061B#!divAbstract

    :param y: The 1D spectrum
    :param lambda_: (Optional) Adjusts the balance between fitness and smoothness.
                    A smaller lamda_ favors fitness.
                    Default is 1.e5.
    :param ratio: (Optional) Iteration will stop when the weights stop changing.
                    (weights_(i) - weights_(i+1)) / (weights_(i)) < ratio.
                    Default is 1.e-6.
    :returns: The smoothed baseline of y.
    """
    itermax = max(1, itermax)
    y = np.array(y)

    N = y.shape[0]

    E = eye(N, format='csc')
    # numpy.diff() does not work with sparse matrix. This is a workaround.
    # It creates the second order difference matrix.
    # [1 -2 1 ......]
    # [0 1 -2 1 ....]
    # [.............]
    # [.... 0 1 -2 1]
    D = E[:-2] - 2 * E[1:-1] + E[2:]

    H = lambda_ * D.T * D
    Y = np.matrix(y)

    w = np.ones(N)

    for i in range(itermax + 10):
        W = diags(w, 0, shape=(N, N))
        Q = W + H
        B = W * Y.T

        z = spsolve(Q, B)
        d = y - z
        dn = d[d < 0.0]

        m = np.mean(dn)
        if np.isnan(m):
            # add a tiny bit of noise to Y
            y2 = y.copy()
            if np.std(y) != 0.:
                y2 += (np.random.random(y.size) - 0.5) * np.std(y) / 1000.
            elif np.mean(y) != 0.0:
                y2 += (np.random.random(y.size) - 0.5) * np.mean(y) / 1000.
            else:
                y2 += (np.random.random(y.size) - 0.5) / 1000.
            y = y2
            Y = np.matrix(y2)
            W = diags(w, 0, shape=(N, N))
            Q = W + H
            B = W * Y.T

            z = spsolve(Q, B)
            d = y - z
            dn = d[d < 0.0]

            m = np.mean(dn)
        s = np.std(dn, ddof=1)

        wt = 1. / (1 + np.exp(2. * (d - (2 * s - m)) / s))

        # check exit condition
        condition = np.linalg.norm(w - wt) / np.linalg.norm(w)
        if condition < ratio:
            break
        if i > itermax:
            break
        w = wt

    return z


def arPLS_Implementation(y, lambdaValue=5.e4, maxValue=1e6, minValue=-1e6, itermax=10, interpolate=True):
    """
    Implementation of the  arPLS algorithm
    :param maxValue = maxValue of the baseline noise
    :param minValue = minValue of the baseline noise
    :param interpolate: Where are the peaks: interpolate the points from neighbours otherwise set them to 0.
    """

    lenghtY = len(y)
    sparseMatrix = eye(lenghtY, format='csc')
    differenceMatrix = sparseMatrix[:-2] - 2 * sparseMatrix[1:-1] + sparseMatrix[2:]
    H = lambdaValue * differenceMatrix.T * differenceMatrix

    Y = np.matrix(y)
    w = np.ones(lenghtY)

    for i in range(itermax):
        W = diags(w, 1, shape=(lenghtY, lenghtY))
        Q = W + H
        B = W * Y.T
        z = spsolve(Q, B)
        mymask = (z > maxValue) | (z < minValue)
        b = np.ma.masked_where(mymask, z)
        if interpolate:
            c = np.interp(np.where(mymask)[0], np.where(~mymask)[0], b[np.where(~mymask)[0]])
            b[np.where(mymask)[0]] = c
        else:
            b = np.ma.filled(b, fill_value=0)

    return b


# GWV disabled 5/8/2021
# def lowess(x, y):
#     """
#     LOWESS (Locally Weighted Scatterplot Smoothing).
#     A lowess function that outs smoothed estimates of endog
#     at the given exog values from points (exog, endog)
#     To use this, you need to install statsmodels in your miniconda:
#      - conda install statsmodels or pip install --upgrade --no-deps statsmodels
#     """
#
#     from scipy.interpolate import interp1d
#     #FIXME: invalid import
#     import statsmodels.api as sm
#
#     # introduce some floats in our x-values
#
#     # lowess will return our "smoothed" data with a y value for at every x-value
#     lowess = sm.nonparametric.lowess(y, x, frac=.3)
#
#     # unpack the lowess smoothed points to their values
#     lowess_x = list(zip(*lowess))[0]
#     lowess_y = list(zip(*lowess))[1]
#
#     # run scipy's interpolation. There is also extrapolation I believe
#     f = interp1d(lowess_x, lowess_y, bounds_error=False)
#
#     # this this generate y values for our xvalues by our interpolator
#     # it will MISS values outsite of the x window (less than 3, greater than 33)
#     # There might be a better approach, but you can run a for loop
#     # and if the value is out of the range, use f(min(lowess_x)) or f(max(lowess_x))
#     ynew = f(x)
#     return ynew


def nmrGlueBaselineCorrector(data, wd=20):
    """
    :param data: 1D ndarray
        One dimensional NMR data with real value (intensities)
        wd : float  Median window size in pts.
    :return: same as data
    """
    import nmrglue as ng

    data = ng.process.proc_bl.baseline_corrector(data, wd=wd)
    return data


def _getDefaultApiSpectrumColours(spectrum) -> Tuple[str, str]:
    """Get the default colours from the core spectrum class
    """
    # from ccpn.util.Colour import spectrumHexColours
    from ccpn.ui.gui.guiSettings import getColours, SPECTRUM_HEXCOLOURS, SPECTRUM_HEXDEFAULTCOLOURS
    from ccpn.util.Colour import hexToRgb, findNearestHex, invertRGBHue, rgbToHex

    dimensionCount = spectrum.dimensionCount
    serial = spectrum._serial
    expSerial = spectrum.experiment.serial

    spectrumHexColours = getColours().get(SPECTRUM_HEXCOLOURS)
    spectrumHexDefaultColours = getColours().get(SPECTRUM_HEXDEFAULTCOLOURS)

    # use different colour lists for 1d and Nd
    if dimensionCount < 2:
        colorCount = len(spectrumHexColours)
        step = ((colorCount // 2 - 1) // 2)
        kk = colorCount // 7
        index = expSerial - 1 + step * (serial - 1)
        posCol = spectrumHexColours[(kk * index + 10) % colorCount]
        negCol = spectrumHexColours[((kk + 1) * index + 10) % colorCount]

    else:
        try:
            # try and get the colourPalette number from the preferences, otherwise use 0
            from ccpn.framework.Application import getApplication

            colourPalette = getApplication().preferences.general.colourPalette
        except:
            colourPalette = 0

        if colourPalette == 0:
            # colours for Vicky :)
            colorCount = len(spectrumHexDefaultColours)
            step = ((colorCount // 2 - 1) // 2)
            index = expSerial - 1 + step * (serial - 1)
            posCol = spectrumHexDefaultColours[(2 * index) % colorCount]
            negCol = spectrumHexDefaultColours[(2 * index + 1) % colorCount]

        else:
            # automatic colours
            colorCount = len(spectrumHexColours)
            step = ((colorCount // 2 - 1) // 2)
            kk = 11  #colorCount // 11
            index = expSerial - 1 + step * (serial - 1)
            posCol = spectrumHexColours[(kk * index + 10) % colorCount]

            # invert the colour by reversing the ycbcr palette
            rgbIn = hexToRgb(posCol)
            negRGB = invertRGBHue(*rgbIn)
            oppCol = rgbToHex(*negRGB)
            # get the nearest one in the current colour list, so colourName exists
            negCol = findNearestHex(oppCol, spectrumHexColours)

    return (posCol, negCol)


def getDefaultSpectrumColours(self: 'Spectrum') -> Tuple[str, str]:
    """Get default positivecontourcolour, negativecontourcolour for Spectrum
    (calculated by hashing spectrum properties to avoid always getting the same colours
    Currently matches getDefaultColours in dataSource that is set through the api
    """
    return _getDefaultApiSpectrumColours(self)


def get1DdataInRange(x, y, xRange):
    """
    :param x:
    :param y:
    :param xRange:
    :return: x,y within the xRange (minXrange,maxXrange)

    """
    if xRange is None:
        return x, y
    point1, point2 = np.max(xRange), np.min(xRange)
    x_filtered = np.where((x <= point1) & (x >= point2))
    y_filtered = y[x_filtered]

    return x_filtered, y_filtered


def _recurseData(ii, dataList, startCondition, endCondition):
    """Iterate over the dataArray, subdividing each iteration
    """
    for data in dataList:

        if not data.size:
            continue

        # calculate the noise values
        flatData = data.flatten()

        SD = np.std(flatData)
        max = np.max(flatData)
        min = np.min(flatData)
        mn = np.mean(flatData)
        noiseLevel = mn + 3.5 * SD

        if not startCondition:
            startCondition[:] = [ii, data.shape, SD, max, min, mn, noiseLevel]
            endCondition[:] = startCondition[:]

        if SD < endCondition[2]:
            endCondition[:] = [ii, data.shape, SD, max, min, mn, noiseLevel]

        # stop iterating when all dimensions are <= 64 elements
        if any(dim > 64 for dim in data.shape):

            newData = [data]
            for jj in range(len(data.shape)):
                newData = [np.array_split(dd, 2, axis=jj) for dd in newData]
                newData = [val for sublist in newData for val in sublist]

            _recurseData(ii + 1, newData, startCondition, endCondition)


# keep for a minute - example of how to call _recurseData
# # iterate over the array to calculate noise at each level
# dataList = [dataArray]
# startCondition = []
# endCondition = []
# _recurseData(0, dataList, startCondition, endCondition)


#------------------------------------------------------------------------------------------------------


DEFAULTMULTIPLIER = 1.414214
DEFAULTLEVELS = 10
DEFAULTCONTOURBASE = 10000.0


def setContourLevelsFromNoise(spectrum, setNoiseLevel=True,
                              setPositiveContours=True, setNegativeContours=True,
                              useDefaultMultiplier=True, useDefaultLevels=True, useDefaultContourBase=False,
                              useSameMultiplier=True,
                              defaultMultiplier=DEFAULTMULTIPLIER, defaultLevels=DEFAULTLEVELS, defaultContourBase=DEFAULTCONTOURBASE):
    """Calculate the noise level, base contour level and positive/negative multipliers for the given spectrum
    """

    # parameter error checking
    if not isinstance(setNoiseLevel, bool):
        raise TypeError('setNoiseLevel is not boolean.')
    if not isinstance(setPositiveContours, bool):
        raise TypeError('setPositiveContours is not boolean.')
    if not isinstance(setNegativeContours, bool):
        raise TypeError('setNegativeContours is not boolean.')
    if not isinstance(useDefaultMultiplier, bool):
        raise TypeError('useDefaultMultiplier is not boolean.')
    if not isinstance(useDefaultLevels, bool):
        raise TypeError('useDefaultLevels is not boolean.')
    if not isinstance(useDefaultContourBase, bool):
        raise TypeError('useDefaultContourBase is not boolean.')
    if not isinstance(useSameMultiplier, bool):
        raise TypeError('useSameMultiplier is not boolean.')

    if not (isinstance(defaultMultiplier, float) and defaultMultiplier > 0):
        raise TypeError('defaultMultiplier is not a positive float.')
    if not (isinstance(defaultLevels, int) and defaultLevels > 0):
        raise TypeError('defaultLevels is not a positive int.')
    if not (isinstance(defaultContourBase, float) and defaultContourBase > 0):
        raise TypeError('defaultContourBase is not a positive float.')

    if spectrum.dimensionCount == 1:
        return

    # exit if nothing set
    if not (setNoiseLevel or setPositiveContours or setNegativeContours):
        return

    if any(x != 'Frequency' for x in spectrum.dimensionTypes):
        raise NotImplementedError("setContourLevelsFromNoise not implemented for processed frequency spectra, dimension types were: {}".format(spectrum.dimensionTypes, ))

    getLogger().info("estimating noise level for spectrum %s" % str(spectrum.pid))
    if setNoiseLevel:
        # get noise level using random sampling method - may be slow for large spectra
        noise = getNoiseEstimate(spectrum)
        base = spectrum.noiseLevel = noise.noiseLevel
    else:
        base = spectrum.noiseLevel
        # need to generate a min/max
        noise = getContourEstimate(spectrum)

    # noise => noise.mean, noise.std, noise.min, noise.max, noise.noiseLevel

    if useDefaultLevels:
        posLevels = defaultLevels
        negLevels = defaultLevels
    else:
        # get from the spectrum
        posLevels = spectrum.positiveContourCount
        negLevels = spectrum.negativeContourCount

    if useDefaultMultiplier:
        # use default as root2
        posMult = negMult = defaultMultiplier
    else:
        # calculate multiplier to give contours across range of spectrum; trap base = 0
        mx = noise.max
        mn = noise.min

        posMult = pow(abs(mx / base), 1 / posLevels) if base else 0.0
        if useSameMultiplier:
            negMult = posMult
        else:
            negMult = pow(abs(mn / base), 1 / negLevels) if base else 0.0

    if setPositiveContours:
        try:
            spectrum.positiveContourBase = base
            spectrum.positiveContourFactor = posMult
        except Exception as es:

            # set to defaults if an error occurs
            spectrum.positiveContourBase = defaultContourBase
            spectrum.positiveContourFactor = defaultMultiplier
            getLogger().warning('Error setting contour levels - %s', str(es))

        spectrum.positiveContourCount = posLevels

    if setNegativeContours:
        try:
            spectrum.negativeContourBase = -base
            spectrum.negativeContourFactor = negMult
        except Exception as es:

            # set to defaults if an error occurs
            spectrum.negativeContourBase = -defaultContourBase
            spectrum.negativeContourFactor = defaultMultiplier
            getLogger().warning('Error setting contour levels - %s', str(es))

        spectrum.negativeContourCount = negLevels

    return


def getContourLevelsFromNoise(spectrum,
                              setPositiveContours=False, setNegativeContours=False,
                              useDefaultMultiplier=True, useDefaultLevels=True, useDefaultContourBase=False,
                              useSameMultiplier=True,
                              defaultMultiplier=DEFAULTMULTIPLIER, defaultLevels=DEFAULTLEVELS, defaultContourBase=DEFAULTCONTOURBASE):
    """Calculate the noise level, base contour level and positive/negative multipliers for the given spectrum
    """

    # parameter error checking
    if not isinstance(setPositiveContours, bool):
        raise TypeError('setPositiveContours is not boolean.')
    if not isinstance(setNegativeContours, bool):
        raise TypeError('setNegativeContours is not boolean.')
    if not isinstance(useDefaultMultiplier, bool):
        raise TypeError('useDefaultMultiplier is not boolean.')
    if not isinstance(useDefaultLevels, bool):
        raise TypeError('useDefaultLevels is not boolean.')
    if not isinstance(useDefaultContourBase, bool):
        raise TypeError('useDefaultContourBase is not boolean.')
    if not isinstance(useSameMultiplier, bool):
        raise TypeError('useSameMultiplier is not boolean.')

    if not (isinstance(defaultMultiplier, float) and defaultMultiplier > 0):
        raise TypeError('defaultMultiplier is not a positive float.')
    if not (isinstance(defaultLevels, int) and defaultLevels > 0):
        raise TypeError('defaultLevels is not a positive int.')
    if not (isinstance(defaultContourBase, float) and defaultContourBase > 0):
        raise TypeError('defaultContourBase is not a positive float.')

    if spectrum.dimensionCount == 1:
        return [None] * 6

    if any(x != 'Frequency' for x in spectrum.dimensionTypes):
        raise NotImplementedError("getContourLevelsFromNoise not implemented for processed frequency spectra, dimension types were: {}".format(spectrum.dimensionTypes, ))

    # need to generate a min/max
    noise = getContourEstimate(spectrum)

    # noise => noise.mean, noise.std, noise.min, noise.max, noise.noiseLevel

    if useDefaultLevels:
        posLevels = defaultLevels
        negLevels = defaultLevels
    else:
        # get from the spectrum
        posLevels = spectrum.positiveContourCount
        negLevels = spectrum.negativeContourCount

    if useDefaultContourBase:
        posBase = defaultContourBase
    else:
        # calculate the base levels
        posBase = spectrum.noiseLevel
    negBase = -posBase if posBase else 0.0

    if useDefaultMultiplier:
        # use default as root2
        posMult = negMult = defaultMultiplier
    else:
        # calculate multiplier to give contours across range of spectrum; trap base = 0
        mx = noise.max
        mn = noise.min

        posMult = pow(abs(mx / posBase), 1 / posLevels) if posBase else 0.0
        if useSameMultiplier:
            negMult = posMult
        else:
            negMult = pow(abs(mn / negBase), 1 / negLevels) if negBase else 0.0

    if not setPositiveContours:
        posBase = posMult = posLevels = None

    if not setNegativeContours:
        negBase = negMult = negLevels = None

    return posBase, negBase, posMult, negMult, posLevels, negLevels


def getClippedRegion(spectrum, strip, sort=False):
    """
    Return the clipped region, bounded by the (ppmPoint(1), ppmPoint(n)) in visible order

    If sorting is True, returns a tuple(tuple(minPpm, maxPpm), ...) for each region
    else returns tuple(tuple(ppmLeft, ppmRight), ...)

    :param spectrum:
    :param strip:
    :return:
    """

    # calculate the visible region
    selectedRegion = [strip.getAxisRegion(0), strip.getAxisRegion(1)]
    for n in strip.orderedAxes[2:]:
        selectedRegion.append((n.region[0], n.region[1]))

    # use the ppmArrays to get the first/last point of the data
    if spectrum.dimensionCount == 1:
        ppmArrays = [spectrum.getPpmArray(dimension=1)]
    else:
        ppmArrays = [spectrum.getPpmArray(dimension=dim) for dim in spectrum.getByAxisCodes('dimensions', strip.axisCodes)]

    # clip to the ppmArrays, not taking aliased regions into account
    if sort:
        return tuple(tuple(sorted(np.clip(region, np.min(limits), np.max(limits)))) for region, limits in zip(selectedRegion, ppmArrays))
    else:
        return tuple(tuple(np.clip(region, np.min(limits), np.max(limits))) for region, limits in zip(selectedRegion, ppmArrays))


def getNoiseEstimateFromRegion(spectrum, strip):
    """
    Get the noise estimate from the visible region of the strip

    :param spectrum:
    :param strip:
    :return:
    """

    # calculate the region over which to estimate the noise
    sortedSelectedRegion = getClippedRegion(spectrum, strip, sort=True)
    if spectrum.dimensionCount == 1:
        indices = [1]
    else:
        indices = spectrum.getByAxisCodes('dimensions', strip.axisCodes)

    regionDict = {}
    for idx, ac, region in zip(indices, strip.axisCodes, sortedSelectedRegion):
        regionDict[ac] = tuple(region)

    # get the data
    with notificationEchoBlocking():
        dataArray = spectrum.getRegion(**regionDict)

    # calculate the noise values
    flatData = dataArray.flatten()

    std = np.std(flatData)
    max = np.max(flatData)
    min = np.min(flatData)
    mean = np.mean(flatData)

    value = NoiseEstimateTuple(mean=mean,
                               std=std if std != 0 else 1.0,
                               min=min, max=max,
                               noiseLevel=None)

    # noise function is defined here, but needs cleaning up
    return _noiseFunc(value)


def getSpectrumNoise(spectrum):
    """
    Get the noise level for a spectrum. If the noise level is not already set it will
    be set at an estimated value.

    .. describe:: Input

    spectrum

    .. describe:: Output

    Float
    """
    noise = spectrum.noiseLevel
    if noise is None:
        noise = getNoiseEstimate(spectrum)
        spectrum.noiseLevel = noise.noiseLevel
    return noise


def getNoiseEstimate(spectrum):
    """Get an estimate of the noiseLevel from the spectrum

    noiseLevel is calculated as abs(mean) + 3.5 * SD

    Calculated from a random subset of points
    """
    # NOTE:ED more detail needed

    fractPerAxis = 0.03
    subsetFract = 0.2
    fract = 0.1
    maxSamples = 10000

    npts = spectrum.pointCounts

    # take % of points in each axis
    _fract = (fractPerAxis ** len(npts))
    nsamples = min(int(np.prod(npts) * _fract), maxSamples)
    nsubsets = max(1, int(nsamples * subsetFract))

    with notificationEchoBlocking():
        return _getNoiseEstimate(spectrum, nsamples, nsubsets, fract)


def getContourEstimate(spectrum):
    """Get an estimate of the contour settings from the spectrum
    Calculated from a random subset of points
    """

    fractPerAxis = 0.03
    subsetFract = 0.01
    fract = 0.1
    maxSamples = 10000

    npts = spectrum.pointCounts

    # take % of points in each axis
    _fract = (fractPerAxis ** len(npts))
    nsamples = min(int(np.prod(npts) * _fract), maxSamples)
    nsubsets = max(1, int(nsamples * subsetFract))

    with notificationEchoBlocking():
        return _getContourEstimate(spectrum, nsamples, nsubsets, fract)


def _noiseFunc(value):
    # take the 'value' NoiseEstimateTuple and add the noiseLevel
    return NoiseEstimateTuple(mean=value.mean,
                              std=value.std,
                              min=value.min, max=value.max,
                              noiseLevel=abs(value.mean) + 3.5 * value.std)

def _getNoiseRegionFromLimits(regionData, yLower, yUpper):
    """Get the sd from the region between two limits value"""
    yValues = regionData
    indices = (yValues >= yLower) & (yValues <= yUpper)
    noiseRegion = yValues[indices]
    return noiseRegion

def _estimateNoiseSDforSpectrumNoiseLevel(spectrum, stdFactor=1.1, noiseLevelFactor=3.5):

    regionData = spectrum.getAllRegionData()
    regionData = regionData.flatten()
    noiseLevel = spectrum.noiseLevel
    if spectrum.noiseLevel is None:
        raise ValueError('This routine requires the noiseLevel to be set')
    yUpper =  noiseLevel/noiseLevelFactor
    yLower =  - yUpper
    noiseRegion = _getNoiseRegionFromLimits(regionData, yLower, yUpper)
    sd = np.std(noiseRegion)
    sd *= stdFactor
    return float(sd)

def _getNoiseEstimate(spectrum, nsamples=1000, nsubsets=10, fraction=0.1):
    """
    Estimate the noise level for a spectrum.

    'nsamples' random samples are taken from the spectrum
    'nsubsets' is the number of random permutations of data taken from the
    and finding subsets with the lowest standard deviation

    A tuple (mean, SD, min, max noiseLevel) is returned from the subset with the lowest standard deviation.
    mean is the mean of the minimum random subset, SD is the standard deviation, min/max are the minimum/maximum values,
    and noiseLevel is the estimated noiseLevel caluated as abs(mean) + 3.5 * SD

    :param spectrum: input spectrum
    :param nsamples: number reandom samples
    :param nsubsets: number of subsets
    :param fraction: subset fraction
    :return: tuple(mean, SD, min, max, noiseLevel)
    """

    npts = spectrum.pointCounts
    if not isinstance(nsamples, int):
        raise TypeError('nsamples must be an int')
    if not (0 < nsamples <= np.prod(npts)):
        raise ValueError(f'nsamples must be in range [1, {np.prod(npts)}]')
    if not isinstance(nsubsets, int):
        raise TypeError('nsubsets must be an int')
    if not (0 < nsubsets <= nsamples):
        # not strictly necessary but stops huge values
        raise ValueError(f'nsubsets must be in range [1, {nsamples}]')
    if not isinstance(fraction, float):
        raise TypeError('fraction must be a float')
    if not (0 < fraction <= 1.0):
        raise ValueError('fraction must be i the range (0, 1]')

    # create a list of random points in the spectrum, get only points that are not nan/inf
    # getPointValue is the slow bit
    allPts = [[min(n - 1, int(n * random.random()) + 1) for n in npts] for i in range(nsamples)]
    _list = np.array([spectrum._getPointValue(pt) for pt in allPts], dtype=np.float32)
    data = _list[np.isfinite(_list)]
    fails = nsamples - len(data)

    if fails:
        getLogger().warning(f'Attempt to access {fails} non-existent data points in spectrum {spectrum}')

    # check whether there are too many bad numbers in the data
    good = nsamples - fails
    if good == 0:
        getLogger().warning(f'Spectrum {spectrum} contains all bad points - check possible endian-ness')
        return NoiseEstimateTuple(mean=None, std=None, min=None, max=None, noiseLevel=1.0)
    elif good < 10:  # arbitrary minimum number of bad points
        getLogger().warning(f'Spectrum {spectrum} contains minimal data')
        maxValue = max([abs(x) for x in data])
        if maxValue > 0:
            return NoiseEstimateTuple(mean=None, std=None, min=None, max=None, noiseLevel=0.1 * maxValue)
        else:
            return NoiseEstimateTuple(mean=None, std=None, min=None, max=None, noiseLevel=1.0)

    m = max(1, int(nsamples * fraction))

    funcs = {'mean': np.mean, 'std': np.std, 'min': np.min, 'max': np.max}

    def meanStd():
        # take m random values from data, and return mean/SD, data is already finite
        y = np.random.choice(data, m)
        attrs = {attr: func(y) for attr, func in funcs.items()}
        if all(np.isfinite(val) for val in attrs.values() if val is not None):
            # only return valid results - too large will give inf
            return NoiseEstimateTuple(noiseLevel=None, **attrs)

    # generate 'nsubsets' noiseEstimates and take the one with the minimum standard deviation
    valid = list({meanStd() for i in range(nsubsets)} - {None})
    if valid:
        value = min(valid, key=lambda mSD: mSD.std)
        value = NoiseEstimateTuple(mean=value.mean,
                                   std=value.std if value.std != 0 else 1.0,
                                   min=value.min, max=value.max,
                                   noiseLevel=None)

        value = _noiseFunc(value)
    else:
        # all None means that there is a major problem with the data - probably endian-ness
        getLogger().warning(f'Spectrum {spectrum} contains all bad points - check possible endian-ness')
        value = NoiseEstimateTuple(mean=None, std=None, min=None, max=None, noiseLevel=1.0)

    return value


def _getDefaultOrdering(spectrum):
    # axisOption = spectrum.project.application.preferences.general.axisOrderingOptions

    preferredAxisOrder = spectrum._preferredAxisOrdering
    if preferredAxisOrder is not None:

        specAxisOrder = spectrum.axisCodes
        axisOrder = [specAxisOrder[ii] for ii in preferredAxisOrder]

    else:
        # sets the Nd default to HCN (or possibly 2d to HC)
        specAxisOrder = spectrum.axisCodes
        pOrder = spectrum.searchAxisCodePermutations(('H', 'C', 'N'))
        if pOrder:
            spectrum._preferredAxisOrdering = pOrder
            axisOrder = [specAxisOrder[ii] for ii in pOrder]
            getLogger().debug('setting default axisOrdering: ', str(axisOrder))

        else:

            # just set to the normal ordering
            spectrum._preferredAxisOrdering = tuple(ii for ii in range(spectrum.dimensionCount))
            axisOrder = specAxisOrder

            # try permutations of repeated codes
            duplicates = [('H', 'H'), ('C', 'C'), ('N', 'N')]
            for dCode in duplicates:
                pOrder = spectrum.searchAxisCodePermutations(dCode)

                # if permutation found and matches first axis
                if pOrder and pOrder[0] == 0:
                    spectrum._preferredAxisOrdering = pOrder
                    axisOrder = [specAxisOrder[ii] for ii in pOrder]
                    getLogger().debug('setting duplicate axisOrdering: ', str(axisOrder))
                    break

    return axisOrder


def _getContourEstimate(spectrum, nsamples=1000, nsubsets=10, fraction=0.1):
    """
    Estimate the contour levels for a spectrum.

    'nsamples' random samples are taken from the spectrum
    'nsubsets' is the number of random permutations of data taken from the
    and finding subsets with the lowest standard deviation

    A tuple (mean, SD, min, max noiseLevel) is returned from the subset with the lowest standard deviation.
    mean is the mean of the minimum random subset, SD is the standard deviation, min/max are the minimum/maximum values,
    and noiseLevel is the estimated noiseLevel caluated as abs(mean) + 3.5 * SD

    :param spectrum: input spectrum
    :param nsamples: number reandom samples
    :param nsubsets: number of subsets
    :param fraction: subset fraction
    :return: tuple(mean, SD, min, max, noiseLevel)
    """

    npts = spectrum.pointCounts
    if not isinstance(nsamples, int):
        raise TypeError('nsamples must be an int')
    if not (0 < nsamples <= np.prod(npts)):
        raise ValueError(f'nsamples must be in range [1, {np.prod(npts)}]')
    if not isinstance(nsubsets, int):
        raise TypeError('nsubsets must be an int')
    if not (0 < nsubsets <= nsamples):
        # not strictly necessary but stops huge values
        raise ValueError(f'nsubsets must be in range [1, {nsamples}]')
    if not isinstance(fraction, float):
        raise TypeError('fraction must be a float')
    if not (0 < fraction <= 1.0):
        raise ValueError('fraction must be i the range (0, 1]')

    # create a list of random points in the spectrum, get only points that are not nan/inf
    # getPointValue is the slow bit
    allPts = [[min(n - 2, int(n * random.random())) for n in npts] for i in range(nsamples)]
    _list = np.array([spectrum.getPointValue(pt) for pt in allPts], dtype=np.float32)
    data = _list[np.isfinite(_list)]
    fails = nsamples - len(data)

    if fails:
        getLogger().warning(f'Attempt to access {fails} non-existent data points in spectrum {spectrum}')

    # check whether there are too many bad numbers in the data
    good = nsamples - fails
    if good == 0:
        getLogger().warning(f'Spectrum {spectrum} contains all bad points')
        return NoiseEstimateTuple(mean=None, std=None, min=None, max=None, noiseLevel=1.0)
    elif good < 10:  # arbitrary number of bad points
        getLogger().warning(f'Spectrum {spectrum} contains minimal data')
        maxValue = max([abs(x) for x in data])
        if maxValue > 0:
            return NoiseEstimateTuple(mean=None, std=None, min=None, max=None, noiseLevel=0.1 * maxValue)
        else:
            return NoiseEstimateTuple(mean=None, std=None, min=None, max=None, noiseLevel=1.0)

    value = NoiseEstimateTuple(mean=None,
                               std=None,
                               min=np.min(data), max=np.max(data),
                               noiseLevel=None)

    return value


def _old_estimateSNR(noiseLevels, signalPoints, factor=2.5):
    """
    This calculation methods, internally known as the Varian Method,
     is deprecated from Version 3.2.1 onwards.
    SNratio = factor*(height/|NoiseMax-NoiseMin|)
    :param noiseLevels: (max, min) floats
    :param signalPoints: iterable of floats estimated to be signal or peak heights
    :param factor: default 2.5
    :return: array of snr for each point compared to the delta noise level
    """
    maxNL = np.max(noiseLevels)
    minNL = np.min(noiseLevels)
    dd = abs(maxNL - minNL)
    pp = np.array([s for s in signalPoints])
    if dd != 0 and dd is not None:
        snRatios = (factor * pp) / dd
        return abs(snRatios)
    return [None] * len(signalPoints)

class _1DRawDataDict(dict):
    """
    Class to contain Spectra Raw ppmPosition and Intensities
    This object is extremely important to speed up the execution of peak picking and peak snapping for extremely large 1D datasets.
    It is a sort of  on-the-fly caching of the raw ppmPositions and intensities array for the requested spectra, without the overhead of looking to the core classes (more than necessary).

    """
    def __init__(self, spectra=None):
        super(_1DRawDataDict, self).__init__()
        from ccpn.framework.Application import getProject

        getLogger().info('Building 1D raw data dictionary...')
        project = getProject()
        dd =  {}
        spectra = spectra or project.spectra
        for sp in tqdm(spectra):
            if sp.dimensionCount == 1:
                dd[sp] = (sp.positions,sp.intensities)
        self.update(dd)
        getLogger().info('Building 1D raw data dictionary. Completed')

def _filterROI1Darray(x, y, roi):
    """ Return region included in the ROI ppm position"""
    mask = _getMaskedRegionInsideLimits(x, roi)
    return x[mask], y[mask]


def _getMaskedRegionInsideLimits(x, limits):
    """
    Return an array of Booleans for the condition.
    True if the point in the array is within the limits, False otherwise.
    Limits and Array can be positives and/or negatives
    """
    import numpy.ma as ma

    mask = ma.masked_inside(x, *limits)
    return mask.mask


def _filtered1DArray(data, ignoredRegions):
    # returns an array without ignoredRegions. Used for automatic 1d peak picking
    ppmValues = data[0]
    masks = []
    ignoredRegions = [sorted(pair, reverse=True) for pair in ignoredRegions]
    for region in ignoredRegions:
        mask = (ppmValues > region[0]) | (ppmValues < region[1])
        masks.append(mask)
    fullmask = [all(mask) for mask in zip(*masks)]
    newArray = (np.ma.MaskedArray(data, mask=np.logical_not((fullmask, fullmask))))
    return newArray


def _initExpBoundResonances(experiment):
    """
    # CCPNInternal  - API Level routine -
    Refresh the covalently bound status for any resonances connected
    via peaks in a given experiment.
    """
    resonances = {}
    for spectrum in experiment.dataSources:
        for peakList in spectrum.peakLists:
            for peak in peakList.peaks:
                for peakDim in peak.peakDims:
                    for contrib in peakDim.peakDimContribs:
                        resonances[contrib.resonance] = None
    for resonance in resonances.keys():
        _getBoundResonances(resonance, recalculate=True)


def _setApiExpTransfers(experiment, overwrite=True):
    """
    # CCPNInternal  - API Level routine -
    Set up the ExpTransfers for an experiment using available refExperiment
    information. Boolean option to remove any existing transfers.
    List of Nmr.ExpTransfers
    """

    if not experiment.refExperiment:
        for expTransfer in experiment.expTransfers:
            expTransfer.delete()

        _initExpBoundResonances(experiment)
        return

    if experiment.expTransfers:
        if not overwrite:
            return list(experiment.expTransfers)
        else:
            for expTransfer in experiment.expTransfers:
                expTransfer.delete()

    visibleSites = {}
    for expDim in experiment.expDims:
        for expDimRef in expDim.expDimRefs:
            if not expDimRef.refExpDimRef:
                continue

            measurement = expDimRef.refExpDimRef.expMeasurement
            if measurement.measurementType in ('Shift', 'shift', 'MQShift'):
                for atomSite in measurement.atomSites:
                    if atomSite not in visibleSites:
                        visibleSites[atomSite] = []

                    visibleSites[atomSite].append(expDimRef)

    transferDict = {}
    for atomSite in visibleSites:
        expDimRefs = visibleSites[atomSite]

        for expTransfer in atomSite.expTransfers:
            atomSiteA, atomSiteB = expTransfer.atomSites

            if (atomSiteA in visibleSites) and (atomSiteB in visibleSites):
                if transferDict.get(expTransfer) is None:
                    transferDict[expTransfer] = []
                transferDict[expTransfer].extend(expDimRefs)

    # Indirect transfers, e.g. Ch_hC.NOESY or H_hC.NOESY
    indirectTransfers = set()
    for expGraph in experiment.refExperiment.nmrExpPrototype.expGraphs:
        for expTransfer in expGraph.expTransfers:
            if (expTransfer not in transferDict) and \
                    (expTransfer.transferType in longRangeTransfers):
                atomSiteA, atomSiteB = expTransfer.atomSites

                if atomSiteA not in visibleSites:
                    for expTransferA in atomSiteA.expTransfers:
                        if expTransferA.transferType != 'onebond':
                            continue

                        atomSites = list(expTransferA.atomSites)
                        atomSites.remove(atomSiteA)
                        atomSiteC = atomSites[0]

                        if atomSiteC in visibleSites:
                            atomSiteA = atomSiteC
                            break

                if atomSiteB not in visibleSites:
                    for expTransferB in atomSiteB.expTransfers:
                        if expTransferB.transferType != 'onebond':
                            continue

                        atomSites = list(expTransferB.atomSites)
                        atomSites.remove(atomSiteB)
                        atomSiteD = atomSites[0]

                        if atomSiteD in visibleSites:
                            atomSiteB = atomSiteD
                            break

                if (atomSiteA in visibleSites) and (atomSiteB in visibleSites):
                    expDimRefsA = visibleSites[atomSiteA]
                    expDimRefsB = visibleSites[atomSiteB]
                    transferDict[expTransfer] = expDimRefsA + expDimRefsB
                    indirectTransfers.add(expTransfer)

    expTransfers = []
    for refTransfer in transferDict.keys():
        expDimRefs = frozenset(transferDict[refTransfer])
        if len(expDimRefs) == 2:
            transferType = refTransfer.transferType
            expTransfer = experiment.findFirstExpTransfer(expDimRefs=expDimRefs)

            if expTransfer:
                # normally this would not need setting
                # but we renamed NOESY to through-space so this catches that situation
                expTransfer.transferType = transferType
            else:
                expTransfer = experiment.newExpTransfer(transferType=transferType,
                                                        expDimRefs=expDimRefs)

            if refTransfer in indirectTransfers:
                isDirect = False
            else:
                isDirect = True

            expTransfer.isDirect = isDirect
            expTransfers.append(expTransfer)

    _initExpBoundResonances(experiment)
    return expTransfers


def _getAvailableReferenceExperimentDimensions(spectrum, apiRefExperiment=None) -> tuple:
    """Return list of available reference experiment dimensions based on spectrum isotopeCodes
    """
    nCodes = tuple(val.strip('0123456789') for val in spectrum.isotopeCodes)

    if apiRefExperiment:
        # get the permutations of the axisCodes and nucleusCodes
        axisCodePerms = list(permutations(apiRefExperiment.axisCodes))
        nucleusPerms = list(permutations(apiRefExperiment.nucleusCodes))

        # return only those that match the current nucleusCodes (from isotopeCodes)
        result = tuple(ac for ac, nc in zip(axisCodePerms, nucleusPerms) if nCodes == nc)
        return result

    else:
        return ()


def _getApiExpTransfers(spectrum, referenceExperimentName, referenceDimensions):
    """Get the magnetisation-transfers for the specified experimentName.
    Either matches against the existing experiment if the experiment has been set in the spectrum,
    or the experiment found in the reference-experiments.


    :param spectrum: target spectrum
    :param referenceExperimentName: experimentName to match against magnetisation-transfers
    :param referenceDimensions: dimension names to match against
    :return: list of magnetisation-transfer-tuples
    """

    magTransfers = []
    apiRefExperiment = None
    try:
        for nmrExpPrototype in spectrum._wrappedData.root.sortedNmrExpPrototypes():
            for apiRefExperiment in nmrExpPrototype.sortedRefExperiments():
                # check if the given value is in the STD nomenclature rather than the CCPN! E.g.: standard=COSY; CCPN=HH
                ccpnName = apiRefExperiment.name
                standardName = apiRefExperiment.synonym

                if referenceExperimentName in [ccpnName, standardName]:
                    # set API RefExperiment and ExpTransfer
                    raise StopIteration

    except StopIteration:
        # found the correct apiRefExperiment

        longRangeTransfers = ('through-space',)

        visibleSites = {}
        useRefs = False
        if False:  # apiRefExperiment == spectrum._wrappedData.experiment.refExperiment:
            # expRefDims should always match the refExperiment atomSites?
            for expDim in spectrum._wrappedData.experiment.expDims:
                for expDimRef in expDim.expDimRefs:
                    if not expDimRef.refExpDimRef:
                        continue

                    measurement = expDimRef.refExpDimRef.expMeasurement
                    if measurement.measurementType in ('Shift', 'shift', 'MQShift'):
                        for atomSite in measurement.atomSites:
                            vs = visibleSites.setdefault(atomSite, [])
                            vs.append(expDimRef)

        else:
            for refExpDim in apiRefExperiment.refExpDims:
                for refExpDimRef in refExpDim.refExpDimRefs:
                    measurement = refExpDimRef.expMeasurement
                    if measurement.measurementType in ('Shift', 'shift', 'MQShift'):
                        for atomSite in measurement.atomSites:
                            vs = visibleSites.setdefault(atomSite, [])
                            vs.append(refExpDimRef)
            useRefs = True

        transferDict = {}
        for atomSite in visibleSites:
            expDimRefs = visibleSites[atomSite]

            for expTransfer in atomSite.expTransfers:
                atomSiteA, atomSiteB = expTransfer.atomSites

                if (atomSiteA in visibleSites) and (atomSiteB in visibleSites):
                    td = transferDict.setdefault(expTransfer, [])
                    td.extend(expDimRefs)

        indirectTransfers = set()
        for expGraph in apiRefExperiment.nmrExpPrototype.expGraphs:
            for expTransfer in expGraph.expTransfers:
                if (expTransfer not in transferDict) and \
                        (expTransfer.transferType in longRangeTransfers):
                    atomSiteA, atomSiteB = expTransfer.atomSites

                    if atomSiteA not in visibleSites:
                        for expTransferA in atomSiteA.expTransfers:
                            if expTransferA.transferType != 'onebond':
                                continue

                            atomSites = list(expTransferA.atomSites)
                            atomSites.remove(atomSiteA)
                            atomSiteC = atomSites[0]

                            if atomSiteC in visibleSites:
                                atomSiteA = atomSiteC
                                break

                    if atomSiteB not in visibleSites:
                        for expTransferB in atomSiteB.expTransfers:
                            if expTransferB.transferType != 'onebond':
                                continue

                            atomSites = list(expTransferB.atomSites)
                            atomSites.remove(atomSiteB)
                            atomSiteD = atomSites[0]

                            if atomSiteD in visibleSites:
                                atomSiteB = atomSiteD
                                break

                    if (atomSiteA in visibleSites) and (atomSiteB in visibleSites):
                        expDimRefsA = visibleSites[atomSiteA]
                        expDimRefsB = visibleSites[atomSiteB]
                        transferDict[expTransfer] = expDimRefsA + expDimRefsB
                        indirectTransfers.add(expTransfer)

        magTransfers = set()
        for refTransfer in transferDict.keys():
            expDimRefs = frozenset(transferDict[refTransfer])
            if len(expDimRefs) == 2:
                transferType = refTransfer.transferType

                isDirect = not (refTransfer in indirectTransfers)
                try:
                    if not useRefs:
                        # dims = sorted(ii + 1 for exp in expDimRefs for ii, val in enumerate(spectrum.spectrumReferences) if exp == val._expDimRef)
                        dims = sorted([ii + 1, exp.refExpDimRef.axisCode] for exp in expDimRefs for ii, val in enumerate(spectrum.spectrumReferences)
                                      if exp == val._expDimRef and exp.refExpDimRef.axisCode in referenceDimensions)

                    else:
                        # read from the reference experiment - spectrum.axisCode order?
                        # refAxes = [y for x in referenceDimensions for y in x.split(',')]
                        refAxes = [x.split(',') if x else [] for x in referenceDimensions]

                        dims = []
                        for refExp in expDimRefs:
                            for ii, val in enumerate(apiRefExperiment.refExpDims):
                                if refExp in list(val.refExpDimRefs):
                                    if (idx := [jj + 1 for jj, ra in enumerate(refAxes) if refExp.axisCode in ra]):
                                        dims.append([idx[0], refExp.axisCode])
                        dims = sorted(dims)

                    if len(dims) == 2 and dims[0][0] != dims[1][0]:
                        # only add the valid transfers
                        magTransfers.add(MagnetisationTransferTuple(dims[0][0], dims[1][0], transferType, not isDirect))

                except Exception:
                    dims = 'not found'

        magTransfers = list(sorted(magTransfers))

    return magTransfers


def _getAcqRefExpDimRef(refExperiment):
    """
    # CCPNInternal  - API Level routine -
    RefExpDimRef that corresponds to acquisition dimension
    """

    # get acquisition measurement
    expGraph = refExperiment.nmrExpPrototype.findFirstExpGraph()
    # even if there are several the acquisition dimension should be common.
    ll = [(expStep.stepNumber, expStep) for expStep in expGraph.expSteps]
    expSteps = [x[1] for x in sorted(ll)]
    if refExperiment.isReversed:
        acqMeasurement = expSteps[0].expMeasurement
    else:
        acqMeasurement = expSteps[-1].expMeasurement

    # get RefExpDimRef that fits measurement
    ll = []
    for refExpDim in refExperiment.sortedRefExpDims():
        for refExpDimRef in refExpDim.sortedRefExpDimRefs():
            if refExpDimRef.expMeasurement is acqMeasurement:
                ll.append(refExpDimRef)

    if len(ll) == 1:
        return ll[0]
    else:
        raise RuntimeError("%s has no unambiguous RefExpDimRef for acqMeasurement (%s)"
                           % (refExperiment, acqMeasurement))


def _getAcqExpDim(experiment, ignorePreset=False):
    """
    # CCPNInternal  - API Level routine -
    ExpDim that corresponds to acquisition dimension. NB uses heuristics
    """

    ll = experiment.findAllExpDims(isAcquisition=True)
    if len(ll) == 1 and not ignorePreset:
        # acquisition dimension set - return it
        result = ll.pop()

    else:
        # no reliable acquisition dimension set
        result = None

        dataSources = experiment.sortedDataSources()
        if dataSources:
            dataSource = dataSources[0]
            for ds in dataSources[1:]:
                # more than one data source. Pick one of the largest.
                if ds.numDim > dataSource.numDim:
                    dataSource = ds

            # Take dimension with most points
            useDim = None
            currentVal = -1
            for dd in dataSource.sortedDataDims():
                if hasattr(dd, 'numPointsOrig'):
                    val = dd.numPointsOrig
                else:
                    val = dd.numPoints
                if val > currentVal:
                    currentVal = val
                    useDim = dd

            if useDim is not None:
                result = useDim.expDim

        if result is None:
            # no joy so far - just take first ExpDim
            ll = experiment.sortedExpDims()
            if ll:
                result = ll[0]

    return result


def _getRefExpDim4ExpDim(expDim):
    """
    get the link between refExpDim and expDim through their children refExpDimRef and expDimRef.
    """
    refExpDim = None
    for expDimRef in expDim.expDimRefs:
        if expDimRef.refExpDimRef:
            refExpDim = expDimRef.refExpDimRef.refExpDim
            break
    return refExpDim


def _tempLinkRefExpDim2ExpDim(expDim, refExpDim):
    """
    Temporary link expDim and refExpDim through their sorted children refExpDimRefs and expDimRefs.
    The match refExpDimRef-expDimRef will be redone by isotope code.
    """
    if len(expDim.sortedExpDimRefs()) == len(refExpDim.sortedRefExpDimRefs()):
        for expDimRef, refExpDimRef in zip(expDim.sortedExpDimRefs(), refExpDim.sortedRefExpDimRefs()):
            expDimRef.setRefExpDimRef(refExpDimRef)


def _clearLinkToRefExp(experiment):
    for expDim in experiment.expDims:
        refExpDim = _getRefExpDim4ExpDim(expDim)
        if refExpDim:
            for expDimRef in expDim.expDimRefs:
                if expDimRef is not None:
                    if expDimRef.refExpDimRef:
                        expDimRef.setRefExpDimRef(None)


def _setApiRefExperiment(experiment, refExperiment):
    """
    # CCPNInternal  - API Level routine -
    Sets the reference experiment for an existing experiment
    and tries to map the ExpDims to RefExpDims appropriately.

    This routine is very convoluted. Should be simplified/reimplemented.
    We are only trying to make this link: expDimRef.refExpDimRef = refExpDimRef

        experiment------ expDim(s)-------expDimRef(s)
                                             *
        refExperiment---refExpDim(s)----refExpDimRef(s)

    """

    _clearLinkToRefExp(experiment)

    experiment.setRefExperiment(refExperiment)
    if refExperiment is None:
        return

    refExpDims = refExperiment.sortedRefExpDims()
    if not refExpDims:
        # Something is wrong with the reference data
        return

    expDims = experiment.sortedExpDims()
    if not expDims:
        # Something is wrong with the experiment
        return

    acqRefExpDim = _getAcqRefExpDimRef(refExperiment).refExpDim
    acqExpDim = _getAcqExpDim(experiment, ignorePreset=True)

    if ((refExpDims.index(acqRefExpDim) * 2 < len(refExpDims)) !=
            (expDims.index(acqExpDim) * 2 < len(expDims))):
        # acqRefExpDim and acqExpDim are at opposite ends of their
        # respective lists. reverse refExpDims so that acquisition
        # dimensions will more likely get mapped to each other.
        refExpDims.reverse()

    # Rasmus 12/7/12. Must be set to None, as otherwise it is never reset below.
    # We do not want the heuristic _getAcqExpDim to override everything else.
    acqExpDim = None

    for expDim in expDims:
        expData = []
        expDim.isAcquisition = False

        for expDimRef in expDim.expDimRefs:
            isotopes = frozenset(expDimRef.isotopeCodes)

            if isotopes:
                mType = expDimRef.measurementType.lower()
                expData.append((mType, isotopes))

        if not expData:
            continue

        for refExpDim in refExpDims:
            refData = []

            for refExpDimRef in refExpDim.refExpDimRefs:
                expMeasurement = refExpDimRef.expMeasurement
                isotopes = frozenset([x.isotopeCode for x in expMeasurement.atomSites])
                mType = expMeasurement.measurementType.lower()
                refData.append((mType, isotopes))

            if expData == refData:
                # expDim.refExpDim = refExpDim # this link is not anymore in the v3 API.  set refExpDimRefs and expDimRefs directly
                _tempLinkRefExpDim2ExpDim(expDim, refExpDim)
                refExpDims.remove(refExpDim)

                if refExpDim is acqRefExpDim:
                    if not acqExpDim:
                        expDim.isAcquisition = True
                        acqExpDim = expDim

                break
    for expDim in expDims:
        if not expDim.expDimRefs:
            continue

        if not _getRefExpDim4ExpDim(expDim):
            if len(refExpDims) > 0:
                refExpDim = refExpDims.pop(0)
                _tempLinkRefExpDim2ExpDim(expDim, refExpDim)

        # set reference data comparison list
        _refExpDim = _getRefExpDim4ExpDim(expDim)
        if _refExpDim:
            refExpDimRefs = list(_refExpDim.refExpDimRefs)
            refData = []
            for refExpDimRef in refExpDimRefs:
                expMeasurement = refExpDimRef.expMeasurement
                atomSites = expMeasurement.atomSites
                refData.append((frozenset(x.isotopeCode for x in atomSites),
                                expMeasurement.measurementType.lower(),
                                frozenset(x.name for x in atomSites),
                                refExpDimRef))

            # set experiment data comparison list
            inData = []
            for expDimRef in expDim.expDimRefs:
                inData.append((frozenset(expDimRef.isotopeCodes),
                               expDimRef.measurementType.lower(),
                               frozenset(((expDimRef.displayName),)),
                               expDimRef))

            # match expDimRef to refExpDimRef. comparing isotopeCodes,
            # if equal measurementTypes, if equal name/displayname
            for end in (-1, -2, -3):
                for ii in range(len(inData) - 1, -1, -1):
                    for jj in range(len(refData) - 1, -1, -1):
                        if inData[ii][:end] == refData[jj][:end]:
                            expDimRef = inData[ii][-1]
                            expDimRef.refExpDimRef = refData[jj][-1]
                            expDimRef.measurementType = refData[jj][-1].expMeasurement.measurementType
                            del inData[ii]
                            del refData[jj]
                            break


#===========================================================================================================
# Peak-related stuff
#===========================================================================================================

def _createPeak(spectrum, peakList=None, height=None, **ppmPositions) -> Optional['Peak']:
    """Create peak at position specified by the ppmPositions dict.

    Return the peak created at this ppm position or None.

    Ppm positions are passed in as a dict of (axisCode, ppmValue) key, value pairs
    with the ppmValue supplied mapping to the closest matching axis.

    Illegal or non-matching axisCodes will return None.

    Example ppmPosition dict:

    ::

        {'Hn': 7.0, 'Nh': 110}


    Example calling function:

    >>> peak = spectrum.createPeak(**limitsDict)
    >>> peak = spectrum.createPeak(peakList, **limitsDict)
    >>> peak = spectrum.createPeak(peakList=peakList, Hn=7.0, Nh=110)

    :param peakList: peakList to create new peak in, or None for the last peakList belonging to spectrum
    :param ppmPositions: dict of (axisCode, ppmValue) key,value pairs
    :return: new peak or None
    """
    with undoBlockWithoutSideBar():

        axisCodes = []
        _ppmPositions = []
        for axis, pos in ppmPositions.items():
            axisCodes.append(axis)
            _ppmPositions.append(float(pos))

        try:
            # try and match the axis codes before creating new peakList (if required)
            # indices = spectrum.getByAxisCodes('dimensionIndices', axisCodes)  # (1)
            indices = getAxisCodeMatchIndices(spectrum.axisCodes, axisCodes)  # (2)

        except Exception as es:
            getLogger().warning(f'Non-matching axis codes found {axisCodes}')
            return

        peakList = spectrum.project.getByPid(peakList) if isinstance(peakList, str) else peakList
        if not peakList:
            if spectrum.peakLists:
                peakList = spectrum.peakLists[-1]
            else:
                # log warning that no peakList exists - this SHOULD never happen
                getLogger().warning(f'Spectrum {spectrum} has no peakLists - creating new')
                peakList = spectrum.newPeakList()

        # should get all ppm's from the reference - shouldn't really be any Nones now though
        # _ppmPositions = [_ppmPositions[indices.index(ind)] if ind in indices else None for ind, ii in enumerate(indices)]  # (1) - reverse lookup
        _ppmPositions = [_ppmPositions[ii] for ii in indices]  # (2)
        if height is None:
            height = spectrum.getHeight(_ppmPositions)
        specLimits = spectrum.spectrumLimits
        aliasInds = spectrum.aliasingIndexes

        for dim, pos in enumerate(_ppmPositions):
            # check that the picked peak lies in the bounded region of the spectrum
            minSpectrumFrequency, maxSpectrumFrequency = sorted(specLimits[dim])
            visibleAlias = aliasInds[dim]
            regionBounds = (round(minSpectrumFrequency + visibleAlias[0] * (maxSpectrumFrequency - minSpectrumFrequency), 3),
                            round(minSpectrumFrequency + (visibleAlias[1] + 1) * (maxSpectrumFrequency - minSpectrumFrequency), 3))

            if not (regionBounds[0] <= pos <= regionBounds[1]):
                break

        else:
            # get the list of existing peak pointPositions in this peakList
            pointCounts = spectrum.pointCounts
            intPositions = [int(((spectrum.ppm2point(pos, dimension=indx + 1)) - 1) % np) + 1
                            for indx, (pos, np) in enumerate(zip(_ppmPositions, pointCounts))]

            # get the existing peak point-positions for this list
            existingPositions = [[int(pp) for pp in pk.pointPositions] for pk in peakList.peaks if None not in pk.pointPositions]

            if intPositions not in existingPositions:
                # add the new peak only if one doesn't exist at these pointPositions
                pk = peakList.newPeak(ppmPositions=_ppmPositions, height=height)
                return pk


# def _pickPeaks(spectrum, peakList=None, positiveThreshold=None, negativeThreshold=None, **ppmRegions) -> Tuple['Peak', ...]:
#     """Pick peaks in the region defined by the ppmRegions dict.
#
#     Ppm regions are passed in as a dict containing the axis codes and the required limits.
#     Each limit is defined as a key, value pair: (str, tuple), with the tuple supplied as (min, max) axis limits in ppm.
#     Axis codes supplied are mapped to the closest matching axis.
#
#     Illegal or non-matching axisCodes will return None.
#
#     Example ppmRegions dict:
#
#     ::
#
#         {'Hn': (7.0, 9.0),
#          'Nh': (110, 130)
#          }
#
#     Example calling function:
#
#     >>> peaks = spectrum.pickPeaks(**regionsDict)
#     >>> peaks = spectrum.pickPeaks(peakList, **regionsDict)
#     >>> peaks = spectrum.pickPeaks(peakList=peakList, Hn=(7.0, 9.0), Nh=(110, 130))
#
#     :param peakList: peakList to create new peak in, or None for the last peakList belonging to spectrum
#     :param positiveThreshold: float or None specifying the positive threshold above which to find peaks.
#                               if None, positive peak picking is disabled.
#     :param negativeThreshold: float or None specifying the negative threshold below which to find peaks.
#                               if None, negative peak picking is disabled.
#     :param ppmRegions: dict of (axisCode, tupleValue) key, value pairs
#     :return: tuple of new peaks
#     """
#     # local import as cycles otherwise
#     from ccpn.core.Spectrum import Spectrum
#
#     application = getApplication()
#     preferences = application.preferences
#     logger = getLogger()
#
#     if spectrum is None or not isinstance(spectrum, Spectrum):
#         raise ValueError('_pickPeaks: required Spectrum instance, got:%r' % spectrum)
#
#     if peakList is None:
#         peakList = spectrum.peakLists[-1]
#
#
#     # get the dimensions by mapping the keys of the ppmRegions dict
#     dimensions = spectrum.getByAxisCodes('dimensions', [a for a in ppmRegions.keys()])
#     # now get all other parameters in dimensions order
#     axisCodes = spectrum.getByDimensions('axisCodes', dimensions)
#     ppmValues = [sorted(float(pos) for pos in region) for region in ppmRegions.values()]
#     ppmValues = spectrum.orderByDimensions(ppmValues, dimensions) # sorted in order of dimensions
#
#     axisDict = dict((axisCode, region) for axisCode, region in zip(axisCodes, ppmValues))
#     sliceTuples = spectrum._axisDictToSliceTuples(axisDict)
#
#     return _pickPeaksByRegion(spectrum, sliceTuples= sliceTuples, peakList=peakList,
#                               positiveThreshold=positiveThreshold, negativeThreshold=negativeThreshold)


def _pickPeaksByRegion(spectrum, sliceTuples, peakList, positiveThreshold, negativeThreshold) -> list:
    """Helper function to pick peaks of spectrum in region defined by sliceTuples

    :param spectrum: a Spectrum instance
    :param sliceTuples: a list of (startPoint,stopPoint) tuples (1-based, inclusive) per dimension
    :param peakList: peakList to hold newly created peak.
    :param positiveThreshold: float or None specifying the positive threshold above which to find peaks.
                              if None, positive peak picking is disabled.
    :param negativeThreshold: float or None specifying the negative threshold below which to find peaks.
                              if None, negative peak picking is disabled.

    :return: list of new peaks
    """

    # local import as cycles otherwise
    from ccpn.core.Spectrum import Spectrum
    from ccpn.core.PeakList import PeakList

    application = getApplication()
    preferences = application.preferences
    logger = getLogger()

    spectrum = application.project.getByPid(spectrum) if isinstance(spectrum, str) else spectrum
    if spectrum is None or not isinstance(spectrum, Spectrum):
        raise ValueError(f'_pickPeaksByRegion: required Spectrum instance, got:{repr(spectrum)}')

    peakList = application.project.getByPid(peakList) if isinstance(peakList, str) else peakList
    if peakList is None or not isinstance(peakList, PeakList):
        raise ValueError(f'_pickPeaksByRegion: required peakList instance, got:{repr(peakList)}')

    # get the peakPicker
    if (peakPicker := spectrum.peakPicker) is None:
        txt = f'_pickPeakByRegion: No valid peakPicker for {spectrum}'
        logger.warning(txt)
        raise RuntimeError(txt)

    # check the sliceTuples; make a copy as list of lists first
    _sliceTuples = [list(sl) for sl in sliceTuples]
    cropped = False
    for dimIdx, _slice, points in zip(spectrum.dimensionIndices, _sliceTuples, spectrum.aliasingPointLimits):
        # check if the region is not completely outside the spectrum;
        # if so, issue a warning
        if (_slice[0] < points[0] and _slice[1] < points[0]) or \
                (_slice[0] > points[1] and _slice[1] > points[1]):
            # region is fully outside the spectral range
            logger.debug('_pickPeaksByRegion: %s: sliceTuples[%d]=%r out of range %r' %
                         (spectrum, dimIdx, tuple(_slice), points))
            logger.warning(f'could not pick peaks for {spectrum} in region {sliceTuples}; ' \
                           f'dimension {dimIdx + 1},"{spectrum.axisCodes[dimIdx]}" = {tuple(_slice)} out of range {points}')
            return []

        if _slice[0] < points[0]:
            _slice[0] = points[0]
            _sliceTuples[dimIdx] = _slice
            cropped = True
        if _slice[1] > points[1]:
            _slice[1] = points[1]
            _sliceTuples[dimIdx] = _slice
            cropped = True

    # revert to a list of tuples
    _sliceTuples = [tuple(sl) for sl in _sliceTuples]
    if cropped:
        logger.warning('_pickPeaksByRegion: %s: cropped sliceTuples from %r to %r' %
                       (spectrum, sliceTuples, _sliceTuples))

    # set any additional parameters from preferences
    minDropFactor = preferences.general.peakDropFactor
    fitMethod = preferences.general.peakFittingMethod
    peakPicker.setParameters(dropFactor=minDropFactor,
                             fitMethod=fitMethod,
                             setLineWidths=True,
                             singularMode=False
                             )
    peaks = []
    with undoBlockWithoutSideBar():
        try:
            peaks = peakPicker.pickPeaks(sliceTuples=_sliceTuples,
                                         peakList=peakList,
                                         positiveThreshold=positiveThreshold,
                                         negativeThreshold=negativeThreshold
                                         )
        except Exception as err:
            # need to trap error that Nd spectra may not be defined in all dimensions of axisDict
            logger.debug('_pickPeaks %s, trapped error: %s' % (spectrum, str(err)))
            logger.warning(f'could not pick peaks for {spectrum} in region {sliceTuples}')
            # if application._isInDebugMode:
            #     raise  err

    return peaks


def fetchPeakPicker(spectrum):
    """Get a peakPicker; either by restore from spectrum or the default relevant for spectrum
    :return a PeakPicker instance or None on errors
    """
    from ccpn.util.traits.CcpNmrJson import CcpNmrJson
    from ccpn.core.Spectrum import Spectrum
    from ccpn.core.lib.PeakPickers.PeakPicker1D import PeakPicker1D
    from ccpn.core.lib.PeakPickers.PeakPickerNd import PeakPickerNd
    from ccpn.core.lib.PeakPickers.PeakPickerABC import getPeakPickerTypes, PEAKPICKERPARAMETERS

    if spectrum is None:
        raise ValueError('fetchPeakPicker: spectrum is None')
    if not isinstance(spectrum, Spectrum):
        raise ValueError('fetchPeakPicker: spectrum is not of Spectrum class')

    project = spectrum.project
    application = project.application
    preferences = application.preferences

    peakPickers = getPeakPickerTypes()
    default1DPickerType = preferences.general.peakPicker1d
    if not default1DPickerType or default1DPickerType not in peakPickers:
        # default to the hard-coded peak-picker
        default1DPickerType = PeakPicker1D.peakPickerType

    defaultNDPickerType = preferences.general.peakPickerNd
    if not defaultNDPickerType or defaultNDPickerType not in peakPickers:
        # default to the hard-coded peak-picker
        defaultNDPickerType = PeakPickerNd.peakPickerType

    _picker = None
    try:
        # read peakPicker from CCPNinternal
        jsonString = spectrum._getInternalParameter(PEAKPICKERPARAMETERS)
        _picker = CcpNmrJson.newObjectFromJson(jsonString=jsonString, spectrum=spectrum)

    except Exception as es:
        # No internal definition found
        _pickerType = default1DPickerType if spectrum.dimensionCount == 1 else defaultNDPickerType
        getLogger().debug(f'peakPicker not restored from {spectrum}; selected {_pickerType} instead')
        if (cls := peakPickers.get(_pickerType)) is not None:
            _picker = cls(spectrum=spectrum)
        else:
            getLogger().debug(f'Failed to initiate {_pickerType} peakPicker')

    if _picker is None:
        getLogger().debug(f'peakPicker for {spectrum} not defined')

    return _picker


#===========================================================================================================
# Spectrum axis permutations
#===========================================================================================================

def _searchAxisCodePermutations(spectrum, checkCodes: Tuple[str, ...]) -> Optional[Tuple[int]]:
    """Generate the permutations of the current axisCodes
    """
    if not checkCodes:
        raise ValueError('checkCodes is not defined')
    if not isinstance(checkCodes, (tuple, list)):
        raise TypeError('checkCodes is not a list/tuple')
    if not all(isinstance(ss, str) for ss in checkCodes):
        raise TypeError('checkCodes elements must be strings')

    from itertools import permutations

    # add permutations for the axes
    axisPerms = tuple(permutations(spectrum.axisCodes))
    axisOrder = tuple(permutations(spectrum.dimensionIndices))

    for ii, perm in enumerate(axisPerms):
        n = min(len(checkCodes), len(perm))
        if n and all(pCode[0] == cCode[0] for pCode, cCode in zip(perm[:n], checkCodes[:n])):
            return axisOrder[ii]


def _setDefaultAxisOrdering(spectrum):
    """Establish and set a preferred axis ordering, based on some default rules;
    e.g. HCN for triple-resonance experiment
    called once from _newSpectrum to set the preferredAxisOrdering
    """
    pOrder = None
    # Define the preferred orderings
    if spectrum.dimensionCount == 2:
        dCodes = ['H N'.split(), 'H C'.split(), ('H',)]
    elif spectrum.dimensionCount == 3:
        dCodes = ['H C N'.split(), 'H H'.split(), 'C C'.split(), 'N N'.split()]
    elif spectrum.dimensionCount == 4:
        dCodes = ['H C H N'.split(), 'H C H C'.split()]
    else:
        dCodes = []

    # See if we can map one of the preferred orderings
    for dCode in dCodes:
        pOrder = _searchAxisCodePermutations(spectrum, dCode)
        if pOrder and pOrder[0] == X_DIM_INDEX:
            spectrum._preferredAxisOrdering = pOrder
            break

    if not pOrder:
        # didn't find anything; revert to default [0...dimensionCount-1]
        pOrder = spectrum.dimensionIndices

    return


#===========================================================================================================
# Spectrum/Peak parameter management
#===========================================================================================================

def _setParameterValues(obj, parameterName: str, values: Sequence, dimensions: Sequence, dimensionCount: int) -> list:
    """A helper function to reduce code overhead in setting parameters of Spectrum and Peak
    :return The list with values

    CCPNINTERNAL: used in setByAxisCode and setByDimension methods of
                  Spectrum and Peak classes
    """
    from ccpn.util.Common import isIterable # this causes circular imports. KEEP LOCAL

    if not hasattr(obj, parameterName):
        raise ValueError('object "%s" does not have parameter "%s"' %
                         (obj.__class__.__name__, parameterName))

    if not isIterable(values):
        raise ValueError('setting "%s.%s" requires "values" tuple or list; got %r' %
                         (obj.__class__.__name__, parameterName, values))

    if not isIterable(dimensions):
        raise ValueError('setting "%s.%s" requires "dimensionIndices" tuple or list; got %r' %
                         (obj.__class__.__name__, parameterName, dimensions))

    if len(values) != len(dimensions):
        raise ValueError('setting "%s.%s": unequal length of "values" and "dimensionIndices"; got %r and %r' %
                         (obj.__class__.__name__, parameterName, values, dimensions))

    newValues = list(getattr(obj, parameterName))
    for dim, val in zip(dimensions, values):
        if dim < 1 or dim > dimensionCount:
            # report error in 1-based, as the error is caught by the calling routines
            raise ValueError('%s: invalid dimension "%s"; should be in range (1,%d)' %
                             (obj, dim, dimensionCount))
        newValues[dim - 1] = val

    try:
        setattr(obj, parameterName, newValues)
    except AttributeError:
        raise ValueError('setting "%s.%s": unable to set to %r' %
                         (obj.__class__.__name__, parameterName, newValues))

    # we get the values from the obj, just in case some haven been modified
    return getattr(obj, parameterName)


def _getParameterValues(obj, parameterName: str, dimensions: Sequence, dimensionCount: int) -> list:
    """A helper function to reduce code overhead in setting parameters of Spectrum and Peak
    :return The list with values

    CCPNINTERNAL: used in getByAxisCode and getByDimension methods of
                  Spectrum and Peak classes
    """
    from ccpn.util.Common import isIterable # this causes circular imports. KEEP LOCAL

    if not hasattr(obj, parameterName):
        raise ValueError('object "%s" does not have parameter "%s"' %
                         (obj.__class__.__name__, parameterName))

    if not isIterable(dimensions):
        raise ValueError('getting "%s.%s" requires "dimensions" tuple or list; got %r' %
                         (obj.__class__.__name__, parameterName, dimensions))

    try:
        values = getattr(obj, parameterName)
    except AttributeError as es:
        raise ValueError('%s: unable to get parameter "%s"' % (obj, parameterName)) from es

    newValues = []
    if all(isinstance(i, tuple) for i in values):
        # this could be the case as in peak.assignedNmrAtoms
        for ll in values:
            # need to check against len(ll) in case of 2D overlaying nD
            _newValuesForDim = [ll[dim - 1] for dim in dimensions if dim <= len(ll)]
            newValues.append(tuple(_newValuesForDim))
        return newValues

    newValues = []
    for dim in dimensions:
        if dim < 1 or dim > dimensionCount:
            # report error in 1-based, as the error is caught by the calling routines
            raise ValueError('%s: invalid dimension "%s"; should be in range (1,%d)' %
                             (obj, dim, dimensionCount))
        newValues.append(values[dim - 1])

    return newValues


def _orderByDimensions(iterable, dimensions, dimensionCount) -> list:
    """Return a list of values of iterable in order defined by dimensions (default order if None).

    :param iterable: an iterable (tuple, list)
    :param dimensions: a tuple or list of dimensions (1..dimensionCount)
    :return: a list with values defined by iterable in dimensions order
    """
    from ccpn.util.Common import isIterable # this causes circular imports. KEEP LOCAL

    if not isIterable(iterable):
        raise ValueError('not an iterable; got %r' % (iterable))
    values = list(iterable)

    if not isIterable(dimensions):
        raise ValueError('"dimensions" is not iterable; got %r' % (dimensions))

    result = []
    for dim in dimensions:
        if dim < 1 or dim > dimensionCount:
            raise ValueError('invalid dimension "%s"; should be in range (1,%d)' %
                             (dim, dimensionCount))
        if dim - 1 >= len(values):
            raise ValueError('invalid dimension "%s"; to large for iterable (%r)' %
                             (dim, values))

        result.append(values[dim - 1])
    return result


#===========================================================================================================
# GWV testing only
#===========================================================================================================

from ccpn.util.traits.CcpNmrTraits import List, Int, Float, TraitError


class SpectrumDimensionTrait(List):
    """
    A trait to implement a Spectrum dimensional attribute; e.g. like spectrumFrequencies
    """
    # GWV test
    # _spectrometerFrequencies = SpectrumDimensionTrait(trait=Float(min=0.0)).tag(
    #                            attributeName='spectrometerFrequency',
    #                            doCopy = True
    # )

    isDimensional = True

    def validate(self, obj, value):
        """Validate the value
        """
        if len(value) != obj.dimensionCount:
            raise TraitError('Setting "%s", invalid value "%s"' % (self.name, value))
        value = self.validate_elements(obj, value)
        return value

    def _getValue(self, obj):
        """Get the value of trait, obtained from the obj (i.e.spectrum) dimensions
        """
        if (dimensionAttributeName := self.get_metadata('attributeName', None)) is None:
            raise RuntimeError('Undefined dimensional attributeName for trait %r' % self.name)
        value = [getattr(specDim, dimensionAttributeName) for specDim in obj.spectrumReferences]
        return value

    def get(self, obj, cls=None):
        try:
            value = self._getValue(obj)

        except (AttributeError, ValueError, RuntimeError):
            # Check for a dynamic initializer.
            dynamic_default = self._dynamic_default_callable(obj)
            if dynamic_default is None:
                raise TraitError("No default value found for %s trait of %r"
                                 % (self.name, obj))
            value = self._validate(obj, dynamic_default())
            obj._trait_values[self.name] = value
            return value

        except Exception:
            # This should never be reached.
            raise TraitError('Unexpected error in DimensionTrait')

        else:
            self._obj = obj  # last obj used for get
            return value

    def _setValue(self, obj, value):
        """Set the value of trait, stored in the obj (i.e.spectrum) dimensions
        """
        if (dimensionAttributeName := self.get_metadata('attributeName', None)) is None:
            raise RuntimeError('Undefined dimensional attributeName for trait %r' % self.name)

        for axis, val in enumerate(value):
            setattr(obj.spectrumReferences[axis], dimensionAttributeName, val)

    def set(self, obj, value):

        new_value = self._validate(obj, value)
        try:
            old_value = self._getValue(obj)
        except (AttributeError, ValueError, RuntimeError):
            old_value = self.default_value

        # obj._trait_values[self.name] = new_value
        self._setValue(obj, new_value)

        try:
            silent = bool(old_value == new_value)
        except:
            # if there is an error in comparing, default to notify
            silent = False
        if silent is not True:
            # we explicitly compare silent to True just in case the equality
            # comparison above returns something other than True/False
            obj._notify_trait(self.name, old_value, new_value)
