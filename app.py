from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash  # Для хеширования паролей
import os
import json  # Для хранения answer_options как JSON строки
import random

app = Flask(__name__)

# --- КОНФИГУРАЦИЯ БАЗЫ ДАННЫХ ---
database_path = os.path.join(app.root_path, 'quiz_app.db')  # Новое имя для базы данных
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_super_secret_key_for_quiz_app_change_me!'  # Очень важный секретный ключ

db = SQLAlchemy(app)

# Регистрируем функцию chr() как Jinja2 фильтр
app.jinja_env.filters['chr'] = chr


# --- ОПРЕДЕЛЕНИЕ МОДЕЛЕЙ БАЗЫ ДАННЫХ ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    total_correct_answers = db.Column(db.Integer, default=0)
    total_questions_attempted = db.Column(db.Integer, default=0)

    # Связь с UserQuizStat
    quiz_stats = db.relationship('UserQuizStat', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class QuizPack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(200), nullable=True)

    # Связи
    questions = db.relationship('Question', backref='quiz_pack', lazy=True)
    user_stats = db.relationship('UserQuizStat', backref='quiz_pack', lazy=True)

    def __repr__(self):
        return f'<QuizPack {self.title}>'


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_pack_id = db.Column(db.Integer, db.ForeignKey('quiz_pack.id'), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    # Храним варианты ответов как JSON строку
    # Пример: '{"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"}'
    answer_options_json = db.Column(db.String(1000), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', 'D'
    image_url = db.Column(db.String(200), nullable=True)

    def get_answer_options(self):
        return json.loads(self.answer_options_json)

    def __repr__(self):
        return f'<Question {self.id} for {self.quiz_pack.title}>'


class UserQuizStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_pack_id = db.Column(db.Integer, db.ForeignKey('quiz_pack.id'), nullable=False)
    correct_answers_in_quiz = db.Column(db.Integer, default=0)
    questions_attempted_in_quiz = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)
    total_correct = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)

    # Уникальная комбинация пользователя и квиза, чтобы не было дубликатов статистики
    __table_args__ = (db.UniqueConstraint('user_id', 'quiz_pack_id', name='_user_quiz_uc'),)

    def __repr__(self):
        return f'<UserQuizStat User:{self.user_id} Quiz:{self.quiz_pack_id} Correct:{self.correct_answers_in_quiz}>'


# --- Инициализация БД при запуске приложения ---
# Это гарантирует, что таблицы будут созданы, если их нет.
@app.before_request
def create_tables_if_not_exist():
    # Проверяем, существует ли база данных
    if not os.path.exists(database_path):
        with app.app_context():
            db.create_all()
            print("Database 'quiz_app.db' and tables created.")


# --- МАРШРУТЫ ---

