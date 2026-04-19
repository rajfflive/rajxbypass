import os
import asyncio
import time
import cloudscraper
import random
import string
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN")
# Render/VPS pe variable name 'paid_api' rakhein
API_KEY = os.environ.get("paid_api") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 # Nayi Owner ID Update Kar di ✅
DEV_HANDLE = "@rajxcheats"
GROUP_LINK = "https://t.me/ffofcchat"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# Database Setup
m_client = AsyncIOMotorClient(MONGO_URL)
db = m_client.bypass_bot
users_db = db.users
codes_db = db.redeem_codes
settings_db = db.settings

# ==================== HELPERS ====================

async def get_admin_list():
    data = await settings_db.find_one({"type": "admins"})
    return data["ids"] if data else [OWNER_ID]

async def get_channel_list():
    data = await settings_db.find_one({"type": "channels"})
    return data["list"] if data else ["ffofcchat", "rajxcheats"]

async def check_force_join(user_id):
    channels = await get_channel_list()
    for channel in channels:
        try:
            m = await bot.get_chat_member(f"@{channel}", user_id)
            if m.status in ["left", "kicked"]: return False
        except: return False
    return True

# ==================== ADMIN & OWNER PANEL ====================

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    admins = await get_admin_list()
    if message.from_user.id not in admins: return

    text = (
        "👑 <b>ADMIN CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Commands:</b>\n"
        "• /broadcast - Reply to msg\n"
        "• /stats - User count\n"
        "• /gen <code>(amt)</code> - Create Promo\n\n"
        "<b>Owner Only (8154922225):</b>\n"
        "• /add_admin <code>(ID)</code>\n"
        "• /rm_admin <code>(ID)</code>\n"
        "• /add_chan <code>(user)</code>\n"
        "• /rm_chan <code>(user)</code>"
    )
    await message.reply(text)

@dp.message(Command("add_admin"), F.from_user.id == OWNER_ID)
async def add_admin(message: types.Message, command: CommandObject):
    if not command.args: return
    await settings_db.update_one({"type": "admins"}, {"$addToSet": {"ids": int(command.args)}}, upsert=True)
    await message.reply(f"✅ User {command.args} added as Admin.")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    admins = await get_admin_list()
    if message.from_user.id not in admins: return
    count = await users_db.count_documents({})
    await message.reply(f"📊 <b>Total Users:</b> <code>{count}</code>")

# ==================== USER FEATURES (REFER/SPIN) ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    
    # Refer Logic (2 Credits per Refer)
    user_exists = await users_db.find_one({"user_id": user_id})
    if not user_exists and command.args:
        referrer_id = int(command.args)
        if referrer_id != user_id:
            await users_db.update_one({"user_id": referrer_id}, {"$inc": {"credits": 2}})
            try: await bot.send_message(referrer_id, "🎁 New Refer! <b>2 Credits</b> added.")
            except: pass

    await users_db.update_one(
        {"user_id": user_id},
        {"$set": {"name": message.from_user.first_name}, "$setOnInsert": {"credits": 0}},
        upsert=True
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚀 USE HERE 🚀", url=GROUP_LINK))
    await message.reply(f"<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nHello {message.from_user.first_name}!\nBypass karne ke liye group mein link bhejein.</blockquote>", reply_markup=builder.as_markup())

@dp.message(Command("spin"))
async def cmd_spin(message: types.Message):
    # Daily Spin (1 to 5 credits)
    win = random.randint(1, 5)
    await users_db.update_one({"user_id": message.from_user.id}, {"$inc": {"credits": win}})
    await message.reply(f"🎰 <b>Spin Result:</b> You won {win} credits!")

@dp.message(Command("refer"))
async def cmd_refer(message: types.Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    await message.reply(f"🔗 <b>Your Link:</b> <code>{link}</code>\n\nInvite and get <b>2 Credits</b> per join!")

# ==================== BYPASS HANDLER ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        return await message.reply("❌ Groups only!", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ GROUP", url=GROUP_LINK)).as_markup())

    if not await check_force_join(message.from_user.id):
        channels = await get_channel_list()
        builder = InlineKeyboardBuilder()
        for c in channels: builder.row(InlineKeyboardButton(text=f"Join @{c}", url=f"https://t.me/{c}"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify"))
        return await message.reply("<blockquote>⚠️ Join channels first!</blockquote>", reply_markup=builder.as_markup())

    # --- LONG PROCESS ANIMATION ---
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    
    stages = [
        ("████░░░░░░░░░  40%", "<blockquote><b>Connecting to API... ⛈️</b></blockquote>"),
        ("██████████░░░  85%", "<blockquote><b>Bypassing Link... ⚡</b></blockquote>"),
        ("█████████████  100%", "<blockquote><b>Success! ✅</b></blockquote>")
    ]
    for b, t in stages:
        await asyncio.sleep(0.8)
        try: await status_msg.edit_text(f"{b}\n{t}")
        except: pass

    try:
        api_url = f"https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key={API_KEY}&link={message.text.strip()}"
        response = scraper.get(api_url, timeout=30)
        data = response.json()
        res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        bypassed_url = res.get("bypassed") if isinstance(res, dict) else res

        await status_msg.edit_text(
            f"<blockquote>━━━━━━━━━━━━━━━━━━━━\n🏎️ <b>RAJX BYPASS BOT</b> ⚡\n━━━━━━━━━━━━━━━━━━━━\n\n🚀 <b>Bypassed :</b>\n<b>{bypassed_url}</b>\n\n👤 <b>User :</b> {message.from_user.first_name}\n👑 <b>Owner :</b> {DEV_HANDLE} ✅\n━━━━━━━━━━━━━━━━━━━━</blockquote>",
            disable_web_page_preview=True
        )
    except: await status_msg.edit_text("❌ Request Timeout!")

# ==================== RUNNING SYSTEM ====================

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Join both first!", show_alert=True)

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
