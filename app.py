import os
import asyncio
import time
import cloudscraper
import random
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ==================== CONFIGURATION (ENV ONLY) ====================
TOKEN = os.environ.get("BOT_TOKEN")
# Aapne 'paid api' naam rakha hai, toh wahi yahan load hoga
PAID_API_KEY = os.environ.get("paid api") 
MONGO_URL = os.environ.get("MONGO_URL")

ADMINS = [7944388044] # Apni numerical ID yahan daalein
CHANNELS = ["ffofcchat", "rajxcheats"] 
GROUP_LINK = "https://t.me/ffofcchat"
DEV_HANDLE = "@rajxcheats"
API_CREDIT = "@RAJFFLIVE"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# Database Connection (With Safety)
users_db = None
if MONGO_URL:
    try:
        m_client = AsyncIOMotorClient(MONGO_URL)
        db = m_client.bypass_bot
        users_db = db.users
    except: pass

# ==================== HELPERS ====================
async def check_force_join(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ["left", "kicked"]: return False
        except Exception: return False
    return True

# ==================== ADMIN & STATS ====================
@dp.message(Command("stats"), F.from_user.id.in_(ADMINS))
async def cmd_stats(message: types.Message):
    if not users_db: return await message.reply("❌ DB not connected.")
    count = await users_db.count_documents({})
    await message.reply(f"📊 <b>Stats:</b> {count} users.")

@dp.message(Command("broadcast"), F.from_user.id.in_(ADMINS))
async def cmd_broadcast(message: types.Message):
    if not message.reply_to_message or not users_db: return
    async for user in users_db.find():
        try: await bot.copy_message(user['user_id'], message.chat.id, message.reply_to_message.message_id)
        except: pass
    await message.reply("✅ Broadcast Done!")

# ==================== BYPASS HANDLER (LONGER PROCESS) ====================
@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK))
        return await message.reply("<blockquote>❌ <b>Only Groups Allowed!</b></blockquote>", reply_markup=builder.as_markup())

    if not await check_force_join(message.from_user.id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Channel", url="https://t.me/rajxcheats"))
        builder.row(InlineKeyboardButton(text="🚀 Verify", callback_data="verify"))
        return await message.reply("<blockquote>⚠️ <b>Join Channel First!</b></blockquote>", reply_markup=builder.as_markup())

    # --- ULTRA LONG PROCESSING (10 STAGES) ---
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░░  10%", "<blockquote><b>Connecting to Proxy... 🌐</b></blockquote>"),
        ("██░░░░░░░░░░░  20%", "<blockquote><b>Checking URL Safety... 🛡️</b></blockquote>"),
        ("███░░░░░░░░░░  30%", "<blockquote><b>Bypassing Cloudflare... ⛈️</b></blockquote>"),
        ("████░░░░░░░░░  40%", "<blockquote><b>Solving Captcha... 🤖</b></blockquote>"),
        ("██████░░░░░░░  55%", "<blockquote><b>Extracting API Data... 🔓</b></blockquote>"),
        ("███████░░░░░░  65%", "<blockquote><b>Scraping Final Link... 🔎</b></blockquote>"),
        ("████████░░░░░  75%", "<blockquote><b>Removing Redirects... ⚡</b></blockquote>"),
        ("██████████░░░  85%", "<blockquote><b>Verifying Result... ✅</b></blockquote>"),
        ("████████████░  95%", "<blockquote><b>Generating UI... 🚀</b></blockquote>"),
        ("█████████████  100%", "<blockquote><b>Done! Sending Result... ✨</b></blockquote>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.5) # Total ~5-6 seconds delay
        try: await status_msg.edit_text(f"{bar}\n{text}")
        except: pass

    start_time = time.perf_counter()

    try:
        # API Call using Hidden Env Key
        api_url = f"https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key={PAID_API_KEY}&link={message.text.strip()}"
        response = scraper.get(api_url, timeout=30)
        data = response.json()

        res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        bypassed_url = res.get("bypassed") if isinstance(res, dict) else res

        if not bypassed_url:
            return await status_msg.edit_text("❌ <b>Bypass Failed!</b>")

        time_taken = round(time.perf_counter() - start_time, 2)

        ui_text = (
            "<blockquote>"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏎️ <b>RAJX BYPASS BOT</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Bypassed :</b>\n"
            f"<b>{bypassed_url}</b>\n\n"
            "⚙️ <b>FOR API :</b> {API_CREDIT}\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅"
            "</blockquote>"
        )
        await status_msg.edit_text(ui_text, disable_web_page_preview=True)
    except:
        await status_msg.edit_text("❌ <b>Timeout Error!</b>")

# ==================== START & SYSTEM ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if users_db is not None:
        await users_db.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚀 USE HERE 🚀", url=GROUP_LINK))
    await message.reply("<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nAdd me to your group to bypass!</blockquote>", reply_markup=builder.as_markup())

# Flask Server for Render
server = Flask(__name__)
@server.route('/')
def st(): return "Live"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)

async def main():
    Thread(target=run_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
