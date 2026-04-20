import os
import asyncio
import cloudscraper
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
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
CHANNELS = ["rajxcheats", "ffofcchat"] 
GROUP_LINK = "https://t.me/ffofcchat"
WELCOME_PIC = "https://i.ibb.co/8L91y1CP/6ee42acc1338.jpg"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# --- Database ---
users_db = None
async def init_db():
    global users_db
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            users_db = client.bypass_bot.users
            await client.server_info()
            print("✅ Database Connected")
        except: print("⚠️ DB Connection Failed")

# ==================== HELPERS ====================

async def check_force_join(user_id):
    if user_id == OWNER_ID: return True
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ["left", "kicked"]: return False
        except: return False
    return True

# ==================== BYPASS HANDLER (CLEAN & GROUP ONLY) ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    # 1. Force Join Check
    if not await check_force_join(message.from_user.id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Join Chat", url="https://t.me/ffofcchat", style="primary"))
        builder.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify", style="success"))
        return await message.reply("<blockquote>⚠️ <b>Join Channels First!</b></blockquote>", reply_markup=builder.as_markup())

    # 2. Only Group Mode (Strict On)
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        builder = InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ JOIN GROUP ⚡", url=GROUP_LINK, style="success"))
        return await message.reply("<blockquote>❌ <b>Direct Bypass Not Allowed!</b>\n\nNiche button par click karke group mein link bhejein.</blockquote>", reply_markup=builder.as_markup())

    # 3. Processing Stages (8 Stages)
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░  15%", "<b>Bypassing Cloudflare... ⛈️</b>"),
        ("███░░░░░░░░░  30%", "<b>Connecting Proxy... 🛰️</b>"),
        ("█████░░░░░░░  45%", "<b>Solving Captcha... 🤖</b>"),
        ("███████░░░░░  60%", "<b>Extracting Data... 🔓</b>"),
        ("█████████░░░  75%", "<b>Generating Link... ⚡</b>"),
        ("███████████░  90%", "<b>Finalizing... ✨</b>"),
        ("████████████  100%", "<b>Bypass Successful! ✅</b>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.6)
        try: await status_msg.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    try:
        # API Call
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        
        # --- CLEAN RESPONSE LOGIC ---
        # Yahan se kachra (JSON) saaf kiya gaya hai
        bypassed_url = data.get("bypassed") or data.get("url") or data.get("result")
        
        if users_db:
            await users_db.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)

        # IMAGE JESI CLEAN UI
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
        builder.row(InlineKeyboardButton(text="‼️ 𝗕𝗨𝗬 𝗔𝗣𝗜 ‼️", url="https://t.me/visitpornhub", style="danger"))
        
        await status_msg.edit_text(res_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
        
    except Exception:
        await status_msg.edit_text("❌ <b>API Timeout!</b> Check URL or Key.")

# ==================== OWNER COMMANDS ====================

@dp.message(Command("stats"), F.from_user.id == OWNER_ID)
async def cmd_stats(message: types.Message):
    count = await users_db.count_documents({}) if users_db else "N/A"
    await message.reply(f"📊 <b>Total Users:</b> <code>{count}</code>")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer_photo(
        photo=WELCOME_PIC, 
        caption=f"<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nWelcome {message.from_user.first_name}!\nSend link in group to bypass instantly.</blockquote>",
        reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="‼️ 𝗕𝗨𝗬 𝗔𝗣𝗜 ‼️", url="https://t.me/visitpornhub", style="danger")).as_markup()
    )

@dp.callback_query(F.data == "verify")
async def verify_cb(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Pehle Join Karo!", show_alert=True)

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
