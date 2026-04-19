from flask import Flask, request, jsonify
import os
import subprocess

app = Flask(__name__)

API_KEY = "my_secure_key"
BASE_DIR = "C:/Users/ASUS/Downloads"

# ✅ Allowed commands (important for safety)
ALLOWED_COMMANDS = ["whoami", "ipconfig", "dir"]

# ---------------- SECURITY ----------------
def verify(req):
    key = req.form.get("api_key") or req.args.get("api_key")
    return key == API_KEY

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