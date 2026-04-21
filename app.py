import os, asyncio, cloudscraper, datetime, pytz, json
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, ReactionTypeEmoji
from motor.motor_asyncio import AsyncIOMotorClient

# ==================== 🛠️ CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN")
API_URL = os.environ.get("NEW_API_URL")
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = int(os.environ.get("OWNER_ID", "8154922225"))
DEV_HANDLE = "@rajfflive"

CHANNELS = ["-1003898508261", "ffofcchat"]
CHANNEL_LINK = "https://t.me/+HpoHOHMq0VpiYWVl"
GROUP_LINK = "https://t.me/ffofcchat"
BUY_API_LINK = "https://t.me/visitpornhub"
WELCOME_PIC = "https://i.ibb.co/8L91y1CP/6ee42acc1338.jpg"

# ==================== DATABASE & BOT SETUP ====================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()
users_col, groups_col = None, None

async def init_db():
    global users_col, groups_col
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
            db = client.bypass_bot
            users_col, groups_col = db.users, db.groups
            print("✅ [DB] MongoDB Initialized!")
        except Exception as e:
            print(f"❌ [DB] Failed: {e}")
    else:
        print("⚠️ [DB] MONGO_URL not set!")

async def save_user(user: types.User):
    if not users_col: return
    try:
        existing = await users_col.find_one({"user_id": user.id})
        if not existing:
            await users_col.insert_one({"user_id": user.id, "name": user.first_name, "username": user.username or "N/A", "joined": datetime.datetime.utcnow()})
            print(f"🆕 [NEW USER] {user.first_name} | ID: {user.id} | @{user.username or 'N/A'}")
        else:
            await users_col.update_one({"user_id": user.id}, {"$set": {"name": user.first_name, "username": user.username or "N/A"}})
    except Exception as e:
        print(f"❌ [SAVE USER ERROR] {e}")

async def save_group(chat: types.Chat):
    if not groups_col: return
    try:
        existing = await groups_col.find_one({"group_id": chat.id})
        if not existing:
            await groups_col.insert_one({"group_id": chat.id, "title": chat.title or "Unknown", "username": chat.username or "N/A", "joined": datetime.datetime.utcnow()})
            print(f"🆕 [NEW GROUP] {chat.title} | ID: {chat.id} | @{chat.username or 'N/A'}")
        else:
            await groups_col.update_one({"group_id": chat.id}, {"$set": {"title": chat.title or "Unknown", "username": chat.username or "N/A"}})
    except Exception as e:
        print(f"❌ [SAVE GROUP ERROR] {e}")

async def check_fj(u_id):
    if u_id == OWNER_ID: return True
    for c in CHANNELS:
        try:
            c_id = c if str(c).startswith("-100") else f"@{c}"
            m = await bot.get_chat_member(c_id, u_id)
            if m.status in ["left", "kicked", "restricted"]:
                print(f"⚠️ [VERIFY] User {u_id} not in {c_id} — Status: {m.status}")
                return False
        except Exception as e:
            print(f"❌ [VERIFY ERROR] Channel: {c} | User: {u_id} | Error: {e}")
            return False
    return True

# ==================== 👑 OWNER COMMANDS ====================

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    print(f"📊 [OWNER CMD] /stats by {message.from_user.id}")
    u = await users_col.count_documents({}) if users_col else 0
    g = await groups_col.count_documents({}) if groups_col else 0
    await message.reply(f"📊 <b>Stats:</b>\nUsers: {u}\nGroups: {g}")

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    print(f"📢 [OWNER CMD] /broadcast by {message.from_user.id}")
    if not message.reply_to_message: return await message.reply("❌ Reply to a message!")
    users = await users_col.find().to_list(None) if users_col else []
    groups = await groups_col.find().to_list(None) if groups_col else []
    targets = list(set([u['user_id'] for u in users] + [g['group_id'] for g in groups]))
    sent, failed = 0, 0
    for t_id in targets:
        try:
            await bot.copy_message(t_id, message.chat.id, message.reply_to_message.message_id)
            sent += 1
        except Exception as e:
            failed += 1
            print(f"❌ [BROADCAST FAIL] {t_id} | {e}")
    print(f"📢 [BROADCAST DONE] Sent: {sent} | Failed: {failed}")
    await message.reply(f"📢 <b>Broadcast Done!</b> Sent: {sent} | Failed: {failed}")

# ==================== 🏎️ MAIN LOGIC ====================

