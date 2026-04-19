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
PAID_API = "https://trycloudflare.com"

CHANNELS = ["ffofcchat", "rajxcheats"] 
GROUP_LINK = "https://t.me"
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
    # --- PRIVATE CHAT REDIRECT ---
    if message.chat.type == "private":
        builder = InlineKeyboardBuilder()
        # SUCCESS Style: Green Color
        builder.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
        return await message.reply(
            "<blockquote>❌ <b>Main Personal Chat mein link bypass nahi karta!</b>\n\nBypass karne ke liye niche diye gaye button par click karke mere Group mein aayein.</blockquote>",
            reply_markup=builder.as_markup()
        )

    user_id = message.from_user.id
    link = message.text.strip()

    # Force Join Check
    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="Join Channel", url="https://t.me"))
        builder.row(InlineKeyboardButton(text="Join Group", url=GROUP_LINK))
        # PRIMARY Style: Blue Color
        builder.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify", style="primary"))
        return await message.reply("<blockquote>⚠️ <b>Join our channels first to use me!</b></blockquote>", reply_markup=builder.as_markup())

    # --- DETAILED PROGRESS ---
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Connecting... ⏳</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░░  10%", "<blockquote><b>Fetching Server... 🛰️</b></blockquote>"),
        ("████░░░░░░░░░  45%", "<blockquote><b>Bypassing Cloudflare... ⛈️</b></blockquote>"),
        ("████████░░░░░  85%", "<blockquote><b>Finalizing Results... 🚀</b></blockquote>"),
        ("█████████████  100%", "<blockquote><b>Success! ✅</b></blockquote>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.3)
        try:
            await status_msg.edit_text(f"{bar}\n{text}")
        except: pass

    start_time = time.perf_counter()

    try:
        # --- TIMEOUT LOGIC (30 SECONDS) ---
        response = scraper.get(f"{PAID_API}&link={link}", timeout=30)
        data = response.json()
        
        raw_res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        bypassed_url = raw_res.get("bypassed") if isinstance(raw_res, dict) else raw_res

        if not bypassed_url:
            return await status_msg.edit_text("<blockquote>❌ <b>API Error:</b> Link not supported!</blockquote>")

        time_taken = round(time.perf_counter() - start_time, 2)

        # --- FINAL CLEAN UI ---
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

    except Exception:
        await status_msg.edit_text("<blockquote>❌ <b>Request Timeout!</b>\nAPI response nahi de rahi, 10-15 sec baad fir try karein.</blockquote>")

# ==================== OTHER HANDLERS ====================
@dp.callback_query(F.data == "verify")
async def verify_user(callback: types.CallbackQuery):
    if await check_force_join(callback.from_user.id):
        await callback.answer("✅ Verified!", show_alert=True)
        await callback.message.delete()
    else:
        await callback.answer("❌ Join both first!", show_alert=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Join Channel", url="https://t.me"))
    # SUCCESS Style: Green Color
    builder.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
    await message.reply(
        f"🏎️ <b>RAJX BYPASS BOT</b>\n━━━━━━━━━━━━━\nAdd me to group to use me!", 
        reply_markup=builder.as_markup()
    )

async def main():
    Thread(target=run_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
