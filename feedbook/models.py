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


class Standard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(1000))
        
    attempts = db.relationship(
        "StandardAttempt",
        backref=backref("standard", cascade='all,delete,delete-orphan', single_parent=True),
        lazy="dynamic",
        passive_deletes=True
    )

    def __repr__(self):
        return self.name

    def __get_scores(self, user_id):
        return [
            item.score for item in self.attempts.filter(
                StandardAttempt.user_id == user_id).all()
        ]

    def current_score(self, user_id):
        """ Average the last attemp with the highest attempt.

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
            return round((max(scores) + scores[-1]) / 2, 1)


class StandardAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.ForeignKey("user.id", onupdate="CASCADE", ondelete="CASCADE")
    )
    standard_id = db.Column(db.ForeignKey("standard.id", onupdate="CASCADE", ondelete="CASCADE"))
    score = db.Column(db.Integer)
    occurred = db.Column(db.DateTime(timezone=True), default=func.now())
    comments = db.Column(db.String(1000))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_name = db.Column(db.String(32), nullable=False)
    first_name = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(64), nullable=False)
    password_hash = db.Column(db.String(128))
    usertype_id = db.Column(db.Integer, db.ForeignKey("user_type.id"))

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
    # assessments = db.relationship()
    # assignments = db.relationship()

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

