# SBG Feedback

I don't have a clever name for this.

## What is it?

This is a Flask application that is designed to track student progress against learning targets (standards) through feedback. Students are able to log in and see their progress on each standard on their own dashboard.

## How does it work?

To get started, teachers:

- Set up classes and enroll students
- Create standards
- Create assignments

Each assignment can be linked to single or multiple standards, each of which can have specific scores and feedback. Standards can also have arbitrary feedback items added, so you're able to include verbal discussions, class observations, or other informal assessment points for evaluating student proficiency.

Each enrollment has its own dashboard which breaks down an individual's progress. Teachers can see each assessment point for a given standard over time, the student's proficiency level, and comments left.

Students are given an individual progress dashboard with each standard's progress clearly shown. Clicking on a single standard will show every attempt, whether or not they showed proficiency on that attempt, and any feedback the teacher left on the assignment.

Student overall proficiency is evaluated based on how many proficient attempts (did they demonstrate the standard?) there are in relation to non-proficient attempts. If they are proficient more than they aren't, they have demonstrated overall proficiency on the standard.

## Improvements

Check the Issues tab for upcoming improvements or other enhancements.

## Running Your Own

This is designed to run with Linux, nginx, SQLite, and Python. Since students don't write to the database, there is no need for a concurrent write system in the database. SQLite works exceptionally well for a single user instance.

Clone the repo and set up your private `config.py` file following the sample included. 

You'll need a WSGI interface, I suggest using `gunicorn`. A sample configuration is also included.

## Contributing

Contributions are welcome. Clone the repo, make edits and add appropraite tests. Open a PR with a detailed summary and what issue it's solving after all tests are passing.

## Questions?

Throw something into the discussion.
