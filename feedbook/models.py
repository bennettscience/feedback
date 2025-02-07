from collections import Counter
from statistics import mean

from flask_login import UserMixin
from sqlalchemy.orm import backref
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

from feedbook.extensions import db, login_manager


@login_manager.user_loader
def load_user(id):  # pragma: no cover
    return db.session.get(User, int(id))


class AssignmentType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    assignmenttype_id = db.Column(db.ForeignKey("assignment_type.id"))
    created_on = db.Column(db.DateTime(timezone=True), default=func.now())

    type = db.relationship("AssignmentType", backref="type")

    assessments = db.relationship(
        "StandardAttempt",
        backref=backref("assessed_on"),
        lazy="dynamic",
        passive_deletes=True,
    )

    alignments = db.relationship(
        "Standard",
        secondary="assignment_standards",
        backref=backref("assignments", lazy="dynamic"),
        lazy="dynamic",
    )

    # Get the average score for an assignment
    # This returns the average for all classes regardless of when it happened. This will be helpful for looking at assignments across all classes and lay a foundation for an eventual `assignment_type` key.
    #
    # Note that this is a straight average, not the weighted average used to calculate student performance.
    def average_all(self):
        scores = self.assessments.all()
        return round(mean([item.score for item in scores]), 2)

    # Get the average score for students in a course
    # Use the StandardAttempt table as the leftmost join to filter down against the other conditions. Since the attempts do not matter which course they're in, just the user, you need to filter against the user_courses table to get only the desired course.
    # Only return values for students with the given course.id AND attempts for the assignment with the matching ID.
    def course_average(self, course):
        course_attempts = (
            StandardAttempt.query.join(User)
            .join(user_courses)
            .filter(
                (user_courses.c.course_id == course.id)
                & (StandardAttempt.assignment_id == self.id)
            )
        ).all()
        if course_attempts:
            return round(mean([attempt.score for attempt in course_attempts]), 2)
        else:
            return None

    # Align the assignment to learning standards. Multiple can be added and assessed at the same time.
    def add_standard(self, standard):
        if not self._has_standard(standard):
            self.alignments.append(standard)
            db.session.commit()
        return self

    def _has_standard(self, standard):
        return (
            self.alignments.filter(
                assignment_standards.c.standard_id == standard.id
            ).count()
            > 0
        )

    def update(self, data):
        for key, value in data.items():
            if key == "courses":
                continue
            else:
                setattr(self, key, value)
        db.session.commit()


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    active = db.Column(db.Boolean, default=True)

    standards = db.relationship(
        "Standard",
        secondary="course_standards",
        backref=backref("standards", lazy="dynamic"),
        lazy="dynamic",
    )

    assignments = db.relationship(
        "Assignment",
        secondary="course_assignments",
        backref=backref("courses", lazy="dynamic"),
        lazy="dynamic",
    )

    def add_assignment(self, assignment):
        if not self._has_assignment(assignment):
            self.assignments.append(assignment)
        return self

    def _has_assignment(self, assignment):
        return (
            self.assignments.filter(
                course_assignments.c.assignment_id == assignment.id
            ).count()
            > 0
        )

    # safely align a standard to a course
    def align(self, standard):
        if not self._is_aligned(standard):
            self.standards.append(standard)
        return self

    def _is_aligned(self, standard):
        return (
            self.standards.filter(course_standards.c.standard_id == standard.id).count()
            > 0
        )


