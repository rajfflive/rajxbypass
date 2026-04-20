import os, asyncio, cloudscraper, datetime, pytz, json
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ==================== 🛠️ CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN")
API_URL = os.environ.get("NEW_API_URL") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajfflive"

# --- 📢 LINKS ---
CHANNELS = ["-1003898508261", "ffofcchat"] 
CHANNEL_1_LINK = "https://t.me/+HpoHOHMq0VpiYWVl" 
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
            client = AsyncIOMotorClient(MONGO_URL)
            db = client.bypass_bot
            users_col, groups_col = db.users, db.groups
            print("✅ Database Connected")
        except: print("⚠️ DB Error")

async def check_fj(u_id):
    if u_id == OWNER_ID: return True
    for c in CHANNELS:
        try:
            c_id = c if str(c).startswith("-100") else f"@{c}"
            m = await bot.get_chat_member(c_id, u_id)
            if m.status in ["left", "kicked", "restricted"]: return False
        except: return False
    return True

# ==================== 👑 OWNER COMMANDS ====================

@dp.message(Command("stats"), F.from_user.id == OWNER_ID)
async def cmd_stats(message: types.Message):
    u = await users_col.count_documents({}) if users_col else 0
    g = await groups_col.count_documents({}) if groups_col else 0
    await message.reply(f"📊 <b>Stats:</b>\nUsers: {u}\nGroups: {g}")

@dp.message(Command("broadcast"), F.from_user.id == OWNER_ID)
async def cmd_broadcast(message: types.Message):
    if not message.reply_to_message: return await message.reply("❌ Reply to a message!")
    users = await users_col.find().to_list(None) if users_col else []
    groups = await groups_col.find().to_list(None) if groups_col else []
    targets = list(set([u['user_id'] for u in users] + [g['group_id'] for g in groups]))
    sent = 0
    for t_id in targets:
        try: 
            await bot.copy_message(t_id, message.chat.id, message.reply_to_message.message_id)
            sent += 1
        except: pass
    await message.reply(f"📢 <b>Broadcast Done!</b> Sent to {sent} users/groups.")

# ==================== 🏎️ MAIN LOGIC ====================

@dp.message(Command("start"))
async def start(message: types.Message):
    if users_col: 
        await users_col.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger"))
    b.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
    await message.answer_photo(photo=WELCOME_PIC, caption="<blockquote>🏎️ <b>RAJX BYPASS SYSTEM</b>\n\nWelcome! Send link to bypass.</blockquote>", reply_markup=b.as_markup())

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    # Force Join Check
    is_verified = await check_fj(message.from_user.id)
    
    if not is_verified:
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify", style="success"))
        b.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
        return await message.reply("❗ <b>ACCESS DENIED! Join our channel.</b>", reply_markup=b.as_markup())

    # Private Bypass Control
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        # Agar aap chahte ho ki verified hone ke baad bhi private chat me na chale:
        b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
        return await message.reply("❌ <b>PRIVATE BYPASS DISABLED!</b>\n\nUse our official group to bypass links.", reply_markup=b.as_markup())

    # --- 🏎️ 10 STAGES PROCESSING ---
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
        # API Response Fix
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        
        # Extract from 'result' nested key
        res_inner = data.get("result", {})
        link = res_inner.get("bypassed", "Error")
        time_val = res_inner.get("time_taken", "N/A")
        usage_val = res_inner.get("usage_count", "N/A")

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
        
        b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger"))
        await status.edit_text(res_text, reply_markup=b.as_markup(), disable_web_page_preview=True)
    except Exception as e:
        await status.edit_text(f"❌ <b>API ERROR!</b>\n<code>{str(e)}</code>")

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_fj(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Join channels first!", show_alert=True)

# ==================== RUNNER ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Online"

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    print("🤖 Bot Ready")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
