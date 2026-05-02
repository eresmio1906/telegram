import os
import time
import hmac
import hashlib
import subprocess
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)
SECRET = os.environ.get("API_SECRET", "super_secret_key").encode()  # 🔒 Never hardcode
BASE_DIR = os.path.expanduser("~")
user_dirs = {}
dir_lock = threading.Lock()  # 🧵 Thread safety
SYSTEM_ENABLED = True
SCREENSHOTS_DIR = os.path.dirname(os.path.abspath(__file__))

def verify(sig, payload, ts):
    try:
        if abs(time.time() - int(ts)) > 30:
            return False
        return hmac.compare_digest(sig, hmac.new(SECRET, f"{payload}:{ts}".encode(), hashlib.sha256).hexdigest())
    except (ValueError, TypeError):
        return False


def capture_screenshot() -> str:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    path = os.path.join(SCREENSHOTS_DIR, filename)
    escaped_path = path.replace("'", "''")
    ps_cmd = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        "$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height; "
        "$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
        "$graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bitmap.Size); "
        f"$bitmap.Save('{escaped_path}'); "
        "$graphics.Dispose(); $bitmap.Dispose();"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=20
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Screenshot command failed")
    return path

def handle_cd(arg, cwd):
    if not arg.strip():
        return os.path.expanduser("~"), ""  # cd without args -> home dir
    target = os.path.abspath(os.path.join(cwd, arg))
    if os.path.isdir(target):
        return target, ""
    return cwd, "❌ Directory not found"

@app.route("/terminal", methods=["POST"])
def terminal():
    if not SYSTEM_ENABLED:
        return jsonify({"output": "🚫 System disabled"}), 403

    cmd = request.form.get("cmd", "").strip()
    action = request.form.get("action", "").strip().lower()
    uid = request.form.get("user_id", "").strip()
    sig = request.form.get("sig", "")
    ts = request.form.get("ts", "")

    payload = action or cmd
    if not payload or not uid or not verify(sig, payload, ts):
        return jsonify({"output": "❌ Invalid request or signature"}), 401

    with dir_lock:
        cwd = user_dirs.get(uid, BASE_DIR)

    if action:
        if action in {"lock", "shutdown", "restart"}:
            commands = {
                "lock": ["rundll32.exe", "user32.dll,LockWorkStation"],
                "shutdown": ["shutdown", "/s", "/t", "0", "/f"],
                "restart": ["shutdown", "/r", "/t", "0", "/f"],
            }
            result = subprocess.run(
                commands[action],
                capture_output=True, text=True, cwd=cwd, timeout=10
            )
            output = (result.stdout + result.stderr).strip() or f"✅ {action.capitalize()} command sent"
            response = {"output": output, "cwd": cwd}
        elif action == "screenshot":
            try:
                path = capture_screenshot()
                response = {"output": f"✅ Screenshot saved: {path}", "cwd": cwd, "screenshot_path": path}
            except Exception as e:
                response = {"output": f"❌ Screenshot failed: {e}", "cwd": cwd}
        else:
            return jsonify({"output": "❌ Unsupported action", "cwd": cwd}), 400

        with dir_lock:
            user_dirs[uid] = cwd

        with open("audit.log", "a") as f:
            f.write(f"{time.ctime()} | {uid} | ACTION={action}\n")

        return jsonify(response)

    # Parse cd properly
    parts = cmd.split(maxsplit=1)
    if parts[0].lower() == "cd" or parts[0].lower() == "set-location":
        arg = parts[1] if len(parts) > 1 else ""
        with dir_lock:
            new_cwd, msg = handle_cd(arg, cwd)
            user_dirs[uid] = new_cwd
        return jsonify({"output": msg or f"📂 {new_cwd}", "cwd": new_cwd})

    shell = request.form.get("shell", "powershell").strip().lower()
    if shell == "cmd":
        process = ["cmd.exe", "/c", cmd]
    else:
        process = ["powershell", "-NoProfile", "-Command", cmd]

    result = subprocess.run(
        process,
        capture_output=True, text=True, cwd=cwd, timeout=10
    )
    output = (result.stdout + result.stderr)[:3500]

    with dir_lock:
        user_dirs[uid] = cwd  # Update to ensure consistency

    with open("audit.log", "a") as f:
        f.write(f"{time.ctime()} | {uid} | {cmd}\n")

    return jsonify({"output": output, "cwd": cwd})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)