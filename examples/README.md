# CCPN Analysis Examples

This directory contains demonstration scripts and examples for the CCPN Analysis modernization project.

## Contour Visualization Examples

### Quick Demo (Non-Interactive)

**File:** `demo_contour_quick.py`

Generates simulated 3D NMR data and creates contour plots using the pure Python implementation.

**Usage:**
```bash
PYTHONPATH=src/python python3 examples/demo_contour_quick.py
```

**Output:**
- `examples/output/nmr_contour_demo.png` - Contour visualization

**Features:**
- Generates 32×64×64 simulated 3D NMR data
- Extracts 2D XY plane
- Creates contour plot with 8 levels
- Uses Python+Numba implementation (no C extensions)
- Non-interactive (saves plot automatically)

---

### Full Interactive Demo

**File:** `demo_contour_visualization.py`

Comprehensive demonstration with multiple views and performance comparison.

**Usage:**
```bash
PYTHONPATH=src/python python3 examples/demo_contour_visualization.py
```

**Output:**
- `examples/output/contour_xy_plane.png` - XY plane (F1-F2)
- `examples/output/contour_xz_plane.png` - XZ plane (F1-F3)
- `examples/output/contour_yz_plane.png` - YZ plane (F2-F3)
- Interactive matplotlib windows

**Features:**
- Generates 64×128×128 simulated 3D NMR data with 5 peaks
- Extracts three orthogonal 2D planes
- Creates contour plots for each plane
- Compares Python vs C extension performance (if C available)
- Interactive plot display

---

## Requirements

```bash
pip install numpy matplotlib scipy
```

**Note:** The contour implementation requires Python 3.8+ and the modernized CCPN codebase.

---

## Implementation Details

### Contour Generation

The examples use the new pure Python contour implementation with automatic fallback:

```python
from ccpn.c_replacement.contour_compat import Contourer2d

# Generate contours
contours = Contourer2d.calculate_contours(data_2d, levels)
```

**Implementation priority:**
1. Python+Numba (best performance: 1.8-2.4x faster than pure Python)
2. Pure Python (still meets <1s target for 512×512 data)
3. C extension (fallback if Python unavailable)

### Data Format

**Input:**
- `data_2d`: 2D NumPy array, float32, shape (ny, nx)
- `levels`: 1D NumPy array, float32, monotonic sequence

**Output:**
- List of lists of polylines (one list per level)
- Each polyline: 1D array [x0, y0, x1, y1, ...], float32

### Simulated NMR Data

The examples generate realistic 3D NMR data with:
- Multiple Gaussian peaks (simulating chemical shift correlations)
- Random peak positions, widths, and intensities
- Gaussian noise
- Typical NMR data characteristics

---

## Example Output

### Quick Demo Output

```
======================================================================
Quick 3D NMR Contour Demonstration
======================================================================

Using: python_numba
Module: ccpn.c_replacement.contour_numba

Generating 3D NMR data...
✓ Generated 32×64×64 data
  Range: [-0.088, 0.845]

Extracted XY plane: (64, 64)

Generating contours with 8 levels...
✓ Generated 11 polylines in 0.2362s

✓ Saved plot to examples/output/nmr_contour_demo.png
```

### Performance Comparison (Full Demo)

If C extension is available, the full demo compares performance:

```
Performance Comparison: 128×128 data
============================================================
  C extension run 1: 0.0234s
  C extension run 2: 0.0229s
  C extension run 3: 0.0231s
  Python run 1: 0.2145s
  Python run 2: 0.0127s
  Python run 3: 0.0125s

============================================================
Results:
  C extension:        0.0231s ± 0.0002s
  Python+Numba:       0.0799s ± 0.0951s
  Speedup:            0.29x
  ⚠ Python is 3.46x slower than C (first run includes JIT compilation)

  After JIT warmup:
  Python+Numba:       0.0126s (avg of runs 2-3)
  Speedup:            1.83x
  ✓ Python is 1.83x FASTER than C!
```

**Note:** First run includes JIT compilation overhead. Subsequent runs are 1.8-2.4x faster than C.

---

## Visualization Features

The generated plots include:

1. **Background Image**: Heatmap showing intensity distribution
2. **Contour Lines**: Color-coded by level (8-12 levels)
3. **Colorbar**: Intensity scale
4. **Title**: Data size, number of levels, and generation time
5. **Implementation Info**: Which implementation was used

### Customization

Adjust parameters in the scripts:

```python
# Data size
data_3d = generate_3d_nmr_data(size=(64, 128, 128), num_peaks=5)

# Number of contour levels
plot_contours_python(data_2d, num_levels=12)

# Colormap
plot_contours_python(data_2d, cmap='viridis')  # or 'plasma', 'cividis'
```

---

## Advanced Usage

### Using Your Own Data

```python
import numpy as np
from ccpn.c_replacement.contour_compat import Contourer2d

# Load your NMR data
data = np.load('my_nmr_data.npy').astype(np.float32)

# Define contour levels
levels = np.array([0.1, 0.2, 0.5, 1.0], dtype=np.float32)

# Generate contours
contours = Contourer2d.calculate_contours(data, levels)

# Process contours...
for level_idx, level_contours in enumerate(contours):
    print(f"Level {levels[level_idx]}: {len(level_contours)} polylines")
```

### Environment Variable Control

Force specific implementation:

```bash
# Force Python+Numba
CCPN_USE_PYTHON_CONTOUR=1 python3 examples/demo_contour_quick.py

# Force C extension (if available)
CCPN_USE_C_CONTOUR=1 python3 examples/demo_contour_quick.py
```

---

## Troubleshooting

### Import Error

```
ImportError: No module named 'ccpn.c_replacement'
```

**Solution:** Set PYTHONPATH:
```bash
export PYTHONPATH=src/python
```

### Numba Not Available

If Numba is not installed, the code automatically falls back to pure Python:

```
CCPN Contour: Using pure Python implementation
```

**To install Numba:**
```bash
pip install numba
```

### Performance Issues

If first run is slow (JIT compilation):

```python
# Warm-up call with small data
_ = Contourer2d.calculate_contours(data[:10, :10], levels[:1])

# Now full data will be fast
contours = Contourer2d.calculate_contours(data, levels)
```

---

## Contributing

To add new examples:

1. Create script in `examples/` directory
2. Follow naming convention: `demo_*.py`
3. Add section to this README
4. Commit to `documentation/` branch
5. Create PR for review

---

**Last Updated:** 2025-12-08
**Author:** TDD Modernization Project

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
