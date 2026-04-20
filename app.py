import os
import asyncio
import cloudscraper
import random
import string
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
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
WELCOME_PIC = "https://i.ibb.co/wZmXVxhc/c24e9ff22ed1.jpg"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# --- Database ---
users_db = None
settings_db = None

async def init_db():
    global users_db, settings_db
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            db = client.bypass_bot
            users_db = db.users
            settings_db = db.settings
            await users_db.create_index([("ref_count", -1)])
            print("✅ Database & Leaderboard Ready")
        except: print("⚠️ DB Connection Failed")

# ==================== HELPERS ====================

async def check_force_join(user_id):
    if user_id == OWNER_ID: return True
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{channel}", user_id)
            if member.status in ["left", "kicked"]: return False
        except: return False
    return True

async def get_user_data(user_id, name="User"):
    if users_db is not None:
        user = await users_db.find_one({"user_id": user_id})
        if not user:
            new_user = {"user_id": user_id, "name": name, "credits": 5, "ref_count": 0, "total_bypass": 0, "last_spin": None}
            await users_db.insert_one(new_user)
            return new_user
        return user
    return {"credits": 0, "ref_count": 0, "total_bypass": 0}

# ==================== ADMIN COMMANDS (FULL) ====================

@dp.message(Command("admin"), F.from_user.id == OWNER_ID)
async def admin_panel(message: types.Message):
    text = (
        "<b>👑 OWNER ADMIN PANEL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📊 /stats - Bot User Stats\n"
        "📢 /broadcast - Reply to msg\n"
        "🎁 /gen <code>(amt)</code> - Create Code\n"
        "➕ /addchan <code>(user)</code> - Add FJ\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await message.reply(text)

@dp.message(Command("stats"), F.from_user.id == OWNER_ID)
async def cmd_stats(message: types.Message):
    total_users = await users_db.count_documents({})
    # Calculate total bypasses (sum of all users total_bypass)
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_bypass"}}}]
    res = await users_db.aggregate(pipeline).to_list(1)
    total_bypass = res[0]['total'] if res else 0
    
    await message.reply(f"📊 <b>BOT STATS:</b>\n\n👤 Total Users: {total_users}\n🏎️ Total Bypasses: {total_bypass}")

# ==================== START & WELCOME ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Referral Logic
    if users_db and command.args and command.args.isdigit():
        ref_id = int(command.args)
        if ref_id != user_id:
            exist = await users_db.find_one({"user_id": user_id})
            if not exist:
                await users_db.update_one({"user_id": ref_id}, {"$inc": {"credits": 5, "ref_count": 1}})
                try: await bot.send_message(ref_id, f"🎉 <b>New Refer!</b> +5 Credits Added.")
                except: pass

    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Join Channel", url="https://t.me/rajxcheats", style="primary"))
        builder.row(InlineKeyboardButton(text="💬 Join Chat", url="https://t.me/ffofcchat", style="primary"))
        builder.row(InlineKeyboardButton(text="🚀 Verify ✅", callback_data="verify", style="success"))
        return await message.answer_photo(photo=WELCOME_PIC, caption="<blockquote>⚠️ <b>Join Channels First!</b></blockquote>", reply_markup=builder.as_markup())

    user_data = await get_user_data(user_id, user_name)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="‼️ BUY PAID API ‼️", url="https://t.me/visitpornhub", style="danger"))
    builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal", style="success"), InlineKeyboardButton(text="🏆 Leaderboard", callback_data="leaderboard", style="primary"))
    builder.row(InlineKeyboardButton(text="🎰 Lucky Spin", callback_data="spin_now", style="success"), InlineKeyboardButton(text="🔗 Refer & Earn", callback_data="refer_info", style="primary"))

    welcome_text = (
        f"🏎️ <b>RAJX BYPASS SYSTEM v5.0</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 <b>Welcome, {user_name}!</b>\n\n"
        f"💰 <b>Credits:</b> <code>{user_data.get('credits', 0)}</code>\n"
        f"👥 <b>Total Refers:</b> <code>{user_data.get('ref_count', 0)}</code>\n"
        f"👑 <b>Owner:</b> {DEV_HANDLE}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Link group mein bhejein aur bypass dekhein!</i>"
    )
    await message.answer_photo(photo=WELCOME_PIC, caption=welcome_text, reply_markup=builder.as_markup())

# ==================== BYPASS (8 STAGES + CLEAN FORMAT) ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if not await check_force_join(message.from_user.id): return
    if message.chat.type == "private":
        return await message.reply("❌ Groups Only!", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ GROUP", url=GROUP_LINK, style="success")).as_markup())

    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░  15%", "<b>Bypassing Ads... ⛈️</b>"),
        ("███░░░░░░░░░  35%", "<b>Connecting Proxy... 🛰️</b>"),
        ("█████░░░░░░░  55%", "<b>Extracting Data... 🔓</b>"),
        ("█████████░░░  75%", "<b>Generating Link... ⚡</b>"),
        ("████████████  100%", "<b>Bypass Done! ✅</b>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.6)
        try: await status_msg.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    try:
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        bypassed_url = data.get("bypassed") or data.get("url") or data.get("result")
        
        # Increment total bypass count
        if users_db: await users_db.update_one({"user_id": message.from_user.id}, {"$inc": {"total_bypass": 1}})
        
        user_data = await get_user_data(message.from_user.id)

        res_text = (
            "<blockquote>"
            "🏎️ <b>RAJX BYPASS BOT</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔗 <b>Original Link :</b>\n"
            f"<code>{message.text}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>Bypassed Link :</b>\n"
            f"<b>{bypassed_url}</b>\n\n"
            f"💰 <b>Your Balance :</b> {user_data.get('credits', 0)}\n"
            f"👤 <b>User :</b> {message.from_user.first_name}\n"
            f"👑 <b>Owner :</b> {DEV_HANDLE}\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/visitpornhub", style="danger"))
        builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal", style="success"))

        await status_msg.edit_text(res_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    except: await status_msg.edit_text("❌ <b>API Timeout!</b> Check URL.")

# ==================== CALLBACKS ====================

@dp.callback_query(F.data == "spin_now")
async def spin_logic(cb: types.CallbackQuery):
    user = await get_user_data(cb.from_user.id)
    last_spin = user.get("last_spin")
    if last_spin and (datetime.now() - datetime.fromisoformat(last_spin)) < timedelta(days=1):
        return await cb.answer("⏳ 24h limit!", show_alert=True)

    win = random.randint(2, 10)
    await users_db.update_one({"user_id": cb.from_user.id}, {"$inc": {"credits": win}, "$set": {"last_spin": datetime.now().isoformat()}})
    await cb.message.answer(f"🎰 <b>Spin Reward:</b> +{win} Credits!")
    await cb.answer()

@dp.callback_query(F.data == "leaderboard")
async def show_leaderboard(cb: types.CallbackQuery):
    top_users = await users_db.find().sort("ref_count", -1).limit(10).to_list(10)
    text = "🏆 <b>TOP REFER LEADERS</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, u in enumerate(top_users, 1):
        text += f"{i}. {u.get('name')} — <b>{u.get('ref_count')} Refers</b>\n"
    await cb.message.answer(text)
    await cb.answer()

@dp.callback_query(F.data == "verify")
async def verify_cb(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Join channels first!", show_alert=True)

# ==================== RUN ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Live"

async def main():
    await init_db()
    Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
