# Multi-Source Discovery for AncientWorld

This document explains how to discover images from multiple sources beyond Wikimedia Commons.

## Sources Available

### 1. MediaWiki Sources
- **Wikimedia Commons** - Largest free media repository
- Already implemented in `ancientgeo/spiders/commons_discover.py`

### 2. IIIF Sources (High-Resolution Scans)
- **Gallica (BnF)** - French National Library, Gothic/Romanesque treasures
- **British Library** - Medieval manuscripts, architectural drawings
- **Vatican Library** - Sacred geometry, Renaissance architecture
- **Internet Archive** - Architectural books and plates

### 3. Museum & Institution APIs
- **Met Museum** - Open Access collection, high-quality images
- **Europeana** - Aggregator for 1000s of European institutions
- **Getty Museum** - Architecture and ornament studies
- **Smithsonian** - US collections

## Quick Start

### Option 1: Run All Discovery Sources (Recommended)

```powershell
python tools\run_all_discovery.py
```

This runs all sources in optimal order:
1. Direct image sources (Met, Commons)
2. IIIF manifest discovery (Gallica, Internet Archive)
3. Manifest processing to extract images

### Option 2: Use the GUI Dashboard

```powershell
streamlit run src\ui\web\dashboard.py
```

Navigate to the "Discovery" page and click buttons for each source.

### Option 3: Run Individual Sources

```powershell
# Met Museum (no key required)
python tools\met_discover.py

# Wikimedia Commons
cd ancientgeo
python -m scrapy crawl commons_discover

# Gallica (French National Library)
python tools\gallica_discover.py

# Internet Archive
python tools\archive_org_discover.py

# Process IIIF manifests
python tools\iiif_harvest_manifest.py
```

## Setup Requirements

### Europeana API Key (Optional)

To use Europeana, you need a free API key:

1. Visit: https://pro.europeana.eu/page/get-api
2. Register for free
3. Set environment variable:

```powershell
# PowerShell
$env:EUROPEANA_API_KEY = "your-key-here"

# CMD
set EUROPEANA_API_KEY=your-key-here
```

## How It Works

### Two-Stage Architecture

**Stage 1: Discovery**
- Sources add entries to the `candidates` table (direct images)
- or the `manifests` table (IIIF sources)

**Stage 2: IIIF Processing**
- `iiif_harvest_manifest.py` processes manifests
- Extracts individual image URLs → `candidates` table

**Stage 3: Download**
- `download_capped.py` downloads all pending candidates
- Respects 500GB storage cap
- Includes rate limiting and retry logic

### Database Tables

**candidates** - Individual image URLs ready to download
- source, query, title, image_url, status, etc.

**manifests** - IIIF manifest URLs to be processed
- source, query, manifest_url, status, etc.

## Source Details

### Wikimedia Commons
- **Type**: MediaWiki API
- **Volume**: Millions of images
- **Quality**: Variable (tourist photos + professional)
- **License**: Mostly CC/Public Domain
- **Keywords**: English terms work best

### Met Museum
- **Type**: REST API
- **Volume**: 500K+ open access images
- **Quality**: Extremely high, professional photography
- **License**: CC0 (public domain)
- **No API key required**

### Gallica (BnF)
- **Type**: IIIF + SRU Search
- **Volume**: Millions of digitized items
- **Quality**: Exceptional for Gothic/Romanesque
- **License**: Public domain heavy
- **Keywords**: French terms work better
  - "cathédrale gothique" not "gothic cathedral"
  - "rosace" not "rose window"
  - "remplage" not "tracery"

### Internet Archive
- **Type**: IIIF via identifier
- **Volume**: Massive book/plate collections
- **Quality**: Variable, but includes rare architectural treatises
- **License**: Public domain + varied
- **Strategy**: Focus on architectural books with many plates

### Europeana
- **Type**: REST API (aggregator)
- **Volume**: 50M+ items across Europe
- **Quality**: Variable
- **License**: Filter by "open" reusability
- **Key required**: Free registration

## Discovery Strategy

### Recommended Order for 500GB Goal

1. **Run Commons** (breadth) → ~100K candidates
2. **Run Met** (quality) → +10-20K
3. **Run Gallica** (geometry/construction) → +50K manifests
4. **Process IIIF** → +500K high-res images
5. **Download with cap** → 500GB limit enforced

### Keywords That Work Well

**Gothic/Medieval:**
- cathedral architecture, gothic tracery, rose window
- medieval architecture, church facade
- romanesque architecture, vault construction

**Geometric Construction:**
- geometric ornament, architectural drawing
- architectural elevation, stereotomy
- sacred geometry, architectural plates

**Islamic:**
- islamic geometric pattern, muqarnas, zellige
- girih, arabesques architecture

**French (for Gallica):**
- cathédrale gothique, rosace, remplage
- stéréotomie, élévation cathédrale
- architecture romane, ornement géométrique

## Troubleshooting

### "Database not found"
```powershell
python tools\init_database.py
python tools\migrate_add_manifests.py
```

### "EUROPEANA_API_KEY not set"
Either:
- Set the environment variable (see above)
- Skip Europeana for now

### Rate Limiting Errors (429)
- Wait 60 seconds
- The downloader now handles this automatically
- config/storage_config.py has SLEEP_BETWEEN_DOWNLOADS = 1.0

### No Images from Source
- Check your internet connection
- Some sources may return empty results for certain queries
- Try different keywords or languages (French for Gallica)

## Next Steps

After discovery:

1. **Check stats:**
```powershell
python -c "import sqlite3; con = sqlite3.connect('D:/PythonProjects/AncientWorld/data/large/db/assets.sqlite3'); print('Candidates:', con.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]); print('Manifests:', con.execute('SELECT COUNT(*) FROM manifests').fetchone()[0])"
```

2. **Start downloading:**
```powershell
python tools\download_capped.py
```

3. **Monitor via GUI:**
```powershell
streamlit run src\ui\web\dashboard.py
```

4. **Deduplicate after downloading:**
```powershell
python tools\dedupe_exact.py
python tools\dedupe_perceptual.py
```

## Adding More Sources

To add a new source:

1. Create `tools/new_source_discover.py`
2. Insert into either:
   - `candidates` table (direct images)
   - `manifests` table (IIIF)
3. Add button to dashboard's discovery_page()
4. Test and verify
