import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from PIL import ImageGrab
import os
from datetime import datetime


BOT_TOKEN = "7901483672:AAG7JUJINcCuSvpEJ-1YUTs_52clD2H3iDE"
ALLOWED_USER_ID = 1010955964

BACKEND_URL = "http://localhost:5000"
API_KEY = "my_secure_key"

# ---------------- SECURITY ----------------
async def authorize(update: Update) -> bool:
    user = update.effective_user
    msg = update.effective_message

    if not user or user.id != ALLOWED_USER_ID:
        if msg:
            await msg.reply_text("❌ Unauthorized")
        return False
    return True

# ---------------- COMMANDS ----------------
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorize(update):
        return

    msg = update.effective_message
    if msg:
        await msg.reply_text(
            "/lock\n"
            "/shutdown\n"
            "/restart\n"
            "/ls\n"
            "/cmd <command>\n"
            "/screenshot\n"
            "/get <filename>"
        )

async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorize(update):
        return

    msg = update.effective_message
    try:
        requests.post(f"{BACKEND_URL}/action/lock", data={"api_key": API_KEY})
        if msg:
            await msg.reply_text("🔒 PC Locked")
    except Exception as e:
        if msg:
            await msg.reply_text(f"Error: {e}")

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorize(update):
        return

    msg = update.effective_message
    try:
        requests.post(f"{BACKEND_URL}/action/shutdown", data={"api_key": API_KEY})
        if msg:
            await msg.reply_text("⏻ Shutdown initiated")
    except Exception as e:
        if msg:
            await msg.reply_text(f"Error: {e}")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorize(update):
        return

    msg = update.effective_message
    try:
        requests.post(f"{BACKEND_URL}/action/restart", data={"api_key": API_KEY})
        if msg:
            await msg.reply_text("🔄 Restart initiated")
    except Exception as e:
        if msg:
            await msg.reply_text(f"Error: {e}")

async def ls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorize(update):
        return

    msg = update.effective_message
    try:
        res = requests.get(f"{BACKEND_URL}/files", params={"api_key": API_KEY})
        files = res.json().get("files", [])

        if msg:
            await msg.reply_text("\n".join(files) if files else "No files found")
    except Exception as e:
        if msg:
            await msg.reply_text(f"Error: {e}")

async def cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorize(update):
        return

    msg = update.effective_message

    if not context.args:
        if msg:
            await msg.reply_text("Usage: /cmd <command>")
        return

    command = " ".join(context.args)

    try:
        res = requests.post(
            f"{BACKEND_URL}/terminal",
            data={"cmd": command, "api_key": API_KEY}
        )
        output = res.json().get("output", "Error")

        if msg:
            await msg.reply_text(output[:4000])  # Telegram limit safe
    except Exception as e:
        if msg:
            await msg.reply_text(f"Error: {e}")

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorize(update):
        return

    msg = update.effective_message

    try:
        # 📁 Folder create (if not exists)
        folder = "Files"
        os.makedirs(folder, exist_ok=True)

        # 🕒 Unique filename (no overwrite)
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join(folder, filename)

        # 📸 Capture screenshot
        img = ImageGrab.grab()
        img.save(path)

        # 📤 Send to Telegram
        if msg:
            with open(path, "rb") as f:
                await msg.reply_photo(photo=f)

        # ❌ (Optional) remove file → comment this if you want to KEEP files
        # os.remove(path)

    except Exception as e:
        if msg:
            await msg.reply_text(f"Error: {e}")
BASE_DIR = "C:/Users/ASUS/Downloads"   # same as backend

async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await authorize(update):
        return

    msg = update.effective_message

    if not context.args:
        if msg:
            await msg.reply_text("Usage: /get filename")
        return

    filename = " ".join(context.args)
    filepath = os.path.join(BASE_DIR, filename)

    try:
        if os.path.exists(filepath):
            if msg:
                await msg.reply_document(open(filepath, "rb"))
        else:
            if msg:
                await msg.reply_text("❌ File not found")
    except Exception as e:
        if msg:
            await msg.reply_text(f"Error: {e}")

# ---------------- ERROR HANDLER ----------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("lock", lock))
    app.add_handler(CommandHandler("shutdown", shutdown))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("ls", ls))
    app.add_handler(CommandHandler("cmd", cmd))
    app.add_handler(CommandHandler("screenshot", screenshot))
    app.add_handler(CommandHandler("get", get_file))

    app.add_error_handler(error_handler)

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()