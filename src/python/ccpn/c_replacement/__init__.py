"""
C Extension Replacement Modules

This package provides pure Python + NumPy + Numba implementations of the C extensions
in src/c/ccpnc/. These implementations aim to match or exceed the performance of the
original C code while eliminating compilation dependencies.

Modules:
- contour: 2D contour generation (marching squares algorithm)
- peak: Peak finding and fitting for NMR spectra
- clib: Common library utilities

Each module provides:
1. Pure Python/NumPy base implementation (readable, maintainable)
2. Numba-optimized version for performance-critical operations
3. Comprehensive test suite with numerical validation
4. Performance benchmarks comparing to C implementation

Usage:
    from ccpn.c_replacement import contour, peak

Installation:
    Requires: numpy, scipy, numba
    pip install numpy scipy numba
"""

__version__ = "1.0.0"
__all__ = ['contour', 'peak', 'clib']
