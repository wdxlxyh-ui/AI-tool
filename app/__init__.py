"""Flask app factory. Registers all blueprints."""
import os
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'egc-ai-tool-collection-dev-key')
    app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500 MB
    app.config['BASE_DIR'] = os.environ.get('EGC_BASE_DIR', os.path.dirname(os.path.dirname(__file__)))
    app.config['DATA_DIR'] = os.path.join(app.config['BASE_DIR'], 'data')
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)

    # Init database
    from .models import init_db
    init_db(app.config['DATA_DIR'])

    # Register blueprints
    from .auth import auth_bp
    from .file_manager import fm_bp
    from .dashboard import dashboard_bp
    from .simulator_manager import sm_bp
    from .sftp_manager import sftp_bp
    from .work_reports import wr_bp
    from .ems_deploy import ed_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(fm_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(sm_bp)
    app.register_blueprint(sftp_bp)
    app.register_blueprint(wr_bp)
    app.register_blueprint(ed_bp)

    # Root redirect
    @app.route('/')
    def index():
        from flask import redirect, url_for, session
        if 'user' in session:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    return app
