from flask import Blueprint, render_template, redirect, url_for, flash, session, jsonify, request
from flask_login import login_required, current_user
from models import db, QuizPack, Question, UserQuizStat # Import all necessary models
import json
import random
from datetime import datetime

# Create a Blueprint for quiz-related routes
quiz_bp = Blueprint('quiz', __name__)


@quiz_bp.route("/static_url")
def static_url_generator():
    """
    Provides a URL for a static file. Used for dynamic image loading.
    Accepts a filename as a query parameter and returns JSON with the URL.
    """
    filename = request.args.get('filename')
    if filename:
        return jsonify(url=url_for('static', filename=filename))
    return jsonify(url=None) # Return None if filename is not provided


@quiz_bp.route("/quiz/<int:pack_id>")
@login_required
def quiz(pack_id):
    """
    Initializes and displays the quiz page for the selected pack.
    Retrieves questions, shuffles them, and stores them in the session for later validation.
    """
    quiz_pack = QuizPack.query.get_or_404(pack_id)

    # Explicitly get all questions for this pack from the database.
    # This ensures we work with actual Question objects.
    all_questions = Question.query.filter_by(quiz_pack_id=pack_id).all()

    if not all_questions:
        flash(f"The quiz '{quiz_pack.title}' currently has no questions.", "info")
        return redirect(url_for('packs.packs'))

    # Convert Question objects into a list of dictionaries for easier JS handling and session storage.
    # Include image_url.
    all_questions_data = []
    for q_obj in all_questions:
        all_questions_data.append({
            'id': q_obj.id,
            'question': q_obj.question_text,
            'options': q_obj.get_options(),  # Use the get_options() method to retrieve choices
            'correct_answer': q_obj.correct_answer_index,
            'image_url': q_obj.image_url if hasattr(q_obj, 'image_url') else None # Ensure image_url exists
        })

    random.shuffle(all_questions_data)  # Shuffle questions so the order is different each time

    # Store necessary question data (ID and correct answer) in the session.
    # This allows us to validate user answers on the backend without sending correct answers to the frontend.
    questions_map_for_session = {str(q['id']): {'correct_answer': q['correct_answer']} for q in all_questions_data}
    session['current_quiz_questions_map'] = questions_map_for_session
    session['current_quiz_pack_id'] = pack_id
    # Limit the quiz session's lifetime if the user is inactive.
    session.permanent = True

    # For the frontend, we pass questions without the 'correct_answer' field.
    js_data_for_template = {
        'pack_id': pack_id,
        'questions': [{
            'id': q['id'],
            'question': q['question'],
            'options': q['options'],
            'image_url': q['image_url']
        } for q in all_questions_data],
        'submit_url': url_for('quiz.submit_quiz'),
        'packs_url': url_for('packs.packs')
    }

    total_questions = len(all_questions_data)
    current_question_index = 0  # Always start with the first question (index 0)

    return render_template("quiz.html",
                           pack=quiz_pack,
                           questions_data_json=json.dumps(js_data_for_template),
                           current_question_index=current_question_index,
                           total_questions=total_questions)


@quiz_bp.route("/submit_quiz", methods=["POST"])
@login_required
def submit_quiz():
    """
    Handles the submission of quiz results by the user.
    Validates answers, calculates score, and saves statistics to the database.
    """
    data = request.get_json() # Get JSON data from the request body
    pack_id = data.get("pack_id")
    user_answers_raw = data.get("answers")
    total_time_taken = data.get("totalTimeTaken")

    # Basic validation of incoming data
    if not pack_id or not isinstance(user_answers_raw, list):
        return jsonify({"success": False, "message": "Invalid quiz data."}), 400

    quiz_pack = QuizPack.query.get(pack_id)
    if not quiz_pack:
        return jsonify({"success": False, "message": "Quiz pack not found."}), 404

    # Retrieve correct answers from the session and clear it
    quiz_questions_map_from_session = session.pop('current_quiz_questions_map', None)
    session.pop('current_quiz_pack_id', None)

    if not quiz_questions_map_from_session:
        # If session data is missing, it could be a resubmission attempt
        # or session expiration.
        return jsonify(
            {"success": False, "message": "Quiz data missing or expired in session. Please start the quiz again."}), 400

    score = 0
    results_for_stat_json = [] # List to save detailed results

    for answer_entry in user_answers_raw:
        question_id = str(answer_entry.get('questionId'))
        selected_answer_index = answer_entry.get('selectedAnswerIndex')

        if question_id in quiz_questions_map_from_session:
            original_question_data = quiz_questions_map_from_session[question_id]
            correct_answer_index = original_question_data['correct_answer']

            is_correct = (selected_answer_index == correct_answer_index)
            if is_correct:
                score += 1

            results_for_stat_json.append({
                'question_id': int(question_id),
                'user_answer_index': selected_answer_index,
                'is_correct': is_correct,
                'correct_answer_index': correct_answer_index # Added for log completeness
            })
        else:
            # Log suspicious activity or question mismatch
            print(f"Warning: Question with ID {question_id} not found in session data. Possible manipulation or error.")
            results_for_stat_json.append({
                'question_id': int(question_id) if question_id.isdigit() else None,
                'user_answer_index': selected_answer_index,
                'is_correct': False, # Consider incorrect if question not from session
                'correct_answer_index': -1 # Unknown
            })


    total_questions_in_pack = len(quiz_questions_map_from_session)

    avg_time_per_question = None
    if total_questions_in_pack > 0 and total_time_taken is not None:
        # Convert milliseconds to seconds for avg_time_per_question
        avg_time_per_question = (total_time_taken / 1000) / total_questions_in_pack

    new_user_quiz_stat = UserQuizStat(
        user_id=current_user.id,
        quiz_pack_id=pack_id,
        score=score,
        total_questions=total_questions_in_pack,
        completed_at=datetime.utcnow(), # Use UTC time for consistency
        user_answers_data=json.dumps(results_for_stat_json),
        avg_time_per_question=avg_time_per_question
    )
    db.session.add(new_user_quiz_stat)

    try:
        db.session.commit()
        flash("Quiz results successfully submitted!", "success")
        return jsonify({
            "success": True,
            "redirect_url": url_for('quiz.quiz_results', pack_id=pack_id, quiz_stat_id=new_user_quiz_stat.id)
        })
    except Exception as e:
        db.session.rollback()
        # Log the actual error for debugging
        print(f"Error saving quiz results: {e}")
        return jsonify({"success": False, "message": "An error occurred while submitting quiz results. Please try again."}), 500


