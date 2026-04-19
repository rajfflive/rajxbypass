import os
import time
import cloudscraper
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from threading import Thread

# ==================== CONFIGURATION ====================
# Ye saari details Render ke Environment Variables mein daal dena
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

# Aapki New Paid API
PAID_API = "https://detect-shirt-generations-prepaid.trycloudflare.com/bypass?key=ccd271950940c3045784da88a1d3276e"

CHANNELS = ["ffofcchat", "rajxcheats"] 
DEV_HANDLE = "@rajxcheats"

app = Client("RajxBypass", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
scraper = cloudscraper.create_scraper()

# ==================== RENDER LIVE FIX (PORT BINDING) ====================
server = Flask(__name__)

@server.route('/')
def status():
    return "✅ Rajx Bypass Bot is Live and Running!"

def run_server():
    # Render hamesha environment se PORT uthata hai, default 10000 rakha hai
    port = int(os.environ.get("PORT", 10000))
    print(f"📡 Web Server started on port {port}")
    server.run(host="0.0.0.0", port=port)

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

# ==================== BYPASS HANDLER ====================
@app.on_message(filters.text & filters.private)
async def handle_bypass(client, message):
    user_id = message.from_user.id
    link = message.text.strip()

    if not link.startswith("http"):
        return

    # 1. Force Join Check
    if not await check_force_join(client, user_id):
        buttons = [[InlineKeyboardButton(f"Join @{c}", url=f"https://t.me/{c}")] for c in CHANNELS]
        return await message.reply_text(
            "❌ **Access Denied!**\n\nPlease join our channels to use this premium bypasser.",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # 2. Loading Animation (Percentage UI)
    status_msg = await message.reply_text("░░░░░░░░░░░░░  0%\n**ꜱᴇᴀʀᴄʜɪɴɢ ⚡**")
    time.sleep(0.5)
    await status_msg.edit_text("█████████░░░░  68%\n**ɢᴇᴛᴛɪɴɢ ʀᴇsᴜʟᴛ ⚡**")
    
    start_time = time.perf_counter()

    try:
        # API Call
        response = scraper.get(f"{PAID_API}&link={link}", timeout=25)
        data = response.json()
        
        # Clean Link Extract (JSON se value nikalna)
        bypassed_url = data.get("bypassed", data.get("bypassed_url", "Link Not Found"))
        
        time_taken = round(time.perf_counter() - start_time, 2)

        # 3. Final Professional UI (Line Separated)
        ui_text = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏎️ **RAJX BYPASS BOT** ⚡\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔗 **Original :**\n"
            f"{link}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 **Bypassed :**\n"
            f"{bypassed_url}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🕒 **Time Taken :** `{time_taken}s`\n"
            f"👤 **User :** {message.from_user.first_name}\n"
            "⚙️ **Status :** `Success`\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👑 **Owner :** {DEV_HANDLE} ✅"
        )
        
        await status_msg.edit_text(ui_text, disable_web_page_preview=True)

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** `{str(e)}`")

# ==================== STARTING POINT ====================
if __name__ == "__main__":
    # Flask ko thread mein chalana zaroori hai Render ke liye
    t = Thread(target=run_server)
    t.daemon = True
    t.start()
    
    print("🚀 Bot is starting...")
    app.run()
