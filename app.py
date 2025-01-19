from flask import Flask, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
import os

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Configurations
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['SECRET_KEY'] = bcrypt.generate_password_hash('simplepassword').decode('utf-8')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Authentication middleware
def authenticate(password):
    return bcrypt.check_password_hash(app.config['SECRET_KEY'], password)

# Routes
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        return "Upload endpoint. Use POST to upload files.", 200
    password = request.form.get('password')
    if not authenticate(password):
        return jsonify({"error": "Unauthorized"}), 403
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    filename = secure_filename(file.filename)
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], password)
    os.makedirs(user_folder, exist_ok=True)
    file.save(os.path.join(user_folder, filename))
    return jsonify({"message": f"File {filename} uploaded successfully"}), 200



@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    # Get the password from the query string
    password = request.args.get('password', None)
    if not password:
        return jsonify({"error": "Password is required"}), 400

    if not authenticate(password):
        return jsonify({"error": "Unauthorized"}), 403

    # Validate user folder
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], password)
    if not os.path.exists(user_folder):
        return jsonify({"error": "User folder not found"}), 404

    # Validate file existence
    file_path = os.path.join(user_folder, filename)
    if not os.path.isfile(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_from_directory(user_folder, filename, as_attachment=True)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
