from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import json
import random

app = Flask(__name__)

# --- КОНФИГУРАЦИЯ БАЗЫ ДАННЫХ ---
database_path = os.path.join(app.root_path, 'quiz_app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_super_secret_key_for_quiz_app_change_me!'  # ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ ЭТОТ КЛЮЧ!

db = SQLAlchemy(app)

# Регистрируем функцию chr() как Jinja2 фильтр (для букв A, B, C...)
app.jinja_env.filters['chr'] = chr


# Jinja2 фильтр для преобразования в JSON (используется в quiz.html)
def tojson_filter(data):
    return json.dumps(data)


app.jinja_env.filters['tojsonfilter'] = tojson_filter


# --- ОПРЕДЕЛЕНИЕ МОДЕЛЕЙ БАЗЫ ДАННЫХ ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    registered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    quiz_stats = db.relationship('UserQuizStat', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.name}>'


class QuizPack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    image_url = db.Column(db.String(200), nullable=True)
    color = db.Column(db.String(20), default='blue')
    difficulty = db.Column(db.String(20), default='Легкий')

    questions = db.relationship('Question', backref='quiz_pack', lazy=True)

    # user_stats теперь будут относиться к каждой попытке
    # user_stats = db.relationship('UserQuizStat', backref='quiz_pack', lazy=True)

    # Добавляем свойство для получения всех вопросов в удобном JSON-формате
    @property
    def questions_data(self):
        # Возвращаем список словарей с полной информацией о вопросах
        return [{
            'id': q.id,
            'question': q.question_text,
            'options': q.get_options(),
            'correct_answer': q.correct_answer_index
        } for q in self.questions]

    def __repr__(self):
        return f'<QuizPack {self.title}>'


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_pack_id = db.Column(db.Integer, db.ForeignKey('quiz_pack.id'), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    options_json = db.Column(db.String(1000), nullable=False)
    correct_answer_index = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)

    def get_options(self):
        # Добавим проверку на None или пустую строку для options_json
        if self.options_json:
            return json.loads(self.options_json)
        return []

    def __repr__(self):
        return f'<Question {self.id} for {self.quiz_pack.title}>'


class UserQuizStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_pack_id = db.Column(db.Integer, db.ForeignKey('quiz_pack.id'), nullable=False)
    score = db.Column(db.Integer, default=0)  # Количество правильных ответов в этом конкретном прохождении
    total_questions = db.Column(db.Integer, default=0)  # Общее количество вопросов в этом прохождении
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)  # Время завершения квиза
    user_answers_data = db.Column(
        db.Text)  # Хранит JSON-строку с ответами пользователя {'question_id': user_answer_index}

    # Удалено: db.UniqueConstraint('user_id', 'quiz_pack_id', name='_user_quiz_uc')
    # Теперь каждый проход квиза - это отдельная запись в UserQuizStat

    def __repr__(self):
        return f'<UserQuizStat ID:{self.id} User:{self.user_id} Pack:{self.quiz_pack_id} Score:{self.score}>'


# --- Инициализация БД при запуске приложения ---
@app.before_request
def create_tables_if_not_exist():
    # Проверяем, существует ли база данных
    if not os.path.exists(database_path):
        with app.app_context():
            db.create_all()
            print("Database 'quiz_app.db' and tables created.")
            _create_initial_data()  # Вызываем функцию для добавления начальных данных


