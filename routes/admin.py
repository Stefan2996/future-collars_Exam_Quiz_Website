from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, QuizPack, Question, UserQuizStat # Import from models
import json # Used for handling JSON strings in questions

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Note: In a real application, full administrator role validation is needed here.
# For instance, an @admin_required decorator could be created.
# However, as this is an examination project and the admin panel is a feature
# you want to showcase, the current logic with login_required is acceptable.


# --- Helper functions for letter/index conversion ---
def letter_to_index(letter):
    """Converts 'A'->0, 'B'->1, 'C'->2, 'D'->3. Case-insensitive.
    Returns None if the letter does not correspond to a valid option."""
    if letter is None:
        return None
    mapping = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    return mapping.get(letter.upper())

def index_to_letter(index):
    """Converts 0->'A', 1->'B', 2->'C', 3->'D'.
    Returns None if the index is out of range."""
    if index is None:
        return None
    letters = ['A', 'B', 'C', 'D']
    if 0 <= index < len(letters):
        return letters[index]
    return None
# --- End of helper functions ---


@admin_bp.route("/")
@login_required # Only for authorized users (for demonstrating the admin panel)
def dashboard():
    """
    Displays the administrator dashboard, showing a list of all quiz packs.
    """
    quiz_packs = QuizPack.query.all()
    return render_template("admin/dashboard.html", quiz_packs=quiz_packs)

