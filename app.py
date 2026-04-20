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

# --- Database ---
users_col = None
groups_col = None

async def init_db():
    global users_col, groups_col
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL)
            db = client.bypass_bot
            users_col = db.users
            groups_col = db.groups
            print("✅ Database Connected")
        except: print("⚠️ DB Error")

# ==================== HELPERS ====================

async def check_fj(u_id):
    if u_id == OWNER_ID: return True
    for c in CHANNELS:
        try:
            m = await bot.get_chat_member(f"@{c}", u_id)
            if m.status in ["left", "kicked"]: return False
        except: continue
    return True

# ==================== HANDLERS ====================

@dp.message(Command("start"))
async def start(message: types.Message):
    if users_col:
        await users_col.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)
    
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger"))
    b.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
    
    caption = (
        "<blockquote>"
        f"🏎️ <b>RAJX BYPASS SYSTEM</b>\n\n"
        f"Welcome <b>{message.from_user.first_name}</b>!\n"
        "Send any link to bypass or join our community."
        "</blockquote>"
    )
    await message.answer_photo(photo=WELCOME_PIC, caption=caption, reply_markup=b.as_markup())

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    # Track Group
    if message.chat.type in ["group", "supergroup"] and groups_col:
        await groups_col.update_one({"group_id": message.chat.id}, {"$set": {"title": message.chat.title}}, upsert=True)

    # Force Join Check
    if not await check_fj(message.from_user.id):
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats"), InlineKeyboardButton(text="💬 Join Group", url="https://t.me/ffofcchat"))
        b.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify", style="success"))
        return await message.reply("<blockquote>❗ <b>ACCESS DENIED!</b>\n\nYou must join our channels to use this bot.</blockquote>", reply_markup=b.as_markup())

    # Private Chat Restriction
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ USE IN GROUP ⚡", url=GROUP_LINK, style="success"))
        return await message.reply("<blockquote>❌ <b>PRIVATE BYPASS DISABLED!</b>\n\nPlease send your links in the group.</blockquote>", reply_markup=b.as_markup())

    # --- 8 STAGES ANIMATED PROGRESS ---
    status = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing Engine... ⚙️</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░  12%", "<b>Connecting Proxy... 🛰️</b>"),
        ("██░░░░░░░░░░  25%", "<b>Bypassing Ads... ⛈️</b>"),
        ("████░░░░░░░░  40%", "<b>Checking Safety... 🛡️</b>"),
        ("██████░░░░░░  55%", "<b>Solving Captcha... 🤖</b>"),
        ("████████░░░░  70%", "<b>Extracting Link... 🔓</b>"),
        ("██████████░░  85%", "<b>Decrypting Data... ⚡</b>"),
        ("████████████  95%", "<b>Finalizing... ✨</b>"),
        ("████████████  100%", "<b>Success! ✅</b>")
    ]

    for bar, text in stages:
        await asyncio.sleep(0.5)
        try:
            await status.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    # API Call
    try:
        r = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30).json()
        link = r.get("bypassed") or r.get("url") or r.get("result")
        if isinstance(link, dict): link = link.get("url") or link.get("bypassed")

        if users_col:
            await users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"bypasses": 1}}, upsert=True)

        # Updated Response Format
        res_text = (
            "<blockquote>"
            "🏎️ <b>BYPASS SUCCESSFUL!</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 <b>Original Link:</b> <code>{message.text}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 <b>Bypassed Link:</b>\n<b>{link}</b>\n\n"
            f"👤 <b>User:</b> {message.from_user.first_name}\n"
            f"👑 <b>Owner:</b> {DEV_HANDLE}\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger"))
        await status.edit_text(res_text, reply_markup=b.as_markup(), disable_web_page_preview=True)
    except:
        await status.edit_text("<blockquote>❌ <b>API ERROR!</b>\nUnable to bypass this link. Please try another one.</blockquote>")

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_fj(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Join both channels first!", show_alert=True)

# ==================== RUNNER ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Online"

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    print("🤖 Bot Ready")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
