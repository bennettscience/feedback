from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates, get_template_context
from feedbook.models import Course


class TestUserModel(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()
        fixtures = ["courses.json", "standards.json"]

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    def test_course_is_active(self):
        c = db.session.get(Course, 1)
        self.assertTrue(c.active)

    def test_align_standard(self):
        from feedbook.models import Standard

        c = db.session.get(Course, 1)
        s = db.session.get(Standard, 1)

        self.assertEqual(len(c.standards.all()), 0)

        c.align(s)
        self.assertEqual(len(c.standards.all()), 1)


class TestCourseBlueprint(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()

        self.client = self.app.test_client()

        fixtures = [
            "courses.json",
            "course_enrollments.json",
            "standards.json",
            "usertype.json",
            "users.json",
        ]

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    # This may be misleading - get all courses means
    # get all courses that user is enrolled in.
    def test_get_all_courses_as_student(self):
        self.login("student1@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses")
            self.assertEqual(resp.status_code, 200)
            names = [template["template_name"] for template in templates]
            self.assertIn("course/partials/course_card.html", names)

    def test_get_create_course_form(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/create")
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("shared/partials/right-sidebar.html", names)

    def test_post_course(self):
        self.login("teacher@example.com")

        course = {"name": "New Course"}

        with captured_templates(self.app) as templates:
            resp = self.client.post("/courses", data=course)
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("course/partials/course_card.html", names)

            # Check for the new course in the returned template
            resp_context = get_template_context(
                templates, "course/partials/course_card.html"
            )
            self.assertEqual(course["name"], "New Course")

    def test_get_roster_form(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1/upload")
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("course/partials/roster-upload.html", names)

    def test_post_roster_upload(self):
        # Simulate a file upload with BytesIO
        from io import BytesIO

        self.login("teacher@example.com")

        # Create a file object to upload to the route
        file_data = b"last_name,first_name,email,password\nExample,Student3,student3@example.com,abc123"

        with captured_templates(self.app) as templates:
            resp = self.client.post(
                "/courses/1/upload",
                data={"file": (BytesIO(file_data), "test.csv")},
            )
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("course/teacher_index_htmx.html", names)

    # anonymous users are redirected to login
    def test_get_single_course_as_anonymous(self):
        resp = self.client.get("/courses/1")
        self.assertEqual(resp.status_code, 302)

    # logged in users not enrolled in the course are not allowed
    def test_get_single_course_not_enrolled(self):
        self.login("teacher@example.com")

        resp = self.client.get("/courses/2")
        self.assertEqual(resp.status_code, 401)

    def test_get_single_course_enrolled_as_student(self):
        self.login("student1@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1")

            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("course/student_index.html", names)

    def test_get_single_course_enrolled_as_teacher(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1")

            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("course/teacher_index.html", names)
            for template in templates:
                if template["template_name"] == "course/teacher_index.html":
                    context = template["context"]
                    self.assertEqual(len(context["students"]), 1)

    def test_get_course_users(self):
        pass

    def test_get_create_standard_form(self):
        pass

    def test_get_course_standard_scores(self):
        pass

    def test_get_student_results(self):
        pass

    def test_delete_student_from_course(self):
        pass

    def test_get_assessment_form(self):
        pass
