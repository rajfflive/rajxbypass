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

# ========== ENV ==========
API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_USERNAME = '@link_bypass_kd_bot'
ADMIN_SECRET = os.environ.get('ADMIN_SECRET', 'mysecret123')
SESSION_STRING = os.environ.get('SESSION_STRING', '')
PORT = int(os.environ.get('PORT', 10000))

if not API_ID or not API_HASH or not SESSION_STRING:
    raise ValueError("Missing API_ID, API_HASH or SESSION_STRING")

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, loop=loop)

user_credits = {}
recent_requests = {}  # key: "api_key|link" -> timestamp

# ---------- Helper Functions ----------
def get_user(api_key):
    if api_key not in user_credits:
        user_credits[api_key] = {
            'credits': 0,
            'used': 0,
            'bypassed': 0,
            'expiry': None,
            'created': datetime.now().isoformat()
        }
    return user_credits[api_key]

def is_expired(api_key):
    exp = get_user(api_key).get('expiry')
    return exp and datetime.now() > datetime.fromisoformat(exp)

def deduct_credit(api_key):
    if is_expired(api_key):
        return False, "Key expired"
    u = get_user(api_key)
    if u['credits'] >= 1:
        u['credits'] -= 1
        u['used'] += 1
        return True, None
    return False, f"Insufficient credits ({u['credits']} left)"

def add_credits(api_key, amount, expiry_days=None):
    u = get_user(api_key)
    u['credits'] += amount
    if expiry_days:
        u['expiry'] = (datetime.now() + timedelta(days=expiry_days)).isoformat()
    return u['credits']

def generate_api_key():
    return "key_" + secrets.token_hex(12)

# ---------- Link Extraction ----------
def extract_links_from_message(msg):
    src_match = re.search(r'Source\s*:\s*(https?://[^\s\n]+)', msg, re.IGNORECASE)
    dst_match = re.search(r'Destination\s*:\s*(https?://[^\s\n]+)', msg, re.IGNORECASE)
    src = src_match.group(1) if src_match else None
    dst = dst_match.group(1) if dst_match else None
    if not dst:
        urls = re.findall(r'https?://[^\s\n]+', msg)
        if urls:
            dst = urls[-1]
    return src, dst

# ---------- Flask Routes ----------
@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'developer': '@rajfflive'})

@app.route('/bypass', methods=['POST'])  # Only POST, no GET
def bypass():
    data = request.json or {}
    link = data.get('link')
    api_key = data.get('api_key')
    
    if not api_key or not link:
        return jsonify({'status': False, 'error': 'Missing api_key or link', 'developer': '@rajfflive'})
    if not link.startswith(('http://', 'https://')):
        link = 'https://' + link
    
    # ----- DUPLICATE CHECK (within 2 seconds) -----
    req_key = f"{api_key}|{link}"
    now = time.time()
    if req_key in recent_requests and now - recent_requests[req_key] < 2:
        return jsonify({'status': False, 'error': 'Duplicate request ignored. Please wait.', 'developer': '@rajfflive'})
    recent_requests[req_key] = now
    # Clean old entries occasionally
    if len(recent_requests) > 100:
        recent_requests.clear()
    
    # Deduct credit
    ok, err = deduct_credit(api_key)
    if not ok:
        return jsonify({'status': False, 'error': err, 'credits': get_user(api_key)['credits'], 'developer': '@rajfflive'})
    
    # Async polling
    async def send_and_poll():
        await client.send_message(BOT_USERNAME, link)
        for _ in range(20):
            await asyncio.sleep(1)
            msgs = await client.get_messages(BOT_USERNAME, limit=5)
            for msg in msgs:
                if msg.text and ('Destination' in msg.text or 'destination' in msg.text.lower()):
                    src, dst = extract_links_from_message(msg.text)
                    if dst:
                        return {'src': src or link, 'dst': dst}
            # Fallback: look for t.me link
            for msg in msgs:
                if msg.text and 't.me' in msg.text:
                    urls = re.findall(r'https?://[^\s\n]+', msg.text)
                    if urls:
                        return {'src': link, 'dst': urls[-1]}
        return None
    
    try:
        result = asyncio.run_coroutine_threadsafe(send_and_poll(), loop).result(timeout=25)
        if result:
            u = get_user(api_key)
            u['bypassed'] += 1
            return jsonify({
                'status': True,
                'original_link': result['src'],
                'bypassed_link': result['dst'],
                'credits_remaining': u['credits'],
                'developer': '@rajfflive'
            })
        else:
            # refund credit on timeout
            u = get_user(api_key)
            u['credits'] += 1
            u['used'] -= 1
            return jsonify({'status': False, 'error': 'Bot did not respond in time', 'developer': '@rajfflive'})
    except Exception as e:
        # refund credit on error
        u = get_user(api_key)
        u['credits'] += 1
        u['used'] -= 1
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
        'total_used': u['used'],
        'total_bypassed': u['bypassed'],
        'expiry': u['expiry'],
        'developer': '@rajfflive'
    })

