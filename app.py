import os
import json
from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = os.urandom(24)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['ADMIN_USERNAME'] = os.getenv('ADMIN_USERNAME', 'admin')
app.config['ADMIN_PASSWORD'] = os.getenv('ADMIN_PASSWORD', 'adminpass')  # Change this!

def is_admin():
    return (session.get('is_admin') and 
            session.get('admin_auth') == f"{app.config['ADMIN_USERNAME']}:{app.config['ADMIN_PASSWORD']}")

# User management
USERS_FILE = 'users.json'

def load_users():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading users file: {e}")
        # If there's an error reading the file, backup the corrupted file
        if os.path.exists(USERS_FILE):
            backup_file = f"{USERS_FILE}.backup"
            try:
                os.rename(USERS_FILE, backup_file)
                print(f"Corrupted {USERS_FILE} backed up to {backup_file}")
            except OSError as e:
                print(f"Error backing up corrupted file: {e}")
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def init_user_folder(username, root_folder):
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(username), secure_filename(root_folder))
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def get_directory_structure(path):
    items = []
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            is_dir = os.path.isdir(item_path)
            items.append({
                'name': item,
                'is_directory': is_dir,
                'path': os.path.relpath(item_path, path)
            })
    except Exception as e:
        print(f"Error reading directory {path}: {e}")
        return []
    return sorted(items, key=lambda x: (not x['is_directory'], x['name'].lower()))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        root_folder = request.form.get('root_folder')
        
        users = load_users()
        if username in users:
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
            
        users[username] = {
            'password': generate_password_hash(password),
            'root_folder': secure_filename(root_folder)
        }
        save_users(users)
        init_user_folder(username, root_folder)
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        users = load_users()
        user = users.get(username)
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['root_folder'] = user['root_folder']
            return redirect(url_for('files'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('files'))
    return redirect(url_for('login'))

@app.route('/files')
def files():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    app.logger.info(f"Loading files page for user: {session['username']}")
    return render_template('files.html', 
                         username=session['username'],
                         root_folder=session['root_folder'])

@app.route('/create_folder', methods=['POST'])
def create_folder():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    folder_name = request.form.get('folder_name')
    parent_path = request.form.get('parent_path', '')
    
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                            secure_filename(session['username']),
                            secure_filename(session['root_folder']))
    new_folder_path = os.path.normpath(os.path.join(base_path, parent_path, secure_filename(folder_name)))
    
    if not new_folder_path.startswith(base_path):
        return jsonify({'error': 'Invalid path'}), 403
        
    os.makedirs(new_folder_path, exist_ok=True)
    return jsonify({'success': True})

@app.route('/delete_file', methods=['POST'])
def delete_file():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
        
    filepath = request.form.get('filepath')
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                            secure_filename(session['username']),
                            secure_filename(session['root_folder']))
    full_path = os.path.normpath(os.path.join(base_path, filepath))
    
    if not full_path.startswith(base_path):
        return jsonify({'error': 'Invalid path'}), 403
        
    try:
        os.remove(full_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Modify list_files to use session
@app.route('/list_files', methods=['POST'])
def list_files():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        folder_path = request.form.get('path', '')
        base_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                                secure_filename(session['username']),
                                secure_filename(session['root_folder']))
        
        target_path = os.path.normpath(os.path.join(base_path, folder_path))
        if not target_path.startswith(base_path):
            return jsonify({'error': 'Invalid path'}), 403
        
        if not os.path.exists(target_path):
            return jsonify({
                'current_path': folder_path,
                'items': []
            })
        
        items = get_directory_structure(target_path)
        return jsonify({
            'current_path': folder_path,
            'items': items
        })
    except Exception as e:
        app.logger.error(f"Error listing files: {e}")
        return jsonify({'error': 'Error listing files'}), 500

# Modify upload endpoint
@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
        
    file = request.files.get('file')
    current_path = request.form.get('current_path', '')
    
    if not file:
        return jsonify({'error': 'No file provided'}), 400
        
    filename = secure_filename(file.filename)
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                            secure_filename(session['username']),
                            secure_filename(session['root_folder']))
    
    upload_path = os.path.normpath(os.path.join(base_path, current_path))
    if not upload_path.startswith(base_path):
        return jsonify({'error': 'Invalid path'}), 403
        
    file.save(os.path.join(upload_path, filename))
    return jsonify({'success': True})

@app.route('/download_file', methods=['GET'])
def download_file():
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
        
    filepath = request.args.get('filepath', '')
    
    if not filepath:
        return "Filepath is required", 400
        
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(session['username']), secure_filename(session['root_folder']))
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

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if is_admin():
        return redirect(url_for('admin_panel'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        app.logger.info(f"Admin login attempt: {username}")  # Add logging
        
        if (username == app.config['ADMIN_USERNAME'] and 
            password == app.config['ADMIN_PASSWORD']):
            session['is_admin'] = True
            session['admin_auth'] = f"{username}:{password}"
            return redirect(url_for('admin_panel'))
        flash('Invalid admin credentials', 'error')
        
    return render_template('admin_login.html', error=request.args.get('error'))

@app.route('/admin')
def admin_panel():
    if not is_admin():
        app.logger.warning("Unauthorized admin access attempt")  # Add logging
        return redirect(url_for('admin_login', error='Please login as admin first'))
    
    try:    
        users = load_users()
        if users is None:
            users = {}
        app.logger.info(f"Admin panel loaded with {len(users)} users")  # Add logging
        return render_template('admin_panel.html', users=users)
    except Exception as e:
        app.logger.error(f"Error in admin panel: {e}")  # Add logging
        flash('Error loading users data', 'error')
        return render_template('admin_panel.html', users={})

# Add admin logout route
@app.route('/admin/logout')
def admin_logout():
    if 'is_admin' in session:
        session.pop('is_admin')
        session.pop('admin_auth', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)