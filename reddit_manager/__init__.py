from flask import Flask
from flask_cors import CORS
from flask_toastr import Toastr
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import logging

from .config import config_by_name
from .config.settings import Settings
from .extensions import csrf
from .utils.logging import setup_logging





USER_ENV_FILES = {}


def create_app(config_name: str = "development", settings: Settings | None = None):
    """
    Application factory for creating Flask app instances.
    
    Args:
        config_name (str): Configuration environment to use ('development', 'testing', or 'production')
        
    Returns:
        Flask: Configured Flask application instance
    """
    if settings is None:
        settings = Settings()

    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, "..", "templates")
    static_dir = os.path.join(base_dir, "..", "static")
    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    
    Toastr(app)
    
    
    app.config.from_object(config_by_name[config_name])
    app.config.setdefault("USER_DB_PATH", settings.user_db_path or app.config["DATABASE_PATH"])
    app.config["SETTINGS"] = settings
    app.config.setdefault("DEFAULT_SCHED_TIME", settings.default_sched_time)
    
    
    setup_logging(app)
    
    
    if app.config['WTF_CSRF_ENABLED']:
        csrf.init_app(app)
        
        
        @app.context_processor
        def inject_csrf_token():
            from flask_wtf.csrf import generate_csrf
            return dict(csrf_token=generate_csrf())
    else:
        
        @app.context_processor
        def inject_csrf_token():
            return dict(csrf_token="disabled-for-development")
    
    
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    
    from .utils.db import init_db
    init_db(app)
    
    
    CORS(app, supports_credentials=True)

    
    from .services.user_service import UserService
    user_service = UserService(settings, app)
    app.user_service = user_service


    
    
    from .services.reddit_service import RedditService
    from .services.group_service import GroupService

    
    app.reddit = RedditService(settings)
    app.group_manager = GroupService(settings)
    try:
        app.group_manager.mark_overdue_scheduled_posts()
    except Exception as exc:
        app.logger.warning(f"Error checking overdue posts: {exc}")

    
    from redis import Redis
    from rq import Queue

    class DummyQueue:
        def enqueue(self, func, *args, **kwargs):
            app.logger.warning("Redis not available, running task synchronously")
            func(*args, **kwargs)

    url = os.getenv('REDIS_URL', 'redis://localhost')
    port = os.getenv('REDIS_PORT')
    if port:
        redis_url = f"{url}:{port}/0"
    else:
        redis_url = f"{url}/0"
    try:
        redis_conn = Redis.from_url(redis_url)
        redis_conn.ping()
        queue = Queue(connection=redis_conn)
    except Exception:
        redis_conn = None
        queue = DummyQueue()

    app.redis_conn = redis_conn
    app.queue = queue
    
    
    from .commands import register_commands
    register_commands(app)
    
    
    from .web import register_web_blueprints
    from .api import register_api_blueprints

    register_web_blueprints(app)
    register_api_blueprints(app)

    
    
    
    from rq_dashboard_fast import RedisQueueDashboard
    from starlette.middleware.wsgi import WSGIMiddleware
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.wrappers import Request, Response

    dashboard = RedisQueueDashboard(redis_url=redis_url, prefix="/rq")

    def auth_wrapper(wsgi_app):
        def _middleware(environ, start_response):
            req = Request(environ)
            api_key = req.headers.get("Authorization")
            env_key = os.getenv("AUTH_KEY")
            if not env_key or api_key != env_key:
                res = Response("Forbidden", status=403)
                return res(environ, start_response)
            return wsgi_app(environ, start_response)

        return _middleware

    dashboard_wsgi = WSGIMiddleware(dashboard)
    app.wsgi_app = DispatcherMiddleware(
        app.wsgi_app, {"/rq": auth_wrapper(dashboard_wsgi)}
    )
    
    
    @app.context_processor
    def inject_context():
        from datetime import datetime
        now = datetime.now(app.group_manager.timezone)
        
        
        reddit_username = "Not connected"
        reddit_connected = False
        try:
            if hasattr(app, 'reddit') and app.reddit:
                reddit_connected = app.reddit.is_connected()
                username = app.reddit.get_reddit_username()
                if username:
                    reddit_username = username
        except Exception as e:
            app.logger.error(f"Error getting Reddit username: {str(e)}")

        return {
            'now': now,
            'current_year': now.year,
            'reddit_username': reddit_username,
            'reddit_connected': reddit_connected,
            'debug': app.debug
        }
    
    
    
    return app
