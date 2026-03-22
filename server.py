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
                    'Cookie': ''  # Session cookie fra browser kan ikke overfÃ¸res
                })
                # Returner instruktion om at bruge Claude i Chrome i stedet
                result = json.dumps({
                    'error': 'Brug knappen i Claude i Chrome til at hente data direkte fra Krone Connect mens du er logget ind',
                    'hint': 'Ãbn sagen pÃ¥ Krone Connect i Chrome, og bed Claude om at hente data'
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

        elif self.path == '/api/makeapp':
            try:
                import os, subprocess, shutil
                base = os.path.dirname(os.path.abspath(__file__))
                app = os.path.join(base, 'SL Sagsark.app')
                macos = os.path.join(app, 'Contents', 'MacOS')
                res   = os.path.join(app, 'Contents', 'Resources')
                subprocess.run(['rm','-rf',app])
                os.makedirs(macos, exist_ok=True)
                os.makedirs(res,   exist_ok=True)
                exe = os.path.join(macos, 'SL Sagsark')
                with open(exe,'w') as f:
                    f.write('#!/bin/bash\nD=\"'+base+'\"\npkill -f \'python3 server.py\' 2>/dev/null\nsleep 1\ncd \"$D\" && python3 server.py >/tmp/sl.log 2>&1 &\nfor i in $(seq 10); do sleep 1; curl -s http://localhost:8765 >/dev/null && break; done\npgrep -f \"chrome.*localhost:8765\" >/dev/null && osascript -e \'tell app \"Google Chrome\" to activate\' || open -a \"Google Chrome\" --args --app=http://localhost:8765 --no-first-run\n')
                os.chmod(exe, 0o755)
                with open(os.path.join(app,'Contents','Info.plist'),'w') as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict>\n<key>CFBundleExecutable</key><string>SL Sagsark</string>\n<key>CFBundleIdentifier</key><string>dk.simpleleasing.sagsark</string>\n<key>CFBundleName</key><string>SL Sagsark</string>\n<key>CFBundleDisplayName</key><string>SL Sagsark</string>\n<key>CFBundlePackageType</key><string>APPL</string>\n<key>CFBundleIconFile</key><string>AppIcon</string>\n<key>CFBundleVersion</key><string>1.0</string>\n<key>NSHighResolutionCapable</key><true/>\n</dict></plist>')
                try:
                    from PIL import Image, ImageDraw, ImageFont
                    def mk(s):
                        i=Image.new('RGBA',(s,s),(0,0,0,0)); d=ImageDraw.Draw(i)
                        d.rounded_rectangle([0,0,s-1,s-1],radius=int(s*.22),fill=(26,26,46,255))
                        p=int(s*.055); d.rounded_rectangle([p,p,s-p-1,s-p-1],radius=int(s*.17),fill=(22,33,62,255))
                        fs=int(s*.44); font=None
                        for fp in ['/System/Library/Fonts/Supplemental/Georgia Bold.ttf','/System/Library/Fonts/Helvetica.ttc']:
                            try: font=ImageFont.truetype(fp,fs); break
                            except: pass
                        font=font or ImageFont.load_default()
                        bb=d.textbbox((0,0),'SL',font=font)
                        d.text(((s-(bb[2]-bb[0]))//2-bb[0],int(s*.1)-bb[1]),'SL',fill=(255,255,255,255),font=font)
                        ly=int(s*.73); lh=max(2,int(s*.014)); lp=int(s*.16)
                        d.rounded_rectangle([lp,ly,s-lp,ly+lh],radius=lh//2,fill=(79,195,247,185))
                        return i
                    mk(1024).save('/tmp/sl1024.png')
                    IS='/tmp/SLIs.iconset'; subprocess.run(['mkdir','-p',IS])
                    for sz in [16,32,64,128,256,512,1024]:
                        subprocess.run(['sips','-z',str(sz),str(sz),'/tmp/sl1024.png','--out',f'{IS}/icon_{sz}x{sz}.png'],capture_output=True)
                    for a,b in [('32','16@2x'),('64','32@2x'),('256','128@2x'),('512','256@2x'),('512','512@2x')]:
                        try: shutil.copy(f'{IS}/icon_{a}x{a}.png',f'{IS}/icon_{b}.png')
                        except: pass
                    subprocess.run(['iconutil','-c','icns',IS,'-o',os.path.join(res,'AppIcon.icns')],capture_output=True)
                    subprocess.run(['rm','-rf',IS])
                except: pass
                subprocess.run(['xattr','-cr',app],capture_output=True)
                subprocess.run(['killall','Dock'],capture_output=True)
                send_json({'ok':True,'msg':'App lavet i '+base})
            except Exception as e:
                send_json({'error':str(e)},500)

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
