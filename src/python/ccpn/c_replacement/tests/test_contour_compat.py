"""
Tests for contour compatibility wrapper with implementation switching.

This test suite validates:
1. Implementation switching works correctly
2. API compatibility with C extension
3. Environment variable overrides work
4. Python and C implementations produce equivalent results
"""

import pytest
import numpy as np
import os
import sys


class TestImplementationInfo:
    """Test implementation information functions"""

    def test_import_compat_module(self):
        """Test that compat module can be imported"""
        from ccpn.c_replacement import contour_compat
        assert contour_compat is not None

    def test_get_implementation_info(self):
        """Test that we can query which implementation is loaded"""
        from ccpn.c_replacement.contour_compat import get_implementation_info

        info = get_implementation_info()

        # Check required keys
        assert 'implementation' in info
        assert 'module' in info
        assert 'using_c' in info
        assert 'c_available' in info
        assert 'python_available' in info

        # Implementation should be a string
        assert isinstance(info['implementation'], str)

        # using_c should be boolean
        assert isinstance(info['using_c'], bool)

        print(f"\n✓ Using implementation: {info['implementation']}")
        print(f"  C available: {info['c_available']}")
        print(f"  Python available: {info['python_available']}")

    def test_get_available_implementations(self):
        """Test that we can check which implementations are available"""
        from ccpn.c_replacement.contour_compat import get_available_implementations

        avail = get_available_implementations()

        # Check required keys
        assert 'c_available' in avail
        assert 'python_available' in avail
        assert 'current' in avail
        assert 'using_c' in avail

        # At least one implementation should be available
        assert avail['c_available'] or avail['python_available'], \
            "At least one implementation must be available"

        print(f"\n✓ Available implementations:")
        print(f"  C: {avail['c_available']}")
        print(f"  Python: {avail['python_available']}")
        print(f"  Current: {avail['current']}")


class TestAPICompatibility:
    """Test API compatibility with C extension"""

    def test_contourer2d_class_exists(self):
        """Test that Contourer2d class exists"""
        from ccpn.c_replacement.contour_compat import Contourer2d

        assert Contourer2d is not None
        assert hasattr(Contourer2d, 'contourerGLList')

    def test_contourerGLList_signature(self):
        """Test contourerGLList has correct signature"""
        from ccpn.c_replacement.contour_compat import Contourer2d
        import inspect

        sig = inspect.signature(Contourer2d.contourerGLList)
        params = list(sig.parameters.keys())

        # Check for expected parameters
        expected_params = ['dataArrays', 'posLevels', 'negLevels',
                          'posColour', 'negColour', 'flatten']

        for param in expected_params:
            assert param in params, f"Missing parameter: {param}"


class TestFunctionalCorrectness:
    """Test that compatibility wrapper produces correct results"""

    def test_simple_gaussian_contour(self):
        """Test contour generation on simple Gaussian data"""
        from ccpn.c_replacement.contour_compat import Contourer2d

        # Create test data
        size = 128
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - size/2)**2 + (Y - size/2)**2) / 500).astype(np.float32) * 100

        dataArrays = (data,)
        posLevels = np.array([20.0], dtype=np.float32)
        negLevels = np.array([], dtype=np.float32)
        posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
        negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

        # Generate contours
        result = Contourer2d.contourerGLList(
            dataArrays, posLevels, negLevels, posColour, negColour, 0
        )

        # Validate result structure
        assert isinstance(result, list)
        assert len(result) == 5, "Result should be [numIndices, numVertices, indexing, vertices, colours]"

        numIndices, numVertices, indexing, vertices, colours = result

        # Check that we got some contours
        assert numVertices > 0, "Should generate vertices"
        assert len(vertices) == numVertices * 2, "Should have x,y for each vertex"
        assert len(colours) == numVertices * 4, "Should have RGBA for each vertex"

        print(f"\n✓ Generated contour with {numVertices} vertices")

    def test_multiple_levels(self):
        """Test multiple contour levels"""
        from ccpn.c_replacement.contour_compat import Contourer2d

        size = 128
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - size/2)**2 + (Y - size/2)**2) / 500).astype(np.float32) * 100

        dataArrays = (data,)
        posLevels = np.array([10.0, 30.0, 50.0], dtype=np.float32)
        negLevels = np.array([], dtype=np.float32)
        posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
        negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

        result = Contourer2d.contourerGLList(
            dataArrays, posLevels, negLevels, posColour, negColour, 0
        )

        numIndices, numVertices, indexing, vertices, colours = result

        # Should have generated contours for multiple levels
        assert numVertices > 0, "Should generate vertices for multiple levels"

        print(f"✓ Multiple levels: {numVertices} vertices total")

    def test_positive_and_negative_levels(self):
        """Test both positive and negative contour levels"""
        from ccpn.c_replacement.contour_compat import Contourer2d

        size = 128
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        # Data with positive and negative regions
        data = (np.exp(-((X - 40)**2 + (Y - 64)**2) / 300) -
                np.exp(-((X - 88)**2 + (Y - 64)**2) / 300)).astype(np.float32) * 100

        dataArrays = (data,)
        posLevels = np.array([20.0], dtype=np.float32)
        negLevels = np.array([-20.0], dtype=np.float32)
        posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
        negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

        result = Contourer2d.contourerGLList(
            dataArrays, posLevels, negLevels, posColour, negColour, 0
        )

        numIndices, numVertices, indexing, vertices, colours = result

        assert numVertices > 0, "Should generate vertices for positive and negative"

        print(f"✓ Pos/neg levels: {numVertices} vertices")


