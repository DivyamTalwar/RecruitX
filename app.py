import streamlit as st
from utils import (
    ingest_inputs,
    parse_job_description,
    parse_resumes,
    score_candidates,
    rank_candidates,
    generate_email_templates,
)

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="RecruitX - AI-Powered Hiring",
    page_icon="✨",
    layout="wide",
)

# --- 2. Custom CSS for a Stunning, Professional UI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap');

    /* --- Universal Styles --- */
    html, body, [class*="st-"], .st-emotion-cache-1r4qj8v {
        font-family: 'Manrope', sans-serif;
    }
    .stApp {
        background-color: #0F172A; /* Deep Slate Blue */
        color: #E2E8F0; /* Light Slate Gray for text */
    }

    /* --- Animation --- */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .main-container {
        animation: fadeIn 1s ease-out;
    }

    /* --- Main Header --- */
    .header-container {
        text-align: center;
        padding: 2rem 0;
    }
    .header-container h1 {
        font-size: 3.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #38BDF8, #007BFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -2px;
    }
    .header-container p {
        font-size: 1.15rem;
        color: #94A3B8; /* Medium Slate Gray */
        max-width: 700px;
        margin: 1rem auto 0;
    }

    /* --- Custom Card Component --- */
    .custom-card {
        background-color: #1E293B; /* Darker Slate */
        border: 1px solid #334155; /* Slate Border */
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .custom-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 20px rgba(0, 0, 0, 0.15);
    }

    /* --- Widget Styling --- */
    .stTextArea, .stFileUploader, .stSlider {
        margin-bottom: 1rem;
    }
    .stTextArea label, .stFileUploader label, .stSlider label {
        color: #CBD5E1 !important; /* Lighter Slate */
        font-weight: 600;
        font-size: 1.1rem;
    }

    /* --- Main Action Button --- */
    .stButton>button {
        background: linear-gradient(90deg, #007BFF, #38BDF8);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 12px 28px;
        font-weight: 700;
        font-size: 1.1rem;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 123, 255, 0.2);
    }
    .stButton>button:hover {
        transform: scale(1.03);
        box-shadow: 0 6px 20px rgba(0, 123, 255, 0.3);
    }

    /* --- Results Section --- */
    .results-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #F8FAFC; /* Almost White */
        text-align: center;
        margin: 3rem 0 2rem 0;
    }

    /* --- Candidate Card Specifics --- */
    .candidate-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
    }
    .candidate-name {
        font-size: 1.6rem;
        font-weight: 700;
        color: #F1F5F9;
    }
    .candidate-rank {
        font-size: 1rem;
        font-weight: 600;
        color: #0F172A;
        background-color: #38BDF8;
        padding: 6px 14px;
        border-radius: 20px;
    }
    .ai-summary {
        font-style: italic;
        color: #CBD5E1;
        background-color: rgba(0,0,0,0.15);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #007BFF;
        margin-top: 1rem;
    }

    /* --- Radial Progress Bar for Scores --- */
    .progress-circle {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        background: conic-gradient(#007BFF var(--progress-value), #334155 0);
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        margin: auto;
    }
    .progress-circle::before {
        content: '';
        position: absolute;
        width: 80px;
        height: 80px;
        background: #1E293B;
        border-radius: 50%;
    }
    .progress-text {
        position: relative;
        font-size: 1.8rem;
        font-weight: 700;
        color: #F1F5F9;
    }
    .progress-label {
        text-align: center;
        margin-top: 0.5rem;
        color: #94A3B8;
        font-weight: 600;
    }

    /* --- Email Section --- */
    .email-section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #E2E8F0;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #334155;
    }
    .email-card .stTextArea label { color: #E2E8F0 !important; }

</style>
""", unsafe_allow_html=True)

# --- 3. App Layout ---

# Use a main container for centered content and animations
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div class="header-container">
    <h1>RecruitX</h1>
    <p>The future of recruitment is here. Leverage cutting-edge AI to identify, rank, and engage top-tier talent in seconds, not weeks.</p>
</div>
""", unsafe_allow_html=True)

