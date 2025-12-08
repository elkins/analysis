"""
Pure Python + NumPy implementation of 2D contour generation.

This module provides a Python replacement for the C extension npy_contourer2d.c,
implementing the marching squares algorithm for generating contour lines at
specified levels in 2D spectral data.

API matches the C implementation:
    calculate_contours(data, levels) -> List[List[ndarray]]

Reference:
    Original C: src/c/ccpnc/contour/npy_contourer2d.c
    Algorithm: Marching squares with vertex linking
    Proven approach: ccpnmr2.4/python/memops/global_/python_impl/contourer.py
"""

import numpy as np
from typing import List, Tuple, Optional
import sys


def calculate_contours(data: np.ndarray, levels: np.ndarray) -> List[List[np.ndarray]]:
    """
    Generate contour polylines for 2D data at specified levels.

    This is the main API function matching the C implementation.

    Args:
        data: 2D NumPy array of float values [y][x]
        levels: 1D NumPy array of contour levels (must be monotonic)

    Returns:
        List of lists of polylines (one list per level).
        Each polyline is a 1D NumPy array [x0, y0, x1, y1, ...] of float32.

    Raises:
        ValueError: If data is not 2D or levels not 1D
        ValueError: If levels are not monotonic

    Example:
        >>> data = np.exp(-(X**2 + Y**2))  # Gaussian hill
        >>> levels = np.array([0.3, 0.5, 0.7], dtype=np.float32)
        >>> contours = calculate_contours(data, levels)
        >>> len(contours)  # One list per level
        3
        >>> len(contours[0])  # Number of polylines at first level
        1
    """
    # Input validation (matching C code lines 988-994)
    if not isinstance(data, np.ndarray):
        raise TypeError("data must be a NumPy array")

    if not isinstance(levels, np.ndarray):
        raise TypeError("levels must be a NumPy array")

    if data.ndim != 2:
        raise ValueError("dataArray needs to be NumPy array with ndim 2")

    if levels.ndim != 1:
        raise ValueError("levelsArray needs to be NumPy array with ndim 1")

    # Convert to float32 if needed (C expects NPY_FLOAT)
    if data.dtype != np.float32:
        data = data.astype(np.float32)

    if levels.dtype != np.float32:
        levels = levels.astype(np.float32)

    # Handle empty levels
    nlevels = len(levels)
    if nlevels == 0:
        return []

    # Check level monotonicity (C code lines 913-926)
    if nlevels > 1:
        are_levels_increasing = _check_levels_monotonic(levels)
    else:
        are_levels_increasing = True  # Arbitrary for single level

    # Create output list
    contours_list = []

    # Process each level
    for l in range(nlevels):
        level = float(levels[l])

        # Find vertices using marching squares
        vertices = _find_vertices_marching_squares(data, level)

        # Link vertices into polylines
        polylines = _process_chains(vertices)

        contours_list.append(polylines)

        # Early termination optimization from C code (line 965):
        # If no vertices found, can skip remaining levels in some cases
        # However, this should not break for all cases - only when we know
        # subsequent levels won't have contours either
        # For now, skip this optimization to match expected behavior
        # if len(vertices) == 0 and l < nlevels - 1:
        #     break

    return contours_list


def _check_levels_monotonic(levels: np.ndarray) -> bool:
    """
    Check that levels are monotonically increasing or decreasing.

    Matches C code lines 913-926.

    Returns:
        True if increasing, False if decreasing

    Raises:
        ValueError: If levels are not monotonic
    """
    prev_level = levels[0]
    level = levels[1]
    are_levels_increasing = (prev_level <= level)

    for l in range(2, len(levels)):
        prev_level = level
        level = levels[l]

        if are_levels_increasing:
            if prev_level > level:
                raise ValueError("levels initially increasing but later decrease")
        else:
            if prev_level < level:
                raise ValueError("levels initially decreasing but later increase")

    return are_levels_increasing


def _find_vertices_marching_squares(data: np.ndarray, level: float) -> List[Tuple[float, float, int, int]]:
    """
    Find all edge crossings using marching squares algorithm.

    Returns list of vertices: (x, y, edge_type, cell_index)
    where edge_type indicates which edge of the cell (0=bottom, 1=right, 2=top, 3=left)
    """
    height, width = data.shape
    vertices = []

    # Scan through all 2x2 cells
    for y in range(height - 1):
        for x in range(width - 1):
            # Get corner values
            v00 = data[y, x]
            v10 = data[y, x + 1]
            v01 = data[y + 1, x]
            v11 = data[y + 1, x + 1]

            # Determine marching squares case (4-bit index)
            case = 0
            if v00 >= level:
                case |= 1
            if v10 >= level:
                case |= 2
            if v11 >= level:
                case |= 4
            if v01 >= level:
                case |= 8

            # Skip if no edges cross (all above or all below)
            if case == 0 or case == 15:
                continue

            # Process edges for this case
            cell_id = y * (width - 1) + x
            edges = _get_edges_for_case(case)

            for edge in edges:
                # Calculate interpolated vertex position
                vx, vy = _interpolate_vertex(x, y, edge, v00, v10, v11, v01, level)
                vertices.append((vx, vy, edge, cell_id))

    return vertices


