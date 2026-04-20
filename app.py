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

# --- Database ---
users_db = None
async def init_db():
    global users_db
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            users_db = client.bypass_bot.users
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
    builder.row(InlineKeyboardButton(text="‼️ BUY PAID API ‼️", url="https://t.me/rajxcheats", style="danger"))
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

# ==================== BYPASS (CLEAN RESPONSE FIX) ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    if not await check_force_join(message.from_user.id): return
    if message.chat.type == "private":
        return await message.reply("❌ Groups Only!", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ GROUP LINK", url=GROUP_LINK, style="success")).as_markup())

    status_msg = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Starting Engine... ⚙️</b></blockquote>")
    
    # 6-7 Processing Stages
    stages = [
        ("██░░░░░░░░░░░  20%", "<b>Bypassing Ads... ⛈️</b>"),
        ("████░░░░░░░░░  40%", "<b>Connecting Proxy... 🛰️</b>"),
        ("██████░░░░░░░  60%", "<b>Decrypting Link... 🔓</b>"),
        ("████████░░░░░  80%", "<b>Generating URL... ⚡</b>"),
        ("█████████████  100%", "<b>Bypass Done! ✅</b>")
    ]
    
    for bar, text in stages:
        await asyncio.sleep(0.6)
        try: await status_msg.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    try:
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30)
        data = response.json()
        
        # --- PARSING JSON TO CLEAN TEXT ---
        # Agar response JSON hai toh usme se 'bypassed' key uthayega
        bypassed_url = data.get("bypassed") or data.get("url") or data.get("result")
        
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
        builder.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url="https://t.me/rajxcheats", style="danger"))
        builder.row(InlineKeyboardButton(text="💰 Balance", callback_data="check_bal", style="success"))

        await status_msg.edit_text(res_text, reply_markup=builder.as_markup(), disable_web_page_preview=True)
    except:
        await status_msg.edit_text("❌ <b>API Timeout!</b> Link invalid ya API down hai.")

# ==================== CALLBACKS (A TO Z) ====================

@dp.callback_query(F.data == "check_bal")
async def bal_cb(cb: types.CallbackQuery):
    data = await get_user_data(cb.from_user.id)
    await cb.answer(f"💰 Balance: {data.get('credits', 0)} Credits", show_alert=True)

@dp.callback_query(F.data == "spin_now")
async def spin_logic(cb: types.CallbackQuery):
    user = await get_user_data(cb.from_user.id)
    last_spin = user.get("last_spin")
    if last_spin and (datetime.now() - datetime.fromisoformat(last_spin)) < timedelta(days=1):
        return await cb.answer("⏳ Ek din mein ek hi baar spin karein!", show_alert=True)

    win = random.randint(2, 10)
    await users_db.update_one({"user_id": cb.from_user.id}, {"$inc": {"credits": win}, "$set": {"last_spin": datetime.now().isoformat()}})
    await cb.message.answer(f"🎰 <b>LUCKY SPIN</b>\n\n🎉 Congrats! You won +{win} Credits.")
    await cb.answer()

@dp.callback_query(F.data == "leaderboard")
async def show_lb(cb: types.CallbackQuery):
    if not users_db: return await cb.answer("DB Error!")
    top = await users_db.find().sort("ref_count", -1).limit(10).to_list(10)
    text = "🏆 <b>REFER LEADERBOARD</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {u.get('name')} — {u.get('ref_count')} Refers\n"
    await cb.message.answer(text)
    await cb.answer()

@dp.callback_query(F.data == "refer_info")
async def ref_cb(cb: types.CallbackQuery):
    me = await bot.get_me()
    await cb.message.answer(f"🔗 <b>Invite Link:</b>\n<code>https://t.me/{me.username}?start={cb.from_user.id}</code>")
    await cb.answer()

@dp.callback_query(F.data == "verify")
async def verify_cb(cb: types.CallbackQuery):
    if await check_force_join(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Dono Channels Join Karein!", show_alert=True)

# ==================== ADMIN COMMANDS ====================

@dp.message(Command("stats"), F.from_user.id == OWNER_ID)
async def cmd_stats(message: types.Message):
    count = await users_db.count_documents({})
    await message.reply(f"📊 Total Users: {count}")

# ==================== SERVER ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Live"

async def main():
    await init_db()
    Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
