from collections import defaultdict

from flask import abort, Blueprint, render_template, redirect, abort
from flask_login import current_user, login_required
from htmx_flask import make_response
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Course, StandardAttempt, User
from feedbook.schemas import StandardAttemptSchema
from feedbook.wrappers import restricted

bp = Blueprint("user", __name__)


@bp.get("/users")
@login_required
@restricted
def index():
    users = User.query.all()
    return render_template("user/index.html", users=users)


# Set the user's active status
@bp.put("/users/<int:user_id>/status")
@login_required
@restricted
def deactivate_user(user_id):
    user = User.query.filter(User.id == user_id).first()

    user.active = not user.active
    db.session.commit()

    value = "Deactivate" if user.active else "Activate"
    return make_response(value, trigger={"showToast": "User status updated"})
