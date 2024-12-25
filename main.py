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
from datetime import datetime,timedelta
from bson import ObjectId

from werkzeug.middleware.proxy_fix import ProxyFix


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
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)  # Increased session lifetime
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS

app.logger.setLevel(logging.INFO)

# Add this line to handle proxy headers correctly
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


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
        'scope': 'openid email profile',
        'prompt': 'select_account'
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
    session.clear()
    session['oauth_state'] = os.urandom(16).hex()
    session.modified = True
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(
        redirect_uri=redirect_uri,
        state=session['oauth_state']
    )

@app.route('/google/callback')
def google_callback():
    try:
        state = request.args.get('state')
        stored_state = session.get('oauth_state')
        
        if not state or not stored_state or state != stored_state:
            raise ValueError("State verification failed")
        
        session.pop('oauth_state', None)
        
        code = request.args.get('code')
        if not code:
            raise ValueError("No authorization code received")

        token = google.authorize_access_token()
        if not token:
            raise ValueError("Failed to get access token")
        
        # Updated this line to use the full URL
        resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
        user_info = resp.json()
        
        if not user_info or 'email' not in user_info:
            raise ValueError("Failed to get user info")

        user_data = {
            "name": user_info.get("name", "User"),
            "email": user_info["email"],
            "picture": user_info.get("picture", "/static/default-profile.png"),
            "last_login": datetime.utcnow()
        }

        result = users_collection.update_one(
            {"email": user_data["email"]},
            {"$set": user_data},
            upsert=True
        )

        session.permanent = True
        session['user'] = user_data
        session.modified = True

        app.logger.info(f"Successfully authenticated user: {user_data['email']}")
        return redirect(url_for('dashboard'))

    except Exception as e:
        app.logger.error(f"Error in Google callback: {str(e)}")
        session.clear()
        return render_template(
            'error.html', 
            error="Authentication failed. Please try again.",
            retry_url=url_for('login')
        )

@app.route('/logout')
def logout():
    session.clear()
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

def get_answer(question,content,formatted_history):
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

    # app.logger.info("\nQuestion is ",question)
    # app.logger.info("\nContent is ",content)
    app.logger.info("\nFormatted history is ",formatted_history)
    # conversation=formatted_history
    data = {
        "inputs": {"content":content,"conversation":formatted_history,"combined_content":question+"\n"+content},
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

        # Ensure the user is logged in and get the user email from the session
        user_email = session.get('user', {}).get('email')
        if not user_email:
            return jsonify({"error": "User not logged in."}), 401

        # Extract text from files
        file_content = ""
        for file in uploaded_files:
            try:
                extracted_text = extract_text_from_file(file)
                file_content += f"\n <file_separator>\n{extracted_text} </file_separator>"
            except Exception as e:
                return jsonify({"error": f"Failed to process {file.filename}: {str(e)}"}), 400

        # Retrieve the past 10 conversations from the database by email
        chat_history = chats_collection.find(
            {"email": user_email},  # Using email instead of user_id (now using user_email)
            {"chat_history": {"$slice": -10}}  # Get the last 10 conversations
        ).sort([("timestamp", 1)])  # Sort in ascending order (oldest first)

        # Debugging: Check if chat_history is being fetched correctly
        app.logger.error(f"Chat history retrieved: {chat_history}")

        # Format chat history with appropriate XML separators
        formatted_history = ""
        for chat in chat_history:
            app.logger.info(f"Processing chat: {chat}")  # Debugging line to inspect each chat entry
            chat_entries = [
                f"\n<chat>\n  <question>{entry.get('question', '').strip()}</question>\n  <response>{entry.get('response', '').strip()}</response>\n</chat>"
                for entry in chat.get("chat_history", [])
                if entry.get("question") and entry.get("response")
            ]
            formatted_history += ''.join(chat_entries)  # Join all entries into a single string

        # Debugging: Log the formatted chat history to ensure it's populated
        app.logger.info(f"Formatted chat history: {formatted_history}")

        # Add the formatted chat history to the user query
        user_query = f"<user_question>{user_question}</user_question>"

        # Interact with LLM
        response = get_answer(user_query, file_content, formatted_history)

        # Log interaction in MongoDB
        for file in uploaded_files:
            file_name = file.filename if file.filename else "empty"
            chats_collection.update_one(
                {"email": user_email, "file_name": file_name},  # Using user_email instead of user_id
                {
                    "$push": {
                        "chat_history": {
                            "question": user_question,
                            "response": response,
                            "timestamp": datetime.utcnow()
                        }
                    },
                    "$setOnInsert": {
                        "email": user_email,  # Using user_email instead of user_id
                        "file_name": file_name
                    }
                },
                upsert=True
            )

        return jsonify({"response": response})

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