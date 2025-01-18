import streamlit as st
import google.generativeai as genai
import os
import PyPDF2 as pdf
from dotenv import load_dotenv
import json
import pandas as pd
from typing import Dict, List
import io
import requests
import re

# For Google Drive API
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

###############################################################################
# 1. Google Drive API Authentication
###############################################################################
def get_drive_service():
    """
    Create and return a Google Drive API service object using a service account JSON file.
    Make sure you have 'service_account.json' in your project folder or set its path.
    
    Scopes: we need at least read-only to list and download PDFs.
    """
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    creds = service_account.Credentials.from_service_account_info(
        json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_INFO")), scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)
    return service

def extract_folder_id(folder_link: str) -> str:
    """
    If link is like 'https://drive.google.com/drive/folders/<FOLDER_ID>',
    we parse out <FOLDER_ID>.
    """
    match = re.search(r"drive/folders/([a-zA-Z0-9-_]+)", folder_link)
    if match:
        return match.group(1)
    return ""

def list_pdfs_in_folder(service, folder_id: str) -> List[dict]:
    """
    List all PDF files in a given folder (id=folder_id) using the Drive API.
    Returns a list of dicts: [{"id": "...", "name": "..."}]
    """
    # query for PDFs not trashed
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    files = response.get("files", [])
    return files

def download_pdf_by_id(service, file_id: str) -> io.BytesIO:
    """
    Download a PDF by file_id using the Drive API, returns file-like BytesIO.
    """
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = build("drive", "v3", credentials=service._http.credentials).files().get_media(fileId=file_id)

    # Actually, the above approach might be repetitive. Let's do it properly:
    from googleapiclient.http import MediaIoBaseDownload
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh

###############################################################################
# 2. Existing Gemini/Resume Logic (unchanged, except for removing single-file link approach)
###############################################################################
def get_gemini_response(prompt: str, text: str, jd: str = "") -> str:
    """Get response from Gemini model with enhanced error handling"""
    import google.generativeai as genai
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        full_prompt = f"{prompt}\n\nResume Text: {text}\n\nJob Description: {jd}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        st.error(f"Error getting response from Gemini: {str(e)}")
        return ""

def parse_resume(text: str) -> Dict:
    """Parse resume text to extract mandatory fields with improved prompt"""
    parse_prompt = """
    You are a precise resume parser. Analyze the following resume text carefully and extract the required information.
    Return ONLY a valid JSON object with these exact keys, ensuring all values are strings:

    {
        "Name": "Full name of the candidate",
        "Phone": "Phone Number",
        "Email": "Email address",
        "University": "Name of the university/institution",
        "YearOfStudy": "Year of study or graduation year",
        "Course": "Name of the course/degree",
        "Discipline": "Field of study/specialization",
        "CGPA": "CGPA or percentage (if available, otherwise 'Not specified')",
        "KeySkills": "Comma-separated list of key technical and soft skills",
        "GenAIExperienceScore": "Score from 1-3 based on Gen AI experience",
        "AIMLExperienceScore": "Score from 1-3 based on AI/ML experience",
        "SupportingInformation": "Brief summary of certifications, internships, projects"
    }

    Notes for scoring:
    - GenAIExperienceScore: 1=Basic/Exposed, 2=Hands-on experience, 3=Advanced (RAG, LLMs, etc.)
    - AIMLExperienceScore: 1=Basic/Exposed, 2=Hands-on experience, 3=Advanced (Deep Learning, Neural Networks, etc.)
    """
    
    try:
        response = get_gemini_response(parse_prompt, text)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:-3]
        
        parsed_data = json.loads(response)
        
        # Validate required fields
        required_fields = [
            "Name", "Phone", "Email", "University", "YearOfStudy", 
            "Course", "Discipline", "CGPA", "KeySkills", 
            "GenAIExperienceScore", "AIMLExperienceScore", "SupportingInformation"
        ]
        
        for field in required_fields:
            if field not in parsed_data or not parsed_data[field]:
                parsed_data[field] = "Not specified"
        
        return parsed_data
        
    except json.JSONDecodeError as e:
        st.error(f"Error parsing resume data: {str(e)}")
        return {field: "Not specified" for field in required_fields}

