"""Rate limiting та Content-Security-Policy.

Rate limiting тут — прикладний захист від перебору паролів, спаму замовленнями та
примітивних флуд-атак з одного IP. Справжній розподілений DDoS потрібно гасити ДО Django:
nginx (limit_req), Cloudflare/WAF, хостинг-провайдер. Див. README.
"""
import logging
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """IP клієнта. X-Forwarded-For довіряємо лише якщо задано NUM_PROXIES (інакше його легко підробити)."""
    proxies = getattr(settings, 'NUM_PROXIES', 0)
    if proxies:
        parts = [p.strip() for p in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') if p.strip()]
        if len(parts) >= proxies:
            return parts[-proxies]
    return request.META.get('REMOTE_ADDR', 'unknown')


def _hit(key, window):
    """Лічильник із фіксованим вікном: повертає, скільки запитів уже зроблено у поточному вікні."""
    if cache.add(key, 1, window):
        return 1
    try:
        return cache.incr(key)
    except ValueError:          # ключ щойно протух
        cache.set(key, 1, window)
        return 1


def too_many_requests(request, retry_after):
    response = HttpResponse(
        render_to_string('429.html', {'retry_after': retry_after}), status=429,
    )
    response['Retry-After'] = str(retry_after)
    return response


def is_limited(request, name, limit, window):
    key = f'rl:{name}:{get_client_ip(request)}'
    if _hit(key, window) > limit:
        logger.warning('Rate limit "%s" exceeded by %s on %s', name, get_client_ip(request), request.path)
        return True
    return False


def rate_limit(name, limit, window, methods=('POST',)):
    """Декоратор для в'юх: не більше `limit` запитів за `window` секунд з одного IP."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if settings.RATE_LIMIT_ENABLED and request.method in methods:
                if is_limited(request, name, limit, window):
                    return too_many_requests(request, window)
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


class RateLimitMiddleware:
    """Загальний ліміт запитів на IP для всього сайту (без статики й медіа)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.RATE_LIMIT_ENABLED and not self._is_asset(request.path):
            limit, window = settings.RATE_LIMIT_GLOBAL
            if is_limited(request, 'global', limit, window):
                return too_many_requests(request, window)
        return self.get_response(request)

    @staticmethod
    def _is_asset(path):
        static = '/' + settings.STATIC_URL.strip('/') + '/'
        return path.startswith(static) or path.startswith(settings.MEDIA_URL)


class ContentSecurityPolicyMiddleware:
    """CSP: браузер виконує лише скрипти з нашого домену, тож ін'єктований <script> не спрацює.

    У DEBUG політика лише звітує (Report-Only), щоб не ламати сторінки помилок Django.
    Адмінку не чіпаємо: у неї власні вимоги до скриптів.
    """

    POLICY = "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' https://cdn.jsdelivr.net",
        "img-src 'self' data:",
        "font-src 'self' https://cdn.jsdelivr.net",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ])

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/' + settings.ADMIN_URL):
            return response
        header = 'Content-Security-Policy-Report-Only' if settings.DEBUG else 'Content-Security-Policy'
        response.headers.setdefault(header, self.POLICY)
        return response
