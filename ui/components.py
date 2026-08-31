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
    
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    
    # Premium Wordmark Treatment
    st.sidebar.markdown(
        f"<h2 style='margin-bottom: 0; padding-bottom: 0; font-weight: 500; font-size: 1.5rem;'>{APP_NAME}</h2>", 
        unsafe_allow_html=True
    )
    st.sidebar.markdown(
        f"<p style='color: #6B7280; font-size: 0.85rem; font-weight: 500; margin-top: 2px; margin-bottom: 24px;'>{APP_SUBTITLE}</p>", 
        unsafe_allow_html=True
    )
    
    if st.sidebar.button("➕ New Workspace", use_container_width=True):
        st.session_state.clear()
        st.rerun()
        
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    
def render_sidebar_footer():
    stats = get_system_stats()
    vram = stats.get('vram_status', 'N/A')
    st.sidebar.markdown("<hr style='border-color: #2B2E36; margin: 32px 0 16px 0;'>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='color: #9CA3AF; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>System Status</p>", unsafe_allow_html=True)
    
    st.sidebar.markdown(
        f"""
        <div style='display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px;'>
            <div>
                <div style='color: #6B7280; font-size: 0.75rem;'>NETWORK</div>
                <div style='color: #10B981; font-weight: 500; font-size: 0.85rem;'>● LOCAL / 0 B/s</div>
            </div>
            <div>
                <div style='color: #6B7280; font-size: 0.75rem;'>VRAM USAGE</div>
                <div style='color: #F3F4F6; font-weight: 500; font-size: 0.85rem;'>{vram}</div>
            </div>
        </div>
        <hr style='border-color: #2B2E36; margin: 16px 0;'>
        <div style='display: flex; flex-direction: column; gap: 8px;'>
            <div style='color: #9CA3AF; font-size: 0.85rem; cursor: pointer;'>⚙️ Settings</div>
            <div style='color: #9CA3AF; font-size: 0.85rem; cursor: pointer;'>❓ Support</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

def render_header(llm_status="READY", vision_status="READY"):
    # Header is cleaner, moves system stats to sidebar
    st.markdown(
        f"""
        <div style="display: flex; justify-content: flex-end; align-items: center; padding: 12px 0; margin-bottom: 24px;">
            <div style="display: flex; gap: 16px;">
                <div style="text-align: right; background: var(--bg-card); padding: 8px 16px; border-radius: 12px; border: 1px solid var(--border-subtle);">
                    <div style="color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">LLM Status</div>
                    <div style="color: {'var(--accent-primary)' if llm_status == 'READY' else 'var(--text-muted)'}; font-size: 0.85rem; font-weight: 500;">{llm_status}</div>
                </div>
                <div style="text-align: right; background: var(--bg-card); padding: 8px 16px; border-radius: 12px; border: 1px solid var(--border-subtle);">
                    <div style="color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Vision Status</div>
                    <div style="color: {'var(--accent-primary)' if vision_status == 'READY' else 'var(--text-muted)'}; font-size: 0.85rem; font-weight: 500;">{vision_status}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

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
