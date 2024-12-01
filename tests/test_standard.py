from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates, get_template_context
from feedbook.models import Course, Standard, StandardAttempt


class TestStandardModel(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()
        fixtures = [
            "standards.json",
            "standard_assessments.json",
            "course_standards.json",
        ]

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    # Check the string representation
    def test_standard_repr(self):
        standard = db.session.get(Standard, 1)
        self.assertEqual(standard.__repr__(), "Standard 1")

    # return list of scores
    def test_get_scores(self):
        standard = db.session.get(Standard, 1)
        results = standard._Standard__get_scores(2)
        self.assertEqual(results, [1, 0])

    # check for a matching proficient override for a student
    def test_has_proficient_override(self):
        pass

    # calculate student proficiency
    def test_is_proficient(self):
        standard = db.session.get(Standard, 1)
        result = standard.is_proficient(2)
        self.assertFalse(result)

    # calculate the score for a given standard
    def test_current_score(self):
        standard = db.session.get(Standard, 1)
        result = standard.current_score(2)
        self.assertEqual(result, 0.5)

    # show the course average on proficiency
    def test_course_average(self):
        standard = db.session.get(Standard, 1)
        result = standard.course_average(1)
        self.assertEqual(result, 0.67)


class TestStandardBlueprint(TestBase):
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
            "standard_assessments.json",
            "course_standards.json",
            "users.json",
        ]

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    def test_get_all_standards(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/standards")
            names = [template["template_name"] for template in templates]

            template_context = get_template_context(templates, "standards/index.html")
            self.assertIn("standards/index.html", names)
            self.assertIs(type(template_context["standards"]), list)
            self.assertIs(type(template_context["standards"][0]), Standard)

    def test_create_standard(self):
        self.login("teacher@example.com")

        data = {
            "name": "New Standard",
            "description": "This is a new standard",
            "course_id": 1,
        }

        with captured_templates(self.app) as templates:
            resp = self.client.post("/standards", data=data)

            template_context = get_template_context(
                templates, "shared/forms/create-standard.html"
            )
            names = [template["template_name"] for template in templates]

            self.assertIn("shared/forms/create-standard.html", names)
            self.assertEqual(template_context["course"].name, "Course 1")
            self.assertIsInstance(template_context["items"], list)

    def test_get_single_standard(self):
        pass

    def test_update_standard_status(self):
        self.login("teacher@example.com")

        resp = self.client.put("/standards/1/status")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.headers["HX-Trigger"])

    def test_get_standard_result(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/standards/1/users/2/results/1")

            template_context = get_template_context(
                templates, "course/right-sidebar.html"
            )
            self.assertIsInstance(template_context["data"]["attempt"], StandardAttempt)
            self.assertEqual(template_context["data"]["attempt"].user_id, 2)
            self.assertEqual(template_context["data"]["attempt"].standard_id, 1)

    def test_add_assessment(self):
        self.login("teacher@example.com")

        data = {
            "user_id": 2,
            "score": 1,
            "assignment": 1,
            "comments": "This is a comment.",
        }

        with captured_templates(self.app) as templates:
            resp = self.client.post("/standards/1/attempts", data=data)

            template_context = get_template_context(
                templates, "standards/student-updated.html"
            )

            self.assertEqual(resp.status_code, 200)
            self.assertIs(type(template_context["record"]), StandardAttempt)
            self.assertEqual(template_context["record"].user_id, 2)

    def test_get_edit_attempt_form(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/standards/1/attempts/1")

            template_context = get_template_context(
                templates, "shared/forms/edit-standard-attempt.html"
            )

            self.assertEqual(resp.status_code, 200)
            self.assertIsInstance(template_context["attempt"], StandardAttempt)
            self.assertIsInstance(template_context["assignments"], list)
            self.assertEqual(template_context["attempt"].id, 1)
            self.assertEqual(len(template_context["standards"]), 3)

    def test_edit_attempt_from_standard(self):
        from feedbook.models import User

        data = {
            "assignment_id": 1,
            "score": 0,
            "standard_id": 1,
            "comments": "This is a modified attempt.",
        }

        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.put("/standards/1/attempts/1?source=standard", data=data)

            template_context = get_template_context(
                templates, "course/partials/student-entry.html"
            )

            self.assertEqual(resp.status_code, 200)
            self.assertIsInstance(template_context["student"], User)

    def test_edit_attempt_from_assignment(self):
        data = {
            "assignment_id": 1,
            "score": 0,
            "standard_id": 1,
            "comments": "This is a modified attempt.",
        }

        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.put(
                "/standards/1/attempts/1?source=assignment", data=data
            )

            template_context = get_template_context(
                templates, "assignments/single-attempt.html"
            )

            self.assertEqual(resp.status_code, 200)
            self.assertIsInstance(template_context["attempt"], StandardAttempt)

    def test_delete_attempt(self):
        import json

        self.login("teacher@example.com")

        resp = self.client.delete("/standards/1/attempts/1")
        self.assertTrue(resp.headers["HX-Trigger"])

        hx_header = json.loads(resp.headers["HX-Trigger"])
        self.assertEqual(hx_header["closeModal"], "")
        self.assertEqual(hx_header["showToast"], "Attempt deleted")

    def test_add_standard_to_course(self):
        self.login("teacher@example.com")

        data = {"standard_id": 3, "course_id": 1}

        with captured_templates(self.app) as templates:
            resp = self.client.post("/standards/align", data=data)

            self.assertEqual(resp.status_code, 200)

            template_context = get_template_context(
                templates, "standards/standard-card.html"
            )

            self.assertIs(type(template_context["item"]), Standard)
            self.assertEqual(template_context["course_id"], data["course_id"])
