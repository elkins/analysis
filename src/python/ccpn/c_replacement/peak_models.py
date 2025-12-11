"""Peak models and fitting functions for NMR peak analysis.

This module provides analytical functions for parabolic interpolation
and peak models (Gaussian, Lorentzian) used in peak fitting.
"""

import numpy as np
from numba import njit
from typing import Tuple


@njit(cache=True)
def fit_parabolic_1d(v_left: float, v_middle: float, v_right: float) -> Tuple[float, float, float]:
    """Fit parabola to three points and extract peak parameters.

    Fits a parabola y = a*x^2 + b*x + c to three points at x = -1, 0, 1
    (left, middle, right) and extracts:
    - Peak position (x where dy/dx = 0)
    - Peak height (y at peak position)
    - Linewidth (FWHM)

    This implementation matches the C code in npy_peak.c:fit_position_x()
    lines 120-153.

    Args:
        v_left: Value at x = -1 (left neighbor)
        v_middle: Value at x = 0 (center point)
        v_right: Value at x = 1 (right neighbor)

    Returns:
        Tuple of (peak_offset, peak_height, linewidth):
            peak_offset: Position offset from middle point (-1 to 1)
            peak_height: Interpolated peak height
            linewidth: Full width at half maximum (FWHM)

    Raises:
        ValueError: If the data doesn't form a valid parabola (flat or linear)
    """
    # Parabola coefficients: y = a*x^2 + b*x + c
    c = v_middle
    a = 0.5 * (v_left + v_right - 2.0 * v_middle)

    # Check if we have a valid parabola (non-zero curvature)
    if abs(a) < 1e-6:
        raise ValueError("Cannot fit parabola: data is too flat or linear")

    # Linear coefficient
    b = v_right - 0.5 * (v_right + v_left)

    # Peak position: dy/dx = 2*a*x + b = 0  =>  x = -b/(2*a)
    x_peak = -b / (2.0 * a)

    # Peak height: substitute x_peak into parabola
    height = a * x_peak * x_peak + b * x_peak + c

    # Linewidth calculation (FWHM)
    # Half-max value
    half_max = 0.5 * height

    # Solve for x where y = half_max:
    # a*x^2 + b*x + c = half_max
    # a*x^2 + b*x + (c - half_max) = 0
    # Use quadratic formula: x = (-b ± sqrt(b^2 - 4*a*(c - half_max))) / (2*a)

    discriminant = b * b - 4.0 * a * (c - half_max)

    if discriminant <= 0:
        raise ValueError("Cannot calculate linewidth: invalid discriminant")

    # Distance from peak to half-max point
    sqrt_disc = np.sqrt(discriminant)
    half_x = (sqrt_disc - b) / (2.0 * a)

    # FWHM is twice the distance from peak to half-max
    linewidth = 2.0 * abs(x_peak - half_x)

    return x_peak, height, linewidth


@njit(cache=True)
def get_value_1d(data: np.ndarray, point: np.ndarray) -> float:
    """Get value at 1D point."""
    return data[point[0]]


@njit(cache=True)
def get_value_2d(data: np.ndarray, point: np.ndarray) -> float:
    """Get value at 2D point."""
    return data[point[0], point[1]]


@njit(cache=True)
def get_value_3d(data: np.ndarray, point: np.ndarray) -> float:
    """Get value at 3D point."""
    return data[point[0], point[1], point[2]]


@njit(cache=True)
def get_value_4d(data: np.ndarray, point: np.ndarray) -> float:
    """Get value at 4D point."""
    return data[point[0], point[1], point[2], point[3]]


def get_value_at_point(data: np.ndarray, point: np.ndarray) -> float:
    """Get value at N-dimensional point in data array.

    This matches the C implementation in npy_peak.c:get_value_at_point()
    lines 69-76. Note: C code reverses dimensions for NumPy compatibility.

    Args:
        data: N-dimensional array
        point: N-dimensional index

    Returns:
        Value at the specified point
    """
    # Dispatch to specialized function based on dimensionality
    # This avoids Numba's type inference issues with dynamic indexing
    ndim = data.ndim

    if ndim == 1:
        return get_value_1d(data, point)
    elif ndim == 2:
        return get_value_2d(data, point)
    elif ndim == 3:
        return get_value_3d(data, point)
    elif ndim == 4:
        return get_value_4d(data, point)
    else:
        raise ValueError(f"Dimensions > 4 not supported, got {ndim}")


