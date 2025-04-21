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

# Page configuration and styling
st.set_page_config(
    page_title="AI Resume Screening",
    page_icon="🚀",
    layout="wide",
)

# Custom CSS for animations and styling
st.markdown("""
    <style>
    /* Gradient animations */
    @keyframes gradient {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    
    .stApp {
        background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
    }
    
    /* Card styling */
    .stMarkdown {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 20px;
        backdrop-filter: blur(10px);
    }
    
    /* Button animations */
    .stButton>button {
        transition: all 0.3s ease;
        border-radius: 20px;
    }
    
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    
    /* Progress bar animations */
    .stProgress > div > div {
        background-color: #4CAF50;
        transition: width 0.5s ease-in-out;
    }
    </style>
    """, unsafe_allow_html=True)

# Animated header with pulsing effect
st.markdown(
    """
    <div style='text-align: center; padding: 30px;'>
        <h1 style='color: white; font-size: 3em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                   animation: pulse 2s infinite;'>
            🚀 AI-Powered Resume Screening
        </h1>
        <p style='color: #E0E0E0; font-size: 1.2em; margin-top: 10px;'>
            Smart Analysis • Instant Results • Better Hiring
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Create tabs for better organization
tab1, tab2 = st.tabs(["📝 Input", "📊 Results"])

with tab1:
    # Job Description Section with glassmorphism effect
    st.markdown("""
        <div style='background: rgba(255,255,255,0.1); 
                    padding: 20px; 
                    border-radius: 15px; 
                    backdrop-filter: blur(10px);
                    margin: 10px 0;'>
    """, unsafe_allow_html=True)
    
    st.subheader("📄 Job Description")
    job_description = st.text_area(
        "Paste the job description or URL",
        height=150,
        help="Enter the complete job description or paste a URL"
    )

    # Resume Upload Section with animation
    st.subheader("📂 Upload Candidate Resumes")
    resume_files = st.file_uploader(
        "Drop resume files here",
        type=["pdf", "docx", "doc"],
        accept_multiple_files=True,
        help="Supports PDF and Word documents"
    )

    # Animated counter for uploaded files
    if resume_files:
        st.markdown(f"""
            <div style='text-align: center; 
                        padding: 10px; 
                        color: white; 
                        font-size: 1.2em;
                        animation: fadeIn 1s ease-in;'>
                📁 {len(resume_files)} files uploaded
            </div>
        """, unsafe_allow_html=True)

    # Candidate Selection with animated slider
    st.subheader("🎯 Candidates to Invite")
    num_candidates = st.slider(
        "Select number of candidates",
        1, 4, 2,
        help="How many top candidates would you like to invite?"
    )

async def run_agent():
    if not job_description or not resume_files:
        st.error("⚠️ Please provide both job description and resume files.")
        return

    progress_text = "Operation in progress. Please wait..."
    my_bar = st.progress(0, text=progress_text)

    try:
        # Step 1: Process Inputs
        my_bar.progress(20, text="🔍 Processing inputs...")
        raw_data = await ingest_inputs(job_description, resume_files)
        
        # Step 2: Parse Requirements
        my_bar.progress(40, text="📑 Analyzing requirements...")
        parsed_requirements = await parse_job_description(raw_data)
        parsed_resumes = await parse_resumes(resume_files)
        
        # Step 3: Score Candidates
        my_bar.progress(60, text="⚖️ Scoring candidates...")
        candidate_scores = await score_candidates(parsed_requirements, parsed_resumes)
        
        # Step 4: Rank Candidates
        my_bar.progress(80, text="📊 Ranking candidates...")
        ranked_candidates = rank_candidates(candidate_scores)
        
        # Step 5: Generate Emails
        my_bar.progress(100, text="✉️ Preparing email templates...")
        email_templates = await generate_email_templates(
            ranked_candidates, 
            parsed_requirements, 
            num_candidates
        )

        # Success Animation
        st.balloons()
        st.success("✨ Processing Complete!")
        
        # Display Results in Tabs
        with tab2:
            st.markdown("""
                <div style='text-align: center'>
                    <h2 style='color: #4CAF50'>🎉 Results Ready!</h2>
                </div>
            """, unsafe_allow_html=True)
            
            # Results displayed in expandable sections
            with st.expander("📊 Candidate Rankings", expanded=True):
                st.json(ranked_candidates)
            
            with st.expander("✉️ Email Templates"):
                st.json(email_templates)

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        my_bar.empty()

# Run Button with hover animation
if st.button(
    "🚀 Start AI Screening",
    help="Click to begin the screening process",
    type="primary",
):
    asyncio.run(run_agent())
