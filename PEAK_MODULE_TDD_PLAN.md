# Peak Module TDD Implementation Plan

## Executive Summary

**Goal**: Convert C extension `src/c/ccpnc/peak/npy_peak.c` (1,153 lines) to pure Python with Numba JIT compilation, following the proven TDD methodology from the contour module conversion.

**Scope**: Three main API functions for N-dimensional NMR peak analysis:
- `findPeaks()` - Automated peak detection with sophisticated filtering
- `fitPeaks()` - Gaussian/Lorentzian peak fitting using Levenberg-Marquardt
- `fitParabolicPeaks()` - Fast parabolic interpolation for peak refinement

**Dependencies**: Complex nonlinear fitting library requiring separate conversion:
- `nonlinear_model.c/h` (305 lines) - Levenberg-Marquardt implementation
- `gauss_jordan.c/h` - Matrix solver for fitting

**Estimated Complexity**: HIGH - More complex than contour module due to:
- Numerical optimization algorithms (Levenberg-Marquardt)
- Matrix algebra (Gauss-Jordan elimination)
- Multiple fitting methods with derivatives
- Statistical error analysis (covariance matrices)

---

## 1. C Code Analysis

### 1.1 File Structure

```
src/c/ccpnc/peak/
├── npy_peak.c          (1,153 lines) - Main Python interface
├── nonlinear_model.c   (305 lines)   - Levenberg-Marquardt fitting
├── gauss_jordan.c                    - Matrix solver
├── npy_defns.h                       - Python/NumPy interface macros
├── nonlinear_model.h                 - Fitting function declarations
├── defns.h                           - Common C macros and definitions
└── gauss_jordan.h                    - Matrix solver declarations
```

### 1.2 API Functions (Python Interface)

#### Function 1: `findPeaks()`

**Purpose**: Automated peak detection in N-dimensional NMR data with sophisticated filtering.

**C Signature** (lines 891-1022):
```c
static PyObject *findPeaks(PyObject *self, PyObject *args) {
    PyArg_ParseTuple(args, "O!iiffO!ifO!O!O!O!",
        &PyArray_Type, &data_array,           // float32 ND array
        &have_low,                             // bool: search for minima
        &have_high,                            // bool: search for maxima
        &low,                                  // float: threshold for minima
        &high,                                 // float: threshold for maxima
        &PyList_Type, &buffer_obj,            // list[int]: exclusion buffer per dim
        &nonadjacent,                          // bool: check all 3^N neighbors
        &drop_factor,                          // float: minimum drop from peak
        &PyList_Type, &min_linewidth_obj,     // list[float]: min linewidth per dim
        &PyList_Type, &excluded_regions_obj,  // list[array]: regions to exclude
        &PyList_Type, &diagonal_exclusion_dims_obj,       // diagonal exclusions
        &PyList_Type, &diagonal_exclusion_transform_obj); // diagonal transforms

    // Returns: list[(point_tuple, height_float)]
}
```

**Peak Detection Algorithm** (lines 459-564):

1. **Threshold Check**: Filter points by intensity (lines 531-536)
   - Check if `v >= high` (maximum) or `v <= low` (minimum)

2. **Extremum Check** (lines 539-544):
   - **Adjacent mode** (`nonadjacent=0`): Check only 2N neighbors along axes
   - **Non-adjacent mode** (`nonadjacent=1`): Check all 3^N cube neighbors

3. **Drop Factor Check** (lines 546-548):
   - Verify intensity drops by `drop_factor * |peak_value|` in all directions
   - Prevents detecting flat regions or shoulders as peaks

4. **Linewidth Check** (lines 550-552):
   - Calculate half-max linewidth in each dimension
   - Reject peaks narrower than `min_linewidth[dim]`

5. **Buffer Check** (lines 554-556):
   - Ensure new peak is not within `buffer[dim]` of existing peaks
   - Prevents duplicate detection

6. **Excluded Regions** (lines 514-526):
   - Skip points in user-defined exclusion boxes
   - Skip diagonal exclusion regions (for homonuclear spectra)

**Helper Functions**:
- `check_nonadjacent_points()` (lines 201-248): 3^N neighbor extremum check
- `check_adjacent_points()` (lines 251-288): 2N neighbor extremum check
- `check_drop()` (lines 330-344): Drop factor verification
- `drops_in_direction()` (lines 290-328): Directional drop check
- `check_linewidth()` (lines 446-457): Multi-dimensional linewidth check
- `half_max_linewidth()` (lines 383-393): Calculate FWHM
- `half_max_position()` (lines 346-381): Find half-max crossing point
- `check_buffer()` (lines 155-168): Buffer zone verification
- `point_within_peak_buffer()` (lines 78-91): Distance check

#### Function 2: `fitPeaks()`

**Purpose**: Fit Gaussian or Lorentzian peak models using nonlinear least squares (Levenberg-Marquardt).

**C Signature** (lines 1024-1065):
```c
static PyObject *fitPeaks(PyObject *self, PyObject *args) {
    PyArg_ParseTuple(args, "O!O!O!i",
        &PyArray_Type, &data_array,      // float32 ND array
        &PyArray_Type, &region_array,    // int32 array (2 x ndim) [first, last]
        &PyArray_Type, &peak_array,      // float32 array (npeaks x ndim) positions
        &method);                         // int: 0=Gaussian, 1=Lorentzian

    // Returns: list[(height, position_tuple, linewidth_tuple)]
}
```

**Fitting Algorithm** (lines 767-889):

1. **Region Setup** (lines 779-788):
   - Extract fitting region `[first, last]` per dimension
   - Calculate `region_size = last - first`
   - Compute cumulative indices for region

2. **Data Extraction** (lines 795-800):
   - Extract data block: `y[j] = data_array[region_offset + array_index[j]]`
   - Create index array: `x[j] = j` (flattened multi-dimensional index)

3. **Initial Parameters** (lines 813-839):
   - For each peak:
     - `height = data_array[nearest_integer(peak_position)]`
     - `position = peak_position` (initial guess)
     - `linewidth[dim] = half_max_linewidth(data_array, height, position, dim)`
   - Total parameters: `nparams = npeaks × (1 + 2 × ndim)`
     - 1 height
     - ndim positions
     - ndim linewidths

4. **Nonlinear Fitting** (line 848):
   - Calls `nonlinear_fit()` with Levenberg-Marquardt algorithm
   - Fitting function: `_fitting_func()` (lines 627-662)
   - Convergence criteria in `nonlinear_model.c`

5. **Parameter Extraction** (lines 860-883):
   - Unpack fitted parameters: `(height, position, linewidth)` per peak
   - Return as list of tuples

**Peak Models**:

**Gaussian** (lines 566-595):
```c
float gaussian(int ndim, int *x, float *a, float *dy_da) {
    float h = a[0];
    float *position = a + 1;
    float *linewidth = a + 1 + ndim;

    float y = h;
    for (i = 0; i < ndim; i++) {
        dx = x[i] - position[i];
        lw = linewidth[i];
        y *= exp(-4 * log(2) * dx^2 / lw^2);  // FWHM formulation

        // Derivatives for Levenberg-Marquardt:
        dy_dh = y / h;
        dy_dp[i] = y * 8 * log(2) * dx / lw^2;
        dy_dl[i] = y * 8 * log(2) * dx^2 / lw^3;
    }
    return y;
}
```

**Lorentzian** (lines 597-625):
```c
float lorentzian(int ndim, int *x, float *a, float *dy_da) {
    float h = a[0];
    float *position = a + 1;
    float *linewidth = a + 1 + ndim;

    float y = h;
    for (i = 0; i < ndim; i++) {
        dx = x[i] - position[i];
        lw = linewidth[i];
        d = lw^2 + 4 * dx^2;
        y *= lw^2 / d;

        // Derivatives:
        dy_dh = y / h;
        dy_dp[i] = y * 8 * dx / d;
        dy_dl[i] = y * 8 * dx^2 / (lw * d);
    }
    return y;
}
```

