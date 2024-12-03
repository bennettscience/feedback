from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates, get_template_context
from feedbook.models import Course, Standard, StandardAttempt


class TestLoader(TestBase):
    def setUp(self):
        self.app = self.create()

        ctx = self.app.app_context()
        ctx.push()

    def test_loader(self):
        loader = Loader(self.app, db, [])
        loader.load()

        self.assertTrue(loader)

    def test_load_single_table_single_file(self):
        from feedbook.models import User

        loader = Loader(self.app, db, ["users.json"])
        loader.load()

        users = User.query.all()

        self.assertEqual(len(users), 3)

    def test_load_mult_tables_mult_files(self):
        from feedbook.models import User, Course

        fixtures = ["courses.json", "users.json"]
        loader = Loader(self.app, db, fixtures)
        loader.load()

        users = User.query.all()
        courses = Course.query.all()

        self.assertEqual(len(users), 3)
        self.assertEqual(len(courses), 2)

    def test_load_mult_tables_single_file(self):
        from feedbook.models import User, Course

        loader = Loader(self.app, db, ["mult_tables_one_file.json"])
        loader.load()

        users = User.query.all()
        courses = Course.query.all()

        self.assertEqual(len(users), 3)
        self.assertEqual(len(courses), 2)

    def test_multiple_loads(self):
        from feedbook.models import User, Course, Assignment

        loader = Loader(self.app, db, ["users.json", "courses.json"])
        loader.load()

        users = User.query.all()
        courses = Course.query.all()

        self.assertEqual(len(users), 3)
        self.assertEqual(len(courses), 2)

        loader.insert(["assignments.json"])
        loader.load()

        assignments = Assignment.query.all()

        self.assertEqual(len(assignments), 1)
