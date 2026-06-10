"""Edge-EMS Deploy Manager — V2: per-component tabs, split download/deploy."""
import os, sys, json, time, threading, subprocess as sp, tempfile
from datetime import datetime
from flask import (
    Blueprint, render_template, session, redirect, url_for,
    request, jsonify, current_app
)

ed_bp = Blueprint('ems_deploy', __name__)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'ems_deploy_assets')
DATA_DIR = '/root/EGC/data'
CONFIG_FILE = os.path.join(DATA_DIR, 'ems-deploy-config.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'ems-deploy-history.json')

COMPONENTS = ['edge-ems', 'edge-ems-hmi', 'edge-ems-hmi-fe']

BLOB_SERVER_DIR = {
    'edge-ems': {'HPUY': 'HPUY', 'EE': 'x86_64'},
    'edge-ems-hmi': {'HPUY': 'HPUY', 'EE': 'x86_64'},
    'edge-ems-hmi-fe': {'HPUY': 'logger', 'EE': 'app_portal'},
}

DEPLOY_DIRS = {
    'HPUY': {
        'edge-ems': '/root/EMS/edge-ems/',
        'edge-ems-hmi': '/root/EMS/edge-ems-hmi/',
        'edge-ems-hmi-fe': '/root/EMS/edge-ems-hmi/edge-ems-hmi-fe/',
    },
    'EE': {
        'edge-ems': '/home/envuser/energy-os/edge-ems/',
        'edge-ems-hmi': '/home/envuser/energy-os/edge-ems-hmi/',
        'edge-ems-hmi-fe': '/home/envuser/energy-os/edge-ems-hmi/edge-ems-hmi-fe/',
    },
}

FILE_TYPES = {
    'edge-ems': 'tar.gz',
    'edge-ems-hmi': 'tar.gz',
    'edge-ems-hmi-fe': 'zip',
}

def require_auth():
    return 'user' in session

def build_blob_path(component, branch, server):
    server_dir = BLOB_SERVER_DIR.get(component, {}).get(server, server)
    ext = FILE_TYPES[component]
    return f'edgeftpfile/{component}/{branch}/{server_dir}/{component}.{ext}'

def build_local_path(component, branch, server, mirror_dir):
    blob_path = build_blob_path(component, branch, server)
    return os.path.join(mirror_dir, blob_path)

# ============================================================
# Config
# ============================================================
DEFAULT_CONFIG = {
    'sas_token': '',
    'blob_mirror_dir': '/root/Blob',
    'servers': {
        'HPUY': {
            'ssh_user': 'admin',
            'ssh_password': '',
            'ssh_host': '',
            'ssh_port': 22,
        },
        'EE': {
            'ssh_user': 'root',
            'ssh_password': '',
            'ssh_host': '',
            'ssh_port': 22,
        },
    },
    'default_branch': 'develop_2605',
    'branches': ['develop_23', 'develop_24', 'develop_25', 'develop_2605'],
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def mask_config(config):
    c = dict(config)
    for name, srv in c.get('servers', {}).items():
        pw = srv.get('ssh_password', '')
        srv['ssh_password_masked'] = (pw[:4] + '****') if len(pw) > 4 else ('****' if pw else '')
        srv.pop('ssh_password', None)
    tok = c.get('sas_token', '')
    c['sas_token_masked'] = (tok[:12] + '...') if len(tok) > 12 else ('****' if tok else '')
    c.pop('sas_token', None)
    return c

# ============================================================
# History (per-component dict)
# ============================================================
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {comp: [] for comp in COMPONENTS}
    with open(HISTORY_FILE) as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    return {comp: [] for comp in COMPONENTS}

def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def add_history_record(component, record):
    history = load_history()
    if component not in history:
        history[component] = []
    history[component].insert(0, record)
    history[component] = history[component][:50]
    save_history(history)

# ============================================================
# Task progress (same pattern as simulator_manager)
# ============================================================
_tasks = {}
_task_lock = threading.Lock()

def _task_log(task_id, msg, status='running'):
    with _task_lock:
        if task_id not in _tasks:
            _tasks[task_id] = {'status': status, 'logs': []}
        _tasks[task_id]['logs'].append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'msg': msg,
        })
        _tasks[task_id]['status'] = status