@app.route("/")
def index():
    user = None  # Изначально user равен None
    logged_in = False

    # Можно добавить логику, чтобы отображать разный контент для авторизованных/неавторизованных
    if 'user_id' in session:
        user_id_from_session = session['user_id']
        user = User.query.get(user_id_from_session)  # Пытаемся найти пользователя по ID из сессии

        if user:  # Если пользователь найден в базе данных
            logged_in = True
        else:  # Если user_id есть в сессии, но пользователя нет в БД (старая/недействительная сессия)
            session.pop('user_id', None)  # Удаляем недействительный user_id из сессии
            flash("Ваша сессия устарела или пользователь не найден. Пожалуйста, войдите снова.", "info")
            # Можно перенаправить на страницу логина, или просто продолжить отображение главной как для неавторизованного
            return redirect(url_for('login'))  # Рекомендуется для четкости

        # Передаем user (может быть None) и logged_in в шаблон
    return render_template("index.html", user=user, logged_in=logged_in)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if 'user_id' in session:  # Если пользователь уже вошел, перенаправляем на главную
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([username, email, password, confirm_password]):
            flash("Все поля должны быть заполнены!", "error")
        elif password != confirm_password:
            flash("Пароли не совпадают!", "error")
        elif User.query.filter_by(username=username).first():
            flash("Пользователь с таким именем уже существует!", "error")
        elif User.query.filter_by(email=email).first():
            flash("Пользователь с такой почтой уже зарегистрирован!", "error")
        else:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            try:
                db.session.commit()
                flash("Регистрация успешна! Теперь вы можете войти.", "success")
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при регистрации: {e}", "error")

    return render_template("register.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if 'user_id' in session:  # Если пользователь уже вошел, перенаправляем на главную
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            flash(f"Добро пожаловать, {user.username}!", "success")
            return redirect(url_for('index'))
        else:
            flash("Неверное имя пользователя или пароль.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for('index'))


@app.route("/quiz_list")
def quiz_list():
    if 'user_id' not in session:
        flash("Пожалуйста, войдите, чтобы просматривать квизы.", "warning")
        return redirect(url_for('login'))

    quizzes = QuizPack.query.all()  # Получаем все доступные квизы

    # Можно добавить получение статистики пользователя для каждого квиза здесь
    user_id = session['user_id']
    user_quiz_stats = {stat.quiz_pack_id: stat for stat in UserQuizStat.query.filter_by(user_id=user_id).all()}

    return render_template("quiz_list.html", quizzes=quizzes, user_quiz_stats=user_quiz_stats)


@app.route("/user_stats")
def user_stats():
    if 'user_id' not in session:
        flash("Пожалуйста, войдите, чтобы просматривать свою статистику.", "warning")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Также можно получить статистику по каждому квизу для конкретного пользователя
    quiz_stats = UserQuizStat.query.filter_by(user_id=user.id).all()
    # Если нужно получить названия квизов, можно сделать JOIN или отдельный запрос
    quiz_pack_titles = {pack.id: pack.title for pack in QuizPack.query.all()}

    return render_template("user_profile.html", user=user, quiz_stats=quiz_stats, quiz_pack_titles=quiz_pack_titles)


@app.route("/start_quiz/<int:quiz_id>")
def start_quiz(quiz_id):
    if 'user_id' not in session:
        flash("Пожалуйста, войдите, чтобы начать квиз.", "warning")
        return redirect(url_for('login'))

    quiz_pack = QuizPack.query.get_or_404(quiz_id)
    questions = quiz_pack.questions  # Получаем все вопросы для этого квиза

    if not questions:
        flash(f"В квизе '{quiz_pack.title}' пока нет вопросов.", "info")
        return redirect(url_for('quiz_list'))

    # Получаем ID вопросов и перемешиваем их
    quiz_questions_ids = [q.id for q in questions]
    random.shuffle(quiz_questions_ids)  # <--- ВОТ ГЛАВНОЕ ИЗМЕНЕНИЕ

    # Сохраняем информацию о текущем квизе и вопросах в сессии
    session['current_quiz_id'] = quiz_id
    session['current_question_index'] = 0
    session['quiz_questions_ids'] = quiz_questions_ids  # Используем перемешанный список
    session['quiz_correct_count'] = 0
    session['quiz_history'] = []  # Инициализируем историю ответов, чтобы история начинала собираться с нуля при каждом новом квизе.

    return redirect(url_for('quiz_game'))


@app.route("/quiz_game", methods=['GET', 'POST'])
def quiz_game():
    if 'user_id' not in session or 'current_quiz_id' not in session:
        flash("Квиз не начат или ваша сессия истекла. Пожалуйста, начните квиз заново.", "warning")
        return redirect(url_for('quiz_list'))

    user_id = session['user_id']
    current_quiz_id = session['current_quiz_id']
    quiz_questions_ids = session['quiz_questions_ids']
    current_question_index = session.get('current_question_index', 0)

    # Инициализируем переменные для обратной связи и текста правильного ответа
    feedback_message = None
    correct_answer_text = None

    if request.method == 'POST':
        user_answer_key = request.form.get('answer')  # Получаем ключ ответа, который выбрал пользователь (A, B, C, D)

        if current_question_index < len(quiz_questions_ids):
            current_question_id = quiz_questions_ids[current_question_index]
            question = Question.query.get_or_404(current_question_id)

            # Получаем все варианты ответа, чтобы найти текст по букве
            all_answer_options = question.get_answer_options()

            if user_answer_key == question.correct_answer:
                session['quiz_correct_count'] += 1
                feedback_message = "Верно!"
            else:
                feedback_message = "Неверно!"
                # Находим текст правильного ответа по его букве
                correct_answer_text = all_answer_options.get(question.correct_answer, "Неизвестно")

                # Сохраняем информацию об этом вопросе и ответе в истории квиза
            # (Этот блок выполняется для КАЖДОГО ОТВЕТА, пока квиз не закончится)
            session['quiz_history'].append({
                'question_id': question.id,
                'question_text': question.question_text,
                'image_url': question.image_url,
                'user_answer_key': user_answer_key,  # Что ответил пользователь (A, B, C, D)
                'user_answer_text': all_answer_options.get(user_answer_key, "Не выбран"),  # Текст ответа пользователя
                'correct_answer_key': question.correct_answer,  # Правильная буква (A, B, C, D)
                'correct_answer_text': all_answer_options.get(question.correct_answer, "Неизвестно"),
                # Текст правильного ответа
                'is_correct': (user_answer_key == question.correct_answer)
            })

            # Переходим к следующему вопросу
            session['current_question_index'] += 1
            current_question_index = session['current_question_index']  # Обновляем для дальнейшей логики

        # --- БЛОК ОБРАБОТКИ ЗАВЕРШЕНИЯ КВИЗА (то, что вы спрашивали) ---
        if current_question_index >= len(quiz_questions_ids):
            # Квиз закончен.

            total_questions = len(quiz_questions_ids)
            correct_count = session['quiz_correct_count']
            quiz_pack = QuizPack.query.get(current_quiz_id)
            quiz_pack_title = quiz_pack.title if quiz_pack else "Неизвестный квиз"

            # Обновление общей статистики пользователя
            user = User.query.get(user_id)
            if user:
                user.total_questions_attempted += total_questions
                user.total_correct_answers += correct_count

                # Обновление статистики для конкретного квиза
                user_quiz_stat = UserQuizStat.query.filter_by(user_id=user_id, quiz_pack_id=current_quiz_id).first()
                if not user_quiz_stat:
                    user_quiz_stat = UserQuizStat(user_id=user_id, quiz_pack_id=current_quiz_id, games_played=0,
                                                  total_correct=0, total_questions=0)
                    db.session.add(user_quiz_stat)

                user_quiz_stat.games_played += 1
                user_quiz_stat.total_correct += correct_count
                user_quiz_stat.total_questions += total_questions

                db.session.commit()

            # ПОЛУЧАЕМ ПОЛНУЮ ИСТОРИЮ КВИЗА ИЗ СЕССИИ ПЕРЕД ЕЕ ОЧИСТКОЙ
            quiz_history = session.get('quiz_history', [])

            # Очистка ВСЕЙ сессии, связанной с квизом, после его завершения
            session.pop('current_quiz_id', None)
            session.pop('current_question_index', None)
            session.pop('quiz_questions_ids', None)
            session.pop('quiz_correct_count', None)
            session.pop('quiz_history', None)  # <--- ЭТОТ ПУНКТ ОЧИЩАЕТ СОХРАНЕННУЮ ИСТОРИЮ

            # Перенаправляем на страницу сводки (quiz_summary.html)
            return render_template("quiz_summary.html",
                                   correct_count=correct_count,
                                   total_questions=total_questions,
                                   quiz_pack_title=quiz_pack_title,
                                   quiz_history=quiz_history  # Передаем историю квиза в шаблон
                                   )
        # --- КОНЕЦ БЛОКА ОБРАБОТКИ ЗАВЕРШЕНИЯ КВИЗА ---

    # Логика для отображения следующего вопроса (для GET-запроса или если вопросы еще есть после POST)
    if current_question_index < len(quiz_questions_ids):
        current_question_id = quiz_questions_ids[current_question_index]
        question = Question.query.get_or_404(current_question_id)

        answer_options_dict = question.get_answer_options()
        answer_options_list = list(answer_options_dict.items())
        random.shuffle(answer_options_list)
        answer_options = answer_options_list

        total_questions = len(quiz_questions_ids)
        current_question_num = current_question_index + 1

        return render_template("quiz_game.html",
                               question=question,
                               answer_options=answer_options,
                               total_questions=total_questions,
                               current_question_num=current_question_num,
                               feedback_message=feedback_message,
                               # Передаем сообщение обратной связи (будет None при первом GET)
                               correct_answer_text=correct_answer_text
                               # Передаем текст правильного ответа (будет None при первом GET)
                               )
    else:
        # Этот блок сработает, если пользователь попытается попасть на /quiz_game
        # после завершения квиза без текущей сессии квиза.
        flash("Квиз завершен или неактивен. Пожалуйста, выберите новый квиз.", "info")
        return redirect(url_for('quiz_list'))


@app.route("/quiz_results")
def quiz_results():
    if 'user_id' not in session or 'current_quiz_id' not in session:
        flash("Результаты квиза недоступны.", "warning")
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])
    quiz_id = session['current_quiz_id']
    correct_count = session.get('quiz_correct_count', 0)
    total_questions = len(session.get('quiz_questions_ids', []))
    quiz_pack = QuizPack.query.get(quiz_id)

    # Обновляем общую статистику пользователя
    user.total_correct_answers += correct_count
    user.total_questions_attempted += total_questions

    # Обновляем или создаем статистику пользователя для конкретного квиза
    user_quiz_stat = UserQuizStat.query.filter_by(user_id=user.id, quiz_pack_id=quiz_id).first()
    if user_quiz_stat:
        user_quiz_stat.correct_answers_in_quiz += correct_count
        user_quiz_stat.questions_attempted_in_quiz += total_questions
    else:
        new_stat = UserQuizStat(user_id=user.id, quiz_pack_id=quiz_id,
                                correct_answers_in_quiz=correct_count,
                                questions_attempted_in_quiz=total_questions)
        db.session.add(new_stat)

    try:
        db.session.commit()
        flash("Ваша статистика обновлена!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при сохранении статистики: {e}", "error")

    # Очищаем сессию квиза
    session.pop('current_quiz_id', None)
    session.pop('current_question_index', None)
    session.pop('quiz_questions_ids', None)
    session.pop('quiz_correct_count', None)

    return render_template("quiz_results.html", correct_count=correct_count,
                           total_questions=total_questions, quiz_pack_title=quiz_pack.title)


