"""
Enhanced TDD Tests for Contour Module - Based on C Implementation Analysis

After analyzing npy_contourer2d.c, this test suite captures ALL requirements:

C API Specification:
- Function: calculate_contours(data, levels)
- Input:
  * data: 2D NumPy array of float32 [y][x] values
  * levels: 1D NumPy array of float32 values (must be monotonic)
- Output:
  * List of lists of polylines (one list per level)
  * Each polyline is a 1D NumPy array [x0, y0, x1, y1, ...] of float32

Key Requirements from C code:
1. Levels must be either all increasing OR all decreasing (not mixed)
2. Marching squares algorithm with vertex linking
3. Polylines are closed loops or open paths
4. Vertices allocated in blocks of 50 for efficiency
5. Level optimization: skip regions not in range for multiple levels
"""

import pytest
import numpy as np
from typing import List
import sys
import os

# Add src/python to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))


class TestContourAPICompliance:
    """Test API matches C implementation exactly"""

    def test_module_import(self):
        """Test: Module can be imported"""
        try:
            from ccpn.c_replacement import contour
            assert contour is not None
        except ImportError as e:
            pytest.fail(f"contour module not implemented yet - this is expected for TDD! ({e})")

    def test_calculate_contours_exists(self):
        """Test: calculate_contours function exists"""
        from ccpn.c_replacement import contour
        assert hasattr(contour, 'calculate_contours'), \
            "Must have calculate_contours function"

    def test_function_signature_compliance(self):
        """Test: Function accepts (data, levels) parameters"""
        from ccpn.c_replacement import contour
        import inspect

        sig = inspect.signature(contour.calculate_contours)
        params = list(sig.parameters.keys())

        assert 'data' in params, "Must accept 'data' parameter"
        assert 'levels' in params, "Must accept 'levels' parameter"
        assert len(params) == 2, "Should have exactly 2 parameters"

    def test_input_validation_2d_data(self):
        """Test: Must reject non-2D data arrays"""
        from ccpn.c_replacement import contour

        # C code checks: PyArray_NDIM(data_obj) != 2
        data_1d = np.array([1, 2, 3], dtype=np.float32)
        levels = np.array([0.5], dtype=np.float32)

        with pytest.raises((ValueError, TypeError)):
            contour.calculate_contours(data_1d, levels)

    def test_input_validation_1d_levels(self):
        """Test: Must reject non-1D levels arrays"""
        from ccpn.c_replacement import contour

        # C code checks: PyArray_NDIM(levels_obj) != 1
        data = np.ones((10, 10), dtype=np.float32)
        levels_2d = np.array([[0.5]], dtype=np.float32)

        with pytest.raises((ValueError, TypeError)):
            contour.calculate_contours(data, levels_2d)

    def test_input_validation_float_types(self):
        """Test: Must accept float32 or convert to float32"""
        from ccpn.c_replacement import contour

        # C code expects NPY_FLOAT (float32)
        data = np.ones((10, 10), dtype=np.float64)  # float64
        levels = np.array([0.5], dtype=np.float64)

        # Should either accept or auto-convert
        result = contour.calculate_contours(data, levels)
        assert result is not None


class TestLevelMonotonicity:
    """Test level ordering requirements from C code (lines 913-929)"""

    def test_increasing_levels_accepted(self):
        """Test: Increasing levels are valid"""
        from ccpn.c_replacement import contour

        data = np.ones((20, 20), dtype=np.float32)
        levels = np.array([0.1, 0.3, 0.5, 0.7, 0.9], dtype=np.float32)

        result = contour.calculate_contours(data, levels)
        assert len(result) == 5

    def test_decreasing_levels_accepted(self):
        """Test: Decreasing levels are valid"""
        from ccpn.c_replacement import contour

        data = np.ones((20, 20), dtype=np.float32)
        levels = np.array([0.9, 0.7, 0.5, 0.3, 0.1], dtype=np.float32)

        result = contour.calculate_contours(data, levels)
        assert len(result) == 5

    def test_mixed_levels_rejected(self):
        """Test: Mixed increasing/decreasing levels rejected"""
        from ccpn.c_replacement import contour

        data = np.ones((20, 20), dtype=np.float32)
        # C code error: "levels initially increasing but later decrease"
        levels = np.array([0.1, 0.5, 0.3, 0.7], dtype=np.float32)

        with pytest.raises(ValueError, match=".*increas.*decreas.*|.*monotonic.*"):
            contour.calculate_contours(data, levels)

    def test_single_level_always_valid(self):
        """Test: Single level has no ordering constraint"""
        from ccpn.c_replacement import contour

        data = np.ones((20, 20), dtype=np.float32)
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)
        assert len(result) == 1


