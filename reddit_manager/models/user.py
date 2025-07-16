from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """Simple user model with an optional ID, username and API key."""

    id: Optional[int] = None
    username: str = ""
    api_key: str = ""