**Fitting Function** (lines 627-662):
```c
void _fitting_func(float xind, float *a, float *y_fit, float *dy_da, void *user_data) {
    // xind: flattened multi-dimensional index
    // a: parameters [h1, p1x, p1y, ..., lw1x, lw1y, ..., h2, p2x, ...]
    // y_fit: output fitted value
    // dy_da: output derivatives (for Levenberg-Marquardt)

    // Convert flat index to ND coordinates
    ARRAY_OF_INDEX(x, ind, cumul_region, ndim);
    ADD_VECTORS(x, x, region_offset, ndim);

    // Bounds check: penalize out-of-region positions
    if (position outside region) {
        *y_fit = LARGE_NUMBER;  // 1.0e20
        return;
    }

    // Sum contributions from all peaks
    *y_fit = 0;
    for (j = 0; j < npeaks; j++) {
        *y_fit += gaussian(ndim, x, a, dy_da);  // or lorentzian
        a += nparams_per_peak;
        dy_da += nparams_per_peak;
    }
}
```

#### Function 3: `fitParabolicPeaks()`

**Purpose**: Fast parabolic interpolation for peak refinement (no iterative fitting).

**C Signature** (lines 1067-1103):
```c
static PyObject *fitParabolicPeaks(PyObject *self, PyObject *args) {
    PyArg_ParseTuple(args, "O!O!O!",
        &PyArray_Type, &data_array,      // float32 ND array
        &PyArray_Type, &region_array,    // int32 array (2 x ndim)
        &PyArray_Type, &peak_array);     // float32 array (npeaks x ndim)

    // Returns: list[(height, position_tuple, linewidth_tuple)]
}
```

**Parabolic Fitting Algorithm** (lines 664-765):

1. **Peak Neighborhood** (lines 702-714):
   - Find nearest grid point: `grid_posn[i] = NEAREST_INTEGER(peak_posn[i])`
   - Clip to array bounds: `[0, npts-1]`
   - Get center height: `height = data_array[grid_posn]`

2. **1D Parabolic Fit Per Dimension** (lines 721-723):
   - For each dimension `i`:
     - Call `fitParabolicToNDim()` to fit along axis `i`
     - Returns: `peakFit[i]`, `lineWidth[i]`, updated `height`

3. **Parabolic Interpolation** (lines 395-435):
```c
fitParabolicToNDim(data_array, point, dim) {
    // Get three points along dimension 'dim'
    pnt[dim] = point[dim] - 1;  vl = data_array[pnt];  // left
    pnt[dim] = point[dim];      vm = data_array[pnt];  // middle
    pnt[dim] = point[dim] + 1;  vr = data_array[pnt];  // right

    // Fit parabola: y = a*x^2 + b*x + c
    fit_position_x(vl, vm, vr, &peak, &height, &lineFit) {
        c = vm;
        a = 0.5 * (vl + vr - 2*vm);
        b = vr - 0.5 * (vr + vl);

        // Peak position: dy/dx = 0
        x = -b / (2*a);
        peakPos = x;  // offset from grid point
        height = a*x^2 + b*x + c;

        // Linewidth at half-max
        k = b^2 - 4*a*(c - 0.5*height);
        if (k <= 0) return ERROR;
        halfX = (sqrt(k) - b) / (2*a);
        lineFit = 2 * |x - halfX|;  // FWHM
    }

    return peakFit = peak + point[dim];
}
```

4. **Parameter Assembly** (lines 737-760):
   - Pack results: `(height, [peakFit[0], ...], [lineWidth[0], ...])`

### 1.3 Levenberg-Marquardt Nonlinear Fitting

**File**: `src/c/ccpnc/peak/nonlinear_model.c` (305 lines)

**Purpose**: Implement Levenberg-Marquardt algorithm for nonlinear least-squares fitting.

**Main Entry Point** (lines 259-304):
```c
CcpnStatus nonlinear_fit(
    int npts,                          // Number of data points
    float *x,                          // x data (flattened ND indices)
    float *y,                          // y data (intensities)
    float *w,                          // weights (NULL = uniform)
    float *y_fit,                      // output: fitted y values
    int nparams,                       // Number of parameters
    float *params,                     // in/out: parameter values
    float *params_dev,                 // out: parameter uncertainties
    int max_iter,                      // Maximum iterations (0 = 20)
    float noise,                       // Noise estimate (0 = auto 5%)
    float *chisq,                      // out: chi-squared
    Nonlinear_model_func func,         // Model function: func(x, a, &y, &dy_da)
    void *user_data,                   // Context (FitPeak struct)
    char *error_msg                    // Error message buffer
)
```

**Algorithm** (lines 201-257):

1. **Initialization**:
   - Allocate workspace: `covar[][]`, `alpha[][]`, `beta[]`, `da[]`, `ap[]`, `dy_da[]`
   - Auto-estimate noise if not provided: `noise = 0.05 * max(|y|)`
   - Set max iterations: default 20

2. **Iterative Refinement**:
```c
CHECK_NONLINEAR_MODEL(INITIAL_STAGE);

for (iter = 0; iter < MAX_MODEL_ITER && cond < MAX_CONDITION; iter++) {
    old_chisq = *chisq;
    CHECK_NONLINEAR_MODEL(GENERAL_STAGE);

    if (*chisq > old_chisq)
        cond = 0;  // Reset convergence counter
    else if ((old_chisq - *chisq) < chisq_stop_criterion)
        cond++;    // Increment convergence counter
}

if (iter == MAX_MODEL_ITER)
    RETURN_ERROR_MSG("fit did not converge");
```

3. **Final Covariance**:
```c
CHECK_NONLINEAR_MODEL(FINAL_STAGE);

// Compute parameter uncertainties
for (i = 0; i < nparams; i++)
    params_dev[i] = sqrt(chisq * max(covar[i][i], 0));
```

**Core Algorithm** (lines 126-199):
```c
CcpnStatus nonlinear_model(
    float *x, float *y, float *w, int n,
    float *a,                          // Parameters
    float **covar,                     // Covariance matrix
    float **alpha,                     // Curvature matrix
    float *beta,                       // Gradient vector
    float *da,                         // Parameter increments
    float *ap,                         // Trial parameters
    float *dy_da,                      // Derivatives
    int *piv, int *row, int *col,     // Workspace for Gauss-Jordan
    int m,                             // Number of parameters
    float *chisq,                      // Chi-squared
    float *lambda,                     // Damping parameter
    Nonlinear_model_func func,
    int stage,
    void *user_data,
    char *error_msg
) {
    if (stage == INITIAL_STAGE) {
        lambda = 0.001;
        find_linearised(x, y, w, n, a, dy_da, alpha, beta, m, chisq, func, user_data);
    } else {
        lambda = *lambda;
    }

    // Modify curvature matrix for damping
    for (i = 0; i < m; i++) {
        COPY_VECTOR(covar[i], alpha[i], m);
        covar[i][i] *= (1 + lambda);
    }

    // Solve linear system: covar * da = beta
    COPY_VECTOR(da, beta, m);
    gauss_jordan_vector(covar, da, m, piv, row, col, &singular);

    if (singular)
        RETURN_ERROR_MSG("singular nonlinear model");

    if (stage == FINAL_STAGE)
        return CCPN_OK;

    // Try new parameters: ap = a + da
    ADD_VECTORS(ap, a, da, m);
    find_linearised(x, y, w, n, ap, dy_da, covar, da, m, chisq, func, user_data);

    // Accept/reject step
    if (*chisq < csq) {
        *lambda = 0.1 * lambda;  // Decrease damping (more Gauss-Newton)
        COPY_VECTOR(a, ap, m);
        COPY_VECTOR(beta, da, m);
        for (i = 0; i < m; i++)
            COPY_VECTOR(alpha[i], covar[i], m);
    } else {
        *lambda = 10.0 * lambda;  // Increase damping (more gradient descent)
        *chisq = csq;
    }

    return CCPN_OK;
}
```

**Linearization** (lines 67-124):
```c
void find_linearised(
    float *x, float *y, float *w, int n,
    float *a, float *dy_da,
    float **alpha, float *beta, int m,
    float *chisq,
    Nonlinear_model_func func,
    void *user_data
) {
    // Build normal equations: alpha * da = beta
    // alpha[j][k] = sum_i (dy_da[j] * dy_da[k] * weight)
    // beta[j] = sum_i (dy_da[j] * (y - y_fit) * weight)

    for (i = 0; i < m; i++)
        for (j = 0; j <= i; j++)
            alpha[i][j] = 0;

    ZERO_VECTOR(beta, m);
    c = 0;

    for (i = 0; i < n; i++) {
        (*func)(x[i], a, &y_fit, dy_da, user_data);
        dy = y[i] - y_fit;

        for (j = 0; j < m; j++) {
            wgt = w ? w[i] * dy_da[j] : dy_da[j];

            for (k = 0; k <= j; k++)
                alpha[j][k] += wgt * dy_da[k];

            beta[j] += wgt * dy;
        }

        c += (w ? w[i] : 1.0) * dy * dy;
    }

    *chisq = c;

    // Fill upper triangle
    for (i = 0; i < m-1; i++)
        for (j = i+1; j < m; j++)
            alpha[i][j] = alpha[j][i];
}
```

