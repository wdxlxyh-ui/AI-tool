"""Work reports blueprint — daily report tool (Flask conversion)."""
import json, uuid, datetime as dt, os
from flask import Blueprint, jsonify, request, render_template, session, redirect, url_for

wr_bp = Blueprint('work_reports', __name__, url_prefix='/work-reports')

# ── data paths ────────────────────────────────────────────────────
DATA_DIR = None

def paths():
    global DATA_DIR
    if DATA_DIR is None:
        base = os.environ.get('EGC_BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
        DATA_DIR = os.path.join(base, 'data_work_reports')
        os.makedirs(os.path.join(DATA_DIR, 'notes'), exist_ok=True)
        os.makedirs(os.path.join(DATA_DIR, 'daily'), exist_ok=True)
        os.makedirs(os.path.join(DATA_DIR, 'weekly'), exist_ok=True)
    return {
        'notes':  os.path.join(DATA_DIR, 'notes'),
        'daily':  os.path.join(DATA_DIR, 'daily'),
        'weekly': os.path.join(DATA_DIR, 'weekly'),
        'projects': os.path.join(DATA_DIR, 'projects.json'),
        'kanban':   os.path.join(DATA_DIR, 'kanban.json'),
    }

def load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_projects():
    p = paths()['projects']
    projs = load_json(p, None)
    if projs is None:
        save_json(p, ["铁合金", "达茂旗"])
        return ["铁合金", "达茂旗"]
    return projs

def require_auth():
    return 'user' in session

# ── report generators ─────────────────────────────────────────────
TYPE_LABEL = {"project_delivery": "项目交付", "product_testing": "产品测试"}
TYPE_ICON  = {"project_delivery": "🔧", "product_testing": "🧪"}

def make_daily(date_str, notes):
    groups = {"project_delivery": {}, "product_testing": {}}
    for n in notes:
        t = n.get("type", "project_delivery")
        p = n.get("project", "其他")
        groups[t].setdefault(p, []).append(n["content"])
    lines = [f"# {date_str} 日报\n"]
    for t in ("project_delivery", "product_testing"):
        bucket = groups[t]
        if not bucket:
            continue
        lines.append(f"## {TYPE_ICON[t]} {TYPE_LABEL[t]}\n")
        for proj, items in bucket.items():
            lines.append(f"**{proj}**")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")
    if not notes:
        lines.append("*今日暂无记录*\n")
    lines += ["---", "*由工作日报系统自动生成*"]
    return "\n".join(lines)

def make_weekly(year, week, week_dates, notes):
    groups = {"project_delivery": {}, "product_testing": {}}
    for n in notes:
        t = n.get("type", "project_delivery")
        p = n.get("project", "其他")
        groups[t].setdefault(p, []).append(n)
    lines = [
        f"# {year} 第 {week} 周  周报\n",
        f"*{week_dates[0]} ～ {week_dates[-1]}*\n",
        "## 本周工作汇总\n",
        "| 工种 | 项目 | 记录条数 |",
        "|------|------|---------|",
    ]
    for t in ("project_delivery", "product_testing"):
        for proj, items in groups[t].items():
            lines.append(f"| {TYPE_LABEL[t]} | {proj} | {len(items)} |")
    lines.append("")
    for t in ("project_delivery", "product_testing"):
        bucket = groups[t]
        if not bucket:
            continue
        lines.append(f"## {TYPE_ICON[t]} {TYPE_LABEL[t]}\n")
        for proj, items in bucket.items():
            lines.append(f"**{proj}**")
            for n in items:
                lines.append(f"- [{n.get('date','')}] {n['content']}")
            lines.append("")
    lines += ["---", "*由工作日报系统自动生成*"]
    return "\n".join(lines)

# ── Routes ─────────────────────────────────────────────────────────

@wr_bp.route('/')
def index():
    if not require_auth():
        return redirect(url_for('auth.login'))
    return render_template('work_reports.html')

# ── Projects ──
@wr_bp.route('/api/projects')
def list_projects():
    return jsonify(get_projects())

@wr_bp.route('/api/projects', methods=['POST'])
def add_project():
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'name required'}), 400
    projs = get_projects()
    if name not in projs:
        projs.append(name)
        save_json(paths()['projects'], projs)
    return jsonify(projs)

@wr_bp.route('/api/projects/<path:name>', methods=['DELETE'])
def del_project(name):
    projs = [p for p in get_projects() if p != name]
    save_json(paths()['projects'], projs)
    return jsonify(projs)

# ── Notes ──
@wr_bp.route('/api/notes/<date_str>')
def get_notes(date_str):
    return jsonify(load_json(os.path.join(paths()['notes'], f"{date_str}.json"), []))

