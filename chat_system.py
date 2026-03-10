import streamlit as st
import os
import json
import time
import shutil
from datetime import datetime, timedelta
from utils import (
    load_json, save_json, generate_id, get_timestamp, format_time,
    save_uploaded_file, delete_directory, PUBLIC_CHAT_DIR, GROUP_CHATS_DIR,
    DATA_DIR
)
import auth
import admin
import hashlib

PUBLIC_CHAT_ID = "public"
DM_DIR = os.path.join(DATA_DIR, "direct_messages")

if not os.path.exists(DM_DIR):
    os.makedirs(DM_DIR)

def get_dm_id(user1, user2):
    """Generate a consistent DM ID for two users."""
    users = sorted([user1, user2])
    return hashlib.md5(f"{users[0]}_{users[1]}".encode()).hexdigest()

def get_dm_dir(dm_id):
    """Get directory for a DM."""
    return os.path.join(DM_DIR, dm_id)

def get_dm_messages_file(dm_id):
    """Get messages file for a DM."""
    return os.path.join(get_dm_dir(dm_id), "messages.json")

def get_dm_files_dir(dm_id):
    """Get files directory for a DM."""
    return os.path.join(get_dm_dir(dm_id), "files")

def save_dm_message(user1, user2, sender, content, uploaded_files=None):
    """Save a direct message."""
    dm_id = get_dm_id(user1, user2)
    dm_dir = get_dm_dir(dm_id)
    files_dir = get_dm_files_dir(dm_id)
    
    if not os.path.exists(dm_dir):
        os.makedirs(dm_dir)
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
            
    message = {
        "id": generate_id(),
        "user": sender,
        "content": content,
        "files": file_info_list,
        "timestamp": get_timestamp(),
        "date_str": format_time(get_timestamp())
    }
    
    messages = load_json(get_dm_messages_file(dm_id), [])
    messages.append(message)
    save_json(get_dm_messages_file(dm_id), messages)
    return True

def load_dm_messages(user1, user2):
    """Load DM messages."""
    dm_id = get_dm_id(user1, user2)
    filepath = get_dm_messages_file(dm_id)
    if not os.path.exists(filepath):
        return []
    return load_json(filepath, [])

def get_chat_dir(chat_id):
    """Get the directory for a specific chat."""
    if chat_id == PUBLIC_CHAT_ID:
        return PUBLIC_CHAT_DIR
    return os.path.join(GROUP_CHATS_DIR, chat_id)

def get_messages_file(chat_id):
    """Get the messages file path."""
    return os.path.join(get_chat_dir(chat_id), "messages.json")

def get_config_file(chat_id):
    """Get the config file path (for group chats)."""
    return os.path.join(get_chat_dir(chat_id), "config.json")

def get_files_dir(chat_id):
    """Get the files directory for a chat."""
    return os.path.join(get_chat_dir(chat_id), "files")

def load_messages(chat_id):
    """Load messages for a chat."""
    filepath = get_messages_file(chat_id)
    if not os.path.exists(filepath):
        return []
    return load_json(filepath, [])

def save_message(chat_id, user, content, uploaded_files=None):
    """Save a message to the chat history."""
    chat_dir = get_chat_dir(chat_id)
    files_dir = get_files_dir(chat_id)
    
    if not os.path.exists(files_dir):
        os.makedirs(files_dir)
    
    # Check limits for Public Chat
    if chat_id == PUBLIC_CHAT_ID:
        config = admin.load_system_config()
        max_msgs = config.get("max_public_msg_count", 200)
        retention = config.get("max_public_msg_retention_days", 7)
        clean_expired_messages(chat_id, retention)
    
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
    
    message = {
        "id": generate_id(),
        "user": user,
        "content": content,
        "files": file_info_list,
        "timestamp": get_timestamp(),
        "date_str": format_time(get_timestamp())
    }
    
    messages = load_messages(chat_id)
    messages.append(message)
    
    # Trim if public
    if chat_id == PUBLIC_CHAT_ID and len(messages) > max_msgs:
        messages = messages[-max_msgs:]
        
    save_json(get_messages_file(chat_id), messages)
    return True