@app.route("/quiz_summary")
def quiz_summary():
    # Этот маршрут будет вызываться из quiz_game после завершения квиза
    # и уже получит данные через render_template
    # В обычной ситуации, если бы мы не перенаправляли сразу из POST,
    # здесь пришлось бы восстанавливать данные из сессии или БД.
    # Но так как мы делаем render_template напрямую, то здесь отдельная логика не нужна.
    # Просто убедитесь, что вы правильно вызываете его из quiz_game, передавая все нужные параметры.
    pass # Этот маршрут фактически не нужен, если вы рендерите шаблон прямо из quiz_game после POST.
         # Я оставлю его как "заглушку", если вы захотите разделить логику.
         # В текущем решении, вся логика передачи данных происходит в quiz_game.

# --- АДМИН-ПАНЕЛЬ ---

@app.route("/admin")
def admin_dashboard():
    # Пока что не будем делать проверку на админа, добавим позже
    quiz_packs = QuizPack.query.all()
    return render_template("admin/dashboard.html", quiz_packs=quiz_packs)

@app.route("/admin/quiz/new", methods=['GET', 'POST'])
def admin_new_quiz_pack():
    # Здесь будем обрабатывать добавление нового квиз-пака
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')

        if not title:
            flash("Название квиз-пака не может быть пустым.", "error")
        elif QuizPack.query.filter_by(title=title).first():
            flash("Квиз-пак с таким названием уже существует.", "error")
        else:
            new_pack = QuizPack(title=title, description=description)
            db.session.add(new_pack)
            try:
                db.session.commit()
                flash(f"Квиз-пак '{title}' успешно добавлен!", "success")
                return redirect(url_for('admin_dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при добавлении квиз-пака: {e}", "error")
    return render_template("admin/new_quiz_pack.html")

@app.route("/admin/quiz/<int:quiz_id>/add_question", methods=['GET', 'POST'])
def admin_add_question(quiz_id):
    # Здесь будем обрабатывать добавление нового вопроса к квиз-паку
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        image_url = request.form.get('image_url') # Получаем URL картинки
        option_A = request.form.get('option_A')
        option_B = request.form.get('option_B')
        option_C = request.form.get('option_C')
        option_D = request.form.get('option_D')
        correct_answer = request.form.get('correct_answer')

        if not all([question_text, option_A, option_B, option_C, option_D, correct_answer]):
            flash("Все поля вопроса и вариантов ответа должны быть заполнены.", "error")
        elif correct_answer not in ['A', 'B', 'C', 'D']:
            flash("Правильный ответ должен быть A, B, C или D.", "error")
        else:
            answer_options = {
                "A": option_A,
                "B": option_B,
                "C": option_C,
                "D": option_D
            }
            new_question = Question(
                quiz_pack_id=quiz_id,
                question_text=question_text,
                image_url=image_url if image_url else None, # Сохраняем URL картинки
                answer_options_json=json.dumps(answer_options),
                correct_answer=correct_answer
            )
            db.session.add(new_question)
            try:
                db.session.commit()
                flash("Вопрос успешно добавлен!", "success")
                # После добавления вопроса, можно остаться на этой же странице
                return redirect(url_for('admin_add_question', quiz_id=quiz_id))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при добавлении вопроса: {e}", "error")

    return render_template("admin/add_question.html", quiz_pack=quiz_pack)


# --- НОВЫЕ МАРШРУТЫ ДЛЯ РЕДАКТИРОВАНИЯ И УДАЛЕНИЯ КВИЗ-ПАКОВ ---

@app.route("/admin/quiz/<int:quiz_id>/edit", methods=['GET', 'POST'])
def admin_edit_quiz_pack(quiz_id):
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')

        if not title:
            flash("Название квиз-пака не может быть пустым.", "error")
        elif QuizPack.query.filter_by(title=title).first() and QuizPack.query.filter_by(
                title=title).first().id != quiz_pack.id:
            flash("Квиз-пак с таким названием уже существует.", "error")
        else:
            quiz_pack.title = title
            quiz_pack.description = description
            try:
                db.session.commit()
                flash(f"Квиз-пак '{quiz_pack.title}' успешно обновлен!", "success")
                return redirect(url_for('admin_dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при обновлении квиз-пака: {e}", "error")

    return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)


@app.route("/admin/quiz/<int:quiz_id>/delete", methods=['POST'])
def admin_delete_quiz_pack(quiz_id):
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    try:
        # Сначала удаляем все связанные вопросы
        Question.query.filter_by(quiz_pack_id=quiz_id).delete()
        # Удаляем статистику пользователей для этого квиза
        UserQuizStat.query.filter_by(quiz_pack_id=quiz_id).delete()
        db.session.delete(quiz_pack)
        db.session.commit()
        flash(f"Квиз-пак '{quiz_pack.title}' и все его вопросы/статистика успешно удалены.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении квиз-пака: {e}", "error")

    return redirect(url_for('admin_dashboard'))


# --- РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ ВОПРОСОВ ---

@app.route("/admin/question/<int:question_id>/edit", methods=['GET', 'POST'])
def admin_edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_pack = QuizPack.query.get_or_404(question.quiz_pack_id)  # Для ссылки "Назад" и контекста

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        image_url = request.form.get('image_url')
        option_A = request.form.get('option_A')
        option_B = request.form.get('option_B')
        option_C = request.form.get('option_C')
        option_D = request.form.get('option_D')
        correct_answer = request.form.get('correct_answer')

        if not all([question_text, option_A, option_B, option_C, option_D, correct_answer]):
            flash("Все поля вопроса и вариантов ответа должны быть заполнены.", "error")
        elif correct_answer not in ['A', 'B', 'C', 'D']:
            flash("Правильный ответ должен быть A, B, C или D.", "error")
        else:
            answer_options = {
                "A": option_A,
                "B": option_B,
                "C": option_C,
                "D": option_D
            }
            question.question_text = question_text
            question.image_url = image_url if image_url else None
            question.answer_options_json = json.dumps(answer_options)
            question.correct_answer = correct_answer
            try:
                db.session.commit()
                flash("Вопрос успешно обновлен!", "success")
                # После обновления вопроса, можно вернуться к списку вопросов этого квиз-пака
                return redirect(url_for('admin_add_question', quiz_id=quiz_pack.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при обновлении вопроса: {e}", "error")

    # Для GET-запроса, заполняем форму текущими данными вопроса
    current_options = question.get_answer_options()
    return render_template("admin/edit_question.html",
                           question=question,
                           quiz_pack=quiz_pack,
                           current_options=current_options)


@app.route("/admin/question/<int:question_id>/delete", methods=['POST'])
def admin_delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_pack_id = question.quiz_pack_id  # Сохраняем ID пака для редиректа

    try:
        db.session.delete(question)
        db.session.commit()
        flash("Вопрос успешно удален.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении вопроса: {e}", "error")

    return redirect(url_for('admin_add_question', quiz_id=quiz_pack_id))  # Возвращаемся к списку вопросов пака


# --- Запуск приложения ---
if __name__ == '__main__':
    # Эта часть также создаст таблицы при первом запуске, если они не существуют.
    # Но `@app.before_request` более надежен для гарантии создания при любом первом запросе.
    with app.app_context():
        db.create_all()  # Создаем таблицы при запуске app.py напрямую

        # Пример добавления начальных данных для тестирования
        # Добавляем пак и вопросы, если их нет
        if not QuizPack.query.first():
            print("Adding initial quiz data...")
            pack1 = QuizPack(title="Основы Python", description="Базовые вопросы по синтаксису и концепциям Python.")
            pack2 = QuizPack(title="Flask & Web Dev",
                             description="Вопросы по фреймворку Flask и основам веб-разработки.")
            db.session.add_all([pack1, pack2])
            db.session.commit()

            q1_options = json.dumps({"A": "var x = 10;", "B": "x = 10;", "C": "int x = 10;", "D": "set x = 10;"})
            q1 = Question(quiz_pack_id=pack1.id, question_text="Как правильно объявить переменную в Python?",
                          answer_options_json=q1_options, correct_answer="B")

            q2_options = json.dumps(
                {"A": "def func():", "B": "function func():", "C": "func() do:", "D": "define func:"})
            q2 = Question(quiz_pack_id=pack1.id, question_text="Как объявить функцию в Python?",
                          answer_options_json=q2_options, correct_answer="A")

            q3_options = json.dumps({"A": "Python IDE", "B": "pip", "C": "conda", "D": "virtualenv"})
            q3 = Question(quiz_pack_id=pack1.id, question_text="Какой командой устанавливаются пакеты в Python?",
                          answer_options_json=q3_options, correct_answer="B")

            q4_options = json.dumps({"A": "@app.route('/index')", "B": "@app.get('/index')", "C": "@route('/index')",
                                     "D": "app.add_url_rule('/index')"})
            q4 = Question(quiz_pack_id=pack2.id,
                          question_text="Какой декоратор используется для определения маршрутов в Flask?",
                          answer_options_json=q4_options, correct_answer="A")

            q5_options = json.dumps({"A": "SQLObject", "B": "Django ORM", "C": "SQLAlchemy", "D": "Peewee"})
            q5 = Question(quiz_pack_id=pack2.id, question_text="Какая библиотека часто используется как ORM с Flask?",
                          answer_options_json=q5_options, correct_answer="C")

            db.session.add_all([q1, q2, q3, q4, q5])
            db.session.commit()
            print("Initial quiz data added.")

    app.run(debug=True)