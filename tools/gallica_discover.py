"""
Gallica (BnF) Discovery via SRU API

Searches the French National Library's digital collections using the SRU protocol.
Excellent source for Gothic, Romanesque, and architectural drawings.
Returns IIIF manifests for high-resolution images.

API Documentation: https://api.bnf.fr/api-gallica-de-recherche
"""

import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import requests

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.storage_config import DB_PATH, REQUEST_TIMEOUT
from config.search_queries import get_queries_for_source

SRU_URL = "https://gallica.bnf.fr/SRU"
USER_AGENT = "AncientWorld/1.0 (gallica harvester; https://github.com/robertwaltos/AncientWorld)"

# Namespaces for XML parsing
NAMESPACES = {
    'srw': 'http://www.loc.gov/zing/srw/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/'
}

# French architectural queries from centralized config
QUERIES = get_queries_for_source('gallica')


def build_cql_query(search_term, doc_type):
    """Build CQL query for Gallica SRU."""
    return f'(gallica all "{search_term}") and (dc.type all "{doc_type}")'


def ark_to_manifest_url(ark_identifier):
    """Convert ARK identifier to IIIF manifest URL."""
    if not ark_identifier.startswith("ark:/"):
        return None
    return f"https://gallica.bnf.fr/iiif/{ark_identifier}/manifest.json"


def extract_ark_from_identifier(identifier):
    """Extract ARK identifier from dc:identifier field."""
    if "ark:/" in identifier:
        start = identifier.find("ark:/")
        ark = identifier[start:]
        ark = ark.split('.f')[0]
        ark = ark.split('/f')[0]
        return ark
    return None


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
    """Parse SRU XML response and extract records."""
    # Get total number of results
    num_records_elem = root.find('.//srw:numberOfRecords', NAMESPACES)
    total_results = int(num_records_elem.text) if num_records_elem is not None else 0

    # Extract records
    records = []
    for record in root.findall('.//srw:record', NAMESPACES):
        dc_elem = record.find('.//oai_dc:dc', NAMESPACES)
        if dc_elem is None:
            continue

        title_elem = dc_elem.find('dc:title', NAMESPACES)
        title = title_elem.text if title_elem is not None else None

        creator_elem = dc_elem.find('dc:creator', NAMESPACES)
        creator = creator_elem.text if creator_elem is not None else None

        date_elem = dc_elem.find('dc:date', NAMESPACES)
        date = date_elem.text if date_elem is not None else None

        identifier_elem = dc_elem.find('dc:identifier', NAMESPACES)
        identifier = identifier_elem.text if identifier_elem is not None else None

        if identifier:
            ark = extract_ark_from_identifier(identifier)
            if ark:
                records.append({
                    'title': title,
                    'creator': creator,
                    'date': date,
                    'identifier': identifier,
                    'ark': ark
                })

    return total_results, records


def main(records_per_query=200):
    """Discover IIIF manifests from Gallica."""
    print("=" * 60)
    print("Gallica (BnF) Discovery via SRU")
    print("=" * 60)
    print(f"SRU Endpoint: {SRU_URL}")
    print(f"Queries: {len(QUERIES)}\n")

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print("ERROR: Database not found. Run init_database.py first.")
        return 1

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")

    total_manifests = 0

    for search_term, doc_type in QUERIES:
        print(f"[GALLICA] Searching: {search_term} ({doc_type})")

        try:
            cql_query = build_cql_query(search_term, doc_type)

            root = search_gallica(cql_query, start_record=1, max_records=50)
            total_results, records = parse_sru_response(root)

            print(f"  Found: {total_results:,} total results")

            all_records = records
            records_collected = len(records)

            while records_collected < min(total_results, records_per_query):
                start_record = records_collected + 1

                root = search_gallica(cql_query, start_record=start_record, max_records=50)
                _, new_records = parse_sru_response(root)

                if not new_records:
                    break

                all_records.extend(new_records)
                records_collected += len(new_records)

                time.sleep(0.5)

            added = 0
            for record in all_records:
                manifest_url = ark_to_manifest_url(record['ark'])
                if not manifest_url:
                    continue

                record_url = record['identifier']
                title = record['title']

                con.execute("""
                    INSERT OR IGNORE INTO manifests(
                        source, query, record_url, manifest_url, title, status
                    )
                    VALUES ('gallica', ?, ?, ?, ?, 'pending')
                """, (f"{search_term} ({doc_type})", record_url, manifest_url, title))

                if con.total_changes > 0:
                    added += 1

            con.commit()
            total_manifests += added

            print(f"  Added: {added} new manifests\n")

            time.sleep(1.0)

        except Exception as e:
            print(f"  ERROR: {e}\n")
            continue

    con.close()

    print("=" * 60)
    print("Gallica Discovery Complete!")
    print(f"Total IIIF manifests added: {total_manifests:,}")
    print("\nNext step: Run iiif_harvest_manifest.py to extract images")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