def get_unread_counts(user):
    """Get unread message counts for a user."""
    users = auth.get_users()
    if user not in users:
        return {}
    
    last_read = users[user].get("last_read", {})
    counts = {"total": 0, "groups": {}, "dms": {}, "public": 0}
    
    # Public Chat
    msgs = load_messages(PUBLIC_CHAT_ID)
    lr = last_read.get(PUBLIC_CHAT_ID, 0)
    cnt = sum(1 for m in msgs if m["timestamp"] > lr)
    counts["public"] = cnt
    # Public chat doesn't count towards sidebar total typically, or does it?
    # User said "除了公共聊天" (excluding public chat) for total.
    
    # Group Chats
    user_groups = users[user].get("created_groups", []) # Only created? No, should be joined.
    # Currently implementation doesn't have explicit "join" list, it relies on knowing the code or being owner.
    # But to track unread, we need to know which groups the user is interested in.
    # For now, let's just scan all groups user has "entered" in session? No, that's temporary.
    # Let's assume user is interested in groups they created + groups they have visited (we need to store this).
    # Since we don't have a "joined_groups" list, let's add it to auth.
    
    joined_groups = users[user].get("joined_groups", [])
    # Also include created groups
    all_my_groups = list(set(joined_groups + users[user].get("created_groups", [])))
    
    for gid in all_my_groups:
        msgs = load_messages(gid)
        lr = last_read.get(gid, 0)
        c = sum(1 for m in msgs if m["timestamp"] > lr)
        counts["groups"][gid] = c
        counts["total"] += c
        
    # DMs
    # Scan all DMs involving user
    # This is inefficient if many DMs.
    # Better: store list of DM partners in user profile.
    dm_partners = users[user].get("dm_partners", [])
    for partner in dm_partners:
        msgs = load_dm_messages(user, partner)
        # DM ID
        dm_id = get_dm_id(user, partner)
        lr = last_read.get(dm_id, 0)
        c = sum(1 for m in msgs if m["timestamp"] > lr)
        counts["dms"][partner] = c
        counts["total"] += c
        
    return counts

def mark_as_read(user, chat_id_or_type, partner=None):
    """Mark a chat as read."""
    users = auth.get_users()
    if user not in users:
        return
    
    if "last_read" not in users[user]:
        users[user]["last_read"] = {}
        
    key = chat_id_or_type
    if partner:
        key = get_dm_id(user, partner)
        
    users[user]["last_read"][key] = get_timestamp()
    auth.save_users(users)

def add_joined_group(user, group_id):
    """Add group to user's joined list."""
    users = auth.get_users()
    if user in users:
        if "joined_groups" not in users[user]:
            users[user]["joined_groups"] = []
        if group_id not in users[user]["joined_groups"]:
            users[user]["joined_groups"].append(group_id)
            auth.save_users(users)

def add_dm_partner(user, partner):
    """Add DM partner to user's list."""
    users = auth.get_users()
    changed = False
    if user in users:
        if "dm_partners" not in users[user]:
            users[user]["dm_partners"] = []
        if partner not in users[user]["dm_partners"]:
            users[user]["dm_partners"].append(partner)
            changed = True
            
    if partner in users:
        if "dm_partners" not in users[partner]:
            users[partner]["dm_partners"] = []
        if user not in users[partner]["dm_partners"]:
            users[partner]["dm_partners"].append(user)
            changed = True
            
    if changed:
        auth.save_users(users)

def create_group_chat(name, code, expiry_days, retention_days, owner):
    """Create a new group chat."""
    # Check if code already exists
    if check_group_code_exists(code):
        return False, "该群组代码已被使用，请使用其他代码。"
    
    # Check limits
    config = admin.load_system_config()
    user_groups = auth.get_user_created_groups(owner)
    
    if len(user_groups) >= config["max_groups_per_user"] and not auth.is_admin():
        return False, "您已达到允许创建的最大群组数。"
    
    if expiry_days > config["max_group_life_days"] and not auth.is_admin():
        return False, f"群组最长存在时间为 {config['max_group_life_days']} 天。"
        
    if retention_days > config["max_msg_retention_days"] and not auth.is_admin():
        return False, f"消息最长保留时间为 {config['max_msg_retention_days']} 天。"

    group_id = generate_id()
    group_dir = os.path.join(GROUP_CHATS_DIR, group_id)
    os.makedirs(group_dir)
    os.makedirs(os.path.join(group_dir, "files"))
    
    group_config = {
        "id": group_id,
        "name": name,
        "code": code,
        "owner": owner,
        "created_at": get_timestamp(),
        "expiry_days": expiry_days,
        "retention_days": retention_days,
        "expires_at": get_timestamp() + (expiry_days * 86400)
    }
    
    save_json(os.path.join(group_dir, "config.json"), group_config)
    save_json(os.path.join(group_dir, "messages.json"), [])
    
    # Add to user's created groups
    auth.add_created_group(owner, group_id)
    
    return True, group_id

