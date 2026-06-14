"""IEC104 Simulator Manager — deploy, upgrade, remote management."""
import os, re, json, time, glob, shutil, threading, subprocess as sp, tempfile
from datetime import datetime
from flask import (
    Blueprint, render_template, session, redirect, url_for,
    request, jsonify, current_app
)

sm_bp = Blueprint('simulator', __name__)

# ============================================================
# Config
# ============================================================
DIST_DIR = '/root/IEC-SIM/iec104-sim-master/dist'
DEPLOY_DIR = '/home/envuser/IEC/gridsim'
BACKUP_DIR = os.path.join(DEPLOY_DIR, 'backups')
DATA_FILE = '/root/EGC/data/sim-deployments.json'

PKG_PATTERN = re.compile(r'gridsim-v(.+)-linux-amd64\.tar\.gz$')

def require_auth():
    if 'user' not in session:
        return False
    return True

# ============================================================
# Helpers
# ============================================================
def load_servers():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)

def save_servers(servers):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(servers, f, indent=2, ensure_ascii=False)

def parse_version(filename):
    m = PKG_PATTERN.search(filename)
    return m.group(1) if m else None

def get_available_versions():
    versions = []
    if not os.path.isdir(DIST_DIR):
        return versions
    for f in sorted(os.listdir(DIST_DIR), reverse=True):
        ver = parse_version(f)
        if ver:
            fpath = os.path.join(DIST_DIR, f)
            sz = os.path.getsize(fpath)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            versions.append({
                'version': ver,
                'filename': f,
                'size': sz,
                'size_fmt': fmt_size(sz),
                'mtime': mtime.strftime('%Y-%m-%d %H:%M'),
            })
    return versions

def fmt_size(n):
    for u in ['B','KB','MB','GB']:
        if n < 1024: return f'{n:.1f}{u}' if u!='B' else f'{n}B'
        n /= 1024
    return f'{n:.1f}TB'

# ============================================================
# Deploy thread progress store
# ============================================================
_deploy_tasks = {}
_task_lock = threading.Lock()

def _task_log(task_id, msg, status='running'):
    with _task_lock:
        if task_id not in _deploy_tasks:
            _deploy_tasks[task_id] = {'status': status, 'logs': []}
        _deploy_tasks[task_id]['logs'].append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'msg': msg,
        })
        _deploy_tasks[task_id]['status'] = status

def _run_cmd(cmd, task_id, timeout=30):
    """Run shell command, log output."""
    try:
        r = sp.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            err = r.stderr.strip() or r.stdout.strip() or f'exit code {r.returncode}'
            _task_log(task_id, f'❌ {err}', 'error')
            return False
        out = r.stdout.strip()
        if out:
            _task_log(task_id, out)
        return True
    except sp.TimeoutExpired:
        _task_log(task_id, '❌ 命令超时', 'error')
        return False
    except Exception as e:
        _task_log(task_id, f'❌ {e}', 'error')
        return False

SERVICE_NAME = 'gridsim'

# ============================================================
# Service management helpers
# ============================================================

def _try_cmd(cmd, timeout=30):
    """Run command silently. Returns (success, stdout, stderr). No logging."""
    try:
        r = sp.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except sp.TimeoutExpired:
        return False, '', 'timeout'
    except Exception as e:
        return False, '', str(e)


def _systemd_unit_path():
    return f'/etc/systemd/system/{SERVICE_NAME}.service'


def _systemd_unit_exists():
    return os.path.exists(_systemd_unit_path())


def _ensure_systemd_service(task_id):
    """Create or migrate systemd unit for gridsim. Never fails the deploy."""
    unit_path = _systemd_unit_path()

    if _systemd_unit_exists():
        try:
            with open(unit_path) as f:
                content = f.read()
            if DEPLOY_DIR not in content:
                content = re.sub(
                    r'WorkingDirectory=.*',
                    f'WorkingDirectory={DEPLOY_DIR}',
                    content
                )
                content = re.sub(
                    r'(ExecStart|ExecStop|PIDFile)=.*?iec104-sim[^\n]*',
                    lambda m: m.group(0).replace('/iec104-sim/', '/gridsim/').replace('iec104-sim', SERVICE_NAME),
                    content
                )
                with open(unit_path, 'w') as f:
                    f.write(content)
                _run_cmd('systemctl daemon-reload', task_id, timeout=5)
                _task_log(task_id, '  ✅ systemd 单元路径已更新')
            else:
                _task_log(task_id, '  ✅ systemd 单元已就绪')
        except Exception as e:
            _task_log(task_id, f'  ⚠ 检查 systemd 单元时出错: {e}')
        return True

    old_unit = '/etc/systemd/system/iec104-sim.service'
    if os.path.exists(old_unit):
        _task_log(task_id, '  🔄 迁移旧 systemd 单元 iec104-sim → gridsim')
        try:
            with open(old_unit) as f:
                content = f.read()
            content = content.replace('/home/envuser/IEC/iec104-sim', DEPLOY_DIR)
            content = content.replace('iec104-sim', SERVICE_NAME)
            content = content.replace('IEC104 Simulator', 'Grid Simulator')
            with open(unit_path, 'w') as f:
                f.write(content)
            os.remove(old_unit)
            _run_cmd('systemctl daemon-reload', task_id, timeout=5)
            _task_log(task_id, f'  ✅ 已迁移 → {unit_path}')
            return True
        except Exception as e:
            _task_log(task_id, f'  ⚠ 迁移失败: {e}，将创建新单元')

    _task_log(task_id, f'  📝 创建 systemd 单元 {unit_path}')
    unit_content = f'''[Unit]
Description=Grid Simulator
After=network.target

[Service]
Type=forking
User=root
WorkingDirectory={DEPLOY_DIR}
ExecStart=/bin/bash {DEPLOY_DIR}/bin/start.sh
ExecStop=/bin/bash {DEPLOY_DIR}/bin/stop.sh
PIDFile={DEPLOY_DIR}/logs/pid
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
'''
    try:
        with open(unit_path, 'w') as f:
            f.write(unit_content)
        _run_cmd('systemctl daemon-reload', task_id, timeout=5)
        _task_log(task_id, '  ✅ systemd 单元创建成功')
        return True
    except Exception as e:
        _task_log(task_id, f'  ⚠ 创建 systemd 单元失败: {e}')
        return False


