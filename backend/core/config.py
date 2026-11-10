"""Process configuration.

This is the only module that reads the environment. Everything else receives a
`Config` — Django settings import it, and modules get it through the kernel's
service registry. Invalid configuration fails loudly at boot with every problem
listed at once, rather than surfacing later as a confusing runtime error.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

_INSECURE_DEV_SECRET = "dev-insecure-secret-key-change-me"  # noqa: S105 - dev-only placeholder
_OPEN_METEO_FREE_URL = "https://api.open-meteo.com"
_OPEN_METEO_CUSTOMER_URL = "https://customer-api.open-meteo.com"


class ConfigError(RuntimeError):
    """Raised at boot when the environment is invalid or half-configured."""


class AdapterMode(StrEnum):
    """How an outside service is reached.

    - off: the feature is disabled; calls fail with SERVICE_DISABLED.
    - simulated: deterministic in-process fake — no network, used by tests and offline dev.
    - live: the real third-party API.
    """

    OFF = "off"
    SIMULATED = "simulated"
    LIVE = "live"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class Config:
    env: Environment
    debug: bool
    secret_key: str
    allowed_hosts: tuple[str, ...]
    csrf_trusted_origins: tuple[str, ...]
    log_level: str
    http_timeout_s: float
    num_proxies: int
    frontend_dist_dir: Path

    routing_mode: AdapterMode
    osrm_url: str

    geocoding_mode: AdapterMode
    photon_url: str

    weather_mode: AdapterMode
    open_meteo_url: str
    open_meteo_api_key: str | None
    weather_cache_ttl_s: int

    @property
    def is_production(self) -> bool:
        return self.env is Environment.PRODUCTION


class _Reader:
    """Collects every problem instead of stopping at the first one."""

    def __init__(self, environ: Mapping[str, str]) -> None:
        self._environ = environ
        self.errors: list[str] = []

    def text(self, key: str, default: str) -> str:
        value = self._environ.get(key, "").strip()
        return value or default

    def optional(self, key: str) -> str | None:
        value = self._environ.get(key, "").strip()
        return value or None

    def flag(self, key: str, default: bool) -> bool:
        raw = self._environ.get(key, "").strip().lower()
        if not raw:
            return default
        if raw in {"1", "true", "yes", "on"}:
            return True
        if raw in {"0", "false", "no", "off"}:
            return False
        self.errors.append(f"{key} must be a boolean (true/false), got {raw!r}")
        return default

    def number(self, key: str, default: float, *, minimum: float, maximum: float) -> float:
        raw = self._environ.get(key, "").strip()
        if not raw:
            return default
        try:
            value = float(raw)
        except ValueError:
            self.errors.append(f"{key} must be a number, got {raw!r}")
            return default
        if not minimum <= value <= maximum:
            self.errors.append(f"{key} must be between {minimum} and {maximum}, got {value}")
            return default
        return value

    def csv(self, key: str, default: tuple[str, ...]) -> tuple[str, ...]:
        raw = self._environ.get(key, "").strip()
        if not raw:
            return default
        return tuple(item.strip() for item in raw.split(",") if item.strip())

    def choice[E: StrEnum](self, key: str, enum: type[E], default: E) -> E:
        raw = self._environ.get(key, "").strip().lower()
        if not raw:
            return default
        try:
            return enum(raw)
        except ValueError:
            allowed = ", ".join(member.value for member in enum)
            self.errors.append(f"{key} must be one of: {allowed}; got {raw!r}")
            return default

    def url(self, key: str, default: str) -> str:
        value = self.text(key, default).rstrip("/")
        if not value.startswith(("http://", "https://")):
            self.errors.append(f"{key} must be an http(s) URL, got {value!r}")
        return value


def load_config(environ: Mapping[str, str]) -> Config:
    """Build a validated `Config` from an environment mapping."""
    read = _Reader(environ)

    env = read.choice("DJANGO_ENV", Environment, Environment.DEVELOPMENT)
    is_prod = env is Environment.PRODUCTION
    # Tests never touch the network unless a test opts into a live adapter explicitly.
    default_mode = AdapterMode.SIMULATED if env is Environment.TEST else AdapterMode.LIVE

    secret_key = read.text("SECRET_KEY", _INSECURE_DEV_SECRET)
    allowed_hosts = read.csv(
        "ALLOWED_HOSTS", () if is_prod else ("localhost", "127.0.0.1", "[::1]", "testserver")
    )
    # Render sets this to the service's onrender.com hostname, which is only known once the
    # service exists, and sends health checks with it as the Host header.
    render_host = read.optional("RENDER_EXTERNAL_HOSTNAME")
    if render_host and render_host not in allowed_hosts:
        allowed_hosts = (*allowed_hosts, render_host)

    open_meteo_url = read.url("OPEN_METEO_URL", _OPEN_METEO_FREE_URL)
    open_meteo_api_key = read.optional("OPEN_METEO_API_KEY")

    config = Config(
        env=env,
        debug=read.flag("DEBUG", not is_prod),
        secret_key=secret_key,
        allowed_hosts=allowed_hosts,
        csrf_trusted_origins=read.csv("CSRF_TRUSTED_ORIGINS", ()),
        log_level=read.text("LOG_LEVEL", "INFO").upper(),
        http_timeout_s=read.number("HTTP_TIMEOUT_S", 15.0, minimum=1, maximum=120),
        # How many reverse proxies sit in front of the app; rate limits key on the client
        # IP that many hops back in X-Forwarded-For. 0 = trust only REMOTE_ADDR.
        num_proxies=int(read.number("NUM_PROXIES", 0, minimum=0, maximum=5)),
        frontend_dist_dir=Path(read.text("FRONTEND_DIST_DIR", str(REPO_DIR / "frontend" / "dist"))),
        routing_mode=read.choice("ROUTING_MODE", AdapterMode, default_mode),
        osrm_url=read.url("OSRM_URL", "https://router.project-osrm.org"),
        geocoding_mode=read.choice("GEOCODING_MODE", AdapterMode, default_mode),
        photon_url=read.url("PHOTON_URL", "https://photon.komoot.io"),
        weather_mode=read.choice("WEATHER_MODE", AdapterMode, default_mode),
        open_meteo_url=open_meteo_url,
        open_meteo_api_key=open_meteo_api_key,
        weather_cache_ttl_s=int(read.number("WEATHER_CACHE_TTL_S", 900, minimum=0, maximum=6 * 3600)),
    )

    errors = read.errors
    if config.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        errors.append(f"LOG_LEVEL must be a standard logging level, got {config.log_level!r}")
    if is_prod:
        if secret_key == _INSECURE_DEV_SECRET or len(secret_key) < 32:
            errors.append("SECRET_KEY must be set to a random value of 32+ characters in production")
        if not allowed_hosts:
            errors.append("ALLOWED_HOSTS must list the public hostname(s) in production")
        if config.debug:
            errors.append("DEBUG must be false in production")
    # Half-configured adapters: a key without the endpoint that accepts it (or the reverse)
    # would silently fall back to the free tier or fail on the first request. Refuse to boot.
    if config.weather_mode is AdapterMode.LIVE:
        uses_customer_url = open_meteo_url == _OPEN_METEO_CUSTOMER_URL
        if open_meteo_api_key and not uses_customer_url:
            errors.append(
                f"OPEN_METEO_API_KEY is set but OPEN_METEO_URL is {open_meteo_url!r}; "
                f"commercial keys only work against {_OPEN_METEO_CUSTOMER_URL}"
            )
        if uses_customer_url and not open_meteo_api_key:
            errors.append("OPEN_METEO_URL points at the customer API but OPEN_METEO_API_KEY is unset")

    if errors:
        raise ConfigError("Invalid configuration:\n  - " + "\n  - ".join(errors))
    return config


def _read_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env reader (KEY=VALUE, # comments, optional quotes). Dev convenience only."""
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


_config: Config | None = None


def get_config() -> Config:
    """The process-wide config: `.env` (if present) overlaid by the real environment."""
    global _config
    if _config is None:
        _config = load_config({**_read_dotenv(BACKEND_DIR / ".env"), **os.environ})
    return _config


def use_test_config(**overrides: str) -> Config:
    """Install a hermetic test config that ignores the developer's .env and shell.

    Called by `server.settings_test` before Django reads settings, so every adapter
    defaults to `simulated` and nothing reaches the network.
    """
    global _config
    _config = load_config({"DJANGO_ENV": "test", **overrides})
    return _config
