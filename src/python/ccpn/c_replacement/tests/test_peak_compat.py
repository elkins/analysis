"""Tests for Peak compatibility wrapper.

This module tests the compatibility wrapper that provides automatic fallback
between C extension and pure Python implementation.
"""

import numpy as np
import pytest
from ccpn.c_replacement.tests.test_peak_data import (
    generate_gaussian_peak,
    generate_multi_peak_spectrum,
)


class TestCompatibilityWrapper:
    """Test the Peak compatibility wrapper."""

    def test_import_wrapper(self):
        """Test that we can import the compatibility wrapper."""
        from ccpn.c_replacement.peak_compat import Peak
        assert Peak is not None

    def test_get_implementation_info(self):
        """Test implementation info function."""
        from ccpn.c_replacement.peak_compat import get_implementation_info

        info = get_implementation_info()

        # Should have required keys
        assert 'implementation' in info
        assert 'module' in info
        assert 'using_c' in info
        assert 'available_functions' in info
        assert 'phase_1_complete' in info
        assert 'phase_2_complete' in info
        assert 'phase_3_complete' in info

        # Implementation should be either C or Python
        valid_impls = [
            'C extension',
            'C extension [RUNTIME SWITCH]',
            'Pure Python (Numba JIT)',
            'Pure Python (Numba JIT) [RUNTIME SWITCH]'
        ]
        assert info['implementation'] in valid_impls

        # using_c should be boolean
        assert isinstance(info['using_c'], bool)

        # Phase 1 and 2 should be complete
        assert info['phase_1_complete'] is True
        assert info['phase_2_complete'] is True

        # Phase 3 depends on whether C extension is available
        if info['using_c']:
            assert info['phase_3_complete'] is True
        else:
            assert info['phase_3_complete'] is False

    def test_find_peaks_via_wrapper(self):
        """Test findPeaks through compatibility wrapper."""
        from ccpn.c_replacement.peak_compat import Peak

        # Generate test data
        shape = (30, 30)
        center = (15, 15)
        height = 100.0
        linewidth = (2.5, 2.5)

        data = generate_gaussian_peak(shape, center, height, linewidth, noise_level=1.0)

        # Find peaks via wrapper
        peaks = Peak.findPeaks(
            data, False, True, 0.0, 50.0,
            [3, 3], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(peaks) == 1
        peak_pos, peak_height = peaks[0]
        assert peak_height >= 50.0
        assert np.allclose(peak_pos, center, atol=1)

    def test_fit_parabolic_peaks_via_wrapper(self):
        """Test fitParabolicPeaks through compatibility wrapper."""
        from ccpn.c_replacement.peak_compat import Peak

        # Generate test data
        shape = (30, 30)
        center = (15, 15)
        height = 100.0
        linewidth = (2.5, 2.5)

        data = generate_gaussian_peak(shape, center, height, linewidth, noise_level=0.5)

        # Define region and peak
        region = np.array([[12, 12], [18, 18]], dtype=np.int32)
        peaks = np.array([[15.0, 15.0]], dtype=np.float32)

        # Fit peaks via wrapper
        results = Peak.fitParabolicPeaks(data, region, peaks)

        assert len(results) == 1
        fitted_height, fitted_position, fitted_linewidth = results[0]

        # Check that fitting refined the position
        assert isinstance(fitted_position, tuple)
        assert len(fitted_position) == 2
        assert np.allclose(fitted_position, center, atol=1.0)

        # Check that height is reasonable
        assert fitted_height > 0
        assert fitted_height < height * 1.5  # Within 50% of expected

        # Check that linewidth is reasonable
        assert isinstance(fitted_linewidth, tuple)
        assert len(fitted_linewidth) == 2

    def test_fit_peaks_not_implemented_python(self):
        """Test that fitPeaks raises NotImplementedError for Python implementation."""
        from ccpn.c_replacement.peak_compat import Peak, get_implementation_info

        info = get_implementation_info()

        # Only test this if we're using Python implementation
        if not info['using_c']:
            shape = (30, 30)
            data = generate_gaussian_peak(shape, (15, 15), 100.0, (2.5, 2.5))
            region = np.array([[12, 12], [18, 18]], dtype=np.int32)
            peaks = np.array([[15.0, 15.0]], dtype=np.float32)

            with pytest.raises(NotImplementedError) as excinfo:
                Peak.fitPeaks(data, region, peaks, 0)

            assert "Levenberg-Marquardt" in str(excinfo.value)
            assert "Phase 3" in str(excinfo.value)

    def test_convenience_functions(self):
        """Test module-level convenience functions."""
        from ccpn.c_replacement.peak_compat import (
            find_peaks,
            fit_parabolic_peaks,
        )

        # Generate test data
        shape = (20, 20)
        data = generate_gaussian_peak(shape, (10, 10), 100.0, (2.0, 2.0))

        # Test find_peaks
        peaks = find_peaks(
            data, False, True, 0.0, 50.0,
            [2, 2], True, 0.0, [0.0, 0.0],
            [], [], []
        )
        assert len(peaks) >= 1

        # Test fit_parabolic_peaks
        region = np.array([[8, 8], [12, 12]], dtype=np.int32)
        peak_array = np.array([[10.0, 10.0]], dtype=np.float32)
        results = fit_parabolic_peaks(data, region, peak_array)
        assert len(results) == 1

    def test_multiple_peaks_workflow(self):
        """Test complete workflow: find peaks, then fit them."""
        from ccpn.c_replacement.peak_compat import Peak

        # Generate data with multiple peaks
        shape = (40, 40)
        peaks_spec = [
            {'center': (10, 10), 'height': 100, 'linewidth': (2, 2), 'model': 'gaussian'},
            {'center': (30, 10), 'height': 120, 'linewidth': (2.5, 2.5), 'model': 'gaussian'},
            {'center': (20, 30), 'height': 90, 'linewidth': (3, 3), 'model': 'gaussian'},
        ]

        data = generate_multi_peak_spectrum(shape, peaks_spec, noise_level=1.0)

        # Step 1: Find peaks
        found_peaks = Peak.findPeaks(
            data, False, True, 0.0, 40.0,
            [3, 3], True, 0.0, [0.0, 0.0],
            [], [], []
        )

        assert len(found_peaks) == 3

        # Step 2: Fit each peak
        for peak_pos, peak_height in found_peaks:
            # Define region around peak
            region = np.array([
                [max(0, peak_pos[0] - 4), max(0, peak_pos[1] - 4)],
                [min(shape[0], peak_pos[0] + 4), min(shape[1], peak_pos[1] + 4)]
            ], dtype=np.int32)

            # Initial peak position
            peak_array = np.array([[float(peak_pos[0]), float(peak_pos[1])]], dtype=np.float32)

            # Fit peak
            results = Peak.fitParabolicPeaks(data, region, peak_array)

            assert len(results) == 1
            fitted_height, fitted_position, fitted_linewidth = results[0]

            # Fitted position should be near initial position
            assert np.allclose(fitted_position, peak_pos, atol=2.0)


class TestAPICompatibility:
    """Test that the wrapper matches the C extension API."""

    def test_find_peaks_signature(self):
        """Test that findPeaks has the correct signature."""
        from ccpn.c_replacement.peak_compat import Peak
        import inspect

        sig = inspect.signature(Peak.findPeaks)
        params = list(sig.parameters.keys())

        # Check for expected parameters
        expected_params = [
            'dataArray', 'haveLow', 'haveHigh', 'low', 'high',
            'buffer', 'nonadjacent', 'dropFactor', 'minLinewidth',
            'excludedRegions', 'diagonalExclusionDims', 'diagonalExclusionTransform'
        ]

        for param in expected_params:
            assert param in params, f"Missing parameter: {param}"

    def test_fit_parabolic_peaks_signature(self):
        """Test that fitParabolicPeaks has the correct signature."""
        from ccpn.c_replacement.peak_compat import Peak
        import inspect

        sig = inspect.signature(Peak.fitParabolicPeaks)
        params = list(sig.parameters.keys())

        # Check for expected parameters
        expected_params = ['dataArray', 'regionArray', 'peakArray']

        for param in expected_params:
            assert param in params, f"Missing parameter: {param}"

    def test_fit_peaks_signature(self):
        """Test that fitPeaks has the correct signature."""
        from ccpn.c_replacement.peak_compat import Peak
        import inspect

        sig = inspect.signature(Peak.fitPeaks)
        params = list(sig.parameters.keys())

        # Check for expected parameters
        expected_params = ['dataArray', 'regionArray', 'peakArray', 'method']

        for param in expected_params:
            assert param in params, f"Missing parameter: {param}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
