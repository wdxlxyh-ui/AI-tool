# Phase 1 UI Animation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade EGC platform UI with sidebar magnetic hover + active glow, dashboard stat count-up, tool card hover glow, and toast notification animation.

**Architecture:** All changes are inline CSS + vanilla JS in two Jinja2 template files (`base.html`, `dashboard.html`). No new files, no external dependencies, no build tools.

**Tech Stack:** Flask + Jinja2 + vanilla JS + CSS

---

### Task 1: Sidebar — Magnetic Hover + Active Glow

**Files:**
- Modify: `app/templates/base.html` (CSS in `<style>` block, JS in existing `<script>` block)

- [ ] **Step 1: Add sidebar hover glow CSS**

Insert after the existing `.nav-item` rules in the `<style>` block:

```css
.nav-item {
  position: relative;
  overflow: hidden;
}
.nav-item .icon {
  position: relative;
  z-index: 1;
  transition: transform .15s ease;
}
.nav-item::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  opacity: 0;
  box-shadow: 0 0 24px rgba(75,140,247,.2);
  transition: opacity .2s ease;
  pointer-events: none;
}
.nav-item:hover::before {
  opacity: 1;
}
.nav-item.active::after {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  border-radius: 0 2px 2px 0;
  background: var(--accent);
  animation: activeGlowIn .35s ease-out forwards;
}
@keyframes activeGlowIn {
  from { height: 0; opacity: 0; }
  to   { height: 60%; opacity: 1; }
}
```

- [ ] **Step 2: Add sidebar magnetic icon JS**

Insert at the top of the existing `showToast` `<script>` block:

```javascript
(function(){
  var navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(function(item){
    item.addEventListener('mousemove', function(e){
      var r = item.getBoundingClientRect();
      var dx = (e.clientX - r.left - r.width/2) / r.width * 3;
      var dy = (e.clientY - r.top - r.height/2) / r.height * 3;
      var icon = item.querySelector('.icon');
      if (icon) icon.style.transform = 'translate('+dx+'px,'+dy+'px)';
    });
    item.addEventListener('mouseleave', function(){
      var icon = item.querySelector('.icon');
      if (icon) icon.style.transform = '';
    });
  });
})();
```

- [ ] **Step 3: Verify**

Restart service: `systemctl restart egc-server`
Open `/login` → log in → hover sidebar items → active item should have glow bar

---

### Task 2: Dashboard — Stat Card Count-Up

**Files:**
- Modify: `app/templates/dashboard.html` (add JS)

- [ ] **Step 1: Add count-up animation JS**

Append to the existing `<script>` block at the bottom of the file (before `checkOW`):

```javascript
(function(){
  var cards = document.querySelectorAll('.stat-card .value');
  cards.forEach(function(el){
    var text = el.textContent.trim();
    var num = parseFloat(text);
    if (isNaN(num)) return;
    var isPercent = text.indexOf('%') > -1;
    var suffix = isPercent ? '%' : '';
    var parts = text.split('/');
    var hasSlash = parts.length === 2;
    el.textContent = '0' + suffix;
    var startTime = performance.now();
    var duration = 800;
    var target = num;
    function tick(now) {
      var t = Math.min((now - startTime) / duration, 1);
      var ease = 1 - Math.pow(1 - t, 3);
      var current = target * ease;
      var display = Number.isInteger(target) ? Math.round(current) : current.toFixed(1);
      el.textContent = display + suffix;
      if (hasSlash) {
        el.textContent += ' / ' + parts[1].trim();
      }
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
})();
```

- [ ] **Step 2: Verify**

Restart service → open dashboard → stat card numbers should animate from 0 → target
Check: CPU load (decimal), memory (has slash), tool count (integer), disk space (decimal with %)

---

### Task 3: Dashboard — Tool Card Glow Hover

**Files:**
- Modify: `app/templates/dashboard.html` (CSS in `<style>` block)

- [ ] **Step 1: Add tool card glow CSS**

Insert into the existing `<style>` block in `dashboard.html`:

