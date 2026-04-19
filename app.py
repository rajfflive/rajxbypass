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

# ==================== CONFIGURATION (HIDDEN) ====================
# Render ke 'Environment Variables' mein ye keys set karein
TOKEN = os.environ.get("BOT_TOKEN", "7944388044:AAEI_DMgZmczKN4YCdmjlyjSUNJvHRGbvPI")
API_KEY = os.environ.get("PAID_API_KEY", "ccd271950940c3045784da88a1d3276e")
MONGO_URL = os.environ.get("MONGO_URL") # MongoDB Atlas Link

PAID_API_BASE = f"https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key={API_KEY}&link="

# Branding & Access
ADMINS = [7944388044] # Apni numerical ID yahan confirm karein
CHANNELS = ["ffofcchat", "rajxcheats"] 
GROUP_LINK = "https://t.me/ffofcchat"
DEV_HANDLE = "@rajxcheats"
API_CREDIT = "@RAJFFLIVE"

# Database Connection
m_client = AsyncIOMotorClient(MONGO_URL)
db = m_client.bypass_bot
users_db = db.users

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# ==================== HELPERS ====================
async def check_force_join(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ["left", "kicked"]: return False
        except Exception: return False
    return True

# ==================== ADMIN COMMANDS ====================
@dp.message(Command("stats"), F.from_user.id.in_(ADMINS))
async def cmd_stats(message: types.Message):
    count = await users_db.count_documents({})
    await message.reply(f"📊 <b>Bot Statistics</b>\n\n👤 Total Users: <code>{count}</code>")

@dp.message(Command("broadcast"), F.from_user.id.in_(ADMINS))
async def cmd_broadcast(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("❌ Reply to a message to broadcast!")
    
    sent = 0
    msg = await message.reply("📢 <b>Broadcasting...</b>")
    async for user in users_db.find():
        try:
            await bot.copy_message(user['user_id'], message.chat.id, message.reply_to_message.message_id)
            sent += 1
            await asyncio.sleep(0.05)
        except: pass
    await msg.edit_text(f"✅ <b>Broadcast Finished!</b>\n\nSent to: <code>{sent}</code> users.")

# ==================== START & FEATURES ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await users_db.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"name": message.from_user.first_name, "username": message.from_user.username}},
        upsert=True
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
    builder.row(InlineKeyboardButton(text="🚀 USE HERE 🚀", url=GROUP_LINK, style="success"))
    
    await message.reply(
        f"<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n━━━━━━━━━━━━━\nHello {message.from_user.first_name}!\n\nAdd me to your group to bypass links instantly.</blockquote>", 
        reply_markup=builder.as_markup()
    )

@dp.message(Command("refer"))
async def cmd_refer(message: types.Message):
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.reply(f"🎁 <b>Refer & Earn</b>\n\nShare this link:\n<code>{ref_link}</code>")

@dp.message(Command("spin"))
async def cmd_spin(message: types.Message):
    res = random.choice(["🔥 Premium", "❌ Try Again", "✨ Lucky Pass"])
    await message.reply(f"🎰 <b>Spin Result:</b> {res}")

# ==================== BYPASS HANDLER ====================
@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
        return await message.reply("<blockquote>❌ <b>Direct Bypass Not Allowed!</b>\n\nNiche button par click karke mere Group mein link send karein.</blockquote>", reply_markup=builder.as_markup())

    user_id = message.from_user.id
    link = message.text.strip()

    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Join Group", url=GROUP_LINK, style="danger"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify", style="success"))
        return await message.reply("<blockquote>⚠️ <b>Join our channels first to use me!</b></blockquote>", reply_markup=builder.as_markup())

    # --- DETAILED 10-STAGE PROCESSING ---
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░░  10%", "<blockquote><b>Connecting to Server... 🛰️</b></blockquote>"),
        ("██░░░░░░░░░░░  25%", "<blockquote><b>Checking Link Security... 🛡️</b></blockquote>"),
        ("███░░░░░░░░░░  40%", "<blockquote><b>Bypassing Cloudflare... ⛈️</b></blockquote>"),
        ("█████░░░░░░░░  55%", "<blockquote><b>Extracting Ad-Data... 🔓</b></blockquote>"),
        ("███████░░░░░░  70%", "<blockquote><b>Bypassing Shortener... ⚡</b></blockquote>"),
        ("█████████░░░░  85%", "<blockquote><b>Getting Destination URL... 🔗</b></blockquote>"),
        ("█████████████  100%", "<blockquote><b>Success! Processing Complete ✅</b></blockquote>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.5) 
        try: await status_msg.edit_text(f"{bar}\n{text}")
        except: pass

    start_time = time.perf_counter()

    try:
        response = scraper.get(f"{PAID_API_BASE}{link}", timeout=30)
        data = response.json()

        raw_res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        bypassed_url = raw_res.get("bypassed") if isinstance(raw_res, dict) else raw_res
        
        if not bypassed_url or not str(bypassed_url).startswith("http"):
            return await status_msg.edit_text("<blockquote>❌ <b>Bypass Failed!</b>\nAPI limit reached or link unsupported.</blockquote>")

        time_taken = round(time.perf_counter() - start_time, 2)

        ui_text = (
            "<blockquote>"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏎️ <b>RAJX BYPASS BOT</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔗 <b>Original :</b>\n"
            f"<code>{link}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Bypassed :</b>\n"
            f"<b>{bypassed_url}</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🕒 <b>Time Taken :</b> <code>{time_taken}s</code>\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"⚙️ <b>FOR API :</b> {API_CREDIT}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅"
            "</blockquote>"
        )
        await status_msg.edit_text(ui_text, disable_web_page_preview=True)

    except Exception:
        await status_msg.edit_text("<blockquote>❌ <b>Request Timeout!</b>\nAPI response slow hai, thodi der mein try karein.</blockquote>")

# ==================== CALLBACKS ====================
@dp.callback_query(F.data == "verify")
async def verify_user(callback: types.CallbackQuery):
    if await check_force_join(callback.from_user.id):
        await callback.answer("✅ Verified!", show_alert=True)
        await callback.message.delete()
    else:
        await callback.answer("❌ Join Dono Channels Pehle!", show_alert=True)

# ==================== RENDER WEB SERVER ====================
server = Flask(__name__)
@server.route('/')
def status_page(): return "✅ Rajx Pro is Live"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)

async def main():
    Thread(target=run_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
