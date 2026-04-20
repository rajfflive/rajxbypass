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
API_URL = os.environ.get("NEW_API_URL") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajxcheats"
CHANNELS = ["rajxcheats", "ffofcchat"] 
GROUP_LINK = "https://t.me/ffofcchat"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# Database Setup
users_db = None
if MONGO_URL:
    try:
        client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        users_db = client.bypass_bot.users
    except: pass

# ==================== HELPERS ====================

async def check_force_join(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ["left", "kicked"]: return False
        except: return False
    return True

async def get_user_credits(user_id):
    if users_db is not None:
        user = await users_db.find_one({"user_id": user_id})
        return user.get("credits", 0) if user else 0
    return 0

# ==================== BYPASS HANDLER (8 STAGES) ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    user_id = message.from_user.id

    # Force Join Check
    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Join Chat", url="https://t.me/ffofcchat", style="primary"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify", style="success"))
        return await message.reply("<blockquote>⚠️ <b>Join our channels first to bypass!</b></blockquote>", reply_markup=builder.as_markup())

    if message.chat.type == "private":
        return await message.reply("❌ <b>Groups Only!</b>", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ USE IN GROUP", url=GROUP_LINK, style="success")).as_markup())

    # --- EXTENDED 8-STAGE PROGRESSION ---
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing Engine... ⚙️</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░░  12%", "<blockquote><b>Connecting to Proxy... 🛰️</b></blockquote>"),
        ("██░░░░░░░░░░░  25%", "<blockquote><b>Checking Link Security... 🛡️</b></blockquote>"),
        ("████░░░░░░░░░  40%", "<blockquote><b>Bypassing Cloudflare... ⛈️</b></blockquote>"),
        ("██████░░░░░░░  55%", "<blockquote><b>Solving Recaptcha... 🤖</b></blockquote>"),
        ("███████░░░░░░  70%", "<blockquote><b>Extracting Ad-Data... 🔓</b></blockquote>"),
        ("██████████░░░  85%", "<blockquote><b>Decrypting Final URL... ⚡</b></blockquote>"),
        ("████████████░  95%", "<blockquote><b>Generating Response... ✨</b></blockquote>"),
        ("█████████████  100%", "<blockquote><b>Success! Processing Done ✅</b></blockquote>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.6) # Total processing time ~5 seconds
        try: await status_msg.edit_text(f"{bar}\n{text}")
        except: pass

    try:
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        bypassed_url = data.get("bypassed") or data.get("url") or data.get("result")
        
        credits = await get_user_credits(user_id)

        # Colorful Inline Buttons
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/rajxcheats", style="danger")) # Red
        builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal", style="success")) # Green
        builder.row(InlineKeyboardButton(text="🔗 Refer & Earn", callback_data="refer_info", style="primary")) # Blue

        ui_text = (
            "<blockquote>"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏎️ <b>RAJX BYPASS BOT</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Result:</b>\n"
            f"<b>{bypassed_url}</b>\n\n"
            f"💰 <b>Your Credits:</b> <code>{credits}</code>\n"
            f"👤 <b>User:</b> {message.from_user.first_name}\n"
            f"👑 <b>Owner:</b> {DEV_HANDLE} ✅\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        await status_msg.edit_text(ui_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    except:
        await status_msg.edit_text("❌ <b>API Error!</b>")

# ==================== START & SYSTEM ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Join Chat", url="https://t.me/ffofcchat", style="primary"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify", style="success"))
        return await message.reply("<blockquote>⚠️ <b>Join first to start!</b></blockquote>", reply_markup=builder.as_markup())

    if users_db:
        await users_db.update_one({"user_id": user_id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/rajxcheats", style="danger")) # Red
    builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal", style="success")) # Green
    builder.row(InlineKeyboardButton(text="🔗 Refer & Earn", callback_data="refer_info", style="primary")) # Blue
    builder.row(InlineKeyboardButton(text="🎯 Daily Spin", callback_data="spin_now", style="success"))

    await message.reply(f"<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nWelcome {message.from_user.first_name}!\nBypass link in group to earn!</blockquote>", reply_markup=builder.as_markup())

# ==================== CALLBACKS ====================

@dp.callback_query(F.data == "check_bal")
async def check_bal(cb: types.CallbackQuery):
    credits = await get_user_credits(cb.from_user.id)
    await cb.answer(f"💰 Your Balance: {credits} Credits", show_alert=True)

@dp.callback_query(F.data == "refer_info")
async def refer_info(cb: types.CallbackQuery):
    me = await bot.get_me()
    await cb.message.answer(f"🔗 <b>Your Refer Link:</b>\n<code>https://t.me/{me.username}?start={cb.from_user.id}</code>")
    await cb.answer()

@dp.callback_query(F.data == "spin_now")
async def spin_now(cb: types.CallbackQuery):
    win = random.randint(1, 5)
    if users_db: await users_db.update_one({"user_id": cb.from_user.id}, {"$inc": {"credits": win}})
    await cb.message.answer("🎯 <b>Dart Thrown...</b>")
    await asyncio.sleep(1)
    await cb.answer(f"🎯 HIT! You won {win} Credits!", show_alert=True)

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Join Dono Channels!", show_alert=True)

# ==================== SERVER RUN ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Bot Active"

async def main():
    Thread(target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
