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
        # ВОССТАНОВЛЕНО: Хеширование пароля для безопасности
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # ВОССТАНОВЛЕНО: Проверка хешированного пароля
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
    user_stats = db.relationship('UserQuizStat', backref='quiz_pack', lazy=True)

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
        return json.loads(self.options_json)

    def __repr__(self):
        return f'<Question {self.id} for {self.quiz_pack.title}>'


class UserQuizStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_pack_id = db.Column(db.Integer, db.ForeignKey('quiz_pack.id'), nullable=False)
    games_played = db.Column(db.Integer, default=0)
    total_correct = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    last_score = db.Column(db.Integer, default=0)
    best_score = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint('user_id', 'quiz_pack_id', name='_user_quiz_uc'),)

    def __repr__(self):
        return f'<UserQuizStat User:{self.user_id} Quiz:{self.quiz_pack_id} Best:{self.best_score}>'


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
        db.session.commit()

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
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)

@app.context_processor
def inject_user():
    """Делает объект пользователя доступным во всех Jinja2 шаблонах."""
    return dict(user=g.user)


# --- МАРШРУТЫ ---

@app.route("/")
def index():
    # user больше не нужно передавать явно, он доступен через g.user / context_processor
    return render_template("index.html")


@app.route("/register", methods=['GET', 'POST'])
def register():
    if g.user: # Используем g.user вместо 'user_id' in session
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
            new_user.set_password(password) # Теперь хеширует
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
    if g.user: # Используем g.user вместо 'user_id' in session
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        # check_password теперь сравнивает хеши
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
    flash("Вы успешно вышли из аккаунта.", "info") # Изменил сообщение для ясности
    return redirect(url_for('index'))


@app.route("/packs")
def packs():
    if not g.user:
        flash("Пожалуйста, войдите, чтобы просматривать квизы.", "warning")
        return redirect(url_for('login'))

    all_packs = QuizPack.query.all()
    user_overall_stats = None # Инициализируем None по умолчанию

    # Если пользователь вошел в систему, получаем его общую статистику
    if g.user:
        # Суммируем все total_correct и total_questions из всех записей UserQuizStat для текущего пользователя
        total_correct_answers = db.session.query(
            func.sum(UserQuizStat.total_correct)
        ).filter_by(user_id=g.user.id).scalar() or 0

        total_questions_answered = db.session.query(
            func.sum(UserQuizStat.total_questions)
        ).filter_by(user_id=g.user.id).scalar() or 0

        # Создаем простой объект (или можно использовать dict), чтобы передать общую статистику в шаблон
        class UserOverallStats:
            def __init__(self, correct, total):
                self.correct_answers = correct
                self.total_questions = total
                self.games_played = 0 # Можно добавить, если нужно для отображения на packs
                self.best_score = 0   # Если нужно

        # Если пользователь уже играл, создаем объект статистики
        if total_questions_answered > 0 or total_correct_answers > 0:
            user_overall_stats = UserOverallStats(total_correct_answers, total_questions_answered)
        else:
            # Если статистики нет, явно создаем объект с нулями, чтобы не было ошибок в шаблоне
            user_overall_stats = UserOverallStats(0, 0)

    # Передаем user_overall_stats в шаблон вместо user_stats_dict
    return render_template("packs.html", packs=all_packs, user_stats=user_overall_stats)


@app.route("/profile")
def profile():
    if not g.user:
        flash("Пожалуйста, войдите, чтобы просматривать свой профиль.", "warning")
        return redirect(url_for('login'))

    total_questions = 0
    correct_answers = 0
    pack_stats = {}

    # Получаем все записи статистики для текущего пользователя одним запросом
    # Eager loading 'quiz_pack' поможет избежать N+1 проблемы, если QuizPack связана с UserQuizStat
    # Если у вас нет eager loading, просто .all() будет работать
    user_quiz_stats = UserQuizStat.query.filter_by(user_id=g.user.id).all()

    for stat in user_quiz_stats:
        # Проверяем, что пак существует, прежде чем пытаться получить его вопросы
        pack = QuizPack.query.get(stat.quiz_pack_id)
        if pack:
            total_questions += stat.total_questions
            correct_answers += stat.total_correct

            pack_stats[pack.id] = {
                'pack_title': pack.title,
                'attempts': stat.games_played,
                'best_score': stat.best_score,
                'last_score': stat.last_score,
                'total_questions': len(pack.questions) # Используем len() напрямую
            }

    return render_template("profile.html",
                           total_questions=total_questions,
                           correct_answers=correct_answers,
                           pack_stats=pack_stats)


