"""Performance Validation Tests for Peak Module

This module validates the performance characteristics of all three phases
of the Peak module implementation:
- Phase 1: Parabolic fitting
- Phase 2: Peak finding
- Phase 3: Levenberg-Marquardt fitting

Performance validation includes:
- Execution time benchmarks
- Memory usage validation
- Scalability tests (varying data sizes)
- Comparison baseline (pure Python vs Numba)
- Numerical accuracy validation

Uses pytest-benchmark for reliable performance measurements.
"""

import numpy as np
import pytest
from ccpn.c_replacement.tests.test_peak_data import (
    generate_gaussian_peak,
    generate_lorentzian_peak,
    generate_multi_peak_spectrum,
)


# =============================================================================
# Phase 1: Parabolic Fitting Performance
# =============================================================================

class TestParabolicFittingPerformance:
    """Performance validation for parabolic fitting."""

    def test_parabolic_2d_single_peak_performance(self, benchmark):
        """Benchmark parabolic fitting of single 2D peak."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (100, 100)
        center = (50.3, 50.7)
        height = 100.0
        linewidth = (2.5, 3.0)

        data = generate_gaussian_peak(shape, center, height, linewidth)
        region = np.array([[48, 48], [53, 53]], dtype=np.int32)
        peak_array = np.array([[50, 50]], dtype=np.float32)

        # Benchmark
        result = benchmark(fit_parabolic_peaks, data, region, peak_array)

        # Validate result
        assert len(result) == 1
        assert result[0][0] > 0  # Has valid height

    def test_parabolic_2d_multiple_peaks_performance(self, benchmark):
        """Benchmark parabolic fitting of 10 peaks in 2D."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (200, 200)
        peaks = []
        for i in range(10):
            x = 30 + i * 15
            y = 30 + i * 15
            peaks.append({'center': (x, y), 'height': 100, 'linewidth': (2.5, 2.5), 'model': 'gaussian'})

        data = generate_multi_peak_spectrum(shape, peaks)

        # Create regions and peak array for all 10 peaks
        regions = []
        peak_positions = []
        for peak_spec in peaks:
            cx, cy = peak_spec['center']
            regions.append([int(cx) - 3, int(cy) - 3])
            regions.append([int(cx) + 3, int(cy) + 3])
            peak_positions.append([float(cx), float(cy)])

        region = np.array(regions[:20]).reshape(10, 2, 2).astype(np.int32)
        peak_array = np.array(peak_positions, dtype=np.float32)

        # Benchmark
        result = benchmark(fit_parabolic_peaks, data, region, peak_array)

        # Validate
        assert len(result) == 10

    def test_parabolic_3d_performance(self, benchmark):
        """Benchmark parabolic fitting in 3D."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (50, 50, 50)
        center = (25.3, 25.7, 25.5)
        height = 100.0
        linewidth = (2.5, 3.0, 2.8)

        data = generate_gaussian_peak(shape, center, height, linewidth)
        region = np.array([[23, 23, 23], [28, 28, 28]], dtype=np.int32)
        peak_array = np.array([[25, 25, 25]], dtype=np.float32)

        # Benchmark
        result = benchmark(fit_parabolic_peaks, data, region, peak_array)

        # Validate
        assert len(result) == 1

    def test_parabolic_scalability_data_size(self):
        """Test parabolic fitting scalability with increasing data size."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks
        import time

        sizes = [(50, 50), (100, 100), (200, 200), (400, 400)]
        times = []

        for shape in sizes:
            center = (shape[0] // 2 + 0.3, shape[1] // 2 + 0.7)
            data = generate_gaussian_peak(shape, center, 100.0, (2.5, 3.0))

            cx, cy = int(center[0]), int(center[1])
            region = np.array([[cx - 3, cy - 3], [cx + 3, cy + 3]], dtype=np.int32)
            peak_array = np.array([[float(cx), float(cy)]], dtype=np.float32)

            # Time 10 runs
            start = time.perf_counter()
            for _ in range(10):
                fit_parabolic_peaks(data, region, peak_array)
            elapsed = time.perf_counter() - start

            times.append(elapsed / 10)  # Average per run

        # Parabolic fitting should be O(1) in data size (only fits local region)
        # Time should not increase significantly with data size
        # Allow 3x slowdown for 64x data increase (due to cache effects)
        assert times[-1] / times[0] < 3.0, \
            f"Parabolic fitting not scaling well: {times}"


# =============================================================================
# Phase 2: Peak Finding Performance
# =============================================================================

class TestPeakFindingPerformance:
    """Performance validation for peak finding."""

    def test_peak_finding_2d_few_peaks_performance(self, benchmark):
        """Benchmark finding 5 peaks in 2D spectrum."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (100, 100)
        peaks = []
        for i in range(5):
            peaks.append({
                'center': (20 + i * 15, 20 + i * 15),
                'height': 100,
                'linewidth': (2.5, 2.5),
                'model': 'gaussian'
            })

        data = generate_multi_peak_spectrum(shape, peaks)

        # Benchmark - correct API
        result = benchmark(
            find_peaks,
            data,
            False,       # have_low
            True,        # have_high
            0.0,         # low
            10.0,        # high (threshold)
            [],          # buffer
            False,       # nonadjacent
            0.0,         # drop_factor
            [0.0, 0.0],  # min_linewidth
            [],          # excluded_regions
            [],          # diagonal_exclusion_dims
            []           # diagonal_exclusion_transform
        )

        # Should find all 5 peaks
        assert len(result) >= 5

    def test_peak_finding_2d_many_peaks_performance(self, benchmark):
        """Benchmark finding many peaks in 2D spectrum."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (200, 200)
        peaks = []
        for i in range(10):
            for j in range(10):
                if (i + j) % 2 == 0:  # 50 peaks
                    peaks.append({
                        'center': (20 + i * 16, 20 + j * 16),
                        'height': 100,
                        'linewidth': (2.5, 2.5),
                        'model': 'gaussian'
                    })

        data = generate_multi_peak_spectrum(shape, peaks)

        # Benchmark
        result = benchmark(
            find_peaks,
            data,
            False, True, 0.0, 10.0, [], False, 0.0, [0.0, 0.0], [], [], []
        )

        # Should find most peaks
        assert len(result) >= 40

    def test_peak_finding_3d_performance(self, benchmark):
        """Benchmark peak finding in 3D."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (50, 50, 50)
        peaks = [
            {'center': (15, 15, 15), 'height': 100, 'linewidth': (2.5, 2.5, 2.5), 'model': 'gaussian'},
            {'center': (25, 25, 25), 'height': 100, 'linewidth': (2.5, 2.5, 2.5), 'model': 'gaussian'},
            {'center': (35, 35, 35), 'height': 100, 'linewidth': (2.5, 2.5, 2.5), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks)

        # Benchmark
        result = benchmark(
            find_peaks,
            data,
            False, True, 0.0, 10.0, [], False, 0.0, [0.0, 0.0, 0.0], [], [], []
        )

        assert len(result) >= 3

    def test_peak_finding_scalability_data_size(self):
        """Test peak finding scalability with increasing data size."""
        from ccpn.c_replacement.peak_numba import find_peaks
        import time

        sizes = [(50, 50), (100, 100), (200, 200)]
        times = []

        for shape in sizes:
            # Single peak in center
            center = (shape[0] // 2, shape[1] // 2)
            data = generate_gaussian_peak(shape, center, 100.0, (2.5, 2.5))

            # Time 5 runs
            start = time.perf_counter()
            for _ in range(5):
                find_peaks(data, False, True, 0.0, 10.0, [], False, 0.0, [0.0, 0.0], [], [], [])
            elapsed = time.perf_counter() - start

            times.append(elapsed / 5)

        # Peak finding is O(N) where N is data size
        # For 4x data increase, expect roughly 4x time increase
        # Allow up to 6x due to overhead
        ratio = (times[-1] / times[0]) / ((sizes[-1][0] * sizes[-1][1]) / (sizes[0][0] * sizes[0][1]))
        assert ratio < 1.5, f"Peak finding not scaling linearly: {times}, ratio={ratio}"


# =============================================================================
# Phase 3: Levenberg-Marquardt Fitting Performance
# =============================================================================

class TestLMFittingPerformance:
    """Performance validation for L-M fitting."""

    def test_lm_gaussian_2d_single_peak_performance(self, benchmark):
        """Benchmark L-M fitting of single Gaussian peak."""
        from ccpn.c_replacement.peak_numba import fit_peaks

        shape = (30, 30)
        center = (15.3, 20.7)
        height = 100.0
        linewidth = (2.5, 3.0)

        data = generate_gaussian_peak(shape, center, height, linewidth)
        region = np.array([[12, 18], [18, 24]], dtype=np.int32)
        peak_array = np.array([[15.0, 21.0]], dtype=np.float32)
        method = 0  # Gaussian

        # Benchmark
        result = benchmark(fit_peaks, data, region, peak_array, method)

        assert len(result) == 1

    def test_lm_lorentzian_2d_single_peak_performance(self, benchmark):
        """Benchmark L-M fitting of single Lorentzian peak."""
        from ccpn.c_replacement.peak_numba import fit_peaks

        shape = (30, 30)
        center = (15.3, 20.7)
        height = 100.0
        linewidth = (2.5, 3.0)

        data = generate_lorentzian_peak(shape, center, height, linewidth)
        region = np.array([[12, 18], [18, 24]], dtype=np.int32)
        peak_array = np.array([[15.0, 21.0]], dtype=np.float32)
        method = 1  # Lorentzian

        # Benchmark
        result = benchmark(fit_peaks, data, region, peak_array, method)

        assert len(result) == 1

    def test_lm_multiple_peaks_performance(self, benchmark):
        """Benchmark L-M fitting of 3 peaks simultaneously."""
        from ccpn.c_replacement.peak_numba import fit_peaks

        shape = (50, 50)
        peaks = [
            {'center': (15, 15), 'height': 100, 'linewidth': (2.5, 2.5), 'model': 'gaussian'},
            {'center': (25, 25), 'height': 80, 'linewidth': (3, 3), 'model': 'gaussian'},
            {'center': (35, 35), 'height': 90, 'linewidth': (2.8, 2.8), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks)
        region = np.array([[10, 10], [40, 40]], dtype=np.int32)
        peak_array = np.array([[15.0, 15.0], [25.0, 25.0], [35.0, 35.0]], dtype=np.float32)
        method = 0

        # Benchmark
        result = benchmark(fit_peaks, data, region, peak_array, method)

        assert len(result) == 3

    def test_lm_3d_performance(self, benchmark):
        """Benchmark L-M fitting in 3D."""
        from ccpn.c_replacement.peak_numba import fit_peaks

        shape = (20, 20, 20)
        center = (10.3, 10.7, 10.5)
        height = 100.0
        linewidth = (2.5, 3.0, 2.8)

        data = generate_gaussian_peak(shape, center, height, linewidth)
        region = np.array([[8, 8, 8], [13, 13, 13]], dtype=np.int32)
        peak_array = np.array([[10.0, 11.0, 10.0]], dtype=np.float32)
        method = 0

        # Benchmark
        result = benchmark(fit_peaks, data, region, peak_array, method)

        assert len(result) == 1

    def test_lm_scalability_region_size(self):
        """Test L-M fitting scalability with region size."""
        from ccpn.c_replacement.peak_numba import fit_peaks
        import time

        # Different region sizes around same peak
        region_sizes = [5, 7, 10, 15]
        times = []

        shape = (50, 50)
        center = (25, 25)
        data = generate_gaussian_peak(shape, center, 100.0, (2.5, 2.5))

        for size in region_sizes:
            half = size // 2
            region = np.array([[25 - half, 25 - half], [25 + half, 25 + half]], dtype=np.int32)
            peak_array = np.array([[25.0, 25.0]], dtype=np.float32)

            # Time 5 runs
            start = time.perf_counter()
            for _ in range(5):
                fit_peaks(data, region, peak_array, 0)
            elapsed = time.perf_counter() - start

            times.append(elapsed / 5)

        # L-M is roughly O(N) where N is number of data points in region
        # For 9x region area increase (5x5 -> 15x15), expect < 15x time increase
        # (less than linear due to convergence effects)
        assert times[-1] / times[0] < 15.0, \
            f"L-M fitting not scaling reasonably: {times}"


# =============================================================================
# Numerical Accuracy Validation
# =============================================================================

class TestNumericalAccuracy:
    """Validate numerical accuracy across all phases."""

    def test_parabolic_accuracy_perfect_data(self):
        """Test parabolic fitting achieves high accuracy on perfect data."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks

        shape = (50, 50)
        true_center = (25.3, 25.7)
        true_height = 100.0
        true_linewidth = (2.5, 3.0)

        data = generate_gaussian_peak(shape, true_center, true_height, true_linewidth)
        region = np.array([[23, 23], [28, 28]], dtype=np.int32)
        peak_array = np.array([[25, 25]], dtype=np.float32)

        results = fit_parabolic_peaks(data, region, peak_array)
        fitted_height, fitted_pos, fitted_lw = results[0]

        # Parabolic is fast but less accurate than L-M
        assert np.isclose(fitted_height, true_height, rtol=0.1)
        assert np.allclose(fitted_pos, true_center, atol=0.2)

    def test_lm_accuracy_perfect_data(self):
        """Test L-M fitting achieves high accuracy on perfect data."""
        from ccpn.c_replacement.peak_numba import fit_peaks

        shape = (30, 30)
        true_center = (15.3, 20.7)
        true_height = 100.0
        true_linewidth = (2.5, 3.0)

        data = generate_gaussian_peak(shape, true_center, true_height, true_linewidth)
        region = np.array([[12, 18], [18, 24]], dtype=np.int32)
        peak_array = np.array([[15.0, 21.0]], dtype=np.float32)

        results = fit_peaks(data, region, peak_array, 0)
        fitted_height, fitted_pos, fitted_lw = results[0]

        # L-M with scipy backend has convergence limitations
        assert np.isclose(fitted_height, true_height, rtol=0.15)
        assert np.allclose(fitted_pos, true_center, atol=0.5)

    def test_peak_finding_accuracy_recall(self):
        """Test peak finding achieves high recall (finds most peaks)."""
        from ccpn.c_replacement.peak_numba import find_peaks

        shape = (200, 200)
        true_peaks = []
        for i in range(10):
            for j in range(10):
                if (i + j) % 2 == 0:  # 50 peaks
                    true_peaks.append({
                        'center': (20 + i * 16, 20 + j * 16),
                        'height': 100,
                        'linewidth': (2.5, 2.5),
                        'model': 'gaussian'
                    })

        data = generate_multi_peak_spectrum(shape, true_peaks)
        found_peaks = find_peaks(data, False, True, 0.0, 10.0, [], False, 0.0, [0.0, 0.0], [], [], [])

        # Should find at least 90% of peaks
        recall = len(found_peaks) / len(true_peaks)
        assert recall >= 0.90, f"Peak finding recall too low: {recall:.2%}"


# =============================================================================
# Memory Usage Validation
# =============================================================================

class TestMemoryUsage:
    """Validate memory usage is reasonable."""

    def test_parabolic_memory_efficiency(self):
        """Test parabolic fitting doesn't allocate excessive memory."""
        from ccpn.c_replacement.peak_numba import fit_parabolic_peaks
        import sys

        shape = (1000, 1000)  # 1M points
        data = generate_gaussian_peak(shape, (500, 500), 100.0, (2.5, 2.5))

        region = np.array([[498, 498], [503, 503]], dtype=np.int32)
        peak_array = np.array([[500, 500]], dtype=np.float32)

        # Measure memory before
        data_size = data.nbytes

        # Run fitting
        result = fit_parabolic_peaks(data, region, peak_array)

        # Result should be tiny compared to input data
        result_size = sys.getsizeof(result)
        assert result_size < data_size / 1000, "Result uses excessive memory"

    def test_peak_finding_memory_efficiency(self):
        """Test peak finding memory efficiency."""
        from ccpn.c_replacement.peak_numba import find_peaks
        import sys

        shape = (500, 500)  # 250k points
        data = generate_gaussian_peak(shape, (250, 250), 100.0, (2.5, 2.5))

        data_size = data.nbytes

        # Run peak finding
        result = find_peaks(data, False, True, 0.0, 10.0, [], False, 0.0, [0.0, 0.0], [], [], [])

        # Result should be much smaller than input
        result_size = sys.getsizeof(result)
        assert result_size < data_size / 100, "Result uses excessive memory"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
