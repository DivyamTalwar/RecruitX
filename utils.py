import os
from typing import List, Dict, Any, Optional
import json
import tempfile
import PyPDF2
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

# Import the Groq-based chat model from langchain-groq
from langchain_groq import ChatGroq

# Initialize ChatGroq with the GROQ API key from Streamlit secrets.
groq_api_key = st.secrets["GROQ_API_KEY"]
llm = ChatGroq(
    model="gemma2-9b-it", 
    temperature=0, 
    max_tokens=None, 
    timeout=None, 
    max_retries=2,
)
# Note: ChatGroq automatically reads GROQ_API_KEY from the environment if set.

# Define Pydantic models for structured responses.

class CandidateScore(BaseModel):
    name: str = Field(..., description="Candidate's name")
    relevance: int = Field(..., description="Resume relevance score (0-100)")
    experience: int = Field(..., description="Candidate experience score (0-100)")
    skills: int = Field(..., description="Candidate skills match (0-100)")
    overall: int = Field(..., description="Overall score (0-100)")
    comment: str = Field(..., description="Evaluation comment")

class Resume(BaseModel):
    name: str = Field(..., description="Candidate's full name")
    work_experiences: List[str] = Field(..., description="List of work experiences")
    location: str = Field(..., description="Candidate's location")
    skills: List[str] = Field(..., description="List of candidate's skills")
    education: List[str] = Field(..., description="Educational background")
    summary: Optional[str] = Field(None, description="Short summary or objective")
    certifications: Optional[List[str]] = Field(None, description="List of certifications")
    languages: Optional[List[str]] = Field(None, description="Languages spoken")

class JobDescription(BaseModel):
    title: str
    company: str
    location: str
    requirements: List[str]
    responsibilities: List[str]
    benefits: List[str]
    experience: str

def ingest_inputs(job_description: str, resume_files: List[Any]) -> Dict[str, Any]:
    if job_description.startswith("http"):
        try:
            # Use GROQ to scrape the URL and return markdown data.
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
    # Append a note about expected schema if one is provided.
    if response_format:
        messages[0]["content"] += f"\nReturn output in JSON matching this schema: {response_format.schema()}"
    response = llm.invoke(messages)
    return response.content

def parse_job_description(data: Dict[str, Any]) -> Dict[str, Any]:
    job_text = data.get("job_description", "")
    if not job_text:
        raise ValueError("No job description text provided.")
    prompt = (
        "Extract key job information from the text below. "
        "Return valid JSON with these keys: title, company, location, requirements, responsibilities, benefits, experience. "
        "Do not include any extra information.\n\nJob description:\n" + job_text
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant that extracts job description details. "
                "Return only the job details in valid JSON format."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    try:
        llm_output = call_llm(messages, response_format=JobDescription)
        structured_jd = json.loads(llm_output)
    except Exception as e:
        raise Exception(f"Error parsing job description: {e}")
    return structured_jd

def parse_resumes(resume_files: List[Any]) -> Dict[str, Any]:
    parsed_resumes = []
    for resume in resume_files:
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
        try:
            llm_response = call_llm(messages, response_format=Resume)
            parsed_resume = json.loads(llm_response)
        except Exception as e:
            parsed_resume = {"error": f"Failed to parse resume: {e}"}
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
            messages.append(
                {
                    "role": "assistant",
                    "content": "Create an invitation email inviting the candidate for a call. The tone should be friendly and professional."
                }
            )
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": "Create a polite rejection email with constructive feedback."
                }
            )
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
