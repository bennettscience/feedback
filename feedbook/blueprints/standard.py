from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required
from htmx_flask import make_response
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Standard, StandardAttempt
from feedbook.schemas import StandardSchema, StandardListSchema
from feedbook.wrappers import restricted

bp = Blueprint("standard", __name__)


# Admin view of all standards
@bp.get("/standards")
@login_required
def index():
    """
    Get all standards in the database.
    """
    standards = Standard.query.all()
    return render_template("standards/index.html", standards=standards)


@bp.post("/standards")
@login_required
@restricted
def create_standard():
    """
    Create a new standard
    Standards are course agnostic and can be created in the database. The course context _calling_ the created standard is immediately added as an association.
    """
    from feedbook.models import Course

    args = parser.parse(
        {
            "name": fields.String(),
            "description": fields.String(),
            "course_id": fields.Int(),
        },
        location="form",
    )

    standard = Standard(name=args["name"], description=args["description"], active=True)
    db.session.add(standard)
    db.session.commit()

    current_app.logger.info(
        f"Standard {standard.name} created by User {current_user.id}"
    )
    # Immediately align it to the course
    course = Course.query.filter(Course.id == args["course_id"]).first()
    course.align(standard)
    db.session.commit()

    current_app.logger.info(f"Standard {standard.id} added to Course {course.id}")

    items = [
        item for item in Standard.query.all() if item not in course.standards.all()
    ]

    # The template expects a results object, so send something empty along because there is no data right now.
    results = {"proficient": 0, "not_proficient": 0}

    return make_response(
        render_template(
            "shared/forms/create-standard.html",
            items=items,
            course=course,
            results=results,
        ),
        trigger={"showToast": "Standard created successfully."},
    )


# Get a single standard
# 11/2024 - Not in use
@bp.get("/standards/<int:standard_id>")
@login_required
def get_single_standard(id):  # pragma: no cover
    # TODO: Add in stats
    # Get all the attempts
    # Sort by class
    # Graph showing breakdown of average score for each course section
    pass


# Set the active/inactive status on a single standard
@bp.put("/standards/<int:standard_id>/status")
@login_required
@restricted
def update_standard_status(standard_id):
    """
    Update the status of the standard.

    """
    standard = Standard.query.filter(Standard.id == standard_id).first()

    standard.active = not standard.active
    db.session.commit()

    current_app.logger.info(
        f"Standard {standard.id} set to {standard.active} by User {current_user.id}"
    )

    value = "Deactivate" if standard.active else "Activate"
    return make_response(value, trigger={"showToast": "Standard status updated."})


# Get standard results for a single student
@bp.get("/standards/<int:standard_id>/users/<int:user_id>/results/<int:result_id>")
@login_required
@restricted
def get_standard_result(standard_id, user_id, result_id):
    """
    Get a single result for a student.

    Returns the sidebar template with the <StandardAttempt> data.
    """
    from datetime import timedelta
    from feedbook.models import User

    student = User.query.filter(User.id == user_id).first()
    attempt = student.assessments.filter(StandardAttempt.id == result_id).first()

    return render_template(
        "course/right-sidebar.html",
        position="right",
        partial="standards/standard-result.html",
        clickable=True,
        data={"attempt": attempt, "student": student},
    )


# Add an assessment to a standard
@bp.post("/standards/<int:standard_id>/attempts")
@login_required
@restricted
def add_standard_assessment(standard_id):
    """
    Add a StandardAttempt record for a student

    Generic attempt record for a user_id on a standard_id. Can be posted from the course context or the assignment context.
    """
    from feedbook.models import StandardAttempt, User
    from feedbook.schemas import StandardAttemptSchema, UserSchema

    args = parser.parse(
        {
            "user_id": fields.Int(),
            "score": fields.Int(),
            "assignment": fields.Int(),
            "comments": fields.Str(),
        },
        location="form",
    )

    sa = StandardAttempt(
        user_id=args["user_id"],
        standard_id=standard_id,
        score=args["score"],
        assignment_id=args["assignment"],
        comments=args["comments"],
    )
    db.session.add(sa)
    db.session.commit()

    # If the assignment is a test, add a record on the
    # student proficiencies
    if sa.assessed_on.type.name == "Assessment":
        sa.standard.add_proficient_override(sa.user)
        current_app.logger.info(
            "Added proficiency record on {} for {}".format(sa.standard, args["user_id"])
        )

    return render_template(
        "standards/student-updated.html",
        record=sa,
        name=f"{sa.user.last_name}, {sa.user.first_name}",
    )


# Edit a single standard attempt
@bp.get("/standards/<int:standard_id>/attempts/<int:attempt_id>")
@login_required
@restricted
def get_edit_form(standard_id, attempt_id):
    """
    Get the edit form to update a StandardAttempt record for a student.
    """
    from feedbook.schemas import StandardListSchema
    from feedbook.models import Assignment

    standards = Standard.query.all()
    attempt = StandardAttempt.query.filter(StandardAttempt.id == attempt_id).first()
    assignments = Assignment.query.all()

    return render_template(
        "shared/forms/edit-standard-attempt.html",
        attempt=attempt,
        standards=standards,
        assignments=assignments,
    )


@bp.put("/standards/<int:standard_id>/attempts/<int:attempt_id>")
@login_required
@restricted
def edit_single_attempt(standard_id, attempt_id):
    """
    Update a StandardAttempt record for a student.
    """
    from feedbook.models import User

    # This will accept a query param as well as the form. Parse
    # the param to return the correct template.
    query = request.args.get("source")

    args = parser.parse(
        {
            "assignment_id": fields.Int(),
            "score": fields.Int(),
            "standard_id": fields.Int(),
            "comments": fields.String(),
        },
        location="form",
    )

    attempt = db.session.get(StandardAttempt, attempt_id)
    attempt.update(args)

    if query == "standard":
        template = "course/partials/student-entry.html"
        student = db.session.get(User, attempt.user_id)
        student.scores = student.assessments.filter(
            StandardAttempt.standard_id == standard_id
        ).all()

        data = {"student": student, "clickable": True}
    else:
        template = "assignments/single-attempt.html"
        data = {"attempt": attempt}

    return make_response(
        render_template(template, **data),
        trigger={"showToast": "Attempt updated", "closeModal": ""},
    )


# Delete a single standard attempt
@bp.delete("/standards/<int:standard_id>/attempts/<int:attempt_id>")
@login_required
@restricted
def delete_standard_assessment(standard_id, attempt_id):
    """
    Remove a single StandardAttempt from the database.
    """
    attempt = db.session.get(StandardAttempt, attempt_id)
    db.session.delete(attempt)
    db.session.commit()

    # The closeModal event doesn't need a specific value in the template,
    # so just pass it an empty string to fire.
    return make_response(trigger={"closeModal": "", "showToast": "Attempt deleted"})


# Attach a standard to a course
@bp.post("/standards/align")
@login_required
@restricted
def add_standard_to_course():
    from feedbook.models import Course, User
    from feedbook.schemas import CourseSchema

    args = parser.parse(
        {"standard_id": fields.Int(), "course_id": fields.Int()}, location="form"
    )

    standard = Standard.query.filter(Standard.id == args["standard_id"]).first()
    course = Course.query.filter(Course.id == args["course_id"]).first()

    course.align(standard)
    db.session.commit()

    results = {"proficient": 0, "not_proficient": 0}

    return render_template(
        "standards/standard-card.html",
        item=standard,
        course_id=args["course_id"],
        results=results,
    )
