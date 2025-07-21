from flask import Blueprint, render_template, redirect, url_for, flash, session, jsonify, request
from flask_login import login_required, current_user
from models import db, QuizPack, Question, UserQuizStat # Импортируем из models
import json
import random
from datetime import datetime

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route("/quiz/<int:pack_id>")
@login_required
def quiz(pack_id):
    quiz_pack = QuizPack.query.get_or_404(pack_id)
    all_questions_data = quiz_pack.questions_data

    if not all_questions_data:
        flash(f"В квизе '{quiz_pack.title}' пока нет вопросов.", "info")
        return redirect(url_for('packs.packs'))

    random.shuffle(all_questions_data)

    # Храним вопросы в сессии для валидации при отправке результатов
    # Ключи словаря должны быть строками, если они приходят из JSON/JS
    questions_map_for_session = {str(q['id']): {'correct_answer': q['correct_answer']} for q in all_questions_data}
    session['current_quiz_questions_map'] = questions_map_for_session
    session['current_quiz_pack_id'] = pack_id

    # Для фронтенда мы передаем вопросы без поля 'correct_answer'
    js_data_for_template = {
        'pack_id': pack_id,
        'questions': [{k: v for k, v in q.items() if k != 'correct_answer'} for q in all_questions_data]
    }

    total_questions = len(all_questions_data)
    current_question_index = 0 # Всегда начинаем с первого вопроса

    return render_template("quiz.html",
                           pack=quiz_pack,
                           questions_data_json=json.dumps(js_data_for_template),
                           current_question_index=current_question_index,
                           total_questions=total_questions)


@quiz_bp.route("/submit_quiz", methods=["POST"])
@login_required
def submit_quiz():
    data = request.get_json()
    pack_id = data.get("pack_id")
    user_answers_raw = data.get("answers")
    total_time_taken = data.get("totalTimeTaken")

    if not pack_id or not isinstance(user_answers_raw, list):
        return jsonify({"success": False, "message": "Некорректные данные квиза."}), 400

    quiz_pack = QuizPack.query.get(pack_id)
    if not quiz_pack:
        return jsonify({"success": False, "message": "Пак квизов не найден."}), 404

    quiz_questions_map_from_session = session.pop('current_quiz_questions_map', None)
    session.pop('current_quiz_pack_id', None)

    if not quiz_questions_map_from_session:
        return jsonify(
            {"success": False, "message": "Данные квиза в сессии отсутствуют. Пожалуйста, начните квиз заново."}), 400

    score = 0
    results_for_stat_json = []

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
                'is_correct': is_correct
            })
        else:
            print(f"Предупреждение: Вопрос с ID {question_id} не найден в данных сессии. Возможно, манипуляция.")

    total_questions_in_pack = len(quiz_questions_map_from_session)

    avg_time_per_question = None
    if total_questions_in_pack > 0 and total_time_taken is not None:
        avg_time_per_question = total_time_taken / total_questions_in_pack

    new_user_quiz_stat = UserQuizStat(
        user_id=current_user.id, # Используем current_user из Flask-Login
        quiz_pack_id=pack_id,
        score=score,
        total_questions=total_questions_in_pack,
        completed_at=datetime.utcnow(),
        user_answers_data=json.dumps(results_for_stat_json),
        avg_time_per_question=avg_time_per_question
    )
    db.session.add(new_user_quiz_stat)

    try:
        db.session.commit()
        flash("Результаты квиза успешно отправлены!", "success")
        return jsonify({
            "success": True,
            "redirect_url": url_for('quiz.quiz_results', pack_id=pack_id, quiz_stat_id=new_user_quiz_stat.id)
        })
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при сохранении результатов квиза: {e}")
        return jsonify({"success": False, "message": "Произошла ошибка при отправке результатов квиза."}), 500

@quiz_bp.route("/quiz_results/<int:pack_id>/<int:quiz_stat_id>")
@login_required
def quiz_results(pack_id, quiz_stat_id):
    quiz_pack = QuizPack.query.get_or_404(pack_id)
    current_quiz_stat = UserQuizStat.query.filter_by(
        id=quiz_stat_id, user_id=current_user.id, quiz_pack_id=pack_id
    ).first_or_404()

    results_data = []
    if current_quiz_stat.user_answers_data:
        saved_results = json.loads(current_quiz_stat.user_answers_data)

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
                    'correct_answer_index': question_obj.correct_answer_index # Добавим для отображения правильного ответа
                })
            else:
                results_data.append({
                    'question_id': int(question_id),
                    'question_text': f"Вопрос (ID: {question_id}) не найден.",
                    'options': [],
                    'user_selected_index': -1,
                    'is_correct': False
                })

    all_attempts_for_pack = UserQuizStat.query.filter_by(
        user_id=current_user.id, quiz_pack_id=pack_id
    ).all()

    total_attempts = len(all_attempts_for_pack)
    best_score = 0
    total_scores_sum = 0
    total_possible_questions = len(quiz_pack.questions)

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

    return render_template("results.html",
                           pack=quiz_pack,
                           quiz_stat=current_quiz_stat,
                           results_data=results_data,
                           pack_stats=pack_stats)