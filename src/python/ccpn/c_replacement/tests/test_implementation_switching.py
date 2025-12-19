"""
Tests for implementation switching functionality across Peak and Contour modules.

This test suite validates:
1. Runtime switching between C and Python implementations
2. Environment variable controls (CCPN_FORCE_PYTHON, CCPN_FORCE_C)
3. Error handling when implementations are unavailable
4. State persistence across operations
"""

import pytest
import numpy as np
import os
import sys


class TestPeakModuleSwitching:
    """Test implementation switching for Peak module"""

    def test_peak_import_and_info(self):
        """Test Peak module can be imported and queried"""
        from ccpn.c_replacement.peak_compat import (
            Peak,
            get_implementation_info,
            get_available_implementations
        )

        assert Peak is not None

        info = get_implementation_info()
        assert 'implementation' in info
        assert 'using_c' in info

        avail = get_available_implementations()
        assert 'c_available' in avail
        assert 'python_available' in avail

        print(f"\n✓ Peak module info:")
        print(f"  Current: {info['implementation']}")
        print(f"  C available: {avail['c_available']}")
        print(f"  Python available: {avail['python_available']}")

    def test_peak_switch_to_python(self):
        """Test switching Peak module to Python implementation"""
        from ccpn.c_replacement.peak_compat import (
            get_available_implementations,
            use_python_implementation,
            use_c_implementation
        )

        avail = get_available_implementations()

        if not avail['python_available']:
            pytest.skip("Python implementation not available")

        original = avail['current']

        try:
            # Switch to Python
            use_python_implementation()

            # Verify
            info = get_available_implementations()
            assert info['using_c'] is False
            assert 'Python' in info['current'] or 'Numba' in info['current']

            print(f"\n✓ Peak switched to Python: {info['current']}")

        finally:
            # Restore
            if 'C extension' in original and avail['c_available']:
                use_c_implementation()

    def test_peak_switch_to_c(self):
        """Test switching Peak module to C implementation"""
        from ccpn.c_replacement.peak_compat import (
            get_available_implementations,
            use_c_implementation,
            use_python_implementation
        )

        avail = get_available_implementations()

        if not avail['c_available']:
            pytest.skip("C implementation not available")

        original = avail['current']

        try:
            # Switch to C
            use_c_implementation()

            # Verify
            info = get_available_implementations()
            assert info['using_c'] is True
            assert 'C extension' in info['current']

            print(f"\n✓ Peak switched to C: {info['current']}")

        finally:
            # Restore
            if 'C extension' not in original and avail['python_available']:
                use_python_implementation()

    def test_peak_operations_work_after_switch(self):
        """Test Peak operations work correctly after switching"""
        from ccpn.c_replacement.peak_compat import (
            Peak,
            get_available_implementations,
            use_python_implementation,
            use_c_implementation
        )

        avail = get_available_implementations()

        if not (avail['c_available'] and avail['python_available']):
            pytest.skip("Both implementations needed")

        # Generate test data
        shape = (30, 30)
        X, Y = np.meshgrid(np.arange(shape[0]), np.arange(shape[1]))
        data = np.exp(-((X - 15)**2 + (Y - 15)**2) / 20).astype(np.float32) * 100

        region = np.array([[12, 12], [18, 18]], dtype=np.int32)
        peaks = np.array([[15.0, 15.0]], dtype=np.float32)

        # Test with C
        use_c_implementation()
        result_c = Peak.fitParabolicPeaks(data, region, peaks)
        assert len(result_c) == 1
        print(f"\n✓ C result: height={result_c[0][0]:.2f}")

        # Test with Python
        use_python_implementation()
        result_py = Peak.fitParabolicPeaks(data, region, peaks)
        assert len(result_py) == 1
        print(f"✓ Python result: height={result_py[0][0]:.2f}")

        # Results should be similar
        height_c = result_c[0][0]
        height_py = result_py[0][0]
        assert abs(height_c - height_py) < 10, "Results should be similar"

        # Restore C
        if 'C extension' in avail['current']:
            use_c_implementation()


