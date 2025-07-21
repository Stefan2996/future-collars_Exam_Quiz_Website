from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User # Импортируем db и User из models
from sqlalchemy import func
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: # Используем current_user из Flask-Login
        return redirect(url_for('index')) # Используем blueprint.name.endpoint

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
                return redirect(url_for('auth.login')) # Используем blueprint.name.endpoint
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при регистрации: {e}", "error")

    return render_template("register.html")

@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me') # Добавим поле "запомнить меня"

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember_me) # Используем Flask-Login
            flash(f"Добро пожаловать, {user.name}!", "success")
            # Перенаправляем на следующую страницу, если она была указана (например, после @login_required)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash("Неверная почта или пароль.", "error")

    return render_template("login.html")

@auth_bp.route("/logout")
@login_required # Защищаем маршрут
def logout():
    logout_user() # Используем Flask-Login
    flash("Вы успешно вышли из аккаунта.", "info")
    return redirect(url_for('index'))

@auth_bp.route("/profile")
@login_required # Защищаем маршрут
def profile():
    # current_user уже доступен из Flask-Login
    user_id = current_user.id

    from models import UserQuizStat, QuizPack # Импортируем здесь, чтобы избежать циклической зависимости

    # Общая статистика пользователя
    overall_stats = db.session.query(
        func.sum(UserQuizStat.total_questions),
        func.sum(UserQuizStat.score)
    ).filter_by(user_id=user_id).first()

    total_questions_answered = overall_stats[0] or 0
    total_correct_answers = overall_stats[1] or 0

    overall_accuracy = 0.0
    if total_questions_answered > 0:
        overall_accuracy = (total_correct_answers / total_questions_answered) * 100

    pack_stats = {}
    all_user_quiz_stats = UserQuizStat.query.filter_by(user_id=user_id).order_by(UserQuizStat.completed_at.asc()).all()

    grouped_stats = {}
    for stat_entry in all_user_quiz_stats:
        if stat_entry.quiz_pack_id not in grouped_stats:
            grouped_stats[stat_entry.quiz_pack_id] = {
                'attempts': 0,
                'best_score': 0,
                'last_score': 0,
                'latest_completed_at': datetime.min,
                'pack_title': ''
            }

        grouped_stats[stat_entry.quiz_pack_id]['attempts'] += 1
        grouped_stats[stat_entry.quiz_pack_id]['best_score'] = max(
            grouped_stats[stat_entry.quiz_pack_id]['best_score'], stat_entry.score
        )

        if stat_entry.completed_at > grouped_stats[stat_entry.quiz_pack_id]['latest_completed_at']:
            grouped_stats[stat_entry.quiz_pack_id]['last_score'] = stat_entry.score
            grouped_stats[stat_entry.quiz_pack_id]['latest_completed_at'] = stat_entry.completed_at

    for pack_id, stats in grouped_stats.items():
        pack = QuizPack.query.get(pack_id)
        if pack:
            pack_stats[pack.id] = {
                'pack_title': pack.title,
                'attempts': stats['attempts'],
                'best_score': stats['best_score'],
                'last_score': stats['last_score'],
                'total_questions_in_pack': len(pack.questions)
            }

    total_quizzes_completed = UserQuizStat.query.filter_by(user_id=user_id).count()

    has_flawless_quiz = db.session.query(UserQuizStat).filter(
        UserQuizStat.user_id == user_id,
        UserQuizStat.score == UserQuizStat.total_questions,
        UserQuizStat.total_questions >= 5
    ).first() is not None

    has_sharpshooter_speed_quiz = db.session.query(UserQuizStat).filter(
        UserQuizStat.user_id == user_id,
        UserQuizStat.total_questions >= 5,
        UserQuizStat.avg_time_per_question <= 3.0,
        (UserQuizStat.score * 100.0 / UserQuizStat.total_questions) >= 80.0
    ).first() is not None

    return render_template("profile.html",
                           total_questions=total_questions_answered,
                           correct_answers=total_correct_answers,
                           overall_accuracy=overall_accuracy,
                           pack_stats=pack_stats,
                           total_quizzes_completed=total_quizzes_completed,
                           has_flawless_quiz=has_flawless_quiz,
                           has_sharpshooter_speed_quiz=has_sharpshooter_speed_quiz)