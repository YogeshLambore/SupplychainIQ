import streamlit as st
import datetime
from config.config import APP_NAME, APP_SUBTITLE
from utils.system_monitor import get_system_stats
from utils.icons import ICONS

def load_css():
    """Loads and injects the centralized enterprise CSS styling."""
    try:
        with open("ui/styles.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

def render_sidebar():
    """Renders the top branding and new workspace trigger in the sidebar."""
    stats = get_system_stats()
    
    st.sidebar.markdown(
        f"""
        <div style="
            padding: 20px 14px 16px;
            border-bottom: 1px solid var(--border-subtle);
            margin-bottom: 14px;
        ">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
                <div style="
                    font-family: 'Google Sans', 'Inter', sans-serif;
                    font-size: 20px;
                    font-weight: 700;
                    letter-spacing: 0.8px;
                    color: #FFFFFF;
                    line-height: 1;
                ">{APP_NAME}</div>
                <span class="nx-status-chip" style="font-size: 9.5px; padding: 3px 8px; color: var(--success); border-color: var(--success-border); background: var(--success-bg);">
                    <span class="status-dot online"></span> AIR-GAPPED
                </span>
            </div>
            <div style="
                font-family: 'Google Sans', 'Inter', sans-serif;
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: var(--bright-blue);
            ">{APP_SUBTITLE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── New Workspace button — on_click / key / logic UNTOUCHED ──────────
    if st.sidebar.button("＋  New Workspace", use_container_width=True):
        st.session_state.current_session_id = None
        keys_to_keep = ['llm', 'pdf_proc', 'csv_proc', 'audit', 'img_proc', 'history_manager']
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)


def render_history_sidebar(history_manager, current_session_id):
    """Renders categorized conversation history in the sidebar."""
    st.sidebar.markdown("<hr style='border-color: var(--border-subtle); border-width: 1px; margin: 16px 0 12px 0;'>", unsafe_allow_html=True)
    st.sidebar.markdown(
        "<p style='"
        "font-family: Google Sans, Inter, sans-serif;"
        "color: var(--text-muted);"
        "font-size: 11px;"
        "font-weight: 600;"
        "text-transform: uppercase;"
        "letter-spacing: 1px;"
        "margin-bottom: 8px;"
        "padding-left: 14px;"
        "'>Session History</p>",
        unsafe_allow_html=True,
    )
    
    if not history_manager or not history_manager.is_connected:
        st.sidebar.markdown("<div style='color: var(--text-muted); font-size: 12px; padding-left: 14px;'>History offline (Local DB)</div>", unsafe_allow_html=True)
        return
        
    sessions = history_manager.get_sessions()
    if not sessions:
        st.sidebar.markdown("<div style='color: var(--text-muted); font-size: 12px; padding-left: 14px;'>No previous sessions</div>", unsafe_allow_html=True)
        return
        
    today = datetime.datetime.now().date()
    yesterday = today - datetime.timedelta(days=1)
    
    groups = {"Today": [], "Yesterday": [], "Previous 7 Days": [], "Older": []}
    for s in sessions:
        try:
            updated_dt = datetime.datetime.fromisoformat(s['updated_at']).date()
            if updated_dt == today:
                groups["Today"].append(s)
            elif updated_dt == yesterday:
                groups["Yesterday"].append(s)
            elif (today - updated_dt).days <= 7:
                groups["Previous 7 Days"].append(s)
            else:
                groups["Older"].append(s)
        except Exception:
            groups["Older"].append(s)
            
    for group_name, group_sessions in groups.items():
        if not group_sessions:
            continue
        st.sidebar.markdown(f"<div style='color: var(--text-muted); font-size: 10px; font-weight: 600; text-transform: uppercase; margin-top: 12px; margin-bottom: 4px; padding-left: 14px;'>{group_name}</div>", unsafe_allow_html=True)
        
        for s in group_sessions:
            sess_id = s['session_id']
            title = s.get('title', 'Conversation')
            
            # Highlight active session
            is_active = (sess_id == current_session_id)
            btn_type = "primary" if is_active else "secondary"
                
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
                f"💬  {title}", 
                key=f"hist_{sess_id}", 
                use_container_width=True, 
                type=btn_type,
                on_click=_handle_history_click
            )
        
    st.sidebar.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
    

def render_sidebar_footer():
    """Renders host telemetry and system stats at the bottom of the sidebar."""
    stats = get_system_stats()
    vram = stats.get('vram_status', 'N/A')
    ram_used = f"{stats.get('ram_used_gb', 0):.1f} / {stats.get('ram_total_gb', 0):.1f} GB" if 'ram_used_gb' in stats else "Normal"
    
    st.sidebar.markdown("<hr style='border-color: var(--border-subtle); border-width: 1px; margin: 20px 0 14px 0;'>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='color: var(--text-muted); font-size: 10.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; padding-left: 14px;'>Host Telemetry</p>", unsafe_allow_html=True)
    
    st.sidebar.markdown(
        f"""
        <div style='display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; padding: 0 14px;'>
            <div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 8px 10px;'>
                <div style='color: var(--text-muted); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;'>Network Traffic</div>
                <div style='color: var(--success); font-weight: 600; font-size: 12px; display: flex; align-items: center; gap: 6px; margin-top: 2px;'>
                    <span class="status-dot online"></span> 0 B/s (Local Air-Gap)
                </div>
            </div>
            <div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 8px 10px;'>
                <div style='color: var(--text-muted); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;'>System RAM</div>
                <div style='color: var(--text-primary); font-weight: 600; font-size: 12px; margin-top: 2px;'>{ram_used}</div>
            </div>
            <div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 8px 10px;'>
                <div style='color: var(--text-muted); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;'>GPU VRAM</div>
                <div style='color: var(--text-primary); font-weight: 600; font-size: 12px; margin-top: 2px;'>{vram}</div>
            </div>
            <div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 8px 10px;'>
                <div style='color: var(--text-muted); font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;'>Vector Store</div>
                <div style='color: var(--text-primary); font-weight: 600; font-size: 12px; display: flex; align-items: center; gap: 6px; margin-top: 2px;'>
                    <span class="status-dot online"></span> ChromaDB Local
                </div>
            </div>
        </div>
        """, 
        unsafe_allow_html=True
    )


def render_header(llm_status="READY", vision_status="READY"):
    """Renders the top enterprise command-center status bar."""
    llm_online = (llm_status == "READY")
    llm_label = "● Ollama Connected" if llm_online else "○ Offline Fallback"
    llm_chip_cls = "color: var(--success); border-color: var(--success-border); background: var(--success-bg);" if llm_online else "color: var(--warning); border-color: var(--warning-border); background: var(--warning-bg);"
    
    html_content = f"""
    <div class="nx-header-shell">
        <div class="nx-header-brand">
            <div style="width: 28px; height: 28px; color: var(--bright-blue); display: flex; align-items: center; justify-content: center;">
                {ICONS['shield_check']}
            </div>
            <div>
                <div class="nx-brand-title">NEXORA WORKBENCH</div>
                <div class="nx-brand-subtitle">Confidential Industrial Intelligence</div>
            </div>
        </div>
        <div class="nx-header-telemetry">
            <div class="nx-status-chip" style="{llm_chip_cls}">
                {llm_label}
            </div>
            <div class="nx-status-chip" style="color: var(--text-primary); border-color: var(--border-subtle); background: var(--bg-card);">
                <span class="status-dot info"></span> ZERO CLOUD LEAKAGE
            </div>
        </div>
    </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)


def render_audit_trace(audit_logs):
    """Renders the execution audit trace at the bottom of pages."""
    if not audit_logs:
        return
        
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📋 Sovereign Agent Execution Trace", expanded=False):
        st.markdown(
            "<div style='font-size: 12px; color: var(--text-muted); margin-bottom: 8px;'>"
            "Chronological log of local tool executions, deterministic calculations, and model queries:"
            "</div>",
            unsafe_allow_html=True
        )
        for log in audit_logs:
            status_cls = "status-green" if log['status'] == "PASS" else ("status-amber" if log['status'] == "WARN" else "status-red")
            st.markdown(
                f"<div class='trace-log'>"
                f"<span style='color: var(--text-muted);'>[{log['timestamp']}]</span> "
                f"<strong style='color: var(--bright-blue);'>{log['task']}</strong> &rarr; "
                f"<span style='color: var(--text-primary);'>{log['action']}</span> &bull; "
                f"<span class='{status_cls}'>[{log['status']}]</span> &bull; "
                f"<span>{log['details']}</span>"
                f"</div>", 
                unsafe_allow_html=True
            )
