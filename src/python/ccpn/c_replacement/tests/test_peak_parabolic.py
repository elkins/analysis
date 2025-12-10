"""Phase 1 Tests: Parabolic Peak Fitting

These tests cover parabolic interpolation for peak refinement.
This is the simplest phase with no iterative fitting or dependencies.
"""

import pytest
import numpy as np
from .test_peak_data import (
    generate_gaussian_peak,
    generate_multi_peak_spectrum,
    generate_parabolic_test_case
)


class TestParabolicFit1D:
    """Test 1D parabolic fitting functions."""

    def test_parabolic_fit_1d_perfect_center(self):
        """Test parabolic fitting with peak exactly at center point.

        RED: This test will fail until we implement fit_parabolic_1d()
        """
        from ccpn.c_replacement.peak_models import fit_parabolic_1d

        # Perfect parabola: y = -(x-0)^2 + 10
        # Peak at x=0 (middle point), height=10
        v_left, v_middle, v_right = generate_parabolic_test_case(
            offset=0.0, height=10.0, curvature=-1.0
        )

        peak_offset, peak_height, linewidth = fit_parabolic_1d(
            v_left, v_middle, v_right
        )

        # Peak should be at offset 0 from middle
        assert np.isclose(peak_offset, 0.0, atol=1e-6)
        # Height should be 10
        assert np.isclose(peak_height, 10.0, atol=1e-6)
        # Linewidth should be positive
        assert linewidth > 0

    def test_parabolic_fit_1d_offset_positive(self):
        """Test parabolic fitting with peak between grid points (positive offset).

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_models import fit_parabolic_1d

        # Peak at x=0.3 (offset +0.3 from middle)
        v_left, v_middle, v_right = generate_parabolic_test_case(
            offset=0.3, height=10.0, curvature=-1.0
        )

        peak_offset, peak_height, linewidth = fit_parabolic_1d(
            v_left, v_middle, v_right
        )

        assert np.isclose(peak_offset, 0.3, atol=0.01)
        assert np.isclose(peak_height, 10.0, atol=0.1)
        assert linewidth > 0

    def test_parabolic_fit_1d_offset_negative(self):
        """Test parabolic fitting with peak offset in negative direction.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_models import fit_parabolic_1d

        # Peak at x=-0.4 (offset -0.4 from middle)
        v_left, v_middle, v_right = generate_parabolic_test_case(
            offset=-0.4, height=15.0, curvature=-2.0
        )

        peak_offset, peak_height, linewidth = fit_parabolic_1d(
            v_left, v_middle, v_right
        )

        assert np.isclose(peak_offset, -0.4, atol=0.01)
        assert np.isclose(peak_height, 15.0, atol=0.1)
        assert linewidth > 0

    def test_parabolic_fit_1d_wide_peak(self):
        """Test parabolic fitting with wide peak (small curvature).

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_models import fit_parabolic_1d

        # Wide peak: small curvature
        v_left, v_middle, v_right = generate_parabolic_test_case(
            offset=0.0, height=100.0, curvature=-0.1
        )

        peak_offset, peak_height, linewidth = fit_parabolic_1d(
            v_left, v_middle, v_right
        )

        assert np.isclose(peak_offset, 0.0, atol=0.01)
        assert np.isclose(peak_height, 100.0, atol=0.5)
        # Wide peak should have large linewidth
        assert linewidth > 2.0

    def test_parabolic_fit_1d_narrow_peak(self):
        """Test parabolic fitting with narrow peak (large curvature).

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_models import fit_parabolic_1d

        # Narrow peak: large curvature magnitude
        # Using curvature=-50 makes peak drop faster => narrower FWHM
        v_left, v_middle, v_right = generate_parabolic_test_case(
            offset=0.0, height=100.0, curvature=-50.0
        )

        peak_offset, peak_height, linewidth = fit_parabolic_1d(
            v_left, v_middle, v_right
        )

        assert np.isclose(peak_offset, 0.0, atol=0.01)
        assert np.isclose(peak_height, 100.0, atol=0.5)
        # Narrow peak should have small linewidth
        # FWHM = 2*sqrt(height/(2*|curvature|)) = 2*sqrt(100/(2*50)) = 2*sqrt(1) = 2.0
        assert linewidth < 3.0

    def test_parabolic_fit_1d_flat_region_error(self):
        """Test that flat region is detected as error.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_models import fit_parabolic_1d

        # Flat region: all values equal
        v_left = 5.0
        v_middle = 5.0
        v_right = 5.0

        # Should return error indication or raise exception
        with pytest.raises((ValueError, ZeroDivisionError)):
            fit_parabolic_1d(v_left, v_middle, v_right)


class TestParabolicFit2D:
    """Test 2D parabolic peak fitting."""

    def test_parabolic_fit_2d_single_peak_centered(self):
        """Test 2D parabolic fitting with peak at integer grid point.

        RED: Test will fail until fitParabolicToNDim is implemented.
        """
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        # Generate 2D Gaussian peak at integer position
        shape = (20, 20)
        center = (10.0, 15.0)  # Integer positions
        height = 100.0
        linewidth = (2.5, 3.0)

        data = generate_gaussian_peak(shape, center, height, linewidth)

        # Peak array: exact center position
        peak_array = np.array([[10.0, 15.0]], dtype=np.float32)

        # Region array: fit region around peak
        region_array = np.array([[8, 13],   # x: [8, 18)
                                 [18, 18]], dtype=np.int32)  # y: [13, 18)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Should recover true parameters
        assert np.isclose(fitted_height, height, rtol=0.05)
        assert np.allclose(fitted_pos, center, atol=0.1)
        assert np.allclose(fitted_lw, linewidth, rtol=0.15)

    def test_parabolic_fit_2d_single_peak_offset(self):
        """Test 2D parabolic fitting with peak between grid points.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        # Generate 2D Gaussian peak at non-integer position
        shape = (20, 20)
        center = (10.3, 15.7)  # Non-integer positions
        height = 100.0
        linewidth = (2.5, 3.0)

        data = generate_gaussian_peak(shape, center, height, linewidth)

        # Peak array: initial guess (rounded positions)
        peak_array = np.array([[10.0, 16.0]], dtype=np.float32)

        # Region array: fit region around peak
        region_array = np.array([[8, 13],
                                 [18, 18]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Should refine to sub-pixel position
        assert np.isclose(fitted_height, height, rtol=0.05)
        assert np.allclose(fitted_pos, center, atol=0.2)
        assert np.allclose(fitted_lw, linewidth, rtol=0.15)

    def test_parabolic_fit_2d_multiple_peaks(self):
        """Test fitting multiple peaks in one call.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (30, 30)
        peaks_spec = [
            {'center': (10, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
            {'center': (20, 15), 'height': 80, 'linewidth': (3, 2.5), 'model': 'gaussian'},
            {'center': (15, 22), 'height': 120, 'linewidth': (2.5, 3), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        peak_array = np.array([[10, 10],
                               [20, 15],
                               [15, 22]], dtype=np.float32)
        region_array = np.array([[0, 0],
                                 [30, 30]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 3

        for i, (fitted_height, fitted_pos, fitted_lw) in enumerate(results):
            expected = peaks_spec[i]
            assert np.isclose(fitted_height, expected['height'], rtol=0.1)
            assert np.allclose(fitted_pos, expected['center'], atol=0.3)


class TestParabolicFit3D:
    """Test 3D parabolic peak fitting."""

    def test_parabolic_fit_3d_single_peak(self):
        """Test 3D parabolic peak fitting.

        RED: Test will fail until 3D implementation exists.
        """
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

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

    def test_parabolic_fit_3d_multiple_peaks(self):
        """Test 3D parabolic fitting with multiple peaks.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20, 20)
        peaks_spec = [
            {'center': (8, 8, 8), 'height': 200, 'linewidth': (2, 2, 2), 'model': 'gaussian'},
            {'center': (14, 14, 14), 'height': 180, 'linewidth': (2.5, 2.5, 2.5), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        peak_array = np.array([[8, 8, 8],
                               [14, 14, 14]], dtype=np.float32)
        region_array = np.array([[0, 0, 0],
                                 [20, 20, 20]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 2

        for i, (fitted_height, fitted_pos, fitted_lw) in enumerate(results):
            expected = peaks_spec[i]
            assert np.isclose(fitted_height, expected['height'], rtol=0.1)
            assert np.allclose(fitted_pos, expected['center'], atol=0.5)
