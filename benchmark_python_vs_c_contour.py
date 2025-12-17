#!/usr/bin/env python3
"""
Benchmark Python contour implementation vs C extension.

This is the critical test - we need to match or exceed C performance.
"""

import numpy as np
import time
import sys

def create_test_data(size=512):
    """Create realistic NMR-like test data."""
    X, Y = np.meshgrid(np.arange(size), np.arange(size))

    # Simulate multiple peaks (like real NMR data)
    data = np.zeros((size, size), dtype=np.float32)

    # Add 5 Gaussian peaks at different positions
    peaks = [
        (size//4, size//4, 2000),
        (size//2, size//2, 5000),
        (3*size//4, size//4, 1500),
        (size//4, 3*size//4, 3000),
        (3*size//4, 3*size//4, 2500),
    ]

    for px, py, intensity in peaks:
        data += intensity * np.exp(-((X - px)**2 + (Y - py)**2) / 200)

    # Add some noise
    data += np.random.normal(0, 50, (size, size)).astype(np.float32)

    return data


def benchmark_c_extension(data, pos_levels, neg_levels, num_runs=5):
    """Benchmark C extension contourerGLList."""
    try:
        from ccpnc.contour import Contourer2d as CContourer2d
    except ImportError:
        print("WARNING: C extension not available for benchmarking")
        return None

    # Setup
    dataArrays = (data,)
    posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
    negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

    # Warm-up
    _ = CContourer2d.contourerGLList(dataArrays, pos_levels, neg_levels,
                                      posColour, negColour, 0)

    # Benchmark
    times = []
    for _ in range(num_runs):
        start = time.perf_counter()
        result = CContourer2d.contourerGLList(dataArrays, pos_levels, neg_levels,
                                               posColour, negColour, 0)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        'mean': np.mean(times),
        'std': np.std(times),
        'min': np.min(times),
        'max': np.max(times),
        'result': result
    }


def benchmark_python_implementation(data, pos_levels, neg_levels, num_runs=5):
    """Benchmark Python contourerGLList."""
    from ccpn.c_replacement.contour_numba import contourerGLList

    # Setup
    dataArrays = (data,)
    posColour = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
    negColour = np.array([0.0, 0.0, 1.0, 1.0], dtype=np.float32)

    # Warm-up (triggers Numba JIT compilation)
    print("  Warming up (JIT compilation)...", end='', flush=True)
    _ = contourerGLList(dataArrays, pos_levels[:1], neg_levels,
                        posColour, negColour, 0)
    print(" done")

    # Benchmark
    times = []
    for _ in range(num_runs):
        start = time.perf_counter()
        result = contourerGLList(dataArrays, pos_levels, neg_levels,
                                 posColour, negColour, 0)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        'mean': np.mean(times),
        'std': np.std(times),
        'min': np.min(times),
        'max': np.max(times),
        'result': result
    }


def verify_results_similar(c_result, python_result, tolerance=0.01):
    """Verify Python and C results are similar."""
    if c_result is None:
        return True  # Can't compare if C not available

    c_indices, c_vertices, c_indexing, c_verts, c_colours = c_result
    p_indices, p_vertices, p_indexing, p_verts, p_colours = python_result

    print(f"\n  Results comparison:")
    print(f"    C:      {c_indices} indices, {c_vertices} vertices")
    print(f"    Python: {p_indices} indices, {p_vertices} vertices")

    # Allow some variation due to algorithm differences
    vertex_diff = abs(c_vertices - p_vertices) / max(c_vertices, 1)

    if vertex_diff < tolerance:
        print(f"    ✓ Results similar (vertex count diff: {vertex_diff*100:.1f}%)")
        return True
    else:
        print(f"    ⚠ Results differ (vertex count diff: {vertex_diff*100:.1f}%)")
        return False


def main():
    print("=" * 70)
    print("CRITICAL TEST: Python vs C Extension Contour Performance")
    print("=" * 70)

    # Test configurations
    test_cases = [
        ("Small (128x128, 3 levels)", 128, 3),
        ("Medium (256x256, 5 levels)", 256, 5),
        ("Large (512x512, 5 levels)", 512, 5),
        ("Production (512x512, 10 levels)", 512, 10),
    ]

    all_results = []

    for test_name, size, num_levels in test_cases:
        print(f"\n{'=' * 70}")
        print(f"Test: {test_name}")
        print(f"{'=' * 70}")

        # Create test data
        data = create_test_data(size)

        # Create levels
        max_val = np.max(data)
        pos_levels = np.linspace(max_val * 0.1, max_val * 0.9, num_levels).astype(np.float32)
        neg_levels = np.array([], dtype=np.float32)

        print(f"Data: {size}x{size}, Levels: {num_levels}")
        print(f"Max value: {max_val:.1f}")

        # Benchmark C extension
        print("\nBenchmarking C extension...")
        c_stats = benchmark_c_extension(data, pos_levels, neg_levels, num_runs=5)

        if c_stats:
            print(f"  Mean: {c_stats['mean']*1000:.2f} ms ± {c_stats['std']*1000:.2f} ms")
            print(f"  Range: {c_stats['min']*1000:.2f} - {c_stats['max']*1000:.2f} ms")

        # Benchmark Python
        print("\nBenchmarking Python implementation...")
        python_stats = benchmark_python_implementation(data, pos_levels, neg_levels, num_runs=5)
        print(f"  Mean: {python_stats['mean']*1000:.2f} ms ± {python_stats['std']*1000:.2f} ms")
        print(f"  Range: {python_stats['min']*1000:.2f} - {python_stats['max']*1000:.2f} ms")

        # Compare
        if c_stats:
            speedup = c_stats['mean'] / python_stats['mean']
            print(f"\n  Performance ratio: Python is {speedup:.2f}x {'FASTER' if speedup > 1 else 'SLOWER'} than C")

            if speedup < 1:
                print(f"  ⚠ WARNING: Python slower by {(1/speedup):.2f}x")
            elif speedup > 1:
                print(f"  ✓ SUCCESS: Python faster by {speedup:.2f}x!")

            # Verify results
            verify_results_similar(c_stats['result'], python_stats['result'])

            all_results.append({
                'test': test_name,
                'c_time': c_stats['mean'],
                'python_time': python_stats['mean'],
                'speedup': speedup
            })
        else:
            all_results.append({
                'test': test_name,
                'c_time': None,
                'python_time': python_stats['mean'],
                'speedup': None
            })

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    if any(r['c_time'] is not None for r in all_results):
        print("\nTest                              C (ms)    Python (ms)   Speedup")
        print("-" * 70)
        for r in all_results:
            if r['c_time'] is not None:
                status = "✓" if r['speedup'] >= 1.0 else "⚠"
                print(f"{status} {r['test']:30s} {r['c_time']*1000:8.2f}  {r['python_time']*1000:8.2f}     {r['speedup']:.2f}x")
            else:
                print(f"  {r['test']:30s}     N/A    {r['python_time']*1000:8.2f}       N/A")

        # Overall assessment
        print("\n" + "=" * 70)
        avg_speedup = np.mean([r['speedup'] for r in all_results if r['speedup'] is not None])
        print(f"Average speedup: {avg_speedup:.2f}x")

        if avg_speedup >= 1.0:
            print("\n✓ SUCCESS: Python implementation meets or exceeds C performance!")
            print(f"  Team goal achieved: Python is {avg_speedup:.2f}x faster than C on average")
            return 0
        else:
            print(f"\n⚠ CONCERN: Python is {1/avg_speedup:.2f}x slower than C on average")
            print("  May need optimization work")
            return 1
    else:
        print("\nC extension not available for comparison")
        print("Python-only benchmarks:")
        for r in all_results:
            print(f"  {r['test']:30s} {r['python_time']*1000:8.2f} ms")
        return 0


if __name__ == '__main__':
    sys.exit(main())
