from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin # Импортируем UserMixin

# Инициализируем SQLAlchemy здесь, но не привязываем к app пока
db = SQLAlchemy()

# --- ОПРЕДЕЛЕНИЕ МОДЕЛЕЙ БАЗЫ ДАННЫХ ---

class User(db.Model, UserMixin): # Добавляем UserMixin
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    registered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    quiz_stats = db.relationship('UserQuizStat', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.name}>'

class QuizPack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(200), nullable=True)
    color = db.Column(db.String(20), default='blue')
    difficulty = db.Column(db.String(20), default='Легкий')

    questions = db.relationship('Question', backref='quiz_pack', lazy=True)

    @property
    def questions_data(self):
        return [{
            'id': q.id,
            'question': q.question_text,
            'options': q.get_options(),
            'correct_answer': q.correct_answer_index
        } for q in self.questions]

    def __repr__(self):
        return f'<QuizPack {self.title}>'

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_pack_id = db.Column(db.Integer, db.ForeignKey('quiz_pack.id'), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    options_json = db.Column(db.String(1000), nullable=False)
    correct_answer_index = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)

    def get_options(self):
        if self.options_json:
            return json.loads(self.options_json)
        return []

    def __repr__(self):
        return f'<Question {self.id} for {self.quiz_pack.title}>'

class UserQuizStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_pack_id = db.Column(db.Integer, db.ForeignKey('quiz_pack.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_answers_data = db.Column(db.Text)
    avg_time_per_question = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<UserQuizStat ID:{self.id} User:{self.user_id} Pack:{self.quiz_pack_id} Score:{self.score}>'