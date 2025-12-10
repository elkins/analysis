"""
Quick NMR Contour Demo (non-interactive, saves plots only)
"""
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

# Now import the demo module
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'python'))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import time

from ccpn.c_replacement.contour_compat import Contourer2d, get_implementation_info


def main():
    print("\n" + "="*70)
    print("Quick 3D NMR Contour Demonstration")
    print("="*70 + "\n")

    # Show implementation
    info = get_implementation_info()
    print(f"Using: {info['implementation']}")
    print(f"Module: {info['module'].__name__}\n")

    # Generate simulated 3D NMR data (smaller for speed)
    print("Generating 3D NMR data...")
    nz, ny, nx = 32, 64, 64

    # Create a simple 3D Gaussian peak
    z, y, x = np.meshgrid(np.arange(nz), np.arange(ny), np.arange(nx), indexing='ij')
    data_3d = (
        0.8 * np.exp(-((z-16)**2 + (y-32)**2 + (x-32)**2) / 80) +
        0.6 * np.exp(-((z-10)**2 + (y-20)**2 + (x-40)**2) / 60) +
        0.7 * np.exp(-((z-22)**2 + (y-44)**2 + (x-24)**2) / 70)
    ).astype(np.float32)

    # Add noise
    data_3d += np.random.normal(0, 0.02, data_3d.shape).astype(np.float32)

    print(f"✓ Generated {nz}×{ny}×{nx} data")
    print(f"  Range: [{data_3d.min():.3f}, {data_3d.max():.3f}]\n")

    # Extract XY plane (middle slice)
    xy_plane = data_3d[nz//2, :, :]
    print(f"Extracted XY plane: {xy_plane.shape}")

    # Generate contour levels
    data_max = xy_plane.max()
    levels = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8], dtype=np.float32) * data_max

    print(f"\nGenerating contours with {len(levels)} levels...")
    start = time.time()
    contours = Contourer2d.calculate_contours(xy_plane, levels)
    elapsed = time.time() - start

    total_polylines = sum(len(level_contours) for level_contours in contours)
    print(f"✓ Generated {total_polylines} polylines in {elapsed:.4f}s\n")

    # Create visualization
    fig, ax = plt.subplots(figsize=(10, 8))

    # Background image
    im = ax.imshow(xy_plane, origin='lower', cmap='plasma', alpha=0.4)
    plt.colorbar(im, ax=ax, label='Intensity')

    # Plot contours
    colors = cm.plasma(np.linspace(0, 1, len(levels)))

    for i, (level, level_contours) in enumerate(zip(levels, contours)):
        for polyline in level_contours:
            if len(polyline) >= 4:
                points = polyline.reshape(-1, 2)
                ax.plot(points[:, 0], points[:, 1],
                       color=colors[i], linewidth=2, alpha=0.9)

    ax.set_xlabel('F2 (points)', fontsize=12)
    ax.set_ylabel('F1 (points)', fontsize=12)
    ax.set_title(f'Simulated 3D NMR - XY Plane Contours\n'
                f'{xy_plane.shape[0]}×{xy_plane.shape[1]} data, '
                f'{len(levels)} levels, {elapsed:.3f}s\n'
                f'Implementation: {info["implementation"]}',
                fontsize=13, fontweight='bold')

    plt.tight_layout()

    # Save
    output_file = 'examples/output/nmr_contour_demo.png'
    fig.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ Saved plot to {output_file}")

    print("\n" + "="*70)
    print("Demo complete!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
