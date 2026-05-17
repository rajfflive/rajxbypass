from flask import Flask, request, jsonify, render_template_string, session, redirect
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import threading
import time
import re
import os
import secrets
from datetime import datetime, timedelta

# ==================== ENVIRONMENT VARIABLES ====================
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_USERNAME = '@link_bypass_kd_bot'
ADMIN_SECRET = os.environ.get('ADMIN_SECRET', 'mysecret123')
SESSION_STRING = os.environ.get('SESSION_STRING', '')
PORT = int(os.environ.get('PORT', 10000))

if not API_ID or not API_HASH:
    raise ValueError("API_ID and API_HASH must be set")
if not SESSION_STRING:
    raise ValueError("SESSION_STRING environment variable not set")

# ==================== FLASK APP ====================
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ==================== TELEGRAM CLIENT ====================
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, loop=loop)

# ==================== DATA STORAGE ====================
user_credits = {}
pending_requests = {}

# ==================== HELPERS ====================
def get_user(api_key):
    if api_key not in user_credits:
        user_credits[api_key] = {
            'credits': 0,
            'total_used': 0,
            'total_bypassed': 0,
            'created_at': datetime.now().isoformat(),
            'last_used': None,
            'expiry': None
        }
    return user_credits[api_key]

def is_expired(api_key):
    expiry_str = get_user(api_key).get('expiry')
    if not expiry_str:
        return False
    try:
        expiry_date = datetime.fromisoformat(expiry_str)
        return datetime.now() > expiry_date
    except:
        return False

def deduct_credit(api_key):
    if is_expired(api_key):
        return False, "API key expired"
    u = get_user(api_key)
    if u['credits'] >= 1:
        u['credits'] -= 1
        u['total_used'] += 1
        u['last_used'] = datetime.now().isoformat()
        return True, None
    return False, "Insufficient credits"

def add_credits(api_key, amount, expiry_days=None):
    u = get_user(api_key)
    u['credits'] += amount
    if expiry_days is not None and expiry_days > 0:
        expiry_date = datetime.now() + timedelta(days=expiry_days)
        u['expiry'] = expiry_date.isoformat()
    return u['credits']

def generate_api_key():
    return "key_" + secrets.token_hex(12)

def extract_links_from_response(msg):
    src = re.search(r'Source:\s*(https?://[^\s]+)', msg, re.I)
    dst = re.search(r'Destination:\s*(https?://[^\s]+)', msg, re.I)
    return (src.group(1) if src else None, dst.group(1) if dst else None)

# ==================== TELEGRAM HANDLER ====================
@client.on(events.NewMessage(chats=BOT_USERNAME))
async def handler(event):
    text = event.message.text
    if 'Destination' not in text:
        return
    orig, bypass = extract_links_from_response(text)
    if not bypass:
        return
    for rid, req in list(pending_requests.items()):
        if req['original_link'] in text or (orig and orig == req['original_link']):
            pending_requests[rid]['result'] = {
                'original_link': orig or req['original_link'],
                'bypassed_link': bypass
            }
            pending_requests[rid]['complete'] = True
            break

def run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)

# ==================== FLASK ROUTES ====================
@app.route('/')
def index():
    return render_template_string(HTML_UI)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'bot': BOT_USERNAME, 'developer': '@rajfflive', 'time': datetime.now().isoformat()})