def _service_action(action, task_id, remote_dir=None):
    """Start/stop/restart with 3-level fallback. Returns True if any succeeds.

    Strategy chain:
      1. systemctl (requires systemd unit)
      2. Direct bin/{action}.sh script
      3. pkill (stop only) / direct binary launch (start only)
    """
    deploy_dir = remote_dir or DEPLOY_DIR

    if action == 'stop':
        strategies = [
            ('systemd', f'systemctl stop {SERVICE_NAME}'),
            ('script',  f'bash {deploy_dir}/bin/stop.sh 2>/dev/null'),
            ('pkill',   f'pkill -x {SERVICE_NAME} 2>/dev/null; pkill -f "{deploy_dir}/bin/{SERVICE_NAME}" 2>/dev/null; sleep 1; echo done'),
        ]
    elif action == 'start':
        strategies = [
            ('systemd', f'systemctl start {SERVICE_NAME}'),
            ('script',  f'bash {deploy_dir}/bin/start.sh 2>/dev/null'),
            ('direct',  f'mkdir -p {deploy_dir}/logs && nohup {deploy_dir}/bin/{SERVICE_NAME} serve --http :8989 --config-dir {deploy_dir}/config --log-dir {deploy_dir}/logs --log info > {deploy_dir}/logs/output.log 2>&1 &'),
        ]
    elif action == 'restart':
        ok = _service_action('stop', task_id, remote_dir)
        time.sleep(1)
        ok = _service_action('start', task_id, remote_dir) and ok
        return ok
    else:
        _task_log(task_id, f'❌ 未知操作: {action}', 'error')
        return False

    for name, cmd in strategies:
        ok, out, err = _try_cmd(cmd, timeout=15 if name != 'direct' else 8)
        if ok:
            if action != 'stop' or name == 'systemd':
                _task_log(task_id, f'  ✅ {name} {action} 成功')
            return True
        if name == 'systemd':
            _task_log(task_id, f'  ⚠ systemd 不可用（将使用脚本控制）')
        else:
            _task_log(task_id, f'  ⚠ {name} {action} 未生效（尝试下一策略）')

    _task_log(task_id, f'❌ {action} 失败：所有策略均无效', 'warning')
    return False


def _preflight_checks(pkg_path, task_id):
    """Pre-deployment checks. Returns False if deployment cannot proceed."""
    if not os.path.exists(pkg_path):
        _task_log(task_id, f'❌ 压缩包不存在: {pkg_path}', 'error')
        return False

    pkg = os.path.basename(pkg_path)
    pkg_size = os.path.getsize(pkg_path)
    _task_log(task_id, f'  📦 {pkg} ({fmt_size(pkg_size)})')

    ok, out, err = _try_cmd(f'tar tzf {pkg_path} 2>/dev/null | wc -l', timeout=15)
    if not ok:
        _task_log(task_id, f'❌ 压缩包损坏或无法读取', 'error')
        return False
    _task_log(task_id, f'  📋 包内文件数: {out.strip() or "?"}')

    try:
        os.makedirs(DEPLOY_DIR, exist_ok=True)
        st = os.statvfs(DEPLOY_DIR)
        free_bytes = st.f_frsize * st.f_bavail
        needed = pkg_size * 2
        free_fmt = fmt_size(free_bytes)
        if free_bytes < needed:
            _task_log(task_id, f'  ⚠ 可用空间 {free_fmt} < 建议 {fmt_size(needed)}')
            if free_bytes < pkg_size:
                _task_log(task_id, f'❌ 磁盘空间不足（仅剩 {free_fmt}）', 'error')
                return False
        else:
            _task_log(task_id, f'  💾 可用空间: {free_fmt} ✓')
    except Exception as e:
        _task_log(task_id, f'  ⚠ 无法检查磁盘空间: {e}')

    if os.path.exists(DEPLOY_DIR) and not os.access(DEPLOY_DIR, os.W_OK):
        _task_log(task_id, f'❌ 部署目录不可写: {DEPLOY_DIR}', 'error')
        return False

    return True


