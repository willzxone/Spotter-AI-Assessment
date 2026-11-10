"""The TypeScript generator: its translation rules, and that the committed frontend types are current."""

from __future__ import annotations

from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from core import tsgen

_REF = "#/components/schemas/"


def _json(name: str) -> dict[str, Any]:
    return {"application/json": {"schema": {"$ref": _REF + name}}}


def _post(input_name: str | None, output_name: str, summary: str = "Do the thing") -> dict[str, Any]:
    op: dict[str, Any] = {
        "summary": summary,
        "responses": {200: {"description": "OK", "content": _json(output_name)}},
    }
    if input_name:
        op["requestBody"] = {"content": _json(input_name), "required": True}
    return {"post": op}


def _openapi(schemas: dict[str, Any], paths: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"components": {"schemas": schemas}, "paths": paths or {}}


def _block(rendered: str, header: str) -> str:
    """The declaration that starts with `header`, up to its closing brace."""
    start = rendered.index(header)
    return rendered[start : rendered.index("\n}", start) + 2]


def test_defaulted_fields_are_optional_on_input_but_always_present_on_output() -> None:
    fields = {"a": {"type": "integer"}, "b": {"type": "integer", "default": 1}}
    schemas = {
        "In": {"type": "object", "properties": fields, "required": ["a"]},
        "Out": {"type": "object", "properties": fields, "required": ["a"], "description": "A result."},
    }
    out = tsgen.render(_openapi(schemas, {"/x/do": _post("In", "Out")}))

    assert "  a: number\n  b?: number" in _block(out, "export interface In ")
    assert "  a: number\n  b: number" in _block(out, "export interface Out ")
    assert "/** A result. */\nexport interface Out {" in out


def test_inputs_reach_through_references() -> None:
    schemas = {
        "In": {"type": "object", "properties": {"p": {"$ref": _REF + "Point"}}, "required": ["p"]},
        "Point": {"type": "object", "properties": {"label": {"type": "string", "default": ""}}},
        "Out": {"type": "object", "properties": {}},
    }
    out = tsgen.render(_openapi(schemas, {"/x/do": _post("In", "Out")}))
    assert "  label?: string" in _block(out, "export interface Point ")


_PAIR = {"type": "array", "prefixItems": [{"type": "number"}] * 2, "minItems": 2, "maxItems": 2}


def test_value_translations() -> None:
    props = {
        "maybe": {"anyOf": [{"type": "string", "maxLength": 9}, {"type": "null"}]},
        "pair": _PAIR,
        "pairs": {"type": "array", "items": _PAIR},
        "names": {"type": "array", "items": {"anyOf": [{"type": "string"}, {"type": "null"}]}},
        "level": {"enum": ["low", "it's"], "type": "string"},
        "fixed": {"const": "load"},
        "at": {"type": "string", "format": "date-time"},
        "ok": {"type": "boolean"},
        "both": {"allOf": [{"$ref": _REF + "Out"}], "default": None},
        "kebab-key": {"type": "integer"},
    }
    schemas = {"Out": {"type": "object", "properties": props}}
    block = _block(tsgen.render(_openapi(schemas)), "export interface Out ")

    for line in [
        "maybe: string | null",
        "pair: [number, number]",
        "pairs: [number, number][]",
        "names: (string | null)[]",
        "level: 'low' | 'it\\'s'",
        "fixed: 'load'",
        "at: IsoDateTime",
        "ok: boolean",
        "both: Out",
        "'kebab-key': number",
    ]:
        assert f"  {line}\n" in block, line


def test_named_aliases_become_type_declarations() -> None:
    schemas = {
        "Level": {"enum": ["low", "high"], "type": "string"},
        "Interval": {"enum": [10, 25], "type": "integer"},
        "Kind": {"anyOf": [{"$ref": _REF + "Level"}, {"const": "load", "type": "string"}]},
    }
    out = tsgen.render(_openapi(schemas))
    assert "export type Level = 'low' | 'high'\n" in out
    assert "export type Interval = 10 | 25\n" in out
    assert "export type Kind = Level | 'load'\n" in out


def test_procedure_map() -> None:
    schemas = {name: {"type": "object", "properties": {}} for name in ("In", "Out", "Rules")}
    paths = {"/x/do": _post("In", "Out", "Do it"), "/x/rules": _post(None, "Rules", "The rules")}
    out = tsgen.render(_openapi(schemas, paths))
    assert "  /** Do it */\n  'x/do': { input: In; output: Out }\n" in out
    assert "  /** The rules */\n  'x/rules': { input: void; output: Rules }\n" in out
    assert "export type ProcedureOutput<TPath extends ProcedurePath>" in out


@pytest.mark.parametrize(
    ("schemas", "paths", "complaint"),
    [
        ({"Out": {"type": "object", "properties": {"a": {"oneOf": [{"type": "string"}]}}}}, {}, "oneOf"),
        (
            {"Out": {"type": "object", "properties": {}, "additionalProperties": {"type": "string"}}},
            {},
            "extra",
        ),
        ({"Out": {"type": "object", "properties": {"a": {"type": "array"}}}}, {}, "item type"),
        ({"Out": {"type": "object", "properties": {}}}, {"/x/do": {"get": {}}}, "POST only"),
        ({"Out": {"type": "object", "properties": {}}}, {"/x/do": _post("Missing", "Out")}, "Missing"),
    ],
)
def test_unsupported_schemas_fail_loudly(
    schemas: dict[str, Any], paths: dict[str, Any], complaint: str
) -> None:
    with pytest.raises(tsgen.SchemaError, match=complaint):
        tsgen.render(_openapi(schemas, paths))


def test_frontend_types_are_current() -> None:
    """Changing a DTO without regenerating would leave the frontend typed against an old API."""
    try:
        call_command("export_ts", "--check")
    except CommandError as exc:
        pytest.fail(str(exc))
