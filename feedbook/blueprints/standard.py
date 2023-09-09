from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from htmx_flask import make_response
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Standard, StandardAttempt
from feedbook.schemas import StandardSchema, StandardListSchema

bp = Blueprint("standard", __name__)

# Admin view of all standards
@bp.get("/standards")
@login_required
def all_standards():
    standards = Standard.query.all()
    return render_template(
        "standards/index.html",
        standards=standards
    )


@bp.post("/standards")
def create_standard():
    from feedbook.models import Course

    args = parser.parse({
        "name": fields.String(),
        "description": fields.String(),
        "course_id": fields.Int()
    }, location="form")

    standard = Standard(name=args["name"], description=args["description"])
    db.session.add(standard)
    db.session.commit()

    # Immediately align it to the course
    course = Course.query.filter(Course.id == args['course_id']).first()
    course.standards.append(standard)
    db.session.commit()

    items = [item for item in Standard.query.all() if item not in course.standards.all()]
    
    #TODO: Toast the result
    return render_template(
        "shared/forms/create-standard.html",
        items=StandardSchema(many=True).dump(items),
        course=course
    )
# Get a single standard
@bp.get("/standards/<int:standard_id>")
def get_single_standard(id):
    standard = Standard.query.filter(Standard.id == standard_id).first()
    # return render_template(
    #     "standards/single-standard.html",
    #     standard=standard
    # )

    print(StandardSchema().dump(standard))
    return StandardSchema().dump(standard)

# TODO: Get all results for a single student
@bp.get("/standards/<int:standard_id>/users/<int:user_id>/results")
def get_all_results_for_user(standard_id, user_id):
    pass

@bp.get("/standards/<int:standard_id>/users/<int:user_id>/results/<int:result_id>")
@login_required
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
        "student": UserSchema().dump(student)
    }

    return render_template(
        "course/right-sidebar.html",
        position="right",
        partial="standards/standard-result.html",
        clickable=True,
        data=data
    )

# Add an assessment to a standard
@bp.post("/standards/<int:standard_id>/attempts")
def add_standard_assessment(standard_id):
    from feedbook.models import StandardAttempt, User
    from feedbook.schemas import StandardAttemptSchema, UserSchema

    args = parser.parse({
        "user_id": fields.Int(),
        "score": fields.Int(),
        "assignment": fields.Str(),
        "comments": fields.Str()
    }, location="form")

    sa = StandardAttempt(
        user_id=args['user_id'], 
        standard_id=standard_id,
        score=args['score'], 
        assignment=args['assignment'],
        comments=args['comments']
    )
    db.session.add(sa)
    db.session.commit()

    user = User.query.filter(User.id == args['user_id']).first()

    user.assessments = user.assessments.filter(StandardAttempt.standard_id == standard_id)

    return render_template(
        "standards/student-updated.html",
        record=StandardAttemptSchema().dump(sa),
        name=f"{user.last_name}, {user.first_name}"
    )

# Edit a single standard attempt
@bp.get("/standards/<int:standard_id>/attempts/<int:attempt_id>")
def get_edit_form(standard_id, attempt_id):
    from feedbook.schemas import StandardListSchema

    standards = Standard.query.all()
    attempt = StandardAttempt.query.filter(StandardAttempt.id == attempt_id).first()

    return render_template(
        "shared/forms/edit-standard-attempt.html",
        attempt=attempt,
        standards=StandardListSchema(many=True).dump(standards)
    )

@bp.put("/standards/<int:standard_id>/attempts/<int:attempt_id>")
def edit_single_attempt(standard_id, attempt_id):
    from feedbook.schemas import StandardAttemptSchema
    args = parser.parse({
        "assignment": fields.String(),
        "score": fields.Int(),
        "standard_id": fields.Int(),
        "comments": fields.String()
    }, location="form")

    attempt = StandardAttempt.query.get(attempt_id)
    attempt.update(args)
        
    return make_response(
        refresh=True,
        trigger="closeModal"
    )

# Attach a standard to a course
@bp.post("/standards/align")
def add_standard_to_course():
    from feedbook.models import Course, User
    from feedbook.schemas import CourseSchema
    
    args = parser.parse({
        "standard_id": fields.Int(),
        "course_id": fields.Int()
    }, location="form")

    standard = Standard.query.filter(Standard.id == args["standard_id"]).first()
    course = Course.query.filter(Course.id == args['course_id']).first()

    course.standards.append(standard) 
    db.session.commit()
    
    # Student scores need to be calculated before sending
    student_enrollments = course.enrollments.filter(User.usertype_id == 2).all()
    for student in student_enrollments:
        student.scores = []
        for standard in course.standards.all():
            user_score = standard.current_score(student.id)
            student.scores.append({
                "standard_id": standard.id,
                "score": user_score
            })
                    
    return render_template(
        "course/teacher_index_htmx.html",
        course=CourseSchema().dump(course),
        students=student_enrollments
    )

