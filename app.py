import os, asyncio, cloudscraper, datetime
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# ==================== 🛠️ CONFIGURATION ====================
TOKEN = os.environ.get("BOT_TOKEN")
API_URL = os.environ.get("NEW_API_URL") 
MONGO_URL = os.environ.get("MONGO_URL")

OWNER_ID = 8154922225 
DEV_HANDLE = "@rajfflive"

# --- 📢 LINKS (Change here to update everywhere) ---
CHANNELS = ["-1003898508261", "ffofcchat"] # IDs/Usernames
CHANNEL_1_LINK = "https://t.me/+HpoHOHMq0VpiYWVl" 
GROUP_LINK = "https://t.me/ffofcchat"
BUY_API_LINK = "https://t.me/visitpornhub"
WELCOME_PIC = "https://i.ibb.co/8L91y1CP/6ee42acc1338.jpg"

# ==================== BOT SETUP ====================
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
scraper = cloudscraper.create_scraper()

async def check_fj(u_id):
    if u_id == OWNER_ID: return True
    for c in CHANNELS:
        try:
            c_id = c if str(c).startswith("-100") else f"@{c}"
            m = await bot.get_chat_member(c_id, u_id)
            if m.status in ["left", "kicked", "restricted"]: return False
        except: return False
    return True

# ==================== HANDLERS ====================

@dp.message(Command("start"))
async def start(message: types.Message):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="‼️ BUY API ‼️", url=BUY_API_LINK, style="danger"))
    b.row(InlineKeyboardButton(text="⚡ USE HERE ⚡", url=GROUP_LINK, style="success"))
    
    caption = (
        "<blockquote>"
        f"🏎️ <b>RAJX BYPASS SYSTEM</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Welcome <b>{message.from_user.first_name}</b>!\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Send any supported link to bypass.\n"
        "━━━━━━━━━━━━━━━━━━━━"
        "</blockquote>"
    )
    await message.answer_photo(photo=WELCOME_PIC, caption=caption, reply_markup=b.as_markup())

@dp.message(F.text.startswith("http"))
async def handle_bypass(message: types.Message):
    # 1. Force Join Check
    if not await check_fj(message.from_user.id):
        b = InlineKeyboardBuilder()
        b.row(InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_1_LINK, style="primary"))
        b.row(InlineKeyboardButton(text="💬 Join Group", url=GROUP_LINK, style="primary"))
        b.row(InlineKeyboardButton(text="Verify ✅", callback_data="verify", style="success"))
        return await message.reply(
            "<blockquote>"
            "❗ <b>ACCESS DENIED!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "You must join our channels to use this bot.\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>", 
            reply_markup=b.as_markup()
        )

    # 2. 10-Stage Fast Processing
    status = await message.reply("░░░░░░░░░░░░░  0%\n<blockquote><b>Initializing... ⚙️</b></blockquote>")
    stages = [
        ("█░░░░░░░░░░░  10%", "Connecting..."), ("██░░░░░░░░░░  25%", "Bypassing Ads..."),
        ("████░░░░░░░░  40%", "Solving Captcha..."), ("██████░░░░░░  60%", "Extracting URL..."),
        ("████████████  100%", "Success! ✅")
    ]

    for bar, text in stages:
        await asyncio.sleep(0.2)
        try: await status.edit_text(f"{bar}\n<blockquote>{text}</blockquote>")
        except: pass

    # 3. API Logic & Detailed Response
    try:
        r = scraper.get(f"{API_URL}{message.text.strip()}", timeout=30).json()
        link = r.get("bypassed") or r.get("url") or r.get("result")
        if isinstance(link, dict): link = link.get("url")

        time_now = datetime.datetime.now().strftime("%I:%M %p | %d-%b")

        res_text = (
            "<blockquote>"
            "🏎️ <b>BYPASS SUCCESSFUL!</b> ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> {message.from_user.first_name}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>Original Link:</b>\n<code>{message.text[:40]}...</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🚀 <b>Bypassed Link:</b>\n<b>{link}</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🕒 <b>Time:</b> <code>{time_now}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 <b>Owner:</b> {DEV_HANDLE}\n"
            "━━━━━━━━━━━━━━━━━━━━"
            "</blockquote>"
        )
        await status.edit_text(res_text, disable_web_page_preview=True)
    except:
        await status.edit_text("❌ <b>API ERROR!</b>")

@dp.callback_query(F.data == "verify")
async def verify(cb: types.CallbackQuery):
    if await check_fj(cb.from_user.id):
        await cb.answer("✅ Verified!", show_alert=True)
        await cb.message.delete()
    else:
        await cb.answer("❌ Join channels first!", show_alert=True)

# ==================== RUNNER ====================
server = Flask(__name__)
@server.route('/')
def st(): return "Online"

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    Thread(target=lambda: server.run(host="0.0.0.0", port=10000), daemon=True).start()
    print("🤖 Bot Ready")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