```css
.tool-card {
  transform: translateY(0);
  box-shadow: 0 0 0 rgba(75,140,247,0);
  transition: transform .28s cubic-bezier(.16,1,.3,1), box-shadow .28s ease, border-color .28s ease;
}
.tool-card:hover {
  transform: translateY(-3px);
  border-color: var(--accent);
  box-shadow: 0 6px 24px rgba(75,140,247,.18);
}
.tool-card .icon {
  transition: transform .28s ease;
}
.tool-card:hover .icon {
  transform: scale(1.1);
}
```

- [ ] **Step 2: Add reduced-motion safeguard**

Append to the same `<style>` block:

```css
@media (prefers-reduced-motion) {
  .tool-card { transition: none !important; }
  .tool-card:hover { transform: none !important; }
}
```

- [ ] **Step 3: Verify**

Restart service → open dashboard → hover tool cards → card raises 3px with blue glow, icon scales up 1.1x

---

### Task 4: Toast Notification Upgrade

**Files:**
- Modify: `app/templates/base.html` (CSS + JS + HTML)

- [ ] **Step 1: Replace toast HTML**

Find the existing toast div:
```html
<div id="toast" style="position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);background:var(--bg-elevated);border:1px solid var(--border);padding:10px 20px;border-radius:8px;font-size:12px;color:var(--text);opacity:0;transition:all .3s ease;pointer-events:none;z-index:100;box-shadow:0 6px 20px rgba(0,0,0,.3);"></div>
```

Replace with:
```html
<div id="toast" class="toast"><span id="toast-text"></span><div class="toast-progress"></div></div>
```

- [ ] **Step 2: Add toast CSS**

Add to the `<style>` block in `base.html`:

```css
.toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 100;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  padding: 12px 20px;
  padding-bottom: 16px;
  border-radius: var(--radius);
  font-size: 12px;
  color: var(--text);
  box-shadow: 0 6px 24px rgba(0,0,0,.35);
  transform: translateX(calc(100% + 30px));
  transition: transform .35s cubic-bezier(.16,1,.3,1);
  pointer-events: none;
  min-width: 180px;
  overflow: hidden;
}
.toast.open {
  transform: translateX(0);
}
.toast .toast-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  background: var(--accent);
  width: 100%;
  transition: none;
}
.toast.success .toast-progress { background: var(--success); }
.toast.error .toast-progress { background: var(--danger); }

@media (prefers-reduced-motion) {
  .toast { transition: none; }
}
```

- [ ] **Step 3: Update showToast JS**

Find the existing `showToast`/`showNotice` functions:

```javascript
function showToast(msg){var t=document.getElementById('toast');t.textContent=msg;t.style.opacity='1';t.style.transform='translateX(-50%) translateY(0)';clearTimeout(t._t);t._t=setTimeout(function(){t.style.opacity='0';t.style.transform='translateX(-50%) translateY(80px)'},2000)}
function showNotice(msg){showToast(msg)}
```

Replace with:

```javascript
function showToast(msg,type){
  type = type || 'info';
  var t = document.getElementById('toast');
  var txt = document.getElementById('toast-text');
  var prog = t.querySelector('.toast-progress');
  t.className = 'toast ' + type;
  txt.textContent = msg;
  prog.style.transition = 'none';
  prog.style.width = '100%';
  t.classList.add('open');
  clearTimeout(t._t);
  requestAnimationFrame(function(){
    prog.style.transition = 'width 2.5s linear';
    prog.style.width = '0%';
  });
  t._t = setTimeout(function(){
    t.classList.remove('open');
  }, 2500);
}
function showNotice(msg){showToast(msg)}
```

- [ ] **Step 4: Verify**

Restart service → open any page → trigger a toast (e.g. log in → wrong password) → should slide in from right with progress bar

---

### Task 5: Final Verification

- [ ] **Step 1: Restart and smoke test**

```bash
systemctl restart egc-server && sleep 1 && systemctl is-active egc-server
```

- [ ] **Step 2: Visual check**
1. Open `http://localhost:8080/login` → log in with admin
2. Hover sidebar items → icon moves with mouse, glow appears, active item has left bar
3. Dashboard stat cards → numbers count up from 0 on load
4. Hover tool cards → cards lift with blue glow, icon scales
5. Toast notification → slides in from right, progress bar depletes, auto-dismisses

---

## Rollback

If anything breaks, revert the changes:

```bash
cd /root/EGC
git checkout -- app/templates/base.html app/templates/dashboard.html
systemctl restart egc-server
```
