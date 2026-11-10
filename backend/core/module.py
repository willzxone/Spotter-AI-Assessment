"""The module contract.

A feature module is a package under `modules/<name>/` whose `module.py` exports a
`ServerModule` manifest. The manifest declares which shared services the module
needs; the kernel refuses to boot if a module asks for something core does not
provide. `register` wires the module (builds its adapter, configures its service);
`start`/`stop` bracket background work — none of today's modules run any, but the
hooks keep the lifecycle explicit.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

import httpx
from django.core.cache.backends.base import BaseCache

from core.config import Config
from core.rpc import Procedures


class Service(StrEnum):
    """Shared services core hands to modules."""

    CONFIG = "config"
    HTTP = "http"
    CACHE = "cache"
    LOGGER = "logger"


@dataclass(frozen=True, slots=True)
class ServiceRegistry:
    config: Config
    http: httpx.Client
    cache: BaseCache
    logger: logging.Logger


@dataclass(frozen=True, slots=True)
class ModuleContext:
    """What a module's lifecycle hooks receive."""

    services: ServiceRegistry
    logger: logging.Logger

    @property
    def config(self) -> Config:
        return self.services.config

    @property
    def http(self) -> httpx.Client:
        return self.services.http

    @property
    def cache(self) -> BaseCache:
        return self.services.cache


Hook = Callable[[ModuleContext], None]


@dataclass(frozen=True, slots=True)
class ServerModule:
    name: str
    version: str
    requires: frozenset[Service]
    procedures: Procedures | None = None
    register: Hook | None = None
    start: Hook | None = None
    stop: Hook | None = None
