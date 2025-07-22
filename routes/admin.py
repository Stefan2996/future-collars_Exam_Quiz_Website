from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, QuizPack, Question, UserQuizStat # Импортируем из models
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# В реальном приложении здесь нужна полноценная проверка на роль администратора
# Например, можно создать декоратор @admin_required
# Так как это просто экзаменационная работа и админ панель - часть функционала, который я хочу показать

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
    """
    Отображает панель управления администратора со списком квиз-паков
    """
    quiz_packs = QuizPack.query.all()
    return render_template("admin/dashboard.html", quiz_packs=quiz_packs)

@admin_bp.route("/quiz/new", methods=['GET', 'POST'])
@login_required
def new_quiz_pack():
    """
    Позволяет администратору создавать новый квиз-пак.
    Обрабатывает GET для отображения формы и POST для сохранения данных
    """
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        color = request.form.get('color', 'blue')
        difficulty = request.form.get('difficulty', 'Легкий')
        time_to_complete_minutes_str = request.form.get('time_to_complete_minutes', '10')

        # Валидация обязательных полей
        if not title:
            flash("Название квиз-пака не может быть пустым.", "danger")
            # Возвращаем текущие значения для удобства пользователя
            return render_template("admin/new_quiz_pack.html",
                                   title=title, description=description,
                                   color=color, difficulty=difficulty,
                                   time_to_complete_minutes=time_to_complete_minutes_str)

        # Проверка на дублирование названия квиз-пака
        if QuizPack.query.filter_by(title=title).first():
            flash("Квиз-пак с таким названием уже существует!", "danger")
            return render_template("admin/new_quiz_pack.html",
                                   title=title, description=description,
                                   color=color, difficulty=difficulty,
                                   time_to_complete_minutes=time_to_complete_minutes_str)
        try:
            # Валидация и преобразование времени прохождения
            time_to_complete_minutes = int(time_to_complete_minutes_str)
            if time_to_complete_minutes < 1:  # Простая валидация: время должно быть положительным
                raise ValueError("Время прохождения должно быть положительным числом.")
        except (ValueError, TypeError):
            flash("Время прохождения должно быть целым числом (в минутах).", "danger")
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
            flash(f"Квиз-пак '{title}' успешно добавлен!", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            # Логирование ошибки 'e' в реальном приложении было бы полезно
            flash(f"Ошибка при добавлении квиз-пака: {e}", "danger")

    # При GET-запросе или ошибке возвращаем шаблон
    return render_template("admin/new_quiz_pack.html")

@admin_bp.route("/quiz/<int:quiz_id>/add_question", methods=['GET', 'POST'])
@login_required
def add_question(quiz_id):
    """
    Позволяет администратору добавлять новые вопросы к существующему квиз-паку
    """
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        image_url = request.form.get('image_url', '').strip() or None
        # Собираем все 4 варианта ответа в список
        options_list = [request.form.get(f'option_{i}', '').strip() for i in range(4)]
        correct_answer_letter = request.form.get('correct_answer', '').strip()

        # Проверяем, что все обязательные поля заполнены
        if not all([question_text, correct_answer_letter] + options_list):
            flash("Все обязательные поля вопроса и вариантов ответа должны быть заполнены.", "danger")
            # Возвращаем текущие значения в форму при ошибке
            return render_template("admin/add_question.html",
                                   quiz_pack=quiz_pack,
                                   questions_in_pack=Question.query.filter_by(quiz_pack_id=quiz_id).all(),
                                   next_question_number=Question.query.filter_by(quiz_pack_id=quiz_id).count() + 1,
                                   question_text=question_text, image_url=image_url,
                                   options=options_list, correct_answer=correct_answer_letter)

        correct_answer_index = letter_to_index(correct_answer_letter)
        if correct_answer_index is None:
            flash("Правильный ответ должен быть одной из букв A, B, C или D.", "danger")
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
            options_json=json.dumps(options_list), # Сохраняем варианты как JSON-строку
            correct_answer_index=correct_answer_index
        )
        db.session.add(new_question)
        try:
            db.session.commit()
            flash("Вопрос успешно добавлен!", "success")
            return redirect(url_for('admin.add_question', quiz_id=quiz_id))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при добавлении вопроса: {e}", "danger")

    # Для GET-запроса:
    questions_count = Question.query.filter_by(quiz_pack_id=quiz_id).count()
    next_question_number = questions_count + 1 # Номер для следующего вопроса
    questions_in_pack = Question.query.filter_by(quiz_pack_id=quiz_id).all() # Вопросы в текущем паке

    # Сбрасываем значения формы при GET-запросе
    return render_template("admin/add_question.html",
                           quiz_pack=quiz_pack,
                           questions_in_pack=questions_in_pack,
                           next_question_number=next_question_number,
                           question_text="", image_url="", # Пустые значения для полей формы
                           options=["", "", "", ""], correct_answer="") # Пустые опции


