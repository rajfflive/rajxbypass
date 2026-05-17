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

API_ID = int(os.environ.get('API_ID', 0))
API_HASH = os.environ.get('API_HASH', '')
BOT_USERNAME = '@link_bypass_kd_bot'
ADMIN_SECRET = os.environ.get('ADMIN_SECRET', 'mysecret123')
SESSION_STRING = os.environ.get('SESSION_STRING', '')
PORT = int(os.environ.get('PORT', 10000))

if not API_ID or not API_HASH or not SESSION_STRING:
    raise ValueError("Missing env")

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, loop=loop)

user_credits = {}

def get_user(k):
    if k not in user_credits:
        user_credits[k] = {'credits':0, 'used':0, 'bypassed':0, 'expiry':None}
    return user_credits[k]

def is_expired(k):
    e = get_user(k).get('expiry')
    return e and datetime.now() > datetime.fromisoformat(e)

def deduct_credit(k):
    if is_expired(k): return False, "Expired"
    u = get_user(k)
    if u['credits']>=1:
        u['credits']-=1
        u['used']+=1
        return True, None
    return False, "Insufficient credits"

def add_credits(k, amt, days=None):
    u = get_user(k)
    u['credits']+=amt
    if days:
        u['expiry']=(datetime.now()+timedelta(days=days)).isoformat()
    return u['credits']

def gen_key(): return "key_"+secrets.token_hex(12)

def extract(msg):
    src=re.search(r'Source:\s*(https?://[^\s]+)',msg,re.I)
    dst=re.search(r'Destination:\s*(https?://[^\s]+)',msg,re.I)
    return (src.group(1) if src else None, dst.group(1) if dst else None)

# ---------- ROUTES ----------
@app.route('/')
def home(): return render_template_string(HOME_HTML)

@app.route('/health')
def health(): return jsonify({'status':'ok','dev':'@rajfflive'})

@app.route('/bypass', methods=['GET', 'POST'])   # <-- FIXED: both GET and POST allowed
def bypass():
    if request.method == 'GET':
        link = request.args.get('link')
        api_key = request.args.get('api_key')
    else:
        data = request.json or {}
        link = data.get('link')
        api_key = data.get('api_key')
    
    if not api_key or not link:
        return jsonify({'status':False, 'error':'Missing api_key or link'})
    if not link.startswith(('http://','https://')):
        link = 'https://' + link
    
    ok, err = deduct_credit(api_key)
    if not ok:
        return jsonify({'status':False, 'error':err, 'credits':get_user(api_key)['credits']})
    
    async def poll():
        await client.send_message(BOT_USERNAME, link)
        for _ in range(20):
            await asyncio.sleep(1)
            msgs = await client.get_messages(BOT_USERNAME, limit=3)
            for m in msgs:
                if m.text and 'Destination' in m.text:
                    orig, dest = extract(m.text)
                    if dest:
                        return {'orig':orig or link, 'dest':dest}
        return None
    
    try:
        res = asyncio.run_coroutine_threadsafe(poll(), loop).result(25)
        if res:
            u = get_user(api_key)
            u['bypassed'] += 1
            return jsonify({'status':True, 'original':res['orig'], 'bypassed':res['dest'], 'credits_remaining':u['credits']})
        else:
            u = get_user(api_key); u['credits']+=1; u['used']-=1
            return jsonify({'status':False, 'error':'Bot timeout'})
    except Exception as e:
        u = get_user(api_key); u['credits']+=1; u['used']-=1
        return jsonify({'status':False, 'error':str(e)})

@app.route('/credits')
def credits():
    k = request.args.get('api_key')
    if not k: return jsonify({'status':False, 'error':'Missing key'})
    u = get_user(k)
    return jsonify({'status':True, 'credits':u['credits'], 'used':u['used'], 'bypassed':u['bypassed'], 'expiry':u['expiry']})

# ---------- ADMIN (same as before, but keep for completeness) ----------
@app.route('/admin', methods=['GET','POST'])
def admin():
    if request.method=='POST' and request.form.get('secret')==ADMIN_SECRET:
        session['admin']=True
        return redirect('/admin')
    if session.get('admin'):
        return render_template_string(ADMIN_HTML, keys=user_credits)
    return LOGIN_HTML

@app.route('/admin/logout')
def logout(): session.pop('admin',None); return redirect('/admin')

@app.route('/admin/gen', methods=['POST'])
def gen():
    if not session.get('admin'): return jsonify({'status':False})
    typ = request.form.get('key_type','auto')
    if typ=='auto': k = gen_key()
    else: k = request.form.get('custom_key','').strip()
    if not k or k in user_credits: return jsonify({'status':False})
    cred = int(request.form.get('credits',0))
    days = request.form.get('expiry_days')
    days = int(days) if days and days.isdigit() else None
    add_credits(k, cred, days)
    return jsonify({'status':True, 'api_key':k, 'credits':cred, 'expiry':days})

