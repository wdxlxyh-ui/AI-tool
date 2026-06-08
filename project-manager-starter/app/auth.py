"""Authentication blueprint — login, logout, register."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        from .models import verify_user
        if verify_user(username, password):
            session['user'] = username
            return redirect(url_for('dashboard.index'))
        flash('用户名或密码错误', 'error')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' in session:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if not username or not password:
            flash('用户名和密码不能为空', 'error')
        elif password != confirm:
            flash('两次密码不一致', 'error')
        elif len(password) < 4:
            flash('密码长度至少4位', 'error')
        else:
            from .models import create_user
            if create_user(username, password):
                flash('注册成功，请登录', 'success')
                return redirect(url_for('auth.login'))
            flash('用户名已存在', 'error')
    return render_template('login.html')
