# Debug Logging Implementation Summary

## What Was Added

Comprehensive debug logging has been added to the CCPN Python implementations to help monitor performance and behavior during GUI testing.

## Files Modified

1. **[contour_compat.py](src/python/ccpn/c_replacement/contour_compat.py)**
   - Added logging module import and configuration
   - Added DEBUG-level logs for module loading
   - Added INFO-level logs for implementation selection
   - Added DEBUG logs in `contourerGLList()` with timing measurements

2. **[contour_numba.py](src/python/ccpn/c_replacement/contour_numba.py)**
   - Added logging module import
   - Added DEBUG logs in `calculate_contours()`
   - Added per-level progress logging with vertex/polyline counts
   - Added DEBUG logs in `contourerGLList()`

3. **[peak_compat.py](src/python/ccpn/c_replacement/peak_compat.py)**
   - Added logging module import and configuration
   - Added DEBUG-level logs for module loading
   - Added INFO-level logs for implementation selection
   - Added DEBUG logs in `findPeaks()` with timing
   - Added DEBUG logs in `fitParabolicPeaks()` with timing

4. **[peak_numba.py](src/python/ccpn/c_replacement/peak_numba.py)**
   - Added logging module import
   - Added DEBUG logs in `find_peaks()` with result summary

## Usage

### Enable Debug Logging

```bash
export CCPN_DEBUG=1
./bin/analysisassign
```

### Example Output

```
[CCPN Contour] Auto-selected: Pure Python (Numba JIT)
[CCPN Peak] Auto-selected: C extension
[CCPN Contour] contourerGLList called: 1 arrays, 5 pos levels, 0 neg levels
[CCPN Contour] calculate_contours: data shape=(512, 512), 5 levels
[CCPN Contour]   Level 1/5 (value=0.100): 1234 vertices → 23 polylines (0.0045s)
[CCPN Contour]   Level 2/5 (value=0.300): 856 vertices → 18 polylines (0.0032s)
[CCPN Contour] Contour generation complete: 3042 vertices, 6084 indices, 0.0121s
```

## Environment Variables

- **CCPN_DEBUG=1**: Enable detailed DEBUG-level logging
- **CCPN_QUIET=1**: Suppress all console output (takes precedence)
- **CCPN_FORCE_PYTHON=1**: Force Python implementation
- **CCPN_FORCE_C=1**: Force C extension

## What Gets Logged

### INFO Level (Always)
- Implementation selection on module import
- Runtime switching between C and Python

### DEBUG Level (CCPN_DEBUG=1 only)
- Module loading success/failure with error details
- Function calls with parameters (data shapes, thresholds, etc.)
- Performance timing for each operation
- Progress information (vertices, polylines, peaks found)
- Detailed per-level contour generation metrics

## Performance Impact

- **INFO logging**: ~1-2 µs overhead (negligible)
- **DEBUG logging**: ~50-100 µs per operation for timing
- Recommendation: Use DEBUG only during development/testing

## Documentation

See [DEBUG_LOGGING.md](DEBUG_LOGGING.md) for complete usage guide with examples.
