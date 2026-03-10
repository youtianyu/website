import os
import shutil
import streamlit as st
from utils import USER_FILES_DIR, create_zip_archive

def get_absolute_path(relative_path):
    """Get absolute path and ensure it's safe."""
    # Normalize path separators
    relative_path = relative_path.replace("\\", "/").strip("/")
    abs_path = os.path.join(USER_FILES_DIR, relative_path)
    
    # Security check: ensure path is within USER_FILES_DIR
    if not os.path.abspath(abs_path).startswith(os.path.abspath(USER_FILES_DIR)):
        return None
    return abs_path

@st.cache_data(ttl=5)
def list_files(relative_path):
    """List files and directories with short TTL caching."""
    abs_path = get_absolute_path(relative_path)
    if not abs_path or not os.path.exists(abs_path):
        return [], []
    
    dirs = []
    files = []
    try:
        for item in os.listdir(abs_path):
            item_path = os.path.join(abs_path, item)
            if os.path.isdir(item_path):
                dirs.append(item)
            else:
                files.append(item)
    except PermissionError:
        pass
        
    return dirs, files

def clear_files_cache():
    """Clear file list cache."""
    list_files.clear()

def create_folder(relative_path, folder_name):
    """Create a new folder."""
    abs_path = get_absolute_path(os.path.join(relative_path, folder_name))
    if not abs_path:
        return False, "无效的路径。"
    
    if os.path.exists(abs_path):
        return False, "文件夹已存在。"
    
    try:
        os.makedirs(abs_path)
        clear_files_cache()
        return True, "文件夹已创建。"
    except Exception as e:
        return False, str(e)

def delete_item(relative_path, item_name):
    """Delete a file or folder."""
    abs_path = get_absolute_path(os.path.join(relative_path, item_name))
    if not abs_path or not os.path.exists(abs_path):
        return False, "项目未找到。"
    
    try:
        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)
        clear_files_cache()
        return True, "项目已删除。"
    except Exception as e:
        return False, str(e)

def rename_item(relative_path, old_name, new_name):
    """Rename a file or folder."""
    old_path = get_absolute_path(os.path.join(relative_path, old_name))
    new_path = get_absolute_path(os.path.join(relative_path, new_name))
    
    if not old_path or not new_path:
        return False, "无效的路径。"
        
    if not os.path.exists(old_path):
        return False, "项目未找到。"
        
    if os.path.exists(new_path):
        return False, "目标已存在。"
        
    try:
        os.rename(old_path, new_path)
        clear_files_cache()
        return True, "项目已重命名。"
    except Exception as e:
        return False, str(e)

def delete_items(relative_path, item_names):
    """Delete multiple items."""
    success_count = 0
    for item in item_names:
        if delete_item(relative_path, item):
            success_count += 1
    return success_count

def move_items(relative_path, item_names, dest_folder_name):
    """Move multiple items to a subfolder."""
    source_dir = get_absolute_path(relative_path)
    dest_dir = get_absolute_path(os.path.join(relative_path, dest_folder_name))
    
    if not source_dir or not dest_dir or not os.path.exists(dest_dir):
        return 0
        
    success_count = 0
    for item in item_names:
        s_path = os.path.join(source_dir, item)
        d_path = os.path.join(dest_dir, item)
        try:
            shutil.move(s_path, d_path)
            success_count += 1
        except Exception:
            pass
            
    clear_files_cache()
    return success_count

def copy_items(relative_path, item_names, dest_folder_name):
    """Copy multiple items to a subfolder."""
    source_dir = get_absolute_path(relative_path)
    dest_dir = get_absolute_path(os.path.join(relative_path, dest_folder_name))
    
    if not source_dir or not dest_dir or not os.path.exists(dest_dir):
        return 0
        
    success_count = 0
    for item in item_names:
        s_path = os.path.join(source_dir, item)
        d_path = os.path.join(dest_dir, item)
        try:
            if os.path.isdir(s_path):
                shutil.copytree(s_path, d_path)
            else:
                shutil.copy2(s_path, d_path)
            success_count += 1
        except Exception:
            pass
            
    clear_files_cache()
    return success_count

