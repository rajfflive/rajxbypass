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

API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_USERNAMES = os.environ.get('BOT_USERNAMES', '@Nick_Bypass_Bot,@link_bypass_kd_bot')
BOT_LIST = [bot.strip() for bot in BOT_USERNAMES.split(',')]
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'rajfflive')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'mysecret123')
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
recent_requests = {}
pending_requests = {}   # store per request with original link

def get_user(k):
    if k not in user_credits:
        user_credits[k] = {'credits': 0, 'used': 0, 'bypassed': 0, 'expiry': None, 'created': datetime.now().isoformat()}
    return user_credits[k]

def is_expired(k):
    exp = get_user(k).get('expiry')
    return exp and datetime.now() > datetime.fromisoformat(exp)

def deduct_credit(k):
    if is_expired(k): return False, "Key expired"
    u = get_user(k)
    if u['credits'] >= 1:
        u['credits'] -= 1
        u['used'] += 1
        return True, None
    return False, f"Insufficient credits ({u['credits']} left)"

def add_credits(k, amt, days=None):
    u = get_user(k)
    u['credits'] += amt
    if days:
        u['expiry'] = (datetime.now() + timedelta(days=days)).isoformat()
    return u['credits']

def generate_api_key():
    return "key_" + secrets.token_hex(12)

def success_rate(used, bypassed):
    return 0.0 if used == 0 else round((bypassed / used) * 100, 2)

def run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=25)

def clean_url(url):
    if not url: return None
    url = re.sub(r'^[`*_]+|[`*_]+$', '', url)
    url = url.replace('*', '').replace('`', '')
    if url and not url.startswith(('http://', 'https://')):
        url = 'https://' + url.lstrip('/')
    url = re.sub(r'[\*_`]+$', '', url)
    return url

def is_valid_destination(url):
    if not url: return False
    if re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|svg)(\?|$)', url, re.I):
        return False
    bad = ['i.ibb.co', 'ibb.co', 'imgur.com', 'imageshack', 'photobucket', 'flickr.com', 'tinypic.com']
    url_lower = url.lower()
    for b in bad:
        if b in url_lower:
            return False
    good = ['t.me', 'telegram.dog', 'mediafire.com', 'devuploads.com', 'modsfire.com',
            'gplinks.co', 'shrinkme.io', 'linkpays.in', 'arolinks.com', 'criticalxr.alwaysdata.net',
            'drive.google.com', 'mega.nz', 'dropbox.com', '1drv.ms', 'gofile.io', 'anonfiles.com',
            'upload.ee', 'send.cm', 'workupload.com', 'pixeldrain.com']
    if any(d in url_lower for d in good):
        return True
    if re.search(r'\.(apk|zip|rar|7z|exe|pdf|txt|mp4|mkv|mp3|docx|xlsx|bin|dmg|iso)$', url_lower):
        return True
    return False

def extract_src_dst(msg_text):
    """Extract source and destination from bot message"""
    src_match = re.search(r'(?:Source|Original Link)\s*:?\s*(https?://[^\s\n]+)', msg_text, re.I)
    dst_match = re.search(r'(?:Destination|Bypassed Link)\s*:?\s*(https?://[^\s\n]+)', msg_text, re.I)
    src = clean_url(src_match.group(1)) if src_match else None
    dst = clean_url(dst_match.group(1)) if dst_match else None
    if not dst:
        urls = re.findall(r'https?://[^\s\n]+', msg_text)
        if urls:
            dst = clean_url(urls[-1])
    return src, dst

# ---------- Flask Routes ----------
@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'developer': '@rajfflive'})

