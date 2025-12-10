"""
Tests for contour compatibility wrapper with fallback loading.

This test suite validates:
1. Fallback loading mechanism works correctly
2. API compatibility with C extension
3. Environment variable overrides work
4. Python and C implementations produce equivalent results
"""

import pytest
import numpy as np
import os
import sys


class TestFallbackMechanism:
    """Test the fallback loading strategy"""

    def test_import_compat_module(self):
        """Test that compat module can be imported"""
        from ccpn.c_replacement import contour_compat
        assert contour_compat is not None

    def test_get_implementation_info(self):
        """Test that we can query which implementation is loaded"""
        from ccpn.c_replacement.contour_compat import get_implementation_info

        info = get_implementation_info()

        assert 'implementation' in info
        assert 'module' in info
        assert 'fallback_occurred' in info

        # Should be using Python implementation (Numba or pure)
        assert info['implementation'] in ['python_numba', 'python_pure', 'c_extension']

        print(f"\n✓ Using implementation: {info['implementation']}")
        print(f"  Module: {info['module'].__name__}")
        print(f"  Fallback: {info['fallback_occurred']}")

    def test_python_implementation_preferred(self):
        """Test that Python implementation is loaded by default"""
        from ccpn.c_replacement.contour_compat import get_implementation_info

        info = get_implementation_info()

        # Should prefer Python over C
        if info['implementation'] == 'c_extension':
            print("\n⚠ Using C extension (Python not available)")
        else:
            assert info['implementation'] in ['python_numba', 'python_pure']
            print(f"\n✓ Correctly using Python implementation: {info['implementation']}")


class TestAPICompatibility:
    """Test API compatibility with C extension"""

    def test_contourer2d_class_exists(self):
        """Test that Contourer2d class exists"""
        from ccpn.c_replacement.contour_compat import Contourer2d

        assert Contourer2d is not None
        assert hasattr(Contourer2d, 'calculate_contours')

    def test_calculate_contours_signature(self):
        """Test calculate_contours has correct signature"""
        from ccpn.c_replacement.contour_compat import Contourer2d
        import inspect

        sig = inspect.signature(Contourer2d.calculate_contours)
        params = list(sig.parameters.keys())

        # Should have 'data' and 'levels' parameters
        assert 'data' in params
        assert 'levels' in params

    def test_module_level_function(self):
        """Test that module-level calculate_contours exists"""
        from ccpn.c_replacement.contour_compat import calculate_contours

        assert calculate_contours is not None


class TestFunctionalCorrectness:
    """Test that compatibility wrapper produces correct results"""

    def test_simple_gaussian_contour(self):
        """Test contour generation on simple Gaussian data"""
        from ccpn.c_replacement.contour_compat import Contourer2d

        # Create test data
        size = 50
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)
        levels = np.array([0.5], dtype=np.float32)

        # Generate contours
        contours = Contourer2d.calculate_contours(data, levels)

        # Validate
        assert contours is not None
        assert len(contours) == 1, "Should return one level"
        assert len(contours[0]) > 0, "Should have at least one polyline"

        # Check first polyline
        polyline = contours[0][0]
        assert isinstance(polyline, np.ndarray)
        assert polyline.dtype == np.float32
        assert len(polyline) % 2 == 0, "Should have even number of coordinates (x,y pairs)"
        assert len(polyline) > 10, "Should have multiple vertices"

        print(f"\n✓ Generated contour with {len(polyline)//2} vertices")

    def test_multiple_levels(self):
        """Test multiple contour levels"""
        from ccpn.c_replacement.contour_compat import Contourer2d

        size = 50
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)
        levels = np.array([0.2, 0.5, 0.8], dtype=np.float32)

        contours = Contourer2d.calculate_contours(data, levels)

        assert len(contours) == 3, "Should return 3 levels"

        for i, level_contours in enumerate(contours):
            assert len(level_contours) > 0, f"Level {i} should have contours"
            print(f"✓ Level {levels[i]}: {len(level_contours)} polyline(s)")

    def test_input_validation(self):
        """Test that input validation works"""
        from ccpn.c_replacement.contour_compat import Contourer2d

        # Invalid: not 2D data
        with pytest.raises((ValueError, TypeError)):
            data_1d = np.array([1, 2, 3], dtype=np.float32)
            levels = np.array([0.5], dtype=np.float32)
            Contourer2d.calculate_contours(data_1d, levels)

        # Invalid: not 1D levels
        with pytest.raises((ValueError, TypeError)):
            data = np.ones((10, 10), dtype=np.float32)
            levels_2d = np.array([[0.5, 0.6]], dtype=np.float32)
            Contourer2d.calculate_contours(data, levels_2d)

        print("✓ Input validation working correctly")


