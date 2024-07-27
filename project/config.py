import os
from pathlib import Path


class BaseConfig:
    """Base configuration"""
    BASE_DIR = Path(__file__).parent.parent

    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR}/db.sqlite3")
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")              # new
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")      # new
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    LOG_PATH = os.environ.get('LOG_PATH', 'app.log')
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
    CACHE_REDIS_HOST = os.environ.get('CACHE_REDIS_HOST')
    CACHE_REDIS_PORT = os.environ.get('CACHE_REDIS_PORT')
    CACHE_REDIS_DB = os.environ.get('CACHE_REDIS_DB')
    CACHE_REDIS_URL = os.environ.get('CACHE_REDIS_URL')
    CACHE_DEFAULT_TIMEOUT = os.environ.get('CACHE_DEFAULT_TIMEOUT')


class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}