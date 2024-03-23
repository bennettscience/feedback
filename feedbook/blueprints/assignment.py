from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required
from htmx_flask import make_response
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Assignment
from feedbook.wrappers import restricted

bp = Blueprint("assignment", __name__)


@bp.get("/assignments")
def index():
    assignments = db.session.scalars(db.select(Assignment)).all()

    return render_template("shared/admin_list.html", items=assignments)


@bp.post("/assignments")
@login_required
@restricted
def create_assignment():
    args = parser.parse(
        {
            "name": fields.String(),
            "description": fields.String(),
        },
        location="form",
    )

    # Assignments don't need to be added to a specific course becuase any assignment can be attached to a standard attempt.
    assignment = Assignment(name=args["name"])
    db.session.add(assignment)
    db.session.commit()

    # Return the full list of assignments to the admin page
    assignments = db.session.scalars(db.select(Assignment)).all()

    return make_response(trigger={"showToast": "Assignment added"})


@bp.get("/assignments/create")
@login_required
@restricted
def create_assignment_form():
    return render_template(
        "course/right-sidebar.html",
        title="Create a new assignment",
        position="right",
        partial="shared/forms/create-assignment.html",
        data={},
    )


@bp.get("/assignments/<int:id>")
def get_single_assignment(id):
    item = db.session.get(Assignment, id)

    return render_template("assignments/assignment_detail.html", assignment=item)
