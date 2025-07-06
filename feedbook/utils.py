from feedbook.extensions import db


def get_system_stats():
    from feedbook.models import Assignment, Standard, StandardAttempt, User

    # Go through each of the models and quantify main points
    # Assignments
    assignments = Assignment.query.count()

    # Standards
    standards = Standard.query.count()
    attempts = StandardAttempt.query.count()

    # Users
    users = User.query.count()
    active = User.query.filter(User.active == True).count()

    return {
        "assignments": {"created": assignments},
        "standards": {"created": standards, "assessments": attempts},
        "users": {"created": users, "active": active},
    }