@app.route('/bypass', methods=['GET', 'POST'])
def bypass():
    if request.method == 'GET':
        link = request.args.get('link')
        api_key = request.args.get('api_key')
    else:
        data = request.json or {}
        link = data.get('link')
        api_key = data.get('api_key')
    
    if not api_key:
        return jsonify({'status': False, 'error': 'Missing api_key', 'developer': '@rajfflive'})
    if not link:
        return jsonify({'status': False, 'error': 'Missing link', 'developer': '@rajfflive'})
    if not link.startswith(('http://', 'https://')):
        link = 'https://' + link
    
    ok, err = deduct_credit(api_key)
    if not ok:
        u = get_user(api_key)
        return jsonify({'status': False, 'error': err, 'credits_remaining': u['credits'], 'expired': is_expired(api_key), 'developer': '@rajfflive'})
    
    req_id = str(int(time.time() * 1000))
    pending_requests[req_id] = {
        'original_link': link,
        'complete': False,
        'result': None,
        'timestamp': time.time()
    }
    try:
        run_async(client.send_message(BOT_USERNAME, link))
        start_time = time.time()
        while time.time() - start_time < 25:
            time.sleep(0.5)
            if pending_requests.get(req_id, {}).get('complete'):
                res = pending_requests[req_id]['result']
                del pending_requests[req_id]
                u = get_user(api_key)
                u['total_bypassed'] += 1
                return jsonify({
                    'status': True,
                    'original_link': res['original_link'],
                    'bypassed_link': res['bypassed_link'],
                    'credits_remaining': u['credits'],
                    'expiry': u['expiry'],
                    'developer': '@rajfflive'
                })
        # timeout - refund
        u = get_user(api_key)
        u['credits'] += 1
        u['total_used'] -= 1
        if req_id in pending_requests:
            del pending_requests[req_id]
        return jsonify({'status': False, 'error': 'Bot timeout - no response in 25 seconds', 'developer': '@rajfflive'})
    except Exception as e:
        u = get_user(api_key)
        u['credits'] += 1
        u['total_used'] -= 1
        if req_id in pending_requests:
            del pending_requests[req_id]
        return jsonify({'status': False, 'error': str(e), 'developer': '@rajfflive'})

@app.route('/credits')
def credits():
    api_key = request.args.get('api_key')
    if not api_key:
        return jsonify({'status': False, 'error': 'Missing api_key', 'developer': '@rajfflive'})
    u = get_user(api_key)
    return jsonify({
        'status': True,
        'credits_remaining': u['credits'],
        'total_used': u['total_used'],
        'total_bypassed': u['total_bypassed'],
        'expiry': u['expiry'],
        'expired': is_expired(api_key),
        'developer': '@rajfflive'
    })

# ==================== ADMIN PANEL (with copy button) ====================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        secret = request.form.get('secret')
        if secret == ADMIN_SECRET:
            session['admin_logged_in'] = True
            return redirect('/admin')
        else:
            return render_template_string(ADMIN_LOGIN, error="Wrong secret")
    if not session.get('admin_logged_in'):
        return render_template_string(ADMIN_LOGIN, error=None)
    return render_template_string(ADMIN_DASHBOARD, keys=user_credits)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin')

@app.route('/admin/generate', methods=['POST'])
def admin_generate():
    if not session.get('admin_logged_in'):
        return jsonify({'status': False, 'error': 'Not logged in'})
    key_type = request.form.get('key_type', 'auto')
    if key_type == 'auto':
        api_key = generate_api_key()
    else:
        api_key = request.form.get('custom_key', '').strip()
        if not api_key:
            return jsonify({'status': False, 'error': 'Custom key empty'})
        if api_key in user_credits:
            return jsonify({'status': False, 'error': 'Key already exists'})
    credits = int(request.form.get('credits', 0))
    expiry_days = request.form.get('expiry_days')
    expiry = int(expiry_days) if expiry_days and expiry_days.isdigit() else None
    add_credits(api_key, credits, expiry)
    return jsonify({'status': True, 'api_key': api_key, 'credits': credits, 'expiry_days': expiry})

@app.route('/admin/add_credits', methods=['POST'])
def admin_add_credits():
    if not session.get('admin_logged_in'):
        return jsonify({'status': False, 'error': 'Not logged in'})
    api_key = request.form.get('api_key')
    amount = int(request.form.get('amount', 0))
    if not api_key or amount <= 0:
        return jsonify({'status': False, 'error': 'Invalid'})
    if api_key not in user_credits:
        return jsonify({'status': False, 'error': 'API key not found'})
    new_bal = add_credits(api_key, amount)
    return jsonify({'status': True, 'new_balance': new_bal})

@app.route('/admin/delete_key', methods=['POST'])
def admin_delete_key():
    if not session.get('admin_logged_in'):
        return jsonify({'status': False, 'error': 'Not logged in'})
    api_key = request.form.get('api_key')
    if api_key in user_credits:
        del user_credits[api_key]
        return jsonify({'status': True})
    return jsonify({'status': False, 'error': 'Key not found'})

