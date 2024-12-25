from flask import Flask
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import logging

def create_app():
    app = Flask(__name__)
    load_dotenv()

    # Configuration
    app.secret_key = os.getenv('SECRET_KEY')
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx'}
    app.logger.setLevel(logging.INFO)

    # OAuth configuration
    oauth = OAuth(app)
    app.oauth = oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        access_token_url='https://accounts.google.com/o/oauth2/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
        client_kwargs={'scope': 'email profile'}
    )

    # Register routes
    from app.routes import auth, main, api, files
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(files.bp)

    return app