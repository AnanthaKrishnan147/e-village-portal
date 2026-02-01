from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

# Configure where uploaded files go
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 1. THE RULE ENGINE (Mock Data)
# In a real app, this would be in a database
REGIONAL_RULES = {
    "Village A": ["Aadhaar", "Ration Card"],
    "Village B": ["Aadhaar", "Income Certificate", "Voter ID"]
}

@app.route('/')
def index():
    return render_template('index.html')

# 2. THE ELIGIBILITY LOGIC
@app.route('/check-eligibility', methods=['POST'])
def check_eligibility():
    # Grab data from your HTML form
    service = request.form.get('service_type')
    region = request.form.get('region')
    file = request.files.get('document')

    # Simple logic for the hackathon:
    if not region or not file:
        return jsonify({"status": "error", "message": "Missing region or document!"})

    # Save the file (to show the officer later)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    # SIMULATED AI/LOGIC CHECK
    # Here is where you'd later add OCR to check for "Mismatches"
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