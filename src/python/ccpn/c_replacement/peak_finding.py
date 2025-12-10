"""Peak finding implementation for NMR data.

This module implements the find_peaks() functionality from npy_peak.c,
with Numba JIT compilation for performance.
"""

import numpy as np
from numba import njit
from typing import List, Tuple
from .peak_models import (
    get_value_at_point,
    calculate_linewidth_at_point
)


# Adjacent extremum checking (2N neighbors - only axis-aligned)

@njit(cache=True)
def check_adjacent_extremum_2d(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    v: float,
    find_maximum: bool
) -> bool:
    """Check if point is extremum vs 2N axis-aligned neighbors (2D).

    Implements check_adjacent_points() from npy_peak.c lines 251-288.
    """
    # Check dimension 0
    if point[0] > 0:
        v2 = data[point[0] - 1, point[1]]
        if find_maximum:
            if v2 > v:
                return False
        else:
            if v2 < v:
                return False

    if point[0] < points[0] - 1:
        v2 = data[point[0] + 1, point[1]]
        if find_maximum:
            if v2 > v:
                return False
        else:
            if v2 < v:
                return False

    # Check dimension 1
    if point[1] > 0:
        v2 = data[point[0], point[1] - 1]
        if find_maximum:
            if v2 > v:
                return False
        else:
            if v2 < v:
                return False

    if point[1] < points[1] - 1:
        v2 = data[point[0], point[1] + 1]
        if find_maximum:
            if v2 > v:
                return False
        else:
            if v2 < v:
                return False

    return True


@njit(cache=True)
def check_adjacent_extremum_3d(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    v: float,
    find_maximum: bool
) -> bool:
    """Check if point is extremum vs 2N axis-aligned neighbors (3D)."""
    # Check dimension 0
    if point[0] > 0:
        v2 = data[point[0] - 1, point[1], point[2]]
        if find_maximum:
            if v2 > v:
                return False
        else:
            if v2 < v:
                return False

    if point[0] < points[0] - 1:
        v2 = data[point[0] + 1, point[1], point[2]]
        if find_maximum:
            if v2 > v:
                return False
        else:
            if v2 < v:
                return False

    # Check dimension 1
    if point[1] > 0:
        v2 = data[point[0], point[1] - 1, point[2]]
        if find_maximum:
            if v2 > v:
                return False
        else:
            if v2 < v:
                return False

    if point[1] < points[1] - 1:
        v2 = data[point[0], point[1] + 1, point[2]]
        if find_maximum:
            if v2 > v:
                return False
        else:
            if v2 < v:
                return False

    # Check dimension 2
    if point[2] > 0:
        v2 = data[point[0], point[1], point[2] - 1]
        if find_maximum:
            if v2 > v:
                return False
        else:
            if v2 < v:
                return False

    if point[2] < points[2] - 1:
        v2 = data[point[0], point[1], point[2] + 1]
        if find_maximum:
            if v2 > v:
                return False
        else:
            if v2 < v:
                return False

    return True


def check_adjacent_extremum(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    v: float,
    find_maximum: bool
) -> bool:
    """Dispatcher for adjacent extremum checking."""
    ndim = data.ndim
    if ndim == 2:
        return check_adjacent_extremum_2d(data, point, points, v, find_maximum)
    elif ndim == 3:
        return check_adjacent_extremum_3d(data, point, points, v, find_maximum)
    else:
        raise ValueError(f"Adjacent mode only supports 2D and 3D, got {ndim}D")


# Nonadjacent extremum checking (3^N neighbors - all cube points)

@njit(cache=True)
def check_nonadjacent_extremum_2d(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    v: float,
    find_maximum: bool
) -> bool:
    """Check if point is extremum vs all 3^N neighbors (2D: 9 points).

    Implements check_nonadjacent_points() from npy_peak.c lines 201-248.
    """
    # Can't test points on border
    if point[0] == 0 or point[0] == points[0] - 1:
        return False
    if point[1] == 0 or point[1] == points[1] - 1:
        return False

    # Check all 9 positions (3x3 grid)
    for i in range(-1, 2):
        for j in range(-1, 2):
            if i == 0 and j == 0:
                continue  # Skip center point

            v2 = data[point[0] + i, point[1] + j]

            if find_maximum:
                if v2 > v:
                    return False
            else:
                if v2 < v:
                    return False

    return True


