"""IEC104 Curtailment Manager — background file generator with cleanup."""
import os, random, time, threading
from datetime import datetime
from flask import (
    Blueprint, render_template, session, redirect, url_for,
    request, jsonify
)

ct_bp = Blueprint('curtailment', __name__)

# ============================================================
# Config
# ============================================================
FOLDER_PATH = '/data2/sftp/fep/Curtailment'
FILE_PREFIX = '203_0000_01000300000000006500010011_'
KEEP_FILES = 4

def require_auth():
    if 'user' not in session:
        return False
    return True

# ============================================================
# Binary file generation (matches updatefile.sh exactly)
# ============================================================
# Prefix: 41 bytes
_PREFIX = (
    b'\x00\x00\x00\x00\x00\x01\x03\x00\x00\x00\x00\x01'
    b'\x02\x05\x00\x01\x00\x01\x00\x00\x00\x03\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x06\x05\x00\x00'
    b'\x00\x01\x00\x00\x01\x01'
)

# Suffix: 17 bytes
_SUFFIX = b'\x06\x00\x00\x02\x00\x02\x04\x00\x07\x00\x01\x01\x08\x03\x06\x00\x00'


def _compute_time_bytes(plan_time=None):
    """Replicate the Python snippet inside updatefile.sh.
    
    Args:
        plan_time: Optional datetime object. If None, uses current time + 9h.
    """
    now = plan_time or datetime.now()
    nian = now.year
    yue = now.month
    ri = now.day
    shi = now.hour + 9
    fen = now.minute

    if fen >= 30:
        shi += 1
        fen_str = '0000'
    else:
        fen_str = '0300'

    if shi >= 24:
        shi -= 24
        ri += 1

    nian_str = f'{nian // 1000:02}{nian // 100 % 10:02}'
    nianS_str = f'0{nian % 100 // 10}0{nian % 10}'
    yue_str = f'{yue // 10:02}0{yue % 10}'
    ri_str = f'{ri // 10:02}0{ri % 10}'
    shi_str = f'{shi // 10:02}0{shi % 10}'

    def insert_x(s):
        """Convert hex string pairs to raw bytes."""
        return bytes(int(s[i:i+2], 16) for i in range(0, len(s), 2))

    return (insert_x(nian_str) + insert_x(nianS_str) + insert_x(yue_str) +
            insert_x(ri_str) + insert_x(shi_str) + insert_x(fen_str))


def generate_curtailment_file(plan_values=None, plan_time=None):
    """Generate a single IEC104 curtailment binary file.
    
    Args:
        plan_values: Optional list of 6 integers (0-100). If None, random values are used.
        plan_time: Optional datetime for plan start time. If None, uses current time + 9h.
    """
    os.makedirs(FOLDER_PATH, exist_ok=True)

    time_bytes = _compute_time_bytes(plan_time)

    # Plan values: use provided or generate random
    if plan_values and len(plan_values) == 6:
        values = bytes(max(0, min(100, int(v))) for v in plan_values)
    else:
        values = bytes(random.randint(0, 100) for _ in range(6))
    
    count_byte = b'\x36'  # ASCII '6' = 0x36

    # Null separator: \x00\x00\x00\x00\x00
    null_sep = b'\x00\x00\x00\x00\x00'

    file_content = _PREFIX + time_bytes + null_sep + count_byte + values + _SUFFIX

    date_str = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f'{FILE_PREFIX}{date_str}.data'
    filepath = os.path.join(FOLDER_PATH, filename)

    with open(filepath, 'wb') as f:
        f.write(file_content)

    return filepath


# ============================================================
# Cleanup: keep only newest N files
# ============================================================
def cleanup_files():
    """Remove oldest .data files, keeping only KEEP_FILES newest."""
    if not os.path.isdir(FOLDER_PATH):
        return
    files = [f for f in os.listdir(FOLDER_PATH) if f.endswith('.data')]
    files = [(os.path.join(FOLDER_PATH, f), os.path.getmtime(os.path.join(FOLDER_PATH, f)))
             for f in files]
    files.sort(key=lambda x: x[1], reverse=True)  # newest first
    for fp, _ in files[KEEP_FILES:]:
        try:
            os.remove(fp)
        except OSError:
            pass


