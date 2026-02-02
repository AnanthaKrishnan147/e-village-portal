from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import sqlite3
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
    conn = sqlite3.connect('village_office.db', timeout=10)
    cursor = conn.cursor()
    
    # USERS TABLE
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
            password_hash TEXT NOT NULL,
            jurisdiction_pincode TEXT,  -- For Officers
            jurisdiction_office TEXT    -- For Officers
        )
    ''')
    
    # DOCUMENTS TABLE
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

    # COMPLAINTS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            target_pincode TEXT NOT NULL,
            target_office TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            date_reported TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- 2. Helper Functions ---
def generate_client_id():
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(random.choices(chars, k=8))
    return f"VO-{suffix}"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 3. Routes ---

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'officer':
            return redirect(url_for('officer_dashboard'))
        return redirect(url_for('portal'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username').strip()
        name = request.form.get('full_name')
        dob = request.form.get('dob')
        phone = request.form.get('phone')
        email = request.form.get('email').strip().lower()
        govt_id = request.form.get('govt_id')
        password = request.form.get('password')
        pincode = request.form.get('pincode')
        office_name = request.form.get('village_office')

        new_client_id = generate_client_id()
        hashed_pw = generate_password_hash(password, method='scrypt')

        try:
            conn = sqlite3.connect('village_office.db', timeout=10)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO users (client_id, role, username, full_name, dob, phone, email, govt_id, password_hash, jurisdiction_pincode, jurisdiction_office) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (new_client_id, role, username, name, dob, phone, email, govt_id, hashed_pw, pincode, office_name))
            
            new_user_db_id = cursor.lastrowid
            conn.commit()
            conn.close()

            session['user_id'] = new_user_db_id
            session['client_id'] = new_client_id
            session['user_name'] = name
            session['role'] = role
            session['jurisdiction_pincode'] = pincode
            session['jurisdiction_office'] = office_name
            
            if role == 'officer':
                return redirect(url_for('officer_dashboard'))
            
            flash(f"🎉 Welcome {name}! Your Client ID is {new_client_id}")
            return redirect(url_for('portal'))
            
        except sqlite3.IntegrityError:
            return "❌ Error: Username, Email, or Aadhaar already exists. <a href='/register'>Try Again</a>"
        except Exception as e:
            return f"❌ System Error: {str(e)}"

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'login_attempts' not in session: session['login_attempts'] = 0

    if request.method == 'POST':
        username_input = request.form.get('username', '').strip()
        password_input = request.form.get('password')

        if session['login_attempts'] >= 3:
            return render_template('login.html', error_type="locked", username_value=username_input)

        conn = sqlite3.connect('village_office.db', timeout=10)
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username_input,)).fetchone()
        conn.close()

        if not user:
            return render_template('login.html', error_type="username", username_value=username_input)
        
        if not check_password_hash(user['password_hash'], password_input):
            session['login_attempts'] += 1
            remaining = 3 - session['login_attempts']
            if remaining <= 0:
                return render_template('login.html', error_type="locked", username_value=username_input)
            return render_template('login.html', error_type="password", remaining=remaining, username_value=username_input)

        session['login_attempts'] = 0
        session['user_id'] = user['id']
        session['client_id'] = user['client_id']
        session['user_name'] = user['full_name']
        session['role'] = user['role']
        session['jurisdiction_pincode'] = user['jurisdiction_pincode']
        session['jurisdiction_office'] = user['jurisdiction_office']
        
        if user['role'] == 'officer':
            return redirect(url_for('officer_dashboard'))
        return redirect(url_for('portal'))

    return render_template('login.html')

@app.route('/officer-dashboard', methods=['GET', 'POST'])
def officer_dashboard():
    if 'user_id' not in session or session.get('role') != 'officer':
        return "⛔ Access Denied: Authorized Personnel Only."

    conn = sqlite3.connect('village_office.db', timeout=10)
    conn.row_factory = sqlite3.Row

    my_pincode = session.get('jurisdiction_pincode')
    my_office = session.get('jurisdiction_office')

    # Fetch complaints for this officer
    complaints = conn.execute('''
        SELECT * FROM complaints 
        WHERE status='Pending' AND target_pincode = ? AND target_office = ?
        ORDER BY id DESC
    ''', (my_pincode, my_office)).fetchall()
    
    client_data = None
    client_docs = []
    error = None

    if request.method == 'POST':
        query_id = request.form.get('search_id').strip()
        client_data = conn.execute("SELECT * FROM users WHERE client_id = ?", (query_id,)).fetchone()
        
        if client_data:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_docs WHERE user_id = ?", (client_data['id'],))
            client_docs = cursor.fetchall()
        else:
            error = "No record found for this Client ID."
            
    conn.close()

    return render_template('officer_dashboard.html', 
                           officer_name=session.get('user_name'), 
                           jurisdiction=f"{my_office} ({my_pincode})",
                           client=client_data, 
                           documents=client_docs,
                           complaints=complaints,
                           error=error)

@app.route('/portal')
def portal():
    if 'user_id' not in session: return redirect(url_for('login'))
    return render_template('index.html', 
                           user_name=session.get('user_name'),
                           client_id=session.get('client_id'))

@app.route('/check-eligibility', methods=['POST'])
def check_eligibility():
    if 'user_id' not in session: return redirect(url_for('login'))

    service = request.form.get('service_type')
    village = request.form.get('village_office')
    uploaded_files = request.files.getlist('documents')
    
    for file in uploaded_files:
        if file and allowed_file(file.filename):
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = secure_filename(f"{service}_{session['user_id']}_{timestamp}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            # Simple doc save, no complex application linking
            conn = sqlite3.connect('village_office.db', timeout=10)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_docs (user_id, doc_type, filename, upload_date)
                VALUES (?, ?, ?, ?)
            ''', (session['user_id'], service + " Doc", filename, datetime.date.today()))
            conn.commit()
            conn.close()

    flash(f"✅ Application for {service} submitted successfully to {village} office!")
    return redirect(url_for('portal'))

