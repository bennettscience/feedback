from flask import Blueprint, render_template, redirect, abort
from flask_login import login_required
from feedbook.models import Course

bp = Blueprint("home", __name__)

@bp.get("/")
@login_required
def index():
    courses = Course.query.all()
    return render_template(
        "home/index.html",
        courses=courses
    )
