#!/usr/bin/env python3
"""
Run all feature extraction tools in sequence.
Can be called standalone or integrated into download pipeline.
"""
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

def run_extraction(script_name: str, limit: int = None) -> tuple[bool, str]:
    """Run a feature extraction script and return success status and output."""
    script_path = ROOT / "tools" / script_name
    cmd = [sys.executable, str(script_path)]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout per tool
            cwd=str(ROOT)
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, f"Timeout after 10 minutes"
    except Exception as e:
        return False, f"Error: {e}"

def main(
    geometry: bool = True,
    scale: bool = True,
    embeddings: bool = False,
    tda: bool = False,
    verbose: bool = True
):
    """
    Run feature extraction pipeline.

    Args:
        geometry: Extract geometry features (lines, circles, symmetry)
        scale: Extract scale features (door/window aspects)
        embeddings: Extract CLIP embeddings (requires GPU, slow)
        tda: Extract TDA features (slow)
        verbose: Print progress messages
    """
    results = {}

    if geometry:
        if verbose:
            print("=" * 70)
            print("Extracting geometry features...")
            print("=" * 70)
        success, output = run_extraction("extract_geometry_features.py")
        results["geometry"] = (success, output)
        if verbose:
            print(output)
            print()

    if scale:
        if verbose:
            print("=" * 70)
            print("Extracting scale features...")
            print("=" * 70)
        success, output = run_extraction("extract_scale_features.py")
        results["scale"] = (success, output)
        if verbose:
            print(output)
            print()

    if embeddings:
        if verbose:
            print("=" * 70)
            print("Extracting CLIP embeddings...")
            print("=" * 70)
        success, output = run_extraction("clip_embed_images.py")
        results["embeddings"] = (success, output)
        if verbose:
            print(output)
            print()

    if tda:
        if verbose:
            print("=" * 70)
            print("Extracting TDA features...")
            print("=" * 70)
        success, output = run_extraction("extract_tda_features.py")
        results["tda"] = (success, output)
        if verbose:
            print(output)
            print()

    # Summary
    if verbose:
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        for name, (success, output) in results.items():
            status = "[OK]" if success else "[FAIL]"
            print(f"{status} {name}: {output}")
        print("=" * 70)

    # Return True if all enabled extractions succeeded
    return all(success for success, _ in results.values())

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run feature extraction pipeline")
    parser.add_argument("--geometry", action="store_true", default=True, help="Extract geometry features")
    parser.add_argument("--scale", action="store_true", default=True, help="Extract scale features")
    parser.add_argument("--embeddings", action="store_true", help="Extract CLIP embeddings (slow)")
    parser.add_argument("--tda", action="store_true", help="Extract TDA features (slow)")
    parser.add_argument("--all", action="store_true", help="Extract all features including slow ones")
    parser.add_argument("--quick", action="store_true", help="Only geometry and scale (fast)")

    args = parser.parse_args()

    if args.all:
        success = main(geometry=True, scale=True, embeddings=True, tda=True)
    elif args.quick:
        success = main(geometry=True, scale=True, embeddings=False, tda=False)
    else:
        success = main(
            geometry=args.geometry,
            scale=args.scale,
            embeddings=args.embeddings,
            tda=args.tda
        )

    sys.exit(0 if success else 1)