# ============================================================
# SSH helpers
# ============================================================
def _ssh_run(host, port, user, password, cmd, task_id, timeout=30):
    if not password:
        r = sp.run(
            f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} "{cmd}"',
            shell=True, capture_output=True, text=True, timeout=timeout
        )
        if r.returncode != 0:
            _task_log(task_id, f'❌ {r.stderr.strip() or "SSH failed"}', 'error')
            return False
        for line in r.stdout.strip().split('\n'):
            if line.strip():
                _task_log(task_id, f'  {line.strip()}')
        return True
    fd, script_path = tempfile.mkstemp(suffix='.exp', text=True)
    with os.fdopen(fd, 'w') as f:
        f.write(f'set timeout {timeout}\n')
        f.write(f'spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} {cmd}\n')
        f.write('expect "password:"\n')
        f.write(f'send "{password}\\r"\n')
        f.write('expect eof\n')
    try:
        r = sp.run(['expect', '-f', script_path], capture_output=True, text=True, timeout=timeout + 10)
        if r.returncode != 0:
            _task_log(task_id, f'❌ {r.stderr.strip() or "SSH failed"}', 'error')
            return False
        for line in r.stdout.strip().split('\n'):
            line = line.strip()
            if line and 'spawn' not in line and 'password' not in line.lower():
                _task_log(task_id, f'  {line}')
        return True
    except sp.TimeoutExpired:
        _task_log(task_id, '❌ SSH 超时', 'error')
        return False
    except Exception as e:
        _task_log(task_id, f'❌ {e}', 'error')
        return False
    finally:
        os.unlink(script_path)

def _sudo_ssh_run(host, port, user, password, cmd, task_id, timeout=60):
    script_name = f'_omo_{os.urandom(4).hex()}.sh'
    escaped = cmd.replace("'", "'\\''")
    write_and_exec = f"echo '{escaped}' > /tmp/{script_name} && sudo bash /tmp/{script_name} && rm -f /tmp/{script_name}"
    return _ssh_run(host, port, user, password, write_and_exec, task_id, timeout=timeout)

def _scp_to_remote(local_file, host, port, user, password, remote_path, task_id, timeout=120):
    _task_log(task_id, f'📤 上传 {os.path.basename(local_file)} → {host}:{remote_path}')
    if not password:
        r = sp.run(
            f'scp -o StrictHostKeyChecking=no -P {port} {local_file} {user}@{host}:{remote_path}',
            shell=True, capture_output=True, text=True, timeout=timeout
        )
        if r.returncode != 0:
            _task_log(task_id, f'❌ SCP 失败: {r.stderr.strip()}', 'error')
            return False
        _task_log(task_id, '  ✅ 上传完成')
        return True
    fd, script_path = tempfile.mkstemp(suffix='.exp', text=True)
    with os.fdopen(fd, 'w') as f:
        f.write(f'set timeout {timeout}\n')
        f.write(f'spawn scp -o StrictHostKeyChecking=no -P {port} {local_file} {user}@{host}:{remote_path}\n')
        f.write('expect "password:"\n')
        f.write(f'send "{password}\\r"\n')
        f.write('expect eof\n')
    try:
        r = sp.run(['expect', '-f', script_path], capture_output=True, text=True, timeout=timeout + 10)
        if r.returncode != 0:
            _task_log(task_id, f'❌ SCP 失败', 'error')
            return False
        _task_log(task_id, '  ✅ 上传完成')
        return True
    except sp.TimeoutExpired:
        _task_log(task_id, '❌ SCP 超时', 'error')
        return False
    except Exception as e:
        _task_log(task_id, f'❌ {e}', 'error')
        return False
    finally:
        os.unlink(script_path)