@njit(cache=True)
def fit_parabolic_to_ndim_1d(
    data: np.ndarray,
    point: np.ndarray,
    dim: int
) -> Tuple[float, float, float]:
    """Fit parabola along one dimension of 1D data."""
    npts = data.shape[dim]

    if point[dim] <= 0 or point[dim] >= npts - 1:
        raise ValueError(f"Point at boundary in dimension {dim}")

    v_left = data[point[0] - 1] if dim == 0 else data[point[0]]
    v_middle = data[point[0]]
    v_right = data[point[0] + 1] if dim == 0 else data[point[0]]

    peak_offset, height, linewidth = fit_parabolic_1d(v_left, v_middle, v_right)
    peak_position = float(point[dim]) + peak_offset

    return peak_position, height, linewidth


@njit(cache=True)
def fit_parabolic_to_ndim_2d(
    data: np.ndarray,
    point: np.ndarray,
    dim: int
) -> Tuple[float, float, float]:
    """Fit parabola along one dimension of 2D data."""
    npts = data.shape[dim]

    if point[dim] <= 0 or point[dim] >= npts - 1:
        raise ValueError(f"Point at boundary in dimension {dim}")

    if dim == 0:
        v_left = data[point[0] - 1, point[1]]
        v_middle = data[point[0], point[1]]
        v_right = data[point[0] + 1, point[1]]
    else:  # dim == 1
        v_left = data[point[0], point[1] - 1]
        v_middle = data[point[0], point[1]]
        v_right = data[point[0], point[1] + 1]

    peak_offset, height, linewidth = fit_parabolic_1d(v_left, v_middle, v_right)
    peak_position = float(point[dim]) + peak_offset

    return peak_position, height, linewidth


@njit(cache=True)
def fit_parabolic_to_ndim_3d(
    data: np.ndarray,
    point: np.ndarray,
    dim: int
) -> Tuple[float, float, float]:
    """Fit parabola along one dimension of 3D data."""
    npts = data.shape[dim]

    if point[dim] <= 0 or point[dim] >= npts - 1:
        raise ValueError(f"Point at boundary in dimension {dim}")

    if dim == 0:
        v_left = data[point[0] - 1, point[1], point[2]]
        v_middle = data[point[0], point[1], point[2]]
        v_right = data[point[0] + 1, point[1], point[2]]
    elif dim == 1:
        v_left = data[point[0], point[1] - 1, point[2]]
        v_middle = data[point[0], point[1], point[2]]
        v_right = data[point[0], point[1] + 1, point[2]]
    else:  # dim == 2
        v_left = data[point[0], point[1], point[2] - 1]
        v_middle = data[point[0], point[1], point[2]]
        v_right = data[point[0], point[1], point[2] + 1]

    peak_offset, height, linewidth = fit_parabolic_1d(v_left, v_middle, v_right)
    peak_position = float(point[dim]) + peak_offset

    return peak_position, height, linewidth


@njit(cache=True)
def fit_parabolic_to_ndim_4d(
    data: np.ndarray,
    point: np.ndarray,
    dim: int
) -> Tuple[float, float, float]:
    """Fit parabola along one dimension of 4D data."""
    npts = data.shape[dim]

    if point[dim] <= 0 or point[dim] >= npts - 1:
        raise ValueError(f"Point at boundary in dimension {dim}")

    if dim == 0:
        v_left = data[point[0] - 1, point[1], point[2], point[3]]
        v_middle = data[point[0], point[1], point[2], point[3]]
        v_right = data[point[0] + 1, point[1], point[2], point[3]]
    elif dim == 1:
        v_left = data[point[0], point[1] - 1, point[2], point[3]]
        v_middle = data[point[0], point[1], point[2], point[3]]
        v_right = data[point[0], point[1] + 1, point[2], point[3]]
    elif dim == 2:
        v_left = data[point[0], point[1], point[2] - 1, point[3]]
        v_middle = data[point[0], point[1], point[2], point[3]]
        v_right = data[point[0], point[1], point[2] + 1, point[3]]
    else:  # dim == 3
        v_left = data[point[0], point[1], point[2], point[3] - 1]
        v_middle = data[point[0], point[1], point[2], point[3]]
        v_right = data[point[0], point[1], point[2], point[3] + 1]

    peak_offset, height, linewidth = fit_parabolic_1d(v_left, v_middle, v_right)
    peak_position = float(point[dim]) + peak_offset

    return peak_position, height, linewidth


