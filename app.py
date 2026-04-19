import os
import time
import cloudscraper
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from pymongo import MongoClient
from threading import Thread

# ==================== CONFIGURATION ====================
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))

# New Paid API & Pure Branding
PAID_API = "https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key=ccd271950940c3045784da88a1d3276e"
CHANNELS = ["ffofcchat", "rajxcheats"] 
DEV_HANDLE = "@rajxcheats"

app = Client("RajxBypass", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
scraper = cloudscraper.create_scraper()

# ==================== HELPERS ====================
async def check_force_join(client, user_id):
    for channel in CHANNELS:
        try:
            await client.get_chat_member(channel, user_id)
        except UserNotParticipant:
            return False
        except Exception:
            continue
    return True

# ==================== COMMANDS ====================
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    welcome_text = (
        f"🚀 **Hello {message.from_user.first_name}!**\n\n"
        "Welcome to **Rajx Bypass Bot**.\n"
        "The fastest link bypasser powered by **@rajxcheats**.\n\n"
        "Just send me your shortlink and see the magic! ✨"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Updates", url="https://t.me/rajxcheats")],
        [InlineKeyboardButton("➕ Add to Group", url=f"http://t.me/{app.me.username}?startgroup=true")]
    ])
    await message.reply_text(welcome_text, reply_markup=buttons)

# ==================== BYPASS HANDLER WITH LOADING ====================
@app.on_message(filters.text & filters.private)
async def handle_bypass(client, message):
    user_id = message.from_user.id
    link = message.text.strip()

    if not link.startswith("http"):
        return

    # Force Join Check
    if not await check_force_join(client, user_id):
        buttons = [[InlineKeyboardButton(f"Join @{c}", url=f"https://t.me/{c}")] for c in CHANNELS]
        return await message.reply_text("❌ **Join our channels first to bypass!**", reply_markup=InlineKeyboardMarkup(buttons))

    # --- CUSTOM LOADING ANIMATION ---
    loading_msg = await message.reply_text("░░░░░░░░░░░░░  0%\n**ꜱᴇᴀʀᴄʜɪɴɢ ⚡**")
    
    # Progress Simulation (Fast)
    stages = [
        ("██░░░░░░░░░░░  15%\n**ꜰᴇᴛᴄʜɪɴɢ ɪɴꜰᴏ ⚡**"),
        ("█████░░░░░░░░  35%\n**ʙʏᴘᴀssɪɴɢ ʟɪɴᴋ ⚡**"),
        ("█████████░░░░  68%\n**ɢᴇᴛᴛɪɴɢ ʀᴇsᴜʟᴛ ⚡**"),
        ("█████████████  100%\n**ᴅᴏɴᴇ ✅**")
    ]
    
    for stage in stages:
        await loading_msg.edit_text(stage)
        time.sleep(0.3) # Isko adjust kar sakte ho speed ke liye

    start_time = time.perf_counter()

    try:
        # API Call
        response = scraper.get(f"{PAID_API}&link={link}", timeout=25)
        data = response.json()
        bypassed_url = data.get("bypassed_url", data.get("result", "API Error!"))
        
        time_taken = round(time.perf_counter() - start_time, 2)

        # Professional Branded Result
        ui_text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏎️ **RAJX BYPASS BOT** ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔗 **Original :**\n{link}\n\n"
            f"🚀 **Bypassed :**\n{bypassed_url}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🕒 **Time Taken :** `{time_taken}s`\n"
            f"👤 **User :** {message.from_user.first_name}\n"
            f"⚙️ **Status :** `Success`\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 **Owner :** {DEV_HANDLE} ✅"
        )
        
        await loading_msg.edit_text(ui_text, disable_web_page_preview=True)

    except Exception as e:
        await loading_msg.edit_text(f"❌ **Error:** `{str(e)}`")

# ==================== RUN ====================
server = Flask(__name__)
@server.route('/')
def status(): return "✅ Rajx Bot Alive"

if __name__ == "__main__":
    Thread(target=lambda: server.run(host="0.0.0.0", port=8080)).start()
    app.run()
