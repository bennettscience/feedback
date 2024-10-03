import csv
from io import TextIOWrapper
from collections import defaultdict

from flask import abort, Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Assignment, Course, Standard, User
from feedbook.schemas import CourseSchema, StandardListSchema
from feedbook.wrappers import restricted

bp = Blueprint("course", __name__)


@bp.get("/courses")
@login_required
def get_all_courses():
    courses = current_user.enrollments.all()
    return render_template(
        "shared/partials/sidebar.html",
        position="left",
        partial="course/partials/course_card.html",
        items=CourseSchema(many=True).dump(courses),
    )


@bp.get("/courses/create")
@login_required
@restricted
def get_create_course_form():
    return render_template(
        "course/right-sidebar.html",
        title="Create a new course",
        position="right",
        partial="shared/forms/create-course.html",
        data={},
    )


@bp.post("/courses")
@login_required
@restricted
def create_course():
    args = parser.parse(
        {
            "name": fields.Str(),
        },
        location="form",
    )

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
        items=CourseSchema(many=True).dump(courses),
    )


# TODO: Enroll a single student


# Request the upload form
@bp.get("/courses/<int:course_id>/upload")
@login_required
@restricted
def get_roster_form(course_id):
    return render_template(
        "course/right-sidebar.html",
        position="right",
        partial="course/partials/roster-upload.html",
        data={"course_id": course_id},
    )


# Process the uploaded CSV file for a new course roster.
@bp.post("/courses/<int:course_id>/upload")
@login_required
@restricted
def roster_upload(course_id):
    args = parser.parse(
        {
            "file": fields.Field(
                validate=lambda file: "csv" == file.filename.split(".")[-1].lower()
            )
        },
        location="files",
    )

    course = current_user.enrollments.filter(Course.id == course_id).first()

    csv_file = TextIOWrapper(args["file"], encoding="utf-8")
    reader = csv.reader(csv_file, delimiter=",")
    next(reader)

    for row in reader:
        user = User(
            email=row[2],
            last_name=row[0],
            first_name=row[1],
            usertype_id=2,
            active=True,
        )
        user.set_password(row[3])
        db.session.add(user)

        user.enroll(course)
        db.session.commit()

    student_enrollments = (
        course.enrollments.filter(User.usertype_id == 2, User.active == True)
        .order_by("last_name")
        .all()
    )
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


# Get a single course
@bp.get("/courses/<int:id>")
@login_required
def get_single_course(id):
    course = current_user.enrollments.filter(Course.id == id).first()

    if not course:
        abort(401)

    if current_user.usertype_id == 2:
        return render_template("course/student_index.html", course=course)
    else:
        # Student scores need to be calculated before sending
        student_enrollments = (
            course.enrollments.filter(User.usertype_id == 2).order_by("last_name").all()
        )

        for student in student_enrollments:
            student.scores = []
            for standard in course.standards.filter(Standard.active == True).all():
                user_score = standard.current_score(student.id)
                student.scores.append(
                    {
                        "standard": {
                            "id": standard.id,
                        },
                        "score": user_score,
                    }
                )

        return render_template(
            "course/teacher_index_htmx.html",
            course=course,
            students=student_enrollments,
        )


# Get a single user from a course
@bp.get("/courses/<int:course_id>/users")
@login_required
@restricted
def get_user(course_id):
    args = parser.parse({"user_id": fields.Int()}, location="querystring")
    course = Course.query.filter(Course.id == course_id).first()
    user = User.query.filter(User.id == args["user_id"]).first()
    standards = defaultdict(list)
    scores_only = defaultdict(list)

    for a in user.assessments.all():
        standards[a.standard.name].append(
            {"assignment": a.assignment, "score": a.score, "occurred": a.occurred}
        )
        scores_only[a.standard.name].append(a.score)

    enrollments = [user for user in course.enrollments if user.usertype_id == 2]

    return render_template(
        "user/user-index.html",
        user=user,
        standards=standards,
        scores_only=scores_only,
        enrollments=enrollments,
        course=course,
    )


# Create new standard
@bp.get("/courses/<int:course_id>/standards/create")
@login_required
@restricted
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
        course_id=course_id,
    )


# Get results for a standard in the course context
@bp.get("/courses/<int:course_id>/standards/<int:standard_id>/results")
@login_required
@restricted
def get_standard_scores_in_course(course_id, standard_id):
    from feedbook.models import StandardAttempt
    from feedbook.schemas import StandardAttemptSchema

    course = Course.query.filter(Course.id == course_id).first()
    standard = Standard.query.filter(Standard.id == standard_id).first()

    student_enrollments = (
        course.enrollments.filter(User.usertype_id == 2, User.active == True)
        .order_by("last_name")
        .all()
    )

    # Get all the assignment IDs to use as keys for displaying results
    # in an organized table.
    assignments = Assignment.query.all()
    headers = [assignment.name for assignment in assignments]

    # Process student results
    results = []
    for student in student_enrollments:
        assessments = student.assessments.filter(
            StandardAttempt.standard_id == standard_id
        ).order_by(StandardAttempt.occurred)

        results.append(
            {
                "last_name": student.last_name,
                "first_name": student.first_name,
                "id": student.id,
                "scores": assessments,
            }
        )

    return render_template(
        "course/partials/standard_score_table.html",
        students=results,
        course_id=course_id,
        standard_id=standard_id,
        headers=headers,
        assignments=assignments,
    )


# Student view
# Get current results for a single student in a course.
@bp.get("/courses/<int:course_id>/users/<int:user_id>/results/<int:standard_id>")
def get_student_results(course_id, user_id, standard_id):
    from feedbook.models import StandardAttempt
    from feedbook.schemas import StandardAttemptSchema

    results = current_user.assessments.filter(
        StandardAttempt.standard_id == standard_id
    ).order_by(StandardAttempt.occurred)

    return render_template(
        "standards/student-standard-scores.html",
        results=StandardAttemptSchema(many=True).dump(results),
    )


# Remove a standard from the course
@bp.delete("/courses/<int:course_id>/standards/<int:standard_id>")
@login_required
@restricted
def remove_standard_from_course(course_id, standard_id):
    if current_user.usertype_id == 2:
        abort(401)
    course = current_user.enrollments.filter(Course.id == course_id).first()
    standard = Standard.query.filter(Standard.id == standard_id).first()

    course.standards.remove(standard)
    db.session.commit()

    student_enrollments = (
        course.enrollments.filter(User.usertype_id == 2).order_by("last_name").all()
    )
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


# Assess a standard in a course
@bp.get("/courses/<int:course_id>/standards/<int:standard_id>/assess")
@login_required
@restricted
def get_assessment_form(course_id, standard_id):
    if current_user.usertype_id == 2:
        abort(401)
    from feedbook.schemas import UserSchema

    course = Course.query.filter(Course.id == course_id).first()

    # Get the enrollments, alphabatized to start the loop
    enrollments = (
        course.enrollments.filter(User.usertype_id == 2, User.active == True)
        .order_by("last_name")
        .all()
    )

    # Get all assignments to add to the assessment form
    assignments = Assignment.query.all()

    return render_template(
        "standards/student-assessment-form.html",
        students=enrollments,
        standard_id=standard_id,
        course_id=course_id,
        assignments=assignments,
    )
