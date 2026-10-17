"""Разбор ответа n8n: поле output — это JSON-строка, а не объект."""

import json

from converter.domain.exceptions import AssemblyDispatchError


def parse_assembly_response(body: object) -> object:
    """Снимает оболочку [{output: "..."}] и возвращает документ без экранирования."""
    if isinstance(body, list):
        if not body:
            raise AssemblyDispatchError("Сервис сборки вернул пустой список.")
        documents = [_unwrap(item) for item in body]
        if len(documents) == 1:
            return documents[0]
        return documents
    return _unwrap(body)


def _unwrap(item: object) -> object:
    if isinstance(item, dict) and "output" in item:
        return _parse_output(item["output"])
    if isinstance(item, str):
        return _parse_output(item)
    if isinstance(item, (dict, list)):
        return item
    raise AssemblyDispatchError("В ответе сборки нет документа JSON.")


def _parse_output(value: object) -> object:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        raise AssemblyDispatchError("Поле output пустое или не является JSON.")

    parsed = _loads(_strip_fence(value.strip()))
    if isinstance(parsed, str):
        nested = parsed.strip()
        if nested.startswith("{") or nested.startswith("["):
            parsed = _loads(nested)
    if not isinstance(parsed, (dict, list)):
        raise AssemblyDispatchError("Поле output не содержит объект JSON.")
    return parsed


def _loads(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AssemblyDispatchError("Не удалось прочитать JSON из ответа сборки.") from exc


def _strip_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
