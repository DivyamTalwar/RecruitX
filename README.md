<div align="center">
  <img src="https://raw.githubusercontent.com/DivyamTalwar/AI-Hiring-Agent/main/Images/Logo.png" alt="RecruitX Banner" width="100%"/>
  <h1 style="font-weight: bold; margin-top: 20px; font-size: 64px; text-shadow: 4px 4px 20px #007BFF;">
    RecruitX
  </h1>
  <a href="https://git.io/typing-svg"><img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=24&pause=1000&color=007BFF&width=600&lines=The+Future+of+Hiring.;AI-Powered+Talent+Analysis.;From+Resumes+to+Revenue+in+Minutes." alt="Typing SVG" /></a>
</div>

<p align="center">
    <a href="https://github.com/DivyamTalwar/AI-Hiring-Agent" target="_blank"><img src="https://img.shields.io/github/stars/DivyamTalwar/AI-Hiring-Agent?style=for-the-badge&logo=github&color=gold" alt="Stars"/></a>
    <a href="https://github.com/DivyamTalwar/AI-Hiring-Agent/network/members" target="_blank"><img src="https://img.shields.io/github/forks/DivyamTalwar/AI-Hiring-Agent?style=for-the-badge&logo=github&color=blue" alt="Forks"/></a>
    <a href="https://github.com/DivyamTalwar/AI-Hiring-Agent/issues" target="_blank"><img src="https://img.shields.io/github/issues/DivyamTalwar/AI-Hiring-Agent?style=for-the-badge&logo=github&color=red" alt="Issues"/></a>
    <a href="https://github.com/DivyamTalwar/AI-Hiring-Agent/blob/main/LICENSE" target="_blank"><img src="https://img.shields.io/github/license/DivyamTalwar/AI-Hiring-Agent?style=for-the-badge&color=brightgreen" alt="License"/></a>
    <br>
    <img src="https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python" alt="Python Version"/>
    <img src="https://img.shields.io/badge/Streamlit-UI-red?style=for-the-badge&logo=streamlit" alt="Streamlit"/>
    <img src="https://img.shields.io/badge/LangChain-Core-black?style=for-the-badge" alt="LangChain"/>
    <img src="https://img.shields.io/badge/Status-Beta-purple?style=for-the-badge" alt="Status"/>
</p>

---

<table width="100%">
  <tr>
    <td align="center" width="33%">
      <h3>🎯 Explainable AI Scoring</h3>
      <p>Go beyond numbers with detailed, evidence-based candidate evaluations.</p>
    </td>
    <td align="center" width="33%">
      <h3>💬 Interactive RAG Chat</h3>
      <p>Dynamically "interview" resumes to probe for specific skills and experience.</p>
    </td>
    <td align="center" width="33%">
      <h3>⚡ 95% Faster Screening</h3>
      <p>Compress days of manual review into a focused, 5-minute AI-driven analysis.</p>
    </td>
  </tr>
</table>

---

> ### **📜 The Manifesto: Hiring is a high-stakes intelligence problem.**
> The traditional hiring process is broken. It's a chaotic storm of biased intuition, manual drudgery, and missed opportunities. Recruiters drown in resumes while top candidates slip through the cracks. **RecruitX** is the lighthouse in the storm. It is an autonomous, AI-driven hiring agent designed to dissect talent with surgical precision. By leveraging advanced language models and a sophisticated analysis engine, RecruitX transforms recruitment from a game of chance into a science of strategic talent acquisition. We don't just find candidates. We identify future cornerstones of your organization.

---

### **🎬 The System in Action**
<div align="center">
  <p>A seamless, intuitive workflow guiding you from job description to final decision.</p>
  <img src="https://raw.githubusercontent.com/DivyamTalwar/AI-Hiring-Agent/main/Images/FlowChart.png" alt="RecruitX Workflow" width="90%"/>
</div>

---

### **🧠 The Architecture: An Intelligence-Augmented Workflow**
RecruitX is engineered as a multi-stage, AI-native application. It employs a sophisticated pipeline that combines structured data extraction, explainable scoring, and dynamic, on-the-fly reasoning to deliver unparalleled insights into your talent pool.

<details>
<summary><strong>🏛️ Click to Explore the Core Architectural Pillars</strong></summary>

| Pillar | Description | Technical Implementation |
| :--- | :--- | :--- |
| **1. Requirement Extraction** | The system first atomizes a complex job description into its most critical, non-negotiable requirements. | An LLM call guided by a `Pydantic` model (`KeyRequirements`) ensures a structured, reliable list of core competencies is extracted. |
| **2. Explainable Scoring (XAI)** | Each candidate is scored against the weighted requirements. Crucially, every point deduction is justified with evidence (or lack thereof) directly from the resume. | The `score_candidate_explainable` function uses a detailed prompt and a `Pydantic` model (`ExplainableCandidateScore`) to force the LLM to "show its work," providing a transparent audit trail for every decision. |
| **3. Per-Candidate RAG** | A unique Retrieval-Augmented Generation (RAG) pipeline is dynamically created for each candidate. This allows for a deep, interactive "chat" with their resume. | `FAISS` vector stores are built in-memory for each resume, powered by `FastEmbedEmbeddings`. This enables a `LangChain` retrieval chain to answer nuanced questions with pinpoint accuracy, based solely on the candidate's document. |
| **4. Automated Communication** | The system generates personalized email drafts for interview invitations and rejections based on the final rankings and user-defined criteria. | LLM-generated text is used to craft context-aware emails, saving hours of manual writing and ensuring a professional candidate experience. |

</details>

