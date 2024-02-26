from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates
from feedbook.models import User

class TestUserModel(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()

        self.client = self.app.test_client()

        fixtures = ["usertype.json", "users.json"]

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    def test_user_is_enrolled(self):
        from feedbook.models import Course
        course = Course(name="Course 1", active=True)
        db.session.add(course)

        user = db.get_or_404(User, 1)
        self.assertFalse(user.is_enrolled(course))

    def test_enroll_user(self):
        from feedbook.models import Course
        course = Course(name="Course 1", active=True)

        user = db.get_or_404(User, 1)
        user.enroll(course)
        self.assertTrue(user.is_enrolled(course))
        self.assertEqual(len(user.enrollments.all()), 1)

    def test_user_password(self):
        user = db.get_or_404(User, 1)
        user.set_password("abc123")
        self.assertTrue(user.check_password("abc123"))
        self.assertFalse(user.check_password("abc122"))


class TestUserBlueprint(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()

        self.client = self.app.test_client()

        fixtures = [
            "courses.json", 
            "standards.json", 
            "usertype.json", 
            "users.json"
        ]

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    # Get all users registerd on the site. This will eventually
    # be behind an admin flag. Right now, requires the user to 
    # be a Teacher.
    def test_get_all_users(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/users")

            self.assertEqual(resp.status_code, 200)            

            names = [template["template_name"] for template in templates]
            self.assertIn("user/index.html", names)
            for template in templates:
                if template["template_name"] == "user/index.html":
                    context = template["context"]
                    self.assertEqual(len(context["users"]), 3)

    # Get the assessment form for a student as a teacher.
    def get_user_assessment_form(self):
        self.login("teacher@example.com")

        with captured_templates as templates:
            # This route requires a query string to get the right course ID
            resp = self.client.get("/users/2/assess?course_id=1")

            self.assertEqual(resp.status_code, 200)
            names = [template["template_name"] for template in templates]
            self.assertIn("user/assess-form.html", names)
            for template in templates:
                if template["template_name"] == "user/assess-form.html":
                    context = template["context"]
                    self.assertEqual(len(context["standards"]), 1)
                    self.assertEqual(context["user_id"], 2)
