import streamlit as st
import json
import requests
from streamlit_lottie import st_lottie
from streamlit_extras.colored_header import colored_header
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.card import card
import time

from utils import (
    ingest_inputs,
    parse_job_description,
    parse_resumes,
    score_candidates,
    rank_candidates,
    generate_email_templates,
)

# Page configuration
st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        background-color: #4A90E2;
        color: white;
        border-radius: 10px;
        padding: 0.5rem 2rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #357ABD;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .css-1d391kg {
        background-color: #ffffff;
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .upload-box {
        border: 2px dashed #4A90E2;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    .upload-box:hover {
        border-color: #357ABD;
        background-color: rgba(74,144,226,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# Load Lottie Animations
def load_lottie_url(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Lottie Animations
lottie_screening = load_lottie_url("https://assets9.lottiefiles.com/packages/lf20_xyadoh9h.json")
lottie_success = load_lottie_url("https://assets5.lottiefiles.com/packages/lf20_sucT7t.json")

# Header Section with Animation
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st_lottie(lottie_screening, height=200, key="screening")

st.markdown(
    "<h1 style='text-align: center; color: #4A90E2; font-size: 3rem; margin-bottom: 0;'>🚀 AI Resume Screener</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center; color: #666; font-size: 1.2rem; margin-top: 0;'>Transform your hiring process with AI-powered resume analysis</p>",
    unsafe_allow_html=True
)

add_vertical_space(2)

# Main Content in Cards
with st.container():
    col1, col2 = st.columns([2,1])
    
    with col1:
        with st.expander("📋 Job Description", expanded=True):
            colored_header(
                label="Enter Job Details",
                description="Paste the job description or provide a URL",
                color_name="blue-70"
            )
            job_description = st.text_area(
                "",
                height=150,
                placeholder="Enter the job description here..."
            )

    with col2:
        with card(
            title="📊 Interview Settings",
            text="Configure your screening parameters",
            styles={
                "card": {
                    "background-color": "#ffffff",
                    "border-radius": "10px",
                    "box-shadow": "0 4px 6px rgba(0,0,0,0.1)",
                    "padding": "1rem",
                }
            }
        ):
            num_candidates = st.slider(
                "Number of candidates to interview",
                1, 10, 3,
                help="Select how many top candidates you want to interview"
            )

add_vertical_space(1)

# Resume Upload Section
st.markdown("<div class='upload-box'>", unsafe_allow_html=True)
resume_files = st.file_uploader(
    "📂 Upload Candidate Resumes (PDF/Word)",
    type=["pdf", "docx", "doc"],
    accept_multiple_files=True,
    help="Upload multiple resume files in PDF or Word format"
)
st.markdown("</div>", unsafe_allow_html=True)

add_vertical_space(2)

# Processing Function with Progress Animation
def run_agent():
    if not job_description:
        st.error("⚠️ Please provide a job description")
        return
    if not resume_files:
        st.error("⚠️ Please upload at least one resume")
        return

    progress_text = "Operation in progress. Please wait..."
    my_bar = st.progress(0, text=progress_text)

    # Step 1: Process Inputs
    try:
        my_bar.progress(20, text="🔍 Processing inputs...")
        raw_data = ingest_inputs(job_description, resume_files)
        with st.expander("🔎 Input Processing Results", expanded=False):
            st.json(raw_data)
    except Exception as e:
        st.error(f"Error processing inputs: {e}")
        return

    # Step 2: Parse Documents
    try:
        my_bar.progress(40, text="📑 Analyzing documents...")
        parsed_requirements = parse_job_description(raw_data)
        parsed_resumes = parse_resumes(resume_files)
        with st.expander("📄 Parsed Documents", expanded=False):
            st.json({"requirements": parsed_requirements, "resumes": parsed_resumes})
    except Exception as e:
        st.error(f"Error parsing documents: {e}")
        return

    # Step 3: Score Candidates
    try:
        my_bar.progress(60, text="⚖️ Evaluating candidates...")
        candidate_scores = score_candidates(parsed_requirements, parsed_resumes)
        with st.expander("📊 Candidate Scores", expanded=False):
            st.json(candidate_scores)
    except Exception as e:
        st.error(f"Error scoring candidates: {e}")
        return

    # Step 4: Rank Candidates
    try:
        my_bar.progress(80, text="🏆 Ranking candidates...")
        ranked_candidates = rank_candidates(candidate_scores)
        with st.expander("🎯 Rankings", expanded=False):
            st.json(ranked_candidates)
    except Exception as e:
        st.error(f"Error ranking candidates: {e}")
        return

    # Step 5: Generate Emails
    try:
        my_bar.progress(100, text="✉️ Generating email templates...")
        email_templates = generate_email_templates(
            ranked_candidates, parsed_requirements, num_candidates
        )
        
        # Success Animation
        st_lottie(lottie_success, height=200, key="success")
        
        # Results Display
        st.markdown("### 🎉 Processing Complete!")
        
        # Display results in tabs
        tab1, tab2, tab3 = st.tabs(["📊 Top Candidates", "✉️ Email Templates", "📈 Detailed Analysis"])
        
        with tab1:
            for idx, candidate in enumerate(ranked_candidates[:num_candidates]):
                with st.container():
                    st.markdown(f"#### Rank {idx+1}: {candidate['name']}")
                    col1, col2 = st.columns([2,1])
                    with col1:
                        st.progress(candidate['overall']/100)
                    with col2:
                        st.metric("Score", f"{candidate['overall']}%")
        
        with tab2:
            for template in email_templates["invitations"]:
                st.text_area(
                    f"Email for {template['name']}",
                    template['email_body'],
                    height=200
                )
        
        with tab3:
            st.json(ranked_candidates)
            
    except Exception as e:
        st.error(f"Error generating emails: {e}")
        return

# Run Button with Animation
if st.button("🚀 Start AI Screening", help="Click to begin the screening process"):
    run_agent()

# Footer
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #666;'>Powered by AI | Built with ❤️ using Streamlit</p>",
    unsafe_allow_html=True
)
