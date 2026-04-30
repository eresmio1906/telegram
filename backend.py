from flask import Flask, request, jsonify
import os
import subprocess
import hmac
from pathlib import Path
from dotenv import load_dotenv

# 🔐 NEW IMPORTS
from dotenv import load_dotenv
from cryptography.fernet import Fernet

app = Flask(__name__)

# ==================================================
# 🔐 LOAD ENCRYPTED SECRETS FROM secrets.env
# ==================================================


env_path = Path(__file__).resolve().parent / "secrets.env"
load_dotenv(env_path)

key = os.getenv("FERNET_KEY")

if not key:
    raise ValueError("FERNET_KEY missing in secrets.env")

FERNET_KEY = key.encode()
fernet = Fernet(FERNET_KEY)
def dec(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing {name}")
    return fernet.decrypt(value.encode()).decode()

# 🔐 Decrypted runtime values
API_KEY = dec("ENC_API_KEY")

# ==================================================
# NORMAL CONFIG
# ==================================================
BASE_DIR = "C:/Users"

# ✅ Allowed commands
ALLOWED_COMMANDS = ["whoami", "ipconfig", "dir", "ping", "systeminfo", "tasklist", "netstat","time", "date","python -m http.server 9874","netuser","cd C:\Users"]

# ==================================================
# 🔥 ULTIMATE WINDOWS ALLOWED COMMANDS PACK
# Safe-ish command categories for personal PC use
# Use with base-command parsing:
base = cmd.split()[0].lower()
# ==================================================
# ---------------- SECURITY ----------------
# ==================================================

def verify(req):
    key = req.form.get("api_key") or req.args.get("api_key") or ""

    # Constant-time secure compare
    return hmac.compare_digest(key, API_KEY)

# ---------------- ROOT ----------------
@app.route("/")
def home():
    return jsonify({"status": "Backend Running Securely"})

# ---------------- SYSTEM ACTIONS ----------------
@app.route("/action/lock", methods=["POST"])
def lock():
    if not verify(request):
        return jsonify({"error": "Unauthorized"}), 403

    os.system("rundll32.exe user32.dll,LockWorkStation")
    return jsonify({"status": "Locked"})


@app.route("/action/shutdown", methods=["POST"])
def shutdown():
    if not verify(request):
        return jsonify({"error": "Unauthorized"}), 403

    os.system("shutdown /s /t 5")
    return jsonify({"status": "Shutdown started"})


@app.route("/action/restart", methods=["POST"])
def restart():
    if not verify(request):
        return jsonify({"error": "Unauthorized"}), 403

    os.system("shutdown /r /t 5")
    return jsonify({"status": "Restart started"})


# ---------------- FILE HANDLING ----------------
@app.route("/files", methods=["GET"])
def files():
    if not verify(request):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        files = os.listdir(BASE_DIR)
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)})


# ---------------- COMMAND EXECUTION ----------------
@app.route("/terminal", methods=["POST"])
def terminal():
    if not verify(request):
        return jsonify({"error": "Unauthorized"}), 403

    cmd = request.form.get("cmd")

    if not cmd:
        return jsonify({"output": "No command provided"})

    # ✅ Whitelist check
    if cmd not in ALLOWED_COMMANDS:
        return jsonify({"output": "❌ Command not allowed"})

    try:
        result = subprocess.run(
            cmd.split(),          # safer than shell=True
            capture_output=True,
            text=True
        )

        output = result.stdout if result.stdout else result.stderr

    except Exception as e:
        output = str(e)

    return jsonify({"output": output})


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
