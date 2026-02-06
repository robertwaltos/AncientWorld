"""
Enhanced Multi-Source Discovery Runner

Runs all discovery sources with scaled-up limits and expanded queries.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run_script(name, command, timeout=600):
    """Run a discovery script."""
    print(f"\n{'='*70}")
    print(f"Running: {name}")
    print(f"{'='*70}\n")

    try:
        result = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout
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
    """Run all enhanced discovery sources."""
    print("""
======================================================================
     AncientWorld Enhanced Multi-Source Discovery (1TB Target)
======================================================================

Running all sources with:
- Increased per-query limits (500-1000 items)
- Expanded query terms (3x more searches)
- Alternative Gallica approach (direct image URLs)
- Additional museum sources

Sources:
1. Met Museum (enhanced queries)
2. Wikimedia Commons (existing)
3. Europeana (expanded queries)
4. Gallica Direct Images (NEW - avoids IIIF blocks)
5. Internet Archive (existing)
6. Rijksmuseum (NEW - requires API key)
7. Smithsonian (NEW - requires API key)

Press Ctrl+C to cancel
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
        timeout=600
    )

    results['Europeana'] = run_script(
        "Europeana (Enhanced)",
        ["python", "tools/europeana_discover.py"],
        timeout=600
    )

    results['Gallica Direct'] = run_script(
        "Gallica Direct Images (NEW)",
        ["python", "tools/gallica_direct_images.py"],
        timeout=900
    )

    # Phase 2: IIIF sources
    print("\n" + "="*70)
    print("PHASE 2: IIIF Manifest Sources")
    print("="*70)

    results['Internet Archive'] = run_script(
        "Internet Archive",
        ["python", "tools/archive_org_discover.py"],
        timeout=300
    )

    # Phase 3: Additional museums (require API keys)
    print("\n" + "="*70)
    print("PHASE 3: Additional Museum Sources (Optional)")
    print("="*70)

    results['Rijksmuseum'] = run_script(
        "Rijksmuseum (requires API key)",
        ["python", "tools/rijksmuseum_discover.py"],
        timeout=300
    )

    results['Smithsonian'] = run_script(
        "Smithsonian (requires API key)",
        ["python", "tools/smithsonian_discover.py"],
        timeout=300
    )

    # Summary
    print("\n" + "="*70)
    print("ENHANCED DISCOVERY COMPLETE!")
    print("="*70)

    successful = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nResults: {successful}/{total} sources completed successfully\n")

    for source, success in results.items():
        status = "[SUCCESS]" if success else "[FAILED]"
        print(f"  {status} {source}")

    print("\n" + "="*70)
    print("Next steps:")
    print("  1. Check stats: python -c \"from tools.show_stats import show_stats; show_stats()\"")
    print("  2. Start download: python tools/download_capped.py")
    print("  3. Or use GUI: streamlit run src/ui/web/dashboard.py")
    print("="*70)

    return 0 if successful == total else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Stopped by user")
        sys.exit(130)
