"""
Run All Discovery Sources

Executes all discovery scripts in optimal order to populate the candidate database.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def run_script(name, command, cwd=None, timeout=600):
    """Run a discovery command and report results."""
    print(f"\n{'='*70}")
    print(f"Running: {name}")
    print(f"{'='*70}\n")

    if cwd is None:
        cwd = ROOT

    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True
        )

        if result.returncode == 0:
            print(result.stdout)
            print(f"\n[SUCCESS] {name} completed")
            return True
        else:
            print(f"[ERROR] {name} failed:")
            print(result.stderr)
            return False

    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {name} timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"[ERROR] running {name}: {e}")
        return False


def main():
    """Run all discovery sources in optimal order."""
    print("""
==================================================================
            AncientWorld Multi-Source Discovery
                  Run All Sources
==================================================================

This will run all discovery sources in optimal order:
1. Met Museum (fast, high-quality)
2. Wikimedia Commons (broad coverage)
3. Europeana (European institutions)
4. Gallica (French National Library)
5. Internet Archive (architectural books)
6. IIIF Manifest Processing

Press Ctrl+C to cancel at any time.
""")

    input("Press Enter to start...")

    results = {}

    # Phase 1: Direct image sources
    print("\n" + "="*70)
    print("PHASE 1: Direct Image Sources")
    print("="*70)

    results['Met Museum'] = run_script(
        "Met Museum",
        ["python", "tools/met_discover.py"],
        timeout=300
    )

    results['Wikimedia Commons'] = run_script(
        "Wikimedia Commons",
        ["python", "-m", "scrapy", "crawl", "commons_discover"],
        cwd=ROOT / "ancientgeo",
        timeout=600
    )

    results['Europeana'] = run_script(
        "Europeana",
        ["python", "tools/europeana_discover.py"],
        timeout=300
    )

    # Phase 2: IIIF manifest sources
    print("\n" + "="*70)
    print("PHASE 2: IIIF Manifest Sources")
    print("="*70)

    results['Gallica'] = run_script(
        "Gallica (BnF)",
        ["python", "tools/gallica_discover.py"],
        timeout=300
    )

    results['Internet Archive'] = run_script(
        "Internet Archive",
        ["python", "tools/archive_org_discover.py"],
        timeout=300
    )

    # Phase 3: Process IIIF manifests
    print("\n" + "="*70)
    print("PHASE 3: IIIF Manifest Processing")
    print("="*70)

    results['IIIF Processing'] = run_script(
        "IIIF Manifest Harvesting",
        ["python", "tools/iiif_harvest_manifest.py"],
        timeout=600
    )

    # Summary
    print("\n" + "="*70)
    print("DISCOVERY COMPLETE!")
    print("="*70)

    successful = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nResults: {successful}/{total} sources completed successfully\n")

    for source, success in results.items():
        status = "[SUCCESS]" if success else "[FAILED]"
        print(f"  {status} {source}")

    print("\n" + "="*70)
    print("Next steps:")
    print("  1. Check stats in GUI: streamlit run src/ui/web/dashboard.py")
    print("  2. Start download: python tools/download_capped.py")
    print("="*70)

    return 0 if successful == total else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Stopped by user")
        sys.exit(130)
