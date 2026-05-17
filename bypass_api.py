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
BOT_USERNAME = '@link_bypass_kd_bot'
ADMIN_SECRET = os.environ.get('ADMIN_SECRET', 'mysecret123')
SESSION_STRING = os.environ.get('SESSION_STRING', '')
PORT = int(os.environ.get('PORT', 10000))

if not API_ID or not API_HASH:
    raise ValueError("API_ID and API_HASH must be set")
if not SESSION_STRING:
    raise ValueError("SESSION_STRING missing")

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, loop=loop)

user_credits = {}
pending_requests = {}  # request_id -> {'link': link, 'timestamp': ...}
processed_request_ids = set()  # to prevent duplicate processing

def get_user(api_key):
    if api_key not in user_credits:
        user_credits[api_key] = {'credits': 0, 'total_used': 0, 'total_bypassed': 0, 'created_at': datetime.now().isoformat(), 'last_used': None, 'expiry': None}
    return user_credits[api_key]

def is_expired(api_key):
    expiry_str = get_user(api_key).get('expiry')
    if not expiry_str: return False
    try: return datetime.now() > datetime.fromisoformat(expiry_str)
    except: return False

def deduct_credit(api_key):
    if is_expired(api_key): return False, "API key expired"
    u = get_user(api_key)
    if u['credits'] >= 1:
        u['credits'] -= 1
        u['total_used'] += 1
        u['last_used'] = datetime.now().isoformat()
        return True, None
    return False, f"Insufficient credits (only {u['credits']} left)"

def add_credits(api_key, amount, expiry_days=None):
    u = get_user(api_key)
    u['credits'] += amount
    if expiry_days:
        u['expiry'] = (datetime.now() + timedelta(days=expiry_days)).isoformat()
    return u['credits']

def generate_api_key(): return "key_" + secrets.token_hex(12)

def extract_links_from_response(msg):
    src = re.search(r'Source:\s*(https?://[^\s]+)', msg, re.I)
    dst = re.search(r'Destination:\s*(https?://[^\s]+)', msg, re.I)
    return (src.group(1) if src else None, dst.group(1) if dst else None)

@app.route('/')
def index(): return render_template_string(HTML_UI)

@app.route('/health')
def health(): return jsonify({'status': 'ok', 'bot': BOT_USERNAME, 'developer': '@rajfflive', 'time': datetime.now().isoformat()})

@app.route('/bypass', methods=['GET', 'POST'])
def bypass():
    if request.method == 'GET':
        link = request.args.get('link')
        api_key = request.args.get('api_key')
    else:
        data = request.json or {}
        link = data.get('link')
        api_key = data.get('api_key')
    
    if not api_key: return jsonify({'status': False, 'error': 'Missing api_key', 'developer': '@rajfflive'})
    if not link: return jsonify({'status': False, 'error': 'Missing link', 'developer': '@rajfflive'})
    if not link.startswith(('http://','https://')): link = 'https://' + link
    
    ok, err = deduct_credit(api_key)
    if not ok: return jsonify({'status': False, 'error': err, 'credits_remaining': get_user(api_key)['credits'], 'developer': '@rajfflive'})
    
    req_id = secrets.token_hex(8)  # unique request ID
    pending_requests[req_id] = {'link': link, 'timestamp': time.time()}
    
    async def process():
        await client.send_message(BOT_USERNAME, link)
        # Poll for response
        for _ in range(20):  # 20 seconds
            await asyncio.sleep(1)
            # Get recent messages from bot (last 3)
            msgs = await client.get_messages(BOT_USERNAME, limit=3)
            for msg in msgs:
                if msg.text and 'Destination' in msg.text:
                    orig, bypassed = extract_links_from_response(msg.text)
                    if bypassed:
                        return {'original': orig or link, 'bypassed': bypassed}
        return None
    
    try:
        result = asyncio.run_coroutine_threadsafe(process(), loop).result(timeout=25)
        if result:
            u = get_user(api_key)
            u['total_bypassed'] += 1
            if req_id in pending_requests: del pending_requests[req_id]
            return jsonify({
                'status': True,
                'original_link': result['original'],
                'bypassed_link': result['bypassed'],
                'credits_remaining': u['credits'],
                'developer': '@rajfflive'
            })
        else:
            # refund credit
            u = get_user(api_key)
            u['credits'] += 1
            u['total_used'] -= 1
            if req_id in pending_requests: del pending_requests[req_id]
            return jsonify({'status': False, 'error': 'Bot did not respond with destination link in 20 seconds', 'developer': '@rajfflive'})
    except Exception as e:
        u = get_user(api_key)
        u['credits'] += 1
        u['total_used'] -= 1
        if req_id in pending_requests: del pending_requests[req_id]
        return jsonify({'status': False, 'error': str(e), 'developer': '@rajfflive'})

