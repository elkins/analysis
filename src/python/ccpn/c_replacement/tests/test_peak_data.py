"""Test data generators for Peak module testing.

This module provides utilities to generate synthetic NMR peak data
for testing peak finding and fitting algorithms.
"""

import numpy as np
from typing import List, Tuple, Dict, Optional


def generate_gaussian_peak(
    shape: Tuple[int, ...],
    center: Tuple[float, ...],
    height: float,
    linewidth: Tuple[float, ...],
    noise_level: float = 0.0
) -> np.ndarray:
    """Generate synthetic N-dimensional Gaussian peak.

    The Gaussian peak model uses the FWHM (Full Width at Half Maximum) formulation
    consistent with the C implementation:
        y = h * exp(-4 * ln(2) * ((x-x0)/lw)^2)

    Args:
        shape: Tuple of array dimensions (e.g., (64, 64) for 2D)
        center: Peak center position in each dimension (can be non-integer)
        height: Peak height (intensity at center)
        linewidth: FWHM linewidth in each dimension
        noise_level: Standard deviation of Gaussian noise to add

    Returns:
        np.ndarray of dtype float32 containing the synthetic peak data
    """
    ndim = len(shape)
    if len(center) != ndim or len(linewidth) != ndim:
        raise ValueError(f"center and linewidth must match shape dimensions ({ndim})")

    # Create coordinate grids
    coords = np.meshgrid(*[np.arange(s, dtype=np.float32) for s in shape], indexing='ij')

    # Initialize with noise if requested
    if noise_level > 0:
        data = noise_level * np.random.randn(*shape).astype(np.float32)
    else:
        data = np.zeros(shape, dtype=np.float32)

    # Generate Gaussian peak: h * exp(-4*ln(2) * sum((x_i - c_i)^2 / lw_i^2))
    peak = np.ones(shape, dtype=np.float32) * height

    for i in range(ndim):
        dx = coords[i] - center[i]
        lw = linewidth[i]
        peak *= np.exp(-4 * np.log(2) * (dx / lw) ** 2)

    return data + peak


def generate_lorentzian_peak(
    shape: Tuple[int, ...],
    center: Tuple[float, ...],
    height: float,
    linewidth: Tuple[float, ...],
    noise_level: float = 0.0
) -> np.ndarray:
    """Generate synthetic N-dimensional Lorentzian peak.

    The Lorentzian peak model uses the FWHM formulation:
        y = h * prod(lw_i^2 / (lw_i^2 + 4*(x_i - c_i)^2))

    Args:
        shape: Tuple of array dimensions
        center: Peak center position in each dimension
        height: Peak height (intensity at center)
        linewidth: FWHM linewidth in each dimension
        noise_level: Standard deviation of Gaussian noise to add

    Returns:
        np.ndarray of dtype float32 containing the synthetic peak data
    """
    ndim = len(shape)
    if len(center) != ndim or len(linewidth) != ndim:
        raise ValueError(f"center and linewidth must match shape dimensions ({ndim})")

    # Create coordinate grids
    coords = np.meshgrid(*[np.arange(s, dtype=np.float32) for s in shape], indexing='ij')

    # Initialize with noise if requested
    if noise_level > 0:
        data = noise_level * np.random.randn(*shape).astype(np.float32)
    else:
        data = np.zeros(shape, dtype=np.float32)

    # Generate Lorentzian peak
    peak = np.ones(shape, dtype=np.float32) * height

    for i in range(ndim):
        dx = coords[i] - center[i]
        lw = linewidth[i]
        peak *= lw**2 / (lw**2 + 4 * dx**2)

    return data + peak


def generate_multi_peak_spectrum(
    shape: Tuple[int, ...],
    peaks: List[Dict],
    noise_level: float = 0.0
) -> np.ndarray:
    """Generate spectrum with multiple peaks.

    Args:
        shape: Tuple of array dimensions
        peaks: List of peak specifications, each containing:
            - 'center': Tuple[float, ...] - peak center
            - 'height': float - peak height
            - 'linewidth': Tuple[float, ...] - FWHM per dimension
            - 'model': str - 'gaussian' or 'lorentzian'
        noise_level: Standard deviation of Gaussian noise

    Returns:
        np.ndarray of dtype float32 with all peaks superimposed
    """
    # Initialize with noise
    if noise_level > 0:
        data = noise_level * np.random.randn(*shape).astype(np.float32)
    else:
        data = np.zeros(shape, dtype=np.float32)

    # Add each peak
    for peak_spec in peaks:
        model = peak_spec.get('model', 'gaussian').lower()

        if model == 'gaussian':
            peak_data = generate_gaussian_peak(
                shape,
                peak_spec['center'],
                peak_spec['height'],
                peak_spec['linewidth'],
                noise_level=0.0  # Already added noise to base
            )
        elif model == 'lorentzian':
            peak_data = generate_lorentzian_peak(
                shape,
                peak_spec['center'],
                peak_spec['height'],
                peak_spec['linewidth'],
                noise_level=0.0
            )
        else:
            raise ValueError(f"Unknown peak model: {model}")

        # Subtract the background noise we already added
        if noise_level > 0:
            peak_data -= noise_level * np.random.randn(*shape).astype(np.float32)

        data += peak_data

    return data


def generate_parabolic_test_case(
    offset: float = 0.0,
    height: float = 10.0,
    curvature: float = -1.0
) -> Tuple[float, float, float]:
    """Generate three-point parabola test case.

    Creates three values from a parabola y = a*(x - offset)^2 + height
    at x = -1, 0, 1 (left, middle, right).

    Args:
        offset: Peak position offset from middle point (-1 to 1)
        height: Peak height
        curvature: Parabola curvature (negative for maximum)

    Returns:
        Tuple of (v_left, v_middle, v_right)
    """
    # Parabola: y = a*(x - offset)^2 + height
    a = curvature

    v_left = a * (-1 - offset) ** 2 + height
    v_middle = a * (0 - offset) ** 2 + height
    v_right = a * (1 - offset) ** 2 + height

    return (float(v_left), float(v_middle), float(v_right))
