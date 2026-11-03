from pathlib import Path #Модуль для работы с путями

# Это корневая директория проекта
# __file__ путь к текущему файлу (settings.py).
# .resolve() превращает путь в абсолютный (убирает относительность и симлинки).
# .parent берёт родительскую папку.
BASE_DIR = Path(__file__).resolve().parent.parent

# Пока ключ лежит тут, позже перенесём его в .env
SECRET_KEY = "k#p$vn3ht8qe2_mcx@rwdkzp7mm2skqf5@xt%*17)6y&n=jo^"

DEBUG = True #В проде обязательно поменять
ALLOWED_HOSTS = [] #Список доменов, которые разрешено обслуживать

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
        "DIRS": [],
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
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
