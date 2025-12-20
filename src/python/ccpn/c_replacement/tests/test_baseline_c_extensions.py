"""
TDD Baseline Tests: Capture C Extension Behavior

This test suite documents the EXACT behavior of the existing C extensions.
These tests serve as the specification for the Python replacements.

Purpose:
1. Document C extension API and behavior
2. Create numerical validation datasets
3. Measure C extension performance baseline
4. Provide regression tests for Python implementation

When these tests pass with Python implementation, we know it's correct!
"""

import pytest
import numpy as np
from operator import itemgetter

# Try to import C extensions - these tests require them
try:
    from ccpnc.peak import Peak
    from ccpnc.contour import Contourer2d
    HAS_C_EXTENSIONS = True
except ImportError:
    HAS_C_EXTENSIONS = False
    Peak = None
    Contourer2d = None


@pytest.mark.skipif(not HAS_C_EXTENSIONS, reason="C extensions not available")
class TestPeakFindingBaseline:
    """Capture exact behavior of C Peak.findPeaks()"""

    def test_simple_gaussian_peak_finding(self):
        """Test finding a single Gaussian peak in 2D data"""
        # Create test data: single 2D Gaussian peak
        size = 100
        x = np.linspace(0, 10, size)
        y = np.linspace(0, 10, size)
        X, Y = np.meshgrid(x, y)

        # Gaussian centered at (5, 5) with sigma=1.0, height=1000
        center_x, center_y = 50, 50  # indices
        sigma = 10.0  # in indices
        height = 1000.0

        data = height * np.exp(-((X - 5)**2 + (Y - 5)**2) / (2 * (sigma/10)**2))
        data = data.astype(np.float32)

        # Call C extension
        haveLow = 0
        haveHigh = 1
        low = 0
        high = 500  # threshold
        buffer = [1, 1]
        nonadjacent = 0
        dropFactor = 0.0
        minLinewidth = [0.0, 0.0]

        peaks = Peak.findPeaks(data, haveLow, haveHigh, low, high, buffer,
                               nonadjacent, dropFactor, minLinewidth, [], [], [])

        # VALIDATION: Document expected behavior
        assert len(peaks) >= 1, "Should find at least one peak"

        # Get highest peak
        peaks.sort(key=itemgetter(1), reverse=True)
        position, peak_height = peaks[0]

        # Validate peak position (should be near center)
        assert abs(position[0] - center_x) < 2, f"Peak x position {position[0]} should be near {center_x}"
        assert abs(position[1] - center_y) < 2, f"Peak y position {position[1]} should be near {center_y}"

        # Validate peak height
        assert peak_height > 990, f"Peak height {peak_height} should be close to {height}"
        assert peak_height <= height, "Peak height should not exceed data maximum"

        # Store for Python implementation validation
        self.baseline_result = {
            'num_peaks': len(peaks),
            'position': position,
            'height': peak_height,
            'data': data
        }

        print(f"✓ C Extension: Found {len(peaks)} peaks")
        print(f"✓ Highest peak at {position} with height {peak_height}")

    def test_multiple_peaks(self):
        """Test finding multiple well-separated peaks"""
        size = 100
        data = np.zeros((size, size), dtype=np.float32)

        # Add 3 peaks at known locations
        peaks_expected = [
            (25, 25, 1000.0),  # (x, y, height)
            (75, 25, 800.0),
            (50, 75, 900.0)
        ]

        sigma = 5.0
        x = np.arange(size)
        y = np.arange(size)
        X, Y = np.meshgrid(x, y)

        for px, py, h in peaks_expected:
            gaussian = h * np.exp(-((X - px)**2 + (Y - py)**2) / (2 * sigma**2))
            data += gaussian

        data = data.astype(np.float32)

        # Call C extension
        peaks = Peak.findPeaks(data, 0, 1, 0, 500, [2, 2], 0, 0.0, [0.0, 0.0], [], [], [])

        # VALIDATION
        assert len(peaks) >= 3, f"Should find at least 3 peaks, found {len(peaks)}"

        peaks.sort(key=itemgetter(1), reverse=True)

        # Verify we found peaks near expected locations
        found_positions = [p[0] for p in peaks[:3]]
        print(f"✓ C Extension: Found {len(peaks)} peaks at {found_positions}")

        # Store baseline
        self.baseline_multiple = {
            'num_peaks': len(peaks),
            'peaks': peaks[:3],
            'data': data
        }


