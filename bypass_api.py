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

def get_cached(original):
    if original in bypass_cache:
        entry = bypass_cache[original]
        if time.time() - entry['ts'] < CACHE_TTL:
            bypass_cache.move_to_end(original)
            # Additional safety: ensure cached link is not same as original
            if entry['bypassed'] == original:
                print(f"[CACHE] WARNING: cached link same as original, deleting")
                del bypass_cache[original]
                return None
            return entry['bypassed']
        else:
            del bypass_cache[original]
    return None

def set_cached(original, bypassed):
    # Only cache if bypassed is a valid destination and different from original
    if bypassed and bypassed != original and is_valid_destination(bypassed):
        bypass_cache[original] = {'bypassed': bypassed, 'ts': time.time()}
        if len(bypass_cache) > MAX_CACHE_SIZE:
            bypass_cache.popitem(last=False)
        print(f"[CACHE] Stored: {original} -> {bypassed}")
    else:
        print(f"[CACHE] Not storing invalid: {original} -> {bypassed}")

# --- Rest of helper functions (get_user, is_expired, deduct_credit, etc.) remain same ---
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

def is_valid_bypass(original, candidate):
    if not candidate or candidate == original: return False
    if not candidate.startswith(('http://', 'https://')): return False
    return is_valid_destination(candidate)

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
        if m: src = clean_url(m.group(1)); break
    for pat in dst_patterns:
        m = re.search(pat, msg, re.I)
        if m:
            dst = clean_url(m.group(1))
            if dst and is_valid_destination(dst):
                break
            else: dst = None
    if not dst:
        urls = re.findall(r'https?://[^\s\n]+', msg)
        for u in reversed(urls):
            cand = clean_url(u)
            if cand and (not src or cand != src) and is_valid_destination(cand):
                dst = cand; break
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

    # duplicate check
    req_key = f"{api_key}|{link}"
    now = time.time()
    if req_key in recent_requests and now - recent_requests[req_key] < 5:
        return jsonify({'status': False, 'error': 'Duplicate. Wait 5s', 'developer': '@rajfflive'})
    recent_requests[req_key] = now
    if len(recent_requests) > 200: recent_requests.clear()

    # check cache
    cached = get_cached(link)
    if cached:
        ok, err = deduct_credit(api_key)
        if not ok:
            u = get_user(api_key)
            return jsonify({'status': False, 'error': err, 'credits': u['credits'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})
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

    # deduct credit for live request
    ok, err = deduct_credit(api_key)
    if not ok:
        u = get_user(api_key)
        return jsonify({'status': False, 'error': err, 'credits': u['credits'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})

    async def try_bot(bot):
        try:
            sent = await client.send_message(bot, link)
            async def del_sent():
                await asyncio.sleep(60)
                try: await sent.delete()
                except: pass
            asyncio.create_task(del_sent())
        except: return None
        for _ in range(12):
            await asyncio.sleep(1)
            try:
                msgs = await client.get_messages(bot, limit=3)
            except: continue
            for msg in msgs:
                if msg.text:
                    src, dst = extract_links_from_message(msg.text)
                    if dst and is_valid_bypass(link, dst):
                        async def del_resp():
                            await asyncio.sleep(60)
                            try: await msg.delete()
                            except: pass
                        asyncio.create_task(del_resp())
                        return {'src': src or link, 'dst': dst, 'bot': bot}
                    if 't.me' in msg.text:
                        urls = re.findall(r'https?://[^\s\n]+', msg.text)
                        for u in urls:
                            cand = clean_url(u)
                            if cand and 't.me' in cand and cand != link and is_valid_bypass(link, cand):
                                async def del_resp2():
                                    await asyncio.sleep(60)
                                    try: await msg.delete()
                                    except: pass
                                asyncio.create_task(del_resp2())
                                return {'src': link, 'dst': cand, 'bot': bot}
        return None

    async def try_all():
        tasks = [asyncio.create_task(try_bot(bot)) for bot in BOT_LIST]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=12)
        for t in pending: t.cancel()
        for t in done:
            res = t.result()
            if res: return res
        return None

    try:
        result = run_async(try_all())
        if result:
            u = get_user(api_key)
            u['bypassed'] += 1
            # Store in cache only if valid
            if is_valid_bypass(link, result['dst']):
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
            u['credits'] += 1; u['used'] -= 1
            return jsonify({'status': False, 'error': 'No valid bypass found.', 'credits_remaining': u['credits'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})
    except Exception as e:
        u = get_user(api_key)
        u['credits'] += 1; u['used'] -= 1
        return jsonify({'status': False, 'error': str(e), 'credits_remaining': u['credits'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})

@app.route('/credits')
def credits():
    api_key = request.args.get('api_key')
    if not api_key: return jsonify({'status': False, 'error': 'Missing api_key', 'developer': '@rajfflive'})
    u = get_user(api_key)
    return jsonify({'status': True, 'credits_remaining': u['credits'], 'total_used': u['used'],
                    'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']),
                    'expiry': u['expiry'], 'developer': '@rajfflive'})

# ---------- Admin routes (same as before, keep existing implementation) ----------
# (I'll include minimal admin routes to save space, but you can add full from previous)
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

# ---------- HTML Templates (Home, Login, Admin with background) ----------
# (Copy from previous final message, they are identical so I'll reuse the same strings)
HOME_HTML = '''<!DOCTYPE html>...'''  # Use the HOME_HTML from earlier
LOGIN_HTML = '''<!DOCTYPE html>...'''  # Use from earlier
ADMIN_HTML = '''<!DOCTYPE html>...'''  # Use the one with blurred background and buttons

# Start functions
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
