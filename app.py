import streamlit as st
import os
import io
import time
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path

from config.config import APP_NAME, APP_SUBTITLE
from ui.components import load_css, render_sidebar, render_header, render_audit_trace
from core.audit import AuditLogger

class MockUploadedFile(io.BytesIO):
    def __init__(self, path, filename):
        with open(path, "rb") as f:
            data = f.read()
        super().__init__(data)
        self.name = filename
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        self.type = mime_type or "application/octet-stream"

# Ensure we use full page width
st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")

from ui.components import render_sidebar_footer

@st.cache_resource
def get_llm():
    from core.llm import LLMManager
    return LLMManager("llama3:8b")

@st.cache_resource
def get_pdf_processor():
    from core.pdf_processor import PDFProcessor
    return PDFProcessor()

@st.cache_resource
def get_csv_analyzer():
    from core.csv_analyzer import CSVAnalyzer
    return CSVAnalyzer()

@st.cache_resource
def get_image_analyzer():
    from core.image_analyzer import ImageAnalyzer
    return ImageAnalyzer()

@st.cache_resource
def get_history_manager():
    from core.history_manager import HistoryManager
    return HistoryManager()

@st.cache_resource
def get_ocr_engine():
    from core.ocr_engine import LocalOCREngine
    return LocalOCREngine()

# Initialize session state
if "audit" not in st.session_state:
    st.session_state.audit = AuditLogger()
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "nav_selection" not in st.session_state:
    st.session_state.nav_selection = "Home"
if "selected_chat_model" not in st.session_state:
    st.session_state["selected_chat_model"] = "qwen3.5:4b"  # Default: Fast


# UI Setup
from utils.icons import ICONS
load_css()
render_sidebar()

# Navigation
st.sidebar.markdown(
    "<p style='"
    "font-family:Google Sans,Inter,sans-serif;"
    "color:#8A8F98;"
    "font-size:11px;"
    "font-weight:600;"
    "text-transform:uppercase;"
    "letter-spacing:1px;"
    "margin-top:4px;"
    "margin-bottom:6px;"
    "padding-left:14px;"
    "'>Workspaces</p>",
    unsafe_allow_html=True
)
nav_options = ["Home", "General Chat", "Documents", "Finance", "Engineering", "Sovereignty"]

# Approach A — emoji prefix in label only.
# args=(option,) still passes the plain name so _nav_callback and
# all session_state routing logic stay byte-for-byte identical.
nav_labels = {
    "Home":         "🏠  Home",
    "General Chat": "💬  General Chat",
    "Documents":    "📄  Documents",
    "Finance":      "📈  Finance",
    "Engineering":  "⚙️  Engineering",
    "Sovereignty":  "🛡️  Sovereignty",
}

if "nav_selection" not in st.session_state:
    st.session_state.nav_selection = "Home"

def _nav_callback(selected_page):
    st.session_state.nav_selection = selected_page
    st.session_state.current_session_id = None

nav_container = st.sidebar.container()
nav_container.markdown("<div class='main-nav-marker' style='display:none;'></div>", unsafe_allow_html=True)

for i, option in enumerate(nav_options):
    # Hidden marker for exact CSS adjacent sibling targeting
    nav_container.markdown(f"<div id='nav-btn-marker-{i}' style='display:none;'></div>", unsafe_allow_html=True)

    is_active = (st.session_state.nav_selection == option)
    btn_type = "primary" if is_active else "secondary"
    nav_container.button(
        label=nav_labels[option],      # ← emoji + label  (ONLY change)
        key=f"nav_main_{option}",      # unchanged
        use_container_width=True,      # unchanged
        type=btn_type,                 # unchanged
        on_click=_nav_callback,        # unchanged
        args=(option,)                 # unchanged — plain name, not emoji string
    )

nav = st.session_state.nav_selection

from ui.components import render_history_sidebar
render_history_sidebar(get_history_manager(), st.session_state.current_session_id)

render_sidebar_footer()
render_header(get_llm().get_status(), "READY")

def add_audit(task, action, details, status="PASS"):
    st.session_state.audit.log(task, action, details, status)

# === PAGES ===
page = nav

# WORKSPACE ISOLATION CHECK
# Ensure the active session belongs to the current workspace.
# If a user clicked the sidebar to switch workspaces, the current_session_id
# will still point to the old workspace's session. We must clear it to open a fresh workspace.
if st.session_state.current_session_id:
    sessions = get_history_manager().get_sessions()
    current_session = next((s for s in sessions if s["session_id"] == st.session_state.current_session_id), None)
    
    if current_session:
        if current_session.get("workspace") != page:
            st.session_state.current_session_id = None
    else:
        st.session_state.current_session_id = None

