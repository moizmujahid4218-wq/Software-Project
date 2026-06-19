import os

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-bakery-key'
    
    # Database Configuration
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = '1234' # Leave blank if you don't have a password on local mysql
    DB_NAME = 'bakery_db'