def analyze_resume(text: str, jd: str) -> Dict:
    """Analyze resume against job description with improved prompt"""
    analysis_prompt = """
    Analyze this resume against the job description as an expert ATS system.
    Consider the following:
    1. Technical skills match
    2. Experience level requirements
    3. Educational requirements
    4. Key responsibilities match
    
    Return ONLY a valid JSON object with these exact keys:
    {
        "match_percentage": "Numerical percentage of match (0-100)",
        "matching_keywords": ["List of matching technical skills and keywords found in both"],
        "missing_keywords": ["List of important keywords from JD missing in resume"],
        "profile_summary": "Brief professional summary",
        "recommendations": ["List of specific improvements suggested"]
    }
    """
    
    try:
        response = get_gemini_response(analysis_prompt, text, jd)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:-3]
            
        return json.loads(response)
    except json.JSONDecodeError:
        return {
            "match_percentage": 0,
            "matching_keywords": [],
            "missing_keywords": [],
            "profile_summary": "Error analyzing profile",
            "recommendations": ["Error generating recommendations"]
        }

def read_pdf(file) -> str:
    """Extract text from PDF file (BytesIO or local file)."""
    try:
        reader = pdf.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += str(page.extract_text())
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

def convert_df_to_excel(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel bytes"""
    import io
    from openpyxl import Workbook
    from pandas import ExcelWriter
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

###############################################################################
# 3. The Main Streamlit Logic
###############################################################################
def main():
    st.set_page_config(page_title="Generative AI-Powered Resume Analyzer", layout="wide")
    
    st.sidebar.title("Generative AI-Powered Resume Analyzer")
    st.sidebar.text("Analyze & Score Resumes")

    # Choose method
    upload_method = st.sidebar.radio(
        "Choose Upload Method",
        ["Upload PDFs Directly", "Use Google Drive File Links", "Use Google Drive Folder Link"]
    )

    jd = st.sidebar.text_area(
        "Job Description",
        placeholder="Paste the job description here..."
    )

    submitted_files = []
    folder_link = ""
    drive_links = ""

    if upload_method == "Upload PDFs Directly":
        uploaded_files = st.sidebar.file_uploader(
            "Upload Resumes (PDF)",
            type="pdf",
            accept_multiple_files=True
        )
        if uploaded_files:
            submitted_files = uploaded_files

    elif upload_method == "Use Google Drive File Links":
        st.sidebar.markdown("""
        ### Google Drive Instructions:
        1. Upload your PDFs to Google Drive
        2. Right-click each file → Share → 'Anyone with the link'
        3. Copy the share links
        4. Paste all links below (one per line)
        """)
        drive_links = st.sidebar.text_area(
            "Enter Google Drive file links (one per line)",
            placeholder="https://drive.google.com/file/d/..."
        )
    else:
        st.sidebar.markdown("""
        ### Google Drive Instructions:
        1. Upload your PDFs to Google Drive
        2. Right on folder → Share → 'Anyone with the link'
        3. Copy the share links
        4. Paste all links below
        """)
        folder_link = st.sidebar.text_input(
            "Enter Google Drive Folder Link",
            placeholder="https://drive.google.com/drive/folders/<folder_id>"
        )

    submit_button = st.sidebar.button("Submit for Analysis")
    
    if not submit_button:
        st.header("Generative AI-Powered Resume Analyzer")
        st.markdown("Upload or link to resumes, then see analysis & scoring. Provide a Job Description to compare.")
        cols = st.columns(2)
        with cols[0]:
            st.link_button("LinkedIn", "https://www.linkedin.com/in/shantam-shukla")
        with cols[1]:
            st.link_button("GitHub", "https://github.com/ShantamShukla")
        
        
        st.info("⚡ Batch process up to 100 resumes at once!")
        st.warning("📄 Upload resumes in PDF format only")
        return

    # If user clicked "Submit for Analysis"
    service = None  # We'll create it once if needed

    # 1) If direct PDF upload
    if upload_method == "Upload PDFs Directly":
        if not submitted_files:
            st.warning("Please upload at least one PDF file.")
            return
    # 2) If "Use Google Drive File Links"
    elif upload_method == "Use Google Drive File Links":
        if not drive_links.strip():
            st.warning("Please enter at least one Google Drive file link.")
            return
        # We'll parse multiple lines
        lines = drive_links.strip().split('\n')
        service = get_drive_service()
        for link in lines:
            link = link.strip()
            # same logic as your old approach: extract file_id from link
            file_id = ""
            patterns = [
                r'file/d/([a-zA-Z0-9-_]+)',
                r'id=([a-zA-Z0-9-_]+)',
                r'open\?id=([a-zA-Z0-9-_]+)'
            ]
            for pat in patterns:
                m = re.search(pat, link)
                if m:
                    file_id = m.group(1)
                    break
            if file_id:
                # download
                try:
                    pdf_bytes = download_pdf_by_id(service, file_id)
                    pdf_bytes.name = f"resume_{file_id}.pdf"
                    submitted_files.append(pdf_bytes)
                except:
                    st.error(f"Failed to download file from link: {link}")
    # 3) If "Use Google Drive Folder Link"
    else:
        if not folder_link.strip():
            st.warning("Please enter a Google Drive folder link.")
            return
        # Extract folder_id from link
        folder_id = extract_folder_id(folder_link.strip())
        if not folder_id:
            st.warning("Unable to parse folder ID from link. Make sure it's drive.google.com/drive/folders/<FOLDER_ID>")
            return
        # Now list all PDFs
        service = get_drive_service()
        pdf_list = list_pdfs_in_folder(service, folder_id)
        st.info(f"Found {len(pdf_list)} PDF(s) in the folder.")
        for fmeta in pdf_list:
            fid = fmeta["id"]
            fname = fmeta["name"]
            try:
                pdf_bytes = download_pdf_by_id(service, fid)
                pdf_bytes.name = fname
                submitted_files.append(pdf_bytes)
            except:
                st.error(f"Failed to download PDF: {fname}")

    if not submitted_files:
        st.warning("No resumes to process.")
        return

    # Now we have "submitted_files" as a list of PDFs (BytesIO or UploadedFile)
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, file_obj in enumerate(submitted_files):
        status_text.text(f"Processing: {file_obj.name}")
        text = read_pdf(file_obj)
        if text:
            parsed_data = parse_resume(text)
            if jd.strip():
                analysis = analyze_resume(text, jd)
                parsed_data.update({
                    "JDMatchPercentage": analysis.get("match_percentage", 0),
                    "MatchingKeywords": ", ".join(analysis.get("matching_keywords", [])),
                    "MissingKeywords": ", ".join(analysis.get("missing_keywords", [])),
                    "Recommendations": "\n".join(analysis.get("recommendations", []))
                })
            results.append(parsed_data)
        progress = (idx + 1) / len(submitted_files)
        progress_bar.progress(progress)

    progress_bar.empty()
    status_text.empty()

    if results:
        st.header("Resume Analysis Results")
        df = pd.DataFrame(results)

        # optional: summary metrics
        if len(results) > 1:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Resumes", len(results))
            if "JDMatchPercentage" in df.columns:
                df["JDMatchPercentage"] = pd.to_numeric(df["JDMatchPercentage"], errors="coerce")
                avg_match = df["JDMatchPercentage"].mean()
                high_match = df["JDMatchPercentage"].max()
            else:
                avg_match = 0
                high_match = 0
            with col2:
                avg_match = 0 if pd.isna(avg_match) else avg_match
                st.metric("Average JD Match", f"{avg_match:.1f}%")
            with col3:
                high_match = 0 if pd.isna(high_match) else high_match
                st.metric("Highest JD Match", f"{high_match:.1f}%")

        st.dataframe(df)
        excel_data = convert_df_to_excel(df)
        st.download_button(
            label="📥 Download Results (Excel)",
            data=excel_data,
            file_name="resume_analysis.xlsx",
            mime="application/vnd.ms-excel"
        )
        st.success("✅ Analysis completed successfully!")
    else:
        st.warning("No results to display.")

if __name__ == "__main__":
    main()
