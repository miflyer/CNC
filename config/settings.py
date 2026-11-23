from pathlib import Path #Модуль для работы с путями
import os  # для чтения переменных окружения (настройки деплоя)

# Это корневая директория проекта
# __file__ путь к текущему файлу (settings.py).
# .resolve() превращает путь в абсолютный (убирает относительность и симлинки).
# .parent берёт родительскую папку.
BASE_DIR = Path(__file__).resolve().parent.parent

# Ключ читаем из окружения. В локальной разработке подставится значение по умолчанию,
# на сервере задаём переменную SECRET_KEY (см. README, раздел «Деплой»).
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "k#p$vn3ht8qe2_mcx@rwdkzp7mm2skqf5@xt%*17)6y&n=jo^",  # только для разработки!
)

# DEBUG=0 в окружении сервера, локально переменная не задана -> True
DEBUG = os.environ.get("DEBUG", "1") == "1"

# Домены, которые разрешено обслуживать: "cnc.onrender.com" или несколько через запятую
_raw_hosts = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(",") if h.strip()]

# Секретный токен для URL-запуска обновления цен (бесплатный cron на хостинге)
PRICE_UPDATE_TOKEN = os.environ.get("PRICE_UPDATE_TOKEN", "dev-token-12345")

# список подключённых Django-приложений
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Наши приложения
    "accounts",
    "market",
    "trading",
    "portfolio",
]

# слои обработки запроса/ответа
# порядок важен
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # раздача статики без nginx
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# главный модуль маршрутизации, указывает, где лежит корневой urls.py, который Django читает первым
ROOT_URLCONF = "config.urls"

# стандартный шаблонизатор
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"], # Порядок поиска шаблона: сначала папки из DIRS, потом templates/ каждого приложения.
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# точки входа синхронных и асинхронных серверов (Web Server Gateway Interface)
WSGI_APPLICATION = "config.wsgi.application" #(Web Server Gateway Interface)
ASGI_APPLICATION = "config.asgi.application"

# Пока — SQLite (файл рядом, ничего ставить не надо).
# На этапе деплоя перейдём на PostgreSQL.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True # При True Django умеет переключать язык в зависимости от настроек пользователя.
USE_TZ = True # При True поле datetime будет aware (с таймзоной),

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"  # сюда собирает collectstatic (для продакшена)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "index"
LOGIN_URL = "login"  # куда перенаправляет login_required
