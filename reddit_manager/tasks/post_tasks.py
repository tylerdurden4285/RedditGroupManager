import logging
import os
import re
import datetime
from datetime import timedelta
from typing import Optional, List

from redis import Redis
from flask import current_app
from rq.decorators import job
from rq.job import Retry
from rq import get_current_job
from rq_scheduler import Scheduler
import praw
import prawcore

from ..services.reddit_service import RedditService
from ..services.group_service import GroupService
from ..utils.db import get_connection
from ..config.settings import Settings


url = os.getenv("REDIS_URL", "redis://localhost")
port = os.getenv("REDIS_PORT")
if port:
    redis_url = f"{url}:{port}/0"
else:
    redis_url = f"{url}/0"
redis_conn = Redis.from_url(redis_url)
scheduler = Scheduler(queue_name="posts", connection=redis_conn)


retry_strategy = Retry(max=5, interval=[2**i for i in range(1, 6)])

logger = logging.getLogger(__name__)

DEFAULT_MOD_CHECK_INTERVALS: List[timedelta] = (
    [timedelta(seconds=5 * (i + 1)) for i in range(4)]
    + [timedelta(minutes=10 * (i + 1)) for i in range(6)]
    + [timedelta(hours=i + 1) for i in range(24)]
)

def _parse_mod_intervals(value: str) -> List[timedelta]:
    intervals: List[timedelta] = []
    for part in value.split(","):
        token = part.strip().lower()
        if not token:
            continue
        m = re.fullmatch(r"(\d+)([smhd])", token)
        if not m:
            logger.warning("Invalid interval '%s' in POST_MOD_CHECK_INTERVALS", token)
            continue
        num = int(m.group(1))
        unit = m.group(2)
        if unit == "s":
            intervals.append(timedelta(seconds=num))
        elif unit == "m":
            intervals.append(timedelta(minutes=num))
        elif unit == "h":
            intervals.append(timedelta(hours=num))
        else:
            intervals.append(timedelta(days=num))
    return intervals

def _load_mod_intervals() -> List[timedelta]:
    env_value = os.getenv("POST_MOD_CHECK_INTERVALS")
    if not env_value:
        return DEFAULT_MOD_CHECK_INTERVALS
    intervals = _parse_mod_intervals(env_value)
    if not intervals:
        logger.warning("POST_MOD_CHECK_INTERVALS had no valid values; using defaults")
        return DEFAULT_MOD_CHECK_INTERVALS
    return intervals

MOD_CHECK_INTERVALS = _load_mod_intervals()



def _ensure_status_columns() -> None:
    """Ensure posts table has required status columns."""

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(posts)")
        columns = [row[1] for row in cursor.fetchall()]
        if "status" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN status TEXT DEFAULT 'pending'")
        if "retry_count" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN retry_count INTEGER DEFAULT 0")
        if "reddit_url" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN reddit_url TEXT")
        if "flair_id" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN flair_id TEXT")
        if "error_message" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN error_message TEXT")
        if "comment_id" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN comment_id TEXT")
        if "campaign" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN campaign TEXT")
        if "image_path" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN image_path TEXT")


def _record_job_id(post_id: int, job_id: str) -> None:
    """Insert a scheduled moderation job row."""
    with get_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS post_check_jobs (post_id INTEGER, job_id TEXT)"
        )
        conn.execute(
            "INSERT INTO post_check_jobs (post_id, job_id) VALUES (?, ?)",
            (post_id, job_id),
        )


