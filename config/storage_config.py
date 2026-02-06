# Large Dataset Storage Configuration

# Storage location for 1TB corpus
LARGE_STORAGE_ROOT = r"F:\AncientWorld"

# Or use project directory (uncomment if needed):
# LARGE_STORAGE_ROOT = r"D:\PythonProjects\AncientWorld\data\large"

# Database location
DB_PATH = f"{LARGE_STORAGE_ROOT}\\db\\assets.sqlite3"

# Images storage (will use prefix-based subdirectories)
IMAGES_ROOT = f"{LARGE_STORAGE_ROOT}\\images"

# Logs
LOGS_ROOT = f"{LARGE_STORAGE_ROOT}\\logs"

# Cache
CACHE_ROOT = f"{LARGE_STORAGE_ROOT}\\cache"

#Download caps
MAX_STORAGE_GB = 2000
MAX_STORAGE_BYTES = MAX_STORAGE_GB * 1024 ** 3

# Download settings
BATCH_SIZE = 200
SLEEP_BETWEEN_DOWNLOADS = 1.0  # Increased from 0.1 to 1.0 second to respect rate limits
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3

# Quality gates
MIN_IMAGE_WIDTH = 600
MIN_IMAGE_HEIGHT = 600

# Deduplication settings
ENABLE_PERCEPTUAL_HASH = True
PERCEPTUAL_HASH_THRESHOLD = 5  # Ham ming distance for near-duplicates
