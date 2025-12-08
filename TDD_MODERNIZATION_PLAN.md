# TDD Modernization Plan - C Extension Elimination

**Status:** Phase 1 & 2 Infrastructure Complete ✅
**Date:** 2025-12-08
**Approach:** Test-Driven Development (TDD)

---

## Overview

This document tracks the Test-Driven Development modernization of C extensions to pure Python + NumPy + Numba implementations, following the proven approach from https://github.com/elkins/ccpnmr2.4.

### Proven Results from ccpnmr2.4:
- ✅ **Contour tracing: 90-3200x FASTER** than original C code (with Numba)
- ✅ **Linear algebra: 10-100x faster** than C (NumPy LAPACK)
- ✅ **708 tests passing** with comprehensive validation
- ✅ **84% completion** (42/50 modules converted)

---

## Current Repository Analysis

### C Extensions to Convert

| Module | Lines | Purpose | Priority |
|--------|-------|---------|----------|
| **npy_contourer2d.c** | ~1,200 | 2D contour generation (marching squares) | HIGH |
| **npy_peak.c** | ~1,500 | Peak finding and Gaussian/Lorentzian fitting | HIGH |
| **npy_clibrary.c** | ~670 | Common library utilities | MEDIUM |
| **gauss_jordan.c** | ~200 | Matrix solving | MEDIUM |
| **nonlinear_model.c** | ~300 | Nonlinear optimization | MEDIUM |

**Total:** ~3,372 lines of C code to eliminate

### Test Coverage Analysis

| Repository | Test Files | Coverage |
|------------|-----------|----------|
| **ccpnmr2.4** (reference) | 127 | Comprehensive (1.43:1 test-to-code ratio) |
| **analysis** (current) | 60 | Good core coverage |
| **Gap** | **67 missing tests** | Need to add |

---

## TDD Infrastructure Created

### ✅ Phase 1: Setup Complete

**Module Structure:**
```
src/python/ccpn/c_replacement/
├── __init__.py                 # Package initialization
├── tests/
│   ├── __init__.py            # Test package
│   ├── test_baseline_c_extensions.py  # C extension baseline capture
│   └── test_contour_tdd.py    # TDD tests for contour module
├── contour.py                 # [TO BE IMPLEMENTED]
├── contour_numba.py           # [TO BE IMPLEMENTED]
├── peak.py                    # [TO BE IMPLEMENTED]
└── peak_numba.py              # [TO BE IMPLEMENTED]
```

**Dependencies Installed:**
- ✅ pytest 9.0.1
- ✅ numpy 2.3.5
- ✅ numba 0.62.1
- ✅ scipy (available)

---

## TDD Test Suite: Contour Module

### Tests Created (12 tests total)

**API Tests (3):**
1. ✓ Module importable
2. ✓ `calculate_contours` function exists
3. ✓ Correct function signature

**Functional Tests (6):**
1. ✓ Single level circular contour
2. ✓ Multiple concentric levels
3. ✓ Two separate Gaussians → 2 contours
4. ✓ Merging contours at low threshold
5. ✓ Empty data handling
6. ✓ Level out of range handling

**Edge Case Tests (2):**
1. ✓ Invalid input type rejection
2. ✓ Boundary conditions

**Performance Test (1):**
1. ✓ 512x512 data in <1 second (with Numba)

### TDD Status

**Current:** 🔴 **RED** (tests fail - module not implemented)
**Expected behavior documented:** ✅
**Test fixtures prepared:** ✅
**Ready for implementation:** ✅

---

## Implementation Roadmap

### Phase 2: Contour Module (Current - Weeks 2-5)

**Week 2: Pure Python Implementation**
- [ ] Implement marching squares algorithm
- [ ] Create polyline extraction
- [ ] Handle saddle points correctly
- [ ] Tests pass (🟢 GREEN phase)

**Week 3: Numba Optimization**
- [ ] Add `@jit(nopython=True)` to hot paths
- [ ] Optimize nested loops
- [ ] Optimize interpolation
- [ ] Target: Match or exceed C performance

**Week 4: Validation & Testing**
- [ ] Numerical accuracy validation
- [ ] Performance benchmarking vs C
- [ ] Add edge case tests
- [ ] Documentation

**Week 5: Integration**
- [ ] Create fallback loading (try Python, fallback to C)
- [ ] Update imports in codebase
- [ ] Integration testing

