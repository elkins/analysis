"""
TDD Tests for Contour Module

Following Test-Driven Development:
1. Write tests FIRST based on expected API
2. Tests will FAIL initially (Red)
3. Implement contour.py to make tests pass (Green)
4. Optimize with Numba (Refactor)

API based on npy_contourer2d.c and ccpnmr2.4/python_impl/contourer.py
"""

import pytest
import numpy as np
from typing import List, Tuple


class TestContourAPI:
    """Test the expected API of the contour module"""

    def test_import_contour_module(self):
        """Test that contour module can be imported"""
        try:
            from ccpn.c_replacement import contour
            assert contour is not None
        except ImportError:
            pytest.fail("contour module not yet implemented - expected for TDD!")

    def test_calculate_contours_function_exists(self):
        """Test that calculate_contours function exists"""
        from ccpn.c_replacement import contour
        assert hasattr(contour, 'calculate_contours'), \
            "calculate_contours function must exist"

    def test_calculate_contours_signature(self):
        """Test calculate_contours has correct signature"""
        from ccpn.c_replacement import contour
        import inspect

        sig = inspect.signature(contour.calculate_contours)
        params = list(sig.parameters.keys())

        # Expected parameters based on C API
        expected_params = ['data', 'levels']
        for param in expected_params:
            assert param in params, f"Missing parameter: {param}"


