#!/usr/bin/env python3
import http.server, os, webbrowser, json, urllib.request, urllib.error, sys, subprocess

os.chdir(os.path.dirname(os.path.abspath(__file__)))

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, f, *a):
        print(self.requestline)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, x-api-key, anthropic-version')
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/krone-hent':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                url = data.get('url', '')
                if 'kronekapital.dk' not in url:
                    raise ValueError('Ugyldig URL')
                import urllib.request
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'text/html,application/xhtml+xml',
                    'Cookie': ''  # Session cookie fra browser kan ikke overføres
                })
                # Returner instruktion om at bruge Claude i Chrome i stedet
                result = json.dumps({
                    'error': 'Brug knappen i Claude i Chrome til at hente data direkte fra Krone Connect mens du er logget ind',
                    'hint': 'Åbn sagen på Krone Connect i Chrome, og bed Claude om at hente data'
                })
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(result.encode())
            except Exception as e:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        elif self.path == '/api/krone-billeder':
            # Modtager billeder fra Krone Connect (base64) og gemmer lokalt
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                import base64, os
                data = json.loads(body)
                aftalenr = data.get('aftalenr', 'ukendt')
                billeder = data.get('billeder', [])
                km = data.get('km', '')
                # Opret mappe
                folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'filer', aftalenr)
                os.makedirs(folder, exist_ok=True)
                saved = []
                for b in billeder:
                    fname = b.get('filename', 'billede.jpg')
                    dataUrl = b.get('dataUrl', '')
                    if ',' in dataUrl:
                        imgData = base64.b64decode(dataUrl.split(',')[1])
                        fpath = os.path.join(folder, fname)
                        with open(fpath, 'wb') as f:
                            f.write(imgData)
                        saved.append(fname)
                result = json.dumps({'ok': True, 'saved': saved, 'folder': folder, 'km': km})
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(result.encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        elif self.path == '/api/krone-data':
            # Modtager data hentet af Claude i Chrome og gemmer til aktiv sag
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True, 'data': data}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        elif self.path == '/api/claude':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            print('POST /api/claude body length:', len(body))
            try:
                data = json.loads(body)
                api_key = data.pop('_api_key', '')
                print('API key starts with:', api_key[:15] if api_key else 'EMPTY')
                req = urllib.request.Request(
                    'https://api.anthropic.com/v1/messages',
                    data=json.dumps(data).encode(),
                    headers={
                        'Content-Type': 'application/json',
                        'x-api-key': api_key,
                        'anthropic-version': '2023-06-01'
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req) as r:
                    result = r.read()
                print('API success, response length:', len(result))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(result)
            except urllib.error.HTTPError as e:
                err = e.read()
                print('API HTTP error:', e.code, err[:200])
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(err)
            except Exception as e:
                print('Error:', str(e))
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

server = http.server.HTTPServer(('localhost', 8765), Handler)
print('Simple Leasing Sagsark korer paa http://localhost:8765')
sys.stdout.flush()

# Abn i Google Chrome
url = 'http://localhost:8765'
chrome_paths = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
]
opened = False
for cp in chrome_paths:
    if os.path.exists(cp):
        subprocess.Popen([cp, url])
        opened = True
        break
if not opened:
    webbrowser.open(url)

server.serve_forever()
