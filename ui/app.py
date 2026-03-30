"""
ui/app.py
---------
Streamlit dashboard for the Multi-Source Data Extraction Engine.
"""

import sys
import os
import json
import shutil
import tempfile
import uuid
from pathlib import Path
from datetime import datetime
import time

# ── Fix imports: ensure project root is on sys.path ──────────────────────────
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd

# ── Page configuration (must be first Streamlit call) ────────────────────────
st.set_page_config(
    page_title="Data Extraction Engine",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

.stApp { background-color: #080b12 !important; }

[data-testid="stAppViewContainer"] { background-color: #080b12 !important; }

[data-testid="stSidebar"] {
  background-color: #0d1117 !important;
  border-right: 1px solid #1e2d40;
}

.stButton > button {
  background: transparent !important;
  border: 1px solid #00d4ff !important;
  color: #00d4ff !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 0 12px rgba(0,212,255,0.1) !important;
}

.stButton > button:hover {
  background: rgba(0,212,255,0.1) !important;
  box-shadow: 0 0 24px rgba(0,212,255,0.3) !important;
  transform: translateY(-1px) !important;
}

.stTextInput > div > div > input {
  background-color: #111827 !important;
  border: 1px solid #1e2d40 !important;
  color: #e2e8f0 !important;
  border-radius: 8px !important;
}

.stTextInput > div > div > input:focus {
  border-color: #00d4ff !important;
  box-shadow: 0 0 0 2px rgba(0,212,255,0.15) !important;
}

.stSelectbox > div > div {
  background-color: #111827 !important;
  border: 1px solid #1e2d40 !important;
  color: #e2e8f0 !important;
  border-radius: 8px !important;
}

.stTextArea > div > div > textarea {
  background-color: #111827 !important;
  border: 1px solid #1e2d40 !important;
  color: #e2e8f0 !important;
  border-radius: 8px !important;
}

[data-testid="stDataFrame"] {
  background-color: #111827 !important;
  border: 1px solid #1e2d40 !important;
  border-radius: 12px !important;
}

p, label, .stMarkdown { color: #e2e8f0 !important; }

h1, h2, h3 { color: #e2e8f0 !important; }

/* Injected Container Styling for major sections natively wrapping widgets */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: linear-gradient(145deg, #111827, #0d1421) !important;
  border: 1px solid #1e2d40 !important;
  border-left: 3px solid #00d4ff !important;
  border-radius: 12px !important;
  padding: 1.5rem !important;
  margin-bottom: 1rem !important;
  box-shadow: 0 4px 24px rgba(0,0,0,0.4) !important;
}

/* Base custom table styles */
.custom-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 10px; }
.custom-table th { background-color: #111827; color: #00d4ff; text-align: left; padding: 12px; border-bottom: 1px solid #1e2d40; }
.custom-table tr:nth-child(even) { background-color: #111827; }
.custom-table tr:nth-child(odd) { background-color: #1c2333; }
.custom-table td { padding: 12px; border-bottom: 1px solid #1e2d40; }
.status-pill { padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; }
.pill-success { background: rgba(16,185,129,0.2); color: #10b981; }
.pill-error { background: rgba(244,63,94,0.2); color: #f43f5e; }

[data-testid="stFileUploader"] {
  background-color: #111827 !important;
  border: 1px dashed #1e2d40 !important;
  border-radius: 12px !important;
  padding: 1rem !important;
}

[data-testid="stFileUploader"]:hover {
  border-color: #00d4ff !important;
  box-shadow: 0 0 16px rgba(0, 212, 255, 0.15) !important;
}

[data-testid="stFileUploaderDropzone"] {
  background-color: #111827 !important;
  color: #64748b !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] {
  color: #64748b !important;
}

.uploadedFileName {
  color: #e2e8f0 !important;
}

section[data-testid="stFileUploadDropzone"] button {
  background: transparent !important;
  border: 1px solid #00d4ff !important;
  color: #00d4ff !important;
  border-radius: 8px !important;
}

</style>
""", unsafe_allow_html=True)


# ── Load config ──────────────────────────────────────────────────────────────
def load_config(config_path: str = None) -> dict:
    if config_path is None:
        config_path = os.path.join(PROJECT_ROOT, "config.json")
    config = {}
    if Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    return config

# ── Upload helpers ───────────────────────────────────────────────────────────
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "data", "input", "_uploads")

def save_uploaded_file(uploaded_file) -> str:
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    # Prefix with short uuid to prevent identical filenames from overwriting each other
    unique_name = f"{uuid.uuid4().hex[:8]}_{uploaded_file.name}"
    dest = os.path.join(UPLOAD_DIR, unique_name)
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return dest

def clear_uploads():
    if Path(UPLOAD_DIR).exists():
        shutil.rmtree(UPLOAD_DIR, ignore_errors=True)

def records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    rows = []
    for i, r in enumerate(records):
        source_val = r.get("source", "")
        if isinstance(source_val, dict):
            src_str = source_val.get("file_name") or source_val.get("url") or source_val.get("name") or str(source_val)
        elif isinstance(source_val, str):
            src_str = os.path.basename(source_val) if source_val else "unknown"
        else:
            src_str = str(source_val)
            
        row = {"id": r.get("id", f"REC-{i:04d}"), "source": src_str}
        content = r.get("content", {})
        if isinstance(content, dict):
            for k, v in content.items():
                row[k] = v
        else:
            row["content"] = str(content)
        meta = r.get("metadata", {})
        if isinstance(meta, dict):
            row["file_name"] = meta.get("file_name", "")
            row["extracted_at"] = meta.get("extracted_at", "")
        # Dummy status based on input if real status not found
        row["status"] = r.get("status", "SUCCESS")
        rows.append(row)
    return pd.DataFrame(rows)

def show_alert(text: str, type: str = "success"):
    if type == "success":
        st.markdown(f"""
        <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2);
          border-left:4px solid #10b981; border-radius:8px; padding:0.9rem 1.2rem;
          color:#10b981; font-weight:500; margin:0.5rem 0;">
          ✅ {text}
        </div>
        """, unsafe_allow_html=True)
    elif type == "error":
        st.markdown(f"""
        <div style="background:rgba(244,63,94,0.08); border:1px solid rgba(244,63,94,0.2);
          border-left:4px solid #f43f5e; border-radius:8px; padding:0.9rem 1.2rem;
          color:#f43f5e; font-weight:500; margin:0.5rem 0;">
          ❌ {text}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.2);
          border-left:4px solid #f59e0b; border-radius:8px; padding:0.9rem 1.2rem;
          color:#f59e0b; font-weight:500; margin:0.5rem 0;">
          ⚠️ {text}
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — Configuration Panel
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
            <div style="font-size: 24px;">⚙️</div>
            <h2 style="margin:0; font-size: 18px; color: #e2e8f0; font-weight: 700;">Settings</h2>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="color:#64748b; font-size:12px; font-weight:700; text-transform:uppercase; margin-bottom:8px;">Configuration</div>', unsafe_allow_html=True)
    output_format = st.selectbox("Output Format", ["json", "csv"], index=0, label_visibility="collapsed")
    llm_format = st.selectbox("LLM Syntax Format", ["instruction", "text"], index=0, label_visibility="collapsed")

    st.markdown("<hr style='border:none; border-top:1px solid #1e2d40;'>", unsafe_allow_html=True)
    
    st.markdown('<div style="color:#64748b; font-size:12px; font-weight:700; text-transform:uppercase; margin-bottom:8px;">Processing Options</div>', unsafe_allow_html=True)
    enable_dedup = st.checkbox("Exact Deduplication", value=True)
    enable_fuzzy = st.checkbox("Fuzzy Deduplication", value=False)
    enable_parallel = st.checkbox("Parallel Processing", value=False)
    
    st.markdown("<hr style='border:none; border-top:1px solid #1e2d40;'>", unsafe_allow_html=True)
    
    st.markdown('<div style="color:#64748b; font-size:12px; font-weight:700; text-transform:uppercase; margin-bottom:8px;">Resiliency</div>', unsafe_allow_html=True)
    max_retries = st.slider("Max Retries", min_value=1, max_value=5, value=3, label_visibility="collapsed")

# ══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="padding:2.5rem 0 1.5rem 0; text-align:center;">
  <div style="font-size:2.8rem; font-weight:800; letter-spacing:-1px;
    background:linear-gradient(90deg,#00d4ff,#7c3aed);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
    ⚡ DataFlow Engine
  </div>
  <div style="color:#64748b; font-size:0.85rem; margin-top:0.5rem;
    letter-spacing:3px; text-transform:uppercase;">
    Multi-Source Data Extraction Pipeline
  </div>
  <div style="margin-top:1.2rem; height:2px;
    background:linear-gradient(90deg,transparent,#00d4ff,#7c3aed,transparent);">
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_input, tab_results, tab_logs = st.tabs(["📥 Input Configuration", "📊 Extraction Results", "📝 Execution Logs"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB: INPUT
# ─────────────────────────────────────────────────────────────────────────────
with tab_input:
    with st.container(border=True):
        st.markdown("<h4 style='margin-top:0;'>1. Ingestion Mode</h4>", unsafe_allow_html=True)
        input_mode = st.radio(
            "Select how you want to ingest data:",
            ["Single Source", "Batch Processing"],
            horizontal=True,
            label_visibility="collapsed"
        )

    sources = []
    
    with st.container(border=True):
        st.markdown("<h4 style='margin-top:0;'>2. Data Endpoint Selection</h4>", unsafe_allow_html=True)
        
        if input_mode == "Single Source":
            col1, col_spacer, col2 = st.columns([1, 0.1, 1])
            
            with col1:
                st.markdown("**📄 Document Upload**")
                uploaded_files = st.file_uploader(
                    "Upload a PDF, CSV, or Excel file directly",
                    type=["csv", "xlsx", "xls", "pdf"],
                    accept_multiple_files=True,
                    label_visibility="collapsed"
                )
                
            with col2:
                st.markdown("**🌐 External URI Systems**")
                url_input = st.text_input("Web URL Endpoint", placeholder="https://example.com/data")
                db_input = st.text_input("Database Connect URI", placeholder="sqlite:///data/input/sample.db")
                
        else:  # Batch Input
            st.markdown("**📋 Upload Batch Files**")
            batch_files = st.file_uploader(
                "Upload your files for batch processing",
                type=["pdf", "csv", "xlsx", "xls", "json"],
                accept_multiple_files=True
            )
            if batch_files:
                show_alert(f"Ready to process {len(batch_files)} file(s).", "success")

    # Action Button
    _, btn_col, _ = st.columns([1, 1.5, 1])
    with btn_col:
        run_clicked = st.button("Initialize Extraction")

    if run_clicked:
        clear_uploads()
        
        if input_mode == "Single Source":
            if uploaded_files:
                for uf in uploaded_files:
                    path = save_uploaded_file(uf)
                    sources.append(path)
            if url_input and url_input.strip():
                sources.append(url_input.strip())
            if db_input and db_input.strip():
                sources.append(db_input.strip())
        else:
            if batch_files:
                for bf in batch_files:
                    suffix = os.path.splitext(bf.name)[1]
                    # We inject the original filename into the prefix so it appears in the logs/results table
                    with tempfile.NamedTemporaryFile(delete=False, prefix=f"batch_{bf.name}_", suffix=suffix) as tmp:
                        tmp.write(bf.getbuffer())
                        sources.append(tmp.name)

        if not sources:
            show_alert("Insufficient parameters: Please provide at least one valid data source.", "warning")
        else:
            config = load_config()
            config["output_format"] = output_format
            config["llm_format"] = llm_format
            config["dedup"] = enable_dedup
            config["fuzzy_dedup"] = enable_fuzzy
            config["parallel"] = enable_parallel
            config["max_retries"] = max_retries
            config["logging_level"] = "DEBUG"

            stepper_placeholder = st.empty()
            
            # Draw fake stepper
            stages = ["Detect", "Extract", "Clean", "Normalize", "Map", "Save"]
            
            def render_stepper(current_idx: int):
                html = '<div style="display:flex; justify-content:space-between; align-items:center; position:relative; margin: 30px 10px;">'
                html += '<div style="position:absolute; top:50%; left:20px; right:20px; height:2px; background:linear-gradient(90deg, #1e2d40, #7c3aed, #00d4ff); transform:translateY(-50%); z-index:1; opacity:0.5;"></div>'
                for j, stage in enumerate(stages):
                    if j < current_idx:
                        # Done
                        circle = '<div style="width:30px; height:30px; border-radius:50%; background:linear-gradient(135deg, #00d4ff, #0284c7); color:white; display:flex; align-items:center; justify-content:center; font-weight:bold; z-index:2; box-shadow:0 0 10px rgba(0,212,255,0.6);">✓</div>'
                        color = '#00d4ff'
                    elif j == current_idx:
                        # Active
                        circle = '<div style="width:30px; height:30px; border-radius:50%; background:#7c3aed; color:white; display:flex; align-items:center; justify-content:center; font-weight:bold; z-index:2; box-shadow:0 0 16px rgba(124,58,237,0.8); border:2px solid #a855f7;">•</div>'
                        color = '#7c3aed'
                    else:
                        # Pending
                        circle = '<div style="width:30px; height:30px; border-radius:50%; background:#111827; color:#64748b; display:flex; align-items:center; justify-content:center; font-weight:bold; z-index:2; border:2px solid #1e2d40;"></div>'
                        color = '#64748b'
                        
                    html += f'<div style="display:flex; flex-direction:column; align-items:center; gap:8px; z-index:2; background:#080b12; padding:0 5px;">'
                    html += f'{circle}'
                    html += f'<div style="font-size:12px; font-weight:700; text-transform:uppercase; color:{color};">{stage}</div>'
                    html += f'</div>'
                html += "</div>"
                return html

            for i in range(len(stages)):
                stepper_html = render_stepper(i)
                stepper_placeholder.markdown(stepper_html, unsafe_allow_html=True)
                time.sleep(0.3)
            
            try:
                from pipeline.orchestrator import DataPipeline
                pipeline = DataPipeline(config)

                results = []
                for source in sources:
                    result = pipeline.run(source)
                    
                    # Ensure records are captured even if pipeline output is empty
                    records = result.get("records", [])
                    job_id = result.get("job_id", "")
                    if not records and job_id:
                        short_id = str(job_id)[:8]
                        output_file = os.path.join(PROJECT_ROOT, "output", f"{short_id}_output.json")
                        if os.path.exists(output_file):
                            try:
                                with open(output_file, "r", encoding="utf-8") as f:
                                    records = json.load(f)
                                result["records"] = records
                                result["record_count"] = len(records)
                            except Exception as e:
                                print(f"Error loading {output_file}: {e}")
                                
                    print(f"Result object keys: {list(result.keys())}, records count: {len(result.get('records', []))}")
                    results.append(result)

                stepper_html = render_stepper(len(stages))
                stepper_placeholder.markdown(stepper_html, unsafe_allow_html=True)
                st.session_state["results"] = results
                st.session_state["run_complete"] = True
                show_alert("Extraction Completed! Please swap to the Results tab to view your structured datasets.", "success")

            except Exception as exc:
                show_alert(f"Execution Failed: {exc}", "error")
                stepper_placeholder.empty()
                st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TAB: RESULTS
# ─────────────────────────────────────────────────────────────────────────────
with tab_results:
    if st.session_state.get("run_complete") and st.session_state.get("results"):
        results = st.session_state["results"]
        
        success_results = [r for r in results if r.get("status") == "SUCCESS"]
        failed_results = [r for r in results if r.get("status") == "FAILED"]
        
        all_records = []
        for r in success_results:
            all_records.extend(r.get("records", []))
            
        total_records = len(all_records)
        total_time = sum(r.get("total_time_seconds", 0) for r in results)

        # EXACT USER REQUEST FOR METRICS:
        st.markdown(f"""
        <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin:1rem 0;">
          <div style="background:#111827; border:1px solid #1e2d40; border-top:2px solid #00d4ff;
            border-radius:12px; padding:1.2rem; text-align:center;">
            <div style="font-size:2rem; font-weight:700; color:#00d4ff;">{total_records:,}</div>
            <div style="color:#64748b; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; margin-top:0.3rem;">Total Records</div>
          </div>
          <div style="background:#111827; border:1px solid #1e2d40; border-top:2px solid #7c3aed;
            border-radius:12px; padding:1.2rem; text-align:center;">
            <div style="font-size:2rem; font-weight:700; color:#7c3aed;">{len(success_results)} / {len(results)}</div>
            <div style="color:#64748b; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; margin-top:0.3rem;">Sources Processed</div>
          </div>
          <div style="background:#111827; border:1px solid #1e2d40; border-top:2px solid #10b981;
            border-radius:12px; padding:1.2rem; text-align:center;">
            <div style="font-size:2rem; font-weight:700; color:#10b981;">{total_time:.2f}s</div>
            <div style="color:#64748b; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px; margin-top:0.3rem;">Execution Time</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if failed_results:
            show_alert(f"{len(failed_results)} job(s) failed. Check Logs Tab.", "warning")

        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0;'>📋 Processed Files</h4>", unsafe_allow_html=True)
            
            job_table_html = '<div style="overflow-x:auto; border-radius:8px; border:1px solid #1e2d40; margin-bottom: 1rem;"><table class="custom-table"><thead><tr>'
            job_headers = ["Job ID", "Source File", "Status", "Records Found", "Time"]
            for h in job_headers:
                job_table_html += f"<th>{h}</th>"
            job_table_html += "</tr></thead><tbody>"
            
            for r in results:
                jid = str(r.get("job_id", ""))[:8]
                
                source_val = r.get("source", "")
                if isinstance(source_val, dict):
                    src = source_val.get("file_name") or source_val.get("url") or source_val.get("name") or str(source_val)
                elif isinstance(source_val, str):
                    src = os.path.basename(source_val) if source_val else "unknown"
                else:
                    src = str(source_val)
                
                status = str(r.get("status", "UNKNOWN"))
                rcnt = str(r.get("record_count", 0))
                tme = f"{r.get('total_time_seconds', 0):.2f}s"
                
                status_html = f'<span class="status-pill pill-success">{status}</span>' if status == "SUCCESS" else f'<span class="status-pill pill-error">{status}</span>'
                
                job_table_html += f"<tr>"
                job_table_html += f'<td><span style="font-family:monospace; color:#00d4ff;">{jid}</span></td>'
                job_table_html += f'<td>{src}</td>'
                job_table_html += f'<td>{status_html}</td>'
                job_table_html += f'<td>{rcnt}</td>'
                job_table_html += f'<td>{tme}</td>'
                job_table_html += f"</tr>"
            job_table_html += "</tbody></table></div>"
            st.markdown(job_table_html, unsafe_allow_html=True)
            
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0;'>📄 Extracted Data Preview</h4>", unsafe_allow_html=True)

            if all_records:
                tab_struct, tab_raw = st.tabs(["📊 Structured Data", "📝 Raw Text"])
                
                with tab_struct:
                    df = pd.json_normalize(all_records[:50])
                    
                    # Render custom HTML table
                    table_html = '<div style="overflow-x:auto; border-radius:8px; border:1px solid #1e2d40;"><table class="custom-table"><thead><tr>'
                    for col in df.columns:
                        table_html += f"<th>{col}</th>"
                    table_html += "</tr></thead><tbody>"
                    
                    for _, row in df.iterrows():
                        table_html += "<tr>"
                        for col in df.columns:
                            val = str(row[col])
                            
                            if col.lower() == "id":
                                val = f'<span style="font-family:monospace; color:#00d4ff;">{val}</span>'
                            elif col.lower() == "status":
                                if "SUCCESS" in val.upper():
                                    val = f'<span class="status-pill pill-success">{val}</span>'
                                else:
                                    val = f'<span class="status-pill pill-error">{val}</span>'
                            elif len(val) > 80: 
                                val = val[:77] + "..."
                                
                            table_html += f'<td>{val}</td>'
                        table_html += "</tr>"
                    table_html += "</tbody></table></div>"
                    
                    st.markdown(table_html, unsafe_allow_html=True)
                
                with tab_raw:
                    st.markdown("<div style='color:#64748b; font-size:14px; margin-bottom:10px;'>Raw text extracted directly from the source documents:</div>", unsafe_allow_html=True)
                    for i, r in enumerate(all_records):
                        fname = r.get("metadata", {}).get("file_name", f"Document {i+1}")
                        with st.expander(f"📄 {fname}", expanded=(i==0)):
                            raw_text = r.get("raw")
                            if raw_text and str(raw_text).strip():
                                st.text_area("Content", value=raw_text, height=300, disabled=True, label_visibility="collapsed", key=f"raw_{i}")
                            else:
                                show_alert(f"No text extracted from **{fname}**. If this is a scanned PDF, ensure Tesseract/Poppler are installed on your OS for OCR.", "warning")
                
                
                st.divider()
                st.markdown("#### 💾 Export Artifacts")
                
                ex1, ex2, ex3 = st.columns(3)
                
                # Unified JSON
                json_str = json.dumps(all_records, indent=2)
                ex1.download_button("📥 JSON", data=json_str, file_name="batch_extraction.json", mime="application/json", use_container_width=True)
                
                # Unified CSV
                df_all = records_to_dataframe(all_records)
                csv_str = df_all.to_csv(index=False)
                ex2.download_button("📥 CSV", data=csv_str, file_name="batch_extraction.csv", mime="text/csv", use_container_width=True)
                
                # Unified LLM Dataset
                all_llm = []
                for r in success_results:
                    lp = r.get("output_paths", {}).get("llm")
                    if lp and Path(lp).exists():
                        try:
                            with open(lp, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                if isinstance(data, list):
                                    all_llm.extend(data)
                                else:
                                    all_llm.append(data)
                        except Exception:
                            pass
                            
                if all_llm:
                    llm_str = json.dumps(all_llm, indent=2)
                    ex3.download_button("📥 LLM Dataset", data=llm_str, file_name="batch_llm_dataset.json", mime="application/json", use_container_width=True)
    else:
        st.info("ℹ️ Pipeline idle. Please submit an extraction job from the Input tab.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB: LOGS
# ─────────────────────────────────────────────────────────────────────────────
with tab_logs:
    if st.session_state.get("run_complete") and st.session_state.get("results"):
        with st.container(border=True):
            st.markdown("<h4 style='margin-top:0;'>🌲 Raw JSON Node Tree</h4>", unsafe_allow_html=True)
            with st.expander("Expand to view raw JSON stream", expanded=False):
                st.json(all_records[:50] if 'all_records' in locals() and all_records else {})

    with st.container(border=True):
        st.markdown("<h4 style='margin-top:0;'>🖥️ Internal Terminal Traces</h4>", unsafe_allow_html=True)
        log_path = os.path.join(PROJECT_ROOT, "output", "pipeline.log")
        if Path(log_path).exists():
            try:
                with st.expander("Expand execution pipeline logs", expanded=True):
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        st.code("".join(f.readlines()[-200:]), language="log")
            except Exception as e:
                show_alert(f"Log retrieval failed: {e}", "warning")
        else:
            st.write("No execution logs found yet.")
