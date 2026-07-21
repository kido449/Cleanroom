import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List
import streamlit as st

# Ensure project root is in sys.path and load .env explicitly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv, find_dotenv
load_dotenv(project_root / ".env", override=True)
load_dotenv(find_dotenv(), override=True)

# Set page configuration before any other Streamlit call
st.set_page_config(
    page_title="Cleanroom Structured Extraction Demo",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Red Noir style (inspired by reference implementation)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Manrope:wght@400;600;700;800&display=swap');

    :root {
        --accent-red: #ef233c;
        --accent-red-glow: rgba(239, 35, 60, 0.5);
    }

    /* Global typography and dark background */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
        background: linear-gradient(180deg, #1a0505 0%, #080202 35%, #000000 100%) !important;
        color: #f8fafc !important;
    }

    h1, h2, h3, h4, h5, h6, .header-title {
        font-family: 'Manrope', sans-serif !important;
        letter-spacing: -0.025em !important;
    }

    /* Selection highlight */
    ::selection {
        background: #ef233c !important;
        color: white !important;
    }

    /* Main container styling */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1250px !important;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: #060101 !important;
        border-right: 1px solid rgba(239, 35, 60, 0.15) !important;
    }

    /* Calmer Engineering-Credible Header Card */
    @keyframes subtleGlowDrift {
        0% { transform: translate(0, 0) scale(1); }
        50% { transform: translate(-25px, 15px) scale(1.06); }
        100% { transform: translate(0, 0) scale(1); }
    }

    .header-card {
        position: relative;
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 20px;
        padding: 2.2rem 2.5rem;
        margin-bottom: 2.5rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.7), inset 0 1px 1px rgba(255, 255, 255, 0.05);
        overflow: hidden;
    }

    .header-card::after {
        content: '';
        position: absolute;
        top: -25%;
        right: -8%;
        width: 450px;
        height: 450px;
        background: radial-gradient(circle, rgba(239, 35, 60, 0.13) 0%, transparent 70%);
        pointer-events: none;
        border-radius: 50%;
        filter: blur(55px);
        z-index: 0;
        animation: subtleGlowDrift 16s ease-in-out infinite;
    }

    .header-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 9999px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 1.2rem;
        backdrop-filter: blur(8px);
        position: relative;
        z-index: 1;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 8px #10b981;
        display: inline-block;
        animation: pulse-green 2s infinite;
    }

    @keyframes pulse-green {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    .pill-text {
        font-size: 0.75rem;
        font-weight: 600;
        color: #cbd5e1;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        font-family: 'Manrope', sans-serif;
    }

    .header-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0 0 0.8rem 0;
        line-height: 1.15;
    }

    .text-red {
        color: #ef233c;
        text-shadow: 0 0 20px rgba(239, 35, 60, 0.4);
    }

    .header-subtitle {
        font-size: 1.08rem;
        color: #a1a1aa;
        line-height: 1.6;
        max-width: 900px;
        font-weight: 300;
    }

    .header-subtitle code {
        background: rgba(239, 35, 60, 0.15);
        color: #ff808b;
        padding: 2px 8px;
        border-radius: 6px;
        border: 1px solid rgba(239, 35, 60, 0.3);
        font-size: 0.9em;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.03) !important;
        border-radius: 9999px !important;
        padding: 6px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        gap: 8px !important;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 9999px !important;
        color: #a1a1aa !important;
        padding: 10px 24px !important;
        font-family: 'Manrope', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(239, 35, 60, 0.2) 0%, rgba(239, 35, 60, 0.05) 100%) !important;
        color: #ffffff !important;
        border: 1px solid #ef233c !important;
        box-shadow: 0 0 20px rgba(239, 35, 60, 0.3) !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* Buttons & Shiny CTA */
    div.stButton > button[kind="primaryButton"], div.stButton > button:first-child {
        background: linear-gradient(135deg, #ef233c 0%, #b81428 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 9999px !important;
        padding: 0.75rem 2rem !important;
        font-family: 'Manrope', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        box-shadow: 0 0 25px rgba(239, 35, 60, 0.4) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    div.stButton > button[kind="primaryButton"]:hover, div.stButton > button:first-child:hover {
        box-shadow: 0 0 35px rgba(239, 35, 60, 0.8) !important;
        transform: translateY(-2px) !important;
        border-color: rgba(255, 255, 255, 0.4) !important;
    }

    div.stButton > button[kind="secondaryButton"] {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #f8fafc !important;
        border-radius: 9999px !important;
        font-family: 'Manrope', sans-serif !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    div.stButton > button[kind="secondaryButton"]:hover {
        border-color: #ef233c !important;
        color: #ef233c !important;
        background: rgba(239, 35, 60, 0.1) !important;
        box-shadow: 0 0 15px rgba(239, 35, 60, 0.2) !important;
    }

    /* Status Badges */
    .badge-success {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 0.6rem 1.4rem;
        border-radius: 9999px;
        background: rgba(16, 185, 129, 0.1);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.4);
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
        font-weight: 700;
        font-size: 0.95rem;
        font-family: 'Manrope', sans-serif;
        margin-bottom: 1.2rem;
    }
    .badge-flagged {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 0.6rem 1.4rem;
        border-radius: 9999px;
        background: rgba(239, 35, 60, 0.15);
        color: #ff6b7a;
        border: 1px solid #ef233c;
        box-shadow: 0 0 25px rgba(239, 35, 60, 0.4);
        font-weight: 700;
        font-size: 0.95rem;
        font-family: 'Manrope', sans-serif;
        margin-bottom: 1.2rem;
    }
    .badge-error {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 0.6rem 1.4rem;
        border-radius: 9999px;
        background: rgba(245, 158, 11, 0.1);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.4);
        box-shadow: 0 0 20px rgba(245, 158, 11, 0.2);
        font-weight: 700;
        font-size: 0.95rem;
        font-family: 'Manrope', sans-serif;
        margin-bottom: 1.2rem;
    }

    /* Metric Cards (Bento Style) */
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(24, 24, 27, 0.6) 0%, rgba(9, 9, 11, 0.8) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 1.2rem 1.4rem !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
        transition: all 0.3s ease !important;
    }

    div[data-testid="stMetric"]:hover {
        border-color: rgba(239, 35, 60, 0.4) !important;
        box-shadow: 0 0 25px rgba(239, 35, 60, 0.15) !important;
        transform: translateY(-2px) !important;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'Manrope', sans-serif !important;
        font-weight: 800 !important;
        color: #ffffff !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #a1a1aa !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        font-weight: 600 !important;
    }

    /* Expanders & Cards */
    div[data-testid="stExpander"] {
        background: rgba(15, 15, 18, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        overflow: hidden !important;
        transition: border-color 0.2s ease !important;
    }

    div[data-testid="stExpander"]:hover {
        border-color: rgba(239, 35, 60, 0.3) !important;
    }

    /* Input boxes & Select boxes */
    div[data-baseweb="select"] > div, textarea, input {
        background-color: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        color: #ffffff !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
    }

    div[data-baseweb="select"] > div:focus-within, textarea:focus, input:focus {
        border-color: #ef233c !important;
        box-shadow: 0 0 15px rgba(239, 35, 60, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)


# Lazy import of extraction pipeline to prevent slowdown on page load
@st.cache_resource
def get_extractor():
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(project_root / ".env", override=True)
    load_dotenv(find_dotenv(), override=True)
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
    st.markdown("""
    <div style="display: flex; items-center; gap: 10px; margin-bottom: 1rem;">
        <div style="width: 18px; height: 18px; background: #ef233c; border-radius: 3px; transform: rotate(45deg); flex-shrink: 0; box-shadow: 0 0 10px rgba(239, 35, 60, 0.6);"></div>
        <span style="font-size: 1.35rem; font-weight: 800; font-family: 'Manrope', sans-serif; letter-spacing: -0.02em; color: white;">Superdesign <span style="color: #ef233c;">Stats</span></span>
    </div>
    """, unsafe_allow_html=True)
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

    st.divider()
    st.subheader("🌌 Design Intelligence UI Showcases")
    st.markdown("""
    Experience our custom Red Noir high-speed visual animations in your browser:
    - **[Letter-By-Letter Text Swap CTA](file:///c:/Users/Niraj%20Damai/OneDrive%20-%20Garden%20City%20University/Desktop/Cleanroom/structured-extract/demo/generate_button.html)** (Interactive Tailwind CTA with star icon & staggered letter swap between Generate and Generating)
    - **[Minimalist Aurora Notion Character](file:///c:/Users/Niraj%20Damai/OneDrive%20-%20Garden%20City%20University/Desktop/Cleanroom/structured-extract/demo/aurora_character.html)** (Floating aurora sphere with geometric white vector facial lines & interactive expressions)
    - **[Lens Flare Spotlight Mask Reveal](file:///c:/Users/Niraj%20Damai/OneDrive%20-%20Garden%20City%20University/Desktop/Cleanroom/structured-extract/demo/spotlight_mask.html)** (Scroll-driven circular clip-path reveal expanding from 0% to 150%)
    - **[3D WebGL Hyperspeed Warp](file:///c:/Users/Niraj%20Damai/OneDrive%20-%20Garden%20City%20University/Desktop/Cleanroom/structured-extract/demo/hyperspeed_showcase.html)** (Three.js 60fps warp tunnel with 6 distortion presets & press-and-hold warp)
    - **[2D Character Speeder Showcase](file:///c:/Users/Niraj%20Damai/OneDrive%20-%20Garden%20City%20University/Desktop/Cleanroom/structured-extract/demo/loading_animation.html)** (Character loader with dynamic longfazers & theme toggle)
    """)

# ============================================
# MAIN PAGE HEADER & TABS
# ============================================
st.markdown("""
<div class="header-card">
    <div class="header-pill">
        <span class="pulse-dot"></span>
        <span class="pill-text">SELF-CORRECTING EXTRACTION PIPELINE</span>
    </div>
    <div class="header-title" style="position: relative; z-index: 1;">Cleanroom <span class="text-red">Structured Extraction</span></div>
    <div class="header-subtitle" style="position: relative; z-index: 1;">
        Transform noisy, unstructured support tickets into strictly validated Pydantic models (<code>ExtractedDocument</code>) with an automated LLM feedback & repair loop powered by Groq (<code>llama-3.3-70b-versatile</code>).
    </div>
</div>
""", unsafe_allow_html=True)

st.components.v1.html("""
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
function initHeaderEffects() {
    const parentDoc = window.parent.document;
    const parentWin = window.parent;
    if (!parentDoc) return;

    // 1. TYPING ANIMATION ON HEADER TITLE
    const titleEl = parentDoc.querySelector('.header-title');
    if (titleEl && !titleEl.dataset.typed) {
        titleEl.dataset.typed = "true";
        const fullText = "Cleanroom ";
        const redText = "Structured Extraction";
        titleEl.innerHTML = '';
        
        const baseSpan = parentDoc.createElement('span');
        const redSpan = parentDoc.createElement('span');
        redSpan.className = 'text-red';
        
        const cursor = parentDoc.createElement('span');
        cursor.style.cssText = 'display: inline-block; width: 4px; height: 2.3rem; background-color: #ef233c; margin-left: 6px; vertical-align: -4px; border-radius: 2px; box-shadow: 0 0 8px #ef233c; animation: pulse 1s infinite;';
        
        titleEl.appendChild(baseSpan);
        titleEl.appendChild(redSpan);
        titleEl.appendChild(cursor);
        
        let i = 0;
        function typeChar() {
            if (i < fullText.length) {
                baseSpan.textContent += fullText.charAt(i);
                i++;
                setTimeout(typeChar, 50);
            } else if (i < fullText.length + redText.length) {
                redSpan.textContent += redText.charAt(i - fullText.length);
                i++;
                setTimeout(typeChar, 50);
            }
        }
        typeChar();
    }
}

initHeaderEffects();
setTimeout(initHeaderEffects, 500);
setTimeout(initHeaderEffects, 1200);
</script>
""", height=0)

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

