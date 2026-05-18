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
from collections import OrderedDict

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
bypass_cache = OrderedDict()
CACHE_TTL = 86400
MAX_CACHE_SIZE = 2000

def get_cached(link):
    if link in bypass_cache:
        entry = bypass_cache[link]
        if time.time() - entry['ts'] < CACHE_TTL:
            bypass_cache.move_to_end(link)
            return entry['bypassed']
        else:
            del bypass_cache[link]
    return None

def set_cached(link, bypassed):
    # Only cache if bypassed is a valid destination (not fake)
    if is_valid_destination(bypassed):
        bypass_cache[link] = {'bypassed': bypassed, 'ts': time.time()}
        if len(bypass_cache) > MAX_CACHE_SIZE:
            bypass_cache.popitem(last=False)
    else:
        print(f"[CACHE] Not caching invalid destination: {bypassed}")

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
    return future.result(timeout=15)

def clean_url(url):
    if not url: return None
    url = re.sub(r'^[`*_]+|[`*_]+$', '', url)
    url = url.replace('*', '').replace('`', '')
    if url and not url.startswith(('http://', 'https://')):
        url = 'https://' + url.lstrip('/')
    url = re.sub(r'[\*_`]+$', '', url)
    return url

def is_valid_destination(url):
    """Strict validation – only real download or t.me links"""
    if not url:
        return False
    # Reject image extensions
    if re.search(r'\.(jpg|jpeg|png|gif|webp|bmp|svg)(\?|$)', url, re.I):
        return False
    # Reject image hosting domains
    bad_domains = [
        'i.ibb.co', 'ibb.co', 'imgur.com', 'i.imgur.com', 'imageshack',
        'photobucket', 'flickr.com', 'tinypic.com', 'pixhost.to',
        'postimg.cc', 'imagehost', 'cdn.discordapp.com/attachments',
        'ibb.co', 'freeimage.host', 'imagebam.com'
    ]
    url_lower = url.lower()
    for bad in bad_domains:
        if bad in url_lower:
            return False
    # Must be from known good domains or be a t.me link or contain valid file extension
    good_domains = [
        't.me', 'telegram.dog', 'mediafire.com', 'devuploads.com', 'modsfire.com',
        'gplinks.co', 'shrinkme.io', 'linkpays.in', 'arolinks.com', 'criticalxr.alwaysdata.net',
        'drive.google.com', 'mega.nz', 'dropbox.com', '1drv.ms', 'gofile.io',
        'anonfiles.com', 'upload.ee', 'send.cm', 'workupload.com', 'pixeldrain.com'
    ]
    if any(domain in url_lower for domain in good_domains):
        return True
    # Allow any link that ends with a common file extension (likely a real download)
    if re.search(r'\.(apk|zip|rar|7z|exe|pdf|txt|mp4|mkv|mp3|docx|xlsx|bin|dmg|iso|img)$', url_lower):
        return True
    # Otherwise reject (too risky)
    return False

def is_valid_bypass(original, candidate):
    if not candidate or candidate == original:
        return False
    if not candidate.startswith(('http://', 'https://')):
        return False
    if not is_valid_destination(candidate):
        return False
    return True

