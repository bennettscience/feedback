from flask import Blueprint, jsonify, render_template
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Course, Standard, User
from feedbook.schemas import CourseSchema, StandardListSchema

bp = Blueprint("course", __name__)

@bp.get("/courses")
def get_all_courses():
    courses = Course.query.all()
    print(courses)
    return render_template(
        "shared/partials/sidebar.html",
        position="left",
        partial="course/partials/course_card.html",
        items=CourseSchema(many=True).dump(courses)
    )

@bp.get("/courses/create")
def get_create_course_form():
    return render_template(
        "shared/forms/create-course.html"
    )

@bp.post("/courses")
def create_course():
    args = parser.parse({
        "name": fields.Str(),
        "active": fields.Boolean()
    }, location="form")

    course = Course(name=args["name"], active=args["active"])
    db.session.add(course)
    db.session.commit()

    # refresh the course list
    courses = Course.query.all()
    
    return render_template(
        "course/partials/course_card.html",
        data=courses    
    )
    
@bp.get("/courses/<int:id>")
def get_single_course(id):
    course = Course.query.filter(Course.id == id).first()
    print(CourseSchema().dump(course))   
    return render_template(
        "course/teacher_index_htmx.html",
        course=CourseSchema().dump(course)
    )

# Create new standard
@bp.get("/courses/<int:course_id>/standards/create")
def get_create_standard_form(course_id):
    standards = Standard.query.all()
    
    return render_template(
        "shared/partials/sidebar.html",
        position="right",
        partial="standards/standard-small.html",
        title="Add standards",
        items=StandardListSchema(many=True).dump(standards),
        data=course_id
    )

