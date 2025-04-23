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

st.set_page_config(page_title="AI Resume Screener", layout="centered")

st.markdown(
    "<h1 style='text-align: center; color: #4A90E2;'>🚀 AI-Powered Resume Screening</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<h5 style='text-align: center; color: #333;'>Smartly analyze resumes & job descriptions to find the best candidates.</h5>",
    unsafe_allow_html=True,
)
st.write("---")

st.subheader("📄 Job Description")
job_description = st.text_area("Paste the job description or URL", height=150)

st.subheader("📂 Upload Candidate Resumes")
resume_files = st.file_uploader(
    "Upload resume files (PDF/Word)",
    type=["pdf", "docx", "doc"],
    accept_multiple_files=True,
)

st.subheader("🎯 Candidates to Invite")
num_candidates = st.slider("Select the number of candidates for interviews", min_value=1, max_value=5, value=2)

async def run_agent():
    if not job_description:
        st.error("⚠️ Please provide a job description or URL.")
        return
    if not resume_files:
        st.error("⚠️ Please upload at least one resume file.")
        return

    st.success("✅ AI Agent is now processing... Stay tuned! ⏳")
    status_text = st.empty()

    try:
        # Step 1: Ingest Input
        with st.spinner("🔍 Step 1: Extracting & processing inputs..."):
            raw_data = await ingest_inputs(job_description, resume_files)
            status_text.markdown("✅ **Step 1 Complete:** Inputs processed.")
            with st.expander("🔎 View Processed Inputs", expanded=False):
                st.json(raw_data)

        # Step 2: Parse JD & Resumes
        with st.spinner("📑 Step 2: Understanding job description & resumes..."):
            parsed_requirements = await parse_job_description(raw_data)
            parsed_resumes = await parse_resumes(resume_files)
            status_text.markdown("✅ **Step 2 Complete:** Job description & resumes parsed.")
            with st.expander("📜 View Job Description", expanded=False):
                st.json(parsed_requirements)
            with st.expander("📄 View Processed Resumes", expanded=False):
                st.json(parsed_resumes)

        # Step 3: Score Candidates
        with st.spinner("⚖️ Step 3: Evaluating candidates..."):
            candidate_scores = await score_candidates(parsed_requirements, parsed_resumes)
            status_text.markdown("✅ **Step 3 Complete:** Candidates scored.")
            with st.expander("📊 View Candidate Scores", expanded=False):
                st.json(candidate_scores)

        # Step 4: Rank Candidates
        with st.spinner("🏆 Step 4: Ranking top candidates..."):
            ranked_candidates = rank_candidates(candidate_scores)
            status_text.markdown("✅ **Step 4 Complete:** Candidates ranked.")
            with st.expander("🏅 View Ranked Candidates", expanded=False):
                st.json(ranked_candidates)

        # Step 5: Generate Emails
        with st.spinner("✉️ Step 5: Generating emails for interview invites and rejections..."):
            email_templates = await generate_email_templates(ranked_candidates, parsed_requirements, num_candidates)
            status_text.markdown("✅ **Step 5 Complete:** Emails generated.")
            with st.expander("📩 View Email Templates", expanded=False):
                st.json(email_templates)

        status_text.markdown(
            "<h3 style='text-align: center; color: #27AE60;'>🎉 AI Agent has completed processing! Your results are ready. 🚀</h3>",
            unsafe_allow_html=True,
        )

    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")

if st.button("🚀 Run AI Screening"):
    asyncio.run(run_agent())
