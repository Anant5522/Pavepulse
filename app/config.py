import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'pavepulse-dev-secret-key-replace-in-production-998877')
    
    # Database config: default to local SQLite if DATABASE_URL not set or MySQL not available
    DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR / "pavepulse.db"}')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration
    UPLOAD_FOLDER = BASE_DIR / 'app' / 'static' / 'uploads'
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 10 * 1024 * 1024)) # 10MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    # AWS S3 Settings
    S3_BUCKET = os.getenv('S3_BUCKET', '')
    AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'ap-south-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', None)
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', None)

    # Optional Google Maps / Places API Key (for 100% Google Places house-number & building autocomplete)
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')
    
    # Pagination
    ITEMS_PER_PAGE = 15
