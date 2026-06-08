# 项目管理平台 — Flask Starter Kit

基于 Flask + 纯 CSS 动画 + Three.js 登录背景的管理平台框架。
登录、注册、仪表盘已就绪，开箱即用。

## 快速启动

```bash
# 1. 安装依赖
pip install flask werkzeug

# 2. 启动
python run.py --port 8080

# 3. 打开浏览器访问
# http://localhost:8080
# 默认账号: admin / admin123
```

## 项目结构

```
project-manager-starter/
├── run.py                  # 启动入口
├── requirements.txt        # 依赖清单
├── app/
│   ├── __init__.py         # Flask app 工厂，注册蓝图
│   ├── auth.py             # 登录/注册/登出（可复用，无需修改）
│   ├── dashboard.py        # 仪表盘路由（工具数据在此定义）
│   ├── models.py           # SQLite 用户模型（可复用）
│   └── templates/
│       ├── base.html       # 主布局（侧边栏、Toast、Modal、动画）
│       ├── login.html      # 登录页（Three.js 背景）
│       └── dashboard.html  # 仪表盘（工具卡片网格）
```

## 架构说明

### 整体框架

```
Flask App
 ├── auth_bp    → /login, /logout, /register
 └── dashboard_bp → /dashboard (工具展示)
      └── 你的蓝图 → 你的功能页面
```

- 使用 Flask Blueprint 注册新功能
- SQLite 用户认证开箱即用
- 管理员账号 `admin / admin123` 首次启动自动创建

### UI 框架

- **深色主题**：完整 CSS 变量系统（`--bg-page`, `--accent`, `--text` 等）
- **侧边栏导航**：支持 `.active` 高亮 + 磁性悬浮图标 + 左侧光条动画
- **工具卡片网格**：自动填充布局，hover 抬起 3px + 蓝光 + 图标缩放
- **Toast 通知**：右侧滑入，进度条倒计时 2.5s 自动消失
- **Modal 模态框**：缩放过渡动画
- **表格**：行 hover 抬起 + 首列左侧光条
- **内容区**：页面加载模糊渐入动画
- **加载 shimmer**：`.shimmer` 类复用
- **prefers-reduced-motion**：所有动画在用户开启精简动效时自动禁用

### 登录页

- Three.js GridScan 着色器背景（鼠标跟随视差）
- 毛玻璃登录卡片（`backdrop-filter: blur`）
- CDN importmap，无需本地安装 Three.js

## 👷 如何添加一个新工具？

### 第 1 步：创建蓝图文件

在 `app/` 下新建 `your_tool.py`：

```python
from flask import Blueprint, render_template, session, redirect, url_for

your_tool_bp = Blueprint('your_tool', __name__, url_prefix='/your-tool')

@your_tool_bp.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template('your_tool.html', user=session['user'])
```

### 第 2 步：注册蓝图

在 `app/__init__.py` 中添加：

```python
from .your_tool import your_tool_bp
app.register_blueprint(your_tool_bp)
```

### 第 3 步：添加侧边栏导航

在 `app/templates/base.html` 的 `<!-- 在此处添加你的工具导航项 -->` 位置插入：

```html
<a class="nav-item {% if active_page == 'your_tool' %}active{% endif %}"
   href="{{ url_for('your_tool.index') }}">
  <span class="icon">🔧</span><span>你的工具</span>
</a>
```

### 第 4 步：创建模板

在 `app/templates/` 下新建 `your_tool.html`：

```html
{% extends "base.html" %}
{% set active_page = "your_tool" %}
{% block page_title %}你的工具{% endblock %}
{% block page_subtitle %}功能描述{% endblock %}

{% block content %}
<!-- 你的页面内容 -->
{% endblock %}

{% block scripts %}
<script>
// 你的 JS 逻辑
</script>
{% endblock %}
```

## 常用组件速查

### Toast 通知

```javascript
showToast('操作成功')           // 普通 toast
showToast('保存成功', 'success') // 绿色成功
showToast('操作失败', 'error')   // 红色失败
```

### 模态框

```html
<div class="modal-overlay" id="myModal">
  <div class="modal">
    <h3>标题</h3>
    <!-- 内容 -->
    <div class="modal-actions">
      <button class="btn btn-outline" onclick="closeModal()">取消</button>
      <button class="btn btn-primary" onclick="confirm()">确认</button>
    </div>
  </div>
</div>
<script>
function openModal(){ document.getElementById('myModal').classList.add('open') }
function closeModal(){ document.getElementById('myModal').classList.remove('open') }
</script>
```

### data-table 表格

```html
<table class="data-table">
  <thead><tr><th>列1</th><th>列2</th></tr></thead>
  <tbody>
    <tr><td>数据</td><td>数据</td></tr>
  </tbody>
</table>
```

### Shimmer 加载占位

```html
<div class="shimmer" style="width:100%;height:40px;border-radius:var(--radius);background:var(--bg-elevated);"></div>
```

### CSS 变量参考

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `--bg-page` | 页面背景 | `#0f1117` |
| `--bg-card` | 卡片背景 | `#1a1d27` |
| `--bg-elevated` | 较高层级背景 | `#222530` |
| `--bg-hover` | hover 背景 | `#2a2d38` |
| `--accent` | 主题色 | `#4b8cf7` |
| `--text` | 主文字 | `#e1e4e8` |
| `--text-secondary` | 次要文字 | `#8b8fa3` |
| `--text-dim` | 弱化文字 | `#555a6a` |
| `--radius` | 圆角 | `8px` |
| `--radius-sm` | 小圆角 | `6px` |
| `--transition` | 默认过渡时间 | `150ms ease` |

## GitHub 工作流建议

### 首次推送

```bash
git init
git add .
git commit -m "init: project-manager-starter"
git remote add origin <你的仓库>
git push -u origin main
```

### 版本迭代

每次让 AI 添加新功能时，创建新分支：

```bash
git checkout -b feat/your-new-feature
# AI 修改代码后
git add .
git commit -m "feat: add your new feature"
git checkout main
git merge feat/your-new-feature
```

---

## 给 AI 的提示词模板

当你需要让 AI 在这个框架上添加功能时，使用以下模板：

> "我有一个基于 Flask 的项目管理平台框架，使用深色主题 UI，包含 Three.js 登录页和工具卡片仪表盘。
> 框架使用 Blueprint 注册新功能，模板继承 base.html。
>
> 请在 app/ 下创建 [功能名称] 模块，包括：
> 1. 蓝图文件 [功能名].py
> 2. 模板 [功能名].html
> 3. 注册到 app/__init__.py
> 4. 在 base.html 的导航区域添加菜单项
> 5. 在 dashboard.py 的 tools 列表中添加工具卡片
>
> 具体功能：[描述需求]"
