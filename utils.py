import os
import json
import uuid
import time
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import streamlit as st

# Global ThreadPool for background tasks
executor = ThreadPoolExecutor(max_workers=2)

def run_in_background(func, *args, **kwargs):
    """Run a function in a background thread."""
    executor.submit(func, *args, **kwargs)

# Data Directories
DATA_DIR = os.path.join(os.getcwd(), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SYSTEM_CONFIG_FILE = os.path.join(DATA_DIR, "system_config.json")
PUBLIC_CHAT_DIR = os.path.join(DATA_DIR, "public_chat")
GROUP_CHATS_DIR = os.path.join(DATA_DIR, "group_chats")
SHIPPING_BOX_DIR = os.path.join(DATA_DIR, "shipping_box")
USER_FILES_DIR = os.path.join(DATA_DIR, "user_files")

def ensure_directories():
    """Ensure all necessary directories exist."""
    dirs = [DATA_DIR, PUBLIC_CHAT_DIR, GROUP_CHATS_DIR, SHIPPING_BOX_DIR, USER_FILES_DIR, 
            os.path.join(PUBLIC_CHAT_DIR, "files"), os.path.join(SHIPPING_BOX_DIR, "files")]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)

def load_json(filepath, default=None):
    """Load JSON file safely."""
    if not os.path.exists(filepath):
        return default if default is not None else {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def save_json(filepath, data):
    """Save data to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def generate_id():
    """Generate a unique ID."""
    return str(uuid.uuid4())

def generate_short_id(length=6):
    """Generate a short ID for shipping codes or group codes."""
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_timestamp():
    """Get current timestamp."""
    return time.time()

def format_time(timestamp):
    """Format timestamp to string."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def save_uploaded_file(uploaded_file, destination_dir):
    """Save an uploaded file to destination directory with a safe name."""
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    
    # Prepend timestamp to filename to avoid collisions
    filename = f"{int(time.time())}_{uploaded_file.name}"
    file_path = os.path.join(destination_dir, filename)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return filename, file_path

def delete_file(file_path):
    """Delete a file safely."""
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    return False

def delete_directory(dir_path):
    """Delete a directory and its contents."""
    if os.path.isdir(dir_path):
        try:
            shutil.rmtree(dir_path)
            return True
        except Exception as e:
            print(f"Error deleting directory {dir_path}: {e}")
            return False
    return False

def create_zip_archive(source_dir, output_filename):
    """Create a zip archive of a directory."""
    try:
        shutil.make_archive(os.path.splitext(output_filename)[0], 'zip', source_dir)
        return True, output_filename
    except Exception as e:
        return False, str(e)

def create_zip_from_files(file_list, root_dir, output_filename):
    """Create a zip archive from a list of files."""
    import zipfile
    try:
        with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in file_list:
                # file_path is absolute or relative to cwd? 
                # Ideally absolute. arcname should be relative to root_dir or just filename.
                if os.path.exists(file_path):
                    arcname = os.path.relpath(file_path, root_dir) if root_dir else os.path.basename(file_path)
                    zipf.write(file_path, arcname)
        return True, output_filename
    except Exception as e:
        return False, str(e)

def get_file_type(filename):
    """Get file type category based on extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
        return 'image'
    elif ext in ['.mp3', '.wav', '.ogg', '.m4a']:
        return 'audio'
    elif ext in ['.mp4', '.mov', '.avi', '.mkv']:
        return 'video'
    elif ext in ['.pdf']:
        return 'pdf'
    elif ext in ['.txt', '.md', '.py', '.json', '.csv']:
        return 'text'
    return 'other'
