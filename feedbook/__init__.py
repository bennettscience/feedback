from flask import Flask
from feedbook.extensions import db, login_manager, migrate

def create_app(config):
	app = Flask(__name__, static_url_path='/static')
	app.config.from_object(config)

	from feedbook import models

	db.init_app(app)
	migrate.init_app(app, db, render_as_batch=True)
	login_manager.init_app(app)

	return app
