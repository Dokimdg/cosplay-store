"""
Налаштування Cosplay Store.

Секрети й режим роботи беруться зі змінних середовища (або з файлу .env у корені проєкту,
див. .env.example). Без жодних змінних проєкт запускається в режимі розробки (DEBUG=True).
У продакшені ОБОВ'ЯЗКОВО: DJANGO_DEBUG=0, DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS.
"""
import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """Мінімальний читач .env (без сторонніх залежностей). Реальні змінні середовища мають пріоритет."""
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name):
    return [item.strip() for item in os.environ.get(name, '').split(',') if item.strip()]


_load_dotenv(BASE_DIR / '.env')

TESTING = 'test' in sys.argv

# ---------------------------------------------------------------------------
# Ключові налаштування: SECRET_KEY, DEBUG, ALLOWED_HOSTS
# ---------------------------------------------------------------------------
DEBUG = env_bool('DJANGO_DEBUG', True)

_DEV_SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-production'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')

if DEBUG:
    SECRET_KEY = SECRET_KEY or _DEV_SECRET_KEY
    ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS') or ['localhost', '127.0.0.1', 'cosplay-store.onrender.com']
else:
    if len(SECRET_KEY) < 50 or SECRET_KEY.startswith('django-insecure'):
        raise ImproperlyConfigured(
            'У продакшені (DJANGO_DEBUG=0) потрібен надійний DJANGO_SECRET_KEY (50+ символів). '
            'Згенеруйте: python -c "from django.core.management.utils import '
            'get_random_secret_key as g; print(g())"'
        )
    ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS') or ['localhost', '127.0.0.1', 'cosplay-store.onrender.com']


# Адреса адмінки: змініть, щоб її не знаходили автоматичні сканери (наприклад, ADMIN_URL=keeper-9f3a/)
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'shop',
    'cart.apps.CartConfig',
    'accounts.apps.AccountsConfig',
    'orders.apps.OrdersConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'cosplay_store.security.RateLimitMiddleware',          # ліміт запитів на IP
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',            # захист від CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cosplay_store.security.ContentSecurityPolicyMiddleware',  # захист від XSS (CSP)
]

ROOT_URLCONF = 'cosplay_store.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            # autoescape увімкнено за замовчуванням — не вимикайте його і не використовуйте |safe для користувацьких даних
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cart.context_processors.cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'cosplay_store.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Кеш потрібен для rate limiting. LocMem — окремий для кожного процесу;
# для кількох воркерів задайте REDIS_URL (потрібен пакет redis).
if os.environ.get('REDIS_URL'):
    CACHES = {'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ['REDIS_URL'],
    }}
else:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'   # сюди збирає `manage.py collectstatic` для продакшену

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CART_SESSION_ID = 'cart'

AUTH_USER_MODEL = 'accounts.CustomUser'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'shop:product_list'
LOGOUT_REDIRECT_URL = 'shop:product_list'

# ---------------------------------------------------------------------------
# Захист HTTP-рівня (діє завжди)
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = 'DENY'                       # забороняє вбудовування сайту у <iframe> (clickjacking)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SESSION_COOKIE_HTTPONLY = True                 # JS не читає сесійну cookie (наслідки XSS менші)
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')   # напр. https://example.com
CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'

# Обмеження розміру запитів (захист від великих тіл/завантажень)
DATA_UPLOAD_MAX_MEMORY_SIZE = 1 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200

# ---------------------------------------------------------------------------
# Додатково для продакшену (DEBUG=False): HTTPS, HSTS, secure cookies
# ---------------------------------------------------------------------------
if not DEBUG:
    # Якщо Django стоїть за nginx/балансувальником, що завершує HTTPS:
    # DJANGO_BEHIND_PROXY=1 (і nginx має передавати X-Forwarded-Proto)
    if env_bool('DJANGO_BEHIND_PROXY'):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', 60 * 60 * 24 * 30))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_HSTS_SUBDOMAINS', False)
    SECURE_HSTS_PRELOAD = False

# ---------------------------------------------------------------------------
# Rate limiting (див. cosplay_store/security.py)
# ---------------------------------------------------------------------------
RATE_LIMIT_ENABLED = env_bool('RATE_LIMIT_ENABLED', True) and not TESTING
RATE_LIMIT_GLOBAL = (120, 60)      # (запитів, секунд) на один IP для всього сайту
NUM_PROXIES = int(os.environ.get('NUM_PROXIES', 0))   # скільки довірених проксі перед Django (для X-Forwarded-For)

# ---------------------------------------------------------------------------
# Логи безпеки
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'simple': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'}},
    'loggers': {
        'django.security': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'cosplay_store.security': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}

# Реквізити компанії для PDF-рахунків (ПРИКЛАД — замініть на свої)
COMPANY_DETAILS = {
    'name': 'ФОП Косплеєр Іван Іванович (Cosplay Store)',
    'edrpou': '0000000000',
    'iban': 'UA00 0000 0000 0000 0000 0000 00000',
    'bank': 'АТ «Приклад Банк»',
    'address': 'м. Київ, вул. Прикладна, 1',
    'phone': '+380 50 000 00 00',
    'email': 'shop@example.com',
}

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'