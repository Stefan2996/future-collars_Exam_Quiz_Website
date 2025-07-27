from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, QuizPack, Question, User, UserQuizStat # Import all necessary models
from sqlalchemy import func
from datetime import datetime
import json # FIXED: Added json import as it is used for json.dumps

packs_bp = Blueprint('packs', __name__)


@packs_bp.route("/packs")
@login_required
def packs():
    """
    Displays a list of all available quiz packs and the current user's overall statistics.
    """
    all_packs = QuizPack.query.all()
    user_overall_stats = {
        'total_correct_answers': 0,
        'total_questions_answered': 0,
        'total_games_played': 0
    }

    # current_user is already available and is a User object from Flask-Login
    # Get all user statistics
    user_all_stats = UserQuizStat.query.filter_by(user_id=current_user.id).all()
    user_overall_stats['total_correct_answers'] = sum(s.score for s in user_all_stats)
    user_overall_stats['total_questions_answered'] = sum(s.total_questions for s in user_all_stats)
    user_overall_stats['total_games_played'] = len(user_all_stats)

    return render_template("packs.html", packs=all_packs, user_stats=user_overall_stats)


@packs_bp.route("/create_pack", methods=['GET', 'POST'])
@login_required
def create_pack():
    """
    Allows a user (administrator) to create a new quiz pack.
    Handles GET for displaying the form and POST for saving data.
    """
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()

        if not title:
            flash('Pack title is required.', 'danger')
            # Return current values for user convenience
            return render_template('create_pack.html', title=title, description=description)

        # Check for duplicate title
        if QuizPack.query.filter_by(title=title).first():
            flash('A pack with this title already exists!', 'danger')
            return render_template('create_pack.html', title=title, description=description)

        new_pack = QuizPack(title=title, description=description)
        db.session.add(new_pack)

        try:
            db.session.commit()
            flash(f'Pack "{title}" successfully created!', 'success')
            return redirect(url_for('packs.edit_pack', pack_id=new_pack.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating pack: {e}", "danger")
            return render_template('create_pack.html', title=title, description=description)

    return render_template('create_pack.html')


@packs_bp.route("/edit_pack/<int:pack_id>", methods=['GET', 'POST'])
@login_required
def edit_pack(pack_id):
    """
    Allows a user (administrator) to edit an existing quiz pack.
    """
    pack = QuizPack.query.get_or_404(pack_id)

    if request.method == 'POST':
        pack.title = request.form.get('title', '').strip()
        pack.description = request.form.get('description', '').strip()

        # Check for duplicate title, excluding the current pack
        existing_pack = QuizPack.query.filter_by(title=pack.title).first()
        if existing_pack and existing_pack.id != pack.id:
            flash("A pack with this title already exists!", "danger")
            # Return current values for user convenience
            questions = Question.query.filter_by(quiz_pack_id=pack.id).order_by(Question.id).all()
            return render_template('edit_pack.html', pack=pack, questions=questions)

        try:
            db.session.commit()
            flash('Pack successfully updated!', 'success')
            return redirect(url_for('packs.edit_pack', pack_id=pack.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating pack: {e}", "danger")
            # Return current values for user convenience
            questions = Question.query.filter_by(quiz_pack_id=pack.id).order_by(Question.id).all()
            return render_template('edit_pack.html', pack=pack, questions=questions)

    questions = Question.query.filter_by(quiz_pack_id=pack.id).order_by(Question.id).all()
    return render_template('edit_pack.html', pack=pack, questions=questions)


@packs_bp.route("/delete_pack/<int:pack_id>", methods=['POST'])
@login_required
def delete_pack(pack_id):
    """
    Allows a user (administrator) to delete a quiz pack and associated data.
    """
    pack = QuizPack.query.get_or_404(pack_id)

    try:
        # Delete related questions and statistics before deleting the pack
        # Use synchronize_session=False for more efficient bulk deletion
        Question.query.filter_by(quiz_pack_id=pack.id).delete(synchronize_session=False)
        UserQuizStat.query.filter_by(quiz_pack_id=pack.id).delete(synchronize_session=False)

        db.session.delete(pack)
        db.session.commit()
        flash('Pack successfully deleted.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting pack: {e}", "danger")
    return redirect(url_for('packs.packs'))


@packs_bp.route("/add_question/<int:pack_id>", methods=['GET', 'POST'])
@login_required
def add_question(pack_id):
    """
    Allows a user (administrator) to add a new question to a quiz pack.
    """
    pack = QuizPack.query.get_or_404(pack_id)

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        options_raw = [request.form.get(f'option_{i}', '').strip() for i in range(4)] # Expect 4 options
        correct_answer_index_str = request.form.get('correct_answer_index', '').strip()

        if not question_text or not all(options_raw) or not correct_answer_index_str: # Check if index is not empty
            flash('Please fill in all question and answer option fields, and specify the correct answer.', 'danger')
            # Return current form values
            return render_template('add_question.html', pack=pack,
                                   question_text=question_text, options=options_raw,
                                   correct_answer_index=correct_answer_index_str)

        try:
            correct_answer_index = int(correct_answer_index_str)
            if not (0 <= correct_answer_index < len(options_raw)):
                raise ValueError("Invalid correct answer index.")
        except ValueError:
            flash('Invalid correct answer index.', 'danger')
            return render_template('add_question.html', pack=pack,
                                   question_text=question_text, options=options_raw,
                                   correct_answer_index=correct_answer_index_str)

        new_question = Question(
            quiz_pack_id=pack.id,
            question_text=question_text,
            options_json=json.dumps(options_raw),
            correct_answer_index=correct_answer_index
        )
        db.session.add(new_question)
        try:
            db.session.commit()
            flash('Question successfully added!', 'success')
            return redirect(url_for('packs.edit_pack', pack_id=pack.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding question: {e}", "danger")
            return render_template('add_question.html', pack=pack,
                                   question_text=question_text, options=options_raw,
                                   correct_answer_index=correct_answer_index_str)

    # For GET request:
    return render_template('add_question.html', pack=pack)


@packs_bp.route("/edit_question/<int:question_id>", methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    """
    Allows a user (administrator) to edit an existing question.
    """
    question = Question.query.get_or_404(question_id)
    pack = QuizPack.query.get_or_404(question.quiz_pack_id)

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        options_raw = [request.form.get(f'option_{i}', '').strip() for i in range(4)] # Expect 4 options
        correct_answer_index_str = request.form.get('correct_answer_index', '').strip()

        if not question_text or not all(options_raw) or not correct_answer_index_str: # Check if index is not empty
            flash('Please fill in all question and answer option fields, and specify the correct answer.', 'danger')
            # Return current form values
            return render_template('edit_question.html', question=question, pack=pack,
                                   options=options_raw, correct_answer_index=correct_answer_index_str)

        try:
            correct_answer_index = int(correct_answer_index_str)
            if not (0 <= correct_answer_index < len(options_raw)):
                raise ValueError("Invalid correct answer index.")
        except ValueError:
            flash('Invalid correct answer index.', 'danger')
            return render_template('edit_question.html', question=question, pack=pack,
                                   options=options_raw, correct_answer_index=correct_answer_index_str)

        question.question_text = question_text
        question.options_json = json.dumps(options_raw)
        question.correct_answer_index = correct_answer_index
        try:
            db.session.commit()
            flash('Question successfully updated!', 'success')
            return redirect(url_for('packs.edit_pack', pack_id=pack.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating question: {e}", "danger")
            return render_template('edit_question.html', question=question, pack=pack,
                                   options=options_raw, correct_answer_index=correct_answer_index_str)

    # For GET request:
    options = question.get_options()
    while len(options) < 4: # Add empty strings if there are fewer than 4 options
        options.append("")

    return render_template('edit_question.html', question=question, pack=pack, options=options)


@packs_bp.route("/delete_question/<int:question_id>", methods=['POST'])
@login_required
def delete_question(question_id):
    """
    Allows a user (administrator) to delete a question.
    """
    question = Question.query.get_or_404(question_id)
    pack = QuizPack.query.get_or_404(question.quiz_pack_id)

    try:
        db.session.delete(question)
        db.session.commit()
        flash('Question successfully deleted.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting question: {e}", "danger")
    return redirect(url_for('packs.edit_pack', pack_id=pack.id))