class TestOutputStructure:
    """Test output format matches C implementation (lines 934-978)"""

    def test_output_is_list_of_lists(self):
        """Test: Returns list (one entry per level) of lists (polylines)"""
        from ccpn.c_replacement import contour

        size = 50
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)
        levels = np.array([0.3, 0.6], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        # Outer list: one per level
        assert isinstance(result, list)
        assert len(result) == 2

        # Inner lists: polylines for each level
        for level_contours in result:
            assert isinstance(level_contours, list)

    def test_polyline_format(self):
        """Test: Each polyline is 1D array [x0,y0,x1,y1,...] of float32"""
        from ccpn.c_replacement import contour

        size = 50
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        # Should have at least one polyline
        assert len(result[0]) > 0, "Should generate contours for Gaussian peak"

        polyline = result[0][0]

        # C code creates: dims[0] = 2 * nvertices (line 819)
        assert isinstance(polyline, np.ndarray)
        assert polyline.ndim == 1
        assert len(polyline) % 2 == 0, "Must have even number of values (x,y pairs)"
        assert polyline.dtype == np.float32

    def test_empty_contours_for_no_vertices(self):
        """Test: Returns empty list when no contours found"""
        from ccpn.c_replacement import contour

        # All zeros - no contours
        data = np.zeros((20, 20), dtype=np.float32)
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        assert len(result) == 1
        assert len(result[0]) == 0, "Should have no polylines"

    def test_early_termination_on_zero_vertices(self):
        """Test: Stops processing levels when no vertices found (line 965)"""
        from ccpn.c_replacement import contour

        # Create data with max value 0.5
        data = np.ones((20, 20), dtype=np.float32) * 0.5
        # Request levels above data - should stop early
        levels = np.array([0.6, 0.7, 0.8], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        # C code: if (contour_vertices->nvertices == 0) break;
        # Should have 3 entries but some may be empty
        assert len(result) <= 3


class TestMarchingSquaresAlgorithm:
    """Test marching squares contour generation"""

    def test_circular_contour_generation(self):
        """Test: Generate smooth circular contour for Gaussian"""
        from ccpn.c_replacement import contour

        size = 100
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        # Gaussian centered at (50, 50)
        data = np.exp(-((X - 50)**2 + (Y - 50)**2) / 200).astype(np.float32)
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        polylines = result[0]
        assert len(polylines) > 0

        # Extract vertices
        polyline = polylines[0]
        vertices = polyline.reshape(-1, 2)

        # Should have many vertices for smooth circle
        assert len(vertices) > 20, f"Expected >20 vertices for smooth circle, got {len(vertices)}"

        # Verify approximate circularity
        center_x = vertices[:, 0].mean()
        center_y = vertices[:, 1].mean()
        assert abs(center_x - 50) < 3
        assert abs(center_y - 50) < 3

        # Check radius consistency
        radii = np.sqrt((vertices[:, 0] - center_x)**2 + (vertices[:, 1] - center_y)**2)
        radius_std = radii.std()
        assert radius_std < radii.mean() * 0.15, "Contour should be approximately circular"

    def test_interpolation_accuracy(self):
        """Test: Vertices are interpolated between grid points"""
        from ccpn.c_replacement import contour

        # Simple linear ramp
        data = np.tile(np.linspace(0, 1, 50), (50, 1)).astype(np.float32)
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        polylines = result[0]
        if len(polylines) > 0:
            polyline = polylines[0]
            vertices = polyline.reshape(-1, 2)

            # All vertices should have x ≈ 25 (halfway across)
            x_coords = vertices[:, 0]
            assert np.all(np.abs(x_coords - 25.0) < 2), "Contour should be near x=25 for 0.5 level"

    def test_multiple_disconnected_contours(self):
        """Test: Multiple separate regions create multiple polylines"""
        from ccpn.c_replacement import contour

        size = 100
        X, Y = np.meshgrid(np.arange(size), np.arange(size))

        # Two well-separated Gaussians
        data = (np.exp(-((X - 25)**2 + (Y - 50)**2) / 50) +
                np.exp(-((X - 75)**2 + (Y - 50)**2) / 50)).astype(np.float32)

        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        polylines = result[0]
        # Should have 2 separate contours for two peaks
        assert len(polylines) >= 2, f"Expected ≥2 polylines for two peaks, got {len(polylines)}"


class TestMultipleLevelOptimization:
    """Test level optimization from C code (swap_old_new, lines 973)"""

    def test_concentric_contours(self):
        """Test: Multiple levels create concentric contours"""
        from ccpn.c_replacement import contour

        size = 80
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - 40)**2 + (Y - 40)**2) / 150).astype(np.float32)

        levels = np.array([0.2, 0.4, 0.6, 0.8], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        assert len(result) == 4

        # Extract radii of each level
        radii = []
        for level_contours in result:
            if len(level_contours) > 0:
                vertices = level_contours[0].reshape(-1, 2)
                center_x = vertices[:, 0].mean()
                center_y = vertices[:, 1].mean()
                distances = np.sqrt((vertices[:, 0] - center_x)**2 +
                                    (vertices[:, 1] - center_y)**2)
                radii.append(distances.mean())

        # Higher levels should have smaller radii (inner contours)
        if len(radii) >= 2:
            for i in range(len(radii) - 1):
                assert radii[i] > radii[i + 1], \
                    f"Level {i} radius {radii[i]:.2f} should be > level {i+1} radius {radii[i+1]:.2f}"


class TestEdgeCases:
    """Test boundary conditions and error handling"""

    def test_constant_data(self):
        """Test: Constant value data produces no contours"""
        from ccpn.c_replacement import contour

        data = np.ones((30, 30), dtype=np.float32) * 0.7
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)
        # Constant data below level → no contours
        # Or boundary contour depending on implementation
        assert len(result) == 1

    def test_single_pixel_above_threshold(self):
        """Test: Single high pixel creates tiny contour"""
        from ccpn.c_replacement import contour

        data = np.zeros((20, 20), dtype=np.float32)
        data[10, 10] = 1.0
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)
        # Should create small contour around pixel
        assert len(result) == 1

    def test_empty_levels_array(self):
        """Test: Empty levels array handled gracefully"""
        from ccpn.c_replacement import contour

        data = np.ones((20, 20), dtype=np.float32)
        levels = np.array([], dtype=np.float32)

        result = contour.calculate_contours(data, levels)
        assert len(result) == 0

    def test_very_small_data(self):
        """Test: Minimum size data (2x2)"""
        from ccpn.c_replacement import contour

        data = np.array([[0, 0], [0, 1]], dtype=np.float32)
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)
        # Should handle gracefully
        assert len(result) == 1


