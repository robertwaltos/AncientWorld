# Large Dataset Storage Configuration

import importlib
import sys
from pathlib import Path

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
PERCEPTUAL_HASH_THRESHOLD = 5  # Hamming distance for near-duplicates


def get_config():
    """Get current configuration as dictionary."""
    return {
        'LARGE_STORAGE_ROOT': LARGE_STORAGE_ROOT,
        'MAX_STORAGE_GB': MAX_STORAGE_GB,
        'BATCH_SIZE': BATCH_SIZE,
        'SLEEP_BETWEEN_DOWNLOADS': SLEEP_BETWEEN_DOWNLOADS,
        'REQUEST_TIMEOUT': REQUEST_TIMEOUT,
        'MAX_RETRIES': MAX_RETRIES,
        'MIN_IMAGE_WIDTH': MIN_IMAGE_WIDTH,
        'MIN_IMAGE_HEIGHT': MIN_IMAGE_HEIGHT,
        'PERCEPTUAL_HASH_THRESHOLD': PERCEPTUAL_HASH_THRESHOLD,
    }


def update_config(**kwargs):
    """Update configuration file with new values."""
    config_path = Path(__file__)
    content = config_path.read_text()

    # Update each provided value
    for key, value in kwargs.items():
        if key == 'LARGE_STORAGE_ROOT':
            # Update storage root
            old_line = f'LARGE_STORAGE_ROOT = r"{LARGE_STORAGE_ROOT}"'
            new_line = f'LARGE_STORAGE_ROOT = r"{value}"'
            content = content.replace(old_line, new_line)
        elif isinstance(value, str):
            old_line = f'{key} = "{globals()[key]}"'
            new_line = f'{key} = "{value}"'
            content = content.replace(old_line, new_line)
        else:
            old_line = f'{key} = {globals()[key]}'
            new_line = f'{key} = {value}'
            content = content.replace(old_line, new_line)

    # Write back
    config_path.write_text(content)

    # Reload module to update globals
    reload_config()


def reload_config():
    """Reload configuration module to pick up changes."""
    import config.storage_config as cfg
    importlib.reload(cfg)

    # Update globals in this module
    for key in dir(cfg):
        if key.isupper():
            globals()[key] = getattr(cfg, key)

