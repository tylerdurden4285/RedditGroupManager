import logging
from typing import List, Dict, Optional, Tuple

import praw
import prawcore
from flask import current_app

from ..config.settings import Settings


class RedditService:
    """Service for interacting with the Reddit API through PRAW."""

    REQUIRED_ENV_VARS = [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
    ]

    def __init__(self, settings: Settings):
        """Initialize the Reddit client using the provided settings."""

        self.logger = logging.getLogger(__name__)
        self.settings = settings
        self._ensure_env_vars()
        self.reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
            username=settings.reddit_username,
            password=settings.reddit_password,
        )
        
        
        self._cached_username = settings.reddit_username or ""
        
        self._connected = bool(self._cached_username)

    def _ensure_env_vars(self) -> None:
        """Verify required Reddit settings are provided."""

        missing = [
            var
            for var in self.REQUIRED_ENV_VARS
            if getattr(self.settings, var.lower(), None) in (None, "")
        ]
        if missing:
            msg = ", ".join(missing)
            self.logger.error("Missing required Reddit settings: %s", msg)
            raise ValueError(f"Missing required Reddit settings: {msg}")

    def reload_from_env(self) -> None:
        """Reload credentials from environment variables into :class:`Settings`."""

        self.logger.info("Reloading Reddit credentials from environment")
        new_settings = Settings()  
        self.settings = new_settings
        self._ensure_env_vars()
        self.reddit = praw.Reddit(
            client_id=new_settings.reddit_client_id,
            client_secret=new_settings.reddit_client_secret,
            user_agent=new_settings.reddit_user_agent,
            username=new_settings.reddit_username,
            password=new_settings.reddit_password,
        )
        self._cached_username = new_settings.reddit_username or ""
        self._connected = bool(self._cached_username)
    
    def get_reddit_username(self) -> str:
        """Return the cached Reddit username."""
        return self._cached_username

    def is_connected(self) -> bool:
        """Return ``True`` if Reddit credentials appear configured."""
        return self._connected
    def get_flairs(self, subreddit_name: str) -> List[Dict]:
        """Fetch flairs for a given subreddit."""
        return self.get_subreddit_flairs(subreddit_name)

    def get_subreddit_flairs(self, subreddit_name: str) -> List[Dict]:
        """Fetch flairs for a given subreddit."""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            flairs = []

            
            
            _ = subreddit.display_name

            
            
            try:
                
                templates = list(subreddit.flair.link_templates)
                if not templates:
                    
                    templates = list(subreddit.flair.link_templates.user_selectable())

                
                for flair in templates:
                    
                    if "id" in flair and isinstance(flair["id"], str):
                        
                        text = (
                            flair.get("text", "")
                            or flair.get("text_editable", "")
                            or flair.get("name", "")
                        )
                        
                        if text and not text.lower() in ["edit", "discussion", "post", "moderate"]:
                            flairs.append({"id": flair["id"], "text": text})

                self.logger.info(
                    f"Retrieved {len(flairs)} validated flairs from r/{subreddit_name}"
                )

            except (AttributeError, TypeError) as e:
                self.logger.warning(
                    f"Error accessing flair templates with standard method: {str(e)}"
                )

                
                try:
                    for template in subreddit.flair.templates:
                        
                        if "id" in template and isinstance(template["id"], str):
                            text = (
                                template.get("text", "")
                                or template.get("text_editable", "")
                                or template.get("name", "")
                            )
                            if text and not text.lower() in [
                                "edit",
                                "discussion",
                                "post",
                                "moderate",
                            ]:
                                flairs.append({"id": template["id"], "text": text})
                    self.logger.info(
                        f"Retrieved {len(flairs)} validated flairs from r/{subreddit_name} using alternative method"
                    )
                except Exception as inner_e:
                    self.logger.error(
                        f"Failed to get flairs using alternative method: {str(inner_e)}"
                    )

            return flairs

        except Exception as e:
            self.logger.error(f"Error in get_subreddit_flairs for r/{subreddit_name}: {str(e)}")
            raise e

    def get_subreddit_info(self, subreddit_name: str) -> Dict:
        """Fetch rules and description for a given subreddit."""
        subreddit = self.reddit.subreddit(subreddit_name)
        rules = [rule.short_name for rule in subreddit.rules]
        description = subreddit.description
        return {"rules": rules, "description": description}

    class SubredditNotFoundError(Exception):
        """Exception raised when a subreddit no longer exists."""

        pass

    def post_to_subreddit(
        self, subreddit_name: str, title: str, body: str, flair_id: Optional[str] = None
    ) -> str:
        """Post a text submission to a subreddit."""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            
            
            _ = subreddit.display_name

            submission = subreddit.submit(title, selftext=body, flair_id=flair_id)
            return submission.id

        except (prawcore.exceptions.NotFound, prawcore.exceptions.Redirect):
            self.logger.error(
                "Subreddit r/%s does not exist or has been redirected", subreddit_name
            )
            raise self.SubredditNotFoundError(f"Subreddit r/{subreddit_name} not found")

        except praw.exceptions.PRAWException as e:
            error_str = str(e).lower()

            
            if any(
                pattern in error_str
                for pattern in ["404", "not found", "doesn't exist", "does not exist", "banned"]
            ):
                self.logger.error(
                    f"Subreddit r/{subreddit_name} no longer exists or is banned: {error_str}"
                )
                raise self.SubredditNotFoundError(
                    f"Subreddit r/{subreddit_name} no longer exists or is banned"
                )
            else:
                
                self.logger.error(f"PRAW error posting to r/{subreddit_name}: {error_str}")
                raise

    def post_link_to_subreddit(
        self, subreddit_name: str, title: str, link_url: str, flair_id: Optional[str] = None
    ) -> str:
        """Post a link submission to a subreddit."""
        subreddit = self.reddit.subreddit(subreddit_name)
        submission = subreddit.submit(title, url=link_url, flair_id=flair_id)
        return submission.id

    def comment_on_post(self, post_id: str, comment_text: str) -> Tuple[str, str]:
        """Comment on a Reddit post."""
        submission = self.reddit.submission(id=post_id)
        comment = submission.reply(comment_text)
        return comment.id, comment.permalink

    def reply_to_comment(self, comment_id: str, reply_text: str) -> str:
        """Reply to a Reddit comment."""
        try:
            comment = self.reddit.comment(id=comment_id)
            reply = comment.reply(reply_text)
            return reply.id
        except praw.exceptions.PRAWException as e:
            self.logger.error(f"PRAW error replying to comment {comment_id}: {e}")
            raise ValueError(f"PRAW error: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error replying to comment {comment_id}: {e}")
            raise ValueError(f"Unexpected error: {str(e)}")

    def delete_post(self, submission_id: str) -> None:
        """Delete a Reddit submission by ID."""
        try:
            submission = self.reddit.submission(id=submission_id)
            submission.delete()
        except Exception as e:  
            self.logger.error(f"Error deleting Reddit post {submission_id}: {e}")
            raise

    def delete_comment(self, comment_id: str) -> None:
        """Delete a Reddit comment by ID."""
        try:
            comment = self.reddit.comment(id=comment_id)
            comment.delete()
        except Exception as e:  
            self.logger.error(f"Error deleting Reddit comment {comment_id}: {e}")
            raise

    def purge_user_history(self) -> None:
        """Delete all submissions and comments for the authenticated user."""
        try:
            user = self.reddit.user.me()
            self.logger.info("Purging history for %s", getattr(user, "name", "user"))
            # Delete comments first so that any replies on submissions are
            # removed before the submissions themselves are deleted.
            for comment in user.comments.new(limit=None):
                try:
                    comment.delete()
                    self.logger.debug("Deleted comment %s", comment.id)
                except Exception as exc:
                    self.logger.error(
                        "Failed deleting comment %s: %s", comment.id, exc
                    )
            for submission in user.submissions.new(limit=None):
                try:
                    submission.delete()
                    self.logger.debug("Deleted submission %s", submission.id)
                except Exception as exc:
                    self.logger.error(
                        "Failed deleting submission %s: %s", submission.id, exc
                    )
            self.logger.info("User history purge completed")
        except Exception as e:  
            self.logger.error("Error purging user history: %s", e)
            raise
