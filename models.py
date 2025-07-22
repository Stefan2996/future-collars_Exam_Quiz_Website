# --- Standard Library Imports ---
from datetime import datetime
import json

# --- Third-Party Library Imports ---
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# --- Database Initialization ---
# The SQLAlchemy object is initialized here, but will be bound to the Flask app in app.py
db = SQLAlchemy()

# --- DATABASE MODEL DEFINITIONS ---

class User(db.Model, UserMixin):
    """
    User model, representing user accounts in the database.
    Inherits UserMixin for integration with Flask-Login (user session management).
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    registered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to UserQuizStat model: one user can have many quiz statistics records.
    quiz_stats = db.relationship('UserQuizStat', backref='user', lazy=True)

    def set_password(self, password):
        """Hashes the provided password and stores it in the database."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        """Returns a string representation of the User object for debugging."""
        return f'<User {self.name}>'

class QuizPack(db.Model):
    """
    Quiz pack model, representing a collection of questions.
    """
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False) # Pack title
    description = db.Column(db.String(500), nullable=True) # Pack description
    image_url = db.Column(db.String(200), nullable=True) # Optional: Image URL for the pack
    color = db.Column(db.String(20), default='blue') # For UI styling
    difficulty = db.Column(db.String(20), default='Легкий') # Pack difficulty levels (e.g., 'Easy', 'Medium', 'Hard')
    time_to_complete_minutes = db.Column(db.Integer, default=10) # Estimated time to complete

    # Relationship to Question model: one quiz pack can contain many questions.
    questions = db.relationship('Question', backref='quiz_pack', lazy=True)

    @property
    def questions_data(self):
        """
        Returns a list of question data suitable for JSON serialization.
        Note: The correct answer index is exposed here, usually for internal/admin use.
        """
        return [{
            'id': q.id,
            'question': q.question_text,
            'options': q.get_options(),
            'correct_answer': q.correct_answer_index
        } for q in self.questions]

    def __repr__(self):
        """Returns a string representation of the QuizPack object for debugging."""
        return f'<QuizPack {self.title}>'

class Question(db.Model):
    """
    Question model, representing an individual question within a QuizPack.
    """
    id = db.Column(db.Integer, primary_key=True)
    quiz_pack_id = db.Column(db.Integer, db.ForeignKey('quiz_pack.id'), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    options_json = db.Column(db.String(1000), nullable=False)
    correct_answer_index = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)

    def get_options(self):
        """Parses the options_json string into a Python list."""
        if self.options_json:
            return json.loads(self.options_json)
        return []

    def __repr__(self):
        """Returns a string representation of the Question object for debugging."""
        return f'<Question {self.id} for {self.quiz_pack.title}>'

class UserQuizStat(db.Model):
    """
    User quiz statistics model, storing the results of quiz completions.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_pack_id = db.Column(db.Integer, db.ForeignKey('quiz_pack.id'), nullable=False)
    score = db.Column(db.Integer, default=0) # Number of correct answers
    total_questions = db.Column(db.Integer, default=0) # Total number of questions in this attempt
    completed_at = db.Column(db.DateTime, default=datetime.utcnow) # Time of quiz completion
    user_answers_data = db.Column(db.Text) # Stores the user's selected answers
    avg_time_per_question = db.Column(db.Float, nullable=True) # Average time per question

    def __repr__(self):
        """Returns a string representation of the UserQuizStat object for debugging."""
        return f'<UserQuizStat ID:{self.id} User:{self.user_id} Pack:{self.quiz_pack_id} Score:{self.score}>'