@app.route('/admin/add', methods=['POST'])
def add():
    if not session.get('admin'): return jsonify({'status':False})
    k = request.form.get('api_key')
    amt = int(request.form.get('amount',0))
    if not k or amt<=0 or k not in user_credits: return jsonify({'status':False})
    bal = add_credits(k, amt)
    return jsonify({'status':True, 'balance':bal})

@app.route('/admin/del', methods=['POST'])
def delete():
    if not session.get('admin'): return jsonify({'status':False})
    k = request.form.get('api_key')
    if k in user_credits: del user_credits[k]; return jsonify({'status':True})
    return jsonify({'status':False})

# ---------- HTML TEMPLATES (same modern UI) ----------
HOME_HTML = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KD Bypass API</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:linear-gradient(135deg,#0a0f1e,#0a192f);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}.glass{background:rgba(15,25,45,0.7);backdrop-filter:blur(12px);border-radius:32px;padding:32px;max-width:500px;width:100%;border:1px solid #00ff8833}h1{font-size:1.8rem;background:linear-gradient(135deg,#00ff88,#00b4ff);-webkit-background-clip:text;background-clip:text;color:transparent}.badge{background:#00ff8810;border:1px solid #00ff88;border-radius:40px;padding:6px 14px;font-size:0.8rem;color:#00ff88;display:inline-block;margin:15px 0}.credit-box{background:#0a0f1e;border-radius:20px;padding:16px;margin:20px 0;text-align:center;border:1px solid #2a3a5a}.credit-number{font-size:2rem;font-weight:bold;color:#00ff88}input,button{width:100%;padding:14px;margin:8px 0;border-radius:16px;border:none;font-size:1rem}input{background:#0a0f1e;border:1px solid #2a3a5a;color:white}input:focus{border-color:#00ff88}button{background:linear-gradient(135deg,#00ff88,#00b4ff);color:#0a0f1e;font-weight:bold;cursor:pointer}.result{background:#0a0f1e;border-radius:16px;padding:12px;margin-top:16px;word-break:break-all;border-left:3px solid #00ff88}.link{color:#00b4ff}.footer{margin-top:24px;font-size:0.75rem;text-align:center;color:#5a6e8a}</style></head>
<body><div class="glass"><h1>🔗 KD Bypass API</h1><div class="badge">⚡ by @rajfflive</div><div class="credit-box"><div>YOUR CREDITS</div><div class="credit-number" id="creditCount">—</div><div id="expiryText"></div></div><input type="text" id="apiKeyInput" placeholder="Your API Key"><button onclick="generateKey()">✨ Generate New Key</button><button onclick="checkCredits()" style="background:#2a3a5a;color:white">⟳ Check Credits</button><hr style="margin:20px 0;border-color:#2a3a5a"><input type="text" id="linkInput" placeholder="Paste link to bypass..."><button onclick="bypass()">🚀 Bypass Now</button><div id="result" class="result" style="display:none"></div><div class="footer"><a href="/admin">Admin Panel</a> • @rajfflive</div></div><script>
let apiKey=localStorage.getItem('api_key')||''; document.getElementById('apiKeyInput').value=apiKey; if(apiKey)checkCredits();
async function generateKey(){ let k='user_'+Math.random().toString(36).substr(2,12); localStorage.setItem('api_key',k); document.getElementById('apiKeyInput').value=k; await checkCredits(); }
async function checkCredits(){ let k=document.getElementById('apiKeyInput').value; if(!k)return; let r=await fetch(`/credits?api_key=${k}`); let d=await r.json(); if(d.status){ document.getElementById('creditCount').innerText=d.credits; document.getElementById('expiryText').innerText=d.expiry?`Expires: ${new Date(d.expiry).toLocaleDateString()}`:''; } else document.getElementById('creditCount').innerText='Error'; }
async function bypass(){ let k=document.getElementById('apiKeyInput').value; let link=document.getElementById('linkInput').value; let resDiv=document.getElementById('result'); if(!k||!link){ resDiv.style.display='block'; resDiv.innerHTML='❌ API key and link required'; return; } resDiv.style.display='block'; resDiv.innerHTML='⏳ Processing...'; try{ let r=await fetch('/bypass',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({link:link,api_key:k})}); let d=await r.json(); if(d.status){ resDiv.innerHTML=`✅ <strong>Bypassed Link:</strong><br><a href="${d.bypassed}" target="_blank" class="link">${d.bypassed}</a><br>💎 Credits left: ${d.credits_remaining}`; }else{ resDiv.innerHTML=`❌ ${d.error}`; } await checkCredits(); }catch(e){ resDiv.innerHTML='❌ Network error'; } }
document.getElementById('apiKeyInput').addEventListener('change',()=>{ localStorage.setItem('api_key',document.getElementById('apiKeyInput').value); checkCredits(); });
</script></body></html>'''

LOGIN_HTML = '''<!DOCTYPE html><html><head><title>Admin Login</title><style>body{background:#0a0f1e;display:flex;justify-content:center;align-items:center;min-height:100vh}.login-card{background:#112235;padding:40px;border-radius:32px;width:320px;text-align:center}button{background:#00ff88;font-weight:bold;padding:12px;border-radius:24px;border:none;width:100%}input{padding:12px;border-radius:24px;border:none;width:100%;margin:8px 0}</style></head><body><div class="login-card"><h2>🔐 Admin Access</h2><form method="post"><input name="secret" type="password" placeholder="Admin Secret"><button>Login</button></form></div></body></html>'''

ADMIN_HTML = '''<!DOCTYPE html><html><head><title>Admin Dashboard</title><meta name="viewport" content="width=device-width"><style>body{background:#0a0f1e;color:#fff;font-family:system-ui;padding:20px}.card{background:#112235;border-radius:24px;padding:24px;margin-bottom:24px}.row{display:flex;gap:15px;flex-wrap:wrap}input,select,button{padding:10px;border-radius:12px;border:none}button{background:#00ff88;font-weight:bold;cursor:pointer}table{width:100%;border-collapse:collapse}th,td{padding:10px;text-align:left;border-bottom:1px solid #2a3a5a}.copy-btn{background:#2a3a5a;padding:2px 8px;border-radius:20px;margin-left:8px}</style></head><body><div><div style="display:flex;justify-content:space-between"><h1>🔐 Admin Panel</h1><a href="/admin/logout" style="color:#ff8866">Logout</a></div><div class="card"><h3>➕ Generate API Key</h3><form id="genForm" class="row"><input type="number" name="credits" placeholder="Credits" required><input type="number" name="expiry_days" placeholder="Expiry days"><select name="key_type"><option value="auto">Auto</option><option value="custom">Custom</option></select><input type="text" name="custom_key" placeholder="Custom key"><button type="submit">Generate</button></form><pre id="genResult"></pre></div><div class="card"><h3>💰 Add Credits</h3><form id="addForm" class="row"><input type="text" name="api_key" placeholder="API Key" required><input type="number" name="amount" placeholder="Amount"><button type="submit">Add Credits</button></form><pre id="addResult"></pre></div><div class="card"><h3>📋 All Keys ({{ keys|length }}) <button onclick="location.reload()" style="background:#2a3a5a">Refresh</button></h3><div style="overflow-x:auto"><tr><th>Key</th><th>Credits</th><th>Used</th><th>Bypassed</th><th>Expiry</th><th>Action</th></tr>{% for k,d in keys.items() %}<tr><td><span id="key-{{ loop.index }}">{{ k }}</span><button class="copy-btn" onclick="copyKey('{{ k }}',{{ loop.index }})">📋 Copy</button></td><td>{{ d.credits }}</td><td>{{ d.used }}</td><td>{{ d.bypassed }}</td><td>{{ d.expiry[:10] if d.expiry else 'Never' }}</td><td><button onclick="delKey('{{ k }}')" style="background:#ff4466">Delete</button></td></tr>{% endfor %}</table></div></div><script>
function copyKey(k,idx){ navigator.clipboard.writeText(k); alert('Copied: '+k); }
async function delKey(k){ if(confirm('Delete?')){ let fd=new FormData(); fd.append('api_key',k); let r=await fetch('/admin/del',{method:'POST',body:fd}); if(r.ok) location.reload(); } }
document.getElementById('genForm').onsubmit=async(e)=>{ e.preventDefault(); let fd=new FormData(e.target); let r=await fetch('/admin/gen',{method:'POST',body:fd}); let d=await r.json(); if(d.status) document.getElementById('genResult').innerHTML=`✅ Generated: ${d.api_key}<br>Credits: ${d.credits}<br>Expiry: ${d.expiry||'None'}<br><button onclick="navigator.clipboard.writeText('${d.api_key}')">📋 Copy Key</button>`; else document.getElementById('genResult').innerHTML=`❌ Error`; setTimeout(()=>location.reload(),1500); };
document.getElementById('addForm').onsubmit=async(e)=>{ e.preventDefault(); let fd=new FormData(e.target); let r=await fetch('/admin/add',{method:'POST',body:fd}); let d=await r.json(); if(d.status) document.getElementById('addResult').innerHTML=`✅ Added! New balance: ${d.balance}`; else document.getElementById('addResult').innerHTML=`❌ Error`; setTimeout(()=>location.reload(),1000); };
</script></body></html>'''

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
