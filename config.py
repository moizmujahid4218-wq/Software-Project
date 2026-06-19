import os

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-bakery-key'
    
    # We no longer need MySQL credentials! We just tell SQLite where to put the file.
    DATABASE = 'bakery.db'
