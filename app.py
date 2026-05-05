from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
import qrcode
import os

app = Flask(__name__)

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Assets table
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

    # Logs table
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

# ---------------- LOG FUNCTION ----------------
def add_log(asset_id, action):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    now = datetime.now().strftime("%d-%m-%Y %H:%M")

    c.execute("""
        INSERT INTO logs (asset_id, action, timestamp)
        VALUES (?, ?, ?)
    """, (asset_id, action, now))

    conn.commit()
    conn.close()

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
    scans = c.fetchone()[0]

    if scans is None:
        scans = 0

    conn.close()

    return render_template(
        'dashboard.html',
        total=total,
        working=working,
        faulty=faulty,
        maintenance=maintenance,
        scans=scans
    )

# ---------------- VIEW ALL ASSETS (FIX ADDED) ----------------
@app.route('/assets')
def assets():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM assets")
    data = c.fetchall()

    conn.close()

    return render_template('assets.html', assets=data)

# ---------------- HOME PAGE ----------------
@app.route('/')
def index():
    return redirect('/dashboard')

# ---------------- ADD ASSET ----------------
@app.route('/add', methods=['POST'])
def add():
    cpu_name = request.form['cpu_name']
    serial = request.form['serial']
    status = request.form['status']

    now = datetime.now().strftime("%d-%m-%Y %H:%M")

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

    base_url = "https://asset-tracker-system-jg9d.onrender.com"
    url = f"{base_url}/asset/{asset_id}"

    qr = qrcode.make(url)

    if not os.path.exists("static"):
        os.makedirs("static")

    qr_path = f"static/qr_{asset_id}.png"
    qr.save(qr_path)

    return f"""
    <h2>Asset Added Successfully!</h2>
    <p>Scan this QR:</p>
    <img src='/{qr_path}' width='200'>
    <br><a href='/dashboard'>Go Dashboard</a>
    """

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
    conn.close()

    add_log(id, "QR Scanned")

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM logs WHERE asset_id=?", (id,))
    logs = c.fetchall()

    conn.close()

    return render_template('asset.html', data=data, scan=new_count, logs=logs)

# ---------------- RUN SERVER ----------------
if __name__ == '__main__':
    app.run()
