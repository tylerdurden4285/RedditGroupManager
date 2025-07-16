from flask import Blueprint, render_template, redirect, url_for, current_app, request, Response
import logging
import os
import requests
import redis
from rq_scheduler import Scheduler
from reddit_manager.utils import get_app_version


main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)
VERSION = get_app_version()


@main_bp.route('/')
def index():
    """Render the main application home page."""
    return render_template('home.html', page_title="Home")


@main_bp.route('/manage_posts')
def manage_posts():
    """Redirect to the unified post history page."""
    return redirect(url_for('posts.post_history'))


@main_bp.route('/faq')
def faq():
    """Render the FAQ page."""
    return render_template('faq.html')


@main_bp.route('/status')
def system_status():
    """Display system status information and connection tests."""
    timezone = os.getenv("TZ", "UTC")
    
    db_status = False
    db_message = "Could not connect to database"
    try:
        
        current_app.group_manager.list_groups()
        db_status = True
        db_message = "Connected successfully"
    except Exception as e:
        logger.error(f"Database status check failed: {str(e)}")
        db_message = f"Error: {str(e)}"
    
    
    reddit_status = False
    reddit_message = "Could not connect to Reddit API"
    try:
        
        if current_app.reddit and current_app.reddit.reddit:
            
            username = current_app.reddit.get_reddit_username()
            if username:
                reddit_status = True
                reddit_message = f"Connected as {username}"
            else:
                reddit_message = "Reddit API connection established but no username set"
        else:
            reddit_message = "Reddit client not initialized. Check your .env file."
    except Exception as e:
        logger.error(f"Reddit API status check failed: {str(e)}")
        reddit_message = f"Error: {str(e)}"
    
    
    api_status = False
    api_message = "Could not connect to API server"
    try:

        api_host = os.getenv("API_STATUS_HOST", "localhost")
        api_port = os.getenv("API_PORT", "8015")
        api_url = f"{request.scheme}://{api_host}:{api_port}/api/v1/groups"
        headers = {}
        auth_key = os.getenv("AUTH_KEY")
        if auth_key:
            headers["Authorization"] = auth_key
        response = requests.get(api_url, timeout=2, headers=headers)
        if response.status_code == 200:
            api_status = True
            api_message = "API server is responding"
        else:
            api_message = f"API server responded with status code {response.status_code}"
    except requests.RequestException as e:
        logger.error(f"API server status check failed: {str(e)}")
        api_message = f"Error: {str(e)}"

    
    redis_status = False
    redis_message = "Could not connect to Redis server. Please ensure a Redis service is running."
    try:
        if current_app.redis_conn:
            current_app.redis_conn.ping()
            redis_status = True
            redis_message = "Redis server is responding"
        else:
            redis_message = "Redis connection not initialized"
    except Exception as e:
        logger.error(f"Redis server status check failed: {str(e)}")
        redis_message = f"Error: {str(e)}. Please ensure a Redis service is running."

    
    scheduler_status = False
    scheduler_message = "Could not connect to scheduler"
    try:
        url = os.getenv("REDIS_URL", "redis://localhost")
        port = os.getenv("REDIS_PORT")
        redis_url = f"{url}:{port}/0" if port else f"{url}/0"
        redis_conn = redis.Redis.from_url(redis_url)
        scheduler = Scheduler(queue_name="posts", connection=redis_conn)
        scheduler.connection.ping()
        scheduler.get_jobs()
        scheduler_status = True
        scheduler_message = "Scheduler is responding"
    except Exception as e:
        logger.error(f"Scheduler connection failed: {e}")
        scheduler_message = f"Error: {e}"

    
    return render_template('status.html',
                           db_status=db_status,
                           db_message=db_message,
                           reddit_status=reddit_status,
                           reddit_message=reddit_message,
                           api_status=api_status,
                           api_message=api_message,
                           redis_status=redis_status,
                           redis_message=redis_message,
                           scheduler_status=scheduler_status,
                           scheduler_message=scheduler_message,
                           timezone=timezone,
                           version=VERSION)
