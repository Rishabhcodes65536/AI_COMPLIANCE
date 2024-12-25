# routes/auth_routes.py
from flask import Blueprint, url_for, session, redirect, render_template, current_app
from utils.oauth_config import configure_oauth

auth_bp = Blueprint('auth', __name__)
oauth = None
google = None

@auth_bp.record_once
def on_registered(state):
    global oauth, google
    oauth, google = configure_oauth(state.app)

@auth_bp.route('/login')
def login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@auth_bp.route('/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        if not token:
            raise ValueError("Failed to retrieve OAuth token.")

        user_info = google.get('userinfo').json()
        if not user_info or 'email' not in user_info:
            raise ValueError("Incomplete user information received from Google.")

        session['user'] = {
            'name': user_info.get('name', 'User'),
            'email': user_info['email'],
            'picture': user_info.get('picture', '/static/default-profile.png')
        }

        current_app.logger.info(f"User successfully logged in: {user_info}")
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        current_app.logger.error(f"Error during Google OAuth callback: {e}")
        return render_template(
            'error.html',
            message="An error occurred during login. Please try again or contact support.",
            retry_url=url_for('auth.login')
        )

@auth_bp.route('/logout')
def logout():
    session.clear()
    return render_template('ui_dark.html')