# ============================================================
# Local deploy thread
# ============================================================
def _deploy_local_thread(version, filename, task_id):
    pkg_path = os.path.join(DIST_DIR, filename)
    _task_log(task_id, f'🚀 开始部署 {version}')

    config_dir = os.path.join(DEPLOY_DIR, 'config')
    start_script = os.path.join(DEPLOY_DIR, 'bin', 'start.sh')
    stop_script = os.path.join(DEPLOY_DIR, 'bin', 'stop.sh')

    if not _preflight_checks(pkg_path, task_id):
        return

    is_upgrade = os.path.exists(start_script) or os.path.exists(stop_script)
    _task_log(task_id, f'{"🔄 升级模式" if is_upgrade else "🆕 全新部署"}')

    os.makedirs(DEPLOY_DIR, exist_ok=True)

    # -- 1. Stop service FIRST (upgrade only) --
    if is_upgrade:
        _service_action('stop', task_id)

    # -- 2. Backup config AFTER service stopped (upgrade only) --
    if is_upgrade:
        if os.path.exists(config_dir) and os.listdir(config_dir):
            ts = datetime.now().strftime('%Y%m%d-%H%M%S')
            backup_name = f'config-pre-upgrade-{ts}'
            backup_path = os.path.join(BACKUP_DIR, backup_name)
            os.makedirs(backup_path, exist_ok=True)
            _run_cmd(f'cp -r {config_dir}/* {backup_path}/', task_id)
            cur_ver = _detect_local_version()
            try:
                with open(os.path.join(backup_path, 'manifest.json'), 'w') as f:
                    json.dump({'backup_time': ts, 'version': cur_ver}, f)
            except Exception:
                pass
            _task_log(task_id, f'📦 配置已备份 → {backup_name}')
        else:
            _task_log(task_id, '📭 无需备份（config 为空）')

    # -- 3. Clear + Extract --
    if is_upgrade:
        _task_log(task_id, '🗑 清理旧文件...')
        for item in os.listdir(DEPLOY_DIR):
            if item in ('backups',):
                continue
            fp = os.path.join(DEPLOY_DIR, item)
            if os.path.isdir(fp):
                _run_cmd(f'rm -rf {fp}', task_id)
            else:
                try:
                    os.remove(fp)
                except Exception:
                    pass

    _task_log(task_id, f'📦 解压 {filename}...')
    r = _run_cmd(
        f'tar xzf {pkg_path} -C {DEPLOY_DIR} --strip-components=1',
        task_id, timeout=30
    )
    if not r:
        return

    # -- 3b. Post-extraction fixups --
    bin_dir = os.path.join(DEPLOY_DIR, 'bin')
    if os.path.isdir(bin_dir):
        _run_cmd(f'chmod +x {bin_dir}/* 2>/dev/null', task_id, timeout=5)
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(os.path.join(DEPLOY_DIR, 'logs'), exist_ok=True)

    # -- 4. Restore config (upgrade only) --
    if is_upgrade:
        if os.path.isdir(BACKUP_DIR):
            backups = sorted(os.listdir(BACKUP_DIR), reverse=True)
            if backups:
                latest = os.path.join(BACKUP_DIR, backups[0])
                _run_cmd(f'cp -r {latest}/* {config_dir}/', task_id)
                manifest = os.path.join(config_dir, 'manifest.json')
                if os.path.exists(manifest):
                    os.remove(manifest)
                _task_log(task_id, f'📂 配置已从 {backups[0]} 恢复')
            else:
                _task_log(task_id, '📂 无需恢复配置')
        else:
            _task_log(task_id, '📂 无备份可恢复')

    # -- 5. Ensure systemd service + Start --
    _ensure_systemd_service(task_id)
    _task_log(task_id, '▶ 启动服务...')
    _service_action('start', task_id)
    time.sleep(2)

    # -- 6. Verify (with retries) --
    _task_log(task_id, '🔍 验证部署...')
    verify_ok = True

    # API health check with retry (service may need a moment)
    api_ok = False
    for attempt in range(5):
        ok, out, _ = _try_cmd(
            'curl -s -o /dev/null -w "%{http_code}" http://localhost:8989/api/v1/status',
            timeout=5)
        if ok and out.strip() == '200':
            api_ok = True
            break
        if attempt < 4:
            time.sleep(3)
    if api_ok:
        _task_log(task_id, '  ✅ API: 200 OK')

        # Instance count
        ok2, out2, _ = _try_cmd(
            'curl -s http://localhost:8989/api/v1/instances', timeout=5)
        if ok2 and out2:
            try:
                insts = json.loads(out2)
                _task_log(task_id, f'  ✅ 实例: {len(insts)} 个')
            except:
                pass

        # Version from API
        ok3, out3, _ = _try_cmd(
            'curl -s http://localhost:8989/api/v1/status', timeout=5)
        if ok3 and out3:
            try:
                info = json.loads(out3)
                _task_log(task_id, f'  📌 运行版本: {info.get("version", "?")}')
            except:
                pass

        # Web UI
        ok4, out4, _ = _try_cmd(
            'curl -s -o /dev/null -w "%{http_code}" http://localhost:8989/', timeout=5)
        if ok4 and out4.strip() == '200':
            _task_log(task_id, '  ✅ Web UI: 可访问')
    else:
        _task_log(task_id, '  ⚠ API 未返回 200（可稍后手动检查）')
        verify_ok = False

    # PID check
    pid_file = os.path.join(DEPLOY_DIR, 'logs', 'pid')
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = f.read().strip()
        _task_log(task_id, f'  🆔 PID: {pid}')
    else:
        # fallback: pgrep
        ok5, out5, _ = _try_cmd(f'pgrep -x {SERVICE_NAME} 2>/dev/null || pgrep -f "{DEPLOY_DIR}/bin/{SERVICE_NAME}" 2>/dev/null', timeout=5)
        if ok5 and out5:
            _task_log(task_id, f'  🆔 PID: {out5.split()[0]}')

    if verify_ok:
        _task_log(task_id, f'🎉 部署完成! 版本: {version}', 'completed')
    else:
        _task_log(task_id, f'⚠ 部署完成，但部分验证未通过', 'warning')

