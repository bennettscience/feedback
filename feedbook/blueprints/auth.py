from flask import abort, Blueprint, redirect, request, render_template, url_for
from flask_login import current_user, login_user, logout_user
from htmx_flask import make_response
from webargs import fields
from webargs.flaskparser import parser

from feedbook.blueprints import home
from feedbook.extensions import db
from feedbook.static.icons import *
from feedbook.models import User

bp = Blueprint("auth", __name__)


@bp.get("/login")
def get_login():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))

    return render_template("shared/forms/login.html")


@bp.post("/login")
def login():
    args = parser.parse(
        {
            "email": fields.Str(),
            "password": fields.Str(),
            "remember_me": fields.Bool(load_default=False),
        },
        location="form",
    )

    user = User.query.filter(User.email == args["email"]).first()
    if user is None or not user.check_password(args["password"]):
        return (
            make_response(
                redirect="/login",
                trigger={"showToast": "Username or password incorrect"},
            ),
            401,
        )

    login_user(user, remember=args["remember_me"])
    return make_response(redirect=url_for("home.index"))


@bp.get("/register")
def get_register_form():
    print("getting registration form")
    return render_template("shared/forms/register-email.html")


@bp.post("/register")
def register():
    """
    Aug 2025
    Two step registration process. First check that the user's name and email
     are in the database. If the record exists, have them set a password.
     If not, abort the attempt.
    """
    reg_step = request.args.get("step")
    if reg_step == "veremail":
        args = parser.parse(
            {
                "email": fields.Str(),
                "last_name": fields.Str(),
                "first_name": fields.Str(),
            },
            location="form",
        )

        user = User.query.filter(
            User.email == args["email"],
            User.last_name.ilike(args["last_name"]),
            User.first_name.ilike(args["first_name"]),
        ).first()

        if not user:
            abort(403)

        # Check for an existing password. If it is saved, then don't allow the registration.
        if user.password_hash is not None:
            abort(403)

        result = render_template(
            "shared/forms/register.html",
            email=args["email"],
            first_name=args["first_name"],
        )
    else:
        args = parser.parse(
            {
                "email": fields.Str(),
                "password": fields.Str(),
                "password_again": fields.Str(),
            },
            location="form",
        )

        if args["password"] != args["password_again"]:
            return make_response(
                redirect(url_for("auth.get_register_form")),
                trigger={"showToast": "Your passwords do not match."},
            )

        user = User.query.filter(User.email == args["email"]).first()

        user.set_password(args["password"])
        db.session.add(user)
        db.session.commit()
        login_user(user)

        result = make_response(redirect=url_for("home.index"))

    return result


@bp.get("/logout")
def logout():
    from feedbook.static.icons import home, login

    icons = {"home": home, "login": login}
    logout_user()
    return redirect(url_for("home.index"))
