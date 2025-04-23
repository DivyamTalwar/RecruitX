from typing import List, Dict, Any, Optional
from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import json
from pydantic import BaseModel, Field
import asyncio
import tempfile
import PyPDF2
import streamlit as st
from groq import Groq
import os

# For handling DOCX files
try:
    from docx import Document
except ImportError:
    Document = None

load_dotenv()

FireCrawlApiKey = st.secrets["FIRECRAWL_API_KEY"]
GroqApiKey = st.secrets["GROQ_API_KEY"]

app = FirecrawlApp(api_key=FireCrawlApiKey)
groq_client = Groq(api_key=GroqApiKey)

class CandidateScore(BaseModel):
    name: str = Field(..., description="Candidate's name")
    relevance: int = Field(..., description="How relevant the candidate's resume is to the job description (0-100)")
    experience: int = Field(..., description="Candidate's match in terms of work experience (0-100)")
    skills: int = Field(..., description="Candidate's match based on skills (0-100)")
    overall: int = Field(..., description="Overall score (0-100)")
    comment: str = Field(..., description="A brief comment explaining the rationale behind the scores")

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
    company: str
    location: str
    requirements: List[str]
    responsibilities: List[str]

async def ingest_inputs(job_description: str, resume_files: List[Any]) -> Dict[str, Any]:
    if job_description.startswith("http"):
        try:
            result = app.scrape_url(job_description, params={"formats": ["markdown"]})
            if not result or "markdown" not in result:
                raise ValueError("Scraping did not return markdown data.")
            job_desc_text = result.get("markdown", "")
        except Exception as e:
            raise ValueError(f"Failed to scrape the job description URL: {e}")
    else:
        job_desc_text = job_description
    resumes = [file.name for file in resume_files]
    return {"job_description": job_desc_text, "resumes": resumes}

async def call_llm(messages: List[Dict[str, str]]) -> str:
    try:
        response = await groq_client.chat.completions.create(model="gemma2-9b-it", messages=messages)
        return response['choices'][0]['message']['content']
    except Exception as e:
        raise ValueError(f"Error calling LLM: {e}")

async def parse_job_description(data: Dict[str, Any]) -> Dict[str, Any]:
    job_text = data.get("job_description", "")
    if not job_text:
        raise ValueError("No job description text provided.")

    prompt = (
        "Extract the key job information from the text below. Return only valid JSON "
        "with the following keys: title, company, location, requirements, responsibilities, benefits, experience.\n\n"
        "Job description:\n" + job_text
    )
    messages = [
        {"role": "system", "content": "You extract job details in strict JSON format."},
        {"role": "user", "content": prompt},
    ]
    try:
        llm_output = await call_llm(messages)
        structured_jd = json.loads(llm_output)
    except Exception as e:
        raise Exception(f"Error parsing job description: {e}")

    return structured_jd

async def parse_resumes(resume_files: List[Any]) -> Dict[str, Any]:
    parsed_resumes = []

    for resume in resume_files:
        file_extension = os.path.splitext(resume.name)[1].lower()
        extracted_text = ""
        if file_extension == ".pdf":
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_file:
                temp_file.write(resume.read())
                temp_file.flush()
                with open(temp_file.name, "rb") as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    extracted_text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)
        elif file_extension in [".docx", ".doc"]:
            if Document is None:
                extracted_text = "Error: python-docx is not installed to process DOCX files."
            else:
                try:
                    with tempfile.NamedTemporaryFile(delete=True, suffix=".docx") as temp_file:
                        temp_file.write(resume.read())
                        temp_file.flush()
                        doc = Document(temp_file.name)
                        paragraphs = [para.text for para in doc.paragraphs]
                        extracted_text = "\n".join(paragraphs)
                except Exception as e:
                    extracted_text = f"Error processing DOCX file: {e}"
        else:
            extracted_text = "Unsupported file format."

        messages = [
            {"role": "system", "content": "You extract structured candidate resume data in JSON format."},
            {"role": "user", "content": f"Extract details from the following resume:\n\n{extracted_text}"},
        ]
        try:
            llm_response = await call_llm(messages)
            parsed_resume = json.loads(llm_response)
        except Exception as e:
            parsed_resume = {"error": f"Failed to parse resume using LLM: {e}"}

        parsed_resumes.append(parsed_resume)

    return {"parsed_resumes": parsed_resumes}

async def score_candidates(parsed_requirements: Dict[str, Any], parsed_resumes: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidate_scores = []
    job_description_text = json.dumps(parsed_requirements)
    resume_list = parsed_resumes.get("parsed_resumes", [])

    for candidate in resume_list:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an unbiased hiring expert. Compare the job description with the candidate's resume. "
                    "Return relevance, experience, skills, and overall score (0-100) in JSON format, along with a comment."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Job Description:\n{job_description_text}\n\n"
                    f"Candidate Resume:\n{json.dumps(candidate)}"
                ),
            },
        ]
        try:
            llm_response = await call_llm(messages)
            score_data = json.loads(llm_response)
            score_data["resume"] = candidate
        except json.JSONDecodeError:
            score_data = {
                "name": candidate.get("name", "Unknown"),
                "relevance": 0,
                "experience": 0,
                "skills": 0,
                "overall": 0,
                "comment": "Error in parsing response from LLM.",
            }
        except Exception as e:
            score_data = {
                "name": candidate.get("name", "Unknown"),
                "relevance": 0,
                "experience": 0,
                "skills": 0,
                "overall": 0,
                "comment": f"Unexpected error: {e}",
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

async def generate_email_templates(ranked_candidates: List[Dict[str, Any]], job_description: Dict[str, Any], top_x: int) -> Dict[str, List[Dict[str, Any]]]:
    invitations = []
    rejections = []

    for idx, candidate in enumerate(ranked_candidates):
        candidate_name = candidate.get("name", "Candidate")
        base_messages = [
            {
                "role": "system",
                "content": (
                    "You are an unbiased HR professional. Your task is to craft clear, concise, "
                    "and professional email responses to candidates based on the job description, "
                    "the candidate's resume details, and evaluation scores. "
                    "Return only the email body as plain text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Job Description (structured):\n{json.dumps(job_description, indent=2)}\n\n"
                    f"Candidate Evaluation (structured):\n{json.dumps(candidate, indent=2)}\n\n"
                ),
            },
        ]
        if idx < top_x:
            base_messages.append({
                "role": "user",
                "content": (
                    "Please create an invitation email inviting the candidate for a quick call. "
                    "The email should be friendly, professional, and include a scheduling request."
                ),
            })
        else:
            base_messages.append({
                "role": "user",
                "content": (
                    "Please create a polite rejection email. Include constructive feedback and key "
                    "suggestions for improvement based on the candidate's evaluation."
                ),
            })
        try:
            email_body = await call_llm(base_messages)
        except Exception as e:
            email_body = f"Error generating email: {e}"
        email_template = {"name": candidate_name, "email_body": email_body}
        if idx < top_x:
            invitations.append(email_template)
        else:
            rejections.append(email_template)
    return {"invitations": invitations, "rejections": rejections}