# Функция для добавления начальных данных
def _create_initial_data():
    if not QuizPack.query.first():
        print("Adding initial quiz data...")
        pack1 = QuizPack(title="Основы Python", description="Базовые вопросы по синтаксису и концепциям Python.",
                         color='blue', difficulty='Легкий')
        pack2 = QuizPack(title="Flask & Web Dev", description="Вопросы по фреймворку Flask и основам веб-разработки.",
                         color='green', difficulty='Средний')
        db.session.add_all([pack1, pack2])
        db.session.commit()  # Сохраняем паки, чтобы получить их ID

        # Теперь добавляем вопросы, используя полученные ID паков
        q1_options = ["var x = 10;", "x = 10;", "int x = 10;", "set x = 10;"]
        q1 = Question(quiz_pack_id=pack1.id, question_text="Как правильно объявить переменную в Python?",
                      options_json=json.dumps(q1_options), correct_answer_index=1)

        q2_options = ["def func():", "function func():", "func() do:", "define func:"]
        q2 = Question(quiz_pack_id=pack1.id, question_text="Как объявить функцию в Python?",
                      options_json=json.dumps(q2_options), correct_answer_index=0)

        q3_options = ["Python IDE", "pip", "conda", "virtualenv"]
        q3 = Question(quiz_pack_id=pack1.id, question_text="Какой командой устанавливаются пакеты в Python?",
                      options_json=json.dumps(q3_options), correct_answer_index=1)

        q4_options = ["@app.route('/index')", "@app.get('/index')", "@route('/index')", "app.add_url_rule('/index')"]
        q4 = Question(quiz_pack_id=pack2.id,
                      question_text="Какой декоратор используется для определения маршрутов в Flask?",
                      options_json=json.dumps(q4_options), correct_answer_index=0)

        q5_options = ["SQLObject", "Django ORM", "SQLAlchemy", "Peewee"]
        q5 = Question(quiz_pack_id=pack2.id, question_text="Какая библиотека часто используется как ORM с Flask?",
                      options_json=json.dumps(q5_options), correct_answer_index=2)

        db.session.add_all([q1, q2, q3, q4, q5])
        db.session.commit()
        print("Initial quiz data added.")


# --- MIDDLEWARE / CONTEXT PROCESSORS ---

@app.before_request
def load_logged_in_user():
    """Загружает пользователя из сессии перед каждым запросом."""
    user_id = session.get('user_id')
    g.user = User.query.get(user_id) if user_id else None


@app.context_processor
def inject_user():
    """Делает объект пользователя доступным во всех Jinja2 шаблонах."""
    return dict(user=g.user)


