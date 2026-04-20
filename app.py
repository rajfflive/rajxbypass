import os
import asyncio
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

# YAHAN DHYAN DE: 'NEW_API_URL' variable Render mein set karna hoga
# Example: https://api.example.com/bypass?key=123&link=
NEW_API_URL = os.environ.get("NEW_API_URL") 

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajxcheats"
GROUP_LINK = "https://t.me/ffofcchat"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# Database Setup
users_db = None
if os.environ.get("MONGO_URL"):
    try:
        client = AsyncIOMotorClient(os.environ.get("MONGO_URL"), serverSelectionTimeoutMS=5000)
        users_db = client.bypass_bot.users
    except: pass

# ==================== BYPASS HANDLER ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        builder = InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ USE IN GROUP", url=GROUP_LINK, style="success"))
        return await message.reply("<blockquote>❌ <b>Groups Only!</b></blockquote>", reply_markup=builder.as_markup())

    link = message.text.strip()
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    
    # 7-Stage Process
    stages = [
        ("██░░░░░░░░░░░  20%", "<b>Connecting Server... 🛰️</b>"),
        ("████░░░░░░░░░  40%", "<b>Bypassing... ⛈️</b>"),
        ("██████░░░░░░░  60%", "<b>Decrypting... 🔓</b>"),
        ("█████████████  100%", "<b>Success! ✅</b>")
    ]
    for b, t in stages:
        await asyncio.sleep(0.6)
        try: await status_msg.edit_text(f"{b}\n<blockquote>{t}</blockquote>")
        except: pass

    try:
        # NEW API CALL LOGIC
        # Variable se URL uthayega aur aage link jod dega
        full_api_path = f"{NEW_API_URL}{link}"
        response = scraper.get(full_api_path, timeout=30)
        data = response.json()

        # Link Extraction (Har format ke liye)
        bypassed_url = data.get("bypassed") or data.get("url") or data.get("result")
        if isinstance(bypassed_url, dict):
            bypassed_url = bypassed_url.get("url") or bypassed_url.get("bypassed")

        if not bypassed_url:
            return await status_msg.edit_text(f"❌ <b>API Error!</b>\nResponse: <code>{data}</code>")

        # UI & Buttons
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔗 Share & Earn", url=f"https://t.me/share/url?url=https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}", style="primary"))
        builder.row(InlineKeyboardButton(text="🎰 Daily Spin", callback_data="spin_now", style="success"))

        ui_text = (
            "<blockquote>"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏎️ <b>RAJX BYPASS BOT</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Bypassed :</b>\n"
            f"<b>{bypassed_url}</b>\n\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        await status_msg.edit_text(ui_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)

    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Error:</b> <code>{str(e)}</code>")

# ==================== SYSTEM RUN ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder().row(InlineKeyboardButton(text="🟢 JOIN GROUP", url=GROUP_LINK, style="success"))
    await message.reply("<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\nActive in Group!</blockquote>", reply_markup=builder.as_markup())

server = Flask(__name__)
@server.route('/')
def st(): return "Live"

async def main():
    Thread(target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
