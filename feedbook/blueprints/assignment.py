from flask import Blueprint, current_app, jsonify, render_template
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
    """
    Get a list of all assignments.
    """
    assignments = Assignment.query.order_by(Assignment.created_on.desc()).all()
    return render_template("assignments/index.html", assignments=assignments)


@bp.post("/assignments")
@login_required
@restricted
def create_assignment():
    """
    Create a new assignment.
    """
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

    # Add the assignment to the courses requested
    for course in args["courses"]:
        course = Course.query.filter(Course.id == course).first()
        course.add_assignment(assignment)
        current_app.logger.info(
            f"Assignment {assignment.id} added to Course {course.id}"
        )

    db.session.commit()
    current_app.logger.info(
        f"Assignment {assignment.id} created by User {current_user.id}"
    )
    # Return the full list of assignments to the admin page
    assignments = db.session.scalars(db.select(Assignment)).all()
    current_course = db.session.get(Course, args["current_course_id"])

    return make_response(
        render_template(
            "assignments/assignment-list-item.html",
            assignment=assignment,
            course=current_course,
        ),
        trigger={
            "showToast": {"msg": "Assignment added", "err": False},
            "closeModal": True,
        },
    )


@bp.get("/assignments/create")
@login_required
@restricted
def create_assignment_form():
    """
    Get the form to create a new assignment.
    """
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


@bp.get("/assignments/<int:assignment_id>")
@login_required
@restricted
def get_assignment(assignment_id):
    """
    Get a single assignment
    """
    assignment = Assignment.query.filter(Assignment.id == assignment_id).first()
    return render_template("assignments/single-assignment.html", assignment=assignment)


@bp.get("/assignments/<int:assignment_id>/edit")
@login_required
@restricted
def get_assignment_edit_form(assignment_id):
    assignment = Assignment.query.filter(Assignment.id == assignment_id).first()
    types = AssignmentType.query.all()

    return render_template(
        "shared/forms/edit-assignment.html", assignment=assignment, types=types
    )


@bp.put("/assignments/<int:assignment_id>/edit")
@login_required
@restricted
def edit_assignment(assignment_id):
    """
    Edit an assignment's details
    """
    args = parser.parse(
        {
            "name": fields.String(),
            "created_on": fields.Date(),
            "assignmenttype_id": fields.Int(),
            "courses": fields.List(fields.Int()),
        },
        location="form",
    )

    assignment = Assignment.query.filter(Assignment.id == assignment_id).first()
    assignment.update(args)

    current_app.logger.info(f"Assignment {assignment.id} updated: {args}")

    if args.get("courses"):
        for course in args["courses"]:
            c = Course.query.filter(Course.id == course).first()
            c.add_assignment(assignment)

    return make_response(
        render_template("assignments/single-assignment.html", assignment=assignment),
        trigger={"showToast": "Assignment updated"},
    )


@bp.post("/assignments/<int:assignment_id>/align")
@login_required
@restricted
def create_standard_alignment(assignment_id):
    """
    Attach a standard to an assignment.
    """
    assignment = db.session.get(Assignment, assignment_id)
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
    """
    Remove a standard from an assignment.
    """
    assignment = Assignment.query.filter(Assignment.id == assignment_id).first()
    standard = Standard.query.filter(Standard.id == standard_id).first()

    assignment.alignments.remove(standard)
    db.session.commit()

    return make_response(trigger={"showToast": "Alignment removed"})


@bp.get("/assignments/<int:assignment_id>/attempts/<int:attempt_id>")
@login_required
@restricted
def get_assignment_attempt_edit_form(assignment_id, attempt_id):
    """
    Get the edit form to update Assignment details.
    """
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
    """
    Get a specific StandardAttempt record for a given assignment.
    """
    from feedbook.models import StandardAttempt

    attempt = db.session.get(StandardAttempt, attempt_id)
    return render_template("assignments/single-attempt.html", attempt=attempt)
