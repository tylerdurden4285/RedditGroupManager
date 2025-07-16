import os
import logging
import requests

logger = logging.getLogger(__name__)

def check_connections(app):
    """Check all required connections and log results.
    Called during application startup to provide early feedback.
    Returns True if all checks pass.
    """
    logger.debug("==== Connection Status Check ====\n")

    db_status = False
    try:
        app.group_manager.list_groups()
        db_status = True
        logger.debug("Database: Connected successfully")
    except Exception as e:
        logger.debug("Database: Could not connect - %s", str(e))
        logger.error(f"Database connection failed during startup: {str(e)}")

    reddit_status = False
    try:
        if app.reddit:
            reddit_status = app.reddit.is_connected()
            if reddit_status:
                username = app.reddit.get_reddit_username()
                logger.debug("Reddit API: Connected as %s", username or "unknown")
            else:
                logger.error("Reddit API authentication failed - Not connected")
        else:
            logger.error("Reddit client not initialized - Check .env file for missing credentials")
    except Exception as e:
        logger.debug("Reddit API: Connection failed - %s", str(e))
        logger.error(f"Reddit API connection failed during startup: {str(e)}")

    port = os.getenv('FRONTEND_PORT', '5015')
    if not db_status or not reddit_status:
        logger.debug("Issues detected with one or more connections - see http://localhost:%s/status", port)
    else:
        logger.debug("All systems operational! Status page at http://localhost:%s/status", port)

    app.config['CONNECTION_STATUS'] = {
        'database': db_status,
        'reddit': reddit_status,
    }

    logger.debug("==================================")

    return db_status and reddit_status
