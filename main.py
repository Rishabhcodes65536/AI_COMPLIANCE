from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = os.getenv('API_URL')
API_KEY = os.getenv('API_KEY')

app = Flask(__name__)

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

    # Parse the response JSON and get the answer
    if response.status_code == 200:
        response_data = response.json()
        return response_data.get('answer', 'No answer received')
    else:
        return f"Error: {response.status_code}"


#Homepage
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')


# Ask
@app.route('/ask', methods=['POST'])
def ask():
    question = request.form.get('question')

    answer = get_answer(question)

    return render_template('answer.html', question=question, answer=answer)


if __name__ == '__main__':
    app.run(debug=True)
