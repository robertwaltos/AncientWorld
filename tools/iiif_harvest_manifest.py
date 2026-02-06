"""
IIIF Manifest Harvester

Processes IIIF manifests from the database and extracts individual image URLs.
Works with Gallica, Internet Archive, Europeana, and any IIIF-compliant source.

IIIF Image API: https://iiif.io/api/image/3.0/
"""

import json
import sqlite3
import sys
import time
from pathlib import Path

import requests

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, REQUEST_TIMEOUT

USER_AGENT = "AncientWorld/1.0 (iiif harvester; https://github.com/robertwaltos/AncientWorld)"


def find_iiif_image_services(manifest):
    """
    Recursively find IIIF Image API service IDs in a IIIF Presentation manifest.
    
    Supports IIIF v2 and v3 patterns.
    Returns list of service IDs (base URLs for images).
    """
    services = []
    
    def walk(node):
        if isinstance(node, dict):
            # v2: "service": {"@id": "...", "profile": "..."}
            # v3: "service": [{"id": "...", "type": "ImageService3"}]
            svc = node.get("service")
            
            if isinstance(svc, dict):
                sid = svc.get("@id") or svc.get("id")
                if sid and isinstance(sid, str):
                    services.append(sid)
            elif isinstance(svc, list):
                for s in svc:
                    if isinstance(s, dict):
                        sid = s.get("@id") or s.get("id")
                        if sid and isinstance(sid, str):
                            services.append(sid)
            
            # Recursively process all values
            for v in node.values():
                walk(v)
                
        elif isinstance(node, list):
            for x in node:
                walk(x)
    
    walk(manifest)
    
    # Deduplicate while preserving order
    seen = set()
    unique_services = []
    for s in services:
        if s not in seen:
            unique_services.append(s)
            seen.add(s)
    
    return unique_services


def iiif_full_image_url(service_id):
    """
    Build IIIF Image API URL for full resolution image.
    
    IIIF Image API URL pattern:
    {scheme}://{server}{/prefix}/{identifier}/{region}/{size}/{rotation}/{quality}.{format}
    
    For full image:
    {service_id}/full/max/0/default.jpg
    """
    service_id = service_id.rstrip("/")
    return f"{service_id}/full/max/0/default.jpg"


def main(batch_size=50):
    """Process pending IIIF manifests and extract image candidates."""
    print("=" * 60)
    print("IIIF Manifest Harvester")
    print("=" * 60)
    
    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found. Run init_database.py first.")
        return 1
    
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")
    cur = con.cursor()
    
    # Count pending manifests
    (pending_count,) = cur.execute("""
        SELECT COUNT(*) FROM manifests WHERE status='pending'
    """).fetchone()
    
    print(f"Pending manifests: {pending_count:,}\n")
    
    if pending_count == 0:
        print("No pending manifests to process.")
        con.close()
        return 0
    
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    
    total_added = 0
    processed = 0
    
    while True:
        # Fetch batch of pending manifests
        rows = cur.execute("""
            SELECT id, source, query, record_url, manifest_url, title
            FROM manifests
            WHERE status='pending'
            ORDER BY id ASC
            LIMIT ?
        """, (batch_size,)).fetchall()
        
        if not rows:
            break
        
        for mid, source, query, record_url, manifest_url, title in rows:
            try:
                # Mark as downloading
                cur.execute("""
                    UPDATE manifests 
                    SET status='downloading', updated_at=datetime('now') 
                    WHERE id=?
                """, (mid,))
                con.commit()
                
                # Fetch manifest
                print(f"[{source}] Processing manifest {mid}: {title[:50] if title else 'Untitled'}...")
                r = session.get(manifest_url, timeout=REQUEST_TIMEOUT)
                r.raise_for_status()
                manifest = r.json()
                
                # Extract image service IDs
                service_ids = find_iiif_image_services(manifest)
                
                if not service_ids:
                    print(f"  WARNING: No image services found in manifest")
                    cur.execute("""
                        UPDATE manifests 
                        SET status='done', updated_at=datetime('now') 
                        WHERE id=?
                    """, (mid,))
                    con.commit()
                    continue
                
                # Add image candidates
                added = 0
                for sid in service_ids:
                    img_url = iiif_full_image_url(sid)
                    
                    cur.execute("""
                        INSERT OR IGNORE INTO candidates(
                            source, query, title, page_url, image_url, status
                        )
                        VALUES (?, ?, ?, ?, ?, 'pending')
                    """, (source, query, title, record_url or manifest_url, img_url))
                    
                    if cur.rowcount > 0:
                        added += 1
                
                # Mark manifest as done
                cur.execute("""
                    UPDATE manifests 
                    SET status='done', updated_at=datetime('now') 
                    WHERE id=?
                """, (mid,))
                con.commit()
                
                total_added += added
                processed += 1
                
                print(f"  Added {added} image candidates (total: {total_added:,})")
                
            except Exception as e:
                print(f"  ERROR: {e}")
                cur.execute("""
                    UPDATE manifests 
                    SET status='failed', updated_at=datetime('now') 
                    WHERE id=?
                """, (mid,))
                con.commit()
                continue
            
            # Rate limiting
            time.sleep(0.5)
        
        if processed % 100 == 0:
            print(f"\nProgress: {processed}/{pending_count} manifests processed")
            print(f"Total images extracted: {total_added:,}\n")
    
    con.close()
    
    print("=" * 60)
    print("IIIF Manifest Harvesting Complete!")
    print(f"Processed: {processed:,} manifests")
    print(f"Total image candidates added: {total_added:,}")
    print("\nNext step: Run download_capped.py to download images")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
