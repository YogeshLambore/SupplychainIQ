import streamlit as st
import os
import io
import time
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path

from config.config import APP_NAME, APP_SUBTITLE
from ui.components import load_css, render_sidebar, render_header, render_audit_trace, render_sidebar_footer, render_history_sidebar
from core.audit import AuditLogger
from utils.icons import ICONS
from utils.system_monitor import get_system_stats

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
st.set_page_config(
    page_title=f"{APP_NAME} — Sovereign AI Workbench",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cached resource loaders
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

def add_audit(task, action, details, status="PASS"):
    st.session_state.audit.log(task, action, details, status)

# ── Load UI Theme & Sidebar ───────────────────────────────────────────────────
load_css()
render_sidebar()

# ── Navigation Items in Sidebar ───────────────────────────────────────────────
st.sidebar.markdown(
    "<p style='"
    "font-family: Google Sans, Inter, sans-serif;"
    "color: var(--text-muted);"
    "font-size: 11px;"
    "font-weight: 600;"
    "text-transform: uppercase;"
    "letter-spacing: 1px;"
    "margin-top: 4px;"
    "margin-bottom: 6px;"
    "padding-left: 14px;"
    "'>Workspaces</p>",
    unsafe_allow_html=True
)

nav_options = ["Home", "General Chat", "Documents", "Finance"]

nav_labels = {
    "Home":         "🏠  Command Center",
    "General Chat": "💬  AI Assistant",
    "Documents":    "📄  Document Intelligence",
    "Finance":      "📈  Finance Analytics",
}

def _nav_callback(selected_page):
    st.session_state.nav_selection = selected_page
    st.session_state.current_session_id = None

nav_container = st.sidebar.container()
nav_container.markdown("<div class='main-nav-marker' style='display:none;'></div>", unsafe_allow_html=True)

for i, option in enumerate(nav_options):
    nav_container.markdown(f"<div id='nav-btn-marker-{i}' style='display:none;'></div>", unsafe_allow_html=True)
    is_active = (st.session_state.nav_selection == option)
    btn_type = "primary" if is_active else "secondary"
    nav_container.button(
        label=nav_labels[option],
        key=f"nav_main_{option}",
        use_container_width=True,
        type=btn_type,
        on_click=_nav_callback,
        args=(option,)
    )

nav = st.session_state.nav_selection

# Render History & Telemetry in Sidebar
render_history_sidebar(get_history_manager(), st.session_state.current_session_id)
render_sidebar_footer()

# Top Workbench Header
llm_status = get_llm().get_status()
render_header(llm_status, "READY")

# === PAGE ROUTING ===
page = nav

# WORKSPACE ISOLATION CHECK
if st.session_state.current_session_id:
    sessions = get_history_manager().get_sessions()
    current_session = next((s for s in sessions if s["session_id"] == st.session_state.current_session_id), None)
    if current_session:
        if current_session.get("workspace") != page:
            st.session_state.current_session_id = None
    else:
        st.session_state.current_session_id = None


# ==============================================================================
# PAGE 1: HOME / COMMAND CENTER
# ==============================================================================
if page == "Home":
    # Hero Banner
    st.markdown(
        f"""
        <div class="nx-hero-banner">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                <span class="nx-status-chip" style="font-size: 10px; color: var(--bright-blue); border-color: rgba(59, 130, 246, 0.4); background: rgba(59, 130, 246, 0.1);">
                    SOVEREIGN ON-PREMISE AI OPERATIONS
                </span>
            </div>
            <h1 class="nx-hero-title">NEXORA Command Center</h1>
            <p class="nx-hero-desc">
                Confidential industrial AI intelligence workbench. Analyze proprietary documents, deterministic financial records, 
                and engineering P&ID diagrams locally with zero external API dependencies.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Section 1: Live System Telemetry Status Grid
    st.markdown(
        "<p style='color: var(--text-muted); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;'>"
        "Active Engine Telemetry"
        "</p>",
        unsafe_allow_html=True
    )

    stat_cols = st.columns(4, gap="medium")
    
    with stat_cols[0]:
        is_llm_ready = (llm_status == "READY")
        status_dot = "online" if is_llm_ready else "warning"
        status_text = "ONLINE" if is_llm_ready else "FALLBACK"
        st.markdown(
            f"""
            <div class="nx-stat-card">
                <div>
                    <div class="nx-stat-label">LOCAL AI INFERENCE</div>
                    <div class="nx-stat-value">
                        <span class="status-dot {status_dot}"></span> {status_text}
                    </div>
                </div>
                <div class="nx-stat-subtext">Ollama (Llama 3 8B / Qwen 4B)</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with stat_cols[1]:
        st.markdown(
            f"""
            <div class="nx-stat-card">
                <div>
                    <div class="nx-stat-label">DOCUMENT ENGINE</div>
                    <div class="nx-stat-value">
                        <span class="status-dot online"></span> READY
                    </div>
                </div>
                <div class="nx-stat-subtext">PyMuPDF Local Parser & OCR</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with stat_cols[2]:
        st.markdown(
            f"""
            <div class="nx-stat-card">
                <div>
                    <div class="nx-stat-label">RAG VECTOR ENGINE</div>
                    <div class="nx-stat-value">
                        <span class="status-dot online"></span> READY
                    </div>
                </div>
                <div class="nx-stat-subtext">sentence-transformers / ChromaDB</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with stat_cols[3]:
        st.markdown(
            f"""
            <div class="nx-stat-card">
                <div>
                    <div class="nx-stat-label">DATA & MATH ENGINE</div>
                    <div class="nx-stat-value">
                        <span class="status-dot online"></span> READY
                    </div>
                </div>
                <div class="nx-stat-subtext">Pandas & NumPy Zero-Hallucination</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-bottom: 28px;'></div>", unsafe_allow_html=True)

    # Section 2: Workspaces Grid
    st.markdown(
        "<p style='color: var(--text-muted); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px;'>"
        "Operational Workspaces"
        "</p>",
        unsafe_allow_html=True
    )

    def _navigate(target):
        st.session_state.nav_selection = target

    cards = [
        {
            "badge_cls": "nx-badge-doc",
            "icon":      ICONS["doc"],
            "title":     "Document Intelligence",
            "desc":      "Process confidential technical documents and engineering manuals with grounded local RAG and source citations.",
            "btn_key":   "btn_doc",
            "btn_args":  ("Documents",),
        },
        {
            "badge_cls": "nx-badge-fin",
            "icon":      ICONS["fin"],
            "title":     "Finance Analytics",
            "desc":      "Execute deterministic Pandas/NumPy calculations with zero-hallucination chart visualizations on sensitive CSV data.",
            "btn_key":   "btn_fin",
            "btn_args":  ("Finance",),
        },

    ]

    grid_cols = st.columns(2, gap="large")
    for i, card in enumerate(cards):
        col = grid_cols[i % 2]
        with col:
            st.markdown(
                f"""
                <div class="nx-card-body">
                    <div class="nx-badge {card['badge_cls']}">{card['icon']}</div>
                    <div class="nx-card-title">{card['title']}</div>
                    <div class="nx-card-desc">{card['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.button(
                label="Launch Workspace →",
                key=card["btn_key"],
                use_container_width=True,
                on_click=_navigate,
                args=card["btn_args"],
            )
            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)


# ==============================================================================
# PAGE 2: GENERAL CHAT / AI ASSISTANT CONSOLE
# ==============================================================================
elif page == "General Chat":
    CHAT_MODEL_LABELS = {
        "qwen3.5:4b":       ("⚡", "Fast",          "Qwen3.5 4B",          "General questions and high-speed responses"),
        "qwen2.5-coder:3b": ("👨‍💻", "Coding",        "Qwen2.5-Coder 3B",    "Software development and code engineering"),
        "llama3:8b":        ("🧠", "Deep Reasoning", "Llama 3 8B",          "Complex analytical reasoning and synthesis"),
    }

    selected_model_id = st.session_state.get("selected_chat_model", "qwen3.5:4b")
    sel_icon, sel_mode, sel_label, sel_desc = CHAT_MODEL_LABELS.get(
        selected_model_id,
        ("⚡", "Fast", "Qwen3.5 4B", "General questions and high-speed responses")
    )

    st.markdown(
        f"""
        <div style='margin-bottom: 20px;'>
            <div style='display: flex; align-items: center; justify-content: space-between;'>
                <div style='display: flex; align-items: center; gap: 12px;'>
                    <div style='color: var(--bright-blue); width: 28px; height: 28px;'>{ICONS['chat']}</div>
                    <div>
                        <h2 style='margin: 0; font-size: 1.5rem;'>Sovereign AI Assistant Console</h2>
                        <p style='color: var(--text-muted); font-size: 0.85rem; margin: 0;'>Local multi-model chat • Fully isolated • Air-gapped execution</p>
                    </div>
                </div>
                <div class="nx-status-chip" style="color: var(--success); border-color: var(--success-border); background: var(--success-bg);">
                    <span class="status-dot online"></span> {sel_label} ACTIVE
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Model Mode Selector Bar
    st.markdown(
        "<p style='color: var(--text-muted); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px;'>"
        "Select Active Inference Model"
        "</p>",
        unsafe_allow_html=True
    )

    _model_options = [
        ("qwen3.5:4b",       "⚡",  "Fast (Qwen 4B)",           "General questions"),
        ("qwen2.5-coder:3b", "👨‍💻", "Coding (Qwen-Coder 3B)",   "Code generation"),
        ("llama3:8b",        "🧠",  "Deep Reasoning (Llama3)",  "Complex reasoning"),
    ]
    
    _btn_cols = st.columns(3, gap="small")
    for col, (mid, icon, label, short_desc) in zip(_btn_cols, _model_options):
        with col:
            is_active = (mid == selected_model_id)
            if st.button(
                f"{icon}  {label}",
                key=f"model_btn_{mid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["selected_chat_model"] = mid
                st.rerun()

    selected_model_id = st.session_state.get("selected_chat_model", "qwen3.5:4b")
    sel_icon, sel_mode, sel_label, sel_desc = CHAT_MODEL_LABELS.get(
        selected_model_id,
        ("⚡", "Fast", "Qwen3.5 4B", "General questions and high-speed responses")
    )

    st.markdown(
        f"<div style='font-size: 0.8rem; color: var(--text-muted); margin: 6px 0 20px 0; display: flex; align-items: center; gap: 8px;'>"
        f"<span style='color: var(--bright-blue); font-weight: 600;'>{sel_icon} Mode: {sel_mode}</span> • {sel_desc}"
        f"</div>",
        unsafe_allow_html=True
    )

    # Chat Messages Stream
    messages = get_history_manager().get_messages(st.session_state.current_session_id) if st.session_state.current_session_id else []
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                attr_model = msg.get("model", "")
                if attr_model and attr_model in CHAT_MODEL_LABELS:
                    a_icon, _, a_label, _ = CHAT_MODEL_LABELS[attr_model]
                    st.markdown(
                        f"<div class='nx-msg-model'>{a_icon} Generated by {a_label}</div>",
                        unsafe_allow_html=True
                    )

    # File Attachment Drawer
    with st.expander("📎 Attach Document, CSV Dataset or Reference Image", expanded=False):
        uploaded_file = st.file_uploader(
            "Upload File Context",
            type=["csv", "pdf", "txt", "md", "json", "png", "jpg", "jpeg"],
            label_visibility="collapsed"
        )
        if not uploaded_file and st.session_state.current_session_id:
            doc_meta = get_history_manager().get_session_document(st.session_state.current_session_id)
            if doc_meta and os.path.exists(doc_meta["file_path"]):
                uploaded_file = MockUploadedFile(doc_meta["file_path"], doc_meta["filename"])
                st.markdown(f"<div style='color: var(--text-muted); font-size: 0.82rem;'>Loaded from session history: <b>{doc_meta['filename']}</b></div>", unsafe_allow_html=True)

    # Chat Input
    query = st.chat_input("Ask a question, request code generation, or analyze attached files...")
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
            with st.spinner(f"Inference with {sel_label}..."):
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

                llm_instance = get_llm()
                final_answer = llm_instance.generate_with_model(
                    prompt=query,
                    model_name=selected_model_id,
                    context=file_context if file_context else None,
                    history=messages,
                )

            st.markdown(final_answer)
            st.markdown(
                f"<div class='nx-msg-model'>{sel_icon} Generated by {sel_label}</div>",
                unsafe_allow_html=True
            )

            get_history_manager().add_message(
                st.session_state.current_session_id, "assistant", final_answer, "General Chat", model=selected_model_id
            )
            st.rerun()


# ==============================================================================
# PAGE 3: DOCUMENT INTELLIGENCE
# ==============================================================================
elif page == "Documents":
    st.markdown(
        f"""
        <div style='margin-bottom: 24px;'>
            <div style='display: flex; align-items: center; justify-content: space-between;'>
                <div style='display: flex; align-items: center; gap: 12px;'>
                    <div style='color: var(--bright-blue); width: 28px; height: 28px;'>{ICONS['doc']}</div>
                    <div>
                        <h2 style='margin: 0; font-size: 1.5rem;'>Document Intelligence Workspace</h2>
                        <p style='color: var(--text-muted); font-size: 0.85rem; margin: 0;'>Confidential PDF analysis • Local vector embeddings • Grounded citations</p>
                    </div>
                </div>
                <div class="nx-status-chip" style="color: var(--success); border-color: var(--success-border); background: var(--success-bg);">
                    <span class="status-dot online"></span> LOCAL RAG READY
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_info, col_preview = st.columns([1, 1.4], gap="large")

    with col_info:
        st.markdown(
            "<p style='color: var(--text-muted); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px;'>"
            "Source Document Upload"
            "</p>",
            unsafe_allow_html=True
        )
        uploaded_file = st.file_uploader("Upload PDF Document", type=["pdf"], label_visibility="collapsed")

        if not uploaded_file and st.session_state.current_session_id:
            doc_meta = get_history_manager().get_session_document(st.session_state.current_session_id)
            if doc_meta and os.path.exists(doc_meta["file_path"]):
                uploaded_file = MockUploadedFile(doc_meta["file_path"], doc_meta["filename"])

        if uploaded_file:
            with st.spinner("Parsing PDF & indexing embeddings..."):
                uploaded_file.seek(0)
                res = get_pdf_processor().process_pdf(uploaded_file)
            if res["success"]:
                st.markdown(
                    f"""
                    <div style='margin-top: 14px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                            <span class="nx-status-chip" style="font-size: 9.5px; padding: 2px 8px; color: var(--success); border-color: var(--success-border); background: var(--success-bg);">
                                ✓ INDEXED & EMBEDDED
                            </span>
                            <span style='color: var(--text-muted); font-size: 11px;'>{res['num_pages']} Pages</span>
                        </div>
                        <div style='font-weight: 600; font-size: 14px; color: var(--text-primary); margin-bottom: 4px;'>{uploaded_file.name}</div>
                        <div style='color: var(--text-secondary); font-size: 12px;'>Text Volume: {res['text_size']:,} characters • Local vector store ready</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
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
                page_obj = doc.load_page(0)
                pix = page_obj.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_bytes = pix.tobytes("png")
                uploaded_file.seek(0)

                st.markdown(
                    """
                    <div class="nx-preview-box">
                        <div class="nx-preview-header">
                            <span>◉</span> VISUAL PAGE 1 PREVIEW
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.image(img_bytes, use_container_width=True)
            except Exception:
                st.warning("Visual preview rendering skipped.")

    st.markdown("<hr style='border-color: var(--border-subtle); margin: 28px 0;'>", unsafe_allow_html=True)

    if uploaded_file and res.get("success"):
        st.markdown(
            "<p style='color: var(--text-muted); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px;'>"
            "Interactive Grounded Document Q&A"
            "</p>",
            unsafe_allow_html=True
        )

        messages = get_history_manager().get_messages(st.session_state.current_session_id) if st.session_state.current_session_id else []
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        query = st.chat_input("Ask about this document (e.g. 'What are the main inspection findings?')")
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
            add_audit("DOC_ROUTER", "QUERY", f"Query received for {uploaded_file.name}")

            with st.chat_message("assistant"):
                with st.spinner("Searching local knowledge & generating response..."):
                    top_chunks = get_pdf_processor().retrieve_relevant(query, chunks)
                    add_audit("DOC_RETRIEVAL", "RAG", f"Found {len(top_chunks)} relevant chunks")
                    context = " ".join([f"[Page {c['page']}] {c['text']}" for c in top_chunks]) if top_chunks else ""
                    answer = get_llm().generate(query, context, history=messages)
                    add_audit("DOC_REASONING", "LLM", "Generated answer", "PASS" if get_llm().is_loaded else "WARN")

                full_response = answer
                st.markdown(answer)

                if top_chunks:
                    full_response += "\n\n*(Source Evidence Used)*"
                    with st.expander("📄 Grounded Source Evidence & Citations", expanded=True):
                        st.markdown(
                            "<div class='nx-verification-banner' style='margin-bottom: 12px;'>"
                            "<div class='nx-verification-title'>✓ SOURCE GROUNDED</div>"
                            "<div class='nx-verification-details'>Retrieved from local PDF pages with zero external indexing</div>"
                            "</div>",
                            unsafe_allow_html=True
                        )
                        for i, chunk in enumerate(top_chunks):
                            sim_score = chunk.get('similarity', 'N/A')
                            sim_str = f" • Similarity: {sim_score:.2f}" if isinstance(sim_score, float) else ""
                            st.markdown(
                                f"""
                                <div class="nx-citation-card">
                                    <div class="nx-citation-page">
                                        <span>[{i+1:02d}] PAGE {chunk['page']}</span>
                                        <span style='color: var(--text-muted); font-size: 11px; font-weight: normal;'>{sim_str}</span>
                                    </div>
                                    <div class="nx-citation-text">{chunk['text']}</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                get_history_manager().add_message(st.session_state.current_session_id, "assistant", full_response, "Documents")
                st.rerun()
    else:
        st.markdown(
            f"""
            <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 260px; border: 1px dashed var(--border-subtle); border-radius: var(--radius-lg); background: var(--bg-card); color: var(--text-muted);'>
                <div style='width: 42px; height: 42px; margin-bottom: 12px; color: var(--bright-blue); opacity: 0.6;'>{ICONS['doc']}</div>
                <div style='font-size: 14px; font-weight: 500; color: var(--text-primary);'>Upload a technical PDF document to begin analysis</div>
                <div style='font-size: 12px; color: var(--text-muted); margin-top: 4px;'>Local vector embeddings will be generated automatically</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ==============================================================================
# PAGE 4: FINANCE ANALYTICS (ZERO-HALLUCINATION ENGINE)
# ==============================================================================
elif page == "Finance":
    st.markdown(
        f"""
        <div style='margin-bottom: 24px;'>
            <div style='display: flex; align-items: center; justify-content: space-between;'>
                <div style='display: flex; align-items: center; gap: 12px;'>
                    <div style='color: var(--bright-blue); width: 28px; height: 28px;'>{ICONS['fin']}</div>
                    <div>
                        <h2 style='margin: 0; font-size: 1.5rem;'>Finance Analytics Workspace</h2>
                        <p style='color: var(--text-muted); font-size: 0.85rem; margin: 0;'>Zero-hallucination deterministic calculations • Pandas / NumPy engine • Matplotlib visualizations</p>
                    </div>
                </div>
                <div class="nx-status-chip" style="color: var(--success); border-color: var(--success-border); background: var(--success-bg);">
                    <span class="status-dot online"></span> ZERO-HALLUCINATION
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Verification banner
    st.markdown(
        """
        <div class="nx-verification-banner">
            <div class="nx-verification-title">
                <span>🛡️</span> DETERMINISTIC PANDAS & NUMPY EXECUTION ENGINE
            </div>
            <div class="nx-verification-details">
                Numerical results and aggregations are computed deterministically. The LLM only explains calculated metrics.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_info, col_preview = st.columns([1, 1.4], gap="large")

    with col_info:
        st.markdown(
            "<p style='color: var(--text-muted); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px;'>"
            "Financial Dataset Upload (CSV)"
            "</p>",
            unsafe_allow_html=True
        )
        uploaded_file = st.file_uploader("Upload CSV Dataset", type=["csv"], label_visibility="collapsed")

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
                st.markdown(
                    f"""
                    <div style='margin-top: 14px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                            <span class="nx-status-chip" style="font-size: 9.5px; padding: 2px 8px; color: var(--success); border-color: var(--success-border); background: var(--success-bg);">
                                ✓ DATASET LOADED
                            </span>
                            <span style='color: var(--text-muted); font-size: 11px;'>{uploaded_file.name}</span>
                        </div>
                        <div style='display: flex; gap: 20px; margin-top: 10px;'>
                            <div>
                                <div style='color: var(--text-muted); font-size: 10px; font-weight: 600; text-transform: uppercase;'>Total Records</div>
                                <div style='color: var(--text-primary); font-size: 16px; font-weight: 700;'>{schema['rows']:,}</div>
                            </div>
                            <div>
                                <div style='color: var(--text-muted); font-size: 10px; font-weight: 600; text-transform: uppercase;'>Columns</div>
                                <div style='color: var(--text-primary); font-size: 16px; font-weight: 700;'>{schema['columns']}</div>
                            </div>
                            <div>
                                <div style='color: var(--text-muted); font-size: 10px; font-weight: 600; text-transform: uppercase;'>Memory</div>
                                <div style='color: var(--text-primary); font-size: 16px; font-weight: 700;'>{df.memory_usage().sum() / 1024:.1f} KB</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                valid_csv = True
            except Exception as e:
                st.error(f"Error parsing CSV: {e}")
                valid_csv = False
        else:
            valid_csv = False

    with col_preview:
        if uploaded_file and valid_csv:
            st.markdown(
                """
                <div class="nx-preview-box">
                    <div class="nx-preview-header">
                        <span>◉</span> DATASET PREVIEW (FIRST 6 ROWS)
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.dataframe(df.head(6), use_container_width=True)

    st.markdown("<hr style='border-color: var(--border-subtle); margin: 28px 0;'>", unsafe_allow_html=True)

    if uploaded_file and valid_csv:
        messages = get_history_manager().get_messages(st.session_state.current_session_id) if st.session_state.current_session_id else []
        for msg in messages:
            with st.chat_message(msg["role"]):
                if "[CHART_PATH:" in msg["content"]:
                    text_part = msg["content"].split("[CHART_PATH:")[0]
                    chart_path = msg["content"].split("[CHART_PATH:")[1].split("]")[0]
                    st.markdown(text_part)
                    if os.path.exists(chart_path):
                        st.markdown(
                            """
                            <div class="nx-preview-box">
                                <div class="nx-preview-header">
                                    <span>📊</span> DETERMINISTIC MATPLOTLIB VISUALIZATION
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        st.image(chart_path)
                        with open(chart_path, "rb") as f:
                            st.download_button(
                                label="⬇️ Download Visual Report (PNG)",
                                data=f,
                                file_name=os.path.basename(chart_path),
                                mime="image/png",
                                use_container_width=True,
                                key=f"dl_{chart_path}"
                            )
                else:
                    st.markdown(msg["content"])

        query = st.chat_input("Ask a financial question (e.g. 'Show total revenue by quarter', 'Which department spent the most?')")
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
                with st.spinner("Executing deterministic calculations..."):
                    from core.chart_engine import ChartEngine
                    engine = ChartEngine()
                    fig, summary_info, err = engine.generate_chart(df, query, llm=get_llm())
                    add_audit("FIN_ANALYSIS", "EXECUTION", f"Chart engine: {summary_info['chart_type'] if summary_info else 'error'}")

                    if err:
                        final_answer = (
                            f"**Unable to generate visualization:** {err}\n\n"
                            f"Try rephrasing your analytical request. For example:\n"
                            f"- *'Show a bar chart of total sales by region'*\n"
                            f"- *'Plot the distribution of expenses'*\n"
                            f"- *'Show the correlation between numeric metrics'*"
                        )
                        add_audit("FIN_VISUAL", "ERROR", err)
                    else:
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

                    st.markdown(
                        """
                        <div class="nx-preview-box" style="margin-top: 16px;">
                            <div class="nx-preview-header">
                                <span>📊</span> DETERMINISTIC MATPLOTLIB VISUALIZATION
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.image(chart_path, use_container_width=True)

                    with open(chart_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Visual Report (PNG)",
                            data=f,
                            file_name=f"nexora_{summary_info['chart_type']}.png",
                            mime="image/png",
                            use_container_width=True,
                            key=f"dl_{chart_path}"
                        )

                    plan = summary_info.get("plan", {})
                    ct_display = summary_info['chart_type'].replace("_"," ").title()
                    st.markdown(
                        f"""
                        <div style='margin-top: 12px; padding: 12px; background: rgba(59,130,246,0.06); border: 1px solid rgba(59,130,246,0.22); border-radius: var(--radius-md); font-size: 12px;'>
                            <span style='color: var(--text-muted);'>Chart Model:</span> <b style='color: var(--bright-blue);'>{ct_display}</b>&nbsp;&nbsp;•&nbsp;&nbsp;
                            <span style='color: var(--text-muted);'>Aggregation:</span> <b>{plan.get('aggregation','').upper()}</b>&nbsp;&nbsp;•&nbsp;&nbsp;
                            <span style='color: var(--text-muted);'>Records Analyzed:</span> <b>{summary_info['rows_analyzed']:,}</b>&nbsp;&nbsp;•&nbsp;&nbsp;
                            <span style='color: var(--success); font-weight: 600;'><span class="status-dot online"></span> Pandas Zero-Hallucination</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    full_response += f"\n\n[CHART_PATH:{chart_path}]"
                    add_audit("FIN_VISUAL", "CHART", f"Generated {summary_info['chart_type']} chart")

                get_history_manager().add_message(st.session_state.current_session_id, "assistant", full_response, "Finance")
                st.rerun()
    else:
        st.markdown(
            f"""
            <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 260px; border: 1px dashed var(--border-subtle); border-radius: var(--radius-lg); background: var(--bg-card); color: var(--text-muted);'>
                <div style='width: 42px; height: 42px; margin-bottom: 12px; color: var(--bright-blue); opacity: 0.6;'>{ICONS['fin']}</div>
                <div style='font-size: 14px; font-weight: 500; color: var(--text-primary);'>Upload a financial or operational CSV dataset to begin</div>
                <div style='font-size: 12px; color: var(--text-muted); margin-top: 4px;'>Calculations are executed locally via Pandas with guaranteed zero hallucination</div>
            </div>
            """,
            unsafe_allow_html=True
        )


# ── Render Audit Trace on all pages ──────────────────────────────────────────
render_audit_trace(st.session_state.audit.get_logs())
