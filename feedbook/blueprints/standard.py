from flask import Blueprint, jsonify, render_template
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Standard, StandardAttempt
from feedbook.schemas import StandardSchema, StandardListSchema

bp = Blueprint("standard", __name__)

# Admin view of all standards
@bp.get("/standards")
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
    #TODO: Toast the result
    return "ok"

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

