import json
from typing import List, Dict, Any, Optional
import PyPDF2
from pydantic import BaseModel, Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

def clean_llm_output(text: str) -> str:
    """Cleans the raw text output from the LLM, removing markdown fences."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def call_llm(llm: BaseChatModel, prompt_template: str, input_data: Dict[str, Any], response_model: Optional[BaseModel] = None) -> Any:
    """Invokes the LLM with structured output enforcement if a model is provided."""
    try:
        chain = ChatPromptTemplate.from_template(prompt_template)
        if response_model:
            structured_llm = llm.with_structured_output(response_model)
            chain = chain | structured_llm
        else:
            chain = chain | llm
        
        response = chain.invoke(input_data)
        return response
    except Exception as e:
        raise Exception(f"LLM invocation failed: {e}")

def repair_and_parse_json(llm: BaseChatModel, broken_json_string: str) -> Optional[Dict]:
    """Attempts to repair a broken JSON string using an LLM."""
    repair_prompt = f"""
    The following string is a broken JSON object. It likely contains unescaped newlines or other syntax errors.
    Your task is to fix it and return ONLY the perfectly valid JSON object. Do not add any explanation, commentary, or markdown formatting.

    Broken JSON:
    ```
    {broken_json_string}
    ```
    """
    try:
        repaired_response = call_llm(llm, repair_prompt, {}, response_model=None)
        repaired_json_string = clean_llm_output(repaired_response.content if hasattr(repaired_response, 'content') else str(repaired_response))
        return json.loads(repaired_json_string)
    except Exception as e:
        print(f"JSON repair failed: {e}")
        return None

class RequirementMatch(BaseModel):
    requirement: str
    match_status: bool
    evidence: str

class ExplainableCandidateScore(BaseModel):
    name: str
    overall_score: int
    summary: str
    requirement_analysis: List[RequirementMatch]

class KeyRequirements(BaseModel):
    key_requirements: List[str]

class InterviewQuestions(BaseModel):
    behavioral: List[str]
    technical: List[str]

def extract_key_requirements(job_description: str, llm: BaseChatModel) -> List[str]:
    """Extracts the most critical requirements from a job description."""
    prompt = """
    You are an expert HR analyst. Analyze the following job description and extract the 5-7 most critical, specific, and non-generic requirements. 
    Focus on quantifiable experience, specific technologies, and mandatory certifications.

    Job Description:
    {jd}
    """
    response = call_llm(llm, prompt, {"jd": job_description}, response_model=KeyRequirements)
    return response.key_requirements

def score_candidate_explainable(job_description: str, resume_text: str, weighted_requirements: Dict, llm: BaseChatModel) -> ExplainableCandidateScore:
    """Scores a candidate with detailed, explainable AI using a reliable two-step approach."""
    prompt = """
    **TASK:** Evaluate a candidate's resume against a job description and weighted requirements.
    Your output MUST be a single, valid JSON object. Do not include any other text or markdown.
    
    **CANDIDATE NAME:** The name of the candidate is present in the resume text. You must extract it for the 'name' field.

    **SCORING RULES:**
    1. Start at 100 points.
    2. For each requirement, if no direct evidence is found in the resume, deduct points:
        - Critical: -25 points
        - Important: -15 points
        - Normal: -5 points
    3. The `overall_score` is the final calculated score.

    **JSON OUTPUT SCHEMA:**
    You must fill out this exact JSON structure:
    ```json
    {{
      "name": "string, extracted from resume",
      "overall_score": "integer, calculated from rubric",
      "summary": "string, 2-3 sentence critical analysis of candidate's fit, highlighting gaps",
      "requirement_analysis": [
        {{
          "requirement": "string, from the list below",
          "match_status": "boolean, must be true or false",
          "evidence": "string, direct quote from resume or 'No direct evidence found in the resume.'"
        }}
      ]
    }}
    ```

    **USER-PROVIDED DATA:**
    1. WEIGHTED REQUIREMENTS: {weights}
    2. JOB DESCRIPTION: {jd}
    3. RESUME TEXT: {resume}
    """
    input_data = {
        "weights": json.dumps(weighted_requirements, indent=2),
        "jd": job_description,
        "resume": resume_text[:6000]
    }
    try:
        raw_response = call_llm(llm, prompt, input_data, response_model=None)
        raw_json_string = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
        cleaned_json_string = clean_llm_output(raw_json_string)
        parsed_data = json.loads(cleaned_json_string)
        return ExplainableCandidateScore(**parsed_data)
    except Exception as e:
        print(f"Error scoring candidate, re-raising exception. Error: {e}")
        raise e

def generate_interview_questions(candidate_name: str, candidate_summary: str, job_description: str, llm: BaseChatModel) -> InterviewQuestions:
    """Generates tailored interview questions using a reliable two-step approach with a repair mechanism."""
    prompt = """
    **Task:** Generate interview questions for a candidate.

    **Candidate Name:** {name}
    **Candidate AI Summary:** {summary}
    **Job Description:** {jd}

    **Your Output MUST be a single, valid JSON object with two keys:**
    1.  `"behavioral"`: A list of 3-4 behavioral questions.
    2.  `"technical"`: A list of 2-3 technical questions.

    Do not add any text before or after the JSON object.
    """
    input_data = {"name": candidate_name, "summary": candidate_summary, "jd": job_description}
    try:
        raw_response = call_llm(llm, prompt, input_data, response_model=None)
        raw_json_string = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
        cleaned_json_string = clean_llm_output(raw_json_string)
        
        try:
            parsed_data = json.loads(cleaned_json_string)
        except json.JSONDecodeError:
            print(f"Initial JSON parsing failed for {candidate_name}. Attempting to repair...")
            parsed_data = repair_and_parse_json(llm, cleaned_json_string)
            if not parsed_data:
                raise ValueError("JSON repair failed.")
        
        return InterviewQuestions(**parsed_data)
    except Exception as e:
        print(f"Could not generate interview questions for {candidate_name}. Error: {e}")
        return InterviewQuestions(
            behavioral=["Could not generate behavioral questions due to a persistent AI formatting error."],
            technical=["Please try again or rephrase the analysis."]
        )

def generate_email_templates(ranked_candidates: list, job_description: dict, num_to_invite: int, min_score: int, interview_datetime: str, llm: BaseChatModel) -> dict:
    """Generates personalized interview invitation and rejection emails with scheduling details."""
    invitations, rejections = [], []
    job_title = job_description.get('title', 'the position')
    
    candidates_to_invite = [c for c in ranked_candidates if c.get('overall_score', 0) >= min_score][:num_to_invite]
    invited_names = {c['name'] for c in candidates_to_invite}

    for candidate in ranked_candidates:
        candidate_name = candidate.get("name", "Candidate")
        if "Error:" in candidate_name: continue

        if candidate_name in invited_names:
            prompt = f"As a friendly HR manager, write a concise, enthusiastic email to {candidate_name} for the {job_title} role. Invite them for a 1-hour virtual interview on {interview_datetime}. Ask them to confirm their availability."
            email_type = "invitation"
        else:
            prompt = f"As a polite HR manager, write a brief, respectful rejection email to {candidate_name} for the {job_title} role. Thank them for their time and wish them luck."
            email_type = "rejection"
        
        try:
            email_response = call_llm(llm, prompt, {}, response_model=None)
            email_body = email_response.content if hasattr(email_response, 'content') else str(email_response)
            email_template = {"name": candidate_name, "email_body": email_body}
            if email_type == "invitation": invitations.append(email_template)
            else: rejections.append(email_template)
        except Exception as e:
            print(f"Error generating email for {candidate.get('name')}: {e}")

    return {"invitations": invitations, "rejections": rejections}

def extract_pdf_text(file_object: Any) -> str:
    """Extracts text from an in-memory PDF file object."""
    try:
        pdf_reader = PyPDF2.PdfReader(file_object)
        return "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

def create_candidate_rag_retriever(resume_text: str, filename: str):
    """Creates an in-memory RAG pipeline for a SINGLE candidate's resume."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.create_documents([resume_text], metadatas=[{"source": filename}])
    embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    vectorstore = FAISS.from_documents(documents=splits, embedding=embeddings)
    return vectorstore.as_retriever()

def ask_rag_question(retriever, question: str, llm: BaseChatModel) -> str:
    """Asks a question to the RAG pipeline."""
    template = "Answer the question based ONLY on the provided context.\n\nContext:\n{context}\n\nQuestion: {input}"
    prompt = ChatPromptTemplate.from_template(template)
    document_chain = create_stuff_documents_chain(llm, prompt)
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    
    response = retrieval_chain.invoke({"input": question})
    return response["answer"]