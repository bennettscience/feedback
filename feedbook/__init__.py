from flask import Flask
from feedbook.extensions import db, login_manager, migrate, partials
from feedbook.blueprints import home, course, standard

def create_app(config):
	app = Flask(__name__, static_url_path='/static')
	app.config.from_object(config)

	from feedbook import models

	db.init_app(app)
	migrate.init_app(app, db, render_as_batch=True)
	login_manager.init_app(app)

	partials.register_extensions(app)
	
	app.register_blueprint(home.bp)
	app.register_blueprint(course.bp)
	app.register_blueprint(standard.bp)

	return app
