# kana_mini_bot.py
import os
import sqlite3
import random
import requests
import telebot
import threading
import json
import hmac
import hashlib
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ----------------- Config / Env -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")             # set in Railway variables
CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")  # set in Railway variables
ADMIN_ID = os.getenv("ADMIN_ID")               # optional, admin Telegram id (for logs)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in environment variables")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ----------------- Database (SQLite) -----------------
DB_PATH = "database.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    type TEXT,        -- deposit/withdraw/bet
    amount REAL,
    status TEXT,
    tx_ref TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    game TEXT,
    amount REAL,
    multiplier REAL,
    status TEXT,      -- won/lost
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)""")
conn.commit()

# ----------------- Helpers -----------------
def get_balance(user_id:int) -> float:
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    if not r:
        cursor.execute("INSERT INTO users(user_id, balance) VALUES (?, ?)", (user_id, 0.0))
        conn.commit()
        return 0.0
    return r[0]

def update_balance(user_id:int, delta:float) -> float:
    bal = get_balance(user_id) + delta
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (bal, user_id))
    conn.commit()
    return bal

def create_chapa_payment(amount, email, user_id, first_name="User", last_name=""):
    """
    Initialize a Chapa transaction. We put the user_id into tx_ref so webhook can map it.
    """
    if not CHAPA_SECRET_KEY:
        return {"error": "CHAPA key missing on server"}
    tx_ref = f"tx-{user_id}-{os.urandom(6).hex()}"
    url = "https://api.chapa.co/v1/transaction/initialize"
    headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}", "Content-Type": "application/json"}
    # callback_url: automatically set at deployment: replace <your-domain> later or update before deploy
    base = os.environ.get("PUBLIC_URL") or os.environ.get("RAILWAY_STATIC_URL") or os.environ.get("PROJECT_URL")
    callback = f"https://{base}/webhook" if base else f"/webhook"
    data = {
        "amount": str(amount),
        "currency": "ETB",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "tx_ref": tx_ref,
        "callback_url": callback,
        "return_url": "https://t.me/"  # user returns to bot
    }
    resp = requests.post(url, headers=headers, json=data, timeout=30)
    return resp.json()

def chapa_payout(amount, email, tx_ref=None):
    """
    Payout via Chapa (requires Chapa payout permission/business account).
    """
    if not CHAPA_SECRET_KEY:
        return {"error":"CHAPA key missing"}
    url = "https://api.chapa.co/v1/payout"
    headers = {"Authorization": f"Bearer {CHAPA_SECRET_KEY}", "Content-Type": "application/json"}
    payload = {
        "amount": str(amount),
        "currency": "ETB",
        "email": email,
        "tx_ref": tx_ref or ("wd-" + os.urandom(6).hex())
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    try:
        return resp.json()
    except:
        return {"error": "invalid response from chapa"}

def parse_tx_ref(tx_ref):
    # Expect pattern: tx-{user_id}-{random}
    try:
        parts = tx_ref.split("-")
        if len(parts) >= 3 and parts[0] == "tx":
            user_id = int(parts[1])
            return user_id
    except:
        pass
    return None

# Telegram WebApp init_data verification (per Telegram docs)
def verify_telegram_init_data(init_data: str) -> dict | None:
    """
    Verifies init_data coming from Telegram WebApp using Bot token.
    init_data is the initData string (query-string-like) provided by the web app.
    Returns parsed dict of params on success, otherwise None.
    """
    if not init_data:
        return None
    # parse params into a dict
    params = {}
    for pair in init_data.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            params[k] = requests.utils.unquote(v)
    check_hash = params.get("hash")
    if not check_hash:
        return None
    # build data_check_string
    items = []
    for k in sorted(params.keys()):
        if k == "hash":
            continue
        items.append(f"{k}={params[k]}")
    data_check_string = "\n".join(items).encode()
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    hmac_calculated = hmac.new(secret_key, data_check_string, hashlib.sha256).hexdigest()
    if hmac_calculated == check_hash:
        return params
    return None

# ----------------- Flask App & API -----------------
app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

@app.route("/")
def root():
    return "Kana Mini Bot backend is running ✅"

# Serve the mini app entry
@app.route("/webapp")
def webapp_index():
    return send_from_directory("static", "index.html")

# Chapa webhook for deposit notifications
@app.route("/webhook", methods=["POST"])
def chapa_webhook():
    data = request.json or {}
    # Chapa returns data including tx_ref and status
    tx_ref = data.get("tx_ref") or data.get("data", {}).get("tx_ref")
    status = data.get("status") or data.get("data", {}).get("status")
    amount = float(data.get("amount", 0) or data.get("data", {}).get("amount", 0) or 0)
    if tx_ref:
        user_id = parse_tx_ref(tx_ref)
        if user_id and status == "success":
            update_balance(user_id, amount)
            cursor.execute("INSERT INTO transactions(user_id, type, amount, status, tx_ref) VALUES (?,?,?,?,?)",
                           (user_id, "deposit", amount, "success", tx_ref))
            conn.commit()
            # notify user if admin configured?
            try:
                bot.send_message(user_id, f"Deposit of {amount} ETB was successful — credited to your wallet.")
            except:
                pass
            return jsonify({"status":"ok"}), 200
    return jsonify({"status":"ignored"}), 200

# API: init payment
@app.route("/api/init_payment", methods=["POST"])
def api_init_payment():
    body = request.json or {}
    amount = body.get("amount")
    email = body.get("email")
    user_id = int(body.get("user_id"))
    if not amount or not email or not user_id:
        return jsonify({"error":"missing fields"}), 400
    resp = create_chapa_payment(amount, email, user_id)
    return jsonify(resp)

# API: get balance
@app.route("/api/get_balance", methods=["POST"])
def api_get_balance():
    body = request.json or {}
    user_id = int(body.get("user_id"))
    bal = get_balance(user_id)
    return jsonify({"user_id":user_id, "balance": bal})

# API: bet (simple Aviator-style)
@app.route("/api/bet", methods=["POST"])
def api_bet():
    body = request.json or {}
    user_id = int(body.get("user_id"))
    amount = float(body.get("amount"))
    game = body.get("game", "aviator")
    if amount <= 0:
        return jsonify({"error":"invalid amount"}), 400
    bal = get_balance(user_id)
    if amount > bal:
        return jsonify({"error":"insufficient funds"}), 400
    # Simple aviator-style: random multiplier, determine win/loss
    multiplier = round(random.uniform(1.00, 8.00), 2)
    won = random.random() < 0.45  # about 45% chance to win (adjustable)
    if won:
        won_amount = round(amount * multiplier, 2)
        update_balance(user_id, won_amount)
        status = "won"
    else:
        update_balance(user_id, -amount)
        won_amount = 0.0
        status = "lost"
    cursor.execute("INSERT INTO bets(user_id, game, amount, multiplier, status) VALUES (?,?,?,?,?)",
                   (user_id, game, amount, multiplier, status))
    conn.commit()
    return jsonify({"status":status, "multiplier":multiplier, "won_amount":won_amount, "balance": get_balance(user_id)})

# API: withdraw (automatic payout attempt)
@app.route("/api/withdraw", methods=["POST"])
def api_withdraw():
    body = request.json or {}
    user_id = int(body.get("user_id"))
    amount = float(body.get("amount"))
    recipient_email = body.get("email")
    if amount <= 0 or not recipient_email:
        return jsonify({"error":"missing fields"}), 400
    bal = get_balance(user_id)
    if amount > bal:
        return jsonify({"error":"insufficient funds"}), 400
    # call chapa payout
    resp = chapa_payout(amount, recipient_email)
    # If success, update balance and save transaction
    if resp.get("status") == "success":
        update_balance(user_id, -amount)
        cursor.execute("INSERT INTO transactions(user_id, type, amount, status) VALUES (?,?,?,?)",
                       (user_id, "withdraw", amount, "success"))
        conn.commit()
        return jsonify({"status":"success", "balance": get_balance(user_id)})
    else:
        # store pending/failed
        cursor.execute("INSERT INTO transactions(user_id, type, amount, status) VALUES (?,?,?,?)",
                       (user_id, "withdraw", amount, "failed"))
        conn.commit()
        return jsonify({"status":"failed", "detail": resp}), 400

# API: auth (verify Telegram init_data sent from webapp)
@app.route("/api/auth", methods=["POST"])
def api_auth():
    body = request.json or {}
    init_data = body.get("init_data")
    parsed = verify_telegram_init_data(init_data)
    if not parsed:
        # fallback: accept initDataUnsafe if present (less secure) - but recommend verifying
        return jsonify({"error":"invalid init_data"}), 400
    # parsed contains keys like user and auth_date
    # user might be in parsed as 'user' string in JSON escaped form; simpler approach:
    # Bot will identify user by the 'user' field parsed server-side by client (we'll also accept user_id in request)
    user_id = int(body.get("user_id") or parsed.get("user_id") or parsed.get("user", {}).get("id", 0))
    if not user_id:
        # if client provides explicit user_id param, use that
        return jsonify({"error":"no user id"}), 400
    # ensure user exists
    cursor.execute("INSERT OR IGNORE INTO users(user_id, balance) VALUES (?, ?)", (user_id, 0.0))
    conn.commit()
    return jsonify({"user_id": user_id, "balance": get_balance(user_id)})

# ----------------- Telegram Bot Handlers -----------------
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    uid = msg.from_user.id
    get_balance(uid)  # ensure inserted
    bot.send_message(uid, "Welcome to Kana Mini Casino! Use /casino to open the web app, /balance to check wallet.")

@bot.message_handler(commands=['balance'])
def cmd_balance(msg):
    uid = msg.from_user.id
    bal = get_balance(uid)
    bot.send_message(uid, f"Your balance: {bal} ETB")

@bot.message_handler(commands=['casino'])
def cmd_casino(msg):
    # When user clicks the inline button, Telegram opens the web app inside the client
    base_url = os.environ.get("PUBLIC_URL") or os.environ.get("RAILWAY_STATIC_URL") or os.environ.get("PROJECT_URL")
    if not base_url:
        # you can copy-paste your Railway domain here as a fallback:
        base_url = os.environ.get("BASE_URL") or "your-project.up.railway.app"
    webapp_url = f"https://{base_url}/webapp"
    markup = telebot.types.InlineKeyboardMarkup()
    webapp = telebot.types.WebAppInfo(webapp_url)
    btn = telebot.types.InlineKeyboardButton("🎮 Open Mini Casino", web_app=webapp)
    markup.add(btn)
    bot.send_message(msg.chat.id, "Open the mini app:", reply_markup=markup)

# ----------------- Main: run bot in a thread and Flask app -----------------
def run_bot():
    # non_stop polling; TeleBot runs in separate thread
    bot.infinity_polling()

if __name__ == "__main__":
    # start Telegram bot in a background thread
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
    # start Flask (use PORT provided by Railway)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
----------
