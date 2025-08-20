def unauthorized(err):
    return "You cannot access this page without logging in.", 401


def forbidden(err):
    return "You do not have access to this resource.", 403


def not_found(err):
    return "That action wasn't found.", 404
