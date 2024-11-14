from flask import abort, Blueprint, current_app, redirect, render_template, url_for
from flask_login import current_user, login_required
from htmx_flask import make_response

from feedbook.extensions import db
from feedbook.models import Standard, User
from feedbook.static.icons import *
from feedbook.wrappers import restricted

bp = Blueprint("admin", __name__)


@bp.get("/admin")
@login_required
@restricted
def index():
    icons = {"home": home, "add": add, "admin": admin, "logout": logout}
    return render_template("admin/index.html", icons=icons)
