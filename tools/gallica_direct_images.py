"""
Gallica Direct Image Discovery (Alternative Approach)

Uses Gallica SRU API to get direct image URLs instead of IIIF manifests.
This avoids the IIIF manifest endpoint blocks.
"""

import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, REQUEST_TIMEOUT
from config.search_queries import get_queries_for_source

SRU_URL = "https://gallica.bnf.fr/SRU"
USER_AGENT = "AncientWorld/1.0 (gallica direct harvester; https://github.com/robertwaltos/AncientWorld)"

NAMESPACES = {
    'srw': 'http://www.loc.gov/zing/srw/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/'
}

# Expanded French queries from centralized config
QUERIES = get_queries_for_source('gallica_direct')


def build_cql_query(search_term, doc_type):
    """Build CQL query."""
    return f'(gallica all "{search_term}") and (dc.type all "{doc_type}")'


def extract_ark_from_identifier(identifier):
    """Extract ARK identifier."""
    if "ark:/" in identifier:
        start = identifier.find("ark:/")
        ark = identifier[start:]
        ark = ark.split('.f')[0]
        ark = ark.split('/f')[0]
        return ark
    return None


def ark_to_direct_image_url(ark_identifier, page=1):
    """
    Convert ARK to direct image URL.
    Gallica provides direct image access via a simpler URL pattern.
    """
    if not ark_identifier.startswith("ark:/"):
        return None
    
    # Format: https://gallica.bnf.fr/ark:/12148/btv1b8594559c/f1.highres
    # f1 = first page, .highres = high resolution JPEG
    return f"https://gallica.bnf.fr/{ark_identifier}/f{page}.highres"


def search_gallica(query, start_record=1, max_records=50):
    """Search Gallica using SRU protocol."""
    params = {
        'version': '1.2',
        'operation': 'searchRetrieve',
        'query': query,
        'startRecord': str(start_record),
        'maximumRecords': str(min(max_records, 50)),
    }

    response = requests.get(
        SRU_URL,
        params=params,
        headers={'User-Agent': USER_AGENT},
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()

    return ET.fromstring(response.content)


def parse_sru_response(root):
    """Parse SRU XML response."""
    num_records_elem = root.find('.//srw:numberOfRecords', NAMESPACES)
    total_results = int(num_records_elem.text) if num_records_elem is not None else 0

    records = []
    for record in root.findall('.//srw:record', NAMESPACES):
        dc_elem = record.find('.//oai_dc:dc', NAMESPACES)
        if dc_elem is None:
            continue

        title_elem = dc_elem.find('dc:title', NAMESPACES)
        title = title_elem.text if title_elem is not None else None

        identifier_elem = dc_elem.find('dc:identifier', NAMESPACES)
        identifier = identifier_elem.text if identifier_elem is not None else None

        if identifier:
            ark = extract_ark_from_identifier(identifier)
            if ark:
                records.append({
                    'title': title,
                    'identifier': identifier,
                    'ark': ark
                })

    return total_results, records


def main(records_per_query=300):  # Increased limit
    """Discover direct image URLs from Gallica."""
    print("=" * 60)
    print("Gallica Direct Image Discovery")
    print("=" * 60)
    print(f"SRU Endpoint: {SRU_URL}")
    print(f"Queries: {len(QUERIES)}")
    print(f"Using direct highres image URLs\n")

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found. Run init_database.py first.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    total_added = 0

    for search_term, doc_type in QUERIES:
        print(f"[GALLICA-DIRECT] Searching: {search_term} ({doc_type})")

        try:
            cql_query = build_cql_query(search_term, doc_type)

            root = search_gallica(cql_query, start_record=1, max_records=50)
            total_results, records = parse_sru_response(root)

            print(f"  Found: {total_results:,} total results")

            all_records = records
            records_collected = len(records)

            # Paginate to collect more records
            while records_collected < min(total_results, records_per_query):
                start_record = records_collected + 1

                root = search_gallica(cql_query, start_record=start_record, max_records=50)
                _, new_records = parse_sru_response(root)

                if not new_records:
                    break

                all_records.extend(new_records)
                records_collected += len(new_records)

                time.sleep(0.5)

            # Add direct image URLs
            added = 0
            for record in all_records:
                # Create direct high-res image URL
                img_url = ark_to_direct_image_url(record['ark'], page=1)
                if not img_url:
                    continue

                record_url = record['identifier']
                title = record['title']

                con.execute("""
                    INSERT OR IGNORE INTO candidates(
                        source, query, title, page_url, image_url, status
                    )
                    VALUES ('gallica_direct', ?, ?, ?, ?, 'pending')
                """, (f"{search_term} ({doc_type})", title, record_url, img_url))

                if con.total_changes > 0:
                    added += 1

            con.commit()
            total_added += added

            print(f"  Added: {added} direct image URLs\n")

            time.sleep(1.0)  # Be polite

        except Exception as e:
            print(f"  ERROR: {e}\n")
            continue

    con.close()

    print("=" * 60)
    print("Gallica Direct Image Discovery Complete!")
    print(f"Total image URLs added: {total_added:,}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
