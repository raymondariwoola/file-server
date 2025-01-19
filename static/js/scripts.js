// Global variables
let currentPath = '';
let currentPassword = '';

// File listing functions
function listFiles(path = '') {
    currentPath = path;
    
    fetch('/list_files', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: `path=${encodeURIComponent(path)}`
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => updateFileList(data))
    .catch(error => {
        console.error('Error:', error);
        alert('Error loading files');
    });
}

function updateFileList(data) {
    const filesList = document.getElementById('files');
    filesList.innerHTML = '';
    document.getElementById('current-path').textContent = data.current_path || '/';

    // Add back button if in subfolder
    if (data.current_path) {
        addBackButton(filesList, data.current_path);
    }

    data.items.forEach(item => addListItem(filesList, item));
    
    // Show files list if it was hidden
    const filesListContainer = document.getElementById('files-list');
    if (filesListContainer) {
        filesListContainer.style.display = 'block';
    }
}

function addBackButton(filesList, currentPath) {
    const li = document.createElement('li');
    li.className = 'item back';
    li.innerHTML = '📁 ..';
    li.onclick = () => {
        const parentPath = currentPath.split('/').slice(0, -1).join('/');
        listFiles(parentPath);
    };
    filesList.appendChild(li);
}

function addListItem(filesList, item) {
    const li = document.createElement('li');
    li.className = 'item';
    
    const itemDiv = document.createElement('div');
    const controlsDiv = document.createElement('div');
    controlsDiv.className = 'controls';
    
    if (item.is_directory) {
        itemDiv.className = 'folder';
        itemDiv.innerHTML = `📁 ${item.name}`;
        itemDiv.onclick = () => listFiles(item.path);
    } else {
        itemDiv.className = 'file';
        itemDiv.innerHTML = `📄 ${item.name}`;
        
        const downloadBtn = document.createElement('button');
        downloadBtn.textContent = 'Download';
        downloadBtn.onclick = () => downloadFile(item.path);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.onclick = () => deleteFile(item.path);
        
        controlsDiv.appendChild(downloadBtn);
        controlsDiv.appendChild(deleteBtn);
    }
    
    li.appendChild(itemDiv);
    li.appendChild(controlsDiv);
    filesList.appendChild(li);
}

// File operations
function createFolder() {
    const folderName = document.getElementById('new-folder-name').value;
    if (!folderName) return;

    fetch('/create_folder', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `folder_name=${encodeURIComponent(folderName)}&parent_path=${encodeURIComponent(currentPath)}`
    })
    .then(response => response.json())
    .then(() => {
        document.getElementById('new-folder-name').value = '';
        listFiles(currentPath);
    })
    .catch(error => alert('Error creating folder'));
}

function uploadFile() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('current_path', currentPath);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(() => {
        fileInput.value = '';
        listFiles(currentPath);
    })
    .catch(error => alert('Error uploading file'));
}

function deleteFile(filepath) {
    if (!confirm('Are you sure you want to delete this file?')) return;

    fetch('/delete_file', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: `filepath=${encodeURIComponent(filepath)}`
    })
    .then(response => response.json())
    .then(() => listFiles(currentPath))
    .catch(error => alert('Error deleting file'));
}

function downloadFile(filepath) {
    const params = new URLSearchParams();
    if (currentPassword) params.append('password', currentPassword);
    params.append('filepath', filepath);
    window.location.href = `/download_file?${params.toString()}`;
}

// Admin functions
function deleteUser(username) {
    if (confirm(`Are you sure you want to delete user "${username}"?`)) {
        // TODO: Implement user deletion in a future update
        alert('User deletion will be implemented in a future update');
    }
}
