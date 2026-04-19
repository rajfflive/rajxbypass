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
from aiogram.types import InlineKeyboardButton

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN", "7944388044:AAEI_DMgZmczKN4YCdmjlyjSUNJvHRGbvPI")
PAID_API = "https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key=ccd271950940c3045784da88a1d3276e"

CHANNELS = ["ffofcchat", "rajxcheats"] # Channel & Group
DEV_HANDLE = "@rajxcheats"
API_CREDIT = "@RAJFFLIVE"

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
    # Button Style matching your screenshot
    builder.row(InlineKeyboardButton(text=" Join Updates", url="https://t.me/rajxcheats"))
    builder.row(InlineKeyboardButton(text=" Main Group", url="https://t.me/ffofcchat"))
    builder.row(InlineKeyboardButton(text=" Support", url=f"https://t.me/rajfflive"))

    welcome_text = (
        f"🚀 <b>Hello {message.from_user.first_name}!</b>\n\n"
        f"Welcome to <b>RAJX BYPASS BOT</b> ✅\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"I can bypass almost any shortlink instantly.\n\n"
        f"✨ <b>Send me a link to start!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Powered By: <b>{DEV_HANDLE}</b>"
    )
    await message.reply(welcome_text, reply_markup=builder.as_markup())

# ==================== BYPASS HANDLER ====================
@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    user_id = message.from_user.id
    link = message.text.strip()

    # 1. Force Join & Verify Button
    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats"))
        builder.row(InlineKeyboardButton(text="💬 Join Group", url="https://t.me/ffofcchat"))
        builder.row(InlineKeyboardButton(text="✅ Verify Membership", callback_data="verify"))
        
        return await message.reply(
            "❌ <b>Access Denied!</b>\n\nYou must join our Channel and Group to use this bot.",
            reply_markup=builder.as_markup()
        )

    # 2. Loading Animation
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<b>ꜱᴇᴀʀᴄʜɪɴɢ ⚡</b>")
    await asyncio.sleep(0.4)
    await status_msg.edit_text("█████████░░░░  68%\n<b>ɢᴇᴛᴛɪɴɢ ʀᴇsᴜʟᴛ ⚡</b>")
    
    start_time = time.perf_counter()

    try:
        # API Call (Fixed Extraction)
        response = scraper.get(f"{PAID_API}&link={link}", timeout=30)
        data = response.json()
        
        # Fixing the 'Bypass Error' by checking keys properly
        bypassed_url = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        
        if not bypassed_url:
            return await status_msg.edit_text("❌ <b>Bypass Failed!</b>\nLink not supported or API limit reached.")

        time_taken = round(time.perf_counter() - start_time, 2)

        # 3. Final Professional UI (Line Separated)
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
            f"⚙️ <b>FOR API :</b> {API_CREDIT}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅"
        )
        
        await status_msg.edit_text(ui_text, disable_web_page_preview=True)

    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Error:</b> <code>{str(e)[:100]}</code>")

# ==================== VERIFY CALLBACK ====================
@dp.callback_query(F.data == "verify")
async def verify_user(callback: types.CallbackQuery):
    if await check_force_join(callback.from_user.id):
        await callback.answer("✅ Verified! You can now send links.", show_alert=True)
        await callback.message.delete()
    else:
        await callback.answer("❌ You still haven't joined both channels!", show_alert=True)

# ==================== MAIN START ====================
async def main():
    Thread(target=run_server, daemon=True).start()
    print("🚀 Bot Started with @RAJFFLIVE Credit!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot Stopped.")
