from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates, get_template_context
from feedbook.models import User


class TestAuthBlueprint(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()

        self.client = self.app.test_client()

        fixtures = ["users.json", "usertype.json"]

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    def test_get_login_form(self):
        with captured_templates(self.app) as templates:
            resp = self.client.get("/login")

            self.assertEqual(resp.status_code, 200)
            self.assertEqual(templates[0]["template_name"], "shared/forms/login.html")

    def test_login_authenticated_user(self):
        self.login("teacher@example.com")

        resp = self.client.get("/login")

        self.assertEqual(resp.status_code, 302)

    def test_login_route(self):
        # Set up a new user from scratch
        new_user = User(
            email="test@example.com", last_name="User", first_name="Test", usertype_id=2
        )
        db.session.add(new_user)
        new_user.set_password("1234")
        db.session.commit()

        # Buld the form object to log the new user in
        data = {"email": "test@example.com", "password": "1234", "remember_me": True}

        resp = self.client.post("/login", data=data)

        self.assertEqual(resp.status_code, 200)

    def test_bad_user_login(self):
        # Set up a new user from scratch
        new_user = User(
            email="test@example.com", last_name="User", first_name="Test", usertype_id=2
        )
        db.session.add(new_user)
        new_user.set_password("1234")
        db.session.commit()

        data = {"email": "test@example.com", "password": "1233", "remember_me": True}

        with captured_templates(self.app) as templates:
            resp = self.client.post("/login", data=data)

            self.assertEqual(resp.status_code, 401)
            self.assertTrue(resp.headers["HX-Trigger"])

    def test_logout(self):
        self.login("teacher@example.com")

        resp = self.client.get("/logout")
        self.assertEqual(resp.status_code, 302)

    def test_registration_placeholder(self):
        resp = self.client.get("/register")

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(str(resp.data), "b'Registrations are not open at this time.'")

    def test_register_post(self):
        resp = self.client.post("/register", data={})

        self.assertEqual(resp.status_code, 403)