def extract_links_from_message(msg):
    msg = re.sub(r'\*\*+', '', msg)
    msg = re.sub(r'`', '', msg)
    src_patterns = [
        r'(?:Original Link|Source)\s*:?✅?\s*(https?://[^\s\n]+)',
        r'⛓\s*𝗢ʀɪɢɪɴᴀʟ\s*:?\s*(https?://[^\s\n]+)',
        r'Original\s*:\s*(https?://[^\s\n]+)'
    ]
    dst_patterns = [
        r'(?:Bypassed Link|Destination)\s*:?✅?\s*(https?://[^\s\n]+)',
        r'🎁\s*𝗕ʏᴩᴀꜱꜱᴇᴅ\s*:?\s*(https?://[^\s\n]+)',
        r'Bypassed\s*:\s*(https?://[^\s\n]+)',
        r'Destination\s*:\s*(https?://[^\s\n]+)'
    ]
    src = dst = None
    for pat in src_patterns:
        m = re.search(pat, msg, re.I)
        if m:
            src = clean_url(m.group(1))
            break
    for pat in dst_patterns:
        m = re.search(pat, msg, re.I)
        if m:
            dst = clean_url(m.group(1))
            if dst and is_valid_destination(dst):
                break
            else:
                dst = None
    if not dst:
        urls = re.findall(r'https?://[^\s\n]+', msg)
        for url in reversed(urls):
            cand = clean_url(url)
            if cand and (not src or cand != src) and is_valid_destination(cand):
                dst = cand
                break
    return src, dst

# ---------- Routes ----------
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

    req_key = f"{api_key}|{link}"
    now = time.time()
    if req_key in recent_requests and now - recent_requests[req_key] < 5:
        return jsonify({'status': False, 'error': 'Duplicate. Wait 5s', 'developer': '@rajfflive'})
    recent_requests[req_key] = now
    if len(recent_requests) > 200:
        recent_requests.clear()

    cached = get_cached(link)
    if cached:
        ok, err = deduct_credit(api_key)
        if not ok:
            u = get_user(api_key)
            return jsonify({'status': False, 'error': err, 'credits': u['credits'],
                           'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']),
                           'developer': '@rajfflive'})
        u = get_user(api_key)
        u['bypassed'] += 1
        return jsonify({
            'status': True,
            'original_link': link,
            'bypassed_link': cached,
            'credits_remaining': u['credits'],
            'total_bypassed': u['bypassed'],
            'success_rate': success_rate(u['used'], u['bypassed']),
            'used_bot': 'cache',
            'developer': '@rajfflive',
            'cached': True
        })

    ok, err = deduct_credit(api_key)
    if not ok:
        u = get_user(api_key)
        return jsonify({'status': False, 'error': err, 'credits': u['credits'],
                       'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']),
                       'developer': '@rajfflive'})

    async def try_bot(bot):
        try:
            sent = await client.send_message(bot, link)
            async def del_sent():
                await asyncio.sleep(60)
                try:
                    await sent.delete()
                except:
                    pass
            asyncio.create_task(del_sent())
        except:
            return None

        for _ in range(12):
            await asyncio.sleep(1)
            try:
                msgs = await client.get_messages(bot, limit=3)
            except:
                continue
            for msg in msgs:
                if msg.text:
                    src, dst = extract_links_from_message(msg.text)
                    if dst and is_valid_bypass(link, dst):
                        async def del_resp():
                            await asyncio.sleep(60)
                            try:
                                await msg.delete()
                            except:
                                pass
                        asyncio.create_task(del_resp())
                        return {'src': src or link, 'dst': dst, 'bot': bot}
                    if 't.me' in msg.text:
                        urls = re.findall(r'https?://[^\s\n]+', msg.text)
                        for u in urls:
                            cand = clean_url(u)
                            if cand and 't.me' in cand and cand != link and is_valid_bypass(link, cand):
                                async def del_resp2():
                                    await asyncio.sleep(60)
                                    try:
                                        await msg.delete()
                                    except:
                                        pass
                                asyncio.create_task(del_resp2())
                                return {'src': link, 'dst': cand, 'bot': bot}
        return None

    async def try_all():
        tasks = [asyncio.create_task(try_bot(bot)) for bot in BOT_LIST]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=12)
        for t in pending:
            t.cancel()
        for t in done:
            res = t.result()
            if res:
                return res
        return None

    try:
        result = run_async(try_all())
        if result:
            u = get_user(api_key)
            u['bypassed'] += 1
            # Store in cache only if valid
            if is_valid_destination(result['dst']):
                set_cached(link, result['dst'])
            return jsonify({
                'status': True,
                'original_link': result['src'],
                'bypassed_link': result['dst'],
                'credits_remaining': u['credits'],
                'total_bypassed': u['bypassed'],
                'success_rate': success_rate(u['used'], u['bypassed']),
                'used_bot': result['bot'],
                'developer': '@rajfflive',
                'cached': False
            })
        else:
            u = get_user(api_key)
            u['credits'] += 1
            u['used'] -= 1
            return jsonify({'status': False, 'error': 'No valid bypass found. Try again.',
                           'credits_remaining': u['credits'], 'total_bypassed': u['bypassed'],
                           'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})
    except Exception as e:
        u = get_user(api_key)
        u['credits'] += 1
        u['used'] -= 1
        return jsonify({'status': False, 'error': str(e), 'credits_remaining': u['credits'],
                       'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']),
                       'developer': '@rajfflive'})

