"""
Complete workflow test script for AncientWorld.

This script guides you through testing all components.
"""

import sqlite3
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))
from config.storage_config import DB_PATH, LARGE_STORAGE_ROOT, MAX_STORAGE_GB

def print_header(text):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def check_database():
    """Check database status."""
    print_header("1. DATABASE CHECK")
    
    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("[ERROR] Database not found!")
        print(f"Expected: {db_path}")
        print("\nRun: python tools/init_database.py")
        return False
    
    print(f"[OK] Database exists: {db_path}")
    
    # Check tables
    con = sqlite3.connect(db_path)
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    
    required_tables = ['candidates', 'stats', 'analysis_results']
    for table in required_tables:
        if table in tables:
            print(f"[OK] Table '{table}' exists")
        else:
            print(f"[ERROR] Table '{table}' missing!")
            return False
    
    # Check stats
    stats = dict(con.execute("SELECT k, v FROM stats").fetchall())
    print(f"\nDatabase Statistics:")
    print(f"  Total candidates: {stats.get('total_candidates', 0):,}")
    print(f"  Files downloaded: {stats.get('total_files_downloaded', 0):,}")
    print(f"  Downloaded bytes: {stats.get('total_downloaded_bytes', 0) / 1024**3:.2f} GB")
    
    # Check candidate counts
    counts = con.execute("""
        SELECT status, COUNT(*) as count FROM candidates GROUP BY status
    """).fetchall()
    
    if counts:
        print(f"\nCandidate Status:")
        for status, count in counts:
            print(f"  {status}: {count:,}")
    else:
        print(f"\n[INFO] No candidates yet - run discovery spider")
    
    con.close()
    return True

def check_storage():
    """Check storage configuration."""
    print_header("2. STORAGE CHECK")
    
    root = Path(LARGE_STORAGE_ROOT)
    print(f"Storage root: {root}")
    print(f"Max capacity: {MAX_STORAGE_GB} GB")
    
    if not root.exists():
        print(f"[WARNING] Storage directory doesn't exist yet")
        print(f"[INFO] Will be created on first download")
    else:
        print(f"[OK] Storage directory exists")
        
        # Check subdirectories
        db_dir = root / "db"
        images_dir = root / "images"
        
        print(f"\nSubdirectories:")
        print(f"  Database: {db_dir.exists() and '[OK]' or '[MISSING]'} {db_dir}")
        print(f"  Images: {images_dir.exists() and '[OK]' or '[NOT YET]'} {images_dir}")
    
    return True

def check_dependencies():
    """Check required Python packages."""
    print_header("3. DEPENDENCIES CHECK")
    
    required = {
        'scrapy': 'Web crawling',
        'streamlit': 'GUI dashboard',
        'pandas': 'Data processing',
        'plotly': 'Charts',
        'PIL': 'Image processing (Pillow)',
        'cv2': 'OpenCV',
        'numpy': 'Numerical computing',
        'requests': 'HTTP requests',
        'imagehash': 'Perceptual hashing',
    }
    
    all_ok = True
    for package, description in required.items():
        try:
            __import__(package)
            print(f"[OK] {package:15s} - {description}")
        except ImportError:
            print(f"[MISSING] {package:15s} - {description}")
            all_ok = False
    
    if not all_ok:
        print(f"\n[ACTION] Install missing packages:")
        print(f"  pip install -r requirements.txt")
        return False
    
    return True

def show_next_steps():
    """Show recommended next steps."""
    print_header("NEXT STEPS")
    
    print("""
PHASE 1: DISCOVERY (Build candidate pool)
==========================================
Command:
  cd ancientgeo
  scrapy crawl commons_discover

Duration: 2-24 hours (leave running)
Result: 10k-100k candidates in database

Alternative: Launch GUI and use Discovery page
  streamlit run src/ui/web/dashboard.py


PHASE 2: DOWNLOAD (Fill 500GB)
================================
Command:
  python tools/download_capped.py

Duration: Hours to days (depends on internet)
Result: Images downloaded to storage root
Note: Stops automatically at 500GB cap


PHASE 3: DEDUPLICATE (Free space)
==================================
Commands:
  python tools/dedupe_exact.py          # Exact duplicates
  python tools/dedupe_perceptual.py     # Near-duplicates

Result: Typically frees 10-30% space


PHASE 4: ANALYZE (Extract features)
====================================
Single image:
  python -m src.analysis.geometry_detector image.jpg --output analyzed.jpg

Batch analysis:
  Use GUI Analysis page (streamlit run src/ui/web/dashboard.py)


GUI DASHBOARD (Recommended!)
=============================
Command:
  streamlit run src/ui/web/dashboard.py

Opens: http://localhost:8501

Features:
  - Real-time monitoring
  - Start discovery/download
  - Browse images
  - Run analysis
  - Database browser
""")

def main():
    """Run all checks."""
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║          ANCIENTWORLD WORKFLOW TEST SCRIPT            ║
    ║                                                        ║
    ║    Testing all components and showing next steps      ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    checks = [
        ("Database", check_database),
        ("Storage", check_storage),
        ("Dependencies", check_dependencies),
    ]
    
    results = []
    for name, func in checks:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] {name} check failed: {e}")
            results.append((name, False))
    
    # Summary
    print_header("SUMMARY")
    all_passed = True
    for name, result in results:
        status = "[OK]" if result else "[FAILED]"
        print(f"  {status} {name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print(f"\n[SUCCESS] All checks passed! System is ready.")
        show_next_steps()
        return 0
    else:
        print(f"\n[WARNING] Some checks failed. Fix issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
