"""Django settings — a thin projection of `core.config`.

Every value comes from the validated `Config`; nothing here reads the environment directly,
so a bad deployment fails once, at import, with every problem listed.

There is no database: the app keeps no records. Routes and forecasts are cached in memory
and everything else is computed per request.
"""

from __future__ import annotations

from core.config import BACKEND_DIR, get_config
from core.logging import logging_config

config = get_config()

SECRET_KEY = config.secret_key
DEBUG = config.debug
ALLOWED_HOSTS = list(config.allowed_hosts)
CSRF_TRUSTED_ORIGINS = list(config.csrf_trusted_origins)

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # A plan response is ~200 KB of coordinates and hourly scores; gzip makes it ~5x smaller.
    # Responses carry no secrets, so BREACH-style length leaks don't apply.
    "django.middleware.gzip.GZipMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.middleware.RequestIdMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "server.urls"
WSGI_APPLICATION = "server.wsgi.application"

DATABASES: dict[str, dict[str, str]] = {}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "weather-aware-truck-routing",
        # A cross-country corridor is several hundred forecast cells; the default 300 would
        # evict a trip's own weather before the trip finished planning.
        "OPTIONS": {"MAX_ENTRIES": 20_000, "CULL_FREQUENCY": 4},
    }
}

TEMPLATES: list[dict[str, object]] = []

# The built frontend. Hashed assets are served by WhiteNoise from `/assets/`; `index.html`
# is served by `core.views.spa` for every client-side route.
STATIC_URL = "/assets/"
STATICFILES_DIRS = (
    [config.frontend_dist_dir / "assets"] if (config.frontend_dist_dir / "assets").is_dir() else []
)
STATIC_ROOT = BACKEND_DIR / "staticfiles"
WHITENOISE_USE_FINDERS = True
WHITENOISE_IMMUTABLE_FILE_TEST = r"^.+[.-][0-9a-zA-Z_-]{8,}\..+$"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_TZ = True
USE_I18N = False

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = logging_config(config.log_level)

# Ninja's anonymous throttles key on the client IP; behind N proxies the real IP is the
# N-th from the right in X-Forwarded-For.
NINJA_NUM_PROXIES = config.num_proxies

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
if config.is_production:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz$", r"^readyz$"]
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
