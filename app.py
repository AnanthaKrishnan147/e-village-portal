from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

# --- Configuration ---
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- 1. Navigation Routes (Pages) ---

@app.route('/')
def home():
    # Landing page: You can point this to login or index
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Technical Lead Note: This is where user_id/password verification happens
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        return f"Login Attempt for {user_id} Successful" 
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        # Capture form data
        name = request.form.get('full_name')
        aadhaar = request.form.get('aadhaar_no')
        
        # Technical Lead Note: In a real system, you would save this to SQLite here
        print(f"New Registration: {name}, Aadhaar: {aadhaar}")
        
        # After registration, redirect back to login
        return render_template('login.html', success_msg="Account created! Please login.")
        
    return render_template('register.html')

@app.route('/portal')
def portal():
    # This serves your original citizen eligibility form
    return render_template('index.html')

# --- 2. Functional Routes (Logic) ---

@app.route('/check-eligibility', methods=['POST'])
def check_eligibility():
    service = request.form.get('service_type')
    region = request.form.get('region')
    file = request.files.get('document')

    if not region or not file:
        return jsonify({"status": "error", "message": "Missing region or document!"})

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    # Simplified AI/Logic Check
    if "Aadhaar" in file.filename:
        return jsonify({
            "status": "success", 
            "pin": "VO-882910",
            "message": f"Verified for {service} in {region}."
        })
    else:
        return jsonify({
            "status": "mismatch",
            "message": "Document type mismatch. Expected Aadhaar based on regional rules."
        })

if __name__ == '__main__':
    app.run(debug=True)