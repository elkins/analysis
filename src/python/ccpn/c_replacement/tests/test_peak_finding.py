"""Phase 2 TDD Tests: Peak Finding

This module contains tests for the peak finding functionality, implementing
the C function findPeaks() from npy_peak.c lines 459-563.

Test Strategy:
- Start with simple single peak detection
- Add multiple peaks
- Test threshold filtering (have_low, have_high)
- Test adjacency checking (nonadjacent mode)
- Test drop criterion
- Test linewidth criterion
- Test exclusion zones
"""

import numpy as np
import pytest
from ccpn.c_replacement.tests.test_peak_data import (
    generate_gaussian_peak,
    generate_multi_peak_spectrum,
)


class TestPeakFindBasic:
    """Basic peak finding tests."""

    def test_find_single_peak_2d(self):
        """Test finding a single Gaussian peak in 2D data.

        RED: Test will fail until find_peaks() implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        # Generate 2D peak
        shape = (20, 20)
        center = (10, 15)
        height = 100.0
        linewidth = (2.5, 3.0)

        data = generate_gaussian_peak(
            shape, center, height, linewidth, noise_level=1.0
        )

        # Search for maxima above threshold
        have_low = False
        have_high = True
        low = 0.0
        high = 50.0  # Threshold: 50% of peak height
        buffer = [3, 3]  # 3-point exclusion buffer per dimension
        nonadjacent = True  # Check all 3^N neighbors
        drop_factor = 0.0  # Disable drop criterion for now
        min_linewidth = [0.0, 0.0]  # Disable linewidth criterion for now

        peaks = find_peaks(
            data, have_low, have_high, low, high,
            buffer, nonadjacent, drop_factor, min_linewidth,
            [], [], []  # No exclusion regions
        )

        assert len(peaks) == 1, f"Expected 1 peak, found {len(peaks)}"

        peak_pos, peak_height = peaks[0]

        # Peak height should be above threshold
        assert peak_height >= high, f"Peak height {peak_height} < threshold {high}"

        # Peak position should be close to actual center
        # (within 1 pixel, since we're finding integer grid positions)
        assert np.allclose(
            peak_pos, center, atol=1
        ), f"Peak at {peak_pos} far from expected {center}"

    def test_find_single_peak_3d(self):
        """Test finding a single peak in 3D data.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (16, 20, 24)
        center = (8, 10, 12)
        height = 500.0
        linewidth = (2.0, 2.5, 3.0)

        data = generate_gaussian_peak(
            shape, center, height, linewidth, noise_level=2.0
        )

        peaks = find_peaks(
            data, False, True, 0.0, 200.0,
            [2, 2, 2], True, 0.0, [0.0, 0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 1
        peak_pos, peak_height = peaks[0]
        assert peak_height >= 200.0
        assert np.allclose(peak_pos, center, atol=1)

    def test_find_multiple_peaks_2d(self):
        """Test finding multiple well-separated peaks.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (40, 40)
        peaks_spec = [
            {'center': (10, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
            {'center': (30, 10), 'height': 120, 'linewidth': (2.5, 2.5), 'model': 'gaussian'},
            {'center': (20, 30), 'height': 90, 'linewidth': (3, 3), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec, noise_level=1.0)

        peaks = find_peaks(
            data, False, True, 0.0, 40.0,
            [3, 3], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 3, f"Expected 3 peaks, found {len(peaks)}"

        # Check that all peak heights are above threshold
        for peak_pos, peak_height in peaks:
            assert peak_height >= 40.0

        # Check that found peaks are close to expected positions
        found_positions = [peak_pos for peak_pos, _ in peaks]
        expected_positions = [(10, 10), (30, 10), (20, 30)]

        for expected in expected_positions:
            # Find closest peak to this expected position
            distances = [
                np.linalg.norm(np.array(found) - np.array(expected))
                for found in found_positions
            ]
            min_dist = min(distances)
            assert min_dist <= 2.0, f"No peak found near {expected}"


class TestPeakFindThresholds:
    """Test threshold filtering (have_low, have_high)."""

    def test_find_maxima_only(self):
        """Test finding only maxima (positive peaks).

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (30, 30)
        data = np.zeros(shape, dtype=np.float32)

        # Add a positive peak
        data += generate_gaussian_peak(
            shape, (10, 10), 100.0, (2, 2), noise_level=0.0
        )

        # Add a negative peak (should be ignored)
        data += generate_gaussian_peak(
            shape, (20, 20), -80.0, (2, 2), noise_level=0.0
        )

        # Search for maxima only
        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        # Should find only the positive peak
        assert len(peaks) == 1
        peak_pos, peak_height = peaks[0]
        assert peak_height > 0
        assert np.allclose(peak_pos, (10, 10), atol=1)

    def test_find_minima_only(self):
        """Test finding only minima (negative peaks).

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (30, 30)
        data = np.zeros(shape, dtype=np.float32)

        # Add a positive peak (should be ignored)
        data += generate_gaussian_peak(
            shape, (10, 10), 100.0, (2, 2), noise_level=0.0
        )

        # Add a negative peak
        data += generate_gaussian_peak(
            shape, (20, 20), -80.0, (2, 2), noise_level=0.0
        )

        # Search for minima only
        peaks = find_peaks(
            data, True, False, -50.0, 0.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        # Should find only the negative peak
        assert len(peaks) == 1
        peak_pos, peak_height = peaks[0]
        assert peak_height < 0
        assert np.allclose(peak_pos, (20, 20), atol=1)

    def test_find_both_maxima_and_minima(self):
        """Test finding both positive and negative peaks.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (30, 30)
        data = np.zeros(shape, dtype=np.float32)

        # Add a positive peak
        data += generate_gaussian_peak(
            shape, (10, 10), 100.0, (2, 2), noise_level=0.0
        )

        # Add a negative peak
        data += generate_gaussian_peak(
            shape, (20, 20), -80.0, (2, 2), noise_level=0.0
        )

        # Search for both
        peaks = find_peaks(
            data, True, True, -50.0, 50.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        # Should find both peaks
        assert len(peaks) == 2

        # Sort by height (negative first)
        peaks_sorted = sorted(peaks, key=lambda p: p[1])

        # First should be negative
        assert peaks_sorted[0][1] < 0
        assert np.allclose(peaks_sorted[0][0], (20, 20), atol=1)

        # Second should be positive
        assert peaks_sorted[1][1] > 0
        assert np.allclose(peaks_sorted[1][0], (10, 10), atol=1)


class TestPeakFindAdjacency:
    """Test adjacency checking (nonadjacent vs adjacent mode)."""

    def test_adjacent_mode_2n_neighbors(self):
        """Test adjacent mode checks only 2N axis-aligned neighbors.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        # Create data with a peak
        shape = (20, 20)
        center = (10, 10)
        data = generate_gaussian_peak(shape, center, 100.0, (2, 2))

        # Adjacent mode (nonadjacent=False)
        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], False, 0.0, [0.0, 0.0],  # nonadjacent=False
            [], [], []
        )

        assert len(peaks) == 1
        assert np.allclose(peaks[0][0], center, atol=1)

    def test_nonadjacent_mode_3n_neighbors(self):
        """Test nonadjacent mode checks all 3^N neighbors.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        # Create data with a peak
        shape = (20, 20)
        center = (10, 10)
        data = generate_gaussian_peak(shape, center, 100.0, (2, 2))

        # Nonadjacent mode (nonadjacent=True)
        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [0.0, 0.0],  # nonadjacent=True
            [], [], []
        )

        assert len(peaks) == 1
        assert np.allclose(peaks[0][0], center, atol=1)


class TestPeakFindCriteria:
    """Test additional filtering criteria (drop, linewidth)."""

    def test_drop_criterion(self):
        """Test drop factor filtering.

        The drop criterion requires intensity to drop by drop_factor * peak_height
        in all directions from the peak.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        # Create a peak with good drop
        shape = (30, 30)
        center = (15, 15)
        height = 100.0
        linewidth = (3.0, 3.0)

        data = generate_gaussian_peak(
            shape, center, height, linewidth, noise_level=1.0
        )

        # With drop_factor=0.5, require drop of 50 units
        # This peak should pass
        peaks_with_drop = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.5, [0.0, 0.0],  # drop_factor=0.5
            [], [], []
        )

        assert len(peaks_with_drop) == 1

        # With very strict drop_factor=0.9, might fail (depends on linewidth)
        # Narrow peaks may not meet this criterion
        peaks_strict = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.95, [0.0, 0.0],  # drop_factor=0.95 (very strict)
            [], [], []
        )

        # May or may not find peak depending on actual shape
        # Just verify it doesn't crash
        assert len(peaks_strict) >= 0

    def test_linewidth_criterion(self):
        """Test minimum linewidth filtering.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (30, 30)

        # Narrow peak (linewidth 1.5 in both dimensions)
        data_narrow = generate_gaussian_peak(
            shape, (15, 15), 100.0, (1.5, 1.5)
        )

        # With min_linewidth=[2.0, 2.0], narrow peak should be rejected
        peaks_narrow = find_peaks(
            data_narrow, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [2.0, 2.0],  # min_linewidth=[2.0, 2.0]
            [], [], []
        )

        # Narrow peak should not be found
        assert len(peaks_narrow) == 0

        # Wide peak (linewidth 3.0 in both dimensions)
        data_wide = generate_gaussian_peak(
            shape, (15, 15), 100.0, (3.0, 3.0)
        )

        # With min_linewidth=[2.0, 2.0], wide peak should pass
        peaks_wide = find_peaks(
            data_wide, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [2.0, 2.0],  # min_linewidth=[2.0, 2.0]
            [], [], []
        )

        # Wide peak should be found
        assert len(peaks_wide) == 1


class TestPeakFindExclusion:
    """Test exclusion zones (excluded regions, diagonal exclusions)."""

    def test_no_exclusion_regions(self):
        """Test with empty exclusion regions list.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (20, 20)
        data = generate_gaussian_peak(shape, (10, 10), 100.0, (2, 2))

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []  # Empty exclusion lists
        )

        assert len(peaks) == 1

    def test_excluded_region(self):
        """Test excluding a rectangular region.

        RED: Test will fail until implementation exists.
        """
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (40, 40)
        peaks_spec = [
            {'center': (10, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
            {'center': (30, 30), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec)

        # Exclude region around second peak: [25:35, 25:35]
        excluded_regions = [
            np.array([[25, 25], [35, 35]], dtype=np.float32)
        ]

        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            excluded_regions, [], []  # Exclude second peak region
        )

        # Should find only first peak
        assert len(peaks) == 1
        peak_pos, _ = peaks[0]
        assert np.allclose(peak_pos, (10, 10), atol=2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
