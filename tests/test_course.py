from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates, get_template_context
from feedbook.models import Course


class TestCourseModel(TestBase):
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
            "assignments.json",
            "assignment_standards.json",
            "courses.json",
            "course_assignments.json",
            "course_enrollments.json",
            "course_standards.json",
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

    def test_get_create_course_form(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/create")
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("course/right-sidebar.html", names)

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
            self.assertIn("course/teacher-index-htmx.html", names)

    # anonymous users are redirected to login
    def test_get_single_course_as_anonymous(self):
        resp = self.client.get("/courses/1")
        self.assertEqual(resp.status_code, 302)

    # logged in users not enrolled in the course are not allowed
    def test_get_single_course_not_enrolled(self):
        self.login("teacher@example.com")

        resp = self.client.get("/courses/2")
        self.assertEqual(resp.status_code, 401)

    # Get the student course view
    def test_get_single_course_enrolled_as_student(self):
        self.login("student1@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1")
            self.assertEqual(resp.status_code, 200)
            names = [template["template_name"] for template in templates]
            self.assertIn("course/student_index.html", names)

    def test_hx_request_get_single_course_enrolled_as_student(self):
        self.login("student1@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1", headers={"HX-Request": True})
            self.assertEqual(resp.status_code, 200)
            names = [template["template_name"] for template in templates]
            self.assertIn("course/student_index.html", names)

    # Get the teacher course view
    def test_get_single_course_enrolled_as_teacher(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1")

            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("course/teacher-index-htmx.html", names)
            for template in templates:
                if template["template_name"] == "course/teacher-index-htmx.html":
                    context = get_template_context(
                        templates, "course/teacher-index-htmx.html"
                    )
                    self.assertEqual(len(context["enrollments"]), 1)
                    self.assertEqual(
                        context["results"]["standard_1"]["not_proficient"], 1
                    )

    def test_get_assignment_from_course(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1/assignments/1")
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("assignments/assignment_detail.html", names)

    def test_get_create_standard_form(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1/standards/create")
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("standards/standard-sidebar.html", names)
            self.assertIn("shared/forms/create-standard.html", names)

    def test_get_course_standard_scores(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1/standards/1/results")
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("course/partials/standard_score_table.html", names)

    def test_get_student_results(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1/users/2/results/1")
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("standards/student-standard-scores.html", names)

    def test_remove_standard_from_course(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.delete("/courses/1/standards/2")
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("course/teacher-index-htmx.html", names)

    def test_remove_standard_as_student(self):
        self.login("student1@example.com")

        resp = self.client.delete("/courses/1/standards/1")

        self.assertEqual(resp.status_code, 403)

    def test_get_assessment_form(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1/standards/1/assess")
            self.assertEqual(resp.status_code, 200)

            names = [template["template_name"] for template in templates]
            self.assertIn("standards/student-assessment-form.html", names)

    def test_get_single_assignment(self):
        from feedbook.models import Assignment

        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1/assignments/1")

            self.assertEqual(resp.status_code, 200)

            context = get_template_context(
                templates, "assignments/assignment_detail.html"
            )

            self.assertIsInstance(context["assignment"], Assignment)
            self.assertEqual(context["course_id"], 1)

    def test_get_alignment_form(self):
        from feedbook.models import Assignment

        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1/assignments/1/align")

            self.assertEqual(resp.status_code, 200)

            context = get_template_context(templates, "course/right-sidebar.html")

            self.assertEqual(context["partial"], "shared/forms/create-alignment.html")
            self.assertIsInstance(context["data"]["course"], Course)
            self.assertIsInstance(context["data"]["assignment"], Assignment)
            self.assertEqual(context["data"]["course"].id, 1)

    def test_get_user_from_course(self):
        from feedbook.models import User

        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/courses/1/users?user_id=2")

            self.assertEqual(resp.status_code, 200)

            context = get_template_context(templates, "user/user-index.html")

            self.assertIsInstance(context["user"], User)
            self.assertEqual(context["user"].id, 2)
            self.assertIsInstance(context["course"], Course)
            self.assertEqual(context["course"].id, 1)
