"""Kiro Gateway Manager blueprint - 管理 Kiro Gateway 服务."""
import os
import subprocess as sp
import json
import socket
from flask import Blueprint, render_template, session, redirect, url_for, current_app, request, jsonify

kiro_bp = Blueprint('kiro_gateway', __name__, url_prefix='/kiro-gateway')

KIRO_GATEWAY_DIR = '/home/egc/kiro-gateway'
KIRO_GATEWAY_PORT = 8000

def require_auth():
    if 'user' not in session:
        return False
    return True

def get_host_ip():
    """获取主机 IP 地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

def get_kiro_status():
    """获取 Kiro Gateway 运行状态"""
    try:
        result = sp.run(['pgrep', '-f', 'kiro-gateway.*main.py'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return {
                'running': True,
                'pid': result.stdout.strip().split('\n')[0],
                'port': KIRO_GATEWAY_PORT,
                'url': f'http://{get_host_ip()}:{KIRO_GATEWAY_PORT}'
            }
    except:
        pass
    return {'running': False, 'port': KIRO_GATEWAY_PORT}

def get_available_models():
    """从 Kiro Gateway API 获取可用模型列表"""
    import httpx
    
    api_key = get_api_key()
    if not api_key:
        return _get_fallback_models()
    
    try:
        url = f'http://localhost:{KIRO_GATEWAY_PORT}/v1/models'
        headers = {'Authorization': f'Bearer {api_key}'}
        response = httpx.get(url, headers=headers, timeout=5.0)
        
        if response.status_code == 200:
            data = response.json()
            models = []
            for m in data.get('data', []):
                model_id = m.get('id', '')
                models.append({
                    'id': model_id,
                    'name': _format_model_name(model_id),
                    'description': _get_model_description(model_id)
                })
            return models
    except:
        pass
    
    return _get_fallback_models()

def _format_model_name(model_id):
    """格式化模型名称"""
    names = {
        'auto-kiro': 'Auto (自动选择)',
        'claude-haiku-4.5': 'Claude Haiku 4.5',
        'claude-opus-4.5': 'Claude Opus 4.5',
        'claude-opus-4.6': 'Claude Opus 4.6',
        'claude-opus-4.7': 'Claude Opus 4.7',
        'claude-sonnet-4': 'Claude Sonnet 4',
        'claude-sonnet-4.5': 'Claude Sonnet 4.5',
        'claude-sonnet-4.6': 'Claude Sonnet 4.6',
        'deepseek-3.2': 'DeepSeek 3.2',
        'glm-5': 'GLM-5',
        'minimax-m2.1': 'MiniMax M2.1',
        'minimax-m2.5': 'MiniMax M2.5',
        'qwen3-coder-next': 'Qwen3 Coder Next',
    }
    return names.get(model_id, model_id)

def _get_model_description(model_id):
    """获取模型描述"""
    descs = {
        'auto-kiro': 'Kiro 自动选择最佳模型',
        'claude-haiku-4.5': '极速响应，适合快速迭代',
        'claude-opus-4.5': 'Opus 系列 - 强力性能',
        'claude-opus-4.6': 'Opus 系列 - 更强性能',
        'claude-opus-4.7': 'Opus 系列 - 最新最强',
        'claude-sonnet-4': 'Sonnet 系列 - 平衡性能',
        'claude-sonnet-4.5': 'Sonnet 系列 - 编码和通用任务',
        'claude-sonnet-4.6': 'Sonnet 系列 - 最新版本',
        'deepseek-3.2': 'DeepSeek 推理模型',
        'glm-5': '智谱 GLM-5 模型',
        'minimax-m2.1': 'MiniMax MoE 模型',
        'minimax-m2.5': 'MiniMax 最新 MoE 模型',
        'qwen3-coder-next': '通义千问编码专用',
    }
    return descs.get(model_id, 'Claude model via Kiro API')

def _get_fallback_models():
    """备用模型列表"""
    return [
        {'id': 'auto-kiro', 'name': 'Auto (自动选择)', 'description': 'Kiro 自动选择最佳模型'},
        {'id': 'claude-sonnet-4.5', 'name': 'Claude Sonnet 4.5', 'description': '平衡性能，适合编码和通用任务'},
        {'id': 'claude-haiku-4.5', 'name': 'Claude Haiku 4.5', 'description': '极速响应，适合快速迭代'},
        {'id': 'claude-opus-4.5', 'name': 'Claude Opus 4.5', 'description': '最强性能，复杂任务'},
        {'id': 'minimax-m2.1', 'name': 'MiniMax M2.1', 'description': 'MoE 模型，复杂规划和多步骤任务'},
        {'id': 'qwen3-coder-next', 'name': 'Qwen3 Coder Next', 'description': '编码专用，大型项目开发'},
    ]

def get_api_key():
    """从 .env 文件读取 API Key"""
    env_file = os.path.join(KIRO_GATEWAY_DIR, '.env')
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('PROXY_API_KEY='):
                        key = line.split('=', 1)[1].strip().strip('"').strip("'")
                        return key
        except:
            pass
    return None

@kiro_bp.route('/')
def index():
    if not require_auth():
        return redirect(url_for('auth.login'))
    
    status = get_kiro_status()
    models = get_available_models()
    api_key = get_api_key()
    host_ip = get_host_ip()
    
    return render_template('kiro_gateway.html', 
                          status=status, 
                          models=models,
                          api_key=api_key,
                          host_ip=host_ip,
                          user=session['user'])

@kiro_bp.route('/api/start', methods=['POST'])
def start_gateway():
    """启动 Kiro Gateway"""
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    
    try:
        # 检查是否已在运行
        status = get_kiro_status()
        if status['running']:
            return jsonify({'ok': True, 'message': '服务已在运行', 'pid': status['pid']})
        
        # 启动服务
        log_file = '/tmp/kiro-gateway.log'
        python_path = os.path.join(KIRO_GATEWAY_DIR, 'venv/bin/python')
        main_script = os.path.join(KIRO_GATEWAY_DIR, 'main.py')
        
        cmd = f'nohup {python_path} {main_script} > {log_file} 2>&1 & echo $!'
        result = sp.run(cmd, shell=True, cwd=KIRO_GATEWAY_DIR, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            pid = result.stdout.strip()
            return jsonify({'ok': True, 'message': '服务启动成功', 'pid': pid})
        else:
            return jsonify({'ok': False, 'error': result.stderr})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@kiro_bp.route('/api/stop', methods=['POST'])
def stop_gateway():
    """停止 Kiro Gateway"""
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    
    try:
        result = sp.run(['pkill', '-f', 'kiro-gateway.*main.py'], capture_output=True, text=True)
        return jsonify({'ok': True, 'message': '服务已停止'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@kiro_bp.route('/api/status')
def gateway_status():
    """获取服务状态"""
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    
    status = get_kiro_status()
    status['api_key'] = get_api_key()
    status['host_ip'] = get_host_ip()
    return jsonify(status)

@kiro_bp.route('/api/test', methods=['POST'])
def test_api():
    """测试 API 连接"""
    if not require_auth():
        return jsonify({'error': 'unauthorized'}), 401
    
    try:
        import httpx
        api_key = get_api_key()
        if not api_key:
            return jsonify({'ok': False, 'error': '未找到 API Key'})
        
        url = f'http://localhost:{KIRO_GATEWAY_PORT}/v1/models'
        headers = {'Authorization': f'Bearer {api_key}'}
        
        response = httpx.get(url, headers=headers, timeout=5.0)
        if response.status_code == 200:
            return jsonify({'ok': True, 'message': 'API 连接正常'})
        else:
            return jsonify({'ok': False, 'error': f'HTTP {response.status_code}'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@kiro_bp.route('/api/logs')
def get_logs():
    """获取服务日志"""
    if not require_auth():
        return 'Unauthorized', 401
    
    log_file = '/tmp/kiro-gateway.log'
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                # 读取最后 500 行
                lines = f.readlines()
                return ''.join(lines[-500:])
        except:
            return '无法读取日志文件'
    return '日志文件不存在'
