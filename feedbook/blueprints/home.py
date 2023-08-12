from flask import Blueprint, render_template, redirect, abort

from feedbook.models import Course

bp = Blueprint("home", __name__)

@bp.get("/")
def index():
    courses = Course.query.all()
    return render_template(
        "home/index.html",
        courses=courses
    )
