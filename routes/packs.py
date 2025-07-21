from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, QuizPack, Question, UserQuizStat  # Импортируем из models

packs_bp = Blueprint('packs', __name__)


@packs_bp.route("/packs")
@login_required
def packs():
    all_packs = QuizPack.query.all()
    user_overall_stats = {
        'total_correct_answers': 0,
        'total_questions_answered': 0,
        'total_games_played': 0
    }

    # current_user уже доступен и является объектом User
    user_all_stats = UserQuizStat.query.filter_by(user_id=current_user.id).all()
    user_overall_stats['total_correct_answers'] = sum(s.score for s in user_all_stats)
    user_overall_stats['total_questions_answered'] = sum(s.total_questions for s in user_all_stats)
    user_overall_stats['total_games_played'] = len(user_all_stats)

    return render_template("packs.html", packs=all_packs, user_stats=user_overall_stats)


# Внимание: здесь не было маршрутов для создания/редактирования/удаления паков/вопросов
# в последней части, которую вы прислали.
# Я возьму их из предыдущих версий app.py, которые вы мне отправляли,
# и адаптирую под Blueprints, так как они относятся к администрированию/созданию контента.

@packs_bp.route("/create_pack", methods=['GET', 'POST'])
@login_required
def create_pack():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')

        if not title:
            flash('Название пака обязательно.', 'danger')
            return redirect(url_for('packs.create_pack'))

        new_pack = QuizPack(title=title,
                            description=description)  # Здесь не было author_id в вашей модели QuizPack, но если бы было, добавили бы author_id=current_user.id
        db.session.add(new_pack)

        try:
            db.session.commit()
            flash(f'Пак "{title}" успешно создан!', 'success')
            return redirect(url_for('packs.edit_pack', pack_id=new_pack.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при создании пака: {e}", "error")

    return render_template('create_pack.html')


@packs_bp.route("/edit_pack/<int:pack_id>", methods=['GET', 'POST'])
@login_required
def edit_pack(pack_id):
    pack = QuizPack.query.get_or_404(pack_id)
    # Здесь была бы проверка pack.author_id == current_user.id,
    # если бы у вас в QuizPack было поле author_id
    # if pack.author_id != current_user.id:
    #    flash('У вас нет прав для редактирования этого пака.', 'danger')
    #    return redirect(url_for('packs.packs'))

    if request.method == 'POST':
        pack.title = request.form.get('title')
        pack.description = request.form.get('description')
        db.session.commit()
        flash('Пак успешно обновлен!', 'success')
        return redirect(url_for('packs.edit_pack', pack_id=pack.id))

    questions = Question.query.filter_by(quiz_pack_id=pack.id).order_by(Question.id).all()
    return render_template('edit_pack.html', pack=pack, questions=questions)


@packs_bp.route("/delete_pack/<int:pack_id>", methods=['POST'])
@login_required
def delete_pack(pack_id):
    pack = QuizPack.query.get_or_404(pack_id)
    # Если есть author_id, добавьте проверку:
    # if pack.author_id != current_user.id:
    #     flash('У вас нет прав для удаления этого пака.', 'danger')
    #     return redirect(url_for('packs.packs'))

    try:
        # Удаляем связанные вопросы и статистику
        Question.query.filter_by(quiz_pack_id=pack.id).delete()
        UserQuizStat.query.filter_by(quiz_pack_id=pack.id).delete()

        db.session.delete(pack)
        db.session.commit()
        flash('Пак успешно удален.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении пака: {e}", "error")
    return redirect(url_for('packs.packs'))


@packs_bp.route("/add_question/<int:pack_id>", methods=['GET', 'POST'])
@login_required
def add_question(pack_id):
    pack = QuizPack.query.get_or_404(pack_id)
    # Если есть author_id, добавьте проверку:
    # if pack.author_id != current_user.id:
    #    flash('У вас нет прав для добавления вопросов в этот пак.', 'danger')
    #    return redirect(url_for('packs.packs'))

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        options_raw = [request.form.get(f'option_{i}') for i in range(4)]  # Ожидаем 4 опции
        correct_answer_index = request.form.get('correct_answer_index')

        if not question_text or not all(options_raw) or correct_answer_index is None:
            flash('Пожалуйста, заполните все поля вопроса и вариантов ответа, и укажите правильный ответ.', 'danger')
            return redirect(url_for('packs.add_question', pack_id=pack.id))

        try:
            correct_answer_index = int(correct_answer_index)
            if not (0 <= correct_answer_index < len(options_raw)):
                raise ValueError("Неверный индекс правильного ответа.")
        except ValueError:
            flash('Неверный индекс правильного ответа.', 'danger')
            return redirect(url_for('packs.add_question', pack_id=pack.id))

        new_question = Question(
            quiz_pack_id=pack.id,
            question_text=question_text,
            options_json=json.dumps(options_raw),
            correct_answer_index=correct_answer_index
        )
        db.session.add(new_question)
        try:
            db.session.commit()
            flash('Вопрос успешно добавлен!', 'success')
            return redirect(url_for('packs.edit_pack', pack_id=pack.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при добавлении вопроса: {e}", "error")

    return render_template('add_question.html', pack=pack)


@packs_bp.route("/edit_question/<int:question_id>", methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    pack = QuizPack.query.get_or_404(question.quiz_pack_id)

    # Если есть author_id, добавьте проверку:
    # if pack.author_id != current_user.id:
    #     flash('У вас нет прав для редактирования этого вопроса.', 'danger')
    #     return redirect(url_for('packs.packs'))

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        options_raw = [request.form.get(f'option_{i}') for i in range(4)]  # Ожидаем 4 опции
        correct_answer_index = request.form.get('correct_answer_index')

        if not question_text or not all(options_raw) or correct_answer_index is None:
            flash('Пожалуйста, заполните все поля вопроса и вариантов ответа, и укажите правильный ответ.', 'danger')
            return redirect(url_for('packs.edit_question', question_id=question.id))

        try:
            correct_answer_index = int(correct_answer_index)
            if not (0 <= correct_answer_index < len(options_raw)):
                raise ValueError("Неверный индекс правильного ответа.")
        except ValueError:
            flash('Неверный индекс правильного ответа.', 'danger')
            return redirect(url_for('packs.edit_question', question_id=question.id))

        question.question_text = question_text
        question.options_json = json.dumps(options_raw)
        question.correct_answer_index = correct_answer_index
        try:
            db.session.commit()
            flash('Вопрос успешно обновлен!', 'success')
            return redirect(url_for('packs.edit_pack', pack_id=pack.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при обновлении вопроса: {e}", "error")

    options = question.get_options()
    while len(options) < 4:  # Добавляем пустые строки, если опций меньше 4
        options.append("")

    return render_template('edit_question.html', question=question, pack=pack, options=options)


@packs_bp.route("/delete_question/<int:question_id>", methods=['POST'])
@login_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    pack = QuizPack.query.get_or_404(question.quiz_pack_id)

    # Если есть author_id, добавьте проверку:
    # if pack.author_id != current_user.id:
    #     flash('У вас нет прав для удаления этого вопроса.', 'danger')
    #     return redirect(url_for('packs.packs'))

    try:
        db.session.delete(question)
        db.session.commit()
        flash('Вопрос успешно удален.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении вопроса: {e}", "error")
    return redirect(url_for('packs.edit_pack', pack_id=pack.id))