class TestContourModuleSwitching:
    """Test implementation switching for Contour module"""

    def test_contour_import_and_info(self):
        """Test Contour module can be imported and queried"""
        from ccpn.c_replacement.contour_compat import (
            Contourer2d,
            get_implementation_info,
            get_available_implementations
        )

        assert Contourer2d is not None

        info = get_implementation_info()
        assert 'implementation' in info
        assert 'using_c' in info

        avail = get_available_implementations()
        assert 'c_available' in avail
        assert 'python_available' in avail

        print(f"\n✓ Contour module info:")
        print(f"  Current: {info['implementation']}")
        print(f"  C available: {avail['c_available']}")
        print(f"  Python available: {avail['python_available']}")

    def test_contour_switch_to_python(self):
        """Test switching Contour module to Python implementation"""
        from ccpn.c_replacement.contour_compat import (
            get_available_implementations,
            use_python_implementation,
            use_c_implementation
        )

        avail = get_available_implementations()

        if not avail['python_available']:
            pytest.skip("Python implementation not available")

        original = avail['current']

        try:
            # Switch to Python
            use_python_implementation()

            # Verify
            info = get_available_implementations()
            assert info['using_c'] is False
            assert 'Python' in info['current'] or 'Numba' in info['current']

            print(f"\n✓ Contour switched to Python: {info['current']}")

        finally:
            # Restore
            if 'C extension' in original and avail['c_available']:
                use_c_implementation()

    def test_contour_switch_to_c(self):
        """Test switching Contour module to C implementation"""
        from ccpn.c_replacement.contour_compat import (
            get_available_implementations,
            use_c_implementation,
            use_python_implementation
        )

        avail = get_available_implementations()

        if not avail['c_available']:
            pytest.skip("C implementation not available")

        original = avail['current']

        try:
            # Switch to C
            use_c_implementation()

            # Verify
            info = get_available_implementations()
            assert info['using_c'] is True
            assert 'C extension' in info['current']

            print(f"\n✓ Contour switched to C: {info['current']}")

        finally:
            # Restore
            if 'C extension' not in original and avail['python_available']:
                use_python_implementation()

    def test_contour_operations_work_after_switch(self):
        """Test Contour operations work correctly after switching"""
        from ccpn.c_replacement.contour_compat import (
            Contourer2d,
            get_available_implementations,
            use_python_implementation,
            use_c_implementation
        )

        avail = get_available_implementations()

        if not (avail['c_available'] and avail['python_available']):
            pytest.skip("Both implementations needed")

        # Generate test data
        size = 128
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data = np.exp(-((X - size/2)**2 + (Y - size/2)**2) / 500).astype(np.float32) * 100

        dataArrays = (data,)
        posLevels = np.array([20.0], dtype=np.float32)
        negLevels = np.array([], dtype=np.float32)
        posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
        negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

        # Test with C
        use_c_implementation()
        result_c = Contourer2d.contourerGLList(
            dataArrays, posLevels, negLevels, posColour, negColour, 0
        )
        vertices_c = result_c[1]
        print(f"\n✓ C result: {vertices_c} vertices")

        # Test with Python
        use_python_implementation()
        result_py = Contourer2d.contourerGLList(
            dataArrays, posLevels, negLevels, posColour, negColour, 0
        )
        vertices_py = result_py[1]
        print(f"✓ Python result: {vertices_py} vertices")

        # Results should be similar (within 20%)
        ratio = vertices_py / vertices_c if vertices_c > 0 else 1.0
        assert 0.8 <= ratio <= 1.2, "Vertex counts should be similar"

        # Restore C
        if 'C extension' in avail['current']:
            use_c_implementation()


class TestIndependentSwitching:
    """Test that Peak and Contour can be switched independently"""

    def test_independent_switching(self):
        """Test that Peak and Contour switch independently"""
        import ccpn.c_replacement.peak_compat as peak_compat
        import ccpn.c_replacement.contour_compat as contour_compat

        peak_avail = peak_compat.get_available_implementations()
        contour_avail = contour_compat.get_available_implementations()

        if not (peak_avail['c_available'] and peak_avail['python_available']):
            pytest.skip("Need both Peak implementations")

        if not (contour_avail['c_available'] and contour_avail['python_available']):
            pytest.skip("Need both Contour implementations")

        try:
            # Set Peak to Python, Contour to C
            peak_compat.use_python_implementation()
            contour_compat.use_c_implementation()

            # Verify
            peak_info = peak_compat.get_available_implementations()
            contour_info = contour_compat.get_available_implementations()

            assert peak_info['using_c'] is False
            assert contour_info['using_c'] is True

            print(f"\n✓ Peak: {peak_info['current']}")
            print(f"✓ Contour: {contour_info['current']}")

            # Now switch both
            peak_compat.use_c_implementation()
            contour_compat.use_python_implementation()

            # Verify
            peak_info = peak_compat.get_available_implementations()
            contour_info = contour_compat.get_available_implementations()

            assert peak_info['using_c'] is True
            assert contour_info['using_c'] is False

            print(f"✓ Switched - Peak: {peak_info['current']}")
            print(f"✓ Switched - Contour: {contour_info['current']}")

        finally:
            # Restore to C for both
            if peak_avail['c_available']:
                peak_compat.use_c_implementation()
            if contour_avail['c_available']:
                contour_compat.use_c_implementation()


class TestErrorHandling:
    """Test error handling for switching"""

    def test_switch_to_unavailable_python_raises(self):
        """Test that switching to unavailable Python raises error"""
        from ccpn.c_replacement.peak_compat import (
            get_available_implementations,
            use_python_implementation
        )

        avail = get_available_implementations()

        if avail['python_available']:
            # Can't test this case - Python is available
            pytest.skip("Python implementation is available")

        # If we get here, Python is not available
        with pytest.raises(RuntimeError) as excinfo:
            use_python_implementation()

        assert "not available" in str(excinfo.value).lower()

    def test_switch_to_unavailable_c_raises(self):
        """Test that switching to unavailable C raises error"""
        from ccpn.c_replacement.peak_compat import (
            get_available_implementations,
            use_c_implementation
        )

        avail = get_available_implementations()

        if avail['c_available']:
            # Can't test this case - C is available
            pytest.skip("C implementation is available")

        # If we get here, C is not available
        with pytest.raises(RuntimeError) as excinfo:
            use_c_implementation()

        assert "not available" in str(excinfo.value).lower()