@admin_bp.route("/quiz/<int:quiz_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_quiz_pack(quiz_id):
    """
    Позволяет администратору редактировать существующий квиз-пак
    """
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', 'blue').strip()
        difficulty = request.form.get('difficulty', 'Легкий').strip()
        time_to_complete_minutes_str = request.form.get('time_to_complete_minutes', '10').strip()

        # Валидация обязательных полей
        if not title:
            flash("Название квиз-пака не может быть пустым.", "danger")
            return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)

        # Проверка на дублирование названия, исключая текущий квиз-пак
        existing_pack = QuizPack.query.filter_by(title=title).first()
        if existing_pack and existing_pack.id != quiz_pack.id:
            flash("Квиз-пак с таким названием уже существует!", "danger")
            return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)

        try:
            # Валидация и преобразование времени прохождения
            time_to_complete_minutes = int(time_to_complete_minutes_str)
            if time_to_complete_minutes < 1:
                raise ValueError("Время прохождения должно быть положительным числом.")
        except (ValueError, TypeError):
            flash("Время прохождения должно быть целым числом (в минутах).", "danger")
            return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)

        # Обновление полей квиз-пака
        quiz_pack.title = title
        quiz_pack.description = description
        quiz_pack.color = color
        quiz_pack.difficulty = difficulty
        quiz_pack.time_to_complete_minutes = time_to_complete_minutes

        try:
            db.session.commit()
            flash(f"Квиз-пак '{quiz_pack.title}' успешно обновлен!", "success")
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при обновлении квиз-пака: {e}", "danger")

    # Для GET-запроса: отображаем форму редактирования с текущими данными пака
    return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)


@admin_bp.route("/question/<int:question_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    """
    Позволяет администратору редактировать существующий вопрос
    """
    question = Question.query.get_or_404(question_id)
    quiz_pack = question.quiz_pack # Получаем родительский квиз-пак

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        image_url = request.form.get('image_url', '').strip() or None
        options_list = [request.form.get(f'option_{i}', '').strip() for i in range(4)]
        correct_answer_letter = request.form.get('correct_answer', '').strip()

        # Валидация обязательных полей
        if not all([question_text, correct_answer_letter] + options_list):
            flash("Все обязательные поля вопроса и вариантов ответа должны быть заполнены.", "danger")
            # Возвращаем текущие значения в форму при ошибке
            return render_template("admin/edit_question.html",
                                   question=question, quiz_pack=quiz_pack,
                                   options=options_list, # Передаем опции из формы
                                   correct_answer=correct_answer_letter) # Передаем выбранную букву

        correct_answer_index = letter_to_index(correct_answer_letter)
        if correct_answer_index is None:
            flash("Правильный ответ должен быть одной из букв A, B, C или D.", "danger")
            return render_template("admin/edit_question.html",
                                   question=question, quiz_pack=quiz_pack,
                                   options=options_list, # Передаем опции из формы
                                   correct_answer=correct_answer_letter) # Передаем выбранную букву

        # Обновление полей вопроса
        question.question_text = question_text
        question.image_url = image_url
        question.options_json = json.dumps(options_list)
        question.correct_answer_index = correct_answer_index
        try:
            db.session.commit()
            flash("Вопрос успешно обновлен!", "success")
            # После редактирования возвращаемся к списку вопросов в этом паке
            return redirect(url_for('admin.add_question', quiz_id=quiz_pack.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при обновлении вопроса: {e}", "danger")

    # Для GET-запроса: отображаем форму редактирования с текущими данными вопроса
    options = question.get_options()
    # Убедимся, что список опций всегда содержит 4 элемента для шаблона
    while len(options) < 4:
        options.append("")

    current_correct_answer_letter = index_to_letter(question.correct_answer_index)

    return render_template("admin/edit_question.html",
                           question=question,
                           quiz_pack=quiz_pack,
                           options=options,
                           correct_answer=current_correct_answer_letter) # Передаем букву правильного ответа


@admin_bp.route("/question/<int:question_id>/delete", methods=['POST'])
@login_required
def delete_question(question_id):
    """
    Позволяет администратору удалить вопрос по его ID.
    """
    question = Question.query.get_or_404(question_id)
    quiz_pack_id = question.quiz_pack_id # Сохраняем ID пакета для редиректа

    try:
        db.session.delete(question)
        db.session.commit()
        flash("Вопрос успешно удален.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении вопроса: {e}", "danger")
    # После удаления возвращаемся к списку вопросов в этом паке
    return redirect(url_for('admin.add_question', quiz_id=quiz_pack_id))


@admin_bp.route("/quiz/<int:quiz_id>/delete", methods=['POST'])
@login_required
def delete_quiz_pack(quiz_id):
    """
    Позволяет администратору удалить квиз-пак и все связанные с ним вопросы и статистику.
    """
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    try:
        # Удаляем связанные вопросы и статистику перед удалением пака
        # synchronize_session=False для более эффективного массового удаления
        Question.query.filter_by(quiz_pack_id=quiz_id).delete(synchronize_session=False)
        UserQuizStat.query.filter_by(quiz_pack_id=quiz_id).delete(synchronize_session=False)
        db.session.delete(quiz_pack)
        db.session.commit()
        flash(f"Квиз-пак '{quiz_pack.title}' и все связанные вопросы/статистика успешно удалены.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении квиз-пака: {e}", "danger")
    return redirect(url_for('admin.dashboard'))