@job("posts", connection=redis_conn, retry=retry_strategy)
def process_post(post_id: int) -> Optional[str]:
    """Process a queued post and submit it to Reddit."""
    logger.info("Processing post %s", post_id)
    _ensure_status_columns()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()
        if not row:
            logger.error("Post %s not found", post_id)
            return None

    subreddit = row["subreddit"]
    title = row["title"]
    content = row["content"] or ""
    post_type = (
        row.get("post_type", "text") if hasattr(row, "get") else row["post_type"]
    )
    flair_id = row.get("flair_id") if hasattr(row, "get") else row["flair_id"]
    comment_text = row.get("comment") if hasattr(row, "get") else row["comment"]

    retry_count = (
        row.get("retry_count", 0) if hasattr(row, "get") else row["retry_count"]
    )

    job = get_current_job()
    image_path = content if post_type == "image" else None
    try:
        reddit_service = current_app.reddit
    except Exception:
        reddit_service = RedditService(Settings())

    try:
        if post_type == "link":
            submission_id = reddit_service.post_link_to_subreddit(
                subreddit, title, content, flair_id
            )
        elif post_type == "image":
            submission = reddit_service.reddit.subreddit(subreddit).submit_image(
                title, image_path, flair_id=flair_id
            )
            submission_id = submission.id
            image_url = submission.url
        else:
            submission_id = reddit_service.post_to_subreddit(
                subreddit, title, content, flair_id
            )

        reddit_url = f"https://www.reddit.com/r/{subreddit}/comments/{submission_id}"

        comment_id = None
        if comment_text:
            try:
                comment_id, _ = reddit_service.comment_on_post(
                    submission_id, comment_text
                )
            except Exception as comment_exc:  
                logger.error(
                    "Error commenting on post %s: %s", submission_id, comment_exc
                )

        status = "waiting"
        with get_connection() as conn:
            if post_type == "image":
                conn.execute(
                    "UPDATE posts SET status = ?, reddit_url = ?, post_id = ?, retry_count = ?, content = ?, comment_id = ?, error_message = NULL WHERE id = ?",
                    (
                        status,
                        reddit_url,
                        submission_id,
                        retry_count,
                        image_url,
                        comment_id,
                        post_id,
                    ),
                )
            else:
                conn.execute(
                    "UPDATE posts SET status = ?, reddit_url = ?, post_id = ?, retry_count = ?, comment_id = ?, error_message = NULL WHERE id = ?",
                    (
                        status,
                        reddit_url,
                        submission_id,
                        retry_count,
                        comment_id,
                        post_id,
                    ),
                )
        logger.info("Post %s submitted successfully", post_id)

        total_checks = len(MOD_CHECK_INTERVALS)
        for idx, delay in enumerate(MOD_CHECK_INTERVALS, start=1):
            job = scheduler.enqueue_in(
                delay,
                check_moderation_status,
                post_id,
                submission_id,
                idx,
                total_checks,
            )
            _record_job_id(post_id, job.id)

        return reddit_url

    except prawcore.exceptions.TooManyRequests as e:
        sleep_time = int(e.response.headers.get("Retry-After", 60))
        logger.warning(
            "Reddit rate limit hit for post %s. Retrying in %s seconds",
            post_id,
            sleep_time,
        )
        retry_count += 1
        status = "retrying"
        if job:
            job.retry_intervals = [sleep_time]
            job.retries_left = max(job.retries_left - 1, 0)
        with get_connection() as conn:
            conn.execute(
                "UPDATE posts SET status = ?, retry_count = ?, error_message = ? WHERE id = ?",
                (status, retry_count, str(e), post_id),
            )
        raise

    except praw.exceptions.APIException as e:
        if e.error_type.lower() == "ratelimit":
            match = re.search(r"(\d+)\s*(minutes?|seconds?)", e.message)
            if match:
                delay = int(match.group(1))
                if "minute" in match.group(2):
                    delay *= 60
            else:
                delay = 60
            logger.warning(
                "Reddit APIException rate limit for post %s. Retrying in %s seconds",
                post_id,
                delay,
            )
            retry_count += 1
            status = "retrying"
            if job:
                job.retry_intervals = [delay]
                job.retries_left = max(job.retries_left - 1, 0)
            with get_connection() as conn:
                conn.execute(
                    "UPDATE posts SET status = ?, retry_count = ?, error_message = ? WHERE id = ?",
                    (status, retry_count, e.message, post_id),
                )
            raise
        else:
            logger.error("Error posting to Reddit for post %s: %s", post_id, e)
            retry_count += 1
            status = "retrying"
            if retry_count >= retry_strategy.max or (job and job.retries_left <= 0):
                status = "failed"
            with get_connection() as conn:
                conn.execute(
                    "UPDATE posts SET status = ?, retry_count = ?, error_message = ? WHERE id = ?",
                    (status, retry_count, str(e), post_id),
                )
            raise

    except RedditService.SubredditNotFoundError as e:
        logger.error("Subreddit not found for post %s: %s", post_id, e)
        retry_count += 1
        status = "failed"
        with get_connection() as conn:
            conn.execute(
                "UPDATE posts SET status = ?, retry_count = ?, error_message = ? WHERE id = ?",
                (status, retry_count, str(e), post_id),
            )
        return None

    except Exception as e:
        logger.error("Error posting to Reddit for post %s: %s", post_id, e)
        retry_count += 1
        status = "retrying"
        if retry_count >= retry_strategy.max or (job and job.retries_left <= 0):
            status = "failed"
        with get_connection() as conn:
            conn.execute(
                "UPDATE posts SET status = ?, retry_count = ?, error_message = ? WHERE id = ?",
                (status, retry_count, str(e), post_id),
            )
        raise

    finally:
        # Keep temporary images until cleanup_temp_files runs or the post is
        # deleted. This avoids broken links for scheduled or undone posts.
        pass


