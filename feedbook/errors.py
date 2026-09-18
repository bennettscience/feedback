def unauthorized(err):
    return "You cannot access this page without logging in.", 401


def forbidden(err):
    return "You are not authorized to perform that action.", 403


def not_found(err):
    return err.description, 404

def server_error(err):
    return err.description, 500
