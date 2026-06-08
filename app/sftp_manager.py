"""SFTP Manager — remote file browsing, upload, download via SSH/expect."""
import os, json, tempfile, subprocess as sp
from datetime import datetime
from flask import (
    Blueprint, render_template, session, redirect, url_for,
    request, jsonify, send_file
)

sftp_bp = Blueprint('sftp', __name__)

SERVERS_FILE = '/root/EGC/data/sftp-servers.json'

def require_auth():
    return 'user' in session

def load_servers():
    if not os.path.exists(SERVERS_FILE):
        return []
    with open(SERVERS_FILE) as f:
        data = json.load(f)
    return data if isinstance(data, list) else []

def save_servers(servers):
    os.makedirs(os.path.dirname(SERVERS_FILE), exist_ok=True)
    with open(SERVERS_FILE, 'w') as f:
        json.dump(servers, f, indent=2, ensure_ascii=False)

def run_remote_cmd(host, port, user, password, cmd, timeout=15):
    """Execute a remote command via expect SSH, return (success, stdout_lines)."""
    if not password:
        r = sp.run(
            f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} "{cmd}"',
            shell=True, capture_output=True, text=True, timeout=timeout
        )
        return r.returncode == 0, r.stdout.strip().split('\n')

    fd, script = tempfile.mkstemp(suffix='.exp', text=True)
    with os.fdopen(fd, 'w') as f:
        f.write(f'set timeout {timeout}\n')
        f.write(f'spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} {cmd}\n')
        f.write(f'expect "password:"\n')
        f.write(f'send "{password}\\r"\n')
        f.write(f'expect eof\n')
    try:
        r = sp.run(['expect', '-f', script], capture_output=True, text=True, timeout=timeout+5)
        if r.returncode != 0:
            return False, []
        lines = [l.strip() for l in r.stdout.split('\n') if l.strip() and 'spawn' not in l and 'password' not in l.lower()]
        return True, lines
    except Exception:
        return False, []
    finally:
        os.unlink(script)

def scp_transfer(host, port, user, password, local, remote, to_remote=True, timeout=60):
    """SCP file transfer using expect. Returns (success, output)."""
    if to_remote:
        cmd = f'scp -o StrictHostKeyChecking=no -P {port} {local} {user}@{host}:{remote}'
    else:
        cmd = f'scp -o StrictHostKeyChecking=no -P {port} {user}@{host}:{remote} {local}'

    if not password:
        r = sp.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout

    fd, script = tempfile.mkstemp(suffix='.exp', text=True)
    with os.fdopen(fd, 'w') as f:
        f.write(f'set timeout {timeout}\n')
        f.write(f'spawn {cmd}\n')
        f.write(f'expect "password:"\n')
        f.write(f'send "{password}\\r"\n')
        f.write(f'expect eof\n')
    try:
        r = sp.run(['expect', '-f', script], capture_output=True, text=True, timeout=timeout+10)
        return r.returncode == 0, r.stdout
    except Exception:
        return False, ''
    finally:
        os.unlink(script)

# ---- Page ----
@sftp_bp.route('/sftp')
def index():
    if not require_auth():
        return redirect(url_for('auth.login'))
    servers = load_servers()
    return render_template('sftp.html', user=session['user'], servers=servers)

# ---- API: List servers ----
@sftp_bp.route('/api/sftp/servers', methods=['GET'])
def api_servers():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify({'servers': load_servers()})

@sftp_bp.route('/api/sftp/servers', methods=['DELETE'])
def api_delete_server():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    host = request.get_json().get('host', '')
    servers = [s for s in load_servers() if s['host'] != host]
    save_servers(servers)
    return jsonify({'ok': True})

# ---- API: Remote file list ----
@sftp_bp.route('/api/sftp/list', methods=['POST'])
def api_remote_list():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    host = data.get('host', '')
    port = int(data.get('port', 22))
    user = data.get('user', 'root')
    password = data.get('password', '')
    path = data.get('path', '/root').rstrip('/') or '/'

    if not host:
        return jsonify({'error': 'host required'}), 400

    # Save/update server record
    servers = load_servers()
    found = False
    for s in servers:
        if s['host'] == host:
            s.update({'port': port, 'user': user, 'password': password, 'last_used': datetime.now().isoformat()})
            found = True
            break
    if not found:
        servers.append({
            'host': host, 'port': port, 'user': user, 'password': password,
            'last_used': datetime.now().isoformat()
        })
    save_servers(servers)

    cmd = f"find {path} -maxdepth 1 -printf '%f\\t%y\\t%s\\t%T@\\n' 2>/dev/null | sort -t$'\\t' -k2,2r -k1,1"
    ok, lines = run_remote_cmd(host, port, user, password, cmd, timeout=10)
    if not ok:
        return jsonify({'error': 'SSH failed', 'entries': [], 'path': path}), 500

    entries = []
    for line in lines:
        if not line or line == '.':
            continue
        parts = line.split('\t')
        if len(parts) < 4:
            continue
        name, ftype, size_str, mtime_str = parts[0], parts[1], parts[2], parts[3]
        if name == '..':
            continue
        is_dir = (ftype == 'd')
        size = int(size_str) if not is_dir else 0
        try:
            mtime = datetime.fromtimestamp(float(mtime_str)).strftime('%m-%d %H:%M')
        except:
            mtime = ''
        entries.append({
            'name': name, 'is_dir': is_dir, 'size': size,
            'size_fmt': fmt_s(size), 'mtime': mtime,
            'full': os.path.join(path, name) if path != '/' else '/' + name
        })
    return jsonify({'entries': entries, 'path': path})

# ---- API: Upload (local → remote) ----
@sftp_bp.route('/api/sftp/upload', methods=['POST'])
def api_upload():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    host = request.form.get('host', '')
    port = int(request.form.get('port', 22))
    user = request.form.get('user', 'root')
    password = request.form.get('password', '')
    remote_path = request.form.get('path', '/root')

    if not host:
        return jsonify({'error': 'host required'}), 400

    uploaded = []
    for f in request.files.getlist('files'):
        if f.filename:
            local_tmp = os.path.join('/tmp', f'sftp_upload_{os.urandom(4).hex()}_{f.filename}')
            f.save(local_tmp)
            remote_full = os.path.join(remote_path.rstrip('/'), f.filename)
            ok, _ = scp_transfer(host, port, user, password, local_tmp, remote_full, to_remote=True, timeout=60)
            os.unlink(local_tmp)
            if ok:
                uploaded.append(f.filename)
    return jsonify({'uploaded': uploaded, 'count': len(uploaded)})

# ---- API: Download (remote → local) ----
@sftp_bp.route('/api/sftp/download', methods=['POST'])
def api_download():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    host = data.get('host', '')
    port = int(data.get('port', 22))
    user = data.get('user', 'root')
    password = data.get('password', '')
    remote_file = data.get('path', '')

    if not host or not remote_file:
        return jsonify({'error': 'host and path required'}), 400

    local_tmp = os.path.join('/tmp', f'sftp_down_{os.urandom(4).hex()}_{os.path.basename(remote_file)}')
    ok, _ = scp_transfer(host, port, user, password, local_tmp, remote_file, to_remote=False, timeout=120)
    if not ok:
        return jsonify({'error': 'SCP failed'}), 500

    return send_file(local_tmp, as_attachment=True, download_name=os.path.basename(remote_file))

def fmt_s(n):
    for u in ['B','KB','MB','GB']:
        if n < 1024: return f'{n:.1f}{u}' if u!='B' else f'{n}B'
        n /= 1024
    return f'{n:.1f}TB'