@job("posts", connection=redis_conn)
def check_moderation_status(post_id: int, submission_id: str, attempt: int, total_attempts: int) -> bool:
    """Check if a Reddit submission has been approved by moderators."""
    logger.info("Checking moderation status for post %s attempt %s/%s", post_id, attempt, total_attempts)
    
    with get_connection() as conn:
        status_row = conn.execute(
            "SELECT status FROM posts WHERE id = ?",
            (post_id,),
        ).fetchone()
    if not status_row:
        return False
    current = status_row["status"]
    if current in {"undone", "posted", "failed"}:
        logger.info("Post %s already %s; skipping moderation check", post_id, current)
        return False
    try:
        reddit_service = current_app.reddit  
    except Exception:  
        reddit_service = RedditService(Settings())

    try:
        submission = reddit_service.reddit.submission(id=submission_id)
        submission._fetch()
        approved = getattr(submission, "approved", False)
        removed = getattr(submission, "removed_by_category", None)
    except Exception as exc:  
        logger.error("Error loading submission %s: %s", submission_id, exc)
        approved = False
        removed = None

    if approved or removed is None:
        with get_connection() as conn:
            conn.execute("UPDATE posts SET status = 'posted' WHERE id = ?", (post_id,))
        logger.info("Post %s approved", post_id)
        return True

    if removed == "reddit":
        with get_connection() as conn:
            conn.execute("UPDATE posts SET status = 'filtered' WHERE id = ?", (post_id,))
        logger.info("Post %s filtered by reddit", post_id)
        return False

    if removed:
        with get_connection() as conn:
            conn.execute("UPDATE posts SET status = 'awaiting' WHERE id = ?", (post_id,))
        logger.info("Post %s awaiting moderation", post_id)
        return False

    if attempt >= total_attempts:
        with get_connection() as conn:
            conn.execute("UPDATE posts SET status = 'failed' WHERE id = ?", (post_id,))
        logger.info("Post %s failed moderation after final check", post_id)
        return False

    return False


@job("posts", connection=redis_conn, retry=retry_strategy)
def undo_post_task(post_id: int) -> bool:
    """Undo a post by ID using :class:`GroupService`."""
    logger.info("Undoing post %s", post_id)
    _ensure_status_columns()
    try:
        group_service = current_app.group_manager  
    except Exception:  
        group_service = GroupService(Settings())
    return group_service.undo_post(post_id)


@job("posts", connection=redis_conn)
def cleanup_temp_files(max_age_hours: int | None = None) -> int:
    """Delete leftover images older than ``max_age_hours`` from the temp folder."""
    if max_age_hours is None:
        try:
            max_age_hours = int(os.getenv("TEMP_FILE_MAX_AGE_HOURS", "24"))
        except ValueError:
            max_age_hours = 24

    cutoff = datetime.datetime.now() - datetime.timedelta(hours=max_age_hours)
    try:
        temp_root = current_app.instance_path
    except Exception:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        temp_root = os.path.join(base_dir, "instance")
    temp_dir = os.path.join(temp_root, "temp")
    if not os.path.isdir(temp_dir):
        return 0

    removed = 0
    for name in os.listdir(temp_dir):
        path = os.path.join(temp_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
            if mtime < cutoff:
                os.remove(path)
                removed += 1
        except Exception as exc:
            logger.warning("Failed to remove temp file %s: %s", path, exc)
    if removed:
        logger.info("Removed %s old temp files", removed)
    return removed
