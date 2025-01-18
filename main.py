from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
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
from bs4 import BeautifulSoup

from werkzeug.middleware.proxy_fix import ProxyFix

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv('API_URL')
API_KEY = os.getenv('API_KEY')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
SECRET_KEY = os.getenv('SECRET_KEY')
MONGO_URI = os.getenv('MONGO_URI')
URL = 'https://www.revisor.mn.gov/statutes/cite/245D/full'
MODE = os.getenv('MODE', 'production')

# Dummy user for test mode
dummy_user = {
    "name": "Tester",
    "email": "tester@example.com",
    "picture": "/static/default-profile.png",
    "last_login": datetime.utcnow()
}


app = Flask(__name__, static_folder='public/static')
app.secret_key = SECRET_KEY 
app.config['SESSION_COOKIE_NAME'] = 'google-login-session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)  # Increased session lifetime
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS

app.logger.setLevel(logging.INFO)

# Add this line to handle proxy headers correctly
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


# MongoDB Setup
client = MongoClient(MONGO_URI)  # Use the MongoDB URI from the .env file
db = client["test"]  # Replace with your database name
users_collection = db["users"]
chats_collection = db["chats"]
hashes_collection = db["hashes_new"]


oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
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
        return response.text
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching the page: {e}")
        return None