# ============================================================
# Download thread: Blob → local
# ============================================================
def _download_thread(task_id, component, branch, server, config):
    start_time = time.time()
    sas_token = config.get('sas_token', '')
    mirror_dir = config.get('blob_mirror_dir', '/root/Blob')
    blob_path = build_blob_path(component, branch, server)
    local_path = build_local_path(component, branch, server, mirror_dir)
    blob_url = f'https://edgeadls2.blob.core.chinacloudapi.cn/edge/{blob_path}?{sas_token}'

    _task_log(task_id, f'🚀 开始下载 {component} ({branch} → {server})')
    _task_log(task_id, f'📡 Blob: {blob_path}')
    _task_log(task_id, f'💾 本地: {local_path}')

    if not sas_token:
        _task_log(task_id, '❌ SAS Token 未配置，请在连接配置中填写', 'error')
        add_history_record(component, {
            'id': task_id, 'timestamp': datetime.now().isoformat(),
            'branch': branch, 'server': server, 'action': 'download',
            'status': 'error', 'duration_seconds': 0,
        })
        return

    _task_log(task_id, '🔍 检查 Blob 文件...')
    try:
        info = _blob_head(blob_path, sas_token)
        if not info.get('exists'):
            _task_log(task_id, f'❌ Blob 文件不存在: {blob_path}', 'error')
            _task_log(task_id, f'⚠️ 请确认分支 [{branch}] 和服务器 [{server}] 是否正确', 'warning')
            add_history_record(component, {
                'id': task_id, 'timestamp': datetime.now().isoformat(),
                'branch': branch, 'server': server, 'action': 'download',
                'status': 'error', 'duration_seconds': 0,
            })
            return
        blob_size = info.get('size', 0)
        if blob_size > 0:
            _task_log(task_id, f'  ✅ Blob 文件存在 ({fmt_size(blob_size)})')
    except Exception as e:
        _task_log(task_id, f'⚠️ Blob 检查失败: {str(e)[:60]}，尝试直接下载', 'warning')

    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    _task_log(task_id, '⬇ 下载中...')
    try:
        r = sp.run(
            ['curl', '-L', '-o', local_path, '-w', '%{http_code}', blob_url],
            capture_output=True, text=True, timeout=600
        )
        http_code = r.stdout.strip() if r.stdout else ''
        if r.returncode != 0:
            _task_log(task_id, f'❌ 下载失败: {r.stderr.strip()}', 'error')
            if os.path.exists(local_path):
                os.remove(local_path)
            add_history_record(component, {
                'id': task_id, 'timestamp': datetime.now().isoformat(),
                'branch': branch, 'server': server, 'action': 'download',
                'status': 'error', 'duration_seconds': int(time.time() - start_time),
            })
            return
        if http_code and http_code.startswith('4'):
            _task_log(task_id, f'❌ Blob 返回 HTTP {http_code}，文件不存在或无权限', 'error')
            _task_log(task_id, f'⚠️ 请确认分支 [{branch}] 和服务器 [{server}] 是否正确', 'warning')
            if os.path.exists(local_path):
                os.remove(local_path)
            add_history_record(component, {
                'id': task_id, 'timestamp': datetime.now().isoformat(),
                'branch': branch, 'server': server, 'action': 'download',
                'status': 'error', 'duration_seconds': int(time.time() - start_time),
            })
            return
    except sp.TimeoutExpired:
        _task_log(task_id, '❌ 下载超时', 'error')
        if os.path.exists(local_path):
            os.remove(local_path)
        return

    if not os.path.exists(local_path) or os.path.getsize(local_path) < 100:
        _task_log(task_id, '❌ 下载文件无效或过小', 'error')
        _task_log(task_id, '⚠️ 可能 SAS Token 无效或 Blob 路径错误', 'warning')
        if os.path.exists(local_path):
            os.remove(local_path)
        add_history_record(component, {
            'id': task_id, 'timestamp': datetime.now().isoformat(),
            'branch': branch, 'server': server, 'action': 'download',
            'status': 'error', 'duration_seconds': int(time.time() - start_time),
        })
        return

    size = os.path.getsize(local_path)
    elapsed = int(time.time() - start_time)
    _task_log(task_id, f'✅ 下载完成 ({fmt_size(size)}) 耗时 {elapsed}s', 'completed')
    add_history_record(component, {
        'id': task_id, 'timestamp': datetime.now().isoformat(),
        'branch': branch, 'server': server, 'action': 'download',
        'status': 'completed', 'duration_seconds': elapsed,
        'file_size': size,
    })

