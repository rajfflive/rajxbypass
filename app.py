import os
import asyncio
import time
import cloudscraper
import random
import string
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
API_KEY = os.environ.get("PAID_API") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajxcheats"
GROUP_LINK = "https://t.me/ffofcchat"
API_CREDIT = "@RAJFFLIVE"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# Database Setup (No-Freeze)
users_db = None
codes_db = None
settings_db = None

async def init_db():
    global users_db, codes_db, settings_db
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            db = client.bypass_bot
            users_db = db.users
            codes_db = db.redeem_codes
            settings_db = db.settings
            await client.server_info()
            print("✅ Database Connected")
        except:
            print("⚠️ Database Error: Running in No-DB Mode")

# ==================== HELPERS ====================
async def check_force_join(user_id):
    channels = ["ffofcchat", "rajxcheats"]
    for c in channels:
        try:
            m = await bot.get_chat_member(f"@{c}", user_id)
            if m.status in ["left", "kicked"]: return False
        except: return False
    return True

# ==================== BYPASS HANDLER (7-STAGE) ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        builder = InlineKeyboardBuilder()
        # SUCCESS Style (Green)
        builder.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
        return await message.reply("<blockquote>❌ <b>Direct Bypass Not Allowed!</b>\nSend link in group.</blockquote>", reply_markup=builder.as_markup())

    if not await check_force_join(message.from_user.id):
        builder = InlineKeyboardBuilder()
        # Blue Color for Channel, Red for Group, Green for Verify
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Join Group", url=GROUP_LINK, style="danger"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify", style="success"))
        return await message.reply("<blockquote>⚠️ <b>Join Channels First!</b></blockquote>", reply_markup=builder.as_markup())

    u_credits = 0
    if users_db:
        u = await users_db.find_one({"user_id": message.from_user.id})
        u_credits = u.get("credits", 0) if u else 0

    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Connecting to API... ⚡</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░░  15%", "<blockquote><b>Connecting Server... 🛰️</b></blockquote>"),
        ("██░░░░░░░░░░░  30%", "<blockquote><b>Checking Safety... 🛡️</b></blockquote>"),
        ("████░░░░░░░░░  45%", "<blockquote><b>Bypassing Links... ⛈️</b></blockquote>"),
        ("██████░░░░░░░  60%", "<blockquote><b>Decrypting Data... 🔓</b></blockquote>"),
        ("████████░░░░░  75%", "<blockquote><b>Finalizing UI... ✨</b></blockquote>"),
        ("█████████████  100%", "<blockquote><b>Bypass Success! ✅</b></blockquote>")
    ]
    for b, t in stages:
        await asyncio.sleep(0.6)
        try: await status_msg.edit_text(f"{b}\n{t}")
        except: pass

    try:
        response = scraper.get(f"https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key={API_KEY}&link={message.text.strip()}", timeout=30)
        data = response.json()
        res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        bypassed_url = res.get("bypassed") if isinstance(res, dict) else res

        # Inline Buttons with Style
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔗 Share & Earn", url=f"https://t.me/share/url?url=https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}", style="primary"))
        builder.row(InlineKeyboardButton(text="🎰 Daily Spin", callback_data="spin_now", style="success"))

        ui_text = (
            "<blockquote>"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏎️ <b>RAJX BYPASS BOT</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔗 <b>Original :</b>\n"
            f"<code>{message.text}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Bypassed :</b>\n"
            f"<b>{bypassed_url}</b>\n\n"
            f"💰 <b>Your Credits :</b> <code>{u_credits}</code>\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"⚙️ <b>FOR API :</b> {API_CREDIT}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅"
            "</blockquote>"
        )
        await status_msg.edit_text(ui_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    except:
        await status_msg.edit_text("❌ <b>API Timeout!</b> Link invalid ya API key check karein.")

# ==================== ADMIN & USER SYSTEM ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    if users_db:
        u_id = message.from_user.id
        u_exists = await users_db.find_one({"user_id": u_id})
        if not u_exists:
            if command.args and command.args.isdigit():
                await users_db.update_one({"user_id": int(command.args)}, {"$inc": {"credits": 2}})
            await users_db.update_one({"user_id": u_id}, {"$set": {"name": message.from_user.first_name, "credits": 0}}, upsert=True)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Channel", url="https://t.me/rajxcheats", style="primary"))
    builder.row(InlineKeyboardButton(text="🟢 USE HERE 🟢", url=GROUP_LINK, style="success"))
    await message.reply("<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nBypass ke liye mere group mein link bhejein!</blockquote>", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "spin_now")
async def spin_now(cb: types.CallbackQuery):
    win = random.randint(1, 5)
    if users_db: await users_db.update_one({"user_id": cb.from_user.id}, {"$inc": {"credits": win}})
    await cb.answer(f"🎰 You won {win} credits!", show_alert=True)

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Join first!", show_alert=True)

# ==================== RUN ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Live"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)

async def main():
    await init_db()
    Thread(target=run_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
