from importlib.metadata import version as pkg_version
from pathlib import Path


def get_app_version() -> str:
    """Return the application version."""
    try:
        return pkg_version("reddit-manager")
    except Exception:
        return Path("app-version").read_text().strip()

