from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import qrcode
import os

app = Flask(__name__)

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cpu_name TEXT,
        serial_number TEXT,
        status TEXT,
        scan_count INTEGER DEFAULT 0,
        last_updated TEXT
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER,
        action TEXT,
        timestamp TEXT
    )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------------- LOG ----------------
def add_log(asset_id, action):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
        INSERT INTO logs (asset_id, action, timestamp)
        VALUES (?, ?, ?)
    """, (asset_id, action, now))

    conn.commit()
    conn.close()

# ---------------- HOME ----------------
@app.route('/')
def home():
    return redirect(url_for('dashboard'))

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM assets")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM assets WHERE status='Working'")
    working = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM assets WHERE status='Faulty'")
    faulty = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM assets WHERE status='Maintenance'")
    maintenance = c.fetchone()[0]

    c.execute("SELECT SUM(scan_count) FROM assets")
    scans = c.fetchone()[0] or 0

    conn.close()

    return render_template("dashboard.html",
                           total=total,
                           working=working,
                           faulty=faulty,
                           maintenance=maintenance,
                           scans=scans)

# ---------------- VIEW ALL ASSETS ----------------
@app.route('/assets')
def assets():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM assets ORDER BY id DESC")
    data = c.fetchall()

    conn.close()

    return render_template("assets.html", assets=data)

# ---------------- ADD PAGE ----------------
@app.route('/add', methods=['GET'])
def add_page():
    return render_template("add.html")

# ---------------- ADD ACTION ----------------
@app.route('/add', methods=['POST'])
def add():
    cpu_name = request.form.get('cpu_name')
    serial = request.form.get('serial')
    status = request.form.get('status')

    if not cpu_name or not serial or not status:
        return "Missing data"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("""
        INSERT INTO assets (cpu_name, serial_number, status, last_updated)
        VALUES (?, ?, ?, ?)
    """, (cpu_name, serial, status, now))

    asset_id = c.lastrowid
    conn.commit()
    conn.close()

    add_log(asset_id, "Asset Created")

    # ---------------- QR ----------------
    base_url = "https://asset-tracker-system-jg9d.onrender.com"
    url = f"{base_url}/asset/{asset_id}"

    qr = qrcode.make(url)

    if not os.path.exists("static"):
        os.makedirs("static")

    qr.save(f"static/qr_{asset_id}.png")

    return redirect(url_for('assets'))

# ---------------- VIEW ASSET ----------------
@app.route('/asset/<int:id>')
def asset(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM assets WHERE id=?", (id,))
    data = c.fetchone()

    if not data:
        return "Asset not found"

    new_count = data[4] + 1

    c.execute("UPDATE assets SET scan_count=? WHERE id=?", (new_count, id))
    conn.commit()

    add_log(id, "QR Scanned")

    c.execute("SELECT * FROM logs WHERE asset_id=? ORDER BY id DESC", (id,))
    logs = c.fetchall()

    conn.close()

    return render_template("asset.html", data=data, scan=new_count, logs=logs)

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
