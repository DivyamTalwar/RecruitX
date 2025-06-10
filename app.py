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
    page_title="AI Resume Screener",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    /* Main container styling */
    .stApp {
        background-color: #f0f2f6;
    }
    /* Card-like containers */
    .st-emotion-cache-1r4qj8v {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px !important;
        background-color: #ffffff;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    /* Button styling */
    .stButton>button {
        background-color: #4A90E2;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #357ABD;
        color: white;
    }
    /* Header styling */
    h1, h2, h3 {
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #4A90E2;'>🚀 AI-Powered Resume Screening</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Automate your hiring workflow by intelligently analyzing resumes against job descriptions.</p>", unsafe_allow_html=True)
st.divider()

with st.container(border=True):
    st.header("1. Provide Job & Candidate Details")
    col1, col2 = st.columns(2)
    
    with col1:
        job_description = st.text_area(
            "📝 **Job Description**", 
            placeholder="Paste the full job description here...", 
            height=250,
            help="You can paste the text directly."
        )

    with col2:
        resume_files = st.file_uploader(
            "📄 **Upload Candidate Resumes**",
            type=["pdf"],
            accept_multiple_files=True,
            help="Upload one or more PDF resumes. Ensure they are text-based, not scanned images."
        )
        num_candidates = st.slider(
            "🎯 **Number of Candidates to Invite**", 
            min_value=1, 
            max_value=10, 
            value=2,
            help="Select how many of the top-ranked candidates you want to generate interview invitations for."
        )

if st.button("✨ Run AI Screening", use_container_width=True, type="primary"):
    if not job_description.strip():
        st.error("⚠️ Please provide a job description.")
    elif not resume_files:
        st.error("⚠️ Please upload at least one resume.")
    else:
        try:
            with st.status("🚀 AI agent is starting the screening process...", expanded=True) as status:

                status.update(label="Step 1: Processing inputs...", state="running")
                raw_data = ingest_inputs(job_description, resume_files)

                status.update(label="Step 2: Analyzing job description...", state="running")
                parsed_job_desc = parse_job_description(raw_data["job_description"])
                
                status.update(label="Step 2: Analyzing resumes...", state="running")
                parsed_resumes_data = parse_resumes(raw_data["resume_files"])
                
                if all('error' in res for res in parsed_resumes_data["parsed_resumes"]):
                    status.update(label="Fatal Error", state="error", expanded=True)
                    st.error("ALL resumes failed to process. Please check your PDF files (must be text-readable, not scanned images) and try again.")
                    st.stop()
                
                status.update(label="Step 3: Scoring candidates against the job description...", state="running")
                candidate_scores = score_candidates(parsed_job_desc, parsed_resumes_data)

                status.update(label="Step 4: Ranking candidates based on scores...", state="running")
                ranked_candidates = rank_candidates(candidate_scores)

                status.update(label="Step 5: Generating personalized email drafts...", state="running")
                email_templates = generate_email_templates(ranked_candidates, parsed_job_desc, num_candidates)
                
                status.update(label="✅ AI Screening Complete!", state="complete", expanded=False)

            st.header("🏆 Screening Results")
            
            tab1, tab2 = st.tabs(["📊 Candidate Ranking", "✉️ Email Drafts"])

            with tab1:
                st.subheader("Top Candidates Overview")
                
                display_data = []
                for candidate in ranked_candidates:
                    display_data.append({
                        "Name": candidate.get("name"),
                        "Overall Score": candidate.get("overall"),
                        "Relevance": candidate.get("relevance"),
                        "Experience": candidate.get("experience"),
                        "Skills": candidate.get("skills"),
                        "AI Summary": candidate.get("comment"),
                    })
                
                df = pd.DataFrame(display_data)
                st.dataframe(
                    df, 
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Overall Score": st.column_config.ProgressColumn(
                            "Overall Score",
                            format="%d/100",
                            min_value=0,
                            max_value=100,
                        ),
                    }
                )

                st.subheader("Detailed Candidate Breakdown")
                for candidate in ranked_candidates:
                    with st.expander(f"**{candidate.get('name')}** - Score: {candidate.get('overall', 'N/A')}/100"):
                        st.json(candidate, expanded=False)

            with tab2:
                st.subheader("Generated Email Templates")
                
                col_invite, col_reject = st.columns(2)
                
                with col_invite:
                    st.markdown("<h4>✅ Invitations</h4>", unsafe_allow_html=True)
                    if email_templates["invitations"]:
                        for email in email_templates["invitations"]:
                            with st.container(border=True):
                                st.markdown(f"**To:** {email['name']}")
                                st.text_area("Email Body", value=email['email_body'], height=250, key=f"invite_{email['name']}")
                    else:
                        st.info("No candidates met the criteria for an invitation.")

                with col_reject:
                    st.markdown("<h4>❌ Rejections</h4>", unsafe_allow_html=True)
                    if email_templates["rejections"]:
                        for email in email_templates["rejections"]:
                            with st.container(border=True):
                                st.markdown(f"**To:** {email['name']}")
                                st.text_area("Email Body", value=email['email_body'], height=250, key=f"reject_{email['name']}")
                    else:
                        st.info("No candidates to reject.")

        except Exception as e:
            st.error(f"An unexpected error occurred during processing: {e}")