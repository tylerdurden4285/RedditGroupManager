import os
import logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEV_LOG = os.getenv("DEV_LOG", "FALSE").upper() == "TRUE"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
logger = logging.getLogger(__name__)
def ensure_log_dir():
    """Create the log directory if it does not already exist."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except OSError as exc:
        logger.error("Failed to create log directory %s: %s", LOG_DIR, exc)
if DEV_LOG:
    ensure_log_dir()
DEV_LOG_FILE = os.path.join(LOG_DIR, "dev.log")
