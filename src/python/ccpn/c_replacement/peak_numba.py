"""Numba-optimized peak analysis functions.

This module provides pure Python implementations of peak finding and fitting
algorithms, optimized with Numba JIT compilation for performance.
"""

import numpy as np
from numba import njit
from typing import List, Tuple
from .peak_models import fit_parabolic_to_ndim, get_value_at_point


def _fit_parabolic_peaks_impl(
    data: np.ndarray,
    region_array: np.ndarray,
    peak_array: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Internal implementation of parabolic peak fitting.

    This implements the C function fit_parabolic() from npy_peak.c lines 664-765.

    Note: Not JIT-compiled itself, but calls JIT-compiled specialized functions
    based on data dimensionality.

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
            try:
                peak_fit, fitted_height, lw = fit_parabolic_to_ndim(
                    data, grid_posn, i
                )
                positions[j, i] = peak_fit
                linewidths[j, i] = lw
                current_height = fitted_height  # Update height with each dimension
            except (ValueError, ZeroDivisionError):
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


# Peak finding implementation
def find_peaks(
    data_array: np.ndarray,
    have_low: bool,
    have_high: bool,
    low: float,
    high: float,
    buffer: list,
    nonadjacent: bool,
    drop_factor: float,
    min_linewidth: list,
    excluded_regions: list,
    diagonal_exclusion_dims: list,
    diagonal_exclusion_transform: list
) -> List[Tuple[Tuple[int, ...], float]]:
    """Find peaks in N-dimensional data.

    This implements the C function findPeaks() from npy_peak.c lines 891-1021.

    Args:
        data_array: N-dimensional float32 array
        have_low: Search for minima
        have_high: Search for maxima
        low: Threshold for minima
        high: Threshold for maxima
        buffer: Exclusion buffer per dimension (list of ints)
        nonadjacent: Check all 3^N neighbors (vs 2N axis-aligned)
        drop_factor: Minimum drop factor from peak (0.0-1.0)
        min_linewidth: Minimum linewidth per dimension (list of floats)
        excluded_regions: List of exclusion boxes (not implemented yet)
        diagonal_exclusion_dims: Diagonal exclusion dimensions (not implemented yet)
        diagonal_exclusion_transform: Diagonal exclusion transforms (not implemented yet)

    Returns:
        List of ((x, y, ...), height) tuples for each peak found
    """
    from .peak_finding import (
        check_adjacent_extremum,
        check_nonadjacent_extremum,
        check_drop_criterion,
        check_linewidth_criterion,
    )
    from .peak_models import get_value_at_point

    # Validate inputs
    if not isinstance(data_array, np.ndarray):
        data_array = np.asarray(data_array, dtype=np.float32)
    elif data_array.dtype != np.float32:
        data_array = data_array.astype(np.float32)

    if not have_low and not have_high:
        return []  # Nothing to search for

    ndim = data_array.ndim
    points = np.array(data_array.shape, dtype=np.int64)

    # Convert lists to arrays
    buffer_array = np.array(buffer, dtype=np.int64)
    min_linewidth_array = np.array(min_linewidth, dtype=np.float32)

    peak_list = []

    # Iterate over all points in the array
    total_points = np.prod(data_array.shape)

    for flat_index in range(total_points):
        # Convert flat index to N-dimensional coordinates
        point = np.zeros(ndim, dtype=np.int64)
        temp_index = flat_index

        for dim in range(ndim):
            point[dim] = temp_index % data_array.shape[dim]
            temp_index //= data_array.shape[dim]

        # TODO: Check exclusion regions and diagonal exclusions
        # For now, skip these checks (will implement in follow-up)

        # Get value at this point
        v = get_value_at_point(data_array, point)

        # Check if value exceeds thresholds
        find_maximum = None
        if have_high and (v >= high):
            find_maximum = True
        elif have_low and (v <= low):
            find_maximum = False
        else:
            continue  # Value doesn't exceed any threshold

        # Check if point is a local extremum
        if nonadjacent:
            ok_extreme = check_nonadjacent_extremum(
                data_array, point, points, v, find_maximum
            )
        else:
            ok_extreme = check_adjacent_extremum(
                data_array, point, points, v, find_maximum
            )

        if not ok_extreme:
            continue

        # Check drop criterion
        ok_drop = check_drop_criterion(
            data_array, point, points, v, drop_factor, find_maximum
        )

        if not ok_drop:
            continue

        # Check linewidth criterion
        ok_linewidth = check_linewidth_criterion(
            data_array, point, points, v, min_linewidth_array, find_maximum
        )

        if not ok_linewidth:
            continue

        # TODO: Check buffer criterion (not too close to existing peaks)
        # For now, skip this check

        # Add peak to list
        peak_position = tuple(int(point[i]) for i in range(ndim))
        peak_height = float(v)
        peak_list.append((peak_position, peak_height))

    return peak_list


def fit_peaks(*args, **kwargs):
    """Gaussian/Lorentzian peak fitting - to be implemented in Phase 3."""
    raise NotImplementedError("fitPeaks will be implemented in Phase 3")
