import os, json, tempfile
from typing import List, Dict, Any, Optional

import PyPDF2
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

from langchain_groq import ChatGroq

groq_api_key = st.secrets.get("GROQ_API_KEY", None)
if not groq_api_key:
    st.error("GROQ_API_KEY not found in secrets.")

llm = ChatGroq(model="gemma2-9b-it", temperature=0, max_tokens=None, timeout=None, max_retries=2)

def clean_llm_output(text: str) -> str:
    text = text.strip()
    # Remove code fences if present.
    if text.startswith("```") and text.endswith("```"):
        text = text.strip("`").replace("json", "", 1).strip()
    return text

# --- Pydantic Models ---

class CandidateScore(BaseModel):
    name: str
    relevance: int
    experience: int
    skills: int
    overall: int
    comment: str

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
    if job_description.startswith("http"):
        try:
            result = llm.client.scrape_url(job_description, params={"formats": ["markdown"]})
            if not result or "markdown" not in result:
                raise ValueError("Scraping did not return markdown data.")
            job_desc_text = result.get("markdown", "")
        except Exception as e:
            raise Exception(f"Failed to scrape the job description URL: {e}")
    else:
        job_desc_text = job_description
    resumes = [file.name for file in resume_files]
    return {"job_description": job_desc_text, "resumes": resumes}

def call_llm(messages: List[Dict[str, Any]], response_format: Optional[Any] = None) -> str:
    if response_format:
        messages[0]["content"] += f"\nReturn output in strict valid JSON matching this schema: {response_format.schema()}"
    try:
        response = llm.invoke(messages)
    except Exception as e:
        raise Exception(f"LLM invocation failed: {e}")
    result = clean_llm_output(response.content)
    # If empty, raise, so you catch this.
    if not result.strip():
        raise ValueError("LLM output was empty.")
    return result

def parse_job_description(data: Dict[str, Any]) -> Dict[str, Any]:
    job_text = data.get("job_description", "")
    if not job_text: raise ValueError("No job description text provided.")
    prompt = (
        "Extract key job information from the text below. "
        "Return strict, valid JSON with keys: title, company, location, requirements, responsibilities, benefits, experience. "
        "Missing values should be set to null or empty as appropriate. No extra information.\n\nJob description:\n" + job_text
    )
    messages = [
        {"role": "system", "content": "You are an assistant that extracts job description details. Return only the job details in valid JSON format."},
        {"role": "user", "content": prompt},
    ]
    llm_output = call_llm(messages, response_format=JobDescription)
    try:
        return json.loads(llm_output)
    except Exception as e:
        # Show the response text in error
        raise Exception(f"Error parsing job description: {e}\nRaw LLM output: {llm_output}")

def extract_pdf_text(file) -> str:
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        pdf_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    except Exception as e:
        pdf_text = ""
    return pdf_text

def parse_resumes(resume_files: List[Any]) -> Dict[str, Any]:
    parsed_resumes = []
    for resume in resume_files:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(resume.read())
                temp_path = temp_file.name
            with open(temp_path, "rb") as file:
                pdf_text = extract_pdf_text(file)

            if not pdf_text.strip():
                raise ValueError("No text could be extracted from this PDF. "
                                 "Is it a scanned image? Try uploading a machine-readable/resume PDF.")

            messages = [
                {
                    "role": "system",
                    "content": "Extract candidate's details from resume below into VALID JSON with keys: name, work_experiences (list), location, skills (list), education (list), summary (str, optional), certifications (list, optional), languages (list, optional). Don't hallucinate if info is missing; leave empty.",
                },
                {"role": "user", "content": f"RESUME TEXT:\n{pdf_text[:3500]}\n---END---"},
            ]
            llm_response = call_llm(messages, response_format=Resume)
            parsed_resume = json.loads(llm_response)
        except Exception as e:
            parsed_resume = {"error": f"Failed to parse resume: {e}"}
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        parsed_resumes.append(parsed_resume)
    return {"parsed_resumes": parsed_resumes}

def score_candidates(parsed_requirements: Dict[str, Any], parsed_resumes: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidate_scores = []
    job_description_text = json.dumps(parsed_requirements)
    resume_list = parsed_resumes.get("parsed_resumes", [])
    for candidate in resume_list:
        if 'error' in candidate:
            candidate_scores.append({
                "name": "Unknown",
                "relevance": 0,
                "experience": 0,
                "skills": 0,
                "overall": 0,
                "comment": candidate['error'],
                "resume": candidate
            })
            continue
        messages = [
            {
                "role": "system",
                "content": "Compare the job description with the candidate resume and assign scores: relevance (0-100), experience (0-100), skills (0-100), overall (0-100), comment. Return VALID JSON.",
            },
            {
                "role": "user",
                "content": f"Job Description:\n{job_description_text}\n\nCandidate Resume:\n{json.dumps(candidate)}",
            },
        ]
        try:
            llm_response = call_llm(messages, response_format=CandidateScore)
            score_data = json.loads(llm_response)
            score_data["resume"] = candidate
        except Exception as e:
            score_data = {
                "name": candidate.get("name", "Unknown"),
                "relevance": 0,
                "experience": 0,
                "skills": 0,
                "overall": 0,
                "comment": f"Error in parsing response: {e}",
                "resume": candidate
            }
        candidate_scores.append(score_data)
    return candidate_scores

def rank_candidates(candidate_scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for candidate in candidate_scores:
        relevance = candidate.get("relevance", 0)
        experience = candidate.get("experience", 0)
        skills = candidate.get("skills", 0)
        overall = candidate.get("overall", 0)
        candidate["avg_score"] = (relevance + experience + skills + overall) / 4.0
    return sorted(candidate_scores, key=lambda x: x["avg_score"], reverse=True)

def generate_email_templates(ranked_candidates: List[Dict[str, Any]], job_description: Dict[str, Any], top_x: int) -> Dict[str, List[Dict[str, Any]]]:
    invitations, rejections = [], []
    for idx, candidate in enumerate(ranked_candidates):
        candidate_name = candidate.get("name", "Candidate")
        messages = [
            {"role": "system", "content": "You are a professional HR representative. Please craft an email response for the candidate based on the evaluation."},
            {
                "role": "user",
                "content": (
                    f"Job Description:\n{json.dumps(job_description, indent=2)}\n\n"
                    f"Candidate Evaluation:\n{json.dumps(candidate, indent=2)}\n\n"
                )
            },
        ]
        if idx < top_x:
            messages.append({"role": "assistant", "content": "Create an invitation email."})
        else:
            messages.append({"role": "assistant", "content": "Create a polite rejection email."})
        try:
            email_body = call_llm(messages, response_format=None)
        except Exception as e:
            email_body = f"Error generating email: {e}"
        email_template = {"name": candidate_name, "email_body": email_body}
        if idx < top_x:
            invitations.append(email_template)
        else:
            rejections.append(email_template)
    return {"invitations": invitations, "rejections": rejections}
