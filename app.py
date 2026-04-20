import os
import asyncio
import cloudscraper
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

# ==================== OWNER GOD FUNCTIONS ====================

def is_owner(u_id): return u_id == OWNER_ID

@dp.message(Command("stats"), F.from_user.id == OWNER_ID)
async def cmd_stats(message: types.Message):
    u_count = await users_col.count_documents({}) if users_col else 0
    g_count = await groups_col.count_documents({}) if groups_col else 0
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$bypasses"}}}]
    res = await users_col.aggregate(pipeline).to_list(1)
    total_b = res[0]['total'] if res else 0

    stats_text = (
        "📈 <b>ULTIMATE BOT STATS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Total Users:</b> <code>{u_count}</code>\n"
        f"👥 <b>Total Groups:</b> <code>{g_count}</code>\n"
        f"🏎️ <b>Total Bypasses:</b> <code>{total_b}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await message.reply(stats_text)

@dp.message(Command("broadcast"), F.from_user.id == OWNER_ID)
async def cmd_broadcast(message: types.Message):
    if not message.reply_to_message:
        return await message.reply("❌ Reply to a message to broadcast!")
    
    users = await users_col.find().to_list(10000)
    groups = await groups_col.find().to_list(10000)
    targets = list(set([u['user_id'] for u in users] + [g['group_id'] for g in groups]))
    
    ok, fail = 0, 0
    for t_id in targets:
        try:
            await bot.copy_message(t_id, message.chat.id, message.reply_to_message.message_id)
            ok += 1
            await asyncio.sleep(0.05)
        except: fail += 1
    await message.reply(f"📢 <b>Broadcast Done!</b>\n✅ Success: {ok}\n❌ Failed: {fail}")

# ==================== BYPASS HANDLER (8 STAGES) ====================

async def check_fj(u_id):
    if is_owner(u_id): return True
    for c in CHANNELS:
        try:
            m = await bot.get_chat_member(f"@{c}", u_id)
            if m.status in ["left", "kicked"]: return False
        except: return False
    return True

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    # Track Group
    if message.chat.type in ["group", "supergroup"]:
        await groups_col.update_one({"group_id": message.chat.id}, {"$set": {"title": message.chat.title}}, upsert=True)

    if not await check_fj(message.from_user.id):
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats"), InlineKeyboardButton(text="💬 Join Group", url="https://t.me/ffofcchat"))
        b.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify", style="success"))
        return await message.reply("<blockquote>❗ <b>Join Channels First!</b></blockquote>", reply_markup=b.as_markup())

    if message.chat.type == "private" and not is_owner(message.from_user.id):
        b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
        return await message.reply("<blockquote>❌ <b>PRIVATE BYPASS OFF!</b>\n\nLink group mein bhejein.</blockquote>", reply_markup=b.as_markup())

    # --- 8 STAGES PROCESSING ---
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
        try: await status.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    try:
        r = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30).json()
        link = r.get("bypassed") or r.get("url") or r.get("result")
        if isinstance(link, dict): link = link.get("bypassed") or link.get("url")

        await users_col.update_one({"user_id": message.from_user.id}, {"$inc": {"bypasses": 1}, "$set": {"name": message.from_user.first_name}}, upsert=True)

        res_text = (
            "<blockquote>"
            "🏎️ <b>RAJX BYPASS SYSTEM</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔗 <b>Original Link :</b>\n"
            f"<code>{message.text}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Bypassed Link :</b>\n"
            f"<b>{link}</b>\n\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE}\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger"))
        await status.edit_text(res_text, reply_markup=b.as_markup(), disable_web_page_preview=True)
    except: await status.edit_text("<blockquote>❌ <b>API Error!</b></blockquote>")

# ==================== SYSTEM ====================

@dp.message(Command("start"))
async def start(message: types.Message):
    await users_col.update_one({"user_id": message.from_user.id}, {"$set": {"name": message.from_user.first_name}}, upsert=True)
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger"))
    b.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
    await message.answer_photo(photo=WELCOME_PIC, caption="<blockquote>🏎️ <b>RAJX BYPASS BOT</b>\n\nWelcome! Group join karein aur bypass karein.</blockquote>", reply_markup=b.as_markup())

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_fj(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Join Dono Channels!", show_alert=True)

server = Flask(__name__)
@server.route('/')
def st(): return "Live"

async def main():
    await init_db()
    Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