# ============================================================
# Deploy thread: local → remote server
# ============================================================
def _deploy_thread(task_id, component, branch, server, config):
    start_time = time.time()
    mirror_dir = config.get('blob_mirror_dir', '/root/Blob')
    local_path = build_local_path(component, branch, server, mirror_dir)
    srv = config.get('servers', {}).get(server, {})
    host = srv.get('ssh_host', '')
    port = int(srv.get('ssh_port', 22))
    user = srv.get('ssh_user', '')
    password = srv.get('ssh_password', '')
    remote_dir = DEPLOY_DIRS.get(server, {}).get(component, '/tmp/')
    need_sudo = (server == 'HPUY')

    _task_log(task_id, f'🚀 开始部署 {component} → {server} ({host})')
    _task_log(task_id, f'📦 本地文件: {local_path}')
    _task_log(task_id, f'📂 远程目录: {remote_dir}')
    if need_sudo:
        _task_log(task_id, f'🔐 模式: sudo (用户 {user} 非root)')

    # Pre-check: local file
    if not os.path.exists(local_path):
        _task_log(task_id, '❌ 本地文件不存在，请先下载', 'error')
        add_history_record(component, {
            'id': task_id, 'timestamp': datetime.now().isoformat(),
            'branch': branch, 'server': server, 'action': 'deploy',
            'status': 'error', 'duration_seconds': 0,
        })
        return

    size = os.path.getsize(local_path)
    _task_log(task_id, f'  文件大小: {fmt_size(size)}')

    if not host:
        _task_log(task_id, '❌ 服务器未配置', 'error')
        add_history_record(component, {
            'id': task_id, 'timestamp': datetime.now().isoformat(),
            'branch': branch, 'server': server, 'action': 'deploy',
            'status': 'error', 'duration_seconds': 0,
        })
        return

    # Pre-check: SSH connectivity
    _task_log(task_id, '🔍 检查 SSH 连接...')
    if not _ssh_run(host, port, user, password, 'whoami', task_id, timeout=10):
        _task_log(task_id, '❌ SSH 连接失败，请检查服务器配置', 'error')
        add_history_record(component, {
            'id': task_id, 'timestamp': datetime.now().isoformat(),
            'branch': branch, 'server': server, 'action': 'deploy',
            'status': 'error', 'duration_seconds': int(time.time() - start_time),
        })
        return
    _task_log(task_id, '  ✅ SSH 连接正常')

    # Pre-check: sudo availability for HPUY
    if need_sudo:
        _task_log(task_id, '🔍 检查 sudo 权限...')
        if not _sudo_ssh_run(host, port, user, password, 'whoami', task_id, timeout=10):
            _task_log(task_id, '❌ sudo 权限不可用，请检查用户 sudo 权限', 'error')
            add_history_record(component, {
                'id': task_id, 'timestamp': datetime.now().isoformat(),
                'branch': branch, 'server': server, 'action': 'deploy',
                'status': 'error', 'duration_seconds': int(time.time() - start_time),
            })
            return
        _task_log(task_id, '  ✅ sudo 权限正常')

    # Upload to /tmp on remote
    remote_tmp = f'/tmp/{os.path.basename(local_path)}'
    if not _scp_to_remote(local_path, host, port, user, password, remote_tmp, task_id):
        add_history_record(component, {
            'id': task_id, 'timestamp': datetime.now().isoformat(),
            'branch': branch, 'server': server, 'action': 'deploy',
            'status': 'error', 'duration_seconds': int(time.time() - start_time),
        })
        return

    # Extract on remote
    _task_log(task_id, '📂 远程解压...')
    ext = FILE_TYPES[component]
    if ext == 'zip':
        extract_cmd = f'mkdir -p {remote_dir} && cd {remote_dir} && unzip -o {remote_tmp} && rm -f {remote_tmp}'
    else:
        extract_cmd = f'mkdir -p {remote_dir} && cd {remote_dir} && tar xzf {remote_tmp} --strip-components=1 && rm -f {remote_tmp}'

    run_fn = _sudo_ssh_run if need_sudo else _ssh_run
    if not run_fn(host, port, user, password, extract_cmd, task_id, timeout=120):
        add_history_record(component, {
            'id': task_id, 'timestamp': datetime.now().isoformat(),
            'branch': branch, 'server': server, 'action': 'deploy',
            'status': 'error', 'duration_seconds': int(time.time() - start_time),
        })
        return
    _task_log(task_id, '  ✅ 解压完成')

    # Fix permissions
    _task_log(task_id, '🔐 修复权限...')
    if need_sudo:
        _sudo_ssh_run(host, port, user, password, f'chown -R root:root {remote_dir}', task_id, timeout=15)
    else:
        _ssh_run(host, port, user, password, f'chown -R envuser:envuser {remote_dir}', task_id, timeout=15)
    _task_log(task_id, '  ✅ 权限修复完成')

    elapsed = int(time.time() - start_time)
    _task_log(task_id, f'🎉 部署完成! 耗时 {elapsed}s', 'completed')
    add_history_record(component, {
        'id': task_id, 'timestamp': datetime.now().isoformat(),
        'branch': branch, 'server': server, 'action': 'deploy',
        'status': 'completed', 'duration_seconds': elapsed,
    })