**Convergence Criteria**:
- `MAX_MODEL_ITER = 20` iterations
- `MAX_CONDITION = 4` consecutive small improvements
- `CHISQ_STOP_CRITERION = 0.1 * noise^2`

### 1.4 Constants and Macros

```c
#define MAX_NDIM 10                    // Maximum dimensionality
#define GAUSSIAN_METHOD 0
#define LORENTZIAN_METHOD 1
#define LARGE_NUMBER 1.0e20           // Penalty for out-of-bounds
#define MAX_MODEL_ITER 20             // Levenberg-Marquardt iterations
#define MAX_CONDITION 4               // Convergence counter
#define CHISQ_STOP_CRITERION (1.0e-1) // Relative chi-squared change
```

### 1.5 Current Usage Patterns

**Usage locations** (31 Python files):
- Peak picking: `src/python/ccpn/core/lib/PeakListLib.py:166`
- Peak fitting: `src/python/ccpn/core/lib/PeakPickers/PeakPickerNd.py:254,319,536,547`
- Testing: `src/c/ccpnc/peak/testing/Test_PeakFit.py:59,77,82,227,413,485,540`

**Example usage**:
```python
from ccpnc import Peak as CPeak

# Find peaks
peakPoints = CPeak.findPeaks(
    dataArray,              # np.float32 ND array
    doNeg,                  # bool: find minima
    doPos,                  # bool: find maxima
    negLevel,               # float: threshold
    posLevel,               # float: threshold
    exclusionBuffer,        # list[int]: per-dim buffer
    nonAdj,                 # bool: check all neighbors
    minDropFactor,          # float: drop criterion
    minLinewidth,           # list[float]: per-dim
    excludedRegionsList,    # list[array]: exclusion boxes
    excludedDiagonalDimsList,           # diagonal exclusions
    excludedDiagonalTransformList       # diagonal transforms
)
# Returns: list[((x, y, ...), height)]

# Fit peaks (Gaussian/Lorentzian)
regionArray = np.array([[first_x, first_y, ...],
                        [last_x, last_y, ...]], dtype=np.int32)
peakArray = np.array([[peak1_x, peak1_y, ...],
                      [peak2_x, peak2_y, ...]], dtype=np.float32)
method = 0  # 0=Gaussian, 1=Lorentzian

result = CPeak.fitPeaks(dataArray, regionArray, peakArray, method)
# Returns: list[(height, (pos_x, pos_y, ...), (lw_x, lw_y, ...))]

# Fit peaks (Parabolic - fast)
result = CPeak.fitParabolicPeaks(dataArray, regionArray, peakArray)
# Returns: list[(height, (pos_x, pos_y, ...), (lw_x, lw_y, ...))]
```

---

## 2. Python Conversion Strategy

### 2.1 Module Structure

```
src/python/ccpn/c_replacement/
├── peak_compat.py           # Compatibility wrapper (like contour_compat.py)
├── peak_numba.py           # Numba-optimized implementations
├── peak_fitting.py         # Levenberg-Marquardt fitting engine
└── peak_models.py          # Gaussian/Lorentzian models with derivatives
```

### 2.2 Implementation Phases

#### Phase 1: Peak Models and Parabolic Fitting (Simplest)

**Why first?**
- No dependencies on Levenberg-Marquardt
- Parabolic fitting is analytical (no iteration)
- Gaussian/Lorentzian models needed for testing, simpler without derivatives initially

**Modules**:
```python
# peak_models.py
@njit(cache=True)
def gaussian_nd(x, height, position, linewidth):
    """N-dimensional Gaussian peak model."""

@njit(cache=True)
def lorentzian_nd(x, height, position, linewidth):
    """N-dimensional Lorentzian peak model."""

@njit(cache=True)
def fit_parabolic_1d(v_left, v_middle, v_right):
    """Parabolic interpolation along one dimension."""
    # Returns: (peak_position, peak_height, linewidth)

@njit(cache=True)
def fit_parabolic_peaks(data, region, peaks):
    """Fast parabolic peak fitting (non-iterative)."""
    # For each peak, for each dimension:
    #   - Get 3-point neighborhood
    #   - Fit parabola
    #   - Return refined position + linewidth
```

#### Phase 2: Peak Finding (Medium Complexity)

**Why second?**
- No fitting dependencies
- Complex filtering logic, but purely algorithmic
- Critical for overall workflow

**Modules**:
```python
# peak_numba.py
@njit(cache=True)
def check_adjacent_extremum(data, point, find_maximum):
    """Check if point is extremum vs 2N neighbors."""

@njit(cache=True)
def check_nonadjacent_extremum(data, point, find_maximum):
    """Check if point is extremum vs 3^N neighbors."""

@njit(cache=True)
def check_drop_criterion(data, point, drop_factor, find_maximum):
    """Verify intensity drops in all directions."""

@njit(cache=True)
def calculate_half_max_linewidth(data, point, height, dim):
    """Calculate FWHM along one dimension."""

@njit(cache=True)
def check_linewidth_criterion(data, point, height, min_linewidth):
    """Verify peak meets minimum linewidth criteria."""

@njit(cache=True)
def point_in_buffer(point, peak_list, buffer):
    """Check if point is too close to existing peaks."""

@njit(cache=True)
def find_peaks(data, have_low, have_high, low, high,
               buffer, nonadjacent, drop_factor, min_linewidth,
               excluded_regions, diagonal_exclusions):
    """Main peak finding algorithm."""
    # Iterate all points
    # Apply all filters
    # Return peak list
```

#### Phase 3: Levenberg-Marquardt Fitting (Highest Complexity)

**Why last?**
- Most complex algorithm
- Requires derivatives of peak models
- Matrix algebra with Gauss-Jordan solver
- Careful validation against C implementation

**Modules**:
```python
# peak_models.py (add derivatives)
@njit(cache=True)
def gaussian_nd_with_derivatives(x, params, ndim, npeaks):
    """Gaussian model with analytical derivatives for Levenberg-Marquardt."""
    # Returns: (y_fit, dy_dparams)

@njit(cache=True)
def lorentzian_nd_with_derivatives(x, params, ndim, npeaks):
    """Lorentzian model with analytical derivatives."""

# peak_fitting.py
@njit(cache=True)
def gauss_jordan_solve(matrix, vector):
    """Gauss-Jordan elimination with partial pivoting."""
    # Solve: matrix * x = vector
    # Returns: x, singular_flag

@njit(cache=True)
def find_linearized(x_data, y_data, weights, params, model_func):
    """Build normal equations for Levenberg-Marquardt."""
    # Returns: (alpha, beta, chisq)

@njit(cache=True)
def levenberg_marquardt_step(x_data, y_data, weights, params,
                              lambda_damping, stage, model_func):
    """Single iteration of Levenberg-Marquardt algorithm."""
    # Returns: (new_params, new_chisq, new_lambda, converged)

@njit(cache=True)
def nonlinear_fit(x_data, y_data, weights, initial_params,
                  model_func, max_iter=20, noise_estimate=None):
    """Full Levenberg-Marquardt fitting."""
    # Returns: (fitted_params, param_uncertainties, chisq)

@njit(cache=True)
def fit_peaks(data, region, peaks, method):
    """Fit Gaussian or Lorentzian peaks using Levenberg-Marquardt."""
    # Extract region data
    # Initialize parameters
    # Run nonlinear_fit()
    # Unpack results
```

### 2.3 Compatibility Wrapper

