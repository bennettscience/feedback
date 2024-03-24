from flask import Blueprint, render_template, redirect, abort
from flask_login import current_user, login_required

from feedbook.extensions import db
from feedbook.models import Course

bp = Blueprint("home", __name__)


@bp.get("/")
@login_required
def index():
    courses = current_user.enrollments.all()
    return render_template("home/index.html", courses=courses)