@app.route('/bypass', methods=['GET', 'POST'])
def bypass():
    if request.method == 'GET':
        link = request.args.get('link')
        api_key = request.args.get('api_key')
    else:
        data = request.json or {}
        link = data.get('link')
        api_key = data.get('api_key')
    if not api_key or not link:
        return jsonify({'status': False, 'error': 'Missing api_key or link', 'developer': '@rajfflive'})
    link = clean_url(link.strip())
    if not link.startswith(('http://','https://')):
        link = 'https://' + link

    # Duplicate prevention (5 sec)
    req_key = f"{api_key}|{link}"
    now = time.time()
    if req_key in recent_requests and now - recent_requests[req_key] < 5:
        return jsonify({'status': False, 'error': 'Duplicate. Wait 5s', 'developer': '@rajfflive'})
    recent_requests[req_key] = now
    if len(recent_requests) > 200:
        recent_requests.clear()

    # Deduct credit
    ok, err = deduct_credit(api_key)
    if not ok:
        u = get_user(api_key)
        return jsonify({'status': False, 'error': err, 'credits': u['credits'],
                        'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']),
                        'developer': '@rajfflive'})

    # Create pending request
    req_id = str(int(time.time() * 1000)) + secrets.token_hex(4)
    pending_requests[req_id] = {
        'link': link,
        'complete': False,
        'result': None,
        'created': time.time()
    }

    async def send_and_poll():
        # Send to all bots
        for bot in BOT_LIST:
            sent = await client.send_message(bot, link)
            # Auto-delete our message after 60 seconds
            async def del_own():
                await asyncio.sleep(60)
                try:
                    await sent.delete()
                except:
                    pass
            asyncio.create_task(del_own())
        print(f"[REQUEST] Sent '{link}' to {BOT_LIST}")

        # Poll for 20 seconds
        for _ in range(20):
            await asyncio.sleep(1)
            # Check if request already completed (by event handler fallback)
            if pending_requests.get(req_id, {}).get('complete'):
                return True
            # Poll each bot's recent messages
            for bot in BOT_LIST:
                try:
                    msgs = await client.get_messages(bot, limit=3)
                except:
                    continue
                for msg in msgs:
                    if msg.text:
                        src, dst = extract_src_dst(msg.text)
                        # Match by source
                        if src and src == link:
                            # Auto-delete bot response
                            async def del_resp():
                                await asyncio.sleep(60)
                                try:
                                    await msg.delete()
                                except:
                                    pass
                            asyncio.create_task(del_resp())
                            pending_requests[req_id]['result'] = {'original': src, 'bypassed': dst}
                            pending_requests[req_id]['complete'] = True
                            print(f"[POLL] Matched {req_id} via src match from {bot}")
                            return True
                        # If no source but link appears in message
                        if link in msg.text and dst and dst != link:
                            async def del_resp2():
                                await asyncio.sleep(60)
                                try:
                                    await msg.delete()
                                except:
                                    pass
                            asyncio.create_task(del_resp2())
                            pending_requests[req_id]['result'] = {'original': link, 'bypassed': dst}
                            pending_requests[req_id]['complete'] = True
                            print(f"[POLL] Matched {req_id} via link in message from {bot}")
                            return True
        return False

    try:
        success = run_async(send_and_poll())
        if success:
            result = pending_requests[req_id]['result']
            del pending_requests[req_id]
            u = get_user(api_key)
            u['bypassed'] += 1
            return jsonify({
                'status': True,
                'original_link': result['original'],
                'bypassed_link': result['bypassed'],
                'credits_remaining': u['credits'],
                'total_bypassed': u['bypassed'],
                'success_rate': success_rate(u['used'], u['bypassed']),
                'developer': '@rajfflive'
            })
        else:
            # Refund credit
            u = get_user(api_key)
            u['credits'] += 1
            u['used'] -= 1
            if req_id in pending_requests:
                del pending_requests[req_id]
            return jsonify({'status': False, 'error': 'No response from any bot within 20 seconds',
                            'credits_remaining': u['credits'], 'total_bypassed': u['bypassed'],
                            'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})
    except Exception as e:
        u = get_user(api_key)
        u['credits'] += 1
        u['used'] -= 1
        if req_id in pending_requests:
            del pending_requests[req_id]
        return jsonify({'status': False, 'error': str(e), 'credits_remaining': u['credits'],
                        'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']),
                        'developer': '@rajfflive'})

@app.route('/credits')
def credits():
    api_key = request.args.get('api_key')
    if not api_key:
        return jsonify({'status': False, 'error': 'Missing api_key', 'developer': '@rajfflive'})
    u = get_user(api_key)
    return jsonify({'status': True, 'credits_remaining': u['credits'], 'total_used': u['used'],
                    'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']),
                    'expiry': u['expiry'], 'developer': '@rajfflive'})

# ---------- Admin routes (same as before, no changes) ----------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect('/admin')
        else:
            return render_template_string(LOGIN_HTML, error="Invalid credentials")
    if session.get('admin_logged_in'):
        total_keys = len(user_credits)
        total_bypassed = sum(u['bypassed'] for u in user_credits.values())
        total_used = sum(u['used'] for u in user_credits.values())
        overall_success = success_rate(total_used, total_bypassed)
        return render_template_string(ADMIN_HTML, keys=user_credits, total_keys=total_keys,
                                      total_bypassed=total_bypassed, overall_success=overall_success)
    return render_template_string(LOGIN_HTML, error=None)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin')

