from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import sqlite3
import re
import datetime
import random
import string

# --- CONFIGURATION ---
UPLOAD_FOLDER = 'user_documents'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.secret_key = 'village_tech_lead_secure_key_2026'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- 1. Database Management ---
def init_db():
    conn = sqlite3.connect('village_office.db')
    cursor = conn.cursor()
    
    # Updated Table: Added 'username' and 'client_id'
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL, 
            role TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            dob TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            govt_id TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    # Document table (same as before)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            doc_type TEXT NOT NULL,
            filename TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- 2. Helper Functions ---
def generate_client_id():
    # Generates a random ID like "VO-8492"
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"VO-{suffix}"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 3. Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        # Redirect based on role
        if session.get('role') == 'officer':
            return redirect(url_for('officer_dashboard'))
        return redirect(url_for('portal'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username').strip() # New Field
        name = request.form.get('full_name')
        dob = request.form.get('dob')
        phone = request.form.get('phone')
        email = request.form.get('email').strip().lower()
        govt_id = request.form.get('govt_id')
        password = request.form.get('password')

        # Generate Unique Client ID
        new_client_id = generate_client_id()
        hashed_pw = generate_password_hash(password, method='scrypt')

        try:
            conn = sqlite3.connect('village_office.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (client_id, role, username, full_name, dob, phone, email, govt_id, password_hash) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_client_id, role, username, name, dob, phone, email, govt_id, hashed_pw))
            conn.commit()
            conn.close()
            
            # Show the Unique ID to the user upon success
            return render_template('registration_success.html', client_id=new_client_id, name=name)
            
        except sqlite3.IntegrityError:
            return "❌ Error: Username, Email, or Aadhaar already exists. <a href='/register'>Try Again</a>"

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Now authenticating via USERNAME
        username_input = request.form.get('username').strip()
        password = request.form.get('password')
        
        conn = sqlite3.connect('village_office.db')
        conn.row_factory = sqlite3.Row
        # Query matching username
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username_input,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['client_id'] = user['client_id'] # Store unique ID in session
            session['user_name'] = user['full_name']
            session['role'] = user['role']
            
            # Smart Redirect based on Role
            if user['role'] == 'officer':
                return redirect(url_for('officer_dashboard'))
            return redirect(url_for('portal'))
        
        return "❌ Login Failed: Invalid Username or Password. <a href='/login'>Try Again</a>"
    
    return render_template('login.html')

# --- OFFICER DASHBOARD (New Feature) ---
@app.route('/officer-dashboard', methods=['GET', 'POST'])
def officer_dashboard():
    # Security Guard
    if 'user_id' not in session or session.get('role') != 'officer':
        return "⛔ Access Denied: Officers Only."

    search_result = None
    if request.method == 'POST':
        query_id = request.form.get('search_id').strip()
        
        conn = sqlite3.connect('village_office.db')
        conn.row_factory = sqlite3.Row
        # Search for client by their Unique ID (VO-XXXX)
        search_result = conn.execute("SELECT * FROM users WHERE client_id = ?", (query_id,)).fetchone()
        conn.close()

    return render_template('officer_dashboard.html', 
                           officer_name=session.get('user_name'), 
                           result=search_result)

# --- CLIENT PORTAL (Existing) ---
@app.route('/portal')
def portal():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('index.html', 
                           user_name=session.get('user_name'),
                           client_id=session.get('client_id')) # Pass ID to template

# (Keep your existing digilocker, profile, and check-eligibility routes here...)
# For brevity, I am assuming the other existing routes remain the same.

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