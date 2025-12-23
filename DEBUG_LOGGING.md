# Debug Logging for CCPN Python Implementation

The Python implementations of the contour and peak modules now include comprehensive debug logging to help monitor performance and behavior during GUI testing.

## Quick Start

Enable debug logging by setting the `CCPN_DEBUG` environment variable:

```bash
# Enable debug logging
export CCPN_DEBUG=1

# Run the GUI
./bin/analysisassign
```

## What Gets Logged

### Implementation Selection (INFO level)

When modules are imported, you'll see which implementation was selected:

```
[CCPN Contour] Auto-selected: Pure Python (Numba JIT) (C extension not available)
[CCPN Peak] Auto-selected: C extension
```

### Runtime Switching (INFO level)

When you switch implementations at runtime:

```python
import ccpn.c_replacement.contour_compat as contour_compat
contour_compat.use_python_implementation()
```

Output:
```
[CCPN Contour] Switched to Pure Python (Numba JIT) [RUNTIME SWITCH]
```

### Debug Details (DEBUG level, requires CCPN_DEBUG=1)

With `CCPN_DEBUG=1`, you'll see detailed operation logs:

#### Contour Generation

```
[CCPN Contour] contourerGLList called: 1 arrays, 5 pos levels, 5 neg levels, implementation=Pure Python (Numba JIT)
[CCPN Contour] calculate_contours: data shape=(512, 512), 5 levels
[CCPN Contour]   Level 1/5 (value=0.100): 1234 vertices → 23 polylines (0.0045s)
[CCPN Contour]   Level 2/5 (value=0.300): 856 vertices → 18 polylines (0.0032s)
[CCPN Contour]   Level 3/5 (value=0.500): 542 vertices → 12 polylines (0.0021s)
[CCPN Contour]   Level 4/5 (value=0.700): 312 vertices → 8 polylines (0.0015s)
[CCPN Contour]   Level 5/5 (value=0.900): 98 vertices → 3 polylines (0.0008s)
[CCPN Contour] calculate_contours complete: 5 levels processed
[CCPN Contour] Contour generation complete: 3042 vertices, 6084 indices, 0.0121s
```

#### Peak Finding

```
[CCPN Peak] findPeaks: data shape=(512, 512), thresholds=[0.000, 3.000], implementation=Pure Python (Numba JIT)
[CCPN Peak] find_peaks: data shape=(512, 512), thresholds=[0.000, 3.000], nonadjacent=True
[CCPN Peak] find_peaks complete: 42 peaks found
[CCPN Peak] findPeaks complete: 42 peaks found (0.1234s)
```

#### Peak Fitting

```
[CCPN Peak] fitParabolicPeaks: data shape=(512, 512), 42 peaks, implementation=Pure Python (Numba JIT)
[CCPN Peak] fitParabolicPeaks complete: 42 peaks fitted (0.0089s)
```

## Environment Variables

### CCPN_DEBUG
- **Values**: `0` (default) or `1`
- **Effect**: Enables detailed DEBUG-level logging
- **Use Case**: Troubleshooting performance, monitoring operations

```bash
export CCPN_DEBUG=1
```

### CCPN_QUIET
- **Values**: `0` (default) or `1`
- **Effect**: Suppresses all console output (stderr)
- **Use Case**: Production environments where you don't want startup messages

```bash
export CCPN_QUIET=1
```

### CCPN_FORCE_PYTHON
- **Values**: `0` (default) or `1`
- **Effect**: Forces use of Python implementation
- **Use Case**: Testing Python implementation, debugging

```bash
export CCPN_FORCE_PYTHON=1
```

### CCPN_FORCE_C
- **Values**: `0` (default) or `1`
- **Effect**: Forces use of C extension (errors if not available)
- **Use Case**: Production environments where C is required

```bash
export CCPN_FORCE_C=1
```

## Usage Examples

### Example 1: Testing Python Performance in GUI

```bash
# Force Python implementation and enable debug logging
export CCPN_FORCE_PYTHON=1
export CCPN_DEBUG=1

# Launch GUI
./bin/analysisassign

# You'll see debug output in the terminal as you:
# - Load spectra (contour generation logs)
# - Pick peaks (peak finding/fitting logs)
# - Zoom/pan (contour regeneration logs)
```

### Example 2: Comparing C vs Python Performance

Terminal 1 (C extension):
```bash
export CCPN_FORCE_C=1
export CCPN_DEBUG=1
./bin/analysisassign
```