@dp.message(Command("start"))
async def start(message: types.Message):
    await save_user(message.from_user)
    if message.chat.type in ["group", "supergroup"]: await save_group(message.chat)
    print(f"▶️ [START] {message.from_user.first_name} | ID: {message.from_user.id} | {message.chat.type}")
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK))
    b.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK))
    await message.answer_photo(photo=WELCOME_PIC, caption="<blockquote>🏎️ <b>RAJX BYPASS SYSTEM</b>\n\nWelcome! Send link to bypass.</blockquote>", reply_markup=b.as_markup())

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    await save_user(message.from_user)
    if message.chat.type in ["group", "supergroup"]: await save_group(message.chat)
    print(f"🔗 [BYPASS] {message.from_user.first_name} | ID: {message.from_user.id} | {message.text.strip()[:60]}...")
    try: await message.react([ReactionTypeEmoji(emoji="👀")])
    except: pass

    is_verified = await check_fj(message.from_user.id)
    if not is_verified:
        print(f"🚫 [ACCESS DENIED] {message.from_user.id}")
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="Join Channel 📢", url=CHANNEL_LINK))
        b.row(InlineKeyboardButton(text="Join Group 💬", url=GROUP_LINK))
        b.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify"))
        b.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK))
        return await message.reply("❗ <b>ACCESS DENIED! Join BOTH our channel and group.</b>", reply_markup=b.as_markup())

    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        print(f"🚫 [PRIVATE BLOCKED] {message.from_user.id}")
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK))
        return await message.reply("❌ <b>PRIVATE BYPASS DISABLED!</b>\n\nUse our official group.", reply_markup=b.as_markup())

    status = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    stages = [
        ("█░░░░░░░░░░░  10%", "Connecting..."), ("██░░░░░░░░░░  20%", "Bypassing Ads..."),
        ("███░░░░░░░░░  30%", "Safety Check..."), ("████░░░░░░░░  40%", "Solving Captcha..."),
        ("█████░░░░░░░  50%", "Extracting Data..."), ("██████░░░░░░  60%", "Bypassing Links..."),
        ("████████░░░░  75%", "Decrypting URL..."), ("██████████░░  85%", "Finalizing Result..."),
        ("████████████  95%", "Generating Link..."), ("████████████  100%", "Success! ✅")
    ]
    for bar, text in stages:
        await asyncio.sleep(0.1)
        try: await status.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    try:
        print(f"🌐 [API CALL] User: {message.from_user.id}")
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30).json()
        res_data = response.get("result", {})
        link = res_data.get("bypassed", "Error")
        time_val = res_data.get("time_taken", "N/A")
        usage_val = res_data.get("usage_count", "N/A")
        print(f"✅ [API SUCCESS] User: {message.from_user.id} | Link: {link[:60]}...")
        try: await message.react([ReactionTypeEmoji(emoji="💯")])
        except: pass
        IST = pytz.timezone('Asia/Kolkata')
        time_now = datetime.datetime.now(IST).strftime("%I:%M %p | %d-%b")
        res_text = (
            "<blockquote>"
            "🏎️ <b>BYPASS SUCCESSFUL!</b> ⚡\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>User:</b> {message.from_user.first_name}\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 <b>Original:</b>\n<code>{message.text.strip()}</code>\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 <b>Bypassed Link:</b>\n{link}\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚡ <b>Time Taken:</b> <code>{time_val}</code>\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>Usage Count:</b> <code>{usage_val}</code>\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🕒 <b>Time:</b> <code>{time_now}</code>\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👑 <b>Owner:</b> {DEV_HANDLE}\n━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK))
        await status.edit_text(res_text, reply_markup=b.as_markup(), disable_web_page_preview=True)
    except Exception as e:
        print(f"❌ [API ERROR] {message.from_user.id} | {e}")
        await status.edit_text("❌ <b>API ERROR!</b>")

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_fj(cb.from_user.id):
        print(f"✅ [VERIFIED] {cb.from_user.id}")
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else:
        print(f"❌ [VERIFY FAIL] {cb.from_user.id}")
        await cb.answer("❌ Join BOTH channel and group first!", show_alert=True)

# ==================== RUNNER ====================
server = Flask(__name__)

@server.route('/')
def st(): return "Online"

async def main():
    print("=" * 40)
    print(f"🤖 BOT TOKEN:   {'✅ SET' if TOKEN else '❌ MISSING'}")
    print(f"🌐 API URL:     {'✅ SET' if API_URL else '❌ MISSING'}")
    print(f"🗄️  MONGO URL:   {'✅ SET' if MONGO_URL else '❌ MISSING'}")
    print(f"👑 OWNER ID:    {OWNER_ID}")
    print("=" * 40)
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    print("🚀 Bot Started! Polling...")
    asyncio.create_task(init_db())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
