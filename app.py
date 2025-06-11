import streamlit as st
from langchain_groq import ChatGroq
import os
from utils import (
    extract_key_requirements,
    score_candidate_explainable,
    generate_interview_questions,
    extract_pdf_text,
    create_candidate_rag_retriever,
    ask_rag_question,
    generate_email_templates,
)
import time
import json

# --- 1. Page & AI Client Configuration ---
st.set_page_config(
    page_title="RecruitX | The Future of Hiring",
    page_icon="🔮",
    layout="wide",
)

# --- 2. Initialize LLM (once per session) ---
if 'llm' not in st.session_state:
    try:
        st.session_state.llm = ChatGroq(
            model="llama3-70b-8192",
            temperature=0.1,
            api_key=st.secrets["GROQ_API_KEY"]
        )
    except (KeyError, FileNotFoundError):
        st.error("🔴 GROQ_API_KEY not found. Please set it as an environment variable.")
        st.stop()

# --- 3. THE ULTIMATE UI - Custom CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap');
    
    :root {
        --bg-color: #0D1117;
        --card-bg-color: #161B22;
        --border-color: #30363D;
        --text-color: #E2E8F0;
        --subtle-text-color: #94A3B8;
        --accent-color: #007BFF;
        --accent-hover: #3895ff;
        --accent-glow: rgba(0, 123, 255, 0.3);
        --font-main: 'Inter', sans-serif;
        --font-display: 'Playfair Display', serif;
    }

    /* --- Base & Background --- */
    html, body, [class*="st-"] { font-family: var(--font-main); color: var(--text-color); }
    .stApp {
        background-color: var(--bg-color);
        background-image: radial-gradient(var(--border-color) 0.5px, transparent 0.5px);
        background-size: 15px 15px;
    }

    /* --- Layout & Animations --- */
    .main-content-wrapper { max-width: 1200px; margin: auto; padding: 2rem; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .fade-in-up { animation: fadeInUp 1s ease-out forwards; }
    .staggered-fade-in-up { opacity: 0; animation: fadeInUp 0.8s ease-out forwards; }

    /* --- Header & Branding --- */
    .header { text-align: center; margin: 2rem 0 4rem 0; }
    .header h1 {
        font-family: var(--font-display);
        font-size: 5rem;
        font-weight: 700;
        color: #FFFFFF;
        opacity: 0;
        animation: fadeInUp 1s ease-out 0.2s forwards;
    }
    .header p {
        color: var(--subtle-text-color);
        font-size: 1.25rem;
        margin-top: 0.5rem;
        opacity: 0;
        animation: fadeInUp 1s ease-out 0.5s forwards;
    }

    /* --- Upgraded Input Cards --- */
    .input-card {
        background: var(--card-bg-color);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 2.5rem;
        transition: all 0.3s ease;
    }
    .input-card:focus-within {
        border-color: var(--accent-color);
        box-shadow: 0 0 20px var(--accent-glow);
    }
    
    /* --- Premium Buttons --- */
    .stButton>button { border-radius: 8px; padding: 12px 24px; font-weight: 600; transition: all 0.2s ease-in-out !important; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 var(--accent-glow); } 70% { box-shadow: 0 0 0 10px rgba(0, 123, 255, 0); } 100% { box-shadow: 0 0 0 0 rgba(0, 123, 255, 0); } }
    .primary-action-button button {
        background-color: var(--accent-color);
        color: white;
        border: none;
        animation: pulse 2s infinite;
    }
    .primary-action-button button:hover {
        transform: scale(1.03);
        box-shadow: 0 0 25px var(--accent-glow);
        animation: none; /* Stop pulsing on hover */
    }
    .secondary-action-button button { background: transparent; border: 1px solid var(--border-color); color: var(--subtle-text-color); }
    .secondary-action-button button:hover { background: var(--card-bg-color); border-color: var(--text-color); color: var(--text-color); }

    /* --- General Styling from previous version --- */
    .section-header { font-size: 1.5rem; font-weight: 600; padding-bottom: 1rem; border-bottom: 1px solid var(--border-color); margin-bottom: 1.5rem; }
    .stProgress > div > div > div > div { background-color: var(--accent-color); }
    .stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid var(--border-color); }
    .stTabs [data-baseweb="tab"] { font-size: 1.05rem; padding: 1rem; }
    .stTabs [data-baseweb="tab--selected"] { color: var(--accent-color); border-bottom-color: var(--accent-color); }
    .stExpander { border: none; background: rgba(0,0,0,0.2); border-radius: 8px; }
    .stExpander header { font-size: 1rem; color: var(--subtle-text-color); }
    .candidate-name { font-size: 1.7rem; font-weight: 700; color: #FFFFFF; }
    .xai-item { border-left: 3px solid; padding-left: 1rem; margin-bottom: 1rem; }
    .xai-met { border-color: #28a745; }
    .xai-gap { border-color: #dc3545; }
    .chat-bubble { padding: 1rem; border-radius: 10px; margin-bottom: 1rem; max-width: 80%; }
    .chat-bubble.user { background-color: var(--accent-color); color: var(--bg-color); align-self: flex-end; border-bottom-right-radius: 0; }
    .chat-bubble.assistant { background-color: #2a2a2a; color: var(--text-color); align-self: flex-start; border-bottom-left-radius: 0; }
</style>
""", unsafe_allow_html=True)


# --- 4. App State Management ---
if "step" not in st.session_state:
    st.session_state.step = "upload"
    st.session_state.candidates = []
    st.session_state.key_requirements = []
    st.session_state.chat_histories = {} 
    st.session_state.rag_retrievers = {}
    st.session_state.compare_list = []
    st.session_state.saved_job_description = ""
    st.session_state.saved_resume_files = []


# --- 5. Callback & Helper Functions ---
def proceed_to_weighting():
    """Validates inputs and calls the AI to extract requirements before proceeding."""
    if not st.session_state.saved_job_description.strip() or not st.session_state.saved_resume_files:
        st.warning("⚠️ Please provide a Job Description and upload at least one Resume.")
        return

    with st.spinner("AI is extracting key requirements from your Job Description..."):
        try:
            requirements = extract_key_requirements(st.session_state.saved_job_description, st.session_state.llm)
            if requirements and isinstance(requirements, list) and len(requirements) > 0:
                st.session_state.key_requirements = requirements
                st.session_state.step = "weighting"
            else:
                st.error("❗️ AI could not extract specific requirements. Please provide a more detailed job description.")
        except Exception as e:
            st.error(f"An error occurred during AI analysis: {e}")

def run_final_analysis(weighted_reqs, resume_files, job_description):
    with st.spinner("Performing deep analysis on all candidates..."):
        resumes_to_process = []
        for file in resume_files:
            text = extract_pdf_text(file)
            if text:
                resumes_to_process.append({"text": text, "filename": file.name})
        candidate_results = []
        progress_bar = st.progress(0, "Analyzing candidates...")
        total_candidates = len(resumes_to_process)

        for i, res in enumerate(resumes_to_process):
            try:
                progress_bar.progress((i + 1) / total_candidates, f"Analyzing {res['filename']}...")
                score_data = score_candidate_explainable(job_description, res["text"], weighted_reqs, st.session_state.llm)
                result_dict = score_data.model_dump()
                result_dict['filename'] = res['filename']
                candidate_results.append(result_dict)
                
            except Exception as e:
                print(f"Error processing {res['filename']}: {e}")
                error_result = {
                    "name": f"Error: {res['filename']}",
                    "overall_score": 0,
                    "summary": f"The AI failed to process this resume. Please check the file. Error: {e}",
                    "requirement_analysis": [],
                    "filename": res['filename']
                }
                candidate_results.append(error_result)
            
            time.sleep(1)
        
        progress_bar.empty()
        st.session_state.candidates = sorted(candidate_results, key=lambda x: x['overall_score'], reverse=True)
        
        st.session_state.rag_retrievers = {}
        st.session_state.chat_histories = {}
        for candidate in st.session_state.candidates:
            if "Error:" not in candidate['name']:
                candidate_name = candidate['name']
                full_text_info = next((res for res in resumes_to_process if res['filename'] == candidate.get('filename')), None)
                if full_text_info:
                    retriever = create_candidate_rag_retriever(full_text_info['text'], full_text_info['filename'])
                    st.session_state.rag_retrievers[candidate_name] = retriever
                    st.session_state.chat_histories[candidate_name] = []

        st.session_state.step = "results"

def go_back_to_upload():
    """Resets the state to go back to the first step."""
    st.session_state.step = "upload"
    st.session_state.key_requirements = []

def trigger_analysis():
    weighted_reqs = {}
    for req in st.session_state.key_requirements:
        weighted_reqs[req] = { "importance": st.session_state[f"imp_{req}"], "knockout": st.session_state[f"ko_{req}"] }
    run_final_analysis(weighted_reqs, st.session_state.saved_resume_files, st.session_state.saved_job_description)


# --- 6. Main App UI ---
st.markdown('<div class="main-content-wrapper fade-in">', unsafe_allow_html=True)
st.markdown('<div class="header"><h1>RecruitX</h1><p>The future of hiring is here. Find the perfect candidate with true AI understanding.</p></div>', unsafe_allow_html=True)

if st.session_state.step == "upload":
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.markdown("<h2 class='section-header'>Step 1: Provide Your Data</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown("<h5>📝 Job Description</h5>", unsafe_allow_html=True)
        st.session_state.saved_job_description = st.text_area("Job Description", st.session_state.saved_job_description, placeholder="Paste the full job description...", height=300, label_visibility="collapsed")
    with col2:
        st.markdown("<h5>👥 Upload Candidate Resumes</h5>", unsafe_allow_html=True)
        st.session_state.saved_resume_files = st.file_uploader("Upload Resumes", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="primary-action-button">', unsafe_allow_html=True)
    st.button("Analyze Requirements", on_click=proceed_to_weighting, use_container_width=True)
    st.markdown('</div></div>', unsafe_allow_html=True)

elif st.session_state.step == "weighting":
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.markdown("<h2 class='section-header'>Step 2: Define What Matters Most</h2>", unsafe_allow_html=True)
    st.info("🤖 Our AI has extracted the key requirements. Please set their importance.")
    for i, req in enumerate(st.session_state.key_requirements):
        st.markdown(f'<div class="staggered-fade-in-up" style="animation-delay: {i*100}ms">', unsafe_allow_html=True)
        cols = st.columns([4, 2, 1])
        with cols[0]: st.write(f"▸ {req}")
        with cols[1]: st.selectbox("Importance", ["Normal", "Important", "Critical"], key=f"imp_{req}", index=1, label_visibility="collapsed")
        with cols[2]: st.checkbox("Knock-Out?", key=f"ko_{req}", help="If unchecked, this requirement is a deal-breaker.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    btn_cols = st.columns(2)
    with btn_cols[0]:
        st.markdown('<div class="secondary-action-button">', unsafe_allow_html=True)
        st.button("⬅️ Go Back & Edit", on_click=go_back_to_upload, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with btn_cols[1]:
        st.markdown('<div class="primary-action-button">', unsafe_allow_html=True)
        st.button("🚀 Run Final Analysis", on_click=trigger_analysis, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.step == "results":
    st.success("✅ Analysis Complete! Explore your results below.")
    tabs = st.tabs(["🏆 Leaderboard", "🤝 Compare Candidates", "✉️ Email Drafts"])
    
    with tabs[0]:
        for candidate in st.session_state.candidates:
            st.markdown('<div class="input-card" style="margin-bottom: 1.5rem;">', unsafe_allow_html=True)
            candidate_name = candidate['name']
            col1, col2 = st.columns([3, 1])
            with col1: st.markdown(f"<h3 class='candidate-name'>{candidate_name}</h3>", unsafe_allow_html=True)
            with col2: st.progress(candidate['overall_score'], text=f"Overall Score: {candidate['overall_score']}%")
            st.markdown(f"<p style='color: var(--subtle-text-color);'>{candidate['summary']}</p>", unsafe_allow_html=True)
            if "Error:" not in candidate_name:
                with st.expander("View Detailed Requirement Analysis (XAI)"):
                    for req in candidate['requirement_analysis']:
                        if req['match_status']: st.markdown(f"<div class='xai-item xai-met'><b>✅ Met:</b> {req['requirement']}<br><small><i><b>Evidence:</b> \"{req['evidence']}\"</i></small></div>", unsafe_allow_html=True)
                        else: st.markdown(f"<div class='xai-item xai-gap'><b>❌ Gap:</b> {req['requirement']}<br><small><i><b>Reason:</b> {req['evidence']}</i></small></div>", unsafe_allow_html=True)
                if st.button("🤖 Generate Interview Questions", key=f"gen_q_{candidate_name}"):
                    with st.spinner("Generating..."):
                        questions = generate_interview_questions(candidate['name'], candidate['summary'], st.session_state.saved_job_description, st.session_state.llm)
                        st.markdown("<h5>Behavioral Questions:</h5>", unsafe_allow_html=True)
                        for q in questions.behavioral: st.markdown(f"- {q}")
                        st.markdown("<h5>Technical Questions:</h5>", unsafe_allow_html=True)
                        for q in questions.technical: st.markdown(f"- {q}")
                st.markdown("<hr style='border-color:var(--border-color); margin: 1.5rem 0;'>", unsafe_allow_html=True)
                st.markdown("<h5>💬 Chat about this Candidate</h5>", unsafe_allow_html=True)
                chat_container = st.container(height=200)
                with chat_container:
                    if candidate_name in st.session_state.chat_histories:
                        for msg in st.session_state.chat_histories[candidate_name]:
                            st.markdown(f"<div class='chat-bubble {msg['role']}'>{msg['content']}</div>", unsafe_allow_html=True)
                if prompt := st.chat_input("Ask about this candidate...", key=f"chat_{candidate_name}"):
                    st.session_state.chat_histories[candidate_name].append({"role": "user", "content": prompt})
                    retriever = st.session_state.rag_retrievers.get(candidate_name)
                    if retriever:
                        with chat_container:
                            st.markdown(f"<div class='chat-bubble user'>{prompt}</div>", unsafe_allow_html=True)
                            with st.spinner("Thinking..."):
                                answer = ask_rag_question(retriever, prompt, st.session_state.llm)
                                st.session_state.chat_histories[candidate_name].append({"role": "assistant", "content": answer})
                                st.markdown(f"<div class='chat-bubble assistant'>{answer}</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.multiselect("Select candidates to compare side-by-side:", [c['name'] for c in st.session_state.candidates if "Error:" not in c['name']], key="compare_list")
        if len(st.session_state.compare_list) > 1:
            compare_data = {c['name']: c for c in st.session_state.candidates if c['name'] in st.session_state.compare_list}
            cols = st.columns(len(st.session_state.compare_list))
            col_index = 0
            for name, data in compare_data.items():
                with cols[col_index]:
                    st.markdown(f"<h4>{name}</h4>", unsafe_allow_html=True)
                    st.progress(data['overall_score'], text=f"Score: {data['overall_score']}%")
                    st.markdown("<h5>AI Summary:</h5>", unsafe_allow_html=True)
                    st.markdown(f"<p style='color:var(--subtle-text-color);'>{data['summary']}</p>", unsafe_allow_html=True)
                    st.markdown("<h5>Met Requirements:</h5>", unsafe_allow_html=True)
                    for req in data['requirement_analysis']:
                        if req['match_status']: st.markdown(f"<small>✅ {req['requirement']}</small>", unsafe_allow_html=True)
                    st.markdown("<hr style='border-color:var(--border-color)'>", unsafe_allow_html=True)
                col_index += 1
        elif len(st.session_state.compare_list) > 0:
            st.info("Select at least two candidates to compare their profiles.")

    with tabs[2]:
        st.markdown("<h3 class='section-header'>✉️ Email Generation Center</h3>", unsafe_allow_html=True)
        if st.session_state.candidates and any("Error:" not in c['name'] for c in st.session_state.candidates):
            email_cols = st.columns(2)
            with email_cols[0]:
                st.markdown("<h5>Configuration</h5>", unsafe_allow_html=True)
                max_candidates = len([c for c in st.session_state.candidates if "Error:" not in c['name']])
                num_to_invite = st.slider("Number of top candidates to invite", 1, max_candidates, min(3, max_candidates))
                min_score = st.slider("Minimum score to invite", 0, 100, 75)
            with email_cols[1]:
                st.markdown("<h5>Interview Scheduling</h5>", unsafe_allow_html=True)
                interview_date = st.date_input("Interview Date")
                interview_time = st.time_input("Interview Time")
            if st.button("Generate All Emails", use_container_width=True, type="primary"):
                with st.spinner("Crafting personalized emails..."):
                    interview_datetime_str = f"{interview_date.strftime('%A, %B %d, %Y')} at {interview_time.strftime('%I:%M %p')}"
                    st.session_state.generated_emails = generate_email_templates(st.session_state.candidates, {"title": st.session_state.saved_job_description}, num_to_invite, min_score, interview_datetime_str, st.session_state.llm)
            if 'generated_emails' in st.session_state:
                st.markdown("<hr style='border-color:var(--border-color); margin: 2rem 0;'>", unsafe_allow_html=True)
                invite_col, reject_col = st.columns(2)
                with invite_col:
                    st.markdown("<h4>✅ Invitations</h4>", unsafe_allow_html=True)
                    if st.session_state.generated_emails['invitations']:
                        for email in st.session_state.generated_emails['invitations']:
                            with st.expander(f"To: {email['name']}", expanded=True): st.code(email['email_body'], language=None)
                    else: st.info("No candidates met the criteria for an invitation.")
                with reject_col:
                    st.markdown("<h4>❌ Rejections</h4>", unsafe_allow_html=True)
                    if st.session_state.generated_emails['rejections']:
                        for email in st.session_state.generated_emails['rejections']:
                            with st.expander(f"To: {email['name']}", expanded=True): st.code(email['email_body'], language=None)
                    else: st.info("No remaining candidates to send rejection emails to.")
        else:
            st.info("There are no valid candidate results to generate emails for.")

st.markdown('</div>', unsafe_allow_html=True)