@njit(cache=True)
def check_nonadjacent_extremum_3d(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    v: float,
    find_maximum: bool
) -> bool:
    """Check if point is extremum vs all 3^N neighbors (3D: 27 points)."""
    # Can't test points on border
    if point[0] == 0 or point[0] == points[0] - 1:
        return False
    if point[1] == 0 or point[1] == points[1] - 1:
        return False
    if point[2] == 0 or point[2] == points[2] - 1:
        return False

    # Check all 27 positions (3x3x3 cube)
    for i in range(-1, 2):
        for j in range(-1, 2):
            for k in range(-1, 2):
                if i == 0 and j == 0 and k == 0:
                    continue  # Skip center point

                v2 = data[point[0] + i, point[1] + j, point[2] + k]

                if find_maximum:
                    if v2 > v:
                        return False
                else:
                    if v2 < v:
                        return False

    return True


def check_nonadjacent_extremum(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    v: float,
    find_maximum: bool
) -> bool:
    """Dispatcher for nonadjacent extremum checking."""
    ndim = data.ndim
    if ndim == 2:
        return check_nonadjacent_extremum_2d(data, point, points, v, find_maximum)
    elif ndim == 3:
        return check_nonadjacent_extremum_3d(data, point, points, v, find_maximum)
    else:
        raise ValueError(f"Nonadjacent mode only supports 2D and 3D, got {ndim}D")


# Drop criterion checking

@njit(cache=True)
def drops_in_direction_2d(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    dim: int,
    direction: int,
    v_peak: float,
    drop_value: float,
    find_maximum: bool
) -> bool:
    """Check if intensity drops enough in one direction (2D).

    Implements drops_in_direction() from npy_peak.c lines 290-328.
    """
    if direction == 1:
        i_start = point[dim] + 1
        i_end = points[dim]
        i_step = 1
    else:
        i_start = point[dim] - 1
        i_end = -1
        i_step = -1

    v_prev = v_peak

    for i in range(i_start, i_end, i_step):
        if dim == 0:
            v_this = data[i, point[1]]
        else:  # dim == 1
            v_this = data[point[0], i]

        if find_maximum:
            # For maxima, values should decrease
            if v_this > v_prev:
                return False
            if (v_peak - v_this) >= drop_value:
                return True
        else:
            # For minima, values should increase
            if v_this < v_prev:
                return False
            if (v_this - v_peak) >= drop_value:
                return True

        v_prev = v_this

    return True


@njit(cache=True)
def drops_in_direction_3d(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    dim: int,
    direction: int,
    v_peak: float,
    drop_value: float,
    find_maximum: bool
) -> bool:
    """Check if intensity drops enough in one direction (3D)."""
    if direction == 1:
        i_start = point[dim] + 1
        i_end = points[dim]
        i_step = 1
    else:
        i_start = point[dim] - 1
        i_end = -1
        i_step = -1

    v_prev = v_peak

    for i in range(i_start, i_end, i_step):
        if dim == 0:
            v_this = data[i, point[1], point[2]]
        elif dim == 1:
            v_this = data[point[0], i, point[2]]
        else:  # dim == 2
            v_this = data[point[0], point[1], i]

        if find_maximum:
            if v_this > v_prev:
                return False
            if (v_peak - v_this) >= drop_value:
                return True
        else:
            if v_this < v_prev:
                return False
            if (v_this - v_peak) >= drop_value:
                return True

        v_prev = v_this

    return True


def check_drop_criterion(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    v_peak: float,
    drop_factor: float,
    find_maximum: bool
) -> bool:
    """Check drop criterion in all dimensions and directions.

    Implements check_drop() from npy_peak.c lines 330-344.
    """
    if drop_factor <= 0:
        return True

    drop_value = drop_factor * abs(v_peak)
    ndim = data.ndim

    # Must drop enough in all dimensions, both directions
    for dim in range(ndim):
        # Forward direction
        if ndim == 2:
            if not drops_in_direction_2d(
                data, point, points, dim, 1, v_peak, drop_value, find_maximum
            ):
                return False
        elif ndim == 3:
            if not drops_in_direction_3d(
                data, point, points, dim, 1, v_peak, drop_value, find_maximum
            ):
                return False

        # Backward direction
        if ndim == 2:
            if not drops_in_direction_2d(
                data, point, points, dim, -1, v_peak, drop_value, find_maximum
            ):
                return False
        elif ndim == 3:
            if not drops_in_direction_3d(
                data, point, points, dim, -1, v_peak, drop_value, find_maximum
            ):
                return False

    return True


# Linewidth criterion checking

def check_linewidth_criterion(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    v_peak: float,
    min_linewidth: np.ndarray,
    find_maximum: bool
) -> bool:
    """Check minimum linewidth criterion in all dimensions.

    Implements check_linewidth() and check_dim_linewidth() from
    npy_peak.c lines 437-456.
    """
    ndim = data.ndim

    for dim in range(ndim):
        if min_linewidth[dim] > 0:
            lw = calculate_linewidth_at_point(
                data, point, points, dim, v_peak, find_maximum
            )
            if lw < min_linewidth[dim]:
                return False

    return True
