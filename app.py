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

# Database Setup
m_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
db = m_client.bypass_bot
users_db = db.users
codes_db = db.redeem_codes
settings_db = db.settings

# ==================== HELPERS ====================

async def get_admins():
    data = await settings_db.find_one({"type": "admins"})
    return data["ids"] if data else [OWNER_ID]

async def get_channels():
    data = await settings_db.find_one({"type": "channels"})
    return data["list"] if data else ["ffofcchat", "rajxcheats"]

async def check_force_join(user_id):
    channels = await get_channels()
    for channel in channels:
        try:
            m = await bot.get_chat_member(f"@{channel}", user_id)
            if m.status in ["left", "kicked"]: return False
        except: return False
    return True

# ==================== BYPASS HANDLER ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="⚡ JOIN GROUP TO USE ⚡", url=GROUP_LINK))
        return await message.reply("<blockquote>❌ <b>Direct Bypass Not Allowed!</b>\n\nNiche button par click karke Group mein link bhejein.</blockquote>", reply_markup=builder.as_markup())

    user_id = message.from_user.id
    if not await check_force_join(user_id):
        channels = await get_channels()
        builder = InlineKeyboardBuilder()
        for c in channels:
            builder.row(InlineKeyboardButton(text=f"Join @{c}", url=f"https://t.me/{c}"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify"))
        return await message.reply("<blockquote>⚠️ <b>Join Channels First!</b></blockquote>", reply_markup=builder.as_markup())

    # User ke credits check karna
    user_data = await users_db.find_one({"user_id": user_id})
    current_credits = user_data.get("credits", 0) if user_data else 0

    # --- PROGRESS ANIMATION ---
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Bypassing... ⛈️</b></blockquote>")
    stages = [
        ("████░░░░░░░░░  45%", "<blockquote><b>Connecting... 🛰️</b></blockquote>"),
        ("█████████████  100%", "<blockquote><b>Completed! ✅</b></blockquote>")
    ]
    for b, t in stages:
        await asyncio.sleep(0.7)
        try: await status_msg.edit_text(f"{b}\n{t}")
        except: pass

    try:
        api_url = f"https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key={API_KEY}&link={message.text.strip()}"
        response = scraper.get(api_url, timeout=30)
        data = response.json()
        res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        bypassed_url = res.get("bypassed") if isinstance(res, dict) else res

        # Inline Buttons with Refer
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔗 Share & Earn", url=f"https://t.me/share/url?url=https://t.me/{(await bot.get_me()).username}?start={user_id}&text=Best%20Bypass%20Bot!"))
        builder.row(InlineKeyboardButton(text="🎰 Daily Spin", callback_data="spin_now"))

        ui_text = (
            "<blockquote>"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏎️ <b>RAJX BYPASS BOT</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Bypassed :</b>\n"
            f"<b>{bypassed_url}</b>\n\n"
            f"💰 <b>Your Credits :</b> <code>{current_credits}</code>\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        await status_msg.edit_text(ui_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)

    except:
        await status_msg.edit_text("❌ <b>Error:</b> API Timeout!")

# ==================== USER COMMANDS ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    # Refer Logic
    if users_db is not None:
        user_exists = await users_db.find_one({"user_id": user_id})
        if not user_exists:
            if command.args and command.args.isdigit():
                ref_id = int(command.args)
                if ref_id != user_id:
                    await users_db.update_one({"user_id": ref_id}, {"$inc": {"credits": 2}})
                    try: await bot.send_message(ref_id, "🎁 <b>+2 Credits!</b> Someone joined using your link.")
                    except: pass
            await users_db.update_one({"user_id": user_id}, {"$set": {"name": message.from_user.first_name, "credits": 0}}, upsert=True)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚀 USE HERE 🚀", url=GROUP_LINK))
    builder.row(InlineKeyboardButton(text="🎁 Refer & Earn", callback_data="refer_info"))
    await message.reply(f"<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nHello {message.from_user.first_name}!\nBypass ke liye group mein link bhejein.</blockquote>", reply_markup=builder.as_markup())

@dp.message(Command("spin"))
@dp.callback_query(F.data == "spin_now")
async def handle_spin(event):
    user_id = event.from_user.id if isinstance(event, types.Message) else event.from_user.id
    win = random.randint(1, 5)
    await users_db.update_one({"user_id": user_id}, {"$inc": {"credits": win}})
    msg = f"🎰 <b>Spin Result:</b> You won {win} credits!"
    if isinstance(event, types.Message): await event.reply(msg)
    else: await event.answer(msg, show_alert=True)

@dp.callback_query(F.data == "refer_info")
async def refer_info(cb: types.CallbackQuery):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={cb.from_user.id}"
    await cb.message.answer(f"🔗 <b>Your Referral Link:</b>\n<code>{link}</code>\n\nHar joiner par aapko <b>2 Credits</b> milenge!")
    await cb.answer()

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Pehle Join Karein!", show_alert=True)

# ==================== SYSTEM RUN ====================

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
