"""Compatibility wrapper for Peak module (C → Python).

This module provides a drop-in replacement for the C extension Peak module,
with automatic fallback between C and pure Python implementations.

Usage:
    from ccpn.c_replacement.peak_compat import Peak

    # Use exactly like the C extension
    peaks = Peak.findPeaks(dataArray, haveLow, haveHigh, low, high, ...)
    results = Peak.fitParabolicPeaks(dataArray, regionArray, peakArray)
"""

import numpy as np
from typing import List, Tuple, Optional

# Try to import C extension, fall back to Python implementation
_implementation = None
_using_c = False

try:
    from ccpnc import Peak as _c_peak
    _implementation = _c_peak
    _using_c = True
    _impl_name = 'C extension'
except ImportError:
    try:
        # Use pure Python implementation
        from . import peak_numba as _implementation
        _using_c = False
        _impl_name = 'Pure Python (Numba JIT)'
    except ImportError as e:
        raise ImportError(
            "Neither C extension nor Python implementation available. "
            f"Error: {e}"
        )


def get_implementation_info() -> dict:
    """Return information about current Peak module implementation.

    Returns:
        Dictionary with implementation details:
        - 'implementation': 'C extension' or 'Pure Python (Numba JIT)'
        - 'module': Module name
        - 'using_c': Boolean indicating if C extension is being used
        - 'available_functions': List of available functions
    """
    available_funcs = []
    if hasattr(_implementation, 'findPeaks'):
        available_funcs.append('findPeaks')
    if hasattr(_implementation, 'fitParabolicPeaks'):
        available_funcs.append('fitParabolicPeaks')
    if hasattr(_implementation, 'fitPeaks'):
        try:
            # Check if it's actually implemented
            _implementation.fit_peaks()
        except NotImplementedError:
            pass  # Not available
        except TypeError:
            available_funcs.append('fitPeaks')  # Available but needs args

    return {
        'implementation': _impl_name,
        'module': _implementation.__name__,
        'using_c': _using_c,
        'available_functions': available_funcs,
        'phase_1_complete': True,  # Parabolic fitting
        'phase_2_complete': True,  # Peak finding
        'phase_3_complete': False,  # Levenberg-Marquardt (future)
    }


