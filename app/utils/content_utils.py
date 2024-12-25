# utils/content_utils.py
import requests
import hashlib
from datetime import datetime
import PyPDF2
from docx import Document
from flask import current_app
import os

def fetch_webpage_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        current_app.logger.info("Webpage content fetched successfully.")

        page_content = response.text
        page_hash = hashlib.md5(page_content.encode('utf-8')).hexdigest()
        last_modified = response.headers.get('Last-Modified')

        if last_modified:
            last_modified_time = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")
        else:
            last_modified_time = None

        return page_hash, last_modified_time

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error fetching the page: {e}")
        return None, None

def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        current_app.logger.error('Failed to extract PDF text')
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")

def extract_text_from_docx(file):
    try:
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        raise ValueError(f"Failed to extract text from DOCX: {str(e)}")

def extract_text_from_file(file):
    if file.filename.endswith('.pdf'):
        text = extract_text_from_pdf(file)
    elif file.filename.endswith('.docx'):
        text = extract_text_from_docx(file)
    else:
        raise ValueError("Unsupported file format. Only PDF and DOCX are allowed.")

    return f"<title>{file.filename}</title>\n<file_content>\n{text}\n</file_content>"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def send_to_api(query, user, files=None, conversation_id="", response_mode="blocking"):
    headers = {
        'Authorization': f'Bearer {current_app.config["API_KEY"]}',
        'Content-Type': 'application/json'
    }
    final_query = "You are a helpful compliance agent who is suppose to answer user query the query with the given knowledge " + query
    
    current_app.logger.info(final_query)
    data = {
        "inputs": {},
        "query": final_query,
        "response_mode": response_mode,
        "conversation_id": conversation_id,
        "user": user,
        "files": files if files else []
    }

    try:
        response = requests.post(current_app.config['API_URL'], headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"API Request failed: {e}")
        return {"error": f"API Request failed: {str(e)}"}
    except ValueError as e:
        current_app.logger.error(f"Failed to decode JSON response: {e}")
        return {"error": "Failed to decode JSON response"}

def get_answer(question, content=None):
    headers = {
        'Authorization': f'Bearer app-G2VCBPrxr5iWvKOHlL9jxwBt',
        'Content-Type': 'application/json'
    }

    max_length = 12000

    if content and len(content) > max_length:
        content = content[:max_length]
        current_app.logger.info(f"Input question truncated to {max_length} characters.")

    data = {
        "inputs": {"content": content, "combined_content": question + "\n" + (content or "")},
        "query": question,
        "response_mode": "blocking",
        "conversation_id": "",
        "user": "sanyam",
        "files": [],
    }

    try:
        response = requests.post(current_app.config['API_URL'], headers=headers, json=data)
        if response.status_code == 200:
            response_data = response.json()
            return response_data.get('answer', 'No answer received')
        else:
            current_app.logger.error(f"API error: {response.status_code}")
            return f"Error: {response.status_code}"

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error communicating with the API: {e}")
        return "An error occurred while fetching the answer."