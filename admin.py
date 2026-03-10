import streamlit as st
import json
import os
from utils import SYSTEM_CONFIG_FILE, load_json, save_json

DEFAULT_CONFIG = {
    "max_groups_per_user": 5,
    "max_group_life_days": 30,
    "max_msg_retention_days": 7,
    "max_public_msg_count": 200,
    "max_public_msg_retention_days": 7
}

@st.cache_data(ttl=600)
def load_system_config():
    """Load system configuration with caching (TTL=10min)."""
    config = load_json(SYSTEM_CONFIG_FILE, {})
    # Merge with default to ensure all keys exist
    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value
    return config

def clear_system_config_cache():
    """Clear config cache."""
    load_system_config.clear()

def save_system_config(config):
    """Save system configuration and clear cache."""
    save_json(SYSTEM_CONFIG_FILE, config)
    clear_system_config_cache()

def get_config_value(key):
    """Get a specific configuration value."""
    config = load_system_config()
    return config.get(key, DEFAULT_CONFIG.get(key))

def admin_dashboard():
    """Render the admin dashboard."""
    st.header("管理员控制台")
    
    config = load_system_config()
    
    st.subheader("系统配置")
    with st.form("system_config_form"):
        max_groups = st.number_input("每位用户最大群组数", min_value=1, value=config["max_groups_per_user"])
        max_life = st.number_input("群组最长存在时间 (天)", min_value=1, value=config["max_group_life_days"])
        max_retention = st.number_input("消息最长保留时间 (天)", min_value=1, value=config["max_msg_retention_days"])
        max_public_msgs = st.number_input("公共聊天最大消息数", min_value=1, value=config.get("max_public_msg_count", 200))
        max_public_retention = st.number_input("公共聊天保留时间 (天)", min_value=1, value=config.get("max_public_msg_retention_days", 7))
        
        submitted = st.form_submit_button("保存配置")
        if submitted:
            config["max_groups_per_user"] = max_groups
            config["max_group_life_days"] = max_life
            config["max_msg_retention_days"] = max_retention
            config["max_public_msg_count"] = max_public_msgs
            config["max_public_msg_retention_days"] = max_public_retention
            save_system_config(config)
            st.success("配置保存成功！")
    
    st.subheader("用户管理")
    import auth
    users = auth.get_users()
    st.write(f"总用户数: {len(users)}")
    
    user_list = []
    for u, data in users.items():
        user_list.append({
            "用户名": u,
            "管理员": data.get("is_admin", False),
            "创建的群组数": len(data.get("created_groups", []))
        })
    st.dataframe(user_list)

    with st.expander("管理用户"):
        selected_user = st.selectbox("选择用户", [u for u in users.keys()])
        action = st.radio("操作", ["重置密码", "删除用户", "切换管理员权限"])
        
        if action == "重置密码":
            new_pass = st.text_input("新密码", type="password", key="admin_reset_pass")
            if st.button("重置密码"):
                if new_pass:
                    auth.reset_user_password(selected_user, new_pass)
                    st.success(f"已重置 {selected_user} 的密码")
                else:
                    st.error("请输入密码")
                    
        elif action == "删除用户":
            if st.button("删除用户", type="primary"):
                if selected_user == "admin":
                    st.error("无法删除主管理员。")
                else:
                    auth.delete_user(selected_user)
                    st.success(f"用户 {selected_user} 已删除")
                    st.rerun()

        elif action == "切换管理员权限":
             if st.button("切换管理员状态"):
                if selected_user == "admin":
                    st.error("无法更改主管理员状态。")
                else:
                    users[selected_user]["is_admin"] = not users[selected_user]["is_admin"]
                    auth.save_users(users)
                    st.success(f"已切换 {selected_user} 的管理员状态")
                    st.rerun()

