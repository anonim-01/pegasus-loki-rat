from flask import render_template
from . import webui, require_admin
from ..models import Smartphone, Backup

@webui.route('/smartphones')
@require_admin
def smartphone_list():
    smartphones = Smartphone.query.all()
    return render_template('smartphones.html', smartphones=smartphones)

@webui.route('/backups')
@require_admin
def backup_list():
    backups = Backup.query.all()
    return render_template('backups.html', backups=backups)

