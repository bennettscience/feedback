from flask import Blueprint, render_template
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Standard, StandardAttempt
from feedbook.schemas import StandardListSchema

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
    args = parser.parse({
        "name": fields.String(),
        "description": fields.String()
    }, location="form")

    standard = Standard(name=args["name"], description=args["description"])
    db.session.add(standard)
    db.session.commit()

    standards = Standard.query.all()
    return render_template(
        "standards/index.html",
        standards=standards
    )

# Get a single standard
@bp.get("/standards/<int:id>")
def get_single_standard(id):
    standard = Standard.query.filter(Standard.id == id).first()
    return render_template(
        "standards/single-standard.html",
        standard=standard
    )

# Attach a standard to a course
@bp.post("/standards/align")
def add_standard_to_course():
    from feedbook.models import Course
    
    args = parser.parse({
        "standard_id": fields.Int(),
        "course_id": fields.Int()
    }, location="form")

    standard = Standard.query.filter(Standard.id == args["standard_id"]).first()
    course = Course.query.filter(Course.id == args['course_id']).first()

    course.standards.append(standard) 
    db.session.commit()
    
    return render_template(
        "course/teacher_index_htmx.html",
        course=course
    )
