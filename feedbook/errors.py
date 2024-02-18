def unauthorized(err):
	return "You cannot access this page without logging in.", 401

def forbidden(err):
	return "You do not have access to this resource.", 403