# UI Animation Upgrade — EGC Platform

## Overview

Upgrade the EGC (Edge Grid Controller) Flask platform's frontend with high-quality,
non-intrusive animations inspired by [React Bits](https://reactbits.dev) components.
All effects must be implemented as pure CSS + vanilla JS — no React, no new framework
dependencies. Three.js (via CDN importmap) is only used where WebGL is required.

## Priority & Phasing

```
Phase 1 ──── Sidebar glow · Dashboard count-up · Card hover · Toast upgrade
Phase 2 ──── Page title animation · Modal transitions · Table hover
Phase 3 ──── Loading shimmer · Cursor trail (optional)
```

## Phase 1 — Detail

### 1.1 Sidebar Navigation — Magnetic Hover + Active Glow

**Files:** `app/templates/base.html`

**Behaviour:**
- On hover: nav-item gets a subtle `box-shadow` radial glow matching the accent color,
  intensity fades in over 150ms
- On hover: icon slightly shifts following cursor position (magnetic effect, ±2px)
- Active nav-item: left border accent glow (`::before` pseudo-element, animated width
  0→3px on page load)

**CSS additions** (inline in `<style>`):
```css
.nav-item {
  position: relative;
  overflow: hidden;
}
.nav-item::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  opacity: 0;
  box-shadow: 0 0 18px var(--accent-glow);
  transition: opacity var(--transition);
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
  height: 60%;
  border-radius: 2px;
  background: var(--accent);
  animation: activeGlowIn .3s ease-out;
}
@keyframes activeGlowIn {
  from { height: 0; opacity: 0; }
  to   { height: 60%; opacity: 1; }
}
```

**JS additions** (in the existing inline `<script>` block):
- `mousemove` handler on `.nav-item` to shift icon position by ±2px based on
  cursor offset within the item (magnetic feel)

**No external dependencies.**

---

### 1.2 Dashboard — Animated Stat Count-Up

**Files:** `app/templates/dashboard.html`

**Behaviour:**
- On page load (or when scrolled into view), each `.stat-card .value` that contains
  a number animates from 0 to its final value over 800ms with ease-out cubic bezier
- Numbers are re-parsed from the existing content (e.g. "2.3" or "45%")

**JS additions:**
```javascript
function animateValue(el, start, end, duration) {
  const startTime = performance.now();
  const isPercent = String(end).includes('%');
  const raw = parseFloat(end);
  function tick(now) {
    const t = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    const current = start + (raw - start) * ease;
    el.textContent = (Number.isInteger(raw) ? Math.round(current) : current.toFixed(1)) + (isPercent ? '%' : '');
    if (t < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
```

**No external dependencies.**

---

### 1.3 Dashboard — Tool Card Glow Hover

**Files:** `app/templates/dashboard.html`

**Behaviour:**
- On hover: `.tool-card` shows a radial gradient glow that follows the cursor
- `translateY(-1px)` → `translateY(-3px)` + `box-shadow` enhancement
- Glow is implemented via CSS only — no per-frame JS needed for the basic version

**CSS additions:**
```css
.tool-card {
  transform: translateY(0);
  box-shadow: 0 0 0 rgba(75,140,247,0);
  transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
}
.tool-card:hover {
  transform: translateY(-3px);
  border-color: var(--accent);
  box-shadow: 0 4px 20px rgba(75,140,247,.15);
}
.tool-card .icon {
  transition: transform .25s ease;
}
.tool-card:hover .icon {
  transform: scale(1.08);
}
```

**No external dependencies.**

---

### 1.4 Toast Notification Upgrade

**Files:** `app/templates/base.html`

**Behaviour:**
- Toast slides in from right (not fade), has a progress timer bar at bottom
- Progress bar animates from 100% → 0% over the display duration
- Toast auto-dismisses when progress bar reaches 0
- Different colour for success (green) vs error (red)

**CSS additions:**
```css
.toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 100;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  padding: 12px 20px;
  border-radius: var(--radius);
  font-size: 12px;
  color: var(--text);
  box-shadow: 0 6px 24px rgba(0,0,0,.35);
  transform: translateX(120%);
  transition: transform .3s cubic-bezier(.16,1,.3,1);
  pointer-events: none;
  min-width: 200px;
  overflow: hidden;
}
.toast.open {
  transform: translateX(0);
}
.toast .progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2px;
  background: var(--accent);
  transition: width 2s linear;
}
.toast.success .progress { background: var(--success); }
.toast.error .progress { background: var(--danger); }
```

**JS:**
- Replace current `showToast()` to use the new markup

**No external dependencies.**

---

## Phase 2 — Summary

| Feature | Approach | Est. CSS | Est. JS |
|---------|----------|----------|---------|
| Page title animation | CSS `@keyframes` blur-in on `.content` mount | 15 lines | 0 |
| Modal transitions | Replace `display: none/block` with opacity + scale | 15 lines | 5 lines |
| Table row lift hover | `transform: translateY(-1px)` + left glow | 8 lines | 0 |

All Phase 2 are purely CSS-driven, zero JS runtime cost.

---

## Phase 3 — Summary

| Feature | Approach | Notes |
|---------|----------|-------|
| Loading shimmer | CSS gradient shimmer on skeleton elements | ~15 lines CSS |
| Cursor trail | Canvas-based particle trail following mouse | ~60 lines JS |

---

## Implementation Rules

1. **No React.** All effects are pure CSS + vanilla JS.
2. **No build tools.** Everything inline in templates or single `effects.js`.
3. **Three.js only** for WebGL backgrounds (GridScan already done).
4. **`prefers-reduced-motion` respected** — all animations disabled when user
   prefers reduced motion:
   ```css
   @media (prefers-reduced-motion) { .nav-item, .tool-card, .toast { transition: none; } }
   ```
5. **changes scoped to Phase 1 first.** Phase 2 & 3 specs are reference only
   until Phase 1 is merged and approved.

## Files Changed

```
Phase 1:
  app/templates/base.html        +30 lines CSS +25 lines JS (toast + sidebar)
  app/templates/dashboard.html   +20 lines CSS +30 lines JS (cards + count-up)

Phase 2:
  app/templates/base.html        +15 lines CSS (modal)
  app/templates/dashboard.html   + 8 lines CSS (table)
  app/templates/*.html           + 3 lines each (page title class)

Phase 3:
  app/templates/base.html        +15 lines CSS +60 lines JS
```
