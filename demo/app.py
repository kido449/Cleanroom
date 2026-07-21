import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List
import streamlit as st

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set page configuration before any other Streamlit call
st.set_page_config(
    page_title="Cleanroom Structured Extraction Demo",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern glassmorphism, badges, and typography
st.markdown("""
<style>
    /* Main container styling */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    
    /* Header card */
    .header-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    .header-title {
        font-size: 2rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0 0 0.5rem 0;
    }
    .header-subtitle {
        font-size: 1.05rem;
        color: #94a3b8;
        margin: 0;
    }
    
    /* Status Badges */
    .badge-success {
        display: inline-block;
        padding: 0.5rem 1.2rem;
        border-radius: 9999px;
        background-color: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid #10b981;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 1rem;
    }
    .badge-flagged {
        display: inline-block;
        padding: 0.5rem 1.2rem;
        border-radius: 9999px;
        background-color: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid #ef4444;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 1rem;
    }
    .badge-error {
        display: inline-block;
        padding: 0.5rem 1.2rem;
        border-radius: 9999px;
        background-color: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
        border: 1px solid #f59e0b;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# Lazy import of extraction pipeline to prevent slowdown on page load
@st.cache_resource
def get_extractor():
    from src.extractor import GroqExtractor
    return GroqExtractor()


def load_eval_summary() -> Dict[str, Any]:
    summary_path = project_root / "eval" / "results" / "eval_summary.json"
    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {}
    return {}


def get_ticket_files() -> List[str]:
    raw_dir = project_root / "data" / "raw"
    if raw_dir.exists():
        files = sorted(list(raw_dir.glob("*.txt")))
        return [f.name for f in files]
    return []


# ============================================
# SIDEBAR: Observability & Pipeline Stats
# ============================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
    st.title("📊 Pipeline Stats")
    st.markdown("Global metrics pulled from `eval/results/eval_summary.json`.")
    
    summary = load_eval_summary()
    if summary:
        total_eval = summary.get("total_tickets_processed", 0)
        success_count = summary.get("success_count", 0)
        rate = summary.get("schema_valid_success_rate_percent", 0.0)
        meets_sla = summary.get("meets_90_percent_requirement", False)
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.metric("Total Evaluated", total_eval)
        with col_s2:
            st.metric("Success Rate", f"{rate:.1f}%")
            
        st.metric(
            "Meets >90% SLA Requirement",
            "✅ YES" if meets_sla else "❌ NO",
            delta=f"{rate - 90.0:+.1f}% vs target"
        )
        
        st.divider()
        st.subheader("Attempts Distribution")
        attempts_breakdown = summary.get("success_by_attempt", {})
        st.markdown(f"""
        - **Attempt 1 (Direct)**: `{attempts_breakdown.get('attempt_1', 0)}`
        - **Attempt 2 (Repaired)**: `{attempts_breakdown.get('attempt_2', 0)}`
        - **Attempt 3 (Repaired)**: `{attempts_breakdown.get('attempt_3', 0)}`
        """)
        
        flagged = summary.get("flagged_for_review_count", 0)
        if flagged > 0:
            st.error(f"⚠️ Flagged Tickets: {flagged}")
    else:
        st.info("ℹ️ No summary report found yet. Run `python src/eval/run_eval.py` to generate evaluation metrics.")


# ============================================
# MAIN PAGE HEADER & TABS
# ============================================
st.markdown("""
<div class="header-card">
    <div class="header-title">🤖 Cleanroom Extraction & Self-Repair Demo</div>
    <div class="header-subtitle">
        Transform messy, noisy customer support tickets into strictly validated Pydantic models (<code>ExtractedDocument</code>) with an automated LLM feedback and repair loop using Groq (<code>llama-3.3-70b-versatile</code>).
    </div>
</div>
""", unsafe_allow_html=True)

tab_live, tab_hitl = st.tabs(["🚀 Live Extraction & Self-Repair", "🧑‍💻 HITL Review Queue Dashboard"])


# ============================================
# TAB 1: LIVE EXTRACTION & SELF-REPAIR
# ============================================
with tab_live:
    ticket_files = get_ticket_files()
    dropdown_options = ["Custom Input (Type or paste text below)"] + ticket_files

    col_input, col_config = st.columns([3, 1])

    with col_config:
        selected_option = st.selectbox(
            "📂 Load Benchmark Example",
            options=dropdown_options,
            index=0,
            help="Choose one of the 55 benchmark tickets from data/raw/ or choose Custom Input."
        )
        max_retries_ui = st.slider("Max Self-Repair Attempts", min_value=1, max_value=5, value=3)

    # Handle text population when dropdown changes
    if selected_option != "Custom Input (Type or paste text below)":
        file_path = project_root / "data" / "raw" / selected_option
        default_text = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    else:
        default_text = "Subject: URGENT Can't login!! charged twice on pro tier!!\n\nHi support, my name is John Smith (john@example.com). Since 2pm today I cannot log into my dashboard, it shows Error 404. Also I noticed on my credit card that you billed me twice for my Pro tier subscription! Plz fix this right away!"

    with col_input:
        raw_text = st.text_area(
            "📝 Support Ticket Raw Text",
            value=default_text,
            height=180,
            placeholder="Paste noisy email, live chat transcript, or crash report here..."
        )

    st.write("")
    extract_btn = st.button("🚀 Run Extraction & Self-Repair Pipeline", type="primary", use_container_width=True)

    if extract_btn:
        if not raw_text.strip():
            st.warning("⚠️ Please provide some input text before running extraction.")
        else:
            from src.extraction.pipeline import extract_with_repair
            
            with st.spinner("🤖 Invoking Groq API (llama-3.3-70b-versatile) & running Pydantic validation checks..."):
                try:
                    extractor = get_extractor()
                    result = extract_with_repair(raw_text, max_retries=max_retries_ui, extractor=extractor)
                except Exception as e:
                    st.error(f"❌ Unhandled System/API Exception during extraction: {e}")
                    st.stop()
                    
            status = result.get("status", "unknown")
            attempts = result.get("attempts", 1)
            errors_encountered = result.get("errors_encountered", [])
            last_errors = result.get("last_errors", [])
            extracted_json = result.get("data") if status == "success" else result.get("last_attempt_json")
            
            st.divider()
            
            # Status Badge & Metrics Row
            if status == "success":
                st.markdown('<div class="badge-success">✅ STATUS: SUCCESS (SCHEMA VALID)</div>', unsafe_allow_html=True)
            elif status == "flagged_for_review":
                st.markdown('<div class="badge-flagged">⚠️ STATUS: FLAGGED FOR HUMAN REVIEW</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="badge-error">❌ STATUS: {status.upper()}</div>', unsafe_allow_html=True)
                
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Total Attempts Taken", f"{attempts} / {max_retries_ui}")
            with m2:
                st.metric("Self-Correction Retries", f"{len(errors_encountered)}")
            with m3:
                st.metric("Schema Adherence", "100% Valid" if status == "success" else "Validation Failed")
                
            # Self-Correction History Expander
            if errors_encountered:
                with st.expander("🛠️ Self-Correction History (Errors Caught & Repaired by Pipeline)", expanded=True):
                    st.markdown("The pipeline detected Pydantic validation errors during earlier attempts and fed exact error feedback to Groq (`llama-3.3-70b-versatile`) to self-correct:")
                    for idx, err_list in enumerate(errors_encountered, 1):
                        st.markdown(f"**Attempt {idx} Validation Failures Encountered:**")
                        for err in err_list:
                            st.markdown(f"- `❌ {err}`")
                        if idx < attempts or status == "success":
                            st.markdown("`-> Sent CORRECTION prompt with exact locator feedback to re-extract.`")
                        st.divider()
                        
            # Flagged Details
            if status == "flagged_for_review" and last_errors:
                st.error(f"❌ Ticket remained invalid after maximum self-repair retries and has been added to the HITL Review Queue (Queue ID: `{result.get('queue_id', 'N/A')}`). Unresolved errors:")
                for err in last_errors:
                    st.markdown(f"- `{err}`")
                    
            # Final JSON Output
            st.subheader("📋 Extracted Structured Document JSON")
            if extracted_json:
                st.json(extracted_json)
            else:
                st.write("No JSON payload produced.")


# ============================================
# TAB 2: HITL REVIEW QUEUE DASHBOARD
# ============================================
with tab_hitl:
    from src.hitl.queue import get_pending_reviews, resolve_review, dismiss_review
    
    st.header("🧑‍💻 Human-In-The-Loop (HITL) Review Queue")
    st.markdown("Inspect and resolve extractions that failed automated schema validation after `max_retries` attempts.")
    
    pending_items = get_pending_reviews()
    if not pending_items:
        st.success("🎉 No items currently pending review! All processed extractions conform 100% to the Pydantic schema.")
    else:
        st.warning(f"⚠️ There are `{len(pending_items)}` item(s) awaiting human inspection and resolution.")
        
        for idx, item in enumerate(pending_items, 1):
            qid = item.get("queue_id", f"item-{idx}")
            tid = item.get("ticket_id", "N/A")
            attempts_taken = item.get("attempts_taken", 3)
            created_at = item.get("created_at", "")[:19].replace("T", " ")
            raw_t = item.get("raw_text", "")
            last_errs = item.get("last_errors", [])
            last_j = item.get("last_attempt_json", {})
            
            with st.expander(f"🔴 [{qid}] Ticket: {tid} (Failed after {attempts_taken} attempts | Created: {created_at})", expanded=(idx==1)):
                st.markdown("**❌ Unresolved Schema Validation Errors:**")
                for e in last_errs:
                    st.markdown(f"- `{e}`")
                    
                col_raw, col_json = st.columns(2)
                with col_raw:
                    st.subheader("📝 Original Raw Text")
                    st.text_area("Raw input text", value=raw_t, height=250, key=f"raw_{qid}", disabled=True)
                    
                with col_json:
                    st.subheader("🛠️ Editable JSON Correction")
                    json_str_init = json.dumps(last_j, indent=2, ensure_ascii=False) if isinstance(last_j, (dict, list)) else "{}"
                    edited_json_str = st.text_area(
                        "Edit JSON to satisfy ExtractedDocument schema:",
                        value=json_str_init,
                        height=250,
                        key=f"edit_json_{qid}"
                    )
                    
                notes = st.text_input("Reviewer Notes / Rationale (Optional):", key=f"notes_{qid}", placeholder="e.g. Corrected invalid account tier enum.")
                
                b_col1, b_col2, b_col3 = st.columns([2, 1, 3])
                with b_col1:
                    if st.button("✅ Verify & Resolve Ticket", key=f"resolve_{qid}", type="primary", use_container_width=True):
                        try:
                            parsed_corrected = json.loads(edited_json_str)
                            success, val_errors = resolve_review(qid, parsed_corrected, reviewer_notes=notes)
                            if success:
                                st.success(f"Ticket {tid} resolved and validated successfully!")
                                st.rerun()
                            else:
                                st.error(f"Validation failed: {val_errors}")
                        except json.JSONDecodeError as je:
                            st.error(f"Invalid JSON syntax: {je}")
                            
                with b_col2:
                    if st.button("🗑️ Dismiss", key=f"dismiss_{qid}", use_container_width=True):
                        dismiss_review(qid, reason=notes or "Dismissed by operator")
                        st.success("Review item dismissed.")
                        st.rerun()

