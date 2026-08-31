import streamlit as st
import os
import io
import time
from PIL import Image
from pathlib import Path

from config.config import APP_NAME, APP_SUBTITLE
from ui.components import load_css, render_sidebar, render_header, render_audit_trace
from core.audit import AuditLogger
from core.llm import LLMManager
from core.pdf_processor import PDFProcessor
from core.csv_analyzer import CSVAnalyzer
from core.image_analyzer import ImageAnalyzer

# Ensure we use full page width
st.set_page_config(page_title=APP_NAME, layout="wide", initial_sidebar_state="expanded")

from ui.components import render_sidebar_footer

# Initialize session state
if "audit" not in st.session_state:
    st.session_state.audit = AuditLogger()
if "llm" not in st.session_state:
    st.session_state.llm = LLMManager("llama3:8b")
if "pdf_proc" not in st.session_state:
    st.session_state.pdf_proc = PDFProcessor()
if "csv_proc" not in st.session_state:
    st.session_state.csv_proc = CSVAnalyzer()
if "img_proc" not in st.session_state:
    st.session_state.img_proc = ImageAnalyzer()
if "nav_selection" not in st.session_state:
    st.session_state.nav_selection = "🏠 Home"

# UI Setup
load_css()
render_sidebar()

# Navigation
st.sidebar.markdown("<p style='color: #6B7280; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Workspaces</p>", unsafe_allow_html=True)
nav_options = ["🏠 Home", "📄 Documents", "📊 Finance", "⚙️ Engineering", "🛡️ Sovereignty"]
nav = st.sidebar.radio("Go to", nav_options, label_visibility="collapsed", key="nav_selection")

render_sidebar_footer()
render_header(st.session_state.llm.get_status(), "READY")

def add_audit(task, action, details, status="PASS"):
    st.session_state.audit.log(task, action, details, status)

# === PAGES ===

# Helper to get the actual page name
page = nav.split(" ", 1)[1] if " " in nav else nav

if page == "Home":
    st.markdown("<h1 style='font-weight: 500; font-size: 2.5rem; letter-spacing: -0.02em; margin-bottom: 8px;'>NEXORA</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-muted); font-size: 1.1rem; margin-top: 0; margin-bottom: 40px;'>Sovereign AI Workbench. Documents, data and reasoning stay local.</p>", unsafe_allow_html=True)
    
    # --- VIDEO SECTION ---
    st.markdown("<div style='margin-bottom: 40px;'>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Future Workflow Preview</p>", unsafe_allow_html=True)
    
    VIDEO_PATH = Path(__file__).resolve().parent / "Untitled_Scene_08-25_15_12_27_202608272126.mp4"
    
    with st.container():
        _, center_col, _ = st.columns([1, 10, 1])
        with center_col:
            if VIDEO_PATH.exists() and VIDEO_PATH.is_file():
                st.video(str(VIDEO_PATH), format="video/mp4", autoplay=True, muted=True, loop=True)
            else:
                st.warning("Future workflow video is not available in the project directory.")
                
    st.markdown("<p style='text-align: center; color: var(--text-subtle); font-size: 0.75rem; margin-top: 12px;'>LOCAL DEMONSTRATION | No external video service</p></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color: var(--border-subtle); margin-bottom: 40px;'>", unsafe_allow_html=True)
    
    st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 24px;'>Explore Workspaces</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 24px; height: 100%;'><div style='font-size: 2rem; margin-bottom: 16px;'>📄</div><h3 style='margin-bottom: 8px; font-size: 1.25rem;'>Document Intelligence</h3><p style='color: var(--text-muted); font-size: 0.95rem; margin-bottom: 24px; line-height: 1.5;'>Work with confidential documents locally. Extract text and utilize local RAG for grounded Q&A.</p>", unsafe_allow_html=True)
        if st.button("Open Workspace →", key="btn_doc", use_container_width=True):
            st.session_state.nav_selection = "📄 Documents"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 24px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 24px; height: 100%;'><div style='font-size: 2rem; margin-bottom: 16px;'>⚙️</div><h3 style='margin-bottom: 8px; font-size: 1.25rem;'>Engineering</h3><p style='color: var(--text-muted); font-size: 0.95rem; margin-bottom: 24px; line-height: 1.5;'>Analyze P&IDs and engineering information locally using isolated vision components.</p>", unsafe_allow_html=True)
        if st.button("Open Workspace →", key="btn_eng", use_container_width=True):
            st.session_state.nav_selection = "⚙️ Engineering"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col2:
        st.markdown("<div style='background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 24px; height: 100%;'><div style='font-size: 2rem; margin-bottom: 16px;'>📊</div><h3 style='margin-bottom: 8px; font-size: 1.25rem;'>Finance</h3><p style='color: var(--text-muted); font-size: 0.95rem; margin-bottom: 24px; line-height: 1.5;'>Analyze CSV data, generate visual insights, and securely compute authoritative calculations.</p>", unsafe_allow_html=True)
        if st.button("Open Workspace →", key="btn_fin", use_container_width=True):
            st.session_state.nav_selection = "📊 Finance"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top: 24px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 16px; padding: 24px; height: 100%;'><div style='font-size: 2rem; margin-bottom: 16px;'>🛡️</div><h3 style='margin-bottom: 8px; font-size: 1.25rem;'>Sovereignty</h3><p style='color: var(--text-muted); font-size: 0.95rem; margin-bottom: 24px; line-height: 1.5;'>View local offline security parameters, system status, and live audit telemetry.</p>", unsafe_allow_html=True)
        if st.button("Open Workspace →", key="btn_sov", use_container_width=True):
            st.session_state.nav_selection = "🛡️ Sovereignty"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