@app.route('/credits')
def credits():
    api_key = request.args.get('api_key')
    if not api_key: return jsonify({'status': False, 'error': 'Missing api_key', 'developer': '@rajfflive'})
    u = get_user(api_key)
    return jsonify({'status': True, 'credits_remaining': u['credits'], 'total_used': u['total_used'], 'total_bypassed': u['total_bypassed'], 'expiry': u['expiry'], 'expired': is_expired(api_key), 'developer': '@rajfflive'})

# ------------------- Admin Routes -------------------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST' and request.form.get('secret') == ADMIN_SECRET:
        session['admin_logged_in'] = True
        return redirect('/admin')
    if session.get('admin_logged_in'):
        return render_template_string(ADMIN_DASHBOARD, keys=user_credits)
    return render_template_string(ADMIN_LOGIN, error=None)

@app.route('/admin/logout')
def admin_logout(): session.pop('admin_logged_in', None); return redirect('/admin')

@app.route('/admin/generate', methods=['POST'])
def admin_generate():
    if not session.get('admin_logged_in'): return jsonify({'status': False, 'error': 'Not logged in'})
    key_type = request.form.get('key_type', 'auto')
    if key_type == 'auto': api_key = generate_api_key()
    else: api_key = request.form.get('custom_key', '').strip()
    if not api_key: return jsonify({'status': False, 'error': 'Empty key'})
    if api_key in user_credits: return jsonify({'status': False, 'error': 'Key exists'})
    credits = int(request.form.get('credits', 0))
    expiry_days = request.form.get('expiry_days')
    expiry = int(expiry_days) if expiry_days and expiry_days.isdigit() else None
    add_credits(api_key, credits, expiry)
    return jsonify({'status': True, 'api_key': api_key, 'credits': credits})

@app.route('/admin/add_credits', methods=['POST'])
def admin_add_credits():
    if not session.get('admin_logged_in'): return jsonify({'status': False, 'error': 'Not logged in'})
    api_key = request.form.get('api_key')
    amount = int(request.form.get('amount', 0))
    if not api_key or amount <= 0: return jsonify({'status': False, 'error': 'Invalid'})
    if api_key not in user_credits: return jsonify({'status': False, 'error': 'Key not found'})
    new_bal = add_credits(api_key, amount)
    return jsonify({'status': True, 'new_balance': new_bal})

@app.route('/admin/delete_key', methods=['POST'])
def admin_delete_key():
    if not session.get('admin_logged_in'): return jsonify({'status': False, 'error': 'Not logged in'})
    api_key = request.form.get('api_key')
    if api_key in user_credits: del user_credits[api_key]; return jsonify({'status': True})
    return jsonify({'status': False, 'error': 'Key not found'})

# HTML templates (same as before, omitted for brevity - include your existing HTML_UI, ADMIN_LOGIN, ADMIN_DASHBOARD)
HTML_UI = '''...'''  # copy from previous code, but keep developer @rajfflive
ADMIN_LOGIN = '''...'''
ADMIN_DASHBOARD = '''...'''

# ------------------- Start -------------------
def start_telegram():
    async def main():
        await client.connect()
        if not await client.is_user_authorized():
            print("ERROR: Invalid session string.")
            return
        print("✅ Telegram client connected")
        await client.send_message(BOT_USERNAME, '/start')
        await client.run_until_disconnected()
    loop.run_until_complete(main())

def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    start_telegram()
