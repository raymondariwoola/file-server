from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Authentication middleware
def authenticate(password):
    return password == "simplepassword"

# Homepage
@app.route('/')
def index():
    return render_template('index.html')

# Upload Page
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        password = request.form.get('password')
        if not authenticate(password):
            return "Unauthorized", 403
        file = request.files.get('file')
        if file:
            filename = secure_filename(file.filename)
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], password)
            os.makedirs(user_folder, exist_ok=True)
            file.save(os.path.join(user_folder, filename))
            return f"File {filename} uploaded successfully!"
    return render_template('upload.html')

# Download Page
@app.route('/download', methods=['GET'])
def download():
    password = request.args.get('password')
    filename = request.args.get('filename')
    if not password or not filename:
        return "Password and filename are required", 400
    if not authenticate(password):
        return "Unauthorized", 403
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], password)
    if not os.path.exists(os.path.join(user_folder, filename)):
        return "File not found", 404
    return send_from_directory(user_folder, filename, as_attachment=True)
