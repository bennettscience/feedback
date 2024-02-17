from collections import defaultdict

from flask import abort, Blueprint, render_template, redirect, abort
from flask_login import current_user, login_required
from htmx_flask import make_response
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Course, StandardAttempt, User
from feedbook.schemas import StandardAttemptSchema


bp = Blueprint('user', __name__)

@bp.get("/users/<int:user_id>")
@login_required
def get_user(user_id):
	args = parser.parse({
		"course_id": fields.Int()
	}, location="querystring")
	user = User.query.filter(User.id == user_id).first()

	standards = defaultdict(list)
	scores_only = defaultdict(list)

	for a in user.assessments.all():
		standards[a.standard.name].append(
			{
				'assignment': a.assignment,
				'score': a.score,
				'occurred': a.occurred
			}
		)
		scores_only[a.standard.name].append(a.score)
	return render_template(
		"user/index.html",
		user=user,
		standards=standards,
		scores_only=scores_only,
		course_id=args["course_id"]
	)

@bp.get("/users/<int:user_id>/assess")
def get_user_assess_form(user_id):
	# Get each of the standards and return an array to the template
	args = parser.parse({
		"course_id": fields.Int()
	}, location="querystring") 

	course = Course.query.filter(Course.id == args["course_id"]).first()
	standards = course.standards.all()

	return render_template(
		"user/assess-form.html",
		standards=standards,
		user_id=user_id
	)

@bp.post("/users/<int:user_id>/assess")
def assess_single_user(user_id):
	args = parser.parse({
			"standard_id": fields.Int(),
			"assignment": fields.Str(),
			"score": fields.Int(),
			"comments": fields.Str()
		}, location="form")

	sa = StandardAttempt(
		user_id=user_id,
		standard_id=args["standard_id"],
		score=args["score"],
		assignment=args["assignment"],
		comments=args["comments"]
	)

	db.session.add(sa)
	db.session.commit()

	return make_response(
		"ok"
	)

@bp.put("/users/<int:user_id>/status")
@login_required
def deactivate_user(user_id):
	user = User.query.filter(User.id == user_id).first()

	user.active = not user.active;
	db.session.commit()

	value = "Deactivate" if user.active else "Activate"
	return make_response(
		value,
        trigger={"showToast": "User status updated" }
    )
