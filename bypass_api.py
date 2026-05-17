from flask import Flask, request, jsonify, render_template_string, session, redirect
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import threading
import time
import re
import os
import secrets
from datetime import datetime, timedelta

# ---------- ENV ----------
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_USERNAME = '@link_bypass_kd_bot'
ADMIN_SECRET = os.environ.get('ADMIN_SECRET', 'mysecret123')
SESSION_STRING = os.environ.get('SESSION_STRING', '')
PORT = int(os.environ.get('PORT', 10000))

if not API_ID or not API_HASH or not SESSION_STRING:
    raise ValueError("Missing env variables")

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, loop=loop)

user_credits = {}
pending = {}

def get_user(api_key):
    if api_key not in user_credits:
        user_credits[api_key] = {
            'credits': 0, 'used': 0, 'bypassed': 0,
            'created': datetime.now().isoformat(),
            'expiry': None
        }
    return user_credits[api_key]

def is_expired(key):
    exp = get_user(key).get('expiry')
    return exp and datetime.now() > datetime.fromisoformat(exp)

def deduct_credit(key):
    if is_expired(key): return False, "Expired"
    u = get_user(key)
    if u['credits'] >= 1:
        u['credits'] -= 1
        u['used'] += 1
        return True, None
    return False, "Insufficient credits"

def add_credits(key, amt, days=None):
    u = get_user(key)
    u['credits'] += amt
    if days:
        u['expiry'] = (datetime.now() + timedelta(days=days)).isoformat()
    return u['credits']

def gen_key(): return "key_" + secrets.token_hex(12)

def extract(msg):
    src = re.search(r'Source:\s*(https?://[^\s]+)', msg, re.I)
    dst = re.search(r'Destination:\s*(https?://[^\s]+)', msg, re.I)
    return (src.group(1) if src else None, dst.group(1) if dst else None)

# ---------- ROUTES ----------
@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'dev': '@rajfflive'})

@app.route('/bypass', methods=['POST'])
def bypass():
    data = request.json or {}
    link = data.get('link')
    key = data.get('api_key')
    if not key or not link:
        return jsonify({'status': False, 'error': 'Missing api_key or link'})
    if not link.startswith(('http://','https://')):
        link = 'https://' + link
    ok, err = deduct_credit(key)
    if not ok:
        return jsonify({'status': False, 'error': err, 'credits': get_user(key)['credits']})
    async def poll():
        await client.send_message(BOT_USERNAME, link)
        for _ in range(20):
            await asyncio.sleep(1)
            msgs = await client.get_messages(BOT_USERNAME, limit=3)
            for m in msgs:
                if m.text and 'Destination' in m.text:
                    orig, dest = extract(m.text)
                    if dest:
                        return {'orig': orig or link, 'dest': dest}
        return None
    try:
        res = asyncio.run_coroutine_threadsafe(poll(), loop).result(25)
        if res:
            u = get_user(key)
            u['bypassed'] += 1
            return jsonify({'status': True, 'original': res['orig'], 'bypassed': res['dest'], 'credits_remaining': u['credits']})
        else:
            u = get_user(key); u['credits'] += 1; u['used'] -= 1
            return jsonify({'status': False, 'error': 'Bot timeout'})
    except Exception as e:
        u = get_user(key); u['credits'] += 1; u['used'] -= 1
        return jsonify({'status': False, 'error': str(e)})

@app.route('/credits')
def credits():
    key = request.args.get('api_key')
    if not key: return jsonify({'status': False, 'error': 'Missing key'})
    u = get_user(key)
    return jsonify({'status': True, 'credits': u['credits'], 'used': u['used'], 'bypassed': u['bypassed'], 'expiry': u['expiry']})

# ---------- ADMIN ----------
@app.route('/admin', methods=['GET','POST'])
def admin():
    if request.method == 'POST' and request.form.get('secret') == ADMIN_SECRET:
        session['admin'] = True
        return redirect('/admin')
    if session.get('admin'):
        return render_template_string(ADMIN_HTML, keys=user_credits, secrets=secrets)
    return render_template_string(LOGIN_HTML, error=None)