# Marching squares lookup table
# Maps 4-bit case index to list of edge pairs
# Edge numbering: 0=bottom, 1=right, 2=top, 3=left
_MARCHING_SQUARES_CASES = [
    [],              # 0000 - no contour
    [(3, 0)],        # 0001 - bottom-left corner
    [(0, 1)],        # 0010 - bottom-right corner
    [(3, 1)],        # 0011 - bottom edge
    [(1, 2)],        # 0100 - top-right corner
    [(3, 0), (1, 2)], # 0101 - saddle (ambiguous)
    [(0, 2)],        # 0110 - right edge
    [(3, 2)],        # 0111 - top-right region
    [(2, 3)],        # 1000 - top-left corner
    [(0, 2)],        # 1001 - left edge (note: same as case 6)
    [(0, 1), (2, 3)], # 1010 - saddle (ambiguous)
    [(1, 2)],        # 1011 - top edge
    [(1, 3)],        # 1100 - top edge (different orientation)
    [(0, 1)],        # 1101 - bottom edge (different orientation)
    [(0, 3)],        # 1110 - left-bottom region
    [],              # 1111 - no contour
]


def _get_edges_for_case(case: int) -> List[Tuple[int, int]]:
    """Get edge pairs for a marching squares case."""
    return _MARCHING_SQUARES_CASES[case]


def _interpolate_vertex(x: int, y: int, edge: int,
                        v00: float, v10: float, v11: float, v01: float,
                        level: float) -> Tuple[float, float]:
    """
    Interpolate vertex position on cell edge.

    Args:
        x, y: Cell bottom-left corner
        edge: Edge number (0=bottom, 1=right, 2=top, 3=left)
        v00, v10, v11, v01: Corner values (bottom-left, bottom-right, top-right, top-left)
        level: Contour level

    Returns:
        (vx, vy): Interpolated vertex position
    """
    if edge == 0:  # Bottom edge
        t = _linear_interpolate(v00, v10, level)
        return (x + t, y)
    elif edge == 1:  # Right edge
        t = _linear_interpolate(v10, v11, level)
        return (x + 1, y + t)
    elif edge == 2:  # Top edge
        t = _linear_interpolate(v01, v11, level)
        return (x + t, y + 1)
    else:  # edge == 3, Left edge
        t = _linear_interpolate(v00, v01, level)
        return (x, y + t)


def _linear_interpolate(v1: float, v2: float, level: float) -> float:
    """
    Linear interpolation between two values.

    Returns parameter t in [0, 1] where level crosses between v1 and v2.
    """
    if abs(v2 - v1) < 1e-10:
        return 0.5

    t = (level - v1) / (v2 - v1)

    # Clamp to [0, 1]
    return max(0.0, min(1.0, t))


def _process_chains(vertices: List[Tuple[float, float, int, int]]) -> List[np.ndarray]:
    """
    Link vertices into polyline chains using connectivity.

    Groups vertices that are part of the same contour by tracking which
    cells they belong to and finding connected components.

    Args:
        vertices: List of (x, y, edge, cell_id) tuples

    Returns:
        List of polylines, each as 1D array [x0, y0, x1, y1, ...]
    """
    if len(vertices) == 0:
        return []

    # Build connectivity graph: vertices that share a cell are connected
    n = len(vertices)
    visited = [False] * n

    polylines = []

    # Find connected components using DFS
    for start_idx in range(n):
        if visited[start_idx]:
            continue

        # Start new polyline
        component = []
        stack = [start_idx]

        while stack:
            idx = stack.pop()
            if visited[idx]:
                continue

            visited[idx] = True
            component.append(idx)

            # Find neighbors (vertices in same or adjacent cells)
            x1, y1, edge1, cell1 = vertices[idx]

            for j in range(n):
                if visited[j]:
                    continue

                x2, y2, edge2, cell2 = vertices[j]

                # Check if vertices are close (same region)
                dist = ((x1 - x2)**2 + (y1 - y2)**2)**0.5

                if dist < 2.0:  # Adjacent vertices
                    stack.append(j)

        # Convert component to polyline
        if len(component) > 0:
            coords = [vertices[i][:2] for i in component]  # Extract (x, y)

            # Convert to flat array
            flat_coords = []
            for x, y in coords:
                flat_coords.extend([x, y])

            polyline = np.array(flat_coords, dtype=np.float32)
            polylines.append(polyline)

    return polylines


# Module-level exports
__all__ = ['calculate_contours']


if __name__ == '__main__':
    # Quick test
    print("Contour module loaded successfully")

    # Simple test
    size = 50
    X, Y = np.meshgrid(np.arange(size), np.arange(size))
    data = np.exp(-((X - 25)**2 + (Y - 25)**2) / 100).astype(np.float32)
    levels = np.array([0.5], dtype=np.float32)

    try:
        result = calculate_contours(data, levels)
        print(f"✓ Generated {len(result)} level(s)")
        print(f"✓ Level 0 has {len(result[0])} polyline(s)")
        if len(result[0]) > 0:
            print(f"✓ First polyline has {len(result[0][0])} coordinates")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
