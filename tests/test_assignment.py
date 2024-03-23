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
            "courses.json",
            "course_enrollments.json",
            "standards.json",
            "standard_assessments.json",
            "users.json",
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
        self.assertEqual(assessments[0].score, 3)

    def get_average_score(self):
        assignment = db.session.get(Assignment, 1)
        average = assignment.average_all()

        self.assertEqual(average, 2)

    def test_average_single_course(self):
        from feedbook.models import Course

        assignment = db.session.get(Assignment, 1)
        course = db.session.get(Course, 1)

        course_average = assignment.course_average(course)

        self.assertEqual(course_average, 1.5)
