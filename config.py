import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    # Base directories
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    SCORES_FILE = os.path.join(DATA_DIR, 'scores.json')
    UPLOADS_DIR = os.path.join(DATA_DIR, 'uploaded_images')
    
    # Create necessary directories
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    
    # Game settings
    TARGET_SCORE = 2500000
    OCR_CONFIDENCE_THRESHOLD = 0.8
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    ADMIN_KEY = os.getenv('ADMIN_KEY', 'pinball123')
    OCR_API_KEY = os.getenv('OCR_API_KEY')
    
    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # OCR settings
    OCR_ENGINE = 2  # More accurate but slower
    OCR_LANGUAGE = 'eng'
    OCR_DEBUG = True  # Enable debug logging for OCR
    OCR_MIN_SCORE_LENGTH = 5  # Minimum digits for a valid score
    OCR_MAX_SCORE_LENGTH = 15  # Maximum digits for a valid score