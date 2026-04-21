import os, asyncio, cloudscraper, datetime, pytz, json
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, ReactionTypeEmoji
from motor.motor_asyncio import AsyncIOMotorClient

# ==================== 🛠️ CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN")
API_URL = os.environ.get("NEW_API_URL") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = int(os.environ.get("OWNER_ID", "8154922225"))
DEV_HANDLE = "@rajfflive"

# --- 📢 LINKS ---
CHANNELS = ["-1003898508261", "ffofcchat"] 
CHANNEL_LINK = "https://t.me/+HpoHOHMq0VpiYWVl" 
GROUP_LINK = "https://t.me/ffofcchat"
BUY_API_LINK = "https://t.me/visitpornhub"
WELCOME_PIC = "https://i.ibb.co/8L91y1CP/6ee42acc1338.jpg"

# ==================== DATABASE & BOT SETUP ====================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()
users_col, groups_col = None, None

async def init_db():
    global users_col, groups_col
    if MONGO_URL:
        try:
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            db = client.bypass_bot
            users_col, groups_col = db.users, db.groups
            await client.admin.command('ping')
            print("✅ [DB] MongoDB Connected!")
        except Exception as e:
            print(f"❌ [DB] Connection Failed: {e}")
    else:
        print("⚠️ [DB] MONGO_URL not set!")

async def save_user(user: types.User):
    if not users_col: return
    await users_col.update_one(
        {"user_id": user.id},
        {"$set": {"name": user.first_name, "username": user.username or "N/A", "joined": datetime.datetime.utcnow()}},
        upsert=True
    )

async def save_group(chat: types.Chat):
    if not groups_col: return
    await groups_col.update_one(
        {"group_id": chat.id},
        {"$set": {"title": chat.title or "Unknown", "username": chat.username or "N/A", "joined": datetime.datetime.utcnow()}},
        upsert=True
    )

async def check_fj(u_id):
    if u_id == OWNER_ID: return True
    for c in CHANNELS:
        try:
            c_id = c if str(c).startswith("-100") else f"@{c}"
            m = await bot.get_chat_member(c_id, u_id)
            if m.status in ["left", "kicked", "restricted"]: return False
        except: return False
    return True

# ==================== 👑 OWNER COMMANDS ====================

@dp.message(Command("stats"), F.from_user.id == OWNER_ID)
async def cmd_stats(message: types.Message):
    u = await users_col.count_documents({}) if users_col else 0
    g = await groups_col.count_documents({}) if groups_col else 0
    await message.reply(f"📊 <b>Stats:</b>\nUsers: {u}\nGroups: {g}")

@dp.message(Command("broadcast"), F.from_user.id == OWNER_ID)
async def cmd_broadcast(message: types.Message):
    if not message.reply_to_message: return await message.reply("❌ Reply to a message!")
    users = await users_col.find().to_list(None) if users_col else []
    groups = await groups_col.find().to_list(None) if groups_col else []
    targets = list(set([u['user_id'] for u in users] + [g['group_id'] for g in groups]))
    sent, failed = 0, 0
    for t_id in targets:
        try: 
            await bot.copy_message(t_id, message.chat.id, message.reply_to_message.message_id)
            sent += 1
        except: failed += 1
    await message.reply(f"📢 <b>Broadcast Done!</b> Sent: {sent} | Failed: {failed}")

# ==================== 🏎️ MAIN LOGIC ====================

@dp.message(Command("start"))
async def start(message: types.Message):
    await save_user(message.from_user)
    if message.chat.type in ["group", "supergroup"]: await save_group(message.chat)
    
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK))
    b.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK))
    await message.answer_photo(photo=WELCOME_PIC, caption="<blockquote>🏎️ <b>RAJX BYPASS SYSTEM</b>\n\nWelcome! Send link to bypass.</blockquote>", reply_markup=b.as_markup())

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    await save_user(message.from_user)
    if message.chat.type in ["group", "supergroup"]: await save_group(message.chat)

    try: await message.react([ReactionTypeEmoji(emoji="👀")])
    except: pass

    if not await check_fj(message.from_user.id):
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="Join Channel 📢", url=CHANNEL_LINK))
        b.row(InlineKeyboardButton(text="Join Group 💬", url=GROUP_LINK))
        b.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify"))
        return await message.reply("❗ <b>ACCESS DENIED! Join BOTH our channel and group.</b>", reply_markup=b.as_markup())

    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK))
        return await message.reply("❌ <b>PRIVATE BYPASS DISABLED!</b>\n\nUse our official group.", reply_markup=b.as_markup())

    status = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    
    stages = [("███░░░░░░░░░  30%", "Bypassing..."), ("████████░░░░  70%", "Decrypting..."), ("████████████  100%", "Success! ✅")]
    for bar, text in stages:
        await asyncio.sleep(0.2)
        try: await status.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    try:
        response = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30).json()
        res_data = response.get("result", {})
        
        link = res_data.get("bypassed", "Error")
        time_val = res_data.get("time_taken", "N/A")
        usage_val = res_data.get("usage_count", "N/A")

        IST = pytz.timezone('Asia/Kolkata')
        time_now = datetime.datetime.now(IST).strftime("%I:%M %p | %d-%b")

        res_text = (
            "<blockquote>"
            "🏎️ <b>BYPASS SUCCESSFUL!</b> ⚡\n\n"
            f"👤 <b>User:</b> {message.from_user.first_name}\n"
            f"🔗 <b>Original:</b>\n<code>{message.text.strip()[:30]}...</code>\n\n"
            f"🚀 <b>Bypassed Link:</b>\n{link}\n\n"
            f"⚡ <b>Time:</b> <code>{time_val}</code> | 📊 <b>Usage:</b> <code>{usage_val}</code>\n"
            f"🕒 <b>Date:</b> <code>{time_now}</code>\n"
            f"👑 <b>Owner:</b> {DEV_HANDLE}"
            "</blockquote>"
        )
        
        b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK))
        await status.edit_text(res_text, reply_markup=b.as_markup(), disable_web_page_preview=True)
        try: await message.react([ReactionTypeEmoji(emoji="💯")])
        except: pass
    except Exception as e:
        await status.edit_text(f"❌ <b>API ERROR!</b>\n<code>{str(e)[:50]}</code>")

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_fj(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else:
        await cb.answer("❌ Join BOTH first!", show_alert=True)

# ==================== RUNNER ====================
server = Flask(__name__)

@server.route('/')
def st(): return "Bot is Running"

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=lambda: server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    print("🚀 Bot Started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
