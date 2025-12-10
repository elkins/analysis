"""
Demonstration: 3D NMR Contour Visualization with Pure Python Implementation

This script generates simulated 3D NMR spectral data and creates contour plots
using the new pure Python contour implementation (no C extensions required).

Features:
- Simulates realistic 3D NMR data with multiple peaks
- Uses Python+Numba contour implementation
- Creates publication-quality contour plots
- Compares with C extension (if available)
- Demonstrates performance

Requirements:
    pip install numpy matplotlib scipy

Usage:
    python examples/demo_contour_visualization.py
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import time
import sys
import os

# Add src/python to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'python'))


def generate_3d_nmr_data(size=(128, 128, 128), num_peaks=5, noise_level=0.05):
    """
    Generate simulated 3D NMR spectral data with multiple peaks.

    Args:
        size: Tuple of (nz, ny, nx) dimensions
        num_peaks: Number of simulated peaks
        noise_level: Gaussian noise standard deviation

    Returns:
        3D numpy array of float32
    """
    print(f"Generating {size[0]}×{size[1]}×{size[2]} 3D NMR data with {num_peaks} peaks...")

    nz, ny, nx = size
    data = np.zeros(size, dtype=np.float32)

    # Random seed for reproducibility
    np.random.seed(42)

    # Generate multiple peaks at random positions
    for i in range(num_peaks):
        # Random peak center
        z_center = np.random.uniform(0.3, 0.7) * nz
        y_center = np.random.uniform(0.3, 0.7) * ny
        x_center = np.random.uniform(0.3, 0.7) * nx

        # Random peak width (linewidth)
        z_width = np.random.uniform(2.0, 5.0)
        y_width = np.random.uniform(2.0, 5.0)
        x_width = np.random.uniform(2.0, 5.0)

        # Random peak intensity
        intensity = np.random.uniform(0.5, 1.0)

        # Create 3D Gaussian peak
        z, y, x = np.meshgrid(
            np.arange(nz),
            np.arange(ny),
            np.arange(nx),
            indexing='ij'
        )

        peak = intensity * np.exp(
            -((z - z_center)**2 / (2 * z_width**2) +
              (y - y_center)**2 / (2 * y_width**2) +
              (x - x_center)**2 / (2 * x_width**2))
        )

        data += peak

        print(f"  Peak {i+1}: center=({z_center:.1f}, {y_center:.1f}, {x_center:.1f}), "
              f"intensity={intensity:.2f}")

    # Add Gaussian noise
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, size=size).astype(np.float32)
        data += noise

    print(f"✓ Data range: [{data.min():.3f}, {data.max():.3f}]")
    return data


def extract_2d_plane(data_3d, plane='xy', slice_index=None):
    """
    Extract a 2D plane from 3D data.

    Args:
        data_3d: 3D numpy array
        plane: 'xy', 'xz', or 'yz'
        slice_index: Index of slice (default: middle)

    Returns:
        2D numpy array
    """
    nz, ny, nx = data_3d.shape

    if slice_index is None:
        if plane == 'xy':
            slice_index = nz // 2
        elif plane == 'xz':
            slice_index = ny // 2
        elif plane == 'yz':
            slice_index = nx // 2

    if plane == 'xy':
        return data_3d[slice_index, :, :]
    elif plane == 'xz':
        return data_3d[:, slice_index, :]
    elif plane == 'yz':
        return data_3d[:, :, slice_index]
    else:
        raise ValueError(f"Unknown plane: {plane}")


def plot_contours_python(data_2d, title="Python Contour Implementation",
                         num_levels=10, cmap='viridis'):
    """
    Generate contour plot using pure Python implementation.

    Args:
        data_2d: 2D numpy array
        title: Plot title
        num_levels: Number of contour levels
        cmap: Matplotlib colormap

    Returns:
        Figure and axis objects
    """
    from ccpn.c_replacement.contour_compat import Contourer2d, get_implementation_info

    # Show which implementation is being used
    info = get_implementation_info()
    print(f"\n{'='*60}")
    print(f"Contour Implementation: {info['implementation']}")
    print(f"Module: {info['module'].__name__}")
    print(f"{'='*60}\n")

    # Prepare data
    data = data_2d.astype(np.float32)

    # Calculate contour levels (logarithmic spacing)
    data_max = data.max()
    data_min = max(data.min(), data_max * 0.01)  # Avoid zero
    levels = np.logspace(np.log10(data_min), np.log10(data_max), num_levels)
    levels = levels.astype(np.float32)

    print(f"Generating contours for {data.shape[0]}×{data.shape[1]} data...")
    print(f"Contour levels: {num_levels} levels from {levels.min():.3f} to {levels.max():.3f}")

    # Time the contour generation
    start_time = time.time()
    contours = Contourer2d.calculate_contours(data, levels)
    elapsed = time.time() - start_time

    print(f"✓ Contour generation: {elapsed:.4f}s")

    # Count polylines
    total_polylines = sum(len(level_contours) for level_contours in contours)
    print(f"✓ Generated {total_polylines} polylines across {len(contours)} levels")

    # Create plot
    fig, ax = plt.subplots(figsize=(10, 8))

    # Show data as background image
    im = ax.imshow(data, origin='lower', cmap=cmap, alpha=0.3, aspect='auto')
    plt.colorbar(im, ax=ax, label='Intensity')

    # Plot contours
    colors = cm.get_cmap(cmap)(np.linspace(0, 1, len(levels)))

    for i, (level, level_contours) in enumerate(zip(levels, contours)):
        for polyline in level_contours:
            if len(polyline) >= 4:  # At least 2 points
                # Reshape from flat [x0,y0,x1,y1,...] to Nx2 array
                points = polyline.reshape(-1, 2)
                ax.plot(points[:, 0], points[:, 1],
                       color=colors[i], linewidth=1.5, alpha=0.8)

    # Formatting
    ax.set_xlabel('X dimension (points)', fontsize=12)
    ax.set_ylabel('Y dimension (points)', fontsize=12)
    ax.set_title(f'{title}\n{data.shape[0]}×{data.shape[1]} data, '
                f'{num_levels} levels, {elapsed:.3f}s',
                fontsize=14, fontweight='bold')

    # Add implementation info
    impl_text = f"Implementation: {info['implementation']}"
    ax.text(0.02, 0.98, impl_text, transform=ax.transAxes,
           fontsize=10, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    return fig, ax


def compare_with_c_extension(data_2d, num_levels=10):
    """
    Compare Python and C extension performance (if C available).

    Args:
        data_2d: 2D numpy array
        num_levels: Number of contour levels
    """
    from ccpn.c_replacement.contour_compat import get_implementation_info

    # Try to import C extension
    try:
        from ccpnc.contour import Contourer2d as CContourer2d
        c_available = True
        print("\n✓ C extension available for comparison")
    except ImportError:
        c_available = False
        print("\n✗ C extension not available (comparison skipped)")
        return

    # Make sure we're using Python implementation
    info = get_implementation_info()
    if info['implementation'] == 'c_extension':
        print("⚠ Wrapper is using C extension, cannot compare")
        return

    from ccpn.c_replacement.contour_compat import Contourer2d as PyContourer2d

    # Prepare data
    data = data_2d.astype(np.float32)
    data_max = data.max()
    data_min = max(data.min(), data_max * 0.01)
    levels = np.logspace(np.log10(data_min), np.log10(data_max), num_levels)
    levels = levels.astype(np.float32)

    print(f"\nPerformance Comparison: {data.shape[0]}×{data.shape[1]} data")
    print("=" * 60)

    # Time C extension
    c_times = []
    for i in range(3):
        start = time.time()
        c_contours = CContourer2d.calculate_contours(data, levels)
        c_time = time.time() - start
        c_times.append(c_time)
        print(f"  C extension run {i+1}: {c_time:.4f}s")

    c_avg = np.mean(c_times)
    c_std = np.std(c_times)

    # Time Python implementation
    py_times = []
    for i in range(3):
        start = time.time()
        py_contours = PyContourer2d.calculate_contours(data, levels)
        py_time = time.time() - start
        py_times.append(py_time)
        print(f"  Python run {i+1}: {py_time:.4f}s")

    py_avg = np.mean(py_times)
    py_std = np.std(py_times)

    # Results
    speedup = c_avg / py_avg
    print("\n" + "=" * 60)
    print("Results:")
    print(f"  C extension:        {c_avg:.4f}s ± {c_std:.4f}s")
    print(f"  Python+Numba:       {py_avg:.4f}s ± {py_std:.4f}s")
    print(f"  Speedup:            {speedup:.2f}x")

    if speedup > 1:
        print(f"  ✓ Python is {speedup:.2f}x FASTER than C!")
    elif speedup < 0.9:
        print(f"  ⚠ Python is {1/speedup:.2f}x slower than C")
    else:
        print(f"  ✓ Python performance comparable to C")

    print("=" * 60)

    # Verify results match
    print("\nVerifying correctness...")
    if len(c_contours) == len(py_contours):
        print(f"  ✓ Same number of levels: {len(c_contours)}")

        for i in range(len(levels)):
            c_count = len(c_contours[i])
            py_count = len(py_contours[i])
            if c_count == py_count:
                print(f"  ✓ Level {i}: {c_count} polylines (both)")
            else:
                print(f"  ⚠ Level {i}: C={c_count}, Python={py_count} polylines")
    else:
        print(f"  ✗ Different number of levels: C={len(c_contours)}, Python={len(py_contours)}")


def main():
    """Main demonstration function."""
    print("\n" + "=" * 70)
    print("3D NMR Contour Visualization with Pure Python Implementation")
    print("=" * 70 + "\n")

    # Generate 3D NMR data
    data_3d = generate_3d_nmr_data(size=(64, 128, 128), num_peaks=5, noise_level=0.02)

    # Extract 2D planes
    print("\nExtracting 2D planes from 3D data...")
    xy_plane = extract_2d_plane(data_3d, plane='xy')
    xz_plane = extract_2d_plane(data_3d, plane='xz')
    yz_plane = extract_2d_plane(data_3d, plane='yz')

    print(f"✓ XY plane: {xy_plane.shape}")
    print(f"✓ XZ plane: {xz_plane.shape}")
    print(f"✓ YZ plane: {yz_plane.shape}")

    # Create contour plots for each plane
    print("\n" + "=" * 70)
    print("Generating Contour Plots")
    print("=" * 70)

    # XY plane
    fig1, ax1 = plot_contours_python(xy_plane,
                                     title="XY Plane Contours (F1-F2)",
                                     num_levels=12,
                                     cmap='plasma')

    # XZ plane
    fig2, ax2 = plot_contours_python(xz_plane,
                                     title="XZ Plane Contours (F1-F3)",
                                     num_levels=12,
                                     cmap='viridis')

    # YZ plane
    fig3, ax3 = plot_contours_python(yz_plane,
                                     title="YZ Plane Contours (F2-F3)",
                                     num_levels=12,
                                     cmap='cividis')

    # Performance comparison (if C extension available)
    compare_with_c_extension(xy_plane, num_levels=12)

    # Save figures
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(output_dir, exist_ok=True)

    fig1.savefig(os.path.join(output_dir, 'contour_xy_plane.png'), dpi=150)
    fig2.savefig(os.path.join(output_dir, 'contour_xz_plane.png'), dpi=150)
    fig3.savefig(os.path.join(output_dir, 'contour_yz_plane.png'), dpi=150)

    print(f"\n✓ Plots saved to {output_dir}/")
    print("  - contour_xy_plane.png")
    print("  - contour_xz_plane.png")
    print("  - contour_yz_plane.png")

    # Show plots
    print("\nDisplaying plots... (close windows to exit)")
    plt.show()

    print("\n" + "=" * 70)
    print("Demonstration Complete!")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
