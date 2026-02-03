"""
Centralized Environment Configuration
Loads and validates all environment variables from .env file
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Centralized configuration from environment variables"""
    
    # MapmyIndia (Mappls) API
    MAPPLS_API_KEY = os.getenv('MAPPLS_API_KEY')
    MAPPLS_CLIENT_ID = os.getenv('MAPPLS_CLIENT_ID')
    MAPPLS_CLIENT_SECRET = os.getenv('MAPPLS_CLIENT_SECRET')
    
    # Alert System
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
    TWILIO_MESSAGING_SERVICE_SID = os.getenv('TWILIO_MESSAGING_SERVICE_SID')
    
    # Email Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    
    # Emergency Services
    POLICE_API_KEY = os.getenv('POLICE_API_KEY')
    AMBULANCE_API_KEY = os.getenv('AMBULANCE_API_KEY')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    
    @classmethod
    def validate(cls):
        """Validate required environment variables"""
        if not cls.MAPPLS_API_KEY:
            print("⚠️  Warning: MAPPLS_API_KEY not set. GPS features will use mock data.")
        return True

# Validate on import
Config.validate()
