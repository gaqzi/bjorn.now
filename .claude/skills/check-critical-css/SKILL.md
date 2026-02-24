---
name: check-critical-css
description: >
  Check for divergences between critical.css and main.css that cause FOUC
  (flash of unstyled content). Trigger this skill when:
  - The user asks to commit and `git status` or `git diff` shows changes to
    any `.css` file under `themes/sanitarium/assets/css/`
  - The user asks about FOUC, style flashing, or critical CSS sync
  - You just finished editing critical.css or main.css
  Run this check BEFORE creating the commit so divergences are caught early.
---

# /check-critical-css

## Why this matters

This blog inlines `critical.css` in the HTML `<head>` so the page renders
immediately with correct layout. The full `main.css` loads asynchronously
afterwards. If the two files disagree on a visible property, users see a
flash — the page paints with critical styles, then jumps when main.css
overrides them.

The worst offenders are **layout properties** (`display`, `flex-direction`,
`justify-content`, `align-items`, `gap`, `grid-template-*`, `position`,
`width`, `max-width`, `margin`, `padding`). A change from `display: block` to
`display: flex` reorganises every child element — that's a full layout shift,
the most jarring kind of FOUC. Text-styling differences (`text-decoration`,
`font-family`, `font-size`, `color`) are less dramatic but still noticeable.

**Files:**
- `themes/sanitarium/assets/css/critical.css` — inlined via `layouts/partials/head.html`
- `themes/sanitarium/assets/css/main.css` — loaded async via `layouts/partials/head/css.html`

## How to check

### 1. Read both files in full

Read `themes/sanitarium/assets/css/critical.css` and
`themes/sanitarium/assets/css/main.css`.

### 2. Build a selector map from each file

Extract every selector and its properties from both files. This blog uses
**native CSS nesting** with `&`, so you need to resolve nested selectors to
their full form. For example:

```css
/* In main.css */
header.masthead {
    display: flex;
    & a {
        text-decoration: none;
    }
}
```

Produces two selectors: `header.masthead` (`display: flex`) and
`header.masthead a` (`text-decoration: none`). Resolve all nesting before
comparing — otherwise you'll miss divergences hiding inside nested blocks.

### 3. Compare overlapping selectors

For every selector that appears in **both** files, compare property values.
Build a list of divergences. There are three kinds:

1. **Same property, different value** — e.g. critical says
   `text-decoration: underline`, main says `text-decoration: none`
2. **Layout property in main.css, missing from critical.css** — causes the
   element to jump from browser-default layout to the intended one
3. **Orphaned selector in critical.css** — a selector in critical.css that
   no longer exists in main.css or the site templates, adding dead weight
   and potentially styling elements in unintended ways

### 4. Filter out safe differences

Not every difference is a problem. Skip these:

- **Selectors only in main.css** — main.css styles far more elements than
  critical.css covers; that's by design
- **Hover / focus / active / focus-visible states** — only trigger on
  interaction, invisible during page load
- **Animation and transition properties** — progressive enhancement
- **The footer** — critical.css intentionally hides it
  (`visibility: hidden; height: 0`) and main.css reveals it. This is the
  FOUC-prevention pattern for below-the-fold content
- **Subtle cosmetic differences** (opacity, border-radius, minor colour
  tweaks on non-structural elements) — use your judgement; if a user
  wouldn't notice the shift, it's fine

### 5. Report

**If no divergences:** say so in one line and move on.

**If divergences found**, group by severity and list each:

- **Selector** — the full resolved selector
- **Property** — the property name
- **Critical value** — what critical.css has, or "missing"
- **Main value** — what main.css has
- **Impact** — what the user would see (e.g. "masthead shifts from stacked
  to side-by-side layout")
- **Fix** — what to change in critical.css

Severity groups:
1. **Layout shifts** — display, flex/grid, position, margin, padding, width
2. **Text styling** — font, text-decoration, color, text-transform
3. **Minor cosmetic** — everything else

### 6. Fix

Edit `critical.css` to resolve each divergence. Keep it minimal — only add
the specific properties needed to prevent the flash, don't duplicate entire
rule blocks from main.css. After editing, re-read both files to confirm no
divergences remain.

### 7. Visual verification (when text comparison isn't enough)

Text comparison catches property divergences, but some FOUCs come from
browser defaults interacting with missing styles (e.g., a `<button>` getting
a default border, or a `<ul>` showing bullets). To verify visually, use
Playwright to see exactly what the critical-CSS-only state looks like:

1. **Block main.css** — route-abort the stylesheet so only inlined critical
   CSS renders:
   ```js
   await page.route('**/css/main*.css', route => route.abort());
   await page.goto('http://localhost:1313/', { waitUntil: 'domcontentloaded' });
   ```
2. **Screenshot** the critical-CSS-only state
3. **Unblock and reload** to get the fully styled state:
   ```js
   await page.unrouteAll();
   await page.goto('http://localhost:1313/', { waitUntil: 'networkidle' });
   ```
4. **Screenshot** the fully styled state
5. **Compare** — any visible difference is a potential FOUC

Check both desktop (1280px+) and mobile (375px) viewports since the sidebar
navigation has completely different layouts at each breakpoint.

## Loading strategy

Both development (`hugo server`) and production (`hugo`) use the same async
loading pattern for main.css:

```html
<link rel="preload" href="..." as="style" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link rel="stylesheet" href="..."></noscript>
```

The only difference is that production adds `minify | fingerprint` for cache
busting and SRI integrity attributes. The loading *behavior* is identical,
which means FOUCs are visible locally during development — not just in
production. This is intentional. If dev used synchronous loading, FOUCs
would be hidden locally and only appear after deploy (which is how the
original bug went unnoticed).
