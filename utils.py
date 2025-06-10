import os, json
from typing import List, Dict, Any, Optional

import PyPDF2
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

groq_api_key = st.secrets.get("GROQ_API_KEY")
if not groq_api_key:
    st.error("GROQ_API_KEY not found in Streamlit secrets. The app will not function.")
    st.stop()

from langchain_groq import ChatGroq

llm = ChatGroq(
    model="gemma2-9b-it",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=groq_api_key
)

def clean_llm_output(text: str) -> str:
    """Cleans the raw text output from the LLM."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

class CandidateScore(BaseModel):
    name: str = Field(description="Full name of the candidate.")
    relevance: int = Field(description="Score from 0 to 100 for overall relevance to the job.", ge=0, le=100)
    experience: int = Field(description="Score from 0 to 100 for relevant work experience.", ge=0, le=100)
    skills: int = Field(description="Score from 0 to 100 for matching skills.", ge=0, le=100)
    overall: int = Field(description="A weighted average overall score from 0 to 100.", ge=0, le=100)
    comment: str = Field(description="A brief, one or two-sentence summary of the candidate's fit.")

class Resume(BaseModel):
    name: str
    work_experiences: List[str]
    location: str
    skills: List[str]
    education: List[str]
    summary: Optional[str]
    certifications: Optional[List[str]]
    languages: Optional[List[str]]

class JobDescription(BaseModel):
    title: str
    company: Optional[str]
    location: Optional[str]
    requirements: List[str]
    responsibilities: List[str]
    benefits: List[str]
    experience: Optional[str]

def ingest_inputs(job_description: str, resume_files: List[Any]) -> Dict[str, Any]:
    """Ingests and performs initial processing of job description and resumes."""
    if job_description.strip().startswith("http"):
        try:
            st.warning("URL scraping is a conceptual feature. Please paste the job description text for best results.")
            job_desc_text = job_description
        except Exception as e:
            raise Exception(f"Failed to scrape the job description URL: {e}")
    else:
        job_desc_text = job_description
    
    return {"job_description": job_desc_text, "resume_files": resume_files}

def call_llm(messages: List[Dict[str, Any]], response_model: Optional[BaseModel] = None) -> str:
    """Invokes the LLM with structured output formatting if a Pydantic model is provided."""
    if response_model:
        structured_llm = llm.with_structured_output(response_model)
        try:
            response = structured_llm.invoke(messages)
            result = response.json()
        except Exception as e:
            raise Exception(f"LLM invocation with structured output failed: {e}")
    else:
        try:
            response = llm.invoke(messages)
            result = clean_llm_output(response.content)
        except Exception as e:
            raise Exception(f"LLM invocation failed: {e}")

    if not result.strip():
        raise ValueError("LLM output was empty.")
    return result

def parse_job_description(job_description_text: str) -> Dict[str, Any]:
    """Parses the job description text into a structured format using an LLM."""
    if not job_description_text:
        raise ValueError("No job description text provided.")
    
    prompt = (
        "You are an expert HR analyst. Extract the key information from the following job description. "
        "Strictly adhere to the provided JSON schema. If a field is not present, use an appropriate null or empty value.\n\n"
        f"Job Description Text:\n---\n{job_description_text}"
    )
    messages = [{"role": "user", "content": prompt}]
    
    llm_output = call_llm(messages, response_model=JobDescription)
    try:
        return json.loads(llm_output)
    except json.JSONDecodeError as e:
        raise Exception(f"Error parsing job description JSON: {e}\nRaw LLM output: {llm_output}")

def extract_pdf_text(file_object: Any) -> str:
    """Extracts text from an in-memory PDF file object."""
    try:
        pdf_reader = PyPDF2.PdfReader(file_object)
        pdf_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
        return pdf_text
    except Exception as e:
        st.warning(f"Could not read a PDF file, it might be corrupted or password-protected. Error: {e}")
        return ""

def parse_resumes(resume_files: List[Any]) -> Dict[str, Any]:
    """Parses a list of uploaded resume files into structured data."""
    parsed_resumes = []
    for resume_file in resume_files:
        try:
            pdf_text = extract_pdf_text(resume_file)

            if not pdf_text.strip():
                raise ValueError(
                    "No text could be extracted from this PDF. "
                    "It might be a scanned image. Please upload a machine-readable PDF."
                )

            prompt = (
                "You are an expert resume parser. Extract the candidate's details from the resume text below. "
                "Adhere strictly to the provided JSON schema. Do not invent information; if a field is missing, use an appropriate empty value.\n\n"
                f"Resume Text (first 4000 characters):\n---\n{pdf_text[:4000]}"
            )
            messages = [{"role": "user", "content": prompt}]
            
            llm_response = call_llm(messages, response_model=Resume)
            parsed_resume = json.loads(llm_response)
            parsed_resume['filename'] = resume_file.name
        
        except Exception as e:
            parsed_resume = {"error": f"Failed to parse '{resume_file.name}': {e}", "filename": resume_file.name}
        
        parsed_resumes.append(parsed_resume)
        
    return {"parsed_resumes": parsed_resumes}

def score_candidates(parsed_job_desc: Dict[str, Any], parsed_resumes_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Scores candidates based on their parsed resume against the parsed job description."""
    candidate_scores = []
    job_description_text = json.dumps(parsed_job_desc)
    resume_list = parsed_resumes_data.get("parsed_resumes", [])

    for candidate_resume in resume_list:
        if 'error' in candidate_resume:
            score_data = {
                "name": f"Error Processing '{candidate_resume.get('filename', 'Unknown File')}'",
                "relevance": 0, "experience": 0, "skills": 0, "overall": 0,
                "comment": candidate_resume['error'],
                "resume": candidate_resume
            }
            candidate_scores.append(score_data)
            continue

        prompt = (
            "You are an expert hiring manager. Compare the candidate's resume against the job description. "
            "Provide scores on a scale of 0-100 for relevance, experience, and skills. Calculate an overall score. "
            "Add a concise comment summarizing the candidate's fit. Strictly follow the JSON schema.\n\n"
            f"Job Description:\n{job_description_text}\n\n"
            f"Candidate Resume:\n{json.dumps(candidate_resume)}"
        )
        messages = [{"role": "user", "content": prompt}]

        try:
            llm_response = call_llm(messages, response_model=CandidateScore)
            score_data = json.loads(llm_response)
            score_data["resume"] = candidate_resume
        except Exception as e:
            score_data = {
                "name": candidate_resume.get("name", "Unknown"),
                "relevance": 0, "experience": 0, "skills": 0, "overall": 0,
                "comment": f"Error during scoring: {e}",
                "resume": candidate_resume
            }
        candidate_scores.append(score_data)
    return candidate_scores

