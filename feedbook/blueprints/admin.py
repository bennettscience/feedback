from flask import Blueprint, render_template
from flask_login import login_required

from feedbook.models import Course, User, user_courses
from feedbook.static.icons import *
from feedbook.utils import get_system_stats
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
                    standard.students.join(User)
                    .join(user_courses)
                    .filter(User.active == True, user_courses.c.course_id == course.id)
                    .count()
                )
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

    # Get info for assignments and users in the database
    system_status = get_system_stats()

    icons = {"home": home, "add": add, "admin": admin, "logout": logout}
    return render_template(
        "admin/index.html", icons=icons, status=data, system_status=system_status
    )
