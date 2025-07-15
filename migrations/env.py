import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Это очень важно: добавьте корневую директорию вашего проекта в sys.path,
# чтобы Python мог найти ваш app.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импортируем ваше Flask-приложение и объект базы данных
# Убедитесь, что 'app' и 'db' правильно импортированы из вашего app.py
from app import app, db 

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's Metadata object here
# for 'autogenerate' support
# from myapp import Base
# target_metadata = Base.metadata  # <-- Закомментируйте или удалите эту строку

# Используйте metadata из вашего объекта Flask-SQLAlchemy db
target_metadata = db.metadata # <-- Эта строка очень важна!


# other values from the config, defined by the needs of env.py,
# can be acquired and passed to the sqlalchemy context.
# ... (остальной код env.py) ...

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an actual Engine, though an Engine is additionally
    useful here.

    By skipping the Engine creation we don't even need a DBAPI to be
    available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Этот блок кода очень важен для работы с Flask-приложением
    with app.app_context(): # <-- Убедитесь, что этот блок присутствует
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata
            )

            with context.begin_transaction():
                context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()