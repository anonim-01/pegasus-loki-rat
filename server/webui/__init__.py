from flask import Blueprint

webui = Blueprint('webui', __name__, template_folder='templates')

from functools import wraps
from flask import session, redirect, url_for, request

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('webui.login', next=request.url))
        # Here you would check if the user is an admin
        # For now, we'll just check if the user is logged in
        return f(*args, **kwargs)
    return decorated_function


