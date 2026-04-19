import os
import asyncio
import time
import cloudscraper
import json
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton

# ==================== CONFIGURATION ====================
# TOKEN yahan se replace karein agar environment variable use nahi kar rahe
TOKEN = os.environ.get("BOT_TOKEN", "7944388044:AAEI_DMgZmczKN4YCdmjlyjSUNJvHRGbvPI")
PAID_API = "https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key=ccd271950940c3045784da88a1d3276e"

CHANNELS = ["ffofcchat", "rajxcheats"] 
GROUP_LINK = "https://t.me/ffofcchat"
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
            if member.status in ["left", "kicked"]: return False
        except Exception: return False
    return True

# ==================== BYPASS HANDLER ====================
@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    # Personal Chat Redirect (Group Only Mode)
    if message.chat.type == "private":
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🟢 USE HERE 🟢", url=GROUP_LINK))
        return await message.reply(
            "<blockquote>❌ <b>Direct Bypass Not Allowed!</b>\n\nNiche diye gaye button par click karke mere Group mein link send karein.</blockquote>",
            reply_markup=builder.as_markup()
        )

    user_id = message.from_user.id
    link = message.text.strip()

    # Force Join Check
    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats"))
        builder.row(InlineKeyboardButton(text="💬 Join Group", url=GROUP_LINK))
        builder.row(InlineKeyboardButton(text="🔵 Verify ✅", callback_data="verify"))
        return await message.reply("<blockquote>⚠️ <b>Join our channels first to use me!</b></blockquote>", reply_markup=builder.as_markup())

    # --- PROGRESS ANIMATION (More Detailed) ---
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Connecting... ⚡</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░░  10%", "<blockquote><b>Fetching API Data... 🛰️</b></blockquote>"),
        ("████░░░░░░░░░  45%", "<blockquote><b>Bypassing Restrictions... ⛈️</b></blockquote>"),
        ("█████████████  100%", "<blockquote><b>Bypass Success! ✅</b></blockquote>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.4)
        try: await status_msg.edit_text(f"{bar}\n{text}")
        except: pass

    start_time = time.perf_counter()

    try:
        # API CALL WITH 30s TIMEOUT
        response = scraper.get(f"{PAID_API}&link={link}", timeout=30)
        data = response.json()

        # Clean Link Extraction (Loda Lassun Fix)
        bypassed_url = None
        if isinstance(data, dict):
            # Checking all possible keys for the link
            raw_res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
            # Handle nested dictionary if any
            bypassed_url = raw_res.get("bypassed") if isinstance(raw_res, dict) else raw_res
        
        if not bypassed_url or not str(bypassed_url).startswith("http"):
            return await status_msg.edit_text("<blockquote>❌ <b>Bypass Failed!</b>\nLink not supported or API limit exceeded.</blockquote>")

        time_taken = round(time.perf_counter() - start_time, 2)

        # --- FINAL PREMIUM UI ---
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
        await status_msg.edit_text("<blockquote>❌ <b>Request Timeout!</b>\nAPI response nahi de rahi. 10 sec baad fir try karein.</blockquote>")

# ==================== CALLBACKS ====================
@dp.callback_query(F.data == "verify")
async def verify_user(callback: types.CallbackQuery):
    if await check_force_join(callback.from_user.id):
        await callback.answer("✅ Verified! You can bypass now.", show_alert=True)
        await callback.message.delete()
    else:
        await callback.answer("❌ Join Dono Channels Pehle!", show_alert=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Channel", url="https://t.me/rajxcheats"))
    builder.row(InlineKeyboardButton(text="🟢 USE HERE 🟢", url=GROUP_LINK))
    
    await message.reply(
        f"<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n━━━━━━━━━━━━━\nHello! I'm the fastest link bypasser. Add me to your group to use me!</blockquote>", 
        reply_markup=builder.as_markup()
    )

# ==================== RUN BOT ====================
async def main():
    Thread(target=run_server, daemon=True).start()
    print(f"🚀 Bot Started Successfully for {DEV_HANDLE}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except: pass
