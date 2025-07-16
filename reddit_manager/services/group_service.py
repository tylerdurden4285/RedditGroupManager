import logging
import datetime
from zoneinfo import ZoneInfo
import sqlite3
import os
from typing import List, Dict, Optional, Any
import redis
from rq_scheduler import Scheduler
from ..models.group import Group
from ..models.subreddit import Subreddit
from ..utils.db import (
    get_connection,
    migrate_group_subreddit_name_column,
    ensure_flair_text_column,
    ensure_error_message_column,
)
from ..config.settings import Settings


class GroupServiceError(Exception):
    """Raised when a database operation in :class:`GroupService` fails."""

    pass


class GroupService:
    """Service for managing Reddit subreddit groups."""

    def __init__(self, settings: Settings, timezone: Optional[ZoneInfo] = None):
        """Initialize the group service.

        Args:
            settings: Loaded :class:`Settings` instance.
            timezone: Optional timezone to use for timestamps. If not provided,
                :attr:`Settings.tz` is consulted and falls back to ``UTC`` when
                invalid or missing.
        """

        self.logger = logging.getLogger(__name__)
        self.settings = settings

        if timezone is None:
            tz_name = settings.tz or "UTC"
            try:
                timezone = ZoneInfo(tz_name)
            except Exception:
                self.logger.warning(f"Invalid timezone {tz_name}, falling back to UTC")
                timezone = ZoneInfo("UTC")

        self.timezone = timezone

        from ..utils.db import ensure_posts_table
        ensure_posts_table()

    def reload_from_env(self) -> None:
        """Reload configuration such as the database path from environment."""

        from flask import current_app

        new_settings = Settings()

        if new_settings.database_path:
            current_app.config["DATABASE_PATH"] = new_settings.database_path

        if new_settings.tz:
            try:
                self.timezone = ZoneInfo(new_settings.tz)
            except Exception:
                self.logger.warning(
                    f"Invalid timezone {new_settings.tz}, keeping previous value"
                )

        self.settings = new_settings

        from ..utils.db import init_db

        init_db(current_app)

    def _run_migrations(self):
        """Run Alembic migrations to update the database schema."""
        self.logger.info("Running database migrations via Alembic...")
        try:
            from alembic.config import Config
            from alembic import command
            from flask import current_app, has_app_context

            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))

            if has_app_context():
                db_path = current_app.config.get("DATABASE_PATH")
            else:
                db_path = os.getenv(
                    "DATABASE_PATH",
                    os.path.join(base_dir, "instance", "app.db"),
                )

            alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
            command.upgrade(alembic_cfg, "head")
            self._update_post_status_values()
            migrate_group_subreddit_name_column()
            ensure_flair_text_column()
            from ..utils.db import ensure_posts_table
            ensure_posts_table()
            ensure_error_message_column()
            self.logger.info("Database migrations completed successfully")
        except Exception as e:
            self.logger.error(f"Error during database migrations: {str(e)}")
            raise GroupServiceError("Database migration failed") from e

    def _update_post_status_values(self):
        """Update existing post records using the old default status."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"
                )
                if not cursor.fetchone():
                    return
                cursor.execute("PRAGMA table_info(posts)")
                columns = [row[1] for row in cursor.fetchall()]
                if "reddit_url" in columns:
                    cursor.execute(
                        "UPDATE posts SET status = 'waiting' WHERE status = 'posted'"
                        " AND (reddit_url IS NULL OR reddit_url = '')"
                    )
                else:
                    cursor.execute(
                        "UPDATE posts SET status = 'waiting' WHERE status = 'posted'"
                    )
        except sqlite3.Error as e:
            self.logger.error(f"SQLite error updating post statuses: {str(e)}")
            raise

    def list_groups(self) -> List[Group]:
        """List all groups with their subreddits."""
        self.logger.info("Listing all groups")

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM groups ORDER BY name")
                groups = [dict(row) for row in cursor.fetchall()]

                for group in groups:
                    try:
                        cursor.execute(
                            """
                            SELECT id, group_id, subreddit, flair_id, flair_text
                            FROM group_subreddits
                            WHERE group_id = ?
                            """,
                            (group["id"],),
                        )

                        subreddits_data = [dict(row) for row in cursor.fetchall()]

                        group["subreddits"] = subreddits_data

                        self.logger.info(
                            f"Loaded {len(subreddits_data)} subreddits for group {group['id']}"
                        )

                    except sqlite3.Error as subreddit_error:
                        self.logger.warning(
                            f"Error loading subreddits for group {group['id']}: {str(subreddit_error)}"
                        )
                        group["subreddits"] = []

                self.logger.info(f"Found {len(groups)} groups")
                return [Group.from_dict(group) for group in groups]
        except sqlite3.Error as e:
            self.logger.error(f"Error listing groups: {str(e)}")
            raise GroupServiceError("Failed to list groups") from e

    def get_group(self, group_id: int) -> Optional[Group]:
        """Get a group by ID with its subreddits."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
                group_data = cursor.fetchone()

                if not group_data:
                    return None

                group = dict(group_data)

                cursor.execute(
                    "SELECT * FROM group_subreddits WHERE group_id = ?", (group_id,)
                )
                group["subreddits"] = [dict(row) for row in cursor.fetchall()]

                return Group.from_dict(group)
        except sqlite3.Error as e:
            self.logger.error(f"Error getting group {group_id}: {str(e)}")
            raise GroupServiceError(f"Failed to get group {group_id}") from e

    def create_group(
        self, name: str, description: str = "", subreddits: List[Dict] = None
    ) -> Optional[int]:
        """Create a new group.

        ``subreddits`` must contain at least one item or a ``ValueError`` is raised.
        """
        self.logger.info(f"Creating group: {name}")

        if not subreddits:
            self.logger.warning("Attempted to create a group with no subreddits")
            raise ValueError("At least one subreddit is required to create a group")

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO groups (name, description) VALUES (?, ?)",
                    (name, description),
                )
                group_id = cursor.lastrowid

                if subreddits:
                    for subreddit in subreddits:

                        self._add_subreddit_to_group(
                            conn,
                            group_id,
                            subreddit["subreddit"],
                            subreddit.get("flair_id"),
                            subreddit.get("flair_text"),
                        )

                self.logger.info(f"Group created with ID: {group_id}")
                return group_id
        except sqlite3.IntegrityError as e:
            self.logger.warning(f"Group name '{name}' already exists: {str(e)}")
            raise GroupServiceError("Group name already exists") from e
        except sqlite3.Error as e:
            self.logger.error(f"Error creating group: {str(e)}")
            raise GroupServiceError("Failed to create group") from e

    def update_group(
        self,
        group_id: int,
        name: str,
        description: str = "",
        subreddits: List[Dict] = None,
    ) -> bool:
        """Update an existing group with optional subreddits.

        If ``subreddits`` is provided it must contain at least one item. A
        ``ValueError`` is raised otherwise.
        """
        if subreddits is not None and len(subreddits) == 0:
            self.logger.warning("Attempted to update a group with no subreddits")
            raise ValueError("At least one subreddit is required to update a group")

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE groups SET name = ?, description = ? WHERE id = ?",
                    (name, description, group_id),
                )

                if subreddits is not None:

                    cursor.execute(
                        "DELETE FROM group_subreddits WHERE group_id = ?", (group_id,)
                    )

                    for subreddit in subreddits:
                        self._add_subreddit_to_group(
                            conn,
                            group_id,
                            subreddit["subreddit"],
                            subreddit.get("flair_id"),
                            subreddit.get("flair_text"),
                        )

                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error updating group {group_id}: {str(e)}")
            raise GroupServiceError(f"Failed to update group {group_id}") from e

    def delete_group(self, group_id: int) -> bool:
        """Delete a group and its subreddits."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting group {group_id}: {str(e)}")
            raise GroupServiceError(f"Failed to delete group {group_id}") from e

    def get_group_subreddits(self, group_id: int) -> List[Subreddit]:
        """Get all subreddits for a group."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM group_subreddits WHERE group_id = ?", (group_id,)
                )
                subreddits = [dict(row) for row in cursor.fetchall()]
                return [Subreddit.from_dict(subreddit) for subreddit in subreddits]
        except sqlite3.Error as e:
            self.logger.error(
                f"Error getting subreddits for group {group_id}: {str(e)}"
            )
            raise GroupServiceError(
                f"Failed to get subreddits for group {group_id}"
            ) from e

    def add_subreddit_to_group(
        self,
        group_id: int,
        subreddit: str,
        flair_id: Optional[str] = None,
        flair_text: Optional[str] = None,
    ) -> Optional[int]:
        """Add a subreddit to a group."""
        try:
            with get_connection() as conn:
                return self._add_subreddit_to_group(
                    conn, group_id, subreddit, flair_id, flair_text
                )
        except sqlite3.Error as e:
            self.logger.error(
                f"Error adding subreddit {subreddit} to group {group_id}: {str(e)}"
            )
            raise GroupServiceError(
                f"Failed to add subreddit {subreddit} to group {group_id}"
            ) from e

    def _add_subreddit_to_group(
        self,
        conn,
        group_id: int,
        subreddit: str,
        flair_id: Optional[str] = None,
        flair_text: Optional[str] = None,
    ) -> int:
        """Internal helper to add a subreddit to a group using an existing connection."""
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO group_subreddits (group_id, subreddit, flair_id, flair_text) VALUES (?, ?, ?, ?)",
                (group_id, subreddit, flair_id, flair_text),
            )
        except sqlite3.IntegrityError as e:
            self.logger.error(
                f"Integrity error adding subreddit '{subreddit}' to group {group_id}: {str(e)}"
            )
            raise GroupServiceError(
                f"Subreddit '{subreddit}' already exists in group {group_id}"
            ) from e

        new_id = cursor.lastrowid
        self.logger.info(
            f"Subreddit '{subreddit}' added to group {group_id} with ID {new_id}"
        )
        return new_id

    def remove_subreddit_from_group(self, group_id: int, subreddit: str) -> bool:
        """Remove a subreddit from a group."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM group_subreddits WHERE group_id = ? AND subreddit = ?",
                    (group_id, subreddit),
                )
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(
                f"Error removing subreddit {subreddit} from group {group_id}: {str(e)}"
            )
            raise GroupServiceError(
                f"Failed to remove subreddit {subreddit} from group {group_id}"
            ) from e

    def get_current_timestamp(self) -> str:
        """Get the current timestamp in ISO format."""
        return datetime.datetime.now(self.timezone).isoformat()

    def _parse_schedule_time(self, value: str) -> datetime.datetime:
        """Parse a date string and apply DEFAULT_SCHED_TIME when only a date is given."""
        default_time = os.getenv("DEFAULT_SCHED_TIME", "00:00")
        try:
            h, m = [int(p) for p in default_time.split(":")]
        except Exception:
            h, m = 0, 0

        try:
            dt = datetime.datetime.fromisoformat(value)
            if "T" not in value and len(value.split()) == 1:
                dt = dt.replace(hour=h, minute=m)
        except ValueError:
            dt = datetime.datetime.strptime(value, "%Y-%m-%d")
            dt = dt.replace(hour=h, minute=m)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self.timezone)
        else:
            dt = dt.astimezone(self.timezone)
        return dt

    def save_post(self, post_data: Dict) -> Optional[int]:
        """Save a post record to the ``posts`` table.

        ``post_data`` must contain ``subreddit``, ``title``, ``created_at``,
        ``post_id`` and ``post_url``. Optional keys include ``content``,
        ``post_type``, ``comment``, ``flair_id``, ``flair_text``, ``status``, ``retry_count``,
        ``scheduled_for``, ``job_id`` and ``scheduled_at``.

        Returns the row ID of the created record.
        """

        self.logger.info(f"Saving post record for r/{post_data['subreddit']}")

        try:
            with get_connection() as conn:
                cursor = conn.cursor()


                cursor.execute(
                    """
                    INSERT INTO posts (
                        subreddit, title, content, image_path, created_at,
                        post_id, post_url, flair_id, flair_text, post_type, comment, comment_id, status,
                        campaign, retry_count, error_message, scheduled_for, job_id, scheduled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post_data["subreddit"],
                        post_data["title"],
                        post_data.get("content", ""),
                        post_data.get("image_path"),
                        post_data["created_at"],
                        post_data["post_id"],
                        post_data["post_url"],
                        post_data.get("flair_id"),
                        post_data.get("flair_text"),
                        post_data.get("post_type", "text"),
                        post_data.get("comment"),
                        post_data.get("comment_id"),
                        post_data.get("status", "waiting"),
                        post_data.get("campaign"),
                        post_data.get("retry_count", 0),
                        post_data.get("error_message"),
                        post_data.get("scheduled_for"),
                        post_data.get("job_id"),
                        post_data.get("scheduled_at"),
                    ),
                )

                post_id = cursor.lastrowid
                self.logger.info(f"Post record saved with ID: {post_id}")
                return post_id

        except sqlite3.Error as e:
            self.logger.error(f"Error saving post record: {str(e)}")
            raise GroupServiceError("Failed to save post") from e

    def create_processing_post(self, post_data: Dict) -> Optional[int]:
        """Insert a new post record with status 'processing'."""
        self.logger.info(
            f"Creating processing post record for r/{post_data.get('subreddit')}"
        )

        try:
            with get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO posts (
                        subreddit, title, content, image_path, created_at,
                        post_id, post_url, flair_id, flair_text, post_type, comment, comment_id, status,
                        campaign, retry_count, error_message, scheduled_for, job_id, scheduled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post_data.get("subreddit"),
                        post_data.get("title"),
                        post_data.get("content", ""),
                        post_data.get("image_path"),
                        post_data.get("created_at"),
                        post_data.get("post_id", ""),
                        post_data.get("post_url", ""),
                        post_data.get("flair_id"),
                        post_data.get("flair_text"),
                        post_data.get("post_type", "text"),
                        post_data.get("comment"),
                        post_data.get("comment_id"),
                        "processing",
                        post_data.get("campaign"),
                        post_data.get("retry_count", 0),
                        post_data.get("error_message"),
                        post_data.get("scheduled_for"),
                        post_data.get("job_id"),
                        post_data.get("scheduled_at"),
                    ),
                )
                post_id = cursor.lastrowid
                self.logger.info(f"Processing post record saved with ID: {post_id}")
                return post_id
        except sqlite3.Error as e:
            self.logger.error(f"Error saving processing post record: {str(e)}")
            raise GroupServiceError("Failed to create processing post") from e

    def create_scheduled_post(
        self, post_data: Dict, run_at: datetime.datetime
    ) -> Optional[int]:
        """Insert a new post record with status 'scheduled' and enqueue job."""

        self.logger.info(
            f"Scheduling post for r/{post_data.get('subreddit')} at {run_at}"
        )
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=self.timezone)
        scheduled_for = run_at.astimezone(self.timezone).isoformat()

        post_data = dict(post_data)
        if post_data.get("image_path"):
            post_data["image_path"] = os.path.basename(post_data["image_path"])
        post_data.setdefault("created_at", self.get_current_timestamp())
        post_data.setdefault("post_type", "text")
        post_data["status"] = "scheduled"
        post_data["scheduled_for"] = scheduled_for

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO posts (
                        subreddit, title, content, image_path, created_at,
                        post_id, post_url, flair_id, flair_text, post_type, comment, comment_id, status,
                        campaign, retry_count, error_message, scheduled_for, job_id, scheduled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post_data.get("subreddit"),
                        post_data.get("title"),
                        post_data.get("content", ""),
                        post_data.get("image_path"),
                        post_data.get("created_at"),
                        post_data.get("post_id", ""),
                        post_data.get("post_url", ""),
                        post_data.get("flair_id"),
                        post_data.get("flair_text"),
                        post_data.get("post_type", "text"),
                        post_data.get("comment"),
                        post_data.get("comment_id"),
                        "scheduled",
                        post_data.get("campaign"),
                        post_data.get("retry_count", 0),
                        post_data.get("error_message"),
                        scheduled_for,
                        None,
                        self.get_current_timestamp(),
                    ),
                )
                post_id = cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"Error saving scheduled post record: {str(e)}")
            raise GroupServiceError("Failed to create scheduled post") from e

        try:
            url = os.getenv("REDIS_URL", "redis://localhost")
            port = os.getenv("REDIS_PORT")
            redis_url = f"{url}:{port}/0" if port else f"{url}/0"
            redis_conn = redis.Redis.from_url(redis_url)
            scheduler = Scheduler(queue_name="posts", connection=redis_conn)
            from ..tasks.post_tasks import process_post

            job = scheduler.enqueue_at(run_at, process_post, post_id)
            with get_connection() as conn:
                conn.execute(
                    "UPDATE posts SET job_id = ? WHERE id = ?",
                    (job.id, post_id),
                )
        except Exception as e:
            self.logger.error(f"Error scheduling job for post {post_id}: {e}")
            with get_connection() as conn:
                conn.execute(
                    "UPDATE posts SET status = 'failed', error_message = ? WHERE id = ?",
                    (str(e), post_id),
                )
            return None

        return post_id

    def update_scheduled_post(
        self, post_id: int, run_at: datetime.datetime
    ) -> bool:
        """Update the scheduled time for a post and reschedule the job."""

        self.logger.info(f"Updating scheduled post {post_id} to {run_at}")

        post = self.get_post(post_id)
        if not post or post.get("status") not in {"scheduled", "overdue"}:
            return False

        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=self.timezone)
        scheduled_for = run_at.astimezone(self.timezone).isoformat()

        url = os.getenv("REDIS_URL", "redis://localhost")
        port = os.getenv("REDIS_PORT")
        redis_url = f"{url}:{port}/0" if port else f"{url}/0"
        redis_conn = redis.Redis.from_url(redis_url)
        scheduler = Scheduler(queue_name="posts", connection=redis_conn)

        if post.get("job_id"):
            try:
                scheduler.cancel(post["job_id"])
            except Exception as cancel_exc:
                self.logger.warning(
                    f"Error cancelling job {post['job_id']}: {cancel_exc}"
                )

        from ..tasks.post_tasks import process_post

        try:
            job = scheduler.enqueue_at(run_at, process_post, post_id)
            with get_connection() as conn:
                conn.execute(
                    "UPDATE posts SET scheduled_for = ?, job_id = ?, scheduled_at = ?, status = 'scheduled' WHERE id = ?",
                    (scheduled_for, job.id, self.get_current_timestamp(), post_id),
                )
            return True
        except Exception as e:
            self.logger.error(f"Error updating scheduled post {post_id}: {e}")
            return False

    def get_recent_posts(
        self,
        limit: int = 50,
        post_type: Optional[str] = None,
        search_query: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Dict]:
        """Get the most recent posts with optional filtering.

        Args:
            limit: Maximum number of posts to return
            offset: Row offset for pagination
            post_type: Filter by post type ('text', 'link', 'image') if provided
            status: Filter by post status ('scheduled', 'failed', etc.) if provided
            search_query: Filter by search term in title or content if provided
            start_date: Include posts created on or after this ``YYYY-MM-DD`` date
            end_date: Include posts created before the day after this ``YYYY-MM-DD`` date


        Returns:
            List of post dictionaries ordered by most recent first including status fields
        """
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM posts WHERE 1=1"
                params = []

                if post_type:
                    query += " AND post_type = ?"
                    params.append(post_type)

                if status:
                    query += " AND status = ?"
                    params.append(status)

                if search_query:
                    search_term = f"%{search_query}%"
                    query += (
                        " AND (title LIKE ? OR content LIKE ? OR subreddit LIKE ?"
                        " OR comment LIKE ? OR campaign LIKE ? OR flair_text LIKE ? OR error_message LIKE ?)"
                    )
                    params.extend(
                        [
                            search_term,
                            search_term,
                            search_term,
                            search_term,
                            search_term,
                            search_term,
                            search_term,
                        ]
                    )

                if start_date:
                    try:
                        start_dt = datetime.datetime.strptime(
                            start_date, "%Y-%m-%d"
                        ).replace(tzinfo=self.timezone)
                        query += " AND created_at >= ?"
                        params.append(start_dt.isoformat())
                    except ValueError:
                        self.logger.warning(f"Invalid start_date: {start_date}")

                if end_date:
                    try:
                        end_dt = datetime.datetime.strptime(
                            end_date, "%Y-%m-%d"
                        ).replace(tzinfo=self.timezone) + datetime.timedelta(days=1)
                        query += " AND created_at < ?"
                        params.append(end_dt.isoformat())
                    except ValueError:
                        self.logger.warning(f"Invalid end_date: {end_date}")

                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                self.logger.info(f"Executing query: {query} with params: {params}")
                cursor.execute(query, params)

                posts = [dict(row) for row in cursor.fetchall()]
                self.logger.info(f"Retrieved {len(posts)} recent posts")
                return posts

        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving recent posts: {str(e)}")
            raise GroupServiceError("Failed to retrieve recent posts") from e

    def count_posts(
        self,
        post_type: Optional[str] = None,
        search_query: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        """Return the total number of posts matching optional filters.

        Args:
            post_type: Filter by post type if provided.
            status: Filter by post status if provided.
        """
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT COUNT(*) FROM posts WHERE 1=1"
                params: List[Any] = []

                if post_type:
                    query += " AND post_type = ?"
                    params.append(post_type)

                if status:
                    query += " AND status = ?"
                    params.append(status)

                if search_query:
                    term = f"%{search_query}%"
                    query += (
                        " AND (title LIKE ? OR content LIKE ? OR subreddit LIKE ?"
                        " OR comment LIKE ? OR campaign LIKE ? OR flair_text LIKE ? OR error_message LIKE ?)"
                    )
                    params.extend([term, term, term, term, term, term, term])

                if start_date:
                    try:
                        start_dt = datetime.datetime.strptime(
                            start_date, "%Y-%m-%d"
                        ).replace(tzinfo=self.timezone)
                        query += " AND created_at >= ?"
                        params.append(start_dt.isoformat())
                    except ValueError:
                        self.logger.warning(f"Invalid start_date: {start_date}")

                if end_date:
                    try:
                        end_dt = datetime.datetime.strptime(
                            end_date, "%Y-%m-%d"
                        ).replace(tzinfo=self.timezone) + datetime.timedelta(days=1)
                        query += " AND created_at < ?"
                        params.append(end_dt.isoformat())
                    except ValueError:
                        self.logger.warning(f"Invalid end_date: {end_date}")

                cursor.execute(query, params)
                return cursor.fetchone()[0]

        except sqlite3.Error as e:
            self.logger.error(f"Error counting posts: {str(e)}")
            raise GroupServiceError("Failed to count posts") from e

    def fail_processing_posts(self) -> int:
        """Mark any posts stuck in the ``processing`` state as failed.

        Returns the number of rows updated.
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE posts SET status = 'failed' WHERE status = 'processing'"
            )
            return cursor.rowcount

    def mark_overdue_scheduled_posts(self) -> int:
        """Mark scheduled posts whose time has passed as overdue.

        Returns the number of rows updated.
        """
        now = datetime.datetime.now(self.timezone).isoformat()

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, job_id FROM posts WHERE status = 'scheduled' AND scheduled_for < ?",
                (now,),
            )
            rows = cursor.fetchall()

        if not rows:
            return 0

        job_ids = [row["job_id"] for row in rows if row["job_id"]]
        if job_ids:
            try:
                url = os.getenv("REDIS_URL", "redis://localhost")
                port = os.getenv("REDIS_PORT")
                redis_url = f"{url}:{port}/0" if port else f"{url}/0"
                redis_conn = redis.Redis.from_url(redis_url)
                scheduler = Scheduler(queue_name="posts", connection=redis_conn)
                for jid in job_ids:
                    try:
                        scheduler.cancel(jid)
                    except Exception as exc:
                        self.logger.warning(f"Error cancelling job {jid}: {exc}")
            except Exception as exc:
                self.logger.warning(f"Scheduler unavailable: {exc}")

        ids = [row["id"] for row in rows]
        placeholders = ",".join("?" for _ in ids)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE posts SET status = 'overdue', job_id = NULL WHERE id IN ({placeholders})",
                ids,
            )
            return cursor.rowcount

    def fail_overdue_posts(self) -> int:
        """Convert all overdue posts to failed status."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE posts SET status = 'failed' WHERE status = 'overdue'")
            return cursor.rowcount

    def delete_failed_posts(self) -> int:
        """Remove all posts with the ``failed`` status.

        Returns the number of rows deleted.
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM posts WHERE status = 'failed'")
            count = cursor.fetchone()[0]
            cursor.execute("DELETE FROM posts WHERE status = 'failed'")
            return count

    def delete_all_posts(self) -> int:
        """Remove all posts from the ``posts`` table.

        Returns the number of rows deleted.
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM posts")
            return cursor.rowcount

    def delete_posts(self, ids: List[int]) -> int:
        """Delete posts matching the provided IDs.

        Args:
            ids: List of post row IDs to delete.

        Returns:
            Number of rows deleted.
        """
        if not ids:
            return 0

        placeholders = ",".join("?" for _ in ids)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT id, job_id, status FROM posts WHERE id IN ({placeholders})",
                ids,
            )
            rows = cursor.fetchall()

        job_ids = [r["job_id"] for r in rows if r["status"] == "scheduled" and r["job_id"]]
        if job_ids:
            try:
                url = os.getenv("REDIS_URL", "redis://localhost")
                port = os.getenv("REDIS_PORT")
                redis_url = f"{url}:{port}/0" if port else f"{url}/0"
                redis_conn = redis.Redis.from_url(redis_url)
                scheduler = Scheduler(queue_name="posts", connection=redis_conn)
                for jid in job_ids:
                    try:
                        scheduler.cancel(jid)
                    except Exception as exc:
                        self.logger.warning(f"Error cancelling job {jid}: {exc}")
            except Exception as exc:
                self.logger.warning(f"Scheduler unavailable: {exc}")

        query = f"DELETE FROM posts WHERE id IN ({placeholders})"
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, ids)
            deleted = cursor.rowcount
            for pid in ids:
                self.delete_post_job_ids(pid)
            return deleted

    def get_post(self, post_id: int) -> Optional[Dict]:
        """Return a single post row by ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def duplicate_post(self, post_id: int) -> Optional[int]:
        """Duplicate an existing post and return the new post ID."""
        post = self.get_post(post_id)
        if not post:
            return None
        post_data = {
            "subreddit": post.get("subreddit"),
            "title": post.get("title"),
            "content": post.get("content"),
            "created_at": self.get_current_timestamp(),
            "flair_id": post.get("flair_id"),
            "flair_text": post.get("flair_text"),
            "post_type": post.get("post_type", "text"),
            "comment": post.get("comment"),
        }
        return self.create_processing_post(post_data)

    def repost_post(self, post_id: int) -> bool:
        """Reset an existing post so it can be reposted."""
        ts = self.get_current_timestamp()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE posts
                SET status = 'processing',
                    created_at = ?,
                    reddit_url = '',
                    post_id = '',
                    comment_id = '',
                    error_message = NULL
                WHERE id = ?
                """,
                (ts, post_id),
            )
            return cursor.rowcount > 0

    def mark_post_failed(self, post_id: int, message: str = None) -> bool:
        """Update a post row to ``failed`` status with an optional message."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE posts SET status = 'failed', error_message = ? WHERE id = ?",
                (message, post_id),
            )
            return cursor.rowcount > 0

    def mark_post_undone(self, post_id: int, message: str = None) -> bool:
        """Update a post row to ``undone`` status with an optional message."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE posts SET status = 'undone', error_message = ? WHERE id = ?",
                (message, post_id),
            )
            return cursor.rowcount > 0

    def get_post_job_ids(self, post_id: int) -> List[str]:
        """Return scheduler job IDs associated with the post."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS post_check_jobs (post_id INTEGER, job_id TEXT)"
            )
            cursor.execute(
                "SELECT job_id FROM post_check_jobs WHERE post_id = ?",
                (post_id,),
            )
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def delete_post_job_ids(self, post_id: int) -> None:
        """Remove scheduler job records for a post."""
        with get_connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS post_check_jobs (post_id INTEGER, job_id TEXT)"
            )
            conn.execute(
                "DELETE FROM post_check_jobs WHERE post_id = ?",
                (post_id,),
            )

    def undo_post(self, post_id: int) -> bool:
        """Delete the Reddit submission and mark it as undone."""
        post = self.get_post(post_id)
        if not post:
            return False

        reddit_id = post.get("post_id")
        comment_id = post.get("comment_id")

        job_ids = self.get_post_job_ids(post_id)

        from flask import current_app, has_app_context
        from .reddit_service import RedditService

        try:
            reddit_service = (
                current_app.reddit
                if has_app_context()
                else RedditService(self.settings)
            )
            if comment_id:
                reddit_service.delete_comment(comment_id)
            if reddit_id:
                reddit_service.delete_post(reddit_id)
            try:
                from reddit_manager.tasks.post_tasks import scheduler
            except Exception:
                url = os.getenv("REDIS_URL", "redis://localhost")
                port = os.getenv("REDIS_PORT")
                redis_url = f"{url}:{port}/0" if port else f"{url}/0"
                redis_conn = redis.Redis.from_url(redis_url)
                scheduler = Scheduler(queue_name="posts", connection=redis_conn)
            for jid in job_ids:
                try:
                    scheduler.cancel(jid)
                except Exception as cancel_exc:
                    self.logger.warning(f"Error cancelling job {jid}: {cancel_exc}")
            self.delete_post_job_ids(post_id)
        except Exception as e:
            self.logger.error(f"Error undoing post {post_id}: {e}")
            self.mark_post_failed(post_id, f"Undo failed: {e}")
            return False

        return self.mark_post_undone(post_id, "Post undone")

    def undo_posts(self, ids: List[int]) -> int:
        """Undo multiple posts and return the count."""
        count = 0
        for pid in ids:
            if self.undo_post(pid):
                count += 1
        return count

    def repost_posts(self, ids: List[int]) -> int:
        """Repost multiple posts and return the count."""
        count = 0
        for pid in ids:
            if self.repost_post(pid):
                count += 1
        return count
