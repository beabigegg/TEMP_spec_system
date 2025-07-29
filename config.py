import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'a_default_secret_key_for_development')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    GENERATED_FOLDER = 'generated'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
