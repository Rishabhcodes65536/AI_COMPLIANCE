from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
import requests
import json
import os
import hashlib
from datetime import datetime
import logging
from dotenv import load_dotenv
import logging
import PyPDF2
from functools import wraps
from docx import Document
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from bson import ObjectId




initial_date = datetime(2024, 11, 1)  


load_dotenv()

# Configuration
API_URL = os.getenv('API_URL')
API_KEY = os.getenv('API_KEY')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
SECRET_KEY = os.getenv('SECRET_KEY')
URL = 'https://www.revisor.mn.gov/statutes/cite/245D/full'



app = Flask(__name__)
app.secret_key = SECRET_KEY 
app.logger.setLevel(logging.INFO)


# MongoDB Setup
client = MongoClient("mongodb+srv://jainrishabh32768:ZYsjkxK62VrO0Nqo@cluster0.h5cd0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")  # Update with your MongoDB connection URI
db = client["test"]  # Replace with your database name
users_collection = db["users"]
chats_collection = db["chats"]

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

last_known_hash = None

def fetch_webpage_content(url):

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


def get_answer(question,content):
    """
    Send a question to the external API and retrieve the answer.
    """
    headers = {
        'Authorization': f'Bearer app-G2VCBPrxr5iWvKOHlL9jxwBt',
        'Content-Type': 'application/json'
    }

    max_length = 12000  # This assumes ~3.5k tokens is ~12,000 characters

    if len(content) > max_length:
        content = content[:max_length]
        app.logger.info(f"Input question truncated to {max_length} characters.")

    app.logger.info("\nQuestion is ",question)
    app.logger.info("\nContent is ",content)
    
    conversation="last ten conversation"
    data = {
        "inputs": {"content":content,"conversation":conversation,"combined_content":question+"\n"+content},
        "query":question,
        "response_mode": "blocking",
        "conversation_id": "",
        "user": "sanyam",
        "files": [],
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        app.logger.info("Request sent to the external API.")
        app.logger.info(response.json())
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
    

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

app.json_encoder = JSONEncoder

@app.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return google.authorize_redirect(
        redirect_uri=url_for('google_callback', _external=True)
    )

@app.route('/google/callback')
def google_callback():
    try:
        # Get token and user info from Google
        token = google.authorize_access_token()
        if not token:
            raise ValueError("Failed to get access token")
            
        resp = google.get('userinfo')
        user_info = resp.json()
        
        if not user_info or 'email' not in user_info:
            raise ValueError("Failed to get user info")

        # Prepare user data
        user_data = {
            "name": user_info.get("name", "User"),
            "email": user_info["email"],
            "picture": user_info.get("picture", "/static/default-profile.png"),
            "last_login": datetime.utcnow()
        }

        # Update or insert user in MongoDB
        users_collection.update_one(
            {"email": user_data["email"]},
            {"$set": user_data},
            upsert=True
        )

        # Store user info in session
        session['user'] = user_data
        return redirect(url_for('files'))

    except Exception as e:
        app.logger.error(f"Error in Google callback: {str(e)}")
        return render_template('error.html', error="Authentication failed. Please try again.")

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """
    Render the dashboard for authenticated users.
    """
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    return render_template('new_ui.html', user=user)



app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx'}



def extract_text_from_pdf(file):
 
    try:
   
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        
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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/files')
def files():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('files.html', user=session['user'])

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

    return f"<title>{file.filename}</title>\n<file_content>\n{text}\n</file_content>"


@app.route('/upload', methods=['POST'])
def upload_files():
    """
    Endpoint for uploading files, extracting text, and interacting with LLM.
    """
    try:
        # Get uploaded files and user question
        uploaded_files = request.files.getlist("files")
        user_question = request.form.get("question", "")
        user_query = f"\n <user_question> {user_question} \n </user_question>"
        user_id = session.get('user', {}).get('id')  # Ensure the user is logged in
        
        if not user_id:
            return jsonify({"error": "User not logged in."}), 401

        # Extract text from files
        file_content = ""
        for file in uploaded_files:
            try:
                extracted_text = extract_text_from_file(file)
                file_content += f"\n <file_separator>\n{extracted_text} </file_separator>"
            except Exception as e:
                return jsonify({"error": f"Failed to process {file.filename}: {str(e)}"}), 400

        # Retrieve the past 10 conversations from the database
        chat_history = chats_collection.find(
            {"user_id": ObjectId(user_id)},
            {"chat_history": {"$slice": -10}}  # Get the last 10 conversations
        ).sort([("timestamp", 1)])  # Sort in ascending order (oldest first)

        # Format chat history with appropriate XML separators
        formatted_history = ""
        for chat in chat_history:
            for entry in chat["chat_history"]:
                question = entry.get("question", "").strip()
                response = entry.get("response", "").strip()
                if question and response:
                    formatted_history += f"\n<chat>\n  <question>{question}</question>\n  <response>{response}</response>\n</chat>\n"
        
        # Add the formatted chat history to the user query
        user_query = f"{formatted_history}\n<user_question>{user_question}</user_question>"

        # Interact with LLM
        response = get_answer(user_query, file_content)

        # Log interaction in MongoDB
        for file in uploaded_files:
            chats_collection.update_one(
                {"user_id": ObjectId(user_id), "file_name": file.filename},
                {"$push": {
                    "chat_history": {
                        "question": user_question,
                        "response": response,
                        "timestamp": datetime.utcnow()
                    }} ,
                 "$setOnInsert": {
                     "user_id": ObjectId(user_id),
                     "file_name": file.filename
                 }},
                upsert=True
            )

        return jsonify({"response": response})

    except Exception as e:
        app.logger.error(f"Error in /upload: {e}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    except Exception as e:
        app.logger.error(f"Error in /upload: {e}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

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



# Converted monolithic to proper directory structure for easy debugging

# main.py
# from flask import Flask
# import os
# import logging
# import sys
# from pathlib import Path

# # Add the project root directory to Python path
# project_root = Path(__file__).parent
# sys.path.append(str(project_root))

# from routes.auth import auth_bp
# from routes.file import file_bp
# from routes.main import main_bp
# from config import Config

# def create_app():
#     app = Flask(__name__)
    
#     # Load configuration
#     app.config.from_object(Config)
    
#     # Configure logging
#     app.logger.setLevel(logging.INFO)
    
#     # Create upload folder if it doesn't exist
#     if not os.path.exists(app.config['UPLOAD_FOLDER']):
#         os.makedirs(app.config['UPLOAD_FOLDER'])
    
#     # Register blueprints
#     app.register_blueprint(auth_bp)
#     app.register_blueprint(file_bp)
#     app.register_blueprint(main_bp)
    
#     return app

# if __name__ == '__main__':
#     app = create_app()
#     app.run(debug=True)