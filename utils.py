import os
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

load_dotenv()

FireCrawlApiKey = st.secrets["FIRECRAWL_API_KEY"]
GroqApiKey = st.secrets["GROQ_API_KEY"]

app = FirecrawlApp(api_key=FireCrawlApiKey)
groq_client = Groq(api_key=GroqApiKey)


'''This model represents the score for a candidate. It uses Pydantic to ensure that the data fits the specified types.
here we had just defined the Pydantic MODEL which specifies the fields,datatypes,description.it is simply a DataStructure ensuring
CandidateScore matches the correct format'''
class CandidateScore(BaseModel):
    name: str = Field(..., description="Candidate's name")
    relevance: int = Field(..., description="How relevant the candidate's resume is to the job description (0-100)")
    experience: int = Field(..., description="Candidate's match in terms of work experience (0-100)")
    skills: int = Field(..., description="Candidate's match based on skills (0-100)")
    overall: int = Field(..., description="Overall score (0-100)")
    comment: str = Field(..., description="A brief comment explaining the rationale behind the scores")


'''This model defines the expected structure for a candidate’s resume.
This only defines the structure of how a resume should be formatted.'''
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


'''This Func processes a job description (either as plain text or a URL) and extracts resume file names from a given list of uploaded 
resume files
It returns a dictionary containing:
job_description" → Contains either : The scraped markdown text (if a URL was provided) | The original text (if it was not a URL).
"resumes" → A list of resume file names.'''
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


"""Calls OpenAI's GPT-4o model using a provided list of chat messages.
Returns the response text from the AI.
response_format: Optional => This is an optional parameter that specifies the expected output format(none of Json)"""
async def call_llm(messages: List[Dict[str, str]]) -> str:
    try:
        response = await groq_client.chat.completions.create(messages=messages)
        return response['choices'][0]['message']['content']
    except Exception as e:
        raise ValueError(f"Error calling LLM: {e}")

"""This function processes a raw job description (either input manually or scraped from a webpage) and extracts key details in 
a structured format using a Large Language Model (LLM) like GPT-4.Returns a clean JSON output with important job details
data AS DEFINED IN THE JobDescription MODEL DEFINED USING PYDANTIC : dictionary containing JD Under JD as key
Here we have given a raw job description and what we did is we took the entire job description as arguement under the key
job description and using LLM we defined it into a structed MANNER that we had defined using pydantic model"""
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
        llm_output = call_llm(messages)
        structured_jd = json.loads(llm_output)
    except Exception as e:
        raise Exception(f"Error parsing job description: {e}")

    return structured_jd


"""from uploaded PDF files, extracts their text, and uses an LLM (GPT-4) to extract structured candidate information like name, 
experience, skills, education, etc.. AS DEFINED IN RESUME MODEL It then returns the extracted details in a JSON format.
LLMs cannot directly read uploaded files, so we save them temporarily and extract text from them."""
async def parse_resumes(resume_files: List[Any]) -> Dict[str, Any]:
    parsed_resumes = []

    for resume in resume_files:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_file:
            temp_file.write(resume.read())
            temp_path = temp_file.name

        with open(temp_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            pdf_text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)

        messages = [
            {"role": "system", "content": "You extract structured candidate resume data in JSON format."},
            {"role": "user", "content": f"Extract details from the following resume:\n\n{pdf_text}"},
        ]

        try:
            llm_response = call_llm(messages)
            parsed_resume = json.loads(llm_response)
        except Exception as e:
            parsed_resume = {"error": f"Failed to parse resume using LLM: {e}"}

        parsed_resumes.append(parsed_resume) #Adds the extracted resume details to the parsed_resumes list.

    return {"parsed_resumes": parsed_resumes}


"""Takes a parsed job description and a list of parsed resumes as input. It uses a language model (LLM) to compare each resume 
with the job description and assigns scores based on relevance, experience, and skills. The function then returns a structured 
list of scored candidates.
We convert the job description dictionary to a JSON string because LLMs process text-based input, and JSON preserves the 
structured key-value relationships for better interpretation.JSON is universally recognized by APIs and AI models"""
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
            llm_response = call_llm(messages)
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

"""This function takes a list of candidate scores, calculates an average score for each candidate, and ranks them in descending 
order based on their average score."""
def rank_candidates(candidate_scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for candidate in candidate_scores:
        relevance = candidate.get("relevance", 0) #default value to 0 if key not found 
        experience = candidate.get("experience", 0)
        skills = candidate.get("skills", 0)
        overall = candidate.get("overall", 0)
        candidate["avg_score"] = (relevance + experience + skills + overall) / 4.0
        
    sorted_candidates = sorted(candidate_scores, key=lambda x: x["avg_score"], reverse=True)
    return sorted_candidates


"""This function generates email templates for candidates based on their ranking.
    Top candidates get invitation emails for a follow-up call.
    Other candidates get polite rejection emails with feedback.
    top_x → The number of top-ranked candidates to invite."""
async def generate_email_templates(
    ranked_candidates: List[Dict[str, Any]],
    job_description: Dict[str, Any],
    top_x: int
) -> Dict[str, List[Dict[str, Any]]]:
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
            email_body = call_llm(base_messages)
        except Exception as e:
            email_body = f"Error generating email: {e}"

        email_template = {"name": candidate_name, "email_body": email_body}
        if idx < top_x:
            invitations.append(email_template)
        else:
            rejections.append(email_template)

    return {"invitations": invitations, "rejections": rejections}
