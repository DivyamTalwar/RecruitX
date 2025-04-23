import streamlit as st
from utils import (
    ingest_inputs,
    parse_job_description,
    parse_resumes,
    score_candidates,
    rank_candidates,
    generate_email_templates,
)

# App Title and Description
st.markdown(
    "<h1 style='text-align: center; color: #4A90E2;'>🚀 AI-Powered Resume Screening</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<h5 style='text-align: center; color: #333;'>Smartly analyze resumes & job descriptions to find the best candidates.</h5>",
    unsafe_allow_html=True,
)
st.write("---")

# Input Sections
st.subheader("📄 Job Description")
job_description = st.text_area("Paste the job description or URL", height=150)

st.subheader("📂 Upload Candidate Resumes")
resume_files = st.file_uploader(
    "Upload resume files (PDF/Word)",
    type=["pdf", "docx", "doc"],
    accept_multiple_files=True
)

st.subheader("🎯 Candidates to Invite")
num_candidates = st.slider("Select the number of candidates for interviews", 1, 4, 2)

def run_agent():
    # Validate user inputs before processing
    if not job_description:
        st.error("⚠️ Please provide a job description or URL.")
        return
    if not resume_files:
        st.error("⚠️ Please upload at least one resume file.")
        return

    st.success("✅ AI Agent is processing... Stay tuned! ⏳")
    
    # STEP 1: Process Inputs
    try:
        with st.spinner("🔍 Step 1: Extracting & processing inputs..."):
            raw_data = ingest_inputs(job_description, resume_files)
            st.success("✅ Step 1 Complete: Inputs processed.")
            with st.expander("🔎 View Processed Inputs", expanded=False):
                st.json(raw_data)
    except Exception as e:
        st.error(f"Error in Step 1 (Ingesting Inputs): {e}")
        return
    
    # STEP 2: Parse Job Description & Resumes
    try:
        with st.spinner("📑 Step 2: Understanding job description & resumes..."):
            parsed_requirements = parse_job_description(raw_data)
            parsed_resumes = parse_resumes(resume_files)
            st.success("✅ Step 2 Complete: Job description & resumes parsed.")
            with st.expander("📜 View Job Description", expanded=False):
                st.json(parsed_requirements)
            with st.expander("📄 View Processed Resumes", expanded=False):
                st.json(parsed_resumes)
    except Exception as e:
        st.error(f"Error in Step 2 (Parsing Inputs): {e}")
        return

    # STEP 3: Score Candidates
    try:
        with st.spinner("⚖️ Step 3: Evaluating candidates..."):
            candidate_scores = score_candidates(parsed_requirements, parsed_resumes)
            st.success("✅ Step 3 Complete: Candidates scored.")
            with st.expander("📊 View Candidate Scores", expanded=False):
                st.json(candidate_scores)
    except Exception as e:
        st.error(f"Error in Step 3 (Scoring Candidates): {e}")
        return

    # STEP 4: Rank Candidates
    try:
        with st.spinner("📊 Step 4: Ranking top candidates..."):
            ranked_candidates = rank_candidates(candidate_scores)
            st.success("✅ Step 4 Complete: Candidates ranked.")
            with st.expander("🏆 View Ranked Candidates", expanded=False):
                st.json(ranked_candidates)
    except Exception as e:
        st.error(f"Error in Step 4 (Ranking Candidates): {e}")
        return

    # STEP 5: Generate Email Templates
    try:
        with st.spinner("✉️ Step 5: Generating email templates..."):
            email_templates = generate_email_templates(ranked_candidates, parsed_requirements, num_candidates)
            st.success("✅ Step 5 Complete: Emails generated.")
            with st.expander("📩 View Email Templates", expanded=False):
                st.json(email_templates)
    except Exception as e:
        st.error(f"Error in Step 5 (Generating Email Templates): {e}")
        return

    st.markdown(
        "<h3 style='text-align: center; color: #27AE60;'>🎉 AI Agent has completed processing! Your results are ready. 🚀</h3>",
        unsafe_allow_html=True,
    )

if st.button("🚀 Run AI Screening"):
    run_agent()