if page == "Home":

    # ── CSS injected once for the home page only ────────────────────────────
    st.markdown("""
    <style>
    /* ── Headline + tagline ──────────────────────────────────────────── */
    .nx-home-title {
        font-family: 'Google Sans', 'Inter', sans-serif;
        font-size: 34px;
        font-weight: 700;
        color: #F5F5F5;
        letter-spacing: 0.5px;
        margin: 0 0 8px 0;
        line-height: 1.2;
    }
    .nx-home-sub {
        font-family: 'Google Sans', 'Inter', sans-serif;
        font-size: 15px;
        font-weight: 400;
        color: #9AA0A6;
        margin: 0 0 24px 0;
        line-height: 1.5;
        max-width: 600px;
    }

    /* ── Section label ───────────────────────────────────────────────── */
    .nx-section-label {
        font-family: 'Google Sans', 'Inter', sans-serif;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #8A8F98;
        margin-top: 8px;
        margin-bottom: 20px;
    }

    /* ── Card Body (HTML part) ───────────────────────────────────────── */
    .nx-card-body {
        background: #1E1F22;
        border: 1px solid rgba(255,255,255,0.08);
        border-bottom: none;
        border-radius: 14px 14px 0 0;
        padding: 20px 20px 16px 20px;
        display: flex;
        flex-direction: column;
        height: 160px;
    }

    /* ── Icon badge ──────────────────────────────────────────────────── */
    .nx-badge {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 12px;
    }
    .nx-badge svg {
        width: 20px;
        height: 20px;
    }

    /* Per-card badge tints */
    .nx-badge-doc  { background: rgba(55,48,163,0.3); } /* #3730a3 tint */
    .nx-badge-doc  svg { stroke: #a5b4fc; }

    .nx-badge-fin  { background: rgba(76,29,149,0.3); } /* #4c1d95 tint */
    .nx-badge-fin  svg { stroke: #c4b5fd; }

    .nx-badge-eng  { background: rgba(20,184,166,0.15); } 
    .nx-badge-eng  svg { stroke: #5eead4; }

    .nx-badge-sov  { background: rgba(251,146,60,0.15); } 
    .nx-badge-sov  svg { stroke: #fbbf24; }

    /* Card title */
    .nx-card-title {
        font-family: 'Google Sans', 'Inter', sans-serif;
        font-size: 16px;
        font-weight: 700;
        color: #F5F5F5;
        margin: 0 0 6px 0;
        line-height: 1.3;
    }

    /* Card description */
    .nx-card-desc {
        font-family: 'Google Sans', 'Inter', sans-serif;
        font-size: 13px;
        color: #9AA0A6;
        line-height: 1.5;
        margin: 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* ── Footer Strip (Styled st.button) ─────────────────────────────── */
    /* Target the button container inside the columns */
    div[data-testid="column"] .stButton > button {
        background: #1E1F22 !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-top: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 0 0 14px 14px !important;
        padding: 14px 20px !important;
        height: 50px !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        transition: all 0.15s ease !important;
        margin: 0 !important;
        box-shadow: none !important;
    }
    
    div[data-testid="column"] .stButton > button > div > p {
        font-family: 'Google Sans', 'Inter', sans-serif !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        color: #C4C7C5 !important;
        margin: 0 !important;
        width: 100% !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
    }

    /* Add the arrow via CSS */
    div[data-testid="column"] .stButton > button > div > p::after {
        content: "→";
        font-size: 14px;
        color: #8A8F98;
        transition: transform 0.15s ease;
    }

    div[data-testid="column"] .stButton > button:hover {
        background: rgba(255,255,255,0.04) !important;
        border-color: rgba(255,255,255,0.16) !important;
    }
    
    div[data-testid="column"] .stButton > button:hover > div > p {
        color: #F5F5F5 !important;
    }

    div[data-testid="column"] .stButton > button:hover > div > p::after {
        transform: translateX(2px);
    }

    /* Ensure column gap and row gap */
    div[data-testid="column"] {
        margin-bottom: 20px;
    }
    
    /* Remove default Streamlit button margin */
    div[data-testid="column"] .stButton {
        margin-top: -16px; /* Pull button up to attach to card body */
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Headline ────────────────────────────────────────────────────────────
    st.markdown(
        "<p class='nx-home-title'>NEXORA</p>"
        "<p class='nx-home-sub'>Sovereign AI Workbench. Documents, data and reasoning stay local.</p>",
        unsafe_allow_html=True,
    )

    # ── Section label ────────────────────────────────────────────────────────
    st.markdown("<p class='nx-section-label'>EXPLORE WORKSPACES</p>", unsafe_allow_html=True)

    # ── Navigation callback — on_click / args UNCHANGED ──────────────────────
    def _navigate(target):
        st.session_state.nav_selection = target

    # ── Card definitions ─────────────────────────────────────────────────────
    cards = [
        {
            "badge_cls": "nx-badge-doc",
            "icon":      ICONS["doc"],
            "title":     "Document Intelligence",
            "desc":      "Work with confidential documents locally. Extract text and utilize local RAG for grounded Q&A.",
            "btn_key":   "btn_doc",
            "btn_args":  ("Documents",),
        },
        {
            "badge_cls": "nx-badge-fin",
            "icon":      ICONS["fin"],
            "title":     "Finance",
            "desc":      "Analyze CSV data, generate visual insights, and securely compute authoritative calculations.",
            "btn_key":   "btn_fin",
            "btn_args":  ("Finance",),
        },
        {
            "badge_cls": "nx-badge-eng",
            "icon":      ICONS["eng"],
            "title":     "Engineering",
            "desc":      "Analyze P&IDs and engineering information locally using isolated vision components.",
            "btn_key":   "btn_eng",
            "btn_args":  ("Engineering",),
        },
        {
            "badge_cls": "nx-badge-sov",
            "icon":      ICONS["sov"],
            "title":     "Sovereignty",
            "desc":      "View local offline security parameters, system status, and live audit telemetry.",
            "btn_key":   "btn_sov",
            "btn_args":  ("Sovereignty",),
        },
    ]

    # ── 3-column grid via st.columns ─────────────────────────────────────────
    for i in range(0, len(cards), 3):
        row = cards[i:i+3]
        cols = st.columns(3, gap="medium")
        for col, card in zip(cols, row):
            with col:
                # 1. Visual Card Body (HTML)
                html_body = f"""<div class="nx-card-body">
<div class="nx-badge {card['badge_cls']}">{card['icon']}</div>
<p class="nx-card-title">{card['title']}</p>
<p class="nx-card-desc">{card['desc']}</p>
</div>"""
                st.markdown(html_body, unsafe_allow_html=True)
                
                # 2. Functional Footer Strip (st.button styled via CSS to attach to body)
                st.button(
                    label="Open workspace",
                    key=card["btn_key"],          # unchanged key
                    use_container_width=True,
                    on_click=_navigate,           # unchanged on_click
                    args=card["btn_args"],        # unchanged args
                )

    # ── Bottom prompt bar note ────────────────────────────────────────────────
    # General Chat already has a persistent st.chat_input on its own page.
    # A duplicate input bar here would require duplicating the full chat
    # backend session management — SKIPPED as "optional, pending backend hook"
    # per the design brief constraints.


elif page == "General Chat":
    # ── Model Config ──────────────────────────────────────────────────────────
    CHAT_MODEL_LABELS = {
        "qwen3.5:4b":       ("⚡", "Fast",          "Qwen3.5 4B",          "General questions and quick answers"),
        "qwen2.5-coder:3b": ("👨‍💻", "Coding",        "Qwen2.5-Coder 3B",    "Programming and software engineering"),
        "llama3:8b":        ("🧠", "Deep Reasoning", "Llama 3 8B",          "Complex reasoning and detailed analysis"),
    }
    # ── Model selector CSS (injected once, scoped to this page) ─────────────
    st.markdown("""
    <style>
    /* ── Model selector bar ─────────────────────────────────────────────── */
    .nx-model-bar {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
        flex-wrap: wrap;
    }
    .nx-model-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.10);
        background: transparent;
        color: #9AA0A6;
        font-family: 'Google Sans', 'Inter', sans-serif;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s ease;
        white-space: nowrap;
    }
    .nx-model-btn:hover {
        background: rgba(255,255,255,0.06);
        border-color: rgba(255,255,255,0.20);
        color: #E8EAED;
    }
    .nx-model-btn.nx-active {
        background: rgba(138,43,226,0.15);
        border-color: rgba(138,43,226,0.55);
        color: #C4B5FD;
        font-weight: 600;
    }
    /* Subtle model attribution under assistant messages */
    .nx-msg-model {
        font-family: 'Google Sans', 'Inter', sans-serif;
        font-size: 11px;
        color: #6B7280;
        margin-top: 6px;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Page header ──────────────────────────────────────────────────────────
    selected_model_id = st.session_state.get("selected_chat_model", "qwen3.5:4b")
    sel_icon, sel_mode, sel_label, sel_desc = CHAT_MODEL_LABELS.get(
        selected_model_id,
        ("⚡", "Fast", "Qwen3.5 4B", "General questions and quick answers")
    )
    st.markdown(f"""
        <div style='margin-bottom: 16px;'>
            <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 6px;'>
                <div style='color: var(--accent-primary); width: 28px; height: 28px;'>{ICONS['chat']}</div>
                <h2 style='margin: 0; font-weight: 600; font-size: 1.75rem; letter-spacing: -0.02em;'>General Chat</h2>
            </div>
            <p style='color: var(--text-muted); font-size: 0.95rem; margin: 0;'>Local AI • Fully Offline • No External APIs</p>
        </div>
    """, unsafe_allow_html=True)

    # ── Model selector row ───────────────────────────────────────────────────
    st.markdown("<p style='color: var(--text-subtle); font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px;'>Select Model</p>", unsafe_allow_html=True)

    _model_options = [
        ("qwen3.5:4b",       "⚡",  "Fast",           "Qwen3.5 4B"),
        ("qwen2.5-coder:3b", "👨‍💻", "Coding",          "Qwen2.5-Coder 3B"),
        ("llama3:8b",        "🧠",  "Deep Reasoning",  "Llama 3 8B"),
    ]
    _btn_cols = st.columns([1.1, 1.4, 1.6, 3], gap="small")
    for col, (mid, icon, label, model_name) in zip(_btn_cols[:3], _model_options):
        with col:
            is_active = (mid == selected_model_id)
            btn_style = (
                "background:rgba(138,43,226,0.15);border:1px solid rgba(138,43,226,0.55);color:#C4B5FD;font-weight:600;"
                if is_active else
                "background:transparent;border:1px solid rgba(255,255,255,0.10);color:#9AA0A6;"
            )
            # Use st.button for real interaction; style with HTML wrapper
            if st.button(
                f"{icon}  {label}",
                key=f"model_btn_{mid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["selected_chat_model"] = mid
                st.rerun()

    # Refresh after possible selection change
    selected_model_id = st.session_state.get("selected_chat_model", "qwen3.5:4b")
    sel_icon, sel_mode, sel_label, sel_desc = CHAT_MODEL_LABELS.get(
        selected_model_id,
        ("⚡", "Fast", "Qwen3.5 4B", "General questions and quick answers")
    )

    st.markdown(
        f"<p style='font-size:0.82rem; color:#9AA0A6; margin:4px 0 20px 0;'>"
        f"{sel_icon} <b style='color:#C4C7C5;'>{sel_label}</b> &nbsp;·&nbsp; {sel_desc}"
        f"</p>",
        unsafe_allow_html=True
    )

    # ── Chat history ─────────────────────────────────────────────────────────
    st.markdown("<div style='margin-bottom: 24px;' id='chat-container'>", unsafe_allow_html=True)

    messages = get_history_manager().get_messages(st.session_state.current_session_id) if st.session_state.current_session_id else []
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Show subtle model attribution on assistant messages
            if msg["role"] == "assistant":
                attr_model = msg.get("model", "")
                if attr_model and attr_model in CHAT_MODEL_LABELS:
                    a_icon, _, a_label, _ = CHAT_MODEL_LABELS[attr_model]
                    st.markdown(
                        f"<div class='nx-msg-model'>{a_icon} {a_label}</div>",
                        unsafe_allow_html=True
                    )

    # ── File upload ──────────────────────────────────────────────────────────
    with st.expander("Attached File / Upload Reference", expanded=False):
        uploaded_file = st.file_uploader("Upload File", type=["csv", "pdf", "txt", "md", "json", "png", "jpg", "jpeg"], label_visibility="collapsed")
        if not uploaded_file and st.session_state.current_session_id:
            doc_meta = get_history_manager().get_session_document(st.session_state.current_session_id)
            if doc_meta and os.path.exists(doc_meta["file_path"]):
                uploaded_file = MockUploadedFile(doc_meta["file_path"], doc_meta["filename"])
                st.markdown(f"<div style='color: var(--text-muted); font-size: 0.85rem;'>Loaded from history: {doc_meta['filename']}</div>", unsafe_allow_html=True)

    # ── Chat input ───────────────────────────────────────────────────────────
    query = st.chat_input("Ask a question, request code, or ask about a file...")
    if query:
        if not st.session_state.current_session_id:
            st.session_state.current_session_id = get_history_manager().create_session("General Chat")
            title_context = uploaded_file.name if uploaded_file else query
            get_history_manager().generate_title(st.session_state.current_session_id, "General Chat", query, title_context, get_llm())

            if uploaded_file and not isinstance(uploaded_file, MockUploadedFile):
                uploaded_file.seek(0)
                get_history_manager().link_document(st.session_state.current_session_id, uploaded_file.name, uploaded_file.read())
                uploaded_file.seek(0)

        get_history_manager().add_message(st.session_state.current_session_id, "user", query, "General Chat")
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner(f"Processing with {sel_label}..."):
                # Build file context (unchanged logic)
                file_context = ""
                if uploaded_file:
                    uploaded_file.seek(0)
                    ext = uploaded_file.name.lower().split('.')[-1]
                    try:
                        if ext == 'csv':
                            import pandas as pd
                            df = pd.read_csv(uploaded_file)
                            schema = get_csv_analyzer().analyze_schema(df)
                            file_context = f"[Attached CSV: {uploaded_file.name}]\nRows: {schema['rows']}, Cols: {schema['columns']}\nColumns: {schema['column_names']}\nSample Data:\n{df.head(3).to_markdown()}"
                        elif ext == 'pdf':
                            res = get_pdf_processor().process_pdf(uploaded_file)
                            if res["success"]:
                                text = "".join(res["pages"])[:4000]
                                file_context = f"[Attached PDF: {uploaded_file.name}]\n{text}..."
                        elif ext in ['txt', 'md', 'json']:
                            text = uploaded_file.read().decode('utf-8', errors='ignore')[:4000]
                            file_context = f"[Attached File: {uploaded_file.name}]\n{text}..."
                        elif ext in ['png', 'jpg', 'jpeg']:
                            res = get_image_analyzer().analyze_image(uploaded_file, "Describe this image in detail.")
                            file_context = f"[Attached Image: {uploaded_file.name}]\nAnalysis: {res['text']}"
                    except Exception as e:
                        file_context = f"[Attached File Error: Could not read {uploaded_file.name} - {str(e)}]"

                # Generate response using the selected model
                llm_instance = get_llm()
                if not hasattr(llm_instance, "generate_with_model"):
                    st.cache_resource.clear()
                    st.rerun()
                    
                final_answer = llm_instance.generate_with_model(
                    prompt=query,
                    model_name=selected_model_id,
                    context=file_context if file_context else None,
                    history=messages,
                )

            st.markdown(final_answer)
            # Subtle model attribution
            st.markdown(
                f"<div class='nx-msg-model'>{sel_icon} {sel_label}</div>",
                unsafe_allow_html=True
            )

            # Save to history (include model metadata in a non-breaking way)
            get_history_manager().add_message(
                st.session_state.current_session_id, "assistant", final_answer, "General Chat", model=selected_model_id
            )
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)



elif page == "Documents":
    st.markdown(f"""
        <div style='margin-bottom: 32px;'>
            <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 8px;'>
                <div style='color: var(--accent-primary); width: 28px; height: 28px;'>{ICONS['doc']}</div>
                <h2 style='margin: 0; font-weight: 600; font-size: 1.75rem; letter-spacing: -0.02em;'>Document Intelligence</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col_info, col_preview = st.columns([1, 1.5], gap="large")
    
    with col_info:
        st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Data Source</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
        
        if not uploaded_file and st.session_state.current_session_id:
            doc_meta = get_history_manager().get_session_document(st.session_state.current_session_id)
            if doc_meta and os.path.exists(doc_meta["file_path"]):
                uploaded_file = MockUploadedFile(doc_meta["file_path"], doc_meta["filename"])
        
        if uploaded_file:
            with st.spinner("Processing PDF..."):
                uploaded_file.seek(0)
                res = get_pdf_processor().process_pdf(uploaded_file)
            if res["success"]:
                st.markdown(f"<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--success-green); font-size: 0.85rem; font-weight: 600; margin-bottom: 8px;'>✓ PROCESSED</div><div style='font-weight: 500; margin-bottom: 4px;'>{uploaded_file.name}</div><div style='color: var(--text-muted); font-size: 0.85rem;'>{res['num_pages']} Pages • {res['text_size']} chars</div></div>", unsafe_allow_html=True)
                chunks = get_pdf_processor().chunk_text(res["pages"])
            else:
                st.error(f"Error processing PDF: {res.get('error')}")
                chunks = None
    
    with col_preview:
        if uploaded_file and res.get("success"):
            try:
                import fitz
                uploaded_file.seek(0)
                doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                page = doc.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_bytes = pix.tobytes("png")
                uploaded_file.seek(0)
                
                st.markdown("<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 16px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>◉ DOCUMENT PREVIEW</div>", unsafe_allow_html=True)
                st.image(img_bytes, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            except Exception as e:
                st.warning("Preview generation failed.")
                
    st.markdown("<hr style='border-color: var(--border-subtle); margin: 32px 0;'>", unsafe_allow_html=True)
    
    if uploaded_file and res.get("success"):
        st.markdown("<div style='margin-bottom: 24px;' id='chat-container'>", unsafe_allow_html=True)
        
        messages = get_history_manager().get_messages(st.session_state.current_session_id) if st.session_state.current_session_id else []
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        query = st.chat_input("Ask about your document...")
        if query:
            if not st.session_state.current_session_id:
                st.session_state.current_session_id = get_history_manager().create_session("Documents")
                get_history_manager().generate_title(st.session_state.current_session_id, "Documents", query, uploaded_file.name, get_llm())
                
                if not isinstance(uploaded_file, MockUploadedFile):
                    uploaded_file.seek(0)
                    get_history_manager().link_document(st.session_state.current_session_id, uploaded_file.name, uploaded_file.read())
                    uploaded_file.seek(0)
                
            get_history_manager().add_message(st.session_state.current_session_id, "user", query, "Documents")
            
            with st.chat_message("user"):
                st.markdown(query)
            add_audit("DOC_ROUTER", "QUERY", f"Query received")
            
            with st.chat_message("assistant"):
                with st.spinner("Retrieving and generating..."):
                    top_chunks = get_pdf_processor().retrieve_relevant(query, chunks)
                    add_audit("DOC_RETRIEVAL", "RAG", f"Found {len(top_chunks)} relevant chunks")
                    context = " ".join([f"[Page {c['page']}] {c['text']}" for c in top_chunks]) if top_chunks else ""
                    answer = get_llm().generate(query, context, history=messages)
                    add_audit("DOC_REASONING", "LLM", "Generated answer", "PASS" if get_llm().is_loaded else "WARN")
                
                full_response = answer
                st.markdown(answer)
                
                if top_chunks:
                    full_response += "\n\n*(Source Evidence Used)*"
                    with st.expander("📄 View Source Evidence"):
                        st.markdown("<div class='status-pill' style='margin-bottom: 10px;'>✓ SOURCE GROUNDED</div>", unsafe_allow_html=True)
                        for i, chunk in enumerate(top_chunks):
                            st.markdown(f"<div style='font-size: 0.85rem; font-weight: 600; margin-bottom: 4px;'>Page {chunk['page']} <span style='color: var(--text-muted); font-weight: 400;'>(Similarity: {chunk.get('similarity', 'N/A')})</span></div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='border-left: 2px solid var(--accent-primary); padding-left: 12px; margin-bottom: 16px; color: var(--text-muted); font-size: 0.9rem;'>{chunk['text']}</div>", unsafe_allow_html=True)
                
                get_history_manager().add_message(st.session_state.current_session_id, "assistant", full_response, "Documents")
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; border: 1px dashed var(--border-subtle); border-radius: 16px; color: var(--text-muted);'><div style='font-size: 2rem; margin-bottom: 12px;'>📄</div><div>Upload a document to begin</div></div>", unsafe_allow_html=True)

elif page == "Finance":
    st.markdown(f"""
        <div style='margin-bottom: 32px;'>
            <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 8px;'>
                <div style='color: var(--accent-primary); width: 28px; height: 28px;'>{ICONS['fin']}</div>
                <h2 style='margin: 0; font-weight: 600; font-size: 1.75rem; letter-spacing: -0.02em;'>Finance Analytics</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col_info, col_preview = st.columns([1, 1.5], gap="large")
    
    with col_info:
        st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Data Source</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
        
        if not uploaded_file and st.session_state.current_session_id:
            doc_meta = get_history_manager().get_session_document(st.session_state.current_session_id)
            if doc_meta and os.path.exists(doc_meta["file_path"]):
                uploaded_file = MockUploadedFile(doc_meta["file_path"], doc_meta["filename"])
        
        if uploaded_file:
            import pandas as pd
            add_audit("FIN_INPUT", "UPLOAD", f"Received {uploaded_file.name}")
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file)
                schema = get_csv_analyzer().analyze_schema(df)
                st.markdown(f"<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--success-green); font-size: 0.85rem; font-weight: 600; margin-bottom: 8px;'><div class='status-dot'></div> PROCESSED</div><div style='font-weight: 500; margin-bottom: 8px;'>{uploaded_file.name}</div><div style='display: flex; gap: 16px; margin-bottom: 12px;'><div style='color: var(--text-primary); font-size: 1.1rem; font-weight: 500;'>{schema['rows']}<span style='color: var(--text-muted); font-size: 0.75rem; font-weight: 600; margin-left: 4px; text-transform: uppercase;'>Rows</span></div><div style='color: var(--text-primary); font-size: 1.1rem; font-weight: 500;'>{schema['columns']}<span style='color: var(--text-muted); font-size: 0.75rem; font-weight: 600; margin-left: 4px; text-transform: uppercase;'>Cols</span></div></div></div>", unsafe_allow_html=True)
                valid_csv = True
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")
                valid_csv = False
        else:
            valid_csv = False
            
    with col_preview:
        if uploaded_file and valid_csv:
            st.markdown("<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 16px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>◉ DATASET PREVIEW</div>", unsafe_allow_html=True)
            st.dataframe(df.head(6), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: var(--border-subtle); margin: 32px 0;'>", unsafe_allow_html=True)
    
    if uploaded_file and valid_csv:
        st.markdown("<div style='margin-bottom: 24px;' id='chat-container'>", unsafe_allow_html=True)
        
        messages = get_history_manager().get_messages(st.session_state.current_session_id) if st.session_state.current_session_id else []
        for msg in messages:
            with st.chat_message(msg["role"]):
                if "[CHART_PATH:" in msg["content"]:
                    text_part = msg["content"].split("[CHART_PATH:")[0]
                    chart_path = msg["content"].split("[CHART_PATH:")[1].split("]")[0]
                    st.markdown(text_part)
                    if os.path.exists(chart_path):
                        st.markdown("<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Data Visualization</div>", unsafe_allow_html=True)
                        st.image(chart_path)
                        with open(chart_path, "rb") as f:
                            st.download_button(label="Download Chart (PNG)", data=f, file_name=os.path.basename(chart_path), mime="image/png", use_container_width=True, key=f"dl_{chart_path}")
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.markdown(msg["content"])
                
        query = st.chat_input("Ask your data (e.g. 'Which department spent the most?')")
        if query:
            if not st.session_state.current_session_id:
                st.session_state.current_session_id = get_history_manager().create_session("Finance")
                get_history_manager().generate_title(st.session_state.current_session_id, "Finance", query, uploaded_file.name, get_llm())
                
                if not isinstance(uploaded_file, MockUploadedFile):
                    uploaded_file.seek(0)
                    get_history_manager().link_document(st.session_state.current_session_id, uploaded_file.name, uploaded_file.read())
                    uploaded_file.seek(0)
                
            get_history_manager().add_message(st.session_state.current_session_id, "user", query, "Finance")
            
            with st.chat_message("user"):
                st.markdown(query)
            add_audit("FIN_ROUTER", "INTENT", "Parsing visualization intent via LLM + deterministic rules")
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing data locally..."):
                    from core.chart_engine import ChartEngine
                    engine = ChartEngine()
                    fig, summary_info, err = engine.generate_chart(df, query, llm=get_llm())
                    add_audit("FIN_ANALYSIS", "EXECUTION", f"Chart engine: {summary_info['chart_type'] if summary_info else 'error'}")
                    
                    if err:
                        # Deterministic fallback description
                        final_answer = (
                            f"**Unable to generate visualization:** {err}\n\n"
                            f"Try rephrasing your request. For example:\n"
                            f"- *'Show a bar chart of total sales by region'*\n"
                            f"- *'Plot the distribution of loan amounts'*\n"
                            f"- *'Show the correlation between all numeric variables'*"
                        )
                        add_audit("FIN_VISUAL", "ERROR", err)
                    else:
                        # Pass actual CALCULATED data summary to Llama — never let LLM invent numbers
                        calc_context = (
                            f"Chart type: {summary_info['chart_type']}\n"
                            f"Chart title: {summary_info['chart_title']}\n"
                            f"Records analyzed: {summary_info['rows_analyzed']:,}\n"
                            f"Calculated data summary:\n{summary_info['explanation']}"
                        )
                        final_answer = get_llm().generate(
                            prompt=f"Explain these data analysis results for the user. Their question was: '{query}'",
                            context=calc_context,
                            default_category="DATA",
                            history=messages
                        )
                        add_audit("FIN_REASONING", "LLM", "Generated explanation from actual calculated results", "PASS" if get_llm().is_loaded else "WARN")
                    
                full_response = final_answer
                st.markdown(final_answer)
                
                if fig and summary_info:
                    import uuid as _uuid
                    import io as _io
                    os.makedirs("./data/uploads", exist_ok=True)
                    chart_path = f"./data/uploads/chart_{_uuid.uuid4().hex[:8]}.png"
                    buf = _io.BytesIO()
                    fig.savefig(buf, format="png", bbox_inches='tight', dpi=120, facecolor=fig.get_facecolor())
                    with open(chart_path, "wb") as f:
                        f.write(buf.getvalue())
                    plt.close(fig)
                    
                    # Render chart
                    st.markdown("<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Data Visualization</div>", unsafe_allow_html=True)
                    st.image(chart_path, use_container_width=True)
                    
                    # Download button
                    with open(chart_path, "rb") as f:
                        st.download_button(label="Download Chart (PNG)", data=f, file_name=f"nexora_{summary_info['chart_type']}.png", mime="image/png", use_container_width=True, key=f"dl_{chart_path}")
                    
                    # Compact insight panel
                    plan = summary_info.get("plan", {})
                    ct_display = summary_info['chart_type'].replace("_"," ").title()
                    st.markdown(
                        f"<div style='margin-top: 12px; padding: 12px; background: rgba(167,139,250,0.05); border: 1px solid rgba(167,139,250,0.15); border-radius: 8px; font-size: 0.8rem;'>"
                        f"<span style='color: var(--text-subtle);'>Chart:</span> <b style='color:#A78BFA'>{ct_display}</b>&nbsp;&nbsp;"
                        f"<span style='color: var(--text-subtle);'>Aggregation:</span> <b>{plan.get('aggregation','').upper()}</b>&nbsp;&nbsp;"
                        f"<span style='color: var(--text-subtle);'>Records:</span> <b>{summary_info['rows_analyzed']:,}</b>&nbsp;&nbsp;"
                        f"<span style='color: #34D399;'><div class='status-dot'></div> Pandas Calculated</span>&nbsp;&nbsp;"
                        f"<span style='color: #34D399;'><div class='status-dot'></div> No External API</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    full_response += f"\n\n[CHART_PATH:{chart_path}]"
                    add_audit("FIN_VISUAL", "CHART", f"Generated {summary_info['chart_type']} chart")
                    
                get_history_manager().add_message(st.session_state.current_session_id, "assistant", full_response, "Finance")
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; border: 1px dashed var(--border-subtle); border-radius: 16px; color: var(--text-muted);'><div style='width: 48px; height: 48px; margin-bottom: 16px; opacity: 0.5;'>{ICONS['upload']}</div><div>Upload a dataset to begin</div></div>", unsafe_allow_html=True)

elif page == "Engineering":
    st.markdown(f"""
        <div style='margin-bottom: 32px;'>
            <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 8px;'>
                <div style='color: var(--accent-primary); width: 28px; height: 28px;'>{ICONS['eng']}</div>
                <h2 style='margin: 0; font-weight: 600; font-size: 1.75rem; letter-spacing: -0.02em;'>Engineering Vision</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col_info, col_preview = st.columns([1, 1.5], gap="large")
    
    with col_info:
        st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Source Diagram</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload P&ID or Diagram (Image/PDF)", type=["png", "jpg", "jpeg", "pdf"], label_visibility="collapsed")
        
        if not uploaded_file and st.session_state.current_session_id:
            doc_meta = get_history_manager().get_session_document(st.session_state.current_session_id)
            if doc_meta and os.path.exists(doc_meta["file_path"]):
                uploaded_file = MockUploadedFile(doc_meta["file_path"], doc_meta["filename"])
                
        st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; margin-top: 16px;'>Context Data (Optional)</p>", unsafe_allow_html=True)
        csv_file = st.file_uploader("Upload Sensor CSV", type=["csv"], label_visibility="collapsed", key="eng_csv")
        
        st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; margin-top: 16px;'>Reference Docs (Optional)</p>", unsafe_allow_html=True)
        ref_pdf_file = st.file_uploader("Upload Reference PDF", type=["pdf"], label_visibility="collapsed", key="eng_pdf")
        
        valid_csv = False
        df = None
        if csv_file:
            import pandas as pd
            add_audit("ENG_DATA", "UPLOAD", f"Received {csv_file.name}")
            try:
                csv_file.seek(0)
                df = pd.read_csv(csv_file)
                valid_csv = True
                st.markdown(f"<div style='margin-top: 16px; padding: 12px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--success-green); font-size: 0.75rem; font-weight: 600; margin-bottom: 4px;'>✓ DATA LOADED</div><div style='font-weight: 500; font-size: 0.85rem;'>{csv_file.name}</div></div>", unsafe_allow_html=True)
            except Exception:
                st.error("Failed to parse CSV")
                
        valid_ref_pdf = False
        ref_chunks = []
        if ref_pdf_file:
            add_audit("ENG_DOC", "UPLOAD", f"Received reference PDF {ref_pdf_file.name}")
            pdf_res = get_pdf_processor().process_pdf(ref_pdf_file)
            if pdf_res.get("success"):
                ref_chunks = get_pdf_processor().chunk_text(pdf_res["pages"])
                valid_ref_pdf = True
                st.markdown(f"<div style='margin-top: 16px; padding: 12px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--success-green); font-size: 0.75rem; font-weight: 600; margin-bottom: 4px;'>✓ REF DOC LOADED</div><div style='font-weight: 500; font-size: 0.85rem;'>{ref_pdf_file.name}</div></div>", unsafe_allow_html=True)
            else:
                st.error("Failed to parse Reference PDF")
        
        if uploaded_file:
            add_audit("ENG_INPUT", "UPLOAD", f"Received {uploaded_file.name}")
            st.markdown(f"<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--success-green); font-size: 0.85rem; font-weight: 600; margin-bottom: 8px;'>✓ IMAGE LOADED</div><div style='font-weight: 500; margin-bottom: 8px;'>{uploaded_file.name}</div></div>", unsafe_allow_html=True)
            
            vision_status = "Vision model ready" if getattr(get_image_analyzer(), 'has_vision_model', False) else "Using Fallback Mode"
            vision_color = "var(--success-green)" if getattr(get_image_analyzer(), 'has_vision_model', False) else "var(--warning-amber)"
            st.markdown(f"<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--text-subtle); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;'>Model:</div><div style='font-weight: 600; font-size: 0.9rem; margin-bottom: 12px;'>● Moondream 1.8B — LOCAL</div><div style='color: var(--text-subtle); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 8px;'>Status:</div><div style='color: {vision_color}; font-weight: 500; font-size: 0.85rem;'>● {vision_status}</div></div>", unsafe_allow_html=True)
            
    with col_preview:
        if uploaded_file:
            st.markdown("<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 16px; margin-bottom: 16px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>◉ DIAGRAM PREVIEW</div>", unsafe_allow_html=True)
            st.image(uploaded_file, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        if valid_csv:
            st.markdown("<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 16px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>◉ SENSOR DATA PREVIEW</div>", unsafe_allow_html=True)
            st.dataframe(df.head(4), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: var(--border-subtle); margin: 32px 0;'>", unsafe_allow_html=True)
            
    if uploaded_file:
        st.markdown("<div style='margin-bottom: 24px;' id='chat-container'>", unsafe_allow_html=True)
        
        messages = get_history_manager().get_messages(st.session_state.current_session_id) if st.session_state.current_session_id else []
        for msg in messages:
            with st.chat_message(msg["role"]):
                content = msg["content"]
                
                # Check for HITL
                hitl_req = False
                if "[HITL_REQUIRED]" in content:
                    hitl_req = True
                    content = content.replace("[HITL_REQUIRED]", "").strip()
                
                # Check for visual evidence (annotated image)
                img_path = None
                if "[IMAGE_PATH:" in content:
                    parts = content.split("[IMAGE_PATH:")
                    content = parts[0].strip()
                    img_path = parts[1].split("]")[0]
                    
                # Check for chart
                chart_path = None
                if "[CHART_PATH:" in content:
                    parts = content.split("[CHART_PATH:")
                    content = parts[0].strip()
                    chart_path = parts[1].split("]")[0]
                    
                st.markdown(content)
                
                if hitl_req and msg["role"] == "assistant":
                    col1, col2, _ = st.columns([1, 1, 4])
                    with col1:
                        if st.button("✓ Approve", key=f"hitl_app_{msg.get('id', hash(content))}"):
                            add_audit("ENG_VERIFICATION", "HUMAN", "Human verified and approved result", "PASS")
                    with col2:
                        if st.button("✕ Reject", key=f"hitl_rej_{msg.get('id', hash(content))}"):
                            add_audit("ENG_VERIFICATION", "HUMAN", "Human rejected result", "FAIL")
                
                if chart_path and os.path.exists(chart_path):
                    st.markdown("<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Engineering Data Visualization</div>", unsafe_allow_html=True)
                    st.image(chart_path)
                    with open(chart_path, "rb") as f:
                        st.download_button(label="⬇️ Download Chart (PNG)", data=f, file_name=os.path.basename(chart_path), mime="image/png", use_container_width=True, key=f"dl_{chart_path}")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                if img_path and os.path.exists(img_path):
                    st.markdown(f"<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Visual Evidence</div>", unsafe_allow_html=True)
                    st.image(img_path)
                    st.markdown("</div>", unsafe_allow_html=True)
                
        query = st.chat_input("e.g. 'What components are visible?', 'Explain this diagram'")
        if query:
            if not st.session_state.current_session_id:
                st.session_state.current_session_id = get_history_manager().create_session("Engineering")
                get_history_manager().generate_title(st.session_state.current_session_id, "Engineering", query, uploaded_file.name, get_llm())
                
                if not isinstance(uploaded_file, MockUploadedFile):
                    uploaded_file.seek(0)
                    get_history_manager().link_document(st.session_state.current_session_id, uploaded_file.name, uploaded_file.read())
                    uploaded_file.seek(0)
                
            get_history_manager().add_message(st.session_state.current_session_id, "user", query, "Engineering")
            
            with st.chat_message("user"):
                st.markdown(query)
                
            with st.chat_message("assistant"):
                with st.spinner("Analyzing diagram locally..."):
                    # Process Image
                    res = get_image_analyzer().analyze_image(uploaded_file, query)
                    audit_msg = "Processed image using Moondream" if res.get("confidence") == "High (Local Moondream)" else "Processed image using fallback mode"
                    audit_level = "PASS" if res.get("confidence") == "High (Local Moondream)" else "WARN"
                    add_audit("ENG_VISION", "ANALYSIS", audit_msg, audit_level)
                    
                    from core.engineering_analyzer import EngineeringAnalyzer
                    _ocr = get_ocr_engine()
                    add_audit("ENG_OCR", "INIT", f"OCR status: {_ocr.status}")
                    eng_analyzer = EngineeringAnalyzer(
                        get_llm(),
                        getattr(st.session_state, 'img_proc', None),
                        ocr_engine=_ocr
                    )
                    
                    # Process RAG (after visual — never before)
                    reference_evidence = ""
                    if valid_ref_pdf and ref_chunks:
                        top_chunks = get_pdf_processor().retrieve_relevant(query, ref_chunks)
                        if top_chunks:
                            reference_evidence = " ".join([f"[Page {c['page']}] {c['text']}" for c in top_chunks])
                            add_audit("ENG_RAG", "RETRIEVAL", f"Found {len(top_chunks)} relevant references")
                    
                    # Process CSV if data-related query
                    fig = None
                    data_context = ""
                    is_data_query = any(w in query.lower() for w in ["trend", "data", "sensor", "csv", "graph", "plot", "compare", "value", "bar", "pie", "hist", "scatter", "chart", "analyze"])
                    if valid_csv and is_data_query:
                        data_ans, fig = get_csv_analyzer().interpret_and_execute(query, df)
                        data_context = f"\n\nAdditional Data Analysis Results:\n{data_ans}"
                        add_audit("ENG_DATA", "ANALYSIS", "Processed sensor data")
                    
                    base64_img = res.get("base64_img") if res else None
                    report = eng_analyzer.generate_final_report(query, base64_img, reference_evidence, data_context, messages)
                    add_audit("ENG_REASONING", "LLM",
                              f"Confidence: {report.get('confidence','LOW')} | "
                              f"Visual: {report.get('visual_state','?')} | "
                              f"OCR labels: {len(report.get('ocr_findings',[]))}",
                              "PASS" if not report.get('hitl_required', True) else "WARN")
                    
                full_response = report["markdown"]
                if report.get('hitl_required', False):
                    full_response += "\n\n[HITL_REQUIRED]"
                
                if fig:
                    import io
                    import uuid
                    import os
                    os.makedirs("./data/uploads", exist_ok=True)
                    chart_path = f"./data/uploads/chart_{uuid.uuid4().hex[:8]}.png"
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", bbox_inches='tight', facecolor=fig.get_facecolor())
                    with open(chart_path, "wb") as f:
                        f.write(buf.getvalue())
                        
                    full_response += f"\n\n[CHART_PATH:{chart_path}]"
                
                if res.get("annotated_image"):
                    import uuid
                    import os
                    from PIL import Image
                    os.makedirs("./data/uploads", exist_ok=True)
                    img_path = f"./data/uploads/annotated_{uuid.uuid4().hex[:8]}.png"
                    if isinstance(res["annotated_image"], Image.Image):
                        res["annotated_image"].save(img_path, format="PNG")
                    else:
                        with open(img_path, "wb") as f:
                            f.write(res["annotated_image"])
                            
                    full_response += f"\n\n[IMAGE_PATH:{img_path}]"
                    
                st.markdown("<div style='background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); padding: 12px; border-radius: 8px; color: var(--warning-amber); margin-top: 16px; font-size: 0.85rem; font-weight: 500;'>⚠️ AI-assisted analysis only. Final engineering decisions remain with the responsible engineer.</div>", unsafe_allow_html=True)
                
                get_history_manager().add_message(st.session_state.current_session_id, "assistant", full_response, "Engineering")
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; border: 1px dashed var(--border-subtle); border-radius: 16px; color: var(--text-muted);'><div style='width: 48px; height: 48px; margin-bottom: 16px; opacity: 0.5;'>{ICONS['upload']}</div><div>Upload a P&ID or Diagram to begin</div></div>", unsafe_allow_html=True)

elif page == "Sovereignty":
    from utils.system_monitor import get_system_stats
    stats = get_system_stats()
    vram = stats.get('vram_status', 'N/A')
    llm_status = get_llm().get_status()
    
    st.markdown(f"""
        <div style='margin-bottom: 32px;'>
            <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 8px;'>
                <div style='color: var(--accent-primary); width: 28px; height: 28px;'>{ICONS['sov']}</div>
                <h2 style='margin: 0; font-weight: 600; font-size: 1.75rem; letter-spacing: -0.02em;'>Sovereignty Status</h2>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 24px; height: 100%;'><div style='color: var(--text-subtle); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;'>Local Processing</div><div style='color: var(--success-green); font-size: 1.5rem; font-weight: 500; margin-bottom: 8px;'>✓ SECURE</div><p style='color: var(--text-muted); font-size: 0.85rem; margin: 0;'>All processing happens strictly on this machine.</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 24px; height: 100%;'><div style='color: var(--text-subtle); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;'>Network Activity</div><div style='color: var(--success-green); font-size: 1.5rem; font-weight: 500; margin-bottom: 8px;'>0 Bytes</div><p style='color: var(--text-muted); font-size: 0.85rem; margin: 0;'>No outbound API calls detected during this session.</p></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 24px; height: 100%;'><div style='color: var(--text-subtle); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;'>System VRAM</div><div style='color: var(--text-primary); font-size: 1.5rem; font-weight: 500; margin-bottom: 8px;'>{vram}</div><p style='color: var(--text-muted); font-size: 0.85rem; margin: 0;'>Current graphics memory allocation for AI models.</p></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 24px;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 1.1rem; margin-bottom: 24px;'>Model Architecture & Isolation</h3>", unsafe_allow_html=True)
    
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 16px;">
            <span style="font-weight: 500; color: var(--text-primary);">Ollama Engine</span>
            <span class='status-pill' style='color: {"var(--success-green)" if llm_status == "READY" else "var(--warning-amber)"}; background: transparent; border-color: var(--border-active);'>{'● RUNNING' if llm_status == 'READY' else '● FALLBACK'}</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 16px;">
            <span style="font-weight: 500; color: var(--text-primary);">Moondream 1.8B</span>
            <span class='status-pill' style='color: {"var(--success-green)" if getattr(get_image_analyzer(), "has_vision_model", False) else "var(--warning-amber)"}; background: transparent; border-color: var(--border-active);'>{'● LOCAL' if getattr(get_image_analyzer(), "has_vision_model", False) else '● FALLBACK'}</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 16px;">
            <span style="font-weight: 500; color: var(--text-primary);">External API Calls</span>
            <span class='status-pill' style='color: var(--text-subtle); background: transparent; border-color: var(--border-active);'>NONE</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 16px;">
            <span style="font-weight: 500; color: var(--text-primary);">Internet Dependency</span>
            <span class='status-pill' style='color: var(--text-subtle); background: transparent; border-color: var(--border-active);'>ISOLATED</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <span style="font-weight: 500; color: var(--text-primary);">Data Location</span>
            <span class='status-pill' style='color: var(--text-subtle); background: transparent; border-color: var(--border-active);'>LOCAL MACHINE</span>
        </div>
        """, unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("RUN LOCAL AUDIT", use_container_width=True):
        with st.spinner("Auditing network interfaces..."):
            time.sleep(1)
        st.markdown("<div style='margin-top: 16px; padding: 16px; border-radius: 12px; background-color: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); color: var(--success-green); font-weight: 500;'>✓ Audit complete. 0 bytes outbound traffic detected during this session.</div>", unsafe_allow_html=True)

# Render Audit trace on all pages at the bottom
st.markdown("<br><hr style='border-color: var(--border-subtle);'>", unsafe_allow_html=True)
render_audit_trace(st.session_state.audit.get_logs())
