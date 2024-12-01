import json
import unittest

from contextlib import contextmanager
from flask import template_rendered
from flask_login.utils import login_user

from feedbook import create_app
from feedbook.extensions import db
from feedbook.models import User
from feedbook.schemas import UserSchema
from config import TestConfig


class TestBase(unittest.TestCase):
    def create(self):
        self.app = create_app(TestConfig)

        # Build the database structure in the application context
        with self.app.app_context():
            # db.init_app(self.app)
            # db.create_all()

            @self.app.route("/auto_login/<email>")
            def auto_login(email):
                user = User.query.filter(User.email == email).first()
                login_user(user, remember=True)
                return UserSchema().dump(user)

        return self.app

    def login(self, email):
        return self.client.get(f"/auto_login/{email}")


@contextmanager
def captured_templates(app):
    # Capture all request data and return a dictionary to the test runner
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append({"template_name": template.name, "context": context})

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


# Look for an object in the templates based on a template title
def get_template_context(values: list, template_name: str) -> dict:
    try:
        result = next(
            template["context"]
            for template in values
            if template["template_name"] == template_name
        )
    except StopIteration:
        result = "{} not found".format(template_name)

    return result
