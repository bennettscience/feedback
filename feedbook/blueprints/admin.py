from flask import abort, Blueprint, current_app, redirect, render_template, url_for
from flask_login import current_user, login_required
from htmx_flask import make_response

from feedbook.extensions import db
from feedbook.models import Course, Standard, User, user_courses
from feedbook.static.icons import *
from feedbook.wrappers import restricted

bp = Blueprint("admin", __name__)


@bp.get("/admin")
@login_required
@restricted
def index():
    """
    Load the main admin panel. Reload the sidebar because
    this extends the main layout right now.
    """
    data = []
    # Loop all the courses
    courses = Course.query.all()
    # For each course, build an array of all of the standards
    for course in courses:
        standard_results = []
        enrollments = course.enrollments.filter(User.usertype_id == 2, User.active)
        for standard in course.standards.all():
            # Filter the students array on the standard and count how many
            # are proficient in the current course through the user_courses table
            if standard.students.all():
                count = (
                    standard.students.join(user_courses)
                    .filter(user_courses.c.course_id == course.id)
                    .count()
                )
            else:
                count = 0
                for student in enrollments.all():
                    if standard.is_proficient(student):
                        count += 1

            # Divide that count by the enrollment length variable
            standard_results.append(
                {"name": standard.name, "avg": round(count / enrollments.count(), 2)}
            )
        data.append({"course": course.name, "results": standard_results})

    icons = {"home": home, "add": add, "admin": admin, "logout": logout}
    return render_template("admin/index.html", icons=icons, status=data)
