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
from aiogram.types import InlineKeyboardButton, URLInputFile
from motor.motor_asyncio import AsyncIOMotorClient

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN")
API_URL = os.environ.get("NEW_API_URL") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajxcheats"
CHANNELS = ["rajxcheats", "ffofcchat"] 
GROUP_LINK = "https://t.me/ffofcchat"
WELCOME_PIC = "https://telegra.ph/file/0c4456956627063229b01.jpg" # Achi image link

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# Database Setup
users_db = None
codes_db = None

async def init_db():
    global users_db, codes_db
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            db = client.bypass_bot
            users_db = db.users
            codes_db = db.redeem_codes
            print("✅ Database Connected")
        except: print("⚠️ DB Error")

# ==================== HELPERS ====================

async def check_force_join(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ["left", "kicked"]: return False
        except: return False
    return True

async def get_data(user_id):
    if users_db is not None:
        user = await users_db.find_one({"user_id": user_id})
        if not user:
            await users_db.insert_one({"user_id": user_id, "credits": 5}) # Starting 5 credits
            return 5
        return user.get("credits", 0)
    return 0

# ==================== START & WELCOME ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Chat", url="https://t.me/ffofcchat", style="primary"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify", style="success"))
        return await message.answer_photo(photo=WELCOME_PIC, caption="<blockquote>⚠️ <b>Join our channels first to use the bot!</b></blockquote>", reply_markup=builder.as_markup())

    credits = await get_data(user_id)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/rajxcheats", style="danger"))
    builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal", style="success"))
    builder.row(InlineKeyboardButton(text="🔗 Refer & Earn", callback_data="refer_info", style="primary"))
    builder.row(InlineKeyboardButton(text="🎯 Daily Spin", callback_data="spin_now", style="success"))

    welcome_text = (
        f"🏎️ <b>Welcome to RAJX BYPASS BOT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Hello, {message.from_user.first_name}!\n\n"
        f"💰 <b>Your Credits:</b> <code>{credits}</code>\n"
        f"👑 <b>Owner:</b> {DEV_HANDLE}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Send any link in our group to bypass!</i>"
    )
    await message.answer_photo(photo=WELCOME_PIC, caption=welcome_text, reply_markup=builder.as_markup())

# ==================== ADMIN COMMANDS ====================

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    await message.reply("👑 <b>Admin Panel</b>\n\n/gen (amt) - Create Code\n/stats - User count\n/broadcast - Message all")

@dp.message(Command("gen"))
async def gen_code(message: types.Message, command: CommandObject):
    if message.from_user.id != OWNER_ID or not command.args: return
    code = "RAJX-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    await codes_db.insert_one({"code": code, "credits": int(command.args), "used": False})
    await message.reply(f"🎁 <b>Promo:</b> <code>{code}</code>\n<b>Value:</b> {command.args}")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    count = await users_db.count_documents({})
    await message.reply(f"📊 <b>Total Users:</b> <code>{count}</code>")

# ==================== FEATURES ====================

@dp.callback_query(F.data == "spin_now")
async def spin_now(cb: types.CallbackQuery):
    # Animation and Win
    win = random.randint(2, 10)
    await users_db.update_one({"user_id": cb.from_user.id}, {"$inc": {"credits": win}})
    
    msg = await cb.message.answer("🎯 <b>Dart Thrown...</b>")
    await asyncio.sleep(1)
    await msg.edit_text(f"🎯 <b>HIT!</b>\n\n🎰 You won <b>{win} Credits!</b>")
    await cb.answer()

@dp.callback_query(F.data == "check_bal")
async def check_bal(cb: types.CallbackQuery):
    credits = await get_data(cb.from_user.id)
    await cb.answer(f"💰 Balance: {credits} Credits", show_alert=True)

# ==================== BYPASS HANDLER ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if not await check_force_join(message.from_user.id): return
    
    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing Engine... ⚙️</b></blockquote>")
    
    # 7 Stages
    stages = [("██░░░░░░  25%", "Connecting..."), ("██████░░  65%", "Bypassing..."), ("████████  100%", "Success!")]
    for b, t in stages:
        await asyncio.sleep(0.8)
        try: await status_msg.edit_text(f"{b}\n<blockquote><b>{t}</b></blockquote>")
        except: pass

    try:
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        res = data.get("bypassed") or data.get("url") or data.get("result")
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/rajxcheats", style="danger"))
        builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal", style="success"))

        await status_msg.edit_text(f"🚀 <b>Result:</b> {res}", reply_markup=builder.as_markup())
    except: await status_msg.edit_text("❌ API Error!")

# ==================== RUN ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Active"

async def main():
    await init_db()
    Thread(target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
