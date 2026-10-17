"""Адаптер RecognizedTextPublisher: POST JSON на webhook из PATH_N8N."""

import json
from collections.abc import Mapping

import httpx

from converter.domain.exceptions import AssemblyDispatchError, AssemblyNotConfiguredError
from converter.infrastructure.settings import N8nSettings, load_n8n_settings


class N8nRecognizedTextPublisher:
    """Отправляет распознанный текст на сборку. URL клиенту не отдаёт."""

    def __init__(
        self,
        settings: N8nSettings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or load_n8n_settings()
        self._client = client

    def publish(self, payload: Mapping[str, object]) -> object:
        if not self._settings.path:
            raise AssemblyNotConfiguredError()
        if not self._settings.is_configured:
            raise AssemblyNotConfiguredError("PATH_N8N должен быть абсолютным http(s) URL.")

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        try:
            response = self._post(body, headers)
        except httpx.TimeoutException as exc:
            raise AssemblyDispatchError("Таймаут отправки на сборку.") from exc
        except httpx.HTTPError as exc:
            raise AssemblyDispatchError("Не удалось связаться с сервисом сборки.") from exc

        if response.status_code >= 400:
            detail = response.text[:300].strip()
            message = f"Сервис сборки вернул HTTP {response.status_code}."
            if detail:
                message = f"{message} {detail}"
            raise AssemblyDispatchError(message)
        if not response.content:
            raise AssemblyDispatchError("Сервис сборки вернул пустой ответ.")
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise AssemblyDispatchError("Сервис сборки вернул не JSON.") from exc

    def _post(self, body: bytes, headers: dict[str, str]) -> httpx.Response:
        if self._client is not None:
            return self._client.post(self._settings.path, content=body, headers=headers)
        with httpx.Client(timeout=self._settings.timeout_seconds, follow_redirects=False) as client:
            return client.post(self._settings.path, content=body, headers=headers)
