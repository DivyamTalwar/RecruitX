import streamlit as st
import pandas as pd
from utils import (
    ingest_inputs,
    parse_job_description,
    parse_resumes,
    score_candidates,
    rank_candidates,
    generate_email_templates,
)

# --- Page Configuration ---
st.set_page_config(
    page_title="VisionaryHire AI Screener",
    page_icon="🔮",
    layout="wide",
)

# --- Custom CSS for the "Sexy" UI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

    /* --- General Styling --- */
    html, body, [class*="st-"] {
        font-family: 'Poppins', sans-serif;
    }

    .stApp {
        background-color: #0c001f;
        background-image: radial-gradient(circle at top right, #4a00e0, transparent 40%),
                          radial-gradient(circle at bottom left, #8e2de2, transparent 40%);
        background-attachment: fixed;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .main-container {
        animation: fadeIn 0.8s ease-in-out;
    }
    
    /* --- Main Title --- */
    .title {
        text-align: center;
        padding: 2rem 0;
    }
    .title h1 {
        font-size: 3.5rem;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #8e2de2, #4a00e0, #8e2de2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -2px;
    }
    .title p {
        color: #d1c4e9;
        font-size: 1.1rem;
        max-width: 600px;
        margin: 0 auto;
    }

    /* --- Glassmorphism Card Effect --- */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem;
        color: white;
        transition: all 0.3s ease;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }
    .glass-card:hover {
        background: rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(74, 0, 224, 0.3);
    }

    /* --- Custom Widget Styling --- */
    .stTextArea, .stFileUploader, .stSlider {
        margin-bottom: 1.5rem;
    }
    .stTextArea label, .stFileUploader label, .stSlider label {
        color: #d1c4e9 !important;
        font-weight: 600;
        font-size: 1.1rem;
    }
    
    /* Main Action Button */
    .stButton>button {
        background: linear-gradient(45deg, #8e2de2, #4a00e0);
        color: white;
        border-radius: 12px;
        border: none;
        padding: 15px 30px;
        font-weight: 700;
        font-size: 1.2rem;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(142, 45, 226, 0.4);
    }
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(142, 45, 226, 0.6);
    }
    
    /* --- Results Display Styling --- */
    .results-header {
        text-align: center;
        color: #f3e5f5;
        font-size: 2.5rem;
        font-weight: 600;
        margin: 3rem 0 1rem 0;
    }
    
    .candidate-card {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .candidate-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .candidate-name {
        font-size: 1.8rem;
        font-weight: 700;
        color: #e1bee7;
    }
    
    .candidate-rank {
        font-size: 1.2rem;
        font-weight: 600;
        color: #4a00e0;
        background-color: #d1c4e9;
        padding: 5px 15px;
        border-radius: 20px;
    }
    
    .score-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
        gap: 1rem;
        text-align: center;
    }
    
    .score-item {
        background-color: rgba(0,0,0,0.2);
        padding: 1rem;
        border-radius: 12px;
    }
    
    .score-label {
        font-size: 0.9rem;
        color: #d1c4e9;
        margin-bottom: 0.5rem;
    }
    
    .score-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
    }

    .ai-comment {
        font-style: italic;
        color: #e0e0e0;
        background-color: rgba(0,0,0,0.2);
        padding: 1rem;
        border-radius: 12px;
        border-left: 3px solid #8e2de2;
    }
    
    /* Email Section */
    .email-section-header {
        font-size: 1.5rem;
        color: #e1bee7;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #4a00e0;
    }
    .email-card {
        margin-bottom: 1.5rem;
        padding: 1.5rem;
    }
    .email-card .stTextArea label {
        color: #e1bee7 !important;
        font-size: 1rem;
    }

</style>
""", unsafe_allow_html=True)


# --- UI Layout ---

st.markdown('<div class="main-container">', unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div class="title">
    <h1>🔮 VisionaryHire AI</h1>
    <p>Unleash the power of AI to instantly screen, rank, and connect with the perfect candidates. Your intelligent hiring partner is here.</p>
</div>
""", unsafe_allow_html=True)

# --- Input Section ---
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.header("1. Configure Your Screening")
col1, col2 = st.columns([2, 1])

with col1:
    job_description = st.text_area(
        "📝 Job Description", 
        placeholder="Paste the full job description here...", 
        height=300
    )
