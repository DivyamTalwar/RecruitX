import os
from typing import List, Dict, Any, Optional
import json
import tempfile
import PyPDF2
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

from langchain_groq import ChatGroq

# Initialize ChatGroq using API key from st.secrets
groq_api_key = st.secrets.get("GROQ_API_KEY")
if not groq_api_key:
    st.error("GROQ_API_KEY not found in secrets.")

llm = ChatGroq(
    model="llama3-8b-8192",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# Define Pydantic models for structured responses
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
    summary: Optional[str] = None
    certifications: Optional[List[str]] = None
    languages: Optional[List[str]] = None

class JobDescription(BaseModel):
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    requirements: List[str]
    responsibilities: List[str]
    benefits: List[str]
    experience: Optional[str] = None

def ingest_inputs(job_description: str, resume_files: List[Any]) -> Dict[str, Any]:
    if job_description.startswith("http"):
        try:
            # Scrape the job description if URL is provided.
            result = llm.client.scrape_url(job_description, params={"formats": ["markdown"]})
            if not result or "markdown" not in result:
                raise ValueError("Scraping did not return markdown data.")
            job_desc_text = result["markdown"]
        except Exception as e:
            raise Exception(f"Failed to scrape the job description URL: {e}")
    else:
        job_desc_text = job_description

    resumes = [file.name for file in resume_files]
    return {"job_description": job_desc_text, "resumes": resumes}

def call_llm(messages: List[Dict[str, Any]], response_format: Optional[Any] = None) -> str:
    if response_format:
        messages[0]["content"] += f"\nReturn output in JSON matching this schema: {response_format.schema()}"
    
    try:
        response = llm.invoke(messages)
        raw_content = response.content
        
        # Remove unnecessary formatting artifacts (e.g., markdown block quotes).
        clean_output = raw_content.strip().replace("```json", "").replace("```", "").strip()
        
        # Check and ensure it's valid JSON
        if not clean_output.startswith("{"):
            raise ValueError("Output is not recognized as valid JSON.")

        return clean_output
    except Exception as e:
        raise Exception(f"LLM invocation failed: {e}. Raw response: {raw_content}")

def parse_job_description(data: Dict[str, Any]) -> Dict[str, Any]:
    job_text = data.get("job_description", "")
    if not job_text:
        raise ValueError("No job description text provided.")
    
    prompt = (
        "Extract key job information from the text below. "
        "Return valid JSON with these keys: title, company, location, requirements, responsibilities, benefits, experience. "
        "If a value for a key is not available, return null instead of an empty list.\n\nJob description:\n" + job_text
    )
    
    messages = [
        {
            "role": "system",
            "content": "You are an assistant that extracts job description details. Return only the job details in valid JSON format.",
        },
        {"role": "user", "content": prompt},
    ]
    
    try:
        llm_output = call_llm(messages, response_format=JobDescription)
        structured_jd = json.loads(llm_output)
    except Exception as e:
        raise Exception(f"Error parsing job description: {e}\nRaw LLM output: {llm_output}")
    
    return structured_jd

def parse_resumes(resume_files: List[Any]) -> Dict[str, Any]:
    parsed_resumes = []
    for resume in resume_files:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(resume.read())
                temp_path = temp_file.name
            
            with open(temp_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pdf_text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)

            messages = [
                {
                    "role": "system",
                    "content": "Extract candidate resume details following the JSON schema.",
                },
                {
                    "role": "user",
                    "content": f"Extract resume details from the following text:\n\n{pdf_text}",
                },
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
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an unbiased hiring manager. Compare the job description with the candidate's resume "
                    "and assign scores for relevance, experience, and skills (0-100), along with an overall score and comment. "
                    "Return valid JSON."
                ),
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

def generate_email_templates(
    ranked_candidates: List[Dict[str, Any]], job_description: Dict[str, Any], top_x: int
) -> Dict[str, List[Dict[str, Any]]]:
    invitations = []
    rejections = []
    for idx, candidate in enumerate(ranked_candidates):
        candidate_name = candidate.get("name", "Candidate")
        messages = [
            {
                "role": "system",
                "content": "You are a professional HR representative. Please craft an email response for the candidate based on the evaluation."
            },
            {
                "role": "user",
                "content": (
                    f"Job Description:\n{json.dumps(job_description, indent=2)}\n\n"
                    f"Candidate Evaluation:\n{json.dumps(candidate, indent=2)}\n\n"
                )
            },
        ]
        if idx < top_x:
            messages.append({
                "role": "assistant",
                "content": "Create an invitation email inviting the candidate for a call. The tone should be friendly and professional."
            })
        else:
            messages.append({
                "role": "assistant",
                "content": "Create a polite rejection email with constructive feedback."
            })
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
