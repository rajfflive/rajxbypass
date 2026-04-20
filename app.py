import os
import asyncio
import cloudscraper
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN")
API_URL = os.environ.get("NEW_API_URL") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajxcheats"
CHANNELS = ["rajxcheats", "ffofcchat"] # Default Channels
GROUP_LINK = "https://t.me/ffofcchat"
WELCOME_PIC = "https://i.ibb.co/8L91y1CP/6ee42acc1338.jpg"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# --- Database for Admin & Stats ---
db_client = None
users_db = None
settings_db = None

async def init_db():
    global db_client, users_db, settings_db
    if MONGO_URL:
        try:
            db_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            db = db_client.bypass_bot
            users_db = db.users
            settings_db = db.settings
            await db_client.server_info()
            print("✅ Admin Database Connected")
        except: print("⚠️ Running without DB")

# ==================== HELPERS ====================

async def check_force_join(user_id):
    if user_id == OWNER_ID: return True
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ["left", "kicked"]: return False
        except: return False
    return True

# ==================== OWNER COMMANDS (ALL IN ONE) ====================

@dp.message(Command("admin"), F.from_user.id == OWNER_ID)
@dp.message(Command("owner"), F.from_user.id == OWNER_ID)
async def owner_panel(message: types.Message):
    text = (
        "👑 <b>RAJX OWNER PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>Stats:</b> /stats\n"
        "📢 <b>Broadcast:</b> /broadcast (Reply to msg)\n"
        "➕ <b>Add Channel:</b> /addchan @username\n"
        "👤 <b>Total Users:</b> /users\n"
        "🧹 <b>Clear DB:</b> /cleardb\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await message.reply(text)

@dp.message(Command("stats"), F.from_user.id == OWNER_ID)
async def cmd_stats(message: types.Message):
    count = await users_db.count_documents({}) if users_db else "N/A"
    await message.reply(f"📊 <b>Current Stats:</b>\n\n👤 Total Users: <code>{count}</code>\n🏎️ Bot Status: <code>Active</code>")

@dp.message(Command("broadcast"), F.from_user.id == OWNER_ID)
async def cmd_broadcast(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("❌ Kisi message ko reply karke /broadcast likho!")
    
    users = await users_db.find().to_list(length=10000)
    count = 0
    for u in users:
        try:
            await bot.copy_message(u['user_id'], message.chat.id, message.reply_to_message.message_id)
            count += 1
        except: pass
    await message.reply(f"📢 Broadcast completed! Sent to {count} users.")

# ==================== BYPASS HANDLER (8 STAGES) ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if not await check_force_join(message.from_user.id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Join Chat", url="https://t.me/ffofcchat", style="primary"))
        builder.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify", style="success"))
        return await message.reply("<blockquote>⚠️ <b>Join Channels First!</b></blockquote>", reply_markup=builder.as_markup())

    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        return await message.reply("❌ Groups Only!", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ GROUP", url=GROUP_LINK, style="success")).as_markup())

    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░  15%", "<b>Bypassing Cloudflare... ⛈️</b>"),
        ("███░░░░░░░░░  35%", "<b>Connecting Proxy... 🛰️</b>"),
        ("█████░░░░░░░  55%", "<b>Extracting Data... 🔓</b>"),
        ("█████████░░░  75%", "<b>Generating Link... ⚡</b>"),
        ("████████████  100%", "<b>Bypass Done! ✅</b>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.6)
        try: await status_msg.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    try:
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        bypassed_url = data.get("bypassed") or data.get("url") or data.get("result")

        # Saving user for stats
        if users_db:
            await users_db.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)

        res_text = (
            "<blockquote>"
            "🏎️ <b>RAJX BYPASS BOT</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔗 <b>Original Link :</b>\n"
            f"<code>{message.text}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Bypassed Link :</b>\n"
            f"<b>{bypassed_url}</b>\n\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE}\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="‼️ BUY PAID API ‼️", url="https://t.me/visitpornhub", style="danger"))
        await status_msg.edit_text(res_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    except: await status_msg.edit_text("❌ <b>API Timeout!</b> Link invalid ya API down hai.")

# ==================== START & CALLBACKS ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if not await check_force_join(message.from_user.id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Join Chat", url="https://t.me/ffofcchat", style="primary"))
        builder.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify", style="success"))
        return await message.answer_photo(photo=WELCOME_PIC, caption="<blockquote>⚠️ Join Channels First!</blockquote>", reply_markup=builder.as_markup())

    await message.answer_photo(
        photo=WELCOME_PIC, 
        caption=f"<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nWelcome {message.from_user.first_name}!\nSend link in group to bypass instantly.</blockquote>",
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/visitpornhub", style="danger")).as_markup()
    )

@dp.callback_query(F.data == "verify")
async def verify_cb(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Join Dono Channels Pehle!", show_alert=True)

# ==================== RUN ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Live"

async def main():
    await init_db()
    Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
