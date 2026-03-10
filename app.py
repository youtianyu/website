import streamlit as st
import os
import time
import auth
import admin
import file_manager
import chat_system
import shipping
import utils
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Ultimate Netdisk & Chat System",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize directories
utils.ensure_directories()
auth.ensure_users_file()

# Clean up expired data on startup (Background)
utils.run_in_background(chat_system.clean_expired_groups)
utils.run_in_background(shipping.clean_expired_shippings)

# Session State Initialization
if "page" not in st.session_state:
    st.session_state.page = "Home"

def render_sidebar():
    st.sidebar.title("导航")
    
    # Navigation Buttons
    if st.sidebar.button("🏠 首页"):
        st.session_state.page = "Home"
        st.rerun()
    
    if st.sidebar.button("📂 网盘"):
        st.session_state.page = "Netdisk"
        st.rerun()
        
    if st.sidebar.button("📦 寄件箱"):
        st.session_state.page = "Shipping Box"
        st.rerun()
        
    if st.sidebar.button("💬 聊天系统"):
        st.session_state.page = "Chat System"
        st.rerun()
        
    if auth.is_logged_in():
        if st.sidebar.button("👤 用户设置"):
            st.session_state.page = "User Settings"
            st.rerun()

    if auth.is_admin():
        if st.sidebar.button("⚙️ 管理员控制台"):
            st.session_state.page = "Admin Panel"
            st.rerun()

    st.sidebar.markdown("---")
    
    # User Authentication Status
    if auth.is_logged_in():
        user = auth.get_current_user()
        # Calculate unread counts
        unread = chat_system.get_unread_counts(user)
        total_unread = unread.get("total", 0)
        
        st.session_state["unread_counts"] = unread # Store for usage in chat pages
        
        # Sidebar Notification
        if total_unread > 0:
            st.sidebar.error(f"🔔 {total_unread} 条新消息")
            
        st.sidebar.success(f"已登录: **{user}**")
        if st.sidebar.button("退出登录"):
            auth.logout()
    else:
        st.sidebar.info("访客用户")
        with st.sidebar.expander("登录 / 注册"):
            tab1, tab2 = st.tabs(["登录", "注册"])
            
            with tab1:
                with st.form("login_form"):
                    username = st.text_input("用户名")
                    password = st.text_input("密码", type="password")
                    submitted = st.form_submit_button("登录")
                    if submitted:
                        if auth.login(username, password):
                            st.success("登录成功！")
                            st.rerun()
                        else:
                            st.error("凭证无效。")
            
            with tab2:
                with st.form("register_form"):
                    new_user = st.text_input("新用户名")
                    new_pass = st.text_input("新密码", type="password")
                    confirm_pass = st.text_input("确认密码", type="password")
                    reg_submitted = st.form_submit_button("注册")
                    if reg_submitted:
                        if new_pass != confirm_pass:
                            st.error("两次输入的密码不一致。")
                        elif len(new_pass) < 4:
                            st.error("密码长度至少为4个字符。")
                        else:
                            success, msg = auth.register(new_user, new_pass)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)

def render_user_settings():
    st.title("👤 用户设置")
    
    user = auth.get_current_user()
    if not user:
        st.error("请先登录。")
        return
        
    st.subheader(f"个人资料: {user}")
    
    with st.form("change_pass_form"):
        st.write("修改密码")
        new_pass = st.text_input("新密码", type="password")
        confirm_pass = st.text_input("确认新密码", type="password")
        submitted = st.form_submit_button("更新密码")
        
        if submitted:
            if new_pass != confirm_pass:
                st.error("两次输入的密码不一致。")
            elif len(new_pass) < 4:
                st.error("密码太短。")
            else:
                success, msg = auth.change_password(user, new_pass)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

