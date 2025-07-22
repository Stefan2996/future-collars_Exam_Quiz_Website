# --- Basic Python Imports ---
import json

# --- Flask and Extension Imports ---
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager
from flask_migrate import Migrate

# --- Project File Imports ---
from models import db, User, QuizPack, Question, UserQuizStat # Import db and models from models
from config import Config

# --- Blueprint Imports ---
from routes.auth import auth_bp
from routes.packs import packs_bp
from routes.quiz import quiz_bp
from routes.admin import admin_bp


# --- Flask App Initialization ---
app = Flask(__name__)
app.config.from_object(Config) # Load configuration from the Config class

# --- Extension Initialization ---
db.init_app(app) # Bind db to the app
migrate = Migrate(app, db) # Initialize Flask-Migrate after DB

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login' # Tell Flask-Login where to redirect for login

# --- User Loader for Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    """Callback function for Flask-Login, loads a user by ID."""
    return User.query.get(int(user_id))

# --- Jinja2 Filters ---
app.jinja_env.filters['chr'] = chr
app.jinja_env.filters['tojsonfilter'] = json.dumps # Use standard json.dumps directly

# --- Blueprint Registration ---
app.register_blueprint(auth_bp)
app.register_blueprint(packs_bp)
app.register_blueprint(quiz_bp)
app.register_blueprint(admin_bp) # Register the admin blueprint

# --- Main Route ---
@app.route("/")
def index():
    """Main page of the application."""
    return render_template("index.html")

# --- 404 Error Handler ---
@app.errorhandler(404)
def page_not_found(e):
    """Handler for page not found (404) errors."""
    return render_template('404.html'), 404

# --- Application Run ---
if __name__ == "__main__":
    # Run the application in debug mode (debug=True)
    # Use debug=False for production
    with app.app_context():
        app.run(debug=True)