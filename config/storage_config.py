# Large Dataset Storage Configuration

# By default, use project data directory
# For 500GB corpus, point to a dedicated drive with space
LARGE_STORAGE_ROOT = r"D:\PythonProjects\AncientWorld\data\large"

# Or use a dedicated drive (uncomment and adjust):
# LARGE_STORAGE_ROOT = r"E:\ancientgeo"
# LARGE_STORAGE_ROOT = r"F:\ancient_buildings_corpus"

# Database location
DB_PATH = f"{LARGE_STORAGE_ROOT}\\db\\assets.sqlite3"

# Images storage (will use prefix-based subdirectories)
IMAGES_ROOT = f"{LARGE_STORAGE_ROOT}\\images"

# Logs
LOGS_ROOT = f"{LARGE_STORAGE_ROOT}\\logs"

# Cache
CACHE_ROOT = f"{LARGE_STORAGE_ROOT}\\cache"

#Download caps
MAX_STORAGE_GB = 500
MAX_STORAGE_BYTES = MAX_STORAGE_GB * 1024 ** 3

# Download settings
BATCH_SIZE = 200
SLEEP_BETWEEN_DOWNLOADS = 0.1
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3

# Quality gates
MIN_IMAGE_WIDTH = 900
MIN_IMAGE_HEIGHT = 900

# Deduplication settings
ENABLE_PERCEPTUAL_HASH = True
PERCEPTUAL_HASH_THRESHOLD = 5  # Ham ming distance for near-duplicates
