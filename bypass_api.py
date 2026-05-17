from flask import Flask, request, jsonify, render_template_string
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import threading
import time
import re
import os
from datetime import datetime

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
BOT_USERNAME = '@link_bypass_kd_bot'
ADMIN_SECRET = os.environ.get('ADMIN_SECRET', 'SuperSecret@123')
DEFAULT_CREDITS = 0
SESSION_STRING = os.environ.get('SESSION_STRING')  # Ye aapki di hui string

app = Flask(__name__)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Ye line important hai - StringSession use kar rahe hai
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, loop=loop)

user_credits = {}
pending_requests = {}

def get_user(api_key):
    if api_key not in user_credits:
        user_credits[api_key] = {'credits': DEFAULT_CREDITS, 'total_used': 0, 'total_bypassed': 0, 'created_at': datetime.now().isoformat(), 'last_used': None}
    return user_credits[api_key]

def deduct_credit(api_key):
    u = get_user(api_key)
    if u['credits'] >= 1:
        u['credits'] -= 1
        u['total_used'] += 1
        u['last_used'] = datetime.now().isoformat()
        return True
    return False

def add_credits(api_key, amt):
    u = get_user(api_key)
    u['credits'] += amt
    return u['credits']

def extract_links_from_response(msg):
    src = re.search(r'Source:\s*(https?://[^\s]+)', msg, re.I)
    dst = re.search(r'Destination:\s*(https?://[^\s]+)', msg, re.I)
    return (src.group(1) if src else None, dst.group(1) if dst else None)

@client.on(events.NewMessage(chats=BOT_USERNAME))
async def handler(event):
    text = event.message.text
    if 'Destination' not in text: return
    orig, bypass = extract_links_from_response(text)
    if not bypass: return
    for rid, req in list(pending_requests.items()):
        if req['original_link'] in text or (orig and orig == req['original_link']):
            pending_requests[rid]['result'] = {'original_link': orig or req['original_link'], 'bypassed_link': bypass}
            pending_requests[rid]['complete'] = True
            break

def run_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=30)

@app.route('/')
def index():
    return render_template_string(HTML_UI)

@app.route('/bypass', methods=['GET','POST'])
def bypass():
    if request.method == 'GET':
        link = request.args.get('link')
        api_key = request.args.get('api_key')
    else:
        data = request.json or {}
        link = data.get('link')
        api_key = data.get('api_key')
    if not api_key or not link:
        return jsonify({'status': False, 'error': 'Missing api_key or link'})
    if not link.startswith(('http://','https://')):
        link = 'https://' + link
    if not deduct_credit(api_key):
        return jsonify({'status': False, 'error': 'Insufficient credits', 'credits': get_user(api_key)['credits']})
    req_id = str(int(time.time()*1000))
    pending_requests[req_id] = {'original_link': link, 'complete': False, 'result': None}
    try:
        run_async(client.send_message(BOT_USERNAME, link))
        start = time.time()
        while time.time() - start < 25:
            time.sleep(0.5)
            if pending_requests.get(req_id, {}).get('complete'):
                res = pending_requests[req_id]['result']
                del pending_requests[req_id]
                get_user(api_key)['total_bypassed'] += 1
                return jsonify({'status': True, 'original_link': res['original_link'], 'bypassed_link': res['bypassed_link'], 'credits_remaining': get_user(api_key)['credits']})
        # timeout refund
        u = get_user(api_key)
        u['credits'] += 1
        u['total_used'] -= 1
        if req_id in pending_requests: del pending_requests[req_id]
        return jsonify({'status': False, 'error': 'Bot timeout'})
    except Exception as e:
        u = get_user(api_key)
        u['credits'] += 1
        u['total_used'] -= 1
        if req_id in pending_requests: del pending_requests[req_id]
        return jsonify({'status': False, 'error': str(e)})

@app.route('/credits')
def credits():
    api_key = request.args.get('api_key')
    if not api_key: return jsonify({'status': False, 'error': 'Missing api_key'})
    u = get_user(api_key)
    return jsonify({'status': True, 'credits_remaining': u['credits'], 'total_used': u['total_used'], 'total_bypassed': u['total_bypassed']})

@app.route('/admin/add_credits', methods=['POST'])
def admin_add():
    data = request.json or {}
    if data.get('admin_key') != ADMIN_SECRET: return jsonify({'status': False, 'error': 'Invalid admin key'})
    target = data.get('api_key'); amount = data.get('amount', 0)
    if not target or not isinstance(amount, int) or amount <= 0: return jsonify({'status': False, 'error': 'Invalid api_key or amount'})
    new_bal = add_credits(target, amount)
    return jsonify({'status': True, 'new_balance': new_bal})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'bot': BOT_USERNAME})

HTML_UI = '''<!DOCTYPE html>
<html><head><title>KD Link Bypass API</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#0a0f1e;color:#fff;font-family:Arial;text-align:center;padding:20px}.card{background:#1e2a3a;margin:20px auto;padding:20px;border-radius:15px;max-width:600px}input,button{padding:10px;margin:5px;border-radius:8px;border:none}input{width:70%;background:#2d3e4e;color:#fff}button{background:#00b4ff;cursor:pointer}.result{background:#0a0f1e;padding:10px;border-radius:8px;margin-top:10px;word-break:break-all}.credit{color:#00ff88;font-size:1.5em}</style></head>
<body><div class="card"><h1>🔗 KD Link Bypass API</h1><p>Bot: @link_bypass_kd_bot | API by @mikey_bhai1</p><div class="credit" id="creditDisplay">Credits: --</div><hr><h3>Your API Key</h3><input type="text" id="apiKey" readonly><br><button onclick="generateKey()">Generate New Key</button><button onclick="checkCredits()">Check Credits</button><hr><h3>Bypass Link</h3><input type="text" id="linkInput" placeholder="Enter link (e.g., https://shrinkme.click/abc)"><button onclick="bypass()">Bypass Now</button><div id="result" class="result"></div></div><script>let apiKey=localStorage.getItem('api_key');if(!apiKey)generateKey();else document.getElementById('apiKey').value=apiKey;function generateKey(){apiKey='user_'+Math.random().toString(36).substr(2,16);localStorage.setItem('api_key',apiKey);document.getElementById('apiKey').value=apiKey;checkCredits()}async function checkCredits(){let res=await fetch(`/credits?api_key=${apiKey}`);let data=await res.json();if(data.status)document.getElementById('creditDisplay').innerText=`Credits: ${data.credits_remaining}`;else document.getElementById('creditDisplay').innerText='Credits: Error'}async function bypass(){let link=document.getElementById('linkInput').value;let resultDiv=document.getElementById('result');if(!link){resultDiv.innerHTML='❌ Enter link';return}resultDiv.innerHTML='⏳ Processing...';try{let res=await fetch('/bypass',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({link:link,api_key:apiKey})});let data=await res.json();if(data.status){resultDiv.innerHTML=`✅ Bypassed: <a href="${data.bypassed_link}" target="_blank">${data.bypassed_link}</a><br>💎 Credits left: ${data.credits_remaining}`;}else{resultDiv.innerHTML=`❌ ${data.error}`;}checkCredits();}catch(e){resultDiv.innerHTML='❌ Error: '+e.message}}checkCredits();</script></body></html>'''

def start_telegram():
    async def start():
        await client.start()
        print("🔥 Bot API started. Bot:", BOT_USERNAME)
        await client.send_message(BOT_USERNAME, '/start')
        await client.run_until_disconnected()
    loop.run_until_complete(start())

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5010)), debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    start_telegram()
