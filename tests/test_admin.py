from feedbook.extensions import db

from tests.loader import Loader
from tests.utils import TestBase, captured_templates, get_template_context


class TestAdminBlueprint(TestBase):
    def setUp(self):
        self.app = self.create()

        # Set up the application context manually to build the database
        # and test client for requests.
        ctx = self.app.app_context()
        ctx.push()

        fixtures = ["users.json"]

        self.client = self.app.test_client()

        # Now that we're in context, we can load the database.
        self.loader = Loader(self.app, db, fixtures)
        self.loader.load()

    def tearDown(self):
        db.drop_all()
        db.session.close()

    def test_admin_index(self):
        self.login("teacher@example.com")

        with captured_templates(self.app) as templates:
            resp = self.client.get("/admin")

            context = get_template_context(templates, "admin/index.html")

            self.assertEqual(type(context["icons"]), dict)