@app.route('/admin/generate', methods=['POST'])
def admin_generate():
    if not session.get('admin_logged_in'): return jsonify({'status': False, 'error': 'Not logged in'})
    key_type = request.form.get('key_type', 'auto')
    if key_type == 'auto':
        api_key = generate_api_key()
    else:
        api_key = request.form.get('custom_key', '').strip()
        if not api_key or api_key in user_credits: return jsonify({'status': False, 'error': 'Invalid or duplicate'})
    credits = int(request.form.get('credits', 0))
    expiry_days = request.form.get('expiry_days')
    expiry = int(expiry_days) if expiry_days and expiry_days.isdigit() else None
    add_credits(api_key, credits, expiry)
    return jsonify({'status': True, 'api_key': api_key, 'credits': credits, 'expiry_days': expiry})

@app.route('/admin/add_credits', methods=['POST'])
def admin_add_credits():
    if not session.get('admin_logged_in'): return jsonify({'status': False, 'error': 'Not logged in'})
    api_key = request.form.get('api_key')
    amount = int(request.form.get('amount', 0))
    if not api_key or amount <= 0 or api_key not in user_credits: return jsonify({'status': False, 'error': 'Invalid'})
    new_bal = add_credits(api_key, amount)
    return jsonify({'status': True, 'new_balance': new_bal})

@app.route('/admin/delete_key', methods=['POST'])
def admin_delete_key():
    if not session.get('admin_logged_in'): return jsonify({'status': False, 'error': 'Not logged in'})
    api_key = request.form.get('api_key')
    if api_key in user_credits:
        del user_credits[api_key]
        return jsonify({'status': True})
    return jsonify({'status': False, 'error': 'Key not found'})