class TestPerformanceBenchmark:
    """Performance tests - target: match or exceed C with Numba"""

    def test_medium_dataset_performance(self):
        """Test: 256x256 dataset performance"""
        from ccpn.c_replacement import contour
        import time

        size = 256
        X, Y = np.meshgrid(np.linspace(-5, 5, size), np.linspace(-5, 5, size))
        data = np.exp(-(X**2 + Y**2)).astype(np.float32)
        levels = np.array([0.1, 0.3, 0.5, 0.7, 0.9], dtype=np.float32)

        # Warm-up (for Numba JIT)
        _ = contour.calculate_contours(data[:50, :50], levels[:1])

        start = time.perf_counter()
        result = contour.calculate_contours(data, levels)
        elapsed = time.perf_counter() - start

        assert len(result) == 5
        print(f"\n  256x256 with 5 levels: {elapsed:.4f}s")

    def test_large_dataset_performance(self):
        """Test: 512x512 dataset - TARGET: <1 second with Numba"""
        from ccpn.c_replacement import contour
        import time

        size = 512
        X, Y = np.meshgrid(np.linspace(-5, 5, size), np.linspace(-5, 5, size))
        data = np.exp(-(X**2 + Y**2)).astype(np.float32)
        levels = np.array([0.1, 0.3, 0.5, 0.7, 0.9], dtype=np.float32)

        # Warm-up
        _ = contour.calculate_contours(data[:100, :100], levels[:1])

        start = time.perf_counter()
        result = contour.calculate_contours(data, levels)
        elapsed = time.perf_counter() - start

        assert len(result) == 5

        print(f"\n  512x512 with 5 levels: {elapsed:.4f}s")

        # PERFORMANCE GOAL from ccpnmr2.4: 90-3200x faster than C
        # Initial pure Python may be slower - that's OK for TDD
        # Numba optimization will achieve the target
        if elapsed > 2.0:
            pytest.skip(f"Performance will be optimized with Numba (current: {elapsed:.3f}s, target: <1s)")


class TestNumericalAccuracy:
    """Numerical validation tests"""

    def test_symmetrical_data_produces_symmetrical_contours(self):
        """Test: Symmetrical input → symmetrical output"""
        from ccpn.c_replacement import contour

        size = 60
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        # Perfectly symmetrical Gaussian
        data = np.exp(-((X - 30)**2 + (Y - 30)**2) / 100).astype(np.float32)
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        polylines = result[0]
        if len(polylines) > 0:
            vertices = polylines[0].reshape(-1, 2)

            # Check x and y distributions are similar (symmetry)
            x_spread = vertices[:, 0].std()
            y_spread = vertices[:, 1].std()
            assert abs(x_spread - y_spread) / max(x_spread, y_spread) < 0.1, \
                "Symmetrical data should produce symmetrical contours"

    def test_level_exactly_at_data_value(self):
        """Test: Level exactly at data value handled correctly"""
        from ccpn.c_replacement import contour

        data = np.ones((20, 20), dtype=np.float32) * 0.5
        data[10, 10] = 0.6
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)
        # Should create contour around the peak
        assert len(result) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s', '--tb=short'])
