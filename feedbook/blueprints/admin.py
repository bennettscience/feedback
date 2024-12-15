from flask import abort, Blueprint, current_app, redirect, render_template, url_for
from flask_login import current_user, login_required
from htmx_flask import make_response

from feedbook.extensions import db
from feedbook.models import Course, Standard, User
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
        print(course.name)
        standard_results = []
        standards = course.standards.all()
        for standard in standards:
            print("{}, {}".format(course.name, standard.course_average(course.id)))
            standard_results.append(
                {"name": standard.name, "avg": standard.course_average(course.id)}
            )
        data.append({"course": course.name, "results": standard_results})

    icons = {"home": home, "add": add, "admin": admin, "logout": logout}
    return render_template("admin/index.html", icons=icons, status=data)
