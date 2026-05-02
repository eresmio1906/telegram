import os
import time
import hmac
import hashlib
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

# ✅ Fix 1: Ensure SECRET is always bytes
TOKEN: str = os.environ.get("BOT_TOKEN", "8041461190:AAF2dORrqEUW2euLE33whRUNqev3y6pLPZI")
BACKEND_URL: str = os.environ.get("BACKEND_URL", "http://127.0.0.1:5000/terminal")
SECRET: bytes = os.environ.get("API_SECRET", "super_secret_key").encode()  # .encode() ensures bytes

# Allowed users
ALLOWED_USERS: set[int] = {1010955964}

def sign(cmd: str, ts: str) -> str:
    return hmac.new(SECRET, f"{cmd}:{ts}".encode(), hashlib.sha256).hexdigest()

async def request_backend(data: dict) -> dict:
    ts = str(int(time.time()))
    payload = data.get("action") or data.get("cmd", "")
    data["ts"] = ts
    data["sig"] = sign(payload, ts)
    async with httpx.AsyncClient() as client:
        res = await client.post(BACKEND_URL, data=data, timeout=15)
        return res.json()

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /exec <command> messages"""
    
    # ✅ Fix 2: Proper None checks
    if update.message is None:
        return
    
    user = update.effective_user
    if user is None or user.id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized access")
        return

    # ✅ Fix 3: Check if text exists
    if update.message.text is None:
        return
    
    # Extract command after /exec
    text = update.message.text
    if text is None:
        return

    parts = text.split(maxsplit=2)
    if len(parts) < 2:
        await update.message.reply_text("⚠️ Usage: /exec [cmd|powershell] <command>")
        return

    shell = "powershell"
    if parts[1].lower() in {"cmd", "powershell", "ps"}:
        if len(parts) < 3:
            await update.message.reply_text("⚠️ Usage: /exec [cmd|powershell] <command>")
            return
        shell = "cmd" if parts[1].lower() == "cmd" else "powershell"
        cmd = parts[2]
    else:
        cmd = text.split(maxsplit=1)[1]

    try:
        data = await request_backend({"cmd": cmd, "shell": shell, "user_id": str(user.id)})
        output: str = data.get("output", "").strip()
        if not output:
            output = "✅ Command executed (no output)"

        safe_output = (output
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("```", "'''")
        )

        await update.message.reply_text(
            f"<b>📦 Command:</b> <code>{cmd}</code>\n<b>Output:</b>\n<pre>{safe_output}</pre>",
            parse_mode="HTML"
        )

    except httpx.TimeoutException:
        await update.message.reply_text("⏱️ Backend timeout")
    except httpx.ConnectError:
        await update.message.reply_text("🔌 Cannot connect to backend")
    except Exception as e:
        await update.message.reply_text("❌ Internal error")
        print(f"[ERROR] {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text("🤖 Bot ready. Use /help to see available commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    help_text = (
        "📚 Available commands:\n"
        "/help - Show this help message\n"
        "/exec [cmd|powershell] <command> - Run a shell command\n"
        "/lock - Lock the PC\n"
        "/shutdown - Shutdown the PC\n"
        "/restart - Restart the PC\n"
        "/screenshot - Capture and return a screenshot\n"
    )
    await update.message.reply_text(help_text)

async def send_action(update: Update, action: str, description: str) -> None:
    if update.message is None:
        return
    try:
        data = await request_backend({"action": action, "user_id": str(update.effective_user.id)})
        output = data.get("output", "").strip()
        if action == "screenshot" and data.get("screenshot_path"):
            path = data["screenshot_path"]
            try:
                with open(path, "rb") as photo:
                    await update.message.reply_photo(photo=photo, caption=output)
            finally:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception as remove_error:
                    print(f"[ERROR] Could not delete screenshot {path}: {remove_error}")
            return
        await update.message.reply_text(f"<b>{description}</b>\n<pre>{output}</pre>", parse_mode="HTML")
    except httpx.TimeoutException:
        await update.message.reply_text("⏱️ Backend timeout")
    except httpx.ConnectError:
        await update.message.reply_text("🔌 Cannot connect to backend")
    except Exception as e:
        await update.message.reply_text("❌ Internal error")
        print(f"[ERROR] {e}")

async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_action(update, "lock", "🔒 Locking PC")

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_action(update, "shutdown", "⚠️ Shutting down PC")

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_action(update, "restart", "♻️ Restarting PC")

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_action(update, "screenshot", "📸 Capturing screenshot")

if __name__ == "__main__":

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("exec", handle_command))
    app.add_handler(CommandHandler("lock", lock))
    app.add_handler(CommandHandler("shutdown", shutdown))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("screenshot", screenshot))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", start))
    print("✅ Bot running...")
    app.run_polling(drop_pending_updates=True)