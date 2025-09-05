from flask import (
    abort,
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from htmx_flask import make_response

from feedbook.extensions import db
from feedbook.models import Course, Standard, User, user_courses
from feedbook.static.icons import *
from feedbook.wrappers import restricted

bp = Blueprint("admin", __name__)


def process_course_data(courses):
    data = []
    for course in courses:
        standard_results = []
        enrollments = course.enrollments.filter(User.usertype_id == 2, User.active)
        for standard in course.standards.filter(Standard.active):
            # Filter the students array on the standard and count how many
            # are proficient in the current course through the user_courses table
            query = (
                standard.students.join(User)
                .join(user_courses)
                .filter(User.active, user_courses.c.course_id == course.id)
            )
            if query.all():
                count = query.count()
            else:
                count = 0
                for student in enrollments.filter(User.active == True).all():
                    if standard.is_proficient(student):
                        count += 1

            # Divide that count by the enrollment length variable
            standard_results.append(
                {
                    "name": standard.name,
                    "avg": round(count / enrollments.count(), 2),
                }
            )
        data.append({"course": course.name, "results": standard_results})

    return data


@bp.get("/admin")
@login_required
@restricted
def index():
    """
    Load the main admin panel. Reload the sidebar because
    this extends the main layout right now.
    """
    # Loop the requested courses
    query = request.args.get("archived")

    if query:
        courses = Course.query.all()
        data = process_course_data(courses)

        return data
    else:
        courses = Course.query.filter(Course.active == True).all()
        # For each course, build an array of all of the standards

        data = process_course_data(courses)

        return render_template("admin/index.html", status=data)
