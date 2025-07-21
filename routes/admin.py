from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, QuizPack, Question, UserQuizStat # Импортируем из models
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin') # Добавляем url_prefix

# ВНИМАНИЕ: В реальном приложении здесь нужна полноценная проверка на роль администратора!
# Например, можно создать декоратор @admin_required

@admin_bp.route("/")
@login_required # Только для авторизованных
def dashboard():
    # Placeholder for admin check
    # if not current_user.is_admin: # Пример проверки роли
    #     flash("У вас нет прав доступа к этой странице.", "danger")
    #     return redirect(url_for('main.index'))

    quiz_packs = QuizPack.query.all()
    return render_template("admin/dashboard.html", quiz_packs=quiz_packs)

@admin_bp.route("/quiz/new", methods=['GET', 'POST'])
@login_required
def new_quiz_pack():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        color = request.form.get('color', 'blue')
        difficulty = request.form.get('difficulty', 'Легкий')

        if not title:
            flash("Название квиз-пака не может быть пустым.", "error")
        elif QuizPack.query.filter_by(title=title).first():
            flash("Квиз-пак с таким названием уже существует!", "error")
        else:
            new_pack = QuizPack(title=title, description=description, color=color,
                                difficulty=difficulty)
            db.session.add(new_pack)
            try:
                db.session.commit()
                flash(f"Квиз-пак '{title}' успешно добавлен!", "success")
                return redirect(url_for('admin.dashboard')) # Используем 'admin.dashboard'
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при добавлении квиз-пака: {e}", "error")
    return render_template("admin/new_quiz_pack.html")

@admin_bp.route("/quiz/<int:quiz_id>/add_question", methods=['GET', 'POST'])
@login_required
def add_question(quiz_id):
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        image_url = request.form.get('image_url')
        option_0 = request.form.get('option_0')
        option_1 = request.form.get('option_1')
        option_2 = request.form.get('option_2')
        option_3 = request.form.get('option_3')
        correct_answer_idx_str = request.form.get('correct_answer_index')

        if not all([question_text, option_0, option_1, option_2, option_3, correct_answer_idx_str is not None]):
            flash("Все поля вопроса и вариантов ответа должны быть заполнены.", "error")
        else:
            try:
                correct_answer_index = int(correct_answer_idx_str)
                if not (0 <= correct_answer_index <= 3):
                    raise ValueError("Индекс правильного ответа вне диапазона 0-3.")
            except (ValueError, TypeError):
                flash("Индекс правильного ответа должен быть числом от 0 до 3.", "error")
                return redirect(url_for('admin.add_question', quiz_id=quiz_id)) # Используем 'admin.add_question'

            options_list = [option_0, option_1, option_2, option_3]

            new_question = Question(
                quiz_pack_id=quiz_id,
                question_text=question_text,
                image_url=image_url if image_url else None,
                options_json=json.dumps(options_list),
                correct_answer_index=correct_answer_index
            )
            db.session.add(new_question)
            try:
                db.session.commit()
                flash("Вопрос успешно добавлен!", "success")
                return redirect(url_for('admin.add_question', quiz_id=quiz_id))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при добавлении вопроса: {e}", "error")

    questions_in_pack = Question.query.filter_by(quiz_pack_id=quiz_id).all()
    return render_template("admin/add_question.html", quiz_pack=quiz_pack, questions_in_pack=questions_in_pack)


@admin_bp.route("/quiz/<int:quiz_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_quiz_pack(quiz_id):
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        color = request.form.get('color', 'blue')
        difficulty = request.form.get('difficulty', 'Легкий')

        existing_pack = QuizPack.query.filter_by(title=title).first()
        if not title:
            flash("Название квиз-пака не может быть пустым.", "error")
        elif existing_pack and existing_pack.id != quiz_pack.id:
            flash("Квиз-пак с таким названием уже существует!", "error")
        else:
            quiz_pack.title = title
            quiz_pack.description = description
            quiz_pack.color = color
            quiz_pack.difficulty = difficulty
            try:
                db.session.commit()
                flash(f"Квиз-пак '{quiz_pack.title}' успешно обновлен!", "success")
                return redirect(url_for('admin.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при обновлении квиз-пака: {e}", "error")

    return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)

@admin_bp.route("/question/<int:question_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_pack = question.quiz_pack

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        image_url = request.form.get('image_url')
        option_0 = request.form.get('option_0')
        option_1 = request.form.get('option_1')
        option_2 = request.form.get('option_2')
        option_3 = request.form.get('option_3')
        correct_answer_idx_str = request.form.get('correct_answer_index')

        if not all([question_text, option_0, option_1, option_2, option_3, correct_answer_idx_str is not None]):
            flash("Все поля вопроса и вариантов ответа должны быть заполнены.", "error")
        else:
            try:
                correct_answer_index = int(correct_answer_idx_str)
                if not (0 <= correct_answer_index <= 3):
                    raise ValueError("Индекс правильного ответа вне диапазона 0-3.")
            except (ValueError, TypeError):
                flash("Индекс правильного ответа должен быть числом от 0 до 3.", "error")
                return redirect(url_for('admin.edit_question', question_id=question_id))

            options_list = [option_0, option_1, option_2, option_3]

            question.question_text = question_text
            question.image_url = image_url if image_url else None
            question.options_json = json.dumps(options_list)
            question.correct_answer_index = correct_answer_index
            try:
                db.session.commit()
                flash("Вопрос успешно обновлен!", "success")
                return redirect(url_for('admin.add_question', quiz_id=quiz_pack.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при обновлении вопроса: {e}", "error")

    options = question.get_options()
    while len(options) < 4:
        options.append("")

    return render_template("admin/edit_question.html", question=question, quiz_pack=quiz_pack, options=options)


@admin_bp.route("/question/<int:question_id>/delete", methods=['POST'])
@login_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_pack_id = question.quiz_pack_id

    try:
        db.session.delete(question)
        db.session.commit()
        flash("Вопрос успешно удален.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении вопроса: {e}", "error")
    return redirect(url_for('admin.add_question', quiz_id=quiz_pack_id))


@admin_bp.route("/quiz/<int:quiz_id>/delete", methods=['POST'])
@login_required
def delete_quiz_pack(quiz_id):
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    try:
        Question.query.filter_by(quiz_pack_id=quiz_id).delete()
        UserQuizStat.query.filter_by(quiz_pack_id=quiz_id).delete()
        db.session.delete(quiz_pack)
        db.session.commit()
        flash(f"Квиз-пак '{quiz_pack.title}' и все связанные вопросы/статистика успешно удалены.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении квиз-пака: {e}", "error")
    return redirect(url_for('admin.dashboard'))