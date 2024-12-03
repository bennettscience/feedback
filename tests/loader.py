import json
import os
from sqlalchemy import Table


class Loader(object):
    """
    Reusable class for loading fixture data into test databases.

    :params:
    app - Flask application. Context must be pushed to the test runner before initializing
    db - SQLAlchemy database session
    fixtures - list of JSON files in the `fixtures/` directory to load.

    Initialize with an in-context application and database engine.
    """

    def __init__(self, app, db, fixtures: list):
        self.app = app
        self.connection = db.engine.connect()
        self.fixtures = fixtures
        self.metadata = db.metadata

        # Create the database in memory
        # every table in models.py is created so any JSON loaded
        # in the load function should have a place to go.
        db.create_all()

    def insert(self, fixtures: list):
        self.fixtures = fixtures

    # Load each fixure in the instance
    def load(self):
        """
        Load all fixtures into the instance of Loader. When loaded, add it to the test database immediately.
        """
        for filename in self.fixtures:
            filepath = os.path.join(self.app.config["FIXTURES_DIR"], filename)
            with open(filepath) as file_in:
                self.data = json.load(file_in)
                self.load_from_file()

            # Reset fixtures back to None
            self.fixtures = None

    def load_from_file(self):
        for entry in self.data:
            table = Table(entry["table"], self.metadata)
            self.connection.execute(table.insert(), entry["records"])
        return