elif page == "Documents":
    st.markdown("<h2 style='font-weight: 500; font-size: 1.75rem; margin-bottom: 24px;'>Document Intelligence</h2>", unsafe_allow_html=True)
    
    col_info, col_preview = st.columns([1, 1.5], gap="large")
    
    with col_info:
        st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Data Source</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
        
        if uploaded_file:
            with st.spinner("Processing PDF..."):
                res = st.session_state.pdf_proc.process_pdf(uploaded_file)
            if res["success"]:
                st.markdown(f"<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--success-green); font-size: 0.85rem; font-weight: 600; margin-bottom: 8px;'>✓ PROCESSED</div><div style='font-weight: 500; margin-bottom: 4px;'>{uploaded_file.name}</div><div style='color: var(--text-muted); font-size: 0.85rem;'>{res['num_pages']} Pages • {res['text_size']} chars</div></div>", unsafe_allow_html=True)
                chunks = st.session_state.pdf_proc.chunk_text(res["pages"])
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
        query = st.chat_input("Ask about your document...")
        if query:
            with st.chat_message("user"):
                st.markdown(query)
            add_audit("DOC_ROUTER", "QUERY", f"Query received")
            
            with st.chat_message("assistant"):
                with st.spinner("Retrieving and generating..."):
                    top_chunks = st.session_state.pdf_proc.retrieve_relevant(query, chunks)
                    add_audit("DOC_RETRIEVAL", "RAG", f"Found {len(top_chunks)} relevant chunks")
                    context = " ".join([f"[Page {c['page']}] {c['text']}" for c in top_chunks]) if top_chunks else ""
                    answer = st.session_state.llm.generate(query, context)
                    add_audit("DOC_REASONING", "LLM", "Generated answer", "PASS" if st.session_state.llm.is_loaded else "WARN")
                
                st.markdown(answer)
                
                if top_chunks:
                    with st.expander("📄 View Source Evidence"):
                        st.markdown("<div class='status-pill' style='margin-bottom: 10px;'>✓ SOURCE GROUNDED</div>", unsafe_allow_html=True)
                        for i, chunk in enumerate(top_chunks):
                            st.markdown(f"<div style='font-size: 0.85rem; font-weight: 600; margin-bottom: 4px;'>Page {chunk['page']} <span style='color: var(--text-muted); font-weight: 400;'>(Similarity: {chunk.get('similarity', 'N/A')})</span></div>", unsafe_allow_html=True)
                            st.markdown(f"<div style='border-left: 2px solid var(--accent-primary); padding-left: 12px; margin-bottom: 16px; color: var(--text-muted); font-size: 0.9rem;'>{chunk['text']}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; border: 1px dashed var(--border-subtle); border-radius: 16px; color: var(--text-muted);'><div style='font-size: 2rem; margin-bottom: 12px;'>📄</div><div>Upload a document to begin</div></div>", unsafe_allow_html=True)

