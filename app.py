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

# --- Database ---
users_col = None
codes_col = None

async def init_db():
    global users_col, codes_col
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client.bypass_bot
        users_col = db.users
        codes_col = db.codes
        print("✅ Advanced System Live")
    except: print("⚠️ DB Connection Failed")

# ==================== OWNER TOOLS (NO BUTTONS) ====================

@dp.message(Command("gen"), F.from_user.id == OWNER_ID)
async def cmd_gen(message: types.Message, command: CommandObject):
    if not command.args: return await message.reply("Usage: /gen [amount]")
    code = f"RAJX-{random.randint(100, 999)}-{random.randint(100, 999)}"
    await codes_col.insert_one({"code": code, "amount": int(command.args), "used": False})
    await message.reply(f"<blockquote>💎 <b>CODE GENERATED</b>\nCode: <code>{code}</code>\nValue: {command.args} Credits</blockquote>")

@dp.message(Command("stats"), F.from_user.id == OWNER_ID)
async def cmd_stats(message: types.Message):
    u_count = await users_col.count_documents({})
    await message.reply(f"<blockquote>📈 <b>STATS</b>\nTotal Users: {u_count}</blockquote>")

# ==================== HELPERS ====================

async def get_user(u_id, name="User"):
    user = await users_col.find_one({"user_id": u_id})
    if not user:
        user = {"user_id": u_id, "name": name, "balance": 2, "refer_count": 0, "last_spin": None}
        await users_col.insert_one(user)
    return user

async def check_fj(u_id):
    for c in CHANNELS:
        try:
            m = await bot.get_chat_member(f"@{c}", u_id)
            if m.status in ["left", "kicked"]: return False
        except: continue
    return True

def get_main_menu(u_id, ref_link):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🎰 Daily Spin", callback_data="spin_now", style="success"))
    b.row(InlineKeyboardButton(text="🏆 Leaderboard", callback_data="show_lb"),
          InlineKeyboardButton(text="💰 My Balance", callback_data="show_bal", style="success"))
    b.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger"))
    b.row(InlineKeyboardButton(text="⚡ USE IN GROUP ⚡", url=GROUP_LINK, style="success"))
    return b.as_markup()

# ==================== SYSTEM HANDLERS ====================

@dp.message(Command("start"))
async def start(message: types.Message, command: CommandObject):
    u_id = message.from_user.id
    user_exists = await users_col.find_one({"user_id": u_id})
    
    if not user_exists and command.args:
        ref_id = int(command.args)
        if ref_id != u_id:
            await users_col.update_one({"user_id": ref_id}, {"$inc": {"balance": 2, "refer_count": 1}})
            try: await bot.send_message(ref_id, "<blockquote>🎉 <b>Referral Success!</b>\nYou earned 2 Credits.</blockquote>")
            except: pass

    user = await get_user(u_id, message.from_user.first_name)
    ref_link = f"https://t.me{(await bot.get_me()).username}?start={u_id}"
    bal = '∞' if u_id == OWNER_ID else user.get('balance', 0)

    msg = (
        "<blockquote>"
        f"🏎️ <b>RAJX BYPASS SYSTEM</b>\n\n"
        f"💰 <b>Wallet:</b> {bal} Credits\n"
        f"🔗 <b>Invite:</b> <code>{ref_link}</code>\n\n"
        "Earn credits via Spin or Invites to bypass links!"
        "</blockquote>"
    )
    await message.answer_photo(photo=WELCOME_PIC, caption=msg, reply_markup=get_main_menu(u_id, ref_link))

@dp.callback_query(F.data == "show_bal")
async def cb_bal(cb: types.CallbackQuery):
    user = await get_user(cb.from_user.id)
    bal = '∞' if cb.from_user.id == OWNER_ID else user.get('balance', 0)
    await cb.answer(f"💰 Balance: {bal} Credits", show_alert=True)

