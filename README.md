# Generative AI-Powered Resume Analyzer

This project demonstrates how to **analyze** and **score** resumes using **Google Generative AI (Gemini)**. It includes:
- Extraction of **mandatory fields** (Name, Contact, University, etc.).
- **AI/ML** and **Gen AI** **experience scoring** (1–3).
- Comparison against a **Job Description** (JD) for a “match percentage.”
- **Batch** processing of PDFs from local upload or a **Google Drive folder** (via Drive API).
- Export of results to **Excel**.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Demo / Hosted Link](#demo--hosted-link)
- [Screenshots](#screenshots)
- [Notes on Generative AI Usage](#notes-on-generative-ai-usage)
- [Author / Credits](#author--credits)

---

## Features
1. **Generative AI** for advanced resume parsing (Gemini from Google).
2. **Batch** up to 100 PDF resumes.
3. **Scoring** for both AI/ML and Gen AI skill sets (1–3).
4. **Google Drive** folder ingestion:
   - Lists and downloads all PDFs in a specified folder.
   - Requires a **service account** JSON to authenticate with the Google Drive API.
5. **Excel** output with structured columns.

---

## Requirements
- **Python 3.8+**
- The following libraries (see [requirements.txt](requirements.txt)):
  - `streamlit`, `google-generativeai`, `PyPDF2`, `python-dotenv`, `pandas`, `requests`, `openpyxl`
  - `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2` (for Drive API)

---

## Installation

1. **Clone** the repo:
   ```bash
   git clone https://github.com/YourUsername/ResumeAnalyzer.git
   cd ResumeAnalyzer
   ```
2. **Create** a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # or .\venv\Scripts\activate on Windows
   ```
3. **Install** dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. **Google Generative AI Key**:
   - Create a `.env` file with:
     ```
     GOOGLE_API_KEY="YOUR_GEMINI_KEY_HERE"
     ```
5. **Google Drive API** (optional for folder approach):
   - Enable the Drive API in your GCP project.
   - Create a **service account** with read access.
   - Place `service_account.json` in your project folder.

---

## Usage

1. **Run** the Streamlit app:
   ```bash
   streamlit run app.py
   ```
2. **Open** the local URL (e.g. `http://127.0.0.1:8501`) in your browser.
3. **Sidebar**:
   - Choose **Upload PDFs Directly** or **Use Google Drive** links/folder.
   - (Optional) Provide a **Job Description** (JD).
4. **Submit**: Wait for the analysis to complete.  
5. **Excel**: Download the final `.xlsx` file containing all mandatory columns:
   - Name, Contact info, University, Course, CGPA, etc.
   - AI/ML and Gen AI experience scores.
   - JD Match Percentage, Missing/Matching keywords, etc.

---

## Project Structure
```
ResumeAnalyzer/
├─ app.py               # Main Streamlit app
├─ requirements.txt     # Libraries
├─ .env.example         # Example environment file
├─ service_account.json # (Optional) Drive API credentials
├─ README.md            # This readme
└─ ...
```

---

## Demo / Hosted Link
If you have a public or private hosting link, add it here:
- **Hosted on Streamlit Cloud**: [https://YOUR-STREAMLIT-APP](https://YOUR-STREAMLIT-APP)

---

## Screenshots
Include any relevant screenshots here.

1. **Sidebar** & **Upload**:
   ![Sidebar with multiple methods](docs/screenshots/sidebar.png)

2. **Results**:
   ![Excel results preview](docs/screenshots/results.png)

---

## Notes on Generative AI Usage
- We use **Gemini** from Google for extracting fields and comparing against the JD.
- The prompt approach is in `parse_resume` and `analyze_resume`.
- **Scores** (1–3) are assigned by the LLM, guided by the custom prompt.

---

## Author / Credits
- **Author**: Shantam Shukla.
- **Credit**: This solution integrates multiple open-source libraries and the Google Generative AI library.

---

**Happy Resume Analysis!**
