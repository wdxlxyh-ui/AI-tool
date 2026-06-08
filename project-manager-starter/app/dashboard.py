"""Dashboard blueprint — main overview page (tools only)."""
from flask import Blueprint, render_template, session, redirect, url_for

dashboard_bp = Blueprint('dashboard', __name__)

def require_auth():
    if 'user' not in session:
        return False
    return True

@dashboard_bp.route('/dashboard')
def index():
    if not require_auth():
        return redirect(url_for('auth.login'))
    # Tools data — replace these with your own project management modules
    tools = [
        {
            'id': 'tool1',
            'icon': '▣',
            'icon_style': 'files',
            'name': '工具一',
            'desc': '在此处描述你的第一个工具功能。',
            'status': '准备就绪',
            'status_class': 'on',
            'route': '#',
            'has_controls': False,
        },
        {
            'id': 'tool2',
            'icon': '◈',
            'icon_style': 'sim',
            'name': '工具二',
            'desc': '在此处描述你的第二个工具功能。',
            'status': '准备就绪',
            'status_class': 'on',
            'route': '#',
            'has_controls': False,
        },
        {
            'id': 'tool3',
            'icon': '⇄',
            'icon_style': 'ow',
            'name': '工具三',
            'desc': '在此处描述你的第三个工具功能。',
            'status': '准备就绪',
            'status_class': 'on',
            'route': '#',
            'has_controls': False,
        },
    ]
    return render_template('dashboard.html', tools=tools, user=session['user'])