Terminal 2 (Python):
```bash
export CCPN_FORCE_PYTHON=1
export CCPN_DEBUG=1
./bin/analysisassign
```

Load the same spectrum in both and compare the timing logs.

### Example 3: Runtime Switching with Logging

```python
import os
os.environ['CCPN_DEBUG'] = '1'

import ccpn.c_replacement.contour_compat as contour_compat
import ccpn.c_replacement.peak_compat as peak_compat
import numpy as np

# Check what's available
print("Contour implementations:", contour_compat.get_available_implementations())
print("Peak implementations:", peak_compat.get_available_implementations())

# Generate test data
data = np.random.randn(512, 512).astype(np.float32)
levels = np.array([0.1, 0.3, 0.5, 0.7, 0.9], dtype=np.float32)

# Test with C (if available)
try:
    contour_compat.use_c_implementation()
    result_c = contour_compat.Contourer2d.contourerGLList(
        (data,), levels, np.array([], dtype=np.float32),
        np.array([1, 0, 0, 1], dtype=np.float32),
        np.array([0, 0, 1, 1], dtype=np.float32)
    )
except RuntimeError:
    print("C extension not available")

# Test with Python
contour_compat.use_python_implementation()
result_py = contour_compat.Contourer2d.contourerGLList(
    (data,), levels, np.array([], dtype=np.float32),
    np.array([1, 0, 0, 1], dtype=np.float32),
    np.array([0, 0, 1, 1], dtype=np.float32)
)
```

Expected output:
```
[CCPN Contour] Auto-selected: C extension
Contour implementations: {'c_available': True, 'python_available': True, 'current': 'C extension', 'using_c': True}
Peak implementations: {'c_available': True, 'python_available': True, 'current': 'C extension', 'using_c': True}
[CCPN Contour] contourerGLList called: 1 arrays, 5 pos levels, 0 neg levels, implementation=C extension
[CCPN Contour] Contour generation complete: 3042 vertices, 6084 indices, 0.0008s
[CCPN Contour] Switched to Pure Python (Numba JIT) [RUNTIME SWITCH]
[CCPN Contour] contourerGLList called: 1 arrays, 5 pos levels, 0 neg levels, implementation=Pure Python (Numba JIT) [RUNTIME SWITCH]
[CCPN Contour] calculate_contours: data shape=(512, 512), 5 levels
[CCPN Contour]   Level 1/5 (value=0.100): 1234 vertices → 23 polylines (0.0045s)
...
[CCPN Contour] Contour generation complete: 3042 vertices, 6084 indices, 0.0121s
```

## Log Levels

The logging system uses Python's standard `logging` module:

- **INFO**: Implementation selection, switching events
- **DEBUG**: Detailed operation logs (requires `CCPN_DEBUG=1`)

## Performance Impact

- **INFO logging**: Minimal overhead (~1-2 µs per call)
- **DEBUG logging**: Small overhead (~50-100 µs per operation for timing measurements)
- **Recommendation**: Use DEBUG logging only during development/testing, not in production

## Troubleshooting

### No debug output appears

Check that `CCPN_DEBUG=1` is set:
```bash
echo $CCPN_DEBUG  # Should print: 1
```

### Too much output

Disable debug mode but keep INFO messages:
```bash
export CCPN_DEBUG=0  # or unset CCPN_DEBUG
```

### Suppress all logging

Use the quiet mode:
```bash
export CCPN_QUIET=1
```

## Log File Redirection

To save logs to a file:

```bash
export CCPN_DEBUG=1
./bin/analysisassign 2>&1 | tee ccpn_debug.log
```

This captures both stdout and stderr to `ccpn_debug.log` while still displaying in the terminal.

## Integration with GUI Testing

When testing the GUI, the debug logs help you:

1. **Verify implementation**: See which implementation is being used
2. **Monitor performance**: Track timing for each operation
3. **Debug issues**: See exactly what data is being processed
4. **Compare implementations**: Run side-by-side tests with different implementations

Example workflow:
```bash
# Start with debug logging
export CCPN_DEBUG=1
export CCPN_FORCE_PYTHON=1

# Launch GUI
./bin/analysisassign

# In the GUI:
# 1. Load a spectrum → See contour generation logs
# 2. Change contour levels → See regeneration logs
# 3. Pick peaks → See peak finding logs
# 4. Fit peaks → See peak fitting logs

# All operations logged with timing information!
```
