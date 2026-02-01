from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
import re

# --- 1. Database Management ---
def init_db():
    conn = sqlite3.connect('village_office.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            full_name TEXT NOT NULL,
            dob TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            govt_id TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

app = Flask(__name__)
app.secret_key = 'village_tech_lead_secure_key_2026'

# --- 2. Security Validators ---

def is_valid_email(email):
    if not email:
        return False
    # Normalizing here as well to ensure consistent checks
    pattern = r'^[a-zA-Z0-9_.+-]+@(gmail|yahoo|outlook|hotmail|icloud)\.com$'
    return re.match(pattern, email.strip().lower())

def is_valid_password(password):
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not password[0].isupper():
        return False, "Password must start with a Capital letter."
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    if not (has_digit and has_special):
        return False, "Password needs a digit and a special character."
    return True, ""

# --- 3. Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('portal'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role')
        name = request.form.get('full_name')
        dob = request.form.get('dob')
        phone = request.form.get('phone')
        # Normalizing email during registration
        email = request.form.get('email').strip().lower()
        govt_id = request.form.get('govt_id')
        password = request.form.get('password')

        if not is_valid_email(email):
            return "❌ INVALID EMAIL: Use @gmail.com, @yahoo.com, etc. <a href='/register'>Try Again</a>"
        
        is_pw_ok, pw_err = is_valid_password(password)
        if not is_pw_ok:
            return f"❌ {pw_err} <a href='/register'>Try Again</a>"

        if not (phone.isdigit() and len(phone) == 10):
            return "❌ PHONE ERROR: 10 digits required. <a href='/register'>Try Again</a>"

        if not (govt_id.isdigit() and len(govt_id) == 12):
            return "❌ AADHAAR ERROR: 12 digits required. <a href='/register'>Try Again</a>"

        hashed_pw = generate_password_hash(password, method='scrypt')

        try:
            conn = sqlite3.connect('village_office.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (role, full_name, dob, phone, email, govt_id, password_hash) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (role, name, dob, phone, email, govt_id, hashed_pw))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "❌ Account already exists for this Email or Aadhaar. <a href='/register'>Back</a>"

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # FIXED: Strip spaces and lowercase the input to match registration format
        email_input = request.form.get('user_id').strip().lower() 
        password_input = request.form.get('password')
        
        conn = sqlite3.connect('village_office.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Query using the normalized email
        cursor.execute("SELECT * FROM users WHERE email = ?", (email_input,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password_input):
            session.clear() 
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['role'] = user['role']
            return redirect(url_for('portal'))
        
        return "❌ LOGIN FAILED: Incorrect email or password. <a href='/login'>Try Again</a>"
    
    return render_template('login.html')

@app.route('/portal')
def portal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('index.html', 
                           user_name=session.get('user_name'), 
                           role=session.get('role'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/clear-database')
def clear_db():
    conn = sqlite3.connect('village_office.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    conn.commit()
    conn.close()
    return "✅ System Wiped. <a href='/register'>Restart Registration</a>"

if __name__ == '__main__':
    app.run(debug=True)