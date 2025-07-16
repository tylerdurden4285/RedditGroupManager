from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Subreddit:
    """
    A subreddit represents a Reddit community with optional flair information.
    """
    id: Optional[int] = None
    group_id: Optional[int] = None
    subreddit: str = ""
    flair_id: Optional[str] = None
    flair_text: Optional[str] = None
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Subreddit':
        """Create a Subreddit instance from a dictionary."""
        return cls(
            id=data.get('id'),
            group_id=data.get('group_id'),
            subreddit=data.get('subreddit', ''),
            flair_id=data.get('flair_id'),
            flair_text=data.get('flair_text'),
            description=data.get('description')
        )
    
    def to_dict(self) -> Dict:
        """Convert the Subreddit instance to a dictionary."""
        return {
            'id': self.id,
            'group_id': self.group_id,
            'subreddit': self.subreddit,
            'flair_id': self.flair_id,
            'flair_text': self.flair_text,
            'description': self.description
        }