<div align="center">
  <h3>The RecruitX Intelligence Flow</h3>
  <img src="https://raw.githubusercontent.com/DivyamTalwar/AI-Hiring-Agent/main/Images/Img.png" alt="RecruitX Intelligence Flow" width="90%"/>
  <p><em>From raw data to actionable intelligence, orchestrated by LangChain and Streamlit.</em></p>
</div>

---

### **✨ Code Spotlight: The Anatomy of Explainable Scoring**
This is where RecruitX transcends simple keyword matching. The system forces the AI to justify its entire reasoning process, providing a clear, auditable analysis for every candidate.

```python
# SourceCode/utils.py (Illustrative Snippet)
class RequirementMatch(BaseModel):
    requirement: str
    match_status: bool
    evidence: str

class ExplainableCandidateScore(BaseModel):
    name: str
    overall_score: int
    summary: str
    requirement_analysis: List[RequirementMatch]

def score_candidate_explainable(
    job_description: str, 
    resume_text: str, 
    weighted_requirements: Dict, 
    llm: BaseChatModel
) -> ExplainableCandidateScore:
    """
    Scores a candidate with detailed, explainable AI using a reliable two-step approach.
    """
    prompt = """
    **TASK:** Evaluate a candidate's resume against a job description and weighted requirements.
    Your output MUST be a single, valid JSON object.

    **SCORING RULES:**
    1. Start at 100 points.
    2. For each requirement, if no direct evidence is found, deduct points based on importance.
    3. The `overall_score` is the final calculated score.

    **JSON OUTPUT SCHEMA:** You must fill out the ExplainableCandidateScore structure...
    
    **USER-PROVIDED DATA:**
    1. WEIGHTED REQUIREMENTS: {weights}
    2. JOB DESCRIPTION: {jd}
    3. RESUME TEXT: {resume}
    """
    # The magic happens here: LangChain's `with_structured_output`
    # binds the LLM's response to our Pydantic model.
    structured_llm = llm.with_structured_output(ExplainableCandidateScore)
    chain = ChatPromptTemplate.from_template(prompt) | structured_llm
    
    response = chain.invoke({
        "weights": json.dumps(weighted_requirements),
        "jd": job_description,
        "resume": resume_text[:6000] # Truncate for context window
    })
    
    return response
```

---

### **💻 The Arsenal: A Symphony of Elite Technology**
This project is built with a modern, powerful, and efficient technology stack, chosen for performance and developer experience.

| Category | Technology | Why We Chose It |
| :--- | :--- | :--- |
| 🚀 **AI Orchestration** | `LangChain` | The premier framework for composing LLM-powered applications, from simple chains to complex RAG systems. |
| 🧠 **LLM & Embeddings**| `Groq / Llama 3` | For world-class reasoning at blazing-fast speeds. |
| | `FastEmbed / BAAI` | High-performance, lightweight, and accurate sentence embeddings that run locally. |
| 🗂️ **Vector Storage** | `FAISS` | Facebook AI's battle-tested library for efficient in-memory similarity search. Perfect for dynamic RAG. |
| 🖥️ **Frontend** | `Streamlit` | The fastest way to build beautiful, interactive data and AI applications in Python. |
| ⚙️ **Core & Backend** | `Python` | The lingua franca of AI. Fast, powerful, and supported by a massive ecosystem. |
| | `Pydantic` | For robust data validation and ensuring structured, reliable outputs from the LLM. |
| 📄 **Document Parsing**| `PyPDF2` | A pure-python library for extracting text content from PDF resumes. |

---

### **📈 The Roadmap: Charting the Future**
- ✅ **Phase 1:** Core XAI Scoring Engine & RAG Chat
- ✅ **Phase 2:** Multi-Candidate Comparison & Email Generation
- 💡 **Phase 3:** Deeper ATS Integration & API Endpoints
- 🚀 **Phase 4:** Long-term Candidate Memory & Cross-Role Analysis
- 🌐 **Phase 5:** Fully Autonomous Mode: AI sources, screens, and schedules interviews.

---

### **🛠️ Ignition Sequence: Activate RecruitX**

#### 1. **Clone the Repository**
```bash
git clone https://github.com/DivyamTalwar/AI-Hiring-Agent.git
cd AI-Hiring-Agent
```

#### 2. **Set Up the Environment**
```bash
python -m venv venv
# On Windows: venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

#### 3. **Configure API Keys**
Create a `.streamlit/secrets.toml` file. This is your configuration hub.
```toml
# .streamlit/secrets.toml
GROQ_API_KEY="gsk_..."
```

#### 4. **Execute**
```bash
streamlit run app.py
```

---

### **🤝 Call to Arms: Join the Revolution**
This is more than a project; it's a new paradigm for talent acquisition. If you are an engineer, a recruiter, or a data scientist, your contributions are vital.
*   **⭐ Star the project** to show your support for the future of hiring.
*   **🍴 Fork the repo** and submit a PR with your enhancements.
*   **💡 Open an issue** with new ideas, bug reports, or feature requests.
*   **🤖 Integrate a new LLM** or a different vector database.

---

<p align="center">
  <a href="https://github.com/DivyamTalwar">
    <img src="https://github-readme-stats.vercel.app/api?username=DivyamTalwar&theme=merko&hide_border=false&include_all_commits=true&count_private=true&bg_color=00000000&border_color=00000000" alt="Divyam's GitHub Stats"/>
    <img src="https://nirzak-streak-stats.vercel.app/?user=DivyamTalwar&theme=merko&hide_border=false&background=00000000&border=00000000" alt="Divyam's GitHub Streak"/>
  </a>
</p>