```python
# peak_compat.py
"""Compatibility wrapper for Peak module (C → Python)."""

import numpy as np
from typing import List, Tuple, Optional

# Try to import C extension, fall back to Python
try:
    from ccpnc import Peak as _c_peak
    _implementation = _c_peak
    _using_c = True
except ImportError:
    from . import peak_numba as _implementation
    _using_c = False

def get_implementation_info():
    """Return information about current implementation."""
    return {
        'implementation': 'C extension' if _using_c else 'Pure Python (Numba)',
        'module': _implementation.__name__,
    }

class PeakFinder:
    """Peak finding and fitting for N-dimensional NMR data."""

    @staticmethod
    def findPeaks(dataArray: np.ndarray,
                  haveLow: bool, haveHigh: bool,
                  low: float, high: float,
                  buffer: List[int],
                  nonadjacent: bool,
                  dropFactor: float,
                  minLinewidth: List[float],
                  excludedRegions: List[np.ndarray],
                  diagonalExclusionDims: List[np.ndarray],
                  diagonalExclusionTransform: List[np.ndarray]
                  ) -> List[Tuple[Tuple[int, ...], float]]:
        """Find peaks in N-dimensional data.

        Args:
            dataArray: N-dimensional float32 array
            haveLow: Search for minima
            haveHigh: Search for maxima
            low: Threshold for minima
            high: Threshold for maxima
            buffer: Exclusion buffer per dimension
            nonadjacent: Check all 3^N neighbors (vs 2N)
            dropFactor: Minimum drop from peak
            minLinewidth: Minimum linewidth per dimension
            excludedRegions: List of exclusion boxes
            diagonalExclusionDims: Diagonal exclusion dimensions
            diagonalExclusionTransform: Diagonal exclusion transforms

        Returns:
            List of (position_tuple, height) for each peak
        """
        return _implementation.findPeaks(
            dataArray, haveLow, haveHigh, low, high,
            buffer, nonadjacent, dropFactor, minLinewidth,
            excludedRegions, diagonalExclusionDims, diagonalExclusionTransform
        )

    @staticmethod
    def fitPeaks(dataArray: np.ndarray,
                 regionArray: np.ndarray,
                 peakArray: np.ndarray,
                 method: int
                 ) -> List[Tuple[float, Tuple[float, ...], Tuple[float, ...]]]:
        """Fit Gaussian or Lorentzian peaks.

        Args:
            dataArray: N-dimensional float32 array
            regionArray: int32 array (2 x ndim) [[first_x, first_y, ...],
                                                  [last_x, last_y, ...]]
            peakArray: float32 array (npeaks x ndim) initial positions
            method: 0=Gaussian, 1=Lorentzian

        Returns:
            List of (height, position_tuple, linewidth_tuple) for each peak
        """
        return _implementation.fitPeaks(dataArray, regionArray, peakArray, method)

    @staticmethod
    def fitParabolicPeaks(dataArray: np.ndarray,
                          regionArray: np.ndarray,
                          peakArray: np.ndarray
                          ) -> List[Tuple[float, Tuple[float, ...], Tuple[float, ...]]]:
        """Fit parabolic peaks (fast, non-iterative).

        Args:
            dataArray: N-dimensional float32 array
            regionArray: int32 array (2 x ndim)
            peakArray: float32 array (npeaks x ndim) initial positions

        Returns:
            List of (height, position_tuple, linewidth_tuple) for each peak
        """
        return _implementation.fitParabolicPeaks(dataArray, regionArray, peakArray)
```

---

## 3. TDD Test Plan

### 3.1 Test Strategy

Following contour module TDD success:
1. **RED**: Write failing test
2. **GREEN**: Implement minimal code to pass
3. **REFACTOR**: Optimize with Numba, ensure C fallback works

### 3.2 Test Data Generators

```python
# tests/test_peak_data.py
import numpy as np

def generate_gaussian_peak(shape, center, height, linewidth, noise_level=0.0):
    """Generate synthetic Gaussian peak for testing."""
    ndim = len(shape)
    coords = np.meshgrid(*[np.arange(s) for s in shape], indexing='ij')

    data = np.ones(shape, dtype=np.float32) * noise_level * np.random.randn(*shape)

    peak = height
    for i in range(ndim):
        dx = coords[i] - center[i]
        lw = linewidth[i]
        peak = peak * np.exp(-4 * np.log(2) * dx**2 / lw**2)

    return data + peak

def generate_lorentzian_peak(shape, center, height, linewidth, noise_level=0.0):
    """Generate synthetic Lorentzian peak for testing."""
    ndim = len(shape)
    coords = np.meshgrid(*[np.arange(s) for s in shape], indexing='ij')

    data = np.ones(shape, dtype=np.float32) * noise_level * np.random.randn(*shape)

    peak = height
    for i in range(ndim):
        dx = coords[i] - center[i]
        lw = linewidth[i]
        peak = peak * lw**2 / (lw**2 + 4 * dx**2)

    return data + peak

def generate_multi_peak_spectrum(shape, peaks, noise_level=0.0):
    """Generate spectrum with multiple peaks.

    Args:
        shape: Tuple of array dimensions
        peaks: List of dicts with 'center', 'height', 'linewidth', 'model'
        noise_level: Standard deviation of Gaussian noise

    Returns:
        np.ndarray of dtype float32
    """
    data = np.zeros(shape, dtype=np.float32)
    if noise_level > 0:
        data += noise_level * np.random.randn(*shape).astype(np.float32)

    for peak in peaks:
        if peak['model'] == 'gaussian':
            peak_data = generate_gaussian_peak(
                shape, peak['center'], peak['height'], peak['linewidth'], 0.0
            )
        elif peak['model'] == 'lorentzian':
            peak_data = generate_lorentzian_peak(
                shape, peak['center'], peak['height'], peak['linewidth'], 0.0
            )
        data += peak_data

    return data
```

### 3.3 Phase 1 Tests: Parabolic Fitting

#### Test 1.1: 1D Parabolic Fit (Simple Case)
```python
def test_parabolic_fit_1d_simple():
    """Test parabolic fitting along one dimension."""
    # Perfect parabola: y = -(x-5)^2 + 10
    # Peak at x=5, height=10
    v_left = 6    # x=4
    v_middle = 10  # x=5
    v_right = 6    # x=4

    peak_pos, peak_height, linewidth = fit_parabolic_1d(v_left, v_middle, v_right)

    assert np.isclose(peak_pos, 0.0)  # Offset from middle
    assert np.isclose(peak_height, 10.0)
    assert linewidth > 0  # Should calculate FWHM
```

#### Test 1.2: 1D Parabolic Fit (Offset Peak)
```python
def test_parabolic_fit_1d_offset():
    """Test parabolic fitting with peak between grid points."""
    # Parabola: y = -(x-5.3)^2 + 10
    # Peak at x=5.3 (offset +0.3 from grid point 5)
    v_left = 8.31   # x=4
    v_middle = 9.91  # x=5
    v_right = 9.11   # x=6

    peak_pos, peak_height, linewidth = fit_parabolic_1d(v_left, v_middle, v_right)

    assert np.isclose(peak_pos, 0.3, atol=0.01)
    assert np.isclose(peak_height, 10.0, atol=0.1)
```

#### Test 1.3: 2D Parabolic Peak Fit
```python
def test_parabolic_fit_2d_peak():
    """Test 2D parabolic peak fitting."""
    # Generate 2D Gaussian peak
    shape = (20, 20)
    center = (10.3, 15.7)  # Non-integer positions
    height = 100.0
    linewidth = (2.5, 3.0)

    data = generate_gaussian_peak(shape, center, height, linewidth)

    # Peak array: initial guess (rounded positions)
    peak_array = np.array([[10.0, 16.0]], dtype=np.float32)

    # Region array: fit region around peak
    region_array = np.array([[8, 13],   # x: [8, 18)
                             [13, 18]], dtype=np.int32)  # y: [13, 18)

    results = fit_parabolic_peaks(data, region_array, peak_array)

    assert len(results) == 1
    fitted_height, fitted_pos, fitted_lw = results[0]

    assert np.isclose(fitted_height, height, rtol=0.05)
    assert np.allclose(fitted_pos, center, atol=0.2)
    assert np.allclose(fitted_lw, linewidth, rtol=0.15)
```

#### Test 1.4: 3D Parabolic Peak Fit
```python
def test_parabolic_fit_3d_peak():
    """Test 3D parabolic peak fitting."""
    shape = (16, 20, 24)
    center = (8.2, 10.5, 12.8)
    height = 500.0
    linewidth = (2.0, 2.5, 3.0)

    data = generate_gaussian_peak(shape, center, height, linewidth)

    peak_array = np.array([[8.0, 11.0, 13.0]], dtype=np.float32)
    region_array = np.array([[6, 8, 10],
                             [11, 13, 15]], dtype=np.int32)

    results = fit_parabolic_peaks(data, region_array, peak_array)

    assert len(results) == 1
    fitted_height, fitted_pos, fitted_lw = results[0]

    assert np.isclose(fitted_height, height, rtol=0.05)
    assert np.allclose(fitted_pos, center, atol=0.3)
    assert np.allclose(fitted_lw, linewidth, rtol=0.2)
```

