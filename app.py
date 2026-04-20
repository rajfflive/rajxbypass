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
# Render pe ye 2 variables 'NEW_API_URL' aur 'MONGO_URL' set karna
API_URL = os.environ.get("NEW_API_URL") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajxcheats"
GROUP_LINK = "https://t.me/ffofcchat"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# Database Connection (No-Freeze Logic)
users_db = None
codes_db = None
settings_db = None

async def init_db():
    global users_db, codes_db, settings_db
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            db = client.bypass_bot
            users_db = db.users
            codes_db = db.redeem_codes
            settings_db = db.settings
            await client.server_info()
            print("✅ Database Connected")
        except:
            print("⚠️ Database Error: Running in No-DB mode")

# ==================== ADMIN & OWNER FUNCTIONS ====================

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    text = (
        "👑 <b>OWNER CONTROL PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "• /stats - Check User Count\n"
        "• /broadcast - Reply to any msg\n"
        "• /gen <code>(amt)</code> - Generate Redeem Code\n"
        "• /aadm <code>(ID)</code> - Add Admin\n"
        "• /rmadm <code>(ID)</code> - Remove Admin"
    )
    await message.reply(text)

@dp.message(Command("gen"))
async def gen_code(message: types.Message, command: CommandObject):
    if message.from_user.id != OWNER_ID: return
    if not command.args or not codes_db: return
    code = "RAJX-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    await codes_db.insert_one({"code": code, "credits": int(command.args), "used": False})
    await message.reply(f"🎁 <b>Code:</b> <code>{code}</code>\n<b>Value:</b> {command.args}")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    count = await users_db.count_documents({}) if users_db else "N/A"
    await message.reply(f"📊 <b>Total Users:</b> <code>{count}</code>")

# ==================== BYPASS & FEATURES ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if message.chat.type == "private":
        builder = InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ USE IN GROUP", url=GROUP_LINK, style="success"))
        return await message.reply("<blockquote>❌ <b>Groups Only!</b></blockquote>", reply_markup=builder.as_markup())

    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Bypassing Link... ⛈️</b></blockquote>")
    
    # 7-Stage Process
    for p in ["████░░░░░░░░░  40%", "█████████████  100%"]:
        await asyncio.sleep(0.6)
        try: await status_msg.edit_text(f"{p}\n<blockquote><b>Success! ✅</b></blockquote>")
        except: pass

    try:
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        bypassed_url = data.get("bypassed") or data.get("url") or data.get("result")

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🛒 BUY API 🛒", url="https://t.me/rajxcheats", style="danger"))
        builder.row(InlineKeyboardButton(text="🔗 Share & Earn", url=f"https://t.me/share/url?url=https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}", style="primary"))
        builder.row(InlineKeyboardButton(text="🎰 Spin Now", callback_data="spin_now", style="success"))

        await status_msg.edit_text(
            f"<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\n🚀 <b>Result:</b> {bypassed_url}\n👑 <b>Owner:</b> {DEV_HANDLE}</blockquote>",
            reply_markup=builder.as_markup(), disable_web_page_preview=True
        )
    except: await status_msg.edit_text("❌ <b>API Timeout!</b>")

@dp.message(Command("spin"))
@dp.callback_query(F.data == "spin_now")
async def spin_feature(event):
    # Dart Animation Logic
    win = random.randint(1, 5)
    user_id = event.from_user.id
    if users_db: await users_db.update_one({"user_id": user_id}, {"$inc": {"credits": win}})
    
    msg = "🎯 <b>Dart is Thrown...</b>"
    if isinstance(event, types.Message):
        m = await event.reply(msg)
    else:
        m = await event.message.answer(msg)
    
    await asyncio.sleep(1)
    await m.edit_text(f"🎯 <b>HIT!</b>\n\n🎰 You won <b>{win} Credits!</b>")

@dp.message(Command("refer"))
async def refer_link(message: types.Message):
    me = await bot.get_me()
    await message.reply(f"🔗 <b>Your Refer Link:</b>\n<code>https://t.me/{me.username}?start={message.from_user.id}</code>")

# ==================== START & SYSTEM ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if users_db:
        await users_db.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🚀 JOIN GROUP 🚀", url=GROUP_LINK, style="success"))
    builder.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/rajxcheats", style="danger"))
    
    await message.reply(f"<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\nActive in Group!</blockquote>", reply_markup=builder.as_markup())

server = Flask(__name__)
@server.route('/')
def st(): return "Live"

async def main():
    await init_db()
    Thread(target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