def _get_file_list():
    """Return list of .data files sorted by mtime (newest first)."""
    if not os.path.isdir(FOLDER_PATH):
        return []
    files = []
    for f in os.listdir(FOLDER_PATH):
        if not f.endswith('.data'):
            continue
        fp = os.path.join(FOLDER_PATH, f)
        if not os.path.isfile(fp):
            continue
        st = os.stat(fp)
        files.append({
            'name': f,
            'size': st.st_size,
            'mtime': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'mtime_ts': st.st_mtime,
        })
    files.sort(key=lambda x: x['mtime_ts'], reverse=True)
    return files


# ============================================================
# Background thread
# ============================================================
_curtailment_running = False
_curtailment_thread = None


def _curtailment_loop():
    """Background loop: generate file → cleanup → sleep 1800s."""
    global _curtailment_running
    while _curtailment_running:
        try:
            generate_curtailment_file()
        except Exception:
            pass
        try:
            cleanup_files()
        except Exception:
            pass
        for _ in range(1800):
            if not _curtailment_running:
                break
            time.sleep(1)


# ============================================================
# Routes
# ============================================================

@ct_bp.route('/curtailment')
def index():
    if not require_auth():
        return redirect(url_for('auth.login'))
    return render_template('curtailment_manager.html', user=session['user'])


@ct_bp.route('/api/curtailment/status')
def api_status():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    files = _get_file_list()
    last_file = files[0] if files else None
    return jsonify({
        'running': _curtailment_running,
        'file_count': len(files),
        'last_file': last_file,
        'folder': FOLDER_PATH,
    })


@ct_bp.route('/api/curtailment/control', methods=['POST'])
def api_control():
    global _curtailment_running, _curtailment_thread
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    action = request.get_json().get('action', '')
    if action == 'start':
        if _curtailment_running:
            return jsonify({'error': 'generator already running'}), 400
        _curtailment_running = True
        _curtailment_thread = threading.Thread(target=_curtailment_loop, daemon=True)
        _curtailment_thread.start()
        return jsonify({'ok': True, 'action': 'started'})
    elif action == 'stop':
        if not _curtailment_running:
            return jsonify({'error': 'generator not running'}), 400
        _curtailment_running = False
        return jsonify({'ok': True, 'action': 'stopped'})
    return jsonify({'error': f'unknown action: {action}'}), 400


@ct_bp.route('/api/curtailment/files')
def api_files():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify({'files': _get_file_list()})


@ct_bp.route('/api/curtailment/files', methods=['DELETE'])
def api_delete_file():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    filename = data.get('filename', '')
    if not filename:
        return jsonify({'error': 'filename required'}), 400
    filepath = os.path.join(FOLDER_PATH, filename)
    if not os.path.isfile(filepath):
        return jsonify({'error': 'file not found'}), 404
    try:
        os.remove(filepath)
        return jsonify({'ok': True})
    except OSError as e:
        return jsonify({'error': str(e)}), 500


@ct_bp.route('/api/curtailment/generate', methods=['POST'])
def api_generate():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    plan_values = data.get('values')
    plan_time_str = data.get('plan_time')
    
    if plan_values is not None:
        if not isinstance(plan_values, list) or len(plan_values) != 6:
            return jsonify({'error': 'values must be a list of 6 integers (0-100)'}), 400
        try:
            plan_values = [int(v) for v in plan_values]
        except (ValueError, TypeError):
            return jsonify({'error': 'values must be integers'}), 400
    
    plan_time = None
    if plan_time_str:
        try:
            plan_time = datetime.strptime(plan_time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            try:
                plan_time = datetime.strptime(plan_time_str, '%Y-%m-%d %H:%M')
            except ValueError:
                return jsonify({'error': 'plan_time format must be YYYY-MM-DDTHH:MM or YYYY-MM-DD HH:MM'}), 400
    
    try:
        filepath = generate_curtailment_file(plan_values, plan_time)
        cleanup_files()
        return jsonify({'ok': True, 'file': os.path.basename(filepath)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
