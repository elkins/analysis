"""Extended test coverage for parabolic peak fitting.

Additional tests for edge cases, error conditions, and validation.
"""

import pytest
import numpy as np
from .test_peak_data import (
    generate_gaussian_peak,
    generate_lorentzian_peak,
    generate_multi_peak_spectrum,
)


class TestParabolicEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_peak_at_array_boundary_left(self):
        """Test that peaks at left boundary are handled gracefully."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20)
        center = (0.5, 10.0)  # Very close to left boundary
        height = 100.0
        linewidth = (2.5, 3.0)

        data = generate_gaussian_peak(shape, center, height, linewidth)

        # Peak at boundary - should fall back to grid position
        peak_array = np.array([[0.0, 10.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [20, 20]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Should have some result (grid position fallback)
        assert fitted_height > 0
        assert fitted_pos[0] == 0.0  # Grid position fallback

    def test_peak_at_array_boundary_right(self):
        """Test that peaks at right boundary are handled gracefully."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20)
        center = (19.5, 10.0)  # Very close to right boundary
        height = 100.0
        linewidth = (2.5, 3.0)

        data = generate_gaussian_peak(shape, center, height, linewidth)

        # Peak at boundary
        peak_array = np.array([[19.0, 10.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [20, 20]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Should have result with fallback
        assert fitted_height > 0
        assert fitted_pos[0] == 19.0  # Grid position fallback

    def test_very_narrow_peak(self):
        """Test fitting of very narrow peak (potential numerical issues)."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (30, 30)
        center = (15.0, 15.0)
        height = 1000.0
        linewidth = (0.5, 0.5)  # Very narrow

        data = generate_gaussian_peak(shape, center, height, linewidth)

        peak_array = np.array([[15.0, 15.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [30, 30]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Should still get reasonable results
        assert fitted_height > 0
        assert np.allclose(fitted_pos, center, atol=0.5)

    def test_very_wide_peak(self):
        """Test fitting of very wide peak."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (50, 50)
        center = (25.0, 25.0)
        height = 100.0
        linewidth = (10.0, 10.0)  # Very wide

        data = generate_gaussian_peak(shape, center, height, linewidth)

        peak_array = np.array([[25.0, 25.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [50, 50]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        assert np.isclose(fitted_height, height, rtol=0.1)
        assert np.allclose(fitted_pos, center, atol=0.5)
        # Wide peak should have large linewidth
        assert fitted_lw[0] > 5.0
        assert fitted_lw[1] > 5.0

    def test_noisy_data(self):
        """Test parabolic fitting with noisy data."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (30, 30)
        center = (15.3, 15.7)
        height = 100.0
        linewidth = (3.0, 3.0)
        noise_level = 10.0  # 10% noise

        data = generate_gaussian_peak(shape, center, height, linewidth, noise_level)

        peak_array = np.array([[15.0, 16.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [30, 30]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Should still get reasonably close results despite noise
        assert np.isclose(fitted_height, height, rtol=0.2)
        assert np.allclose(fitted_pos, center, atol=1.0)

    def test_negative_peak(self):
        """Test fitting of negative (inverted) peak."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20)
        center = (10.0, 10.0)
        height = -100.0  # Negative peak
        linewidth = (2.5, 2.5)

        data = generate_gaussian_peak(shape, center, height, linewidth)

        peak_array = np.array([[10.0, 10.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [20, 20]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Should handle negative peaks
        assert fitted_height < 0
        assert np.isclose(fitted_height, height, rtol=0.1)


class TestParabolicValidation:
    """Test input validation and error handling."""

    def test_wrong_dtype_data(self):
        """Test that non-float32 data is converted."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20)
        # Create float64 data (wrong dtype)
        data = np.random.rand(*shape).astype(np.float64)
        data[10, 10] = 100.0

        peak_array = np.array([[10.0, 10.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [20, 20]], dtype=np.int32)

        # Should auto-convert to float32
        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1

    def test_wrong_region_shape(self):
        """Test that wrong region array shape raises error."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20)
        data = np.random.rand(*shape).astype(np.float32)

        peak_array = np.array([[10.0, 10.0]], dtype=np.float32)
        # Wrong shape: should be (2, 2) not (2, 3)
        region_array = np.array([[0, 0, 0], [20, 20, 20]], dtype=np.int32)

        with pytest.raises(ValueError, match="regionArray must be"):
            fit_parabolic_peaks(data, region_array, peak_array)

    def test_wrong_peak_shape(self):
        """Test that wrong peak array shape raises error."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20)
        data = np.random.rand(*shape).astype(np.float32)

        # Wrong shape: ndim mismatch
        peak_array = np.array([[10.0, 10.0, 10.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [20, 20]], dtype=np.int32)

        with pytest.raises(ValueError, match="peakArray must be"):
            fit_parabolic_peaks(data, region_array, peak_array)

    def test_empty_peak_array(self):
        """Test with empty peak array."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20)
        data = np.random.rand(*shape).astype(np.float32)

        # Empty peak array
        peak_array = np.zeros((0, 2), dtype=np.float32)
        region_array = np.array([[0, 0], [20, 20]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        # Should return empty list
        assert len(results) == 0

    def test_many_peaks(self):
        """Test fitting many peaks at once."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (50, 50)
        # Create 25 peaks in a grid
        peaks_spec = []
        for i in range(5):
            for j in range(5):
                peaks_spec.append({
                    'center': (10 + i * 8, 10 + j * 8),
                    'height': 100.0 + i * j * 5,
                    'linewidth': (2.0 + i * 0.1, 2.0 + j * 0.1),
                    'model': 'gaussian'
                })

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        # Create peak array for all peaks
        peak_positions = np.array([p['center'] for p in peaks_spec], dtype=np.float32)
        region_array = np.array([[0, 0], [50, 50]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_positions)

        # Should fit all 25 peaks
        assert len(results) == 25

        # All should have reasonable results
        for height, pos, lw in results:
            assert height > 50.0  # All peaks > 50
            assert lw[0] > 1.0 and lw[0] < 5.0
            assert lw[1] > 1.0 and lw[1] < 5.0


class TestParabolicLorentzian:
    """Test parabolic fitting with Lorentzian peaks."""

    def test_lorentzian_2d(self):
        """Test parabolic fitting works with Lorentzian peak shape."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (30, 30)
        center = (15.3, 15.7)
        height = 100.0
        linewidth = (2.5, 3.0)

        # Generate Lorentzian peak
        data = generate_lorentzian_peak(shape, center, height, linewidth)

        peak_array = np.array([[15.0, 16.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [30, 30]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Parabolic fit should work reasonably well for Lorentzian too
        assert np.isclose(fitted_height, height, rtol=0.15)
        assert np.allclose(fitted_pos, center, atol=0.5)

    def test_mixed_gaussian_lorentzian(self):
        """Test fitting mixed Gaussian and Lorentzian peaks."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (40, 40)
        peaks_spec = [
            {'center': (10, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
            {'center': (30, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'lorentzian'},
            {'center': (20, 30), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        peak_array = np.array([[10, 10], [30, 10], [20, 30]], dtype=np.float32)
        region_array = np.array([[0, 0], [40, 40]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 3

        # All should fit reasonably well
        for i, (fitted_height, fitted_pos, fitted_lw) in enumerate(results):
            expected = peaks_spec[i]
            assert np.isclose(fitted_height, expected['height'], rtol=0.15)
            assert np.allclose(fitted_pos, expected['center'], atol=0.5)


class TestParabolic4D:
    """Test 4D parabolic fitting."""

    def test_4d_single_peak(self):
        """Test 4D parabolic peak fitting."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (10, 12, 14, 16)
        center = (5.2, 6.3, 7.4, 8.5)
        height = 200.0
        linewidth = (1.5, 2.0, 2.5, 3.0)

        data = generate_gaussian_peak(shape, center, height, linewidth)

        peak_array = np.array([[5.0, 6.0, 7.0, 9.0]], dtype=np.float32)
        region_array = np.array([[3, 4, 5, 6],
                                 [8, 9, 10, 11]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # 4D should work with reasonable accuracy
        assert np.isclose(fitted_height, height, rtol=0.2)
        assert np.allclose(fitted_pos, center, atol=0.5)
        assert len(fitted_lw) == 4


class TestParabolicCornerCases:
    """Test unusual but valid corner cases."""

    def test_peak_positions_out_of_bounds(self):
        """Test that out-of-bounds peak positions are clipped."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20)
        data = np.random.rand(*shape).astype(np.float32)
        data[10, 10] = 100.0

        # Peak position outside array bounds
        peak_array = np.array([[25.0, 25.0]], dtype=np.float32)  # Out of bounds
        region_array = np.array([[0, 0], [20, 20]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        # Should clip to bounds and return result
        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Position should be clipped to [0, 19]
        assert fitted_pos[0] <= 19.0
        assert fitted_pos[1] <= 19.0

    def test_identical_overlapping_peaks(self):
        """Test multiple peaks at same position."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20)
        center = (10.0, 10.0)
        height = 100.0
        linewidth = (2.5, 2.5)

        data = generate_gaussian_peak(shape, center, height, linewidth)

        # Two peaks at same location
        peak_array = np.array([[10.0, 10.0],
                               [10.0, 10.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [20, 20]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        # Should fit both (even though they're identical)
        assert len(results) == 2

        # Results should be nearly identical
        assert np.isclose(results[0][0], results[1][0], rtol=0.01)

    def test_asymmetric_peak(self):
        """Test with asymmetric peak (different linewidths in each dimension)."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (30, 30)
        center = (15.0, 15.0)
        height = 100.0
        linewidth = (1.5, 5.0)  # Very asymmetric

        data = generate_gaussian_peak(shape, center, height, linewidth)

        peak_array = np.array([[15.0, 15.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [30, 30]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Should capture asymmetry in linewidths
        assert fitted_lw[0] < fitted_lw[1]  # x narrower than y
        ratio = fitted_lw[1] / fitted_lw[0]
        assert ratio > 2.0  # Significant asymmetry


class TestParabolicRobustness:
    """Test robustness to various data conditions."""

    def test_constant_background(self):
        """Test fitting with constant background offset."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (30, 30)
        center = (15.0, 15.0)
        height = 100.0
        linewidth = (2.5, 2.5)
        background = 20.0

        data = generate_gaussian_peak(shape, center, height, linewidth)
        data += background  # Add constant background

        peak_array = np.array([[15.0, 15.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [30, 30]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Should fit peak + background height
        assert np.isclose(fitted_height, height + background, rtol=0.1)

    def test_very_low_intensity(self):
        """Test with very low intensity peak."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (20, 20)
        center = (10.0, 10.0)
        height = 0.01  # Very low intensity
        linewidth = (2.5, 2.5)

        data = generate_gaussian_peak(shape, center, height, linewidth)

        peak_array = np.array([[10.0, 10.0]], dtype=np.float32)
        region_array = np.array([[0, 0], [20, 20]], dtype=np.int32)

        results = fit_parabolic_peaks(data, region_array, peak_array)

        assert len(results) == 1
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Should still get reasonable fit even with low intensity
        assert fitted_height > 0
        assert np.allclose(fitted_pos, center, atol=0.5)

    def test_single_point_spectrum_1d(self):
        """Test 1D array (edge case for dimensionality)."""
        from ccpn.c_replacement.peak_models import fit_parabolic_to_ndim_1d

        # Create simple 1D peak
        data = np.array([1.0, 5.0, 10.0, 5.0, 1.0], dtype=np.float32)
        point = np.array([2], dtype=np.int64)  # Peak at index 2
        dim = 0

        peak_pos, height, lw = fit_parabolic_to_ndim_1d(data, point, dim)

        # Should fit the peak
        assert peak_pos >= 1.5 and peak_pos <= 2.5
        assert height >= 9.0  # Should be close to 10
        assert lw > 0