def fit_parabolic_to_ndim(
    data: np.ndarray,
    point: np.ndarray,
    dim: int
) -> Tuple[float, float, float]:
    """Fit parabola along one dimension of N-dimensional data.

    This implements the C function fitParabolicToNDim() from npy_peak.c
    lines 395-435.

    Dispatcher function that calls specialized versions based on dimensionality.

    Args:
        data: N-dimensional array
        point: Peak position (integer grid coordinates)
        dim: Dimension along which to fit (0, 1, 2, ...)

    Returns:
        Tuple of (peak_position, peak_height, linewidth):
            peak_position: Refined position in this dimension (float)
            peak_height: Interpolated height
            linewidth: FWHM in this dimension

    Raises:
        ValueError: If point is at array boundary or parabola fit fails
    """
    ndim = data.ndim

    if ndim == 1:
        return fit_parabolic_to_ndim_1d(data, point, dim)
    elif ndim == 2:
        return fit_parabolic_to_ndim_2d(data, point, dim)
    elif ndim == 3:
        return fit_parabolic_to_ndim_3d(data, point, dim)
    elif ndim == 4:
        return fit_parabolic_to_ndim_4d(data, point, dim)
    else:
        raise ValueError(f"Dimensions > 4 not supported, got {ndim}")


# Peak finding helper functions

@njit(cache=True)
def half_max_position_2d(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    dim: int,
    direction: int,
    v_peak: float,
    find_maximum: bool
) -> float:
    """Find half-max position (2D version)."""
    v_half = 0.5 * v_peak
    v_prev = v_peak

    if direction == 1:
        i_start = point[dim] + 1
        i_end = points[dim]
        i_step = 1
    else:
        i_start = point[dim] - 1
        i_end = -1
        i_step = -1

    for i in range(i_start, i_end, i_step):
        if dim == 0:
            v_this = data[i, point[1]]
        else:
            v_this = data[point[0], i]

        if find_maximum:
            if v_this < v_half:
                return float(i - i_step * (v_half - v_this) / (v_prev - v_this))
        else:
            if v_this > v_half:
                return float(i - i_step * (v_half - v_this) / (v_prev - v_this))

        v_prev = v_this

    if direction == 1:
        return float(points[dim] - 1)
    else:
        return 1.0


@njit(cache=True)
def half_max_position_3d(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    dim: int,
    direction: int,
    v_peak: float,
    find_maximum: bool
) -> float:
    """Find half-max position (3D version)."""
    v_half = 0.5 * v_peak
    v_prev = v_peak

    if direction == 1:
        i_start = point[dim] + 1
        i_end = points[dim]
        i_step = 1
    else:
        i_start = point[dim] - 1
        i_end = -1
        i_step = -1

    for i in range(i_start, i_end, i_step):
        if dim == 0:
            v_this = data[i, point[1], point[2]]
        elif dim == 1:
            v_this = data[point[0], i, point[2]]
        else:
            v_this = data[point[0], point[1], i]

        if find_maximum:
            if v_this < v_half:
                return float(i - i_step * (v_half - v_this) / (v_prev - v_this))
        else:
            if v_this > v_half:
                return float(i - i_step * (v_half - v_this) / (v_prev - v_this))

        v_prev = v_this

    if direction == 1:
        return float(points[dim] - 1)
    else:
        return 1.0


def calculate_linewidth_at_point(
    data: np.ndarray,
    point: np.ndarray,
    points: np.ndarray,
    dim: int,
    v_peak: float,
    find_maximum: bool
) -> float:
    """Calculate FWHM linewidth along one dimension.

    This implements the C function half_max_linewidth() from npy_peak.c lines 383-393.

    Args:
        data: N-dimensional array
        point: Peak position
        points: Array shape
        dim: Dimension to measure
        v_peak: Peak height
        find_maximum: True for maxima, False for minima

    Returns:
        Full width at half maximum (FWHM)
    """
    ndim = data.ndim

    if ndim == 2:
        a = half_max_position_2d(data, point, points, dim, 1, v_peak, find_maximum)
        b = half_max_position_2d(data, point, points, dim, -1, v_peak, find_maximum)
    elif ndim == 3:
        a = half_max_position_3d(data, point, points, dim, 1, v_peak, find_maximum)
        b = half_max_position_3d(data, point, points, dim, -1, v_peak, find_maximum)
    else:
        raise ValueError(f"Linewidth calculation only supports 2D and 3D, got {ndim}D")

    linewidth = a - b
    return linewidth
