from flask import abort, Blueprint, current_app, redirect, render_template, url_for
from flask_login import current_user, login_user, logout_user
from htmx_flask import make_response
from webargs import fields
from webargs.flaskparser import parser

from feedbook.blueprints import home
from feedbook.extensions import db
from feedbook.models import User

bp = Blueprint("auth", __name__)


@bp.get("/login")
def get_login():
    if current_user.is_authenticated:
        return redirect(url_for(home.index))

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
        return make_response(
            redirect="/login",
            trigger={"showToast": "Username or password incorrect"},
        )

    login_user(user, remember=args["remember_me"])
    return make_response(redirect=url_for("home.index"))


@bp.get("/register")
def get_register():
    return "Registrations are not open at this time.", 403
    # return render_template(
    #     "shared/forms/register.html"
    # )


@bp.post("/register")
def register():
    abort(403)
    # args = parser.parse({
    #     "email": fields.Str(),
    #     "last_name": fields.Str(),
    #     "first_name": fields.Str(),
    #     "password": fields.Str(),
    #     "password_again": fields.Str()
    # }, location="form")

    # if args['password'] != args['password_again']:
    #     return make_response(
    #         redirect(url_for('auth.get_register')),
    #         trigger={"showToast": "Your passwords do not match."}
    #     )
    # user = User.query.filter(User.email == args['email']).first()
    # if user:
    #     print(f"{args['email']} already exists")
    #     return render_template(
    #         "shared/partials/register-form.html",
    #         error="That email is unavailable"
    #     )

    # user = User(
    #     email=args['email'],
    #     last_name=args['last_name'],
    #     first_name=args['first_name'],
    #     usertype_id=2,
    # )
    # user.set_password(args['password'])
    # db.session.add(user)
    # db.session.commit()
    # login_user(user)

    # return make_response(
    #     redirect=url_for('home.index')
    #     )


@bp.get("/logout")
def logout():
    logout_user()
    return redirect(url_for("home.index"))
