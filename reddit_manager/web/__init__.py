from flask import Flask


def register_web_blueprints(app: Flask):
    """
    Register all web blueprints with the Flask application.
    
    Args:
        app (Flask): Flask application instance
    """
    from .main import main_bp
    from .groups import groups_bp
    from .posts_history import posts_history_bp
    from .posts_create import posts_create_bp
    from .posts_actions import posts_actions_bp
    from .temp_files import temp_files_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(groups_bp, url_prefix='/groups')
    app.register_blueprint(posts_history_bp)
    app.register_blueprint(posts_create_bp)
    app.register_blueprint(posts_actions_bp)
    app.register_blueprint(temp_files_bp)
