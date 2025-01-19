import os
from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DEFAULT_PASSWORD'] = 'admin'  # Change this in production!
app.secret_key = os.urandom(24)  # Required for flash messages
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Authentication middleware
def authenticate(password):
    return password == os.getenv('UPLOAD_PASSWORD', app.config['DEFAULT_PASSWORD'])

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
            flash('Invalid password', 'error')
            return redirect(url_for('upload'))
        file = request.files.get('file')
        if not file:
            flash('No file selected', 'error')
            return redirect(url_for('upload'))
        filename = secure_filename(file.filename)
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(password))
        os.makedirs(user_folder, exist_ok=True)
        file.save(os.path.join(user_folder, filename))
        flash(f'File {filename} uploaded successfully!', 'success')
        return redirect(url_for('upload'))
    return render_template('upload.html')

# List files page
@app.route('/download', methods=['GET'])
def download_page():
    return render_template('download.html')

def get_directory_structure(path):
    items = []
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        is_dir = os.path.isdir(item_path)
        items.append({
            'name': item,
            'is_directory': is_dir,
            'path': os.path.relpath(item_path, path)
        })
    return sorted(items, key=lambda x: (not x['is_directory'], x['name']))

# List available files
@app.route('/list_files', methods=['POST'])
def list_files():
    password = request.form.get('password')
    folder_path = request.form.get('path', '')
    
    if not password or not authenticate(password):
        return "Unauthorized", 403
        
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(password))
    if not os.path.exists(user_folder):
        return jsonify([])
        
    # Ensure the requested path is within user's folder
    target_path = os.path.normpath(os.path.join(user_folder, folder_path))
    if not target_path.startswith(user_folder):
        return "Invalid path", 403
    
    if not os.path.exists(target_path):
        return "Path not found", 404
        
    items = get_directory_structure(target_path)
    return jsonify({
        'current_path': folder_path,
        'items': items
    })

@app.route('/download_file', methods=['GET'])
def download_file():
    password = request.args.get('password')
    filepath = request.args.get('filepath', '')
    
    if not password or not filepath:
        return "Password and filepath are required", 400
    if not authenticate(password):
        return "Unauthorized", 403
        
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(password))
    target_path = os.path.normpath(os.path.join(user_folder, filepath))
    
    # Security check to prevent directory traversal
    if not target_path.startswith(user_folder):
        return "Invalid path", 403
        
    if not os.path.exists(target_path):
        return "File not found", 404
    if os.path.isdir(target_path):
        return "Cannot download directories", 400
        
    return send_from_directory(os.path.dirname(target_path), 
                             os.path.basename(target_path), 
                             as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)