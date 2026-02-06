"""
British Library Discovery

Searches the British Library's digital collections.
Excellent for medieval manuscripts and architectural drawings.
"""

import sqlite3
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, REQUEST_TIMEOUT
from config.search_queries import QUERIES

# British Library uses various APIs - this uses their image service
BASE_URL = "https://www.bl.uk"
USER_AGENT = "AncientWorld/1.0 (bl harvester; https://github.com/robertwaltos/AncientWorld)"


def main():
    """
    Note: British Library collections require specific API access.
    This is a placeholder for when BL access is configured.
    For now, we recommend using their IIIF collections once available.
    """
    print("=" * 60)
    print("British Library Discovery")
    print("=" * 60)
    print("NOTE: British Library requires specific API configuration.")
    print("Consider using BL's IIIF collections once endpoints are identified.")
    print("Placeholder created for future implementation.")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
