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
    raise ValueError("Missing env")

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

def success_rate(used, bypassed):
    return 0.0 if used == 0 else round((bypassed / used) * 100, 2)

def run_async(coro):
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=30)

def clean_url(url):
    if not url:
        return url
    # Remove backticks, asterisks, underscores from start/end
    url = re.sub(r'^[`*_]+|[`*_]+$', '', url)
    url = url.replace('*', '').replace('`', '')
    # Ensure it starts with http
    if url and not url.startswith(('http://', 'https://')):
        url = 'https://' + url.lstrip('/')
    return url

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
        r'Bypassed\s*:\s*(https?://[^\s\n]+)'
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
            break
    if not dst:
        urls = re.findall(r'https?://[^\s\n]+', msg)
        if urls:
            dst = clean_url(urls[-1])
    if not src and 'urls' in locals() and urls:
        src = clean_url(urls[0])
    return src, dst

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
    print(f"[BYPASS] Link: {link}")

    req_key = f"{api_key}|{link}"
    now = time.time()
    if req_key in recent_requests and now - recent_requests[req_key] < 5:
        return jsonify({'status': False, 'error': 'Duplicate. Wait 5s', 'developer': '@rajfflive'})
    recent_requests[req_key] = now
    if len(recent_requests) > 200:
        recent_requests.clear()

    ok, err = deduct_credit(api_key)
    if not ok:
        u = get_user(api_key)
        return jsonify({'status': False, 'error': err, 'credits': u['credits'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})

    async def try_one_bot(bot):
        try:
            await client.send_message(bot, link)
            print(f"[TRY] Sent to {bot}")
        except Exception as e:
            print(f"[SEND ERR] {bot}: {e}")
            return None
        for _ in range(20):
            await asyncio.sleep(1)
            try:
                msgs = await client.get_messages(bot, limit=5)
            except:
                continue
            for msg in msgs:
                if msg.text:
                    src, dst = extract_links_from_message(msg.text)
                    # CRITICAL: Never return original link as bypassed
                    if dst and dst.startswith('http') and dst != link:
                        print(f"[SUCCESS] {bot} -> {dst}")
                        return {'src': src or link, 'dst': dst, 'bot': bot}
                    if 't.me' in msg.text:
                        urls = re.findall(r'https?://[^\s\n]+', msg.text)
                        if urls:
                            dst = clean_url(urls[-1])
                            if dst and dst != link:
                                print(f"[SUCCESS] {bot} (t.me) -> {dst}")
                                return {'src': link, 'dst': dst, 'bot': bot}
        print(f"[FAIL] {bot} no valid response")
        return None

    async def try_all():
        tasks = [asyncio.create_task(try_one_bot(bot)) for bot in BOT_LIST]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=25)
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
            # Refund credit
            u = get_user(api_key)
            u['credits'] += 1
            u['used'] -= 1
            return jsonify({'status': False, 'error': 'All bots failed', 'credits_remaining': u['credits'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})
    except Exception as e:
        u = get_user(api_key)
        u['credits'] += 1
        u['used'] -= 1
        return jsonify({'status': False, 'error': str(e), 'credits_remaining': u['credits'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'developer': '@rajfflive'})

@app.route('/credits')
def credits():
    api_key = request.args.get('api_key')
    if not api_key: return jsonify({'status': False, 'error': 'Missing api_key', 'developer': '@rajfflive'})
    u = get_user(api_key)
    return jsonify({'status': True, 'credits_remaining': u['credits'], 'total_used': u['used'], 'total_bypassed': u['bypassed'], 'success_rate': success_rate(u['used'], u['bypassed']), 'expiry': u['expiry'], 'developer': '@rajfflive'})

# Admin routes (same as before – omitted for brevity, but include your full admin HTML)
# ... (keep your existing admin routes and HTML templates)
# For the sake of completeness, I'll include them minimally, but you can copy from previous.