@dp.callback_query(F.data == "spin_now")
async def cb_spin(cb: types.CallbackQuery):
    user = await get_user(cb.from_user.id)
    now = datetime.now()
    if user.get("last_spin") and now < user.get("last_spin") + timedelta(days=1):
        rem = (user.get("last_spin") + timedelta(days=1)) - now
        return await cb.answer(f"⏳ Cooldown! Try in {rem.seconds // 3600}h.", show_alert=True)

    # Animation
    await cb.message.edit_caption(caption="🎰 <b>Spinning...</b>\n<blockquote>[ 🍎 | 🍋 | 🍒 ]</blockquote>")
    await asyncio.sleep(1)
    
    win = random.randint(1, 5)
    await users_col.update_one({"user_id": cb.from_user.id}, {"$inc": {"balance": win}, "$set": {"last_spin": now}})
    await cb.answer(f"🎰 JACKPOT! You won {win} Credits!", show_alert=True)
    await start(cb.message, CommandObject(args=None))

@dp.callback_query(F.data == "show_lb")
async def cb_lb(cb: types.CallbackQuery):
    top = await users_col.find().sort("refer_count", -1).limit(5).to_list(5)
    text = "<blockquote>🏆 <b>TOP REFERRERS</b>\n\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {u.get('name', 'User')} - {u.get('refer_count', 0)} Refers\n"
    text += "</blockquote>"
    b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔙 Back", callback_data="back_start", style="danger"))
    await cb.message.edit_caption(caption=text, reply_markup=b.as_markup())

@dp.callback_query(F.data == "back_start")
async def cb_back(cb: types.CallbackQuery):
    await start(cb.message, CommandObject(args=None))

# ==================== BYPASS LOGIC ====================

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    u_id = message.from_user.id
    user = await get_user(u_id, message.from_user.first_name)

    # Force Join - Group Only
    if message.chat.type in ["group", "supergroup"]:
        if not await check_fj(u_id):
            b = InlineKeyboardBuilder()
            b.row(InlineKeyboardButton(text="📢 Join Channel", url=f"https://t.merajxcheats", style="danger"))
            b.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify", style="success"))
            return await message.reply("<blockquote>❗ <b>JOIN CHANNELS TO BYPASS!</b></blockquote>", reply_markup=b.as_markup())

    # Credit Check
    if u_id != OWNER_ID and user.get("balance", 0) < 1:
        ref = f"https://t.me{(await bot.get_me()).username}?start={u_id}"
        return await message.reply(f"<blockquote>⚠️ <b>NO CREDITS!</b>\nInvite friends to earn.\n\n🔗 <code>{ref}</code></blockquote>")

    # Private Check
    if message.chat.type == "private" and u_id != OWNER_ID:
        b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="⚡ USE IN GROUP ⚡", url=GROUP_LINK, style="success"))
        return await message.reply("<blockquote>❌ <b>PRIVATE MODE OFF!</b></blockquote>", reply_markup=b.as_markup())

    status = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing Engine... ⚙️</b></blockquote>")
    stages = [("██████░░░░░░  50%", "<b>Processing... 🚀</b>"), ("████████████  100%", "<b>Success! ✅</b>")]
    for bar, txt in stages:
        await asyncio.sleep(0.5); await status.edit_text(f"{bar}\n<blockquote>{txt}</blockquote>")

    try:
        r = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30).json()
        link = r.get("bypassed") or r.get("url") or r.get("result")
        
        cost_txt = "Unlimited"
        if u_id != OWNER_ID:
            await users_col.update_one({"user_id": u_id}, {"$inc": {"balance": -1}})
            cost_txt = f"{user.get('balance', 0) - 1} Credits"

        res = (
            "<blockquote>"
            "🏎️ <b>BYPASS SUCCESSFUL!</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 <b>Original:</b> <code>{message.text[:20]}...</code>\n\n"
            f"🚀 <b>Bypassed Link:</b>\n<b>{link}</b>\n\n"
            f"💰 <b>Wallet:</b> {cost_txt}\n"
            f"👑 <b>Owner:</b> {DEV_HANDLE}\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        b = InlineKeyboardBuilder().row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger"))
        await status.edit_text(res, reply_markup=b.as_markup(), disable_web_page_preview=True)
    except: await status.edit_text("<blockquote>❌ <b>API ERROR!</b></blockquote>")

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_fj(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else: await cb.answer("❌ Join both channels first!", show_alert=True)

# ==================== RUNNER ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Live"

async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
