from collections import defaultdict

from flask import abort, Blueprint, render_template, redirect, abort, request
from flask_login import current_user, login_required
from htmx_flask import make_response
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Course, StandardAttempt, User
from feedbook.schemas import StandardAttemptSchema
from feedbook.wrappers import restricted

bp = Blueprint("user", __name__)

# Admin view of all users
@bp.get("/admin/users")
@login_required
@restricted
def index():
    stmt = db.select(User).where(User.usertype_id == 2).order_by(User.last_name)
    users = db.session.scalars(stmt).all()

    resp_data = {
        "users": users
    }

    template = "user/index.html"

    if request.htmx:
        resp = render_template(template, **resp_data)
    else:
        resp = render_template(
            "shared/layout_wrapper.html", partial=template, data=resp_data
        )

    # return resp
    return render_template("user/index.html", users=users)


# Get a single user
@bp.get("/users/<int:user_id>")
@login_required
@restricted
def get_user(user_id):
    # args = parser.parse({"user_id": fields.Int()}, location="querystring")
    # course = Course.query.filter(Course.id == course_id).first()
    stmt = db.select(User).where(User.id == user_id)
    user = db.session.scalar(stmt)
    if not user:
        abort(404)

    # user = User.query.filter(User.id == args["user_id"]).first()
    standards = defaultdict(dict)

    for a in user.assessments.all():
        standards[a.standard.name]["is_proficient"] = a.standard.is_proficient(user)
        standards[a.standard.name]["id"] = a.standard.id
        standards[a.standard.name].setdefault("assessments", []).append(
            {
                "id": a.id,
                "assignment": a.assessed_on,
                "score": a.score,
                "occurred": a.occurred,
                "comments": a.comments,
            }
        )

    template = "user/user-index.html"
    resp_data = {
        "user": user,
        "standards": standards,
    }

    return render_template("user/user-index.html", user=user, standards=standards)


# Set the user's active status
@bp.put("/users/<int:user_id>/status")
@login_required
@restricted
def deactivate_user(user_id):
    user = User.query.filter(User.id == user_id).first()

    if not user:
        abort(404)

    user.active = not user.active
    db.session.commit()

    value = "Deactivate" if user.active else "Activate"
    return make_response(value, trigger={"showToast": "User status updated"})
