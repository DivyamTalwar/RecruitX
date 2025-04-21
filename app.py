import streamlit as st
import asyncio
from utils import (
    ingest_inputs,
    parse_job_description,
    parse_resumes,
    score_candidates,
    rank_candidates,
    generate_email_templates,
)

# Page config
st.set_page_config(
    page_title="AI Resume Screener Pro",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS with animations and modern design
st.markdown("""
<style>
    /* Modern gradient animated background */
    .stApp {
        background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Glassmorphism cards */
    .stTextArea, .stFileUploader, div[data-baseweb="select"] {
        backdrop-filter: blur(21px) saturate(200%);
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(209, 213, 219, 0.3) !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        transition: all 0.3s ease;
    }
    
    /* Hover effects */
    .stTextArea:hover, .stFileUploader:hover, div[data-baseweb="select"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.45);
    }
    
    /* Animated button */
    .stButton > button {
        width: 100%;
        padding: 15px 20px;
        background: linear-gradient(45deg, #FF512F, #DD2476, #FF512F);
        background-size: 200% auto;
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        transition: 0.5s;
        animation: pulse 2s infinite;
    }
    
    .stButton > button:hover {
        background-position: right center;
        transform: scale(1.02);
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 82, 47, 0.7); }
        70% { box-shadow: 0 0 0 15px rgba(255, 82, 47, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 82, 47, 0); }
    }
    
    /* Progress animations */
    .stProgress > div > div {
        background: linear-gradient(90deg, #4CAF50, #8BC34A);
        transition: width 0.5s ease-out;
    }
    
    /* Floating labels */
    .floating-label {
        position: relative;
        margin-bottom: 20px;
        animation: float 3s ease-in-out infinite;
    }
    
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        background: transparent;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(45deg, #FF512F, #DD2476);
        border-radius: 5px;
    }
    
    /* Neon text effect */
    .neon-text {
        color: #fff;
        text-shadow: 0 0 7px #fff,
                     0 0 10px #fff,
                     0 0 21px #fff,
                     0 0 42px #0fa,
                     0 0 82px #0fa,
                     0 0 92px #0fa,
                     0 0 102px #0fa,
                     0 0 151px #0fa;
        animation: neon 1.5s ease-in-out infinite alternate;
    }
    
    @keyframes neon {
        from { text-shadow: 0 0 10px #fff, 0 0 20px #fff, 0 0 30px #fff, 0 0 40px #0fa; }
        to { text-shadow: 0 0 5px #fff, 0 0 10px #fff, 0 0 15px #fff, 0 0 20px #0fa; }
    }
    
    /* Card layouts */
    .custom-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        transition: all 0.3s ease;
    }
    
    .custom-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# Animated header with SVG wave
st.markdown("""
<div style='text-align: center; padding: 30px 0;'>
    <h1 class='neon-text' style='font-size: 3.5em; font-weight: 800; margin-bottom: 10px;'>
        🚀 AI Resume Screening Pro
    </h1>
    <p style='color: #E0E0E0; font-size: 1.2em; margin-bottom: 30px;'>
        Transform Your Hiring Process with AI-Powered Intelligence
    </p>
    <svg viewBox="0 0 1440 320" style="margin-top: -50px;">
        <path fill="rgba(255,255,255,0.1)" fill-opacity="1" 
              d="M0,96L48,112C96,128,192,160,288,186.7C384,213,480,235,576,213.3C672,192,768,128,864,128C960,128,1056,192,1152,213.3C1248,235,1344,213,1392,202.7L1440,192L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z">
        </path>
    </svg>
</div>
""", unsafe_allow_html=True)

# Job Description Section with animation
st.markdown('<div class="custom-card">', unsafe_allow_html=True)
st.subheader("📄 Job Description")
job_description = st.text_area(
    "Enter the job requirements or paste URL",
    height=150,
    key="job_desc"
)
st.markdown('</div>', unsafe_allow_html=True)

# Resume Upload Section with animation
st.markdown('<div class="custom-card">', unsafe_allow_html=True)
st.subheader("📂 Upload Resumes")
resume_files = st.file_uploader(
    "Drop candidate resumes here",
    type=["pdf", "docx"],
    accept_multiple_files=True,
    key="resume_upload"
)

if resume_files:
    st.markdown(f"""
        <div style='text-align: center; padding: 15px; color: #4CAF50; font-size: 1.1em;'>
            ✅ {len(resume_files)} files uploaded successfully!
        </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Candidates Selection with animated slider
st.markdown('<div class="custom-card">', unsafe_allow_html=True)
st.subheader("🎯 Select Interview Candidates")
num_candidates = st.slider(
    "Number of candidates to interview",
    1, 4, 2,
    help="Slide to select number of top candidates"
)
st.markdown('</div>', unsafe_allow_html=True)

async def run_agent():
    if not job_description or not resume_files:
        st.error("⚠️ Please provide both job description and resumes!")
        return
    
    progress_text = "Operation in progress. Please wait..."
    progress_bar = st.progress(0, text=progress_text)
    
    try:
        # Step 1: Process Inputs
        progress_bar.progress(20, text="🔍 Processing inputs...")
        raw_data = await ingest_inputs(job_description, resume_files)
        
        # Step 2: Parse Requirements
        progress_bar.progress(40, text="📑 Analyzing requirements...")
        parsed_requirements = await parse_job_description(raw_data)
        parsed_resumes = await parse_resumes(resume_files)
        
        # Step 3: Score Candidates
        progress_bar.progress(60, text="⚖️ Evaluating candidates...")
        candidate_scores = await score_candidates(parsed_requirements, parsed_resumes)
        
        # Step 4: Rank Candidates
        progress_bar.progress(80, text="📊 Ranking candidates...")
        ranked_candidates = rank_candidates(candidate_scores)
        
        # Step 5: Generate Emails
        progress_bar.progress(100, text="✉️ Preparing email templates...")
        email_templates = await generate_email_templates(ranked_candidates, parsed_requirements, num_candidates)
        
        # Success Animation
        st.balloons()
        st.success("✨ Processing Complete!")
        
        # Display Results
        st.markdown("""
            <div style='text-align: center; margin: 30px 0;'>
                <h2 class='neon-text'>🌟 Results Ready!</h2>
            </div>
        """, unsafe_allow_html=True)
        
        # Results in expandable cards
        with st.expander("📊 Candidate Rankings", expanded=True):
            st.json(ranked_candidates)
        
        with st.expander("✉️ Email Templates"):
            st.json(email_templates)
            
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        progress_bar.empty()

# Animated Run Button
if st.button("🚀 Start AI Screening", help="Click to begin analysis"):
    asyncio.run(run_agent())
