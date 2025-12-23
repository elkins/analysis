"""
Compatibility wrapper for contour module with switchable implementations.

This module provides the Contourer2d interface with automatic fallback and
runtime switching between C and Python implementations.

Usage:
    from ccpn.c_replacement.contour_compat import Contourer2d

    # Same API as C extension
    contours = Contourer2d.contourerGLList(dataArrays, posLevels, ...)

Configuration (Environment Variables):
    export CCPN_FORCE_PYTHON=1    # Force pure Python (disable C)
    export CCPN_FORCE_C=1          # Force C (error if not available)

Runtime Switching:
    import ccpn.c_replacement.contour_compat as contour_compat
    contour_compat.use_python_implementation()  # Switch to Python
    contour_compat.use_c_implementation()        # Switch to C

    # Check what's available
    info = contour_compat.get_available_implementations()
    print(info['current'])  # Current implementation
"""

import os
import sys
import numpy as np
from typing import List, Optional, Tuple
import warnings


# Configuration: Check environment variables
_FORCE_PYTHON = os.environ.get('CCPN_FORCE_PYTHON', '0') == '1'
_FORCE_C = os.environ.get('CCPN_FORCE_C', '0') == '1'

# Store both implementations if available
_c_implementation = None
_python_implementation = None
_implementation = None
_using_c = False
_impl_name = None

# Try to load C extension
if not _FORCE_PYTHON:
    try:
        from ccpnc.contour import Contourer2d as _c_implementation
    except ImportError:
        _c_implementation = None

# Try to load Python implementation
if not _FORCE_C:
    try:
        from . import contour_numba as _python_implementation
    except ImportError:
        _python_implementation = None

# Select implementation based on configuration
if _FORCE_PYTHON:
    if _python_implementation is None:
        raise ImportError("CCPN_FORCE_PYTHON=1 but Python implementation not available")
    _implementation = _python_implementation
    _using_c = False
    _impl_name = 'Pure Python (Numba JIT) [FORCED]'
elif _FORCE_C:
    if _c_implementation is None:
        raise ImportError("CCPN_FORCE_C=1 but C extension not available")
    _implementation = _c_implementation
    _using_c = True
    _impl_name = 'C extension [FORCED]'
else:
    # Auto-select: prefer C, fallback to Python
    if _c_implementation is not None:
        _implementation = _c_implementation
        _using_c = True
        _impl_name = 'C extension'
    elif _python_implementation is not None:
        _implementation = _python_implementation
        _using_c = False
        _impl_name = 'Pure Python (Numba JIT)'
    else:
        raise ImportError("Neither C extension nor Python implementation available")


def use_python_implementation():
    """Force use of pure Python implementation.

    Raises:
        RuntimeError: If Python implementation is not available
    """
    global _implementation, _using_c, _impl_name

    if _python_implementation is None:
        raise RuntimeError("Python implementation not available")

    _implementation = _python_implementation
    _using_c = False
    _impl_name = 'Pure Python (Numba JIT) [RUNTIME SWITCH]'
    print(f"Contour module: Switched to {_impl_name}", file=sys.stderr)


def use_c_implementation():
    """Force use of C extension.

    Raises:
        RuntimeError: If C extension is not available
    """
    global _implementation, _using_c, _impl_name

    if _c_implementation is None:
        raise RuntimeError("C extension not available")

    _implementation = _c_implementation
    _using_c = True
    _impl_name = 'C extension [RUNTIME SWITCH]'
    print(f"Contour module: Switched to {_impl_name}", file=sys.stderr)


def get_available_implementations() -> dict:
    """Get information about which implementations are available.

    Returns:
        Dictionary with availability information:
        - 'c_available': bool
        - 'python_available': bool
        - 'current': str (name of current implementation)
        - 'using_c': bool
    """
    return {
        'c_available': _c_implementation is not None,
        'python_available': _python_implementation is not None,
        'current': _impl_name,
        'using_c': _using_c,
    }


def get_implementation_info() -> dict:
    """Return information about current Contour module implementation.

    Returns:
        Dictionary with implementation details
    """
    return {
        'implementation': _impl_name,
        'module': _implementation.__name__ if _implementation else None,
        'using_c': _using_c,
        'c_available': _c_implementation is not None,
        'python_available': _python_implementation is not None,
    }


class Contourer2d:
    """2D contour generation for NMR spectra.

    This class provides a unified interface to contour generation,
    automatically using either the C extension or pure Python implementation.

    Performance note:
        C extension is ~16x faster than Python for typical use cases.
        Python version suitable for development/testing.
    """

    @staticmethod
    def contourerGLList(dataArrays, posLevels, negLevels, posColour, negColour, flatten=0):
        """Generate contours in OpenGL format.

        Args:
            dataArrays: Tuple of 2D numpy arrays (float32)
            posLevels: 1D array of positive contour levels (float32)
            negLevels: 1D array of negative contour levels (float32)
            posColour: RGBA color for positive contours (4 floats)
            negColour: RGBA color for negative contours (4 floats)
            flatten: Whether to flatten multiple arrays (0 or 1)

        Returns:
            List containing [numIndices, numVertices, indexing, vertices, colours]
        """
        if _using_c:
            # C implementation is the Contourer2d class itself
            return _implementation.contourerGLList(
                dataArrays, posLevels, negLevels, posColour, negColour, flatten
            )
        else:
            # Python implementation is the module
            return _implementation.contourerGLList(
                dataArrays, posLevels, negLevels, posColour, negColour, flatten
            )


# Export public API
__all__ = [
    'Contourer2d',
    'get_implementation_info',
    'get_available_implementations',
    'use_python_implementation',
    'use_c_implementation',
]


# Print implementation info on import (can be disabled)
if os.environ.get('CCPN_QUIET') != '1':
    print(f"CCPN Contour: Using {_impl_name}", file=sys.stderr)
    if not _using_c and _c_implementation is not None:
        print(f"  Note: C extension available but not selected", file=sys.stderr)
        print(f"  (C is ~16x faster - use use_c_implementation() to switch)", file=sys.stderr)
