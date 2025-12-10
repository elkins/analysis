"""Numba-optimized peak analysis functions.

This module provides pure Python implementations of peak finding and fitting
algorithms, optimized with Numba JIT compilation for performance.
"""

import numpy as np
from numba import njit
from typing import List, Tuple
from .peak_models import fit_parabolic_to_ndim, get_value_at_point


@njit(cache=True)
def _fit_parabolic_peaks_impl(
    data: np.ndarray,
    region_array: np.ndarray,
    peak_array: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Internal implementation of parabolic peak fitting.

    This implements the C function fit_parabolic() from npy_peak.c lines 664-765.

    Args:
        data: N-dimensional float32 array
        region_array: int32 array (2 x ndim) - [[first_x, ...], [last_x, ...]]
        peak_array: float32 array (npeaks x ndim) - initial peak positions

    Returns:
        Tuple of (heights, positions, linewidths):
            heights: array of shape (npeaks,)
            positions: array of shape (npeaks, ndim)
            linewidths: array of shape (npeaks, ndim)
    """
    ndim = data.ndim
    npeaks = peak_array.shape[0]

    # Output arrays
    heights = np.zeros(npeaks, dtype=np.float32)
    positions = np.zeros((npeaks, ndim), dtype=np.float32)
    linewidths = np.zeros((npeaks, ndim), dtype=np.float32)

    # Process each peak
    for j in range(npeaks):
        # Find nearest grid point to peak position
        grid_posn = np.zeros(ndim, dtype=np.int64)

        for i in range(ndim):
            peak_posn = peak_array[j, i]
            posn = int(np.round(peak_posn))

            # Clip to array bounds
            npts = data.shape[i]
            posn = max(0, min(npts - 1, posn))
            grid_posn[i] = posn

        # Fit parabola along each dimension
        # Use the first dimension's height as starting point
        current_height = get_value_at_point(data, grid_posn)

        for i in range(ndim):
            fit_success = True
            try:
                peak_fit, fitted_height, lw = fit_parabolic_to_ndim(
                    data, grid_posn, i
                )
            except ValueError:
                fit_success = False
            except ZeroDivisionError:
                fit_success = False

            if fit_success:
                positions[j, i] = peak_fit
                linewidths[j, i] = lw
                current_height = fitted_height  # Update height with each dimension
            else:
                # If parabolic fit fails, use grid position
                positions[j, i] = float(grid_posn[i])
                linewidths[j, i] = 1.0  # Default linewidth
                # Keep current height

        heights[j] = current_height

    return heights, positions, linewidths


def fit_parabolic_peaks(
    data_array: np.ndarray,
    region_array: np.ndarray,
    peak_array: np.ndarray
) -> List[Tuple[float, Tuple[float, ...], Tuple[float, ...]]]:
    """Fit parabolic peaks (fast, non-iterative).

    This is the main API function matching the C extension:
        CPeak.fitParabolicPeaks(dataArray, regionArray, peakArray)

    Args:
        data_array: N-dimensional float32 array
        region_array: int32 array (2 x ndim) [[first_x, ...], [last_x, ...]]
        peak_array: float32 array (npeaks x ndim) initial positions

    Returns:
        List of (height, position_tuple, linewidth_tuple) for each peak
    """
    # Validate inputs
    if not isinstance(data_array, np.ndarray) or data_array.dtype != np.float32:
        data_array = np.asarray(data_array, dtype=np.float32)

    if not isinstance(region_array, np.ndarray) or region_array.dtype != np.int32:
        region_array = np.asarray(region_array, dtype=np.int32)

    if not isinstance(peak_array, np.ndarray) or peak_array.dtype != np.float32:
        peak_array = np.asarray(peak_array, dtype=np.float32)

    ndim = data_array.ndim

    # Validate shapes
    if region_array.shape != (2, ndim):
        raise ValueError(f"regionArray must be (2 x {ndim}), got {region_array.shape}")

    if peak_array.ndim != 2 or peak_array.shape[1] != ndim:
        raise ValueError(f"peakArray must be (npeaks x {ndim}), got {peak_array.shape}")

    # Call Numba implementation
    heights, positions, linewidths = _fit_parabolic_peaks_impl(
        data_array, region_array, peak_array
    )

    # Convert to list of tuples (matching C API)
    results = []
    for i in range(len(heights)):
        height = float(heights[i])
        position = tuple(float(positions[i, j]) for j in range(ndim))
        linewidth = tuple(float(linewidths[i, j]) for j in range(ndim))
        results.append((height, position, linewidth))

    return results


# Placeholder functions for future phases
def find_peaks(*args, **kwargs):
    """Peak finding function - to be implemented in Phase 2."""
    raise NotImplementedError("findPeaks will be implemented in Phase 2")


def fit_peaks(*args, **kwargs):
    """Gaussian/Lorentzian peak fitting - to be implemented in Phase 3."""
    raise NotImplementedError("fitPeaks will be implemented in Phase 3")
