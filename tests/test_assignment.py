from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates, get_template_context
from feedbook.models import Assignment, StandardAttempt


class TestUserModel(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()
        fixtures = [
            "assignments.json",
            "standards.json",
            "standard_assessments.json",
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

        self.assertEqual(len(assessments), 1)
        self.assertIsInstance(assessments[0], StandardAttempt)
        self.assertEqual(assessments[0].score, 3)
