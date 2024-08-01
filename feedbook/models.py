from collections import Counter

from flask_login import UserMixin
from sqlalchemy.orm import backref
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash

from feedbook.extensions import db, login_manager


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class Artifact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    link = db.Column(db.String(128))
    narrative = db.Column(db.String(1000))


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    active = db.Column(db.Boolean, default=True)

    standards = db.relationship(
        "Standard",
        secondary="course_standards",
        backref=backref("standards", lazy="dynamic"),
        lazy="dynamic"
    )

    # safely align a standard to a course
    def align(self, standard):
        if not self._is_aligned(standard):
            self.standards.append(standard)
        return self
                
    def _is_aligned(self, standard):
        return self.standards.filter(course_standards.c.standard_id == standard.id).count() > 0


class Standard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(1000))
    active = db.Column(db.Boolean, default=True)
            
    attempts = db.relationship(
        "StandardAttempt",
        backref=backref("standard", single_parent=True),
        lazy="dynamic",
        passive_deletes=True
    )

    def __repr__(self):
        return self.name

    def __get_scores(self, user_id):
        scores = self.attempts.filter(StandardAttempt.user_id == user_id).order_by('occurred').all()
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
        """ Average the last attemp with the highest attempt.
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


class StandardAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.ForeignKey("user.id", onupdate="CASCADE", ondelete="CASCADE")
    )
    standard_id = db.Column(db.ForeignKey("standard.id", onupdate="CASCADE", ondelete="CASCADE"))
    score = db.Column(db.Integer)
    occurred = db.Column(db.DateTime(timezone=True), default=func.now())
    assignment = db.Column(db.String(32))
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
        lazy="dynamic"
    )

    artifacts = db.relationship(
        "Artifact",
        secondary="user_artifacts",
        backref=backref("artifacts", lazy="subquery"),
        lazy="dynamic"
    )

    assessments = db.relationship(
        "StandardAttempt",
        backref=backref("user",single_parent=True),
        lazy='dynamic',
        passive_deletes=True
    )

    def enroll(self, course):
        if not self.is_enrolled(course):
            self.enrollments.append(course)
            db.session.commit()
        else:
            raise DuplicateException('{} is already enrolled in {}'.format(self.name, course.name))
    
    def is_enrolled(self, course):
        return self.enrollments.filter(user_courses.c.course_id == course.id).count() > 0
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        db.session.commit()

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class UserType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))


course_standards = db.Table(
    "course_standards",
    db.Column("id", db.Integer, primary_key=True),
    db.Column("course_id", db.Integer, db.ForeignKey("course.id", onupdate="CASCADE", ondelete="CASCADE")),
    db.Column("standard_id", db.Integer, db.ForeignKey("standard.id", onupdate="CASCADE", ondelete="CASCADE"))
)

user_artifacts = db.Table(
    "user_artifacts", db.Column("id", db.Integer, primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id", onupdate="CASCADE", ondelete="CASCADE")),
    db.Column("artifact_id", db.Integer, db.ForeignKey("artifact.id", onupdate="CASCADE", ondelete="CASCADE"))
)

standard_artifact = db.Table(
    "standard_artifact", db.Column("id", db.Integer, primary_key=True),
    db.Column("standard_id", db.Integer, db.ForeignKey("standard.id", onupdate="CASCADE", ondelete="CASCADE")),
    db.Column("artifact_id", db.Integer, db.ForeignKey("artifact.id", onupdate="CASCADE", ondelete="CASCADE"))
)

user_courses= db.Table(
    "user_courses",
    db.Column("id", db.Integer, primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id", onupdate="CASCADE", ondelete="CASCADE")),
    db.Column("course_id", db.Integer, db.ForeignKey("course.id", onupdate="CASCADE", ondelete="CASCADE"))
)

