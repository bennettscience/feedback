from flask import Blueprint, jsonify, render_template
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
    standards = Standard.query.all()
    return render_template("standards/index.html", standards=standards)


@bp.post("/standards")
@login_required
@restricted
def create_standard():
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

    # Immediately align it to the course
    course = Course.query.filter(Course.id == args["course_id"]).first()
    course.align(standard)
    db.session.commit()

    items = [
        item for item in Standard.query.all() if item not in course.standards.all()
    ]

    # TODO: Toast the result
    return render_template(
        "shared/forms/create-standard.html",
        items=StandardSchema(many=True).dump(items),
        course=course,
    )


# Get data for a single standard
@bp.get("/standards/<int:standard_id>/stats")
@login_required
@restricted
def get_standard_stats(standard_id):
    pass

    # Get all the attempts
    # Sort by class
    # Graph showing breakdown of average score for each course section


# Get a single standard
@bp.get("/standards/<int:standard_id>")
@login_required
def get_single_standard(id):
    standard = Standard.query.filter(Standard.id == standard_id).first()
    # return render_template(
    #     "standards/single-standard.html",
    #     standard=standard
    # )

    print(StandardSchema().dump(standard))
    return StandardSchema().dump(standard)


# Set the active/inactive status on a single standard
@bp.put("/standards/<int:standard_id>/status")
@login_required
@restricted
def update_standard_status(standard_id):
    standard = Standard.query.filter(Standard.id == standard_id).first()

    standard.active = not standard.active
    db.session.commit()

    value = "Deactivate" if standard.active else "Activate"
    return make_response(value, trigger={"showToast": "Standard stauts updated"})


# Get standard results for a single student
@bp.get("/standards/<int:standard_id>/users/<int:user_id>/results/<int:result_id>")
@login_required
@restricted
def get_standard_result(standard_id, user_id, result_id):
    from datetime import timedelta
    from feedbook.schemas import StandardAttemptSchema, UserSchema
    from feedbook.models import User

    if current_user.usertype_id == 1:
        student = User.query.filter(User.id == user_id).first()
        attempt = student.assessments.filter(StandardAttempt.id == result_id).first()
    else:
        attempt = current_user.assessments.query.filter(StandardAttempt.id == result_id)
        student = current_user

    data = {
        "attempt": StandardAttemptSchema().dump(attempt),
        "student": UserSchema().dump(student),
    }

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

    user = User.query.filter(User.id == args["user_id"]).first()

    user.assessments = user.assessments.filter(
        StandardAttempt.standard_id == standard_id
    )

    return render_template(
        "standards/student-updated.html",
        record=sa,
        name=f"{user.last_name}, {user.first_name}",
    )


# TODO: Bulk upload a CSV of scores
# Accept a file with a single score in each row to speed up scoring from
# third party platforms.


# Edit a single standard attempt
@bp.get("/standards/<int:standard_id>/attempts/<int:attempt_id>")
@login_required
@restricted
def get_edit_form(standard_id, attempt_id):
    from feedbook.schemas import StandardListSchema

    standards = Standard.query.all()
    attempt = StandardAttempt.query.filter(StandardAttempt.id == attempt_id).first()

    return render_template(
        "shared/forms/edit-standard-attempt.html",
        attempt=attempt,
        standards=StandardListSchema(many=True).dump(standards),
    )


@bp.put("/standards/<int:standard_id>/attempts/<int:attempt_id>")
@login_required
@restricted
def edit_single_attempt(standard_id, attempt_id):
    from feedbook.models import User
    from feedbook.schemas import StandardAttemptSchema

    args = parser.parse(
        {
            "assignment": fields.String(),
            "score": fields.Int(),
            "standard_id": fields.Int(),
            "comments": fields.String(),
        },
        location="form",
    )

    attempt = StandardAttempt.query.get(attempt_id)
    attempt.update(args)

    student = User.query.get(attempt.user_id)
    student.scores = student.assessments.filter(
        StandardAttempt.standard_id == standard_id
    ).all()

    return make_response(
        render_template(
            "course/partials//student_entry.html", student=student, clickable=True
        ),
        trigger={"showToast": "Attempt updated", "closeModal": ""},
    )


# Delete a single standard attempt
@bp.delete("/standards/<int:standard_id>/attempts/<int:attempt_id>")
@login_required
@restricted
def delete_standard_assessment(standard_id, attempt_id):
    attempt = StandardAttempt.query.get(attempt_id)
    db.session.delete(attempt)
    db.session.commit()

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

    # Student scores need to be calculated before sending
    student_enrollments = course.enrollments.filter(User.usertype_id == 2).all()
    for student in student_enrollments:
        student.scores = []
        for standard in course.standards.all():
            user_score = standard.current_score(student.id)
            student.scores.append({"standard_id": standard.id, "score": user_score})

    return render_template(
        "course/teacher_index_htmx.html",
        course=CourseSchema().dump(course),
        students=student_enrollments,
    )