#### Test 1.5: Multiple Parabolic Peaks
```python
def test_parabolic_fit_multiple_peaks():
    """Test fitting multiple peaks in one call."""
    shape = (30, 30)
    peaks = [
        {'center': (10, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
        {'center': (20, 15), 'height': 80, 'linewidth': (3, 2.5), 'model': 'gaussian'},
        {'center': (15, 22), 'height': 120, 'linewidth': (2.5, 3), 'model': 'gaussian'},
    ]

    data = generate_multi_peak_spectrum(shape, peaks)

    peak_array = np.array([[10, 10],
                           [20, 15],
                           [15, 22]], dtype=np.float32)
    region_array = np.array([[0, 0],
                             [30, 30]], dtype=np.int32)

    results = fit_parabolic_peaks(data, region_array, peak_array)

    assert len(results) == 3
    for i, (fitted_height, fitted_pos, fitted_lw) in enumerate(results):
        expected = peaks[i]
        assert np.isclose(fitted_height, expected['height'], rtol=0.1)
        assert np.allclose(fitted_pos, expected['center'], atol=0.3)
```

### 3.4 Phase 2 Tests: Peak Finding

#### Test 2.1: Find Single Peak (2D)
```python
def test_find_single_peak_2d():
    """Test finding a single peak in 2D data."""
    shape = (20, 20)
    center = (10, 15)
    height = 100.0
    linewidth = (2.5, 3.0)

    data = generate_gaussian_peak(shape, center, height, linewidth, noise_level=1.0)

    # Search parameters
    have_low = False
    have_high = True
    low = 0.0
    high = 50.0  # Threshold
    buffer = [3, 3]  # 3-point exclusion buffer
    nonadjacent = True  # Check all neighbors
    drop_factor = 0.5
    min_linewidth = [1.5, 1.5]

    peaks = find_peaks(data, have_low, have_high, low, high,
                      buffer, nonadjacent, drop_factor, min_linewidth,
                      [], [], [])

    assert len(peaks) == 1
    peak_pos, peak_height = peaks[0]

    assert peak_height >= high
    assert np.allclose(peak_pos, center, atol=1)
```

#### Test 2.2: Find Multiple Peaks
```python
def test_find_multiple_peaks_2d():
    """Test finding multiple peaks in 2D data."""
    shape = (40, 40)
    peaks_spec = [
        {'center': (10, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
        {'center': (30, 10), 'height': 120, 'linewidth': (2.5, 2.5), 'model': 'gaussian'},
        {'center': (20, 30), 'height': 90, 'linewidth': (3, 3), 'model': 'gaussian'},
    ]

    data = generate_multi_peak_spectrum(shape, peaks_spec, noise_level=2.0)

    peaks = find_peaks(data, False, True, 0.0, 40.0,
                      [3, 3], True, 0.3, [1.5, 1.5],
                      [], [], [])

    assert len(peaks) == 3

    # Check all peaks found
    found_centers = [p[0] for p in peaks]
    expected_centers = [tuple(p['center']) for p in peaks_spec]

    for expected in expected_centers:
        assert any(np.allclose(found, expected, atol=2) for found in found_centers)
```

#### Test 2.3: Peak Finding with Buffer Exclusion
```python
def test_find_peaks_with_buffer():
    """Test that buffer prevents finding nearby peaks."""
    shape = (30, 30)
    # Two peaks very close together
    peaks_spec = [
        {'center': (15, 15), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
        {'center': (16, 16), 'height': 95, 'linewidth': (2, 2), 'model': 'gaussian'},
    ]

    data = generate_multi_peak_spectrum(shape, peaks_spec)

    # Small buffer: should find both
    peaks_small = find_peaks(data, False, True, 0.0, 40.0,
                            [1, 1], True, 0.0, [0, 0],
                            [], [], [])

    # Large buffer: should find only strongest
    peaks_large = find_peaks(data, False, True, 0.0, 40.0,
                            [5, 5], True, 0.0, [0, 0],
                            [], [], [])

    assert len(peaks_small) >= len(peaks_large)
    assert len(peaks_large) == 1  # Only strongest peak
```

#### Test 2.4: Drop Factor Filtering
```python
def test_find_peaks_drop_factor():
    """Test drop factor filtering."""
    shape = (30, 30)
    # Create peak with shoulder
    center = (15, 15)
    height = 100.0
    linewidth = (5, 5)  # Wide peak

    data = generate_gaussian_peak(shape, center, height, linewidth)

    # Add shoulder (local maximum but doesn't drop enough)
    data[10, 10] = 40.0
    data[11, 11] = 35.0
    data[9, 9] = 35.0

    # No drop factor: might find shoulder
    peaks_no_drop = find_peaks(data, False, True, 0.0, 20.0,
                              [2, 2], True, 0.0, [0, 0],
                              [], [], [])

    # High drop factor: should reject shoulder
    peaks_with_drop = find_peaks(data, False, True, 0.0, 20.0,
                                [2, 2], True, 0.5, [0, 0],
                                [], [], [])

    assert len(peaks_with_drop) <= len(peaks_no_drop)
    # Main peak should always be found
    assert any(np.allclose(p[0], center, atol=2) for p in peaks_with_drop)
```

#### Test 2.5: Linewidth Filtering
```python
def test_find_peaks_linewidth_filter():
    """Test minimum linewidth filtering."""
    shape = (30, 30)
    # Create narrow peak (noise spike) and wide peak (real signal)
    peaks_spec = [
        {'center': (10, 10), 'height': 50, 'linewidth': (0.8, 0.8), 'model': 'gaussian'},
        {'center': (20, 20), 'height': 100, 'linewidth': (3, 3), 'model': 'gaussian'},
    ]

    data = generate_multi_peak_spectrum(shape, peaks_spec)

    # No linewidth filter: find both
    peaks_all = find_peaks(data, False, True, 0.0, 20.0,
                          [2, 2], True, 0.0, [0, 0],
                          [], [], [])

    # Linewidth filter: reject narrow peak
    peaks_filtered = find_peaks(data, False, True, 0.0, 20.0,
                               [2, 2], True, 0.0, [2.0, 2.0],
                               [], [], [])

    assert len(peaks_filtered) < len(peaks_all)
    assert len(peaks_filtered) == 1
    # Should find only the wide peak
    assert peaks_filtered[0][1] == 100.0
```

#### Test 2.6: Excluded Regions
```python
def test_find_peaks_excluded_regions():
    """Test excluded region filtering."""
    shape = (40, 40)
    peaks_spec = [
        {'center': (10, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
        {'center': (30, 30), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
    ]

    data = generate_multi_peak_spectrum(shape, peaks_spec)

    # No exclusion: find both
    peaks_all = find_peaks(data, False, True, 0.0, 40.0,
                          [2, 2], True, 0.0, [0, 0],
                          [], [], [])

    # Exclude first peak region
    excluded = [np.array([[8, 8], [12, 12]], dtype=np.float32)]
    peaks_excluded = find_peaks(data, False, True, 0.0, 40.0,
                               [2, 2], True, 0.0, [0, 0],
                               excluded, [], [])

    assert len(peaks_all) == 2
    assert len(peaks_excluded) == 1
    # Should find only second peak
    assert np.allclose(peaks_excluded[0][0], (30, 30), atol=1)
```

