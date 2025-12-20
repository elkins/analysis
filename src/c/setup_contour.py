#!/usr/bin/env python3
"""
Build script for CCPN C contour extension.

Usage:
    python setup_contour.py build_ext --inplace
"""

from setuptools import setup, Extension
import numpy as np
import os

# Get numpy include dirs (both locations)
numpy_includes = [
    np.get_include(),
    os.path.join(np.get_include(), 'numpy'),
]

# Define the contour extension
contour_extension = Extension(
    'ccpnc.contour.Contourer2d',
    sources=['ccpnc/contour/npy_contourer2d.c'],
    include_dirs=numpy_includes + ['ccpnc/contour'],
    extra_compile_args=['-O3', '-ffast-math'],  # Aggressive optimization
    define_macros=[('NPY_NO_DEPRECATED_API', 'NPY_1_7_API_VERSION')],
)

setup(
    name='ccpnc-contour',
    version='1.0',
    description='CCPN Contour C Extension',
    ext_modules=[contour_extension],
)
