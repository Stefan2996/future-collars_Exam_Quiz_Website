import os

class Config:
    # Замените на сильный случайный ключ! Можно сгенерировать командой os.urandom(24).hex()
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_for_quiz_app_change_me!'

    # Путь к базе данных
    database_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'quiz_app.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{database_path}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Папка для загрузки аватаров (если вы её используете, хотя в предоставленном коде её не было)
    # UPLOAD_FOLDER = 'static/avatars'
    # MAX_CONTENT_LENGTH = 16 * 1024 * 1024 # Макс. размер файла 16MB