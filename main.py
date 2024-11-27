from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
import requests
import os
import hashlib
from datetime import datetime
import logging
from dotenv import load_dotenv

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
    client_kwargs={'scope': 'openid email profile'}
)

# Global variable to track the last known hash of the webpage
last_known_hash = None


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
def home():
    """
    Render the homepage with the user interface.
    """
    return render_template('ui_dark.html')


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

    if last_known_hash is None:
        last_known_hash = current_hash
        return jsonify({
            "message": "Initial check completed, no changes detected.",
            "last_modified": last_modified_time.isoformat() if last_modified_time else "Unknown"
        }), 200
    elif current_hash != last_known_hash:
        last_known_hash = current_hash
        return jsonify({
            "message": "The webpage has been updated.",
            "last_modified": last_modified_time.isoformat() if last_modified_time else "Unknown"
        }), 200
    else:
        return jsonify({
            "message": "No changes detected.",
            "last_modified": last_modified_time.isoformat() if last_modified_time else "Unknown"
        }), 200


# Google OAuth Routes
@app.route('/login')
def login():
    """
    Redirect the user to Google's OAuth 2.0 authorization page.
    """
    return google.authorize_redirect(url_for('authorize', _external=True))


@app.route('/authorize')
def authorize():
    """
    Handle the callback from Google OAuth and fetch the user's profile.
    """
    try:
        token = google.authorize_access_token()
        user_info = google.get('userinfo').json()
        session['user'] = user_info
        app.logger.info(f"User logged in: {user_info}")
        return redirect(url_for('dashboard'))
    except Exception as e:
        app.logger.error(f"Error during Google OAuth: {e}")
        return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    """
    Render the dashboard for authenticated users.
    """
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=user)


@app.route('/logout')
def logout():
    """
    Log out the user by clearing the session.
    """
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
