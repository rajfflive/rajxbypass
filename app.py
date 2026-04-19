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
# Render pe key ka naam 'PAID_API' rakhna
API_KEY = os.environ.get("PAID_API") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajxcheats"
GROUP_LINK = "https://t.me/ffofcchat"
API_CREDIT = "@RAJFFLIVE"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# Database Setup
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
            print("✅ Database Connected")
        except Exception as e:
            print(f"⚠️ DB Error: {e}")

# ==================== ADMIN & OWNER LOGIC ====================

async def get_admins():
    if not settings_db: return [OWNER_ID]
    data = await settings_db.find_one({"type": "admins"})
    return data["ids"] if data else [OWNER_ID]

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    admins = await get_admins()
    if message.from_user.id not in admins: return
    
    text = (
        "👑 <b>ADMIN CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <b>Commands:</b>\n"
        "• /stats - User Count\n"
        "• /broadcast - Reply to msg\n"
        "• /gen <code>(amt)</code> - Create Promo\n\n"
        "💎 <b>Owner Tools:</b>\n"
        "• /add_admin <code>(ID)</code>\n"
        "• /rm_admin <code>(ID)</code>\n"
        "• /add_chan <code>(user)</code>"
    )
    await message.reply(text)

@dp.message(Command("gen"))
async def gen_code(message: types.Message, command: CommandObject):
    admins = await get_admins()
    if message.from_user.id not in admins: return
    if not command.args or not codes_db: return
    
    code = "RAJX-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    await codes_db.insert_one({"code": code, "credits": int(command.args), "used": False})
    await message.reply(f"🎁 <b>Promo Created:</b>\n<code>{code}</code>\n<b>Value:</b> {command.args} Credits")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    admins = await get_admins()
    if message.from_user.id not in admins or not users_db: return
    count = await users_db.count_documents({})
    await message.reply(f"📊 <b>Total Users:</b> <code>{count}</code>")

# ==================== BYPASS HANDLER (7-STAGE) ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
        return await message.reply("<blockquote>❌ <b>Private Bypass Disabled!</b>\nSend link in group.</blockquote>", reply_markup=builder.as_markup())

    # Force Join Check
    for c in ["ffofcchat", "rajxcheats"]:
        try:
            m = await bot.get_chat_member(f"@{c}", message.from_user.id)
            if m.status in ["left", "kicked"]:
                builder = InlineKeyboardBuilder()
                builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
                builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify", style="success"))
                return await message.reply("<blockquote>⚠️ <b>Join Channels First!</b></blockquote>", reply_markup=builder.as_markup())
        except: pass

    # Credits Check
    u_credits = 0
    if users_db:
        u = await users_db.find_one({"user_id": message.from_user.id})
        u_credits = u.get("credits", 0) if u else 0

    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Connecting to API... ⚡</b></blockquote>")
    
    stages = [
        ("██░░░░░░░░░░░  20%", "<blockquote><b>Connecting Server... 🛰️</b></blockquote>"),
        ("████░░░░░░░░░  45%", "<blockquote><b>Bypassing Links... ⛈️</b></blockquote>"),
        ("████████░░░░░  75%", "<blockquote><b>Decrypting Data... 🔓</b></blockquote>"),
        ("█████████████  100%", "<blockquote><b>Success! ✅</b></blockquote>")
    ]
    for b, t in stages:
        await asyncio.sleep(0.7)
        try: await status_msg.edit_text(f"{b}\n{t}")
        except: pass

    try:
        # Final API Request
        api_url = f"https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key={API_KEY}&link={message.text.strip()}"
        response = scraper.get(api_url, timeout=30)
        data = response.json()
        res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        bypassed_url = res.get("bypassed") if isinstance(res, dict) else res

        if not bypassed_url:
            return await status_msg.edit_text("❌ <b>Bypass Failed!</b> API Key galat hai ya link unsupported hai.")

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
            f"💰 <b>Credits :</b> <code>{u_credits}</code>\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"⚙️ <b>FOR API :</b> {API_CREDIT}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅"
            "</blockquote>"
        )
        await status_msg.edit_text(ui_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    except Exception:
        await status_msg.edit_text("❌ <b>API Invalid!</b> Render pe <code>PAID_API</code> check karein.")

# ==================== SYSTEM & REDEEM ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    if users_db:
        # Refer logic (2 credits)
        exists = await users_db.find_one({"user_id": message.from_user.id})
        if not exists:
            if command.args and command.args.isdigit():
                await users_db.update_one({"user_id": int(command.args)}, {"$inc": {"credits": 2}})
            await users_db.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name, "credits": 0}}, upsert=True)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Channel", url="https://t.me/rajxcheats", style="primary"))
    builder.row(InlineKeyboardButton(text="🚀 USE HERE 🚀", url=GROUP_LINK, style="success"))
    await message.reply("<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nBypass karne ke liye group join karein!</blockquote>", reply_markup=builder.as_markup())

@dp.message(Command("redeem"))
async def cmd_redeem(message: types.Message, command: CommandObject):
    if not command.args or not codes_db: return
    data = await codes_db.find_one({"code": command.args, "used": False})
    if data:
        await users_db.update_one({"user_id": message.from_user.id}, {"$inc": {"credits": data['credits']}})
        await codes_db.update_one({"code": command.args}, {"$set": {"used": True}})
        await message.reply(f"✅ Success! {data['credits']} Credits added.")
    else: await message.reply("❌ Code invalid ya used hai.")

@dp.callback_query(F.data == "spin_now")
async def spin_now(cb: types.CallbackQuery):
    win = random.randint(1, 5)
    if users_db: await users_db.update_one({"user_id": cb.from_user.id}, {"$inc": {"credits": win}})
    await cb.answer(f"🎰 You won {win} credits!", show_alert=True)

# ==================== SERVER RUN ====================
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