@app.route('/admin/logout')
def logout():
    session.pop('admin', None)
    return redirect('/admin')

@app.route('/admin/gen', methods=['POST'])
def gen():
    if not session.get('admin'): return jsonify({'status': False})
    key_type = request.form.get('key_type', 'auto')
    if key_type == 'auto':
        api_key = gen_key()
    else:
        api_key = request.form.get('custom_key', '').strip()
        if not api_key or api_key in user_credits:
            return jsonify({'status': False, 'error': 'Invalid or duplicate'})
    credits = int(request.form.get('credits', 0))
    days = request.form.get('expiry_days')
    days = int(days) if days and days.isdigit() else None
    add_credits(api_key, credits, days)
    return jsonify({'status': True, 'api_key': api_key, 'credits': credits, 'expiry': days})

@app.route('/admin/add', methods=['POST'])
def add():
    if not session.get('admin'): return jsonify({'status': False})
    key = request.form.get('api_key')
    amt = int(request.form.get('amount', 0))
    if not key or amt <= 0 or key not in user_credits:
        return jsonify({'status': False})
    bal = add_credits(key, amt)
    return jsonify({'status': True, 'balance': bal})

@app.route('/admin/del', methods=['POST'])
def delete():
    if not session.get('admin'): return jsonify({'status': False})
    key = request.form.get('api_key')
    if key in user_credits:
        del user_credits[key]
        return jsonify({'status': True})
    return jsonify({'status': False})