#### Test 2.7: Diagonal Exclusion (Homonuclear)
```python
def test_find_peaks_diagonal_exclusion():
    """Test diagonal exclusion for homonuclear spectra."""
    shape = (40, 40)
    # Place peaks on and off diagonal
    peaks_spec = [
        {'center': (20, 20), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},  # On diagonal
        {'center': (10, 30), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},  # Off diagonal
    ]

    data = generate_multi_peak_spectrum(shape, peaks_spec)

    # No diagonal exclusion: find both
    peaks_all = find_peaks(data, False, True, 0.0, 40.0,
                          [2, 2], True, 0.0, [0, 0],
                          [], [], [])

    # Diagonal exclusion: exclude diagonal ± 3 points
    # Transform: a1*x - a2*y + b12 = 0, exclude if |delta| < d
    diagonal_dims = [np.array([0, 1], dtype=np.int32)]  # Dims 0 vs 1
    diagonal_transform = [np.array([1.0, 1.0, 0.0, 3.0], dtype=np.float32)]  # x - y, d=3

    peaks_excluded = find_peaks(data, False, True, 0.0, 40.0,
                               [2, 2], True, 0.0, [0, 0],
                               [], diagonal_dims, diagonal_transform)

    assert len(peaks_all) == 2
    assert len(peaks_excluded) == 1
    # Should find only off-diagonal peak
    assert np.allclose(peaks_excluded[0][0], (10, 30), atol=1)
```

#### Test 2.8: 3D Peak Finding
```python
def test_find_peaks_3d():
    """Test peak finding in 3D data."""
    shape = (20, 24, 28)
    peaks_spec = [
        {'center': (10, 12, 14), 'height': 100, 'linewidth': (2, 2.5, 3), 'model': 'gaussian'},
        {'center': (15, 18, 20), 'height': 120, 'linewidth': (2.5, 3, 3.5), 'model': 'gaussian'},
    ]

    data = generate_multi_peak_spectrum(shape, peaks_spec, noise_level=2.0)

    peaks = find_peaks(data, False, True, 0.0, 40.0,
                      [2, 2, 2], True, 0.3, [1.5, 1.5, 1.5],
                      [], [], [])

    assert len(peaks) == 2

    found_centers = [p[0] for p in peaks]
    for spec in peaks_spec:
        expected = tuple(spec['center'])
        assert any(np.allclose(found, expected, atol=2) for found in found_centers)
```

### 3.5 Phase 3 Tests: Levenberg-Marquardt Fitting

#### Test 3.1: Gauss-Jordan Matrix Solver
```python
def test_gauss_jordan_solve_simple():
    """Test Gauss-Jordan solver with simple system."""
    # Solve: 2x + y = 5
    #        x + 3y = 8
    # Solution: x = 1, y = 3

    matrix = np.array([[2.0, 1.0],
                       [1.0, 3.0]], dtype=np.float32)
    vector = np.array([5.0, 8.0], dtype=np.float32)

    solution, singular = gauss_jordan_solve(matrix, vector)

    assert not singular
    assert np.allclose(solution, [1.0, 3.0], atol=1e-5)
```

#### Test 3.2: Gauss-Jordan Singular Matrix
```python
def test_gauss_jordan_singular():
    """Test Gauss-Jordan detection of singular matrix."""
    # Singular matrix (rows are linearly dependent)
    matrix = np.array([[1.0, 2.0],
                       [2.0, 4.0]], dtype=np.float32)
    vector = np.array([3.0, 6.0], dtype=np.float32)

    solution, singular = gauss_jordan_solve(matrix, vector)

    assert singular
```

#### Test 3.3: Gaussian Model with Derivatives
```python
def test_gaussian_derivatives():
    """Test Gaussian model derivatives for Levenberg-Marquardt."""
    ndim = 2
    npeaks = 1
    x = np.array([10, 15], dtype=np.int32)

    # Parameters: [height, pos_x, pos_y, lw_x, lw_y]
    params = np.array([100.0, 10.5, 15.3, 2.5, 3.0], dtype=np.float32)

    y_fit, dy_dparams = gaussian_nd_with_derivatives(x, params, ndim, npeaks)

    # Check y_fit is reasonable
    assert y_fit > 0
    assert y_fit <= 100.0

    # Check derivatives by numerical differentiation
    epsilon = 1e-5
    for i in range(len(params)):
        params_plus = params.copy()
        params_plus[i] += epsilon
        y_plus, _ = gaussian_nd_with_derivatives(x, params_plus, ndim, npeaks)

        numerical_deriv = (y_plus - y_fit) / epsilon
        assert np.isclose(dy_dparams[i], numerical_deriv, rtol=0.01)
```

#### Test 3.4: Lorentzian Model with Derivatives
```python
def test_lorentzian_derivatives():
    """Test Lorentzian model derivatives."""
    ndim = 2
    npeaks = 1
    x = np.array([10, 15], dtype=np.int32)
    params = np.array([100.0, 10.5, 15.3, 2.5, 3.0], dtype=np.float32)

    y_fit, dy_dparams = lorentzian_nd_with_derivatives(x, params, ndim, npeaks)

    # Numerical derivative check
    epsilon = 1e-5
    for i in range(len(params)):
        params_plus = params.copy()
        params_plus[i] += epsilon
        y_plus, _ = lorentzian_nd_with_derivatives(x, params_plus, ndim, npeaks)

        numerical_deriv = (y_plus - y_fit) / epsilon
        assert np.isclose(dy_dparams[i], numerical_deriv, rtol=0.01)
```

#### Test 3.5: Levenberg-Marquardt Single Peak (Gaussian)
```python
def test_levenberg_marquardt_gaussian_2d():
    """Test Levenberg-Marquardt fitting of single Gaussian peak."""
    # Generate perfect Gaussian peak
    shape = (30, 30)
    true_center = (15.3, 20.7)
    true_height = 100.0
    true_linewidth = (2.5, 3.0)

    data = generate_gaussian_peak(shape, true_center, true_height, true_linewidth)

    # Initial guess (slightly off)
    initial_params = np.array([
        90.0,      # height (off by 10%)
        15.0, 21.0, # position (off by 0.3)
        2.0, 2.5   # linewidth (off)
    ], dtype=np.float32)

    # Fit region
    region = np.array([[12, 18], [18, 24]], dtype=np.int32)

    # Extract region data
    x_data, y_data = extract_region_data(data, region)

    # Run Levenberg-Marquardt
    fitted_params, param_dev, chisq = nonlinear_fit(
        x_data, y_data, None, initial_params,
        model_func=gaussian_model_func,
        max_iter=20
    )

    # Check convergence
    assert chisq < 1.0  # Good fit

    # Check parameters
    fitted_height = fitted_params[0]
    fitted_center = fitted_params[1:3]
    fitted_lw = fitted_params[3:5]

    assert np.isclose(fitted_height, true_height, rtol=0.01)
    assert np.allclose(fitted_center, true_center, atol=0.05)
    assert np.allclose(fitted_lw, true_linewidth, rtol=0.05)
```

#### Test 3.6: Levenberg-Marquardt Single Peak (Lorentzian)
```python
def test_levenberg_marquardt_lorentzian_2d():
    """Test Levenberg-Marquardt fitting of Lorentzian peak."""
    shape = (30, 30)
    true_center = (15.3, 20.7)
    true_height = 100.0
    true_linewidth = (2.5, 3.0)

    data = generate_lorentzian_peak(shape, true_center, true_height, true_linewidth)

    initial_params = np.array([90.0, 15.0, 21.0, 2.0, 2.5], dtype=np.float32)
    region = np.array([[12, 18], [18, 24]], dtype=np.int32)

    x_data, y_data = extract_region_data(data, region)

    fitted_params, param_dev, chisq = nonlinear_fit(
        x_data, y_data, None, initial_params,
        model_func=lorentzian_model_func,
        max_iter=20
    )

    assert chisq < 1.0
    assert np.isclose(fitted_params[0], true_height, rtol=0.01)
    assert np.allclose(fitted_params[1:3], true_center, atol=0.05)
    assert np.allclose(fitted_params[3:5], true_linewidth, rtol=0.05)
```

#### Test 3.7: Levenberg-Marquardt with Noise
```python
def test_levenberg_marquardt_noisy_data():
    """Test fitting with realistic noise."""
    shape = (30, 30)
    true_center = (15, 20)
    true_height = 100.0
    true_linewidth = (2.5, 3.0)
    noise_level = 5.0  # 5% noise

    data = generate_gaussian_peak(shape, true_center, true_height, true_linewidth, noise_level)

    initial_params = np.array([95.0, 15.0, 20.0, 2.0, 2.5], dtype=np.float32)
    region = np.array([[12, 18], [18, 23]], dtype=np.int32)

    x_data, y_data = extract_region_data(data, region)

    fitted_params, param_dev, chisq = nonlinear_fit(
        x_data, y_data, None, initial_params,
        model_func=gaussian_model_func,
        max_iter=20,
        noise_estimate=noise_level
    )

    # Should still converge, but with larger uncertainties
    assert chisq < 5.0
    assert np.isclose(fitted_params[0], true_height, rtol=0.1)
    assert np.allclose(fitted_params[1:3], true_center, atol=0.2)

    # Check uncertainties are reasonable
    assert all(param_dev > 0)
    assert all(param_dev < 10.0)
```

