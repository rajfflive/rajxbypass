import os, asyncio, cloudscraper
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
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
WELCOME_PIC = "https://i.ibb.co/8L91y1CP/6ee42acc1338.jpg"
BUY_API_LINK = "https://t.me/visitpornhub"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

users_col = None
groups_col = None

async def init_db():
    global users_col, groups_col
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client.bypass_bot
        users_col = db.users
        groups_col = db.groups
        print("✅ MongoDB Connected")
    except Exception as e:
        print(f"❌ DB Error: {e}")

# ==================== HELPERS ====================

async def check_fj(u_id):
    if u_id == OWNER_ID: return True
    for c in CHANNELS:
        try:
            m = await bot.get_chat_member(f"@{c}", u_id)
            if m.status in ["left", "kicked"]: return False
        except: return True # Admin nhi hai tab bhi bypass allow karega error se bachne ke liye
    return True

# ==================== HANDLERS ====================

@dp.message(Command("start"))
async def start(message: types.Message):
    if users_col is not None:
        await users_col.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)
    
    b = InlineKeyboardBuilder()
    b.button(text="‼️ BUY API ‼️", url=BUY_API_LINK)
    b.button(text="⚡ USE HERE ⚡", url=GROUP_LINK)
    b.adjust(1)
    
    await message.answer_photo(
        photo=WELCOME_PIC, 
        caption=f"🏎️ <b>RAJX BYPASS BOT</b>\n\nWelcome <b>{message.from_user.first_name}</b>!\nLinks bypass karne ke liye group join karein.",
        reply_markup=b.as_markup()
    )

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    # Log Group
    if message.chat.type in ["group", "supergroup"] and groups_col is not None:
        await groups_col.update_one({"group_id": message.chat.id}, {"$set": {"title": message.chat.title}}, upsert=True)

    # Force Join Check
    if not await check_fj(message.from_user.id):
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.me/{CHANNELS[0]}"))
        b.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify"))
        return await message.reply("❗ <b>Please Join our channels to use this bot!</b>", reply_markup=b.as_markup())

    # Private Chat Restriction
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        b = InlineKeyboardBuilder().button(text="⚡ JOIN GROUP ⚡", url=GROUP_LINK)
        return await message.reply("❌ <b>Private Bypass is OFF!</b>\n\nBypass karne ke liye group join karein.", reply_markup=b.as_markup())

    # Progress Animation
    status = await message.reply("⏳ <b>Initializing...</b>")
    stages = ["█░░░ 25%", "████░ 50%", "███████ 75%", "██████████ 100%"]
    for s in stages:
        await asyncio.sleep(0.4)
        try: await status.edit_text(f"🚀 <b>Processing:</b>\n<code>{s}</code>")
        except: pass

    # API Call
    try:
        r = scraper.get(f"{API_URL}{message.text.strip()}", timeout=20).json()
        # API Response format check
        link = r.get("bypassed") or r.get("url") or r.get("result")
        if isinstance(link, dict): link = link.get("url")

        if not link: raise Exception("No Link")

        if users_col is not None:
            await users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"bypasses": 1}}, upsert=True)

        res_text = (
            "🏎️ <b>BYPASS SUCCESSFUL!</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>Link:</b> {link}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>By:</b> {message.from_user.first_name}"
        )
        await status.edit_text(res_text, disable_web_page_preview=True)
    except Exception as e:
        await status.edit_text(f"❌ <b>Bypass Failed!</b>\nReason: API down ya galat link.")

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_fj(cb.from_user.id):
        await cb.answer("✅ Verification Successful!", show_alert=True)
        await cb.message.delete()
    else:
        await cb.answer("❌ Abhi bhi join nahi kiya!", show_alert=True)

# ==================== RUNNER ====================
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Online"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

async def main():
    await init_db()
    Thread(target=run_flask, daemon=True).start()
    print("🤖 Bot Started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
