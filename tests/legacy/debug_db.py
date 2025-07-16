#!/usr/bin/env python3
import os
import sys
import time
import sqlite3
import logging
from legacy.group_manager import GroupManager


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_db.log')
    ]
)
logger = logging.getLogger("debug_db")

def check_db_exists(db_path):
    """Check if the database file exists and print its details."""
    logger.info(f"Checking database at path: {db_path}")
    if os.path.exists(db_path):
        logger.info(f"Database file exists: {db_path}")
        file_size = os.path.getsize(db_path)
        logger.info(f"File size: {file_size} bytes")
        file_permissions = oct(os.stat(db_path).st_mode)[-3:]
        logger.info(f"File permissions: {file_permissions}")
        return True
    else:
        logger.error(f"Database file does not exist: {db_path}")
        return False

def check_db_connection(db_path):
    """Try to connect to the database and report any issues."""
    logger.info(f"Testing database connection to: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        logger.info("Connection successful")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        return False

def check_db_tables(db_path):
    """Check the database tables and their contents."""
    logger.info(f"Checking database tables in: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logger.info(f"Tables found: {[table[0] for table in tables]}")
        
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            logger.info(f"Table '{table_name}' has {count} records")
            
            
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                sample = cursor.fetchall()
                logger.info(f"Sample data from '{table_name}': {sample}")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error checking tables: {str(e)}")
        return False

def check_for_locks(db_path):
    """Check if the database has any locks."""
    logger.info("Checking for database locks...")
    
    
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=exclusive", uri=True, timeout=1)
        logger.info("No locks detected - able to open database in exclusive mode")
        conn.close()
        return False
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            logger.warning("Database appears to be locked")
            return True
        else:
            logger.error(f"Error checking locks: {str(e)}")
            return False

def test_group_manager(db_path):
    """Test GroupManager operations to verify functionality."""
    logger.info("Testing GroupManager operations...")
    try:
        
        gm = GroupManager(db_path=db_path)
        
        
        logger.info("Listing all groups...")
        groups = gm.list_groups()
        logger.info(f"Found {len(groups)} groups")
        for group in groups:
            logger.info(f"Group: {group['id']} - {group['name']}")
            
            
            subreddits = gm.get_group_subreddits(group['id'])
            logger.info(f"Group {group['id']} has {len(subreddits)} subreddits")
        
        
        test_group_name = f"Test Group {int(time.time())}"
        logger.info(f"Creating test group: {test_group_name}")
        group_id = gm.create_group(test_group_name, "Created by debug tool")
        logger.info(f"Test group created with ID: {group_id}")
        
        
        group = gm.get_group(group_id)
        if group:
            logger.info(f"Successfully retrieved group: {group['name']}")
        else:
            logger.error("Failed to retrieve newly created group")
        
        
        logger.info(f"Deleting test group {group_id}")
        result = gm.delete_group(group_id)
        logger.info(f"Delete result: {result}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing GroupManager: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def examine_flask_config():
    """Try to examine Flask configuration."""
    try:
        from legacy import app
        logger.info("Flask app configuration:")
        for key in sorted(app.config.keys()):
            
            if "SECRET" in key or "PASSWORD" in key:
                continue
            logger.info(f"  {key}: {app.config[key]}")
    except Exception as e:
        logger.error(f"Could not examine Flask config: {str(e)}")

def reset_database(db_path):
    """Reset the database by moving the current file and creating a new one."""
    try:
        logger.warning("Attempting to reset the database")
        
        
        if os.path.exists(db_path):
            backup_path = f"{db_path}.backup.{int(time.time())}"
            os.rename(db_path, backup_path)
            logger.info(f"Backed up existing database to {backup_path}")
        
        
        gm = GroupManager(db_path=db_path)
        logger.info("Created new database")
        
        
        group_id = gm.create_group("Default Group", "Created during database reset")
        logger.info(f"Created default group with ID: {group_id}")
        
        return True
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

def main():
    """Main diagnostic function."""
    logger.info("====== Reddit Group Manager Database Diagnostic Tool ======")
    
    
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'reddit_groups.db')
    logger.info(f"Using database path: {db_path}")
    
    
    db_exists = check_db_exists(db_path)
    if not db_exists:
        logger.warning("Database file doesn't exist - will be created during tests")
    
    db_connection_ok = check_db_connection(db_path)
    if not db_connection_ok:
        logger.error("Database connection failed - severe issue detected")
        if input("Would you like to reset the database? (y/n): ").lower() == 'y':
            reset_database(db_path)
        return
    
    is_locked = check_for_locks(db_path)
    if is_locked:
        logger.warning("Database appears to be locked by another process")
        if input("Would you like to force close all database connections? (y/n): ").lower() == 'y':
            os.system(f"fuser -k {db_path}")
            logger.info("Attempted to kill processes using the database")
    
    db_tables_ok = check_db_tables(db_path)
    if not db_tables_ok:
        logger.error("Error examining database tables")
    
    gm_test_ok = test_group_manager(db_path)
    if not gm_test_ok:
        logger.error("GroupManager tests failed")
        if input("Would you like to reset the database? (y/n): ").lower() == 'y':
            reset_database(db_path)
    
    examine_flask_config()
    
    logger.info("====== Diagnostic Complete ======")
    if db_exists and db_connection_ok and db_tables_ok and gm_test_ok:
        logger.info("RESULT: Database appears to be functioning correctly")
    else:
        logger.warning("RESULT: Database issues detected - see log for details")

if __name__ == "__main__":
    main()
