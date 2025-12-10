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
    # Numba doesn't support tuple(array) conversion
    # Handle common cases explicitly for efficiency
    ndim = len(point)

    if ndim == 1:
        return data[point[0]]
    elif ndim == 2:
        return data[point[0], point[1]]
    elif ndim == 3:
        return data[point[0], point[1], point[2]]
    elif ndim == 4:
        return data[point[0], point[1], point[2], point[3]]
    else:
        # For higher dimensions (rare in NMR), raise error
        raise ValueError("Dimensions > 4 not supported")


@njit(cache=True)
def fit_parabolic_to_ndim(
    data: np.ndarray,
    point: np.ndarray,
    dim: int
) -> Tuple[float, float, float]:
    """Fit parabola along one dimension of N-dimensional data.

    This implements the C function fitParabolicToNDim() from npy_peak.c
    lines 395-435.

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
    ndim = len(data.shape)
    npts = data.shape[dim]

    # Check if we're at a boundary (need neighbors on both sides)
    if point[dim] <= 0 or point[dim] >= npts - 1:
        raise ValueError(f"Point at boundary in dimension {dim}: cannot fit parabola")

    # Get three values along this dimension
    # Create neighbor points
    pnt_left = point.copy()
    pnt_middle = point.copy()
    pnt_right = point.copy()

    pnt_left[dim] = point[dim] - 1
    pnt_middle[dim] = point[dim]
    pnt_right[dim] = point[dim] + 1

    v_left = get_value_at_point(data, pnt_left)
    v_middle = get_value_at_point(data, pnt_middle)
    v_right = get_value_at_point(data, pnt_right)

    # Fit parabola to these three points
    peak_offset, height, linewidth = fit_parabolic_1d(v_left, v_middle, v_right)

    # Convert offset to absolute position
    peak_position = float(point[dim]) + peak_offset

    return peak_position, height, linewidth