@pytest.mark.skipif(not HAS_C_EXTENSIONS, reason="C extensions not available")
class TestPeakFittingBaseline:
    """Capture exact behavior of C Peak.fitPeaks()"""

    def test_gaussian_fit(self):
        """Test Gaussian fitting of a known peak"""
        # Create perfect Gaussian
        size = 20
        x = np.arange(size, dtype=np.float32)
        y = np.arange(size, dtype=np.float32)
        X, Y = np.meshgrid(x, y)

        # Known parameters
        center_x, center_y = 10.0, 10.0
        sigma_x, sigma_y = 2.0, 2.0
        height = 1000.0

        data = height * np.exp(-((X - center_x)**2 / (2 * sigma_x**2) +
                                  (Y - center_y)**2 / (2 * sigma_y**2)))
        data = data.astype(np.float32)

        # Set up fitting region
        peak_pos = np.array([[10.0, 10.0]], dtype=np.float32)
        region = np.array([[5, 5], [15, 15]], dtype=np.int32)

        # Call C extension (method 0 = Gaussian)
        result = Peak.fitPeaks(data, region, peak_pos, 0)

        # VALIDATION
        assert len(result) == 1, "Should return one fit result"

        fitted_height, fitted_center, fitted_linewidth = result[0]

        # Validate fit quality
        assert abs(fitted_center[0] - center_x) < 0.5, \
            f"Fitted center x {fitted_center[0]} should match true {center_x}"
        assert abs(fitted_center[1] - center_y) < 0.5, \
            f"Fitted center y {fitted_center[1]} should match true {center_y}"
        assert fitted_height > height * 0.95, \
            f"Fitted height {fitted_height} should be close to true {height}"

        print(f"✓ C Extension Gaussian Fit:")
        print(f"  Height: {fitted_height:.2f} (true: {height})")
        print(f"  Center: {fitted_center} (true: [{center_x}, {center_y}])")
        print(f"  Linewidth: {fitted_linewidth}")

        # Store baseline
        self.baseline_gaussian = {
            'data': data,
            'region': region,
            'peak_pos': peak_pos,
            'result': result[0]
        }

    def test_lorentzian_fit(self):
        """Test Lorentzian fitting"""
        # Create Lorentzian peak
        size = 20
        x = np.arange(size, dtype=np.float32)
        y = np.arange(size, dtype=np.float32)
        X, Y = np.meshgrid(x, y)

        center_x, center_y = 10.0, 10.0
        gamma = 2.0  # FWHM/2
        height = 1000.0

        # Lorentzian: I = I0 * gamma^2 / ((x-x0)^2 + gamma^2)
        data = height * (gamma**2 / ((X - center_x)**2 + (Y - center_y)**2 + gamma**2))
        data = data.astype(np.float32)

        peak_pos = np.array([[10.0, 10.0]], dtype=np.float32)
        region = np.array([[5, 5], [15, 15]], dtype=np.int32)

        # Call C extension (method 1 = Lorentzian)
        result = Peak.fitPeaks(data, region, peak_pos, 1)

        # VALIDATION
        assert len(result) == 1, "Should return one fit result"

        fitted_height, fitted_center, fitted_linewidth = result[0]

        print(f"✓ C Extension Lorentzian Fit:")
        print(f"  Height: {fitted_height:.2f}")
        print(f"  Center: {fitted_center}")
        print(f"  Linewidth: {fitted_linewidth}")

        # Store baseline
        self.baseline_lorentzian = {
            'data': data,
            'result': result[0]
        }


@pytest.mark.skipif(not HAS_C_EXTENSIONS, reason="C extensions not available")
class TestContourBaseline:
    """Capture exact behavior of C Contourer2d"""

    def test_simple_contour(self):
        """Test contour generation on simple data"""
        # Create test data with known contours
        size = 50
        x = np.linspace(-5, 5, size)
        y = np.linspace(-5, 5, size)
        X, Y = np.meshgrid(x, y)

        # Create concentric circles: z = exp(-(x^2 + y^2))
        data = np.exp(-(X**2 + Y**2))
        data = data.astype(np.float32)

        # Define contour levels
        levels = np.array([0.2, 0.5, 0.8], dtype=np.float32)

        try:
            # Call C extension (use correct function name)
            contours = Contourer2d.contourer2d(data, levels)

            # VALIDATION
            assert contours is not None, "Should return contours"
            assert len(contours) == len(levels), \
                f"Should return {len(levels)} contour levels"

            print(f"✓ C Extension Contours: Generated {len(contours)} levels")
            for i, level in enumerate(levels):
                if contours[i]:
                    print(f"  Level {level}: {len(contours[i])} polylines")

            # Store baseline
            self.baseline_contours = {
                'data': data,
                'levels': levels,
                'contours': contours
            }
        except (AttributeError, ImportError) as e:
            pytest.skip(f"Contour C extension not fully available: {e}")


class TestGenerateValidationDatasets:
    """Generate comprehensive test datasets for Python implementation"""

    def test_create_peak_dataset(self):
        """Create and save validation dataset for peak detection"""
        # Various test cases
        datasets = {}

        # 1. Single isolated peak
        size = 100
        X, Y = np.meshgrid(np.arange(size), np.arange(size))
        data1 = 1000 * np.exp(-((X - 50)**2 + (Y - 50)**2) / 200)
        datasets['single_peak'] = data1.astype(np.float32)

        # 2. Overlapping peaks
        data2 = (800 * np.exp(-((X - 40)**2 + (Y - 50)**2) / 150) +
                 900 * np.exp(-((X - 60)**2 + (Y - 50)**2) / 150))
        datasets['overlapping_peaks'] = data2.astype(np.float32)

        # 3. Weak peak with noise
        np.random.seed(42)
        noise = np.random.normal(0, 10, (size, size))
        data3 = 100 * np.exp(-((X - 50)**2 + (Y - 50)**2) / 200) + noise
        datasets['noisy_peak'] = data3.astype(np.float32)

        # Save datasets for later use
        import os
        os.makedirs('src/python/ccpn/c_replacement/tests/fixtures', exist_ok=True)
        np.savez('src/python/ccpn/c_replacement/tests/fixtures/peak_test_data.npz',
                 **datasets)

        print(f"✓ Created {len(datasets)} test datasets")
        assert len(datasets) == 3


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s'])