class Standard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(1000))
    active = db.Column(db.Boolean, default=True)

    attempts = db.relationship(
        "StandardAttempt",
        backref=backref("standard", single_parent=True),
        lazy="dynamic",
        passive_deletes=True,
    )

    def __repr__(self):
        return self.name

    def _get_scores(self, user_id):
        scores = (
            self.attempts.filter(StandardAttempt.user_id == user_id)
            .order_by("occurred")
            .all()
        )
        return [item.score for item in scores]

    def _has_proficient_override(self, user) -> bool:
        """
        Check for an override on proficiency from a specific user. Returns True and overrides the is_proficient calculation for a specific user.
        """
        query = self.students.filter(user_standards.c.user_id == user.id).count()
        if query > 0:
            return True
        return False

    def _has_assessment_proficient(self, user) -> bool:
        """
        Check for a passed assessment on the current standard in the student's results.
        """

        # To work around show progress _up until_ an assessment, check for
        # an assessment assignment in the database. If there is one, then check
        # for student scores and return as normal.
        # If no assessment is in the database, return true to move on
        # checking student scores.
        # This is NOT a great solution to the problem of displaying progress
        # on skills before a test, but it's the best I can come up with for now.
        # has_assessment = self.assignments.filter(
        #     Assignment.assignmenttype_id == 2
        # ).all()

        query = (
            self.attempts.join(Assignment)
            .filter(
                Assignment.assignmenttype_id == 2,
                StandardAttempt.score == 1,
                StandardAttempt.user_id == user.id,
            )
            .order_by("occurred")
            .all()
        )

        # If ANY results come back, then return true
        if len(query) > 0:
            return True
        else:
            return False

    def add_proficient_override(self, user):
        if not self._has_proficient_override(user):
            self.students.append(user)
            db.session.commit()
        else:
            return (
                "{} already has an override for {}".format(
                    f"{user.first_name} {user.last_name}", self.name
                ),
                409,
            )

        return (
            "Added proficient record for {}".format(
                f"{user.first_name} {user.last_name}"
            ),
            200,
        )

    def is_proficient(self, user) -> bool:
        """
        Determine if a user is showing mastery on a standard.

        Perform several checks:
        - If an assessment is present:
            - If the assessment attempt == 1, then True
            - If an override is present, then True
        - else no assessment is present:
            - If an override is present, then True
            - More 1's than 0's in the assessment objects AND a true assessment, otherwise false
        """
        assessment_present = self.assignments.filter(
            Assignment.assignmenttype_id == 2
        ).all()

        # Get a count of 1's and 0's for the user
        scores = self._get_scores(user.id)
        counts = Counter(scores)

        # Build a dict for the user with the different conditions.
        result = {
            "has_assessment": self._has_assessment_proficient(user),
            "has_override": self._has_proficient_override(user),
            "scores": counts[1] > counts[0],
        }

        # Still can't decide how I feel about this check. What point is
        # there for multiple proficient attempts if all that matters is the
        # assessment object? And if the assessment can be trumped by multiple
        # attempts, why care about the test at all?
        # Is having both the key? How to reconcile students who don't _need_
        # to do all the practice?
        if assessment_present:
            if result["has_assessment"] or result["has_override"]:
                return True
        else:
            if result["scores"]:
                return True
            else:
                return False

    def current_score(self, user):
        """Average the last attemp with the highest attempt.
        Make sure to score by submission date, not assessed date!
        Example 1:
        scores = [1, 4, 3, 2]
        Average = 3

        Example 2:
        scores = [1, 2, 3, 4]
        Average = 4

        Args:
            user_id (int): User ID

        Returns:
            float: average
        """
        scores = self._get_scores(user.id)
        if len(scores) == 0:
            return None
        else:
            return (max(scores) + scores[-1]) / 2

    # Get the average score for students in a course
    # Use the StandardAttempt table as the leftmost join to filter down against the other conditions. Since the attempts do not matter which course they're in, just the user, you need to filter against the user_courses table to get only the desired course.
    # Only return values for students with the given course.id AND attempts for the assignment with the matching ID.
    def course_average(self, course_id):
        course_attempts = (
            StandardAttempt.query.join(User, StandardAttempt.user_id == User.id)
            .join(user_courses)
            .filter(
                (user_courses.c.course_id == course_id)
                & (StandardAttempt.standard_id == self.id)
            )
            .all()
        )
        if course_attempts:
            return round(mean([attempt.score for attempt in course_attempts]), 2)
        else:
            return None


class StandardAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.ForeignKey("user.id", onupdate="CASCADE", ondelete="CASCADE")
    )
    standard_id = db.Column(
        db.ForeignKey("standard.id", onupdate="CASCADE", ondelete="CASCADE")
    )
    score = db.Column(db.Integer)
    occurred = db.Column(db.DateTime(timezone=True), default=func.now())
    assignment = db.Column(db.String(32))
    assignment_id = db.Column(db.ForeignKey("assignment.id"))
    comments = db.Column(db.String(1000))

    def update(self, data):
        for key, value in data.items():
            setattr(self, key, value)
        db.session.commit()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(32), nullable=False)
    first_name = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(64), nullable=False, unique=True)
    password_hash = db.Column(db.String(128))
    usertype_id = db.Column(db.Integer, db.ForeignKey("user_type.id"))
    active = db.Column(db.Boolean, default=True)

    enrollments = db.relationship(
        "Course",
        secondary="user_courses",
        backref=backref("enrollments", lazy="dynamic"),
        lazy="dynamic",
    )

    assessments = db.relationship(
        "StandardAttempt",
        backref=backref("user", single_parent=True),
        lazy="dynamic",
        passive_deletes=True,
    )

    proficiencies = db.relationship(
        "Standard",
        secondary="user_standards",
        backref=backref("students", lazy="dynamic"),
        lazy="dynamic",
    )

    def enroll(self, course):
        if not self.is_enrolled(course):
            self.enrollments.append(course)
            db.session.commit()
        else:
            raise Exception(
                "{} is already enrolled in {}".format(self.first_name, course.name)
            )

    def is_enrolled(self, course):
        return (
            self.enrollments.filter(user_courses.c.course_id == course.id).count() > 0
        )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        db.session.commit()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class UserType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))


assignment_standards = db.Table(
    "assignment_standards",
    db.Column("id", db.Integer, primary_key=True),
    db.Column(
        "assignment_id",
        db.Integer,
        db.ForeignKey("assignment.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
    db.Column(
        "standard_id",
        db.Integer,
        db.ForeignKey("standard.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
)

course_standards = db.Table(
    "course_standards",
    db.Column("id", db.Integer, primary_key=True),
    db.Column(
        "course_id",
        db.Integer,
        db.ForeignKey("course.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
    db.Column(
        "standard_id",
        db.Integer,
        db.ForeignKey("standard.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
)

course_assignments = db.Table(
    "course_assignments",
    db.Column("id", db.Integer, primary_key=True),
    db.Column(
        "course_id",
        db.Integer,
        db.ForeignKey("course.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
    db.Column(
        "assignment_id",
        db.Integer,
        db.ForeignKey("assignment.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
)

user_courses = db.Table(
    "user_courses",
    db.Column("id", db.Integer, primary_key=True),
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("user.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
    db.Column(
        "course_id",
        db.Integer,
        db.ForeignKey("course.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
)

user_standards = db.Table(
    "user_standards",
    db.Column("id", db.Integer, primary_key=True),
    db.Column(
        "user_id",
        db.Integer,
        db.ForeignKey("user.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
    db.Column(
        "standard_id",
        db.Integer,
        db.ForeignKey("standard.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
)
