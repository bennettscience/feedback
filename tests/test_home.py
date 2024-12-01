from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates, get_template_context


class TestAdminBlueprint(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()

        fixtures = ["users.json", "courses.json", "course_enrollments.json"]

        self.client = self.app.test_client()

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    # login the teacher
    def test_home_index(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/")
            context = get_template_context(templates, "home/index.html")

            self.assertEqual(type(context["icons"]), dict)
            self.assertEqual(type(context["courses"]), list)

    # allow students to login
    def test_home_as_student(self):
        self.login("student1@example.com")

        resp = self.client.get("/")

        self.assertEqual(resp.status_code, 200)

    # Redirect to the login page
    def test_not_logged_in(self):
        resp = self.client.get("/")

        self.assertEqual(resp.status_code, 302)