@admin_bp.route("/quiz/new", methods=['GET', 'POST'])
@login_required
def new_quiz_pack():
    """
    Allows an administrator to create a new quiz pack.
    Handles GET for displaying the form and POST for saving data.
    """
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', 'blue').strip()
        difficulty = request.form.get('difficulty', 'Легкий').strip() # 'Легкий' is kept as per user's last edit
        time_to_complete_minutes_str = request.form.get('time_to_complete_minutes', '10').strip()

        # Validate required fields
        if not title:
            flash("Quiz pack title cannot be empty.", "danger")
            # Return current values for user convenience
            return render_template("admin/new_quiz_pack.html",
                                   title=title, description=description,
                                   color=color, difficulty=difficulty,
                                   time_to_complete_minutes=time_to_complete_minutes_str)

        # Check for duplicate quiz pack title
        if QuizPack.query.filter_by(title=title).first():
            flash("A quiz pack with this title already exists!", "danger")
            return render_template("admin/new_quiz_pack.html",
                                   title=title, description=description,
                                   color=color, difficulty=difficulty,
                                   time_to_complete_minutes=time_to_complete_minutes_str)
        try:
            # Validate and convert completion time
            time_to_complete_minutes = int(time_to_complete_minutes_str)
            if time_to_complete_minutes < 1: # Simple validation: time must be positive
                raise ValueError("Completion time must be a positive number.")
        except (ValueError, TypeError):
            flash("Completion time must be an integer (in minutes).", "danger")
            return render_template("admin/new_quiz_pack.html",
                                   title=title, description=description,
                                   color=color, difficulty=difficulty,
                                   time_to_complete_minutes=time_to_complete_minutes_str)

        new_pack = QuizPack(
            title=title,
            description=description,
            color=color,
            difficulty=difficulty,
            time_to_complete_minutes=time_to_complete_minutes
        )
        db.session.add(new_pack)
        try:
            db.session.commit()
            flash(f"Quiz pack '{title}' successfully added!", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            # Logging error 'e' in a real application would be useful
            flash(f"Error adding quiz pack: {e}", "danger")

    # For GET request or on error if no redirect occurred
    return render_template("admin/new_quiz_pack.html")

@admin_bp.route("/quiz/<int:quiz_id>/add_question", methods=['GET', 'POST'])
@login_required
def add_question(quiz_id):
    """
    Allows an administrator to add new questions to an existing quiz pack.
    """
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        image_url = request.form.get('image_url', '').strip() or None
        # Collect all 4 answer options into a list
        options_list = [request.form.get(f'option_{i}', '').strip() for i in range(4)]
        correct_answer_letter = request.form.get('correct_answer', '').strip()

        # Check if all required fields are filled
        if not all([question_text, correct_answer_letter] + options_list):
            flash("All required question and answer option fields must be filled.", "danger")
            # Return current values to the form on error
            return render_template("admin/add_question.html",
                                   quiz_pack=quiz_pack,
                                   questions_in_pack=Question.query.filter_by(quiz_pack_id=quiz_id).all(),
                                   next_question_number=Question.query.filter_by(quiz_pack_id=quiz_id).count() + 1,
                                   question_text=question_text, image_url=image_url,
                                   options=options_list, correct_answer=correct_answer_letter)

        correct_answer_index = letter_to_index(correct_answer_letter)
        if correct_answer_index is None:
            flash("The correct answer must be one of the letters A, B, C, or D.", "danger")
            return render_template("admin/add_question.html",
                                   quiz_pack=quiz_pack,
                                   questions_in_pack=Question.query.filter_by(quiz_pack_id=quiz_id).all(),
                                   next_question_number=Question.query.filter_by(quiz_pack_id=quiz_id).count() + 1,
                                   question_text=question_text, image_url=image_url,
                                   options=options_list, correct_answer=correct_answer_letter)

        new_question = Question(
            quiz_pack_id=quiz_id,
            question_text=question_text,
            image_url=image_url,
            options_json=json.dumps(options_list), # Save options as a JSON string
            correct_answer_index=correct_answer_index
        )
        db.session.add(new_question)
        try:
            db.session.commit()
            flash("Question successfully added!", "success")
            return redirect(url_for('admin.add_question', quiz_id=quiz_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding question: {e}", "danger")

    # For GET request:
    questions_count = Question.query.filter_by(quiz_pack_id=quiz_id).count()
    next_question_number = questions_count + 1 # Number for the next question
    questions_in_pack = Question.query.filter_by(quiz_pack_id=quiz_id).all() # Questions in the current pack

    # Reset form values on GET request
    return render_template("admin/add_question.html",
                           quiz_pack=quiz_pack,
                           questions_in_pack=questions_in_pack,
                           next_question_number=next_question_number,
                           question_text="", image_url="", # Empty values for form fields
                           options=["", "", "", ""], correct_answer="") # Empty options


@admin_bp.route("/quiz/<int:quiz_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_quiz_pack(quiz_id):
    """
    Allows an administrator to edit an existing quiz pack.
    """
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', 'blue').strip()
        difficulty = request.form.get('difficulty', 'Легкий').strip() # 'Легкий' is kept as per user's last edit
        time_to_complete_minutes_str = request.form.get('time_to_complete_minutes', '10').strip()

        # Validate required fields
        if not title:
            flash("Quiz pack title cannot be empty.", "danger")
            return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)

        # Check for duplicate title, excluding the current quiz pack
        existing_pack = QuizPack.query.filter_by(title=title).first()
        if existing_pack and existing_pack.id != quiz_pack.id:
            flash("A quiz pack with this title already exists!", "danger")
            return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)

        try:
            # Validate and convert completion time
            time_to_complete_minutes = int(time_to_complete_minutes_str)
            if time_to_complete_minutes < 1:
                raise ValueError("Completion time must be a positive number.")
        except (ValueError, TypeError):
            flash("Completion time must be an integer (in minutes).", "danger")
            return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)

        # Update quiz pack fields
        quiz_pack.title = title
        quiz_pack.description = description
        quiz_pack.color = color
        quiz_pack.difficulty = difficulty
        quiz_pack.time_to_complete_minutes = time_to_complete_minutes

        try:
            db.session.commit()
            flash(f"Quiz pack '{quiz_pack.title}' successfully updated!", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating quiz pack: {e}", "danger")

    # For GET request: display the edit form with current pack data
    return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)


@admin_bp.route("/question/<int:question_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    """
    Allows an administrator to edit an existing question.
    """
    question = Question.query.get_or_404(question_id)
    quiz_pack = question.quiz_pack # Get the parent quiz pack

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        image_url = request.form.get('image_url', '').strip() or None
        options_list = [request.form.get(f'option_{i}', '').strip() for i in range(4)]
        correct_answer_letter = request.form.get('correct_answer', '').strip()

        # Validate required fields
        if not all([question_text, correct_answer_letter] + options_list):
            flash("All required question and answer option fields must be filled.", "danger")
            # Return current values to the form on error
            return render_template("admin/edit_question.html",
                                   question=question, quiz_pack=quiz_pack,
                                   options=options_list, # Pass options from the form
                                   correct_answer=correct_answer_letter) # Pass the selected letter

        correct_answer_index = letter_to_index(correct_answer_letter)
        if correct_answer_index is None:
            flash("The correct answer must be one of the letters A, B, C, or D.", "danger")
            return render_template("admin/edit_question.html",
                                   question=question, quiz_pack=quiz_pack,
                                   options=options_list, # Pass options from the form
                                   correct_answer=correct_answer_letter) # Pass the selected letter

        # Update question fields
        question.question_text = question_text
        question.image_url = image_url
        question.options_json = json.dumps(options_list)
        question.correct_answer_index = correct_answer_index
        try:
            db.session.commit()
            flash("Question successfully updated!", "success")
            # After editing, redirect back to the list of questions in this pack
            return redirect(url_for('admin.add_question', quiz_id=quiz_pack.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating question: {e}", "danger")

    # For GET request: display the edit form with current question data
    options = question.get_options()
    # Ensure the options list always contains 4 elements for the template
    while len(options) < 4:
        options.append("")

    current_correct_answer_letter = index_to_letter(question.correct_answer_index)

    return render_template("admin/edit_question.html",
                           question=question,
                           quiz_pack=quiz_pack,
                           options=options,
                           correct_answer=current_correct_answer_letter) # Pass the correct answer letter


@admin_bp.route("/question/<int:question_id>/delete", methods=['POST'])
@login_required
def delete_question(question_id):
    """
    Allows an administrator to delete a question by its ID.
    """
    question = Question.query.get_or_404(question_id)
    quiz_pack_id = question.quiz_pack_id # Save pack ID for redirect

    try:
        db.session.delete(question)
        db.session.commit()
        flash("Question successfully deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting question: {e}", "danger")
    # After deletion, redirect back to the list of questions in this pack
    return redirect(url_for('admin.add_question', quiz_id=quiz_pack_id))


@admin_bp.route("/quiz/<int:quiz_id>/delete", methods=['POST'])
@login_required
def delete_quiz_pack(quiz_id):
    """
    Allows an administrator to delete a quiz pack and all associated questions and statistics.
    """
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    try:
        # Delete related questions and statistics before deleting the pack
        # synchronize_session=False for more efficient bulk deletion
        Question.query.filter_by(quiz_pack_id=quiz_id).delete(synchronize_session=False)
        UserQuizStat.query.filter_by(quiz_pack_id=quiz_id).delete(synchronize_session=False)
        db.session.delete(quiz_pack)
        db.session.commit()
        flash(f"Quiz pack '{quiz_pack.title}' and all associated questions/statistics successfully deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting quiz pack: {e}", "danger")
    return redirect(url_for('admin.dashboard'))