def paste_items(source_path, items, dest_path, action, items_are_full_paths=False):
    """Paste items from source to destination.
    
    Args:
        source_path: Source directory relative path
        items: List of item names or full relative paths
        dest_path: Destination directory relative path
        action: 'copy' or 'move'
        items_are_full_paths: If True, items are full relative paths from USER_FILES_DIR
    """
    dest_abs = get_absolute_path(dest_path)
    
    if not dest_abs or not os.path.exists(dest_abs):
        return 0, ["无效的目标路径。"]
        
    success_count = 0
    errors = []
    
    for item in items:
        if items_are_full_paths:
            # Items are full relative paths from USER_FILES_DIR (e.g., from search results)
            src_abs = USER_FILES_DIR
            s_item = os.path.join(src_abs, item)
        else:
            # Items are item names, need to combine with source_path
            src_abs = get_absolute_path(source_path)
            if not src_abs or not os.path.exists(src_abs):
                continue
            s_item = os.path.join(src_abs, item)
        
        d_item = os.path.join(dest_abs, os.path.basename(item) if items_are_full_paths else item)
        
        if not os.path.exists(s_item):
            errors.append(f"{item} 源文件不存在")
            continue
            
        if os.path.exists(d_item):
            errors.append(f"{os.path.basename(item)} 已存在于目标位置")
            continue
            
        try:
            if action == 'move':
                shutil.move(s_item, d_item)
            elif action == 'copy':
                if os.path.isdir(s_item):
                    shutil.copytree(s_item, d_item)
                else:
                    shutil.copy2(s_item, d_item)
            success_count += 1
        except Exception as e:
            errors.append(f"{item}: {str(e)}")
            
    clear_files_cache()
    return success_count, errors

def search_files(relative_path, query):
    """Recursively search for files in a directory."""
    abs_path = get_absolute_path(relative_path)
    if not abs_path:
        return []
    
    results = []
    try:
        for root, dirs, files in os.walk(abs_path):
            for file in files:
                if query.lower() in file.lower():
                    # Return relative path from USER_FILES_DIR
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, USER_FILES_DIR).replace("\\", "/")
                    results.append(rel_path)
    except Exception:
        pass
    return results

def download_folder_zip(relative_path, folder_name):
    """Create a zip of a folder for download."""
    folder_path = get_absolute_path(os.path.join(relative_path, folder_name))
    if not folder_path or not os.path.exists(folder_path):
        return None
    
    zip_filename = os.path.join(USER_FILES_DIR, f"{folder_name}.zip")
    success, _ = create_zip_archive(folder_path, zip_filename)
    
    if success:
        return zip_filename
    return None

def download_selected_zip(relative_path, item_names, zip_name="selected_files.zip"):
    """Create a zip of selected items."""
    abs_root = get_absolute_path(relative_path)
    if not abs_root:
        return None
    
    file_list = []
    for item in item_names:
        item_path = os.path.join(abs_root, item)
        # If item is directory, we need to walk it? 
        # utils.create_zip_from_files usually expects files.
        # But we can handle folders too if we want complex logic.
        # For simplicity, if it's a folder, maybe we should skip or recursively add?
        # Let's support both.
        if os.path.isdir(item_path):
            for root, _, files in os.walk(item_path):
                for f in files:
                    file_list.append(os.path.join(root, f))
        elif os.path.isfile(item_path):
            file_list.append(item_path)
            
    zip_filename = os.path.join(USER_FILES_DIR, zip_name)
    from utils import create_zip_from_files
    success, _ = create_zip_from_files(file_list, abs_root, zip_filename)
    
    if success:
        return zip_filename
    return None

def handle_file_upload(relative_path, uploaded_files):
    """Handle multiple file uploads."""
    abs_path = get_absolute_path(relative_path)
    if not abs_path:
        return False, "无效的路径。"
        
    if not os.path.exists(abs_path):
        os.makedirs(abs_path)
        
    count = 0
    for file in uploaded_files:
        try:
            with open(os.path.join(abs_path, file.name), "wb") as f:
                f.write(file.getbuffer())
            count += 1
        except Exception as e:
            return False, f"保存 {file.name} 时出错: {e}"
            
    clear_files_cache()
    return True, f"已上传 {count} 个文件。"
