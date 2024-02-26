from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates
from feedbook.models import User, UserType
from feedbook.wrappers import restricted

class TestWrappers(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()

        self.client = self.app.test_client()

        fixtures = ["usertype.json", "users.json"]

        # Now that we're in context, we can load the database.
        loader = Loader(self.app, db, fixtures)
        loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    def test_restricted_wrapper(self):
        user = db.get_or_404(User, 1)
        user2 = db.get_or_404(User, 2)
        teacher = db.get_or_404(UserType, 1)
        student = db.get_or_404(UserType, 2)

        @restricted
        def test_to_wrap():
            assert user is Teacher

        @restricted
        def test2_to_wrap():
            assert user2 is Student