with col2:
    resume_files = st.file_uploader(
        "📄 Upload Resumes (PDF)",
        type=["pdf"],
        accept_multiple_files=True
    )
    num_candidates = st.slider(
        "🎯 Number to Invite", 
        min_value=1, 
        max_value=10, 
        value=3,
        help="Select the top candidates for whom you want to generate interview invitations."
    )
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Agent Execution ---
if st.button("✨ Launch AI Screening", type="primary"):
    if not job_description.strip():
        st.error("⚠️ The job description cannot be empty. Please paste the details.")
    elif not resume_files:
        st.error("⚠️ No resumes uploaded. Please upload at least one PDF file.")
    else:
        try:
            with st.spinner("🤖 The AI is analyzing... Please wait..."):
                # All backend logic is encapsulated here
                raw_data = ingest_inputs(job_description, resume_files)
                parsed_job_desc = parse_job_description(raw_data["job_description"])
                parsed_resumes_data = parse_resumes(raw_data["resume_files"])
                
                if all('error' in res for res in parsed_resumes_data["parsed_resumes"]):
                    st.error("Fatal Error: ALL resumes failed to process. Please check your PDF files (must be text-readable, not scanned images) and try again.")
                    st.stop()
                
                candidate_scores = score_candidates(parsed_job_desc, parsed_resumes_data)
                ranked_candidates = rank_candidates(candidate_scores)
                email_templates = generate_email_templates(ranked_candidates, parsed_job_desc, num_candidates)

            # --- Results Display ---
            st.markdown('<h2 class="results-header">🏆 Screening Results</h2>', unsafe_allow_html=True)
            
            # Display Ranked Candidates
            for i, candidate in enumerate(ranked_candidates):
                if "Error Processing" in candidate.get("name", ""):
                    st.error(f"Could not process file: {candidate.get('comment')}")
                    continue
                
                with st.container():
                    st.markdown('<div class="glass-card candidate-card">', unsafe_allow_html=True)
                    
                    # Header: Name and Rank
                    st.markdown(f"""
                    <div class="candidate-header">
                        <div class="candidate-name">{candidate.get('name', 'N/A')}</div>
                        <div class="candidate-rank">Rank #{i+1}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Scores
                    col_score1, col_score2, col_score3, col_score4 = st.columns(4)
                    with col_score1:
                        st.markdown(f"""
                        <div class="score-item">
                            <div class="score-label">Overall Fit</div>
                            <div class="score-value">{candidate.get('overall', 0)}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_score2:
                        st.markdown(f"""
                        <div class="score-item">
                            <div class="score-label">Relevance</div>
                            <div class="score-value">{candidate.get('relevance', 0)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_score3:
                        st.markdown(f"""
                        <div class="score-item">
                            <div class="score-label">Experience</div>
                            <div class="score-value">{candidate.get('experience', 0)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_score4:
                        st.markdown(f"""
                        <div class="score-item">
                            <div class="score-label">Skills</div>
                            <div class="score-value">{candidate.get('skills', 0)}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    # AI Comment
                    st.markdown(f"<div class='ai-comment'><strong>AI Summary:</strong> {candidate.get('comment', 'No comment available.')}</div>", unsafe_allow_html=True)
                    
                    # Expander for full details
                    with st.expander("Show Full Analysis (JSON)"):
                        st.json(candidate)
                    
                    st.markdown('</div>', unsafe_allow_html=True)


            # Display Email Templates
            st.markdown('<h2 class="results-header">✉️ Email Drafts</h2>', unsafe_allow_html=True)
            
            email_col1, email_col2 = st.columns(2)
            
            with email_col1:
                st.markdown('<h3 class="email-section-header">✅ Invitations</h3>', unsafe_allow_html=True)
                if email_templates["invitations"]:
                    for email in email_templates["invitations"]:
                        st.markdown('<div class="glass-card email-card">', unsafe_allow_html=True)
                        st.text_area(f"To: {email['name']}", value=email['email_body'], height=250, key=f"invite_{email['name']}")
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("No candidates met the criteria for an invitation.")

            with email_col2:
                st.markdown('<h3 class="email-section-header">❌ Rejections</h3>', unsafe_allow_html=True)
                if email_templates["rejections"]:
                    for email in email_templates["rejections"]:
                        st.markdown('<div class="glass-card email-card">', unsafe_allow_html=True)
                        st.text_area(f"To: {email['name']}", value=email['email_body'], height=250, key=f"reject_{email['name']}")
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.info("No candidates to reject based on the settings.")

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

st.markdown('</div>', unsafe_allow_html=True)