#### Test 3.8: Levenberg-Marquardt Multiple Peaks
```python
def test_levenberg_marquardt_multiple_peaks():
    """Test simultaneous fitting of multiple overlapping peaks."""
    shape = (40, 40)
    peaks_spec = [
        {'center': (15, 15), 'height': 100, 'linewidth': (2.5, 2.5), 'model': 'gaussian'},
        {'center': (20, 20), 'height': 80, 'linewidth': (3, 3), 'model': 'gaussian'},
    ]

    data = generate_multi_peak_spectrum(shape, peaks_spec)

    # Initial parameters: [h1, p1x, p1y, lw1x, lw1y, h2, p2x, p2y, lw2x, lw2y]
    initial_params = np.array([
        90.0, 15.0, 15.0, 2.0, 2.0,
        70.0, 20.0, 20.0, 2.5, 2.5
    ], dtype=np.float32)

    region = np.array([[10, 10], [25, 25]], dtype=np.int32)
    x_data, y_data = extract_region_data(data, region)

    fitted_params, param_dev, chisq = nonlinear_fit(
        x_data, y_data, None, initial_params,
        model_func=gaussian_model_func_multi,
        max_iter=30
    )

    # Extract fitted parameters for each peak
    fitted_peak1 = fitted_params[0:5]
    fitted_peak2 = fitted_params[5:10]

    # Check both peaks fitted correctly
    assert np.isclose(fitted_peak1[0], 100, rtol=0.1)
    assert np.allclose(fitted_peak1[1:3], (15, 15), atol=0.2)

    assert np.isclose(fitted_peak2[0], 80, rtol=0.1)
    assert np.allclose(fitted_peak2[1:3], (20, 20), atol=0.2)
```

#### Test 3.9: Full fitPeaks API (Gaussian)
```python
def test_fit_peaks_api_gaussian():
    """Test complete fitPeaks API with Gaussian method."""
    shape = (30, 30)
    center = (15.3, 20.7)
    height = 100.0
    linewidth = (2.5, 3.0)

    data = generate_gaussian_peak(shape, center, height, linewidth)

    region_array = np.array([[12, 18], [18, 24]], dtype=np.int32)
    peak_array = np.array([[15.0, 21.0]], dtype=np.float32)
    method = 0  # Gaussian

    results = fit_peaks(data, region_array, peak_array, method)

    assert len(results) == 1
    fitted_height, fitted_pos, fitted_lw = results[0]

    assert np.isclose(fitted_height, height, rtol=0.01)
    assert np.allclose(fitted_pos, center, atol=0.05)
    assert np.allclose(fitted_lw, linewidth, rtol=0.05)
```

#### Test 3.10: Full fitPeaks API (Lorentzian)
```python
def test_fit_peaks_api_lorentzian():
    """Test complete fitPeaks API with Lorentzian method."""
    shape = (30, 30)
    center = (15.3, 20.7)
    height = 100.0
    linewidth = (2.5, 3.0)

    data = generate_lorentzian_peak(shape, center, height, linewidth)

    region_array = np.array([[12, 18], [18, 24]], dtype=np.int32)
    peak_array = np.array([[15.0, 21.0]], dtype=np.float32)
    method = 1  # Lorentzian

    results = fit_peaks(data, region_array, peak_array, method)

    assert len(results) == 1
    fitted_height, fitted_pos, fitted_lw = results[0]

    assert np.isclose(fitted_height, height, rtol=0.01)
    assert np.allclose(fitted_pos, center, atol=0.05)
    assert np.allclose(fitted_lw, linewidth, rtol=0.05)
```

#### Test 3.11: 3D Peak Fitting
```python
def test_fit_peaks_3d_gaussian():
    """Test 3D Gaussian peak fitting."""
    shape = (20, 24, 28)
    center = (10.3, 12.5, 14.7)
    height = 200.0
    linewidth = (2.0, 2.5, 3.0)

    data = generate_gaussian_peak(shape, center, height, linewidth)

    region_array = np.array([[8, 10, 12],
                             [13, 15, 17]], dtype=np.int32)
    peak_array = np.array([[10.0, 12.0, 15.0]], dtype=np.float32)
    method = 0

    results = fit_peaks(data, region_array, peak_array, method)

    assert len(results) == 1
    fitted_height, fitted_pos, fitted_lw = results[0]

    assert np.isclose(fitted_height, height, rtol=0.02)
    assert np.allclose(fitted_pos, center, atol=0.1)
    assert np.allclose(fitted_lw, linewidth, rtol=0.1)
```

### 3.6 Cross-Validation Tests (C vs Python)

```python
def test_c_vs_python_find_peaks():
    """Cross-validate findPeaks: C vs Python implementation."""
    try:
        from ccpnc import Peak as CPeak
    except ImportError:
        pytest.skip("C extension not available")

    from ccpn.c_replacement.peak_numba import find_peaks as python_find_peaks

    # Generate test data
    shape = (40, 40)
    peaks_spec = [
        {'center': (10, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
        {'center': (30, 30), 'height': 120, 'linewidth': (2.5, 2.5), 'model': 'gaussian'},
    ]
    data = generate_multi_peak_spectrum(shape, peaks_spec, noise_level=2.0)

    # Common parameters
    args = (data, False, True, 0.0, 40.0, [3, 3], True, 0.3, [1.5, 1.5], [], [], [])

    # Run both implementations
    peaks_c = CPeak.findPeaks(*args)
    peaks_python = python_find_peaks(*args)

    # Should find same number of peaks
    assert len(peaks_c) == len(peaks_python)

    # Should find same positions (order may differ)
    c_positions = sorted([p[0] for p in peaks_c])
    python_positions = sorted([p[0] for p in peaks_python])

    for c_pos, py_pos in zip(c_positions, python_positions):
        assert np.allclose(c_pos, py_pos, atol=1)

def test_c_vs_python_fit_parabolic():
    """Cross-validate fitParabolicPeaks: C vs Python."""
    try:
        from ccpnc import Peak as CPeak
    except ImportError:
        pytest.skip("C extension not available")

    from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

    shape = (30, 30)
    center = (15.3, 20.7)
    height = 100.0
    linewidth = (2.5, 3.0)

    data = generate_gaussian_peak(shape, center, height, linewidth)

    region_array = np.array([[12, 18], [18, 24]], dtype=np.int32)
    peak_array = np.array([[15.0, 21.0]], dtype=np.float32)

    result_c = CPeak.fitParabolicPeaks(data, region_array, peak_array)
    result_python = fit_parabolic_peaks(data, region_array, peak_array)

    assert len(result_c) == len(result_python)

    for c_res, py_res in zip(result_c, result_python):
        assert np.isclose(c_res[0], py_res[0], rtol=0.01)  # height
        assert np.allclose(c_res[1], py_res[1], atol=0.01)  # position
        assert np.allclose(c_res[2], py_res[2], rtol=0.05)  # linewidth

def test_c_vs_python_fit_peaks_gaussian():
    """Cross-validate fitPeaks (Gaussian): C vs Python."""
    try:
        from ccpnc import Peak as CPeak
    except ImportError:
        pytest.skip("C extension not available")

    from ccpn.c_replacement.peak_numba import fit_peaks

    shape = (30, 30)
    center = (15.3, 20.7)
    height = 100.0
    linewidth = (2.5, 3.0)

    data = generate_gaussian_peak(shape, center, height, linewidth)

    region_array = np.array([[12, 18], [18, 24]], dtype=np.int32)
    peak_array = np.array([[15.0, 21.0]], dtype=np.float32)
    method = 0

    result_c = CPeak.fitPeaks(data, region_array, peak_array, method)
    result_python = fit_peaks(data, region_array, peak_array, method)

    # Nonlinear fitting may give slightly different results
    # Check they're close
    assert len(result_c) == len(result_python)

    c_height, c_pos, c_lw = result_c[0]
    py_height, py_pos, py_lw = result_python[0]

    assert np.isclose(c_height, py_height, rtol=0.02)
    assert np.allclose(c_pos, py_pos, atol=0.1)
    assert np.allclose(c_lw, py_lw, rtol=0.1)
```

