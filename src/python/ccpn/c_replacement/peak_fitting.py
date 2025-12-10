"""Levenberg-Marquardt peak fitting implementation.

This module implements peak fitting using scipy's Levenberg-Marquardt
optimizer for Gaussian and Lorentzian peak models.

Implementation Strategy:
- Uses scipy.optimize.curve_fit as the L-M backend (proven, robust)
- Provides Numba-compatible analytical derivative functions for testing
- Wraps scipy interface to match C extension API exactly

This pragmatic approach:
- Gets us to GREEN quickly with battle-tested optimization
- Maintains numerical accuracy
- Can be refactored to pure Numba later if performance requires it
"""

import numpy as np
from numba import njit
from typing import Tuple
from scipy.optimize import curve_fit


# =============================================================================
# Gauss-Jordan Matrix Solver (for testing, not used in main fitting)
# =============================================================================

def gauss_jordan_solve(matrix: np.ndarray, vector: np.ndarray) -> Tuple[np.ndarray, bool]:
    """Solve linear system Ax = b using Gauss-Jordan elimination.

    Note: Uses numpy.linalg.solve for reliability. This function is
    primarily for testing/validation purposes.

    Args:
        matrix: Square matrix A (n x n), float32
        vector: Right-hand side b (n,), float32

    Returns:
        solution: Solution vector x (n,), float32
        singular: True if matrix is singular
    """
    try:
        solution = np.linalg.solve(matrix, vector).astype(np.float32)

        # Check if solution is valid (not singular)
        # Verify Ax ≈ b
        residual = np.linalg.norm(matrix @ solution - vector)
        if residual > 1e-3 * np.linalg.norm(vector):
            return np.zeros(len(vector), dtype=np.float32), True

        return solution, False
    except np.linalg.LinAlgError:
        return np.zeros(len(vector), dtype=np.float32), True


# =============================================================================
# Gaussian Peak Model with Derivatives
# =============================================================================

@njit(cache=True)
def gaussian_nd_with_derivatives(x: np.ndarray, params: np.ndarray,
                                ndim: int, npeaks: int) -> Tuple[float, np.ndarray]:
    """Evaluate N-dimensional Gaussian model and its derivatives.

    The Gaussian model uses FWHM formulation:
        y = h * exp(-4 * ln(2) * sum((x_i - x0_i)^2 / lw_i^2))

    Args:
        x: Point coordinates (ndim,), int32
        params: Parameters array (npeaks * (1 + 2*ndim),), float32
                For each peak: [height, pos_1, ..., pos_ndim, lw_1, ..., lw_ndim]
        ndim: Number of dimensions
        npeaks: Number of peaks

    Returns:
        y_fit: Fitted value at x
        dy_dparams: Derivatives w.r.t. each parameter
    """
    nparams = npeaks * (1 + 2 * ndim)
    dy_dparams = np.zeros(nparams, dtype=np.float32)
    y_fit = 0.0

    c = 4.0 * np.log(2.0)  # Constant for FWHM formulation

    param_idx = 0
    for peak in range(npeaks):
        height = params[param_idx]
        param_idx += 1

        # Calculate exponent and derivatives
        exponent = 0.0
        for dim in range(ndim):
            pos = params[param_idx + dim]
            lw = params[param_idx + ndim + dim]
            dx = float(x[dim]) - pos
            exponent += c * (dx / lw) ** 2

        # Peak value
        peak_val = height * np.exp(-exponent)
        y_fit += peak_val

        # Derivatives
        peak_start_idx = peak * (1 + 2 * ndim)

        # d/d(height)
        dy_dparams[peak_start_idx] = np.exp(-exponent)

        # d/d(position) and d/d(linewidth)
        for dim in range(ndim):
            pos = params[peak_start_idx + 1 + dim]
            lw = params[peak_start_idx + 1 + ndim + dim]
            dx = float(x[dim]) - pos

            # d/d(position_i)
            dy_dparams[peak_start_idx + 1 + dim] = \
                peak_val * (2.0 * c * dx / (lw * lw))

            # d/d(linewidth_i)
            dy_dparams[peak_start_idx + 1 + ndim + dim] = \
                peak_val * (2.0 * c * dx * dx / (lw * lw * lw))

    return y_fit, dy_dparams


# =============================================================================
# Lorentzian Peak Model with Derivatives
# =============================================================================

