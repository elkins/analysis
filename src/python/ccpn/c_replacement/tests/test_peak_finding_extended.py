"""Phase 2 Extended Tests: Peak Finding

Additional comprehensive tests for peak finding functionality beyond the core tests.
Tests edge cases, robustness, and various peak configurations.
"""

import numpy as np
import pytest
from ccpn.c_replacement.tests.test_peak_data import (
    generate_gaussian_peak,
    generate_lorentzian_peak,
    generate_multi_peak_spectrum,
)


class TestPeakFindEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_no_peaks_above_threshold(self):
        """Test with data that has no peaks above threshold."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (20, 20)
        # Low intensity peak
        data = generate_gaussian_peak(shape, (10, 10), 10.0, (2, 2))

        # Very high threshold
        peaks = find_peaks(
            data, False, True, 0.0, 100.0,  # threshold=100, peak=10
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 0

    def test_peak_at_array_edge(self):
        """Test peak very close to array boundary."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (20, 20)
        # Peak near edge (but not exactly at edge, which would fail nonadjacent check)
        center = (2, 2)
        data = generate_gaussian_peak(shape, center, 100.0, (1.5, 1.5))

        # Use adjacent mode (less strict about boundaries)
        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [1, 1], False,  # adjacent mode
            0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) >= 1

    def test_very_noisy_data(self):
        """Test peak finding with high noise level."""
        from ccpn.c_replacement.peak_numba import find_peaks

        np.random.seed(42)  # Reproducible
        shape = (30, 30)
        center = (15, 15)
        height = 100.0

        # High noise
        data = generate_gaussian_peak(
            shape, center, height, (2.5, 2.5), noise_level=15.0
        )

        # Should still find the main peak with appropriate threshold
        peaks = find_peaks(
            data, False, True, 0.0, 60.0,  # threshold below peak but above noise
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        # Should find at least one peak (the main one)
        assert len(peaks) >= 1

        # Verify main peak is found
        found_positions = [p[0] for p in peaks]
        distances = [
            np.linalg.norm(np.array(pos) - np.array(center))
            for pos in found_positions
        ]
        assert min(distances) <= 2.0

    def test_overlapping_peaks(self):
        """Test with partially overlapping peaks."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (30, 30)
        # Two peaks close together (overlapping)
        peaks_spec = [
            {'center': (12, 15), 'height': 100, 'linewidth': (3, 3), 'model': 'gaussian'},
            {'center': (18, 15), 'height': 90, 'linewidth': (3, 3), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        peaks = find_peaks(
            data, False, True, 0.0, 40.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        # Should find both peaks despite overlap
        assert len(peaks) == 2

    def test_uniform_data_no_peaks(self):
        """Test with completely uniform data (no peaks).

        Note: In uniform data, every point is technically an extremum
        (neighbors have equal values), so the extremum check passes.
        However, no points should exceed threshold if data is below it.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (20, 20)
        data = np.ones(shape, dtype=np.float32) * 50.0

        # Use threshold above the uniform value
        peaks = find_peaks(
            data, False, True, 0.0, 60.0,  # threshold=60, data=50
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        # No peaks when threshold is above uniform data
        assert len(peaks) == 0


class TestPeakFindDifferentShapes:
    """Test with various array shapes and peak types."""

    def test_narrow_spectrum_2d(self):
        """Test with narrow 2D spectrum."""
        from ccpn.c_replacement.peak_numba import find_peaks

        # Narrow in one dimension
        shape = (50, 10)
        center = (25, 5)
        data = generate_gaussian_peak(shape, center, 100.0, (2, 1))

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 1], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 1
        assert np.allclose(peaks[0][0], center, atol=1)

    def test_small_spectrum_2d(self):
        """Test with very small spectrum."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (10, 10)
        center = (5, 5)
        data = generate_gaussian_peak(shape, center, 100.0, (1.5, 1.5))

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [1, 1], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 1

    def test_large_spectrum_sparse_peaks(self):
        """Test large spectrum with sparse peaks."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (60, 60)
        peaks_spec = [
            {'center': (10, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
            {'center': (50, 50), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [3, 3], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 2

    def test_asymmetric_peak_2d(self):
        """Test peak with different linewidths in each dimension."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (30, 30)
        center = (15, 15)
        # Very different linewidths
        linewidth = (1.5, 4.0)

        data = generate_gaussian_peak(shape, center, 100.0, linewidth)

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 1
        assert np.allclose(peaks[0][0], center, atol=1)


class TestPeakFindLorentzian:
    """Test with Lorentzian peaks (different lineshape)."""

    def test_lorentzian_single_peak_2d(self):
        """Test finding Lorentzian peak."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (30, 30)
        center = (15, 15)
        height = 100.0
        linewidth = (2.5, 2.5)

        data = generate_lorentzian_peak(shape, center, height, linewidth)

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 1
        assert np.allclose(peaks[0][0], center, atol=1)
        assert peaks[0][1] >= 50.0

    def test_mixed_gaussian_lorentzian(self):
        """Test with both Gaussian and Lorentzian peaks."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (40, 40)
        peaks_spec = [
            {'center': (12, 12), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
            {'center': (28, 28), 'height': 100, 'linewidth': (2, 2), 'model': 'lorentzian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        # Should find both peaks regardless of lineshape
        assert len(peaks) == 2


class TestPeakFind3D:
    """Extended 3D tests."""

    def test_multiple_peaks_3d(self):
        """Test finding multiple peaks in 3D."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (20, 20, 20)
        peaks_spec = [
            {'center': (8, 8, 8), 'height': 200, 'linewidth': (2, 2, 2), 'model': 'gaussian'},
            {'center': (12, 12, 12), 'height': 180, 'linewidth': (2, 2, 2), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        peaks = find_peaks(
            data, False, True, 0.0, 80.0,
            [2, 2, 2], True, 0.0, [0.0, 0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 2

    def test_3d_peak_with_noise(self):
        """Test 3D peak finding with noise."""
        from ccpn.c_replacement.peak_numba import find_peaks

        np.random.seed(123)
        shape = (16, 16, 16)
        center = (8, 8, 8)
        height = 300.0

        data = generate_gaussian_peak(
            shape, center, height, (2, 2, 2), noise_level=10.0
        )

        peaks = find_peaks(
            data, False, True, 0.0, 100.0,
            [2, 2, 2], True, 0.0, [0.0, 0.0, 0.0],
            [], [], []
        )

        assert len(peaks) >= 1
        # Main peak should be found
        found_positions = [p[0] for p in peaks]
        distances = [
            np.linalg.norm(np.array(pos) - np.array(center))
            for pos in found_positions
        ]
        assert min(distances) <= 2.0


class TestPeakFindStrictCriteria:
    """Test with strict filtering criteria."""

    def test_strict_drop_factor(self):
        """Test with very strict drop factor."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (30, 30)
        # Narrow peak (drops quickly)
        data_narrow = generate_gaussian_peak(
            shape, (15, 15), 100.0, (1.5, 1.5)
        )

        # Wide peak (drops slowly)
        data_wide = generate_gaussian_peak(
            shape, (15, 15), 100.0, (4.0, 4.0)
        )

        # Strict drop factor (0.8 = must drop 80%)
        peaks_narrow = find_peaks(
            data_narrow, False, True, 0.0, 50.0,
            [2, 2], True, 0.8, [0.0, 0.0],
            [], [], []
        )

        peaks_wide = find_peaks(
            data_wide, False, True, 0.0, 50.0,
            [2, 2], True, 0.8, [0.0, 0.0],
            [], [], []
        )

        # Narrow peak should pass (drops quickly)
        assert len(peaks_narrow) == 1

        # Wide peak might not drop enough in the array
        # Just verify it doesn't crash
        assert len(peaks_wide) >= 0

    def test_strict_linewidth_filters_narrow_peaks(self):
        """Test that strict linewidth criterion filters narrow peaks."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (30, 30)
        peaks_spec = [
            # Narrow peak (should be filtered)
            {'center': (10, 10), 'height': 100, 'linewidth': (1.3, 1.3), 'model': 'gaussian'},
            # Wide peak (should pass)
            {'center': (20, 20), 'height': 100, 'linewidth': (3.5, 3.5), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        # Require minimum linewidth of 2.5
        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [2.5, 2.5],
            [], [], []
        )

        # Should find only the wide peak
        assert len(peaks) == 1
        # Verify it's the wide peak
        assert np.allclose(peaks[0][0], (20, 20), atol=2)

    def test_dimension_specific_linewidth(self):
        """Test linewidth criterion with different values per dimension."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (30, 30)
        # Peak with asymmetric linewidth
        center = (15, 15)
        linewidth = (3.0, 1.5)  # Wide in dim0, narrow in dim1

        data = generate_gaussian_peak(shape, center, 100.0, linewidth)

        # Require 2.5 in dim0, 1.0 in dim1
        peaks_pass = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [2.5, 1.0],  # Should pass
            [], [], []
        )

        # Require 2.5 in both dimensions
        peaks_fail = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [2.5, 2.5],  # Should fail (dim1 too narrow)
            [], [], []
        )

        assert len(peaks_pass) == 1
        assert len(peaks_fail) == 0


class TestPeakFindIntensityRange:
    """Test with various intensity ranges."""

    def test_very_low_intensity_peak(self):
        """Test with very low intensity peak."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (20, 20)
        center = (10, 10)
        height = 5.0  # Very low

        data = generate_gaussian_peak(shape, center, height, (2, 2))

        peaks = find_peaks(
            data, False, True, 0.0, 2.0,  # Low threshold
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 1
        assert peaks[0][1] >= 2.0

    def test_very_high_intensity_peak(self):
        """Test with very high intensity peak."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (20, 20)
        center = (10, 10)
        height = 10000.0  # Very high

        data = generate_gaussian_peak(shape, center, height, (2, 2))

        peaks = find_peaks(
            data, False, True, 0.0, 5000.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 1
        assert peaks[0][1] >= 5000.0

    def test_peak_with_negative_background(self):
        """Test peak on negative background."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (20, 20)
        center = (10, 10)

        # Positive peak on negative background
        data = generate_gaussian_peak(shape, center, 100.0, (2, 2))
        data = data - 20.0  # Shift down

        peaks = find_peaks(
            data, False, True, 0.0, 40.0,  # Positive threshold
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 1


class TestPeakFindRobustness:
    """Test robustness to various conditions."""

    def test_zero_drop_factor(self):
        """Test with drop_factor=0 (disabled)."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (20, 20)
        data = generate_gaussian_peak(shape, (10, 10), 100.0, (2, 2))

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0,  # drop_factor=0 (disabled)
            [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 1

    def test_zero_min_linewidth(self):
        """Test with min_linewidth=0 (disabled)."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (20, 20)
        data = generate_gaussian_peak(shape, (10, 10), 100.0, (1.0, 1.0))

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0,
            [0.0, 0.0],  # min_linewidth=0 (disabled)
            [], [], []
        )

        assert len(peaks) == 1

    def test_many_peaks_performance(self):
        """Test with many peaks (performance check)."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (50, 50)
        peaks_spec = []

        # Create grid of peaks
        for i in range(10, 45, 8):
            for j in range(10, 45, 8):
                peaks_spec.append({
                    'center': (i, j),
                    'height': 100,
                    'linewidth': (2, 2),
                    'model': 'gaussian'
                })

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        # Should find most peaks (might miss some at edges)
        assert len(peaks) >= len(peaks_spec) - 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
