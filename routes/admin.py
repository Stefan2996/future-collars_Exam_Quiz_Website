from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, QuizPack, Question, UserQuizStat # Импортируем из models
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ВНИМАНИЕ: В реальном приложении здесь нужна полноценная проверка на роль администратора!
# Например, можно создать декоратор @admin_required

# --- Вспомогательные функции для конвертации букв/индексов ---
def letter_to_index(letter):
    """Конвертирует 'A'->0, 'B'->1, 'C'->2, 'D'->3. Нечувствительна к регистру."""
    if letter is None:
        return None
    mapping = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    return mapping.get(letter.upper())

def index_to_letter(index):
    """Конвертирует 0->'A', 1->'B', 2->'C', 3->'D'."""
    if index is None:
        return None
    letters = ['A', 'B', 'C', 'D']
    if 0 <= index < len(letters):
        return letters[index]
    return None # Возвращаем None, если индекс вне диапазона
# --- Конец вспомогательных функций ---


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
        # НОВОЕ: Получаем время прохождения при создании
        time_to_complete_minutes_str = request.form.get('time_to_complete_minutes', '10')

        if not title:
            flash("Название квиз-пака не может быть пустым.", "error")
        elif QuizPack.query.filter_by(title=title).first():
            flash("Квиз-пак с таким названием уже существует!", "error")
        else:
            try:
                # Валидация и преобразование времени
                time_to_complete_minutes = int(time_to_complete_minutes_str)
                if time_to_complete_minutes < 1: # Простая валидация
                    raise ValueError("Время прохождения должно быть положительным числом.")
            except (ValueError, TypeError):
                flash("Время прохождения должно быть целым числом (в минутах).", "error")
                # Остаемся на странице с текущими данными формы
                return render_template("admin/new_quiz_pack.html",
                                       title=title, description=description,
                                       color=color, difficulty=difficulty,
                                       time_to_complete_minutes=time_to_complete_minutes_str)


            new_pack = QuizPack(title=title, description=description, color=color,
                                difficulty=difficulty, time_to_complete_minutes=time_to_complete_minutes) # Сохраняем новое поле
            db.session.add(new_pack)
            try:
                db.session.commit()
                flash(f"Квиз-пак '{title}' успешно добавлен!", "success")
                return redirect(url_for('admin.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при добавлении квиз-пака: {e}", "error")
    # При GET-запросе или ошибке возвращаем шаблон
    return render_template("admin/new_quiz_pack.html")

@admin_bp.route("/quiz/<int:quiz_id>/add_question", methods=['GET', 'POST'])
@login_required
def add_question(quiz_id):
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        image_url = request.form.get('image_url', '').strip() or None
        option_0 = request.form.get('option_0', '').strip()
        option_1 = request.form.get('option_1', '').strip()
        option_2 = request.form.get('option_2', '').strip()
        option_3 = request.form.get('option_3', '').strip()
        correct_answer_letter = request.form.get('correct_answer', '').strip()

        if not all([question_text, option_0, option_1, option_2, option_3, correct_answer_letter]):
            flash("Все обязательные поля вопроса и вариантов ответа должны быть заполнены.", "error")
        else:
            correct_answer_index = letter_to_index(correct_answer_letter)

            if correct_answer_index is None:
                flash("Правильный ответ должен быть одной из букв A, B, C или D.", "error")
            else:
                options_list = [option_0, option_1, option_2, option_3]

                new_question = Question(
                    quiz_pack_id=quiz_id,
                    question_text=question_text,
                    image_url=image_url,
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

    # Получаем количество вопросов в паке для отображения следующего номера
    questions_count = Question.query.filter_by(quiz_pack_id=quiz_id).count()
    next_question_number = questions_count + 1

    questions_in_pack = Question.query.filter_by(quiz_pack_id=quiz_id).all()
    return render_template("admin/add_question.html",
                           quiz_pack=quiz_pack,
                           questions_in_pack=questions_in_pack,
                           next_question_number=next_question_number)


@admin_bp.route("/quiz/<int:quiz_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_quiz_pack(quiz_id):
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        color = request.form.get('color', 'blue')
        difficulty = request.form.get('difficulty', 'Легкий')
        # НОВОЕ: Получаем обновленное время прохождения
        time_to_complete_minutes_str = request.form.get('time_to_complete_minutes', '10')

        existing_pack = QuizPack.query.filter_by(title=title).first()
        if not title:
            flash("Название квиз-пака не может быть пустым.", "error")
        elif existing_pack and existing_pack.id != quiz_pack.id:
            flash("Квиз-пак с таким названием уже существует!", "error")
        else:
            try:
                # Валидация времени
                time_to_complete_minutes = int(time_to_complete_minutes_str)
                if time_to_complete_minutes < 1:
                    raise ValueError("Время прохождения должно быть положительным числом.")
            except (ValueError, TypeError):
                flash("Время прохождения должно быть целым числом (в минутах).", "error")
                # Возвращаемся на страницу редактирования с текущим паком
                return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)


            quiz_pack.title = title
            quiz_pack.description = description
            quiz_pack.color = color
            quiz_pack.difficulty = difficulty
            quiz_pack.time_to_complete_minutes = time_to_complete_minutes # Сохраняем новое поле

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
        question_text = request.form.get('question_text', '').strip()
        image_url = request.form.get('image_url', '').strip() or None
        option_0 = request.form.get('option_0', '').strip()
        option_1 = request.form.get('option_1', '').strip()
        option_2 = request.form.get('option_2', '').strip()
        option_3 = request.form.get('option_3', '').strip()
        correct_answer_letter = request.form.get('correct_answer', '').strip()

        if not all([question_text, option_0, option_1, option_2, option_3, correct_answer_letter]):
            flash("Все обязательные поля вопроса и вариантов ответа должны быть заполнены.", "error")
        else:
            correct_answer_index = letter_to_index(correct_answer_letter)

            if correct_answer_index is None:
                flash("Правильный ответ должен быть одной из букв A, B, C или D.", "error")
            else:
                options_list = [option_0, option_1, option_2, option_3]

                question.question_text = question_text
                question.image_url = image_url
                question.options_json = json.dumps(options_list)
                question.correct_answer_index = correct_answer_index
                try:
                    db.session.commit()
                    flash("Вопрос успешно обновлен!", "success")
                    return redirect(url_for('admin.add_question', quiz_id=quiz_pack.id))
                except Exception as e:
                    db.session.rollback()
                    flash(f"Ошибка при обновлении вопроса: {e}", "error")

    # При GET-запросе для отображения формы редактирования
    question.correct_answer = index_to_letter(question.correct_answer_index)

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
        # Удаляем связанные вопросы и статистику перед удалением пака
        Question.query.filter_by(quiz_pack_id=quiz_id).delete()
        UserQuizStat.query.filter_by(quiz_pack_id=quiz_id).delete()
        db.session.delete(quiz_pack)
        db.session.commit()
        flash(f"Квиз-пак '{quiz_pack.title}' и все связанные вопросы/статистика успешно удалены.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении квиз-пака: {e}", "error")
    return redirect(url_for('admin.dashboard'))