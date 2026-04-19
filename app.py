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
API_KEY = os.environ.get("PAID_API") # Render pe 'PAID_API' naam rkhna
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajxcheats"
GROUP_LINK = "https://t.me/ffofcchat"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# Database Setup (Safety Locked)
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
            print("⚠️ DB Error: Running without Database")

# ==================== HELPERS ====================
async def get_admins():
    if not settings_db: return [OWNER_ID]
    try:
        data = await settings_db.find_one({"type": "admins"})
        return data["ids"] if data else [OWNER_ID]
    except: return [OWNER_ID]

async def check_force_join(user_id):
    channels = ["ffofcchat", "rajxcheats"]
    for c in channels:
        try:
            m = await bot.get_chat_member(f"@{c}", user_id)
            if m.status in ["left", "kicked"]: return False
        except: return False
    return True

# ==================== ADMIN & OWNER TOOLS ====================

@dp.message(Command("admin"))
async def admin_menu(message: types.Message):
    admins = await get_admins()
    if message.from_user.id not in admins: return
    text = (
        "👑 <b>ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "• /broadcast - Reply to msg\n"
        "• /stats - User Count\n"
        "• /gen <code>(amt)</code> - Create Code\n\n"
        "<b>Owner Tools:</b>\n"
        "• /add_admin <code>(ID)</code>\n"
        "• /add_chan <code>(user)</code>"
    )
    await message.reply(text)

@dp.message(Command("gen"))
async def gen_code(message: types.Message, command: CommandObject):
    admins = await get_admins()
    if message.from_user.id not in admins or not codes_db: return
    if not command.args: return
    code = "RAJX-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    await codes_db.insert_one({"code": code, "credits": int(command.args), "used": False})
    await message.reply(f"🎁 <b>Code:</b> <code>{code}</code>\n<b>Amt:</b> {command.args}")

# ==================== BYPASS HANDLER (7 STAGES) ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        return await message.reply("❌ Groups only!", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ GROUP", url=GROUP_LINK)).as_markup())

    if not await check_force_join(message.from_user.id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify"))
        return await message.reply("<blockquote>⚠️ Join first!</blockquote>", reply_markup=builder.as_markup())

    # Credit Check
    u_credits = 0
    if users_db:
        u = await users_db.find_one({"user_id": message.from_user.id})
        u_credits = u.get("credits", 0) if u else 0

    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    
    stages = [
        ("██░░░░░░░░░░░  20%", "<b>Connecting... 🛰️</b>"),
        ("████░░░░░░░░░  45%", "<b>Bypassing... ⛈️</b>"),
        ("████████░░░░░  75%", "<b>Decrypting... 🔓</b>"),
        ("█████████████  100%", "<b>Success! ✅</b>")
    ]
    for b, t in stages:
        await asyncio.sleep(0.7)
        try: await status_msg.edit_text(f"{b}\n<blockquote>{t}</blockquote>")
        except: pass

    try:
        response = scraper.get(f"https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key={API_KEY}&link={message.text.strip()}", timeout=30)
        data = response.json()
        res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        bypassed_url = res.get("bypassed") if isinstance(res, dict) else res

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
            f"💰 <b>Credits :</b> <code>{u_credits}</code>\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        await status_msg.edit_text(ui_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    except: await status_msg.edit_text("❌ API Timeout!")

# ==================== USER SYSTEM ====================

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
    builder.row(InlineKeyboardButton(text="🚀 USE HERE 🚀", url=GROUP_LINK))
    await message.reply("<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nAdd me to group to bypass!</blockquote>", reply_markup=builder.as_markup())

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
