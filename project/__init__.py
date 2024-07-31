import os
import logging
from logging.config import dictConfig

from flask import Flask
from flask_celeryext import FlaskCeleryExt  # new
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from project.celery_utils import make_celery  # new
from project.config import config


# instantiate the extensions
db = SQLAlchemy()
migrate = Migrate()
ext_celery = FlaskCeleryExt(create_celery_app=make_celery)  # new

def _configure_logger(config):
    """Configure application logging."""
    return {
        'version': 1,
        'formatters': {'default': {
            'format': '[%(asctime)s] %(levelname)s in func %(module)s %(funcName)s line %(lineno)s %(threadName)s: %(message)s',
        }},
        'disable_existing_loggers': False,
        'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },

        'file.handler': {
            'class': 'logging.FileHandler',
            'filename': config.LOG_PATH,
            'level': 'DEBUG',
            'formatter': 'default'
            }
           },

        'root': {
            'level': config.LOG_LEVEL,
            'filename': config.LOG_PATH,
            'handlers': ['wsgi', 'file.handler']
        }
    }


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "development")
    logging.config.dictConfig(_configure_logger(config[config_name]))

    # instantiate the app
    app = Flask(__name__)

    # set config
    app.config.from_object(config[config_name])
    from .cache import cache
    cache.init_app(app, config=app.config)
    # set up extensions
    db.init_app(app)
    migrate.init_app(app, db)
    ext_celery.init_app(app)  # new

    # register blueprints
    from project.commands import commands_blueprint
    app.register_blueprint(commands_blueprint)

    # shell context for flask cli
    @app.shell_context_processor
    def ctx():
        return {"app": app, "db": db}

    return app