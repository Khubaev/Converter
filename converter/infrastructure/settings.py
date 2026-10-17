"""Конфигурация из окружения / .env."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_DEFAULT_VISION_URL = "https://smarty.mail.ru/api/v1/text/recognize"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class VkVisionSettings:
    """Параметры клиента VK Vision."""

    oauth_token: str
    oauth_provider: str = "mcs"
    api_url: str = _DEFAULT_VISION_URL
    timeout_seconds: float = 60.0

    @property
    def is_configured(self) -> bool:
        return bool(self.oauth_token.strip())


def load_env_file() -> None:
    """Подхватывает .env из корня проекта и из текущей папки."""
    # override=True: значение из .env важнее пустой переменной окружения.
    load_dotenv(_PROJECT_ROOT / ".env", override=True)
    load_dotenv(Path.cwd() / ".env", override=True)


@dataclass(frozen=True, slots=True)
class N8nSettings:
    """Адрес webhook n8n, куда уходит JSON распознанного текста."""

    path: str
    timeout_seconds: float = 30.0

    @property
    def is_configured(self) -> bool:
        return self.path.startswith(("http://", "https://"))


def load_n8n_settings() -> N8nSettings:
    """Читает PATH_N8N — полный URL приёмника сборки."""
    load_env_file()
    return N8nSettings(path=os.getenv("PATH_N8N", "").strip())


def load_vk_vision_settings() -> VkVisionSettings:
    """Читает VK_VISION_* из окружения."""
    load_env_file()
    return VkVisionSettings(
        oauth_token=os.getenv("VK_VISION_OAUTH_TOKEN", "").strip(),
        oauth_provider=os.getenv("VK_VISION_OAUTH_PROVIDER", "mcs").strip() or "mcs",
        api_url=os.getenv("VK_VISION_URL", _DEFAULT_VISION_URL).strip() or _DEFAULT_VISION_URL,
        timeout_seconds=float(os.getenv("VK_VISION_TIMEOUT_SECONDS", "60")),
    )