def rank_candidates(candidate_scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ranks candidates based on their overall score."""
    return sorted(candidate_scores, key=lambda x: x.get("overall", 0), reverse=True)

def generate_email_templates(ranked_candidates: List[Dict[str, Any]], job_description: Dict[str, Any], top_x: int) -> Dict[str, List[Dict[str, Any]]]:
    """Generates interview invitation and rejection email templates."""
    invitations, rejections = [], []
    job_title = job_description.get('title', 'the position')

    for idx, candidate in enumerate(ranked_candidates):
        candidate_name = candidate.get("name", "Candidate")
        
        if "Error Processing" in candidate_name:
            continue

        email_type = "invitation" if idx < top_x else "rejection"
        
        if email_type == "invitation":
            prompt = (
                f"You are a friendly and professional HR manager. Write a concise and enthusiastic email to {candidate_name} "
                f"inviting them to an interview for the {job_title} role. Mention their strong profile as a key reason. "
                "Ask for their availability for a 30-minute call next week. Do not use placeholders like [Your Name] or [Company Name]."
            )
        else: # Rejection
            prompt = (
                f"You are a polite and professional HR manager. Write a brief and respectful rejection email to {candidate_name} "
                f"for the {job_title} role. Thank them for their interest and time, and mention that the decision was difficult due to a high volume "
                "of qualified applicants. Wish them luck in their job search. Do not use placeholders."
            )

        messages = [{"role": "user", "content": prompt}]
        
        try:
            email_body = call_llm(messages)
        except Exception as e:
            email_body = f"Error generating email: {e}"
            
        email_template = {"name": candidate_name, "email_body": email_body}
        
        if email_type == "invitation":
            invitations.append(email_template)
        else:
            rejections.append(email_template)
            
    return {"invitations": invitations, "rejections": rejections}