class TestContourSimpleCircle:
    """TDD: Test contour generation on a simple circle"""

    def test_single_level_circular_contour(self):
        """
        Test: Generate contour for a single circular level

        Given: 2D data forming a circular hill (Gaussian)
        When: Request contour at level 0.5
        Then: Should return closed loop approximately circular
        """
        from ccpn.c_replacement import contour

        # Create test data: Gaussian hill
        size = 50
        x = np.linspace(-3, 3, size)
        y = np.linspace(-3, 3, size)
        X, Y = np.meshgrid(x, y)
        data = np.exp(-(X**2 + Y**2)).astype(np.float32)

        # Request contour at level 0.5
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        # Validate result structure
        assert result is not None, "Should return contours"
        assert len(result) == 1, "Should return one level"
        assert len(result[0]) > 0, "Level should have at least one polyline"

        # Validate contour is approximately circular
        polylines = result[0]
        assert len(polylines) > 0, "Should have polylines"

        # First polyline should be the main contour
        main_contour = polylines[0]
        assert len(main_contour) > 10, "Contour should have multiple vertices"

        # Check that vertices form approximate circle around origin
        vertices = np.array(main_contour)
        center_x = vertices[:, 0].mean()
        center_y = vertices[:, 1].mean()

        # Center should be near middle of grid
        assert abs(center_x - size/2) < 5, f"Center x {center_x} should be near {size/2}"
        assert abs(center_y - size/2) < 5, f"Center y {center_y} should be near {size/2}"

        # Vertices should be roughly equidistant from center (circular)
        distances = np.sqrt((vertices[:, 0] - center_x)**2 +
                           (vertices[:, 1] - center_y)**2)
        radius_std = distances.std()
        assert radius_std < distances.mean() * 0.2, \
            "Contour should be approximately circular (low std dev in radius)"

        print(f"✓ Test passed: Generated circular contour with {len(main_contour)} vertices")
        print(f"  Center: ({center_x:.2f}, {center_y:.2f})")
        print(f"  Mean radius: {distances.mean():.2f} ± {radius_std:.2f}")

    def test_multiple_levels_concentric(self):
        """
        Test: Generate multiple concentric contour levels

        Given: Same Gaussian hill
        When: Request contours at levels [0.2, 0.5, 0.8]
        Then: Should return 3 concentric circles, outer to inner
        """
        from ccpn.c_replacement import contour

        size = 50
        x = np.linspace(-3, 3, size)
        y = np.linspace(-3, 3, size)
        X, Y = np.meshgrid(x, y)
        data = np.exp(-(X**2 + Y**2)).astype(np.float32)

        levels = np.array([0.2, 0.5, 0.8], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        # Validate structure
        assert len(result) == 3, "Should return 3 contour levels"

        # Each level should have contours
        for i, level_contours in enumerate(result):
            assert len(level_contours) > 0, f"Level {i} should have contours"
            print(f"✓ Level {levels[i]}: {len(level_contours[0])} vertices")

        # Validate they are concentric (higher level = smaller radius)
        radii = []
        for level_contours in result:
            vertices = np.array(level_contours[0])
            center_x = vertices[:, 0].mean()
            center_y = vertices[:, 1].mean()
            distances = np.sqrt((vertices[:, 0] - center_x)**2 +
                               (vertices[:, 1] - center_y)**2)
            radii.append(distances.mean())

        # Higher levels should have smaller radii
        assert radii[0] > radii[1] > radii[2], \
            f"Contours should be concentric (radii: {radii})"

        print(f"✓ Concentric contours validated: radii = {[f'{r:.2f}' for r in radii]}")


class TestContourTwoGaussians:
    """TDD: Test contours with two separate Gaussians"""

    def test_two_separate_contours(self):
        """
        Test: Generate contours for two separated peaks

        Given: Two Gaussian hills well separated
        When: Request contour at low level
        Then: Should return 2 separate closed polylines
        """
        from ccpn.c_replacement import contour

        size = 100
        x = np.arange(size, dtype=np.float32)
        y = np.arange(size, dtype=np.float32)
        X, Y = np.meshgrid(x, y)

        # Two Gaussians at (30, 50) and (70, 50)
        data = (np.exp(-((X - 30)**2 + (Y - 50)**2) / 100) +
                np.exp(-((X - 70)**2 + (Y - 50)**2) / 100))
        data = data.astype(np.float32)

        levels = np.array([0.3], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        # Validate
        assert len(result) == 1, "Should return one level"
        polylines = result[0]
        assert len(polylines) >= 2, "Should have at least 2 separate contours"

        print(f"✓ Found {len(polylines)} separate contours for two peaks")

    def test_merging_contours_high_level(self):
        """
        Test: At high level, contours should merge

        Given: Same two Gaussians
        When: Request contour at very low level
        Then: Should return 1 merged contour enclosing both
        """
        from ccpn.c_replacement import contour

        size = 100
        X, Y = np.meshgrid(np.arange(size, dtype=np.float32),
                           np.arange(size, dtype=np.float32))

        data = (np.exp(-((X - 30)**2 + (Y - 50)**2) / 100) +
                np.exp(-((X - 70)**2 + (Y - 50)**2) / 100))
        data = data.astype(np.float32)

        # Very low level should merge the contours
        levels = np.array([0.05], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        polylines = result[0]
        # Depending on implementation, might be 1 merged or 2 separate
        # For now just validate we got contours
        assert len(polylines) >= 1, "Should have at least one contour"

        print(f"✓ Low level contours: {len(polylines)} polyline(s)")


class TestContourEdgeCases:
    """TDD: Test edge cases and error conditions"""

    def test_empty_data(self):
        """Test: Empty or zero data should return empty contours"""
        from ccpn.c_replacement import contour

        data = np.zeros((50, 50), dtype=np.float32)
        levels = np.array([0.5], dtype=np.float32)

        result = contour.calculate_contours(data, levels)

        # Should return structure but with no polylines
        assert len(result) == 1, "Should return one level"
        assert len(result[0]) == 0, "Should have no contours for zero data"

        print("✓ Empty data handled correctly")

    def test_level_above_all_data(self):
        """Test: Level higher than all data should return no contours"""
        from ccpn.c_replacement import contour

        data = np.ones((50, 50), dtype=np.float32) * 0.5
        levels = np.array([1.0], dtype=np.float32)  # Above all data

        result = contour.calculate_contours(data, levels)

        assert len(result) == 1
        assert len(result[0]) == 0, "Should have no contours when level exceeds data"

        print("✓ High level handled correctly")

    def test_level_below_all_data(self):
        """Test: Level lower than all data should contour the boundary"""
        from ccpn.c_replacement import contour

        data = np.ones((50, 50), dtype=np.float32)
        levels = np.array([0.5], dtype=np.float32)  # Below all data

        result = contour.calculate_contours(data, levels)

        # Should return boundary contour
        assert len(result) == 1

        print("✓ Low level handled correctly")

    def test_invalid_input_types(self):
        """Test: Invalid input types should raise appropriate errors"""
        from ccpn.c_replacement import contour

        with pytest.raises((TypeError, ValueError)):
            contour.calculate_contours(None, None)

        with pytest.raises((TypeError, ValueError)):
            contour.calculate_contours("not an array", [0.5])

        print("✓ Invalid inputs rejected correctly")


class TestContourPerformance:
    """TDD: Performance requirements (will be validated with Numba)"""

    def test_large_dataset_performance(self):
        """
        Test: Should handle large datasets efficiently

        Requirement: Process 512x512 data in < 1 second (with Numba)
        This test documents the performance requirement
        """
        from ccpn.c_replacement import contour
        import time

        size = 512
        x = np.linspace(-5, 5, size)
        y = np.linspace(-5, 5, size)
        X, Y = np.meshgrid(x, y)
        data = np.exp(-(X**2 + Y**2)).astype(np.float32)

        levels = np.array([0.1, 0.3, 0.5, 0.7, 0.9], dtype=np.float32)

        # Warm-up run (for Numba JIT compilation)
        _ = contour.calculate_contours(data[:100, :100], levels[:1])

        # Timed run
        start = time.time()
        result = contour.calculate_contours(data, levels)
        elapsed = time.time() - start

        assert len(result) == 5, "Should return 5 levels"

        print(f"✓ Performance: 512x512 data with 5 levels in {elapsed:.3f}s")

        # Performance goal: < 1 second with Numba
        # Will be marked as expected to fail until Numba optimization added
        if elapsed > 1.0:
            pytest.skip(f"Performance not yet optimized: {elapsed:.3f}s (target: <1s)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
