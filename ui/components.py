import streamlit as st
from config.config import APP_NAME, APP_SUBTITLE
from utils.system_monitor import get_system_stats

def load_css():
    try:
        with open("ui/styles.css", "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

def render_sidebar():
    stats = get_system_stats()
    vram = stats.get('vram_status', 'N/A')

    # ── Wordmark header (visual only — no functional code here) ──────────
    st.sidebar.markdown(
        f"""
        <div style="
            padding: 20px {14}px 16px;
            border-bottom: 1px solid var(--border-subtle);
            margin-bottom: 12px;
        ">
            <div style="
                font-family: 'Google Sans', 'Inter', sans-serif;
                font-size: 20px;
                font-weight: 700;
                letter-spacing: 0.5px;
                color: #F5F5F5;
                line-height: 1;
                margin-bottom: 4px;
            ">{APP_NAME}</div>
            <div style="
                font-family: 'Google Sans', 'Inter', sans-serif;
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #8A8F98;
                font-variant: small-caps;
            ">{APP_SUBTITLE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── New Workspace button — on_click / key / logic UNTOUCHED ──────────
    if st.sidebar.button("New Workspace", use_container_width=True):
        st.session_state.current_session_id = None
        keys_to_keep = ['llm', 'pdf_proc', 'csv_proc', 'audit', 'img_proc', 'history_manager']
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)


def render_history_sidebar(history_manager, current_session_id):
    st.sidebar.markdown("<hr style='border-color: var(--border-subtle); border-width: 1px; margin: 16px 0;'>", unsafe_allow_html=True)
    st.sidebar.markdown(
        "<p style='"
        "font-family:Google Sans,Inter,sans-serif;"
        "color:#8A8F98;"
        "font-size:11px;"
        "font-weight:600;"
        "text-transform:uppercase;"
        "letter-spacing:1px;"
        "margin-bottom:6px;"
        "padding-left:14px;"
        "'>History</p>",
        unsafe_allow_html=True,
    )
    
    if not history_manager or not history_manager.is_connected:
        st.sidebar.markdown("<div style='color: var(--text-muted); font-size: 13px;'>History unavailable (Local DB offline)</div>", unsafe_allow_html=True)
        return
        
    sessions = history_manager.get_sessions()
    if not sessions:
        st.sidebar.markdown("<div style='color: var(--text-muted); font-size: 13px;'>No previous conversations</div>", unsafe_allow_html=True)
        return
        
    import datetime
    today = datetime.datetime.now().date()
    yesterday = today - datetime.timedelta(days=1)
    
    groups = {"Today": [], "Yesterday": [], "Previous 7 Days": [], "Older": []}
    for s in sessions:
        updated_dt = datetime.datetime.fromisoformat(s['updated_at']).date()
        if updated_dt == today:
            groups["Today"].append(s)
        elif updated_dt == yesterday:
            groups["Yesterday"].append(s)
        elif (today - updated_dt).days <= 7:
            groups["Previous 7 Days"].append(s)
        else:
            groups["Older"].append(s)
            
    for group_name, group_sessions in groups.items():
        if not group_sessions: continue
        st.sidebar.markdown(f"<div style='color: var(--text-muted); font-size: 10px; font-weight: 600; text-transform: uppercase; margin-top: 16px; margin-bottom: 4px;'>{group_name}</div>", unsafe_allow_html=True)
        
        for s in group_sessions:
            sess_id = s['session_id']
            title = s.get('title', 'Conversation')
            
            # Highlight active session
            if sess_id == current_session_id:
                btn_type = "primary"
            else:
                btn_type = "secondary"
                
            def _handle_history_click(selected_id=sess_id, selected_ws=s.get("workspace", "Home")):
                st.session_state.current_session_id = selected_id
                nav_map = {
                    "Home": "Home",
                    "General Chat": "General Chat",
                    "Documents": "Documents",
                    "Finance": "Finance",
                    "Engineering": "Engineering",
                    "Sovereignty": "Sovereignty"
                }
                if selected_ws in nav_map:
                    st.session_state.nav_selection = nav_map[selected_ws]

            st.sidebar.button(
                f"{title}", 
                key=f"hist_{sess_id}", 
                use_container_width=True, 
                type=btn_type,
                on_click=_handle_history_click
            )
        
    st.sidebar.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
    
def render_sidebar_footer():
    stats = get_system_stats()
    vram = stats.get('vram_status', 'N/A')
    st.sidebar.markdown("<hr style='border-color: var(--border-subtle); border-width: 1px; margin: 24px 0 16px 0;'>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='color: var(--text-subtle); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>System Status</p>", unsafe_allow_html=True)
    
    from utils.icons import ICONS
    
    st.sidebar.markdown(
        f"""
        <div style='display: flex; flex-direction: column; gap: 16px; margin-bottom: 24px;'>
            <div>
                <div style='color: var(--text-subtle); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;'>NETWORK</div>
                <div style='color: var(--success-green); font-weight: 500; font-size: 13px; display: flex; align-items: center; gap: 8px;'><div class="status-dot"></div>LOCAL / 0 B/s</div>
            </div>
            <div>
                <div style='color: var(--text-subtle); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;'>VRAM USAGE</div>
                <div style='color: var(--text-primary); font-weight: 500; font-size: 13px;'>{vram}</div>
            </div>
            <div>
                <div style='color: var(--text-subtle); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;'>STORAGE</div>
                <div style='color: var(--text-primary); font-weight: 500; font-size: 13px; display: flex; align-items: center; gap: 8px;'><div class="status-dot"></div>ChromaDB</div>
            </div>
        </div>
        <hr style='border-color: var(--border-subtle); border-width: 1px; margin: 16px 0;'>
        <div style='display: flex; flex-direction: column; gap: 12px;'>
            <div style='color: var(--text-muted); font-size: 13px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 10px; transition: color 0.15s ease;' onmouseover='this.style.color="var(--text-primary)"' onmouseout='this.style.color="var(--text-muted)"'>
                <div style='width: 16px; height: 16px;'>{ICONS['settings']}</div> Settings
            </div>
            <div style='color: var(--text-muted); font-size: 13px; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 10px; transition: color 0.15s ease;' onmouseover='this.style.color="var(--text-primary)"' onmouseout='this.style.color="var(--text-muted)"'>
                <div style='width: 16px; height: 16px;'>{ICONS['support']}</div> Support
            </div>
        </div>
        """, 
        unsafe_allow_html=True
    )

def render_header(llm_status="READY", vision_status="READY"):
    llm_color   = "#34a853" if llm_status   == "READY" else "#9aa0a6"
    vis_color   = "#a78bfa" if vision_status == "READY" else "#9aa0a6"
    
    html_content = f"""<div style="display: flex; justify-content: flex-end; align-items: center; padding: 10px 0 20px 0;">
<div style="display: flex; gap: 10px; align-items: center;">
<!-- LLM Status pill -->
<div style="display: flex; flex-direction: column; align-items: flex-start; background: #1e1f22; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 7px 14px; min-width: 108px;">
<span style="color: #8a8f98; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; line-height: 1; margin-bottom: 4px; font-family: 'Google Sans','Inter',sans-serif;">LLM Status</span>
<span style="color: {llm_color}; font-size: 12px; font-weight: 600; letter-spacing: 0.2px; line-height: 1; font-family: 'Google Sans','Inter',sans-serif;">{llm_status}</span>
</div>
<!-- Vision Status pill -->
<div style="display: flex; flex-direction: column; align-items: flex-start; background: #1e1f22; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 7px 14px; min-width: 108px;">
<span style="color: #8a8f98; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; line-height: 1; margin-bottom: 4px; font-family: 'Google Sans','Inter',sans-serif;">Vision Status</span>
<span style="color: {vis_color}; font-size: 12px; font-weight: 600; letter-spacing: 0.2px; line-height: 1; font-family: 'Google Sans','Inter',sans-serif;">{vision_status}</span>
</div>
</div>
</div>"""

    st.markdown(html_content, unsafe_allow_html=True)


def render_audit_trace(audit_logs):
    if not audit_logs:
        return
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("📋 Agent Audit Trace", expanded=False):
        for log in audit_logs:
            color = "green" if log['status'] == "PASS" else ("amber" if log['status'] == "WARN" else "red")
            st.markdown(
                f"<div class='trace-log'>[{log['timestamp']}] <strong>{log['task']}</strong> &rarr; {log['action']} &bull; <span class='status-{color}'>{log['status']}</span> &bull; <span style='color: var(--text-primary);'>{log['details']}</span></div>", 
                unsafe_allow_html=True
            )
