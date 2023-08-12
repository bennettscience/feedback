from flask import Blueprint, jsonify, render_template
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Course, User
from feedbook.schemas import CourseSchema

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
        "home/courses",
        courses=courses    
    )
    
@bp.get("/courses/<int:id>")
def get_single_course(id):
    course = Course.query.filter(Course.id == id).first()
    return render_template(
        "home/single-course.html",
        course=course
    )