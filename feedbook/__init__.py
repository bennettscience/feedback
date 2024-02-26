from flask import Flask

from config import Config
from feedbook.extensions import db, htmx, login_manager, migrate, partials
from feedbook.blueprints import admin, auth, home, course, standard, user
from feedbook.errors import forbidden, unauthorized

def create_app(config=Config):
	app = Flask(__name__, static_url_path='/static')
	app.config.from_object(config)

	from feedbook import models

	db.init_app(app)
	htmx.init_app(app)
	migrate.init_app(app, db, render_as_batch=True)
	login_manager.init_app(app)

	login_manager.login_view = "auth.get_login"

	partials.register_extensions(app)

	app.register_blueprint(admin.bp)
	app.register_blueprint(auth.bp)
	app.register_blueprint(home.bp)
	app.register_blueprint(course.bp)
	app.register_blueprint(standard.bp)
	app.register_blueprint(user.bp)

	app.register_error_handler(401, unauthorized)
	app.register_error_handler(403, forbidden)
	
	return app
