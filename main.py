from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv
import hashlib
from datetime import datetime
import logging


load_dotenv()



API_URL = os.getenv('API_URL')
API_KEY = os.getenv('API_KEY')

app = Flask(__name__)


last_known_hash = None

URL = 'https://www.revisor.mn.gov/statutes/cite/245D/full'


def get_answer(question):
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

    # Send request
    response = requests.post(API_URL, headers=headers, json=data)
    app.logger.info(response)
    # Parse the response JSON and get the answer
    if response.status_code == 200:
        response_data = response.json()
        return response_data.get('answer', 'No answer received')
    else:
        return f"Error: {response.status_code}"


#Homepage
@app.route('/', methods=['GET'])
def home():
    return render_template('ui_dark.html')


# Ask
@app.route('/ask', methods=['POST'])
def ask():
    question = request.form.get('question')

    answer = get_answer(question)

    return render_template('answer.html', question=question, answer=answer)


def get_page_info(url):
    """Fetch the webpage and return the MD5 hash of its content and Last-Modified timestamp."""
    try:
        response = requests.get(url)
        response.raise_for_status() 
        app.logger.info(response.text)
        page_content = response.text
        page_hash = hashlib.md5(page_content.encode('utf-8')).hexdigest()
        
        last_modified = response.headers.get('Last-Modified')
        
        if last_modified:
            last_modified_time = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")
        else:
            last_modified_time = None
        
        return page_hash, last_modified_time

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the page: {e}")
        return None, None

@app.route('/check-update', methods=['GET'])
def check_update():
    """API endpoint to check if the page has changed and return the last modified timestamp."""
    global last_known_hash

    current_hash, last_modified_time = get_page_info(URL)
    
    if current_hash is None:
        return jsonify({"error": "Failed to fetch page"}), 500

    # Compare with the last known hash
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

if __name__ == '__main__':
    app.run(debug=True)