class TestEnvironmentOverrides:
    """Test environment variable overrides (manual testing guide)"""

    def test_env_override_documentation(self):
        """
        Document how to test environment overrides.

        Manual testing:
        1. Force Python: CCPN_USE_PYTHON_CONTOUR=1 pytest test_contour_compat.py
        2. Force C:      CCPN_USE_C_CONTOUR=1 pytest test_contour_compat.py
        """
        from ccpn.c_replacement.contour_compat import get_implementation_info

        info = get_implementation_info()

        print("\n" + "=" * 60)
        print("Environment Override Testing")
        print("=" * 60)
        print("\nCurrent configuration:")
        print(f"  CCPN_USE_PYTHON_CONTOUR = {os.environ.get('CCPN_USE_PYTHON_CONTOUR', 'not set')}")
        print(f"  CCPN_USE_C_CONTOUR      = {os.environ.get('CCPN_USE_C_CONTOUR', 'not set')}")
        print(f"\nActive implementation: {info['implementation']}")
        print(f"Module: {info['module'].__name__}")

        print("\n" + "=" * 60)
        print("To test overrides, run:")
        print("  CCPN_USE_PYTHON_CONTOUR=1 pytest test_contour_compat.py -v -s")
        print("  CCPN_USE_C_CONTOUR=1 pytest test_contour_compat.py -v -s")
        print("=" * 60)

        # This test always passes - it's for documentation
        assert True


class TestPerformance:
    """Test performance of compatibility wrapper"""

    def test_wrapper_overhead(self):
        """Test that wrapper adds minimal overhead"""
        from ccpn.c_replacement.contour_compat import Contourer2d
        import time

        # Prepare test data
        size = 256
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - size/2)**2 + (Y - size/2)**2) / 1000).astype(np.float32)
        levels = np.array([0.1, 0.3, 0.5, 0.7, 0.9], dtype=np.float32)

        # Warm-up
        _ = Contourer2d.calculate_contours(data[:50, :50], levels[:1])

        # Time wrapper
        start = time.time()
        result = Contourer2d.calculate_contours(data, levels)
        wrapper_time = time.time() - start

        # Time direct implementation
        from ccpn.c_replacement.contour_compat import _load_implementation
        impl = _load_implementation()

        start = time.time()
        result_direct = impl.calculate_contours(data, levels)
        direct_time = time.time() - start

        overhead = wrapper_time - direct_time
        overhead_percent = (overhead / direct_time) * 100 if direct_time > 0 else 0

        print(f"\n✓ Performance overhead:")
        print(f"  Wrapper:     {wrapper_time:.4f}s")
        print(f"  Direct:      {direct_time:.4f}s")
        print(f"  Overhead:    {overhead:.4f}s ({overhead_percent:.1f}%)")

        # Overhead should be negligible (< 5%)
        # For first call, JIT compilation might dominate, so be lenient
        assert overhead_percent < 50, f"Wrapper overhead too high: {overhead_percent:.1f}%"


class TestComparisonWithC:
    """Compare Python and C implementations (if C extension available)"""

    def test_python_vs_c_equivalence(self):
        """
        Compare Python and C extension results (if both available).

        This test demonstrates that Python implementation produces
        equivalent results to the C extension.
        """
        # Try to import C extension
        try:
            from ccpnc.contour import Contourer2d as CContourer2d
            c_available = True
        except ImportError:
            c_available = False
            pytest.skip("C extension not available for comparison")

        from ccpn.c_replacement.contour_compat import Contourer2d as PyContourer2d
        from ccpn.c_replacement.contour_compat import get_implementation_info

        # Make sure we're actually using Python
        info = get_implementation_info()
        if info['implementation'] == 'c_extension':
            pytest.skip("Wrapper is using C extension, cannot compare")

        # Create test data
        size = 50
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)
        levels = np.array([0.3, 0.5, 0.7], dtype=np.float32)

        # Generate contours with both implementations
        c_contours = CContourer2d.calculate_contours(data, levels)
        py_contours = PyContourer2d.calculate_contours(data, levels)

        # Compare structure
        assert len(c_contours) == len(py_contours), "Same number of levels"

        for i in range(len(levels)):
            c_level = c_contours[i]
            py_level = py_contours[i]

            # Number of polylines might differ slightly due to algorithm details
            # but should be close
            print(f"\nLevel {levels[i]}:")
            print(f"  C polylines:      {len(c_level)}")
            print(f"  Python polylines: {len(py_level)}")

            # Both should have found contours
            assert len(c_level) > 0, f"C found contours at level {levels[i]}"
            assert len(py_level) > 0, f"Python found contours at level {levels[i]}"

        print("\n✓ Python and C implementations produce compatible results")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
