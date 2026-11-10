"""Boot and shutdown.

Order is deliberate; each step exists because the next depends on it:

1. config     — already validated when settings imported it (bad env never gets here)
2. services   — shared HTTP client, cache, logger
3. register   — each module in registry load order wires its adapter and service
4. start      — background work (none today; the hook keeps the lifecycle explicit)

Shutdown runs `stop` in reverse order, then closes the HTTP pool.
"""

from __future__ import annotations

import atexit
import threading

from django.core.cache import cache

from core.config import ConfigError, get_config
from core.http import build_http_client
from core.logging import get_logger
from core.module import ModuleContext, ServerModule, Service, ServiceRegistry
from modules import load_registry

_PROVIDED = frozenset(Service)

_lock = threading.Lock()
_booted: tuple[ServerModule, ...] | None = None
_services: ServiceRegistry | None = None

log = get_logger("kernel")


def _validate(registry: tuple[ServerModule, ...]) -> None:
    names = [module.name for module in registry]
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        raise ConfigError(f"Duplicate module names in registry: {sorted(duplicates)}")
    for module in registry:
        missing = module.requires - _PROVIDED
        if missing:
            raise ConfigError(
                f"Module {module.name!r} requires services core does not provide: {sorted(missing)}"
            )


def _context(services: ServiceRegistry, module: ServerModule) -> ModuleContext:
    return ModuleContext(services=services, logger=get_logger(module.name))


def boot() -> tuple[ServerModule, ...]:
    """Idempotent: Django may call `ready()` more than once in some management paths."""
    global _booted, _services
    with _lock:
        if _booted is not None:
            return _booted
        config = get_config()
        registry = load_registry()
        _validate(registry)
        services = ServiceRegistry(
            config=config,
            http=build_http_client(config),
            cache=cache,
            logger=get_logger("app"),
        )
        for module in registry:
            if module.register:
                module.register(_context(services, module))
        for module in registry:
            if module.start:
                module.start(_context(services, module))
        _booted, _services = registry, services
        atexit.register(shutdown)
        log.info(
            "booted %d modules (%s) env=%s routing=%s geocoding=%s weather=%s",
            len(registry),
            ", ".join(f"{m.name}@{m.version}" for m in registry),
            config.env,
            config.routing_mode,
            config.geocoding_mode,
            config.weather_mode,
        )
        return registry


def shutdown() -> None:
    global _booted, _services
    with _lock:
        if _booted is None or _services is None:
            return
        for module in reversed(_booted):
            if module.stop:
                try:
                    module.stop(_context(_services, module))
                except Exception:  # shutdown must keep going
                    log.exception("module %s failed to stop cleanly", module.name)
        _services.http.close()
        _booted, _services = None, None


def is_ready() -> bool:
    return _booted is not None
