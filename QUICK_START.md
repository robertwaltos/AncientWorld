# AncientWorld - Quick Start Guide

## Storage Location (Updated!)
**All data now stored at: `F:\AncientWorld`**
- Database: `F:\AncientWorld\db\assets.sqlite3`
- Images: `F:\AncientWorld\images\`
- Capacity: **1000 GB (1 TB)**

---

## Current Status
- **4,479 image candidates** discovered
- **4,311 images** ready to download
- **2.84 GB** downloaded so far
- **997 GB** remaining capacity

---

## Quick Commands

### Start Downloading Images
```powershell
python tools\download_capped.py
```

### Launch GUI Dashboard
```powershell
streamlit run src\ui\web\dashboard.py
```

### Discover More Images (Enhanced)
```powershell
# Gallica direct images (working - already ran!)
python tools\gallica_direct_images.py

# Enhanced Europeana (3x more queries)
python tools\europeana_discover.py

# Additional museums (require free API keys)
python tools\rijksmuseum_discover.py
python tools\smithsonian_discover.py

# Or run all at once
python tools\run_all_discovery_enhanced.py
```

---

## Getting API Keys (Free!)

### Rijksmuseum
1. Visit: https://data.rijksmuseum.nl/object-metadata/api/
2. Register for free key
3. Set: `$env:RIJKSMUSEUM_API_KEY='your-key'`

### Smithsonian
1. Visit: https://api.si.edu/#signup
2. Register for free key
3. Set: `$env:SMITHSONIAN_API_KEY='your-key'`

---

## What Changed

### Storage Relocated
- Old: `D:\PythonProjects\AncientWorld\data\large`
- New: `F:\AncientWorld`
- Cap: **500 GB → 1000 GB**

### New Discovery Sources
1. **Gallica Direct Images** - Bypasses blocked IIIF (1,699 images added!)
2. **Rijksmuseum** - Dutch architectural collections
3. **Smithsonian** - US architectural surveys
4. **Enhanced Europeana** - 3x more queries, 5x per-query limit

### Scaling Improvements
- Per-query limits increased: 100 → 500+
- Query terms expanded: 3x more searches per source
- Alternative Gallica approach: Direct URLs instead of blocked IIIF manifests

---

## To Reach 1 TB

**Step 1**: Download current 4,311 pending images
```powershell
python tools\download_capped.py
```
Expected: ~200-250 GB

**Step 2**: Run enhanced Europeana for more
```powershell
python tools\europeana_discover.py
```
Expected: +10K-50K images = 500-1000 GB

**Step 3**: Continue downloading until you hit 1 TB cap
```powershell
python tools\download_capped.py
```
Auto-stops at 1 TB!

---

## Documentation
- Full details: `docs/RELOCATION_AND_SCALING_SUMMARY.md`
- Multi-source guide: `docs/MULTI_SOURCE_DISCOVERY.md`

---

## GUI Dashboard Features
- 📊 Real-time statistics
- 🔍 Discovery buttons for all sources  
- ⬇️ Download management
- 🖼️ Image viewer
- 📈 Storage visualization

**Launch**: `streamlit run src\ui\web\dashboard.py`
