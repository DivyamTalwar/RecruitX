import os
from typing import List, Dict, Any #any indicates that variable can be of "ANY" datatype
from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import json #Imports the JSON module to encode and decode JSON strings.
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional #optional indicates that the value might be "NONE"
import asyncio
import tempfile
import PyPDF2
import streamlit as st

load_dotenv()

FireCrawlApiKey = st.secrets["FIRECRAWL_API_KEY"]
app = FirecrawlApp(api_key=FireCrawlApiKey)
openai_api_key = st.secrets["OPENAI_API_KEY"]
openai_client = OpenAI(api_key=openai_api_key)

'''This model represents the score for a candidate. It uses Pydantic to ensure that the data fits the specified types.
here we had just defined the Pydantic MODEL which specifies the fields,datatypes,description.it is simply a DataStructure ensuring
CandidateScore matches the correct format'''
class CandidateScore(BaseModel):
    name: str = Field(..., description="Candidate's name")
    relevance: int = Field(
        ...,
        description="How relevant the candidate's resume is to the job description (0-100)",
    )
    experience: int = Field(
        ..., description="Candidate's match in terms of work experience (0-100)"
    )
    skills: int = Field(..., description="Candidate's match based on skills (0-100)")
    overall: int = Field(..., description="Overall score (0-100)")
    comment: str = Field(
        ..., description="A cbrief omment explaining the rationale behind the scores"
    )


'''This model defines the expected structure for a candidate’s resume.
This only defines the structure of how a resume should be formatted.'''
class Resume(BaseModel):
    name: str = Field(..., description="Candidate's full name")
    work_experiences: List[str] = Field(..., description="List of work experiences")
    location: str = Field(..., description="Candidate's location")
    skills: List[str] = Field(..., description="List of candidate's skills")
    education: List[str] = Field(..., description="Educational background")
    summary: Optional[str] = Field(
        None, description="A short summary or objective statement"
    )
    certifications: Optional[List[str]] = Field(
        None, description="List of certifications"
    )
    languages: Optional[List[str]] = Field(
        None, description="Languages spoken by the candidate"
    )


class JobDescription(BaseModel):
    title: str
    company: str
    location: str
    requirements: list[str]
    responsibilities: list[str]


'''This Func processes a job description (either as plain text or a URL) and extracts resume file names from a given list of uploaded 
resume files
It returns a dictionary containing:
job_description" → Contains either : The scraped markdown text (if a URL was provided) | The original text (if it was not a URL).
"resumes" → A list of resume file names.'''
async def ingest_inputs(job_description: str, resume_files: List[Any]) -> Dict[str, Any]:
    if job_description.startswith("http"):
        try:
            result = app.scrape_url(job_description, params={"formats": ["markdown"]}) #Return response must be in markdown fmt
            if not result or "markdown" not in result:
                raise ValueError("Scraping did not return markdown data.")
            job_desc_text = result.get("markdown", "") #if markdown doesnt exists then job_desc_test = ""(empty string)
        except Exception as e:
            raise Exception(f"Failed to scrape the job description URL: {e}")
    else:
        job_desc_text = job_description #if JD is not url a simple text
    resumes = [file.name for file in resume_files] #extracts File Names for each uploaded resume
    return {"job_description": job_desc_text, "resumes": resumes}


"""Calls OpenAI's GPT-4o model using a provided list of chat messages.
Returns the response text from the AI.
response_format: Optional => This is an optional parameter that specifies the expected output format(none of Json)"""
def call_llm(messages: list, response_format=None) -> str:
    params = {"model": "gpt-4o", "messages": messages}

    if response_format:#if response format is provided set its value in the dictionary
        params["response_format"] = response_format

    response = openai_client.beta.chat.completions.parse(**params) #send req to openai client with specified params
    
    return response.choices[0].message.content #contains list of choices so choose 1st choice and choose ai msg from that


