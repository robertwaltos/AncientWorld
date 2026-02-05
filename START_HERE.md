# 🚀 AncientWorld - Getting Started

## ✅ System Status

Your AncientWorld platform is **ready to use**!

- ✅ Database initialized
- ✅ All tables created  
- ✅ Ready for discovery phase

---

## 🎯 Quick Start (Choose One)

### Option 1: GUI Dashboard (Recommended)

```powershell
streamlit run src\ui\web\dashboard.py
```

This will open **http://localhost:8501** in your browser with:
- Real-time monitoring dashboard
- Start/stop discovery and downloads
- Browse images
- Run analysis
- Database browser

---

### Option 2: Command Line Workflow

#### Step 1: Discovery (Build candidate pool)

```powershell
cd ancientgeo
scrapy crawl commons_discover
```

**What this does:**
- Searches Wikimedia Commons for architectural images
- Catalogs URLs and metadata (NO downloads yet)
- Runs for 2-24 hours
- Finds 10k-100k+ candidates

**Seeds included:**
- Rose windows, Gothic tracery, cathedral facades
- Islamic geometric patterns, muqarnas, girih
- Greek/Roman temples
- Architectural drawings

Let it run in the background!

---

#### Step 2: Download (Fill 500GB)

```powershell
python tools\download_capped.py
```

**What this does:**
- Downloads images from discovered candidates
- **Stops automatically at 500GB**
- Resume-able if interrupted
- Prioritizes high-resolution images
- Computes SHA256 hashes
- Full metadata preservation

**Progress monitoring:**
- Watch console output
- Or check GUI dashboard in parallel

---

#### Step 3: Deduplicate (Free space)

```powershell
# Remove exact duplicates (SHA256)
python tools\dedupe_exact.py

# Remove near-duplicates (perceptual hash)
python tools\dedupe_perceptual.py
```

**Results:**
- Typically frees 10-30% of storage
- Can download more after deduplication

---

#### Step 4: Analyze Images

```powershell
# Single image geometry analysis
python -m src.analysis.geometry_detector image.jpg --output analyzed.jpg

# Batch analysis via GUI
streamlit run src\ui\web\dashboard.py
```

---

## 📊 Monitor Progress

### Check Database Status

```powershell
python -c "import sqlite3; con = sqlite3.connect('D:/PythonProjects/AncientWorld/data/large/db/assets.sqlite3'); print(dict(con.execute('SELECT k, v FROM stats').fetchall())); con.close()"
```

### View Candidates Count

```powershell
python -c "import sqlite3; con = sqlite3.connect('D:/PythonProjects/AncientWorld/data/large/db/assets.sqlite3'); print(con.execute('SELECT status, COUNT(*) FROM candidates GROUP BY status').fetchall()); con.close()"
```

---

## ⚙️ Configuration

Edit `config/storage_config.py` to change:

```python
# Storage location (change if needed)
LARGE_STORAGE_ROOT = r"D:\PythonProjects\AncientWorld\data\large"

# Storage cap (default 500GB)
MAX_STORAGE_GB = 500

# Image quality thresholds
MIN_IMAGE_WIDTH = 900
MIN_IMAGE_HEIGHT = 900

# Download settings
BATCH_SIZE = 200
SLEEP_BETWEEN_DOWNLOADS = 0.1
```

---

## 🎯 Recommended First Run

1. **Launch GUI** (in one terminal):
   ```
   streamlit run src\ui\web\dashboard.py
   ```

2. **Start discovery** (in another terminal):
   ```
   cd ancientgeo
   scrapy crawl commons_discover
   ```

3. **Watch progress** in GUI dashboard

4. **Once you have 1000+ candidates**, start download:
   ```
   python tools\download_capped.py
   ```

---

## 📚 Documentation

- **Full README**: `README.md`
- **Quick Start**: `QUICKSTART.md`
- **Agent Docs**: `docs/AGENT_HANDOFF.md`
- **Architecture**: `docs/TWO_STAGE_ARCHITECTURE.md`

---

## 🆘 Troubleshooting

### "ModuleNotFoundError"
```powershell
pip install -r requirements.txt
```

### "Database not found"
```powershell
python tools\init_database.py
```

### "Permission denied" on storage
Change `LARGE_STORAGE_ROOT` in `config/storage_config.py`

### GUI won't start
```powershell
pip install streamlit plotly
```

---

## 🎉 You're Ready!

Your AncientWorld platform is fully operational. Start with the GUI dashboard:

```powershell
streamlit run src\ui\web\dashboard.py
```

Then navigate to **http://localhost:8501** and explore! 🏛️

