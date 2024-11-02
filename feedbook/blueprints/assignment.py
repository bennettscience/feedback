from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from htmx_flask import make_response
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Assignment, AssignmentType, Course, Standard
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
            "current_course_id": fields.Int(),
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
    current_course = Course.query.get(args["current_course_id"])

    return make_response(
        render_template(
            "assignments/assignment_list.html",
            assignments=assignments,
            course=current_course,
        ),
        trigger={"showToast": "Assignment added", "closeModal": True},
    )


@bp.get("/assignments/create")
@login_required
@restricted
def create_assignment_form():
    args = parser.parse({"current_course_id": fields.Int()}, location="query")
    types = AssignmentType.query.all()
    courses = Course.query.all()
    return render_template(
        "course/right-sidebar.html",
        title="Create a new assignment",
        position="right",
        partial="shared/forms/create-assignment.html",
        data={
            "types": types,
            "courses": courses,
            "course_id": args["current_course_id"],
        },
    )


@bp.post("/assignments/<int:assignment_id>/align")
@login_required
@restricted
def create_standard_alignment(assignment_id):
    assignment = Assignment.query.get(assignment_id)
    args = parser.parse({"standards": fields.List(fields.Int())}, location="form")
    for standard_id in args["standards"]:
        standard = Standard.query.filter(Standard.id == standard_id).first()
        if standard:
            assignment.add_standard(standard)

    return make_response(trigger={"showToast": "Alignments created"})


@bp.delete("/assignments/<int:assignment_id>/align/<int:standard_id>")
@login_required
@restricted
def remove_standard_alignment(assignment_id, standard_id):
    assignment = Assignment.query.filter(Assignment.id == assignment_id).first()
    standard = Standard.query.filter(Standard.id == standard_id).first()

    assignment.alignments.remove(standard)
    db.session.commit()

    return make_response(trigger={"showToast": "Alignment removed"})


@bp.get("/assignments/<int:assignment_id>/attempts/<int:attempt_id>")
@login_required
@restricted
def get_assignment_edit_form(assignment_id, attempt_id):
    from feedbook.models import StandardAttempt

    attempt = StandardAttempt.query.filter(StandardAttempt.id == attempt_id).first()

    return render_template(
        "shared/forms/assignment-attempt-form.html",
        attempt=attempt,
    )


@bp.get("/assignments/<int:assignment_id>/results/<int:attempt_id>")
@login_required
@restricted
def get_assignment_attempt_result(assignment_id, attempt_id):
    from feedbook.models import StandardAttempt

    attempt = db.session.get(StandardAttempt, attempt_id)
    return render_template("assignments/single_attempt.html", attempt=attempt)


# In the scoring table, list by student. Have a yes/no checkbox for each standard attached to the assignment.