@app.route('/credits')
def credits():
    api_key = request.args.get('api_key')
    if not api_key: return jsonify({'status': False, 'error': 'Missing api_key', 'developer': '@rajfflive'})
    u = get_user(api_key)
    return jsonify({'status': True, 'credits_remaining': u['credits'], 'total_used': u['used'],
                   'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']),
                   'expiry': u['expiry'], 'developer': '@rajfflive'})

# ---------- Admin Panel (blur background, white text, styled buttons) ----------
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

@app.route('/admin/clear_cache', methods=['POST'])
def admin_clear_cache():
    if not session.get('admin_logged_in'): return jsonify({'status': False, 'error': 'Not logged in'})
    bypass_cache.clear()
    return jsonify({'status': True, 'message': 'Cache cleared'})

# ---------- HTML Templates (Home + Login + Admin with blurred background) ----------
HOME_HTML = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Raj Bypass API</title><style>*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui}body{background:linear-gradient(135deg,#0a0f1e,#0a192f);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}.glass{background:rgba(15,25,45,0.7);backdrop-filter:blur(12px);border-radius:32px;padding:32px;max-width:550px;width:100%;border:1px solid rgba(0,255,136,0.2)}h1{font-size:1.8rem;background:linear-gradient(135deg,#00ff88,#00b4ff);-webkit-background-clip:text;background-clip:text;color:transparent}.badge{background:#00ff8810;border:1px solid #00ff88;border-radius:40px;padding:6px 14px;font-size:0.8rem;color:#00ff88;display:inline-block;margin:15px 0}.credit-box{background:#0a0f1e;border-radius:20px;padding:16px;margin:20px 0;text-align:center;border:1px solid #2a3a5a}.credit-number{font-size:2rem;font-weight:bold;color:#00ff88}.stats-row{display:flex;justify-content:space-between;margin-top:10px;font-size:0.85rem}input,button{width:100%;padding:14px;margin:8px 0;border-radius:16px;border:none;font-size:1rem}input{background:#0a0f1e;border:1px solid #2a3a5a;color:white}input:focus{border-color:#00ff88}button{background:linear-gradient(135deg,#00ff88,#00b4ff);color:#0a0f1e;font-weight:bold;cursor:pointer}button:disabled{opacity:0.6}.result{background:#0a0f1e;border-radius:16px;padding:12px;margin-top:16px;word-break:break-all;border-left:3px solid #00ff88}.footer{margin-top:24px;font-size:0.75rem;text-align:center;color:#5a6e8a}a{color:#00b4ff}</style></head>
<body><div class="glass"><h1>🔗 Raj Bypass API</h1><div class="badge">⚡ by @rajfflive</div><div class="credit-box"><div>YOUR CREDITS</div><div class="credit-number" id="creditCount">—</div><div id="expiryText"></div><div class="stats-row"><span>✅ Total Bypassed: <span id="totalBypassed">0</span></span><span>📊 Success Rate: <span id="successRate">0</span>%</span></div></div><input type="text" id="apiKeyInput" placeholder="Your API Key"><button onclick="generateKey()">✨ Generate New Key</button><button onclick="checkCredits()" style="background:#2a3a5a;color:white">⟳ Check Credits</button><hr style="margin:20px 0;border-color:#2a3a5a"><input type="text" id="linkInput" placeholder="Paste link to bypass..."><button id="bypassBtn" onclick="bypass()">🚀 Bypass Now</button><div id="result" class="result" style="display:none"></div><div class="footer">👑 Developer: @rajfflive | <a href="https://t.me/rajfflive" target="_blank">💬 Support</a> | <a href="/admin">Admin</a></div></div><script>let apiKey=localStorage.getItem('api_key')||''; document.getElementById('apiKeyInput').value=apiKey; if(apiKey)checkCredits();async function generateKey(){ let k='user_'+Math.random().toString(36).substr(2,12); localStorage.setItem('api_key',k); document.getElementById('apiKeyInput').value=k; await checkCredits(); }async function checkCredits(){ let k=document.getElementById('apiKeyInput').value; if(!k)return; let r=await fetch(`/credits?api_key=${k}`); let d=await r.json(); if(d.status){ document.getElementById('creditCount').innerText=d.credits_remaining; document.getElementById('expiryText').innerText=d.expiry?`Expires: ${new Date(d.expiry).toLocaleDateString()}`:''; document.getElementById('totalBypassed').innerText=d.total_bypassed; document.getElementById('successRate').innerText=d.success_rate; }else document.getElementById('creditCount').innerText='Error'; }async function bypass(){ let k=document.getElementById('apiKeyInput').value; let link=document.getElementById('linkInput').value; let resultDiv=document.getElementById('result'); let btn=document.getElementById('bypassBtn'); if(!k||!link){ resultDiv.style.display='block'; resultDiv.innerHTML='❌ API key and link required'; return; } btn.disabled=true; btn.innerText='⏳ Processing...'; resultDiv.style.display='block'; resultDiv.innerHTML='⏳ Processing...'; try{ let r=await fetch('/bypass',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({link:link,api_key:k})}); let d=await r.json(); if(d.status){ let cacheInfo = d.cached ? ' (from cache)' : ''; resultDiv.innerHTML=`✅ <strong>Bypassed${cacheInfo}</strong><br><a href="${d.bypassed_link}" target="_blank">${d.bypassed_link}</a><br>💎 Credits left: ${d.credits_remaining}<br>✅ Total bypassed: ${d.total_bypassed}<br>📊 Success rate: ${d.success_rate}%`; }else{ resultDiv.innerHTML=`❌ ${d.error}<br>💎 Credits: ${d.credits_remaining}<br>✅ Total bypassed: ${d.total_bypassed}<br>📊 Success rate: ${d.success_rate}%`; } await checkCredits(); }catch(e){ resultDiv.innerHTML='❌ Network error'; }finally{ btn.disabled=false; btn.innerText='🚀 Bypass Now'; } }document.getElementById('apiKeyInput').addEventListener('change',()=>{ localStorage.setItem('api_key',document.getElementById('apiKeyInput').value); checkCredits(); });</script></body></html>'''

LOGIN_HTML = '''<!DOCTYPE html><html><head><title>Admin Login</title><style>body{background:#0a0f1e;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:sans-serif}.login-card{background:rgba(17,34,53,0.95);backdrop-filter:blur(10px);padding:40px;border-radius:32px;width:360px;text-align:center;border:1px solid #00ff8844}input,button{width:100%;padding:12px;margin:8px 0;border-radius:24px;border:none}input{background:#0a0f1e;color:#fff;border:1px solid #2a3a5a}button{background:#00ff88;font-weight:bold;cursor:pointer}.error{color:#ff8866;margin-bottom:10px}.footer{margin-top:20px;font-size:12px;color:#5a6e8a}a{color:#00b4ff}</style></head><body><div class="login-card"><h2>🔐 Admin Access</h2>{% if error %}<div class="error">{{ error }}</div>{% endif %}<form method="post"><input type="text" name="username" placeholder="Username" required><input type="password" name="password" placeholder="Password" required><button>Login</button></form><div class="footer">Developer: @rajfflive | <a href="https://t.me/rajfflive">Support</a></div></div></body></html>'''

ADMIN_HTML = '''<!DOCTYPE html>
<html><head><title>Admin Dashboard</title><meta name="viewport" content="width=device-width"><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif}
body{
    background: url('https://i.ibb.co/n8jX6HmQ/a4671110f8cc.jpg') no-repeat center center fixed;
    background-size: cover;
    backdrop-filter: blur(12px);
    padding: 20px;
    color: #fff;
}
.overlay{
    background: rgba(0, 0, 0, 0.5);
    border-radius: 32px;
    padding: 20px;
    min-height: 100vh;
}
.dashboard{max-width:1400px;margin:auto}
.stats-grid{display:flex;gap:20px;margin-bottom:20px;flex-wrap:wrap}
.stat-card{
    background: rgba(20, 30, 45, 0.85);
    backdrop-filter: blur(10px);
    padding: 20px;
    border-radius: 24px;
    flex: 1;
    min-width: 180px;
    text-align: center;
    border: 1px solid rgba(255, 255, 255, 0.2);
    transition: transform 0.2s;
    color: white;
}
.stat-card:hover{transform:translateY(-5px)}
.stat-number{font-size:2.5rem;font-weight:bold;color:#00ff88}
.card{
    background: rgba(20, 30, 45, 0.85);
    backdrop-filter: blur(10px);
    border-radius: 24px;
    padding: 24px;
    margin-bottom: 24px;
    border: 1px solid rgba(255, 255, 255, 0.2);
}
.row{display:flex;gap:15px;flex-wrap:wrap;margin-bottom:15px}
input,select,button{
    padding: 12px;
    border-radius: 12px;
    border: none;
    font-size: 14px;
    color: white;
}
input,select{
    background: rgba(0, 0, 0, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.3);
    color: white;
}
input::placeholder{color:#aaa}
button{
    background: linear-gradient(135deg, #00ff88, #00b4ff);
    color: #0a0f1e;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.2s;
}
button:hover{transform:scale(1.02); box-shadow: 0 0 12px rgba(0,255,136,0.4)}
.danger-btn{background:#ff4466; color:white}
.danger-btn:hover{background:#ff6688}
.success-btn{background:#00cc66; color:white}
table{width:100%;border-collapse:collapse}
th,td{padding:12px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.2)}
th{color:#00ff88}
.copy-btn{
    background: rgba(255,255,255,0.2);
    padding: 4px 12px;
    border-radius: 20px;
    margin-left: 8px;
    color: white;
    cursor: pointer;
    font-size: 12px;
}
.footer{margin-top:30px;text-align:center;font-size:12px;color:#ccc}
a{color:#00b4ff;text-decoration:none}
.badge{background:#00ff8822;color:#00ff88;padding:2px 10px;border-radius:20px;font-size:12px}
</style></head>
<body><div class="overlay"><div class="dashboard"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;margin-bottom:20px"><h1>🔐 Admin Panel <span class="badge">@rajfflive</span></h1><div><a href="/admin/logout" style="color:#ff8866;background:rgba(0,0,0,0.5);padding:8px 16px;border-radius:12px">🚪 Logout</a></div></div><div class="stats-grid"><div class="stat-card"><div class="stat-number">{{ total_keys }}</div><div>Total API Keys</div></div><div class="stat-card"><div class="stat-number">{{ total_bypassed }}</div><div>Total Bypassed</div></div><div class="stat-card"><div class="stat-number">{{ overall_success }}%</div><div>Overall Success Rate</div></div></div><div class="card"><h3>➕ Generate API Key</h3><form id="genForm" class="row"><input type="number" name="credits" placeholder="Credits" required><input type="number" name="expiry_days" placeholder="Expiry days"><select name="key_type"><option value="auto">Auto</option><option value="custom">Custom</option></select><input type="text" name="custom_key" placeholder="Custom key"><button type="submit">Generate Key</button></form><pre id="genResult" style="margin-top:10px;color:#00ff88"></pre></div><div class="card"><h3>💰 Add Credits</h3><form id="addForm" class="row"><input type="text" name="api_key" placeholder="API Key" required><input type="number" name="amount" placeholder="Amount" required><button type="submit">Add Credits</button></form><pre id="addResult" style="margin-top:10px;color:#00ff88"></pre></div><div class="card"><h3>📋 All Keys <button onclick="location.reload()" style="background:rgba(255,255,255,0.2);color:white;padding:8px 16px;margin-left:10px">⟳ Refresh</button> <button onclick="clearCache()" class="danger-btn" style="padding:8px 16px">🗑️ Clear Cache</button></h3><div style="overflow-x:auto;margin-top:15px"><table><th>API Key</th><th>Credits</th><th>Used</th><th>Bypassed</th><th>Success Rate</th><th>Expiry</th><th>Action</th></tr>{% for k,d in keys.items() %}<tr><td><span id="key-{{ loop.index }}">{{ k }}</span><button class="copy-btn" onclick="copyKey('{{ k }}',{{ loop.index }})">📋 Copy</button></div><div class="stat-number">{{ d.credits }}</div><div class="stat-number">{{ d.used }}</div><div class="stat-number">{{ d.bypassed }}</div><div class="stat-number">{{ (d.bypassed / d.used * 100)|round(1) if d.used > 0 else 0 }}%</div><div class="stat-number">{{ d.expiry[:10] if d.expiry else 'Never' }}</div><div class="stat-number"><button onclick="deleteKey('{{ k }}')" class="danger-btn" style="padding:6px 12px">Delete</button></div></tr>{% endfor %}</table></div></div><div class="footer">👑 Developer: @rajfflive | <a href="https://t.me/rajfflive">💬 Support</a> | <a href="/">🏠 Home</a></div></div></div><script>function copyKey(key,idx){ navigator.clipboard.writeText(key); alert('Copied: '+key); }async function deleteKey(key){ if(confirm('Delete this key?')){ let fd=new FormData(); fd.append('api_key',key); let r=await fetch('/admin/delete_key',{method:'POST',body:fd}); if(r.ok) location.reload(); else alert('Failed'); } }async function clearCache(){ if(confirm('Clear all cached bypass results?')){ let r=await fetch('/admin/clear_cache',{method:'POST'}); let d=await r.json(); if(d.status) alert('Cache cleared!'); else alert('Failed'); location.reload(); } }document.getElementById('genForm').onsubmit=async(e)=>{ e.preventDefault(); let fd=new FormData(e.target); let r=await fetch('/admin/generate',{method:'POST',body:fd}); let d=await r.json(); if(d.status){ document.getElementById('genResult').innerHTML=`✅ Generated: ${d.api_key}<br>Credits: ${d.credits}<br>Expiry: ${d.expiry_days||'None'}<br><button onclick="navigator.clipboard.writeText('${d.api_key}')">📋 Copy Key</button>`; setTimeout(()=>location.reload(),1500); } else document.getElementById('genResult').innerHTML=`❌ ${d.error}`; };document.getElementById('addForm').onsubmit=async(e)=>{ e.preventDefault(); let fd=new FormData(e.target); let r=await fetch('/admin/add_credits',{method:'POST',body:fd}); let d=await r.json(); if(d.status){ document.getElementById('addResult').innerHTML=`✅ Added! New balance: ${d.new_balance}`; setTimeout(()=>location.reload(),1000); } else document.getElementById('addResult').innerHTML=`❌ ${d.error}`; };</script></body></html>'''

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