def render_home():
    st.title("欢迎使用终极网盘与聊天系统 🚀")
    st.markdown("""
    这是一个集成了以下功能的综合平台：
    - **📂 网盘**: 安全地管理您的文件。
    - **📦 寄件箱**: 使用临时取件码发送和接收文件。
    - **💬 聊天系统**: 公共和私人聊天，支持文件分享。
    - **⚙️ 管理员控制台**: 全面的系统控制。
    """)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("### 📂 文件管理器\n轻松存储和分享您的文件。")
    with col2:
        st.warning("### 📦 寄件箱\n使用取件码进行临时文件传输。")
    with col3:
        st.success("### 💬 群组聊天\n创建私人小组并安全聊天。")

def render_netdisk():
    st.title("📂 网盘 & 文件管理器")
    
    user = auth.get_current_user()
    if not user:
        st.info("您正在查看公共文件夹。登录以访问私人文件。")


    # Path management
    if "current_path" not in st.session_state:
        st.session_state.current_path = user if user else "public"
    
    # Ensure public folder exists
    if not user and not os.path.exists(os.path.join(utils.USER_FILES_DIR, "public")):
        os.makedirs(os.path.join(utils.USER_FILES_DIR, "public"))

    # Ensure user stays in their directory or subdirectories
    # If guest, stay in public
    root_dir = user if user else "public"
    if not st.session_state.current_path.startswith(root_dir):
         st.session_state.current_path = root_dir

    # Breadcrumbs
    path_parts = st.session_state.current_path.split("/")
    st.write(f"当前路径: `/{st.session_state.current_path}`")
    
    if len(path_parts) > 1:
        if st.button("⬅️ 返回"):
            st.session_state.current_path = "/".join(path_parts[:-1])
            st.rerun()

    # Operations
    # Tabs for Netdisk
    nd_tab1, nd_tab2, nd_tab3 = st.tabs(["📂 文件浏览", "📤 上传与新建", "🔍 搜索"])
    
    with nd_tab3:
        with st.expander("搜索", expanded=True):
            search_query = st.text_input("搜索文件", placeholder="在当前文件夹中搜索...", label_visibility="collapsed")
        
        if search_query:
            results = file_manager.search_files(st.session_state.current_path, search_query)
            if not results:
                st.warning("未找到文件。")
            else:
                # Search Results with Actions
                with st.form("search_results_form"):
                    st.write("##### 搜索结果")
                    selected_search_items = []
                    for res in results:
                        c1, c2, c3 = st.columns([0.05, 0.75, 0.2])
                        with c1:
                            if st.checkbox(" ", key=f"chk_search_{res}", label_visibility="collapsed"):
                                selected_search_items.append(res)
                        with c2:
                            st.write(f"📄 {res}")
                        with c3:
                            # Jump button
                            dir_path = os.path.dirname(res)
                            if st.form_submit_button("📂", key=f"jump_{res}", help=f"跳转到 {dir_path}"):
                                st.session_state.current_path = dir_path.replace("\\", "/")
                                st.rerun()

                    st.markdown("---")
                    c_act1, c_act2, c_act3, c_act4 = st.columns(4)
                    with c_act1:
                        if st.form_submit_button("🗑️ 删除所选"):
                            if selected_search_items:
                                count = 0
                                for item in selected_search_items:
                                    # search returns relative path from user root, but delete_item expects relative to current_path?
                                    # No, file_manager functions expect relative_path + item_name usually.
                                    # But search_files returns relative path from USER_FILES_DIR.
                                    # So we need to handle full path deletion.
                                    # Let's use a specialized delete for full relative paths.
                                    # Actually delete_item uses get_absolute_path which joins USER_FILES_DIR + path.
                                    # So passing the result directly to delete_item with root "" should work?
                                    # delete_item("", item) -> join(USER_FILES_DIR, "", item) -> USER_FILES_DIR/item. Correct.
                                    if file_manager.delete_item("", item):
                                        count += 1
                                st.rerun()
                    with c_act2:
                        if st.form_submit_button("📋 复制所选"):
                            if selected_search_items:
                                # For search results, items are paths relative to root.
                                # Clipboard expects simple names usually? No, it stores items.
                                # paste_items expects source path.
                                # If we have mixed paths, we can't use single source.
                                # Complex... Let's just say we copy from root with full relative paths?
                                # paste_items joins source + item.
                                # If source="", item="folder/file.txt", path = root/folder/file.txt. Correct.
                                st.session_state.clipboard = {"action": "copy", "items": selected_search_items, "source": ""}
                    with c_act3:
                        if st.form_submit_button("✂️ 移动所选"):
                            if selected_search_items:
                                st.session_state.clipboard = {"action": "move", "items": selected_search_items, "source": ""}
                    with c_act4:
                        if st.form_submit_button("📦 打包下载所选"):
                            if selected_search_items:
                                zip_path = file_manager.download_selected_zip("", selected_search_items)
                                if zip_path:
                                    with open(zip_path, "rb") as f:
                                        st.download_button("⬇️ 下载 Zip", f, file_name="search_results.zip", mime="application/zip")

    with nd_tab2:
        with st.expander("上传文件", expanded=True):
            uploaded_files = st.file_uploader("选择文件", accept_multiple_files=True)
            if uploaded_files:
                if st.button("上传"):
                    with st.spinner("正在上传文件..."):
                        success, msg = file_manager.handle_file_upload(st.session_state.current_path, uploaded_files)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
        
        with st.expander("新建文件夹", expanded=True):
            new_folder = st.text_input("文件夹名称")
            if st.button("创建文件夹"):
                if new_folder:
                    success, msg = file_manager.create_folder(st.session_state.current_path, new_folder)
                    if success:
                        st.success(msg)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)

    with nd_tab1:
        # Header Row
        h1, h2 = st.columns([0.8, 0.2])
        with h1:
            st.markdown("#### 文件列表")
        with h2:
            if st.button("📦 打包下载当前文件夹"):
                folder_name = os.path.basename(st.session_state.current_path)
                with st.spinner("正在压缩文件..."):
                    zip_path = file_manager.download_folder_zip(os.path.dirname(st.session_state.current_path), folder_name)
                if zip_path:
                    with open(zip_path, "rb") as f:
                        st.download_button(
                            label="点击下载 Zip",
                            data=f,
                            file_name=f"{folder_name}.zip",
                            mime="application/zip"
                        )
        
        dirs, files = file_manager.list_files(st.session_state.current_path)
        
        if not dirs and not files:
            st.info("此文件夹为空。")
        
        # Batch Selection
        if "selected_items" not in st.session_state:
            st.session_state.selected_items = []
            
        selected_items = []
        
        # Use columns for layout
        # Header
        c1, c2, c3, c4 = st.columns([0.05, 0.05, 0.6, 0.3])
        # We can put a "Select All" here if we wanted, but let's keep it simple.
        
        for d in dirs:
            c1, c2, c3, c4 = st.columns([0.05, 0.05, 0.6, 0.3])
            with c1:
                if st.checkbox(" ", key=f"chk_dir_{d}", label_visibility="collapsed"):
                    selected_items.append(d)
            with c2:
                st.write("📁")
            with c3:
                st.write(d)
            with c4:
                # Folder Actions
                if st.button("进入", key=f"ent_{d}"):
                    st.session_state.current_path += f"/{d}"
                    st.rerun()
                
        for f in files:
            c1, c2, c3, c4 = st.columns([0.05, 0.05, 0.6, 0.3])
            with c1:
                if st.checkbox(" ", key=f"chk_file_{f}", label_visibility="collapsed"):
                    selected_items.append(f)
            with c2:
                st.write("📄")
            with c3:
                st.write(f)
            with c4:
                file_path = file_manager.get_absolute_path(os.path.join(st.session_state.current_path, f))
                if os.path.exists(file_path):
                    with open(file_path, "rb") as file_data:
                        st.download_button("⬇️", file_data, file_name=f, key=f"down_{f}")

        st.markdown("---")
        c_act1, c_act2, c_act3, c_act4, c_act5 = st.columns(5)
        with c_act1:
            if st.button("🗑️ 删除所选"):
                if selected_items:
                    count = file_manager.delete_items(st.session_state.current_path, selected_items)
                    time.sleep(1)
                    st.rerun()
        with c_act2:
            if st.button("📋 复制所选"):
                if selected_items:
                    st.session_state.clipboard = {"action": "copy", "items": selected_items, "source": st.session_state.current_path}
        with c_act3:
            if st.button("✂️ 移动所选"):
                if selected_items:
                    st.session_state.clipboard = {"action": "move", "items": selected_items, "source": st.session_state.current_path}
        with c_act4:
            if "clipboard" in st.session_state:
                if st.button("📥 粘贴"):
                    clipboard = st.session_state.clipboard
                    count, errors = file_manager.paste_items(
                        clipboard["source"],
                        clipboard["items"],
                        st.session_state.current_path,
                        clipboard["action"]
                    )
                    if count > 0:
                        action_name = "移动" if clipboard["action"] == "move" else "复制"
                        del st.session_state.clipboard
                        time.sleep(1)
                        st.rerun()
                    if errors:
                        for err in errors:
                            st.error(err)
            else:
                st.button("📥 粘贴", disabled=True)
        with c_act5:
            if st.button("📦 打包下载所选"):
                if selected_items:
                    zip_path = file_manager.download_selected_zip(st.session_state.current_path, selected_items)
                    if zip_path:
                        st.session_state.ready_to_download_zip = zip_path
                        st.rerun()
        
        # Show download button if ready
        if "ready_to_download_zip" in st.session_state:
            zip_path = st.session_state.ready_to_download_zip
            if os.path.exists(zip_path):
                with open(zip_path, "rb") as f:
                    st.download_button("⬇️ 点击下载打包文件", f, file_name="selected_files.zip", mime="application/zip")
            del st.session_state.ready_to_download_zip

