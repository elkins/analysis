"""Compatibility wrapper for Peak module (C → Python).

This module provides a drop-in replacement for the C extension Peak module,
with automatic fallback between C and pure Python implementations.

Usage:
    from ccpn.c_replacement.peak_compat import Peak

    # Use exactly like the C extension
    peaks = Peak.findPeaks(dataArray, haveLow, haveHigh, low, high, ...)
    results = Peak.fitParabolicPeaks(dataArray, regionArray, peakArray)

Configuration:
    You can force a specific implementation using environment variables:

    export CCPN_FORCE_PYTHON=1    # Force pure Python (disable C)
    export CCPN_FORCE_C=1          # Force C (error if not available)

    Or at runtime:

    import ccpn.c_replacement.peak_compat as peak_compat
    peak_compat.use_python_implementation()  # Switch to Python
    peak_compat.use_c_implementation()        # Switch to C
"""

import numpy as np
import os
from typing import List, Tuple, Optional

# Configuration: Check environment variables
_FORCE_PYTHON = os.environ.get('CCPN_FORCE_PYTHON', '0') == '1'
_FORCE_C = os.environ.get('CCPN_FORCE_C', '0') == '1'

# Store both implementations if available
_c_implementation = None
_python_implementation = None
_implementation = None
_using_c = False
_impl_name = None

# Try to load C extension
if not _FORCE_PYTHON:
    try:
        from ccpnc.peak import Peak as _c_implementation
    except ImportError:
        _c_implementation = None

# Try to load Python implementation
if not _FORCE_C:
    try:
        from . import peak_numba as _python_implementation
    except ImportError:
        _python_implementation = None

# Select implementation based on configuration
if _FORCE_PYTHON:
    if _python_implementation is None:
        raise ImportError("CCPN_FORCE_PYTHON=1 but Python implementation not available")
    _implementation = _python_implementation
    _using_c = False
    _impl_name = 'Pure Python (Numba JIT) [FORCED]'
elif _FORCE_C:
    if _c_implementation is None:
        raise ImportError("CCPN_FORCE_C=1 but C extension not available")
    _implementation = _c_implementation
    _using_c = True
    _impl_name = 'C extension [FORCED]'
else:
    # Auto-select: prefer C, fallback to Python
    if _c_implementation is not None:
        _implementation = _c_implementation
        _using_c = True
        _impl_name = 'C extension'
    elif _python_implementation is not None:
        _implementation = _python_implementation
        _using_c = False
        _impl_name = 'Pure Python (Numba JIT)'
    else:
        raise ImportError("Neither C extension nor Python implementation available")


def use_python_implementation():
    """Force use of pure Python implementation.

    Raises:
        RuntimeError: If Python implementation is not available
    """
    global _implementation, _using_c, _impl_name

    if _python_implementation is None:
        raise RuntimeError("Python implementation not available")

    _implementation = _python_implementation
    _using_c = False
    _impl_name = 'Pure Python (Numba JIT) [RUNTIME SWITCH]'
    print(f"Peak module: Switched to {_impl_name}")


def use_c_implementation():
    """Force use of C extension.

    Raises:
        RuntimeError: If C extension is not available
    """
    global _implementation, _using_c, _impl_name

    if _c_implementation is None:
        raise RuntimeError("C extension not available")

    _implementation = _c_implementation
    _using_c = True
    _impl_name = 'C extension [RUNTIME SWITCH]'
    print(f"Peak module: Switched to {_impl_name}")


def get_available_implementations() -> dict:
    """Get information about which implementations are available.

    Returns:
        Dictionary with availability information:
        - 'c_available': bool
        - 'python_available': bool
        - 'current': str (name of current implementation)
    """
    return {
        'c_available': _c_implementation is not None,
        'python_available': _python_implementation is not None,
        'current': _impl_name,
        'using_c': _using_c,
    }


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
        available_funcs.append('fitPeaks')

    return {
        'implementation': _impl_name,
        'module': _implementation.__name__,
        'using_c': _using_c,
        'available_functions': available_funcs,
        'phase_1_complete': True,  # Parabolic fitting
        'phase_2_complete': True,  # Peak finding
        'phase_3_complete': _using_c,  # Levenberg-Marquardt only in C extension
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

        if _using_c:
            return _implementation.findPeaks(
                dataArray, haveLow, haveHigh, low, high,
                buffer, nonadjacent, dropFactor, minLinewidth,
                excludedRegions, diagonalExclusionDims, diagonalExclusionTransform
            )
        else:
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
        if _using_c:
            return _implementation.fitParabolicPeaks(
                dataArray, regionArray, peakArray
            )
        else:
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
    'get_available_implementations',
    'use_python_implementation',
    'use_c_implementation',
]


# Print implementation info on import (can be disabled by setting environment variable)
import os
if os.environ.get('CCPN_PEAK_QUIET') != '1':
    info = get_implementation_info()
    print(f"Peak module: Using {info['implementation']}")
    print(f"  Available: {', '.join(info['available_functions'])}")
    if not info['phase_3_complete']:
        print(f"  Note: fitPeaks() requires C extension (Phase 3 pending)")
