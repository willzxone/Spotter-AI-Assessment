"""Production boot checks, and the hostname Render injects."""

from __future__ import annotations

import pytest

from core.config import ConfigError, load_config

PROD = {
    "DJANGO_ENV": "production",
    "SECRET_KEY": "x" * 40,
    "ROUTING_MODE": "simulated",
    "GEOCODING_MODE": "simulated",
    "WEATHER_MODE": "simulated",
}


def test_production_refuses_to_boot_without_a_hostname() -> None:
    with pytest.raises(ConfigError, match="ALLOWED_HOSTS"):
        load_config(PROD)


def test_render_hostname_alone_is_enough() -> None:
    config = load_config({**PROD, "RENDER_EXTERNAL_HOSTNAME": "trucks.onrender.com"})
    assert config.allowed_hosts == ("trucks.onrender.com",)


def test_render_hostname_joins_explicit_hosts_once() -> None:
    config = load_config(
        {
            **PROD,
            "ALLOWED_HOSTS": "trucks.example.com, trucks.onrender.com",
            "RENDER_EXTERNAL_HOSTNAME": "trucks.onrender.com",
        }
    )
    assert config.allowed_hosts == ("trucks.example.com", "trucks.onrender.com")


def test_production_refuses_a_short_secret_key() -> None:
    with pytest.raises(ConfigError, match="SECRET_KEY"):
        load_config({**PROD, "SECRET_KEY": "short", "ALLOWED_HOSTS": "trucks.example.com"})
