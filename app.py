import os
import asyncio
import time
import cloudscraper
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN", "7944388044:AAEI_DMgZmczKN4YCdmjlyjSUNJvHRGbvPI")
PAID_API = "https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key=ccd271950940c3045784da88a1d3276e"

CHANNELS = ["ffofcchat", "rajxcheats"]
DEV_HANDLE = "@rajxcheats"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# ==================== RENDER LIVE FIX ====================
server = Flask(__name__)
@server.route('/')
def status(): return "✅ Rajx Bot is Live"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)

# ==================== HELPERS ====================
async def check_force_join(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

# ==================== WELCOME MESSAGE ====================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    # Colourful Emojis for "Buttons Color" feel
    builder.row(types.InlineKeyboardButton(text="🔵 JOIN UPDATES", url="https://t.me/rajxcheats"))
    builder.row(types.InlineKeyboardButton(text="🟢 ADD TO GROUP", url=f"http://t.me/{(await bot.get_me()).username}?startgroup=true"))
    builder.row(
        types.InlineKeyboardButton(text="🔴 SUPPORT", url="https://t.me/rajxcheats"),
        types.InlineKeyboardButton(text="🟡 HELP", callback_data="help")
    )

    welcome_msg = (
        f"🚀 <b>Hello {message.from_user.first_name}!</b>\n\n"
        f"Welcome to <b>RAJX BYPASS BOT</b> ✅\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"The most powerful and fastest link bypasser on Telegram.\n\n"
        f"✨ <b>Send me any link to start!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Powered By: <b>{DEV_HANDLE}</b>"
    )
    await message.answer(welcome_msg, reply_markup=builder.as_markup())

# ==================== BYPASS HANDLER ====================
@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    user_id = message.from_user.id
    link = message.text.strip()

    # 1. Force Join Check
    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        for c in CHANNELS:
            builder.row(types.InlineKeyboardButton(text=f"📢 Join @{c}", url=f"https://t.me/{c}"))
        
        return await message.answer(
            "❌ <b>Access Denied!</b>\n\nYou must join our channels to use this bot.",
            reply_markup=builder.as_markup()
        )

    # 2. Loading Animation
    status_msg = await message.answer("░░░░░░░░░░░░░  0%\n<b>ꜱᴇᴀʀᴄʜɪɴɢ ⚡</b>")
    await asyncio.sleep(0.5)
    await status_msg.edit_text("█████████░░░░  68%\n<b>ɢᴇᴛᴛɪɴɢ ʀᴇsᴜʟᴛ ⚡</b>")
    
    start_time = time.perf_counter()

    try:
        # API Call
        response = scraper.get(f"{PAID_API}&link={link}", timeout=25)
        data = response.json()
        bypassed_url = data.get("bypassed", data.get("bypassed_url", "Error in Link"))
        
        time_taken = round(time.perf_counter() - start_time, 2)

        # 3. Final Professional UI
        ui_text = (
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
            "⚙️ <b>Status :</b> Success ✅\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅"
        )
        
        await status_msg.edit_text(ui_text, disable_web_page_preview=True)

    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Error:</b> <code>{str(e)}</code>")

# ==================== MAIN START ====================
async def main():
    # Run Flask in background for Render
    Thread(target=run_server, daemon=True).start()
    
    print("🚀 Bot is Starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot Stopped.")
