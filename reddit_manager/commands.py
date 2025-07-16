import click
from flask import current_app
from flask.cli import with_appcontext
import logging

logger = logging.getLogger(__name__)


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database with required tables."""
    from .utils.db import init_db
    
    click.echo('Initializing the database...')
    init_db(current_app)
    click.echo('Database initialized successfully.')


def register_commands(app):
    """Register CLI commands with the Flask application."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(generate_api_key_command)
    app.cli.add_command(create_admin_command)


@click.command("generate-api-key")
@click.argument("username")
@with_appcontext
def generate_api_key_command(username):
    """Generate or rotate an API key for USERNAME."""
    from .services.user_service import UserService
    from .config.settings import Settings

    service = UserService(Settings(), current_app)
    key = service.generate_api_key(username)
    click.echo(f"API key for {username}: {key}")


@click.command("create-admin")
@with_appcontext
def create_admin_command():
    """Create an initial admin user if none exist."""
    from .utils.db import get_connection
    from .services.user_service import UserService
    from .config.settings import Settings
    from dotenv import load_dotenv
    import os

    dotenv_path = os.getenv("DOTENV_PATH", ".env")
    load_dotenv(dotenv_path, override=True)

    username = os.getenv("AUTH_USERNAME")
    if not username:
        click.echo("AUTH_USERNAME not set")
        return

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
        if existing:
            click.echo("Admin user already exists, skipping")
            return
        key = UserService(Settings(), current_app).generate_api_key(username)
        click.echo(f"Created admin user '{username}' with API key {key}")


