# routes/main_routes.py
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from datetime import datetime
from utils.content_utils import fetch_webpage_content, get_answer

main_bp = Blueprint('main', __name__)

last_known_hash = None
initial_date = datetime(2024, 11, 1)

@main_bp.route('/')
def root():
    return render_template('new_ui.html')

@main_bp.route('/home')
def home():
    return render_template('new_ui.html')

@main_bp.route('/dashboard')
def dashboard():
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    return render_template('new_ui.html', user=user)

@main_bp.route('/ask', methods=['POST'])
def ask():
    question = request.form.get('question')
    answer = get_answer(question)
    return render_template('answer.html', question=question, answer=answer)

@main_bp.route('/check-update', methods=['GET'])
def check_update():
    global last_known_hash

    current_hash, last_modified_time = fetch_webpage_content(current_app.config['STATUTE_URL'])

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