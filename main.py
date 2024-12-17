from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
import requests
import os
import hashlib
from datetime import datetime
import logging
from dotenv import load_dotenv
import logging
import PyPDF2
from docx import Document

from werkzeug.utils import secure_filename
from datetime import datetime


initial_date = datetime(2024, 11, 1)  # Example hardcoded date (today's date or any fixed date)


# import textract

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv('API_URL')
API_KEY = os.getenv('API_KEY')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
SECRET_KEY = os.getenv('SECRET_KEY')
URL = 'https://www.revisor.mn.gov/statutes/cite/245D/full'

# Initialize Flask app


app = Flask(__name__)
app.secret_key = SECRET_KEY  # Required for session management
app.logger.setLevel(logging.INFO)

# Configure OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'email profile'}
)

# Global variable to track the last known hash of the webpage
last_known_hash = None





def send_to_api(query, user, files=None, conversation_id="", response_mode="blocking"):
    """
    Send a request to the external API with the given parameters.

    Args:
        query (str): The question or query to send.
        user (str): The user identifier.
        files (list): List of file paths (optional).
        conversation_id (str): Conversation ID for context (default is "").
        response_mode (str): The response mode (default is "blocking").

    Returns:
        dict: The JSON response from the API, or an error message if the request fails.
    """
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    final_query="You are a helpful compliance agent who is suppose to answer user query the query with the given knowledge "+ query
    # Construct the payload
    app.logger.info(final_query)
    data = {
        "inputs": {},
        "query": final_query,
        "response_mode": response_mode,
        "conversation_id": conversation_id,
        "user": user,
        "files": files if files else []
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"API Request failed: {e}")
        return {"error": f"API Request failed: {str(e)}"}
    except ValueError as e:
        logging.error(f"Failed to decode JSON response: {e}")
        return {"error": "Failed to decode JSON response"}


