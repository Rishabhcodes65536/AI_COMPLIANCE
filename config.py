# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_URL = os.getenv('API_URL')
    API_KEY = os.getenv('API_KEY')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    SECRET_KEY = os.getenv('SECRET_KEY')
    STATUTE_URL = 'https://www.revisor.mn.gov/statutes/cite/245D/full'
    
    # File upload configs
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
    
    # Logging config
    LOG_LEVEL = 'INFO'