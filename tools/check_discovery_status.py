"""Quick script to check discovery status"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH

con = sqlite3.connect(Path(DB_PATH))
cur = con.cursor()

print('=' * 70)
print('DISCOVERY STATUS')
print('=' * 70)

print('\nCANDIDATES (Direct Images):')
for row in cur.execute('SELECT source, status, COUNT(*) FROM candidates GROUP BY source, status ORDER BY source, status').fetchall():
    print(f'  {row[0]:20s} {row[1]:15s} {row[2]:6,}')

total_candidates = cur.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
print(f'\n  Total candidates: {total_candidates:,}')

print('\nMANIFESTS (IIIF to process):')
for row in cur.execute('SELECT source, status, COUNT(*) FROM manifests GROUP BY source, status ORDER BY source, status').fetchall():
    print(f'  {row[0]:20s} {row[1]:15s} {row[2]:6,}')

total_manifests = cur.execute('SELECT COUNT(*) FROM manifests').fetchone()[0]
print(f'\n  Total manifests: {total_manifests:,}')

print('\n' + '=' * 70)
print(f'READY TO HARVEST: {total_manifests:,} IIIF manifests')
print(f'READY TO DOWNLOAD: {total_candidates:,} direct images')
print('=' * 70)

con.close()
