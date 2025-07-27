from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User # Import db and User from models
from sqlalchemy import func
from datetime import datetime

# Create a Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    """
    Handles the registration of new users.
    If the user is already authenticated, redirects to the main page.
    Validates form data and creates a new user in the database.
    """
    # If the user is already authenticated, there's no need to register them again
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Get data from the form, using .strip() to remove extra whitespace
        name = request.form.get('name').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()
        confirm_password = request.form.get('confirm_password').strip()

        # Field validation
        if not all([name, email, password, confirm_password]):
            flash("All fields must be filled!", "danger") # Use "danger" for errors
            # Return the template with current form data for user convenience
            return render_template("register.html", name=name, email=email)
        elif password != confirm_password:
            flash("Passwords do not match!", "danger")
            return render_template("register.html", name=name, email=email)
        elif User.query.filter_by(name=name).first():
            flash("A user with this name already exists!", "danger")
            return render_template("register.html", name=name, email=email)
        elif User.query.filter_by(email=email).first():
            flash("A user with this email is already registered!", "danger")
            return render_template("register.html", name=name, email=email)
        else:
            # Create a new user and hash the password
            new_user = User(name=name, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            try:
                db.session.commit()
                flash("Registration successful! You can now log in.", "success")
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback()
                # In a real application, logging the error 'e' might be beneficial
                flash(f"Error during registration: {e}", "danger")
                return render_template("register.html", name=name, email=email)

    # For GET requests, display the registration form
    return render_template("register.html")

@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    """
    Handles user login to the system.
    If the user is already authenticated, redirects to the main page.
    """
    # If the user is already authenticated, there's no need to show them the login page
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password').strip()
        # The "remember me" field can be empty if the checkbox is not checked
        remember_me = True if request.form.get('remember_me') else False

        user = User.query.filter_by(email=email).first()

        # Check for user existence and correct password
        if user and user.check_password(password):
            login_user(user, remember=remember_me) # Log in the user with "remember me" option
            flash(f"Welcome, {user.name}!", "success")
            # Redirect to the next page if specified (e.g., after @login_required),
            # otherwise to the main page
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash("Invalid email or password.", "danger")
            # Return the template with the entered email
            return render_template("login.html", email=email)

    # For GET requests, display the login form
    return render_template("login.html")

@auth_bp.route("/logout")
@login_required # Protect the route: logout is only available to authenticated users
def logout():
    """
    Logs the user out of the system.
    """
    logout_user() # End the Flask-Login user session
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('index'))

@auth_bp.route("/profile")
@login_required # Protect the route: profile is only available to authenticated users
def profile():
    """
    Displays the user profile page with their quiz completion statistics.
    """
    user_id = current_user.id # ID of the currently authenticated user

    # Import models here to avoid potential circular dependencies,
    # if models.py imports auth_bp or has references that depend on it.
    from models import UserQuizStat, QuizPack

    # --- Overall user statistics ---
    # Query to get the sum of all questions and correct answers across all user quizzes
    overall_stats = db.session.query(
        func.sum(UserQuizStat.total_questions),
        func.sum(UserQuizStat.score)
    ).filter_by(user_id=user_id).first()

    total_questions_answered = overall_stats[0] or 0 # Total number of questions answered
    total_correct_answers = overall_stats[1] or 0 # Total number of correct answers

    overall_accuracy = 0.0
    if total_questions_answered > 0:
        overall_accuracy = (total_correct_answers / total_questions_answered) * 100 # Overall accuracy in percentage

    # --- Statistics by quiz pack ---
    pack_stats = {}
    # Get all user quiz statistics entries, sorted by completion time
    all_user_quiz_stats = UserQuizStat.query.filter_by(user_id=user_id).order_by(UserQuizStat.completed_at.asc()).all()

    # Group statistics by quiz_pack_id
    grouped_stats = {}
    for stat_entry in all_user_quiz_stats:
        if stat_entry.quiz_pack_id not in grouped_stats:
            grouped_stats[stat_entry.quiz_pack_id] = {
                'attempts': 0,
                'best_score': 0,
                'last_score': 0,
                'latest_completed_at': datetime.min, # Initialize with minimum date
                'pack_title': '' # Will be filled later
            }

        grouped_stats[stat_entry.quiz_pack_id]['attempts'] += 1 # Increment attempt count
        grouped_stats[stat_entry.quiz_pack_id]['best_score'] = max(
            grouped_stats[stat_entry.quiz_pack_id]['best_score'], stat_entry.score
        ) # Update best score

        # Update last score and completion time if the current entry is newer
        if stat_entry.completed_at and stat_entry.completed_at > grouped_stats[stat_entry.quiz_pack_id]['latest_completed_at']:
            grouped_stats[stat_entry.quiz_pack_id]['last_score'] = stat_entry.score
            grouped_stats[stat_entry.quiz_pack_id]['latest_completed_at'] = stat_entry.completed_at

    # Populate pack_stats with information about each quiz pack
    for pack_id, stats in grouped_stats.items():
        pack = QuizPack.query.get(pack_id)
        if pack:
            pack_stats[pack.id] = {
                'pack_title': pack.title,
                'attempts': stats['attempts'],
                'best_score': stats['best_score'],
                'last_score': stats['last_score'],
                'total_questions_in_pack': len(pack.questions) # Number of questions in the pack
            }

    # --- Additional metrics ---
    total_quizzes_completed = UserQuizStat.query.filter_by(user_id=user_id).count() # Total number of quizzes completed

    # Check for achieving a "flawless quiz" (all answers correct, at least 5 questions)
    has_flawless_quiz = db.session.query(UserQuizStat).filter(
        UserQuizStat.user_id == user_id,
        UserQuizStat.score == UserQuizStat.total_questions, # Score equals total number of questions
        UserQuizStat.total_questions >= 5 # At least 5 questions
    ).first() is not None

    # Check for achieving a "sharpshooter speed quiz" (fast and accurate quiz)
    has_sharpshooter_speed_quiz = db.session.query(UserQuizStat).filter(
        UserQuizStat.user_id == user_id,
        UserQuizStat.total_questions >= 5, # At least 5 questions
        UserQuizStat.avg_time_per_question <= 3.0, # Average time per question <= 3 seconds
        (UserQuizStat.score * 100.0 / UserQuizStat.total_questions) >= 80.0 # Accuracy >= 80%
    ).first() is not None

    return render_template("profile.html",
                           total_questions=total_questions_answered,
                           correct_answers=total_correct_answers,
                           overall_accuracy=overall_accuracy,
                           pack_stats=pack_stats,
                           total_quizzes_completed=total_quizzes_completed,
                           has_flawless_quiz=has_flawless_quiz,
                           has_sharpshooter_speed_quiz=has_sharpshooter_speed_quiz)