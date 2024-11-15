from collections import Counter
from statistics import mean

from flask_login import UserMixin
from sqlalchemy.orm import backref
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

from feedbook.extensions import db, login_manager


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


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
        return mean([item.score for item in scores])

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

    def __get_scores(self, user_id):
        scores = (
            self.attempts.filter(StandardAttempt.user_id == user_id)
            .order_by("occurred")
            .all()
        )
        return [item.score for item in scores]

    def is_proficient(self, user_id) -> bool:
        """
        Aug 1 2024
        Determine if a user is showing mastery on a standard. They must have more 1's than 0's in the book to be proficient. Return the unicode checkmark or x depending on their current progress.
        """
        scores = self.__get_scores(user_id)
        counts = Counter(scores)
        # Compare 0's to 1's. If 1's are greater, the user is proficient.
        return counts[1] > counts[0]

    def current_score(self, user_id):
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
        scores = self.__get_scores(user_id)
        if len(scores) == 0:
            return None
        else:
            return (max(scores) + scores[-1]) / 2

    # Get the average score for students in a course
    # Use the StandardAttempt table as the leftmost join to filter down against the other conditions. Since the attempts do not matter which course they're in, just the user, you need to filter against the user_courses table to get only the desired course.
    # Only return values for students with the given course.id AND attempts for the assignment with the matching ID.
    def course_average(self, course_id):
        course_attempts = (
            StandardAttempt.query.join(Standard)
            .join(course_standards)
            .filter(
                (course_standards.c.course_id == course_id)
                & (StandardAttempt.standard_id == self.id)
            )
        ).all()
        return round(mean([attempt.score for attempt in course_attempts]), 2)


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

    def enroll(self, course):
        if not self.is_enrolled(course):
            self.enrollments.append(course)
            db.session.commit()
        else:
            raise DuplicateException(
                "{} is already enrolled in {}".format(self.name, course.name)
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
