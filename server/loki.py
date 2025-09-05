#!/usr/bin/env python2

import random
import string
import hashlib
from functools import wraps
import datetime
import os
import shutil
import tempfile
import sys

# Add server directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, current_app
from flask.cli import AppGroup, with_appcontext
from models import db, Agent, Command
from webui import webui
from api import api
from config import config

# Create the Flask application
app = Flask(__name__)
app.config.from_object(config['dev'])
app.register_blueprint(webui)
app.register_blueprint(api, url_prefix="/api")
db.init_app(app)

# Create CLI command group
cli = AppGroup('cli')

@app.after_request
def headers(response):
    response.headers["Server"] = "Loki"
    return response

@cli.command('initdb')
@with_appcontext
def initdb():
    db.drop_all()
    db.create_all()
    db.session.commit()
    print("Initialized the database.")

# Register CLI commands
app.cli.add_command(cli)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, threaded=True)