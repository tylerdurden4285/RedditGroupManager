import logging
import os
import sys
from flask import Flask

try:
    # When executed as part of the installed package, the relative import
    # succeeds.  This covers most "normal" application entry points.
    from .. import logging_config  # type: ignore
except ImportError as exc:
    # Fall back to trying an absolute import which will work when the project
    # has been installed in editable mode or the user is executing commands
    # from the repository root.
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    try:
        import logging_config  # type: ignore
    except ImportError as exc2:  # pragma: no cover - defensive
        raise ImportError(
            "Could not import logging_config. Run this command from the "
            "repository root or install the package with 'pip install -e .'"
        ) from exc2

_log_configured = False  

def setup_logging(app: Flask = None, log_filename_prefix: str = "rgm_app"):
    """Configure logging for the application.

    The configuration is performed once per process.  When the ``DEV_LOG``
    environment variable is ``TRUE`` a single ``logs/dev.log`` file is used.
    Otherwise only a stream handler is attached so logs go to stdout/stderr.

    Args:
        app: Optional Flask application instance whose logger level should be
            aligned with the root logger.
        log_filename_prefix: Ignored when ``DEV_LOG`` is ``TRUE`` but kept for
            backward compatibility.
    """
    global _log_configured

    
    if app and app.config.get('LOG_LEVEL'):
        log_level_str = app.config.get('LOG_LEVEL', 'INFO')
    else:
        log_level_str = os.getenv('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    if not _log_configured:
        handlers = [logging.StreamHandler()]
        if logging_config.DEV_LOG:
            log_file_path = logging_config.DEV_LOG_FILE
            logging_config.ensure_log_dir()
            try:
                handlers.insert(0, logging.FileHandler(log_file_path))
            except OSError as exc:
                logging.error(
                    "Failed to open dev log file %s: %s", log_file_path, exc
                )

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers,
        )
        if logging_config.DEV_LOG:
            logging.getLogger().info(
                f"Logging configured. Dev log file: {log_file_path}"
            )
        else:
            logging.getLogger().info("Logging configured. Stream only mode")
        _log_configured = True
    else:
        
        current_root_level = logging.getLogger().getEffectiveLevel()
        if log_level < current_root_level:
            logging.getLogger().setLevel(log_level)
            for handler in logging.getLogger().handlers:
                handler.setLevel(log_level)
        logging.getLogger().info("Logging already configured. Adjusted level if necessary.")

    if app:
        
        
        app.logger.setLevel(log_level)
        
        
        app_specific_logger = logging.getLogger(app.name) 
        app_specific_logger.setLevel(log_level)
        app_specific_logger.info(f"Flask app logger '{app.name}' level set to {log_level_str}")