"""This function processes a raw job description (either input manually or scraped from a webpage) and extracts key details in 
a structured format using a Large Language Model (LLM) like GPT-4.Returns a clean JSON output with important job details
data AS DEFINED IN THE JobDescription MODEL DEFINED USING PYDANTIC : dictionary containing JD Under JD as key
Here we have given a raw job description and what we did is we took the entire job description as arguement under the key
job description and using LLM we defined it into a structed MANNER that we had defined using pydantic model"""
async def parse_job_description(data: Dict[str, Any]) -> Dict[str, Any]:
    job_text = data.get("job_description", "") #get values for key as job description is missing make it empty string
    if not job_text:
        raise ValueError("No job description text provided.")

    prompt = (
        "Extract the key job information from the text below. Return only valid JSON "
        "with the following keys: title, company, location, requirements, responsibilities, benefits, experience. "
        "Do not include any Extra information that is not mentioned above.\n\n"
        "Job description:\n" + job_text #provides the raw job description
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant that extracts key job description information from text. "
                "Return only the job details in valid JSON format using the keys: "
                "title, company, location, requirements (as a list), responsibilities (as a list), "
                "benefits (as a list), and experience."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        llm_output = call_llm(messages, response_format=JobDescription)#specifies the response format as defined using PYDANTIC MODEl
        structured_jd = json.loads(llm_output) #Converts the LLM's response (a JSON-formatted string) into a Python dictionary
    except Exception as e:
        raise Exception(f"Error parsing job description: {e}")

    return structured_jd


"""from uploaded PDF files, extracts their text, and uses an LLM (GPT-4) to extract structured candidate information like name, 
experience, skills, education, etc.. AS DEFINED IN RESUME MODEL It then returns the extracted details in a JSON format.
LLMs cannot directly read uploaded files, so we save them temporarily and extract text from them."""
async def parse_resumes(resume_files: List[Any]) -> Dict[str, Any]:
    parsed_resumes = []
    for resume in resume_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(resume.read())
            temp_path = temp_file.name
        
        with open(temp_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file) ## Load the PDF
            pdf_text = " ".join(page.extract_text() or "" for page in pdf_reader.pages)
            """ extracting text from all pages of a PDF and joining them into a single string"""
            
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant that extracts candidate resume details. "
                    "Extract only the information following this JSON schema: "
                ),
            },
            {
                "role": "user",
                "content": f"Extract resume details from the following resume text:\n\n{pdf_text}",
            },
        ]

        try:
            llm_response = call_llm(messages, response_format=Resume) #format is RESUME the model defined above
            """LLM responses are returned as JSON strings(NOT actually dictionary just strings which looks like a dictionary),
            and json.loads() converts them into a usable Python dictionary."""
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
    job_description_text = json.dumps(parsed_requirements) #convers dict => Json string
    resume_list = parsed_resumes.get("parsed_resumes", [])
    for candidate in resume_list:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an unbiased hiring manager. Compare the following job description with the candidate's resume and provide"
                    "scores (0-100) for relevance, experience, and skills. Also compute an overall score that reflects the candidate's fit "
                    "and provide a comment explaining your evaluation. Return only valid JSON using the following schema: "
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
            llm_response = call_llm(messages, response_format=CandidateScore)
            score_data = json.loads(llm_response) #Json String => Dictionary
            score_data["resume"] = candidate #Adds the original candidate resume to score_data for reference.
            
        except json.JSONDecodeError: #Handles cases where the LLM response isn't valid JSON.
            score_data = {
            "name": candidate.get("name", "Unknown"),
            "relevance": 0,
            "experience": 0,
            "skills": 0,
            "overall": 0,
            "comment": "Error in parsing response from LLM.",
        }
            
        except Exception as e: #Handles any unexpected runtime errors.
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
    ranked_candidates: List[Dict[str, Any]], job_description: Dict[str, Any], top_x: int) -> Dict[str, List[Dict[str, Any]]]:
    invitations = []
    rejections = []

    for idx, candidate in enumerate(ranked_candidates): #loops through each candidate and also keep the track of index(idx)
        candidate_name = candidate.get("name", "Candidate")
        messages = [
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
                        "Please create a polite rejection email. Include constructive feedback and key "
                        "suggestions for improvement based on the candidate's evaluation."
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
