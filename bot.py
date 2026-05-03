import os
import time
import hmac
import hashlib
import httpx
import asyncio
from PIL import ImageGrab
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# ✅ Fix 1: Ensure SECRET is always bytes
TOKEN: str = os.environ.get("BOT_TOKEN", "8041461190:AAF2dORrqEUW2euLE33whRUNqev3y6pLPZI")
BACKEND_URL: str = os.environ.get("BACKEND_URL", "http://127.0.0.1:5000/terminal")
SECRET: bytes = os.environ.get("API_SECRET", "super_secret_key").encode()  # .encode() ensures bytes

# Allowed users
ALLOWED_USERS: set[int] = {1010955964}

STREAMING = False
STREAM_TASK = None

CURRENT_DIR = os.path.expanduser("~")

async def authorize(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id in ALLOWED_USERS

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
        "/stream - Start streaming screenshots\n"
        "/stop_stream - Stop streaming screenshots\n"
        "/ls - List files in current directory\n"
        "/cd <folder> - Change directory\n"
        "/back - Go back to parent directory\n"
        "/view <file_path> - View a file or image\n"
    )
    await update.message.reply_text(help_text)

async def send_action(update: Update, action: str, description: str) -> None:
    if update.message is None:
        return
    
    user = update.effective_user
    if user is None:
        return
    
    try:
        data = await request_backend({"action": action, "user_id": str(user.id)})
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


async def stream_loop(msg):
    while STREAMING:
        try:
            img = ImageGrab.grab()
            path = "temp_stream.png"
            img.save(path)

            with open(path, "rb") as f:
                await msg.reply_photo(f)

            os.remove(path)
            await asyncio.sleep(3)  # interval

        except asyncio.CancelledError:
            break
        except Exception as e:
            await msg.reply_text(str(e))
            break


async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STREAMING, STREAM_TASK
    msg = update.effective_message

    if msg is None:
        return

    if not await authorize(update):
        return

    if STREAM_TASK and not STREAM_TASK.done():
        await msg.reply_text("📡 Already streaming")
        return

    STREAMING = True
    await msg.reply_text("📡 Streaming started...")

    STREAM_TASK = asyncio.create_task(stream_loop(msg))


async def stop_stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STREAMING, STREAM_TASK
    msg = update.effective_message

    if msg is None:
        return

    if not await authorize(update):
        return

    STREAMING = False
    if STREAM_TASK and not STREAM_TASK.done():
        STREAM_TASK.cancel()
    await msg.reply_text("⛔ Streaming stopped")


# -------- LIST FILES --------
async def ls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CURRENT_DIR
    msg = update.effective_message

    if msg is None:
        return

    if not await authorize(update):
        return

    try:
        files = os.listdir(CURRENT_DIR)
        if not files:
            await msg.reply_text("📂 Empty folder")
            return

        output = "\n".join(files[:50])  # limit output
        await msg.reply_text(f"📁 {CURRENT_DIR}\n\n{output}")

    except Exception as e:
        await msg.reply_text(str(e))


# -------- CHANGE DIRECTORY --------
async def cd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CURRENT_DIR
    msg = update.effective_message

    if msg is None:
        return

    if not await authorize(update):
        return

    if not context.args:
        await msg.reply_text("Usage: /cd <folder>")
        return

    new_path = os.path.join(CURRENT_DIR, " ".join(context.args))

    if os.path.isdir(new_path):
        CURRENT_DIR = os.path.abspath(new_path)
        await msg.reply_text(f"📂 Moved to:\n{CURRENT_DIR}")
    else:
        await msg.reply_text("❌ Folder not found")


# -------- BACK --------
async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CURRENT_DIR
    msg = update.effective_message

    if msg is None:
        return

    if not await authorize(update):
        return

    CURRENT_DIR = os.path.dirname(CURRENT_DIR)
    await msg.reply_text(f"⬅️ Back to:\n{CURRENT_DIR}")


async def view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message

    if msg is None:
        return

    if not await authorize(update):
        return

    if not context.args:
        await msg.reply_text("Usage: /view <file_path>")
        return

    path = os.path.join(CURRENT_DIR, " ".join(context.args))

    if not os.path.exists(path):
        await msg.reply_text("❌ File not found")
        return

    try:
        # IMAGE
        if path.lower().endswith((".png", ".jpg", ".jpeg")):
            with open(path, "rb") as photo:
                await msg.reply_photo(photo=photo)

        # TEXT
        elif path.lower().endswith((".txt", ".log", ".py")):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                await msg.reply_text(f.read(4000))

        # OTHER FILES
        else:
            with open(path, "rb") as doc:
                await msg.reply_document(document=doc)

    except Exception as e:
        await msg.reply_text(str(e))
if __name__ == "__main__":

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("exec", handle_command))
    app.add_handler(CommandHandler("lock", lock))
    app.add_handler(CommandHandler("shutdown", shutdown))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("screenshot", screenshot))
    app.add_handler(CommandHandler("stream", stream))
    app.add_handler(CommandHandler("stop_stream", stop_stream))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ls", ls))
    app.add_handler(CommandHandler("cd", cd))
    app.add_handler(CommandHandler("back", back))
    app.add_handler(CommandHandler("view", view))
    print("✅ Bot running...")
    app.run_polling(drop_pending_updates=True)