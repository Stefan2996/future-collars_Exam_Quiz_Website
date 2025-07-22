import os

class Config:
    # In the future, it should be replaced with a strong random key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_for_quiz_app_change_me!'

    # Path to the database
    database_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'quiz_app.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{database_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False