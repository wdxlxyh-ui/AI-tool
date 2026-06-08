"""File manager blueprint — browse, upload, download, delete.
Supports full filesystem access with absolute paths."""
import os, mimetypes, json, time
from flask import (
    Blueprint, render_template, session, redirect, url_for,
    request, send_from_directory, jsonify, current_app
)
from werkzeug.utils import secure_filename

fm_bp = Blueprint('file_manager', __name__)

def require_auth():
    if 'user' not in session:
        return False
    return True

def resolve_path(path_str):
    """Resolve an absolute path safely. path_str is treated as absolute.
    Returns normalized absolute path, or None if invalid."""
    if not path_str:
        return '/'
    # Ensure it starts with /
    if not path_str.startswith('/'):
        path_str = '/' + path_str
    resolved = os.path.normpath(path_str)
    # Must still start with / after normalization
    if not resolved.startswith('/'):
        return None
    return resolved

def list_files(abs_path):
    """Return a list of files/dirs in the given absolute path."""
    if not os.path.isdir(abs_path):
        return []
    entries = []
    try:
        for entry in sorted(os.scandir(abs_path),
                            key=lambda e: (not e.is_dir(), e.name.lower())):
            if entry.name.startswith('.'):
                continue
            info = {
                'name': entry.name,
                'is_dir': entry.is_dir(),
                'size': entry.stat().st_size if entry.is_file() else 0,
                'mtime': entry.stat().st_mtime,
                'path': os.path.join(abs_path, entry.name),
            }
            entries.append(info)
    except OSError:
        pass
    return entries

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f'{size:.1f} {unit}' if unit != 'B' else f'{size} B'
        size /= 1024
    return f'{size:.1f} TB'

def format_time(timestamp):
    import datetime
    dt = datetime.datetime.fromtimestamp(timestamp)
    now = datetime.datetime.now()
    if dt.date() == now.date():
        return dt.strftime('今天 %H:%M')
    if dt.year == now.year:
        return dt.strftime('%m-%d %H:%M')
    return dt.strftime('%Y-%m-%d %H:%M')

def compute_parent(abs_path):
    """Return parent directory path, or None if at root."""
    parent = os.path.dirname(abs_path.rstrip('/'))
    if parent == abs_path.rstrip('/'):
        return None
    return parent

def breadcrumbs_from_path(abs_path):
    """Build breadcrumb list from an absolute path."""
    crumbs = []
    parts = abs_path.rstrip('/').split('/')
    for i, p in enumerate(parts):
        if not p and i == 0:
            crumbs.append({'name': '/', 'path': '/'})
        elif p:
            parent_path = '/'.join(parts[:i+1]) or '/'
            if not parent_path.startswith('/'):
                parent_path = '/' + parent_path
            crumbs.append({'name': p, 'path': parent_path})
    if not crumbs:
        crumbs.append({'name': '/', 'path': '/'})
    return crumbs

# ---- HTML Page ----
@fm_bp.route('/files')
def index():
    if not require_auth():
        return redirect(url_for('auth.login'))
    raw_path = request.args.get('path', '/')
    abs_path = resolve_path(raw_path)
    if abs_path is None:
        abs_path = '/'
    # If path doesn't exist, fallback to /
    if not os.path.exists(abs_path):
        abs_path = '/'
    entries = list_files(abs_path)
    parent = compute_parent(abs_path)
    crumbs = breadcrumbs_from_path(abs_path)
    return render_template('file_manager.html',
        entries=entries,
        parent=parent,
        breadcrumbs=crumbs,
        current_path=abs_path,
        user=session['user'],
        format_size=format_size,
        format_time=format_time,
    )

# ---- API: List files (JSON) ----
@fm_bp.route('/api/files')
def api_list():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    raw_path = request.args.get('path', '/')
    abs_path = resolve_path(raw_path)
    if abs_path is None or not os.path.isdir(abs_path):
        return jsonify({'entries': [], 'path': raw_path})
    entries = list_files(abs_path)
    for e in entries:
        e['size_fmt'] = format_size(e['size'])
        e['mtime_fmt'] = format_time(e['mtime'])
    return jsonify({'entries': entries, 'path': abs_path})

# ---- API: Upload ----
@fm_bp.route('/api/upload', methods=['POST'])
def api_upload():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    raw_path = request.form.get('path', '/')
    abs_path = resolve_path(raw_path)
    if abs_path is None:
        return jsonify({'error': 'invalid path'}), 400
    # Create target dir if needed
    try:
        os.makedirs(abs_path, exist_ok=True)
    except OSError as e:
        return jsonify({'error': str(e)}), 500

    uploaded = []
    for f in request.files.getlist('files'):
        if f.filename:
            safe_name = secure_filename(f.filename)
            f.save(os.path.join(abs_path, safe_name))
            uploaded.append(safe_name)
    return jsonify({'uploaded': uploaded, 'count': len(uploaded)})

# ---- API: Download ----
@fm_bp.route('/api/download')
def api_download():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    raw_path = request.args.get('path', '')
    abs_path = resolve_path(raw_path)
    if abs_path is None or not os.path.isfile(abs_path):
        return jsonify({'error': 'file not found'}), 404
    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory, filename, as_attachment=True)

# ---- API: Delete ----
@fm_bp.route('/api/delete', methods=['POST'])
def api_delete():
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    raw_path = data.get('path', '')
    abs_path = resolve_path(raw_path)
    if abs_path is None:
        return jsonify({'error': 'invalid path'}), 400
    try:
        if os.path.isdir(abs_path):
            os.rmdir(abs_path)
        else:
            os.remove(abs_path)
        return jsonify({'deleted': abs_path})
    except OSError as e:
        return jsonify({'error': str(e)}), 500

# ---- Direct HTML file serving ----
@fm_bp.route('/serve/<path:filename>')
def serve_html(filename):
    if not require_auth():
        return redirect(url_for('auth.login'))
    abs_path = resolve_path(filename)
    if abs_path is None or not os.path.isfile(abs_path):
        return 'Not found', 404
    directory = os.path.dirname(abs_path)
    filebase = os.path.basename(abs_path)
    return send_from_directory(directory, filebase)
