import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, has_request_context, request

from config import Config
from feedbook.extensions import cache, db, htmx, login_manager, migrate, partials
from feedbook.blueprints import admin, assignment, auth, home, course, standard, user
from feedbook.errors import forbidden, unauthorized


class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
        else:
            record.url = None
            record.remote_addr = None

        return super().format(record)


def create_app(config=Config):
    app = Flask(__name__, static_url_path="/static")
    app.config.from_object(config)
    if not app.debug and not app.testing:
        if not os.path.exists("logs"):
            os.mkdir("logs")

        formatter = RequestFormatter(
            "[%(asctime)s] %(remote_addr)s requested %(url)s\n"
            "%(levelname)s in %(module)s: %(message)s"
        )
        file_handler = RotatingFileHandler(
            "logs/feedback.log", maxBytes=10240, backupCount=10
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("Starting application")

    from feedbook import models

    cache.init_app(app, {"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300})
    db.init_app(app)
    htmx.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)

    login_manager.login_view = "auth.get_login"

    partials.register_extensions(app)

    app.register_blueprint(admin.bp)
    app.register_blueprint(assignment.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(home.bp)
    app.register_blueprint(course.bp)
    app.register_blueprint(standard.bp)
    app.register_blueprint(user.bp)

    app.register_error_handler(401, unauthorized)
    app.register_error_handler(403, forbidden)

    return app