@app.route('/report-issue', methods=['POST'])
def report_issue():
    if 'user_id' not in session: return redirect(url_for('login'))

    category = request.form.get('category')
    location = request.form.get('location')
    description = request.form.get('description')
    target_pincode = request.form.get('complaint_pincode')
    target_office = request.form.get('complaint_village_office')
    
    conn = sqlite3.connect('village_office.db', timeout=10)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO complaints (user_id, category, location, description, target_pincode, target_office, date_reported)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session['user_id'], category, location, description, target_pincode, target_office, datetime.date.today()))
    
    conn.commit()
    conn.close()
    
    flash(f"📢 Complaint Registered for {target_office} ({target_pincode})!")
    return redirect(url_for('portal'))

@app.route('/digilocker', methods=['GET', 'POST'])
def digilocker():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('village_office.db', timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if request.method == 'POST':
        doc_type = request.form.get('doc_type')
        file = request.files.get('file')
        if file and allowed_file(file.filename):
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = secure_filename(f"Locker_{session['user_id']}_{timestamp}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cursor.execute('INSERT INTO user_docs (user_id, doc_type, filename, upload_date) VALUES (?, ?, ?, ?)',
                           (session['user_id'], doc_type, filename, datetime.date.today()))
            conn.commit()
    cursor.execute("SELECT * FROM user_docs WHERE user_id = ?", (session['user_id'],))
    documents = cursor.fetchall()
    conn.close()
    return render_template('digilocker.html', documents=documents)

@app.route('/download/<filename>')
def download_file(filename):
    if 'user_id' not in session: return redirect(url_for('login'))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = sqlite3.connect('village_office.db', timeout=10)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/clear-database')
def clear_db():
    conn = sqlite3.connect('village_office.db', timeout=10)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM user_docs")
    cursor.execute("DELETE FROM complaints") 
    conn.commit()
    conn.close()
    return "✅ System Wiped. <a href='/register'>Restart Registration</a>"

if __name__ == '__main__':
    app.run(debug=True)