# --- МАРШРУТЫ ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not all([name, email, password, confirm_password]):
            flash("Все поля должны быть заполнены!", "error")
        elif password != confirm_password:
            flash("Пароли не совпадают!", "error")
        elif User.query.filter_by(name=name).first():
            flash("Пользователь с таким именем уже существует!", "error")
        elif User.query.filter_by(email=email).first():
            flash("Пользователь с такой почтой уже зарегистрирован!", "error")
        else:
            new_user = User(name=name, email=email)
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
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            flash(f"Добро пожаловать, {user.name}!", "success")
            return redirect(url_for('index'))
        else:
            flash("Неверная почта или пароль.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop('user_id', None)
    flash("Вы успешно вышли из аккаунта.", "info")
    return redirect(url_for('index'))


@app.route("/packs")
def packs():
    if not g.user:
        flash("Пожалуйста, войдите, чтобы просматривать квизы.", "warning")
        return redirect(url_for('login'))

    all_packs = QuizPack.query.all()
    user_overall_stats = {
        'total_correct_answers': 0,
        'total_questions_answered': 0,
        'total_games_played': 0
    }

    if g.user:
        # Агрегируем общие показатели по всем квизам пользователя
        user_all_stats = UserQuizStat.query.filter_by(user_id=g.user.id).all()
        user_overall_stats['total_correct_answers'] = sum(s.score for s in user_all_stats)
        user_overall_stats['total_questions_answered'] = sum(s.total_questions for s in user_all_stats)
        user_overall_stats['total_games_played'] = len(user_all_stats)

    return render_template("packs.html", packs=all_packs, user_stats=user_overall_stats)


@app.route("/profile")
def profile():
    if not g.user:
        flash("Пожалуйста, войдите, чтобы просматривать свой профиль.", "warning")
        return redirect(url_for('login'))

    # Общая статистика пользователя
    total_questions_answered = 0
    total_correct_answers = 0

    # Статистика по каждому паку для пользователя
    pack_stats = {}

    # Получаем все записи UserQuizStat для текущего пользователя
    all_user_quiz_stats = UserQuizStat.query.filter_by(user_id=g.user.id).all()

    # Группируем статистику по pack_id
    grouped_stats = {}
    for stat_entry in all_user_quiz_stats:
        if stat_entry.quiz_pack_id not in grouped_stats:
            grouped_stats[stat_entry.quiz_pack_id] = {
                'attempts': 0,
                'total_correct': 0,
                'total_questions': 0,
                'best_score': 0,
                'last_score': 0,  # Это будет последний по времени прохождения
                'latest_completed_at': datetime.min  # Для отслеживания самой свежей записи
            }

        grouped_stats[stat_entry.quiz_pack_id]['attempts'] += 1
        grouped_stats[stat_entry.quiz_pack_id]['total_correct'] += stat_entry.score
        grouped_stats[stat_entry.quiz_pack_id]['total_questions'] += stat_entry.total_questions
        grouped_stats[stat_entry.quiz_pack_id]['best_score'] = max(
            grouped_stats[stat_entry.quiz_pack_id]['best_score'], stat_entry.score
        )

        # Обновляем "последний" результат, если текущая запись новее
        if stat_entry.completed_at > grouped_stats[stat_entry.quiz_pack_id]['latest_completed_at']:
            grouped_stats[stat_entry.quiz_pack_id]['last_score'] = stat_entry.score
            grouped_stats[stat_entry.quiz_pack_id]['latest_completed_at'] = stat_entry.completed_at

    # Формируем pack_stats для шаблона
    for pack_id, stats in grouped_stats.items():
        pack = QuizPack.query.get(pack_id)
        if pack:
            total_questions_answered += stats['total_questions']
            total_correct_answers += stats['total_correct']

            pack_stats[pack.id] = {
                'pack_title': pack.title,
                'attempts': stats['attempts'],
                'best_score': stats['best_score'],
                'last_score': stats['last_score'],
                'total_questions_in_pack': len(pack.questions)  # Общее количество вопросов в этом паке
            }

    return render_template("profile.html",
                           total_questions=total_questions_answered,
                           correct_answers=total_correct_answers,
                           pack_stats=pack_stats)


@app.route("/quiz/<int:pack_id>")
def quiz(pack_id):
    if not g.user:
        flash("Пожалуйста, войдите, чтобы начать квиз.", "warning")
        return redirect(url_for('login'))

    quiz_pack = QuizPack.query.get_or_404(pack_id)
    # Используем свойство questions_data, которое возвращает список словарей
    all_questions_data = quiz_pack.questions_data

    if not all_questions_data:
        flash(f"В квизе '{quiz_pack.title}' пока нет вопросов.", "info")
        return redirect(url_for('packs'))

    # Перемешиваем вопросы
    random.shuffle(all_questions_data)

    # Храним вопросы в сессии для валидации при отправке результатов
    # Используем id вопроса как ключ, чтобы не зависеть от порядка
    # на фронте и бэкенде.
    # ВНИМАНИЕ: Здесь мы сохраняем только необходимые данные для проверки ответа,
    # чтобы не раскрывать правильный ответ на фронтенде или в сессии.
    questions_map_for_session = {str(q['id']): {'correct_answer': q['correct_answer']} for q in all_questions_data}
    session['current_quiz_questions_map'] = questions_map_for_session
    session['current_quiz_pack_id'] = pack_id

    # Для фронтенда мы передаем вопросы без поля 'correct_answer'
    js_data_for_template = {
        'pack_id': pack_id,
        'questions': [{k: v for k, v in q.items() if k != 'correct_answer'} for q in all_questions_data]
    }

    total_questions = len(all_questions_data)
    current_question_index = 0

    return render_template("quiz.html",
                           pack=quiz_pack,
                           questions_data_json=json.dumps(js_data_for_template),
                           current_question_index=current_question_index,
                           total_questions=total_questions)


@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():
    if not g.user:
        return jsonify({"success": False, "message": "Необходима авторизация."}), 401

    data = request.get_json()
    pack_id = data.get("pack_id")
    # user_answers_raw: [{'questionId': 1, 'selectedAnswerIndex': 2}, {'questionId': 2, 'selectedAnswerIndex': 0}]
    user_answers_raw = data.get("answers")

    if not pack_id or not isinstance(user_answers_raw, list):
        return jsonify({"success": False, "message": "Некорректные данные квиза."}), 400

    quiz_pack = QuizPack.query.get(pack_id)
    if not quiz_pack:
        return jsonify({"success": False, "message": "Пак квизов не найден."}), 404

    # Получаем оригинальные вопросы из сессии по их ID
    quiz_questions_map_from_session = session.pop('current_quiz_questions_map', None)
    session.pop('current_quiz_pack_id', None)  # Удаляем pack_id из сессии

    if not quiz_questions_map_from_session:
        return jsonify(
            {"success": False, "message": "Данные квиза в сессии отсутствуют. Пожалуйста, начните квиз заново."}), 400

    score = 0
    user_answers_to_save = {}  # Для сохранения в базу данных

    # Мы больше не собираем 'is_correct' или 'correct_answer_text' в results_data
    # так как они не будут отображаться на странице результатов.
    # Собираем только информацию о вопросе, выбранном ответе и его корректности.
    results_for_stat_json = []

    for answer_entry in user_answers_raw:
        question_id = str(answer_entry.get('questionId'))  # Приводим к строке, т.к. ключи в JSON - строки
        selected_answer_index = answer_entry.get('selectedAnswerIndex')

        if question_id in quiz_questions_map_from_session:
            original_question_data = quiz_questions_map_from_session[question_id]
            correct_answer_index = original_question_data['correct_answer']

            is_correct = (selected_answer_index == correct_answer_index)
            if is_correct:
                score += 1

            # Сохраняем в user_answers_to_save только ID вопроса и выбранный ответ
            user_answers_to_save[question_id] = selected_answer_index

            # Для results_data в quiz_results (если бы мы его использовали для детального отображения)
            # мы могли бы добавить больше полей. Но так как не показываем правильный ответ,
            # нам нужно только, был ли ответ правильным.
            results_for_stat_json.append({
                'question_id': int(question_id),  # Сохраняем как int
                'user_answer_index': selected_answer_index,
                'is_correct': is_correct
            })
        else:
            print(f"Предупреждение: Вопрос с ID {question_id} не найден в данных сессии. Возможно, манипуляция.")

    total_questions_in_pack = len(
        quiz_questions_map_from_session)  # Количество вопросов, по которым были данные в сессии

    # Создаем новую запись UserQuizStat для этого прохождения
    new_user_quiz_stat = UserQuizStat(
        user_id=g.user.id,
        quiz_pack_id=pack_id,
        score=score,
        total_questions=total_questions_in_pack,
        completed_at=datetime.utcnow(),
        user_answers_data=json.dumps(results_for_stat_json)  # Сохраняем отформатированные данные
    )
    db.session.add(new_user_quiz_stat)

    try:
        db.session.commit()
        flash("Результаты квиза успешно отправлены!", "success")
        # Возвращаем URL для редиректа на страницу результатов конкретного прохождения
        return jsonify({
            "success": True,
            "redirect_url": url_for('quiz_results', pack_id=pack_id, quiz_stat_id=new_user_quiz_stat.id)
        })
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при сохранении результатов квиза: {e}")
        return jsonify({"success": False, "message": "Произошла ошибка при отправке результатов квиза."}), 500


@app.route("/quiz_results/<int:pack_id>/<int:quiz_stat_id>")
def quiz_results(pack_id, quiz_stat_id):
    if not g.user:
        flash("Пожалуйста, войдите, чтобы просматривать результаты квиза.", "warning")
        return redirect(url_for('login'))

    quiz_pack = QuizPack.query.get_or_404(pack_id)
    # Получаем конкретную запись статистики для этого прохождения
    current_quiz_stat = UserQuizStat.query.filter_by(
        id=quiz_stat_id, user_id=g.user.id, quiz_pack_id=pack_id
    ).first_or_404()

    # Десериализуем ответы пользователя из results_json (теперь user_answers_data)
    results_data = []
    if current_quiz_stat.user_answers_data:
        saved_results = json.loads(current_quiz_stat.user_answers_data)

        # Получаем все вопросы для этого пака
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
                    # Мы больше НЕ передаем correct_answer_index и correct_answer_text в шаблон,
                    # так как вы просили их не отображать.
                    # 'correct_answer_index': question_obj.correct_answer_index,
                    # 'correct_answer_text': options[question_obj.correct_answer_index]
                })
            else:
                # На случай, если вопрос был удален из пака после прохождения квиза
                results_data.append({
                    'question_id': int(question_id),  # Сохраняем как int
                    'question_text': f"Вопрос (ID: {question_id}) не найден.",
                    'options': [],  # Пустые опции
                    'user_selected_index': -1,  # Неизвестный индекс
                    'is_correct': False
                })

    # --- Общая статистика по паку для пользователя (для блока "Ваша статистика по паку") ---
    # Суммируем все попытки пользователя для этого пака
    all_attempts_for_pack = UserQuizStat.query.filter_by(
        user_id=g.user.id, quiz_pack_id=pack_id
    ).all()

    total_attempts = len(all_attempts_for_pack)
    best_score = 0
    total_scores_sum = 0
    total_possible_questions = len(quiz_pack.questions)  # Общее кол-во вопросов в паке

    for attempt in all_attempts_for_pack:
        if attempt.score > best_score:
            best_score = attempt.score
        total_scores_sum += attempt.score

    average_score = (total_scores_sum / total_attempts) if total_attempts > 0 else 0

    pack_stats = {
        'total_attempts': total_attempts,
        'best_score': best_score,
        'average_score': average_score,  # average_score теперь будет числом, а не строкой
        'total_questions_in_pack': total_possible_questions  # Используем общее количество вопросов в паке
    }

    return render_template("results.html",
                           pack=quiz_pack,
                           quiz_stat=current_quiz_stat,  # Передаем текущую запись статистики
                           results_data=results_data,  # Детальные результаты для каждого вопроса
                           pack_stats=pack_stats)  # Общая статистика по паку


