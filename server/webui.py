from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, request, send_from_directory
from models import db, Agent

webui = Blueprint('webui', __name__)

def require_admin(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For now, we'll allow all requests - you can implement proper auth later
        # if 'admin' not in session:
        #     return redirect(url_for('webui.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@webui.route('/')
def index():
    """Main dashboard showing all agents"""
    agents = Agent.query.all()
    return render_template('index.html', agents=agents)

@webui.route('/agent/<agent_id>')
@require_admin
def agent_detail(agent_id):
    """Show details for a specific agent"""
    agent = Agent.query.get_or_404(agent_id)
    return render_template('agent_detail.html', agent=agent)

@webui.route('/uploads/<path:path>')
def uploads(path):
    """Serve uploaded files"""
    return send_from_directory('static/uploads', path)
