# AncientWorld Quick Start Guide

## 🚀 Setup (5 minutes)

### 1. Install Dependencies

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install all dependencies
pip install -r requirements.txt
```

### 2. Configure Storage

Edit `config/storage_config.py`:

```python
# For 500GB corpus, use a dedicated drive:
LARGE_STORAGE_ROOT = r"D:\PythonProjects\AncientWorld\data\large"

# Or use external drive:
# LARGE_STORAGE_ROOT = r"E:\ancientgeo"
```

### 3. Initialize Database

```powershell
python tools\init_database.py
```

---

## 📊 Launch the GUI

```powershell
streamlit run src\ui\web\dashboard.py
```

The dashboard will open in your browser at http://localhost:8501

---

## 🔍 Two-Stage Workflow

### Stage 1: Discovery (Catalog URLs)

From the GUI Dashboard → Discovery → Start Discovery

Or from command line:

```powershell
cd ancientgeo
scrapy crawl commons_discover
```

This will:
- Search Wikimedia Commons for architectural images
- Store metadata in database
- NO downloads yet (just catalog URLs)

**Let it run for a while to build a large candidate pool!**

### Stage 2: Download (With 500GB Cap)

From GUI Dashboard → Download → Start Download

Or from command line:

```powershell
python tools\download_capped.py
```

This will:
- Download from pending candidates
- Stop automatically at 500GB cap
- Track progress in database
- Resume where it left off if interrupted

### Stage 3: Deduplication

From GUI Dashboard → Download → Remove Exact Duplicates / Remove Near-Duplicates

Or from command line:

```powershell
# Remove exact duplicates (SHA256)
python tools\dedupe_exact.py

# Remove near-duplicates (perceptual hash)
python tools\dedupe_perceptual.py
```

---

## 🖼️ Browse Your Collection

From GUI Dashboard → Image Viewer

See random samples of downloaded images with metadata.

---

## 🔬 Run Analysis

### Geometry Detection (Single Image)

```powershell
python -m src.analysis.geometry_detector path\to\image.jpg --output analyzed.jpg
```

### Batch Analysis (Coming Soon)

Integration with GUI for batch processing.

---

## 📈 Monitor Progress

### GUI Dashboard
Real-time stats:
- Storage used / remaining
- Files downloaded
- Pending candidates
- Failed downloads

### Database Browser
Search and filter collected images by:
- Source
- Status
- Title/description

---

## 🎯 Recommended Workflow

1. **Day 1**: Run discovery spider overnight
   - `cd ancientgeo && scrapy crawl commons_discover`
   - Let it catalog 10k-100k candidates

2. **Day 2-7**: Download with cap
   - `python tools\download_capped.py`
   - Fills up to 500GB
  - Resume-able if interrupted

3. **Day 8**: Deduplicate
   - `python tools\dedupe_exact.py`
   - `python tools\dedupe_perceptual.py`
   - Might free 10-30% of space

4. **Day 9**: Download more to fill freed space
   - Run downloader again

5. **Day 10+**: Analysis
   - Run geometry detection
   - Run symmetry analysis
   - Pattern recognition

---

## ⚙️ Configuration

### Change Storage Cap

Edit `config/storage_config.py`:

```python
MAX_STORAGE_GB = 500  # Change to your desired cap
```

### Change Image Quality Thresholds

```python
MIN_IMAGE_WIDTH = 900  # Minimum width in pixels
MIN_IMAGE_HEIGHT = 900  # Minimum height in pixels
```

### Add More Discovery Queries

Edit `ancientgeo/ancientgeo/spiders/commons_discover.py`:

```python
SEED_QUERIES = [
    "rose window",
    "gothic tracery",
    # Add your own:
    "romanesque capitals",
    "byzantine mosaics",
]
```

---

## 🐛 Troubleshooting

### "Database not found"
Run: `python tools\init_database.py`

### "Permission denied" on E:/
Change `LARGE_STORAGE_ROOT` in `config/storage_config.py` to use D:/ drive

### Out of memory during download
Reduce `BATCH_SIZE` in `config/storage_config.py`

### GUI won't start
Make sure Streamlit is installed: `pip install streamlit`

---

## 📚 Next Steps

- [ ] Read full docs: `docs/AGENT_HANDOFF.md`
- [ ] Add more sources: Europeana, IIIF
- [ ] Implement advanced analysis
- [ ] Export datasets for ML training

---

## 🆘 Need Help?

- Check the full README: `README.md`
- Review agent documentation: `docs/AGENT_HANDOFF.md`
- Open an issue: https://github.com/robertwaltos/AncientWorld/issues