# --- Input Section ---
with st.container():
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    st.markdown("<h3><span style='color:#94A3B8;'>Step 1:</span> Provide Your Requirements</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 2])
    with col1:
        job_description = st.text_area(
            "📄 **Job Description**", 
            placeholder="Paste the entire job description here for a detailed analysis...", 
            height=300
        )
    with col2:
        resume_files = st.file_uploader(
            "👥 **Upload Candidate Resumes**",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload multiple text-based PDF resumes. Scanned images are not supported."
        )
        num_candidates = st.slider(
            "🎯 **Top Candidates to Invite**", 
            min_value=1, 
            max_value=min(10, len(resume_files) if resume_files else 10), 
            value=min(3, len(resume_files) if resume_files else 3),
            help="Select how many top-ranked candidates to generate interview invitations for."
        )
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Action Button ---
if st.button("🚀 Analyze and Rank Candidates", type="primary"):
    # Input validation
    if not job_description.strip():
        st.error("⚠️ Please provide a job description to begin the analysis.")
    elif not resume_files:
        st.error("⚠️ Please upload at least one resume to screen.")
    else:
        try:
            # Modern progress indicator
            with st.status("RecruitX AI is on the job...", expanded=True) as status:
                status.update(label="Phase 1: Ingesting and understanding your data...", state="running")
                raw_data = ingest_inputs(job_description, resume_files)
                
                status.update(label="Phase 2: Parsing job description and resumes with high precision...", state="running")
                parsed_job_desc = parse_job_description(raw_data["job_description"])
                parsed_resumes_data = parse_resumes(raw_data["resume_files"])
                
                if all('error' in res for res in parsed_resumes_data.get("parsed_resumes", [])):
                    status.update(label="Critical Error", state="error", expanded=True)
                    st.error("Fatal Error: ALL resumes failed to process. Ensure they are text-readable PDFs and not scanned images.")
                    st.stop()
                
                status.update(label="Phase 3: Scoring each candidate against key metrics...", state="running")
                candidate_scores = score_candidates(parsed_job_desc, parsed_resumes_data)
                
                status.update(label="Phase 4: Ranking candidates to find the top talent...", state="running")
                ranked_candidates = rank_candidates(candidate_scores)
                
                status.update(label="Phase 5: Crafting personalized email drafts...", state="running")
                email_templates = generate_email_templates(ranked_candidates, parsed_job_desc, num_candidates)
                
                status.update(label="✅ Analysis Complete!", state="complete", expanded=False)

            # --- Results Display ---
            st.markdown('<h2 class="results-header">🏆 Candidate Leaderboard</h2>', unsafe_allow_html=True)
            
            for i, candidate in enumerate(ranked_candidates):
                if "Error Processing" in candidate.get("name", ""):
                    st.warning(f"Skipped a file due to a processing error: {candidate.get('comment')}")
                    continue
                
                with st.container():
                    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="candidate-card-header">
                        <div class="candidate-name">{candidate.get('name', 'N/A')}</div>
                        <div class="candidate-rank">Rank #{i+1}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    score_col1, score_col2 = st.columns([1, 2])
                    with score_col1:
                        overall_score = candidate.get('overall', 0)
                        st.markdown(f"""
                        <div class="progress-circle" style="--progress-value: {overall_score}%">
                            <div class="progress-text">{overall_score}%</div>
                        </div>
                        <div class="progress-label">Overall Fit</div>
                        """, unsafe_allow_html=True)
                    
                    with score_col2:
                        st.markdown(f"<div class='ai-summary'><strong>AI Assessment:</strong> {candidate.get('comment', 'No comment available.')}</div>", unsafe_allow_html=True)
                    
                    with st.expander("View Detailed Score Breakdown"):
                        st.json(candidate)
                    
                    st.markdown('</div>', unsafe_allow_html=True)

            # --- Email Section ---
            st.markdown('<h2 class="results-header">✉️ Communication Center</h2>', unsafe_allow_html=True)
            email_col1, email_col2 = st.columns(2)
            
            with email_col1:
                st.markdown('<div class="custom-card email-card">', unsafe_allow_html=True)
                st.markdown('<h3 class="email-section-header">✅ Interview Invitations</h3>', unsafe_allow_html=True)
                if email_templates["invitations"]:
                    for email in email_templates["invitations"]:
                        st.text_area(f"To: {email['name']}", value=email['email_body'], height=250, key=f"invite_{email['name']}", label_visibility="visible")
                else:
                    st.info("No candidates were selected for invitations.")
                st.markdown('</div>', unsafe_allow_html=True)

            with email_col2:
                st.markdown('<div class="custom-card email-card">', unsafe_allow_html=True)
                st.markdown('<h3 class="email-section-header">❌ Polite Rejections</h3>', unsafe_allow_html=True)
                if email_templates["rejections"]:
                    for email in email_templates["rejections"]:
                        st.text_area(f"To: {email['name']}", value=email['email_body'], height=250, key=f"reject_{email['name']}", label_visibility="visible")
                else:
                    st.info("No candidates to send rejection emails to.")
                st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"An unexpected system error occurred: {e}")

st.markdown('</div>', unsafe_allow_html=True)