# --- АДМИН-ПАНЕЛЬ ---
# В реальном приложении здесь нужна проверка на роль администратора!

@app.route("/admin")
def admin_dashboard():
    quiz_packs = QuizPack.query.all()
    return render_template("admin/dashboard.html", quiz_packs=quiz_packs)


@app.route("/admin/quiz/new", methods=['GET', 'POST'])
def admin_new_quiz_pack():
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
                return redirect(url_for('admin_dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при добавлении квиз-пака: {e}", "error")
    return render_template("admin/new_quiz_pack.html")


@app.route("/admin/quiz/<int:quiz_id>/add_question", methods=['GET', 'POST'])
def admin_add_question(quiz_id):
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
                return redirect(url_for('admin_add_question', quiz_id=quiz_id))

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
                return redirect(url_for('admin_add_question', quiz_id=quiz_id))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при добавлении вопроса: {e}", "error")

    questions_in_pack = Question.query.filter_by(quiz_pack_id=quiz_id).all()
    return render_template("admin/add_question.html", quiz_pack=quiz_pack, questions_in_pack=questions_in_pack)


@app.route("/admin/quiz/<int:quiz_id>/edit", methods=['GET', 'POST'])
def admin_edit_quiz_pack(quiz_id):
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        color = request.form.get('color', 'blue')
        difficulty = request.form.get('difficulty', 'Легкий')

        # Проверяем на уникальность названия, исключая текущий пак
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
                return redirect(url_for('admin_dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при обновлении квиз-пака: {e}", "error")

    return render_template("admin/edit_quiz_pack.html", quiz_pack=quiz_pack)


@app.route("/admin/quiz/<int:quiz_id>/delete", methods=['POST'])
def admin_delete_quiz_pack(quiz_id):
    quiz_pack = QuizPack.query.get_or_404(quiz_id)

    try:
        # Удаляем связанные вопросы и статистику
        Question.query.filter_by(quiz_pack_id=quiz_id).delete()
        UserQuizStat.query.filter_by(quiz_pack_id=quiz_id).delete()  # Удаляем все записи статистики для этого пака
        db.session.delete(quiz_pack)
        db.session.commit()
        flash(f"Квиз-пак '{quiz_pack.title}' и все его вопросы/статистика успешно удалены.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении квиз-пака: {e}", "error")

    return redirect(url_for('admin_dashboard'))


@app.route("/admin/question/<int:question_id>/edit", methods=['GET', 'POST'])
def admin_edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_pack = QuizPack.query.get_or_404(question.quiz_pack_id)

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
                return redirect(url_for('admin_edit_question', question_id=question_id))

            options_list = [option_0, option_1, option_2, option_3]

            question.question_text = question_text
            question.image_url = image_url if image_url else None
            question.options_json = json.dumps(options_list)
            question.correct_answer_index = correct_answer_index
            try:
                db.session.commit()
                flash("Вопрос успешно обновлен!", "success")
                return redirect(url_for('admin_add_question', quiz_id=quiz_pack.id))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при обновлении вопроса: {e}", "error")

    current_options = question.get_options()
    return render_template("admin/edit_question.html",
                           question=question,
                           quiz_pack=quiz_pack,
                           current_options=current_options)


@app.route("/admin/question/<int:question_id>/delete", methods=['POST'])
def admin_delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz_pack_id = question.quiz_pack_id

    try:
        db.session.delete(question)
        db.session.commit()
        flash("Вопрос успешно удален.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка при удалении вопроса: {e}", "error")

    return redirect(url_for('admin_add_question', quiz_id=quiz_pack_id))


if __name__ == '__main__':
    app.run(debug=True)