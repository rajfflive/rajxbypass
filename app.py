import os
import asyncio
import cloudscraper
import random
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
WELCOME_PIC = "https://i.ibb.co/8L91y1CP/6ee42acc1338.jpg"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

# --- Database Connection ---
users_db = None
async def init_db():
    global users_db
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            users_db = client.bypass_bot.users
            # Indexing for Leaderboard
            await users_db.create_index([("ref_count", -1)])
            print("✅ Database Connected & Leaderboard Ready")
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
            new_user = {"user_id": user_id, "name": name, "credits": 5, "ref_count": 0, "last_spin": None}
            await users_db.insert_one(new_user)
            return new_user
        return user
    return {"credits": 0, "ref_count": 0}

# ==================== START & WELCOME ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if users_db and command.args and command.args.isdigit():
        ref_id = int(command.args)
        if ref_id != user_id:
            exist = await users_db.find_one({"user_id": user_id})
            if not exist:
                await users_db.update_one({"user_id": ref_id}, {"$inc": {"credits": 5, "ref_count": 1}})
                try: await bot.send_message(ref_id, f"🎉 <b>New Referral!</b> <code>{user_name}</code> joined via your link. +5 Credits!")
                except: pass

    if not await check_force_join(user_id):
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📢 Channel", url="https://t.me/rajxcheats"), InlineKeyboardButton(text="💬 Chat", url="https://t.me/ffofcchat"))
        builder.row(InlineKeyboardButton(text="🚀 Verify Join ✅", callback_data="verify"))
        return await message.answer_photo(photo=WELCOME_PIC, caption="<blockquote>⚠️ <b>Join Channels First!</b>\nJoin karke 'Verify' button dabayein.</blockquote>", reply_markup=builder.as_markup())

    user_data = await get_user_data(user_id, user_name)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="‼️ BUY PAID API ‼️", url="https://t.me/visitpornhub"))
    builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal"), InlineKeyboardButton(text="🏆 Leaderboard", callback_data="leaderboard"))
    builder.row(InlineKeyboardButton(text="🎰 Lucky Spin", callback_data="spin_now"), InlineKeyboardButton(text="🔗 Refer & Earn", callback_data="refer_info"))

    welcome_text = (
        f"🏎️ <b>RAJX BYPASS SYSTEM v5.0</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 <b>Welcome, {user_name}!</b>\n\n"
        f"💰 <b>Credits:</b> <code>{user_data.get('credits', 0)}</code>\n"
        f"👥 <b>Total Refers:</b> <code>{user_data.get('ref_count', 0)}</code>\n"
        f"👑 <b>Owner:</b> {DEV_HANDLE}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Link group mein bhejein aur 8-stage bypass dekhein!</i>"
    )
    await message.answer_photo(photo=WELCOME_PIC, caption=welcome_text, reply_markup=builder.as_markup())

# ==================== BYPASS (8 STAGES + IMAGE 2 FORMAT) ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if not await check_force_join(message.from_user.id): return
    if message.chat.type == "private":
        return await message.reply("❌ <b>Bypass Groups mein allowed hai!</b>", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ GROUP LINK", url=GROUP_LINK)).as_markup())

    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Starting Engine... ⚙️</b></blockquote>")
    
    stages = [
        ("█░░░░░░░░░░░  15%", "<b>Bypassing Cloudflare... ⛈️</b>"),
        ("███░░░░░░░░░  30%", "<b>Connecting Proxy... 🛰️</b>"),
        ("█████░░░░░░░  45%", "<b>Solving Captcha... 🤖</b>"),
        ("███████░░░░░  60%", "<b>Extracting Data... 🔓</b>"),
        ("█████████░░░  75%", "<b>Generating Link... ⚡</b>"),
        ("███████████░  90%", "<b>Finalizing... ✨</b>"),
        ("████████████  100%", "<b>Bypass Successful! ✅</b>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.6)
        try: await status_msg.edit_text(f"{bar}\n{text}")
        except: pass

    try:
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        
        bypassed_url = data.get("bypassed") or data.get("url") or data.get("result") or "Error in API"
        user_data = await get_user_data(message.from_user.id)

        # IMAGE 2 JESI CLEAN RESPONSE
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
        builder.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/visitpornhub"))
        builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal"))

        await status_msg.edit_text(res_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    except:
        await status_msg.edit_text("❌ <b>API Timeout!</b> Check URL or API Status.")

# ==================== SPIN & LEADERBOARD FIXES ====================

@dp.callback_query(F.data == "spin_now")
async def spin_logic(cb: types.CallbackQuery):
    user = await get_user_data(cb.from_user.id)
    last_spin = user.get("last_spin")
    
    if last_spin:
        if isinstance(last_spin, str): last_spin = datetime.fromisoformat(last_spin)
        if (datetime.now() - last_spin) < timedelta(days=1):
            return await cb.answer("⏳ Spin 24 ghante mein ek baar chalta hai!", show_alert=True)

    win = random.randint(2, 10)
    await users_db.update_one({"user_id": cb.from_user.id}, {"$inc": {"credits": win}, "$set": {"last_spin": datetime.now().isoformat()}})
    
    await cb.message.answer(f"🎯 <b>SPIN DONE!</b>\n\n🎉 <b>Reward:</b> +{win} Credits won!")
    await cb.answer()

@dp.callback_query(F.data == "leaderboard")
async def show_leaderboard(cb: types.CallbackQuery):
    if users_db is None: return await cb.answer("❌ Database Error!", show_alert=True)
    
    cursor = users_db.find().sort("ref_count", -1).limit(10)
    top_users = await cursor.to_list(length=10)
    
    text = "🏆 <b>TOP 10 REFER LEADERS</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, u in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
        text += f"{medal} {i}. {u.get('name', 'User')} — <b>{u.get('ref_count', 0)} Refers</b>\n"
    
    text += "━━━━━━━━━━━━━━━━━━━━\nInvite more to top the list!"
    await cb.message.answer(text)
    await cb.answer()

@dp.callback_query(F.data == "check_bal")
async def bal_cb(cb: types.CallbackQuery):
    d = await get_user_data(cb.from_user.id)
    await cb.answer(f"💰 Balance: {d.get('credits', 0)} Credits", show_alert=True)

@dp.callback_query(F.data == "refer_info")
async def refer_cb(cb: types.CallbackQuery):
    me = await bot.get_me()
    await cb.message.answer(f"🔗 <b>Your Invite Link:</b>\n<code>https://t.me/{me.username}?start={cb.from_user.id}</code>\n\nGet 5 Credits per active refer!")
    await cb.answer()

@dp.callback_query(F.data == "verify")
async def verify_cb(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified Success!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Pehle Join Karo Dono Channels!", show_alert=True)

# ==================== SERVER RUN ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Alive"

async def main():
    await init_db()
    Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
