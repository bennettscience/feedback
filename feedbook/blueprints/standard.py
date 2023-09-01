from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
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
@bp.get("/standards/<int:id>")
def get_single_standard(id):
    standard = Standard.query.filter(Standard.id == id).first()
    # return render_template(
    #     "standards/single-standard.html",
    #     standard=standard
    # )

    print(StandardSchema().dump(standard))
    return StandardSchema().dump(standard)

@bp.get("/standards/<int:standard_id>/results/<int:user_id>")
@login_required
def get_standard_result(standard_id, user_id):
    from datetime import timedelta
    from feedbook.schemas import StandardAttemptSchema, UserSchema
    from feedbook.models import User

    # Set up the timezone offset
    # This is a nasty fix
    diff = timedelta(hours=5)

    if current_user.usertype_id == 1:
        student = User.query.filter(User.id == user_id).first()
        attempt = student.assessments.filter(StandardAttempt.id == standard_id).first()
    else:
        attempt = current_user.assessments.query.filter(StandardAttempt.id == standard_id)
        student = current_user
    
    # handle the timezone offset
    # attempt.occurred = attempt.occurred - diff

    data = {
        "standard": StandardAttemptSchema().dump(attempt),
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
        "standard_id": fields.Int(),
        "score": fields.Int(),
        "assignment": fields.Str(),
        "comments": fields.Str()
    }, location="form")

    sa = StandardAttempt(
        user_id=args['user_id'], 
        standard_id=args['standard_id'], 
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

