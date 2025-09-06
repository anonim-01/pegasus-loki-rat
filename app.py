from flask import Flask
from server.api import api
from server.webui import webui
from server.models import db
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loki.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'server/webui/static/uploads'

# Initialize database
db.init_app(app)

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create database tables
with app.app_context():
    db.create_all()

# Register blueprints
app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(webui, url_prefix='/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
