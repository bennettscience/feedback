from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates
from feedbook.models import Course

class TestUserModel(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()

        self.client = self.app.test_client()

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