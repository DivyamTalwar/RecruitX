# utils.py
import os
from typing import List, Dict, Any, Optional
import json
import tempfile
import PyPDF2
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


from groq import GroqClient


groq_api_key = st.secrets["GROQ_API_KEY"]
groq_client = GroqClient(api_key=groq_api_key)



class CandidateScore(BaseModel):
    name: str = Field(..., description="Candidate's name")
    relevance: int = Field(..., description="How relevant the candidate's resume is to the job description (0-100)")
    experience: int = Field(..., description="Candidate's match in terms of work experience (0-100)")
    skills: int = Field(..., description="Candidate's match based on skills (0-100)")
    overall: int = Field(..., description="Overall score (0-100)")
    comment: str = Field(..., description="A brief comment explaining the rationale behind the scores")
    
class Resume(BaseModel):
    name: str = Field(..., description="Candidate's full name")
    work_experiences: List[str] = Field(..., description="List of work experiences")
    location: str = Field(..., description="Candidate's location")
    skills: List[str] = Field(..., description="List of candidate's skills")
    education: List[str] = Field(..., description="Educational background")
    summary: Optional[str] = Field(None, description="A short summary or objective statement")
    certifications: Optional[List[str]] = Field(None, description="List of certifications")
    languages: Optional[List[str]] = Field(None, description="Languages spoken by the candidate")
    
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
            # Use GROQ's scraping functionality to fetch job description in markdown format
            result = groq_client.scrape_url(job_description, params={"formats": ["markdown"]})
            if not result or "markdown" not in result:
                raise ValueError("Scraping did not return markdown data.")
            job_desc_text = result.get("markdown", "")
        except Exception as e:
            raise Exception(f"Failed to scrape the job description URL: {e}")
    else:
        job_desc_text = job_description # If not a URL, treat the text as-is
    resumes = [file.name for file in resume_files] # Extract resume file names
    return {"job_description": job_desc_text, "resumes": resumes}

def call_llm(messages: List[Dict[str, Any]], response_format: Optional[Any] = None) -> str:
    # Build parameters for the GROQ LLM call with the gemma2-9b-it model
    params = {
        "model": "gemma2-9b-it",
        "messages": messages,
    }
    if response_format:
        # Assume that the model expects a JSON schema from the Pydantic model – using a hypothetical schema() method
        params["response_format"] = response_format.schema()
    response = groq_client.chat_completion(**params)
    return response["choices"][0]["message"]["content"] # Return the generated text <sup data-citation="1" className="inline select-none [&>a]:rounded-2xl [&>a]:border [&>a]:px-1.5 [&>a]:py-0.5 [&>a]:transition-colors shadow [&>a]:bg-ds-bg-subtle [&>a]:text-xs [&>svg]:w-4 [&>svg]:h-4 relative -top-[2px] citation-shimmer"><a href="https://medium.com/@rehmanakram03/building-a-chatbot-with-groq-apis-llama-3-and-streamlit-with-deployment-on-cloud-74ef041f60d2" target="_blank" title="Building a Chatbot with GROQ APIs (Llama 3) and ...">1</a></sup><sup data-citation="8" className="inline select-none [&>a]:rounded-2xl [&>a]:border [&>a]:px-1.5 [&>a]:py-0.5 [&>a]:transition-colors shadow [&>a]:bg-ds-bg-subtle [&>a]:text-xs [&>svg]:w-4 [&>svg]:h-4 relative -top-[2px] citation-shimmer"><a href="https://ai.gopubby.com/lets-automate-candidate-screening-for-the-company-hr-dept-be794f965181" target="_blank" title="Lets Automate Candidate Screening For The Company HR Dept.">8</a></sup>

def parse_job_description(data: Dict[str, Any]) -> Dict[str, Any]:
    job_text = data.get("job_description", "")
    if not job_text:
        raise ValueError("No job description text provided.")
    prompt = (
        "Extract the key job information from the text below. "
        "Return only valid JSON with the following keys: title, company, location, requirements, responsibilities, benefits, experience. "
        "Do not include any extra information.\n\n"
        "Job description:\n" + job_text
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant that extracts key job description information from text. "
                "Return only the job details in valid JSON format with keys: title, company, location, requirements (list), responsibilities (list), benefits (list), and experience."
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
                "content": (
                    "You are an assistant that extracts candidate resume details. "
                    "Extract only the information following the JSON schema."
                ),
            },
            {
                "role": "user",
                "content": f"Extract resume details from the following resume text:\n\n{pdf_text}",
            },
        ]
        try:
            llm_response = call_llm(messages, response_format=Resume)
            parsed_resume = json.loads(llm_response)
        except Exception as e:
            parsed_resume = {"error": f"Failed to parse resume using LLM: {e}"}
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
                    "You are an unbiased hiring manager. Compare the following job description with the candidate's resume and provide "
                    "scores (0-100) for relevance, experience, and skills. Also compute an overall score that reflects the candidate's fit "
                    "and provide a comment. Return only valid JSON using the schema."
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
                "comment": f"Error in parsing response from LLM: {e}",
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
    sorted_candidates = sorted(candidate_scores, key=lambda x: x["avg_score"], reverse=True)
    return sorted_candidates

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
                "content": "You are a professional HR representative. Craft an email response based on the candidate's evaluation."
            },
            {
                "role": "user",
                "content": (
                    f"Job Description (structured):\n{json.dumps(job_description, indent=2)}\n\n"
                    f"Candidate Evaluation (structured):\n{json.dumps(candidate, indent=2)}\n\n"
                )
            },
        ]
        if idx < top_x:
            messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "Please create an invitation email inviting the candidate for a quick call. "
                        "The email should be friendly, professional, and include a scheduling request."
                    ),
                }
            )
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "Please create a polite rejection email. Include constructive feedback and suggestions for improvement "
                        "based on the candidate's evaluation."
                    ),
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
