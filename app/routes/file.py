# routes/file_routes.py
from flask import Blueprint, request, jsonify, current_app, session, redirect, url_for, render_template
from utils.content_utils import extract_text_from_file, get_answer
import os

file_bp = Blueprint('file', __name__)

@file_bp.route('/files')
def files():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template('files.html', user=session['user'])

@file_bp.route('/upload', methods=['POST'])
def upload_files():
    uploaded_files = request.files.getlist("files")
    user_question = request.form.get("question", "")
    user_query = f"/n <user_question> {user_question} /n </user_question>"
    
    file_content = ""
    for file in uploaded_files:
        try:
            extracted_text = extract_text_from_file(file)
            file_content += f"\n <file_separator>\n{extracted_text} </file_separator>"
        except Exception as e:
            return jsonify({"error": f"Failed to process {file.filename}: {str(e)}"}), 400

    try:
        response = get_answer(user_query, file_content)
    except Exception as e:
        return jsonify({"error": f"Failed to interact with LLM: {str(e)}"}), 500

    return jsonify({"response": response})

@file_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'message': f'{filename} deleted successfully'})
    else:
        return jsonify({'error': f'{filename} not found'}), 404