def _detect_local_version():
    """Detect current version from deployed files or process."""
    # Try process command line
    r = sp.run('ps -eo cmd | grep "gridsim" | grep -v grep',
               shell=True, capture_output=True, text=True, timeout=3)
    for line in r.stdout.strip().split('\n'):
        line = line.strip()
        # Check for version in start.sh call or process args
        break
    # Try to read version from deployment
    for f in sorted(glob.glob(os.path.join(DEPLOY_DIR, 'bin', '*')), reverse=True):
        pass
    return 'unknown'

# ============================================================
# Remote deploy thread
# ============================================================
def _deploy_remote_thread(version, filename, host, port, user, password, task_id):
    pkg_local = os.path.join(DIST_DIR, filename)
    pkg_remote = f'/tmp/{filename}'
    remote_deploy_dir = DEPLOY_DIR  # same path on remote

    # Check if we already have a key set up for this host
    servers = load_servers()
    server_record = next((s for s in servers if s['host'] == host), None)
    if server_record and server_record.get('auth') == 'key':
        password = ''  # use key auth

    _task_log(task_id, f'🚀 远程部署 {version} → {host}' + (' (密钥认证)' if not password else ' (密码认证)'))

    def _run_remote_cmd(cmd, timeout=30):
        if not password:
            return _run_cmd(
                f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} '{cmd}'",
                task_id, timeout=timeout
            )
        fd, script_path = tempfile.mkstemp(suffix='.exp', text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(f'set timeout {timeout}\n')
            f.write(f'spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} {cmd}\n')
            f.write(f'expect "password:"\n')
            f.write(f'send "{password}\\r"\n')
            f.write(f'expect eof\n')
        try:
            r = sp.run(['expect', '-f', script_path], capture_output=True, text=True, timeout=timeout + 10)
            if r.returncode != 0:
                err = r.stderr.strip() or r.stdout.strip() or f'exit {r.returncode}'
                _task_log(task_id, f'❌ {err}', 'error')
                return False
            for line in r.stdout.strip().split('\n'):
                line = line.strip()
                if line and 'spawn' not in line and 'password' not in line.lower() and 'send' not in line:
                    _task_log(task_id, line)
            return True
        except sp.TimeoutExpired:
            _task_log(task_id, '❌ 命令超时', 'error')
            return False
        except Exception as e:
            _task_log(task_id, f'❌ {e}', 'error')
            return False
        finally:
            os.unlink(script_path)

    def _run_remote_scp(local, remote, timeout=120):
        """SCP a file to the remote host using expect for password auth."""
        if not password:
            return _run_cmd(
                f'scp -o StrictHostKeyChecking=no -P {port} {local} {user}@{host}:{remote}',
                task_id, timeout=timeout
            )
        fd, script_path = tempfile.mkstemp(suffix='.exp', text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(f'set timeout {timeout}\n')
            f.write(f'spawn scp -o StrictHostKeyChecking=no -P {port} {local} {user}@{host}:{remote}\n')
            f.write(f'expect "password:"\n')
            f.write(f'send "{password}\\r"\n')
            f.write(f'expect eof\n')
        try:
            r = sp.run(['expect', '-f', script_path], capture_output=True, text=True, timeout=timeout + 10)
            if r.returncode != 0:
                err = r.stderr.strip() or r.stdout.strip() or f'exit {r.returncode}'
                _task_log(task_id, f'❌ {err}', 'error')
                return False
            for line in r.stdout.strip().split('\n'):
                line = line.strip()
                if line and 'spawn' not in line and 'password' not in line.lower() and 'send' not in line:
                    _task_log(task_id, line)
            return True
        except sp.TimeoutExpired:
            _task_log(task_id, '❌ 命令超时', 'error')
            return False
        except Exception as e:
            _task_log(task_id, f'❌ {e}', 'error')
            return False
        finally:
            os.unlink(script_path)

    def _remote_ssh_output(cmd, timeout=30):
        """Run SSH and return stdout as string."""
        if not password:
            r = sp.run(
                f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} '{cmd}'",
                shell=True, capture_output=True, text=True, timeout=timeout
            )
            return r.stdout, r.returncode
        fd, script_path = tempfile.mkstemp(suffix='.exp', text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(f'set timeout {timeout}\n')
            f.write(f'spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} {cmd}\n')
            f.write(f'expect "password:"\n')
            f.write(f'send "{password}\\r"\n')
            f.write(f'expect eof\n')
        try:
            r = sp.run(['expect', '-f', script_path], capture_output=True, text=True, timeout=timeout + 10)
            return r.stdout, r.returncode
        finally:
            os.unlink(script_path)

    # -- 1. Pre-check: ping --
    _task_log(task_id, '🌐 检查远程服务器可达性...')
    r = sp.run(f'ping -c1 -W3 {host}', shell=True, capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        _task_log(task_id, '❌ 远程服务器不可达', 'error')
        return

    # -- 2. Detect fresh deploy or upgrade --
    _task_log(task_id, '🔍 检测远程安装状态...')
    stdout, _ = _remote_ssh_output(
        f'test -f {remote_deploy_dir}/bin/start.sh && echo upgrade || echo fresh'
    )
    is_upgrade = 'upgrade' in stdout
    _task_log(task_id, f'{"🔄 升级模式" if is_upgrade else "🆕 全新部署模式"}')

    # Always ensure deploy dir exists
    _run_remote_cmd(f'mkdir -p {remote_deploy_dir} {remote_deploy_dir}/backups')

    # -- 3. Stop service FIRST (upgrade only) --
    if is_upgrade:
        _task_log(task_id, '⏹ 停止远程服务...')
        _run_remote_cmd(
            f'cd {remote_deploy_dir} && bash bin/stop.sh 2>/dev/null || '
            f'pkill -f gridsim 2>/dev/null; sleep 1; echo "stopped"',
            timeout=15
        )

    # -- 4. Backup config AFTER service stopped (upgrade only) --
    if is_upgrade:
        _task_log(task_id, '📦 备份远程配置...')
        ts = datetime.now().strftime('%Y%m%d-%H%M%S')
        _run_remote_cmd(
            f'if [ -d {remote_deploy_dir}/config ] && ls {remote_deploy_dir}/config/* >/dev/null 2>&1; then '
            f'mkdir -p {remote_deploy_dir}/backups/config-pre-upgrade-{ts} && '
            f'cp -r {remote_deploy_dir}/config/* {remote_deploy_dir}/backups/config-pre-upgrade-{ts}/ && '
            f'echo "Backup done"; '
            f'else echo "No config to backup"; fi',
            timeout=15
        )

    # -- 5. SCP transfer --
    _task_log(task_id, f'📤 传输 {filename} ({fmt_size(os.path.getsize(pkg_local))})...')
    ok = _run_remote_scp(pkg_local, pkg_remote, timeout=120)
    if not ok:
        _task_log(task_id, '❌ SCP 传输失败', 'error')
        return
    _task_log(task_id, '  ✔ 传输完成')

    # -- 6. Clean + Extract --
    if is_upgrade:
        _task_log(task_id, '🗑 清理远程旧文件...')
        _run_remote_cmd(
            f'for item in {remote_deploy_dir}/bin {remote_deploy_dir}/logs '
            f'{remote_deploy_dir}/manuals {remote_deploy_dir}/resources '
            f'{remote_deploy_dir}/web; do '
            f'[ -d "$item" ] && rm -rf "$item"; done; '
            f'rm -f {remote_deploy_dir}/*.md {remote_deploy_dir}/*.sh 2>/dev/null; '
            f'echo "Cleaned"',
            timeout=15
        )

    _task_log(task_id, '📦 远程解压...')
    _run_remote_cmd(
        f'tar xzf {pkg_remote} -C {remote_deploy_dir} --strip-components=1 && '
        f'rm -f {pkg_remote} && echo "Extracted {version}"',
        timeout=30
    )

    # -- 7. Restore config (upgrade only) --
    if is_upgrade:
        _task_log(task_id, '📂 恢复远程配置...')
        _run_remote_cmd(
            f'backups=($(ls -d {remote_deploy_dir}/backups/config-pre-upgrade-* 2>/dev/null)); '
            f'if [ ${{#backups[@]}} -gt 0 ]; then '
            f'latest=${{backups[-1]}}; '
            f'cp -r "$latest"/* {remote_deploy_dir}/config/ 2>/dev/null; '
            f'rm -f {remote_deploy_dir}/config/manifest.json 2>/dev/null; '
            f'echo "Config restored from $latest"; '
            f'else echo "No backup to restore"; fi',
            timeout=15
        )

    # -- 8. Start service --
    _task_log(task_id, '▶ 启动远程服务...')
    _run_remote_cmd(f'cd {remote_deploy_dir} && bash bin/start.sh', timeout=15)
    time.sleep(2)

    # -- 9. Verify --
    _task_log(task_id, '🔍 验证远程部署...')
    stdout, _ = _remote_ssh_output(
        'curl -s -o /dev/null -w "%{http_code}" http://localhost:8989/api/v1/status'
    )
    verify_ok = '200' in stdout

    # Always save/update server record
    servers = load_servers()
    existing = [s for s in servers if s['host'] == host]
    record = {
        'id': f'dep-{os.urandom(4).hex()}',
        'host': host,
        'port': port,
        'user': user,
        'version': version,
        'status': 'running' if verify_ok else 'unknown',
        'created_at': datetime.now().isoformat(),
        'last_seen': datetime.now().isoformat(),
    }
    if not password:
        record['auth'] = 'key'
    else:
        record['password'] = password
    if existing:
        for s in servers:
            if s['host'] == host:
                s.update(record)
                break
    else:
        servers.append(record)
    save_servers(servers)
    _task_log(task_id, '💾 远程服务器记录已保存')

    if verify_ok:
        _task_log(task_id, f'  ✅ API: 200 OK')
        _task_log(task_id, f'  🌐 Web UI: http://{host}:8989/')
        _task_log(task_id, f'🎉 远程部署完成! 版本: {version}', 'completed')
    else:
        _task_log(task_id, f'  ⚠ API 未返回 200')
        _task_log(task_id, f'🎉 部署完成，验证异常 · 版本: {version}', 'warning')

# ============================================================
# Routes
# ============================================================

@sm_bp.route('/simulator')
def index():
    if not require_auth():
        return redirect(url_for('auth.login'))
    return render_template('simulator_manager.html', user=session['user'])

# ---- Versions ----
@sm_bp.route('/api/simulator/versions')
def api_versions():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify({'versions': get_available_versions()})

# ---- Local Status ----
@sm_bp.route('/api/simulator/status')
def api_status():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    # Auto-detect host IP
    host_ip = '127.0.0.1'
    try:
        r = sp.run('hostname -I', shell=True, capture_output=True, text=True, timeout=3)
        if r.stdout.strip():
            host_ip = r.stdout.strip().split()[0]
    except:
        pass

    status = {
        'deploy_dir_exists': os.path.isdir(DEPLOY_DIR),
        'running': False,
        'pid': None,
        'version': None,
        'api_ok': False,
        'instances': 0,
        'ports': {},
        'host_ip': host_ip,
    }
    # Check PID
    pid_file = os.path.join(DEPLOY_DIR, 'logs', 'pid')
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            pid = f.read().strip()
        # Verify pid is running
        r = sp.run(f'kill -0 {pid} 2>/dev/null && echo alive || echo dead',
                   shell=True, capture_output=True, text=True, timeout=3)
        if r.stdout.strip() == 'alive':
            status['running'] = True
            status['pid'] = pid
            # Get process command to find version
            r2 = sp.run(f'ps -p {pid} -o cmd= 2>/dev/null',
                        shell=True, capture_output=True, text=True, timeout=3)
            if r2.stdout.strip():
                status['cmd'] = r2.stdout.strip()[:200]
    if not status['running']:
        # Fallback: check if any gridsim process running
        r = sp.run('pgrep -x gridsim 2>/dev/null',
                   shell=True, capture_output=True, text=True, timeout=3)
        if r.stdout.strip():
            status['running'] = True
            status['pid'] = r.stdout.strip().split('\n')[0]

    # Check API
    r = sp.run('curl -s -o /dev/null -w "%{http_code}" http://localhost:8989/api/v1/status',
               shell=True, capture_output=True, text=True, timeout=5)
    if r.stdout.strip() == '200':
        status['api_ok'] = True
        # Get instance count
        r2 = sp.run('curl -s http://localhost:8989/api/v1/instances',
                    shell=True, capture_output=True, text=True, timeout=5)
        if r2.stdout.strip():
            try:
                status['instances'] = len(json.loads(r2.stdout))
            except:
                pass
        # Get version info
        r3 = sp.run('curl -s http://localhost:8989/api/v1/status',
                    shell=True, capture_output=True, text=True, timeout=5)
        if r3.stdout.strip():
            try:
                info = json.loads(r3.stdout)
                status['status_info'] = info
            except:
                pass

    # Check ports
    r = sp.run('ss -tlnp 2>/dev/null | grep -E "8989|2404" || true',
               shell=True, capture_output=True, text=True, timeout=3)
    for line in r.stdout.strip().split('\n'):
        if '8989' in line:
            status['ports']['8989'] = 'listening'
        if '2404' in line:
            status['ports']['2404'] = 'listening'

    # Detect version from deployment
    ver_file = os.path.join(DEPLOY_DIR, 'backups', 'current_version')
    # Try to find version from start.sh content or process
    if not status['version'] and status.get('cmd'):
        m = re.search(r'gridsim-v(\S+)', status['cmd'])
        if m:
            status['version'] = m.group(1)

    # Uptime
    if status['pid']:
        r = sp.run(f'ps -o etimes= -p {status["pid"]} 2>/dev/null',
                   shell=True, capture_output=True, text=True, timeout=3)
        if r.stdout.strip():
            secs = int(r.stdout.strip())
            days = secs // 86400
            hours = (secs % 86400) // 3600
            mins = (secs % 3600) // 60
            status['uptime'] = f'{days}d {hours}h {mins}m'

    return jsonify(status)

# ---- Deploy Local ----
@sm_bp.route('/api/simulator/deploy', methods=['POST'])
def api_deploy():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    version = data.get('version', '')
    # Find matching file
    versions = get_available_versions()
    match = next((v for v in versions if v['version'] == version), None)
    if not match:
        return jsonify({'error': f'版本 {version} 未找到'}), 404

    task_id = f'deploy-{os.urandom(4).hex()}'
    t = threading.Thread(target=_deploy_local_thread,
                         args=(match['version'], match['filename'], task_id))
    t.daemon = True
    t.start()
    return jsonify({'task_id': task_id, 'version': version})

# ---- Deploy Remote ----
@sm_bp.route('/api/simulator/remote-deploy', methods=['POST'])
def api_remote_deploy():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    version = data.get('version', '')
    host = data.get('host', '').strip()
    port = int(data.get('port', 22))
    user = data.get('user', 'root').strip()
    password = data.get('password', '')

    if not host or not password:
        return jsonify({'error': 'IP 和密码不能为空'}), 400

    versions = get_available_versions()
    match = next((v for v in versions if v['version'] == version), None)
    if not match:
        return jsonify({'error': f'版本 {version} 未找到'}), 404

    task_id = f'remote-{os.urandom(4).hex()}'
    t = threading.Thread(target=_deploy_remote_thread,
                         args=(match['version'], match['filename'],
                               host, port, user, password, task_id))
    t.daemon = True
    t.start()
    return jsonify({'task_id': task_id, 'version': version, 'host': host})

# ---- Deploy Progress ----
@sm_bp.route('/api/simulator/deploy-status/<task_id>')
def api_deploy_status(task_id):
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    with _task_lock:
        task = _deploy_tasks.get(task_id, {'status': 'not_found', 'logs': []})
    return jsonify(task)

# ---- Control: start/stop/restart ----
@sm_bp.route('/api/simulator/control', methods=['POST'])
def api_control():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    action = request.get_json().get('action', '')
    task_id = f'ctrl-{os.urandom(4).hex()}'

    if action not in ('start', 'stop', 'restart'):
        return jsonify({'error': f'未知操作: {action}'}), 400

    labels = {'stop': ('⏹', '服务已停止'), 'start': ('▶', '服务已启动'), 'restart': ('🔄', '服务已重启')}
    icon, done_label = labels[action]
    _task_log(task_id, f'{icon} {action}服务...')
    ok = _service_action(action, task_id)
    time.sleep(1)
    _task_log(task_id, f'{icon} {done_label}', 'completed' if ok else 'warning')
    return jsonify({'task_id': task_id})

# ---- Remote Control ----
def _exec_remote_ssh(host, port, user, password, remote_cmd, timeout=15):
    """Execute a command on remote host via SSH. Uses key auth if server record says so."""
    servers = load_servers()
    record = next((s for s in servers if s['host'] == host), None)
    use_key = record and record.get('auth') == 'key'

    if use_key:
        r = sp.run(
            f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} "{remote_cmd}"',
            shell=True, capture_output=True, text=True, timeout=timeout
        )
        if r.returncode == 0:
            return True, r.stdout.strip(), ''
        return False, '', r.stderr.strip()

    if not password:
        return False, '', 'no password or key auth configured'

    fd, script_path = tempfile.mkstemp(suffix='.exp', text=True)
    with os.fdopen(fd, 'w') as f:
        f.write(f'set timeout {timeout}\n')
        f.write(f'spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} {remote_cmd}\n')
        f.write(f'expect "password:"\n')
        f.write(f'send "{password}\\r"\n')
        f.write(f'expect eof\n')
    try:
        r = sp.run(['expect', '-f', script_path], capture_output=True, text=True, timeout=timeout + 5)
        if r.returncode == 0:
            return True, r.stdout.strip(), ''
        return False, '', r.stderr.strip()
    except sp.TimeoutExpired:
        return False, '', 'timeout'
    except Exception as e:
        return False, '', str(e)
    finally:
        os.unlink(script_path)

@sm_bp.route('/api/simulator/remote-control', methods=['POST'])
def api_remote_control():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    host = data.get('host', '').strip()
    action = data.get('action', '')
    if not host or action not in ('start', 'stop', 'restart'):
        return jsonify({'error': 'host and valid action required'}), 400

    servers = load_servers()
    record = next((s for s in servers if s['host'] == host), None)
    if not record:
        return jsonify({'error': 'server not found'}), 404

    port = int(record.get('port', 22))
    user = record.get('user', 'root')
    password = record.get('password', '')

    remote_dir = DEPLOY_DIR
    cmds = {
        'start': f'cd {remote_dir} && bash bin/start.sh 2>/dev/null || (nohup bin/gridsim serve --http :8989 --config-dir config --log-dir logs --log info > logs/output.log 2>&1 &)',
        'stop': f'cd {remote_dir} && bash bin/stop.sh 2>/dev/null || pkill -f gridsim',
        'restart': f'cd {remote_dir} && (bash bin/restart.sh 2>/dev/null || (bash bin/stop.sh 2>/dev/null || pkill -f gridsim); sleep 1; (bash bin/start.sh 2>/dev/null || (nohup bin/gridsim serve --http :8989 --config-dir config --log-dir logs --log info > logs/output.log 2>&1 &)))',
    }

    ok, out, err = _exec_remote_ssh(host, port, user, password, cmds[action], timeout=15)
    if not ok:
        return jsonify({'error': err or 'remote command failed'}), 500

    time.sleep(2)
    ok2, status_out, _ = _exec_remote_ssh(
        host, port, user, password,
        'curl -s -o /dev/null -w "%{http_code}" http://localhost:8989/api/v1/status',
        timeout=8
    )
    running = ok2 and status_out.strip() == '200'

    if running:
        record['status'] = 'running'
    elif action == 'stop':
        record['status'] = 'stopped'
    record['last_seen'] = datetime.now().isoformat()
    save_servers(servers)

    return jsonify({'ok': True, 'action': action, 'running': running, 'output': out[:500]})

# ---- Backups ----
@sm_bp.route('/api/simulator/backups')
def api_backups():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    backups = []
    if os.path.isdir(BACKUP_DIR):
        for d in sorted(os.listdir(BACKUP_DIR), reverse=True):
            dp = os.path.join(BACKUP_DIR, d)
            if os.path.isdir(dp):
                manifest = {}
                mf = os.path.join(dp, 'manifest.json')
                if os.path.exists(mf):
                    with open(mf) as f:
                        manifest = json.load(f)
                files = [f for f in os.listdir(dp) if f != 'manifest.json']
                backups.append({
                    'name': d,
                    'time': d.replace('config-pre-upgrade-', ''),
                    'files': len(files),
                    'size': fmt_size(sum(
                        os.path.getsize(os.path.join(dp, f)) for f in files
                        if os.path.isfile(os.path.join(dp, f))
                    )),
                    'version': manifest.get('version', ''),
                })
    return jsonify({'backups': backups})

# ---- Remote Servers CRUD ----
@sm_bp.route('/api/simulator/remote-servers', methods=['GET'])
def api_remote_list():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    servers = load_servers()
    # Check live status for each
    for s in servers:
        r = sp.run(
            f'timeout 3 bash -c "echo > /dev/tcp/{s["host"]}/8989" 2>/dev/null && echo open || echo closed',
            shell=True, capture_output=True, text=True, timeout=5)
        s['status'] = 'running' if 'open' in r.stdout else 'stopped'
    return jsonify({'servers': servers})

@sm_bp.route('/api/simulator/remote-servers', methods=['DELETE'])
def api_remote_delete():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    host = data.get('host', '')
    servers = load_servers()
    servers = [s for s in servers if s['host'] != host]
    save_servers(servers)
    return jsonify({'ok': True})

@sm_bp.route('/api/simulator/remote-check', methods=['POST'])
def api_remote_check():
    """Check if a remote server is reachable and return status."""
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    host = data.get('host', '')
    port = int(data.get('port', 22))
    user = data.get('user', 'root')
    password = data.get('password', '')

    result = {'host': host, 'reachable': False, 'sim_running': False, 'version': None}

    # Ping check
    r = sp.run(f'ping -c1 -W3 {host}', shell=True, capture_output=True, text=True, timeout=10)
    result['reachable'] = r.returncode == 0

    if not result['reachable']:
        return jsonify(result)

    # SSH check for sim status using expect if password is set
    remote_cmd = 'curl -s http://localhost:8989/api/v1/status'
    if password:
        fd, script_path = tempfile.mkstemp(suffix='.exp', text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(f'set timeout 10\n')
            f.write(f'spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} {remote_cmd}\n')
            f.write(f'expect "password:"\n')
            f.write(f'send "{password}\\r"\n')
            f.write(f'expect eof\n')
        try:
            r = sp.run(['expect', '-f', script_path], capture_output=True, text=True, timeout=15)
            if r.returncode == 0 and r.stdout.strip():
                result['sim_running'] = True
                try:
                    lines = r.stdout.strip().split('\n')
                    json_line = lines[-1] if lines else ''
                    info = json.loads(json_line)
                    result['version'] = info.get('version', 'unknown')
                except:
                    pass
        except Exception:
            pass
        finally:
            os.unlink(script_path)
    else:
        r = sp.run(
            f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} "{remote_cmd}"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        if r.stdout.strip() and r.returncode == 0:
            result['sim_running'] = True
            try:
                info = json.loads(r.stdout)
                result['version'] = info.get('version', 'unknown')
            except:
                pass

    if not result['sim_running']:
        r2 = sp.run(f'timeout 2 bash -c "echo > /dev/tcp/{host}/8989" 2>&1',
                    shell=True, capture_output=True, text=True, timeout=5)
        result['sim_running'] = r2.returncode == 0

    return jsonify(result)

@sm_bp.route('/api/simulator/setup-key', methods=['POST'])
def api_setup_key():
    """Generate local SSH key (if missing) and copy it to remote server."""
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    host = data.get('host', '')
    port = int(data.get('port', 22))
    user = data.get('user', 'root')
    password = data.get('password', '')
    if not host or not password:
        return jsonify({'error': 'host and password required'}), 400

    key_file = os.path.expanduser('~/.ssh/id_rsa')
    if not os.path.exists(key_file):
        r = sp.run(['ssh-keygen', '-t', 'rsa', '-N', '', '-f', key_file],
                   capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return jsonify({'error': f'ssh-keygen failed: {r.stderr}'}), 500

    fd, script_path = tempfile.mkstemp(suffix='.exp', text=True)
    with os.fdopen(fd, 'w') as f:
        f.write(f'set timeout 30\n')
        f.write(f'spawn ssh-copy-id -o StrictHostKeyChecking=no -p {port} {user}@{host}\n')
        f.write(f'expect "password:"\n')
        f.write(f'send "{password}\\r"\n')
        f.write(f'expect eof\n')
    try:
        r = sp.run(['expect', '-f', script_path], capture_output=True, text=True, timeout=35)
        ok = 'Number of key(s) added' in r.stdout or 'already' in r.stdout.lower()
        if not ok:
            return jsonify({'error': 'ssh-copy-id failed', 'output': r.stdout[:500]}), 500
    finally:
        os.unlink(script_path)

    # Mark key auth in server record — clear password since key handles auth
    servers = load_servers()
    found = False
    for s in servers:
        if s['host'] == host:
            s['auth'] = 'key'
            s.pop('password', None)
            found = True
            break
    if not found:
        servers.append({
            'id': f'dep-{os.urandom(4).hex()}',
            'host': host, 'port': port, 'user': user,
            'auth': 'key', 'version': '', 'status': 'unknown',
            'created_at': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
        })
    save_servers(servers)
    return jsonify({'ok': True, 'host': host})

    # SSH check for sim status using expect if password is set
    remote_cmd = 'curl -s http://localhost:8989/api/v1/status'
    if password:
        fd, script_path = tempfile.mkstemp(suffix='.exp', text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(f'set timeout 10\n')
            f.write(f'spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} {remote_cmd}\n')
            f.write(f'expect "password:"\n')
            f.write(f'send "{password}\\r"\n')
            f.write(f'expect eof\n')
        try:
            r = sp.run(['expect', '-f', script_path], capture_output=True, text=True, timeout=15)
            if r.returncode == 0 and r.stdout.strip():
                result['sim_running'] = True
                try:
                    info = json.loads(r.stdout.strip().split('\r\n')[-1] if '\r\n' in r.stdout else r.stdout.strip())
                    result['version'] = info.get('version', 'unknown')
                except:
                    pass
        except Exception:
            pass
        finally:
            os.unlink(script_path)
    else:
        r = sp.run(
            f'ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p {port} {user}@{host} "{remote_cmd}"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        if r.stdout.strip() and r.returncode == 0:
            result['sim_running'] = True
            try:
                info = json.loads(r.stdout)
                result['version'] = info.get('version', 'unknown')
            except:
                pass

    if not result['sim_running']:
        # Check port directly
        r2 = sp.run(f'timeout 2 bash -c "echo > /dev/tcp/{host}/8989" 2>&1',
                    shell=True, capture_output=True, text=True, timeout=5)
        result['sim_running'] = r2.returncode == 0

    return jsonify(result)
