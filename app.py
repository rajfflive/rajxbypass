import os, asyncio, cloudscraper, random
from datetime import datetime, timedelta
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

# Database Variables
users_col = None
codes_col = None

async def init_db():
    global users_col, codes_col
    if MONGO_URL:
        try:
            # Short timeout to prevent Render hang
            client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
            db = client.bypass_bot
            users_col, codes_col = db.users, db.codes
            await client.server_info()
            print("✅ DB Connected")
        except: print("⚠️ DB Connection Failed - Running in Offline Mode")

# ==================== HELPERS ====================

async def get_user_data(u_id, name="User"):
    if users_col is None: return {"balance": 2, "name": name}
    user = await users_col.find_one({"user_id": u_id})
    if not user:
        user = {"user_id": u_id, "name": name, "balance": 2, "refer_count": 0, "last_spin": None}
        await users_col.insert_one(user)
    return user

async def check_fj(u_id):
    if u_id == OWNER_ID: return True
    for c in CHANNELS:
        try:
            m = await bot.get_chat_member(f"@{c}", u_id)
            if m.status in ["left", "kicked"]: return False
        except: continue
    return True

# ==================== UI MENUS ====================

def main_menu_btn(u_id, ref_link):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🎰 Daily Spin", callback_data="spin"),
          InlineKeyboardButton(text="💰 Balance", callback_data="bal"), style="success")
    b.row(InlineKeyboardButton(text="🏆 Leaderboard", callback_data="lb"),
          InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK), style="danger")
    b.row(InlineKeyboardButton(text="⚡ USE IN GROUP ⚡", url=GROUP_LINK), style="success")
    return b.as_markup()

# ==================== HANDLERS ====================

@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject):
    u_id = message.from_user.id
    # Refer Logic
    if users_col and command.args:
        ref_id = int(command.args)
        if ref_id != u_id and not await users_col.find_one({"user_id": u_id}):
            await users_col.update_one({"user_id": ref_id}, {"$inc": {"balance": 2, "refer_count": 1}})
            try: await bot.send_message(ref_id, "<blockquote>🎁 <b>+2 Credits Received from Referral!</b></blockquote>")
            except: pass

    user = await get_user_data(u_id, message.from_user.first_name)
    ref_link = f"https://t.me{(await bot.get_me()).username}?start={u_id}"
    bal = "∞" if u_id == OWNER_ID else user.get('balance', 2)

    await message.answer_photo(photo=WELCOME_PIC, caption=(
        "<blockquote>"
        f"🏎️ <b>RAJX BYPASS SYSTEM</b>\n\n"
        f"💰 <b>Wallet:</b> {bal} Credits\n"
        f"🔗 <b>Invite:</b> <code>{ref_link}</code>\n\n"
        "Bypass costs 1 Credit. New users get 2 free!"
        "</blockquote>"
    ), reply_markup=main_menu_btn(u_id, ref_link))

@dp.callback_query(F.data == "spin")
async def spin_cb(cb: types.CallbackQuery):
    u_id = cb.from_user.id
    user = await get_user_data(u_id)
    now = datetime.now()
    if user.get("last_spin") and now < user.get("last_spin") + timedelta(days=1):
        return await cb.answer("⏳ Come back tomorrow!", show_alert=True)

    await cb.message.edit_caption(caption="🎰 <b>Spinning...</b>\n<blockquote>[ 💎 | 🍒 | 🔔 ]</blockquote>")
    await asyncio.sleep(1)
    win = random.randint(1, 5)
    if users_col: await users_col.update_one({"user_id": u_id}, {"$inc": {"balance": win}, "$set": {"last_spin": now}})
    await cb.answer(f"🎉 Won {win} Credits!", show_alert=True)
    await start_cmd(cb.message, CommandObject(args=None))

@dp.message(Command("gen"), F.from_user.id == OWNER_ID)
async def gen_code(message: types.Message, command: CommandObject):
    if not codes_col or not command.args: return
    code = f"RAJX-{random.randint(100,999)}"
    await codes_col.insert_one({"code": code, "amount": int(command.args), "used": False})
    await message.reply(f"<blockquote>Code: <code>{code}</code>\nValue: {command.args}</blockquote>")

@dp.message(F.text.startswith("http"))
async def bypass_handler(message: types.Message):
    u_id = message.from_user.id
    user = await get_user_data(u_id)

    # Force Join - Group Only
    if message.chat.type != "private" and not await check_fj(u_id):
        b = InlineKeyboardBuilder().button(text="📢 Join Channel", url=f"https://t.merajxcheats").as_markup()
        return await message.reply("<blockquote>❗ <b>Join Channel First!</b></blockquote>", reply_markup=b)

    # Credits Check
    if u_id != OWNER_ID and user.get("balance", 0) < 1:
        return await message.reply("<blockquote>⚠️ <b>NO CREDITS!</b>\nInvite friends to earn more.</blockquote>")

    # Private Restriction
    if message.chat.type == "private" and u_id != OWNER_ID:
        return await message.reply("<blockquote>❌ <b>USE IN GROUP!</b></blockquote>")

    status = await message.reply("⏳ <b>Processing...</b>")
    try:
        r = scraper.get(f"{API_URL}{message.text.strip()}", timeout=20).json()
        link = r.get("bypassed") or r.get("url") or r.get("result")
        
        if u_id != OWNER_ID and users_col:
            await users_col.update_one({"user_id": u_id}, {"$inc": {"balance": -1}})

        res = (
            "<blockquote>"
            "🏎️ <b>BYPASS SUCCESSFUL!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🚀 <b>Link:</b> <b>{link}</b>\n\n"
            f"💰 <b>Wallet:</b> {'∞' if u_id == OWNER_ID else user.get('balance', 0)-1} Credits\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        b = InlineKeyboardBuilder().button(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger").as_markup()
        await status.edit_text(res, reply_markup=b)
    except: await status.edit_text("<blockquote>❌ <b>API ERROR!</b></blockquote>")

# ==================== RUNNER ====================
app = Flask(__name__)
@app.route('/')
def h(): return "OK"

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=lambda: app.run(host="0.0.0.0", port=10000), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