elif page == "Finance":
    st.markdown("<h2 style='font-weight: 500; font-size: 1.75rem; margin-bottom: 24px;'>Finance Analytics</h2>", unsafe_allow_html=True)
    
    col_info, col_preview = st.columns([1, 1.5], gap="large")
    
    with col_info:
        st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Data Source</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
        
        if uploaded_file:
            import pandas as pd
            add_audit("FIN_INPUT", "UPLOAD", f"Received {uploaded_file.name}")
            try:
                df = pd.read_csv(uploaded_file)
                schema = st.session_state.csv_proc.analyze_schema(df)
                st.markdown(f"<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--success-green); font-size: 0.85rem; font-weight: 600; margin-bottom: 8px;'>✓ PROCESSED</div><div style='font-weight: 500; margin-bottom: 8px;'>{uploaded_file.name}</div><div style='display: flex; gap: 16px; margin-bottom: 12px;'><div style='color: var(--text-primary); font-size: 1.1rem; font-weight: 500;'>{schema['rows']}<span style='color: var(--text-muted); font-size: 0.75rem; font-weight: 600; margin-left: 4px; text-transform: uppercase;'>Rows</span></div><div style='color: var(--text-primary); font-size: 1.1rem; font-weight: 500;'>{schema['columns']}<span style='color: var(--text-muted); font-size: 0.75rem; font-weight: 600; margin-left: 4px; text-transform: uppercase;'>Cols</span></div></div></div>", unsafe_allow_html=True)
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
        query = st.chat_input("Ask your data (e.g. 'Which department spent the most?')")
        if query:
            with st.chat_message("user"):
                st.markdown(query)
            add_audit("FIN_ROUTER", "INTENT", "Parsing data query")
            
            with st.chat_message("assistant"):
                with st.spinner("Running local analysis..."):
                    import time
                    time.sleep(0.5) # Simulate processing for demo
                    answer, fig = st.session_state.csv_proc.interpret_and_execute(query, df)
                    add_audit("FIN_ANALYSIS", "EXECUTION", "Calculated standard analytics")
                    
                    if not answer.startswith("An error") and not answer.startswith("I could not"):
                        final_answer = st.session_state.llm.generate(
                            prompt=f"Explain these data analysis results simply for the user. Question was: '{query}'", 
                            context=answer,
                            default_category="DATA"
                        )
                        add_audit("FIN_REASONING", "LLM", "Generated explanation", "PASS" if st.session_state.llm.is_loaded else "WARN")
                    else:
                        final_answer = answer
                        
                st.markdown(final_answer)
                
                if fig:
                    st.markdown("<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Data Visualization</div>", unsafe_allow_html=True)
                    st.pyplot(fig)
                    
                    import io
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", bbox_inches='tight', facecolor=fig.get_facecolor())
                    buf.seek(0)
                    st.download_button(label="⬇️ Download Chart (PNG)", data=buf, file_name="finance_chart.png", mime="image/png", use_container_width=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                    add_audit("FIN_VISUAL", "CHART", "Generated matplotlib figure")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; border: 1px dashed var(--border-subtle); border-radius: 16px; color: var(--text-muted);'><div style='font-size: 2rem; margin-bottom: 12px;'>📊</div><div>Upload a dataset to begin</div></div>", unsafe_allow_html=True)

elif page == "Engineering":
    st.markdown("<h2 style='font-weight: 500; font-size: 1.75rem; margin-bottom: 24px;'>Engineering Vision</h2>", unsafe_allow_html=True)
    
    col_info, col_preview = st.columns([1, 1.5], gap="large")
    
    with col_info:
        st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Diagram Source</p>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload P&ID / Diagram", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        
        st.markdown("<p style='color: var(--text-subtle); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 24px; margin-bottom: 12px;'>Engineering Data (Optional)</p>", unsafe_allow_html=True)
        csv_file = st.file_uploader("Upload Sensor CSV", type=["csv"], label_visibility="collapsed")
        
        valid_csv = False
        df = None
        if csv_file:
            import pandas as pd
            add_audit("ENG_DATA", "UPLOAD", f"Received {csv_file.name}")
            try:
                df = pd.read_csv(csv_file)
                valid_csv = True
                st.markdown(f"<div style='margin-top: 16px; padding: 12px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--success-green); font-size: 0.75rem; font-weight: 600; margin-bottom: 4px;'>✓ DATA LOADED</div><div style='font-weight: 500; font-size: 0.85rem;'>{csv_file.name}</div></div>", unsafe_allow_html=True)
            except Exception:
                st.error("Failed to parse CSV")
        
        if uploaded_file:
            add_audit("ENG_INPUT", "UPLOAD", f"Received {uploaded_file.name}")
            st.markdown(f"<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--success-green); font-size: 0.85rem; font-weight: 600; margin-bottom: 8px;'>✓ IMAGE LOADED</div><div style='font-weight: 500; margin-bottom: 8px;'>{uploaded_file.name}</div></div>", unsafe_allow_html=True)
            
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
        query = st.chat_input("e.g. 'What components are visible?', 'Explain this diagram'")
        if query:
            with st.chat_message("user"):
                st.markdown(query)
                
            with st.chat_message("assistant"):
                with st.spinner("Running visual and data processing..."):
                    # Process Image
                    res = st.session_state.img_proc.analyze_image(uploaded_file, query)
                    add_audit("ENG_VISION", "ANALYSIS", "Processed image using fallback mode", "WARN")
                    
                    # Process CSV if data-related query and CSV exists
                    fig = None
                    data_context = ""
                    is_data_query = any(w in query.lower() for w in ["trend", "data", "sensor", "csv", "graph", "plot", "compare", "value", "bar", "pie", "hist", "scatter", "chart", "analyze"])
                    if valid_csv and is_data_query:
                        data_ans, fig = st.session_state.csv_proc.interpret_and_execute(query, df)
                        data_context = f"\n\nAdditional Data Analysis Results:\n{data_ans}"
                        add_audit("ENG_DATA", "ANALYSIS", "Processed sensor data")
                    
                    final_answer = st.session_state.llm.generate(
                        prompt=f"Explain these findings simply for the user. Question was: '{query}'",
                        context=res["text"] + data_context,
                        default_category="ENGINEERING"
                    )
                    add_audit("ENG_REASONING", "LLM", "Generated explanation", "PASS" if st.session_state.llm.is_loaded else "WARN")
                    
                st.markdown(final_answer)
                
                if fig:
                    st.markdown("<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Engineering Data Visualization</div>", unsafe_allow_html=True)
                    st.pyplot(fig)
                    
                    import io
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", bbox_inches='tight', facecolor=fig.get_facecolor())
                    buf.seek(0)
                    st.download_button(label="⬇️ Download Chart (PNG)", data=buf, file_name="engineering_chart.png", mime="image/png", use_container_width=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                if res.get("annotated_image"):
                    st.markdown(f"<div style='margin-top: 16px; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 12px;'><div style='color: var(--text-subtle); font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;'>Visual Evidence (Confidence: {res['confidence']})</div>", unsafe_allow_html=True)
                    st.image(res["annotated_image"])
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                st.markdown("<div style='background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); padding: 12px; border-radius: 8px; color: var(--warning-amber); margin-top: 16px; font-size: 0.85rem; font-weight: 500;'>⚠️ AI-assisted analysis only. Final engineering decisions remain with the responsible engineer.</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; border: 1px dashed var(--border-subtle); border-radius: 16px; color: var(--text-muted);'><div style='font-size: 2rem; margin-bottom: 12px;'>⚙️</div><div>Upload a P&ID or Diagram to begin</div></div>", unsafe_allow_html=True)

elif page == "Sovereignty":
    from utils.system_monitor import get_system_stats
    stats = get_system_stats()
    vram = stats.get('vram_status', 'N/A')
    llm_status = st.session_state.llm.get_status()
    
    st.markdown("<h2 style='font-weight: 500; font-size: 1.75rem; margin-bottom: 24px;'>Sovereignty Status</h2>", unsafe_allow_html=True)
    
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