# ============================================================
# Blob client
# ============================================================
def _blob_head(blob_path, sas_token):
    url = f'https://edgeadls2.blob.core.chinacloudapi.cn/edge/{blob_path}?{sas_token}'
    r = sp.run(['curl', '-sI', url], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise RuntimeError('curl failed')
    headers = r.stdout.lower()
    if '200 ok' in headers.split('\n')[0] if headers else '':
        size = 0
        for line in headers.split('\n'):
            if line.startswith('content-length:'):
                size = int(line.split(':')[1].strip())
        return {'exists': True, 'size': size}
    status_line = r.stdout.split('\n')[0] if r.stdout else ''
    if '200' in status_line:
        size = 0
        for line in r.stdout.split('\n'):
            if line.lower().startswith('content-length:'):
                size = int(line.split(':')[1].strip())
        return {'exists': True, 'size': size}
    return {'exists': False, 'size': 0}

# ============================================================
# Routes
# ============================================================

@ed_bp.route('/ems-deploy')
def index():
    if not require_auth():
        return redirect(url_for('auth.login'))
    return render_template('ems_deploy.html', user=session['user'])

@ed_bp.route('/api/ems-deploy/config', methods=['GET'])
def api_get_config():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify({'config': mask_config(load_config())})

@ed_bp.route('/api/ems-deploy/config', methods=['POST'])
def api_save_config():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    config = load_config()
    if data.get('sas_token') and '****' not in data['sas_token']:
        config['sas_token'] = data['sas_token']
    if 'blob_mirror_dir' in data:
        config['blob_mirror_dir'] = data['blob_mirror_dir']
    if 'branches' in data:
        config['branches'] = data['branches']
    if 'servers' in data:
        for srv_name, srv_data in data['servers'].items():
            if srv_name not in config['servers']:
                config['servers'][srv_name] = dict(DEFAULT_CONFIG['servers'].get(srv_name, {}))
            for key in ('ssh_user', 'ssh_host', 'ssh_port'):
                if key in srv_data:
                    config['servers'][srv_name][key] = srv_data[key]
            if srv_data.get('ssh_password') and '****' not in srv_data['ssh_password']:
                config['servers'][srv_name]['ssh_password'] = srv_data['ssh_password']
    save_config(config)
    return jsonify({'ok': True})

@ed_bp.route('/api/ems-deploy/test-blob', methods=['POST'])
def api_test_blob():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    config = load_config()
    sas = config.get('sas_token', '')
    if not sas:
        return jsonify({'ok': False, 'error': 'SAS Token 未配置'})
    try:
        info = _blob_head('edgeftpfile/', sas)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:100]})