@njit(cache=True)
def lorentzian_nd_with_derivatives(x: np.ndarray, params: np.ndarray,
                                  ndim: int, npeaks: int) -> Tuple[float, np.ndarray]:
    """Evaluate N-dimensional Lorentzian model and its derivatives.

    The Lorentzian model:
        y = h * product(lw_i^2 / (lw_i^2 + 4*(x_i - x0_i)^2))

    Args:
        x: Point coordinates (ndim,), int32
        params: Parameters array (npeaks * (1 + 2*ndim),), float32
        ndim: Number of dimensions
        npeaks: Number of peaks

    Returns:
        y_fit: Fitted value at x
        dy_dparams: Derivatives w.r.t. each parameter
    """
    nparams = npeaks * (1 + 2 * ndim)
    dy_dparams = np.zeros(nparams, dtype=np.float32)
    y_fit = 0.0

    param_idx = 0
    for peak in range(npeaks):
        height = params[param_idx]
        param_idx += 1

        # Calculate peak value as product over dimensions
        peak_val = height
        denominators = np.zeros(ndim, dtype=np.float32)

        for dim in range(ndim):
            pos = params[param_idx + dim]
            lw = params[param_idx + ndim + dim]
            dx = float(x[dim]) - pos
            denom = lw * lw + 4.0 * dx * dx
            denominators[dim] = denom
            peak_val *= (lw * lw) / denom

        y_fit += peak_val

        # Derivatives
        peak_start_idx = peak * (1 + 2 * ndim)

        # d/d(height)
        dy_dparams[peak_start_idx] = peak_val / height

        # d/d(position) and d/d(linewidth)
        for dim in range(ndim):
            pos = params[peak_start_idx + 1 + dim]
            lw = params[peak_start_idx + 1 + ndim + dim]
            dx = float(x[dim]) - pos
            denom = denominators[dim]

            # d/d(position_i)
            dy_dparams[peak_start_idx + 1 + dim] = \
                peak_val * (-8.0 * dx / denom)

            # d/d(linewidth_i)
            dy_dparams[peak_start_idx + 1 + ndim + dim] = \
                peak_val * (8.0 * dx * dx / (lw * denom))

    return y_fit, dy_dparams


# =============================================================================
# Peak Fitting using scipy.optimize.curve_fit
# =============================================================================

def fit_peak_region(data: np.ndarray, region: np.ndarray, initial_params: np.ndarray,
                   method: int, ndim: int, npeaks: int) -> Tuple[np.ndarray, np.ndarray, float]:
    """Fit peak(s) in a region using Levenberg-Marquardt optimization.

    Args:
        data: N-dimensional data array, float32
        region: Region bounds [[first_x, first_y, ...], [last_x, last_y, ...]], int32
        initial_params: Initial parameter guess, float32
        method: 0=Gaussian, 1=Lorentzian
        ndim: Number of dimensions
        npeaks: Number of peaks to fit

    Returns:
        fitted_params: Optimized parameters
        param_uncertainties: Parameter uncertainties (standard deviations)
        chisq: Reduced chi-squared
    """
    # Extract region data
    if ndim == 2:
        region_data = data[region[0,0]:region[1,0], region[0,1]:region[1,1]]
    elif ndim == 3:
        region_data = data[region[0,0]:region[1,0], region[0,1]:region[1,1], region[0,2]:region[1,2]]
    else:
        raise ValueError(f"fit_peak_region only supports 2D and 3D data, got ndim={ndim}")

    # Create coordinate arrays
    shape = region_data.shape
    coords = np.meshgrid(*[np.arange(s) for s in shape], indexing='ij')
    coords_flat = np.array([c.ravel() for c in coords]).T  # (npts, ndim)
    data_flat = region_data.ravel()

    # Define model function for scipy
    if method == 0:  # Gaussian
        def model_func(coords, *params):
            """Vectorized Gaussian model for scipy.curve_fit."""
            result = np.zeros(len(coords))
            params_array = np.array(params, dtype=np.float32)
            for i, coord in enumerate(coords):
                c = 4.0 * np.log(2.0)
                y = 0.0
                param_idx = 0
                for peak in range(npeaks):
                    height = params_array[param_idx]
                    param_idx += 1
                    exponent = 0.0
                    for dim in range(ndim):
                        pos = params_array[param_idx + dim]
                        lw = params_array[param_idx + ndim + dim]
                        dx = coord[dim] - pos
                        exponent += c * (dx / lw) ** 2
                    y += height * np.exp(-exponent)
                    param_idx += 2 * ndim
                result[i] = y
            return result
    else:  # Lorentzian
        def model_func(coords, *params):
            """Vectorized Lorentzian model for scipy.curve_fit."""
            result = np.zeros(len(coords))
            params_array = np.array(params, dtype=np.float32)
            for i, coord in enumerate(coords):
                y = 0.0
                param_idx = 0
                for peak in range(npeaks):
                    height = params_array[param_idx]
                    param_idx += 1
                    peak_val = height
                    for dim in range(ndim):
                        pos = params_array[param_idx + dim]
                        lw = params_array[param_idx + ndim + dim]
                        dx = coord[dim] - pos
                        denom = lw * lw + 4.0 * dx * dx
                        peak_val *= (lw * lw) / denom
                    y += peak_val
                    param_idx += 2 * ndim
                result[i] = y
            return result

    try:
        # Fit using curve_fit (Levenberg-Marquardt)
        popt, pcov = curve_fit(model_func, coords_flat, data_flat, p0=initial_params,
                              maxfev=100, method='lm')

        # Calculate uncertainties
        perr = np.sqrt(np.diag(pcov)).astype(np.float32)

        # Calculate chi-squared
        residuals = data_flat - model_func(coords_flat, *popt)
        chisq = np.sum(residuals**2) / (len(data_flat) - len(popt))

        return popt.astype(np.float32), perr, float(chisq)

    except Exception as e:
        # If fitting fails, return initial parameters with large uncertainties
        return initial_params, np.ones_like(initial_params) * 1e6, 1e6
