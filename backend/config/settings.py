"""
Django settings for the household financial planning backend.

Every value falls back to a working local default so that the stack boots
without a hand written .env. See `.env.example` in the repository root.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def env(key: str, default: str = "") -> str:
    value = os.environ.get(key)
    return default if value is None or value == "" else value


def env_bool(key: str, default: bool = False) -> bool:
    return env(key, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    try:
        return int(env(key, str(default)))
    except ValueError:
        return default


def env_list(key: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(key, default).split(",") if item.strip()]


# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-secret-change-me")
SECURITY_SALT = env("SECURITY_SALT", "insecure-dev-salt-change-me")
DEBUG = env_bool("DEBUG", True)

DOMAIN = env("DOMAIN", "localhost")
SCHEME = env("SCHEME", "http")
PUBLIC_PORT = env("PORT", "8080")
PUBLIC_URL = f"{SCHEME}://{DOMAIN}" + ("" if PUBLIC_PORT in {"80", "443"} else f":{PUBLIC_PORT}")

ALLOWED_HOSTS = list(
    {
        DOMAIN,
        "localhost",
        "127.0.0.1",
        "backend",
        "0.0.0.0",
        *env_list("EXTRA_ALLOWED_HOSTS"),
    }
)
if DEBUG:
    ALLOWED_HOSTS.append("*")

CSRF_TRUSTED_ORIGINS = [
    PUBLIC_URL,
    f"{SCHEME}://{DOMAIN}",
    "http://localhost:3000",
    "http://localhost:8080",
]

# Token auth means the SPA never relies on cookies; CORS stays permissive for
# local development and is restricted to the configured domain in production.
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = list({PUBLIC_URL, "http://localhost:3000", "http://localhost:8080"})
CORS_ALLOW_CREDENTIALS = False

# -----------------------------------------------------------------------------
# Applications
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "corsheaders",
    "channels",
    "django_celery_beat",
    "drf_spectacular",
    # local
    "base",
    "users",
    "finance",
    "imports",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "finplan"),
        "USER": env("POSTGRES_USER", "finplan"),
        "PASSWORD": env("POSTGRES_PASSWORD", "finplan_dev_password"),
        "HOST": env("POSTGRES_HOST", "postgres"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# Internationalisation
# -----------------------------------------------------------------------------
LANGUAGE_CODE = env("LANGUAGE_CODE", "de-de")
TIME_ZONE = env("TIME_ZONE", "Europe/Berlin")
USE_I18N = True
USE_TZ = True

DEFAULT_CURRENCY = env("DEFAULT_CURRENCY", "EUR")

# -----------------------------------------------------------------------------
# Static & media (MinIO / S3)
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("MINIO_BUCKET", "finplan-files"),
            "access_key": env("MINIO_ROOT_USER", "finplan"),
            "secret_key": env("MINIO_ROOT_PASSWORD", "finplan_dev_password"),
            "endpoint_url": env("MINIO_ENDPOINT", "http://minio:9000"),
            "region_name": "us-east-1",
            "addressing_style": "path",
            "file_overwrite": False,
            "querystring_auth": True,
            "querystring_expire": 3600,
            "default_acl": None,
        },
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# Endpoint the browser can reach – used when we rewrite presigned URLs.
# Empty means "through our own nginx", which keeps the stack on a single port.
MINIO_ENDPOINT = env("MINIO_ENDPOINT", "http://minio:9000")
MINIO_PUBLIC_ENDPOINT = env("MINIO_PUBLIC_ENDPOINT") or f"{PUBLIC_URL}/s3"
MINIO_BUCKET = env("MINIO_BUCKET", "finplan-files")

# -----------------------------------------------------------------------------
# REST framework
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "base.authentication.ExpiringTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "base.pagination.DefaultPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DATETIME_FORMAT": "iso-8601",
    "DATE_FORMAT": "iso-8601",
    "EXCEPTION_HANDLER": "base.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Haushalts-Finanzplanung API",
    "DESCRIPTION": "REST API für die Finanzplanung eines Haushalts.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# Auth tokens expire after this many days (0 disables expiry).
AUTH_TOKEN_TTL_DAYS = env_int("AUTH_TOKEN_TTL_DAYS", 30)
AUTH_TOKEN_TTL = timedelta(days=AUTH_TOKEN_TTL_DAYS) if AUTH_TOKEN_TTL_DAYS > 0 else None
PASSWORD_LINK_TTL = timedelta(hours=env_int("PASSWORD_LINK_TTL_HOURS", 24))

# SMTP values are defaults. The corresponding database settings, editable in
# the UI, take precedence when account emails are sent.
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "finanzplanung@localhost")

# -----------------------------------------------------------------------------
# Channels / Redis
# -----------------------------------------------------------------------------
REDIS_HOST = env("REDIS_HOST", "redis")
REDIS_PORT = env_int("REDIS_PORT", 6379)
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [(REDIS_HOST, REDIS_PORT)]},
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
    }
}

# -----------------------------------------------------------------------------
# Celery
# -----------------------------------------------------------------------------
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/2"
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# -----------------------------------------------------------------------------
# Domain configuration
# -----------------------------------------------------------------------------
# Fallbacks for the key/value Settings model. The database always wins;
# these are only used until the user changes something in the UI.
PREDICTION_HORIZON_MONTHS = env_int("PREDICTION_HORIZON_MONTHS", 24)
OPENAI_API_KEY = env("OPENAI_API_KEY")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_BASE_URL = env("OPENAI_BASE_URL")
OPENAI_BATCH_SIZE = env_int("OPENAI_BATCH_SIZE", 25)

BOOTSTRAP_ADMIN_EMAIL = env("BOOTSTRAP_ADMIN_EMAIL", "admin@localhost")
BOOTSTRAP_ADMIN_PASSWORD = env("BOOTSTRAP_ADMIN_PASSWORD")
BOOTSTRAP_ADMIN_NAME = env("BOOTSTRAP_ADMIN_NAME", "Administrator")

# Maximum upload size for CSV imports (bytes).
MAX_UPLOAD_SIZE = env_int("MAX_UPLOAD_SIZE", 64 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE

# -----------------------------------------------------------------------------
# Security (only tightened when DEBUG is off)
# -----------------------------------------------------------------------------
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    SESSION_COOKIE_HTTPONLY = True
    X_FRAME_OPTIONS = "DENY"
    if SCHEME == "https":
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name} – {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.db.backends": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        "base": {"level": "DEBUG" if DEBUG else "INFO", "handlers": ["console"], "propagate": False},
        "finance": {"level": "DEBUG" if DEBUG else "INFO", "handlers": ["console"], "propagate": False},
        "imports": {"level": "DEBUG" if DEBUG else "INFO", "handlers": ["console"], "propagate": False},
    },
}
