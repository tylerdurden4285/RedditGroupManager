from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from .subreddit import Subreddit


@dataclass
class Group:
    """
    A group represents a collection of subreddits that can be managed together.
    """
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: datetime = None
    subreddits: List[Subreddit] = None
    
    def __post_init__(self):
        if self.subreddits is None:
            self.subreddits = []
        
        if isinstance(self.created_at, str):
            
            try:
                self.created_at = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
            except ValueError:
                self.created_at = datetime.now()
        elif self.created_at is None:
            self.created_at = datetime.now()
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Group':
        """Create a Group instance from a dictionary."""
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            created_at=data.get('created_at'),
            subreddits=[Subreddit.from_dict(s) for s in data.get('subreddits', [])] if 'subreddits' in data else []
        )
    
    def to_dict(self) -> Dict:
        """Convert the Group instance to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'subreddits': [s.to_dict() for s in self.subreddits] if self.subreddits else []
        }
