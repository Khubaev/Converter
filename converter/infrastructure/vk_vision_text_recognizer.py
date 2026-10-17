"""Адаптер TextRecognizer: VK Cloud Vision document OCR."""

from __future__ import annotations

import json
from typing import Any

import httpx

from converter.domain.exceptions import OcrError, OcrNotConfiguredError
from converter.infrastructure.settings import VkVisionSettings, load_vk_vision_settings

# name в meta должен совпадать с именем поля multipart ("file"), не с именем файла на диске.
_META = json.dumps({"mode": "detailed", "images": [{"name": "file"}]}, ensure_ascii=False)


class VkVisionTextRecognizer:
    """Шлёт одно JPEG в Vision и возвращает plain text.

    В Vision уходит уже распакованный JPEG из ConversionArtifactBundle,
    а не ZIP (ZIP собирается только при скачивании).
    """

    def __init__(
        self,
        settings: VkVisionSettings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or load_vk_vision_settings()
        self._client = client

    def recognize(self, image: bytes, filename: str) -> str:
        if not self._settings.is_configured:
            raise OcrNotConfiguredError()
        if not image:
            raise OcrError("Пустое изображение для OCR.")
        if image[:2] == b"PK":
            raise OcrError(
                "В OCR передан ZIP. Нужен JPEG страницы; проверьте RecognizeConversionResult."
            )
        if not image.startswith(b"\xff\xd8"):
            raise OcrError(
                f"В OCR ожидался JPEG, получено {len(image)} байт "
                f"(сигнатура {image[:8]!r})."
            )

        params = {
            "oauth_token": self._settings.oauth_token,
            "oauth_provider": self._settings.oauth_provider,
        }
        # Поле формы обязательно называется "file" — как в meta.images[].name.
        files = {
            "file": (filename or "page.jpg", image, "image/jpeg"),
        }
        data = {"meta": _META}

        try:
            response = self._request(params=params, files=files, data=data)
        except httpx.TimeoutException as exc:
            raise OcrError("Таймаут запроса к VK Vision.") from exc
        except httpx.HTTPError as exc:
            raise OcrError(f"Сеть VK Vision: {exc}") from exc

        if response.status_code >= 400:
            raise OcrError(
                f"VK Vision HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise OcrError("VK Vision вернул не-JSON ответ.") from exc

        return self._extract_text(payload).strip()

    def _request(
        self,
        *,
        params: dict[str, str],
        files: dict[str, tuple[str, bytes, str]],
        data: dict[str, str],
    ) -> httpx.Response:
        if self._client is not None:
            return self._client.post(
                self._settings.api_url,
                params=params,
                files=files,
                data=data,
            )
        with httpx.Client(timeout=self._settings.timeout_seconds) as client:
            return client.post(
                self._settings.api_url,
                params=params,
                files=files,
                data=data,
            )

    def _extract_text(self, payload: Any) -> str:
        """Достаёт текст: body.objects[].text или detailed body.objects[].results[].words[].text."""
        if isinstance(payload, str):
            return payload
        if not isinstance(payload, dict):
            raise OcrError("Неожиданный формат ответа VK Vision.")

        status = payload.get("status")
        body = payload.get("body", payload)

        if isinstance(status, int) and status >= 400:
            detail = body if isinstance(body, str) else payload
            raise OcrError(f"VK Vision status={status}: {detail}")

        if isinstance(body, str):
            if status and int(status) >= 400:
                raise OcrError(f"VK Vision: {body}")
            return body

        texts: list[str] = []
        if isinstance(body, dict):
            objects = body.get("objects")
            if isinstance(objects, list):
                for item in objects:
                    texts.append(self._text_from_object(item))
            else:
                texts.append(self._text_from_object(body))
        elif isinstance(body, list):
            for item in body:
                texts.append(self._text_from_object(item))

        return "\n".join(part for part in texts if part).strip()

    def _text_from_object(self, item: Any) -> str:
        if not isinstance(item, dict):
            return str(item) if item else ""

        obj_status = item.get("status")
        if obj_status not in (None, 0, "0"):
            error = item.get("error") or f"status={obj_status}"
            raise OcrError(f"VK Vision отклонил изображение: {error}")

        direct = item.get("text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        # mode=detailed: текст в results[].words[].text
        results = item.get("results") or item.get("lines") or item.get("set")
        if isinstance(results, list):
            lines: list[str] = []
            for line in results:
                line_text = self._text_from_line(line)
                if line_text:
                    lines.append(line_text)
            if lines:
                return "\n".join(lines)

        words = item.get("words")
        if isinstance(words, list):
            joined = " ".join(
                w.get("text", "").strip()
                for w in words
                if isinstance(w, dict) and w.get("text")
            )
            if joined.strip():
                return joined.strip()

        return ""

    def _text_from_line(self, line: Any) -> str:
        if isinstance(line, str):
            return line.strip()
        if not isinstance(line, dict):
            return ""
        if isinstance(line.get("text"), str) and line["text"].strip():
            return line["text"].strip()
        words = line.get("words")
        if isinstance(words, list):
            return " ".join(
                w.get("text", "").strip()
                for w in words
                if isinstance(w, dict) and w.get("text")
            ).strip()
        return ""