### Phase 3: Peak Module (Weeks 6-9)

**Modules to implement:**
1. Peak finding (`findPeaks`)
2. Gaussian fitting
3. Lorentzian fitting
4. Parabolic fitting

**Test count target:** 400+ lines

### Phase 4: Library Module (Weeks 10-11)

**Utilities to convert:**
- Common numerical operations
- Array utilities
- Math helpers

**Test count target:** 300+ lines

### Phase 5: Test Coverage Enhancement (Weeks 12-15)

**Add 67 test files:**
- Match ccpnmr2.4's 1.4:1 test-to-code ratio
- Comprehensive numerical validation
- Performance benchmarks
- Integration tests

---

## Performance Requirements

Based on ccpnmr2.4 proven results:

| Operation | C Baseline | Target (Python+Numba) | Status |
|-----------|------------|-----------------------|--------|
| **Contour generation** | 1x | **90-3200x faster** | To implement |
| Peak finding | 1x | ≥1x (match) | To implement |
| Gaussian fitting | 1x | ≥0.95x | To implement |
| Linear algebra | 1x | 10-100x (NumPy LAPACK) | To implement |

**Critical:** Contour performance MUST meet or exceed C implementation.

---

## TDD Workflow

### Red-Green-Refactor Cycle

```
1. 🔴 RED: Write failing test
   - Document expected behavior
   - Test API and outputs
   - Run: pytest (should FAIL)

2. 🟢 GREEN: Make test pass
   - Implement minimal code
   - Focus on correctness
   - Run: pytest (should PASS)

3. 🔵 REFACTOR: Optimize
   - Add Numba JIT compilation
   - Optimize algorithms
   - Maintain passing tests
```

### Example Pattern from ccpnmr2.4

```python
# Step 1: Pure Python implementation
def interpolate_edge(v1, v2, level):
    """Linear interpolation."""
    if abs(v2 - v1) < 1e-10:
        return 0.5
    return (level - v1) / (v2 - v1)

# Step 2: Add Numba for performance (AFTER tests pass)
from numba import jit

@jit(nopython=True)
def interpolate_edge_numba(v1: float, v2: float, level: float) -> float:
    """Linear interpolation (numba-optimized)."""
    if abs(v2 - v1) < 1e-10:
        return 0.5
    return (level - v1) / (v2 - v1)
```

---

## Numerical Validation Strategy

### 1. Baseline Capture
- Run C extensions on test data
- Save outputs for comparison
- Document exact behavior

### 2. Python Implementation Validation
- Compare outputs against C baseline
- Validate numerical accuracy (tolerance: 1e-6)
- Test edge cases

### 3. Performance Validation
- Benchmark Python vs C
- Must meet or exceed C performance
- Document speedup ratios

---

## Next Steps

### Immediate (This Week)

1. **Implement contour.py** (marching squares algorithm)
   - Pure Python + NumPy
   - Make TDD tests pass
   - ~500-600 lines estimated

2. **Add contour_numba.py** (Numba optimization)
   - JIT compile hot paths
   - Target: 90-3200x speedup (proven achievable)
   - ~200-300 lines estimated

3. **Validate performance**
   - Run benchmarks
   - Compare to C extension
   - Document results

### This Month

4. **Implement peak module**
   - Write TDD tests first
   - Implement with NumPy + SciPy
   - Numba optimization

5. **Begin test coverage expansion**
   - Add missing 67 test files
   - Follow ccpnmr2.4 patterns

---

## Success Criteria

✅ **All TDD tests passing**
✅ **Performance ≥ C implementations**
✅ **Numerical accuracy validated**
✅ **No compilation dependencies**
✅ **Comprehensive test coverage (1.4:1 ratio)**
✅ **Documentation complete**

---

## References

- **ccpnmr2.4 Repository:** https://github.com/elkins/ccpnmr2.4
- **Key Documents:**
  - `STREAM_2_C_TO_PYTHON_STATUS.md` - Conversion tracking
  - `OPTIMIZATION_PHASE_COMPLETE.md` - Performance results
  - `README_NUMBA.md` - Numba strategy and benchmarks
  - `OPTIMIZATION_GUIDE.md` - Best practices

---

**Last Updated:** 2025-12-08
**Next Review:** After contour module implementation complete
