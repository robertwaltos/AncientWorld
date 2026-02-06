#!/usr/bin/env python3
"""
Parallel discovery orchestrator - runs all discovery sources simultaneously.

Usage:
    python tools/run_all_discovery_parallel.py
"""

import sys
import subprocess
import multiprocessing as mp
from pathlib import Path
from typing import Tuple
import time

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# All discovery sources with their scripts
DISCOVERY_SOURCES = [
    ("Met Museum", "tools/met_discover.py"),
    ("Europeana", "tools/europeana_discover.py"),
    ("Smithsonian", "tools/smithsonian_discover.py"),
    ("Getty", "tools/getty_discover.py"),
    ("Archive.org", "tools/archive_org_discover.py"),
    ("British Library", "tools/british_library_discover.py"),
    ("Gallica (API)", "tools/gallica_discover.py"),
    ("Gallica (Direct)", "tools/gallica_direct_images.py"),
]


def run_discovery_source(name: str, script_path: str, timeout: int = 1800) -> Tuple[str, bool, str, float]:
    """
    Run a single discovery source.

    Args:
        name: Display name of the source
        script_path: Path to discovery script
        timeout: Maximum execution time in seconds (default 30 minutes)

    Returns:
        Tuple of (name, success, message, elapsed_time)
    """
    script = ROOT / script_path
    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(ROOT)
        )

        elapsed = time.time() - start_time

        if result.returncode == 0:
            # Extract useful info from output
            output = result.stdout.strip()
            lines = output.split('\n')
            last_line = lines[-1] if lines else "Completed"

            return (name, True, f"Completed: {last_line}", elapsed)
        else:
            error = result.stderr.strip() if result.stderr else result.stdout.strip()
            error_msg = error.split('\n')[-1] if error else "Unknown error"
            return (name, False, f"Error: {error_msg[:100]}", elapsed)

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        return (name, False, f"Timeout after {timeout//60} minutes", elapsed)

    except Exception as e:
        elapsed = time.time() - start_time
        return (name, False, f"Error: {str(e)[:100]}", elapsed)


def run_all_parallel(max_workers: int = None) -> list:
    """
    Run all discovery sources in parallel.

    Args:
        max_workers: Maximum number of parallel workers (None = use all sources)

    Returns:
        List of results: [(name, success, message, elapsed_time), ...]
    """
    if max_workers is None:
        max_workers = len(DISCOVERY_SOURCES)

    print(f"Starting parallel discovery with {max_workers} workers")
    print(f"Sources: {len(DISCOVERY_SOURCES)}")
    print()

    # Create work items
    work_items = [(name, script) for name, script in DISCOVERY_SOURCES]

    # Run in parallel
    with mp.Pool(processes=max_workers) as pool:
        results = pool.starmap(run_discovery_source, work_items)

    return results


def print_results(results: list):
    """Print formatted results."""
    print()
    print("=" * 80)
    print("DISCOVERY RESULTS")
    print("=" * 80)

    successful = sum(1 for _, success, _, _ in results if success)
    failed = len(results) - successful

    for name, success, message, elapsed in results:
        status = "[OK]" if success else "[FAIL]"
        elapsed_str = f"{elapsed:.1f}s"
        print(f"{status:6} {name:25} {elapsed_str:>8} - {message}")

    print("=" * 80)
    print(f"Summary: {successful} succeeded, {failed} failed")
    print("=" * 80)


def main():
    """Main entry point."""
    results = run_all_parallel()
    print_results(results)

    # Exit with error code if any failed
    failed = sum(1 for _, success, _, _ in results if not success)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
