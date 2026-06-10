from flask import Flask, request, jsonify, redirect, session, render_template
import requests
import time
import datetime

app = Flask(__name__, template_folder="templates")
app.secret_key = "secret123"

session_req = requests.Session()

# Browser headers for the API
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json",
    "Origin": "https://ffemote.com",
    "Referer": "https://ffemote.com/"
}

# ---------- BLOCKED UID ----------
blocked_uids = set()

# ---------- LOG STORAGE ----------
logs = []

def add_log(team, uid, response_text):
    current_time = time.time()
    timestamp = datetime.datetime.fromtimestamp(current_time).strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] TEAM: {team} | UID: {uid} | {response_text}"
    logs.append((current_time, log_entry))
    # Keep last 200 logs
    if len(logs) > 200:
        logs.pop(0)

# ---------- HOME ----------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- ADMIN ----------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == "pak112233":
            session["admin"] = True
            return redirect("/admin")
        else:
            return "Wrong Password"

    if not session.get("admin"):
        return '''
        <form method="POST">
            <input name="password" placeholder="Enter Password">
            <button>Login</button>
        </form>
        '''

    return render_template("admin.html", uids=list(blocked_uids))

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/admin")

# ---------- LOG PAGE ----------
@app.route("/logs")
def view_logs():
    if not session.get("admin"):
        return redirect("/admin")
    return render_template("logs.html")

# ---------- LOG DATA (RAW TEXT, NO AUTO-REFRESH) ----------
@app.route("/logs-data")
def logs_data():
    if not session.get("admin"):
        return "Unauthorized"

    # Return plain text lines with newlines (no <br> tags)
    output = []
    for t, msg in reversed(logs):  # newest first
        output.append(msg)
    return "\n".join(output)

# ---------- BLOCK ----------
@app.route("/block", methods=["POST"])
def block():
    if not session.get("admin"):
        return redirect("/admin")

    uid = request.form.get("uid")
    if uid:
        blocked_uids.add(uid)
        add_log("SYSTEM", uid, "BLOCKED")

    return redirect("/admin")

# ---------- UNBLOCK ----------
@app.route("/unblock", methods=["POST"])
def unblock():
    if not session.get("admin"):
        return redirect("/admin")

    uid = request.form.get("uid")
    if uid in blocked_uids:
        blocked_uids.remove(uid)
        add_log("SYSTEM", uid, "UNBLOCKED")

    return redirect("/admin")

# ---------- SEND ----------
@app.route("/send", methods=["POST"])
def send():
    uid = request.form.get("uid")
    team = request.form.get("team")
    emote = str(request.form.get("emote")).strip()
    # Get the No Bot toggle value from the form (defaults to false)
    no_bot = request.form.get("no_bot", "false").lower() == "true"

    if uid in blocked_uids:
        add_log(team, uid, "BLOCKED")
        return jsonify({"status": "blocked"})

    try:
        session_req.post(
            "https://ffemote.com/validate_passwords",
            json={"yt_password": "B25", "tg_password": "B25"},
            headers=BROWSER_HEADERS,
            timeout=10
        )

        r = session_req.post(
            "https://ffemote.com/send_emote",
            json={
                "server": "pakistan",
                "team_code": team,
                "emote_id": emote,
                "uids": [uid],
                "auto_leave": no_bot   # true if "No Bot" is toggled on
            },
            headers=BROWSER_HEADERS,
            timeout=10
        )

        response_text = r.text.strip()
        
        if r.status_code == 200 and "success" in r.text.lower():
            add_log(team, uid, f"SUCCESS - {response_text}")
            return jsonify({"status": "success"})
        else:
            add_log(team, uid, f"FAIL - {response_text}")
            return jsonify({"status": "fail"})

    except Exception as e:
        add_log(team, uid, f"ERROR - {str(e)}")
        return jsonify({"status": "error"})

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