class Peak:
    """Peak finding and fitting for N-dimensional NMR data.

    This class provides a unified interface to peak analysis functions,
    automatically using either the C extension or pure Python implementation.

    All methods are static and match the C extension API exactly.
    """

    @staticmethod
    def findPeaks(
        dataArray: np.ndarray,
        haveLow: bool,
        haveHigh: bool,
        low: float,
        high: float,
        buffer: List[int],
        nonadjacent: bool,
        dropFactor: float,
        minLinewidth: List[float],
        excludedRegions: Optional[List[np.ndarray]] = None,
        diagonalExclusionDims: Optional[List[np.ndarray]] = None,
        diagonalExclusionTransform: Optional[List[np.ndarray]] = None
    ) -> List[Tuple[Tuple[int, ...], float]]:
        """Find peaks in N-dimensional data.

        Args:
            dataArray: N-dimensional float32 array of intensities
            haveLow: Search for minima (negative peaks)
            haveHigh: Search for maxima (positive peaks)
            low: Threshold for minima
            high: Threshold for maxima
            buffer: Exclusion buffer per dimension (list of ints)
            nonadjacent: Check all 3^N neighbors (vs 2N axis-aligned)
            dropFactor: Minimum drop factor from peak (0.0-1.0)
            minLinewidth: Minimum linewidth per dimension (list of floats)
            excludedRegions: List of exclusion boxes (optional)
            diagonalExclusionDims: Diagonal exclusion dimensions (optional)
            diagonalExclusionTransform: Diagonal exclusion transforms (optional)

        Returns:
            List of (position_tuple, height) for each peak found
            where position_tuple is (x, y, ...) integer coordinates

        Example:
            >>> data = np.random.randn(50, 50).astype(np.float32)
            >>> peaks = Peak.findPeaks(
            ...     data, False, True, 0.0, 2.0,
            ...     [3, 3], True, 0.5, [2.0, 2.0],
            ...     [], [], []
            ... )
            >>> print(f"Found {len(peaks)} peaks")
        """
        # Handle optional arguments
        if excludedRegions is None:
            excludedRegions = []
        if diagonalExclusionDims is None:
            diagonalExclusionDims = []
        if diagonalExclusionTransform is None:
            diagonalExclusionTransform = []

        return _implementation.find_peaks(
            dataArray, haveLow, haveHigh, low, high,
            buffer, nonadjacent, dropFactor, minLinewidth,
            excludedRegions, diagonalExclusionDims, diagonalExclusionTransform
        )

    @staticmethod
    def fitParabolicPeaks(
        dataArray: np.ndarray,
        regionArray: np.ndarray,
        peakArray: np.ndarray
    ) -> List[Tuple[float, Tuple[float, ...], Tuple[float, ...]]]:
        """Fit parabolic peaks (fast, non-iterative).

        Uses parabolic interpolation to refine peak positions and estimate
        linewidths. This is much faster than Levenberg-Marquardt fitting
        but less accurate.

        Args:
            dataArray: N-dimensional float32 array
            regionArray: int32 array (2 x ndim) with [[first_x, ...], [last_x, ...]]
                        defining the fitting region
            peakArray: float32 array (npeaks x ndim) with initial peak positions

        Returns:
            List of (height, position_tuple, linewidth_tuple) for each peak
            where:
            - height: float, peak intensity
            - position_tuple: (x, y, ...) refined positions (float)
            - linewidth_tuple: (lw_x, lw_y, ...) FWHM linewidths (float)

        Example:
            >>> data = generate_gaussian_peak((30, 30), (15, 15), 100.0, (2.5, 2.5))
            >>> region = np.array([[12, 12], [18, 18]], dtype=np.int32)
            >>> peaks = np.array([[15.0, 15.0]], dtype=np.float32)
            >>> results = Peak.fitParabolicPeaks(data, region, peaks)
            >>> height, position, linewidth = results[0]
            >>> print(f"Peak at {position} with height {height}")
        """
        return _implementation.fit_parabolic_peaks(
            dataArray, regionArray, peakArray
        )

    @staticmethod
    def fitPeaks(
        dataArray: np.ndarray,
        regionArray: np.ndarray,
        peakArray: np.ndarray,
        method: int
    ) -> List[Tuple[float, Tuple[float, ...], Tuple[float, ...]]]:
        """Fit Gaussian or Lorentzian peaks using Levenberg-Marquardt.

        This is the most accurate fitting method but also the slowest.
        Uses iterative nonlinear least-squares fitting.

        Args:
            dataArray: N-dimensional float32 array
            regionArray: int32 array (2 x ndim) defining fitting region
            peakArray: float32 array (npeaks x ndim) with initial positions
            method: 0 for Gaussian, 1 for Lorentzian

        Returns:
            List of (height, position_tuple, linewidth_tuple) for each peak

        Note:
            Phase 3 (Levenberg-Marquardt fitting) is not yet implemented
            in the pure Python version. This function will raise
            NotImplementedError if called without the C extension.

        Example:
            >>> data = generate_gaussian_peak((30, 30), (15, 15), 100.0, (2.5, 2.5))
            >>> region = np.array([[12, 12], [18, 18]], dtype=np.int32)
            >>> peaks = np.array([[15.0, 15.0]], dtype=np.float32)
            >>> method = 0  # Gaussian
            >>> results = Peak.fitPeaks(data, region, peaks, method)
        """
        if _using_c:
            return _implementation.fitPeaks(
                dataArray, regionArray, peakArray, method
            )
        else:
            # Pure Python implementation - Phase 3 not yet complete
            raise NotImplementedError(
                "Levenberg-Marquardt fitting (fitPeaks) is not yet implemented "
                "in the pure Python version. Use fitParabolicPeaks() for fast "
                "non-iterative fitting, or ensure the C extension is available. "
                "Phase 3 implementation is planned for future release."
            )


# Module-level convenience functions (alternative to class interface)

def find_peaks(*args, **kwargs) -> List[Tuple[Tuple[int, ...], float]]:
    """Convenience function for Peak.findPeaks(). See Peak.findPeaks() for docs."""
    return Peak.findPeaks(*args, **kwargs)


def fit_parabolic_peaks(*args, **kwargs) -> List[Tuple[float, Tuple[float, ...], Tuple[float, ...]]]:
    """Convenience function for Peak.fitParabolicPeaks(). See Peak.fitParabolicPeaks() for docs."""
    return Peak.fitParabolicPeaks(*args, **kwargs)


def fit_peaks(*args, **kwargs) -> List[Tuple[float, Tuple[float, ...], Tuple[float, ...]]]:
    """Convenience function for Peak.fitPeaks(). See Peak.fitPeaks() for docs."""
    return Peak.fitPeaks(*args, **kwargs)


# Export public API
__all__ = [
    'Peak',
    'find_peaks',
    'fit_parabolic_peaks',
    'fit_peaks',
    'get_implementation_info',
]


# Print implementation info on import (can be disabled by setting environment variable)
import os
if os.environ.get('CCPN_PEAK_QUIET') != '1':
    info = get_implementation_info()
    print(f"Peak module: Using {info['implementation']}")
    print(f"  Available: {', '.join(info['available_functions'])}")
    if not info['phase_3_complete']:
        print(f"  Note: fitPeaks() requires C extension (Phase 3 pending)")
