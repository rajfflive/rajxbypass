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

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# --- Database Safety Connection ---
users_db = None
settings_db = None
codes_db = None

async def init_db():
    global users_db, settings_db, codes_db
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            db = client.bypass_bot
            users_db = db.users
            settings_db = db.settings
            codes_db = db.redeem_codes
            await client.server_info()
            print("✅ Database Connected!")
        except Exception as e:
            print(f"⚠️ DB Error: {e}")

# ==================== BYPASS HANDLER (7 STAGES) ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        return await message.reply("❌ <b>Only Group Work!</b>", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ JOIN GROUP", url=GROUP_LINK)).as_markup())

    if not await check_force_join(message.from_user.id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify"))
        return await message.reply("<blockquote>⚠️ <b>Join First!</b></blockquote>", reply_markup=builder.as_markup())

    # Credit Check
    u_credits = 0
    if users_db is not None:
        try:
            u_data = await users_db.find_one({"user_id": message.from_user.id})
            u_credits = u_data.get("credits", 0) if u_data else 0
        except: pass

    # --- 7 STAGES PROCESSING ---
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░░  15%", "<b>Connecting to Server... 🛰️</b>"),
        ("██░░░░░░░░░░░  30%", "<b>Checking Safety... 🛡️</b>"),
        ("████░░░░░░░░░  45%", "<b>Bypassing Cloudflare... ⛈️</b>"),
        ("██████░░░░░░░  60%", "<b>Decrypting Link... 🔓</b>"),
        ("████████░░░░░  75%", "<b>Finalizing Results... 🚀</b>"),
        ("██████████░░░  90%", "<b>Generating UI... ✨</b>"),
        ("█████████████  100%", "<b>Bypass Success! ✅</b>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.6) # Har stage 0.6s ki hogi (Total ~4-5 sec)
        try: await status_msg.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    try:
        api_url = f"https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key={API_KEY}&link={message.text.strip()}"
        response = scraper.get(api_url, timeout=30)
        data = response.json()
        res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        bypassed_url = res.get("bypassed") if isinstance(res, dict) else res

        # Inline Buttons
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔗 Share & Earn", url=f"https://t.me/share/url?url=https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}"))
        builder.row(InlineKeyboardButton(text="🎰 Daily Spin", callback_data="spin_now"))

        ui_text = (
            "<blockquote>"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏎️ <b>RAJX BYPASS BOT</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Bypassed :</b>\n"
            f"<b>{bypassed_url}</b>\n\n"
            f"💰 <b>Your Credits :</b> <code>{u_credits}</code>\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        await status_msg.edit_text(ui_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    except:
        await status_msg.edit_text("❌ <b>Error:</b> API Timeout! Variable <code>PAID_API</code> check karein.")

# ==================== SYSTEM & COMMANDS ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    if users_db is not None:
        try:
            u_id = message.from_user.id
            u_exists = await users_db.find_one({"user_id": u_id})
            if not u_exists:
                if command.args and command.args.isdigit():
                    ref_id = int(command.args)
                    await users_db.update_one({"user_id": ref_id}, {"$inc": {"credits": 2}})
                await users_db.update_one({"user_id": u_id}, {"$set": {"name": message.from_user.first_name, "credits": 0}}, upsert=True)
        except: pass
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚀 USE HERE 🚀", url=GROUP_LINK))
    await message.reply("<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nBypass ke liye mere group mein link bhejein!</blockquote>", reply_markup=builder.as_markup())

async def check_force_join(user_id):
    channels = ["ffofcchat", "rajxcheats"]
    for c in channels:
        try:
            m = await bot.get_chat_member(f"@{c}", user_id)
            if m.status in ["left", "kicked"]: return False
        except: return False
    return True

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Pehle join karein!", show_alert=True)

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
