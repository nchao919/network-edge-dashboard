#!/usr/bin/env python3
"""
NE Dashboard — Local Proxy Server
══════════════════════════════════════════════════════════════════
Serves NE_Dashboard.html at http://localhost:8080 and proxies
API calls to EAP and Tableau server-side so CORS never blocks you.
Credentials stay on your machine — the browser never sees tokens.

Usage:
  python3 proxy_server.py

Then open:  http://localhost:8080/NE_Dashboard.html
══════════════════════════════════════════════════════════════════
"""

import http.server
import urllib.request
import urllib.parse
import urllib.error
import json
import os
import sys
import threading
import time

PORT      = 8080
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
CFG_FILE  = os.path.join(BASE_DIR, 'dashboard_config.json')

# ── Load config ──────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CFG_FILE):
        with open(CFG_FILE) as f:
            return json.load(f)
    print(f"⚠️  Config not found: {CFG_FILE}")
    print("   Copy dashboard_config.template.json → dashboard_config.json and fill in your credentials.")
    return {}

cfg = load_config()

# ── Tableau sign-in (PAT → session token) ───────────────────────────────────
_tableau_token   = None
_tableau_site_id = None
_signin_lock     = threading.Lock()

def tableau_sign_in(force=False):
    global _tableau_token, _tableau_site_id
    with _signin_lock:
        if _tableau_token and not force:
            return _tableau_token

        tc = cfg.get('tableau', {})
        if not tc.get('server_url') or not tc.get('pat_name') or not tc.get('pat_secret'):
            print("⚠️  Tableau not configured — fill in dashboard_config.json")
            return None

        api_version = tc.get('api_version', '3.21')
        url = f"{tc['server_url'].rstrip('/')}/api/{api_version}/auth/signin"
        payload = json.dumps({
            "credentials": {
                "personalAccessTokenName":   tc['pat_name'],
                "personalAccessTokenSecret": tc['pat_secret'],
                "site": {"contentUrl": tc.get('site_name', '')}
            }
        }).encode()

        req = urllib.request.Request(url, data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Accept', 'application/json')

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                _tableau_token   = data['credentials']['token']
                _tableau_site_id = data['credentials']['site']['id']
                print(f"✅ Tableau signed in  site_id={_tableau_site_id}")
                return _tableau_token
        except urllib.error.HTTPError as e:
            print(f"❌ Tableau sign-in HTTP {e.code}: {e.read().decode()[:200]}")
        except Exception as e:
            print(f"❌ Tableau sign-in error: {e}")
        return None


# ── HTTP handler ─────────────────────────────────────────────────────────────
class DashboardHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    # Quiet successful GETs to keep the terminal readable
    def log_message(self, fmt, *args):
        if len(args) >= 2 and args[1] == '200':
            return
        super().log_message(fmt, *args)

    # ── helpers ──────────────────────────────────────────────────────────────
    def cors_headers(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def proxy_upstream(self, url, method='GET', body=None, extra_headers=None):
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header('Accept', 'application/json')
        for k, v in (extra_headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                self.send_response(resp.status)
                ct = resp.headers.get('Content-Type', 'application/json')
                self.send_header('Content-Type', ct)
                self.cors_headers()
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            body_err = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.cors_headers()
            self.end_headers()
            self.wfile.write(body_err)
        except Exception as e:
            self.send_json({'error': str(e)}, 502)

    # ── CORS preflight ────────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self.cors_headers()
        self.end_headers()

    # ── GET routes ────────────────────────────────────────────────────────────
    def do_GET(self):
        path = self.path.split('?')[0]

        # ── /proxy/config  (safe status — no secrets) ────────────────────────
        if path == '/proxy/config':
            tc = cfg.get('tableau', {})
            eap = cfg.get('eap', {})
            self.send_json({
                'eap_configured':     bool(eap.get('token') and not eap['token'].startswith('PASTE')),
                'tableau_configured': bool(tc.get('pat_secret') and not tc['pat_secret'].startswith('PASTE')),
                'tableau_site_id':    _tableau_site_id or '',
                'tableau_server':     tc.get('server_url', ''),
                'tableau_api_version':tc.get('api_version', '3.21'),
            })

        # ── /proxy/eap/*  →  eap.equinix.com ────────────────────────────────
        elif path.startswith('/proxy/eap/'):
            eap  = cfg.get('eap', {})
            tail = self.path[len('/proxy/eap'):]          # keep query string
            url  = eap.get('base_url', 'https://eap.equinix.com/api/v1') + tail
            self.proxy_upstream(url, extra_headers={
                'Authorization': f"Bearer {eap.get('token', '')}"
            })

        # ── /proxy/tableau/*  →  Tableau Server ─────────────────────────────
        elif path.startswith('/proxy/tableau/'):
            global _tableau_token
            if not _tableau_token:
                _tableau_token = tableau_sign_in()
            tc   = cfg.get('tableau', {})
            tail = self.path[len('/proxy/tableau'):]       # keep query string
            api  = tc.get('api_version', '3.21')
            url  = f"{tc.get('server_url','').rstrip('/')}/api/{api}{tail}"
            self.proxy_upstream(url, extra_headers={
                'X-Tableau-Auth': _tableau_token or ''
            })

        # ── static files (NE_Dashboard.html, etc.) ──────────────────────────
        else:
            super().do_GET()

    # ── POST routes ───────────────────────────────────────────────────────────
    def do_POST(self):
        path = self.path.split('?')[0]

        # Re-authenticate Tableau (called by dashboard on 401)
        if path == '/proxy/tableau/signin':
            token = tableau_sign_in(force=True)
            if token:
                self.send_json({'token': token, 'site_id': _tableau_site_id})
            else:
                self.send_json({'error': 'Sign-in failed — check dashboard_config.json'}, 401)

        # Proxy POST to Tableau (e.g. create session, query)
        elif path.startswith('/proxy/tableau/'):
            global _tableau_token
            if not _tableau_token:
                _tableau_token = tableau_sign_in()
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length) if length else None
            tc     = cfg.get('tableau', {})
            tail   = self.path[len('/proxy/tableau'):]
            api    = tc.get('api_version', '3.21')
            url    = f"{tc.get('server_url','').rstrip('/')}/api/{api}{tail}"
            self.proxy_upstream(url, method='POST', body=body, extra_headers={
                'X-Tableau-Auth': _tableau_token or '',
                'Content-Type':   self.headers.get('Content-Type', 'application/json'),
            })

        else:
            self.send_json({'error': 'Not found'}, 404)


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Pre-authenticate Tableau in the background if configured
    tc = cfg.get('tableau', {})
    if tc.get('pat_secret') and not tc['pat_secret'].startswith('PASTE'):
        threading.Thread(target=tableau_sign_in, daemon=True).start()

    try:
        with http.server.HTTPServer(('localhost', PORT), DashboardHandler) as httpd:
            print(f"""
╔══════════════════════════════════════════════════════╗
║   NE Dashboard — Proxy Server                        ║
╠══════════════════════════════════════════════════════╣
║  Dashboard → http://localhost:{PORT}/NE_Dashboard.html  ║
║  EAP proxy → /proxy/eap/...                          ║
║  Tableau   → /proxy/tableau/...                      ║
║  Config    → dashboard_config.json                   ║
╠══════════════════════════════════════════════════════╣
║  Press Ctrl+C to stop                                ║
╚══════════════════════════════════════════════════════╝
""")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋  Server stopped.")
    except OSError as e:
        if 'Address already in use' in str(e):
            print(f"❌  Port {PORT} is in use. Stop the other process or change PORT in proxy_server.py")
        else:
            raise
