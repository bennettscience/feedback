from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates, get_template_context
from feedbook.models import Assignment, Course, StandardAttempt


class TestUserModel(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()
        fixtures = [
            "assignments.json",
            "courses.json",
            "standards.json",
            "users.json",
            "assignment_standards.json",
            "standard_assessments.json",
            "course_enrollments.json",
        ]

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    def test_get_assessments(self):
        assignment = db.session.get(Assignment, 1)
        assessments = assignment.assessments.all()

        self.assertEqual(len(assessments), 3)
        self.assertIsInstance(assessments[0], StandardAttempt)
        self.assertEqual(assessments[0].score, 1)

    def test_get_average_score(self):
        assignment = db.session.get(Assignment, 1)
        average = assignment.average_all()

        self.assertEqual(average, 0.67)

    def test_average_single_course(self):
        from feedbook.models import Course

        assignment = db.session.get(Assignment, 1)
        course = db.session.get(Course, 1)

        course_average = assignment.course_average(course)

        self.assertEqual(course_average, 0.5)


class TestAssignmentBlueprint(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()

        self.client = self.app.test_client()

        fixtures = [
            "assignments.json",
            "courses.json",
            "standards.json",
            "course_assignments.json",
            "course_enrollments.json",
            "assignment_standards.json",
            "assignment_types.json",
            "standard_assessments.json",
            "users.json",
        ]

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    def test_get_all_assignments(self):
        resp = self.client.get("/assignments")

        self.assertEqual(resp.status_code, 200)

    def test_create_assignment(self):
        self.login("teacher@example.com")
        data = {
            "name": "New Assignment",
            "description": "A new assignment.",
            "type_id": 1,
            "courses": [1, 2],
            "current_course_id": 1,
        }

        with captured_templates(self.app) as templates:
            resp = self.client.post("/assignments", data=data)
            context = get_template_context(
                templates, "assignments/assignment-list.html"
            )

            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.headers["HX-Trigger"])
            self.assertIsInstance(context["assignments"], list)
            self.assertIsInstance(context["assignments"][0], Assignment)
            self.assertIsInstance(context["course"], Course)

    def test_get_create_assignment_form(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/assignments/create?current_course_id=1")
            self.assertEqual(resp.status_code, 200)

            template_context = get_template_context(
                templates, "course/right-sidebar.html"
            )

            self.assertEqual(
                template_context["partial"], "shared/forms/create-assignment.html"
            )

    def test_get_assignment(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/assignments/1")
            self.assertEqual(resp.status_code, 200)

            context = get_template_context(
                templates, "assignments/single-assignment.html"
            )

            self.assertIsInstance(context["assignment"], Assignment)
            self.assertEqual(context["assignment"].name, "Assignment 1")

    def test_get_assignment_edit_form(self):
        from feedbook.models import AssignmentType

        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/assignments/1/edit")

            self.assertEqual(resp.status_code, 200)

            context = get_template_context(
                templates, "shared/forms/edit-assignment.html"
            )

            self.assertIsInstance(context["assignment"], Assignment)
            self.assertEqual(context["assignment"].name, "Assignment 1")
            self.assertIsInstance(context["types"], list)
            self.assertIsInstance(context["types"][0], AssignmentType)

    def test_edit_assignment(self):
        self.login("teacher@example.com")

        data = {"name": "New name", "courses": [1, 2]}

        with captured_templates(self.app) as templates:
            resp = self.client.put("/assignments/1/edit", data=data)

            context = get_template_context(
                templates, "assignments/single-assignment.html"
            )

            received_courses = [
                course.id for course in context["assignment"].courses.all()
            ]

            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.headers["HX-Trigger"])
            self.assertEqual(context["assignment"].name, "New name")
            self.assertEqual(received_courses, [1, 2])

    def test_create_standard_alignment(self):
        self.login("teacher@example.com")

        data = {"standards": [2]}

        resp = self.client.post("/assignments/1/align", data=data)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.headers["HX-Trigger"])

    def test_remove_standard_alignment(self):
        self.login("teacher@example.com")
        resp = self.client.delete("/assignments/1/align/1")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.headers["HX-Trigger"])

    def test_get_assignment_attempt_edit_form(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/assignments/1/attempts/1")

            context = get_template_context(
                templates, "shared/forms/assignment-attempt-form.html"
            )

            self.assertEqual(resp.status_code, 200)
            self.assertIsInstance(context["attempt"], StandardAttempt)
            self.assertEqual(context["attempt"].comments, "This is an example comment.")

    def test_get_assignment_attempt_result(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/assignments/1/results/1")

            context = get_template_context(templates, "assignments/single-attempt.html")

            self.assertEqual(resp.status_code, 200)
            self.assertIsInstance(context["attempt"], StandardAttempt)
            self.assertEqual(context["attempt"].comments, "This is an example comment.")
