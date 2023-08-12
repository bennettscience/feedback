from flask import Blueprint, render_template
from webargs import fields
from webargs.flaskparser import parser

from feedbook.extensions import db
from feedbook.models import Standard, StandardAttempt


bp = Blueprint("standard", __name__)

# Admin view of all standards
@bp.get("/standards")
def all_standards():
    standards = Standard.query.all()
    return render_template(
        "standards/index.html",
        standards=standards
    )

# Create new standard
@bp.get("/standards/create")
def get_create_standard_form():
    return render_template(
        "shared/forms/create-standard.html"
    )

@bp.post("/standards")
def create_standard():
    args = parser.parse({
        "name": fields.String(),
        "description": fields.String()
    }, location="form")

    standard = Standard(name=args["name"], description=args["description"])
    db.session.add(standard)
    db.session.commit()

    standards = Standard.query.all()
    return render_template(
        "standards/index.html",
        standards=standards
    )

# Get a single standard
@bp.get("/standards/<int:id>")
def get_single_standard(id):
    standard = Standard.query.filter(Standard.id == id).first()
    return render_template(
        "standards/single-standard.html",
        standard=standard
    )