# ---------- HTML Templates (same as before) ----------
HOME_HTML = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Raj Bypass API</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{background:url('https://i.ibb.co/n8jX6HmQ/a4671110f8cc.jpg') no-repeat center center fixed;background-size:cover;backdrop-filter:blur(12px);padding:20px;color:#fff;min-height:100vh;display:flex;justify-content:center;align-items:center}
.glass{background:rgba(15,25,45,0.7);backdrop-filter:blur(12px);border-radius:32px;padding:32px;max-width:550px;width:100%;border:1px solid rgba(0,255,136,0.2)}
h1{font-size:1.8rem;background:linear-gradient(135deg,#00ff88,#00b4ff);-webkit-background-clip:text;background-clip:text;color:transparent}
.badge{background:#00ff8810;border:1px solid #00ff88;border-radius:40px;padding:6px 14px;font-size:0.8rem;color:#00ff88;display:inline-block;margin:15px 0}
input,button{width:100%;padding:14px;margin:8px 0;border-radius:16px;border:none;font-size:1rem}
input{background:#0a0f1e;border:1px solid #2a3a5a;color:white}
input:focus{border-color:#00ff88}
button{background:linear-gradient(135deg,#00ff88,#00b4ff);color:#0a0f1e;font-weight:bold;cursor:pointer}
button:disabled{opacity:0.6}
.result{background:#0a0f1e;border-radius:16px;padding:12px;margin-top:16px;word-break:break-all;border-left:3px solid #00ff88}
.footer{margin-top:24px;font-size:0.75rem;text-align:center;color:#ccc}
a{color:#00b4ff;text-decoration:none}
</style></head>
<body><div class="glass"><h1>🔗 Raj Bypass API</h1><div class="badge">⚡ by @rajfflive</div><input type="text" id="apiKeyInput" placeholder="Your API Key (provided by admin)"><hr style="margin:20px 0;border-color:#2a3a5a"><input type="text" id="linkInput" placeholder="Paste link to bypass..."><button id="bypassBtn" onclick="bypass()">🚀 Bypass Now</button><div id="result" class="result" style="display:none"></div><div class="footer">👑 Developer: @rajfflive | <a href="https://t.me/rajfflive" target="_blank">💬 Support</a> | <a href="/admin">Admin</a></div></div><script>
let apiKeyInput = document.getElementById('apiKeyInput');
let resultDiv = document.getElementById('result');
let bypassBtn = document.getElementById('bypassBtn');
async function bypass(){
    let key = apiKeyInput.value.trim();
    let link = document.getElementById('linkInput').value.trim();
    if(!key || !link){
        resultDiv.style.display = 'block';
        resultDiv.innerHTML = '❌ API key and link required';
        return;
    }
    bypassBtn.disabled = true;
    bypassBtn.innerText = '⏳ Processing...';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '⏳ Processing...';
    try{
        let res = await fetch('/bypass', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({link: link, api_key: key})
        });
        let data = await res.json();
        if(data.status){
            resultDiv.innerHTML = `✅ <strong>Bypassed</strong><br><a href="${data.bypassed_link}" target="_blank">${data.bypassed_link}</a><br>💎 Credits left: ${data.credits_remaining}<br>✅ Total bypassed: ${data.total_bypassed}<br>📊 Success rate: ${data.success_rate}%`;
        } else {
            resultDiv.innerHTML = `❌ ${data.error}<br>💎 Credits: ${data.credits_remaining}<br>✅ Total bypassed: ${data.total_bypassed}<br>📊 Success rate: ${data.success_rate}%`;
        }
    } catch(e){
        resultDiv.innerHTML = '❌ Network error';
    } finally {
        bypassBtn.disabled = false;
        bypassBtn.innerText = '🚀 Bypass Now';
    }
}
</script></body></html>'''

LOGIN_HTML = '''<!DOCTYPE html><html><head><title>Admin Login</title><style>body{background:#0a0f1e;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:sans-serif}.login-card{background:rgba(17,34,53,0.95);backdrop-filter:blur(10px);padding:40px;border-radius:32px;width:360px;text-align:center;border:1px solid #00ff8844}input,button{width:100%;padding:12px;margin:8px 0;border-radius:24px;border:none}input{background:#0a0f1e;color:#fff;border:1px solid #2a3a5a}button{background:#00ff88;font-weight:bold;cursor:pointer}.error{color:#ff8866;margin-bottom:10px}.footer{margin-top:20px;font-size:12px;color:#5a6e8a}a{color:#00b4ff}</style></head><body><div class="login-card"><h2>🔐 Admin Access</h2>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Username" required><input type="password" name="password" placeholder="Password" required><button>Login</button></form><div class="footer">Developer: @rajfflive | <a href="https://t.me/rajfflive">Support</a></div></div></body></html>'''

ADMIN_HTML = '''<!DOCTYPE html>
<html><head><title>Admin Dashboard</title><meta name="viewport" content="width=device-width"><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{background:url('https://i.ibb.co/n8jX6HmQ/a4671110f8cc.jpg') no-repeat center center fixed;background-size:cover;backdrop-filter:blur(12px);padding:20px;color:#fff}
.overlay{background:rgba(0,0,0,0.5);border-radius:32px;padding:20px;min-height:100vh}
.dashboard{max-width:1400px;margin:auto}
.stats-grid{display:flex;gap:20px;margin-bottom:20px;flex-wrap:wrap}
.stat-card{background:rgba(20,30,45,0.85);backdrop-filter:blur(10px);padding:20px;border-radius:24px;flex:1;min-width:180px;text-align:center;border:1px solid rgba(255,255,255,0.2);transition:transform 0.2s}
.stat-card:hover{transform:translateY(-5px)}
.stat-number{font-size:2.5rem;font-weight:bold;color:#00ff88}
.card{background:rgba(20,30,45,0.85);backdrop-filter:blur(10px);border-radius:24px;padding:24px;margin-bottom:24px;border:1px solid rgba(255,255,255,0.2)}
.row{display:flex;gap:15px;flex-wrap:wrap;margin-bottom:15px}
input,select,button{padding:12px;border-radius:12px;border:none;font-size:14px}
input,select{background:rgba(0,0,0,0.6);border:1px solid rgba(255,255,255,0.3);color:white}
input::placeholder{color:#aaa}
button{background:linear-gradient(135deg,#00ff88,#00b4ff);color:#0a0f1e;font-weight:bold;cursor:pointer;transition:all 0.2s}
button:hover{transform:scale(1.02);box-shadow:0 0 12px rgba(0,255,136,0.4)}
.danger-btn{background:#ff4466;color:white}
.danger-btn:hover{background:#ff6688}
table{width:100%;border-collapse:collapse}
th,td{padding:12px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.2)}
th{color:#00ff88}
.copy-btn{background:rgba(255,255,255,0.2);padding:4px 12px;border-radius:20px;margin-left:8px;color:white;cursor:pointer;font-size:12px}
.footer{margin-top:30px;text-align:center;font-size:12px;color:#ccc}
a{color:#00b4ff;text-decoration:none}
.badge{background:#00ff8822;color:#00ff88;padding:2px 10px;border-radius:20px;font-size:12px}
</style></head>
<body><div class="overlay"><div class="dashboard"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;margin-bottom:20px"><h1>🔐 Admin Panel <span class="badge">@rajfflive</span></h1><div><a href="/admin/logout" style="color:#ff8866;background:rgba(0,0,0,0.5);padding:8px 16px;border-radius:12px">🚪 Logout</a></div></div><div class="stats-grid"><div class="stat-card"><div class="stat-number">{{ total_keys }}</div><div>Total API Keys</div></div><div class="stat-card"><div class="stat-number">{{ total_bypassed }}</div><div>Total Bypassed</div></div><div class="stat-card"><div class="stat-number">{{ overall_success }}%</div><div>Overall Success Rate</div></div></div><div class="card"><h3>➕ Generate API Key</h3><form id="genForm" class="row"><input type="number" name="credits" placeholder="Credits" required><input type="number" name="expiry_days" placeholder="Expiry days"><select name="key_type"><option value="auto">Auto</option><option value="custom">Custom</option></select><input type="text" name="custom_key" placeholder="Custom key"><button type="submit">Generate Key</button></form><pre id="genResult" style="margin-top:10px;color:#00ff88"></pre></div><div class="card"><h3>💰 Add Credits</h3><form id="addForm" class="row"><input type="text" name="api_key" placeholder="API Key" required><input type="number" name="amount" placeholder="Amount" required><button type="submit">Add Credits</button></form><pre id="addResult" style="margin-top:10px;color:#00ff88"></pre></div><div class="card"><h3>📋 All Keys <button onclick="location.reload()" style="background:rgba(255,255,255,0.2);color:white;padding:8px 16px;margin-left:10px">⟳ Refresh</button></h3><div style="overflow-x:auto;margin-top:15px"><table><th>API Key</th><th>Credits</th><th>Used</th><th>Bypassed</th><th>Success Rate</th><th>Expiry</th><th>Action</th></tr>{% for k,d in keys.items() %}<tr><td><span id="key-{{ loop.index }}">{{ k }}</span><button class="copy-btn" onclick="copyKey('{{ k }}',{{ loop.index }})">📋 Copy</button></div><div class="stat-number">{{ d.credits }}</div><div class="stat-number">{{ d.used }}</div><div class="stat-number">{{ d.bypassed }}</div><div class="stat-number">{{ (d.bypassed / d.used * 100)|round(1) if d.used > 0 else 0 }}%</div><div class="stat-number">{{ d.expiry[:10] if d.expiry else 'Never' }}</div><div class="stat-number"><button onclick="deleteKey('{{ k }}')" class="danger-btn" style="padding:6px 12px">Delete</button></div></tr>{% endfor %}</table></div></div><div class="footer">👑 Developer: @rajfflive | <a href="https://t.me/rajfflive">💬 Support</a> | <a href="/">🏠 Home</a></div></div></div><script>function copyKey(key,idx){ navigator.clipboard.writeText(key); alert('Copied: '+key); }async function deleteKey(key){ if(confirm('Delete this key?')){ let fd=new FormData(); fd.append('api_key',key); let r=await fetch('/admin/delete_key',{method:'POST',body:fd}); if(r.ok) location.reload(); else alert('Failed'); } }document.getElementById('genForm').onsubmit=async(e)=>{ e.preventDefault(); let fd=new FormData(e.target); let r=await fetch('/admin/generate',{method:'POST',body:fd}); let d=await r.json(); if(d.status){ document.getElementById('genResult').innerHTML=`✅ Generated: ${d.api_key}<br>Credits: ${d.credits}<br>Expiry: ${d.expiry_days||'None'}<br><button onclick="navigator.clipboard.writeText('${d.api_key}')">📋 Copy Key</button>`; setTimeout(()=>location.reload(),1500); } else document.getElementById('genResult').innerHTML=`❌ ${d.error}`; };document.getElementById('addForm').onsubmit=async(e)=>{ e.preventDefault(); let fd=new FormData(e.target); let r=await fetch('/admin/add_credits',{method:'POST',body:fd}); let d=await r.json(); if(d.status){ document.getElementById('addResult').innerHTML=`✅ Added! New balance: ${d.new_balance}`; setTimeout(()=>location.reload(),1000); } else document.getElementById('addResult').innerHTML=`❌ ${d.error}`; };</script></body></html>'''

# ---------- Start ----------
def start_telegram():
    async def main():
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Invalid session string")
        else:
            print("✅ Telegram client connected")
            await client.send_message(BOT_LIST[0], '/start')
            await client.run_until_disconnected()
    loop.run_until_complete(main())

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    start_telegram()
