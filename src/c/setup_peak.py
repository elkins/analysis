#!/usr/bin/env python3
"""
Build script for CCPN C peak extension.

Usage:
    python setup_peak.py build_ext --inplace
"""

from setuptools import setup, Extension
import numpy as np
import os

# Get numpy include dirs (both locations)
numpy_includes = [
    np.get_include(),
    os.path.join(np.get_include(), 'numpy'),
]

# Define the peak extension
peak_extension = Extension(
    'ccpnc.peak.Peak',
    sources=[
        'ccpnc/peak/npy_peak.c',
        'ccpnc/peak/nonlinear_model.c',
        'ccpnc/peak/gauss_jordan.c'
    ],
    include_dirs=numpy_includes + ['ccpnc/peak'],
    extra_compile_args=['-O3', '-ffast-math'],  # Aggressive optimization
    define_macros=[('NPY_NO_DEPRECATED_API', 'NPY_1_7_API_VERSION')],
)

setup(
    name='ccpnc-peak',
    version='1.0',
    description='CCPN Peak C Extension',
    ext_modules=[peak_extension],
)
