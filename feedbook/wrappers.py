from functools import wraps
from flask import abort, request, render_template
from flask_login import current_user


def templated(template=None):
	def decorator(f):
		@wraps(f)
		def decorated_function(*args, **kwargs):
			template_name = template
			ctx = f(*args, **kwargs)
			if request.htmx:
				resp = render_template(template_name, **ctx)
			else:
				resp = render_template(
					"shared/layout-wrap.html", 
					partial=template_name, 
					data=ctx
				)
			return resp
		return decorated_function
	return decorator

def restricted(func):
	@wraps(func)
	def __restricted(*args, **kwargs):
		if current_user.is_anonymous:
			abort(401)
		if current_user.usertype_id == 2: 
			abort(403)
		return func(*args, **kwargs)
	return __restricted
	