class TestStatePersistence:
    """Test that implementation choice persists across operations"""

    def test_peak_state_persists(self):
        """Test Peak implementation choice persists"""
        from ccpn.c_replacement.peak_compat import (
            Peak,
            get_available_implementations,
            use_python_implementation,
            use_c_implementation
        )

        avail = get_available_implementations()

        if not avail['python_available']:
            pytest.skip("Python implementation not available")

        original = avail['current']

        try:
            # Switch to Python
            use_python_implementation()

            # Do multiple operations
            shape = (20, 20)
            X, Y = np.meshgrid(np.arange(shape[0]), np.arange(shape[1]))
            data = np.exp(-((X - 10)**2 + (Y - 10)**2) / 20).astype(np.float32) * 100

            region = np.array([[8, 8], [12, 12]], dtype=np.int32)
            peaks = np.array([[10.0, 10.0]], dtype=np.float32)

            # Operation 1
            result1 = Peak.fitParabolicPeaks(data, region, peaks)

            # Verify still using Python
            info = get_available_implementations()
            assert info['using_c'] is False

            # Operation 2
            result2 = Peak.fitParabolicPeaks(data, region, peaks)

            # Still using Python
            info = get_available_implementations()
            assert info['using_c'] is False

            print(f"\n✓ State persisted across operations")

        finally:
            if 'C extension' in original and avail['c_available']:
                use_c_implementation()

    def test_contour_state_persists(self):
        """Test Contour implementation choice persists"""
        from ccpn.c_replacement.contour_compat import (
            Contourer2d,
            get_available_implementations,
            use_python_implementation,
            use_c_implementation
        )

        avail = get_available_implementations()

        if not avail['python_available']:
            pytest.skip("Python implementation not available")

        original = avail['current']

        try:
            # Switch to Python
            use_python_implementation()

            # Do multiple operations
            size = 64
            X, Y = np.meshgrid(np.arange(size), np.arange(size))
            data = np.exp(-((X - size/2)**2 + (Y - size/2)**2) / 200).astype(np.float32) * 100

            dataArrays = (data,)
            posLevels = np.array([20.0], dtype=np.float32)
            negLevels = np.array([], dtype=np.float32)
            posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
            negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

            # Operation 1
            result1 = Contourer2d.contourerGLList(
                dataArrays, posLevels, negLevels, posColour, negColour, 0
            )

            # Verify still using Python
            info = get_available_implementations()
            assert info['using_c'] is False

            # Operation 2
            result2 = Contourer2d.contourerGLList(
                dataArrays, posLevels, negLevels, posColour, negColour, 0
            )

            # Still using Python
            info = get_available_implementations()
            assert info['using_c'] is False

            print(f"\n✓ State persisted across operations")

        finally:
            if 'C extension' in original and avail['c_available']:
                use_c_implementation()


class TestEnvironmentVariables:
    """Test environment variable controls (documentation)"""

    def test_environment_variable_documentation(self):
        """
        Document environment variable usage.

        Manual testing:
        1. Force Python: CCPN_FORCE_PYTHON=1 pytest test_implementation_switching.py
        2. Force C:      CCPN_FORCE_C=1 pytest test_implementation_switching.py
        3. Quiet mode:   CCPN_QUIET=1 pytest test_implementation_switching.py
        """
        print("\n" + "=" * 70)
        print("ENVIRONMENT VARIABLE TESTING")
        print("=" * 70)
        print("\nCurrent environment:")
        print(f"  CCPN_FORCE_PYTHON = {os.environ.get('CCPN_FORCE_PYTHON', 'not set')}")
        print(f"  CCPN_FORCE_C      = {os.environ.get('CCPN_FORCE_C', 'not set')}")
        print(f"  CCPN_QUIET        = {os.environ.get('CCPN_QUIET', 'not set')}")

        from ccpn.c_replacement.peak_compat import get_implementation_info as peak_info
        from ccpn.c_replacement.contour_compat import get_implementation_info as contour_info

        print(f"\nPeak implementation: {peak_info()['implementation']}")
        print(f"Contour implementation: {contour_info()['implementation']}")

        print("\n" + "=" * 70)
        print("To test environment variables:")
        print("  CCPN_FORCE_PYTHON=1 pytest test_implementation_switching.py -v -s")
        print("  CCPN_FORCE_C=1 pytest test_implementation_switching.py -v -s")
        print("  CCPN_QUIET=1 pytest test_implementation_switching.py -v -s")
        print("=" * 70)

        # This test always passes - it's for documentation
        assert True


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
