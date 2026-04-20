import os, asyncio, cloudscraper, datetime, pytz
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

# --- 📢 LINKS & CHANNELS ---
CHANNELS = ["-1003898508261", "ffofcchat"] 
CHANNEL_1_LINK = "https://t.me/+HpoHOHMq0VpiYWVl" 
GROUP_LINK = "https://t.me/ffofcchat"
BUY_API_LINK = "https://t.me/visitpornhub"
WELCOME_PIC = "https://i.ibb.co/8L91y1CP/6ee42acc1338.jpg"

# ==================== BOT SETUP ====================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

users_col = None
groups_col = None

async def init_db():
    global users_col, groups_col
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL)
            db = client.bypass_bot
            users_col = db.users
            groups_col = db.groups
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
    u_count = await users_col.count_documents({}) if users_col else 0
    g_count = await groups_col.count_documents({}) if groups_col else 0
    await message.reply(f"📊 <b>BOT STATISTICS</b>\n\n👤 <b>Users:</b> {u_count}\n👥 <b>Groups:</b> {g_count}")

@dp.message(Command("broadcast"), F.from_user.id == OWNER_ID)
async def cmd_broadcast(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("❌ Reply to a message to broadcast!")
    
    users = await users_col.find().to_list(None) if users_col else []
    groups = await groups_col.find().to_list(None) if groups_col else []
    targets = list(set([u['user_id'] for u in users] + [g['group_id'] for g in groups]))
    
    ok, fail = 0, 0
    msg = await message.reply(f"🚀 <b>Broadcasting to {len(targets)} targets...</b>")
    for t_id in targets:
        try:
            await bot.copy_message(t_id, message.chat.id, message.reply_to_message.message_id)
            ok += 1
            await asyncio.sleep(0.05)
        except: fail += 1
    await msg.edit_text(f"📢 <b>Broadcast Done!</b>\n\n✅ Success: {ok}\n❌ Failed: {fail}")

# ==================== 🏎️ BYPASS LOGIC ====================

@dp.message(Command("start"))
async def start(message: types.Message):
    if users_col:
        await users_col.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)
    
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger"))
    b.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
    
    caption = (
        "<blockquote>"
        f"🏎️ <b>RAJX BYPASS SYSTEM</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Welcome <b>{message.from_user.first_name}</b>!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Send any link to bypass or join our community.\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
        "</blockquote>"
    )
    await message.answer_photo(photo=WELCOME_PIC, caption=caption, reply_markup=b.as_markup())

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    # Auto-save Group ID
    if message.chat.type in ["group", "supergroup"] and groups_col:
        await groups_col.update_one({"group_id": message.chat.id}, {"$set": {"title": message.chat.title}}, upsert=True)

    if not await check_fj(message.from_user.id):
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_1_LINK, style="primary"))
        b.row(InlineKeyboardButton(text="💬 Join Group", url=GROUP_LINK, style="primary"))
        b.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify", style="success"))
        return await message.reply("<blockquote>❗ <b>ACCESS DENIED!</b>\n\n━━━━━━━━━━━━━━━━━━━━\n\nYou must join our channels to use this bot.\n\n━━━━━━━━━━━━━━━━━━━━</blockquote>", reply_markup=b.as_markup())

    # --- 10 STAGES ANIMATION ---
    status = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    stages = [
        ("█░░░░░░░░░░░  10%", "<b>Connecting Proxy... 🛰️</b>"),
        ("██░░░░░░░░░░  20%", "<b>Bypassing Ads... ⛈️</b>"),
        ("███░░░░░░░░░  30%", "<b>Checking Safety... 🛡️</b>"),
        ("████░░░░░░░░  40%", "<b>Solving Captcha... 🤖</b>"),
        ("██████░░░░░░  55%", "<b>Extracting Data... 🔓</b>"),
        ("███████░░░░░  65%", "<b>Bypassing Links... ⚡</b>"),
        ("█████████░░░  80%", "<b>Decrypting URL... 🔑</b>"),
        ("██████████░░  90%", "<b>Finalizing Result... ✨</b>"),
        ("████████████  98%", "<b>Generating Response... 📝</b>"),
        ("████████████  100%", "<b>Success! ✅</b>")
    ]

    for bar, text in stages:
        await asyncio.sleep(0.15)
        try: await status.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    try:
        r = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30).json()
        IST = pytz.timezone('Asia/Kolkata')
        time_now = datetime.datetime.now(IST).strftime("%I:%M %p | %d-%b")
        
        link = r.get("bypassed") or r.get("url") or r.get("result")
        if isinstance(link, dict): link = link.get("url")

        if not link or str(link).lower() == "none":
            return await status.edit_text("<blockquote>❌ <b>LINK NOT FOUND!</b></blockquote>")

        res_text = (
            "<blockquote>"
            "🏎️ <b>BYPASS SUCCESSFUL!</b> ⚡\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>User:</b> {message.from_user.first_name}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 <b>Original Link:</b>\n<code>{message.text[:35]}...</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 <b>Bypassed Link:</b>\n<b>{link}</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🕒 <b>Time:</b> <code>{time_now}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👑 <b>Owner:</b> {DEV_HANDLE}\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        await status.edit_text(res_text, disable_web_page_preview=True)
    except:
        await status.edit_text("❌ API Error!")

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