@app.route("/quiz/<int:pack_id>")
def quiz(pack_id):
    if not g.user: # Используем g.user
        flash("Пожалуйста, войдите, чтобы начать квиз.", "warning")
        return redirect(url_for('login'))

    quiz_pack = QuizPack.query.get_or_404(pack_id)
    # Убедитесь, что quiz_pack.questions возвращает список или QuerySet, который можно преобразовать в список
    # Если questions - это отношение SQLAlchemy, используйте .all()
    raw_questions = quiz_pack.questions

    if not raw_questions:
        flash(f"В квизе '{quiz_pack.title}' пока нет вопросов.", "info")
        return redirect(url_for('packs'))

    questions_for_js = []
    for q in raw_questions:
        questions_for_js.append({
            'id': q.id,
            'question': q.question_text,
            'options': q.get_options(), # Убедитесь, что get_options() возвращает список строк
            'correct': q.correct_answer_index # Убедитесь, что это 0-based индекс правильного ответа
        })
    random.shuffle(questions_for_js)

    # Храним полные данные вопросов в сессии для валидации при отправке результатов
    # Это важно для submit_quiz, который будет проверять ответы на сервере
    session['current_quiz_questions_data'] = questions_for_js
    session['current_quiz_pack_id'] = pack_id

    # Подготавливаем данные для JavaScript. Теперь они включают pack_id и все вопросы.
    js_data_for_template = {
        'pack_id': pack_id,
        'questions': questions_for_js
    }

    # Для начального отображения в шаблоне (JavaScript обновит это динамически)
    total_questions = len(questions_for_js)
    current_question_index = 0 # Всегда начинаем с 0 для клиентского квиза

    return render_template("quiz.html",
                           pack=quiz_pack,
                           questions_data_json=json.dumps(js_data_for_template), # Передаем все данные в виде JSON-строки
                           current_question_index=current_question_index, # Для начального отображения
                           total_questions=total_questions) # Для начального отображения


@app.route("/submit_quiz", methods=['POST'])
def submit_quiz():
    if not g.user:
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    data = request.get_json()
    pack_id = data.get('pack_id')
    user_answers_indices = data.get('answers', []) # Это список ответов пользователя

    if not pack_id or not isinstance(user_answers_indices, list):
        return jsonify({"status": "error", "message": "Invalid data"}), 400

    if not g.user:
        return jsonify({"status": "error", "message": "User session expired or not found"}), 404

    quiz_pack = QuizPack.query.get(pack_id)
    if not quiz_pack:
        return jsonify({"status": "error", "message": "Quiz pack not found"}), 404

    # Получаем данные вопросов из сессии для валидации
    quiz_questions_data_from_session = session.pop('current_quiz_questions_data', None)
    session.pop('current_quiz_pack_id', None)

    if not quiz_questions_data_from_session or len(user_answers_indices) != len(quiz_questions_data_from_session):
        # Если данные сессии отсутствуют или количество ответов не совпадает, это ошибка
        return jsonify({"status": "error", "message": "Quiz session data missing or mismatched answers. Please restart the quiz."}), 400

    score = 0
    # Проверяем каждый ответ пользователя
    for i, user_chosen_index in enumerate(user_answers_indices):
        # Убедитесь, что 'correct' - это 0-based индекс правильного ответа
        if user_chosen_index == quiz_questions_data_from_session[i]['correct']:
            score += 1

    total_questions_answered = len(quiz_questions_data_from_session) # Количество вопросов в квизе

    user_quiz_stat = UserQuizStat.query.filter_by(user_id=g.user.id, quiz_pack_id=pack_id).first()
    if not user_quiz_stat:
        user_quiz_stat = UserQuizStat(
            user_id=g.user.id,
            quiz_pack_id=pack_id,
            # Инициализируем числовые поля нулем при первом создании
            games_played=0,
            total_correct=0,
            total_questions=0,
            last_score=0,
            best_score=0
        )
        db.session.add(user_quiz_stat)

    # Теперь эти операции будут безопасны, так как поля точно являются числами
    user_quiz_stat.games_played += 1
    user_quiz_stat.total_correct += score
    user_quiz_stat.total_questions += total_questions_answered
    user_quiz_stat.last_score = score
    user_quiz_stat.best_score = max(user_quiz_stat.best_score, score)

    try:
        db.session.commit()
        # Возвращаем успешный статус и данные для отображения или редиректа
        return jsonify({"status": "success", "message": "Quiz results submitted", "score": score,
                        "total": total_questions_answered})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Failed to save quiz results: {e}"}), 500



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

        if not title:
            flash("Название квиз-пака не может быть пустым.", "error")
        elif QuizPack.query.filter_by(title=title).first() and QuizPack.query.filter_by(
                title=title).first().id != quiz_pack.id:
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
        Question.query.filter_by(quiz_pack_id=quiz_id).delete()
        UserQuizStat.query.filter_by(quiz_pack_id=quiz_id).delete()
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