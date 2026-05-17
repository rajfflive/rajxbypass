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

def extract_links_from_message(msg):
    src_match = re.search(r'(?:Original Link|Source)\s*:?✅?\s*(https?://[^\s\n]+)', msg, re.I)
    dst_match = re.search(r'(?:Bypassed Link|Destination)\s*:?✅?\s*(https?://[^\s\n]+)', msg, re.I)
    src = src_match.group(1) if src_match else None
    dst = dst_match.group(1) if dst_match else None
    if not dst:
        urls = re.findall(r'https?://[^\s\n]+', msg)
        if urls:
            dst = urls[-1]
    if not src and 'urls' in locals() and urls:
        src = urls[0]
    return src, dst

def success_rate(used, bypassed):
    return 0.0 if used == 0 else round((bypassed / used) * 100, 2)

def run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)

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
    
    # Clean and validate link
    link = link.strip()
    if not link.startswith(('http://', 'https://')):
        link = 'https://' + link
    
    # Log to console (Render logs)
    print(f"[BYPASS] Received link: {link}")
    
    # Duplicate check
    req_key = f"{api_key}|{link}"
    now = time.time()
    if req_key in recent_requests and now - recent_requests[req_key] < 5:
        return jsonify({'status': False, 'error': 'Duplicate request. Wait 5s', 'developer': '@rajfflive'})
    recent_requests[req_key] = now
    if len(recent_requests) > 200:
        recent_requests.clear()
    
    ok, err = deduct_credit(api_key)
    if not ok:
        u = get_user(api_key)
        return jsonify({'status': False, 'error': err, 'credits': u['credits'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})
    
    async def try_one_bot(bot):
        # Ensure link is sent as raw text, no extra whitespace
        await client.send_message(bot, link)
        print(f"[TRY] Sent to {bot}: {link}")
        for _ in range(20):
            await asyncio.sleep(1)
            msgs = await client.get_messages(bot, limit=5)
            for msg in msgs:
                if msg.text and ('Bypassed Link' in msg.text or 'Destination' in msg.text):
                    src, dst = extract_links_from_message(msg.text)
                    if dst:
                        print(f"[SUCCESS] {bot} returned: {dst}")
                        return {'src': src or link, 'dst': dst, 'bot': bot}
                if msg.text and 't.me' in msg.text:
                    urls = re.findall(r'https?://[^\s\n]+', msg.text)
                    if urls:
                        dst = urls[-1]
                        print(f"[SUCCESS] {bot} fallback: {dst}")
                        return {'src': link, 'dst': dst, 'bot': bot}
        print(f"[FAIL] {bot} no response")
        return None
    
    async def try_all_bots():
        tasks = [asyncio.create_task(try_one_bot(bot)) for bot in BOT_LIST]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=25)
        for task in pending:
            task.cancel()
        for task in done:
            result = task.result()
            if result:
                return result
        return None
    
    try:
        result = run_async(try_all_bots())
        if result:
            u = get_user(api_key)
            u['bypassed'] += 1
            return jsonify({
                'status': True,
                'original_link': result['src'],
                'bypassed_link': result['dst'],
                'credits_remaining': u['credits'],
                'total_bypassed': u['bypassed'],
                'success_rate': success_rate(u['used'], u['bypassed']),
                'used_bot': result['bot'],
                'developer': '@rajfflive'
            })
        else:
            u = get_user(api_key)
            u['credits'] += 1
            u['used'] -= 1
            return jsonify({'status': False, 'error': 'All bots failed to respond (link might be invalid)', 'credits_remaining': u['credits'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})
    except Exception as e:
        u = get_user(api_key)
        u['credits'] += 1
        u['used'] -= 1
        return jsonify({'status': False, 'error': str(e), 'credits_remaining': u['credits'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})

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
        'success_rate': success_rate(u['used'], u['bypassed']),
        'expiry': u['expiry'],
        'developer': '@rajfflive'
    })

# ------------------- Admin Panel (unchanged but included for completeness) -------------------
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
        return render_template_string(ADMIN_HTML, keys=user_credits, total_keys=total_keys, total_bypassed=total_bypassed, overall_success=overall_success)
    return render_template_string(LOGIN_HTML, error=None)

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

# ==================== HTML TEMPLATES (same as before, omitted for brevity) ====================
# I'll include them as they are long, but to save space I'll put a placeholder.
# In your actual code, keep your existing HOME_HTML, LOGIN_HTML, ADMIN_HTML.
# For the sake of completeness, I assume you already have them.

# ----------------------------------------------------------------------
# START TELEGRAM
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
