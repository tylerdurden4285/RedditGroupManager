import secrets
from pathlib import Path
from dotenv import load_dotenv

from .settings import Settings


load_dotenv()

settings = Settings()


class Config:
    """Base configuration loaded from :class:`Settings`."""

    SECRET_KEY = settings.flask_secret_key
    WTF_CSRF_ENABLED = True
    DATABASE_PATH = settings.database_path
    SQLALCHEMY_DATABASE_URI = settings.database_url or f"sqlite:///{DATABASE_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    
    REDDIT_CLIENT_ID = settings.reddit_client_id
    REDDIT_CLIENT_SECRET = settings.reddit_client_secret
    REDDIT_USER_AGENT = settings.reddit_user_agent
    REDDIT_USERNAME = settings.reddit_username
    REDDIT_PASSWORD = settings.reddit_password

    


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    WTF_CSRF_ENABLED = False  
    

class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    DATABASE_PATH = str(Path(__file__).resolve().parents[2] / 'instance' / 'test.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH}"


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    SECRET_KEY = settings.flask_secret_key
    
    
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True



config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}