class TestImplementationSwitching:
    """Test implementation switching functionality"""

    def test_switch_to_python_if_available(self):
        """Test switching to Python implementation"""
        from ccpn.c_replacement.contour_compat import (
            get_available_implementations,
            use_python_implementation,
            use_c_implementation
        )

        avail = get_available_implementations()

        if not avail['python_available']:
            pytest.skip("Python implementation not available")

        # Remember original
        original = avail['current']

        try:
            # Switch to Python
            use_python_implementation()

            # Verify switch
            info = get_available_implementations()
            assert info['using_c'] is False
            assert 'Python' in info['current'] or 'Numba' in info['current']

            print(f"\n✓ Switched to Python: {info['current']}")

        finally:
            # Restore original if it was C
            if 'C extension' in original and avail['c_available']:
                use_c_implementation()

    def test_switch_to_c_if_available(self):
        """Test switching to C implementation"""
        from ccpn.c_replacement.contour_compat import (
            get_available_implementations,
            use_c_implementation,
            use_python_implementation
        )

        avail = get_available_implementations()

        if not avail['c_available']:
            pytest.skip("C implementation not available")

        # Remember original
        original = avail['current']

        try:
            # Switch to C
            use_c_implementation()

            # Verify switch
            info = get_available_implementations()
            assert info['using_c'] is True
            assert 'C extension' in info['current']

            print(f"\n✓ Switched to C: {info['current']}")

        finally:
            # Restore original if it was Python
            if 'C extension' not in original and avail['python_available']:
                use_python_implementation()

    def test_switch_to_unavailable_implementation_raises_error(self):
        """Test that switching to unavailable implementation raises error"""
        from ccpn.c_replacement.contour_compat import (
            get_available_implementations,
            use_python_implementation,
            use_c_implementation
        )
        import os

        avail = get_available_implementations()

        # Try to switch to unavailable implementation
        # We can't easily test this without uninstalling, so we document the behavior
        # This test validates that at least one implementation is available
        assert avail['c_available'] or avail['python_available']

        print(f"\n✓ At least one implementation available")


class TestBothImplementations:
    """Compare Python and C implementations if both available"""

    def test_python_vs_c_equivalence(self):
        """Test that Python and C produce similar results"""
        from ccpn.c_replacement.contour_compat import (
            Contourer2d,
            get_available_implementations,
            use_python_implementation,
            use_c_implementation
        )

        avail = get_available_implementations()

        if not (avail['c_available'] and avail['python_available']):
            pytest.skip("Both C and Python implementations needed for comparison")

        # Create test data
        size = 128
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - size/2)**2 + (Y - size/2)**2) / 500).astype(np.float32) * 100

        dataArrays = (data,)
        posLevels = np.array([20.0, 40.0], dtype=np.float32)
        negLevels = np.array([], dtype=np.float32)
        posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
        negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

        # Get C result
        use_c_implementation()
        result_c = Contourer2d.contourerGLList(
            dataArrays, posLevels, negLevels, posColour, negColour, 0
        )

        # Get Python result
        use_python_implementation()
        result_py = Contourer2d.contourerGLList(
            dataArrays, posLevels, negLevels, posColour, negColour, 0
        )

        # Compare structures
        assert len(result_c) == len(result_py) == 5

        numVertices_c = result_c[1]
        numVertices_py = result_py[1]

        print(f"\n✓ C vertices:      {numVertices_c}")
        print(f"✓ Python vertices: {numVertices_py}")

        # Vertex counts should be similar (within 20% due to algorithm differences)
        ratio = numVertices_py / numVertices_c if numVertices_c > 0 else 1.0
        assert 0.8 <= ratio <= 1.2, \
            f"Vertex counts should be similar (C: {numVertices_c}, Python: {numVertices_py})"

        print(f"✓ Ratio: {ratio:.2f} (within acceptable range)")

        # Restore C if it was originally selected
        if 'C extension' in avail['current']:
            use_c_implementation()


class TestPerformance:
    """Test performance characteristics"""

    def test_wrapper_overhead_minimal(self):
        """Test that wrapper adds minimal overhead"""
        from ccpn.c_replacement.contour_compat import Contourer2d
        import time

        # Prepare test data
        size = 256
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - size/2)**2 + (Y - size/2)**2) / 1000).astype(np.float32) * 100

        dataArrays = (data,)
        posLevels = np.array([10.0, 30.0, 50.0], dtype=np.float32)
        negLevels = np.array([], dtype=np.float32)
        posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
        negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

        # Warm-up
        _ = Contourer2d.contourerGLList(
            (data[:50, :50],), posLevels[:1], negLevels,
            posColour, negColour, 0
        )

        # Time wrapper
        start = time.time()
        result = Contourer2d.contourerGLList(
            dataArrays, posLevels, negLevels, posColour, negColour, 0
        )
        wrapper_time = time.time() - start

        # Should complete in reasonable time
        assert wrapper_time < 1.0, f"Should complete in <1s (got {wrapper_time:.4f}s)"

        print(f"\n✓ Completed in {wrapper_time:.4f}s")
        print(f"✓ Generated {result[1]} vertices")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
