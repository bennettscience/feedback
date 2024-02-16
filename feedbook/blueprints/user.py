from collections import defaultdict

from flask import abort, Blueprint, render_template, redirect, abort
from flask_login import current_user, login_required

from htmx_flask import make_response

from feedbook.extensions import db
from feedbook.models import User
from feedbook.schemas import StandardAttemptSchema

bp = Blueprint('user', __name__)

@bp.get("/users/<int:user_id>")
@login_required
def get_user(user_id):
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
		scores_only=scores_only
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
