import os
import re
import base64
import numpy as np
import pandas as pd
import cv2
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_file
from werkzeug.utils import secure_filename
from PIL import Image
import io

from attendance_core import AttendanceCore

app = Flask(__name__)

# Configurations
UPLOAD_FOLDER = 'uploads'
KNOWN_FACES_DIR = 'known_faces'
LOGS_DIR = 'attendance_logs'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'xlsx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['KNOWN_FACES_DIR'] = KNOWN_FACES_DIR
app.config['LOGS_DIR'] = LOGS_DIR

# Default master spreadsheet path
DEFAULT_EXCEL_PATH = 'students_master.xlsx'
app.config['EXCEL_PATH'] = DEFAULT_EXCEL_PATH if os.path.exists(DEFAULT_EXCEL_PATH) else None

# Initialize folders
for folder in [UPLOAD_FOLDER, KNOWN_FACES_DIR, LOGS_DIR]:
    os.makedirs(folder, exist_ok=True)

# Initialize core model
core = AttendanceCore(known_faces_dir=KNOWN_FACES_DIR)

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

@app.route('/')
def index():
    """Serves the frontend dashboard."""
    # We will serve the index.html from a template file. Flask will automatically look for templates/index.html.
    # If templates/index.html exists, we render it.
    try:
        return send_file(os.path.join('templates', 'index.html'))
    except Exception as e:
        return f"Error loading index.html: {e}. Please ensure templates/index.html is created.", 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns the current state of the application."""
    return jsonify({
        "excel_loaded": app.config['EXCEL_PATH'] is not None,
        "excel_filename": os.path.basename(app.config['EXCEL_PATH']) if app.config['EXCEL_PATH'] else "None",
        "registered_students_count": len(core.known_rolls),
        "registered_rolls": core.known_rolls,
        "present_students_count": len(core.get_present_rolls()),
        "present_rolls": core.get_present_rolls()
    })

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    """Endpoint for uploading a master student spreadsheet (.xlsx)."""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
    
    if file and allowed_file(file.filename, {'xlsx'}):
        filename = secure_filename(file.filename)
        dest_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(dest_path)
        app.config['EXCEL_PATH'] = dest_path
        
        # Verify columns in the uploaded Excel
        try:
            df = pd.read_excel(dest_path)
            if df.empty:
                return jsonify({"success": False, "message": "Excel file is empty"}), 400
            
            first_col = df.columns[0]
            student_count = len(df)
            return jsonify({
                "success": True, 
                "message": f"Successfully loaded master Excel. First column: '{first_col}' ({student_count} records found)."
            })
        except Exception as e:
            app.config['EXCEL_PATH'] = None
            return jsonify({"success": False, "message": f"Invalid Excel format: {str(e)}"}), 400
            
    return jsonify({"success": False, "message": "Only .xlsx Excel files are allowed"}), 400

@app.route('/register_face', methods=['POST'])
def register_face():
    """Registers a new student face image (filename = <roll_number>.jpg/png)."""
    roll_number = request.form.get('roll_number')
    if not roll_number:
        return jsonify({"success": False, "message": "Roll number is required"}), 400
    
    # Sanitize roll number to prevent path traversal
    roll_number = re.sub(r'[^a-zA-Z0-9_\-]', '', roll_number)
    if not roll_number:
        return jsonify({"success": False, "message": "Invalid roll number format"}), 400

    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No face image file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
    
    if file and allowed_file(file.filename, {'png', 'jpg', 'jpeg'}):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{roll_number}.{ext}"
        dest_path = os.path.join(app.config['KNOWN_FACES_DIR'], filename)
        file.save(dest_path)
        
        # Reload faces in core model
        try:
            core.load_known_faces()
            return jsonify({"success": True, "message": f"Registered face for roll number: {roll_number}."})
        except Exception as e:
            return jsonify({"success": False, "message": f"Error registering face: {str(e)}"}), 500
            
    return jsonify({"success": False, "message": "Only image files (png, jpg, jpeg) are allowed"}), 400

@app.route('/process_frame', methods=['POST'])
def process_frame():
    """
    Decodes base64 image data, performs face-recognition, 
    and returns annotated base64 image along with list of present rolls.
    """
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"error": "Missing image data"}), 400
    
    try:
        # Base64 string format: "data:image/jpeg;base64,/9j/4AAQSk..."
        image_data = data['image']
        if ',' in image_data:
            image_data = image_data.split(',')[1]
            
        decoded_bytes = base64.b64decode(image_data)
        
        # Convert bytes to OpenCV Mat
        nparr = np.frombuffer(decoded_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({"error": "Failed to decode image"}), 400

        # Process frame
        processed_frame = core.process_frame(frame)
        
        # Encode back to JPEG
        _, buffer = cv2.imencode('.jpg', processed_frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            "image": f"data:image/jpeg;base64,{jpg_as_text}",
            "present_rolls": core.get_present_rolls()
        })
    except Exception as e:
        return jsonify({"error": f"Internal frame processing error: {str(e)}"}), 500

@app.route('/start_attendance', methods=['POST'])
def start_attendance():
    """Starts a new attendance session."""
    core.finish()
    return jsonify({"success": True, "message": "Attendance session started. Ready for scanning."})

@app.route('/stop_attendance', methods=['POST'])
def stop_attendance():
    """
    Stops the attendance session, updates the Excel worksheet 
    with a new column of checkmarks, and returns download details.
    """
    excel_path = app.config.get('EXCEL_PATH')
    if not excel_path or not os.path.exists(excel_path):
        return jsonify({"success": False, "message": "Master Excel file is not loaded. Please upload one first."}), 400
    
    present_rolls = core.get_present_rolls()
    if not present_rolls:
        return jsonify({"success": False, "message": "No students marked present. Attendance was not saved."}), 400

    try:
        # Load the spreadsheet
        master_df = pd.read_excel(excel_path)
        
        # Roll numbers are assumed to be in the first column
        roll_col = master_df.columns[0]
        master_df[roll_col] = master_df[roll_col].astype(str)
        
        # Generate new timestamped column
        col_name = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        master_df[col_name] = master_df[roll_col].apply(
            lambda r: "✔" if r in present_rolls else ""
        )
        
        # Save to logs directory to keep the master file intact, or update the active one
        output_filename = f"attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output_path = os.path.join(app.config['LOGS_DIR'], output_filename)
        
        # Write updated file
        master_df.to_excel(output_path, index=False)
        
        # Also overwrite the active excel path so next session builds on top of it (similar to original app)
        master_df.to_excel(excel_path, index=False)
        
        # Store log path in config for downloading
        app.config['LATEST_LOG_PATH'] = output_path
        
        # Clean up session
        core.finish()
        
        return jsonify({
            "success": True, 
            "message": f"Attendance logged successfully! Updated {len(present_rolls)} records.",
            "download_url": "/download_excel"
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error updating Excel sheet: {str(e)}"}), 500

@app.route('/download_excel', methods=['GET'])
def download_excel():
    """Downloads the latest updated attendance spreadsheet."""
    log_path = app.config.get('LATEST_LOG_PATH')
    if not log_path or not os.path.exists(log_path):
        # Fallback to the current excel_path if available
        log_path = app.config.get('EXCEL_PATH')
        
    if log_path and os.path.exists(log_path):
        filename = f"attendance_report_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return send_file(log_path, as_attachment=True, download_name=filename)
        
    return "No report available for download.", 404

if __name__ == "__main__":
    # For local running (fallback)
    app.run(host="0.0.0.0", port=7860, debug=True)