@quiz_bp.route("/quiz_results/<int:pack_id>/<int:quiz_stat_id>")
@login_required
def quiz_results(pack_id, quiz_stat_id):
    """
    Displays detailed results of a specific quiz attempt by the user.
    """
    quiz_pack = QuizPack.query.get_or_404(pack_id)
    current_quiz_stat = UserQuizStat.query.filter_by(
        id=quiz_stat_id,
        user_id=current_user.id, # Ensure statistics belong to the current user
        quiz_pack_id=pack_id
    ).first_or_404()

    results_data = []
    if current_quiz_stat.user_answers_data:
        saved_results = json.loads(current_quiz_stat.user_answers_data)

        # Get all pack questions in one query for efficiency
        all_pack_questions = {str(q.id): q for q in Question.query.filter_by(quiz_pack_id=pack_id).all()}

        for q_data in saved_results:
            question_id = str(q_data['question_id'])
            user_selected_index = q_data['user_answer_index']
            is_correct = q_data['is_correct']

            question_obj = all_pack_questions.get(question_id)
            if question_obj:
                options = question_obj.get_options()
                results_data.append({
                    'question_id': question_obj.id,
                    'question_text': question_obj.question_text,
                    'options': options,
                    'user_selected_index': user_selected_index,
                    'is_correct': is_correct,
                    'correct_answer_index': question_obj.correct_answer_index,
                    'image_url': question_obj.image_url if hasattr(question_obj, 'image_url') else None # Include image_url for results
                })
            else:
                # In case the question was deleted from the pack after the quiz was taken
                results_data.append({
                    'question_id': int(question_id),
                    'question_text': f"Question (ID: {question_id}) not found in pack.",
                    'options': [],
                    'user_selected_index': user_selected_index, # Keep user's selection
                    'is_correct': False, # Consider incorrect if question not found
                    'correct_answer_index': -1 # Unknown
                })

    # Get all user statistics for this pack to calculate overall metrics
    all_attempts_for_pack = UserQuizStat.query.filter_by(
        user_id=current_user.id, quiz_pack_id=pack_id
    ).all()

    total_attempts = len(all_attempts_for_pack)
    best_score = 0
    total_scores_sum = 0
    total_possible_questions = len(quiz_pack.questions) # Total number of questions in the pack

    for attempt in all_attempts_for_pack:
        if attempt.score > best_score:
            best_score = attempt.score
        total_scores_sum += attempt.score

    average_score = (total_scores_sum / total_attempts) if total_attempts > 0 else 0

    pack_stats = {
        'total_attempts': total_attempts,
        'best_score': best_score,
        'average_score': average_score,
        'total_questions_in_pack': total_possible_questions
    }

    js_data_for_template = {
        'score': current_quiz_stat.score,
        'total_questions': current_quiz_stat.total_questions,
        'percentage': int((current_quiz_stat.score / current_quiz_stat.total_questions) * 100) if current_quiz_stat.total_questions > 0 else 0,
        'pack_title': quiz_pack.title,
    }
    results_data_json = json.dumps(js_data_for_template)


    return render_template("results.html",
                           pack=quiz_pack,
                           quiz_stat=current_quiz_stat,
                           results_data=results_data,
                           pack_stats=pack_stats,
                           results_data_json=results_data_json) # ПЕРЕДАЕМ НОВЫЕ ДАННЫЕ В ШАБЛОН