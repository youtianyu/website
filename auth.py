import os
import json
import streamlit as st
import hashlib
from utils import USERS_FILE, load_json, save_json

def get_admin_credentials():
    """Get admin credentials from Streamlit secrets."""
    try:
        if hasattr(st, 'secrets') and "admin" in st.secrets:
            return {
                "username": st.secrets["admin"].get("username", "admin"),
                "password": st.secrets["admin"].get("password", "admin")
            }
    except Exception:
        pass
    return {"username": "admin", "password": "admin"}

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """Verify a stored password against one provided by user."""
    return stored_password == hashlib.sha256(provided_password.encode()).hexdigest()

def ensure_users_file():
    """Ensure the users file exists and has an admin account."""
    if not os.path.exists(USERS_FILE):
        admin_creds = get_admin_credentials()
        users = {
            admin_creds["username"]: {
                "password": hash_password(admin_creds["password"]),
                "is_admin": True,
                "created_groups": []
            }
        }
        save_json(USERS_FILE, users)

@st.cache_data(ttl=60)
def get_users():
    """Load all users with caching (TTL=60s)."""
    ensure_users_file()
    return load_json(USERS_FILE, {})

def clear_users_cache():
    """Clear users cache."""
    get_users.clear()

def save_users(users):
    """Save all users and clear cache."""
    save_json(USERS_FILE, users)
    clear_users_cache()

def login(username, password):
    """Attempt to log in a user."""
    users = get_users()
    if username in users:
        # Re-hashing here is fast, but we can cache verify_password if needed
        # But password checking is security critical, avoid caching result.
        if verify_password(users[username]["password"], password):
            st.session_state["username"] = username
            st.session_state["is_admin"] = users[username].get("is_admin", False)
            st.session_state["logged_in"] = True
            return True
    return False

def register(username, password):
    """Register a new user."""
    users = get_users()
    if username in users:
        return False, "用户名已存在。"
    
    users[username] = {
        "password": hash_password(password),
        "is_admin": False,
        "created_groups": []
    }
    save_users(users)
    return True, "注册成功。请登录。"

def logout():
    """Log out the current user."""
    st.session_state.clear()
    st.rerun()

def is_logged_in():
    """Check if a user is logged in."""
    return st.session_state.get("logged_in", False)

def get_current_user():
    """Get the current logged in username."""
    return st.session_state.get("username", None)

def is_admin():
    """Check if the current user is an admin."""
    return st.session_state.get("is_admin", False)

def get_user_created_groups(username=None):
    """Get the list of groups created by a user."""
    if username is None:
        username = get_current_user()
    if not username:
        return []
    
    users = get_users()
    return users.get(username, {}).get("created_groups", [])

def add_created_group(username, group_id):
    """Add a group ID to the user's created groups list."""
    users = get_users()
    if username in users:
        if "created_groups" not in users[username]:
            users[username]["created_groups"] = []
        users[username]["created_groups"].append(group_id)
        save_users(users)

def remove_created_group(username, group_id):
    """Remove a group ID from the user's created groups list."""
    users = get_users()
    if username in users:
        if "created_groups" in users[username]:
            if group_id in users[username]["created_groups"]:
                users[username]["created_groups"].remove(group_id)
                save_users(users)

def change_password(username, new_password):
    """Change user password."""
    users = get_users()
    if username in users:
        users[username]["password"] = hash_password(new_password)
        save_users(users)
        return True, "密码修改成功。"
    return False, "用户未找到。"

def reset_user_password(username, new_password):
    """Reset user password (admin only)."""
    return change_password(username, new_password)

def delete_user(username):
    """Delete a user."""
    users = get_users()
    if username in users:
        del users[username]
        save_users(users)
        return True, "用户已删除。"
    return False, "用户未找到。"
