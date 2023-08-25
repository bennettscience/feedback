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
    return render_template(
        "shared/partials/sidebar.html",
        position="left",
        partial="course/partials/course_card.html",
        items=CourseSchema(many=True).dump(courses)
    )

@bp.get("/courses/create")
def get_create_course_form():
    return render_template(
        "course/right-sidebar.html",
        title="Create a new course",
        position="right",
        partial="shared/forms/create-course.html"
    )

@bp.post("/courses")
def create_course():
    args = parser.parse({
        "name": fields.Str(),
    }, location="form")

    course = Course(name=args["name"], active=True)
    db.session.add(course)
    db.session.commit()

    # refresh the course list
    courses = Course.query.all()
    
    return render_template(
        "shared/partials/sidebar.html",
        position="left",
        partial="course/partials/course_card.html",
        items=CourseSchema(many=True).dump(courses)
    )
    
@bp.get("/courses/<int:id>")
def get_single_course(id):
    course = Course.query.filter(Course.id == id).first()

    # Student scores need to be calculated before sending
    student_enrollments = course.enrollments.filter(User.usertype_id == 2).order_by('last_name').all()
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

# Create new standard
@bp.get("/courses/<int:course_id>/standards/create")
def get_create_standard_form(course_id):
    standards = Standard.query.all()
    course = Course.query.filter(Course.id == course_id).first()

    filtered = [standard for standard in standards if standard not in course.standards]
    
    return render_template(
        "standards/standard-sidebar.html",
        position="right",
        partial="shared/forms/create-standard.html",
        title="Add standards",
        items=StandardListSchema(many=True).dump(filtered),
        course_id=course_id
    )

# Get results for a standard in the course context
@bp.get("/courses/<int:course_id>/standards/<int:standard_id>/results")
def get_standard_scores_in_course(course_id, standard_id):
    from feedbook.models import StandardAttempt
    from feedbook.schemas import StandardAttemptSchema

    course = Course.query.filter(Course.id== course_id).first()
    standard = Standard.query.filter(Standard.id == standard_id).first()

    student_enrollments = course.enrollments.filter(User.usertype_id == 2).order_by('last_name').all()

    scores = []
    for student in student_enrollments:
        assessments = student.assessments.filter(StandardAttempt.standard_id == standard_id)
        scores.append({
            "last_name": student.last_name,
            "first_name": student.first_name, 
            "scores": StandardAttemptSchema(many=True).dump(assessments)
        })

    return render_template(
        "course/partials/standard_score_table.html",
        students=scores,
        course_id=course_id,
        standard_id=standard_id
    )

# Remove a standard from the course
@bp.delete("/courses/<int:course_id>/standards/<int:standard_id>")
def remove_standard_from_course(course_id, standard_id):
    course = Course.query.filter(Course.id == course_id).first()
    standard = Standard.query.filter(Standard.id == standard_id).first()
    
    print(standard)
    course.standards.remove(standard)
    db.session.commit()

    student_enrollments = course.enrollments.filter(User.usertype_id == 2).order_by('last_name').all()
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

@bp.get("/courses/<int:course_id>/standards/<int:standard_id>/assess")
def get_assessment_form(course_id, standard_id):
    from feedbook.schemas import UserSchema
    course = Course.query.filter(Course.id == course_id).first()

    # Get the enrollments, alphabatized to start the loop
    enrollments = course.enrollments.filter(User.usertype_id == 2).order_by('last_name').all()

    return render_template(
        "standards/student-assessment-form.html",
        students=enrollments,
        standard_id=standard_id,
        course_id=course_id
    )