@ed_bp.route('/api/ems-deploy/blob-info', methods=['POST'])
def api_blob_info():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    component = data.get('component', '')
    branch = data.get('branch', '')
    server = data.get('server', 'HPUY')
    if component not in COMPONENTS:
        return jsonify({'error': '无效组件'}), 400

    config = load_config()
    sas = config.get('sas_token', '')
    if not sas:
        return jsonify({'error': 'SAS Token 未配置'}), 400

    blob_path = build_blob_path(component, branch, server)
    local_path = build_local_path(component, branch, server, config.get('blob_mirror_dir', '/root/Blob'))

    result = {
        'component': component,
        'branch': branch,
        'server': server,
        'blob_path': blob_path,
        'local_path': local_path,
        'remote_dir': DEPLOY_DIRS.get(server, {}).get(component, ''),
        'file_type': FILE_TYPES.get(component, ''),
    }

    try:
        info = _blob_head(blob_path, sas)
        result['blob_exists'] = info.get('exists', False)
        result['blob_size'] = info.get('size', 0)
        result['blob_size_fmt'] = fmt_size(result['blob_size'])
    except Exception as e:
        result['blob_exists'] = False
        result['blob_error'] = str(e)[:80]

    result['local_exists'] = os.path.exists(local_path)
    if result['local_exists']:
        sz = os.path.getsize(local_path)
        result['local_size'] = sz
        result['local_size_fmt'] = fmt_size(sz)
        mtime = os.path.getmtime(local_path)
        result['local_mtime'] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')

    return jsonify(result)

@ed_bp.route('/api/ems-deploy/blob-download', methods=['POST'])
def api_blob_download():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    component = data.get('component', '')
    branch = data.get('branch', '')
    server = data.get('server', 'HPUY')
    if component not in COMPONENTS:
        return jsonify({'error': '无效组件'}), 400
    if not branch:
        return jsonify({'error': '分支不能为空'}), 400

    config = load_config()
    task_id = f'dl-{os.urandom(4).hex()}'
    t = threading.Thread(target=_download_thread, args=(task_id, component, branch, server, config))
    t.daemon = True
    t.start()
    return jsonify({'task_id': task_id})

@ed_bp.route('/api/ems-deploy/deploy', methods=['POST'])
def api_deploy():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    component = data.get('component', '')
    branch = data.get('branch', '')
    server = data.get('server', 'HPUY')
    if component not in COMPONENTS:
        return jsonify({'error': '无效组件'}), 400
    if not branch:
        return jsonify({'error': '分支不能为空'}), 400

    config = load_config()
    task_id = f'dep-{os.urandom(4).hex()}'
    t = threading.Thread(target=_deploy_thread, args=(task_id, component, branch, server, config))
    t.daemon = True
    t.start()
    return jsonify({'task_id': task_id})

@ed_bp.route('/api/ems-deploy/task-status/<task_id>')
def api_task_status(task_id):
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    with _task_lock:
        task = _tasks.get(task_id, {'status': 'not_found', 'logs': []})
    return jsonify(task)

@ed_bp.route('/api/ems-deploy/history/<component>')
def api_history(component):
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    history = load_history()
    return jsonify({'history': history.get(component, [])})

@ed_bp.route('/api/ems-deploy/history/<component>/<hid>', methods=['DELETE'])
def api_delete_history(component, hid):
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    history = load_history()
    if component in history:
        history[component] = [h for h in history[component] if h.get('id') != hid]
        save_history(history)
    return jsonify({'ok': True})

# ============================================================
# Helpers
# ============================================================
def fmt_size(n):
    for u in ['B', 'KB', 'MB', 'GB']:
        if n < 1024:
            return f'{n:.1f}{u}' if u != 'B' else f'{n}B'
        n /= 1024
    return f'{n:.1f}TB'