def compute_chunk_hashes(content, chunk_size=1000):
    """
    Compute hashes of content chunks for efficient comparison.
    Uses rolling hash for better performance.
    """
    soup = BeautifulSoup(content, 'html.parser')
    text = ' '.join(block.get_text() for block in soup.find_all(['p', 'div', 'span', 'li']))
    
    chunks = []
    hashes = []
    
    # Create chunks with overlap for better change detection
    for i in range(0, len(text), chunk_size//2):
        chunk = text[i:i + chunk_size]
        if chunk:
            chunk_hash = hashlib.md5(chunk.encode('utf-8')).hexdigest()
            chunks.append(chunk)
            hashes.append(chunk_hash)
    
    return chunks, hashes

def binary_search_changes(old_hashes, new_hashes):
    """
    Use binary search to efficiently locate changes between versions.
    Returns the indices where changes are detected.
    """
    changes = []
    min_len = min(len(old_hashes), len(new_hashes))
    
    def binary_search_chunk(start, end):
        if start >= end:
            return
        
        mid = (start + end) // 2
        if mid < min_len and old_hashes[mid] != new_hashes[mid]:
            changes.append(mid)
            binary_search_chunk(start, mid)
            binary_search_chunk(mid + 1, end)
    
    binary_search_chunk(0, min_len)
    
    # Handle case where new content is longer/shorter
    if len(new_hashes) > len(old_hashes):
        changes.extend(range(len(old_hashes), len(new_hashes)))
    
    return sorted(changes)

@app.route('/check-update', methods=['GET'])
def check_update():
    """
    Optimized API endpoint to check if the tracked webpage has been updated.
    """
    content = fetch_webpage_content(URL)
    if content is None:
        return jsonify({"error": "Failed to fetch the page."}), 500

    # Compute new chunks and hashes
    new_chunks, new_hashes = compute_chunk_hashes(content)
    
    # Get previous state from MongoDB
    last_state = hashes_collection.find_one({"url": URL})
    current_date = datetime.now()
    
    if not last_state:
        # First time checking - store initial state
        hashes_collection.insert_one({
            "url": URL,
            "chunks": new_chunks,
            "hashes": new_hashes,
            "last_checked": current_date
        })
        return jsonify({
            "message": "Initial check completed.",
            "date_range": f"From {current_date.strftime('%Y-%m-%d')} to {current_date.strftime('%Y-%m-%d')}"
        }), 200
    
    # Find changes using binary search
    old_hashes = last_state['hashes']
    changed_indices = binary_search_changes(old_hashes, new_hashes)
    
    if changed_indices:
        # Update stored state and return changes
        hashes_collection.update_one(
            {"url": URL},
            {
                "$set": {
                    "chunks": new_chunks,
                    "hashes": new_hashes,
                    "last_checked": current_date
                }
            }
        )
        
        # Prepare summary of changes
        changes_summary = [
            {
                "index": idx,
                "new_content": new_chunks[idx] if idx < len(new_chunks) else "Content removed"
            }
            for idx in changed_indices[:5]  # Limit to first 5 changes
        ]
        
        return jsonify({
            "message": f"Found {len(changed_indices)} changes in the webpage.",
            "date_range": f"From {last_state['last_checked'].strftime('%Y-%m-%d')} to {current_date.strftime('%Y-%m-%d')}",
            "changes_sample": changes_summary
        }), 200
    
    return jsonify({
        "message": "No changes detected.",
        "date_range": f"From {last_state['last_checked'].strftime('%Y-%m-%d')} to {current_date.strftime('%Y-%m-%d')}"
    }), 200

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
    Redirect to the root.
    """
    return redirect(url_for('root'))

@app.route('/ask', methods=['POST'])
def ask():
    """
    Handle user questions and return the answer.
    """
    question = request.form.get('question')
    answer = get_answer(question)
    return render_template('answer.html', question=question, answer=answer)

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
        
        app.logger.debug(f"State received: {state}")
        app.logger.debug(f"Stored state: {stored_state}")
        
        if not state or not stored_state or state != stored_state:
            raise ValueError("State verification failed")
        
        session.pop('oauth_state', None)
        
        code = request.args.get('code')
        app.logger.debug(f"Authorization code received: {code}")
        
        if not code:
            raise ValueError("No authorization code received")

        token = google.authorize_access_token()
        app.logger.debug(f"Access token received: {token}")
        
        if not token:
            raise ValueError("Failed to get access token")
        
        resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
        user_info = resp.json()
        app.logger.debug(f"User info received: {user_info}")
        
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
        app.logger.debug(f"User data updated in MongoDB: {result}")

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
    Redirect to the root.
    """
    user = session.get('user')
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
            text += paragraph.text
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
        'Authorization': f'Bearer app-L6FpZUwrFNaGvrtohJq6x83u',
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
@login_required
def files():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    return render_template('files.html', user=user)

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
        if MODE == 'test':
            user_email = dummy_user['email']
        else:
            user_email = session.get('user', {}).get('email')
            if not user_email:
                return jsonify({"error": "User not logged in."}), 401

        # Extract text from files
        file_content = ""
        for file in uploaded_files:
            try:
                extracted_text = extract_text_from_file(file)
                file_content += f"\n <content>\n{extracted_text} </content>"
            except Exception as e:
                return jsonify({"error": f"Failed to process {file.filename}: {str(e)}"}), 400

        # Retrieve the past 10 conversations from the database by email
        chat_history = chats_collection.find(
            {"email": user_email},  # Using email instead of user_id (now using user_email)
            {"chat_history": {"$slice": -10}}  # Get the last 10 conversations
        ).sort([("timestamp", 1)])  # Sort in ascending order (oldest first)

        # Debugging: Check if chat_history is being fetched correctly
        app.logger.info(f"Chat history retrieved: {chat_history}")

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
        # app.logger.info(f"Formatted chat history: {formatted_history}")

        # Add the formatted chat history to the user query
        user_query = f"<user_question>{user_question}</user_question>"

        # Interact with LLM
        response = get_answer(user_query, file_content, formatted_history)

        # app.logger.info(f"Response from LLM: {response}")

        # Parse the response to separate the actual response and citations
        if "@@@Perplexity Response:" in response:
            actual_response, perplexity_response = response.split("@@@Perplexity Response:", 1)
            response_data = json.loads(perplexity_response)
            actual_response = actual_response.replace("Actual Response:", "").strip()
            citations = response_data.get("citations", [])
        else:
            actual_response = response
            citations = []

        # Log interaction in MongoDB
        for file in uploaded_files:
            file_name = file.filename if file.filename else "empty"
            chats_collection.update_one(
                {"email": user_email, "file_name": file_name},  # Using user_email instead of user_id
                {
                    "$push": {
                        "chat_history": {
                            "question": user_question,
                            "response": actual_response,
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
        print("Response is rishabh   ",actual_response)
        print("Citations is rishabh   ",citations)
        return jsonify({"response": actual_response, "citations": citations})

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

@app.route('/static/<path:filename>')
def serve_static(filename):
    """
    Serve static files.
    """
    return send_from_directory(app.static_folder, filename)

@app.route('/delete-chat', methods=['DELETE'])
@login_required
def delete_chat():
    """
    Delete all chat history for the current user.
    """
    try:
        user_email = session.get('user', {}).get('email')
        if not user_email:
            return jsonify({"error": "User not logged in"}), 401

        # Delete all chat history documents for this user
        result = chats_collection.delete_many({"email": user_email})
        
        if result.deleted_count > 0:
            return jsonify({
                "message": "Chat history deleted successfully",
                "deleted_count": result.deleted_count
            }), 200
        else:
            return jsonify({
                "message": "No chat history found to delete"
            }), 204

    except Exception as e:
        app.logger.error(f"Error deleting chat history: {e}")
        return jsonify({
            "error": "Failed to delete chat history"
        }), 500

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