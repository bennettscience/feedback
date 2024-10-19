from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from htmx_flask import make_response
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Assignment, AssignmentType, Course
from feedbook.wrappers import restricted

bp = Blueprint("assignment", __name__)


@bp.get("/assignments")
def index():
    assignments = db.session.scalars(db.select(Assignment)).all()

    return render_template("assignments/index.html", assignments=assignments)


@bp.post("/assignments")
@login_required
@restricted
def create_assignment():
    args = parser.parse(
        {
            "name": fields.String(),
            "description": fields.String(),
            "type_id": fields.Int(),
            "courses": fields.List(fields.Int()),
        },
        location="form",
    )

    # Assignments don't need to be added to a specific course becuase any assignment can be attached to a standard attempt.
    assignment = Assignment(name=args["name"], assignmenttype_id=args["type_id"])
    db.session.add(assignment)
    db.session.commit()

    # Add the assignment to the courses requested
    for course in args["courses"]:
        c = Course.query.filter(Course.id == course).first()
        c.add_assignment(assignment)

    db.session.commit()
    # Return the full list of assignments to the admin page
    assignments = db.session.scalars(db.select(Assignment)).all()

    return make_response(trigger={"showToast": "Assignment added"})


@bp.get("/assignments/create")
@login_required
@restricted
def create_assignment_form():
    types = AssignmentType.query.all()
    courses = Course.query.all()
    return render_template(
        "course/right-sidebar.html",
        title="Create a new assignment",
        position="right",
        partial="shared/forms/create-assignment.html",
        data={"types": types, "courses": courses},
    )


@bp.get("/assignments/<int:id>")
def get_single_assignment(id):
    item = db.session.get(Assignment, id)

    return render_template("assignments/assignment_detail.html", assignment=item)


# TODO: Score single assignment
# Get the assignment, attach standards
# In the scoring table, list by student. Have a yes/no checkbox for each standard attached to the assignment.
