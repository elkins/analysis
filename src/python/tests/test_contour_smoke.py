"""
Smoke tests for contour module replacement.

These tests verify that the Python contour implementation works correctly
as a drop-in replacement for the C extension.
"""

import numpy as np
import pytest


def test_contour_numba_import():
    """Test that contour_numba module can be imported."""
    from ccpn.c_replacement import contour_numba
    assert contour_numba is not None
    assert hasattr(contour_numba, 'calculate_contours')
    assert hasattr(contour_numba, 'contourerGLList')


def test_contour_compat_import():
    """Test that contour_compat module can be imported."""
    from ccpn.c_replacement import contour_compat
    assert contour_compat is not None
    assert hasattr(contour_compat, 'Contourer2d')


def test_calculate_contours_basic():
    """Test basic contour generation."""
    from ccpn.c_replacement.contour_numba import calculate_contours

    # Create simple Gaussian test data
    size = 50
    X, Y = np.meshgrid(np.arange(size), np.arange(size))
    data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)
    levels = np.array([0.5], dtype=np.float32)

    # Generate contours
    contours = calculate_contours(data, levels)

    # Verify output structure
    assert isinstance(contours, list)
    assert len(contours) == 1  # One level
    assert isinstance(contours[0], list)  # List of polylines
    assert len(contours[0]) > 0  # At least one polyline


def test_contourerGLList_basic():
    """Test contourerGLList wrapper function."""
    from ccpn.c_replacement.contour_numba import contourerGLList

    # Create simple test data
    size = 50
    X, Y = np.meshgrid(np.arange(size), np.arange(size))
    data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)

    # Setup parameters
    dataArrays = (data,)
    posLevels = np.array([0.5], dtype=np.float32)
    negLevels = np.array([], dtype=np.float32)
    posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)  # Red
    negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)  # Blue

    # Call contourerGLList
    result = contourerGLList(dataArrays, posLevels, negLevels,
                            posColour, negColour, flatten=0)

    # Verify output structure
    assert isinstance(result, list)
    assert len(result) == 5

    numIndices, numVertices, indexing, vertices, colours = result

    # Check types
    assert isinstance(numIndices, int)
    assert isinstance(numVertices, int)
    assert isinstance(indexing, np.ndarray)
    assert isinstance(vertices, np.ndarray)
    assert isinstance(colours, np.ndarray)

    # Check arrays
    assert indexing.dtype == np.uint32
    assert vertices.dtype == np.float32
    assert colours.dtype == np.float32

    # Check sizes are consistent
    assert len(indexing) == numIndices
    assert len(vertices) == 2 * numVertices  # x, y pairs
    assert len(colours) == 4 * numVertices   # r, g, b, a per vertex


def test_compat_wrapper():
    """Test compatibility wrapper class."""
    from ccpn.c_replacement.contour_compat import Contourer2d

    # Create test data
    size = 50
    X, Y = np.meshgrid(np.arange(size), np.arange(size))
    data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)
    levels = np.array([0.5], dtype=np.float32)

    # Test calculate_contours through wrapper
    contours = Contourer2d.calculate_contours(data, levels)

    assert isinstance(contours, list)
    assert len(contours) == 1


def test_contourerGLList_through_wrapper():
    """Test contourerGLList through compatibility wrapper."""
    from ccpn.c_replacement.contour_compat import Contourer2d

    # Create test data
    size = 50
    X, Y = np.meshgrid(np.arange(size), np.arange(size))
    data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)

    # Setup parameters
    dataArrays = (data,)
    posLevels = np.array([0.5], dtype=np.float32)
    negLevels = np.array([], dtype=np.float32)
    posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
    negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

    # Call through wrapper
    result = Contourer2d.contourerGLList(dataArrays, posLevels, negLevels,
                                         posColour, negColour, flatten=0)

    # Verify output
    assert isinstance(result, list)
    assert len(result) == 5


def test_multiple_levels():
    """Test with multiple contour levels."""
    from ccpn.c_replacement.contour_numba import calculate_contours

    # Create test data
    size = 50
    X, Y = np.meshgrid(np.arange(size), np.arange(size))
    data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)
    levels = np.array([0.3, 0.5, 0.7], dtype=np.float32)

    # Generate contours
    contours = calculate_contours(data, levels)

    # Verify
    assert len(contours) == 3  # Three levels


def test_positive_and_negative_contours():
    """Test with both positive and negative contours."""
    from ccpn.c_replacement.contour_numba import contourerGLList

    # Create test data
    size = 50
    X, Y = np.meshgrid(np.arange(size), np.arange(size))
    data = (np.exp(-((X - 25)**2 + (Y - 25)**2) / 100) - 0.5).astype(np.float32)

    # Setup parameters
    dataArrays = (data,)
    posLevels = np.array([0.2, 0.4], dtype=np.float32)
    negLevels = np.array([-0.2, -0.4], dtype=np.float32)
    posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
    negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

    # Call contourerGLList
    result = contourerGLList(dataArrays, posLevels, negLevels,
                            posColour, negColour, flatten=0)

    # Verify we got results
    numIndices, numVertices, indexing, vertices, colours = result
    assert numVertices > 0  # Should have some vertices


def test_empty_levels():
    """Test with empty level arrays."""
    from ccpn.c_replacement.contour_numba import calculate_contours

    # Create test data
    size = 50
    X, Y = np.meshgrid(np.arange(size), np.arange(size))
    data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)
    levels = np.array([], dtype=np.float32)

    # Generate contours
    contours = calculate_contours(data, levels)

    # Should return empty list
    assert len(contours) == 0


def test_input_validation():
    """Test input validation."""
    from ccpn.c_replacement.contour_numba import calculate_contours

    # Test with wrong dimensions
    data_1d = np.array([1, 2, 3], dtype=np.float32)
    levels = np.array([0.5], dtype=np.float32)

    with pytest.raises(ValueError, match="ndim 2"):
        calculate_contours(data_1d, levels)

    # Test with wrong level dimensions
    data = np.ones((10, 10), dtype=np.float32)
    levels_2d = np.array([[0.5]], dtype=np.float32)

    with pytest.raises(ValueError, match="ndim 1"):
        calculate_contours(data, levels_2d)


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