def render_shipping():
    st.title("📦 寄件箱")
    
    tab1, tab2 = st.tabs(["📤 发送包裹", "📥 接收包裹"])
    
    with tab1:
        st.subheader("发送文件包裹")
        message = st.text_area("留言 (可选)")
        retention = st.slider("保留时间 (天)", 1, 30, 7)
        files = st.file_uploader("上传文件", accept_multiple_files=True, key="shipping_upload")
        
        if st.button("📦 创建包裹"):
            if not message and not files:
                st.error("请提供留言或文件。")
            else:
                code = shipping.create_shipping(message, retention, files)
                st.info(f"包裹已创建！您的取件码: **{code}**")
                st.info(f"此取件码将在 {retention} 天后过期。")
    
    with tab2:
        st.subheader("接收包裹")
        code = st.text_input("输入取件码")
        if st.button("🔍 查找包裹"):
            if code:
                data, error = shipping.retrieve_shipping(code)
                if error:
                    st.error(error)
                else:
                    st.success("找到包裹！")
                    st.markdown("**留言:**")
                    st.code(data['message'], language=None)
                    st.markdown(f"**过期时间:** {datetime.fromtimestamp(data['expires_at'])}")
                    
                    if data['files']:
                        st.write("### 文件:")
                        
                        # Prepare file list for potential batch zip
                        file_paths = []
                        files_map = {}
                        
                        with st.form("shipping_files_form"):
                            selected_files = []
                            for f in data['files']:
                                if os.path.exists(f['path']):
                                    file_paths.append(f['path'])
                                    files_map[f['path']] = f['name']
                                    
                                    c1, c2 = st.columns([0.05, 0.95])
                                    with c1:
                                        if st.checkbox(" ", key=f"ship_chk_{f['name']}", label_visibility="collapsed"):
                                            selected_files.append(f['path'])
                                    with c2:
                                        st.write(f"📄 {f['name']} ({f['size']} 字节)")
                                else:
                                    st.error(f"文件 {f['name']} 在服务器上丢失。")
                            
                            st.markdown("---")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.form_submit_button("📦 打包下载全部"):
                                    if file_paths:
                                        zip_path = file_manager.download_selected_zip(os.path.dirname(file_paths[0]), [os.path.basename(p) for p in file_paths], "all_files.zip")
                                        if zip_path:
                                            st.session_state.shipping_zip = zip_path
                            with c2:
                                if st.form_submit_button("📦 打包下载所选"):
                                    if selected_files:
                                        # download_selected_zip expects relative names to root usually, but here we have full paths.
                                        # Let's handle it manually or use utils directly.
                                        # Actually download_selected_zip logic: 
                                        # It takes relative_path (root) and item_names.
                                        # Here files are in a specific folder.
                                        root_dir = os.path.dirname(file_paths[0])
                                        items = [os.path.basename(p) for p in selected_files]
                                        zip_path = file_manager.download_selected_zip(root_dir, items, "selected_files.zip")
                                        if zip_path:
                                            st.session_state.shipping_zip = zip_path

                        if "shipping_zip" in st.session_state:
                            zip_path = st.session_state.shipping_zip
                            if os.path.exists(zip_path):
                                with open(zip_path, "rb") as f:
                                    st.download_button("⬇️ 点击下载打包文件", f, file_name="package_files.zip", mime="application/zip")
                            del st.session_state.shipping_zip
            else:
                st.warning("请输入取件码。")

