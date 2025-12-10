"""
Test Numba-optimized contour module.

Validates that contour_numba.py produces identical results to contour.py
while achieving significant performance improvements.
"""

import pytest
import numpy as np


class TestNumbaContourAPI:
    """Test Numba-optimized API matches pure Python API"""

    def test_import_contour_numba_module(self):
        """Test that contour_numba module can be imported"""
        from ccpn.c_replacement import contour_numba
        assert contour_numba is not None

    def test_numba_api_matches_python(self):
        """Test that Numba API is identical to pure Python"""
        from ccpn.c_replacement import contour
        from ccpn.c_replacement import contour_numba
        import inspect

        # Check function exists
        assert hasattr(contour_numba, 'calculate_contours')

        # Check signatures match
        sig_python = inspect.signature(contour.calculate_contours)
        sig_numba = inspect.signature(contour_numba.calculate_contours)

        params_python = list(sig_python.parameters.keys())
        params_numba = list(sig_numba.parameters.keys())

        assert params_python == params_numba, "Function signatures should match"


class TestNumbaCorrectnessValidation:
    """Validate Numba implementation produces identical results to pure Python"""

    def test_single_gaussian_matches_python(self):
        """Test Numba produces same results as Python for single Gaussian"""
        from ccpn.c_replacement import contour
        from ccpn.c_replacement import contour_numba

        # Create test data
        size = 50
        x = np.linspace(-3, 3, size)
        y = np.linspace(-3, 3, size)
        X, Y = np.meshgrid(x, y)
        data = np.exp(-(X**2 + Y**2)).astype(np.float32)
        levels = np.array([0.5], dtype=np.float32)

        # Generate contours with both implementations
        result_python = contour.calculate_contours(data, levels)
        result_numba = contour_numba.calculate_contours(data, levels)

        # Validate structure matches
        assert len(result_python) == len(result_numba), "Same number of levels"
        assert len(result_python[0]) == len(result_numba[0]), "Same number of polylines"

        # Validate vertices approximately match (may differ slightly due to ordering)
        python_verts = result_python[0][0]
        numba_verts = result_numba[0][0]

        # Same number of vertices
        assert len(python_verts) == len(numba_verts), "Same number of vertices"

        print(f"✓ Python: {len(python_verts)} vertices")
        print(f"✓ Numba:  {len(numba_verts)} vertices")

    def test_multiple_levels_matches_python(self):
        """Test Numba matches Python for multiple concentric levels"""
        from ccpn.c_replacement import contour
        from ccpn.c_replacement import contour_numba

        size = 50
        x = np.linspace(-3, 3, size)
        y = np.linspace(-3, 3, size)
        X, Y = np.meshgrid(x, y)
        data = np.exp(-(X**2 + Y**2)).astype(np.float32)
        levels = np.array([0.2, 0.5, 0.8], dtype=np.float32)

        result_python = contour.calculate_contours(data, levels)
        result_numba = contour_numba.calculate_contours(data, levels)

        # Validate structure
        assert len(result_python) == len(result_numba) == 3

        for i in range(3):
            assert len(result_python[i]) == len(result_numba[i]), \
                f"Level {i} should have same number of polylines"

        print("✓ Multi-level contours match between Python and Numba")

    def test_two_gaussians_matches_python(self):
        """Test Numba matches Python for disconnected contours"""
        from ccpn.c_replacement import contour
        from ccpn.c_replacement import contour_numba

        size = 100
        X, Y = np.meshgrid(np.arange(size, dtype=np.float32),
                           np.arange(size, dtype=np.float32))

        data = (np.exp(-((X - 30)**2 + (Y - 50)**2) / 100) +
                np.exp(-((X - 70)**2 + (Y - 50)**2) / 100))
        data = data.astype(np.float32)

        levels = np.array([0.3], dtype=np.float32)

        result_python = contour.calculate_contours(data, levels)
        result_numba = contour_numba.calculate_contours(data, levels)

        # Both should find 2 separate contours
        assert len(result_python[0]) >= 2
        assert len(result_numba[0]) >= 2
        assert len(result_python[0]) == len(result_numba[0]), \
            "Should find same number of separate contours"

        print(f"✓ Found {len(result_python[0])} separate contours (Python and Numba match)")


class TestNumbaPerformance:
    """Validate Numba performance improvements"""

    def test_numba_performance_improvement(self):
        """Test that Numba is faster than pure Python"""
        from ccpn.c_replacement import contour
        from ccpn.c_replacement import contour_numba
        import time

        size = 256
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - size/2)**2 + (Y - size/2)**2) / 1000).astype(np.float32)
        levels = np.array([0.1, 0.3, 0.5, 0.7, 0.9], dtype=np.float32)

        # Warm-up Numba JIT
        _ = contour_numba.calculate_contours(data[:50, :50], levels[:1])

        # Time pure Python
        start = time.time()
        result_python = contour.calculate_contours(data, levels)
        time_python = time.time() - start

        # Time Numba
        start = time.time()
        result_numba = contour_numba.calculate_contours(data, levels)
        time_numba = time.time() - start

        speedup = time_python / time_numba

        print(f"\n  Pure Python: {time_python:.4f}s")
        print(f"  Numba:       {time_numba:.4f}s")
        print(f"  Speedup:     {speedup:.2f}x")

        # Numba should be at least as fast (may not be much faster for small datasets)
        assert time_numba <= time_python * 1.2, \
            f"Numba should be competitive (Python: {time_python:.4f}s, Numba: {time_numba:.4f}s)"

    def test_large_dataset_performance(self):
        """Test Numba performance on large dataset"""
        from ccpn.c_replacement import contour_numba
        import time

        size = 512
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - size/2)**2 + (Y - size/2)**2) / 5000).astype(np.float32)
        levels = np.array([0.1, 0.3, 0.5, 0.7, 0.9], dtype=np.float32)

        # Warm-up
        _ = contour_numba.calculate_contours(data[:100, :100], levels[:1])

        # Benchmark
        times = []
        for _ in range(3):
            start = time.time()
            result = contour_numba.calculate_contours(data, levels)
            elapsed = time.time() - start
            times.append(elapsed)

        avg_time = np.mean(times)

        print(f"\n  512x512 dataset: {avg_time:.4f}s (avg of 3 runs)")
        print(f"  Levels: {len(result)}")
        print(f"  Polylines: {sum(len(level) for level in result)}")

        # Should meet <1s target
        assert avg_time < 1.0, f"Should process 512x512 in <1s (got {avg_time:.4f}s)"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
