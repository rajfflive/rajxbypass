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

# MongoDB ko optional rakha hai taaki bot crash na ho
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN")
API_URL = os.environ.get("NEW_API_URL") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajxcheats"
CHANNELS = ["rajxcheats", "ffofcchat"] 
GROUP_LINK = "https://t.me/ffofcchat"
WELCOME_PIC = "https://i.ibb.co/wZmXVxhc/c24e9ff22ed1.jpg"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# Database Vars
users_db = None
codes_db = None

async def init_db():
    global users_db, codes_db
    if MONGO_URL and MONGO_AVAILABLE:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            db = client.bypass_bot
            users_db = db.users
            codes_db = db.redeem_codes
            await client.server_info()
            print("✅ MongoDB Connected")
        except: print("⚠️ DB Connection Failed - Running in Cache Mode")

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
    return "N/A"

# ==================== ADMIN COMMANDS ====================

@dp.message(Command("admin"), F.from_user.id == OWNER_ID)
async def admin_panel(message: types.Message):
    count = await users_db.count_documents({}) if users_db else "0"
    text = (
        f"👑 <b>OWNER ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Total Users: <code>{count}</code>\n"
        f"• /broadcast - Reply to msg\n"
        f"• /gen <code>(amt)</code> - Generate Code\n"
        f"• /stats - Detailed Stats"
    )
    await message.reply(text)

@dp.message(Command("gen"), F.from_user.id == OWNER_ID)
async def gen_promo(message: types.Message, command: CommandObject):
    if not command.args or not codes_db: return
    code = "RAJX-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    await codes_db.insert_one({"code": code, "credits": int(command.args), "used": False})
    await message.reply(f"✅ <b>Redeem Code:</b> <code>{code}</code>\n<b>Value:</b> {command.args}")

# ==================== START & USER INTERFACE ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    
    # Database Saving & Refer Logic
    if users_db:
        user = await users_db.find_one({"user_id": user_id})
        if not user:
            # First time user setup
            if command.args and command.args.isdigit():
                ref_id = int(command.args)
                await users_db.update_one({"user_id": ref_id}, {"$inc": {"credits": 2}})
                try: await bot.send_message(ref_id, "🎁 <b>+2 Credits!</b> Someone joined via your link.")
                except: pass
            await users_db.update_one({"user_id": user_id}, {"$set": {"name": message.from_user.first_name, "credits": 5}}, upsert=True)

    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Join Chat", url="https://t.me/ffofcchat", style="primary"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify", style="success"))
        return await message.answer_photo(photo=WELCOME_PIC, caption="<blockquote>⚠️ <b>Pehle dono channels join karo bypass karne ke liye!</b></blockquote>", reply_markup=builder.as_markup())

    credits = await get_user_credits(user_id)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/rajxcheats", style="danger"))
    builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal", style="success"))
    builder.row(InlineKeyboardButton(text="🔗 Refer & Earn", callback_data="refer_info", style="primary"))
    builder.row(InlineKeyboardButton(text="🎰 Daily Spin", callback_data="spin_now", style="success"))

    welcome_text = (
        f"🏎️ <b>RAJX BYPASS BOT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Hello, {message.from_user.first_name}!\n\n"
        f"💰 <b>Balance:</b> <code>{credits} Credits</code>\n"
        f"👑 <b>Owner:</b> {DEV_HANDLE}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Group mein link bhejo aur bypass karo!</i>"
    )
    await message.answer_photo(photo=WELCOME_PIC, caption=welcome_text, reply_markup=builder.as_markup())

# ==================== SPIN & BYPASS ====================

@dp.callback_query(F.data == "spin_now")
async def spin_logic(cb: types.CallbackQuery):
    win = random.randint(1, 5)
    if users_db: await users_db.update_one({"user_id": cb.from_user.id}, {"$inc": {"credits": win}})
    
    msg = await cb.message.answer("🎯 <b>Throwing Dart...</b>")
    await asyncio.sleep(0.8)
    await msg.edit_text("🥅 <b>GOAL! Congrats!</b>")
    await asyncio.sleep(0.5)
    
    final_bal = await get_user_credits(cb.from_user.id)
    res_text = (
        "<blockquote>"
        "🎁 <b>DAILY SPIN RESULT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🎉 Won: +{win} Credits\n"
        f"💰 Total: {final_bal}\n"
        "━━━━━━━━━━━━━━━━━━━━</blockquote>"
    )
    builder = InlineKeyboardBuilder().row(InlineKeyboardButton(text="🎁 Get More Credits", callback_data="refer_info", style="success"))
    await msg.edit_text(res_text, reply_markup=builder.as_markup())
    await cb.answer()

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if not await check_force_join(message.from_user.id): return
    if message.chat.type == "private":
        return await message.reply("❌ Groups Only!", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ GROUP LINK", url=GROUP_LINK, style="success")).as_markup())

    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Bypassing... ⛈️</b></blockquote>")
    
    # Multi-Stage Processing
    stages = [("███░░░░░░  35%", "Bypassing..."), ("█████████  100%", "Success! ✅")]
    for b, t in stages:
        await asyncio.sleep(0.7)
        try: await status_msg.edit_text(f"{b}\n<blockquote>{t}</blockquote>")
        except: pass

    try:
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        res = data.get("bypassed") or data.get("url") or data.get("result")
        
        credits = await get_user_credits(message.from_user.id)
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/rajxcheats", style="danger"))
        builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal", style="success"))

        await status_msg.edit_text(
            f"<blockquote>🏎️ <b>BYPASS SUCCESS</b>\n\n🚀 <b>Result:</b> {res}\n💰 <b>Credits:</b> {credits}</blockquote>",
            reply_markup=builder.as_markup(), disable_web_page_preview=True
        )
    except: await status_msg.edit_text("❌ <b>API Error!</b> Check variables.")

# ==================== SYSTEM RUN ====================

@dp.callback_query(F.data == "verify")
async def verify_cb(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Join Dono Channels!", show_alert=True)

@dp.callback_query(F.data == "refer_info")
async def refer_info(cb: types.CallbackQuery):
    me = await bot.get_me()
    await cb.message.answer(f"🔗 <b>Refer Link:</b>\n<code>https://t.me/{me.username}?start={cb.from_user.id}</code>\n\nGet 2 Credits per join!")
    await cb.answer()

@dp.callback_query(F.data == "check_bal")
async def bal_cb(cb: types.CallbackQuery):
    c = await get_user_credits(cb.from_user.id)
    await cb.answer(f"💰 Balance: {c} Credits", show_alert=True)

server = Flask(__name__)
@server.route('/')
def st(): return "Live"

async def main():
    await init_db()
    Thread(target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
