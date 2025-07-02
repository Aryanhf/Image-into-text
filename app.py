from flask import Flask, render_template, request, jsonify, abort
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
import os
import logging

# --- Configuration ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

# Path to tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- Flask App Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Logging ---
logging.basicConfig(level=logging.INFO)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large. Max 5MB allowed.'}), 413

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    # 1. Check file part
    if 'image' not in request.files:
        return jsonify({'error': 'No file part.'}), 400

    file = request.files['image']

    # 2. Check filename
    if file.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    # 3. Save securely
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    try:
        file.save(filepath)
    except Exception as e:
        logging.exception("Failed to save uploaded file")
        return jsonify({'error': 'Failed to save file.'}), 500

    try:
        # 4. Open and preprocess
        with Image.open(filepath) as img:
            gray = img.convert('L')

            # 5. OCR
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(gray, config=custom_config)

    except Exception as e:
        logging.exception("OCR processing failed")
        # Clean up on error
        try: os.remove(filepath)
        except: pass
        return jsonify({'error': 'Failed to process image.'}), 500

    # 6. Clean up file
    try:
        os.remove(filepath)
    except Exception:
        logging.warning(f"Could not delete temp file {filepath}")

    # 7. Return result
    return jsonify({'text': text}), 200

if __name__ == '__main__':
    app.run(debug=True)