# ---------- Admin Panel (with @rajfflive) ----------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST' and request.form.get('secret') == ADMIN_SECRET:
        session['admin_logged_in'] = True
        return redirect('/admin')
    if session.get('admin_logged_in'):
        return render_template_string(ADMIN_HTML, keys=user_credits)
    return render_template_string(LOGIN_HTML)

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
        if not api_key or api_key in user_credits:
            return jsonify({'status': False, 'error': 'Invalid or duplicate'})
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
    if not api_key or amount <= 0 or api_key not in user_credits:
        return jsonify({'status': False, 'error': 'Invalid'})
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

# ---------- HTML Templates (button disable + developer credit) ----------
HOME_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KD Bypass API</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,sans-serif}
        body{background:linear-gradient(135deg,#0a0f1e 0%,#0a192f 100%);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}
        .glass{background:rgba(15,25,45,0.7);backdrop-filter:blur(12px);border-radius:32px;padding:32px;max-width:500px;width:100%;border:1px solid rgba(0,255,136,0.2)}
        h1{font-size:1.8rem;background:linear-gradient(135deg,#00ff88,#00b4ff);-webkit-background-clip:text;background-clip:text;color:transparent}
        .badge{background:#00ff8810;border:1px solid #00ff88;border-radius:40px;padding:6px 14px;font-size:0.8rem;color:#00ff88;display:inline-block;margin:15px 0}
        .credit-box{background:#0a0f1e;border-radius:20px;padding:16px;margin:20px 0;text-align:center;border:1px solid #2a3a5a}
        .credit-number{font-size:2rem;font-weight:bold;color:#00ff88}
        input,button{width:100%;padding:14px;margin:8px 0;border-radius:16px;border:none;font-size:1rem}
        input{background:#0a0f1e;border:1px solid #2a3a5a;color:white;outline:none}
        input:focus{border-color:#00ff88}
        button{background:linear-gradient(135deg,#00ff88,#00b4ff);color:#0a0f1e;font-weight:bold;cursor:pointer;transition:0.1s}
        button:active{transform:scale(0.98)}
        button:disabled{opacity:0.6;cursor:not-allowed}
        .result{background:#0a0f1e;border-radius:16px;padding:12px;margin-top:16px;word-break:break-all;border-left:3px solid #00ff88}
        .footer{margin-top:24px;font-size:0.75rem;text-align:center;color:#5a6e8a}
        a{color:#00b4ff;text-decoration:none}
    </style>
</head>
<body>
<div class="glass">
    <h1>🔗 KD Bypass API</h1>
    <div class="badge">⚡ by @rajfflive</div>
    <div class="credit-box">
        <div>YOUR CREDITS</div>
        <div class="credit-number" id="creditCount">—</div>
        <div id="expiryText"></div>
    </div>
    <input type="text" id="apiKeyInput" placeholder="Your API Key">
    <button onclick="generateKey()">✨ Generate New Key</button>
    <button onclick="checkCredits()" style="background:#2a3a5a;color:white">⟳ Check Credits</button>
    <hr style="margin:20px 0;border-color:#2a3a5a">
    <input type="text" id="linkInput" placeholder="Paste link to bypass...">
    <button id="bypassBtn" onclick="bypass()">🚀 Bypass Now</button>
    <div id="result" class="result" style="display:none;"></div>
    <div class="footer">👑 Developer: @rajfflive | <a href="https://t.me/rajfflive" target="_blank">💬 Support</a> | <a href="/admin">Admin</a></div>
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
            document.getElementById('creditCount').innerText = data.credits_remaining;
            document.getElementById('expiryText').innerText = data.expiry ? `Expires: ${new Date(data.expiry).toLocaleDateString()}` : '';
        } else {
            document.getElementById('creditCount').innerText = 'Error';
        }
    }
    async function bypass() {
        let key = document.getElementById('apiKeyInput').value;
        let link = document.getElementById('linkInput').value;
        let resultDiv = document.getElementById('result');
        let btn = document.getElementById('bypassBtn');
        if(!key || !link) {
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '❌ API key and link required';
            return;
        }
        // Disable button to prevent double-click
        btn.disabled = true;
        btn.innerText = '⏳ Processing...';
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '⏳ Processing...';
        try {
            let res = await fetch('/bypass', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({link: link, api_key: key})
            });
            let data = await res.json();
            if(data.status) {
                resultDiv.innerHTML = `✅ <strong>Bypassed:</strong><br><a href="${data.bypassed_link}" target="_blank" class="link">${data.bypassed_link}</a><br>💎 Credits left: ${data.credits_remaining}`;
            } else {
                resultDiv.innerHTML = `❌ ${data.error}`;
            }
            await checkCredits();
        } catch(e) {
            resultDiv.innerHTML = '❌ Network error';
        } finally {
            btn.disabled = false;
            btn.innerText = '🚀 Bypass Now';
        }
    }
    document.getElementById('apiKeyInput').addEventListener('change', () => {
        localStorage.setItem('api_key', document.getElementById('apiKeyInput').value);
        checkCredits();
    });
</script>
</body>
</html>
'''

LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Admin Login</title><style>
body{background:#0a0f1e;display:flex;justify-content:center;align-items:center;min-height:100vh}
.login-card{background:#112235;padding:40px;border-radius:32px;width:320px;text-align:center;border:1px solid #00ff8844}
input,button{width:100%;padding:12px;margin:8px 0;border-radius:24px;border:none}
button{background:#00ff88;font-weight:bold;cursor:pointer}
.footer{margin-top:20px;font-size:12px;color:#5a6e8a}
a{color:#00b4ff}
</style></head>
<body>
<div class="login-card"><h2>🔐 Admin Access</h2>
<form method="post"><input name="secret" type="password" placeholder="Admin Secret"><button>Login</button></form>
<div class="footer">Developer: @rajfflive | <a href="https://t.me/rajfflive">Support</a></div>
</div></body></html>
'''

ADMIN_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Admin Dashboard</title><meta name="viewport" content="width=device-width">
<style>
body{background:#0a0f1e;color:#fff;font-family:'Segoe UI',system-ui;padding:20px}
.card{background:#112235;border-radius:24px;padding:24px;margin-bottom:24px}
.row{display:flex;gap:15px;flex-wrap:wrap}
input,select,button{padding:10px;border-radius:12px;border:none}
input,select{background:#0a0f1e;color:#fff;border:1px solid #2a3a5a}
button{background:#00ff88;font-weight:bold;cursor:pointer}
table{width:100%;border-collapse:collapse}
th,td{padding:12px;text-align:left;border-bottom:1px solid #2a3a5a}
.copy-btn{background:#2a3a5a;padding:4px 12px;border-radius:20px;margin-left:8px}
.footer{margin-top:30px;text-align:center;font-size:12px;color:#5a6e8a}
a{color:#00b4ff}
</style></head>
<body>
<div style="max-width:1400px;margin:auto">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">
        <h1>🔐 Admin Panel <span style="background:#00ff8822;color:#00ff88;padding:2px 10px;border-radius:20px;font-size:12px">@rajfflive</span></h1>
        <a href="/admin/logout" style="color:#ff8866">🚪 Logout</a>
    </div>
    <div class="card">
        <h3>➕ Generate API Key</h3>
        <form id="genForm" class="row">
            <input type="number" name="credits" placeholder="Credits" required>
            <input type="number" name="expiry_days" placeholder="Expiry days">
            <select name="key_type"><option value="auto">Auto</option><option value="custom">Custom</option></select>
            <input type="text" name="custom_key" placeholder="Custom key">
            <button type="submit">Generate</button>
        </form>
        <pre id="genResult"></pre>
    </div>
    <div class="card">
        <h3>💰 Add Credits</h3>
        <form id="addForm" class="row">
            <input type="text" name="api_key" placeholder="API Key" required>
            <input type="number" name="amount" placeholder="Amount" required>
            <button type="submit">Add Credits</button>
        </form>
        <pre id="addResult"></pre>
    </div>
    <div class="card">
        <h3>📋 All Keys <button onclick="location.reload()" style="background:#2a3a5a;padding:4px 12px">⟳ Refresh</button></h3>
        <div style="overflow-x:auto"><tr><th>Key</th><th>Credits</th><th>Used</th><th>Bypassed</th><th>Expiry</th><th>Action</th></tr>
            {% for k,d in keys.items() %}
            <tr>
                <td><span id="key-{{ loop.index }}">{{ k }}</span><button class="copy-btn" onclick="copyKey('{{ k }}',{{ loop.index }})">📋 Copy</button></td>
                <td>{{ d.credits }}</td><td>{{ d.used }}</td><td>{{ d.bypassed }}</td>
                <td>{{ d.expiry[:10] if d.expiry else 'Never' }}</td>
                <td><button onclick="deleteKey('{{ k }}')" style="background:#ff4466">Delete</button></td>
            </tr>
            {% endfor %}
        </div>
    </div>
    <div class="footer">👑 Developer: @rajfflive | <a href="https://t.me/rajfflive">💬 Support</a> | <a href="/">🏠 Home</a></div>
</div>
<script>
function copyKey(key,idx){ navigator.clipboard.writeText(key); alert('Copied: '+key); }
async function deleteKey(key){ if(confirm('Delete?')){ let fd=new FormData(); fd.append('api_key',key); let r=await fetch('/admin/delete_key',{method:'POST',body:fd}); if(r.ok) location.reload(); else alert('Failed'); } }
document.getElementById('genForm').onsubmit=async(e)=>{ e.preventDefault(); let fd=new FormData(e.target); let r=await fetch('/admin/generate',{method:'POST',body:fd}); let d=await r.json(); if(d.status){ document.getElementById('genResult').innerHTML=`✅ Generated: ${d.api_key}<br>Credits: ${d.credits}<br>Expiry: ${d.expiry_days||'None'}<br><button onclick="navigator.clipboard.writeText('${d.api_key}')">📋 Copy Key</button>`; setTimeout(()=>location.reload(),1500); } else document.getElementById('genResult').innerHTML=`❌ ${d.error}`; };
document.getElementById('addForm').onsubmit=async(e)=>{ e.preventDefault(); let fd=new FormData(e.target); let r=await fetch('/admin/add_credits',{method:'POST',body:fd}); let d=await r.json(); if(d.status){ document.getElementById('addResult').innerHTML=`✅ Added! New balance: ${d.new_balance}`; setTimeout(()=>location.reload(),1000); } else document.getElementById('addResult').innerHTML=`❌ ${d.error}`; };
</script>
</body></html>
'''

# ---------- Start ----------
def start_telegram():
    async def main():
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Invalid session string")
        else:
            print("✅ Telegram client connected")
            await client.send_message(BOT_USERNAME, '/start')
            await client.run_until_disconnected()
    loop.run_until_complete(main())

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    start_telegram()
