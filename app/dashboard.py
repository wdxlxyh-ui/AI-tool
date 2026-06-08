"""Dashboard blueprint — main overview page."""
import os, time, shutil, subprocess as sp
from flask import Blueprint, render_template, session, redirect, url_for, current_app, request, jsonify

dashboard_bp = Blueprint('dashboard', __name__)

def require_auth():
    if 'user' not in session:
        return False
    return True

def get_system_stats(base_dir):
    stats = {}
    file_count = 0
    try:
        for entry in os.scandir(base_dir):
            if entry.name.startswith('.'): continue
            file_count += 1
    except OSError: pass
    stats['file_count'] = file_count

    try:
        usage = shutil.disk_usage(base_dir)
        stats['disk_total'] = usage.total
        stats['disk_used'] = usage.used
        stats['disk_free'] = usage.free
        stats['disk_percent'] = round(usage.used / usage.total * 100, 1)
    except OSError:
        stats['disk_total'] = stats['disk_used'] = stats['disk_free'] = 0
        stats['disk_percent'] = 0

    # CPU load
    try:
        with open('/proc/loadavg') as f:
            stats['cpu_load'] = f.read().split()[0]
    except: stats['cpu_load'] = '0'

    # RAM
    try:
        with open('/proc/meminfo') as f:
            mem = f.read()
        total = int([l for l in mem.split('\n') if 'MemTotal' in l][0].split()[1])
        avail = int([l for l in mem.split('\n') if 'MemAvailable' in l][0].split()[1])
        stats['ram_total'] = f'{total//1024}'
        stats['ram_used'] = f'{(total-avail)//1024}'
        stats['ram_percent'] = round((total-avail)/total*100)
    except:
        stats['ram_total'] = '0'; stats['ram_used'] = '0'; stats['ram_percent'] = 0

    try:
        with open('/proc/uptime') as f:
            s = float(f.read().split()[0])
            d = int(s//86400); h = int((s%86400)//3600)
            stats['uptime'] = f'{d}天{h}小时'
    except: stats['uptime'] = '未知'

    stats['tool_count'] = 6
    return stats

@dashboard_bp.route('/dashboard')
def index():
    if not require_auth():
        return redirect(url_for('auth.login'))
    stats = get_system_stats(current_app.config['BASE_DIR'])
    return render_template('dashboard.html', stats=stats, user=session['user'])

@dashboard_bp.route('/api/system/opencode-control', methods=['POST'])
def opencode_control():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    action = request.get_json().get('action', '')
    if action not in ('start','stop','restart'):
        return jsonify({'error': 'invalid action'}), 400
    try:
        r = sp.run(['systemctl', action, 'opencode-web'], capture_output=True, text=True, timeout=10)
        return jsonify({'ok': r.returncode == 0, 'output': r.stdout.strip()[:200]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/system/hermes-control', methods=['POST'])
def hermes_control():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    action = request.get_json().get('action', '')
    if action not in ('start','stop','restart'):
        return jsonify({'error': 'invalid action'}), 400
    try:
        r = sp.run(['systemctl', action, 'hermes-web-ui'], capture_output=True, text=True, timeout=10)
        return jsonify({'ok': r.returncode == 0, 'output': r.stdout.strip()[:200]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
