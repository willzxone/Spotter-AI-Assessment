from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    label = "core"

    def ready(self) -> None:
        # Boot every module once settings are loaded and before the first request,
        # so a misconfigured adapter fails the deploy instead of the first user.
        from core import kernel

        kernel.boot()
