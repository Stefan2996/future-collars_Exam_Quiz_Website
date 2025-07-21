import os
import json
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, flash
from flask_login import LoginManager, current_user
from models import db, User, QuizPack, Question # Импортируем db и модели из models

# Импортируем блюпринты
from routes.auth import auth_bp
from routes.packs import packs_bp
from routes.quiz import quiz_bp
from routes.admin import admin_bp

# Импортируем конфигурацию
from config import Config

# Инициализация Flask приложения
app = Flask(__name__)
app.config.from_object(Config) # Загружаем конфигурацию из класса Config

# Инициализация расширений
db.init_app(app) # Привязываем db к приложению
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login' # Указываем Flask-Login, куда перенаправлять для входа

# --- Загрузка пользователя для Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Jinja2 фильтры ---
app.jinja_env.filters['chr'] = chr
app.jinja_env.filters['tojsonfilter'] = json.dumps # Используем стандартный json.dumps напрямую

# --- Регистрация Blueprints ---
app.register_blueprint(auth_bp)
app.register_blueprint(packs_bp)
app.register_blueprint(quiz_bp)
app.register_blueprint(admin_bp) # Регистрируем админ-блюпринт

# --- Основной маршрут ---
@app.route("/")
def index():
    return render_template("index.html")

# --- Обработчик 404 ошибки ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# --- Функция для добавления начальных данных ---
# Перенесли сюда, чтобы иметь доступ к db и моделям после их инициализации с app
def _create_initial_data():
    with app.app_context(): # Убедимся, что работаем в контексте приложения
        if not QuizPack.query.first():
            print("Adding initial quiz data...")
            pack1 = QuizPack(title="Основы Python", description="Базовые вопросы по синтаксису и концепциям Python.", color='blue', difficulty='Легкий')
            pack2 = QuizPack(title="Flask & Web Dev", description="Вопросы по фреймворку Flask и основам веб-разработки.", color='green', difficulty='Средний')
            pack3 = QuizPack(title="Базы данных SQL", description="Вопросы по основам SQL и базам данных.", color='purple', difficulty='Средний')
            pack4 = QuizPack(title="JavaScript Основы", description="Базовые концепции и синтаксис JavaScript.", color='yellow', difficulty='Легкий')
            pack5 = QuizPack(title="HTML & CSS", description="Вопросы по структуре HTML и стилизации CSS.", color='red', difficulty='Легкий')
            pack6 = QuizPack(title="Алгоритмы", description="Основы алгоритмов и структур данных.", color='orange', difficulty='Сложный')

            db.session.add_all([pack1, pack2, pack3, pack4, pack5, pack6])
            db.session.commit()

            q1_1_options = ["var x = 10;", "x = 10;", "int x = 10;", "set x = 10;"]
            q1_1 = Question(quiz_pack_id=pack1.id, question_text="Как правильно объявить переменную в Python?", options_json=json.dumps(q1_1_options), correct_answer_index=1)
            q1_2_options = ["def func():", "function func():", "func() do:", "define func:"]
            q1_2 = Question(quiz_pack_id=pack1.id, question_text="Как объявить функцию в Python?", options_json=json.dumps(q1_2_options), correct_answer_index=0)
            q1_3_options = ["Python IDE", "pip", "conda", "virtualenv"]
            q1_3 = Question(quiz_pack_id=pack1.id, question_text="Какой командой устанавливаются пакеты в Python?", options_json=json.dumps(q1_3_options), correct_answer_index=1)

            q2_1_options = ["@app.route('/index')", "@app.get('/index')", "@route('/index')", "app.add_url_rule('/index')"]
            q2_1 = Question(quiz_pack_id=pack2.id, question_text="Какой декоратор используется для определения маршрутов в Flask?", options_json=json.dumps(q2_1_options), correct_answer_index=0)
            q2_2_options = ["SQLObject", "Django ORM", "SQLAlchemy", "Peewee"]
            q2_2 = Question(quiz_pack_id=pack2.id, question_text="Какая библиотека часто используется как ORM с Flask?", options_json=json.dumps(q2_2_options), correct_answer_index=2)

            q3_1_options = ["SELECT", "INSERT", "UPDATE", "DELETE"]
            q3_1 = Question(quiz_pack_id=pack3.id, question_text="Какое ключевое слово используется для извлечения данных из базы данных?", options_json=json.dumps(q3_1_options), correct_answer_index=0)
            q3_2_options = ["WHERE", "FROM", "JOIN", "GROUP BY"]
            q3_2 = Question(quiz_pack_id=pack3.id, question_text="Какое ключевое слово используется для фильтрации результатов в SQL?", options_json=json.dumps(q3_2_options), correct_answer_index=0)
            q3_3_options = ["PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "NOT NULL"]
            q3_3 = Question(quiz_pack_id=pack3.id, question_text="Какой тип ключа используется для связи между таблицами?", options_json=json.dumps(q3_3_options), correct_answer_index=1)
            q3_4_options = ["ALTER TABLE", "CREATE TABLE", "DROP TABLE", "TRUNCATE TABLE"]
            q3_4 = Question(quiz_pack_id=pack3.id, question_text="Какая команда используется для создания новой таблицы в SQL?", options_json=json.dumps(q3_4_options), correct_answer_index=1)
            q3_5_options = ["VIEW", "INDEX", "TRIGGER", "STORED PROCEDURE"]
            q3_5 = Question(quiz_pack_id=pack3.id, question_text="Что такое оптимизированный набор строк и столбцов из одной или нескольких таблиц?", options_json=json.dumps(q3_5_options), correct_answer_index=0)

            q4_1_options = ["const x = 10;", "let x = 10;", "var x = 10;", "all of the above"]
            q4_1 = Question(quiz_pack_id=pack4.id, question_text="Какое ключевое слово используется для объявления переменной в JavaScript, которая может быть переназначена?", options_json=json.dumps(q4_1_options), correct_answer_index=1)
            q4_2_options = ["function myFunction()", "def myFunction()", "func myFunction()", "myFunction = function()"]
            q4_2 = Question(quiz_pack_id=pack4.id, question_text="Как объявить функцию в JavaScript?", options_json=json.dumps(q4_2_options), correct_answer_index=0)
            q4_3_options = ["console.log()", "print()", "log()", "display()"]
            q4_3 = Question(quiz_pack_id=pack4.id, question_text="Какой метод используется для вывода сообщений в консоль в JavaScript?", options_json=json.dumps(q4_3_options), correct_answer_index=0)

            q5_1_options = ["<head>", "<body>", "<!DOCTYPE html>", "<html>"]
            q5_1 = Question(quiz_pack_id=pack5.id, question_text="С какого тега начинается любой HTML-документ?", options_json=json.dumps(q5_1_options), correct_answer_index=2)
            q5_2_options = ["<p>", "<div>", "<span>", "<a>"]
            q5_2 = Question(quiz_pack_id=pack5.id, question_text="Какой тег используется для создания абзаца текста?", options_json=json.dumps(q5_2_options), correct_answer_index=0)
            q5_3_options = ["background-color", "color", "font-size", "text-align"]
            q5_3 = Question(quiz_pack_id=pack5.id, question_text="Какое свойство CSS используется для изменения цвета текста?", options_json=json.dumps(q5_3_options), correct_answer_index=1)

            q6_1_options = ["Пузырьковая сортировка", "Быстрая сортировка", "Сортировка выбором", "Сортировка слиянием"]
            q6_1 = Question(quiz_pack_id=pack6.id, question_text="Какой алгоритм сортировки имеет среднюю сложность O(n log n)?", options_json=json.dumps(q6_1_options), correct_answer_index=1)
            q6_2_options = ["FIFO", "LIFO", "FILO", "LILO"]
            q6_2 = Question(quiz_pack_id=pack6.id, question_text="По какому принципу работает очередь (Queue)?", options_json=json.dumps(q6_2_options), correct_answer_index=0)
            q6_3_options = ["Дерево", "Граф", "Связный список", "Хеш-таблица"]
            q6_3 = Question(quiz_pack_id=pack6.id, question_text="Какая структура данных использует пары ключ-значение для быстрого поиска?", options_json=json.dumps(q6_3_options), correct_answer_index=3)

            db.session.add_all([q1_1, q1_2, q1_3, q2_1, q2_2, q3_1, q3_2, q3_3, q3_4, q3_5, q4_1, q4_2, q4_3, q5_1, q5_2, q5_3, q6_1, q6_2, q6_3])
            db.session.commit()
            print("Initial quiz data added.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all() # Создаст таблицы, если их нет
        _create_initial_data() # Добавит начальные данные, если их нет
    app.run(debug=True)