def render_chat_system():
    st.title("💬 聊天系统")
    
    # Get unread counts
    unread = st.session_state.get("unread_counts", {})
    pub_cnt = unread.get("public", 0)
    grp_cnt = sum(unread.get("groups", {}).values())
    dm_cnt = sum(unread.get("dms", {}).values())
    
    # Tabs for navigation
    t_pub = f"公共聊天 ({pub_cnt})" if pub_cnt > 0 else "公共聊天"
    t_grp = f"群组聊天 ({grp_cnt})" if grp_cnt > 0 else "群组聊天"
    t_dm = f"私信 ({dm_cnt})" if dm_cnt > 0 else "私信"
    
    tab1, tab2, tab3 = st.tabs([t_pub, t_grp, t_dm])
    
    with tab1:
        render_public_chat()
    with tab2:
        render_group_chat()
    with tab3:
        render_direct_messages()

def render_chat_filters(prefix):
    """Render folded search and date filters."""
    with st.expander("🔍 搜索与筛选", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            search_query = st.text_input("搜索消息", key=f"{prefix}_search_q")
        with c2:
            date_filter = st.date_input("按日期筛选", value=None, key=f"{prefix}_date_f")
    return search_query, date_filter

def display_messages(messages, search_query, date_filter, key_prefix="msg"):
    """Display messages with filters and latest at bottom."""
    filtered_msgs = []
    for msg in messages:
        # Date Filter
        if date_filter:
            msg_date = datetime.fromtimestamp(msg['timestamp']).date()
            if msg_date != date_filter:
                continue
        
        # Search Filter
        if search_query:
            q = search_query.lower()
            if q not in msg['content'].lower() and q not in msg['user'].lower():
                continue
            
        filtered_msgs.append(msg)
        
    # Standard chat view: Newest at bottom
    with st.container(height=500):
        for msg in filtered_msgs:
            with st.chat_message("user"):
                st.write(f"**{msg['user']}** - *{msg['date_str']}*")
                st.write(msg['content'])
                
                if msg['files']:
                    with st.expander(f"📎 {len(msg['files'])} 个附件"):
                        for f in msg['files']:
                            if os.path.exists(f['path']):
                                with open(f['path'], "rb") as fd:
                                    st.download_button(f"⬇️ {f['name']}", fd, file_name=f['name'], key=f"{key_prefix}_att_{msg['id']}_{f['name']}")

def render_direct_messages():
    st.subheader("📨 私信")
    
    if not auth.is_logged_in():
        st.warning("请登录以使用私信功能。")
        return

    current_user = auth.get_current_user()
    users = auth.get_users()
    
    # Select User to Chat With
    all_users = list(users.keys())
    other_users = [u for u in all_users if u != current_user]
    
    # Format options with unread counts
    unread = st.session_state.get("unread_counts", {}).get("dms", {})
    
    def format_user_option(u):
        cnt = unread.get(u, 0)
        return f"{u} ({cnt})" if cnt > 0 else u
    
    # Map display string back to username
    user_map = {format_user_option(u): u for u in other_users}
    options = ["选择用户..."] + list(user_map.keys())
    
    selected_option = st.selectbox("选择聊天对象", options)
    
    if selected_option != "选择用户...":
        recipient = user_map[selected_option]
        st.markdown(f"**与 {recipient} 聊天**")
        
        # Mark as read
        chat_system.mark_as_read(current_user, "dm", recipient)
        
        # Filters
        search_query, date_filter = render_chat_filters("dm")
        
        # Display Messages
        messages = chat_system.load_dm_messages(current_user, recipient)
        display_messages(messages, search_query, date_filter, "dm")
            
        # Message Input
        with st.form("dm_form", clear_on_submit=True):
            content = st.text_area("消息")
            files = st.file_uploader("附件", accept_multiple_files=True, key="dm_files")
            submitted = st.form_submit_button("发送")
            
            if submitted:
                if not content and not files:
                    st.warning("消息不能为空。")
                else:
                    chat_system.save_dm_message(current_user, recipient, current_user, content, files)
                    chat_system.add_dm_partner(current_user, recipient) # Add partner to list
                    st.rerun()

def render_public_chat():
    st.subheader("🌐 公共聊天")
    
    # Mark read
    if auth.is_logged_in():
        chat_system.mark_as_read(auth.get_current_user(), chat_system.PUBLIC_CHAT_ID)
    
    # Message Input
    with st.form("public_chat_form", clear_on_submit=True):
        user_name = st.text_input("昵称 (可选)", value="访客" if not auth.is_logged_in() else auth.get_current_user())
        content = st.text_area("消息")
        files = st.file_uploader("附件", accept_multiple_files=True)
        submitted = st.form_submit_button("发送 🚀")
        
        if submitted:
            if not content and not files:
                st.warning("消息不能为空。")
            else:
                chat_system.save_message(chat_system.PUBLIC_CHAT_ID, user_name, content, files)
                st.rerun()
    
    # Filters
    search_query, date_filter = render_chat_filters("pub")
    
    # Display Messages
    messages = chat_system.load_messages(chat_system.PUBLIC_CHAT_ID)
    display_messages(messages, search_query, date_filter, "pub")

def render_group_chat():
    st.subheader("👥 群组聊天")
    
    # Render Active Group Chat
    if "current_group_id" in st.session_state:
        # Hide the main action radio if inside a group
        st.empty() # Placeholder to clear previous UI if needed, though rerun handles it.
        
        gid = st.session_state.current_group_id
        conf = chat_system.get_group_config(gid)
        
        if not conf:
            st.error("群组未找到或已过期。")
            del st.session_state.current_group_id
            st.rerun()
            return
            
        # Clean expired messages
        chat_system.clean_expired_messages(gid, conf['retention_days'])
        
        # Mark as read
        if auth.is_logged_in():
            chat_system.mark_as_read(auth.get_current_user(), gid)
        
        # Back Button
        if st.button("⬅️ 返回群组列表"):
            del st.session_state.current_group_id
            st.rerun()

        st.markdown("---")
        st.header(f"群组: {conf['name']}")
        
        # Group Management (Owner only)
        if auth.is_logged_in() and auth.get_current_user() == conf['owner']:
            with st.expander("群组设置 (仅群主)"):
                new_expiry = st.number_input("更新有效期 (天)", value=conf['expiry_days'], key="new_exp")
                new_retention = st.number_input("更新保留时间 (天)", value=conf['retention_days'], key="new_ret")
                new_owner = st.text_input("转让所有权 (用户名)", key="new_own")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("更新设置"):
                        success, msg = chat_system.update_group_settings(gid, new_expiry, new_retention, new_owner if new_owner else None)
                        if success:
                            st.success(msg)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)
                with c2:
                    if st.button("❌ 销毁群组", type="primary"):
                        chat_system.delete_group_chat(gid)
                        del st.session_state.current_group_id
                        st.success("群组已销毁。")
                        st.rerun()

        # Filters
        search_query, date_filter = render_chat_filters("grp")
        
        # Display Messages
        messages = chat_system.load_messages(gid)
        display_messages(messages, search_query, date_filter, "grp")

        # Message Input
        with st.form("group_chat_form", clear_on_submit=True):
            content = st.text_area("消息")
            files = st.file_uploader("附件", accept_multiple_files=True, key="grp_files")
            submitted = st.form_submit_button("发送")
            
            if submitted:
                if not content and not files:
                    st.warning("消息不能为空。")
                else:
                    user = auth.get_current_user() if auth.is_logged_in() else "匿名"
                    chat_system.save_message(gid, user, content, files)
                    st.rerun()

    else:
        # Show selection UI only if no group selected
        action = st.radio("操作", ["我的群组", "加入群组", "创建群组"], horizontal=True)

        if action == "加入群组":
            code = st.text_input("输入群组代码")
            if st.button("加入"):
                if auth.is_logged_in() and chat_system.check_user_in_group_by_code(auth.get_current_user(), code):
                    st.warning("您已加入过使用该代码的群组。")
                else:
                    groups = chat_system.find_group_by_code(code)
                    if groups:
                        group = groups[0]
                        st.session_state.current_group_id = group['id']
                        if auth.is_logged_in():
                            chat_system.add_joined_group(auth.get_current_user(), group['id'])
                        st.success(f"已加入群组: {group['name']}")
                        st.rerun()
                    else:
                        st.error("群组未找到。")
                    
        elif action == "创建群组":
            if not auth.is_logged_in():
                st.warning("您必须登录才能创建群组。")
            else:
                # Get config limits
                config = admin.load_system_config()
                max_life = config.get("max_group_life_days", 30)
                max_retention = config.get("max_msg_retention_days", 7)
                
                with st.form("create_group_form"):
                    name = st.text_input("群组名称")
                    code = st.text_input("群组代码 (密码)")
                    expiry = st.number_input("有效期 (天)", min_value=1, max_value=max_life, value=min(30, max_life))
                    retention = st.number_input("消息保留时间 (天)", min_value=1, max_value=max_retention, value=min(7, max_retention))
                    
                    submitted = st.form_submit_button("创建群组")
                    if submitted:
                        if not name or not code:
                            st.error("群组名称和代码不能为空。")
                        else:
                            success, result = chat_system.create_group_chat(
                                name, code, expiry, retention, auth.get_current_user()
                            )
                            if success:
                                st.success(f"群组已创建！ID: {result}")
                                chat_system.add_joined_group(auth.get_current_user(), result)
                            else:
                                st.error(result)
                        
        elif action == "我的群组":
            if not auth.is_logged_in():
                st.warning("请登录。")
            else:
                user = auth.get_current_user()
                # Combine created and joined groups
                users = auth.get_users()
                joined = users[user].get("joined_groups", [])
                created = auth.get_user_created_groups()
                all_groups = list(set(joined + created))
                
                if not all_groups:
                    st.info("您尚未加入任何群组。")
                else:
                    unread_grp = st.session_state.get("unread_counts", {}).get("groups", {})
                    
                    for gid in all_groups:
                        conf = chat_system.get_group_config(gid)
                        if conf:
                            cnt = unread_grp.get(gid, 0)
                            label = f"{conf['name']} ({cnt})" if cnt > 0 else conf['name']
                            if st.button(f"进入: {label}", key=gid):
                                st.session_state.current_group_id = gid
                                st.rerun()
                        else:
                            # cleanup invalid group id?
                            pass

def main():
    render_sidebar()
    
    page = st.session_state.page
    
    if page == "Home":
        render_home()
    elif page == "Netdisk":
        render_netdisk()
    elif page == "Shipping Box":
        render_shipping()
    elif page == "Chat System":
        render_chat_system()
    elif page == "Admin Panel":
        if auth.is_admin():
            admin.admin_dashboard()
        else:
            st.error("拒绝访问。")
    elif page == "User Settings":
        render_user_settings()

if __name__ == "__main__":
    main()