def get_group_config(group_id):
    """Get group configuration."""
    return load_json(get_config_file(group_id), {})

def verify_group_code(group_id, code):
    """Verify group code."""
    config = get_group_config(group_id)
    return config.get("code") == code

def delete_group_chat(group_id):
    """Delete a group chat."""
    config = get_group_config(group_id)
    owner = config.get("owner")
    
    if delete_directory(get_chat_dir(group_id)):
        if owner:
            auth.remove_created_group(owner, group_id)
        return True
    return False

def clean_expired_messages(chat_id, retention_days):
    """Clean messages older than retention period."""
    messages = load_messages(chat_id)
    if not messages:
        return
    
    cutoff_time = get_timestamp() - (retention_days * 86400)
    new_messages = [msg for msg in messages if msg["timestamp"] > cutoff_time]
    
    if len(new_messages) < len(messages):
        # Delete files associated with removed messages
        removed_messages = [msg for msg in messages if msg["timestamp"] <= cutoff_time]
        for msg in removed_messages:
            for file_info in msg.get("files", []):
                if os.path.exists(file_info["path"]):
                    try:
                        os.remove(file_info["path"])
                    except:
                        pass
        save_json(get_messages_file(chat_id), new_messages)

def clean_expired_groups():
    """Clean expired groups."""
    if not os.path.exists(GROUP_CHATS_DIR):
        return

    for group_id in os.listdir(GROUP_CHATS_DIR):
        config = get_group_config(group_id)
        if not config:
            continue
            
        if get_timestamp() > config.get("expires_at", 0):
            delete_group_chat(group_id)

def check_group_code_exists(code):
    """Check if a group with the given code already exists."""
    if not os.path.exists(GROUP_CHATS_DIR):
        return False
    
    for group_id in os.listdir(GROUP_CHATS_DIR):
        config = get_group_config(group_id)
        if config and config.get("code") == code:
            return True
    return False

def check_user_in_group_by_code(username, code):
    """Check if user is already in a group with the given code."""
    if not username:
        return False
    
    users = auth.get_users()
    if username not in users:
        return False
    
    user_data = users.get(username, {})
    joined_groups = user_data.get("joined_groups", [])
    
    for group_id in joined_groups:
        config = get_group_config(group_id)
        if config and config.get("code") == code:
            return True
    return False

def update_group_settings(group_id, expiry_days, retention_days, new_owner=None):
    """Update group settings."""
    config = get_group_config(group_id)
    
    # Verify limits again if not admin (though this function is usually called by owner)
    sys_config = admin.load_system_config()
    
    if expiry_days > sys_config["max_group_life_days"] and not auth.is_admin():
        return False, f"群组最长存在时间为 {sys_config['max_group_life_days']} 天。"
    
    if retention_days > sys_config["max_msg_retention_days"] and not auth.is_admin():
        return False, f"消息最长保留时间为 {sys_config['max_msg_retention_days']} 天。"
    
    config["expiry_days"] = expiry_days
    config["retention_days"] = retention_days
    # Recalculate expiry based on creation time or just extend from now? 
    # Usually extend from creation or set absolute expiry. Let's keep it simple:
    # Update expires_at based on creation time + new expiry_days
    config["expires_at"] = config["created_at"] + (expiry_days * 86400)
    
    if new_owner:
        # Check if new owner exists
        users = auth.get_users()
        if new_owner in users:
            old_owner = config["owner"]
            config["owner"] = new_owner
            auth.remove_created_group(old_owner, group_id)
            auth.add_created_group(new_owner, group_id)
        else:
            return False, "新群主不存在。"
            
    save_json(get_config_file(group_id), config)
    return True, "设置已更新。"

def find_group_by_code(code):
    """Find a group ID by its code. (Note: Codes might not be unique, but let's assume they should be or return list)"""
    # This is inefficient if there are many groups. A mapping file would be better.
    # For now, iterate.
    if not os.path.exists(GROUP_CHATS_DIR):
        return []
        
    found_groups = []
    for group_id in os.listdir(GROUP_CHATS_DIR):
        config = get_group_config(group_id)
        if config.get("code") == code:
            found_groups.append(config)
    return found_groups