def fetch_webpage_content(url):
    """
    Fetch the content of a webpage and return its MD5 hash and last modified timestamp.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        app.logger.info("Webpage content fetched successfully.")

        page_content = response.text
        page_hash = hashlib.md5(page_content.encode('utf-8')).hexdigest()
        last_modified = response.headers.get('Last-Modified')

        if last_modified:
            last_modified_time = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")
        else:
            last_modified_time = None

        return page_hash, last_modified_time

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching the page: {e}")
        return None, None


def get_answer(question):
    """
    Send a question to the external API and retrieve the answer.
    """
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    data = {
        "inputs": {},
        "query": question,
        "response_mode": "blocking",
        "conversation_id": "",
        "user": "sanyam",
        "files": []
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        app.logger.info("Request sent to the external API.")

        if response.status_code == 200:
            response_data = response.json()
            return response_data.get('answer', 'No answer received')
        else:
            app.logger.error(f"API error: {response.status_code}")
            return f"Error: {response.status_code}"

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error communicating with the API: {e}")
        return "An error occurred while fetching the answer."


# Routes
@app.route('/', methods=['GET'])
def root():
    """
    Render the homepage with the user interface.
    """
    return render_template('new_ui.html')

@app.route('/home', methods=['GET'])
def home():
    """
    Render the homepage with the user interface.
    """
    return render_template('new_ui.html')


@app.route('/ask', methods=['POST'])
def ask():
    """
    Handle user questions and return the answer.
    """
    question = request.form.get('question')
    answer = get_answer(question)
    return render_template('answer.html', question=question, answer=answer)

@app.route('/check-update', methods=['GET'])
def check_update():
    """
    API endpoint to check if the tracked webpage has been updated.
    """
    global last_known_hash

    current_hash, last_modified_time = fetch_webpage_content(URL)

    if current_hash is None:
        return jsonify({"error": "Failed to fetch the page."}), 500

    # Calculate the date range (from initial_date to now)
    current_date = datetime.now()
    date_range = f"From {initial_date.strftime('%Y-%m-%d')} to {current_date.strftime('%Y-%m-%d')}"

    if last_known_hash is None:
        last_known_hash = current_hash
        return jsonify({
            "message": "Initial check completed, no changes detected.",
            "date_range": date_range
        }), 200
    elif current_hash != last_known_hash:
        last_known_hash = current_hash
        return jsonify({
            "message": "The webpage has been updated.",
            "date_range": date_range
        }), 200
    else:
        return jsonify({
            "message": "No changes detected.",
            "date_range": date_range
        }), 200
    

# Google OAuth Routes
@app.route('/login')
def login():
    """
    Redirect the user to Google's OAuth 2.0 authorization page.
    """
    # if 'user' in session:
    #     return redirect(url_for('dashboard'))  # or any logged-in page
    redirect_uri = url_for('google_callback', _external=True)  # Generates full URL
    return google.authorize_redirect(redirect_uri)
    # return google.authorize_redirect('http://localhost:5000/google/callback')


@app.route('/google/callback')
def google_callback():
    """
    Handle the callback from Google OAuth and fetch the user's profile.
    """
    try:
        token = google.authorize_access_token()
        user_info = google.get('userinfo').json()

        if not user_info:
            raise ValueError("Failed to fetch user info")  # Handle failure gracefully

        session['user'] = user_info
        app.logger.info(f"User logged in: {user_info}")
        return redirect(url_for('dashboard'))
    except Exception as e:
        app.logger.error(f"Error during Google OAuth: {e}")
        return redirect(url_for('home'))  # Avoid redirecting to login to break the loop


@app.route('/dashboard')
def dashboard():
    """
    Render the dashboard for authenticated users.
    """
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    return render_template('ui_dark.html', user=user)


@app.route('/logout')
def logout():
    """
    Log out the user by clearing the session.
    """
    session.clear()
    return  render_template('ui_dark.html')  # Redirect to login, not other routes



#file upload section


app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx'}



def extract_text_from_pdf(file):
    """
    Extract text from a PDF file.
    """
    try:
        # Open the file
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        # app.logger.info(text)
        return text
    except Exception as e:
        app.logger.error('no text')
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")

from docx import Document

def extract_text_from_docx(file):
    """
    Extract text from a DOCX file.
    """
    try:
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        raise ValueError(f"Failed to extract text from DOCX: {str(e)}")

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Helper function to check file format
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Route for homepage
@app.route('/files')
def index():
    return render_template('file_upload.html')


# Combine text with file titles for indexing
def extract_text_from_file(file):
    """
    Extract text from an uploaded file.
    Supports PDF and DOCX formats.
    """
    if file.filename.endswith('.pdf'):
        text = extract_text_from_pdf(file)
    elif file.filename.endswith('.docx'):
        text = extract_text_from_docx(file)
    else:
        raise ValueError("Unsupported file format. Only PDF and DOCX are allowed.")
    
    # Add title delimiter for indexing
    return f"---Title: {file.filename}---\n{text}"


@app.route('/upload', methods=['POST'])
def upload_files():
    """
    Endpoint for uploading files, extracting text, and interacting with LLM.
    """
    uploaded_files = request.files.getlist("files")
    combined_text = "You are a helpful compliance agent who is suppose to answer user query the query with the given knowledge "

    # Extract text from uploaded files
    for file in uploaded_files:
        try:
            extracted_text = extract_text_from_file(file)
            combined_text += f"\n---File Separator---\n{extracted_text}"
        except Exception as e:
            return jsonify({"error": f"Failed to process {file.filename}: {str(e)}"}), 400

    # Add user question
    user_question = request.form.get("question", "")
    combined_text += f"\n---User Question---\n{user_question}"

    app.logger.info(combined_text)
    # Send combined text to the LLM
    try:
        response = get_answer(combined_text)  # Replace with your actual LLM function
    except Exception as e:
        return jsonify({"error": f"Failed to interact with LLM: {str(e)}"}), 500

    return jsonify({"response": response})

# Route to handle file deletion
@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'message': f'{filename} deleted successfully'})
    else:
        return jsonify({'error': f'{filename} not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)