import os
import sqlite3
import logging
from typing import Optional
from flask import Flask


logger = logging.getLogger(__name__)

def get_connection():
    """
    Get a database connection with consistent settings.
    
    Returns:
        sqlite3.Connection: A configured SQLite connection
    """
    from flask import current_app
    
    
    try:
        db_path = current_app.config['DATABASE_PATH']
    except RuntimeError:
        
        instance_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'instance')
        db_path = os.path.join(instance_dir, 'app.db')
    
    logger.debug(f"Opening connection to {db_path}")
    
    
    dir_path = os.path.dirname(db_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    
    
    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
    conn.execute('PRAGMA busy_timeout = 30000')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    return conn

def init_db(app: Optional[Flask] = None):
    """
    Initialize the database schema.
    
    Args:
        app (Flask, optional): Flask app instance. Defaults to None.
    """
    if app:
        db_path = app.config['DATABASE_PATH']
    else:
        instance_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'instance')
        db_path = os.path.join(instance_dir, 'app.db')
    
    logger.info(f"Initializing database at {db_path}")
    
    
    dir_path = os.path.dirname(db_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    
    try:
        conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
        conn.execute('PRAGMA busy_timeout = 30000')
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        with conn:
            
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    api_key TEXT NOT NULL UNIQUE
                )
            """
            )

            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS group_subreddits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    subreddit TEXT NOT NULL,
                    flair_id TEXT,
                    FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                    UNIQUE(group_id, subreddit)
                )
            ''')


        logger.info("Database initialized successfully")
        ensure_flair_text_column()
        ensure_posts_table()
        ensure_error_message_column()
        migrate_user_table()
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

def migrate_group_subreddit_name_column():
    """Rename 'name' column to 'subreddit' in group_subreddits if needed."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='group_subreddits'")
            if not cursor.fetchone():
                logger.info("group_subreddits table doesn't exist, skipping migration")
                return

            cursor.execute("PRAGMA table_info(group_subreddits)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'subreddit' in columns:
                
                return

            if 'name' in columns:
                logger.info("Renaming column 'name' to 'subreddit' on group_subreddits table")
                cursor.execute("ALTER TABLE group_subreddits RENAME COLUMN name TO subreddit")
                logger.info("Column rename completed")
    except sqlite3.Error as e:
        logger.error(f"SQLite error during migration: {str(e)}")
        raise


def ensure_flair_text_column():
    """Add flair_text column to group_subreddits table if it doesn't exist."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='group_subreddits'"
            )
            if not cursor.fetchone():
                logger.info(
                    "group_subreddits table doesn't exist, skipping flair_text migration"
                )
                return

            cursor.execute("PRAGMA table_info(group_subreddits)")
            columns = [row[1] for row in cursor.fetchall()]

            if "flair_text" not in columns:
                logger.info("Adding flair_text column to group_subreddits table")
                cursor.execute(
                    "ALTER TABLE group_subreddits ADD COLUMN flair_text TEXT"
                )
                logger.info("flair_text column added successfully")
            else:
                logger.info("flair_text column already exists")
    except sqlite3.Error as e:
        logger.error(f"SQLite error ensuring flair_text column: {str(e)}")
        raise


def ensure_posts_table():
    """Create the posts table if it doesn't already exist."""
    try:
        with get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subreddit TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    image_path TEXT,
                    created_at TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    post_url TEXT NOT NULL,
                    flair_id TEXT,
                    flair_text TEXT,
                    post_type TEXT,
                    comment TEXT,
                    comment_id TEXT,
                    status TEXT DEFAULT 'waiting',
                    campaign TEXT,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    scheduled_for TEXT,
                    job_id TEXT,
                    scheduled_at TEXT
                )
                """
            )
    except sqlite3.Error as e:
        logger.error(f"SQLite error creating posts table: {str(e)}")
        raise


def ensure_error_message_column():
    """Add error_message column to posts table if it doesn't exist."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"
            )
            if not cursor.fetchone():
                logger.info("posts table doesn't exist, skipping error_message migration")
                return
            cursor.execute("PRAGMA table_info(posts)")
            columns = [row[1] for row in cursor.fetchall()]
            if "error_message" not in columns:
                logger.info("Adding error_message column to posts table")
                cursor.execute("ALTER TABLE posts ADD COLUMN error_message TEXT")
                logger.info("error_message column added successfully")
            else:
                logger.info("error_message column already exists")
    except sqlite3.Error as e:
        logger.error(f"SQLite error ensuring error_message column: {str(e)}")
        raise


def migrate_user_table():
    """Remove the deprecated env_file column and ensure api_key exists."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
            )
            if not cursor.fetchone():
                return

            cursor.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cursor.fetchall()]

            if "env_file" in columns:
                logger.info("Dropping obsolete env_file column from users table")
                cursor.execute("ALTER TABLE users DROP COLUMN env_file")
                columns.remove("env_file")

            if "api_key" not in columns:
                logger.info("Adding api_key column to users table")
                cursor.execute("ALTER TABLE users ADD COLUMN api_key TEXT UNIQUE")
    except sqlite3.Error as e:
        logger.error(f"SQLite error migrating users table: {str(e)}")
        raise