@wr_bp.route('/api/notes', methods=['POST'])
def add_note():
    data = request.get_json(silent=True) or {}
    d = data.get('date') or dt.date.today().isoformat()
    f = os.path.join(paths()['notes'], f"{d}.json")
    notes = load_json(f, [])
    item = {
        "id": str(uuid.uuid4()),
        "type": data['type'],
        "project": data.get('project', ''),
        "content": data.get('content', ''),
        "created_at": dt.datetime.now().isoformat(),
    }
    notes.append(item)
    save_json(f, notes)
    return jsonify(item)

@wr_bp.route('/api/notes/<date_str>/<note_id>', methods=['DELETE'])
def del_note(date_str, note_id):
    f = os.path.join(paths()['notes'], f"{date_str}.json")
    notes = [n for n in load_json(f, []) if n["id"] != note_id]
    save_json(f, notes)
    return jsonify({"ok": True})

# ── Daily ──
@wr_bp.route('/api/daily/<date_str>', methods=['POST', 'GET'])
def daily(date_str):
    p = paths()['daily']
    f = os.path.join(p, f"{date_str}.md")
    if request.method == 'GET':
        exists = os.path.exists(f)
        content = ''
        if exists:
            with open(f, 'r', encoding='utf-8') as fh:
                content = fh.read()
        return jsonify({"content": content, "exists": exists})
    notes = load_json(os.path.join(paths()['notes'], f"{date_str}.json"), [])
    report = make_daily(date_str, notes)
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(report)
    return jsonify({"content": report})

# ── Weekly ──
@wr_bp.route('/api/weekly/<int:year>/<int:week>', methods=['POST', 'GET'])
def weekly(year, week):
    p = paths()['weekly']
    f = os.path.join(p, f"{year}-W{week:02d}.md")
    if request.method == 'GET':
        exists = os.path.exists(f)
        content = ''
        if exists:
            with open(f, 'r', encoding='utf-8') as fh:
                content = fh.read()
        return jsonify({"content": content, "exists": exists})
    week_start = dt.date.fromisocalendar(year, week, 1)
    week_dates = [(week_start + dt.timedelta(days=i)).isoformat() for i in range(7)]
    all_notes = []
    for d in week_dates:
        for n in load_json(os.path.join(paths()['notes'], f"{d}.json"), []):
            n["date"] = d
            all_notes.append(n)
    report = make_weekly(year, week, week_dates, all_notes)
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(report)
    return jsonify({"content": report})

# ── Kanban ──
@wr_bp.route('/api/kanban')
def get_kanban():
    return jsonify(load_json(paths()['kanban'], []))

@wr_bp.route('/api/kanban', methods=['POST'])
def add_kanban():
    data = request.get_json(silent=True) or {}
    tasks = load_json(paths()['kanban'], [])
    item = {
        "id": str(uuid.uuid4()),
        "title": data.get('title', ''),
        "note": data.get('note', ''),
        "priority": data.get('priority', '中'),
        "status": "todo",
        "updates": [],
        "created_at": dt.datetime.now().isoformat(),
        "updated_at": dt.datetime.now().isoformat(),
    }
    tasks.append(item)
    save_json(paths()['kanban'], tasks)
    return jsonify(item)

@wr_bp.route('/api/kanban/<task_id>', methods=['PATCH'])
def update_kanban(task_id):
    data = request.get_json(silent=True) or {}
    tasks = load_json(paths()['kanban'], [])
    for t in tasks:
        if t["id"] == task_id:
            if data.get('status'):
                t["status"] = data['status']
            if data.get('append_note'):
                t.setdefault("updates", []).append({
                    "text": data['append_note'],
                    "time": dt.datetime.now().strftime("%m-%d %H:%M"),
                    "status": t.get("status", ""),
                })
            t["updated_at"] = dt.datetime.now().isoformat()
    save_json(paths()['kanban'], tasks)
    return jsonify({"ok": True})

@wr_bp.route('/api/kanban/<task_id>', methods=['DELETE'])
def del_kanban(task_id):
    tasks = [t for t in load_json(paths()['kanban'], []) if t["id"] != task_id]
    save_json(paths()['kanban'], tasks)
    return jsonify({"ok": True})

# ── History ──
@wr_bp.route('/api/history/daily')
def list_daily():
    p = paths()['daily']
    try:
        files = sorted([f.replace('.md', '') for f in os.listdir(p) if f.endswith('.md')], reverse=True)
    except OSError:
        files = []
    return jsonify(files)

@wr_bp.route('/api/history/weekly')
def list_weekly():
    p = paths()['weekly']
    try:
        files = sorted([f.replace('.md', '') for f in os.listdir(p) if f.endswith('.md')], reverse=True)
    except OSError:
        files = []
    return jsonify(files)
