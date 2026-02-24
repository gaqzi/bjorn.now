---
title: "Hugo dev server CSS fails to load on real iPhone via Tailscale"
date: 2026-02-24
category: integration-issues
severity: medium
component:
  - Hugo dev server
  - Tailscale VPN
  - Safari iOS
  - CSS delivery
tags:
  - hugo
  - tailscale
  - ios-safari
  - css
  - dev-server
  - networking
symptoms:
  - "All CSS files fail to load on real iPhone accessing Hugo dev server via Tailscale URL"
  - "Page renders completely unstyled — not just feature CSS but also main.css"
  - "HTML source correctly contains <link rel=\"stylesheet\"> tags"
  - "curl confirms CSS files serve with 200 OK and correct text/css content-type"
  - "Playwright (Chromium and WebKit) loads CSS correctly via the same Tailscale URL"
  - "Static file server on the same port/interface works perfectly on the phone"
root_cause: "Hugo's dev server HTTP implementation fails to serve CSS to real mobile Safari over Tailscale VPN tunnels, despite correct headers and content"
resolution_time: "1 hour"
confidence: medium
---

# Hugo dev server CSS fails to load on real iPhone via Tailscale

## Problem

Hugo's built-in development server (`hugo server --bind 0.0.0.0`) serves CSS files that fail to load on a real iPhone accessing the site via Tailscale VPN (e.g., `http://hostname.example-tailnet.ts.net:1313/`). Pages load without any styling applied — the HTML renders but all `<link rel="stylesheet">` resources silently fail.

This occurs even though:
- The HTML source contains correct `<link>` tags
- `curl` from any client returns the CSS with `Content-Type: text/css; charset=utf-8` and HTTP 200
- Playwright automation (both Chromium and WebKit engines) renders CSS correctly via the same Tailscale URL
- The same static files served by Python's `http.server` on the same interface work perfectly

## Investigation Steps

1. **Safari browser caching** — Ruled out with private tab test. CSS still failed to apply.

2. **Conflicting Hugo server instances** — Found two Hugo servers on port 1313 (one IPv4 localhost-only, one IPv6 all-interfaces). Killed both, restarted single server. Problem persisted.

3. **HTTP response headers** — Curled CSS URLs from the Tailscale IP. Headers correct: `Content-Type: text/css; charset=utf-8`, HTTP 200, correct `Content-Length`.

4. **HTML source inspection** — Confirmed `<link rel="stylesheet" href="/css/main.css">` tags present with no path errors.

5. **Playwright WebKit test** — Ran Playwright with WebKit (same engine as Safari) via Tailscale URL. CSS loaded perfectly: 26 rules in slideshow.css, 140 in main.css. Ruled out browser engine compatibility.

6. **CSS nesting compatibility** — Considered native CSS nesting (`&` syntax, 48 instances in main.css) as a Safari issue. Ruled out — Playwright WebKit handled it and the phone runs modern iOS.

7. **Static file server test** — Built with `hugo -D`, served with `python3 -m http.server 8765 --bind 0.0.0.0`. CSS loaded perfectly on the same iPhone via the same Tailscale hostname.

## Root Cause

Hugo's built-in development server has an issue serving CSS to real mobile Safari over Tailscale (WireGuard) VPN tunnels. The exact mechanism is unclear — it's not MIME types, not response headers, not CSS syntax, and not browser engine compatibility.

Something about Hugo's HTTP server implementation or connection handling doesn't work when real mobile Safari requests resources over a WireGuard tunnel. The problem does not manifest for localhost, Playwright automation, curl, or standard HTTP servers serving the same files over the same network path.

## Workaround

For real-device mobile testing over Tailscale, bypass Hugo's dev server:

```bash
# 1. Build the site with drafts
hugo -D --destination /tmp/hugo-public

# 2. Serve with a standard HTTP server
python3 -m http.server 8765 --bind 0.0.0.0 --directory /tmp/hugo-public

# 3. Access from mobile device
# http://<hostname>.<tailnet>.ts.net:8765/path/to/page/
```

For automatic rebuilds without Hugo's HTTP server:

```bash
# Terminal 1: Hugo watches and rebuilds on change
hugo -D --destination /tmp/hugo-public --watch

# Terminal 2: Serve the static output
python3 -m http.server 8765 --bind 0.0.0.0 --directory /tmp/hugo-public
```

Note: This lacks Hugo's live-reload. Each change requires a manual browser refresh.

## Key Lessons

**Playwright mobile emulation is not real device testing.** Even with a matching browser engine (WebKit), Playwright runs on the host machine and shares its network stack. A real iPhone over Tailscale traverses a completely different network path. Emulation catches layout and JS issues but not network-layer or server-behavior issues.

**Hugo's dev server is optimized for localhost.** It handles assets through its own Go HTTP handler, which may differ from a standard static file server in ways that matter over network tunnels. Static builds eliminate this variable.

**The failure mode is silent.** No errors in Hugo's terminal output. The page loads, HTML renders, but CSS doesn't apply. The only indication is visual.

## When This Applies

This issue occurs when ALL of these conditions are met:
- Testing on a **real mobile device** (not emulator or Playwright)
- Device accesses Hugo dev server **over a network** (Tailscale, VPN, LAN)
- Feature depends on **CSS or static assets loading**

You do NOT need to worry about this when:
- Developing on localhost in a desktop browser
- Using Playwright or automated testing
- Deploying to production (uses static builds + real web server)

## Testing Checklist for Real Mobile Devices

- [ ] Build static output with `hugo` (not `hugo server`)
- [ ] Serve with a standard HTTP server (`python3 -m http.server` or equivalent)
- [ ] Verify CSS loads on the actual device
- [ ] Test interactive states (swipe, tap, orientation change)
- [ ] Test both light and dark mode
- [ ] Check with reduced motion enabled
- [ ] If emulation passed but real device fails, suspect the serving layer
