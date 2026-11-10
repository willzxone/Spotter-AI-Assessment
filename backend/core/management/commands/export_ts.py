"""`manage.py export_ts`: write the frontend's API types from the backend's OpenAPI schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from core import tsgen
from core.api import get_api
from core.config import REPO_DIR

TARGET = REPO_DIR / "frontend" / "src" / "integrations" / "rpc" / "api.gen.ts"


def rendered() -> str:
    # An empty prefix gives procedure paths ("trips/plan") rather than mounted URLs.
    return tsgen.render(get_api().get_openapi_schema(path_prefix=""))


class Command(BaseCommand):
    help = "Write the frontend's API types (frontend/src/integrations/rpc/api.gen.ts)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--check",
            action="store_true",
            help="Fail if the file is out of date instead of writing it (for CI).",
        )

    def handle(self, *args: Any, check: bool, **options: Any) -> None:
        target: Path = TARGET
        shown = target.relative_to(REPO_DIR)
        fresh = rendered()
        current = target.read_text(encoding="utf-8") if target.is_file() else None

        if check:
            if current != fresh:
                raise CommandError(f"{shown} is out of date: run `python manage.py export_ts`")
            self.stdout.write(f"{shown} is up to date")
            return
        if current == fresh:
            self.stdout.write(f"{shown} unchanged")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(fresh, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"wrote {shown}"))