# ---------- HTML TEMPLATES (Modern UI) ----------
HOME_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KD Bypass API</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', system-ui, sans-serif; }
        body { background: linear-gradient(135deg, #0a0f1e 0%, #0a192f 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .glass-card { background: rgba(15, 25, 45, 0.7); backdrop-filter: blur(12px); border-radius: 32px; padding: 32px; width: 100%; max-width: 500px; border: 1px solid rgba(0, 255, 136, 0.2); box-shadow: 0 25px 45px rgba(0,0,0,0.3); }
        h1 { font-size: 1.8rem; background: linear-gradient(135deg, #00ff88, #00b4ff); -webkit-background-clip: text; background-clip: text; color: transparent; margin-bottom: 8px; }
        .badge { background: #00ff8810; border: 1px solid #00ff88; border-radius: 40px; padding: 6px 14px; font-size: 0.8rem; color: #00ff88; display: inline-block; margin: 15px 0; }
        .credit-box { background: #0a0f1e; border-radius: 20px; padding: 16px; margin: 20px 0; text-align: center; border: 1px solid #2a3a5a; }
        .credit-number { font-size: 2rem; font-weight: bold; color: #00ff88; }
        input, button { width: 100%; padding: 14px; margin: 8px 0; border-radius: 16px; border: none; font-size: 1rem; }
        input { background: #0a0f1e; border: 1px solid #2a3a5a; color: white; outline: none; transition: 0.2s; }
        input:focus { border-color: #00ff88; box-shadow: 0 0 12px #00ff8830; }
        button { background: linear-gradient(135deg, #00ff88, #00b4ff); color: #0a0f1e; font-weight: bold; cursor: pointer; transition: transform 0.1s; }
        button:active { transform: scale(0.98); }
        .result { background: #0a0f1e; border-radius: 16px; padding: 12px; margin-top: 16px; font-size: 0.9rem; word-break: break-all; border-left: 3px solid #00ff88; }
        .link { color: #00b4ff; text-decoration: none; }
        .footer { margin-top: 24px; font-size: 0.75rem; text-align: center; color: #5a6e8a; }
        a { color: #00b4ff; text-decoration: none; }
        button.secondary { background: #2a3a5a; color: white; }
    </style>
</head>
<body>
<div class="glass-card">
    <h1>🔗 KD Bypass API</h1>
    <div class="badge">⚡ by @rajfflive</div>
    <div class="credit-box">
        <div style="font-size:0.8rem;">YOUR CREDITS</div>
        <div class="credit-number" id="creditCount">—</div>
        <div id="expiryText" style="font-size:0.7rem;"></div>
    </div>
    <input type="text" id="apiKeyInput" placeholder="Your API Key" value="">
    <button onclick="generateKey()">✨ Generate New Key</button>
    <button class="secondary" onclick="checkCredits()">⟳ Check Credits</button>
    <hr style="margin: 20px 0; border-color:#2a3a5a;">
    <input type="text" id="linkInput" placeholder="Paste link to bypass...">
    <button onclick="bypass()">🚀 Bypass Now</button>
    <div id="result" class="result" style="display:none;"></div>
    <div class="footer"><a href="/admin">Admin Panel</a> • @rajfflive</div>
</div>
<script>
    let apiKey = localStorage.getItem('api_key') || '';
    document.getElementById('apiKeyInput').value = apiKey;
    if(apiKey) checkCredits();

    async function generateKey() {
        let newKey = 'user_' + Math.random().toString(36).substr(2, 12);
        localStorage.setItem('api_key', newKey);
        document.getElementById('apiKeyInput').value = newKey;
        await checkCredits();
    }
    async function checkCredits() {
        let key = document.getElementById('apiKeyInput').value;
        if(!key) return;
        let res = await fetch(`/credits?api_key=${key}`);
        let data = await res.json();
        if(data.status) {
            document.getElementById('creditCount').innerText = data.credits;
            document.getElementById('expiryText').innerText = data.expiry ? `Expires: ${new Date(data.expiry).toLocaleDateString()}` : 'No expiry';
        } else {
            document.getElementById('creditCount').innerText = 'Error';
        }
    }
    async function bypass() {
        let key = document.getElementById('apiKeyInput').value;
        let link = document.getElementById('linkInput').value;
        let resultDiv = document.getElementById('result');
        if(!key || !link) { resultDiv.style.display='block'; resultDiv.innerHTML='❌ API key and link required'; return; }
        resultDiv.style.display='block'; resultDiv.innerHTML='⏳ Processing...';
        try {
            let res = await fetch('/bypass', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({link:link, api_key:key}) });
            let data = await res.json();
            if(data.status) {
                resultDiv.innerHTML = `✅ <strong>Bypassed Link:</strong><br><a href="${data.bypassed}" target="_blank" class="link">${data.bypassed}</a><br>💎 Credits left: ${data.credits_remaining}`;
            } else {
                resultDiv.innerHTML = `❌ ${data.error}`;
            }
            await checkCredits();
        } catch(e) { resultDiv.innerHTML = '❌ Network error'; }
    }
    document.getElementById('apiKeyInput').addEventListener('change', () => { localStorage.setItem('api_key', document.getElementById('apiKeyInput').value); checkCredits(); });
</script>
</body>
</html>
'''

LOGIN_HTML = '''
<!DOCTYPE html>
<html><head><title>Admin Login</title><style>body{background:#0a0f1e;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:sans-serif;} .login-card{background:#112235;padding:40px;border-radius:32px;width:320px;text-align:center;border:1px solid #00ff8844;} input,button{width:100%;padding:12px;margin:8px 0;border-radius:24px;border:none;} button{background:#00ff88;font-weight:bold;}</style></head>
<body><div class="login-card"><h2>🔐 Admin Access</h2>{% if error %}<p style="color:red">{{ error }}</p>{% endif %}<form method="post"><input name="secret" type="password" placeholder="Admin Secret"><button>Login</button></form></div></body></html>
'''

ADMIN_HTML = '''
<!DOCTYPE html>
<html><head><title>Admin Dashboard</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#0a0f1e;color:#fff;font-family:'Segoe UI',sans-serif;padding:20px}.dashboard{max-width:1400px;margin:auto}.card{background:#112235;border-radius:24px;padding:24px;margin-bottom:24px;border:1px solid #2a3a5a}.row{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:20px}.col{flex:1;min-width:280px}input,select,button{padding:10px;border-radius:12px;border:none;margin:5px 0}button{background:#00ff88;font-weight:bold;cursor:pointer}.btn-danger{background:#ff4466}.table-container{overflow-x:auto}table{width:100%;border-collapse:collapse}th,td{padding:12px;text-align:left;border-bottom:1px solid #2a3a5a}.copy-btn{background:#2a3a5a;padding:4px 12px;border-radius:20px;font-size:12px;margin-left:8px}.badge{background:#00ff8822;color:#00ff88;padding:4px 12px;border-radius:40px;font-size:12px}</style></head>
<body><div class="dashboard"><div style="display:flex;justify-content:space-between;align-items:center"><h1>🔐 Admin Panel</h1><a href="/admin/logout" style="color:#ff8866">Logout</a></div>
<div class="card"><h3>➕ Generate API Key</h3><form id="genForm" class="row"><div class="col"><input type="number" name="credits" placeholder="Credits" required></div><div class="col"><input type="number" name="expiry_days" placeholder="Expiry days"></div><div class="col"><select name="key_type"><option value="auto">Auto generate</option><option value="custom">Custom key</option></select></div><div class="col"><input type="text" name="custom_key" placeholder="Custom key"></div><div class="col"><button type="submit">Generate</button></div></form><pre id="genResult"></pre></div>
<div class="card"><h3>💰 Add Credits</h3><form id="addForm" class="row"><div class="col"><input type="text" name="api_key" placeholder="API Key" required></div><div class="col"><input type="number" name="amount" placeholder="Amount" required></div><div class="col"><button type="submit">Add Credits</button></div></form><pre id="addResult"></pre></div>
<div class="card"><h3>📋 All API Keys <span style="font-size:12px">({{ keys|length }} total)</span> <button onclick="refresh()" style="background:#2a3a5a">⟳ Refresh</button></h3><div class="table-container"><table><tr><th>API Key</th><th>Credits</th><th>Used</th><th>Bypassed</th><th>Expiry</th><th>Action</th></tr>{% for k, d in keys.items() %}<tr><td><span id="key-{{ loop.index }}">{{ k }}</span><button class="copy-btn" onclick="copyKey('{{ k }}', {{ loop.index }})">📋 Copy</button></td><td>{{ d.credits }}</td><td>{{ d.used }}</td><td>{{ d.bypassed }}</td><td>{{ d.expiry[:10] if d.expiry else 'Never' }}</td><td><button onclick="delKey('{{ k }}')" style="background:#ff4466">Delete</button></td></tr>{% endfor %}</table></div></div></div>
<script>
function copyKey(key, idx){ navigator.clipboard.writeText(key); alert('Copied: '+key); }
function refresh(){ location.reload(); }
async function delKey(key){ if(confirm('Delete key?')){ let fd=new FormData(); fd.append('api_key',key); let res=await fetch('/admin/del',{method:'POST',body:fd}); if(res.ok) location.reload(); } }
document.getElementById('genForm').onsubmit=async(e)=>{ e.preventDefault(); let fd=new FormData(e.target); let res=await fetch('/admin/gen',{method:'POST',body:fd}); let d=await res.json(); if(d.status) document.getElementById('genResult').innerHTML=`✅ Generated: ${d.api_key}<br>Credits: ${d.credits}<br>Expiry: ${d.expiry||'None'}<br><button onclick="navigator.clipboard.writeText('${d.api_key}')">📋 Copy Key</button>`; else document.getElementById('genResult').innerHTML=`❌ ${d.error}`; setTimeout(()=>refresh(),1500); };
document.getElementById('addForm').onsubmit=async(e)=>{ e.preventDefault(); let fd=new FormData(e.target); let res=await fetch('/admin/add',{method:'POST',body:fd}); let d=await res.json(); if(d.status) document.getElementById('addResult').innerHTML=`✅ Added! New balance: ${d.balance}`; else document.getElementById('addResult').innerHTML=`❌ Error`; setTimeout(()=>refresh(),1000); };
</script></body></html>
'''

# ---------- START ----------
def start_telegram():
    async def main():
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Invalid session string")
        else:
            print("✅ Telegram connected")
            await client.send_message(BOT_USERNAME, '/start')
            await client.run_until_disconnected()
    loop.run_until_complete(main())

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    start_telegram()
