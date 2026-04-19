import os
import asyncio
import time
import cloudscraper
import random
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ==================== CONFIGURATION (HIDDEN) ====================
# Yeh saari keys aapko Render/VPS ke Environment Variables mein daalni hain
TOKEN = os.environ.get("BOT_TOKEN")
# API key ko 'PAID_API_KEY' naam se environment mein save karein
API_KEY = os.environ.get("PAID_API_KEY") 
PAID_API_URL = f"https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key={API_KEY}&link="

MONGO_URL = os.environ.get("MONGO_URL")
ADMINS = [7944388044, 123456789] # Apni ID yahan list mein add karein

# Branding
CHANNELS = ["ffofcchat", "rajxcheats"] 
GROUP_LINK = "https://t.me/ffofcchat"
DEV_HANDLE = "@rajxcheats"
API_CREDIT = "@RAJFFLIVE"

# Database Connection
m_client = AsyncIOMotorClient(MONGO_URL)
db = m_client.bypass_bot
users_db = db.users

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# ==================== HELPERS ====================
async def check_force_join(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ["left", "kicked"]: return False
        except Exception: return False
    return True

# ==================== ADMIN COMMANDS ====================
@dp.message(Command("admin"), F.from_user.id.in_(ADMINS))
async def admin_menu(message: types.Message):
    menu = (
        "👑 <b>Admin Control Panel</b>\n\n"
        "• <code>/broadcast</code> (Reply to msg) - Send to all users\n"
        "• <code>/stats</code> - Check total users\n"
        "• <code>/add_admin ID</code> - Add new admin\n"
        "• <code>/ban ID</code> - Ban a user"
    )
    await message.reply(menu)

@dp.message(Command("broadcast"), F.from_user.id.in_(ADMINS))
async def broadcast(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("Reply to a message to broadcast!")
    
    users = users_db.find({})
    count, fail = 0, 0
    await message.reply("🚀 Broadcast started...")
    
    async for user in users:
        try:
            await bot.copy_message(user['user_id'], message.chat.id, message.reply_to_message.message_id)
            count += 1
            await asyncio.sleep(0.05) # Rate limit check
        except: fail += 1
    await message.reply(f"✅ Finished!\nSent: {count}\nFailed: {fail}")

# ==================== REFER & SPIN SYSTEM ====================
@dp.message(Command("refer"))
async def refer(message: types.Message):
    bot_me = await bot.get_me()
    ref_link = f"https://t.me/{bot_me.username}?start={message.from_user.id}"
    await message.reply(
        f"🎁 <b>Refer & Earn</b>\n\nInvite 5 friends to get 1 week Ad-Free access!\n\n"
        f"🔗 Your Link: <code>{ref_link}</code>"
    )

@dp.message(Command("spin"))
async def spin(message: types.Message):
    # Basic Spin Logic
    items = ["💎 Premium", "❌ Try Again", "🔥 Double Points", "✨ Lucky Pass"]
    result = random.choice(items)
    await message.reply(f"🎰 <b>Daily Spin</b>\n\nResult: <b>{result}</b>")

# ==================== BYPASS LOGIC ====================
@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="‼️ USE HERE ‼️", url=GROUP_LINK, style="success"))
        return await message.reply("<blockquote>❌ <b>Private Bypass Disabled!</b>\nUse our official group.</blockquote>", reply_markup=builder.as_markup())

    user_id = message.from_user.id
    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Join Group", url=GROUP_LINK, style="danger"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify", style="success"))
        return await message.reply("<blockquote>⚠️ <b>Join our channels first!</b></blockquote>", reply_markup=builder.as_markup())

    # --- PROGRESS ANIMATION ---
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Connecting... ⚡</b></blockquote>")
    await asyncio.sleep(0.4)
    await status_msg.edit_text("█████████████  100%\n<blockquote><b>Success! ✅</b></blockquote>")
    
    start_time = time.perf_counter()

    try:
        response = scraper.get(f"{PAID_API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        
        # Clean Link Logic (JSON kachra hatane ke liye)
        res = data.get("bypassed") or data.get("bypassed_url") or data.get("result")
        bypassed_url = res.get("bypassed") if isinstance(res, dict) else res

        if not bypassed_url:
            return await status_msg.edit_text("❌ <b>Bypass Failed!</b>\nLink not supported.")

        time_taken = round(time.perf_counter() - start_time, 2)
        
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
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🕒 <b>Time Taken :</b> <code>{time_taken}s</code>\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"⚙️ <b>FOR API :</b> {API_CREDIT}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE} ✅"
            "</blockquote>"
        )
        await status_msg.edit_text(ui_text, disable_web_page_preview=True)

    except:
        await status_msg.edit_text("❌ <b>Request Timeout!</b>\nAPI busy hai, thodi der mein try karein.")

# ==================== VERIFY & START ====================
@dp.callback_query(F.data == "verify")
async def verify(callback: types.CallbackQuery):
    if await check_force_join(callback.from_user.id):
        await callback.answer("✅ Verified!", show_alert=True)
        await callback.message.delete()
    else:
        await callback.answer("❌ Join both channels first!", show_alert=True)

@dp.message(Command("start"))
async def start(message: types.Message):
    # Save User to DB
    await users_db.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Channel", url="https://t.me/rajxcheats", style="primary"))
    builder.row(InlineKeyboardButton(text="🚀 USE HERE 🚀", url=GROUP_LINK, style="success"))
    await message.reply(f"<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n━━━━━━━━━━━━━\nAdd me to group to bypass!</blockquote>", reply_markup=builder.as_markup())

# ==================== RUN SERVER & BOT ====================
server = Flask(__name__)
@server.route('/')
def st(): return "✅ Bot is Live"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)

async def main():
    Thread(target=run_server, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
