import csv
from io import TextIOWrapper

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Course, Standard, User
from feedbook.schemas import CourseSchema, StandardListSchema

bp = Blueprint("course", __name__)

@bp.get("/courses")
@login_required
def get_all_courses():
    courses = current_user.enrollments.all()
    return render_template(
        "shared/partials/sidebar.html",
        position="left",
        partial="course/partials/course_card.html",
        items=CourseSchema(many=True).dump(courses)
    )

@bp.get("/courses/create")
@login_required
def get_create_course_form():
    return render_template(
        "course/right-sidebar.html",
        title="Create a new course",
        position="right",
        partial="shared/forms/create-course.html",
        data={}
    )

@bp.post("/courses")
@login_required
def create_course():
    args = parser.parse({
        "name": fields.Str(),
    }, location="form")

    course = Course(name=args["name"], active=True)
    db.session.add(course)
    db.session.commit()

    current_user.enroll(course)
    
    # refresh the course list
    courses = current_user.enrollments.all()
    
    return render_template(
        "shared/partials/sidebar.html",
        position="left",
        partial="course/partials/course_card.html",
        items=CourseSchema(many=True).dump(courses)
    )

@bp.get("/courses/<int:course_id>/upload")
@login_required
def get_roster_form(course_id):
    return render_template(
        "course/right-sidebar.html",
        position="right",
        partial="course/partials/roster-upload.html",
        data={
            "course_id": course_id
        }
    )

@bp.post("/courses/<int:course_id>/upload")
@login_required
def roster_upload(course_id):
    args = parser.parse({
        "file": fields.Field(
            validate=lambda file: "csv" == file.filename.split(".")[-1].lower())
    }, location="files")

    course = current_user.enrollments.filter(Course.id == course_id).first()
    
    csv_file = TextIOWrapper(args['file'], encoding="utf-8")
    reader = csv.reader(csv_file, delimiter=",")
    next(reader)
    
    for row in reader:
        user = User(
            email=row[2],
            last_name=row[0],
            first_name=row[1],
            usertype_id=2
        )
        user.set_password(row[3])
        db.session.add(user)

        user.enroll(course)
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
    
@bp.get("/courses/<int:id>")
@login_required
def get_single_course(id):
    course = current_user.enrollments.filter(Course.id == id).first()

    if current_user.usertype_id == 2:
        return render_template(
            "course/student_index.html",
            course=course
        )
    else:
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
@login_required
def get_create_standard_form(course_id):
    standards = Standard.query.all()
    course = current_user.enrollments.filter(Course.id == course_id).first()

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
@login_required
def get_standard_scores_in_course(course_id, standard_id):
    from feedbook.models import StandardAttempt
    from feedbook.schemas import StandardAttemptSchema

    course = Course.query.filter(Course.id== course_id).first()
    standard = Standard.query.filter(Standard.id == standard_id).first()

    student_enrollments = course.enrollments.filter(User.usertype_id == 2).order_by('last_name').all()

    scores = []
    for student in student_enrollments:
        assessments = student.assessments.filter(StandardAttempt.standard_id == standard_id).order_by(StandardAttempt.occurred)
        
        scores.append({
            "last_name": student.last_name,
            "first_name": student.first_name,
            "id": student.id, 
            "scores": StandardAttemptSchema(many=True).dump(assessments)
        })

    return render_template(
        "course/partials/standard_score_table.html",
        students=scores,
        course_id=course_id,
        standard_id=standard_id
    )

@bp.get("/courses/<int:course_id>/users/<int:user_id>/results/<int:standard_id>")
def get_student_results(course_id, user_id, standard_id):
    from feedbook.models import StandardAttempt
    from feedbook.schemas import StandardAttemptSchema
    
    results = current_user.assessments.filter(StandardAttempt.standard_id == standard_id).order_by(StandardAttempt.occurred)

    return render_template(
        "standards/student-standard-scores.html",
        results=StandardAttemptSchema(many=True).dump(results)        
    )

# Remove a standard from the course
@bp.delete("/courses/<int:course_id>/standards/<int:standard_id>")
@login_required
def remove_standard_from_course(course_id, standard_id):
    if current_user.usertype_id == 2:
        abort(401)
    course = current_user.enrollments.filter(Course.id == course_id).first()
    standard = Standard.query.filter(Standard.id == standard_id).first()
    
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
@login_required
def get_assessment_form(course_id, standard_id):
    if current_user.usertype_id == 2:
        abort(401)
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