---

## 4. Performance Targets

Based on contour module experience:

### 4.1 Acceptable Performance Ranges

| Function | Target Speed | Acceptance Criteria |
|----------|-------------|---------------------|
| `findPeaks` | 0.5-2x C speed | Peak finding is typically fast; 2x slower acceptable |
| `fitParabolicPeaks` | 0.8-1.5x C speed | Simple analytical calculation; should be close to C |
| `fitPeaks` (Gaussian) | 0.3-1.0x C speed | Iterative fitting; inherently slower acceptable |
| `fitPeaks` (Lorentzian) | 0.3-1.0x C speed | Same as Gaussian |

### 4.2 Benchmark Test Cases

```python
def benchmark_find_peaks_2d():
    """Benchmark findPeaks on 2D spectrum."""
    shape = (512, 512)
    peaks_spec = [
        {'center': (100, 100), 'height': 1000, 'linewidth': (5, 5), 'model': 'gaussian'},
        {'center': (300, 200), 'height': 800, 'linewidth': (4, 6), 'model': 'gaussian'},
        {'center': (400, 450), 'height': 1200, 'linewidth': (6, 4), 'model': 'gaussian'},
    ]
    data = generate_multi_peak_spectrum(shape, peaks_spec, noise_level=10.0)

    # Benchmark parameters
    args = (data, False, True, 0.0, 200.0, [10, 10], True, 0.5, [3, 3], [], [], [])

    # Time C implementation
    try:
        from ccpnc import Peak as CPeak
        time_c = timeit.timeit(lambda: CPeak.findPeaks(*args), number=10) / 10
    except ImportError:
        time_c = None

    # Time Python implementation
    from ccpn.c_replacement.peak_numba import find_peaks
    time_python = timeit.timeit(lambda: find_peaks(*args), number=10) / 10

    print(f"findPeaks (512x512):")
    if time_c:
        print(f"  C:      {time_c:.4f}s")
        print(f"  Python: {time_python:.4f}s")
        print(f"  Ratio:  {time_python/time_c:.2f}x")
    else:
        print(f"  Python: {time_python:.4f}s")

def benchmark_fit_peaks_3d():
    """Benchmark fitPeaks on 3D spectrum."""
    shape = (64, 64, 64)
    center = (32.3, 32.7, 32.5)
    height = 1000.0
    linewidth = (4.0, 4.5, 5.0)

    data = generate_gaussian_peak(shape, center, height, linewidth, noise_level=20.0)

    region_array = np.array([[28, 28, 28], [37, 37, 37]], dtype=np.int32)
    peak_array = np.array([[32.0, 33.0, 32.0]], dtype=np.float32)
    method = 0

    # Time implementations
    try:
        from ccpnc import Peak as CPeak
        time_c = timeit.timeit(
            lambda: CPeak.fitPeaks(data, region_array, peak_array, method),
            number=10
        ) / 10
    except ImportError:
        time_c = None

    from ccpn.c_replacement.peak_numba import fit_peaks
    time_python = timeit.timeit(
        lambda: fit_peaks(data, region_array, peak_array, method),
        number=10
    ) / 10

    print(f"fitPeaks (64x64x64, Gaussian):")
    if time_c:
        print(f"  C:      {time_c:.4f}s")
        print(f"  Python: {time_python:.4f}s")
        print(f"  Ratio:  {time_python/time_c:.2f}x")
    else:
        print(f"  Python: {time_python:.4f}s")
```

---

## 5. Integration Plan

### 5.1 Compatibility Wrapper Integration

```python
# Update: src/python/ccpn/core/lib/PeakListLib.py
# Change line 166:

# OLD:
from ccpnc import Peak as CPeak
peakPoints = CPeak.findPeaks(...)

# NEW:
from ccpn.c_replacement.peak_compat import PeakFinder
peakPoints = PeakFinder.findPeaks(...)
```

### 5.2 Testing Integration

1. Run existing C-based tests with Python implementation
2. Verify all 31 usage locations work correctly
3. Run full application test suite
4. Monitor for regressions

### 5.3 Production Deployment

Following contour module strategy:

1. **Week 1-2**: Deploy to beta testers
2. **Week 3-4**: Monitor performance and errors
3. **Week 5**: Full production if stable

---

## 6. Risk Assessment

### 6.1 High Risk Areas

1. **Levenberg-Marquardt Convergence**
   - **Risk**: Python implementation may have different convergence behavior
   - **Mitigation**: Extensive cross-validation with C implementation
   - **Fallback**: Keep C version available for critical cases

2. **Numerical Stability**
   - **Risk**: Matrix operations in Gauss-Jordan may be numerically unstable
   - **Mitigation**: Use NumPy's stable linear algebra routines where possible
   - **Fallback**: Add condition number checks

3. **Performance on Large 3D Spectra**
   - **Risk**: 3D peak fitting may be too slow in Python
   - **Mitigation**: Profile and optimize critical loops with Numba
   - **Fallback**: Use C version for 3D fitting if necessary

### 6.2 Medium Risk Areas

1. **Edge Cases in Peak Finding**
   - Peaks at array boundaries
   - Overlapping peaks
   - Very noisy data

2. **Multi-peak Fitting**
   - Initial guess quality
   - Convergence with many peaks

### 6.3 Low Risk Areas

1. **Parabolic Fitting** - Simple analytical calculation
2. **API Compatibility** - Straightforward wrapper
3. **2D Peak Finding** - Well-tested algorithm

---

## 7. Success Criteria

### 7.1 Functional Requirements

- [ ] All 38 test cases pass (100% coverage)
- [ ] Cross-validation with C: <1% difference in results
- [ ] All 31 usage locations work without modification
- [ ] No regressions in existing application tests

### 7.2 Performance Requirements

- [ ] `findPeaks`: <2x slower than C
- [ ] `fitParabolicPeaks`: <1.5x slower than C
- [ ] `fitPeaks`: <3x slower than C (acceptable for iterative fitting)
- [ ] Memory usage: <1.5x C implementation

### 7.3 Quality Requirements

- [ ] No compiler/build dependencies
- [ ] Cross-platform (macOS, Linux, Windows)
- [ ] Automatic fallback to C if available
- [ ] Clear error messages
- [ ] Comprehensive documentation

---

## 8. Timeline Estimate

### 8.1 Development Phases

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| **Phase 1: Parabolic** | Tests (10) + Implementation | 2-3 days |
| **Phase 2: Peak Finding** | Tests (8) + Implementation | 3-4 days |
| **Phase 3: L-M Fitting** | Tests (11) + Implementation | 5-7 days |
| **Cross-validation** | C vs Python tests (3) | 1-2 days |
| **Integration** | Update 31 locations, test | 1-2 days |
| **Documentation** | API docs, examples | 1 day |
| **Total** | | **13-19 days** |

### 8.2 Phased Rollout

Unlike contour module (immediate cutover), Peak module should be gradual:

1. **Phase 1-2 Only**: Deploy parabolic + finding (lower risk)
2. **Monitor for 1 week**
3. **Phase 3**: Deploy Levenberg-Marquardt fitting
4. **Monitor for 2 weeks**
5. **Full cutover** if stable

---

## 9. Open Questions

1. **Should we use SciPy for Levenberg-Marquardt?**
   - Pro: Battle-tested, optimized
   - Con: External dependency, less control
   - **Recommendation**: Start with custom implementation, benchmark against SciPy

2. **Should we implement Gauss-Jordan or use NumPy's `linalg.solve`?**
   - Pro (Gauss-Jordan): Exact C behavior, educational
   - Pro (NumPy): More stable, faster
   - **Recommendation**: Use NumPy but validate against C

3. **How to handle convergence failures?**
   - C returns error message
   - Should Python raise exception or return None?
   - **Recommendation**: Raise exception with clear message

4. **Should we support weighted fitting?**
   - C implementation accepts weights but rarely used
   - **Recommendation**: Implement but don't prioritize testing

---

## 10. Next Steps

1. **Set up branch**: `feature/peak-module-tdd`
2. **Create test infrastructure**: `tests/test_peak_*.py`
3. **Implement Phase 1**: Parabolic fitting (lowest risk)
4. **Validate Phase 1** before proceeding
5. **Iterate through phases** with continuous validation

**Ready to begin?** ✓
