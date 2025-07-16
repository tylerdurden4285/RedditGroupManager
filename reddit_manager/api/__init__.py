from flask import Flask


def register_api_blueprints(app: Flask):
    """
    Register all API blueprints with the Flask application.
    
    Args:
        app (Flask): Flask application instance
    """
    from .groups import groups_api
    from .reddit import reddit_api
    from .admin import admin_api
    
    app.register_blueprint(groups_api, url_prefix='/api/v1/groups')
    app.register_blueprint(reddit_api, url_prefix='/api/v1/reddit')
    app.register_blueprint(admin_api, url_prefix='/admin')