# ==================== HTML TEMPLATES (with copy) ====================
HTML_UI = '''<!DOCTYPE html>
<html><head><title>Link Bypass API</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#0a0f1e;color:#fff;font-family:Arial;text-align:center;padding:20px}.card{background:#1e2a3a;margin:20px auto;padding:20px;border-radius:15px;max-width:600px}input,button{padding:10px;margin:5px;border-radius:8px;border:none}input{width:70%;background:#2d3e4e;color:#fff}button{background:#00b4ff;cursor:pointer}.result{background:#0a0f1e;padding:10px;border-radius:8px;margin-top:10px;word-break:break-all}.credit{color:#00ff88;font-size:1.5em}.footer{font-size:12px;margin-top:20px;color:#888}</style></head>
<body><div class="card"><h1>🔗 Link Bypass API</h1><p>Bot: @link_bypass_kd_bot | <a href="/admin">Admin</a></p><div class="credit" id="creditDisplay">Credits: --</div><hr><h3>Your API Key</h3><input type="text" id="apiKey" readonly><br><button onclick="generateKey()">Generate New Key</button><button onclick="checkCredits()">Check Credits</button><hr><h3>Bypass Link</h3><input type="text" id="linkInput" placeholder="Enter link (e.g., https://shrinkme.click/abc)"><button onclick="bypass()">Bypass Now</button><div id="result" class="result"></div></div><div class="footer">Developer: @rajfflive | API v2.0</div><script>let apiKey=localStorage.getItem('api_key');if(!apiKey)generateKey();else document.getElementById('apiKey').value=apiKey;function generateKey(){apiKey='user_'+Math.random().toString(36).substr(2,16);localStorage.setItem('api_key',apiKey);document.getElementById('apiKey').value=apiKey;checkCredits()}async function checkCredits(){let res=await fetch(`/credits?api_key=${apiKey}`);let data=await res.json();if(data.status)document.getElementById('creditDisplay').innerHTML=`Credits: ${data.credits_remaining}<br>Expires: ${data.expiry||'Never'}`;else document.getElementById('creditDisplay').innerText='Credits: Error'}async function bypass(){let link=document.getElementById('linkInput').value;let resultDiv=document.getElementById('result');if(!link){resultDiv.innerHTML='❌ Enter link';return}resultDiv.innerHTML='⏳ Processing...';try{let res=await fetch('/bypass',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({link:link,api_key:apiKey})});let data=await res.json();if(data.status){resultDiv.innerHTML=`✅ Bypassed: <a href="${data.bypassed_link}" target="_blank">${data.bypassed_link}</a><br>💎 Credits left: ${data.credits_remaining}`;}else{resultDiv.innerHTML=`❌ ${data.error}`;}checkCredits();}catch(e){resultDiv.innerHTML='❌ Error: '+e.message}}checkCredits();</script></body></html>'''

ADMIN_LOGIN = '''<!DOCTYPE html>
<html><head><title>Admin Login</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#0a0f1e;color:#fff;font-family:Arial;text-align:center;padding:50px}.card{background:#1e2a3a;margin:auto;padding:30px;border-radius:15px;max-width:400px}input,button{padding:10px;margin:10px;border-radius:8px;border:none}button{background:#00b4ff;cursor:pointer}.footer{font-size:12px;margin-top:20px;color:#888}</style></head>
<body><div class="card"><h2>Admin Login</h2>{% if error %}<p style="color:red">{{ error }}</p>{% endif %}<form method="post"><input type="password" name="secret" placeholder="Admin Secret" required><br><button type="submit">Login</button></form><div class="footer">Developer: @rajfflive</div></div></body></html>'''

