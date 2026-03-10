import os
import json
import time
import shutil
from utils import (
    SHIPPING_BOX_DIR, generate_short_id, get_timestamp, 
    save_uploaded_file, load_json, save_json
)

def get_shipping_dir(code):
    """Get the directory for a specific shipping code."""
    return os.path.join(SHIPPING_BOX_DIR, code)

def create_shipping(message, retention_days, uploaded_files):
    """Create a new shipping entry."""
    code = generate_short_id(6)
    shipping_dir = get_shipping_dir(code)
    
    # Ensure code is unique
    while os.path.exists(shipping_dir):
        code = generate_short_id(6)
        shipping_dir = get_shipping_dir(code)
    
    os.makedirs(shipping_dir)
    files_dir = os.path.join(shipping_dir, "files")
    os.makedirs(files_dir)
    
    file_info_list = []
    if uploaded_files:
        for file in uploaded_files:
            filename, filepath = save_uploaded_file(file, files_dir)
            file_info_list.append({
                "name": file.name,
                "path": filepath,
                "type": file.type,
                "size": file.size
            })
    
    data = {
        "code": code,
        "message": message,
        "files": file_info_list,
        "created_at": get_timestamp(),
        "expires_at": get_timestamp() + (retention_days * 86400)
    }
    
    save_json(os.path.join(shipping_dir, "info.json"), data)
    return code

def retrieve_shipping(code):
    """Retrieve shipping entry by code."""
    shipping_dir = get_shipping_dir(code)
    info_file = os.path.join(shipping_dir, "info.json")
    
    if not os.path.exists(shipping_dir) or not os.path.exists(info_file):
        return None, "无效的取件码或已过期。"
    
    data = load_json(info_file)
    
    # Check expiry
    if get_timestamp() > data.get("expires_at", 0):
        # Expired, delete it
        shutil.rmtree(shipping_dir)
        return None, "此包裹已过期。"
        
    return data, None

def clean_expired_shippings():
    """Clean all expired shipping entries."""
    if not os.path.exists(SHIPPING_BOX_DIR):
        return

    for code in os.listdir(SHIPPING_BOX_DIR):
        shipping_dir = os.path.join(SHIPPING_BOX_DIR, code)
        info_file = os.path.join(shipping_dir, "info.json")
        
        if os.path.isdir(shipping_dir):
            if os.path.exists(info_file):
                data = load_json(info_file)
                if get_timestamp() > data.get("expires_at", 0):
                    shutil.rmtree(shipping_dir)
            else:
                # Invalid directory, maybe delete?
                pass