ADMIN_DASHBOARD = '''<!DOCTYPE html>
<html><head><title>Admin Dashboard</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#0a0f1e;color:#fff;font-family:Arial;padding:20px}.card{background:#1e2a3a;margin:15px auto;padding:20px;border-radius:15px;max-width:1000px}.key-list{background:#0a0f1e;padding:10px;border-radius:10px;margin-top:10px;overflow-x:auto}table{width:100%;border-collapse:collapse}th,td{padding:8px;text-align:left;border-bottom:1px solid #2d3e4e}input,button{padding:8px;margin:5px;border-radius:8px;border:none}button{background:#00b4ff;cursor:pointer}.delete{background:#ff4444}.copy-btn{background:#555;padding:2px 8px;margin:0;font-size:12px}.footer{font-size:12px;margin-top:20px;text-align:center;color:#888}</style></head>
<body><div class="card"><h2>🔐 Admin Dashboard</h2><a href="/admin/logout">Logout</a><hr><h3>Generate New API Key</h3><form id="genForm"><input type="number" name="credits" placeholder="Credits" required><input type="number" name="expiry_days" placeholder="Expiry days (optional)"><select name="key_type"><option value="auto">Auto generate</option><option value="custom">Custom key</option></select><input type="text" name="custom_key" placeholder="Custom key (if selected)"><button type="submit">Generate Key</button></form><pre id="genResult"></pre><hr><h3>Add Credits to Existing Key</h3><form id="addForm"><input type="text" name="api_key" placeholder="API Key" required><input type="number" name="amount" placeholder="Amount" required><button type="submit">Add Credits</button></form><pre id="addResult"></pre><hr><h3>All API Keys <button onclick="refreshPage()" style="background:#555">🔄 Refresh</button></h3><div class="key-list"><table><tr><th>API Key</th><th>Credits</th><th>Used</th><th>Bypassed</th><th>Expiry</th><th>Action</th></tr>{% for key, data in keys.items() %}不错<tr><td><span id="key-{{ loop.index }}">{{ key }}</span> <button class="copy-btn" onclick="copyKey('{{ key }}', {{ loop.index }})">📋 Copy</button></td><td>{{ data.credits }}</td><td>{{ data.total_used }}</td><td>{{ data.total_bypassed }}</td><td>{{ data.expiry or 'Never' }}</td><td><button onclick="deleteKey('{{ key }}')" class="delete">Delete</button></td></tr>{% endfor %}</table></div><div class="footer">Developer: @rajfflive | All rights reserved</div></div><script>function copyKey(key, idx){navigator.clipboard.writeText(key);alert('Copied: '+key);}function refreshPage(){location.reload();}document.getElementById('genForm').onsubmit=async(e)=>{e.preventDefault();let fd=new FormData(e.target);let res=await fetch('/admin/generate',{method:'POST',body:fd});let data=await res.json();if(data.status){document.getElementById('genResult').innerHTML=`✅ Generated: ${data.api_key}<br>Credits: ${data.credits}<br>Expiry days: ${data.expiry_days||'None'}<br><button onclick="navigator.clipboard.writeText('${data.api_key}')">📋 Copy Key</button>`;setTimeout(()=>location.reload(),2000);}else{document.getElementById('genResult').innerHTML=`❌ ${data.error}`;}};document.getElementById('addForm').onsubmit=async(e)=>{e.preventDefault();let fd=new FormData(e.target);let res=await fetch('/admin/add_credits',{method:'POST',body:fd});let data=await res.json();if(data.status){document.getElementById('addResult').innerHTML=`✅ Added! New balance: ${data.new_balance}`;setTimeout(()=>location.reload(),1500);}else{document.getElementById('addResult').innerHTML=`❌ ${data.error}`;}};async function deleteKey(key){if(confirm('Delete this key?')){let fd=new FormData();fd.append('api_key',key);let res=await fetch('/admin/delete_key',{method:'POST',body:fd});if(res.ok)location.reload();}}</script></body></html>'''

# ==================== START TELEGRAM IN BACKGROUND ====================
def start_telegram():
    async def main():
        await client.connect()
        if not await client.is_user_authorized():
            print("ERROR: Invalid session string. Please regenerate.")
            return
        print("✅ Telegram client connected")
        await client.send_message(BOT_USERNAME, '/start')
        print("📤 Sent /start to bot")
        await client.run_until_disconnected()
    loop.run_until_complete(main())

def run_flask():
    print(f"🚀 Starting Flask on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    start_telegram()
